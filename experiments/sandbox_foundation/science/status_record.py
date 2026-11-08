"""OPERATION XXV-2 (#166): the science run's JSON receipt, with FOUR SEPARATE lanes.

    production_compat      the hosted 1.x ci.yml run for this head SHA, read from a `gh run list --json` dump.
                           Absent or unreadable dump => NOT_EVALUATED (never inferred from anything else).
    sandbox_numerical      sandbox_foundation pytest junit.  Absent => NOT_EVALUATED.
    live_reference_solver  the designated science junit (manifest.json).  Any skip => UNVERIFIED, never PASS.
    measured_validation    holdouts/REGISTRY.json.  PASS only for a qualified PASS entry whose prereg_commit is an
                           ancestor of the run commit; otherwise UNVERIFIED (a qualified FAIL => FAIL).

A PASS in one lane implies NOTHING about another; the receipt has no overall verdict.  Stdlib only.

    python -m experiments.sandbox_foundation.science.status_record --run-commit SHA --out receipt.json \
        [--science-junit J] [--sandbox-junit J] [--production-runs RUNS.json --production-head-sha SHA] \
        [--hashes-report R.json] [--manifest M] [--registry R]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from experiments.sandbox_foundation.science.check_junit import JunitError, junit_summary, violations

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / "manifest.json"
REGISTRY = HERE.parent / "holdouts" / "REGISTRY.json"

PASS, FAIL, UNVERIFIED, NOT_EVALUATED, PENDING = "PASS", "FAIL", "UNVERIFIED", "NOT_EVALUATED", "PENDING"
LANES = ("production_compat", "sandbox_numerical", "live_reference_solver", "measured_validation")


def _counts(s: dict) -> dict:
    return {k: s[k] for k in ("tests", "executed", "passed", "failures", "errors", "skipped")}


def junit_lane(path, expected_executed: int = 1) -> dict:
    """PASS only for a readable junit with no failure, no error, NO SKIP and executed >= expected_executed."""
    if path is None:
        return {"status": NOT_EVALUATED, "reason": "NO_JUNIT_SUPPLIED"}
    try:
        s = junit_summary(path)
    except JunitError as exc:
        return {"status": NOT_EVALUATED, "reason": f"JUNIT_UNREADABLE: {exc}"}
    out = {"counts": _counts(s), "expected_executed": expected_executed, "skipped_cases": s["skipped_cases"],
           "failed_cases": s["failed_cases"], "junit": str(path)}
    if s["failures"] or s["errors"]:
        return dict(out, status=FAIL, reason="TEST_FAILURES")
    v = violations(s, expected_executed)
    if v:
        return dict(out, status=UNVERIFIED, reason="; ".join(v))
    return dict(out, status=PASS, reason="ALL_EXECUTED_NO_SKIP")


def production_lane(runs_path, head_sha) -> dict:
    """From `gh run list --workflow ci.yml --json databaseId,headSha,status,conclusion,workflowName,url`."""
    if runs_path is None or not head_sha:
        return {"status": NOT_EVALUATED, "reason": "NO_PRODUCTION_RUN_DATA_SUPPLIED"}
    try:
        runs = json.loads(Path(runs_path).read_text())
    except (OSError, ValueError) as exc:
        return {"status": NOT_EVALUATED, "reason": f"PRODUCTION_RUN_DATA_UNREADABLE: {exc}"}
    if not isinstance(runs, list):
        return {"status": NOT_EVALUATED, "reason": "PRODUCTION_RUN_DATA_NOT_A_LIST"}
    mine = [r for r in runs if isinstance(r, dict) and r.get("headSha") == head_sha
            and isinstance(r.get("databaseId"), int)]
    if not mine:
        return {"status": NOT_EVALUATED, "reason": f"NO_CI_RUN_FOR_HEAD_SHA {head_sha}"}
    r = max(mine, key=lambda x: x["databaseId"])                     # the latest attempt for this SHA
    base = {"head_sha": head_sha, "run_id": r["databaseId"], "run_status": r.get("status"),
            "conclusion": r.get("conclusion"), "url": r.get("url")}
    if r.get("status") != "completed":
        return dict(base, status=PENDING, reason="CI_RUN_NOT_COMPLETED (in progress is not a pass)")
    if r.get("conclusion") == "success":
        return dict(base, status=PASS, reason="CI_RUN_COMPLETED_SUCCESS")
    return dict(base, status=FAIL, reason=f"CI_RUN_CONCLUSION_{r.get('conclusion')}")


def git_is_ancestor(commit: str, run_commit: str, repo=REPO) -> bool:
    try:
        p = subprocess.run(["git", "merge-base", "--is-ancestor", commit, run_commit], cwd=repo,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return p.returncode == 0


def measured_lane(registry_path, run_commit, is_ancestor=git_is_ancestor) -> dict:
    try:
        reg = json.loads(Path(registry_path).read_text())
    except (OSError, ValueError) as exc:
        return {"status": UNVERIFIED, "reason": f"REGISTRY_UNREADABLE: {exc}"}
    entries = reg.get("entries") if isinstance(reg, dict) else None
    if not isinstance(entries, list):
        return {"status": UNVERIFIED, "reason": "REGISTRY_HAS_NO_ENTRIES_LIST"}
    considered = []
    for e in entries:
        if not isinstance(e, dict) or e.get("qualified") is not True:
            continue
        pre = e.get("prereg_commit")
        anc = isinstance(pre, str) and bool(pre) and bool(run_commit) and is_ancestor(pre, run_commit)
        considered.append({"id": e.get("id"), "outcome": e.get("outcome"), "prereg_commit": pre,
                           "prereg_is_ancestor": anc})
    valid = [c for c in considered if c["prereg_is_ancestor"]]
    base = {"registry": str(registry_path), "n_entries": len(entries), "qualified_entries": considered}
    if any(c["outcome"] == "FAIL" for c in valid):
        return dict(base, status=FAIL, reason="QUALIFIED_HOLDOUT_FAILED")
    if any(c["outcome"] == "PASS" for c in valid):
        return dict(base, status=PASS, reason="QUALIFIED_PREREGISTERED_HOLDOUT_PASSED")
    return dict(base, status=UNVERIFIED, reason="NO_QUALIFIED_PREREGISTERED_PASS" if entries else "REGISTRY_EMPTY")


def _environment() -> dict:
    import importlib.metadata as md
    vers = {}
    for dist in ("phreeqpython", "periodictable", "pyparsing", "numpy", "scipy", "pytest"):
        try:
            vers[dist] = md.version(dist)
        except md.PackageNotFoundError:
            vers[dist] = None
    return {"python": sys.version, "implementation": platform.python_implementation(),
            "platform": platform.platform(), "distributions": vers}


def build_receipt(*, run_commit, science_junit=None, sandbox_junit=None, production_runs=None,
                  production_head_sha=None, hashes_report=None, manifest=MANIFEST, registry=REGISTRY,
                  is_ancestor=git_is_ancestor) -> dict:
    man = json.loads(Path(manifest).read_text())
    hashes = None
    if hashes_report is not None:
        try:
            hashes = json.loads(Path(hashes_report).read_text())
        except (OSError, ValueError) as exc:
            hashes = {"ok": False, "problem": f"HASH_REPORT_UNREADABLE: {exc}"}
    lanes = {
        "production_compat": production_lane(production_runs, production_head_sha),
        "sandbox_numerical": junit_lane(sandbox_junit),
        "live_reference_solver": junit_lane(science_junit, int(man["expected_executed"])),
        "measured_validation": measured_lane(registry, run_commit, is_ancestor),
    }
    if hashes is not None and hashes.get("ok") is not True and lanes["live_reference_solver"]["status"] == PASS:
        lanes["live_reference_solver"] = dict(lanes["live_reference_solver"], status=UNVERIFIED,
                                              reason="PINNED_BYTES_NOT_VERIFIED")
    return {
        "schema": "smartchem-science-receipt/1",
        "run_commit": run_commit,
        "production_head_sha": production_head_sha,
        "github": {k: os.environ.get(k) for k in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
                                                  "GITHUB_EVENT_NAME", "GITHUB_REF", "GITHUB_SHA")},
        "environment": _environment(),
        "pinned_bytes": hashes,
        "science_tests": man["tests"],
        "lanes": lanes,
        "non_implication": "Lanes are independent. production/sandbox/live-reference PASS never implies "
                           "measured_validation; live-reference agreement is MODEL-vs-MODEL, not measurement.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-commit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--science-junit")
    ap.add_argument("--sandbox-junit")
    ap.add_argument("--production-runs")
    ap.add_argument("--production-head-sha")
    ap.add_argument("--hashes-report")
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--registry", default=str(REGISTRY))
    a = ap.parse_args(argv)

    def _opt(p):                                    # a path that does not exist is "not supplied"
        return p if p and Path(p).is_file() else None

    rec = build_receipt(run_commit=a.run_commit, science_junit=a.science_junit, sandbox_junit=a.sandbox_junit,
                        production_runs=_opt(a.production_runs), production_head_sha=a.production_head_sha,
                        hashes_report=_opt(a.hashes_report), manifest=a.manifest, registry=a.registry)
    Path(a.out).write_text(json.dumps(rec, indent=2, sort_keys=True))
    print(json.dumps({k: v["status"] for k, v in rec["lanes"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
