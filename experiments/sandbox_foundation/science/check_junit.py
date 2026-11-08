"""OPERATION XXV-2 (#166): fail a science run that skipped anything or executed fewer tests than declared.

    python -m experiments.sandbox_foundation.science.check_junit JUNIT.xml --manifest science/manifest.json
    python -m experiments.sandbox_foundation.science.check_junit JUNIT.xml --expected-executed 60

Exit 0 only if the junit file parses, has zero failures, zero errors, zero skips, and executed >= expected.
Exit 1 on any of those violations; exit 2 on a missing or unreadable input.  Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


class JunitError(ValueError):
    """The junit file is missing or cannot be read as a pytest junit report."""


def junit_summary(path) -> dict:
    """Counts and per-case outcomes, taken from the <testcase> elements (not the suite attributes)."""
    p = Path(path)
    if not p.is_file():
        raise JunitError(f"junit file not found: {p}")
    try:
        root = ET.parse(p).getroot()
    except ET.ParseError as exc:
        raise JunitError(f"junit file {p} does not parse: {exc}") from exc
    if root.tag not in ("testsuites", "testsuite"):
        raise JunitError(f"junit file {p} has root <{root.tag}>, expected <testsuites> or <testsuite>")
    cases = list(root.iter("testcase"))
    out = {"path": str(p), "tests": len(cases), "passed": 0, "failures": 0, "errors": 0, "skipped": 0,
           "skipped_cases": [], "failed_cases": []}
    for tc in cases:
        name = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        kinds = {child.tag for child in tc}
        if "failure" in kinds:
            out["failures"] += 1
            out["failed_cases"].append({"case": name, "kind": "failure"})
        elif "error" in kinds:
            out["errors"] += 1
            out["failed_cases"].append({"case": name, "kind": "error"})
        elif "skipped" in kinds:
            sk = tc.find("skipped")
            out["skipped"] += 1
            out["skipped_cases"].append({"case": name, "reason": (sk.get("message") or sk.text or "").strip()})
        else:
            out["passed"] += 1
    out["executed"] = out["tests"] - out["skipped"]
    return out


def violations(summary: dict, expected_executed: int) -> list:
    """Every reason this run cannot count as a complete science run (empty list = clean)."""
    v = []
    if summary["failures"] or summary["errors"]:
        v.append(f"{summary['failures']} failure(s), {summary['errors']} error(s)")
    if summary["skipped"]:
        v.append(f"{summary['skipped']} skipped: " + "; ".join(f"{c['case']} ({c['reason']})"
                                                             for c in summary["skipped_cases"]))
    if summary["executed"] < expected_executed:
        v.append(f"executed {summary['executed']} < expected {expected_executed}")
    if summary["executed"] == 0:
        v.append("no test executed")
    return v


def expected_from_manifest(path) -> int:
    data = json.loads(Path(path).read_text())
    n = data.get("expected_executed")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise JunitError(f"{path}: expected_executed must be an int >= 1")
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("junit")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--manifest")
    g.add_argument("--expected-executed", type=int)
    a = ap.parse_args(argv)
    try:
        expected = expected_from_manifest(a.manifest) if a.manifest else a.expected_executed
        s = junit_summary(a.junit)
    except (JunitError, OSError, json.JSONDecodeError) as exc:
        print(f"check_junit: INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    v = violations(s, expected)
    print(json.dumps({"summary": {k: s[k] for k in ("tests", "executed", "passed", "failures", "errors", "skipped")},
                      "expected_executed": expected, "violations": v}, indent=2))
    if v:
        print("check_junit: FAIL -- " + " | ".join(v), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
