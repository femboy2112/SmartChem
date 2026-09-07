"""ID-STEREO-CIP-NAMER (ROUND 20): the general CIP R/S namer -- breadth-first hierarchical digraph.

Priority ranking is the hard half of R/S naming.  Two prior attempts (ROUND 13/14) died to a DEPTH-first tie-break;
the fix is CIP Rule 1a done BREADTH-first, branch-by-branch (Hanson et al. 2018).  These tests pin the fix, the
soundness boundary (defer, never guess), and the committed validation harness that carries the full battery + the
combinatorial alkyl pool + the oracle cross-check.  See ``experiments/cip_namer_probe.py`` for the method.
"""
import pytest

from smartchem.smiles import _cip_compare, cip_labels
from experiments import cip_namer_probe as probe


def test_the_committed_harness_validates():
    """The whole five-layer battery (textbook absolutes, oracle cross-check, R14 differential, branch-paired proof,
    combinatorial alkyl pool) passes -- the single anti-regression gate."""
    probe.validate()


def test_the_frozen_hash_is_intact():
    """A tamper pin over every label + priority + oracle-agreement; reddens on any unintended drift."""
    assert probe.content_hash() == probe.FROZEN_HASH, (
        "cip_namer battery drifted -- re-run `python -m experiments.cip_namer_probe` and, if INTENTIONAL, re-freeze"
    )


def test_the_serine_cysteine_flip_is_named_correctly():
    """The discriminator a 'carboxyl always wins' shortcut silently mislabels: same skeleton and ``@@`` tag, OPPOSITE
    label, because cysteine's real S(16) out-ranks the carboxyl's phantom-O(8) at sphere 1."""
    assert cip_labels("C([C@@H](C(=O)O)N)O") == ("S",)          # L-serine
    assert cip_labels("C([C@@H](C(=O)O)N)S") == ("R",)          # L-cysteine -- FLIPS


def test_the_r14_branch_vs_chain_case_is_named_R_not_the_depth_first_S():
    """The exact molecule ROUND-14 got wrong: breadth-first names (R); a depth-first key gives the WRONG (S)."""
    assert cip_labels("C[C@H](CCC)C(C)C") == ("R",)
    assert probe._dfs_labels("C[C@H](CCC)C(C)C") == ("S",)      # the bug, exhibited
    assert cip_labels("C[C@H](CCC)C(C)C") != probe._dfs_labels("C[C@H](CCC)C(C)C")


def test_textbook_absolutes_are_named():
    for smi, expected, note in probe.TEXTBOOK:
        assert cip_labels(smi) == expected, f"{smi}: {note}"


def test_every_named_centre_agrees_with_the_geometric_oracle():
    """Geometry validated independently of ranking: label == geometric_handedness(namer's priorities, sense)."""
    from experiments.cip_geometry_oracle_probe import geometric_handedness
    seen = 0
    for smi, _e, _n in probe.TEXTBOOK:
        for ranks, sense, label in probe._named_centres(smi):
            seen += 1
            assert geometric_handedness(tuple(r + 1 for r in ranks), sense) == label, smi
    assert seen >= len(probe.TEXTBOOK)                          # non-vacuous


def test_the_comparator_is_branch_paired_not_sphere_pooling():
    """On a constructed divergence pair, the correct need-to-know branch-paired order (the deep-deciding high branch
    wins) and a sphere-pooling order DISAGREE; the shipped comparator takes the branch-paired side."""
    assert _cip_compare(probe._DIV_A, probe._DIV_B, probe._ctx()) == 1     # high branch decides deep: A > B
    assert probe._pooled_compare(probe._DIV_A, probe._DIV_B) == -1         # pooling wrongly says B > A


@pytest.mark.parametrize("base,mirror,respell", probe._alkyl_pool()[:120])
def test_named_alkyl_centres_invert_and_are_spelling_invariant(base, mirror, respell):
    """Over the combinatorial alkyl pool (the class the R14 bug hid in): a named centre inverts under enantiomer
    reflection and is invariant under re-spelling (swap two substituents + flip the sense = the same molecule)."""
    lb = cip_labels(base)
    assert lb and lb[0] in ("R", "S")
    assert cip_labels(mirror)[0] != lb[0]                        # enantiomer inverts
    assert cip_labels(respell) == lb                            # re-spelling is invariant


def test_rule_1a_ties_defer_never_guess():
    """Sound, not complete: an isotope-only tie (Rule 2), a false centre (true duplicate), and a ring centre all
    DEFER -- no label -- because a guessed R/S is worse than none."""
    assert cip_labels("C[C@](C)(N)O") == ()                     # twin methyls: false centre
    assert cip_labels("CC[C@](CC)(N)O") == ()                   # twin ethyls
    assert cip_labels("F[C@@](Cl)([2H])[3H]") == ()             # isotope-only tie
    assert cip_labels("N[C@]1(F)CCCCO1") == ()                  # ring stereocentre (acyclic scope)


def test_an_aromatic_digraph_defers_never_a_fixed_kekule_guess():
    """Correct Rule 1a on a mancude ring needs Kekule-invariant atomic-number averaging (unbuilt).  A single fixed
    Kekule structure would MISLABEL an aryl centre, so any centre whose digraph reaches an aromatic atom defers.
    The di-2-pyridyl carbinol is the soundness pin: two identical 2-pyridyls = a FALSE centre; before this guard a
    fixed Kekule split them and named a spurious (R)."""
    assert cip_labels("O[C@H](c1ccccn1)c1ccccn1") == ()         # false centre -- MUST defer (was wrongly named (R))
    assert cip_labels("C[C@H](N)c1ccccc1") == ()                # a genuine aryl centre also defers (sound, incomplete)


def test_an_aromatic_ring_in_a_branch_decided_by_atomic_number_does_not_spuriously_defer():
    """evil-morty finding #1: a ranking decided by atomic number BEFORE the aromatic ring is relevant must NAME, not
    defer.  The styryl centre (aromatic ring two bonds past a vinyl the sphere already decides) must give the SAME
    label as its tert-butyl twin -- the only difference is the ring, which never enters the tiebreak."""
    aromatic = cip_labels("Cl[C@H](C)C=Cc1ccccc1")             # vinyl-C {C,C,H} > CH3 decides; ring irrelevant
    aliphatic = cip_labels("Cl[C@H](C)C=CC(C)(C)C")            # identical skeleton, tBu for phenyl
    assert aromatic and aromatic == aliphatic == ("R",)         # names, and the ring did not change the answer


def test_the_distinct_z_slice_is_unchanged():
    """A strict extension: on four distinct-atomic-number neighbours the digraph decides at sphere 0, byte-identical
    to the prior descending-atomic-number ranks."""
    assert cip_labels("[C@H](F)(Cl)Br") == ("S",)
    assert cip_labels("[C@@H](F)(Cl)Br") == ("R",)
