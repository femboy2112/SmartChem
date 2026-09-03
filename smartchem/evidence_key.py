"""EVD-KEY-01 -- the section 9.1 ``ReactionEvidenceKey``: one canonical, direction-specific reaction identity.

Before this, every sourced-evidence provider rolled its OWN reaction key: the kinetics/Eyring providers keyed on
canonical STRUCTURE (sound -- an isomer never inherits another reaction's rate), while the conditions/selectivity
providers keyed on FORMULA signatures (the isomer-borrow hazard).  Three independent gcd-stoichiometry normalisers
existed side by side.  This is the ONE value the standard's section 9.1 names: two reactions share an evidence key
IFF they are the same reaction at canonical STRUCTURE, in the same DIRECTION, with the same PRIMITIVE (gcd-reduced)
stoichiometry and the same CONTEXT.

ADOPTION, stated honestly (not "everywhere" yet): the sound rate providers -- ``experiment/kinetics.py`` and
``experiment/eyring.py`` -- now resolve their sourced records THROUGH this type (``reaction_evidence_key`` /
``record_evidence_key``), so it is LIVE in production, not a dead switch.  Migrating the FORMULA-keyed providers
(``decompiler_conditions``' decomposition path, ``selectivity``, and ``decompiler_review``) onto it -- which is
what would close their isomer-borrow hazard -- is the remaining EVD-KEY-01 work; those providers do NOT key on
this type yet.  The ``context`` field is now LIVE too (EVD-KEY-CTX-01): those same two rate providers populate a
``"phase"`` dimension -- from a record's SOURCED phase and a step's DECLARED medium -- and resolve through the
:meth:`ReactionEvidenceKey.applies_to` LOOKUP relation, which subsumes context rather than equating it, so a
gas-phase sourced rate no longer silently answers a step declared to run in a conflicting phase (the phase-borrow,
the condition-domain analogue of the isomer-borrow) while a phase-unspecified step still resolves as before.

Fields (section 9.1):

* ``reactant_identities`` / ``product_identities`` -- each a canonical, sorted tuple of ``(structure-digest,
  coefficient)`` pairs, the digest being ``canonical_digest(molecule.canonical())`` (the SAME structural identity
  the rest of the pipeline keys on), so two constitutional isomers get DIFFERENT keys.  DIRECTION is encoded
  structurally: which side a species sits on -- a decomposition and its algebraic reverse are different keys.
* stoichiometry is PRIMITIVE: coefficients are gcd-reduced across both sides, so a reaction written at any scale
  (``2A -> 2B`` vs ``A -> B``) yields ONE key -- the scale-invariance the kinetics provider already relied on.
* ``context`` -- the optional, canonically-sorted ``(dimension, value)`` pairs (phase / standard state / condition
  domain) section 9.1 adds.  Empty by default, so it never SPLITS a key a provider did not mean to distinguish; as
  part of the key's IDENTITY (``==``) a declared context makes the key strictly FINER, and it can never merge two
  distinct contexts.  The rate providers populate the ``"phase"`` dimension via :func:`phase_context` (a record's
  sourced phase, a step's declared medium), and the LOOKUP is :meth:`ReactionEvidenceKey.applies_to`, which SUBSUMES
  context (a dimension both sides declare must AGREE; a dimension only one side declares is unconstrained) -- so an
  explicit phase conflict withholds a borrow, an unspecified phase does not regress, and identity stays exact.

This is the STRUCTURE-and-stoichiometry identity of a reaction.  It deliberately carries no rate, condition, or
source PAYLOAD -- those are the VALUES a provider stores AGAINST this key; the source/citation lives with the
record, not in the key (a key is what you look up BY, not what you found).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import gcd

from .contracts import Digestible, canonical_digest

__all__ = [
    "REACTION_EVIDENCE_KEY_SCHEMA",
    "PHASE_DIMENSION",
    "ReactionEvidenceKey",
    "normalize_phase",
    "phase_context",
]

REACTION_EVIDENCE_KEY_SCHEMA = "smartchem.evidence/reaction-evidence-key-v1alpha1"

#: The ``context`` dimension name the rate providers populate: the reaction's phase / condition domain.
PHASE_DIMENSION = "phase"

#: The initial controlled phase vocabulary for the ``"phase"`` context dimension.  DELIBERATELY SMALL and
#: EXACT-MATCH (case/whitespace-insensitive): a medium string is recognised only as one of these canonical
#: phases, and ANY unrecognised medium normalises to ``""`` -- it declines.  Declining is the SOUND default:
#: an unrecognised phase leaves the key context-free on that dimension, so it matches ANY phase exactly as it
#: did before this field existed -- a missing or wrong entry can only FAIL to close a borrow, never manufacture
#: a false refusal or a false match.  A fuzzy / substring match WOULD manufacture one ("non-aqueous" contains
#: "aqueous"; "gas" is a substring of many words), which is why this is a closed dictionary, never a heuristic.
#: Extend it with more canonical phases as sourced data needs them; never loosen it to substring matching.
_PHASE_ALIASES: dict[str, str] = {
    "gas": "gas", "gaseous": "gas", "gas phase": "gas", "gas-phase": "gas",
    "vapor": "gas", "vapour": "gas", "g": "gas",
    "aqueous": "aqueous", "aqueous solution": "aqueous", "water": "aqueous", "aq": "aqueous",
}


def normalize_phase(medium: "object") -> str:
    """Map a free-text medium/phase string to a canonical phase token, or ``""`` when unrecognised.

    Conservative by construction: an exact (case- and whitespace-insensitive) lookup against the small
    controlled :data:`_PHASE_ALIASES` vocabulary, declining everything else.  Declining is SOUND -- a
    context-free key matches any phase, so an unclassifiable medium never falsely refuses nor falsely
    resolves a record; a fuzzy match would not be sound.  A non-string returns ``""``.
    """
    if not isinstance(medium, str):
        return ""
    return _PHASE_ALIASES.get(medium.strip().lower(), "")


def phase_context(medium: "object") -> "tuple[tuple[str, str], ...]":
    """The section-9.1 ``context`` a medium contributes: ``(("phase", token),)`` if recognised, else ``()``.

    The single bridge from a free-text medium (a record's sourced phase, a step's declared
    :attr:`~smartchem.conditions.ConditionEnvelope.medium`) to the canonical, key-ready context tuple.  An
    unrecognised or empty medium yields ``()`` -- a context-free key -- so the reaction still resolves exactly
    as it did before a phase was declared.
    """
    token = normalize_phase(medium)
    return ((PHASE_DIMENSION, token),) if token else ()


def _merge(pairs: "object") -> "dict[str, int]":
    """Sum coefficients per structure digest (a species appearing twice on one side merges)."""
    merged: dict[str, int] = {}
    for digest, coefficient in pairs:
        if not isinstance(digest, str) or not digest:
            raise ValueError("a structure digest must be a non-empty string")
        if type(coefficient) is not int or coefficient <= 0:
            raise ValueError("a coefficient must be a positive int")
        merged[digest] = merged.get(digest, 0) + coefficient
    return merged


@dataclass(frozen=True)
class ReactionEvidenceKey(Digestible):
    """The canonical, direction-specific STRUCTURE+stoichiometry+context identity of a reaction (section 9.1)."""

    schema_version: str
    reactant_identities: tuple[tuple[str, int], ...]
    product_identities: tuple[tuple[str, int], ...]
    context: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != REACTION_EVIDENCE_KEY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {REACTION_EVIDENCE_KEY_SCHEMA!r}")
        for name, side in (
            ("reactant_identities", self.reactant_identities),
            ("product_identities", self.product_identities),
        ):
            if type(side) is not tuple or not side:
                raise ValueError(f"{name} must be a non-empty tuple of (structure-digest, coefficient) pairs")
            seen: set[str] = set()
            prev: "tuple[str, int] | None" = None
            for pair in side:
                if type(pair) is not tuple or len(pair) != 2:
                    raise ValueError(f"each {name} entry must be a (digest, coefficient) pair")
                digest, coefficient = pair
                if not isinstance(digest, str) or not digest:
                    raise ValueError("a structure digest must be a non-empty string")
                if type(coefficient) is not int or coefficient <= 0:
                    raise ValueError("a coefficient must be a positive int")
                if digest in seen:
                    raise ValueError(f"{name} names a structure twice; coefficients must be merged")
                seen.add(digest)
                if prev is not None and pair < prev:
                    raise ValueError(f"{name} must be in canonical (sorted) order")
                prev = pair
        if type(self.context) is not tuple or any(
            type(c) is not tuple or len(c) != 2 or not all(isinstance(x, str) and x for x in c)
            for c in self.context
        ):
            raise TypeError("context must be a tuple of (dimension, value) non-empty string pairs")
        if list(self.context) != sorted(self.context):
            raise ValueError("context must be in canonical (sorted) order")
        if len({dim for dim, _ in self.context}) != len(self.context):
            raise ValueError("context must name each dimension at most once")

    @classmethod
    def of(
        cls,
        reactant_pairs: "object",
        product_pairs: "object",
        *,
        context: "object" = (),
        primitive: bool = True,
    ) -> "ReactionEvidenceKey":
        """Build from ``(structure-digest, coefficient)`` pairs per side (the digests already computed).

        ``primitive`` (default) gcd-reduces the coefficients across BOTH sides, so a reaction written at any scale
        yields one key.  ``context`` is an optional iterable of ``(dimension, value)`` string pairs.
        """
        reactants = _merge(reactant_pairs)
        products = _merge(product_pairs)
        if not reactants or not products:
            raise ValueError("a reaction evidence key needs at least one reactant and one product")
        if primitive:
            divisor = 0
            for coefficient in (*reactants.values(), *products.values()):
                divisor = gcd(divisor, coefficient)
            divisor = divisor or 1
            reactants = {d: c // divisor for d, c in reactants.items()}
            products = {d: c // divisor for d, c in products.items()}
        return cls(
            REACTION_EVIDENCE_KEY_SCHEMA,
            tuple(sorted(reactants.items())),
            tuple(sorted(products.items())),
            tuple(sorted(context)),
        )

    @classmethod
    def from_molecules(
        cls,
        reactant_mol_pairs: "object",
        product_mol_pairs: "object",
        *,
        context: "object" = (),
        primitive: bool = True,
    ) -> "ReactionEvidenceKey":
        """Build from ``(molecule, coefficient)`` pairs, digesting each ``molecule.canonical()`` (isomer-distinct)."""
        reactants = [(canonical_digest(m.canonical()), int(c)) for m, c in reactant_mol_pairs]
        products = [(canonical_digest(m.canonical()), int(c)) for m, c in product_mol_pairs]
        return cls.of(reactants, products, context=context, primitive=primitive)

    @property
    def sides(self) -> "tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]":
        """The ``(reactants, products)`` structure-key tuple -- the shape the kinetics provider's key has always had."""
        return self.reactant_identities, self.product_identities

    def applies_to(self, step_key: "ReactionEvidenceKey") -> bool:
        """Does a sourced record with THIS key answer a step whose key is ``step_key``?  (the section-9.1 LOOKUP.)

        The lookup relation, deliberately NOT identity (``==``).  Structure, stoichiometry, and DIRECTION must
        match EXACTLY -- ``self.sides == step_key.sides`` -- so an isomer or the reverse direction never answers.
        ``context`` is SUBSUMED, not equated: on every dimension BOTH keys declare, the values must AGREE (a
        gas-phase record does not answer an aqueous step -- the phase-borrow closed), while a dimension only ONE
        side declares is unconstrained (a phase-unspecified step still resolves a phase-tagged record, and an
        untagged record still answers any step -- neither regresses).  The relation is symmetric in context and
        strictly weaker than ``==``: ``a == b`` implies ``a.applies_to(b)``, never the reverse.
        """
        if type(step_key) is not ReactionEvidenceKey:
            raise TypeError("applies_to takes a ReactionEvidenceKey")
        if self.sides != step_key.sides:
            return False
        mine = dict(self.context)
        theirs = dict(step_key.context)
        return all(mine[dim] == theirs[dim] for dim in mine.keys() & theirs.keys())

    def with_context(self, context: "object") -> "ReactionEvidenceKey":
        """The same reaction key at a declared context (phase/standard-state/condition-domain), section 9.1."""
        return ReactionEvidenceKey(
            self.schema_version, self.reactant_identities, self.product_identities, tuple(sorted(context))
        )
