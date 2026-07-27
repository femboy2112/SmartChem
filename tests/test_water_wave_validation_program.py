"""Acceptance tests for the manufactured finite water-background v2 vertical."""
from __future__ import annotations

from dataclasses import replace
import math

import pytest

import smartchem
import smartchem.program as program_module
from smartchem.contracts import ClaimKind, EvidenceStatus, InferenceKind, RunStatus
from smartchem.ledger import COMPILED, STALLED, Spec, shepherd
from smartchem.program import (
    ClaimScope, ObservableRequest, RuntimeLimits, approve, execute, record_approval,
)
from smartchem.water_wave_validation import (
    WATER_WAVE_VALIDATION_CASUALTIES, WATER_WAVE_VALIDATION_OMISSIONS,
    FiniteSectionCompatibilityEngine, compile_session_water_wave_validation,
    compile_water_wave_validation, water_wave_validation_slot,
)
from smartchem.water_wave_validation_domain import (
    BackgroundSample, BackgroundTolerances, DeclaredWavelengthSupport,
    FluidProperties, ValidationDiagnostic, ValidationStatus, WaterWaveValidationSpec,
    diagnose_water_wave_background,
)
from smartchem.water_wave_domain import (
    FlowDirection,
    HorizonOrientation,
    WaveBranch,
)


G = 9.81
C = math.sqrt(G)


def _sample(x: float, velocity: float, *, width: float, bed: float = 0.0) -> BackgroundSample:
    return BackgroundSample(x, width, 1.0, velocity, bed, 0.0, 0.0, 0.0, 0.0, 0.0)


def _spec(samples: tuple[BackgroundSample, ...] | None = None) -> WaterWaveValidationSpec:
    # This is the passing manufactured profile from the domain acceptance tests.
    return WaterWaveValidationSpec(
        samples or (_sample(0.0, 0.5 * C, width=4.0), _sample(10.0, 2.0 * C, width=1.0, bed=-1.875)),
        FluidProperties(1000.0, 0.072, G, "manufactured-water constants"),
        DeclaredWavelengthSupport(100.0, 200.0, 0.1, 1.0, "declared gravity-wave support"),
        BackgroundTolerances(1e-10, 1e-10, 1.0, "manufactured-profile acceptance gate"),
        WaveBranch.COUNTER_CURRENT,
        HorizonOrientation.BLACK,
        FlowDirection.POSITIVE_X,
    )


def _approved(plan):
    return approve(plan, record_approval(plan, "scientist", "manufactured finite water-background preflight only"))


def test_v2_public_symbols_are_explicitly_exported():
    assert {
        "WaterWaveValidationSpec",
        "WaterWaveValidationStatus",
        "FiniteSectionCompatibilityEngine",
        "compile_water_wave_validation",
    }.issubset(smartchem.__all__)


def test_public_experiment_summary_is_complete_and_uses_real_identity_fields(tmp_path):
    from experiments.compiled_water_wave_validation import run, summary

    payload = summary(run(tmp_path / "public-summary.json"))

    assert payload["status"] == "COMPLETE"
    assert payload["diagnostic_status"] == (
        "FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET"
    )
    assert len(payload["compiler_implementation_digest"]) == 64
    assert len(payload["engine_implementation_digest"]) == 64
    assert payload["gate_results"]["crossing_uncertainty_resolved"] is True
    assert payload["gate_results"]["position_order_resolved"] is True
    assert payload["crossings"][0]["orientation"] == "BLACK"


def test_typed_shepherd_lifecycle_and_exact_output_contract(tmp_path):
    subject = _spec()
    starting = Spec("water-background", (water_wave_validation_slot("background", "Check a water analogue background."),))
    stalled = shepherd(starting, lambda spec, _holes: spec)
    assert stalled.outcome == STALLED
    with pytest.raises(ValueError, match="COMPILED"):
        compile_session_water_wave_validation("check", stalled, "background", FiniteSectionCompatibilityEngine())

    session = shepherd(starting, lambda current, _holes: current.bind_typed(
        "background", subject, source_text="Use a manufactured finite profile preflight.", inference=InferenceKind.QUESTION_CONFIRMED))
    assert session.outcome == COMPILED
    engine = FiniteSectionCompatibilityEngine()
    report = execute(_approved(compile_session_water_wave_validation("check", session, "background", engine)), engine, journal_path=tmp_path / "run.json")

    assert report.record.status is RunStatus.COMPLETE
    assert engine.calls == 1
    assert report.result is not None and report.certificate is not None
    assert report.result.values[0].payload.status is ValidationStatus.FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET
    assert report.result.values[0].payload.orientation_gate_passed is True
    assert (
        report.result.values[0].payload
        .uncertainty_resolved_bracket_gate_passed
        is True
    )
    assert report.certificate.claim_scope.kind is ClaimKind.ANALOGUE
    assert report.certificate.evidence_status is EvidenceStatus.STRUCTURAL_TOY
    assert report.certificate.casualties == WATER_WAVE_VALIDATION_CASUALTIES
    assert report.certificate.omissions == WATER_WAVE_VALIDATION_OMISSIONS
    assert report.certificate.output_inventory == (
        "water_background_validation", "water_background_sample_diagnostics",
        "water_background_crossing_brackets", "water_background_regime_inventory",
    )
    assert len(report.record.checkpoints) == 1


def test_contract_mutation_and_nonmanufactured_provenance_are_blockers():
    engine = FiniteSectionCompatibilityEngine()
    baseline = compile_water_wave_validation("check", _spec(), engine)
    expanded = replace(baseline.request.output_contract, observables=baseline.request.output_contract.observables + (
        ObservableRequest("quantum_emission", "unsupported", "none", "none", "none", "none", "none"),))
    plan = compile_water_wave_validation("check", _spec(), engine, output_contract=expanded)
    assert plan.blockers
    with pytest.raises(ValueError, match="blockers"):
        _approved(plan)
    unmanufactured = replace(_spec(), fluid=replace(_spec().fluid, provenance="measured flume record"))
    provenance_plan = compile_water_wave_validation("check", unmanufactured, engine)
    assert any("provenance" in blocker for blocker in provenance_plan.blockers)


def test_forged_diagnostic_is_invalid_after_checkpoint():
    from smartchem.water_wave_validation_domain import SampleDiagnostic

    class ForgedSample(SampleDiagnostic):
        pass

    class ForgingEngine(FiniteSectionCompatibilityEngine):
        def solve(self, subject):
            self.calls += 1
            genuine = diagnose_water_wave_background(subject)
            forged = ForgedSample(**genuine.samples[0].__dict__)
            return replace(genuine, samples=(forged,) + genuine.samples[1:])

    engine = ForgingEngine()
    report = execute(_approved(compile_water_wave_validation("check", _spec(), engine)), engine)
    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert len(report.record.checkpoints) == 1


def test_calculation_and_implementation_mutation_are_rejected_before_execution(monkeypatch):
    class ChangingEngine(FiniteSectionCompatibilityEngine):
        revision = 1
        def calculation_spec(self):
            base = super().calculation_spec()
            base["revision"] = self.revision
            return base

    engine = ChangingEngine()
    approved = _approved(compile_water_wave_validation("check", _spec(), engine))
    engine.revision = 2
    with pytest.raises(ValueError, match="CalculationSpec changed"):
        execute(approved, engine)

    clean_engine = FiniteSectionCompatibilityEngine()
    clean_approved = _approved(compile_water_wave_validation("check", _spec(), clean_engine))
    monkeypatch.setattr(program_module, "_compiler_implementation_digest", lambda: "changed")
    with pytest.raises(ValueError, match="implementation changed"):
        execute(clean_approved, clean_engine)


def test_resource_wall_and_tampered_claim_scope_refuse_without_result():
    engine = FiniteSectionCompatibilityEngine()
    resource_plan = compile_water_wave_validation("check", _spec(), engine, limits=RuntimeLimits(max_engine_calls=0))
    resource_report = execute(_approved(resource_plan), engine)
    assert resource_report.record.status is RunStatus.INCOMPLETE
    assert engine.calls == 0

    plan = compile_water_wave_validation("check", _spec(), FiniteSectionCompatibilityEngine())
    widened_ir = replace(plan.request.physical_ir, claim_scope=ClaimScope(ClaimKind.LITERAL, "measured flume validation", ()))
    tampered = replace(plan, request=replace(plan.request, physical_ir=widened_ir))
    report = execute(_approved(tampered), FiniteSectionCompatibilityEngine())
    assert report.record.status is RunStatus.REFUSED
    assert report.result is None


@pytest.mark.parametrize("subject, status", [
    (_spec((_sample(0.0, 0.5 * C, width=4.0), _sample(10.0, 0.75 * C, width=8.0 / 3.0, bed=-0.15625))), ValidationStatus.NO_BRACKET_AT_SAMPLES),
    (_spec((_sample(0.0, 0.5 * C, width=4.0), _sample(10.0, 2.0 * C, width=1.0))), ValidationStatus.FINITE_SAMPLE_BALANCE_INCOMPATIBLE),
])
def test_negative_diagnostics_complete_without_promoting_evidence(subject, status):
    engine = FiniteSectionCompatibilityEngine()
    report = execute(_approved(compile_water_wave_validation("check", subject, engine)), engine)
    assert report.record.status is RunStatus.COMPLETE
    assert report.result is not None
    assert report.result.values[0].payload.status is status
    assert report.certificate.evidence_status is EvidenceStatus.STRUCTURAL_TOY
