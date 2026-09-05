"""M-4b C1 — sourced condition annotation for decomposition edges (a seed table).

C0 gave the condition *algebra* (the Env comonad); this attaches *sourced* conditions to the
edges that a reference actually documents, and returns a loud `unknown()` for everything else —
which is the overwhelming majority. A conditions layer that guessed would be worse than the
formal engine that admits it knows only conservation, so this table is deliberately tiny and
every entry carries a provenance; the point is the *mechanism* (real reaction -> its real
conditions, everything else UNKNOWN), not coverage.

Matching is by the reaction's identity — the reactant composition, the multiset of reagent
compositions, and the multiset of product compositions — independent of how the equation is
scaled, so `paracetamol + H2O -> 4-aminophenol + acetic acid` is recognised however it is written.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import gcd
from types import SimpleNamespace

from .conditions import ConditionEnvelope
from .contracts import Digestible, EvidenceStatus
from .decompiler import Formula
from .process_constraints import Agitation, Attention, ProcessRequirements
from .provenance import SourceCitation, SourceReview

__all__ = [
    "ReactionDirection",
    "ConditionRecord",
    "assembly_conditions",
    "reaction_conditions",
    "SEED_CONDITIONS",
]


class ReactionDirection(str, Enum):
    """The direction in which a sourced condition record is licensed to fire.

    A balanced edge can always be reversed algebraically.  Its experimental conditions cannot:
    hydrolysis conditions are not amidation conditions, and a synthesis citation does not document the
    decomposition merely because the equation balances both ways.
    """

    DECOMPOSITION = "DECOMPOSITION"
    ASSEMBLY = "ASSEMBLY"


@dataclass(frozen=True)
class ConditionRecord(Digestible):
    """One provenance-bearing envelope plus the reaction direction(s) it actually documents.

    Assembly records additionally name the exact target and precursor structures.  Formula balance is a
    useful index, not chemical identity: without this structural selector a same-formula isomer could borrow
    another compound's bench conditions.
    """

    envelope: ConditionEnvelope
    directions: tuple[ReactionDirection, ...]
    assembly_target_name: str | None = None
    assembly_precursor_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.envelope) is not ConditionEnvelope or not self.envelope.is_declared:
            raise ValueError("a condition record must carry a declared ConditionEnvelope")
        if (
            type(self.directions) is not tuple
            or not self.directions
            or any(not isinstance(d, ReactionDirection) for d in self.directions)
        ):
            raise TypeError("directions must be a non-empty tuple of ReactionDirection values")
        object.__setattr__(self, "directions", tuple(sorted(set(self.directions), key=lambda d: d.value)))
        if ReactionDirection.ASSEMBLY in self.directions:
            if not isinstance(self.assembly_target_name, str) or not self.assembly_target_name:
                raise ValueError("an ASSEMBLY condition record needs an exact assembly_target_name")
            if (
                type(self.assembly_precursor_names) is not tuple
                or not self.assembly_precursor_names
                or any(not isinstance(n, str) or not n for n in self.assembly_precursor_names)
            ):
                raise ValueError("an ASSEMBLY condition record needs exact assembly_precursor_names")
            object.__setattr__(self, "assembly_precursor_names", tuple(sorted(self.assembly_precursor_names)))


def _composition_key(formula: Formula) -> tuple:
    return (formula.counts, formula.charge)


def _reaction_signature(edge) -> tuple:
    """Primitive signed stoichiometry by composition (formula index only, never structural identity)."""
    merged: dict[tuple[str, tuple], int] = {}

    def add(side: str, formula: Formula, coefficient: int) -> None:
        key = (side, _composition_key(formula))
        merged[key] = merged.get(key, 0) + coefficient

    add("L", edge.reactant, getattr(edge, "reactant_multiplicity", 1))
    for formula, coefficient in getattr(edge, "reagents", ()):
        add("L", formula, coefficient)
    for formula, coefficient in edge.products:
        add("R", formula, coefficient)
    divisor = 0
    for coefficient in merged.values():
        divisor = gcd(divisor, coefficient)
    divisor = divisor or 1
    return tuple(sorted((side, composition, coefficient // divisor) for (side, composition), coefficient in merged.items()))


def _sig(reactant: str, reagents: tuple[str, ...], products: tuple[str, ...]) -> tuple:
    edge = SimpleNamespace(
        reactant=Formula.parse(reactant),
        reactant_multiplicity=1,
        reagents=tuple((Formula.parse(r), 1) for r in reagents),
        products=tuple((Formula.parse(p), 1) for p in products),
    )
    return _reaction_signature(edge)


#: Sourced conditions, keyed by scale-independent reaction signature. Tiny by design; every entry
#: is provenance-bearing and `EXPERIMENTAL` (a decorator never claims a certified-lane status).
SEED_CONDITIONS: dict[tuple, ConditionRecord] = {
    # Paracetamol hydrolysis -> 4-aminophenol + acetic acid. Only what the literature states is
    # claimed: an acidic aqueous medium. No temperature/catalyst value is fabricated.
    _sig("C8H9NO2", ("H2O",), ("C6H7NO", "C2H4O2")): ConditionRecord(
        ConditionEnvelope(
            medium="aqueous, acidic",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance="acidic amide hydrolysis of paracetamol; DOI 10.1039/C3AY40747K",
            source=SourceCitation(
                "https://doi.org/10.1039/C3AY40747K", SourceReview.ACCEPTED
            ),
        ),
        (ReactionDirection.DECOMPOSITION,),
    ),
    # Anhydrous backbone C8H9NO2 -> C6H7NO + C2H2O. Its REVERSE (assembly) is the ketene
    # acetylation of 4-aminophenol -- ketene acetylates the amine to give paracetamol. Ketene is
    # an acutely toxic reactive gas generated and consumed in situ; N- vs O-selectivity is a
    # structure-level concern this formula-level edge does not resolve.
    _sig("C8H9NO2", (), ("C6H7NO", "C2H2O")): ConditionRecord(
        ConditionEnvelope(
            medium="ketene generated and consumed in situ (not storable)",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: ketene acetylation of 4-aminophenol; ketene is acutely toxic and "
                "generated in situ (NJ RTK / CAMEO; see hazards). Formula-level edge does not distinguish "
                "N- vs O-acetylation"
            ),
        ),
        (ReactionDirection.ASSEMBLY,),
        "paracetamol",
        ("4-aminophenol", "ketene"),
    ),
    # Mediated C8H9NO2 + C2H4O2 -> C6H7NO + C4H6O3. Its REVERSE (assembly) is the standard lab
    # synthesis: 4-aminophenol + acetic anhydride -> paracetamol + acetic acid.
    _sig("C8H9NO2", ("C2H4O2",), ("C6H7NO", "C4H6O3")): ConditionRecord(
        ConditionEnvelope(
            medium="aqueous or neat; addition/temperature controlled",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: standard acetic-anhydride acetylation of 4-aminophenol "
                "(ACS J. Chem. Educ., DOI 10.1021/acs.jchemed.0c01512); acetic anhydride reacts with water, "
                "so addition and temperature are controlled in practice"
            ),
            source=SourceCitation(
                "https://doi.org/10.1021/acs.jchemed.0c01512", SourceReview.ACCEPTED
            ),
            # PROCESS-FIT-02: the poor-man's whole-process record for this route, SOURCED from an
            # open-license bench procedure (never fabricated; every value below traces to a quote,
            # a DERIVED open-vessel constant, or is left UNKNOWN).
            process=ProcessRequirements(
                min_elapsed_minutes=84.0,   # SOURCED floor = the 4 timed steps: 4-min charcoal swirl + 10-min acetylation + ~55-min ("almost an hour") ice-bath crystallization + 15-min recrystallization cooling
                min_active_minutes=14.0,    # SOURCED floor: 4-min charcoal swirl + 10-min acetylation swirl (the two hands-on timed steps)
                attention=Attention.PERIODIC,     # active swirl, then "allow to sit ... for almost an hour", then filter
                agitation=Agitation.MANUAL,       # every agitation verb is a hand action ("swirl", "stir with a glass rod")
                equipment=(
                    "erlenmeyer flask", "steam bath", "glass rod", "ice bath",
                    "fluted filter paper", "buchner funnel", "water aspirator",
                ),
                workup_included=True,             # crystallize + Buchner vacuum filtration + wash + recrystallize
                peak_temperature_k=373.15,        # SOURCED: steam bath / "boiling water"
                max_pressure_atm=1.0,             # DERIVED: open-vessel benchtop (ambient)
                provenance=(
                    "whole-process record, SOURCED from LibreTexts 'Synthesis of Acetaminophen (Experiment)' "
                    "(CC BY-NC-SA 4.0); reaction identity + temperature cross-checked against Kurnianto & "
                    "Fahrurrozi, J. Rekayasa Proses (Univ. Gadjah Mada, CC BY-SA 4.0). SOURCED: peak 373.15 K "
                    "(steam bath), MANUAL agitation, PERIODIC attention, workup included. min_elapsed 84 min / "
                    "min_active 14 min are SOURCED LOWER BOUNDS (timed steps); the whole-step CEILING (incl. "
                    "untimed drying) is UNKNOWN, so elapsed/active ceilings stay UNKNOWN -- a floor can only "
                    "exclude, never confirm a fit. max_pressure 1 atm DERIVED (open vessel); min_pressure "
                    "(aspirator vacuum, unquantified) left UNKNOWN. 'house vacuum line' is a source-accepted "
                    "equivalent to the water aspirator."
                ),
                source=SourceCitation(
                    "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
                    "Organic_Chemistry_Labs/Experiments/2:__Synthesis_of_Acetaminophen_(Experiment)",
                    SourceReview.ACCEPTED,
                ),
            ),
        ),
        (ReactionDirection.ASSEMBLY,),
        "paracetamol",
        ("4-aminophenol", "acetic anhydride"),
    ),
    # Mediated C7H14O2 + H2O -> C5H12O + C2H4O2. Its REVERSE (assembly) is the acid-catalyzed
    # Fischer esterification: isopentyl alcohol + acetic acid -> isopentyl acetate + water.
    _sig("C7H14O2", ("H2O",), ("C5H12O", "C2H4O2")): ConditionRecord(
        ConditionEnvelope(
            medium="neat; acid-catalyzed (conc. H2SO4); reflux then fractional distillation",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: acid-catalyzed Fischer esterification of isopentyl alcohol with "
                "acetic acid; LibreTexts 'Synthesis of Isopentyl Acetate (Experiment)' (CC BY-NC-SA 4.0)"
            ),
            source=SourceCitation(
                "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
                "Organic_Chemistry_Labs/Experiments/5:_Synthesis_of_Isopentyl_Acetate_(Experiment)",
                SourceReview.ACCEPTED,
            ),
            # PROCESS-FIT-02 whole-process record, SOURCED (open license); single-sourced (see provenance).
            process=ProcessRequirements(
                min_elapsed_minutes=60.0,   # SOURCED floor: the quoted 1-hour reflux (untimed workup/distillation on top -> ceiling UNKNOWN)
                attention=Attention.PERIODIC,     # reflux then leave; return for the sep-funnel extractions and distillation
                agitation=Agitation.MANUAL,       # sep-funnel extractions are hand-shaken (reflux itself uses boiling stones)
                equipment=(
                    "round-bottom flask", "reflux condenser", "heating mantle", "boiling stones",
                    "separatory funnel", "distillation apparatus", "thermometer",
                ),
                workup_included=True,             # sequential extractions + MgSO4 dry + fractional distillation
                peak_temperature_k=416.15,        # DERIVED from the SOURCED distillation fraction (134-143 C); ~143 C peak
                min_pressure_atm=1.0, max_pressure_atm=1.0,  # DERIVED: open reflux/distillation at ambient
                provenance=(
                    "whole-process record, SOURCED from LibreTexts 'Synthesis of Isopentyl Acetate (Experiment)' "
                    "(CC BY-NC-SA 4.0). SINGLE-SOURCED within the open literature: the located cross-source "
                    "(Sci. Rep. 2023, PMC9935880, CC BY 4.0) is a DIFFERENT (solvent-free, seashell-catalyzed) "
                    "method, so it corroborates reaction identity only, not these conventional bench numbers. "
                    "SOURCED: MANUAL agitation, PERIODIC attention, workup included. min_elapsed 60 min is the "
                    "SOURCED 1-hour reflux LOWER BOUND; the whole-step CEILING (untimed workup + distillation) "
                    "is UNKNOWN, so elapsed ceiling stays UNKNOWN. peak 416.15 K DERIVED from the sourced "
                    "134-143 C distillation fraction; pressure ambient (open apparatus)."
                ),
            ),
        ),
        (ReactionDirection.ASSEMBLY,),
        "isopentyl acetate",
        ("acetic acid", "isopentyl alcohol"),
    ),
    # methyl salicylate (oil of wintergreen): salicylic acid + methanol -> methyl salicylate + water.
    # ROUND 11 item 4: a THIRD sourced whole-process record. Every value is quote-backed and passed an
    # adversarial fabrication guard (a MANUAL agitation value was KILLED as a workup-step misattribution).
    _sig("C8H8O3", ("H2O",), ("C7H6O3", "CH4O")): ConditionRecord(
        ConditionEnvelope(
            medium="warm water bath (60-65 C); Fischer esterification of salicylic acid with methanol",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: Fischer esterification of salicylic acid with methanol (methyl salicylate, "
                "oil of wintergreen); LibreTexts 'Experiment 731: Esters' (Los Medanos College, CC BY)"
            ),
            source=SourceCitation(
                "https://chem.libretexts.org/Courses/Los_Medanos_College/"
                "Chemistry_6_and_Chemistry_7_Combined_Laboratory_Manual_(Los_Medanos_College)/"
                "01:_Experiments/1.31:_Experiment_731_Esters__1_0",
                SourceReview.ACCEPTED,
            ),
            # PROCESS-FIT record, SOURCED (CC BY); every value quote-backed + adversarially verified (item 4).
            process=ProcessRequirements(
                min_elapsed_minutes=10.0,   # SOURCED floor: "Heat ... for 10 minutes or longer" (whole-step ceiling untimed -> UNKNOWN)
                attention=Attention.PERIODIC,   # SOURCED: "Be sure to monitor the temperature to maintain it within the specified range."
                equipment=(
                    "hot plate", "250 mL beaker (warm water bath)", "small (~10 mL) test tubes",
                    "test tube clamp", "test tube rack", "pipet", "watch glass",
                ),
                # HONEST: the ONLY post-reaction step the source describes is a QUALITATIVE detection
                # (add water, two layers form, pipet the top layer to a watch glass and smell) -- NOT a
                # preparative isolation/drying/purification, so whole-step workup coverage stays UNKNOWN.
                # workup_included defaults to False -> this record can EXCLUDE or be UNKNOWN, never a false FITS.
                peak_temperature_k=338.15,   # SOURCED: 65 C, top of the quoted 60-65 C water-bath range
                min_pressure_atm=1.0, max_pressure_atm=1.0,   # DERIVED: open test-tube heating at ambient
                provenance=(
                    "whole-process record, SOURCED from LibreTexts 'Experiment 731: Esters' (Los Medanos College, "
                    "CC BY). Every value is quote-backed and passed an adversarial fabrication guard (item 4): "
                    "min_elapsed 10 min is the SOURCED heating LOWER BOUND ('for 10 minutes or longer'); the "
                    "whole-step CEILING is untimed -> UNKNOWN (a floor can only EXCLUDE). PERIODIC attention and "
                    "peak 338.15 K (65 C) are directly quoted. agitation is UNKNOWN: the source's only mixing "
                    "instruction is a POST-REACTION workup dilution, not a reaction condition (the guard KILLED a "
                    "MANUAL agitation value as a step misattribution). workup_included=False: the post-reaction step "
                    "is a QUALITATIVE detection (phase-separate + smell), not a preparative isolation, so whole-step "
                    "workup coverage is honestly UNKNOWN. Pressure ambient (open apparatus). SINGLE-SOURCED."
                ),
            ),
        ),
        (ReactionDirection.ASSEMBLY,),
        "methyl salicylate",
        ("methanol", "salicylic acid"),
    ),
}


def reaction_conditions(
    edge, *, direction: ReactionDirection = ReactionDirection.DECOMPOSITION, losses: tuple = (),
) -> ConditionEnvelope:
    """The conditions sourced for ``edge`` in exactly ``direction``, else loud ``unknown()``.

    The default preserves the decompiler-facing API: an edge is read in its written decomposition direction.
    Retrosynthesis callers MUST request :attr:`ReactionDirection.ASSEMBLY`; algebraic reversibility is not
    experimental provenance.

    ``losses`` (EVD-KEY-01): if a section-5.3 BLOCKER forbids a ``"conditions"`` claim on this identity, no sourced
    envelope survives (section 5.3) -- ``unknown()`` is returned before the lookup.
    """
    from .identity import is_blocked
    if not isinstance(direction, ReactionDirection):
        raise TypeError("direction must be a ReactionDirection")
    if is_blocked(tuple(losses), "conditions"):
        return ConditionEnvelope.unknown()
    record = SEED_CONDITIONS.get(_reaction_signature(edge))
    if record is None or direction not in record.directions:
        return ConditionEnvelope.unknown()
    if direction is ReactionDirection.ASSEMBLY:
        # Formula-only callers cannot prove the structural selector.  Retrosynthesis must use
        # assembly_conditions(capped), which has the bond graphs needed to do so.
        return ConditionEnvelope.unknown()
    return record.envelope


def assembly_conditions(capped, *, losses: tuple = ()) -> ConditionEnvelope:
    """Conditions for reversing one structural capped scission, only after exact identity matches.

    Any unresolved structure or selector mismatch returns ``unknown()``.  This deliberately refuses a
    formula-only fallback: paracetamol and 4-aminophenyl acetate are both C8H9NO2 but are not interchangeable.

    ``losses`` (EVD-KEY-01): a section-5.3 BLOCKER for ``"conditions"`` refuses a sourced envelope (section 5.3),
    even when the structure resolves and the selector matches -- the dropped feature (stereo/isotope/charge) is one
    the sourced bench conditions may depend on.

    Expected-absence contract (ERR-EVIDENCE-01): the ONLY reasons this returns ``unknown()`` are the explicit,
    anticipated ones below -- a section-5.3 ``"conditions"`` blocker, no seed record for the reaction signature, a
    record that carries no ASSEMBLY direction, an unresolved reactant/precursor structure, or a selector-name
    mismatch.  It does NOT catch exceptions.  An unexpected fault in signature computation or structure resolution
    is an INTERNAL DEFECT, not the scientific statement "conditions unknown"; it propagates to the
    ``ERROR_INTERNAL`` / exit-70 boundary rather than being laundered into an epistemic UNKNOWN.
    """
    from .identity import is_blocked
    from .structure import resolve_structure

    if is_blocked(tuple(losses), "conditions"):
        return ConditionEnvelope.unknown()
    record = SEED_CONDITIONS.get(_reaction_signature(capped.forget()))
    if record is None or ReactionDirection.ASSEMBLY not in record.directions:
        return ConditionEnvelope.unknown()
    target = resolve_structure(capped.reactant)
    precursors = tuple(resolve_structure(m) for m in capped.products)
    if target is None or any(p is None for p in precursors):
        return ConditionEnvelope.unknown()
    names = tuple(sorted(p.name for p in precursors if p is not None))
    if target.name != record.assembly_target_name or names != record.assembly_precursor_names:
        return ConditionEnvelope.unknown()
    return record.envelope
