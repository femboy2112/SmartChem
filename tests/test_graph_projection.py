"""Graph projection contracts: typed bipartite incidence, no invented evidence, loud limits."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
import json

import pytest

from smartchem.category import Molecule
from smartchem.decompiler import build_decomposition, search_decomposition
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.routes import search_dags, search_routes
from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles, resonance_identity
from smartchem.graph_projection import (
    GraphArc,
    GraphNode,
    GraphProjectionError,
    project_decomposition,
    project_synthesis,
    render_dot,
    render_mermaid,
)


def _reaction_nodes(g):
    return [n for n in g.nodes if n.kind == "reaction"]


def _species_nodes(g):
    return [n for n in g.nodes if n.kind == "species"]


def test_water_formula_graph_is_complete_in_exact_declared_space():
    result = search_decomposition("H2O")
    graph = project_decomposition(result)
    assert graph.source_kind == "FORMULA_DECOMPOSITION"
    assert graph.search_status == result.receipt.status.value
    assert graph.receipt_digest == result.receipt.digest
    assert len(_reaction_nodes(graph)) == 1
    assert len(_species_nodes(graph)) == 3
    assert len(graph.arcs) == 3
    assert sum(a.multiplicity for a in graph.arcs if a.role == "consumes") == 1
    assert sorted(a.multiplicity for a in graph.arcs if a.role == "produces") == [1, 2]
    assert all(dict(n.attributes)["reaction_semantics"] == "ACCOUNTING_ONLY"
               for n in _reaction_nodes(graph))
    assert json.loads(graph.to_json()) == graph.to_payload()
    assert graph.digest == project_decomposition(search_decomposition("H2O")).digest


def test_formula_partial_search_is_never_laundered_into_completeness():
    # C3H6O decomposes to elemental buckets in exactly ONE edge, so no edge budget can
    # ever truncate an element-only search -- it is always complete.  Only a MOLECULAR
    # inventory widens the OR-alternative fan (here: 4 admissible partitions) enough for a
    # tiny edge cap to bite.  The projection must carry that incompleteness, never hide it.
    result = search_decomposition("C3H6O", inventory=("H2O", "CO2", "CH4"), max_edges=2)
    assert not result.receipt.complete_within_bounds
    assert result.receipt.status.value == "PARTIAL_RESULT_LIMIT"
    graph = project_decomposition(result)
    assert graph.search_status == "PARTIAL_RESULT_LIMIT"
    assert graph.search_status != "COMPLETE_WITHIN_BOUNDS"
    assert graph.receipt_digest == result.receipt.digest
    # Every returned edge is projected; a partial search exposes FEWER than the full fan.
    assert len(_reaction_nodes(graph)) == len(result.graph.edges)
    assert len(_reaction_nodes(graph)) < len(
        search_decomposition("C3H6O", inventory=("H2O", "CO2", "CH4")).graph.edges
    )
    # One of the three partial notes states plainly that a budget-stopped search stays incomplete.
    assert any("incomplete" in note.lower() for note in graph.notes)


def test_stocked_target_has_no_fake_reaction():
    original = build_decomposition("H2O", ("H2O",))
    graph = project_decomposition(original)
    assert len(graph.nodes) == 1
    assert graph.arcs == ()
    assert graph.receipt_digest is None
    assert graph.search_status == "COMPLETE"


def test_linear_synthesis_retains_all_multiplicity_without_claiming_completeness():
    h = Molecule.atom("H")
    h2 = Molecule.diatomic("H", "H")
    step = ExperimentStep.assembling(h2, (h, h), (h2,))
    route = ExperimentRoute(ROUTE_SCHEMA, (step,))
    before = route.digest
    graph = project_synthesis(route)
    assert route.digest == before
    assert graph.source_kind == "SYNTHESIS_ROUTE"
    assert graph.search_status == "UNATTESTED"
    assert graph.receipt_digest is None
    assert len(_reaction_nodes(graph)) == 1
    assert len(_species_nodes(graph)) == 2
    assert len(graph.arcs) == 2
    assert [(e.role, e.multiplicity) for e in graph.arcs
            if e.role == "consumes"] == [("consumes", 2)]
    assert [a.multiplicity for a in graph.arcs if a.role == "produces"] == [1]
    assert dict(_reaction_nodes(graph)[0].attributes)["evidence_status"] == "NOT_ASSESSED"


def test_convergent_synthesis_has_distinct_branches_and_one_join():
    h, cl = Molecule.atom("H"), Molecule.atom("Cl")
    h2 = Molecule.diatomic("H", "H")
    cl2 = Molecule.diatomic("Cl", "Cl")
    hcl = Molecule.diatomic("H", "Cl")
    a = ExperimentStep.assembling(h2, (h, h), (h2,))
    b = ExperimentStep.assembling(cl2, (cl, cl), (cl2,))
    join = ExperimentStep.assembling(hcl, (h2, cl2), (hcl, hcl))
    dag = SynthesisDAG.of(a, b, join)
    assert dag.is_convergent
    graph = project_synthesis(dag)
    assert graph.source_kind == "SYNTHESIS_DAG"
    assert len(_reaction_nodes(graph)) == 3
    assert len(_species_nodes(graph)) == 5
    assert len(graph.arcs) == 7
    assert sum(arc.multiplicity for arc in graph.arcs if arc.role == "produces") == 4
    assert len({n.id for n in graph.nodes}) == len(graph.nodes)
    assert graph.digest == project_synthesis(dag).digest


def test_wrong_result_kind_and_projection_limits_fail_closed():
    h = Molecule.atom("H")
    h2 = Molecule.diatomic("H", "H")
    route = ExperimentRoute(ROUTE_SCHEMA, (ExperimentStep.assembling(h2, (h, h), (h2,)),))
    with pytest.raises(GraphProjectionError, match="search-result kind"):
        project_synthesis(route, search_result=object())
    with pytest.raises(GraphProjectionError, match="limit exceeded"):
        project_decomposition(search_decomposition("H2O"), max_nodes=1)
    with pytest.raises(GraphProjectionError, match="limit exceeded"):
        project_synthesis(route, max_arcs=1)


def test_forger_cannot_invent_or_dangle_an_incidence_arc():
    graph = project_decomposition(search_decomposition("H2O"))
    with pytest.raises(GraphProjectionError, match="endpoint"):
        replace(graph, arcs=tuple(sorted(
            graph.arcs + (GraphArc("unknown", graph.target_id, "produces", 1),),
            key=lambda a: a.key())))
    with pytest.raises(GraphProjectionError, match="species -> reaction"):
        source, target = graph.target_id, graph.target_id
        replace(graph, arcs=tuple(sorted(
            graph.arcs + (GraphArc(source, target, "consumes", 1),), key=lambda a: a.key())))
    with pytest.raises(GraphProjectionError, match="duplicate incidence"):
        sample = graph.arcs[0]
        duplicate = GraphArc(sample.source, sample.target, sample.role,
                             sample.multiplicity + 1)
        replace(graph, arcs=tuple(sorted(graph.arcs + (duplicate,), key=lambda a: a.key())))
    with pytest.raises(GraphProjectionError, match="unique sorted"):
        replace(graph, nodes=graph.nodes + (graph.nodes[-1],))
    with pytest.raises(GraphProjectionError, match="attribute keys"):
        GraphNode("f:fake", "species", "fake", (("dup", "a"), ("dup", "b")))


def test_renderers_are_deterministic_and_escape_untrusted_labels():
    graph = project_decomposition(search_decomposition("H2O"))
    assert render_dot(graph) == render_dot(graph)
    assert render_mermaid(graph) == render_mermaid(graph)
    assert "digraph SmartChem" in render_dot(graph)
    assert "flowchart LR" in render_mermaid(graph)
    altered_nodes = tuple(
        replace(n, label='H2O\"]; evil -> something') if n.id == graph.target_id else n
        for n in graph.nodes
    )
    altered = replace(graph, nodes=altered_nodes)
    assert '\\\"' in render_dot(altered)
    assert "&quot;" in render_mermaid(altered)
    assert "#93;" in render_mermaid(altered)


def test_demo_runs_real_formula_search_and_marks_partial(capsys):
    from scripts.graph_projection_demo import main
    assert main(["formula", "H2O", "--format", "dot"]) == 0
    output = capsys.readouterr()
    assert "digraph SmartChem" in output.out
    assert "COMPLETE_WITHIN_BOUNDS" in output.out
    assert "status=COMPLETE_WITHIN_BOUNDS" in output.err

    # Partial requires a molecular inventory + a tiny cap (empty-inventory C3H6O is one edge).
    assert main(["formula", "C3H6O", "--inventory", "H2O", "CO2", "CH4",
                 "--max-edges", "2", "--format", "json"]) == 4
    output = capsys.readouterr()
    assert json.loads(output.out)["search_status"] == "PARTIAL_RESULT_LIMIT"
    assert json.loads(output.out)["search_status"] != "COMPLETE_WITHIN_BOUNDS"
    assert "receipt=" in output.err


def test_demo_runs_genuine_certified_dag_fixture(capsys):
    from scripts.graph_projection_demo import main
    assert main(["convergent-fixture", "--format", "mermaid"]) == 0
    output = capsys.readouterr()
    assert "flowchart LR" in output.out
    assert "search: UNATTESTED" in output.out
    assert "source=SYNTHESIS_DAG" in output.err


# Documented route/DAG searches (mirrors tests/test_routes.py); real objects, not toys.
_PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
_WATER = parse_smiles("O")
_ACOH = parse_smiles("CC(=O)O")
_ANH = parse_smiles("CC(=O)OC(=O)C")
_AMP = parse_smiles("Nc1ccc(O)cc1")
_ETAC = parse_smiles("CCOC(=O)C")
_DAG_REAGENTS = tuple(parse_smiles(s) for s in ("O", "CO", "CC(=O)O", "C=C", "CCO", "C=C=O"))


def test_attested_synthesis_binds_receipt_and_rejects_impostors():
    """The search_result=... path binds a real receipt and fails closed on impostors.

    This path was entirely unexercised by the initial contribution; its receipt binding
    compares receipt.target_identity_digest against resonance_identity(final_target), and
    those must share a hash space or every honest result would be falsely rejected.
    """
    routes = search_routes(_PARA, reagents=(_WATER, _ACOH, _ANH), available=(_AMP,), max_depth=3)
    assert routes.routes, "documented paracetamol search must return candidates"
    attested = project_synthesis(routes.routes[0], search_result=routes)
    assert attested.search_status == routes.receipt.status.value != "UNATTESTED"
    assert attested.receipt_digest == routes.receipt.digest

    dags = search_dags(_ETAC, reagents=_DAG_REAGENTS, available=(), max_depth=2)
    assert dags.dags, "documented ethyl-acetate DAG search must return candidates"
    attested_dag = project_synthesis(dags.dags[0], search_result=dags)
    assert attested_dag.search_status == dags.receipt.status.value
    assert attested_dag.receipt_digest == dags.receipt.digest

    # A route cannot borrow a DAG search's receipt (kind mismatch fails closed, checked first).
    with pytest.raises(GraphProjectionError, match="route kind disagrees"):
        project_synthesis(routes.routes[0], search_result=dags)
    # A candidate that is not a member of the supplied result cannot claim its receipt.
    h = Molecule.atom("H")
    h2 = Molecule.diatomic("H", "H")
    alien = ExperimentRoute(ROUTE_SCHEMA, (ExperimentStep.assembling(h2, (h, h), (h2,)),))
    with pytest.raises(GraphProjectionError, match="not a member"):
        project_synthesis(alien, search_result=routes)


def test_stoichiometry_multiset_reconstructs_from_incidence_with_negative_control():
    """Reconstruct each reaction's multiset from graph incidence; it must equal the source,
    and a single forged multiplicity must make the reconstruction DISagree (negative control)."""
    result = search_decomposition("C3H6O", inventory=("H2O", "CO2", "CH4"))
    graph = project_decomposition(result)
    for edge in result.graph.edges:
        rid = "r:" + edge.digest
        produced = Counter()
        for arc in graph.arcs:
            if arc.source == rid and arc.role == "produces":
                produced[arc.target] += arc.multiplicity
        authoritative = Counter({"f:" + p.digest: c for p, c in edge.products})
        assert produced == authoritative
        consumed = [(a.source, a.multiplicity) for a in graph.arcs
                    if a.target == rid and a.role == "consumes"]
        assert consumed == [("f:" + edge.reactant.digest, edge.reactant_multiplicity)]

    # Negative control: bump ONE produced multiplicity; the reconstruction no longer matches.
    victim = next(a for a in graph.arcs if a.role == "produces")
    forged = replace(graph, arcs=tuple(sorted(
        (replace(a, multiplicity=a.multiplicity + 1) if a.key() == victim.key() else a
         for a in graph.arcs), key=lambda a: a.key())))
    edge = next(e for e in result.graph.edges if "r:" + e.digest == victim.source)
    reconstructed = Counter()
    for arc in forged.arcs:
        if arc.source == victim.source and arc.role == "produces":
            reconstructed[arc.target] += arc.multiplicity
    authoritative = Counter({"f:" + p.digest: c for p, c in edge.products})
    assert reconstructed != authoritative
    assert forged.digest != graph.digest


def test_constitutional_isomers_are_distinct_species_nodes():
    """Two molecules with one formula but different constitution stay distinct species nodes:
    the projection keys identity on resonance constitution, never on the printed formula."""
    ethanol, dme = parse_smiles("CCO"), parse_smiles("COC")
    assert ethanol.formula == dme.formula  # identical molecular formula C2H6O ...
    assert resonance_identity(ethanol) != resonance_identity(dme)  # ... different constitution
    step = ExperimentStep.assembling(dme, (ethanol,), (dme,))  # atom-conserving isomerization
    graph = project_synthesis(ExperimentRoute(ROUTE_SCHEMA, (step,)))
    species = _species_nodes(graph)
    assert len({n.id for n in species}) == 2  # two distinct identity nodes, not collapsed
    assert len({dict(n.attributes)["formula"] for n in species}) == 1  # same printed formula
    assert len({dict(n.attributes)["structure_identity"] for n in species}) == 2  # distinct identity
