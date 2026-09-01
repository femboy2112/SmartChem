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

from ..category import Molecule
from ..conditions import ConditionEnvelope
from ..contracts import Digestible, canonical_digest
from ..decompiler_conditions import assembly_conditions
from ..search import SearchStatus
from ..structure_descent import capped_scissions
from .dag import DAGError, SynthesisDAG
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "SearchStatus",
    "RouteSearchReceipt",
    "RouteSearchResult",
    "search_routes",
    "enumerate_routes",
    "DAGSearchReceipt",
    "DAGSearchResult",
    "search_dags",
    "enumerate_dags",
]

ROUTE_SEARCH_RECEIPT_SCHEMA = "smartchem.experiment/route-search-receipt-v1alpha1"
ROUTE_SEARCH_RESULT_SCHEMA = "smartchem.experiment/route-search-result-v1alpha2"
DAG_SEARCH_RECEIPT_SCHEMA = "smartchem.experiment/dag-search-receipt-v1alpha1"
DAG_SEARCH_RESULT_SCHEMA = "smartchem.experiment/dag-search-result-v1alpha1"


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
    # a linear-expandable branch (exactly one missing precursor) cut solely because the recursion hit max_depth;
    # trailing default keeps the first-brick positional constructions valid. See SearchStatus.PARTIAL_DEPTH_LIMIT.
    depth_truncated_branches: int = 0

    def __post_init__(self) -> None:
        if self.schema_version != ROUTE_SEARCH_RECEIPT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {ROUTE_SEARCH_RECEIPT_SCHEMA!r}")
        for name in ("max_depth", "result_limit", "cut_budget_per_expansion"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("expansions_attempted", "incomplete_expansions", "results_returned", "depth_truncated_branches"):
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
    def depth_limited(self) -> bool:
        """True iff an expandable branch was cut solely by the max-depth bound (a real missed-route truncation)."""
        return self.depth_truncated_branches > 0

    @property
    def complete_within_bounds(self) -> bool:
        return not self.cut_budget_exhausted and not self.result_limit_saturated and not self.depth_limited

    @property
    def status(self) -> SearchStatus:
        active = [
            s for fired, s in (
                (self.cut_budget_exhausted, SearchStatus.PARTIAL_CUT_BUDGET),
                (self.result_limit_saturated, SearchStatus.PARTIAL_RESULT_LIMIT),
                (self.depth_limited, SearchStatus.PARTIAL_DEPTH_LIMIT),
            ) if fired
        ]
        if not active:
            return SearchStatus.COMPLETE_WITHIN_BOUNDS
        if len(active) > 1:
            return SearchStatus.PARTIAL_MULTIPLE_LIMITS
        return active[0]

    def render(self) -> str:
        return (
            f"SEARCH RECEIPT: {self.status.value}; results={self.results_returned}/{self.result_limit}; "
            f"depth<={self.max_depth}; expansions={self.expansions_attempted}; "
            f"incomplete cut expansions={self.incomplete_expansions}; "
            f"depth-truncated branches={self.depth_truncated_branches}; "
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


@dataclass(frozen=True)
class DAGSearchReceipt(Digestible):
    """Auditable termination facts for one convergent-DAG synthesis search.

    The exact sibling of :class:`RouteSearchReceipt` for the convergent generalisation (:func:`search_dags`):
    ``COMPLETE_WITHIN_BOUNDS`` means exhaustive only within the current capped-scission rewrite grammar, the
    stated depth, and the attempted per-expansion cut budget -- never complete chemistry.

    One honesty caveat is specific to the DAG search and stated loudly: ``result_limit_saturated`` is
    *conservative*.  ``max_dags`` caps the distinct syntheses collected at *every* recursion level (a scarce
    precursor may itself have more ways to make it than the cap allows), so the flag is set whenever any level
    filled its cap and stopped enumerating.  When the true distinct count happened to equal ``max_dags`` exactly,
    this reports PARTIAL where COMPLETE would also have been defensible -- an error that always points toward
    "there may be more", never toward a false claim of completeness (W2: a truncated search is never silently a
    full one).
    """

    schema_version: str
    max_depth: int
    result_limit: int
    cut_budget_per_expansion: int
    expansions_attempted: int
    incomplete_expansions: int
    result_limit_saturated: bool
    results_returned: int
    # a convergent branch (any missing precursor) cut solely because the recursion hit max_depth; trailing
    # default keeps the first-brick positional constructions valid. See SearchStatus.PARTIAL_DEPTH_LIMIT.
    depth_truncated_branches: int = 0

    def __post_init__(self) -> None:
        if self.schema_version != DAG_SEARCH_RECEIPT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {DAG_SEARCH_RECEIPT_SCHEMA!r}")
        for name in ("max_depth", "result_limit", "cut_budget_per_expansion"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("expansions_attempted", "incomplete_expansions", "results_returned", "depth_truncated_branches"):
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
    def depth_limited(self) -> bool:
        """True iff an expandable branch was cut solely by the max-depth bound (a real missed-synthesis truncation)."""
        return self.depth_truncated_branches > 0

    @property
    def complete_within_bounds(self) -> bool:
        return not self.cut_budget_exhausted and not self.result_limit_saturated and not self.depth_limited

    @property
    def status(self) -> SearchStatus:
        active = [
            s for fired, s in (
                (self.cut_budget_exhausted, SearchStatus.PARTIAL_CUT_BUDGET),
                (self.result_limit_saturated, SearchStatus.PARTIAL_RESULT_LIMIT),
                (self.depth_limited, SearchStatus.PARTIAL_DEPTH_LIMIT),
            ) if fired
        ]
        if not active:
            return SearchStatus.COMPLETE_WITHIN_BOUNDS
        if len(active) > 1:
            return SearchStatus.PARTIAL_MULTIPLE_LIMITS
        return active[0]

    def render(self) -> str:
        return (
            f"DAG SEARCH RECEIPT: {self.status.value}; distinct syntheses={self.results_returned}/"
            f"{self.result_limit}; depth<={self.max_depth}; expansions={self.expansions_attempted}; "
            f"incomplete cut expansions={self.incomplete_expansions}; "
            f"depth-truncated branches={self.depth_truncated_branches}; "
            f"cut budget={self.cut_budget_per_expansion} candidates per expansion. "
            "Scope: convergent + linear synthesis DAGs in the current capped-scission rewrite grammar; "
            "not all chemistry."
        )


@dataclass(frozen=True)
class DAGSearchResult(Digestible):
    schema_version: str
    dags: tuple[SynthesisDAG, ...]
    receipt: DAGSearchReceipt
    target_in_terminal_stock: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != DAG_SEARCH_RESULT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {DAG_SEARCH_RESULT_SCHEMA!r}")
        if type(self.dags) is not tuple or any(type(d) is not SynthesisDAG for d in self.dags):
            raise TypeError("dags must be a tuple of SynthesisDAG values")
        if type(self.receipt) is not DAGSearchReceipt:
            raise TypeError("receipt must be a DAGSearchReceipt")
        if type(self.target_in_terminal_stock) is not bool:
            raise TypeError("target_in_terminal_stock must be bool")
        if self.receipt.results_returned != len(self.dags):
            raise ValueError("receipt.results_returned must equal len(dags)")
        if self.target_in_terminal_stock and self.dags:
            raise ValueError("an already-stocked target cannot also carry synthesis DAGs")
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
    depth_truncated = 0
    result_limit_saturated = False

    def routes_making(t: Molecule, depth: int, ancestors: frozenset[str]):
        nonlocal expansions_attempted, incomplete_expansions, depth_truncated
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
            elif len(missing) == 1:
                # a linear-expandable branch (exactly one missing precursor) we could have recursed on, but
                # depth ran out -- a real depth truncation (a route may exist just past max_depth). A >=2-missing
                # branch is a LINEAR-grammar boundary (search_dags' job), not a depth limit, so it is not counted.
                depth_truncated += 1

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
        depth_truncated,
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


def search_dags(
    target: Molecule,
    *,
    reagents: tuple[Molecule, ...],
    available: tuple[Molecule, ...] = (),
    commodities: tuple[Molecule, ...] = (),
    max_depth: int = 2,
    max_dags: int = 100,
    cut_budget: int = 20_000,
) -> DAGSearchResult:
    """Search for candidate CONVERGENT synthesis DAGs and return them plus an explicit completeness receipt.

    The receipt-bearing sibling of :func:`enumerate_dags`, exactly as :func:`search_routes` is to
    :func:`enumerate_routes`.  It *instruments* -- never rewrites -- the enumeration hardened at ``b5faf7d``
    (against the ``max_dags`` pre-dedup truncation and the shared-intermediate orphan), adding three auditable
    facts the receipt-free tuple API discarded:

    * ``expansions_attempted`` / ``incomplete_expansions`` -- how many sub-searches ran and how many hit an
      incomplete cut budget (the ``complete`` flag from :func:`~smartchem.structure_descent.capped_scissions`
      that :func:`enumerate_dags` dropped on the floor at every level);
    * ``result_limit_saturated`` -- whether the distinct-result cap ``max_dags`` truncated any level's
      enumeration.

    Without these, a DAG "no route" was indistinguishable from "the cut budget was too small" or "``max_dags``
    was too small" -- the exact silent-sample defect P0-1 forbids.  ``COMPLETE_WITHIN_BOUNDS`` on the receipt
    never means complete chemistry: only exhaustive within this bounded rewrite grammar, depth and cut budget.

    The enumeration itself is unchanged.  :func:`enumerate_routes` recurses on exactly ONE missing precursor per
    step and silently drops any cleavage whose join needs two-or-more from-scratch precursors; this lifts that by
    recursing on EACH missing precursor, taking the cartesian product of the ways to make them, merging the
    branches (deduping shared intermediates, :func:`_merge_branches`), pruning any branch orphaned by that dedup
    (:func:`_prune_to_sink`), and appending the joining step -- a strict superset of :func:`enumerate_routes`.
    Every step-list is handed to :meth:`SynthesisDAG.of`, the single source of DAG-invariant truth (refusing
    duplicate targets, cycles, orphans).  ``max_dags`` bounds the number of DISTINCT syntheses at every recursion
    level -- deduped by an order-invariant step-set signature AS built, so the cap counts unique results, not the
    duplicate-heavy raw ``itertools.product`` combos.

    A target already present in ``available``/``reagents``/``commodities`` terminates before expansion
    (standard §7: a node matching the active terminal policy MUST terminate; the target need not be synthesised)
    and returns ``target_in_terminal_stock=True`` with no DAGs and no expansions -- exactly as
    :func:`search_routes` does, so the two directions share one terminal semantics.
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    for name, value in (("max_depth", max_depth), ("max_dags", max_dags), ("cut_budget", cut_budget)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    on_hand = {_ident(m) for m in (*available, *reagents, *commodities)}
    if _ident(target) in on_hand:
        receipt = DAGSearchReceipt(
            DAG_SEARCH_RECEIPT_SCHEMA, max_depth, max_dags, cut_budget, 0, 0, False, 0
        )
        return DAGSearchResult(DAG_SEARCH_RESULT_SCHEMA, (), receipt, True)

    expansions_attempted = 0
    incomplete_expansions = 0
    depth_truncated = 0
    result_limit_saturated = False

    def _sig(steps: tuple[ExperimentStep, ...]) -> frozenset[str]:
        """Order-invariant identity of a synthesis: the SET of its step digests (a DAG is not an ordered list)."""
        return frozenset(s.digest for s in steps)

    def syntheses_making(t: Molecule, depth: int, ancestors: frozenset[str]) -> list[tuple[ExperimentStep, ...]]:
        """The DISTINCT step-lists (deduped by :func:`_sig`) that make ``t`` -- capped at ``max_dags`` UNIQUE."""
        nonlocal expansions_attempted, incomplete_expansions, result_limit_saturated, depth_truncated
        out: list[tuple[ExperimentStep, ...]] = []
        seen: set[frozenset[str]] = set()
        if depth > max_depth:
            return out

        def offer(cand: tuple[ExperimentStep, ...]) -> bool:
            """Record a candidate if it is new; return False once the distinct cap is reached (stop the caller).

            Reaching the cap is a real truncation of *this level's* candidate set, so it flags the whole search
            partial -- conservatively (see :class:`DAGSearchReceipt`): the flag also fires when the level's true
            distinct count merely equalled ``max_dags``, which errs toward "there may be more", never toward a
            false COMPLETE.
            """
            nonlocal result_limit_saturated
            sig = _sig(cand)
            if sig not in seen:
                seen.add(sig)
                out.append(cand)
            if len(out) >= max_dags:
                result_limit_saturated = True
                return False
            return True

        expansions_attempted += 1
        cleavages, complete = capped_scissions(t, reagents, budget=cut_budget)
        if not complete:
            incomplete_expansions += 1
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
            else:
                # missing precursors but depth == max_depth: an expandable convergent branch cut by the depth
                # bound (the recursion could have made any number of missing precursors) -- a real depth
                # truncation, so a synthesis may exist just past max_depth and the search is not complete.
                depth_truncated += 1
            if len(out) >= max_dags:
                break
        return out

    seen_dags: dict[str, SynthesisDAG] = {}
    for steps in syntheses_making(target, 1, frozenset()):
        if len(seen_dags) >= max_dags:
            result_limit_saturated = True
            break
        try:
            dag = SynthesisDAG.of(*steps)
        except DAGError:
            continue  # a cyclic / duplicate-target / orphaned candidate -- refused by the invariant, skipped
        seen_dags.setdefault(dag.digest, dag)
    dags = tuple(seen_dags.values())
    receipt = DAGSearchReceipt(
        DAG_SEARCH_RECEIPT_SCHEMA,
        max_depth,
        max_dags,
        cut_budget,
        expansions_attempted,
        incomplete_expansions,
        result_limit_saturated,
        len(dags),
        depth_truncated,
    )
    return DAGSearchResult(DAG_SEARCH_RESULT_SCHEMA, dags, receipt, False)


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
    """Compatibility wrapper returning only the DAGs; use :func:`search_dags` for completeness facts.

    One deliberate, standard-driven behaviour change over the pre-receipt enumerator: a target already present
    in ``available``/``reagents``/``commodities`` now terminates before expansion (§7) and yields ``()`` -- you
    do not synthesise what you already hold, and the linear :func:`enumerate_routes` already behaved this way.
    Every other input is unchanged.
    """
    return search_dags(
        target,
        reagents=reagents,
        available=available,
        commodities=commodities,
        max_depth=max_depth,
        max_dags=max_dags,
        cut_budget=cut_budget,
    ).dags
