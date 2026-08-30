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
from itertools import combinations, combinations_with_replacement, product

from .category import Bond, Molecule
from .contracts import Digestible, canonical_digest
from .decompiler import DecompositionEdge, Formula
from .decompiler_mediated import MediatedEdge

__all__ = [
    "STRUCTURE_DESCENT_SCHEMA",
    "CAPPED_SCISSION_SCHEMA",
    "STRUCTURE_GRAPH_SCHEMA",
    "HETEROLYTIC_SCHEMA",
    "REDOX_SCHEMA",
    "IONIC_EDGES_SCHEMA",
    "ELECTRON",
    "ScissionError",
    "Fragment",
    "ScissionEdge",
    "CappedScission",
    "HeterolyticScission",
    "RedoxHalfReaction",
    "IonicEdges",
    "StructureDecompositionGraph",
    "scission_edges",
    "capped_scissions",
    "heterolytic_scissions",
    "redox_couples",
    "ionic_edges",
    "structure_decompose",
    "verify_valence_integrity",
]

STRUCTURE_DESCENT_SCHEMA = "smartchem.structure_descent/scission-v2"
CAPPED_SCISSION_SCHEMA = "smartchem.structure_descent/capped-scission-v2"
STRUCTURE_GRAPH_SCHEMA = "smartchem.structure_descent/structure-graph-v2"
HETEROLYTIC_SCHEMA = "smartchem.structure_descent/heterolytic-v2"
REDOX_SCHEMA = "smartchem.structure_descent/redox-v1"
IONIC_EDGES_SCHEMA = "smartchem.structure_descent/ionic-edges-v1"

#: The electron, spelled the repository's way -- a charge carrier with NO atoms, so it is massless in
#: the mass ledger (it never enters ``formula``) while carrying charge -1. This is the idiom
#: ``category.Molecule.carrier`` exists for (see its docstring and ``cell.py``); an electron is not
#: ``Molecule.atom("e")``, which would make charge into matter.
ELECTRON = Molecule.carrier("e-", charge=-1)


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


# ======================================================================================
# Rung 2b -- capped scission: a valence-preserving bond rewrite (derived mediated reactions)
# ======================================================================================
def _join(reactant: Molecule, reagents: tuple[Molecule, ...]) -> tuple[tuple[str, ...], frozenset[Bond], list[int]]:
    """Lay reactant and reagents into one combined index space.

    Returns ``(atoms, bonds, offsets)`` where ``offsets[k]`` is the starting index of the k-th
    molecule (reactant is molecule 0).  Deterministic, so the combined graph a :class:`CappedScission`
    verifies against is recovered from its stored molecules alone.
    """
    atoms: list[str] = list(reactant.atoms)
    bonds: set[Bond] = set(reactant.bonds)
    offsets = [0]
    for reagent in reagents:
        off = len(atoms)
        offsets.append(off)
        atoms.extend(reagent.atoms)
        for b in reagent.bonds:
            bonds.add(Bond(b.i + off, b.j + off, b.order))
    return tuple(atoms), frozenset(bonds), offsets


def _degree(bonds: frozenset[Bond], index: int) -> int:
    return sum(b.order for b in bonds if index in (b.i, b.j))


def _perfect_matchings(n: int):
    """Yield every way to pair up ``0..n-1`` (n even), each as a list of ``(i, j)`` index pairs.

    ``(n-1)!!`` matchings -- the general enumeration a capper needs: pairing the *open ends* freely
    (not a reactant-to-reagent bijection) is exactly what admits a reactant-end-to-reactant-end cap,
    i.e. a ring-forming rewrite. The caller filters each pairing by equal-order and by the
    :class:`CappedScission` certificate, and bounds the count with a budget.
    """
    if n % 2 != 0:
        return
    order = list(range(n))

    def rec(remaining: list[int]):
        if not remaining:
            yield []
            return
        first, rest = remaining[0], remaining[1:]
        for k in range(len(rest)):
            for sub in rec(rest[:k] + rest[k + 1:]):
                yield [(first, rest[k])] + sub

    yield from rec(order)


@dataclass(frozen=True)
class CappedScission(Digestible):
    """A valence-preserving bond rewrite: break ``cut`` bonds and form ``caps`` bonds, then read off
    the closed product molecules.  This is the graph-level *derivation* of a mediated reaction (an
    amide/ester hydrolysis, an addition-elimination) from structure -- the structural refinement of
    :class:`~smartchem.decompiler_mediated.MediatedEdge`.

    The object *is* the plan (reactant, consumed reagents, and the broken/formed bonds in one joined
    index space); :attr:`products` are DERIVED, so there is nothing to lie about.  The constructor is
    the certificate, all of it recomputed from the stored molecules:

    * **valence preserved atom-by-atom** -- for every atom, the bond order removed by ``cut`` equals
      the order restored by ``caps``, so each atom ends with exactly its starting valence.  This is
      the structural teeth: bonds are *rewired*, never created or destroyed at an atom.  It is a
      strictly stronger claim than mass conservation.
    * **closed products** -- ``cut``/``caps`` partition the joined graph into connected molecules with
      no residual open valence (``caps`` are genuinely new bonds, not duplicates of surviving ones);
    * **a real mediated cleavage** -- at least two products, the reactant's own atoms end up split
      across at least two of them (it was actually cleaved), and no product is an untouched reagent
      (the reagent was consumed, matching the MediatedEdge no-pass-through rule);
    * **W1 descent** -- every product is strictly lower rank (fewer atoms) than the reactant.

    W3 is unchanged: this certifies that such a rewrite EXISTS and conserves valence, never that the
    reaction occurs or under what conditions.  Which of several valence-valid rewrites corresponds to
    a real compound is decided downstream, by matching :attr:`products` against the sourced structure
    registry -- structure enumerates, evidence identifies.
    """

    schema_version: str
    reactant: Molecule
    reagents: tuple[Molecule, ...]
    cut: tuple[Bond, ...]
    caps: tuple[Bond, ...]

    def __post_init__(self) -> None:
        if self.schema_version != CAPPED_SCISSION_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {CAPPED_SCISSION_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a Molecule")
        if type(self.reagents) is not tuple or not self.reagents or any(
            type(r) is not Molecule for r in self.reagents
        ):
            raise ScissionError("reagents must be a non-empty tuple of Molecules (the consumed mediators)")
        for name, seq in (("cut", self.cut), ("caps", self.caps)):
            if type(seq) is not tuple or any(type(b) is not Bond for b in seq):
                raise ScissionError(f"{name} must be a tuple of Bond values")
            if list(seq) != sorted(seq) or len(set(seq)) != len(seq):
                raise ScissionError(f"{name} must be sorted and distinct")
        atoms, bonds, _offsets = _join(self.reactant, self.reagents)
        n = len(atoms)
        cut = frozenset(self.cut)
        caps = frozenset(self.caps)
        if not cut <= bonds:
            raise ScissionError("every cut bond must be a bond of the joined reactant+reagents graph")
        if not cut:
            raise ScissionError("a capped scission must break at least one bond")
        surviving = bonds - cut
        # caps must be genuinely NEW bonds (not a surviving pair re-added), and reference real atoms
        surviving_pairs = {(b.i, b.j) for b in surviving}
        for c in caps:
            if not (0 <= c.i < n and 0 <= c.j < n):
                raise ScissionError("a cap bond refers outside the joined atom set")
            if (c.i, c.j) in surviving_pairs:
                raise ScissionError("a cap bond duplicates a surviving bond; caps must be new bonds")
        # -- valence preserved at every atom: order removed by cut == order added by caps -----
        for a in range(n):
            removed = _degree(cut, a)
            added = _degree(caps, a)
            if removed != added:
                raise ScissionError(
                    f"valence not preserved at joined atom {a}: cut removed {removed} but caps "
                    f"added {added}; a capped scission only REWIRES bonds"
                )
        result = surviving | caps
        comps = _components(n, result)
        if len(comps) < 2:
            raise ScissionError("a capped scission must yield at least two product molecules")
        # every product strictly lower rank than the reactant (descent), and the reactant's own
        # atoms must be split across >= 2 products (it was genuinely cleaved, not merely conjugated)
        r_atoms = set(range(len(self.reactant.atoms)))
        reactant_touch = sum(1 for comp in comps if r_atoms & set(comp))
        if reactant_touch < 2:
            raise ScissionError("the reactant's atoms are not split across products; nothing was cleaved")
        for comp in comps:
            if len(comp) >= len(self.reactant.atoms):
                raise ScissionError("every product must have strictly fewer atoms than the reactant (W1)")
        # no product is an untouched reagent (the reagent must be consumed -- no pass-through)
        reagent_canon = {r.canonical() for r in self.reagents}
        for prod in self._product_molecules(atoms, comps, result):
            if prod.canonical() in reagent_canon:
                raise ScissionError(
                    "a product is an unconsumed reagent (pass-through); the mediator must be consumed"
                )

    @staticmethod
    def _product_molecules(
        atoms: tuple[str, ...], comps: list[tuple[int, ...]], result: frozenset[Bond]
    ) -> tuple[Molecule, ...]:
        out: list[Molecule] = []
        for comp in comps:
            local = {a: k for k, a in enumerate(comp)}
            frag_atoms = tuple(atoms[a] for a in comp)
            frag_bonds = frozenset(
                Bond(local[b.i], local[b.j], b.order)
                for b in result
                if b.i in local and b.j in local
            )
            out.append(Molecule(frag_atoms, frag_bonds).canonical())
        return tuple(out)

    @property
    def products(self) -> tuple[Molecule, ...]:
        """The derived, valence-closed product molecules (canonical), sorted deterministically."""
        atoms, bonds, _ = _join(self.reactant, self.reagents)
        result = (bonds - frozenset(self.cut)) | frozenset(self.caps)
        mols = self._product_molecules(atoms, _components(len(atoms), result), result)
        return tuple(sorted(mols, key=lambda m: (len(m.atoms), repr(m))))

    def forget(self) -> MediatedEdge:
        """The forgetful image: the composition-level :class:`MediatedEdge` this rewrite realizes.

        Products and reagents collapse to formulas; the result flows into the review layer exactly
        like any mediated edge, now cross-checked against a real bond-graph derivation.
        """
        def _formula(m: Molecule) -> Formula:
            return Formula.of(m.formula, m.charge)

        def _merge(mols) -> tuple[tuple[Formula, int], ...]:
            counts: dict[Formula, int] = {}
            for m in mols:
                f = _formula(m)
                if f.is_element:
                    # a single-element product (H2 from capping two H ends, O2, ...) forgets to its
                    # unit element bucket carrying the atom count -- MediatedEdge's element convention,
                    # the same collapse ScissionEdge.forget performs. The general capper can now
                    # produce these where the order-1 capper never did.
                    (symbol, count), = f.counts
                    bucket = Formula.bucket(symbol)
                    counts[bucket] = counts.get(bucket, 0) + count
                else:
                    counts[f] = counts.get(f, 0) + 1
            return tuple(sorted(counts.items(), key=lambda pm: ((pm[0].counts, pm[0].charge), pm[1])))

        return MediatedEdge(
            _formula(self.reactant), 1, _merge(self.reagents), _merge(self.products)
        )

    def equation(self) -> str:
        lhs = " + ".join([repr(self.reactant)] + [repr(r) for r in self.reagents])
        rhs = " + ".join(repr(p) for p in self.products)
        return f"{lhs} -> {rhs}"

    def __repr__(self) -> str:
        return f"CappedScission({self.equation()})"


def capped_scissions(
    reactant: Molecule,
    reagents: tuple[Molecule, ...],
    *,
    max_reactant_cuts: int = 1,
    budget: int = 50_000,
) -> tuple[tuple[CappedScission, ...], bool]:
    """Enumerate valence-preserving hydrolytic / addition-elimination cleavages of ``reactant``.

    The general order-1 capper: break ``k`` order-1 bonds of the reactant (``k`` in
    ``1..max_reactant_cuts``), opening ``2k`` order-1 valences, and consume ``k`` reagent instances --
    a size-``k`` multiset drawn (with repetition) from the declared reagent TYPES ``reagents``, each
    cut at one of its order-1 bonds, opening ``2k`` reagent valences.  The ``2k`` reactant ends are
    then matched to the ``2k`` reagent ends over EVERY bipartite pairing (a permutation), and each
    pairing's cap set is handed to the :class:`CappedScission` certificate, which drops any rewrite
    that fails to cleave, conserve valence, or consume its reagents.

    ``max_reactant_cuts = 1`` (the default) is single-bond hydrolysis -- amide/ester cleavage,
    hydrogenolysis. ``k = 2`` reaches double-hydrolysis (a diester to two acids + a diol needs two
    water) and multi-site cleavage; higher orders multiply the search.  Every valence-valid rewrite is
    emitted -- including chemically odd ones -- because the engine enumerates structure; *which*
    products are real compounds is the data layer's job.  Returns ``(edges, complete)``; ``complete``
    is ``False`` iff ``budget`` was hit.

    General over order and topology (G3): a cut bond may be of any order, and the ``2k`` reactant plus
    ``2k`` reagent open ends are paired by a full **perfect matching** (not a reactant-to-reagent
    bijection), so a reactant-end-to-reactant-end cap -- a **ring-forming** rewrite -- is enumerated
    alongside the substitutions. A cap only joins two ends of EQUAL order (a single bond restoring both
    valences), and every candidate is filtered by the :class:`CappedScission` certificate, so soundness
    is unchanged; only the reach grew. Still out of scope (documented, not silently attempted):
    partial bond-order change (addition ACROSS a double bond, which is not a whole-bond rewrite) and
    heterolytic/charged caps -- the latter is :class:`HeterolyticScission` (Part 13 item 6).
    """
    if type(reactant) is not Molecule:
        raise TypeError("reactant must be a Molecule")
    if type(reagents) is not tuple or not reagents or any(type(r) is not Molecule for r in reagents):
        raise TypeError("reagents must be a non-empty tuple of reagent-TYPE Molecules")
    reagent_types = [r for r in reagents if r.bonds]
    if not reagent_types:
        return (), True
    r_bonds = sorted(reactant.bonds)
    out: dict[str, CappedScission] = {}
    work = 0
    for k in range(1, max_reactant_cuts + 1):
        for rcuts in combinations(r_bonds, k):
            r_ends = [(b.i, b.order) for b in rcuts] + [(b.j, b.order) for b in rcuts]  # 2k ends
            for type_choice in combinations_with_replacement(range(len(reagent_types)), k):
                reagent_mols = tuple(reagent_types[i] for i in type_choice)
                bond_options = [sorted(m.bonds) for m in reagent_mols]
                _atoms, _bonds, offsets = _join(reactant, reagent_mols)
                for chosen in product(*bond_options):
                    reagent_cut: list[Bond] = []
                    g_ends: list[tuple[int, int]] = []
                    for inst, b in enumerate(chosen):
                        off = offsets[1 + inst]
                        reagent_cut.append(Bond(b.i + off, b.j + off, b.order))
                        g_ends += [(b.i + off, b.order), (b.j + off, b.order)]  # 2k reagent ends
                    cut = tuple(sorted(list(rcuts) + reagent_cut))
                    ends = r_ends + g_ends
                    for matching in _perfect_matchings(len(ends)):
                        work += 1
                        if work > budget:
                            return tuple(sorted(out.values(), key=lambda e: e.digest)), False
                        caps: list[Bond] = []
                        valid = True
                        for i, j in matching:
                            (a, oa), (b, ob) = ends[i], ends[j]
                            if oa != ob or a == b:       # a cap joins equal-order ends of distinct atoms
                                valid = False
                                break
                            caps.append(Bond(a, b, oa))
                        if not valid:
                            continue
                        if len({(c.i, c.j) for c in caps}) != len(caps):
                            continue  # two caps on the same atom pair -> not a simple graph
                        try:
                            edge = CappedScission(
                                CAPPED_SCISSION_SCHEMA, reactant, reagent_mols, cut, tuple(sorted(caps))
                            )
                        except ScissionError:
                            continue  # not cleaving / not valence-preserving / pass-through -> dropped
                        out.setdefault(edge.digest, edge)
    return tuple(sorted(out.values(), key=lambda e: e.digest)), True


# ======================================================================================
# Rung 3 -- the recursive structure-level descent graph (the structure analogue of B2)
# ======================================================================================
def _mol_key(molecule: Molecule) -> str:
    """A presentation-invariant node identity for a fragment molecule (``asgiven:`` fallback)."""
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(molecule)


@dataclass(frozen=True)
class StructureDecompositionGraph(Digestible):
    """The full descent of one target *structure* to single atoms by repeated bond-graph scission.

    Nodes are molecules (the target and every radical fragment reached); hyperedges are
    :class:`ScissionEdge` s.  It is the structure-level analogue of
    :class:`~smartchem.decompiler.DecompositionGraph`: where that splits atom multisets, this splits
    the bond graph, so each node is a specific sub-structure rather than a composition.  Termination is
    W1, forced by the partition -- every fragment has strictly fewer atoms, so the descent bottoms out
    at single atoms.  ``status`` is ``COMPLETE`` only when the whole reachable graph fit the budget;
    ``REFUSED_BUDGET`` carries a partial graph and a reason, never a silent truncation (W2).

    One honest boundary, stated: a fragment is carried into the next level as its own bond graph, and
    the open valences left by the cut that made it are not threaded across levels -- so this certifies
    the SKELETON descent (which bonds break, into which sub-structures), not a radical-electron ledger.
    Cross-level open-valence tracking is a documented refinement.

    Three honest statuses, never a silent partial (W2):

    * ``COMPLETE`` -- the whole reachable graph descended to single atoms within budget.
    * ``COMPLETE_TO_DEPTH`` -- a *positive* bounded guarantee: every node within ``max_depth`` scission
      steps of the target is fully expanded, and the graph is complete out to that horizon. Deeper
      structure was deliberately not explored (the fast, chemically-legible mode for a large target
      whose full descent to atoms is huge). This is NOT a refusal and NOT ``is_complete``; it is a
      complete answer to a bounded question.
    * ``REFUSED_BUDGET`` -- the edge/candidate budget was hit before the graph closed; a partial graph
      plus a reason, never readable as complete.
    """

    schema_version: str
    target: Molecule
    max_cut_bonds: int
    budget: int
    status: str
    edges: tuple[ScissionEdge, ...]
    refusal_reason: str = ""
    max_depth: int | None = None

    _STATUSES = ("COMPLETE", "COMPLETE_TO_DEPTH", "REFUSED_BUDGET")

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURE_GRAPH_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {STRUCTURE_GRAPH_SCHEMA!r}")
        if type(self.target) is not Molecule:
            raise ScissionError("target must be a Molecule")
        if self.status not in self._STATUSES:
            raise ScissionError(f"status must be one of {self._STATUSES}")
        if self.status in ("COMPLETE", "COMPLETE_TO_DEPTH") and self.refusal_reason:
            raise ScissionError("a complete graph carries no refusal reason")
        if self.status == "REFUSED_BUDGET" and not self.refusal_reason:
            raise ScissionError("a REFUSED_BUDGET graph must state its reason")
        if self.status == "COMPLETE_TO_DEPTH" and self.max_depth is None:
            raise ScissionError("a COMPLETE_TO_DEPTH graph must state the max_depth it is complete to")
        if any(type(e) is not ScissionEdge for e in self.edges):
            raise ScissionError("edges must be ScissionEdge values")

    @property
    def is_complete(self) -> bool:
        """True only for a full descent to single atoms -- NOT for a bounded-depth graph."""
        return self.status == "COMPLETE"

    @property
    def is_complete_to_depth(self) -> bool:
        """True iff the graph is a positive bounded-depth answer (complete out to ``max_depth``)."""
        return self.status == "COMPLETE_TO_DEPTH"

    def nodes(self) -> frozenset[str]:
        """The identities (:func:`_mol_key`) of every molecule reached, including the target."""
        seen = {_mol_key(self.target)}
        for edge in self.edges:
            seen.add(_mol_key(edge.reactant))
            for fragment in edge.fragments:
                seen.add(_mol_key(fragment.molecule))
        return frozenset(seen)

    def terminals(self) -> frozenset[str]:
        """The single-atom leaf identities the descent bottoms out at."""
        keys: set[str] = set()
        for edge in self.edges:
            for fragment in edge.fragments:
                if len(fragment.molecule.atoms) == 1:
                    keys.add(_mol_key(fragment.molecule))
        return frozenset(keys)

    def edges_from(self, molecule: Molecule) -> tuple[ScissionEdge, ...]:
        """Every scission whose reactant is ``molecule`` (compared by presentation-invariant key)."""
        key = _mol_key(molecule)
        return tuple(e for e in self.edges if _mol_key(e.reactant) == key)


def structure_decompose(
    target: Molecule,
    *,
    max_cut_bonds: int = 1,
    budget: int = 100_000,
    max_edges: int = 5_000,
    max_depth: int | None = None,
) -> StructureDecompositionGraph:
    """Build the structure-level descent of ``target`` toward single atoms.

    Recurses :func:`scission_edges` on every fragment molecule (each strictly smaller, so it
    terminates), deduplicating nodes by presentation-invariant identity.  A budget hit yields a
    **loud** ``REFUSED_BUDGET`` graph, never a silent partial (W2).

    ``max_depth`` bounds the descent to that many scission steps from the target. It is the fast,
    chemically-legible mode: the full descent of a drug-sized molecule to single atoms is huge
    (paracetamol is ~7,750 edges / ~1,100 nodes) and its deepest layers are combinatorial shrapnel a
    chemist has no use for, whereas the first few layers are the recognisable fragments. A bounded run
    that closes within the horizon reports ``COMPLETE_TO_DEPTH`` -- a *positive* guarantee, complete
    out to ``max_depth``, distinct from both a full ``COMPLETE`` and a ``REFUSED_BUDGET`` truncation.
    ``max_depth=None`` (the default) is the full descent to atoms.
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    if max_depth is not None and max_depth < 1:
        raise ValueError("max_depth must be >= 1 (or None for the full descent)")
    collected: dict[str, ScissionEdge] = {}
    expanded: set[str] = set()
    frontier: list[tuple[Molecule, int]] = [(target, 0)]

    def build(status: str, reason: str) -> StructureDecompositionGraph:
        return StructureDecompositionGraph(
            STRUCTURE_GRAPH_SCHEMA, target, max_cut_bonds, budget, status,
            tuple(sorted(collected.values(), key=lambda e: e.digest)), reason, max_depth,
        )

    while frontier:
        node, depth = frontier.pop()
        key = _mol_key(node)
        if key in expanded or len(node.atoms) <= 1 or not node.bonds:
            expanded.add(key)
            continue
        if max_depth is not None and depth >= max_depth:
            continue                      # at the horizon: expandable, deliberately left unexpanded
        edges, complete = scission_edges(node, max_cut_bonds=max_cut_bonds, budget=budget)
        if not complete:
            return build("REFUSED_BUDGET", f"scission budget exhausted at {node!r}")
        expanded.add(key)
        for edge in edges:
            collected[edge.digest] = edge
            if len(collected) > max_edges:
                return build("REFUSED_BUDGET", f"edge budget ({max_edges}) exceeded")
            for fragment in edge.fragments:
                fkey = _mol_key(fragment.molecule)
                if fkey not in expanded and len(fragment.molecule.atoms) > 1:
                    frontier.append((fragment.molecule, depth + 1))
    # complete to atoms unless the depth horizon left an expandable fragment unexpanded (W2:
    # a bounded answer is labelled as such, never silently sold as a full descent)
    if max_depth is not None and any(
        len(f.molecule.atoms) > 1 and f.molecule.bonds and _mol_key(f.molecule) not in expanded
        for e in collected.values() for f in e.fragments
    ):
        return build("COMPLETE_TO_DEPTH", "")
    return build("COMPLETE", "")


# ======================================================================================
# Rung 6 -- heterolytic (ionic) scission: a bond breaks BOTH electrons one way
# ======================================================================================
def _subgraph(reactant: Molecule, origin: tuple[int, ...], charge: int) -> Molecule:
    """The connected sub-graph on ``origin`` (re-indexed) carrying net ``charge``."""
    local = {r: k for k, r in enumerate(origin)}
    atoms = tuple(reactant.atoms[r] for r in origin)
    bonds = frozenset(
        Bond(local[b.i], local[b.j], b.order)
        for b in reactant.bonds
        if b.i in local and b.j in local
    )
    return Molecule(atoms, bonds, charge, reactant.state)


@dataclass(frozen=True)
class HeterolyticScission(Digestible):
    """One HETEROLYTIC single-bond cleavage: ``reactant -> anion(-1) + cation(+1)``.

    Where a :class:`ScissionEdge` breaks a bond homolytically (each fragment keeps one electron, a
    radical), a heterolytic cleavage sends BOTH electrons to one side: the atom that keeps the pair
    becomes an anion, the atom that loses it a cation.  ``H-Cl -> H(+) + Cl(-)``, ``Na-Cl -> Na(+) +
    Cl(-)``, an acid dissociation.  The certificate is charge conservation on top of the scission
    conservation:

    * one order-1 ``cut_bond`` of a NEUTRAL reactant (v1 heterolysis of neutrals);
    * ``anion`` carries charge -1 and ``cation`` charge +1, so total charge is conserved (0);
    * their atoms partition the reactant's, and each is a strict sub-molecule (W1 descent);
    * stripped of charge, ``{anion, cation}`` are exactly the two connected components of
      ``reactant`` minus ``cut_bond`` (fidelity: the ions are the cut pieces, not invented graphs).

    W3 unchanged: this certifies that a valence-and-charge-consistent heterolytic split EXISTS, never
    that a bond ionises this way (which direction the electrons go is the physical selectivity the
    engine refuses to predict -- both assignments are enumerated).  The formula-level engine is
    neutral-only, so a heterolytic split has no v1 ``forget`` image; ionic descent lives at structure
    level, and its formula/review integration is a documented next rung.
    """

    schema_version: str
    reactant: Molecule
    cut_bond: Bond
    anion: Molecule
    cation: Molecule

    def __post_init__(self) -> None:
        if self.schema_version != HETEROLYTIC_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {HETEROLYTIC_SCHEMA!r}")
        for name, mol in (("reactant", self.reactant), ("anion", self.anion), ("cation", self.cation)):
            if type(mol) is not Molecule:
                raise ScissionError(f"{name} must be a Molecule")
        if self.reactant.charge != 0:
            raise ScissionError("v1 heterolysis splits a NEUTRAL reactant")
        if type(self.cut_bond) is not Bond or self.cut_bond not in self.reactant.bonds:
            raise ScissionError("cut_bond must be a bond of the reactant")
        if self.cut_bond.order != 1:
            raise ScissionError("v1 heterolysis cleaves an order-1 bond (one electron pair)")
        if self.anion.charge != -1 or self.cation.charge != 1:
            raise ScissionError("anion must carry charge -1 and cation charge +1")
        # charge conserved: -1 + 1 == reactant charge (0)
        if self.anion.charge + self.cation.charge != self.reactant.charge:
            raise ScissionError("charge not conserved across the heterolytic split")
        # atoms partition the reactant, each fragment strictly smaller (W1)
        if Counter(self.anion.atoms) + Counter(self.cation.atoms) != Counter(self.reactant.atoms):
            raise ScissionError("anion + cation atoms do not sum to the reactant composition")
        n = len(self.reactant.atoms)
        if len(self.anion.atoms) >= n or len(self.cation.atoms) >= n:
            raise ScissionError("each ion must have strictly fewer atoms than the reactant (W1)")
        # fidelity: neutralised, the ions are exactly the two components of reactant - cut_bond
        comps = _components(n, self.reactant.bonds - {self.cut_bond})
        if len(comps) != 2:
            raise ScissionError("a single-bond heterolysis needs a bridge bond (exactly two pieces)")
        want = {_subgraph(self.reactant, origin, 0).canonical() for origin in comps}
        got = {
            Molecule(self.anion.atoms, self.anion.bonds, 0, self.anion.state).canonical(),
            Molecule(self.cation.atoms, self.cation.bonds, 0, self.cation.state).canonical(),
        }
        if want != got:
            raise ScissionError("anion/cation are not the two connected pieces of the cut reactant")

    def equation(self) -> str:
        return f"{self.reactant!r} -> {self.cation!r} + {self.anion!r}"

    def __repr__(self) -> str:
        return f"HeterolyticScission({self.equation()})"


def heterolytic_scissions(molecule: Molecule) -> tuple[HeterolyticScission, ...]:
    """Every single-bond heterolytic cleavage of a neutral ``molecule`` into an anion + a cation.

    For each order-1 bridge bond, both electron assignments are emitted (either component may take the
    pair) -- because which way a bond ionises is physical selectivity the engine does not predict.
    Deduplicated by digest.  Multi-bond and charged-reactant heterolysis are documented gaps.
    """
    if type(molecule) is not Molecule:
        raise TypeError("molecule must be a Molecule")
    if molecule.charge != 0:
        raise ScissionError("v1 heterolysis splits a neutral molecule")
    n = len(molecule.atoms)
    out: dict[str, HeterolyticScission] = {}
    for b in sorted(molecule.bonds):
        if b.order != 1:
            continue
        comps = _components(n, molecule.bonds - {b})
        if len(comps) != 2:
            continue  # not a bridge -> no single-bond split
        first, second = comps
        for neg_origin, pos_origin in ((first, second), (second, first)):
            edge = HeterolyticScission(
                HETEROLYTIC_SCHEMA,
                molecule,
                b,
                _subgraph(molecule, neg_origin, -1),
                _subgraph(molecule, pos_origin, 1),
            )
            out.setdefault(edge.digest, edge)
    return tuple(sorted(out.values(), key=lambda e: e.digest))


# ======================================================================================
# G4 -- redox (electron-transfer) half-reactions and the unified ionic edge view
# ======================================================================================
@dataclass(frozen=True)
class RedoxHalfReaction(Digestible):
    """One electron-transfer half-reaction: ``reduced -> oxidized + n e-`` (an OXIDATION).

    Electrons are charge carriers with no atoms (:data:`ELECTRON`), so mass is conserved trivially and
    **charge** is the conserved quantity the certificate turns on: the oxidised species carries ``n``
    more positive charge, the ``n`` electrons carry ``n`` negative. This is the chemical<->EM bridge --
    an electrode half-reaction, an ionisation, a redox couple -- spelled as an exact conserving
    morphism, the ionic analogue of a scission.

    The certificate (recomputed from the fields, never trusted):

    * ``reduced`` and ``oxidized`` are the SAME species but for charge -- identical atoms, bonds and
      state (a redox step moves electrons, it does not make or break bonds);
    * ``electrons`` >= 1;
    * charge conserved: ``oxidized.charge - electrons == reduced.charge`` (removing ``n`` electrons
      raises the charge by ``n``).

    W3 unchanged: this certifies that a charge-and-mass-consistent electron transfer EXISTS, never that
    it occurs, at what potential, or that this oxidation state is accessible -- *which* oxidation
    happens is physical selectivity the engine refuses to predict (it enumerates ``n = 1, 2, ...``).
    """

    schema_version: str
    reduced: Molecule
    oxidized: Molecule
    electrons: int

    def __post_init__(self) -> None:
        if self.schema_version != REDOX_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {REDOX_SCHEMA!r}")
        if type(self.reduced) is not Molecule or type(self.oxidized) is not Molecule:
            raise ScissionError("reduced and oxidized must be Molecules")
        if type(self.electrons) is not int or self.electrons < 1:
            raise ScissionError("a half-reaction must transfer at least one electron")
        if (self.reduced.atoms != self.oxidized.atoms
                or self.reduced.bonds != self.oxidized.bonds
                or self.reduced.state != self.oxidized.state):
            raise ScissionError(
                "reduced and oxidized must be the same species but for charge; a redox step moves "
                "electrons, it does not make or break bonds"
            )
        if self.oxidized.charge - self.electrons != self.reduced.charge:
            raise ScissionError(
                f"charge not conserved: oxidized {self.oxidized.charge} - {self.electrons} e- "
                f"!= reduced {self.reduced.charge}"
            )

    @property
    def products(self) -> tuple[Molecule, ...]:
        """The oxidised species plus the ``n`` released electrons (each a massless charge carrier)."""
        return (self.oxidized,) + (ELECTRON,) * self.electrons

    def equation(self) -> str:
        e = f"{self.electrons} e-" if self.electrons > 1 else "e-"
        return f"{self.reduced!r} -> {self.oxidized!r} + {e}"

    def __repr__(self) -> str:
        return f"RedoxHalfReaction({self.equation()})"


def redox_couples(species: Molecule, *, max_electrons: int = 2) -> tuple[RedoxHalfReaction, ...]:
    """The oxidation half-reactions of ``species`` removing ``1..max_electrons`` electrons.

    A pure structural/charge enumeration -- it does NOT claim which oxidation state is accessible or at
    what potential (that is physics, W3). The reduction direction is the mirror image and is obtained by
    swapping reduced/oxidized; only oxidations are emitted here to avoid double-counting a couple.
    """
    if type(species) is not Molecule:
        raise TypeError("species must be a Molecule")
    if type(max_electrons) is not int or max_electrons < 1:
        raise ValueError("max_electrons must be >= 1")
    out: list[RedoxHalfReaction] = []
    for n in range(1, max_electrons + 1):
        oxidized = Molecule(species.atoms, species.bonds, species.charge + n, species.state)
        out.append(RedoxHalfReaction(REDOX_SCHEMA, species, oxidized, n))
    return tuple(out)


@dataclass(frozen=True)
class IonicEdges(Digestible):
    """The ionic decompositions of one species, wiring heterolysis and redox into one node view.

    This is the ionic analogue of a node's scission menu -- what :func:`scission_edges` is to homolytic
    (radical) descent, :func:`ionic_edges` is to heterolytic (ion) + redox (electron-transfer) descent.
    Every product here is a charged species or an electron, and :func:`~smartchem.decompiler_boundary`
    ``species_class`` labels them ION / carrier, never a neutral compound.

    One honest boundary, stated: heterolysis is emitted only for a NEUTRAL species (the v1 heterolytic
    engine splits neutrals), so this is a single ionic level, not a recursive ionic graph -- heterolysis
    of an already-charged ion is the documented next rung.
    """

    schema_version: str
    species: Molecule
    heterolytic: tuple[HeterolyticScission, ...]
    redox: tuple[RedoxHalfReaction, ...]

    def __post_init__(self) -> None:
        if self.schema_version != IONIC_EDGES_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {IONIC_EDGES_SCHEMA!r}")
        if type(self.species) is not Molecule:
            raise ScissionError("species must be a Molecule")
        if any(type(h) is not HeterolyticScission for h in self.heterolytic):
            raise ScissionError("heterolytic must be HeterolyticScission values")
        if any(type(r) is not RedoxHalfReaction for r in self.redox):
            raise ScissionError("redox must be RedoxHalfReaction values")

    @property
    def ions(self) -> tuple[Molecule, ...]:
        """Every charged product across the heterolytic cleavages (anions and cations)."""
        out: list[Molecule] = []
        for h in self.heterolytic:
            out.extend((h.anion, h.cation))
        return tuple(out)


def ionic_edges(molecule: Molecule, *, max_electrons: int = 2) -> IonicEdges:
    """The unified ionic edge set of ``molecule``: heterolytic cleavages + redox half-reactions.

    Heterolysis is enumerated only for a neutral molecule (the v1 engine's boundary); redox couples are
    enumerated for any species. The result bundles both so a caller sees a species' whole ionic menu at
    once -- the graph-level wiring of :class:`HeterolyticScission` and :class:`RedoxHalfReaction`.
    """
    if type(molecule) is not Molecule:
        raise TypeError("molecule must be a Molecule")
    het = heterolytic_scissions(molecule) if molecule.charge == 0 else ()
    redox = redox_couples(molecule, max_electrons=max_electrons)
    return IonicEdges(IONIC_EDGES_SCHEMA, molecule, het, redox)
