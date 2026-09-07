"""ROUND-13 item 4b (ID-STEREO-01): CIP R/S NAMING for the soundly-nameable stereocentre slice.

``cip_labels`` names ONLY a tetrahedral centre whose four directly-bonded atoms differ by atomic number alone --
there CIP priority is exactly descending atomic number, so the notorious recursive hierarchical-digraph tie-break is
categorically irrelevant.  Every other centre (two same-element substituents -- the COMMON case: amino acids, sugars,
any secondary/tertiary carbon; a ring centre; an E/Z bond) is a NAMED DEFERRAL and gets NO label, because a half-built
CIP that guessed those would emit an UNSOUND R/S (worse than none).

The load-bearing risk (the recon's warning): a globally-FLIPPED sign convention passes every RELATIVE test (enantiomers
still differ, spellings still agree) -- so the convention is pinned by an ABSOLUTE anchor to a KNOWN truth, L-alanine =
(S), re-derived here rather than asserted from memory.
"""
from smartchem.smiles import cip_labels, parse_smiles
from smartchem.contracts import canonical_digest


def _perm_parity(seq):
    inv = 0
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            if seq[i] > seq[j]:
                inv += 1
    return inv & 1


def test_the_sign_convention_is_anchored_to_L_alanine_S_not_asserted_from_memory():
    """The ABSOLUTE anchor (catches a globally-flipped convention that every relational test would miss).

    L-alanine ``N[C@@H](C)C(=O)O`` is textbook (S).  Its stereocentre's written neighbour order is
    [N, H, CH3, COOH] with CIP priority ranks [1, 4, 3, 2] (N > COOH-carbon > CH3-carbon > H) and sense ``@@`` (bit 1).
    So ``perm_parity([1,4,3,2]) ^ 1`` is the handedness bit that MUST correspond to (S).  We re-derive it here and
    require the convention (handedness 0 -> S) to be exactly the one ``cip_labels`` uses on the distinct-Z slice:
    ``[C@H](F)(Cl)Br`` computes the SAME handedness 0 and so must be named (S).
    """
    alanine_handedness = _perm_parity([1, 4, 3, 2]) ^ 1          # @@ = sense bit 1
    assert alanine_handedness == 0                               # ... and textbook L-alanine is (S), so 0 <-> S
    # the distinct-Z slice member that computes handedness 0 is therefore (S):
    assert cip_labels("[C@H](F)(Cl)Br") == ("S",)               # bromochlorofluoromethane, @  -> (S)
    assert cip_labels("[C@@H](F)(Cl)Br") == ("R",)              # its mirror -> (R)


def test_enantiomers_get_opposite_labels():
    assert cip_labels("[C@H](F)(Cl)Br") != cip_labels("[C@@H](F)(Cl)Br")
    assert set(cip_labels("[C@H](F)(Cl)Br")) | set(cip_labels("[C@@H](F)(Cl)Br")) == {"R", "S"}


def test_labels_are_spelling_invariant_for_one_enantiomer():
    # swapping two neighbours AND flipping the sense is the SAME physical molecule (OpenSMILES) -> SAME label.
    for a, b in [("[C@H](F)(Cl)Br", "F[C@@H](Cl)Br"), ("[C@@H](F)(Cl)Br", "F[C@H](Cl)Br")]:
        assert canonical_digest(parse_smiles(a).canonical()) == canonical_digest(parse_smiles(b).canonical())
        assert cip_labels(a) == cip_labels(b)


def test_a_centre_with_two_same_element_substituents_is_now_named_by_the_general_digraph():
    # ROUND 20: the COMMON case the distinct-Z slice deferred is now NAMED by the Rule-1a breadth-first digraph --
    # ties break one or more spheres out.  Labels are textbook/PubChem-checked and oracle-cross-validated in
    # tests/test_cip_namer.py; here they pin that the same-element centre no longer silently defers.
    assert cip_labels("N[C@@H](C)C(=O)O") == ("S",)             # L-alanine: COOH's phantom-O {O,O,O} beats CH3 {H,H,H}
    assert cip_labels("OC[C@@H](O)C=O") == ("R",)               # D-glyceraldehyde: CHO's phantom-O beats CH2OH


def test_an_aromatic_substituent_is_named_with_kekule_invariant_averaging():
    # Neutral mancude averaging now names the aryl centre; equal pyridyls remain equal.
    assert cip_labels("C[C@H](N)c1ccccc1") == ("S",)
    assert cip_labels("O[C@H](c1ccccn1)c1ccccn1") == ()          # di-2-pyridyl: a FALSE centre a fixed Kekule would name


def test_ring_and_false_and_achiral_centres_get_no_label():
    assert cip_labels("N[C@]1(F)CCCCO1") == ()                   # ring stereocentre -> deferred (out of acyclic scope)
    assert cip_labels("C[C@](C)(N)O") == ()                      # false centre (two identical methyls)
    assert cip_labels("CCO") == ()                               # achiral
    assert cip_labels("CC(=O)Nc1ccc(O)cc1") == ()                # paracetamol: achiral, no label


def test_multiple_distinct_z_centres_are_each_named():
    # a molecule with two independent distinct-Z stereocentres joined by a spacer: both named, sorted.
    labels = cip_labels("Br[C@H](F)O[C@@H](F)Cl")
    assert len(labels) == 2 and set(labels) <= {"R", "S"}


def test_the_branch_vs_chain_family_is_named_breadth_first_never_the_r14_depth_first_answer():
    """ROUND-20: the branch-vs-chain family that killed the ROUND-14 depth-first attempt is now NAMED correctly by the
    breadth-first hierarchical digraph.  A naive nested-tuple LEXICOGRAPHIC key compares DEPTH-first and emits the WRONG
    label; true CIP Rule 1a is BREADTH-first (sphere-by-sphere).  For ``C[C@H](CCC)C(C)C`` (n-propyl vs isopropyl) the
    DFS key emits (S), but the truth is (R) -- isopropyl's first carbon (C,C,H) out-ranks n-propyl's (C,H,H) AT the
    sphere, the decision DFS defers past by descending the longer chain first.  All three labels are hand-derived via
    the pinned convention and oracle-cross-validated in tests/test_cip_namer.py; this pins the FIX, so nobody re-ships
    the naive DFS digraph (which would flip C[C@H](CCC)C(C)C to S)."""
    assert cip_labels("C[C@H](CCC)C(C)C") == ("R",)       # n-propyl vs isopropyl -- (R), the DFS answer (S) is WRONG
    assert cip_labels("C[C@H](CCC)C(C)CC") == ("R",)      # sec-butyl vs n-propyl -- (R)
    assert cip_labels("CCCC[C@H](CC(C)C)C") == ("R",)     # isobutyl vs n-butyl -- (R), the tie breaks at sphere 2
    # and the distinct-Z base case is unchanged (a strict extension, never a regression).
    assert cip_labels("[C@H](F)(Cl)Br") == ("S",)


def test_malformed_input_raises_like_the_parser():
    import pytest
    from smartchem.smiles import SmilesError
    with pytest.raises(SmilesError):
        cip_labels("")
    with pytest.raises(SmilesError):
        cip_labels("not a smiles [[[")
