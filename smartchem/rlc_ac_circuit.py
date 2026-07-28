"""Finite positive-frequency passive RLC phasor interpreter.

This is deliberately a bounded fixed-frequency control, not a transient, device, or
general transfer-function simulator.  Exact Q(i) algebra guards relation construction
and MNA rank; complex128 is only the retained numerical witness.
"""

from __future__ import annotations

from fractions import Fraction
from math import isfinite
from typing import Sequence
import warnings

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from .open_diagram import BoundaryRef, BoundarySide, OpenDiagram
from .rlc_ac_schema import (
    ACCircuitDiagnostics,
    ACSolveResult,
    ACSolveSpec,
    ACSourceObservation,
    ComplexBoundaryRelation,
    ElementKind,
    GaussianComplex,
    MNAState,
    NodePhasor,
    Phasor,
    PositiveAngularFrequency,
    RLCBranch,
    RLCComponent,
    RLCModel,
)

__all__ = [
    "ACCircuitError",
    "ACFloatingCircuitError",
    "ACNumericalRefusal",
    "ACResidualError",
    "ConditioningRefusal",
    "LosslessSingularResonanceError",
    "admittance_exact",
    "blackbox_rlc_ac",
    "solve_rlc_ac",
]


class ACCircuitError(ValueError):
    pass


class ACFloatingCircuitError(ACCircuitError):
    pass


class ACNumericalRefusal(ACCircuitError):
    pass


class ACResidualError(ACNumericalRefusal):
    pass


class ConditioningRefusal(ACNumericalRefusal):
    pass


class LosslessSingularResonanceError(ACNumericalRefusal):
    pass


def _edges(diagram: OpenDiagram) -> tuple[object, ...]:
    if type(diagram) is not OpenDiagram:
        raise TypeError("diagram must be exact OpenDiagram")
    result = diagram.structural_edges()
    if type(result) is not tuple:
        raise TypeError("structural edges must be an exact tuple")
    return result


def _nodes(diagram: OpenDiagram) -> int:
    return len(diagram.node_kinds)


def _edge_nodes(edge: object) -> tuple[int, int]:
    a, b = edge.node_a, edge.node_b
    if type(a) is not int or type(b) is not int:
        raise TypeError("edge nodes must be exact ints")
    return a, b


def _refs(diagram: OpenDiagram) -> tuple[BoundaryRef, ...]:
    return tuple(
        BoundaryRef(BoundarySide.INPUT, i) for i in range(len(diagram.dom.ports))
    ) + tuple(
        BoundaryRef(BoundarySide.OUTPUT, i) for i in range(len(diagram.cod.ports))
    )


def _resolve(diagram: OpenDiagram, ref: BoundaryRef) -> int:
    if type(ref) is not BoundaryRef:
        raise TypeError("boundary reference must be exact")
    node = diagram.node_for(ref)
    if type(node) is not int or not 0 <= node < _nodes(diagram):
        raise TypeError("invalid canonical boundary node")
    return node


def admittance_exact(
    component: RLCComponent, omega: PositiveAngularFrequency
) -> GaussianComplex:
    """Return the exact RMS phasor admittance at positive angular frequency."""
    if (
        type(component) is not RLCComponent
        or type(omega) is not PositiveAngularFrequency
    ):
        raise TypeError("component and omega must be exact nominal records")
    w = omega.fraction
    if component.kind is ElementKind.RESISTOR:
        return GaussianComplex.from_parts(1 / component.value.ohms.fraction)
    if component.kind is ElementKind.INDUCTOR:
        return GaussianComplex.from_parts(
            0, -1 / (w * component.value.henries.fraction)
        )
    return GaussianComplex.from_parts(0, w * component.value.farads.fraction)


def _impedance_scale(
    components: Sequence[RLCComponent], omega: PositiveAngularFrequency
) -> Fraction:
    factors: list[Fraction] = []
    for component in components:
        if component.kind is ElementKind.RESISTOR:
            factors.append(component.value.ohms.fraction)
        elif component.kind is ElementKind.INDUCTOR:
            factors.append(omega.fraction * component.value.henries.fraction)
        else:
            factors.append(1 / (omega.fraction * component.value.farads.fraction))
    if not factors:
        raise ACCircuitError("a driven RLC analysis needs at least one passive branch")
    return max(factors)


def _connected(
    node_count: int,
    edges: Sequence[object],
    positive: int,
    negative: int,
    reference: int,
) -> None:
    adjacency = [set() for _ in range(node_count)]
    for edge in edges:
        a, b = _edge_nodes(edge)
        adjacency[a].add(b)
        adjacency[b].add(a)
    adjacency[positive].add(negative)
    adjacency[negative].add(positive)
    reached, stack = {reference}, [reference]
    while stack:
        node = stack.pop()
        for neighbor in adjacency[node]:
            if neighbor not in reached:
                reached.add(neighbor)
                stack.append(neighbor)
    if len(reached) != node_count:
        raise ACFloatingCircuitError(
            f"nodes are not connected to the declared reference: {tuple(i for i in range(node_count) if i not in reached)}"
        )


def _stamp_exact(
    node_count: int,
    edges: Sequence[object],
    components: Sequence[RLCComponent],
    reference: int,
    positive: int,
    negative: int,
    omega: PositiveAngularFrequency,
) -> tuple[list[list[GaussianComplex]], tuple[int, ...], Fraction]:
    unknown = tuple(i for i in range(node_count) if i != reference)
    local = {node: i for i, node in enumerate(unknown)}
    scale = _impedance_scale(components, omega)
    dimension = len(unknown) + 1
    matrix = [
        [GaussianComplex.zero() for _ in range(dimension)] for _ in range(dimension)
    ]
    scale_z = GaussianComplex.from_parts(scale)
    for edge, component in zip(edges, components):
        a, b = _edge_nodes(edge)
        y = admittance_exact(component, omega) * scale_z
        if a != reference:
            matrix[local[a]][local[a]] = matrix[local[a]][local[a]] + y
        if b != reference:
            matrix[local[b]][local[b]] = matrix[local[b]][local[b]] + y
        if a != reference and b != reference:
            matrix[local[a]][local[b]] = matrix[local[a]][local[b]] - y
            matrix[local[b]][local[a]] = matrix[local[b]][local[a]] - y
    source = len(unknown)
    one = GaussianComplex.one()
    minus_one = -one
    if positive != reference:
        matrix[local[positive]][source] = matrix[local[positive]][source] + one
        matrix[source][local[positive]] = matrix[source][local[positive]] + one
    if negative != reference:
        matrix[local[negative]][source] = matrix[local[negative]][source] + minus_one
        matrix[source][local[negative]] = matrix[source][local[negative]] + minus_one
    return matrix, unknown, scale


def _as_sparse(matrix: Sequence[Sequence[GaussianComplex]]) -> sparse.csc_matrix:
    rows: list[int] = []
    columns: list[int] = []
    data: list[complex] = []
    for r, line in enumerate(matrix):
        for c, value in enumerate(line):
            if not value.is_zero:
                try:
                    numeric = value.to_complex()
                except OverflowError as exc:
                    raise ACNumericalRefusal(str(exc)) from exc
                rows.append(r)
                columns.append(c)
                data.append(numeric)
    return sparse.coo_matrix(
        (data, (rows, columns)), shape=(len(matrix), len(matrix))
    ).tocsc()


def _solve(matrix: sparse.csc_matrix, rhs: np.ndarray) -> np.ndarray:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            candidate = spsolve(matrix, rhs)
    except (MatrixRankWarning, RuntimeError, ValueError) as exc:
        raise ACNumericalRefusal(
            "complex sparse MNA is singular or not factorizable"
        ) from exc
    candidate = np.asarray(candidate, dtype=complex)
    if (
        candidate.ndim != 1
        or not np.all(np.isfinite(candidate.real))
        or not np.all(np.isfinite(candidate.imag))
    ):
        raise ACNumericalRefusal("complex sparse MNA produced a non-finite solution")
    return candidate


def _project_relation(
    dom_ports: int,
    cod_ports: int,
    rows: Sequence[Sequence[GaussianComplex]],
    total_width: int,
    keep: Sequence[int],
) -> ComplexBoundaryRelation:
    eliminated = [i for i in range(total_width) if i not in set(keep)]
    permutation = eliminated + list(keep)
    # Build an intermediate relation so its canonical RREF can expose rows independent of eliminated variables.
    from .rlc_ac_schema import (
        _rref,
    )  # private helper is semantic code in this module family

    reduced = _rref(([row[i] for i in permutation] for row in rows), total_width)
    external = [
        row[len(eliminated) :]
        for row in reduced
        if all(value.is_zero for value in row[: len(eliminated)])
    ]
    return ComplexBoundaryRelation.from_equations(dom_ports, cod_ports, external)


def blackbox_rlc_ac(
    diagram: OpenDiagram, model: RLCModel, omega: PositiveAngularFrequency
) -> ComplexBoundaryRelation:
    if type(model) is not RLCModel or type(omega) is not PositiveAngularFrequency:
        raise TypeError("model and omega must be exact nominal records")
    model.validate_diagram(diagram)
    edges, count, refs = _edges(diagram), _nodes(diagram), _refs(diagram)
    components = model.components_in_structural_order()
    total = count + 2 * len(refs)
    rows: list[list[GaussianComplex]] = []
    zero = GaussianComplex.zero()
    one = GaussianComplex.one()
    laplacian = [[zero for _ in range(count)] for _ in range(count)]
    for edge, component in zip(edges, components):
        a, b = _edge_nodes(edge)
        y = admittance_exact(component, omega)
        laplacian[a][a] = laplacian[a][a] + y
        laplacian[b][b] = laplacian[b][b] + y
        laplacian[a][b] = laplacian[a][b] - y
        laplacian[b][a] = laplacian[b][a] - y
    for node in range(count):
        row = [zero for _ in range(total)]
        row[:count] = laplacian[node]
        for port, ref in enumerate(refs):
            if _resolve(diagram, ref) == node:
                row[count + len(refs) + port] = row[count + len(refs) + port] - one
        rows.append(row)
    for port, ref in enumerate(refs):
        row = [zero for _ in range(total)]
        row[count + port] = one
        row[_resolve(diagram, ref)] = -one
        rows.append(row)
    return _project_relation(
        len(diagram.dom.ports),
        len(diagram.cod.ports),
        rows,
        total,
        list(range(count, total)),
    )


def solve_rlc_ac(
    diagram: OpenDiagram, model: RLCModel, spec: ACSolveSpec
) -> ACSolveResult:
    if type(model) is not RLCModel or type(spec) is not ACSolveSpec:
        raise TypeError("model and spec must be exact nominal records")
    model.validate_diagram(diagram)
    edges, count = _edges(diagram), _nodes(diagram)
    if count == 0:
        raise ACCircuitError("a driven analysis needs at least one canonical node")
    reference, positive, negative = (
        _resolve(diagram, spec.reference),
        _resolve(diagram, spec.drive.positive),
        _resolve(diagram, spec.drive.negative),
    )
    if positive == negative:
        raise ACCircuitError("ideal voltage drive terminals resolve to the same node")
    components = model.components_in_structural_order()
    _connected(count, edges, positive, negative, reference)
    exact_matrix, unknown, scale_fraction = _stamp_exact(
        count, edges, components, reference, positive, negative, spec.omega
    )
    from .rlc_ac_schema import exact_rank

    if exact_rank(exact_matrix) != len(exact_matrix):
        if not any(component.kind is ElementKind.RESISTOR for component in components):
            raise LosslessSingularResonanceError(
                "exact lossless resonant MNA is rank deficient; no regularization was applied"
            )
        raise ACNumericalRefusal("exact complex MNA matrix is rank deficient")
    matrix = _as_sparse(exact_matrix)
    if matrix.shape[0] > spec.conditioning_dimension_limit:
        raise ConditioningRefusal(
            "conditioning assessment exceeds the declared dense-screen dimension limit"
        )
    dense = matrix.toarray()
    try:
        condition = float(np.linalg.cond(dense))
    except np.linalg.LinAlgError as exc:
        raise ConditioningRefusal("conditioning assessment failed") from exc
    if not isfinite(condition) or condition > float(spec.conditioning_limit):
        raise ConditioningRefusal(
            "normalized complex MNA condition exceeds the declared limit"
        )
    try:
        drive = spec.drive.volts_rms.to_complex()
        scale = float(scale_fraction)
    except OverflowError as exc:
        raise ACNumericalRefusal(
            "drive or impedance scale cannot be represented as finite binary64"
        ) from exc
    if not isfinite(scale) or scale <= 0:
        raise ACNumericalRefusal("impedance normalization is non-finite")
    rhs = np.zeros(matrix.shape[0], dtype=complex)
    rhs[-1] = drive
    solution = _solve(matrix, rhs)
    voltages = np.zeros(count, dtype=complex)
    for local, node in enumerate(unknown):
        voltages[node] = solution[local]
    source_current = solution[-1] / scale
    branches: list[RLCBranch] = []
    for index, (edge, component) in enumerate(zip(edges, components)):
        a, b = _edge_nodes(edge)
        drop = complex(voltages[a] - voltages[b])
        try:
            current = admittance_exact(component, spec.omega).to_complex() * drop
        except OverflowError as exc:
            raise ACNumericalRefusal(
                "physical branch admittance cannot be represented as finite binary64"
            ) from exc
        power = drop * current.conjugate()
        branches.append(
            RLCBranch(
                index,
                a,
                b,
                component,
                Phasor.from_complex(drop),
                Phasor.from_complex(current),
                Phasor.from_complex(power),
            )
        )
    source_power = drive * complex(source_current).conjugate()
    source = ACSourceObservation(
        positive,
        negative,
        Phasor.from_complex(drive),
        Phasor.from_complex(complex(source_current)),
        Phasor.from_complex(source_power),
    )
    kcl_values = np.zeros(count, dtype=complex)
    for branch in branches:
        current = branch.current_amperes_rms.to_complex()
        kcl_values[branch.node_a] += current
        kcl_values[branch.node_b] -= current
    source_current_numeric = source.current_entering_positive_amperes_rms.to_complex()
    kcl_values[positive] += source_current_numeric
    kcl_values[negative] -= source_current_numeric
    kcl = float(np.max(np.abs(kcl_values)))
    constraint = float(abs(voltages[positive] - voltages[negative] - drive))
    branch_powers = [x.absorbed_power_va.to_complex() for x in branches]
    branch_currents = [x.current_amperes_rms.to_complex() for x in branches]
    complex_power = abs(sum(branch_powers, source.absorbed_power_va.to_complex()))
    current_scale = max(
        1e-30, abs(source_current_numeric), *(abs(x) for x in branch_currents)
    )
    voltage_scale = max(1.0, abs(drive), *(abs(x) for x in voltages))
    power_scale = max(
        1e-30,
        abs(source.absorbed_power_va.to_complex()),
        *(abs(x) for x in branch_powers),
    )
    refs = _refs(diagram)
    boundary_currents = [0j for _ in refs]
    for i, ref in enumerate(refs):
        if ref == spec.drive.positive:
            boundary_currents[i] -= source_current_numeric
        if ref == spec.drive.negative:
            boundary_currents[i] += source_current_numeric
    relation = blackbox_rlc_ac(diagram, model, spec.omega)
    relation_residual, scaled_relation = relation.residual(
        [complex(voltages[_resolve(diagram, ref)]) for ref in refs] + boundary_currents
    )
    vector_norm = float(np.linalg.norm(solution, ord=np.inf))
    matrix_norm = float(np.linalg.norm(dense, ord=np.inf))
    rhs_norm = float(np.linalg.norm(rhs, ord=np.inf))
    backward = float(
        np.linalg.norm(dense @ solution - rhs, ord=np.inf)
        / max(1e-30, matrix_norm * vector_norm + rhs_norm)
    )
    tolerance = float(spec.scaled_tolerance)
    resistor_real = [
        power.real
        for branch, power in zip(branches, branch_powers)
        if branch.component.kind is ElementKind.RESISTOR
    ]
    ideal_real = [
        abs(power.real)
        for branch, power in zip(branches, branch_powers)
        if branch.component.kind is not ElementKind.RESISTOR
    ]
    if any(value < -tolerance * power_scale for value in resistor_real):
        raise ACResidualError(
            "a positive resistor has materially negative absorbed real power"
        )
    if any(value > tolerance * power_scale for value in ideal_real):
        raise ACResidualError(
            "an ideal inductor or capacitor has material real-power leakage"
        )
    if (
        max(
            kcl / current_scale,
            constraint / voltage_scale,
            complex_power / power_scale,
            scaled_relation,
            backward,
        )
        > tolerance
    ):
        raise ACResidualError("complex MNA failed a declared residual gate")
    diagnostics = ACCircuitDiagnostics(
        kcl,
        constraint,
        float(complex_power),
        relation_residual,
        backward,
        kcl / current_scale,
        constraint / voltage_scale,
        complex_power / power_scale,
        scaled_relation,
        condition,
        min(resistor_real, default=0.0),
        max(ideal_real, default=0.0),
    )
    return ACSolveResult(
        tuple(
            NodePhasor(i, Phasor.from_complex(complex(v)))
            for i, v in enumerate(voltages)
        ),
        tuple(branches),
        source,
        MNAState(
            unknown,
            len(unknown),
            scale,
            tuple(Phasor.from_complex(complex(x)) for x in solution),
        ),
        diagnostics,
    )
