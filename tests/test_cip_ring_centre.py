"""Ring stereocentres: written-order naming with a recursive-auxiliary defer boundary (ROUND 35).

Pins the oracle-verified finding that a stereocentre ON a ring is scoped out by _on_cycle and DEFERS soundly
(never a mislabel), while RDKit names a real consumer population -- including pseudo-asymmetric (r/s, Rule 5) and
multi-centre (menthol). A sound ring-centre namer still needs written-neighbour-order parity + Rules 4/5; ROUND
34's FIFO correction removed the earlier ring-ranking wall. Committed assertions are RDKit-FREE; the live
rdkit cross-check skips when rdkit is absent.
"""
from __future__ import annotations

import pytest

from experiments import cip_ring_centre_probe as probe
from smartchem.smiles import cip_labels


def test_the_finding_validates_and_is_frozen():
    probe.validate()
    r = probe.report()
    assert r["hash_matches"], f"ring-centre finding drifted: {r['content_hash']} != {probe.FROZEN_HASH}"


def test_admitted_ring_stereocentres_match_the_baked_oracle():
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"{smi}: got {got} [{note}]"
        if category == "ringcentre-name":
            assert got == rd_label


def test_recursive_pseudo_ring_pair_still_defers():
    deferred = [b for b in probe.BATTERY if b[3] == "rule45-defer"]
    assert len(deferred) >= 2
    assert all(cip_labels(b[0]) == () for b in deferred)


def test_topology_control_really_contains_ring_centres():
    assert probe._on_cycle_gates_all_marked_ring_centres()


def test_symmetric_ring_carbon_is_agreed_defer():
    # a non-stereogenic symmetric ring carbon: both we and RDKit defer (sound, not a consumer).
    assert cip_labels("O[C@H]1CCCCC1") == ()


def test_rdkit_cross_check_confirms_the_consumer_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["named"] >= 5
    assert summary["battery_verified"] == len(probe.BATTERY)
