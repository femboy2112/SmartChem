"""Direct verifier for the manufactured continuous-water payload.

This module intentionally does not import or call ``solve_continuous_background``.
It evaluates the retained equations, mesh inventory, high-precision manufactured
reference, critical regularity, and comparison payload through a separate code path.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
import math

from .contracts import EvidenceStatus
from .water_wave_continuous_domain import (
    CONTINUOUS_UNCERTAINTY_SEMANTICS,
    ContinuousBackgroundSpec,
    ContinuousDiagnostic,
    ContinuousMeshResult,
    ContinuousSample,
    ContinuousStatus,
    ManufacturedFamily,
)

__all__ = [
    "continuous_diagnostic_error",
    "continuous_payload_error",
]


def _cuberoot(value: Decimal) -> Decimal:
    if value <= 0:
        raise ValueError("cube-root input must be positive")
    guess = Decimal(str(float(value) ** (1.0 / 3.0)))
    for _ in range(80):
        updated = (Decimal(2) * guess + value / (guess * guess)) / Decimal(3)
        if updated == guess:
            break
        guess = updated
    return +guess


def _parameters(
    family: ManufacturedFamily,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if family is ManufacturedFamily.SUBCRITICAL:
        return (
            Decimal("1.45"),
            Decimal("0.08"),
            Decimal("0.04"),
            Decimal("0.5"),
        )
    if family is ManufacturedFamily.SUPERCRITICAL:
        return (
            Decimal("0.55"),
            Decimal("0.08"),
            Decimal("0.04"),
            Decimal("0.5"),
        )
    if family is ManufacturedFamily.REGULAR_TRANSCRITICAL:
        return (
            Decimal("1.0"),
            Decimal("0.35"),
            Decimal("0.04"),
            Decimal("0.43"),
        )
    raise TypeError("unsupported manufactured family")


def _critical_depth(spec: ContinuousBackgroundSpec) -> float:
    with localcontext() as context:
        context.prec = 60
        q = Decimal(str(spec.discharge_m3_s))
        g = Decimal(str(spec.gravitational_acceleration_m_s2))
        width = Decimal(str(spec.width_m))
        return float(_cuberoot(q * q / (g * width * width)))


def _reference_depth_fraction(
    spec: ContinuousBackgroundSpec,
    fraction: Decimal,
) -> float:
    with localcontext() as context:
        context.prec = 60
        q = Decimal(str(spec.discharge_m3_s))
        g = Decimal(str(spec.gravitational_acceleration_m_s2))
        width = Decimal(str(spec.width_m))
        hc = _cuberoot(q * q / (g * width * width))
        offset, linear, quadratic, critical = _parameters(spec.family)
        shifted = fraction - critical
        return float(
            hc * (offset + linear * shifted + quadratic * shifted * shifted)
        )


def _reference_depth_at_x(
    spec: ContinuousBackgroundSpec,
    x_m: float,
) -> float:
    with localcontext() as context:
        context.prec = 60
        fraction = Decimal(str(x_m)) / Decimal(str(spec.length_m))
        return _reference_depth_fraction(spec, fraction)


def _reference_depth_prime(
    spec: ContinuousBackgroundSpec,
    x_m: float,
) -> float:
    with localcontext() as context:
        context.prec = 60
        q = Decimal(str(spec.discharge_m3_s))
        g = Decimal(str(spec.gravitational_acceleration_m_s2))
        width = Decimal(str(spec.width_m))
        length = Decimal(str(spec.length_m))
        hc = _cuberoot(q * q / (g * width * width))
        _offset, linear, quadratic, critical = _parameters(spec.family)
        shifted = Decimal(str(x_m)) / length - critical
        return float(hc * (linear + Decimal(2) * quadratic * shifted) / length)


def _specific_energy(
    depth_m: float,
    spec: ContinuousBackgroundSpec,
) -> float:
    return (
        depth_m
        + spec.discharge_m3_s * spec.discharge_m3_s
        / (
            2.0
            * spec.gravitational_acceleration_m_s2
            * spec.width_m
            * spec.width_m
            * depth_m
            * depth_m
        )
    )


def _bed(
    x_m: float,
    spec: ContinuousBackgroundSpec,
) -> float:
    depth = _reference_depth_at_x(spec, x_m)
    upstream_depth = _reference_depth_fraction(spec, Decimal(0))
    return (
        -spec.friction.constant_slope * x_m
        - (_specific_energy(depth, spec) - _specific_energy(upstream_depth, spec))
    )


def _source(
    x_m: float,
    spec: ContinuousBackgroundSpec,
) -> float:
    depth = _reference_depth_at_x(spec, x_m)
    depth_prime = _reference_depth_prime(spec, x_m)
    froude_squared = (
        spec.discharge_m3_s * spec.discharge_m3_s
        / (
            spec.gravitational_acceleration_m_s2
            * spec.width_m
            * spec.width_m
            * depth
            * depth
            * depth
        )
    )
    balanced = (
        spec.friction.constant_slope
        + (1.0 - froude_squared) * depth_prime
    )
    if spec.family is ManufacturedFamily.REGULAR_TRANSCRITICAL:
        hc = _critical_depth(spec)
        _offset, linear, _quadratic, critical = _parameters(spec.family)
        critical_x = float(critical) * spec.length_m
        critical_prime = hc * float(linear) / spec.length_m
        required_derivative = (
            3.0 * critical_prime * critical_prime / hc
        )
        balanced += (
            (spec.source.critical_derivative_scale - 1.0)
            * (x_m - critical_x)
            * required_derivative
        )
    return spec.source.balance_sign * balanced


def _close(
    actual: float,
    expected: float,
    *,
    absolute: float = 2e-12,
    relative: float = 2e-12,
) -> bool:
    return math.isfinite(actual) and math.isclose(
        actual,
        expected,
        abs_tol=absolute,
        rel_tol=relative,
    )


def _order(coarse: float, fine: float) -> float | None:
    if coarse <= 0.0 or fine <= 0.0:
        return None
    return math.log(coarse / fine, 2.0)


def _mesh_error(
    spec: ContinuousBackgroundSpec,
    mesh: ContinuousMeshResult,
    cells: int,
) -> str | None:
    if type(mesh) is not ContinuousMeshResult:
        return "mesh is not an exact ContinuousMeshResult"
    if mesh.cells != cells:
        return f"mesh cell count differs: expected {cells}, got {mesh.cells}"
    array_names = (
        "x_m",
        "depth_m",
        "high_precision_reference_depth_m",
        "depth_error_m",
        "velocity_m_s",
        "discharge_m3_s",
        "bed_elevation_m",
        "head_m",
        "froude_number",
        "source_slope",
        "friction_slope",
        "continuity_residual",
        "momentum_residual",
        "root_iterations",
        "energy_root_residual_m",
        "critical_projection_applied",
        "samples",
    )
    for name in array_names:
        value = getattr(mesh, name)
        if type(value) is not tuple or len(value) != cells:
            return f"mesh {name} must retain exactly {cells} entries"

    dx = spec.length_m / cells
    hc = _critical_depth(spec)
    upstream_depth = _reference_depth_fraction(spec, Decimal(0))
    upstream_head = _specific_energy(upstream_depth, spec)
    expected_errors: list[float] = []
    expected_continuity: list[float] = []
    expected_momentum: list[float] = []
    expected_energy_residual: list[float] = []

    for index in range(cells):
        x_m = (index + 0.5) * dx
        if not _close(mesh.x_m[index], x_m, absolute=1e-14, relative=1e-14):
            return f"mesh x_m[{index}] differs from the declared cell centre"
        depth = mesh.depth_m[index]
        if not math.isfinite(depth) or depth <= 0.0:
            return f"mesh depth_m[{index}] is not positive and finite"
        reference = _reference_depth_fraction(
            spec,
            Decimal(2 * index + 1) / Decimal(2 * cells),
        )
        error = depth - reference
        if not _close(
            mesh.high_precision_reference_depth_m[index],
            reference,
            absolute=2e-14,
            relative=2e-14,
        ):
            return f"mesh high-precision reference depth {index} differs"
        if not _close(
            mesh.depth_error_m[index],
            error,
            absolute=2e-14,
            relative=2e-12,
        ):
            return f"mesh depth error {index} differs"
        expected_errors.append(error)

        velocity = spec.discharge_m3_s / (spec.width_m * depth)
        discharge = spec.width_m * depth * velocity
        froude = abs(velocity) / math.sqrt(
            spec.gravitational_acceleration_m_s2 * depth
        )
        bed = _bed(x_m, spec)
        head = bed + _specific_energy(depth, spec)
        source = _source(x_m, spec)
        friction = spec.friction.constant_slope
        continuity = discharge - spec.discharge_m3_s
        for name, actual, expected in (
            ("velocity", mesh.velocity_m_s[index], velocity),
            ("discharge", mesh.discharge_m3_s[index], discharge),
            ("Froude", mesh.froude_number[index], froude),
            ("bed", mesh.bed_elevation_m[index], bed),
            ("head", mesh.head_m[index], head),
            ("source", mesh.source_slope[index], source),
            ("friction", mesh.friction_slope[index], friction),
            ("continuity residual", mesh.continuity_residual[index], continuity),
        ):
            if not _close(actual, expected):
                return f"mesh {name} {index} differs from direct evaluation"
        expected_continuity.append(continuity)

        left = index * dx
        right = (index + 1) * dx
        target_head = upstream_head - spec.friction.constant_slope * x_m
        target_energy = (target_head - (_bed(left, spec) + _bed(right, spec)) / 2.0)
        energy_residual = abs(_specific_energy(depth, spec) - target_energy)
        expected_energy_residual.append(energy_residual)
        projected = target_energy <= _specific_energy(hc, spec)
        if mesh.critical_projection_applied[index] is not projected:
            return f"mesh critical projection flag {index} differs"
        expected_iterations = 0 if projected else 80
        if mesh.root_iterations[index] != expected_iterations:
            return f"mesh root iteration count {index} differs"
        if not _close(
            mesh.energy_root_residual_m[index],
            energy_residual,
            absolute=3e-12,
            relative=3e-10,
        ):
            return f"mesh energy-root residual {index} differs"
        subcritical_branch = (
            spec.family is ManufacturedFamily.SUBCRITICAL
            or (
                spec.family is ManufacturedFamily.REGULAR_TRANSCRITICAL
                and x_m > 0.43 * spec.length_m
            )
        )
        if subcritical_branch and depth < hc - 2e-12:
            return f"mesh depth {index} is on the wrong supercritical root"
        if not subcritical_branch and depth > hc + 2e-12:
            return f"mesh depth {index} is on the wrong subcritical root"

    derivatives: list[float] = []
    for index in range(cells):
        if index == 0:
            derivatives.append((mesh.depth_m[1] - mesh.depth_m[0]) / dx)
        elif index == cells - 1:
            derivatives.append((mesh.depth_m[-1] - mesh.depth_m[-2]) / dx)
        else:
            derivatives.append(
                (mesh.depth_m[index + 1] - mesh.depth_m[index - 1])
                / (2.0 * dx)
            )
    for index, derivative in enumerate(derivatives):
        expected = (
            (1.0 - mesh.froude_number[index] ** 2) * derivative
            - (
                mesh.source_slope[index]
                - mesh.friction_slope[index]
            )
        )
        expected_momentum.append(expected)
        if not _close(mesh.momentum_residual[index], expected):
            return f"mesh momentum residual {index} differs"

    for index, sample in enumerate(mesh.samples):
        if type(sample) is not ContinuousSample:
            return f"mesh sample {index} is not an exact ContinuousSample"
        expected_sample = ContinuousSample(
            x_m=mesh.x_m[index],
            depth_m=mesh.depth_m[index],
            high_precision_reference_depth_m=(
                mesh.high_precision_reference_depth_m[index]
            ),
            depth_error_m=mesh.depth_error_m[index],
            velocity_m_s=mesh.velocity_m_s[index],
            discharge_m3_s=mesh.discharge_m3_s[index],
            bed_elevation_m=mesh.bed_elevation_m[index],
            total_head_m=mesh.head_m[index],
            froude_number=mesh.froude_number[index],
            source_slope=mesh.source_slope[index],
            friction_slope=mesh.friction_slope[index],
            continuity_residual_m3_s=mesh.continuity_residual[index],
            momentum_residual=mesh.momentum_residual[index],
            root_iterations=mesh.root_iterations[index],
            energy_root_residual_m=mesh.energy_root_residual_m[index],
            critical_projection_applied=mesh.critical_projection_applied[index],
        )
        if sample != expected_sample:
            return f"mesh sample {index} differs from retained arrays"

    l2_depth = math.sqrt(
        sum(value * value for value in expected_errors) / cells
    )
    l2_momentum = math.sqrt(
        sum(value * value for value in expected_momentum) / cells
    )
    aggregates = (
        (
            "maximum continuity residual",
            mesh.max_continuity_residual,
            max(map(abs, expected_continuity)),
        ),
        (
            "maximum momentum residual",
            mesh.max_momentum_residual,
            max(map(abs, expected_momentum)),
        ),
        (
            "maximum energy-root residual",
            mesh.max_energy_root_residual_m,
            max(expected_energy_residual),
        ),
        ("depth L2 error", mesh.l2_depth_error, l2_depth),
        ("momentum residual L2", mesh.momentum_residual_l2, l2_momentum),
    )
    for name, actual, expected in aggregates:
        if not _close(actual, expected):
            return f"mesh {name} differs from direct aggregation"

    numerator, derivative = _critical_residuals(spec)
    if not _close(
        mesh.critical_compatibility_residual,
        numerator,
        absolute=3e-12,
        relative=3e-10,
    ):
        return "mesh critical numerator compatibility residual differs"
    if not _close(
        mesh.critical_derivative_compatibility_residual,
        derivative,
        absolute=3e-10,
        relative=3e-8,
    ):
        return "mesh critical derivative compatibility residual differs"
    return None


def _critical_residuals(
    spec: ContinuousBackgroundSpec,
) -> tuple[float, float]:
    if spec.family is not ManufacturedFamily.REGULAR_TRANSCRITICAL:
        return (0.0, 0.0)
    hc = _critical_depth(spec)
    _offset, linear, _quadratic, _critical = _parameters(spec.family)
    critical_prime = hc * float(linear) / spec.length_m
    required = 3.0 * critical_prime * critical_prime / hc
    if spec.source.balance_sign == 1:
        return (
            0.0,
            (spec.source.critical_derivative_scale - 1.0) * required,
        )
    return (
        -2.0 * spec.friction.constant_slope,
        -(spec.source.critical_derivative_scale + 1.0) * required,
    )


def _boundary_matches(spec: ContinuousBackgroundSpec) -> bool:
    upstream_depth = _reference_depth_fraction(spec, Decimal(0))
    downstream_depth = _reference_depth_fraction(spec, Decimal(1))
    upstream_head = _specific_energy(upstream_depth, spec)
    downstream_head = (
        upstream_head - spec.friction.constant_slope * spec.length_m
    )
    return all(
        _close(actual, expected, absolute=2e-12, relative=2e-12)
        for actual, expected in (
            (spec.upstream_boundary.depth_m, upstream_depth),
            (spec.downstream_boundary.depth_m, downstream_depth),
            (spec.upstream_boundary.total_head_m, upstream_head),
            (spec.downstream_boundary.total_head_m, downstream_head),
        )
    )


def continuous_diagnostic_error(
    spec: ContinuousBackgroundSpec,
    diagnostic: object,
) -> str | None:
    """Return a precise error, or ``None`` when direct verification succeeds."""
    if type(spec) is not ContinuousBackgroundSpec:
        return "approved subject has no exact ContinuousBackgroundSpec"
    if type(diagnostic) is not ContinuousDiagnostic:
        return "diagnostic is not an exact ContinuousDiagnostic"
    if diagnostic.spec != spec:
        return "diagnostic spec differs from the approved subject"
    if diagnostic.evidence_status is not EvidenceStatus.STRUCTURAL_TOY:
        return "diagnostic evidence status was promoted"
    if diagnostic.uncertainty_propagated is not False:
        return "manufactured metadata-only uncertainty was reported as propagated"
    if diagnostic.uncertainty_semantics != CONTINUOUS_UNCERTAINTY_SEMANTICS:
        return "diagnostic uncertainty semantics differ from the closed contract"
    if type(diagnostic.meshes) is not tuple or len(diagnostic.meshes) != 3:
        return "diagnostic must retain exactly three meshes"

    cells = (spec.base_cells, 2 * spec.base_cells, 4 * spec.base_cells)
    for mesh, expected_cells in zip(diagnostic.meshes, cells):
        error = _mesh_error(spec, mesh, expected_cells)
        if error is not None:
            return error

    depth_orders = (
        _order(
            diagnostic.meshes[0].l2_depth_error,
            diagnostic.meshes[1].l2_depth_error,
        ),
        _order(
            diagnostic.meshes[1].l2_depth_error,
            diagnostic.meshes[2].l2_depth_error,
        ),
    )
    residual_orders = (
        _order(
            diagnostic.meshes[0].momentum_residual_l2,
            diagnostic.meshes[1].momentum_residual_l2,
        ),
        _order(
            diagnostic.meshes[1].momentum_residual_l2,
            diagnostic.meshes[2].momentum_residual_l2,
        ),
    )
    for index, mesh in enumerate(diagnostic.meshes):
        expected = None if index == 0 else depth_orders[index - 1]
        if mesh.observed_order != expected:
            return f"mesh observed order {index} differs"
    finite_depth = tuple(value for value in depth_orders if value is not None)
    finite_residual = tuple(
        value for value in residual_orders if value is not None
    )
    expected_spatial = min(finite_depth) if finite_depth else None
    expected_residual = min(finite_residual) if finite_residual else None
    if diagnostic.spatial_convergence_order != expected_spatial:
        return "diagnostic spatial convergence order differs"
    if diagnostic.residual_convergence_order != expected_residual:
        return "diagnostic residual convergence order differs"

    critical_x = (
        0.43 * spec.length_m
        if spec.family is ManufacturedFamily.REGULAR_TRANSCRITICAL
        else None
    )
    if diagnostic.critical_location_m != critical_x:
        return "diagnostic critical location differs"
    numerator, derivative = _critical_residuals(spec)
    regularity = (
        critical_x is None
        or (
            spec.regularity.require_isolated_critical_compatibility
            and abs(numerator) <= spec.regularity.compatibility_tolerance
            and abs(derivative)
            <= spec.regularity.derivative_compatibility_tolerance
        )
    )
    if diagnostic.regularity_satisfied is not regularity:
        return "diagnostic regularity verdict differs"

    if spec.source.balance_sign != 1:
        expected_status = ContinuousStatus.SOURCE_SIGN_INVALID
    elif not _boundary_matches(spec):
        expected_status = ContinuousStatus.BOUNDARY_MISMATCH
    elif not regularity:
        expected_status = ContinuousStatus.REGULARITY_REFUSED
    elif any(
        value is None or value < 0.8
        for value in (*depth_orders, *residual_orders)
    ) or any(
        mesh.max_continuity_residual > 1e-12
        or mesh.max_energy_root_residual_m > 1e-10
        or mesh.max_momentum_residual > 1e-3
        for mesh in diagnostic.meshes
    ):
        expected_status = ContinuousStatus.CONVERGENCE_NOT_OBSERVED
    else:
        expected_status = ContinuousStatus.CONVERGED_MANUFACTURED
    if diagnostic.status is not expected_status:
        return (
            "diagnostic status differs from direct equation, regularity, and "
            "convergence evaluation"
        )
    return None


def continuous_payload_error(
    subject: object,
    diagnostic: object,
    meshes: object,
    comparison: object,
) -> str | None:
    """Directly validate all three observable payloads without the production solver."""
    from .water_wave_continuous import (
        ContinuousFiniteV2Comparison,
        ContinuousWaterSubject,
    )
    from .water_wave_validation_domain import diagnose_water_wave_background

    if type(subject) is not ContinuousWaterSubject:
        return "continuous-water plan has no exact ContinuousWaterSubject"
    error = continuous_diagnostic_error(subject.background, diagnostic)
    if error is not None:
        return error
    assert type(diagnostic) is ContinuousDiagnostic
    if type(meshes) is not tuple or meshes != diagnostic.meshes:
        return "continuous-water mesh inventory differs from the verified diagnostic"
    if type(comparison) is not ContinuousFiniteV2Comparison:
        return "finite-v2 comparison is not an exact ContinuousFiniteV2Comparison"

    finest_by_x = {
        sample.x_m: sample for sample in diagnostic.meshes[-1].samples
    }
    for sample in subject.finite_v2.samples:
        retained = finest_by_x.get(sample.x_m)
        if retained is None:
            return "finite-v2 sample is not a retained finest-mesh point"
        if (
            sample.width_m != subject.background.width_m
            or sample.depth_m != retained.depth_m
            or sample.velocity_m_s != retained.velocity_m_s
            or sample.bed_elevation_m != retained.bed_elevation_m
        ):
            return "finite-v2 sample differs from the retained continuous point"

    finite = diagnose_water_wave_background(subject.finite_v2)
    if comparison.continuous_status != diagnostic.status.value:
        return "comparison continuous status differs"
    if comparison.finite_v2_status != finite.status.value:
        return "comparison finite-v2 status differs"
    if comparison.finite_v2_diagnostic != finite:
        return "comparison finite-v2 diagnostic differs from direct evaluation"
    heads = tuple(item.bernoulli_head_m for item in finite.samples)
    observed_range = max(heads) - min(heads)
    first_x = finite.samples[0].sample.x_m
    last_x = finite.samples[-1].sample.x_m
    friction_drop = (
        subject.background.friction.constant_slope * (last_x - first_x)
    )
    expected_heads = tuple(
        subject.background.upstream_boundary.total_head_m
        - subject.background.friction.constant_slope * item.sample.x_m
        for item in finite.samples
    )
    reconstruction_offset = max(
        abs(observed - expected)
        for observed, expected in zip(heads, expected_heads)
    )
    head_scale = max(
        abs(heads[0]),
        subject.finite_v2.tolerances.head_reference_scale_m,
    )
    tolerance = subject.finite_v2.tolerances.head_relative * head_scale
    friction_dominated = (
        not finite.head_gate_passed
        and friction_drop > 10.0 * max(reconstruction_offset, tolerance)
    )
    if friction_dominated:
        expected_relation = (
            "FRICTION_DOMINATED_CONTINUOUS_PASS_LOSSLESS_FINITE_V2_HEAD_MISMATCH"
        )
        expected_explanation = (
            "Finite v2 applies a lossless constant-head gate, while the continuous "
            "model declares frictional head loss. The declared friction head drop "
            "exceeds both the retained reconstruction offset and the v2 head tolerance "
            "by more than 10x, so friction dominates this specific disagreement. "
            "Neither diagnostic is promoted to physical truth."
        )
    elif finite.head_gate_passed:
        expected_relation = (
            "FINITE_V2_HEAD_GATE_AGREES_WITHIN_DECLARED_TOLERANCE"
        )
        expected_explanation = (
            "The independent finite-v2 lossless head gate passes at its declared "
            "tolerance. This numerical agreement does not validate either model."
        )
    else:
        expected_relation = "FINITE_V2_HEAD_MISMATCH_CAUSE_NOT_ISOLATED"
        expected_explanation = (
            "The independent finite-v2 head gate fails, but declared friction does "
            "not dominate the retained reconstruction offset and v2 tolerance by "
            "10x. The mismatch cause is therefore not isolated and no friction-only "
            "explanation is licensed."
        )
    for name, actual, expected in (
        (
            "observed head range",
            comparison.observed_head_range_m,
            observed_range,
        ),
        (
            "declared friction head drop",
            comparison.declared_friction_head_drop_m,
            friction_drop,
        ),
        (
            "maximum reconstruction head offset",
            comparison.max_reconstruction_head_offset_m,
            reconstruction_offset,
        ),
    ):
        if not _close(actual, expected):
            return f"comparison {name} differs"
    if comparison.comparison != expected_relation:
        return "comparison relation differs from direct attribution gate"
    if comparison.explanation != expected_explanation:
        return "comparison explanation differs from direct attribution gate"
    return None
