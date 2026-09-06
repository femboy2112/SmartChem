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
    "stereo_loss",
    "isotope_loss",
    "local_charge_loss",
    "representation_losses_for",
    "blocking_losses",
    "is_blocked",
    "blocked_claim_classes",
    "identity_loss_to_payload",
    "identity_loss_from_payload",
]

# The section-5.3 evidence classes a sourced record MUST NOT survive a blocker for ("sourced conditions,
# selectivity, kinetics, and hazard records"), named once so every producer and consumer keys on the same strings.
EVIDENCE_CLAIM_CLASSES = ("conditions", "hazard", "kinetics", "selectivity")

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

        The machine ``identity_losses`` field carries the STRUCTURED record (IR-LOSS-01), not this string; this
        summary is the DERIVED one-line form that the human CLI prints and that the response's semantic projection
        (``identity_loss_summaries`` / ``response_semantic_fields``) exposes, so the two views cannot disagree on
        what was lost (CLI-JSON-01 human/JSON agreement)."""
        return (
            f"IDENTITY LOSS [{self.severity.value}]: {self.feature} -- {self.reason} "
            f"(input {self.input_representation}, retained {self.retained_representation}); "
            f"affected: {', '.join(self.affected_claims)}"
        )


def identity_loss_to_payload(loss: IdentityLoss) -> dict:
    """A JSON-compatible dict of a section 5.3 :class:`IdentityLoss` -- its structured, machine-readable form.

    This is the FIRST-CLASS record the IR carries (IR-LOSS-01): a consumer reads ``severity``/``affected_claims``
    programmatically, never by parsing the one-line ``summary()``.  The enum rides by its ``.value``; nothing
    derived (the summary) is stored, so the payload is exactly the record's semantic fields.
    """
    if type(loss) is not IdentityLoss:
        raise TypeError("identity_loss_to_payload needs an IdentityLoss")
    return {
        "schema_version": loss.schema_version,
        "feature": loss.feature,
        "input_representation": loss.input_representation,
        "retained_representation": loss.retained_representation,
        "reason": loss.reason,
        "affected_claims": list(loss.affected_claims),
        "severity": loss.severity.value,
    }


def identity_loss_from_payload(payload: dict) -> IdentityLoss:
    """Rebuild an :class:`IdentityLoss` from :func:`identity_loss_to_payload`, re-validating every invariant.

    The frozen record's ``__post_init__`` re-runs, so a tampered loss payload (an empty ``feature``, unsorted or
    duplicate ``affected_claims``, or the fail-open BLOCKER that names no claim) is REFUSED on read rather than
    silently trusted -- deserialization never constructs a loss record it would have rejected itself.
    """
    if not isinstance(payload, dict):
        raise TypeError("identity_loss_from_payload needs a dict")
    return IdentityLoss(
        payload["schema_version"],
        payload["feature"],
        payload["input_representation"],
        payload["retained_representation"],
        payload["reason"],
        tuple(payload["affected_claims"]),
        LossSeverity(payload["severity"]),
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
    def of_molecule(cls, molecule: "object", features: "object | None" = None) -> "LayeredIdentity":
        """A layered identity for a :class:`~smartchem.category.Molecule`, perceiving FORMULA and CONSTITUTION -- and,
        when ``features`` (a :class:`~smartchem.smiles.SmilesFeatures`) is supplied, CONFIGURATION and ISOTOPIC too
        (ID-STEREO-02).

        The FORMULA digest is built from the atom counts AND the molecule's total charge (section 5.1's FormulaIdentity
        is "elemental counts and total charge"), so two species that differ only in charge -- e.g. ``[NH4+]`` and a
        neutral NH4 -- are distinct at FORMULA, and the digest is congruent with ``ChemicalIdentity.of_formula`` of the
        species' TRUE (charged) formula, not of a charge-stripped neutral one.

        The CONSTITUTION digest is ``_structure_ident`` byte-for-byte, so it is exactly as presentation-invariant as
        the shared canonicalizer -- and inherits its limitations: a form the canonicalizer cannot relate to another
        (e.g. an explicit Kekulé structure vs its aromatic spelling) stays distinct.  That is a shared-canonicalizer
        boundary this layered identity reflects, never one it introduces.

        WITHOUT ``features`` (the historical call), the bare ``Molecule`` model cannot see chirality or isotope, so
        CONFIGURATION/ISOTOPIC are absent (a match there is UNKNOWN, section 5.3's fail-closed rule) rather than
        fabricated -- unchanged.  WITH ``features`` (ID-STEREO-02), the parser's perceived stereo/isotope is wired in,
        FAIL-CLOSED on the completeness signal ``features.configuration_complete``:

        * CONFIGURATION is perceived ONLY when the configuration is FULLY determined -- no marked stereocentre scoped
          out and no unperceived double-bond (E/Z) stereo.  Its digest REFINES the CONSTITUTION digest --
          ``canonical_digest(("configuration-layer-v1", constitution, features.configuration_digest or ""))`` -- so
          CONFIGURATION-equal implies CONSTITUTION-equal BY CONSTRUCTION, enantiomers (same constitution, different
          ``configuration_digest``) get DISTINCT identities, and an achiral molecule (``configuration_digest`` None ->
          refinement "") reduces to a deterministic function of its constitution.  When perception is INCOMPLETE
          CONFIGURATION is absent (honest UNKNOWN) -- never reduced to constitution, which would FALSELY MERGE two
          enantiomers differing only at an unperceived centre.
        * ISOTOPIC is perceived exactly when CONFIGURATION is (isotope labels are explicit, so always fully perceived).
          Its digest REFINES the CONFIGURATION digest with the isotope key --
          ``canonical_digest(("isotopic-layer-v1", configuration, features.isotopic_digest or ""))`` -- so
          ISOTOPIC-equal implies CONFIGURATION-equal, isotopologues are distinguished, AND the enantiomeric-isotopologue
          trap is closed: the bare ``isotopic_digest`` is chirality-blind, but folding it OVER the configuration digest
          keeps two enantiomeric isotopologues distinct (same isotopes, different configuration -> different ISOTOPIC).
        """
        from .category import Molecule
        from .compilation_ir import _structure_ident
        from .decompiler import Formula
        if type(molecule) is not Molecule:
            raise TypeError("of_molecule needs a smartchem.category.Molecule")
        formula = Formula.of(dict(molecule.formula), molecule.charge)  # counts + TOTAL CHARGE (section 5.1)
        constitution = _structure_ident(molecule)
        by_layer = {
            MatchLayer.FORMULA.value: canonical_digest(formula),
            MatchLayer.CONSTITUTION.value: constitution,
        }
        known = MatchLayer.CONSTITUTION
        if features is not None:
            from .smiles import SmilesFeatures
            if type(features) is not SmilesFeatures:
                raise TypeError("features must be a smartchem.smiles.SmilesFeatures or None")
            if features.configuration_complete:
                configuration = canonical_digest(
                    ("configuration-layer-v1", constitution, features.configuration_digest or "")
                )
                by_layer[MatchLayer.CONFIGURATION.value] = configuration
                isotopic = canonical_digest(
                    ("isotopic-layer-v1", configuration, features.isotopic_digest or "")
                )
                by_layer[MatchLayer.ISOTOPIC.value] = isotopic
                known = MatchLayer.ISOTOPIC
        return cls(
            LAYERED_IDENTITY_SCHEMA,
            known,
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


# -- ID-STEREO-01: finer-layer features a constitution-only parse DECLARES but cannot keep -----------------------
#
# The current Molecule model perceives constitution (atoms + bonds), so a SMILES that names a stereocenter, an
# isotope label, or an internal (net-neutral) charge separation collapses to the same graph as its flat analogue
# (an enantiomer, an isotopologue, a zwitterion all become the flat species).  That collapse is CORRECT at the
# CONSTITUTION layer, but section 5.3 forbids it being SILENT.  These constructors record the drop as a typed
# BLOCKER, so a downstream sourced claim that depends on the dropped feature cannot survive (checked via
# :func:`is_blocked` -- the EVD-KEY-01 consumer).  This is the standard's "record blocker" arm; it is NOT stereo/
# isotope PERCEPTION (a sound CONFIGURATION/ISOTOPIC digest needs canonical CIP / positioned-isotopologue keys and
# the atom-coloured Molecule extension), which stays deferred and named -- never faked here.


def stereo_loss(input_representation: str, *, double_bond: bool = False) -> IdentityLoss:
    """A section 5.3 BLOCKER for a stereochemical marker (``@``/``@@`` or ``/``/``\\``) the graph cannot keep.

    Two enantiomers, or two double-bond geometric isomers, share one constitution and so collapse to one
    ``Molecule``; a configuration-dependent sourced fact (a stereospecific rate, an enantiomer-specific hazard, a
    diastereoselective condition) must not attach to that flattened identity.
    """
    kind = "double-bond configuration (cis/trans)" if double_bond else "tetrahedral chirality (R/S)"
    marker = "'/'/'\\'" if double_bond else "'@'/'@@'"
    # NOT "hazard": the modeled hazard is a CONSTITUTION-level physical handling class (flammability, toxicity
    # flags) that two enantiomers share, so a dropped stereocentre does not change it -- listing it would
    # over-refuse a legitimate, gated handling claim.  Enantiomer-specific toxicology (thalidomide) is a
    # configuration-keyed hazard model this system does not have (deferred, not faked).
    return IdentityLoss(
        IDENTITY_LOSS_SCHEMA,
        "stereochemistry",
        input_representation,
        "constitution only (CONSTITUTION layer; stereochemistry not represented)",
        f"{kind} was declared ({marker}) but the constitution-only model does not represent it, so enantiomers / "
        f"geometric isomers collapse to one identity",
        ("conditions", "configuration-identity", "kinetics", "product-identity", "selectivity", "stereochemistry"),
        LossSeverity.BLOCKER,
    )


def isotope_loss(input_representation: str, isotopes: "tuple[int, ...]" = ()) -> IdentityLoss:
    """A section 5.3 BLOCKER for isotope labels (e.g. ``[13C]``, ``[2H]``) the graph cannot keep.

    Isotopologues share one constitution; a kinetic isotope effect or an isotope-tracer identity claim must not
    survive the collapse to the unlabelled graph.
    """
    seen = f" ({', '.join(str(m) for m in isotopes)})" if isotopes else ""
    return IdentityLoss(
        IDENTITY_LOSS_SCHEMA,
        "isotope-labeling",
        input_representation,
        "constitution only (CONSTITUTION layer; isotope labels not represented)",
        f"an isotope label{seen} was declared but the model does not represent isotopes, so isotopologues collapse "
        f"to one identity",
        ("isotope-identity", "kinetics", "product-identity"),
        LossSeverity.BLOCKER,
    )


def local_charge_loss(input_representation: str) -> IdentityLoss:
    """A section 5.3 BLOCKER for a per-atom (net-neutral) charge separation the scalar total cannot keep.

    A zwitterion / ylide (``[NH3+]CC(=O)[O-]``) is net neutral, so the one total-charge scalar the ``Molecule``
    keeps hides the internal ``+``/``-`` distribution; a protonation-state-dependent condition or product-identity
    claim must not attach to the flattened form.
    """
    return IdentityLoss(
        IDENTITY_LOSS_SCHEMA,
        "local-charge",
        input_representation,
        "constitution + total charge only (per-atom formal charge not represented)",
        "a per-atom formal-charge separation (a net-neutral zwitterion/ylide) was declared, but only the molecular "
        "total charge is represented, so the internal +/- distribution is not distinguished",
        ("conditions", "product-identity", "protonation-state"),
        LossSeverity.BLOCKER,
    )


def representation_losses_for(input_representation: str, features: "object") -> "tuple[IdentityLoss, ...]":
    """Map a :class:`~smartchem.smiles.SmilesFeatures` to the typed section-5.3 losses it implies (ID-STEREO-01).

    Only features actually PRESENT produce a loss (a flat, unlabelled, neutral molecule yields ``()``), so this is
    never a vacuous blanket blocker.  Tetrahedral and double-bond stereo collapse to one ``stereo_loss`` per kind
    present; isotopes and net-neutral local charge each produce their own.  Digest order is imposed by the IR, not
    here.
    """
    from .smiles import SmilesFeatures
    if type(features) is not SmilesFeatures:
        raise TypeError("representation_losses_for needs a smartchem.smiles.SmilesFeatures")
    losses: list[IdentityLoss] = []
    if features.tetrahedral_stereo:
        losses.append(stereo_loss(input_representation, double_bond=False))
    if features.double_bond_stereo:
        losses.append(stereo_loss(input_representation, double_bond=True))
    if features.has_isotope:
        losses.append(isotope_loss(input_representation, features.isotopes))
    if features.has_local_charge_structure:
        losses.append(local_charge_loss(input_representation))
    return tuple(losses)


# -- EVD-KEY-01 (consumer half): a sourced claim MUST NOT survive a BLOCKER for its class (section 5.3) ----------


def blocking_losses(losses: "tuple[IdentityLoss, ...]", claim: str) -> "tuple[IdentityLoss, ...]":
    """The losses in ``losses`` that BLOCK ``claim`` (severity BLOCKER and ``claim`` in ``affected_claims``)."""
    if type(losses) is not tuple or any(type(x) is not IdentityLoss for x in losses):
        raise TypeError("blocking_losses needs a tuple of IdentityLoss records")
    if not isinstance(claim, str) or not claim:
        raise ValueError("claim must be a non-empty string")
    return tuple(loss for loss in losses if loss.blocks(claim))


def is_blocked(losses: "tuple[IdentityLoss, ...]", claim: str) -> bool:
    """Whether any loss in ``losses`` is a BLOCKER for ``claim`` -- the consumer's section-5.3 gate."""
    return bool(blocking_losses(losses, claim))


def blocked_claim_classes(losses: "tuple[IdentityLoss, ...]") -> "tuple[str, ...]":
    """The sorted union of every claim class any BLOCKER loss in ``losses`` forbids."""
    if type(losses) is not tuple or any(type(x) is not IdentityLoss for x in losses):
        raise TypeError("blocked_claim_classes needs a tuple of IdentityLoss records")
    classes: set[str] = set()
    for loss in losses:
        if loss.severity is LossSeverity.BLOCKER:
            classes.update(loss.affected_claims)
    return tuple(sorted(classes))
