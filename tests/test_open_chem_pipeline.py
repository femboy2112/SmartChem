"""Move-1 keystone Rung C: the pipeline speaks open-diagram.

``ExperimentRoute.open()`` and ``SynthesisDAG.open()`` project a whole multi-step synthesis onto ONE
:class:`~smartchem.open_chem_diagram.OpenChemDiagram`, gluing at the shared intermediates via the new
``plug_all`` partial-pushout primitive.  A real route step carries byproducts and fresh reagents, so its
codomain never equals the next step's domain -- the whole-vessel ``then``/``Reaction.then`` cannot chain
it; ``plug_all`` (glue a chosen subset of ports, keep the rest boundary) is the open-morphism composition
the backbone promised.  These gates pin: saturation + conservation-as-closure (P1/P3), the topology-derived
provenance DAG (P4, occurrence-aware over distinct steps), the ``canonicalize`` congruence through
``tensor``/``plug_all``, and the three Rung-B tracked debts this rung closes (2 tensor coherence,
3 occurrence collision, 5 self-incidence).
"""
import pytest

from smartchem.category import Config, Reaction
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.open_chem_diagram import (
    ConservationStatus,
    OpenDiagramError,
    PortState,
    canonicalize,
)
from smartchem.open_core import (
    DiagramCompositionError,
    Hyperedge,
    Interface,
    OpenDiagram,
    Terminal,
    UNIT_DECORATION,
)
from smartchem.smiles import parse_smiles as M


def _step(reactants, products, target):
    return ExperimentStep.assembling(target, tuple(reactants), tuple(products))


# fixtures: an ester chain with a real byproduct + reagent leaf
ANH = M("CC(=O)OC(C)=O")   # acetic anhydride  C4H6O3
WATER = M("O")
ACOH = M("CC(=O)O")        # acetic acid  C2H4O2
ETOH = M("CCO")
ETOAC = M("CCOC(C)=O")     # ethyl acetate  C4H8O2
ETHYLENE = M("C=C")


def _ester_route() -> ExperimentRoute:
    s1 = _step([ANH, WATER], [ACOH, ACOH], ACOH)      # target acetic acid, water a leaf input
    s2 = _step([ACOH, ETOH], [ETOAC, WATER], ETOAC)   # target ethyl acetate, water a byproduct
    return ExperimentRoute.of(s1, s2)


def _convergent_dag() -> SynthesisDAG:
    sa = _step([ANH, WATER], [ACOH, ACOH], ACOH)      # branch A
    sb = _step([ETHYLENE, WATER], [ETOH], ETOH)       # branch B
    sj = _step([ACOH, ETOH], [ETOAC, WATER], ETOAC)   # the join
    return SynthesisDAG.of(sa, sb, sj)


# ======================================================================================
# Gate C1 -- ExperimentRoute.open(): saturation, conservation-as-closure, provenance
# ======================================================================================
class TestRouteProjection:
    def test_a_conserving_route_projects_to_a_saturated_conserving_diagram(self):
        diagram = _ester_route().open()
        assert diagram.is_saturated
        assert diagram.conservation_status() is ConservationStatus.CONSERVING

    def test_the_additive_conservation_decoration_agrees_with_the_verdict(self):
        # the cross-check the Rung-B review demanded, extended to a multi-step route
        assert _ester_route().open().apex.conservation.is_balanced is True

    def test_provenance_is_the_linear_step_chain(self):
        route = _ester_route()
        prov = route.open().apex.provenance
        assert len(prov.nodes) == len(route.steps)
        assert len(prov.deps) == route.n_transitions
        assert len(prov.linearization()) == len(route.steps)

    def test_the_carried_intermediate_is_internal_the_byproduct_and_leaves_external(self):
        diagram = _ester_route().open()
        states = {diagram.port_state(n) for n in range(len(diagram.core.node_ports))}
        assert PortState.INTERNAL in states   # the carried acetic acid
        assert PortState.EXTERNAL in states   # leaves + byproduct water + target
        assert PortState.OPEN not in states   # a full route has no unfilled slot

    def test_net_reaction_is_the_conserving_overall_equation(self):
        net = _ester_route().open().net_reaction()
        assert type(net) is Reaction
        assert net.dom.formula == net.cod.formula and net.dom.charge == net.cod.charge

    def test_each_provenance_step_matches_its_own_step_certificate(self):
        # P3 preserved per node: a projected step's endpoints are its own reactants/products
        route = _ester_route()
        prov = route.open().apex.provenance
        by_target = {node.target: node for node in prov.nodes}
        for step in route.steps:
            node = by_target[Config.of(*step.products)]
            assert node.source == Config.of(*step.reactants)


# ======================================================================================
# Gate C3 -- SynthesisDAG.open(): the branching causal DAG, close() refuses, net conserves
# ======================================================================================
class TestConvergentDagProjection:
    def test_a_convergent_dag_projects_and_conserves(self):
        dag = _convergent_dag()
        diagram = dag.open()
        assert dag.is_convergent
        assert diagram.is_saturated
        assert diagram.conservation_status() is ConservationStatus.CONSERVING
        assert diagram.apex.conservation.is_balanced is True

    def test_provenance_deps_match_the_dag_edges(self):
        dag = _convergent_dag()
        prov = dag.open().apex.provenance
        assert len(prov.nodes) == len(dag.steps)
        # one dependency per producer->consumer edge (P4), occurrence-aware over the distinct steps
        assert len(prov.deps) == len(dag.edges)
        dep_targets = {(p.target, c.target) for p, c in prov.deps}
        edge_targets = {
            (Config.of(*dag.steps[i].products), Config.of(*dag.steps[j].products))
            for i, j, _m in dag.edges
        }
        assert dep_targets == edge_targets

    def test_a_convergent_history_has_no_single_reaction_path(self):
        with pytest.raises(OpenDiagramError):
            _convergent_dag().open().close()

    def test_the_convergent_net_reaction_conserves(self):
        net = _convergent_dag().open().net_reaction()
        assert net.dom.formula == net.cod.formula and net.dom.charge == net.cod.charge


# ======================================================================================
# Gate C4 -- interchange invariance (provenance / net) + the boundary-order tripwire
# ======================================================================================
class TestCongruenceAndInvariance:
    def test_provenance_and_net_are_invariant_under_step_reordering(self):
        # the interchange-invariant reads are content/multiset-valued, so a step reorder cannot move them
        sa = _step([ANH, WATER], [ACOH, ACOH], ACOH)
        sb = _step([ETHYLENE, WATER], [ETOH], ETOH)
        sj = _step([ACOH, ETOH], [ETOAC, WATER], ETOAC)
        one = SynthesisDAG.of(sa, sb, sj).open()
        other = SynthesisDAG.of(sb, sa, sj).open()
        assert one.apex.provenance == other.apex.provenance
        assert one.net_reaction() == other.net_reaction()

    def test_canonicalize_respects_boundary_order_and_does_not_over_merge(self):
        # boundary order IS identity (Rung B): a step reorder permutes the EXTERNAL leaf ports, so the
        # canonical forms DIFFER -- the quotient is up to internal relabelling, not up to a boundary
        # braid.  A differential tripwire against a canonicalizer that silently over-quotients boundaries.
        sa = _step([ANH, WATER], [ACOH, ACOH], ACOH)
        sb = _step([ETHYLENE, WATER], [ETOH], ETOH)
        sj = _step([ACOH, ETOH], [ETOAC, WATER], ETOAC)
        one = canonicalize(SynthesisDAG.of(sa, sb, sj).open())
        other = canonicalize(SynthesisDAG.of(sb, sa, sj).open())
        assert one.dom != other.dom  # the leaf-input order is genuinely different
        assert one != other

    def test_interchange_equivalent_tensor_orders_have_equal_provenance(self):
        sa = _step([ANH, WATER], [ACOH, ACOH], ACOH)
        sb = _step([ETHYLENE, WATER], [ETOH], ETOH)
        left = sa.open().tensor(sb.open())
        right = sb.open().tensor(sa.open())
        assert left.apex.provenance == right.apex.provenance  # no deps yet; equal (empty-DAG) provenance


# ======================================================================================
# Rung-B tracked debts this rung closes
# ======================================================================================
class TestClosedDebts:
    def test_debt3_identical_steps_fail_closed_rather_than_merge(self):
        # two structurally identical hyperedges in one diagram -> ambiguous provenance -> refuse
        step = _step([ANH, WATER], [ACOH, ACOH], ACOH)
        doubled = step.open().tensor(step.open())
        with pytest.raises(OpenDiagramError):
            _ = doubled.apex

    def test_debt5_edge_incidence_counts_distinct_generators_not_terminals(self):
        # a node touched twice by ONE hyperedge is incident to one generator (not "internal")
        edge = Hyperedge("reaction", "", (Terminal("reactant", 0), Terminal("product", 0)))
        core = OpenDiagram(Interface(()), Interface(()), (), (), ("a",), (edge,), UNIT_DECORATION)
        assert core.terminal_incidence() == (2,)
        assert core.edge_incidence() == (1,)

    def test_debt2_gluing_is_by_token_not_by_port_position(self):
        # the carried intermediate is the producing step's SECOND product (byproduct first); a positional
        # glue would union the byproduct (token mismatch -> raise), so a clean projection PROVES token match
        s1 = _step([ANH, ETOH], [ACOH, ETOAC], ETOAC)     # products [acetic acid, ethyl acetate]; target = ethyl acetate (index 1)
        s2 = _step([ETOAC, WATER], [ACOH, ETOH], ACOH)    # hydrolysis consumes ethyl acetate
        diagram = ExperimentRoute.of(s1, s2).open()
        assert diagram.is_saturated
        assert diagram.conservation_status() is ConservationStatus.CONSERVING
        assert len(diagram.apex.provenance.deps) == 1


# ======================================================================================
# plug_all primitive -- direct unit test of the partial pushout
# ======================================================================================
class TestPlugAllPrimitive:
    def test_plug_all_rejects_reusing_a_boundary_port(self):
        diagram = _ester_route().open()
        with pytest.raises(DiagramCompositionError):
            diagram.core.plug_all(((0, 0), (0, 1)))  # output position 0 reused

    def test_plug_all_rejects_a_token_mismatch(self):
        # tensoring two unrelated single steps then plugging mismatched species must refuse
        left = _step([ANH, WATER], [ACOH, ACOH], ACOH).open()
        right = _step([ETHYLENE, WATER], [ETOH], ETOH).open()
        combined = left.tensor(right)
        # output 0 is one of left's products (acetic acid); input for right's ethanol side won't match it
        with pytest.raises(DiagramCompositionError):
            # find an output/input pair that carries different tokens
            combined.core.plug_all(((0, len(left.core.dom.ports)),))
