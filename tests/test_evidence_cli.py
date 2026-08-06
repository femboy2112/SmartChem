"""B2 acceptance: the verify-probes CLI — exit codes and determinism."""
from __future__ import annotations

import json
from pathlib import Path

from smartchem.evidence.cli import main

_FIXTURES = Path(__file__).parent / "fixtures" / "evidence"


def test_cli_certifies_healthy_fixture(capsys):
    code = main(["verify-probes", str(_FIXTURES / "healthy_probe.json")])
    out = capsys.readouterr().out
    assert code == 0
    assert "CERTIFIED" in out


def test_cli_refuses_section8_fixture(capsys):
    code = main(["verify-probes", str(_FIXTURES / "section8_retraction.json")])
    out = capsys.readouterr().out
    assert code == 1
    assert "REFUSED" in out


def test_cli_reports_load_error_as_exit_2(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    code = main(["verify-probes", str(bad)])
    assert code == 2
    assert "error" in capsys.readouterr().out.lower()


def test_cli_directory_mixed_returns_refuse(capsys):
    # The fixtures dir contains one CERTIFY and one REFUSE → overall exit 1.
    code = main(["verify-probes", str(_FIXTURES)])
    assert code == 1


def test_cli_json_output_is_deterministic(capsys):
    path = str(_FIXTURES / "healthy_probe.json")
    main(["verify-probes", path, "--json"])
    first = capsys.readouterr().out
    main(["verify-probes", path, "--json"])
    second = capsys.readouterr().out
    assert first == second
    payload = json.loads(first)
    assert payload[0]["certificate"]["type"] == "dataclass"
