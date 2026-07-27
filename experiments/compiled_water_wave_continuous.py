"""Run the approved manufactured continuous steady-water control.

The calculation reconstructs one regular-transcritical manufactured background on
N, 2N, and 4N meshes, checks steady balance and both critical compatibility
conditions, and compares the retained finest-mesh points with the independent
finite-section v2 diagnostic.
It remains STRUCTURAL_TOY evidence, not a measured flume or continuum theorem.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from smartchem import (
    COMPILED,
    ContinuousBackgroundSpec,
    ContinuousWaterSubject,
    ContinuousWaterWaveEngine,
    InferenceKind,
    ManufacturedFamily,
    SourceProgram,
    Spec,
    approve,
    canonical_digest,
    compile_session_water_wave_continuous,
    continuous_water_slot,
    execute,
    record_approval,
    shepherd,
)


def build_subject() -> ContinuousWaterSubject:
    background = ContinuousBackgroundSpec.manufactured(
        ManufacturedFamily.REGULAR_TRANSCRITICAL,
        length_m=10.0,
        width_m=2.0,
        discharge_m3_s=2.0,
        gravitational_acceleration_m_s2=9.81,
        friction_slope=0.01,
        base_cells=32,
    )
    return ContinuousWaterSubject.manufactured_comparison(
        background,
        retained_sample_count=9,
    )


def compile_plan(engine: ContinuousWaterWaveEngine):
    source = SourceProgram(
        (
            "Run the manufactured continuous steady shallow-water control on the "
            "declared regular-transcritical family. Retain the N, 2N, and 4N meshes, "
            "all fields and residuals, binary64 roundings of a 60-digit Decimal "
            "manufactured reference evaluation, critical "
            "numerator/derivative "
            "compatibility, metadata-only uncertainty, and the "
            "exact finite-v2 comparison. Explain the friction/lossless disagreement. "
            "Do not claim a measured flume, continuum theorem, dispersive scattering, "
            "quantum radiation, or literal gravity."
        ),
        (
            "manufactured continuous steady shallow-water control",
            "regular-transcritical family",
            "N, 2N, and 4N meshes",
            "critical numerator and derivative compatibility",
            "finite-v2 comparison",
            "friction/lossless disagreement",
        ),
        "Leah",
    )
    subject = build_subject()
    starting = Spec(
        "compiled-continuous-water-control",
        (
            continuous_water_slot(
                "continuous-water",
                "Confirm the manufactured family, balances, mesh ladder, and comparison.",
            ),
        ),
    )
    session = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            "continuous-water",
            subject,
            source_text=(
                "Use the exact regular-transcritical manufactured subject, constant "
                "friction/source balance, metadata-only uncertainty, 32/64/128 meshes, and "
                "the attached nine-point finite-v2 comparison."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        ),
        discarded=(
            "measured provenance or calibration",
            "general continuum or time-dependent solution",
            "dispersive, quantum, or literal-gravity interpretation",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return compile_session_water_wave_continuous(
        source,
        session,
        "continuous-water",
        engine,
    )


def run(journal: Path):
    engine = ContinuousWaterWaveEngine()
    plan = compile_plan(engine)
    approved = approve(
        plan,
        record_approval(
            plan,
            "Leah",
            (
                "run this manufactured regular-transcritical N/2N/4N control with "
                "complete residual, reference, metadata-only uncertainty, both critical, and finite-v2 outputs; "
                "retain STRUCTURAL_TOY scope"
            ),
        ),
    )
    return plan, engine, execute(
        approved,
        engine,
        journal_path=journal,
    )


def summary(results: object) -> dict[str, object]:
    plan, engine, report = results
    if report.result is None or report.certificate is None:
        return {
            "status": report.record.status.value,
            "engine_calls": engine.calls,
            "failures": list(report.record.failures),
        }
    diagnostic = report.result.values[0].payload
    comparison = report.result.values[2].payload
    return {
        "run_id": report.record.run_id,
        "status": report.record.status.value,
        "engine_calls": engine.calls,
        "family": diagnostic.spec.family.value,
        "claim_kind": report.certificate.claim_scope.kind.value,
        "evidence_status": report.certificate.evidence_status.value,
        "execution_lane": plan.execution_lane.value,
        "mesh_cells": [mesh.cells for mesh in diagnostic.meshes],
        "depth_l2_errors": [mesh.l2_depth_error for mesh in diagnostic.meshes],
        "max_absolute_depth_errors_m": [
            max(map(abs, mesh.depth_error_m)) for mesh in diagnostic.meshes
        ],
        "momentum_residual_l2": [
            mesh.momentum_residual_l2 for mesh in diagnostic.meshes
        ],
        "max_continuity_residuals": [
            mesh.max_continuity_residual for mesh in diagnostic.meshes
        ],
        "max_momentum_residuals": [
            mesh.max_momentum_residual for mesh in diagnostic.meshes
        ],
        "max_energy_root_residuals_m": [
            mesh.max_energy_root_residual_m for mesh in diagnostic.meshes
        ],
        "critical_projection_counts": [
            sum(mesh.critical_projection_applied) for mesh in diagnostic.meshes
        ],
        "root_iteration_ranges": [
            [min(mesh.root_iterations), max(mesh.root_iterations)]
            for mesh in diagnostic.meshes
        ],
        "spatial_convergence_order": diagnostic.spatial_convergence_order,
        "residual_convergence_order": diagnostic.residual_convergence_order,
        "critical_location_m": diagnostic.critical_location_m,
        "critical_compatibility_residual": (
            diagnostic.meshes[-1].critical_compatibility_residual
        ),
        "critical_derivative_compatibility_residual": (
            diagnostic.meshes[-1].critical_derivative_compatibility_residual
        ),
        "regularity_satisfied": diagnostic.regularity_satisfied,
        "uncertainty_propagated": diagnostic.uncertainty_propagated,
        "uncertainty_semantics": diagnostic.uncertainty_semantics,
        "finite_v2_status": comparison.finite_v2_status,
        "finite_v2_head_gate_passed": (
            comparison.finite_v2_diagnostic.head_gate_passed
        ),
        "comparison": comparison.comparison,
        "comparison_explanation": comparison.explanation,
        "observed_head_range_m": comparison.observed_head_range_m,
        "declared_friction_head_drop_m": (
            comparison.declared_friction_head_drop_m
        ),
        "max_reconstruction_head_offset_m": (
            comparison.max_reconstruction_head_offset_m
        ),
        "finite_v2_sample_count": len(
            comparison.finite_v2_diagnostic.samples
        ),
        "output_inventory": list(report.certificate.output_inventory),
        "obligation_outcomes": [
            item.outcome.value for item in report.certificate.validity_results
        ],
        "source_digest": plan.request.source.digest,
        "resolved_digest": plan.request.resolved.digest,
        "physical_ir_digest": plan.request.physical_ir.digest,
        "request_digest": plan.request.digest,
        "plan_digest": plan.digest,
        "approval_digest": report.certificate.approval_digest,
        "calculation_digest": report.certificate.calculation_digest,
        "compiler_implementation_digest": (
            report.certificate.compiler_implementation_digest
        ),
        "diagnostic_digest": canonical_digest(diagnostic),
        "certificate_digest": report.certificate.digest,
        "casualties": list(report.certificate.casualties),
        "omissions": list(report.certificate.omissions),
        "failures": list(report.record.failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summary(run(args.journal)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
