"""Compiled ideal-resistor DC control over the finite open-diagram syntax.

The claim is literal only for the declared mathematical circuit: positive ideal resistors,
an ideal voltage drive, exact rational topology parameters, and the stated sparse numerical
acceptance gates.  It is not a claim about an assembled device, parasitics, AC/RLC, thermal
behaviour, safety, or any material implementation.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

from .circuit import (
    BoundaryLinearRelation,
    CircuitError,
    CircuitDiagnostics,
    CircuitResidualError,
    DCSolveResult,
    DCSolveSpec,
    ResistiveDCModel,
    blackbox_resistive_dc,
    solve_resistive_dc,
)
from .contracts import (
    ClaimKind,
    Digestible,
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
from .open_diagram import CanonicalDiagram, OpenDiagram, canonicalize
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
    _RESISTIVE_DC_EXECUTOR,
    _compiler_implementation_digest,
    _require_runtime_dispatch,
    _resource_wall,
)

__all__ = [
    "RESISTIVE_DC_CASUALTIES",
    "RESISTIVE_DC_OMISSIONS",
    "ExactResistiveDCEngine",
    "ResistiveDCAnalysis",
    "ResistiveDCSubject",
    "analyze_resistive_dc",
    "compile_resistive_dc",
    "compile_session_resistive_dc",
    "resistive_dc_slot",
]


RESISTIVE_DC_CASUALTIES = (
    "non-ideal resistor behaviour, tolerance, temperature coefficient, aging, noise, or failure",
    "inductance, capacitance, electromagnetic radiation, transients, AC phasors, or resonance",
    "a physical device, component package, wiring layout, grounding practice, or safety claim",
    "nonlinear, active, controlled, semiconductor, distributed, or quantum circuit behaviour",
    "a categorical semantics for arbitrary domain models beyond this ideal resistor relation",
)

RESISTIVE_DC_OMISSIONS = (
    "only finite positive ideal resistors are admitted",
    "one declared ideal-voltage drive and one declared reference are solved",
    "resistance parameters are exact rationals while the sparse MNA witness is floating point",
    "floating, singular, non-finite, and residual-failing numerical cases are refused",
    "edge labels in the canonical model form are opaque exact resistance spellings, not units inference",
    "canonical comparison is an exact but bounded observer; presentation composition remains total when it refuses",
    "resistance tuples bind the exact declaration-order presentation, not an automatically transported alpha-renamed model",
    "finite control tests and deterministic recomputation are not a universal proof over all circuits or Python values",
)


def _ideal_resistor_model() -> ModelSpec:
    return ModelSpec(
        "finite passive ideal-resistor DC relation with sparse MNA witness",
        (
            "i_e=(V_a-V_b)/R_e for every R_e>0",
            "sum currents leaving each internal node equals zero",
            "V_positive-V_negative=V_drive",
            "sum resistor absorbed power plus ideal-source absorbed power equals zero",
        ),
        (
            "finite typed electrical open diagram",
            "every structural edge is a positive ideal resistor",
            "one exact-rational ideal-voltage experiment and explicit reference boundary",
            "sparse MNA and exact boundary relation are both evaluated",
        ),
        (
            "model parameters are bound to the exact diagram presentation digest",
            "all nodes are reference-connected through resistor/source constraints",
            "scaled KCL, voltage-constraint, power, and relation residuals pass",
        ),
        (
            "all structural edges, boundary relation rows, node voltages, branch values, and diagnostics are retained",
            "no output reduction or scalar series-parallel shortcut is used",
        ),
        ("KCL", "ideal source voltage constraint", "nonnegative resistor dissipation"),
        "1",
    )


@dataclass(frozen=True)
class ResistiveDCSubject(Digestible):
    """Exact structure, declaration-order model, experiment, and observer budget."""

    diagram: OpenDiagram
    model: ResistiveDCModel
    experiment: DCSolveSpec
    canonicalization_budget: int

    def __post_init__(self) -> None:
        if type(self.diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        if type(self.model) is not ResistiveDCModel:
            raise TypeError("model must be an exact ResistiveDCModel")
        if type(self.experiment) is not DCSolveSpec:
            raise TypeError("experiment must be an exact DCSolveSpec")
        if type(self.canonicalization_budget) is not int or self.canonicalization_budget < 0:
            raise ValueError("canonicalization_budget must be a non-negative exact integer")
        self.model.validate_diagram(self.diagram)


@dataclass(frozen=True)
class ResistiveDCAnalysis(Digestible):
    """Retained structural, exact-relation, and sparse-MNA witnesses from one engine call."""

    structural_canonical_form: CanonicalDiagram
    decorated_model_canonical_form: CanonicalDiagram
    boundary_relation: BoundaryLinearRelation
    sparse_solution: DCSolveResult

    def __post_init__(self) -> None:
        if type(self.structural_canonical_form) is not CanonicalDiagram:
            raise TypeError("structural_canonical_form must be an exact CanonicalDiagram")
        if type(self.decorated_model_canonical_form) is not CanonicalDiagram:
            raise TypeError("decorated_model_canonical_form must be an exact CanonicalDiagram")
        if type(self.boundary_relation) is not BoundaryLinearRelation:
            raise TypeError("boundary_relation must be an exact BoundaryLinearRelation")
        if type(self.sparse_solution) is not DCSolveResult:
            raise TypeError("sparse_solution must be an exact DCSolveResult")


def _resistance_labels(model: ResistiveDCModel) -> tuple[str, ...]:
    """Opaque exact labels that preserve resistance/model alignment during canonicalization."""
    return tuple(
        f"{resistance.ohms.numerator}/{resistance.ohms.denominator} ohm"
        for resistance in model.resistances
    )


def analyze_resistive_dc(subject: ResistiveDCSubject) -> ResistiveDCAnalysis:
    """Compute the exact topology/relation and separately recomputed sparse witness."""
    if type(subject) is not ResistiveDCSubject:
        raise TypeError("subject must be an exact ResistiveDCSubject")
    if subject.canonicalization_budget < 1:
        raise ValueError("canonicalization budget exhausted before analysis")
    structure = canonicalize(subject.diagram, budget=subject.canonicalization_budget)
    decorated = canonicalize(
        subject.diagram,
        budget=subject.canonicalization_budget,
        edge_labels=_resistance_labels(subject.model),
    )
    relation = blackbox_resistive_dc(subject.diagram, subject.model)
    solution = solve_resistive_dc(subject.diagram, subject.model, subject.experiment)
    return ResistiveDCAnalysis(structure, decorated, relation, solution)


class ExactResistiveDCEngine:
    """One-call engine: it may not self-authorize a runtime model or plan."""

    name = "SmartChem exact-relation plus sparse-MNA ideal-resistor engine"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": "exact rational boundary relation plus scipy sparse modified nodal analysis",
            "domain": "finite positive ideal resistors with one ideal-voltage drive",
            "residuals": "scaled KCL, source constraint, power, and exact-relation witness",
            "version": 1,
        }

    def solve(self, subject: ResistiveDCSubject) -> ResistiveDCAnalysis:
        if type(subject) is not ResistiveDCSubject:
            raise TypeError("engine requires an exact ResistiveDCSubject")
        self.calls += 1
        return analyze_resistive_dc(subject)


def resistive_dc_slot(name: str, written: str) -> Slot:
    return Slot(name=name, written=written, schema=BindingSchema((ResistiveDCSubject,)))


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                "resistive_dc_analysis",
                "complete typed ideal-resistor structural/relation/sparse-MNA analysis",
                "typed exact-and-floating record",
                "the approved finite open diagram, exact resistance tuple, and one approved drive",
                "canonical forms, exact RREF relation, every node/branch/source value and residual",
                "exact fractions for topology/relation; declared floating residual tolerance for MNA",
                "all structural edges and all solution records",
                ("canonicalization budget", "KCL", "source constraint", "power", "relation residual"),
                ("complete ResistiveDCAnalysis",),
            ),
            ObservableRequest(
                "resistive_dc_boundary_relation",
                "exact passive boundary linear relation",
                "typed rational RREF rows",
                "all ordered input/output voltage and inward-current boundary variables",
                "every canonical RREF row",
                "exact Rational coefficients",
                "complete relation without scalar impedance reduction",
                ("relation rank", "exact row reduction"),
                ("complete BoundaryLinearRelation",),
            ),
            ObservableRequest(
                "resistive_dc_sparse_solution",
                "one grounded ideal-voltage sparse MNA witness",
                "typed volts/amperes/watts record",
                "the exact approved drive/reference and the same finite positive resistor diagram",
                "every node voltage, branch current/power, source observation, and diagnostics",
                "declared scaled residual tolerance", "all nodes and all branches",
                ("KCL", "constraint", "global power", "relation residual", "passivity"),
                ("complete DCSolveResult",),
            ),
        ),
        diagnostics=(
            "runtime-owned ideal-resistor model identity",
            "exact alpha-invariant canonical forms",
            "separate deterministic recomputation before certificate completion",
            "refusal, quarantine, resource-cap, invalidity, and failure states",
        ),
        retention=(
            "source, resolved subject, complete plan, approval, and one engine checkpoint",
            "all three complete observable payloads, run record, and certificate",
        ),
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation("resistive-DC-subject-and-model-are-exact", ObligationStage.PRE,
            "smartchem.resistive_dc/exact-subject-model-v1", "subject binds an exact presentation, exact resistance tuple, and runtime-owned ideal-resistor model"),
        ValidityObligation("resistive-DC-literal-scope-remains-narrow", ObligationStage.PRE,
            "smartchem.resistive_dc/literal-casualty-boundary-v1", "literal status remains confined to the declared ideal mathematical circuit"),
        ValidityObligation("resistive-DC-canonicalization-budget-is-available", ObligationStage.PRE,
            "smartchem.resistive_dc/canonicalization-budget-v1", "the declared observer budget can construct both structural and resistance-decorated forms"),
        ValidityObligation("resistive-DC-analysis-recomputes-exactly", ObligationStage.POST,
            "smartchem.resistive_dc/analysis-recomputation-v1", "checkpoint equals separate deterministic topology/relation/MNA recomputation"),
        ValidityObligation("resistive-DC-residual-and-passivity-gates-pass", ObligationStage.POST,
            "smartchem.resistive_dc/residual-passivity-v1", "every retained resistor is passive and every declared scaled residual is within tolerance"),
        ValidityObligation("resistive-DC-output-inventory-is-exact", ObligationStage.POST,
            "smartchem.resistive_dc/output-inventory-v1", "emitted output IDs exactly equal the frozen contract"),
    )


def _scope() -> ClaimScope:
    return ClaimScope(
        ClaimKind.LITERAL,
        "the exact finite ideal-resistor equations and the declared sparse-MNA numerical witness",
        RESISTIVE_DC_CASUALTIES,
    )


def compile_resistive_dc(
    source: SourceProgram | str,
    subject: ResistiveDCSubject,
    engine: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """Compile the narrow ideal-resistor vertical without executing its one-call engine."""
    if type(source) is str:
        source = SourceProgram(source)
    if type(source) is not SourceProgram or type(subject) is not ResistiveDCSubject:
        raise TypeError("source must be SourceProgram or str and subject must be ResistiveDCSubject")
    source_theory = SourceTheory(
        "finite passive ideal-resistor DC equations",
        (
            "each finite structural edge has one exact positive resistance",
            "KCL holds at every retained node",
            "the experiment declares reference and ideal voltage source terminals",
        ),
        ("smartchem.open_diagram", "smartchem.circuit"),
    )
    target = TargetIntent(
        source.text,
        "one finite ideal-resistor open circuit under a declared DC experiment",
        "retain the exact boundary relation and one sparse-MNA witness without series-parallel reduction",
    )
    resolved = ResolvedDomainProgram(source.digest, subject, target, source_theory, shepherd_session_digest)
    model = _ideal_resistor_model()
    transport = TransportMap(
        source_theory.digest, target.digest,
        ("typed port order", "finite topology", "positive exact resistor parameters", "KCL and source polarity"),
        ("equations become exact RREF boundary rows plus one sparse numerical witness",),
        RESISTIVE_DC_CASUALTIES, (),
    )
    assembly = AssemblySpec(
        "finite-open-electrical-diagram",
        "resolved construction-local IDs erased into a typed finite graph presentation",
        (
            f"presentation_digest={canonical_digest(subject.diagram)}",
            f"edge_count={len(subject.diagram.edges)}",
            f"node_count={len(subject.diagram.node_kinds)}",
        ),
    )
    component = Component(
        "ideal-resistor-open-diagram",
        "finite typed ideal-resistor structure",
        Identity(
            canonical_digest(subject.diagram),
            "resistive-DC-open-structure",
            (("edge-count", str(len(subject.diagram.edges))),),
        ),
    )
    physical_ir = PhysicalIR(
        resolved_digest=resolved.digest,
        components=(component,), connections=(), reservoirs=(),
        boundaries=(Boundary("declared-open-boundaries", (component.component_id,), "ordered input/output electrical ports; drive and reference are retained in the typed subject"),),
        models=(model,),
        adapters=(Adapter("open-diagram to passive boundary relation", "typed finite open graph", "exact rational boundary relation and one sparse MNA witness", _default_output_contract().observable_ids,
            ("positive exact resistances", "ordered boundary variables", "one declared experiment"), "no material-device or dynamic interpretation"),),
        invariants=(
            Invariant("exact topology/model binding", "resistance tuple digest names exactly this presentation", "this subject", "smartchem.resistive_dc/exact-subject-model-v1"),
            Invariant("residual and passivity gates", "KCL/source/power/relation residuals and resistor dissipation are checked", "one approved sparse-MNA witness", "smartchem.resistive_dc/residual-passivity-v1"),
        ),
        transport_maps=(transport,),
        transport_evidence=(TransportEvidence(transport.digest, ("typed boundary order", "exact Rational resistance data", "ideal-source sign convention"), ("exact relation elimination", "independent sparse MNA residual checks"), ()),),
        assemblies=(assembly,),
        assembly_evidence=(AssemblyEvidence(assembly.digest, ("exact component-terminal coverage", "ordered boundary maps", "edge declaration order retained for model alignment"), ()),),
        claim_scope=_scope(), evidence_status=EvidenceStatus.VALIDATED_WITHIN_REGIME,
    )
    contract = output_contract or _default_output_contract()
    request = SimulationRequest(
        source, resolved, physical_ir, contract,
        equivalence_contract or EquivalenceContract(
            "exact equality of subject, canonical forms, rational boundary relation, and all typed sparse-MNA records under separate deterministic recomputation",
            (("scaled residual tolerance", float(subject.experiment.scaled_tolerance)),),
            "boundary order is all input ports then all output ports; model labels follow edge declaration order",
            "no RNG", "one indivisible engine call; interruption quarantines every checkpoint and observable", (),
        ),
        _obligations(),
    )
    blockers = () if contract == _default_output_contract() else (
        "this narrow executor can honor only its exact default output contract; changing support, resolution, precision, coverage, diagnostics, retention, or observable membership requires a different validated executor",
    )
    return CandidatePlan(
        request, model,
        SolverSpec(getattr(engine, "name", type(engine).__qualname__), "exact rational boundary relation plus one scipy sparse MNA solve", "1", (("scaled residual tolerance", float(subject.experiment.scaled_tolerance)),), "one complete solve or refusal/quarantine", "immutable subject/model/drive plus calculation specification"),
        CalculationSpec.from_oracle(engine), _compiler_implementation_digest(), _RESISTIVE_DC_EXECUTOR, (),
        (("engine calls", "1"), ("retained structural edges", str(len(subject.diagram.edges))), ("retained nodes", str(len(subject.diagram.node_kinds))), ("canonicalization budget", str(subject.canonicalization_budget))),
        blockers, ExecutionLane.CERTIFIED, limits or RuntimeLimits(max_engine_calls=1),
    )


def compile_session_resistive_dc(source: SourceProgram | str, session: Session, slot_name: str, engine: object, **kwargs: object) -> CandidatePlan:
    if type(session) is not Session or session.outcome != COMPILED or session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError("resistive-DC execution requires an outright closed COMPILED typed session")
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if slot.typed_binding is None or type(slot.typed_binding.value) is not ResistiveDCSubject:
        raise TypeError(f"slot {slot_name!r} must hold an exact ResistiveDCSubject")
    return compile_resistive_dc(source, slot.typed_binding.value, engine, shepherd_session_digest=canonical_digest(session), **kwargs)


def _payloads(analysis: ResistiveDCAnalysis) -> dict[str, object]:
    return {
        "resistive_dc_analysis": analysis,
        "resistive_dc_boundary_relation": analysis.boundary_relation,
        "resistive_dc_sparse_solution": analysis.sparse_solution,
    }


def _result(obligation: ValidityObligation, outcome: ObligationOutcome, detail: str) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _pre_result(obligation: ValidityObligation, approved: ApprovedPlan, subject: ResistiveDCSubject) -> ObligationResult:
    plan = approved.plan
    if obligation.evaluator_id == "smartchem.resistive_dc/exact-subject-model-v1":
        passed = plan.model == _ideal_resistor_model() and plan.request.physical_ir.models == (_ideal_resistor_model(),)
        try:
            subject.model.validate_diagram(subject.diagram)
        except (TypeError, ValueError):
            passed = False
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE, "exact subject model and runtime-owned ideal-resistor model are bound" if passed else "subject/model binding differs from the approved ideal-resistor vertical")
    if obligation.evaluator_id == "smartchem.resistive_dc/literal-casualty-boundary-v1":
        ir = plan.request.physical_ir
        passed = ir.claim_scope == _scope() and ir.evidence_status is EvidenceStatus.VALIDATED_WITHIN_REGIME and plan.execution_lane is ExecutionLane.CERTIFIED
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE, "literal scope is confined to ideal circuit mathematics" if passed else "claim scope, evidence, lane, or casualties were widened")
    if obligation.evaluator_id == "smartchem.resistive_dc/canonicalization-budget-v1":
        if subject.canonicalization_budget < 1:
            return _result(obligation, ObligationOutcome.REFUSE, "declared canonicalization budget is exhausted before analysis")
        try:
            canonicalize(subject.diagram, budget=subject.canonicalization_budget)
            canonicalize(subject.diagram, budget=subject.canonicalization_budget, edge_labels=_resistance_labels(subject.model))
        except Exception as error:
            return _result(obligation, ObligationOutcome.REFUSE, f"canonicalization refused: {type(error).__name__}: {error}")
        return _result(obligation, ObligationOutcome.PASS, "structural and resistance-decorated canonical forms fit the declared budget")
    return _result(obligation, ObligationOutcome.REFUSE, f"no evaluator registered for {obligation.evaluator_id}")


def _post_result(obligation: ValidityObligation, analysis: object, subject: ResistiveDCSubject, emitted: tuple[str, ...], expected: tuple[str, ...]) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.resistive_dc/analysis-recomputation-v1":
        try:
            reference = analyze_resistive_dc(subject)
            passed = type(analysis) is ResistiveDCAnalysis and canonical_digest(analysis) == canonical_digest(reference)
        except Exception:
            passed = False
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL, "checkpoint equals separate deterministic topology/relation/MNA recomputation" if passed else "engine analysis differs from separate deterministic recomputation")
    if obligation.evaluator_id == "smartchem.resistive_dc/residual-passivity-v1":
        if type(analysis) is not ResistiveDCAnalysis:
            return _result(obligation, ObligationOutcome.FAIL, "engine did not return an exact ResistiveDCAnalysis")
        d: CircuitDiagnostics = analysis.sparse_solution.diagnostics
        tolerance = float(subject.experiment.scaled_tolerance)
        residuals = (d.scaled_kcl_residual, d.scaled_constraint_residual, d.scaled_power_residual, d.scaled_relation_residual)
        passed = all(value <= tolerance for value in residuals) and all(branch.absorbed_power_watts >= 0.0 for branch in analysis.sparse_solution.branches)
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL, "all scaled residuals and resistor passivity gates pass" if passed else "a scaled residual or resistor passivity gate failed")
    if obligation.evaluator_id == "smartchem.resistive_dc/output-inventory-v1":
        passed = tuple(sorted(emitted)) == tuple(sorted(expected))
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL, f"expected={sorted(expected)}, emitted={sorted(emitted)}")
    return _result(obligation, ObligationOutcome.REFUSE, f"no evaluator registered for {obligation.evaluator_id}")


def _preflight_resistive_dc(plan: CandidatePlan) -> None:
    if plan.executor_id != _RESISTIVE_DC_EXECUTOR:
        raise ValueError("resistive-DC preflight received a different executor plan")
    expected = _ideal_resistor_model()
    if plan.model != expected or plan.request.physical_ir.models != (expected,):
        raise ValueError("resistive-DC executor requires its exact runtime-owned ideal-resistor model")
    if plan.transforms:
        raise ValueError("resistive-DC executor does not support transforms")


def _execute_resistive_dc(approved: ApprovedPlan, engine: object, *, actual_calculation: CalculationSpec, journal_path: str | os.PathLike[str] | None = None, _dispatch_token: object = None) -> ExecutionReport:
    _require_runtime_dispatch(_dispatch_token)
    plan = approved.plan
    _preflight_resistive_dc(plan)
    resolved = plan.request.resolved
    if type(resolved) is not ResolvedDomainProgram or type(resolved.subject) is not ResistiveDCSubject:
        raise TypeError("resistive-DC executor requires an exact ResolvedDomainProgram ResistiveDCSubject")
    subject = resolved.subject
    started = time.monotonic()
    journal = RunJournal(approved, backend=actual_calculation.engine_name, path=journal_path)
    try:
        for artifact_id, kind, payload in (("source-program", "source", plan.request.source), ("candidate-plan", "plan", plan), ("approval", "approval", approved.approval)):
            journal.add_artifact(Artifact(artifact_id, kind, payload.digest, True, False, payload=payload))
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.PRE:
                verdict = _pre_result(obligation, approved, subject)
                journal.add_obligation_result(verdict)
                if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                    return ExecutionReport(journal.refused(f"precondition {obligation.name} ended {verdict.outcome.value}: {verdict.detail}"), None, None)
        breach = _resource_wall(plan.limits, started=started, completed_calls=0, call_label="ideal-resistor engine calls")
        if breach is not None or (plan.limits.max_engine_calls is not None and plan.limits.max_engine_calls < 1):
            return ExecutionReport(journal.incomplete(breach or "approved engine-call cap reached before ideal-resistor analysis"), None, None)
        solver = getattr(engine, "solve", None)
        if not callable(solver):
            raise TypeError("resistive-DC engine must expose solve(ResistiveDCSubject)")
        try:
            analysis = solver(subject)
        except CircuitResidualError as error:
            return ExecutionReport(journal.invalid(f"resistive-DC residual gate failed: {error}"), None, None)
        except CircuitError as error:
            return ExecutionReport(journal.refused(f"resistive-DC circuit interpretation refused: {error}"), None, None)
        if type(analysis) is not ResistiveDCAnalysis:
            return ExecutionReport(journal.invalid("resistive-DC engine returned no exact ResistiveDCAnalysis"), None, None)
        journal.add_checkpoint(Artifact("checkpoint:resistive-DC-analysis", "checkpoint", analysis.digest, True, False, detail=f"edges={len(subject.diagram.edges)} nodes={len(subject.diagram.node_kinds)}", payload=analysis))
        if CalculationSpec.from_oracle(engine).digest != plan.calculation.digest:
            raise RuntimeError("CalculationSpec changed during the approved resistive-DC engine call")
        breach = _resource_wall(plan.limits, started=started, completed_calls=1, call_label="ideal-resistor engine calls")
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        payloads = _payloads(analysis)
        emitted: list[str] = []
        for observable_id in plan.request.output_contract.observable_ids:
            payload = payloads[observable_id]
            journal.add_artifact(Artifact(f"observable:{observable_id}", "observable", canonical_digest(payload), True, False, detail=f"complete {observable_id}", payload=payload))
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        journal.add_cache_state("no cache: one complete exact-relation plus sparse-MNA engine call")
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.POST:
                verdict = _post_result(obligation, analysis, subject, emitted_ids, plan.request.output_contract.observable_ids)
                journal.add_obligation_result(verdict)
                if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                    return ExecutionReport(journal.invalid(f"postcondition {obligation.name} ended {verdict.outcome.value}: {verdict.detail}"), None, None)
        certificate = Certificate(plan.request.source.digest, plan.request.digest, plan.digest, approved.approval.digest, actual_calculation.digest, plan.compiler_implementation_digest, journal.record.run_id, RunStatus.COMPLETE, plan.request.physical_ir.claim_scope, plan.request.physical_ir.evidence_status, journal.record.obligation_results, emitted_ids, RESISTIVE_DC_CASUALTIES, RESISTIVE_DC_OMISSIONS, ())
        journal.add_artifact(Artifact("certificate", "certificate", certificate.digest, True, False, payload=certificate))
        elapsed = time.monotonic() - started
        values = tuple(StructuredObservableValue(observable_id, payloads[observable_id], next(item.unit for item in plan.request.output_contract.observables if item.observable_id == observable_id), "ideal-resistor exact-relation sparse-MNA v1", next(item.support for item in plan.request.output_contract.observables if item.observable_id == observable_id), elapsed, "VALIDATED_WITHIN_REGIME for the declared ideal mathematical circuit only.", "See certificate casualties and omissions.") for observable_id in emitted_ids)
        result = SimulationResult(journal.record.run_id, values, certificate.digest)
        record = journal.complete()
        return ExecutionReport(record, result, certificate) if record.status is RunStatus.COMPLETE else ExecutionReport(record, None, None)
    except Exception as error:
        return ExecutionReport(journal.failed(f"{type(error).__name__}: {error}"), None, None)
