"""The front door: an arbitrary target -> a bounded synthesis analysis over declared terminal stock.

`compile_synthesis(target)` is the one entry that composes the whole stack a chemist needs, reusing every
rung and inventing no physics:

* it DECOMPILES the target and enumerates candidate synthesis routes that bottom out at declared terminal stock
  or -- enabled by default -- the POOR-MAN'S commodity buckets (table salt, vinegar, baking soda;
  :mod:`smartchem.data.reagents`), retaining the distinction between chemical identity and material suitability;
* it enforces hard bench exclusions, then picks the best eligible candidate by L2 grade (a KNOWN documented
  synthesis beats a HYPOTHESIZED longer chain), with fit ranking as tiebreaker,
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
from ..search import PARTIAL_CANDIDATE_SET, SECTION_8_3_NOTE, section_8_3_label
from ..structure import resolve_structure
from .classify import Grade, UnifiedVerdict, classify_route
from .drafter import ConstraintBox, RouteDossier, RouteFit, RouteFitStatus, draft_route_dossier, rank_routes
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
    #: STEREO-DOSSIER-01: the human-readable TARGET STEREOCHEMISTRY perception block (CIP R/S + configuration
    #: completeness), pre-rendered from the target's :class:`~smartchem.smiles.SmilesFeatures`.  Empty when the target
    #: declared no perceivable stereo (achiral / a name / a formula).  PERCEPTION ONLY -- the search ran on the achiral
    #: constitution, so this is a disclosure block, never a search-identity or bench claim.
    target_stereo_lines: tuple[str, ...] = ()

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
        lines.extend(self.target_stereo_lines)   # STEREO-DOSSIER-01: the perceived R/S + configuration disclosure (if any)
        lines.append("=" * 88)

        if self.search_receipt is not None:
            lines.append(self.search_receipt.render())
            # SRCH-NO-01: when candidate(s) were returned, emit the section-8.3 label for the candidate cell so this
            # renderer covers ALL FOUR outcomes uniformly (COMPLETE_CANDIDATE_SET / PARTIAL_CANDIDATE_SET here; the
            # two empty cells are labelled in the no-route branch below).  The ranking caveat rides only the PARTIAL
            # cell, where the returned set is not proven exhaustive.
            if self.search_receipt.results_returned:
                label = section_8_3_label(
                    self.search_receipt.complete_within_bounds, self.search_receipt.results_returned
                )
                note = SECTION_8_3_NOTE[label]
                if label == PARTIAL_CANDIDATE_SET:
                    note += ". Ranking applies only to returned candidates; additional candidates may be missing."
                    if self.best_draft is not None:
                        note += " The selected route is not proven best within the declared bounds."
                lines.append(f"[{label}] {note}")

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
            if self.ranked:
                lines.append(
                    "[NO_ADMISSIBLE_RETURNED_ROUTE] Candidates were returned, but none qualifies for selection "
                    "under the declared bench constraints. No synthesis dossier or shopping recommendation is selected."
                )
                lines.append("RETURNED CANDIDATES -- diagnostic evidence only:")
                for fit in self.ranked:
                    lines.append(f"  route {fit.route.digest[:12]}: {_equation(fit.route)}")
                    lines.append(fit.explain())
                if self.alternatives:
                    lines.append("Candidate epistemic grades (independent of bench admissibility):")
                    for grade, equation in self.alternatives:
                        lines.append(f"  [{grade}] {equation}")
                for note in self.ledger:
                    lines.append(f"  - {note}")
                return "\n".join(lines)
            # SRCH-NO-01: route the no-route wording through the ONE section-8.3 label so the compile Dossier reads
            # the same four-outcome vocabulary as recompile/decompile.  No route was returned, so candidate_count=0;
            # the receipt's completeness picks NO_ROUTE_IN_DECLARED_SPACE (complete) vs INCOMPLETE_NO_ROUTE_OBSERVED
            # (incomplete).  A missing receipt is treated as complete, as the prior wording did.
            complete = self.search_receipt is None or self.search_receipt.complete_within_bounds
            label = section_8_3_label(complete, 0)
            lines.append(f"[{label}] {SECTION_8_3_NOTE[label]}.")
            for note in self.ledger:
                lines.append(f"  - {note}")
            return "\n".join(lines)

        refuted = self.verdict is not None and self.verdict.grade is Grade.REFUTED
        lines.append(f"OVERALL GRADE (L2): {self.verdict.grade.value} -- {self.verdict.headline}")
        for fit in self.ranked:
            if fit.route.digest == self.best_draft.route.digest:
                lines.append(fit.explain())
                break
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
            for fit in self.ranked:
                if fit.route.digest != self.best_draft.route.digest and (fit.exclusions or fit.gaps):
                    lines.append(f"  candidate {fit.route.digest[:12]} constraint diagnostics:")
                    lines.append(fit.explain())
        if self.ledger:
            lines.append("LEDGER (scope of this compile; per-value derived/sourced/UNKNOWN labels are on the "
                         "drafted quantities above):")
            for note in self.ledger:
                lines.append(f"  - {note}")
        return "\n".join(lines)


def _equation(route: ExperimentRoute) -> str:
    return " ; ".join(s.equation() for s in route.steps)


def _target_stereo_lines(features: "object | None") -> tuple[str, ...]:
    """The human-readable TARGET STEREOCHEMISTRY disclosure block from the target's SMILES features (STEREO-DOSSIER-01).

    Surfaces the ID-STEREO-01 perception a chemist otherwise never sees: the CIP R/S names of the SOUNDLY-nameable
    stereocentres (``features.cip_labels``) and whether the configuration is FULLY perceived
    (``features.configuration_complete``).  Returns ``()`` -- nothing to disclose -- when the target declared no
    perceivable stereo (achiral, or a name/formula target whose ``features`` is ``None`` or carries no marker).  It is
    strictly PERCEPTION: the route search ran on the achiral constitution :class:`~smartchem.category.Molecule`, so this
    block is a disclosure of the target-as-written, never a search-identity term or a bench-readiness claim (the §5.3
    achiral-collapse the whole ID-STEREO arc is honest about).  A marked centre that could NOT be soundly named (a
    same-element/ring priority, or an E/Z double bond) is disclosed as an explicit DEFERRAL, never dropped in silence.
    """
    if features is None:
        return ()
    cip = getattr(features, "cip_labels", ())
    marked = getattr(features, "stereocentres_marked", 0)
    tetrahedral = getattr(features, "tetrahedral_stereo", False)
    double_bond = getattr(features, "double_bond_stereo", False)
    complete = getattr(features, "configuration_complete", False)
    if not (tetrahedral or double_bond):
        return ()  # no declared stereo at all -- nothing to disclose (achiral as written)
    lines = [
        "TARGET STEREOCHEMISTRY (perceived from the target as written; PERCEPTION ONLY -- the route search ran on the "
        "achiral constitution, so this is a disclosure, not a search-identity or bench claim):",
    ]
    # STEREO-DOSSIER-01 fold (evil-morty Finding 1): disclose the NAMED and the DEFERRED centres INDEPENDENTLY, against
    # the marked-centre count, so a target with one nameable centre never hides the OTHER, deferred centres behind it.
    if cip:
        named = ", ".join(f"({label})" for label in cip)
        lines.append(
            f"  CIP R/S soundly named ({len(cip)} of {marked} marked tetrahedral centre(s), by descending-atomic-number "
            f"priority): {named}  (an unordered set -- not tied to a specific atom)"
        )
    deferred = marked - len(cip)
    if deferred > 0:
        lines.append(
            f"  {deferred} of {marked} marked tetrahedral centre(s) NOT soundly named -- a same-element/ring priority "
            "needs the recursive CIP digraph (a named ID-STEREO-01 deferral, never a guessed label)"
        )
    if double_bond:
        lines.append("  double-bond (E/Z) stereo: DECLARED but unperceived (E/Z naming is a named deferral)")
    # A SEPARATE axis from naming (evil-morty Finding 2): 'complete' means every declared centre was PERCEIVED for
    # identity/matching (WL parity), which a deferred centre still is -- so it must never be read as 'every centre named'.
    lines.append(
        "  configuration perception (for identity/matching, SEPARATE from the R/S naming above): "
        + ("COMPLETE -- every declared centre distinguished" if complete else
           "INCOMPLETE -- some declared configuration is unperceived, so it stays UNKNOWN (never a false merge)")
    )
    return tuple(lines)


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
    box: ConstraintBox | None = None,
    stability_loader=None,
    target_features: "object | None" = None,
) -> CompiledSynthesis:
    """Compile ``target`` into a bounded, bucket-terminated candidate-route evidence dossier.

    ``box`` carries physical and process limits through the same ``rank_routes`` used by the service.
    ``None`` leaves the bench unconstrained. Hard EXCLUDED candidates cannot be selected, regardless of grade.
    When process limits are active, only assessed FITS candidates qualify for a dossier; UNKNOWN candidates
    remain diagnostic evidence until the missing whole-step requirements are supplied. A fit assesses the
    selected constraints, not reaction success or bench readiness.

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

    ``stability_loader`` (CLI-CAN-02 remainder): an optional ``Callable[[tuple[Molecule, ...]], StabilityTable]``
    invoked AFTER the search with exactly the species it discovered, and only when ``stability`` was not passed.
    It lets a caller (``synthesize``) source stability for the route species -- intermediates included -- under its
    section-9 provider lever, without this engine importing the autoload stack.  ``None`` (every non-synthesize
    caller) means no autoload, so the ranked result is byte-identical to before.
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    # STEREO-DOSSIER-01: the target's perceived R/S + configuration disclosure, computed ONCE and threaded to every
    # return path (a chiral target discloses its stereo whether or not a route was found).  () when no perceivable stereo.
    stereo_lines = _target_stereo_lines(target_features)
    if not reagents:
        # the cleavage needs at least one cutting reagent; water is the universal default (as the CLI uses).
        from ..structure import structure_by_name
        w = structure_by_name("water")
        if w is not None:
            reagents = (w.molecule,)
    commodity_stock = commodity_inventory() if commodities is None else tuple(commodities)

    ledger = [
        "candidate routes are LINEAR chains; convergent (multi-precursor) trees are a roadmap item",
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
            target_stereo_lines=stereo_lines,
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
            target_stereo_lines=stereo_lines,
        )
    routes = search.routes
    if not routes:
        return CompiledSynthesis(
            target, (), None, None, None, None, (), (), (), None,
            tuple(ledger) + ("no cleavage reached the buckets within max_depth -- raise --max-depth or "
                             "widen the inventory",),
            search.receipt,
            target_stereo_lines=stereo_lines,
        )

    # CLI-CAN-02 remainder: when a stability LOADER is supplied (synthesize's --offline / section-9 provider lever),
    # source stability for exactly the species THIS search discovered -- run AFTER the search so route intermediates
    # are covered too -- then thread it through ranking/grading/draft below.  Every other caller passes no loader, so
    # ``stability`` stays exactly as given (no autoload) and the ranked result is byte-identical -- the deterministic
    # run_compilation ranking and the golden fixtures never move.
    if stability is None and stability_loader is not None:
        _seen: set[str] = set()
        _species: list[Molecule] = []
        for r in routes:
            for step in r.steps:
                for m in (*step.reactants, *step.products):
                    k = _ident(m)
                    if k not in _seen:
                        _seen.add(k)
                        _species.append(m)
        stability = stability_loader(tuple(_species))

    ranked = rank_routes(
        routes, box=box, stability=stability, selectivity=selectivity, thermo=thermo, kinetics=kinetics,
        losses=losses,
    )
    kw = {k: v for k, v in (
        ("thermo", thermo), ("stability", stability), ("selectivity", selectivity),
        ("kinetics", kinetics), ("barriers", barriers),
    ) if v is not None}

    # A known reaction outside the declared bench is still inadmissible. Grade is
    # a preference only after this hard gate, never permission to override it.
    # Under process bounds, UNKNOWN fit remains diagnostic evidence: it cannot
    # support the requested claim that the route is manageable on this bench.
    process_constrained = box is not None and box.process.constrains_anything
    head = ranked
    graded = []
    for i, rf in enumerate(head):
        v = classify_route(rf.route, losses=losses, **kw)
        admissible = rf.status is not RouteFitStatus.EXCLUDED and (
            not process_constrained or rf.status is RouteFitStatus.FITS
        )
        graded.append((not admissible, _GRADE_RANK.get(v.grade, 99), i, rf, v))
    graded.sort(key=lambda t: (t[0], t[1], t[2]))
    inadmissible, _, _, best_fit, verdict = graded[0]
    if inadmissible:
        reason = (
            "process constraints require assessed FITS for selection; UNKNOWN candidates are retained for "
            "evidence review, and EXCLUDED candidates cannot be selected"
            if process_constrained else
            "all returned routes are EXCLUDED by hard bench bounds or composability; an epistemic grade "
            "cannot override those exclusions"
        )
        return CompiledSynthesis(
            target=target, ranked=ranked, best_draft=None, verdict=None,
            kinetics=None, eyring=None, shopping=(), other_leaves=(),
            alternatives=tuple((v.grade.value, _equation(rf.route)) for _, _, _, rf, v in graded),
            ledger=tuple(ledger) + (reason, "no admissible route was observed among the returned candidates"),
            search_receipt=search.receipt,
            target_stereo_lines=stereo_lines,
        )
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
        (v.grade.value, _equation(rf.route)) for _, _, _, rf, v in graded if rf.route.digest != best.digest
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
        target_stereo_lines=stereo_lines,
    )
