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

from .conditions import ConditionEnvelope, Interval
from .contracts import Digestible, EvidenceStatus
from .decompiler import Formula
from .procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureOperation,
)
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


# -- v0.8 Round II: typed procedure evidence, migrated from the same accepted primary sources --------------------
# The four sourced routes' whole-process records above are free-text ProcessRequirements; these author the
# STRUCTURED procedure the same accepted primary source specifies, so PROCESS_SPECIFIED becomes decidable from
# structured fields (plan docs/research/V0_8_ROUND_II_PROCEDURE_EVIDENCE_PLAN_v0.1.md, section 3). Every value
# traces to a quote from the cited page; each EXPLICIT_NOT_APPLICABLE carries the justification that closes it out
# (silence is UNKNOWN_MISSING, never N/A). These attach ONLY via assembly_conditions (structurally guarded), never
# reaction_conditions (isomer-blind) -- Wave A Lane F KILL 2 / mutation M19.
_ISOPENTYL_URL = (
    "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
    "Organic_Chemistry_Labs/Experiments/5:_Synthesis_of_Isopentyl_Acetate_(Experiment)"
)
_ASPIRIN_URL = (
    "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
    "Organic_Chemistry_Labs/Experiments/1:__Synthesis_of_Aspirin_(Experiment)"
)
_ACETAMINOPHEN_URL = (
    "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
    "Organic_Chemistry_Labs/Experiments/2:__Synthesis_of_Acetaminophen_(Experiment)"
)

# Isopentyl acetate -- a COMPLETE, sourced preparative procedure. reaction_type is recognized (esterification
# makes water), conditions are sourced, and this procedure is complete -> the round's real PROCESS_SPECIFIED
# positive. Quantities, ordered operations, workup and analytical acceptance all quoted from the LibreTexts page.
_ISOPENTYL_PROCEDURE = ProcedureEvidence(
    reaction_scope="Fischer esterification: isopentyl alcohol + acetic acid -> isopentyl acetate + water",
    source=SourceCitation(_ISOPENTYL_URL, SourceReview.ACCEPTED),
    scale=EvidenceField.present(
        "15 mL (12.2 g, 0.138 mol) isopentyl alcohol; 20 mL (21 g, 0.35 mol) glacial acetic acid; "
        "4 mL conc. H2SO4 (alcohol:acid ~ 1:2.5, acid in excess)", _ISOPENTYL_URL),
    operations=(
        ProcedureOperation(
            ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
            materials=("isopentyl alcohol", "acetic acid", "sulfuric acid"),
            quantity=EvidenceField.present("15 mL alcohol + 20 mL glacial acetic acid + 4 mL conc. H2SO4", _ISOPENTYL_URL),
            rate=EvidenceField.present("combine alcohol and acid, then add conc. H2SO4 with caution", _ISOPENTYL_URL),
            apparatus=("100-mL round-bottom flask",), locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=2, kind=OperationKind.HOLD, role=OperationRole.REACTION,
            temperature=EvidenceField.present("reflux (boiling mixture on a heating mantle)", _ISOPENTYL_URL),
            agitation=EvidenceField.present("boiling stones for even reflux", _ISOPENTYL_URL),
            duration=EvidenceField.present(Interval(60.0, 60.0, "min"), _ISOPENTYL_URL),
            endpoint=EvidenceField.present("reflux the mixture for 1 hour", _ISOPENTYL_URL),
            apparatus=("reflux condenser", "heating mantle", "boiling stones"), locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=3, kind=OperationKind.COOL, role=OperationRole.OTHER,
            temperature=EvidenceField.present("cool to room temperature", _ISOPENTYL_URL), locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=4, kind=OperationKind.SEPARATE, role=OperationRole.OTHER, materials=("cold water",),
            quantity=EvidenceField.present("55 mL cold water + 10 mL rinse; separate the lower aqueous layer", _ISOPENTYL_URL),
            apparatus=("separatory funnel",), locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=5, kind=OperationKind.ADD, role=OperationRole.WASH, materials=("5% sodium bicarbonate solution",),
            quantity=EvidenceField.present("25 mL of 5% sodium bicarbonate, twice", _ISOPENTYL_URL),
            endpoint=EvidenceField.present("wash until the aqueous layer is basic to litmus", _ISOPENTYL_URL),
            locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=6, kind=OperationKind.ADD, role=OperationRole.WASH, materials=("water",),
            quantity=EvidenceField.present("25 mL water", _ISOPENTYL_URL), locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=7, kind=OperationKind.ADD, role=OperationRole.WASH, materials=("saturated aqueous sodium chloride",),
            quantity=EvidenceField.present("5 mL saturated NaCl to aid layer separation (swirl, do not shake)", _ISOPENTYL_URL),
            locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=8, kind=OperationKind.DRY, role=OperationRole.OTHER, materials=("anhydrous magnesium sulfate",),
            quantity=EvidenceField.present("2 g anhydrous magnesium sulfate", _ISOPENTYL_URL), locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=9, kind=OperationKind.DISTILL, role=OperationRole.OTHER,
            endpoint=EvidenceField.present("collect the fraction between 134 and 143 C", _ISOPENTYL_URL),
            apparatus=("distillation apparatus", "thermometer"), locator=_ISOPENTYL_URL),
        ProcedureOperation(
            ordinal=10, kind=OperationKind.VERIFY, role=OperationRole.OTHER, locator=_ISOPENTYL_URL),
    ),
    quench=EvidenceField.not_applicable(
        _ISOPENTYL_URL,
        "the complete sourced sequence proceeds reflux -> cool -> aqueous partition -> bicarbonate/water/brine "
        "washes -> dry -> distill; the acid catalyst is removed by the bicarbonate wash and the source specifies "
        "no separate reaction quench"),
    workup_isolation=EvidenceField.present(
        "separatory-funnel partition, bicarbonate/water/brine washes, magnesium-sulfate drying", _ISOPENTYL_URL),
    separation=EvidenceField.present("separatory funnel; separate the lower aqueous layer", _ISOPENTYL_URL),
    wash=EvidenceField.present("2 x 25 mL 5% NaHCO3, 25 mL water, 5 mL saturated NaCl", _ISOPENTYL_URL),
    drying=EvidenceField.present("2 g anhydrous magnesium sulfate", _ISOPENTYL_URL),
    purification=EvidenceField.present("fractional distillation, 134-143 C fraction", _ISOPENTYL_URL),
    analytical_verification=EvidenceField.present(
        "weigh and calculate percent yield; obtain an infrared spectrum", _ISOPENTYL_URL),
)

# Aspirin -- a COMPLETE, sourced preparative procedure, but reaction_type is UNRECOGNIZED (anhydride
# transacylation expels acetic acid, not water, so it fails the acyl-condensation shape guard,
# feasibility.py:_is_intermolecular_acyl_condensation). Its coarse tier stays FORMAL_CANDIDATE while its
# process/workup evidence is visibly SATISFIED -- the one-rung-higher non-monotonicity witness. NO reaction
# class #18 is added to prettify the tier.
_ASPIRIN_PROCEDURE = ProcedureEvidence(
    reaction_scope="acetylation: salicylic acid + acetic anhydride -> acetylsalicylic acid + acetic acid",
    source=SourceCitation(_ASPIRIN_URL, SourceReview.ACCEPTED),
    scale=EvidenceField.present(
        "2.0 g (0.015 mol) salicylic acid; 5 mL (0.05 mol) acetic anhydride; 5 drops conc. H2SO4 "
        "(anhydride:acid ~ 3.3:1)", _ASPIRIN_URL),
    operations=(
        ProcedureOperation(
            ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
            materials=("salicylic acid", "acetic anhydride", "sulfuric acid"),
            quantity=EvidenceField.present("2.0 g salicylic acid + 5 mL acetic anhydride + 5 drops conc. H2SO4", _ASPIRIN_URL),
            agitation=EvidenceField.present("swirl gently until the salicylic acid dissolves", _ASPIRIN_URL),
            apparatus=("125-mL Erlenmeyer flask",), locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=2, kind=OperationKind.HOLD, role=OperationRole.REACTION,
            temperature=EvidenceField.present("steam bath, gentle heating", _ASPIRIN_URL),
            endpoint=EvidenceField.present("heat gently on the steam bath for at least 10 minutes", _ASPIRIN_URL),
            apparatus=("steam bath",), locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=3, kind=OperationKind.COOL, role=OperationRole.OTHER,
            temperature=EvidenceField.present(
                "cool to room temperature, scratch with a glass rod, then ice bath until crystallization completes", _ASPIRIN_URL),
            apparatus=("glass rod", "ice bath"), locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=4, kind=OperationKind.FILTER, role=OperationRole.OTHER, materials=("water",),
            quantity=EvidenceField.present("add 50 mL water, cool in an ice bath, then vacuum filter", _ASPIRIN_URL),
            apparatus=("Buchner funnel",), locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=5, kind=OperationKind.ADD, role=OperationRole.WASH, materials=("cold water",),
            quantity=EvidenceField.present("rinse the crystals several times with 5 mL portions of cold water", _ASPIRIN_URL),
            locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=6, kind=OperationKind.HEAT, role=OperationRole.RECRYSTALLIZATION, materials=("ethyl acetate",),
            temperature=EvidenceField.present("dissolve in a minimum (2-3 mL) of hot ethyl acetate", _ASPIRIN_URL),
            locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=7, kind=OperationKind.COOL, role=OperationRole.RECRYSTALLIZATION,
            temperature=EvidenceField.present("cool to room temperature, then in an ice bath", _ASPIRIN_URL),
            apparatus=("ice bath",), locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=8, kind=OperationKind.FILTER, role=OperationRole.RECRYSTALLIZATION, materials=("petroleum ether",),
            quantity=EvidenceField.present("collect by vacuum filtration, rinse with a few mL cold petroleum ether", _ASPIRIN_URL),
            apparatus=("Buchner funnel",), locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=9, kind=OperationKind.DRY, role=OperationRole.OTHER,
            quantity=EvidenceField.present("air dry the crystals", _ASPIRIN_URL), locator=_ASPIRIN_URL),
        ProcedureOperation(
            ordinal=10, kind=OperationKind.VERIFY, role=OperationRole.OTHER, locator=_ASPIRIN_URL),
    ),
    quench=EvidenceField.not_applicable(
        _ASPIRIN_URL,
        "worked up by dilution, ice-bath crystallization and filtration; the sourced procedure specifies no "
        "separate reaction quench"),
    workup_isolation=EvidenceField.present(
        "dilute with water, vacuum (Buchner) filtration, cold-water rinse, air dry", _ASPIRIN_URL),
    separation=EvidenceField.not_applicable(
        _ASPIRIN_URL,
        "the solid product is isolated by filtration; the sourced procedure uses no liquid-liquid partition"),
    wash=EvidenceField.present(
        "cold-water rinses of the crystals; cold petroleum-ether rinse after recrystallization", _ASPIRIN_URL),
    drying=EvidenceField.present("air dry the collected crystals", _ASPIRIN_URL),
    purification=EvidenceField.present(
        "recrystallize from hot ethyl acetate (after a bicarbonate/HCl reprecipitation)", _ASPIRIN_URL),
    analytical_verification=EvidenceField.present(
        "weigh; melting point (lit mp 135 C); percent yield; ferric-chloride purity test", _ASPIRIN_URL),
)

# Paracetamol (acetic-anhydride route) -- the flagship non-monotonicity witness: a COMPLETE, sourced preparative
# procedure whose reaction_type is UNRECOGNIZED for the same structural reason as aspirin. Coarse tier stays
# FORMAL_CANDIDATE; process/workup evidence is visibly SATISFIED. Procedure source is the LibreTexts acetaminophen
# page (the envelope's CONDITIONS citation is a different accepted source -- the ACS DOI -- so the procedure
# carries its OWN accepted locator, never borrowing the conditions citation; plan D4 / Lane F KILL 1(c)).
_PARACETAMOL_PROCEDURE = ProcedureEvidence(
    reaction_scope="acetylation: 4-aminophenol + acetic anhydride -> paracetamol + acetic acid",
    source=SourceCitation(_ACETAMINOPHEN_URL, SourceReview.ACCEPTED),
    scale=EvidenceField.present(
        "2.1 g p-aminophenol; 35 mL water; 1.5 mL conc. HCl; 0.3-0.4 g Norit charcoal; 2.5 g sodium acetate "
        "trihydrate in 7.5 mL water (buffer); 2.0 mL acetic anhydride", _ACETAMINOPHEN_URL),
    operations=(
        ProcedureOperation(
            ordinal=1, kind=OperationKind.ADD, role=OperationRole.OTHER,
            materials=("p-aminophenol", "water", "hydrochloric acid"),
            quantity=EvidenceField.present("2.1 g p-aminophenol + 35 mL water + 1.5 mL conc. HCl, swirl to dissolve", _ACETAMINOPHEN_URL),
            apparatus=("125-mL Erlenmeyer flask",), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=2, kind=OperationKind.ADD, role=OperationRole.OTHER, materials=("decolorizing charcoal (Norit)",),
            quantity=EvidenceField.present("0.3-0.4 g Norit; swirl on a steam bath for 4-8 minutes", _ACETAMINOPHEN_URL),
            apparatus=("steam bath",), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=3, kind=OperationKind.FILTER, role=OperationRole.OTHER,
            quantity=EvidenceField.present("gravity filter through fluted paper while warm to remove charcoal", _ACETAMINOPHEN_URL),
            apparatus=("fluted filter paper",), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=4, kind=OperationKind.ADD, role=OperationRole.REACTION,
            materials=("sodium acetate buffer", "acetic anhydride"),
            quantity=EvidenceField.present("add 8.8 mL sodium-acetate buffer in one portion, then 2.0 mL acetic anhydride", _ACETAMINOPHEN_URL),
            rate=EvidenceField.present("add the buffer in one portion, then immediately add the anhydride while swirling", _ACETAMINOPHEN_URL),
            locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=5, kind=OperationKind.HOLD, role=OperationRole.REACTION,
            temperature=EvidenceField.present("steam bath", _ACETAMINOPHEN_URL),
            agitation=EvidenceField.present("swirl vigorously", _ACETAMINOPHEN_URL),
            duration=EvidenceField.present(Interval(10.0, 10.0, "min"), _ACETAMINOPHEN_URL),
            endpoint=EvidenceField.present("continue heating on the steam bath, swirling vigorously, for 10 minutes", _ACETAMINOPHEN_URL),
            apparatus=("steam bath",), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=6, kind=OperationKind.COOL, role=OperationRole.OTHER,
            temperature=EvidenceField.present("ice-water bath; stir until crystallization begins; sit ~1 hour", _ACETAMINOPHEN_URL),
            apparatus=("ice bath", "glass rod"), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=7, kind=OperationKind.FILTER, role=OperationRole.OTHER,
            quantity=EvidenceField.present("Buchner vacuum filtration", _ACETAMINOPHEN_URL),
            apparatus=("Buchner funnel", "water aspirator"), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=8, kind=OperationKind.ADD, role=OperationRole.WASH, materials=("cold water",),
            quantity=EvidenceField.present("rinse the crystals once with a few mL of cold water", _ACETAMINOPHEN_URL),
            locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=9, kind=OperationKind.DRY, role=OperationRole.OTHER,
            quantity=EvidenceField.present("air dry under vacuum", _ACETAMINOPHEN_URL), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=10, kind=OperationKind.HEAT, role=OperationRole.RECRYSTALLIZATION, materials=("water",),
            temperature=EvidenceField.present("dissolve in the minimum amount of hot (boiling) water, add another 2 mL hot water", _ACETAMINOPHEN_URL),
            locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=11, kind=OperationKind.COOL, role=OperationRole.RECRYSTALLIZATION,
            temperature=EvidenceField.present("cool with an ice bath until crystallization ceases", _ACETAMINOPHEN_URL),
            duration=EvidenceField.present(Interval(15.0, 15.0, "min"), _ACETAMINOPHEN_URL),
            apparatus=("ice bath",), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=12, kind=OperationKind.FILTER, role=OperationRole.RECRYSTALLIZATION, materials=("cold water",),
            quantity=EvidenceField.present("collect the crystals, rinse once with a few mL cold water, air dry", _ACETAMINOPHEN_URL),
            apparatus=("Buchner funnel",), locator=_ACETAMINOPHEN_URL),
        ProcedureOperation(
            ordinal=13, kind=OperationKind.VERIFY, role=OperationRole.OTHER, locator=_ACETAMINOPHEN_URL),
    ),
    quench=EvidenceField.not_applicable(
        _ACETAMINOPHEN_URL,
        "worked up by ice-bath crystallization and filtration; the sourced procedure specifies no separate "
        "reaction quench"),
    workup_isolation=EvidenceField.present(
        "ice-bath crystallization, Buchner vacuum filtration, cold-water rinse, air dry", _ACETAMINOPHEN_URL),
    separation=EvidenceField.not_applicable(
        _ACETAMINOPHEN_URL,
        "the solid product is isolated by filtration; the sourced procedure uses no liquid-liquid partition"),
    wash=EvidenceField.present("rinse the crystals with cold water (crude and recrystallized)", _ACETAMINOPHEN_URL),
    drying=EvidenceField.present("air dry under vacuum", _ACETAMINOPHEN_URL),
    purification=EvidenceField.present("recrystallize from hot water", _ACETAMINOPHEN_URL),
    analytical_verification=EvidenceField.present(
        "weigh; melting point (lit mp 169-170.5 C); percent yield", _ACETAMINOPHEN_URL),
)


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
            procedure=_PARACETAMOL_PROCEDURE,
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
            # STRUCTURED catalyst (CATALYST-OBTAIN-01): a quote-read of the sourced medium's "conc. H2SO4" -- the
            # regenerated Fischer acid catalyst, promoted from free text to the structured field so the obtainability
            # model (smartchem.experiment.catalyst_availability) can see it.  Sulfuric acid is a HARDWARE-tier
            # commodity (drain opener / battery acid) -> kitchen-obtainable, so this route is correctly NOT blocked.
            # Only this ONE record carries a structured catalyst: methyl salicylate/paracetamol name no specific
            # catalyst species in their sourced quotes ("Fischer esterification" / "acid-catalyzed" alone), so naming
            # one there would be an inference, not a quote -- they stay catalysts=().
            catalysts=("sulfuric acid",),
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: acid-catalyzed Fischer esterification of isopentyl alcohol with "
                "acetic acid; LibreTexts 'Synthesis of Isopentyl Acetate (Experiment)' (CC BY-NC-SA 4.0); "
                "structured catalysts=(sulfuric acid) is a quote-read of the sourced 'conc. H2SO4' medium"
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
            procedure=_ISOPENTYL_PROCEDURE,
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
    # ROUND 12 item 3: a FOURTH sourced whole-process record -- ASPIRIN, the flagship reaction (unblocked for
    # compilation in ROUND 11 by resonance-canonical identity).  Unlike methyl salicylate, this source describes a
    # genuinely PREPARATIVE workup (vacuum filter -> recrystallise -> dry -> weigh -> melting point), so
    # workup_included=True and this record can produce a real FITS -- the first sourced FITS demo on aspirin itself.
    # Every value re-verified by fetching the LibreTexts page directly and grepping the raw HTML for each quote.
    _sig("C9H8O4", ("C2H4O2",), ("C7H6O3", "C4H6O3")): ConditionRecord(
        ConditionEnvelope(
            medium="steam bath; acetylation of salicylic acid with acetic anhydride (acid-catalyzed)",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: acetylation of salicylic acid with acetic anhydride -> acetylsalicylic acid "
                "(aspirin) + acetic acid; LibreTexts 'Experiment 1: Synthesis of Aspirin' (Chickos/Garin/D'Souza, "
                "University of Missouri-St. Louis, CC BY-NC-SA 4.0)"
            ),
            source=SourceCitation(
                "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
                "Organic_Chemistry_Labs/Experiments/1:__Synthesis_of_Aspirin_(Experiment)",
                SourceReview.ACCEPTED,
            ),
            # PROCESS-FIT record, SOURCED (CC BY-NC-SA 4.0); every value quote-backed against the raw page (item 3).
            process=ProcessRequirements(
                min_elapsed_minutes=10.0,   # SOURCED floor: "Heat the flask gently on the steam bath for at least 10 minutes."
                attention=Attention.PERIODIC,   # INTERPRETIVE (existing convention): swirl -> heat 10 min -> cool -> scratch/wait -> ice bath -> filter (monitor-and-return)
                agitation=Agitation.MANUAL,   # SOURCED: "swirl the flask gently until the salicylic acid dissolves."
                equipment=(
                    "125-mL Erlenmeyer flask", "steam bath", "glass rod", "ice bath",
                    "Buchner funnel", "150 mL beaker", "dropper",
                ),
                # SOURCED preparative workup: "Vacuum filter the product using a Buchner funnel", recrystallise
                # ("heating on a steam bath. Cool ... in a ice-bath. Collect the product by vacuum filtration"),
                # "air dry", then "weigh ... determine its melting point ... calculate the percentage yield".
                workup_included=True,
                peak_temperature_k=373.15,   # DERIVED (existing convention): "steam bath" = open boiling-water bath ~100 C; no numeric T quoted
                min_pressure_atm=1.0, max_pressure_atm=1.0,   # DERIVED: open-vessel benchtop at ambient
                provenance=(
                    "whole-process record, SOURCED from LibreTexts 'Experiment 1: Synthesis of Aspirin' "
                    "(CC BY-NC-SA 4.0). Re-verified by fetching the page and grepping each quote from raw HTML "
                    "(item 3). min_elapsed 10 min is the SOURCED heating LOWER BOUND ('for at least 10 minutes'); "
                    "the whole-step CEILING is untimed -> UNKNOWN (a floor can only EXCLUDE). agitation=MANUAL "
                    "('swirl the flask gently'). Equipment nouns each directly quoted. workup_included=True: the "
                    "source describes a genuinely PREPARATIVE isolation (Buchner vacuum filtration -> recrystallise "
                    "-> air dry -> weigh -> melting point -> percent yield), UNLIKE the qualitative methyl-salicylate "
                    "prep -- so this record CAN produce a FITS. attention PERIODIC and peak 373.15 K ('steam bath') "
                    "are the same interpretive/derivational convention the three existing records use, not new "
                    "fabricated values. Pressure ambient (open apparatus). SINGLE-SOURCED. NOTE: the source uses a "
                    "1:3.3 salicylic-acid:anhydride molar excess (normal for this prep); the composition-only _sig is "
                    "unaffected, but a future quantity-weighted demo must read the real ratio, not 1:1."
                ),
            ),
            procedure=_ASPIRIN_PROCEDURE,
        ),
        (ReactionDirection.ASSEMBLY,),
        "aspirin",
        ("acetic anhydride", "salicylic acid"),   # MUST be sorted (assembly_conditions compares sorted precursor names)
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
