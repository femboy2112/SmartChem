"""0.9.5 verification-performance experiment (the committed "before/after" yardstick).

What it measures: ``response_from_payload`` (the verifier / loader) on a FROZEN payload set that the harness builds
itself from real requests (never committed as blobs; cached under ``--cache-dir``), per payload:

  * COLD  -- a fresh subprocess per run (process-level caches empty), first load only.  Declared N: ``--cold-n`` (3).
  * WARM  -- repeated loads inside ONE process after one discarded cold load.  Declared N: ``--warm-n`` (5).
  * median / p90 / worst (worst == max; with N<=5 p90 is the nearest-rank value and is close to the worst),
    peak RSS (``ru_maxrss`` of the child, MB), and the terminal STATUS of every run.
  * FEATURE-DETECTED 0.9.5 layer: if ``smartchem.verification`` exposes ``load_response`` the loads go through it and
    the receipt's work counters are recorded; if it exposes ``ENUMERATION_CACHE`` its hit/miss stats are recorded;
    a load refused by ``VerificationBudgetExceeded`` is recorded as ``REFUSED(VerificationBudgetExceeded)`` WITH its
    time -- for the hostile payload that refusal is the success condition, not an error.
  * On a tree without the layer (the 0.9.0a1 BASELINE) the layer fields read ``absent``.

Usage (heavy: EVERY run goes under the shared flock -- export SMARTCHEM_PERF_LOCK=<lockfile> and each child takes it;
the hostile cold load alone is ~2 min each):
    python experiments/v0_9_5_verification_performance.py --label BASELINE
    python experiments/v0_9_5_verification_performance.py --label AFTER
    python experiments/v0_9_5_verification_performance.py --compare experiments/RESULTS_..._BASELINE.json \\
                                                                    experiments/RESULTS_..._AFTER.json
Internal modes (one payload / one measurement per process): ``--build NAME``, ``--child PATH``.

Timings on a shared box are +-30%; the ratio table is only as good as the box was quiet -- results record ``loadavg``.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXP = Path(__file__).resolve().parent
DEFAULT_CACHE = Path(os.environ.get("SMARTCHEM_PERF_CACHE", "/tmp/smartchem_v095_perf_payloads"))
LEGACY_FIXTURE = REPO / "tests" / "fixtures" / "v08" / "response_isopentyl_acetate.json"
CHILD_TIMEOUT_S = 1500

# (name, description, heavy?)  -- ``heavy`` payloads get the cold/warm counts trimmed only if --quick is passed.
PAYLOADS = (
    ("a_tiny_linear", "smiles:CC(=O)OC linear, max_depth=2, water, stock CO/CC(=O)O"),
    ("b1_isopentyl_noprofile", "isopentyl acetate thick 27-route, no capability profile"),
    ("b2_isopentyl_fitbench", "isopentyl acetate thick 27-route + isopentyl_capability_fit_bench()"),
    ("c1_methyl_acetate_dag", "methyl acetate CAPPED_SCISSION_CONVERGENT DAG, max_total_minutes=30"),
    ("c2_isopentyl_dag", "isopentyl acetate CAPPED_SCISSION_CONVERGENT DAG, ProcessBounds.quick()"),
    ("d_diels_alder", "Diels-Alder control C1CC=CCC1, certified-route-v07"),
    ("e_legacy_v08_isopentyl", "real v0.8 fixture response_isopentyl_acetate.json (legacy read leg)"),
    ("f_hostile2_45", "hostile large target: 45-heavy-atom wax ester, 6 helper reagents, default bounds (C7-1)"),
)


# --------------------------------------------------------------------------------------------- payload building
def _build_request(name: str):
    from smartchem.service import InputKind, TransformGrammar, build_recompile_request
    if name == "a_tiny_linear":
        return build_recompile_request("smiles:CC(=O)OC", helper_reagents=("water",),
                                       stock_materials=("CO", "CC(=O)O"), max_depth=2)
    if name == "b1_isopentyl_noprofile":
        return build_recompile_request("isopentyl acetate", helper_reagents=("water", "acetic acid"),
                                       stock_materials=("isopentyl alcohol",))
    if name == "b2_isopentyl_fitbench":
        from smartchem.capability.presets import isopentyl_capability_fit_bench
        return build_recompile_request("isopentyl acetate", helper_reagents=("water", "acetic acid"),
                                       stock_materials=("isopentyl alcohol",),
                                       capability_profile=isopentyl_capability_fit_bench())
    if name == "c1_methyl_acetate_dag":
        from smartchem.process_constraints import ProcessBounds
        return build_recompile_request("smiles:CC(=O)OC", max_depth=2,
                                       grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
                                       helper_reagents=("water", "acetic acid"),
                                       process=ProcessBounds.of(max_total_minutes=30.0))
    if name == "c2_isopentyl_dag":
        from smartchem.process_constraints import ProcessBounds
        return build_recompile_request("isopentyl acetate", helper_reagents=("water", "acetic acid"),
                                       stock_materials=("isopentyl alcohol",),
                                       grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
                                       process=ProcessBounds.quick())
    if name == "d_diels_alder":
        return build_recompile_request("C1CC=CCC1", input_kind=InputKind.SMILES, helper_reagents=(),
                                       stock_materials=("C=CC=C", "C=C"), algebra_profile="certified-route-v07")
    if name == "f_hostile2_45":
        # Lane B's f_hostile2_45, verbatim: n=45 heavy atoms; acyl (k C incl. carbonyl) + O + O(=) + alkyl (m C).
        n = 45
        k = (n - 2) // 2 + 1
        m = n - 2 - k
        smi = "C" * (k - 1) + "C(=O)O" + "C" * m
        return build_recompile_request(
            smi, input_kind=InputKind.SMILES, max_depth=1,
            helper_reagents=("O", "CC(=O)O", "CO", "CCO", "N", "C=O"),
            stock_materials=("C" * (k - 1) + "C(=O)O", "C" * m + "O"))
    raise SystemExit(f"unknown payload {name}")


def _build_one(name: str, out: Path) -> None:
    from smartchem.service import response_to_payload, run_compilation
    t = time.perf_counter()
    resp = run_compilation(_build_request(name))
    dt = time.perf_counter() - t
    out.write_text(json.dumps(response_to_payload(resp), sort_keys=True))
    print(f"built {name} compile_s={dt:.1f} exit={resp.exit_code} routes={len(resp.ranked_route_dossiers)} "
          f"dags={len(resp.ranked_dag_dossiers)} bytes={out.stat().st_size}", flush=True)


def _payload_path(name: str, cache: Path) -> Path:
    if name == "e_legacy_v08_isopentyl":
        return LEGACY_FIXTURE
    return cache / f"{name}.json"


def _ensure_payload(name: str, cache: Path, rebuild: bool) -> Path:
    path = _payload_path(name, cache)
    if path.exists() and (not rebuild or path == LEGACY_FIXTURE):   # the real v0.8 fixture is read, never rebuilt
        return path
    cache.mkdir(parents=True, exist_ok=True)
    print(f"[build] {name} ...", flush=True)
    cmd, to = _locked([sys.executable, str(Path(__file__).resolve()), "--build", name, "--build-out", str(path)])
    subprocess.run(cmd, check=True, env=_child_env(), timeout=to)
    return path


def _locked(cmd: list[str]) -> tuple[list[str], int | None]:
    """Per-subprocess shared-box lock: if SMARTCHEM_PERF_LOCK names a lock file every build/measure child runs under
    ``flock <file> timeout N`` (kinder than holding the box for the whole run).  Timing is taken INSIDE the child, so
    lock-wait never enters a sample.  Returns (cmd, parent-side timeout -- None when queueing on a lock)."""
    lock = os.environ.get("SMARTCHEM_PERF_LOCK")
    if not lock:
        return cmd, CHILD_TIMEOUT_S
    return ["flock", lock, "timeout", str(CHILD_TIMEOUT_S), *cmd], None


def _child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    return env


# ------------------------------------------------------------------------------------------------ child (measure)
def _layer_probe():
    """Feature-detect the 0.9.5 verification layer.  Returns (module_or_None, info dict of what it exposes)."""
    try:
        import smartchem.verification as v
    except ImportError:
        return None, {"present": False}
    return v, {"present": True, "load_response": hasattr(v, "load_response"),
               "enumeration_cache": hasattr(v, "ENUMERATION_CACHE"),
               "budget": hasattr(v, "VerificationBudgetExceeded")}


def _cache_stats(v) -> object:
    cache = getattr(v, "ENUMERATION_CACHE", None) if v is not None else None
    if cache is None:
        return "absent"
    for attr in ("stats", "info", "cache_info"):
        fn = getattr(cache, attr, None)
        if callable(fn):
            try:
                s = fn()
                return s._asdict() if hasattr(s, "_asdict") else (s if isinstance(s, (dict, list, str, int, float))
                                                                  else repr(s))
            except Exception as e:  # noqa: BLE001 -- a stats accessor must never sink a measurement
                return f"stats-error:{type(e).__name__}"
    out = {a: getattr(cache, a) for a in ("hits", "misses", "size", "weight") if hasattr(cache, a)}
    return out or repr(cache)


def _work(receipt) -> object:
    work = getattr(receipt, "work", None)
    if work is None:
        return None
    for f in ("as_dict", "to_dict", "_asdict"):
        fn = getattr(work, f, None)
        if callable(fn):
            return fn()
    try:
        import dataclasses
        return dataclasses.asdict(work)
    except TypeError:
        return work if isinstance(work, (dict, list, str, int, float)) else repr(work)


def _child(path: str, reps: int) -> None:
    t0 = time.perf_counter()
    import smartchem.service as svc
    v, layer = _layer_probe()
    t_import = time.perf_counter() - t0
    raw = Path(path).read_text()
    load = getattr(v, "load_response", None) if v is not None else None
    entry = "verification.load_response" if load is not None else "service.response_from_payload"
    runs, receipt = [], None
    for _ in range(reps):
        payload = json.loads(raw)
        t = time.perf_counter()
        try:
            res = load(payload) if load is not None else svc.response_from_payload(payload)
            status = "ok"
            receipt = getattr(res, "receipt", receipt)
        except Exception as e:  # noqa: BLE001 -- refusal IS a recorded outcome
            status = f"REFUSED({type(e).__name__})"
            if type(e).__name__ == "VerificationBudgetExceeded":
                receipt = None
        runs.append({"seconds": time.perf_counter() - t, "status": status})
    print("@@CHILD@@" + json.dumps({
        "runs": runs, "import_seconds": t_import, "entry": entry, "layer": layer,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "cache_stats": _cache_stats(v), "receipt_work": _work(receipt) if receipt is not None else None,
        "receipt_facets": (None if receipt is None else {
            k: str(getattr(receipt, k)) for k in ("schema_generation", "transport_mode", "reexecuted",
                                                  "replay_rederived_routes", "replay_rederived_dags")
            if hasattr(receipt, k)}),
    }), flush=True)


def _run_child(path: Path, reps: int) -> dict:
    t = time.perf_counter()
    cmd, to = _locked([sys.executable, str(Path(__file__).resolve()), "--child", str(path), "--reps", str(reps)])
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, env=_child_env(), timeout=to)
    except subprocess.TimeoutExpired:
        return {"runs": [{"seconds": time.perf_counter() - t, "status": "TIMEOUT"}], "peak_rss_mb": None}
    for line in cp.stdout.splitlines():
        if line.startswith("@@CHILD@@"):
            return json.loads(line[len("@@CHILD@@"):])
    return {"runs": [{"seconds": time.perf_counter() - t, "status": f"CHILD-FAILED rc={cp.returncode}: "
                      + cp.stderr.strip()[-200:]}], "peak_rss_mb": None}


# --------------------------------------------------------------------------------------------------- statistics
def _summ(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    s = sorted(xs)
    p90 = s[min(len(s) - 1, max(0, -(-9 * len(s) // 10) - 1))]   # nearest-rank
    return {"n": len(s), "median": statistics.median(s), "p90": p90, "worst": s[-1], "best": s[0]}


def _measure(name: str, desc: str, path: Path, cold_n: int, warm_n: int) -> dict:
    print(f"[measure] {name}: cold x{cold_n} (fresh procs), warm x{warm_n} (one proc) ...", flush=True)
    cold_children = [_run_child(path, 1) for _ in range(cold_n)]
    warm_child = _run_child(path, 1 + warm_n)               # rep 0 = discarded cold, reps 1.. = WARM
    cold_runs = [c["runs"][0] for c in cold_children]
    warm_runs = warm_child["runs"][1:]
    rec = {
        "payload": name, "description": desc, "bytes": path.stat().st_size, "path_kind": "fixture" if
        name.startswith("e_") else "built-cache",
        "cold": {**_summ([r["seconds"] for r in cold_runs]), "statuses": [r["status"] for r in cold_runs],
                 "samples": [round(r["seconds"], 3) for r in cold_runs]},
        "warm": {**_summ([r["seconds"] for r in warm_runs]), "statuses": [r["status"] for r in warm_runs],
                 "samples": [round(r["seconds"], 3) for r in warm_runs]},
        "peak_rss_mb": max([c.get("peak_rss_mb") or 0 for c in cold_children] + [warm_child.get("peak_rss_mb") or 0]),
        "import_seconds": (warm_child.get("import_seconds")),
        "entry": warm_child.get("entry"), "layer": warm_child.get("layer"),
        "cache_stats_after_warm_child": warm_child.get("cache_stats"),
        "receipt_work": warm_child.get("receipt_work") or next(
            (c.get("receipt_work") for c in cold_children if c.get("receipt_work")), None),
        "receipt_facets": warm_child.get("receipt_facets"),
    }
    print(f"          cold med {rec['cold'].get('median', float('nan')):.2f}s {set(rec['cold']['statuses'])}  "
          f"warm med {rec['warm'].get('median', float('nan')):.2f}s  rss {rec['peak_rss_mb']:.0f}MB", flush=True)
    return rec


# ------------------------------------------------------------------------------------------------ report / compare
def _md(res: dict) -> str:
    L = [f"# 0.9.5 verification performance -- {res['label']}", "",
         f"- tree commit: `{res['git_head']}`; smartchem `{res['smartchem_version']}`; python {res['python']}",
         f"- layer (smartchem.verification): `{res['layer']}`",
         f"- declared runs: COLD n={res['cold_n']} (fresh subprocess each), WARM n={res['warm_n']} "
         f"(one process, after 1 discarded cold load); p90 = nearest-rank; worst = max",
         f"- box: loadavg at start {res['loadavg_start']}, at end {res['loadavg_end']} (timings on a shared box: +-30%)",
         f"- wall: {res['wall_seconds']:.0f}s; generated {res['generated_utc']}", "",
         "| payload | bytes | cold med | cold p90 | cold worst | warm med | warm p90 | warm worst | peak RSS MB | "
         "cold status |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in res["payloads"]:
        c, w = r["cold"], r["warm"]
        f = lambda d, k: f"{d[k]:.2f}" if k in d else "-"  # noqa: E731
        L.append(f"| {r['payload']} | {r['bytes']:,} | {f(c, 'median')} | {f(c, 'p90')} | {f(c, 'worst')} | "
                 f"{f(w, 'median')} | {f(w, 'p90')} | {f(w, 'worst')} | {r['peak_rss_mb']:.0f} | "
                 f"{'/'.join(sorted(set(c['statuses'])))} |")
    L += ["", "## Samples (seconds) and 0.9.5-layer facts", ""]
    for r in res["payloads"]:
        L.append(f"- **{r['payload']}** ({r['description']}): cold {r['cold']['samples']}, warm {r['warm']['samples']}; "
                 f"entry `{r['entry']}`; warm statuses {sorted(set(r['warm']['statuses']))}; "
                 f"cache stats {r['cache_stats_after_warm_child']}; receipt work {r['receipt_work']}; "
                 f"receipt facets {r['receipt_facets']}")
    return "\n".join(L) + "\n"


def _compare(a_path: str, b_path: str) -> None:
    a, b = (json.loads(Path(p).read_text()) for p in (a_path, b_path))
    bm = {r["payload"]: r for r in b["payloads"]}
    print(f"ratio table  {a['label']} -> {b['label']}   (AFTER/BEFORE; <1 is faster; REFUSED rows are the "
          f"success condition for the hostile payload)")
    print(f"{'payload':26s} {'cold before':>11s} {'cold after':>11s} {'ratio':>6s} {'warm before':>11s} "
          f"{'warm after':>11s} {'ratio':>6s} {'rss b/a MB':>12s}  after-status")
    for r in a["payloads"]:
        o = bm.get(r["payload"])
        if o is None:
            continue
        cm = lambda x: x["cold"].get("median")  # noqa: E731
        wm = lambda x: x["warm"].get("median")  # noqa: E731
        ratio = lambda p, q: f"{q / p:6.2f}" if p and q else "     -"  # noqa: E731
        print(f"{r['payload']:26s} {cm(r):11.2f} {cm(o):11.2f} {ratio(cm(r), cm(o))} {wm(r):11.2f} {wm(o):11.2f} "
              f"{ratio(wm(r), wm(o))} {r['peak_rss_mb']:5.0f}/{o['peak_rss_mb']:<5.0f}  "
              f"{'/'.join(sorted(set(o['cold']['statuses'])))}")


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              timeout=20).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--label")
    ap.add_argument("--cold-n", type=int, default=3)
    ap.add_argument("--warm-n", type=int, default=5)
    ap.add_argument("--only", nargs="*", help="payload names to run (default all)")
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=EXP)
    ap.add_argument("--compare", nargs=2, metavar=("BASELINE_JSON", "AFTER_JSON"))
    ap.add_argument("--build")
    ap.add_argument("--build-out", type=Path)
    ap.add_argument("--child")
    ap.add_argument("--reps", type=int, default=1)
    a = ap.parse_args()
    if a.compare:
        _compare(*a.compare)
        return 0
    if a.build:
        _build_one(a.build, a.build_out)
        return 0
    if a.child:
        _child(a.child, a.reps)
        return 0
    if not a.label:
        ap.error("--label is required for a measurement run")
    t0 = time.time()
    la0 = os.getloadavg()
    sys.path.insert(0, str(REPO))   # so the parent probes THIS tree, not the venv's stale editable install
    layer = _layer_probe()[1]
    names = a.only or [n for n, _ in PAYLOADS]
    recs = []
    for name, desc in PAYLOADS:
        if name not in names:
            continue
        path = _ensure_payload(name, a.cache_dir, a.rebuild)
        recs.append(_measure(name, desc, path, a.cold_n, a.warm_n))
    import smartchem
    res = {"label": a.label, "git_head": _git_head(), "smartchem_version": getattr(smartchem, "__version__", "?"),
           "python": platform.python_version(), "layer": layer, "cold_n": a.cold_n, "warm_n": a.warm_n,
           "loadavg_start": [round(x, 2) for x in la0], "loadavg_end": [round(x, 2) for x in os.getloadavg()],
           "wall_seconds": time.time() - t0, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "payloads": recs}
    stem = a.out_dir / f"RESULTS_v0_9_5_verification_performance_{a.label}"
    stem.parent.mkdir(parents=True, exist_ok=True)   # never lose a finished measurement to a missing --out-dir
    stem.with_suffix(".json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    stem.with_suffix(".md").write_text(_md(res))
    print(f"wrote {stem}.md/.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
