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

from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isfinite
from numbers import Real
from typing import Iterable, Sequence
import warnings

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from .contracts import canonical_digest
from .open_diagram import BoundaryRef, BoundarySide, OpenDiagram


__all__ = [
    "CircuitError",
    "FloatingCircuitError",
    "CircuitNumericalRefusal",
    "CircuitResidualError",
    "Rational",
    "PositiveResistance",
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


@dataclass(frozen=True, order=True)
class Rational:
    """A normalized exact rational number with an explicitly positive denominator."""

    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        if type(self.numerator) is not int or type(self.denominator) is not int:
            raise TypeError("Rational numerator and denominator must be exact ints")
        if self.denominator == 0:
            raise ValueError("Rational denominator must be non-zero")
        sign = -1 if self.denominator < 0 else 1
        divisor = gcd(abs(self.numerator), abs(self.denominator))
        object.__setattr__(self, "numerator", sign * self.numerator // divisor)
        object.__setattr__(self, "denominator", sign * self.denominator // divisor)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def __float__(self) -> float:
        return float(self.fraction)


@dataclass(frozen=True)
class PositiveResistance:
    """An exact, finite-by-construction resistance in ohms.

    The exact record may still underflow or overflow when converted to IEEE-754 for the
    sparse numerical control.  That conversion failure is an explicit numerical refusal,
    not a silently regularized circuit.
    """

    ohms: Rational

    def __post_init__(self) -> None:
        if type(self.ohms) is not Rational:
            raise TypeError("ohms must be an exact Rational")
        if self.ohms.fraction <= 0:
            raise ValueError("resistance must be strictly positive")

    @property
    def fraction(self) -> Fraction:
        return self.ohms.fraction


@dataclass(frozen=True)
class ResistiveDCModel:
    """Positive resistor parameters in the exact structural-edge order of a diagram."""

    resistances: tuple[PositiveResistance, ...]
    presentation_digest: str

    def __post_init__(self) -> None:
        if type(self.resistances) is not tuple:
            raise TypeError("resistances must be an exact tuple")
        if any(type(item) is not PositiveResistance for item in self.resistances):
            raise TypeError("resistances must contain only PositiveResistance records")
        if type(self.presentation_digest) is not str or len(self.presentation_digest) != 64:
            raise TypeError("presentation_digest must be a SHA-256 hex digest")
        try:
            int(self.presentation_digest, 16)
        except ValueError as exc:
            raise ValueError("presentation_digest must be hexadecimal") from exc

    @classmethod
    def for_diagram(
        cls,
        diagram: OpenDiagram,
        resistances: tuple[PositiveResistance, ...],
    ) -> "ResistiveDCModel":
        """Bind opaque edge-order parameters to one exact OpenDiagram presentation.

        This is intentionally a presentation digest, not the budgeted alpha-invariant
        canonical observer: a model tuple is aligned to this presentation's edge order.
        Reordering a raw construction therefore needs an explicit rebind.
        """
        return cls(resistances, canonical_digest(diagram))

    def validate_diagram(self, diagram: OpenDiagram) -> None:
        edges = _structural_edges(diagram)
        if len(edges) != len(self.resistances):
            raise ValueError(
                "ResistiveDCModel resistance count must equal the diagram structural-edge count"
            )
        if canonical_digest(diagram) != self.presentation_digest:
            raise ValueError("ResistiveDCModel is not bound to this exact OpenDiagram presentation")

    def blackbox(self, diagram: OpenDiagram) -> "BoundaryLinearRelation":
        return blackbox_resistive_dc(diagram, self)


def _as_fraction(value: Fraction | Rational | int) -> Fraction:
    if type(value) is Rational:
        return value.fraction
    if type(value) is Fraction:
        return value
    if type(value) is int:
        return Fraction(value, 1)
    raise TypeError("linear-relation coefficients must be exact Fractions or ints")


def _rref(rows: Iterable[Sequence[Fraction | Rational | int]], width: int) -> tuple[tuple[Fraction, ...], ...]:
    """Canonical reduced row echelon form over the rationals, with zero rows removed."""
    matrix = [[_as_fraction(value) for value in row] for row in rows]
    if any(len(row) != width for row in matrix):
        raise ValueError("linear-relation row has the wrong width")
    pivot_row = 0
    for column in range(width):
        candidate = next(
            (row for row in range(pivot_row, len(matrix)) if matrix[row][column] != 0),
            None,
        )
        if candidate is None:
            continue
        matrix[pivot_row], matrix[candidate] = matrix[candidate], matrix[pivot_row]
        pivot = matrix[pivot_row][column]
        matrix[pivot_row] = [value / pivot for value in matrix[pivot_row]]
        for row in range(len(matrix)):
            if row == pivot_row:
                continue
            coefficient = matrix[row][column]
            if coefficient:
                matrix[row] = [
                    value - coefficient * pivot_value
                    for value, pivot_value in zip(matrix[row], matrix[pivot_row])
                ]
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return tuple(tuple(row) for row in matrix if any(value != 0 for value in row))


def _rational_rows(rows: Iterable[Sequence[Fraction]]) -> tuple[tuple[Rational, ...], ...]:
    """Store exact coefficients in the repository's digestible immutable record type."""
    return tuple(
        tuple(Rational(value.numerator, value.denominator) for value in row)
        for row in rows
    )


@dataclass(frozen=True)
class BoundaryLinearRelation:
    """An exact homogeneous relation on ``V(dom,cod), I_inward(dom,cod)``.

    ``rref_rows`` is the canonical RREF of the equation matrix.  A vector belongs to the
    relation exactly when every stored row has zero dot product with it.
    """

    dom_ports: int
    cod_ports: int
    rref_rows: tuple[tuple[Rational, ...], ...]

    def __post_init__(self) -> None:
        if type(self.dom_ports) is not int or type(self.cod_ports) is not int:
            raise TypeError("relation interface widths must be exact ints")
        if self.dom_ports < 0 or self.cod_ports < 0:
            raise ValueError("relation interface widths must be non-negative")
        if type(self.rref_rows) is not tuple or any(type(row) is not tuple for row in self.rref_rows):
            raise TypeError("rref_rows must be an exact tuple of tuples")
        if any(any(type(value) is not Rational for value in row) for row in self.rref_rows):
            raise TypeError("rref_rows must contain only digestible Rational coefficients")
        if any(len(row) != self.variable_count for row in self.rref_rows):
            raise ValueError("relation row width does not match its interfaces")
        normalized = _rational_rows(_rref(self.rref_rows, self.variable_count))
        if normalized != self.rref_rows:
            raise ValueError("rref_rows must already be canonical RREF")

    @property
    def boundary_ports(self) -> int:
        return self.dom_ports + self.cod_ports

    @property
    def variable_count(self) -> int:
        return 2 * self.boundary_ports

    @classmethod
    def from_equations(
        cls,
        dom_ports: int,
        cod_ports: int,
        rows: Iterable[Sequence[Fraction | Rational | int]],
    ) -> "BoundaryLinearRelation":
        width = 2 * (dom_ports + cod_ports)
        return cls(dom_ports, cod_ports, _rational_rows(_rref(rows, width)))

    @classmethod
    def identity(cls, ports: int) -> "BoundaryLinearRelation":
        if type(ports) is not int or ports < 0:
            raise ValueError("identity interface width must be a non-negative exact int")
        # V_in - V_out = 0; current is inward at both exposed boundaries.
        rows: list[list[Fraction]] = []
        width = 4 * ports
        for index in range(ports):
            row = [Fraction(0) for _ in range(width)]
            row[index] = Fraction(1)
            row[ports + index] = Fraction(-1)
            rows.append(row)
            row = [Fraction(0) for _ in range(width)]
            row[2 * ports + index] = Fraction(1)
            row[3 * ports + index] = Fraction(1)
            rows.append(row)
        return cls.from_equations(ports, ports, rows)

    def contains_exact(self, values: Sequence[Fraction | Rational | int]) -> bool:
        if len(values) != self.variable_count:
            raise ValueError("relation witness has the wrong width")
        vector = tuple(_as_fraction(value) for value in values)
        return all(
            sum(coefficient.fraction * value for coefficient, value in zip(row, vector)) == 0
            for row in self.rref_rows
        )

    def residual(self, values: Sequence[float]) -> float:
        if len(values) != self.variable_count:
            raise ValueError("relation witness has the wrong width")
        if any(not isfinite(float(value)) for value in values):
            return float("inf")
        return max(
            (
                abs(sum(float(coefficient.fraction) * float(value) for coefficient, value in zip(row, values)))
                for row in self.rref_rows
            ),
            default=0.0,
        )

    def scaled_residual(self, values: Sequence[float]) -> float:
        """Dimensionless row-wise cancellation residual for a floating-point witness."""
        if len(values) != self.variable_count:
            raise ValueError("relation witness has the wrong width")
        if any(not isfinite(float(value)) for value in values):
            return float("inf")
        worst = 0.0
        for row in self.rref_rows:
            terms = [float(coefficient.fraction) * float(value) for coefficient, value in zip(row, values)]
            worst = max(worst, abs(sum(terms)) / max(1e-30, sum(abs(term) for term in terms)))
        return worst

    def then(self, other: "BoundaryLinearRelation") -> "BoundaryLinearRelation":
        if type(other) is not BoundaryLinearRelation:
            raise TypeError("can only compose BoundaryLinearRelation values")
        if self.cod_ports != other.dom_ports:
            raise ValueError("relation interfaces do not compose")
        a, b, c = self.dom_ports, self.cod_ports, other.cod_ports
        # Global coordinates are V_A,V_B,V_C,I_A,I_B(f),I_B(g),I_C.  The two B-current
        # vectors are kept separate so their cancellation equation is explicit.
        total = a + b + c + a + b + b + c
        rows: list[list[Fraction]] = []

        def embed(row: Sequence[Fraction], positions: Sequence[int]) -> list[Fraction]:
            result = [Fraction(0) for _ in range(total)]
            for coefficient, position in zip(row, positions):
                result[position] = coefficient
            return result

        f_positions = (
            list(range(0, a))
            + list(range(a, a + b))
            + list(range(a + b + c, a + b + c + a))
            + list(range(a + b + c + a, a + b + c + a + b))
        )
        g_positions = (
            list(range(a, a + b))
            + list(range(a + b, a + b + c))
            + list(range(a + b + c + a + b, a + b + c + a + b + b))
            + list(range(a + b + c + a + b + b, total))
        )
        rows.extend(embed(row, f_positions) for row in self.rref_rows)
        rows.extend(embed(row, g_positions) for row in other.rref_rows)
        # I_B(f) + I_B(g) = 0.
        for index in range(b):
            row = [Fraction(0) for _ in range(total)]
            row[a + b + c + a + index] = Fraction(1)
            row[a + b + c + a + b + index] = Fraction(1)
            rows.append(row)
        keep = (
            list(range(0, a))
            + list(range(a + b, a + b + c))
            + list(range(a + b + c, a + b + c + a))
            + list(range(a + b + c + a + b + b, total))
        )
        return _project_relation(a, c, rows, total, keep)

    def tensor(self, other: "BoundaryLinearRelation") -> "BoundaryLinearRelation":
        if type(other) is not BoundaryLinearRelation:
            raise TypeError("can only tensor BoundaryLinearRelation values")
        a, b, c, d = self.dom_ports, self.cod_ports, other.dom_ports, other.cod_ports
        total = 2 * (a + c + b + d)
        rows: list[list[Fraction]] = []

        def embed(row: Sequence[Fraction], positions: Sequence[int]) -> list[Fraction]:
            result = [Fraction(0) for _ in range(total)]
            for coefficient, position in zip(row, positions):
                result[position] = coefficient
            return result

        f_positions = (
            list(range(0, a))
            + list(range(a + c, a + c + b))
            + list(range(a + c + b + d, a + c + b + d + a))
            + list(range(a + c + b + d + a + c, a + c + b + d + a + c + b))
        )
        g_positions = (
            list(range(a, a + c))
            + list(range(a + c + b, a + c + b + d))
            + list(range(a + c + b + d + a, a + c + b + d + a + c))
            + list(range(a + c + b + d + a + c + b, total))
        )
        rows.extend(embed(row, f_positions) for row in self.rref_rows)
        rows.extend(embed(row, g_positions) for row in other.rref_rows)
        return BoundaryLinearRelation.from_equations(a + c, b + d, rows)


def _project_relation(
    dom_ports: int,
    cod_ports: int,
    rows: Iterable[Sequence[Fraction]],
    total_width: int,
    keep: Sequence[int],
) -> BoundaryLinearRelation:
    """Eliminate every non-kept variable from homogeneous rational equations."""
    if len(set(keep)) != len(keep) or any(index < 0 or index >= total_width for index in keep):
        raise ValueError("invalid relation projection indices")
    eliminated = [index for index in range(total_width) if index not in set(keep)]
    permutation = eliminated + list(keep)
    reduced = _rref(([row[index] for index in permutation] for row in rows), total_width)
    internal_width = len(eliminated)
    external_rows = [row[internal_width:] for row in reduced if all(value == 0 for value in row[:internal_width])]
    return BoundaryLinearRelation.from_equations(dom_ports, cod_ports, external_rows)


def _structural_edges(diagram: OpenDiagram) -> tuple[object, ...]:
    """Read S0's immutable canonical edge sequence without trusting user labels."""
    if type(diagram) is not OpenDiagram:
        raise TypeError("diagram must be an exact OpenDiagram")
    # The S0 implementation exposes this stable structural sequence.  Keeping the lookup
    # isolated makes the semantic boundary explicit and avoids treating construction labels
    # as meaning.
    edges = diagram.edges
    if type(edges) is not tuple:
        raise TypeError("OpenDiagram structural_edges must be an exact tuple")
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
    for edge, resistance in zip(edges, model.resistances):
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


@dataclass(frozen=True)
class DCVoltageDrive:
    """One signed exact ideal source; current is reported entering ``positive``."""

    positive: BoundaryRef
    negative: BoundaryRef
    volts: Rational

    def __post_init__(self) -> None:
        if type(self.positive) is not BoundaryRef or type(self.negative) is not BoundaryRef:
            raise TypeError("drive terminals must be exact BoundaryRef values")
        if type(self.volts) is not Rational:
            raise TypeError("drive volts must be an exact Rational")


@dataclass(frozen=True)
class DCSolveSpec:
    """Experiment data, deliberately separate from the open topology/model."""

    reference: BoundaryRef
    drive: DCVoltageDrive
    scaled_tolerance: float = 1e-9

    def __post_init__(self) -> None:
        if type(self.reference) is not BoundaryRef:
            raise TypeError("reference must be an exact BoundaryRef")
        if type(self.drive) is not DCVoltageDrive:
            raise TypeError("drive must be an exact DCVoltageDrive")
        if isinstance(self.scaled_tolerance, bool) or not isinstance(self.scaled_tolerance, Real):
            raise TypeError("scaled_tolerance must be a real number")
        if not isfinite(float(self.scaled_tolerance)) or not 0 < float(self.scaled_tolerance) < 1:
            raise ValueError("scaled_tolerance must be finite and strictly between zero and one")


@dataclass(frozen=True)
class NodeVoltage:
    node_index: int
    volts: float


@dataclass(frozen=True)
class ResistorBranch:
    branch_index: int
    node_a: int
    node_b: int
    resistance: PositiveResistance
    voltage_drop_volts: float
    current_amperes: float
    absorbed_power_watts: float


@dataclass(frozen=True)
class SourceObservation:
    positive_node: int
    negative_node: int
    volts: float
    current_entering_positive_amperes: float
    absorbed_power_watts: float


@dataclass(frozen=True)
class CircuitDiagnostics:
    kcl_residual_amperes: float
    constraint_residual_volts: float
    power_residual_watts: float
    relation_residual: float
    scaled_kcl_residual: float
    scaled_constraint_residual: float
    scaled_power_residual: float
    scaled_relation_residual: float


@dataclass(frozen=True)
class DCSolveResult:
    nodes: tuple[NodeVoltage, ...]
    branches: tuple[ResistorBranch, ...]
    source: SourceObservation
    diagnostics: CircuitDiagnostics


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
        nodes, edges, model.resistances, reference, positive, negative, drive_volts
    )
    solution = _solve_sparse(matrix, rhs)
    voltages = np.zeros(nodes, dtype=float)
    for local, node in enumerate(unknown_nodes):
        voltages[node] = solution[local]
    source_current = float(solution[-1])
    branches: list[ResistorBranch] = []
    for index, (edge, resistance) in enumerate(zip(edges, model.resistances)):
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
    # Separate physical dimensions; a raw norm of the mixed-unit MNA block is not a
    # meaningful numerical certificate.
    residual = matrix @ solution - rhs
    kcl = float(np.max(np.abs(residual[:-1]))) if len(residual) > 1 else 0.0
    constraint = float(abs(residual[-1]))
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
