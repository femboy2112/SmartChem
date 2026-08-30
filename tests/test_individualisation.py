"""#25 -- individualisation canonicalisation: the second nauty move, verified by brute force.

This is the one change where a silent error corrupts *every* graph equality in the category, so
it is not trusted, it is PROVEN, three ways:

* **Soundness.** The individualised canonical form of benzene is a GENUINE relabelling of benzene
  -- reachable as some within-cell permutation of the input, so the graph was never corrupted,
  only re-spelled. (It need not be the global edge-minimum: individualisation minimises over the
  leaves of its search tree, a relabel-invariant subset, not over all 518,400 labellings -- and
  it does not have to, because this branch is reached only where no prior canonical form existed.)
* **Completeness (relabel-invariance).** The property that actually matters: a molecule and every
  relabelling of it canonicalise to one identical form. Checked on benzene and cyclohexane under
  random relabellings -- if the individualisation choice leaked into the answer, these diverge.
* **Additivity.** Molecules that canonicalised before #25 never reach this branch (their symbol/
  colour cost is under budget), so no canonical form that existed before can move -- the whole
  rest of the suite is the regression proof; here we just assert the branch really is skipped.
"""

import random
from itertools import permutations, product

from smartchem.category import (
    _MAX_CANONICAL_CANDIDATES,
    _blocks,
    _canonical_blocks,
    _cost_of,
    _wl_colours,
    Bond,
    Molecule,
)


# -- fixtures ---------------------------------------------------------------------------
def _benzene() -> Molecule:
    """Kekule benzene C6H6: a 6-ring of alternating single/double C-C bonds, one H per C.

    Every carbon sees exactly {double-C, single-C, H}, so WL colours them one 6-cell -- 6! x 6!
    = 518,400 candidates, over budget, refinement powerless. The individualisation case.
    """
    atoms = ("C",) * 6 + ("H",) * 6
    ring = [Bond(0, 1, 2), Bond(1, 2, 1), Bond(2, 3, 2),
            Bond(3, 4, 1), Bond(4, 5, 2), Bond(5, 0, 1)]
    hydrogens = [Bond(c, 6 + c, 1) for c in range(6)]
    return Molecule(atoms, frozenset(ring + hydrogens))


def _cyclohexane() -> Molecule:
    """C6H12: an all-single 6-ring, two H per carbon -- a bigger automorphism group (ring x the
    two-H swap at each carbon), far over budget and not brute-forceable, a relabel-invariance case."""
    atoms = ("C",) * 6 + ("H",) * 12
    ring = [Bond(c, (c + 1) % 6, 1) for c in range(6)]
    hydrogens = [Bond(c, 6 + 2 * c, 1) for c in range(6)] + [Bond(c, 7 + 2 * c, 1) for c in range(6)]
    return Molecule(atoms, frozenset(ring + hydrogens))


def _ethanol() -> Molecule:
    # C-C-O with the hydrogens; a species the cheap path handles -- must NOT reach individualisation
    atoms = ("C", "C", "O", "H", "H", "H", "H", "H", "H")
    bonds = [Bond(0, 1, 1), Bond(1, 2, 1),
             Bond(0, 3, 1), Bond(0, 4, 1), Bond(0, 5, 1),
             Bond(1, 6, 1), Bond(1, 7, 1), Bond(2, 8, 1)]
    return Molecule(atoms, frozenset(bonds))


def _relabel(m: Molecule, perm: list[int]) -> Molecule:
    """The molecule with atom i moved to position perm[i] -- an isomorphic respelling."""
    n = len(m.atoms)
    atoms: list[str] = [""] * n
    for old, new in enumerate(perm):
        atoms[new] = m.atoms[old]
    bonds = frozenset(Bond(perm[b.i], perm[b.j], b.order) for b in m.bonds)
    return Molecule(tuple(atoms), bonds, m.charge, m.state)


def _is_reachable_relabelling(m: Molecule, candidate: Molecule) -> bool:
    """True iff ``candidate`` is some within-WL-cell relabelling of ``m`` -- an isomorphism oracle.

    Enumerates every permutation that shuffles atoms within their WL colour class (the same set
    :meth:`Molecule.canonical` searches) and asks whether any of them turns ``m`` into
    ``candidate``'s exact edge set. If one does, ``candidate`` is a genuine respelling of ``m``:
    the canonicaliser re-labelled the graph, it did not corrupt it. 518,400 candidates for benzene.
    """
    atoms, bonds, n = m.atoms, m.bonds, len(m.atoms)
    if candidate.atoms != tuple(atoms[i] for cell in _blocks(_wl_colours(atoms, bonds)) for i in cell):
        return False
    blocks = _blocks(_wl_colours(atoms, bonds))
    targets, pos = [], 0
    for cell in blocks:
        targets.append(tuple(range(pos, pos + len(cell))))
        pos += len(cell)
    want = candidate.bonds
    for choice in product(*(permutations(cell) for cell in blocks)):
        perm = [0] * n
        for olds, news in zip(choice, targets):
            for old, new in zip(olds, news):
                perm[old] = new
        edges = frozenset(
            Bond(perm[b.i], perm[b.j], b.order) for b in bonds
        )
        if edges == want:
            return True
    return False


# -- the proofs -------------------------------------------------------------------------
def test_benzene_now_canonicalises_at_all():
    # pre-#25 this raised NotImplementedError; the whole point is that it no longer does
    canon = _benzene().canonical()
    assert canon.formula == {"C": 6, "H": 6}


def test_benzene_is_over_budget_so_it_exercises_individualisation():
    b = _benzene()
    assert _cost_of(_canonical_blocks(b.atoms, b.bonds)) > _MAX_CANONICAL_CANDIDATES


def test_benzene_canonical_is_a_genuine_relabelling_not_a_corrupted_graph():
    b = _benzene()
    assert _is_reachable_relabelling(b, b.canonical())   # sound: isomorphic to the input


def test_over_budget_canonical_is_relabel_invariant():
    for mol in (_benzene(), _cyclohexane()):
        base = mol.canonical()
        rng = random.Random(20260830)
        for _ in range(40):
            perm = list(range(len(mol.atoms)))
            rng.shuffle(perm)
            assert _relabel(mol, perm).canonical() == base


def test_relabel_invariance_holds_symbols_and_bonds_exactly():
    # not just "equal Molecule" -- the atoms tuple and the bond set are identical, byte for byte
    b = _benzene()
    base = b.canonical()
    rng = random.Random(7)
    for _ in range(10):
        perm = list(range(12))
        rng.shuffle(perm)
        c = _relabel(b, perm).canonical()
        assert c.atoms == base.atoms
        assert c.bonds == base.bonds


def test_additive_small_molecules_never_reach_the_individualisation_branch():
    # ethanol/water take the cheap path unchanged; the full suite is the real additivity regression
    for m in (_ethanol(),
              Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))):
        assert _cost_of(_canonical_blocks(m.atoms, m.bonds)) <= _MAX_CANONICAL_CANDIDATES
        assert m.canonical().formula == m.formula
