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

from ..category import Molecule
from ..conditions import ConditionEnvelope
from ..contracts import canonical_digest
from ..decompiler_conditions import reaction_conditions
from ..structure_descent import capped_scissions
from .step import ExperimentRoute, ExperimentStep

__all__ = ["enumerate_routes"]


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
