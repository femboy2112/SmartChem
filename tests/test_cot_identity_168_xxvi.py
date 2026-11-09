"""DEFECT-PIN for issue #168 (OPERATION XXVI, Packet I): the SMILES parser and
``resonance_identity`` MERGE cyclooctatetraene (COT) bond-shift isomers that are
genuinely distinct species.

WHAT THIS TEST IS
-----------------
This test PINS A DEFECT.  Its ``*_collide`` assertions assert that the collision
REPRODUCES on today's code (they are GREEN on current ``main``).  It is NOT a
specification of correct behaviour: a successor that fixes #168 (an aromaticity-aware
identity policy that distinguishes true aromatic delocalisation from non-aromatic
bond-shift interconversion) MUST FLIP the ``*_collide`` assertions from ``==`` to
``!=``.  The ``*_are_distinct_species`` assertions are ground truth (an independent,
complete graph-isomorphism check) and must stay GREEN across the fix.

THE EXACT COLLAPSE STAGE
------------------------
The two distinct input graphs are already merged at PARSE TIME.  ``parse_smiles``
calls ``_build_molecule`` -> ``_canonical_kekule_orders`` -> ``_min_constitution_
placement``, which re-distributes the explicit C=C double bonds to a single
"constitution-minimal placement over the whole pi system".  For an all-explicit
(non-aromatic) ring this redistribution collapses the two bond-shift isomers into
one ``Molecule`` before ``canonical()`` or ``resonance_identity()`` is ever called.
Every downstream key (``Molecule.canonical()``, ``resonance_identity``,
``isotope_refined_key``, ``configuration_key``) therefore inherits the collapse.

WHY IT IS A DEFECT (not correct resonance merging)
--------------------------------------------------
COT is a tub-shaped, NON-aromatic [8]annulene with localised alternating single/
double bonds.  Its two Kekule drawings are distinct bond-shift ISOMERS connected by
a process with a real barrier, not resonance forms of one delocalised species.
Merging them is the over-unification ``resonance_canonical`` claims it never does
("never over-unifies", smartchem/smiles.py ~line 1052).  Merging Kekule forms is
only correct for genuine aromatic delocalisation (e.g. benzene, Hückel 4n+2).

INDEPENDENCE
------------
Neither rdkit nor networkx is importable in the venv, so distinctness is confirmed
by a self-contained, COMPLETE backtracking bond-labelled graph isomorphism test
(below) that shares none of SmartChem's Kekule canonicalisation.  For both pairs the
two methylated ring carbons are joined by a DOUBLE bond in A and a SINGLE bond in B,
so no bond-order-preserving bijection exists -> the species are non-isomorphic.
"""

from __future__ import annotations

from collections import Counter

import pytest

from smartchem.smiles import (
    parse_smiles,
    resonance_identity,
    isotope_refined_key,
    configuration_key,
)

# Each pair: (label, SMILES A, SMILES B) -- A and B are distinct COT bond-shift isomers.
COT_PAIRS = [
    # methyls across one C=C (A) vs across a C-C single bond (B)
    ("disubstituted", "CC1=C(C)C=CC=CC=C1", "CC1=CC=CC=CC=C1C"),
    # the 1,2,3,4-tetrasubstituted analogue
    ("tetrasubstituted", "CC1=C(C)C(C)=C(C)C=CC=C1", "CC1=CC=CC=C(C)C(C)=C1C"),
]


# --------------------------------------------------------------------------------------
# Self-contained, SmartChem-independent confirmation that A and B are distinct graphs.
# A tiny SMILES reader that preserves the WRITTEN bond orders (the subset these inputs
# use: single-letter atoms, branches, ring-closure digits, bonds - = #), plus a complete
# backtracking bond-labelled graph-isomorphism test.  No rdkit, no networkx, no SmartChem.
# --------------------------------------------------------------------------------------
def _independent_read(smiles: str):
    atoms: list[str] = []
    bonds: list[tuple[int, int, int]] = []
    stack: list[int | None] = []
    prev: int | None = None
    pending = 1
    ring: dict[str, tuple[int, int]] = {}
    for c in smiles:
        if c == "(":
            stack.append(prev)
        elif c == ")":
            prev = stack.pop()
        elif c in "=#-":
            pending = {"-": 1, "=": 2, "#": 3}[c]
        elif c.isdigit():
            if c in ring:
                a0, o0 = ring.pop(c)
                order = o0 if o0 != 1 else pending
                a, b = sorted((a0, prev))  # type: ignore[arg-type]
                bonds.append((a, b, order))
            else:
                ring[c] = (prev, pending)  # type: ignore[assignment]
            pending = 1
        elif c.isalpha():
            idx = len(atoms)
            atoms.append(c)
            if prev is not None:
                a, b = sorted((prev, idx))
                bonds.append((a, b, pending))
            pending = 1
            prev = idx
        else:  # pragma: no cover - the #168 inputs never hit this
            raise ValueError(f"unhandled SMILES char {c!r}")
    assert not ring, f"unclosed ring(s): {ring}"
    return atoms, bonds


def _build(atoms, bonds):
    adj: dict[int, dict[int, int]] = {k: {} for k in range(len(atoms))}
    for a, b, o in bonds:
        adj[a][b] = o
        adj[b][a] = o
    label = {}
    for k in range(len(atoms)):
        val = sum(adj[k].values())
        label[k] = (atoms[k], (4 - val) if atoms[k] == "C" else 0)  # (element, implicit H)
    return adj, label


def _wl_colors(adj, label, rounds=10):
    color = dict(label)
    for _ in range(rounds):
        color = {k: (color[k], tuple(sorted((o, color[n]) for n, o in adj[k].items()))) for k in adj}
    return color


def _exact_isomorphic(a, b) -> bool:
    """True iff a label- and bond-order-preserving bijection A->B exists (complete)."""
    adjA, labA = _build(*a)
    adjB, labB = _build(*b)
    if len(adjA) != len(adjB):
        return False
    if Counter(labA.values()) != Counter(labB.values()):
        return False
    eA = Counter((tuple(sorted((labA[i], labA[j]))), o) for i in adjA for j, o in adjA[i].items() if i < j)
    eB = Counter((tuple(sorted((labB[i], labB[j]))), o) for i in adjB for j, o in adjB[i].items() if i < j)
    if eA != eB:
        return False
    cA, cB = _wl_colors(adjA, labA), _wl_colors(adjB, labB)
    if Counter(cA.values()) != Counter(cB.values()):
        return False
    cand = {i: [j for j in adjB if cB[j] == cA[i]] for i in adjA}
    order = sorted(adjA, key=lambda i: len(cand[i]))
    mapping: dict[int, int] = {}
    used: set[int] = set()

    def bt(idx: int) -> bool:
        if idx == len(order):
            return True
        i = order[idx]
        for j in cand[i]:
            if j in used:
                continue
            if all(adjB[j].get(mapping[n]) == o for n, o in adjA[i].items() if n in mapping):
                mapping[i] = j
                used.add(j)
                if bt(idx + 1):
                    return True
                del mapping[i]
                used.discard(j)
        return False

    return bt(0)


@pytest.mark.parametrize("label, sa, sb", COT_PAIRS, ids=[p[0] for p in COT_PAIRS])
def test_cot_pair_are_distinct_species(label, sa, sb):
    """GROUND TRUTH (stays GREEN across the fix): A and B are non-isomorphic bond-
    labelled molecular graphs, by a complete, SmartChem-independent isomorphism test."""
    a = _independent_read(sa)
    b = _independent_read(sb)
    assert not _exact_isomorphic(a, b), (
        f"{label}: the independent graph-isomorphism test unexpectedly found the two "
        f"COT bond-shift inputs ISOMORPHIC; the #168 premise (distinct species) would be wrong"
    )


@pytest.mark.parametrize("label, sa, sb", COT_PAIRS, ids=[p[0] for p in COT_PAIRS])
def test_cot_pair_collide_in_smartchem_identity(label, sa, sb):
    """DEFECT PIN (GREEN today; a #168 fix FLIPS every ``==`` below to ``!=``): two
    distinct COT bond-shift isomers are merged by the parser and by every identity key.

    The first stage that equates them is ``parse_smiles`` itself (the Kekule
    re-placement in ``_build_molecule``); ``canonical()``, ``resonance_identity``,
    ``isotope_refined_key`` and ``configuration_key`` all inherit the collapse.
    """
    mol_a = parse_smiles(sa)
    mol_b = parse_smiles(sb)

    # Stage a/c -- the parser already re-kekulises to ONE graph (collapse at parse time).
    assert mol_a.canonical() == mol_b.canonical(), (
        f"{label}: parse_smiles no longer merges the COT bond-shift isomers at canonical() "
        f"-- if #168 was fixed, convert this to assertNotEqual"
    )
    # Stage d -- resonance_identity (the documented material key) inherits the merge.
    assert resonance_identity(mol_a) == resonance_identity(mol_b), (
        f"{label}: resonance_identity no longer merges the COT bond-shift isomers "
        f"-- if #168 was fixed, convert this to assertNotEqual"
    )
    # Stage e -- the refined identity layers inherit it too.
    assert isotope_refined_key(sa) == isotope_refined_key(sb), (
        f"{label}: isotope_refined_key no longer merges the COT bond-shift isomers"
    )
    assert configuration_key(sa) == configuration_key(sb), (
        f"{label}: configuration_key no longer merges the COT bond-shift isomers"
    )


def test_collapse_is_a_defect_not_identical_inputs():
    """Tie the two facts together: the inputs are DISTINCT species (independent check)
    yet SmartChem assigns them ONE identity -- that conjunction is the #168 defect.
    A successor that fixes #168 keeps the first clause and negates the second."""
    for label, sa, sb in COT_PAIRS:
        distinct = not _exact_isomorphic(_independent_read(sa), _independent_read(sb))
        merged = resonance_identity(parse_smiles(sa)) == resonance_identity(parse_smiles(sb))
        assert distinct and merged, (
            f"{label}: expected distinct-but-merged (the #168 defect); "
            f"got distinct={distinct}, merged={merged}"
        )
