"""An INDEPENDENT structural witness for the 26th-class alcohol dehydration (#116, ``alcohol -> alkene + H2O``).

Standalone: it is NOT registered into the reaction-type oracle and nothing in production imports it.  It exists so the
production verdict (:func:`smartchem.elimination._dehydrates_to`, shared by the generator's edge certificate and the
oracle recognizer) can be cross-checked by a route that is NOT common-mode with it.

PRODUCTION'S ROUTE: scan the PRECURSOR for guarded hydroxyl sites, apply the FORWARD elimination as a graph op, and
compare to the target by ``resonance_identity`` (the repo's canonical-identity subsystem).

THIS WITNESS'S ROUTE (each step deliberately different):
  1. STOICHIOMETRY on the formula dicts: ``precursor.formula == target.formula + H2O``, both neutral and stateless.
  2. CYCLE RANK unchanged (``mu = bonds - atoms + 1``): a 1,2-elimination forms no ring and opens none.  This alone
     rejects a ring-closing etherification (butane-1,4-diol -> THF + H2O).
  3. A FUNCTIONAL-GROUP CENSUS computed on each molecule alone and differenced: sp3 alcohols -1; isolated C=C +1;
     ring-conjugated C=C, other hydroxyls (enol / phenol / acid), ethers, carbonyls and multiply-unsaturated atoms
     all unchanged.  "Ring-conjugated" is decided by TARJAN BRIDGE-FINDING on the subgraph of pi-capable atoms (a C=C
     that is not a bridge there lies on a fully pi-capable ring); production instead runs a path search from the new
     bond on the product.
  4. THE RETRO DIRECTION with an OWN ISOMORPHISM TEST: for each eligible C=C of the TARGET (both carbons sp2 with no
     other multiple bond, only C/H substituents, not on a three-membered ring by a smallest-cycle BFS, not
     ring-conjugated), add H-OH in BOTH orientations as a raw graph and ask whether it is isomorphic to the precursor
     by this module's own refinement + backtracking matcher -- never ``Molecule.canonical`` / ``resonance_identity``.
The verdict is the conjunction 1-4; each check is exposed on :class:`DehydrationWitnessResult`.

RESIDUAL SHARED ASSUMPTIONS (not zero): both routes read the same explicit-H Kekule ``Molecule`` graph and share the
class DEFINITION (H-OH lost across two adjacent carbons, the new C=C carrying only C/H substituents, no aromatising
or three-membered-ring closure).  Independence is in the direction (retro vs forward), the detection algorithms and
the identity test.  Because the isomorphism is exact on Kekule bond orders, a substituted arene drawn with
DIFFERENT Kekule assignments in precursor and target can make the witness say False where production (resonance
identity) says True -- a disagreement in the safe direction, not a false accept.

This module imports ONLY ``Molecule`` from ``smartchem.category``.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass

from .category import Molecule

_WATER_FORMULA = {"H": 2, "O": 1}

Graph = dict[int, dict[int, int]]            # atom -> {neighbour: bond order}


def _graph(mol: Molecule) -> Graph:
    g: Graph = {i: {} for i in range(len(mol.atoms))}
    for b in mol.bonds:
        g[b.i][b.j] = b.order
        g[b.j][b.i] = b.order
    return g


# --------------------------------------------------------------------------------------------------------------------
# Ring facts: Tarjan bridges on a vertex-induced subgraph, and the smallest ring through a bond.
# --------------------------------------------------------------------------------------------------------------------

def _bridges_within(g: Graph, keep: set[int]) -> set[frozenset[int]]:
    """Every bridge of the subgraph induced by ``keep`` (iterative Tarjan low-link)."""
    disc: dict[int, int] = {}
    low: dict[int, int] = {}
    out: set[frozenset[int]] = set()
    clock = 0
    for root in sorted(keep):
        if root in disc:
            continue
        disc[root] = low[root] = clock
        clock += 1
        stack = [(root, -1, iter(sorted(n for n in g[root] if n in keep)))]
        while stack:
            node, parent, it = stack[-1]
            pushed = False
            for nxt in it:
                if nxt == parent:
                    continue
                if nxt in disc:
                    low[node] = min(low[node], disc[nxt])
                else:
                    disc[nxt] = low[nxt] = clock
                    clock += 1
                    stack.append((nxt, node, iter(sorted(n for n in g[nxt] if n in keep))))
                    pushed = True
                    break
            if pushed:
                continue
            stack.pop()
            if stack:
                up = stack[-1][0]
                low[up] = min(low[up], low[node])
                if low[node] > disc[up]:
                    out.add(frozenset((up, node)))
    return out


def _smallest_ring_size(g: Graph, a: int, b: int) -> int | None:
    """Size of the smallest ring through bond ``a--b`` (BFS distance from ``a`` to ``b`` without that bond, + 1)."""
    dist = {a: 0}
    queue = deque([a])
    while queue:
        cur = queue.popleft()
        for nxt in g[cur]:
            if {cur, nxt} == {a, b} or nxt in dist:
                continue
            dist[nxt] = dist[cur] + 1
            if nxt == b:
                return dist[nxt] + 1
            queue.append(nxt)
    return None


def _pi_capable_atoms(atoms, g: Graph) -> set[int]:
    """Atoms that can sit in a fully conjugated ring: any atom with a multiple bond, and any non-carbon heavy atom."""
    return {i for i, el in enumerate(atoms)
            if el != "H" and (el != "C" or any(o >= 2 for o in g[i].values()))}


def _cc_doubles(atoms, g: Graph) -> list[frozenset[int]]:
    return sorted({frozenset((i, j)) for i in g for j, o in g[i].items()
                   if o == 2 and atoms[i] == "C" and atoms[j] == "C"}, key=sorted)


# --------------------------------------------------------------------------------------------------------------------
# The census (one molecule at a time).
# --------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class DehydrationCensus:
    cycle_rank: int
    sp3_alcohols: int              # O-H on a carbon with four single bonds
    other_hydroxyls: int           # O-H on any other atom (enol, phenol, acid, hydroperoxide, ...)
    ethers: int                    # O with exactly two carbon neighbours, both single bonds
    carbonyls: int                 # C=O double bonds
    isolated_cc: int               # C=C that are bridges of the pi-capable subgraph
    ring_conjugated_cc: int        # C=C on a fully pi-capable ring
    multiply_unsaturated: int      # atoms whose bonds carry >= 2 extra orders (allene centre, alkyne C, ketene C)


def dehydration_census(mol: Molecule) -> DehydrationCensus:
    atoms = mol.atoms
    g = _graph(mol)
    sp3_oh = other_oh = ethers = carbonyls = 0
    for o, el in enumerate(atoms):
        if el != "O":
            continue
        nbrs = g[o]
        hs = [n for n in nbrs if atoms[n] == "H"]
        heavy = [n for n in nbrs if atoms[n] != "H"]
        if len(nbrs) == 2 and len(hs) == 1 and len(heavy) == 1 and nbrs[heavy[0]] == 1:
            c = heavy[0]
            if atoms[c] == "C" and len(g[c]) == 4 and all(v == 1 for v in g[c].values()):
                sp3_oh += 1
            else:
                other_oh += 1
        elif len(nbrs) == 2 and len(heavy) == 2 and all(atoms[n] == "C" and nbrs[n] == 1 for n in heavy):
            ethers += 1
    for i, el in enumerate(atoms):
        if el == "C":
            carbonyls += sum(1 for n, v in g[i].items() if v == 2 and atoms[n] == "O")
    pi = _pi_capable_atoms(atoms, g)
    bridges = _bridges_within(g, pi)
    doubles = _cc_doubles(atoms, g)
    isolated = sum(1 for d in doubles if d in bridges)
    unsat = sum(1 for i in g if sum(v - 1 for v in g[i].values()) >= 2)
    return DehydrationCensus(
        cycle_rank=len(mol.bonds) - len(atoms) + 1,
        sp3_alcohols=sp3_oh,
        other_hydroxyls=other_oh,
        ethers=ethers,
        carbonyls=carbonyls,
        isolated_cc=isolated,
        ring_conjugated_cc=len(doubles) - isolated,
        multiply_unsaturated=unsat,
    )


def _census_deltas_match(cp: DehydrationCensus, ct: DehydrationCensus) -> bool:
    return (ct.sp3_alcohols == cp.sp3_alcohols - 1
            and ct.isolated_cc == cp.isolated_cc + 1
            and ct.ring_conjugated_cc == cp.ring_conjugated_cc
            and ct.other_hydroxyls == cp.other_hydroxyls
            and ct.ethers == cp.ethers
            and ct.carbonyls == cp.carbonyls
            and ct.multiply_unsaturated == cp.multiply_unsaturated)


def _formula_gap_is_water(precursor: Molecule, target: Molecule) -> bool:
    total = Counter({k: v for k, v in target.formula.items() if v})
    for el, n in _WATER_FORMULA.items():
        total[el] += n
    have = Counter({k: v for k, v in precursor.formula.items() if v})
    return (total == have and precursor.charge == 0 and target.charge == 0
            and not precursor.state and not target.state)


# --------------------------------------------------------------------------------------------------------------------
# Retro hydration of the target's eligible C=C sites, and the witness's own isomorphism test.
# --------------------------------------------------------------------------------------------------------------------

def eligible_alkene_sites(mol: Molecule) -> tuple[tuple[int, int], ...]:
    """The target's C=C bonds a 1,2-dehydration could have formed, read off the target alone."""
    atoms = mol.atoms
    g = _graph(mol)
    bridges = _bridges_within(g, _pi_capable_atoms(atoms, g))
    out: list[tuple[int, int]] = []
    for d in _cc_doubles(atoms, g):
        a, b = sorted(d)
        ok = True
        for x, partner in ((a, b), (b, a)):
            others = [n for n in g[x] if n != partner]
            if len(g[x]) != 3 or any(g[x][n] != 1 for n in others):
                ok = False                             # sp2 with explicit H, no second multiple bond (no cumulene)
            elif any(atoms[n] not in ("C", "H") for n in others):
                ok = False                             # the alkene carries only C/H substituents
        if not ok or d not in bridges:
            continue                                   # a ring-conjugated C=C is not a dehydration product here
        if _smallest_ring_size(g, a, b) == 3:
            continue
        out.append((a, b))
    return tuple(out)


def _hydrated(mol: Molecule, c_oh: int, c_h: int) -> tuple[list[str], Graph]:
    atoms = list(mol.atoms)
    g = {i: dict(v) for i, v in _graph(mol).items()}
    g[c_oh][c_h] = g[c_h][c_oh] = 1
    o, h_o, h_c = len(atoms), len(atoms) + 1, len(atoms) + 2
    atoms += ["O", "H", "H"]
    g[o] = {c_oh: 1, h_o: 1}
    g[h_o] = {o: 1}
    g[h_c] = {c_h: 1}
    g[c_oh][o] = 1
    g[c_h][h_c] = 1
    return atoms, g


def _isomorphic(atoms_a: list[str], ga: Graph, atoms_b: list[str], gb: Graph) -> bool:
    """Exact (element, bond-order)-labelled graph isomorphism: invariant-partitioned backtracking.  The initial colour
    of an atom is (element, sorted multiset of (bond order, neighbour element)); candidates are restricted to equal
    colours and every mapped edge is checked in both directions, so the result is an actual bijection."""
    n = len(atoms_a)
    if n != len(atoms_b) or Counter(atoms_a) != Counter(atoms_b):
        return False
    if sum(len(v) for v in ga.values()) != sum(len(v) for v in gb.values()):
        return False

    def colour(atoms, g, i):
        return (atoms[i], tuple(sorted((o, atoms[j]) for j, o in g[i].items())))

    ca = [colour(atoms_a, ga, i) for i in range(n)]
    cb = [colour(atoms_b, gb, j) for j in range(n)]
    if Counter(ca) != Counter(cb):
        return False
    # visit A in BFS order from its rarest-colour atom, so each new atom is usually adjacent to a mapped one
    freq = Counter(ca)
    order: list[int] = []
    placed: set[int] = set()
    for start in sorted(range(n), key=lambda i: (freq[ca[i]], i)):
        if start in placed:
            continue
        queue = deque([start])
        placed.add(start)
        while queue:
            cur = queue.popleft()
            order.append(cur)
            for nxt in sorted(ga[cur]):
                if nxt not in placed:
                    placed.add(nxt)
                    queue.append(nxt)
    fwd: dict[int, int] = {}
    rev: dict[int, int] = {}

    def extend(k: int) -> bool:
        if k == n:
            return True
        i = order[k]
        mapped_nbrs = [(x, o) for x, o in ga[i].items() if x in fwd]
        if mapped_nbrs:
            anchor = fwd[mapped_nbrs[0][0]]
            candidates = [j for j in gb[anchor] if j not in rev]
        else:
            candidates = [j for j in range(n) if j not in rev]
        for j in candidates:
            if cb[j] != ca[i]:
                continue
            if any(gb[j].get(fwd[x]) != o for x, o in mapped_nbrs):
                continue
            if any(y in rev and ga[i].get(rev[y]) != o for y, o in gb[j].items()):
                continue
            fwd[i], rev[j] = j, i
            if extend(k + 1):
                return True
            del fwd[i], rev[j]
        return False

    return extend(0)


# --------------------------------------------------------------------------------------------------------------------
# The verdict.
# --------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class DehydrationWitnessResult:
    is_dehydration: bool
    water_stoichiometry: bool
    cycle_rank_unchanged: bool
    census_deltas_match: bool
    hydration_recovers_precursor: bool
    note: str = ""


def witnesses_dehydration(precursor: Molecule, target: Molecule) -> DehydrationWitnessResult:
    """Is ``precursor -> target + H2O`` a 1,2-dehydration of an alcohol, judged by the independent route?"""
    stoich = _formula_gap_is_water(precursor, target)
    cp, ct = dehydration_census(precursor), dehydration_census(target)
    rank = cp.cycle_rank == ct.cycle_rank
    deltas = _census_deltas_match(cp, ct)
    recovers = False
    if stoich:
        atoms_p, gp = list(precursor.atoms), _graph(precursor)
        for a, b in eligible_alkene_sites(target):
            for c_oh, c_h in ((a, b), (b, a)):
                atoms_h, gh = _hydrated(target, c_oh, c_h)
                if _isomorphic(atoms_h, gh, atoms_p, gp):
                    recovers = True
                    break
            if recovers:
                break
    verdict = stoich and rank and deltas and recovers
    failed = [name for name, ok in (("water_stoichiometry", stoich), ("cycle_rank_unchanged", rank),
                                    ("census_deltas_match", deltas),
                                    ("hydration_recovers_precursor", recovers)) if not ok]
    return DehydrationWitnessResult(verdict, stoich, rank, deltas, recovers,
                                    "" if verdict else "failed: " + ", ".join(failed))
