"""Localized unsaturated-ring substituents in the CIP namer (ROUND 33).

Pins the oracle-verified finding that a LOCALIZED unsaturated ring (a single forced Kekule structure --
cyclopropene, cyclohexene, cyclopentadiene, a cyclic enol ether, a localized fused bicyclic) now NAMES, closing
the R32-surfaced gap, while the two mechanisms that remain (exocyclic double bonds; aromatic-fused-to-saturated)
and the ring-vs-ring / isotope-on-ring corners DEFER soundly.  Committed assertions are RDKit-FREE; the live
rdkit cross-check (re-running the localized sweep) skips when rdkit is absent (the committed environment).
"""
from __future__ import annotations

import pytest

from experiments import cip_localized_ring_probe as probe
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()                                    # RDKit-free: raises if the namer drifts from the finding
    r = probe.report()
    assert r["hash_matches"], f"localized-ring finding drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_localized_rings_name_and_match_the_oracle_never_mislabel():
    named = 0
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: {got} != {expected} [{note}]"
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi} [{note}]"
            named += 1
    assert named >= 15, "battery must non-vacuously name the localized-ring class + reroute + mancude"


def test_the_isolation_the_r32_gap_is_closed():
    # R32's isolation: the saturated ring named; the SAME ring + one double bond DEFERRED.  R33 closes it --
    # BOTH now name (the ligands were always Rule-1a-distinct; only the ring-digraph boundary was too eager).
    assert cip_labels("[C@](C1CC1)(C)(F)Cl") == ("R",)       # saturated cyclopropyl -> NAMES (as before)
    assert cip_labels("[C@](C1=CC1)(C)(F)Cl") == ("R",)      # localized cyclopropenyl -> NAMES (was () in R32)


def test_localized_diene_enol_ether_and_fused_bicyclic_name():
    # a spread across the localized class: multiple localized double bonds, a cyclic enol ether, a localized
    # fused bicyclic (the fused/bridged topology the R32 harness never exercised -- birdperson guard 5).
    assert cip_labels("[C@](C1C=CC=C1)(C)(F)Cl") == ("R",)       # cyclopentadiene
    assert cip_labels("[C@](C1CC=CO1)(C)(F)Cl") == ("R",)        # 2,3-dihydrofuran (cyclic enol ether)
    assert cip_labels("[C@](C1=CCC2CCCCC12)(C)(F)Cl") == ("R",)  # fused hydrindane-ene


def test_aromatic_heterocycle_reroute_names_rule1a_unchanged():
    # furan/pyrrole/thiophene are UNIQUE-matching, so R33 reroutes them from a spurious Rule-2 defer (mass=None)
    # to their real mass; Rule 1a is byte-identical (average of one partner == real Z), and the label matches rdkit.
    assert cip_labels("[C@](c1ccoc1)(C)(F)Cl") == ("R",)
    assert cip_labels("[C@](c1ccsc1)(C)(F)Cl") == ("R",)
    assert cip_labels("[C@](c1cc[nH]c1)(C)(F)Cl") == ("R",)


def test_benzene_mancude_path_is_byte_identical():
    # the >=2-matching (no-spectator) branch is unchanged: benzene still names via averaging exactly as before.
    assert cip_labels("[C@](c1ccccc1)(C)(F)Cl") == ("R",)
    assert cip_labels("O[C@H](c1ccccc1)c1ccccn1") == ("R",)    # phenyl vs pyridyl (R22 mancude, unchanged)


def test_aromatic_fused_to_saturated_still_defers_soundly():
    # the EXOCYCLIC boundary R33 recorded (methylenecyclohexane, cyclopentanone) was CLOSED by ROUND 34 item 2
    # (see tests/test_cip_exocyclic_ring.py); the aromatic-ring-FUSED-to-saturated case still defers here.
    assert cip_labels("[C@](C1Cc2ccccc2C1)(C)(F)Cl") == ()     # indane (aromatic fused to saturated)


def test_ring_vs_ring_and_isotope_on_ring_fail_closed():
    # a released localized ring ranked against ANOTHER ring is Rule-1b / clean-mancude territory -> DEFER;
    # an isotope-labelled Rule-1a tie on RING ligands is Rule-1b territory (R32: 1b bites with closures) -> DEFER.
    # These guard against the sweep-found mislabels; two SATURATED rings (never released) still NAME.
    assert cip_labels("[C@](C1=CCCCC1)(C1=CCCC1)(C)F") == ()        # two localized rings -> DEFER
    assert cip_labels("[C@](C1=CC1)(c1ccccc1)(F)Cl") == ()          # released ring vs mancude aromatic -> DEFER
    assert cip_labels("[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl") == ()   # isotope-on-ring Rule-1a tie -> DEFER
    assert cip_labels("[C@](C1CCCCC1)(C1CCCC1)(C)F") == ("R",)      # two SATURATED rings -> still NAME (no regression)


def test_rdkit_cross_check_reproduces_the_sweep_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["mismatches"] == 0                  # the soundness bar: 0 disagreements over the localized sweep
    assert summary["localized_named"] >= 150
    assert summary["battery_verified"] == len(probe.BATTERY)
