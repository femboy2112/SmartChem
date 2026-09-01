"""Smoke tests for the unified ``python -m smartchem`` front door (:mod:`smartchem.cli`).

Fast cases only -- each subcommand is exercised for exit code + a load-bearing line of output; the heavy
retrosynthesis path is covered by the experiment tests, not re-run here.
"""
from __future__ import annotations

from smartchem.cli import main


class TestUsage:
    def test_no_args_prints_usage(self, capsys):
        assert main([]) == 0
        out = capsys.readouterr().out
        for cmd in ("decompile", "compile", "synthesize", "audit"):
            assert cmd in out

    def test_help_flag(self, capsys):
        assert main(["--help"]) == 0
        assert "commands:" in capsys.readouterr().out

    def test_version_flag(self, capsys):
        assert main(["--version"]) == 0
        assert capsys.readouterr().out.strip() == "smartchem 0.5.0a1"

    def test_unknown_command_is_error(self, capsys):
        assert main(["frobnicate"]) == 2
        assert "unknown command" in capsys.readouterr().err


class TestDecompile:
    def test_formula_reaches_buckets(self, capsys):
        assert main(["decompile", "C8H9NO2"]) == 0
        out = capsys.readouterr().out
        assert "COMPLETE" in out
        assert "-> " in out  # at least one decomposition edge rendered

    def test_smiles_target(self, capsys):
        assert main(["decompile", "CC(=O)Nc1ccc(O)cc1", "--smiles"]) == 0
        out = capsys.readouterr().out
        assert "C8H9NO2" in out  # the SMILES was reduced to its formula and decomposed
        assert "IDENTITY LOSS" in out

    def test_pure_elements_inventory(self, capsys):
        assert main(["decompile", "CO2", "--inventory"]) == 0
        assert "pure elements" in capsys.readouterr().out

    def test_declared_target_inventory_is_a_terminal(self, capsys):
        assert main(["decompile", "CO2", "--inventory", "CO2"]) == 0
        out = capsys.readouterr().out
        assert "0 decomposition edge" in out
        assert "target is already a bucket" in out

    def test_invalid_zero_count_formula_is_a_clean_domain_error(self, capsys):
        assert main(["decompile", "H0"]) == 2
        err = capsys.readouterr().err
        assert "positive" in err and "Traceback" not in err


class TestCompile:
    def test_commodity_target_short_circuits(self, capsys):
        # ethanol is a commodity -> the front door says "just obtain it", no synthesis (fast, no route search)
        assert main(["compile", "CCO"]) == 0
        assert "COMMODITY" in capsys.readouterr().out.upper()

    def test_registered_chemical_name_is_accepted(self, capsys):
        assert main(["compile", "acetic acid"]) == 0
        assert "COMMODITY" in capsys.readouterr().out.upper()

    def test_bounded_no_route_is_a_nonzero_domain_outcome(self, capsys):
        assert main(["compile", "acetic anhydride", "--elements", "--max-depth", "1"]) == 3
        out = capsys.readouterr().out
        assert "COMPLETE_WITHIN_BOUNDS" in out and "NO ROUTE FOUND WITHIN" in out

    def test_partial_candidates_use_the_partial_exit_status(self, capsys):
        code = main([
            "compile", "paracetamol", "--have", "4-aminophenol",
            "--reagents", "water", "acetic acid", "acetic anhydride",
            "--max-depth", "1", "--cut-budget", "1000", "--elements",
        ])
        assert code == 4
        assert "PARTIAL_CUT_BUDGET" in capsys.readouterr().out

    def test_charged_structural_request_is_a_clean_unsupported_error(self, capsys):
        assert main(["compile", "[CH2+]CCC", "--elements", "--max-depth", "1"]) == 5
        err = capsys.readouterr().err
        assert "charged chemistry" in err and "Traceback" not in err


class TestDelegation:
    def test_audit_example_delegates_to_evidence(self, capsys):
        assert main(["audit", "--example"]) == 0
        assert "{" in capsys.readouterr().out  # the evidence CLI emitted the JSON template
