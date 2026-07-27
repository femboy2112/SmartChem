"""Typed preflight for a manufactured finite-section water-wave background.

This is deliberately a *background-consistency* diagnostic.  It evaluates a
finite set of supplied samples under the one-dimensional shallow-water
approximation; it neither turns those samples into measurements nor extends a
sample-level result to the unsampled continuum. In particular, the strongest
compatibility result is not a stationary-solution or experimental
validation claim, and ``NO_BRACKET_AT_SAMPLES`` is not evidence that no crossing
exists between or beyond the supplied samples.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real

from .contracts import canonical_digest
from .water_wave_domain import (
    FlowDirection,
    HorizonOrientation,
    WaveBranch,
)

__all__ = [
    "BackgroundSample",
    "BackgroundTolerances",
    "CharacteristicInterval",
    "CrossingBracket",
    "DeclaredWavelengthSupport",
    "FluidProperties",
    "SampleDiagnostic",
    "ValidationDiagnostic",
    "ValidationStatus",
    "WaterWaveValidationSpec",
    "diagnose_water_wave_background",
]


class _Digestible:
    @property
    def digest(self) -> str:
        return canonical_digest(self)


class ValidationStatus(str, Enum):
    """Finite-sample compatibility, regime, uncertainty, and orientation outcomes."""

    FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET = (
        "FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET"
    )
    FINITE_SAMPLE_BALANCE_INCOMPATIBLE = "FINITE_SAMPLE_BALANCE_INCOMPATIBLE"
    REGIME_UNSUPPORTED = "REGIME_UNSUPPORTED"
    NO_BRACKET_AT_SAMPLES = "NO_BRACKET_AT_SAMPLES"
    UNCERTAINTY_AMBIGUOUS_SAMPLE_BRACKET = (
        "UNCERTAINTY_AMBIGUOUS_SAMPLE_BRACKET"
    )
    POSITION_ORDER_AMBIGUOUS = "POSITION_ORDER_AMBIGUOUS"
    ORIENTATION_MISMATCH = "ORIENTATION_MISMATCH"


@dataclass(frozen=True)
class BackgroundSample(_Digestible):
    """One SI background sample and nonnegative absolute input uncertainties."""

    x_m: float
    width_m: float
    depth_m: float
    velocity_m_s: float
    bed_elevation_m: float
    x_uncertainty_m: float
    width_uncertainty_m: float
    depth_uncertainty_m: float
    velocity_uncertainty_m_s: float
    bed_elevation_uncertainty_m: float

    def __post_init__(self) -> None:
        for name in (
            "x_m",
            "width_m",
            "depth_m",
            "velocity_m_s",
            "bed_elevation_m",
        ):
            _require_finite_real(name, getattr(self, name))
        for name in (
            "x_uncertainty_m",
            "width_uncertainty_m",
            "depth_uncertainty_m",
            "velocity_uncertainty_m_s",
            "bed_elevation_uncertainty_m",
        ):
            _require_nonnegative_finite(name, getattr(self, name))
        if self.width_m <= 0.0:
            raise ValueError("width_m must be positive")
        if self.depth_m <= 0.0:
            raise ValueError("depth_m must be positive")
        if self.depth_uncertainty_m >= self.depth_m:
            raise ValueError("depth_uncertainty_m must leave a positive depth interval")
        if self.velocity_m_s == 0.0:
            raise ValueError("velocity_m_s must be nonzero")
        if self.velocity_uncertainty_m_s >= abs(self.velocity_m_s):
            raise ValueError(
                "velocity_uncertainty_m_s must preserve the declared flow direction"
            )
        if self.width_uncertainty_m >= self.width_m:
            raise ValueError("width_uncertainty_m must leave a positive width interval")
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, float(getattr(self, name)))


@dataclass(frozen=True)
class FluidProperties(_Digestible):
    density_kg_m3: float
    surface_tension_n_m: float
    gravitational_acceleration_m_s2: float
    provenance: str

    def __post_init__(self) -> None:
        for name in (
            "density_kg_m3",
            "surface_tension_n_m",
            "gravitational_acceleration_m_s2",
        ):
            _require_positive_finite(name, getattr(self, name))
            object.__setattr__(self, name, float(getattr(self, name)))
        _require_text("provenance", self.provenance)


@dataclass(frozen=True)
class DeclaredWavelengthSupport(_Digestible):
    """The exact wavelength band that the shallow gravity-wave claim covers."""

    minimum_wavelength_m: float
    maximum_wavelength_m: float
    shallow_water_max_kh: float
    minimum_bond_number: float
    provenance: str

    def __post_init__(self) -> None:
        for name in (
            "minimum_wavelength_m",
            "maximum_wavelength_m",
            "shallow_water_max_kh",
            "minimum_bond_number",
        ):
            _require_positive_finite(name, getattr(self, name))
            object.__setattr__(self, name, float(getattr(self, name)))
        if self.minimum_wavelength_m > self.maximum_wavelength_m:
            raise ValueError("minimum_wavelength_m must not exceed maximum_wavelength_m")
        _require_text("provenance", self.provenance)


@dataclass(frozen=True)
class BackgroundTolerances(_Digestible):
    """Dimensionless residual gates with an explicit head scale and provenance."""

    continuity_relative: float
    head_relative: float
    head_reference_scale_m: float
    provenance: str

    def __post_init__(self) -> None:
        _require_nonnegative_finite("continuity_relative", self.continuity_relative)
        _require_nonnegative_finite("head_relative", self.head_relative)
        _require_positive_finite("head_reference_scale_m", self.head_reference_scale_m)
        _require_text("provenance", self.provenance)
        object.__setattr__(self, "continuity_relative", float(self.continuity_relative))
        object.__setattr__(self, "head_relative", float(self.head_relative))
        object.__setattr__(self, "head_reference_scale_m", float(self.head_reference_scale_m))


@dataclass(frozen=True)
class WaterWaveValidationSpec(_Digestible):
    """Immutable input for a finite-sample shallow-water preflight."""

    samples: tuple[BackgroundSample, ...]
    fluid: FluidProperties
    wavelength_support: DeclaredWavelengthSupport
    tolerances: BackgroundTolerances
    branch: WaveBranch
    requested_orientation: HorizonOrientation
    flow_direction: FlowDirection

    def __post_init__(self) -> None:
        if type(self.samples) is not tuple or len(self.samples) < 2:
            raise TypeError("samples must be a tuple of at least two BackgroundSample values")
        if any(type(sample) is not BackgroundSample for sample in self.samples):
            raise TypeError("samples must contain exact BackgroundSample values")
        if type(self.fluid) is not FluidProperties:
            raise TypeError("fluid must be an exact FluidProperties value")
        if type(self.wavelength_support) is not DeclaredWavelengthSupport:
            raise TypeError("wavelength_support must be an exact DeclaredWavelengthSupport value")
        if type(self.tolerances) is not BackgroundTolerances:
            raise TypeError("tolerances must be an exact BackgroundTolerances value")
        if type(self.branch) is not WaveBranch:
            raise TypeError("branch must be an exact WaveBranch value")
        if self.branch is not WaveBranch.COUNTER_CURRENT:
            raise ValueError("this finite preflight supports only COUNTER_CURRENT")
        if type(self.requested_orientation) is not HorizonOrientation:
            raise TypeError(
                "requested_orientation must be an exact HorizonOrientation value"
            )
        if type(self.flow_direction) is not FlowDirection:
            raise TypeError("flow_direction must be an exact FlowDirection value")
        previous_x = self.samples[0].x_m
        velocity_sign = (
            1.0 if self.flow_direction is FlowDirection.POSITIVE_X else -1.0
        )
        if math.copysign(1.0, self.samples[0].velocity_m_s) != velocity_sign:
            raise ValueError(
                "sample velocities must follow the declared flow direction"
            )
        for sample in self.samples[1:]:
            if sample.x_m <= previous_x:
                raise ValueError("sample x_m positions must be strictly increasing")
            if math.copysign(1.0, sample.velocity_m_s) != velocity_sign:
                raise ValueError("sample velocities must be unidirectional")
            previous_x = sample.x_m


@dataclass(frozen=True)
class CharacteristicInterval(_Digestible):
    lower_m_s: float
    upper_m_s: float

    def __post_init__(self) -> None:
        _require_finite_real("lower_m_s", self.lower_m_s)
        _require_finite_real("upper_m_s", self.upper_m_s)
        if self.lower_m_s > self.upper_m_s:
            raise ValueError("characteristic interval lower bound must not exceed upper bound")
        object.__setattr__(self, "lower_m_s", float(self.lower_m_s))
        object.__setattr__(self, "upper_m_s", float(self.upper_m_s))


@dataclass(frozen=True)
class SampleDiagnostic(_Digestible):
    """Every retained input sample plus its derived local quantities."""

    sample: BackgroundSample
    discharge_m3_s: float
    bernoulli_head_m: float
    normalized_continuity_residual: float
    normalized_head_residual: float
    kh_at_shortest_wavelength: float
    bond_number: float
    characteristic_m_s: float
    characteristic_interval: CharacteristicInterval


@dataclass(frozen=True)
class CrossingBracket(_Digestible):
    """A finite-sample sign bracket, never a continuum or measured location claim."""

    left_sample_index: int
    right_sample_index: int
    linear_interpolation_position_m: float
    conservative_position_interval_m: tuple[float, float]
    orientation: HorizonOrientation
    uncertainty_resolved: bool
    position_order_resolved: bool

    def __post_init__(self) -> None:
        if type(self.left_sample_index) is not int or type(self.right_sample_index) is not int:
            raise TypeError("crossing indices must be integers")
        if self.left_sample_index < 0 or self.right_sample_index != self.left_sample_index + 1:
            raise ValueError("crossing indices must name adjacent increasing samples")
        _require_finite_real("linear_interpolation_position_m", self.linear_interpolation_position_m)
        if type(self.conservative_position_interval_m) is not tuple or len(self.conservative_position_interval_m) != 2:
            raise TypeError("conservative_position_interval_m must be a two-item tuple")
        lower, upper = self.conservative_position_interval_m
        _require_finite_real("conservative position lower bound", lower)
        _require_finite_real("conservative position upper bound", upper)
        if lower > upper:
            raise ValueError("conservative position interval must be ordered")
        if not lower <= self.linear_interpolation_position_m <= upper:
            raise ValueError("linear crossing position must lie inside conservative interval")
        if type(self.orientation) is not HorizonOrientation:
            raise TypeError("orientation must be an exact HorizonOrientation value")
        if self.orientation is HorizonOrientation.PAIR:
            raise ValueError("an individual crossing bracket cannot have PAIR orientation")
        if type(self.uncertainty_resolved) is not bool:
            raise TypeError("uncertainty_resolved must be a bool")
        if type(self.position_order_resolved) is not bool:
            raise TypeError("position_order_resolved must be a bool")
        object.__setattr__(self, "linear_interpolation_position_m", float(self.linear_interpolation_position_m))
        object.__setattr__(self, "conservative_position_interval_m", (float(lower), float(upper)))


@dataclass(frozen=True)
class ValidationDiagnostic(_Digestible):
    """Full receipt for the finite diagnostic, including all samples and gates."""

    spec: WaterWaveValidationSpec
    samples: tuple[SampleDiagnostic, ...]
    crossings: tuple[CrossingBracket, ...]
    status: ValidationStatus
    continuity_gate_passed: bool
    head_gate_passed: bool
    shallow_water_gate_passed: bool
    gravity_capillarity_gate_passed: bool
    uncertainty_resolved_bracket_gate_passed: bool
    position_order_resolved_gate_passed: bool
    orientation_gate_passed: bool


def diagnose_water_wave_background(spec: WaterWaveValidationSpec) -> ValidationDiagnostic:
    """Evaluate nominal finite-sample compatibility without a continuum claim."""
    if type(spec) is not WaterWaveValidationSpec:
        raise TypeError("spec must be an exact WaterWaveValidationSpec value")
    reference_discharge = _discharge(spec.samples[0])
    reference_head = _head(spec.samples[0], spec.fluid.gravitational_acceleration_m_s2)
    head_scale = max(abs(reference_head), spec.tolerances.head_reference_scale_m)
    sample_diagnostics = tuple(
        _diagnose_sample(sample, spec, reference_discharge, reference_head, head_scale)
        for sample in spec.samples
    )
    continuity_passed = all(
        sample.normalized_continuity_residual <= spec.tolerances.continuity_relative
        for sample in sample_diagnostics
    )
    head_passed = all(
        sample.normalized_head_residual <= spec.tolerances.head_relative
        for sample in sample_diagnostics
    )
    shallow_passed = all(
        sample.kh_at_shortest_wavelength <= spec.wavelength_support.shallow_water_max_kh
        for sample in sample_diagnostics
    )
    gravity_capillarity_passed = all(
        sample.bond_number >= spec.wavelength_support.minimum_bond_number
        for sample in sample_diagnostics
    )
    flow_sign = 1 if spec.flow_direction is FlowDirection.POSITIVE_X else -1
    crossings = _find_sample_brackets(sample_diagnostics, flow_sign)
    uncertainty_resolved = bool(crossings) and all(
        crossing.uncertainty_resolved for crossing in crossings
    )
    position_order_resolved = bool(crossings) and all(
        crossing.position_order_resolved for crossing in crossings
    )
    found_orientations = {crossing.orientation for crossing in crossings}
    if spec.requested_orientation is HorizonOrientation.PAIR:
        orientation_passed = (
            HorizonOrientation.BLACK in found_orientations
            and HorizonOrientation.WHITE in found_orientations
        )
    else:
        orientation_passed = spec.requested_orientation in found_orientations
    if not continuity_passed or not head_passed:
        status = ValidationStatus.FINITE_SAMPLE_BALANCE_INCOMPATIBLE
    elif not shallow_passed or not gravity_capillarity_passed:
        status = ValidationStatus.REGIME_UNSUPPORTED
    elif not crossings:
        status = ValidationStatus.NO_BRACKET_AT_SAMPLES
    elif not position_order_resolved:
        status = ValidationStatus.POSITION_ORDER_AMBIGUOUS
    elif not orientation_passed:
        status = ValidationStatus.ORIENTATION_MISMATCH
    elif not uncertainty_resolved:
        status = ValidationStatus.UNCERTAINTY_AMBIGUOUS_SAMPLE_BRACKET
    else:
        status = (
            ValidationStatus
            .FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET
        )
    return ValidationDiagnostic(
        spec=spec,
        samples=sample_diagnostics,
        crossings=crossings,
        status=status,
        continuity_gate_passed=continuity_passed,
        head_gate_passed=head_passed,
        shallow_water_gate_passed=shallow_passed,
        gravity_capillarity_gate_passed=gravity_capillarity_passed,
        uncertainty_resolved_bracket_gate_passed=uncertainty_resolved,
        position_order_resolved_gate_passed=position_order_resolved,
        orientation_gate_passed=orientation_passed,
    )


def _diagnose_sample(
    sample: BackgroundSample,
    spec: WaterWaveValidationSpec,
    reference_discharge: float,
    reference_head: float,
    head_scale: float,
) -> SampleDiagnostic:
    fluid = spec.fluid
    discharge = _discharge(sample)
    head = _head(sample, fluid.gravitational_acceleration_m_s2)
    flow_sign = 1.0 if sample.velocity_m_s > 0.0 else -1.0
    characteristic = sample.velocity_m_s - flow_sign * math.sqrt(
        fluid.gravitational_acceleration_m_s2 * sample.depth_m
    )
    interval = _characteristic_interval(sample, fluid.gravitational_acceleration_m_s2)
    wave_number = 2.0 * math.pi / spec.wavelength_support.minimum_wavelength_m
    return SampleDiagnostic(
        sample=sample,
        discharge_m3_s=discharge,
        bernoulli_head_m=head,
        normalized_continuity_residual=abs(discharge - reference_discharge) / abs(reference_discharge),
        normalized_head_residual=abs(head - reference_head) / head_scale,
        kh_at_shortest_wavelength=wave_number * sample.depth_m,
        bond_number=(
            fluid.density_kg_m3
            * fluid.gravitational_acceleration_m_s2
            * sample.depth_m**2
            / fluid.surface_tension_n_m
        ),
        characteristic_m_s=characteristic,
        characteristic_interval=interval,
    )


def _find_sample_brackets(
    samples: tuple[SampleDiagnostic, ...],
    flow_sign: int,
) -> tuple[CrossingBracket, ...]:
    brackets: list[CrossingBracket] = []
    for index, (left, right) in enumerate(zip(samples, samples[1:])):
        left_characteristic = left.characteristic_m_s
        right_characteristic = right.characteristic_m_s
        if left_characteristic * right_characteristic >= 0.0:
            continue
        fraction = -left_characteristic / (right_characteristic - left_characteristic)
        left_x = left.sample.x_m
        right_x = right.sample.x_m
        signed_left = flow_sign * left_characteristic
        signed_right = flow_sign * right_characteristic
        downstream_before, downstream_after = (
            (signed_left, signed_right)
            if flow_sign > 0
            else (signed_right, signed_left)
        )
        if downstream_before < 0.0 < downstream_after:
            orientation = HorizonOrientation.BLACK
        elif downstream_before > 0.0 > downstream_after:
            orientation = HorizonOrientation.WHITE
        else:  # guarded by the nominal sign change.
            raise ValueError("sample bracket could not be oriented")
        interval_resolved = (
            left.characteristic_interval.upper_m_s < 0.0
            and right.characteristic_interval.lower_m_s > 0.0
        ) or (
            left.characteristic_interval.lower_m_s > 0.0
            and right.characteristic_interval.upper_m_s < 0.0
        )
        position_order_resolved = (
            left_x + left.sample.x_uncertainty_m
            < right_x - right.sample.x_uncertainty_m
        )
        brackets.append(
            CrossingBracket(
                left_sample_index=index,
                right_sample_index=index + 1,
                linear_interpolation_position_m=left_x + fraction * (right_x - left_x),
                # Without a model for the unsampled profile, the whole adjacent interval is
                # the only defensible positional uncertainty bound.
                conservative_position_interval_m=(
                    left_x - left.sample.x_uncertainty_m,
                    right_x + right.sample.x_uncertainty_m,
                ),
                orientation=orientation,
                uncertainty_resolved=interval_resolved,
                position_order_resolved=position_order_resolved,
            )
        )
    return tuple(brackets)


def _discharge(sample: BackgroundSample) -> float:
    return sample.width_m * sample.depth_m * sample.velocity_m_s


def _head(sample: BackgroundSample, gravitational_acceleration_m_s2: float) -> float:
    return (
        sample.bed_elevation_m
        + sample.depth_m
        + sample.velocity_m_s**2 / (2.0 * gravitational_acceleration_m_s2)
    )


def _characteristic_interval(
    sample: BackgroundSample, gravitational_acceleration_m_s2: float
) -> CharacteristicInterval:
    minimum_depth = sample.depth_m - sample.depth_uncertainty_m
    maximum_depth = sample.depth_m + sample.depth_uncertainty_m
    if sample.velocity_m_s < 0.0:
        return CharacteristicInterval(
            lower_m_s=(
                sample.velocity_m_s
                - sample.velocity_uncertainty_m_s
                + math.sqrt(gravitational_acceleration_m_s2 * minimum_depth)
            ),
            upper_m_s=(
                sample.velocity_m_s
                + sample.velocity_uncertainty_m_s
                + math.sqrt(gravitational_acceleration_m_s2 * maximum_depth)
            ),
        )
    return CharacteristicInterval(
        lower_m_s=(
            sample.velocity_m_s
            - sample.velocity_uncertainty_m_s
            - math.sqrt(gravitational_acceleration_m_s2 * maximum_depth)
        ),
        upper_m_s=(
            sample.velocity_m_s
            + sample.velocity_uncertainty_m_s
            - math.sqrt(gravitational_acceleration_m_s2 * minimum_depth)
        ),
    )


def _require_finite_real(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_positive_finite(name: str, value: object) -> None:
    _require_finite_real(name, value)
    if value <= 0.0:  # type: ignore[operator]
        raise ValueError(f"{name} must be positive")


def _require_nonnegative_finite(name: str, value: object) -> None:
    _require_finite_real(name, value)
    if value < 0.0:  # type: ignore[operator]
        raise ValueError(f"{name} must be nonnegative")


def _require_text(name: str, value: object) -> None:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must be non-empty")
