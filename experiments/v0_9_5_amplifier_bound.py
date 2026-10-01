"""V0.9.5-A13: the canonicalisation amplifier bound -- is the A13 work unit honest in WALL TIME?

A13 meters canonicalisation in passes over the graph (``atoms + 2 x bonds`` units per refinement round and per
block-path candidate; ``smartchem.category._CanonicalMeter``), bounds one call at ``_MAX_CANONICAL_CALL_WORK`` units
and refuses graphs over ``_MAX_CANONICAL_ATOMS`` before any work.  A budget in a unit is only as honest as the unit's
wall-time rate is FLAT: if some shape runs many times slower per unit than another, the budget admits that many times
the wall time on it.  So this harness runs HOSTILE witness shapes -- each built to stress one axis (long refinement,
deep search, wide cells, many bonds, big block-path candidate loops, many automorphisms) -- through the live
``Molecule.canonical`` (uncached, its charge recorded by the charge channel itself), and reports per shape:

    atoms, bonds, outcome (ok / refused), units charged, wall seconds, units per second.

From the SLOWEST admitted rate it states the worst cases the bounds imply:

    per call  = _MAX_CANONICAL_CALL_WORK / slowest rate        (one canonical() call, refused at the ceiling)
    per load  = VerificationBudget().canonical_work / slowest rate   (canonical work alone, one load at the default)

and it times the A13 refusals themselves (each must be fast: refused BEFORE the work): the bracket H count, the parser
atom ceiling ("C" * 4000 / "C" * 100000 through resolve_identity), the canonical() atom ceiling on a built graph, and a
block-path call whose up-front charge is over the call ceiling.

Run:  .venv/bin/python experiments/v0_9_5_amplifier_bound.py [--json out.json] [--quick]
Timings on a shared box are +-30%; rates are taken from calls that ran >= 0.05 s.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import smartchem.category as cat  # noqa: E402
from smartchem.category import Bond, CanonicalBoundExceeded, Molecule  # noqa: E402
from smartchem.verification import VerificationBudget, _recording_canonical_work  # noqa: E402


# ---------------------------------------------------------------------------------------------------------- shapes
def _mol(atoms: list, edges) -> Molecule:
    return Molecule(tuple(atoms), frozenset(Bond(min(i, j), max(i, j), o) for i, j, o in edges))


def chain(k: int) -> Molecule:
    """n-alkane C_k H_(2k+2): refinement walks inward one step per round (~k/2 rounds of O(n)), then ~k searches."""
    atoms, edges = ["C"] * k, [(i, i + 1, 1) for i in range(k - 1)]
    for c in range(k):
        for _ in range(4 - (1 if c in (0, k - 1) else 2) if k > 1 else 4):
            atoms.append("H")
            edges.append((c, len(atoms) - 1, 1))
    return _mol(atoms, edges)


def star(k: int) -> Molecule:
    """C bonded to k H: one wide cell, k-1 nested individualisations (the S16 depth witness)."""
    return _mol(["C"] + ["H"] * k, [(0, i, 1) for i in range(1, k + 1)])


def ring(n: int, hydrogens: bool) -> Molecule:
    atoms, edges = ["C"] * n, [(i, (i + 1) % n, 1) for i in range(n)]
    if hydrogens:
        for c in range(n):
            for _ in range(2):
                atoms.append("H")
                edges.append((c, len(atoms) - 1, 1))
    return _mol(atoms, edges)


def grid(k: int) -> Molecule:
    edges = []
    for r in range(k):
        for c in range(k):
            if c + 1 < k:
                edges.append((r * k + c, r * k + c + 1, 1))
            if r + 1 < k:
                edges.append((r * k + c, (r + 1) * k + c, 1))
    return _mol(["C"] * (k * k), edges)


def bintree(depth: int) -> Molecule:
    """A complete binary tree: |Aut| = 2**(2**depth - 1) -- the automorphism-pruning stress."""
    atoms, edges, level = ["C"], [], [0]
    for _ in range(depth):
        nxt = []
        for p in level:
            for _ in range(2):
                atoms.append("C")
                edges.append((p, len(atoms) - 1, 1))
                nxt.append(len(atoms) - 1)
        level = nxt
    return _mol(atoms, edges)


def dense(n: int, m: int, seed: int = 13) -> Molecule:
    """A connected random graph with many bonds per atom: each pass is dominated by its 2 x bonds term."""
    rng = random.Random(seed)
    edges = {(i, i + 1) for i in range(n - 1)}
    while len(edges) < m:
        a, b = rng.randrange(n), rng.randrange(n)
        if a != b:
            edges.add((min(a, b), max(a, b)))
    return _mol(["C"] * n, [(a, b, 1) for a, b in edges])


def regular_circulant(n: int, offsets: tuple) -> Molecule:
    """Vertex-transitive (every vertex alike): refinement splits nothing; the search must individualise."""
    edges = {(min(i, (i + d) % n), max(i, (i + d) % n)) for i in range(n) for d in offsets}
    return _mol(["C"] * n, [(a, b, 1) for a, b in edges])


def theta(paths: int, length: int) -> Molecule:
    """Two hubs joined by ``paths`` disjoint carbon paths of ``length`` bonds: S_paths symmetry the search must walk
    (twin pruning cannot: path starts are not twins) with every node's refinement running the length of a path --
    the shape built to reach the per-call work ceiling under the atom ceiling."""
    atoms, edges = ["C", "C"], []
    for _ in range(paths):
        prev = 0
        for _ in range(length - 1):
            atoms.append("C")
            edges.append((prev, len(atoms) - 1, 1))
            prev = len(atoms) - 1
        edges.append((prev, 1, 1))
    return _mol(atoms, edges)


def block_witness(k: int, ch2: int) -> Molecule:
    """O-[C(F)(Cl)]_k-[CH2]_ch2-NH2 (H on O): every backbone position WL-distinct, each CH2 / NH2 a 2-block of H
    twins -- the block path's candidate loop, 2**(ch2+1) candidates over a graph that grows with k."""
    atoms, edges, prev = ["O"], [], 0
    for _ in range(k):
        c = len(atoms)
        atoms += ["C", "F", "Cl"]
        edges += [(prev, c, 1), (c, c + 1, 1), (c, c + 2, 1)]
        prev = c
    for _ in range(ch2):
        c = len(atoms)
        atoms += ["C", "H", "H"]
        edges += [(prev, c, 1), (c, c + 1, 1), (c, c + 2, 1)]
        prev = c
    nn = len(atoms)
    atoms += ["N", "H", "H", "H"]
    edges += [(prev, nn, 1), (nn, nn + 1, 1), (nn, nn + 2, 1), (0, nn + 3, 1)]
    return _mol(atoms, edges)


def shapes(quick: bool) -> list:
    out = [
        ("chain C100", chain(100)), ("chain C200", chain(200)), ("chain C340 (1,022 atoms)", chain(340)),
        ("star H400", star(400)), ("star H1000", star(1000)), ("star H1023 (1,024 atoms)", star(1023)),
        ("ring C320 bare", ring(320, False)), ("ring C300 + H (900 atoms)", ring(300, True)),
        ("grid 30x30", grid(30)), ("bintree depth 9 (1,023 atoms)", bintree(9)),
        ("dense n=200 m=5000", dense(200, 5000)), ("dense n=1000 m=20000", dense(1000, 20000)),
        ("circulant n=500 (1,2,5)", regular_circulant(500, (1, 2, 5))),
        ("block k=20 ch2=13", block_witness(20, 13)), ("block k=100 ch2=13", block_witness(100, 13)),
        ("block k=300 ch2=13 (over the call ceiling up front)", block_witness(300, 13)),
        ("theta 16 paths x 16", theta(16, 16)), ("theta 32 paths x 32 (994 atoms)", theta(32, 32)),
    ]
    if quick:
        out = [row for row in out if "1,0" not in row[0] and "k=300" not in row[0] and "m=20000" not in row[0]]
    return out


# ------------------------------------------------------------------------------------------------------- measuring
def run_shape(label: str, m: Molecule) -> dict:
    t = time.perf_counter()
    with _recording_canonical_work() as frame:
        try:
            Molecule.canonical.__wrapped__(m)          # live body, uncached
            outcome = "ok"
        except CanonicalBoundExceeded as exc:
            outcome = f"refused: {str(exc)[:96]}"
    dt = time.perf_counter() - t
    row = {"shape": label, "atoms": len(m.atoms), "bonds": len(m.bonds), "outcome": outcome,
           "units": frame.total, "seconds": round(dt, 4),
           "units_per_s": round(frame.total / dt) if dt > 0 else None}
    print(f"  {label:52} atoms={row['atoms']:5} bonds={row['bonds']:6} units={row['units']:>12,} "
          f"{dt:8.3f}s {(row['units_per_s'] or 0) / 1e6:6.2f} M/s  {outcome[:60]}", flush=True)
    return row


def refusals() -> dict:
    """Each A13 refusal must come BEFORE the work it refuses: wall time of the refusal itself."""
    from smartchem.identity_parse import IdentityParseError, resolve_identity
    from smartchem.smiles import SmilesError, parse_smiles

    out = {}

    def clock(name, fn):
        t = time.perf_counter()
        try:
            fn()
            res = "ANSWERED (not refused)"
        except (SmilesError, IdentityParseError, CanonicalBoundExceeded) as exc:
            res = f"{type(exc).__name__}: {str(exc)[:90]}"
        out[name] = {"seconds": round(time.perf_counter() - t, 4), "result": res}
        print(f"  [refusal] {name:44} {out[name]['seconds']:8.4f}s  {res[:100]}", flush=True)

    clock("parse [CH1234567]", lambda: parse_smiles("[CH1234567]"))
    clock("parse [CH123456789]", lambda: parse_smiles("[CH123456789]"))
    for k in (1000, 4000, 100_000):
        clock(f"resolve_identity C*{k}", lambda k=k: resolve_identity("C" * k))
    clock("canonical() star H100000 (built graph)", lambda: Molecule.canonical.__wrapped__(star(100_000)))
    clock("canonical() block k=300 ch2=13 (charge up front)", lambda: Molecule.canonical.__wrapped__(
        block_witness(300, 13)))
    return out


def load_probe(hostile: Molecule, label: str) -> dict:
    """ONE load whose replay step carries ``hostile`` (re-forged by the keyless forger of tests/test_v0_9_5_loader_laws.py
    -- every derived key and the whole-body digest recomputed): the load's wall time, and how many times the call
    ceiling refused during it.  A refused canonicalisation is not cached, so a load that meets the same over-ceiling
    graph at several call sites pays the ceiling at each -- this counts them."""
    import copy
    import importlib.util

    from smartchem.service import build_recompile_request, load_response, response_to_payload, run_compilation

    spec = importlib.util.spec_from_file_location("_a13_loader_laws", REPO / "tests" / "test_v0_9_5_loader_laws.py")
    laws = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_a13_loader_laws", laws)
    spec.loader.exec_module(laws)
    thick = response_to_payload(run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man")))
    forged = copy.deepcopy(thick)
    forged["ranked_route_dossiers"][0]["replay_payload"][0]["reactants"][0] = {
        "atoms": list(hostile.atoms), "bonds": sorted([b.i, b.j, b.order] for b in hostile.bonds),
        "charge": hostile.charge, "state": hostile.state}
    forged = laws._reforge(forged)
    ceiling_refusals = [0]
    live = cat._CanonicalMeter.spend

    def counting(self, units):
        try:
            return live(self, units)
        except CanonicalBoundExceeded:
            ceiling_refusals[0] += 1
            raise
    cat._CanonicalMeter.spend = counting
    t = time.perf_counter()
    try:
        load_response(forged)
        outcome = "LOADED"
    except Exception as exc:  # noqa: BLE001 -- the refusal class is the recorded fact
        outcome = f"{type(exc).__name__}: {str(exc)[:110]}"
    finally:
        cat._CanonicalMeter.spend = live
    row = {"carried": label, "atoms": len(hostile.atoms), "load_seconds": round(time.perf_counter() - t, 2),
           "call_ceiling_refusals": ceiling_refusals[0], "outcome": outcome}
    print(f"  [load] {row}", flush=True)
    return row


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--json", default=None)
    ap.add_argument("--quick", action="store_true", help="skip the ~1,000-atom shapes")
    args = ap.parse_args(argv)
    print(f"[proof] measuring smartchem.category from {cat.__file__}", flush=True)
    budget = VerificationBudget().canonical_work
    results = {"argv": argv, "smartchem_file": cat.__file__, "atom_ceiling": cat._MAX_CANONICAL_ATOMS,
               "call_work_ceiling": cat._MAX_CANONICAL_CALL_WORK, "default_canonical_work": budget}
    print(f"atom ceiling {cat._MAX_CANONICAL_ATOMS:,}; call ceiling {cat._MAX_CANONICAL_CALL_WORK:,} units; "
          f"default canonical_work {budget:,} units", flush=True)
    rows = [run_shape(label, m) for label, m in shapes(args.quick)]
    timed = [r for r in rows if r["outcome"] == "ok" and r["seconds"] >= 0.05 and r["units_per_s"]]
    slowest = min(timed, key=lambda r: r["units_per_s"])
    fastest = max(timed, key=lambda r: r["units_per_s"])
    results["shapes"] = rows
    results["slowest_rate"] = {"shape": slowest["shape"], "units_per_s": slowest["units_per_s"]}
    results["fastest_rate"] = {"shape": fastest["shape"], "units_per_s": fastest["units_per_s"]}
    results["rate_spread"] = round(fastest["units_per_s"] / slowest["units_per_s"], 2)
    results["worst_case_per_call_s"] = round(cat._MAX_CANONICAL_CALL_WORK / slowest["units_per_s"], 1)
    results["worst_case_per_load_canonical_s"] = round(budget / slowest["units_per_s"], 1)
    results["refusals"] = refusals()
    if not args.quick:
        results["load_probe"] = load_probe(theta(32, 32), "theta 32 paths x 32 in a replay reactant")
    print(json.dumps({k: v for k, v in results.items() if k not in ("shapes", "refusals")}, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1, sort_keys=True))
    late = [name for name, r in results["refusals"].items() if r["seconds"] > 5.0 or "ANSWERED" in r["result"]]
    if late:
        print(f"FAIL: refusals not prompt / not refused: {late}")
    return 1 if late else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
