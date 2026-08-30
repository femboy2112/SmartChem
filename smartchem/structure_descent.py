"""M-4 v2 (rung 2) -- structure-aware descent: decomposition as *bond-graph surgery*.

Where v1 (:mod:`smartchem.decompiler`) splits a bond-free atom multiset, this module splits a
real :class:`~smartchem.category.Molecule`: it **cuts a set of bonds** and reads off the connected
components that fall out.  Two things the formula-level engine cannot represent become facts here:

* **The fragments are specific sub-structures, not just compositions.**  Cutting paracetamol's
  amide C-N bond yields a *4-aminophenyl-amino radical* and an *acetyl radical* -- particular
  graphs with particular open valences -- where the formula engine sees only ``C6H6NO + C2H3O``.
* **Which cleavages even exist is decided by the structure.**  Paracetamol has an amide bond and a
  phenol C-O bond; it has *no* ester linkage, so an ester cleavage is not merely disfavoured, it is
  **structurally unavailable**.  Its O-acetyl isomer (4-aminophenyl acetate) has the opposite menu.
  N- versus O-acetylation, gap #3 of the litmus and invisible to v1, is now a graph fact.

The one law (W3, unchanged)
---------------------------
A scission certifies **graph surgery** -- that removing these bonds partitions the molecule into
exactly these connected fragments, conserving every atom and every unit of valence -- and *nothing*
about whether that bond breaks, under what conditions, or at what rate.  A ``ScissionEdge`` is an
exact combinatorial object over the bond graph, the structure-level analogue of v1's exact integer
conservation.  It is not a prediction that a molecule decomposes this way.

The soundness bridge (why this is a *refinement*, not a parallel invention)
---------------------------------------------------------------------------
Every scission has a forgetful image :meth:`ScissionEdge.forget`, the v1
:class:`~smartchem.decompiler.DecompositionEdge` you get by dropping the bonds and keeping the
fragment compositions.  It is always a *valid* v1 edge (atoms conserved, every fragment strictly
lower rank, at least two products), so the structure-level descent projects onto the formula-level
one.  That map is the whole reason this is the same feature at finer resolution rather than a second,
possibly-inconsistent engine -- and ``tests/test_structure_descent.py`` holds the commuting square
down.

The walls (same three as v1, restated for graphs)
-------------------------------------------------
* **W1 Termination.**  A cut that disconnects yields components each with *strictly fewer atoms*
  than the parent, so the descent measure (atom count) drops -- exactly v1's rank guard, now forced
  by the partition rather than checked.  A cut that does *not* disconnect (a single ring bond) is no
  decomposition at all and is never emitted.
* **W2 Budget.**  The cut-set powerset explodes, so enumeration is bounded by ``max_cut_bonds`` (a
  stated completeness boundary) -- single-bond cleavages by default, multi-bond ring-opening opt-in.
* **W3 Formal != physical.**  The law above.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from .category import Bond, Molecule
from .contracts import Digestible, canonical_digest
from .decompiler import DecompositionEdge, Formula

__all__ = [
    "STRUCTURE_DESCENT_SCHEMA",
    "ScissionError",
    "Fragment",
    "ScissionEdge",
    "scission_edges",
    "verify_valence_integrity",
]

STRUCTURE_DESCENT_SCHEMA = "smartchem.structure_descent/scission-v2"


def _fkey(formula: Formula) -> tuple:
    """The formula sort key v1 edges use -- (composition, charge) -- kept local to avoid coupling."""
    return (formula.counts, formula.charge)


class ScissionError(ValueError):
    """A proposed bond-cut is not an admissible structure-level decomposition."""


def _components(n: int, bonds: frozenset[Bond]) -> list[tuple[int, ...]]:
    """Connected components of the graph on ``0..n-1`` with edge set ``bonds`` (order ignored).

    Returned as a list of sorted index tuples, the components themselves ordered by their first
    (smallest) member, so the decomposition of a fixed graph is deterministic.
    """
    adj: dict[int, set[int]] = {i: set() for i in range(n)}
    for b in bonds:
        adj[b.i].add(b.j)
        adj[b.j].add(b.i)
    seen: set[int] = set()
    out: list[tuple[int, ...]] = []
    for start in range(n):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        block: list[int] = []
        while stack:
            cur = stack.pop()
            block.append(cur)
            for nxt in adj[cur] - seen:
                seen.add(nxt)
                stack.append(nxt)
        out.append(tuple(sorted(block)))
    return sorted(out, key=lambda c: c[0])


def _fragment_of(
    reactant: Molecule, origin: tuple[int, ...], cut: frozenset[Bond]
) -> "Fragment":
    """Build the fragment carried by the atoms ``origin`` after removing ``cut`` from ``reactant``.

    Internal bonds are the surviving (non-cut) reactant bonds with both endpoints in ``origin``,
    re-indexed to the fragment's own ``0..k-1``.  Open valences are the cut-bond ends that land on
    an atom of ``origin`` -- one entry per incident cut-bond end, so an intra-component cut (a ring
    bond cut without the ring disconnecting) contributes *two* entries to the one fragment.
    """
    local = {r: k for k, r in enumerate(origin)}
    atoms = tuple(reactant.atoms[r] for r in origin)
    internal: set[Bond] = set()
    for b in reactant.bonds:
        if b in cut:
            continue
        if b.i in local and b.j in local:
            internal.add(Bond(local[b.i], local[b.j], b.order))
    open_valences: list[tuple[int, int]] = []
    for b in cut:
        for endpoint in (b.i, b.j):
            if endpoint in local:
                open_valences.append((local[endpoint], b.order))
    return Fragment(
        molecule=Molecule(atoms, frozenset(internal), 0, reactant.state),
        origin=origin,
        open_valences=tuple(sorted(open_valences)),
    )


@dataclass(frozen=True)
class Fragment(Digestible):
    """One connected piece of a scissioned molecule, with the valences the cut left open.

    ``molecule`` is the re-indexed connected sub-graph -- a valence-*deficient* species (a radical
    relative to a closed molecule).  That deficiency is recorded in ``open_valences``, never hidden:
    a fragment is not a stable compound, and pretending it were would be the exact structural lie
    this package refuses.

    ``origin`` maps each fragment-local atom back to its position in the parent molecule (so the
    parent's degree can be recovered atom-by-atom); ``open_valences`` is the sorted multiset of
    ``(local_atom_index, opened_bond_order)`` pairs, one per cut-bond end incident to this fragment.
    """

    molecule: Molecule
    origin: tuple[int, ...]
    open_valences: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if type(self.molecule) is not Molecule:
            raise ScissionError("fragment molecule must be a smartchem.category.Molecule")
        if type(self.origin) is not tuple or any(type(r) is not int for r in self.origin):
            raise ScissionError("origin must be a tuple of parent atom indices")
        if len(self.origin) != len(self.molecule.atoms):
            raise ScissionError("origin must have one parent index per fragment atom")
        if len(set(self.origin)) != len(self.origin):
            raise ScissionError("origin indices must be distinct")
        k = len(self.molecule.atoms)
        for idx, order in self.open_valences:
            if type(idx) is not int or not (0 <= idx < k):
                raise ScissionError(f"open-valence atom index {idx} out of range")
            if type(order) is not int or order < 1:
                raise ScissionError("open-valence order must be a positive int")
        if list(self.open_valences) != sorted(self.open_valences):
            raise ScissionError("open_valences must be sorted")

    @property
    def formula(self) -> Formula:
        """The forgetful fragment->composition map (bond-free, radical composition and all)."""
        return Formula.of(self.molecule.formula, self.molecule.charge)

    @property
    def open_valence_total(self) -> int:
        """Total opened bond order across this fragment -- how many half-bonds the cut left dangling."""
        return sum(order for _, order in self.open_valences)

    def open_valence_at(self, local_index: int) -> int:
        return sum(order for idx, order in self.open_valences if idx == local_index)

    @property
    def canonical_identity(self) -> str:
        """A presentation-invariant identity of the fragment as a *graph* (ignoring open valences).

        Uses the 1-WL canonical form where it succeeds, an ``asgiven:`` digest otherwise -- the same
        honest fallback as :mod:`smartchem.structure`.
        """
        try:
            return canonical_digest(self.molecule.canonical())
        except NotImplementedError:
            return "asgiven:" + canonical_digest(self.molecule)


@dataclass(frozen=True)
class ScissionEdge(Digestible):
    """One admissible structure-level decomposition: cut ``cut_bonds`` from ``reactant`` -> ``fragments``.

    The constructor is the certificate.  Every invariant is re-derived from the stored fields alone
    (never trusted from the factory), so a hand-built edge that lies about its fragments fails here:

    * **the cut is real** -- ``cut_bonds`` are distinct bonds of ``reactant``;
    * **partition** -- the fragment ``origin`` sets tile ``reactant``'s atoms exactly (disjoint,
      covering), and every non-cut reactant bond is internal to exactly one fragment;
    * **fidelity** -- each fragment's atom labels and internal bonds are exactly the surviving
      reactant sub-graph on its atoms (no fabricated atom, no invented bond);
    * **valence conservation** -- for every atom, ``used valence in fragment + open valence ==
      its degree in the parent``, and the total open valence is ``2 * sum(cut bond orders)``;
    * **W1 descent** -- at least two fragments, each with strictly fewer atoms than the parent.
    """

    schema_version: str
    reactant: Molecule
    cut_bonds: tuple[Bond, ...]
    fragments: tuple[Fragment, ...]

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURE_DESCENT_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {STRUCTURE_DESCENT_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a smartchem.category.Molecule")
        n = len(self.reactant.atoms)
        if n < 2:
            raise ScissionError("a scission needs a molecule of at least two atoms")
        # -- the cut is a set of real reactant bonds ------------------------------------------
        if type(self.cut_bonds) is not tuple or not self.cut_bonds:
            raise ScissionError("cut_bonds must be a non-empty tuple of Bond values")
        if len(set(self.cut_bonds)) != len(self.cut_bonds):
            raise ScissionError("cut_bonds must be distinct")
        if list(self.cut_bonds) != sorted(self.cut_bonds):
            raise ScissionError("cut_bonds must be sorted")
        cut = frozenset(self.cut_bonds)
        if not cut <= self.reactant.bonds:
            raise ScissionError("every cut bond must be a bond of the reactant")
        # -- at least two fragments, each a strict sub-molecule (W1) --------------------------
        if type(self.fragments) is not tuple or len(self.fragments) < 2:
            raise ScissionError(
                "a scission must yield at least two fragments; a single-component cut (e.g. one "
                "ring bond) is not a decomposition"
            )
        if any(type(f) is not Fragment for f in self.fragments):
            raise ScissionError("fragments must be Fragment values")
        if any(len(f.origin) >= n for f in self.fragments):
            raise ScissionError("every fragment must have strictly fewer atoms than the parent (W1)")
        # -- the origins tile the parent's atoms exactly --------------------------------------
        covered = [r for f in self.fragments for r in f.origin]
        if sorted(covered) != list(range(n)):
            raise ScissionError(
                "fragment origins must partition the parent's atoms exactly (disjoint and covering)"
            )
        # -- each fragment is faithfully the surviving sub-graph on its atoms -----------------
        internal_total = 0
        for f in self.fragments:
            expected = _fragment_of(self.reactant, f.origin, cut)
            if expected.molecule.atoms != f.molecule.atoms:
                raise ScissionError("a fragment's atom labels do not match the parent sub-graph")
            if expected.molecule.bonds != f.molecule.bonds:
                raise ScissionError("a fragment's internal bonds are not the surviving parent bonds")
            if expected.open_valences != f.open_valences:
                raise ScissionError("a fragment's open valences do not match the incident cut bonds")
            internal_total += len(f.molecule.bonds)
        # -- every non-cut reactant bond is accounted for as exactly one internal bond --------
        if internal_total + len(cut) != len(self.reactant.bonds):
            raise ScissionError(
                "bond bookkeeping failed: internal fragment bonds + cut bonds != parent bonds"
            )
        # -- valence conservation: nothing created or destroyed by the cut --------------------
        opened = sum(f.open_valence_total for f in self.fragments)
        if opened != 2 * sum(b.order for b in self.cut_bonds):
            raise ScissionError(
                "open-valence total must equal twice the cut bond order (each cut opens two ends)"
            )
        for f in self.fragments:
            for k, r in enumerate(f.origin):
                used = f.molecule.degree(k)
                if used + f.open_valence_at(k) != self.reactant.degree(r):
                    raise ScissionError(
                        f"valence not conserved at parent atom {r}: fragment used {used} + open "
                        f"{f.open_valence_at(k)} != parent degree {self.reactant.degree(r)}"
                    )
        # -- atom conservation, as a cheap independent cross-check ----------------------------
        parent_comp = Counter(self.reactant.atoms)
        frag_comp: Counter = Counter()
        for f in self.fragments:
            frag_comp.update(f.molecule.atoms)
        if parent_comp != frag_comp:
            raise ScissionError("fragment atoms do not sum to the parent composition")

    # -- reads -------------------------------------------------------------------------------
    @property
    def reactant_formula(self) -> Formula:
        return Formula.of(self.reactant.formula, self.reactant.charge)

    @property
    def disconnects(self) -> bool:
        """Whether the cut genuinely disconnected the molecule (always True for a built edge)."""
        return len(self.fragments) >= 2

    @property
    def signature(self) -> tuple:
        """A presentation-invariant identity of this scission.

        Two cuts that produce the same multiset of fragment *graphs* with the same opened valences
        (however the parent happened to be indexed) share a signature -- the dedup key of
        :func:`scission_edges` and the invariant the relabelling tests pin down.  It is coarse in one
        stated way: it pairs each fragment's canonical *graph* identity with its multiset of opened
        orders, so it does not distinguish which symmetry-equivalent atom carried an open valence --
        which is correct, because those are the same fragment.
        """
        frag_sigs = sorted(
            (f.canonical_identity, tuple(sorted(o for _, o in f.open_valences)))
            for f in self.fragments
        )
        return (
            tuple(sorted(f"{s}{c if c > 1 else ''}" for s, c in
                         Counter(self.reactant.atoms).items())),
            tuple(sorted(b.order for b in self.cut_bonds)),
            tuple(frag_sigs),
        )

    def forget(self) -> DecompositionEdge:
        """The forgetful image in v1: the formula-level :class:`DecompositionEdge` of the fragments.

        Compositions only -- the radical fragments become bare formulas, single-element fragments
        collapse to unit element buckets carrying their count as multiplicity (v1's canonical bucket
        spelling).  The result is always a valid v1 edge: atoms conserved, every product strictly
        lower rank, at least two products.  This is the commuting map that makes the structure-level
        descent a refinement of the formula-level one.
        """
        merged: dict[Formula, int] = {}
        for f in self.fragments:
            comp = f.formula
            if comp.is_element:
                (symbol, count), = comp.counts
                bucket = Formula.bucket(symbol)
                merged[bucket] = merged.get(bucket, 0) + count
            else:
                merged[comp] = merged.get(comp, 0) + 1
        products = tuple(sorted(merged.items(), key=lambda pm: (_fkey(pm[0]), pm[1])))
        return DecompositionEdge(self.reactant_formula, 1, products)

    def equation(self) -> str:
        """A human-readable scission equation over fragment formulas, marking dangling valences."""
        def term(f: Fragment) -> str:
            body = repr(f.formula)
            dangles = f.open_valence_total
            return f"[{body}]*{dangles}" if dangles else body
        rhs = " + ".join(term(f) for f in self.fragments)
        cut = ", ".join(f"{b.i}-{b.j}" + (f"({b.order})" if b.order > 1 else "") for b in self.cut_bonds)
        return f"{self.reactant!r} --cut[{cut}]--> {rhs}"

    def __repr__(self) -> str:
        return f"ScissionEdge({self.equation()})"


def verify_valence_integrity(reactant: Molecule, cut_bonds: tuple[Bond, ...]) -> bool:
    """Independently recompute whether cutting ``cut_bonds`` conserves valence atom-by-atom.

    Recomputes the fragmentation from ``reactant`` + ``cut_bonds`` directly -- a second path to the
    same fact the :class:`ScissionEdge` constructor enforces, so a test can check the certificate
    without going through the object it certifies (the repo's "no check derived from its own subject"
    discipline).  Returns ``True`` iff every atom's parent degree equals its surviving valence plus
    its opened valence.
    """
    cut = frozenset(cut_bonds)
    if not cut <= reactant.bonds:
        return False
    n = len(reactant.atoms)
    for origin in _components(n, reactant.bonds - cut):
        frag = _fragment_of(reactant, origin, cut)
        for k, r in enumerate(origin):
            if frag.molecule.degree(k) + frag.open_valence_at(k) != reactant.degree(r):
                return False
    return True


def scission_edges(
    molecule: Molecule, *, max_cut_bonds: int = 1, budget: int = 100_000
) -> tuple[tuple[ScissionEdge, ...], bool]:
    """Every admissible scission of ``molecule`` cutting up to ``max_cut_bonds`` bonds.

    A cut set is admissible iff removing it disconnects the molecule into at least two components
    (a cut that leaves the graph connected -- e.g. a single ring bond -- is no decomposition and is
    skipped).  Edges are deduplicated by :attr:`ScissionEdge.signature`, so two index-different cuts
    that yield the same fragmentation appear once.  Returns ``(edges, complete)``; ``complete`` is
    ``False`` iff the enumeration hit ``budget`` (a partial result, never silently a full one -- W2).

    ``max_cut_bonds`` is the completeness boundary: ``1`` (the default) enumerates every single-bond
    cleavage (all the non-ring bonds); ``2`` and above reach ring-opening and multi-site cleavages
    and multiply the search.
    """
    if type(molecule) is not Molecule:
        raise TypeError("molecule must be a smartchem.category.Molecule")
    n = len(molecule.atoms)
    if n < 2 or not molecule.bonds:
        return (), True
    bonds = sorted(molecule.bonds)
    edges: dict[tuple, ScissionEdge] = {}
    work = 0
    for size in range(1, max_cut_bonds + 1):
        for combo in combinations(bonds, size):
            work += 1
            if work > budget:
                return tuple(edges.values()), False
            cut = frozenset(combo)
            comps = _components(n, molecule.bonds - cut)
            if len(comps) < 2:
                continue  # cut did not disconnect: not a decomposition
            fragments = tuple(_fragment_of(molecule, origin, cut) for origin in comps)
            edge = ScissionEdge(STRUCTURE_DESCENT_SCHEMA, molecule, tuple(sorted(combo)), fragments)
            edges.setdefault(edge.signature, edge)
    ordered = tuple(sorted(edges.values(), key=lambda e: e.digest))
    return ordered, True
