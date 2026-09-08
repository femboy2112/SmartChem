"""E1 -- the composability verifier: does each intermediate survive the transition to the next step?

This is the executable form of the operator's degeneracy test -- *"a mid-reaction chemical that will not
survive the transition to the next step's conditions makes the pathway degenerate."*  It is
CONSTRAINT SATISFACTION over SOURCED stability windows, not a prediction about chemistry:

* a route's intermediate is the target of one step, carried into the next (the E0 route linearity guard);
* the transition between them subjects that intermediate to the DECLARED conditions of both steps;
* :mod:`smartchem.data.stability` supplies the intermediate's SOURCED thresholds -- a decomposition onset,
  or the flat fact that it is never isolable;
* the verdict is a comparison of those two SOURCED facts.  ``DEGENERATE`` means the declared conditions and
  the sourced threshold *contradict*; it is a logical refusal, a ``COMPOSABILITY``-bucket fact, never a
  claim about what the molecule does.

The three honest verdicts, and the non-vacuity guard (W2)
--------------------------------------------------------
A transition is ``COMPOSABLE`` (affirmatively cleared against sourced data), ``DEGENERATE`` (affirmatively
refuted against sourced data), or ``UNKNOWN`` (no sourced threshold to judge it -- a LOUD gap, never read as
"fine").  The whole route's verdict then follows, and it is guarded against the repo's recurring "vacuous
green over an empty subject" disease:

* ``SINGLE_STEP`` -- a route with NO transitions.  There is nothing to compose, so it is never reported as
  ``COMPOSABLE``; that would be a green light over an empty subject.
* ``DEGENERATE`` -- at least one transition is degenerate.
* ``COMPOSABLE`` -- at least one transition, and EVERY transition was affirmatively cleared on sourced data.
* ``UNKNOWN`` -- at least one transition, none degenerate, but at least one could not be judged (a gap).
  The handoff is not transition-cleared; this is ``UNKNOWN``, never a silent pass.

Independence (why this is not self-certifying)
----------------------------------------------
The thresholds come from a SEPARATE sourced table, not from the route's own declaration.  The check
compares the route's declared envelopes against externally-sourced facts, so a route cannot certify its own
composability.

Duration awareness (DURATION-SURVIVAL-01)
-----------------------------------------
The onset test is INSTANTANEOUS -- it asks only whether an exposure stays below a decomposition ONSET, not how
LONG the intermediate is held.  Where a DAG's serial schedule imposes a sourced HOLD (DAG-HOLD-01) AND the
intermediate has a SOURCED first-order decomposition rate (:mod:`smartchem.experiment.stability_horizon`,
matched on CANONICAL STRUCTURE), :func:`_apply_duration_gate` reads the surviving fraction over that hold's
intervening steps at their OWN declared temperatures (the temperatures the intermediate actually idles at -- NOT
a producer/consumer endpoint's, and fail-closed if any intervening temperature is undeclared) and lets it MOVE
the verdict: majority-destroyed -> ``DEGENERATE`` (even where the onset table was silent), a marginal survival ->
``UNKNOWN``, a clean survival confirms the instantaneous verdict without upgrading it.  It only ever TIGHTENS;
where no rate is sourced (the common case) the hold stays a pure disclosure, exactly as before.  A whole route's
composite survival is the PRODUCT of the assessed per-transition fractions -- ``route_surviving_fraction``, the
survival monoid functor ``S: Process -> ([0, 1], x)`` on the composite.

The stated boundary (a sourced-model gap, not a silent guess)
-------------------------------------------------------------
Temperature-vs-decomposition and non-isolability are the hard teeth.  Pressure is reported honestly as a
declared-condition change but is NOT turned into a survival verdict: a boiling point's shift with pressure
(Clausius-Clapeyron) is a sourced-model gap E1 does not attempt.  A caller who has sourced pressure
tolerance injects it and extends the check; unassessed pressure stays a noted ``UNKNOWN``, never "fine".
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..category import Molecule
from ..conditions import ConditionEnvelope, Interval
from ..contracts import Digestible
from ..data.kinetics import DEFAULT_KINETICS, KineticRef, KineticTable
from ..data.stability import DEFAULT_STABILITY, StabilityRef, StabilityTable
from ..decompiler import Formula
from ..structure import known_compounds, resolve_structure
from .bucket import Bucket, Quantity, unknown
from .phase import estimate_phase
from .stability_horizon import (
    SurvivalVerdict,
    decomposition_rate_for,
    survival_verdict,
    surviving_fraction,
)
from .step import ExperimentRoute

__all__ = [
    "TransitionStatus",
    "Transition",
    "Composability",
    "verify_composability",
    "resolve_stability",
]


class TransitionStatus(str, Enum):
    """The verdict for one intermediate crossing one step-to-step transition."""

    COMPOSABLE = "COMPOSABLE"
    DEGENERATE = "DEGENERATE"
    UNKNOWN = "UNKNOWN"


def _formula_str(molecule: Molecule) -> str:
    return repr(Formula.of(molecule.formula, molecule.charge))


def resolve_stability(
    molecule: Molecule, table: StabilityTable = DEFAULT_STABILITY
) -> StabilityRef | None:
    """The sourced stability record for ``molecule``, keyed on canonical STRUCTURE, never borrowed by formula.

    Three cases, and no formula-borrow in any of them (tension-A, ``a-reaction-key-by-formula-borrows-a-rate``):

    * ``molecule`` resolves to a KNOWN (canonical) isomer -> its NAMED record, or ``None`` (a loud gap for *this*
      isomer), never a same-formula sibling's record. This was the one instance live on the DEFAULT table before the
      fix: the ester 4-aminophenyl acetate, correctly identified as a distinct C8H9NO2 isomer, was inheriting
      paracetamol's onset/isolability/provenance as if sourced for it.
    * ``molecule`` is an UNREGISTERED isomer of a formula the registry DOES know (``known_compounds`` is non-empty
      but none matched its resonance identity) -> ``None``. It is a *different compound* than every registered isomer
      of that formula, so returning a seeded record keyed to one of them would fabricate a verdict for the wrong
      compound (e.g. ethynol borrowing ketene's ``isolable=False`` -> a fabricated DEGENERATE; a 2-aminophenol
      byproduct printing "4-aminophenol decomposes at >= 557 K"). The GENERAL form of the borrow, closed here --
      not merely the ester (evil-morty MEDIUM fold).
    * ``molecule``'s formula is NOVEL to the registry (``known_compounds`` is empty) -> the formula fallback fires.
      There is no registered isomer for the query to be confused with, so a ``for_formula`` hit can only be a record
      the caller INJECTED for exactly this formula -- the universality/injection lever (ethyl acetate, N2O5 in the
      tests). ``for_formula`` still refuses a table holding several isomers of the formula.

    Consults the (possibly caller-extended) table.
    """
    named = resolve_structure(molecule)
    if named is not None:
        # KNOWN canonical isomer: match by name only. for_named's None is an honest gap, not a formula-borrow.
        return table.for_named(named.expected_formula, named.name)
    if known_compounds(Formula.of(molecule.formula, molecule.charge)):
        # an UNREGISTERED isomer of a formula the registry KNOWS: fail closed rather than borrow a registered
        # sibling's sourced record for what is a different compound. Only a formula the registry knows NOTHING of
        # (below) may take the injected-record fallback.
        return None
    return table.for_formula(_formula_str(molecule))


def _temperature_union(a: ConditionEnvelope, b: ConditionEnvelope) -> Interval | None:
    """The union of the two envelopes' declared temperature ranges (K), or ``None`` if neither declares."""
    temps = [e.temperature for e in (a, b) if e.temperature is not None]
    if not temps:
        return None
    return Interval(min(t.lo for t in temps), max(t.hi for t in temps), "K")


def _pressure_note(a: ConditionEnvelope, b: ConditionEnvelope) -> Quantity | None:
    """A COMPOSABILITY observation when the two declared pressure ranges are disjoint (a real change).

    Not a survival verdict -- the pressure-dependence of phase is a sourced-model gap E1 does not attempt.
    It is surfaced so a chemist sees the handoff pressure change; when either pressure is undeclared, the
    honest read is an ``UNKNOWN`` pressure dimension, not silence.
    """
    pa, pb = a.pressure, b.pressure
    if pa is None or pb is None:
        return unknown("transition-pressure", "atm", "at least one step declares no pressure")
    disjoint = pa.hi < pb.lo or pb.hi < pa.lo
    if not disjoint:
        return None
    return Quantity(
        label="transition-pressure-change",
        value=f"[{pa.lo},{pa.hi}] -> [{pb.lo},{pb.hi}]",
        unit="atm",
        bucket=Bucket.COMPOSABILITY,
        provenance="the two steps declare disjoint pressures; the intermediate must be transferred across "
        "this change (pressure-dependent phase not assessed -- sourced-model gap)",
    )


def _serial_hold_note(hold_minutes: float | None) -> Quantity | None:
    """A COMPOSABILITY observation of the serial-schedule hold imposed on this intermediate (DAG-only, DAG-HOLD-01).

    ``hold_minutes`` is the sourced MINIMUM elapsed time the intermediate sits idle between its producer and its
    consumer under the DAG's serial schedule -- the sum of the intervening sibling steps' floors (unknown floors
    counted as 0, so it is a sound LOWER bound).  Surfaced ONLY when there IS such a hold (a convergent DAG whose
    serial schedule runs sibling branches between a producer and its join); a linear/adjacent handoff passes ``None``
    (or 0) and gets no note.  It is an observation, NOT a survival verdict: E1's decomposition check is INSTANTANEOUS
    (onset-vs-exposure) and does NOT model how LONG the intermediate is held, so the chemist is shown the hold that
    the COMPOSABLE verdict is blind to.  Mirrors :func:`_pressure_note` exactly -- a finding, never a status change
    (time / max-hold stability is a sourced-model gap E1 does not attempt: the named next-step).
    """
    if hold_minutes is None or hold_minutes <= 0:
        return None
    return Quantity(
        label="serial-hold-minutes",
        value=f">={hold_minutes:g}",
        unit="min",
        bucket=Bucket.COMPOSABILITY,
        provenance="under the serial schedule computed here (one of several valid orders -- a different order may "
        "shift the hold to a sibling intermediate) the intermediate is held at least this long through sibling "
        "branches before the join consumes it (sum of intervening steps' sourced minimum elapsed, unknown floors "
        "counted as 0); E1's survival verdict is instantaneous and does not model this hold (time/max-hold "
        "stability not assessed -- sourced-model gap)",
    )


def _pressure_phase_degeneracy(
    rec: StabilityRef, env_from: ConditionEnvelope, env_to: ConditionEnvelope
) -> tuple[str, Quantity] | None:
    """A DEGENERATE reason (+ its sourced finding) when a real pressure drop flashes the intermediate off.

    Fires ONLY when it is fully sourced and unambiguous: both steps declare temperature AND pressure, the two
    pressures are DISJOINT (a genuine change the route imposes), the record carries a boiling point and an
    enthalpy of vaporisation, and the Clausius-Clapeyron estimate places the intermediate as a CONDENSED
    phase at the higher-pressure step but a GAS at the lower-pressure step -- i.e. the pressure change itself
    boils it away, so it cannot be transferred to the next step.  Returns ``None`` in every other case (no
    change, or insufficient sourced data), so the pressure dimension is never a fabricated verdict.
    """
    pf, pt = env_from.pressure, env_to.pressure
    tf, tt = env_from.temperature, env_to.temperature
    if pf is None or pt is None or tf is None or tt is None:
        return None
    if rec.boiling is None or rec.dhvap_kj_per_mol is None:
        return None
    disjoint = pf.hi < pt.lo or pt.hi < pf.lo
    if not disjoint:
        return None
    from_p, to_p = (pf.lo + pf.hi) / 2.0, (pt.lo + pt.hi) / 2.0
    from_t, to_t = (tf.lo + tf.hi) / 2.0, (tt.lo + tt.hi) / 2.0
    (hi_t, hi_p), (lo_t, lo_p) = (
        ((from_t, from_p), (to_t, to_p)) if from_p >= to_p else ((to_t, to_p), (from_t, from_p))
    )
    phase_hi = estimate_phase(rec, hi_t, hi_p)
    phase_lo = estimate_phase(rec, lo_t, lo_p)
    if phase_hi in ("liquid", "solid") and phase_lo == "gas":
        reason = (
            f"DEGENERATE: {rec.name} is {phase_hi} at {hi_p} atm but a gas at {lo_p} atm "
            f"(Clausius-Clapeyron estimate from sourced bp + dHvap {rec.dhvap_kj_per_mol} kJ/mol); the "
            f"pressure drop across the transition boils it off, so it cannot be carried to the next step"
        )
        finding = Quantity(
            "phase-at-transition", f"{phase_hi}@{hi_p}atm -> gas@{lo_p}atm", "",
            Bucket.KNOWN_SOURCED,
            f"Clausius-Clapeyron (established model) over sourced bp + dHvap {rec.dhvap_kj_per_mol} kJ/mol",
        )
        return reason, finding
    return None


@dataclass(frozen=True)
class Transition(Digestible):
    """One intermediate crossing one step-to-step transition, with its sourced verdict and evidence."""

    from_step: int
    to_step: int
    intermediate: Molecule
    status: TransitionStatus
    reason: str
    exposed_temperature: Interval | None
    findings: tuple[Quantity, ...]
    #: DURATION-SURVIVAL-01: the fraction of this intermediate surviving the serial hold under SOURCED
    #: first-order decomposition kinetics, or ``None`` when the handoff was not duration-assessed (no sourced
    #: rate, or no modeled hold).  ``compare=False`` -> DIGEST-EXCLUDED disclosure: the survival reading rides
    #: here while any verdict change it drives lands in ``status``/``reason`` (which ARE digested), so a route
    #: whose intermediate has no sourced rate keeps its exact prior digest.
    surviving_fraction: float | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.status, TransitionStatus):
            raise TypeError("status must be a TransitionStatus")
        if type(self.intermediate) is not Molecule:
            raise TypeError("intermediate must be a Molecule")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string (cite the envelopes / threshold)")
        if self.surviving_fraction is not None and (
            type(self.surviving_fraction) is not float or not (0.0 <= self.surviving_fraction <= 1.0)
        ):
            raise ValueError("surviving_fraction must be None or a float in [0, 1]")

    @property
    def degenerate(self) -> bool:
        return self.status is TransitionStatus.DEGENERATE


def _judge_transition_instant(
    from_step: int,
    to_step: int,
    intermediate: Molecule,
    env_from: ConditionEnvelope,
    env_to: ConditionEnvelope,
    table: StabilityTable,
    *,
    hold_minutes: float | None = None,
) -> Transition:
    exposed = _temperature_union(env_from, env_to)
    findings: list[Quantity] = []
    pnote = _pressure_note(env_from, env_to)
    if pnote is not None:
        findings.append(pnote)
    hnote = _serial_hold_note(hold_minutes)  # DAG-HOLD-01: the serial-schedule hold E1's instantaneous verdict misses
    if hnote is not None:
        findings.append(hnote)

    rec = resolve_stability(intermediate, table)
    if rec is None:
        findings.append(unknown("stability", "", "no sourced stability record for this intermediate"))
        return Transition(
            from_step, to_step, intermediate, TransitionStatus.UNKNOWN,
            f"UNKNOWN: no sourced stability data for {intermediate!r}; survival across the transition "
            f"cannot be judged (inject its sourced thresholds to close this gap)",
            exposed, tuple(findings),
        )

    # -- the load-bearing sourced fact #1: is it isolable at all? -------------------------------------
    if not rec.isolable:
        findings.append(Quantity(
            "isolable", False, "", Bucket.COMPOSABILITY, rec.provenance,
        ))
        return Transition(
            from_step, to_step, intermediate, TransitionStatus.DEGENERATE,
            f"DEGENERATE: {rec.name} is not isolable and is generated/consumed in situ ({rec.provenance}); "
            f"a route that hands it from step {from_step + 1} to step {to_step + 1} cannot exist",
            exposed, tuple(findings),
        )

    # -- sourced fact #1b (E1 depth): a pressure drop that boils the intermediate off (Clausius-Clapeyron)
    pressure_deg = _pressure_phase_degeneracy(rec, env_from, env_to)
    if pressure_deg is not None:
        reason, finding = pressure_deg
        findings.append(finding)
        return Transition(
            from_step, to_step, intermediate, TransitionStatus.DEGENERATE, reason, exposed, tuple(findings),
        )

    # -- the load-bearing sourced fact #2: thermal decomposition vs the exposure ----------------------
    if rec.decomposition_onset is not None:
        onset = rec.decomposition_onset
        findings.append(Quantity(
            "decomposition-onset", onset.lo, "K", Bucket.KNOWN_SOURCED, rec.provenance,
        ))
        if exposed is None:
            findings.append(unknown(
                "exposure-temperature", "K",
                "neither step declares a temperature, so the known decomposition risk cannot be checked",
            ))
            return Transition(
                from_step, to_step, intermediate, TransitionStatus.UNKNOWN,
                f"UNKNOWN: {rec.name} decomposes at >= {onset.lo} K (sourced) but neither step declares a "
                f"temperature, so its exposure across the transition cannot be judged",
                exposed, tuple(findings),
            )
        survives = rec.survives_temperature(exposed)
        if survives is False:
            return Transition(
                from_step, to_step, intermediate, TransitionStatus.DEGENERATE,
                f"DEGENERATE: {rec.name} decomposes at >= {onset.lo} K (sourced: {rec.provenance}), but the "
                f"transition from step {from_step + 1} to step {to_step + 1} holds it over up to "
                f"{exposed.hi} K -- it will not survive to the next step",
                exposed, tuple(findings),
            )
        return Transition(
            from_step, to_step, intermediate, TransitionStatus.COMPOSABLE,
            f"COMPOSABLE: {rec.name} is isolable and its exposure (up to {exposed.hi} K) stays below its "
            f"sourced decomposition onset ({onset.lo} K)",
            exposed, tuple(findings),
        )

    # isolable and NO tabulated onset: the record asserts no bench-range decomposition (see stability.py)
    findings.append(Quantity(
        "isolable", True, "", Bucket.KNOWN_SOURCED, rec.provenance,
    ))
    return Transition(
        from_step, to_step, intermediate, TransitionStatus.COMPOSABLE,
        f"COMPOSABLE: {rec.name} is isolable with no sourced bench-range decomposition threshold "
        f"({rec.provenance})",
        exposed, tuple(findings),
    )


def _survival_product(transitions: "tuple[Transition, ...]") -> float | None:
    """The composite surviving fraction over a sequence of transitions: the PRODUCT of each duration-assessed
    transition's ``surviving_fraction`` -- the survival monoid functor ``S: Process -> ([0, 1], x)``, whose
    defining law is that survival composes multiplicatively along sequential composition
    (``S(g . f) = S(g) * S(f)``).  ``None`` when NO transition was duration-assessed, so an unassessed route is
    never misread as "100% survives" (the anti-vacuous-green discipline).

    This is the product over the DURATION-ASSESSED handoffs ONLY -- it is NOT a whole-route survival
    probability.  A route can carry a reassuring fraction here while its ``verdict`` is DEGENERATE for a
    non-duration reason (a non-isolable intermediate, an onset exceeded).  Read it ALONGSIDE the verdict, never
    instead of it.

    Move 6 (order-invariance scope): the set of duration-assessed handoffs and each handoff's fraction are
    functions of the causal partial order, so the VERDICT is EXACTLY invariant under any linear extension.  This
    displayed product is invariant only up to IEEE float rounding -- with three or more distinct partial fractions
    in ``(0, 1)`` the iteration order (which follows ``dag.edges``, and so the listing) can differ in the last ULP.
    That cannot change a band (DEGENERATE/COMPOSABLE/UNKNOWN); the fraction is a disclosed magnitude, not a verdict."""
    fractions = [t.surviving_fraction for t in transitions if t.surviving_fraction is not None]
    if not fractions:
        return None
    product = 1.0
    for fraction in fractions:
        product *= fraction
    return product


def _hold_survival(
    rec: KineticRef, segments: "tuple[tuple[Interval | None, float], ...]"
) -> "tuple[float, bool, float, float]":
    """Composite surviving fraction over the hold's ``(temperature, minutes)`` segments: the PRODUCT of the
    per-segment first-order survivals ``prod_k exp(-k(T_k) t_k)`` -- the survival monoid applied ALONG the idle
    hold, using each intervening step's OWN declared temperature (never a producer/consumer endpoint's), so the
    reading rests on the temperatures the intermediate actually sits at.  Each segment takes the HIGH end of its
    declared range (the worst case WITHIN that step).  Returns ``(fraction, all_in_fit_window, total_minutes,
    peak_K)``.  The caller has already established that every segment carries a temperature, ``minutes > 0``, and
    the rate's ``(Ea, A)`` are finite -- so ``surviving_fraction`` cannot raise here."""
    fraction = 1.0
    all_in_window = True
    total_minutes = 0.0
    peak = 0.0
    lo, hi = rec.temperature_range_k
    for temperature, minutes in segments:
        t = temperature.hi                                   # worst case WITHIN this intervening step's range
        fraction *= surviving_fraction(rec, t, minutes * 60.0)
        total_minutes += minutes
        peak = max(peak, t)
        if not (lo <= t <= hi):
            all_in_window = False
    return fraction, all_in_window, total_minutes, peak


def _apply_duration_gate(
    base: Transition,
    intermediate: Molecule,
    *,
    hold_segments: "tuple[tuple[Interval | None, float], ...] | None",
    kinetics: KineticTable,
) -> Transition:
    """DURATION-SURVIVAL-01: fold a duration-aware survival reading into E1's instantaneous verdict.

    E1's shipped check is instantaneous (onset-vs-exposure) and TIME-BLIND; DAG-HOLD-01 computes the sourced
    serial hold but only DISCLOSED it (a note, never a verdict).  This consumes that hold.  The intermediate
    sits through the intervening SIBLING steps, so the survival is computed over THEIR actual ``(temperature,
    duration)`` segments (:func:`_hold_survival`) -- NOT the producer/consumer endpoint temperatures (those are
    the reaction temperatures the instantaneous check already used, and are not where the intermediate idles).
    Where the intermediate has a SOURCED first-order decomposition rate (matched on CANONICAL STRUCTURE, never
    formula), the composite fraction moves the verdict -- the wire-in the primitive's own docstring named.

    Move 6: ``hold_segments`` here is strictly the **forced-between** (unavoidable) hold -- the steps that idle the
    intermediate in EVERY linear extension of the DAG's causal order (:func:`~smartchem.experiment.dag._hold_segments`
    with ``unavoidable=True``).  So a ``DEGENERATE`` from this gate holds under every valid schedule (no reordering
    saves it), and the verdict is invariant under how independent branches were listed -- it never fabricates a
    refutation a competent schedule would avoid.  Two honest boundaries follow: (1) COMPLETENESS -- a convergent join
    where BOTH branches carry a fast decay has an empty forced-between set (neither forces the other), so the gate
    stays silent and the verdict is ``UNKNOWN`` even though every single-vessel schedule destroys one intermediate;
    that route-level (makespan) fact is out of scope here, so ``UNKNOWN`` must NOT be read as "just needs more data".
    (2) The hold survival assumes the idle intermediate sits at each intervening step's OWN declared temperature (a
    refrigerated bench would differ); a forced-between ``DEGENERATE`` inherits that W3 tendency (pre-existing R23
    modelling), it is not a measurement of the real bench.

    It only ever TIGHTENS, never loosens:

    * ``DEGRADES`` **inside the sourced fit window** (majority-destroyed over the hold, sourced) -> ``DEGENERATE``
      -- even where the instantaneous stability table was silent, because a sourced kinetic refutation is
      stronger than a missing record;
    * ``DEGRADES`` from an **out-of-window (extrapolated)** rate -> ``UNKNOWN``, NOT ``DEGENERATE`` -- a
      verdict-flipping refutation resting on an extrapolated rate would be fabrication (a wrong refutation is
      worse than none, the anti-fabrication asymmetry: an extrapolated SURVIVES is safe because colder is
      monotonically slower, but an extrapolated DEGRADES needs the rate large where the fit does not vouch for
      it), so it fails CLOSED, disclosing the extrapolated concern as a finding;
    * ``MARGINAL`` -> ``UNKNOWN`` (a disclosed concern, not affirmatively cleared);
    * ``SURVIVES`` leaves the instantaneous verdict as it stood -- a kinetic survival over a hold does NOT
      establish isolability or cure a missing record, so it never UPGRADES a verdict.

    Fail-closed: an already-``DEGENERATE`` base, no positive hold, ANY hold segment whose temperature is
    undeclared (the hold temperature is then unmodeled -- the gate never borrows an endpoint's and never renders
    a verdict on a temperature the model does not actually know), no sourced rate, or a non-finite sourced
    ``(Ea, A)`` all return ``base`` untouched -- never fabricating a survival, a verdict, or a finding.

    The out-of-window DEGRADES guard reads ``all_in_window`` (every forced-between segment in the fit window),
    so a hold MIXING a legitimately-destroying in-window segment with a harmless out-of-window one conservatively
    fails closed to UNKNOWN rather than DEGENERATE (evil-morty R30) -- a completeness cost in the SAFE direction
    (a real in-window refutation is suppressed, never a fabricated one admitted); a per-segment "which segment
    drove the destruction" refinement is tracked debt, not built.
    """
    if base.status is TransitionStatus.DEGENERATE:
        return base                                          # already refuted on sourced grounds; the hold is moot
    material = [(t, m) for (t, m) in (hold_segments or ()) if m > 0]
    if not material:
        return base                                          # no positive serial hold (linear / adjacent handoff)
    if any(temperature is None for temperature, _m in material):
        return base                                          # a hold segment's temperature is unmodeled -> fail-closed
    rec = decomposition_rate_for(intermediate, kinetics=kinetics)
    if rec is None or not (math.isfinite(rec.ea_kj_per_mol) and math.isfinite(rec.log10_a)):
        return base                                          # no SOURCED (finite) first-order rate -> silent
    fraction, in_window, total_minutes, peak = _hold_survival(rec, material)
    verdict = survival_verdict(fraction)
    grade = "DERIVED" if in_window else "PREDICTED"
    detail = (
        f"{fraction * 100:.1f}% of '{rec.name}' remains over a {total_minutes:g} min serial hold (peak {peak:g} K, "
        f"each intervening step held at its OWN declared temperature) by first-order consumption exp(-k t), "
        f"k = A*exp(-Ea/RT) over the SOURCED Arrhenius fit (Ea = {rec.ea_kj_per_mol:.1f} kJ/mol, log10 A = "
        f"{rec.log10_a:.2f}), grade {grade} -- a kinetic tendency under the sourced fit, NOT a claim about the "
        f"real process or its true rate (W3)"
    )
    finding = Quantity("duration-survival-fraction", f"{fraction:.4g}", "", Bucket.KNOWN_SOURCED, detail)
    findings = base.findings + (finding,)
    if verdict is SurvivalVerdict.DEGRADES and in_window:
        status = TransitionStatus.DEGENERATE
        reason = (
            f"DEGENERATE: over the serial hold this route imposes ({total_minutes:g} min through intervening "
            f"steps, peak {peak:g} K) only {fraction * 100:.1f}% of the intermediate remains by SOURCED "
            f"first-order decomposition kinetics -- majority-destroyed before the next step consumes it, a "
            f"duration-aware refutation the instantaneous onset check is blind to ({detail})"
        )
    elif verdict is SurvivalVerdict.DEGRADES:                # out-of-window: an extrapolated refutation is fabrication
        status = TransitionStatus.UNKNOWN
        reason = (
            f"UNKNOWN: over the serial hold this route imposes ({total_minutes:g} min through intervening "
            f"steps, peak {peak:g} K) SOURCED first-order kinetics leave only {fraction * 100:.1f}% of the "
            f"intermediate -- but the peak {peak:g} K is OUTSIDE the sourced Arrhenius fit window, so the rate "
            f"is an EXTRAPOLATION; a verdict-flipping refutation resting on an extrapolated rate would be "
            f"fabrication (a wrong refutation is worse than none), so it fails CLOSED to UNKNOWN rather than "
            f"DEGENERATE ({detail})"
        )
    elif verdict is SurvivalVerdict.MARGINAL:
        status = TransitionStatus.UNKNOWN
        reason = (
            f"UNKNOWN: over the serial hold this route imposes ({total_minutes:g} min through intervening steps, "
            f"peak {peak:g} K) SOURCED first-order kinetics leave only {fraction * 100:.1f}% of the intermediate "
            f"remaining -- a MARGINAL duration-survival concern (neither cleanly surviving nor majority-"
            f"destroyed), so the handoff is not affirmatively cleared ({detail})"
        )
    else:                                                    # SURVIVES: confirm the instantaneous verdict, never upgrade
        status, reason = base.status, base.reason
    return Transition(
        base.from_step, base.to_step, intermediate, status, reason,
        base.exposed_temperature, findings, surviving_fraction=fraction,
    )


def _judge_transition(
    from_step: int,
    to_step: int,
    intermediate: Molecule,
    env_from: ConditionEnvelope,
    env_to: ConditionEnvelope,
    table: StabilityTable,
    *,
    gate_segments: "tuple[tuple[Interval | None, float], ...] | None" = None,
    disclosure_segments: "tuple[tuple[Interval | None, float], ...] | None" = None,
    kinetics: KineticTable = DEFAULT_KINETICS,
) -> Transition:
    """E1's per-transition verdict: the instantaneous onset/isolability check, then the DURATION-SURVIVAL-01
    duration gate (:func:`_apply_duration_gate`) over any sourced serial hold.

    Move 6 (breach #4) threads TWO distinct DAG serial-hold sets, which MUST NOT be conflated (a linear handoff has
    neither):

    * ``gate_segments`` -- the FORCED-BETWEEN (unavoidable) ``(temperature, minutes)``: the hold suffered in EVERY
      linear extension.  ONLY this may flip the verdict (:func:`_apply_duration_gate`), so the verdict is invariant
      under how independent branches were linearized.  Feeding the possibly-between/worst set here would fabricate a
      wrong ``DEGENERATE`` for a route a viable schedule saves.
    * ``disclosure_segments`` -- the POSSIBLY-BETWEEN (schedule-relative) ``(temperature, minutes)``: their total
      drives the instantaneous check's DAG-HOLD-01 disclosure note ONLY, never a verdict."""
    hold_minutes = sum(m for _t, m in disclosure_segments) if disclosure_segments else None
    base = _judge_transition_instant(
        from_step, to_step, intermediate, env_from, env_to, table, hold_minutes=hold_minutes,
    )
    return _apply_duration_gate(base, intermediate, hold_segments=gate_segments, kinetics=kinetics)


@dataclass(frozen=True)
class Composability(Digestible):
    """The composability of a whole route: one :class:`Transition` per step-to-step handoff, and the verdict.

    ``verdict`` is guarded against a vacuous pass: a route with no transitions is ``SINGLE_STEP`` (nothing to
    compose), never ``COMPOSABLE``; and ``COMPOSABLE`` requires every transition affirmatively cleared on
    sourced data, so any ``UNKNOWN`` gap keeps the route at ``UNKNOWN`` (a ``DRAFT``, not a pass).
    """

    route: ExperimentRoute
    transitions: tuple[Transition, ...]

    def __post_init__(self) -> None:
        if type(self.route) is not ExperimentRoute:
            raise TypeError("route must be an ExperimentRoute")
        if type(self.transitions) is not tuple or any(
            type(t) is not Transition for t in self.transitions
        ):
            raise TypeError("transitions must be a tuple of Transition values")
        if len(self.transitions) != self.route.n_transitions:
            raise ValueError(
                f"expected {self.route.n_transitions} transitions for this route, got "
                f"{len(self.transitions)}"
            )

    @property
    def verdict(self) -> str:
        if not self.transitions:
            return "SINGLE_STEP"
        if any(t.status is TransitionStatus.DEGENERATE for t in self.transitions):
            return "DEGENERATE"
        if all(t.status is TransitionStatus.COMPOSABLE for t in self.transitions):
            return "COMPOSABLE"
        return "UNKNOWN"

    @property
    def is_degenerate(self) -> bool:
        return self.verdict == "DEGENERATE"

    @property
    def transitions_cleared(self) -> bool:
        """Whether every inter-step survival transition is affirmatively cleared; not procedure readiness."""
        return self.verdict == "COMPOSABLE"

    @property
    def is_runnable(self) -> bool:
        """Deprecated compatibility alias for :attr:`transitions_cleared`.

        The name predates procedure-readiness tiers and must not be read as a bench-readiness claim.
        """
        import warnings
        warnings.warn(
            "Composability.is_runnable only means inter-step transitions cleared; use transitions_cleared",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.transitions_cleared

    @property
    def degenerate_reasons(self) -> tuple[str, ...]:
        return tuple(t.reason for t in self.transitions if t.degenerate)

    @property
    def gaps(self) -> tuple[str, ...]:
        return tuple(t.reason for t in self.transitions if t.status is TransitionStatus.UNKNOWN)

    @property
    def route_surviving_fraction(self) -> float | None:
        """The composite fraction surviving the whole route's duration-assessed inter-step holds -- the survival
        monoid functor's value on this composite (see :func:`_survival_product`).  ``None`` when no handoff was
        duration-assessed, never read as a full-survival pass."""
        return _survival_product(self.transitions)

    def explain(self) -> str:
        head = f"composability: {self.verdict}"
        lines = [head]
        for t in self.transitions:
            lines.append(f"  step {t.from_step + 1}->{t.to_step + 1}: {t.reason}")
        return "\n".join(lines)


def verify_composability(
    route: ExperimentRoute, *, stability: StabilityTable = DEFAULT_STABILITY,
    kinetics: KineticTable = DEFAULT_KINETICS,
) -> Composability:
    """Judge whether every intermediate survives its transition, over SOURCED stability windows.

    ``stability`` defaults to the seed table; pass an extended one
    (:meth:`~smartchem.data.stability.StabilityTable.with_records`) to bring sourced thresholds for any
    compound the seed does not carry.  The route's own declared envelopes supply the exposures.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    transitions: list[Transition] = []
    for k in range(route.n_transitions):
        intermediate = route.steps[k].target
        transitions.append(_judge_transition(
            k, k + 1, intermediate,
            route.steps[k].envelope, route.steps[k + 1].envelope, stability, kinetics=kinetics,
        ))
    return Composability(route, tuple(transitions))
