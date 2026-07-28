"""Production-independent verifier for the finite ideal-resistor DC control.

This module deliberately imports neither :mod:`smartchem.circuit` nor
:mod:`smartchem.resistive_dc`.  It shares only immutable nominal records from
:mod:`smartchem.resistive_dc_schema`; it does not call the production sparse assembler,
solver, exact-relation builder, analysis function, or their row-reduction helpers.  It
traverses the public open-diagram presentation and retained result fields, re-derives
the exact boundary relation with verifier-local ``Fraction`` elimination, and evaluates
Ohm's law, KCL, the source constraint, passivity, and power balance directly.

The verifier certifies consistency only for the declared finite positive ideal-resistor
model and numerical tolerance.  It says nothing about hardware, parasitics, AC/RLC,
thermal behaviour, or forward error outside the accepted residual regime.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from math import isfinite
import sys
from typing import Iterable, Sequence

from .contracts import canonical_digest
from .open_diagram import (
    BoundaryRef,
    BoundarySide,
    CanonicalDiagram,
    OpenDiagram,
    canonicalize,
)
from .resistive_dc_schema import (
    BoundaryLinearRelation,
    CircuitDiagnostics,
    DCSolveResult,
    DCSolveSpec,
    DCVoltageDrive,
    NodeVoltage,
    PositiveResistance,
    Rational,
    ResistiveDCAnalysis,
    ResistiveDCModel,
    ResistiveDCSubject,
    ResistorBranch,
    ResistorEdgeBinding,
    SourceObservation,
)

__all__ = [
    "DirectCircuitDiagnostics",
    "DirectVerificationDecision",
    "DirectVerificationReport",
    "direct_preflight",
    "verify_resistive_dc_analysis",
]


class DirectVerificationDecision(str, Enum):
    PASS = "pass"
    REFUSE = "refuse"
    FAIL = "fail"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class DirectCircuitDiagnostics:
    """Verifier-local, dimension-separated residuals and scales."""

    kcl_residual_amperes: float
    constraint_residual_volts: float
    power_residual_watts: float
    relation_residual: float
    scaled_kcl_residual: float
    scaled_constraint_residual: float
    scaled_power_residual: float
    scaled_relation_residual: float


@dataclass(frozen=True)
class DirectVerificationReport:
    """One fail-closed independent-verification decision."""

    decision: DirectVerificationDecision
    canonical_forms_ok: bool
    inventory_ok: bool
    exact_relation_ok: bool
    branch_law_ok: bool
    kcl_ok: bool
    source_constraint_ok: bool
    power_ok: bool
    passivity_ok: bool
    diagnostics: DirectCircuitDiagnostics
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.decision is DirectVerificationDecision.PASS


_ZERO_DIAGNOSTICS = DirectCircuitDiagnostics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def _report(
    decision: DirectVerificationDecision,
    reasons: Iterable[str],
    *,
    canonical_forms_ok: bool = False,
    inventory_ok: bool = False,
    exact_relation_ok: bool = False,
    branch_law_ok: bool = False,
    kcl_ok: bool = False,
    source_constraint_ok: bool = False,
    power_ok: bool = False,
    passivity_ok: bool = False,
    diagnostics: DirectCircuitDiagnostics = _ZERO_DIAGNOSTICS,
) -> DirectVerificationReport:
    return DirectVerificationReport(
        decision,
        canonical_forms_ok,
        inventory_ok,
        exact_relation_ok,
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
        raise TypeError(f"{name} has the wrong exact rational type")
    numerator = getattr(value, "numerator", None)
    denominator = getattr(value, "denominator", None)
    if type(numerator) is not int or type(denominator) is not int or denominator == 0:
        raise TypeError(f"{name} is not an exact rational record")
    return Fraction(numerator, denominator)


def _resistance_fraction(value: object, name: str) -> Fraction:
    if type(value) is not PositiveResistance:
        raise TypeError(f"{name} has the wrong exact resistance type")
    result = _fraction(getattr(value, "ohms", None), f"{name}.ohms")
    if result <= 0:
        raise ValueError(f"{name} must be strictly positive")
    return result


def _structural_resistances(
    model: object,
    edge_count: int,
) -> tuple[Fraction, ...]:
    """Independently apply the retained model-to-structure reindex witness."""
    if type(model) is not ResistiveDCModel:
        raise TypeError("model has the wrong exact ResistiveDCModel type")
    resistances = getattr(model, "resistances", None)
    bindings = getattr(model, "edge_bindings", None)
    if type(resistances) is not tuple or len(resistances) != edge_count:
        raise ValueError("resistance inventory does not match the structural-edge inventory")
    if type(bindings) is not tuple or len(bindings) != edge_count:
        raise ValueError("edge-binding witness does not cover every model parameter")
    ordered: list[Fraction | None] = [None] * edge_count
    model_indices: list[int] = []
    structural_indices: list[int] = []
    for position, binding in enumerate(bindings):
        if type(binding) is not ResistorEdgeBinding:
            raise TypeError(f"edge binding {position} has the wrong exact type")
        model_index = getattr(binding, "model_index", None)
        structural_index = getattr(binding, "structural_edge_index", None)
        if type(model_index) is not int or type(structural_index) is not int:
            raise TypeError("edge-binding indices must be exact ints")
        if not 0 <= model_index < edge_count or not 0 <= structural_index < edge_count:
            raise ValueError("edge-binding index is outside the finite inventories")
        model_indices.append(model_index)
        structural_indices.append(structural_index)
        ordered[structural_index] = _resistance_fraction(
            resistances[model_index],
            f"resistance[{model_index}]",
        )
    if sorted(model_indices) != list(range(edge_count)):
        raise ValueError("edge bindings do not cover model indices exactly once")
    if sorted(structural_indices) != list(range(edge_count)):
        raise ValueError("edge bindings do not cover structural indices exactly once")
    if any(value is None for value in ordered):  # pragma: no cover - checked above
        raise ValueError("edge binding left one structural edge unparameterized")
    return tuple(value for value in ordered if value is not None)


def _boundary_refs(diagram: OpenDiagram) -> tuple[BoundaryRef, ...]:
    return tuple(
        BoundaryRef(BoundarySide.INPUT, index)
        for index in range(len(diagram.dom.ports))
    ) + tuple(
        BoundaryRef(BoundarySide.OUTPUT, index)
        for index in range(len(diagram.cod.ports))
    )


def _row_reduce(
    rows: Iterable[Sequence[Fraction]],
    width: int,
) -> tuple[tuple[Fraction, ...], ...]:
    """Verifier-local canonical Gauss-Jordan elimination over exact fractions."""
    work = [list(row) for row in rows]
    if any(len(row) != width for row in work):
        raise ValueError("verifier relation row has the wrong width")
    active = 0
    for column in range(width):
        pivot = None
        for row_index in range(active, len(work)):
            if work[row_index][column]:
                pivot = row_index
                break
        if pivot is None:
            continue
        if pivot != active:
            work[active], work[pivot] = work[pivot], work[active]
        divisor = work[active][column]
        work[active] = [entry / divisor for entry in work[active]]
        for row_index, row in enumerate(work):
            if row_index == active:
                continue
            multiplier = row[column]
            if multiplier:
                work[row_index] = [
                    entry - multiplier * pivot_entry
                    for entry, pivot_entry in zip(row, work[active])
                ]
        active += 1
        if active == len(work):
            break
    return tuple(tuple(row) for row in work if any(row))


def _expected_relation(
    diagram: OpenDiagram,
    resistance_values: tuple[Fraction, ...],
) -> tuple[tuple[Fraction, ...], ...]:
    """Eliminate internal node potentials through an independent exact path."""
    node_count = len(diagram.node_kinds)
    edges = diagram.structural_edges()
    refs = _boundary_refs(diagram)
    boundary_count = len(refs)
    total_width = node_count + 2 * boundary_count
    equations: list[list[Fraction]] = []

    laplacian = [
        [Fraction(0) for _ in range(node_count)]
        for _ in range(node_count)
    ]
    for edge, resistance in zip(edges, resistance_values):
        conductance = Fraction(1, 1) / resistance
        a, b = edge.node_a, edge.node_b
        laplacian[a][a] += conductance
        laplacian[b][b] += conductance
        laplacian[a][b] -= conductance
        laplacian[b][a] -= conductance

    for node_index in range(node_count):
        row = [Fraction(0) for _ in range(total_width)]
        row[:node_count] = laplacian[node_index]
        for boundary_index, boundary in enumerate(refs):
            if diagram.node_for(boundary) == node_index:
                row[node_count + boundary_count + boundary_index] -= Fraction(1)
        equations.append(row)

    for boundary_index, boundary in enumerate(refs):
        row = [Fraction(0) for _ in range(total_width)]
        row[diagram.node_for(boundary)] = Fraction(-1)
        row[node_count + boundary_index] = Fraction(1)
        equations.append(row)

    reduced = _row_reduce(equations, total_width)
    external = tuple(
        row[node_count:]
        for row in reduced
        if all(entry == 0 for entry in row[:node_count])
    )
    return _row_reduce(external, 2 * boundary_count)


def _candidate_relation_rows(
    relation: object,
    *,
    dom_ports: int,
    cod_ports: int,
) -> tuple[tuple[Fraction, ...], ...]:
    if type(relation) is not BoundaryLinearRelation:
        raise TypeError("boundary relation has the wrong exact type")
    if (
        getattr(relation, "dom_ports", None) != dom_ports
        or getattr(relation, "cod_ports", None) != cod_ports
    ):
        raise ValueError("boundary relation interface does not match the diagram")
    rows = getattr(relation, "rref_rows", None)
    if type(rows) is not tuple or any(type(row) is not tuple for row in rows):
        raise TypeError("boundary relation rows must be an exact tuple of tuples")
    width = 2 * (dom_ports + cod_ports)
    converted = tuple(
        tuple(_fraction(entry, "boundary relation coefficient") for entry in row)
        for row in rows
    )
    if any(len(row) != width for row in converted):
        raise ValueError("boundary relation row has the wrong width")
    if _row_reduce(converted, width) != converted:
        raise ValueError("boundary relation rows are not verifier-canonical")
    return converted


def _canonical_form_matches(
    diagram: OpenDiagram,
    labels: tuple[str | None, ...],
    candidate: object,
    *,
    budget: int,
) -> bool:
    """Validate canonical output content through verifier-local graph isomorphism.

    The S0 canonicalizer owns the choice of canonical numbering.  This local check first
    proves that the retained form is a sorted, label-preserving, boundary-preserving
    presentation; the enclosing verifier then requires equality with the exact S0
    canonicalizer output.
    """
    if type(candidate) is not CanonicalDiagram:
        return False
    if getattr(candidate, "dom", None) != diagram.dom:
        return False
    if getattr(candidate, "cod", None) != diagram.cod:
        return False
    candidate_kinds = getattr(candidate, "node_kinds", None)
    candidate_inputs = getattr(candidate, "input_nodes", None)
    candidate_outputs = getattr(candidate, "output_nodes", None)
    candidate_edges = getattr(candidate, "edges", None)
    node_count = len(diagram.node_kinds)
    if (
        type(candidate_kinds) is not tuple
        or len(candidate_kinds) != node_count
        or type(candidate_inputs) is not tuple
        or type(candidate_outputs) is not tuple
        or len(candidate_inputs) != len(diagram.input_nodes)
        or len(candidate_outputs) != len(diagram.output_nodes)
        or type(candidate_edges) is not tuple
        or len(candidate_edges) != len(diagram.structural_edges())
        or len(labels) != len(diagram.structural_edges())
    ):
        return False
    if any(type(node) is not int or not 0 <= node < node_count for node in candidate_inputs):
        return False
    if any(type(node) is not int or not 0 <= node < node_count for node in candidate_outputs):
        return False
    normalized_candidate_edges: list[tuple[str, str | None, int, int]] = []
    for edge in candidate_edges:
        if type(edge) is not tuple or len(edge) != 4:
            return False
        kind, label, node_a, node_b = edge
        if type(kind) is not str or (label is not None and type(label) is not str):
            return False
        if (
            type(node_a) is not int
            or type(node_b) is not int
            or not 0 <= node_a < node_count
            or not 0 <= node_b < node_count
            or node_a > node_b
        ):
            return False
        normalized_candidate_edges.append((kind, label, node_a, node_b))
    if tuple(sorted(normalized_candidate_edges)) != candidate_edges:
        return False

    source_markers: list[list[tuple[str, int]]] = [[] for _ in range(node_count)]
    target_markers: list[list[tuple[str, int]]] = [[] for _ in range(node_count)]
    for index, node in enumerate(diagram.input_nodes):
        source_markers[node].append(("input", index))
    for index, node in enumerate(diagram.output_nodes):
        source_markers[node].append(("output", index))
    for index, node in enumerate(candidate_inputs):
        target_markers[node].append(("input", index))
    for index, node in enumerate(candidate_outputs):
        target_markers[node].append(("output", index))

    source_incident: list[list[tuple[str, str | None, bool]]] = [
        [] for _ in range(node_count)
    ]
    for edge, label in zip(diagram.structural_edges(), labels):
        loop = edge.node_a == edge.node_b
        source_incident[edge.node_a].append((edge.kind.value, label, loop))
        source_incident[edge.node_b].append((edge.kind.value, label, loop))
    target_incident: list[list[tuple[str, str | None, bool]]] = [
        [] for _ in range(node_count)
    ]
    for kind, label, node_a, node_b in normalized_candidate_edges:
        loop = node_a == node_b
        target_incident[node_a].append((kind, label, loop))
        target_incident[node_b].append((kind, label, loop))

    choices: dict[int, tuple[int, ...]] = {}
    for source in range(node_count):
        compatible = tuple(
            target
            for target in range(node_count)
            if candidate_kinds[target] is diagram.node_kinds[source]
            and tuple(sorted(target_markers[target]))
            == tuple(sorted(source_markers[source]))
            and tuple(sorted(target_incident[target]))
            == tuple(sorted(source_incident[source]))
        )
        if not compatible:
            return False
        choices[source] = compatible
    order = tuple(sorted(range(node_count), key=lambda node: (len(choices[node]), node)))
    expected_counter = Counter(normalized_candidate_edges)
    mapping: dict[int, int] = {}
    used: set[int] = set()
    attempts = 0

    def search(position: int) -> bool:
        nonlocal attempts
        if position == len(order):
            transformed = Counter(
                (
                    edge.kind.value,
                    label,
                    min(mapping[edge.node_a], mapping[edge.node_b]),
                    max(mapping[edge.node_a], mapping[edge.node_b]),
                )
                for edge, label in zip(diagram.structural_edges(), labels)
            )
            return transformed == expected_counter
        source = order[position]
        for target in choices[source]:
            if target in used:
                continue
            attempts += 1
            if attempts > budget:
                raise ValueError("canonical-form direct-verification budget exceeded")
            mapping[source] = target
            used.add(target)
            if search(position + 1):
                return True
            used.remove(target)
            del mapping[source]
        return False

    return search(0)


def _connected_to_reference(
    diagram: OpenDiagram,
    positive: int,
    negative: int,
    reference: int,
) -> bool:
    adjacency = [set() for _ in diagram.node_kinds]
    for edge in diagram.structural_edges():
        adjacency[edge.node_a].add(edge.node_b)
        adjacency[edge.node_b].add(edge.node_a)
    adjacency[positive].add(negative)
    adjacency[negative].add(positive)
    reached = {reference}
    frontier = [reference]
    while frontier:
        node = frontier.pop()
        for neighbour in adjacency[node]:
            if neighbour not in reached:
                reached.add(neighbour)
                frontier.append(neighbour)
    return len(reached) == len(adjacency)


def direct_preflight(subject: object) -> DirectVerificationReport:
    """Independently reject subjects outside the finite E1 verification domain."""
    reasons: list[str] = []
    if type(subject) is not ResistiveDCSubject:
        return _report(
            DirectVerificationDecision.REFUSE,
            ("subject is not an exact ResistiveDCSubject",),
        )
    diagram = getattr(subject, "diagram", None)
    if type(diagram) is not OpenDiagram:
        return _report(
            DirectVerificationDecision.REFUSE,
            ("subject does not retain an exact OpenDiagram",),
        )
    model = getattr(subject, "model", None)
    experiment = getattr(subject, "experiment", None)
    if type(model) is not ResistiveDCModel:
        reasons.append("subject model has the wrong exact ResistiveDCModel type")
    if type(experiment) is not DCSolveSpec:
        reasons.append("subject experiment has the wrong exact DCSolveSpec type")
        return _report(DirectVerificationDecision.REFUSE, reasons)
    edges = diagram.structural_edges()
    if getattr(model, "presentation_digest", None) != canonical_digest(diagram):
        reasons.append("model presentation digest does not bind the approved diagram")
    try:
        resistance_values = _structural_resistances(model, len(edges))
        for index, exact in enumerate(resistance_values):
            numeric = float(exact)
            if not isfinite(numeric) or numeric <= 0:
                reasons.append(
                    f"resistance[{index}] is not representable as a finite positive float"
                )
    except (OverflowError, TypeError, ValueError) as error:
        reasons.append(str(error))
    reference = getattr(experiment, "reference", None)
    drive = getattr(experiment, "drive", None)
    if type(drive) is not DCVoltageDrive:
        reasons.append("subject drive has the wrong exact DCVoltageDrive type")
        return _report(DirectVerificationDecision.REFUSE, reasons)
    positive_ref = getattr(drive, "positive", None)
    negative_ref = getattr(drive, "negative", None)
    if any(
        type(ref) is not BoundaryRef
        for ref in (reference, positive_ref, negative_ref)
    ):
        reasons.append("reference and drive terminals must be exact boundary references")
        return _report(DirectVerificationDecision.REFUSE, reasons)
    try:
        reference_node = diagram.node_for(reference)
        positive_node = diagram.node_for(positive_ref)
        negative_node = diagram.node_for(negative_ref)
    except (TypeError, ValueError) as error:
        reasons.append(f"boundary resolution failed: {error}")
        return _report(DirectVerificationDecision.REFUSE, reasons)
    if positive_node == negative_node:
        reasons.append("drive terminals collapse to one structural node")
    if not diagram.node_kinds:
        reasons.append("driven analysis requires at least one structural node")
    elif not _connected_to_reference(
        diagram,
        positive_node,
        negative_node,
        reference_node,
    ):
        reasons.append("one or more structural nodes are reference-disconnected")
    try:
        drive_volts = float(_fraction(getattr(drive, "volts", None), "drive.volts"))
        if not isfinite(drive_volts):
            reasons.append("drive voltage is not representable as a finite float")
    except (OverflowError, TypeError, ValueError) as error:
        reasons.append(str(error))
    tolerance = getattr(experiment, "scaled_tolerance", None)
    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not isfinite(float(tolerance))
        or not 0 < float(tolerance) < 1
    ):
        reasons.append("scaled tolerance must be finite and strictly between zero and one")
    if reasons:
        return _report(DirectVerificationDecision.REFUSE, reasons)
    return _report(
        DirectVerificationDecision.PASS,
        ("subject is inside the finite positive ideal-resistor verification domain",),
        inventory_ok=True,
    )


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real scalar")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _field_close(actual: float, expected: float, scale: float, tolerance: float) -> bool:
    allowance = max(
        64.0 * sys.float_info.epsilon * max(1.0, scale),
        tolerance * max(1.0, scale) / 16.0,
    )
    return abs(actual - expected) <= allowance


def _relation_residual(
    rows: tuple[tuple[Fraction, ...], ...],
    values: Sequence[float],
) -> tuple[float, float]:
    raw = 0.0
    scaled = 0.0
    for row in rows:
        terms = [float(coefficient) * value for coefficient, value in zip(row, values)]
        row_residual = abs(sum(terms))
        raw = max(raw, row_residual)
        scaled = max(
            scaled,
            row_residual / max(1e-30, sum(abs(term) for term in terms)),
        )
    return raw, scaled


def verify_resistive_dc_analysis(
    subject: object,
    candidate: object,
) -> DirectVerificationReport:
    """Verify one retained E1 candidate without invoking production computations."""
    preflight = direct_preflight(subject)
    if not preflight.passed:
        return preflight
    if type(candidate) is not ResistiveDCAnalysis:
        return _report(
            DirectVerificationDecision.FAIL,
            ("candidate is not an exact ResistiveDCAnalysis",),
        )

    diagram = subject.diagram
    model = subject.model
    experiment = subject.experiment
    tolerance = float(experiment.scaled_tolerance)
    edges = diagram.structural_edges()
    resistance_values = _structural_resistances(model, len(edges))
    reasons: list[str] = []

    retained_bindings = getattr(candidate, "model_edge_bindings", None)
    approved_binding_pairs = tuple(
        (binding.model_index, binding.structural_edge_index)
        for binding in model.edge_bindings
    )
    binding_ok = not (
        type(retained_bindings) is not tuple
        or any(type(binding) is not ResistorEdgeBinding for binding in retained_bindings)
        or tuple(
            (
                getattr(binding, "model_index", None),
                getattr(binding, "structural_edge_index", None),
            )
            for binding in retained_bindings
        )
        != approved_binding_pairs
    )
    if not binding_ok:
        reasons.append(
            "analysis does not retain the approved model-to-structure edge-binding witness"
        )

    structural_labels: tuple[str | None, ...] = (None,) * len(edges)
    decorated_labels: tuple[str | None, ...] = tuple(
        f"{value.numerator}/{value.denominator} ohm"
        for value in resistance_values
    )
    try:
        structural_form = getattr(candidate, "structural_canonical_form", None)
        decorated_form = getattr(candidate, "decorated_model_canonical_form", None)
        canonical_forms_ok = _canonical_form_matches(
            diagram,
            structural_labels,
            structural_form,
            budget=subject.canonicalization_budget,
        ) and _canonical_form_matches(
            diagram,
            decorated_labels,
            decorated_form,
            budget=subject.canonicalization_budget,
        ) and structural_form == canonicalize(
            diagram,
            budget=subject.canonicalization_budget,
        ) and decorated_form == canonicalize(
            diagram,
            budget=subject.canonicalization_budget,
            edge_labels=tuple(label for label in decorated_labels if label is not None),
        )
    except ValueError as error:
        canonical_forms_ok = False
        reasons.append(str(error))
    if not canonical_forms_ok:
        reasons.append(
            "structural or decorated canonical form does not preserve the approved topology/model"
        )

    relation = getattr(candidate, "boundary_relation", None)
    try:
        expected_rows = _expected_relation(diagram, resistance_values)
        candidate_rows = _candidate_relation_rows(
            relation,
            dom_ports=len(diagram.dom.ports),
            cod_ports=len(diagram.cod.ports),
        )
        exact_relation_ok = candidate_rows == expected_rows
        if not exact_relation_ok:
            reasons.append("exact boundary relation differs from verifier elimination")
    except (AttributeError, TypeError, ValueError) as error:
        expected_rows = ()
        candidate_rows = ()
        exact_relation_ok = False
        reasons.append(f"exact boundary relation is invalid: {error}")

    solution = getattr(candidate, "sparse_solution", None)
    if type(solution) is not DCSolveResult:
        reasons.append("candidate does not retain an exact DCSolveResult")
        return _report(
            DirectVerificationDecision.FAIL,
            reasons,
            canonical_forms_ok=canonical_forms_ok,
            exact_relation_ok=exact_relation_ok,
        )
    nodes = getattr(solution, "nodes", None)
    branches = getattr(solution, "branches", None)
    source = getattr(solution, "source", None)
    reported_diagnostics = getattr(solution, "diagnostics", None)
    if type(nodes) is not tuple or type(branches) is not tuple:
        reasons.append("node and branch inventories must be exact tuples")
        return _report(
            DirectVerificationDecision.FAIL,
            reasons,
            canonical_forms_ok=canonical_forms_ok,
            exact_relation_ok=exact_relation_ok,
        )

    inventory_ok = binding_ok
    if len(nodes) != len(diagram.node_kinds):
        inventory_ok = False
        reasons.append("node inventory is incomplete or duplicated")
    if len(branches) != len(edges):
        inventory_ok = False
        reasons.append("branch inventory is incomplete or duplicated")
    if type(source) is not SourceObservation:
        inventory_ok = False
        reasons.append("source inventory is missing or has the wrong exact type")

    voltage_by_node: dict[int, float] = {}
    for position, node in enumerate(nodes):
        if type(node) is not NodeVoltage:
            inventory_ok = False
            reasons.append(f"node record {position} has the wrong exact type")
            continue
        index = getattr(node, "node_index", None)
        if type(index) is not int or index != position:
            inventory_ok = False
            reasons.append("node records are not exactly ordered 0..N-1")
            continue
        try:
            voltage_by_node[index] = _finite_float(
                getattr(node, "volts", None),
                f"node[{index}].volts",
            )
        except (TypeError, ValueError) as error:
            inventory_ok = False
            reasons.append(str(error))

    branch_law_ok = inventory_ok
    branch_currents: list[float] = []
    branch_powers: list[float] = []
    net_resistor_current = [0.0 for _ in diagram.node_kinds]
    for position, (branch, edge, resistance) in enumerate(
        zip(branches, edges, resistance_values)
    ):
        if type(branch) is not ResistorBranch:
            inventory_ok = False
            branch_law_ok = False
            reasons.append(f"branch record {position} has the wrong exact type")
            continue
        if (
            getattr(branch, "branch_index", None) != position
            or getattr(branch, "node_a", None) != edge.node_a
            or getattr(branch, "node_b", None) != edge.node_b
        ):
            inventory_ok = False
            branch_law_ok = False
            reasons.append(f"branch[{position}] does not match its structural edge")
            continue
        try:
            recorded_resistance = _resistance_fraction(
                getattr(branch, "resistance", None),
                f"branch[{position}].resistance",
            )
            if recorded_resistance != resistance:
                inventory_ok = False
                branch_law_ok = False
                reasons.append(f"branch[{position}] does not retain its approved resistance")
                continue
            drop = _finite_float(
                getattr(branch, "voltage_drop_volts", None),
                f"branch[{position}].voltage_drop_volts",
            )
            current = _finite_float(
                getattr(branch, "current_amperes", None),
                f"branch[{position}].current_amperes",
            )
            power = _finite_float(
                getattr(branch, "absorbed_power_watts", None),
                f"branch[{position}].absorbed_power_watts",
            )
        except (TypeError, ValueError) as error:
            branch_law_ok = False
            reasons.append(str(error))
            continue
        if edge.node_a not in voltage_by_node or edge.node_b not in voltage_by_node:
            branch_law_ok = False
            continue
        expected_drop = voltage_by_node[edge.node_a] - voltage_by_node[edge.node_b]
        expected_current = expected_drop / float(resistance)
        expected_power = expected_drop * expected_current
        scale_v = max(abs(expected_drop), abs(drop), 1.0)
        scale_i = max(abs(expected_current), abs(current), 1e-30)
        scale_p = max(abs(expected_power), abs(power), 1e-30)
        if not _field_close(drop, expected_drop, scale_v, tolerance):
            branch_law_ok = False
            reasons.append(f"branch[{position}] voltage drop violates the retained node values")
        if not _field_close(current, expected_current, scale_i, tolerance):
            branch_law_ok = False
            reasons.append(f"branch[{position}] current violates Ohm's law")
        if not _field_close(power, expected_power, scale_p, tolerance):
            branch_law_ok = False
            reasons.append(f"branch[{position}] power violates V*I")
        branch_currents.append(expected_current)
        branch_powers.append(expected_power)
        net_resistor_current[edge.node_a] += expected_current
        net_resistor_current[edge.node_b] -= expected_current

    reference_node = diagram.node_for(experiment.reference)
    positive_node = diagram.node_for(experiment.drive.positive)
    negative_node = diagram.node_for(experiment.drive.negative)
    drive_volts = float(_fraction(experiment.drive.volts, "drive.volts"))
    source_constraint_ok = inventory_ok
    source_current = 0.0
    source_power = 0.0
    if inventory_ok:
        try:
            if (
                getattr(source, "positive_node", None) != positive_node
                or getattr(source, "negative_node", None) != negative_node
            ):
                source_constraint_ok = False
                reasons.append("source node inventory differs from the approved drive")
            recorded_source_volts = _finite_float(
                getattr(source, "volts", None),
                "source.volts",
            )
            source_current = _finite_float(
                getattr(source, "current_entering_positive_amperes", None),
                "source.current_entering_positive_amperes",
            )
            source_power = _finite_float(
                getattr(source, "absorbed_power_watts", None),
                "source.absorbed_power_watts",
            )
            voltage_scale = max(
                1.0,
                abs(drive_volts),
                *(abs(value) for value in voltage_by_node.values()),
            )
            if not _field_close(
                recorded_source_volts,
                drive_volts,
                voltage_scale,
                tolerance,
            ):
                source_constraint_ok = False
                reasons.append("source voltage record differs from the approved drive")
            if not _field_close(
                voltage_by_node[positive_node] - voltage_by_node[negative_node],
                drive_volts,
                voltage_scale,
                tolerance,
            ):
                source_constraint_ok = False
                reasons.append("node voltages violate the ideal-source constraint")
            if not _field_close(
                voltage_by_node[reference_node],
                0.0,
                voltage_scale,
                tolerance,
            ):
                source_constraint_ok = False
                reasons.append("declared reference node is not at zero volts")
            expected_source_power = drive_volts * source_current
            if not _field_close(
                source_power,
                expected_source_power,
                max(abs(source_power), abs(expected_source_power), 1e-30),
                tolerance,
            ):
                source_constraint_ok = False
                reasons.append("source absorbed power violates V*I")
        except (KeyError, TypeError, ValueError) as error:
            source_constraint_ok = False
            reasons.append(str(error))

    kcl_values = list(net_resistor_current)
    if len(kcl_values) == len(diagram.node_kinds):
        kcl_values[positive_node] += source_current
        kcl_values[negative_node] -= source_current
    kcl_residual = max((abs(value) for value in kcl_values), default=0.0)
    current_scale = max(
        1e-30,
        abs(source_current),
        *(abs(value) for value in branch_currents),
    )
    scaled_kcl = kcl_residual / current_scale
    kcl_ok = inventory_ok and branch_law_ok and scaled_kcl <= tolerance
    if not kcl_ok:
        reasons.append("nodewise KCL exceeds the approved scaled tolerance")

    constraint_residual = abs(
        voltage_by_node.get(positive_node, float("inf"))
        - voltage_by_node.get(negative_node, float("inf"))
        - drive_volts
    )
    voltage_scale = max(
        1.0,
        abs(drive_volts),
        *(abs(value) for value in voltage_by_node.values()),
    )
    scaled_constraint = constraint_residual / voltage_scale

    power_residual = abs(sum(branch_powers) + source_power)
    power_scale = max(
        1e-30,
        abs(source_power),
        *(abs(value) for value in branch_powers),
    )
    scaled_power = power_residual / power_scale
    passivity_ok = (
        inventory_ok
        and branch_law_ok
        and all(power >= -tolerance * power_scale for power in branch_powers)
    )
    power_ok = passivity_ok and scaled_power <= tolerance
    if not passivity_ok:
        reasons.append("one or more positive resistors have negative absorbed power")
    if not power_ok:
        reasons.append("global source-inclusive power balance exceeds tolerance")

    refs = _boundary_refs(diagram)
    boundary_currents = [0.0 for _ in refs]
    for index, boundary in enumerate(refs):
        if boundary == experiment.drive.positive:
            boundary_currents[index] -= source_current
        if boundary == experiment.drive.negative:
            boundary_currents[index] += source_current
    relation_vector = [
        voltage_by_node.get(diagram.node_for(boundary), float("inf"))
        for boundary in refs
    ] + boundary_currents
    relation_residual, scaled_relation = _relation_residual(
        expected_rows,
        relation_vector,
    )
    relation_numeric_ok = scaled_relation <= tolerance
    if not relation_numeric_ok:
        reasons.append("numerical boundary witness violates the verifier-derived relation")

    diagnostics = DirectCircuitDiagnostics(
        kcl_residual,
        constraint_residual,
        power_residual,
        relation_residual,
        scaled_kcl,
        scaled_constraint,
        scaled_power,
        scaled_relation,
    )

    diagnostics_ok = type(reported_diagnostics) is CircuitDiagnostics
    if diagnostics_ok:
        recomputed_by_name = {
            "kcl_residual_amperes": kcl_residual,
            "constraint_residual_volts": constraint_residual,
            "power_residual_watts": power_residual,
            "relation_residual": relation_residual,
            "scaled_kcl_residual": scaled_kcl,
            "scaled_constraint_residual": scaled_constraint,
            "scaled_power_residual": scaled_power,
            "scaled_relation_residual": scaled_relation,
        }
        for name in (
            "kcl_residual_amperes",
            "constraint_residual_volts",
            "power_residual_watts",
            "relation_residual",
            "scaled_kcl_residual",
            "scaled_constraint_residual",
            "scaled_power_residual",
            "scaled_relation_residual",
        ):
            try:
                retained_value = _finite_float(
                    getattr(reported_diagnostics, name, None),
                    f"diagnostics.{name}",
                )
                if retained_value != recomputed_by_name[name]:
                    diagnostics_ok = False
                    reasons.append(
                        f"diagnostics.{name} differs from direct recomputation"
                    )
            except (TypeError, ValueError) as error:
                diagnostics_ok = False
                reasons.append(str(error))
    else:
        reasons.append("candidate diagnostics have the wrong exact type")

    all_gates = (
        canonical_forms_ok
        and inventory_ok
        and exact_relation_ok
        and relation_numeric_ok
        and branch_law_ok
        and kcl_ok
        and source_constraint_ok
        and power_ok
        and passivity_ok
        and diagnostics_ok
    )
    maximum_scaled = max(
        scaled_kcl,
        scaled_constraint,
        scaled_power,
        scaled_relation,
    )
    if all_gates and maximum_scaled <= tolerance / 8.0:
        decision = DirectVerificationDecision.PASS
        reasons.append("all independent E1 gates pass with certification margin")
    elif all_gates and maximum_scaled <= tolerance:
        decision = DirectVerificationDecision.AMBIGUOUS
        reasons.append("residuals pass the solver tolerance but not the verifier margin")
    else:
        decision = DirectVerificationDecision.FAIL
    return _report(
        decision,
        reasons,
        canonical_forms_ok=canonical_forms_ok,
        inventory_ok=inventory_ok,
        exact_relation_ok=exact_relation_ok and relation_numeric_ok,
        branch_law_ok=branch_law_ok,
        kcl_ok=kcl_ok,
        source_constraint_ok=source_constraint_ok,
        power_ok=power_ok,
        passivity_ok=passivity_ok,
        diagnostics=diagnostics,
    )
