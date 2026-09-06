"""ROUND-13 item 3: does a `_canonical_cost`-derived proxy bound the resonance-canonicalisation runtime?

MEASURED ANSWER: no.  This harness REPRODUCES the refutation of the "cheap work-metered canonicaliser" (the
ROUND-13 recon's design (A), which proposed using ``category._canonical_cost`` as a per-placement work meter at the
``_min_constitution_placement`` layer to lift the ``_RESONANCE_MAX_HEAVY`` / ``_RESONANCE_MAX_MATCHINGS`` caps).

Run it: ``.venv/bin/python experiments/resonance_cost_proxy_probe.py`` (a few seconds; it deliberately grinds).

WHY THE PROXY FAILS (both directions, both branches -- reproduced below):

* ``category._canonical_cost`` is the NOMINAL candidate-permutation COUNT ``prod(block_size!)`` -- NOT a runtime.
  ``Molecule.canonical()`` has two regimes (``category._canonical_blocks``): a PERMUTATION branch when that count is
  <= ``_MAX_CANONICAL_CANDIDATES`` (50000), and an INDIVIDUALISATION branch (nauty-style, bounded by a leaf ceiling)
  otherwise.  ``_canonical_cost`` describes only the permutation branch's arithmetic.
* In the INDIVIDUALISATION branch it OVER-predicts wildly: real coronene (C24) has ``_canonical_cost`` ~1.2e23 yet
  canonicalises in ~4.6 ms/call -- so charging a placement its ``_canonical_cost`` would bail a FAST molecule.
* In the PERMUTATION branch it UNDER-predicts: each candidate's key comparison scales with molecule SIZE, so a
  30-atom placement with count 16384 takes ~300-540 ms, not the ~33 ms the count-at-2us/candidate model implies.
* Worst: the SLOW regime is asymmetric PERMUTATION-branch PAHs, and LEGIT ones out-cost the crafted grind.  Ordered by
  per-placement permutation cost: anthracene 4096 (~720 ms, a FIXTURE), pyrene 8192 (~1600 ms, legit), the crafted
  GRIND 16384 (~6.3 s), triphenylene 32768 (~6.7 s, legit).  A LEGIT molecule (triphenylene) has a HIGHER per-placement
  cost than the crafted grind, so any per-placement-cost threshold low enough to bail the grind also bails legit PAHs;
  and one set just above the anthracene FIXTURE (4096) leaves anthracene's own ~720 ms grind un-bounded.  There is no
  ``_canonical_cost`` cut that separates crafted-slow from legit-slow -- they are the same asymmetric-permutation shape.

CONCLUSION: the caps are RETAINED unchanged.  The only sound lift is a TRUE runtime meter (actual leaf/iteration
count) INSIDE ``canonical()``, which conflicts with ``Molecule.canonical()``'s ``lru_cache`` -- a budget-truncated
result cached under ``(self,)`` alone would poison every later, unrelated caller of the shared pure function.  That is
the MEASURED CORE CHANGE ROUND-12 named and this round re-confirms; it is NOT a cheap placement-layer patch.  Pinned by
tests/test_resonance_cost.py (the structural, non-timing tripwire).
"""
from __future__ import annotations

import time

import smartchem.category as cat
from smartchem.smiles import parse_smiles, resonance_canonical

# Instrument the (un-cached) canonicaliser to record, per placement, its runtime + the proxy + which branch it took.
_ORIG = getattr(cat.Molecule.canonical, "__wrapped__", cat.Molecule.canonical)
_LOG: list[tuple[float, int, str, int]] = []


def _instrumented(self):
    cost = cat._canonical_cost(self.atoms, self.bonds)
    branch = "PERM" if cost <= cat._MAX_CANONICAL_CANDIDATES else "INDIV"
    t = time.perf_counter()
    result = _ORIG(self)
    _LOG.append((time.perf_counter() - t, cost, branch, len(self.atoms)))
    return result


# labelled probe set: (label, SMILES, expectation) -- expectation is documentation, not an assertion here.
_CASES = [
    ("naphthalene   [FIXTURE, fast]", "c1cccc2ccccc12"),
    ("anthracene    [FIXTURE, SLOW]", "c1ccc2cc3ccccc3cc2c1"),
    ("phenanthrene  [FIXTURE]",       "c1ccc2ccc3ccccc3c2c1"),
    ("aspirin       [FIXTURE, fast]", "O=C(O)c1ccccc1OC(C)=O"),
    ("pyrene        [legit, SLOW]",   "c1cc2ccc3cccc4ccc(c1)c2c34"),
    ("coronene-C24  [legit, FAST]",   "c1cc2ccc3ccc4ccc5ccc6ccc1c1c2c3c4c5c61"),
    ("triphenylene  [legit, SLOW]",   "c1ccc2c(c1)c1ccccc1c1ccccc21"),
    ("GRIND-crafted [DoS, SLOW]",     "c1cc2ccc3ccc4ccc5ccc1c1c2c3c4c51"),
]


def main() -> None:
    cat.Molecule.canonical = _instrumented  # drop the cache; count every placement's canonicalisation
    print(f"{'molecule':32s} {'total(ms)':>9s} {'placements':>10s} {'perm':>4s} {'indiv':>5s} "
          f"{'max_call(ms)':>12s} {'max_call_cost':>16s} {'branch':>6s}")
    print("-" * 104)
    rows = []
    for label, smi in _CASES:
        _LOG.clear()
        t0 = time.perf_counter()
        try:
            resonance_canonical(parse_smiles(smi))
        except Exception as exc:  # noqa: BLE001 -- a fallback/raise is a datum, not a failure
            print(f"{label:32s}  (raised {type(exc).__name__})")
            continue
        total = time.perf_counter() - t0
        perm = sum(1 for r in _LOG if r[2] == "PERM")
        indiv = len(_LOG) - perm
        slowest = max(_LOG, default=(0.0, 0, "-", 0))
        rows.append((label, total, len(_LOG), perm, indiv, slowest))
        print(f"{label:32s} {total * 1000:9.1f} {len(_LOG):10d} {perm:4d} {indiv:5d} "
              f"{slowest[0] * 1000:12.1f} {slowest[1]:16d} {slowest[2]:>6s}")
    print("-" * 104)
    # the reproducible refutation: a LEGIT molecule's max per-placement PERMUTATION cost is >= the crafted grind's, so
    # no per-placement-cost cut separates them; and the individualisation branch (real coronene) is fast at ~1e23 cost.
    def _max_perm_cost(label_substr):
        for lbl, _t, _n, _p, _i, slow in rows:
            if label_substr in lbl:
                return max((c for _dt, c, br, _a in [slow] if br == "PERM"), default=0)
        return 0
    grind = _max_perm_cost("GRIND")
    legit_slow = max(_max_perm_cost("triphenylene"), _max_perm_cost("pyrene"))
    indiv_row = next((r for r in rows if "coronene" in r[0]), None)
    print(f"\ncrafted grind max perm-cost = {grind:,}; legit-slow (triphenylene/pyrene) max perm-cost = {legit_slow:,}")
    print(f"=> legit_slow >= crafted ({legit_slow >= grind}): a threshold that bails the grind also bails legit PAHs.")
    if indiv_row:
        print(f"=> real coronene is ALL-individualisation and FAST ({indiv_row[1]*1000:.0f} ms) at nominal cost "
              f"{indiv_row[5][1]:.2e} -- so a raw _canonical_cost budget would bail a FAST molecule.")
    print("=> no _canonical_cost-derived proxy is a sound runtime bound.  Caps retained; the robust fix (a true")
    print("   runtime meter inside canonical()) conflicts with its lru_cache -- the measured core change, deferred.")


if __name__ == "__main__":
    main()
