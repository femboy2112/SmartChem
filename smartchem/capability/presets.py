"""smartchem/capability/presets.py -- the v0.9 named ``CapabilityProfile`` builders (FREEZE decision 6,
Wave B item 2, "v09-profile-presets").

**OOH YEAH, LOOK AT ME, I'M THE BENCH-STOCKING MEESEEKS!** Somebody has to actually FILL the empty
``CapabilityProfile`` shell with a specific, honest, defensible declared bench -- three flavors, one
type, never a competing evaluator. ``research_lab()`` hands back a well-equipped teaching/research bench
(reflux condenser, fractional distillation, a fume hood -- but NOT an unknown pantry and NOT an
industrial reagent supplier by default). ``poor_man()`` hands back a kitchen-and-hardware-store bench on
a declared budget -- explicitly missing the glassware a stovetop just doesn't have. ``custom()`` is the
honest escape hatch: a fully-explicit passthrough for whoever actually knows what THEIR bench has.

This module consumes the FROZEN core (:mod:`.profile`, :mod:`.enums`) and adds nothing new to compare
against -- every preset is just a specific, named point in the SAME ``CapabilityProfile`` space. Building
a second bespoke "ResearchLabProfile" type here would be exactly the competing-evaluator mistake decision
1's docstring warns against; existence is pain enough without a type getting to reinvent itself twice.

Closed preset registry (:data:`CAPABILITY_PROFILE_PRESETS`) + :func:`resolve_capability_profile`: a NAME
resolves through a closed dict lookup, on purpose -- FREEZE decision 6/7 is explicit that this is NEVER a
dynamic import from an arbitrary string. An unrecognized name is a loud ``ValueError``, not a guess.
"""
from __future__ import annotations

from typing import Callable

from ..constraints import PhysicalBounds
from ..data.reagents import Availability
from ..experiment.affordability import CostVector
from ..experiment.stock import StockMaterial
from ..process_constraints import ProcessBounds
from .enums import ContainmentCapability, EquipmentCapability, MeasurementCapability, VentilationCapability, WasteCapability
from .profile import CAPABILITY_PROFILE_SCHEMA, CapabilityProfile

__all__ = [
    "research_lab",
    "poor_man",
    "custom",
    "CAPABILITY_PROFILE_PRESETS",
    "resolve_capability_profile",
]


#: the well-equipped bench (FREEZE decision 6): every corpus-forced apparatus item, a real fume hood, and
#: procurement across every layperson-obtainable tier -- but NOT the unlimited-everything strawman. No
#: declared T/P ceiling and no declared time/attention ceiling (the enum/bounds "don't force a choice"
#: here -- a real teaching lab's exact ceiling isn't sourced data this Meeseeks is allowed to invent, so
#: those two axes stay honestly UNCONSTRAINED rather than fabricated).
_RESEARCH_LAB_EQUIPMENT: "frozenset[EquipmentCapability]" = frozenset(EquipmentCapability)

#: the household/hardware-store bench (FREEZE decision 6): explicitly missing every distillation/vacuum/
#: analytical-balance item -- "kitchen scale != analytical", and a stovetop reflux setup has no condenser.
#: (Also, quietly, no separatory funnel: the frozen 6-member set names exactly what a poor man's kitchen
#: keeps, and a funnel for liquid-liquid separation didn't make that cut either -- not a typo, the freeze
#: text itself only lists these six.)
_POOR_MAN_EQUIPMENT: "frozenset[EquipmentCapability]" = frozenset({
    EquipmentCapability.CONTROLLED_HEATING,
    EquipmentCapability.WATER_BATH,
    EquipmentCapability.ICE_BATH,
    EquipmentCapability.REACTION_VESSEL,
    EquipmentCapability.GRAVITY_FILTRATION,
    EquipmentCapability.THERMOMETER,
})

#: layperson-obtainable procurement tiers, EVERY tier except INDUSTRIAL -- a research lab still isn't an
#: unlimited chemical supplier by default (FREEZE decision 6: "industrial only if explicitly declared").
_NON_INDUSTRIAL_TIERS: "frozenset[Availability]" = frozenset(Availability) - frozenset({Availability.INDUSTRIAL})

#: the poor man's four kitchen-adjacent shops -- NOT industrial, same four tiers named in decision 6.
_POOR_MAN_TIERS: "frozenset[Availability]" = frozenset({
    Availability.GROCERY, Availability.PHARMACY, Availability.HARDWARE, Availability.POOL_GARDEN,
})


def research_lab(*, material_inventory: "tuple[StockMaterial, ...]" = ()) -> CapabilityProfile:
    """A well-equipped teaching/research bench (FREEZE decision 6): explicit apparatus, a real fume hood,
    indoor ventilation, every non-industrial procurement tier, and every :class:`MeasurementCapability`
    tier (a real lab can do free observation AND run a cheap instrument AND an analytical one).

    ``material_inventory=()`` by default -- the honest F2 default: nobody declared real stock, so the
    material axis stays UNKNOWN under :func:`~smartchem.capability.assess.assess` until a caller supplies
    real :class:`StockMaterial` items. This is deliberately NOT "unlimited lab": no industrial reagent
    supplier, no arbitrary pressure vessel, no assumed 100%-pure pantry.
    """
    return CapabilityProfile(
        schema_version=CAPABILITY_PROFILE_SCHEMA,
        profile_id="research-lab",
        material_inventory=tuple(material_inventory),
        equipment=_RESEARCH_LAB_EQUIPMENT,
        physical_bounds=PhysicalBounds.unconstrained(),
        process_bounds=ProcessBounds.unconstrained(),
        containment=frozenset({ContainmentCapability.FUME_HOOD}),
        ventilation=frozenset({VentilationCapability.INDOOR}),
        measurement=frozenset(MeasurementCapability),
        waste_handling=frozenset(WasteCapability),
        procurement=_NON_INDUSTRIAL_TIERS,
        budget=None,
        provenance=(
            "smartchem.capability.presets.research_lab() -- a well-equipped teaching/research bench "
            "preset (FREEZE decision 6): explicit apparatus + fume hood + non-industrial procurement; "
            "no declared material stock unless the caller supplies it"
        ),
    )


def poor_man(
    *,
    budget: "CostVector | None" = None,
    material_inventory: "tuple[StockMaterial, ...]" = (),
) -> CapabilityProfile:
    """A household/hardware-store bench on a declared budget (FREEZE decision 6): the low-resource
    equipment subset, NO containment (no fume hood -- the kitchen doesn't have one), outdoor ventilation
    (real, but never a containment substitute -- see F-nag), and the four kitchen-adjacent procurement
    tiers.

    ``budget`` defaults to ``CostVector(cash=200.0, currency="USD", unit="USD")`` -- a DEFAULT PARAMETER
    value, built fresh on every call, never a class-level/module-level constant a caller could accidentally
    share or mutate. Pass a different ``CostVector`` (or ``None`` for no ceiling) to override it.
    """
    resolved_budget = budget if budget is not None else CostVector(cash=200.0, currency="USD", unit="USD")
    return CapabilityProfile(
        schema_version=CAPABILITY_PROFILE_SCHEMA,
        profile_id="poor-man",
        material_inventory=tuple(material_inventory),
        equipment=_POOR_MAN_EQUIPMENT,
        physical_bounds=PhysicalBounds.unconstrained(),
        process_bounds=ProcessBounds.unconstrained(),
        containment=frozenset(),
        ventilation=frozenset({VentilationCapability.OUTDOOR}),
        measurement=frozenset({MeasurementCapability.FREE_OBSERVATION, MeasurementCapability.CHEAP_INSTRUMENT}),
        waste_handling=frozenset({WasteCapability.AQUEOUS_NEUTRAL}),
        procurement=_POOR_MAN_TIERS,
        budget=resolved_budget,
        provenance=(
            "smartchem.capability.presets.poor_man() -- a household/hardware-store bench preset (FREEZE "
            "decision 6): low-resource equipment, no containment, outdoor ventilation, kitchen-adjacent "
            "procurement tiers, a declared cash budget"
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
    measurement: "frozenset[MeasurementCapability]" = frozenset(),
    waste_handling: "frozenset[WasteCapability]" = frozenset(),
    procurement: "frozenset[Availability]" = frozenset(),
    budget: "CostVector | None" = None,
    provenance: str = "smartchem.capability.presets.custom() -- a fully explicit declared capability profile",
) -> CapabilityProfile:
    """The forcing tool (FREEZE decision 6): a fully-explicit passthrough of every ``CapabilityProfile``
    field, no hidden defaults doing anyone's thinking for them. This is how the gate #18 CAPABILITY_FIT
    positive gets built -- a caller who genuinely knows their bench (real declared ``StockMaterial`` stock,
    real glassware, a real fume hood) states it here, plainly, and ``assess()`` takes it at its word.

    Every keyword mirrors :class:`~smartchem.capability.profile.CapabilityProfile` one-for-one (only
    ``profile_id`` has no default -- every custom bench needs its own honest name); ``physical_bounds``/
    ``process_bounds`` default to unconstrained rather than sharing one frozen instance as a mutable
    default would risk (they are immutable ``Digestible`` values, but building fresh keeps this function's
    discipline identical to the two named presets above).
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
    )


#: the CLOSED preset registry (FREEZE decision 6/7): a NAME maps to a zero-argument builder, and NOTHING
#: else resolves a string into a profile -- no dynamic import, no ``getattr``, no ``eval``. Adding a new
#: named preset means adding a reviewed line here, on purpose, forever.
CAPABILITY_PROFILE_PRESETS: "dict[str, Callable[[], CapabilityProfile]]" = {
    "research-lab": research_lab,
    "poor-man": poor_man,
}


def resolve_capability_profile(spec: "str | CapabilityProfile") -> CapabilityProfile:
    """Resolve a preset NAME or an already-built :class:`CapabilityProfile` into one, closed-lookup only.

    **I'm the Meeseeks who refuses to improvise!** A ``str`` goes through :data:`CAPABILITY_PROFILE_PRESETS`
    -- an unrecognized name is a loud ``ValueError``, never a silent fallback and NEVER a dynamic
    ``importlib``/``eval`` reach into whatever module happens to share that name (FREEZE decision 6/7's
    hard rail). A :class:`CapabilityProfile` instance passes straight through unchanged -- a caller who
    already built one (including via :func:`custom`) never gets re-wrapped or re-validated twice.
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
