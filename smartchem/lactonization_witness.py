"""An INDEPENDENT structural witness for the 25th-class intramolecular lactonization (OPERATION XX, section 10).

STATUS: 1.6 CANDIDATE.  Standalone.  It is NOT registered into the reaction-type oracle, it moves no ``semantic_digest``,
and it touches no released-24-class semantics.  Nothing imports this module.

WHY THIS EXISTS.  The production recognizer (``smartchem.intramolecular_condensation``, held on the 1.6 line) and the
oracle's lactonization recognizer both route through ONE hand-written pair of group scanners
(``_ring_ester_sites`` for the target, ``_carboxyl_sites`` / ``_hydroxyl_sites`` for the precursor) and ONE verdict
(``_lactonizes_to``: apply the forward esterification as a graph op, compare by ``Molecule.canonical``).  A second
recognizer that re-ran that same detection would be COMMON-MODE: if the shared scanner were wrong, both "independent"
checks would be wrong together (the prior audit already caught exactly that failure).  This module therefore reaches
the lactonization verdict by DIFFERENT structural routes, so that it can genuinely DISAGREE with the recognizer.

THE INDEPENDENCE ROUTE (each step, and why it is not the production step):

  1. RING DETECTION BY BRIDGE-FINDING (``_bridges``).  A bond lies on a ring iff it is NOT a bridge of the bond graph.
     Bridges are found with an iterative Tarjan low-link DFS (discovery times and back-edge low-links).  Production
     tests "is this bond on a ring" by DELETING the bond and re-running a connectivity flood fill.  Different algorithm,
     different data structure; the two agree only if the chemistry of the input is what both think it is.
  2. THE ESTER MOTIF FROM FIRST PRINCIPLES (``lactone_motifs``).  A lactone is a carboxylic ester whose -C(=O)-O-
     linkage is closed into a ring.  The witness reads that off the graph as: a carbon with exactly three neighbours
     (one carbon-or-hydrogen substituent R, one =O, one -O-) whose -O- has exactly two neighbours, both carbon (so it
     is a C-O-C ether-type oxygen, not an -OH), the far carbon being NOT itself an acyl carbon (rules out an anhydride),
     and with the C-O bond on a ring (step 1), the ring recovered as an explicit shortest cycle by BFS (so the motif
     carries its ring size and members, and the =O is verified to be EXOCYCLIC).  Production decides the same facts by
     "the acyl carbon bears no heteroatom other than the linkage O" and "the alkoxy side is a lone carbon" -- an
     inverse bookkeeping (it excludes carbonate/carbamate by what the acyl carbon may NOT carry; the witness excludes
     them by what the carbon MUST be: exactly {R in C/H, =O, -O-}).
  3. A GROUP CENSUS ON BOTH SIDES (``group_census``) and a CYCLOMATIC-NUMBER delta.  Production never counts groups on
     the target and never uses the cycle rank.  The witness requires, between precursor P and target T:
        mu(T) = mu(P) + 1            (one new ring: the intramolecular signature; mu = bonds - atoms + 1)
        carboxylic acids:  T = P - 1,   alcohol/phenol -OH:  T = P - 1,   esters:  T = P + 1,   lactones:  T = P + 1.
     These are surgery-free invariants: they are computed on each molecule alone and merely differenced.
  4. STOICHIOMETRY (``_formula_gap_is_water``).  P.formula == T.formula + H2O, by plain dict addition, and equal charge.
     Production leans on the repo's ``Reaction``/``Config`` conservation machinery; the witness does the arithmetic
     on the ``formula`` dict itself.
  5. IDENTITY BY AN OWN-BUILT ISOMORPHISM TEST (``_isomorphic``).  For each lactone motif of T the witness adds the
     elements of water across the ring ester bond (the hydrolytic retro step) and asks whether the result is
     isomorphic to P.  The comparison is the witness's OWN colour-refinement + backtracking isomorphism over
     (element, bond-order) labels -- NOT ``Molecule.canonical`` / ``resonance_identity``, the identity subsystem the
     production verdict is a function of.  (The verdict is the conjunction 1-5; steps 3-4 corroborate step 5 and are
     reported individually in :class:`WitnessResult`.)

DOCUMENTED, DELIBERATE DIVERGENCES FROM PRODUCTION (so the witness can disagree, and where):
  * production refuses a hydroxyl whose carbinol carbon carries a second O/N (hemiacetal / gem-diol -- the dalembert
    XV-P8 kill).  The witness has no such guard: a lactone whose alkoxy carbon bears a second oxygen is still a cyclic
    ester structurally, so the witness says True where production says False.  That is a DISAGREEMENT worth a human
    look, not a bug to be silenced.
  * production declines a charged or stateful target; the witness only requires charge CONSERVATION.

RESIDUAL SHARED ASSUMPTIONS (honest, not zero): both routes read the SAME ``Molecule`` graph model (explicit-hydrogen
Kekule bond orders, undirected ``Bond(i, j, order)``), both embody the SAME chemical definition of "lactone"
(cyclic carboxylic ester) and of "lactonization" (hydroxy acid -> lactone + H2O), and both inherit whatever the
SMILES parser did to the input.  Independence is in the DETECTION ROUTE and the arithmetic/isomorphism checks, not in
premises.  Like the production edge, a True verdict means "structurally a valid intramolecular lactonization" and
NEVER that the reaction is feasible, favourable or kinetically accessible.

This module imports ONLY ``Molecule`` (for typing) from ``smartchem.category``; it imports nothing from
``smartchem.intramolecular_condensation`` or the reaction-type oracle.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass

from .category import Molecule

_WATER_FORMULA = {"H": 2, "O": 1}

Adj = dict[int, dict[int, int]]            # atom -> {neighbour: bond order}


# --------------------------------------------------------------------------------------------------------------------
# Raw graph helpers (the witness's own representation: dict-of-dicts, never the production adjacency idiom).
# --------------------------------------------------------------------------------------------------------------------

def _graph(mol: Molecule) -> Adj:
    adj: Adj = {i: {} for i in range(len(mol.atoms))}
    for b in mol.bonds:
        adj[b.i][b.j] = b.order
        adj[b.j][b.i] = b.order
    return adj


def _bridges(adj: Adj) -> set[frozenset[int]]:
    """Every bridge of the (connected) bond graph, by an iterative Tarjan low-link DFS.  A bond is on a ring iff it is
    absent from this set."""
    disc: dict[int, int] = {}
    low: dict[int, int] = {}
    bridges: set[frozenset[int]] = set()
    clock = 0
    for root in adj:
        if root in disc:
            continue
        disc[root] = low[root] = clock
        clock += 1
        stack = [(root, -1, iter(adj[root]))]
        while stack:
            node, parent, it = stack[-1]
            advanced = False
            for nxt in it:
                if nxt == parent:
                    continue
                if nxt in disc:                      # back-edge
                    low[node] = min(low[node], disc[nxt])
                else:                                # tree edge
                    disc[nxt] = low[nxt] = clock
                    clock += 1
                    stack.append((nxt, node, iter(adj[nxt])))
                    advanced = True
                    break
            if advanced:
                continue
            stack.pop()
            if stack:
                up = stack[-1][0]
                low[up] = min(low[up], low[node])
                if low[node] > disc[up]:
                    bridges.add(frozenset((up, node)))
    return bridges


def _ring_through(adj: Adj, a: int, b: int) -> list[int] | None:
    """The smallest ring containing the bond ``a--b`` as an explicit atom list (BFS from ``a`` to ``b`` that may not use
    that bond), or ``None`` when the bond is on no ring."""
    prev: dict[int, int] = {a: -1}
    queue = deque([a])
    while queue:
        cur = queue.popleft()
        for nxt in adj[cur]:
            if {cur, nxt} == {a, b}:
                continue
            if nxt in prev:
                continue
            prev[nxt] = cur
            if nxt == b:
                path = [b]
                while path[-1] != a:
                    path.append(prev[path[-1]])
                return path[::-1]
            queue.append(nxt)
    return None


# --------------------------------------------------------------------------------------------------------------------
# The ester / lactone motif, read off the graph from first principles.
# --------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class EsterMotif:
    """One carboxylic-ester linkage ``R-C(=O)-O-C'``: ``c`` acyl carbon, ``o_exo`` its =O, ``o_link`` the ester oxygen,
    ``c_alk`` the alkoxy-side carbon, ``ring`` the smallest ring through ``c--o_link`` (empty when acyclic)."""
    c: int
    o_exo: int
    o_link: int
    c_alk: int
    ring: tuple[int, ...]

    @property
    def is_lactone(self) -> bool:
        return len(self.ring) >= 3 and self.o_exo not in self.ring


def _is_acyl(adj: Adj, atoms: tuple[str, ...], c: int) -> bool:
    return atoms[c] == "C" and any(o == 2 and atoms[n] == "O" for n, o in adj[c].items())


def ester_motifs(mol: Molecule) -> tuple[EsterMotif, ...]:
    """Every carboxylic-ester linkage in ``mol`` (ring or not), each annotated with its smallest ring."""
    atoms = mol.atoms
    adj = _graph(mol)
    bridges = _bridges(adj)
    out: list[EsterMotif] = []
    for c in range(len(atoms)):
        if atoms[c] != "C" or len(adj[c]) != 3:
            continue
        doubles = [n for n, o in adj[c].items() if o == 2 and atoms[n] == "O"]
        if len(doubles) != 1:
            continue
        singles = [n for n, o in adj[c].items() if o == 1]
        if len(singles) != 2:
            continue
        o_exo = doubles[0]
        # the single-bonded neighbours are {R, -O-}: R must be carbon or hydrogen, -O- an oxygen.
        for o_link, r in (singles, singles[::-1]):
            if atoms[o_link] != "O" or atoms[r] not in ("C", "H"):
                continue
            if len(adj[o_link]) != 2 or any(o != 1 for o in adj[o_link].values()):
                continue                              # not a C-O-C: an -OH (or odd valence) is no ester linkage
            c_alk = next(x for x in adj[o_link] if x != c)
            if atoms[c_alk] != "C" or _is_acyl(adj, atoms, c_alk):
                continue                              # an alkoxy side that is itself acyl is an ANHYDRIDE, not an ester
            ring: list[int] = []
            if frozenset((c, o_link)) not in bridges:
                ring = _ring_through(adj, c, o_link) or []
            out.append(EsterMotif(c, o_exo, o_link, c_alk, tuple(ring)))
    return tuple(out)


def lactone_motifs(mol: Molecule) -> tuple[EsterMotif, ...]:
    """The ester linkages of ``mol`` that sit on a ring (the lactone linkages), with the =O verified exocyclic."""
    return tuple(m for m in ester_motifs(mol) if m.is_lactone)


def is_lactone_structure(mol: Molecule) -> bool:
    """Is ``mol`` a lactone, i.e. does it contain a cyclic carboxylic ester?  Decided WITHOUT any reference to a
    precursor and without the production ring-ester scanner."""
    return bool(lactone_motifs(mol))


# --------------------------------------------------------------------------------------------------------------------
# Surgery-free group census and cycle rank.
# --------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class GroupCensus:
    """Counts computed on ONE molecule alone."""
    cycle_rank: int          # mu = bonds - atoms + 1  (the number of independent rings)
    carboxylic_acids: int    # R-C(=O)-OH
    alcohol_hydroxyls: int   # C-OH where that carbon is not an acyl carbon (alcohol / phenol / enol)
    esters: int              # R-C(=O)-O-C', ring or not
    lactones: int            # ring esters


def group_census(mol: Molecule) -> GroupCensus:
    atoms = mol.atoms
    adj = _graph(mol)
    acids = alcohols = 0
    for o in range(len(atoms)):
        if atoms[o] != "O" or len(adj[o]) != 2:
            continue
        hs = [n for n in adj[o] if atoms[n] == "H"]
        heavy = [n for n in adj[o] if atoms[n] != "H"]
        if len(hs) != 1 or len(heavy) != 1 or atoms[heavy[0]] != "C" or adj[o][heavy[0]] != 1:
            continue
        c = heavy[0]
        if _is_acyl(adj, atoms, c):
            others = [n for n, od in adj[c].items() if n != o and not (od == 2 and atoms[n] == "O")]
            if len(adj[c]) == 3 and len(others) == 1 and atoms[others[0]] in ("C", "H"):
                acids += 1                            # a genuine carboxylic acid (R is C/H; no carbonate/carbamate)
        else:
            alcohols += 1
    motifs = ester_motifs(mol)
    return GroupCensus(
        cycle_rank=len(mol.bonds) - len(atoms) + 1,
        carboxylic_acids=acids,
        alcohol_hydroxyls=alcohols,
        esters=len(motifs),
        lactones=sum(1 for m in motifs if m.is_lactone),
    )


# --------------------------------------------------------------------------------------------------------------------
# Stoichiometry, on the formula dict itself.
# --------------------------------------------------------------------------------------------------------------------

def _formula_gap_is_water(precursor: Molecule, target: Molecule) -> bool:
    """``precursor.formula == target.formula + H2O`` by element-wise dict addition (zero counts ignored), and the
    charge is conserved."""
    total = Counter({k: v for k, v in target.formula.items() if v})
    for el, n in _WATER_FORMULA.items():
        total[el] += n
    have = Counter({k: v for k, v in precursor.formula.items() if v})
    return total == have and precursor.charge == target.charge


# --------------------------------------------------------------------------------------------------------------------
# The witness's own isomorphism test (labelled by element and bond order).
# --------------------------------------------------------------------------------------------------------------------

def _isomorphic(atoms_a: list[str], adj_a: Adj, atoms_b: list[str], adj_b: Adj) -> bool:
    """Exact isomorphism of two (element, bond-order)-labelled graphs: joint colour refinement to prune, then
    backtracking to confirm an actual atom bijection (so a refinement collision cannot yield a false True)."""
    if len(atoms_a) != len(atoms_b) or Counter(atoms_a) != Counter(atoms_b):
        return False
    na = len(atoms_a)
    if sum(len(v) for v in adj_a.values()) != sum(len(v) for v in adj_b.values()):
        return False
    # joint refinement over the disjoint union (nodes 0..na-1 are A, na.. are B)
    colour = {}
    for i, el in enumerate(atoms_a):
        colour[i] = el
    for j, el in enumerate(atoms_b):
        colour[na + j] = el
    nbrs = {i: [(n, o) for n, o in adj_a[i].items()] for i in range(na)}
    nbrs.update({na + j: [(na + n, o) for n, o in adj_b[j].items()] for j in range(len(atoms_b))})
    for _ in range(na + 1):
        sig = {v: (colour[v], tuple(sorted((o, colour[n]) for n, o in nbrs[v]))) for v in nbrs}
        table: dict = {}
        new = {v: table.setdefault(sig[v], len(table)) for v in sorted(nbrs)}
        stable = len(set(new.values())) == len(set(colour.values()))
        colour = new
        if stable:
            break
    a_cols = Counter(colour[i] for i in range(na))
    b_cols = Counter(colour[na + j] for j in range(len(atoms_b)))
    if a_cols != b_cols:
        return False
    mapping: dict[int, int] = {}
    inverse: dict[int, int] = {}
    order = sorted(range(na), key=lambda i: (a_cols[colour[i]], i))     # rarest colour classes first

    def extend(k: int) -> bool:
        if k == na:
            return True
        i = order[k]
        for j in range(len(atoms_b)):
            if j in inverse or colour[na + j] != colour[i]:
                continue
            ok = True
            for n, o in adj_a[i].items():                                # A-side edges to mapped atoms must exist in B
                if n in mapping and adj_b[j].get(mapping[n]) != o:
                    ok = False
                    break
            if ok:
                for m, o in adj_b[j].items():                            # ...and B-side edges to used atoms in A
                    if m in inverse and adj_a[i].get(inverse[m]) != o:
                        ok = False
                        break
            if not ok:
                continue
            mapping[i] = j
            inverse[j] = i
            if extend(k + 1):
                return True
            del mapping[i]
            del inverse[j]
        return False

    return extend(0)


def _hydrolyse(mol: Molecule, m: EsterMotif) -> tuple[list[str], Adj]:
    """Add the elements of water across ``m``'s ring ester bond: break ``c--o_link``; ``c`` gains -OH, ``o_link`` gains -H.
    Returns raw (atoms, adjacency) -- never a ``Molecule`` -- so no production constructor/identity path is involved."""
    atoms = list(mol.atoms)
    adj = {i: dict(v) for i, v in _graph(mol).items()}
    del adj[m.c][m.o_link]
    del adj[m.o_link][m.c]
    o_new, h_acid, h_alk = len(atoms), len(atoms) + 1, len(atoms) + 2
    atoms += ["O", "H", "H"]
    adj[o_new] = {m.c: 1, h_acid: 1}
    adj[h_acid] = {o_new: 1}
    adj[h_alk] = {m.o_link: 1}
    adj[m.c][o_new] = 1
    adj[m.o_link][h_alk] = 1
    return atoms, adj


# --------------------------------------------------------------------------------------------------------------------
# The verdict.
# --------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class WitnessResult:
    """The witness's verdict, with every individual check exposed (so a disagreement can be diagnosed, and so the
    surgery-free corroborating checks are visible apart from the identity check)."""
    is_lactonization: bool
    target_is_lactone: bool
    water_stoichiometry: bool
    ring_count_plus_one: bool
    group_deltas_match: bool
    hydrolysis_recovers_precursor: bool
    note: str = ""


def witnesses_lactonization(precursor: Molecule, target: Molecule) -> WitnessResult:
    """Does ``precursor -> target + H2O`` look like an intramolecular lactonization, judged by the independent route?

    True iff ALL of: the target contains a cyclic carboxylic ester; ``precursor.formula == target.formula + H2O``
    (charge conserved); the cycle rank rises by exactly one; the acid / alcohol-OH / ester / lactone census moves by
    exactly (-1, -1, +1, +1); and adding water across some lactone linkage of the target gives a graph isomorphic to
    the precursor (own isomorphism test)."""
    stoich = _formula_gap_is_water(precursor, target)
    t_motifs = lactone_motifs(target)
    t_lactone = bool(t_motifs)
    cp, ct = group_census(precursor), group_census(target)
    ring_up = ct.cycle_rank == cp.cycle_rank + 1
    deltas = (ct.carboxylic_acids == cp.carboxylic_acids - 1
              and ct.alcohol_hydroxyls == cp.alcohol_hydroxyls - 1
              and ct.esters == cp.esters + 1
              and ct.lactones == cp.lactones + 1)
    recovers = False
    if stoich and t_lactone:
        atoms_p, adj_p = list(precursor.atoms), _graph(precursor)
        for m in t_motifs:
            atoms_h, adj_h = _hydrolyse(target, m)
            if _isomorphic(atoms_h, adj_h, atoms_p, adj_p):
                recovers = True
                break
    verdict = t_lactone and stoich and ring_up and deltas and recovers
    failed = [name for name, ok in (("target_is_lactone", t_lactone), ("water_stoichiometry", stoich),
                                    ("ring_count_plus_one", ring_up), ("group_deltas_match", deltas),
                                    ("hydrolysis_recovers_precursor", recovers)) if not ok]
    return WitnessResult(verdict, t_lactone, stoich, ring_up, deltas, recovers,
                         "" if verdict else "failed: " + ", ".join(failed))
