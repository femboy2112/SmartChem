"""B2 acceptance: the verify-probes CLI — exit codes, determinism, and the authoring aids."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartchem.evidence import audit_manifest, manifest_from_mapping
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


def test_cli_reports_missing_manifest_as_exit_2(tmp_path, capsys):
    # A nonexistent (or unreadable) manifest is a load failure, not an internal crash:
    # the documented contract is exit 2, never a raw FileNotFoundError traceback at exit 1.
    # Regression guard for the OSError wrap in manifest_io.load_manifest.
    missing = tmp_path / "does_not_exist.json"
    code = main(["verify-probes", str(missing)])
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


def test_cli_bare_path_form_certifies_without_the_subcommand_word(capsys):
    # The stutter-free form: a path with no leading `verify-probes` token. The old
    # two-word alias (exercised by every test above) must keep working too.
    code = main([str(_FIXTURES / "healthy_probe.json")])
    assert code == 0
    assert "CERTIFIED" in capsys.readouterr().out


def test_cli_example_emits_a_certifying_template(capsys):
    # `--example` prints a known-good template; a consumer runs `--example > m.json`, and
    # that file audits CLEAN — the emitted starting point is guaranteed sound, not a guess.
    code = main(["--example"])
    assert code == 0
    manifest = manifest_from_mapping(json.loads(capsys.readouterr().out))
    assert audit_manifest(manifest).certified


def test_cli_example_output_is_deterministic(capsys):
    main(["--example"])
    first = capsys.readouterr().out
    main(["--example"])
    second = capsys.readouterr().out
    assert first == second


def test_cli_example_rejects_a_stray_path():
    # `--example` emits a template and takes no path; passing one is a usage error (exit 2).
    with pytest.raises(SystemExit) as exc:
        main(["--example", str(_FIXTURES / "healthy_probe.json")])
    assert exc.value.code == 2
