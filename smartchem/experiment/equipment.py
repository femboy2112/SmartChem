"""E4's equipment layer -- turn declared conditions into the apparatus a chemist reaches for.

The operator's bar: *"a chemist should look at what we produce and immediately have it click -- ok, this
needs a Bunsen and a few flasks, this needs a volumetric."*  That mapping -- from a step's DECLARED
conditions to the standard bench apparatus -- is established laboratory practice, so this module reproduces
it, item by item, each tagged with the exact condition that called for it.

Universal, and honest at the edges
----------------------------------
Equipment is inferred from the :class:`~smartchem.conditions.ConditionEnvelope`, NOT from a per-compound
table, so it works for ANY chemical: the conditions drive the glassware.  Two honesty rules hold:

* an UNDECLARED envelope yields a single ``UNKNOWN`` item -- *equipment undetermined, no declared
  conditions* -- never a guessed apparatus;
* every inferred item is ``KNOWN_SOURCED`` to standard practice and carries the triggering condition as its
  reason, so a chemist sees *why* each piece is on the list and can overrule it with their own judgement.

This selects standard apparatus for the declared conditions.  It is not a claim the reaction proceeds, and
it never overrides a chemist's safety call -- it informs (fume-hood/containment items are attached from the
step's sourced hazards, inform-never-neuter, the same doctrine as the review layer).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..conditions import ConditionEnvelope
from ..contracts import Digestible
from .bucket import Bucket
from .step import ExperimentStep

__all__ = [
    "EquipmentKind",
    "EquipmentItem",
    "equipment_for_envelope",
    "equipment_for_step",
]

# -- sourced thresholds for the condition->apparatus mapping (standard bench practice) ---------------
_AMBIENT_K = 298.15
_WARM_K = 313.0            # ~40 C: above here, active heating is needed
_WATER_BATH_MAX_K = 373.0  # ~100 C: a water bath / hotplate covers up to boiling water
_STRONG_FLAME_MAX_K = 1773.0  # a Bunsen burner reaches ~1500 C
_SUBAMBIENT_K = 288.0     # ~15 C: below here, a cooling/ice bath is needed
_ELEVATED_ATM = 1.5       # above here, a sealed/pressure vessel
_VACUUM_ATM = 0.5         # below here, a vacuum line
_STD = "standard laboratory practice (Vogel's Practical Organic Chemistry; standard bench technique)"
_FLAMMABLE_HINTS = ("ethanol", "ether", "acetone", "methanol", "organic", "neat", "hexane", "toluene", "thf")


class EquipmentKind(str, Enum):
    HEATING = "HEATING"
    COOLING = "COOLING"
    VESSEL = "VESSEL"
    MEASURING = "MEASURING"
    PRESSURE = "PRESSURE"
    SEPARATION = "SEPARATION"
    ATMOSPHERE = "ATMOSPHERE"
    CONTAINMENT = "CONTAINMENT"


@dataclass(frozen=True)
class EquipmentItem(Digestible):
    """One piece of apparatus, the condition that called for it, and its evidence bucket."""

    name: str
    kind: EquipmentKind
    reason: str
    bucket: Bucket = Bucket.KNOWN_SOURCED
    provenance: str = _STD

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("equipment name must be a non-empty string")
        if not isinstance(self.kind, EquipmentKind):
            raise TypeError("kind must be an EquipmentKind")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string (the triggering condition)")

    def render(self) -> str:
        return f"{self.name} ({self.kind.value.lower()}) -- {self.reason}"


def _flammable(medium: str) -> bool:
    low = medium.lower()
    return any(h in low for h in _FLAMMABLE_HINTS)


def equipment_for_envelope(envelope: ConditionEnvelope) -> tuple[EquipmentItem, ...]:
    """Infer the standard apparatus a chemist needs for one step's DECLARED conditions.

    Returns a single ``UNKNOWN``-bucket item when nothing is declared (equipment undetermined), never a
    guess.  Works for any chemical -- the conditions, not the compound, drive the list.
    """
    if type(envelope) is not ConditionEnvelope:
        raise TypeError("envelope must be a ConditionEnvelope")
    if not envelope.is_declared:
        return (EquipmentItem(
            "equipment undetermined", EquipmentKind.VESSEL,
            "no declared conditions -- inject a sourced envelope to infer apparatus",
            bucket=Bucket.UNKNOWN, provenance="no declared conditions",
        ),)

    items: list[EquipmentItem] = []
    medium = envelope.medium
    flammable = _flammable(medium)

    # -- a reaction vessel, always; its kind depends on whether it is heated under reflux -----------
    temp = envelope.temperature
    heated = temp is not None and temp.hi > _WARM_K
    if heated and temp.hi > _WATER_BATH_MAX_K and medium:
        items.append(EquipmentItem(
            "round-bottom flask with reflux condenser", EquipmentKind.VESSEL,
            f"a liquid medium heated to {temp.hi} K needs reflux to avoid boil-off",
        ))
    else:
        items.append(EquipmentItem(
            "reaction flask (Erlenmeyer or round-bottom) + a few beakers", EquipmentKind.VESSEL,
            "every bench step needs a vessel; a flask and a few beakers cover a standard prep",
        ))

    # -- heating -----------------------------------------------------------------------------------
    if heated:
        if temp.hi <= _WATER_BATH_MAX_K:
            items.append(EquipmentItem(
                "hotplate or water bath", EquipmentKind.HEATING,
                f"gentle heating to {temp.hi} K (<=100 C) is a water bath / hotplate job",
            ))
        elif flammable:
            items.append(EquipmentItem(
                "heating mantle or hotplate (NO open flame -- flammable medium)", EquipmentKind.HEATING,
                f"heating a flammable medium to {temp.hi} K: a mantle/hotplate, not a burner",
            ))
        elif temp.hi <= _STRONG_FLAME_MAX_K:
            items.append(EquipmentItem(
                "Bunsen burner", EquipmentKind.HEATING,
                f"strong heating to {temp.hi} K in a non-flammable medium -- a burner reaches this",
            ))
        else:
            items.append(EquipmentItem(
                "furnace / high-temperature source", EquipmentKind.HEATING,
                f"{temp.hi} K exceeds a Bunsen burner's ~1500 C reach -- a furnace is needed",
            ))

    # -- cooling -----------------------------------------------------------------------------------
    if temp is not None and temp.lo < _SUBAMBIENT_K:
        items.append(EquipmentItem(
            "ice bath or cooling bath", EquipmentKind.COOLING,
            f"a declared low of {temp.lo} K (<15 C) needs active cooling",
        ))

    # -- pressure ----------------------------------------------------------------------------------
    pres = envelope.pressure
    if pres is not None and pres.hi > _ELEVATED_ATM:
        items.append(EquipmentItem(
            "sealed pressure vessel / autoclave", EquipmentKind.PRESSURE,
            f"a declared pressure up to {pres.hi} atm (>1.5 atm) needs a sealed vessel",
        ))
    if pres is not None and pres.lo < _VACUUM_ATM:
        items.append(EquipmentItem(
            "vacuum line / rotary evaporator", EquipmentKind.PRESSURE,
            f"a declared low pressure of {pres.lo} atm (<0.5 atm) needs a vacuum source",
        ))

    # -- measuring / solution prep -----------------------------------------------------------------
    low_medium = medium.lower()
    if any(k in low_medium for k in ("aqueous", "solution", "molar", "volumetric", "titr", "dilut")):
        items.append(EquipmentItem(
            "volumetric flask, graduated cylinder, pipette + balance", EquipmentKind.MEASURING,
            "a solution/aqueous medium implies volumetric make-up and weighing",
        ))

    # -- inert atmosphere --------------------------------------------------------------------------
    if any(k in low_medium for k in ("anhydrous", "inert", "nitrogen", "argon", "air-sensitive", "schlenk")) \
            or envelope.catalysts:
        if any(k in low_medium for k in ("anhydrous", "inert", "nitrogen", "argon", "air-sensitive", "schlenk")):
            items.append(EquipmentItem(
                "inert-gas line (N2/Ar) or Schlenk apparatus", EquipmentKind.ATMOSPHERE,
                "an anhydrous/inert/air-sensitive medium needs an inert atmosphere",
            ))

    return tuple(items)


def equipment_for_step(step: ExperimentStep) -> tuple[EquipmentItem, ...]:
    """Envelope-inferred apparatus PLUS hazard-driven containment for the step's species.

    Adds a fume-hood/containment item when any species in the step carries a sourced hazard record --
    inform, never neuter (the review layer's doctrine): the chemist owns the safety call, and the tool
    surfaces the known reason for containment.
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    items = list(equipment_for_envelope(step.envelope))

    # hazard-driven containment (isomer-resolved via the review layer's molecule_hazards)
    from ..decompiler_review import molecule_hazards
    hazardous: list[str] = []
    for m in (*step.reactants, *step.products):
        haz = molecule_hazards(m)
        if haz is not None:
            hazardous.append(haz.name)
    if hazardous:
        names = ", ".join(sorted(set(hazardous)))
        items.append(EquipmentItem(
            "fume hood (and appropriate PPE)", EquipmentKind.CONTAINMENT,
            f"sourced hazards present for: {names} -- work in a fume hood (inform, never neuter)",
            provenance="smartchem.data.hazards (CAMEO / NJ RTK / GHS); the chemist owns the safety call",
        ))
    return tuple(items)
