"""OPERATION XXV-2 (#166) -- the science workflow's stdlib helpers, on synthetic inputs (no phreeqpython needed).

check_junit must go red on a skip / short count; verify_hashes must go red on a flipped byte; status_record must keep
its four lanes separate and must never produce PASS from a skip, an empty registry, or a non-ancestor preregistration.

XXV red-team regressions (findings 3, 4, 12 + check_junit shapes + residuals a/b/c) are pinned below, each against a
discriminating control that the hardened code still passes.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import run_solid_equilibrium_xxiii as h
from experiments.sandbox_foundation.science import check_junit as cj
from experiments.sandbox_foundation.science import manifest_guard as mg
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


def _hashes_ok(tmp_path):
    p = tmp_path / "hashes-ok.json"
    p.write_text(json.dumps({"ok": True, "installed": {"checked": True}, "files": [{"ok": True}]}))
    return p


def _xml(tmp_path, name, body):
    p = tmp_path / name
    p.write_text('<?xml version="1.0" encoding="utf-8"?>' + body)
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


def test_empty_registry_is_unverified_and_the_committed_registry_has_no_qualified_entry():
    # XXV section 9: the committed registry now records the tier-W Guidone holdout (qualified false). No committed
    # entry is qualified, so the measured lane must stay UNVERIFIED; an EMPTY registry reads REGISTRY_EMPTY.
    committed = json.loads((REPO / "experiments/sandbox_foundation/holdouts/REGISTRY.json").read_text())
    assert "schema_note" in committed
    assert all(e["qualified"] is False for e in committed["entries"])
    assert [e["tier"] for e in committed["entries"] if e["id"] == "GUIDONE2025-CA-XXV"] == ["W"]
    lane = sr.measured_lane(REPO / "experiments/sandbox_foundation/holdouts/REGISTRY.json", "HEAD")
    assert lane["status"] == sr.UNVERIFIED and lane["qualified_entries"] == []
    empty = json.loads(json.dumps(committed))
    empty["entries"] = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "REGISTRY.json"
        path.write_text(json.dumps(empty))
        lane = sr.measured_lane(path, "HEAD")
    assert lane["status"] == sr.UNVERIFIED and lane["reason"] == "REGISTRY_EMPTY"


# --- finding 3: a REAL git history (tmp repo), so ancestry, blob bytes and add-commits are measured, not stubbed
def _g(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
                           *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


REG_REL = "holdouts/REGISTRY.json"


@pytest.fixture
def history(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q")

    def commit(msg, files):
        for rel, content in files.items():
            f = repo / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", msg)
        return _g(repo, "rev-parse", "HEAD")

    pending = {"qualified": True, "outcome": "PENDING", "evidence": "ev/result.json"}
    root = commit("root", {"README": "root"})
    early = commit("a result committed BEFORE any preregistration", {"ev/early.json": '{"r": 0}'})
    pre = commit("preregister h1/h2/hearly", {REG_REL: json.dumps({"entries": [
        dict(pending, id="h1"), dict(pending, id="h2"), dict(pending, id="hearly", evidence="ev/early.json")]})})
    ev = commit("results", {"ev/result.json": '{"r": 1}', "ev/fail.json": '{"r": -1}'})
    run = commit("the run commit", {"other": "y"})
    sha = {rel: hashlib.sha256((repo / rel).read_bytes()).hexdigest()
           for rel in ("ev/result.json", "ev/fail.json", "ev/early.json")}
    return SimpleNamespace(repo=repo, root=root, early=early, pre=pre, ev=ev, run=run, sha=sha)


def _entry(h, **kw):
    e = {"id": "h1", "qualified": True, "outcome": "PASS", "prereg_commit": h.pre, "evidence": "ev/result.json",
         "evidence_sha256": h.sha["ev/result.json"]}
    e.update(kw)
    return e


def _lane(h, entries, run=None):
    reg = h.repo / REG_REL
    reg.write_text(json.dumps({"entries": entries}))           # the registry as it stands at run time
    return sr.measured_lane(reg, h.run if run is None else run, repo=h.repo)


def test_a_verified_preregistered_holdout_passes_the_control(history):
    lane = _lane(history, [_entry(history)])
    assert lane["status"] == sr.PASS, lane
    assert lane["qualified_entries"][0]["verified"] is True


def test_prereg_must_be_a_full_sha_strictly_before_the_run(history):
    h = history
    for pre in ("HEAD", "main", "HEAD~0", h.pre[:12], h.pre.upper(), h.run, "0" * 40, h.root):
        lane = _lane(h, [_entry(h, prereg_commit=pre)])
        assert lane["status"] == sr.INVALID_REGISTRY, (pre, lane)
    # the root IS a strict ancestor of everything; what it lacks is a PENDING registration of h1
    root_lane = _lane(h, [_entry(h, prereg_commit=h.root)])
    assert any("PENDING" in p for p in root_lane["invalid_entries"][0]["problems"])


def test_evidence_must_exist_match_and_postdate_the_preregistration(history):
    h = history
    assert _lane(h, [_entry(h, evidence="ev/absent.json")])["status"] == sr.INVALID_REGISTRY
    assert _lane(h, [_entry(h, evidence_sha256="0" * 64)])["status"] == sr.INVALID_REGISTRY
    assert _lane(h, [_entry(h, evidence_sha256=None)])["status"] == sr.INVALID_REGISTRY
    assert _lane(h, [_entry(h, evidence="../outside.json")])["status"] == sr.INVALID_REGISTRY
    early = _lane(h, [_entry(h, id="hearly", evidence="ev/early.json", evidence_sha256=h.sha["ev/early.json"])])
    assert early["status"] == sr.INVALID_REGISTRY                            # result committed before the prereg
    assert any("not a strict ancestor of evidence-adding" in p for p in early["invalid_entries"][0]["problems"])
    # evidence that exists in the working tree but not AT the run commit does not count
    (h.repo / "ev" / "later.json").write_text("{}")
    later = _entry(h, evidence="ev/later.json",
                   evidence_sha256=hashlib.sha256((h.repo / "ev" / "later.json").read_bytes()).hexdigest())
    assert _lane(h, [later])["status"] == sr.INVALID_REGISTRY
    # and a run commit that precedes the evidence cannot see it
    assert _lane(h, [_entry(h)], run=h.pre)["status"] == sr.INVALID_REGISTRY
    assert _lane(h, [_entry(h)], run="not-a-commit")["status"] == sr.INVALID_REGISTRY


def test_malformed_qualified_entries_invalidate_and_a_verified_fail_beats_a_pass(history):
    h = history
    good_fail = _entry(h, id="h2", outcome="FAIL", evidence="ev/fail.json", evidence_sha256=h.sha["ev/fail.json"])
    assert _lane(h, [_entry(h), good_fail])["status"] == sr.FAIL                # a sibling PASS does not outvote it
    bad_fail = dict(good_fail, prereg_commit="deadbeef")                       # the red-team (b2) shape
    assert _lane(h, [bad_fail, _entry(h)])["status"] == sr.INVALID_REGISTRY     # never dropped, never PASS
    for bad in ({"qualified": "true"}, {"qualified": 1}, {"qualified": None}, {"outcome": "pass"}, {"id": ""}):
        assert _lane(h, [_entry(h, **bad)])["status"] == sr.INVALID_REGISTRY, bad
    assert _lane(h, ["not an object", _entry(h)])["status"] == sr.INVALID_REGISTRY
    assert _lane(h, [_entry(h, qualified=False)])["status"] == sr.UNVERIFIED     # not qualified: not counted
    assert _lane(h, [_entry(h, outcome="PENDING")])["status"] == sr.UNVERIFIED
    assert sr.measured_lane(h.repo / "absent.json", h.run, repo=h.repo)["status"] == sr.UNVERIFIED


def test_a_tier_W_entry_can_never_qualify(history):
    # XXV runner review finding 11: a tier-W (weak, nuisance-limited) holdout cannot satisfy the 2.0-alpha gate whatever
    # its outcome, so a registry that marks one qualified is itself malformed -- even when every git check verifies.
    h = history
    assert _lane(h, [_entry(h)])["status"] == sr.PASS                          # control: the same entry, no tier
    for tier in ("W", " w "):
        lane = _lane(h, [_entry(h, tier=tier)])
        assert lane["status"] == sr.INVALID_REGISTRY, (tier, lane)
        assert any("tier" in p for p in lane["invalid_entries"][0]["problems"])
    assert _lane(h, [_entry(h, tier="W", qualified=False)])["status"] == sr.UNVERIFIED     # recorded, not counted
    note = json.loads((REPO / "experiments/sandbox_foundation/holdouts/REGISTRY.json").read_text())["schema_note"]
    assert '\"tier\"' in note and "tier W" in note


def test_a_registry_outside_the_repository_cannot_show_a_preregistration(history, tmp_path):
    lane = sr.measured_lane(_registry(tmp_path, [_entry(history)]), history.run, repo=history.repo)
    assert lane["status"] == sr.INVALID_REGISTRY


# --- finding 12: the production lane counts only a ci.yml run whose headSha IS the run commit
def test_production_lane_is_never_inferred(tmp_path):
    a, b = "a" * 40, "b" * 40
    assert sr.production_lane(None, a, a)["status"] == sr.NOT_EVALUATED
    runs = tmp_path / "runs.json"

    def ci(**kw):
        return dict({"databaseId": 1, "headSha": a, "status": "completed", "conclusion": "success",
                     "workflowName": sr.CI_WORKFLOW_NAME}, **kw)
    runs.write_text(json.dumps([ci(status="in_progress", conclusion="")]))
    assert sr.production_lane(runs, a, a)["status"] == sr.PENDING
    assert sr.production_lane(runs, b, b)["status"] == sr.NOT_EVALUATED
    runs.write_text(json.dumps([ci(conclusion="failure"), ci(databaseId=2)]))
    assert sr.production_lane(runs, a, a)["status"] == sr.PASS                   # the latest attempt decides
    runs.write_text("not json")
    assert sr.production_lane(runs, a, a)["status"] == sr.NOT_EVALUATED


def test_production_lane_refuses_another_workflow_and_another_commit(tmp_path):
    a, b = "a" * 40, "b" * 40
    runs = tmp_path / "runs.json"
    runs.write_text(json.dumps([{"databaseId": 9, "headSha": a, "status": "completed", "conclusion": "success",
                                 "workflowName": "Science reproduction", "url": "x"}]))
    assert sr.production_lane(runs, a, a)["status"] == sr.NOT_EVALUATED       # the red-team (c) shape
    runs.write_text(json.dumps([{"databaseId": 9, "headSha": a, "status": "completed", "conclusion": "success",
                                 "workflowName": sr.CI_WORKFLOW_NAME}]))
    assert sr.production_lane(runs, a, a)["status"] == sr.PASS                 # the control
    assert sr.production_lane(runs, a, b)["status"] == sr.NOT_EVALUATED       # head SHA is not the run commit
    assert sr.production_lane(runs, "HEAD", "HEAD")["status"] == sr.NOT_EVALUATED


def test_ci_workflow_name_constant_matches_ci_yml():
    names = re.findall(r"^name:\s*(.+?)\s*$", (REPO / ".github/workflows/ci.yml").read_text(), re.M)
    assert names[0].strip("'\"") == sr.CI_WORKFLOW_NAME


def test_receipt_keeps_four_separate_lanes_and_no_overall_verdict(tmp_path):
    rec = sr.build_receipt(run_commit="r", science_junit=_designated_junit(tmp_path), manifest=SCIENCE / "manifest.json",
                           registry=_registry(tmp_path, []), hashes_report=_hashes_ok(tmp_path))
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
    rec = sr.build_receipt(run_commit="r", science_junit=_designated_junit(tmp_path), hashes_report=bad,
                           manifest=SCIENCE / "manifest.json", registry=_registry(tmp_path, []))
    assert rec["lanes"]["live_reference_solver"]["status"] == sr.UNVERIFIED


# --- finding 4: an absent / unreadable / vendored-only pinned-bytes report can never leave the live lane PASS
def _designated_junit(tmp_path, *, per_file=None, name="designated.xml", extra=""):
    man = json.loads((SCIENCE / "manifest.json").read_text())
    n = per_file or -(-man["expected_executed"] // len(man["tests"]))
    cases = "".join(f'<testcase classname="{cj.module_of(t)}" name="test_{i}"/>' for t in man["tests"] for i in range(n))
    return _xml(tmp_path, name, f"<testsuites><testsuite>{cases}{extra}</testsuite></testsuites>")


def test_the_live_lane_needs_a_present_ok_pinned_bytes_report(tmp_path):
    j = _designated_junit(tmp_path)
    kw = dict(science_junit=j, manifest=SCIENCE / "manifest.json", registry=_registry(tmp_path, []))
    live = "live_reference_solver"
    assert sr.build_receipt(run_commit="r", hashes_report=_hashes_ok(tmp_path), **kw)["lanes"][live]["status"] == sr.PASS
    absent = sr.build_receipt(run_commit="r", **kw)["lanes"][live]
    assert absent["status"] == sr.UNVERIFIED and absent["reason"] == "PINNED_BYTES_REPORT_ABSENT"
    garbled = tmp_path / "garbled.json"
    garbled.write_text("{")
    assert sr.build_receipt(run_commit="r", hashes_report=garbled, **kw)["lanes"][live]["status"] == sr.UNVERIFIED
    vendored_only = tmp_path / "vendored-only.json"
    vendored_only.write_text(json.dumps({"ok": True, "installed": {"checked": False}, "files": [{"ok": True}]}))
    assert sr.build_receipt(run_commit="r", hashes_report=vendored_only, **kw)["lanes"][live]["status"] == sr.UNVERIFIED
    # the CLI maps a path that does not exist to "not supplied": that is now UNVERIFIED, not PASS (red-team (a))
    out = tmp_path / "receipt.json"
    sr.main(["--run-commit", "r", "--out", str(out), "--science-junit", str(j), "--hashes-report",
             str(tmp_path / "MISSING-hashes-after.json"), "--registry", str(_registry(tmp_path, []))])
    assert json.loads(out.read_text())["lanes"][live]["status"] == sr.UNVERIFIED


def test_verify_hashes_writes_a_report_even_on_unusable_input(tmp_path):
    report = tmp_path / "r.json"
    assert vh.main(["--expected", str(tmp_path / "absent.json"), "--report", str(report)]) == 2
    rep = json.loads(report.read_text())
    assert rep["ok"] is False and "INPUT_ERROR" in rep["error"]
    (tmp_path / "e.json").write_text(json.dumps({"vendored": ["not", "a", "map"]}))
    report.unlink()
    assert vh.main(["--expected", str(tmp_path / "e.json"), "--root", str(tmp_path), "--vendored-only",
                    "--report", str(report)]) == 2
    assert json.loads(report.read_text())["ok"] is False


def test_the_live_lane_counts_only_designated_files_and_unique_cases(tmp_path):
    man = json.loads((SCIENCE / "manifest.json").read_text())
    kw = dict(expected_executed=man["expected_executed"], designated=man["tests"])
    assert sr.junit_lane(_designated_junit(tmp_path), **kw)["status"] == sr.PASS          # the control
    foreign = _designated_junit(tmp_path, name="foreign.xml", extra='<testcase classname="tests.test_other" name="x"/>')
    assert sr.junit_lane(foreign, **kw)["status"] == sr.UNVERIFIED
    # enough cases, but all from ONE designated file: the other designated files never ran
    one = "".join(f'<testcase classname="{cj.module_of(man["tests"][0])}" name="t{i}"/>' for i in range(100))
    lane = sr.junit_lane(_xml(tmp_path, "one.xml", f"<testsuite>{one}</testsuite>"), **kw)
    assert lane["status"] == sr.UNVERIFIED and "no executed testcase" in lane["reason"]
    # 60 copies of one test name (the red-team shape) -- even from a designated file
    same = f'<testcase classname="{cj.module_of(man["tests"][0])}" name="same"/>' * 100
    assert sr.junit_lane(_xml(tmp_path, "same.xml", f"<testsuite>{same}</testsuite>"), **kw)["status"] == sr.UNVERIFIED
    # a class inside a designated module counts as that module
    cls = _designated_junit(tmp_path, name="cls.xml").read_text().replace(
        f'classname="{cj.module_of(man["tests"][0])}"', f'classname="{cj.module_of(man["tests"][0])}.TestX"')
    assert sr.junit_lane(_xml(tmp_path, "cls2.xml", cls.split("?>", 1)[1]), **kw)["status"] == sr.PASS


def test_the_receipt_reads_the_sandbox_floor_from_the_manifest(tmp_path):
    man = json.loads((SCIENCE / "manifest.json").read_text())
    floor = man["sandbox_expected_executed"]
    assert isinstance(floor, int) and not isinstance(floor, bool) and floor > 1000      # a measured floor, not 1
    rec = sr.build_receipt(run_commit="r", sandbox_junit=_junit(tmp_path, passed=floor - 1),
                           manifest=SCIENCE / "manifest.json", registry=_registry(tmp_path, []))
    assert rec["lanes"]["sandbox_numerical"]["status"] == sr.UNVERIFIED
    rec = sr.build_receipt(run_commit="r", sandbox_junit=_junit(tmp_path, passed=floor, name="full.xml"),
                           manifest=SCIENCE / "manifest.json", registry=_registry(tmp_path, []))
    assert rec["lanes"]["sandbox_numerical"]["status"] == sr.PASS


# --- check_junit: the three handcrafted shapes that fooled it, each beside a control that still passes
def test_check_junit_sees_nested_and_namespaced_outcomes_and_duplicates(tmp_path):
    ok = "".join(f'<testcase classname="c" name="t{i}"/>' for i in range(60))
    shapes = {
        "skip nested in properties": '<testcase classname="c" name="s"><properties><skipped message="x"/></properties>'
                                     '</testcase>',
        "namespaced skip": '<testcase classname="c" name="s"><j:skipped/></testcase>',
        "namespaced failure": '<testcase classname="c" name="s"><j:failure message="boom"/></testcase>',
        "nested error": '<testcase classname="c" name="s"><system-out><error/></system-out></testcase>',
        "duplicate name": '<testcase classname="c" name="t0"/>',
    }
    control = _xml(tmp_path, "control.xml", f'<testsuite xmlns:j="urn:x">{ok}<testcase classname="c" name="s">'
                                            f'<properties><property name="k" value="v"/></properties>'
                                            f'<system-out>skipped error failure</system-out></testcase></testsuite>')
    assert cj.main([str(control), "--expected-executed", "60"]) == 0
    for label, case in shapes.items():
        p = _xml(tmp_path, label.replace(" ", "_") + ".xml", f'<testsuite xmlns:j="urn:x">{ok}{case}</testsuite>')
        assert cj.main([str(p), "--expected-executed", "60"]) == 1, label
        assert sr.junit_lane(p, 60)["status"] != sr.PASS, label
    same = _xml(tmp_path, "same.xml", "<testsuite>" + '<testcase classname="c" name="same"/>' * 60 + "</testsuite>")
    assert cj.main([str(same), "--expected-executed", "60"]) == 1


def test_check_junit_manifest_mode_enforces_the_designated_files(tmp_path):
    assert cj.main([str(_designated_junit(tmp_path)), "--manifest", str(SCIENCE / "manifest.json")]) == 0
    foreign = _designated_junit(tmp_path, name="f.xml", extra='<testcase classname="x.test_y" name="z"/>')
    assert cj.main([str(foreign), "--manifest", str(SCIENCE / "manifest.json")]) == 1


# --- residual (a): the manifest floors may not drop silently against the PR base
def test_manifest_guard_refuses_an_unjustified_drop(tmp_path):
    base = json.loads((SCIENCE / "manifest.json").read_text())
    bp, hp, jp = tmp_path / "base.json", tmp_path / "head.json", tmp_path / "J.md"
    bp.write_text(json.dumps(base))

    def guard(head, just=None, base_just=None):
        hp.write_text(json.dumps(head))
        if just is None:
            jp.unlink(missing_ok=True)
        else:
            jp.write_text(just)
        args = ["--base", str(bp), "--head", str(hp), "--justification", str(jp)]
        if base_just is not None:
            (tmp_path / "BJ.md").write_text(base_just)
            args += ["--base-justification", str(tmp_path / "BJ.md")]
        return mg.main(args)

    n = base["expected_executed"]
    assert guard(base) == 0                                                         # unchanged: the control
    assert guard(dict(base, expected_executed=n + 5, tests=base["tests"] + ["x/test_new.py"])) == 0     # raising
    lowered = dict(base, expected_executed=n - 1)
    assert guard(lowered) == 1
    assert guard(lowered, "we dropped some tests") == 1                            # does not name the change
    token = f"expected_executed: {n} -> {n - 1}"
    assert guard(lowered, f"why: {token}") == 0
    assert guard(lowered, f"why: {token}", base_just=f"why: {token}") == 1         # a stale note excuses nothing
    gone = dict(base, tests=base["tests"][1:])
    assert guard(gone) == 1 and guard(gone, f"removed {base['tests'][0]}: reason") == 0
    sb = base["sandbox_expected_executed"]
    assert guard(dict(base, sandbox_expected_executed=sb - 1)) == 1
    assert guard({k: v for k, v in base.items() if k != "sandbox_expected_executed"}) == 1


# --- residual (b): a core-package change must trigger the science workflow
def test_science_workflow_triggers_on_the_core_package_and_guards_the_manifest():
    wf = (REPO / ".github/workflows/science.yml").read_text()
    paths = wf.split("pull_request:", 1)[1].split("permissions:", 1)[0]
    assert '"smartchem/**"' in paths and '"experiments/sandbox_foundation/**"' in paths
    assert "science.manifest_guard" in wf and "sandbox_expected_executed" in wf


def test_requirements_are_hash_locked():
    lines = [ln.strip() for ln in (SCIENCE / "requirements-science.txt").read_text().splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    reqs = [ln.rstrip(" \\") for ln in lines if not ln.startswith("--hash")]
    hashes = [ln for ln in lines if ln.startswith("--hash=sha256:")]
    assert reqs == ["phreeqpython==1.6.2", "periodictable==2.1.0", "pyparsing==3.3.3"]
    assert len(hashes) == 3 and all(len(x.split(":", 1)[1]) == 64 for x in hashes)
    exp = json.loads((SCIENCE / "expected_hashes.json").read_text())
    assert f"--hash=sha256:{exp['installed_phreeqpython']['wheel']['sha256']}" in hashes


@pytest.mark.parametrize("mod", [cj, sr, vh, mg])
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
