"""CIP-PER-ATOM-ORACLE-01: the per-atom oracle cross-check that closes the multiset-blind gap.

ROUND 35's three review bearings agreed the shipped ``cip_labels`` sorted multiset (and every committed
RDKit probe that mirrors it) cannot see a per-centre R<->S swap on a symmetric multiset -- the failure mode
the parser-driven ring-parity witness would produce.  These tests exercise the RDKit-free half always, gate
the live oracle comparison behind ``importorskip`` (skipped in the maintained baseline, run in the dev venv),
and pin the NON-VACUITY proof so a green cross-check means the check can actually catch the bug.
"""
import pytest

from experiments import cip_per_atom_oracle_probe as probe


def test_validate_rdkit_free():
    probe.validate()


def test_frozen_hash_pins_per_atom_output():
    assert probe.content_hash() == probe.FROZEN_HASH


def test_swap_is_blind_in_multiset_but_caught_per_atom():
    # The non-vacuity guarantee: a per-centre swap the sorted multiset cannot distinguish IS distinguished
    # per atom. If this regresses, a green cross-check would be meaningless.
    probe._assert_swap_detected()


def test_rdkit_per_atom_cross_check():
    pytest.importorskip("rdkit")
    report = probe._rdkit_cross_check()
    assert report["mismatches"] == 0, report["details"]
    assert report["compared"] > 0
    assert report["skipped"] == 0
