"""ROUND-14 item 3 (the ACTUAL-work REFINEMENT tripwire): a running work-meter of the candidates canonical() TRULY
examines characterises the sound path to lifting the resonance caps -- and pins WHY the caps still stand.

ROUND-13 refuted a NOMINAL `_canonical_cost` budget (a permutation count) on two prongs: it OVER-charges the
individualisation branch (coronene astronomical yet fast) and UNDER-separates the permutation branch (a legit PAH
out-costs a crafted grind).  ROUND-14 measured the ACTUAL-work meter (leaves truly explored / permutations truly
enumerated, uncached; see experiments/resonance_actual_work_probe.py) and found:

  1. the actual meter FIXES the over-charge -- coronene's per-placement actual work is TINY next to its astronomical
     nominal `_canonical_cost` (false-twin-pruned individualisation leaves).  So actual-work IS a sound TIME bound.
  2. the actual meter does NOT fix the under-separation -- triphenylene (LEGIT) still OUT-COSTS a crafted grind,
     because both are permutation-branch where canonical() enumerates every candidate with no early exit (actual ==
     nominal there).  So no work budget separates legit-from-crafted; the meter is a TIME bound, NOT a malice filter.

Therefore the caps stand (a size cap is a fine proxy for a limit no real molecule -- ~11-13 heavy for the litmus
targets -- ever approaches), and the only sound lift the meter enables (an ADDITIVE >64-heavy escape valve) entangles
the enumeration with an uncached work-meter -- the lru_cache-conflicting core change ROUND-13 deferred, deliberately
not gambled here for a cap that never fires.  This file pins the refinement so nobody re-walks it as a fresh idea.
"""
from experiments.resonance_actual_work_probe import measure
from smartchem.category import _MAX_CANONICAL_CANDIDATES, _canonical_cost
from smartchem.smiles import _RESONANCE_MAX_HEAVY, _RESONANCE_MAX_MATCHINGS, parse_smiles

_CORONENE = "c1cc2ccc3ccc4ccc5ccc6ccc1c1c2c3c4c5c61"       # 24 heavy, symmetric -> individualisation branch (fast)
_TRIPHENYLENE = "c1ccc2c(c1)c1ccccc1c1ccccc21"             # 18 heavy, LEGIT -> permutation branch (slow)
_GRIND = "c1cc2ccc3ccc4ccc5ccc1c1c2c3c4c51"                # 20 heavy, a CRAFTED under-cap grind (slow)


def test_actual_work_meter_fixes_the_over_charge_but_not_the_under_separation():
    """The two structural facts that make the actual-work meter a sound TIME bound yet NOT a malice filter."""
    # the ROUND-11 caps are NOT lifted -- the measured core change stays deferred.
    assert (_RESONANCE_MAX_HEAVY, _RESONANCE_MAX_MATCHINGS) == (64, 128)

    # (1) OVER-CHARGE FIXED: coronene's per-placement ACTUAL work is tiny, while its NOMINAL _canonical_cost is
    # astronomical (well past the candidate ceiling -- it takes the individualisation branch).  The nominal proxy would
    # have (wrongly) bailed this fast molecule; the actual meter does not.
    coronene = measure(_CORONENE)
    coronene_nominal = _canonical_cost(parse_smiles(_CORONENE).atoms, parse_smiles(_CORONENE).bonds)
    assert coronene_nominal > _MAX_CANONICAL_CANDIDATES * 1000          # astronomical nominal (the over-charge)
    assert coronene["max_per_placement"] < 10_000                       # ... yet the ACTUAL per-placement work is tiny
    assert coronene["max_per_placement"] * 100_000 < coronene_nominal   # the over-charge gap is enormous

    # (2) UNDER-SEPARATION PERSISTS: a LEGIT PAH out-costs a CRAFTED grind in ACTUAL total work too, so no work budget
    # can bail the grind without also bailing the legit molecule -- the meter cannot tell malice from a hard structure.
    triphenylene = measure(_TRIPHENYLENE)
    grind = measure(_GRIND)
    assert grind["total_actual"] > 100_000                             # the grind IS genuinely expensive ...
    assert triphenylene["total_actual"] >= grind["total_actual"]       # ... yet a LEGIT molecule out-costs it: no cut
    # both are permutation-branch dominated (actual == nominal there -- the reason a work budget cannot separate them).
    assert "perm" in triphenylene["branches"] and "perm" in grind["branches"]


def test_the_meter_is_deterministic_regardless_of_cache_warmth():
    """evil-morty finding D: `resonance_canonical` is @lru_cache'd, so a WARM entry would skip the metered body and
    report 0 -- which would make this whole tripwire green only by luck of a cold cache (collection order).  `measure`
    now clears that cache, so the reading is the TRUE work whether the species was seen before or not.  This pins it:
    warm the shared cache exactly as an upstream search/`resonance_identity` call does, then assert the meter is
    unmoved AND that two back-to-back measures agree (a cached-0 second reading is the exact regression guarded here)."""
    from smartchem.smiles import resonance_identity
    resonance_identity(parse_smiles(_GRIND))                # warm the shared resonance_canonical cache (the hazard)
    first = measure(_GRIND)["total_actual"]
    second = measure(_GRIND)["total_actual"]                # a cached-0 reading here is the regression
    assert first > 100_000 and first == second             # unmoved by warmth, and stable across calls

