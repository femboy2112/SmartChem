"""OPERATION XXV-2 (#166) red-team residual (a): a pull request must not quietly lower the science manifest's floors.

    python -m experiments.sandbox_foundation.science.manifest_guard --base BASE_MANIFEST.json --head HEAD_MANIFEST.json \
        --justification science/MANIFEST_CHANGE_JUSTIFICATION.md [--base-justification BASE_JUSTIFICATION.md]

Compared against the PR base: every count in COUNT_KEYS that the base declares may not drop, and no designated test file
may disappear, UNLESS the committed justification file mentions each such change verbatim --
``<key>: <base> -> <head>`` for a lowered count and the file's repo path for a removed test file -- AND the
justification differs from the base's copy (an old note cannot excuse a new drop).  Raising a count or adding a file
needs no justification.  Exit 0 = no unjustified drop; 1 = an unjustified drop; 2 = unusable input.  Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

COUNT_KEYS = ("expected_executed", "sandbox_expected_executed")


def _count(man: dict, key: str):
    n = man.get(key)
    if isinstance(n, bool) or not isinstance(n, int):
        return None
    return n


def drops(base: dict, head: dict) -> list:
    """Every lowering of a declared count and every disappearance of a designated file, as (kind, detail, token)."""
    out = []
    for key in COUNT_KEYS:
        if key not in base:
            continue
        b, h = _count(base, key), _count(head, key)
        if b is None:
            raise ValueError(f"base manifest {key!r} is not an int")
        if h is None:
            out.append(("count", f"{key} removed or not an int (base {b})", f"{key}: {b} -> {head.get(key)!r}"))
        elif h < b:
            out.append(("count", f"{key} lowered {b} -> {h}", f"{key}: {b} -> {h}"))
    base_tests = base.get("tests")
    head_tests = head.get("tests")
    if not isinstance(base_tests, list):
        raise ValueError("base manifest 'tests' is not a list")
    head_set = set(head_tests) if isinstance(head_tests, list) else set()
    for t in base_tests:
        if t not in head_set:
            out.append(("file", f"designated test file removed: {t}", t))
    return out


def unjustified(changes: list, justification, base_justification) -> list:
    """The subset of ``changes`` the justification text does not excuse."""
    if not changes:
        return []
    if justification is None:
        return changes
    if base_justification is not None and justification == base_justification:
        return changes                       # an unchanged note justifies nothing new
    return [c for c in changes if c[2] not in justification]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--justification", required=True)
    ap.add_argument("--base-justification")
    a = ap.parse_args(argv)
    try:
        base = json.loads(Path(a.base).read_text())
        head = json.loads(Path(a.head).read_text())
        if not isinstance(base, dict) or not isinstance(head, dict):
            raise ValueError("a manifest is not a JSON object")
        changes = drops(base, head)
    except (OSError, ValueError) as exc:
        print(f"manifest_guard: INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    jp = Path(a.justification)
    just = jp.read_text() if jp.is_file() else None
    bj = Path(a.base_justification) if a.base_justification else None
    base_just = bj.read_text() if bj is not None and bj.is_file() else None
    bad = unjustified(changes, just, base_just)
    for kind, detail, token in changes:
        print(f"{'UNJUSTIFIED' if (kind, detail, token) in bad else 'justified  '} {detail}")
    if bad:
        print(f"manifest_guard: FAIL -- {len(bad)} unjustified drop(s); {a.justification} must be committed in this "
              f"change and mention each verbatim: " + " | ".join(t for _k, _d, t in bad), file=sys.stderr)
        return 1
    print("manifest_guard: OK -- no count dropped and no designated file removed without justification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
