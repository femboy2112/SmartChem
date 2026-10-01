"""0.9.5 repeatable invariant stress harness (mission Part 19).

Seeded and configurable; every invariant is a NAMED check with a pass / fail / pending / vacuous count.  A check whose
0.9.5 API is not on the tree yet (feature-detected) is recorded PENDING -- never pass.  Exit status is non-zero iff any
invariant has a FAIL (PENDING/VACUOUS do not fail the run but are printed loudly and appear in the results file).

Invariants
  roundtrip_byte_identity      serialize -> deserialize -> serialize is byte-identical (canonical JSON text)
  compile_replay_acceptance    an honest compile is accepted by response_from_payload, result_digest preserved
  cross_process_result_digest  same request -> identical result_digest in K fresh processes (random PYTHONHASHSEED)
  profile_search_noninterference  none/research-lab/poor-man/custom => same semantic_digest, candidate digests,
                               search receipt, ranked route digests
  kekule_identity_law          graph-surgery Kekule alternates -> one stock.structure_key   (PENDING if absent)
  receipt_consistency          len(candidates) <= result_limit ; results_returned == len(candidates of the kind)
  cache_on_off_identity        enumeration cache on/off => byte-identical accepted results (PENDING if absent)
  policy_only_promised_changes advisory / pinned / verified-admission accept identically; thin under a canonical
                               requirement is refused (policy half PENDING if VerificationPolicy is absent)
Resource series (long-lived process): RSS per iteration + least-squares slope, cache stats (feature-detected),
latency tails (p50/p90/p99/max) per operation.

Every run is HEAVY on a shared 7 GB box: run under the shared flock, e.g.
    flock <heavy.lock> timeout 1800 python experiments/v0_9_5_stress.py --label BASELINE
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXP = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))  # this tree, not the venv's stale editable install

# cheap "methyl acetate family": (target smiles, helper reagents, stock materials)
FAMILY = (
    ("CC(=O)OC", ("water",), ("CO", "CC(=O)O")),
    ("CC(=O)OCC", ("water",), ("CCO", "CC(=O)O")),
    ("CCC(=O)OC", ("water",), ("CO", "CCC(=O)O")),
    ("CCC(=O)OCC", ("water",), ("CCO", "CCC(=O)O")),
    ("CC(=O)OCCC", ("water",), ("CCCO", "CC(=O)O")),
)
# constitutional Kekule-flip candidates (parsed, then graph-surgery on alternating 6-rings)
KEKULE_SMILES = ("Cc1ccccc1C", "Oc1ccccc1O", "OC(=O)c1ccccc1O", "COC(=O)c1ccccc1O", "CC(=O)Oc1ccccc1C(=O)O",
                 "Cc1ccccc1O", "OC(=O)c1ccccc1C(=O)O", "Nc1ccccc1O", "c1ccc2ccccc2c1")


class Invariant:
    def __init__(self, name: str, doc: str):
        self.name, self.doc = name, doc
        self.passed = self.failed = self.pending = self.vacuous = 0
        self.failures: list[str] = []
        self.note = ""

    def ok(self, cond: bool, detail: str = "") -> bool:
        if cond:
            self.passed += 1
        else:
            self.failed += 1
            if len(self.failures) < 5:
                self.failures.append(detail)
        return cond

    def mark_pending(self, why: str) -> None:
        self.pending += 1
        self.note = why

    def mark_vacuous(self, why: str) -> None:
        self.vacuous += 1
        self.note = why

    def status(self) -> str:
        if self.failed:
            return "FAIL"
        if self.passed:
            return "PASS" + (" (+pending)" if self.pending else "")
        return "PENDING" if self.pending else ("VACUOUS" if self.vacuous else "NOT-RUN")


def _rss_kb() -> int:
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * (os.sysconf("SC_PAGE_SIZE") // 1024)


def _slope(ys: list[float]) -> float:
    """Least-squares slope of ys against 0..n-1 (units per iteration)."""
    n = len(ys)
    if n < 3:
        return 0.0
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return sum((i - mx) * (y - my) for i, y in enumerate(ys)) / den


def _tails(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    s = sorted(xs)
    q = lambda p: s[min(len(s) - 1, int(p * len(s)))]  # noqa: E731
    return {"n": len(s), "p50": round(statistics.median(s), 4), "p90": round(q(0.90), 4),
            "p99": round(q(0.99), 4), "max": round(s[-1], 4)}


def _cj(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# ------------------------------------------------------------------------------------------ feature detection
def _verification():
    try:
        import smartchem.verification as v
        return v
    except ImportError:
        return None


def _cache_toggle():
    """The enumeration-cache on/off switch, wherever the 0.9.5 layer put it; None if absent."""
    import smartchem.service as svc
    for mod in (_verification(), svc):
        fn = getattr(mod, "set_enumeration_cache_enabled", None) if mod is not None else None
        if callable(fn):
            return fn
    return None


def _cache_size() -> object:
    v = _verification()
    cache = getattr(v, "ENUMERATION_CACHE", None) if v is not None else None
    if cache is None:
        return None
    for attr in ("stats", "info", "cache_info"):
        fn = getattr(cache, attr, None)
        if callable(fn):
            try:
                s = fn()
                return s._asdict() if hasattr(s, "_asdict") else (s if isinstance(s, (dict, int, float, str))
                                                                  else repr(s))
            except Exception as e:  # noqa: BLE001
                return f"stats-error:{type(e).__name__}"
    return {a: getattr(cache, a) for a in ("hits", "misses", "size", "weight") if hasattr(cache, a)} or repr(cache)


def _canonical_lru() -> dict:
    from smartchem.category import Molecule
    ci = Molecule.canonical.cache_info()
    return {"hits": ci.hits, "misses": ci.misses, "currsize": ci.currsize, "maxsize": ci.maxsize}


# ------------------------------------------------------------------------------------------------- request specs
def _request(spec: dict):
    from smartchem.service import TransformGrammar, build_recompile_request
    kw = dict(helper_reagents=tuple(spec["helpers"]), stock_materials=tuple(spec["stock"]),
              max_depth=spec.get("max_depth"), max_routes=spec.get("max_routes"))
    if spec.get("dag"):
        from smartchem.process_constraints import ProcessBounds
        kw["grammar"] = TransformGrammar.CAPPED_SCISSION_CONVERGENT
        kw["process"] = ProcessBounds.of(max_total_minutes=30.0)
    if spec.get("profile"):
        kw["capability_profile"] = spec["profile"]
    kw = {k: v for k, v in kw.items() if v is not None}
    return build_recompile_request(spec["target"], **kw)


def _profiles() -> dict:
    from smartchem.capability.presets import custom
    return {"none": None, "research-lab": "research-lab", "poor-man": "poor-man",
            "custom": custom(profile_id="stress-custom-bench")}


def _random_spec(rng: random.Random, allow_dag: bool) -> dict:
    tgt, helpers, stock = rng.choice(FAMILY)
    return {"target": "smiles:" + tgt, "helpers": list(helpers), "stock": list(stock),
            "max_depth": rng.choice((1, 2)), "max_routes": rng.choice((1, 2, 5, 100)),
            "dag": allow_dag and rng.random() < 0.5}


# -------------------------------------------------------------------------------------------- Kekule surgery
def _kekule_alternates(mol):
    """Flip every alternating (1,2,1,2,1,2) 6-ring's bond orders -- the other Kekule form, same graph."""
    from smartchem.category import Bond, Molecule
    order = {frozenset((b.i, b.j)): b.order for b in mol.bonds}
    adj: dict[int, list[int]] = {}
    for e in order:
        i, j = tuple(e)
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    flipped: set[frozenset] = set()

    def ring_from(start: int, cur: int, path: list[int]):
        if len(path) == 6:
            return path if start in adj[cur] else None
        for nxt in adj[cur]:
            if nxt > start and nxt not in path:
                r = ring_from(start, nxt, path + [nxt])
                if r:
                    return r
        return None

    for s in sorted(adj):
        r = ring_from(s, s, [s])
        if not r:
            continue
        es = [frozenset((r[k], r[(k + 1) % 6])) for k in range(6)]
        os_ = [order[e] for e in es]
        if os_ in ([1, 2] * 3, [2, 1] * 3) and not (set(es) & flipped):
            flipped |= set(es)
    if not flipped:
        return None
    new = frozenset(Bond(b.i, b.j, (3 - b.order) if frozenset((b.i, b.j)) in flipped else b.order)
                    for b in mol.bonds)
    return Molecule(atoms=mol.atoms, bonds=new, charge=mol.charge, state=mol.state)


# --------------------------------------------------------------------------------------------- worker (child)
def _worker(spec_json: str) -> None:
    from smartchem.service import run_compilation
    resp = run_compilation(_request(json.loads(spec_json)))
    print("@@WORKER@@" + json.dumps({"result_digest": resp.result_digest,
                                     "semantic_digest": resp.request.semantic_digest,
                                     "hashseed": os.environ.get("PYTHONHASHSEED")}))


def _spawn_worker(spec: dict, hashseed: int) -> dict | None:
    env = dict(os.environ, PYTHONHASHSEED=str(hashseed), PYTHONPATH=str(REPO) + os.pathsep + os.environ.get(
        "PYTHONPATH", ""))
    cp = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", json.dumps(spec)],
                        capture_output=True, text=True, env=env, timeout=900)
    for line in cp.stdout.splitlines():
        if line.startswith("@@WORKER@@"):
            return json.loads(line[len("@@WORKER@@"):])
    return None


# ------------------------------------------------------------------------------------------------- the checks
def _load(payload, **kw):
    from smartchem.service import response_from_payload
    return response_from_payload(json.loads(_cj(payload)), **kw)


def check_iteration(spec: dict, inv: dict, lat: dict) -> None:
    from smartchem.service import response_to_payload, run_compilation
    req = _request(spec)
    t = time.perf_counter()
    resp = run_compilation(req)
    lat["compile"].append(time.perf_counter() - t)

    t = time.perf_counter()
    payload = response_to_payload(resp)
    lat["serialize"].append(time.perf_counter() - t)

    # receipt_consistency -- on the LIVE compile (the producer side)
    ir = resp.compilation_ir
    tag = f"{spec['target']} d={spec.get('max_depth')} r={spec.get('max_routes')} dag={spec.get('dag')}"
    if ir is None:
        inv["receipt_consistency"].mark_vacuous("a compile produced no IR (refusal/invalid) -- nothing to check")
    else:
        rc = ir.search_receipt
        kind = "DAG" if spec.get("dag") else "ROUTE"
        cands = [c for c in ir.candidates if c.candidate_kind == kind]
        lim = rc.result_limit
        inv["receipt_consistency"].ok(lim is None or len(ir.candidates) <= lim,
                                      f"{tag}: {len(ir.candidates)} candidates > result_limit {lim}")
        inv["receipt_consistency"].ok(rc.results_returned == len(cands),
                                      f"{tag}: results_returned {rc.results_returned} != {len(cands)} {kind} candidates")
        if spec.get("max_routes") is not None and not spec.get("dag"):
            inv["receipt_consistency"].ok(len(cands) <= spec["max_routes"],
                                          f"{tag}: {len(cands)} routes > requested max_routes {spec['max_routes']}")
        inv["receipt_consistency"].ok(rc.result_limit == (spec.get("max_routes") or 100),
                                      f"{tag}: receipt result_limit {rc.result_limit} != request bound")

    # compile_replay_acceptance
    t = time.perf_counter()
    try:
        loaded = _load(payload)
        lat["load"].append(time.perf_counter() - t)
        inv["compile_replay_acceptance"].ok(loaded.result_digest == resp.result_digest,
                                            f"{tag}: loaded result_digest differs from compiled")
    except Exception as e:  # noqa: BLE001
        lat["load"].append(time.perf_counter() - t)
        inv["compile_replay_acceptance"].ok(False, f"{tag}: honest payload REFUSED {type(e).__name__}: {str(e)[:120]}")
        return

    # roundtrip_byte_identity (canonical JSON text; also survives an actual text hop)
    t = time.perf_counter()
    text = _cj(payload)
    again = _cj(response_to_payload(_load(json.loads(text))))
    lat["roundtrip"].append(time.perf_counter() - t)
    inv["roundtrip_byte_identity"].ok(text == again, f"{tag}: re-serialised payload differs "
                                      f"({len(text)} vs {len(again)} bytes)")

    # policy_only_promised_changes -- legacy kwargs half (always available)
    pol = inv["policy_only_promised_changes"]
    variants = {"pinned": dict(expected_request_digest=req.semantic_digest),
                "verified-admission": dict(require_verified_admission=True)}
    # None == pinned to NOT_REQUESTED, which is exactly what a no-profile compile carries
    variants["pinned+question"] = dict(expected_request_digest=req.semantic_digest,
                                       expected_capability_question_digest=resp.request.capability_question_digest)
    for vname, kw in variants.items():
        try:
            r2 = _load(payload, **kw)
            pol.ok(r2.result_digest == loaded.result_digest, f"{tag}: {vname} accepted a DIFFERENT result_digest")
        except Exception as e:  # noqa: BLE001
            pol.ok(False, f"{tag}: {vname} REFUSED an honest payload: {type(e).__name__}: {str(e)[:120]}")

    v = _verification()
    policy_cls = getattr(v, "VerificationPolicy", None) if v is not None else None
    load_response = getattr(v, "load_response", None) if v is not None else None
    if policy_cls is None or load_response is None:
        pol.mark_pending("smartchem.verification.VerificationPolicy/load_response absent: the 'thin under a canonical "
                         "requirement is refused' and policy-object half is PENDING (legacy-kwarg half ran)")
    else:
        thin = response_to_payload(resp, include_replay=False)
        for pname, mk in (("advisory", lambda: policy_cls.advisory()), ("canonical", lambda: policy_cls.canonical())):
            try:
                vl = load_response(json.loads(_cj(payload)), mk())
                pol.ok(vl.response.result_digest == loaded.result_digest, f"{tag}: policy {pname} moved result_digest")
            except Exception as e:  # noqa: BLE001
                pol.ok(False, f"{tag}: policy {pname} REFUSED an honest thick payload: {type(e).__name__}")
        try:
            load_response(json.loads(_cj(thin)), policy_cls.canonical())
            pol.ok(False, f"{tag}: THIN payload ACCEPTED under a canonical requirement")
        except Exception as e:  # noqa: BLE001
            pol.ok(type(e).__name__ != "AttributeError", f"{tag}: thin refusal was a bug ({type(e).__name__})")

    # cache_on_off_identity
    toggle = _cache_toggle()
    co = inv["cache_on_off_identity"]
    if toggle is None:
        co.mark_pending("set_enumeration_cache_enabled absent on this tree (pre-0.9.5 layer)")
    else:
        outs = []
        for state in (True, False, True):
            toggle(state)
            try:
                outs.append(_cj(response_to_payload(_load(payload))))
            finally:
                toggle(True)
        co.ok(outs[0] == outs[1] == outs[2], f"{tag}: cache on/off/on produced different accepted results")


def check_profiles(spec: dict, inv: dict) -> None:
    from smartchem.service import run_compilation
    ni = inv["profile_search_noninterference"]
    seen = {}
    for pname, prof in _profiles().items():
        resp = run_compilation(_request({**spec, "profile": prof}))
        ir = resp.compilation_ir
        seen[pname] = (resp.request.semantic_digest,
                       tuple(sorted(c.candidate_digest for c in ir.candidates)) if ir else None,
                       repr(ir.search_receipt) if ir else None,
                       tuple(d.route_digest for d in resp.ranked_route_dossiers))
    base = seen["none"]
    for pname, got in seen.items():
        for i, what in enumerate(("semantic_digest", "candidate digests", "search receipt", "ranked route digests")):
            ni.ok(got[i] == base[i], f"{spec['target']}: profile {pname} moved {what}")


def check_kekule(inv: dict, rng: random.Random) -> None:
    k = inv["kekule_identity_law"]
    try:
        from smartchem.experiment import stock
    except ImportError:
        k.mark_pending("smartchem.experiment.stock unimportable")
        return
    key_fn = getattr(stock, "structure_key", None)
    if key_fn is None:
        k.mark_pending("smartchem.experiment.stock.structure_key absent (S7 not landed): the law cannot be checked")
        return
    from smartchem.smiles import parse_smiles
    for smi in rng.sample(KEKULE_SMILES, len(KEKULE_SMILES)):
        m = parse_smiles(smi)
        alt = _kekule_alternates(m)
        if alt is None or alt == m:
            k.mark_vacuous(f"no alternating 6-ring to flip in {smi} -- surgery control is vacuous for it")
            continue
        k.ok(key_fn(m) == key_fn(alt), f"{smi}: Kekule alternate got a different structure_key")
    # distinctness half: o/m/p-xylene must NOT merge
    keys = {key_fn(parse_smiles(s)) for s in ("Cc1ccccc1C", "Cc1cccc(C)c1", "Cc1ccc(C)cc1")}
    k.ok(len(keys) == 3, "o/m/p-xylene structure_keys merged")


def check_cross_process(spec: dict, inv: dict, k: int, rng: random.Random) -> None:
    from smartchem.service import run_compilation
    xp = inv["cross_process_result_digest"]
    here = run_compilation(_request(spec)).result_digest
    for _ in range(k):
        seed = rng.randrange(0, 4294967295)
        got = _spawn_worker(spec, seed)
        if got is None:
            xp.ok(False, f"{spec['target']}: worker (PYTHONHASHSEED={seed}) produced no digest")
            continue
        xp.ok(got["result_digest"] == here, f"{spec['target']}: NONDETERMINISTIC result_digest under "
              f"PYTHONHASHSEED={seed}: {got['result_digest'][:12]} != {here[:12]}  <-- release bug")


# ------------------------------------------------------------------------------------------------------- main
def run(a) -> dict:
    rng = random.Random(a.seed)
    names = [
        ("roundtrip_byte_identity", "serialize->deserialize->serialize byte identity"),
        ("compile_replay_acceptance", "honest compile -> load accepted, result_digest preserved"),
        ("cross_process_result_digest", f"same request -> identical result_digest across {a.processes} fresh processes"),
        ("profile_search_noninterference", "none/research-lab/poor-man/custom leave the search untouched"),
        ("kekule_identity_law", "Kekule alternates -> one structure_key; constitutional isomers distinct"),
        ("receipt_consistency", "len(candidates) <= result_limit; results_returned == len(candidates)"),
        ("cache_on_off_identity", "enumeration cache on/off byte-identical accepted results"),
        ("policy_only_promised_changes", "policy changes only the promised trust/refusal behaviour"),
    ]
    inv = {n: Invariant(n, d) for n, d in names}
    lat = {k: [] for k in ("compile", "serialize", "load", "roundtrip")}
    rss, cache_series, lru_series = [], [], []
    t_start = time.time()

    specs = [_random_spec(rng, allow_dag=(i % a.dag_every == 0)) for i in range(a.iterations)]
    for i, spec in enumerate(specs):
        check_iteration(spec, inv, lat)
        if a.profile_every and i % a.profile_every == 0:
            check_profiles({**spec, "dag": False}, inv)
        rss.append(_rss_kb())
        cache_series.append(_cache_size())
        lru_series.append(_canonical_lru()["currsize"])
        if (i + 1) % 10 == 0:
            print(f"  iter {i + 1}/{a.iterations}  rss {rss[-1] / 1024:.0f} MB  elapsed {time.time() - t_start:.0f}s",
                  flush=True)

    # cross-process determinism: two cheap specs (+ an optional third the caller names)
    for spec in ({"target": "smiles:CC(=O)OC", "helpers": ["water"], "stock": ["CO", "CC(=O)O"], "max_depth": 2},
                 {"target": "smiles:CC(=O)OCC", "helpers": ["water"], "stock": ["CCO", "CC(=O)O"], "max_depth": 2}):
        check_cross_process(spec, inv, a.processes, rng)
    check_kekule(inv, rng)

    # a few isopentyl iterations (heavy: 27 routes)
    iso_rss = []
    for _ in range(a.isopentyl_iters):
        spec = {"target": "isopentyl acetate", "helpers": ["water", "acetic acid"], "stock": ["isopentyl alcohol"]}
        check_iteration(spec, inv, lat)
        iso_rss.append(_rss_kb())
        if a.isopentyl_xproc:
            check_cross_process(spec, inv, 1, rng)

    # resource series: slope over the post-warmup 80% of the cheap-family loop
    tail = rss[len(rss) // 5:]
    resources = {
        "rss_kb_first": rss[0] if rss else None, "rss_kb_last": rss[-1] if rss else None,
        "rss_kb_max": max(rss) if rss else None,
        "rss_slope_kb_per_iteration_post_warmup": round(_slope([float(x) for x in tail]), 2),
        "rss_slope_kb_per_iteration_all": round(_slope([float(x) for x in rss]), 2),
        "rss_after_isopentyl_kb": iso_rss,
        "canonical_lru_currsize_first_last_max": [lru_series[0], lru_series[-1], max(lru_series)] if lru_series else None,
        "enumeration_cache_series_first_last": [cache_series[0], cache_series[-1]] if cache_series else None,
        "latency_seconds": {k: _tails(v) for k, v in lat.items()},
    }
    return {"label": a.label, "seed": a.seed, "iterations": a.iterations, "processes": a.processes,
            "isopentyl_iters": a.isopentyl_iters, "dag_every": a.dag_every, "profile_every": a.profile_every,
            "python": platform.python_version(), "wall_seconds": round(time.time() - t_start, 1),
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "invariants": {n: {"status": v.status(), "pass": v.passed, "fail": v.failed, "pending": v.pending,
                               "vacuous": v.vacuous, "note": v.note, "failures": v.failures, "doc": v.doc}
                           for n, v in inv.items()},
            "resources": resources, "specs_sample": specs[:5]}


def _head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _md(res: dict) -> str:
    import smartchem
    L = [f"# 0.9.5 stress -- {res['label']}", "",
         f"- tree `{_head()}`, smartchem `{getattr(smartchem, '__version__', '?')}`, python {res['python']}",
         f"- config: seed {res['seed']}, {res['iterations']} cheap-family iterations (methyl-acetate family, DAG every "
         f"{res['dag_every']}th, profile noninterference every {res['profile_every']}th), {res['processes']} fresh "
         f"processes per cross-process spec, {res['isopentyl_iters']} isopentyl iteration(s); wall {res['wall_seconds']}s",
         f"- generated {res['generated_utc']}",
         "", "| invariant | status | pass | fail | pending | vacuous |", "|---|---|---:|---:|---:|---:|"]
    for n, v in res["invariants"].items():
        L.append(f"| {n} | {v['status']} | {v['pass']} | {v['fail']} | {v['pending']} | {v['vacuous']} |")
    L.append("")
    for n, v in res["invariants"].items():
        if v["note"] or v["failures"]:
            L.append(f"- **{n}**: {v['note']}" + ("".join(f"\n  - FAILURE: {f}" for f in v["failures"])))
    r = res["resources"]
    L += ["", "## Resources (long-lived process)", "",
          f"- RSS first/last/max: {r['rss_kb_first'] / 1024:.1f} / {r['rss_kb_last'] / 1024:.1f} / "
          f"{r['rss_kb_max'] / 1024:.1f} MB",
          f"- **RSS slope (post-warmup 80%): {r['rss_slope_kb_per_iteration_post_warmup']} KB/iteration** "
          f"(all points: {r['rss_slope_kb_per_iteration_all']} KB/iteration)",
          f"- RSS after each isopentyl iteration (KB): {r['rss_after_isopentyl_kb']}",
          f"- Molecule.canonical lru currsize first/last/max: {r['canonical_lru_currsize_first_last_max']} (maxsize 8192)",
          f"- enumeration cache stats first/last: {r['enumeration_cache_series_first_last']} (null == layer absent)",
          "", "Latency (seconds):", "", "| op | n | p50 | p90 | p99 | max |", "|---|---:|---:|---:|---:|---:|"]
    for k, t in r["latency_seconds"].items():
        L.append(f"| {k} | {t.get('n')} | {t.get('p50')} | {t.get('p90')} | {t.get('p99')} | {t.get('max')} |")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--label", default="ADHOC")
    ap.add_argument("--seed", type=int, default=20260929)
    ap.add_argument("--iterations", type=int, default=30)
    ap.add_argument("--processes", type=int, default=3, help="K fresh processes per cross-process spec")
    ap.add_argument("--isopentyl-iters", type=int, default=1)
    ap.add_argument("--isopentyl-xproc", action="store_true", help="also run isopentyl through 1 fresh worker (slow)")
    ap.add_argument("--dag-every", type=int, default=6, help="every Nth cheap iteration uses the DAG grammar")
    ap.add_argument("--profile-every", type=int, default=6, help="profile-noninterference every Nth iteration (0=off)")
    ap.add_argument("--out-dir", type=Path, default=EXP)
    ap.add_argument("--worker")
    a = ap.parse_args()
    if a.worker:
        _worker(a.worker)
        return 0
    res = run(a)
    stem = a.out_dir / f"RESULTS_v0_9_5_stress_{a.label}"
    stem.parent.mkdir(parents=True, exist_ok=True)   # never lose a finished run to a missing --out-dir
    stem.with_suffix(".json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    stem.with_suffix(".md").write_text(_md(res))
    print(_md(res))
    print(f"wrote {stem}.md/.json")
    return 1 if any(v["fail"] for v in res["invariants"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
