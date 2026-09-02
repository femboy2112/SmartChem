"""The front door: an arbitrary target -> a bounded synthesis analysis over declared terminal stock.

`compile_synthesis(target)` is the one entry that composes the whole stack a chemist needs, reusing every
rung and inventing no physics:

* it DECOMPILES the target and enumerates candidate synthesis routes that bottom out at either the classic
  ELEMENTAL buckets or -- the default -- the POOR-MAN'S commodity buckets (table salt, vinegar, baking soda;
  :mod:`smartchem.data.reagents`), so a route ends at stock a chemist can obtain, not at elemental sodium;
* it ranks them and picks the best by L2 GRADE FIRST (a KNOWN documented synthesis beats a HYPOTHESIZED
  longer chain), then the fit ranking (composability, sourced feasibility/selectivity, rate) as tiebreaker,
  and renders the best returned route as an evidence dossier (:func:`~smartchem.experiment.drafter.draft_route_dossier`:
  balanced equations, conditions, ΔG feasibility, equilibrium extent, selectivity, the E6 byproduct/off-gas/
  hazard/care ledger, equipment, the conservation ceiling);
* it grades the whole thing with the single L2 verdict (:func:`~smartchem.experiment.classify.classify_route`)
  and surfaces the orthogonal RATE (Arrhenius + Eyring) the bare draft omits;
* it hands back the SHOPPING LIST -- the commodity leaves to buy -- and lists the alternative routes WITH
  their grades, so a KNOWN route is never hidden behind a bare count.

Every number keeps its epistemic bucket; a genuine gap is a loud UNKNOWN, never a fabricated value.  Each
per-value derived/sourced/unknown label lives on the drafted quantities themselves; the LEDGER states the
SCOPE.  This is the composition layer only -- it adds no model and asserts no reaction.

Honest scope (stated in the ledger so the output never over-claims): the best route is a LINEAR chain (the
enumerator drops convergent, multi-precursor-from-scratch branches -- true AND-OR-tree enumeration is a
roadmap item); rate/thermo reach only where sourced/derivable, else UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..category import Molecule
from ..contracts import canonical_digest
from ..data.reagents import CommodityReagent, commodity_for, commodity_inventory
from ..decompiler import Formula
from ..structure import resolve_structure
from .classify import Grade, UnifiedVerdict, classify_route
from .drafter import RouteDossier, RouteFit, draft_route_dossier, rank_routes
from .eyring import RouteEyring, verify_eyring
from .kinetics import RouteKinetics, verify_kinetics
from .routes import RouteSearchReceipt, search_routes
from .step import ExperimentRoute

__all__ = ["CompiledSynthesis", "compile_synthesis"]

#: Best-first order over the L2 grade: a KNOWN documented synthesis outranks a longer HYPOTHESIZED chain;
#: a REFUTED route sinks last.  This is the criterion the fit-ranking (drafter._route_score) never applies.
_GRADE_RANK = {
    Grade.KNOWN: 0, Grade.DERIVED: 1, Grade.PREDICTED: 2, Grade.HYPOTHESIZED: 3,
    Grade.UNKNOWN: 4, Grade.REFUTED: 5,
}
def _ident(m: Molecule) -> str:
    try:
        return canonical_digest(m.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(m)


def _chemist_label(m: Molecule) -> str:
    formula = repr(Formula.of(m.formula, m.charge))
    named = resolve_structure(m)
    return f"{named.name} [{formula}]" if named is not None else formula


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
    """A compiled target: bounded routes ranked by grade, the best rendered as an evidence dossier,
    and identity-level sourcing leads -- with a scope ledger.  A presentation aggregate; adds no physics."""

    target: Molecule
    ranked: tuple[RouteFit, ...]
    best_draft: RouteDossier | None
    verdict: UnifiedVerdict | None
    kinetics: RouteKinetics | None
    eyring: RouteEyring | None
    shopping: tuple[CommodityReagent, ...]
    other_leaves: tuple[str, ...]
    alternatives: tuple[tuple[str, str], ...] = ()   # (grade, equation) for the other classified routes
    already_obtainable: CommodityReagent | None = None  # set when the target IS itself a commodity
    ledger: tuple[str, ...] = field(default_factory=tuple)
    search_receipt: RouteSearchReceipt | None = None
    already_in_active_inventory: bool = False

    @property
    def found_route(self) -> bool:
        return (
            self.best_draft is not None
            or self.already_obtainable is not None
            or self.already_in_active_inventory
        )

    def render(self) -> str:
        lines: list[str] = []
        tgt = _chemist_label(self.target)
        lines.append(f"COMPILED SYNTHESIS -- target {tgt}")
        lines.append("=" * 88)

        if self.search_receipt is not None:
            lines.append(self.search_receipt.render())
            if not self.search_receipt.complete_within_bounds and self.search_receipt.results_returned:
                lines.append(
                    "PARTIAL SEARCH: ranking applies only to returned candidates; the selected route is not "
                    "proven best within the declared bounds."
                )

        if self.already_in_active_inventory:
            lines.append(
                "ACTIVE INVENTORY MATCH (EXACT CHEMICAL IDENTITY): the target is already present in the "
                "declared terminal stock; no synthesis expansion was attempted."
            )
            lines.append(
                "This identity match does not establish quantity, assay, concentration, phase, grade, "
                "impurities, or fitness for a particular operation."
            )
            for note in self.ledger:
                lines.append(f"  - {note}")
            return "\n".join(lines)

        if self.already_obtainable is not None:
            r = self.already_obtainable
            lines.append(
                f"COMMODITY SOURCE MATCH (CHEMICAL IDENTITY ONLY): {r.name} occurs in {r.common_source} "
                f"[{r.availability.value}]."
            )
            lines.append(
                "This does NOT establish that the retail material meets the target's purity, concentration, "
                "phase, grade, or impurity specification. Accept that source only if its material specification "
                "is adequate; otherwise purification and analytical verification remain open operations."
            )
            for note in self.ledger:
                lines.append(f"  - {note}")
            return "\n".join(lines)

        if self.best_draft is None:
            if self.search_receipt is not None and not self.search_receipt.complete_within_bounds:
                lines.append(
                    "NO ROUTE RETURNED; SEARCH WAS PARTIAL. Absence is not evidence that no route exists."
                )
            else:
                lines.append(
                    "NO ROUTE FOUND WITHIN THE DECLARED BOUNDED SEARCH SPACE. This is not a claim about all "
                    "chemistry outside the stated rewrite grammar and bounds."
                )
            for note in self.ledger:
                lines.append(f"  - {note}")
            return "\n".join(lines)

        refuted = self.verdict is not None and self.verdict.grade is Grade.REFUTED
        lines.append(f"OVERALL GRADE (L2): {self.verdict.grade.value} -- {self.verdict.headline}")
        if refuted:
            # a refuted route is not a synthesis; do not dress it up as a procedure.
            lines.append("This route is REFUTED by a named law -- it is NOT a synthesis procedure and is not "
                         "rendered as a route dossier. See the headline for the law it violates.")
            if self.alternatives:
                lines.append("Other routes considered (grade -- equation):")
                for g, eq in self.alternatives:
                    lines.append(f"  [{g}] {eq}")
            for note in self.ledger:
                lines.append(f"  - {note}")
            return "\n".join(lines)

        if self.kinetics is not None and self.kinetics.verdict != "UNKNOWN":
            lines.append(f"RATE (orthogonal, ranking-only): Arrhenius {self.kinetics.verdict}")
        if self.eyring is not None and self.eyring.verdict != "UNKNOWN":
            lines.append(f"RATE (orthogonal, ranking-only): Eyring/TST {self.eyring.verdict}")
        lines.append("")

        lines.append("SHOPPING LIST -- commodity buckets to obtain:")
        if self.shopping:
            for r in self.shopping:
                lines.append(f"  * {r.name} -- {r.common_source} [{r.availability.value}]")
        else:
            lines.append("  (none of the route's starting materials matched a known commodity)")
        lines.append(
            "  MATERIAL NOTE: matches are identity-level source leads, not pure-reagent equivalence; assay, "
            "concentration, formulation, impurities, grade, region, quantity, and price are not yet modelled."
        )
        if self.other_leaves:
            lines.append("  other starting materials (not a known commodity -- source separately):")
            for lbl in self.other_leaves:
                lines.append(f"    - {lbl}")
        lines.append("")

        lines.append("SYNTHESIS (buckets -> target) CANDIDATE -- evidence dossier:")
        lines.append(self.best_draft.render())
        lines.append("")

        if self.alternatives:
            lines.append("ALTERNATIVE ROUTES considered (grade -- equation; best is drafted above):")
            for g, eq in self.alternatives:
                lines.append(f"  [{g}] {eq}")
        if self.ledger:
            lines.append("LEDGER (scope of this compile; per-value derived/sourced/UNKNOWN labels are on the "
                         "drafted quantities above):")
            for note in self.ledger:
                lines.append(f"  - {note}")
        return "\n".join(lines)


def _equation(route: ExperimentRoute) -> str:
    return " ; ".join(s.equation() for s in route.steps)


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
    max_routes: int = 100,
    cut_budget: int = 20_000,
    losses: tuple = (),
) -> CompiledSynthesis:
    """Compile ``target`` into a bounded, bucket-terminated candidate-route evidence dossier.

    ``losses`` (EVD-KEY-01): the section-5.3 :class:`~smartchem.identity.IdentityLoss` records the TARGET identity
    carries (e.g. a stereo/isotope BLOCKER when the target was parsed from a SMILES that declared a feature the
    constitution-only model drops).  They thread to every sourced-evidence rung -- ranking, grading and the dossier
    -- so a sourced selectivity/kinetics verdict cannot SURVIVE a blocker for its class on a real compile run (the
    end-to-end bite ID-STEREO-01 records and this consumer enforces).

    ``commodities`` defaults to the full poor-man's inventory (:func:`commodity_inventory`) so routes bottom
    out at curated source leads; pass ``()`` to disable commodity termination (only explicit reagents and
    ``available`` stock then terminate structural search), or a custom tuple to restrict the bench.  All the
    sourced-data levers (``stability``/``thermo``/
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

    ledger = [
        "best route is a LINEAR chain; convergent (multi-precursor) trees are a roadmap item",
        "commodity terminals are curated source leads; identity is grounded, availability is editorial, and "
        "no purity/concentration/formulation equivalence is implied",
    ]

    # target-is-itself-a-commodity short-circuit: don't hand back a synthesis for something you can just buy.
    commodity_idents = {_ident(m) for m in commodity_stock}
    self_commodity = commodity_for(target) if _ident(target) in commodity_idents else None
    if self_commodity is not None:
        return CompiledSynthesis(
            target, (), None, None, None, None, (), (), (), self_commodity,
            tuple(ledger) + ("the target is itself a commodity -- synthesis is unnecessary",),
        )

    search = search_routes(
        target, reagents=reagents, available=available, commodities=commodity_stock, max_depth=max_depth,
        max_routes=max_routes, cut_budget=cut_budget,
    )
    if search.target_in_terminal_stock:
        return CompiledSynthesis(
            target=target,
            ranked=(),
            best_draft=None,
            verdict=None,
            kinetics=None,
            eyring=None,
            shopping=(),
            other_leaves=(),
            ledger=tuple(ledger) + (
                "the target matched the active exact-identity terminal stock; no synthesis was searched",
            ),
            search_receipt=search.receipt,
            already_in_active_inventory=True,
        )
    routes = search.routes
    if not routes:
        return CompiledSynthesis(
            target, (), None, None, None, None, (), (), (), None,
            tuple(ledger) + ("no cleavage reached the buckets within max_depth -- raise --max-depth or "
                             "widen the inventory",),
            search.receipt,
        )

    ranked = rank_routes(
        routes, stability=stability, selectivity=selectivity, thermo=thermo, kinetics=kinetics, losses=losses,
    )
    kw = {k: v for k, v in (
        ("thermo", thermo), ("stability", stability), ("selectivity", selectivity),
        ("kinetics", kinetics), ("barriers", barriers),
    ) if v is not None}

    # Re-rank every returned route by L2 GRADE first (fit order as the tiebreaker), so a 1-step KNOWN
    # documented synthesis surfaces above a longer HYPOTHESIZED chain.  The search receipt already bounds the
    # result set; silently classifying only a prefix would make "best returned" false.
    head = ranked
    graded = []
    for i, rf in enumerate(head):
        v = classify_route(rf.route, losses=losses, **kw)
        graded.append((_GRADE_RANK.get(v.grade, 99), i, rf, v))
    graded.sort(key=lambda t: (t[0], t[1]))
    _, _, best_fit, verdict = graded[0]
    best = best_fit.route

    draft = draft_route_dossier(best, feed=feed, stability=stability, selectivity=selectivity, thermo=thermo,
                                losses=losses)
    kin = verify_kinetics(best, kinetics=kinetics, losses=losses)
    eyr = verify_eyring(best, barriers=barriers)

    shopping: dict[str, CommodityReagent] = {}
    others: list[str] = []
    for m in _leaf_inputs(best):
        if _ident(m) in commodity_idents:
            r = commodity_for(m)
            if r is not None:
                shopping[r.name] = r
                continue
        others.append(_chemist_label(m))

    alternatives = tuple(
        (v.grade.value, _equation(rf.route)) for _, _, rf, v in graded if rf.route.digest != best.digest
    )

    return CompiledSynthesis(
        target=target,
        ranked=ranked,
        best_draft=draft,
        verdict=verdict,
        kinetics=kin,
        eyring=eyr,
        shopping=tuple(sorted(shopping.values(), key=lambda r: r.name)),
        other_leaves=tuple(sorted(set(others))),
        alternatives=alternatives,
        already_obtainable=None,
        ledger=tuple(ledger),
        search_receipt=search.receipt,
    )
