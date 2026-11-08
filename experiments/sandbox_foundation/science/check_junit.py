"""OPERATION XXV-2 (#166): fail a science run that skipped anything or executed fewer tests than declared.

    python -m experiments.sandbox_foundation.science.check_junit JUNIT.xml --manifest science/manifest.json
    python -m experiments.sandbox_foundation.science.check_junit JUNIT.xml --expected-executed 60

Exit 0 only if the junit file parses, has zero failures, zero errors, zero skips, executed >= expected, and every
(classname, name) pair is unique.  With --manifest, every testcase must also come from one of the manifest's designated
test files (matched on the pytest classname) and every designated file must contribute an executed testcase.
Exit 1 on any of those violations; exit 2 on a missing or unreadable input.  Stdlib only.

An outcome element is recognised by its LOCAL name (namespace stripped) anywhere beneath its <testcase>, not only as a
direct child: a <skipped/> tucked inside <properties>, or spelled <j:skipped/>, is still a skip.
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
           "skipped_cases": [], "failed_cases": [], "duplicate_cases": [], "classnames": [],
           "executed_classnames": []}
    seen = set()
    for tc in cases:
        key = (tc.get("classname", ""), tc.get("name", ""))
        name = f"{key[0]}::{key[1]}"
        if key in seen:
            out["duplicate_cases"].append(name)
        seen.add(key)
        out["classnames"].append(key[0])
        # every descendant, namespace stripped: nesting or a prefix must not hide an outcome
        found = {}
        for el in tc.iter():
            if el is not tc:
                found.setdefault(_local(el.tag), el)
        if "failure" in found:
            out["failures"] += 1
            out["failed_cases"].append({"case": name, "kind": "failure"})
        elif "error" in found:
            out["errors"] += 1
            out["failed_cases"].append({"case": name, "kind": "error"})
        elif "skipped" in found:
            sk = found["skipped"]
            out["skipped"] += 1
            out["skipped_cases"].append({"case": name, "reason": (sk.get("message") or sk.text or "").strip()})
        else:
            out["passed"] += 1
        if "skipped" not in found:
            out["executed_classnames"].append(key[0])
    out["executed"] = out["tests"] - out["skipped"]
    return out


def _local(tag) -> str:
    """The local name of an element tag ('{urn:x}skipped' -> 'skipped'); comments/PIs have no string tag."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def module_of(test_file: str) -> str:
    """The pytest junit classname prefix of a repo-relative test file ('a/b/test_x.py' -> 'a.b.test_x')."""
    rel = str(test_file)
    if not rel.endswith(".py"):
        raise JunitError(f"designated test file {rel!r} is not a .py file")
    return rel[:-3].replace("/", ".")


def _from(classname: str, module: str) -> bool:
    return classname == module or classname.startswith(module + ".")


def designated_violations(summary: dict, designated) -> list:
    """Every testcase must come from a designated file; every designated file must contribute an executed case."""
    mods = [module_of(t) for t in designated]
    v = []
    foreign = sorted({c for c in summary["classnames"] if not any(_from(c, m) for m in mods)})
    if foreign:
        v.append(f"testcase(s) not from the designated files: {foreign[:5]}")
    idle = [t for t, m in zip(designated, mods) if not any(_from(c, m) for c in summary["executed_classnames"])]
    if idle:
        v.append(f"designated file(s) with no executed testcase: {idle}")
    return v


def violations(summary: dict, expected_executed: int, designated=None) -> list:
    """Every reason this run cannot count as a complete science run (empty list = clean).  ``designated``: the
    manifest's test files, when the cases must come from them."""
    v = []
    if summary["duplicate_cases"]:
        v.append(f"{len(summary['duplicate_cases'])} duplicate (classname, name) testcase(s): "
                 + "; ".join(sorted(set(summary["duplicate_cases"]))[:5]))
    if summary["failures"] or summary["errors"]:
        v.append(f"{summary['failures']} failure(s), {summary['errors']} error(s)")
    if summary["skipped"]:
        v.append(f"{summary['skipped']} skipped: " + "; ".join(f"{c['case']} ({c['reason']})"
                                                             for c in summary["skipped_cases"]))
    if summary["executed"] < expected_executed:
        v.append(f"executed {summary['executed']} < expected {expected_executed}")
    if summary["executed"] == 0:
        v.append("no test executed")
    if designated is not None:
        v.extend(designated_violations(summary, designated))
    return v


def expected_from_manifest(path) -> int:
    data = json.loads(Path(path).read_text())
    n = data.get("expected_executed")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise JunitError(f"{path}: expected_executed must be an int >= 1")
    return n


def designated_from_manifest(path) -> list:
    data = json.loads(Path(path).read_text())
    t = data.get("tests")
    if not isinstance(t, list) or not t or not all(isinstance(x, str) and x.endswith(".py") for x in t):
        raise JunitError(f"{path}: tests must be a non-empty list of .py paths")
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("junit")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--manifest")
    g.add_argument("--expected-executed", type=int)
    a = ap.parse_args(argv)
    try:
        expected = expected_from_manifest(a.manifest) if a.manifest else a.expected_executed
        designated = designated_from_manifest(a.manifest) if a.manifest else None
        s = junit_summary(a.junit)
    except (JunitError, OSError, json.JSONDecodeError) as exc:
        print(f"check_junit: INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    v = violations(s, expected, designated)
    print(json.dumps({"summary": {k: s[k] for k in ("tests", "executed", "passed", "failures", "errors", "skipped")},
                      "expected_executed": expected, "violations": v}, indent=2))
    if v:
        print("check_junit: FAIL -- " + " | ".join(v), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
