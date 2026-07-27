"""Typed runtime for a manufactured finite-sample water-wave compatibility preflight.

The executor screens supplied manufactured sections against declared nominal
one-dimensional shallow-water compatibility gates. It deliberately reports only a
finite diagnostic: it neither manufactures measurement provenance nor extends
sample brackets into a continuum, dispersive, scattering, quantum, gravity, or
literal-black-hole result.
"""
from __future__ import annotations

import os
import time

from .contracts import (
    ClaimKind, EvidenceStatus, ExecutionLane, ObligationOutcome,
    ObligationResult, ObligationStage, RunStatus, ValidityObligation,
    canonical_digest,
)
from .ledger import BindingSchema, COMPILED, Session, Slot
from .program import (
    Adapter, ApprovedPlan, Artifact, AssemblyEvidence, AssemblySpec, Boundary,
    CalculationSpec, CandidatePlan, Certificate, ClaimScope, Component,
    EquivalenceContract, ExecutionReport, Identity, Invariant, ModelSpec,
    ObservableRequest, OutputContract, PhysicalIR, ResolvedDomainProgram,
    RunJournal, RuntimeLimits, SimulationRequest, SimulationResult, SolverSpec,
    SourceProgram, SourceTheory, StructuredObservableValue, TargetIntent,
    TransportEvidence, TransportMap, _WATER_WAVE_VALIDATION_EXECUTOR,
    _compiler_implementation_digest, _resource_wall,
)
from .water_wave_validation_domain import (
    BackgroundSample, CharacteristicInterval, CrossingBracket, SampleDiagnostic,
    ValidationDiagnostic, ValidationStatus, WaterWaveValidationSpec,
    diagnose_water_wave_background,
)

__all__ = [
    "WATER_WAVE_VALIDATION_CASUALTIES",
    "WATER_WAVE_VALIDATION_OMISSIONS",
    "FiniteSectionCompatibilityEngine",
    "compile_session_water_wave_validation",
    "compile_water_wave_validation",
    "water_wave_validation_slot",
]


WATER_WAVE_VALIDATION_CASUALTIES = (
    "a measured laboratory validation or measured water-channel profile",
    "a continuum statement between or beyond the supplied finite samples",
    "dispersive gravity-capillary, scattering, mode-conversion, or black-hole-laser dynamics",
    "quantum Hawking radiation, thermal spectra, or quantum state claims",
    "Einstein gravity, literal spacetime curvature, or an astrophysical black hole",
    "a physical horizon location rather than a sample-bounded kinematic bracket",
)

WATER_WAVE_VALIDATION_OMISSIONS = (
    "nominal-only discharge and Bernoulli-head gates do not propagate input uncertainty",
    "sectionwise q and Bernoulli-head agreement is not a steady momentum residual or a "
    "continuous stationary solution",
    "hydrostatic depth averaging, rectangular section means, inviscid lossless flow, "
    "unit energy coefficient, and absence of jumps or friction are assumptions, not checks",
    "no transcritical critical-control or regularity condition is checked",
    "no measured provenance, calibration, spatial-resolution study, or held-out validation is retained",
    "finite sample brackets do not establish a continuum crossing or its absence",
    "dispersive, scattering, quantum, and gravitational observables are not modeled",
)


class FiniteSectionCompatibilityEngine:
    """One deterministic manufactured finite-sample compatibility call."""

    name = "SmartChem manufactured water-wave finite-sample compatibility preflight"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": "finite-sample shallow-water compatibility preflight",
            "arithmetic": "IEEE-754 binary64",
            "crossing": "strict adjacent-sample U-sign(U)*sqrt(g*h) sign brackets only",
            "uncertainty": "characteristic interval only; nominal continuity/head gates",
            "version": 2,
        }

    def solve(self, spec: WaterWaveValidationSpec) -> ValidationDiagnostic:
        self.calls += 1
        return diagnose_water_wave_background(spec)


def water_wave_validation_slot(name: str, written: str) -> Slot:
    return Slot(name=name, written=written, schema=BindingSchema((WaterWaveValidationSpec,)))


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                "water_background_validation", "finite-sample background compatibility diagnostic",
                "typed SI record", "every supplied manufactured sample and declared gate",
                "no suppression of supplied samples", "retain binary64 derived values",
                "status, gates, samples, and finite crossing brackets",
                diagnostics=(
                    "compatibility is nominal and manufactured-only",
                    "finite samples are not a stationary continuum solution",
                    "crossing uncertainty and orientation gates are explicit",
                ),
                retention=("complete WaterWaveValidationSpec", "complete ValidationDiagnostic"),
            ),
            ObservableRequest(
                "water_background_sample_diagnostics", "complete per-sample diagnostic inventory",
                "m, m/s, m^3/s, dimensionless", "every supplied sample in source order",
                "exact scientist-supplied sampling", "retain binary64 input and derived values",
                "discharge, head residuals, regime values, characteristic interval",
                diagnostics=("input/output sample-count equality",),
                retention=("every exact SampleDiagnostic",),
            ),
            ObservableRequest(
                "water_background_crossing_brackets", "finite adjacent-sample kinematic brackets",
                "m and sample indices", "strict sign changes between adjacent supplied samples only",
                "one retained bracket per adjacent sign change", "retain binary64 interpolation point",
                "brackets and conservative whole-adjacent-interval bounds",
                diagnostics=("not a continuum crossing claim",),
                retention=("every exact CrossingBracket",),
            ),
            ObservableRequest(
                "water_background_regime_inventory", "complete shallow-water and gravity-capillarity gate inventory",
                "typed gate record", "all supplied samples and declared wavelength support",
                "all gates retained", "exact categorical and binary64 record",
                "continuity, head, shallow-water, gravity-capillarity, crossing-uncertainty, "
                "and orientation gates",
                diagnostics=("nominal-only continuity/head gates",),
                retention=("ValidationDiagnostic status and gate booleans",),
            ),
        ),
        diagnostics=(
            "typed manufactured-provenance, claim-scope, and finite-support verdicts",
            "exact output inventory", "refusals, invalid results, resource walls, and failures",
        ),
        retention=(
            "source program and typed shepherd interpretation", "complete plan and approval",
            "full diagnostic checkpoint", "every requested observable payload", "run record and certificate",
        ),
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation("water-background-subject-is-typed-and-manufactured", ObligationStage.PRE,
                           "smartchem.water_wave_validation/typed-manufactured-subject-v2",
                           "the approved subject is an exact manufactured finite background"),
        ValidityObligation("water-background-scope-remains-analogue", ObligationStage.PRE,
                           "smartchem.water_wave_validation/analogue-casualty-boundary-v2",
                           "the plan remains a structural-toy experimental analogue with every casualty"),
        ValidityObligation("water-background-diagnostic-is-complete", ObligationStage.POST,
                           "smartchem.water_wave_validation/complete-diagnostic-v2",
                           "the diagnostic equals an independent recomputation with every nested output"),
        ValidityObligation("water-background-output-inventory-is-exact", ObligationStage.POST,
                           "smartchem.water_wave_validation/output-inventory-v2",
                           "emitted observable identities exactly equal the frozen output contract"),
    )


def _manufactured_provenance_is_supported(spec: WaterWaveValidationSpec) -> bool:
    provenance = (
        spec.fluid.provenance, spec.wavelength_support.provenance, spec.tolerances.provenance,
    )
    normalized = tuple(item.casefold() for item in provenance)
    forbidden = ("measur", "observ", "experiment", "field", "laboratory", "calibrat")
    return (
        "manufactured" in normalized[0]
        and "manufactured" in normalized[2]
        and "declared" in normalized[1]
        and not any(token in item for item in normalized for token in forbidden)
    )


def compile_water_wave_validation(
    source: SourceProgram | str, spec: WaterWaveValidationSpec, engine: object, *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """Compile the finite preflight; unsupported evidence is a blocker, never a default."""
    if isinstance(source, str):
        source = SourceProgram(source)
    if type(source) is not SourceProgram:
        raise TypeError("source must be an exact SourceProgram or str")
    if type(spec) is not WaterWaveValidationSpec:
        raise TypeError("spec must be an exact WaterWaveValidationSpec")
    source_theory = SourceTheory(
        "analogue-gravity shallow-water vocabulary",
        ("a kinematic analogue is not literal gravity", "finite samples do not prove continuum behavior"),
        ("https://arxiv.org/abs/gr-qc/0205099", "https://arxiv.org/abs/1806.05539"),
    )
    target = TargetIntent(
        source.text, "finite manufactured one-dimensional open-channel samples",
        "screen finite-section nominal compatibility and sample-bounded kinematic brackets",
    )
    resolved = ResolvedDomainProgram(source.digest, spec, target, source_theory, shepherd_session_digest)
    model = ModelSpec(
        "manufactured finite-section shallow-water compatibility preflight",
        ("q = width * depth * velocity", "H = bed + depth + velocity^2/(2g)",
         "lambda = U - sqrt(g*h)", "kh = 2*pi*h/lambda_min", "Bo = rho*g*h^2/sigma"),
        (
            "one-dimensional finite supplied samples",
            "nominal section-mean continuity and lossless Bernoulli-head gates",
            "hydrostatic depth-averaged rectangular sections with unit energy coefficient",
            "no friction, hydraulic jump, or resolved transcritical control",
            "declared long-wave and gravity-dominance support",
            "manufactured, not measured, provenance",
        ),
        ("all inputs are exact WaterWaveValidationSpec values", "provenance is manufactured/declaration-only"),
        ("every sample is retained", "every adjacent strict sign bracket is retained", "status does not promote evidence"),
        (), "2",
    )
    transport = TransportMap(source_theory.digest, target.digest,
        preserved=("sample-level shallow-water kinematic characteristic",),
        modified=("source analogy is reduced to a nominal finite-section compatibility screen",),
        discarded=WATER_WAVE_VALIDATION_CASUALTIES,
        unknown=("actual-channel provenance and continuum behavior",),
    )
    assembly = AssemblySpec("manufactured finite-section background", "one SI cross-section sample",
                            ("source order retained", "no interpolation except bracket locator", "no measurement is implied"))
    claim_scope = ClaimScope(ClaimKind.ANALOGUE, "structural finite-sample water-wave analogue preflight", WATER_WAVE_VALIDATION_CASUALTIES)
    component = Component("manufactured-water-background", "one-dimensional shallow-water sample set",
                          Identity(canonical_digest(spec), "manufactured-water-background", (("position-unit", "m"), ("velocity-unit", "m/s"))))
    physical_ir = PhysicalIR(
        resolved.digest, (component,), (), (),
        (Boundary("supplied-manufactured-background", (component.component_id,), "fixed finite samples; no evolved free surface or backreaction"),),
        (model,),
        (Adapter("finite-background analogue adapter", "analogue-gravity vocabulary", "sample-level shallow-water checks",
                 _default_output_contract().observable_ids, ("manufactured finite samples",), "no literal or continuum physics transports"),),
        (Invariant("complete finite diagnostic", "every supplied sample and bracket is retained", "approved WaterWaveValidationSpec", "smartchem.water_wave_validation/complete-diagnostic-v2"),
         Invariant("analogue casualty boundary", "execution cannot promote a finite manufactured preflight", "approved request", "smartchem.water_wave_validation/analogue-casualty-boundary-v2")),
        (transport,),
        (TransportEvidence(transport.digest, ("finite-section shallow-water compatibility gate",), ("typed deterministic diagnostic",), ("steady momentum/regularity, measured provenance, and continuum validation",)),),
        (assembly,),
        (AssemblyEvidence(assembly.digest, ("typed manufactured samples",), ("measured assembly/provenance",)),),
        claim_scope, EvidenceStatus.STRUCTURAL_TOY,
    )
    contract = output_contract or _default_output_contract()
    request = SimulationRequest(source, resolved, physical_ir, contract, equivalence_contract or EquivalenceContract(
        "exact categorical/digest equality and binary64 equality of every retained sample, gate, and bracket",
        (), "source sample order and adjacent crossing order", "no RNG",
        "one indivisible diagnostic call; failed recomputation quarantines the output",
    ), _obligations())
    blockers: list[str] = []
    if contract != _default_output_contract():
        blockers.append("this narrow water-background executor can honor only its exact default output contract; changing support, resolution, precision, coverage, diagnostics, retention, or observable membership requires a different validated executor")
    if not _manufactured_provenance_is_supported(spec):
        blockers.append("measured, experimental, or non-manufactured provenance requires a data-bound validation executor; this preflight accepts only the declared manufactured profile")
    unsupported = sorted(set(contract.observable_ids) - set(_default_output_contract().observable_ids))
    if unsupported:
        blockers.append("water-background preflight executor cannot emit requested observable(s): " + ", ".join(unsupported))
    return CandidatePlan(request, model, SolverSpec(getattr(engine, "name", type(engine).__qualname__),
        "deterministic finite-section compatibility preflight", "2", (), "one complete diagnostic call or no result",
        "typed manufactured input, immutable calculation spec, and source digests"), CalculationSpec.from_oracle(engine),
        _compiler_implementation_digest(), _WATER_WAVE_VALIDATION_EXECUTOR, (),
        (("engine calls", "1"), ("sample evaluations", str(len(spec.samples))), ("wall/memory", "linear in retained finite samples")),
        tuple(blockers), ExecutionLane.EXPERIMENTAL, limits or RuntimeLimits(max_engine_calls=1))


def compile_session_water_wave_validation(
    source: SourceProgram | str, session: Session, slot_name: str, engine: object, **kwargs: object,
) -> CandidatePlan:
    if type(session) is not Session:
        raise TypeError("session must be an exact shepherd Session")
    if session.outcome != COMPILED or session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError("water-background execution requires an outright closed COMPILED typed session")
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if slot.typed_binding is None or type(slot.typed_binding.value) is not WaterWaveValidationSpec:
        raise TypeError(f"slot {slot_name!r} must hold an exact WaterWaveValidationSpec")
    return compile_water_wave_validation(source, slot.typed_binding.value, engine,
                                         shepherd_session_digest=canonical_digest(session), **kwargs)


def _result(obligation: ValidityObligation, outcome: ObligationOutcome, detail: str) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _pre_result(obligation: ValidityObligation, approved: ApprovedPlan, spec: WaterWaveValidationSpec) -> ObligationResult:
    plan = approved.plan
    if obligation.evaluator_id == "smartchem.water_wave_validation/typed-manufactured-subject-v2":
        passed = type(spec) is WaterWaveValidationSpec and _manufactured_provenance_is_supported(spec)
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
                       "exact typed manufactured profile and declared support are present" if passed else "subject or provenance is outside the supported manufactured preflight")
    if obligation.evaluator_id == "smartchem.water_wave_validation/analogue-casualty-boundary-v2":
        passed = (plan.request.physical_ir.claim_scope == ClaimScope(ClaimKind.ANALOGUE, "structural finite-sample water-wave analogue preflight", WATER_WAVE_VALIDATION_CASUALTIES)
                  and plan.request.physical_ir.evidence_status is EvidenceStatus.STRUCTURAL_TOY
                  and plan.execution_lane is ExecutionLane.EXPERIMENTAL)
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
                       "claim remains a structural-toy experimental analogue with exact casualties" if passed else "claim scope, evidence status, lane, or casualties were widened")
    return _result(obligation, ObligationOutcome.REFUSE, f"no approved evaluator registered for {obligation.evaluator_id}")


def _complete_diagnostic(diagnostic: object, spec: WaterWaveValidationSpec) -> bool:
    if type(diagnostic) is not ValidationDiagnostic:
        return False
    if type(diagnostic.spec) is not WaterWaveValidationSpec or canonical_digest(diagnostic.spec) != canonical_digest(spec):
        return False
    if type(diagnostic.samples) is not tuple or len(diagnostic.samples) != len(spec.samples):
        return False
    if any(type(item) is not SampleDiagnostic or type(item.sample) is not BackgroundSample or type(item.characteristic_interval) is not CharacteristicInterval for item in diagnostic.samples):
        return False
    if type(diagnostic.crossings) is not tuple or any(type(item) is not CrossingBracket for item in diagnostic.crossings):
        return False
    if type(diagnostic.status) is not ValidationStatus or any(type(getattr(diagnostic, name)) is not bool for name in (
        "continuity_gate_passed", "head_gate_passed", "shallow_water_gate_passed",
        "gravity_capillarity_gate_passed", "uncertainty_resolved_bracket_gate_passed",
        "position_order_resolved_gate_passed", "orientation_gate_passed")):
        return False
    return canonical_digest(diagnostic) == canonical_digest(diagnose_water_wave_background(spec))


def _post_result(obligation: ValidityObligation, diagnostic: object, spec: WaterWaveValidationSpec,
                 emitted: tuple[str, ...], expected: tuple[str, ...]) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.water_wave_validation/complete-diagnostic-v2":
        passed = _complete_diagnostic(diagnostic, spec)
        status = diagnostic.status.value if type(diagnostic) is ValidationDiagnostic else "untyped"
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
                       f"independent recomputation retained every sample, gate, and bracket; status={status}" if passed else "diagnostic or nested retained output was altered or forged")
    if obligation.evaluator_id == "smartchem.water_wave_validation/output-inventory-v2":
        passed = tuple(sorted(emitted)) == tuple(sorted(expected))
        return _result(obligation, ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
                       f"expected={sorted(expected)}, emitted={sorted(emitted)}")
    return _result(obligation, ObligationOutcome.REFUSE, f"no approved evaluator registered for {obligation.evaluator_id}")


def _execute_water_wave_validation(approved: ApprovedPlan, engine: object, *, actual_calculation: CalculationSpec,
                                   journal_path: str | os.PathLike[str] | None = None) -> ExecutionReport:
    """Run one approved preflight; completion follows result-safe construction only."""
    plan = approved.plan
    if plan.executor_id != _WATER_WAVE_VALIDATION_EXECUTOR:
        raise ValueError("water-background runner received a different executor plan")
    resolved = plan.request.resolved
    if type(resolved) is not ResolvedDomainProgram or type(resolved.subject) is not WaterWaveValidationSpec:
        raise TypeError("water-background executor requires an exact ResolvedDomainProgram WaterWaveValidationSpec")
    spec = resolved.subject
    started = time.monotonic()
    journal = RunJournal(approved, backend=actual_calculation.engine_name, path=journal_path)
    try:
        for artifact_id, kind, payload in (("source-program", "source", plan.request.source), ("candidate-plan", "plan", plan), ("approval", "approval", approved.approval)):
            journal.add_artifact(Artifact(artifact_id, kind, payload.digest, True, False, payload=payload))
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.PRE:
                verdict = _pre_result(obligation, approved, spec)
                journal.add_obligation_result(verdict)
                if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                    return ExecutionReport(journal.refused(f"precondition {obligation.name} ended {verdict.outcome.value}: {verdict.detail}"), None, None)
        breach = _resource_wall(plan.limits, started=started, completed_calls=0, call_label="water-background engine calls")
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        if plan.limits.max_engine_calls is not None and plan.limits.max_engine_calls < 1:
            return ExecutionReport(journal.incomplete("approved max_engine_calls reached before the diagnostic call"), None, None)
        solver = getattr(engine, "solve", None)
        if not callable(solver):
            raise TypeError("water-background engine must expose solve(WaterWaveValidationSpec)")
        diagnostic = solver(spec)
        if type(diagnostic) is not ValidationDiagnostic:
            return ExecutionReport(journal.invalid("water-background engine returned no exact ValidationDiagnostic"), None, None)
        journal.add_checkpoint(Artifact("checkpoint:water-background-validation", "checkpoint", canonical_digest(diagnostic), True, False,
                                        detail=f"{diagnostic.status.value}; {len(diagnostic.samples)} samples; {len(diagnostic.crossings)} brackets", payload=diagnostic))
        if CalculationSpec.from_oracle(engine).digest != plan.calculation.digest:
            raise RuntimeError("CalculationSpec changed during the approved water-background engine call")
        breach = _resource_wall(plan.limits, started=started, completed_calls=1, call_label="water-background engine calls")
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        payloads: dict[str, object] = {
            "water_background_validation": diagnostic,
            "water_background_sample_diagnostics": diagnostic.samples,
            "water_background_crossing_brackets": diagnostic.crossings,
            "water_background_regime_inventory": (
                diagnostic.status,
                diagnostic.continuity_gate_passed,
                diagnostic.head_gate_passed,
                diagnostic.shallow_water_gate_passed,
                diagnostic.gravity_capillarity_gate_passed,
                diagnostic.uncertainty_resolved_bracket_gate_passed,
                diagnostic.position_order_resolved_gate_passed,
                diagnostic.orientation_gate_passed,
            ),
        }
        emitted: list[str] = []
        for observable_id in plan.request.output_contract.observable_ids:
            payload = payloads[observable_id]
            journal.add_artifact(Artifact(f"observable:{observable_id}", "observable", canonical_digest(payload), True, False,
                                          detail=f"complete {observable_id}; status={diagnostic.status.value}; samples={len(diagnostic.samples)}", payload=payload))
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        journal.add_cache_state("no cache: one deterministic complete finite-background diagnostic call")
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.POST:
                verdict = _post_result(obligation, diagnostic, spec, emitted_ids, plan.request.output_contract.observable_ids)
                journal.add_obligation_result(verdict)
                if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                    return ExecutionReport(journal.invalid(f"postcondition {obligation.name} ended {verdict.outcome.value}: {verdict.detail}"), None, None)
        certificate = Certificate(plan.request.source.digest, plan.request.digest, plan.digest, approved.approval.digest,
            actual_calculation.digest, plan.compiler_implementation_digest, journal.record.run_id, RunStatus.COMPLETE,
            plan.request.physical_ir.claim_scope, plan.request.physical_ir.evidence_status, journal.record.obligation_results,
            emitted_ids, plan.request.physical_ir.claim_scope.exclusions, WATER_WAVE_VALIDATION_OMISSIONS, ())
        journal.add_artifact(Artifact("certificate", "certificate", certificate.digest, True, False, payload=certificate))
        elapsed = time.monotonic() - started
        values = tuple(StructuredObservableValue(observable_id, payloads[observable_id],
            next(item.unit for item in plan.request.output_contract.observables if item.observable_id == observable_id),
            "manufactured water-wave finite-section compatibility preflight v2",
            next(item.support for item in plan.request.output_contract.observables if item.observable_id == observable_id), elapsed,
            "No measurement uncertainty, provenance, continuum interpolation, or validation evidence was inferred; evidence remains STRUCTURAL_TOY.",
            "Finite manufactured preflight only; see certificate casualties and omissions.") for observable_id in emitted_ids)
        result = SimulationResult(journal.record.run_id, values, certificate.digest)
        record = journal.complete()
        return ExecutionReport(record, result, certificate) if record.status is RunStatus.COMPLETE else ExecutionReport(record, None, None)
    except Exception as error:
        return ExecutionReport(journal.failed(f"{type(error).__name__}: {error}"), None, None)
