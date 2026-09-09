"""ROUND 35 admission tests for ring-source order and CIP Rules 1b/4a/5."""
import pytest

from experiments import cip_ring_aux_rules_probe as probe
from smartchem.smiles import cip_labels


def test_committed_probe_and_hash():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


def test_open_smiles_ring_order_pair_is_invariant():
    for first, second, expected in probe.OPENSMILES_EQUIVALENTS:
        assert cip_labels(first) == cip_labels(second) == expected


def test_official_rule1b_witness_is_a_real_rule1a_tie():
    assert probe._rule1b_isolation()["rule1a"] == 0
    assert probe._rule1b_isolation()["rule1b"] == 1


def test_bounded_auxiliary_slice_and_recursive_boundary():
    for text, oracle, expected, category, note in probe.BATTERY:
        got = cip_labels(text)
        assert got == expected, f"{text}: {got} [{note}]"
        if category in ("rule4a", "rule5"):
            assert got == oracle
    assert cip_labels("O[C@H]1CC[C@@H](C)CC1") == ()


def test_rdkit_randomized_equivalents_when_available():
    pytest.importorskip("rdkit")
    result = probe._rdkit_cross_check()
    assert result["random_equivalents"] >= 300
    assert result["mismatches"] == 0
