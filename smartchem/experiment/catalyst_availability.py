"""CATALYST-OBTAIN-01 -- can the poor man's kitchen obtain the CATALYST a step declares?

The gap this closes (R50 KILL-2, re-verified in source). The kitchen capability model was blind to
catalysis. A reaction's declared catalyst is checked by NO gate: :class:`~smartchem.process_constraints.ProcessBounds`
has no catalyst field; :mod:`~smartchem.experiment.equipment` names no catalyst as a gate; the affordability model
(:mod:`~smartchem.experiment.affordability`) prices only the CONSUMED leaves a route buys, and a catalyst is
*regenerated* -- so it is never a purchased leaf and never reaches the cost vector.  ``ConditionEnvelope.catalysts``
is a real structured field, but until now it was only serialized and accounted, never asked "can a layperson get
this?".  A borrowing-hydrogen N-alkylation that DECLARES a Ru/Ir catalyst therefore sailed through the whole poor-man
stack as if it were kitchen-runnable.  This module is the missing organ.

What it claims, and what it deliberately does NOT (the soundness law).
The only honest thing an obtainability model may do is EXCLUDE (a catalyst the kitchen cannot get) or stay NEUTRAL
(a catalyst it positively recognizes as kitchen-obtainable).  It NEVER vouches feasibility: "the catalyst can be
bought" is a narrow claim about a substance, not a claim the reaction proceeds (chemoselectivity/sterics stay
unmodeled -- that is R50 KILL-1, a different and unsolved problem).  ``false-VOUCH >> false-UNRECOGNIZED``: wrongly
certifying a metal-catalyzed route as poor-man-reachable is the catastrophic error; wrongly excluding a reachable one
is the cheap error.  So the polarity here is a BURDEN-OF-PROOF FLIP (the R50 design gate's load-bearing fold): a
*declared* catalyst passes ONLY if it is POSITIVELY classified kitchen-obtainable; a declared catalyst we cannot
positively classify is BLOCKED, never silently waved through.  A declared-but-unrecognized catalyst is, in real
literature, overwhelmingly an industrial metal complex -- so blocking on uncertainty is not just safe, it is usually
right.  An *undeclared* catalyst (``catalysts == ()``) is genuine silence, not a claim, and is neutral.

How a catalyst is classified (structure/reality, derived -- never a per-reaction lookup, never a fuzzy name scan).
:func:`catalyst_availability` maps a catalyst NAME to an :class:`~smartchem.data.reagents.Availability` tier or
``None`` (unrecognized), by, in order:

1. an EXACT (case-normalized) match against the grounded commodity catalog by name
   (:data:`~smartchem.data.reagents.COMMODITY_REAGENTS`) -- the same per-substance obtainability catalog the
   consumed-reagent layer uses;
2. a grounded TRANSITION/HEAVY-metal guard: if a recognized substance's real element composition contains a
   catalytic transition, platinum-group, coinage, or heavy metal (a periodic-table fact, NOT a name), it is
   INDUSTRIAL -- "buy the reagent" never implies "possess the catalyst" (guards the reverse direction: a metal salt
   that is a cheap consumer commodity, e.g. a copper pool algaecide, must NOT read as a kitchen catalyst system);
3. a small curated table of common NAMED catalysts absent from the molecular catalog (Pd/C, Raney nickel, the
   eponymous metathesis/hydrogenation catalysts) -- exact normalized names + aliases only;
4. otherwise ``None`` (unrecognized).

There is deliberately NO substring/element-TOKEN scan over the free-text name: it is negation-blind
(`"palladium-free"` reads as palladium) and substring-catastrophic (`"os"` in *phosphoric*, `"ir"` in *stirring*) --
the recurring keyword-match lesson.  Coverage of exotic metal catalysts is carried by the burden-of-proof flip
above (unrecognized-but-declared -> BLOCK), not by an unsound recogniser.

Scope (honest, per the design gate).  The live consumer is the poor-man affordability frontier
(:func:`smartchem.service._affordability_frontier`), which is populated in ROUTES mode; a non-kitchen catalyst
becomes a hard blocker there.  Folding this verdict into the general combined ``fit_status`` is deliberately NOT done:
that verdict serves an arbitrary bench box (a real lab may own palladium), so an unconditional catalyst exclusion
there would be wrong -- a box-gated fold and DAG-mode reach are named follow-ups.  And because no registered reaction
declares a metal catalyst today (the honest data boundary: the whole EXCLUDE path is a guard ahead of its data), the
one live route that exercises this end-to-end -- isopentyl acetate's sourced ``conc. H2SO4`` -- is the NEUTRAL case
(sulfuric acid is HARDWARE-tier), correctly not blocked.
"""
from __future__ import annotations

from ..data.reagents import Availability, COMMODITY_REAGENTS

__all__ = [
    "NON_KITCHEN_METALS",
    "KITCHEN_TIERS",
    "catalyst_availability",
    "is_kitchen_obtainable",
    "is_obtainable_under",
    "route_catalyst_blockers",
]

#: The tiers a layperson can obtain (grocery / pharmacy / hardware / pool-garden).  INDUSTRIAL is the honest
#: opposite -- a chemical-supplier-only material, not a kitchen commodity.  Mirrors the poor-man census's kitchen set.
KITCHEN_TIERS: frozenset[Availability] = frozenset(
    a for a in Availability if a is not Availability.INDUSTRIAL
)

#: Element symbols of the catalytic metals a kitchen cannot furnish as a CATALYST SYSTEM -- the d-block transition
#: metals, the platinum-group + coinage metals, the catalytic f-block, and the heavy post-transition metals.  A
#: periodic-table fact (reality), NOT a reaction or a name.  Deliberately EXCLUDES the s-block (Na/K/Li/Ca/Mg/...):
#: alkali/alkaline-earth hydroxides/carbonates/acetates ARE genuine kitchen base catalysts (lye, washing soda), so a
#: metal check that blocked them would false-EXCLUDE a real kitchen catalyst.  Aluminium is also left out (Al foil is
#: a kitchen staple; a declared industrial Al catalyst like AlCl3 is caught by the burden-of-proof flip instead).
NON_KITCHEN_METALS: frozenset[str] = frozenset({
    # 1st-row d-block
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    # 2nd-row d-block (incl. platinum-group Ru/Rh/Pd + Ag)
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    # 3rd-row d-block (incl. platinum-group Os/Ir/Pt + Au)
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    # heavy post-transition metals used as Lewis-acid/oxidation catalysts
    "Sn", "Sb", "Pb", "Bi", "Tl",
    # f-block (lanthanide/actinide catalysts, e.g. Ce/Sm/La) -- none kitchen-obtainable
    "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Ac", "Th", "Pa", "U", "Np", "Pu",
})


def _norm(name: str) -> str:
    return name.strip().casefold()


#: canonical-normalized commodity name -> its curated Availability tier (grounded identity + tier).
_COMMODITY_BY_NAME: dict[str, Availability] = {_norm(r.name): r.availability for r in COMMODITY_REAGENTS}
#: canonical-normalized commodity name -> its element symbols (for the metal guard).
_COMMODITY_ELEMENTS: dict[str, frozenset[str]] = {
    _norm(r.name): frozenset(r.molecule.atoms) for r in COMMODITY_REAGENTS
}

#: Common NAMED catalysts absent from the consumed-reagent commodity catalog, keyed by exact normalized name +
#: aliases.  Every entry is INDUSTRIAL and justified by a grounded element fact (the metal it is built on is a
#: transition/platinum-group metal -- periodic-table reality, noted per row), NOT by matching a token in the string.
#: The table is a UX nicety that produces a precise "industrial metal catalyst" reason: SOUNDNESS does not depend on
#: its coverage, because any DECLARED catalyst absent from it still BLOCKS via the burden-of-proof flip in
#: :func:`route_catalyst_blockers` (unrecognized-but-declared -> not certifiable kitchen -> blocked).
_CATALYST_TABLE: dict[str, Availability] = {
    # palladium (Pd, platinum-group)
    "pd/c": Availability.INDUSTRIAL, "pd-c": Availability.INDUSTRIAL,
    "palladium on carbon": Availability.INDUSTRIAL, "palladium/carbon": Availability.INDUSTRIAL,
    "palladium on charcoal": Availability.INDUSTRIAL, "pdcl2": Availability.INDUSTRIAL,
    "palladium(ii) chloride": Availability.INDUSTRIAL, "palladium acetate": Availability.INDUSTRIAL,
    # platinum (Pt, platinum-group)
    "pto2": Availability.INDUSTRIAL, "platinum oxide": Availability.INDUSTRIAL,
    "platinum dioxide": Availability.INDUSTRIAL, "adams catalyst": Availability.INDUSTRIAL,
    "adams' catalyst": Availability.INDUSTRIAL, "chloroplatinic acid": Availability.INDUSTRIAL,
    "speier's catalyst": Availability.INDUSTRIAL, "karstedt's catalyst": Availability.INDUSTRIAL,
    # nickel (Ni, d-block)
    "raney nickel": Availability.INDUSTRIAL, "raney ni": Availability.INDUSTRIAL,
    # palladium, cont. (Lindlar is a lead-poisoned Pd/CaCO3 hydrogenation catalyst)
    "lindlar": Availability.INDUSTRIAL, "lindlar catalyst": Availability.INDUSTRIAL,
    # ruthenium (Ru, platinum-group) -- incl. the metathesis eponyms
    "rucl3": Availability.INDUSTRIAL, "ruthenium trichloride": Availability.INDUSTRIAL,
    "ruthenium(iii) chloride": Availability.INDUSTRIAL,
    "grubbs": Availability.INDUSTRIAL, "grubbs catalyst": Availability.INDUSTRIAL,
    "grubbs i": Availability.INDUSTRIAL, "grubbs ii": Availability.INDUSTRIAL,
    "grubbs 2": Availability.INDUSTRIAL, "grubbs 2nd generation catalyst": Availability.INDUSTRIAL,
    "hoveyda-grubbs catalyst": Availability.INDUSTRIAL, "hoveyda-grubbs": Availability.INDUSTRIAL,
    # rhodium (Rh, platinum-group)
    "wilkinson's catalyst": Availability.INDUSTRIAL, "wilkinsons catalyst": Availability.INDUSTRIAL,
    "rhcl3": Availability.INDUSTRIAL, "rhodium(iii) chloride": Availability.INDUSTRIAL,
    # iridium (Ir, platinum-group)
    "crabtree's catalyst": Availability.INDUSTRIAL, "crabtree catalyst": Availability.INDUSTRIAL,
    "ircl3": Availability.INDUSTRIAL,
    # manganese (Mn, d-block)
    "jacobsen catalyst": Availability.INDUSTRIAL, "jacobsen's catalyst": Availability.INDUSTRIAL,
    # titanium (Ti, d-block)
    "ziegler-natta": Availability.INDUSTRIAL, "ziegler-natta catalyst": Availability.INDUSTRIAL,
    "titanium tetrachloride": Availability.INDUSTRIAL, "ticl4": Availability.INDUSTRIAL,
    # -- kitchen-obtainable acid/base catalysts: formulae + common variants the molecular commodity catalog
    #    does not carry by name (so a step declaring "conc. H2SO4" or "HCl" is NOT false-excluded).  Each is a
    #    genuine layperson-obtainable mineral acid/base (drain opener / pool / masonry) -- the same curated
    #    obtainability judgment reagents.py makes, no metal center, so no reverse-vouch risk.
    "h2so4": Availability.HARDWARE, "conc. h2so4": Availability.HARDWARE, "conc h2so4": Availability.HARDWARE,
    "concentrated sulfuric acid": Availability.HARDWARE, "conc. sulfuric acid": Availability.HARDWARE,
    "dilute sulfuric acid": Availability.HARDWARE,
    "hcl": Availability.HARDWARE, "hydrochloric acid": Availability.HARDWARE, "conc. hcl": Availability.HARDWARE,
    "muriatic acid": Availability.HARDWARE,
    "naoh": Availability.HARDWARE, "koh": Availability.HARDWARE, "potassium hydroxide": Availability.HARDWARE,
    "lye": Availability.HARDWARE, "caustic soda": Availability.HARDWARE,
    "na2co3": Availability.GROCERY, "nahco3": Availability.GROCERY, "k2co3": Availability.HARDWARE,
    "glacial acetic acid": Availability.GROCERY, "vinegar": Availability.GROCERY,
    "citric acid": Availability.GROCERY,
}


def _has_non_kitchen_metal(elements: "frozenset[str]") -> bool:
    """True iff a grounded element set contains a catalytic transition/heavy/precious metal (see
    :data:`NON_KITCHEN_METALS`).  s-block alkali/alkaline-earth metals are deliberately absent from that set, so a
    kitchen base salt (NaOH, K2CO3, sodium acetate) is NOT flagged here."""
    return bool(elements & NON_KITCHEN_METALS)


def catalyst_availability(name: str) -> Availability | None:
    """The obtainability tier of a catalyst NAMED ``name``, or ``None`` when it is not positively recognized.

    ``None`` is NOT "kitchen-obtainable": it is "unrecognized", and a *declared* unrecognized catalyst is BLOCKED by
    :func:`route_catalyst_blockers` (the burden-of-proof flip).  Fail-closed on a non-string or empty/blank name.
    """
    if not isinstance(name, str):
        return None
    norm = _norm(name)
    if not norm:
        return None
    # 1. grounded commodity catalog (identity + curated tier), with the metal guard applied BEFORE the tier is
    #    returned: a recognized substance built on a catalytic metal is an industrial catalyst system regardless of
    #    how cheap the salt is to buy as a consumer commodity (KILL-2 guard -- "buy the reagent" != "possess the
    #    catalyst"; sound only for the EXCLUDE direction).
    if norm in _COMMODITY_BY_NAME:
        if _has_non_kitchen_metal(_COMMODITY_ELEMENTS[norm]):
            return Availability.INDUSTRIAL
        return _COMMODITY_BY_NAME[norm]
    # 2. curated named-catalyst table (industrial metal catalysts absent from the molecular catalog).
    if norm in _CATALYST_TABLE:
        return _CATALYST_TABLE[norm]
    # 3. fail-closed: unrecognized.
    return None


def is_obtainable_under(tier: Availability | None, allowed_tiers: frozenset[Availability]) -> bool:
    """True ONLY for a tier positively recognized as obtainable under ``allowed_tiers`` -- the profile-relative form
    (FREEZE decision 3) of the burden-of-proof flip's positive-classification test.  ``None`` (unrecognized) is
    always False regardless of ``allowed_tiers``: this function answers "is a POSITIVELY CLASSIFIED tier inside the
    allowed set", never "is the absence of a classification excusable" -- that call stays with the caller
    (:func:`route_catalyst_blockers`), which is where the burden-of-proof flip itself lives."""
    return tier is not None and tier in allowed_tiers


def is_kitchen_obtainable(tier: Availability | None) -> bool:
    """True ONLY for a tier positively recognized as layperson-obtainable (grocery/pharmacy/hardware/pool-garden).
    ``None`` (unrecognized) and ``INDUSTRIAL`` are both False -- an unrecognized catalyst is never assumed kitchen.

    The kitchen-specific instance of :func:`is_obtainable_under`; kept as its own name because it is the DEFAULT
    profile every existing caller (and ``route_catalyst_blockers``'s default parameter) still means."""
    return is_obtainable_under(tier, KITCHEN_TIERS)


def route_catalyst_blockers(
    route, allowed_tiers: frozenset[Availability] = KITCHEN_TIERS
) -> tuple[str, ...]:
    """The obtainability blockers for ``route`` under ``allowed_tiers``: one reason string per DECLARED catalyst not
    positively obtainable in that set, deduplicated and ordered.  ``allowed_tiers`` defaults to :data:`KITCHEN_TIERS`
    -- the poor-man profile -- so every existing call site (unchanged) gets the EXACT prior behavior and message
    text; a caller with a different capability profile (a lab that owns INDUSTRIAL reagents, or a stricter profile
    that excludes e.g. POOL_GARDEN) passes its own ``allowed_tiers`` and the SAME algorithm below runs against it
    (FREEZE decision 3 -- profile-relative obtainability, one implementation).

    The burden-of-proof flip (R50 KILL-1 design-gate fold) itself does not change with the profile: a step that
    declares no catalyst (``catalysts == ()``) is genuine silence and contributes nothing; a declared catalyst
    contributes a blocker UNLESS it is positively classified obtainable under ``allowed_tiers``.  A catalyst
    recognized at a tier outside the allowed set blocks with a precise reason; a declared-but-unrecognized catalyst
    blocks with an uncertainty reason regardless of profile (never a silent pass -- unrecognized stays
    ``false-VOUCH >> false-UNRECOGNIZED`` no matter who is asking).  These strings feed
    :func:`smartchem.service._affordability_frontier`'s ``hard_blockers`` (section-10.4 G6: a hard blocker dominates
    cost), so a route needing a catalyst the caller's profile cannot get sinks on that profile's affordability
    frontier.
    """
    is_default_profile = allowed_tiers == KITCHEN_TIERS
    reasons: set[str] = set()
    for step in route.steps:
        for cat in step.envelope.catalysts:
            tier = catalyst_availability(cat)
            if tier is None:
                reasons.add(
                    f"declared catalyst {cat!r} of uncertain obtainability -- cannot certify kitchen-reachable"
                )
            elif not is_obtainable_under(tier, allowed_tiers):
                if is_default_profile:
                    # Byte-stable on the default (kitchen) path: existing callers/tests pin this exact wording.
                    reasons.add(f"catalyst not kitchen-obtainable: {cat} [{tier.value}]")
                else:
                    allowed_str = ", ".join(sorted(a.value for a in allowed_tiers))
                    reasons.add(
                        f"catalyst not obtainable under allowed tiers ({allowed_str}): {cat} [{tier.value}]"
                    )
    return tuple(sorted(reasons))
