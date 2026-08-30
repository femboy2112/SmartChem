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
  A route is not "runnable" until its gaps are closed; this is ``DRAFT``, never a silent pass.

Independence (why this is not self-certifying)
----------------------------------------------
The thresholds come from a SEPARATE sourced table, not from the route's own declaration.  The check
compares the route's declared envelopes against externally-sourced facts, so a route cannot certify its own
composability.

The stated boundary (a sourced-model gap, not a silent guess)
-------------------------------------------------------------
Temperature-vs-decomposition and non-isolability are the hard teeth.  Pressure is reported honestly as a
declared-condition change but is NOT turned into a survival verdict: a boiling point's shift with pressure
(Clausius-Clapeyron) is a sourced-model gap E1 does not attempt.  A caller who has sourced pressure
tolerance injects it and extends the check; unassessed pressure stays a noted ``UNKNOWN``, never "fine".
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..category import Molecule
from ..conditions import ConditionEnvelope, Interval
from ..contracts import Digestible
from ..data.stability import DEFAULT_STABILITY, StabilityRef, StabilityTable
from ..decompiler import Formula
from ..structure import resolve_structure
from .bucket import Bucket, Quantity, unknown
from .phase import estimate_phase
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
    """The sourced stability record for ``molecule`` -- named if the structure registry resolves it,
    else formula-level (unambiguous only), else ``None``.  Consults the (possibly caller-extended) table,
    so an arbitrary compound resolves once its sourced record is injected keyed by its formula string.
    """
    named = resolve_structure(molecule)
    if named is not None:
        hit = table.for_named(named.expected_formula, named.name)
        if hit is not None:
            return hit
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

    def __post_init__(self) -> None:
        if not isinstance(self.status, TransitionStatus):
            raise TypeError("status must be a TransitionStatus")
        if type(self.intermediate) is not Molecule:
            raise TypeError("intermediate must be a Molecule")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string (cite the envelopes / threshold)")

    @property
    def degenerate(self) -> bool:
        return self.status is TransitionStatus.DEGENERATE


def _judge_transition(
    from_step: int,
    to_step: int,
    intermediate: Molecule,
    env_from: ConditionEnvelope,
    env_to: ConditionEnvelope,
    table: StabilityTable,
) -> Transition:
    exposed = _temperature_union(env_from, env_to)
    findings: list[Quantity] = []
    pnote = _pressure_note(env_from, env_to)
    if pnote is not None:
        findings.append(pnote)

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
    def is_runnable(self) -> bool:
        """True only for a route with transitions, all affirmatively cleared on sourced data."""
        return self.verdict == "COMPOSABLE"

    @property
    def degenerate_reasons(self) -> tuple[str, ...]:
        return tuple(t.reason for t in self.transitions if t.degenerate)

    @property
    def gaps(self) -> tuple[str, ...]:
        return tuple(t.reason for t in self.transitions if t.status is TransitionStatus.UNKNOWN)

    def explain(self) -> str:
        head = f"composability: {self.verdict}"
        lines = [head]
        for t in self.transitions:
            lines.append(f"  step {t.from_step + 1}->{t.to_step + 1}: {t.reason}")
        return "\n".join(lines)


def verify_composability(
    route: ExperimentRoute, *, stability: StabilityTable = DEFAULT_STABILITY
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
            route.steps[k].envelope, route.steps[k + 1].envelope, stability,
        ))
    return Composability(route, tuple(transitions))
