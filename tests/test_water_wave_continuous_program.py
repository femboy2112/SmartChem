"""Focused lifecycle boundaries for the continuous-water wrapper.

Registry integration is intentionally owned outside this pair of files.  The tests below
still pin the wrapper's public contract and activate its full lifecycle cases as soon as
the closed descriptor is present.
"""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from smartchem.contracts import ObligationOutcome, RunStatus
from smartchem.program import (
    Transform,
    approve,
    execute,
    record_approval,
)
from smartchem.water_wave_continuous import (
    CONTINUOUS_WATER_CASUALTIES,
    CONTINUOUS_WATER_OMISSIONS,
    ContinuousWaterSubject,
    ContinuousWaterWaveEngine,
    _default_output_contract,
    _runtime_model,
    compile_water_wave_continuous,
    plan_preflight,
)
from smartchem.water_wave_continuous_domain import (
    ContinuousBackgroundSpec,
    ContinuousDiagnostic,
    ContinuousStatus,
    ManufacturedFamily,
    RegularityRequirement,
    solve_continuous_background,
)


def _subject() -> ContinuousWaterSubject:
    return ContinuousWaterSubject.manufactured_comparison(
        ContinuousBackgroundSpec.manufactured(
            ManufacturedFamily.REGULAR_TRANSCRITICAL,
        )
    )


def _approved(plan):
    return approve(
        plan,
        record_approval(plan, "test", "run exact manufactured continuous-water control"),
    )


def test_runtime_model_is_explicit_about_critical_and_n_2n_4n_controls():
    model = _runtime_model()
    assert model.version == "1"
    assert any("critical compatibility" in equation for equation in model.equations)
    assert any("N, 2N, and 4N" in equation for equation in model.equations)
    assert any("finite-v2" in condition for condition in model.postconditions)


def test_output_contract_closes_the_retained_payload_inventory():
    contract = _default_output_contract()
    assert contract.observable_ids == (
        "water_wave_continuous_diagnostic",
        "water_wave_continuous_meshes",
        "water_wave_finite_v2_comparison",
    )
    assert "N, 2N, and 4N" in contract.observables[0].support
    assert "lossless-versus-friction" in contract.observables[2].diagnostics[0]


def test_subject_binds_an_exact_finite_v2_view_to_retained_continuous_points():
    subject = _subject()
    finest = solve_continuous_background(subject.background).meshes[-1]
    retained_x = {sample.x_m for sample in finest.samples}

    assert all(sample.x_m in retained_x for sample in subject.finite_v2.samples)
    assert len(subject.finite_v2.samples) == 9
    assert "finite-v2" in CONTINUOUS_WATER_OMISSIONS[-1]


def test_preflight_rejects_a_different_executor_before_any_journal_or_engine_call():
    forged = SimpleNamespace(executor_id="different-executor")
    with pytest.raises(ValueError, match="different executor"):
        plan_preflight(forged)  # type: ignore[arg-type]


def test_scope_casualties_keep_literal_gravity_and_measurement_out_of_the_vertical():
    joined = " ".join(CONTINUOUS_WATER_CASUALTIES)
    assert "measured" in joined
    assert "literal black hole" in joined
    assert "dispersive" in joined


def test_compiled_lifecycle_retains_meshes_and_explains_friction_v2_disagreement(tmp_path):
    engine = ContinuousWaterWaveEngine()
    plan = compile_water_wave_continuous("manufactured continuous test", _subject(), engine)

    report = execute(
        _approved(plan),
        engine,
        journal_path=tmp_path / "continuous.json",
    )

    assert report.record.status is RunStatus.COMPLETE
    assert report.result is not None and report.certificate is not None
    assert engine.calls == 1
    assert tuple(value.observable_id for value in report.result.values) == (
        "water_wave_continuous_diagnostic",
        "water_wave_continuous_meshes",
        "water_wave_finite_v2_comparison",
    )
    diagnostic = report.result.values[0].payload
    comparison = report.result.values[2].payload
    assert diagnostic.status is ContinuousStatus.CONVERGED_MANUFACTURED
    assert tuple(mesh.cells for mesh in diagnostic.meshes) == (32, 64, 128)
    assert comparison.finite_v2_diagnostic.head_gate_passed is False
    assert comparison.finite_v2_diagnostic.continuity_gate_passed is True
    assert comparison.finite_v2_diagnostic.shallow_water_gate_passed is True
    assert comparison.finite_v2_diagnostic.gravity_capillarity_gate_passed is True
    assert (
        comparison.finite_v2_diagnostic.uncertainty_resolved_bracket_gate_passed
        is True
    )
    assert comparison.finite_v2_diagnostic.orientation_gate_passed is True
    assert comparison.comparison == (
        "FRICTION_DOMINATED_CONTINUOUS_PASS_LOSSLESS_FINITE_V2_HEAD_MISMATCH"
    )
    assert all(
        result.outcome is ObligationOutcome.PASS
        for result in report.certificate.validity_results
    )


@pytest.mark.parametrize("attack", ("model", "transform"))
def test_model_and_transform_forgery_are_refused_before_engine_or_journal(
    tmp_path,
    attack,
):
    engine = ContinuousWaterWaveEngine()
    plan = compile_water_wave_continuous("manufactured continuous test", _subject(), engine)
    if attack == "model":
        model = replace(plan.model, version="forged")
        forged = replace(
            plan,
            model=model,
            request=replace(
                plan.request,
                physical_ir=replace(plan.request.physical_ir, models=(model,)),
            ),
        )
    else:
        forged = replace(
            plan,
            transforms=(
                Transform(
                    "forged",
                    "UNKNOWN",
                    plan.model.digest,
                    plan.model.digest,
                    (),
                    (),
                    (),
                ),
            ),
        )
    journal = tmp_path / f"{attack}.json"

    with pytest.raises(ValueError, match="runtime-owned|supports no transforms"):
        execute(_approved(forged), engine, journal_path=journal)

    assert engine.calls == 0
    assert not journal.exists()


def test_forged_engine_diagnostic_is_invalid_and_quarantined(tmp_path):
    class ForgingEngine(ContinuousWaterWaveEngine):
        def solve(self, subject):
            exact = super().solve(subject)
            forged_mesh = replace(
                exact.meshes[-1],
                depth_m=exact.meshes[-1].depth_m[:-1],
            )
            return replace(
                exact,
                meshes=exact.meshes[:-1] + (forged_mesh,),
            )

    engine = ForgingEngine()
    plan = compile_water_wave_continuous("manufactured continuous test", _subject(), engine)
    report = execute(
        _approved(plan),
        engine,
        journal_path=tmp_path / "forged-result.json",
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert engine.calls == 1
    assert "altered, incomplete, or forged" in report.record.failures[-1]


def test_false_regularity_cannot_complete_the_compiled_vertical(tmp_path):
    background = ContinuousBackgroundSpec.manufactured(
        ManufacturedFamily.REGULAR_TRANSCRITICAL,
        regularity=RegularityRequirement(False),
    )
    subject = ContinuousWaterSubject.manufactured_comparison(background)
    engine = ContinuousWaterWaveEngine()
    plan = compile_water_wave_continuous("false regularity mutation", subject, engine)
    report = execute(
        _approved(plan),
        engine,
        journal_path=tmp_path / "false-regularity.json",
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert "critical compatibility did not pass" in report.record.failures[-1]


def test_finite_v2_attachment_cannot_drift_from_the_retained_continuous_mesh():
    subject = _subject()
    changed_sample = replace(
        subject.finite_v2.samples[0],
        depth_m=subject.finite_v2.samples[0].depth_m + 0.01,
    )
    changed_v2 = replace(
        subject.finite_v2,
        samples=(changed_sample,) + subject.finite_v2.samples[1:],
    )

    with pytest.raises(ValueError, match="exactly retain"):
        replace(subject, finite_v2=changed_v2)


def test_public_compiled_experiment_summary_retains_real_lineage_and_comparison(
    tmp_path,
):
    from experiments.compiled_water_wave_continuous import run, summary

    payload = summary(run(tmp_path / "public-continuous.json"))

    assert payload["status"] == "COMPLETE"
    assert payload["engine_calls"] == 1
    assert payload["mesh_cells"] == [32, 64, 128]
    assert payload["finite_v2_head_gate_passed"] is False
    assert payload["comparison"] == (
        "FRICTION_DOMINATED_CONTINUOUS_PASS_LOSSLESS_FINITE_V2_HEAD_MISMATCH"
    )
    assert payload["obligation_outcomes"] == ["PASS"] * 6
    for key in (
        "source_digest",
        "resolved_digest",
        "physical_ir_digest",
        "request_digest",
        "plan_digest",
        "approval_digest",
        "calculation_digest",
        "compiler_implementation_digest",
        "diagnostic_digest",
        "certificate_digest",
    ):
        assert isinstance(payload[key], str) and len(payload[key]) == 64


def test_v2_head_mismatch_is_not_misattributed_when_friction_does_not_dominate(
    tmp_path,
):
    background = ContinuousBackgroundSpec.manufactured(
        ManufacturedFamily.REGULAR_TRANSCRITICAL,
        friction_slope=1e-14,
    )
    subject = ContinuousWaterSubject.manufactured_comparison(background)
    engine = ContinuousWaterWaveEngine()
    plan = compile_water_wave_continuous("tiny friction attribution probe", subject, engine)
    report = execute(
        _approved(plan),
        engine,
        journal_path=tmp_path / "tiny-friction.json",
    )

    assert report.record.status is RunStatus.COMPLETE
    comparison = report.result.values[2].payload
    assert comparison.finite_v2_diagnostic.head_gate_passed is False
    assert comparison.comparison == "FINITE_V2_HEAD_MISMATCH_CAUSE_NOT_ISOLATED"
    assert (
        comparison.declared_friction_head_drop_m
        < comparison.max_reconstruction_head_offset_m
    )
