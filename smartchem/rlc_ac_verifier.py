"""Production-independent verifier for the finite positive-frequency RLC control.

This module deliberately imports neither :mod:`smartchem.rlc_ac_circuit` nor
:mod:`smartchem.rlc_ac`.  It shares immutable records with the interpreter, but derives
the Q(i) boundary relation, normalized driven-MNA matrix/rank, and every numerical check
locally.  It is a verifier for one finite passive phasor network, not a device or
transient-model certification.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from math import isfinite
import sys
from typing import Iterable, Sequence

import numpy as np

from .contracts import canonical_digest
from .open_diagram import BoundaryRef, BoundarySide, CanonicalDiagram, OpenDiagram
from .rlc_ac_schema import (
    ACCircuitDiagnostics,
    ACSolveResult,
    ACSolveSpec,
    ACSourceObservation,
    ACVoltageDrive,
    ComplexBoundaryRelation,
    ElementKind,
    GaussianComplex,
    MNAState,
    NodePhasor,
    Phasor,
    PositiveAngularFrequency,
    PositiveCapacitance,
    PositiveInductance,
    PositiveResistance,
    RLCACAnalysis,
    RLCACSubject,
    RLCBranch,
    RLCComponent,
    RLCEdgeBinding,
    RLCModel,
    Rational,
)

__all__ = [
    "DirectACDiagnostics",
    "DirectACVerificationDecision",
    "DirectACVerificationReport",
    "direct_preflight",
    "verify_rlc_ac_analysis",
]


class DirectACVerificationDecision(str, Enum):
    PASS = "pass"
    REFUSE = "refuse"
    FAIL = "fail"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class DirectACDiagnostics:
    kcl_residual_amperes: float
    constraint_residual_volts: float
    complex_power_residual_va: float
    relation_residual: float
    mna_backward_residual: float
    scaled_kcl_residual: float
    scaled_constraint_residual: float
    scaled_power_residual: float
    scaled_relation_residual: float
    condition_number: float
    minimum_resistor_absorbed_real_power_watts: float
    maximum_ideal_reactive_real_power_watts: float

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(float(value))
            ):
                raise TypeError(f"{name} must be a finite real scalar")
        if self.condition_number < 1:
            raise ValueError("condition_number must be at least one")
        if self.maximum_ideal_reactive_real_power_watts < 0:
            raise ValueError("maximum ideal reactive real power must be non-negative")


@dataclass(frozen=True)
class DirectACVerificationReport:
    decision: DirectACVerificationDecision
    canonical_forms_ok: bool
    inventory_ok: bool
    exact_relation_ok: bool
    exact_mna_rank_ok: bool
    branch_law_ok: bool
    kcl_ok: bool
    source_constraint_ok: bool
    power_ok: bool
    passivity_ok: bool
    diagnostics: DirectACDiagnostics
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.decision) is not DirectACVerificationDecision:
            raise TypeError("decision must be an exact DirectACVerificationDecision")
        for name in (
            "canonical_forms_ok",
            "inventory_ok",
            "exact_relation_ok",
            "exact_mna_rank_ok",
            "branch_law_ok",
            "kcl_ok",
            "source_constraint_ok",
            "power_ok",
            "passivity_ok",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be an exact bool")
        if type(self.diagnostics) is not DirectACDiagnostics:
            raise TypeError("diagnostics must be an exact DirectACDiagnostics")
        if type(self.reasons) is not tuple or any(
            type(reason) is not str for reason in self.reasons
        ):
            raise TypeError("reasons must be an exact tuple of strings")

    @property
    def passed(self) -> bool:
        return self.decision is DirectACVerificationDecision.PASS


_Q = tuple[Fraction, Fraction]
_ZERO: _Q = (Fraction(0), Fraction(0))
_ONE: _Q = (Fraction(1), Fraction(0))
_ZERO_DIAGNOSTICS = DirectACDiagnostics(
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
)


def _report(
    decision: DirectACVerificationDecision,
    reasons: Iterable[str],
    *,
    canonical_forms_ok: bool = False,
    inventory_ok: bool = False,
    exact_relation_ok: bool = False,
    exact_mna_rank_ok: bool = False,
    branch_law_ok: bool = False,
    kcl_ok: bool = False,
    source_constraint_ok: bool = False,
    power_ok: bool = False,
    passivity_ok: bool = False,
    diagnostics: DirectACDiagnostics = _ZERO_DIAGNOSTICS,
) -> DirectACVerificationReport:
    return DirectACVerificationReport(
        decision,
        canonical_forms_ok,
        inventory_ok,
        exact_relation_ok,
        exact_mna_rank_ok,
        branch_law_ok,
        kcl_ok,
        source_constraint_ok,
        power_ok,
        passivity_ok,
        diagnostics,
        tuple(reasons),
    )


def _fraction(value: object, name: str) -> Fraction:
    if type(value) is not Rational:
        raise TypeError(f"{name} has the wrong exact Rational type")
    numerator, denominator = (
        getattr(value, "numerator", None),
        getattr(value, "denominator", None),
    )
    if type(numerator) is not int or type(denominator) is not int or denominator == 0:
        raise TypeError(f"{name} is not an exact rational record")
    return Fraction(numerator, denominator)


def _q(real: Fraction | int = 0, imag: Fraction | int = 0) -> _Q:
    return Fraction(real), Fraction(imag)


def _q_add(left: _Q, right: _Q) -> _Q:
    return left[0] + right[0], left[1] + right[1]


def _q_sub(left: _Q, right: _Q) -> _Q:
    return left[0] - right[0], left[1] - right[1]


def _q_neg(value: _Q) -> _Q:
    return -value[0], -value[1]


def _q_mul(left: _Q, right: _Q) -> _Q:
    return left[0] * right[0] - left[1] * right[1], left[0] * right[1] + left[
        1
    ] * right[0]


def _q_inv(value: _Q) -> _Q:
    denominator = value[0] * value[0] + value[1] * value[1]
    if not denominator:
        raise ZeroDivisionError("zero Q(i) element is not invertible")
    return value[0] / denominator, -value[1] / denominator


def _q_to_complex(value: _Q) -> complex:
    result = complex(float(value[0]), float(value[1]))
    if not isfinite(result.real) or not isfinite(result.imag):
        raise OverflowError(
            "exact Q(i) coefficient cannot be represented as finite binary64"
        )
    return result


def _q_from_schema(value: object, name: str) -> _Q:
    if type(value) is not GaussianComplex:
        raise TypeError(f"{name} has the wrong exact GaussianComplex type")
    return _fraction(getattr(value, "real", None), f"{name}.real"), _fraction(
        getattr(value, "imag", None), f"{name}.imag"
    )


def _component_value(component: object, name: str) -> Fraction:
    if type(component) is not RLCComponent:
        raise TypeError(f"{name} has the wrong exact RLCComponent type")
    kind, value = getattr(component, "kind", None), getattr(component, "value", None)
    if type(kind) is not ElementKind:
        raise TypeError(f"{name}.kind has the wrong exact ElementKind type")
    expected = {
        ElementKind.RESISTOR: (PositiveResistance, "ohms"),
        ElementKind.INDUCTOR: (PositiveInductance, "henries"),
        ElementKind.CAPACITOR: (PositiveCapacitance, "farads"),
    }[kind]
    if type(value) is not expected[0]:
        raise TypeError(f"{name} has the wrong exact positive parameter record")
    result = _fraction(getattr(value, expected[1], None), f"{name}.{expected[1]}")
    if result <= 0:
        raise ValueError(f"{name} must be strictly positive")
    return result


def _structural_components(model: object, edge_count: int) -> tuple[RLCComponent, ...]:
    if type(model) is not RLCModel:
        raise TypeError("model has the wrong exact RLCModel type")
    components, bindings = (
        getattr(model, "components", None),
        getattr(model, "edge_bindings", None),
    )
    if type(components) is not tuple or len(components) != edge_count:
        raise ValueError("component inventory does not match structural edges")
    if type(bindings) is not tuple or len(bindings) != edge_count:
        raise ValueError("edge bindings do not cover the model inventory")
    ordered: list[RLCComponent | None] = [None] * edge_count
    source_indices: list[int] = []
    destination_indices: list[int] = []
    for position, binding in enumerate(bindings):
        if type(binding) is not RLCEdgeBinding:
            raise TypeError(f"edge binding {position} has the wrong exact type")
        source, destination = (
            getattr(binding, "model_index", None),
            getattr(binding, "structural_edge_index", None),
        )
        if (
            type(source) is not int
            or type(destination) is not int
            or not 0 <= source < edge_count
            or not 0 <= destination < edge_count
        ):
            raise ValueError("edge binding index is outside the finite inventory")
        component = components[source]
        _component_value(component, f"component[{source}]")
        ordered[destination] = component
        source_indices.append(source)
        destination_indices.append(destination)
    if (
        sorted(source_indices) != list(range(edge_count))
        or sorted(destination_indices) != list(range(edge_count))
        or any(item is None for item in ordered)
    ):
        raise ValueError(
            "edge bindings must cover model and structural inventories exactly once"
        )
    return tuple(item for item in ordered if item is not None)


def _admittance(component: RLCComponent, omega: Fraction) -> _Q:
    value = _component_value(component, "component")
    if component.kind is ElementKind.RESISTOR:
        return _q(1 / value)
    if component.kind is ElementKind.INDUCTOR:
        return _q(0, -1 / (omega * value))
    return _q(0, omega * value)


def _impedance_scale(components: Sequence[RLCComponent], omega: Fraction) -> Fraction:
    factors: list[Fraction] = []
    for component in components:
        value = _component_value(component, "component")
        if component.kind is ElementKind.RESISTOR:
            factors.append(value)
        elif component.kind is ElementKind.INDUCTOR:
            factors.append(omega * value)
        else:
            factors.append(1 / (omega * value))
    if not factors:
        raise ValueError("a driven RLC analysis requires one passive branch")
    return max(factors)


def _refs(diagram: OpenDiagram) -> tuple[BoundaryRef, ...]:
    return tuple(
        BoundaryRef(BoundarySide.INPUT, i) for i in range(len(diagram.dom.ports))
    ) + tuple(
        BoundaryRef(BoundarySide.OUTPUT, i) for i in range(len(diagram.cod.ports))
    )


def _q_rref(rows: Iterable[Sequence[_Q]], width: int) -> tuple[tuple[_Q, ...], ...]:
    work = [list(row) for row in rows]
    if any(len(row) != width for row in work):
        raise ValueError("verifier Q(i) relation row has the wrong width")
    active = 0
    for column in range(width):
        pivot = next(
            (row for row in range(active, len(work)) if work[row][column] != _ZERO),
            None,
        )
        if pivot is None:
            continue
        work[active], work[pivot] = work[pivot], work[active]
        inverse = _q_inv(work[active][column])
        work[active] = [_q_mul(value, inverse) for value in work[active]]
        for row in range(len(work)):
            if row == active or work[row][column] == _ZERO:
                continue
            multiple = work[row][column]
            work[row] = [
                _q_sub(value, _q_mul(multiple, pivot_value))
                for value, pivot_value in zip(work[row], work[active])
            ]
        active += 1
        if active == len(work):
            break
    return tuple(tuple(row) for row in work if any(value != _ZERO for value in row))


def _expected_relation(
    diagram: OpenDiagram, components: tuple[RLCComponent, ...], omega: Fraction
) -> tuple[tuple[_Q, ...], ...]:
    node_count, edges, refs = (
        len(diagram.node_kinds),
        diagram.structural_edges(),
        _refs(diagram),
    )
    boundary_count, total_width = len(refs), node_count + 2 * len(refs)
    laplacian = [[_ZERO for _ in range(node_count)] for _ in range(node_count)]
    for edge, component in zip(edges, components):
        y = _admittance(component, omega)
        a, b = edge.node_a, edge.node_b
        laplacian[a][a] = _q_add(laplacian[a][a], y)
        laplacian[b][b] = _q_add(laplacian[b][b], y)
        laplacian[a][b] = _q_sub(laplacian[a][b], y)
        laplacian[b][a] = _q_sub(laplacian[b][a], y)
    equations: list[list[_Q]] = []
    for node in range(node_count):
        row = [_ZERO for _ in range(total_width)]
        row[:node_count] = laplacian[node]
        for index, ref in enumerate(refs):
            if diagram.node_for(ref) == node:
                row[node_count + boundary_count + index] = _q(-1)
        equations.append(row)
    for index, ref in enumerate(refs):
        row = [_ZERO for _ in range(total_width)]
        row[diagram.node_for(ref)] = _q(-1)
        row[node_count + index] = _q(1)
        equations.append(row)
    reduced = _q_rref(equations, total_width)
    external = tuple(
        row[node_count:]
        for row in reduced
        if all(value == _ZERO for value in row[:node_count])
    )
    return _q_rref(external, 2 * boundary_count)


def _candidate_relation(
    relation: object, dom_ports: int, cod_ports: int
) -> tuple[tuple[_Q, ...], ...]:
    if type(relation) is not ComplexBoundaryRelation:
        raise TypeError(
            "boundary relation has the wrong exact ComplexBoundaryRelation type"
        )
    if (
        getattr(relation, "dom_ports", None) != dom_ports
        or getattr(relation, "cod_ports", None) != cod_ports
    ):
        raise ValueError("boundary relation interface does not match the diagram")
    rows = getattr(relation, "rref_rows", None)
    if type(rows) is not tuple or any(type(row) is not tuple for row in rows):
        raise TypeError("boundary relation rows must be exact tuples")
    width = 2 * (dom_ports + cod_ports)
    result = tuple(
        tuple(_q_from_schema(value, "boundary relation coefficient") for value in row)
        for row in rows
    )
    if any(len(row) != width for row in result) or _q_rref(result, width) != result:
        raise ValueError("boundary relation rows are not verifier-canonical Q(i) RREF")
    return result


def _canonical_form_matches(
    diagram: OpenDiagram, labels: tuple[str | None, ...], candidate: object, budget: int
) -> bool:
    if type(candidate) is not CanonicalDiagram:
        return False
    if (
        getattr(candidate, "dom", None) != diagram.dom
        or getattr(candidate, "cod", None) != diagram.cod
    ):
        return False
    kinds, inputs, outputs, edges = (
        getattr(candidate, "node_kinds", None),
        getattr(candidate, "input_nodes", None),
        getattr(candidate, "output_nodes", None),
        getattr(candidate, "edges", None),
    )
    count = len(diagram.node_kinds)
    if (
        type(kinds) is not tuple
        or len(kinds) != count
        or type(inputs) is not tuple
        or type(outputs) is not tuple
        or type(edges) is not tuple
        or len(inputs) != len(diagram.input_nodes)
        or len(outputs) != len(diagram.output_nodes)
        or len(edges) != len(diagram.structural_edges())
    ):
        return False
    if any(type(node) is not int or not 0 <= node < count for node in inputs + outputs):
        return False
    normalized: list[tuple[str, str | None, int, int]] = []
    for edge in edges:
        if type(edge) is not tuple or len(edge) != 4:
            return False
        kind, label, left, right = edge
        if (
            type(kind) is not str
            or (label is not None and type(label) is not str)
            or type(left) is not int
            or type(right) is not int
            or not 0 <= left <= right < count
        ):
            return False
        normalized.append((kind, label, left, right))
    if tuple(sorted(normalized)) != edges:
        return False
    source_marks = [[] for _ in range(count)]
    target_marks = [[] for _ in range(count)]
    for index, node in enumerate(diagram.input_nodes):
        source_marks[node].append(("input", index))
    for index, node in enumerate(diagram.output_nodes):
        source_marks[node].append(("output", index))
    for index, node in enumerate(inputs):
        target_marks[node].append(("input", index))
    for index, node in enumerate(outputs):
        target_marks[node].append(("output", index))
    source_incident = [[] for _ in range(count)]
    target_incident = [[] for _ in range(count)]
    for edge, label in zip(diagram.structural_edges(), labels):
        item = (edge.kind.value, label, edge.node_a == edge.node_b)
        source_incident[edge.node_a].append(item)
        source_incident[edge.node_b].append(item)
    for kind, label, left, right in normalized:
        item = (kind, label, left == right)
        target_incident[left].append(item)
        target_incident[right].append(item)
    choices = {
        source: tuple(
            target
            for target in range(count)
            if kinds[target] is diagram.node_kinds[source]
            and tuple(sorted(target_marks[target]))
            == tuple(sorted(source_marks[source]))
            and tuple(sorted(target_incident[target]))
            == tuple(sorted(source_incident[source]))
        )
        for source in range(count)
    }
    if any(not value for value in choices.values()):
        return False
    order, mapping, used, attempts = (
        tuple(sorted(range(count), key=lambda node: (len(choices[node]), node))),
        {},
        set(),
        [0],
    )
    expected = Counter(normalized)

    def search(position: int) -> bool:
        if position == len(order):
            return (
                Counter(
                    (
                        edge.kind.value,
                        label,
                        min(mapping[edge.node_a], mapping[edge.node_b]),
                        max(mapping[edge.node_a], mapping[edge.node_b]),
                    )
                    for edge, label in zip(diagram.structural_edges(), labels)
                )
                == expected
            )
        source = order[position]
        for target in choices[source]:
            if target in used:
                continue
            attempts[0] += 1
            if attempts[0] > budget:
                raise ValueError("canonical-form direct-verification budget exceeded")
            mapping[source] = target
            used.add(target)
            if search(position + 1):
                return True
            used.remove(target)
            del mapping[source]
        return False

    return search(0)


def _connected(
    diagram: OpenDiagram, positive: int, negative: int, reference: int
) -> bool:
    adjacency = [set() for _ in diagram.node_kinds]
    for edge in diagram.structural_edges():
        adjacency[edge.node_a].add(edge.node_b)
        adjacency[edge.node_b].add(edge.node_a)
    adjacency[positive].add(negative)
    adjacency[negative].add(positive)
    reached, todo = {reference}, [reference]
    while todo:
        node = todo.pop()
        for neighbour in adjacency[node]:
            if neighbour not in reached:
                reached.add(neighbour)
                todo.append(neighbour)
    return len(reached) == len(adjacency)


def _exact_mna(
    diagram: OpenDiagram,
    components: tuple[RLCComponent, ...],
    omega: Fraction,
    reference: int,
    positive: int,
    negative: int,
) -> tuple[tuple[tuple[_Q, ...], ...], tuple[int, ...], Fraction]:
    unknown = tuple(
        index for index in range(len(diagram.node_kinds)) if index != reference
    )
    local = {node: index for index, node in enumerate(unknown)}
    scale = _impedance_scale(components, omega)
    dimension = len(unknown) + 1
    matrix = [[_ZERO for _ in range(dimension)] for _ in range(dimension)]
    for edge, component in zip(diagram.structural_edges(), components):
        y = _q_mul(_admittance(component, omega), _q(scale))
        a, b = edge.node_a, edge.node_b
        if a != reference:
            matrix[local[a]][local[a]] = _q_add(matrix[local[a]][local[a]], y)
        if b != reference:
            matrix[local[b]][local[b]] = _q_add(matrix[local[b]][local[b]], y)
        if a != reference and b != reference:
            matrix[local[a]][local[b]] = _q_sub(matrix[local[a]][local[b]], y)
            matrix[local[b]][local[a]] = _q_sub(matrix[local[b]][local[a]], y)
    source = len(unknown)
    if positive != reference:
        matrix[local[positive]][source] = _q_add(matrix[local[positive]][source], _ONE)
        matrix[source][local[positive]] = _q_add(matrix[source][local[positive]], _ONE)
    if negative != reference:
        matrix[local[negative]][source] = _q_sub(matrix[local[negative]][source], _ONE)
        matrix[source][local[negative]] = _q_sub(matrix[source][local[negative]], _ONE)
    return tuple(tuple(row) for row in matrix), unknown, scale


def _finite_phasor(value: object, name: str) -> complex:
    if type(value) is not Phasor:
        raise TypeError(f"{name} must be an exact finite Phasor")
    real, imag = getattr(value, "real", None), getattr(value, "imag", None)
    if (
        isinstance(real, bool)
        or isinstance(imag, bool)
        or not isinstance(real, (int, float))
        or not isinstance(imag, (int, float))
    ):
        raise TypeError(f"{name} has non-real coordinates")
    result = complex(float(real), float(imag))
    if not isfinite(result.real) or not isfinite(result.imag):
        raise ValueError(f"{name} must be finite")
    return result


def _close(
    actual: complex | float, expected: complex | float, scale: float, tolerance: float
) -> bool:
    allowance = max(
        128.0 * sys.float_info.epsilon * max(1.0, scale),
        tolerance * max(1.0, scale) / 16.0,
    )
    return abs(actual - expected) <= allowance


def _relation_residual(
    rows: tuple[tuple[_Q, ...], ...], values: Sequence[complex]
) -> tuple[float, float]:
    raw = scaled = 0.0
    for row in rows:
        terms = [
            _q_to_complex(coefficient) * value
            for coefficient, value in zip(row, values)
        ]
        residual = abs(sum(terms))
        raw = max(raw, residual)
        scaled = max(scaled, residual / max(1e-30, sum(abs(term) for term in terms)))
    return raw, scaled


def _decoration(component: RLCComponent) -> str:
    unit = {
        ElementKind.RESISTOR: "ohm",
        ElementKind.INDUCTOR: "H",
        ElementKind.CAPACITOR: "F",
    }[component.kind]
    value = _component_value(component, "component")
    return f"{component.kind.value}:{value.numerator}/{value.denominator} {unit}"


def direct_preflight(subject: object) -> DirectACVerificationReport:
    """Refuse malformed, floating, singular, or non-finite finite-frequency subjects."""
    if type(subject) is not RLCACSubject:
        return _report(
            DirectACVerificationDecision.REFUSE,
            ("subject is not an exact RLCACSubject",),
        )
    diagram, model, experiment = (
        getattr(subject, "diagram", None),
        getattr(subject, "model", None),
        getattr(subject, "experiment", None),
    )
    reasons: list[str] = []
    if type(diagram) is not OpenDiagram:
        reasons.append("subject does not retain an exact OpenDiagram")
    if type(model) is not RLCModel:
        reasons.append("subject model has the wrong exact RLCModel type")
    if type(experiment) is not ACSolveSpec:
        reasons.append("subject experiment has the wrong exact ACSolveSpec type")
    if reasons:
        return _report(DirectACVerificationDecision.REFUSE, reasons)
    edges = diagram.structural_edges()
    if getattr(model, "presentation_digest", None) != canonical_digest(diagram):
        reasons.append("model presentation digest does not bind the approved diagram")
    try:
        components = _structural_components(model, len(edges))
        omega_record = getattr(experiment, "omega", None)
        if type(omega_record) is not PositiveAngularFrequency:
            raise TypeError("experiment omega has the wrong exact type")
        omega = _fraction(getattr(omega_record, "radians_per_second", None), "omega")
        if omega <= 0:
            raise ValueError("omega must be positive")
        scale = _impedance_scale(components, omega)
        if not isfinite(float(scale)) or float(scale) <= 0:
            reasons.append("normalized impedance is not finite and positive")
    except (OverflowError, TypeError, ValueError) as error:
        reasons.append(str(error))
        components = ()
        omega = Fraction(1)
    drive, reference = (
        getattr(experiment, "drive", None),
        getattr(experiment, "reference", None),
    )
    if type(drive) is not ACVoltageDrive:
        reasons.append("subject drive has the wrong exact ACVoltageDrive type")
    if type(reference) is not BoundaryRef:
        reasons.append("reference must be an exact BoundaryRef")
    if not reasons:
        try:
            positive_ref, negative_ref = drive.positive, drive.negative
            if (
                type(positive_ref) is not BoundaryRef
                or type(negative_ref) is not BoundaryRef
            ):
                raise TypeError("drive terminals must be exact BoundaryRefs")
            reference_node, positive_node, negative_node = (
                diagram.node_for(reference),
                diagram.node_for(positive_ref),
                diagram.node_for(negative_ref),
            )
            if positive_node == negative_node:
                reasons.append("drive terminals collapse to one structural node")
            if not diagram.node_kinds:
                reasons.append("driven analysis requires at least one structural node")
            elif not _connected(diagram, positive_node, negative_node, reference_node):
                reasons.append(
                    "one or more structural nodes are reference-disconnected"
                )
            _q_from_schema(drive.volts_rms, "drive.volts_rms")
            matrix, _, _ = _exact_mna(
                diagram, components, omega, reference_node, positive_node, negative_node
            )
            if len(_q_rref(matrix, len(matrix))) != len(matrix):
                reasons.append(
                    "exact driven MNA is rank deficient; singular resonance is refused without regularization"
                )
        except (OverflowError, TypeError, ValueError) as error:
            reasons.append(str(error))
    tolerance, limit, dimension_limit = (
        getattr(experiment, "scaled_tolerance", None),
        getattr(experiment, "conditioning_limit", None),
        getattr(experiment, "conditioning_dimension_limit", None),
    )
    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not isfinite(float(tolerance))
        or not 0 < float(tolerance) < 1
    ):
        reasons.append("scaled tolerance must be finite and in (0,1)")
    if (
        isinstance(limit, bool)
        or not isinstance(limit, (int, float))
        or not isfinite(float(limit))
        or float(limit) < 1
    ):
        reasons.append("conditioning limit must be finite and at least one")
    if type(dimension_limit) is not int or dimension_limit < 1:
        reasons.append("conditioning dimension limit must be a positive exact int")
    if reasons:
        return _report(DirectACVerificationDecision.REFUSE, reasons)
    return _report(
        DirectACVerificationDecision.PASS,
        (
            "subject is inside the finite positive-frequency passive RLC verification domain",
        ),
        inventory_ok=True,
        exact_mna_rank_ok=True,
    )


def verify_rlc_ac_analysis(
    subject: object, analysis: object
) -> DirectACVerificationReport:
    """Check a retained RLC result without invoking any production AC computation."""
    preflight = direct_preflight(subject)
    if not preflight.passed:
        return preflight
    if type(analysis) is not RLCACAnalysis:
        return _report(
            DirectACVerificationDecision.FAIL,
            ("candidate is not an exact RLCACAnalysis",),
            exact_mna_rank_ok=True,
        )
    diagram, model, experiment = subject.diagram, subject.model, subject.experiment
    tolerance, edges = float(experiment.scaled_tolerance), diagram.structural_edges()
    components = _structural_components(model, len(edges))
    omega = _fraction(experiment.omega.radians_per_second, "omega")
    reasons: list[str] = []
    bindings = getattr(analysis, "model_edge_bindings", None)
    approved_bindings = tuple(
        (binding.model_index, binding.structural_edge_index)
        for binding in model.edge_bindings
    )
    binding_ok = (
        type(bindings) is tuple
        and all(type(binding) is RLCEdgeBinding for binding in bindings)
        and tuple(
            (binding.model_index, binding.structural_edge_index) for binding in bindings
        )
        == approved_bindings
    )
    if not binding_ok:
        reasons.append(
            "analysis does not retain the approved model-to-structure edge bindings"
        )
    labels = tuple(_decoration(component) for component in components)
    try:
        structural = getattr(analysis, "structural_canonical_form", None)
        decorated = getattr(analysis, "decorated_model_canonical_form", None)
        canonical_forms_ok = _canonical_form_matches(
            diagram, (None,) * len(edges), structural, subject.canonicalization_budget
        ) and _canonical_form_matches(
            diagram, labels, decorated, subject.canonicalization_budget
        )
    except ValueError as error:
        canonical_forms_ok = False
        reasons.append(str(error))
    if not canonical_forms_ok:
        reasons.append(
            "structural or decorated canonical form differs from the approved topology/model"
        )
    try:
        expected_rows = _expected_relation(diagram, components, omega)
        relation_ok = (
            _candidate_relation(
                getattr(analysis, "boundary_relation", None),
                len(diagram.dom.ports),
                len(diagram.cod.ports),
            )
            == expected_rows
        )
        if not relation_ok:
            reasons.append(
                "exact Q(i) boundary relation differs from verifier elimination"
            )
    except (TypeError, ValueError) as error:
        expected_rows = ()
        relation_ok = False
        reasons.append(f"exact boundary relation is invalid: {error}")
    reference, positive, negative = (
        diagram.node_for(experiment.reference),
        diagram.node_for(experiment.drive.positive),
        diagram.node_for(experiment.drive.negative),
    )
    matrix, unknown, scale_fraction = _exact_mna(
        diagram, components, omega, reference, positive, negative
    )
    exact_mna_rank_ok = len(_q_rref(matrix, len(matrix))) == len(matrix)
    if not exact_mna_rank_ok:
        reasons.append("verifier exact driven-MNA rank is deficient")
    result = getattr(analysis, "sparse_solution", None)
    if type(result) is not ACSolveResult:
        return _report(
            DirectACVerificationDecision.FAIL,
            reasons + ["candidate does not retain an exact ACSolveResult"],
            canonical_forms_ok=canonical_forms_ok,
            exact_relation_ok=relation_ok,
            exact_mna_rank_ok=exact_mna_rank_ok,
        )
    nodes, branches, source, retained_mna, retained_diagnostics = (
        result.nodes,
        result.branches,
        result.source,
        result.mna_state,
        result.diagnostics,
    )
    inventory_ok = (
        binding_ok
        and len(nodes) == len(diagram.node_kinds)
        and len(branches) == len(edges)
        and type(source) is ACSourceObservation
        and type(retained_mna) is MNAState
    )
    if not inventory_ok:
        reasons.append(
            "node, branch, source, or MNA inventory is incomplete or has the wrong type"
        )
    voltages: dict[int, complex] = {}
    for index, node in enumerate(nodes):
        if type(node) is not NodePhasor or getattr(node, "node_index", None) != index:
            inventory_ok = False
            reasons.append("node records are not exact ordered NodePhasor values")
            continue
        try:
            voltages[index] = _finite_phasor(node.volts_rms, f"node[{index}].volts_rms")
        except (TypeError, ValueError) as error:
            inventory_ok = False
            reasons.append(str(error))
    try:
        if (
            retained_mna.unknown_node_indices != unknown
            or retained_mna.source_current_index != len(unknown)
            or not _close(
                float(retained_mna.normalized_impedance_ohms),
                float(scale_fraction),
                max(float(scale_fraction), 1.0),
                tolerance,
            )
        ):
            inventory_ok = False
            reasons.append(
                "retained MNA state does not declare the verifier-derived normalization/indexing"
            )
        mna_solution = tuple(
            _finite_phasor(value, f"mna.solution[{index}]")
            for index, value in enumerate(retained_mna.solution)
        )
    except (TypeError, ValueError) as error:
        inventory_ok = False
        mna_solution = ()
        reasons.append(str(error))
    branch_law_ok = inventory_ok
    currents: list[complex] = []
    powers: list[complex] = []
    kcl = [0j for _ in diagram.node_kinds]
    for index, (branch, edge, component) in enumerate(zip(branches, edges, components)):
        if (
            type(branch) is not RLCBranch
            or branch.branch_index != index
            or branch.node_a != edge.node_a
            or branch.node_b != edge.node_b
            or branch.component != component
        ):
            inventory_ok = False
            branch_law_ok = False
            reasons.append(
                f"branch[{index}] does not retain its approved structural component"
            )
            continue
        try:
            drop, current, power = (
                _finite_phasor(
                    branch.voltage_drop_rms, f"branch[{index}].voltage_drop_rms"
                ),
                _finite_phasor(
                    branch.current_amperes_rms, f"branch[{index}].current_amperes_rms"
                ),
                _finite_phasor(
                    branch.absorbed_power_va, f"branch[{index}].absorbed_power_va"
                ),
            )
            expected_drop = voltages[edge.node_a] - voltages[edge.node_b]
            expected_current = (
                _q_to_complex(_admittance(component, omega)) * expected_drop
            )
            expected_power = expected_drop * expected_current.conjugate()
            if not _close(
                drop, expected_drop, max(abs(drop), abs(expected_drop), 1.0), tolerance
            ):
                branch_law_ok = False
                reasons.append(f"branch[{index}] voltage violates retained node values")
            if not _close(
                current,
                expected_current,
                max(abs(current), abs(expected_current), 1e-30),
                tolerance,
            ):
                branch_law_ok = False
                reasons.append(
                    f"branch[{index}] current violates its exact one-frequency admittance"
                )
            if not _close(
                power,
                expected_power,
                max(abs(power), abs(expected_power), 1e-30),
                tolerance,
            ):
                branch_law_ok = False
                reasons.append(f"branch[{index}] complex power violates V*conj(I)")
            currents.append(expected_current)
            powers.append(expected_power)
            kcl[edge.node_a] += expected_current
            kcl[edge.node_b] -= expected_current
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            branch_law_ok = False
            reasons.append(str(error))
    source_constraint_ok, source_current, source_power = inventory_ok, 0j, 0j
    try:
        if source.positive_node != positive or source.negative_node != negative:
            source_constraint_ok = False
            reasons.append("source nodes differ from the approved drive")
        drive = _q_to_complex(
            _q_from_schema(experiment.drive.volts_rms, "drive.volts_rms")
        )
        source_volts, source_current, source_power = (
            _finite_phasor(source.volts_rms, "source.volts_rms"),
            _finite_phasor(
                source.current_entering_positive_amperes_rms,
                "source.current_entering_positive_amperes_rms",
            ),
            _finite_phasor(source.absorbed_power_va, "source.absorbed_power_va"),
        )
        voltage_scale = max(
            1.0, abs(drive), *(abs(value) for value in voltages.values())
        )
        if not _close(source_volts, drive, voltage_scale, tolerance) or not _close(
            voltages[positive] - voltages[negative], drive, voltage_scale, tolerance
        ):
            source_constraint_ok = False
            reasons.append(
                "source voltage/sign constraint differs from the approved drive"
            )
        if not _close(voltages[reference], 0j, voltage_scale, tolerance):
            source_constraint_ok = False
            reasons.append("declared reference node is not zero")
        if not _close(
            source_power,
            drive * source_current.conjugate(),
            max(abs(source_power), abs(drive * source_current.conjugate()), 1e-30),
            tolerance,
        ):
            source_constraint_ok = False
            reasons.append("source complex power violates V*conj(I)")
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        source_constraint_ok = False
        reasons.append(str(error))
    kcl[positive] += source_current
    kcl[negative] -= source_current
    kcl_residual = max((abs(value) for value in kcl), default=0.0)
    current_scale = max(1e-30, abs(source_current), *(abs(value) for value in currents))
    scaled_kcl = kcl_residual / current_scale
    kcl_ok = inventory_ok and branch_law_ok and scaled_kcl <= tolerance
    if not kcl_ok:
        reasons.append("nodewise complex KCL exceeds the approved scaled tolerance")
    drive = _q_to_complex(_q_from_schema(experiment.drive.volts_rms, "drive.volts_rms"))
    constraint_residual = abs(
        voltages.get(positive, complex(float("inf")))
        - voltages.get(negative, complex(float("inf")))
        - drive
    )
    voltage_scale = max(1.0, abs(drive), *(abs(value) for value in voltages.values()))
    scaled_constraint = constraint_residual / voltage_scale
    power_residual = abs(sum(powers) + source_power)
    power_scale = max(1e-30, abs(source_power), *(abs(value) for value in powers))
    scaled_power = power_residual / power_scale
    resistor_real = [
        power.real
        for component, power in zip(components, powers)
        if component.kind is ElementKind.RESISTOR
    ]
    reactive_real = [
        abs(power.real)
        for component, power in zip(components, powers)
        if component.kind is not ElementKind.RESISTOR
    ]
    minimum_resistor = min(resistor_real, default=0.0)
    maximum_reactive = max(reactive_real, default=0.0)
    passivity_ok = (
        inventory_ok
        and branch_law_ok
        and all(value >= -tolerance * power_scale for value in resistor_real)
        and all(value <= tolerance * power_scale for value in reactive_real)
    )
    power_ok = passivity_ok and scaled_power <= tolerance
    if not passivity_ok:
        reasons.append(
            "one-frequency R/L/C passivity or ideal reactive real-power gate failed"
        )
    if not power_ok:
        reasons.append(
            "global source-inclusive complex-power balance exceeds tolerance"
        )
    refs = _refs(diagram)
    boundary_currents = [0j for _ in refs]
    for index, ref in enumerate(refs):
        if ref == experiment.drive.positive:
            boundary_currents[index] -= source_current
        if ref == experiment.drive.negative:
            boundary_currents[index] += source_current
    relation_residual, scaled_relation = _relation_residual(
        expected_rows,
        [voltages.get(diagram.node_for(ref), complex(float("inf"))) for ref in refs]
        + boundary_currents,
    )
    relation_numeric_ok = scaled_relation <= tolerance
    if not relation_numeric_ok:
        reasons.append("numerical boundary witness violates the verifier Q(i) relation")
    dense = np.array(
        [[_q_to_complex(value) for value in row] for row in matrix], dtype=complex
    )
    try:
        exact_drive = _q_to_complex(
            _q_from_schema(experiment.drive.volts_rms, "drive.volts_rms")
        )
        rhs = np.zeros(len(matrix), dtype=complex)
        rhs[-1] = exact_drive
        vector = np.array(mna_solution, dtype=complex)
        condition = float(np.linalg.cond(dense))
        backward = float(
            np.linalg.norm(dense @ vector - rhs, ord=np.inf)
            / max(
                1e-30,
                float(np.linalg.norm(dense, ord=np.inf))
                * float(np.linalg.norm(vector, ord=np.inf))
                + float(np.linalg.norm(rhs, ord=np.inf)),
            )
        )
    except (ValueError, np.linalg.LinAlgError) as error:
        condition = float("inf")
        backward = float("inf")
        reasons.append(f"independent conditioning/backward computation failed: {error}")
    mna_ok = (
        inventory_ok
        and len(mna_solution) == len(matrix)
        and isfinite(condition)
        and condition <= float(experiment.conditioning_limit)
        and backward <= tolerance
    )
    if not mna_ok:
        reasons.append(
            "retained MNA state fails condition declaration or independent backward residual"
        )
    diagnostics = DirectACDiagnostics(
        kcl_residual,
        constraint_residual,
        power_residual,
        relation_residual,
        backward,
        scaled_kcl,
        scaled_constraint,
        scaled_power,
        scaled_relation,
        condition,
        minimum_resistor,
        maximum_reactive,
    )
    diagnostics_ok = type(retained_diagnostics) is ACCircuitDiagnostics
    if diagnostics_ok:
        for name, expected in vars(diagnostics).items():
            try:
                actual = getattr(retained_diagnostics, name)
                if (
                    isinstance(actual, bool)
                    or not isinstance(actual, (int, float))
                    or not isfinite(float(actual))
                    or not _close(
                        float(actual),
                        expected,
                        max(abs(expected), abs(float(actual)), 1.0),
                        tolerance,
                    )
                ):
                    diagnostics_ok = False
                    reasons.append(
                        f"diagnostics.{name} differs from direct recomputation"
                    )
            except (AttributeError, TypeError, ValueError):
                diagnostics_ok = False
                reasons.append(f"diagnostics.{name} is not a finite scalar")
    else:
        reasons.append("candidate diagnostics have the wrong exact type")
    all_gates = (
        canonical_forms_ok
        and inventory_ok
        and relation_ok
        and relation_numeric_ok
        and exact_mna_rank_ok
        and branch_law_ok
        and kcl_ok
        and source_constraint_ok
        and power_ok
        and passivity_ok
        and mna_ok
        and diagnostics_ok
    )
    maximum_scaled = max(
        scaled_kcl, scaled_constraint, scaled_power, scaled_relation, backward
    )
    if all_gates and maximum_scaled <= tolerance / 8.0:
        decision = DirectACVerificationDecision.PASS
        reasons.append("all independent E2 gates pass with certification margin")
    elif all_gates and maximum_scaled <= tolerance:
        decision = DirectACVerificationDecision.AMBIGUOUS
        reasons.append(
            "residuals pass solver tolerance but not verifier certification margin"
        )
    else:
        decision = DirectACVerificationDecision.FAIL
    return _report(
        decision,
        reasons,
        canonical_forms_ok=canonical_forms_ok,
        inventory_ok=inventory_ok,
        exact_relation_ok=relation_ok and relation_numeric_ok,
        exact_mna_rank_ok=exact_mna_rank_ok,
        branch_law_ok=branch_law_ok,
        kcl_ok=kcl_ok,
        source_constraint_ok=source_constraint_ok,
        power_ok=power_ok,
        passivity_ok=passivity_ok,
        diagnostics=diagnostics,
    )
