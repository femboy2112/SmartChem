"""Ring stereocentres (CIP Rules 4/5 territory): a VERIFIED DEFER (ROUND 34 item 3).

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


def test_all_ring_stereocentres_defer_never_mislabel():
    for smi, rd_label, expected, category, note in probe.BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected == (), f"{smi}: ring stereocentre must DEFER, got {got} [{note}]"


def test_the_consumer_is_real_including_pseudo_asymmetric():
    # RDKit names ring stereocentres we defer -- the consumer exists (incl. Rule-5 pseudo-asymmetric r/s + menthol).
    consumers = [b for b in probe.BATTERY if b[3] == "ringcentre-defer"]
    assert len(consumers) >= 6
    assert any(x in ("r", "s") for b in consumers for x in b[1]), "must exhibit pseudo-asymmetric r/s (Rule 5)"


def test_on_cycle_gates_the_deferral():
    # the deferral is the ring-centre scope gate (_on_cycle), not an incidental miss.
    assert probe._on_cycle_gates_all_marked_ring_centres()


def test_symmetric_ring_carbon_is_agreed_defer():
    # a non-stereogenic symmetric ring carbon: both we and RDKit defer (sound, not a consumer).
    assert cip_labels("O[C@H]1CCCCC1") == ()


def test_rdkit_cross_check_confirms_the_consumer_when_available():
    pytest.importorskip("rdkit")
    summary = probe._rdkit_cross_check()
    assert summary["consumers"] >= 6
    assert summary["battery_verified"] == len(probe.BATTERY)
