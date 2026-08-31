"""L2 -- the unified epistemic classifier: ONE graded verdict over any formal combination.

This is the mission made literal.  The operator's stated destination for the whole repo is to
*"systematically parse ALL formal linear combinations of atoms/chemicals/reactions and judge which are
legitimate / known / hypothesized / physically unreal."*  Every rung needed for that judgement now exists
as a verified engine -- conservation (E0/E2), composability (E1), feasibility (M1), equilibrium (M2),
regiochemical selectivity (E5+) -- each emitting its own labelled verdict.  L2 does not add a new engine or
a new physics.  It is the single function that *composes* those verdicts into the one grade the governing
frame demands, exactly the mapping :mod:`~smartchem.experiment.bucket` already documents as a promise:

    a DERIVED or PREDICTED verdict is carried by KNOWN_SOURCED quantities; a REFUTED verdict cites
    CONSERVATION / COMPOSABILITY / KNOWN_SOURCED facts; an UNKNOWN verdict is all UNKNOWN.

The six grades, each earned by a CHECKABLE condition (never a vibe)
------------------------------------------------------------------
* ``REFUTED`` -- a NAMED law forbids it; the "physically unreal" bucket, and it OVERRIDES every other grade.
  Two sources, each citing its fact: (1) conservation of mass/charge is violated -- the formal combination
  does not even build a :class:`~smartchem.category.Reaction` (E0); (2) a SOURCED fact forbids a handoff --
  an E1 ``DEGENERATE`` transition (an intermediate that is not isolable, or is boiled off by a declared
  pressure drop).  This is the one permanent refusal: contradicting established sourced physics.
* ``KNOWN`` -- a SOURCED record attests *this exact reaction*: a sourced regiochemistry record matches it
  (:mod:`~smartchem.experiment.selectivity`), or the step carries a sourced (declared) condition envelope.
  Direct literature attestation of the reaction ITSELF -- a step above a model computation.  A reaction can
  be KNOWN yet have UNKNOWN thermodynamics (paracetamol acetylation: a documented ACS teaching synthesis
  whose ΔG has no sourced formation data); the grade reflects the sourced attestation, and the thermo gap is
  a separate, loudly-noted dimension -- never papered over.
* ``DERIVED`` -- no direct attestation, but an ESTABLISHED model computes it IN-ENVELOPE: feasibility graded
  ``DERIVED`` (ΔG at/near the data's 298.15 K reference).  Reproducing known chemistry, not inventing it.
* ``PREDICTED`` -- an established model computes it, but EXTRAPOLATED far from the reference (feasibility
  graded ``PREDICTED``, constant-ΔH/ΔS).  A real approximation, flagged as an extrapolation.
* ``HYPOTHESIZED`` -- the combination CONSERVES mass/charge (a formally valid candidate) but is neither
  sourced nor thermodynamically derivable (no sourced record, no reachable ΔG).  The decompiler's raw
  candidate edges live here.  This is the FLOOR for any balanced reaction: balanced => at least a
  hypothesis; unbalanced => REFUTED.  "Hypothesized" is the mission's word for exactly this.
* ``UNKNOWN`` -- the combination cannot even be placed: a species will not canonicalise for the conservation
  check, so no verdict (not even REFUTED) can be asserted.  The honest "no claim".

Composition (routes and DAGs): worst-step-dominated
---------------------------------------------------
A route or a convergent DAG is graded by its WEAKEST step on the legitimacy ladder
(``HYPOTHESIZED < PREDICTED < DERIVED < KNOWN``) -- a combination is only as well-founded as its least
well-founded reaction -- with a ``DEGENERATE`` transition (E1) overriding everything to ``REFUTED``.  This
is the identical honest bottleneck aggregation :class:`~smartchem.experiment.feasibility.RouteFeasibility`
and :class:`~smartchem.experiment.equilibrium.RouteEquilibrium` already use; L2 reuses their machinery
(and M4's :func:`~smartchem.experiment.dag.dag_composability` for the convergent shape), never re-deriving it.

Boundaries, stated loudly
-------------------------
* The grade classifies epistemic FOOTING, never a rate or a yield -- a ``KNOWN`` or ``DERIVED`` reaction can
  be kinetically frozen; L2 says *what we know about whether it is a real, legitimate transformation*, never
  *how fast* on its own.  The rate is reported as a SEPARATE, orthogonal dimension
  (:mod:`~smartchem.experiment.kinetics`, roadmap L1): where a reaction's Arrhenius ``(Ea, A)`` are sourced,
  the ``kinetics`` sub-verdict carries its rate regime (``FAST`` .. ``FROZEN``), and where they are not it is a
  loud ``UNKNOWN`` rate -- but NEITHER ever alters the grade.  So a ``KNOWN`` reaction stays ``KNOWN`` while
  its rate reads ``FROZEN`` or ``UNKNOWN``; L2 can now SAY "known-but-kinetically-frozen" without predicting a
  rate it has no source for.
* ``KNOWN`` is only as broad as the sourced records injected; the seed attests a few reactions, and coverage
  grows by injecting sourced selectivity records / declared envelopes, NOT by editing this module.  A
  narrow ``KNOWN`` is honest, not a bug -- most formal combinations are genuinely DERIVED / HYPOTHESIZED.
* A ``DEGENERATE``-driven ``REFUTED`` refutes the ROUTE-as-written (this ordering, these conditions), not the
  underlying chemistry; the reason names the sourced fact and the specific handoff.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..category import ConservationError, Molecule
from ..contracts import Digestible
from ..data.eyring import DEFAULT_EYRING, EyringTable
from ..data.kinetics import DEFAULT_KINETICS, KineticTable
from ..data.stability import DEFAULT_STABILITY, StabilityTable
from ..data.thermo import DEFAULT_THERMO, ThermoTable
from .bucket import Bucket, Quantity
from .composability import verify_composability
from .dag import (
    SynthesisDAG,
    _worst_equilibrium,
    _worst_feasibility,
    dag_composability,
)
from .equilibrium import equilibrium_of_step, verify_equilibrium
from .eyring import eyring_of_step, rate_agreement, verify_eyring
from .feasibility import FeasibilityGrade, StepFeasibility, feasibility_of_step, verify_feasibility
from .kinetics import kinetics_of_step, verify_kinetics, worst_regime
from .selectivity import (
    DEFAULT_SELECTIVITY,
    SelectivityStatus,
    SelectivityTable,
    StepSelectivity,
    selectivity_of_step,
    verify_selectivity,
)
from .step import ExperimentRoute, ExperimentStep, StepError

__all__ = [
    "Grade",
    "UnifiedVerdict",
    "classify",
    "classify_step",
    "classify_reaction",
    "classify_route",
    "classify_dag",
]


class Grade(str, Enum):
    """The unified epistemic grade of a formal combination (the governing frame's six-way verdict)."""

    KNOWN = "KNOWN"                # a sourced record attests this exact reaction (documented chemistry)
    DERIVED = "DERIVED"           # an established model computes it in-envelope (near the data's reference)
    PREDICTED = "PREDICTED"       # an established model computes it, but extrapolated -- flagged
    HYPOTHESIZED = "HYPOTHESIZED"  # conserves (a formally valid candidate) but neither sourced nor derived
    REFUTED = "REFUTED"           # a NAMED law forbids it (conservation, or a sourced impossibility)
    UNKNOWN = "UNKNOWN"           # cannot even be placed (no conservation decision possible)


#: The legitimacy ladder used to aggregate a route/DAG worst-step-dominated (higher = better founded).
#: REFUTED and UNKNOWN are handled by precedence, not by this ordinal, so they are absent here.
_LADDER: dict[Grade, int] = {
    Grade.HYPOTHESIZED: 0,
    Grade.PREDICTED: 1,
    Grade.DERIVED: 2,
    Grade.KNOWN: 3,
}


@dataclass(frozen=True)
class UnifiedVerdict(Digestible):
    """One graded verdict over a formal combination, composing every rung, with its evidence and boundary.

    ``grade`` is the six-way verdict; ``law`` names the forbidding law/fact for a ``REFUTED`` grade (``None``
    otherwise); ``conserves`` is the mass/charge bookkeeping outcome; ``findings`` are the labelled
    :class:`~smartchem.experiment.bucket.Quantity` values each rung contributed (so the verdict carries its
    own bucketed evidence); the sub-verdict fields hold the composed rung objects (``None`` where a rung does
    not apply -- a single step has no composability); ``notes`` are the per-rung human reasons.
    ``kinetics`` (Arrhenius) and ``eyring`` (transition-state) are the ORTHOGONAL rate dimension -- TWO
    INDEPENDENT providers of the same observable ``k``, reported alongside the grade but NEVER entering it (a
    ``KNOWN`` reaction with a ``FROZEN`` or ``UNKNOWN`` rate is still ``KNOWN``); where both fire, a rate
    cross-check note corroborates or flags the two.
    """

    grade: Grade
    headline: str
    law: str | None
    conserves: bool
    findings: tuple[Quantity, ...]
    notes: tuple[str, ...]
    feasibility: Digestible | None
    equilibrium: Digestible | None
    selectivity: Digestible | None
    composability: Digestible | None
    kinetics: Digestible | None = None
    eyring: Digestible | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.grade, Grade):
            raise TypeError("grade must be a Grade")
        if not isinstance(self.headline, str) or not self.headline:
            raise ValueError("headline must be a non-empty string")
        if self.grade is Grade.REFUTED and not self.law:
            raise ValueError("a REFUTED verdict must NAME the law/fact that forbids it")
        if self.grade is not Grade.REFUTED and self.law is not None:
            raise ValueError("only a REFUTED verdict carries a named law")
        if type(self.findings) is not tuple or any(type(q) is not Quantity for q in self.findings):
            raise TypeError("findings must be a tuple of Quantity values")

    @property
    def is_legitimate(self) -> bool:
        """True for a grade that rests on sourced or model-derived footing (KNOWN / DERIVED / PREDICTED)."""
        return self.grade in (Grade.KNOWN, Grade.DERIVED, Grade.PREDICTED)

    @property
    def is_refuted(self) -> bool:
        return self.grade is Grade.REFUTED

    def explain(self) -> str:
        lines = [self.headline]
        if self.law is not None:
            lines.append(f"  law: {self.law}")
        for note in self.notes:
            lines.append(f"  - {note}")
        return "\n".join(lines)


def _conservation_finding() -> Quantity:
    return Quantity(
        "conservation", "balanced", "", Bucket.CONSERVATION,
        "mass and charge balance, independently re-verified through smartchem.category.Reaction",
    )


def _feas_summary(feas: StepFeasibility) -> str:
    """A tight one-line reading of a step's feasibility for a headline."""
    if feas.grade is FeasibilityGrade.UNKNOWN:
        return "thermodynamics UNKNOWN (no sourced ΔfH°/S°)"
    return f"ΔG = {feas.delta_g_kj:.1f} kJ/mol ({feas.direction.value}, {feas.grade.value})"


def _step_grade(feas: StepFeasibility, sel: StepSelectivity, is_declared: bool) -> Grade:
    """The KNOWN / DERIVED / PREDICTED / HYPOTHESIZED grade of ONE conserving step (never REFUTED/UNKNOWN).

    Conservation is a precondition (the step exists), so the floor is HYPOTHESIZED.  A sourced attestation of
    the reaction itself (a matched selectivity record, or a sourced/declared envelope) earns KNOWN; else an
    established ΔG earns DERIVED (in-envelope) or PREDICTED (extrapolated); else HYPOTHESIZED.
    """
    attested = sel.status in (SelectivityStatus.FAVORED, SelectivityStatus.DISFAVORED) or is_declared
    if attested:
        return Grade.KNOWN
    if feas.grade is FeasibilityGrade.DERIVED:
        return Grade.DERIVED
    if feas.grade is FeasibilityGrade.PREDICTED:
        return Grade.PREDICTED
    return Grade.HYPOTHESIZED


def _attestation(sel: StepSelectivity, is_declared: bool) -> str:
    """Name the sourced fact that makes a step KNOWN (for the headline)."""
    if sel.status in (SelectivityStatus.FAVORED, SelectivityStatus.DISFAVORED):
        minor = " (this route makes the MINOR isomer)" if sel.status is SelectivityStatus.DISFAVORED else ""
        return f"a sourced regiochemistry record for this reaction{minor}"
    if is_declared:
        return "a sourced (declared) condition envelope for this reaction"
    return "a sourced record"  # unreachable when grade is KNOWN, kept total


def classify_step(
    step: ExperimentStep,
    *,
    thermo: ThermoTable = DEFAULT_THERMO,
    selectivity: SelectivityTable = DEFAULT_SELECTIVITY,
    kinetics: KineticTable = DEFAULT_KINETICS,
    barriers: EyringTable = DEFAULT_EYRING,
    temperature_k: float | None = None,
) -> UnifiedVerdict:
    """Grade one conserving :class:`ExperimentStep` -- the atomic case of the unified classifier.

    Composes feasibility (M1), equilibrium (M2), and selectivity (E5+) into one grade, and reports the rate
    (L1 kinetics) as an ORTHOGONAL dimension that never enters the grade.  A single step has no transition, so
    composability does not apply and a single step is never ``REFUTED`` here (conservation is guaranteed by
    construction; use :func:`classify_reaction` to grade an unbuilt, possibly non-conserving combination).
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    feas = feasibility_of_step(step, thermo=thermo, temperature_k=temperature_k)
    equi = equilibrium_of_step(step, thermo=thermo, temperature_k=temperature_k)
    sel = selectivity_of_step(step, table=selectivity)
    kin = kinetics_of_step(step, kinetics=kinetics, temperature_k=temperature_k)
    eyr = eyring_of_step(step, barriers=barriers, temperature_k=temperature_k)
    grade = _step_grade(feas, sel, step.is_declared)  # rate is deliberately NOT an input -- it is orthogonal

    if grade is Grade.KNOWN:
        headline = (
            f"KNOWN: {step.equation()} -- attested by {_attestation(sel, step.is_declared)}; "
            f"{_feas_summary(feas)}"
        )
    elif grade in (Grade.DERIVED, Grade.PREDICTED):
        headline = (
            f"{grade.value}: {step.equation()} -- an established model computes {_feas_summary(feas)}; "
            f"equilibrium {equi.extent.value}"
        )
    else:  # HYPOTHESIZED
        missing = ", ".join(sorted(set(feas.missing))) if feas.missing else "no reachable thermodynamic data"
        headline = (
            f"HYPOTHESIZED: {step.equation()} -- conserves mass/charge (a formally valid candidate), but no "
            f"sourced attestation and no derivable ΔG ({missing})"
        )

    findings = (_conservation_finding(), feas.finding, equi.k_finding, sel.finding, kin.k_finding)
    notes = (feas.reason, equi.reason, sel.reason, kin.reason)
    if eyr.is_known:  # the second (Eyring) rate provider speaks only when it has sourced (ΔH‡, ΔS‡)
        findings = (*findings, eyr.k_finding)
        notes = (*notes, eyr.reason)
        agreement = rate_agreement(kin, eyr)
        if agreement is not None:  # both providers fired -> cross-check the two independent k's
            notes = (*notes, agreement)
    return UnifiedVerdict(
        grade, headline, None, True, findings, notes,
        feasibility=feas, equilibrium=equi, selectivity=sel, composability=None, kinetics=kin, eyring=eyr,
    )


def classify_reaction(
    reactants: tuple[Molecule, ...],
    products: tuple[Molecule, ...],
    *,
    target: Molecule | None = None,
    thermo: ThermoTable = DEFAULT_THERMO,
    selectivity: SelectivityTable = DEFAULT_SELECTIVITY,
    kinetics: KineticTable = DEFAULT_KINETICS,
    barriers: EyringTable = DEFAULT_EYRING,
    temperature_k: float | None = None,
) -> UnifiedVerdict:
    """Grade ANY formal combination ``reactants -> products`` -- the universal front door.

    Unlike :func:`classify_step`, this accepts an UNBUILT combination and so can return ``REFUTED``: a
    combination that does not conserve mass/charge fails to build a :class:`~smartchem.category.Reaction` and
    is graded ``REFUTED`` citing conservation of mass and charge -- the "physically unreal" verdict the
    mission exists to distinguish.  A conserving combination is delegated to :func:`classify_step`.

    ``target`` defaults to the first product (the choice is immaterial to conservation; it only labels which
    product the step "makes").
    """
    reactants = tuple(reactants)
    products = tuple(products)
    if not products:
        raise ValueError("a formal combination must have at least one product")
    tgt = target if target is not None else products[0]
    try:
        step = ExperimentStep.assembling(tgt, reactants, products)
    except StepError as exc:
        cause = exc.__cause__
        if isinstance(cause, ConservationError):
            law = "conservation of mass and charge"
            finding = Quantity(
                "conservation", "violated", "", Bucket.CONSERVATION,
                f"the formal combination does not balance and is refused: {cause}",
            )
            headline = f"REFUTED: {' + '.join(repr(m) for m in reactants)} -> " \
                       f"{' + '.join(repr(m) for m in products)} does not conserve mass/charge ({cause})"
            return UnifiedVerdict(
                Grade.REFUTED, headline, law, False, (finding,), (str(cause),),
                feasibility=None, equilibrium=None, selectivity=None, composability=None,
            )
        if isinstance(cause, NotImplementedError):
            headline = f"UNKNOWN: a species in this combination could not be canonicalised for the " \
                       f"conservation check ({cause}); no verdict can be asserted"
            finding = Quantity(
                "conservation", None, "", Bucket.UNKNOWN,
                "a species could not be canonicalised, so mass/charge balance is undecided here",
            )
            return UnifiedVerdict(
                Grade.UNKNOWN, headline, None, False, (finding,), (str(cause),),
                feasibility=None, equilibrium=None, selectivity=None, composability=None,
            )
        raise  # a genuine usage error (empty reactants, target not a product): not a chemistry verdict
    return classify_step(
        step, thermo=thermo, selectivity=selectivity, kinetics=kinetics, barriers=barriers,
        temperature_k=temperature_k,
    )


def _aggregate_grade(step_grades: tuple[Grade, ...]) -> Grade:
    """The worst-step-dominated grade over a route/DAG's conserving steps (min on the legitimacy ladder)."""
    return min(step_grades, key=lambda g: _LADDER[g])


def classify_route(
    route: ExperimentRoute,
    *,
    thermo: ThermoTable = DEFAULT_THERMO,
    stability: StabilityTable = DEFAULT_STABILITY,
    selectivity: SelectivityTable = DEFAULT_SELECTIVITY,
    kinetics: KineticTable = DEFAULT_KINETICS,
    barriers: EyringTable = DEFAULT_EYRING,
    temperature_k: float | None = None,
) -> UnifiedVerdict:
    """Grade a linear :class:`ExperimentRoute` -- worst-step-dominated, a ``DEGENERATE`` handoff => REFUTED."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    comp = verify_composability(route, stability=stability)
    rfeas = verify_feasibility(route, thermo=thermo, temperature_k=temperature_k)
    requi = verify_equilibrium(route, thermo=thermo, temperature_k=temperature_k)
    rsel = verify_selectivity(route, table=selectivity)
    rkin = verify_kinetics(route, kinetics=kinetics, temperature_k=temperature_k)  # orthogonal rate dimension
    reyr = verify_eyring(route, barriers=barriers, temperature_k=temperature_k)  # second (Eyring) rate provider

    findings = (_conservation_finding(),)
    if comp.verdict == "DEGENERATE":
        law = "; ".join(comp.degenerate_reasons)
        headline = (
            f"REFUTED: the {len(route.steps)}-step route -> {route.final_target!r} carries an intermediate a "
            f"SOURCED fact forbids across a transition (composability DEGENERATE) -- the route as written "
            f"cannot exist"
        )
        return UnifiedVerdict(
            Grade.REFUTED, headline, law, True, findings, comp.degenerate_reasons,
            feasibility=rfeas, equilibrium=requi, selectivity=rsel, composability=comp, kinetics=rkin,
            eyring=reyr,
        )

    step_grades = tuple(
        _step_grade(f, s, st.is_declared)
        for f, s, st in zip(rfeas.per_step, rsel.per_step, route.steps)
    )
    grade = _aggregate_grade(step_grades)  # rate is deliberately NOT aggregated into the grade
    headline = (
        f"{grade.value}: {len(route.steps)}-step route -> {route.final_target!r} (weakest step: "
        f"{grade.value}); composability {comp.verdict}, feasibility {rfeas.verdict}, equilibrium "
        f"{requi.verdict}, selectivity {rsel.verdict}, kinetics {rkin.verdict}"
    )
    notes = (
        f"composability: {comp.verdict}",
        f"feasibility (ΔG, worst step): {rfeas.verdict}",
        f"equilibrium (extent, worst step): {requi.verdict}",
        f"selectivity: {rsel.verdict}",
        f"kinetics (rate, worst step): {rkin.verdict}",
    )
    return UnifiedVerdict(
        grade, headline, None, True, findings, notes,
        feasibility=rfeas, equilibrium=requi, selectivity=rsel, composability=comp, kinetics=rkin,
        eyring=reyr,
    )


def classify_dag(
    dag: SynthesisDAG,
    *,
    thermo: ThermoTable = DEFAULT_THERMO,
    stability: StabilityTable = DEFAULT_STABILITY,
    selectivity: SelectivityTable = DEFAULT_SELECTIVITY,
    kinetics: KineticTable = DEFAULT_KINETICS,
    temperature_k: float | None = None,
) -> UnifiedVerdict:
    """Grade a convergent :class:`~smartchem.experiment.dag.SynthesisDAG` -- the same worst-step-dominated
    rule over a partial order instead of a chain, reusing M4's per-edge composability and per-step rungs.

    The transition-state (Eyring) rate axis is not threaded at the DAG level: like the per-step feasibility /
    selectivity FIELDS (which this function stores as ``None``, surfacing only aggregate verdicts in the
    notes), the DAG deliberately carries a reduced rung fidelity.  ``classify_step`` and ``classify_route``
    carry the full Eyring rate axis and its Arrhenius cross-check."""
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    comp = dag_composability(dag, stability=stability)
    feas = tuple(feasibility_of_step(s, thermo=thermo, temperature_k=temperature_k) for s in dag.steps)
    equi = tuple(equilibrium_of_step(s, thermo=thermo, temperature_k=temperature_k) for s in dag.steps)
    sels = tuple(selectivity_of_step(s, table=selectivity) for s in dag.steps)
    kins = tuple(kinetics_of_step(s, kinetics=kinetics, temperature_k=temperature_k) for s in dag.steps)

    shape = "convergent" if dag.is_convergent else "linear"
    findings = (_conservation_finding(),)
    if comp.verdict == "DEGENERATE":
        law = "; ".join(comp.degenerate_reasons)
        headline = (
            f"REFUTED: the {shape} DAG -> {dag.final_target!r} carries an intermediate a SOURCED fact forbids "
            f"across an edge (composability DEGENERATE) -- this convergent synthesis as written cannot exist"
        )
        return UnifiedVerdict(
            Grade.REFUTED, headline, law, True, findings, comp.degenerate_reasons,
            feasibility=None, equilibrium=None, selectivity=None, composability=comp,
        )

    step_grades = tuple(
        _step_grade(f, s, st.is_declared) for f, s, st in zip(feas, sels, dag.steps)
    )
    grade = _aggregate_grade(step_grades)  # rate is deliberately NOT aggregated into the grade
    feas_verdict = _worst_feasibility(tuple(f.direction for f in feas))
    equi_verdict = _worst_equilibrium(tuple(e.extent for e in equi))
    kin_verdict = worst_regime(k.regime for k in kins).value
    headline = (
        f"{grade.value}: {shape} DAG -> {dag.final_target!r} ({len(dag.steps)} steps, "
        f"{len(dag.convergence_points)} join(s); weakest step: {grade.value}); composability "
        f"{comp.verdict}, feasibility {feas_verdict}, equilibrium {equi_verdict}, kinetics {kin_verdict}"
    )
    notes = (
        f"composability (per edge): {comp.verdict}",
        f"feasibility (ΔG, worst step): {feas_verdict}",
        f"equilibrium (extent, worst step): {equi_verdict}",
        f"kinetics (rate, worst step): {kin_verdict}",
    )
    return UnifiedVerdict(
        grade, headline, None, True, findings, notes,
        feasibility=None, equilibrium=None, selectivity=None, composability=comp,
    )


def classify(
    subject: ExperimentStep | ExperimentRoute | SynthesisDAG,
    *,
    thermo: ThermoTable = DEFAULT_THERMO,
    stability: StabilityTable = DEFAULT_STABILITY,
    selectivity: SelectivityTable = DEFAULT_SELECTIVITY,
    kinetics: KineticTable = DEFAULT_KINETICS,
    barriers: EyringTable = DEFAULT_EYRING,
    temperature_k: float | None = None,
) -> UnifiedVerdict:
    """Grade any built formal combination -- a step, a linear route, or a convergent DAG -- with one verdict.

    Dispatches on the subject's type.  For an UNBUILT (possibly non-conserving) combination -- raw reactants
    and products -- use :func:`classify_reaction`, the front door that can return ``REFUTED`` on conservation.
    """
    if type(subject) is ExperimentStep:
        return classify_step(
            subject, thermo=thermo, selectivity=selectivity, kinetics=kinetics, barriers=barriers,
            temperature_k=temperature_k,
        )
    if type(subject) is ExperimentRoute:
        return classify_route(
            subject, thermo=thermo, stability=stability, selectivity=selectivity, kinetics=kinetics,
            barriers=barriers, temperature_k=temperature_k,
        )
    if type(subject) is SynthesisDAG:
        return classify_dag(
            subject, thermo=thermo, stability=stability, selectivity=selectivity, kinetics=kinetics,
            temperature_k=temperature_k,
        )
    raise TypeError(
        "classify accepts an ExperimentStep, ExperimentRoute, or SynthesisDAG; for raw reactants/products "
        "use classify_reaction"
    )
