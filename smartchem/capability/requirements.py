"""smartchem/capability/requirements.py -- the PURE requirement projection (FREEZE decision 2 + 3).

**Look at me, I'm a Meeseeks who only ever ASKS questions!** ``compile_capability_requirements`` reads
ONE ``ExperimentRoute`` and answers, axis by axis, "what does the sourced evidence say THIS route needs?"
-- and it is FORBIDDEN, on pain of not being the projection the FREEZE describes, from ever peeking at a
``CapabilityProfile`` to answer that question. A requirement compiled here has no idea whether anyone's
bench can meet it; that verdict is a whole separate Meeseeks's job (:mod:`smartchem.capability.assess`).

Every axis here reads a fact that ALREADY EXISTS on the route -- never a new physics, never a fabricated
threshold:

* ``material`` -- the route's purchasable leaf reactants (:attr:`ExperimentRoute.leaf_inputs`, the SAME
  COST-VEC-01 leaf definition ``affordability.py`` already uses), each an honest
  :class:`MaterialRequirement` with ``required_assay=None`` (this corpus never sources a numeric purity
  spec -- FREEZE decision 3: "never assume 100%"). A caller who DOES have a sourced minimum assay for a
  given input is free to build a :class:`MaterialRequirement` with a real ``required_assay`` directly;
  this projection just never invents one from silence.
* ``equipment`` -- the union, over every step, of ``ProcedureEvidence.apparatus`` (per-operation, quote
  sourced) PLUS ``ProcessRequirements.equipment`` (whole-step cross-check), CLASSIFIED through
  :func:`~smartchem.capability.equipment_resolver.classify_apparatus_strings` -- deliberately NOT
  ``equipment_for_step`` (Wave-A finding F1: that function reads only free-text medium + T/P extrema and
  silently drops the reflux condenser and the distillation rig the source actually demands). Vetted
  consumables (``"boiling stones"`` and friends) are dropped without a trace; anything else the resolver
  has never met stays on the record as ``equipment_unrecognized`` -- never quietly absorbed into "no
  requirement" (that silent absorption was the exact hole assess.py's equipment axis now refuses).
* ``containment`` -- ONLY ``equipment_for_step``'s hazard-driven ``CONTAINMENT``-kind items (F-nag: "two
  evidence lanes, never crossed" -- apparatus tuples feed equipment, GHS hazards feed containment, never
  the reverse).
* ``physical`` -- T/P extrema off ``ProcessRequirements``/the envelope, fed into the REUSED
  :class:`~smartchem.constraints.PhysicalBounds` container.
* ``process`` -- literally each step's ``ProcessRequirements`` untouched, so
  :func:`~smartchem.process_constraints.evaluate_process_requirements` -- NOT reimplemented here -- does
  the real comparison against a profile's ``ProcessBounds``.
* ``waste`` -- derived from ``RouteHandling.all_byproducts``/``all_offgases`` + ``Fate`` (never
  ``CostVector.waste_disposal``, which nothing populates).
* ``procurement`` -- carried as ``procurement_catalysts``: one ``(name, tier)`` pair per catalyst the route
  actually DECLARES (``ConditionEnvelope.catalysts``, every step, deduplicated), ``tier`` resolved through
  the grounded, UNMODIFIED :func:`~smartchem.experiment.catalyst_availability.catalyst_availability`
  classifier (``None`` = UNRECOGNIZED -- a fact this projection reports, never launders into "no
  requirement"). The former leaf-commodity slice (``commodity_for`` over ``route.leaf_inputs``) is
  RETIRED here: a purchasable leaf's tier is a *material*-sourcing fact already implicit in the material
  axis's own inventory check, whereas a declared catalyst is a REGENERATED substance the material axis
  never prices at all -- conflating the two bought nothing and cost this axis its only real teeth (gate
  #10, Wave-B item 3 "v09-procurement"). Whether that ``(name, tier)`` is actually obtainable is a
  profile-relative verdict, so it is left un-folded here and decided in :mod:`smartchem.capability.assess`.
* ``attention_care`` -- ``RouteHandling.care`` (the hazard-driven DEMAND), kept structurally apart from
  the ``process`` axis's operator-declared ``Attention``/``Agitation`` (the CAPABILITY) per decision 2.
* ``monetary`` -- ``affordability.basket_cost_vector`` over the same leaf inputs (known lower bounds only).
* ``measurement`` -- always empty in THIS corpus (decision 4: no ``VERIFY`` op carries a structured
  apparatus tuple today, and fabricating one from free text like "weigh + IR" would be exactly the
  invented-requirement failure the freeze forbids).

Nothing here decides FIT/BLOCKED/UNKNOWN -- that fold lives in :mod:`smartchem.capability.assess`.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..category import Molecule
from ..contracts import Digestible
from ..data.reagents import Availability
from ..experiment.affordability import CostVector, basket_cost_vector
from ..experiment.catalyst_availability import catalyst_availability
from ..experiment.equipment import EquipmentKind, equipment_for_step
from ..experiment.handling import CareLevel, verify_handling
from ..experiment.step import ExperimentRoute
from ..experiment.stock import Phase, StockQuantity
from ..constraints import PhysicalBounds
from ..process_constraints import ProcessRequirements
from .enums import ContainmentCapability, EquipmentCapability, MeasurementCapability, WasteCapability
from .equipment_resolver import classify_apparatus_strings

__all__ = [
    "MaterialRequirement",
    "WasteRequirement",
    "RouteCapabilityRequirements",
    "compile_capability_requirements",
]


@dataclass(frozen=True)
class MaterialRequirement(Digestible):
    """A REQUIREMENT-side object (never a second inventory -- FREEZE decision 3): one route input, its
    canonical structure identity, and what assay it needs -- if that is even known.

    ``required_assay`` is ``float | None`` where ``None`` is the honest UNKNOWN (never a fabricated 100%):
    this corpus's sourced procedures name reagents ("isopentyl alcohol", "glacial acetic acid") without a
    quoted numeric purity floor, so the PURE route projection never invents one. A caller who genuinely has
    a sourced minimum assay for a given input may construct one with a real value; :meth:`satisfies-style
    <smartchem.experiment.stock.StockMaterial.satisfies>` assessment against a declared
    :class:`~smartchem.experiment.stock.StockMaterial` inventory happens in
    :mod:`smartchem.capability.assess`, never here.
    """

    identity: Molecule
    required_assay: "float | None"
    phase: "Phase | None"
    quantity: "StockQuantity | None"
    role: str
    evidence_source: str

    def __post_init__(self) -> None:
        if type(self.identity) is not Molecule:
            raise TypeError("identity must be a smartchem.category.Molecule")
        if self.required_assay is not None:
            if isinstance(self.required_assay, bool) or not isinstance(self.required_assay, (int, float)):
                raise TypeError("required_assay must be a real number or None (UNKNOWN)")
            if not (0.0 < float(self.required_assay) <= 1.0):
                raise ValueError("required_assay must be a fraction in (0, 1] or None (UNKNOWN)")
            object.__setattr__(self, "required_assay", float(self.required_assay))
        if self.phase is not None and type(self.phase) is not Phase:
            raise TypeError("phase must be a smartchem.experiment.stock.Phase or None")
        if self.quantity is not None and type(self.quantity) is not StockQuantity:
            raise TypeError("quantity must be a smartchem.experiment.stock.StockQuantity or None")
        for name in ("role", "evidence_source"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
            object.__setattr__(self, name, value.strip())


@dataclass(frozen=True)
class WasteRequirement(Digestible):
    """The waste-routing categories a route's byproduct/off-gas ledger demands, plus the named facts that
    put them there (FREEZE decision 2: derived from ``RouteHandling.all_byproducts``/``all_offgases`` +
    ``Fate``, never ``CostVector.waste_disposal``). An empty ``categories`` means no waste-routing
    obligation was derived (e.g. a single-product step with no byproduct at all)."""

    categories: "frozenset[WasteCapability]"
    reasons: "tuple[str, ...]"

    def __post_init__(self) -> None:
        if type(self.categories) is not frozenset or any(
            type(c) is not WasteCapability for c in self.categories
        ):
            raise TypeError("categories must be a frozenset of WasteCapability values")
        if type(self.reasons) is not tuple or any(
            not isinstance(r, str) or not r.strip() for r in self.reasons
        ):
            raise TypeError("reasons must be a tuple of non-empty strings")


@dataclass(frozen=True)
class RouteCapabilityRequirements(Digestible):
    """The independent capability axes a route needs, PURELY projected from its own sourced evidence
    (FREEZE decision 2). ``route_digest`` ties this record back to the exact ``ExperimentRoute`` it was
    compiled from (the transport-layer binding decision 7 relies on).

    ``equipment_unrecognized`` is this package's concrete carrier for decision 4's "an UNRECOGNIZED
    apparatus string -> that requirement item is UNKNOWN, never silently satisfied": it is the exact set of
    sourced apparatus/equipment strings that hit NEITHER the closed alias table NOR the vetted consumable
    whitelist (see :mod:`.equipment_resolver`'s docstring). Vetted consumables like "boiling stones" or
    "glass rod" are real evidence too, but they are dropped before this field is built -- being on the
    whitelist IS the trace that they were seen and deliberately judged not a capability. What is left in
    ``equipment_unrecognized`` is genuinely untabled apparatus (a "rotary evaporator", a "Soxhlet
    extractor"), and :func:`~smartchem.capability.assess.assess` folds a non-empty set here straight to
    an UNKNOWN equipment axis, ahead of the ordinary recognized-subset check -- an untabled capability
    item must never silently pass just because nobody taught the resolver its name yet.
    """

    route_digest: str
    material: "tuple[MaterialRequirement, ...]"
    equipment: "frozenset[EquipmentCapability]"
    equipment_unrecognized: "tuple[str, ...]"
    physical: PhysicalBounds
    process: "tuple[ProcessRequirements | None, ...]"
    containment: "frozenset[ContainmentCapability]"
    measurement: "frozenset[MeasurementCapability]"
    waste: WasteRequirement
    procurement_catalysts: "tuple[tuple[str, Availability | None], ...]"
    attention_care: CareLevel
    monetary: CostVector

    def __post_init__(self) -> None:
        if not isinstance(self.route_digest, str) or not self.route_digest:
            raise ValueError("route_digest must be a non-empty string")
        if type(self.material) is not tuple or any(
            type(m) is not MaterialRequirement for m in self.material
        ):
            raise TypeError("material must be a tuple of MaterialRequirement values")
        if type(self.equipment) is not frozenset or any(
            type(e) is not EquipmentCapability for e in self.equipment
        ):
            raise TypeError("equipment must be a frozenset of EquipmentCapability values")
        if type(self.equipment_unrecognized) is not tuple or any(
            not isinstance(s, str) or not s.strip() for s in self.equipment_unrecognized
        ):
            raise TypeError("equipment_unrecognized must be a tuple of non-empty strings")
        if type(self.physical) is not PhysicalBounds:
            raise TypeError("physical must be a smartchem.constraints.PhysicalBounds")
        if type(self.process) is not tuple or any(
            p is not None and type(p) is not ProcessRequirements for p in self.process
        ):
            raise TypeError("process must be a tuple of (ProcessRequirements | None)")
        if type(self.containment) is not frozenset or any(
            type(c) is not ContainmentCapability for c in self.containment
        ):
            raise TypeError("containment must be a frozenset of ContainmentCapability values")
        if type(self.measurement) is not frozenset or any(
            type(m) is not MeasurementCapability for m in self.measurement
        ):
            raise TypeError("measurement must be a frozenset of MeasurementCapability values")
        if type(self.waste) is not WasteRequirement:
            raise TypeError("waste must be a WasteRequirement")
        if type(self.procurement_catalysts) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0].strip()
            or (item[1] is not None and type(item[1]) is not Availability)
            for item in self.procurement_catalysts
        ):
            raise TypeError(
                "procurement_catalysts must be a tuple of (name: non-empty str, tier: Availability | None) pairs"
            )
        if type(self.attention_care) is not CareLevel:
            raise TypeError("attention_care must be a CareLevel")
        if type(self.monetary) is not CostVector:
            raise TypeError("monetary must be a CostVector")


def _material_requirements(route: ExperimentRoute) -> "tuple[MaterialRequirement, ...]":
    """One honest, UNKNOWN-assay requirement per purchasable leaf reactant (COST-VEC-01's own leaf
    definition -- an intermediate a route makes internally is never a material REQUIREMENT, only
    something a profile would need to stock if it were bought instead)."""
    return tuple(
        MaterialRequirement(
            identity=leaf,
            required_assay=None,
            phase=None,
            quantity=None,
            role="reactant",
            evidence_source=(
                "route leaf input (ExperimentRoute.leaf_inputs); no sourced minimum-assay requirement is "
                "declared in this corpus -- required_assay stays UNKNOWN, never assumed 100%"
            ),
        )
        for leaf in route.leaf_inputs
    )


def _equipment_requirement(
    route: ExperimentRoute,
) -> "tuple[frozenset[EquipmentCapability], tuple[str, ...]]":
    """The union, over every step, of sourced apparatus strings classified through the closed resolver --
    NEVER ``equipment_for_step`` (F1: it drops the reflux condenser / distillation rig the source names).

    Vetted consumables are dropped here, silently and on purpose (the whitelist itself is their trace);
    anything the resolver has never met at all is carried forward as ``equipment_unrecognized`` so
    :mod:`.assess` can refuse to guess past it."""
    raw: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is not None:
            for op in procedure.operations:
                raw.update(op.apparatus)
        process = step.envelope.process
        if process is not None and process.equipment is not None:
            raw.update(process.equipment)
    recognized, _ignored_consumables, unrecognized = classify_apparatus_strings(raw)
    return recognized, tuple(sorted(unrecognized))


def _containment_requirement(route: ExperimentRoute) -> "frozenset[ContainmentCapability]":
    """ONLY ``equipment_for_step``'s hazard-driven ``CONTAINMENT``-kind items (F-nag's two-lanes rule);
    today that function only ever emits the "fume hood" item for this kind, so the sole reachable member
    is ``FUME_HOOD`` -- but the check is on ``kind``, not on a name string, so it stays sound if that
    function ever grows a second CONTAINMENT-kind item."""
    for step in route.steps:
        for item in equipment_for_step(step):
            if item.kind is EquipmentKind.CONTAINMENT:
                return frozenset({ContainmentCapability.FUME_HOOD})
    return frozenset()


def _physical_requirement(route: ExperimentRoute) -> PhysicalBounds:
    """The route's own T/P extrema (a DEMAND, reusing the ceiling-shaped ``PhysicalBounds`` container as
    decision 2 directs: "feed PhysicalBounds"), read off ``ProcessRequirements`` first and the envelope's
    declared temperature interval as a fallback."""
    peaks: "list[float]" = []
    min_pressures: "list[float]" = []
    max_pressures: "list[float]" = []
    for step in route.steps:
        process = step.envelope.process
        if process is not None and process.peak_temperature_k is not None:
            peaks.append(process.peak_temperature_k)
        elif step.envelope.temperature is not None:
            peaks.append(step.envelope.temperature.hi)
        if process is not None:
            if process.min_pressure_atm is not None:
                min_pressures.append(process.min_pressure_atm)
            if process.max_pressure_atm is not None:
                max_pressures.append(process.max_pressure_atm)
    return PhysicalBounds.of(
        max_temperature_k=max(peaks) if peaks else None,
        min_pressure_atm=min(min_pressures) if min_pressures else None,
        max_pressure_atm=max(max_pressures) if max_pressures else None,
    )


def _waste_requirement(route: ExperimentRoute) -> WasteRequirement:
    """Waste-routing categories derived from the sourced byproduct ledger + ``Fate`` -- an off-gas needs
    ``OFFGAS_CAPTURE``; a byproduct whose resolved hazard record carries a REAL (non-empty) GHS profile
    needs ``HAZARDOUS``; a condensed byproduct that is either UNASSESSED or POSITIVELY assessed benign
    (e.g. water's empty GHS profile -- ``ByproductEntry.hazard_name`` is set for a benign assessment too,
    ``handling.py``'s own "inform, never neuter" doctrine) is treated as an ``AQUEOUS_NEUTRAL`` disposal
    stream: a coarse, honestly-labelled default for "nothing hazardous was found on it", never a hazard
    clearance."""
    handling = verify_handling(route)
    # a byproduct's hazard_name only names WHICH record resolved (benign or not); the real GHS codes live
    # on the matching HazardFlag, so build that lookup once rather than re-deriving hazard.py facts here.
    ghs_codes_by_name: "dict[str, tuple[str, ...]]" = {
        hazard.name: hazard.ghs_codes for step_handling in handling.steps for hazard in step_handling.hazards
    }
    categories: "set[WasteCapability]" = set()
    reasons: "list[str]" = []
    for b in handling.all_byproducts:
        is_real_hazard = b.hazard_name is not None and bool(ghs_codes_by_name.get(b.hazard_name))
        if b.is_offgas:
            categories.add(WasteCapability.OFFGAS_CAPTURE)
            reasons.append(f"waste: {b.molecule!r} evolves as an off-gas ({b.reason}) -- needs OFFGAS_CAPTURE")
            if is_real_hazard:
                categories.add(WasteCapability.HAZARDOUS)
                reasons.append(f"waste: off-gas {b.molecule!r} carries a real sourced hazard ({b.hazard_name})")
        elif is_real_hazard:
            categories.add(WasteCapability.HAZARDOUS)
            reasons.append(f"waste: condensed byproduct {b.molecule!r} carries a real sourced hazard ({b.hazard_name})")
        else:
            categories.add(WasteCapability.AQUEOUS_NEUTRAL)
            reasons.append(
                f"waste: condensed byproduct {b.molecule!r} carries no real (non-empty GHS) sourced hazard -- "
                "routed AQUEOUS_NEUTRAL"
            )
    return WasteRequirement(frozenset(categories), tuple(sorted(set(reasons))))


def _procurement_catalysts_requirement(
    route: ExperimentRoute,
) -> "tuple[tuple[str, Availability | None], ...]":
    """One ``(name, tier)`` pair per catalyst ``route`` actually DECLARES -- every step's
    ``ConditionEnvelope.catalysts`` (the SAME field :func:`~smartchem.experiment.catalyst_availability.
    route_catalyst_blockers` iterates), deduplicated first-seen so a catalyst named on two steps costs one
    entry, not two identical reasons downstream. ``tier`` is resolved through the UNMODIFIED, grounded
    :func:`~smartchem.experiment.catalyst_availability.catalyst_availability` classifier; ``None`` is the
    honest UNRECOGNIZED verdict -- reported here, never quietly promoted to "no requirement" (that
    promotion is exactly the M17 hole this field exists to close). Whether a given tier is actually
    obtainable is profile-relative and stays out of this PURE projection -- see
    :mod:`smartchem.capability.assess`."""
    seen: "dict[str, Availability | None]" = {}
    for step in route.steps:
        for cat in step.envelope.catalysts:
            if cat not in seen:
                seen[cat] = catalyst_availability(cat)
    return tuple(seen.items())


def compile_capability_requirements(route: ExperimentRoute) -> RouteCapabilityRequirements:
    """The PURE projection: what does ``route``'s own sourced evidence require, on every capability axis?

    Reads ONLY ``route`` -- never a :class:`~smartchem.capability.profile.CapabilityProfile`, never a
    named preset, never the network. Every axis is documented at the top of this module; this function
    just assembles them.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be a smartchem.experiment.step.ExperimentRoute")

    equipment, equipment_unrecognized = _equipment_requirement(route)
    handling_care = verify_handling(route).care

    return RouteCapabilityRequirements(
        route_digest=route.digest,
        material=_material_requirements(route),
        equipment=equipment,
        equipment_unrecognized=equipment_unrecognized,
        physical=_physical_requirement(route),
        process=tuple(step.envelope.process for step in route.steps),
        containment=_containment_requirement(route),
        measurement=frozenset(),
        waste=_waste_requirement(route),
        procurement_catalysts=_procurement_catalysts_requirement(route),
        attention_care=handling_care,
        monetary=basket_cost_vector(list(route.leaf_inputs)),
    )
