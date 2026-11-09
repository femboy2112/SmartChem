"""Tests for the ``python -m smartchem doctor`` environment diagnostic (additive subcommand)."""
from __future__ import annotations

import json

import smartchem
from smartchem import cli
from smartchem.cli import main


class TestDoctor:
    def test_exits_zero_and_reports_core_lines(self, capsys):
        assert main(["doctor"]) == 0
        out = capsys.readouterr().out
        assert "Python:" in out
        assert f"SmartChem:  {smartchem.__version__}" in out
        assert "numpy" in out and "scipy" in out
        assert "pyscf" in out and "phreeqpython" in out
        assert "science lane (PHREEQC)" in out

    def test_json_is_valid_with_expected_keys(self, capsys):
        assert main(["doctor", "--json"]) == 0
        rep = json.loads(capsys.readouterr().out)
        assert {"python", "smartchem", "required", "optional", "test_lanes", "git", "missing_required"} <= set(rep)
        assert rep["smartchem"]["version"] == smartchem.__version__
        assert set(rep["required"]) == {"numpy", "scipy"}

    def test_strict_exits_zero_when_required_present(self, capsys):
        assert main(["doctor", "--strict"]) == 0
        capsys.readouterr()

    def test_strict_exits_one_when_required_missing(self, capsys, monkeypatch):
        real = cli._doctor_probe
        monkeypatch.setattr(cli, "_doctor_probe",
                            lambda m, d: {"present": False, "version": None} if m == "numpy" else real(m, d))
        assert main(["doctor", "--strict"]) == 1
        assert main(["doctor"]) == 0  # default stays fail-soft
        capsys.readouterr()

    def test_listed_in_usage(self, capsys):
        assert main([]) == 0
        assert "doctor" in capsys.readouterr().out
