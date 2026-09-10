"""CIP-CHARGE-AWARE-KEKULIZER-01: ROUND 41 build (queue item q1) -- a charged AROMATIC-spelling ring now NAMES
and unifies with its explicit-Kekulé spelling.

R40 named the cationic-ring-N heterocycle in EXPLICIT-KEKULÉ form but WALLED the natural aromatic spelling
(``c1cccc[n+]1C``) at ``_aromatic_matchings`` (a cationic ring N was misclassified as a pyrrole-type donor).  R41
gives the classifier a FAIL-CLOSED CHARGE WHITELIST admitting exactly the cationic ring N as a pi-acceptor; every
other charged aromatic atom (chalcogen cation, anion, exotic) fails closed with a loud raise.  Admitting the
charged aromatic spelling also exposed and fixed a LATENT resonance-canonicaliser false-split: a molecule mixing
an aromatic ring with an explicit-Kekulé charged ring got a different canonical identity than its uniform
spellings.  All three canonicalisation functions now share ``_canonical_kekule_orders``, so the aromatic, explicit
and mixed spellings of one molecule are ONE identity.  These tests pin the RDKit-free build; the gated cross-check
confirms 0 mislabels + aromatic/explicit unification when RDKit is present (dev venv only).
"""
from __future__ import annotations

import pytest

from experiments import cip_charge_aware_kekulizer_probe as probe
from smartchem.smiles import (SmilesError, canonical_digest, cip_labels, cip_labels_by_atom, parse_smiles)


def _dg(smi):
    return canonical_digest(parse_smiles(smi).canonical())


def test_probe_validates_and_frozen_hash_stable():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


def test_charged_aromatic_spelling_now_names_matching_the_oracle():
    # the natural aromatic spelling of the R40 cationic-ring-N class now names (was a parser wall)
    assert cip_labels_by_atom("C[C@H](O)c1cccc[n+]1C") == {1: "S"}       # N-methylpyridinium
    assert cip_labels_by_atom("C[C@@H](O)c1cccc[n+]1C") == {1: "R"}      # enantiomer flips
    assert cip_labels_by_atom("C[C@H](O)c1cc[nH+]cc1") == {1: "S"}       # protonated pyridinium (N-H)
    assert cip_labels_by_atom("C[C@@H](O)c1scc[n+]1C") == {1: "R"}       # thiazolium
    assert cip_labels_by_atom("C[C@H](O)c1[nH]cc[n+]1C") == {1: "S"}     # imidazolium
    assert cip_labels_by_atom("C[C@H](O)c1cc[n+]([O-])cc1") == {1: "S"}  # pyridine N-oxide


def test_aromatic_spelling_unifies_with_explicit_kekule_identity():
    # the R41 representation-invariance guarantee: aromatic and explicit spellings of ONE molecule share identity
    pairs = [
        ("C[C@H](O)c1cccc[n+]1C", "C[C@H](O)C1=CC=CC=[N+]1C"),
        ("C[C@H](O)c1cc[nH+]cc1", "C[C@H](O)C1=CC=[NH+]C=C1"),
        ("C[C@@H](O)c1scc[n+]1C", "C[C@@H](O)C1=[N+](C)C=CS1"),
    ]
    for arom, expl in pairs:
        assert _dg(arom) == _dg(expl), f"aromatic/explicit split: {arom} vs {expl}"


def test_mixed_aromatic_explicit_charged_ring_unifies_r41_falsesplit():
    # the exact bug R41 fixed: pyridyl(aromatic) + pyridinium(explicit) mixed spelling once split from its uniform
    # spellings; all three are now ONE identity AND one CIP label.
    spellings = [
        "C[n+]1ccccc1[C@H](O)c1ccncc1",         # both aromatic
        "O[C@H](c1ccncc1)C1=CC=CC=[N+]1C",       # pyridyl aromatic / pyridinium explicit (the mixed split)
        "O[C@H](C1=CC=NC=C1)C1=CC=CC=[N+]1C",    # both explicit
    ]
    assert len({_dg(s) for s in spellings}) == 1
    assert len({tuple(sorted(cip_labels_by_atom(s).values())) for s in spellings}) == 1


def test_charged_ring_vs_ring_aromatic_spelling():
    # ring-vs-ring in aromatic spelling: the charged ring's averaged fractions decide (dalembert regime)
    assert cip_labels_by_atom("C[n+]1ccccc1[C@H](O)c1ccccc1") == {7: "R"}   # phenyl vs pyridinium
    assert cip_labels_by_atom("C[n+]1ccccc1[C@@H](O)c1ccccc1") == {7: "S"}  # enantiomer flips
    assert cip_labels_by_atom("C[n+]1ccccc1[C@@H](O)c1nccs1") == {7: "R"}   # pyridinium vs thiazole


def test_chalcogen_cation_and_anion_aromatic_fail_closed():
    # a wrong Kekulé structure is worse than a loud refusal: the dalembert-divergent chalcogen cation and any
    # anion must RAISE (never silently mis-kekulise via the O/S donor branch on an even acceptor count).
    for smi in ["C[C@H](O)c1cccc[o+]1",       # pyrylium (O+)
                "C[C@@H](O)c1cccc[s+]1",       # thiopyrylium (S+)
                "C[C@H](O)c1ccc[cH-]1",        # cyclopentadienide (C-)
                "O[C@H](c1ccccc1)c1ccc[n-]c1"]:  # anionic ring N
        with pytest.raises(SmilesError, match="charged aromatic atom"):
            cip_labels_by_atom(smi)


def test_over_charged_nitrogen_fails_closed_r41_review():
    # R41-review tightening: the whitelist admits ONLY a formal +1 ring N of coordination 3, matching RDKit's own
    # valence rejection.  An OVER-CHARGED [n+2] or OVER-COORDINATED [nH2+] aromatic N is not a real molecule
    # (RDKit's MolFromSmiles returns None), so we must never NAME it -- the aromatic path RAISES, and the explicit
    # path declines ({}), never a silent label on a non-molecule.
    for smi in ["C[C@H](O)c1cccc[n+2]1C", "C[C@H](O)c1cccc[nH2+]1"]:
        with pytest.raises(SmilesError, match="charged aromatic atom"):
            cip_labels_by_atom(smi)                              # aromatic over-charge -> fail closed at parse
    assert cip_labels_by_atom("C[C@H](O)C1=CC=CC=[N+2]1C") == {}  # explicit [N+2] -> declines at the mancude gate
    assert cip_labels_by_atom("C[C@H](O)C1=CC=[NH2+]C=C1") == {}  # explicit [NH2+] -> declines


def test_neutral_aromatics_byte_stable_no_regression():
    # the shared kekuliser is byte-identical for every neutral molecule (the SPLIT-KEKULE red-team stays green)
    assert _dg("c1ccccc1") == _dg("C1=CC=CC=C1")
    assert _dg("c1ccc2ccccc2c1") == _dg("C1=CC2=CC=CC=C2C=C1")          # naphthalene aromatic == explicit
    assert _dg("c1ccncc1") == _dg("C1=CC=NC=C1")
    assert cip_labels_by_atom("O[C@H](c1ccccc1)c1ccncc1") == {1: "R"}    # neutral averaging path, untouched
    assert cip_labels("[C@H](F)(Cl)Br") == ("S",)                        # ordinary naming untouched


def test_structure_theorem_holds():
    probe._assert_representation_invariance()


def test_rdkit_cross_check_zero_mislabels():
    pytest.importorskip("rdkit")
    result = probe._rdkit_cross_check()
    assert result["mismatches"] == 0
    assert result["consumers_named"] >= 10
    assert result["consumers_unified_aromatic_vs_explicit"] == result["consumers_named"]
    assert result["defers_confirmed"] >= 2
