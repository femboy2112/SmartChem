"""Pins :mod:`experiments.v0_7_forcing_corpus` -- the certified route algebra widens generation across ALL EIGHT
admitted Diels-Alder families (Round I's forcing vertical only exercised the alkene family; this closes the gap).
"""
from __future__ import annotations

from experiments.v0_7_forcing_corpus import FAMILIES, HOLDOUTS, HOSTILE, run


def test_all_properties_hold():
    results = run()
    failed = [(name, detail) for name, ok, detail in results if not ok]
    assert failed == [], f"forcing-corpus properties FAILED: {failed}"


def test_eight_families_declared():
    assert len(FAMILIES) == 8
    assert len({kind for _, kind, _, _, _ in FAMILIES}) == 8   # 8 distinct witness_kinds, no duplicate family


def test_each_family_enumerates_and_is_class_vouched_with_no_cross_poach():
    results = run()
    by_name = {name: ok for name, ok, _ in results}
    for name, _kind, _smiles, _marker, _source in FAMILIES:
        assert by_name[f"{name}: enumerated"] is True
        assert by_name[f"{name}: re-derived + reachable"] is True
        assert by_name[f"{name}: class-vouched"] is True
        assert by_name[f"{name}: no cross-poach"] is True
        assert by_name[f"{name}: default registry stays silent"] is True


def test_hostile_near_misses_emit_zero_da_witnesses_under_both_registries():
    results = run()
    by_name = {name: ok for name, ok, _ in results}
    for name, _smiles in HOSTILE:
        assert by_name[f"hostile near-miss ({name}): certified registry emits zero DA witnesses"] is True
        assert by_name[f"hostile near-miss ({name}): default registry emits zero DA witnesses"] is True


def test_fresh_holdouts_fire_their_family_and_stay_silent_under_default():
    results = run()
    by_name = {name: ok for name, ok, _ in results}
    for name, _smiles, _kind in HOLDOUTS:
        assert by_name[f"fresh holdout ({name}): certified registry enumerates its family"] is True
        assert by_name[f"fresh holdout ({name}): default registry stays silent"] is True
