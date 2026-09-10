"""Move-5 evidence (EM scope): the circuit-route SELECTOR -- the open-circuit pipeline's first NON-TEST caller.

Covers the selector logic (rank by exact cost, gate on the ``within_spec`` survival predicate, fail-closed
disclosure), the up-front band validation (the ``vacuous-green-over-an-empty-subject`` pin: a bad band is refused
even on an empty candidate set), the ingest path reaching the selector (``from_circuit`` -> ``CircuitStage.ingest``
-> a ranked candidate), an open-circuit (``None`` cost) candidate that never survives, and the minimal
fail-closed ``python -m smartchem.circuit_selection`` driver.
"""
from __future__ import annotations

import math
from fractions import Fraction

import pytest

from smartchem.circuit import ResistiveDCModel
from smartchem.circuit_selection import (
    CircuitCandidate,
    CircuitSelection,
    RankedCandidate,
    main,
    select_within_spec,
    _parse_bound,
    _parse_resistor_spec,
)
from smartchem.open_circuit_pipeline import CircuitRoute, CircuitStage
from smartchem.open_core import OpenDiagram as OCDiagram
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
from smartchem.open_resistor_diagram import ResistorDecoration, resistor_edge
from smartchem.resistive_dc_schema import BoundaryLinearRelation, PositiveResistance, Rational

_E = PortKind.ELECTRICAL
_ONE = Interface((_E,))
_IN = BoundaryRef(BoundarySide.INPUT, 0)
_OUT = BoundaryRef(BoundarySide.OUTPUT, 0)


def _series_net():
    return OpenDiagram.build(
        _ONE, _ONE,
        (ComponentSlot("r0", ComponentKind.ELECTRICAL_TWO_TERMINAL),
         ComponentSlot("r1", ComponentKind.ELECTRICAL_TWO_TERMINAL)),
        (Junction("p", _E, (_IN, ElementPortRef("r0", "a"))),
         Junction("m", _E, (ElementPortRef("r0", "b"), ElementPortRef("r1", "a"))),
         Junction("n", _E, (ElementPortRef("r1", "b"), _OUT))),
    )


def _model(diagram, *ohms):
    return ResistiveDCModel.for_diagram(diagram, tuple(PositiveResistance(Rational(o)) for o in ohms))


def _resistor_route(*ohms) -> CircuitRoute:
    return CircuitRoute.of(*(CircuitStage.resistor(o) for o in ohms))


def _open_circuit_route() -> CircuitRoute:
    open_relation = BoundaryLinearRelation.from_equations(1, 1, [[0, 0, 1, 0], [0, 0, 0, 1]])
    edge = resistor_edge(1)
    opened = OCDiagram(
        edge.dom, edge.cod, edge.input_nodes, edge.output_nodes, edge.node_ports, edge.hyperedges,
        ResistorDecoration(open_relation),
    )
    return CircuitRoute.of(CircuitStage(opened, "open"))


# ======================================================================================
# select_within_spec: rank by exact cost, gate on the survival predicate, disclose rejects
# ======================================================================================
class TestSelectWithinSpec:
    def test_survivors_are_ordered_by_exact_resistance_then_name(self):
        sel = select_within_spec(
            [
                CircuitCandidate("b_8", _resistor_route(4, 4)),         # 8
                CircuitCandidate("a_5", _resistor_route(2, 3)),         # 5
                CircuitCandidate("c_20", _resistor_route(20)),         # 20 (out of band)
            ],
            5, 10,
        )
        assert type(sel) is CircuitSelection
        assert all(type(r) is RankedCandidate for r in sel.within_spec)
        assert [(r.name, r.equivalent_resistance) for r in sel.within_spec] == [
            ("a_5", Fraction(5)), ("b_8", Fraction(8)),
        ]
        assert sel.rejected == (("c_20", Fraction(20)),)
        assert sel.best.name == "a_5"

    def test_ties_break_on_name_deterministically(self):
        sel = select_within_spec(
            [CircuitCandidate("zeta", _resistor_route(5)), CircuitCandidate("alpha", _resistor_route(5))],
            0, 10,
        )
        assert [r.name for r in sel.within_spec] == ["alpha", "zeta"]

    def test_no_survivor_gives_none_best(self):
        sel = select_within_spec([CircuitCandidate("c_20", _resistor_route(20))], 0, 10)
        assert sel.within_spec == ()
        assert sel.best is None

    def test_exact_fraction_bound_at_the_edge(self):
        route = _resistor_route(2, 3)  # exactly 5
        assert select_within_spec([CircuitCandidate("x", route)], Fraction(5), Fraction(5)).best is not None
        assert select_within_spec([CircuitCandidate("x", route)], Fraction(6), Fraction(7)).best is None

    def test_one_sided_band_with_inf(self):
        sel = select_within_spec(
            [CircuitCandidate("a", _resistor_route(5)), CircuitCandidate("b", _resistor_route(9000))],
            5, math.inf,
        )
        assert {r.name for r in sel.within_spec} == {"a", "b"}

    def test_a_wire_r0_is_a_valid_finite_survivor(self):
        sel = select_within_spec([CircuitCandidate("wire", _resistor_route(0))], 0, 10)
        assert sel.best.equivalent_resistance == Fraction(0)

    def test_candidate_cost_property_matches_its_route(self):
        # CircuitCandidate.equivalent_resistance is the cost the selector ranks on (its live consumer)
        cand = CircuitCandidate("x", _resistor_route(2, 3))
        assert cand.equivalent_resistance == Fraction(5)
        assert CircuitCandidate("open", _open_circuit_route()).equivalent_resistance is None


# ======================================================================================
# Fail-closed: bad band up front (even empty), open-circuit disclosure, type gates
# ======================================================================================
class TestFailClosed:
    def test_inverted_band_is_refused_even_on_empty_candidates(self):
        # the vacuous-green lesson: a spec check that only fires on a non-empty subject passes a bad band silently
        with pytest.raises(ValueError):
            select_within_spec([], 10, 5)

    def test_finite_float_bound_is_refused(self):
        with pytest.raises(TypeError):
            select_within_spec([CircuitCandidate("a", _resistor_route(5))], 0.1, 10)

    def test_open_circuit_candidate_never_survives_and_is_disclosed_with_none_cost(self):
        sel = select_within_spec([CircuitCandidate("open", _open_circuit_route())], 0, 10 ** 12)
        assert sel.within_spec == ()
        assert sel.rejected == (("open", None),)

    def test_non_candidate_input_is_refused(self):
        with pytest.raises(TypeError):
            select_within_spec([("a", _resistor_route(5))], 0, 10)  # a raw tuple, not a CircuitCandidate

    def test_candidate_validation(self):
        with pytest.raises(ValueError):
            CircuitCandidate("", _resistor_route(5))
        with pytest.raises(TypeError):
            CircuitCandidate("a", _resistor_route(5).assemble())  # an OpenDiagram, not a CircuitRoute


# ======================================================================================
# The ingest path reaches the selector: from_circuit -> CircuitStage.ingest -> a ranked candidate
# ======================================================================================
class TestIngestReachesSelector:
    def test_an_ingested_production_network_is_a_rankable_candidate(self):
        ingested = CircuitStage.ingest(_series_net(), _model(_series_net(), 25, 25), label="ingested 50")  # 50 ohms
        route = CircuitRoute.of(ingested)
        sel = select_within_spec(
            [CircuitCandidate("ingested", route), CircuitCandidate("composed", _resistor_route(10, 10))],
            0, 100,
        )
        # both survive; the composed 20-ohm design ranks ahead of the ingested 50-ohm network
        assert [r.name for r in sel.within_spec] == ["composed", "ingested"]
        assert dict((r.name, r.equivalent_resistance) for r in sel.within_spec)["ingested"] == Fraction(50)

    def test_ingested_and_composed_in_one_route(self):
        route = CircuitRoute.of(
            CircuitStage.ingest(_series_net(), _model(_series_net(), 25, 25), label="ingested 50"),
            CircuitStage.resistor(10),
        )
        sel = select_within_spec([CircuitCandidate("mixed", route)], 0, 100)
        assert sel.best.equivalent_resistance == Fraction(60)


# ======================================================================================
# The fail-closed parser + the python -m driver
# ======================================================================================
class TestParser:
    def test_series_and_parallel_and_mixed(self):
        assert _parse_resistor_spec("2,3").equivalent_resistance == Fraction(5)
        assert _parse_resistor_spec("12|12").equivalent_resistance == Fraction(6)
        assert _parse_resistor_spec("2,3,4|4").equivalent_resistance == Fraction(7)  # 2 -> 3 -> (4||4)
        assert _parse_resistor_spec("6|6|6").equivalent_resistance == Fraction(2)   # n-way parallel folds

    @pytest.mark.parametrize("bad", ["2,-3", "2,x", "2.5", "", "2,3|", "|4", "2, ,3", "٣", "2,٣", "5²"])
    def test_malformed_specs_are_refused(self, bad):
        # includes non-ASCII decimals ('٣') and superscripts ('²'): the plain-integer contract is ASCII-only,
        # so an over-generous isdigit() never slips a non-ASCII token through (adversarial review, evil-morty)
        with pytest.raises(ValueError):
            _parse_resistor_spec(bad)

    def test_bounds_parse(self):
        assert _parse_bound("10") == 10
        assert _parse_bound("inf") == math.inf
        assert _parse_bound("+inf") == math.inf
        # -inf is NOT a CLI bound (a -inf floor is meaningless for a non-negative resistance, and argparse would
        # strand it anyway); non-ASCII decimals and non-integers are refused
        for bad in ("1.5", "-inf", "-5", "٣", "²", "abc"):
            with pytest.raises(ValueError):
                _parse_bound(bad)


class TestMain:
    def test_selection_exit_zero(self, capsys):
        rc = main(["--band", "5", "10", "--candidate", "a=2,3", "--candidate", "c=20"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "best: a" in out
        assert "reject   c" in out

    def test_no_survivor_exit_three(self, capsys):
        rc = main(["--band", "1", "4", "--candidate", "c=20"])
        assert rc == 3
        assert "no candidate met spec" in capsys.readouterr().out

    def test_bad_band_exit_two(self, capsys):
        rc = main(["--band", "x", "4", "--candidate", "c=20"])
        assert rc == 2
        assert "circuit_selection:" in capsys.readouterr().err

    def test_bad_candidate_shape_exit_two(self, capsys):
        rc = main(["--band", "0", "10", "--candidate", "noeq"])
        assert rc == 2

    def test_inverted_band_exit_two(self, capsys):
        rc = main(["--band", "10", "5", "--candidate", "a=5"])
        assert rc == 2
