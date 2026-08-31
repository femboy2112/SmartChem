"""E6 -- the bench HANDLING profile: what a step throws off, and how much care running it needs.

The rungs above this one grade a reaction's *legitimacy* (conservation, composability, feasibility, rate).
This one answers the question a working chemist asks *before touching the flask*: what ELSE comes out of this
step besides the thing I want, where does it go, and can I set it running and walk away -- or does it make a
gas that is fatal to inhale, a reagent that reacts violently with water, or an intermediate that cannot be
stored?  It is the operator's ask made literal: track byproducts in general, flag the off-gasses, and separate
"reflux it and go to lunch" from "this one needs a hand on it the whole time."

It is an INTERPRETATION over sourced facts, never a new physics
----------------------------------------------------------------
This module adds no data and predicts nothing.  It composes three things that already exist, each sourced:

* :meth:`~smartchem.experiment.step.ExperimentStep.byproducts` -- the co-products the balanced equation
  already names (the amount per target is exact stoichiometry, a ``CONSERVATION`` fact);
* :mod:`smartchem.data.stability` (via :func:`~smartchem.experiment.composability.resolve_stability`) +
  :func:`~smartchem.experiment.phase.estimate_phase` -- whether a co-product is a GAS at the step's declared
  conditions (Clausius-Clapeyron over a sourced boiling point + enthalpy of vaporisation), and the flat
  sourced fact of whether a species is isolable at all;
* :mod:`smartchem.data.hazards` (via :func:`~smartchem.decompiler_review.molecule_hazards`) -- the sourced,
  isomer-specific GHS profile of every species present.

Doctrine, inherited verbatim from the hazard/stability layers and load-bearing
-----------------------------------------------------------------------------
* **Inform, never neuter.**  A handling profile ATTACHES facts; it never refuses or hides a step.  The chemist
  owns the decision.
* **UNKNOWN is not "safe".**  The safe verdict :attr:`CareLevel.PROCEED_UNATTENDED` is reachable ONLY when
  EVERY species present carries a positive (assessed) hazard record -- one unassessed species holds the step
  at :attr:`CareLevel.UNKNOWN`, never a green light over ignorance.  This is the same non-vacuity guard E1's
  ``COMPOSABLE`` uses, and the same "vacuous green over an empty subject" disease it is written against.
* **A known hazard is never masked by an unknown one.**  The care level is worst-dominated over sourced facts
  (``NEEDS_ACTIVE_CONTROL`` > ``ATTENTION_ADVISED`` > ``UNKNOWN`` > ``PROCEED_UNATTENDED``), so a step with a
  known corrosive AND an unassessed exotic reports ``ATTENTION_ADVISED`` (the actionable floor) WITH the
  unassessed species listed loudly -- never a bare ``UNKNOWN`` that would bury the corrosive.
* **Isomer-specific.**  Hazards and stability belong to a compound, not a bare formula; resolution is
  structure-registry-keyed (an unresolved structure is UNASSESSED, never attached a same-formula stranger's
  record -- the "borrows a value by formula" failure this repo has caught before).

W3 unchanged: this says what is KNOWN about what comes off a step and how it must be handled; it never claims
the step proceeds, at what rate, or in what yield.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from ..category import Molecule
from ..contracts import Digestible, canonical_digest
from ..data.hazards import HazardRef
from ..data.stability import DEFAULT_STABILITY, StabilityRef, StabilityTable
from ..decompiler import Formula
from ..decompiler_review import molecule_hazards
from .bucket import Bucket, Quantity
from .composability import resolve_stability
from .dag import SynthesisDAG
from .phase import estimate_phase
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "Fate",
    "CareLevel",
    "ByproductEntry",
    "HazardFlag",
    "StepHandling",
    "RouteHandling",
    "handling_of_step",
    "handling_of_dag",
    "verify_handling",
]

#: GHS physical-hazard codes that classify a substance AS A GAS at ambient conditions (a sourced statement of
#: physical state, independent of any Clausius-Clapeyron estimate): H220/H221 flammable gas, H230/H231
#: chemically-unstable gas, H280/H281 gas under pressure / refrigerated gas.
_GHS_GAS_CODES = frozenset({"H220", "H221", "H230", "H231", "H280", "H281"})
#: Acute-inhalation-lethal codes: an OFF-GAS carrying one of these is a TOXIC off-gas (control-level).
_GHS_TOXIC_INHALATION = frozenset({"H330", "H331"})  # H330 fatal / H331 toxic if inhaled
#: Flammable-gas codes: an OFF-GAS carrying one is an ignition + pressure hazard (control-level).
_GHS_FLAMMABLE_GAS = frozenset({"H220", "H221"})
#: A default bench pressure (atm) assumed for the phase estimate when a step declares none -- stated, not
#: silent; the pressure correction to an off-gas call is minor near 1 atm.
_DEFAULT_PRESSURE_ATM = 1.0


class Fate(str, Enum):
    """Where a co-product ends up under the step's declared conditions -- a SOURCED phase call, or a gap."""

    OFFGAS = "OFFGAS"        # a gas at the step's (T, P): it evolves and must be vented/contained
    CONDENSED = "CONDENSED"  # a liquid or solid: it stays in the pot (to separate / dispose)
    UNKNOWN = "UNKNOWN"      # no sourced phase data (no bp+dHvap, no GHS gas class) -- a loud gap, never "safe"


class CareLevel(str, Enum):
    """How much attention running this step needs -- worst-dominated over SOURCED handling facts.

    The ordering is by precedence (see :data:`_CARE_LADDER`): a NAMED sourced danger outranks a milder known
    hazard, which outranks an unassessed gap, which outranks the clean pass -- and the clean pass is reachable
    ONLY when every species present is positively assessed (UNKNOWN is not "safe").
    """

    NEEDS_ACTIVE_CONTROL = "NEEDS_ACTIVE_CONTROL"  # a sourced fact demands a hand on it: toxic/flammable
    #                                                off-gas, a non-isolable in-situ species, or a species that
    #                                                decomposes at the operating temperature
    ATTENTION_ADVISED = "ATTENTION_ADVISED"        # a sourced hazard is present (corrosive, toxic, carcinogen,
    #                                                harmful-if-inhaled) -- PPE / fume hood, but not a
    #                                                walk-away blocker on its own
    UNKNOWN = "UNKNOWN"                            # at least one species present is UNASSESSED -- cannot
    #                                                certify either way (never a false "safe")
    PROCEED_UNATTENDED = "PROCEED_UNATTENDED"      # every species assessed AND benign: no dangerous off-gas,
    #                                                all isolable, no known hazard -- it can run unattended


#: Precedence used to aggregate a route/DAG worst-step-dominated (higher wins).
_CARE_LADDER: dict[CareLevel, int] = {
    CareLevel.PROCEED_UNATTENDED: 0,
    CareLevel.UNKNOWN: 1,
    CareLevel.ATTENTION_ADVISED: 2,
    CareLevel.NEEDS_ACTIVE_CONTROL: 3,
}


def _ident(molecule: Molecule) -> str:
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(molecule)


def _formula_str(molecule: Molecule) -> str:
    return repr(Formula.of(molecule.formula, molecule.charge))


def _resolve_hazard(molecule: Molecule) -> HazardRef | None:
    """The sourced hazard record for ``molecule``, isomer-resolved through the structure registry, or ``None``.

    Deliberately NAME-resolved only (never a formula-level fallback): attaching a single recorded isomer's
    hazards to an unresolved same-formula molecule would be the "borrows a value by formula" false attach this
    repo has caught before.  An unresolved structure is UNASSESSED (a loud gap), never a stranger's record.
    """
    return molecule_hazards(molecule)


def _step_conditions(step: ExperimentStep, temperature_k: float | None, pressure_atm: float | None):
    """The (temperature K, pressure atm, temperature_declared) to place phases at for this step.

    An explicit ``temperature_k`` / ``pressure_atm`` override wins; else the step's declared envelope is used
    (its temperature high bound -- a co-product that is a gas at any point of the range evolves); an undeclared
    pressure defaults to :data:`_DEFAULT_PRESSURE_ATM` (stated).  ``temperature_declared`` is False when no
    temperature is known, so a Clausius-Clapeyron phase call is skipped rather than guessed.
    """
    env = step.envelope
    if temperature_k is not None:
        temp, temp_declared = temperature_k, True
    elif env.temperature is not None:
        temp, temp_declared = env.temperature.hi, True
    else:
        temp, temp_declared = None, False
    if pressure_atm is not None:
        press = pressure_atm
    elif env.pressure is not None:
        press = (env.pressure.lo + env.pressure.hi) / 2.0
    else:
        press = _DEFAULT_PRESSURE_ATM
    return temp, press, temp_declared


def _fate_of(
    molecule: Molecule,
    hazard: HazardRef | None,
    rec: StabilityRef | None,
    temp: float | None,
    press: float,
    temp_declared: bool,
) -> tuple[Fate, str]:
    """The sourced fate of one co-product: OFFGAS / CONDENSED / UNKNOWN, with the fact that decided it.

    Two independent sourced signals mark a gas: (1) a GHS gas-class code (a sourced statement of physical
    state), (2) the Clausius-Clapeyron phase estimate placing it as a gas at the step's (T, P).  Only the
    Clausius-Clapeyron estimate can affirm CONDENSED; absent both, the fate is a loud UNKNOWN.
    """
    if hazard is not None and (set(hazard.ghs_codes) & _GHS_GAS_CODES):
        codes = ", ".join(sorted(set(hazard.ghs_codes) & _GHS_GAS_CODES))
        return Fate.OFFGAS, f"a gas by sourced GHS classification ({codes}: {hazard.name})"
    if rec is not None and temp_declared and temp is not None:
        phase = estimate_phase(rec, temp, press)
        if phase == "gas":
            return Fate.OFFGAS, (
                f"a gas at {temp:.0f} K / {press:g} atm (Clausius-Clapeyron over sourced bp"
                + (f" + dHvap {rec.dhvap_kj_per_mol} kJ/mol" if rec.dhvap_kj_per_mol is not None else "")
                + f"; {rec.name})"
            )
        if phase in ("liquid", "solid"):
            return Fate.CONDENSED, f"{phase} at {temp:.0f} K / {press:g} atm (sourced thresholds; {rec.name})"
    return Fate.UNKNOWN, "phase UNASSESSED (no sourced bp+dHvap and no GHS gas classification) -- a loud gap"


@dataclass(frozen=True)
class ByproductEntry(Digestible):
    """One co-product of a step: its identity, exact amount per target, sourced fate, and any hazard.

    ``moles_per_target`` is the exact stoichiometric ratio from the balanced equation (a ``CONSERVATION``
    fact -- how much of this comes off per mole of the thing you want).  ``fate`` is the sourced phase call;
    ``hazard_name`` is the resolved hazard record's compound name (``None`` if unassessed).
    """

    molecule: Molecule
    moles_per_target: Fraction
    fate: Fate
    hazard_name: str | None
    reason: str

    def __post_init__(self) -> None:
        if type(self.molecule) is not Molecule:
            raise TypeError("molecule must be a Molecule")
        if type(self.moles_per_target) is not Fraction or self.moles_per_target <= 0:
            raise ValueError("moles_per_target must be a positive Fraction")
        if not isinstance(self.fate, Fate):
            raise TypeError("fate must be a Fate")

    @property
    def is_offgas(self) -> bool:
        return self.fate is Fate.OFFGAS


@dataclass(frozen=True)
class HazardFlag(Digestible):
    """A sourced hazard on one species present in a step, with the role it plays (input vs. co-product)."""

    name: str
    role: str  # "reagent" / "reactant" / "target" / "byproduct"
    ghs_codes: tuple[str, ...]
    summary: str
    provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if type(self.ghs_codes) is not tuple:
            raise TypeError("ghs_codes must be a tuple")


@dataclass(frozen=True)
class StepHandling(Digestible):
    """The bench handling profile of ONE step: its byproduct ledger, off-gasses, hazards, and care level."""

    step: ExperimentStep
    byproducts: tuple[ByproductEntry, ...]   # the general co-product ledger (every product but the target)
    hazards: tuple[HazardFlag, ...]          # sourced hazards on ANY species present (inputs and outputs)
    unassessed: tuple[str, ...]              # species present with NO sourced hazard record (the loud gaps)
    care: CareLevel
    care_reasons: tuple[str, ...]            # the NAMED sourced facts (and gaps) that set `care`
    finding: Quantity

    def __post_init__(self) -> None:
        if type(self.step) is not ExperimentStep:
            raise TypeError("step must be an ExperimentStep")
        if not isinstance(self.care, CareLevel):
            raise TypeError("care must be a CareLevel")

    @property
    def offgases(self) -> tuple[ByproductEntry, ...]:
        """The byproducts whose sourced fate is a gas -- what evolves and must be vented/contained."""
        return tuple(b for b in self.byproducts if b.is_offgas)

    @property
    def toxic_offgases(self) -> tuple[ByproductEntry, ...]:
        """The off-gasses carrying a sourced acute-inhalation code (fatal/toxic if inhaled)."""
        out = []
        for b in self.offgases:
            haz = _hazard_by_name(self.hazards, b.hazard_name)
            if haz is not None and (set(haz.ghs_codes) & _GHS_TOXIC_INHALATION):
                out.append(b)
        return tuple(out)

    def explain(self) -> str:
        lines = [f"handling: {self.care.value}"]
        if self.byproducts:
            lines.append("  byproducts:")
            for b in self.byproducts:
                haz = f" [{b.hazard_name}]" if b.hazard_name else " [hazard UNASSESSED]"
                lines.append(f"    {b.moles_per_target} x {b.molecule!r} -- {b.fate.value}{haz}")
        else:
            lines.append("  byproducts: none (single-product step)")
        for r in self.care_reasons:
            lines.append(f"  - {r}")
        if self.unassessed:
            lines.append(f"  UNASSESSED species (hazard unknown, not cleared): {', '.join(self.unassessed)}")
        return "\n".join(lines)


def _hazard_by_name(hazards: tuple[HazardFlag, ...], name: str | None) -> HazardFlag | None:
    if name is None:
        return None
    for h in hazards:
        if h.name == name:
            return h
    return None


def _role_of(ident: str, step: ExperimentStep) -> str:
    tgt = _ident(step.target)
    reactant_idents = {_ident(m) for m in step.reactants}
    product_idents = {_ident(m) for m in step.products}
    reagent_idents = {_ident(m) for m in step.reagents}
    if ident == tgt:
        return "target"
    if ident in product_idents and ident not in reactant_idents:
        return "byproduct"
    if ident in reagent_idents:
        return "reagent"
    if ident in reactant_idents:
        return "reactant"
    return "species"


def handling_of_step(
    step: ExperimentStep,
    *,
    stability: StabilityTable = DEFAULT_STABILITY,
    temperature_k: float | None = None,
    pressure_atm: float | None = None,
) -> StepHandling:
    """The bench handling profile of one step: byproduct ledger + off-gasses + hazards + care level.

    Every number and flag is sourced or a loud UNKNOWN; nothing is predicted.  ``stability`` may be an extended
    table (:meth:`~smartchem.data.stability.StabilityTable.with_records`) to bring phase thresholds for a
    compound the seed does not carry; ``temperature_k`` / ``pressure_atm`` override the step's declared
    conditions for the phase (off-gas) estimate.
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    temp, press, temp_declared = _step_conditions(step, temperature_k, pressure_atm)

    # -- the byproduct ledger (general): every co-product, exact amount per target, sourced fate ----------
    prod_counts = Counter(_ident(m) for m in step.products)
    tgt_coeff = prod_counts[_ident(step.target)]  # >= 1 (E0 guarantees the target is a product)
    seen: dict[str, Molecule] = {}
    counts: Counter = Counter()
    for m in step.byproducts:
        key = _ident(m)
        counts[key] += 1
        seen.setdefault(key, m)
    byproducts: list[ByproductEntry] = []
    for key, mol in seen.items():
        haz = _resolve_hazard(mol)
        rec = resolve_stability(mol, stability)
        fate, fate_reason = _fate_of(mol, haz, rec, temp, press, temp_declared)
        byproducts.append(ByproductEntry(
            molecule=mol,
            moles_per_target=Fraction(counts[key], tgt_coeff),
            fate=fate,
            hazard_name=haz.name if haz is not None else None,
            reason=fate_reason,
        ))

    # -- hazards on ANY species present (inputs AND outputs), and the unassessed gaps --------------------
    present: dict[str, Molecule] = {}
    for m in (*step.reactants, *step.products):
        present.setdefault(_ident(m), m)
    hazards: list[HazardFlag] = []
    unassessed: list[str] = []
    control_reasons: list[str] = []
    attention_reasons: list[str] = []
    for key, mol in present.items():
        haz = _resolve_hazard(mol)
        rec = resolve_stability(mol, stability)
        role = _role_of(key, step)
        # -- sourced control triggers on this species (named facts) --------------------------------------
        if rec is not None and not rec.isolable:
            control_reasons.append(
                f"{rec.name} ({role}) is NON-ISOLABLE -- generated/consumed in situ, so this step must be run "
                f"with it under active control ({rec.provenance})"
            )
        if (
            rec is not None and rec.decomposition_onset is not None
            and temp_declared and temp is not None and rec.decomposition_onset.lo <= temp
        ):
            control_reasons.append(
                f"{rec.name} ({role}) decomposes at >= {rec.decomposition_onset.lo:.0f} K, at/below the "
                f"operating {temp:.0f} K -- thermal-instability risk, do not leave it to sit ({rec.provenance})"
            )
        if haz is None:
            unassessed.append(f"{mol!r} ({role})")
            continue
        hazards.append(HazardFlag(
            name=haz.name, role=role, ghs_codes=tuple(haz.ghs_codes),
            summary=haz.summary, provenance=haz.provenance,
        ))
        if haz.ghs_codes:  # a non-empty GHS profile is a real (attention-level) hazard present
            attention_reasons.append(
                f"{haz.name} ({role}): {haz.summary} [GHS {', '.join(haz.ghs_codes)}]"
            )

    # -- toxic / flammable OFF-GAS is a control-level trigger (over the byproduct ledger) ----------------
    for b in byproducts:
        if not b.is_offgas or b.hazard_name is None:
            continue
        haz = _resolve_hazard(b.molecule)
        if haz is None:
            continue
        codes = set(haz.ghs_codes)
        if codes & _GHS_TOXIC_INHALATION:
            which = ", ".join(sorted(codes & _GHS_TOXIC_INHALATION))
            control_reasons.append(
                f"{haz.name} evolves as a TOXIC off-gas ({which}) -- vent/scrub and do not seal or leave "
                f"unattended ({haz.provenance})"
            )
        elif codes & _GHS_FLAMMABLE_GAS:
            which = ", ".join(sorted(codes & _GHS_FLAMMABLE_GAS))
            control_reasons.append(
                f"{haz.name} evolves as a FLAMMABLE off-gas ({which}) -- ignition and pressure hazard, "
                f"needs venting/inerting under control ({haz.provenance})"
            )

    # -- the worst-dominated care level (a known hazard never masked by an unknown; UNKNOWN never "safe") -
    if control_reasons:
        care = CareLevel.NEEDS_ACTIVE_CONTROL
        reasons = tuple(control_reasons)
    elif attention_reasons:
        care = CareLevel.ATTENTION_ADVISED
        reasons = tuple(attention_reasons)
    elif unassessed:
        care = CareLevel.UNKNOWN
        reasons = (
            "no sourced hazard for at least one species present, so this step cannot be certified safe to "
            "leave unattended (UNKNOWN is not 'safe')",
        )
    else:
        care = CareLevel.PROCEED_UNATTENDED
        reasons = (
            "every species present carries a positive (assessed) hazard record and none triggers active "
            "control -- no dangerous off-gas, all isolable, no known hazard: it can run unattended",
        )
    if unassessed and care is not CareLevel.UNKNOWN:  # surface the gaps even when a known hazard dominates
        reasons = (*reasons, f"NOTE: {len(unassessed)} species unassessed -- the true care level may be higher")

    provenance = (
        "worst-dominated over sourced byproduct fate + GHS hazard + stability facts; "
        f"{len(byproducts)} byproduct(s), {len([b for b in byproducts if b.is_offgas])} off-gas(es), "
        f"{len(hazards)} sourced hazard(s), {len(unassessed)} unassessed"
    )
    if care is CareLevel.UNKNOWN:  # the bucket contract refuses a value under UNKNOWN -- state None, loudly
        finding = Quantity(
            label="handling-care-level", value=None, unit="", bucket=Bucket.UNKNOWN,
            provenance=f"UNKNOWN care -- {provenance}",
        )
    else:  # a determinate care verdict, grounded in sourced hazard/stability data
        finding = Quantity(
            label="handling-care-level", value=care.value, unit="", bucket=Bucket.KNOWN_SOURCED,
            provenance=provenance,
        )
    return StepHandling(step, tuple(byproducts), tuple(hazards), tuple(unassessed), care, reasons, finding)


def _aggregate_care(levels: tuple[CareLevel, ...]) -> CareLevel:
    """The worst-step-dominated care level over a route/DAG (max on the precedence ladder)."""
    return max(levels, key=lambda c: _CARE_LADDER[c])


@dataclass(frozen=True)
class RouteHandling(Digestible):
    """The handling profile of a whole synthesis: per-step profiles, and the worst-dominated care level.

    :attr:`care` is the worst care level any step demands (a synthesis is only as walk-away-able as its most
    demanding step); :attr:`all_offgases` and :attr:`all_byproducts` are the full inventories across every
    step -- what a chemist running the WHOLE route will have to vent, separate, and dispose of.
    """

    steps: tuple[StepHandling, ...]

    def __post_init__(self) -> None:
        if type(self.steps) is not tuple or not self.steps or any(
            type(s) is not StepHandling for s in self.steps
        ):
            raise TypeError("steps must be a non-empty tuple of StepHandling values")

    @property
    def care(self) -> CareLevel:
        return _aggregate_care(tuple(s.care for s in self.steps))

    @property
    def all_byproducts(self) -> tuple[ByproductEntry, ...]:
        return tuple(b for s in self.steps for b in s.byproducts)

    @property
    def all_offgases(self) -> tuple[ByproductEntry, ...]:
        return tuple(b for s in self.steps for b in s.offgases)

    @property
    def unassessed(self) -> tuple[str, ...]:
        return tuple(u for s in self.steps for u in s.unassessed)

    def explain(self) -> str:
        lines = [f"handling (whole synthesis; most demanding step dominates): {self.care.value}"]
        for idx, s in enumerate(self.steps):
            lines.append(f"  step {idx + 1}: {s.care.value}"
                         + (f" -- off-gasses: {', '.join(b.molecule.__repr__() for b in s.offgases)}"
                            if s.offgases else ""))
        return "\n".join(lines)


def verify_handling(
    route: ExperimentRoute,
    *,
    stability: StabilityTable = DEFAULT_STABILITY,
    temperature_k: float | None = None,
    pressure_atm: float | None = None,
) -> RouteHandling:
    """The bench handling profile of every step of a linear route, and the worst-dominated care level."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    per = tuple(
        handling_of_step(s, stability=stability, temperature_k=temperature_k, pressure_atm=pressure_atm)
        for s in route.steps
    )
    return RouteHandling(per)


def handling_of_dag(
    dag: SynthesisDAG,
    *,
    stability: StabilityTable = DEFAULT_STABILITY,
    temperature_k: float | None = None,
    pressure_atm: float | None = None,
) -> RouteHandling:
    """The bench handling profile of every step of a convergent DAG, and the worst-dominated care level."""
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    per = tuple(
        handling_of_step(s, stability=stability, temperature_k=temperature_k, pressure_atm=pressure_atm)
        for s in dag.steps
    )
    return RouteHandling(per)
