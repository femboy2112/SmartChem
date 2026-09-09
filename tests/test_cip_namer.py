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
    """The whole five-layer battery (textbook absolutes, oracle cross-check, R14 differential, FIFO-queue proof,
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


def test_the_comparator_uses_the_hanson_mayfield_fifo_pair_queue():
    """A lower branch's shallow difference precedes a higher branch's deeper generation (the old recursion reversed it)."""
    assert _cip_compare(probe._DIV_A, probe._DIV_B, probe._ctx()) == -1
    assert probe._queued_compare_reference(probe._DIV_A, probe._DIV_B) == -1


def test_rule_1a_adversarial_mislabels_stay_fixed():
    """The concrete acyclic/ring/polyene families that exposed the recursive-top-branch traversal defect."""
    for smi, expected, note in probe.ADVERSARIAL_RULE1A:
        assert cip_labels(smi) == expected, f"{smi}: {note}"


@pytest.mark.parametrize("base,mirror,respell", probe._alkyl_pool()[:120])
def test_named_alkyl_centres_invert_and_are_spelling_invariant(base, mirror, respell):
    """Over the combinatorial alkyl pool (the class the R14 bug hid in): a named centre inverts under enantiomer
    reflection and is invariant under re-spelling (swap two substituents + flip the sense = the same molecule)."""
    lb = cip_labels(base)
    assert lb and lb[0] in ("R", "S")
    assert cip_labels(mirror)[0] != lb[0]                        # enantiomer inverts
    assert cip_labels(respell) == lb                            # re-spelling is invariant


def test_true_duplicate_ties_defer_but_ring_centres_now_name():
    assert cip_labels("C[C@](C)(N)O") == ()                     # twin methyls: false centre
    assert cip_labels("CC[C@](CC)(N)O") == ()                   # twin ethyls
    assert cip_labels("N[C@]1(F)CCCCO1") == ("R",)             # ROUND 35 written-order ring parity


def test_rule_2_isotope_mass_breaks_ties():
    """ROUND 28 -- CIP Rule 2 (mass number) breaks a same-Z tie Rule 1a leaves, in the Rule-1a-established order.
    Higher mass ranks higher; a specified isotope carries its mass number, an unspecified atom the CIAAW standard
    weight (so protium [1H]=1 < natural H=1.008 < [2H]=2 < [3H]=3).  Sound-not-complete: where the Rule-2 pairing
    is ambiguous (Rule-1a-tied siblings) the centre still DEFERS, never guesses."""
    assert cip_labels("F[C@@](Cl)([2H])[3H]") == ("R",)         # sphere-0: Cl>F>[3H]>[2H]
    assert cip_labels("F[C@](Cl)([2H])[3H]") == ("S",)          # enantiomer inverts
    assert cip_labels("F[C@@](Cl)([1H])[2H]") == ("R",)         # protium [1H] < [2H]
    assert cip_labels("[2H]O[C@@](Br)(Cl)O[3H]") == ("S",)      # sphere-1: -O[3H] > -O[2H] one sphere in
    assert cip_labels("[2H]O[C@](Br)(Cl)O[3H]") == ("R",)       # enantiomer inverts
    # ROUND-28 evil-morty fold: Rule 2 NAMES multi-sphere ties too (not just sphere-0/1) -- pin sphere-2/3 so a
    # traversal refactor cannot silently reverse a deep mass verdict (both blind-sign-checked by the oracle).
    assert cip_labels("FC(F)O[C@@](Br)(Cl)O[13CH](F)F") == ("S",)   # sphere-2: [13C] vs C at the far carbon
    assert cip_labels("FC(F)O[C@](Br)(Cl)O[13CH](F)F") == ("R",)
    assert cip_labels("F[13C](F)CO[C@@](Br)(Cl)OCC(F)F") == ("S",)  # sphere-3
    assert cip_labels("F[13C](F)CO[C@](Br)(Cl)OCC(F)F") == ("R",)
    # Cumulative Rules-1a/1b/2 child ordering makes this pairing deterministic; RDKit 2026.3.6 agrees.
    assert cip_labels("[C@@](Br)(Cl)(C[2H])C[3H]") == ("S",)


def test_mancude_averaging_names_aryl_but_keeps_identical_pyridyls_tied():
    """A single fixed Kekule structure split two identical 2-pyridyls into a false centre.
    Exact duplicate-Z averaging must preserve that tie while naming an ordinary aryl centre."""
    assert cip_labels("O[C@H](c1ccccn1)c1ccccn1") == ()         # false centre -- MUST defer (was wrongly named (R))
    assert cip_labels("C[C@H](N)c1ccccc1") == ("S",)


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
