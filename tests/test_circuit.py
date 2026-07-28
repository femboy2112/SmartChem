"""Exact open-resistor semantics and the narrow sparse DC MNA control."""
from __future__ import annotations

from fractions import Fraction
import warnings

import numpy as np
import pytest

import smartchem.circuit as circuit
from smartchem.circuit import (
    BoundaryLinearRelation,
    CircuitError,
    CircuitNumericalRefusal,
    CircuitResidualError,
    DCVoltageDrive,
    DCSolveSpec,
    FloatingCircuitError,
    PositiveResistance,
    Rational,
    ResistiveDCModel,
    blackbox_resistive_dc,
    solve_resistive_dc,
)
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
    identity as diagram_identity,
)


ELECTRICAL = PortKind.ELECTRICAL
ONE = Interface((ELECTRICAL,))
TWO = Interface((ELECTRICAL, ELECTRICAL))


def _input(index: int = 0) -> BoundaryRef:
    return BoundaryRef(BoundarySide.INPUT, index)


def _output(index: int = 0) -> BoundaryRef:
    return BoundaryRef(BoundarySide.OUTPUT, index)


def _a(name: str) -> ElementPortRef:
    return ElementPortRef(name, "a")


def _b(name: str) -> ElementPortRef:
    return ElementPortRef(name, "b")


def _components(*names: str) -> tuple[ComponentSlot, ...]:
    return tuple(ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names)


def _diagram(
    names: tuple[str, ...],
    junctions: tuple[tuple[str, tuple[object, ...]], ...],
    dom: Interface = ONE,
    cod: Interface = ONE,
) -> OpenDiagram:
    return OpenDiagram.build(
        dom,
        cod,
        _components(*names),
        tuple(Junction(name, ELECTRICAL, endpoints) for name, endpoints in junctions),
    )


def _resistances(diagram: OpenDiagram, *ohms: int | Rational) -> ResistiveDCModel:
    return ResistiveDCModel.for_diagram(
        diagram,
        tuple(PositiveResistance(value if type(value) is Rational else Rational(value)) for value in ohms),
    )


def _single(name: str = "r") -> OpenDiagram:
    return _diagram(
        (name,),
        (("positive", (_input(), _a(name))), ("negative", (_output(), _b(name)))),
    )


def _series() -> OpenDiagram:
    return _diagram(
        ("r0", "r1"),
        (
            ("positive", (_input(), _a("r0"))),
            ("middle", (_b("r0"), _a("r1"))),
            ("negative", (_b("r1"), _output())),
        ),
    )


def _parallel() -> OpenDiagram:
    return _diagram(
        ("r0", "r1"),
        (
            ("positive", (_input(), _a("r0"), _a("r1"))),
            ("negative", (_output(), _b("r0"), _b("r1"))),
        ),
    )


def _bridge() -> OpenDiagram:
    """The non-series/parallel five-edge control: P-L, L-N, P-R, R-N, L-R."""
    return _diagram(
        ("r0", "r1", "r2", "r3", "r4"),
        (
            ("positive", (_input(), _a("r0"), _a("r2"))),
            ("left", (_b("r0"), _a("r1"), _a("r4"))),
            ("right", (_b("r2"), _a("r3"), _b("r4"))),
            ("negative", (_output(), _b("r1"), _b("r3"))),
        ),
    )


def _bridge_left() -> OpenDiagram:
    """P -> (L,R), retaining the bridge rail in the left 1-to-2 fragment."""
    return _diagram(
        ("r0", "r2", "r4"),
        (
            ("positive", (_input(), _a("r0"), _a("r2"))),
            ("left", (_output(0), _b("r0"), _a("r4"))),
            ("right", (_output(1), _b("r2"), _b("r4"))),
        ),
        ONE,
        TWO,
    )


def _bridge_right() -> OpenDiagram:
    """(L,R) -> N, completing the bridge without a topology special case."""
    return _diagram(
        ("r1", "r3"),
        (
            ("left", (_input(0), _a("r1"))),
            ("right", (_input(1), _a("r3"))),
            ("negative", (_output(), _b("r1"), _b("r3"))),
        ),
        TWO,
        ONE,
    )


def _splitter() -> OpenDiagram:
    return _diagram((), (("split", (_input(), _output(0), _output(1))),), ONE, TWO)


def _merger() -> OpenDiagram:
    return _diagram((), (("merge", (_input(0), _input(1), _output())),), TWO, ONE)


def _cycle() -> OpenDiagram:
    """A distinct three-resistor triangular cycle, with one direct P-N chord."""
    return _diagram(
        ("r0", "r1", "r2"),
        (
            ("positive", (_input(), _a("r0"), _a("r2"))),
            ("middle", (_b("r0"), _a("r1"))),
            ("negative", (_output(), _b("r1"), _b("r2"))),
        ),
    )


def _spec(volts: int | Rational, *, reference: BoundaryRef | None = None) -> DCSolveSpec:
    return DCSolveSpec(
        _output() if reference is None else reference,
        DCVoltageDrive(_input(), _output(), volts if type(volts) is Rational else Rational(volts)),
    )


class TestExactBoundaryRelations:
    def test_identity_is_exact_open_wire_relation(self):
        diagram = diagram_identity(ONE)
        assert blackbox_resistive_dc(diagram, _resistances(diagram)) == BoundaryLinearRelation.identity(1)

    def test_series_is_diagram_composition_not_a_special_reducer(self):
        left, right = _single("left"), _single("right")
        whole = left.then(right)
        assert blackbox_resistive_dc(whole, _resistances(whole, 100, 200)) == (
            blackbox_resistive_dc(left, _resistances(left, 100)).then(
                blackbox_resistive_dc(right, _resistances(right, 200))
            )
        )
        # 300 V across 100+200 ohms gives one inward ampere and its cancelled return.
        assert blackbox_resistive_dc(whole, _resistances(whole, 100, 200)).contains_exact(
            (300, 0, 1, -1)
        )
        identity = diagram_identity(ONE)
        identity_model = _resistances(identity)
        assert blackbox_resistive_dc(left.then(identity), _resistances(left.then(identity), 100)) == (
            blackbox_resistive_dc(left, _resistances(left, 100)).then(
                blackbox_resistive_dc(identity, identity_model)
            )
        )

    def test_tensor_is_direct_product_of_relations(self):
        left, right = _single("left"), _single("right")
        whole = left.tensor(right)
        assert blackbox_resistive_dc(whole, _resistances(whole, 100, 200)) == (
            blackbox_resistive_dc(left, _resistances(left, 100)).tensor(
                blackbox_resistive_dc(right, _resistances(right, 200))
            )
        )

    def test_parallel_relation_has_exact_admittance_not_scalar_tensor(self):
        diagram = _parallel()
        relation = blackbox_resistive_dc(diagram, _resistances(diagram, 100, 200))
        assert relation.contains_exact((100, 0, Rational(3, 2), Rational(-3, 2)))

    def test_bridge_and_cycle_have_exact_relations(self):
        bridge, cycle = _bridge(), _cycle()
        assert blackbox_resistive_dc(bridge, _resistances(bridge, 100, 200, 300, 400, 500)).variable_count == 4
        assert blackbox_resistive_dc(cycle, _resistances(cycle, 100, 200, 300)).variable_count == 4

    def test_bridge_blackbox_is_compositional_with_explicit_edge_model_reordering(self):
        left, right = _bridge_left(), _bridge_right()
        assembled = left.then(right)
        # `then` preserves left-edge order followed by right-edge order: 100,300,500,200,400.
        whole = blackbox_resistive_dc(assembled, _resistances(assembled, 100, 300, 500, 200, 400))
        composed = blackbox_resistive_dc(left, _resistances(left, 100, 300, 500)).then(
            blackbox_resistive_dc(right, _resistances(right, 200, 400))
        )
        direct = _bridge()
        assert whole == composed == blackbox_resistive_dc(direct, _resistances(direct, 100, 200, 300, 400, 500))

    def test_parallel_is_split_tensor_merge_not_a_scalar_tensor(self):
        splitter, merger = _splitter(), _merger()
        left, right = _single("left"), _single("right")
        middle = left.tensor(right)
        whole = splitter.then(middle).then(merger)
        relation = blackbox_resistive_dc(splitter, _resistances(splitter)).then(
            blackbox_resistive_dc(middle, _resistances(middle, 100, 200))
        ).then(blackbox_resistive_dc(merger, _resistances(merger)))
        assert relation == blackbox_resistive_dc(whole, _resistances(whole, 100, 200))
        direct = _parallel()
        assert relation == blackbox_resistive_dc(direct, _resistances(direct, 100, 200))

    def test_alpha_renaming_and_junction_reordering_do_not_change_blackbox(self):
        first = _single("old")
        second = _diagram(
            ("new",),
            (("negative-renamed", (_output(), _b("new"))), ("positive-renamed", (_input(), _a("new")))),
        )
        bound_first = _resistances(first, 47)
        with pytest.raises(ValueError, match="exact OpenDiagram presentation"):
            blackbox_resistive_dc(second, bound_first)
        assert blackbox_resistive_dc(first, bound_first) == blackbox_resistive_dc(second, _resistances(second, 47))

    def test_relation_storage_is_digestible_rationals_not_fraction_instances(self):
        diagram = _single()
        relation = blackbox_resistive_dc(diagram, _resistances(diagram, 3))
        assert all(type(value) is Rational for row in relation.rref_rows for value in row)
        assert not any(type(value) is Fraction for row in relation.rref_rows for value in row)


class TestSparseMNA:
    def test_single_resistor_analytic_control(self):
        diagram = _single()
        result = solve_resistive_dc(diagram, _resistances(diagram, 100), _spec(10))
        assert [node.volts for node in result.nodes] == pytest.approx([10.0, 0.0])
        assert result.branches[0].current_amperes == pytest.approx(0.1)
        assert result.branches[0].absorbed_power_watts == pytest.approx(1.0)
        assert result.source.current_entering_positive_amperes == pytest.approx(-0.1)
        assert result.source.absorbed_power_watts == pytest.approx(-1.0)
        assert max(vars(result.diagnostics).values()) == pytest.approx(0.0)

    def test_series_analytic_control(self):
        diagram = _series()
        result = solve_resistive_dc(diagram, _resistances(diagram, 100, 200), _spec(12))
        assert [node.volts for node in result.nodes] == pytest.approx([12.0, 8.0, 0.0])
        assert [branch.current_amperes for branch in result.branches] == pytest.approx([0.04, 0.04])
        assert result.source.current_entering_positive_amperes == pytest.approx(-0.04)

    def test_parallel_analytic_control(self):
        diagram = _parallel()
        result = solve_resistive_dc(diagram, _resistances(diagram, 100, 200), _spec(10))
        assert [branch.current_amperes for branch in result.branches] == pytest.approx([0.1, 0.05])
        assert result.source.current_entering_positive_amperes == pytest.approx(-0.15)
        assert sum(branch.absorbed_power_watts for branch in result.branches) == pytest.approx(1.5)

    def test_asymmetric_five_edge_bridge_uses_the_same_stamping_path(self, monkeypatch):
        diagram = _bridge()
        called_edge_counts: list[int] = []
        original_assemble = circuit._assemble_mna

        def observed_assemble(*args, **kwargs):
            called_edge_counts.append(len(args[1]))
            return original_assemble(*args, **kwargs)

        monkeypatch.setattr(circuit, "_assemble_mna", observed_assemble)
        result = solve_resistive_dc(diagram, _resistances(diagram, 100, 200, 300, 400, 500), _spec(10))
        assert called_edge_counts == [5]
        assert [node.volts for node in result.nodes] == pytest.approx(
            [10.0, 6.580645161290322, 5.935483870967741, 0.0]
        )
        assert [branch.current_amperes for branch in result.branches] == pytest.approx(
            [0.03419354838709678, 0.03290322580645161, 0.013548387096774197,
             0.014838709677419354, 0.001290322580645162]
        )
        assert result.source.current_entering_positive_amperes == pytest.approx(-0.04774193548387098)
        assert sum(branch.absorbed_power_watts for branch in result.branches) == pytest.approx(0.47741935483870973)

    def test_cycle_control_and_exact_relation_crosscheck(self):
        diagram = _cycle()
        result = solve_resistive_dc(diagram, _resistances(diagram, 100, 200, 300), _spec(6))
        assert result.diagnostics.scaled_relation_residual < 1e-12
        assert result.diagnostics.scaled_kcl_residual < 1e-12

    def test_floating_internal_component_refuses_before_sparse_solver(self):
        diagram = _diagram(
            ("main", "floating"),
            (
                ("positive", (_input(), _a("main"))),
                ("negative", (_output(), _b("main"))),
                ("isolated", (_a("floating"), _b("floating"))),
            ),
        )
        model = _resistances(diagram, 100, 100)
        # A closed floating fragment is valid open syntax and has an exact relation; only a
        # grounded experiment must refuse to turn it into an authoritative numeric answer.
        assert blackbox_resistive_dc(diagram, model).variable_count == 4
        with pytest.raises(FloatingCircuitError, match="not connected"):
            solve_resistive_dc(diagram, model, _spec(10))

    def test_short_drive_refuses_when_boundary_ports_resolve_to_the_same_node(self):
        diagram = diagram_identity(ONE)
        with pytest.raises(CircuitError, match="same node"):
            solve_resistive_dc(
                diagram,
                _resistances(diagram),
                _spec(10),
            )

    def test_exact_values_that_underflow_in_mna_refuse(self):
        with pytest.raises(CircuitNumericalRefusal, match="underflowed"):
            diagram = _single()
            solve_resistive_dc(diagram, _resistances(diagram, Rational(1, 10**400)), _spec(1))

    def test_exact_resistance_that_overflows_in_mna_refuses(self):
        with pytest.raises(CircuitNumericalRefusal, match="cannot be represented"):
            diagram = _single()
            solve_resistive_dc(diagram, _resistances(diagram, Rational(10**400)), _spec(1))

    def test_exact_drive_that_overflows_in_mna_refuses(self):
        with pytest.raises(CircuitNumericalRefusal, match="cannot be represented"):
            diagram = _single()
            solve_resistive_dc(diagram, _resistances(diagram, 1), _spec(Rational(10**400)))

    def test_mutated_sparse_solution_cannot_pass_residual_gates(self, monkeypatch):
        monkeypatch.setattr(circuit, "_solve_sparse", lambda matrix, rhs: np.zeros(matrix.shape[0]))
        with pytest.raises(CircuitResidualError, match="residual gate"):
            diagram = _single()
            solve_resistive_dc(diagram, _resistances(diagram, 100), _spec(10))

    def test_sparse_rank_warning_is_a_named_refusal(self, monkeypatch):
        matrix = circuit.sparse.identity(1, format="csc")
        rhs = np.zeros(1)

        def warned_solve(*_args, **_kwargs):
            warnings.warn("rank", circuit.MatrixRankWarning)
            return np.zeros(1)

        monkeypatch.setattr(circuit, "spsolve", warned_solve)
        with pytest.raises(CircuitNumericalRefusal, match="singular"):
            circuit._solve_sparse(matrix, rhs)

    def test_source_boundary_currents_satisfy_the_exact_relation(self):
        diagram = _single()
        result = solve_resistive_dc(diagram, _resistances(diagram, 100), _spec(10))
        assert result.diagnostics.relation_residual == pytest.approx(0.0)
        assert result.diagnostics.scaled_relation_residual == pytest.approx(0.0)

    @pytest.mark.parametrize(
        ("resistances", "volts"),
        [((1,), 1), ((1,), -3), ((2, 3), 5), ((Rational(2, 3), Rational(5, 2)), -7)],
    )
    def test_small_exact_models_agree_with_sparse_points(self, resistances, volts):
        diagram = _single() if len(resistances) == 1 else _series()
        result = solve_resistive_dc(diagram, _resistances(diagram, *resistances), _spec(volts))
        assert result.diagnostics.scaled_kcl_residual < 1e-12
        assert result.diagnostics.scaled_constraint_residual < 1e-12
        assert result.diagnostics.scaled_power_residual < 1e-12
        assert result.diagnostics.scaled_relation_residual < 1e-12
