"""E5 -- route enumeration from the decompiler, and the CLI, proven on the paracetamol loop-closer.

E5 reads the decompiler's conservation-valid cleavages backward into candidate synthesis routes; the tests
pin that it finds the REAL paracetamol syntheses, that every generated step still conserves (E0 would have
raised otherwise), that it is honest when no route exists, and that the CLI runs offline end to end.
"""
import pytest

from smartchem.experiment.dag import SynthesisDAG, verify_dag
from smartchem.experiment.drafter import rank_routes
from smartchem.experiment.routes import (
    DAG_SEARCH_RECEIPT_SCHEMA,
    DAG_SEARCH_RESULT_SCHEMA,
    DAGSearchReceipt,
    DAGSearchResult,
    SearchStatus,
    enumerate_dags,
    enumerate_routes,
    search_dags,
    search_routes,
)
from smartchem.experiment.step import ExperimentRoute
from smartchem.smiles import parse_smiles

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
PARA_O_ESTER = parse_smiles("CC(=O)Oc1ccc(N)cc1")
AMP = parse_smiles("Nc1ccc(O)cc1")
WATER = parse_smiles("O")
ACOH = parse_smiles("CC(=O)O")
ANH = parse_smiles("CC(=O)OC(=O)C")

# A reagent pool over which ethyl acetate has a genuinely CONVERGENT retro-synthesis (two intermediates each
# made from scratch, then joined) -- the case enumerate_routes silently dropped and enumerate_dags now reaches.
ETAC = parse_smiles("CCOC(=O)C")
DAG_REAGENTS = tuple(parse_smiles(s) for s in ("O", "CO", "CC(=O)O", "C=C", "CCO", "C=C=O"))


class TestEnumeration:
    def test_target_in_exact_terminal_stock_stops_before_expansion(self):
        result = search_routes(PARA, reagents=(WATER,), available=(PARA,), max_depth=1)
        assert result.routes == ()
        assert result.target_in_terminal_stock
        assert result.receipt.expansions_attempted == 0
        assert result.receipt.complete_within_bounds

    def test_rich_search_api_preserves_tuple_wrapper_and_reports_completion(self):
        result = search_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        assert result.routes == enumerate_routes(
            PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1
        )
        assert result.receipt.status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert result.receipt.results_returned == len(result.routes)

    def test_cut_budget_exhaustion_is_not_laundered_into_no_route(self):
        result = search_routes(PARA, reagents=(WATER,), available=(), max_depth=1, cut_budget=1)
        assert result.routes == ()
        assert result.receipt.status is SearchStatus.PARTIAL_CUT_BUDGET
        assert result.receipt.cut_budget_exhausted

    def test_unique_result_cap_is_visible(self):
        result = search_routes(
            PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1, max_routes=1
        )
        assert len(result.routes) == 1
        assert result.receipt.status is SearchStatus.PARTIAL_RESULT_LIMIT

    @pytest.mark.parametrize("field", ["max_depth", "max_routes", "cut_budget"])
    def test_search_bounds_must_be_positive(self, field):
        kwargs = dict(reagents=(WATER,), max_depth=1, max_routes=1, cut_budget=1)
        kwargs[field] = 0
        with pytest.raises(ValueError, match="positive integer"):
            search_routes(PARA, **kwargs)

    def test_finds_the_real_paracetamol_syntheses(self):
        routes = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        assert routes
        eqs = {s.equation() for r in routes for s in r.steps}
        # the acetic-acid condensation and the acetic-anhydride acetylation of 4-aminophenol
        assert "C2H4O2 + C6H7NO -> C8H9NO2 + H2O" in eqs
        assert "C4H6O3 + C6H7NO -> C8H9NO2 + C2H4O2" in eqs

    def test_conditions_are_directional_and_structure_keyed(self):
        routes = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        by_lhs = {s.equation().split(" -> ")[0]: s for r in routes for s in r.steps}
        # Acidic aqueous conditions document paracetamol hydrolysis, not the reverse condensation.
        assert not by_lhs["C2H4O2 + C6H7NO"].envelope.is_declared
        assert by_lhs["C4H6O3 + C6H7NO"].envelope.is_declared

        # The O-acetyl constitutional isomer has the same formula and formal route, but cannot borrow
        # paracetamol's assembly conditions without an exact structure match.
        ester_routes = enumerate_routes(
            PARA_O_ESTER, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1
        )
        ester_anhydride = next(
            s for r in ester_routes for s in r.steps if s.equation().startswith("C4H6O3 + C6H7NO")
        )
        assert not ester_anhydride.envelope.is_declared

    def test_every_generated_route_is_a_valid_conserving_route(self):
        routes = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        for r in routes:
            assert isinstance(r, ExperimentRoute)  # construction re-checked conservation + linearity
            assert r.final_target == PARA

    def test_no_route_from_an_empty_inventory_is_a_loud_empty_not_a_fabrication(self):
        # nothing on hand and only water as a reagent: no single-step route to paracetamol
        routes = enumerate_routes(PARA, reagents=(WATER,), available=(), max_depth=1)
        assert routes == ()

    def test_generated_routes_rank(self):
        routes = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        ranked = rank_routes(list(routes))
        assert ranked and ranked[0].composability.verdict in {"COMPOSABLE", "SINGLE_STEP"}


class TestConvergentDAGEnumeration:
    """The mid-term lift: enumerate_dags generalises enumerate_routes to CONVERGENT syntheses -- a step fed by
    two-or-more precursors both made from scratch, which the linear enumerator silently dropped."""

    def test_every_emitted_structure_is_a_valid_dag_to_the_target(self):
        dags = enumerate_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=60)
        assert dags
        for d in dags:
            assert isinstance(d, SynthesisDAG)          # construction re-checked every DAG invariant
            assert d.final_target == ETAC

    def test_reaches_a_genuinely_convergent_synthesis(self):
        # enumerate_routes drops any join needing two from-scratch precursors; enumerate_dags reaches them.
        dags = enumerate_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=60)
        convergent = [d for d in dags if d.is_convergent]
        assert convergent, "expected at least one convergent DAG for ethyl acetate over this pool"
        d = convergent[0]
        # a convergence point is a step fed by >=2 produced intermediates
        assert d.convergence_points
        join = d.convergence_points[0]
        produced_into_join = [(i, j) for (i, j, _m) in d.edges if j == join]
        assert len(produced_into_join) >= 2  # two branches feed the join

    def test_the_convergent_dag_verifies_on_every_rung(self):
        dags = enumerate_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=60)
        d = next(x for x in dags if x.is_convergent)
        v = verify_dag(d)                                # E1 composability + M1 feasibility + M2 equilibrium
        assert v.feasibility_verdict in {"FAVORABLE", "BORDERLINE", "UNFAVORABLE", "UNKNOWN"}
        assert v.composability.verdict in {"COMPOSABLE", "DEGENERATE", "UNKNOWN", "NO_TRANSITIONS"}

    def test_is_a_superset_of_the_linear_enumerator(self):
        # every linear route enumerate_routes finds appears among enumerate_dags' NON-convergent (path) DAGs.
        routes = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        dags = enumerate_dags(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        assert dags and all(not d.is_convergent for d in dags)  # depth-1 single-precursor steps are all linear
        route_step_sets = {frozenset(s.equation() for s in r.steps) for r in routes}
        dag_step_sets = {frozenset(s.equation() for s in d.steps) for d in dags}
        assert route_step_sets <= dag_step_sets

    def test_no_dag_from_an_empty_pool_is_a_loud_empty(self):
        assert enumerate_dags(PARA, reagents=(WATER,), available=(), max_depth=1) == ()

    def test_max_dags_caps_distinct_results_not_raw_candidates(self):
        # RED-TEAM (HIGH): the cap must bound DISTINCT DAGs, not the duplicate-heavy raw itertools.product
        # candidates.  If it capped raw candidates, a small cap would truncate before the dedup and silently
        # return a fraction of the answer (and drop linear routes -> the superset claim would be false).
        # The full distinct set is stable once the cap exceeds it; a smaller-but-sufficient cap returns it too.
        full = enumerate_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=5000)
        n = len(full)
        assert n > 20  # ethyl acetate has many distinct DAGs over this pool
        # a cap at exactly the distinct count returns the whole set (not a duplicate-throttled fraction)
        at_n = enumerate_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=n)
        assert len(at_n) == n
        # and a cap below it returns AT MOST that many distinct DAGs (a real bound on the result)
        assert len(enumerate_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=5)) <= 5

    def test_depth_three_terminates_and_stays_valid(self):
        # RED-TEAM residual: the dedup + distinct-cap must keep deeper enumeration bounded (it did not terminate
        # before), and the orphan-prune must keep every emitted DAG a valid connected synthesis.
        dags = enumerate_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=3, max_dags=40)
        assert dags and len(dags) <= 40
        assert all(isinstance(d, SynthesisDAG) and d.final_target == ETAC for d in dags)


class TestConvergentDAGReceipt:
    """The DAG path now carries the same completeness receipt the linear search does (P0-1 / SRCH-RCT-02 /
    SRCH-CAP-01).  Before this, ``enumerate_dags`` dropped ``capped_scissions.complete`` on the floor at every
    level and the ``max_dags`` cap truncated silently -- so a DAG "no route" was indistinguishable from "the cut
    budget was too small" or "``max_dags`` was too small".  ``search_dags`` makes that distinction auditable
    while ``enumerate_dags`` stays a tuple-returning compatibility wrapper."""

    def test_target_in_exact_terminal_stock_stops_before_expansion(self):
        # §7 terminal policy, now shared with search_routes: a target already on hand is not synthesised.
        result = search_dags(PARA, reagents=(WATER,), available=(PARA,), max_depth=1)
        assert result.dags == ()
        assert result.target_in_terminal_stock
        assert result.receipt.expansions_attempted == 0
        assert result.receipt.complete_within_bounds

    def test_rich_dag_api_matches_tuple_wrapper_and_reports_completion(self):
        result = search_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=5000)
        assert result.dags == enumerate_dags(
            ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=5000
        )
        assert result.receipt.status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert result.receipt.results_returned == len(result.dags)
        assert result.receipt.incomplete_expansions == 0
        assert not result.target_in_terminal_stock

    def test_cut_budget_exhaustion_is_not_laundered_into_no_route(self):
        # THE headline falsifier (P0-1) for the DAG path: an empty result under an exhausted cut budget is a
        # PARTIAL search, never a certified "no route in the declared space".
        starved = search_dags(PARA, reagents=(WATER,), available=(), max_depth=1, cut_budget=1)
        assert starved.dags == ()
        assert starved.receipt.status is SearchStatus.PARTIAL_CUT_BUDGET
        assert starved.receipt.cut_budget_exhausted
        assert starved.receipt.incomplete_expansions > 0
        # ...whereas the SAME query at full budget is a genuine complete-empty (NO_ROUTE_IN_DECLARED_SPACE),
        # and only the receipt tells the two empties apart.
        complete = search_dags(PARA, reagents=(WATER,), available=(), max_depth=1)
        assert complete.dags == ()
        assert complete.receipt.status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert complete.receipt.complete_within_bounds

    def test_distinct_result_cap_saturation_is_visible(self):
        # A cap below the true distinct count must be reported partial (SRCH-CAP-01), not passed off as complete.
        result = search_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=5)
        assert len(result.dags) <= 5
        assert result.receipt.status is SearchStatus.PARTIAL_RESULT_LIMIT
        assert result.receipt.result_limit_saturated

    def test_result_cap_saturation_is_conservative_at_the_exact_count(self):
        # DOCUMENTED BOUNDARY: max_dags caps DISTINCT syntheses at every recursion level, so proving "there was
        # nothing more" would defeat the cap.  A cap equal to the true count therefore still flags PARTIAL while
        # returning the whole set -- an over-report that always points toward "there may be more", never toward a
        # false COMPLETE (contrast the linear search, which is precise here).  Pinned so a "fix" can't silently
        # flip it to the dangerous direction.
        full = search_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=5000)
        n = len(full.dags)
        assert full.receipt.status is SearchStatus.COMPLETE_WITHIN_BOUNDS  # a cap well above the count is complete
        at_n = search_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=n)
        assert len(at_n.dags) == n  # the whole set is still returned
        assert at_n.receipt.status is SearchStatus.PARTIAL_RESULT_LIMIT  # conservatively flagged partial

    @pytest.mark.parametrize("field", ["max_depth", "max_dags", "cut_budget"])
    def test_search_bounds_must_be_positive(self, field):
        kwargs = dict(reagents=DAG_REAGENTS, max_depth=2, max_dags=5, cut_budget=1)
        kwargs[field] = 0
        with pytest.raises(ValueError, match="positive integer"):
            search_dags(ETAC, **kwargs)

    def test_receipt_render_states_status_and_bounded_scope(self):
        receipt = search_dags(ETAC, reagents=DAG_REAGENTS, available=(), max_depth=2, max_dags=5).receipt
        text = receipt.render()
        assert receipt.status.value in text
        assert "not all chemistry" in text  # the scope is bounded to the capped-scission grammar, said out loud

    def test_result_rejects_a_receipt_count_that_disagrees_with_the_dags(self):
        # Value-construction layer: the result cannot claim a different number of syntheses than it carries.
        liar = DAGSearchReceipt(DAG_SEARCH_RECEIPT_SCHEMA, 2, 100, 20_000, 0, 0, False, 1)
        with pytest.raises(ValueError, match="results_returned must equal len"):
            DAGSearchResult(DAG_SEARCH_RESULT_SCHEMA, (), liar)

    def test_result_rejects_a_stocked_target_that_also_expanded(self):
        expanded = DAGSearchReceipt(DAG_SEARCH_RECEIPT_SCHEMA, 2, 100, 20_000, 3, 0, False, 0)
        with pytest.raises(ValueError, match="terminate before expansion"):
            DAGSearchResult(DAG_SEARCH_RESULT_SCHEMA, (), expanded, True)


class TestOrphanPrune:
    """The reachability prune that keeps a shared-intermediate dedup from orphaning a branch (red-team residual)."""

    def test_prune_drops_a_branch_that_feeds_nothing_downstream(self):
        from smartchem.experiment.routes import _prune_to_sink
        from smartchem.experiment.step import ExperimentStep
        ethene, water = parse_smiles("C=C"), parse_smiles("O")
        ethanol, acid = parse_smiles("CCO"), parse_smiles("CC(=O)O")
        etac, butene = parse_smiles("CCOC(=O)C"), parse_smiles("CC=CC")
        feeder = ExperimentStep.assembling(ethanol, (ethene, water), (ethanol,))          # ethene + H2O -> EtOH
        orphan = ExperimentStep.assembling(butene, (ethene, ethene), (butene,))           # 2 ethene -> butene (unused)
        sink = ExperimentStep.assembling(etac, (ethanol, acid), (etac, water))            # EtOH + AcOH -> EtOAc + H2O
        pruned = _prune_to_sink((orphan, feeder, sink))
        targets = {p.target for p in pruned}
        assert sink.target in targets and ethanol in targets      # sink + its feeder kept
        assert butene not in targets                              # the orphan branch pruned away

    def test_prune_is_a_noop_when_everything_feeds_the_sink(self):
        from smartchem.experiment.routes import _prune_to_sink
        from smartchem.experiment.step import ExperimentStep
        ethene, water, ethanol, acid = (parse_smiles(s) for s in ("C=C", "O", "CCO", "CC(=O)O"))
        etac = parse_smiles("CCOC(=O)C")
        feeder = ExperimentStep.assembling(ethanol, (ethene, water), (ethanol,))
        sink = ExperimentStep.assembling(etac, (ethanol, acid), (etac, water))
        assert _prune_to_sink((feeder, sink)) == (feeder, sink)  # both feed the sink -> unchanged


class TestCLI:
    def test_cli_runs_offline_end_to_end(self, capsys):
        from smartchem.experiment.cli import main
        code = main([
            "CC(=O)Nc1ccc(O)cc1", "--have", "Nc1ccc(O)cc1",
            "--reagents", "O", "CC(=O)O", "CC(=O)OC(=O)C",
            "--max-depth", "1", "--offline",
        ])
        out = capsys.readouterr().out
        assert code == 0
        assert "candidate route(s)" in out
        assert "NOT a predicted successful synthesis" in out  # the draft banner
        assert "route ceiling" not in out  # no quantities were supplied; the CLI must not invent one mole

    def test_cli_reports_no_route_loudly(self, capsys):
        from smartchem.experiment.cli import main
        code = main(["CC(=O)Nc1ccc(O)cc1", "--reagents", "O", "--max-depth", "1", "--offline"])
        out = capsys.readouterr().out
        assert code == 3
        assert "no synthesis route" in out

    def test_cli_returns_partial_status_even_when_candidates_exist(self, capsys):
        from smartchem.experiment.cli import main
        code = main([
            "paracetamol", "--have", "4-aminophenol",
            "--reagents", "water", "acetic acid", "acetic anhydride",
            "--max-depth", "1", "--cut-budget", "1000", "--offline",
        ])
        out = capsys.readouterr().out
        assert code == 4
        assert "PARTIAL_CUT_BUDGET" in out

    def test_cli_rejects_bad_smiles(self, capsys):
        from smartchem.experiment.cli import main
        assert main(["not-a-smiles-@@@", "--offline"]) == 2
        assert "could not parse" in capsys.readouterr().err
