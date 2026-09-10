"""CIP-CHARGED-RING-01: ROUND 40 build -- CHARGED conjugated/aromatic rings in EXPLICIT-KEKULE spelling
(pyridinium / pyridine N-oxide / imidazolium / thiazolium / pyrylium / thiopyrylium) now NAME (queue item q1,
the charged-ring slice, refuting the prior verified-defer lean for the explicit-Kekule route).

The prior namer refused EVERY charged ring atom at a blanket charge gate (``smiles.py`` ``if atom.charge:
valid = False``).  ROUND 40 replaces that gate with a FAIL-CLOSED WHITELIST admitting exactly the
charge-EXCLUSIVE cationic ACCEPTOR valence patterns the oracle validated -- a cationic ring N (``[1,1,2]``) and a
cationic ring chalcogen (``[1,2]``).  CIP priority is by ATOMIC NUMBER and formal charge changes no atomic
number, so a charged acceptor is partner-Z averaged EXACTLY as its neutral isoelectronic analogue -- the
matching/averaging math in ``_cip_mancude`` is charge-blind by construction.  Out-of-scope charged sub-cases
(a charged AROMATIC spelling -> parser kekulization wall; an ANIONIC ring; an exotic over-charged valence) stay
deferred fail-closed.  These tests pin the RDKit-free build; the gated cross-check confirms 0 mislabels +
representation-invariance when RDKit is present (dev venv only).
"""
from __future__ import annotations

import pytest

from experiments import cip_charged_ring_probe as probe
from smartchem.smiles import cip_labels, cip_labels_by_atom


def test_probe_validates_and_frozen_hash_stable():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


def test_charged_rings_now_name_matching_the_oracle():
    # cationic ring N acceptor ONLY: pyridinium, N-methylpyridinium, pyridine N-oxide, imidazolium, thiazolium.
    # (cationic ring N has a neutral pyridine-N analogue RDKit averages identically; the chalcogen cation does not.)
    assert cip_labels("C[C@H](O)C1=CC=[NH+]C=C1") == ("S",)          # protonated pyridinium (N-H)
    assert cip_labels("C[C@H](O)C1=CC=CC=[N+]1C") == ("S",)          # N-methylpyridinium
    assert cip_labels("C[C@H](O)C1=CC=[N+]([O-])C=C1") == ("S",)     # pyridine N-oxide (zwitterion)
    assert cip_labels("C[C@H](O)C1=[N+](C)C=CN1") == ("S",)          # imidazolium (N+ acceptor + pyrrole-N spectator)
    assert cip_labels("C[C@@H](O)C1=[N+](C)C=CS1") == ("R",)         # thiazolium (N+ acceptor + S spectator)


def test_enantiomer_labels_flip():
    # a CIP descriptor is geometric: the mirror image carries the mirrored label (no fabricated charge distinction)
    assert cip_labels("C[C@H](O)C1=CC=CC=[N+]1C") == ("S",)
    assert cip_labels("C[C@@H](O)C1=CC=CC=[N+]1C") == ("R",)
    assert cip_labels("C[C@H](O)C1=CC=[N+]([O-])C=C1") == ("S",)
    assert cip_labels("C[C@@H](O)C1=CC=[N+]([O-])C=C1") == ("R",)


def test_charged_ring_vs_ring_the_fractions_decide():
    # RING-vs-RING: the centre bears two rings, so the charged ring's averaged fractions (not just ring>alkyl) decide.
    # This is the regime dalembert's structure theorem showed is load-bearing; the N+ ipso avg 6.5 < any real
    # heteroatom Z, so N+ stays sound where the chalcogen cation (avg 7/11) would cross and mislabel.
    assert cip_labels("O[C@H](c1ccccc1)C1=CC=CC=[N+]1C") == ("R",)          # phenyl vs N-methylpyridinium
    assert cip_labels("O[C@@H](c1ccccc1)C1=CC=CC=[N+]1C") == ("S",)         # enantiomer flips
    assert cip_labels("O[C@H](c1ccncc1)C1=CC=CC=[N+]1C") == ("R",)          # pyridyl vs pyridinium
    assert cip_labels("O[C@H](C1=CC=CC=[N+]1C)C1=NC=CS1") == ("R",)         # pyridinium vs THIAZOLE (heteroaromatic)
    assert cip_labels("O[C@@H](C1=CC=CC=[N+]1C)C1=NC=CS1") == ("S",)        # enantiomer flips
    assert cip_labels("O[C@H](C1=CC=[N+]([O-])C=C1)C1=NC=CS1") == ("R",)    # N-oxide vs thiazole


def test_out_of_scope_charged_subcases_fail_closed():
    # a wrong R/S is worse than an honest decline: the still-out-of-scope charged classes return {} (an explicit
    # anion / an exotic over-charge decline at the mancude gate), NEVER a silent label.  (The charged AROMATIC
    # spelling this once pinned as a parser wall now NAMES -- ROUND 41's charge-aware kekulizer; the consumer is
    # asserted in tests/test_cip_charge_aware_kekulizer.py.)
    assert cip_labels_by_atom("C[C@H](O)c1cccc[n+]1C") == {1: "S"}  # charged AROMATIC spelling -> NAMED (R41)
    assert cip_labels_by_atom("C[C@H](O)C1=CC=C[CH-]1") == {}       # ANIONIC ring (carbanion) -> no donor branch
    assert cip_labels_by_atom("C[C@H](O)C1=CC=[NH2+]C=C1") == {}    # exotic over-protonated [NH2+] -> declines


def test_chalcogen_cation_rings_fail_closed_dalembert():
    # dalembert R40: a cationic ring CHALCOGEN (pyrylium O+ / thiopyrylium S+) has NO neutral acceptor analogue,
    # so its charge-blind average crosses a real heteroatom and RDKit diverges -- a proven ring-vs-ring mislabel
    # class.  It is DELIBERATELY fail-closed (declines), never a silent wrong label.
    assert cip_labels("C[C@H](O)C1=CC=CC=[O+]1") == ()                     # pyrylium carbinol -> defer
    assert cip_labels("C[C@@H](O)C1=CC=CC=[S+]1") == ()                    # thiopyrylium carbinol -> defer
    assert cip_labels("O[C@H](C1=CC=CC=[S+]1)C1=NC=CS1") == ()             # the dalembert tombstone -> defer


def test_neutral_overvalent_ring_atoms_stay_byte_stable():
    # birdperson R40: the parser accepts a neutral OVERVALENT ring atom the charge>0 guard must keep fail-closed,
    # so its (previously deferred) outcome is byte-identical -- a neutral atom must never reach the cationic branch.
    assert cip_labels("C[C@H](O)C1=CC=N(C)C=C1") == ()             # neutral overvalent ring N [1,1,2]
    assert cip_labels("C[C@H](O)C1=CC=[S]C=C1") == ()             # neutral hypervalent ring S [1,2]


def test_neutral_rings_unchanged_no_regression():
    # the charge-exclusive admission leaves every NEUTRAL ring byte-identical
    assert cip_labels_by_atom("O[C@H](c1ccccc1)c1ccncc1") == {1: "R"}       # neutral mancude averaging
    assert cip_labels("OC(=O)[C@@H]1CCC=CC1") == ("R",)                     # localized ring (R33)
    assert cip_labels("C[C@H](O)C1=CC=CC1=O") == ("S",)                     # R39 exocyclic carbonyl
    assert cip_labels_by_atom("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O") == {3: "S", 6: "R", 9: "R"}  # menthol


def test_structure_theorem_holds():
    probe._assert_structure_theorem()


def test_rdkit_cross_check_zero_mislabels():
    pytest.importorskip("rdkit")
    result = probe._rdkit_cross_check()
    assert result["mismatches"] == 0
    assert result["consumers_named"] >= 12
    assert result["defers_confirmed"] >= 2
    assert result["invariance_ok"] == len(probe._INVARIANCE)
