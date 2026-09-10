"""Exocyclic-unsaturation ring substituents in the CIP namer (ROUND 34 item 2).

Pins the oracle-verified finding that a ring whose only unsaturation is EXOCYCLIC (a ring ketone/lactone/lactam
C=O, an exocyclic C=C/C=N/C=S -- every RING edge single) now NAMES, closing the R33-characterised exocyclic gap,
while a conjugated ring (an INTERNAL ring double, e.g. cyclohexenone) still defers. Rule-1a-distinct two-ring
comparisons name after the R34 FIFO correction. Committed assertions are RDKit-FREE; the live cross-check skips
when rdkit is absent.
"""
from __future__ import annotations

import pytest

from experiments import cip_exocyclic_ring_probe as probe
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()
    r = probe.report()
    assert r["hash_matches"], f"exocyclic-ring finding drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_exocyclic_rings_name_and_match_the_oracle_never_mislabel():
    named = 0
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: {got} != {expected} [{note}]"
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi} [{note}]"
            named += 1
    assert named >= 12, "battery must non-vacuously name the exocyclic-ring class"


def test_ring_carbonyls_name():
    # the big real class: ring ketones/lactones/lactams by size and position
    assert cip_labels("[C@](C1CCCC1=O)(C)(F)Cl") == ("R",)       # cyclopentanone-yl
    assert cip_labels("[C@](C1CCCCC1=O)(C)(F)Cl") == ("R",)      # cyclohexanone-yl
    assert cip_labels("[C@](C1CCC(=O)O1)(C)(F)Cl") == ("R",)     # lactone
    assert cip_labels("[C@](C1CCC(=O)N1)(C)(F)Cl") == ("R",)     # lactam
    assert cip_labels("[C@](C1C(=O)CCCC1=O)(C)(F)Cl") == ("R",)  # ring 1,3-dione (two exocyclic C=O)


def test_exocyclic_alkene_imine_thioketone_name():
    assert cip_labels("[C@](C1CCCCC1=C)(C)(F)Cl") == ("R",)      # methylenecyclohexane
    assert cip_labels("[C@](C1CCCCC1=N)(C)(F)Cl") == ("R",)      # exocyclic imine
    assert cip_labels("[C@](C1CCCCC1=S)(C)(F)Cl") == ("R",)      # exocyclic thioketone


def test_conjugated_carbonyl_now_names_but_methylene_and_charged_still_defer():
    # ROUND 39 moved the boundary: a conjugated ring (INTERNAL ring double) bearing an exocyclic terminal-
    # chalcogen carbonyl now NAMES (the exocyclic-carbonyl carbon is a spectator; the ring releases).
    assert cip_labels("[C@](C1=CCCCC1=O)(C)(F)Cl") == ("R",)      # cyclohexenone -> NAMED (was defer)
    assert cip_labels("[C@](C1C=CC(=O)C1)(C)(F)Cl") == ("R",)     # cyclopentenone -> NAMED (was defer)
    # the R39 boundary: a conjugated ring bearing an exocyclic =CH2 (aromatic-resonance) or a CHARGED ring
    # still DEFERS fail-closed (a wrong R/S is worse than an honest decline).
    assert cip_labels("[C@](C1=CCCCC1=C)(C)(F)Cl") == ()          # conjugated exocyclic =CH2 -> defer
    assert cip_labels("[C@](C1=CC=[NH+]C=C1)(C)(F)Cl") == ()      # charged pyridinium ring -> defer
    # a Rule-1a-distinct exocyclic ring pair still NAMES
    assert cip_labels("[C@](C1CCCCC1=O)(C1CCCCC1)(F)Cl") == ("R",)


def test_rdkit_cross_check_reproduces_the_sweep_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["mismatches"] == 0
    assert summary["exocyclic_named"] >= 100
    assert summary["battery_verified"] == len(probe.BATTERY)
