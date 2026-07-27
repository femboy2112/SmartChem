"""Acceptance tests for the finite manufactured water-wave background preflight."""
from __future__ import annotations

import math
from dataclasses import replace

import pytest

from smartchem.water_wave_validation_domain import (
    BackgroundSample,
    BackgroundTolerances,
    DeclaredWavelengthSupport,
    FluidProperties,
    ValidationStatus,
    WaterWaveValidationSpec,
    diagnose_water_wave_background,
)
from smartchem.water_wave_domain import (
    FlowDirection,
    HorizonOrientation,
    WaveBranch,
)


G = 9.81
DEPTH = 1.0
C = math.sqrt(G * DEPTH)


def sample(x: float, velocity: float, *, depth: float = DEPTH, width: float = 2.0, bed: float = 0.0, uncertainty: float = 0.0) -> BackgroundSample:
    return BackgroundSample(
        x_m=x,
        width_m=width,
        depth_m=depth,
        velocity_m_s=velocity,
        bed_elevation_m=bed,
        x_uncertainty_m=uncertainty,
        width_uncertainty_m=uncertainty,
        depth_uncertainty_m=uncertainty,
        velocity_uncertainty_m_s=uncertainty,
        bed_elevation_uncertainty_m=uncertainty,
    )


def spec(
    samples: tuple[BackgroundSample, ...],
    *,
    continuity: float = 1e-10,
    head: float = 1e-10,
    min_wavelength: float = 100.0,
    min_bond: float = 1.0,
    flow_direction: FlowDirection = FlowDirection.POSITIVE_X,
    orientation: HorizonOrientation = HorizonOrientation.BLACK,
) -> WaterWaveValidationSpec:
    return WaterWaveValidationSpec(
        samples=samples,
        fluid=FluidProperties(1000.0, 0.072, G, "manufactured-water constants"),
        wavelength_support=DeclaredWavelengthSupport(
            min_wavelength, 200.0, 0.1, min_bond, "declared gravity-wave support"
        ),
        tolerances=BackgroundTolerances(
            continuity, head, 1.0, "manufactured-profile acceptance gate"
        ),
        branch=WaveBranch.COUNTER_CURRENT,
        requested_orientation=orientation,
        flow_direction=flow_direction,
    )


def test_inconsistent_head_is_retained_and_rejected_without_dropping_samples():
    # q is conserved but the nominal Bernoulli head is not.
    low = sample(0.0, 0.5 * C, width=4.0)
    high = sample(10.0, 2.0 * C, width=1.0)
    diagnostic = diagnose_water_wave_background(spec((low, high)))

    assert diagnostic.status is ValidationStatus.FINITE_SAMPLE_BALANCE_INCOMPATIBLE
    assert tuple(item.sample for item in diagnostic.samples) == (low, high)
    assert tuple(item.discharge_m3_s for item in diagnostic.samples) == pytest.approx((2.0 * C, 2.0 * C))
    assert tuple(item.bernoulli_head_m for item in diagnostic.samples) == pytest.approx((1.125, 3.0))
    assert diagnostic.head_gate_passed is False


def test_pass_manufactured_profile_has_expected_residuals_gates_and_bracket():
    low = sample(0.0, 0.5 * C, width=4.0, bed=0.0)
    # H_low=1.125 and H_high=bed+3, so the declared bed offset preserves H.
    high = sample(10.0, 2.0 * C, width=1.0, bed=-1.875)
    diagnostic = diagnose_water_wave_background(spec((low, high)))

    assert diagnostic.status is ValidationStatus.FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET
    assert diagnostic.continuity_gate_passed and diagnostic.head_gate_passed
    assert diagnostic.shallow_water_gate_passed and diagnostic.gravity_capillarity_gate_passed
    assert tuple(item.normalized_continuity_residual for item in diagnostic.samples) == pytest.approx((0.0, 0.0))
    assert tuple(item.normalized_head_residual for item in diagnostic.samples) == pytest.approx((0.0, 0.0))
    assert len(diagnostic.crossings) == 1
    crossing = diagnostic.crossings[0]
    assert crossing.conservative_position_interval_m == (0.0, 10.0)
    assert 0.0 < crossing.linear_interpolation_position_m < 10.0
    assert all(item.kh_at_shortest_wavelength < 0.1 for item in diagnostic.samples)
    assert all(item.bond_number > 1.0 for item in diagnostic.samples)


@pytest.mark.parametrize(
    "subject, expected_gate",
    [
        (spec((sample(0.0, C, width=2.0), sample(1.0, C, width=3.0))), "continuity_gate_passed"),
        (spec((sample(0.0, C, width=2.0), sample(1.0, C, width=2.0, bed=0.5))), "head_gate_passed"),
    ],
)
def test_background_failures_are_inadmissible(subject, expected_gate):
    diagnostic = diagnose_water_wave_background(subject)
    assert diagnostic.status is ValidationStatus.FINITE_SAMPLE_BALANCE_INCOMPATIBLE
    assert getattr(diagnostic, expected_gate) is False


@pytest.mark.parametrize(
    "subject, expected_gate",
    [
        (spec((sample(0.0, C, width=2.0), sample(1.0, C, width=2.0)), min_wavelength=1.0), "shallow_water_gate_passed"),
        (spec((sample(0.0, C, width=2.0), sample(1.0, C, width=2.0)), min_bond=1e9), "gravity_capillarity_gate_passed"),
    ],
)
def test_regime_failures_are_explicit(subject, expected_gate):
    diagnostic = diagnose_water_wave_background(subject)
    assert diagnostic.status is ValidationStatus.REGIME_UNSUPPORTED
    assert getattr(diagnostic, expected_gate) is False


def test_no_bracket_at_samples_does_not_erase_samples_or_claim_continuous_absence():
    diagnostic = diagnose_water_wave_background(
        spec((sample(0.0, 0.5 * C, width=4.0), sample(10.0, 0.75 * C, width=8.0 / 3.0, bed=-0.15625)))
    )
    assert diagnostic.status is ValidationStatus.NO_BRACKET_AT_SAMPLES
    assert diagnostic.crossings == ()
    assert len(diagnostic.samples) == 2


def test_negative_flow_uses_the_sign_aware_counter_current_characteristic():
    low = sample(0.0, -0.5 * C, width=4.0)
    high = sample(10.0, -2.0 * C, width=1.0, bed=-1.875)
    diagnostic = diagnose_water_wave_background(
        spec(
            (low, high),
            flow_direction=FlowDirection.NEGATIVE_X,
            orientation=HorizonOrientation.WHITE,
        )
    )

    assert diagnostic.status is ValidationStatus.FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET
    assert tuple(item.characteristic_m_s for item in diagnostic.samples) == pytest.approx(
        (0.5 * C, -1.0 * C)
    )
    assert len(diagnostic.crossings) == 1
    assert diagnostic.crossings[0].orientation is HorizonOrientation.WHITE


def test_larger_uncertainty_only_widens_the_conservative_characteristic_interval():
    exact = diagnose_water_wave_background(
        spec((sample(0.0, 0.5 * C, width=4.0), sample(10.0, 2.0 * C, width=1.0, bed=-1.875)))
    )
    uncertain = diagnose_water_wave_background(
        spec((sample(0.0, 0.5 * C, width=4.0, uncertainty=0.01), sample(10.0, 2.0 * C, width=1.0, bed=-1.875, uncertainty=0.01)))
    )
    for exact_item, uncertain_item in zip(exact.samples, uncertain.samples):
        assert uncertain_item.characteristic_interval.lower_m_s <= exact_item.characteristic_interval.lower_m_s
        assert uncertain_item.characteristic_interval.upper_m_s >= exact_item.characteristic_interval.upper_m_s
    assert (
        uncertain.crossings[0].conservative_position_interval_m[0]
        <= exact.crossings[0].conservative_position_interval_m[0]
    )
    assert (
        uncertain.crossings[0].conservative_position_interval_m[1]
        >= exact.crossings[0].conservative_position_interval_m[1]
    )


def test_nominal_bracket_can_be_unresolved_by_declared_input_uncertainty():
    left = sample(0.0, 0.99 * C, width=2.0, uncertainty=0.1)
    right = sample(
        1.0,
        1.01 * C,
        width=2.0 * 0.99 / 1.01,
        bed=-0.02,
        uncertainty=0.1,
    )
    diagnostic = diagnose_water_wave_background(spec((left, right)))

    assert diagnostic.status is ValidationStatus.UNCERTAINTY_AMBIGUOUS_SAMPLE_BRACKET
    assert len(diagnostic.crossings) == 1
    assert diagnostic.crossings[0].uncertainty_resolved is False
    assert diagnostic.uncertainty_resolved_bracket_gate_passed is False
    assert all(
        item.characteristic_interval.lower_m_s < 0.0
        < item.characteristic_interval.upper_m_s
        for item in diagnostic.samples
    )


def test_overlapping_position_intervals_make_order_and_orientation_ambiguous():
    left = replace(
        sample(0.0, 0.5 * C, width=4.0),
        x_uncertainty_m=1.0,
    )
    right = replace(
        sample(0.1, 2.0 * C, width=1.0, bed=-1.875),
        x_uncertainty_m=1.0,
    )
    diagnostic = diagnose_water_wave_background(spec((left, right)))

    assert diagnostic.status is ValidationStatus.POSITION_ORDER_AMBIGUOUS
    assert diagnostic.position_order_resolved_gate_passed is False
    assert diagnostic.crossings[0].position_order_resolved is False
    assert diagnostic.crossings[0].conservative_position_interval_m == (-1.0, 1.1)


def test_orientation_mismatch_and_pair_semantics_are_explicit():
    low = sample(0.0, 0.5 * C, width=4.0)
    high = sample(10.0, 2.0 * C, width=1.0, bed=-1.875)
    mismatch = diagnose_water_wave_background(
        spec((low, high), orientation=HorizonOrientation.WHITE)
    )
    pair = diagnose_water_wave_background(
        spec(
            (low, high, sample(20.0, 0.5 * C, width=4.0)),
            orientation=HorizonOrientation.PAIR,
        )
    )

    assert mismatch.status is ValidationStatus.ORIENTATION_MISMATCH
    assert mismatch.crossings[0].orientation is HorizonOrientation.BLACK
    assert mismatch.orientation_gate_passed is False
    assert pair.status is (
        ValidationStatus
        .FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET
    )
    assert tuple(item.orientation for item in pair.crossings) == (
        HorizonOrientation.BLACK,
        HorizonOrientation.WHITE,
    )
    assert pair.orientation_gate_passed is True


def test_digests_are_stable_and_change_when_retained_input_changes():
    first = spec((sample(0.0, C, width=2.0), sample(1.0, C, width=2.0)))
    equal = spec((sample(0.0, C, width=2.0), sample(1.0, C, width=2.0)))
    changed = spec((sample(0.0, C, width=2.0), sample(1.0, C, width=2.0, bed=0.01)))
    assert len(first.digest) == 64
    assert first.digest == equal.digest
    assert first.digest != changed.digest
    assert diagnose_water_wave_background(first).digest == diagnose_water_wave_background(equal).digest


def test_exact_type_and_bad_value_invariants_reject_forged_or_malformed_inputs():
    class ForgedSpec(WaterWaveValidationSpec):
        pass

    genuine = spec((sample(0.0, C, width=2.0), sample(1.0, C, width=2.0)))
    forged = ForgedSpec(**genuine.__dict__)
    with pytest.raises(TypeError, match="exact WaterWaveValidationSpec"):
        diagnose_water_wave_background(forged)
    with pytest.raises(ValueError, match="nonnegative"):
        sample(0.0, C, uncertainty=-0.01)
    with pytest.raises(ValueError, match="positive depth interval"):
        sample(0.0, C, uncertainty=1.0)
    with pytest.raises(ValueError, match="preserve the declared flow direction"):
        sample(0.0, 0.005, uncertainty=0.01)
    with pytest.raises(TypeError, match="exact BackgroundSample"):
        WaterWaveValidationSpec(
            samples=(sample(0.0, C), object()),  # type: ignore[arg-type]
            fluid=genuine.fluid,
            wavelength_support=genuine.wavelength_support,
            tolerances=genuine.tolerances,
            branch=WaveBranch.COUNTER_CURRENT,
            requested_orientation=HorizonOrientation.BLACK,
            flow_direction=FlowDirection.POSITIVE_X,
        )
    with pytest.raises(ValueError, match="supports only COUNTER_CURRENT"):
        replace(genuine, branch=WaveBranch.CO_CURRENT)
    with pytest.raises(ValueError, match="declared flow direction"):
        replace(genuine, flow_direction=FlowDirection.NEGATIVE_X)
