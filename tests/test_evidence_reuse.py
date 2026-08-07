"""Cross-project reuse hardening: a second, non-fine-man consumer, end to end.

The steering question behind ``smartchem.evidence`` is *can an outside project
depend on it without pain?*  This suite answers it adversarially from the outside,
as a fresh "quadrature-lab" consumer that has never seen the internals:

1. **Installed-package path only.**  Cases are driven through ``cli.main`` — the exact
   entry point both the ``smartchem-verify-probes`` console script and
   ``python -m smartchem.evidence`` resolve to — so what is exercised is the real
   ``argv → exit code`` contract, not an in-process shortcut.  One case additionally
   spawns the literal ``python -m smartchem.evidence --example`` subprocess to prove
   the module entry point itself resolves and emits (the wheel's *contents* — schema,
   README, console script — are verified out of band; here we prove the entry runs).

2. **A first-timer's realistic mistakes yield actionable refusals, not bare stacks.**
   Every malformed manifest a newcomer plausibly emits must exit with the documented
   code (2 = could not load, 1 = refused) and a message that names the field/rule —
   never an uncaught traceback.  ``main`` returning an ``int`` (rather than raising)
   is itself the no-bare-stack guarantee at this layer.

3. **The empty/claim-free manifest never certifies vacuously** (the ``nonvacuous``
   rule, 2026-08-07): a dropped-records emitter bug is the single most likely way a
   consumer ships a green gate over nothing, and it is refused.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from smartchem.evidence import audit_manifest, manifest_from_mapping
from smartchem.evidence.cli import main

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _base() -> dict:
    """A generic, non-fine-man consumer's *certifying* manifest (a quadrature lab).

    Deliberately not derived from any SmartChem fixture: it is what a newcomer would
    author by editing ``--example`` for their own probe suite.
    """
    return {
        "schema": "smartchem.evidence/probe-manifest-v1",
        "program": "quadrature-lab",
        "claimed_tier": "floor",
        "floor_tier": "floor",
        "promoted_tier": "legitimized",
        "records": [
            {
                "probe": "simpson_rule",
                "check": "recovers_known_integral",
                "role": "CALIBRATION",
                "claim_kind": "LITERAL",
                "evidence_status": "CALIBRATED",
                "passed": True,
                "empirical_values": [
                    {"label": "integral_of_x2", "value": 0.3333333, "source": "closed_form"}
                ],
            },
            {
                "probe": "simpson_rule",
                "check": "converges_on_smooth",
                "role": "CLAIM",
                "claim_kind": "ANALOGUE",
                "evidence_status": "STRUCTURAL_TOY",
                "passed": True,
                "agreement": True,
                "inputs": [
                    {"source": "closed_form", "derivation": "exact integral"},
                    {"source": "richardson", "derivation": "independent estimate"},
                ],
                "scope_boundary": "smooth integrands only; singular endpoints excluded",
                "pairs_with": ["step_doubling_must_not_converge"],
            },
            {
                "probe": "simpson_rule",
                "check": "step_doubling_must_not_converge",
                "role": "MUTATION",
                "claim_kind": "ANALOGUE",
                "evidence_status": "STRUCTURAL_TOY",
                "passed": True,
            },
            {
                "probe": "simpson_rule",
                "check": "declared_boundary",
                "role": "SCOPE",
                "claim_kind": "ANALOGUE",
                "evidence_status": "STRUCTURAL_TOY",
                "passed": True,
                "scope_boundary": "floor tier only; no legitimization claimed",
            },
        ],
    }


def _run(tmp_path: Path, obj: dict) -> int:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(obj), encoding="utf-8")
    # main() returns an int for every well-formed argv; if it *raised*, that is the
    # bare-stack failure this suite exists to forbid, and pytest surfaces it as such.
    return main([str(path)])


def test_second_consumer_certifies_end_to_end(tmp_path, capsys):
    code = _run(tmp_path, _base())
    out = capsys.readouterr().out
    assert code == 0
    assert "CERTIFIED" in out


def _without_record(role: str) -> dict:
    obj = _base()
    obj["records"] = [r for r in obj["records"] if r["role"] != role]
    return obj


def _empty() -> dict:
    obj = _base()
    obj["records"] = []
    return obj


def _dropped_program() -> dict:
    obj = _base()
    del obj["program"]
    return obj


def _bad_role_enum() -> dict:
    obj = _base()
    obj["records"][1]["role"] = "claim"  # lowercase; not a Role member
    return obj


def _numeric_result_array() -> dict:
    obj = _base()
    obj["records"][0]["numeric_result"] = [1, 2, 3]
    return obj


def _records_not_a_list() -> dict:
    obj = _base()
    obj["records"] = {"oops": "an object, not a list"}
    return obj


# (name, factory, expected_exit, message_substring the refusal must name)
_MISTAKES = [
    ("empty_records", _empty, 1, "nonvacuous"),
    ("claim_missing_mutation", lambda: _without_record("MUTATION"), 1, "teeth"),
    ("dropped_program", _dropped_program, 2, "program"),
    ("lowercase_role_enum", _bad_role_enum, 2, "role"),
    ("numeric_result_is_array", _numeric_result_array, 2, "numeric_result"),
    ("records_not_a_list", _records_not_a_list, 2, "records"),
]


@pytest.mark.parametrize("name,factory,expected_exit,needle", _MISTAKES)
def test_first_timer_mistake_is_an_actionable_refusal(
    tmp_path, capsys, name, factory, expected_exit, needle
):
    code = _run(tmp_path, factory())
    out = capsys.readouterr().out
    assert code == expected_exit, f"{name}: expected exit {expected_exit}, got {code}"
    assert "Traceback (most recent call last)" not in out, f"{name}: leaked a bare stack"
    assert needle in out, f"{name}: refusal did not name {needle!r} — not actionable"


def test_empty_manifest_names_the_dropped_records_fix(tmp_path, capsys):
    # The refusal must be self-explaining enough that a consumer knows what to add.
    _run(tmp_path, _empty())
    out = capsys.readouterr().out
    assert "nothing to certify" in out
    assert "--example" in out


def _calibration_only() -> dict:
    """One file of a split suite: calibration + scope, its CLAIM in a sibling file."""
    obj = _base()
    obj["records"] = [r for r in obj["records"] if r["role"] in ("CALIBRATION", "SCOPE")]
    return obj


def test_calibration_only_file_certifies(tmp_path, capsys):
    # A claim-free-but-non-empty manifest is a legitimate independent unit; refusing it
    # would be a false positive against directory audit (adversarial probe 2026-08-07).
    code = _run(tmp_path, _calibration_only())
    out = capsys.readouterr().out
    assert code == 0, out
    assert "CERTIFIED" in out


def test_split_suite_directory_audit_certifies_every_file(tmp_path, capsys):
    # The Finding-2 regression: a suite organized one-concern-per-file. The baseline
    # file holds only calibration+scope; the CLAIM lives next door. Every file must
    # certify — the empty-manifest guard must not fire on an honest claim-free file.
    (tmp_path / "00_baseline.json").write_text(
        json.dumps(_calibration_only()), encoding="utf-8"
    )
    (tmp_path / "01_claim.json").write_text(json.dumps(_base()), encoding="utf-8")
    code = main([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "REFUSE" not in out.upper()


def test_module_entry_point_emits_a_certifying_template():
    # The one true installed path: `python -m smartchem.evidence --example`. Prove the
    # entry point resolves and emits, then re-audit its output in process.
    result = subprocess.run(
        [sys.executable, "-m", "smartchem.evidence", "--example"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    manifest = manifest_from_mapping(json.loads(result.stdout))
    assert audit_manifest(manifest).certified
