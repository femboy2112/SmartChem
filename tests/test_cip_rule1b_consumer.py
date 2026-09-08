"""CIP Rule 1b (Rung 2) consumer investigation -> VERIFIED DEFER (ROUND 32).

Pins the oracle-verified finding that Rule 1b has no demonstrated consumer anywhere in the namer's scope: the
shipped Rule-1a+2 namer agrees with RDKit's rdCIPLabeler on every acyclic + saturated-ring case, every
in-scope deferral where RDKit labels is a ring-UNSATURATION gap (ligands Rule-1a-distinct) not a Rule-1b tie,
and ring-on-centre cases are filtered out of scope.  Committed assertions are RDKit-FREE; the live rdkit
cross-check (re-running both committed sweeps) skips when rdkit is absent (the committed environment).
"""
from __future__ import annotations

import pytest

from experiments import cip_rule1b_consumer_probe as probe
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()                                    # RDKit-free: raises if the namer drifts from the finding
    r = probe.report()
    assert r["hash_matches"], f"Rule-1b consumer finding drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_shipped_namer_agrees_with_the_oracle_never_mislabels():
    agreements = 0
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: {got} != {expected} [{note}]"
        if category in ("acyclic-name", "ring-sub-sat-name"):
            assert got == rd_label, f"mislabel vs oracle on {smi}"
            agreements += 1
    assert agreements >= 10


def test_no_rule_1b_consumer_in_scope_every_inscope_deferral_is_ring_handling():
    # the whole justification for the defer: no molecule where 1a+2 tie and 1b decides.
    assert probe.ACYCLIC_RULE1B_CONSUMERS == 0
    assert probe.RING_SUB_UNSATURATED == probe.RING_SUB_INSCOPE_DEFERRALS   # all ring-sub defers are unsaturation


def test_the_isolation_saturated_ring_names_unsaturated_ring_defers():
    # spectators (C/F/Cl) can never tie a ring ligand at Rule 1a, so this deferral is a ring-UNSATURATION gap,
    # NOT a Rule-1b tie-break: the ONLY change is the ring double bond.
    assert cip_labels("[C@](C1CC1)(C)(F)Cl") == ("R",)      # saturated cyclopropyl -> NAMES
    assert cip_labels("[C@](C1=CC1)(C)(F)Cl") == ()          # unsaturated cyclopropenyl -> DEFERS


def test_the_acyclic_soundness_crux_duplicate_never_collides_with_real():
    # dalembert's proven lemma rests on this invariant: a real terminal C/N/O/S node always outranks a
    # duplicate-atom leaf of the same element under _cip_compare (a real node has a Z>=1 child; a duplicate
    # leaf has only phantom-0 children).  Pinned against an H-filling / phantom-child regression that would
    # re-open the acyclic Rule-1b gap.
    assert probe.duplicate_never_collides_with_real() == len(probe._DUPLICATE_CAPABLE)


def test_acyclic_deferrals_that_exist_are_rule_3_not_rule_1b():
    # honest boundary: acyclic deferrals where rdkit labels DO exist -- but they are Rule 3 (E/Z geometry) on
    # constitutionally-identical ligands, never Rule 1b (which the lemma proves ties on identical constitution).
    assert cip_labels(r"C[C@](/C=C\C)(/C=C/C)O") == ()      # rdkit: R; we defer soundly (Rule 3, not 1b)


def test_rdkit_cross_check_reproduces_both_sweeps_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["acyclic"]["rule1b_consumers"] == 0
    assert summary["ring_substituent"]["unsaturated"] == summary["ring_substituent"]["inscope_deferrals"]
    assert summary["battery_verified"] == len(probe.BATTERY)
