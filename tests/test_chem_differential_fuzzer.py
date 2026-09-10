"""CHEM-FUZZ-01: the committed, RDKit-FREE core of the differential fuzzer runs in CI.

The generative differential campaign (``run_fuzz``) needs RDKit as the oracle and is a dev-venv instrument; but the
fuzzer's INVARIANTS -- representation invariance (one identity + one CIP multiset over a frozen respelling corpus),
enantiomer flip, and synthesis-path conservation (the cert accepts balanced isomerisations, refuses unbalanced) --
are checkable with no RDKit present, so they gate every commit here.  When RDKit IS available the full campaign is
run and asserted to surface zero findings.
"""
from __future__ import annotations

import random

import pytest

from experiments import chem_differential_fuzzer as F


def test_selftest_invariants_hold_rdkit_free():
    F.selftest()


def test_frozen_hash_stable():
    assert F.content_hash() == F.FROZEN_HASH


def test_synthesis_path_conservation_fail_closed():
    # the conservation cert accepts a balanced isomerisation (same formula, different structure) and refuses an
    # atom-unbalanced reaction -- a wrong "synthesis path" never rides silently.
    assert F.check_synthesis_conservation(random.Random(0)) == []


def test_generative_campaign_finds_nothing_when_rdkit_present():
    pytest.importorskip("rdkit")
    summary = F.run_fuzz(seed=0, n_mutations=150, n_respellings=4, verbose=False)
    assert summary["n_findings"] == 0, summary["findings"][:10]
    assert summary["unique_molecules_tested"] >= 40
    assert summary["same_molecule_pairs_checked"] >= 1
