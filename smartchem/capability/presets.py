"""smartchem/capability/presets.py -- the v0.9 named ``CapabilityProfile`` builders (Round III, D6/D8).

**OOH YEAH, LOOK AT ME, I'M THE BENCH-STOCKING MEESEEKS!** Somebody has to actually FILL the empty
``CapabilityProfile`` shell with a specific, honest, defensible declared bench -- three flavors, one
type, never a competing evaluator. ``research_lab()`` hands back a well-equipped teaching/research bench
(reflux condenser, fractional distillation, a fume hood, EVERY instrument method) that declares REAL,
FINITE physical/process ceilings it genuinely reaches (Round III D6: all-``None`` bounds are no longer
allowed to masquerade as omnipotence -- a bench that claims a capability declares a real bound for it).
``poor_man()`` hands back a kitchen-and-hardware-store bench on a declared budget -- explicitly missing the
glassware a stovetop lacks, missing the IR spectrometer, with a LOWER declared thermal ceiling.
``custom()`` is the honest escape hatch, and :func:`isopentyl_capability_fit_bench` is the Round-III gate
#18 CAPABILITY_FIT positive built on it: a fully-declared bench that actually stocks the WHOLE isopentyl
procedure.

Closed preset registry (:data:`CAPABILITY_PROFILE_PRESETS`) + :func:`resolve_capability_profile`: a NAME
resolves through a closed dict lookup, on purpose -- NEVER a dynamic import from an arbitrary string.

Round V D10: presets NEVER emit a NO_LIMIT declaration -- their finite time ceilings (10080/20160 min) are
DECLARED_BOUNDs (see :mod:`smartchem.capability.declarations`). Only an explicit ``custom(no_limit_dimensions=...)``
caller declaration may say "no time limit".
"""
from __future__ import annotations

from typing import Callable

from ..constraints import PhysicalBounds
from ..data.reagents import Availability
from ..experiment.affordability import CostVector
from ..experiment.stock import StockMaterial
from ..process_constraints import Agitation, Attention, ProcessBounds
from .enums import (
    ContainmentCapability,
    EquipmentCapability,
    MeasurementMethod,
    VentilationCapability,
    WasteCapability,
)
from .profile import CAPABILITY_PROFILE_SCHEMA, CapabilityProfile

__all__ = [
    "research_lab",
    "poor_man",
    "custom",
    "isopentyl_capability_fit_bench",
    "CAPABILITY_PROFILE_PRESETS",
    "resolve_capability_profile",
]


#: the well-equipped bench: every corpus-forced apparatus item, a real fume hood, and procurement across
#: every layperson-obtainable tier -- but NOT the unlimited-everything strawman.
_RESEARCH_LAB_EQUIPMENT: "frozenset[EquipmentCapability]" = frozenset(EquipmentCapability)

#: the household/hardware-store bench: explicitly missing every distillation/vacuum/analytical-balance item.
_POOR_MAN_EQUIPMENT: "frozenset[EquipmentCapability]" = frozenset({
    EquipmentCapability.CONTROLLED_HEATING,
    EquipmentCapability.WATER_BATH,
    EquipmentCapability.ICE_BATH,
    EquipmentCapability.REACTION_VESSEL,
    EquipmentCapability.GRAVITY_FILTRATION,
    EquipmentCapability.THERMOMETER,
})

#: layperson-obtainable procurement tiers, EVERY tier except INDUSTRIAL.
_NON_INDUSTRIAL_TIERS: "frozenset[Availability]" = frozenset(Availability) - frozenset({Availability.INDUSTRIAL})

#: the poor man's four kitchen-adjacent shops -- NOT industrial.
_POOR_MAN_TIERS: "frozenset[Availability]" = frozenset({
    Availability.GROCERY, Availability.PHARMACY, Availability.HARDWARE, Availability.POOL_GARDEN,
})

#: D6 real, finite, DEFENSIBLE bounds -- never all-``None`` masquerading as capability. A research bench
#: reaching reflux + fractional distillation genuinely holds a mixture near 250 C in a hood; a kitchen
#: stovetop a lower ~200 C. Both express a real process ceiling (any declared attention/agitation mode,
#: hourly-or-slacker checks) that the sourced corpus's PERIODIC/MANUAL procedures satisfy without a gap.
# Wave-C F1: declare the honest atmospheric floor (min_pressure_atm=1.0) too -- a standard bench operates
# at atmospheric and cannot pull a vacuum below 1 atm without a pump. Now that _physical_axis fails closed
# per-dimension (a real route demand on an undeclared dimension -> UNKNOWN), a bench that omitted its
# pressure FLOOR would go UNKNOWN against the isopentyl route's 1 atm demand; declaring it keeps the honest
# atmospheric FIT while a real vacuum route (min_pressure < 1 atm) still correctly BLOCKS on these benches.
_RESEARCH_LAB_PHYSICAL: PhysicalBounds = PhysicalBounds.of(
    max_temperature_k=523.15, max_pressure_atm=2.0, min_pressure_atm=1.0
)
_POOR_MAN_PHYSICAL: PhysicalBounds = PhysicalBounds.of(
    max_temperature_k=473.15, max_pressure_atm=1.5, min_pressure_atm=1.0
)


def _bench_process_bounds() -> ProcessBounds:
    """A permissive-but-REAL process ceiling (D6/F56): it constrains real TIME dimensions (a bench has finite,
    if generous, patience) AND admits every attention/agitation mode the hand-run sourced corpus declares.
    Round IV F56 retires the "process-time omission = unlimited patience" reading -- an omitted bound is
    UNMODELED (assess fails it closed to UNKNOWN against a real demand), so a bench that claims it can run a
    process declares a real finite time ceiling. A genuinely multi-week route now BLOCKS on the elapsed
    ceiling. Built fresh per call so no caller shares one mutable default. NOTE: the sourced isopentyl route
    leaves its whole-STEP elapsed CEILING undeclared (only the 1-hour reflux FLOOR is timed; the workup +
    fractional distillation are untimed), so its process axis honestly reads UNKNOWN here -- not a pass, and
    not a fabricated duration."""
    return ProcessBounds.of(
        max_step_minutes=10080.0,     # <= 1 week per step: a real, finite bench patience (D6), never omnipotence
        max_total_minutes=20160.0,    # <= 2 weeks whole-route
        allowed_attention=tuple(Attention),
        allowed_agitation=tuple(Agitation),
    )


def research_lab(*, material_inventory: "tuple[StockMaterial, ...]" = ()) -> CapabilityProfile:
    """A well-equipped teaching/research bench (D6): explicit apparatus, a real fume hood, indoor
    ventilation, every non-industrial procurement tier, every :class:`MeasurementMethod` (mass, m.p., IR),
    and REAL finite physical/process ceilings it genuinely reaches (>= the sourced corpus's reflux demand).

    ``material_inventory=()`` by default -- the honest F2 default: nobody declared real stock, so the
    material axis stays UNKNOWN until a caller supplies real :class:`StockMaterial` items. NOT "unlimited
    lab": no industrial supplier, no arbitrary pressure vessel, no assumed 100%-pure pantry.
    """
    return CapabilityProfile(
        schema_version=CAPABILITY_PROFILE_SCHEMA,
        profile_id="research-lab",
        material_inventory=tuple(material_inventory),
        equipment=_RESEARCH_LAB_EQUIPMENT,
        physical_bounds=_RESEARCH_LAB_PHYSICAL,
        process_bounds=_bench_process_bounds(),
        containment=frozenset({ContainmentCapability.FUME_HOOD}),
        ventilation=frozenset({VentilationCapability.INDOOR}),
        measurement=frozenset(MeasurementMethod),
        waste_handling=frozenset(WasteCapability),
        procurement=_NON_INDUSTRIAL_TIERS,
        budget=None,
        provenance=(
            "smartchem.capability.presets.research_lab() -- a well-equipped teaching/research bench preset "
            "(D6): explicit apparatus + fume hood + non-industrial procurement + every instrument method + "
            "real finite T<=523.15 K / P<=2 atm ceilings; no declared material stock unless supplied"
        ),
    )


def poor_man(
    *,
    budget: "CostVector | None" = None,
    material_inventory: "tuple[StockMaterial, ...]" = (),
) -> CapabilityProfile:
    """A household/hardware-store bench on a declared budget (D6): the low-resource equipment subset, NO
    containment (no fume hood), outdoor ventilation (real, but never a containment substitute), the four
    kitchen-adjacent procurement tiers, and only the two CHEAP instrument methods it plausibly owns -- a
    kitchen scale (MASS) and a melting-point check, but explicitly NO INFRARED_SPECTROSCOPY. That missing
    IR is what BLOCKS the isopentyl route's measurement axis under this bench (criterion 14). Its declared
    thermal ceiling is a real ~200 C stovetop, not all-``None`` omnipotence.

    ``budget`` defaults to ``CostVector(cash=200.0, currency="USD", unit="USD")`` -- a DEFAULT PARAMETER
    value, built fresh on every call. Pass a different ``CostVector`` (or ``None``) to override it.
    """
    resolved_budget = budget if budget is not None else CostVector(cash=200.0, currency="USD", unit="USD")
    return CapabilityProfile(
        schema_version=CAPABILITY_PROFILE_SCHEMA,
        profile_id="poor-man",
        material_inventory=tuple(material_inventory),
        equipment=_POOR_MAN_EQUIPMENT,
        physical_bounds=_POOR_MAN_PHYSICAL,
        process_bounds=_bench_process_bounds(),
        containment=frozenset(),
        ventilation=frozenset({VentilationCapability.OUTDOOR}),
        measurement=frozenset({MeasurementMethod.MASS, MeasurementMethod.MELTING_POINT}),
        waste_handling=frozenset({WasteCapability.AQUEOUS_NEUTRAL}),
        procurement=_POOR_MAN_TIERS,
        budget=resolved_budget,
        provenance=(
            "smartchem.capability.presets.poor_man() -- a household/hardware-store bench preset (D6): "
            "low-resource equipment, no containment, outdoor ventilation, kitchen-adjacent procurement, "
            "MASS + MELTING_POINT only (NO IR), real finite T<=473.15 K ceiling, a declared cash budget"
        ),
    )


def custom(
    *,
    profile_id: str,
    material_inventory: "tuple[StockMaterial, ...]" = (),
    equipment: "frozenset[EquipmentCapability]" = frozenset(),
    physical_bounds: "PhysicalBounds | None" = None,
    process_bounds: "ProcessBounds | None" = None,
    containment: "frozenset[ContainmentCapability]" = frozenset(),
    ventilation: "frozenset[VentilationCapability]" = frozenset(),
    measurement: "frozenset[MeasurementMethod]" = frozenset(),
    waste_handling: "frozenset[WasteCapability]" = frozenset(),
    procurement: "frozenset[Availability]" = frozenset(),
    budget: "CostVector | None" = None,
    provenance: str = "smartchem.capability.presets.custom() -- a fully explicit declared capability profile",
    no_limit_dimensions: "frozenset[str]" = frozenset(),
) -> CapabilityProfile:
    """The forcing tool (D6): a fully-explicit passthrough of every ``CapabilityProfile`` field, no hidden
    defaults doing anyone's thinking for them. This is how the gate #18 CAPABILITY_FIT positive
    (:func:`isopentyl_capability_fit_bench`) and its targeted negatives get built -- a caller who genuinely
    knows their bench states it here, plainly, and ``assess()`` takes it at its word.

    ``physical_bounds``/``process_bounds`` default to unconstrained; a Custom bench that claims a real
    physical/process capability against a real route demand must state a real finite bound (D6), or the
    axis honestly reads UNKNOWN, never a fabricated UNCONSTRAINED pass.

    ``no_limit_dimensions`` (Round V D10) is the ONLY way any profile carries a NO_LIMIT declaration: an explicit
    caller statement that a time PREFERENCE dimension (``max_step_minutes``/``max_total_minutes``/
    ``max_active_minutes``) is unbounded for them. It defaults to empty; no preset ever passes it.
    """
    return CapabilityProfile(
        schema_version=CAPABILITY_PROFILE_SCHEMA,
        profile_id=profile_id,
        material_inventory=tuple(material_inventory),
        equipment=frozenset(equipment),
        physical_bounds=physical_bounds if physical_bounds is not None else PhysicalBounds.unconstrained(),
        process_bounds=process_bounds if process_bounds is not None else ProcessBounds.unconstrained(),
        containment=frozenset(containment),
        ventilation=frozenset(ventilation),
        measurement=frozenset(measurement),
        waste_handling=frozenset(waste_handling),
        procurement=frozenset(procurement),
        budget=budget,
        provenance=provenance,
        no_limit_dimensions=frozenset(no_limit_dimensions),
    )


def isopentyl_capability_fit_bench(
    *,
    material_inventory: "tuple[StockMaterial, ...] | None" = None,
    equipment: "frozenset[EquipmentCapability] | None" = None,
    containment: "frozenset[ContainmentCapability] | None" = None,
    measurement: "frozenset[MeasurementMethod] | None" = None,
    procurement: "frozenset[Availability] | None" = None,
    physical_bounds: "PhysicalBounds | None" = None,
    process_bounds: "ProcessBounds | None" = None,
    profile_id: str = "isopentyl-fit-bench",
    provenance: str = (
        "smartchem.capability.presets.isopentyl_capability_fit_bench() -- the Round-III gate #18 "
        "CAPABILITY_FIT positive: a fully-declared Custom bench stocking the WHOLE isopentyl procedure"
    ),
) -> CapabilityProfile:
    """The Round-III gate #18 CAPABILITY_FIT positive (D1/D5/D6): a fully-declared Custom bench that stocks
    the whole isopentyl-acetate procedure (:func:`~smartchem.data.material_library.isopentyl_fully_declared_inventory`),
    owns the full distillation glassware + a fume hood + every instrument method (IR included), declares
    real finite physical/process ceilings >= the route's 416 K reflux demand, routes AQUEOUS_NEUTRAL + HAZARDOUS
    waste (Round V D9: the conc. H2SO4 catalyst residual is a certain HAZARDOUS stream -- a hood bench that runs
    it declares hazardous-waste routing; the waste axis still reads UNKNOWN on the unresolved spent streams),
    reaches HARDWARE-tier procurement (the H2SO4 catalyst), and declares NO budget (the monetary axis rides
    UNCONSTRAINED -- commensurable-or-absent; Round V: ``budget=None`` without a NO_LIMIT declaration is
    UNDECLARED). Since Round IV it no longer reaches ``CapabilityStatus.FIT`` on the REAL searched isopentyl route
    (the source under-specifies whole-process duration / spent-stream disposal) -- honest UNKNOWN, not gamed.

    Every keyword is an override hook so the targeted-negative benches (minus one capability apiece) are
    built by MINIMAL diff from this exact positive -- each fails on its ONE axis, nothing else moved.
    """
    from ..data import material_library
    return custom(
        profile_id=profile_id,
        material_inventory=(
            material_library.isopentyl_fully_declared_inventory() if material_inventory is None else material_inventory
        ),
        equipment=frozenset(EquipmentCapability) if equipment is None else equipment,
        physical_bounds=PhysicalBounds.of(max_temperature_k=500.0, max_pressure_atm=2.0, min_pressure_atm=1.0)
        if physical_bounds is None else physical_bounds,
        process_bounds=_bench_process_bounds() if process_bounds is None else process_bounds,
        containment=frozenset({ContainmentCapability.FUME_HOOD}) if containment is None else containment,
        ventilation=frozenset({VentilationCapability.INDOOR}),
        measurement=frozenset(MeasurementMethod) if measurement is None else measurement,
        waste_handling=frozenset({WasteCapability.AQUEOUS_NEUTRAL, WasteCapability.HAZARDOUS}),
        procurement=_NON_INDUSTRIAL_TIERS if procurement is None else procurement,
        budget=None,
        provenance=provenance,
    )


#: the CLOSED preset registry: a NAME maps to a zero-argument builder, and NOTHING else resolves a string
#: into a profile -- no dynamic import, no ``getattr``, no ``eval``.
CAPABILITY_PROFILE_PRESETS: "dict[str, Callable[[], CapabilityProfile]]" = {
    "research-lab": research_lab,
    "poor-man": poor_man,
}


def resolve_capability_profile(spec: "str | CapabilityProfile") -> CapabilityProfile:
    """Resolve a preset NAME or an already-built :class:`CapabilityProfile` into one, closed-lookup only.

    **I'm the Meeseeks who refuses to improvise!** A ``str`` goes through :data:`CAPABILITY_PROFILE_PRESETS`
    -- an unrecognized name is a loud ``ValueError``, never a silent fallback and NEVER a dynamic
    ``importlib``/``eval`` reach. A :class:`CapabilityProfile` instance passes straight through unchanged.
    """
    if type(spec) is CapabilityProfile:
        return spec
    if isinstance(spec, str):
        try:
            builder = CAPABILITY_PROFILE_PRESETS[spec]
        except KeyError:
            raise ValueError(
                f"unknown capability profile preset {spec!r}; known presets: "
                f"{sorted(CAPABILITY_PROFILE_PRESETS)}"
            ) from None
        return builder()
    raise TypeError("capability profile spec must be a preset name (str) or a CapabilityProfile instance")
