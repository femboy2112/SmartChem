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


def test_a_centre_with_two_same_element_substituents_is_a_named_deferral():
    # the COMMON case -- CIP priority there needs the recursive digraph tie-break, which is NOT built, so NO label
    # (never a guessed/unsound one).  Alanine, glyceraldehyde: both have two carbons on the centre.
    assert cip_labels("N[C@@H](C)C(=O)O") == ()                  # L-alanine
    assert cip_labels("OC[C@@H](O)C=O") == ()                    # glyceraldehyde
    assert cip_labels("C[C@H](N)c1ccccc1") == ()                 # 1-phenylethylamine (two carbons: CH3 and phenyl)


def test_ring_and_false_and_achiral_centres_get_no_label():
    assert cip_labels("N[C@]1(F)CCCCO1") == ()                   # ring stereocentre -> deferred (out of acyclic scope)
    assert cip_labels("C[C@](C)(N)O") == ()                      # false centre (two identical methyls)
    assert cip_labels("CCO") == ()                               # achiral
    assert cip_labels("CC(=O)Nc1ccc(O)cc1") == ()                # paracetamol: achiral, no label


def test_multiple_distinct_z_centres_are_each_named():
    # a molecule with two independent distinct-Z stereocentres joined by a spacer: both named, sorted.
    labels = cip_labels("Br[C@H](F)O[C@@H](F)Cl")
    assert len(labels) == 2 and set(labels) <= {"R", "S"}


def test_the_general_cip_digraph_wall_defers_branch_vs_chain_never_mislabels_it():
    """ROUND-14 item-4b REFUTATION tripwire: a naive hierarchical-digraph CIP (nested-tuple LEXICOGRAPHIC key ordering)
    is UNSOUND -- it compares DEPTH-first, but true CIP Rule 1a is BREADTH-first (sphere-by-sphere).  The two total
    orders disagree on the common branch-vs-chain alkyl motif: for ``C[C@H](CCC)C(C)C`` (n-propyl vs isopropyl), a DFS
    key emits (S) but the truth is (R) -- isopropyl's first carbon carries (C,C,H) and out-ranks n-propyl's (C,H,H) at
    the sphere, a decision DFS wrongly defers past by descending the longer chain first (evil-morty, ROUND-14; verified
    against a breadth-first oracle: 740 order-flips in an alkyl-only pool).

    A correct general CIP needs the full breadth-first hierarchical comparison + phantom-0 padding + aromatic/Rule-1b
    handling, a large correctness-critical build we cannot exhaustively validate WITHOUT an independent oracle (RDKit is
    out of the dependency-light core), and a WRONG R/S in a chemist's dossier is worse than none.  So the general CIP is
    a NAMED DEFERRAL and the SOUND distinct-atomic-number slice stands: this tripwire pins that the branch-vs-chain
    family gets NO label (fail-closed), so nobody re-ships the naive DFS digraph as a fresh idea."""
    # every one of these WOULD be mislabelled by a lexicographic-key digraph; the sound slice DEFERS them all.
    assert cip_labels("C[C@H](CCC)C(C)C") == ()           # n-propyl vs isopropyl -- the fully-worked counterexample
    assert cip_labels("C[C@H](CCC)C(C)CC") == ()          # sec-butyl vs n-propyl
    assert cip_labels("CCCC[C@H](CC(C)C)C") == ()         # isobutyl vs n-butyl
    # and the sound slice still NAMES what it can prove (the distinct-Z base case), so it is not vacuously safe.
    assert cip_labels("[C@H](F)(Cl)Br") == ("S",)


def test_malformed_input_raises_like_the_parser():
    import pytest
    from smartchem.smiles import SmilesError
    with pytest.raises(SmilesError):
        cip_labels("")
    with pytest.raises(SmilesError):
        cip_labels("not a smiles [[[")
