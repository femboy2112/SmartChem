"""Item 1: CIP target-relative Rules 4b/4c is a VERIFIED DEFER.

The forcing class (symmetric even-ring mutually-pseudoasymmetric centres) is deferred SOUNDLY -- the repo
declines, RDKit names lowercase ``s,s`` via a recursion the repo does not implement -- and no north-star or real
chiral molecule needs it.  RDKit-free assertions run in the committed baseline; the oracle cross-check is
``importorskip``-gated (dev venv only), matching the standing CIP-probe convention.
"""
from __future__ import annotations

import pytest

from smartchem.smiles import cip_labels, cip_labels_by_atom

from experiments import cip_target_relative_rules_probe as probe


def test_probe_validate_and_structure_theorem():
    probe.validate()  # forcing-class defers, controls name, the empty-vs-nonempty aux-pool structure holds


def test_frozen_hash_unmoved():
    assert probe.content_hash() == probe.FROZEN_HASH


def test_forcing_class_defers_soundly():
    # the canonical target and its dimethyl twin: the repo declines BOTH centres (never a guessed/wrong label)
    for smi in ("O[C@H]1CC[C@@H](C)CC1", "C[C@H]1CC[C@@H](C)CC1"):
        assert cip_labels(smi) == ()
        assert cip_labels_by_atom(smi) == {}


def test_defer_is_precisely_the_mutual_pseudo_case():
    # symmetry-broken homologs are NAMED -> the defer is not a blanket ring failure
    assert cip_labels_by_atom("O[C@H]1CC[C@@H](C)CCC1") == {1: "R", 4: "S"}   # 7-ring
    assert cip_labels_by_atom("O[C@H]1C[C@@H](C)CC1") == {1: "R", 3: "S"}     # 5-ring
    # the bounded ROUND-35 4a/5 pass names a pseudo centre when the auxiliary pool is NON-empty (the seeded case)
    assert cip_labels_by_atom("O[C@H]1[C@H](O)[C@@H](O)CCC1") == {1: "R", 4: "S", 2: "r"}


def test_no_north_star_or_real_chiral_consumer():
    # the litmus targets are stereocenter-free; real chiral drugs are fully named -> no in-scope 4b/4c consumer
    assert cip_labels("CC(=O)Nc1ccc(O)cc1") == ()                             # paracetamol (achiral)
    assert cip_labels("CC(=O)Oc1ccccc1C(=O)O") == ()                         # aspirin (achiral)
    assert cip_labels_by_atom("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O") == {3: "S", 6: "R", 9: "R"}  # menthol


def test_rdkit_cross_check_zero_mismatch():
    pytest.importorskip("rdkit")
    r = probe._rdkit_cross_check()
    assert r["mismatches"] == 0, r["details"]
    assert r["forcing_confirmed"] == 2        # both forcing-class molecules: repo declines, RDKit names
    assert r["compared"] >= 12                # every named centre compared to the oracle, element-verified
    assert r["hash_matches"]
