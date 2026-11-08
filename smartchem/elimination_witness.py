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
  4. THE RETRO DIRECTION with an OWN ISOMORPHISM TEST: for each eligible ORIENTATION of a TARGET C=C
     (:func:`eligible_hydrations`), add H-OH as a raw graph and ask whether it is isomorphic to the precursor by this
     module's own refinement + backtracking matcher -- never ``Molecule.canonical`` / ``resonance_identity``.  An
     orientation is eligible only inside the same POSITIVE SAFE-SET production enforces (both alkene carbons sp2 with no
     other multiple bond and only C/H substituents, not ring-conjugated; and, read off the TARGET with
     ``c_oh`` = C_alpha, ``c_h`` = C_beta, A(c_h) = the carbonyl / carboxyl / ester / nitrile carbons on ``c_h``
     and E = their O/N atoms):
       (M) a MOLECULE-WIDE heteroatom whitelist -- every non-C/H atom of the target is in E, so a remote OH, ether,
           ester, halogen, N, S, Si, B, P ... anywhere refuses;
       (a) monocyclic-or-acyclic ring context of ``c_oh`` / ``c_h``; (b) ring size >= 5; (c) no ring <= 4 next door;
       (d) no quaternary and (e) no hydroxyl-bearing carbon neighbour of ``c_oh``;
       (e') carbon-only radius-2 neighbourhood, A(c_h)'s own O/N excepted;
       (R) RADIUS-1 RING SATURATION (replaces r3's (f')): every ring atom among ``c_oh``, ``c_h`` and their heavy
           neighbours sits in a MONOCYCLIC system (no fused / bridged / spiro ring next door), and that ring is
           either a benzenoid (6 C, each with exactly one in-ring double bond) containing neither alkene carbon -- an
           untouched arene -- or keeps k > 2 (ring size 6 or 7) / k > 1 (any other size) atoms that are NOT
           pi-capable in the target (pi-capable = any non-carbon heavy atom, or a carbon with a bond of order >= 2);
       (S) no sp / cumulene carbon next door -- every carbon neighbour of ``c_oh`` / ``c_h`` outside A(c_h) has no
           triple bond and at most one double bond;
       (g) closed-shell unlabelled species, by the witness's own valence table),
     decided by the witness's OWN algorithms: Tarjan bridges + union-find ring systems (a monocyclic system's atom
     set is its ring), edge-deletion BFS ring sizes -- where production uses edge-deletion connectivity, ring-bond
     flood fill and vertex-deletion BFS.
The verdict is the conjunction 1-4; each check is exposed on :class:`DehydrationWitnessResult`.

RESIDUAL SHARED ASSUMPTIONS (not zero): both routes read the same explicit-H Kekule ``Molecule`` graph and share the
class DEFINITION (H-OH lost across two adjacent carbons, the new C=C carrying only C/H substituents, the safe-set
conditions (a)-(g), (M), (R), (S)).  Independence is in the direction (retro vs forward), the detection algorithms and
the identity test.  Because the isomorphism is exact on Kekule bond orders, a substituted arene drawn with
DIFFERENT Kekule assignments in precursor and target can make the witness say False where production (resonance
identity) says True -- a disagreement in the safe direction, not a false accept.  The round-5 conditions widen the
shared surface rather than narrow it: the acyl signatures defining A(c_h) and E, the pi-capable predicate, the
benzenoid predicate and the k thresholds (<= 2 for 6- and 7-rings, <= 1 otherwise) are taken from the same spec
production implements, so a mistake IN that spec -- an over-generous excuse, a threshold one too low -- is
common-mode and invisible to this cross-check.  The benzenoid test reads Kekule double bonds, but every Kekule
spelling of an isolated benzene ring passes it, and fused arenes are refused before it is consulted.

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

class _RingFacts:
    """Ring facts of one graph by the witness's own route: Tarjan bridges give the ring bonds, a union-find over the
    ring bonds gives the ring systems (a system is MONOCYCLIC iff its ring-bond count equals its atom count), and
    ring sizes come from an edge-deletion BFS."""

    def __init__(self, atoms, g: Graph) -> None:
        self.g = g
        heavy = {i for i, el in enumerate(atoms) if el != "H"}
        bridges = _bridges_within(g, heavy)
        self.ring_bonds = [(i, j) for i in heavy for j in g[i] if j in heavy and i < j
                           and frozenset((i, j)) not in bridges]
        parent = {i: i for i in heavy}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, j in self.ring_bonds:
            parent[find(i)] = find(j)
        self._root = {i: find(i) for i in heavy}
        self._members: dict[int, set[int]] = {}
        self._edges: Counter = Counter()
        for i, j in self.ring_bonds:
            r = self._root[i]
            self._members.setdefault(r, set()).update((i, j))
            self._edges[r] += 1

    def ring_neighbours(self, x: int) -> list[int]:
        return sorted(j for i, j in self.ring_bonds if i == x) + sorted(i for i, j in self.ring_bonds if j == x)

    def is_monocyclic_or_acyclic(self, x: int) -> bool:
        if not self.ring_neighbours(x):
            return True
        r = self._root[x]
        return self._edges[r] == len(self._members[r])

    def smallest_ring(self, x: int) -> int | None:
        sizes = [_smallest_ring_size(self.g, x, u) for u in self.ring_neighbours(x)]
        sizes = [z for z in sizes if z is not None]
        return min(sizes) if sizes else None

    def ring_system(self, x: int) -> tuple[frozenset[int], bool] | None:
        """``(atoms of x's ring system, is_monocyclic)``, or ``None`` when ``x`` lies on no ring.  A monocyclic system's
        atom set IS its single ring -- no path search needed, the union-find already drew the outline."""
        if not self.ring_neighbours(x):
            return None
        r = self._root[x]
        return frozenset(self._members[r]), self._edges[r] == len(self._members[r])


def _orientation_is_safe(atoms, g: Graph, rf: _RingFacts, pi: set[int], c_oh: int, c_h: int) -> bool:
    """The safe-set conditions for hydrating ``c_oh = c_h`` (OH on ``c_oh``), read off the TARGET.  Ring structure and
    every neighbour other than the two alkene carbons are the same in target and precursor.

    (M) every non-C/H atom of the molecule is in E, the O/N excused by an acyl carbon in A(c_h)
        (:func:`_excused_acyl`) -- a remote OH, ether, ester elsewhere, halogen, N, S, Si, B, P ... refuses;
    (a) ``c_oh`` and ``c_h`` are each acyclic or in a monocyclic ring system; (b) that ring has >= 5 members;
    (c) no carbon neighbour of either (other than each other) lies on a ring of size <= 4;
    (d) no quaternary carbon neighbour of ``c_oh``; (e) no hydroxyl-bearing carbon neighbour of ``c_oh``;
    (R) for every ring atom of S = {c_oh, c_h} + their heavy neighbours: its ring system is monocyclic, and that ring R
        is either benzenoid without ``c_oh`` / ``c_h`` (an untouched arene) or has k > 2 (|R| in 6, 7) / k > 1 (any
        other size) atoms that are not pi-capable in the target;
    (S) every carbon neighbour of ``c_oh`` / ``c_h`` outside A(c_h) (and not the partner) carries no triple bond and
        at most one double bond -- no sp / cumulene carbon next door;
    (e') the radius-2 neighbourhood is carbon, A(c_h)'s own O/N excepted (:func:`_radius_two_is_carbon`)."""
    excused = _excused_acyl(atoms, g, c_oh, c_h)
    allowed = set().union(*excused.values())
    if any(el not in ("C", "H") and i not in allowed for i, el in enumerate(atoms)):
        return False                                   # (M) a heteroatom the class has no excuse for, anywhere
    for x in (c_oh, c_h):
        if not rf.is_monocyclic_or_acyclic(x):
            return False                               # (a) bridgehead / fusion / spiro / polycyclic system
        size = rf.smallest_ring(x)
        if size is not None and size < 5:
            return False                               # (b)
    for x, partner in ((c_oh, c_h), (c_h, c_oh)):
        for n in g[x]:
            if n == partner or atoms[n] != "C":
                continue
            size = rf.smallest_ring(n)
            if size is not None and size <= 4:
                return False                           # (c)
    for n in g[c_oh]:
        if n == c_h or atoms[n] != "C":
            continue
        if len(g[n]) == 4 and all(atoms[m] != "H" for m in g[n]):
            return False                               # (d) quaternary neighbour of C_alpha
        if any(atoms[o] == "O" and any(atoms[h] == "H" for h in g[o]) for o in g[n]):
            return False                               # (e) vicinal hydroxyl
    shell = {c_oh, c_h} | {n for x in (c_oh, c_h) for n in g[x] if atoms[n] != "H"}
    for v in sorted(shell):
        system = rf.ring_system(v)
        if system is None:
            continue
        ring, monocyclic = system
        if not monocyclic:
            return False                               # (R) fused / bridged / spiro system at radius one
        if c_oh not in ring and c_h not in ring and _is_benzenoid(atoms, g, ring):
            continue                                   # (R) an untouched arene: a bystander, not a patient
        k = sum(1 for u in ring if u not in pi)
        if k <= (2 if len(ring) in (6, 7) else 1):
            return False                               # (R) too few saturated atoms: aromatisable / tautomer-prone
    for x in (c_oh, c_h):
        for n in g[x]:
            if n in (c_oh, c_h) or atoms[n] != "C" or n in excused:
                continue
            orders = list(g[n].values())
            if 3 in orders or orders.count(2) > 1:
                return False                           # (S) sp / cumulene carbon next door
    if not _radius_two_is_carbon(atoms, g, c_oh, c_h):
        return False                                   # (e')
    return True


#: The heteroatom signatures (sorted (element, bond order) pairs) of an acyl carbon on ``c_h`` whose O/N are excused:
#: carbonyl, carboxyl / ester, nitrile.  Anything else on that carbon and it excuses nothing.
_ACYL_SIGNATURES = ([("O", 2)], [("O", 1), ("O", 2)], [("N", 3)])


def _excused_acyl(atoms, g: Graph, c_oh: int, c_h: int) -> dict[int, set[int]]:
    """A(c_h) on the TARGET: each carbon neighbour of ``c_h`` (``c_oh`` excepted) whose non-C/H neighbours match one
    of :data:`_ACYL_SIGNATURES`, mapped to exactly those heteroatoms.  The union of the values is E, the only
    heteroatoms the class tolerates anywhere in the molecule ((M)) -- the whole guest list, checked at the door."""
    excusers: dict[int, set[int]] = {}
    for x in g[c_h]:
        if x == c_oh or atoms[x] != "C":
            continue
        hetero = {u: order for u, order in g[x].items() if atoms[u] not in ("C", "H")}
        orders = sorted((atoms[u], order) for u, order in hetero.items())
        if orders in _ACYL_SIGNATURES:
            excusers[x] = set(hetero)
    return excusers


def _is_benzenoid(atoms, g: Graph, ring: frozenset[int]) -> bool:
    """A benzenoid ring in the TARGET's Kekule graph: six atoms, all carbon, each with exactly one bond of order 2 and
    that bond to another atom of the same ring.  Every Kekule spelling of an isolated benzene ring satisfies it, so
    the witness's exact-Kekule habit does not bite here; fused arenes never reach it ((R) refuses polycycles first)."""
    if len(ring) != 6 or any(atoms[v] != "C" for v in ring):
        return False
    for v in ring:
        doubles = [u for u, order in g[v].items() if order == 2]
        if len(doubles) != 1 or doubles[0] not in ring:
            return False
    return True


def _radius_two_is_carbon(atoms, g: Graph, c_oh: int, c_h: int) -> bool:
    """(e') on the TARGET, by BFS distance from the alkene pair: every heavy atom at graph distance 1 or 2 from
    ``c_oh`` / ``c_h`` is carbon, except an O/N bonded to a carbonyl / carboxyl / ester / nitrile carbon that is itself
    bonded to ``c_h`` (the beta-hydroxy-carbonyl scope).  The hydroxyl to be added is not on the target, so it is
    excluded by construction."""
    dist = {c_oh: 0, c_h: 0}
    frontier = [c_oh, c_h]
    for depth in (1, 2):
        nxt = []
        for v in frontier:
            for u in g[v]:
                if atoms[u] != "H" and u not in dist:
                    dist[u] = depth
                    nxt.append(u)
        frontier = nxt
    excusers = _excused_acyl(atoms, g, c_oh, c_h)     # acyl carbon on c_h -> the O/N atoms it may excuse
    for v, d in dist.items():
        if d == 0 or atoms[v] == "C":
            continue
        if d == 1:
            return False                               # a heteroatom on the alkene carbons
        # d == 2: excused only if EVERY distance-1 parent it is reached through is an acyl carbon on c_h that excuses
        # it (parent-set form; production walks bond by bond instead)
        if not all(p in excusers and v in excusers[p] for p in g[v] if dist.get(p) == 1):
            return False
    return True


#: (g) closed-shell valences the witness accepts (bond-order sum per element); any other element is out of scope.
_CLOSED_SHELL_VALENCE = {"C": {4}, "H": {1}, "O": {2}, "N": {3, 5}, "S": {2, 4, 6}, "P": {3, 5},
                         "F": {1}, "Cl": {1}, "Br": {1}, "I": {1}}


def closed_shell_unlabelled(mol: Molecule) -> bool:
    """(g) neutral, stateless, every atom a plain (unlabelled) element at a closed-shell valence."""
    if mol.charge != 0 or mol.state:
        return False
    g = _graph(mol)
    for i, el in enumerate(mol.atoms):
        if el not in _CLOSED_SHELL_VALENCE or sum(g[i].values()) not in _CLOSED_SHELL_VALENCE[el]:
            return False                               # D / T / "13C" / a radical / an out-of-table element
    return True


def eligible_hydrations(mol: Molecule) -> tuple[tuple[int, int], ...]:
    """Every ``(c_oh, c_h)`` orientation of a target C=C that a safe-set 1,2-dehydration could have formed (OH placed on
    ``c_oh``), read off the target alone."""
    atoms = mol.atoms
    g = _graph(mol)
    pi = _pi_capable_atoms(atoms, g)
    bridges = _bridges_within(g, pi)
    rf = _RingFacts(atoms, g)
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
        for c_oh, c_h in ((a, b), (b, a)):
            if _orientation_is_safe(atoms, g, rf, pi, c_oh, c_h):
                out.append((c_oh, c_h))
    return tuple(out)


def eligible_alkene_sites(mol: Molecule) -> tuple[tuple[int, int], ...]:
    """The target's C=C bonds (``a < b``) with at least one eligible hydration orientation."""
    return tuple(sorted({tuple(sorted(pair)) for pair in eligible_hydrations(mol)}))


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
    closed_shell_unlabelled: bool = True
    note: str = ""


def witnesses_dehydration(precursor: Molecule, target: Molecule) -> DehydrationWitnessResult:
    """Is ``precursor -> target + H2O`` a 1,2-dehydration of an alcohol, judged by the independent route?"""
    stoich = _formula_gap_is_water(precursor, target)
    cp, ct = dehydration_census(precursor), dehydration_census(target)
    rank = cp.cycle_rank == ct.cycle_rank
    deltas = _census_deltas_match(cp, ct)
    shell = closed_shell_unlabelled(precursor) and closed_shell_unlabelled(target)
    recovers = False
    if stoich and shell:
        atoms_p, gp = list(precursor.atoms), _graph(precursor)
        for c_oh, c_h in eligible_hydrations(target):
            atoms_h, gh = _hydrated(target, c_oh, c_h)
            if _isomorphic(atoms_h, gh, atoms_p, gp):
                recovers = True
                break
    verdict = stoich and rank and deltas and recovers and shell
    failed = [name for name, ok in (("water_stoichiometry", stoich), ("cycle_rank_unchanged", rank),
                                    ("census_deltas_match", deltas),
                                    ("hydration_recovers_precursor", recovers),
                                    ("closed_shell_unlabelled", shell)) if not ok]
    return DehydrationWitnessResult(verdict, stoich, rank, deltas, recovers, shell,
                                    "" if verdict else "failed: " + ", ".join(failed))
