"""STOCK-01 (first brick) -- StockMaterial: a real bottle, which is NOT the same as a pure identity.

The prime material-honesty rule of the standard (section 10): a chemical IDENTITY match is not a MATERIAL claim.
"Vinegar contains acetic acid" is true; "this bottle of vinegar is a suitable pure-acetic-acid feedstock" is
false -- household vinegar is only a few percent acetic acid in water.  A ``CommodityReagent``
(:mod:`smartchem.data.reagents`) is a source LEAD (an identity that MAY occur in an accessible source); a
``StockMaterial`` is a typed material with components, a phase, and an ASSAY interval, and it REFUSES to satisfy a
pure-reagent requirement it cannot prove it meets.

This first brick implements the core falsifier (section 10.2): a dilute mixture cannot satisfy a pure input
without a proven assay -- the honest verdicts are ``INSUFFICIENT_ASSAY`` (even the best case falls short, so
preprocessing is required) and ``UNKNOWN_ASSAY`` (the interval straddles the requirement, so a measurement is
required), never a silent pass.  Components are keyed on the RESONANCE-canonical structure (:func:`structure_key`,
ID-LAYER-01) or on a declared NAME (:func:`normalize_material_name`); this module is the ONE owner of both keys.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from typing import TYPE_CHECKING

from ..category import Molecule
from ..contracts import Digestible
from ..material_spec import ConcentrationBasis, EvidenceKind

if TYPE_CHECKING:
    from ..data.derived_evidence import IntervalEvidence
    from ..material_spec import PhaseClaim, StateClaim, StockSpecView

__all__ = [
    "STOCK_MATERIAL_SCHEMA",
    "MATERIAL_COMPONENT_SCHEMA",
    "STOCK_QUANTITY_SCHEMA",
    "COST_OBSERVATION_SCHEMA",
    "Phase",
    "FitnessVerdict",
    "MaterialComponent",
    "StockQuantity",
    "CostObservation",
    "StockMaterial",
    "stock_material_from_commodity",
    "structure_key",
    "is_structure_key",
    "normalize_material_name",
]

#: Round V (barrier D8/D11): component v1alpha2 adds ``MaterialComponent.basis``/``.evidence``/``.states`` (Wave-C
#: K1 moved state claims from the bottle onto the component). Round V X-high (D18/D22): stock-material v1alpha3 adds
#: ``StockMaterial.phase_evidence`` -- the bottle phase is no longer an ungraded scalar. Older ids are NOT
#: constructible: no v0.8 payload ever carried a StockMaterial (the capability profile is new in 0.9), and a WIP-only
#: 0.9 id was never released, so there is nothing to migrate -- a stale record would silently mean "phase evidence
#: absent" under a new identity. Every in-repo constructor passes the schema CONSTANT, so the bump is transparent.
#: 0.9.5 (barrier S7): component v1alpha3 -- ``identity_key`` now means the RESONANCE-canonical structure key
#: (:func:`structure_key`), a strict coarsening of the literal-bond-order key; 0 parse-origin keys move, but the
#: meaning did, so the id says so. 0.9.5 (barrier S9): stock-material v1alpha4 -- a stock-side state/phase claim
#: may no longer carry a SOURCED evidence kind (the accepted set only narrows; 0 existing uses). Pre-release ids
#: are not migrated (S14): a 0.9.0a1 alpha is refused, never reinterpreted.
STOCK_MATERIAL_SCHEMA = "smartchem.experiment/stock-material-v1alpha4"
MATERIAL_COMPONENT_SCHEMA = "smartchem.experiment/material-component-v1alpha3"
STOCK_QUANTITY_SCHEMA = "smartchem.experiment/stock-quantity-v1alpha1"
COST_OBSERVATION_SCHEMA = "smartchem.experiment/cost-observation-v1alpha2"


def _exact_positive(value: str, what: str) -> Fraction:
    """Parse ``value`` through the ONE strict exact grammar (:func:`smartchem.material_spec.exact_fraction`) and
    require it strictly positive -- no float, no epsilon, no ``'1/3'``/``'1_000'``/``' 5 '``/NaN/inf (barrier D1)."""
    from ..material_spec import exact_fraction
    v = exact_fraction(value, what)
    if v <= 0:
        raise ValueError(f"{what} must be a strictly positive quantity")
    return v


#: Bases whose values are fractions bounded by 1 (UNKNOWN included: an unknown basis claims nothing larger).
_FRACTION_BASES = frozenset({ConcentrationBasis.MASS_FRACTION, ConcentrationBasis.VOLUME_FRACTION,
                             ConcentrationBasis.UNKNOWN})


def _exact_float(x: float) -> Fraction:
    """A component fraction float read EXACTLY through its shortest repr (never binary-float arithmetic)."""
    return Fraction(repr(float(x)))


class Phase(str, Enum):
    SOLID = "SOLID"
    LIQUID = "LIQUID"
    GAS = "GAS"
    AQUEOUS_SOLUTION = "AQUEOUS_SOLUTION"
    UNKNOWN = "UNKNOWN"


class FitnessVerdict(str, Enum):
    """Whether a :class:`StockMaterial` satisfies a required pure-identity assay -- never a silent yes."""

    SATISFIES = "SATISFIES"                     # the WORST-case active fraction already meets the requirement
    INSUFFICIENT_ASSAY = "INSUFFICIENT_ASSAY"   # even the BEST case falls short -> preprocessing required
    UNKNOWN_ASSAY = "UNKNOWN_ASSAY"             # the interval straddles the requirement / is unknown -> measure
    IDENTITY_ABSENT = "IDENTITY_ABSENT"         # the material does not contain the required identity at all


def normalize_material_name(name: str) -> str:
    """THE material-name normaliser (barrier S8): strip, casefold, and collapse every internal whitespace run to one
    space. Stock NAME keys, the requirement projection and waste derivation all fold names through THIS function --
    whitespace folding is spelling, not synonymy ("sodium  bicarbonate" is "sodium bicarbonate"; "baking soda" is
    still not). There is no synonym knowledge here and there must not be: the declared world's keys stay closed."""
    # Three modules used to carry three private folds, and stock's (strip + casefold only) disagreed with the other
    # two on a double space -- enough to BLOCK a bottle that was sitting right there. One fold now; the copies are out.
    return " ".join(name.strip().casefold().split())


_STRUCT_PREFIX = "struct:"
_STRUCT_ASGIVEN = "struct-asgiven:"
_ASGIVEN = "asgiven:"  # resonance_identity's own sentinel for a graph the canonicaliser refuses


@lru_cache(maxsize=8192)
def _structure_key(molecule: Molecule) -> str:
    """The implementation behind :func:`structure_key` (memoised on the hashable Molecule). Kept as a module global
    on purpose: :func:`structure_key` resolves it by NAME at call time, so a test/mutation patch of
    ``stock._structure_key`` reaches every consumer, requirement and waste side included."""
    from ..smiles import resonance_identity  # lazy: smiles pulls the data package, which imports this module

    ident = resonance_identity(molecule)
    if ident.startswith(_ASGIVEN):
        # byte-identical to the pre-0.9.5 literal fallback: resonance_identity's "asgiven:" + canonical_digest(m)
        return _STRUCT_ASGIVEN + ident[len(_ASGIVEN):]
    return _STRUCT_PREFIX + ident


def structure_key(molecule: Molecule) -> str:
    """The ONE material STRUCTURE key (barrier S7): ``"struct:" + resonance_identity(molecule)`` -- keyed on
    structure, not a fragile name (ID-LAYER-01). Every consumer (stock components and lookups, the requirement
    projection, waste derivation, ``name_resolves_to``, the assess name-only test) imports THIS function; no other
    module may compute a structure digest of its own.

    The ``struct:`` namespace keeps a structure key and a human-declared NAME key from ever colliding inside
    ``identity_key``. Keying on structure is what makes fitness SOUND against the "keyed by formula fails open"
    hazard: a same-formula CONSTITUTIONAL isomer (ethanol vs dimethyl ether; o-/m-/p-xylene) has a DIFFERENT key, so
    one can never borrow the other's assay.

    RESONANCE invariance: the key is ``resonance_identity(molecule)`` (:mod:`smartchem.smiles`), which re-distributes
    bond orders over the fixed sigma skeleton + per-atom pi-demand and takes the minimum, so ANY Kekule placement of
    one molecule -- SMILES-parsed OR built by graph surgery (an ortho-disubstituted salicylate fragment cut from
    aspirin) -- shares one key. The class is CONSTITUTION-level. It does NOT perceive stereo (R/S, cis/trans share a
    key), isotopes (H2O and D2O share a key), tautomers (distinct keys, by design), per-atom charge location (a
    Molecule carries one global charge), or multi-fragment salts (a Molecule is one connected species; salts are
    NAME-keyed). Molecules above the resonance caps (>64 heavy atoms or >128 placements) fall back to the literal
    canonical digest and may not unify across Kekule spellings; a graph the canonicaliser refuses keys as
    ``struct-asgiven:`` + its as-given digest. The soundness guarantee is therefore: a same-formula CONSTITUTIONAL
    isomer never borrows -- NOT every isomer.
    """
    # Deliberately a thin module-global lookup rather than the cached function itself: M3 patches
    # ``stock._structure_key`` by name, and a patient that ignores the anaesthetic is not a controlled experiment.
    return _structure_key(molecule)


def is_structure_key(identity_key: str) -> bool:
    """Does ``identity_key`` live in the STRUCTURE namespace (``struct:`` / ``struct-asgiven:``)? Every other
    ``identity_key`` is a declared NAME. The one predicate -- assess no longer keeps its own prefix tuple."""
    return identity_key.startswith(_STRUCT_PREFIX) or identity_key.startswith(_STRUCT_ASGIVEN)


#: Barrier S9 (B-narrow): the evidence kinds a stock-side STATE or PHASE claim may NOT carry. Each names a source
#: record (a quote, a kernel derivation, a clamp) and a stock state/phase slot has nowhere to attach one -- the
#: claim is the operator's own declaration. Stock ``IntervalEvidence`` is unaffected: it carries structural locators.
_STOCK_CLAIM_REFUSED_EVIDENCE = frozenset({EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.CLAMPED})
_STOCK_CLAIM_REFUSAL = (
    "a stock-side state/phase claim is the operator's declaration: use USER_DECLARED (or ASSUMED/UNKNOWN); a sourced "
    "kind needs a structurally attached source record, which stock claims do not carry")


@dataclass(frozen=True)
class MaterialComponent(Digestible):
    """One declared component of a material: its identity key, role, and a fraction INTERVAL ``[lo, hi]``.

    An unknown fraction is the honest full interval ``[0.0, 1.0]``, never a point guess.  ``identity_key`` is either
    the resonance-canonical STRUCTURE key (:func:`structure_key`, ``struct:`` namespace) or a declared NAME (matched
    through :func:`normalize_material_name`).
    """

    schema_version: str
    identity_key: str
    role: str
    min_fraction: float
    max_fraction: float
    #: Round V (barrier D4/D8): what the fraction interval MEANS. ``UNKNOWN`` (the default) is honest for every
    #: legacy component that never said whether it was mass, volume or mole based -- and an unknown basis can never
    #: certify a composition requirement (F68).
    basis: "ConcentrationBasis" = None  # type: ignore[assignment]  # defaulted to UNKNOWN in __post_init__
    #: Round V (barrier D7/D8): the typed, re-computable evidence behind ``[min_fraction, max_fraction]``. ``None``
    #: means UNKNOWN strength (the interval is carried but nothing certifies it). When present, its endpoints must
    #: EQUAL the fraction slots exactly and its basis must equal ``basis`` -- the number IS the evidence's number.
    evidence: "IntervalEvidence | None" = None
    #: Round V Wave-C K1: positively-declared states OF THIS SPECIES in this material (NEAT / ANHYDROUS / SATURATED
    #: ...), each with its evidence strength. Scoped to the COMPONENT on purpose: a bottle-level "NEAT" claim on an
    #: acetone bottle must never certify the trace acetic acid inside it. Empty = nothing declared -> UNKNOWN.
    states: "tuple[StateClaim, ...]" = ()

    def __post_init__(self) -> None:
        from ..data.derived_evidence import IntervalEvidence
        from ..material_spec import ConcentrationBasis, StateClaim
        if self.basis is None:
            object.__setattr__(self, "basis", ConcentrationBasis.UNKNOWN)
        if type(self.basis) is not ConcentrationBasis:
            raise TypeError("basis must be a smartchem.material_spec.ConcentrationBasis")
        if self.schema_version != MATERIAL_COMPONENT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {MATERIAL_COMPONENT_SCHEMA!r}")
        for name in ("identity_key", "role"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        # Wave-C K3: only a FRACTION (or UNKNOWN) basis is bounded by 1 -- a MOLAR or w/v concentration is a
        # non-negative magnitude (6 M NaOH must be expressible, and must never be squeezed to 1).
        bounded = self.basis in _FRACTION_BASES
        for name in ("min_fraction", "max_fraction"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) or float(v) < 0.0:
                raise ValueError(f"{name} must be a finite, non-negative number")
            if bounded and float(v) > 1.0:
                raise ValueError(f"{name} must be a fraction in [0, 1] on a {self.basis.value} basis")
        if type(self.states) is not tuple or any(type(c) is not StateClaim for c in self.states):
            raise TypeError("states must be a tuple of smartchem.material_spec.StateClaim")
        if len({type(c.state) for c in self.states}) != len(self.states):
            raise ValueError("states may carry at most ONE claim per state family")
        for claim in self.states:  # barrier S9 (B-narrow): no sourced label without a source to attach it to
            if claim.evidence in _STOCK_CLAIM_REFUSED_EVIDENCE:
                raise ValueError(f"component state {claim.state.value} carries {claim.evidence.value}: "
                                 f"{_STOCK_CLAIM_REFUSAL}")
        if self.min_fraction > self.max_fraction:
            raise ValueError("min_fraction cannot exceed max_fraction")
        if self.evidence is not None:
            if type(self.evidence) is not IntervalEvidence:
                raise TypeError("evidence must be a smartchem.data.derived_evidence.IntervalEvidence or None")
            if (_exact_float(self.min_fraction), _exact_float(self.max_fraction)) != self.evidence.interval:
                raise ValueError(
                    f"evidence interval [{self.evidence.low}, {self.evidence.high}] does not equal the component's "
                    f"[{self.min_fraction!r}, {self.max_fraction!r}] -- the carried number must BE the evidence's")
            if self.evidence.basis is not self.basis:
                raise ValueError(
                    f"evidence basis {self.evidence.basis.value} does not equal component basis {self.basis.value}")

    @classmethod
    def evidenced(
        cls, identity: "Molecule | str", role: str, evidence: "IntervalEvidence",
        states: "tuple[StateClaim, ...]" = (),
    ) -> "MaterialComponent":
        """A component whose interval AND basis are taken from a typed :class:`IntervalEvidence` record (the Round V
        way to build a curated component). ``identity`` is a Molecule (structure key) or a declared NAME."""
        if isinstance(identity, Molecule):
            key = structure_key(identity)
        elif isinstance(identity, str):
            if is_structure_key(identity):
                raise ValueError("a declared NAME key must not use the reserved structure-key prefix")
            key = identity
        else:
            raise TypeError("identity must be a Molecule or a declared-name str")
        lo, hi = evidence.as_floats()
        return cls(MATERIAL_COMPONENT_SCHEMA, key, role, lo, hi, evidence.basis, evidence, tuple(states))

    @classmethod
    def known(cls, identity_key: str, role: str, min_fraction: float, max_fraction: float) -> "MaterialComponent":
        """A component identified by declared NAME -- the weaker human-declaration key (prefer :meth:`of_molecule`).

        A name is what a person can write off a label; it is honest but weaker than a structure (synonyms do not
        match, and it cannot be checked against a route's Molecule).  For a component whose structure is known,
        :meth:`of_molecule` keys on the canonical structure instead -- the sound, isomer-proof key.
        """
        if isinstance(identity_key, str) and is_structure_key(identity_key):
            raise ValueError("a declared NAME key must not use the reserved structure-key prefix")
        return cls(MATERIAL_COMPONENT_SCHEMA, identity_key, role, float(min_fraction), float(max_fraction))

    @classmethod
    def unknown_fraction(cls, identity_key: str, role: str) -> "MaterialComponent":
        """A NAME-identified component known PRESENT but of unknown fraction -- the honest full interval [0, 1]."""
        if isinstance(identity_key, str) and is_structure_key(identity_key):
            raise ValueError("a declared NAME key must not use the reserved structure-key prefix")
        return cls(MATERIAL_COMPONENT_SCHEMA, identity_key, role, 0.0, 1.0)

    @classmethod
    def of_molecule(
        cls, molecule: Molecule, role: str, min_fraction: float, max_fraction: float
    ) -> "MaterialComponent":
        """A component identified by canonical STRUCTURE (ID-LAYER-01) -- the sound key.

        Robust across the molecule's NAME and, crucially, CONSTITUTIONAL-isomer-proof: a same-formula species of
        different connectivity has a different canonical digest, so it can never borrow this component's assay.  It
        is NOT proof against stereo/isotope isomers -- see :func:`structure_key` for the honest scope (a
        resonance-canonical structure key: every Kekule placement shares it; its stereo/isotope/tautomer/salt limits
        are stated there).
        This is the key a route/shopping Molecule is matched against; prefer it over :meth:`known` wherever the
        structure is in hand.
        """
        return cls(MATERIAL_COMPONENT_SCHEMA, structure_key(molecule), role, float(min_fraction), float(max_fraction))

    @classmethod
    def unknown_molecule(cls, molecule: Molecule, role: str) -> "MaterialComponent":
        """A STRUCTURE-identified component known PRESENT but of unknown fraction -- the honest full interval [0, 1]."""
        return cls(MATERIAL_COMPONENT_SCHEMA, structure_key(molecule), role, 0.0, 1.0)


@dataclass(frozen=True)
class StockQuantity(Digestible):
    """A declared physical amount of a material: an exact numeric-string ``value`` plus a ``unit``.

    Section 10.3 forbids inventing a quantity: the honest "no declared amount" is the ABSENCE of this value
    (``StockMaterial.quantity is None`` -> UNKNOWN), never an assumed one mole / one bottle.  ``value`` is kept
    as the exact source string (no float drift enters the identity); Round V (D1): it must match the ONE strict
    exact grammar (:func:`smartchem.material_spec.exact_fraction`) and be strictly positive -- ``'1/3'``,
    ``'1_000'``, ``' 5 '``, ``'nan'``, ``'inf'`` and ``'0'`` are refused. Read it with :meth:`exact`, never float().
    """

    schema_version: str
    value: str
    unit: str

    def __post_init__(self) -> None:
        if self.schema_version != STOCK_QUANTITY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {STOCK_QUANTITY_SCHEMA!r}")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("unit must be a non-empty string")
        if not isinstance(self.value, str):
            raise ValueError("value must be a numeric string")
        _exact_positive(self.value, "value")

    @classmethod
    def of(cls, value: "str | int", unit: str) -> "StockQuantity":
        """``value`` as an exact decimal string (or an int). A float is refused: its decimal spelling is not the
        source's (``StockQuantity.of(0.1, ...)`` would silently mean whatever ``str(0.1)`` prints)."""
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise TypeError("StockQuantity.of takes an exact decimal string or an int, never a float")
        return cls(STOCK_QUANTITY_SCHEMA, str(value), unit)

    def exact(self) -> Fraction:
        """The declared amount as an exact :class:`~fractions.Fraction` (the only sanctioned numeric read)."""
        return _exact_positive(self.value, "value")

    def render(self) -> str:
        return f"{self.value} {self.unit}"


@dataclass(frozen=True)
class CostObservation(Digestible):
    """A DATED, SOURCED price observation (section 10.4: prices MUST be dated and sourced; the compiler MUST NOT
    invent a price).

    There is deliberately no way to construct one without an amount, currency, unit, observation date, and source:
    an unpriced material carries ``cost_observation=None`` (UNKNOWN), never a guessed number.  ``region`` is the one
    optional field (an empty string means unspecified market).

    ``unit`` is the price DENOMINATOR (what one ``amount`` buys, e.g. ``"metric ton"``).  Section 9.2 requires the
    reported value's units to be retained -- a bare number is nonconformant -- so ``amount`` + ``currency`` + ``unit``
    together are the full price ("52.95 USD per metric ton"), never just a scalar with an implied basis.
    """

    schema_version: str
    amount: str
    currency: str
    unit: str
    observed_date: str
    source: str
    region: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != COST_OBSERVATION_SCHEMA:
            raise ValueError(f"schema_version must be exactly {COST_OBSERVATION_SCHEMA!r}")
        for name in ("amount", "currency", "unit", "observed_date", "source"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(
                    f"{name} must be a non-empty string -- a price observation must be dated and sourced "
                    "(section 10.4); an unpriced material uses cost_observation=None"
                )
        try:
            a = float(self.amount)
        except (TypeError, ValueError) as exc:
            raise ValueError("amount must be a numeric string") from exc
        if not math.isfinite(a) or a < 0:
            raise ValueError("amount must be a non-negative, finite number")
        if not isinstance(self.region, str):
            raise TypeError("region must be a string")

    @classmethod
    def of(
        cls, amount: "str | int | float", currency: str, unit: str, observed_date: str, source: str,
        region: str = "",
    ) -> "CostObservation":
        return cls(COST_OBSERVATION_SCHEMA, str(amount), currency, unit, observed_date, source, region)

    def render(self) -> str:
        where = f", {self.region}" if self.region else ""
        return (
            f"{self.amount} {self.currency}/{self.unit} (observed {self.observed_date}{where}; "
            f"source: {self.source})"
        )


@dataclass(frozen=True)
class StockMaterial(Digestible):
    """A real material: one or more components (each a fraction interval), a phase, and provenance.

    Unlike a pure identity or a commodity source lead, a ``StockMaterial`` can be ASKED whether it satisfies a
    pure-reagent requirement, and it answers honestly with an interval verdict (:meth:`satisfies`).

    Round V X-high (D18): ``phase`` is BOTTLE-level on purpose -- it describes the material you dispense (a brine is an
    aqueous solution whichever species you ask about), unlike the per-species material STATES, which stay scoped to
    their :class:`MaterialComponent` (Wave-C K1). ``phase_evidence`` grades it: the capability compiler reads ONLY
    :attr:`phase_claim` (phase + evidence), never the bare ``phase`` scalar, and an ungraded phase
    (``EvidenceKind.UNKNOWN``, the default) can neither certify nor refute a phase demand. ``phase`` itself stays for
    every legacy reader (render, commodity bridge).
    """

    schema_version: str
    material_id: str
    display_name: str
    components: tuple[MaterialComponent, ...]
    phase: Phase
    provenance: str
    # -- the rest of the section 10.2 schema; all keyword-optional so the first-brick positional form still
    # constructs, and every one defaults to an honest UNKNOWN (None / empty), never an assumed value.
    quantity: "StockQuantity | None" = None
    assay_method: "str | None" = None
    container_and_storage: "str | None" = None
    opened_or_age_state: "str | None" = None
    jurisdiction_and_availability: "str | None" = None
    cost_observation: "CostObservation | None" = None
    formulation_notes: tuple[str, ...] = ()
    known_impurities: tuple[str, ...] = field(default_factory=tuple)
    #: Round V X-high (D18): how strongly ``phase`` is established. UNKNOWN (the default) is the honest grade of every
    #: bottle nobody vouched for; the bench operator's own declaration is ``USER_DECLARED``. An unknown PHASE carries
    #: no evidence at all (there is nothing to grade), so ``Phase.UNKNOWN`` forces ``EvidenceKind.UNKNOWN``.
    phase_evidence: EvidenceKind = EvidenceKind.UNKNOWN

    def __post_init__(self) -> None:
        if self.schema_version != STOCK_MATERIAL_SCHEMA:
            raise ValueError(f"schema_version must be exactly {STOCK_MATERIAL_SCHEMA!r}")
        for name in ("material_id", "display_name", "provenance"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.phase, Phase):
            raise TypeError("phase must be a Phase")
        if type(self.phase_evidence) is not EvidenceKind:
            raise TypeError("phase_evidence must be a smartchem.material_spec.EvidenceKind")
        if self.phase_evidence in _STOCK_CLAIM_REFUSED_EVIDENCE:  # barrier S9 (B-narrow)
            raise ValueError(f"phase_evidence {self.phase_evidence.value}: {_STOCK_CLAIM_REFUSAL}")
        if self.phase is Phase.UNKNOWN and self.phase_evidence is not EvidenceKind.UNKNOWN:
            raise ValueError(
                f"phase UNKNOWN cannot carry {self.phase_evidence.value} evidence -- an unknown phase is not a claim")
        if type(self.components) is not tuple or not self.components or any(
            type(c) is not MaterialComponent for c in self.components
        ):
            raise TypeError("components must be a non-empty tuple of MaterialComponent values")
        if sum((_exact_float(c.min_fraction) for c in self.components if c.basis in _FRACTION_BASES),
               Fraction(0)) > 1:
            raise ValueError("component minimum fractions sum above 1.0 -- an infeasible material")
        # D25.2 (Wave-C'' NEW-2): the one basis-free PROVABLE contradiction. When the mass (or volume) fraction lower
        # bounds of the components keyed like a species already account for the WHOLE material, no OTHER species can
        # be present at a positive amount on ANY basis -- a 0.3 g/mL or 6 M second species beside an "acetic acid
        # [1, 1] w/w" component is a self-contradictory bottle, refused here so neither the pure witness nor the
        # composition path can ever read it. (No density engine, no threshold: only the exact "== 1" case is provable.)
        for basis in (ConcentrationBasis.MASS_FRACTION, ConcentrationBasis.VOLUME_FRACTION):
            for key in {c.identity_key for c in self.components if c.basis is basis}:
                whole = sum((_exact_float(c.min_fraction) for c in self.components
                             if c.basis is basis and c.identity_key == key), Fraction(0))
                if whole == 1 and any(c.identity_key != key and _exact_float(c.min_fraction) > 0
                                      for c in self.components):
                    raise ValueError(
                        f"component {key!r} accounts for the whole material ({basis.value} lower bound 1) while "
                        "another species declares a positive amount -- a self-contradictory bottle (D25.2)")
        # -- section 10.2 optional fields: each is a typed value or an honest UNKNOWN -----------------------
        if self.quantity is not None and type(self.quantity) is not StockQuantity:
            raise TypeError("quantity must be a StockQuantity or None (UNKNOWN)")
        if self.cost_observation is not None and type(self.cost_observation) is not CostObservation:
            raise TypeError("cost_observation must be a CostObservation or None (UNKNOWN)")
        for name in ("assay_method", "container_and_storage", "opened_or_age_state", "jurisdiction_and_availability"):
            v = getattr(self, name)
            if v is not None and (not isinstance(v, str) or not v.strip()):
                raise ValueError(f"{name} must be a non-empty string or None (UNKNOWN)")
        for name in ("formulation_notes", "known_impurities"):
            seq = getattr(self, name)
            if type(seq) is not tuple or any(not isinstance(x, str) or not x.strip() for x in seq):
                raise TypeError(f"{name} must be a tuple of non-empty strings")

    @property
    def phase_claim(self) -> "PhaseClaim | None":
        """Round V X-high (D18): the bottle's phase AS AN EVIDENCE-GRADED CLAIM -- the only phase surface the capability
        compiler may read (through :func:`smartchem.material_spec.compare_phase`). ``None`` iff the phase is UNKNOWN
        (an unknown phase is the absence of a claim); an ungraded known phase is a claim carrying
        ``EvidenceKind.UNKNOWN``, which certifies nothing either way."""
        from ..material_spec import PhaseClaim
        if self.phase is Phase.UNKNOWN:
            return None
        return PhaseClaim(self.phase, self.phase_evidence)

    def active_fraction_interval(self, required_identity: "Molecule | str") -> tuple[float, float] | None:
        """The summed fraction interval ``(lo, hi)`` of components matching ``required_identity``, or ``None``.

        ``required_identity`` may be a :class:`~smartchem.category.Molecule` -- matched by canonical STRUCTURE, the
        SOUND key (a same-formula CONSTITUTIONAL isomer never borrows another's assay; a name synonym still matches;
        stereoisomers share a key -- the blocked ID-STEREO layer) -- or a ``str`` name, matched by the weaker
        declared-name key.  A structure query matches ONLY structure-keyed
        components and a name query ONLY name-keyed components: a bare name can never stand in for a proven
        structure, nor a structure for a name.  Several components may share an identity (two additives of the same
        species); their intervals sum, capped at 1.0 on the high side.  ``None`` means the identity is not present.
        """
        if isinstance(required_identity, Molecule):
            want = structure_key(required_identity)
            matches = [c for c in self.components if c.identity_key == want]
        elif isinstance(required_identity, str):
            want = normalize_material_name(required_identity)
            matches = [
                c for c in self.components
                if not is_structure_key(c.identity_key) and normalize_material_name(c.identity_key) == want
            ]
        else:
            raise TypeError("required_identity must be a Molecule (canonical structure) or a str (declared name)")
        if not matches:
            return None
        lo = sum(c.min_fraction for c in matches)
        hi = sum(c.max_fraction for c in matches)
        if all(c.basis in _FRACTION_BASES for c in matches):  # Wave-C2: never clamp a MOLAR/w-v magnitude to 1
            hi = min(1.0, hi)
        return (lo, hi)

    def spec_view(self, required_identity: "Molecule | str") -> "StockSpecView | None":
        """Round V (barrier D3-D8): the stock-side facts :func:`smartchem.material_spec.compare_specification` needs
        for ONE species in THIS bottle -- the matched components' summed EXACT interval, their common basis (UNKNOWN
        if they disagree or any is UNKNOWN), the WEAKEST interval-evidence kind among them (a component with no
        evidence record is UNKNOWN strength), and the matched components' own declared states (Wave-C K1). ``None`` if the
        species is absent
        under the F44 key rules of :meth:`active_fraction_interval`."""
        from ..material_spec import (
            CERTIFYING_STOCK_EVIDENCE,
            ConcentrationBasis,
            DilutionState,
            EvidenceKind,
            StockSpecView,
        )
        if isinstance(required_identity, Molecule):
            want = structure_key(required_identity)
            matches = [c for c in self.components if c.identity_key == want]
        elif isinstance(required_identity, str):
            want_n = normalize_material_name(required_identity)
            matches = [
                c for c in self.components
                if not is_structure_key(c.identity_key) and normalize_material_name(c.identity_key) == want_n
            ]
        else:
            raise TypeError("required_identity must be a Molecule (canonical structure) or a str (declared name)")
        if not matches:
            return None
        # exact: the float fractions are re-read through their shortest repr, never binary-float arithmetic
        # exact: a component WITH an evidence record contributes the record's exact decimal endpoints (never the
        # float slot -- Wave-C K2d: "0.99999999999999999" must not read as 1); otherwise the float's shortest repr.
        def _lo(c: "MaterialComponent") -> Fraction:
            return c.evidence.interval[0] if c.evidence is not None else _exact_float(c.min_fraction)

        def _hi(c: "MaterialComponent") -> Fraction:
            return c.evidence.interval[1] if c.evidence is not None else _exact_float(c.max_fraction)

        bases = {c.basis for c in matches}
        basis = bases.pop() if len(bases) == 1 else ConcentrationBasis.UNKNOWN
        lo = sum((_lo(c) for c in matches), Fraction(0))
        hi = sum((_hi(c) for c in matches), Fraction(0))
        if basis in _FRACTION_BASES:  # Wave-C K3: cap ONLY a fraction basis at 1; a MOLAR/w-v sum is a magnitude
            hi = min(Fraction(1), hi)
        order = [EvidenceKind.UNKNOWN, EvidenceKind.ASSUMED, EvidenceKind.AUTHOR_INFERRED, EvidenceKind.USER_DECLARED,
                 EvidenceKind.CLAMPED, EvidenceKind.DERIVED, EvidenceKind.SOURCE_QUOTED]
        kinds = []
        for c in matches:
            kinds.append(EvidenceKind.UNKNOWN if c.evidence is None else c.evidence.kind)
        weakest = min(kinds, key=order.index)
        # Wave-C K1: states are the MATCHED COMPONENTS' own claims -- never the bottle's. A family claimed differently
        # by two matched components is contradictory and is dropped (-> UNDETERMINED), never resolved by preference.
        by_family: "dict[type, list]" = {}
        for c in matches:
            for claim in c.states:
                by_family.setdefault(type(claim.state), []).append(claim)
        states = tuple(
            claims[0] for claims in by_family.values()
            if len({(cl.state, cl.evidence) for cl in claims}) == 1 and len(claims) == len(matches)
        )
        # D24.5 (Wave-C' C2): a NEAT ("undiluted") claim is contradicted by the bottle's OWN declaration of a positive
        # diluent -- ANY other component whose certified lower bound is > 0 (on any basis: 0.3 g/mL NaCl beside
        # "neat" water is as much a diluent as 50 % w/w water beside "neat" acid). The contradicted claim is DROPPED,
        # so the comparison reads UNDETERMINED (never resolved by preference). No numeric purity threshold is
        # introduced: an impurity declared with lower bound 0 (commercial glacial acid, water 0-0.3 %) keeps NEAT.
        matched_ids = {id(c) for c in matches}
        diluted = any(
            c.evidence is not None and c.evidence.kind in CERTIFYING_STOCK_EVIDENCE and c.evidence.interval[0] > 0
            for c in self.components if id(c) not in matched_ids
        )
        if diluted:
            states = tuple(claim for claim in states if claim.state is not DilutionState.NEAT)
        return StockSpecView((lo, hi), basis, weakest, states)

    def satisfies(self, required_identity: "Molecule | str", *, min_assay: float) -> FitnessVerdict:
        """Whether this material meets a ``min_assay`` (mass/mole fraction) requirement for ``required_identity``.

        Rigorous interval logic, never a silent yes: the material SATISFIES only if its worst-case (lower-bound)
        active fraction already clears ``min_assay``; it is ``INSUFFICIENT_ASSAY`` (preprocessing required) only
        if even its best case (upper bound) falls short; and anywhere the interval straddles the requirement -- or
        the fraction is unknown -- it is ``UNKNOWN_ASSAY`` (a measurement is required), because assuming the
        favourable end of an interval is exactly the identity-is-purity error section 10 forbids.

        LEGACY helper (Round V): it compares numbers only -- no basis, no evidence strength. The capability compiler
        no longer uses it; material specifications go through :meth:`spec_view` +
        :func:`smartchem.material_spec.compare_specification`.
        """
        if isinstance(min_assay, bool) or not isinstance(min_assay, (int, float)) or not (0.0 < float(min_assay) <= 1.0):
            raise ValueError("min_assay must be a fraction in (0, 1]")
        interval = self.active_fraction_interval(required_identity)
        if interval is None:
            return FitnessVerdict.IDENTITY_ABSENT
        lo, hi = interval
        if lo >= min_assay:
            return FitnessVerdict.SATISFIES
        if hi < min_assay:
            return FitnessVerdict.INSUFFICIENT_ASSAY
        return FitnessVerdict.UNKNOWN_ASSAY

    def satisfies_band(
        self, required_identity: "Molecule | str", *, low: float, high: float
    ) -> FitnessVerdict:
        """Round-IV F43: whether this material's active fraction of ``required_identity`` is PROVABLY within
        a TWO-SIDED composition band ``[low, high]`` -- the generalisation of :meth:`satisfies` a formulated
        wash needs. ``satisfies`` checks a one-sided assay FLOOR (``fraction >= min_assay``), which is right
        for a pure reagent ("glacial acetic acid, >=99%" == band ``[0.99, 1.0]``) but WRONG for a formulated
        wash: 100% sodium bicarbonate is not a "5% NaHCO3 wash", and a floor-only check would wave it through.
        A required band carries a real CEILING, so an over-concentrated (or under-concentrated) stock BLOCKS.

        Same rigorous interval logic as :meth:`satisfies`, never a silent yes: SATISFIES only if the WHOLE
        stock interval sits inside the band (``low <= s.lo`` and ``s.hi <= high``); ``INSUFFICIENT_ASSAY``
        (provably outside -> preprocessing/a different bottle) only if the stock interval is DISJOINT from the
        band (``s.hi < low`` or ``s.lo > high``); anywhere the interval straddles a band edge -- or the
        fraction is unknown -- it is ``UNKNOWN_ASSAY`` (measure it), because assuming the favourable end of a
        straddling interval is exactly the identity-is-purity error section 10 forbids.

        LEGACY helper (Round V): numbers only, no basis/evidence strength; the capability compiler uses
        :meth:`spec_view` + :func:`smartchem.material_spec.compare_specification` instead.
        """
        for name, value in (("low", low), ("high", high)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
                raise ValueError(f"{name} must be a fraction in [0, 1]")
        if float(low) > float(high):
            raise ValueError("low cannot exceed high")
        interval = self.active_fraction_interval(required_identity)
        if interval is None:
            return FitnessVerdict.IDENTITY_ABSENT
        s_lo, s_hi = interval
        if s_lo >= float(low) and s_hi <= float(high):
            return FitnessVerdict.SATISFIES
        if s_hi < float(low) or s_lo > float(high):
            return FitnessVerdict.INSUFFICIENT_ASSAY
        return FitnessVerdict.UNKNOWN_ASSAY

    def render(self) -> str:
        comps = "; ".join(
            f"{c.identity_key} ({c.role}) {c.min_fraction * 100:.0f}-{c.max_fraction * 100:.0f}%"
            for c in self.components
        )
        detail = [
            f"quantity: {self.quantity.render() if self.quantity else 'UNKNOWN'}",
            f"assay method: {self.assay_method or 'UNKNOWN'}",
            f"container/storage: {self.container_and_storage or 'UNKNOWN'}",
            f"opened/age: {self.opened_or_age_state or 'UNKNOWN'}",
            f"jurisdiction/availability: {self.jurisdiction_and_availability or 'UNKNOWN'}",
            f"cost: {self.cost_observation.render() if self.cost_observation else 'UNKNOWN'}",
        ]
        if self.known_impurities:
            detail.append("known impurities: " + ", ".join(self.known_impurities))
        if self.formulation_notes:
            detail.append("formulation: " + "; ".join(self.formulation_notes))
        return (
            f"STOCK MATERIAL {self.display_name!r} [{self.phase.value}; phase evidence {self.phase_evidence.value}] "
            f"-- {comps}. "
            f"Source: {self.provenance}. " + " | ".join(detail) + ". "
            "A material, not a pure identity: assay is an interval, and a pure-reagent requirement is met only "
            "when the interval PROVES it (section 10). Unknown fields are UNKNOWN, never an assumed value."
        )


def stock_material_from_commodity(commodity: "object") -> StockMaterial:
    """Bridge a :class:`~smartchem.data.reagents.CommodityReagent` (a SOURCE LEAD) to an UNKNOWN-assay material.

    Section 10.1: a commodity record states an identity MAY occur in a type of accessible source; it is NOT
    evidence that an arbitrary retail material has a suitable assay, purity, phase, or grade, and it MUST NOT
    silently satisfy a :class:`StockMaterial` requirement.  This bridge enforces exactly that: the commodity's
    identity becomes a single component of UNKNOWN fraction ``[0, 1]`` in a phase-``UNKNOWN`` material, so
    :meth:`StockMaterial.satisfies` can never return ``SATISFIES`` for it -- a pure-reagent query gets the honest
    ``UNKNOWN_ASSAY`` ("measure it") rather than a fabricated pass.  The everyday-source note and availability
    tier ride along as provenance/formulation, explicitly labelled a curated editorial judgment, not an assay.
    """
    from ..data.reagents import CommodityReagent
    if type(commodity) is not CommodityReagent:
        raise TypeError("stock_material_from_commodity needs a smartchem.data.reagents.CommodityReagent")
    # COST-VEC-01: attach a dated, SOURCED bulk price where one exists (lazy import breaks the stock<->pricing cycle;
    # commodity_pricing already keys on the canonical structure via commodity_for, so no same-formula isomer borrows a
    # price).  An unpriced commodity keeps cost_observation=None -- honest UNKNOWN, never a fabricated number (10.4).
    from .commodity_pricing import cost_observation_for
    cost = cost_observation_for(commodity.molecule)
    # keyed by canonical STRUCTURE (ID-LAYER-01), not the commodity NAME: this is the LIVE default-data path, so a
    # commodity material is matched against a route/shopping Molecule the sound way -- and never satisfies a query
    # for a same-formula isomer.  The human name still rides along as the display name and provenance.
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        f"commodity-lead:{commodity.name}",
        commodity.name,
        (MaterialComponent.unknown_molecule(commodity.molecule, "active"),),
        Phase.UNKNOWN,
        (
            f"commodity source lead: {commodity.name!r} (commonly found in {commodity.common_source}); "
            f"availability {commodity.availability.value!r} is a curated editorial obtainability judgment, not an "
            "assay -- a SOURCE LEAD, not a proven material (section 10.1). Assay, purity, phase and grade are UNKNOWN."
        ),
        cost_observation=cost,
        formulation_notes=(f"everyday source: {commodity.common_source}",),
    )
