"""ID-LAYER-01 (first brick) -- the section 5 layered identity model and the section 5.3 ``IdentityLoss`` record.

Today the codebase carries a two-value identity layer (``compilation_ir.IdentityLayer``: FORMULA / STRUCTURE), whose
own docstring names the gap: *"the full stereo/isotope/salt/mixture model is ID-LAYER-01 (TODO)."*  This module is
that model's foundation.  It provides:

* :class:`MatchLayer` -- the ordered lattice of identity layers (section 5.1), coarse to fine, with a refinement
  order.  A claim true at a finer layer is true at every coarser one; never the reverse.
* :class:`LayeredIdentity` -- a species resolved at every layer the current model can actually PERCEIVE, keyed by a
  per-layer canonical digest that is byte-congruent with the existing pipeline identities (so this does not fork a
  new notion of identity).  Layers it cannot perceive are ABSENT, never guessed.
* :func:`same_identity_at` -- section 5.4 layer-relative equality.  It returns ``True``/``False`` only when BOTH
  identities perceive the layer, and ``None`` (honest UNKNOWN) when either cannot.  Formula equality is therefore
  NEVER silently promoted to a finer-layer (structure) match -- the exact confusion section 5.4 forbids.
* :class:`IdentityLoss` / :func:`formula_reduction_loss` -- the section 5.3 typed loss record (the record IR-LOSS-01
  will carry inside the IR), and the concrete loss the pipeline incurs when a structural input is reduced to its
  formula (the ``decompile --smiles`` path), lowered to a BLOCKER for every structure-level claim.

SCOPE (named honestly, W3): the current :class:`~smartchem.category.Molecule` model perceives constitution (the
atom/bond graph) but not stereochemistry or isotope labels, so :meth:`LayeredIdentity.of_molecule` resolves FORMULA
and CONSTITUTION and stops there; CONFIGURATION/ISOTOPIC are declared in the lattice but not yet perceivable, so a
match at them is reported UNKNOWN rather than fabricated.  Wiring :class:`MatchLayer` into the service's
``IdentityPolicy`` (so a request declares its comparison layer) is a named follow-on (ID-LAYER-02); salt/mixture
COMPONENT identity lives with the material model (StockMaterial, section 10).  None of that is silently assumed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import Digestible, canonical_digest

__all__ = [
    "IDENTITY_LOSS_SCHEMA",
    "LAYERED_IDENTITY_SCHEMA",
    "MatchLayer",
    "LossSeverity",
    "IdentityLoss",
    "LayeredIdentity",
    "same_identity_at",
    "refines",
    "formula_reduction_loss",
]

IDENTITY_LOSS_SCHEMA = "smartchem.identity/identity-loss-v1alpha1"
LAYERED_IDENTITY_SCHEMA = "smartchem.identity/layered-identity-v1alpha1"


class MatchLayer(str, Enum):
    """The identity layer a claim or match is made at (standard section 5.1), ordered coarse -> fine.

    A claim that holds at a finer layer holds at every coarser layer (two molecules equal at CONFIGURATION are equal
    at CONSTITUTION and at FORMULA); the converse is false, which is section 5.4's whole point.
    """

    FORMULA = "FORMULA"              # elemental counts + total charge; no topology (section 5.1 FormulaIdentity)
    CONSTITUTION = "CONSTITUTION"    # atom/bond graph; no stereo/isotope (today's STRUCTURE layer)
    CONFIGURATION = "CONFIGURATION"  # + stereochemistry (cis/trans, R/S)
    ISOTOPIC = "ISOTOPIC"            # + isotope labels (the finest layer the lattice currently names)


# Refinement rank: a higher index is a finer (more specific) layer.  This tuple IS the refinement order.
_LAYER_RANK = {layer: i for i, layer in enumerate(
    (MatchLayer.FORMULA, MatchLayer.CONSTITUTION, MatchLayer.CONFIGURATION, MatchLayer.ISOTOPIC)
)}


def refines(fine: MatchLayer, coarse: MatchLayer) -> bool:
    """True iff ``fine`` is at least as specific as ``coarse`` (equality at ``fine`` implies equality at ``coarse``)."""
    if not isinstance(fine, MatchLayer) or not isinstance(coarse, MatchLayer):
        raise TypeError("refines needs two MatchLayer values")
    return _LAYER_RANK[fine] >= _LAYER_RANK[coarse]


class LossSeverity(str, Enum):
    """Whether an identity loss merely warns or blocks matching claims (standard section 5.3)."""

    WARNING = "WARNING"
    BLOCKER = "BLOCKER"


@dataclass(frozen=True)
class IdentityLoss(Digestible):
    """A section 5.3 information-loss record: a represented feature a parser/operation could not preserve.

    The fields are exactly section 5.3's: ``feature``, ``input_representation``, ``retained_representation``,
    ``reason``, ``affected_claims`` and ``severity``.  Per section 5.3, a sourced condition/selectivity/kinetics/
    hazard record MUST NOT survive a loss marked ``BLOCKER`` for its matching key -- this record is what a consumer
    (IR-LOSS-01, evidence keying) checks that against.
    """

    schema_version: str
    feature: str
    input_representation: str
    retained_representation: str
    reason: str
    affected_claims: tuple[str, ...]
    severity: LossSeverity

    def __post_init__(self) -> None:
        if self.schema_version != IDENTITY_LOSS_SCHEMA:
            raise ValueError(f"schema_version must be exactly {IDENTITY_LOSS_SCHEMA!r}")
        for name in ("feature", "input_representation", "retained_representation", "reason"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.affected_claims) is not tuple or any(
            not isinstance(x, str) or not x for x in self.affected_claims
        ):
            raise TypeError("affected_claims must be a tuple of non-empty strings")
        if list(self.affected_claims) != sorted(self.affected_claims):
            raise ValueError("affected_claims must be in canonical (sorted) order")
        if len(set(self.affected_claims)) != len(self.affected_claims):
            raise ValueError("affected_claims must be distinct")
        if not isinstance(self.severity, LossSeverity):
            raise TypeError("severity must be a LossSeverity")
        # A BLOCKER that names no affected claim blocks NOTHING -- a silently vacuous blocker, the fail-open section
        # 5.3 forbids.  A blocker must block at least one claim; reject the incoherent record at construction.
        if self.severity is LossSeverity.BLOCKER and not self.affected_claims:
            raise ValueError("a BLOCKER identity loss must name at least one affected claim")

    def blocks(self, claim: str) -> bool:
        """Whether this loss is a BLOCKER for ``claim`` (section 5.3): a matching affected claim cannot survive it."""
        return self.severity is LossSeverity.BLOCKER and claim in self.affected_claims

    def summary(self) -> str:
        """One canonical line naming the loss, its severity and its affected claims.

        Rendered identically by the human CLI and carried verbatim into the machine ``identity_losses`` field, so the
        two views cannot disagree on what was lost (CLI-JSON-01 human/JSON agreement)."""
        return (
            f"IDENTITY LOSS [{self.severity.value}]: {self.feature} -- {self.reason} "
            f"(input {self.input_representation}, retained {self.retained_representation}); "
            f"affected: {', '.join(self.affected_claims)}"
        )


@dataclass(frozen=True)
class LayeredIdentity(Digestible):
    """A species' identity resolved at every layer the current model can PERCEIVE (standard section 5.1).

    ``digest_by_layer`` maps a perceivable :class:`MatchLayer` to a canonical digest; a layer the model cannot
    establish is simply absent (never a fabricated value).  The FORMULA digest is byte-congruent with
    ``ChemicalIdentity.of_formula`` and the CONSTITUTION digest with ``ChemicalIdentity.of_molecule`` /
    ``_structure_ident``, so a layered identity is the SAME value the rest of the pipeline keys on -- it just also
    records which coarser layers it is comparable at.
    """

    schema_version: str
    known_layer: MatchLayer
    canonical_repr: str
    digest_by_layer: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.schema_version != LAYERED_IDENTITY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {LAYERED_IDENTITY_SCHEMA!r}")
        if not isinstance(self.known_layer, MatchLayer):
            raise TypeError("known_layer must be a MatchLayer")
        if not isinstance(self.canonical_repr, str) or not self.canonical_repr:
            raise ValueError("canonical_repr must be a non-empty string")
        if type(self.digest_by_layer) is not tuple or not self.digest_by_layer:
            raise ValueError("digest_by_layer must be a non-empty tuple of (layer, digest) pairs")
        names = []
        for pair in self.digest_by_layer:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("each digest_by_layer entry must be a (layer, digest) pair")
            layer_name, digest = pair
            if layer_name not in MatchLayer._value2member_map_:
                raise ValueError(f"unknown identity layer {layer_name!r}")
            if not isinstance(digest, str) or not digest:
                raise ValueError("a per-layer digest must be a non-empty string")
            names.append(layer_name)
        if names != sorted(names):
            raise ValueError("digest_by_layer must be in canonical (layer-name-sorted) order")
        if len(set(names)) != len(names):
            raise ValueError("digest_by_layer must name each layer at most once")
        # the known (finest perceived) layer must actually be present, and every layer it refines must be too --
        # a claim to know CONSTITUTION with no FORMULA digest would be an incoherent identity.
        present = {MatchLayer(n) for n in names}
        if self.known_layer not in present:
            raise ValueError("known_layer must appear in digest_by_layer")
        for layer in present:
            if not refines(self.known_layer, layer):
                raise ValueError("digest_by_layer must not carry a layer finer than known_layer")

    def digest_at(self, layer: MatchLayer) -> "str | None":
        """The canonical digest at ``layer``, or ``None`` if this identity cannot be perceived at that layer."""
        if not isinstance(layer, MatchLayer):
            raise TypeError("digest_at needs a MatchLayer")
        for name, digest in self.digest_by_layer:
            if name == layer.value:
                return digest
        return None

    @classmethod
    def of_formula(cls, formula: "object") -> "LayeredIdentity":
        """A FORMULA-only layered identity (no topology claim), congruent with ``ChemicalIdentity.of_formula``."""
        from .decompiler import Formula
        if type(formula) is not Formula:
            raise TypeError("of_formula needs a smartchem.decompiler.Formula")
        return cls(
            LAYERED_IDENTITY_SCHEMA,
            MatchLayer.FORMULA,
            repr(formula),
            ((MatchLayer.FORMULA.value, canonical_digest(formula)),),
        )

    @classmethod
    def of_molecule(cls, molecule: "object") -> "LayeredIdentity":
        """A layered identity for a :class:`~smartchem.category.Molecule`, perceiving FORMULA and CONSTITUTION.

        The FORMULA digest is built from the atom counts AND the molecule's total charge (section 5.1's FormulaIdentity
        is "elemental counts and total charge"), so two species that differ only in charge -- e.g. ``[NH4+]`` and a
        neutral NH4 -- are distinct at FORMULA, and the digest is congruent with ``ChemicalIdentity.of_formula`` of the
        species' TRUE (charged) formula, not of a charge-stripped neutral one.

        The CONSTITUTION digest is ``_structure_ident`` byte-for-byte, so it is exactly as presentation-invariant as
        the shared canonicalizer -- and inherits its limitations: a form the canonicalizer cannot relate to another
        (e.g. an explicit Kekulé structure vs its aromatic spelling) stays distinct.  That is a shared-canonicalizer
        boundary this layered identity reflects, never one it introduces.

        CONFIGURATION/ISOTOPIC are not perceived by the current Molecule model, so they are absent (a match at them is
        UNKNOWN, section 5.3's fail-closed rule) rather than fabricated from the constitution digest.
        """
        from .category import Molecule
        from .compilation_ir import _structure_ident
        from .decompiler import Formula
        if type(molecule) is not Molecule:
            raise TypeError("of_molecule needs a smartchem.category.Molecule")
        formula = Formula.of(dict(molecule.formula), molecule.charge)  # counts + TOTAL CHARGE (section 5.1)
        by_layer = {
            MatchLayer.FORMULA.value: canonical_digest(formula),
            MatchLayer.CONSTITUTION.value: _structure_ident(molecule),
        }
        return cls(
            LAYERED_IDENTITY_SCHEMA,
            MatchLayer.CONSTITUTION,
            repr(molecule),
            tuple(sorted(by_layer.items())),
        )


def same_identity_at(a: LayeredIdentity, b: LayeredIdentity, layer: MatchLayer) -> "bool | None":
    """Section 5.4 layer-relative equality: are ``a`` and ``b`` the same species AT ``layer``?

    Returns ``True``/``False`` only when BOTH identities perceive ``layer``; returns ``None`` -- an honest UNKNOWN --
    when either cannot, so a formula-only identity is never reported equal or unequal to another *at a structural
    layer it cannot see*, and a formula match is never silently promoted to a structure match.  This is the machine
    form of "formula equality is not structure equality".
    """
    if type(a) is not LayeredIdentity or type(b) is not LayeredIdentity:
        raise TypeError("same_identity_at needs two LayeredIdentity values")
    da, db = a.digest_at(layer), b.digest_at(layer)
    if da is None or db is None:
        return None
    return da == db


def formula_reduction_loss(
    input_representation: str,
    retained_formula_repr: str,
    *,
    affected_claims: "tuple[str, ...] | None" = None,
) -> IdentityLoss:
    """The section 5.3 loss incurred when a structural input is reduced to its bare formula (the ``decompile
    --smiles`` path): connectivity, stereochemistry, isotope labels and local charge are dropped.

    It is a BLOCKER -- per section 5.4 a formula must not terminate a structure search, attach structure-specific
    conditions/selectivity, or assert product identity/purity, so every such claim is affected.
    """
    claims = affected_claims if affected_claims is not None else (
        # the four evidence classes section 5.3 names explicitly ("sourced conditions, selectivity, kinetics, and
        # hazard records MUST NOT survive a loss marked as a blocker") ...
        "conditions",
        "hazard",
        "kinetics",
        "selectivity",
        # ... plus the structure-level claims section 5.4 forbids a formula from making.
        "isomer-distinction",
        "product-identity",
        "purity",
        "stereochemistry",
        "structure-identity",
    )
    return IdentityLoss(
        IDENTITY_LOSS_SCHEMA,
        "molecular-constitution",
        input_representation,
        f"{retained_formula_repr} ({MatchLayer.FORMULA.value} layer)",
        "the target was reduced to its elemental formula; connectivity, stereochemistry, isotope labels and local "
        "charge are not represented",
        tuple(sorted(claims)),
        LossSeverity.BLOCKER,
    )
