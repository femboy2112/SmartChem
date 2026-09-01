"""E5 -- enumerate candidate synthesis routes from the decompiler, closing the loop.

E0-E4 *consume* a route; E5 *generates* candidate routes from the decompiler's own conservation-valid
cleavages, so a chemist can hand the compiler a target + an inventory and get back ranked route candidates.

It is a bounded retrosynthesis over :func:`~smartchem.structure_descent.capped_scissions`: to make ``target``,
enumerate its capped cleavages against a declared ``reagents`` pool, read each backward as an assembly step
(``products -> target`` via :meth:`ExperimentStep.from_capped_scission`), attach any SOURCED conditions
(:func:`~smartchem.decompiler_conditions.reaction_conditions`), and -- for a precursor not already on hand --
recurse to make it, up to ``max_depth``.  Structure ENUMERATES the candidates; evidence (composability,
conditions, the constraint box) IDENTIFIES the good ones, exactly the repo's standing doctrine -- so
:func:`~smartchem.experiment.drafter.rank_routes` floats the composable, sourced, in-budget routes to the top
and the degenerate ones to the bottom.

W1 (termination) is inherited: every cleavage yields strictly-smaller precursors, so the backward search
descends and ``max_depth`` bounds it.  Nothing here predicts chemistry -- it enumerates conservation-valid
assemblies and lets the E-rungs judge them.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from enum import Enum

from ..category import Molecule
from ..conditions import ConditionEnvelope
from ..contracts import Digestible, canonical_digest
from ..decompiler_conditions import assembly_conditions
from ..structure_descent import capped_scissions
from .dag import DAGError, SynthesisDAG
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "SearchStatus",
    "RouteSearchReceipt",
    "RouteSearchResult",
    "search_routes",
    "enumerate_routes",
    "enumerate_dags",
]

ROUTE_SEARCH_RECEIPT_SCHEMA = "smartchem.experiment/route-search-receipt-v1alpha1"
ROUTE_SEARCH_RESULT_SCHEMA = "smartchem.experiment/route-search-result-v1alpha2"


class SearchStatus(str, Enum):
    """Whether the declared bounded search actually exhausted its admitted candidate space."""

    COMPLETE_WITHIN_BOUNDS = "COMPLETE_WITHIN_BOUNDS"
    PARTIAL_CUT_BUDGET = "PARTIAL_CUT_BUDGET"
    PARTIAL_RESULT_LIMIT = "PARTIAL_RESULT_LIMIT"
    PARTIAL_MULTIPLE_LIMITS = "PARTIAL_MULTIPLE_LIMITS"


@dataclass(frozen=True)
class RouteSearchReceipt(Digestible):
    """Auditable termination facts for one linear route search.

    ``COMPLETE_WITHIN_BOUNDS`` never means complete chemistry.  It means exhaustive only within the current
    linear, acyclic, capped-scission grammar, the stated depth, and the attempted per-expansion cut budget.
    """

    schema_version: str
    max_depth: int
    result_limit: int
    cut_budget_per_expansion: int
    expansions_attempted: int
    incomplete_expansions: int
    result_limit_saturated: bool
    results_returned: int

    def __post_init__(self) -> None:
        if self.schema_version != ROUTE_SEARCH_RECEIPT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {ROUTE_SEARCH_RECEIPT_SCHEMA!r}")
        for name in ("max_depth", "result_limit", "cut_budget_per_expansion"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("expansions_attempted", "incomplete_expansions", "results_returned"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if type(self.result_limit_saturated) is not bool:
            raise TypeError("result_limit_saturated must be bool")
        if self.incomplete_expansions > self.expansions_attempted:
            raise ValueError("incomplete_expansions cannot exceed expansions_attempted")
        if self.results_returned > self.result_limit:
            raise ValueError("results_returned cannot exceed result_limit")

    @property
    def cut_budget_exhausted(self) -> bool:
        return self.incomplete_expansions > 0

    @property
    def complete_within_bounds(self) -> bool:
        return not self.cut_budget_exhausted and not self.result_limit_saturated

    @property
    def status(self) -> SearchStatus:
        if self.cut_budget_exhausted and self.result_limit_saturated:
            return SearchStatus.PARTIAL_MULTIPLE_LIMITS
        if self.cut_budget_exhausted:
            return SearchStatus.PARTIAL_CUT_BUDGET
        if self.result_limit_saturated:
            return SearchStatus.PARTIAL_RESULT_LIMIT
        return SearchStatus.COMPLETE_WITHIN_BOUNDS

    def render(self) -> str:
        return (
            f"SEARCH RECEIPT: {self.status.value}; results={self.results_returned}/{self.result_limit}; "
            f"depth<={self.max_depth}; expansions={self.expansions_attempted}; "
            f"incomplete cut expansions={self.incomplete_expansions}; "
            f"cut budget={self.cut_budget_per_expansion} candidates per expansion. "
            "Scope: linear acyclic routes in the current capped-scission rewrite grammar; not all chemistry."
        )


@dataclass(frozen=True)
class RouteSearchResult(Digestible):
    schema_version: str
    routes: tuple[ExperimentRoute, ...]
    receipt: RouteSearchReceipt
    target_in_terminal_stock: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != ROUTE_SEARCH_RESULT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {ROUTE_SEARCH_RESULT_SCHEMA!r}")
        if type(self.routes) is not tuple or any(type(route) is not ExperimentRoute for route in self.routes):
            raise TypeError("routes must be a tuple of ExperimentRoute values")
        if type(self.receipt) is not RouteSearchReceipt:
            raise TypeError("receipt must be a RouteSearchReceipt")
        if type(self.target_in_terminal_stock) is not bool:
            raise TypeError("target_in_terminal_stock must be bool")
        if self.receipt.results_returned != len(self.routes):
            raise ValueError("receipt.results_returned must equal len(routes)")
        if self.target_in_terminal_stock and self.routes:
            raise ValueError("an already-stocked target cannot also carry synthesis routes")
        if self.target_in_terminal_stock and self.receipt.expansions_attempted:
            raise ValueError("an already-stocked target must terminate before expansion")


def _ident(m: Molecule) -> str:
    try:
        return canonical_digest(m.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(m)


def _conditions_for(capped) -> ConditionEnvelope:
    """The sourced conditions for a capped cleavage (via its forgetful mediated edge), or unknown()."""
    try:
        # The capped edge is a DECOMPOSITION but this module reads it backward as an ASSEMBLY.  Conditions
        # are directional experimental evidence, not algebraic decoration: hydrolysis conditions cannot be
        # copied onto the reverse condensation merely because the balance is reversible.
        return assembly_conditions(capped)
    except Exception:  # noqa: BLE001 -- a conditions lookup miss must never break route generation
        return ConditionEnvelope.unknown()


def search_routes(
    target: Molecule,
    *,
    reagents: tuple[Molecule, ...],
    available: tuple[Molecule, ...] = (),
    commodities: tuple[Molecule, ...] = (),
    max_depth: int = 2,
    max_routes: int = 100,
    cut_budget: int = 20_000,
) -> RouteSearchResult:
    """Search for candidate routes and return candidates plus an explicit completeness receipt.

    ``reagents`` are the small helpers the cleavage may consume (water, an anhydride, an acid); ``available``
    are precursors the chemist already has, which terminate the backward search (the ``reagents`` are treated
    as available too).  ``commodities`` are widely-obtainable stock (the "poor-man's buckets" -- table salt,
    vinegar, baking soda; see :mod:`smartchem.data.reagents`) that ALSO terminate a branch: a route can bottom
    out at stuff a chemist can actually buy instead of at pure elements.  All three sets terminate identically
    -- they are keyed by the same canonical identity (:func:`_ident`), never by formula, so a same-formula
    isomer never wrongly terminates (the ``a-reaction-key-by-formula-borrows-a-rate`` fail-open).  Linear
    routes only (a step with at most one not-yet-available precursor is recursed on); a step whose precursors
    are all on hand is a complete route.  The receipt distinguishes an exhaustive empty result *within this
    bounded rewrite grammar* from a search cut short by a candidate budget or unique-result limit.
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    for name, value in (("max_depth", max_depth), ("max_routes", max_routes), ("cut_budget", cut_budget)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    on_hand = {_ident(m) for m in (*available, *reagents, *commodities)}
    if _ident(target) in on_hand:
        receipt = RouteSearchReceipt(
            ROUTE_SEARCH_RECEIPT_SCHEMA,
            max_depth,
            max_routes,
            cut_budget,
            0,
            0,
            False,
            0,
        )
        return RouteSearchResult(ROUTE_SEARCH_RESULT_SCHEMA, (), receipt, True)
    seen_routes: dict[str, ExperimentRoute] = {}
    expansions_attempted = 0
    incomplete_expansions = 0
    result_limit_saturated = False

    def routes_making(t: Molecule, depth: int, ancestors: frozenset[str]):
        nonlocal expansions_attempted, incomplete_expansions
        if depth > max_depth:
            return
        expansions_attempted += 1
        cleavages, complete = capped_scissions(t, reagents, budget=cut_budget)
        if not complete:
            incomplete_expansions += 1
        for cs in cleavages:
            step = ExperimentStep.from_capped_scission(cs, envelope=_conditions_for(cs))
            # distinct precursors this step consumes, minus what is already on hand
            distinct: dict[str, Molecule] = {}
            for m in step.reactants:
                distinct.setdefault(_ident(m), m)
            missing = [m for k, m in distinct.items() if k not in on_hand and k not in ancestors]
            if not missing:
                yield ExperimentRoute.of(step)
            elif len(missing) == 1 and depth < max_depth:
                precursor = missing[0]
                for sub in routes_making(precursor, depth + 1, ancestors | {_ident(t)}):
                    yield ExperimentRoute.of(*sub.steps, step)

    for route in routes_making(target, 1, frozenset()):
        if route.digest in seen_routes:
            continue
        if len(seen_routes) == max_routes:
            result_limit_saturated = True
            break
        seen_routes[route.digest] = route
    routes = tuple(seen_routes.values())
    receipt = RouteSearchReceipt(
        ROUTE_SEARCH_RECEIPT_SCHEMA,
        max_depth,
        max_routes,
        cut_budget,
        expansions_attempted,
        incomplete_expansions,
        result_limit_saturated,
        len(routes),
    )
    return RouteSearchResult(ROUTE_SEARCH_RESULT_SCHEMA, routes, receipt, False)


def enumerate_routes(
    target: Molecule,
    *,
    reagents: tuple[Molecule, ...],
    available: tuple[Molecule, ...] = (),
    commodities: tuple[Molecule, ...] = (),
    max_depth: int = 2,
    max_routes: int = 100,
    cut_budget: int = 20_000,
) -> tuple[ExperimentRoute, ...]:
    """Compatibility wrapper returning only routes; use :func:`search_routes` for completeness facts."""
    return search_routes(
        target,
        reagents=reagents,
        available=available,
        commodities=commodities,
        max_depth=max_depth,
        max_routes=max_routes,
        cut_budget=cut_budget,
    ).routes


def _prune_to_sink(steps: tuple[ExperimentStep, ...]) -> tuple[ExperimentStep, ...]:
    """Keep only the steps that (transitively) feed the final-target producer (``steps[-1]``), dropping any
    ORPHAN branch that makes nothing downstream consumes.

    When :func:`_merge_branches` drops a duplicate producer of a shared intermediate, that producer's private
    sub-tree can be left orphaned (its output now feeds nothing).  ``SynthesisDAG`` refuses an orphan, so such a
    candidate would be silently lost (a false negative -- correct, but incomplete).  Pruning to the sink's
    backward-reachable set turns it into the valid synthesis "make the shared intermediate once, via the kept
    route".  A no-op whenever every step already feeds the sink (e.g. every depth<=2 candidate)."""
    producer: dict[str, ExperimentStep] = {}
    for s in steps:
        producer.setdefault(_ident(s.target), s)
    keep: set[str] = set()
    stack = [_ident(steps[-1].target)]
    while stack:
        tid = stack.pop()
        if tid in keep:
            continue
        keep.add(tid)
        s = producer.get(tid)
        if s is None:
            continue
        for r in s.reactants:
            rid = _ident(r)
            if rid in producer and rid not in keep:
                stack.append(rid)
    return tuple(s for s in steps if _ident(s.target) in keep)


def _merge_branches(branches: tuple[tuple[ExperimentStep, ...], ...]) -> tuple[ExperimentStep, ...]:
    """Flatten several branch step-lists into one, deduplicating by produced-target identity.

    Two branches of a convergent synthesis may share an intermediate (both need the same acid, say); a DAG
    makes each intermediate exactly once (``SynthesisDAG``'s distinct-targets invariant), so the shared step is
    kept once and the later branch's consumers resolve to it by identity in :meth:`SynthesisDAG.edges`.  First
    producer of a target wins; order is preserved so producers precede their eventual consumers.
    """
    by_target: dict[str, ExperimentStep] = {}
    order: list[ExperimentStep] = []
    for branch in branches:
        for step in branch:
            key = _ident(step.target)
            if key in by_target:
                continue
            by_target[key] = step
            order.append(step)
    return tuple(order)


def enumerate_dags(
    target: Molecule,
    *,
    reagents: tuple[Molecule, ...],
    available: tuple[Molecule, ...] = (),
    commodities: tuple[Molecule, ...] = (),
    max_depth: int = 2,
    max_dags: int = 100,
    cut_budget: int = 20_000,
) -> tuple[SynthesisDAG, ...]:
    """Enumerate candidate CONVERGENT synthesis DAGs to ``target`` -- the multi-precursor generalisation of
    :func:`enumerate_routes`.

    :func:`enumerate_routes` recurses on exactly ONE missing precursor per step and silently drops any cleavage
    whose join needs two-or-more precursors both made from scratch -- so a genuinely convergent target (make A
    down one branch, B down another, then a step consuming both) never compiled.  This function lifts that: at a
    step with several missing precursors it recurses on EACH, takes the cartesian product of the ways to make
    them, merges the branches (deduping shared intermediates, :func:`_merge_branches`), and appends the joining
    step -- yielding a :class:`~smartchem.experiment.dag.SynthesisDAG`.

    Every proposed step-list is handed to :meth:`SynthesisDAG.of`, which is the single source of DAG-invariant
    truth: it refuses a duplicate-target, a cycle (a sub-branch that consumes an ancestor, the bounded-recursion
    escape hatch here), or a disconnected orphan, and any such candidate is skipped rather than special-cased
    out.  The linear route is the special case where the DAG is a path (:attr:`SynthesisDAG.is_convergent` is
    ``False``); this enumerator is a strict superset of :func:`enumerate_routes`, adding the convergent shapes it
    could not reach.  Termination and identity discipline are inherited unchanged (strictly-smaller precursors,
    ``max_depth`` bound, identity-keyed inventory termination -- never by formula).

    Returns deduplicated DAGs (by digest); empty if nothing within ``max_depth`` reaches the inventory -- a loud
    "no route found", never a fabricated one.  ``max_dags`` bounds the number of DISTINCT syntheses at every
    recursion level (candidates are deduped by an order-invariant step-set signature AS they are built, so the
    cap counts unique results, not the duplicate-heavy raw ``itertools.product`` combos -- a cap that throttled
    the raw candidates would truncate before the dedup and silently drop most of the answer, including linear
    routes, breaking the superset guarantee).
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    on_hand = {_ident(m) for m in (*available, *reagents, *commodities)}

    def _sig(steps: tuple[ExperimentStep, ...]) -> frozenset[str]:
        """Order-invariant identity of a synthesis: the SET of its step digests (a DAG is not an ordered list)."""
        return frozenset(s.digest for s in steps)

    def syntheses_making(t: Molecule, depth: int, ancestors: frozenset[str]) -> list[tuple[ExperimentStep, ...]]:
        """The DISTINCT step-lists (deduped by :func:`_sig`) that make ``t`` -- capped at ``max_dags`` UNIQUE."""
        out: list[tuple[ExperimentStep, ...]] = []
        seen: set[frozenset[str]] = set()
        if depth > max_depth:
            return out

        def offer(cand: tuple[ExperimentStep, ...]) -> bool:
            """Record a candidate if it is new; return False once the distinct cap is reached (stop the caller)."""
            sig = _sig(cand)
            if sig not in seen:
                seen.add(sig)
                out.append(cand)
            return len(out) < max_dags

        cleavages, _complete = capped_scissions(t, reagents, budget=cut_budget)
        for cs in cleavages:
            step = ExperimentStep.from_capped_scission(cs, envelope=_conditions_for(cs))
            distinct: dict[str, Molecule] = {}
            for m in step.reactants:
                distinct.setdefault(_ident(m), m)
            missing = [m for k, m in distinct.items() if k not in on_hand and k not in ancestors]
            if not missing:
                if not offer((step,)):
                    break
            elif depth < max_depth:
                child_ancestors = ancestors | {_ident(t)}
                options: list[list[tuple[ExperimentStep, ...]]] = []
                reachable = True
                for m in missing:
                    subs = syntheses_making(m, depth + 1, child_ancestors)
                    if not subs:
                        reachable = False  # a precursor no branch can make -> this cleavage is a dead end
                        break
                    options.append(subs)
                if not reachable:
                    continue
                capped = False
                for combo in itertools.product(*options):
                    # merge the branches, append the join, then prune any branch orphaned by a shared-intermediate
                    # dedup -> a valid connected synthesis (a no-op at depth<=2, where nothing is orphaned).
                    if not offer(_prune_to_sink(_merge_branches(combo) + (step,))):
                        capped = True
                        break
                if capped:
                    break
            if len(out) >= max_dags:
                break
        return out

    seen_dags: dict[str, SynthesisDAG] = {}
    for steps in syntheses_making(target, 1, frozenset()):
        if len(seen_dags) >= max_dags:
            break
        try:
            dag = SynthesisDAG.of(*steps)
        except DAGError:
            continue  # a cyclic / duplicate-target / orphaned candidate -- refused by the invariant, skipped
        seen_dags.setdefault(dag.digest, dag)
    return tuple(seen_dags.values())
