"""E5 -- enumerate candidate synthesis routes from the decompiler, closing the loop.

E0-E4 *consume* a route; E5 *generates* candidate routes from the decompiler's own conservation-valid
cleavages, so a chemist can hand the compiler a target + an inventory and get back ranked, runnable drafts.

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

from ..category import Molecule
from ..conditions import ConditionEnvelope
from ..contracts import canonical_digest
from ..decompiler_conditions import reaction_conditions
from ..structure_descent import capped_scissions
from .dag import DAGError, SynthesisDAG
from .step import ExperimentRoute, ExperimentStep

__all__ = ["enumerate_routes", "enumerate_dags"]


def _ident(m: Molecule) -> str:
    try:
        return canonical_digest(m.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(m)


def _conditions_for(capped) -> ConditionEnvelope:
    """The sourced conditions for a capped cleavage (via its forgetful mediated edge), or unknown()."""
    try:
        return reaction_conditions(capped.forget())
    except Exception:  # noqa: BLE001 -- a conditions lookup miss must never break route generation
        return ConditionEnvelope.unknown()


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
    """Enumerate candidate synthesis routes to ``target`` from an ``available`` inventory + a ``reagents`` pool.

    ``reagents`` are the small helpers the cleavage may consume (water, an anhydride, an acid); ``available``
    are precursors the chemist already has, which terminate the backward search (the ``reagents`` are treated
    as available too).  ``commodities`` are widely-obtainable stock (the "poor-man's buckets" -- table salt,
    vinegar, baking soda; see :mod:`smartchem.data.reagents`) that ALSO terminate a branch: a route can bottom
    out at stuff a chemist can actually buy instead of at pure elements.  All three sets terminate identically
    -- they are keyed by the same canonical identity (:func:`_ident`), never by formula, so a same-formula
    isomer never wrongly terminates (the ``a-reaction-key-by-formula-borrows-a-rate`` fail-open).  Linear
    routes only (a step with at most one not-yet-available precursor is recursed on); a step whose precursors
    are all on hand is a complete route.  Returns deduplicated routes, ready for
    :func:`~smartchem.experiment.drafter.rank_routes`.  Empty if nothing within ``max_depth`` reaches the
    inventory -- a loud "no route found", never a fabricated one.
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    on_hand = {_ident(m) for m in (*available, *reagents, *commodities)}
    seen_routes: dict[str, ExperimentRoute] = {}

    def routes_making(t: Molecule, depth: int, ancestors: frozenset[str]) -> list[ExperimentRoute]:
        out: list[ExperimentRoute] = []
        if depth > max_depth or len(seen_routes) >= max_routes:
            return out
        cleavages, _complete = capped_scissions(t, reagents, budget=cut_budget)
        for cs in cleavages:
            step = ExperimentStep.from_capped_scission(cs, envelope=_conditions_for(cs))
            # distinct precursors this step consumes, minus what is already on hand
            distinct: dict[str, Molecule] = {}
            for m in step.reactants:
                distinct.setdefault(_ident(m), m)
            missing = [m for k, m in distinct.items() if k not in on_hand and k not in ancestors]
            if not missing:
                out.append(ExperimentRoute.of(step))
            elif len(missing) == 1 and depth < max_depth:
                precursor = missing[0]
                for sub in routes_making(precursor, depth + 1, ancestors | {_ident(t)}):
                    out.append(ExperimentRoute.of(*sub.steps, step))
            if len(out) + len(seen_routes) >= max_routes:
                break
        return out

    for route in routes_making(target, 1, frozenset()):
        seen_routes.setdefault(route.digest, route)
    return tuple(seen_routes.values())


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
