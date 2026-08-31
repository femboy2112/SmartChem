"""The front door: an arbitrary target -> a COMPLETE synthesis, terminating at buckets you can actually buy.

`compile_synthesis(target)` is the one entry that composes the whole stack a chemist needs, reusing every
rung and inventing no physics:

* it DECOMPILES the target and enumerates candidate synthesis routes that bottom out at either the classic
  ELEMENTAL buckets or -- the default -- the POOR-MAN'S commodity buckets (table salt, vinegar, baking soda;
  :mod:`smartchem.data.reagents`), so a route ends at stock a chemist can obtain, not at elemental sodium;
* it RANKS them (composability, sourced feasibility/selectivity, rate) and drafts the best one in FULL
  chemist detail (:func:`~smartchem.experiment.drafter.draft_procedure`: balanced equations, conditions,
  ΔG feasibility, equilibrium extent, selectivity, the E6 byproduct/off-gas/hazard/care ledger, equipment,
  the conservation ceiling);
* it grades the whole thing with the single L2 verdict (:func:`~smartchem.experiment.classify.classify`)
  and surfaces the orthogonal RATE (Arrhenius + Eyring) the bare draft omits;
* it hands back the SHOPPING LIST -- the commodity leaves to buy -- and an honesty LEDGER of what is derived,
  what is sourced, and what stays a loud UNKNOWN.

Every number keeps its epistemic bucket; a genuine gap is a loud UNKNOWN, never a fabricated value.  This is
the composition layer only -- it adds no model and asserts no reaction.

Honest scope (rolled forward, named here so the output never over-claims): the best route is a LINEAR chain
(the enumerator drops convergent, multi-precursor-from-scratch branches -- true AND-OR-tree enumeration is a
roadmap item); rate/thermo reach only where sourced/derivable, else UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..category import Molecule
from ..contracts import canonical_digest
from ..data.reagents import CommodityReagent, commodity_for, commodity_inventory
from .classify import UnifiedVerdict, classify_route
from .drafter import DraftedProcedure, RouteFit, draft_procedure, rank_routes
from .eyring import RouteEyring, verify_eyring
from .kinetics import RouteKinetics, verify_kinetics
from .routes import enumerate_routes
from .step import ExperimentRoute

__all__ = ["CompiledSynthesis", "compile_synthesis"]


def _ident(m: Molecule) -> str:
    try:
        return canonical_digest(m.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(m)


def _leaf_inputs(route: ExperimentRoute) -> tuple[Molecule, ...]:
    """The external starting materials of a route: reactants produced by no earlier step (deduped)."""
    made = {_ident(s.target) for s in route.steps}
    seen: dict[str, Molecule] = {}
    for step in route.steps:
        for m in step.reactants:
            k = _ident(m)
            if k not in made:
                seen.setdefault(k, m)
    return tuple(seen.values())


@dataclass(frozen=True)
class CompiledSynthesis:
    """A compiled target: ranked bucket-terminated routes, the best drafted in full, its grade + rate, and
    the commodity shopping list -- with an honesty ledger.  A presentation aggregate; adds no physics."""

    target: Molecule
    ranked: tuple[RouteFit, ...]
    best_draft: DraftedProcedure | None
    verdict: UnifiedVerdict | None
    kinetics: RouteKinetics | None
    eyring: RouteEyring | None
    shopping: tuple[CommodityReagent, ...]
    other_leaves: tuple[str, ...]
    ledger: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found_route(self) -> bool:
        return self.best_draft is not None

    def render(self) -> str:
        lines: list[str] = []
        tgt = repr(self.target.formula) if hasattr(self.target, "formula") else repr(self.target)
        lines.append(f"COMPILED SYNTHESIS -- target {tgt}")
        lines.append("=" * 88)
        if not self.found_route:
            lines.append("NO ROUTE FOUND to the given buckets within the search horizon "
                         "(a loud 'no route', never a fabricated one).")
            for note in self.ledger:
                lines.append(f"  - {note}")
            return "\n".join(lines)

        # --- the headline grade + rate ---------------------------------------------------------------
        lines.append(f"OVERALL GRADE (L2): {self.verdict.grade.value} -- {self.verdict.headline}")
        if self.kinetics is not None and self.kinetics.verdict != "UNKNOWN":
            lines.append(f"RATE (orthogonal, ranking-only): Arrhenius {self.kinetics.verdict}")
        if self.eyring is not None and self.eyring.verdict != "UNKNOWN":
            lines.append(f"RATE (orthogonal, ranking-only): Eyring/TST {self.eyring.verdict}")
        lines.append("")

        # --- the shopping list (poor-man's buckets) --------------------------------------------------
        lines.append("SHOPPING LIST -- commodity buckets to obtain:")
        if self.shopping:
            for r in self.shopping:
                lines.append(f"  * {r.name} -- {r.common_source} [{r.availability.value}]")
        else:
            lines.append("  (none of the route's starting materials matched a known commodity)")
        if self.other_leaves:
            lines.append("  other starting materials (not a known commodity -- source separately):")
            for lbl in self.other_leaves:
                lines.append(f"    - {lbl}")
        lines.append("")

        # --- the full drafted procedure (all per-step chemist detail) --------------------------------
        lines.append("SYNTHESIS (buckets -> target), full detail:")
        lines.append(self.best_draft.render())
        lines.append("")

        # --- alternatives + honesty ledger -----------------------------------------------------------
        if len(self.ranked) > 1:
            lines.append(f"ALTERNATIVE ROUTES considered (ranked, best shown above): {len(self.ranked)}")
        if self.ledger:
            lines.append("LEDGER (what is derived / sourced / unknown, and the scope):")
            for note in self.ledger:
                lines.append(f"  - {note}")
        return "\n".join(lines)


def compile_synthesis(
    target: Molecule,
    *,
    reagents: tuple[Molecule, ...] = (),
    commodities: tuple[Molecule, ...] | None = None,
    available: tuple[Molecule, ...] = (),
    max_depth: int = 3,
    stability=None,
    thermo=None,
    selectivity=None,
    kinetics=None,
    barriers=None,
    feed=None,
) -> CompiledSynthesis:
    """Compile ``target`` into a complete, bucket-terminated synthesis with all chemist detail.

    ``commodities`` defaults to the full poor-man's inventory (:func:`commodity_inventory`) so routes bottom
    out at obtainable stock; pass ``()`` to disable commodity termination (elemental/``available`` only), or
    a custom tuple to restrict the bench.  All the sourced-data levers (``stability``/``thermo``/
    ``selectivity``/``kinetics``/``barriers``) and the E2 ``feed`` thread straight through to the rungs.
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    if not reagents:
        # the cleavage needs at least one cutting reagent; water is the universal default (as the CLI uses).
        from ..structure import structure_by_name
        w = structure_by_name("water")
        if w is not None:
            reagents = (w.molecule,)
    commodity_stock = commodity_inventory() if commodities is None else tuple(commodities)

    routes = enumerate_routes(
        target, reagents=reagents, available=available, commodities=commodity_stock, max_depth=max_depth,
    )
    ledger: list[str] = [
        "best route is a LINEAR chain; convergent (multi-precursor) trees are a roadmap item",
        "commodity buckets are a curated obtainability set; identity is grounded, availability is editorial",
    ]
    if not routes:
        return CompiledSynthesis(
            target, (), None, None, None, None, (), (),
            tuple(ledger) + ("no cleavage reached the buckets within max_depth -- raise --max-depth or "
                             "widen the inventory",),
        )

    ranked = rank_routes(
        routes, stability=stability, selectivity=selectivity, thermo=thermo, kinetics=kinetics,
    )
    best = ranked[0].route
    draft = draft_procedure(best, feed=feed, stability=stability, selectivity=selectivity, thermo=thermo)
    verdict = classify_route(
        best,
        **{k: v for k, v in (
            ("thermo", thermo), ("stability", stability), ("selectivity", selectivity),
            ("kinetics", kinetics), ("barriers", barriers),
        ) if v is not None},
    )
    kin = verify_kinetics(best, kinetics=kinetics)
    eyr = verify_eyring(best, barriers=barriers)

    # split the route's external leaves into commodities-to-buy vs everything else
    commodity_idents = {_ident(m) for m in commodity_stock}
    shopping: dict[str, CommodityReagent] = {}
    others: list[str] = []
    for m in _leaf_inputs(best):
        if _ident(m) in commodity_idents:
            r = commodity_for(m)
            if r is not None:
                shopping[r.name] = r
                continue
        others.append(repr(m.formula) if hasattr(m, "formula") else repr(m))

    return CompiledSynthesis(
        target=target,
        ranked=ranked,
        best_draft=draft,
        verdict=verdict,
        kinetics=kin,
        eyring=eyr,
        shopping=tuple(sorted(shopping.values(), key=lambda r: r.name)),
        other_leaves=tuple(sorted(set(others))),
        ledger=tuple(ledger),
    )
