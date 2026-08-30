"""E5 -- route enumeration from the decompiler, and the CLI, proven on the paracetamol loop-closer.

E5 reads the decompiler's conservation-valid cleavages backward into candidate synthesis routes; the tests
pin that it finds the REAL paracetamol syntheses, that every generated step still conserves (E0 would have
raised otherwise), that it is honest when no route exists, and that the CLI runs offline end to end.
"""
import pytest

from smartchem.experiment.drafter import rank_routes
from smartchem.experiment.routes import enumerate_routes
from smartchem.experiment.step import ExperimentRoute
from smartchem.smiles import parse_smiles

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
AMP = parse_smiles("Nc1ccc(O)cc1")
WATER = parse_smiles("O")
ACOH = parse_smiles("CC(=O)O")
ANH = parse_smiles("CC(=O)OC(=O)C")


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
