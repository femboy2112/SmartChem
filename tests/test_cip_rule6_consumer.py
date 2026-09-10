"""CIP-RULE6-CONSUMER-01: the committed VERIFIED DEFER of CIP Rule 6 (queue item 1).

Rule 6 (the reference-dependent like/unlike tail after target-relative Rules 4b/4c) has NO reachable consumer:
the aux pass terminates at revised Rule 5 with ``return None``, there is no Rule-6 branch, and the same
empty-auxiliary-pool / bounded-admission bottleneck that starves 4b/4c (R36) starves Rule 6 a fortiori.  These
tests pin the RDKit-free structure theorem; the gated cross-check confirms 0 mislabels vs RDKit when it is
present (dev venv only).
"""
from __future__ import annotations

import pytest

from experiments import cip_rule6_consumer_probe as probe
from smartchem.smiles import cip_labels_by_atom


def test_probe_validates_and_frozen_hash_stable():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_empty_pool_forcing_class_defers_all_centres():
    # both centres pseudoasymmetric + unresolved by Rules 1a-3 -> the aux pool Rule 6 would read is empty -> DEFER
    assert cip_labels_by_atom("O[C@H]1CC[C@@H](C)CC1") == {}
    assert cip_labels_by_atom("C[C@H]1CC[C@@H](C)CC1") == {}


def test_a_non_empty_pool_is_resolved_by_revised_rule5_no_rule6_residual():
    # revised Rule 5 (the +-2 pseudoasymmetry) names the pseudoasymmetric centre when the pool is seeded, so the
    # admitted-pool case leaves NO like/unlike residual for a Rule 6 to break
    assert cip_labels_by_atom("O[C@H]1[C@H](O)[C@@H](O)CCC1") == {1: "R", 4: "S", 2: "r"}
    assert cip_labels_by_atom("OC(=O)[C@@H](O)[C@H](O)[C@@H](O)C(=O)O") == {3: "S", 7: "R", 5: "s"}


def test_real_chiral_battery_fully_named_north_stars_achiral():
    # no in-scope consumer: north stars have no centres; real chiral drugs are fully named by the shipped rules
    assert cip_labels_by_atom("CC(=O)Nc1ccc(O)cc1") == {}          # paracetamol
    assert cip_labels_by_atom("CC(=O)Oc1ccccc1C(=O)O") == {}       # aspirin
    assert cip_labels_by_atom("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O") == {3: "S", 6: "R", 9: "R"}  # menthol


def test_structure_theorem_holds():
    # covers the empty-pool wall, revised-Rule-5 resolution, AND the admission cap checked BEHAVIOURALLY (the aux
    # pass is never entered with |pool| > 2) rather than by grepping the gate's source string (dalembert fold)
    probe._assert_structure_theorem()


def test_rdkit_cross_check_zero_mislabels():
    pytest.importorskip("rdkit")
    result = probe._rdkit_cross_check()
    assert result["mismatches"] == 0
    assert result["forcing_confirmed"] == 2
    assert result["compared"] >= 12
