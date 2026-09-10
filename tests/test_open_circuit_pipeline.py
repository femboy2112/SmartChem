"""Item 1 / Move-5 evidence (EM scope): the second-domain circuit PIPELINE on the generic open SMC.

``from_circuit`` ingests an arbitrary production resistor network into ``open_core``; ``parallel`` constructs a
parallel block with an EXACT apex (the ``BoundaryLinearRelation.parallel`` merge, the correct-apex counterpart
to the ``plug_all`` hazard); ``CircuitRoute`` composes stages in series through the generic core; the domain
cost and Move-5 survival predicate read off the assembled apex.  Cross-checks are non-circular (the independent
Kirchhoff verifier).
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from smartchem.circuit import ResistiveDCModel, blackbox_resistive_dc
from smartchem.open_circuit_pipeline import (
    CircuitRoute,
    CircuitStage,
    equivalent_resistance,
    from_circuit,
    parallel,
    within_spec,
)
from smartchem.open_core import OpenDiagram as OCDiagram, canonicalize
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
from smartchem.open_resistor_diagram import ResistorDecoration, apex_matches_boundary, resistor_edge, resistor_relation
from smartchem.resistive_dc_schema import BoundaryLinearRelation, PositiveResistance, Rational

from experiments import open_circuit_pipeline_probe as probe

_E = PortKind.ELECTRICAL
_ONE = Interface((_E,))
_IN = BoundaryRef(BoundarySide.INPUT, 0)
_OUT = BoundaryRef(BoundarySide.OUTPUT, 0)


def _a(name):
    return ElementPortRef(name, "a")


def _b(name):
    return ElementPortRef(name, "b")


def _build(names, junctions):
    return OpenDiagram.build(
        _ONE, _ONE,
        tuple(ComponentSlot(n, ComponentKind.ELECTRICAL_TWO_TERMINAL) for n in names),
        tuple(Junction(nm, _E, ep) for nm, ep in junctions),
    )


def _model(diagram, *ohms):
    return ResistiveDCModel.for_diagram(diagram, tuple(PositiveResistance(Rational(o)) for o in ohms))


def _series():
    return _build(("r0", "r1"), (("p", (_IN, _a("r0"))), ("m", (_b("r0"), _a("r1"))), ("n", (_b("r1"), _OUT))))


def _parallel_net():
    return _build(("r0", "r1"), (("p", (_IN, _a("r0"), _a("r1"))), ("n", (_OUT, _b("r0"), _b("r1")))))


def test_probe_validate_and_frozen_hash():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


# ======================================================================================
# The relation-level parallel-merge primitive (BoundaryLinearRelation.parallel)
# ======================================================================================
class TestBoundaryRelationParallel:
    def test_parallel_of_two_resistors_is_the_closed_form(self):
        par = resistor_relation(100).parallel(resistor_relation(200))
        assert par == resistor_relation(Fraction(200, 3))

    def test_identical_resistors_halve(self):
        assert resistor_relation(100).parallel(resistor_relation(100)) == resistor_relation(50)

    def test_parallel_is_commutative(self):
        a, b = resistor_relation(30), resistor_relation(70)
        assert a.parallel(b) == b.parallel(a)

    def test_parallel_is_associative(self):
        a, b, c = resistor_relation(2), resistor_relation(3), resistor_relation(6)
        assert a.parallel(b).parallel(c) == a.parallel(b.parallel(c))  # 2||3||6 = 1

    def test_a_wire_in_parallel_shorts(self):
        # R || 0 (a wire) = 0
        assert resistor_relation(100).parallel(resistor_relation(0)) == resistor_relation(0)

    def test_mismatched_interfaces_are_refused(self):
        one = resistor_relation(100)                      # 1->1
        two = BoundaryLinearRelation.identity(2)          # 2->2
        with pytest.raises(ValueError):
            one.parallel(two)

    def test_parallel_only_composes_relations(self):
        with pytest.raises(TypeError):
            resistor_relation(100).parallel(object())


# ======================================================================================
# from_circuit: lift a production network into open_core with the exact whole-network apex
# ======================================================================================
class TestFromCircuit:
    def test_apex_equals_the_production_solver_relation(self):
        for dg, ohms in ((_series(), (100, 200)), (_parallel_net(), (100, 200))):
            model = _model(dg, *ohms)
            assert from_circuit(dg, model).decoration.relation == blackbox_resistive_dc(dg, model)

    def test_topology_is_one_resistor_hyperedge_per_structural_edge(self):
        lifted = from_circuit(_parallel_net(), _model(_parallel_net(), 100, 200))
        assert len(lifted.hyperedges) == 2
        assert all(edge.kind == "resistor" for edge in lifted.hyperedges)
        assert apex_matches_boundary(lifted)

    def test_functor_preserves_series_composition(self):
        # from_circuit(A).then(from_circuit(B)).apex == the solver on the old-core series A then B
        def single(name):
            return _build((name,), ((f"p{name}", (_IN, _a(name))), (f"n{name}", (_b(name), _OUT))))
        a_old, b_old = single("x"), single("y")
        composed = from_circuit(a_old, _model(a_old, 100)).then(from_circuit(b_old, _model(b_old, 200)))
        ab = a_old.then(b_old)
        assert composed.decoration.relation == blackbox_resistive_dc(ab, _model(ab, 100, 200))
        # ...and it agrees with the item-6 resistor_edge construction
        assert composed.decoration.relation == resistor_edge(100).then(resistor_edge(200)).decoration.relation

    def test_a_bridge_is_reconstructed(self):
        # a Wheatstone bridge is NOT series-parallel; from_circuit reconstructs it directly, canonicalize applies
        bridge = probe._bridge()
        lifted = from_circuit(bridge, _model(bridge, 3, 5, 7, 11, 13))
        assert apex_matches_boundary(lifted)
        canonicalize(lifted)  # the open_core quotient is available on the second domain

    def test_rejects_a_wrong_diagram_type(self):
        with pytest.raises(TypeError):
            from_circuit(resistor_edge(100), _model(_series(), 100, 200))  # an open_core diagram, not electrical


# ======================================================================================
# parallel(): compositional parallel construction with an exact apex (closes item-6's deferral)
# ======================================================================================
class TestDiagramParallel:
    def test_parallel_apex_is_exact_and_matches_from_circuit(self):
        par = parallel(resistor_edge(100), resistor_edge(200))
        # the PHYSICS (apex) matches the directly-reconstructed network, even though the hyperedge payload
        # labels differ (a legibility label, not physics): the apex + cost are the load-bearing equality.
        direct = from_circuit(_parallel_net(), _model(_parallel_net(), 100, 200))
        assert par.decoration.relation == direct.decoration.relation
        assert equivalent_resistance(par) == equivalent_resistance(direct) == Fraction(200, 3)

    def test_parallel_topology_merges_to_one_input_and_one_output(self):
        par = parallel(resistor_edge(100), resistor_edge(200))
        assert len(par.dom.ports) == 1 and len(par.cod.ports) == 1
        assert len(par.hyperedges) == 2
        assert apex_matches_boundary(par)

    def test_parallel_rejects_a_non_two_terminal_stage(self):
        block = resistor_edge(100).tensor(resistor_edge(200))  # a 2->2 diagram
        with pytest.raises(ValueError):
            parallel(block, resistor_edge(50))


# ======================================================================================
# equivalent_resistance: the domain cost, fail-closed on non-two-terminal / open apices
# ======================================================================================
class TestEquivalentResistance:
    def test_series_adds_and_parallel_is_the_product_over_sum(self):
        assert equivalent_resistance(resistor_edge(100).then(resistor_edge(200))) == Fraction(300)
        assert equivalent_resistance(parallel(resistor_edge(100), resistor_edge(200))) == Fraction(200, 3)

    def test_a_wire_has_zero_resistance(self):
        assert equivalent_resistance(resistor_edge(0)) == Fraction(0)

    def test_an_open_circuit_has_no_equivalent_resistance(self):
        open_relation = BoundaryLinearRelation.from_equations(1, 1, [[0, 0, 1, 0], [0, 0, 0, 1]])
        edge = resistor_edge(1)
        opened = OCDiagram(
            edge.dom, edge.cod, edge.input_nodes, edge.output_nodes, edge.node_ports, edge.hyperedges,
            ResistorDecoration(open_relation),
        )
        assert equivalent_resistance(opened) is None

    def test_a_non_two_terminal_diagram_has_no_scalar_resistance(self):
        assert equivalent_resistance(resistor_edge(100).tensor(resistor_edge(200))) is None  # 2->2

    def test_a_non_resistor_decoration_is_none(self):
        assert equivalent_resistance("not a diagram") is None


# ======================================================================================
# within_spec: the Move-5 survival predicate
# ======================================================================================
class TestWithinSpec:
    def test_in_band_survives_and_out_of_band_does_not(self):
        par = parallel(resistor_edge(100), resistor_edge(200))  # 200/3 ~= 66.7 ohms
        assert within_spec(par, 0, 100) is True
        assert within_spec(par, 100, 200) is False

    def test_an_open_circuit_never_survives(self):
        open_relation = BoundaryLinearRelation.from_equations(1, 1, [[0, 0, 1, 0], [0, 0, 0, 1]])
        edge = resistor_edge(1)
        opened = OCDiagram(
            edge.dom, edge.cod, edge.input_nodes, edge.output_nodes, edge.node_ports, edge.hyperedges,
            ResistorDecoration(open_relation),
        )
        assert within_spec(opened, 0, 10 ** 12) is False

    def test_reversed_bounds_are_refused(self):
        with pytest.raises(ValueError):
            within_spec(resistor_edge(100), 200, 100)


# ======================================================================================
# The route/step shape: stages compose in series through the generic open_core.then
# ======================================================================================
class TestCircuitRoute:
    def test_a_mixed_series_parallel_route_has_the_closed_form_cost(self):
        route = CircuitRoute.of(
            CircuitStage.resistor(100),
            CircuitStage.in_parallel(CircuitStage.resistor(200), CircuitStage.resistor(200)),  # 100
            CircuitStage.ingest(_series(), _model(_series(), 25, 25), label="ingested 50"),      # 50
        )
        assert route.equivalent_resistance == Fraction(250)
        assert apex_matches_boundary(route.assemble())

    def test_route_survival_reads_off_the_assembled_apex(self):
        route = CircuitRoute.of(CircuitStage.resistor(100), CircuitStage.resistor(150))  # 250 ohms
        assert route.within_spec(200, 300) is True
        assert route.within_spec(0, 100) is False

    def test_a_single_stage_route_is_that_stage(self):
        route = CircuitRoute.of(CircuitStage.resistor(470))
        assert route.equivalent_resistance == Fraction(470)

    def test_an_empty_route_is_refused(self):
        with pytest.raises(ValueError):
            CircuitRoute.of()

    def test_a_stage_must_be_two_terminal(self):
        block = resistor_edge(100).tensor(resistor_edge(200))  # 2->2
        with pytest.raises(ValueError):
            CircuitStage(block, "bad")

    def test_ingest_stage_lifts_a_production_network(self):
        stage = CircuitStage.ingest(_parallel_net(), _model(_parallel_net(), 100, 200), label="par")
        assert stage.equivalent_resistance == Fraction(200, 3)


# ======================================================================================
# Adversarial-review folds (evil-morty / dalembert / birdperson, before merge)
# ======================================================================================
class TestNegativeResistanceRefused:
    """The negative-R scope leak: the compositional path accepted an active element the ingest path refused."""

    def test_for_resistor_refuses_negative(self):
        from smartchem.open_resistor_diagram import for_resistor
        with pytest.raises(ValueError):
            for_resistor(-100)

    def test_resistor_edge_and_stage_refuse_negative(self):
        with pytest.raises(ValueError):
            resistor_edge(-100)
        with pytest.raises(ValueError):
            CircuitStage.resistor(-40)

    def test_a_wire_zero_is_still_allowed(self):
        assert equivalent_resistance(resistor_edge(0)) == Fraction(0)

    def test_equivalent_resistance_of_a_negative_apex_is_none(self):
        # a hand-built negative-R apex (now unreachable via construction) reads None, not a fabricated -R
        edge = resistor_edge(1)
        neg = OCDiagram(
            edge.dom, edge.cod, edge.input_nodes, edge.output_nodes, edge.node_ports, edge.hyperedges,
            ResistorDecoration(resistor_relation(-5)),
        )
        assert equivalent_resistance(neg) is None


class TestWithinSpecBounds:
    """within_spec honors the exact-bounds contract: ±inf for one-sided bands, finite floats refused."""

    def test_infinite_upper_bound_is_a_one_sided_band(self):
        import math
        assert within_spec(resistor_edge(100), 0, math.inf) is True
        assert within_spec(resistor_edge(100), 200, math.inf) is False

    def test_infinite_lower_bound_is_a_one_sided_band(self):
        import math
        assert within_spec(resistor_edge(100), -math.inf, 200) is True

    def test_finite_float_bound_is_refused(self):
        # Fraction(0.1) != 1/10 -- a finite float silently misjudges a band edge, so it is refused
        with pytest.raises(TypeError):
            within_spec(resistor_edge(100), 0, 0.1)


class TestTopologyIsLoadBearing:
    """The reconstructed topology is cross-checked, not decorative (both reviewers' central doubt)."""

    def test_from_circuit_topology_mirrors_the_source(self):
        bridge = probe._bridge()
        lifted = from_circuit(bridge, _model(bridge, 3, 5, 7, 11, 13))
        src = sorted((min(e.node_a, e.node_b), max(e.node_a, e.node_b)) for e in bridge.structural_edges())
        oc = sorted(
            (min(h.terminals[0].node, h.terminals[1].node), max(h.terminals[0].node, h.terminals[1].node))
            for h in lifted.hyperedges
        )
        assert src == oc

    def test_parallel_merge_topology_matches_direct_reconstruction(self):
        # parallel()'s hand-rolled node-merge canonicalizes byte-identically to from_circuit of the same network
        par = parallel(resistor_edge(100, name="r0"), resistor_edge(200, name="r1"))
        direct = from_circuit(_parallel_net(), _model(_parallel_net(), 100, 200))
        assert canonicalize(par) == canonicalize(direct)


class TestDistinctOracleAndMultiport:
    """The physically-distinct spanning-tree oracle (no Laplacian common-mode) and the multiport merge."""

    def test_equivalent_resistance_matches_the_spanning_tree_oracle(self):
        for dg, ohms in ((_series(), (100, 200)), (_parallel_net(), (100, 200)), (probe._bridge(), (3, 5, 7, 11, 13))):
            got = equivalent_resistance(from_circuit(dg, _model(dg, *ohms)))
            assert got == probe._spanning_tree_oracle(dg, *ohms)

    def test_multiport_parallel_is_physically_correct(self):
        n2 = probe._net_2to1(("r0", "r1"))
        apex = from_circuit(n2, _model(n2, 100, 200)).decoration.relation
        assert apex.dom_ports == 2 and apex.cod_ports == 1
        doubled = probe._net_2to1_doubled(("r0", "r1", "r2", "r3"))
        expected = from_circuit(doubled, _model(doubled, 100, 200, 100, 200)).decoration.relation
        assert apex.parallel(apex) == expected
