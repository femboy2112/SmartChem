"""CIP-ORACLE-01 (queue item 1): the INDEPENDENT geometric handedness oracle.

The roadmap's general-CIP gate is oracle-first ("the wall isn't the namer -- it's the oracle"; the namer was
built and discarded twice because its cross-check was common-mode with the code it audited).  This battery
pins the committed oracle: the two ABSOLUTE textbook anchors that fix the sign convention (a globally-flipped
convention passes every relational test, so it must be pinned to a known truth), its exhaustive agreement
with the shipped distinct-Z slice by a genuinely DIFFERENT computation (real coordinates + a signed volume,
not a permutation parity), and -- the reason it is worth committing -- its ability to label a centre GIVEN
priorities where the shipped slice defers, which is the ground-truth property a future breadth-first namer
must be validated against.
"""
from __future__ import annotations

import pytest

from experiments.cip_geometry_oracle_probe import (
    FROZEN_HASH,
    content_hash,
    geometric_handedness,
    oracle_labels,
)
from experiments.cip_geometry_oracle_probe import validate as validate_oracle
from smartchem.smiles import cip_labels


# --- the absolute anchors: a flipped convention would pass every relational test but die here -------

def test_the_two_textbook_anchors_pin_the_sign_convention_S_for_both():
    # ONE derived convention (signed volume V > 0 -> S) must reproduce BOTH known (S) molecules -- a
    # distinct-Z one and a same-Z one -- or it was tuned, not derived.
    assert geometric_handedness((4, 3, 2, 1), 1) == "S"       # [C@H](F)(Cl)Br  (Br>Cl>F>H, @)  = (S)
    assert geometric_handedness((1, 4, 3, 2), 2) == "S"       # L-alanine (N>COOH-C>CH3-C>H, @@) = (S)


def test_each_anchor_inverts_with_its_enantiomer():
    assert geometric_handedness((4, 3, 2, 1), 2) == "R"       # [C@@H](F)(Cl)Br = (R)
    assert geometric_handedness((1, 4, 3, 2), 1) == "R"       # D-alanine = (R)


# --- the independent computation agrees with the shipped slice across the whole battery -------------

def test_the_oracle_agrees_with_the_shipped_distinct_z_slice_exhaustively():
    # validate() asserts oracle_labels == cip_labels over all 48 {F,Cl,Br,I} orderings + the anchors, and
    # that the battery is non-vacuous (both R and S occur).  A single call re-runs the whole battery.
    validate_oracle()


def test_the_oracle_and_the_shipped_slice_are_two_methods_one_answer():
    # spot-check the agreement directly (not only through validate) on a bare four-halogen centre and a
    # two-centre molecule: same labels, computed by geometry here vs by perm_parity in smartchem.smiles.
    for s in ("[C@](F)(Cl)(Br)I", "[C@@](F)(Cl)(Br)I", "Br[C@H](F)O[C@@H](F)Cl"):
        assert oracle_labels(s) == cip_labels(s) and oracle_labels(s)


def test_enantiomeric_smiles_get_opposite_oracle_labels():
    assert oracle_labels("[C@H](F)(Cl)Br") == ("S",)
    assert oracle_labels("[C@@H](F)(Cl)Br") == ("R",)


# --- the ground-truth property: it labels what the shipped slice DEFERS, given priorities ------------

def test_the_oracle_and_the_now_built_namer_agree_on_a_same_z_centre():
    # THE reason this oracle was committed: it decoupled "are the priorities right" (the namer's job, the R14
    # bug locus) from "is the geometry right" (this oracle), so the general namer could be BUILT against it.
    # ROUND 20 did exactly that -- cip_labels now NAMES L-alanine (S) via the breadth-first digraph -- and the
    # oracle, HANDED the true CIP priorities [N > COOH > CH3 > H], returns the SAME (S) from geometry alone.
    assert cip_labels("N[C@@H](C)C(=O)O") == ("S",)          # the general namer now ranks the same-Z centre
    assert geometric_handedness((1, 4, 3, 2), 2) == "S"       # and the oracle agrees from geometry, given priorities


# --- honest scope of the "independence" (an adversarial review right-sized this) --------------------

def test_the_full_pipeline_agrees_with_external_textbook_absolutes():
    # the one genuinely-independent bit: parse a molecule of KNOWN external absolute configuration through
    # the FULL stack and check the label against the TEXTBOOK answer (OpenSMILES @ + CIP -> [C@H](F)(Cl)Br is
    # (S), its mirror (R)), NOT against cip_labels.  This is the external-ground-truth check for the shared
    # parser sense->order convention (the seam that has no RDKit oracle in the dependency-light core).
    assert oracle_labels("[C@H](F)(Cl)Br") == ("S",)          # textbook bromochlorofluoromethane, @  = (S)
    assert oracle_labels("[C@@H](F)(Cl)Br") == ("R",)         # its enantiomer = (R)


def test_the_oracle_is_algebraically_perm_parity_xor_sense_not_an_extra_bearing():
    # HONEST pin of what the red-team proved: geometric_handedness is the SAME group-theoretic quantity as the
    # shipped `_perm_parity(ranks) ^ sense` (signed volume of permuted vertices is alternating; the base
    # tetrahedron's global sign is +, so V>0 <-> even permutation <-> S).  So the 48-case sweep confirms ONE
    # constant, not 48 bearings -- pinning this stops anyone re-inflating the "two independent methods" claim.
    from itertools import permutations

    def _parity(seq):
        inv = sum(1 for i in range(len(seq)) for j in range(i + 1, len(seq)) if seq[i] > seq[j])
        return inv & 1

    for priorities in permutations((1, 2, 3, 4)):
        ranks = [p - 1 for p in priorities]                   # 0 = highest, as the shipped code encodes it
        for sense in (1, 2):
            handedness = _parity(ranks) ^ (0 if sense == 1 else 1)   # the shipped mapping
            shipped_label = "S" if handedness == 0 else "R"
            assert geometric_handedness(priorities, sense) == shipped_label


# --- fail-closed input discipline -------------------------------------------------------------------

def test_non_permutation_priorities_are_refused_never_guessed():
    for bad in ((1, 1, 2, 3), (0, 1, 2, 3), (1, 2, 3), (1, 2, 3, 5)):
        with pytest.raises(ValueError, match="permutation"):
            geometric_handedness(bad, 1)


def test_a_sense_other_than_the_two_tetrahedral_bits_is_refused():
    with pytest.raises(ValueError, match="sense"):
        geometric_handedness((1, 2, 3, 4), 0)


# --- the committed harness --------------------------------------------------------------------------

def test_the_committed_harness_validates_and_its_hash_is_frozen():
    validate_oracle()
    assert content_hash() == FROZEN_HASH
