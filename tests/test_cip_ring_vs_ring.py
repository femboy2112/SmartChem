"""ROUND 34 item 5: Rule-1a-distinct ring-vs-ring priorities after the FIFO comparator correction."""
from __future__ import annotations

import pytest

from experiments import cip_ring_vs_ring_probe as probe
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()
    result = probe.report()
    assert result["hash_matches"], f"ring-vs-ring evidence drifted: {result['content_hash']} != {probe.FROZEN_HASH}"


def test_rule_1a_distinct_ring_pairs_name_and_match_the_baked_oracle():
    named = 0
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: {got} != {expected} [{note}]"
        if category == "ringring-name":
            assert got == rd_label, f"MISLABEL vs oracle on {smi} [{note}]"
            named += 1
    assert named >= 10


def test_isotope_on_rule_1a_tied_rings_still_defers_before_rule_2():
    assert cip_labels("[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl") == ()
    assert cip_labels("[C@]([13CH]1CCCC1)(C1CCCC1)(F)Cl") == ()


def test_rdkit_cross_check_reproduces_the_all_kind_holdout_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["mismatches"] == 0
    assert summary["compared"] >= 2500
    assert summary["battery_verified"] == len(probe.BATTERY)
