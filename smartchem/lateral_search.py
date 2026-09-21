"""Bounded lateral-isomerization search -- the SOUND core of the deferred lateral-search epic.

The [3,3]/electrocyclization seam (:mod:`smartchem.lateral_rewrite`) built the rank-FLAT rewrite machinery and proved,
end-to-end, WHY a lateral edge cannot enter the strict-descent route search: ``search_routes`` recurses only onto a
``precursor`` drawn from ``transform.products`` and its termination rests on invariant W1 -- *every product has
strictly smaller* ``Formula.rank`` *(= atom count)*.  An isomerization preserves atom count, so it is rank-flat, so
W1 is unsatisfiable for it; forcing one through the decompiler/conditions path calls ``forget()``, which a
:class:`~smartchem.lateral_rewrite.LateralRewriteEdge` refuses by design (fail-loud).  That block is a structure
theorem, not a bug: a rank-flat edge inside the descent recursion collapses the well-ordering (the ancestor guard
blocks only exact revisits ALONG ONE PATH, never isomerization cycles across the whole frontier), so the search
would no longer terminate.

THIS MODULE is the other half: a lateral search that terminates on its OWN measure, entirely OUTSIDE the descent.
It is a bounded breadth-first closure over MOLECULE isomer states -- the exact discipline of the kernel's
:func:`~smartchem.rule_calculus.bounded_closure` (which tolerates state-preserving cycles precisely because it
carries its own visited-set + budgets rather than relying on a descent measure), lifted from ``BondGraph`` to
``Molecule`` and keyed by canonical constitutional identity (:func:`~smartchem.smiles.resonance_identity` -- the same
key the route search itself already uses to dedup states).

TERMINATION (the load-bearing soundness).  Let ``V`` be the set of canonical identities admitted.  Each identity is
inserted into ``depth_of`` at most once and expanded at most once (the ``if pid in depth_of`` guard); the BFS never
re-expands a visited state, so no isomerization cycle A->B->A can loop.  Expansion stops at ``depth`` (a finite BFS
distance cap) and admission stops at ``state_budget`` (a finite cap on ``|V|``), so the frontier is exhausted in a
finite number of steps regardless of how many isomers the families could in principle reach.  This closure NEVER
calls ``forget()``, NEVER registers a :class:`~smartchem.transform_provider.TransformProvider`, and NEVER re-enters
``routes_making`` -- so the W1 termination guarantee of ``search_routes`` is untouched, and this search's termination
is independent of (and does not borrow) strict rank descent.

SOUND CONSUMER.  :func:`lateral_route_to` reconstructs an explicit hand-assembled route -- an ordered tuple of
guarded :class:`~smartchem.lateral_rewrite.LateralRewriteEdge` steps from a seed to a goal isomer -- which the
reaction-type oracle VOUCHES step by step (each edge is a structurally valid lateral rewrite) instead of demoting as
unrecognized.  Structural type-validity ONLY (Problem A): reachability here means "a chain of structurally valid
lateral isomerizations connects these constitutions", NEVER that the chain is feasible, thermally allowed, or
kinetically accessible.  What stays DEFERRED (still the epic): auto-discovery that FUSES lateral hops into the
rank-descent ``search_routes`` recursion (unsound -- see the structure theorem above); this module keeps the two
searches strictly separate, which is exactly what makes it sound.
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Config, Molecule
from .lateral_rewrite import LATERAL_FAMILIES, LateralRewriteEdge, _SigmatropicFamily, guarded_isomer_edges
from .smiles import resonance_identity

#: Closure status: fully explored to the depth cap without truncation.
COMPLETE_TO_DEPTH = "COMPLETE_TO_DEPTH"
#: Closure status: the distinct-state cap ``state_budget`` was hit (combinatorial isomer blow-up) -- INCOMPLETE.
INCOMPLETE_STATE_BUDGET = "INCOMPLETE_STATE_BUDGET"
#: Closure status: a single node's kernel match enumeration was truncated by ``match_budget`` -- INCOMPLETE.
INCOMPLETE_MATCH_BUDGET = "INCOMPLETE_MATCH_BUDGET"


@dataclass(frozen=True)
class LateralClosureReceipt:
    """The result of a bounded lateral closure: the reachable isomer set, the transition edges, and an HONEST status.

    ``complete`` is ``True`` only for :data:`COMPLETE_TO_DEPTH` -- a state- or match-budget truncation leaves the
    closure INCOMPLETE (fail-closed: a truncated closure never claims it found every reachable isomer)."""

    seed: Molecule
    isomers: tuple[Molecule, ...]              # every distinct isomer reached (incl. the seed), canonical order
    edges: tuple[LateralRewriteEdge, ...]      # the guarded lateral transitions discovered (the isomerization graph)
    depth_of: dict[str, int]                   # resonance_identity -> BFS depth at which it was first reached
    status: str

    @property
    def complete(self) -> bool:
        """``True`` iff the closure was explored to the depth cap with NO budget truncation."""
        return self.status == COMPLETE_TO_DEPTH

    def reaches(self, molecule: Molecule) -> bool:
        """Whether ``molecule`` (by canonical identity) is in the reached isomer set."""
        return resonance_identity(molecule) in self.depth_of


def _ordered(by_id: dict[str, Molecule]) -> tuple[Molecule, ...]:
    """The reached isomers in a deterministic canonical order (by their identity key)."""
    return tuple(by_id[k] for k in sorted(by_id))


def lateral_closure(seed: Molecule, families: tuple[_SigmatropicFamily, ...] = LATERAL_FAMILIES, *,
                    depth: int = 4, state_budget: int = 1000, match_budget: int = 100000) -> LateralClosureReceipt:
    """The bounded lateral-isomerization closure of ``seed`` under ``families`` -- the distinct isomers reachable by
    a chain of at most ``depth`` guarded lateral rewrites, with the transition edges, terminating on its OWN
    visited-set + budgets (see the module docstring's termination proof).  NEVER touches the strict-descent route
    search: no provider, no ``forget()``, no recursion into ``routes_making``.

    COVERAGE (honest, per dalembert's boundary): a guarded lateral rewrite is DIRECTIONAL -- the enumerator applies
    each family's ``retro``, which matches its product-isomer form (a Claisen fires on the carbonyl, an
    electrocyclization on the RING), so the closure reaches, e.g., the open polyene FROM a ring but not the ring from
    an open polyene.  ``COMPLETE_TO_DEPTH`` therefore means "complete over the guarded rewrites' matched directions",
    an honest coverage floor (under-reporting), NEVER a false reach: a reported isomer is always genuinely reachable."""
    if type(seed) is not Molecule:
        raise TypeError("lateral_closure expects a Molecule seed")
    if depth < 0 or state_budget < 1:
        raise ValueError("depth must be >= 0 and state_budget >= 1")
    seed_id = resonance_identity(seed)
    depth_of: dict[str, int] = {seed_id: 0}
    reached: dict[str, Molecule] = {seed_id: seed}
    edges: list[LateralRewriteEdge] = []
    status = COMPLETE_TO_DEPTH
    frontier: list[tuple[Molecule, int]] = [(seed, 0)]
    while frontier:
        nxt: list[tuple[Molecule, int]] = []
        for mol, d in frontier:
            if d >= depth:
                continue
            for family in families:
                fam_edges, fam_complete = guarded_isomer_edges(family, mol, budget=match_budget)
                if not fam_complete:
                    status = INCOMPLETE_MATCH_BUDGET
                for edge in fam_edges:
                    product = edge.products[0]
                    pid = resonance_identity(product)
                    edges.append(edge)
                    if pid in depth_of:
                        continue  # already seen -- the visited-set that makes isomerization cycles terminate
                    if len(reached) >= state_budget:
                        return LateralClosureReceipt(seed, _ordered(reached), tuple(edges), depth_of,
                                                     INCOMPLETE_STATE_BUDGET)
                    depth_of[pid] = d + 1
                    reached[pid] = product
                    nxt.append((product, d + 1))
        frontier = nxt
    return LateralClosureReceipt(seed, _ordered(reached), tuple(edges), depth_of, status)


def lateral_route_to(seed: Molecule, goal: Molecule,
                     families: tuple[_SigmatropicFamily, ...] = LATERAL_FAMILIES, *,
                     depth: int = 4, state_budget: int = 1000,
                     match_budget: int = 100000) -> tuple[LateralRewriteEdge, ...] | None:
    """A shortest hand-assembled lateral route (ordered guarded :class:`LateralRewriteEdge` steps) from ``seed`` to
    ``goal`` within the bounded closure, or ``None`` if ``goal`` is not reached within ``depth``/budget.  The sound
    reachable CONSUMER the seam promised: the returned chain is vouched step by step by the reaction-type oracle
    (each step a structurally valid lateral rewrite), assembled OUTSIDE the strict-descent search.  Structural
    type-validity only -- reachability is not feasibility."""
    if type(seed) is not Molecule or type(goal) is not Molecule:
        raise TypeError("lateral_route_to expects Molecule seed and goal")
    goal_id = resonance_identity(goal)
    seed_id = resonance_identity(seed)
    if goal_id == seed_id:
        return ()  # already there -- the empty route (a degenerate but honest answer)
    goal_config = Config.of(goal)   # exact constitution, to bind reachability to identity (not just the digest)
    # BFS recording, per identity, the single edge that first reached it (predecessor pointers for reconstruction).
    predecessor: dict[str, LateralRewriteEdge] = {}
    depth_of: dict[str, int] = {seed_id: 0}
    reached_count = 1
    frontier: list[tuple[Molecule, int]] = [(seed, 0)]
    while frontier:
        nxt: list[tuple[Molecule, int]] = []
        for mol, d in frontier:
            if d >= depth:
                continue
            for family in families:
                fam_edges, _ = guarded_isomer_edges(family, mol, budget=match_budget)
                for edge in fam_edges:
                    pid = resonance_identity(edge.products[0])
                    if pid in depth_of:
                        continue
                    predecessor[pid] = edge
                    # goal reached ONLY when the digest AND the exact constitution match -- the belt-and-suspenders
                    # against a (conjectured-impossible) resonance_identity collision: never claim seed->goal on a
                    # look-alike (fail-closed -- a collision costs coverage, never a false reachability claim).
                    if pid == goal_id and Config.of(edge.products[0]) == goal_config:
                        return _reconstruct(predecessor, seed_id, goal_id)
                    if reached_count >= state_budget:
                        return None  # budget hit before reaching goal -- fail-closed (no partial claim)
                    reached_count += 1
                    depth_of[pid] = d + 1
                    nxt.append((edge.products[0], d + 1))
        frontier = nxt
    return None


def _reconstruct(predecessor: dict[str, LateralRewriteEdge], seed_id: str,
                 goal_id: str) -> tuple[LateralRewriteEdge, ...]:
    """Walk the predecessor edges back from ``goal`` to ``seed`` and return them seed->goal ordered."""
    chain: list[LateralRewriteEdge] = []
    cursor = goal_id
    while cursor != seed_id:
        edge = predecessor[cursor]
        chain.append(edge)
        cursor = resonance_identity(edge.reactant)
    chain.reverse()
    return tuple(chain)
