"""Compiler/runtime vertical for synthetic interval-cohort survival recovery.

This is a separate rung from the human-isotope underidentification diagnostic.
It selects one Weibull proportional-hazards family before fitting, accepts only
content-addressed synthetic independent cohorts, fits TRAIN only, and scores a
locked HOLDOUT split.  Same-generator recovery is implementation evidence, not
human calibration, toxicology, or validation of the isotope metaphor.
"""
from __future__ import annotations

import os
import time

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
from .human_survival_domain import (
    Applicability,
    DataAuthority,
    FitStatus,
    IntervalPrediction,
    Split,
    SurvivalCalibrationResult,
    SurvivalCalibrationSpec,
    SurvivalFitInput,
    SurvivalFitResult,
    SyntheticValidationStatus,
    assess_synthetic_survival,
    fit_synthetic_survival,
    fit_synthetic_survival_model,
)
from .ledger import BindingSchema, COMPILED, Session, Slot
from .program import (
    Adapter,
    ApprovedPlan,
    Artifact,
    AssemblyEvidence,
    AssemblySpec,
    Boundary,
    CalculationSpec,
    CalibrationSpec,
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
    _HUMAN_SURVIVAL_EXECUTOR,
    _compiler_implementation_digest,
    _require_runtime_dispatch,
    _resource_wall,
)

__all__ = [
    "HUMAN_SURVIVAL_CASUALTIES",
    "HUMAN_SURVIVAL_OMISSIONS",
    "SyntheticSurvivalRecoveryEngine",
    "compile_human_survival_recovery",
    "compile_session_human_survival_recovery",
    "human_survival_slot",
]


HUMAN_SURVIVAL_CASUALTIES = (
    "actual-human, animal, clinical, epidemiological, or toxicological evidence",
    "a prediction for any actual person or population",
    "LD50 or LC50 as a rate, universal threshold, or validation endpoint",
    "causal environmental, biological, repair, or molecular mechanism",
    "validation of the human-isotope metaphor or nuclear-decay semantics",
    "individual lifetime, cause-specific incidence, or competing-risk prediction",
    "authority for human or animal experimentation or a safety decision",
)

HUMAN_SURVIVAL_OMISSIONS = (
    "the records are deterministic synthetic independent cohorts, not observations",
    "the Weibull proportional-hazards family and static dose covariate are selected in advance",
    "the fixed scalar dose is not a time-varying exposure, toxicokinetic, or repair model",
    "conditional likelihood-curvature intervals are not calibrated confidence coverage "
    "and omit cohort bootstrap and profile likelihood",
    "the locked synthetic holdout is not external or biological validation",
    "same-generator recovery tests implementation only and has no transfer authority",
    "no LD50, LC50, individual risk, causal, clinical, regulatory, or safety output is emitted",
)


class SyntheticSurvivalRecoveryEngine:
    """One deterministic fixed-family synthetic recovery calculation."""

    name = "SmartChem synthetic Weibull interval-cohort recovery"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": (
                "fixed multistart L-BFGS-B conditional-binomial interval likelihood"
            ),
            "coordinates": ("log(lambda_days)", "log(shape_k)", "beta"),
            "uncertainty": "finite-difference observed information in fitted coordinates",
            "evaluation": "locked synthetic HOLDOUT binomial log and Brier scores",
            "truth_use": "post-fit recovery assessment only",
            "arithmetic": "IEEE-754 binary64",
            "version": 1,
        }

    def solve(self, fit_input: SurvivalFitInput) -> SurvivalFitResult:
        self.calls += 1
        return fit_synthetic_survival_model(fit_input)


def human_survival_slot(name: str, written: str) -> Slot:
    return Slot(name=name, written=written, schema=BindingSchema((SurvivalCalibrationSpec,)))


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                "human_survival_synthetic_fit",
                "fixed-family synthetic interval-cohort fit",
                "typed synthetic-only record",
                "complete content-addressed TRAIN and locked HOLDOUT design",
                "one complete fit result or explicit unstable result",
                "retain binary64 estimates, scores, and diagnostics",
                "status, parameters, uncertainty, optimizer, scores, and recovery",
                diagnostics=(
                    "TRAIN-only likelihood",
                    "truth used only after fitting",
                    "COMPLETE is lifecycle status, not biological validation",
                ),
                retention=("complete SurvivalCalibrationSpec", "complete result"),
            ),
            ObservableRequest(
                "human_survival_data_governance",
                "complete synthetic records, split, and authority inventory",
                "typed content-addressed record",
                "every supplied synthetic cohort interval",
                "no record, count, or split suppression",
                "exact record and SHA-256 identities",
                "dataset, generator version, independent split, and no-transfer clause",
                retention=("all interval records", "all governance fields"),
            ),
            ObservableRequest(
                "human_survival_parameter_uncertainty",
                "complete conditional curvature and optimizer inventory",
                "days and transformed-coordinate covariance",
                "the fixed three-parameter Weibull proportional-hazards family",
                "all fitted coordinates or explicit absence on instability",
                "binary64 conditional likelihood-curvature result",
                "estimates, conditional covariance/intervals, rank, conditioning, and start agreement",
                diagnostics=(
                    "not calibrated confidence coverage",
                    "no bootstrap or profile-likelihood promotion",
                ),
                retention=("all optimizer and uncertainty diagnostics",),
            ),
            ObservableRequest(
                "human_survival_training_predictions",
                "complete TRAIN interval prediction inventory",
                "conditional interval probability and binomial log/Brier scores",
                "every immutable TRAIN cohort",
                "one exact retained prediction per TRAIN record",
                "binary64 probabilities and scores",
                "record-bound probability, log score, and Brier score",
                retention=("all TRAIN predictions in record order",),
            ),
            ObservableRequest(
                "human_survival_heldout_scoring",
                "locked synthetic HOLDOUT scoring and post-fit recovery assessment",
                "conditional interval probability and binomial log/Brier scores",
                "every immutable HOLDOUT cohort and declared generator truth",
                "one exact retained prediction per HOLDOUT record",
                "binary64 probabilities, scores, and recovery errors",
                "heldout predictions, aggregate scores, status, and recovery assessment",
                diagnostics=("not external, human, biological, or causal validation",),
                retention=("all HOLDOUT predictions and post-fit truth comparison",),
            ),
        ),
        diagnostics=(
            "typed synthetic-only authority and no-transfer boundary",
            "fixed model, likelihood, optimizer, split, and uncertainty protocol",
            "exact output inventory",
            "refusals, unstable fits, resource walls, and failures",
        ),
        retention=(
            "source program and typed shepherd interpretation",
            "complete plan and approval",
            "complete fit checkpoint",
            "every requested observable payload",
            "run record and certificate",
        ),
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation(
            "human-survival-subject-is-exact-synthetic-interval-data",
            ObligationStage.PRE,
            "smartchem.human_survival/typed-synthetic-subject-v1",
            "the exact subject has content-addressed independent synthetic cohorts",
        ),
        ValidityObligation(
            "human-survival-scope-remains-nontransferable-proxy",
            ObligationStage.PRE,
            "smartchem.human_survival/synthetic-casualty-boundary-v1",
            "claim scope remains a structural-toy experimental proxy with every casualty",
        ),
        ValidityObligation(
            "human-survival-fit-is-complete-and-recomputed",
            ObligationStage.POST,
            "smartchem.human_survival/complete-fit-v1",
            "the fit exactly equals an independent deterministic recomputation",
        ),
        ValidityObligation(
            "human-survival-output-inventory-is-exact",
            ObligationStage.POST,
            "smartchem.human_survival/output-inventory-v1",
            "emitted observable identities exactly equal the frozen contract",
        ),
)


def _human_survival_model() -> ModelSpec:
    return ModelSpec(
        "synthetic Weibull proportional-hazards interval-cohort proxy",
        (
            "H(t|d) = (t/lambda)^k * exp(beta*d/d_ref)",
            "q[t0,t1|d] = 1 - exp(-(H(t1|d)-H(t0|d)))",
            "events ~ Binomial(at_risk, q) for independent synthetic cohorts",
        ),
        (
            "one fixed preselected family and static synthetic dose covariate",
            "independent cohorts; no repeated cumulative rows treated as independent",
            "TRAIN-only fitting; locked HOLDOUT scoring; post-fit truth comparison",
        ),
        (
            "authority is SYNTHETIC_ONLY",
            "record and split digests are exact",
            "optimizer agreement and conditional likelihood-curvature gates pass or no fit is emitted",
        ),
        (
            "all records and scores retained",
            "scientific status never exceeds synthetic generator recovery",
        ),
        (),
        "1",
    )


def compile_human_survival_recovery(
    source: SourceProgram | str,
    spec: SurvivalCalibrationSpec,
    engine: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """Compile the fixed synthetic recovery problem without weakening D2a."""
    if isinstance(source, str):
        source = SourceProgram(source)
    if type(source) is not SourceProgram:
        raise TypeError("source must be an exact SourceProgram or str")
    if type(spec) is not SurvivalCalibrationSpec:
        raise TypeError("spec must be an exact SurvivalCalibrationSpec")
    source_theory = SourceTheory(
        "cross-domain reliability/survival vocabulary",
        (
            "survival-family mathematics does not transport nuclear material semantics",
            "synthetic generator recovery does not transport to people or biology",
        ),
        (),
    )
    target = TargetIntent(
        source.text,
        "synthetic independent-cohort all-cause interval events",
        (
            "recover a preselected Weibull proportional-hazards generator from TRAIN "
            "and score the locked synthetic HOLDOUT without biological transfer"
        ),
    )
    resolved = ResolvedDomainProgram(
        source.digest,
        spec,
        target,
        source_theory,
        shepherd_session_digest,
    )
    model = _human_survival_model()
    transport = TransportMap(
        source_theory.digest,
        target.digest,
        preserved=(
            "population-level survival-family mathematics",
            "environment sensitivity represented only by a declared static synthetic covariate",
        ),
        modified=(
            "decay vocabulary becomes a conditional cohort event-probability proxy",
        ),
        discarded=HUMAN_SURVIVAL_CASUALTIES,
        unknown=(
            "all biological assembly, toxicokinetic, causal, and external applicability",
        ),
    )
    assembly = AssemblySpec(
        spec.assembly.assembly_id,
        "one independent synthetic interval cohort",
        (
            "one record per cohort",
            "fixed TRAIN/HOLDOUT split",
            spec.assembly.aggregation_rule,
        ),
    )
    scope = ClaimScope(
        ClaimKind.EXPERIMENTAL_PROXY,
        "synthetic fixed-family interval-cohort generator recovery only",
        HUMAN_SURVIVAL_CASUALTIES,
    )
    component = Component(
        "synthetic-survival-dataset",
        "content-addressed independent interval cohorts",
        Identity(
            spec.dataset.declared_records_digest,
            "synthetic-only-survival-dataset",
            (
                ("record-count", str(spec.dataset.declared_record_count)),
                ("dose-unit", spec.dose_unit),
                ("time-unit", spec.time_unit),
            ),
        ),
    )
    calibration = CalibrationSpec(
        population="synthetic independent cohorts only",
        protocol=(
            "fixed conditional-binomial interval likelihood; TRAIN-only multistart fit"
        ),
        endpoints=("conditional all-cause interval event count",),
        identifiability=(
            "three fitted coordinates with full-rank positive-definite observed information"
        ),
        validation_split="immutable disjoint TRAIN/HOLDOUT record and cohort identities",
        uncertainty_treatment=(
            "conditional likelihood-curvature covariance in log(lambda), log(k), beta "
            "coordinates; no calibrated confidence coverage; bootstrap and profile "
            "likelihood omitted"
        ),
    )
    physical_ir = PhysicalIR(
        resolved.digest,
        (component,),
        (),
        (),
        (
            Boundary(
                "synthetic-only-no-transfer",
                (component.component_id,),
                spec.governance.no_transfer_clause,
            ),
        ),
        (model,),
        (
            Adapter(
                "cross-domain survival-proxy adapter",
                "human-isotope/environmental-decay metaphor",
                "synthetic cohort interval likelihood",
                _default_output_contract().observable_ids,
                (
                    "synthetic-only authority",
                    "fixed-family conditional probability semantics",
                ),
                "all nuclear, human, biological, causal, and safety meaning is discarded",
            ),
        ),
        (
            Invariant(
                "holdout cannot select the fit",
                "only TRAIN records enter the likelihood and optimizer",
                "this approved SurvivalCalibrationSpec",
                "smartchem.human_survival/complete-fit-v1",
            ),
            Invariant(
                "synthetic status cannot promote",
                "completion and recovery do not validate biology or people",
                "this approved request and certificate",
                "smartchem.human_survival/synthetic-casualty-boundary-v1",
            ),
        ),
        (transport,),
        (
            TransportEvidence(
                transport.digest,
                (
                    "fixed synthetic Weibull family",
                    "independent interval cohorts",
                    "no transfer beyond declared generator",
                ),
                (
                    "conditional-binomial likelihood",
                    "locked heldout scoring",
                    "post-fit same-generator recovery",
                ),
                HUMAN_SURVIVAL_OMISSIONS,
            ),
        ),
        (assembly,),
        (
            AssemblyEvidence(
                assembly.digest,
                ("typed synthetic cohort construction only",),
                ("biological assembly and external applicability",),
            ),
        ),
        scope,
        EvidenceStatus.STRUCTURAL_TOY,
        (calibration,),
    )
    contract = output_contract or _default_output_contract()
    request = SimulationRequest(
        source,
        resolved,
        physical_ir,
        contract,
        equivalence_contract
        or EquivalenceContract(
            (
                "exact categorical/digest equality and binary64 equality of every "
                "retained record, fit coordinate, uncertainty, prediction, and score"
            ),
            (),
            "source record order and fixed optimizer-start order",
            "no RNG",
            (
                "one indivisible fit; interruption or failed independent recomputation "
                "quarantines the complete checkpoint"
            ),
        ),
        _obligations(),
    )
    blockers = ()
    if contract != _default_output_contract():
        blockers = (
            "this narrow synthetic-survival executor can honor only its exact default "
            "output contract; changing support, resolution, precision, coverage, "
            "diagnostics, retention, or observable membership requires another executor",
        )
    return CandidatePlan(
        request=request,
        model=model,
        solver=SolverSpec(
            getattr(engine, "name", type(engine).__qualname__),
            "fixed multistart conditional-binomial interval likelihood",
            "1",
            (
                ("gradient tolerance", spec.protocol.gradient_tolerance),
                (
                    "objective agreement tolerance",
                    spec.protocol.objective_agreement_tolerance,
                ),
                (
                    "parameter agreement tolerance",
                    spec.protocol.parameter_agreement_tolerance,
                ),
            ),
            "all fixed starts must agree and observed information must pass",
            "immutable records, fixed starts/bounds, deterministic optimizer, no RNG",
        ),
        calculation=CalculationSpec.from_oracle(engine),
        compiler_implementation_digest=_compiler_implementation_digest(),
        executor_id=_HUMAN_SURVIVAL_EXECUTOR,
        transforms=(),
        predicted_resources=(
            ("engine calls", "1"),
            ("fixed optimizer starts", str(len(spec.protocol.transformed_starts))),
            ("retained records", str(spec.dataset.declared_record_count)),
        ),
        blockers=blockers,
        execution_lane=ExecutionLane.EXPERIMENTAL,
        limits=limits or RuntimeLimits(max_engine_calls=1),
    )


def compile_session_human_survival_recovery(
    source: SourceProgram | str,
    session: Session,
    slot_name: str,
    engine: object,
    **kwargs: object,
) -> CandidatePlan:
    if type(session) is not Session:
        raise TypeError("session must be an exact shepherd Session")
    if session.outcome != COMPILED or session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError("synthetic survival execution requires an outright closed COMPILED session")
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if slot.typed_binding is None or type(slot.typed_binding.value) is not SurvivalCalibrationSpec:
        raise TypeError(f"slot {slot_name!r} must hold an exact SurvivalCalibrationSpec")
    return compile_human_survival_recovery(
        source,
        slot.typed_binding.value,
        engine,
        shepherd_session_digest=canonical_digest(session),
        **kwargs,
    )


def _payloads(
    result: SurvivalCalibrationResult,
    spec: SurvivalCalibrationSpec,
) -> dict[str, object]:
    train = tuple(item for item in result.predictions if item.split is Split.TRAIN)
    holdout = tuple(item for item in result.predictions if item.split is Split.HOLDOUT)
    return {
        "human_survival_synthetic_fit": result,
        "human_survival_data_governance": (spec.dataset, spec.governance),
        "human_survival_parameter_uncertainty": (
            result.fitted_parameters,
            result.transformed_covariance,
            result.intervals,
            result.optimizer,
        ),
        "human_survival_training_predictions": train,
        "human_survival_heldout_scoring": (
            holdout,
            result.heldout_mean_negative_log_score,
            result.heldout_brier_score,
            result.recovery,
            result.status,
        ),
    }


def _result(
    obligation: ValidityObligation,
    outcome: ObligationOutcome,
    detail: str,
) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _pre_result(
    obligation: ValidityObligation,
    approved: ApprovedPlan,
    spec: SurvivalCalibrationSpec,
) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.human_survival/typed-synthetic-subject-v1":
        passed = (
            type(spec) is SurvivalCalibrationSpec
            and spec.governance.authority is DataAuthority.SYNTHETIC_ONLY
            and spec.governance.applicability
            is Applicability.DECLARED_GENERATOR_RECOVERY_ONLY
            and spec.dataset.declared_records_digest
            == canonical_digest(spec.dataset.records)
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "exact content-addressed synthetic interval cohorts and split are present"
                if passed
                else "subject is outside the exact synthetic-only interval-cohort scope"
            ),
        )
    if obligation.evaluator_id == "smartchem.human_survival/synthetic-casualty-boundary-v1":
        ir = approved.plan.request.physical_ir
        passed = (
            ir.claim_scope
            == ClaimScope(
                ClaimKind.EXPERIMENTAL_PROXY,
                "synthetic fixed-family interval-cohort generator recovery only",
                HUMAN_SURVIVAL_CASUALTIES,
            )
            and ir.evidence_status is EvidenceStatus.STRUCTURAL_TOY
            and approved.plan.execution_lane is ExecutionLane.EXPERIMENTAL
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "scope remains a structural-toy experimental proxy with exact casualties"
                if passed
                else "claim kind, evidence, lane, or casualty boundary was widened"
            ),
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _post_result(
    obligation: ValidityObligation,
    diagnostic: object,
    spec: SurvivalCalibrationSpec,
    emitted: tuple[str, ...],
    expected: tuple[str, ...],
) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.human_survival/complete-fit-v1":
        passed = (
            type(diagnostic) is SurvivalCalibrationResult
            and canonical_digest(diagnostic)
            == canonical_digest(fit_synthetic_survival(spec))
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            (
                "independent recomputation retained the complete synthetic fit and scores"
                if passed
                else "fit, uncertainty, predictions, scores, or status were altered"
            ),
        )
    if obligation.evaluator_id == "smartchem.human_survival/output-inventory-v1":
        passed = tuple(sorted(emitted)) == tuple(sorted(expected))
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            f"expected={sorted(expected)}, emitted={sorted(emitted)}",
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _preflight_human_survival(plan: CandidatePlan) -> None:
    expected = _human_survival_model()
    if plan.executor_id != _HUMAN_SURVIVAL_EXECUTOR:
        raise ValueError("human-survival preflight received a different executor plan")
    if plan.model != expected or plan.request.physical_ir.models != (expected,):
        raise ValueError("human-survival executor requires its exact runtime-owned model")
    if plan.transforms:
        raise ValueError("human-survival executor does not support transforms")


def _execute_human_survival(
    approved: ApprovedPlan,
    engine: object,
    *,
    actual_calculation: CalculationSpec,
    journal_path: str | os.PathLike[str] | None = None,
    _dispatch_token: object = None,
) -> ExecutionReport:
    _require_runtime_dispatch(_dispatch_token)
    plan = approved.plan
    _preflight_human_survival(plan)
    if plan.executor_id != _HUMAN_SURVIVAL_EXECUTOR:
        raise ValueError("human-survival runner received a different executor plan")
    resolved = plan.request.resolved
    if (
        type(resolved) is not ResolvedDomainProgram
        or type(resolved.subject) is not SurvivalCalibrationSpec
    ):
        raise TypeError(
            "human-survival executor requires an exact ResolvedDomainProgram "
            "SurvivalCalibrationSpec"
        )
    spec = resolved.subject
    started = time.monotonic()
    journal = RunJournal(
        approved,
        backend=actual_calculation.engine_name,
        path=journal_path,
    )
    try:
        for artifact_id, kind, payload in (
            ("source-program", "source", plan.request.source),
            ("candidate-plan", "plan", plan),
            ("approval", "approval", approved.approval),
        ):
            journal.add_artifact(
                Artifact(
                    artifact_id,
                    kind,
                    payload.digest,
                    True,
                    False,
                    payload=payload,
                )
            )
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.PRE:
                verdict = _pre_result(obligation, approved, spec)
                journal.add_obligation_result(verdict)
                if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                    return ExecutionReport(
                        journal.refused(
                            f"precondition {obligation.name} ended "
                            f"{verdict.outcome.value}: {verdict.detail}"
                        ),
                        None,
                        None,
                    )
        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=0,
            call_label="human-survival engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        if plan.limits.max_engine_calls is not None and plan.limits.max_engine_calls < 1:
            return ExecutionReport(
                journal.incomplete("approved engine-call cap reached before fitting"),
                None,
                None,
            )
        solver = getattr(engine, "solve", None)
        if not callable(solver):
            raise TypeError("human-survival engine must expose solve(SurvivalFitInput)")
        fit_input = SurvivalFitInput(spec.dataset.train_records, spec.protocol)
        fit_result = solver(fit_input)
        if type(fit_result) is not SurvivalFitResult:
            return ExecutionReport(
                journal.invalid(
                    "human-survival engine returned no exact SurvivalFitResult"
                ),
                None,
                None,
            )
        diagnostic = assess_synthetic_survival(spec, fit_result)
        journal.add_checkpoint(
            Artifact(
                "checkpoint:human-survival-synthetic-fit",
                "checkpoint",
                canonical_digest(diagnostic),
                True,
                False,
                detail=(
                    f"{diagnostic.status.value}; "
                    f"{len(diagnostic.predictions)} retained predictions"
                ),
                payload=diagnostic,
            )
        )
        if CalculationSpec.from_oracle(engine).digest != plan.calculation.digest:
            raise RuntimeError(
                "CalculationSpec changed during the approved human-survival call"
            )
        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=1,
            call_label="human-survival engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        payloads = _payloads(diagnostic, spec)
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
                    detail=(
                        f"complete {observable_id}; scientific status="
                        f"{diagnostic.status.value}"
                    ),
                    payload=payload,
                )
            )
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        journal.add_cache_state(
            "no cache: one deterministic complete synthetic recovery calculation"
        )
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.POST:
                verdict = _post_result(
                    obligation,
                    diagnostic,
                    spec,
                    emitted_ids,
                    plan.request.output_contract.observable_ids,
                )
                journal.add_obligation_result(verdict)
                if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                    return ExecutionReport(
                        journal.invalid(
                            f"postcondition {obligation.name} ended "
                            f"{verdict.outcome.value}: {verdict.detail}"
                        ),
                        None,
                        None,
                    )
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
            HUMAN_SURVIVAL_CASUALTIES,
            HUMAN_SURVIVAL_OMISSIONS,
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
                "synthetic Weibull interval-cohort recovery v1",
                next(
                    item.support
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                elapsed,
                (
                    "Likelihood-curvature intervals are conditional on this fixed "
                    "synthetic binomial family, not calibrated confidence coverage; "
                    "no bootstrap, biology, or transfer was inferred."
                ),
                (
                    "COMPLETE means lifecycle completion only; scientific status is "
                    f"{diagnostic.status.value} and validation is "
                    f"{diagnostic.validation.value}."
                ),
            )
            for observable_id in emitted_ids
        )
        result = SimulationResult(journal.record.run_id, values, certificate.digest)
        record = journal.complete()
        if record.status is not RunStatus.COMPLETE:
            return ExecutionReport(record, None, None)
        return ExecutionReport(record, result, certificate)
    except Exception as error:
        return ExecutionReport(
            journal.failed(f"{type(error).__name__}: {error}"),
            None,
            None,
        )
