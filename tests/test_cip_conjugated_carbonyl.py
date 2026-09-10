"""CIP-CONJUGATED-CARBONYL-01: ROUND 39 build -- conjugated rings bearing an exocyclic terminal-chalcogen
carbonyl (enone / dienone / quinone / butenolide) now NAME (queue item 1, the conjugated-ring slice).

The exocyclic-carbonyl ring carbon is admitted as a ring SPECTATOR (its ring bonds are both single, its
exocyclic C=O/C=S is Kekule-fixed to a terminal chalcogen), so the ring RELEASES on its unique acceptor
matching and ordinary Rule 1a names the centre -- ADMISSION, not new averaging.  Real forcing consumers that
previously deferred and now name include L-ascorbic acid (VITAMIN C) and carvone; 0 mislabels vs RDKit.
Out-of-scope conjugated sub-cases (charged rings; exocyclic =CH2/=NH) stay deferred fail-closed.  These tests
pin the RDKit-free build; the gated cross-check confirms 0 mislabels + representation-invariance when RDKit is
present (dev venv only).
"""
from __future__ import annotations

import pytest

from experiments import cip_conjugated_carbonyl_probe as probe
from smartchem.smiles import SmilesError, cip_labels, cip_labels_by_atom


def test_probe_validates_and_frozen_hash_stable():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


def test_vitamin_c_and_carvone_now_name():
    # the north-star-grade real consumers: the enediol-lactone (two centres) and the spearmint terpene enone
    assert cip_labels_by_atom("OC[C@@H](O)[C@@H]1OC(=O)C(O)=C1O") == {2: "R", 4: "S"}   # L-ascorbic acid
    assert cip_labels_by_atom("CC(=C)[C@@H]1CC(=O)C(C)=CC1") == {3: "S"}                 # carvone


def test_enones_quinones_butenolides_name():
    assert cip_labels("O[C@@H]1CCC(=O)C=C1") == ("R",)              # 4-hydroxycyclohex-2-enone
    assert cip_labels("C[C@@H](O)C1=CC(=O)C=CC1=O") == ("R",)       # quinonyl ethanol
    assert cip_labels("O[C@@H](C)C1=CC(=O)c2ccccc2C1=O") == ("S",)  # hydroxyethyl-naphthoquinone
    assert cip_labels("C[C@@H]1OC(=O)C=C1") == ("S",)               # butenolide (lactone C=O + ring C=C)
    assert cip_labels("C[C@H](O)C1=CC=CC1=O") == ("S",)             # cyclopentadienone
    # dalembert reinforcement: a carbonyl on a NON-benzenoid FUSED ring reaching the averaging path
    assert cip_labels("O[C@@H](C)C1=CC2=CC=CC=CC=C2C1=O") == ("S",)


def test_enantiomer_labels_flip():
    # a CIP descriptor is geometric: the mirror image carries the mirrored label (no fabricated distinction)
    assert cip_labels("C[C@@H](O)C1=CC(=O)C=CC1=O") == ("R",)
    assert cip_labels("C[C@H](O)C1=CC(=O)C=CC1=O") == ("S",)


def test_out_of_scope_conjugated_subcases_defer_fail_closed():
    # exocyclic =CH2 (fulvene) and =NH (quinone-imine): RDKit names them, we DECLINE (a wrong R/S is worse).
    # NB: the CHARGED explicit-Kekule thiazolium this test once pinned as a defer now NAMES -- ROUND 40 admitted
    # charged conjugated/aromatic rings; that consumer is asserted in tests/test_cip_charged_ring.py.
    assert cip_labels_by_atom("C[C@@H](O)C1=[N+](C)C=CS1") == {1: "R"}  # thiazolium: charged -> NAMED (R40)
    assert cip_labels_by_atom("O[C@@H](CC)C1=CC=CC1=C") == {}       # fulvenyl (=CH2)
    assert cip_labels_by_atom("O[C@@H](C)C1=CC(=N)C=CC1=O") == {}   # quinone-imine (=NH)


def test_charged_aromatic_spelling_hits_the_parser_wall():
    # the OTHER charged defer path (mr-president cond 2): a charged AROMATIC spelling is refused UPSTREAM of the
    # namer at kekulization, distinct from the explicit-Kekule thiazolium above which declines at the namer.
    with pytest.raises(SmilesError, match="could not assign a Kekulé structure"):
        cip_labels_by_atom("C[C@@H](O)c1cccc[n+]1C")


def test_localized_and_saturated_rings_unchanged():
    # no regression on the neutral slice: saturated ring, localized ring, and mancude averaging all unchanged
    assert cip_labels_by_atom("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O") == {3: "S", 6: "R", 9: "R"}  # menthol
    assert cip_labels("OC(=O)[C@@H]1CCC=CC1") == ("R",)             # localized cyclohexene ring (R33)
    assert cip_labels("O[C@H](c1ccccc1)c1ccncc1") == ("R",)         # mancude averaging (phenyl vs pyridyl)


def test_structure_theorem_holds():
    probe._assert_structure_theorem()


def test_rdkit_cross_check_zero_mislabels():
    pytest.importorskip("rdkit")
    result = probe._rdkit_cross_check()
    assert result["mismatches"] == 0
    assert result["consumers_named"] >= 8
    assert result["defers_confirmed"] >= 2   # R40 moved the charged defer out; =CH2 + =NH remain
    assert result["invariance_ok"] == len(probe._INVARIANCE)
