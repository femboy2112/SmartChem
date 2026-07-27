"""Acceptance tests for the pure prescribed-background shallow-water diagnostic."""
from __future__ import annotations

import math

import pytest

from smartchem.water_wave_domain import (
    WaveBranch,
    FlowDirection,
    HorizonOrientation,
    HorizonStatus,
    ProfilePoint,
    RegimeAssumptions,
    WaveRegime,
    WaveTarget,
    WaterWaveSpec,
    diagnose_horizon,
)


G = 9.81
DEPTH = 1.0
C = math.sqrt(G * DEPTH)


def assumptions(**changes: bool) -> RegimeAssumptions:
    values = {
        "stationary": True,
        "inviscid": True,
        "irrotational": True,
        "gravity_only": True,
        "shallow_water": True,
        "linear_perturbations": True,
        "one_dimensional": True,
        "prescribed_background": True,
        "no_retained_wave_forcing": True,
        "negligible_reflections": True,
    }
    values.update(changes)
    return RegimeAssumptions(**values)


def request(
    velocities: tuple[float, ...],
    *,
    direction: FlowDirection = FlowDirection.POSITIVE_X,
    branch: WaveBranch = WaveBranch.COUNTER_CURRENT,
    orientation: HorizonOrientation = HorizonOrientation.BLACK,
    target: WaveTarget = WaveTarget.KINEMATIC_HORIZON,
    regime: WaveRegime = WaveRegime.NONDISPERSIVE_SHALLOW_WATER,
    declared_assumptions: RegimeAssumptions | None = None,
) -> WaterWaveSpec:
    return WaterWaveSpec(
        profile=tuple(
            ProfilePoint(float(index), DEPTH, velocity) for index, velocity in enumerate(velocities)
        ),
        gravitational_acceleration_m_s2=G,
        target=target,
        regime=regime,
        branch=branch,
        requested_orientation=orientation,
        flow_direction=direction,
        assumptions=declared_assumptions or assumptions(),
    )


def test_counter_current_positive_flow_acceleration_is_a_black_horizon():
    diagnostic = diagnose_horizon(request((0.5 * C, 1.5 * C)))

    assert diagnostic.status is HorizonStatus.KINEMATIC_CROSSING_IN_DECLARED_MODEL
    assert len(diagnostic.horizons) == 1
    horizon = diagnostic.horizons[0]
    assert horizon.orientation is HorizonOrientation.BLACK
    assert horizon.position_m == pytest.approx(0.5)
    assert tuple(sample.froude_number for sample in diagnostic.samples) == pytest.approx((0.5, 1.5))
    assert tuple(sample.gravity_wave_speed_m_s for sample in diagnostic.samples) == pytest.approx((C, C))


def test_counter_current_positive_flow_deceleration_is_a_white_horizon():
    diagnostic = diagnose_horizon(
        request((1.5 * C, 0.5 * C), orientation=HorizonOrientation.WHITE)
    )

    assert diagnostic.status is HorizonStatus.KINEMATIC_CROSSING_IN_DECLARED_MODEL
    assert diagnostic.horizons[0].orientation is HorizonOrientation.WHITE
    assert diagnostic.horizons[0].position_m == pytest.approx(0.5)


def test_negative_x_flow_uses_downstream_order_not_left_to_right_order():
    diagnostic = diagnose_horizon(
        request(
            (-1.5 * C, -0.5 * C),
            direction=FlowDirection.NEGATIVE_X,
            orientation=HorizonOrientation.BLACK,
        )
    )

    assert diagnostic.status is HorizonStatus.KINEMATIC_CROSSING_IN_DECLARED_MODEL
    assert diagnostic.horizons[0].orientation is HorizonOrientation.BLACK
    assert diagnostic.horizons[0].position_m == pytest.approx(0.5)


def test_negative_x_flow_deceleration_along_flow_is_a_white_horizon():
    diagnostic = diagnose_horizon(
        request(
            (-0.5 * C, -1.5 * C),
            direction=FlowDirection.NEGATIVE_X,
            orientation=HorizonOrientation.WHITE,
        )
    )

    assert diagnostic.status is HorizonStatus.KINEMATIC_CROSSING_IN_DECLARED_MODEL
    assert diagnostic.horizons[0].orientation is HorizonOrientation.WHITE
    assert diagnostic.horizons[0].position_m == pytest.approx(0.5)


def test_subcritical_counter_current_profile_is_a_complete_no_horizon_result():
    diagnostic = diagnose_horizon(request((0.2 * C, 0.8 * C)))

    assert diagnostic.status is HorizonStatus.NO_HORIZON_IN_DECLARED_REGIME
    assert diagnostic.horizons == ()
    assert len(diagnostic.samples) == len(diagnostic.spec.profile) == 2


def test_co_current_characteristic_has_no_horizon_for_unidirectional_flow():
    diagnostic = diagnose_horizon(
        request((0.5 * C, 1.5 * C), branch=WaveBranch.CO_CURRENT)
    )

    assert diagnostic.status is HorizonStatus.NO_HORIZON_IN_DECLARED_REGIME
    assert diagnostic.horizons == ()
    assert all(sample.selected_characteristic_m_s > 0.0 for sample in diagnostic.samples)


def test_multiple_crossings_are_retained_and_can_satisfy_a_requested_pair():
    diagnostic = diagnose_horizon(
        request(
            (0.5 * C, 1.5 * C, 0.5 * C),
            orientation=HorizonOrientation.PAIR,
        )
    )

    assert diagnostic.status is HorizonStatus.KINEMATIC_CROSSING_IN_DECLARED_MODEL
    assert tuple(horizon.orientation for horizon in diagnostic.horizons) == (
        HorizonOrientation.BLACK,
        HorizonOrientation.WHITE,
    )
    assert tuple(horizon.position_m for horizon in diagnostic.horizons) == pytest.approx((0.5, 1.5))


def test_an_isolated_exact_critical_sample_is_a_strict_zero_crossing():
    diagnostic = diagnose_horizon(request((0.5 * C, C, 1.5 * C)))

    assert diagnostic.status is HorizonStatus.KINEMATIC_CROSSING_IN_DECLARED_MODEL
    assert len(diagnostic.horizons) == 1
    assert diagnostic.horizons[0].orientation is HorizonOrientation.BLACK
    assert diagnostic.horizons[0].position_m == pytest.approx(1.0)


def test_requested_orientation_mismatch_is_reported_without_relabelling_crossing():
    diagnostic = diagnose_horizon(request((0.5 * C, 1.5 * C), orientation=HorizonOrientation.WHITE))

    assert diagnostic.status is HorizonStatus.ORIENTATION_MISMATCH
    assert diagnostic.horizons[0].orientation is HorizonOrientation.BLACK


@pytest.mark.parametrize(
    "factory, error",
    [
        (
            lambda: ProfilePoint(0.0, -1.0, 1.0),
            "depth_m must be positive",
        ),
        (
            lambda: ProfilePoint(float("nan"), 1.0, 1.0),
            "position_m must be finite",
        ),
        (
            lambda: WaterWaveSpec(
                gravitational_acceleration_m_s2=G,
                profile=(ProfilePoint(0.0, DEPTH, C), ProfilePoint(1.0, DEPTH, C)),
                target="KINEMATIC_HORIZON",  # type: ignore[arg-type]
                regime=WaveRegime.NONDISPERSIVE_SHALLOW_WATER,
                branch=WaveBranch.COUNTER_CURRENT,
                requested_orientation=HorizonOrientation.BLACK,
                flow_direction=FlowDirection.POSITIVE_X,
                assumptions=assumptions(),
            ),
            "target must be a WaveTarget value",
        ),
        (
            lambda: RegimeAssumptions(
                stationary="yes",  # type: ignore[arg-type]
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
            "stationary must be a bool",
        ),
        (
            lambda: WaterWaveSpec(
                profile=(ProfilePoint(1.0, DEPTH, C), ProfilePoint(0.0, DEPTH, C)),
                gravitational_acceleration_m_s2=G,
                target=WaveTarget.KINEMATIC_HORIZON,
                regime=WaveRegime.NONDISPERSIVE_SHALLOW_WATER,
                branch=WaveBranch.COUNTER_CURRENT,
                requested_orientation=HorizonOrientation.BLACK,
                flow_direction=FlowDirection.POSITIVE_X,
                assumptions=assumptions(),
            ),
            "positions must be strictly increasing",
        ),
        (
            lambda: request((0.5 * C, -0.5 * C)),
            "unidirectional",
        ),
    ],
)
def test_invalid_inputs_and_raw_strings_are_refused(factory, error):
    with pytest.raises((TypeError, ValueError), match=error):
        factory()


@pytest.mark.parametrize(
    "velocities, error",
    [
        ((0.5 * C, C, C, 1.5 * C), "zero plateau"),
        ((C, 0.5 * C), "profile boundary"),
        ((0.5 * C, C, 0.5 * C), "without a strict crossing"),
    ],
)
def test_critical_plateaus_boundary_zeros_and_touches_are_unclassifiable(velocities, error):
    with pytest.raises(ValueError, match=error):
        diagnose_horizon(request(velocities))


def test_unsupported_target_regime_and_missing_assumption_are_refused():
    with pytest.raises(ValueError, match="unsupported target"):
        diagnose_horizon(request((0.5 * C, 1.5 * C), target=WaveTarget.THERMAL_RELATION))
    with pytest.raises(ValueError, match="unsupported regime"):
        diagnose_horizon(
            request(
                (0.5 * C, 1.5 * C),
                regime=WaveRegime.DISPERSIVE_GRAVITY_CAPILLARY,
            )
        )
    with pytest.raises(ValueError, match="false: stationary"):
        diagnose_horizon(
            request((0.5 * C, 1.5 * C), declared_assumptions=assumptions(stationary=False))
        )
