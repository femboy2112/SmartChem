"""CIP Rule 3 (double-bond E/Z geometry) in the namer (ROUND 34 item 1).

Pins the oracle-verified finding that a stereocentre whose two acyclic ligands differ only in double-bond geometry
(the R32 isolation ``C[C@](/C=C\\C)(/C=C/C)O``) now NAMES via CIP Rule 3 (seqcis 'Z' > seqtrans 'E'), built as a
third hierarchical pass at the Rule-1a+Rule-2 tie hand-off with E/Z perceived from the parsed ``/``/``\\`` markers.
A double bond with unresolvable geometry (no marker) or a ring stereocentre still DEFERS.  Committed assertions are
RDKit-FREE; the live rdkit cross-check skips when rdkit is absent.
"""
from __future__ import annotations

import pytest

from experiments import cip_rule3_ez_probe as probe
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()
    r = probe.report()
    assert r["hash_matches"], f"Rule-3 E/Z finding drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_ez_centres_name_and_match_the_oracle_never_mislabel():
    named = 0
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: {got} != {expected} [{note}]"
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi} [{note}]"
            named += 1
    assert named >= 8, "battery must non-vacuously name the E/Z (Rule 3) class"


def test_the_r32_isolation_names_by_rule_3():
    # the two propenyl arms tie under Rules 1a AND 2 (identical constitution); only Rule 3 (Z > E) decides.
    assert cip_labels(r"C[C@](/C=C\C)(/C=C/C)O") == ("R",)   # Z-propenyl outranks E-propenyl
    assert cip_labels(r"C[C@](/C=C/C)(/C=C\C)O") == ("S",)   # swap -> S


def test_lower_rules_unchanged_by_rule_3():
    # Rule 3 fires ONLY at the Rule-1a+2 tie hand-off, so Rule-1a and isotope-Rule-2 centres are byte-identical.
    assert cip_labels("C[C@H](N)C(=O)O") == ("S",)           # L-alanine (Rule 1a)
    assert cip_labels("[C@H](F)(Cl)Br") == ("S",)            # distinct-Z
    assert cip_labels("F[C@@](Cl)([2H])[3H]") == ("R",)      # isotope Rule 2 (R28)
    assert cip_labels("[C@](C1CCCCC1=O)(C)(F)Cl") == ("R",)  # exocyclic ring (R34 item 2)


def test_unresolvable_geometry_and_ring_centre_defer():
    assert cip_labels(r"C[C@](C=CC)(C=CC)O") == ()           # no direction markers -> geometry unknown
    assert cip_labels(r"O[C@](/C(\F)=C\C)(/C(\F)=C/C)N") == ()  # contradictory markers -> no E/Z
    assert cip_labels(r"[C@]1(/C=C/C)CCCC1") == ()           # ring stereocentre -> out of scope


def test_rdkit_cross_check_reproduces_the_sweep_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["mismatches"] == 0
    assert summary["ez_named"] >= 100
    assert summary["battery_verified"] == len(probe.BATTERY)
