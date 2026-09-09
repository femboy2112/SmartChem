"""Ring-vs-ring + isotope-on-ring CIP naming: a VERIFIED DEFER (ROUND 34 item 5).

Pins the oracle-verified finding that an off-ring stereocentre bearing TWO rings cannot yet be named soundly: the
Rule-1a(+2) digraph resolves a deep ring-vs-ring descent differently from RDKit for same-kind unsaturated pairs
(Rule-1b territory, R32).  The _CIP_RING_VS_RING_GUARD fails such a centre CLOSED; the guard is LOAD-BEARING
(relaxing it reintroduces mislabels) yet TARGETED (two saturated rings, a single ring, and pure mancude-vs-mancude
still NAME).  Committed assertions are RDKit-FREE; the live rdkit cross-check + the guard-off proof skip when
rdkit is absent.
"""
from __future__ import annotations

import pytest

from experiments import cip_ring_vs_ring_probe as probe
from smartchem import smiles
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()
    r = probe.report()
    assert r["hash_matches"], f"ring-vs-ring finding drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_the_guard_ships_on():
    assert smiles._CIP_RING_VS_RING_GUARD is True


def test_ring_vs_ring_and_isotope_on_ring_defer_never_mislabel():
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: {got} != {expected} [{note}]"
        if category != "sound-name":
            assert not got, f"{smi} must DEFER [{note}]"


def test_the_guard_is_targeted_sound_ring_pairs_still_name():
    # the guard does NOT over-defer: two saturated rings, a single released/fused ring, and pure mancude-vs-mancude
    assert cip_labels("[C@](C1CCCCC1)(C1CCCC1)(C)F") == ("R",)     # two saturated rings
    assert cip_labels("[C@](C1CCCCC1=O)(C)(F)Cl") == ("R",)        # single exocyclic ring (item 2)
    assert cip_labels("[C@](C1Cc2ccccc2C1)(C)(F)Cl") == ("R",)     # single fused ring (item 4)
    assert cip_labels("[C@](c1ccccc1)(c1ccncc1)(C)O") == ("S",)    # phenyl vs pyridyl (pure mancude, R22)


def test_the_guard_is_load_bearing_relaxing_it_mislabels():
    # the fused-vs-fused surface item 4 opened is covered too: indane vs tetralin defers, never mislabels.
    assert cip_labels("[C@](C1Cc2ccccc2C1)(C1CCc2ccccc2C1)(C)F") == ()
    assert cip_labels("[C@](C1=CCCCC1)(C1=CCCC1)(C)F") == ()
    pytest.importorskip("rdkit")
    assert probe.guard_off_mislabels() > 0, "relaxing the guard must reintroduce ring-vs-ring mislabels"


def test_rdkit_cross_check_guard_on_never_mislabels_off_does():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["guard_on_mislabels"] == 0
    assert summary["guard_off_mislabels"] > 0
    assert summary["battery_verified"] == len(probe.BATTERY)
