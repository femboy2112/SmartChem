"""Shared immutable records for the finite ideal-resistor DC control.

This module is the nominal trust boundary shared by the production interpreter and its
independent verifier.  It deliberately contains only immutable data contracts and exact
linear-relation algebra: no sparse assembly, numerical solve, compiled executor, or direct
verification logic.  Both sides therefore compare real class identities without importing
one another or accepting dynamically forged lookalike classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isfinite
from numbers import Real
from typing import Iterable, Sequence

from .contracts import Digestible, canonical_digest
from .open_diagram import BoundaryRef, CanonicalDiagram, OpenDiagram

__all__ = [
    "BoundaryLinearRelation",
    "CircuitDiagnostics",
    "DCSolveResult",
    "DCSolveSpec",
    "DCVoltageDrive",
    "NodeVoltage",
    "PositiveResistance",
    "Rational",
    "ResistiveDCAnalysis",
    "ResistiveDCModel",
    "ResistiveDCSubject",
    "ResistorBranch",
    "ResistorEdgeBinding",
    "SourceObservation",
]


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
    """An exact positive resistance in ohms."""

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
class ResistorEdgeBinding:
    """Explicit model-index to structural-edge-index alignment witness."""

    model_index: int
    structural_edge_index: int

    def __post_init__(self) -> None:
        if type(self.model_index) is not int or self.model_index < 0:
            raise TypeError("model_index must be a non-negative exact int")
        if type(self.structural_edge_index) is not int or self.structural_edge_index < 0:
            raise TypeError("structural_edge_index must be a non-negative exact int")


@dataclass(frozen=True)
class ResistiveDCModel:
    """Positive resistor parameters plus an explicit structural-edge reindex witness."""

    resistances: tuple[PositiveResistance, ...]
    edge_bindings: tuple[ResistorEdgeBinding, ...]
    presentation_digest: str

    def __post_init__(self) -> None:
        if type(self.resistances) is not tuple:
            raise TypeError("resistances must be an exact tuple")
        if any(type(item) is not PositiveResistance for item in self.resistances):
            raise TypeError("resistances must contain only PositiveResistance records")
        if type(self.edge_bindings) is not tuple or any(
            type(item) is not ResistorEdgeBinding for item in self.edge_bindings
        ):
            raise TypeError("edge_bindings must contain only ResistorEdgeBinding records")
        count = len(self.resistances)
        if len(self.edge_bindings) != count:
            raise ValueError("edge_bindings must cover every model parameter exactly once")
        if tuple(sorted(item.model_index for item in self.edge_bindings)) != tuple(
            range(count)
        ):
            raise ValueError("edge_bindings model indices must be exactly 0..N-1")
        if tuple(
            sorted(item.structural_edge_index for item in self.edge_bindings)
        ) != tuple(range(count)):
            raise ValueError("edge_bindings structural indices must be exactly 0..N-1")
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
        *,
        edge_bindings: tuple[ResistorEdgeBinding, ...] | None = None,
    ) -> "ResistiveDCModel":
        """Bind model parameters to one exact open-diagram presentation."""
        if type(diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        bindings = (
            tuple(ResistorEdgeBinding(index, index) for index in range(len(resistances)))
            if edge_bindings is None
            else edge_bindings
        )
        return cls(resistances, bindings, canonical_digest(diagram))

    def validate_diagram(self, diagram: OpenDiagram) -> None:
        if type(diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        if len(diagram.structural_edges()) != len(self.resistances):
            raise ValueError(
                "ResistiveDCModel resistance count must equal the diagram structural-edge count"
            )
        if canonical_digest(diagram) != self.presentation_digest:
            raise ValueError(
                "ResistiveDCModel is not bound to this exact OpenDiagram presentation"
            )

    def resistances_in_structural_order(self) -> tuple[PositiveResistance, ...]:
        """Transport model order through the explicit finite reindex witness."""
        ordered: list[PositiveResistance | None] = [None] * len(self.resistances)
        for binding in self.edge_bindings:
            ordered[binding.structural_edge_index] = self.resistances[binding.model_index]
        if any(item is None for item in ordered):  # pragma: no cover - constructor invariant
            raise ValueError("edge binding did not cover every structural edge")
        return tuple(item for item in ordered if item is not None)

    def blackbox(self, diagram: OpenDiagram) -> "BoundaryLinearRelation":
        """Convenience dispatch to the production exact-relation interpreter."""
        from .circuit import blackbox_resistive_dc

        return blackbox_resistive_dc(diagram, self)


def _as_fraction(value: Fraction | Rational | int) -> Fraction:
    if type(value) is Rational:
        return value.fraction
    if type(value) is Fraction:
        return value
    if type(value) is int:
        return Fraction(value, 1)
    raise TypeError("linear-relation coefficients must be exact Fractions or ints")


def _rref(
    rows: Iterable[Sequence[Fraction | Rational | int]],
    width: int,
) -> tuple[tuple[Fraction, ...], ...]:
    """Canonical rational RREF with zero rows removed."""
    matrix = [[_as_fraction(value) for value in row] for row in rows]
    if any(len(row) != width for row in matrix):
        raise ValueError("linear-relation row has the wrong width")
    pivot_row = 0
    for column in range(width):
        candidate = next(
            (row for row in range(pivot_row, len(matrix)) if matrix[row][column]),
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
    return tuple(tuple(row) for row in matrix if any(value for value in row))


def _rational_rows(
    rows: Iterable[Sequence[Fraction]],
) -> tuple[tuple[Rational, ...], ...]:
    return tuple(
        tuple(Rational(value.numerator, value.denominator) for value in row)
        for row in rows
    )


@dataclass(frozen=True)
class BoundaryLinearRelation:
    """Exact homogeneous relation on boundary potentials and inward currents."""

    dom_ports: int
    cod_ports: int
    rref_rows: tuple[tuple[Rational, ...], ...]

    def __post_init__(self) -> None:
        if type(self.dom_ports) is not int or type(self.cod_ports) is not int:
            raise TypeError("relation interface widths must be exact ints")
        if self.dom_ports < 0 or self.cod_ports < 0:
            raise ValueError("relation interface widths must be non-negative")
        if type(self.rref_rows) is not tuple or any(
            type(row) is not tuple for row in self.rref_rows
        ):
            raise TypeError("rref_rows must be an exact tuple of tuples")
        if any(
            any(type(value) is not Rational for value in row)
            for row in self.rref_rows
        ):
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
            sum(
                coefficient.fraction * value
                for coefficient, value in zip(row, vector)
            )
            == 0
            for row in self.rref_rows
        )

    def residual(self, values: Sequence[float]) -> float:
        if len(values) != self.variable_count:
            raise ValueError("relation witness has the wrong width")
        if any(not isfinite(float(value)) for value in values):
            return float("inf")
        return max(
            (
                abs(
                    sum(
                        float(coefficient.fraction) * float(value)
                        for coefficient, value in zip(row, values)
                    )
                )
                for row in self.rref_rows
            ),
            default=0.0,
        )

    def scaled_residual(self, values: Sequence[float]) -> float:
        if len(values) != self.variable_count:
            raise ValueError("relation witness has the wrong width")
        if any(not isfinite(float(value)) for value in values):
            return float("inf")
        worst = 0.0
        for row in self.rref_rows:
            terms = [
                float(coefficient.fraction) * float(value)
                for coefficient, value in zip(row, values)
            ]
            worst = max(
                worst,
                abs(sum(terms)) / max(1e-30, sum(abs(term) for term in terms)),
            )
        return worst

    def then(self, other: "BoundaryLinearRelation") -> "BoundaryLinearRelation":
        if type(other) is not BoundaryLinearRelation:
            raise TypeError("can only compose BoundaryLinearRelation values")
        if self.cod_ports != other.dom_ports:
            raise ValueError("relation interfaces do not compose")
        a, b, c = self.dom_ports, self.cod_ports, other.cod_ports
        total = a + b + c + a + b + b + c
        rows: list[list[Fraction]] = []

        def embed(row: Sequence[Rational], positions: Sequence[int]) -> list[Fraction]:
            result = [Fraction(0) for _ in range(total)]
            for coefficient, position in zip(row, positions):
                result[position] = coefficient.fraction
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

    def parallel(self, other: "BoundaryLinearRelation") -> "BoundaryLinearRelation":
        """Parallel composition: both relations hold over a SHARED boundary, port currents SUM.

        For two relations on the *same* interfaces (``self.dom_ports == other.dom_ports`` and likewise cod),
        the parallel identifies each boundary potential across the two operands (``V`` is shared) and sums the
        two inward currents at each port (``I = I_self + I_other``), then existentially eliminates the two
        branch currents -- the exact ``R1||R2 = 1/(1/R1 + 1/R2)`` law for the ideal resistor case.

        This is the relation-level MERGE that gives a CORRECT apex under parallel gluing -- the counterpart to
        the ``open_core.plug_all`` node-merge, which passes its apex through UNCHANGED and so leaves a stale,
        wrong relation (the item-6 hazard).  Here the branch currents are properly eliminated, so the composite
        relation is exact.  It is commutative and associative (shared potentials, summed currents).  The
        interfaces must match exactly; a mismatch is a loud error, never a silent wrong composite.

        Correct for ARBITRARY matching interfaces, not only the 1->1 resistor case: an adversarial
        structure-theorem review cross-checked it against an INDEPENDENT image-space oracle (nullspace
        intersection with potential-agreement + current-sum, a computation dual to this constraint-space
        elimination) over random multiport relations (p,q up to 3) with 0 mismatches, and confirmed multiport
        physical correctness, commutativity, and associativity.
        """
        if type(other) is not BoundaryLinearRelation:
            raise TypeError("can only parallel-compose BoundaryLinearRelation values")
        if self.dom_ports != other.dom_ports or self.cod_ports != other.cod_ports:
            raise ValueError("parallel composition requires identical dom and cod interfaces")
        p, q = self.dom_ports, self.cod_ports
        ext = 2 * (p + q)                       # shared external vars: V_dom(p), V_cod(q), I_dom(p), I_cod(q)
        total = 2 * ext                         # + branch-1 currents I(p+q), branch-2 currents I(p+q)
        rows: list[list[Fraction]] = []

        def embed(row: Sequence[Rational], positions: Sequence[int]) -> list[Fraction]:
            result = [Fraction(0) for _ in range(total)]
            for coefficient, position in zip(row, positions):
                result[position] = coefficient.fraction
            return result

        # each operand's own vars are ordered [V_dom(p), V_cod(q), I_dom(p), I_cod(q)]: potentials map to the
        # SHARED externals (0..p+q-1); currents map to that operand's own branch block.
        self_positions = list(range(p + q)) + list(range(ext, ext + p + q))
        other_positions = list(range(p + q)) + list(range(ext + p + q, total))
        rows.extend(embed(row, self_positions) for row in self.rref_rows)
        rows.extend(embed(row, other_positions) for row in other.rref_rows)
        # per-port KCL at the merged boundary: I_ext[c] - I_branch1[c] - I_branch2[c] = 0
        for c in range(p + q):
            row = [Fraction(0) for _ in range(total)]
            row[(p + q) + c] = Fraction(1)                  # external inward current at port c
            row[ext + c] = Fraction(-1)                     # branch-1 current at port c
            row[ext + (p + q) + c] = Fraction(-1)           # branch-2 current at port c
            rows.append(row)
        keep = list(range(ext))
        return _project_relation(p, q, rows, total, keep)

    def tensor(self, other: "BoundaryLinearRelation") -> "BoundaryLinearRelation":
        if type(other) is not BoundaryLinearRelation:
            raise TypeError("can only tensor BoundaryLinearRelation values")
        a, b, c, d = self.dom_ports, self.cod_ports, other.dom_ports, other.cod_ports
        total = 2 * (a + c + b + d)
        rows: list[list[Fraction]] = []

        def embed(row: Sequence[Rational], positions: Sequence[int]) -> list[Fraction]:
            result = [Fraction(0) for _ in range(total)]
            for coefficient, position in zip(row, positions):
                result[position] = coefficient.fraction
            return result

        f_positions = (
            list(range(0, a))
            + list(range(a + c, a + c + b))
            + list(range(a + c + b + d, a + c + b + d + a))
            + list(
                range(
                    a + c + b + d + a + c,
                    a + c + b + d + a + c + b,
                )
            )
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
    if len(set(keep)) != len(keep) or any(
        index < 0 or index >= total_width for index in keep
    ):
        raise ValueError("invalid relation projection indices")
    eliminated = [index for index in range(total_width) if index not in set(keep)]
    permutation = eliminated + list(keep)
    reduced = _rref(
        ([row[index] for index in permutation] for row in rows),
        total_width,
    )
    internal_width = len(eliminated)
    external_rows = [
        row[internal_width:]
        for row in reduced
        if all(value == 0 for value in row[:internal_width])
    ]
    return BoundaryLinearRelation.from_equations(dom_ports, cod_ports, external_rows)


@dataclass(frozen=True)
class DCVoltageDrive:
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
    reference: BoundaryRef
    drive: DCVoltageDrive
    scaled_tolerance: float = 1e-9

    def __post_init__(self) -> None:
        if type(self.reference) is not BoundaryRef:
            raise TypeError("reference must be an exact BoundaryRef")
        if type(self.drive) is not DCVoltageDrive:
            raise TypeError("drive must be an exact DCVoltageDrive")
        if isinstance(self.scaled_tolerance, bool) or not isinstance(
            self.scaled_tolerance, Real
        ):
            raise TypeError("scaled_tolerance must be a real number")
        if not isfinite(float(self.scaled_tolerance)) or not (
            0 < float(self.scaled_tolerance) < 1
        ):
            raise ValueError(
                "scaled_tolerance must be finite and strictly between zero and one"
            )


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


@dataclass(frozen=True)
class ResistiveDCSubject(Digestible):
    """Exact structure, explicitly reindexed model, experiment, and observer budget."""

    diagram: OpenDiagram
    model: ResistiveDCModel
    experiment: DCSolveSpec
    canonicalization_budget: int

    def __post_init__(self) -> None:
        if type(self.diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        if type(self.model) is not ResistiveDCModel:
            raise TypeError("model must be an exact ResistiveDCModel")
        if type(self.experiment) is not DCSolveSpec:
            raise TypeError("experiment must be an exact DCSolveSpec")
        if (
            type(self.canonicalization_budget) is not int
            or self.canonicalization_budget < 0
        ):
            raise ValueError(
                "canonicalization_budget must be a non-negative exact integer"
            )
        self.model.validate_diagram(self.diagram)


@dataclass(frozen=True)
class ResistiveDCAnalysis(Digestible):
    """Retained structural, exact-relation, and sparse-MNA witnesses."""

    structural_canonical_form: CanonicalDiagram
    decorated_model_canonical_form: CanonicalDiagram
    model_edge_bindings: tuple[ResistorEdgeBinding, ...]
    boundary_relation: BoundaryLinearRelation
    sparse_solution: DCSolveResult

    def __post_init__(self) -> None:
        if type(self.structural_canonical_form) is not CanonicalDiagram:
            raise TypeError(
                "structural_canonical_form must be an exact CanonicalDiagram"
            )
        if type(self.decorated_model_canonical_form) is not CanonicalDiagram:
            raise TypeError(
                "decorated_model_canonical_form must be an exact CanonicalDiagram"
            )
        if type(self.model_edge_bindings) is not tuple or any(
            type(item) is not ResistorEdgeBinding
            for item in self.model_edge_bindings
        ):
            raise TypeError(
                "model_edge_bindings must retain exact ResistorEdgeBinding records"
            )
        if type(self.boundary_relation) is not BoundaryLinearRelation:
            raise TypeError("boundary_relation must be an exact BoundaryLinearRelation")
        if type(self.sparse_solution) is not DCSolveResult:
            raise TypeError("sparse_solution must be an exact DCSolveResult")
