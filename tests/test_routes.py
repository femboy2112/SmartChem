"""E5 -- route enumeration from the decompiler, and the CLI, proven on the paracetamol loop-closer.

E5 reads the decompiler's conservation-valid cleavages backward into candidate synthesis routes; the tests
pin that it finds the REAL paracetamol syntheses, that every generated step still conserves (E0 would have
raised otherwise), that it is honest when no route exists, and that the CLI runs offline end to end.
"""
import pytest

from smartchem.experiment.dag import SynthesisDAG, verify_dag
from smartchem.experiment.drafter import rank_routes
from smartchem.experiment.routes import enumerate_dags, enumerate_routes
from smartchem.experiment.step import ExperimentRoute
from smartchem.smiles import parse_smiles

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
AMP = parse_smiles("Nc1ccc(O)cc1")
WATER = parse_smiles("O")
ACOH = parse_smiles("CC(=O)O")
ANH = parse_smiles("CC(=O)OC(=O)C")

# A reagent pool over which ethyl acetate has a genuinely CONVERGENT retro-synthesis (two intermediates each
# made from scratch, then joined) -- the case enumerate_routes silently dropped and enumerate_dags now reaches.
ETAC = parse_smiles("CCOC(=O)C")
DAG_REAGENTS = tuple(parse_smiles(s) for s in ("O", "CO", "CC(=O)O", "C=C", "CCO", "C=C=O"))


class TestEnumeration:
    def test_finds_the_real_paracetamol_syntheses(self):
        routes = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        assert routes
        eqs = {s.equation() for r in routes for s in r.steps}
        # the acetic-acid condensation and the acetic-anhydride acetylation of 4-aminophenol
        assert "C2H4O2 + C6H7NO -> C8H9NO2 + H2O" in eqs
        assert "C4H6O3 + C6H7NO -> C8H9NO2 + C2H4O2" in eqs

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
        assert "route ceiling" in out

    def test_cli_reports_no_route_loudly(self, capsys):
        from smartchem.experiment.cli import main
        code = main(["CC(=O)Nc1ccc(O)cc1", "--reagents", "O", "--max-depth", "1", "--offline"])
        out = capsys.readouterr().out
        assert code == 1
        assert "no synthesis route" in out

    def test_cli_rejects_bad_smiles(self):
        from smartchem.experiment.cli import main
        with pytest.raises(SystemExit, match="could not parse"):
            main(["not-a-smiles-@@@", "--offline"])
