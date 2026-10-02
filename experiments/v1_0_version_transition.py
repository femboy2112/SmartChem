"""V1.0-VERSION-TRANSITION-01: prove what a PACKAGE-ONLY version bump is allowed to move, and nothing else.

COMPATIBILITY.md section 2.2 + section 9 declare the transition law in prose: ``result_digest`` binds the producing
``tool_version`` and the implementation digest binds ``__version__``, so a version bump moves EXACTLY those, while the
request's ``digest`` / ``semantic_digest``, the route digests, the verdicts, the readiness tiers, the capability
assessments, the schema ids and the search candidate set/order all stay put.  This harness turns that declaration
into a field-by-field differential: it fingerprints the FULL canonical request+response payload of a representative
fast corpus, plus the implementation digest and the CLI ``--version`` banner, and classifies every changed field as
EXPECTED (a declared move) or UNEXPECTED.  Unexpected movement MUST be empty.

The expected move-set is DECLARED HERE, before any bump, never read back from a blessed baseline:

    EXPECTED TO MOVE   any ``tool_version`` field, any ``result_digest`` field, the implementation digest, the
                       CLI ``--version`` banner.
    EXPECTED INVARIANT everything else.

Wall-clock provenance (``fetched_at``) is stripped before comparison so clock drift can never masquerade as version
drift; a determinism control (capture the SAME tree twice, require identical) proves nothing else is non-deterministic.

Workflow for the real 0.9.5a1 -> 1.0.0rc1 transition:
    .venv/bin/python experiments/v1_0_version_transition.py --capture pre.json     # at 0.9.5a1
    .venv/bin/python experiments/v1_0_version_transition.py --capture pre2.json    # at 0.9.5a1 (control)
    # ... diff pre.json pre2.json -> must be IDENTICAL (determinism control) ...
    # ... edit smartchem/__init__.py: __version__ = "1.0.0rc1" ...
    .venv/bin/python experiments/v1_0_version_transition.py --capture post.json    # at 1.0.0rc1
    .venv/bin/python experiments/v1_0_version_transition.py --diff pre.json post.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

STRIP_KEYS = {"fetched_at"}  # wall-clock provenance, NOT in any digest; non-deterministic, never compared


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k not in STRIP_KEYS}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def _fast_corpus():
    """The baseline corpus, fast cases only (Algorithm: relocate, don't reinvent). Covers routes, poor-man and
    research-lab profiles, incomplete, invalid, target-already-available, decompile and a process-bounded DAG --
    every field class the transition law touches. The slow isopentyl family adds no new field STRUCTURE."""
    from experiments.v0_9_5_baseline_freeze import _corpus

    return [row for row in _corpus() if row[1] == "fast"]


def capture() -> dict:
    """The full, wall-clock-stripped fingerprint of the current source tree."""
    import smartchem
    from smartchem.program import _compiler_implementation_digest
    from smartchem.service import (
        build_decompile_request,
        build_recompile_request,
        request_to_payload,
        response_to_payload,
        run_compilation,
    )

    cases: dict[str, dict] = {}
    for cid, _cost, builder, target, kwargs in _fast_corpus():
        try:
            if builder == "recompile":
                req = build_recompile_request(target, **kwargs)
            elif builder == "decompile":
                req = build_decompile_request(target, **kwargs)
            else:  # pragma: no cover - corpus only has these two builders
                raise ValueError(f"unknown builder {builder!r}")
            resp = run_compilation(req)
            cases[cid] = {
                "request_payload": _strip(request_to_payload(req)),
                "response_payload": _strip(response_to_payload(resp)),
                "exit_code": resp.exit_code,
            }
        except Exception as exc:  # noqa: BLE001 -- a refusal CLASS is itself an invariant fact
            cases[cid] = {"refused": {"exc": type(exc).__name__, "msg": str(exc)[:240]}}

    return {
        "cases": cases,
        "_global": {
            "implementation_digest": _compiler_implementation_digest(),
            "cli_version_banner": f"smartchem {smartchem.__version__}",
            "package_version": smartchem.__version__,  # recorded; it is the INDEPENDENT variable, not a result
        },
    }


VERSION_BOUND_KEYS = {"tool_version", "result_digest"}  # the ONLY payload fields a version bump is allowed to move
INVARIANT_GOLDEN = REPO / "docs" / "research" / "V1_0_VERSION_INDEPENDENT_FINGERPRINT.json"


def _strip_version_bound(obj):
    if isinstance(obj, dict):
        return {k: _strip_version_bound(v) for k, v in obj.items() if k not in VERSION_BOUND_KEYS}
    if isinstance(obj, list):
        return [_strip_version_bound(v) for v in obj]
    return obj


def fingerprint_invariant() -> dict:
    """The VERSION-INDEPENDENT fingerprint: each case's request+response payload with the two version-bound fields
    (``tool_version``, ``result_digest``) stripped, hashed to a single sha.  This projection is identical at
    0.9.5a1 and at any 1.x version -- so a committed golden of it is a durable gate: it fires the instant a
    SEMANTIC field (a verdict, a route digest, a readiness tier, a schema id) moves, and stays silent for a pure
    version bump.  It also records, per case, that a tool-version-bound field is PRESENT and carries the live
    version, so the gate cannot be satisfied by a tree that simply dropped the version binding."""
    import hashlib

    import smartchem

    full = capture()
    ver = smartchem.__version__
    out: dict[str, dict] = {}
    for cid, rec in full["cases"].items():
        if "refused" in rec:
            out[cid] = {"refused": rec["refused"]}
            continue
        inv = _strip_version_bound({"request_payload": rec["request_payload"],
                                    "response_payload": rec["response_payload"],
                                    "exit_code": rec["exit_code"]})
        blob = json.dumps(inv, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        rd = rec["response_payload"].get("result_digest")
        tv = rec["response_payload"].get("compilation_ir", {}).get("tool_version") if isinstance(
            rec["response_payload"].get("compilation_ir"), dict) else None
        out[cid] = {
            "invariant_sha": hashlib.sha256(blob.encode()).hexdigest(),
            "tool_version_carries_live": tv == ver,
            "has_result_digest": isinstance(rd, str) and len(rd) == 64,
        }
    return {"cases": out}


def _flatten(obj, prefix="") -> dict[str, object]:
    flat: dict[str, object] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            flat.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flat.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        flat[prefix] = obj
    return flat


def _is_expected_move(key: str) -> bool:
    last = key.split(".")[-1].split("[")[0]
    if last in ("tool_version", "result_digest"):
        return True
    if key in ("_global.implementation_digest", "_global.cli_version_banner", "_global.package_version"):
        return True
    return False


def diff(pre: dict, post: dict) -> int:
    fa, fb = _flatten(pre), _flatten(post)
    changed = [k for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]

    expected_moved, unexpected = [], []
    for k in changed:
        (expected_moved if _is_expected_move(k) else unexpected).append(k)

    print("=" * 100)
    print(f"VERSION TRANSITION  {pre['_global']['package_version']}  ->  {post['_global']['package_version']}")
    print("=" * 100)
    print(f"\nEXPECTED moves ({len(expected_moved)}):")
    for k in expected_moved:
        print(f"  MOVED  {k}")
    print(f"\nUNEXPECTED moves ({len(unexpected)})  -- MUST be zero:")
    for k in unexpected:
        print(f"  !!!!!  {k}: {fa.get(k)!r} -> {fb.get(k)!r}")

    # the bump must actually have taken effect (a vacuous no-op diff is not a proof)
    took = {
        "implementation_digest": fa.get("_global.implementation_digest") != fb.get("_global.implementation_digest"),
        "a tool_version": any(k.endswith("tool_version") for k in expected_moved),
        "a result_digest": any(k.split(".")[-1].split("[")[0] == "result_digest" for k in expected_moved),
    }
    print("\nbump-took-effect:")
    for name, ok in took.items():
        print(f"  {'YES' if ok else 'NO '}  {name} moved")

    ok = not unexpected and all(took.values())
    print("\n" + ("VERSION TRANSITION PROVEN: only the declared tool-version-bound fields moved."
                  if ok else "VERSION TRANSITION FAILED (see above)."))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--capture", metavar="OUT", help="fingerprint the current tree (full payloads) to OUT.json")
    g.add_argument("--diff", nargs=2, metavar=("PRE", "POST"), help="classify PRE->POST field movement")
    g.add_argument("--write-golden", action="store_true",
                   help="(re)freeze the version-INDEPENDENT fingerprint golden (only for a sanctioned semantic change)")
    g.add_argument("--check-golden", action="store_true",
                   help="recompute the version-independent fingerprint, diff against the golden, exit 1 on drift")
    args = ap.parse_args(argv)

    if args.capture:
        doc = capture()
        Path(args.capture).write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        print(f"captured {len(doc['cases'])} cases at {doc['_global']['package_version']} -> {args.capture}")
        return 0

    if args.write_golden:
        import smartchem

        INVARIANT_GOLDEN.write_text(
            json.dumps(fingerprint_invariant(), indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        print(f"wrote {INVARIANT_GOLDEN.relative_to(REPO)} (version-independent; captured at {smartchem.__version__})")
        return 0

    if args.check_golden:
        if not INVARIANT_GOLDEN.exists():
            print(f"ERROR: {INVARIANT_GOLDEN} missing; run --write-golden", file=sys.stderr)
            return 1
        frozen = json.loads(INVARIANT_GOLDEN.read_text())
        live = fingerprint_invariant()
        drift = [k for k in sorted(set(_flatten(frozen)) | set(_flatten(live)))
                 if _flatten(frozen).get(k) != _flatten(live).get(k)]
        if drift:
            print(f"VERSION-INDEPENDENT FINGERPRINT DRIFT ({len(drift)} key(s)):", file=sys.stderr)
            for k in drift:
                print(f"  {k}: {_flatten(frozen).get(k)!r} -> {_flatten(live).get(k)!r}", file=sys.stderr)
            return 1
        print("version-independent fingerprint: NO DRIFT (semantic content unmoved by the version bump)")
        return 0

    pre = json.loads(Path(args.diff[0]).read_text())
    post = json.loads(Path(args.diff[1]).read_text())
    return diff(pre, post)


if __name__ == "__main__":
    raise SystemExit(main())
