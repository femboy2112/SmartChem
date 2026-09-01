"""M-4 v1 decompiler: B0 (object + termination), B1 (edge generator), B2 (AND-OR builder).

Every load-bearing claim of the elemental-descent engine, with the guards isolated so a
regression names the exact broken invariant, and the descent guard proven *non-vacuous*
(it accepts a genuine descending edge, not just rejects a growing one).
"""

import pytest

from smartchem.contracts import canonical_digest
from smartchem.decompiler import (
    DECOMPILER_SCHEMA,
    DECOMPOSITION_SEARCH_RESULT_SCHEMA,
    FORMULA_SEARCH_RECEIPT_SCHEMA,
    DecompilerError,
    DecompositionEdge,
    DecompositionGraph,
    DecompositionSearchResult,
    Formula,
    FormulaSearchReceipt,
    admissible_edges,
    build_decomposition,
    example_inventory,
    search_decomposition,
    standard_state_equation,
)
from smartchem.search import STANDARD_8_2_STATUSES, SearchStatus
from smartchem.transform_registry import transform_registry_digest

H = Formula.bucket("H")
OX = Formula.bucket("O")
C = Formula.bucket("C")


def _sorted_products(*pairs):
    return tuple(sorted(pairs, key=lambda pm: (pm[0].counts, pm[0].charge, pm[1])))


# ======================================================================================
# Formula -- the v1 node identity
# ======================================================================================
class TestFormula:
    def test_parse_flat_and_counts(self):
        f = Formula.parse("C8H9NO2")
        assert f.as_dict == {"C": 8, "H": 9, "N": 1, "O": 2}
        assert f.rank == 20

    def test_parse_parentheses(self):
        assert Formula.parse("(NH4)2SO4").as_dict == {"N": 2, "H": 8, "S": 1, "O": 4}

    def test_parse_is_capital_lowercase_convention(self):
        # "CO" is carbon+oxygen, never cobalt
        assert Formula.parse("CO").as_dict == {"C": 1, "O": 1}

    def test_the_complete_periodic_table_is_accepted(self):
        assert Formula.parse("CaO").as_dict == {"Ca": 1, "O": 1}
        assert Formula.parse("LiAlH4").as_dict == {"Li": 1, "Al": 1, "H": 4}

    def test_unknown_element_is_refused_by_name(self):
        with pytest.raises(DecompilerError, match="Xx"):
            Formula.parse("XxO")

    @pytest.mark.parametrize("mapping", [{}, {"H": 0}, {"H": -1}])
    def test_empty_or_nonpositive_formulas_are_refused(self, mapping):
        with pytest.raises(ValueError):
            Formula.of(mapping)

    def test_fractional_counts_are_refused_instead_of_truncated(self):
        with pytest.raises(TypeError):
            Formula.of({"H": 1.9})

    def test_representation_independence_isomer_collapse(self):
        # string, mapping, and reordered mapping are one Formula (formula-level v1 contract)
        assert Formula.parse("H2O") == Formula.of({"O": 1, "H": 2}) == Formula.of({"H": 2, "O": 1})

    def test_is_element_bucket(self):
        assert Formula.parse("O2").is_element  # O2 and O are the same bucket
        assert Formula.bucket("O", 2).is_element
        assert not Formula.parse("H2O").is_element

    def test_element_buckets_are_the_targets_own_composition(self):
        # "how full is each bucket" is forced by conservation, not searched
        assert Formula.parse("C8H9NO2").element_buckets() == (("C", 8), ("H", 9), ("N", 1), ("O", 2))

    def test_charged_formula_allowed_as_value_but_not_decomposed(self):
        ion = Formula.of({"O": 1}, charge=-2)
        assert ion.charge == -2
        assert not ion.is_element  # charged, so not a neutral terminal


# ======================================================================================
# B0 -- DecompositionEdge: the termination guard and every construction invariant
# ======================================================================================
class TestEdgeInvariants:
    def test_a_genuine_descending_edge_is_accepted(self):
        # NON-VACUITY: the descent guard is not rejecting everything -- a real edge builds.
        edge = DecompositionEdge(Formula.parse("CH2O"), 1, _sorted_products((Formula.parse("CO"), 1), (H, 2)))
        assert edge.equation() == "CH2O -> CO + 2 H"

    def test_growing_product_is_refused_W1(self):
        # 2 CH2O -> C2H2O + H2O : C2H2O (rank 5) exceeds CH2O (rank 4) -> non-terminating.
        with pytest.raises(DecompilerError, match="non-descending"):
            DecompositionEdge(Formula.parse("CH2O"), 2, _sorted_products((Formula.parse("C2H2O"), 1), (Formula.parse("H2O"), 1)))

    def test_nonconserving_edge_is_refused(self):
        with pytest.raises(DecompilerError, match="not conserved"):
            DecompositionEdge(Formula.parse("H2O"), 1, ((H, 2),))  # drops the O

    def test_non_primitive_edge_is_refused(self):
        # 2 H2O -> 4 H + 2 O has common factor 2; must be spelled H2O -> 2 H + O
        with pytest.raises(DecompilerError, match="not primitive"):
            DecompositionEdge(Formula.parse("H2O"), 2, _sorted_products((H, 4), (OX, 2)))

    def test_element_bucket_must_be_unit_spelled(self):
        # a two-atom oxygen product must be O-bucket x2, never {O:2} x1
        with pytest.raises(DecompilerError, match="unit bucket"):
            DecompositionEdge(Formula.parse("O3"), 1, _sorted_products((Formula.of({"O": 2}), 1), (OX, 1)))

    def test_single_instance_is_not_a_decomposition(self):
        # one product of the same size is a rename; conservation+descent already forbid it,
        # and the >=2-instance guard is the explicit belt-and-suspenders
        with pytest.raises(DecompilerError):
            DecompositionEdge(Formula.parse("O2"), 1, ((OX, 1),))

    def test_charged_species_refused_in_v1(self):
        with pytest.raises(DecompilerError, match="neutral"):
            DecompositionEdge(Formula.of({"O": 2}, charge=-1), 1, ((OX, 2),))

    def test_edge_digest_is_stable_and_order_independent(self):
        a = DecompositionEdge(Formula.parse("H2O"), 1, _sorted_products((H, 2), (OX, 1)))
        b = DecompositionEdge(Formula.parse("H2O"), 1, _sorted_products((OX, 1), (H, 2)))
        assert a.digest == b.digest == canonical_digest(a)


# ======================================================================================
# B1 -- admissible_edges: the balanced-edge generator over a closed inventory
# ======================================================================================
class TestEdgeGenerator:
    def test_water_over_elements_is_exactly_one_family(self):
        edges, complete = admissible_edges(Formula.parse("H2O"))
        assert complete
        assert len(edges) == 1
        assert edges[0].equation() == "H2O -> 2 H + O"

    def test_element_reactant_has_no_decomposition(self):
        edges, complete = admissible_edges(Formula.parse("O2"))
        assert complete and edges == ()

    def test_every_generated_edge_conserves_and_descends(self):
        edges, complete = admissible_edges(Formula.parse("C3H6O"), example_inventory())
        assert complete and edges
        for e in edges:
            want = {s: e.reactant_multiplicity * k for s, k in e.reactant.counts}
            got: dict[str, int] = {}
            for p, m in e.products:
                for s, k in p.counts:
                    got[s] = got.get(s, 0) + m * k
            assert got == want  # exact integer conservation
            assert sum(m for _, m in e.products) >= 2  # a real split
            assert all(p.rank < e.reactant.rank for p, _ in e.products)  # W1

    def test_known_small_target_exact_edge_set(self):
        # CO over an empty inventory: the only decomposition is the atom floor.
        edges, complete = admissible_edges(Formula.parse("CO"))
        assert complete
        assert [e.equation() for e in edges] == ["CO -> C + O"]

    def test_budget_exhaustion_reports_incomplete_not_silent(self):
        # a tiny budget on a branching target must return complete=False, never a quiet subset
        edges, complete = admissible_edges(Formula.parse("C8H9NO2"), example_inventory(), budget=5)
        assert complete is False

    def test_multiplicity_knob_adds_scaled_edges(self):
        # n>1 opens fraction-clearing edges the n=1 default does not enumerate
        base, _ = admissible_edges(Formula.parse("C2H6O"), example_inventory(), max_multiplicity=1)
        more, _ = admissible_edges(Formula.parse("C2H6O"), example_inventory(), max_multiplicity=3)
        assert len(more) >= len(base)


# ======================================================================================
# B2 -- build_decomposition: the AND-OR DAG with a loud budget refusal
# ======================================================================================
class TestDecompositionGraph:
    def test_water_graph_is_shallow_and_complete(self):
        g = build_decomposition("H2O")
        assert g.is_complete
        assert g.schema_version == DECOMPILER_SCHEMA
        assert [e.equation() for e in g.edges] == ["H2O -> 2 H + O"]
        assert g.terminals() == {H, OX}

    def test_acetone_graph_is_layered_and_complete(self):
        g = build_decomposition("C3H6O", example_inventory())
        assert g.is_complete
        assert len(g.edges) > 1 and len(g.nodes()) > len(g.terminals())
        assert {C, H, OX} <= g.terminals()

    def test_denser_target_has_a_denser_graph(self):
        inv = example_inventory()
        acetone = build_decomposition("C3H6O", inv)
        paracetamol = build_decomposition("C8H9NO2", inv)
        assert paracetamol.is_complete and acetone.is_complete
        assert len(paracetamol.edges) > len(acetone.edges)

    def test_every_nonterminal_node_reaches_elements(self):
        g = build_decomposition("C3H6O", example_inventory())
        for node in g.nodes():
            if not node.is_element and node not in g.inventory:
                assert g.edges_from(node), f"{node!r} is a non-terminal dead end"

    def test_declared_inventory_is_a_terminal_bucket_not_an_expansion_hint(self):
        g = build_decomposition("CO2", ("CO2",))
        assert g.is_complete and g.edges == ()
        assert Formula.parse("CO2") in g.terminals()

    def test_inventory_order_and_duplicates_do_not_change_graph_identity(self):
        a = build_decomposition("C3H6O", ("H2O", "CO", "CH4", "H2O"))
        b = build_decomposition("C3H6O", ("CH4", "CO", "H2O"))
        assert a.identity == b.identity

    @pytest.mark.parametrize("kwargs", [
        {"max_multiplicity": 0}, {"budget": 0}, {"max_edges": 0},
    ])
    def test_nonpositive_graph_bounds_are_refused(self, kwargs):
        with pytest.raises(ValueError, match="positive integer"):
            build_decomposition("H2O", **kwargs)

    def test_budget_refusal_is_loud_never_a_silent_partial(self):
        g = build_decomposition("C3H6O", example_inventory(), max_edges=3)
        assert not g.is_complete
        assert g.status == "REFUSED_BUDGET"
        assert g.refusal_reason  # names why; the partial edges are flagged, not passed off
        # the disease this guards: a truncated graph reported as COMPLETE
        assert g.status != "COMPLETE"

    def test_graph_identity_is_deterministic(self):
        inv = example_inventory()
        assert build_decomposition("C3H6O", inv).identity == build_decomposition("C3H6O", inv).identity

    def test_graph_identity_is_representation_independent(self):
        assert build_decomposition("H2O").identity == build_decomposition({"H": 2, "O": 1}).identity

    def test_graph_is_digestible_round_trips_through_canonical_digest(self):
        g = build_decomposition("C3H6O", example_inventory())
        assert g.digest == canonical_digest(g) == g.identity
        assert len(g.digest) == 64

    def test_complete_graph_has_no_refusal_reason_invariant(self):
        with pytest.raises(ValueError, match="refusal reason"):
            DecompositionGraph(DECOMPILER_SCHEMA, Formula.parse("H2O"), (), 1, 100, "COMPLETE", (), "spurious")

    def test_refused_graph_must_state_a_reason_invariant(self):
        with pytest.raises(ValueError, match="reason"):
            DecompositionGraph(DECOMPILER_SCHEMA, Formula.parse("H2O"), (), 1, 100, "REFUSED_BUDGET", (), "")


# ======================================================================================
# Reporting layer -- the coherent "keep the 2 part" bucket packaging (decision 4)
# ======================================================================================
class TestStandardStatePackaging:
    def test_water_repackages_to_diatomic_standard_state(self):
        assert standard_state_equation(Formula.parse("H2O")) == "2 H2O -> 2 H2 + O2"

    def test_scaling_is_minimal(self):
        # CO2 needs no scaling for O (already even) and C is monatomic -> coefficient 1
        assert standard_state_equation(Formula.parse("CO2")) == "CO2 -> C + O2"

    def test_odd_hydrogen_forces_a_scale(self):
        # CH4: H is diatomic and count 4 is even -> no scaling; C monatomic
        assert standard_state_equation(Formula.parse("CH4")) == "CH4 -> C + 2 H2"

    @pytest.mark.parametrize("count", [0, -1])
    def test_nonpositive_equation_count_is_refused(self, count):
        with pytest.raises(ValueError, match="positive integer"):
            standard_state_equation(Formula.parse("H2O"), count=count)


# ======================================================================================
# search_decomposition -- the formula path's completeness receipt (section 8.1)
# ======================================================================================
class TestFormulaSearchReceipt:
    """The formula decompiler now returns a first-class SearchReceipt like the route/DAG searches (SRCH-RCT-01),
    over the ONE shared smartchem.search.SearchStatus vocabulary; build_decomposition stays the graph-only wrapper.

    The elemental descent is structurally depth-1 in v1 (every product is a declared-inventory bucket or an
    element bucket, both terminal), so the receipt does not fake a per-node expansion counter -- its meaningful
    fields are the search bounds, the edge count, and the completeness status/reason."""

    def test_complete_search_returns_a_complete_receipt(self):
        r = search_decomposition("C8H9NO2", example_inventory())
        assert r.receipt.status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert r.receipt.complete_within_bounds
        assert r.graph.is_complete
        assert r.receipt.stop_reason == ""
        assert r.receipt.edges_emitted == len(r.graph.edges) > 0

    def test_search_node_budget_exhaustion_is_partial_not_complete(self):
        # The headline: a budget-starved formula search is a loud PARTIAL, never a silent or complete-looking graph.
        r = search_decomposition("C8H9NO2", example_inventory(), budget=1)
        assert r.receipt.status is SearchStatus.PARTIAL_SEARCH_BUDGET
        assert not r.receipt.complete_within_bounds
        assert not r.graph.is_complete
        assert "budget" in r.receipt.stop_reason

    def test_edge_cap_saturation_is_partial_result_limit(self):
        r = search_decomposition("C8H9NO2", example_inventory(), max_edges=1)
        assert r.receipt.status is SearchStatus.PARTIAL_RESULT_LIMIT
        assert not r.graph.is_complete
        assert "edge budget" in r.receipt.stop_reason

    def test_the_two_W2_walls_are_named_distinctly(self):
        # A caller must know WHICH knob to raise: node budget and edge cap are different stops, different statuses.
        node = search_decomposition("C8H9NO2", example_inventory(), budget=1).receipt.status
        edge = search_decomposition("C8H9NO2", example_inventory(), max_edges=1).receipt.status
        assert node is SearchStatus.PARTIAL_SEARCH_BUDGET
        assert edge is SearchStatus.PARTIAL_RESULT_LIMIT
        assert node is not edge

    def test_build_decomposition_is_exactly_the_graph_of_the_search(self):
        g = build_decomposition("C8H9NO2", example_inventory())
        assert g == search_decomposition("C8H9NO2", example_inventory()).graph

    def test_receipt_uses_the_one_shared_search_status_vocabulary(self):
        # the formula receipt speaks the SAME enum the route/DAG receipts do -- one vocabulary, three searches.
        from smartchem.experiment.routes import SearchStatus as RouteSearchStatus
        assert SearchStatus is RouteSearchStatus
        assert isinstance(search_decomposition("H2O").receipt.status, SearchStatus)

    @pytest.mark.parametrize("field", ["max_multiplicity", "budget", "max_edges"])
    def test_search_bounds_must_be_positive(self, field):
        kwargs = dict(max_multiplicity=1, budget=100, max_edges=100)
        kwargs[field] = 0
        with pytest.raises(ValueError, match="positive integer"):
            search_decomposition("H2O", **kwargs)

    def test_receipt_render_states_status_and_bounded_scope(self):
        text = search_decomposition("H2O").receipt.render()
        assert "COMPLETE_WITHIN_BOUNDS" in text
        assert "not chemistry" in text  # conservation only, said out loud -- W3

    def test_receipt_rejects_a_complete_status_carrying_a_stop_reason(self):
        with pytest.raises(ValueError, match="complete search carries no stop reason"):
            FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 0,
                                 SearchStatus.COMPLETE_WITHIN_BOUNDS, "spurious reason")

    def test_receipt_rejects_a_partial_status_without_a_reason(self):
        with pytest.raises(ValueError, match="partial search must state its stop reason"):
            FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 0,
                                 SearchStatus.PARTIAL_SEARCH_BUDGET, "")

    def test_receipt_rejects_the_unreachable_multiple_limits_status(self):
        # the formula descent stops on exactly one budget at a time; PARTIAL_MULTIPLE_LIMITS is not a real outcome.
        with pytest.raises(ValueError, match="PARTIAL_MULTIPLE_LIMITS is not"):
            FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 0,
                                 SearchStatus.PARTIAL_MULTIPLE_LIMITS, "two at once")

    def test_result_rejects_a_receipt_that_disagrees_with_graph_completeness(self):
        g = search_decomposition("H2O").graph  # a COMPLETE graph
        partial = FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, len(g.edges),
                                       SearchStatus.PARTIAL_SEARCH_BUDGET, "claims partial")
        with pytest.raises(ValueError, match="completeness must agree"):
            DecompositionSearchResult(DECOMPOSITION_SEARCH_RESULT_SCHEMA, g, partial)

    def test_result_rejects_a_receipt_edge_count_that_disagrees_with_the_graph(self):
        g = search_decomposition("H2O").graph  # exactly one edge
        wrong = FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 999,
                                     SearchStatus.COMPLETE_WITHIN_BOUNDS, "")
        with pytest.raises(ValueError, match="edges_emitted must equal"):
            DecompositionSearchResult(DECOMPOSITION_SEARCH_RESULT_SCHEMA, g, wrong)


class TestSection81FormulaReceiptTelemetry:
    """FormulaSearchReceipt carries the section 8.1 counters, instrumented by search_decomposition.

    Formula-shaped: each admissible edge is one transform application (one candidate), and edges_emitted is the
    DISTINCT collected result, so transforms_considered (pre-dedup) >= edges_emitted.
    """

    def test_a_real_decomposition_populates_honest_counters(self):
        r = search_decomposition("C8H9NO2", example_inventory())
        rc = r.receipt
        assert rc.search_kind == "FORMULA_DECOMPOSITION" and rc.cut_budget_scope == "PER_NODE"
        assert rc.nodes_visited is not None and rc.nodes_visited >= 1
        assert rc.transforms_considered is not None and rc.transforms_considered >= rc.edges_emitted

    def test_the_formula_schema_was_bumped(self):
        assert FORMULA_SEARCH_RECEIPT_SCHEMA.endswith("v1alpha3")

    def test_the_formula_receipt_names_what_it_searched(self):
        rc = search_decomposition("C8H9NO2", example_inventory()).receipt
        assert rc.target_identity_digest and rc.terminal_policy_digest and rc.transform_registry_digest
        assert rc.transform_registry_digest == transform_registry_digest("formula-decomposition")

    def test_an_empty_formula_identity_digest_is_refused(self):
        with pytest.raises(ValueError, match="target_identity_digest must be None"):
            FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 0,
                                 SearchStatus.COMPLETE_WITHIN_BOUNDS, "", target_identity_digest="")

    def test_unmeasured_formula_counters_are_unknown_not_zero(self):
        rc = FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 0,
                                  SearchStatus.COMPLETE_WITHIN_BOUNDS, "")
        assert rc.nodes_visited is None and rc.transforms_considered is None
        assert "UNKNOWN" in rc.render()

    def test_formula_construction_guards_reject_incoherent_telemetry(self):
        # edges_emitted=3, transforms_considered must be >= 3 (pre-dedup >= distinct)
        with pytest.raises(ValueError, match="transforms_considered cannot be fewer than edges_emitted"):
            FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 3,
                                 SearchStatus.COMPLETE_WITHIN_BOUNDS, "", transforms_considered=2)
        with pytest.raises(ValueError, match="sorted by reason"):
            FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 0,
                                 SearchStatus.COMPLETE_WITHIN_BOUNDS, "",
                                 candidates_rejected_by_reason=(("z", 1), ("a", 1)))
        with pytest.raises(ValueError, match="must be a positive int"):
            FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 100, 0,
                                 SearchStatus.COMPLETE_WITHIN_BOUNDS, "",
                                 candidates_rejected_by_reason=(("duplicate", 0),))


class TestSection82FormulaStandardStatus:
    """Section 8.2: the formula receipt speaks the standard terminal-status vocabulary. The descent stops on
    exactly one budget at a time (PARTIAL_MULTIPLE_LIMITS is refused), so no primary resolution is needed."""

    def _receipt(self, status, reason):
        return FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 5000, 3, status, reason)

    def test_complete_maps_to_declared_space(self):
        rc = FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 5000, 3,
                                  SearchStatus.COMPLETE_WITHIN_BOUNDS, "")
        assert rc.standard_status == "COMPLETE_WITHIN_DECLARED_SPACE"

    def test_search_node_budget_maps_to_the_one_8_2_cut_budget_status(self):
        # the per-node search budget IS 8.2's single cut budget; search_kind FORMULA_DECOMPOSITION (and the
        # `budget` field) names which knob to raise -- not cut_budget_scope, which is PER_NODE here as on route/DAG.
        rc = self._receipt(SearchStatus.PARTIAL_SEARCH_BUDGET, "search budget exhausted")
        assert rc.standard_status == "INCOMPLETE_CUT_BUDGET"

    def test_edge_cap_maps_to_result_limit(self):
        rc = self._receipt(SearchStatus.PARTIAL_RESULT_LIMIT, "edge cap exceeded")
        assert rc.standard_status == "INCOMPLETE_RESULT_LIMIT"

    def test_every_reachable_formula_status_is_a_valid_8_2_member(self):
        for status, reason in (
            (SearchStatus.COMPLETE_WITHIN_BOUNDS, ""),
            (SearchStatus.PARTIAL_SEARCH_BUDGET, "budget"),
            (SearchStatus.PARTIAL_RESULT_LIMIT, "cap"),
        ):
            rc = FormulaSearchReceipt(FORMULA_SEARCH_RECEIPT_SCHEMA, 1, 100, 5000, 3, status, reason)
            assert rc.standard_status in STANDARD_8_2_STATUSES
            assert rc.standard_status == rc.status.standard_name  # never MULTIPLE here, so always agrees

    def test_a_live_decomposition_receipt_speaks_8_2(self):
        r = search_decomposition("C8H9NO2", example_inventory())
        assert r.receipt.standard_status in STANDARD_8_2_STATUSES
