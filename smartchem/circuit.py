"""Exact passive-resistor relations and a deliberately narrow DC MNA control.

This module is intentionally *not* a scalar-impedance reducer.  ``blackbox`` maps an
open resistor diagram to the exact linear relation on its boundary potentials and
currents (all currents are positive **into** the diagram).  ``solve_resistive_dc``
then chooses one ideal-voltage experiment on that relation and independently solves the
same network by sparse modified nodal analysis.

The first interpreter admits only finite positive resistances.  It is a passive DC
control, not an AC/RLC, port-Hamiltonian, or general circuit simulator.
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
from .resistive_dc_schema import (
    BoundaryLinearRelation,
    CircuitDiagnostics,
    DCSolveResult,
    DCSolveSpec,
    DCVoltageDrive,
    NodeVoltage,
    PositiveResistance,
    Rational,
    ResistiveDCModel,
    ResistorBranch,
    ResistorEdgeBinding,
    SourceObservation,
    _project_relation,
    _rref,
)


__all__ = [
    "CircuitError",
    "FloatingCircuitError",
    "CircuitNumericalRefusal",
    "CircuitResidualError",
    "Rational",
    "PositiveResistance",
    "ResistorEdgeBinding",
    "ResistiveDCModel",
    "BoundaryLinearRelation",
    "DCVoltageDrive",
    "DCSolveSpec",
    "NodeVoltage",
    "ResistorBranch",
    "SourceObservation",
    "CircuitDiagnostics",
    "DCSolveResult",
    "blackbox_resistive_dc",
    "solve_resistive_dc",
]


class CircuitError(ValueError):
    """Base class for a refused circuit construction or interpretation."""


class FloatingCircuitError(CircuitError):
    """A driven analysis found topology with no reference-connected path."""


class CircuitNumericalRefusal(CircuitError):
    """Sparse MNA could not produce a finite, backward-stable answer."""


class CircuitResidualError(CircuitNumericalRefusal):
    """A candidate answer failed a declared residual, power, or relation gate."""


def _structural_edges(diagram: OpenDiagram) -> tuple[object, ...]:
    """Read S0's public model-alignment edge view without trusting user labels."""
    if type(diagram) is not OpenDiagram:
        raise TypeError("diagram must be an exact OpenDiagram")
    edges = diagram.structural_edges()
    if type(edges) is not tuple:
        raise TypeError("OpenDiagram.structural_edges() must return an exact tuple")
    return edges


def _node_count(diagram: OpenDiagram) -> int:
    kinds = diagram.node_kinds
    if type(kinds) is not tuple:
        raise TypeError("OpenDiagram node_kinds must be an exact tuple")
    count = len(kinds)
    return count


def _edge_nodes(edge: object) -> tuple[int, int]:
    a = edge.node_a
    b = edge.node_b
    if type(a) is not int or type(b) is not int:
        raise TypeError("structural edge nodes must be exact node indices")
    return a, b


def _boundary_refs(diagram: OpenDiagram) -> tuple[BoundaryRef, ...]:
    return tuple(
        [BoundaryRef(BoundarySide.INPUT, index) for index in range(len(diagram.dom.ports))]
        + [BoundaryRef(BoundarySide.OUTPUT, index) for index in range(len(diagram.cod.ports))]
    )


def _resolve_boundary(diagram: OpenDiagram, ref: BoundaryRef) -> int:
    if type(ref) is not BoundaryRef:
        raise TypeError("boundary references must be exact BoundaryRef values")
    node = diagram.node_for(ref)
    if type(node) is not int or node < 0 or node >= _node_count(diagram):
        raise TypeError("OpenDiagram resolved an invalid canonical node")
    return node


def blackbox_resistive_dc(diagram: OpenDiagram, model: ResistiveDCModel) -> BoundaryLinearRelation:
    """Return the exact passive boundary relation for ``diagram`` and ``model``.

    Boundary variables are ordered ``V(dom,cod), I_inward(dom,cod)``.  Every internal
    node voltage is existentially eliminated over ``Fraction`` arithmetic.
    """
    if type(model) is not ResistiveDCModel:
        raise TypeError("model must be an exact ResistiveDCModel")
    model.validate_diagram(diagram)
    nodes = _node_count(diagram)
    edges = _structural_edges(diagram)
    refs = _boundary_refs(diagram)
    dom_ports = len(diagram.dom.ports)
    cod_ports = len(diagram.cod.ports)
    if len(refs) != dom_ports + cod_ports:
        raise TypeError("OpenDiagram boundary reference order does not match its interfaces")
    total = nodes + 2 * len(refs)
    rows: list[list[Fraction]] = []
    # Nodal KCL: passive current leaving the node minus boundary current entering it is 0.
    laplacian = [[Fraction(0) for _ in range(nodes)] for _ in range(nodes)]
    for edge, resistance in zip(edges, model.resistances_in_structural_order()):
        a, b = _edge_nodes(edge)
        if not (0 <= a < nodes and 0 <= b < nodes):
            raise TypeError("structural edge refers to an invalid canonical node")
        conductance = Fraction(1, 1) / resistance.fraction
        laplacian[a][a] += conductance
        laplacian[b][b] += conductance
        laplacian[a][b] -= conductance
        laplacian[b][a] -= conductance
    for node in range(nodes):
        row = [Fraction(0) for _ in range(total)]
        row[:nodes] = laplacian[node]
        for port, ref in enumerate(refs):
            if _resolve_boundary(diagram, ref) == node:
                row[nodes + len(refs) + port] -= Fraction(1)
        rows.append(row)
    # Each exposed potential is the potential of its attached canonical node.
    for port, ref in enumerate(refs):
        row = [Fraction(0) for _ in range(total)]
        row[nodes + port] = Fraction(1)
        row[_resolve_boundary(diagram, ref)] = Fraction(-1)
        rows.append(row)
    keep = list(range(nodes, total))
    return _project_relation(dom_ports, cod_ports, rows, total, keep)


def _float_resistance(value: PositiveResistance) -> float:
    try:
        result = float(value.fraction)
    except OverflowError as exc:
        raise CircuitNumericalRefusal("exact resistance cannot be represented as finite float") from exc
    if not isfinite(result) or result <= 0:
        raise CircuitNumericalRefusal("exact resistance underflowed or overflowed in numerical MNA")
    return result


def _reference_connected(
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
    reached = {reference}
    frontier = [reference]
    while frontier:
        node = frontier.pop()
        for neighbor in adjacency[node]:
            if neighbor not in reached:
                reached.add(neighbor)
                frontier.append(neighbor)
    if len(reached) != node_count:
        missing = tuple(index for index in range(node_count) if index not in reached)
        raise FloatingCircuitError(f"nodes are not connected to the declared reference: {missing}")


def _assemble_mna(
    node_count: int,
    edges: Sequence[object],
    resistances: Sequence[PositiveResistance],
    reference: int,
    positive: int,
    negative: int,
    drive_volts: float,
) -> tuple[sparse.csc_matrix, np.ndarray, tuple[int, ...]]:
    """The sole numerical stamping path for every E1 topology."""
    unknown_nodes = tuple(index for index in range(node_count) if index != reference)
    local = {node: index for index, node in enumerate(unknown_nodes)}
    dimension = len(unknown_nodes) + 1
    row: list[int] = []
    column: list[int] = []
    data: list[float] = []

    def stamp(r: int, c: int, value: float) -> None:
        row.append(r)
        column.append(c)
        data.append(value)

    for edge, resistance in zip(edges, resistances):
        a, b = _edge_nodes(edge)
        resistance_float = _float_resistance(resistance)
        conductance = 1.0 / resistance_float
        if not isfinite(conductance) or conductance <= 0:
            raise CircuitNumericalRefusal("resistor conductance is not finite and positive")
        if a != reference:
            stamp(local[a], local[a], conductance)
        if b != reference:
            stamp(local[b], local[b], conductance)
        if a != reference and b != reference:
            stamp(local[a], local[b], -conductance)
            stamp(local[b], local[a], -conductance)
    source_index = len(unknown_nodes)
    if positive != reference:
        stamp(local[positive], source_index, 1.0)
        stamp(source_index, local[positive], 1.0)
    if negative != reference:
        stamp(local[negative], source_index, -1.0)
        stamp(source_index, local[negative], -1.0)
    rhs = np.zeros(dimension, dtype=float)
    rhs[source_index] = drive_volts
    return sparse.coo_matrix((data, (row, column)), shape=(dimension, dimension)).tocsc(), rhs, unknown_nodes


def _solve_sparse(matrix: sparse.csc_matrix, rhs: np.ndarray) -> np.ndarray:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            candidate = spsolve(matrix, rhs)
    except (MatrixRankWarning, RuntimeError, ValueError) as exc:
        raise CircuitNumericalRefusal("sparse MNA matrix is singular or not factorizable") from exc
    candidate = np.asarray(candidate, dtype=float)
    if candidate.ndim != 1 or not np.all(np.isfinite(candidate)):
        raise CircuitNumericalRefusal("sparse MNA produced a non-finite solution")
    return candidate


def solve_resistive_dc(
    diagram: OpenDiagram,
    model: ResistiveDCModel,
    spec: DCSolveSpec,
) -> DCSolveResult:
    """Solve exactly one grounded ideal-voltage experiment by sparse MNA.

    The returned numerical point is required to satisfy both independent assembly
    diagnostics and the exact black-box relation evaluated in floating point.
    """
    if type(model) is not ResistiveDCModel:
        raise TypeError("model must be an exact ResistiveDCModel")
    if type(spec) is not DCSolveSpec:
        raise TypeError("spec must be an exact DCSolveSpec")
    model.validate_diagram(diagram)
    edges = _structural_edges(diagram)
    nodes = _node_count(diagram)
    if nodes == 0:
        raise CircuitError("a driven analysis needs at least one canonical node")
    reference = _resolve_boundary(diagram, spec.reference)
    positive = _resolve_boundary(diagram, spec.drive.positive)
    negative = _resolve_boundary(diagram, spec.drive.negative)
    if positive == negative:
        raise CircuitError("ideal-voltage drive terminals resolve to the same node")
    try:
        drive_volts = float(spec.drive.volts.fraction)
    except OverflowError as exc:
        raise CircuitNumericalRefusal("exact drive voltage cannot be represented as finite float") from exc
    if not isfinite(drive_volts):
        raise CircuitNumericalRefusal("exact drive voltage is not finite in numerical MNA")
    _reference_connected(nodes, edges, positive, negative, reference)
    matrix, rhs, unknown_nodes = _assemble_mna(
        nodes,
        edges,
        model.resistances_in_structural_order(),
        reference,
        positive,
        negative,
        drive_volts,
    )
    solution = _solve_sparse(matrix, rhs)
    voltages = np.zeros(nodes, dtype=float)
    for local, node in enumerate(unknown_nodes):
        voltages[node] = solution[local]
    source_current = float(solution[-1])
    branches: list[ResistorBranch] = []
    for index, (edge, resistance) in enumerate(
        zip(edges, model.resistances_in_structural_order())
    ):
        a, b = _edge_nodes(edge)
        drop = float(voltages[a] - voltages[b])
        current = drop / _float_resistance(resistance)
        power = drop * current
        branches.append(ResistorBranch(index, a, b, resistance, drop, current, power))
    source = SourceObservation(
        positive,
        negative,
        drive_volts,
        source_current,
        drive_volts * source_current,
    )
    # Re-evaluate physical residuals from retained branch/source values.  A raw norm of
    # the mixed-unit MNA block is not a meaningful numerical certificate.
    node_kcl = [0.0 for _ in range(nodes)]
    for branch in branches:
        node_kcl[branch.node_a] += branch.current_amperes
        node_kcl[branch.node_b] -= branch.current_amperes
    node_kcl[positive] += source_current
    node_kcl[negative] -= source_current
    kcl = max((abs(value) for value in node_kcl), default=0.0)
    constraint = abs(float(voltages[positive] - voltages[negative]) - drive_volts)
    power = abs(sum(branch.absorbed_power_watts for branch in branches) + source.absorbed_power_watts)
    voltage_scale = max(1.0, abs(drive_volts), float(np.max(np.abs(voltages))))
    current_scale = max(
        1e-30,
        abs(source_current),
        *(abs(branch.current_amperes) for branch in branches),
    )
    power_scale = max(
        1e-30,
        abs(source.absorbed_power_watts),
        *(abs(branch.absorbed_power_watts) for branch in branches),
    )
    refs = _boundary_refs(diagram)
    boundary_currents = [0.0 for _ in refs]
    # The source is external to the passive diagram.  Its current at each selected port is
    # the inward current of the resistor black-box; all other exposed ports receive zero.
    for port, ref in enumerate(refs):
        if ref == spec.drive.positive:
            boundary_currents[port] -= source_current
        if ref == spec.drive.negative:
            boundary_currents[port] += source_current
    relation_vector = [float(voltages[_resolve_boundary(diagram, ref)]) for ref in refs] + boundary_currents
    relation = blackbox_resistive_dc(diagram, model)
    relation_residual = relation.residual(relation_vector)
    relation_scaled = relation.scaled_residual(relation_vector)
    diagnostics = CircuitDiagnostics(
        kcl,
        constraint,
        power,
        relation_residual,
        kcl / current_scale,
        constraint / voltage_scale,
        power / power_scale,
        relation_scaled,
    )
    tolerance = float(spec.scaled_tolerance)
    if any(branch.absorbed_power_watts < -tolerance * power_scale for branch in branches):
        raise CircuitResidualError("a positive resistor has materially negative absorbed power")
    if max(
        diagnostics.scaled_kcl_residual,
        diagnostics.scaled_constraint_residual,
        diagnostics.scaled_power_residual,
        diagnostics.scaled_relation_residual,
    ) > tolerance:
        raise CircuitResidualError("sparse MNA failed an independently declared residual gate")
    return DCSolveResult(
        tuple(NodeVoltage(index, float(value)) for index, value in enumerate(voltages)),
        tuple(branches),
        source,
        diagnostics,
    )
