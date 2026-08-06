"""Exact nominal records for the bounded positive-frequency passive RLC control.

The semantic coefficients are elements of Q(i), never Python ``complex`` values.  The
numeric interpreter may round them only after the exact relation and rank preflights.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from math import isfinite
from numbers import Real
from typing import Iterable, Sequence

from .contracts import Digestible, canonical_digest
from .open_diagram import BoundaryRef, CanonicalDiagram, OpenDiagram
from .resistive_dc_schema import Rational

__all__ = [
    "ACCircuitDiagnostics",
    "ACSolveResult",
    "ACSolveSpec",
    "ACSourceObservation",
    "ACVoltageDrive",
    "ComplexBoundaryRelation",
    "ElementKind",
    "GaussianComplex",
    "MNAState",
    "NodePhasor",
    "Phasor",
    "PositiveAngularFrequency",
    "PositiveCapacitance",
    "PositiveInductance",
    "PositiveResistance",
    "RLCBranch",
    "RLCComponent",
    "RLCEdgeBinding",
    "RLCACAnalysis",
    "RLCACSubject",
    "RLCModel",
    "Rational",
    "exact_rank",
]


def _fraction(value: Rational | Fraction | int) -> Fraction:
    if type(value) is Rational:
        return value.fraction
    if type(value) is Fraction:
        return value
    if type(value) is int:
        return Fraction(value, 1)
    raise TypeError("exact coefficients must be Rational, Fraction, or int")


@dataclass(frozen=True)
class GaussianComplex:
    """A normalized exact element ``real + i imag`` of Q(i)."""

    real: Rational = Rational(0)
    imag: Rational = Rational(0)

    def __post_init__(self) -> None:
        if type(self.real) is not Rational or type(self.imag) is not Rational:
            raise TypeError("GaussianComplex coordinates must be exact Rational values")

    @classmethod
    def from_parts(
        cls, real: Rational | Fraction | int = 0, imag: Rational | Fraction | int = 0
    ) -> "GaussianComplex":
        a, b = _fraction(real), _fraction(imag)
        return cls(
            Rational(a.numerator, a.denominator), Rational(b.numerator, b.denominator)
        )

    @classmethod
    def zero(cls) -> "GaussianComplex":
        return cls()

    @classmethod
    def one(cls) -> "GaussianComplex":
        return cls.from_parts(1)

    def __add__(self, other: object) -> "GaussianComplex":
        if type(other) is not GaussianComplex:
            return NotImplemented
        return GaussianComplex.from_parts(
            self.real.fraction + other.real.fraction,
            self.imag.fraction + other.imag.fraction,
        )

    def __sub__(self, other: object) -> "GaussianComplex":
        if type(other) is not GaussianComplex:
            return NotImplemented
        return GaussianComplex.from_parts(
            self.real.fraction - other.real.fraction,
            self.imag.fraction - other.imag.fraction,
        )

    def __neg__(self) -> "GaussianComplex":
        return GaussianComplex.from_parts(-self.real.fraction, -self.imag.fraction)

    def __mul__(self, other: object) -> "GaussianComplex":
        if type(other) is not GaussianComplex:
            return NotImplemented
        a, b, c, d = (
            self.real.fraction,
            self.imag.fraction,
            other.real.fraction,
            other.imag.fraction,
        )
        return GaussianComplex.from_parts(a * c - b * d, a * d + b * c)

    def inverse(self) -> "GaussianComplex":
        a, b = self.real.fraction, self.imag.fraction
        denominator = a * a + b * b
        if not denominator:
            raise ZeroDivisionError("zero GaussianComplex has no inverse")
        return GaussianComplex.from_parts(a / denominator, -b / denominator)

    def __truediv__(self, other: object) -> "GaussianComplex":
        if type(other) is not GaussianComplex:
            return NotImplemented
        return self * other.inverse()

    def conjugate(self) -> "GaussianComplex":
        return GaussianComplex.from_parts(self.real.fraction, -self.imag.fraction)

    @property
    def is_zero(self) -> bool:
        return self.real.fraction == 0 and self.imag.fraction == 0

    def to_complex(self) -> complex:
        try:
            value = complex(float(self.real.fraction), float(self.imag.fraction))
        except OverflowError as exc:
            raise OverflowError(
                "GaussianComplex cannot be represented as finite binary64 complex"
            ) from exc
        if not isfinite(value.real) or not isfinite(value.imag):
            raise OverflowError(
                "GaussianComplex cannot be represented as finite binary64 complex"
            )
        return value


class ElementKind(str, Enum):
    RESISTOR = "R"
    INDUCTOR = "L"
    CAPACITOR = "C"


def _positive(value: Rational, name: str) -> None:
    if type(value) is not Rational:
        raise TypeError(f"{name} must be an exact Rational")
    if value.fraction <= 0:
        raise ValueError(f"{name} must be strictly positive")


@dataclass(frozen=True)
class PositiveResistance:
    ohms: Rational

    def __post_init__(self) -> None:
        _positive(self.ohms, "ohms")


@dataclass(frozen=True)
class PositiveInductance:
    henries: Rational

    def __post_init__(self) -> None:
        _positive(self.henries, "henries")


@dataclass(frozen=True)
class PositiveCapacitance:
    farads: Rational

    def __post_init__(self) -> None:
        _positive(self.farads, "farads")


@dataclass(frozen=True)
class PositiveAngularFrequency:
    radians_per_second: Rational

    def __post_init__(self) -> None:
        _positive(self.radians_per_second, "radians_per_second")

    @property
    def fraction(self) -> Fraction:
        return self.radians_per_second.fraction


@dataclass(frozen=True)
class RLCComponent:
    kind: ElementKind
    value: PositiveResistance | PositiveInductance | PositiveCapacitance

    def __post_init__(self) -> None:
        if type(self.kind) is not ElementKind:
            raise TypeError("component kind must be an exact ElementKind")
        expected = {
            ElementKind.RESISTOR: PositiveResistance,
            ElementKind.INDUCTOR: PositiveInductance,
            ElementKind.CAPACITOR: PositiveCapacitance,
        }[self.kind]
        if type(self.value) is not expected:
            raise TypeError(
                f"{self.kind.value} component has the wrong positive parameter record"
            )


@dataclass(frozen=True)
class RLCEdgeBinding:
    model_index: int
    structural_edge_index: int

    def __post_init__(self) -> None:
        if (
            type(self.model_index) is not int
            or self.model_index < 0
            or type(self.structural_edge_index) is not int
            or self.structural_edge_index < 0
        ):
            raise TypeError("edge binding indices must be non-negative exact ints")


@dataclass(frozen=True)
class RLCModel:
    components: tuple[RLCComponent, ...]
    edge_bindings: tuple[RLCEdgeBinding, ...]
    presentation_digest: str

    def __post_init__(self) -> None:
        if type(self.components) is not tuple or any(
            type(x) is not RLCComponent for x in self.components
        ):
            raise TypeError("components must be an exact tuple of RLCComponent records")
        if type(self.edge_bindings) is not tuple or any(
            type(x) is not RLCEdgeBinding for x in self.edge_bindings
        ):
            raise TypeError(
                "edge_bindings must be an exact tuple of RLCEdgeBinding records"
            )
        count = len(self.components)
        if (
            len(self.edge_bindings) != count
            or sorted(x.model_index for x in self.edge_bindings) != list(range(count))
            or sorted(x.structural_edge_index for x in self.edge_bindings)
            != list(range(count))
        ):
            raise ValueError(
                "edge bindings must cover model and structural inventories exactly once"
            )
        if (
            type(self.presentation_digest) is not str
            or len(self.presentation_digest) != 64
        ):
            raise TypeError("presentation_digest must be a SHA-256 hex digest")
        try:
            int(self.presentation_digest, 16)
        except ValueError as exc:
            raise ValueError("presentation_digest must be hexadecimal") from exc

    @classmethod
    def for_diagram(
        cls,
        diagram: OpenDiagram,
        components: tuple[RLCComponent, ...],
        *,
        edge_bindings: tuple[RLCEdgeBinding, ...] | None = None,
    ) -> "RLCModel":
        if type(diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        bindings = (
            tuple(RLCEdgeBinding(i, i) for i in range(len(components)))
            if edge_bindings is None
            else edge_bindings
        )
        return cls(components, bindings, canonical_digest(diagram))

    def validate_diagram(self, diagram: OpenDiagram) -> None:
        if type(diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        if len(diagram.structural_edges()) != len(self.components):
            raise ValueError("component inventory does not match structural edges")
        if canonical_digest(diagram) != self.presentation_digest:
            raise ValueError(
                "RLCModel is not bound to this exact OpenDiagram presentation"
            )

    def components_in_structural_order(self) -> tuple[RLCComponent, ...]:
        ordered: list[RLCComponent | None] = [None] * len(self.components)
        for binding in self.edge_bindings:
            ordered[binding.structural_edge_index] = self.components[
                binding.model_index
            ]
        return tuple(x for x in ordered if x is not None)

    def canonical_edge_labels(self) -> tuple[str, ...]:
        """Opaque exact edge decorations, declaration/structural-order aligned.

        Each label injectively encodes one component's kind and exact rational value in
        the structural edge order (the order ``diagram.edges`` is declared in), so it can
        be handed to :func:`~smartchem.open_diagram.canonicalize` as the ``edge_labels``
        that carry the R/L/C decoration through the exact alpha-invariant canonicalizer.
        This is the single source of the decoration convention: the analysis pipeline and
        the :class:`~smartchem.circuit_model_ir.CircuitModelIR` identity both consume it,
        so a decorated canonical form is byte-identical however it was produced.
        """
        labels: list[str] = []
        for component in self.components_in_structural_order():
            if component.kind is ElementKind.RESISTOR:
                value = component.value.ohms
                unit = "ohm"
            elif component.kind is ElementKind.INDUCTOR:
                value = component.value.henries
                unit = "H"
            else:
                value = component.value.farads
                unit = "F"
            labels.append(
                f"{component.kind.value}:{value.numerator}/{value.denominator} {unit}"
            )
        return tuple(labels)


def _rref(
    rows: Iterable[Sequence[GaussianComplex]], width: int
) -> tuple[tuple[GaussianComplex, ...], ...]:
    matrix = [list(row) for row in rows]
    if any(len(row) != width for row in matrix):
        raise ValueError("complex relation row has wrong width")
    if any(type(x) is not GaussianComplex for row in matrix for x in row):
        raise TypeError("complex relation coefficients must be GaussianComplex")
    active = 0
    for column in range(width):
        pivot = next(
            (r for r in range(active, len(matrix)) if not matrix[r][column].is_zero),
            None,
        )
        if pivot is None:
            continue
        matrix[active], matrix[pivot] = matrix[pivot], matrix[active]
        inv = matrix[active][column].inverse()
        matrix[active] = [x * inv for x in matrix[active]]
        for r in range(len(matrix)):
            if r == active:
                continue
            coefficient = matrix[r][column]
            if not coefficient.is_zero:
                matrix[r] = [
                    x - coefficient * y for x, y in zip(matrix[r], matrix[active])
                ]
        active += 1
        if active == len(matrix):
            break
    return tuple(tuple(row) for row in matrix if any(not x.is_zero for x in row))


def exact_rank(
    rows: Iterable[Sequence[GaussianComplex]], width: int | None = None
) -> int:
    materialized = tuple(tuple(row) for row in rows)
    return len(
        _rref(
            materialized,
            len(materialized[0]) if width is None and materialized else (width or 0),
        )
    )


@dataclass(frozen=True)
class ComplexBoundaryRelation:
    dom_ports: int
    cod_ports: int
    rref_rows: tuple[tuple[GaussianComplex, ...], ...]

    def __post_init__(self) -> None:
        if (
            type(self.dom_ports) is not int
            or type(self.cod_ports) is not int
            or self.dom_ports < 0
            or self.cod_ports < 0
        ):
            raise ValueError("relation widths must be non-negative exact ints")
        if type(self.rref_rows) is not tuple or any(
            type(row) is not tuple for row in self.rref_rows
        ):
            raise TypeError("rref_rows must be an exact tuple of tuples")
        if any(len(row) != self.variable_count for row in self.rref_rows):
            raise ValueError("complex relation row width is wrong")
        if _rref(self.rref_rows, self.variable_count) != self.rref_rows:
            raise ValueError("complex relation rows must already be canonical RREF")

    @property
    def boundary_ports(self) -> int:
        return self.dom_ports + self.cod_ports

    @property
    def variable_count(self) -> int:
        return 2 * self.boundary_ports

    @classmethod
    def from_equations(
        cls, dom_ports: int, cod_ports: int, rows: Iterable[Sequence[GaussianComplex]]
    ) -> "ComplexBoundaryRelation":
        return cls(dom_ports, cod_ports, _rref(rows, 2 * (dom_ports + cod_ports)))

    def residual(self, values: Sequence[complex]) -> tuple[float, float]:
        if len(values) != self.variable_count:
            raise ValueError("relation witness has wrong width")
        worst = scaled = 0.0
        for row in self.rref_rows:
            terms = [
                coefficient.to_complex() * value
                for coefficient, value in zip(row, values)
            ]
            worst = max(worst, abs(sum(terms)))
            scaled = max(
                scaled, abs(sum(terms)) / max(1e-30, sum(abs(x) for x in terms))
            )
        return worst, scaled


@dataclass(frozen=True)
class ACVoltageDrive:
    positive: BoundaryRef
    negative: BoundaryRef
    volts_rms: GaussianComplex

    def __post_init__(self) -> None:
        if (
            type(self.positive) is not BoundaryRef
            or type(self.negative) is not BoundaryRef
            or type(self.volts_rms) is not GaussianComplex
        ):
            raise TypeError(
                "AC drive requires exact boundary refs and GaussianComplex RMS volts"
            )


@dataclass(frozen=True)
class ACSolveSpec:
    reference: BoundaryRef
    drive: ACVoltageDrive
    omega: PositiveAngularFrequency
    scaled_tolerance: float = 1e-9
    conditioning_limit: float = 1e8
    conditioning_dimension_limit: int = 64

    def __post_init__(self) -> None:
        if (
            type(self.reference) is not BoundaryRef
            or type(self.drive) is not ACVoltageDrive
            or type(self.omega) is not PositiveAngularFrequency
        ):
            raise TypeError("AC spec contains wrong nominal records")
        if (
            isinstance(self.scaled_tolerance, bool)
            or not isinstance(self.scaled_tolerance, Real)
            or not isfinite(float(self.scaled_tolerance))
            or not 0 < float(self.scaled_tolerance) < 1
        ):
            raise ValueError("scaled_tolerance must be finite and in (0,1)")
        if (
            isinstance(self.conditioning_limit, bool)
            or not isinstance(self.conditioning_limit, Real)
            or not isfinite(float(self.conditioning_limit))
            or float(self.conditioning_limit) < 1
        ):
            raise ValueError("conditioning_limit must be finite and at least one")
        if (
            type(self.conditioning_dimension_limit) is not int
            or self.conditioning_dimension_limit < 1
        ):
            raise ValueError(
                "conditioning_dimension_limit must be a positive exact int"
            )


@dataclass(frozen=True)
class Phasor:
    """Finite binary64 phasor retained without relying on Python complex serialization."""

    real: float
    imag: float

    def __post_init__(self) -> None:
        for name, value in (("real", self.real), ("imag", self.imag)):
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not isfinite(float(value))
            ):
                raise ValueError(f"Phasor {name} must be finite")

    @classmethod
    def from_complex(cls, value: complex) -> "Phasor":
        return cls(float(value.real), float(value.imag))

    def to_complex(self) -> complex:
        return complex(self.real, self.imag)


@dataclass(frozen=True)
class NodePhasor:
    node_index: int
    volts_rms: Phasor

    def __post_init__(self) -> None:
        if (
            type(self.node_index) is not int
            or self.node_index < 0
            or type(self.volts_rms) is not Phasor
        ):
            raise TypeError("NodePhasor requires a non-negative exact index and Phasor")


@dataclass(frozen=True)
class RLCBranch:
    branch_index: int
    node_a: int
    node_b: int
    component: RLCComponent
    voltage_drop_rms: Phasor
    current_amperes_rms: Phasor
    absorbed_power_va: Phasor

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (self.branch_index, self.node_a, self.node_b)
        ):
            raise TypeError("RLCBranch indices must be non-negative exact ints")
        if type(self.component) is not RLCComponent or any(
            type(value) is not Phasor
            for value in (
                self.voltage_drop_rms,
                self.current_amperes_rms,
                self.absorbed_power_va,
            )
        ):
            raise TypeError(
                "RLCBranch requires its exact component and finite Phasor fields"
            )


@dataclass(frozen=True)
class ACSourceObservation:
    positive_node: int
    negative_node: int
    volts_rms: Phasor
    current_entering_positive_amperes_rms: Phasor
    absorbed_power_va: Phasor

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (self.positive_node, self.negative_node)
        ):
            raise TypeError("source node indices must be non-negative exact ints")
        if any(
            type(value) is not Phasor
            for value in (
                self.volts_rms,
                self.current_entering_positive_amperes_rms,
                self.absorbed_power_va,
            )
        ):
            raise TypeError("source observations require finite Phasors")


@dataclass(frozen=True)
class MNAState:
    """Normalized MNA state; the final solution phasor is ``Z0 * I_source``."""

    unknown_node_indices: tuple[int, ...]
    source_current_index: int
    normalized_impedance_ohms: float
    solution: tuple[Phasor, ...]

    def __post_init__(self) -> None:
        if type(self.unknown_node_indices) is not tuple or any(
            type(x) is not int or x < 0 for x in self.unknown_node_indices
        ):
            raise TypeError(
                "MNA unknown node indices must be an exact tuple of non-negative ints"
            )
        if type(
            self.source_current_index
        ) is not int or self.source_current_index != len(self.unknown_node_indices):
            raise ValueError("source current must follow every retained unknown node")
        if (
            type(self.solution) is not tuple
            or len(self.solution) != len(self.unknown_node_indices) + 1
            or any(type(x) is not Phasor for x in self.solution)
        ):
            raise TypeError("MNA solution must retain every finite Phasor state")
        if (
            isinstance(self.normalized_impedance_ohms, bool)
            or not isinstance(self.normalized_impedance_ohms, Real)
            or not isfinite(float(self.normalized_impedance_ohms))
            or float(self.normalized_impedance_ohms) <= 0
        ):
            raise ValueError("normalized impedance must be finite and positive")


@dataclass(frozen=True)
class ACCircuitDiagnostics:
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
                or not isinstance(value, Real)
                or not isfinite(float(value))
            ):
                raise ValueError(f"diagnostic {name} must be finite")
        if (
            self.condition_number < 1
            or self.maximum_ideal_reactive_real_power_watts < 0
        ):
            raise ValueError(
                "condition and absolute ideal reactive real-power diagnostics are invalid"
            )


@dataclass(frozen=True)
class ACSolveResult:
    nodes: tuple[NodePhasor, ...]
    branches: tuple[RLCBranch, ...]
    source: ACSourceObservation
    mna_state: MNAState
    diagnostics: ACCircuitDiagnostics

    def __post_init__(self) -> None:
        if (
            type(self.nodes) is not tuple
            or any(type(x) is not NodePhasor for x in self.nodes)
            or tuple(x.node_index for x in self.nodes) != tuple(range(len(self.nodes)))
        ):
            raise TypeError(
                "nodes must be a complete canonically ordered NodePhasor tuple"
            )
        if (
            type(self.branches) is not tuple
            or any(type(x) is not RLCBranch for x in self.branches)
            or tuple(x.branch_index for x in self.branches)
            != tuple(range(len(self.branches)))
        ):
            raise TypeError(
                "branches must be a complete structurally ordered RLCBranch tuple"
            )
        if (
            type(self.source) is not ACSourceObservation
            or type(self.mna_state) is not MNAState
            or type(self.diagnostics) is not ACCircuitDiagnostics
        ):
            raise TypeError("AC result has wrong retained record types")


@dataclass(frozen=True)
class RLCACSubject(Digestible):
    diagram: OpenDiagram
    model: RLCModel
    experiment: ACSolveSpec
    canonicalization_budget: int

    def __post_init__(self) -> None:
        if (
            type(self.diagram) is not OpenDiagram
            or type(self.model) is not RLCModel
            or type(self.experiment) is not ACSolveSpec
        ):
            raise TypeError("RLCACSubject has wrong nominal records")
        if (
            type(self.canonicalization_budget) is not int
            or self.canonicalization_budget < 0
        ):
            raise ValueError("canonicalization_budget must be a non-negative exact int")
        self.model.validate_diagram(self.diagram)


@dataclass(frozen=True)
class RLCACAnalysis(Digestible):
    structural_canonical_form: CanonicalDiagram
    decorated_model_canonical_form: CanonicalDiagram
    model_edge_bindings: tuple[RLCEdgeBinding, ...]
    boundary_relation: ComplexBoundaryRelation
    sparse_solution: ACSolveResult

    def __post_init__(self) -> None:
        if (
            type(self.structural_canonical_form) is not CanonicalDiagram
            or type(self.decorated_model_canonical_form) is not CanonicalDiagram
        ):
            raise TypeError("analysis must retain exact canonical diagram forms")
        if type(self.model_edge_bindings) is not tuple or any(
            type(x) is not RLCEdgeBinding for x in self.model_edge_bindings
        ):
            raise TypeError("analysis must retain exact RLC edge bindings")
        if (
            type(self.boundary_relation) is not ComplexBoundaryRelation
            or type(self.sparse_solution) is not ACSolveResult
        ):
            raise TypeError("analysis contains wrong semantic witnesses")
