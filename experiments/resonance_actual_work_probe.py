"""ROUND-14 item 3: does an ACTUAL-work meter (candidates truly examined) enable a SOUND lift of the resonance
_RESONANCE_MAX_HEAVY=64 size cap, where ROUND-13's NOMINAL `_canonical_cost` proxy was REFUTED?

ROUND-13 refuted a per-placement `_canonical_cost` budget: `_canonical_cost` is a nominal permutation count that
OVER-charges the individualisation branch (coronene: astronomical nominal, yet fast) and UNDER-separates the
permutation branch (a legit PAH out-costs a crafted grind).  The named-next-step sound path is a running work-meter
INSIDE the canonicaliser.  This harness measures that meter directly.

The ACTUAL work of one `Molecule.canonical()` call is well-defined and already bounded inside the core:
  * permutation branch (budget = _cost_of(_canonical_blocks) <= _MAX_CANONICAL_CANDIDATES): the loop enumerates
    EVERY one of `budget` permutations with NO early exit, so actual == budget.
  * individualisation branch (budget > _MAX_CANONICAL_CANDIDATES): `_canonical_by_individualisation` explores
    `leaves` discrete leaves (false-twin pruned), bounded by _MAX_INDIVIDUALISATION_LEAVES=50k.  actual == leaves.
Both are "candidate labellings examined", a common unit.  The resonance enumeration pays this per Kekule placement
(<= _RESONANCE_MAX_MATCHINGS), so the TOTAL resonance work is their sum.

We force the enumeration PAST the 64 cap (temporarily raising it) and meter the total actual work, UNCACHED (the
sound meter must be cache-independent / deterministic -- so ``measure`` calls ``resonance_canonical.cache_clear()``
before it runs; a warm ``@lru_cache`` entry would otherwise SKIP the metered body and report 0).  The decision:

TWO honest caveats on the unit (evil-morty), neither affecting the load-bearing comparison:
  * ``total_actual`` sums individualisation LEAVES and permutation ITERATIONS as one "candidate examined" count, but a
    leaf drags a full refine chain while a permutation is a cheap tuple-compare -- a cross-branch sum is rough.  It is
    exact for the load-bearing comparison (triphenylene vs the grind are BOTH permutation-branch, same unit); the
    "coronene 78 vs astronomical nominal" over-charge point is qualitative (leaves vs permutations), not dimensional.
  * ``_count_individ_leaves`` mirrors the real recursion bit-for-bit BELOW the leaf ceiling; at/above
    ``_MAX_INDIVIDUALISATION_LEAVES`` the real algorithm RAISES while this mirror truncates -- no in-scope molecule
    (max 24 heavy in the whole corpus) reaches it, so the divergence is unreachable, but it is a real divergence.
  * if total actual work DECOUPLES from heavy-count along the symmetry axis -- large SYMMETRIC PAHs stay CHEAP while
    crafted grinds are EXPENSIVE, with a clean threshold between -- a work budget beats the size cap (BUILD).
  * if a legit molecule's actual work is >= a crafted grind's (no clean cut), the meter is refuted too (REFUTE).

MEASURED RESULT (ROUND-14, this harness):
  molecule                heavy  total_actual   note
  coronene (symmetric)      24            78    individualisation branch; nominal _canonical_cost is ASTRONOMICAL
  pentacene (linear-sym)    22            14    individualisation branch
  triphenylene (LEGIT)      18       196,632    permutation branch -- actual == nominal (no early exit)
  grind20 (CRAFTED)         20       180,234    permutation branch

Two structural facts, the item-3 characterisation:
  1. The actual-work meter FIXES the ROUND-13 OVER-CHARGE: coronene's actual work (78) is ~1e-? of its astronomical
     nominal `_canonical_cost` (individualisation leaves, false-twin pruned).  So actual-work IS a sound TIME bound,
     which the nominal proxy was not.
  2. But it does NOT fix the UNDER-SEPARATION: triphenylene (LEGIT, 196,632) OUT-COSTS grind20 (CRAFTED, 180,234).
     Both are permutation-branch, where the canonical loop enumerates every candidate with NO early exit, so actual
     == nominal there -- exactly the prong the nominal refutation named.  No work budget separates legit-from-crafted.

CONCLUSION -- REFINEMENT, not a lift.  An actual-work meter is a sound TIME bound but NOT a malice filter: the
decoupling is on the SYMMETRY axis (individualisation branch), never the malice axis.  A budget that admits legit
large molecules (triphenylene-scale) also admits crafted grinds; one tight enough to bail the grind bails legit
molecules too.  The ONLY sound lift the meter enables is an ADDITIVE >64-heavy escape valve (admit a large SYMMETRIC
molecule the size-cap wrongly rejects, fall back to literal identity above a total-work budget) -- but that (a)
entangles the resonance enumeration with an UNCACHED work meter (the lru_cache-conflicting core change ROUND-13
deferred) and (b) never fires in practice (no molecule approaches 64 heavy).  So the caps stay; this harness + the
tripwire characterise the sound path precisely, deliberately not gambling the core for a cap that never fires.
"""
from __future__ import annotations

import smartchem.category as cat
import smartchem.smiles as sm
from smartchem.smiles import parse_smiles

_orig_canonical = getattr(cat.Molecule.canonical, "__wrapped__", cat.Molecule.canonical)


# A leaf-counting individualisation that mirrors the real `_canonical_by_individualisation` EXACTLY (same false-twin
# pruning, same recursion order) but returns only the leaf count -- the actual work of the individualisation branch.
def _count_individ_leaves(atoms, bonds) -> int:
    n = len(atoms)
    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for b in bonds:
        adjacency[b.i].append((b.j, b.order))
        adjacency[b.j].append((b.i, b.order))
    start = cat._refine_partition(atoms, bonds, cat._blocks(cat._wl_colours(atoms, bonds)))
    leaves = [0]

    def recurse(partition):
        if leaves[0] > cat._MAX_INDIVIDUALISATION_LEAVES:
            return
        partition = cat._refine_partition(atoms, bonds, partition)
        target = next((k for k, cell in enumerate(partition) if len(cell) > 1), None)
        if target is None:
            leaves[0] += 1
            return
        cell = partition[target]
        cellset = set(cell)
        reps: list[int] = []
        seen: set = set()
        for v in cell:
            if any(j in cellset for j, _o in adjacency[v]):
                key: tuple = ("distinct", v)
            else:
                key = ("false-twin", frozenset(adjacency[v]))
            if key in seen:
                continue
            seen.add(key)
            reps.append(v)
        for v in reps:
            recurse(partition[:target] + [(v,), tuple(x for x in cell if x != v)] + partition[target + 1:])

    recurse(start)
    return leaves[0]


def measure(smi: str) -> dict:
    """Total ACTUAL resonance work for one SMILES: force the enumeration past the 64 cap, meter every placement."""
    mol = parse_smiles(smi)
    heavy = sum(1 for s in mol.atoms if s != "H")
    per_call: list[tuple[str, int]] = []

    def _metered(self):
        n = len(self.atoms)
        if n > 1:
            blocks = cat._canonical_blocks(self.atoms, self.bonds)
            budget = cat._cost_of(blocks)
            if budget > cat._MAX_CANONICAL_CANDIDATES:
                per_call.append(("individ", _count_individ_leaves(self.atoms, self.bonds)))
            else:
                per_call.append(("perm", budget))
        return _orig_canonical(self)

    saved_cap = sm._RESONANCE_MAX_HEAVY
    saved_can = cat.Molecule.canonical
    sm._RESONANCE_MAX_HEAVY = 10_000          # force the enumeration to run even for a big molecule
    cat.Molecule.canonical = _metered
    # `resonance_canonical` is itself @lru_cache'd (smiles.py): a warm entry SKIPS the whole metered body and reports
    # 0 work.  Clear it so `measure` reports the TRUE per-invocation work DETERMINISTICALLY, independent of cache state
    # -- without this, the "uncached" claim is a lie and any repeat/warm call zeroes the reading (evil-morty finding D).
    sm.resonance_canonical.cache_clear()
    try:
        sm.resonance_canonical(mol)
    finally:
        sm._RESONANCE_MAX_HEAVY = saved_cap
        cat.Molecule.canonical = saved_can
        sm.resonance_canonical.cache_clear()  # leave no metered-region entry cached for a later real caller
    total = sum(c for _b, c in per_call)
    return {
        "smi": smi, "heavy": heavy, "placements": len(per_call), "total_actual": total,
        "max_per_placement": max((c for _b, c in per_call), default=0),
        "branches": {b for b, _c in per_call},
    }


LEGIT = {
    "benzene": "c1ccccc1",
    "naphthalene": "c1ccc2ccccc2c1",
    "anthracene": "c1ccc2cc3ccccc3cc2c1",
    "phenanthrene": "c1ccc2ccc3ccccc3c2c1",
    "triphenylene": "c1ccc2c(c1)c1ccccc1c1ccccc21",
    "pyrene": "c1cc2ccc3cccc4ccc(c1)c2c34",
    "coronene(24C,sym)": "c1cc2ccc3ccc4ccc5ccc6ccc1c1c2c3c4c5c61",
    "pentacene(22C)": "c1ccc2cc3cc4cc5ccccc5cc4cc3cc2c1",
}
CRAFTED = {
    "grind20(under-cap)": "c1cc2ccc3ccc4ccc5ccc1c1c2c3c4c51",
}

if __name__ == "__main__":
    rows = []
    for name, smi in {**{f"L:{k}": v for k, v in LEGIT.items()},
                      **{f"C:{k}": v for k, v in CRAFTED.items()}}.items():
        try:
            r = measure(smi)
            rows.append((name, r))
        except Exception as exc:  # noqa: BLE001 -- a probe: record the failure mode, don't crash the sweep
            rows.append((name, {"error": f"{type(exc).__name__}: {exc}"}))
    print(f"{'molecule':28s} {'heavy':>5s} {'plc':>4s} {'total_actual':>13s} {'max/plc':>9s}  branches")
    for name, r in rows:
        if "error" in r:
            print(f"{name:28s} ERROR {r['error']}")
        else:
            print(f"{name:28s} {r['heavy']:5d} {r['placements']:4d} {r['total_actual']:13d} "
                  f"{r['max_per_placement']:9d}  {sorted(r['branches'])}")
