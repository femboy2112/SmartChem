"""Pure, prescribed-background shallow-water horizon diagnostics.

This module deliberately implements only a narrow kinematic analogue calculation.  Given
one-dimensional, stationary, inviscid, irrotational, gravity-only shallow-water samples, it
checks a selected linear characteristic for critical crossings.  It does not evolve a water
surface, calculate scattering or spectra, model dispersion, or make thermal, quantum,
laser, backreaction, or astrophysical claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real

__all__ = [
    "WaveBranch",
    "CharacteristicSample",
    "FlowDirection",
    "HorizonDiagnostic",
    "HorizonOrientation",
    "HorizonPoint",
    "HorizonStatus",
    "ProfilePoint",
    "RegimeAssumptions",
    "WaveRegime",
    "WaveTarget",
    "WaterWaveSpec",
    "diagnose_horizon",
]


class WaveTarget(str, Enum):
    """Requested analogue observable; only kinematic horizons are implemented here."""

    KINEMATIC_HORIZON = "KINEMATIC_HORIZON"
    SCATTERING_COEFFICIENTS = "SCATTERING_COEFFICIENTS"
    THERMAL_RELATION = "THERMAL_RELATION"
    QUANTUM_RADIATION = "QUANTUM_RADIATION"
    BLACK_HOLE_LASER = "BLACK_HOLE_LASER"
    BACKREACTION = "BACKREACTION"


class WaveRegime(str, Enum):
    """Regimes named explicitly so unsupported physics cannot look silently included."""

    NONDISPERSIVE_SHALLOW_WATER = "NONDISPERSIVE_SHALLOW_WATER"
    DISPERSIVE_GRAVITY_CAPILLARY = "DISPERSIVE_GRAVITY_CAPILLARY"
    VISCOUS = "VISCOUS"
    NONLINEAR = "NONLINEAR"
    TURBULENT = "TURBULENT"


class WaveBranch(str, Enum):
    """The selected lab-frame characteristic relative to the declared bulk flow."""

    COUNTER_CURRENT = "COUNTER_CURRENT"
    CO_CURRENT = "CO_CURRENT"


class HorizonOrientation(str, Enum):
    """Requested kinematic orientation, interpreted along the direction of flow."""

    BLACK = "BLACK"
    WHITE = "WHITE"
    PAIR = "PAIR"


class FlowDirection(str, Enum):
    """The one permitted sign of the prescribed normal velocity field."""

    POSITIVE_X = "POSITIVE_X"
    NEGATIVE_X = "NEGATIVE_X"


class HorizonStatus(str, Enum):
    """Sample-bracketing result; unsampled continuous behavior remains unknown."""

    KINEMATIC_CROSSING_BRACKETED_IN_SUPPLIED_SAMPLES = (
        "KINEMATIC_CROSSING_BRACKETED_IN_SUPPLIED_SAMPLES"
    )
    NO_BRACKET_IN_SUPPLIED_SAMPLES = "NO_BRACKET_IN_SUPPLIED_SAMPLES"
    ORIENTATION_MISMATCH = "ORIENTATION_MISMATCH"


@dataclass(frozen=True)
class ProfilePoint:
    """One SI sample of the prescribed background at position ``x``."""

    position_m: float
    depth_m: float
    normal_velocity_m_s: float

    def __post_init__(self) -> None:
        for name, value in (
            ("position_m", self.position_m),
            ("depth_m", self.depth_m),
            ("normal_velocity_m_s", self.normal_velocity_m_s),
        ):
            _require_finite_real(name, value)
        if self.depth_m <= 0.0:
            raise ValueError("depth_m must be positive")


@dataclass(frozen=True)
class RegimeAssumptions:
    """Explicit assumptions required by this prescribed-background diagnostic."""

    stationary: bool
    inviscid: bool
    irrotational: bool
    gravity_only: bool
    shallow_water: bool
    linear_perturbations: bool
    one_dimensional: bool
    prescribed_background: bool
    no_retained_wave_forcing: bool
    negligible_reflections: bool

    def __post_init__(self) -> None:
        for name in (
            "stationary",
            "inviscid",
            "irrotational",
            "gravity_only",
            "shallow_water",
            "linear_perturbations",
            "one_dimensional",
            "prescribed_background",
            "no_retained_wave_forcing",
            "negligible_reflections",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a bool")

    def require_supported(self) -> None:
        """Refuse an input whose declared assumptions do not match this model."""
        missing = tuple(
            name
            for name in (
                "stationary",
                "inviscid",
                "irrotational",
                "gravity_only",
                "shallow_water",
                "linear_perturbations",
                "one_dimensional",
                "prescribed_background",
                "no_retained_wave_forcing",
                "negligible_reflections",
            )
            if not getattr(self, name)
        )
        if missing:
            raise ValueError(
                "this diagnostic requires all declared shallow-water assumptions; "
                f"false: {', '.join(missing)}"
            )


@dataclass(frozen=True)
class WaterWaveSpec:
    """Full immutable prescribed-background diagnostic specification, in SI units."""

    profile: tuple[ProfilePoint, ...]
    gravitational_acceleration_m_s2: float
    target: WaveTarget
    regime: WaveRegime
    branch: WaveBranch
    requested_orientation: HorizonOrientation
    flow_direction: FlowDirection
    assumptions: RegimeAssumptions

    def __post_init__(self) -> None:
        _require_finite_real(
            "gravitational_acceleration_m_s2", self.gravitational_acceleration_m_s2
        )
        if self.gravitational_acceleration_m_s2 <= 0.0:
            raise ValueError("gravitational_acceleration_m_s2 must be positive")
        _require_enum("target", self.target, WaveTarget)
        _require_enum("regime", self.regime, WaveRegime)
        _require_enum("branch", self.branch, WaveBranch)
        _require_enum("requested_orientation", self.requested_orientation, HorizonOrientation)
        _require_enum("flow_direction", self.flow_direction, FlowDirection)
        if not isinstance(self.assumptions, RegimeAssumptions):
            raise TypeError("assumptions must be a RegimeAssumptions value")
        if not isinstance(self.profile, tuple):
            raise TypeError("profile must be an immutable tuple of ProfilePoint values")
        if len(self.profile) < 2:
            raise ValueError("profile must contain at least two points")
        if not all(isinstance(point, ProfilePoint) for point in self.profile):
            raise TypeError("profile must contain only ProfilePoint values")
        previous_x = self.profile[0].position_m
        for point in self.profile[1:]:
            if point.position_m <= previous_x:
                raise ValueError("profile positions must be strictly increasing")
            previous_x = point.position_m
        expected_sign = _flow_sign(self.flow_direction)
        if any(expected_sign * point.normal_velocity_m_s <= 0.0 for point in self.profile):
            raise ValueError(
                "profile normal velocities must be nonzero and unidirectional in the "
                "declared flow direction"
            )


@dataclass(frozen=True)
class CharacteristicSample:
    """Every input point augmented with the evaluated selected characteristic."""

    position_m: float
    depth_m: float
    normal_velocity_m_s: float
    gravity_wave_speed_m_s: float
    selected_characteristic_m_s: float
    froude_number: float


@dataclass(frozen=True)
class HorizonPoint:
    """One isolated selected-characteristic crossing, linearly located between samples."""

    position_m: float
    orientation: HorizonOrientation
    left_sample_index: int
    right_sample_index: int

    def __post_init__(self) -> None:
        _require_finite_real("position_m", self.position_m)
        _require_enum("orientation", self.orientation, HorizonOrientation)
        if self.orientation is HorizonOrientation.PAIR:
            raise ValueError("an individual horizon point must be BLACK or WHITE")
        if type(self.left_sample_index) is not int or type(self.right_sample_index) is not int:
            raise TypeError("horizon sample indices must be integers")
        if self.left_sample_index < 0 or self.right_sample_index <= self.left_sample_index:
            raise ValueError("horizon sample indices must delimit an increasing interval")


@dataclass(frozen=True)
class HorizonDiagnostic:
    """Complete deterministic record, including every input and evaluated sample."""

    spec: WaterWaveSpec
    samples: tuple[CharacteristicSample, ...]
    horizons: tuple[HorizonPoint, ...]
    status: HorizonStatus


def diagnose_horizon(spec: WaterWaveSpec) -> HorizonDiagnostic:
    """
    Diagnose isolated crossings of the selected shallow-water characteristic.

    ``COUNTER_CURRENT`` uses ``U - sign(U) sqrt(g h)``.  ``CO_CURRENT`` uses
    ``U + sign(U) sqrt(g h)``.  Individual horizons are BLACK when, travelling
    downstream, the selected characteristic changes from negative to positive;
    the reverse transition is WHITE. A boundary zero, a zero plateau, or a zero that merely
    touches rather than crosses is refused as unclassifiable. Absence of a bracket does not
    establish absence of a crossing between samples.
    """
    if not isinstance(spec, WaterWaveSpec):
        raise TypeError("spec must be a WaterWaveSpec value")
    if spec.target is not WaveTarget.KINEMATIC_HORIZON:
        raise ValueError(f"unsupported target for this diagnostic: {spec.target.value}")
    if spec.regime is not WaveRegime.NONDISPERSIVE_SHALLOW_WATER:
        raise ValueError(f"unsupported regime for this diagnostic: {spec.regime.value}")
    spec.assumptions.require_supported()

    flow_sign = _flow_sign(spec.flow_direction)
    samples = tuple(
        _sample(point, spec.gravitational_acceleration_m_s2, spec.branch, flow_sign)
        for point in spec.profile
    )
    horizons = _find_horizons(samples, flow_sign)
    if not horizons:
        status = HorizonStatus.NO_BRACKET_IN_SUPPLIED_SAMPLES
    elif _orientation_matches(spec.requested_orientation, horizons):
        status = HorizonStatus.KINEMATIC_CROSSING_BRACKETED_IN_SUPPLIED_SAMPLES
    else:
        status = HorizonStatus.ORIENTATION_MISMATCH
    return HorizonDiagnostic(spec=spec, samples=samples, horizons=horizons, status=status)


def _sample(
    point: ProfilePoint,
    gravitational_acceleration_m_s2: float,
    branch: WaveBranch,
    flow_sign: int,
) -> CharacteristicSample:
    wave_speed = math.sqrt(gravitational_acceleration_m_s2 * point.depth_m)
    if branch is WaveBranch.COUNTER_CURRENT:
        characteristic = point.normal_velocity_m_s - flow_sign * wave_speed
    else:
        characteristic = point.normal_velocity_m_s + flow_sign * wave_speed
    return CharacteristicSample(
        position_m=point.position_m,
        depth_m=point.depth_m,
        normal_velocity_m_s=point.normal_velocity_m_s,
        gravity_wave_speed_m_s=wave_speed,
        selected_characteristic_m_s=characteristic,
        froude_number=abs(point.normal_velocity_m_s) / wave_speed,
    )


def _find_horizons(
    samples: tuple[CharacteristicSample, ...], flow_sign: int
) -> tuple[HorizonPoint, ...]:
    characteristic = tuple(sample.selected_characteristic_m_s for sample in samples)
    if characteristic[0] == 0.0 or characteristic[-1] == 0.0:
        raise ValueError("critical characteristic zero on a profile boundary is unclassifiable")

    exact_zero_indices = tuple(index for index, value in enumerate(characteristic) if value == 0.0)
    zero_set = set(exact_zero_indices)
    for index in exact_zero_indices:
        if index - 1 in zero_set or index + 1 in zero_set:
            raise ValueError("critical characteristic zero plateau is unclassifiable")
        if characteristic[index - 1] * characteristic[index + 1] >= 0.0:
            raise ValueError("critical characteristic zero without a strict crossing is unclassifiable")

    horizons: list[HorizonPoint] = []
    for index in exact_zero_indices:
        horizons.append(
            _horizon_point(
                samples,
                left_index=index - 1,
                right_index=index + 1,
                position_m=samples[index].position_m,
                flow_sign=flow_sign,
            )
        )
    for left_index, (left, right) in enumerate(zip(samples, samples[1:])):
        if left_index in zero_set or left_index + 1 in zero_set:
            continue
        left_value = left.selected_characteristic_m_s
        right_value = right.selected_characteristic_m_s
        if left_value * right_value < 0.0:
            fraction = -left_value / (right_value - left_value)
            position = left.position_m + fraction * (right.position_m - left.position_m)
            horizons.append(
                _horizon_point(
                    samples,
                    left_index=left_index,
                    right_index=left_index + 1,
                    position_m=position,
                    flow_sign=flow_sign,
                )
            )
    return tuple(sorted(horizons, key=lambda horizon: horizon.position_m))


def _horizon_point(
    samples: tuple[CharacteristicSample, ...],
    *,
    left_index: int,
    right_index: int,
    position_m: float,
    flow_sign: int,
) -> HorizonPoint:
    left_value = flow_sign * samples[left_index].selected_characteristic_m_s
    right_value = flow_sign * samples[right_index].selected_characteristic_m_s
    downstream_before, downstream_after = (
        (left_value, right_value) if flow_sign > 0 else (right_value, left_value)
    )
    if downstream_before < 0.0 < downstream_after:
        orientation = HorizonOrientation.BLACK
    elif downstream_before > 0.0 > downstream_after:
        orientation = HorizonOrientation.WHITE
    else:  # guarded by _find_horizons; keep the classifier fail-closed.
        raise ValueError("selected characteristic crossing could not be oriented")
    return HorizonPoint(
        position_m=position_m,
        orientation=orientation,
        left_sample_index=left_index,
        right_sample_index=right_index,
    )


def _orientation_matches(
    requested: HorizonOrientation, horizons: tuple[HorizonPoint, ...]
) -> bool:
    found = {horizon.orientation for horizon in horizons}
    if requested is HorizonOrientation.PAIR:
        return HorizonOrientation.BLACK in found and HorizonOrientation.WHITE in found
    return requested in found


def _flow_sign(direction: FlowDirection) -> int:
    _require_enum("flow_direction", direction, FlowDirection)
    return 1 if direction is FlowDirection.POSITIVE_X else -1


def _require_finite_real(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_enum(name: str, value: object, enum_type: type[Enum]) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{name} must be a {enum_type.__name__} value")
