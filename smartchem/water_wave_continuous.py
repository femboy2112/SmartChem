"""Lifecycle wrapper for the manufactured continuous steady-water control.

The domain module owns the discretisation and its numerical verdict.  This module owns
the compiler/runtime boundary: exact model identity, analogue scope, complete retained
outputs, independent finite-v2 comparison, and pre/post validity obligations.
"""
from __future__ import annotations

import os
import math
import time
from dataclasses import dataclass

from .contracts import (
    ClaimKind, EvidenceStatus, ExecutionLane, ObligationOutcome, ObligationResult,
    ObligationStage, RunStatus, ValidityObligation, canonical_digest,
)
from .ledger import BindingSchema, COMPILED, Session, Slot
from .program import (
    Adapter, ApprovedPlan, Artifact, AssemblyEvidence, AssemblySpec, Boundary,
    CalculationSpec, CandidatePlan, Certificate, ClaimScope, Component,
    EquivalenceContract, ExecutionReport, Identity, Invariant, ModelSpec,
    ObservableRequest, OutputContract, PhysicalIR, Quantity, ResolvedDomainProgram,
    RunJournal, RuntimeLimits, SimulationRequest, SimulationResult, SolverSpec,
    SourceProgram, SourceTheory, StructuredObservableValue, TargetIntent,
    TransportEvidence, TransportMap, _compiler_implementation_digest,
    _require_runtime_dispatch, _resource_wall,
)
from .water_wave_continuous_domain import (
    CONTINUOUS_UNCERTAINTY_SEMANTICS,
    ContinuousBackgroundSpec, ContinuousDiagnostic,
    ContinuousStatus, solve_continuous_background,
)
from .water_wave_continuous_verifier import continuous_diagnostic_error
from .water_wave_validation_domain import (
    BackgroundSample, BackgroundTolerances, DeclaredWavelengthSupport,
    FluidProperties, ValidationDiagnostic, WaterWaveValidationSpec,
    diagnose_water_wave_background,
)
from .water_wave_domain import FlowDirection, HorizonOrientation, WaveBranch

__all__ = [
    "CONTINUOUS_WATER_CASUALTIES", "CONTINUOUS_WATER_OMISSIONS",
    "ContinuousFiniteV2Comparison", "ContinuousWaterWaveEngine",
    "ContinuousWaterSubject",
    "compile_session_water_wave_continuous", "compile_water_wave_continuous",
    "continuous_water_slot", "plan_preflight",
]


_EXECUTOR_ID = "smartchem.water_wave_continuous/manufactured-steady-v1"

CONTINUOUS_WATER_CASUALTIES = (
    "a measured water-channel validation or measured background profile",
    "a literal black hole, Einstein dynamics, or spacetime curvature",
    "quantum Hawking radiation, a Hawking temperature, or a thermal spectrum",
    "dispersive gravity-capillary scattering, mode conversion, or black-hole-laser dynamics",
    "two-dimensional, turbulent, breaking, hydraulic-jump, or free-boundary dynamics",
    "a general continuous solution beyond the declared manufactured family and meshes",
)

CONTINUOUS_WATER_OMISSIONS = (
    "no measurement provenance, calibration, or experimental validation is supplied",
    "no dispersive, capillary, nonlinear, turbulent, or two-dimensional uncertainty is quantified",
    CONTINUOUS_UNCERTAINTY_SEMANTICS,
    "N/2N/4N agreement is finite manufactured numerical evidence, not a continuum theorem",
    "finite-v2 remains an independent lossless finite-section diagnostic, not a validation oracle",
)


@dataclass(frozen=True)
class ContinuousFiniteV2Comparison:
    """Retained, independently recomputed finite-v2 comparison payload."""

    continuous_status: str
    finite_v2_status: str
    comparison: str
    explanation: str
    finite_v2_diagnostic: ValidationDiagnostic
    observed_head_range_m: float
    declared_friction_head_drop_m: float
    max_reconstruction_head_offset_m: float

    def __post_init__(self) -> None:
        for name in (
            "continuous_status",
            "finite_v2_status",
            "comparison",
            "explanation",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.finite_v2_diagnostic) is not ValidationDiagnostic:
            raise TypeError(
                "finite_v2_diagnostic must be an exact ValidationDiagnostic"
            )
        for name in (
            "observed_head_range_m",
            "declared_friction_head_drop_m",
            "max_reconstruction_head_offset_m",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0.0
            ):
                raise ValueError(f"{name} must be a nonnegative finite real")


@dataclass(frozen=True)
class ContinuousWaterSubject:
    """One continuous background plus an exact, independently evaluated v2 subject."""

    background: ContinuousBackgroundSpec
    finite_v2: WaterWaveValidationSpec

    def __post_init__(self) -> None:
        if type(self.background) is not ContinuousBackgroundSpec:
            raise TypeError("background must be an exact ContinuousBackgroundSpec")
        if type(self.finite_v2) is not WaterWaveValidationSpec:
            raise TypeError("finite_v2 must be an exact WaterWaveValidationSpec")
        if (
            self.finite_v2.fluid.gravitational_acceleration_m_s2
            != self.background.gravitational_acceleration_m_s2
        ):
            raise ValueError("finite-v2 gravity must equal the continuous background gravity")
        finest = solve_continuous_background(self.background).meshes[-1]
        reference_by_x = {sample.x_m: sample for sample in finest.samples}
        for sample in self.finite_v2.samples:
            reference = reference_by_x.get(sample.x_m)
            if reference is None:
                raise ValueError(
                    "every finite-v2 sample must name an explicitly retained finest-mesh point"
                )
            if (
                sample.width_m != self.background.width_m
                or sample.depth_m != reference.depth_m
                or sample.velocity_m_s != reference.velocity_m_s
                or sample.bed_elevation_m != reference.bed_elevation_m
            ):
                raise ValueError(
                    "finite-v2 samples must exactly retain the corresponding continuous "
                    "mesh width, depth, velocity, and bed values"
                )

    @classmethod
    def manufactured_comparison(
        cls,
        background: ContinuousBackgroundSpec,
        *,
        retained_sample_count: int = 9,
    ) -> "ContinuousWaterSubject":
        """Bind a disclosed finite-v2 view to retained finest-mesh points.

        V2 deliberately applies its lossless finite-section head gate to the
        frictional continuous reconstruction.  A head disagreement is therefore a
        useful scope control, not a failed attempt to force both models to agree.
        """
        if type(background) is not ContinuousBackgroundSpec:
            raise TypeError("background must be an exact ContinuousBackgroundSpec")
        if type(retained_sample_count) is not int or retained_sample_count < 3:
            raise ValueError("retained_sample_count must be an integer of at least three")
        finest = solve_continuous_background(background).meshes[-1]
        count = min(retained_sample_count, len(finest.samples))
        indices = tuple(
            round(index * (len(finest.samples) - 1) / (count - 1))
            for index in range(count)
        )
        samples = tuple(
            BackgroundSample(
                item.x_m,
                background.width_m,
                item.depth_m,
                item.velocity_m_s,
                item.bed_elevation_m,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            )
            for item in (finest.samples[index] for index in indices)
        )
        comparison = WaterWaveValidationSpec(
            samples=samples,
            fluid=FluidProperties(
                1000.0,
                0.072,
                background.gravitational_acceleration_m_s2,
                "manufactured-water comparison constants",
            ),
            wavelength_support=DeclaredWavelengthSupport(
                1000.0,
                2000.0,
                0.1,
                1.0,
                "declared finite-v2 comparison support",
            ),
            tolerances=BackgroundTolerances(
                1e-10,
                1e-10,
                1.0,
                "manufactured continuous-to-finite-v2 comparison gate",
            ),
            branch=WaveBranch.COUNTER_CURRENT,
            requested_orientation=(
                HorizonOrientation.WHITE
                if background.family.value == "REGULAR_TRANSCRITICAL"
                else HorizonOrientation.BLACK
            ),
            flow_direction=FlowDirection.POSITIVE_X,
        )
        return cls(background, comparison)


class ContinuousWaterWaveEngine:
    """Deterministic domain-owned manufactured continuous-background engine."""

    name = "SmartChem manufactured continuous steady-water diagnostic"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": "manufactured steady shallow-water residual/regularity/convergence diagnostic",
            "arithmetic": "IEEE-754 binary64",
            "meshes": "N, 2N, 4N retained",
            "comparison": "independent finite-section-v2 exact attached subject",
            "version": 1,
        }

    def solve(self, subject: ContinuousWaterSubject) -> ContinuousDiagnostic:
        self.calls += 1
        if type(subject) is not ContinuousWaterSubject:
            raise TypeError("subject must be an exact ContinuousWaterSubject")
        return solve_continuous_background(subject.background)


def continuous_water_slot(name: str, written: str) -> Slot:
    return Slot(name=name, written=written, schema=BindingSchema((ContinuousWaterSubject,)))


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                "water_wave_continuous_diagnostic",
                "manufactured steady continuous shallow-water diagnostic",
                "structured SI record",
                "the exact approved manufactured family on retained N, 2N, and 4N meshes",
                "every retained mesh point and every named residual/regularity verdict",
                "retain binary64 solver values plus binary64 roundings of a 60-digit Decimal manufactured reference evaluation; no physical uncertainty is invented",
                "specification, status, all mesh records, residual maxima, both critical residuals, and observed orders",
                diagnostics=(
                    "critical numerator and first-derivative compatibility",
                    "continuity and momentum residuals",
                    "N/2N/4N convergence",
                    CONTINUOUS_UNCERTAINTY_SEMANTICS,
                ),
                retention=("complete ContinuousDiagnostic",),
            ),
            ObservableRequest(
                "water_wave_continuous_meshes",
                "all manufactured continuous mesh fields",
                "structured SI arrays",
                "all N, 2N, and 4N mesh points", "no downsampling", "retain binary64 arrays",
                "x, depth, velocity, discharge, head, Froude, source/friction slopes, and residuals",
                diagnostics=(
                    "mesh cell counts",
                    "observed convergence order",
                    "per-cell root iterations, energy residual, and critical projection",
                    "binary64 rounding of a 60-digit Decimal manufactured reference depth and pointwise depth error",
                ),
                retention=("every ContinuousMeshResult",),
            ),
            ObservableRequest(
                "water_wave_finite_v2_comparison",
                "independent finite-v2 comparison statement",
                "structured explanatory record",
                "the exact attached finite-v2 subject",
                "one retained finite-v2 diagnostic; no interpolation or inferred agreement",
                "retain all status/explanation fields", "continuous and finite-v2 status plus model-discrepancy explanation",
                diagnostics=("lossless-versus-friction distinction",),
                retention=("ContinuousFiniteV2Comparison",),
            ),
        ),
        diagnostics=("typed analogue scope", "exact output inventory", "resource walls and refusal/invalid transitions"),
        retention=(
            "source, plan, approval, complete diagnostic, comparison, run record, certificate",
        ),
    )


def _runtime_model() -> ModelSpec:
    """The one runtime-owned continuous model; plans may not substitute prose or equations."""
    return ModelSpec(
        "manufactured steady one-dimensional shallow-water regularity model",
        (
            "q(x) = b(x) h(x) U(x)",
            "H(x) = z_b(x) + h(x) + U(x)^2/(2 g)",
            "steady momentum residual retains source slope and declared friction slope",
            "critical compatibility retains numerator and first-derivative residuals at the declared transcritical control",
            "N, 2N, and 4N manufactured meshes retain observed convergence order",
        ),
        (
            "one-dimensional hydrostatic depth-averaged shallow-water regime",
            "declared manufactured family, boundary conditions, source law, friction law, and uncertainty",
            "steady prescribed geometry; no resolved free-surface evolution or backreaction",
            "finite convergence evidence is scoped to the declared mesh family",
        ),
        (
            "the subject is an exact ContinuousBackgroundSpec",
            "all domain preconditions and manufactured boundary data are accepted by the domain constructor",
            "critical numerator/derivative compatibility and N/2N/4N convergence are checked after one complete engine call",
        ),
        (
            "every retained mesh has complete field/residual arrays",
            "a separately implemented direct verifier checks the diagnostic without calling the production solver",
            "a finite-v2 comparison explicitly distinguishes lossless finite-section gates from frictional continuous momentum",
        ),
        (
            "steady discharge under the declared one-dimensional manufactured model",
            CONTINUOUS_UNCERTAINTY_SEMANTICS,
        ),
        "1",
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation("continuous-water-typed-subject", ObligationStage.PRE,
                           "smartchem.water_wave_continuous/typed-subject-v1",
                           "exact manufactured continuous subject is present"),
        ValidityObligation("continuous-water-analogue-boundary", ObligationStage.PRE,
                           "smartchem.water_wave_continuous/analogue-boundary-v1",
                           "claim remains an ANALOGUE/STRUCTURAL_TOY with exact casualties"),
        ValidityObligation("continuous-water-complete-diagnostic", ObligationStage.POST,
                           "smartchem.water_wave_continuous/complete-diagnostic-v1",
                           "independent recomputation retains every N/2N/4N mesh and field"),
        ValidityObligation("continuous-water-critical-compatibility", ObligationStage.POST,
                           "smartchem.water_wave_continuous/critical-compatibility-v1",
                           "the domain status and retained critical residual admit the declared manufactured control"),
        ValidityObligation("continuous-water-convergence", ObligationStage.POST,
                           "smartchem.water_wave_continuous/convergence-v1",
                           "all N/2N/4N mesh records and convergence verdict are retained"),
        ValidityObligation("continuous-water-output-inventory", ObligationStage.POST,
                           "smartchem.water_wave_continuous/output-inventory-v1",
                           "emitted observable IDs exactly equal the frozen contract"),
    )


def compile_water_wave_continuous(
    source: SourceProgram | str, subject: ContinuousWaterSubject, engine: object, *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    if isinstance(source, str):
        source = SourceProgram(source)
    if type(source) is not SourceProgram:
        raise TypeError("source must be an exact SourceProgram or str")
    if type(subject) is not ContinuousWaterSubject:
        raise TypeError("subject must be an exact ContinuousWaterSubject")
    source_theory = SourceTheory(
        "analogue-gravity shallow-water vocabulary",
        ("a water-wave analogy is not literal gravity", "manufactured convergence is not measured validation"),
        ("https://arxiv.org/abs/gr-qc/0205099", "https://arxiv.org/abs/1806.05539"),
    )
    target = TargetIntent(source.text, "manufactured continuous one-dimensional steady background",
                          "retain steady residual, critical-regularity, and N/2N/4N convergence diagnostics")
    resolved = ResolvedDomainProgram(source.digest, subject, target, source_theory, shepherd_session_digest)
    model = _runtime_model()
    transport = TransportMap(source_theory.digest, target.digest,
        preserved=("one-dimensional shallow-water kinematic/steady-flow vocabulary",),
        modified=("analogy is a manufactured steady continuous residual control",),
        discarded=CONTINUOUS_WATER_CASUALTIES,
        unknown=("physical-channel applicability and measurement provenance",),
    )
    assembly = AssemblySpec("manufactured continuous water background", "retained finite mesh point",
                            ("N, 2N, and 4N arrays retained", "no field downsampling", "no measurement is implied"))
    scope = ClaimScope(ClaimKind.ANALOGUE, "structural manufactured continuous water-wave analogue", CONTINUOUS_WATER_CASUALTIES)
    component = Component("manufactured-continuous-water-background", "one-dimensional steady manufactured background",
                          Identity(canonical_digest(subject), "continuous-water-background"),
                          parameters=(Quantity(1.0, "dimensionless", "1", source="typed ContinuousBackgroundSpec identity"),))
    physical_ir = PhysicalIR(
        resolved.digest, (component,), (), (),
        (Boundary("manufactured-continuous-boundary", (component.component_id,), "declared steady boundary data; no free-boundary evolution or backreaction"),),
        (model,),
        (Adapter("continuous steady-water analogue adapter", "analogue-gravity vocabulary", "manufactured steady shallow-water residual control",
                 _default_output_contract().observable_ids, ("declared manufactured one-dimensional regime",),
                 "literal gravity, measurement, dispersive/free-boundary dynamics, and validation do not transport"),),
        (Invariant("complete N/2N/4N retention", "all mesh fields/residuals remain output", "approved ContinuousBackgroundSpec", "smartchem.water_wave_continuous/complete-diagnostic-v1"),
         Invariant("analogue casualty boundary", "run cannot promote structural toy evidence", "approved request", "smartchem.water_wave_continuous/analogue-boundary-v1")),
        (transport,),
        (TransportEvidence(transport.digest, ("manufactured steady shallow-water control",), ("typed deterministic domain solver",), ("measured validation and broader physics" ,)),),
        (assembly,),
        (AssemblyEvidence(assembly.digest, ("exact manufactured subject and retained convergence grids",), ("physical assembly/provenance",)),),
        scope, EvidenceStatus.STRUCTURAL_TOY,
    )
    contract = output_contract or _default_output_contract()
    request = SimulationRequest(source, resolved, physical_ir, contract, equivalence_contract or EquivalenceContract(
        "exact status/digest equality and binary64 equality of all retained N/2N/4N arrays and comparison payload",
        (), "meshes ordered N, 2N, 4N", "no RNG", "one indivisible continuous diagnostic; failed recomputation quarantines output",
    ), _obligations())
    blockers: list[str] = []
    if contract != _default_output_contract():
        blockers.append("this narrow continuous-water executor can honor only its exact default output contract")
    return CandidatePlan(request, model, SolverSpec(getattr(engine, "name", type(engine).__qualname__),
        "deterministic manufactured steady residual/regularity/convergence diagnostic", "1", (),
        "one complete N/2N/4N diagnostic call or no result", "typed manufactured input and immutable calculation identity"),
        CalculationSpec.from_oracle(engine), _compiler_implementation_digest(), _EXECUTOR_ID, (),
        (("engine calls", "1"), ("mesh evaluations", "N + 2N + 4N retained by domain"), ("wall/memory", "reported from retained finite meshes")),
        tuple(blockers), ExecutionLane.EXPERIMENTAL, limits or RuntimeLimits(max_engine_calls=1))


def compile_session_water_wave_continuous(source: SourceProgram | str, session: Session, slot_name: str,
                                          engine: object, **kwargs: object) -> CandidatePlan:
    if type(session) is not Session:
        raise TypeError("session must be an exact shepherd Session")
    if session.outcome is not COMPILED or session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError("continuous-water execution requires an outright closed COMPILED typed session")
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if slot.typed_binding is None or type(slot.typed_binding.value) is not ContinuousWaterSubject:
        raise TypeError(f"slot {slot_name!r} must hold an exact ContinuousWaterSubject")
    return compile_water_wave_continuous(source, slot.typed_binding.value, engine,
                                         shepherd_session_digest=canonical_digest(session), **kwargs)


def plan_preflight(plan: CandidatePlan) -> None:
    """Registry-callable refusal before calculation identity or journal creation."""
    if plan.executor_id != _EXECUTOR_ID:
        raise ValueError("continuous-water preflight received a different executor plan")
    if type(plan.request.resolved) is not ResolvedDomainProgram or type(plan.request.resolved.subject) is not ContinuousWaterSubject:
        raise ValueError("continuous-water executor requires an exact ResolvedDomainProgram ContinuousWaterSubject")
    model = _runtime_model()
    if plan.model != model or plan.request.physical_ir.models != (model,):
        raise ValueError("continuous-water model differs from the exact runtime-owned manufactured steady model")
    if plan.transforms:
        raise ValueError("continuous-water executor supports no transforms")
    scope = ClaimScope(ClaimKind.ANALOGUE, "structural manufactured continuous water-wave analogue", CONTINUOUS_WATER_CASUALTIES)
    if plan.request.physical_ir.claim_scope != scope or plan.request.physical_ir.evidence_status is not EvidenceStatus.STRUCTURAL_TOY:
        raise ValueError("continuous-water claim scope or evidence status was widened")


def _comparison(subject: ContinuousWaterSubject, diagnostic: ContinuousDiagnostic) -> ContinuousFiniteV2Comparison:
    """Run the exact attached v2 subject and explain the declared model difference."""
    finite = diagnose_water_wave_background(subject.finite_v2)
    heads = tuple(item.bernoulli_head_m for item in finite.samples)
    observed_head_range = max(heads) - min(heads)
    first_x = finite.samples[0].sample.x_m
    last_x = finite.samples[-1].sample.x_m
    declared_friction_drop = (
        subject.background.friction.constant_slope * (last_x - first_x)
    )
    expected_heads = tuple(
        subject.background.upstream_boundary.total_head_m
        - subject.background.friction.constant_slope * item.sample.x_m
        for item in finite.samples
    )
    reconstruction_offset = max(
        abs(observed - expected)
        for observed, expected in zip(heads, expected_heads)
    )
    head_scale = max(
        abs(heads[0]),
        subject.finite_v2.tolerances.head_reference_scale_m,
    )
    finite_head_tolerance = (
        subject.finite_v2.tolerances.head_relative * head_scale
    )
    friction_dominated = (
        not finite.head_gate_passed
        and declared_friction_drop
        > 10.0 * max(reconstruction_offset, finite_head_tolerance)
    )
    if friction_dominated:
        relation = (
            "FRICTION_DOMINATED_CONTINUOUS_PASS_LOSSLESS_FINITE_V2_HEAD_MISMATCH"
        )
        explanation = (
            "Finite v2 applies a lossless constant-head gate, while the continuous "
            "model declares frictional head loss. The declared friction head drop "
            "exceeds both the retained reconstruction offset and the v2 head tolerance "
            "by more than 10x, so friction dominates this specific disagreement. "
            "Neither diagnostic is promoted to physical truth."
        )
    elif finite.head_gate_passed:
        relation = "FINITE_V2_HEAD_GATE_AGREES_WITHIN_DECLARED_TOLERANCE"
        explanation = (
            "The independent finite-v2 lossless head gate passes at its declared "
            "tolerance. This numerical agreement does not validate either model."
        )
    else:
        relation = "FINITE_V2_HEAD_MISMATCH_CAUSE_NOT_ISOLATED"
        explanation = (
            "The independent finite-v2 head gate fails, but declared friction does "
            "not dominate the retained reconstruction offset and v2 tolerance by "
            "10x. The mismatch cause is therefore not isolated and no friction-only "
            "explanation is licensed."
        )
    return ContinuousFiniteV2Comparison(
        diagnostic.status.value,
        finite.status.value,
        relation,
        explanation,
        finite,
        observed_head_range,
        declared_friction_drop,
        reconstruction_offset,
    )


def _result(obligation: ValidityObligation, outcome: ObligationOutcome, detail: str) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _complete(diagnostic: object, spec: ContinuousBackgroundSpec) -> bool:
    return continuous_diagnostic_error(spec, diagnostic) is None


def _pre_result(obligation: ValidityObligation, approved: ApprovedPlan, subject: ContinuousWaterSubject) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.water_wave_continuous/typed-subject-v1":
        passed = type(subject) is ContinuousWaterSubject
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
                       "exact typed manufactured continuous subject is present" if passed else "unsupported subject")
    if obligation.evaluator_id == "smartchem.water_wave_continuous/analogue-boundary-v1":
        try:
            plan_preflight(approved.plan)
            return _result(obligation, ObligationOutcome.PASS, "claim remains the exact structural-toy analogue")
        except ValueError as error:
            return _result(obligation, ObligationOutcome.REFUSE, str(error))
    return _result(obligation, ObligationOutcome.REFUSE, f"no approved evaluator registered for {obligation.evaluator_id}")


def _post_result(obligation: ValidityObligation, diagnostic: object, spec: ContinuousBackgroundSpec,
                 emitted: tuple[str, ...], expected: tuple[str, ...]) -> ObligationResult:
    complete = _complete(diagnostic, spec)
    if obligation.evaluator_id == "smartchem.water_wave_continuous/complete-diagnostic-v1":
        error = continuous_diagnostic_error(spec, diagnostic)
        return _result(obligation, ObligationOutcome.PASS if complete else ObligationOutcome.FAIL,
                       "separate direct verifier retained the exact N/2N/4N diagnostic" if complete else f"diagnostic was altered, incomplete, or forged: {error}")
    if obligation.evaluator_id == "smartchem.water_wave_continuous/critical-compatibility-v1":
        passed = (
            complete
            and diagnostic.regularity_satisfied
            and diagnostic.status
            not in (ContinuousStatus.SOURCE_SIGN_INVALID, ContinuousStatus.REGULARITY_REFUSED)
        )
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
                       f"status={getattr(diagnostic, 'status', 'untyped')}" if passed else "critical compatibility did not pass")
    if obligation.evaluator_id == "smartchem.water_wave_continuous/convergence-v1":
        passed = complete and diagnostic.status is ContinuousStatus.CONVERGED_MANUFACTURED
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
                       "N/2N/4N records retained with passing domain convergence status" if passed else "convergence did not pass")
    if obligation.evaluator_id == "smartchem.water_wave_continuous/output-inventory-v1":
        passed = tuple(sorted(emitted)) == tuple(sorted(expected))
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
                       f"expected={sorted(expected)}, emitted={sorted(emitted)}")
    return _result(obligation, ObligationOutcome.REFUSE, f"no approved evaluator registered for {obligation.evaluator_id}")


def _execute_water_wave_continuous(approved: ApprovedPlan, engine: object, *, actual_calculation: CalculationSpec,
                                   journal_path: str | os.PathLike[str] | None = None,
                                   _dispatch_token: object = None) -> ExecutionReport:
    """Registry runner; common approval/calculation checks have already happened."""
    _require_runtime_dispatch(_dispatch_token)
    plan = approved.plan
    plan_preflight(plan)
    subject = plan.request.resolved.subject
    assert type(subject) is ContinuousWaterSubject
    spec = subject.background
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
        breach = _resource_wall(plan.limits, started=started, completed_calls=0, call_label="continuous-water engine calls")
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        if plan.limits.max_engine_calls is not None and plan.limits.max_engine_calls < 1:
            return ExecutionReport(journal.incomplete("approved max_engine_calls reached before the continuous diagnostic"), None, None)
        solver = getattr(engine, "solve", None)
        if not callable(solver):
            raise TypeError("continuous-water engine must expose solve(ContinuousBackgroundSpec)")
        diagnostic = solver(subject)
        if type(diagnostic) is not ContinuousDiagnostic:
            return ExecutionReport(journal.invalid("continuous-water engine returned no exact ContinuousDiagnostic"), None, None)
        journal.add_checkpoint(Artifact("checkpoint:continuous-water", "checkpoint", canonical_digest(diagnostic), True, False,
                                        detail=f"{diagnostic.status.value}; meshes={len(diagnostic.meshes)}", payload=diagnostic))
        if CalculationSpec.from_oracle(engine).digest != plan.calculation.digest:
            raise RuntimeError("CalculationSpec changed during the approved continuous-water engine call")
        comparison = _comparison(subject, diagnostic)
        payloads: dict[str, object] = {
            "water_wave_continuous_diagnostic": diagnostic,
            "water_wave_continuous_meshes": diagnostic.meshes,
            "water_wave_finite_v2_comparison": comparison,
        }
        emitted: list[str] = []
        for observable_id in plan.request.output_contract.observable_ids:
            payload = payloads[observable_id]
            journal.add_artifact(Artifact(f"observable:{observable_id}", "observable", canonical_digest(payload), True, False,
                                          detail=f"complete {observable_id}; continuous_status={diagnostic.status.value}", payload=payload))
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.POST:
                verdict = _post_result(obligation, diagnostic, spec, emitted_ids, plan.request.output_contract.observable_ids)
                journal.add_obligation_result(verdict)
                if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                    return ExecutionReport(journal.invalid(f"postcondition {obligation.name} ended {verdict.outcome.value}: {verdict.detail}"), None, None)
        certificate = Certificate(plan.request.source.digest, plan.request.digest, plan.digest, approved.approval.digest,
            actual_calculation.digest, plan.compiler_implementation_digest, journal.record.run_id, RunStatus.COMPLETE,
            plan.request.physical_ir.claim_scope, plan.request.physical_ir.evidence_status, journal.record.obligation_results,
            emitted_ids, plan.request.physical_ir.claim_scope.exclusions, CONTINUOUS_WATER_OMISSIONS, ())
        journal.add_artifact(Artifact("certificate", "certificate", certificate.digest, True, False, payload=certificate))
        elapsed = time.monotonic() - started
        values = tuple(StructuredObservableValue(item, payloads[item], next(o.unit for o in plan.request.output_contract.observables if o.observable_id == item),
            "manufactured continuous steady-water control v1", next(o.support for o in plan.request.output_contract.observables if o.observable_id == item), elapsed,
            "STRUCTURAL_TOY only; finite-v2 comparison does not promote either model.", "See certificate casualties and omissions.") for item in emitted_ids)
        result = SimulationResult(journal.record.run_id, values, certificate.digest)
        record = journal.complete()
        return ExecutionReport(record, result, certificate) if record.status is RunStatus.COMPLETE else ExecutionReport(record, None, None)
    except Exception as error:
        return ExecutionReport(journal.failed(f"{type(error).__name__}: {error}"), None, None)
