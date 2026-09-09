"""ID-STEREO-CIP-NAMER (ROUND 20): committed validation of the general CIP R/S namer.

The distinct-atomic-number slice (ID-STEREO-01) named only centres whose four direct neighbours already differ
by atomic number; the general namer (``smartchem.smiles._cip_ranks`` + ``_cip_compare``) computes CIP **Rule 1a**
priorities for the common case those neighbours TIE -- amino acids, sugars, any secondary/tertiary carbon.

Two prior attempts (ROUND 13/14) died to a DEPTH-first tie-break (a nested-tuple lexicographic key) that descends
the first branch to its leaves before comparing the second branch's near sphere; that gives the WRONG order on the
branch-vs-chain motif ``C[C@H](CCC)C(C)C`` (DFS -> S, truth -> R).  The correct rule is BREADTH-first, branch-by-
branch with need-to-know pruning (Hanson, Musacchio, Mayfield, Vainio, Yerin, Redkin, *J. Chem. Inf. Model.* 2018,
58(9), 1755).  This harness is the anti-regression proof, in five layers:

  1. TEXTBOOK ABSOLUTES -- ~26 molecules with hand-derived / PubChem-checked R/S, including the L-serine (S) /
     L-cysteine (R) flip (same skeleton and ``@@`` tag, OPPOSITE label because cysteine's real S out-ranks the
     carboxyl's phantom-O at sphere 1 -- a shortcut that special-cases "carboxyl wins" silently mislabels it), and
     the ROUND-28 CIP Rule-2 (isotope mass) cases at spheres 0/1/2/3 (each enantiomer-inverting).
  2. ORACLE CROSS-CHECK -- for every NAMED centre, the label equals ``geometric_handedness(priorities, sense)``
     (the ROUND-19 geometric oracle), with the priorities the namer computed: geometry validated independently of
     ranking, exactly the decoupling the oracle was committed for.
  3. THE R14 DIFFERENTIAL -- a naive DEPTH-first comparator (built here) MISLABELS ``C[C@H](CCC)C(C)C`` as (S)
     while the shipped breadth-first namer names it (R); pins the fix so nobody re-ships the DFS digraph.
  4. THE BRANCH-PAIRED PROOF -- a synthetic pair of digraphs where a SPHERE-POOLING comparator (a *different*,
     also-wrong bug) and the correct need-to-know branch-paired comparator DISAGREE; ``_cip_compare`` gives the
     branch-paired answer (the high branch, deciding deep, wins over a low branch differing shallow).
  5. COMBINATORIAL PROPERTIES -- over a generated alkyl-substituent pool (the class the R14 bug hid in, invisible
     to curated anchors), every named centre INVERTS under enantiomer reflection and is INVARIANT under re-spelling,
     and a centre with two identical substituents DEFERS.  (No external CIP oracle exists in the dependency-light
     core -- RDKit is absent -- so absolute ground truth is the hand/PubChem battery; the pool proves internal
     soundness on the combinatorial family curated anchors miss.)

SOUND, not complete: ROUND 28 added CIP Rule 2 (mass number), so an isotope-only tie now NAMES (at any sphere, as
long as the pairing is unambiguous).  A centre the BUILT rules (1a, 2) still cannot fully order -- a tie needing
Rule 1b/3/4/5, a Rule-2 pairing made ambiguous by Rule-1a-tied siblings (the all-pairs guard) or an unknown mass, or
a true constitutional duplicate -- is a NAMED DEFERRAL (no label), because a guessed R/S is worse than none.
Bounded neutral mancude rings now use exact duplicate atomic-number averaging;
the source-derived anchors and hostile aromatic/Kekule controls are in ``cip_mancude_probe``. The di-2-pyridyl
false centre still defers: averaging must never split its two identical pyridyls. Unsupported unsaturated ring
systems retain a lazy deferral boundary. Those DEFER cases are pinned in layer 5.
A ranking DECIDED by atomic number before the ring is relevant still names (a distinct-Z centre with a benzyl or styryl
arm -- pinned in the battery), because the sphere comparison uses each child's known atomic number without ranking it.

BOUNDARY (evil-morty residuals): ``_cip_compare`` is used as a ``cmp_to_key`` sort key, which assumes transitivity; a
deep degenerate tie tree could in principle violate it.  No counterexample was found (the 400-molecule spelling fuzzer
showed 0 inconsistencies) and the ``sorted(ranks) == [0,1,2,3]`` guard in ``_cip_ranks`` catches any top-level cycle
(-> DEFER, sound), but a transitivity PROOF is not in hand -- documented, not eliminated.  The exocyclic-multiple-bond-
into-an-aromatic-atom path (a Kekule-dependent phantom count) IS discharged, by an explicit guard in ``_cip_digraph``.

Deterministic: re-run ``python -m experiments.cip_namer_probe`` after an INTENTIONAL change and set ``FROZEN_HASH``
to the printed value; an UNINTENTIONAL drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json
from functools import cmp_to_key
from itertools import permutations

from smartchem.data.periodic_table import ATOMIC_NUMBER
from smartchem.smiles import (
    _cip_compare,
    _cip_digraph,
    _cip_mancude,
    _cip_mass,
    _cip_ranks,
    _fill_hydrogens,
    _kekulize_in_place,
    _on_cycle,
    _parse_skeleton,
    cip_labels,
)
from experiments.cip_geometry_oracle_probe import geometric_handedness

#: Tamper pin over the whole battery (labels + priorities + oracle agreement).  Regenerate ONLY on an intentional
#: change: ``python -m experiments.cip_namer_probe`` and paste the printed value.
FROZEN_HASH = "b074caae739ef475d7e40095da6a2b493eb7f41d1d8082b45c6338b4ed17c6b5"


# --- textbook / PubChem absolutes (hand-derived R/S, the ground truth) -------------------------------

#: (SMILES, expected sorted labels, note).  Every label is textbook or PubChem-sourced.
TEXTBOOK = [
    ("[C@H](F)(Cl)Br", ("S",), "distinct-Z base (unchanged from ID-STEREO-01)"),
    ("[C@@H](F)(Cl)Br", ("R",), "distinct-Z mirror"),
    ("N[C@@H](C)C(=O)O", ("S",), "L-alanine: COOH phantom-O {O,O,O} > CH3 {H,H,H} at sphere 1"),
    ("N[C@H](C)C(=O)O", ("R",), "D-alanine"),
    ("OC[C@@H](O)C=O", ("R",), "D-glyceraldehyde: CHO phantom-O breaks the C-vs-C tie"),
    ("C([C@H](C=O)O)O", ("R",), "D-glyceraldehyde, alternate spelling -> same (R)"),
    ("C([C@@H](C(=O)O)N)O", ("S",), "L-serine (PubChem CID 5951): COOH {O,O,O} > CH2OH {O,H,H}"),
    ("C([C@@H](C(=O)O)N)S", ("R",), "L-cysteine (PubChem CID 5862): real S(16) > COOH phantom-O -> FLIPS to R"),
    ("N[C@@H](CS)C(=O)O", ("R",), "L-cysteine, alternate spelling -> R"),
    ("CC[C@@H](C)Cl", ("R",), "(R)-2-chlorobutane: ethyl > methyl at sphere 1"),
    ("CC[C@@H](C)O", ("R",), "(R)-2-butanol"),
    ("CC[C@@H](C)CCC", ("R",), "3-methylhexane: propyl > ethyl only at sphere 2"),
    ("Cl[C@H](F)Cc1ccccc1", ("S",), "distinct-Z (Cl,F,H,C) with a BENZYL arm: named at sphere 0, the aromatic onward structure never needed"),
    ("Cl[C@H](C)C=CC(C)(C)C", ("R",), "vinyl/styryl-like chain vs methyl: vinyl {C,C,H} > CH3 {H,H,H} at the sphere -> R"),
    ("C[C@H](CCC)C(C)C", ("R",), "R14 branch-vs-chain: isopropyl (C,C,H) > n-propyl (C,H,H); DFS wrongly says S"),
    ("C[C@H](CCC)C(C)CC", ("R",), "sec-butyl > n-propyl -> R"),
    ("CCCC[C@H](CC(C)C)C", ("R",), "isobutyl > n-butyl (tie breaks at sphere 2) -> R"),
    ("Br[C@H](F)O[C@@H](F)Cl", ("S", "S"), "two distinct-Z centres (unchanged slice; labels from the anchored convention)"),
    ("C[C@@H](O)[C@H](N)C(=O)O", ("R", "S"), "threonine-like: two named centres"),
    ("C[C@H](N)c1ccccc1", ("S",), "neutral mancude extension: N > phenyl {C,C,C} > methyl {H,H,H} > H"),
    # ROUND 28 -- CIP Rule 2 (mass number).  A same-Z tie Rule 1a leaves is broken by the isotope mass, in the
    # Rule-1a-established order (higher mass ranks higher; specified isotope carries its mass number, unspecified
    # the CIAAW standard weight).  These NAME centres the R20/R22 Rule-1a-only namer DEFERRED.
    ("F[C@@](Cl)([2H])[3H]", ("R",), "Rule 2 sphere-0: Cl>F>[3H](3)>[2H](2); the direct isotope tie breaks at the ligand atom"),
    ("F[C@](Cl)([2H])[3H]", ("S",), "Rule 2 sphere-0 enantiomer (sense flip inverts the label)"),
    ("F[C@@](Cl)([1H])[2H]", ("R",), "Rule 2 direction: protium [1H](1) < [2H](2), so 2H outranks 1H"),
    ("[2H]O[C@@](Br)(Cl)O[3H]", ("S",), "Rule 2 sphere-1: two -OH tie under Rule 1a; -O[3H] > -O[2H] one sphere in (3>2)"),
    ("[2H]O[C@](Br)(Cl)O[3H]", ("R",), "Rule 2 sphere-1 enantiomer"),
    # ROUND-28 evil-morty coverage fold: Rule 2 also NAMES multi-sphere ties (it does NOT stop at sphere 1) -- pin
    # sphere-2 and sphere-3 so a traversal refactor cannot silently reverse a deep mass verdict.  Both hand-derived
    # (higher mass wins; branch order is Rule-1a-established) and blind-sign-checked by the geometric oracle (layer 2).
    ("FC(F)O[C@@](Br)(Cl)O[13CH](F)F", ("S",), "Rule 2 sphere-2: two -O-CHF2 tie until [13C](13) > C(12.011) at the far carbon"),
    ("FC(F)O[C@](Br)(Cl)O[13CH](F)F", ("R",), "Rule 2 sphere-2 enantiomer"),
    ("F[13C](F)CO[C@@](Br)(Cl)OCC(F)F", ("S",), "Rule 2 sphere-3: the [13C] two carbons out breaks the tie"),
    ("F[13C](F)CO[C@](Br)(Cl)OCC(F)F", ("R",), "Rule 2 sphere-3 enantiomer"),
]

#: The discriminator that a "carboxyl always wins" shortcut silently mislabels.
SERINE = ("C([C@@H](C(=O)O)N)O", ("S",))
CYSTEINE = ("C([C@@H](C(=O)O)N)S", ("R",))

#: Centres Rule 1a CANNOT order, or that need machinery not built -> must DEFER (no label), never a guessed one.
DEFERRALS = [
    ("C[C@](C)(N)O", "false centre: two identical methyls (true constitutional duplicate)"),
    ("CC[C@](CC)(N)O", "false centre: two identical ethyls"),
    ("N[C@]1(F)CCCCO1", "ring stereocentre (out of the acyclic scope)"),
    ("[C@@](Br)(Cl)(C[2H])C[3H]", "Rule-2 pairing AMBIGUOUS: -CH2[2H] vs -CH2[3H] tie under Rule 1a AND the three H's on each carbon tie (all z=1), so the sibling pairing for the mass compare is arbitrary -> DEFER, never guess (ROUND-28 all-pairs guard)"),
    ("O[C@H](c1ccccn1)c1ccccn1", "SOUNDNESS PIN: two identical 2-pyridyls = a FALSE centre; a fixed Kekule would wrongly name it"),
]


# --- extract the priorities the namer computed, for the oracle cross-check ---------------------------

def _named_centres(text: str) -> "list[tuple[list[int], int, str]]":
    """For each acyclic four-coordinate marked centre the namer NAMES in ``text``, return
    ``(ranks, sense, label)`` -- mirroring ``smartchem.smiles._cip_labels`` so the priorities are exactly the ones
    the shipped namer used."""
    atoms, bonds = _parse_skeleton(text.strip())
    charge = sum(a.charge for a in atoms)
    marked = [a for a in range(len(atoms)) if atoms[a].chirality]
    if not marked:
        return []
    work = [list(b) for b in bonds]
    _kekulize_in_place(atoms, work, charge)
    elems, filled_bonds = _fill_hydrogens(atoms, work)
    n = len(atoms)
    mass = [_cip_mass(elems[i], atoms[i].isotope if i < n else 0) for i in range(len(elems))]
    neighbours: dict[int, list[int]] = {i: [] for i in range(len(elems))}
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(elems))}
    for b in filled_bonds:
        neighbours[b.i].append(b.j)
        neighbours[b.j].append(b.i)
        adj[b.i].append((b.j, b.order))
        adj[b.j].append((b.i, b.order))
    aromatic, mancude, released = _cip_mancude(atoms, work, adj)
    out: list[tuple[list[int], int, str]] = []
    for a in marked:
        if _on_cycle(a, neighbours, len(elems)):
            continue
        incoming = [bd[0] for bd in bonds if bd[1] == a]
        outgoing = [bd[1] for bd in bonds if bd[0] == a]
        h_neighbours = [j for j in neighbours[a] if j >= n and elems[j] == "H"]
        if len(incoming) > 1:
            continue
        written = ([incoming[0]] if incoming else []) + h_neighbours + outgoing
        if len(written) != 4 or any(ATOMIC_NUMBER.get(elems[x]) is None for x in written):
            continue
        ranks = _cip_ranks(written, a, adj, elems, mass, aromatic, mancude, released)
        if ranks is None:
            continue
        from smartchem.smiles import _perm_parity
        handedness = _perm_parity(ranks) ^ (0 if atoms[a].chirality == 1 else 1)
        out.append((ranks, atoms[a].chirality, "S" if handedness == 0 else "R"))
    return out


# --- the R14 depth-first comparator (built here only to PROVE the namer is NOT it) -------------------

def _dfs_key(node):
    """A naive DEPTH-first CIP key: (atomic_number, sorted child keys) compared lexicographically.  This is the
    ROUND-14 bug -- Python's tuple ``<`` descends the first child's whole subtree before the second child's near
    atomic number, so it defers a sphere-1 decision past a longer chain and mislabels branch-vs-chain."""
    return (node[0], tuple(sorted((_dfs_key(c) for c in node[2]), reverse=True)))  # children moved to [2] (ROUND 28)


def _dfs_labels(text: str) -> "tuple[str, ...]":
    """cip_labels-shaped output, but ranked by the DEPTH-first key -- used only to exhibit the wrong answer."""
    atoms, bonds = _parse_skeleton(text.strip())
    charge = sum(a.charge for a in atoms)
    marked = [a for a in range(len(atoms)) if atoms[a].chirality]
    work = [list(b) for b in bonds]
    _kekulize_in_place(atoms, work, charge)
    elems, filled_bonds = _fill_hydrogens(atoms, work)
    n = len(atoms)
    mass = [_cip_mass(elems[i], atoms[i].isotope if i < n else 0) for i in range(len(elems))]
    aromatic = frozenset(i for i in range(n) if atoms[i].aromatic)
    neighbours: dict[int, list[int]] = {i: [] for i in range(len(elems))}
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(elems))}
    for b in filled_bonds:
        neighbours[b.i].append(b.j)
        neighbours[b.j].append(b.i)
        adj[b.i].append((b.j, b.order))
        adj[b.j].append((b.i, b.order))
    from smartchem.smiles import _CIP_NODE_BUDGET, _perm_parity
    labels = []
    for a in marked:
        if _on_cycle(a, neighbours, len(elems)):
            continue
        incoming = [bd[0] for bd in bonds if bd[1] == a]
        outgoing = [bd[1] for bd in bonds if bd[0] == a]
        h_neighbours = [j for j in neighbours[a] if j >= n and elems[j] == "H"]
        if len(incoming) > 1:
            continue
        written = ([incoming[0]] if incoming else []) + h_neighbours + outgoing
        if len(written) != 4:
            continue
        roots = [_cip_digraph(w, a, frozenset((a, w)), adj, elems, mass, aromatic, [_CIP_NODE_BUDGET]) for w in written]
        keys = [_dfs_key(r) for r in roots]
        if len(set(keys)) != 4:
            continue
        order = sorted(keys, reverse=True)
        ranks = [order.index(k) for k in keys]
        handedness = _perm_parity(ranks) ^ (0 if atoms[a].chirality == 1 else 1)
        labels.append("S" if handedness == 0 else "R")
    return tuple(sorted(labels))


# --- the branch-paired proof (a sphere-pooling comparator disagrees; the namer is right) -------------

def _pooled_compare(a, b) -> int:
    """A GLOBAL sphere-pooling comparator: compares each sphere's atoms across ALL sibling branches at once (a
    different, also-wrong bug from DFS).  Lets a low branch decide at a shallow sphere ahead of a high branch that
    decides deep -- the namer's ``_cip_compare`` must NOT agree with it on the divergence pair below."""
    fa, fb = [a], [b]
    while fa or fb:
        za = [n[0] for n in fa]
        zb = [n[0] for n in fb]
        length = max(len(za), len(zb))
        za += [0] * (length - len(za))
        zb += [0] * (length - len(zb))
        for x, y in zip(za, zb):
            if x != y:
                return 1 if x > y else -1
        na: list = []
        nb: list = []
        for n in fa:
            na += sorted(n[2], key=cmp_to_key(_pooled_compare), reverse=True)  # children moved to [2] (ROUND 28)
        for n in fb:
            nb += sorted(n[2], key=cmp_to_key(_pooled_compare), reverse=True)
        fa, fb = na, nb
    return 0


#: A divergence pair.  A's high branch ties B's shallow but wins DEEP; A's low branch loses B's shallow.
#: Correct (branch-paired, need-to-know): the high branch decides -> A > B.  Sphere-pooling: B > A (wrong).
#: ROUND-28 node shape ``(z, mass, children)``: the ``mass`` slot carries the real standard weight of each z but
#: is Rule-1a-INERT for this fixture (``_cip_compare``/``_pooled_compare`` read only ``[0]``/``[2]``); it exists
#: only so the literals are valid enriched nodes.
_DIV_A = (6, 12.011, ((6, 12.011, ((8, 15.999, ((6, 12.011, ((9, 18.998, ()),)),)), (1, 1.008, ()))),
                      (6, 12.011, ((7, 14.007, ()), (1, 1.008, ())))))
_DIV_B = (6, 12.011, ((6, 12.011, ((8, 15.999, ((6, 12.011, ((7, 14.007, ()),)),)), (1, 1.008, ()))),
                      (6, 12.011, ((8, 15.999, ()), (1, 1.008, ())))))


def _ctx():
    return {"cmp": {}, "sc": {}, "budget": [10 ** 9]}


# --- the combinatorial alkyl pool (internal soundness on the class the R14 bug hid in) ---------------

_ALKYL = ("C", "CC", "CCC", "CCCC", "C(C)C", "CC(C)C", "C(C)(C)C")


def _alkyl_pool() -> "list[tuple[str, str, str]]":
    """Distinct-alkyl stereocentres ``[C@](a)(b)(c)d`` and ``[C@@]...``, plus a re-spelling (swap the first two
    substituents AND flip the sense = the same molecule) and the enantiomer (flip the sense only)."""
    out = []
    for combo in permutations(_ALKYL, 4):
        a, b, c, d = combo
        base = f"[C@]({a})({b})({c}){d}"
        mirror = f"[C@@]({a})({b})({c}){d}"          # enantiomer: sense flipped, same order
        respell = f"[C@@]({b})({a})({c}){d}"         # SAME molecule: two swapped + sense flipped
        out.append((base, mirror, respell))
    return out


# --- validation ------------------------------------------------------------------------------------

def validate() -> None:
    """Raise if the namer does not hold across all five layers."""
    # 1. textbook absolutes.
    for smi, expected, note in TEXTBOOK:
        got = cip_labels(smi)
        assert got == expected, f"{smi}: got {got}, expected {expected} ({note})"
    # 1b. the serine/cysteine flip explicitly (same skeleton + tag, opposite label).
    assert cip_labels(SERINE[0]) == SERINE[1], "L-serine must be (S)"
    assert cip_labels(CYSTEINE[0]) == CYSTEINE[1], "L-cysteine must FLIP to (R) -- real S beats phantom-O"
    assert SERINE[0][:3] == CYSTEINE[0][:3], "serine/cysteine must share the written skeleton up to the heteroatom"

    # 2. oracle cross-check: every named centre's label == geometric_handedness(its priorities, sense).
    named_any = False
    for smi, _expected, _note in TEXTBOOK:
        for ranks, sense, label in _named_centres(smi):
            named_any = True
            priorities = tuple(r + 1 for r in ranks)
            assert geometric_handedness(priorities, sense) == label, (
                f"{smi}: oracle {geometric_handedness(priorities, sense)} != namer {label} (priorities {priorities})"
            )
    assert named_any, "the oracle cross-check ran on ZERO centres -- non-vacuity failed"

    # 3. the R14 differential: the DFS comparator mislabels; the shipped namer is right.
    assert cip_labels("C[C@H](CCC)C(C)C") == ("R",), "the breadth-first namer must name the R14 case (R)"
    assert _dfs_labels("C[C@H](CCC)C(C)C") == ("S",), "the DEPTH-first key must give the WRONG (S) -- the R14 bug"
    assert cip_labels("C[C@H](CCC)C(C)C") != _dfs_labels("C[C@H](CCC)C(C)C"), "namer must NOT be the DFS key"

    # 4. the branch-paired proof: the namer disagrees with sphere-pooling, and takes the correct side.
    assert _cip_compare(_DIV_A, _DIV_B, _ctx()) == 1, "branch-paired: the deep-deciding high branch must win (A>B)"
    assert _pooled_compare(_DIV_A, _DIV_B) == -1, "sphere-pooling gives the WRONG B>A -- the divergence must be real"

    # 5. combinatorial properties over the alkyl pool.
    pool = _alkyl_pool()
    named = 0
    for base, mirror, respell in pool:
        lb, lm, lr = cip_labels(base), cip_labels(mirror), cip_labels(respell)
        if lb:                                                  # a named centre must invert and be spelling-invariant
            named += 1
            assert len(lb) == 1 and lb[0] in ("R", "S"), f"{base}: {lb}"
            assert lm and lm[0] != lb[0], f"enantiomer must invert: {base} {lb} vs {mirror} {lm}"
            assert lr == lb, f"re-spelling must be invariant: {base} {lb} vs {respell} {lr}"
    assert named > 100, f"the alkyl pool named too few centres to be a real test ({named})"
    # a two-identical-substituent centre must DEFER (a false centre is a genuine Rule-1a tie).
    for a in _ALKYL:
        assert cip_labels(f"[C@]({a})({a})(N)O") == (), f"twin-{a} false centre must DEFER"

    # 6. the sound DEFER classes.
    for smi, note in DEFERRALS:
        assert cip_labels(smi) == (), f"{smi} must DEFER ({note})"


# --- report / freeze -------------------------------------------------------------------------------

def _content() -> dict:
    return {
        "textbook": {smi: list(cip_labels(smi)) for smi, _e, _n in TEXTBOOK},
        "serine": list(cip_labels(SERINE[0])),
        "cysteine": list(cip_labels(CYSTEINE[0])),
        "deferrals": {smi: list(cip_labels(smi)) for smi, _n in DEFERRALS},
        "priorities": {
            smi: [(list(r), s, lab) for (r, s, lab) in _named_centres(smi)] for smi, _e, _n in TEXTBOOK
        },
        "r14_namer": list(cip_labels("C[C@H](CCC)C(C)C")),
        "r14_dfs_wrong": list(_dfs_labels("C[C@H](CCC)C(C)C")),
        "divergence": [_cip_compare(_DIV_A, _DIV_B, _ctx()), _pooled_compare(_DIV_A, _DIV_B)],
        "alkyl_named": sum(1 for b, _m, _r in _alkyl_pool() if cip_labels(b)),
    }


def content_hash() -> str:
    encoded = json.dumps(_content(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def report() -> dict:
    return {
        "textbook_size": len(TEXTBOOK),
        "alkyl_pool_size": len(_alkyl_pool()),
        "alkyl_named": _content()["alkyl_named"],
        "serine_cysteine_flip": (cip_labels(SERINE[0]), cip_labels(CYSTEINE[0])),
        "r14_namer_vs_dfs": (cip_labels("C[C@H](CCC)C(C)C"), _dfs_labels("C[C@H](CCC)C(C)C")),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    for key, value in report().items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
