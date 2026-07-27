"""Run the approved manufactured finite-section water-background preflight.

The profile is constructed to satisfy nominal sectionwise discharge and Bernoulli-head
compatibility while crossing the counter-current shallow-water characteristic between two
supplied samples with separated uncertainty intervals. It is synthetic compiler/runtime
evidence, not a continuous stationary solution or measured flume validation.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from smartchem import (
    COMPILED,
    BackgroundSample,
    BackgroundTolerances,
    DeclaredWavelengthSupport,
    FluidProperties,
    FlowDirection,
    HorizonOrientation,
    InferenceKind,
    SourceProgram,
    Spec,
    FiniteSectionCompatibilityEngine,
    WaterWaveValidationSpec,
    WaveBranch,
    approve,
    compile_session_water_wave_validation,
    execute,
    record_approval,
    shepherd,
    water_wave_validation_slot,
)


def build_spec() -> WaterWaveValidationSpec:
    """Return a two-sample exact manufactured profile with one nominal sign bracket."""
    gravity = 9.81
    wave_speed = math.sqrt(gravity)
    return WaterWaveValidationSpec(
        samples=(
            BackgroundSample(
                0.0,
                4.0,
                1.0,
                0.5 * wave_speed,
                0.0,
                0.01,
                0.01,
                0.005,
                0.01,
                0.005,
            ),
            BackgroundSample(
                10.0,
                1.0,
                1.0,
                2.0 * wave_speed,
                -1.875,
                0.01,
                0.01,
                0.005,
                0.01,
                0.005,
            ),
        ),
        fluid=FluidProperties(
            1000.0,
            0.072,
            gravity,
            "manufactured-water constants only",
        ),
        wavelength_support=DeclaredWavelengthSupport(
            100.0,
            200.0,
            0.1,
            1.0,
            "declared gravity-wave support for this manufactured preflight",
        ),
        tolerances=BackgroundTolerances(
            1e-10,
            1e-10,
            1.0,
            "manufactured-profile nominal acceptance gate",
        ),
        branch=WaveBranch.COUNTER_CURRENT,
        requested_orientation=HorizonOrientation.BLACK,
        flow_direction=FlowDirection.POSITIVE_X,
    )


def compile_plan(engine: FiniteSectionCompatibilityEngine):
    source = SourceProgram(
        text=(
            "Check whether these manufactured water-channel sections satisfy the declared "
            "nominal discharge and Bernoulli-head compatibility screen, whether their "
            "wavelength support is shallow and gravity dominated, and whether adjacent samples bracket the "
            "counter-current analogue characteristic. Retain every sample, uncertainty, "
            "residual, gate, and bracket; do not claim measured or continuum validation."
        ),
        spans=(
            "manufactured water-channel background",
            "nominal discharge and Bernoulli-head compatibility screen",
            "shallow and gravity dominated",
            "adjacent samples bracket",
            "retain every sample, uncertainty, residual, gate, and bracket",
            "do not claim measured or continuum validation",
        ),
        scientist="Leah",
    )
    spec = build_spec()
    starting = Spec(
        "compiled-water-background-validation",
        (
            water_wave_validation_slot(
                "water-background",
                "Validate the background for a black-hole-in-water analogue.",
            ),
        ),
    )
    session = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            "water-background",
            spec,
            source_text=(
                "Use the complete manufactured finite sections, nominal discharge/head "
                "compatibility gates, declared wavelength/capillarity support, and "
                "sample-bracket-only crossing semantics."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        ),
        discarded=(
            "measured flume provenance",
            "continuous-profile interpolation or absence claim",
            "dispersive, scattering, quantum, or literal-gravity interpretation",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return compile_session_water_wave_validation(
        source,
        session,
        "water-background",
        engine,
    )


def run(journal: Path):
    engine = FiniteSectionCompatibilityEngine()
    plan = compile_plan(engine)
    approved = approve(
        plan,
        record_approval(
            plan,
            principal="Leah",
            scope=(
                "run this complete manufactured finite-background preflight with no "
                "measured, continuum, dispersive, quantum, or literal-gravity claim"
            ),
        ),
    )
    return execute(approved, engine, journal_path=journal)


def summary(report) -> dict[str, object]:
    diagnostic = report.result.values[0].payload if report.result is not None else None
    plan_artifact = next(
        (
            artifact
            for artifact in report.record.artifacts
            if artifact.artifact_id == "candidate-plan"
        ),
        None,
    )
    plan = plan_artifact.payload if plan_artifact is not None else None
    certificate = next(
        (
            artifact
            for artifact in report.record.artifacts
            if artifact.artifact_id == "certificate"
        ),
        None,
    )
    return {
        "run_id": report.record.run_id,
        "status": report.record.status.value,
        "started_at": report.record.started_at,
        "updated_at": report.record.updated_at,
        "plan_digest": report.record.plan_digest,
        "approval_digest": report.record.approval_digest,
        "source_digest": plan.request.source.digest if plan is not None else None,
        "resolved_program_digest": (
            plan.request.resolved.digest if plan is not None else None
        ),
        "physical_ir_digest": (
            plan.request.physical_ir.digest if plan is not None else None
        ),
        "request_digest": plan.request.digest if plan is not None else None,
        "calculation_digest": plan.calculation.digest if plan is not None else None,
        "engine_implementation_digest": (
            plan.calculation.implementation_digest
            if plan is not None
            else None
        ),
        "compiler_implementation_digest": (
            plan.compiler_implementation_digest if plan is not None else None
        ),
        "certificate_artifact_content_digest": (
            certificate.content_digest if certificate is not None else None
        ),
        "claim_scope": (
            report.certificate.claim_scope.kind.value
            if report.certificate is not None
            else None
        ),
        "evidence_status": (
            report.certificate.evidence_status.value
            if report.certificate is not None
            else None
        ),
        "output_inventory": (
            list(report.certificate.output_inventory)
            if report.certificate is not None
            else []
        ),
        "observable_digests": (
            {
                value.observable_id: value.digest
                for value in report.result.values
            }
            if report.result is not None
            else {}
        ),
        "diagnostic_status": (
            diagnostic.status.value if diagnostic is not None else None
        ),
        "gate_results": (
            {
                "continuity": diagnostic.continuity_gate_passed,
                "head": diagnostic.head_gate_passed,
                "shallow_water": diagnostic.shallow_water_gate_passed,
                "gravity_capillarity": diagnostic.gravity_capillarity_gate_passed,
                "crossing_uncertainty_resolved": (
                    diagnostic.uncertainty_resolved_bracket_gate_passed
                ),
                "position_order_resolved": (
                    diagnostic.position_order_resolved_gate_passed
                ),
                "orientation": diagnostic.orientation_gate_passed,
            }
            if diagnostic is not None
            else {}
        ),
        "samples": (
            [
                {
                    "x_m": item.sample.x_m,
                    "discharge_m3_s": item.discharge_m3_s,
                    "bernoulli_head_m": item.bernoulli_head_m,
                    "continuity_residual": item.normalized_continuity_residual,
                    "head_residual": item.normalized_head_residual,
                    "kh": item.kh_at_shortest_wavelength,
                    "bond_number": item.bond_number,
                    "characteristic_m_s": item.characteristic_m_s,
                    "characteristic_interval_m_s": [
                        item.characteristic_interval.lower_m_s,
                        item.characteristic_interval.upper_m_s,
                    ],
                }
                for item in diagnostic.samples
            ]
            if diagnostic is not None
            else []
        ),
        "crossings": (
            [
                {
                    "left_index": item.left_sample_index,
                    "right_index": item.right_sample_index,
                    "linear_position_m": item.linear_interpolation_position_m,
                    "conservative_interval_m": list(
                        item.conservative_position_interval_m
                    ),
                    "orientation": item.orientation.value,
                    "uncertainty_resolved": item.uncertainty_resolved,
                    "position_order_resolved": item.position_order_resolved,
                }
                for item in diagnostic.crossings
            ]
            if diagnostic is not None
            else []
        ),
        "obligations": (
            [
                {
                    "outcome": item.outcome.value,
                    "detail": item.detail,
                }
                for item in report.certificate.validity_results
            ]
            if report.certificate is not None
            else []
        ),
        "casualties": (
            list(report.certificate.casualties)
            if report.certificate is not None
            else []
        ),
        "omissions": (
            list(report.certificate.omissions)
            if report.certificate is not None
            else []
        ),
        "failures": list(report.record.failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--journal",
        required=True,
        type=Path,
        help="fresh write-once JSON journal path",
    )
    arguments = parser.parse_args()
    report = run(arguments.journal)
    print(json.dumps(summary(report), indent=2, sort_keys=True))
    return 0 if report.record.status.value == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
