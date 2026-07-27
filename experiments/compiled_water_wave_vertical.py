"""Run an approved structural-toy classical water-wave kinematics acceptance vertical.

The profile is synthetic and chosen so the analytic long-wave counter-current
characteristic crosses zero once.  This is an executable compiler/runtime acceptance
calculation, not validation against a flume and not an astrophysical or quantum result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from smartchem import (
    COMPILED,
    FlowDirection,
    HorizonOrientation,
    InferenceKind,
    ProfilePoint,
    RegimeAssumptions,
    ShallowWaterHorizonEngine,
    SourceProgram,
    Spec,
    WaterWaveSpec,
    WaveBranch,
    WaveRegime,
    WaveTarget,
    approve,
    compile_session_water_wave_horizon,
    execute,
    record_approval,
    shepherd,
    water_wave_slot,
)


DEFAULT_JOURNAL = Path(__file__).with_name("compiled_water_wave_run.json")


def build_spec() -> WaterWaveSpec:
    """Synthetic single-crossing profile in explicit SI fields."""
    return WaterWaveSpec(
        profile=(
            ProfilePoint(-1.0, 0.1, 0.4),
            ProfilePoint(0.0, 0.1, 0.8),
            ProfilePoint(1.0, 0.1, 1.2),
            ProfilePoint(2.0, 0.1, 1.6),
        ),
        gravitational_acceleration_m_s2=9.81,
        target=WaveTarget.KINEMATIC_HORIZON,
        regime=WaveRegime.NONDISPERSIVE_SHALLOW_WATER,
        branch=WaveBranch.COUNTER_CURRENT,
        requested_orientation=HorizonOrientation.BLACK,
        flow_direction=FlowDirection.POSITIVE_X,
        assumptions=RegimeAssumptions(
            stationary=True,
            inviscid=True,
            irrotational=True,
            gravity_only=True,
            shallow_water=True,
            linear_perturbations=True,
            one_dimensional=True,
            prescribed_background=True,
            no_retained_wave_forcing=True,
            negligible_reflections=True,
        ),
    )


def compile_plan(engine: ShallowWaterHorizonEngine):
    source = SourceProgram(
        text=(
            "Model the kinematic black-hole analogue in this synthetic prescribed water "
            "profile. Preserve every profile and characteristic value. Do not infer "
            "scattering, thermality, quantum radiation, backreaction, or literal gravity."
        ),
        spans=(
            "kinematic black-hole analogue",
            "synthetic prescribed water profile",
            "Preserve every profile and characteristic value",
            "Do not infer scattering, thermality, quantum radiation, backreaction, or "
            "literal gravity",
        ),
        scientist="Leah",
    )
    spec = build_spec()
    starting = Spec(
        "compiled-water-wave-vertical",
        (water_wave_slot("water-model", "Simulate a black hole in water."),),
    )

    def select(current, _holes):
        return current.bind_typed(
            "water-model",
            spec,
            source_text=(
                "Use a counter-current nondispersive shallow-water characteristic on the "
                "supplied positive-x synthetic profile; test black-hole orientation."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        )

    session = shepherd(
        starting,
        select,
        discarded=(
            "literal astrophysical black hole",
            "unspecified target, orientation, wave regime, units, and profile",
            "scattering, thermal, quantum, laser, and backreaction interpretations",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return compile_session_water_wave_horizon(
        source,
        session,
        "water-model",
        engine,
    )


def run(journal_path: Path):
    engine = ShallowWaterHorizonEngine()
    plan = compile_plan(engine)
    approved = approve(
        plan,
        record_approval(
            plan,
            principal="Leah",
            scope=(
                "run this synthetic prescribed-background classical water-wave analogue; "
                "retain the full default output; no literal, scattering, thermal, quantum, "
                "laser, or backreaction claims"
            ),
        ),
    )
    return execute(approved, engine, journal_path=journal_path)


def summary(report) -> dict[str, object]:
    result = report.result
    diagnostic = result.values[0].payload if result is not None else None
    certificate_artifact = next(
        (
            item
            for item in report.record.artifacts
            if item.artifact_id == "certificate"
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
        "certificate_artifact_content_digest": (
            certificate_artifact.content_digest
            if certificate_artifact is not None
            else None
        ),
        "claim_scope": (
            report.certificate.claim_scope.kind.value
            if report.certificate is not None
            else None
        ),
        "claim_referent": (
            report.certificate.claim_scope.referent
            if report.certificate is not None
            else None
        ),
        "evidence_status": (
            report.certificate.evidence_status.value
            if report.certificate is not None
            else None
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
        "observable_uncertainty_notes": (
            {
                value.observable_id: value.uncertainty_note
                for value in result.values
            }
            if result is not None
            else {}
        ),
        "output_inventory": list(report.record.output_inventory),
        "diagnostic_status": diagnostic.status.value if diagnostic is not None else None,
        "horizons": (
            [
                {
                    "position_m": item.position_m,
                    "orientation": item.orientation.value,
                    "left_sample_index": item.left_sample_index,
                    "right_sample_index": item.right_sample_index,
                }
                for item in diagnostic.horizons
            ]
            if diagnostic is not None
            else []
        ),
        "characteristic_profile": (
            [
                {
                    "position_m": item.position_m,
                    "depth_m": item.depth_m,
                    "normal_velocity_m_s": item.normal_velocity_m_s,
                    "gravity_wave_speed_m_s": item.gravity_wave_speed_m_s,
                    "selected_characteristic_m_s": item.selected_characteristic_m_s,
                    "froude_number": item.froude_number,
                }
                for item in diagnostic.samples
            ]
            if diagnostic is not None
            else []
        ),
        "obligations": (
            [
                {
                    "obligation_digest": item.obligation_digest,
                    "outcome": item.outcome.value,
                    "detail": item.detail,
                }
                for item in report.certificate.validity_results
            ]
            if report.certificate is not None
            else []
        ),
        "failures": list(report.record.failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    args = parser.parse_args()
    report = run(args.journal)
    print(json.dumps(summary(report), indent=2, sort_keys=True))
    return 0 if report.record.status.value == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
