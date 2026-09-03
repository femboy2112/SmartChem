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
required), never a silent pass.  The full section 10.2 schema (quantity, container, cost, jurisdiction, impurity
profile) and canonical-structure component keying (ID-LAYER-01) are later bricks, named as such.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..category import Molecule
from ..contracts import Digestible, canonical_digest

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
]

STOCK_MATERIAL_SCHEMA = "smartchem.experiment/stock-material-v1alpha1"
MATERIAL_COMPONENT_SCHEMA = "smartchem.experiment/material-component-v1alpha1"
STOCK_QUANTITY_SCHEMA = "smartchem.experiment/stock-quantity-v1alpha1"
COST_OBSERVATION_SCHEMA = "smartchem.experiment/cost-observation-v1alpha1"

_FRACTION_EPS = 1e-9


def _positive_numeric(value: str, what: str) -> float:
    """Parse ``value`` as a finite, strictly-positive number, or raise -- no NaN/inf/zero quantity."""
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{what} must be a numeric string") from exc
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{what} must be a positive, finite quantity")
    return v


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


def _norm(identity: str) -> str:
    return identity.strip().casefold()


_STRUCT_PREFIX = "struct:"
_STRUCT_ASGIVEN = "struct-asgiven:"


def _structure_key(molecule: Molecule) -> str:
    """The canonical STRUCTURE digest of ``molecule`` -- keyed on structure, not a fragile name (ID-LAYER-01).

    This is the same canonical identity routes and shopping key on (``canonical_digest(m.canonical())``, with the
    as-given fallback for a molecule that cannot canonicalise), namespaced with a ``struct:`` prefix so a
    structure key and a human-declared NAME key can never collide inside ``identity_key``.  Keying on structure is
    what makes fitness SOUND against the "keyed by formula fails open" hazard: a same-formula CONSTITUTIONAL isomer
    (ethanol vs dimethyl ether, both C2H6O) has a DIFFERENT digest, so one can never borrow the other's assay.

    Scope, stated honestly -- this key inherits the canonicalizer's guarantees AND its current limitations:
      * CONSTITUTIONAL only: the digest is the molecular graph, so it is STEREO-BLIND (R/S, cis/trans share a key)
        and ISOTOPE-BLIND (H2O and D2O share a key).  Distinguishing configuration needs real CIP R/S-parity (the
        BLOCKED ID-STEREO layer) and isotopes an isotope-aware digest; this key never claims to do either.  So the
        soundness guarantee is: a same-formula CONSTITUTIONAL isomer never borrows -- NOT every isomer.
      * RESONANCE non-invariance: ``canonical()`` normalises an AROMATIC spelling and simple rings (benzene) to one
        Kekule form, but does NOT yet normalise an EXPLICIT-Kekule spelling of a FUSED aromatic (naphthalene,
        indole, ...): the aromatic and explicit-Kekule spellings of the SAME such molecule get DIFFERENT digests, so
        a material can fail to satisfy its OWN identity written the other way (a fails-CLOSED false negative).  This
        is a canonicalizer limitation (tracked ``CANON-KEKULE-01``), pinned as an xfail, NOT faked here.
    """
    try:
        return _STRUCT_PREFIX + canonical_digest(molecule.canonical())
    except NotImplementedError:
        return _STRUCT_ASGIVEN + canonical_digest(molecule)


def _is_structure_key(identity_key: str) -> bool:
    return identity_key.startswith(_STRUCT_PREFIX) or identity_key.startswith(_STRUCT_ASGIVEN)


@dataclass(frozen=True)
class MaterialComponent(Digestible):
    """One declared component of a material: its identity key, role, and a fraction INTERVAL ``[lo, hi]``.

    An unknown fraction is the honest full interval ``[0.0, 1.0]``, never a point guess.  ``identity_key`` is a
    normalized name/formula string in this first brick; canonical-structure keying is ID-LAYER-01.
    """

    schema_version: str
    identity_key: str
    role: str
    min_fraction: float
    max_fraction: float

    def __post_init__(self) -> None:
        if self.schema_version != MATERIAL_COMPONENT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {MATERIAL_COMPONENT_SCHEMA!r}")
        for name in ("identity_key", "role"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("min_fraction", "max_fraction"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
                raise ValueError(f"{name} must be a fraction in [0, 1]")
        if self.min_fraction > self.max_fraction:
            raise ValueError("min_fraction cannot exceed max_fraction")

    @classmethod
    def known(cls, identity_key: str, role: str, min_fraction: float, max_fraction: float) -> "MaterialComponent":
        """A component identified by declared NAME -- the weaker human-declaration key (prefer :meth:`of_molecule`).

        A name is what a person can write off a label; it is honest but weaker than a structure (synonyms do not
        match, and it cannot be checked against a route's Molecule).  For a component whose structure is known,
        :meth:`of_molecule` keys on the canonical structure instead -- the sound, isomer-proof key.
        """
        if isinstance(identity_key, str) and _is_structure_key(identity_key):
            raise ValueError("a declared NAME key must not use the reserved structure-key prefix")
        return cls(MATERIAL_COMPONENT_SCHEMA, identity_key, role, float(min_fraction), float(max_fraction))

    @classmethod
    def unknown_fraction(cls, identity_key: str, role: str) -> "MaterialComponent":
        """A NAME-identified component known PRESENT but of unknown fraction -- the honest full interval [0, 1]."""
        if isinstance(identity_key, str) and _is_structure_key(identity_key):
            raise ValueError("a declared NAME key must not use the reserved structure-key prefix")
        return cls(MATERIAL_COMPONENT_SCHEMA, identity_key, role, 0.0, 1.0)

    @classmethod
    def of_molecule(
        cls, molecule: Molecule, role: str, min_fraction: float, max_fraction: float
    ) -> "MaterialComponent":
        """A component identified by canonical STRUCTURE (ID-LAYER-01) -- the sound key.

        Robust across the molecule's NAME and, crucially, CONSTITUTIONAL-isomer-proof: a same-formula species of
        different connectivity has a different canonical digest, so it can never borrow this component's assay.  It
        is NOT proof against stereo/isotope isomers or every SMILES spelling -- see :func:`_structure_key` for the
        honest scope (stereo/isotope-blind; explicit-Kekule fused aromatics not yet normalised, CANON-KEKULE-01).
        This is the key a route/shopping Molecule is matched against; prefer it over :meth:`known` wherever the
        structure is in hand.
        """
        return cls(MATERIAL_COMPONENT_SCHEMA, _structure_key(molecule), role, float(min_fraction), float(max_fraction))

    @classmethod
    def unknown_molecule(cls, molecule: Molecule, role: str) -> "MaterialComponent":
        """A STRUCTURE-identified component known PRESENT but of unknown fraction -- the honest full interval [0, 1]."""
        return cls(MATERIAL_COMPONENT_SCHEMA, _structure_key(molecule), role, 0.0, 1.0)


@dataclass(frozen=True)
class StockQuantity(Digestible):
    """A declared physical amount of a material: an exact numeric-string ``value`` plus a ``unit``.

    Section 10.3 forbids inventing a quantity: the honest "no declared amount" is the ABSENCE of this value
    (``StockMaterial.quantity is None`` -> UNKNOWN), never an assumed one mole / one bottle.  ``value`` is kept
    as the exact source string (no float drift enters the identity); it must parse as a positive finite number.
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
        _positive_numeric(self.value, "value")

    @classmethod
    def of(cls, value: "str | int | float", unit: str) -> "StockQuantity":
        return cls(STOCK_QUANTITY_SCHEMA, str(value), unit)

    def render(self) -> str:
        return f"{self.value} {self.unit}"


@dataclass(frozen=True)
class CostObservation(Digestible):
    """A DATED, SOURCED price observation (section 10.4: prices MUST be dated and sourced; the compiler MUST NOT
    invent a price).

    There is deliberately no way to construct one without an amount, currency, observation date, and source: an
    unpriced material carries ``cost_observation=None`` (UNKNOWN), never a guessed number.  ``region`` is the one
    optional field (an empty string means unspecified market).
    """

    schema_version: str
    amount: str
    currency: str
    observed_date: str
    source: str
    region: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != COST_OBSERVATION_SCHEMA:
            raise ValueError(f"schema_version must be exactly {COST_OBSERVATION_SCHEMA!r}")
        for name in ("amount", "currency", "observed_date", "source"):
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
        cls, amount: "str | int | float", currency: str, observed_date: str, source: str, region: str = ""
    ) -> "CostObservation":
        return cls(COST_OBSERVATION_SCHEMA, str(amount), currency, observed_date, source, region)

    def render(self) -> str:
        where = f", {self.region}" if self.region else ""
        return f"{self.amount} {self.currency} (observed {self.observed_date}{where}; source: {self.source})"


@dataclass(frozen=True)
class StockMaterial(Digestible):
    """A real material: one or more components (each a fraction interval), a phase, and provenance.

    Unlike a pure identity or a commodity source lead, a ``StockMaterial`` can be ASKED whether it satisfies a
    pure-reagent requirement, and it answers honestly with an interval verdict (:meth:`satisfies`).
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

    def __post_init__(self) -> None:
        if self.schema_version != STOCK_MATERIAL_SCHEMA:
            raise ValueError(f"schema_version must be exactly {STOCK_MATERIAL_SCHEMA!r}")
        for name in ("material_id", "display_name", "provenance"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.phase, Phase):
            raise TypeError("phase must be a Phase")
        if type(self.components) is not tuple or not self.components or any(
            type(c) is not MaterialComponent for c in self.components
        ):
            raise TypeError("components must be a non-empty tuple of MaterialComponent values")
        if sum(c.min_fraction for c in self.components) > 1.0 + _FRACTION_EPS:
            raise ValueError("component minimum fractions sum above 1.0 -- an infeasible material")
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
            want = _structure_key(required_identity)
            matches = [c for c in self.components if c.identity_key == want]
        elif isinstance(required_identity, str):
            want = _norm(required_identity)
            matches = [
                c for c in self.components if not _is_structure_key(c.identity_key) and _norm(c.identity_key) == want
            ]
        else:
            raise TypeError("required_identity must be a Molecule (canonical structure) or a str (declared name)")
        if not matches:
            return None
        lo = sum(c.min_fraction for c in matches)
        hi = min(1.0, sum(c.max_fraction for c in matches))
        return (lo, hi)

    def satisfies(self, required_identity: "Molecule | str", *, min_assay: float) -> FitnessVerdict:
        """Whether this material meets a ``min_assay`` (mass/mole fraction) requirement for ``required_identity``.

        Rigorous interval logic, never a silent yes: the material SATISFIES only if its worst-case (lower-bound)
        active fraction already clears ``min_assay``; it is ``INSUFFICIENT_ASSAY`` (preprocessing required) only
        if even its best case (upper bound) falls short; and anywhere the interval straddles the requirement -- or
        the fraction is unknown -- it is ``UNKNOWN_ASSAY`` (a measurement is required), because assuming the
        favourable end of an interval is exactly the identity-is-purity error section 10 forbids.
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
            f"STOCK MATERIAL {self.display_name!r} [{self.phase.value}] -- {comps}. "
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
        formulation_notes=(f"everyday source: {commodity.common_source}",),
    )
