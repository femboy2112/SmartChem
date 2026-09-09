"""Aromatic-fused-to-saturated ring substituents in the CIP namer (ROUND 34 item 4).

Pins the oracle-verified finding that a delocalized aromatic ring FUSED to a saturated ring (indane, tetralin,
their hetero- and PAH-fused homologues) now NAMES -- the aromatic acceptors get the SAME R22 partner-Z averaging,
the sp3 spectator carbons keep real z -- closing the R33-recorded fused boundary, while identical fused ligands
and an ambiguous partially-hydrogenated PAH DEFER soundly. Committed assertions are RDKit-FREE; the live rdkit
cross-check skips when rdkit is absent.
"""
from __future__ import annotations

import pytest

from experiments import cip_aromatic_fused_probe as probe
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()
    r = probe.report()
    assert r["hash_matches"], f"aromatic-fused finding drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_fused_rings_name_and_match_the_oracle_never_mislabel():
    named = 0
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: {got} != {expected} [{note}]"
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi} [{note}]"
            named += 1
    assert named >= 9, "battery must non-vacuously name the aromatic-fused class"


def test_indane_and_tetralin_name():
    assert cip_labels("[C@](C1Cc2ccccc2C1)(C)(F)Cl") == ("R",)     # indane-2-yl
    assert cip_labels("[C@](C1CCc2ccccc2C1)(C)(F)Cl") == ("R",)    # tetralin
    assert cip_labels("[C@](C1Cc2ccncc2C1)(C)(F)Cl") == ("R",)     # aza-fused
    assert cip_labels("[C@](C1Cc2ccc3ccccc3c2C1)(C)(F)Cl") == ("R",)  # naphthalene-fused


def test_benzene_mancude_path_still_byte_identical():
    # the >=2-matching averaging (no spectator) is unchanged: benzene/pyridyl still name exactly as before.
    assert cip_labels("[C@](c1ccccc1)(C)(F)Cl") == ("R",)
    assert cip_labels("O[C@H](c1ccccc1)c1ccccn1") == ("R",)


def test_false_centre_and_ambiguous_pah_defer_soundly():
    assert cip_labels("[C@](C1Cc2ccccc2C1)(C1Cc2ccccc2C1)(F)Cl") == ()   # identical ligands -> false centre
    assert cip_labels("[C@](C1CCc2ccc3ccccc3c2C1)(C)F") == ()            # partially-hydrogenated phenanthrene


def test_rdkit_cross_check_reproduces_the_sweep_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["mismatches"] == 0
    assert summary["fused_named"] >= 100
    assert summary["battery_verified"] == len(probe.BATTERY)
