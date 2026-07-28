"""Analytic and hostile controls for the bounded positive-frequency RLC interpreter."""

from __future__ import annotations

import pytest

import smartchem.rlc_ac_circuit as circuit
from smartchem.contracts import canonical_digest
from smartchem.open_diagram import (
    BoundaryRef,
    BoundarySide,
    ComponentKind,
    ComponentSlot,
    ElementPortRef,
    Interface,
    Junction,
    OpenDiagram,
    PortKind,
)
from smartchem.rlc_ac_circuit import (
    ACNumericalRefusal,
    ACResidualError,
    ConditioningRefusal,
    LosslessSingularResonanceError,
    solve_rlc_ac,
)
from smartchem.rlc_ac_schema import (
    ACVoltageDrive,
    ACSolveSpec,
    ElementKind,
    GaussianComplex,
    PositiveAngularFrequency,
    PositiveCapacitance,
    PositiveInductance,
    PositiveResistance,
    RLCComponent,
    RLCEdgeBinding,
    RLCModel,
    Rational,
)


ELECTRICAL = PortKind.ELECTRICAL
ONE = Interface((ELECTRICAL,))


def _in() -> BoundaryRef:
    return BoundaryRef(BoundarySide.INPUT, 0)


def _out() -> BoundaryRef:
    return BoundaryRef(BoundarySide.OUTPUT, 0)


def _a(name: str) -> ElementPortRef:
    return ElementPortRef(name, "a")


def _b(name: str) -> ElementPortRef:
    return ElementPortRef(name, "b")


def _diagram(names: tuple[str, ...]) -> OpenDiagram:
    endpoints: list[tuple[str, tuple[object, ...]]] = [
        ("positive", (_in(), _a(names[0])))
    ]
    for left, right in zip(names, names[1:]):
        endpoints.append((f"mid-{left}", (_b(left), _a(right))))
    endpoints.append(("negative", (_b(names[-1]), _out())))
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(
            ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names
        ),
        tuple(Junction(name, ELECTRICAL, items) for name, items in endpoints),
    )


def _parallel_diagram(names: tuple[str, ...]) -> OpenDiagram:
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(
            ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names
        ),
        (
            Junction(
                "positive",
                ELECTRICAL,
                (_in(), *(ElementPortRef(name, "a") for name in names)),
            ),
            Junction(
                "negative",
                ELECTRICAL,
                (_out(), *(ElementPortRef(name, "b") for name in names)),
            ),
        ),
    )


def _component(
    kind: ElementKind, numerator: int = 1, denominator: int = 1
) -> RLCComponent:
    value = Rational(numerator, denominator)
    if kind is ElementKind.RESISTOR:
        return RLCComponent(kind, PositiveResistance(value))
    if kind is ElementKind.INDUCTOR:
        return RLCComponent(kind, PositiveInductance(value))
    return RLCComponent(kind, PositiveCapacitance(value))


def _solve(
    diagram: OpenDiagram,
    components: tuple[RLCComponent, ...],
    *,
    bindings: tuple[RLCEdgeBinding, ...] | None = None,
    tolerance: float = 1e-9,
):
    return solve_rlc_ac(
        diagram,
        RLCModel.for_diagram(diagram, components, edge_bindings=bindings),
        ACSolveSpec(
            _out(),
            ACVoltageDrive(_in(), _out(), GaussianComplex.from_parts(1)),
            PositiveAngularFrequency(Rational(1)),
            tolerance,
        ),
    )


def test_analytic_rc_phasors_power_and_serialization():
    result = _solve(
        _diagram(("r", "c")),
        (_component(ElementKind.RESISTOR), _component(ElementKind.CAPACITOR)),
    )
    assert result.branches[0].current_amperes_rms.to_complex() == pytest.approx(
        (1 + 1j) / 2
    )
    assert result.branches[0].absorbed_power_va.to_complex() == pytest.approx(0.5)
    assert result.branches[1].absorbed_power_va.to_complex() == pytest.approx(-0.5j)
    assert result.source.absorbed_power_va.to_complex() == pytest.approx(-0.5 + 0.5j)
    assert (
        result.diagnostics.minimum_resistor_absorbed_real_power_watts
        == pytest.approx(0.5)
    )
    assert result.diagnostics.maximum_ideal_reactive_real_power_watts < 1e-12
    assert len(canonical_digest(result)) == 64


def test_analytic_parallel_rc_complex_power_signs():
    result = _solve(
        _parallel_diagram(("r", "c")),
        (_component(ElementKind.RESISTOR), _component(ElementKind.CAPACITOR)),
    )
    assert [
        branch.current_amperes_rms.to_complex() for branch in result.branches
    ] == pytest.approx([1, 1j])
    assert [
        branch.absorbed_power_va.to_complex() for branch in result.branches
    ] == pytest.approx([1, -1j])
    assert result.source.current_entering_positive_amperes_rms.to_complex() == (
        pytest.approx(-1 - 1j)
    )
    assert result.source.absorbed_power_va.to_complex() == pytest.approx(-1 + 1j)


def test_damped_series_rlc_resonance_control():
    center = _solve(
        _diagram(("r", "l", "c")),
        (
            _component(ElementKind.RESISTOR),
            _component(ElementKind.INDUCTOR),
            _component(ElementKind.CAPACITOR),
        ),
    )
    powers = [branch.absorbed_power_va.to_complex() for branch in center.branches]
    assert powers == pytest.approx([1, 1j, -1j])
    assert center.source.absorbed_power_va.to_complex() == pytest.approx(-1)
    diagram = _diagram(("r", "l", "c"))
    model = RLCModel.for_diagram(
        diagram,
        (
            _component(ElementKind.RESISTOR),
            _component(ElementKind.INDUCTOR),
            _component(ElementKind.CAPACITOR),
        ),
    )

    def current_at(omega: Rational) -> float:
        result = solve_rlc_ac(
            diagram,
            model,
            ACSolveSpec(
                _out(),
                ACVoltageDrive(_in(), _out(), GaussianComplex.from_parts(1)),
                PositiveAngularFrequency(omega),
            ),
        )
        return abs(result.branches[0].current_amperes_rms.to_complex())

    assert current_at(Rational(1)) > current_at(Rational(1, 2))
    assert current_at(Rational(1)) > current_at(Rational(2))


def test_nonsingular_lossless_inductor_is_not_banned():
    result = _solve(_diagram(("l",)), (_component(ElementKind.INDUCTOR),))
    assert result.branches[0].absorbed_power_va.to_complex() == pytest.approx(1j)
    assert result.source.absorbed_power_va.to_complex() == pytest.approx(-1j)
    assert result.diagnostics.minimum_resistor_absorbed_real_power_watts == 0.0


def test_exact_lossless_series_resonance_refuses_without_regularization():
    with pytest.raises(LosslessSingularResonanceError, match="no regularization"):
        _solve(
            _diagram(("l", "c")),
            (_component(ElementKind.INDUCTOR), _component(ElementKind.CAPACITOR)),
        )


def test_nonidentity_edge_binding_controls_component_assignment():
    diagram = _diagram(("r", "c"))
    result = _solve(
        diagram,
        (_component(ElementKind.CAPACITOR), _component(ElementKind.RESISTOR)),
        bindings=(RLCEdgeBinding(0, 1), RLCEdgeBinding(1, 0)),
    )
    assert [branch.component.kind for branch in result.branches] == [
        ElementKind.RESISTOR,
        ElementKind.CAPACITOR,
    ]
    assert result.branches[1].absorbed_power_va.to_complex() == pytest.approx(-0.5j)


def test_adverse_conditioning_and_mutated_solution_refuse(monkeypatch):
    diagram = _diagram(("r", "l", "c"))
    with pytest.raises(ConditioningRefusal):
        _solve(
            diagram,
            (
                _component(ElementKind.RESISTOR, 1, 10**12),
                _component(ElementKind.INDUCTOR),
                _component(ElementKind.CAPACITOR),
            ),
        )
    monkeypatch.setattr(
        circuit,
        "_solve",
        lambda matrix, rhs: __import__("numpy").zeros(matrix.shape[0], dtype=complex),
    )
    with pytest.raises(ACResidualError):
        _solve(_diagram(("r",)), (_component(ElementKind.RESISTOR),))


def test_nonfinite_conversion_refuses():
    with pytest.raises(ACNumericalRefusal):
        _solve(_diagram(("r",)), (_component(ElementKind.RESISTOR, 10**400),))
