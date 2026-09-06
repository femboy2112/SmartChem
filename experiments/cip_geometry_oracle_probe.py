"""CIP-ORACLE-01 committed demonstration: an INDEPENDENT geometric handedness oracle for CIP R/S.

The roadmap's general-CIP gate (queue item 1) is explicit: *"the wall isn't the namer -- it's the
oracle"*.  A general R/S namer was built and discarded TWICE (ROUND 13/14); each time the cross-check
that was meant to catch the bug shared the same graph-walk plumbing as the code it audited (an in-repo
``configuration_digest``), so a systematic depth-first-vs-breadth-first priority-ordering bug survived
13/13 textbook cases and full spelling-invariance.  A cross-check that shares the suspect's assumptions
is common-mode and cannot see the suspect's bug.

This harness commits the missing piece: a handedness oracle that reads the CIP label off an actual signed
volume of real synthetic 3-D coordinates, built from the OpenSMILES sense convention (view the centre with
the lowest-priority substituent pointing AWAY; trace priority 1 -> 2 -> 3; clockwise is R, anticlockwise is
S).  It takes the four written neighbours' priorities and the tetrahedral SENSE bit; it does NOT guess CIP
priorities.

Be precise about what this buys, because it is easy to oversell (an adversarial review caught exactly that).
A signed volume of permuted tetrahedron vertices is an ALTERNATING function of the ordering, so
``sign(V) = parity(pi) * epsilon * sense`` -- ALGEBRAICALLY the same group-theoretic quantity the shipped
``_perm_parity(ranks) ^ sense`` computes, with ``epsilon`` the single global sign of the base tetrahedron in
natural order (measured ``+``, i.e. V > 0 <-> S).  So the exhaustive 48-case agreement with ``cip_labels``
confirms ONE constant (``epsilon``), not 48 independent facts: once any one non-degenerate case agrees, the
algebra forces the rest.  What this oracle GENUINELY adds is two things, both real but narrow:
  (1) it re-derives ``epsilon`` from actual COORDINATES + the actual CIP viewing rule rather than copying the
      shipped ``"S" if handedness == 0`` line, so a GLOBAL sign-flip planted in the shipped emit line WOULD be
      caught (the oracle says S for ``[C@H](F)(Cl)Br``; a flipped slice says R; ``validate`` fires) -- and the
      convention is checked against EXTERNAL reality (OpenSMILES ``@`` + CIP hand-derive ``[C@H](F)(Cl)Br`` =
      (S), textbook), not merely against itself;
  (2) it is the DECOUPLING instrument -- CIP has two parts, (a) RANK the substituents by priority (the hard
      recursive-digraph part, the R14 bug locus) and (b) given priorities + geometry assign R/S.  This oracle
      nails (b) and takes (a) as an INPUT, so a FUTURE breadth-first namer can be validated by
      ``namer(mol) == geometric_handedness(true_priorities, sense)`` on textbook cases -- isolating "are the
      priorities right" (the namer, the R14 failure axis) from "is the geometry right" (this oracle), which
      is the separation the R14 common-mode ``configuration_digest`` check could not make.
It does NOT, by itself, catch a RANKING bug on the distinct-Z slice (there its priorities are
``sorted(z, reverse=True)``, identical to the shipped code); that is the namer's axis, tested THROUGH this
oracle in a later round.  BOUNDARY (stated, not papered over): the parser's ``@``/``@@`` -> written-neighbour
ORDER is shared common-mode with ``smartchem.smiles`` and is validated only against the hand-checkable
textbook absolutes below -- there is no external RDKit oracle in the dependency-light core, so that one seam
is asserted from the OpenSMILES spec, not cross-checked by a third party.

The sign convention is DERIVED, not tuned: the OpenSMILES sense rule + the CIP viewing rule, worked
through by hand, give signed volume V > 0 for the two independent textbook anchors below, and both are
(S) -- so V > 0 <-> S is forced, not fitted:
  * distinct-Z anchor ``[C@H](F)(Cl)Br`` = (S): written [H,F,Cl,Br], priorities [4,3,2,1] (Br>Cl>F>H),
    sense ``@`` -> V > 0.
  * same-Z textbook ``N[C@@H](C)C(=O)O`` (L-alanine) = (S): written [N,H,CH3,COOH], priorities [1,4,3,2]
    (N>COOH-C>CH3-C>H), sense ``@@`` -> V > 0.
A globally-flipped convention would still pass every RELATIVE test (enantiomers differ, spellings agree);
these two ABSOLUTE anchors are what pin it, re-derived here rather than asserted from memory.

Cross-check discipline: the PARSER and the distinct-Z scoping are shared with ``smartchem.smiles`` (that is
not where R14 failed).  ``oracle_labels(text)`` must equal ``cip_labels(text)`` across an exhaustive
{F,Cl,Br,I} battery -- that agreement pins ``epsilon`` (one bit), and the frozen digest pins the SHIPPED
slice's labels too, so it reddens on EITHER a global convention flip in the oracle OR a regression in the
audited slice.  It is NOT 48 independent bearings -- see the "what this buys" note above.

Deterministic, so the battery is tamper-pinned by a frozen digest: re-run
``python -m experiments.cip_geometry_oracle_probe`` after an INTENTIONAL change and set ``FROZEN_HASH`` to
the printed value; an UNINTENTIONAL drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json
import math
from itertools import permutations

from smartchem.data.periodic_table import ATOMIC_NUMBER
from smartchem.smiles import (
    _fill_hydrogens,
    _kekulize_in_place,
    _on_cycle,
    _parse_skeleton,
    cip_labels,
)

#: The committed tamper pin over the oracle battery's labels.  Regenerate ONLY on an intentional change:
#: ``python -m experiments.cip_geometry_oracle_probe`` and paste the printed value.
FROZEN_HASH = "e224c3a503af29a06f7147e01e70b7831a6f9ab7d8856505c3785e80d71ebc06"

_Vec = "tuple[float, float, float]"


# --- pure vector helpers (no numpy: the oracle stays dependency-free) --------------------------------

def _sub(a: _Vec, b: _Vec) -> _Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: _Vec, b: _Vec) -> _Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a: _Vec, b: _Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _signed_volume(p1: _Vec, p2: _Vec, p3: _Vec, p4: _Vec) -> float:
    """(p1 - p4) . ((p2 - p4) x (p3 - p4)) -- positive iff (p1,p2,p3) wind anticlockwise seen from the side
    of the centre OPPOSITE p4.  With p1..p4 the priority-1..priority-4 substituent positions this is exactly
    the CIP viewing construction (lowest priority p4 away; trace 1 -> 2 -> 3)."""
    return _dot(_sub(p1, p4), _cross(_sub(p2, p4), _sub(p3, p4)))


# --- the synthetic tetrahedron from the OpenSMILES sense --------------------------------------------

def _tetrahedron(sense: int) -> "tuple[_Vec, _Vec, _Vec, _Vec]":
    """Real 3-D positions for the four WRITTEN neighbours of a tetrahedral centre, honouring the OpenSMILES
    sense.  The first written neighbour sits on +z; the other three sit on the lower cone 120 deg apart.
    ``sense`` 1 (``@``) is the base arrangement; ``sense`` 2 (``@@``) is its mirror image (reflect through
    the xz-plane), so the two senses are genuine enantiomers and their signed volumes are opposite."""
    if sense not in (1, 2):
        raise ValueError(f"sense must be 1 (@) or 2 (@@), got {sense!r}")
    r = math.sqrt(8.0) / 3.0                                   # cone radius for a regular tetrahedron
    z = -1.0 / 3.0
    base = [
        (0.0, 0.0, 1.0),
        (r * math.cos(0.0), r * math.sin(0.0), z),
        (r * math.cos(2.0 * math.pi / 3.0), r * math.sin(2.0 * math.pi / 3.0), z),
        (r * math.cos(4.0 * math.pi / 3.0), r * math.sin(4.0 * math.pi / 3.0), z),
    ]
    if sense == 2:
        base = [(x, -y, zz) for (x, y, zz) in base]            # mirror -> the @@ enantiomer
    return tuple(base)  # type: ignore[return-value]


def geometric_handedness(priorities: "tuple[int, int, int, int]", sense: int) -> str:
    """The CIP R/S label of one tetrahedral centre, from GEOMETRY alone.

    ``priorities`` is the CIP priority of each of the four WRITTEN neighbours, 1 = highest ... 4 = lowest
    (it must be a permutation of {1,2,3,4}); ``sense`` is the tetrahedral sense bit (1 for ``@``, 2 for
    ``@@``).  Priorities are an INPUT -- ranking substituents is CIP's hard recursive part and this oracle
    deliberately does not attempt it, so that "are the priorities right" and "is the geometry right" are
    separable.  Returns ``"R"`` or ``"S"``.  Raises on a non-permutation input.  (The degeneracy guard below
    is a defensive invariant, not a live feature: the fixed regular tetrahedron has ``|V| = 3.079`` for every
    permutation, so it is unreachable today -- it would only fire if ``_tetrahedron`` were replaced by a
    non-regular construction.)"""
    if tuple(sorted(priorities)) != (1, 2, 3, 4):
        raise ValueError(f"priorities must be a permutation of 1..4, got {priorities!r}")
    coords = _tetrahedron(sense)
    by_priority: "list[_Vec | None]" = [None, None, None, None]
    for slot, pr in enumerate(priorities):
        by_priority[pr - 1] = coords[slot]                     # by_priority[0] = the priority-1 position
    p1, p2, p3, p4 = by_priority                               # highest .. lowest
    v = _signed_volume(p1, p2, p3, p4)                         # type: ignore[arg-type]
    if abs(v) < 1e-9:
        raise ValueError("degenerate tetrahedron: the four substituents are (near-)coplanar")
    return "S" if v > 0.0 else "R"                             # DERIVED anchor: [C@H](F)(Cl)Br & L-alanine -> V>0 -> S


# --- the cross-check bridge: the shipped parser's distinct-Z scope, an INDEPENDENT geometric label ---

def _distinct_z_centres(text: str) -> "list[tuple[tuple[int, int, int, int], int]]":
    """For every centre the shipped ``cip_labels`` would NAME (acyclic, four-coordinate, four pairwise
    distinct atomic numbers), return ``(priorities_in_written_order, sense)`` -- reusing the parser and the
    exact scope of ``smartchem.smiles._cip_labels`` (that scoping is shared and is NOT the R14 bug locus),
    so ``oracle_labels`` and ``cip_labels`` compare apples to apples and differ ONLY in the geometry step.
    """
    atoms, bonds = _parse_skeleton(text.strip())
    charge = sum(a.charge for a in atoms)
    marked = [a for a in range(len(atoms)) if atoms[a].chirality]
    if not marked:
        return []
    work = [list(b) for b in bonds]
    _kekulize_in_place(atoms, work, charge)
    filled_atoms, filled_bonds = _fill_hydrogens(atoms, work)
    n = len(atoms)
    neighbours: "dict[int, list[int]]" = {i: [] for i in range(len(filled_atoms))}
    for b in filled_bonds:
        neighbours[b.i].append(b.j)
        neighbours[b.j].append(b.i)
    out: "list[tuple[tuple[int, int, int, int], int]]" = []
    for a in marked:
        if _on_cycle(a, neighbours, len(filled_atoms)):
            continue
        incoming = [bd[0] for bd in bonds if bd[1] == a]
        outgoing = [bd[1] for bd in bonds if bd[0] == a]
        h_neighbours = [j for j in neighbours[a] if j >= n and filled_atoms[j] == "H"]
        if len(incoming) > 1:
            continue
        written = ([incoming[0]] if incoming else []) + h_neighbours + outgoing
        if len(written) != 4:
            continue
        z = [ATOMIC_NUMBER.get(filled_atoms[x]) for x in written]
        if any(zx is None for zx in z) or len(set(z)) != 4:
            continue                                           # same-Z needs the digraph tie-break -> not in scope
        order = sorted(z, reverse=True)                        # descending atomic number = CIP priority
        priorities = tuple(order.index(zx) + 1 for zx in z)    # each written neighbour's priority, 1 = highest
        out.append((priorities, atoms[a].chirality))           # type: ignore[arg-type]
    return out


def oracle_labels(text: str) -> "tuple[str, ...]":
    """The distinct-Z CIP R/S labels of ``text`` computed by the GEOMETRIC oracle, sorted -- the same output
    shape as ``smartchem.smiles.cip_labels``, so the two can be asserted equal across the battery."""
    labels = [geometric_handedness(pri, sense) for pri, sense in _distinct_z_centres(text)]
    return tuple(sorted(labels))


# --- the exhaustive battery -------------------------------------------------------------------------

_HALO = ("F", "Cl", "Br", "I")


def _four_halogen_smiles() -> "list[str]":
    """Every ordering of {F,Cl,Br,I} on a bare stereocentre, both senses -- 4! * 2 = 48 distinct-Z SMILES."""
    out: "list[str]" = []
    for perm in permutations(_HALO):
        a, b, c, d = perm
        for sense in ("@", "@@"):
            out.append(f"[C{sense}]({a})({b})({c}){d}")
    return out


def battery() -> "dict[str, tuple[str, ...]]":
    """The oracle's label for every battery member, keyed by SMILES (canonical, deterministic)."""
    smiles = _four_halogen_smiles() + [
        "[C@H](F)(Cl)Br", "[C@@H](F)(Cl)Br",                   # the 3-halogen + H anchor and its mirror
        "Br[C@H](F)O[C@@H](F)Cl",                              # two independent distinct-Z centres
    ]
    return {s: oracle_labels(s) for s in smiles}


def _content() -> dict:
    # Hand-specified textbook anchors (priorities + sense straight from CIP, INDEPENDENT of the parser).
    chfclbr_written = (4, 3, 2, 1)                             # [H,F,Cl,Br]: H lowest .. Br highest
    alanine_written = (1, 4, 3, 2)                             # [N,H,CH3,COOH]: N>COOH-C>CH3-C>H
    return {
        "anchor_chfclbr_at": geometric_handedness(chfclbr_written, 1),      # @  -> S
        "anchor_chfclbr_atat": geometric_handedness(chfclbr_written, 2),    # @@ -> R
        "anchor_L_alanine": geometric_handedness(alanine_written, 2),       # @@ -> S (L-alanine)
        "anchor_D_alanine": geometric_handedness(alanine_written, 1),       # @  -> R (D-alanine)
        "battery": {s: list(lab) for s, lab in sorted(battery().items())},
        # pin the AUDITED slice's labels too, so a regression in smartchem.smiles.cip_labels (not only in the
        # oracle) reddens the frozen digest -- the hash is a tripwire on the agreement, not just the oracle.
        "shipped_slice": {s: list(cip_labels(s)) for s in sorted(battery())},
    }


def content_hash() -> str:
    encoded = json.dumps(_content(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate() -> None:
    """Raise if the oracle does not hold: the two textbook absolute anchors, the exhaustive agreement with
    the shipped distinct-Z slice, non-vacuity, enantiomer inversion, and the input guards."""
    # 1. the ABSOLUTE anchors, derived not remembered (a globally-flipped convention dies here).
    assert geometric_handedness((4, 3, 2, 1), 1) == "S", "[C@H](F)(Cl)Br must be (S)"
    assert geometric_handedness((4, 3, 2, 1), 2) == "R", "[C@@H](F)(Cl)Br must be (R)"
    assert geometric_handedness((1, 4, 3, 2), 2) == "S", "L-alanine (N[C@@H](C)C(=O)O) must be (S)"
    assert geometric_handedness((1, 4, 3, 2), 1) == "R", "D-alanine must be (R)"

    # 2. exhaustive agreement with the shipped slice by an INDEPENDENT method -- the real validation.
    seen: set[str] = set()
    for s in _four_halogen_smiles():
        got, ref = oracle_labels(s), cip_labels(s)
        assert got == ref, f"oracle {got} != cip_labels {ref} for {s}"
        assert len(got) == 1, f"a bare stereocentre must name exactly one centre: {s} -> {got}"
        seen.update(got)
    assert seen == {"R", "S"}, f"battery must be NON-vacuous (both R and S occur), got {seen}"

    # 3. the 3-halogen + H anchor, its mirror, and a two-centre molecule all agree with the shipped slice.
    for s in ("[C@H](F)(Cl)Br", "[C@@H](F)(Cl)Br", "Br[C@H](F)O[C@@H](F)Cl"):
        assert oracle_labels(s) == cip_labels(s), f"oracle disagrees with cip_labels on {s}"
    assert oracle_labels("[C@H](F)(Cl)Br") != oracle_labels("[C@@H](F)(Cl)Br"), "enantiomers must invert"

    # 4. the input guards: a non-permutation and a bad sense are refused (fail-closed, never a guess).
    for bad in ((1, 1, 2, 3), (0, 1, 2, 3), (1, 2, 3)):
        try:
            geometric_handedness(bad, 1)                       # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(f"non-permutation priorities {bad} must raise")
    try:
        geometric_handedness((1, 2, 3, 4), 3)
    except ValueError:
        pass
    else:
        raise AssertionError("a sense other than 1/2 must raise")


def report() -> dict:
    b = battery()
    labelled = [lab for lab in b.values() if lab]
    return {
        "battery_size": len(b),
        "distinct_labels": sorted({x for lab in labelled for x in lab}),
        "chfclbr_at": geometric_handedness((4, 3, 2, 1), 1),
        "L_alanine": geometric_handedness((1, 4, 3, 2), 2),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    for key, value in report().items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
