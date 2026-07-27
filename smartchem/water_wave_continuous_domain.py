"""Manufactured continuous steady shallow-water backgrounds.

This is a deliberately narrow numerical *reconstruction* rung.  It provides
constant-width, one-dimensional, manufactured steady backgrounds and retains
three meshes so that spatial convergence is an observed finite fact.  It is
not a general Saint-Venant solver, measured-flume model, or scattering solver.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from numbers import Real

from .contracts import EvidenceStatus

_MAX_ROOT_BRACKET_EXPANSIONS = 64

__all__ = [
    "ContinuousBackgroundSpec", "ContinuousDiagnostic", "ContinuousMeshResult",
    "ContinuousSample", "ContinuousStatus", "ContinuousUncertainty",
    "FrictionLaw", "ManufacturedFamily", "RegularityRequirement", "SourceLaw",
    "SteadyBoundary", "solve_continuous_background",
]


class ManufacturedFamily(str, Enum):
    SUBCRITICAL = "SUBCRITICAL"
    SUPERCRITICAL = "SUPERCRITICAL"
    REGULAR_TRANSCRITICAL = "REGULAR_TRANSCRITICAL"


class ContinuousStatus(str, Enum):
    CONVERGED_MANUFACTURED = "CONVERGED_MANUFACTURED"
    SOURCE_SIGN_INVALID = "SOURCE_SIGN_INVALID"
    REGULARITY_REFUSED = "REGULARITY_REFUSED"
    BOUNDARY_MISMATCH = "BOUNDARY_MISMATCH"
    CONVERGENCE_NOT_OBSERVED = "CONVERGENCE_NOT_OBSERVED"


def _real(name: str, value: object, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise TypeError(f"{name} must be a finite real number")
    result = float(value)
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and result < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _require_manufactured_provenance(name: str, value: object) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty")
    normalized = value.casefold()
    forbidden = ("measur", "observ", "laboratory", "field survey", "calibrat")
    if "manufactured" not in normalized or any(
        token in normalized for token in forbidden
    ):
        raise ValueError(
            f"{name} must be manufactured-only and must not imply measurement or calibration"
        )


@dataclass(frozen=True)
class ContinuousUncertainty:
    """Absolute retained uncertainty bounds; no uncertainty is silently discarded."""

    depth_m: float = 0.0
    discharge_m3_s: float = 0.0
    slope: float = 0.0

    def __post_init__(self) -> None:
        for name in ("depth_m", "discharge_m3_s", "slope"):
            object.__setattr__(self, name, _real(name, getattr(self, name), nonnegative=True))


@dataclass(frozen=True)
class FrictionLaw:
    """A mandatory, positive, manufactured friction slope ``S_f``."""

    constant_slope: float
    provenance: str = "manufactured constant friction slope"

    def __post_init__(self) -> None:
        object.__setattr__(self, "constant_slope", _real("constant_slope", self.constant_slope, positive=True))
        _require_manufactured_provenance("friction provenance", self.provenance)


@dataclass(frozen=True)
class SourceLaw:
    """Manufactured ``S0`` with the declared equation convention ``S0 - Sf``.

    ``balance_sign=-1`` is allowed only to make sign-mutation diagnostics
    falsifiable; it is never a valid manufactured balance.
    """

    balance_sign: int = 1
    provenance: str = "manufactured source slope derived from exact profile"

    def __post_init__(self) -> None:
        if self.balance_sign not in (-1, 1):
            raise ValueError("balance_sign must be +1 or -1")
        _require_manufactured_provenance("source provenance", self.provenance)


@dataclass(frozen=True)
class RegularityRequirement:
    require_isolated_critical_compatibility: bool = True
    compatibility_tolerance: float = 1e-12

    def __post_init__(self) -> None:
        if type(self.require_isolated_critical_compatibility) is not bool:
            raise TypeError("require_isolated_critical_compatibility must be a bool")
        object.__setattr__(self, "compatibility_tolerance", _real(
            "compatibility_tolerance", self.compatibility_tolerance, nonnegative=True
        ))


@dataclass(frozen=True)
class SteadyBoundary:
    position_m: float
    depth_m: float
    total_head_m: float
    boundary_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "position_m", _real("position_m", self.position_m))
        object.__setattr__(self, "depth_m", _real("depth_m", self.depth_m, positive=True))
        object.__setattr__(self, "total_head_m", _real("total_head_m", self.total_head_m))
        if not isinstance(self.boundary_id, str) or not self.boundary_id:
            raise ValueError("boundary_id must be non-empty")


@dataclass(frozen=True)
class ContinuousBackgroundSpec:
    """A fully typed manufactured background, including both boundary values."""

    family: ManufacturedFamily
    length_m: float
    width_m: float
    discharge_m3_s: float
    gravitational_acceleration_m_s2: float
    upstream_boundary: SteadyBoundary
    downstream_boundary: SteadyBoundary
    friction: FrictionLaw
    source: SourceLaw
    uncertainty: ContinuousUncertainty
    regularity: RegularityRequirement
    base_cells: int = 32
    evidence_status: EvidenceStatus = EvidenceStatus.STRUCTURAL_TOY
    provenance: str = "manufactured continuous steady shallow-water background"

    def __post_init__(self) -> None:
        if type(self.family) is not ManufacturedFamily:
            raise TypeError("family must be an exact ManufacturedFamily")
        for name in ("length_m", "width_m", "discharge_m3_s", "gravitational_acceleration_m_s2"):
            object.__setattr__(self, name, _real(name, getattr(self, name), positive=True))
        for name, cls in (("upstream_boundary", SteadyBoundary), ("downstream_boundary", SteadyBoundary),
                          ("friction", FrictionLaw), ("source", SourceLaw),
                          ("uncertainty", ContinuousUncertainty), ("regularity", RegularityRequirement)):
            if type(getattr(self, name)) is not cls:
                raise TypeError(f"{name} must be an exact {cls.__name__}")
        if type(self.base_cells) is not int or self.base_cells < 8:
            raise ValueError("base_cells must be an integer of at least 8")
        if self.evidence_status is not EvidenceStatus.STRUCTURAL_TOY:
            raise ValueError("continuous manufactured backgrounds remain STRUCTURAL_TOY")
        _require_manufactured_provenance(
            "continuous background provenance",
            self.provenance,
        )
        if self.upstream_boundary.position_m != 0.0 or self.downstream_boundary.position_m != self.length_m:
            raise ValueError("boundaries must be fixed at x=0 and x=length_m")

    @classmethod
    def manufactured(
        cls, family: ManufacturedFamily, *, length_m: float = 10.0, width_m: float = 2.0,
        discharge_m3_s: float = 2.0, gravitational_acceleration_m_s2: float = 9.81,
        friction_slope: float = 0.01, uncertainty: ContinuousUncertainty | None = None,
        regularity: RegularityRequirement | None = None, base_cells: int = 32,
    ) -> "ContinuousBackgroundSpec":
        """Build one of the exact manufactured families with consistent boundaries."""
        # Construct provisionally to reuse the single exact-profile implementation below.
        hc = (discharge_m3_s ** 2 / (gravitational_acceleration_m_s2 * width_m ** 2)) ** (1.0 / 3.0)
        params = _family_parameters(family)
        h0 = _exact_depth(0.0, length_m, hc, params)
        hL = _exact_depth(length_m, length_m, hc, params)
        e0 = _specific_energy(h0, discharge_m3_s, width_m, gravitational_acceleration_m_s2)
        hL_total = e0 - friction_slope * length_m
        return cls(
            family, length_m, width_m, discharge_m3_s, gravitational_acceleration_m_s2,
            SteadyBoundary(0.0, h0, e0, "upstream"),
            SteadyBoundary(length_m, hL, hL_total, "downstream"),
            FrictionLaw(friction_slope), SourceLaw(), uncertainty or ContinuousUncertainty(),
            regularity or RegularityRequirement(), base_cells,
        )


@dataclass(frozen=True)
class ContinuousSample:
    x_m: float
    depth_m: float
    velocity_m_s: float
    discharge_m3_s: float
    bed_elevation_m: float
    total_head_m: float
    froude_number: float
    source_slope: float
    friction_slope: float
    continuity_residual_m3_s: float
    momentum_residual: float
    root_iterations: int
    energy_root_residual_m: float
    critical_projection_applied: bool


@dataclass(frozen=True)
class ContinuousMeshResult:
    cells: int
    x_m: tuple[float, ...]
    depth_m: tuple[float, ...]
    velocity_m_s: tuple[float, ...]
    discharge_m3_s: tuple[float, ...]
    bed_elevation_m: tuple[float, ...]
    head_m: tuple[float, ...]
    froude_number: tuple[float, ...]
    source_slope: tuple[float, ...]
    friction_slope: tuple[float, ...]
    continuity_residual: tuple[float, ...]
    momentum_residual: tuple[float, ...]
    root_iterations: tuple[int, ...]
    energy_root_residual_m: tuple[float, ...]
    critical_projection_applied: tuple[bool, ...]
    critical_compatibility_residual: float
    max_continuity_residual: float
    max_momentum_residual: float
    max_energy_root_residual_m: float
    l2_depth_error: float
    momentum_residual_l2: float
    observed_order: float | None
    samples: tuple[ContinuousSample, ...]


@dataclass(frozen=True)
class ContinuousDiagnostic:
    spec: ContinuousBackgroundSpec
    meshes: tuple[ContinuousMeshResult, ...]
    status: ContinuousStatus
    evidence_status: EvidenceStatus
    spatial_convergence_order: float | None
    residual_convergence_order: float | None
    critical_location_m: float | None
    regularity_satisfied: bool


def _family_parameters(family: ManufacturedFamily) -> tuple[float, float, float]:
    # h/hc = offset + a*s + b*s^2, s=x/L-critical_fraction.
    if family is ManufacturedFamily.SUBCRITICAL:
        return (1.45, 0.08, 0.04)
    if family is ManufacturedFamily.SUPERCRITICAL:
        return (0.55, 0.08, 0.04)
    return (1.0, 0.35, 0.04)


def _critical_fraction(family: ManufacturedFamily) -> float:
    return 0.43 if family is ManufacturedFamily.REGULAR_TRANSCRITICAL else 0.5


def _exact_depth(x: float, length: float, hc: float, params: tuple[float, float, float]) -> float:
    offset, a, b = params
    s = x / length - 0.43 if offset == 1.0 else x / length - 0.5
    return hc * (offset + a * s + b * s * s)


def _exact_depth_prime(x: float, length: float, hc: float, params: tuple[float, float, float]) -> float:
    offset, a, b = params
    s = x / length - 0.43 if offset == 1.0 else x / length - 0.5
    return hc * (a + 2.0 * b * s) / length


def _root_reconstruct_depth(left: float, right: float, spec: ContinuousBackgroundSpec, hc: float,
                            params: tuple[float, float, float]) -> tuple[float, int, float, bool]:
    """Solve one bounded branch-aware finite-volume energy root by bisection.

    The cell stores the trapezoidal bed reconstruction, not the exact point bed.
    Consequently this is a real second-order spatial reconstruction rather than a
    copy of the manufactured depth.  The declared family/regime selects the
    subcritical or supercritical root when the energy equation has two roots.
    """
    midpoint = (left + right) / 2.0
    h0 = _exact_depth(0.0, spec.length_m, hc, params)
    total_head = _specific_energy(h0, spec.discharge_m3_s, spec.width_m, spec.gravitational_acceleration_m_s2) - spec.friction.constant_slope * midpoint
    bed = (_bed_elevation(left, spec, hc, params) + _bed_elevation(right, spec, hc, params)) / 2.0
    target_energy = total_head - bed
    minimum_energy = _specific_energy(hc, spec.discharge_m3_s, spec.width_m, spec.gravitational_acceleration_m_s2)
    # At the isolated critical cell, a second-order bed reconstruction can sit a
    # few ulps below the exact minimum.  The conservative projection records that
    # limiting critical root instead of inventing an unphysical branch.
    if target_energy <= minimum_energy:
        return (
            hc,
            0,
            abs(minimum_energy - target_energy),
            True,
        )
    subcritical_branch = (
        spec.family is ManufacturedFamily.SUBCRITICAL
        or (
            spec.family is ManufacturedFamily.REGULAR_TRANSCRITICAL
            and midpoint > _critical_fraction(spec.family) * spec.length_m
        )
    )
    if not subcritical_branch:
        lo, hi = hc * 1e-9, hc
    else:
        lo, hi = hc, 2.0 * hc
        for _ in range(_MAX_ROOT_BRACKET_EXPANSIONS):
            if (
                _specific_energy(
                    hi,
                    spec.discharge_m3_s,
                    spec.width_m,
                    spec.gravitational_acceleration_m_s2,
                )
                >= target_energy
            ):
                break
            hi *= 2.0
        else:
            if (
                _specific_energy(
                    hi,
                    spec.discharge_m3_s,
                    spec.width_m,
                    spec.gravitational_acceleration_m_s2,
                )
                < target_energy
            ):
                raise ValueError(
                    "subcritical energy root was not bracketed within "
                    f"{_MAX_ROOT_BRACKET_EXPANSIONS} expansions"
                )
    for _ in range(80):
        mid = (lo + hi) / 2.0
        value = _specific_energy(mid, spec.discharge_m3_s, spec.width_m, spec.gravitational_acceleration_m_s2)
        if not subcritical_branch:  # energy decreases toward the critical depth
            if value > target_energy:
                lo = mid
            else:
                hi = mid
        elif value < target_energy:
            lo = mid
        else:
            hi = mid
    root = (lo + hi) / 2.0
    return (
        root,
        80,
        abs(
            _specific_energy(
                root,
                spec.discharge_m3_s,
                spec.width_m,
                spec.gravitational_acceleration_m_s2,
            )
            - target_energy
        ),
        False,
    )


def _specific_energy(h: float, q: float, width: float, gravity: float) -> float:
    return h + q * q / (2.0 * gravity * width * width * h * h)


def _bed_elevation(x: float, spec: ContinuousBackgroundSpec, hc: float,
                   params: tuple[float, float, float]) -> float:
    h = _exact_depth(x, spec.length_m, hc, params)
    h0 = _exact_depth(0.0, spec.length_m, hc, params)
    return -spec.friction.constant_slope * x - (_specific_energy(h, spec.discharge_m3_s, spec.width_m, spec.gravitational_acceleration_m_s2) - _specific_energy(h0, spec.discharge_m3_s, spec.width_m, spec.gravitational_acceleration_m_s2))


def _source_slope(x: float, spec: ContinuousBackgroundSpec, hc: float,
                  params: tuple[float, float, float]) -> float:
    h = _exact_depth(x, spec.length_m, hc, params)
    fr2 = spec.discharge_m3_s ** 2 / (spec.gravitational_acceleration_m_s2 * spec.width_m ** 2 * h ** 3)
    balanced = spec.friction.constant_slope + (1.0 - fr2) * _exact_depth_prime(x, spec.length_m, hc, params)
    return spec.source.balance_sign * balanced


def _boundary_matches(spec: ContinuousBackgroundSpec, hc: float, params: tuple[float, float, float]) -> bool:
    h0 = _exact_depth(0.0, spec.length_m, hc, params)
    hL = _exact_depth(spec.length_m, spec.length_m, hc, params)
    H0 = _specific_energy(h0, spec.discharge_m3_s, spec.width_m, spec.gravitational_acceleration_m_s2)
    HL = H0 - spec.friction.constant_slope * spec.length_m
    tolerance = max(spec.uncertainty.depth_m, 1e-12)
    return (abs(spec.upstream_boundary.depth_m - h0) <= tolerance and abs(spec.downstream_boundary.depth_m - hL) <= tolerance
            and abs(spec.upstream_boundary.total_head_m - H0) <= tolerance and abs(spec.downstream_boundary.total_head_m - HL) <= tolerance)


def _mesh(spec: ContinuousBackgroundSpec, cells: int, hc: float, params: tuple[float, float, float]) -> ContinuousMeshResult:
    dx = spec.length_m / cells
    x = tuple((i + 0.5) * dx for i in range(cells))
    roots = tuple(
        _root_reconstruct_depth(i * dx, (i + 1) * dx, spec, hc, params)
        for i in range(cells)
    )
    h = tuple(item[0] for item in roots)
    root_iterations = tuple(item[1] for item in roots)
    energy_root_residual = tuple(item[2] for item in roots)
    critical_projection = tuple(item[3] for item in roots)
    u = tuple(spec.discharge_m3_s / (spec.width_m * value) for value in h)
    q = tuple(spec.width_m * depth * velocity for depth, velocity in zip(h, u))
    froude = tuple(abs(velocity) / math.sqrt(spec.gravitational_acceleration_m_s2 * depth) for depth, velocity in zip(h, u))
    source = tuple(_source_slope(value, spec, hc, params) for value in x)
    friction = tuple(spec.friction.constant_slope for _ in x)
    bed = tuple(_bed_elevation(value, spec, hc, params) for value in x)
    head = tuple(z + _specific_energy(depth, spec.discharge_m3_s, spec.width_m, spec.gravitational_acceleration_m_s2) for z, depth in zip(bed, h))
    continuity = tuple(value - spec.discharge_m3_s for value in q)
    derivative: list[float] = []
    for index in range(cells):
        if index == 0:
            derivative.append((h[1] - h[0]) / dx)
        elif index == cells - 1:
            derivative.append((h[-1] - h[-2]) / dx)
        else:
            derivative.append((h[index + 1] - h[index - 1]) / (2.0 * dx))
    momentum = tuple((1.0 - fr * fr) * dh - (s0 - sf) for fr, dh, s0, sf in zip(froude, derivative, source, friction))
    exact = tuple(_exact_depth(value, spec.length_m, hc, params) for value in x)
    l2_error = math.sqrt(sum((a - b) ** 2 for a, b in zip(h, exact)) / cells)
    mom_l2 = math.sqrt(sum(value * value for value in momentum) / cells)
    critical_x = _critical_fraction(spec.family) * spec.length_m if spec.family is ManufacturedFamily.REGULAR_TRANSCRITICAL else None
    compatibility = 0.0 if critical_x is None else _source_slope(critical_x, spec, hc, params) - spec.friction.constant_slope
    samples = tuple(
        ContinuousSample(
            a,
            b,
            c,
            d,
            e,
            f,
            g,
            h1,
            i,
            j,
            k,
            iterations,
            root_residual,
            projected,
        )
        for (
            a,
            b,
            c,
            d,
            e,
            f,
            g,
            h1,
            i,
            j,
            k,
            iterations,
            root_residual,
            projected,
        ) in zip(
            x,
            h,
            u,
            q,
            bed,
            head,
            froude,
            source,
            friction,
            continuity,
            momentum,
            root_iterations,
            energy_root_residual,
            critical_projection,
        )
    )
    return ContinuousMeshResult(
        cells,
        x,
        h,
        u,
        q,
        bed,
        head,
        froude,
        source,
        friction,
        continuity,
        momentum,
        root_iterations,
        energy_root_residual,
        critical_projection,
        compatibility,
        max(map(abs, continuity)),
        max(map(abs, momentum)),
        max(energy_root_residual),
        l2_error,
        mom_l2,
        None,
        samples,
    )


def _order(coarse: float, fine: float) -> float | None:
    if coarse <= 0.0 or fine <= 0.0:
        return None
    return math.log(coarse / fine, 2.0)


def solve_continuous_background(spec: ContinuousBackgroundSpec) -> ContinuousDiagnostic:
    """Return three retained finite-volume reconstructions, never a continuum proof."""
    if type(spec) is not ContinuousBackgroundSpec:
        raise TypeError("spec must be an exact ContinuousBackgroundSpec")
    hc = (spec.discharge_m3_s ** 2 / (spec.gravitational_acceleration_m_s2 * spec.width_m ** 2)) ** (1.0 / 3.0)
    params = _family_parameters(spec.family)
    raw = tuple(_mesh(spec, cells, hc, params) for cells in (spec.base_cells, 2 * spec.base_cells, 4 * spec.base_cells))
    depth_orders = (_order(raw[0].l2_depth_error, raw[1].l2_depth_error), _order(raw[1].l2_depth_error, raw[2].l2_depth_error))
    residual_orders = (_order(raw[0].momentum_residual_l2, raw[1].momentum_residual_l2), _order(raw[1].momentum_residual_l2, raw[2].momentum_residual_l2))
    meshes = tuple(replace(mesh, observed_order=(None if index == 0 else depth_orders[index - 1])) for index, mesh in enumerate(raw))
    critical_x = _critical_fraction(spec.family) * spec.length_m if spec.family is ManufacturedFamily.REGULAR_TRANSCRITICAL else None
    compatibility = raw[-1].critical_compatibility_residual
    regularity = (critical_x is None or (spec.regularity.require_isolated_critical_compatibility and abs(compatibility) <= spec.regularity.compatibility_tolerance))
    if spec.source.balance_sign != 1:
        status = ContinuousStatus.SOURCE_SIGN_INVALID
    elif not _boundary_matches(spec, hc, params):
        status = ContinuousStatus.BOUNDARY_MISMATCH
    elif not regularity:
        status = ContinuousStatus.REGULARITY_REFUSED
    elif any(
        order is None or order < 0.8
        for order in (*depth_orders, *residual_orders)
    ):
        status = ContinuousStatus.CONVERGENCE_NOT_OBSERVED
    else:
        status = ContinuousStatus.CONVERGED_MANUFACTURED
    finite_depth_orders = tuple(
        order for order in depth_orders if order is not None
    )
    finite_residual_orders = tuple(
        order for order in residual_orders if order is not None
    )
    return ContinuousDiagnostic(
        spec,
        meshes,
        status,
        EvidenceStatus.STRUCTURAL_TOY,
        min(finite_depth_orders) if finite_depth_orders else None,
        min(finite_residual_orders) if finite_residual_orders else None,
        critical_x,
        regularity,
    )
