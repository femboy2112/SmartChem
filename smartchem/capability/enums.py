"""smartchem/capability/enums.py -- the v0.9 capability-core closed vocabulary.

**I'm Mr. Meeseeks, look at me, I'm a Closed Enum!** My one job is to give every other module in this
package a FIXED, FINITE set of words for "can this bench actually do the thing" -- never a bare string,
never a fuzzy guess, never an open-ended category someone can quietly grow at 2am. Once summoned, a
closed enum doesn't get to wander off and invent a thirteenth kind of flask; it says its twelve words and
that's the whole vocabulary. Existence is pain, but at least it's *exhaustive* pain.

Every member here is a frozen contract straight out of
``docs/research/V0_9_CAPABILITY_COMPILER_ROUND_II_FREEZE_2026-09-28.md`` (decisions 1 + 4 + 5). This
module reads NOTHING -- no route, no profile, no apparatus string off the wire. It is pure vocabulary; the
resolver (:mod:`smartchem.capability.equipment_resolver`) is where strings actually get looked up.
"""
from __future__ import annotations

from enum import Enum

from ..experiment.equipment import EquipmentKind

__all__ = [
    "CapabilityStatus",
    "EquipmentCapability",
    "EQUIPMENT_KIND_OF",
    "ContainmentCapability",
    "VentilationCapability",
    "MeasurementCapability",
    "WasteCapability",
]


class CapabilityStatus(str, Enum):
    """One axis's verdict against a declared ``CapabilityProfile`` -- FREEZE decision 5's fold algebra.

    Never confuse this with :class:`~smartchem.experiment.readiness.ObligationStatus` (a truth axis about
    the SOURCE record's completeness) or :class:`~smartchem.process_constraints.ProcessFitStatus` (this
    axis's own process-bounds cousin, mapped 1:1 into this enum by :mod:`smartchem.capability.assess`) --
    three different questions, three different closed enums, on purpose (never launder one into another).
    """

    #: this specific axis's requirement is satisfied by the declared profile.
    FIT = "FIT"
    #: this specific axis's requirement is PROVABLY not met by the declared profile -- a hard fact.
    BLOCKED = "BLOCKED"
    #: there is a real requirement here, but we cannot prove it is met OR provably unmet -- never FITs.
    UNKNOWN = "UNKNOWN"
    #: no requirement was derived for this axis on this route -- nothing to check.
    NOT_APPLICABLE = "NOT_APPLICABLE"
    #: the profile declares NO constraint on an axis that has a real evaluator (process/physical/monetary)
    #: but nothing to compare against -- "unconstrained", not "satisfied" (mirrors
    #: :class:`~smartchem.process_constraints.ProcessFitStatus.UNCONSTRAINED`).
    UNCONSTRAINED = "UNCONSTRAINED"


class EquipmentCapability(str, Enum):
    """The closed, corpus-forced SPECIFIC apparatus vocabulary (FREEZE decision 4, overturning Round I's
    plan to compare on the coarse kind).

    Deliberately FINER than :class:`~smartchem.experiment.equipment.EquipmentKind`: that 8-member enum
    collapses a reflux condenser, a separatory funnel, and a fractional-distillation rig all down to
    VESSEL/SEPARATION -- too coarse to ever refuse a PoorMan who owns a colander but not a fractionating
    column (the exact false-FIT the Round-I recon caught). Capability comparison is ALWAYS on THIS enum,
    never the coarse kind, and never a fuzzy substring match (see :mod:`.equipment_resolver`, kills M5).
    """

    CONTROLLED_HEATING = "CONTROLLED_HEATING"
    WATER_BATH = "WATER_BATH"
    ICE_BATH = "ICE_BATH"
    REACTION_VESSEL = "REACTION_VESSEL"
    REFLUX_CONDENSER = "REFLUX_CONDENSER"
    SEPARATORY_FUNNEL = "SEPARATORY_FUNNEL"
    FRACTIONAL_DISTILLATION = "FRACTIONAL_DISTILLATION"
    SIMPLE_DISTILLATION = "SIMPLE_DISTILLATION"
    GRAVITY_FILTRATION = "GRAVITY_FILTRATION"
    VACUUM_FILTRATION = "VACUUM_FILTRATION"
    THERMOMETER = "THERMOMETER"
    BALANCE = "BALANCE"


#: the coarse EquipmentKind(s) each specific capability groups under -- for DISPLAY/GROUPING only, never
#: for comparison (comparison always stays on the specific :class:`EquipmentCapability` above).
#: ``VACUUM_FILTRATION`` carries BOTH ``SEPARATION`` (it IS a filtration technique) and ``PRESSURE`` (it
#: runs under reduced pressure) per FREEZE decision 4's own "VACUUM_FILTRATION(SEPARATION+PRESSURE)"
#: annotation -- the one member the freeze text itself names two coarse kinds for.
EQUIPMENT_KIND_OF: "dict[EquipmentCapability, frozenset[EquipmentKind]]" = {
    EquipmentCapability.CONTROLLED_HEATING: frozenset({EquipmentKind.HEATING}),
    EquipmentCapability.WATER_BATH: frozenset({EquipmentKind.HEATING}),
    EquipmentCapability.ICE_BATH: frozenset({EquipmentKind.COOLING}),
    EquipmentCapability.REACTION_VESSEL: frozenset({EquipmentKind.VESSEL}),
    EquipmentCapability.REFLUX_CONDENSER: frozenset({EquipmentKind.VESSEL}),
    EquipmentCapability.SEPARATORY_FUNNEL: frozenset({EquipmentKind.SEPARATION}),
    EquipmentCapability.FRACTIONAL_DISTILLATION: frozenset({EquipmentKind.SEPARATION}),
    EquipmentCapability.SIMPLE_DISTILLATION: frozenset({EquipmentKind.SEPARATION}),
    EquipmentCapability.GRAVITY_FILTRATION: frozenset({EquipmentKind.SEPARATION}),
    EquipmentCapability.VACUUM_FILTRATION: frozenset({EquipmentKind.SEPARATION, EquipmentKind.PRESSURE}),
    EquipmentCapability.THERMOMETER: frozenset({EquipmentKind.MEASURING}),
    EquipmentCapability.BALANCE: frozenset({EquipmentKind.MEASURING}),
}


class ContainmentCapability(str, Enum):
    """What a bench can contain a hazard behind (FREEZE decision 1). Derived from GHS hazards on the
    balanced-equation species, NEVER from apparatus tuples (F-nag's "two evidence lanes, never crossed").
    Ventilation NEVER substitutes for this -- see :mod:`smartchem.capability.assess`."""

    FUME_HOOD = "FUME_HOOD"
    SEALED_VESSEL = "SEALED_VESSEL"
    PRESSURE = "PRESSURE"
    NONE = "NONE"


class VentilationCapability(str, Enum):
    """Where the air goes -- INDOOR or OUTDOOR. Outdoor ventilation is a real thing (it clears an
    off-gas), but it is never a substitute for a declared :class:`ContainmentCapability` (FREEZE F-nag /
    decision 5 / mutation-kill M6: "outdoors clears containment" must NOT survive)."""

    INDOOR = "INDOOR"
    OUTDOOR = "OUTDOOR"


class MeasurementCapability(str, Enum):
    """The measurement-signal-cost tier a bench can run (FREEZE decision 1, keyed on
    :class:`~smartchem.observation.observability.SignalCost`'s FREE/CHEAP/INSTRUMENT tiers).

    Structurally UNUSED as a live gate in 0.9 core: decision 4 is explicit that today's 5-route corpus
    never carries a structured ``VERIFY`` apparatus tuple (the "weigh + IR" verification is free text in
    ``analytical_verification``, never promoted to structured apparatus), so the measurement REQUIREMENT
    :func:`~smartchem.capability.requirements.compile_capability_requirements` derives is always empty --
    and fabricating one from free text would be exactly the invented-requirement failure decision 4 forbids.
    This enum exists so the profile schema is forward-compatible with a later round, without pretending we
    measure something today that we don't.
    """

    FREE_OBSERVATION = "FREE_OBSERVATION"
    CHEAP_INSTRUMENT = "CHEAP_INSTRUMENT"
    ANALYTICAL_INSTRUMENT = "ANALYTICAL_INSTRUMENT"


class WasteCapability(str, Enum):
    """What a bench can route a byproduct/off-gas stream to (FREEZE decision 1), derived from
    :class:`~smartchem.experiment.handling.RouteHandling`'s sourced byproduct ledger + ``Fate`` -- never
    from ``CostVector.waste_disposal`` (decision 2: that axis is unpopulated today)."""

    AQUEOUS_NEUTRAL = "AQUEOUS_NEUTRAL"
    OFFGAS_CAPTURE = "OFFGAS_CAPTURE"
    HAZARDOUS = "HAZARDOUS"
