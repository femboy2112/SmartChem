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
        assert capsys.readouterr().out.strip() == "smartchem 0.9.5a1"

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
    # F52 (RC Round IV): `compile`'s human path now runs the SAME canonical service/render seam `recompile` does
    # (no more bespoke compile_synthesis dossier), so its wording matches recompile's typed-response render --
    # "COMMODITY" was the old dossier's phrasing; the canonical outcome banner is TARGET_ALREADY_AVAILABLE.
    def test_commodity_target_short_circuits(self, capsys):
        # ethanol is a commodity -> the front door says "just obtain it", no synthesis (fast, no route search)
        assert main(["compile", "CCO"]) == 0
        assert "TARGET_ALREADY_AVAILABLE" in capsys.readouterr().out

    def test_registered_chemical_name_is_accepted(self, capsys):
        assert main(["compile", "acetic acid"]) == 0
        assert "TARGET_ALREADY_AVAILABLE" in capsys.readouterr().out

    def test_bounded_no_route_is_a_nonzero_domain_outcome(self, capsys):
        # depth 2 genuinely exhausts the elemental search for acetic anhydride (no branch cut by the bound), so
        # this is a real COMPLETE no-route (exit 3). At depth 1 it is honestly PARTIAL_DEPTH_LIMIT (routes may
        # exist deeper), which is exit 4 -- so a bumped bound is required to reach the genuine complete-empty.
        assert main(["compile", "acetic anhydride", "--elements", "--max-depth", "2"]) == 3
        out = capsys.readouterr().out
        # SRCH-NO-01: the receipt still reports the engine's COMPLETE_WITHIN_BOUNDS, and the no-route wording now
        # rides the uniform section-8.3 label -- a complete, empty declared space is NO_ROUTE_IN_DECLARED_SPACE.
        assert "COMPLETE_WITHIN_BOUNDS" in out and "NO_ROUTE_IN_DECLARED_SPACE" in out

    def test_partial_candidates_use_the_partial_exit_status(self, capsys):
        code = main([
            "compile", "paracetamol", "--have", "4-aminophenol",
            "--reagents", "water", "acetic acid", "acetic anhydride",
            "--max-depth", "1", "--cut-budget", "1000", "--elements",
        ])
        assert code == 4
        # partial exit even with candidates present; here the cut budget and the depth bound both bit, so the
        # receipt reads PARTIAL_MULTIPLE_LIMITS -- the exit status must be the partial 4, never a false 0.
        out = capsys.readouterr().out
        assert "PARTIAL" in out and "COMPLETE_WITHIN_BOUNDS" not in out

    def test_charged_structural_request_is_a_clean_unsupported_error(self, capsys):
        # F52: the charged-species model-boundary refusal is now a typed REFUSED response rendered on stdout (the
        # SAME path recompile takes), not a raised exception caught on stderr by the old compile_synthesis path.
        assert main(["compile", "[CH2+]CCC", "--elements", "--max-depth", "1"]) == 5
        out, err = capsys.readouterr()
        assert "charged chemistry" in out and "Traceback" not in out and "Traceback" not in err


class TestDelegation:
    def test_audit_example_delegates_to_evidence(self, capsys):
        assert main(["audit", "--example"]) == 0
        assert "{" in capsys.readouterr().out  # the evidence CLI emitted the JSON template
