"""Decisive acceptance tests for manufactured continuous steady backgrounds."""
from __future__ import annotations

from dataclasses import replace

import pytest

from smartchem.contracts import EvidenceStatus
import smartchem.water_wave_continuous_domain as continuous_domain
from smartchem.water_wave_continuous_domain import (
    ContinuousBackgroundSpec,
    ContinuousStatus,
    ContinuousUncertainty,
    FrictionLaw,
    ManufacturedFamily,
    RegularityRequirement,
    SourceLaw,
    solve_continuous_background,
)


@pytest.mark.parametrize("family", tuple(ManufacturedFamily))
def test_each_manufactured_family_retains_a_three_mesh_convergence_receipt(family):
    diagnostic = solve_continuous_background(ContinuousBackgroundSpec.manufactured(family))

    assert diagnostic.status is ContinuousStatus.CONVERGED_MANUFACTURED
    assert diagnostic.evidence_status is EvidenceStatus.STRUCTURAL_TOY
    assert diagnostic.spec.evidence_status is EvidenceStatus.STRUCTURAL_TOY
    assert tuple(mesh.cells for mesh in diagnostic.meshes) == (32, 64, 128)
    # The off-grid regular-critical limiter is grid-phase sensitive. Require both
    # refinement pairs to decrease at first-order class or better, not a cherry-picked
    # final-pair rate or an invented universal second-order claim.
    assert diagnostic.spatial_convergence_order is not None
    assert 0.8 <= diagnostic.spatial_convergence_order <= 2.4
    assert diagnostic.residual_convergence_order is not None
    assert diagnostic.residual_convergence_order >= 0.8
    errors = tuple(mesh.l2_depth_error for mesh in diagnostic.meshes)
    residuals = tuple(mesh.momentum_residual_l2 for mesh in diagnostic.meshes)
    assert errors[0] > errors[1] > errors[2]
    assert residuals[0] > residuals[1] > residuals[2]
    for mesh in diagnostic.meshes:
        assert len(mesh.samples) == len(mesh.x_m) == mesh.cells
        assert len(mesh.depth_m) == len(mesh.velocity_m_s) == mesh.cells
        assert len(mesh.bed_elevation_m) == len(mesh.head_m) == mesh.cells
        assert len(mesh.source_slope) == len(mesh.friction_slope) == mesh.cells
        assert len(mesh.continuity_residual) == len(mesh.momentum_residual) == mesh.cells
        assert len(mesh.root_iterations) == len(mesh.energy_root_residual_m) == mesh.cells
        assert len(mesh.critical_projection_applied) == mesh.cells
        assert mesh.max_continuity_residual == pytest.approx(0.0, abs=1e-14)
        assert mesh.max_energy_root_residual_m < 1e-4
        assert all(
            iteration in (0, 80)
            for iteration in mesh.root_iterations
        )
        assert all(left < right for left, right in zip(mesh.x_m, mesh.x_m[1:]))
    assert all(
        mesh.observed_order is not None and mesh.observed_order >= 0.8
        for mesh in diagnostic.meshes[1:]
    )


def test_subcritical_root_bracketing_has_a_finite_refusal_budget(monkeypatch):
    spec = ContinuousBackgroundSpec.manufactured(ManufacturedFamily.SUBCRITICAL)
    hc = (
        spec.discharge_m3_s ** 2
        / (
            spec.gravitational_acceleration_m_s2
            * spec.width_m ** 2
        )
    ) ** (1.0 / 3.0)
    params = continuous_domain._family_parameters(spec.family)
    h0 = continuous_domain._exact_depth(0.0, spec.length_m, hc, params)

    monkeypatch.setattr(
        continuous_domain,
        "_bed_elevation",
        lambda *_args, **_kwargs: 0.0,
    )
    monkeypatch.setattr(
        continuous_domain,
        "_specific_energy",
        lambda depth, *_args, **_kwargs: 2.0 if depth == h0 else 0.0,
    )

    with pytest.raises(ValueError, match="within 64 expansions"):
        continuous_domain._root_reconstruct_depth(
            0.0,
            spec.length_m / spec.base_cells,
            spec,
            hc,
            params,
        )


def test_subcritical_and_supercritical_froude_regimes_do_not_get_relabelled():
    subcritical = solve_continuous_background(
        ContinuousBackgroundSpec.manufactured(ManufacturedFamily.SUBCRITICAL)
    )
    supercritical = solve_continuous_background(
        ContinuousBackgroundSpec.manufactured(ManufacturedFamily.SUPERCRITICAL)
    )

    assert max(subcritical.meshes[-1].froude_number) < 1.0
    assert min(supercritical.meshes[-1].froude_number) > 1.0


def test_regular_transcritical_family_has_one_declared_critical_point_and_exact_compatibility():
    spec = ContinuousBackgroundSpec.manufactured(ManufacturedFamily.REGULAR_TRANSCRITICAL)
    diagnostic = solve_continuous_background(spec)

    assert diagnostic.critical_location_m == pytest.approx(0.43 * spec.length_m)
    assert diagnostic.regularity_satisfied is True
    assert diagnostic.meshes[-1].critical_compatibility_residual == pytest.approx(0.0, abs=1e-13)
    froude = diagnostic.meshes[-1].froude_number
    assert min(froude) < 1.0 < max(froude)
    assert sum(
        (left - 1.0) * (right - 1.0) < 0.0
        for left, right in zip(froude, froude[1:])
    ) == 1


def test_discharge_and_head_fields_are_retained_not_reconstructed_from_a_summary():
    diagnostic = solve_continuous_background(
        ContinuousBackgroundSpec.manufactured(ManufacturedFamily.SUBCRITICAL)
    )
    mesh = diagnostic.meshes[-1]
    spec = diagnostic.spec

    assert all(q == pytest.approx(spec.discharge_m3_s) for q in mesh.discharge_m3_s)
    for sample in mesh.samples:
        assert sample.discharge_m3_s == pytest.approx(spec.width_m * sample.depth_m * sample.velocity_m_s)
        assert sample.total_head_m == pytest.approx(
            sample.bed_elevation_m + sample.depth_m + sample.velocity_m_s ** 2 / (2.0 * spec.gravitational_acceleration_m_s2)
        )


def test_sign_flip_is_a_discriminating_mutation_not_a_second_valid_convention():
    spec = ContinuousBackgroundSpec.manufactured(ManufacturedFamily.REGULAR_TRANSCRITICAL)
    bad = replace(spec, source=replace(spec.source, balance_sign=-1))
    diagnostic = solve_continuous_background(bad)

    assert diagnostic.status is ContinuousStatus.SOURCE_SIGN_INVALID
    assert diagnostic.regularity_satisfied is False
    assert abs(diagnostic.meshes[-1].critical_compatibility_residual) > 0.0


def test_false_regularity_declaration_is_refused_even_for_an_exact_family():
    spec = ContinuousBackgroundSpec.manufactured(ManufacturedFamily.REGULAR_TRANSCRITICAL)
    bad = replace(spec, regularity=RegularityRequirement(False))
    diagnostic = solve_continuous_background(bad)

    assert diagnostic.status is ContinuousStatus.REGULARITY_REFUSED
    assert diagnostic.regularity_satisfied is False


def test_boundary_mutation_is_reported_not_absorbed_by_interpolation():
    spec = ContinuousBackgroundSpec.manufactured(ManufacturedFamily.SUBCRITICAL)
    bad_boundary = replace(spec.downstream_boundary, depth_m=spec.downstream_boundary.depth_m + 0.1)
    diagnostic = solve_continuous_background(replace(spec, downstream_boundary=bad_boundary))

    assert diagnostic.status is ContinuousStatus.BOUNDARY_MISMATCH


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda spec: replace(spec, friction=None), "friction must be an exact FrictionLaw"),
        (lambda spec: replace(spec, uncertainty=None), "uncertainty must be an exact ContinuousUncertainty"),
        (lambda spec: replace(spec, evidence_status=EvidenceStatus.EXPERIMENTAL), "STRUCTURAL_TOY"),
        (lambda spec: replace(spec, provenance="measured flume"), "manufactured"),
    ],
)
def test_omitted_friction_or_uncertainty_and_evidence_promotion_are_unconstructible(mutation, message):
    spec = ContinuousBackgroundSpec.manufactured(ManufacturedFamily.SUBCRITICAL)
    with pytest.raises((TypeError, ValueError), match=message):
        mutation(spec)


def test_uncertainty_is_retained_in_the_full_spec_and_survives_the_numerical_receipt():
    uncertainty = ContinuousUncertainty(depth_m=0.01, discharge_m3_s=0.02, slope=0.003)
    diagnostic = solve_continuous_background(
        ContinuousBackgroundSpec.manufactured(ManufacturedFamily.SUPERCRITICAL, uncertainty=uncertainty)
    )

    assert diagnostic.spec.uncertainty == uncertainty
    assert all(sample.source_slope != 0.0 and sample.friction_slope > 0.0 for sample in diagnostic.meshes[-1].samples)


def test_friction_is_required_and_positive():
    with pytest.raises(ValueError, match="positive"):
        FrictionLaw(0.0)


@pytest.mark.parametrize(
    "constructor",
    (
        lambda: FrictionLaw(0.01, "measured flume calibration"),
        lambda: SourceLaw(1, "measured bed survey"),
    ),
)
def test_source_and_friction_provenance_cannot_smuggle_measurement_authority(
    constructor,
):
    with pytest.raises(ValueError, match="manufactured-only"):
        constructor()


def test_reported_convergence_is_the_conservative_minimum_over_both_pairs():
    diagnostic = solve_continuous_background(
        ContinuousBackgroundSpec.manufactured(
            ManufacturedFamily.REGULAR_TRANSCRITICAL,
            base_cells=32,
        )
    )
    pair_orders = tuple(
        mesh.observed_order for mesh in diagnostic.meshes[1:]
    )

    assert diagnostic.status is ContinuousStatus.CONVERGED_MANUFACTURED
    assert diagnostic.spatial_convergence_order == min(pair_orders)
    assert diagnostic.spatial_convergence_order < max(pair_orders)


def test_omitting_friction_from_the_balance_creates_a_nonconvergent_order_one_residual():
    diagnostic = solve_continuous_background(
        ContinuousBackgroundSpec.manufactured(
            ManufacturedFamily.REGULAR_TRANSCRITICAL,
        )
    )
    mesh = diagnostic.meshes[-1]
    dx = diagnostic.spec.length_m / mesh.cells
    depth_prime = tuple(
        (
            (mesh.depth_m[1] - mesh.depth_m[0]) / dx
            if index == 0
            else (mesh.depth_m[-1] - mesh.depth_m[-2]) / dx
            if index == mesh.cells - 1
            else (mesh.depth_m[index + 1] - mesh.depth_m[index - 1])
            / (2.0 * dx)
        )
        for index in range(mesh.cells)
    )
    omitted_friction = tuple(
        (1.0 - froude * froude) * derivative - source
        for froude, derivative, source in zip(
            mesh.froude_number,
            depth_prime,
            mesh.source_slope,
        )
    )

    assert min(abs(value) for value in omitted_friction) > 0.009
    assert mesh.max_momentum_residual < 1e-4
