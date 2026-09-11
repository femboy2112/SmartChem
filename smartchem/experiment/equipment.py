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
* every inferred item carries the triggering condition as its reason. A source-attested envelope yields
  ``KNOWN_SOURCED`` apparatus guidance; an operator declaration stays ``COMPOSABILITY`` and is never
  relabelled as scientific evidence.

This selects standard apparatus for the declared conditions.  It is not a claim the reaction proceeds, and
it never overrides a chemist's safety call -- it informs (fume-hood/containment items are attached from the
step's sourced hazards, inform-never-neuter, the same doctrine as the review layer).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
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
        provenance = f": {self.provenance}" if self.provenance else ""
        return (
            f"{self.name} ({self.kind.value.lower()}) -- {self.reason} "
            f"[{self.bucket.value}{provenance}]"
        )


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
        else:
            items.append(EquipmentItem(
                "controlled electric heater / furnace (open-flame compatibility UNASSESSED)",
                EquipmentKind.HEATING,
                f"heating to {temp.hi} K needs a temperature-rated source; free-text medium labels and "
                "species-level records are not a process flame-safety assessment, so no open flame is cleared",
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
    # (Catalyst OBTAINABILITY is gated separately in smartchem.experiment.catalyst_availability; a bare
    # `or envelope.catalysts` disjunct used to guard this branch but appended nothing under a catalyst-only
    # declaration -- a dead reference, removed so nothing here falsely reads as a catalyst gate.)
    if any(k in low_medium for k in ("anhydrous", "inert", "nitrogen", "argon", "air-sensitive", "schlenk")):
        items.append(EquipmentItem(
            "inert-gas line (N2/Ar) or Schlenk apparatus", EquipmentKind.ATMOSPHERE,
            "an anhydrous/inert/air-sensitive medium needs an inert atmosphere",
        ))

    if not envelope.is_sourced:
        return tuple(
            replace(
                item,
                bucket=Bucket.COMPOSABILITY,
                provenance=(
                    "apparatus inferred from an operator-declared condition constraint; the condition is "
                    "not source-attested"
                ),
            )
            for item in items
        )
    return tuple(
        replace(
            item,
            provenance=(
                f"{item.provenance}; triggering condition accepted from {envelope.source.locator}"
            ),
        )
        for item in items
    )


def equipment_for_step(step: ExperimentStep) -> tuple[EquipmentItem, ...]:
    """Envelope-inferred apparatus PLUS hazard-driven containment for the step's species.

    Adds a fume-hood/containment item when any species in the step carries a sourced hazard record --
    inform, never neuter (the review layer's doctrine): the chemist owns the safety call, and the tool
    surfaces the known reason for containment.
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    items = list(equipment_for_envelope(step.envelope))

    # hazard-driven containment (isomer-resolved via the review layer's molecule_hazards).  A positive
    # *benign* assessment such as water's empty GHS profile is evidence of assessment, not a reason to buy or
    # use a hood.  Conversely, any flammability code vetoes an open-flame suggestion even when the free-text
    # medium used an unrecognised alias (EtOH/IPA/etc.).
    from ..decompiler_review import molecule_hazards
    hazardous: list[str] = []
    flammable: list[str] = []
    flammable_codes = {"H220", "H221", "H222", "H223", "H224", "H225", "H226", "H227", "H228"}
    for m in (*step.reactants, *step.products):
        haz = molecule_hazards(m)
        if haz is not None and haz.ghs_codes:
            hazardous.append(haz.name)
            if flammable_codes.intersection(haz.ghs_codes):
                flammable.append(haz.name)
    if flammable:
        items = [i for i in items if "Bunsen" not in i.name and "open flame" not in i.name.lower()]
        if step.envelope.temperature is not None and step.envelope.temperature.hi > _WARM_K:
            names = ", ".join(sorted(set(flammable)))
            items.append(EquipmentItem(
                "controlled non-flame heating source", EquipmentKind.HEATING,
                f"sourced flammability classification for {names} vetoes an open flame",
                provenance="smartchem.data.hazards GHS flammability codes; process review still required",
            ))
    if hazardous:
        names = ", ".join(sorted(set(hazardous)))
        items.append(EquipmentItem(
            "fume hood (and appropriate PPE)", EquipmentKind.CONTAINMENT,
            f"sourced hazards present for: {names} -- work in a fume hood (inform, never neuter)",
            provenance="smartchem.data.hazards (CAMEO / NJ RTK / GHS); the chemist owns the safety call",
        ))
    return tuple(items)
