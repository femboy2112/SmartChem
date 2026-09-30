"""V0.9.5-S16: the canonical-bound differential -- OLD canonicalisation vs NEW, byte for byte.

S16 (barrier amendment, release-blocking) adds automorphism pruning and a node ceiling to
``smartchem.category._canonical_by_individualisation`` and makes canonicalisation budgeted verification work.  The
pruning claims to be IDENTITY-PRESERVING: a pruned child is an automorphic image of an explored sibling, so the set of
leaf certificates -- hence its minimum, hence every canonical form -- is unchanged.  A claim like that is not believed,
it is measured: this harness embeds a VERBATIM copy of the pre-S16 search and ``canonical`` body (from ``22d0bd8``) and
requires the live code to return the byte-identical molecule wherever the old code terminates within a timeout.

Corpus (every family seeded / enumerated, nothing hand-picked after the fact):

* ``named``      benzene, naphthalene, anthracene, adamantane, cubane, cyclohexane, neopentane, coronene,
                 triphenylene, hexamethylbenzene, tri-tert-butylbenzene, tetra-tert-butylmethane (``neo2``), C60;
* ``rings``      bare carbon rings C3..C80 and cycloalkanes C3..C80 with explicit hydrogens;
* ``shapes``     the Wave C4 micro-bench shapes (spiders, stars, binary trees, grids, polyamides);
* ``random``     >= 2,000 seeded molecules with explicit hydrogens: plain random skeletons plus symmetric families
                 (k identical branches on one atom, one branch on every atom of a ring, dimers, dendrimers) -- the
                 families that actually reach the individualisation branch;
* ``registry``   every Molecule held in a module global of the imported package (registered structures, commodity
                 reagents, material-library constants, ...);
* ``literals``   every string literal in ``tests/*.py`` that parses as SMILES;
* ``service``    every distinct Molecule ``canonical()`` was called on while the frozen baseline-freeze service corpus
                 compiled and loaded (``--service fast`` / ``full`` / ``none``).

Every input is fed OLD and NEW under one seeded random relabelling (NEW also under a second one: relabel invariance).
A second pass (``literals`` + corpus targets) is end-to-end: ``resolve_target`` + ``resonance_identity`` with
``Molecule.canonical`` swapped to the OLD body, against the live code.

It also measures what S16 must size: the NEW search-node maximum (the node ceiling), and the ``canonical_work`` a load
charges over the frozen corpus loads -- plain thick, pinned + verified-admission, thin, and pinned re-execution --
cold (every process cache cleared) and warm (the same load again), which must agree (the budget never depends on
what is warm).

Run:  .venv/bin/python experiments/v0_9_5_canonical_differential.py                 # all families, service=fast
      .venv/bin/python experiments/v0_9_5_canonical_differential.py --service full   # + the slow isopentyl family
      .venv/bin/python experiments/v0_9_5_canonical_differential.py --random 4000 --old-timeout 20 --json out.json
Exit 1 on ANY mismatch, on NEW refusing where OLD answered, or on a cold/warm work disagreement.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import re
import signal
import sys
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "experiments")):   # the package, and the frozen corpus harness beside this file
    if _p not in sys.path:
        sys.path.insert(0, _p)

import smartchem.category as cat  # noqa: E402
from smartchem.category import (  # noqa: E402
    _MAX_CANONICAL_CANDIDATES,
    _blocks,
    _canonical_blocks,
    _cost_of,
    _permute_within,
    _refine_partition,
    _wl_colours,
    Bond,
    Molecule,
)
import smartchem.smiles as sm  # noqa: E402
from smartchem.contracts import canonical_digest  # noqa: E402
from smartchem.smiles import _MAX_KEKULE_MATCHINGS, SmilesError, _Atom, _fill_hydrogens  # noqa: E402,F401
from smartchem.verification import _recording_canonical_work  # noqa: E402

# =====================================================================================================================
# OLD -- a VERBATIM copy of the pre-S16 search and canonical body (smartchem/category.py @ 22d0bd8, lines 329-431 and
# 646-680).  The helpers it calls (_blocks, _wl_colours, _refine_partition, _canonical_blocks, _cost_of,
# _permute_within) are untouched by S16 and are imported live.  Do not "fix" anything below: it is the control.
# =====================================================================================================================
_OLD_MAX_INDIVIDUALISATION_LEAVES = 50_000


def _old_canonical_by_individualisation(
    atoms: tuple[str, ...], bonds: frozenset["Bond"]
) -> tuple[tuple[str, ...], tuple[tuple[int, int, int], ...]]:
    n = len(atoms)
    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for b in bonds:
        adjacency[b.i].append((b.j, b.order))
        adjacency[b.j].append((b.i, b.order))
    start = _refine_partition(atoms, bonds, _blocks(_wl_colours(atoms, bonds)))
    symbols = tuple(atoms[i] for cell in start for i in cell)
    best: list[tuple[tuple[int, int, int], ...] | None] = [None]
    leaves = [0]

    def recurse(partition: list[tuple[int, ...]]) -> None:
        if leaves[0] > _OLD_MAX_INDIVIDUALISATION_LEAVES:
            raise NotImplementedError(
                f"canonical relabelling by individualisation exceeded "
                f"{_OLD_MAX_INDIVIDUALISATION_LEAVES:,} leaves; graph too symmetric for this budget"
            )
        partition = _refine_partition(atoms, bonds, partition)
        target = next((k for k, cell in enumerate(partition) if len(cell) > 1), None)
        if target is None:                         # discrete: read the labelling off cell order
            leaves[0] += 1
            perm = [0] * n
            for new, old in enumerate(i for cell in partition for i in cell):
                perm[old] = new
            edges = tuple(sorted(
                (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
                for b in bonds
            ))
            if best[0] is None or edges < best[0]:
                best[0] = edges
            return
        cell = partition[target]
        cellset = set(cell)
        reps: list[int] = []
        seen_twins: set = set()
        for v in cell:
            if any(j in cellset for j, _o in adjacency[v]):
                key: tuple = ("distinct", v)                  # in-cell neighbour -> keep distinct
            else:
                key = ("false-twin", frozenset(adjacency[v]))  # provably swappable
            if key in seen_twins:
                continue
            seen_twins.add(key)
            reps.append(v)
        for v in reps:                             # individualise each choice; minimise over them
            refined_choice = (
                partition[:target]
                + [(v,), tuple(x for x in cell if x != v)]
                + partition[target + 1:]
            )
            recurse(refined_choice)

    recurse(start)
    assert best[0] is not None
    return symbols, best[0]


def old_canonical(self: Molecule) -> Molecule:
    """The pre-S16 ``Molecule.canonical`` body, uncached (``self`` is the molecule)."""
    n = len(self.atoms)
    if n <= 1:
        return self
    blocks = _canonical_blocks(self.atoms, self.bonds)
    budget = _cost_of(blocks)
    if budget > _MAX_CANONICAL_CANDIDATES:
        # refinement alone cannot afford this graph (a vertex-transitive cell it cannot
        # split): fall through to individualisation, nauty's second move (#25). Purely
        # additive -- only molecules that USED to raise here reach this branch.
        symbols, best = _old_canonical_by_individualisation(self.atoms, self.bonds)
        return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in best),
                        self.charge, self.state)
    symbols = tuple(self.atoms[i] for block in blocks for i in block)
    best: tuple | None = None
    for perm in _permute_within(blocks, n):
        # perm[old] = new
        edges = tuple(sorted(
            (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
            for b in self.bonds
        ))
        if best is None or edges < best:
            best = edges
    assert best is not None
    return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in best),
                    self.charge, self.state)


# OLD placement search -- a VERBATIM copy of ``smartchem.smiles._min_constitution_placement`` @ 22d0bd8 (lines 593-710),
# renamed.  S16 (Wave C6 C6-F4) added a DFS-node bound + charge to it; the walk order is untouched, so under the bound
# the returned placement must be the same.  Swapped in for the OLD leg of ``end_to_end``.
def _old_min_constitution_placement(
    atoms: list[_Atom], bonds: list[list[int]], charge: int, max_matchings: int = _MAX_KEKULE_MATCHINGS
) -> tuple[int, ...]:
    """The bond-order assignment that minimises the constitution digest over EVERY multiple-bond placement
    consistent with the fixed sigma-skeleton and per-atom pi-demand -- resonance-canonical for an EXPLICIT
    (unflagged) structure (CANON-KEKULE-01).

    The current aromatic path (:func:`_aromatic_matchings`) resonance-canonicalises only bonds the INPUT flagged
    aromatic (lowercase / ``:``); an explicit-Kekulé drawing (uppercase atoms, ``=`` bonds) carries no flags, so a
    fused aromatic written that way kept its authored double bonds and a molecule could fail to match its OWN
    aromatic spelling.  This closes it WITHOUT aromaticity perception: each atom's pi-demand ``need[a] =
    sum(order-1)`` is fixed by the drawn structure (so the input's H-counts pin a LOCALISED double -- 1-butene's
    is forced onto C1=C2, and a tautomer keeps its distinct H-placement), and every placement satisfying that
    demand exactly is a resonance form of the SAME constitutional molecule.  Minimising the constitution digest
    over them is the canonical representative -- the exact R2 move, generalised from aromatic-flagged bonds to the
    pi-system.  A molecule with a UNIQUE placement (every localised/pinned double, i.e. most molecules) returns its
    drawn orders unchanged, so this is byte-identical for everything except a genuinely resonance-degenerate
    unflagged system.  Refuses (never truncates to a non-deterministic minimum) if the placements exceed the bound.
    """
    n = len(atoms)
    need = [0] * n
    for a, b, o in bonds:
        need[a] += o - 1
        need[b] += o - 1
    incident: list[list[int]] = [[] for _ in range(n)]
    for bi, (a, b, _o) in enumerate(bonds):
        incident[a].append(bi)
        incident[b].append(bi)
    remaining = need[:]
    extra = [0] * len(bonds)
    best: list = [None, None]  # [orders_tuple, digest_key]
    count = [0]

    def _other(bi: int, a: int) -> int:
        x, y, _o = bonds[bi]
        return y if x == a else x

    def _consider() -> None:
        count[0] += 1
        if count[0] > max_matchings:
            raise SmilesError(
                f"structure has more than {max_matchings} resonance placements; a resonance-canonical "
                "identity for it is out of scope (give an aromatic-lowercase SMILES for the aromatic ring)"
            )
        for k in range(len(bonds)):
            bonds[k][2] = 1 + extra[k]
        out_atoms, out_bonds = _fill_hydrogens(atoms, bonds)
        key = canonical_digest(Molecule(tuple(out_atoms), frozenset(out_bonds), charge).canonical())
        if best[1] is None or key < best[1]:
            best[0], best[1] = tuple(1 + e for e in extra), key

    def _atom_distributions(a: int) -> list[list[tuple[int, int]]]:
        """Every way to meet ``remaining[a]`` over a's forward bonds, as lists of ``(bond, extra_order)`` with
        extra_order > 0.  Recurses only over a's OWN bonds (a handful), never over the molecule -- so this stays
        shallow whatever the molecule's size (the atom-walk below is iterative, not recursive)."""
        forward = [bi for bi in incident[a] if _other(bi, a) > a]  # bonds to not-yet-fixed atoms
        out: list[list[tuple[int, int]]] = []

        def _go(idx: int, left: int, acc: list[tuple[int, int]]) -> None:
            if left == 0:
                out.append(list(acc))
                return
            if idx >= len(forward):
                return  # a's demand cannot be met from here -- a dead branch, not a placement
            bi = forward[idx]
            b = _other(bi, a)
            cap = min(left, remaining[b], 2 - extra[bi])  # a bond order never exceeds 3 (extra <= 2)
            for add in range(cap, -1, -1):
                if add:
                    acc.append((bi, add))
                _go(idx + 1, left - add, acc)
                if add:
                    acc.pop()

        _go(0, remaining[a], [])
        return out

    def _next_pi(a: int) -> int:
        while a < n and remaining[a] == 0:
            a += 1
        return a

    def _apply(a: int, dist: list[tuple[int, int]], sign: int) -> None:
        for bi, add in dist:
            extra[bi] += sign * add
            remaining[a] -= sign * add
            remaining[_other(bi, a)] -= sign * add

    # Iterative DFS over the pi-atoms (an explicit list stack, so a large pinned/conjugated system -- which the
    # atom-walk descends one frame per pi-atom -- never blows the Python recursion limit; the earlier recursive
    # walk crashed with an uncaught RecursionError on a ~330-atom cumulene, the red-team fold).
    start = _next_pi(0)
    if start == n:
        _consider()  # no multiple bond at all: the single all-single placement (a saturated molecule)
    else:
        stack: list[dict] = [{"atom": start, "dists": _atom_distributions(start), "idx": -1, "applied": None}]
        while stack:
            top = stack[-1]
            if top["applied"] is not None:                 # backtrack: undo the distribution we had applied
                _apply(top["atom"], top["applied"], -1)
                top["applied"] = None
            top["idx"] += 1
            if top["idx"] >= len(top["dists"]):
                stack.pop()
                continue
            dist = top["dists"][top["idx"]]
            _apply(top["atom"], dist, +1)
            top["applied"] = dist
            nxt = _next_pi(top["atom"] + 1)
            if nxt == n:
                _consider()                                # a complete placement (every pi-demand met)
            else:
                stack.append({"atom": nxt, "dists": _atom_distributions(nxt), "idx": -1, "applied": None})

    if best[0] is None:  # pragma: no cover -- the drawn structure is always a valid placement
        raise SmilesError("could not assign a valid multiple-bond placement to the structure")
    return best[0]



# =====================================================================================================================
# NEW -- the live body, uncached (``__wrapped__`` of the work-transparent cache), with its work measured
# =====================================================================================================================
_NEW_CANONICAL = Molecule.canonical            # the live work-transparent wrapper (restored after every swap)


def new_canonical_with_work(m: Molecule) -> tuple[Molecule, int, bool]:
    """``(canonical form, canonical work charged, took the individualisation branch?)`` -- uncached, cold."""
    with _recording_canonical_work() as frame:
        out = _NEW_CANONICAL.__wrapped__(m)
    individualised = len(m.atoms) > 1 and _cost_of(_canonical_blocks(m.atoms, m.bonds)) > _MAX_CANONICAL_CANDIDATES
    return out, frame.total, individualised


class _Timeout(Exception):
    pass


@contextmanager
def _deadline(seconds: float):
    def _raise(*_a):
        raise _Timeout()
    old = signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


# =====================================================================================================================
# corpus builders
# =====================================================================================================================
_VALENCE = {"C": 4, "N": 3, "O": 2, "S": 2, "Si": 4}


def _mol(atoms, edges) -> Molecule:
    return Molecule(tuple(atoms), frozenset(Bond(min(i, j), max(i, j), o) for (i, j), o in edges.items()))


def relabel(m: Molecule, rng: random.Random) -> Molecule:
    perm = list(range(len(m.atoms)))
    rng.shuffle(perm)
    atoms = [""] * len(m.atoms)
    for old, new in enumerate(perm):
        atoms[new] = m.atoms[old]
    return Molecule(tuple(atoms), frozenset(Bond(perm[b.i], perm[b.j], b.order) for b in m.bonds), m.charge, m.state)


def _hydrogenate(atoms: list, edges: dict) -> Molecule:
    """Fill every heavy atom's spare valence with explicit H (as the parser materialises them)."""
    atoms = list(atoms)
    edges = dict(edges)
    used = [0] * len(atoms)
    for (i, j), o in edges.items():
        used[i] += o
        used[j] += o
    for i in range(len(atoms)):
        for _ in range(max(_VALENCE.get(atoms[i], 0) - used[i], 0)):
            atoms.append("H")
            edges[(i, len(atoms) - 1)] = 1
    return _mol(atoms, edges)


def _random_skeleton(rng: random.Random, n: int, elements=("C", "C", "C", "N", "O", "S")):
    atoms = ["C"] + [rng.choice(elements) for _ in range(n - 1)]
    edges: dict = {}
    deg = [0] * n
    size = 1
    for k in range(1, n):
        cands = [i for i in range(k) if deg[i] < _VALENCE[atoms[i]]]
        if not cands:
            break
        i = rng.choice(cands)
        edges[(i, k)] = 1
        deg[i] += 1
        deg[k] += 1
        size = k + 1
    atoms, deg = atoms[:size], deg[:size]
    for _ in range(rng.randint(0, 2)):                      # ring closures
        if size < 3:
            break
        i, j = sorted(rng.sample(range(size), 2))
        if (i, j) not in edges and deg[i] < _VALENCE[atoms[i]] and deg[j] < _VALENCE[atoms[j]]:
            edges[(i, j)] = 1
            deg[i] += 1
            deg[j] += 1
    for key in list(edges):                                 # a few double bonds
        i, j = key
        if rng.random() < 0.2 and deg[i] < _VALENCE[atoms[i]] and deg[j] < _VALENCE[atoms[j]]:
            edges[key] = 2
            deg[i] += 1
            deg[j] += 1
    return atoms, edges, deg


def _graft(atoms: list, edges: dict, deg: list, at: int, branch) -> None:
    """Attach a copy of ``branch`` (atoms, edges, deg; root = atom 0) to atom ``at`` (in place)."""
    b_atoms, b_edges, _b_deg = branch
    offset = len(atoms)
    atoms.extend(b_atoms)
    deg.extend(_b_deg)
    for (i, j), o in b_edges.items():
        edges[(i + offset, j + offset)] = o
    edges[(at, offset)] = 1
    deg[at] += 1
    deg[offset] += 1


def _branch(rng: random.Random, max_size: int):
    while True:
        b = _random_skeleton(rng, rng.randint(1, max_size))
        if b[2][0] < _VALENCE[b[0][0]]:                     # the root keeps a free valence for the graft
            return b


def random_family(rng: random.Random, kind: str) -> Molecule:
    if kind == "plain":
        atoms, edges, _deg = _random_skeleton(rng, rng.randint(2, 14))
        return _hydrogenate(atoms, edges)
    if kind == "star":                                       # k identical branches on one core atom
        k = rng.randint(2, 4)
        branch = _branch(rng, 4)
        atoms, edges, deg = [rng.choice(("C", "Si"))], {}, [0]
        for _ in range(k):
            _graft(atoms, edges, deg, 0, branch)
        return _hydrogenate(atoms, edges)
    if kind == "ring":                                       # one identical branch on every (or every other) ring atom
        r = rng.randint(3, 10)
        atoms = ["C"] * r
        edges = {(min(i, (i + 1) % r), max(i, (i + 1) % r)): 1 for i in range(r)}
        deg = [2] * r
        if r % 2 == 0 and rng.random() < 0.5:                # alternating Kekule ring
            for i in range(0, r, 2):
                key = (i, i + 1)
                edges[key] = 2
                deg[i] += 1
                deg[i + 1] += 1
        branch = _branch(rng, 3)
        step = rng.choice((1, 1, 2)) if r % 2 == 0 else 1
        for i in range(0, r, step):
            if deg[i] < 4:
                _graft(atoms, edges, deg, i, branch)
        return _hydrogenate(atoms, edges)
    if kind == "dimer":                                      # two copies of one fragment, root to root
        b = _branch(rng, 6)
        atoms, edges, deg = list(b[0]), dict(b[1]), list(b[2])
        offset = len(atoms)
        atoms.extend(b[0])
        deg.extend(b[2])
        for (i, j), o in b[1].items():
            edges[(i + offset, j + offset)] = o
        edges[(0, offset)] = 1
        return _hydrogenate(atoms, edges)
    if kind == "dendrimer":                                  # C(C(branch)3)3-style, depth 2
        branch = _branch(rng, 2)
        atoms, edges, deg = ["C"], {}, [0]
        for _ in range(rng.randint(2, 3)):
            mid = len(atoms)
            atoms.append("C")
            deg.append(0)
            edges[(0, mid)] = 1
            deg[0] += 1
            deg[mid] += 1
            for _ in range(rng.randint(2, 3)):
                _graft(atoms, edges, deg, mid, branch)
        return _hydrogenate(atoms, edges)
    raise ValueError(kind)


_RANDOM_KINDS = ("plain", "plain", "star", "ring", "dimer", "dendrimer")


def random_corpus(seed: int, count: int) -> list:
    rng = random.Random(seed)
    out = []
    for k in range(count):
        kind = _RANDOM_KINDS[k % len(_RANDOM_KINDS)]
        out.append((f"random/{kind}/{k}", random_family(rng, kind)))
    return out


def ring(n: int, hydrogens: bool) -> Molecule:
    atoms = ["C"] * n
    edges = {(min(i, (i + 1) % n), max(i, (i + 1) % n)): 1 for i in range(n)}
    return _hydrogenate(atoms, edges) if hydrogens else _mol(atoms, edges)


def _kekule_carbon_smiles(s: str) -> Molecule:
    """A carbon-only Kekule SMILES (explicit '=', ring digits / %nn, branches) -> bare graph; enough for C60."""
    atoms: list = []
    edges: dict = {}
    stack: list = []
    ring_open: dict = {}
    prev, order, i = None, 1, 0
    while i < len(s):
        ch = s[i]
        if ch == "C":
            atoms.append("C")
            cur = len(atoms) - 1
            if prev is not None:
                edges[(min(prev, cur), max(prev, cur))] = order
            prev, order = cur, 1
        elif ch == "=":
            order = 2
        elif ch == "(":
            stack.append(prev)
        elif ch == ")":
            prev = stack.pop()
        elif ch.isdigit() or ch == "%":
            label = s[i + 1:i + 3] if ch == "%" else ch
            i += 2 if ch == "%" else 0
            if label in ring_open:
                other, o = ring_open.pop(label)
                edges[(min(other, prev), max(other, prev))] = max(o, order)
                order = 1
            else:
                ring_open[label] = (prev, order)
                order = 1
        else:
            raise ValueError(ch)
        i += 1
    return _mol(atoms, edges)


_C60 = ("C12=C3C4=C5C6=C1C7=C8C9=C1C%10=C%11C(=C29)C3=C2C3=C4C4=C5C5=C9C6=C7C6=C7C8=C1C1=C8C%10=C%10C%11=C2C2=C3"
        "C3=C4C4=C5C5=C%11C%12=C(C6=C95)C7=C1C1=C%12C5=C%11C4=C3C3=C5C(=C81)C%10=C23")

def benzenoid_kekule_smiles(cells, seed: int = 1) -> str:
    """An explicit-Kekule (uppercase, '=') SMILES of the benzenoid on hexagon ``cells`` (axial (q, r)), atoms written in
    a seeded random DFS order -- adapted from Wave C6's ``dos_pah.py`` (the C6-F4 reproducer).  Linear acene of L rings:
    ``[(q, 0) for q in range(L)]``; coronene-like flake of radius R: every cell with max(|q|, |r|, |q+r|) <= R."""
    import math
    vid: dict = {}
    edges: set = set()

    def vert(x, y):
        return vid.setdefault((round(x * 1e4), round(y * 1e4)), len(vid))

    for q, r in cells:
        cx, cy = math.sqrt(3) * (q + r / 2.0), 1.5 * r
        ring_ = [vert(cx + math.cos(math.radians(30 + 60 * k)), cy + math.sin(math.radians(30 + 60 * k)))
                 for k in range(6)]
        for a, b in zip(ring_, ring_[1:] + ring_[:1]):
            edges.add((min(a, b), max(a, b)))
    n = len(vid)
    adj: dict = {i: [] for i in range(n)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    colour, todo = {0: 0}, [0]                              # honeycomb is bipartite: augmenting-path matching
    while todo:
        u = todo.pop()
        for v in adj[u]:
            if v not in colour:
                colour[v] = 1 - colour[u]
                todo.append(v)
    match: dict = {}

    def augment(u, seen):
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                if v not in match or augment(match[v], seen):
                    match[v] = u
                    return True
        return False

    for u in (i for i in range(n) if colour[i] == 0):
        if not augment(u, set()):
            raise ValueError("benzenoid without a Kekule structure")
    double = {(min(u, v), max(u, v)) for v, u in match.items()}
    rng = random.Random(seed)
    visited: set = set()
    children: dict = {i: [] for i in range(n)}
    closures: list = []

    def dfs(u, parent):
        visited.add(u)
        around = adj[u][:]
        rng.shuffle(around)
        for v in around:
            if v == parent:
                continue
            if v in visited:
                if not any({a, b} == {u, v} for a, b in closures):
                    closures.append((u, v))
                continue
            children[u].append(v)
            dfs(v, u)

    dfs(0, None)
    opens: dict = {i: [] for i in range(n)}
    order: dict = {}
    for label, (a, b) in enumerate(closures, start=1):
        opens[a].append(label)
        opens[b].append(label)
        order[label] = 2 if (min(a, b), max(a, b)) in double else 1
    written: set = set()

    def emit(u):
        s = "C"
        for label in opens[u]:
            tag = str(label) if label < 10 else "%%%02d" % label
            if label not in written:
                written.add(label)
                s += ("=" if order[label] == 2 else "") + tag
            else:
                s += tag
        parts = [("=" if (min(u, v), max(u, v)) in double else "") + emit(v) for v in children[u]]
        return s + "".join("(" + x + ")" for x in parts[:-1]) + (parts[-1] if parts else "")

    return emit(0)


def acene(length: int, seed: int = 1) -> str:
    return benzenoid_kekule_smiles([(q, 0) for q in range(length)], seed)


def flake(radius: int, seed: int = 1) -> str:
    return benzenoid_kekule_smiles([(q, r) for q in range(-radius, radius + 1) for r in range(-radius, radius + 1)
                                    if abs(q + r) <= radius], seed)


_NAMED_SMILES = {
    "benzene": "c1ccccc1", "naphthalene": "c1ccc2ccccc2c1", "anthracene": "c1ccc2cc3ccccc3cc2c1",
    "adamantane": "C1C2CC3CC1CC(C2)C3", "cubane": "C12C3C4C1C5C2C3C45", "cyclohexane": "C1CCCCC1",
    "neopentane": "CC(C)(C)C", "coronene": "c1cc2ccc3ccc4ccc5ccc6ccc1c7c2c3c4c5c67",
    "triphenylene": "c1ccc2c(c1)c1ccccc1c1ccccc21", "hexamethylbenzene": "Cc1c(C)c(C)c(C)c(C)c1C",
    "tri_tBu_benzene": "CC(C)(C)c1cc(C(C)(C)C)cc(C(C)(C)C)c1",
    "neo2": "C(C(C)(C)C)(C(C)(C)C)(C(C)(C)C)C(C)(C)C",
}


def named_corpus() -> list:
    from smartchem.smiles import parse_smiles
    out = [(f"named/{k}", parse_smiles(s)) for k, s in _NAMED_SMILES.items()]
    c60 = _kekule_carbon_smiles(_C60)
    assert len(c60.atoms) == 60 and len(c60.bonds) == 90, (len(c60.atoms), len(c60.bonds))
    out.append(("named/C60", c60))
    return out


def rings_corpus() -> list:
    return ([(f"rings/bare/C{n}", ring(n, False)) for n in range(3, 81)]
            + [(f"rings/H/C{n}", ring(n, True)) for n in range(3, 81)])


def two_orbit_cell() -> Molecule:
    """A hub bonded to every vertex of a triangular prism and of K3,3: all twelve ring vertices are 1-WL-equivalent
    (3-regular, plus the hub) yet prism and K3,3 vertices are NOT automorphic -- ONE refinement cell holding TWO orbits.
    Symmetric molecules almost never have such a cell, so this is the graph that catches a search pruning a sibling
    that is merely WL-equivalent rather than an automorphic image (a plain chemistry corpus lets that bug pass)."""
    prism = [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3), (0, 3), (1, 4), (2, 5)]
    k33 = [(6 + a, 9 + b) for a in range(3) for b in range(3)]
    return _mol(["C"] * 13, {edge: 1 for edge in prism + k33 + [(v, 12) for v in range(12)]})


def shapes_corpus() -> list:
    """The Wave C4 ``mb_canon.py`` shapes, at sizes the OLD search still finishes (the big ones are timing-only)."""
    def spider(k):
        atoms, edges = ["C"], {}
        for _ in range(k):
            a = len(atoms)
            atoms += ["C", "C"]
            edges[(0, a)] = 1
            edges[(a, a + 1)] = 1
        return _mol(atoms, edges)

    def star(k):
        return _mol(["C"] * (k + 1), {(0, i + 1): 1 for i in range(k)})

    def bintree(d):
        atoms, edges, level = ["C"], {}, [0]
        for _ in range(d):
            nxt = []
            for p in level:
                for _ in range(2):
                    atoms.append("C")
                    edges[(p, len(atoms) - 1)] = 1
                    nxt.append(len(atoms) - 1)
            level = nxt
        return _mol(atoms, edges)

    def grid(k):
        edges = {}
        for r in range(k):
            for c in range(k):
                if c + 1 < k:
                    edges[(r * k + c, r * k + c + 1)] = 1
                if r + 1 < k:
                    edges[(r * k + c, (r + 1) * k + c)] = 1
        return _mol(["C"] * (k * k), edges)

    def polyamide(n):
        atoms, edges, prev = [], {}, None
        for _ in range(n):
            b = len(atoms)
            atoms += ["C", "O", "N", "C"]
            edges.update({(b, b + 1): 2, (b, b + 2): 1, (b + 2, b + 3): 1})
            if prev is not None:
                edges[(prev, b)] = 1
            prev = b + 3
        return _mol(atoms, edges)

    out = [(f"shapes/spider/{k}", spider(k)) for k in range(2, 11)]
    out += [(f"shapes/star/{k}", star(k)) for k in (3, 5, 8, 10)]
    out += [(f"shapes/bintree/{d}", bintree(d)) for d in range(1, 6)]
    out += [(f"shapes/grid/{k}", grid(k)) for k in range(2, 7)]
    out += [(f"shapes/polyamide/{n}", polyamide(n)) for n in (2, 4, 8)]
    out += [(f"shapes/two_orbit_cell/{k}", two_orbit_cell()) for k in range(20)]   # 20 relabellings of it
    return out


def registry_corpus() -> list:
    """Every Molecule held (directly, or one container / ``.molecule`` level deep) in a module global."""
    import smartchem.capability.presets  # noqa: F401 -- import the package surface the service uses
    import smartchem.data.material_library  # noqa: F401
    import smartchem.data.reagents  # noqa: F401
    import smartchem.service  # noqa: F401
    import smartchem.structure  # noqa: F401
    seen: dict = {}

    def take(label, value):
        if isinstance(value, Molecule) and value not in seen:
            seen[value] = label

    for name, module in sorted(sys.modules.items()):
        if not name.startswith("smartchem") or module is None:
            continue
        for attr, value in list(vars(module).items()):
            take(f"registry/{name}.{attr}", value)
            take(f"registry/{name}.{attr}.molecule", getattr(value, "molecule", None))
            if isinstance(value, (tuple, list, frozenset, set)):
                for k, item in enumerate(value):
                    take(f"registry/{name}.{attr}[{k}]", item)
                    take(f"registry/{name}.{attr}[{k}].molecule", getattr(item, "molecule", None))
            elif isinstance(value, dict):
                for k, item in value.items():
                    take(f"registry/{name}.{attr}[{k!r}]", item)
                    take(f"registry/{name}.{attr}[{k!r}].molecule", getattr(item, "molecule", None))
    return [(label, m) for m, label in seen.items()]


_SMILES_CHARS = re.compile(r"^[A-Za-z0-9@+\-\[\]()=#$/\\%.:]{1,160}$")
_LITERAL = re.compile(r"""(?:"([^"\\\n]{1,160})"|'([^'\\\n]{1,160})')""")


def literal_strings() -> list:
    out = set()
    for path in sorted((REPO / "tests").glob("*.py")):
        for a, b in _LITERAL.findall(path.read_text(encoding="utf-8", errors="replace")):
            s = a or b
            if s.startswith("smiles:"):
                s = s[len("smiles:"):]
            if _SMILES_CHARS.match(s) and re.search(r"[BCNOPSFIcnops]", s):
                out.add(s)
    return sorted(out)


def literals_corpus(strings: list, timeout: float) -> list:
    from smartchem.smiles import parse_smiles
    out = []
    for s in strings:
        try:
            with _deadline(timeout):
                out.append((f"literals/{s}", parse_smiles(s)))
        except Exception:  # noqa: BLE001 -- a literal that is not SMILES is simply not in this family
            continue
    return out


# =====================================================================================================================
# the service corpus: every canonical() input, plus the canonical_work each frozen load charges (cold vs warm)
# =====================================================================================================================
def _clear_process_caches() -> None:
    """Empty every process cache above canonical() we know of -- the 'cold' state (modules stay imported)."""
    from smartchem.capability import requirements as req_mod
    from smartchem.experiment import kinetics as kin_mod
    from smartchem.experiment import stock as stock_mod
    from smartchem.smiles import resonance_canonical
    from smartchem.verification import ENUMERATION_CACHE
    _NEW_CANONICAL.cache_clear()           # not Molecule.canonical: the harvest may have swapped in a recorder
    resonance_canonical.cache_clear()
    ENUMERATION_CACHE.clear()
    for fn in (stock_mod._structure_key, req_mod._resolved_name_key, kin_mod._side_key_from_smiles):
        fn.cache_clear()


def install_foreign_transparency() -> list:
    """In-process only (no file edited): re-wrap the three lru caches outside S16's files that sit above canonical()
    -- ``stock._structure_key``, ``requirements._resolved_name_key``, ``kinetics._side_key_from_smiles`` -- in the
    work-transparent cache, to show what their one-line swap would do."""
    from smartchem.capability import requirements as req_mod
    from smartchem.experiment import kinetics as kin_mod
    from smartchem.experiment import stock as stock_mod
    from smartchem.verification import work_transparent_cache
    done = []
    for module, name in ((stock_mod, "_structure_key"), (req_mod, "_resolved_name_key"),
                         (kin_mod, "_side_key_from_smiles")):
        fn = getattr(module, name)
        raw = getattr(fn, "__wrapped__", fn)
        if hasattr(fn, "cache_parameters"):                 # a functools.lru_cache: swap it
            setattr(module, name, work_transparent_cache(maxsize=1 << 16)(raw))
            done.append(f"{module.__name__}.{name}")
    return done


_PASSES = ("cold", "warm", "after_enumeration_clear")


def _canonical_work_of(payload, policy) -> "int | str":
    from smartchem.service import load_response
    try:
        return load_response(copy.deepcopy(payload), policy).receipt.work.canonical_work
    except Exception as exc:  # noqa: BLE001 -- recorded (a refusal is a fact, not a crash)
        return f"refused:{type(exc).__name__}:{str(exc)[:80]}"


def _measure_loads(req, resp) -> dict:
    """canonical_work of the four loads of one answer (plain thick, pinned + verified-admission thick, plain thin,
    pinned re-execution), each cold (every process cache cleared), warm, and after ENUMERATION_CACHE.clear() --
    which the distinct-once law says must be one number."""
    from smartchem.service import response_to_payload
    from smartchem.verification import ENUMERATION_CACHE, VerificationPolicy

    thick = response_to_payload(resp)
    thin = response_to_payload(resp, include_replay=False)
    pinned = dict(expected_request_digest=req.semantic_digest,
                  expected_capability_question_digest=req.capability_question_digest)
    record = {}
    for name, payload, policy in (
        ("plain_thick", thick, VerificationPolicy()),
        ("pinned_va_thick", thick, VerificationPolicy(require_verified_admission=True, **pinned)),
        ("plain_thin", thin, VerificationPolicy()),
        ("pinned_reexec_thick", thick, VerificationPolicy(require_reexecution=True, **pinned)),
    ):
        works = {}
        for pass_ in _PASSES:
            if pass_ == "cold":
                _clear_process_caches()
            elif pass_ == "after_enumeration_clear":
                ENUMERATION_CACHE.clear()
            works[pass_] = _canonical_work_of(payload, policy)
        record[name] = works
    stats_now = ENUMERATION_CACHE.stats()
    record["enumeration_cache"] = {             # C3-F3: what an honest load leaves retained (size units)
        "entries": stats_now.entries, "retained_transforms": stats_now.retained_transforms,
        "retained_size": stats_now.retained_size,
        "max_entry_size": max((size for _c, size in ENUMERATION_CACHE._meta.values()), default=0)}
    return record


def perf_loads(results: dict) -> None:
    """The verification-performance payloads (experiments/v0_9_5_verification_performance.py), built from their own
    request builders: the honest ones join the canonical_work maximum; f_hostile2_45 is recorded apart."""
    import v0_9_5_verification_performance as perf
    from smartchem.service import run_compilation
    from smartchem.verification import VerificationPolicy

    out = results.setdefault("perf_loads", {})
    for name in ("a_tiny_linear", "b1_isopentyl_noprofile", "b2_isopentyl_fitbench", "c1_methyl_acetate_dag",
                 "c2_isopentyl_dag", "d_diels_alder", "f_hostile2_45"):
        t0 = time.time()
        req = perf._build_request(name)
        out[name] = _measure_loads(req, run_compilation(req))
        print(f"  [perf] {name} ({time.time() - t0:.0f}s) {out[name]}", flush=True)
    legacy = json.loads(perf.LEGACY_FIXTURE.read_text())
    record = {}
    for pass_ in _PASSES:
        if pass_ == "cold":
            _clear_process_caches()
        elif pass_ == "after_enumeration_clear":
            from smartchem.verification import ENUMERATION_CACHE
            ENUMERATION_CACHE.clear()
        record[pass_] = _canonical_work_of(legacy, VerificationPolicy())
    out["e_legacy_v08_isopentyl"] = {"plain": record}
    print(f"  [perf] e_legacy_v08_isopentyl {out['e_legacy_v08_isopentyl']}", flush=True)


def service_corpus(which: str, results: dict) -> list:
    """Compile + load every frozen case, harvesting canonical() inputs; record each load's canonical_work."""
    import v0_9_5_baseline_freeze as freeze  # the frozen corpus itself, not a copy

    from smartchem.service import build_decompile_request, build_recompile_request, run_compilation

    harvested: dict = {}
    real = Molecule.canonical

    def recording(self):
        harvested.setdefault(self, None)
        return real(self)

    loads = results.setdefault("service_loads", {})
    for cid, cost, builder, target, kw in freeze._corpus():
        if which == "none" or (which == "fast" and cost == freeze.SLOW):
            continue
        t0 = time.time()
        Molecule.canonical = recording
        try:
            build = build_recompile_request if builder == "recompile" else build_decompile_request
            try:
                req = build(target, **kw)
                resp = run_compilation(req)
            except Exception as exc:  # noqa: BLE001 -- a refused case still contributed its canonical() inputs
                loads[cid] = {"refused": type(exc).__name__}
                continue
            record = _measure_loads(req, resp)
            loads[cid] = record
        finally:
            Molecule.canonical = real
        print(f"  [service] {cid}: {len(harvested)} inputs so far ({time.time() - t0:.1f}s) {loads[cid]}", flush=True)
    return [(f"service/{k}", m) for k, m in enumerate(harvested)]


# =====================================================================================================================
# the differential
# =====================================================================================================================
def differential(corpus: list, old_timeout: float, seed: int, stats: dict, report: list) -> None:
    rng = random.Random(seed)
    for index, (label, m) in enumerate(corpus):
        family = label.split("/")[0]
        s = stats.setdefault(family, Counter())
        s["inputs"] += 1
        if index and index % 500 == 0:
            print(f"    ... {family}: {index}/{len(corpus)}", flush=True)
        a, b = relabel(m, rng), relabel(m, rng)
        t = time.perf_counter()
        try:
            new_a, work, individualised = new_canonical_with_work(a)
            new_err = None
        except NotImplementedError as exc:
            new_a, work, individualised, new_err = None, None, True, exc
        t_new = time.perf_counter() - t
        if individualised:
            s["individualisation_branch"] += 1
        if work is not None:
            if individualised:                      # every node charges the atom count: nodes = work / atoms
                s["max_atom_nodes"] = max(s["max_atom_nodes"], work)
                s["max_nodes"] = max(s["max_nodes"], work // len(a.atoms))
            else:
                s["max_block_candidates"] = max(s["max_block_candidates"], work)
        t = time.perf_counter()
        try:
            with _deadline(old_timeout):
                old_a = old_canonical(a)
            old_err = None
        except _Timeout:
            s["old_timeout"] += 1
            invariant = None
            if new_err is not None:
                s["new_refused_old_timeout"] += 1
            else:                                   # no OLD form to compare: hold NEW to relabel invariance
                invariant = new_canonical_with_work(b)[0] == new_a
                if not invariant:
                    s["MISMATCH_relabel_invariance"] += 1
            report.append({"label": label, "atoms": len(m.atoms), "old": "timeout", "new_s": round(t_new, 4),
                           "new": "refused" if new_err else "ok", "new_work": work, "relabel_invariant": invariant})
            continue
        except (NotImplementedError, RecursionError) as exc:
            # OLD refused (leaf cap) or crashed (its recursive walk: one frame per individualisation -- C6's
            # RecursionError); either way there is no OLD form, so NEW is held to relabel invariance below
            old_a, old_err = None, exc
            if isinstance(exc, RecursionError):
                s["old_recursion_error"] += 1
        t_old = time.perf_counter() - t
        if old_err is not None and new_err is not None:
            s["both_refused"] += 1
            continue
        if old_err is not None:
            # OLD hit its leaf cap; NEW answers.  No OLD form to compare with, so hold the NEW one to relabel
            # invariance instead (a pruning that leaked the input labelling would split the two spellings).
            s["widened_old_refused_new_ok"] += 1
            invariant = new_canonical_with_work(b)[0] == new_a
            if not invariant:
                s["MISMATCH_relabel_invariance"] += 1
            report.append({"label": label, "atoms": len(m.atoms), "old": "refused", "new": "ok", "new_work": work,
                           "relabel_invariant": invariant})
            continue
        if new_err is not None:
            s["REGRESSION_new_refused_old_ok"] += 1
            report.append({"label": label, "atoms": len(m.atoms), "old": "ok", "new": f"refused: {new_err}"})
            continue
        s["compared"] += 1
        s["old_s_x1e6"] += int(t_old * 1e6)
        s["new_s_x1e6"] += int(t_new * 1e6)
        if new_a != old_a or canonical_digest(new_a) != canonical_digest(old_a):
            s["MISMATCH"] += 1
            report.append({"label": label, "atoms": len(m.atoms), "old": canonical_digest(old_a)[:16],
                           "new": canonical_digest(new_a)[:16]})
            continue
        s["byte_identical"] += 1
        new_b, _w, _i = new_canonical_with_work(b)
        if new_b != new_a:
            s["MISMATCH_relabel_invariance"] += 1
            report.append({"label": label, "atoms": len(m.atoms), "relabel_invariance": "broken"})


_NEW_PLACEMENT = sm._min_constitution_placement
_NEW_SEARCH = cat._canonical_by_individualisation       # isotope_refined_key calls the search directly


def _old_search_adapter(atoms, bonds, on_node=None):
    """The OLD search behind the live call signature (``on_node`` did not exist; it is ignored)."""
    return _old_canonical_by_individualisation(atoms, bonds)
_NEW_PLACEMENT_CHARGE = sm.charge_canonical_work      # smiles' own binding: charged ONLY by the placement DFS


def end_to_end(strings: list, timeout: float, stats: dict, report: list, family: str) -> None:
    """resolve_target + resonance_identity with canonical() AND the placement search swapped to the OLD bodies vs the
    live code; the live leg also records the placement-DFS node maximum of any single search (the S16 bound's size)."""
    from smartchem.identity_parse import InputKind, resolve_target
    from smartchem.smiles import isotope_refined_key, resonance_canonical, resonance_identity
    s = stats.setdefault(family, Counter())
    walked = {"now": 0}
    current = {"text": ""}
    hit_labels: set = set()

    def counting_charge(amount):
        walked["now"] += amount
        _NEW_PLACEMENT_CHARGE(amount)

    def measured_placement(*a, **k):
        walked["now"] = 0
        try:
            return _NEW_PLACEMENT(*a, **k)
        finally:
            s["max_placement_dfs_nodes"] = max(s["max_placement_dfs_nodes"], walked["now"])
            if walked["now"] >= sm._MAX_PLACEMENT_DFS_NODES:
                # the S16 bound fired: this search took the placement cap's road (parser: SmilesError; identity
                # path: the literal-key fallback).  Counted by name -- a parsed input's literal key equals its
                # resonance key (idempotence), so only a non-canonical Kekule spelling would show a changed key.
                s["new_placement_bound_hits"] += 1
                hit_labels.add(current["text"][:48])

    def run(text):
        m = resolve_target(text, InputKind.AUTO)
        return canonical_digest(m.canonical()), resonance_identity(m), isotope_refined_key(text)

    for text in strings:
        s["inputs"] += 1
        current["text"] = text
        outs = []
        for mode in ("old", "new"):
            Molecule.canonical = old_canonical if mode == "old" else _NEW_CANONICAL
            cat._canonical_by_individualisation = _old_search_adapter if mode == "old" else _NEW_SEARCH
            sm._min_constitution_placement = _old_min_constitution_placement if mode == "old" else measured_placement
            sm.charge_canonical_work = counting_charge
            resonance_canonical.cache_clear()
            try:
                with _deadline(timeout):
                    outs.append(("ok", run(text)))
            except _Timeout:
                outs.append(("timeout", None))
            except Exception as exc:  # noqa: BLE001 -- the refusal CLASS is the compared fact
                outs.append(("refused", type(exc).__name__))
            finally:
                Molecule.canonical = _NEW_CANONICAL
                cat._canonical_by_individualisation = _NEW_SEARCH
                sm._min_constitution_placement = _NEW_PLACEMENT
                sm.charge_canonical_work = _NEW_PLACEMENT_CHARGE
        resonance_canonical.cache_clear()
        (o_st, o_val), (n_st, n_val) = outs
        if o_st == "timeout":
            s["old_timeout"] += 1
            report.append({family: text, "old": "timeout", "new": n_st})
        elif o_st == "refused" and o_val == "RecursionError" and n_st == "ok":
            s["widened_old_recursion_error"] += 1       # OLD's recursive walk crashed; NEW answers (the C6 fix)
            report.append({family: text, "old": "RecursionError", "new": "ok"})
        elif o_st == n_st and o_val == n_val:
            s["identical"] += 1
        else:
            s["MISMATCH"] += 1
            report.append({family: text, "old": [o_st, o_val], "new": [n_st, n_val]})
    if hit_labels:
        report.append({f"{family}_placement_bound_hits": sorted(hit_labels)})


def timings(results: dict) -> None:
    """NEW wall time on the shapes Waves C4/C6 measured OLD on: neo2 (> 40 s), the 320-ring (~50 s), the 21-atom
    spider (~6 s), [S](tBu)5 (391 s, then a leaf-cap refusal), explicit-Kekule polyacene L=30 (8 s) / L=50 (1,425 s),
    [CH1000] and C*1000 (RecursionError after 8 s / 40 s)."""
    from smartchem.experiment.stock import structure_key
    from smartchem.smiles import parse_smiles
    out = results.setdefault("timings_new_s", {})

    def clock(name, fn):
        _clear_process_caches()
        t = time.perf_counter()
        try:
            with _deadline(900):
                fn()
            out[name] = round(time.perf_counter() - t, 4)
        except _Timeout:
            out[name] = "timeout>900s"
        except (NotImplementedError, SmilesError, RecursionError) as exc:
            out[name] = f"{type(exc).__name__} ({time.perf_counter() - t:.3f}s): {str(exc)[:110]}"
        print(f"  [timing] {name}: {out[name]}", flush=True)

    tbu = "C(C)(C)C"
    clock("neo2_parse", lambda: parse_smiles(_NAMED_SMILES["neo2"]))
    clock("ring320_canonical", lambda: ring(320, False).canonical())
    spiders = dict(shapes_corpus())
    clock("spider10_canonical(21 atoms)", lambda: spiders["shapes/spider/10"].canonical())
    clock("C60_canonical", lambda: _kekule_carbon_smiles(_C60).canonical())
    clock("coronene_parse", lambda: parse_smiles(_NAMED_SMILES["coronene"]))
    clock("tri_tBu_benzene_parse", lambda: parse_smiles(_NAMED_SMILES["tri_tBu_benzene"]))
    clock("S(tBu)4_parse", lambda: parse_smiles("[S]" + f"({tbu})" * 3 + tbu))
    clock("S(tBu)5_parse", lambda: parse_smiles("[S]" + f"({tbu})" * 4 + tbu))
    clock("S(tBu)6_parse", lambda: parse_smiles("[S]" + f"({tbu})" * 5 + tbu))
    for length in (24, 30, 50):
        smiles = acene(length)
        clock(f"polyacene_L{length}_parse({len(smiles)} chars)", lambda s=smiles: parse_smiles(s))
    clock("flake_r3_parse", lambda: parse_smiles(flake(3)))
    clock("[CH1000]_parse", lambda: parse_smiles("[CH1000]"))
    clock("C*300_parse", lambda: parse_smiles("C" * 300))
    clock("C*300_structure_key", lambda: structure_key(parse_smiles("C" * 300)))


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--service", choices=("none", "fast", "full"), default="fast")
    ap.add_argument("--random", type=int, default=2400, help="seeded random molecules (>= 2000 for the gate)")
    ap.add_argument("--seed", type=int, default=16)
    ap.add_argument("--old-timeout", type=float, default=10.0)
    ap.add_argument("--foreign-transparency", action="store_true",
                    help="swap any remaining plain lru cache above canonical() for a work-transparent one (in-process; "
                         "a no-op since the S16 follow-up made all three natively work-transparent)")
    ap.add_argument("--perf", action="store_true",
                    help="also measure canonical_work on the verification-performance payloads")
    ap.add_argument("--families", default=None,
                    help="comma list of canonical-level families to run (default: all); end_to_end/placement always run")
    ap.add_argument("--max-acene", type=int, default=30, help="largest explicit-Kekule acene in the placement family")
    ap.add_argument("--skip-timings", action="store_true")
    ap.add_argument("--json", default=None, help="write the full results document here")
    args = ap.parse_args(argv)

    # which tree is measured (the dev venv's editable install points elsewhere; REPO is put first on sys.path above)
    results: dict = {"argv": argv, "smartchem_file": cat.__file__, "node_cap": cat._MAX_INDIVIDUALISATION_NODES}
    print(f"[proof] measuring smartchem.category from {cat.__file__}", flush=True)
    if args.foreign_transparency:
        results["foreign_transparency"] = install_foreign_transparency()
    stats: dict = {}
    report: list = []
    t0 = time.time()
    strings = literal_strings()
    families = [
        ("named", named_corpus),
        ("rings", rings_corpus),
        ("shapes", shapes_corpus),
        ("random", lambda: random_corpus(args.seed, args.random)),
        ("registry", registry_corpus),
        ("literals", lambda: literals_corpus(strings, 10.0)),
        ("service", lambda: service_corpus(args.service, results)),
    ]
    if args.perf:
        perf_loads(results)
    wanted = set(args.families.split(",")) if args.families else None
    for name, build in families:
        if wanted is not None and name not in wanted:
            continue
        t = time.time()
        corpus = build()
        differential(corpus, args.old_timeout, args.seed, stats, report)
        print(f"[{name}] {len(corpus)} inputs in {time.time() - t:.1f}s: {dict(stats.get(name, {}))}", flush=True)
    import v0_9_5_baseline_freeze as freeze
    targets = sorted({t for _c, _k, _b, t, _kw in freeze._corpus()})
    # the C6-F4 placement family: explicit-Kekule acenes (two atom orders each) and small flakes, every size the OLD
    # search still finishes -- the placement bound must leave all of them byte-identical
    benzenoids = [acene(L, seed) for L in range(2, args.max_acene + 1) for seed in (1, 2)] + [flake(1), flake(2)]
    end_to_end(strings + list(_NAMED_SMILES.values()) + targets, args.old_timeout * 6, stats, report, "end_to_end")
    print(f"[end_to_end] {dict(stats['end_to_end'])}", flush=True)
    end_to_end(benzenoids, args.old_timeout * 6, stats, report, "placement")
    print(f"[placement] {dict(stats['placement'])}", flush=True)
    if not args.skip_timings:
        timings(results)

    total = Counter()
    for fam, s in stats.items():
        if fam not in ("end_to_end", "placement"):
            total.update({k: v for k, v in s.items() if not k.startswith("max_")})
    old_s, new_s = total["old_s_x1e6"] / 1e6, total["new_s_x1e6"] / 1e6
    results.update({
        "families": {k: dict(v) for k, v in stats.items()},
        "total": dict(total),
        "old_over_new_time_ratio": round(old_s / new_s, 3) if new_s else None,
        "max_nodes_new": max((s.get("max_nodes", 0) for s in stats.values()), default=0),
        "max_atom_nodes_new": max((s.get("max_atom_nodes", 0) for s in stats.values()), default=0),
        "max_placement_dfs_nodes": {k: stats[k].get("max_placement_dfs_nodes", 0) for k in ("end_to_end", "placement")},
        "max_block_candidates_new": max((s.get("max_block_candidates", 0) for s in stats.values()), default=0),
        "report": report,
        "elapsed_s": round(time.time() - t0, 1),
    })
    # every load: cold == warm == after an enumeration-cache clear; the honest maximum excludes the hostile payload
    loads = {f"service/{cid}": rec for cid, rec in results.get("service_loads", {}).items()}
    loads.update({f"perf/{name}": rec for name, rec in results.get("perf_loads", {}).items()})
    passes = {cid: {load: v for load, v in rec.items() if isinstance(v, dict) and "cold" in v}
              for cid, rec in loads.items() if isinstance(rec, dict)}
    bad_work = {cid: rec for cid, rec in passes.items() if any(len(set(map(str, v.values()))) != 1 for v in rec.values())}
    honest = {(cid, load): v["cold"] for cid, rec in passes.items() if cid != "perf/f_hostile2_45"
              for load, v in rec.items() if isinstance(v["cold"], int)}
    worst = max(honest, key=honest.get, default=None)
    results["canonical_work_cold_warm_disagreements"] = bad_work
    results["canonical_work_honest_max"] = {"value": honest.get(worst, 0), "load": worst}
    results["canonical_work_hostile_f_hostile2_45"] = passes.get("perf/f_hostile2_45")
    failed = (total["MISMATCH"] + total["MISMATCH_relabel_invariance"] + total["REGRESSION_new_refused_old_ok"]
              + stats.get("end_to_end", Counter())["MISMATCH"] + stats.get("placement", Counter())["MISMATCH"]
              + len(bad_work))
    results["verdict"] = "PASS" if failed == 0 else "FAIL"
    print(json.dumps({k: v for k, v in results.items() if k != "report"}, indent=1, sort_keys=True, default=str))
    for row in report[:60]:
        print("  ", row)
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1, sort_keys=True, default=str))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
