"""0.9.5 barrier A16 (transport-loader hardening): the committed measurements behind two loader constants, and the
type-confusion fuzz of every public wire-load entry point.

* ``verification._MAX_PAYLOAD_DEPTH`` (C8 F4, dict leg) -- the container nesting depth, in ``count_payload_nodes``'
  convention (the root container is depth 1; a scalar adds none), of every frozen honest payload: every JSON file under
  ``tests/fixtures`` (the real v0.8 fixtures, the CLI goldens, the fuzz repros, ...) and the request, thick and thin
  payload of every frozen service case (``v0_9_5_baseline_freeze._corpus``) and of the verification-performance
  payloads (``v0_9_5_verification_performance``: the fit bench, both DAGs, Diels-Alder, the C7-1 hostile).  The depth is
  computed HERE by an independent walk, not by the function under test.
* ``verification._DEFAULT_CAPABILITY_WORK`` (C8 F5) -- the receipt's ``capability_work`` for the four loads of every
  frozen answer (plain thick, pinned + verified-admission thick, plain thin, pinned re-execution), each under the
  DEFAULT policy budget, and of every real v0.8 fixture response; then (``--hostile-bottles N``) a hostile but
  schema-valid bench -- the fit bench's own bottles re-labelled to N distinct packages -- honestly compiled on the
  isopentyl 27-route recipe and loaded under the default: its refusal, its time to refusal, and the assessments run.
* ``--fuzz`` -- every public loader, fed a deterministic set of type confusions (every dict path to depth 4, list
  index 0, x 15 replacement values, plus key deletion); each outcome is ACCEPT, REFUSE (a ``ValueError``: the refusal
  class, ``MalformedPayloadError`` and ``VerificationBudgetExceeded`` included) or LEAK (anything else).  Target: 0 LEAK.

Run (heavy -- under the shared flock):
    PYTHONPATH=. .venv/bin/python experiments/v0_9_5_loader_bounds.py [--quick] [--hostile-bottles 1792] [--fuzz]
                                                                       [--json OUT.json]
``--quick`` skips the freeze corpus' SLOW cases and the perf payloads (the honest maxima need the full run).
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import math
import resource
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "experiments")):   # the package, and the frozen-corpus harnesses beside this file
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------------------------------- depth
def container_depth(payload: object) -> int:
    """Deepest container nesting (root container = 1, scalars add none): ``count_payload_nodes``' convention, walked
    independently here so the measurement does not trust the code it sizes."""
    best, stack = 0, [(payload, 1)]
    while stack:
        node, depth = stack.pop()
        children = node.values() if isinstance(node, dict) else node if isinstance(node, (list, tuple)) else None
        if children is None:
            continue
        best = max(best, depth)
        stack.extend((child, depth + 1) for child in children)
    return best


def fixture_depths() -> dict:
    out = {}
    for path in sorted((REPO / "tests" / "fixtures").rglob("*.json")):
        out[str(path.relative_to(REPO))] = container_depth(json.loads(path.read_text()))
    return out


# ---------------------------------------------------------------------------------------------- capability_work
def _loads(req, resp) -> dict:
    """capability_work (or the refusal) of the four loads of one answer, under the DEFAULT budget."""
    from smartchem.service import load_response, response_to_payload
    from smartchem.verification import VerificationPolicy

    thick = response_to_payload(resp)
    thin = response_to_payload(resp, include_replay=False)
    pins = dict(expected_request_digest=req.semantic_digest,
                expected_capability_question_digest=req.capability_question_digest)
    record = {"depth": {"request": container_depth(thick["request"]), "thick": container_depth(thick),
                        "thin": container_depth(thin)},
              "bottles": (0 if req.capability_profile is None else len(req.capability_profile.material_inventory))}
    for name, payload, policy in (
        ("plain_thick", thick, VerificationPolicy()),
        ("pinned_va_thick", thick, VerificationPolicy(require_verified_admission=True, **pins)),
        ("plain_thin", thin, VerificationPolicy()),
        ("pinned_reexec_thick", thick, VerificationPolicy(require_reexecution=True, **pins)),
    ):
        try:
            record[name] = load_response(copy.deepcopy(payload), policy).receipt.work.capability_work
        except ValueError as exc:
            record[name] = f"REFUSED {type(exc).__name__}: {str(exc)[:160]}"
    return record


def service_measurements(quick: bool) -> dict:
    import v0_9_5_baseline_freeze as freeze           # the frozen corpus itself, not a copy
    import v0_9_5_verification_performance as perf    # the perf payloads' own request builders
    from smartchem.service import build_decompile_request, build_recompile_request, run_compilation

    out = {}
    cases = [(f"freeze/{cid}", builder, target, kw) for cid, cost, builder, target, kw in freeze._corpus()
             if not (quick and cost == freeze.SLOW)]
    for cid, builder, target, kw in cases:
        t0 = time.time()
        build = build_recompile_request if builder == "recompile" else build_decompile_request
        try:
            req = build(target, **kw)
            resp = run_compilation(req)
        except ValueError as exc:                     # a refused build/compile (an honest refusal): nothing to load
            out[cid] = {"refused": type(exc).__name__}
            continue
        out[cid] = _loads(req, resp)
        print(f"  [load] {cid} ({time.time() - t0:.0f}s) {out[cid]}", flush=True)
    if not quick:
        for name in ("b2_isopentyl_fitbench", "c1_methyl_acetate_dag", "c2_isopentyl_dag", "d_diels_alder",
                     "f_hostile2_45"):
            t0 = time.time()
            req = perf._build_request(name)
            out[f"perf/{name}"] = _loads(req, run_compilation(req))
            print(f"  [load] perf/{name} ({time.time() - t0:.0f}s) {out[f'perf/{name}']}", flush=True)
    return out


def legacy_measurements() -> dict:
    from smartchem.service import load_response
    from smartchem.verification import VerificationPolicy

    out = {}
    for path in sorted((REPO / "tests" / "fixtures" / "v08").rglob("response_*.json")):
        if "schema_descriptor" in path.name:
            continue
        rel = str(path.relative_to(REPO))
        for name, policy in (("plain", VerificationPolicy()), ("va", VerificationPolicy(require_verified_admission=True))):
            try:
                out[f"{rel}:{name}"] = load_response(json.loads(path.read_text()), policy).receipt.work.capability_work
            except ValueError as exc:
                out[f"{rel}:{name}"] = f"REFUSED {type(exc).__name__}"
    return out


def ceiling_recursion_need() -> dict:
    """The ceiling's OTHER side: the least ``sys.setrecursionlimit`` under which a load of a payload nested exactly AT
    ``_MAX_PAYLOAD_DEPTH`` (a canonical-codec tuple chain in the capability profile -- the C8 F4 shape) finishes without
    ``RecursionError``, beside the same for the honest payload it was built from.  The ceiling must sit far under the
    interpreter's default limit, or a payload the walk admits could still crash a decoder."""
    from smartchem import verification as V
    from smartchem.service import build_recompile_request, load_response, response_to_payload, run_compilation

    honest = response_to_payload(run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2,
                                                                         capability_profile="poor-man")))

    def with_chain(levels: int) -> dict:
        payload = copy.deepcopy(honest)
        deep = node = {"type": "tuple", "items": []}
        for _ in range(levels):
            child = {"type": "tuple", "items": []}
            node["items"].append(child)
            node = child
        for field in payload["request"]["capability_profile"]["fields"]:
            if field[0] == "material_inventory":
                field[1] = deep
        return payload

    levels = 0
    while container_depth(with_chain(levels + 1)) <= V._MAX_PAYLOAD_DEPTH:
        levels += 1
    at_ceiling = with_chain(levels)

    def crashes(payload, limit: int) -> bool:
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(limit)
        try:
            load_response(copy.deepcopy(payload))
        except RecursionError:
            return True
        except ValueError:
            pass
        finally:
            sys.setrecursionlimit(old)
        return False

    def least(payload) -> int:
        lo, hi = 30, sys.getrecursionlimit()
        while lo < hi:
            mid = (lo + hi) // 2
            lo, hi = (mid + 1, hi) if crashes(payload, mid) else (lo, mid)
        return lo

    return {"ceiling": V._MAX_PAYLOAD_DEPTH, "at_ceiling_depth": container_depth(at_ceiling),
            "honest_depth": container_depth(honest), "default_recursion_limit": sys.getrecursionlimit(),
            "least_limit_honest": least(honest), "least_limit_at_ceiling": least(at_ceiling)}


def hostile_bench(bottles: int) -> dict:
    """The fit bench's bottles re-labelled into ``bottles`` distinct packages: schema-valid, honestly compiled (so every
    carried assessment re-derives), loaded under the default -- the C8 F5 shape (1,792 bottles x 27 dossiers)."""
    import smartchem.service as svc
    from smartchem.capability.presets import isopentyl_capability_fit_bench
    from smartchem.data import material_library
    from smartchem.service import build_recompile_request, load_response, response_to_payload, run_compilation
    from smartchem.verification import VerificationBudgetExceeded

    base = material_library.isopentyl_fully_declared_inventory()
    inventory = tuple(dataclasses.replace(m, material_id=f"{m.material_id}#{i}")
                      for i in range(math.ceil(bottles / len(base))) for m in base)[:bottles]
    req = build_recompile_request("isopentyl acetate", helper_reagents=("water", "acetic acid"),
                                  stock_materials=("isopentyl alcohol",),
                                  capability_profile=isopentyl_capability_fit_bench(material_inventory=inventory))
    t0 = time.time()
    resp = run_compilation(req)
    compile_s = time.time() - t0
    payload = response_to_payload(resp)
    calls = []
    real = svc.assess_capability

    def spy(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    svc.assess_capability = spy
    try:
        t1 = time.time()
        try:
            load_response(payload)
            verdict = "ACCEPTED"
        except VerificationBudgetExceeded as exc:
            verdict = f"REFUSED {exc.counter} consumed {exc.consumed} > limit {exc.limit}"
        load_s = time.time() - t1
    finally:
        svc.assess_capability = real
    return {"bottles": bottles, "dossiers": len(resp.ranked_route_dossiers), "compile_s": round(compile_s, 1),
            "producer_s_per_bottle_assessment_ms": round(1000 * compile_s / max(1, bottles * len(resp.ranked_route_dossiers)), 3),
            "default_load": verdict, "load_s_to_verdict": round(load_s, 1), "assessments_run": len(calls),
            "depth": container_depth(payload)}


# ---------------------------------------------------------------------------------------------------- fuzz
REPLACEMENTS = (None, 0, "", [], {}, True, 1.5, float("nan"), float("inf"), -1, 10 ** 30, "xxx", [None], {"x": None},
                [[[[]]]])
_DELETE = object()


def _paths(obj, prefix=(), depth=0, max_depth=4):
    if depth >= max_depth:
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield prefix + (key,)
            yield from _paths(value, prefix + (key,), depth + 1, max_depth)
    elif isinstance(obj, list) and obj:
        yield prefix + (0,)
        yield from _paths(obj[0], prefix + (0,), depth + 1, max_depth)


def mutations(payload, max_depth=4):
    """Every (path, value) confusion of ``payload``: each path x each replacement, and deletion of each dict key."""
    for path in _paths(payload, max_depth=max_depth):
        for value in REPLACEMENTS + (_DELETE,):
            mutated = copy.deepcopy(payload)
            parent = mutated
            for step in path[:-1]:
                parent = parent[step]
            if value is _DELETE:
                if not isinstance(parent, dict):
                    continue
                del parent[path[-1]]
            else:
                parent[path[-1]] = copy.deepcopy(value)
            yield path, value, mutated


def classify(call) -> str:
    try:
        call()
        return "ACCEPT"
    except ValueError:                                # the refusal class (MalformedPayloadError, budget, ...)
        return "REFUSE"
    except Exception as exc:  # noqa: BLE001 -- the class IS the measured fact
        return f"LEAK {type(exc).__name__}"


def entry_points() -> list:
    """(name, base payload, loader-of-payload, raw loader) for every public wire-load entry point -- the raw loader takes
    the argument a caller passes (a dict, or the TEXT for a text loader), for the top-level shape confusions."""
    import smartchem.compilation_ir as cir
    from smartchem.data.provider_snapshot import PROVIDER_SNAPSHOT_SCHEMA, ProviderSnapshot
    from smartchem.identity import identity_loss_from_payload, identity_loss_to_payload, stereo_loss
    from smartchem.process_constraints import ProcessBounds
    from smartchem.service import (
        TransformGrammar,
        affordability_entry_from_payload,
        build_recompile_request,
        deserialize_request,
        deserialize_response,
        load_response,
        load_response_text,
        provider_snapshot_from_payload,
        provider_snapshot_to_payload,
        ranked_dag_summary_from_payload,
        ranked_summary_from_payload,
        request_from_payload,
        response_from_payload,
        response_to_payload,
        run_compilation,
    )
    from smartchem.smiles import parse_smiles

    snap = ProviderSnapshot(PROVIDER_SNAPSHOT_SCHEMA, ("offline",), 1, "d" * 64, "2026-01-01T00:00:00Z", False)
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man"),
                           provider_snapshots=(snap,))
    wire = response_to_payload(resp)
    dag = response_to_payload(run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        helper_reagents=("water", "acetic acid"), process=ProcessBounds.of(max_total_minutes=30.0))))
    structure_ir = cir.ir_to_payload(cir.decompile_structure_to_ir(parse_smiles("CC"), reagents=(parse_smiles("O"),)))
    formula_ir = cir.ir_to_payload(cir.decompile_to_ir("H2O", ("H2", "O2")))
    water = parse_smiles("O")

    def recompile_formula(t):
        return cir.recompile_from_serialized(t, structure=water, reagents=())

    def on_text(loader):
        return lambda p: loader(json.dumps(p))

    rows = [
        ("load_response", wire, load_response),
        ("response_from_payload", wire, response_from_payload),
        ("deserialize_response", wire, deserialize_response),
        ("load_response_text", wire, load_response_text),
        ("request_from_payload", wire["request"], request_from_payload),
        ("deserialize_request", wire["request"], deserialize_request),
        ("ranked_summary_from_payload", wire["ranked_route_dossiers"][0], ranked_summary_from_payload),
        ("ranked_dag_summary_from_payload", dag["ranked_dag_dossiers"][0], ranked_dag_summary_from_payload),
        ("affordability_entry_from_payload", wire["affordability_frontier"][0], affordability_entry_from_payload),
        ("provider_snapshot_from_payload", provider_snapshot_to_payload(snap), provider_snapshot_from_payload),
        ("ir_from_payload", wire["compilation_ir"], cir.ir_from_payload),
        ("deserialize_ir", structure_ir, cir.deserialize_ir),
        ("identity_loss_from_payload", identity_loss_to_payload(stereo_loss("C[C@H](O)CC")), identity_loss_from_payload),
        ("recompile_structure_from_serialized", structure_ir, cir.recompile_structure_from_serialized),
        ("recompile_from_serialized", formula_ir, recompile_formula),
    ]
    text_loaders = {"deserialize_response", "load_response_text", "deserialize_request", "deserialize_ir",
                    "recompile_structure_from_serialized", "recompile_from_serialized"}
    return [(name, base, on_text(raw) if name in text_loaders else raw, raw) for name, base, raw in rows]


def fuzz(stride: int = 1) -> dict:
    """Outcome counts per entry point (``stride`` > 1 samples every stride-th mutation, deterministically)."""
    out = {}
    for name, base, load, raw in entry_points():
        assert classify(lambda b=base: load(copy.deepcopy(b))) == "ACCEPT", f"setup: the honest {name} payload must load"
        counts, leaks = Counter(), {}
        for top in (None, [], "x", 3, 1.5, True, b"{}", "[]", "null", "{}"):
            outcome = classify(lambda t=top: raw(t))
            counts[outcome] += 1
            if outcome.startswith("LEAK"):
                leaks.setdefault(outcome, ("<top-level>", repr(top)))
        for index, (path, value, mutated) in enumerate(mutations(base)):
            if index % stride:
                continue
            outcome = classify(lambda m=mutated: load(m))
            counts[outcome] += 1
            if outcome.startswith("LEAK"):
                leaks.setdefault(outcome, (path, "<delete>" if value is _DELETE else repr(value)[:20]))
        out[name] = {"counts": dict(sorted(counts.items())), "untyped_escapes": sum(
            n for k, n in counts.items() if k.startswith("LEAK")), "first_leak_of_each_class": leaks}
        print(f"  [fuzz] {name}: {out[name]['counts']}" + (f" LEAKS {leaks}" if leaks else ""), flush=True)
    return out


# ---------------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    resource.setrlimit(resource.RLIMIT_AS, (3 * 2 ** 30, 3 * 2 ** 30))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--hostile-bottles", type=int, default=0)
    ap.add_argument("--fuzz", action="store_true")
    ap.add_argument("--no-measure", action="store_true", help="skip the depth/capability measurements")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    import smartchem
    from smartchem import verification as V
    print(f"tree: {smartchem.__file__}", flush=True)
    # getattr: the fuzz also runs on a pre-A16 tree (the BEFORE count), which has neither constant
    results: dict = {"defaults": {"_MAX_PAYLOAD_DEPTH": getattr(V, "_MAX_PAYLOAD_DEPTH", "absent"),
                                  "_DEFAULT_CAPABILITY_WORK": getattr(V, "_DEFAULT_CAPABILITY_WORK", "absent")}}
    if not args.no_measure:
        results["fixture_depths"] = fixture_depths()
        results["service"] = service_measurements(args.quick)
        results["legacy_v08"] = legacy_measurements()
        depths = dict(results["fixture_depths"])
        works = {}
        for cid, rec in results["service"].items():
            for k, d in rec.get("depth", {}).items():
                depths[f"{cid}:{k}"] = d
            for k in ("plain_thick", "pinned_va_thick", "plain_thin", "pinned_reexec_thick"):
                if isinstance(rec.get(k), int):
                    works[f"{cid}:{k}"] = rec[k]
        works.update({k: v for k, v in results["legacy_v08"].items() if isinstance(v, int)})
        refused = sorted(f"{cid}:{k}" for cid, rec in results["service"].items() for k, v in rec.items()
                         if isinstance(v, str) and v.startswith("REFUSED"))
        # a budget refusal of an honest load is a false refusal; any other refusal must be one the baseline freeze
        # already records (the 0.8 thin law refuses the isopentyl THIN wire's PROCESS_SPECIFIED routes by design)
        budget_refused = [k for k in refused if "VerificationBudgetExceeded" in str(
            results["service"][k.rsplit(":", 1)[0]][k.rsplit(":", 1)[1]])]
        deepest = max(depths.items(), key=lambda kv: kv[1])
        busiest = max(works.items(), key=lambda kv: kv[1])
        results["summary"] = {"honest_max_depth": deepest, "honest_max_capability_work": busiest,
                              "payloads_measured": len(depths), "loads_measured": len(works),
                              "honest_loads_refused_by_a_budget": budget_refused,
                              "honest_loads_refused_otherwise": [k for k in refused if k not in budget_refused]}
        print(f"\nhonest max depth {deepest[1]} ({deepest[0]}) over {len(depths)} payloads")
        print(f"honest max capability_work {busiest[1]} ({busiest[0]}) over {len(works)} loads")
        print(f"honest loads refused by a budget under the default policy: {budget_refused or 'none'}")
        print(f"honest loads refused otherwise (must match the baseline freeze): "
              f"{[k for k in refused if k not in budget_refused] or 'none'}")
    if not args.no_measure:
        results["ceiling_recursion"] = ceiling_recursion_need()
        print(f"recursion need: {results['ceiling_recursion']}", flush=True)
    if args.hostile_bottles:
        results["hostile"] = hostile_bench(args.hostile_bottles)
        print(f"hostile bench: {results['hostile']}", flush=True)
    if args.fuzz:
        results["fuzz"] = fuzz()
        total = sum(r["untyped_escapes"] for r in results["fuzz"].values())
        print(f"\nfuzz: {sum(sum(r['counts'].values()) for r in results['fuzz'].values())} inputs over "
              f"{len(results['fuzz'])} entry points, UNTYPED ESCAPES {total}")
    if args.json:
        args.json.write_text(json.dumps(results, indent=1, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
