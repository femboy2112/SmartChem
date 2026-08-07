"""Compiled positive-frequency passive RLC phasor control.

This vertical is deliberately separate from the resistive-DC executor.  It retains one
fixed-frequency finite mathematical RLC presentation, an exact Q(i) boundary relation,
one complex sparse-MNA witness, and a production-independent verification record.  It
does not model a device, transient, transfer function, or port-Hamiltonian system.
"""

from __future__ import annotations

import os
import time

from .circuit_model_ir import CircuitModelIR, observe_circuit_model_ir
from .contracts import (
    ClaimKind,
    EvidenceStatus,
    ExecutionLane,
    ObligationOutcome,
    ObligationResult,
    ObligationStage,
    RunStatus,
    ValidityObligation,
    canonical_digest,
)
from .ledger import BindingSchema, COMPILED, Session, Slot
from .open_diagram import canonicalize
from .program import (
    Adapter,
    ApprovedPlan,
    Artifact,
    AssemblyEvidence,
    AssemblySpec,
    Boundary,
    CalculationSpec,
    CandidatePlan,
    Certificate,
    ClaimScope,
    Component,
    EquivalenceContract,
    ExecutionReport,
    Identity,
    Invariant,
    ModelSpec,
    ObservableRequest,
    OutputContract,
    PhysicalIR,
    ResolvedDomainProgram,
    RunJournal,
    RuntimeLimits,
    SimulationRequest,
    SimulationResult,
    SolverSpec,
    SourceProgram,
    SourceTheory,
    StructuredObservableValue,
    TargetIntent,
    TransportEvidence,
    TransportMap,
    _ExecutionAdmissionSnapshot,
    _RLC_AC_EXECUTOR,
    _compiler_implementation_digest,
    _execution_admission_error,
    _require_runtime_dispatch,
    _resource_wall,
)
from .rlc_ac_circuit import (
    ACCircuitError,
    ACResidualError,
    blackbox_rlc_ac,
    solve_rlc_ac,
)
from .rlc_ac_schema import (
    RLCACAnalysis,
    RLCACSubject,
    RLCModel,
)
from .rlc_ac_verifier import (
    DirectACVerificationReport,
    direct_preflight,
    verify_rlc_ac_analysis,
)

__all__ = [
    "RLC_AC_CASUALTIES",
    "RLC_AC_OMISSIONS",
    "ExactRLCACEngine",
    "RLCACAnalysis",
    "RLCACSubject",
    "analyze_rlc_ac",
    "circuit_model_ir_of",
    "compile_rlc_ac",
    "compile_session_rlc_ac",
    "rlc_ac_slot",
]


RLC_AC_CASUALTIES = (
    "non-ideal components, tolerance, temperature coefficient, aging, noise, failure, or parasitics",
    "transient initial conditions, switching, harmonics, distributed effects, radiation, or electromagnetic compatibility",
    "a physical device, component package, wiring layout, grounding practice, or safety claim",
    "active, controlled, nonlinear, semiconductor, distributed, quantum, or multi-frequency circuit behaviour",
    "a port-Hamiltonian, dynamic-state, or general transfer-function semantics",
)

RLC_AC_OMISSIONS = (
    "only finite positive ideal R/L/C elements at one exact positive angular frequency are admitted",
    "one declared RMS ideal-voltage phasor drive and one declared reference are solved",
    "the exact Q(i) relation and rank screen precede the retained binary64 complex sparse-MNA witness",
    "floating, singular, lossless-resonant, non-finite, ill-conditioned, and residual-failing cases are refused without regularization",
    "edge labels in the canonical model form are opaque exact kind/value spellings, not unit inference",
    "canonical comparison is an exact but bounded observer; presentation composition remains total when it refuses",
    "an explicit model-to-edge reindex witness binds the exact presentation; alpha-renamed presentations are not transported automatically",
    "finite controls and a separately implemented direct verifier are not a universal proof over all circuits or Python values",
)


def _ideal_rlc_model() -> ModelSpec:
    return ModelSpec(
        "finite passive ideal-RLC positive-frequency phasor relation with sparse MNA witness",
        (
            "Y_R=1/R, Y_L=1/(j omega L), and Y_C=j omega C at one omega>0",
            "sum phasor currents leaving each retained node equals zero",
            "V_positive-V_negative=V_drive",
            "sum branch absorbed complex powers plus ideal-source absorbed complex power equals zero",
        ),
        (
            "finite typed electrical open diagram",
            "every structural edge is one positive ideal resistor, inductor, or capacitor",
            "one exact positive angular frequency, RMS ideal-voltage phasor drive, and explicit reference boundary",
            "exact complex boundary relation/rank screen and sparse complex MNA are both evaluated",
        ),
        (
            "model parameters are bound to the exact diagram presentation digest",
            "all nodes are reference-connected through passive/source constraints",
            "the exact MNA matrix is full rank and the declared conditioning screen passes",
            "scaled KCL, source-constraint, complex-power, relation, and backward residuals pass",
        ),
        (
            "all structural edges, boundary relation rows, node phasors, branch values, source values, MNA state, and diagnostics are retained",
            "no scalar impedance, magnitude-only, or resonance-frequency output replaces the complete witness",
        ),
        (
            "KCL",
            "ideal-source phasor constraint",
            "source-inclusive complex-power balance",
            "one-frequency passive real-power checks",
        ),
        "1",
    )


def _component_labels(model: RLCModel) -> tuple[str, ...]:
    """Opaque exact labels preserving kind/value/model alignment in canonicalization.

    Delegates to :meth:`RLCModel.canonical_edge_labels`, the single source of the
    decoration convention shared with :class:`~smartchem.circuit_model_ir.CircuitModelIR`.
    """
    return model.canonical_edge_labels()


def analyze_rlc_ac(subject: RLCACSubject) -> RLCACAnalysis:
    """Compute complete exact-topology/relation and sparse phasor witnesses."""
    if type(subject) is not RLCACSubject:
        raise TypeError("subject must be an exact RLCACSubject")
    if subject.canonicalization_budget < 1:
        raise ValueError("canonicalization budget exhausted before analysis")
    structure = canonicalize(subject.diagram, budget=subject.canonicalization_budget)
    decorated = canonicalize(
        subject.diagram,
        budget=subject.canonicalization_budget,
        edge_labels=_component_labels(subject.model),
    )
    relation = blackbox_rlc_ac(subject.diagram, subject.model, subject.experiment.omega)
    solution = solve_rlc_ac(subject.diagram, subject.model, subject.experiment)
    return RLCACAnalysis(
        structure,
        decorated,
        subject.model.edge_bindings,
        relation,
        solution,
    )


def circuit_model_ir_of(subject: RLCACSubject) -> CircuitModelIR:
    """The optional fused-identity face of an RLC-AC subject (M-1a1 pipeline wiring).

    :func:`analyze_rlc_ac` computes the decorated canonical form inline and drops it,
    unnamed, into an :class:`~smartchem.rlc_ac_schema.RLCACAnalysis`; this derives the
    *named*, reusable :class:`~smartchem.circuit_model_ir.CircuitModelIR` for the SAME
    presentation at the SAME budget, reaching the plan-seam
    :class:`~smartchem.structure_ir.StructureIR` topology face the analysis never builds.

    It is an **optional face**, not a new analysis field.  :class:`RLCACAnalysis` is a
    frozen :class:`~smartchem.contracts.Digestible` whose identity must not move, so the
    fused identity is derived on demand rather than stored -- adding a field would silently
    change every analysis digest.  Nothing here touches, mutates, or re-solves the analysis.

    Because this and :func:`analyze_rlc_ac` both decorate through
    ``subject.model.canonical_edge_labels()``, the returned
    :attr:`~smartchem.circuit_model_ir.CircuitModelIR.decorated_canonical_form` is
    **byte-identical** to ``analyze_rlc_ac(subject).decorated_model_canonical_form`` -- the
    stated M-1a congruence, now reachable as a value.  That equality is *relational* (both
    sides share the label convention), so it certifies cross-world congruence, not label
    correctness; the absolute invariance of the identity is proved separately in
    ``tests/test_circuit_model_ir.py``.

    Fails closed exactly as :func:`~smartchem.circuit_model_ir.observe_circuit_model_ir`:
    an exhausted budget or an unobservable topology raises
    :class:`~smartchem.circuit_model_ir.CircuitModelIRError`, so a subject whose budget the
    analysis pipeline would also reject has no fused identity.  It refuses the *same*
    budget-starved subjects as :func:`analyze_rlc_ac`, but with this exception type rather
    than the canonicalizer's own budget error -- a caller wrapping both should catch each.
    """
    if type(subject) is not RLCACSubject:
        raise TypeError("subject must be an exact RLCACSubject")
    return observe_circuit_model_ir(
        subject.diagram, subject.model, budget=subject.canonicalization_budget
    )


class ExactRLCACEngine:
    """One-call E2 engine; it may not self-authorize a model or plan."""

    name = "SmartChem exact-Q(i) relation plus sparse-MNA passive-RLC engine"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": "exact Q(i) boundary relation/rank preflight plus scipy sparse complex modified nodal analysis",
            "domain": "finite positive ideal R/L/C elements at one exact positive angular frequency",
            "residuals": "scaled KCL, source constraint, complex power, relation, backward error, passivity, and conditioning",
            "version": 1,
        }

    def solve(self, subject: RLCACSubject) -> RLCACAnalysis:
        if type(subject) is not RLCACSubject:
            raise TypeError("engine requires an exact RLCACSubject")
        self.calls += 1
        return analyze_rlc_ac(subject)


def rlc_ac_slot(name: str, written: str) -> Slot:
    return Slot(name=name, written=written, schema=BindingSchema((RLCACSubject,)))


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                "rlc_ac_analysis",
                "complete typed positive-frequency passive-RLC structural/relation/sparse-MNA analysis",
                "typed exact-and-floating record",
                "the approved finite open diagram, exact R/L/C tuple, omega, and one approved RMS phasor drive",
                "canonical forms, exact Q(i) RREF relation, every node/branch/source/MNA value, and diagnostics",
                "exact Q(i) coefficients for topology/relation; declared floating residual and conditioning limits for MNA",
                "all structural edges and all solution records",
                (
                    "canonicalization budget",
                    "exact rank",
                    "conditioning",
                    "KCL",
                    "source constraint",
                    "complex power",
                    "relation residual",
                ),
                ("complete RLCACAnalysis",),
            ),
            ObservableRequest(
                "rlc_ac_boundary_relation",
                "exact positive-frequency passive-RLC boundary linear relation",
                "typed Q(i) RREF rows",
                "all ordered input/output RMS-voltage and inward-current phasor boundary variables",
                "every canonical Q(i) RREF row",
                "exact GaussianComplex coefficients",
                "complete relation without scalar impedance reduction",
                ("relation rank", "exact complex row reduction"),
                ("complete ComplexBoundaryRelation",),
            ),
            ObservableRequest(
                "rlc_ac_sparse_solution",
                "one grounded RMS ideal-voltage complex sparse-MNA witness",
                "typed RMS volts/amperes/VA record",
                "the exact approved omega/drive/reference and the same finite positive R/L/C diagram",
                "every node phasor, branch current/power, source observation, normalized MNA state, and diagnostics",
                "declared scaled residual and conditioning limits",
                "all nodes, branches, and MNA unknowns",
                (
                    "KCL",
                    "constraint",
                    "source-inclusive complex power",
                    "relation residual",
                    "backward error",
                    "passivity",
                    "conditioning",
                ),
                ("complete ACSolveResult",),
            ),
            ObservableRequest(
                "rlc_ac_direct_verification",
                "production-independent direct positive-frequency passive-RLC verification record",
                "typed verifier decision and dimension-separated diagnostics",
                "the approved topology, model, omega, experiment, and retained candidate analysis",
                "inventory, exact relation/rank, branch law, KCL, source, complex power, passivity, conditioning, and reasons",
                "exact Q(i) relation/rank comparison plus declared numerical limits",
                "every direct verification gate and residual",
                (
                    "independent implementation",
                    "lossless singular refusal",
                    "certification margin",
                    "fail-closed decision",
                ),
                ("complete DirectACVerificationReport",),
            ),
        ),
        diagnostics=(
            "runtime-owned fixed-frequency passive-RLC model identity",
            "exact alpha-invariant structural and kind/value-decorated canonical forms",
            "separate direct relation/rank, branch-law, KCL, source, complex-power, passivity, and conditioning verification before output emission",
            "refusal, quarantine, resource-cap, invalidity, and failure states",
        ),
        retention=(
            "source, resolved subject, complete plan, approval, and one engine checkpoint",
            "all four complete observable payloads, run record, and certificate",
        ),
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation(
            "RLC-AC-subject-and-model-are-exact",
            ObligationStage.PRE,
            "smartchem.rlc_ac/exact-subject-model-v1",
            "subject binds an exact presentation, exact R/L/C tuple, exact omega, and runtime-owned passive-RLC model",
        ),
        ValidityObligation(
            "RLC-AC-literal-scope-remains-narrow",
            ObligationStage.PRE,
            "smartchem.rlc_ac/literal-casualty-boundary-v1",
            "literal status remains confined to declared fixed-frequency ideal circuit mathematics",
        ),
        ValidityObligation(
            "RLC-AC-canonicalization-budget-is-available",
            ObligationStage.PRE,
            "smartchem.rlc_ac/canonicalization-budget-v1",
            "the declared observer budget can construct structural and kind/value-decorated forms",
        ),
        ValidityObligation(
            "RLC-AC-analysis-passes-direct-verification",
            ObligationStage.POST,
            "smartchem.rlc_ac/direct-verification-v1",
            "checkpoint passes the production-independent passive-RLC verifier",
        ),
        ValidityObligation(
            "RLC-AC-rank-residual-passivity-gates-pass",
            ObligationStage.POST,
            "smartchem.rlc_ac/rank-residual-passivity-v1",
            "exact rank, conditioning, KCL, source, complex-power, and passive real-power gates pass",
        ),
        ValidityObligation(
            "RLC-AC-output-inventory-is-exact",
            ObligationStage.POST,
            "smartchem.rlc_ac/output-inventory-v1",
            "emitted output IDs exactly equal the frozen contract",
        ),
    )


def _scope() -> ClaimScope:
    return ClaimScope(
        ClaimKind.LITERAL,
        "the exact finite ideal R/L/C one-frequency phasor equations and declared sparse-MNA numerical witness",
        RLC_AC_CASUALTIES,
    )


def compile_rlc_ac(
    source: SourceProgram | str,
    subject: RLCACSubject,
    engine: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """Compile the narrow passive-RLC vertical without executing its one-call engine."""
    if type(source) is str:
        source = SourceProgram(source)
    if type(source) is not SourceProgram or type(subject) is not RLCACSubject:
        raise TypeError(
            "source must be SourceProgram or str and subject must be RLCACSubject"
        )
    source_theory = SourceTheory(
        "finite positive-frequency passive-RLC phasor equations",
        (
            "each finite structural edge has one exact positive ideal R/L/C parameter",
            "one exact positive angular frequency is declared",
            "phasor KCL holds at every retained node and the experiment declares reference and ideal voltage-source terminals",
        ),
        ("smartchem.open_diagram", "smartchem.rlc_ac_circuit"),
    )
    target = TargetIntent(
        source.text,
        "one finite positive-frequency passive-RLC open circuit under a declared RMS phasor experiment",
        "retain the exact Q(i) boundary relation and one sparse complex-MNA witness without scalar impedance reduction",
    )
    resolved = ResolvedDomainProgram(
        source.digest, subject, target, source_theory, shepherd_session_digest
    )
    model = _ideal_rlc_model()
    transport = TransportMap(
        source_theory.digest,
        target.digest,
        (
            "typed port order",
            "finite topology",
            "exact positive R/L/C parameters",
            "one exact positive frequency",
            "KCL and source phasor polarity",
        ),
        (
            "equations become exact Q(i) RREF boundary rows, an exact rank screen, and one sparse complex numerical witness",
        ),
        RLC_AC_CASUALTIES,
        (),
    )
    assembly = AssemblySpec(
        "finite-open-electrical-diagram",
        "resolved construction-local IDs erased into a typed finite graph presentation",
        (
            f"presentation_digest={canonical_digest(subject.diagram)}",
            f"edge_count={len(subject.diagram.edges)}",
            f"node_count={len(subject.diagram.node_kinds)}",
            f"omega={subject.experiment.omega.radians_per_second.numerator}/{subject.experiment.omega.radians_per_second.denominator}",
        ),
    )
    component = Component(
        "ideal-passive-RLC-open-diagram",
        "finite typed ideal R/L/C structure",
        Identity(
            canonical_digest(subject.diagram),
            "positive-frequency-passive-RLC-open-structure",
            (("edge-count", str(len(subject.diagram.edges))),),
        ),
    )
    physical_ir = PhysicalIR(
        resolved_digest=resolved.digest,
        components=(component,),
        connections=(),
        reservoirs=(),
        boundaries=(
            Boundary(
                "declared-open-boundaries",
                (component.component_id,),
                "ordered input/output electrical ports; RMS phasor drive, reference, and omega are retained in the typed subject",
            ),
        ),
        models=(model,),
        adapters=(
            Adapter(
                "open-diagram to passive positive-frequency phasor boundary relation",
                "typed finite open graph",
                "exact Q(i) boundary relation, rank screen, and one sparse complex-MNA witness",
                _default_output_contract().observable_ids,
                (
                    "positive exact R/L/C values",
                    "positive exact omega",
                    "ordered boundary variables",
                    "one declared experiment",
                ),
                "no material-device, transient, or dynamic-state interpretation",
            ),
        ),
        invariants=(
            Invariant(
                "exact topology/model binding",
                "R/L/C tuple digest names exactly this presentation",
                "this subject",
                "smartchem.rlc_ac/exact-subject-model-v1",
            ),
            Invariant(
                "rank, residual, and passivity gates",
                "exact rank/conditioning and KCL/source/complex-power/relation residuals plus passive real power are checked",
                "one approved sparse complex-MNA witness",
                "smartchem.rlc_ac/rank-residual-passivity-v1",
            ),
        ),
        transport_maps=(transport,),
        transport_evidence=(
            TransportEvidence(
                transport.digest,
                (
                    "typed boundary order",
                    "exact R/L/C data",
                    "exact positive omega",
                    "ideal-source RMS sign convention",
                ),
                (
                    "exact Q(i) relation/rank elimination",
                    "independent sparse-MNA residual checks",
                ),
                (),
            ),
        ),
        assemblies=(assembly,),
        assembly_evidence=(
            AssemblyEvidence(
                assembly.digest,
                (
                    "exact component-terminal coverage",
                    "ordered boundary maps",
                    "edge declaration order retained for model alignment",
                ),
                (),
            ),
        ),
        claim_scope=_scope(),
        evidence_status=EvidenceStatus.VALIDATED_WITHIN_REGIME,
    )
    contract = output_contract or _default_output_contract()
    request = SimulationRequest(
        source,
        resolved,
        physical_ir,
        contract,
        equivalence_contract
        or EquivalenceContract(
            "exact equality of subject, canonical forms, Q(i) boundary relation, exact rank decision, and all typed sparse complex-MNA records under separate direct verification",
            (
                (
                    "scaled residual tolerance",
                    float(subject.experiment.scaled_tolerance),
                ),
                ("conditioning limit", float(subject.experiment.conditioning_limit)),
            ),
            "boundary order is all input ports then all output ports; model labels follow edge declaration order",
            "no RNG",
            "one indivisible engine call; interruption quarantines every checkpoint and observable",
            (),
        ),
        _obligations(),
    )
    blockers = (
        ()
        if contract == _default_output_contract()
        else (
            "this narrow executor can honor only its exact default output contract; changing support, frequency, resolution, precision, coverage, diagnostics, retention, or observable membership requires a different validated executor",
        )
    )
    return CandidatePlan(
        request,
        model,
        SolverSpec(
            getattr(engine, "name", type(engine).__qualname__),
            "exact Q(i) boundary relation/rank preflight plus one scipy sparse complex MNA solve",
            "1",
            (
                (
                    "scaled residual tolerance",
                    float(subject.experiment.scaled_tolerance),
                ),
                ("conditioning limit", float(subject.experiment.conditioning_limit)),
            ),
            "one complete solve or refusal/quarantine",
            "immutable subject/model/omega/drive plus calculation specification",
        ),
        CalculationSpec.from_oracle(engine),
        _compiler_implementation_digest(),
        _RLC_AC_EXECUTOR,
        (),
        (
            ("engine calls", "1"),
            ("retained structural edges", str(len(subject.diagram.edges))),
            ("retained nodes", str(len(subject.diagram.node_kinds))),
            ("canonicalization budget", str(subject.canonicalization_budget)),
        ),
        blockers,
        ExecutionLane.CERTIFIED,
        limits or RuntimeLimits(max_engine_calls=1),
    )


def compile_session_rlc_ac(
    source: SourceProgram | str,
    session: Session,
    slot_name: str,
    engine: object,
    **kwargs: object,
) -> CandidatePlan:
    if (
        type(session) is not Session
        or session.outcome != COMPILED
        or session.spec.measure() != 0
        or session.spec.subject_to()
    ):
        raise ValueError(
            "RLC-AC execution requires an outright closed COMPILED typed session"
        )
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if slot.typed_binding is None or type(slot.typed_binding.value) is not RLCACSubject:
        raise TypeError(f"slot {slot_name!r} must hold an exact RLCACSubject")
    return compile_rlc_ac(
        source,
        slot.typed_binding.value,
        engine,
        shepherd_session_digest=canonical_digest(session),
        **kwargs,
    )


def _payloads(
    analysis: RLCACAnalysis, verification: DirectACVerificationReport
) -> dict[str, object]:
    return {
        "rlc_ac_analysis": analysis,
        "rlc_ac_boundary_relation": analysis.boundary_relation,
        "rlc_ac_sparse_solution": analysis.sparse_solution,
        "rlc_ac_direct_verification": verification,
    }


def _result(
    obligation: ValidityObligation, outcome: ObligationOutcome, detail: str
) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _pre_result(
    obligation: ValidityObligation, approved: ApprovedPlan, subject: RLCACSubject
) -> ObligationResult:
    plan = approved.plan
    if obligation.evaluator_id == "smartchem.rlc_ac/exact-subject-model-v1":
        model_bound = (
            plan.model == _ideal_rlc_model()
            and plan.request.physical_ir.models == (_ideal_rlc_model(),)
        )
        try:
            subject.model.validate_diagram(subject.diagram)
        except (TypeError, ValueError):
            model_bound = False
        direct = direct_preflight(subject)
        if not model_bound:
            return _result(
                obligation,
                ObligationOutcome.REFUSE,
                "subject/model/frequency binding differs from the approved passive-RLC vertical",
            )
        if not direct.passed:
            return _result(
                obligation,
                ObligationOutcome.REFUSE,
                "direct subject preflight refused: " + "; ".join(direct.reasons),
            )
        return _result(
            obligation,
            ObligationOutcome.PASS,
            "exact subject model, positive frequency, and runtime-owned passive-RLC model are bound",
        )
    if obligation.evaluator_id == "smartchem.rlc_ac/literal-casualty-boundary-v1":
        ir = plan.request.physical_ir
        passed = (
            ir.claim_scope == _scope()
            and ir.evidence_status is EvidenceStatus.VALIDATED_WITHIN_REGIME
            and plan.execution_lane is ExecutionLane.CERTIFIED
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            "literal scope is confined to fixed-frequency ideal circuit mathematics"
            if passed
            else "claim scope, evidence, lane, or casualties were widened",
        )
    if obligation.evaluator_id == "smartchem.rlc_ac/canonicalization-budget-v1":
        if subject.canonicalization_budget < 1:
            return _result(
                obligation,
                ObligationOutcome.REFUSE,
                "declared canonicalization budget is exhausted before analysis",
            )
        try:
            canonicalize(subject.diagram, budget=subject.canonicalization_budget)
            canonicalize(
                subject.diagram,
                budget=subject.canonicalization_budget,
                edge_labels=_component_labels(subject.model),
            )
        except Exception as error:
            return _result(
                obligation,
                ObligationOutcome.REFUSE,
                f"canonicalization refused: {type(error).__name__}: {error}",
            )
        return _result(
            obligation,
            ObligationOutcome.PASS,
            "structural and kind/value-decorated canonical forms fit the declared budget",
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no evaluator registered for {obligation.evaluator_id}",
    )


def _post_result(
    obligation: ValidityObligation,
    verification: DirectACVerificationReport,
    emitted: tuple[str, ...],
    expected: tuple[str, ...],
) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.rlc_ac/direct-verification-v1":
        return _result(
            obligation,
            ObligationOutcome.PASS if verification.passed else ObligationOutcome.FAIL,
            "checkpoint passed the production-independent exact-relation/rank and direct-physics verifier"
            if verification.passed
            else "; ".join(verification.reasons),
        )
    if obligation.evaluator_id == "smartchem.rlc_ac/rank-residual-passivity-v1":
        return _result(
            obligation,
            ObligationOutcome.PASS if verification.passed else ObligationOutcome.FAIL,
            "direct rank, conditioning, branch-law, KCL, source, complex-power, and passive-real-power gates pass"
            if verification.passed
            else "; ".join(verification.reasons),
        )
    if obligation.evaluator_id == "smartchem.rlc_ac/output-inventory-v1":
        passed = tuple(sorted(emitted)) == tuple(sorted(expected))
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            f"expected={sorted(expected)}, emitted={sorted(emitted)}",
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no evaluator registered for {obligation.evaluator_id}",
    )


def _preflight_rlc_ac(plan: CandidatePlan) -> None:
    if plan.executor_id != _RLC_AC_EXECUTOR:
        raise ValueError("RLC-AC preflight received a different executor plan")
    expected = _ideal_rlc_model()
    if plan.model != expected or plan.request.physical_ir.models != (expected,):
        raise ValueError(
            "RLC-AC executor requires its exact runtime-owned passive-RLC model"
        )
    if plan.transforms:
        raise ValueError("RLC-AC executor does not support transforms")


def _execute_rlc_ac(
    approved: ApprovedPlan,
    engine: object,
    *,
    actual_calculation: CalculationSpec,
    journal_path: str | os.PathLike[str] | None = None,
    _dispatch_token: object = None,
    _admission_snapshot: _ExecutionAdmissionSnapshot | None = None,
) -> ExecutionReport:
    _require_runtime_dispatch(_dispatch_token)
    plan = approved.plan
    _preflight_rlc_ac(plan)
    resolved = plan.request.resolved
    if (
        type(resolved) is not ResolvedDomainProgram
        or type(resolved.subject) is not RLCACSubject
    ):
        raise TypeError(
            "RLC-AC executor requires an exact ResolvedDomainProgram RLCACSubject"
        )
    subject = resolved.subject
    if type(_admission_snapshot) is not _ExecutionAdmissionSnapshot:
        raise TypeError("RLC-AC executor requires an execution admission snapshot")
    started = time.monotonic()
    journal = RunJournal(
        approved, backend=actual_calculation.engine_name, path=journal_path
    )
    try:
        for artifact_id, kind, payload in (
            ("source-program", "source", plan.request.source),
            ("candidate-plan", "plan", plan),
            ("approval", "approval", approved.approval),
        ):
            journal.add_artifact(
                Artifact(
                    artifact_id, kind, payload.digest, True, False, payload=payload
                )
            )
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.PRE:
                verdict = _pre_result(obligation, approved, subject)
                journal.add_obligation_result(verdict)
                if (
                    obligation.required
                    and verdict.outcome is not ObligationOutcome.PASS
                ):
                    return ExecutionReport(
                        journal.refused(
                            f"precondition {obligation.name} ended {verdict.outcome.value}: {verdict.detail}"
                        ),
                        None,
                        None,
                    )
        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=0,
            call_label="passive-RLC engine calls",
        )
        if breach is not None or (
            plan.limits.max_engine_calls is not None
            and plan.limits.max_engine_calls < 1
        ):
            return ExecutionReport(
                journal.incomplete(
                    breach
                    or "approved engine-call cap reached before passive-RLC analysis"
                ),
                None,
                None,
            )
        solver = getattr(engine, "solve", None)
        if not callable(solver):
            raise TypeError("RLC-AC engine must expose solve(RLCACSubject)")
        try:
            analysis = solver(subject)
        except ACResidualError as error:
            admission_error = _execution_admission_error(
                approved, subject, _admission_snapshot
            )
            if admission_error is not None:
                return ExecutionReport(journal.invalid(admission_error), None, None)
            return ExecutionReport(
                journal.invalid(f"RLC-AC residual gate failed: {error}"), None, None
            )
        except ACCircuitError as error:
            admission_error = _execution_admission_error(
                approved, subject, _admission_snapshot
            )
            if admission_error is not None:
                return ExecutionReport(journal.invalid(admission_error), None, None)
            return ExecutionReport(
                journal.refused(f"RLC-AC circuit interpretation refused: {error}"),
                None,
                None,
            )
        admission_error = _execution_admission_error(
            approved, subject, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        if type(analysis) is not RLCACAnalysis:
            return ExecutionReport(
                journal.invalid("RLC-AC engine returned no exact RLCACAnalysis"),
                None,
                None,
            )
        journal.add_checkpoint(
            Artifact(
                "checkpoint:RLC-AC-analysis",
                "checkpoint",
                analysis.digest,
                True,
                False,
                detail=f"edges={len(subject.diagram.edges)} nodes={len(subject.diagram.node_kinds)} omega={subject.experiment.omega.radians_per_second.numerator}/{subject.experiment.omega.radians_per_second.denominator}",
                payload=analysis,
            )
        )
        observed_calculation = CalculationSpec.from_oracle(engine)
        admission_error = _execution_admission_error(
            approved, subject, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        if observed_calculation.digest != plan.calculation.digest:
            raise RuntimeError(
                "CalculationSpec changed during the approved passive-RLC engine call"
            )
        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=1,
            call_label="passive-RLC engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        verification = verify_rlc_ac_analysis(subject, analysis)
        if not verification.passed:
            for obligation in plan.request.obligations:
                if obligation.stage is ObligationStage.POST:
                    journal.add_obligation_result(
                        _post_result(
                            obligation,
                            verification,
                            (),
                            plan.request.output_contract.observable_ids,
                        )
                    )
            return ExecutionReport(
                journal.invalid(
                    f"production-independent RLC-AC verification ended {verification.decision.value}: {'; '.join(verification.reasons)}"
                ),
                None,
                None,
            )
        payloads = _payloads(analysis, verification)
        emitted: list[str] = []
        for observable_id in plan.request.output_contract.observable_ids:
            payload = payloads[observable_id]
            journal.add_artifact(
                Artifact(
                    f"observable:{observable_id}",
                    "observable",
                    canonical_digest(payload),
                    True,
                    False,
                    detail=f"complete {observable_id}",
                    payload=payload,
                )
            )
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        journal.add_cache_state(
            "no cache: one complete exact-Q(i)-relation/rank plus sparse-complex-MNA engine call"
        )
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.POST:
                verdict = _post_result(
                    obligation,
                    verification,
                    emitted_ids,
                    plan.request.output_contract.observable_ids,
                )
                journal.add_obligation_result(verdict)
                if (
                    obligation.required
                    and verdict.outcome is not ObligationOutcome.PASS
                ):
                    return ExecutionReport(
                        journal.invalid(
                            f"postcondition {obligation.name} ended {verdict.outcome.value}: {verdict.detail}"
                        ),
                        None,
                        None,
                    )
        admission_error = _execution_admission_error(
            approved, subject, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        certificate = Certificate(
            plan.request.source.digest,
            plan.request.digest,
            plan.digest,
            approved.approval.digest,
            actual_calculation.digest,
            plan.compiler_implementation_digest,
            journal.record.run_id,
            RunStatus.COMPLETE,
            plan.request.physical_ir.claim_scope,
            plan.request.physical_ir.evidence_status,
            journal.record.obligation_results,
            emitted_ids,
            RLC_AC_CASUALTIES,
            RLC_AC_OMISSIONS,
            (),
        )
        journal.add_artifact(
            Artifact(
                "certificate",
                "certificate",
                certificate.digest,
                True,
                False,
                payload=certificate,
            )
        )
        elapsed = time.monotonic() - started
        values = tuple(
            StructuredObservableValue(
                observable_id,
                payloads[observable_id],
                next(
                    item.unit
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                "positive-frequency passive-RLC exact-Q(i) sparse-MNA v1",
                next(
                    item.support
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                elapsed,
                "VALIDATED_WITHIN_REGIME for the declared fixed-frequency ideal mathematical circuit only.",
                "See certificate casualties and omissions.",
            )
            for observable_id in emitted_ids
        )
        result = SimulationResult(journal.record.run_id, values, certificate.digest)
        record = journal.complete()
        return (
            ExecutionReport(record, result, certificate)
            if record.status is RunStatus.COMPLETE
            else ExecutionReport(record, None, None)
        )
    except Exception as error:
        admission_error = _execution_admission_error(
            approved, subject, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        return ExecutionReport(
            journal.failed(f"{type(error).__name__}: {error}"), None, None
        )
