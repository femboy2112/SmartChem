"""
A category of conserving sequential histories.

This is the load-bearing structural layer. It enforces atom and net-charge conservation;
it does not enforce chemical feasibility, kinetics, thermodynamics or open-system balance.

The central design decision
--------------------------
Objects carry **bond topology**, not just atom counts.

That is not decoration. If an object were merely a bag of atoms, then every
mass-conserving reaction would have ``dom == cod`` and be an endomorphism: ``Na + Cl``
and ``NaCl`` would be the *same object*, so the reaction between them could not be a
morphism at all. That is exactly the defect the legacy engine had -- every "product" it
returned was its own reactants (finding F11). Giving objects structure is what makes
``Na + Cl -> NaCl`` a genuine arrow.

The theorem this buys
---------------------
Conservation is checked once, in the ``Reaction`` smart constructor, for **generators
only**. It then holds for every composite for free::

    f : A -> B  conserves  =>  formula(A) == formula(B)
    g : B -> C  conserves  =>  formula(B) == formula(C)
    ------------------------------------------------------
    g . f : A -> C         =>  formula(A) == formula(C)          [transitivity]

The object operation ``tensor_obj`` is commutative multiset union. The current morphism
representation is a *linear history*, however, so it cannot represent independent parallel
events modulo the interchange law. ``Reaction.scheduled_product`` therefore gives an
explicit left-then-right schedule; the legacy name ``Reaction.tensor`` is retained only as
a compatibility alias. The true symmetric-monoidal/open-system layer -- ports and process
graphs, where interchange holds under ``canonicalize`` -- is
``smartchem.open_chem_diagram.OpenChemDiagram``; ``scheduled_product`` is a deterministic
left-then-right SCHEDULE of the same generators, NOT the image of any projection from that
layer (the backbone's ``close`` is partial and refuses exactly the parallel diagrams this
method linearises), and not a rival tuple convention.

So a mass-violating reaction is not merely absent from this system, it is
**unconstructible**. ``Fe + O + Cl -> FeO`` (finding F1) raises at construction time
rather than silently dropping the chlorine.

This is also where structural pruning happens, before an energy oracle is consulted.
Composition and total charge are enforced here. Chemical valence is deliberately not:
labels are domain-neutral, so valence belongs in a chemistry-specific validator.

See ``tests/test_laws.py`` for property tests over generated finite examples. They exercise
the implementation but are not a formal proof of all Python values or physical validity.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import permutations, product
from math import factorial
from typing import Callable, Iterable, Iterator, Mapping

# 0.9.5 S16: canonicalisation is budgeted verification work. `verification` imports nothing of this
# package's chemistry at module level, so the dependency points one way and stays that way.
from .verification import charge_canonical_work, work_transparent_cache

# Budget for canonical relabelling, counted in *candidate permutations actually examined*
# -- not in atoms. See `_sorting_permutations` for why those differ by orders of magnitude.
# Above this, canonicalisation is refused rather than silently returning a non-canonical
# form. Full graph canonicalisation (the whole of nauty: automorphism pruning, a search
# tree over target cells) remains out of scope; only its first move, refinement, is here.
#
# Set to hold the ORIGINAL cap's worst-case TIME fixed, rather than to a round number.
# The 8-atom cap permitted 8! = 40_320 candidates at ~5.4 us each, about 0.2 s. That same
# 0.2 s has now been spent twice over to buy reach rather than atoms -- first by
# restricting to symbol classes (#21), then by refining those classes (#23) -- and the
# budget itself has never moved. It matters because `Config.__post_init__` canonicalises
# on every construction, so the worst case is paid per object, not once.
#
# Measured 2026-07-20 on this machine, and the per-candidate cost depends on how many
# bonds there are to sort, so the honest figure comes from a BONDED worst case:
#
#   C7 ring       5_040 candidates    19.4 ms    3.85 us/candidate
#   => 50_000 candidates is ~0.19 s, which is the ceiling this budget actually buys
#   C8 unbonded  40_320 candidates    57.1 ms    1.42 us/candidate  (no edges to sort)
#   C3H8 propane  2_880 candidates    16.2 ms    (241_920 before refinement)
#
# Benzene is out of REFINEMENT's budget at 518_400 candidates: its bond graph is
# vertex-transitive within each element, so no invariant computed from local structure can
# split the carbons. Refinement is only the first move of the nauty-style algorithm.
#
# The second move, INDIVIDUALISATION, is now BUILT (#25, `_canonical_by_individualisation`):
# when refinement stalls on a non-singleton cell, give one of its vertices a colour nobody
# else has and refine again, breaking by fiat the symmetry no local invariant could break.
# Canonicality is kept by minimising the edge tuple over every choice within the cell, so the
# cost is |cell| x (subproblem) rather than |cell|!. Reached ONLY when refinement alone is
# over budget -- exactly the molecules that used to raise -- so it is purely additive: no
# canonical form that existed before it can move. Benzene now canonicalises in ~0.5 ms.
#
# Measured (scratchpad/ir_probe.py), leaves of the individualisation tree:
#
#   C6H6 benzene   518_400 -> 6        86_400x
#   C6H14 hexane 3_317_760 -> 1_152     2_880x
#   C4H10 butane    69_120 -> 288         240x
#   C3H8 propane     2_880 -> 144          20x
#   C8 unbonded     40_320 -> 40_320         1x
#
# and on every case small enough to brute-force, the leaf count equals |Aut(G)| exactly,
# which is the floor -- no canonical search can examine fewer labellings than the graph
# has automorphisms. C8 is unimprovable for that reason and not for want of trying.
#
# So the boundary is no longer "benzene is too symmetric" NOR "this implementation stops
# after the first of two moves" -- both moves are now here. Because a third canonical form is
# exactly the change where a silent error corrupts every equality in the category, it earned
# the brute-force verification #23 got: `tests/test_individualisation.py` proves the benzene
# form is a genuine relabelling of benzene (sound, isomorphic) AND relabel-invariant across
# every respelling, and the whole suite is the additivity regression that no prior form moved.
# The one remaining honest boundary is the leaf ceiling: a fully-symmetric non-molecule (the
# complete graph K_n) still refuses loudly rather than grind, since false-twin pruning is not
# true-twin pruning (see `_canonical_by_individualisation`).
#
# 0.9.5 S16 moved the boundary again, and retired two sentences above: with automorphism pruning
# the leaf count is no longer |Aut(G)| (a symmetric subtree is walked once, not once per image),
# and the ceilings are now leaves, search nodes, and search nodes x atoms -- each refusing with
# `CanonicalBoundExceeded`. The history stays; it is how the floor was found before it was lowered.
_MAX_CANONICAL_CANDIDATES = 50_000


def _blocks(keys: tuple) -> list[tuple[int, ...]]:
    """Positions grouped by equal key, the groups themselves in sorted key order."""
    order = sorted(range(len(keys)), key=lambda i: keys[i])
    blocks: list[tuple[int, ...]] = []
    start = 0
    for k in range(1, len(order) + 1):
        if k == len(order) or keys[order[k]] != keys[order[start]]:
            blocks.append(tuple(order[start:k]))
            start = k
    return blocks


def _wl_colours(atoms: tuple[str, ...], bonds: frozenset["Bond"]) -> tuple[int, ...]:
    """
    One-dimensional Weisfeiler-Leman refinement: a colour per atom, invariant under
    relabelling, computed only from what the bond graph says about each atom's
    surroundings.

    Start every atom coloured by its element, then repeatedly recolour it by the pair
    ``(its own colour, the sorted multiset of its neighbours' colours-and-bond-orders)``,
    naming the new colours by sorting those signatures. Stop when a round splits nothing.

    Two properties are load-bearing, and both come from the same fact -- that nothing here
    ever mentions an atom's index:

    - **Equivariance.** Relabelling the molecule permutes the colours with it. That is
      what lets `canonical()` put colours in its sort key at all.
    - **Consistency with symbols.** A colour is ranked by a signature whose first
      component is the previous colour, so refinement never reorders classes, only splits
      them. Sorting by final colour therefore also sorts by element.

    What it cannot do is separate atoms that are genuinely interchangeable. It is a
    one-sided instrument: different colours prove two atoms are distinguishable, equal
    colours prove nothing. So the classes it returns are always a coarsening of the true
    automorphism orbits, which is exactly why the count it produces is a safe upper bound
    on the work and never an underestimate.
    """
    ranks = {symbol: k for k, symbol in enumerate(sorted(set(atoms)))}
    return _refine_from(atoms, bonds, [ranks[a] for a in atoms])


def _refine_from(
    atoms: tuple[str, ...], bonds: frozenset["Bond"], initial: list[int]
) -> tuple[int, ...]:
    """Equitable colour refinement seeded from an arbitrary initial colouring.

    Generalises :func:`_wl_colours` (which seeds from element symbols) to any starting
    partition, so an *individualised* vertex -- one handed a colour of its own -- propagates
    its distinction through the graph.  Same one-sided guarantee as WL: the result is a
    coarsening of the orbits under the automorphisms that FIX the seed, and it is equivariant
    under any relabelling that preserves the seed.

    The seed's rank is the first component of every signature, so a round only ever *splits* a
    class, never reorders two -- the ordered partition therefore stays consistent with the
    seed, which is exactly what keeps the individualisation search (below) canonical.
    """
    n = len(atoms)
    neighbours: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for b in bonds:
        neighbours[b.i].append((b.j, b.order))
        neighbours[b.j].append((b.i, b.order))
    seed = {c: k for k, c in enumerate(sorted(set(initial)))}
    colour = [seed[c] for c in initial]
    for _ in range(n):                      # each round splits or stops; at most n-1 split
        signature = [
            (colour[i], tuple(sorted((order, colour[j]) for j, order in neighbours[i])))
            for i in range(n)
        ]
        ranks = {s: k for k, s in enumerate(sorted(set(signature)))}
        refined = [ranks[s] for s in signature]
        if len(set(refined)) == len(set(colour)):
            break                           # partition stable: no class was split
        colour = refined
    return tuple(colour)


def _refined_blocks(atoms: tuple[str, ...], bonds: frozenset["Bond"]) -> list[tuple[int, ...]]:
    """Atom positions grouped by Weisfeiler-Leman colour, groups in colour order."""
    return _blocks(_wl_colours(atoms, bonds))


def _cost_of(blocks: list[tuple[int, ...]]) -> int:
    """Candidates enumerated when permuting within these classes: prod(m_i!)."""
    total = 1
    for block in blocks:
        total *= factorial(len(block))
    return total


def _canonical_blocks(
    atoms: tuple[str, ...], bonds: frozenset["Bond"]
) -> list[tuple[int, ...]]:
    """
    The classes `canonical()` permutes within: symbol classes, refined ONLY if the plain
    ones would blow the budget.

    Refinement is reach, not speed -- and it was measured to be a tax when spent where
    reach was not needed. Weisfeiler-Leman costs a fixed 5-55 us per call, against 1-4 us
    per candidate; on H2O, CO2, H2 and CH2O it splits nothing at all (2 candidates before,
    2 after) and made construction 3x slower. Those are the species this repository builds
    most, and `Config.__post_init__` canonicalises on every construction.

    So the rule is: try the cheap restriction; refine only when the alternative is
    refusing. Two properties fall out of that, and both are worth more than the speedup
    given up:

    - **The change is purely additive.** Any molecule that could be canonicalised before
      #23 has a symbol cost within budget, so it never reaches the refined branch and its
      canonical form is bit-for-bit what it always was. Only molecules that previously
      RAISED can see the new key.
    - **The two keys never have to agree.** A molecule takes its branch by symbol cost,
      which is fixed by its multiset of elements -- an isomorphism invariant. So every
      relabelling of one molecule takes the same branch, and two molecules in different
      branches differ in composition and were never equal anyway.

    The price, stated rather than hidden: a species whose symbol cost is under budget but
    which refinement would have made much cheaper still pays the old price. A C7 chain
    costs 5,040 candidates (~20 ms) where refinement would have charged 8. That is a
    missed optimisation on a molecule that already worked, not a regression, and it buys
    the additivity above.
    """
    blocks = _blocks(atoms)
    if _cost_of(blocks) <= _MAX_CANONICAL_CANDIDATES:
        return blocks
    return _refined_blocks(atoms, bonds)


def _canonical_cost(atoms: tuple[str, ...], bonds: frozenset["Bond"]) -> int:
    """How many candidate permutations `canonical()` will examine."""
    return _cost_of(_canonical_blocks(atoms, bonds))


def _symbol_cost(atoms: tuple[str, ...]) -> int:
    """
    What canonicalisation costs without refinement: prod over ELEMENTS.

    Kept because the gap between this and `_canonical_cost` is the whole of #23, and a
    claim about a gap is worth more when both sides of it are computed rather than
    remembered. Also the gate itself: refinement happens exactly when this exceeds the
    budget.
    """
    return _cost_of(_blocks(atoms))


def _sorting_permutations(
    atoms: tuple[str, ...], bonds: frozenset["Bond"]
) -> Iterator[tuple[int, ...]]:
    """
    Every permutation that sorts the atom colours -- and, deliberately, no others.

    Why this loses nothing
    ----------------------
    ``canonical()`` minimises the key ``(symbols, colours, edges)`` lexicographically, and
    the restriction falls out of that ordering in two stages:

    1. Over all n! permutations the minimum of ``symbols`` is ``tuple(sorted(atoms))`` --
       a value fixed by the multiset of symbols and reachable by some permutation. A
       permutation that does not sort the symbols is beaten on the primary component
       whatever it does to the rest, so it can never be the argmin.
    2. Among those, the minimum of ``colours`` is ``tuple(sorted(colours))``, by the same
       argument one component down. Colours refine symbols and are ordered consistently
       with them (see `_wl_colours`), so the two stages never fight: sorting by colour
       sorts by symbol for free.

    What survives is the set of permutations that shuffle atoms *within a colour class*,
    of which there are prod(m_i!) over the refined classes rather than over the elements.
    That is where the reach comes from, and it is worth an order of magnitude or three:

        species      symbol classes   refined classes
        C2H5OH                1,440                12
        C3H8 propane        241,920             2,880
        C3H7OH propanol     241,920                24

    This is an exact restriction of the search, not a heuristic prune -- verified against
    brute force over all n! permutations in ``TestCanonicalShortcutIsExact``. The saving
    is composition- *and* topology-dependent, and vanishes entirely where the graph is
    symmetric enough that no local invariant separates anything: C8, and benzene. The
    refusal above ``_MAX_CANONICAL_CANDIDATES`` is what keeps those cases honest.

    Stage 2 is only *reached* when stage 1 alone would exceed the budget; see
    ``_canonical_blocks`` for why refining unconditionally was measured to be a tax.
    """
    return _permute_within(_canonical_blocks(atoms, bonds), len(atoms))


def _permute_within(blocks: list[tuple[int, ...]], n: int) -> Iterator[tuple[int, ...]]:
    """Every permutation that shuffles atoms only within the given classes."""
    targets: list[tuple[int, ...]] = []
    position = 0
    for block in blocks:
        targets.append(tuple(range(position, position + len(block))))
        position += len(block)
    for choice in product(*(permutations(block) for block in blocks)):
        perm = [0] * n
        for olds, news in zip(choice, targets):
            for old, new in zip(olds, news):
                perm[old] = new
        yield tuple(perm)


# --------------------------------------------------------------------------------------
# #25 -- individualisation: nauty's SECOND move, so a graph refinement cannot split still
# canonicalises. Reached ONLY when refinement alone leaves the block search above budget
# (exactly the molecules that used to raise), so it is purely additive: no canonical form
# that existed before this can move, and a molecule always takes the same branch because
# `_canonical_cost` is an isomorphism invariant. See the module header (#25) for the why.
# --------------------------------------------------------------------------------------
# A leaf ceiling, honest above the refinement path's, not infinite: it caps the search-tree
# leaves we will grind before refusing loudly (never a wrong silent form). With false-twin
# pruning (see below) every REAL molecule stays in the low thousands -- benzene 12, adamantane
# ~40, a 90-atom symmetric ring ~1,000 -- so 50k is 10x-plus headroom for chemistry while
# keeping the refusal on a pathological all-symmetric graph (a complete graph K_n, not a
# molecule) bounded in time rather than a 13-second grind.
_MAX_INDIVIDUALISATION_LEAVES = 50_000
# 0.9.5 S16 -- a NODE ceiling beside the leaf ceiling. The leaf cap alone left the INTERNAL nodes
# unbounded: 17-carbon tetra-tert-butylmethane's skeleton (four tBu on one carbon, |Aut| ~ 31,000
# before its hydrogens) recursed 24+ levels for well over 40 s without ever reaching the leaf cap
# -- a front-door hang, not a refusal. Every call of the search counts one node. Exceeding it
# refuses exactly as the leaf cap does (a NotImplementedError), so `resonance_identity`'s
# literal-key fallback keeps working. MEASURED 2026-09-30 by the S16 differential
# (`experiments/v0_9_5_canonical_differential.py`) over ~4,400 molecules -- named (incl. C60),
# rings C3-C80 bare and hydrogenated, the Wave C4 shapes, 2,400 seeded random molecules with
# explicit H (1,288 on this path), registry constants, the test suite's SMILES literals, and
# every molecule the frozen service corpus canonicalised: chemistry maximum 578 nodes
# (tetra-tert-butylmethane); the deliberate depth probe [CH1100] 1,100. 2**14 is 28x / 14.9x.
_MAX_INDIVIDUALISATION_NODES = 1 << 14
# ...and a ceiling on search nodes x atoms, because a node is not a constant: each one re-refines
# the WHOLE graph, O(n) and worse. A node cap alone let a large, merely-repetitive input grind --
# [CH5000] (8 characters) is 5,000 nodes, under the cap, and 610 s of refinement. Every node costs
# its atom count in this unit (and in the canonical_work charge), so the product bounds the time a
# search can take, not just its shape. MEASURED (same differential): chemistry maximum 111,852
# (a hydrogenated C78-C80 ring); [CH1000] 1.0M and [CH1100] 1.21M stay in bounds; 2**21 is 18.7x
# the chemistry maximum, and [CH5000] now refuses at node 419 instead of grinding for 610 s.
_MAX_INDIVIDUALISATION_ATOM_NODES = 1 << 21
# How many discovered automorphisms the search keeps as pruning generators. Every node re-reads the
# stored list, so an unbounded list would make a node cost grow with the automorphisms found (on a
# near-ceiling graph, quadratic in the node count). Dropping a generator only prunes LESS -- the
# orbits get finer, never wrong -- so a cap costs speed on a pathological graph, never soundness.
_MAX_STORED_AUTOMORPHISMS = 1 << 10


class CanonicalBoundExceeded(NotImplementedError):
    """Canonicalisation refused: the graph needs more individualisation leaves or search nodes than
    the ceilings above allow (0.9.5 S16).

    Still a ``NotImplementedError`` -- the family every existing caller already catches (the
    ``asgiven:`` literal-key fallback of ``resonance_identity``, the structure-descent guards) -- so
    naming it moves no behaviour; it exists so the front door can tell THIS refusal ("the compiler
    will not identify that graph within its bounds") from an arbitrary internal ``NotImplementedError``.
    """


def _partition_colours(partition: list[tuple[int, ...]], n: int) -> list[int]:
    """The per-atom colour (its cell's ordinal) implied by an ordered partition."""
    colour = [0] * n
    for k, cell in enumerate(partition):
        for i in cell:
            colour[i] = k
    return colour


def _refine_partition(
    atoms: tuple[str, ...], bonds: frozenset["Bond"], partition: list[tuple[int, ...]]
) -> list[tuple[int, ...]]:
    """Equitably refine an ordered partition to a fixpoint, preserving cell order (splits only).

    Seeds :func:`_refine_from` from the partition's own colouring, so a singleton individualised
    cell keeps its distinction; the result is the refined cells grouped in colour order, which --
    because refinement only splits -- is consistent with the input order.
    """
    colour = _refine_from(atoms, bonds, _partition_colours(partition, len(atoms)))
    return _blocks(colour)


def _canonical_by_individualisation(
    atoms: tuple[str, ...],
    bonds: frozenset["Bond"],
    on_node: Callable[[], None] | None = None,
) -> tuple[tuple[str, ...], tuple[tuple[int, int, int], ...]]:
    """Canonical ``(symbols, edges)`` via refinement + individualisation.

    When refinement stalls on a non-singleton cell, individualise each of its vertices in turn
    (hand it a colour of its own), refine again, and recurse to a discrete partition; the
    canonical edge-tuple is the **minimum** over every individualisation choice. Minimising over
    the choices is what makes the answer independent of *which* symmetric vertex was picked --
    the relabel-invariance the tests pin down by brute force. The symbols prefix is the atoms in
    refined-cell order and is constant across every leaf (refinement never crosses a symbol
    class), so it is read once from the start partition.

    **False-twin pruning keeps it fast.** Two atoms in the target cell with no neighbour inside
    that cell and an identical neighbour multiset are *provably* interchangeable -- swapping them
    is a graph automorphism that needs no discovery -- so the branch is taken on ONE representative
    per twin class. This is exactly what collapses the ``2**(#CH2)`` hydrogen blow-up (the two H on
    a carbon are false twins) that otherwise makes a symmetric ring hopeless. It is sound because a
    pruned branch is an automorphic image of an explored one, so the minimum is unchanged -- pinned
    by the soundness + relabel-invariance tests, which break the instant a non-twin is pruned.

    **Automorphism pruning (0.9.5 S16) catches what twins cannot.** Twins are depth-one symmetry
    only; symmetric SUBTREES (the twelve methyls of four tert-butyls) are not twins, and the search
    used to enumerate them factorially -- the leaf cap never fired because the time went into
    internal nodes. So: whenever a leaf's certificate (its sorted edge tuple; the symbols prefix is
    constant) EQUALS the first leaf's or the current best's, the two labellings differ by an
    automorphism ``g`` (``g[v]`` = the reference leaf's atom carrying ``v``'s label). ``g`` is
    VERIFIED -- symbols and the bond set with orders preserved, target cell mapped onto itself --
    never trusted, then stored. At every node with individualised prefix ``(v1..vd)``, the stored
    automorphisms that fix every ``vi`` generate a group whose orbits on the target cell are joined
    (union-find); ONE child per orbit is explored, in the existing cell order, re-checked before
    each child, because an earlier sibling's subtree may have found the automorphism that merges
    two later siblings. It composes with twin pruning: a twin swap is an automorphism fixing the
    prefix too, so both prune along one equivalence.

    *Soundness.* A pruned child ``w = h(v)``, ``h`` in that group -- a product of automorphisms
    fixing the prefix, hence one itself -- is an automorphic image of an explored sibling ``v``.
    Refinement is equivariant under automorphisms fixing its seed, so ``h`` carries ``v``'s whole
    subtree onto ``w``'s, and every leaf under ``w`` is a leaf under ``v`` relabelled by ``h`` --
    the IDENTICAL edge tuple. The set of leaf certificates is unchanged, so its MINIMUM is
    unchanged, so every canonical form returned is byte-identical to the unpruned search; only the
    number of nodes visited to find it moves. (Proven, not asserted: the S16 differential
    ``experiments/v0_9_5_canonical_differential.py`` runs a verbatim copy of the old search.)

    Bounded three ways -- :data:`_MAX_INDIVIDUALISATION_LEAVES` leaves,
    :data:`_MAX_INDIVIDUALISATION_NODES` search nodes, :data:`_MAX_INDIVIDUALISATION_ATOM_NODES`
    search nodes x atoms; past any of them this refuses loudly with :class:`CanonicalBoundExceeded`
    (a ``NotImplementedError``), exactly like the plain path, only at a far higher ceiling. The
    walk is an explicit stack, so depth is bounded by those ceilings, never by Python's recursion
    limit. ``on_node`` (if given) is called once per node BEFORE that node's work -- how
    :meth:`Molecule.canonical` charges a verification budget ahead of the work it bounds (the return
    value is unchanged: ``(symbols, edges)``).
    """
    n = len(atoms)
    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for b in bonds:
        adjacency[b.i].append((b.j, b.order))
        adjacency[b.j].append((b.i, b.order))
    bond_set = frozenset((b.i, b.j, b.order) for b in bonds)       # Bond keeps i < j
    start = _refine_partition(atoms, bonds, _blocks(_wl_colours(atoms, bonds)))
    symbols = tuple(atoms[i] for cell in start for i in cell)
    # (edges, order) of the FIRST leaf reached and of the running best; order[new] = old atom
    first: list[tuple | None] = [None]
    best: list[tuple | None] = [None]
    automorphisms: list[tuple[int, ...]] = []
    known: set[tuple[int, ...]] = set()
    identity = tuple(range(n))
    leaves = [0]
    nodes = [0]

    def verified_automorphism(order: tuple[int, ...], reference: tuple[int, ...]) -> tuple[int, ...]:
        # g sends this leaf's atom labelled `new` to the reference leaf's atom labelled `new`.
        # Equal certificates make that an automorphism by construction -- checked anyway, since a
        # wrong one would prune a live branch and move a canonical form without a sound.
        g = [0] * n
        for new, old in enumerate(order):
            g[old] = reference[new]
        if any(atoms[g[v]] != atoms[v] for v in range(n)) or any(
            (min(g[i], g[j]), max(g[i], g[j]), o) not in bond_set for i, j, o in bond_set
        ):
            raise AssertionError(
                "individualisation derived a non-automorphism from two equal leaf certificates; "
                "refusing to prune on it"
            )
        return tuple(g)

    def leaf(order: tuple[int, ...]) -> None:
        perm = [0] * n
        for new, old in enumerate(order):
            perm[old] = new
        edges = tuple(sorted(
            (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
            for b in bonds
        ))
        if first[0] is None:
            first[0] = best[0] = (edges, order)
            return
        for ref_edges, ref_order in (first[0], best[0]):
            if edges == ref_edges:
                g = verified_automorphism(order, ref_order)
                if g != identity and g not in known and len(automorphisms) < _MAX_STORED_AUTOMORPHISMS:
                    known.add(g)
                    automorphisms.append(g)
                break
        if edges < best[0][0]:
            best[0] = (edges, order)

    def enter(partition: list[tuple[int, ...]], prefix: tuple[int, ...]) -> dict | None:
        # One search node: bounds, charge, refine; a leaf is scored on the spot (None), an
        # internal node comes back as the frame the loop below walks its children from.
        if leaves[0] > _MAX_INDIVIDUALISATION_LEAVES:
            raise CanonicalBoundExceeded(
                f"canonical relabelling by individualisation exceeded "
                f"{_MAX_INDIVIDUALISATION_LEAVES:,} leaves; graph too symmetric for this budget"
            )
        if nodes[0] >= _MAX_INDIVIDUALISATION_NODES:
            raise CanonicalBoundExceeded(
                f"canonical relabelling by individualisation exceeded "
                f"{_MAX_INDIVIDUALISATION_NODES:,} search nodes; graph too symmetric for this budget"
            )
        if (nodes[0] + 1) * n > _MAX_INDIVIDUALISATION_ATOM_NODES:
            raise CanonicalBoundExceeded(
                f"canonical relabelling by individualisation exceeded "
                f"{_MAX_INDIVIDUALISATION_ATOM_NODES:,} atom-refinements ({nodes[0]:,} search nodes x "
                f"{n:,} atoms); graph too large and symmetric for this budget"
            )
        nodes[0] += 1
        if on_node is not None:
            on_node()                              # charged BEFORE this node's refinement
        partition = _refine_partition(atoms, bonds, partition)
        target = next((k for k, cell in enumerate(partition) if len(cell) > 1), None)
        if target is None:                         # discrete: read the labelling off cell order
            leaves[0] += 1
            leaf(tuple(i for cell in partition for i in cell))
            return None
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
        # `root`: orbits on this cell of <stored automorphisms fixing the prefix>, grown lazily
        return {"partition": partition, "prefix": prefix, "target": target, "cell": cell,
                "cellset": cellset, "reps": reps, "next": 0, "root": {v: v for v in cell},
                "absorbed": 0, "explored": []}

    def find(root: dict, v: int) -> int:
        while root[v] != v:
            root[v] = root[root[v]]
            v = root[v]
        return v

    # The walk is an explicit stack, not recursion: depth grows with the individualisations a
    # graph needs (one per false-twin pair -- a CH2 chain, a CH1000 star), and the recursive
    # walk died with RecursionError near depth 1,000 (Wave C6). Same children in the same order
    # as the recursion it replaces, so the same leaves are scored in the same sequence.
    frame = enter(start, ())
    stack: list[dict] = [] if frame is None else [frame]
    while stack:
        top = stack[-1]
        root, cell, cellset, prefix = top["root"], top["cell"], top["cellset"], top["prefix"]
        child = None
        while child is None and top["next"] < len(top["reps"]):
            v = top["reps"][top["next"]]           # individualise each choice; minimise over them
            top["next"] += 1
            while top["absorbed"] < len(automorphisms):   # including those an earlier sibling found
                g = automorphisms[top["absorbed"]]
                top["absorbed"] += 1
                if any(g[p] != p for p in prefix):
                    continue
                for u in cell:
                    if g[u] not in cellset:        # equivariance says impossible; never trusted
                        raise AssertionError(
                            "an automorphism fixing the individualised prefix moved a target-cell "
                            "atom out of its cell; refusing to prune on it"
                        )
                    a, c = find(root, u), find(root, g[u])
                    if a != c:
                        root[c] = a
            if any(find(root, v) == find(root, x) for x in top["explored"]):
                continue                           # an automorphic image of an explored sibling
            top["explored"].append(v)
            partition, target = top["partition"], top["target"]
            child = enter(
                partition[:target] + [(v,), tuple(x for x in cell if x != v)] + partition[target + 1:],
                prefix + (v,),
            )
        if child is None:
            stack.pop()                            # every child walked (or the last one was a leaf)
        else:
            stack.append(child)

    assert best[0] is not None
    return symbols, best[0][0]


class ConservationError(ValueError):
    """Raised when a proposed reaction would create or destroy matter or charge."""


class CompositionError(ValueError):
    """Raised when morphisms are composed with mismatched domain and codomain."""


# ======================================================================================
# Bonds and molecules
# ======================================================================================
@dataclass(frozen=True, order=True)
class Bond:
    """An undirected bond between two atom positions within one molecule."""
    i: int
    j: int
    order: int = 1

    def __post_init__(self) -> None:
        if type(self.i) is not int or type(self.j) is not int:
            raise TypeError("bond endpoints must be integer atom positions")
        if type(self.order) is not int:
            raise TypeError("bond order must be an integer")
        if self.i == self.j:
            raise ValueError(f"self-bond at position {self.i}")
        if self.order < 1:
            raise ValueError(f"bond order must be >= 1, got {self.order}")
        if self.i > self.j:
            # keep (i, j) canonical so equality is structural, not orientation-dependent.
            # capture both endpoints before writing either: assigning i first would
            # clobber the value j needs to read.
            lo, hi = self.j, self.i
            object.__setattr__(self, "i", lo)
            object.__setattr__(self, "j", hi)


@dataclass(frozen=True)
class Molecule:
    """
    One connected chemical species, with explicit topology.

    ``atoms`` is positional: ``bonds`` refers to atoms by index. Raw dataclass equality is
    positional. Calling :meth:`canonical` (as ``Config`` does automatically) maps isomorphic
    spellings to the same labelled graph, so ``H-O-H`` built in either atom order then
    compares equal.

    ``state`` is an opaque internal-state label -- an electronic excitation, a mode, an
    operating point. It is part of the object's IDENTITY but not of the conserved
    signature, and that separation is the whole point of the field.

    Without it, the only way to distinguish an excited emitter from a relaxed one is to
    change a symbol, and changing a symbol changes ``formula`` -- so ``Na* -> Na + photon``
    is rejected as mass-violating when it is nothing of the kind. That is a real
    foreclosure rather than a hypothetical: an antenna or any radiating system is exactly
    *the same matter* in a different energy state, and a category that cannot say so
    cannot host one. Photochemistry needs it for the same reason.

    So: composition and charge are conserved; state is free to change. ``Na(state="*") ->
    Na + photon`` is a legal morphism, and the energy difference is the oracle's business,
    not the category's.
    """
    atoms: tuple[str, ...]
    bonds: frozenset[Bond] = frozenset()
    charge: int = 0
    state: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.atoms, tuple):
            raise TypeError("atoms must be a tuple of component labels")
        if not isinstance(self.bonds, frozenset) or any(
            not isinstance(bond, Bond) for bond in self.bonds
        ):
            raise TypeError("bonds must be a frozenset of Bond values")
        if type(self.charge) is not int:
            raise TypeError("molecular charge must be an integer number of elementary charges")
        if not isinstance(self.state, str):
            raise TypeError("molecular state must be a string label")
        if any(not isinstance(symbol, str) or not symbol for symbol in self.atoms):
            raise ValueError("atom/component labels must be non-empty strings")
        n = len(self.atoms)
        endpoints: set[tuple[int, int]] = set()
        for b in self.bonds:
            if not (0 <= b.i < n and 0 <= b.j < n):
                raise ValueError(f"bond {b} refers outside atoms {self.atoms}")
            pair = (b.i, b.j)
            if pair in endpoints:
                raise ValueError(
                    f"multiple bond records for atom pair {pair}; encode multiplicity "
                    "with one Bond.order value"
                )
            endpoints.add(pair)
        if n > 1 and not self.is_connected():
            raise ValueError(
                "a Molecule must be one connected species; represent disconnected "
                "components as separate Molecule values inside a Config"
            )

    # -- construction ------------------------------------------------------------
    @classmethod
    def atom(cls, symbol: str, charge: int = 0, state: str = "") -> "Molecule":
        """A lone unbonded atom."""
        return cls((symbol,), frozenset(), charge, state)

    @classmethod
    def carrier(cls, label: str = "", charge: int = 0) -> "Molecule":
        """
        An object with no atom inventory, whose conserved content is charge alone.

        Empty ``atoms`` is deliberate and already legal -- it contributes nothing to
        ``formula``, so a carrier appearing on one side only still conserves composition,
        while ``charge`` is tracked exactly as for any ion.

        **This is how an electron is spelled.** Not ``Molecule.atom("e", charge=-1)``,
        which is what #22 shipped as the circuit idiom and which is wrong: that puts
        ``"e"`` into ``formula``, so an electron becomes matter, and an electrode
        half-reaction

            Zn + 2 OH- -> ZnO + H2O + 2 e-

        is rejected as mass-violating when nothing of the kind has happened. The charge
        ledger already handles it correctly on its own (-2 -> -2); the mass ledger was
        double-counting a quantity it does not own.

        That defect survived #22 because every test written for it had the SAME number of
        carriers on both sides -- a ``3 e- -> 3 e-`` example then mislabeled as a test of
        Kirchhoff's law -- and a balanced count cannot fail this way whatever the spelling.
        It tested inventory syntax, not node-current semantics. The unbalanced case is the
        electrode, which is the entire point of a battery, and it was never tried.
        ``tests/test_domain_neutral.py::TestAnElectrodeIsAMorphism`` is the regression
        test; the lesson is that a conservation claim must be tested where the counts do
        NOT match, or it tests nothing.
        """
        return cls((), frozenset(), charge, label)

    @classmethod
    def quantum(cls, state: str = "") -> "Molecule":
        """
        A zero-atom token for an energy-carrying mode or quantum.

        This is the chargeless case of :meth:`carrier`. It says only that no chemical atom
        inventory is attached to the token; it does not say that every such excitation is
        physically interchangeable or massless. An electron has nonzero rest mass, and a
        phonon is a collective excitation of a material. Frequency, momentum, polarization,
        medium and dispersion therefore belong in a future typed state/port model rather
        than being inferred from this placeholder.
        """
        return cls.carrier(state, charge=0)

    @classmethod
    def diatomic(cls, a: str, b: str, order: int = 1, charge: int = 0) -> "Molecule":
        return cls((a, b), frozenset({Bond(0, 1, order)}), charge).canonical()

    # -- structure ---------------------------------------------------------------
    @property
    def formula(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.atoms:
            counts[s] = counts.get(s, 0) + 1
        return counts

    def degree(self, index: int) -> int:
        """Total bond order at one atom position -- its used valence."""
        return sum(b.order for b in self.bonds if index in (b.i, b.j))

    def is_connected(self) -> bool:
        """True if the bond graph is connected (a single species, not a mixture)."""
        n = len(self.atoms)
        if n <= 1:
            return True
        adj: dict[int, set[int]] = {i: set() for i in range(n)}
        for b in self.bonds:
            adj[b.i].add(b.j)
            adj[b.j].add(b.i)
        seen = {0}
        stack = [0]
        while stack:
            cur = stack.pop()
            for nxt in adj[cur] - seen:
                seen.add(nxt)
                stack.append(nxt)
        return len(seen) == n

    @work_transparent_cache(maxsize=8192)
    def canonical(self) -> "Molecule":
        """
        Canonical relabelling, so structurally identical molecules compare equal.

        Results are cached by the complete immutable molecule value. This matters because
        every ``Config`` construction canonicalises its members; repeated pathway states
        should not repay the permutation search for a species already seen in this process.

        **Canonicalisation is verification work (0.9.5 S16).** Its WORK, defined once: the
        candidate permutations evaluated on the block path (``_cost_of(blocks)``, which is 1 for
        a molecule of at most one atom), or on the individualisation path the atoms refined:
        every search node re-refines the whole graph, so each costs the molecule's atom count
        (a node count alone let a large, repetitive input grind cheaply). It is charged to the
        active verification context through
        :func:`~smartchem.verification.charge_canonical_work` BEFORE the work it bounds (the
        block path in one charge ahead of the loop, the search one node at a time), and the
        cache is work-transparent: an entry keeps the work its computation charged and every
        hit re-charges it -- so a load pays the same whatever this process has already seen.

        Minimises the key ``(symbols, edges)`` over the candidate permutations, then
        rebuilds the molecule from the winner.

        For molecules the symbol restriction alone cannot afford, the key becomes
        ``(symbols, colours, edges)`` and the candidate set shrinks accordingly -- see
        ``_canonical_blocks``. Those are exactly the molecules that used to raise, so no
        canonical form computed before that change moved.

        For molecules refinement *still* cannot afford (a vertex-transitive cell it cannot
        split -- benzene, symmetric rings), it falls through to individualisation, nauty's
        second move (#25, ``_canonical_by_individualisation``): a relabel-invariant canonical
        form, proven sound and invariant by brute force. Still purely additive -- only
        molecules that used to raise reach it -- and it refuses loudly above a leaf ceiling
        for the fully-symmetric non-molecule (a complete graph) rather than returning a wrong
        form.

        Only ``edges`` is compared in the loop below. The other two components are what
        *define* the candidate set -- every candidate realises the same sorted ``symbols``
        and the same sorted ``colours``, so they are constant here and cannot break a tie.
        They are hoisted, not dropped; ``test_every_candidate_realises_the_same_prefix``
        is what holds that claim down.
        """
        n = len(self.atoms)
        if n <= 1:
            charge_canonical_work(1)               # the one (identity) candidate; nothing to search
            return self
        blocks = _canonical_blocks(self.atoms, self.bonds)
        budget = _cost_of(blocks)
        if budget > _MAX_CANONICAL_CANDIDATES:
            # refinement alone cannot afford this graph (a vertex-transitive cell it cannot
            # split): fall through to individualisation, nauty's second move (#25). Purely
            # additive -- only molecules that USED to raise here reach this branch. Charged per
            # search node, before each node's refinement; the cache records the total.
            symbols, best = _canonical_by_individualisation(
                self.atoms, self.bonds, on_node=lambda: charge_canonical_work(n)
            )
            return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in best),
                            self.charge, self.state)
        charge_canonical_work(budget)              # every candidate below, paid for up front
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

    def __repr__(self) -> str:
        """
        A text form that is never empty, because "" is indistinguishable from absence.

        Exactly one species has no atoms, no charge and no state -- the bare
        ``Molecule.quantum()`` -- and it used to render as the empty string. That is not a
        cosmetic wart. Every renderer in this package joins species reprs with separators
        and then decides emptiness from the joined text, so a species that renders as
        nothing DISAPPEARS from the statement it is part of, and the statement stays
        fluent: ``Config((quantum,))`` printed as ``""``, ``Reaction`` printed as
        ``" -> "``, and the stoichiometry menu printed the balance ``quantum -> Na`` as
        ``(nothing) -> Na`` -- a module whose whole subject is conservation, announcing
        that matter came from nowhere.

        The token is ``quantum``, lower-case and unbracketed, and both of those are load
        bearing. A formula is a concatenation of element symbols and every element symbol
        is capitalised, so a lower-case token can never be mistaken for one; a state
        renders as ``(state)``, so an unbracketed token can never be mistaken for one
        either. ``Molecule.quantum("quantum")`` therefore still renders distinctly, as
        ``(quantum)``. It is deliberately not ``photon`` or ``hv``: this method's
        counterpart :meth:`quantum` is explicit that a zero-atom token is "an
        energy-carrying mode or quantum" and need not be radiation at all.
        """
        counts = self.formula
        body = "".join(
            f"{s}{counts[s] if counts[s] > 1 else ''}" for s in sorted(counts)
        )
        if self.charge > 0:
            body += f"^{self.charge}+"
        elif self.charge < 0:
            body += f"^{abs(self.charge)}-"
        if self.state:
            body += f"({self.state})"
        return body or "quantum"


# ======================================================================================
# Objects of the category
# ======================================================================================
@dataclass(frozen=True)
class Config:
    """
    An object of the category: a multiset of coexisting molecules.

    This is the contents of the vessel. ``Na + Cl`` (two species) and ``NaCl`` (one
    species) have the same ``formula`` but are different objects -- which is precisely
    what lets a reaction between them be a non-identity morphism.
    """
    species: tuple[Molecule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.species, tuple) or any(
            not isinstance(molecule, Molecule) for molecule in self.species
        ):
            raise TypeError("species must be a tuple of Molecule values")
        # canonical: each molecule canonicalised, then the multiset sorted deterministically
        # `state` belongs in this key even though it is not conserved. Without it two
        # species differing only in state tie, the sort is stable, and the canonical
        # tuple would then depend on the order they were passed in -- making
        # `Config.of(a, b) != Config.of(b, a)`. Silent, and fatal to every equality above.
        canon = tuple(sorted(
            (m.canonical() for m in self.species),
            key=lambda m: (tuple(sorted(m.formula.items())), m.charge,
                           sorted(m.bonds), m.state),
        ))
        object.__setattr__(self, "species", canon)

    # -- construction ------------------------------------------------------------
    @classmethod
    def of(cls, *molecules: Molecule) -> "Config":
        return cls(tuple(molecules))

    @classmethod
    def atoms(cls, *symbols: str) -> "Config":
        """A configuration of lone unbonded atoms -- the usual reactant side."""
        return cls(tuple(Molecule.atom(s) for s in symbols))

    # -- the conserved quantity --------------------------------------------------
    @property
    def formula(self) -> dict[str, int]:
        """Total atom counts across all species. Invariant under any valid reaction."""
        counts: dict[str, int] = {}
        for m in self.species:
            for s, k in m.formula.items():
                counts[s] = counts.get(s, 0) + k
        return counts

    @property
    def charge(self) -> int:
        """Total charge. Also invariant."""
        return sum(m.charge for m in self.species)

    @property
    def signature(self) -> tuple:
        """The full conserved signature: atoms and charge together."""
        return (tuple(sorted(self.formula.items())), self.charge)

    def atom_count(self) -> int:
        return sum(self.formula.values())

    def __len__(self) -> int:
        return len(self.species)

    def __repr__(self) -> str:
        return " + ".join(repr(m) for m in self.species) if self.species else "I"


#: Unit of the commutative object product: the empty formal configuration.
UNIT = Config(())


def tensor_obj(a: Config, b: Config) -> Config:
    """Commutative multiset union of configurations.

    This is a formal object product. It does not assert physical co-location, interaction,
    spatial separation or a parallel product on reaction morphisms.
    """
    return Config(a.species + b.species)


# ======================================================================================
# Morphisms
# ======================================================================================
@dataclass(frozen=True)
class Reaction:
    """
    A morphism ``dom -> cod``.

    The constructor is where conservation is enforced. There is no way to build a
    ``Reaction`` that creates or destroys matter or charge, so no downstream code has to
    remember to check -- and no composite of valid reactions can violate it either.

    Why ``path`` exists
    -------------------
    A morphism is not determined by its endpoints alone. Two mechanisms can carry the
    same overall species from A to C through different intermediates, and collapsing
    them would throw away exactly the information mechanism search needs.

    So a reaction records the sequence of elementary steps it traverses:

    * an elementary reaction has ``path == ((dom, cod),)`` -- one step
    * an identity has ``path == ()`` -- it traverses nothing
    * composition concatenates paths

    That makes the category laws hold for the right reason rather than by accident:
    associativity is associativity of concatenation, and the identity laws hold because
    the empty tuple is the unit of concatenation.

    ``name`` is a human label and is excluded from equality -- two reactions differing
    only in what they are called are the same morphism.
    """
    dom: Config
    cod: Config
    name: str = field(default="", compare=False)
    path: tuple[tuple[Config, Config], ...] | None = None
    generator_id: str | None = field(default=None, compare=False, kw_only=True)
    generator_word: tuple[tuple[Config, Config, str], ...] | None = field(
        default=None, kw_only=True, repr=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.dom, Config) or not isinstance(self.cod, Config):
            raise TypeError("reaction domain and codomain must be Config values")
        if not isinstance(self.name, str):
            raise TypeError("reaction name must be a string")
        if self.path is None:
            # A constructor call denotes an elementary event even when its endpoints
            # coincide.  Endomorphisms are not identities merely because their net state
            # change is zero (a catalytic cycle and an AC period are obvious examples).
            # ``identity`` passes path=() explicitly.
            object.__setattr__(self, "path", ((self.dom, self.cod),))
        elif not isinstance(self.path, tuple):
            raise TypeError("reaction path must be a tuple of typed transitions")
        if any(not isinstance(step, tuple) or len(step) != 2 for step in (self.path or ())):
            raise TypeError("each reaction path entry must be a (Config, Config) tuple")
        if self.generator_id is not None and (
            not isinstance(self.generator_id, str)
            or not self.generator_id
            or "\x00" in self.generator_id
        ):
            raise ValueError(
                "generator_id must be a non-empty stable string without NUL characters"
            )
        if self.generator_word is None:
            path = self.path or ()
            if self.generator_id is not None and len(path) != 1:
                raise ValueError("generator_id can only label one elementary transition")
            object.__setattr__(
                self,
                "generator_word",
                tuple(
                    (source, target, self.generator_id or "")
                    for source, target in path
                ),
            )
        elif not isinstance(self.generator_word, tuple):
            raise TypeError("generator_word must be a tuple of typed generator keys")
        if any(
            not isinstance(key, tuple) or len(key) != 3
            for key in (self.generator_word or ())
        ):
            raise TypeError(
                "each generator key must be a (source, target, stable_id) tuple"
            )
        if self.generator_id is not None:
            word = self.generator_word or ()
            if len(word) != 1 or word[0][2] != self.generator_id:
                raise ValueError(
                    "generator_id must match the sole identity in generator_word"
                )
        if self.dom.formula != self.cod.formula:
            raise ConservationError(
                f"mass not conserved: {self.dom} -> {self.cod}; "
                f"{self.dom.formula} != {self.cod.formula}"
            )
        if self.dom.charge != self.cod.charge:
            raise ConservationError(
                f"charge not conserved: {self.dom} -> {self.cod}; "
                f"{self.dom.charge:+d} != {self.cod.charge:+d}"
            )
        self._validate_path()

    def _validate_path(self) -> None:
        """Reject forged or discontinuous histories before they become certificates."""
        path = self.path or ()
        word = self.generator_word or ()
        if len(word) != len(path):
            raise CompositionError(
                "generator_word must contain exactly one typed key per path transition"
            )
        if not path:
            if self.dom != self.cod:
                raise CompositionError(
                    "only an identity may have an empty path; non-identity endpoints "
                    "need at least one transition"
                )
            return

        cursor = self.dom
        for index, (source, target) in enumerate(path):
            if source != cursor:
                raise CompositionError(
                    f"path step {index} starts at {source}, expected {cursor}"
                )
            if source.formula != target.formula or source.charge != target.charge:
                raise ConservationError(
                    f"path step {index} violates conservation: {source} -> {target}"
                )
            word_source, word_target, stable_id = word[index]
            if (word_source, word_target) != (source, target):
                raise CompositionError(
                    f"generator key {index} is typed for {word_source} -> {word_target}, "
                    f"not path transition {source} -> {target}"
                )
            if not isinstance(stable_id, str):
                raise TypeError("generator identities must be stable strings")
            cursor = target
        if cursor != self.cod:
            raise CompositionError(
                f"path ends at {cursor}, but the declared codomain is {self.cod}"
            )

    def then(self, other: "Reaction") -> "Reaction":
        """
        Sequential composition ``other . self``, written left-to-right.

        Defined only when ``self.cod == other.dom``. Conservation of the result is
        automatic: it follows from transitivity, not from a re-check.
        """
        if self.cod != other.dom:
            raise CompositionError(
                f"cannot compose {self.dom} -> {self.cod} with "
                f"{other.dom} -> {other.cod}: codomain != domain"
            )
        label = " ; ".join(name for name in (self.name, other.name) if name)
        return Reaction(
            self.dom, other.cod, label,
            path=(self.path or ()) + (other.path or ()),
            generator_word=(self.generator_word or ()) + (other.generator_word or ()),
        )

    def scheduled_product(self, other: "Reaction") -> "Reaction":
        """
        Put two histories alongside one another without erasing either history.

        The current representation is a linear trace of whole-configuration states, so
        independent events need a deterministic linearisation.  ``self`` is traversed
        first while ``other.dom`` is held fixed, then ``other`` while ``self.cod`` is held
        fixed.  This preserves certificates and the unit operation, but it deliberately
        does *not* pretend that a linear trace implements the interchange quotient of a
        free symmetric monoidal category.  That requires explicit ports/wires (an open
        process graph), not another tuple convention.

        That open process graph is :class:`smartchem.open_chem_diagram.OpenChemDiagram`, where the interchange
        law DOES hold under ``canonicalize`` (``test_open_chem_diagram`` GATE 1).  This method is NOT the image of a
        projection from that layer -- there is no such map: a genuinely parallel history has no single linearisation,
        so ``OpenChemDiagram.close`` is PARTIAL and refuses exactly the parallel diagrams a ``.tensor`` builds.
        ``scheduled_product`` is instead an INDEPENDENT deterministic left-then-right schedule of the same
        generators that the backbone declines to linearise; the debt is representational, not open: nothing here is
        an SMC tensor, and no caller relies on it being one.
        ``test_laws.test_true_parallel_interchange_lives_on_the_open_diagram_backbone`` pins both halves (this trace
        loses interchange; the backbone recovers it).
        """
        label = " (x) ".join(name for name in (self.name, other.name) if name)
        path: list[tuple[Config, Config]] = []
        word: list[tuple[Config, Config, str]] = []
        for index, (source, target) in enumerate(self.path or ()):
            padded_source = tensor_obj(source, other.dom)
            padded_target = tensor_obj(target, other.dom)
            path.append((padded_source, padded_target))
            stable_id = (self.generator_word or ())[index][2]
            word.append((padded_source, padded_target, stable_id))
        for index, (source, target) in enumerate(other.path or ()):
            padded_source = tensor_obj(self.cod, source)
            padded_target = tensor_obj(self.cod, target)
            path.append((padded_source, padded_target))
            stable_id = (other.generator_word or ())[index][2]
            word.append((padded_source, padded_target, stable_id))
        return Reaction(
            tensor_obj(self.dom, other.dom),
            tensor_obj(self.cod, other.cod),
            label,
            path=tuple(path),
            generator_word=tuple(word),
        )

    def tensor(self, other: "Reaction") -> "Reaction":
        """
        Compatibility alias for :meth:`scheduled_product`.

        This operation serializes the left history before the right history. It is not a
        parallel categorical tensor and does not satisfy interchange; use it only when that
        explicit scheduling convention is intended.
        """
        __import__("warnings").warn(
            "Reaction.tensor is deprecated because it is a left-first schedule, not a "
            "parallel tensor; call scheduled_product() explicitly",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.scheduled_product(other)

    @property
    def steps(self) -> int:
        """How many elementary steps this morphism traverses. 0 for an identity."""
        return len(self.path or ())

    def __repr__(self) -> str:
        tag = f" [{self.name}]" if self.name else ""
        return f"{self.dom} -> {self.cod}{tag}"


def identity(obj: Config) -> Reaction:
    """``id_A : A -> A``. Trivially conserving, and traverses no steps."""
    return Reaction(obj, obj, "id", path=())


def braid(a: Config, b: Config) -> Reaction:
    """
    Object-level exchange ``A (+) B -> B (+) A``.

    Because ``Config`` canonicalises its species multiset, ``A (x) B`` and ``B (x) A``
    are already the *same object*, so this is an identity. That is the honest outcome:
    the object product is commutative on the nose. This does not make the scheduled
    morphism product symmetric or natural; interchange remains explicit architecture debt.
    """
    return Reaction(tensor_obj(a, b), tensor_obj(b, a), "braid", path=())


# ======================================================================================
# Structural properties, decided rather than asserted
# ======================================================================================
def is_regenerated(reaction: Reaction, species: Molecule) -> bool:
    """
    Decide whether ``species`` has the same positive multiplicity at both endpoints.

    This is a structural stoichiometric predicate only. An inert spectator passes it, so
    it is not evidence of catalysis, rate enhancement, participation in a mechanism, or
    kinetic accessibility.
    """
    c = species.canonical()
    return (
        reaction.dom.species.count(c) > 0
        and reaction.dom.species.count(c) == reaction.cod.species.count(c)
    )


def is_catalytic(reaction: Reaction, catalyst: Molecule) -> bool:
    """Compatibility alias for :func:`is_regenerated`; it does not prove catalysis."""
    return is_regenerated(reaction, catalyst)


def reaction_residue(reaction: Reaction) -> tuple[Config, Config]:
    """
    Strip the spectators: return ``(dom', cod')`` with the common sub-multiset removed.

    This is the structural half of an exact shortcut *inside the current separable,
    isolated-species energy model*. Under ``E(S + X) = E(S) + E(X)``, the shared part
    cancels identically::

        dE(f) = (E(S) + E(B)) - (E(S) + E(A)) = E(B) - E(A)

    ``E(S)`` therefore cannot influence the answer and does not need to be computed under
    that adapter. The multiset structure identifies the common spelling before any oracle
    call; the separability assumption, not category theory alone, licenses cancellation.

    Two things follow, and the second matters more than the first:

    1. **Cost.** A spectator is never priced. A nominated catalyst is often the largest
       regenerated species present, so this can be the difference between paying for the
       whole separable inventory and paying only for the species that change.

    2. **Consistent reuse of one modeled quantity.** Quadrature is valid only for
       independent terms. A spectator's energy is not two independent samples -- it is
       one number, appearing twice, minus itself. Summing both sides first and subtracting
       afterwards invents ``2 * u(S)^2`` under that independence model. Removing the
       shared species preserves exact self-correlation. The remaining scalar scale is not
       automatically a calibrated coverage interval.

    It is not a universal statement about spectators in one interacting vessel. Binding,
    solvent reorganisation, electrostatics and long-range fields can make the interaction
    energy context-dependent even when the spectator's spelling is unchanged.

    An identity morphism has empty residue on both sides, giving ``dE = 0`` exactly.
    """
    left = Counter(reaction.dom.species)
    right = Counter(reaction.cod.species)
    shared = left & right               # multiset intersection: the spectators
    return (
        Config(tuple((left - shared).elements())),
        Config(tuple((right - shared).elements())),
    )


def bond_signature(config: Config) -> Counter:
    """
    The multiset of bond *types* in a configuration: ``{(("H", "Cl"), 1): 2, ...}``.

    A bond type is its two element symbols (sorted, so it is undirected) together with its
    order. This is coarser than the topology -- it forgets which atom is which -- and that
    coarseness is the point: it is the granularity at which method error is roughly
    transferable between molecules.
    """
    sig: Counter = Counter()
    for molecule in config.species:
        for b in molecule.bonds:
            pair = tuple(sorted((molecule.atoms[b.i], molecule.atoms[b.j])))
            sig[(pair, b.order)] += 1
    return sig


def bond_order_profile(config: Config) -> Counter:
    """
    The multiset of bond *orders* in a configuration, forgetting which elements they join:
    ``{1: 2, 3: 1}`` for two single bonds and one triple.

    Coarser than ``bond_signature``, and the coarseness is deliberate. It is the level at
    which "one single bond was broken and one single bond was made" is a statement about
    the morphism, regardless of whether the partners changed.
    """
    profile: Counter = Counter()
    for molecule in config.species:
        for b in molecule.bonds:
            profile[b.order] += 1
    return profile


def is_bond_order_conserving(reaction: Reaction) -> bool:
    """
    Decide whether ``reaction`` preserves the multiset of bond orders -- the same number of
    single bonds, double bonds and so on, though the partners may swap.

    ``HCl + F -> HF + Cl`` satisfies this: one single bond in, one single bond out.
    ``2 H -> H2`` does not: it makes a bond out of nothing.

    Decided from structure alone, with no oracle call, because the objects carry bond
    topology. This is the predicate the measurement below actually tested.

    Why it is worth deciding: a correlated method's error is approximately a property of
    the bonds present, so in a morphism whose bond content is unchanged the errors appear
    on both sides and partly cancel in ``dE`` -- the same shape of argument as the
    arbitrary energy zero, but *approximate* where that one is exact.

    MEASURED, and the pre-registered prediction was wrong. Over 5 bond-creating and 4
    bond-order-conserving diatomic reactions scored against experimental D0:

    ==================  ================  =====================  =====
    tier                bond-creating     bond-order-conserving  ratio
    ==================  ================  =====================  =====
    HF/cc-pVTZ          1.8847 eV         0.7475 eV              2.52
    CCSD(T)/cc-pVTZ     0.1265 eV         0.0592 eV              2.14
    ==================  ================  =====================  =====

    The prediction was a ratio above 3. It is not met at either tier. The effect is real,
    consistent in sign and size across two tiers differing ~15x in absolute error, and
    worth about a factor of two -- not the larger effect claimed in advance.

    So this function DECIDES the property and reports it. It deliberately does not select
    a cheaper tier on its own. Nine diatomic reactions in one basis family do not license
    an automatic accuracy policy, and the last policy proposed here on that kind of
    evidence -- basis augmentation -- lost outright when finally measured at the tier that
    mattered. Candidate generation does not upgrade proof status.

    See ``THE_DIFFERENCE.md`` section 5 and ``tests/test_shortcuts.py``.
    """
    return bond_order_profile(reaction.dom) == bond_order_profile(reaction.cod)


def is_isodesmic(reaction: Reaction) -> bool:
    """
    Decide whether ``reaction`` preserves the multiset of bond *types* -- element pair and
    order both. Strictly stronger than ``is_bond_order_conserving``.

    ``HCl + F -> HF + Cl`` is bond-order conserving but NOT isodesmic, because ``H-Cl``
    became ``H-F``. Chemistry expects the stronger property to cancel error better still,
    since the bonds on each side are then genuinely the same kind of object.

    MEASURED, AND THE MEASUREMENT CANNOT DECIDE. The honest verdict is UNDECIDED, not a
    number, and the reason is worth more than a number would have been.

    Prediction P4, registered before the run: isodesmic < order-conserving < creating in
    mean absolute error against experiment. Over 82 mass-balanced reactions among 14
    species, scored against experimental enthalpies of formation at 0 K:

    ==============  ===  ==========  ==========  ==========
    class             n  absolute    relative    per bond
    ==============  ===  ==========  ==========  ==========
    isodesmic         7  0.1818 eV   0.33        0.0191 eV
    order-conserving 47  0.1101 eV   0.19        0.0111 eV
    creating         28  0.2858 eV   0.57        0.0339 eV
    ==============  ===  ==========  ==========  ==========

    Read naively that refutes P4 on all three statistics at once: isodesmic looks 1.65x
    WORSE than merely order-conserving. It does not refute it, because the comparison is
    confounded, and the confound was introduced by the fix for an earlier problem.

    Over the nine species originally referenced, exactly ONE strictly isodesmic reaction
    exists. Fixing that meant adding species, and over this element set the only species
    that unlock isodesmic reactions carry C=O. So 5 of 7 isodesmic reactions contain a
    carbonyl against 3 of 47 order-conserving ones -- "isodesmic" and "contains C=O" are
    very nearly the same variable in this sample. That matters because HF omits electron
    correlation and correlation energy is largest for multiple bonds, so a C=O species is
    exactly what this tier handles worst. Stratifying:

    ==================  =======================  ==========================
    stratum             isodesmic                order-conserving
    ==================  =======================  ==========================
    no C=O species      0.0701 eV  (n=2)         0.1040 eV  (n=44)
    contains C=O        0.2264 eV  (n=5)         0.2003 eV  (n=3)
    ==================  =======================  ==========================

    The sign flips between strata and the pooled figure agrees with neither -- Simpson's
    paradox, driven by a composition imbalance this project created for itself. n=2 in the
    clean stratum decides nothing, and the largest single isodesmic error and the smallest
    are BOTH carbonyl reactions, so it is not a tidy species effect either.

    One confound was predicted in advance and turned out to be null: reactions containing
    H2 get an experimental zero-point energy rather than a computed one, and H2 appears in
    21 of 47 order-conserving reactions and none of the isodesmic ones. It is worth
    nothing -- 0.1111 eV with H2 against 0.1101 eV overall.

    So this function DECIDES the property and reports it, and quotes no accuracy claim. To
    settle P4 the isodesmic class needs members without carbonyls, which over these
    elements means larger alkanes and alcohols; propane is the smallest and is currently
    beyond ``_MAX_CANONICAL_CANDIDATES``. The blocker is therefore the canonical key, not
    the oracle -- a dependency that is now demonstrated rather than assumed.

    See ``tests/test_shortcuts.py::TestTheIsodesmicMeasurementIsConfounded``.
    """
    return bond_signature(reaction.dom) == bond_signature(reaction.cod)


def catalytic_cycle(steps: Iterable[Reaction], catalyst: Molecule) -> Reaction | None:
    """
    Compatibility name: compose ``steps`` and require stoichiometric regeneration.

    Returns None if the steps do not compose (a real gap in the mechanism) or if the
    nominated species is not regenerated. Returning the composed morphism rather than a bare
    ``True`` lets the caller re-check that structural fact. It does not establish catalysis:
    an inert spectator passes, and no rate enhancement or mechanistic participation is tested.
    """
    steps = list(steps)
    if not steps:
        return None
    composite = steps[0]
    for nxt in steps[1:]:
        try:
            composite = composite.then(nxt)
        except CompositionError:
            return None
    return composite if is_regenerated(composite, catalyst) else None


def conserves(reaction: Reaction) -> bool:
    """
    Re-verify conservation independently of the constructor.

    Always True for any ``Reaction`` that exists, by construction. Kept as a separate
    predicate so the property tests can assert it over hypothesis-generated composition
    chains without relying on the same code path that enforced it.
    """
    return (
        reaction.dom.formula == reaction.cod.formula
        and reaction.dom.charge == reaction.cod.charge
    )


def formula_of(counts: Mapping[str, int], charge: int = 0) -> tuple:
    """Build the conserved signature directly, for comparison in tests."""
    return (tuple(sorted(counts.items())), charge)
