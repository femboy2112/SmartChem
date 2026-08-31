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
