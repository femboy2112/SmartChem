"""OPERATION XXV-2 (#166): the science run's JSON receipt, with FOUR SEPARATE lanes.

    production_compat      the hosted 1.x ci.yml run (workflowName == CI_WORKFLOW_NAME) whose headSha IS the run
                           commit, read from a `gh run list --json` dump.  Absent or unreadable dump, another
                           workflow's run, or a head SHA other than the run commit => NOT_EVALUATED (never inferred).
    sandbox_numerical      sandbox_foundation pytest junit, executed >= manifest sandbox_expected_executed.
                           Absent => NOT_EVALUATED.
    live_reference_solver  the designated science junit (manifest.json): every case from a designated file, every
                           designated file executed, unique case names, no skip, executed >= expected_executed, AND a
                           present pinned-bytes report with ok == true and the installed solver checked.  Any gap =>
                           UNVERIFIED, never PASS.
    measured_validation    holdouts/REGISTRY.json.  A qualified entry counts only if VERIFIED with git: prereg_commit is
                           a full 40-hex commit and a STRICT ancestor of the run commit AND of every commit that added
                           its evidence file (preregistration before result); the registry AT prereg_commit already
                           holds the entry's id as a qualified PENDING entry; the evidence file exists at the run
                           commit and hashes to evidence_sha256.  ANY malformed or unverifiable qualified entry =>
                           INVALID_REGISTRY (never silently dropped); any verified qualified FAIL => FAIL (a sibling
                           PASS does not outvote it); PASS only for a verified qualified PASS; otherwise UNVERIFIED.

A PASS in one lane implies NOTHING about another; the receipt has no overall verdict.  Stdlib only.

    python -m experiments.sandbox_foundation.science.status_record --run-commit SHA --out receipt.json \
        [--science-junit J] [--sandbox-junit J] [--production-runs RUNS.json --production-head-sha SHA] \
        [--hashes-report R.json] [--manifest M] [--registry R]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

from experiments.sandbox_foundation.science.check_junit import JunitError, junit_summary, violations

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / "manifest.json"
REGISTRY = HERE.parent / "holdouts" / "REGISTRY.json"

PASS, FAIL, UNVERIFIED, NOT_EVALUATED, PENDING = "PASS", "FAIL", "UNVERIFIED", "NOT_EVALUATED", "PENDING"
INVALID_REGISTRY = "INVALID_REGISTRY"
LANES = ("production_compat", "sandbox_numerical", "live_reference_solver", "measured_validation")
#: the top-level ``name:`` of .github/workflows/ci.yml (pinned by test_xxv_science_status.py)
CI_WORKFLOW_NAME = "CI"
_SHA1_40 = re.compile(r"[0-9a-f]{40}")
_SHA256_64 = re.compile(r"[0-9a-f]{64}")


def _counts(s: dict) -> dict:
    return {k: s[k] for k in ("tests", "executed", "passed", "failures", "errors", "skipped")}


def junit_lane(path, expected_executed: int = 1, designated=None) -> dict:
    """PASS only for a readable junit with no failure, no error, NO SKIP, unique case names, executed >=
    expected_executed and (when ``designated`` is given) every case from -- and every file in -- the designated list."""
    if path is None:
        return {"status": NOT_EVALUATED, "reason": "NO_JUNIT_SUPPLIED"}
    try:
        s = junit_summary(path)
    except JunitError as exc:
        return {"status": NOT_EVALUATED, "reason": f"JUNIT_UNREADABLE: {exc}"}
    out = {"counts": _counts(s), "expected_executed": expected_executed, "skipped_cases": s["skipped_cases"],
           "failed_cases": s["failed_cases"], "duplicate_cases": s["duplicate_cases"][:20], "junit": str(path)}
    if s["failures"] or s["errors"]:
        return dict(out, status=FAIL, reason="TEST_FAILURES")
    try:
        v = violations(s, expected_executed, designated)
    except JunitError as exc:
        return dict(out, status=UNVERIFIED, reason=f"DESIGNATED_LIST_UNUSABLE: {exc}")
    if v:
        return dict(out, status=UNVERIFIED, reason="; ".join(v))
    return dict(out, status=PASS, reason="ALL_EXECUTED_NO_SKIP")


def production_lane(runs_path, head_sha, run_commit) -> dict:
    """From `gh run list --workflow ci.yml --json databaseId,headSha,status,conclusion,workflowName,url`.  Only a run
    of the ci.yml workflow (by workflowName) whose headSha is the run commit itself is considered."""
    if runs_path is None or not head_sha:
        return {"status": NOT_EVALUATED, "reason": "NO_PRODUCTION_RUN_DATA_SUPPLIED"}
    if not (isinstance(run_commit, str) and _SHA1_40.fullmatch(run_commit)) or head_sha != run_commit:
        return {"status": NOT_EVALUATED, "head_sha": head_sha, "run_commit": run_commit,
                "reason": "PRODUCTION_HEAD_SHA_IS_NOT_THE_RUN_COMMIT (the lanes must describe one commit)"}
    try:
        runs = json.loads(Path(runs_path).read_text())
    except (OSError, ValueError) as exc:
        return {"status": NOT_EVALUATED, "reason": f"PRODUCTION_RUN_DATA_UNREADABLE: {exc}"}
    if not isinstance(runs, list):
        return {"status": NOT_EVALUATED, "reason": "PRODUCTION_RUN_DATA_NOT_A_LIST"}
    mine = [r for r in runs if isinstance(r, dict) and r.get("headSha") == head_sha
            and r.get("workflowName") == CI_WORKFLOW_NAME
            and isinstance(r.get("databaseId"), int) and not isinstance(r.get("databaseId"), bool)]
    if not mine:
        return {"status": NOT_EVALUATED, "reason": f"NO_{CI_WORKFLOW_NAME}_RUN_FOR_HEAD_SHA {head_sha}"}
    r = max(mine, key=lambda x: x["databaseId"])                     # the latest attempt for this SHA
    base = {"head_sha": head_sha, "run_id": r["databaseId"], "run_status": r.get("status"),
            "conclusion": r.get("conclusion"), "url": r.get("url")}
    if r.get("status") != "completed":
        return dict(base, status=PENDING, reason="CI_RUN_NOT_COMPLETED (in progress is not a pass)")
    if r.get("conclusion") == "success":
        return dict(base, status=PASS, reason="CI_RUN_COMPLETED_SUCCESS")
    return dict(base, status=FAIL, reason=f"CI_RUN_CONCLUSION_{r.get('conclusion')}")


def _git(repo, *args, binary: bool = False):
    """Run git read-only; None if git itself could not be run."""
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=not binary, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None


def git_resolve_commit(rev, repo=REPO):
    """The full 40-hex SHA of the commit ``rev`` names, or None if it does not name a commit."""
    if not isinstance(rev, str) or not rev or rev.startswith("-"):
        return None
    p = _git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    if p is None or p.returncode != 0:
        return None
    out = p.stdout.strip()
    return out if _SHA1_40.fullmatch(out) else None


def git_is_strict_ancestor(commit: str, descendant: str, repo=REPO) -> bool:
    """True iff ``commit`` != ``descendant`` and ``commit`` is reachable from ``descendant`` (both full SHAs)."""
    if commit == descendant:
        return False
    p = _git(repo, "merge-base", "--is-ancestor", commit, descendant)
    return p is not None and p.returncode == 0


def git_blob_at(commit: str, path: str, repo=REPO):
    """The bytes of ``path`` in ``commit``'s tree, or None if absent."""
    p = _git(repo, "cat-file", "blob", f"{commit}:{path}", binary=True)
    return p.stdout if p is not None and p.returncode == 0 else None


def git_adding_commits(commit: str, path: str, repo=REPO):
    """Every commit reachable from ``commit`` that ADDED ``path`` (renames counted as adds, merges diffed against each
    parent), or None if git could not answer."""
    p = _git(repo, "log", "--full-history", "-m", "--no-renames", "--diff-filter=A", "--format=%H", commit,
             "--", path)
    if p is None or p.returncode != 0:
        return None
    return sorted({ln.strip() for ln in p.stdout.splitlines() if ln.strip()})


def _safe_rel_path(path) -> bool:
    if not isinstance(path, str) or not path or "\\" in path:
        return False
    pp = PurePosixPath(path)
    return not pp.is_absolute() and all(part not in ("", ".", "..") for part in path.split("/"))


def _preregistered_at(commit: str, registry_rel, entry_id: str, repo=REPO) -> bool:
    """True iff the registry at ``commit`` already holds ``entry_id`` as a qualified PENDING entry -- the comparison
    was registered before its outcome (an arbitrary ancestor such as the root commit holds no such entry)."""
    if registry_rel is None:
        return False
    blob = git_blob_at(commit, registry_rel, repo)
    try:
        reg = json.loads(blob.decode("utf-8")) if blob is not None else None
    except (UnicodeDecodeError, ValueError):
        return False
    ents = reg.get("entries") if isinstance(reg, dict) else None
    return isinstance(ents, list) and any(
        isinstance(x, dict) and x.get("id") == entry_id and x.get("qualified") is True and x.get("outcome") == "PENDING"
        for x in ents)


def verify_holdout_entry(e: dict, run_full: str, repo=REPO, registry_rel=None) -> list:
    """Every reason a QUALIFIED registry entry cannot be verified at ``run_full`` (empty list = verified).
    ``registry_rel``: the registry's repo-relative path, used to confirm the entry was PENDING at prereg_commit."""
    probs = []
    if not (isinstance(e.get("id"), str) and e["id"]):
        probs.append("id must be a non-empty string")
    if e.get("outcome") not in ("PASS", "FAIL", "PENDING"):
        probs.append(f"outcome {e.get('outcome')!r} is not PASS | FAIL | PENDING")
    pre, ev, ev_sha = e.get("prereg_commit"), e.get("evidence"), e.get("evidence_sha256")
    if not (isinstance(pre, str) and _SHA1_40.fullmatch(pre)):
        probs.append(f"prereg_commit {pre!r} is not a full 40-hex lowercase SHA")
    if not _safe_rel_path(ev):
        probs.append(f"evidence {ev!r} is not a repo-relative path")
    if not (isinstance(ev_sha, str) and _SHA256_64.fullmatch(ev_sha)):
        probs.append(f"evidence_sha256 {ev_sha!r} is not a 64-hex lowercase sha256")
    if probs:
        return probs
    if git_resolve_commit(pre, repo) != pre:
        return [f"prereg_commit {pre} does not resolve to a commit"]
    if not git_is_strict_ancestor(pre, run_full, repo):
        probs.append(f"prereg_commit {pre} is not a strict ancestor of the run commit {run_full}")
    if not _preregistered_at(pre, registry_rel, e["id"], repo):
        probs.append(f"the registry at prereg_commit {pre} holds no qualified PENDING entry {e['id']!r} "
                     f"(nothing was preregistered there)")
    blob = git_blob_at(run_full, ev, repo)
    if blob is None:
        probs.append(f"evidence {ev} does not exist at the run commit")
    elif hashlib.sha256(blob).hexdigest() != ev_sha:
        probs.append(f"evidence {ev} at the run commit hashes to {hashlib.sha256(blob).hexdigest()}, "
                     f"not evidence_sha256 {ev_sha}")
    adds = git_adding_commits(run_full, ev, repo)
    if not adds:
        probs.append(f"no commit adding evidence {ev} is visible from the run commit (shallow clone?)")
    else:
        late = [a for a in adds if not git_is_strict_ancestor(pre, a, repo)]
        if late:
            probs.append(f"prereg_commit {pre} is not a strict ancestor of evidence-adding commit(s) {late} "
                         f"(the result was not committed after the preregistration)")
    return probs


def measured_lane(registry_path, run_commit, repo=REPO) -> dict:
    try:
        reg = json.loads(Path(registry_path).read_text())
    except (OSError, ValueError) as exc:
        return {"status": UNVERIFIED, "reason": f"REGISTRY_UNREADABLE: {exc}"}
    entries = reg.get("entries") if isinstance(reg, dict) else None
    if not isinstance(entries, list):
        return {"status": UNVERIFIED, "reason": "REGISTRY_HAS_NO_ENTRIES_LIST"}
    base = {"registry": str(registry_path), "n_entries": len(entries)}
    if not entries:
        return dict(base, qualified_entries=[], status=UNVERIFIED, reason="REGISTRY_EMPTY")
    run_full = git_resolve_commit(run_commit, repo)
    try:
        registry_rel = Path(registry_path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        registry_rel = None                             # outside the repository: no preregistration can be shown
    considered, invalid = [], []
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or type(e.get("qualified")) is not bool:
            invalid.append({"index": i, "id": e.get("id") if isinstance(e, dict) else None,
                            "problems": ["entry is not an object with a JSON-boolean 'qualified'"]})
            continue
        if e["qualified"] is not True:
            continue
        probs = (["run commit does not resolve to a commit"] if run_full is None
                 else verify_holdout_entry(e, run_full, repo, registry_rel))
        row = {"index": i, "id": e.get("id"), "outcome": e.get("outcome"), "prereg_commit": e.get("prereg_commit"),
               "evidence": e.get("evidence"), "verified": not probs, "problems": probs}
        considered.append(row)
        if probs:
            invalid.append(row)
    base.update(run_commit_resolved=run_full, qualified_entries=considered)
    if invalid:
        return dict(base, status=INVALID_REGISTRY, invalid_entries=invalid,
                    reason="MALFORMED_OR_UNVERIFIABLE_QUALIFIED_ENTRY (fail closed; never dropped)")
    if any(c["outcome"] == "FAIL" for c in considered):
        return dict(base, status=FAIL, reason="QUALIFIED_HOLDOUT_FAILED")
    if any(c["outcome"] == "PASS" for c in considered):
        return dict(base, status=PASS, reason="QUALIFIED_PREREGISTERED_HOLDOUT_PASSED")
    return dict(base, status=UNVERIFIED, reason="NO_QUALIFIED_PREREGISTERED_PASS")


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


def _pinned_bytes_problem(hashes):
    """None iff the pinned-bytes report is present, ok == true, and checked the installed solver too."""
    if hashes is None:
        return "PINNED_BYTES_REPORT_ABSENT"
    if not isinstance(hashes, dict) or hashes.get("ok") is not True:
        return "PINNED_BYTES_NOT_VERIFIED"
    inst = hashes.get("installed")
    if not (isinstance(inst, dict) and inst.get("checked") is True):
        return "PINNED_BYTES_INSTALLED_SOLVER_NOT_CHECKED"
    return None


def build_receipt(*, run_commit, science_junit=None, sandbox_junit=None, production_runs=None,
                  production_head_sha=None, hashes_report=None, manifest=MANIFEST, registry=REGISTRY,
                  repo=REPO) -> dict:
    man = json.loads(Path(manifest).read_text())
    hashes = None
    if hashes_report is not None:
        try:
            hashes = json.loads(Path(hashes_report).read_text())
        except (OSError, ValueError) as exc:
            hashes = {"ok": False, "problem": f"HASH_REPORT_UNREADABLE: {exc}"}
    lanes = {
        "production_compat": production_lane(production_runs, production_head_sha, run_commit),
        "sandbox_numerical": junit_lane(sandbox_junit, int(man["sandbox_expected_executed"])),
        "live_reference_solver": junit_lane(science_junit, int(man["expected_executed"]), man["tests"]),
        "measured_validation": measured_lane(registry, run_commit, repo),
    }
    pin_problem = _pinned_bytes_problem(hashes)
    if pin_problem and lanes["live_reference_solver"]["status"] == PASS:
        lanes["live_reference_solver"] = dict(lanes["live_reference_solver"], status=UNVERIFIED, reason=pin_problem)
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
