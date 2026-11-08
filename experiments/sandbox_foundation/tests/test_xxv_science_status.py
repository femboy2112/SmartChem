"""OPERATION XXV-2 (#166) -- the science workflow's stdlib helpers, on synthetic inputs (no phreeqpython needed).

check_junit must go red on a skip / short count; verify_hashes must go red on a flipped byte; status_record must keep
its four lanes separate and must never produce PASS from a skip, an empty registry, or a non-ancestor preregistration.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import run_solid_equilibrium_xxiii as h
from experiments.sandbox_foundation.science import check_junit as cj
from experiments.sandbox_foundation.science import status_record as sr
from experiments.sandbox_foundation.science import verify_hashes as vh

SCIENCE = Path(sr.__file__).resolve().parent
REPO = SCIENCE.parents[2]


def _junit(tmp_path, *, passed=3, skipped=0, failed=0, name="j.xml"):
    cases = [f'<testcase classname="t" name="p{i}"/>' for i in range(passed)]
    cases += [f'<testcase classname="t" name="s{i}"><skipped type="pytest.skip" message="could not import '
              f'&apos;phreeqpython&apos;"/></testcase>' for i in range(skipped)]
    cases += [f'<testcase classname="t" name="f{i}"><failure message="boom"/></testcase>' for i in range(failed)]
    p = tmp_path / name
    p.write_text('<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" '
                 f'tests="{len(cases)}">{"".join(cases)}</testsuite></testsuites>')
    return p


def _registry(tmp_path, entries):
    p = tmp_path / "REGISTRY.json"
    p.write_text(json.dumps({"schema": "smartchem-holdout-registry/1", "entries": entries}))
    return p


# ------------------------------------------------------------------------------------------------ check_junit
def test_check_junit_passes_a_clean_run_and_fails_a_skip_of_the_same_size(tmp_path):
    clean = _junit(tmp_path, passed=4, name="clean.xml")
    skip = _junit(tmp_path, passed=3, skipped=1, name="skip.xml")     # same 4 cases, one skipped: the control
    assert cj.main([str(clean), "--expected-executed", "4"]) == 0
    assert cj.main([str(skip), "--expected-executed", "3"]) == 1      # executed count is met; the SKIP alone fails it


def test_check_junit_fails_a_short_count_a_failure_and_a_missing_file(tmp_path):
    assert cj.main([str(_junit(tmp_path, passed=2)), "--expected-executed", "3"]) == 1
    assert cj.main([str(_junit(tmp_path, passed=3, failed=1, name="f.xml")), "--expected-executed", "3"]) == 1
    assert cj.main([str(tmp_path / "absent.xml"), "--expected-executed", "1"]) == 2


def test_manifest_is_well_formed_and_lists_existing_files():
    man = json.loads((SCIENCE / "manifest.json").read_text())
    assert cj.expected_from_manifest(SCIENCE / "manifest.json") == man["expected_executed"]
    assert len(man["tests"]) == len(set(man["tests"]))
    for t in man["tests"]:
        assert (REPO / t).is_file(), t
    assert "experiments/sandbox_foundation/tests/test_xxv_calcite_live_phreeqc.py" in man["tests"]


# ------------------------------------------------------------------------------------------------ verify_hashes
def test_vendored_pins_agree_with_the_harness_pins_in_code():
    exp = json.loads((SCIENCE / "expected_hashes.json").read_text())
    for path, sha in h.DB_SHA256.items():
        assert exp["vendored"][str(path.relative_to(REPO))] == sha
    res = vh.verify(exp, REPO, installed=False)
    assert res["ok"] is True and len(res["files"]) == len(exp["vendored"])


def test_a_flipped_byte_in_a_copy_turns_the_pin_check_red(tmp_path):
    exp = json.loads((SCIENCE / "expected_hashes.json").read_text())
    rel = "experiments/sandbox_foundation/benchmarks/solid_equilibrium_xxiii/db/phreeqc.dat"
    only = {"vendored": {rel: exp["vendored"][rel]}}
    dst = tmp_path / rel
    dst.parent.mkdir(parents=True)
    shutil.copyfile(REPO / rel, dst)
    assert vh.verify(only, tmp_path, installed=False)["ok"] is True      # the unmutated copy passes: discriminating
    data = bytearray(dst.read_bytes())
    data[0] ^= 0x01
    dst.write_bytes(bytes(data))
    res = vh.verify(only, tmp_path, installed=False)
    assert res["ok"] is False and res["files"][0]["problem"] == "SHA256_MISMATCH"
    (tmp_path / "e.json").write_text(json.dumps(only))
    assert vh.main(["--expected", str(tmp_path / "e.json"), "--root", str(tmp_path), "--vendored-only"]) == 1


def test_installed_check_fails_closed_when_the_distribution_is_absent(tmp_path):
    exp = {"vendored": {}, "installed_phreeqpython": {"distribution": "no_such_dist_xxv", "version": "1.0",
                                                        "files": {"database/x.dat": "0" * 64}}}
    res = vh.verify(exp, tmp_path, installed=True)
    assert res["ok"] is False and res["files"][-1]["problem"] == "NOT_INSTALLED"


# ------------------------------------------------------------------------------------------------ status_record
def test_a_skip_is_unverified_never_pass(tmp_path):
    lane = sr.junit_lane(_junit(tmp_path, passed=59, skipped=1), expected_executed=59)
    assert lane["status"] == sr.UNVERIFIED and "skipped" in lane["reason"]
    assert lane["skipped_cases"][0]["reason"] == "could not import 'phreeqpython'"
    assert sr.junit_lane(_junit(tmp_path, passed=60, name="ok.xml"), expected_executed=60)["status"] == sr.PASS


def test_no_skip_combination_ever_yields_pass(tmp_path):
    for passed in (0, 1, 60, 61):
        for skipped in (1, 4):
            for exp in (1, 60):
                lane = sr.junit_lane(_junit(tmp_path, passed=passed, skipped=skipped, name=f"{passed}{skipped}.xml"),
                                     expected_executed=exp)
                assert lane["status"] != sr.PASS


def test_failures_fail_and_missing_junit_is_not_evaluated(tmp_path):
    assert sr.junit_lane(_junit(tmp_path, passed=60, failed=1), 60)["status"] == sr.FAIL
    assert sr.junit_lane(None)["status"] == sr.NOT_EVALUATED
    assert sr.junit_lane(tmp_path / "absent.xml")["status"] == sr.NOT_EVALUATED


def test_empty_registry_is_unverified_and_the_committed_registry_is_empty():
    committed = json.loads((REPO / "experiments/sandbox_foundation/holdouts/REGISTRY.json").read_text())
    assert committed["entries"] == [] and "schema_note" in committed
    lane = sr.measured_lane(REPO / "experiments/sandbox_foundation/holdouts/REGISTRY.json", "HEAD",
                            is_ancestor=lambda a, b: True)
    assert lane["status"] == sr.UNVERIFIED and lane["reason"] == "REGISTRY_EMPTY"


def test_registry_pass_requires_qualified_true_and_an_ancestor_preregistration(tmp_path):
    entry = {"id": "h1", "prereg_commit": "abc1234", "qualified": True, "outcome": "PASS"}
    yes, no = (lambda a, b: True), (lambda a, b: False)
    assert sr.measured_lane(_registry(tmp_path, [entry]), "run", yes)["status"] == sr.PASS
    assert sr.measured_lane(_registry(tmp_path, [entry]), "run", no)["status"] == sr.UNVERIFIED
    for bad in ({"qualified": "true"}, {"qualified": 1}, {"qualified": False}, {"outcome": "PENDING"},
                {"prereg_commit": ""}, {"prereg_commit": None}):
        assert sr.measured_lane(_registry(tmp_path, [dict(entry, **bad)]), "run", yes)["status"] == sr.UNVERIFIED, bad
    fail = dict(entry, id="h2", outcome="FAIL")
    assert sr.measured_lane(_registry(tmp_path, [entry, fail]), "run", yes)["status"] == sr.FAIL
    assert sr.measured_lane(tmp_path / "absent.json", "run", yes)["status"] == sr.UNVERIFIED


def test_production_lane_is_never_inferred(tmp_path):
    assert sr.production_lane(None, "abc")["status"] == sr.NOT_EVALUATED
    runs = tmp_path / "runs.json"
    runs.write_text(json.dumps([{"databaseId": 1, "headSha": "abc", "status": "in_progress", "conclusion": ""}]))
    assert sr.production_lane(runs, "abc")["status"] == sr.PENDING
    assert sr.production_lane(runs, "other")["status"] == sr.NOT_EVALUATED
    runs.write_text(json.dumps([{"databaseId": 1, "headSha": "abc", "status": "completed", "conclusion": "failure"},
                                {"databaseId": 2, "headSha": "abc", "status": "completed", "conclusion": "success"}]))
    assert sr.production_lane(runs, "abc")["status"] == sr.PASS                  # the latest attempt decides
    runs.write_text("not json")
    assert sr.production_lane(runs, "abc")["status"] == sr.NOT_EVALUATED


def test_receipt_keeps_four_separate_lanes_and_no_overall_verdict(tmp_path):
    rec = sr.build_receipt(run_commit="r", science_junit=_junit(tmp_path, passed=60), manifest=SCIENCE / "manifest.json",
                           registry=_registry(tmp_path, []), is_ancestor=lambda a, b: True)
    assert tuple(rec["lanes"]) == sr.LANES
    assert rec["lanes"]["live_reference_solver"]["status"] == sr.PASS
    assert rec["lanes"]["measured_validation"]["status"] == sr.UNVERIFIED       # a live PASS implies nothing here
    assert rec["lanes"]["production_compat"]["status"] == sr.NOT_EVALUATED
    assert rec["lanes"]["sandbox_numerical"]["status"] == sr.NOT_EVALUATED
    assert not ({"status", "overall", "verdict"} & set(rec))
    json.dumps(rec, allow_nan=False)


def test_unverified_pins_demote_a_live_pass(tmp_path):
    bad = tmp_path / "hashes.json"
    bad.write_text(json.dumps({"ok": False}))
    rec = sr.build_receipt(run_commit="r", science_junit=_junit(tmp_path, passed=60), hashes_report=bad,
                           manifest=SCIENCE / "manifest.json", registry=_registry(tmp_path, []),
                           is_ancestor=lambda a, b: True)
    assert rec["lanes"]["live_reference_solver"]["status"] == sr.UNVERIFIED


def test_requirements_are_hash_locked():
    lines = [ln.strip() for ln in (SCIENCE / "requirements-science.txt").read_text().splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    reqs = [ln.rstrip(" \\") for ln in lines if not ln.startswith("--hash")]
    hashes = [ln for ln in lines if ln.startswith("--hash=sha256:")]
    assert reqs == ["phreeqpython==1.6.2", "periodictable==2.1.0", "pyparsing==3.3.3"]
    assert len(hashes) == 3 and all(len(x.split(":", 1)[1]) == 64 for x in hashes)
    exp = json.loads((SCIENCE / "expected_hashes.json").read_text())
    assert f"--hash=sha256:{exp['installed_phreeqpython']['wheel']['sha256']}" in hashes


@pytest.mark.parametrize("mod", [cj, sr, vh])
def test_helpers_are_stdlib_only(mod):
    import ast
    import sys as _sys
    tree = ast.parse(Path(mod.__file__).read_text())
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    assert roots - {"__future__", "experiments"} <= set(_sys.stdlib_module_names)
