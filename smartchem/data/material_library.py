"""smartchem/data/material_library.py -- the curated ``StockMaterial`` library behind the isopentyl bench (gate #18).

**Chart note.** A route's ``MaterialRequirement`` is a demand; a ``StockMaterial`` is a real bottle that
either meets it or doesn't (:mod:`smartchem.experiment.stock`). Nobody upstream hands us a supplier
certificate of analysis, so this module stands in for one -- and Round V (barrier D7/D8) makes it say only
what its evidence supports. Every component carries:

* an honest :class:`~smartchem.material_spec.ConcentrationBasis` -- ``MASS_FRACTION`` only where the cited
  spec is a w/w assay (or the material is a solid, where an assay % can only be by mass), else ``UNKNOWN``;
* a typed, re-computable :class:`~smartchem.data.derived_evidence.IntervalEvidence` record whose closed
  kernel fixes the evidence KIND -- the interval the bottle carries IS the number that record recomputes,
  and it enters every material / profile / request digest above it.

Round V Lane C (source map + PubChem re-fetch) drove every change; see :data:`INTERVAL_EVIDENCE` and the
per-builder docstrings. Headlines: the 5% NaHCO3 wash is ASSUMED on an UNKNOWN basis (the source states no
basis or tolerance) so it can never certify; saturated NaCl collapses to the ONE sourced g/100 g-water
figure (36.0 g at 25 C; the old 35.7 lower input was a per-VOLUME figure); the isoamyl dilute bottle drops
its derived interval to UNKNOWN [0, 1] (its sources report g/100 mL and mg/L, never g/100 g -- F72); the
wash water no longer claims to be distilled.

**Boundary, stated loudly.** The supplier-spec locators (Fisher, Sigma-Aldrich, laballey) are Round-III
citations that could NOT be re-fetched in Round V (network-blocked); per Lane C's table the glacial acetic,
H2SO4 and MgSO4 intervals keep their sourced kinds on those citations. The isoamyl reagent assay, whose
Round-III record was internally inconsistent (three different labels), is ASSUMED.

Material STATES (barrier D5) are declared only where the bottle's own label/provenance states them, as
``USER_DECLARED`` (this module IS the operator's bench declaration): glacial acetic acid NEAT, reagent
isoamyl alcohol NEAT, anhydrous MgSO4 ANHYDROUS, saturated brine SATURATED + SOLUTION, the bicarbonate wash,
vinegar and the dilute isoamyl bottle SOLUTION.

Bottle PHASES (Round V X-high, barrier D18) follow the same declared-world convention: every curated bench bottle
declares ``phase_evidence=USER_DECLARED`` -- the phase on the bottle is the bench operator's own declaration about
their own stock, which CAN certify against a SOURCED phase demand (and only a sourced one: an author-inferred
requirement phase stays UNKNOWN whatever this bottle says). No phase VALUE changed.

Builders:

* :func:`isopentyl_fully_declared_inventory` -- the Round-III fully-declared bench (every reactant + auxiliary).
* :func:`isopentyl_lab_inventory` / :func:`isopentyl_vinegar_inventory` -- the two-bottle positive/control pair.
* :func:`isopentyl_insufficient_quantity_inventory` / :func:`isopentyl_wrong_phase_inventory` -- the
  forcing-matrix targeted negatives (one axis broken apiece: too little acid; a mis-phased alcohol).
"""
from __future__ import annotations

from ..experiment.stock import (
    MaterialComponent,
    Phase,
    STOCK_MATERIAL_SCHEMA,
    StockMaterial,
    StockQuantity,
)
from ..identity_parse import InputKind, resolve_target
from ..material_spec import (
    ConcentrationBasis,
    DilutionState,
    EvidenceKind,
    HydrationState,
    SaturationState,
    StateClaim,
)
from .derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput

__all__ = [
    "isoamyl_alcohol_reagent_grade",
    "isoamyl_alcohol_dilute_aqueous",
    "glacial_acetic_acid",
    "concentrated_sulfuric_acid",
    "household_white_vinegar",
    "sodium_bicarbonate_wash_5pct",
    "sodium_chloride_saturated_wash",
    "magnesium_sulfate_anhydrous",
    "wash_water",
    "isopentyl_fully_declared_inventory",
    "isopentyl_lab_inventory",
    "isopentyl_vinegar_inventory",
    "isopentyl_insufficient_quantity_inventory",
    "isopentyl_wrong_phase_inventory",
    "INTERVAL_EVIDENCE",
]

# -- canonical structures, resolved once through the SAME name-resolution path a route's search uses -----------
_ISOAMYL_ALCOHOL = resolve_target("isoamyl alcohol", InputKind.NAME).canonical()
_ACETIC_ACID = resolve_target("acetic acid", InputKind.NAME).canonical()
# "sulfuric acid" has no registered offline NAME entry -- resolved via its canonical SMILES instead.
_SULFURIC_ACID = resolve_target("OS(=O)(=O)O", InputKind.SMILES).canonical()
_WATER = resolve_target("water", InputKind.NAME).canonical()  # Round IV F44: water resolves -> structure-keyed stock

_ISOPENTYL_URL = (
    "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
    "Organic_Chemistry_Labs/Experiments/5:_Synthesis_of_Isopentyl_Acetate_(Experiment)"
)
_PC_NACL = (
    "https://pubchem.ncbi.nlm.nih.gov/compound/5234 (Solubility; HSDB 6368 citing CRC Handbook of Chemistry and "
    "Physics 94th ed. p. 4-89: '36.0 g/100 g of water at 25 °C')"
)
_FISHER_GLACIAL = "https://www.fishersci.com/shop/products/glacial-acetic-acid-usp-99-5-100-5-spectrum-11/18602907"
_SIGMA_GLACIAL = "https://www.sigmaaldrich.com/US/en/product/sigald/695092"
_SIGMA_H2SO4 = "https://www.sigmaaldrich.com/US/en/product/sigald/258105"
_SIGMA_MGSO4 = "https://www.sigmaaldrich.com/US/en/product/sigald/m7506"
_SIGMA_ISOAMYL = "https://www.sigmaaldrich.com/US/en/product/sigald/320021"
_FDA_VINEGAR = "https://www.fda.gov/media/71937/download (CPG Sec. 525.825: not less than 4 grams acetic acid per 100 mL)"

_NOT_REFETCHED = "supplier spec cited in Round III; not re-fetchable in Round V"


def _src(name: str, value: str, unit: InputUnit, locator: str, temperature_k: "str | None" = None) -> TypedInput:
    return TypedInput(name, value, unit, EvidenceKind.SOURCE_QUOTED, locator, temperature_k)


def _assumed(name: str, value: str, unit: InputUnit = InputUnit.FRACTION) -> TypedInput:
    return TypedInput(name, value, unit, EvidenceKind.ASSUMED)


# -- the evidence records (every production interval) ----------------------------------------------------------

# Glacial acetic acid: the cited compendial range 99.5-100.5 % w/w (titrimetric) CLAMPED to the physical bound 1.
_GLACIAL_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, basis=ConcentrationBasis.MASS_FRACTION,
    inputs=(_src("low", "99.5", InputUnit.PERCENT, _FISHER_GLACIAL),
            _src("high", "100.5", InputUnit.PERCENT, _FISHER_GLACIAL)),
    source_locators=(_FISHER_GLACIAL, _SIGMA_GLACIAL),
    domain_of_validity=f"as-supplied sealed USP/ACS glacial acetic acid, titrimetric % w/w ({_NOT_REFETCHED})",
)

# Conc. H2SO4: ACS reagent spec 95.0-98.0 % w/w (alkalimetric titration), quoted as-is.
_H2SO4_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, basis=ConcentrationBasis.MASS_FRACTION,
    inputs=(_src("low", "95.0", InputUnit.PERCENT, _SIGMA_H2SO4), _src("high", "98.0", InputUnit.PERCENT, _SIGMA_H2SO4)),
    source_locators=(_SIGMA_H2SO4,),
    domain_of_validity=f"as-supplied sealed ACS-grade sulfuric acid, % w/w ({_NOT_REFETCHED})",
)

# Anhydrous MgSO4: a quoted floor (>=97 %), the open upper end clipped to 1. Basis MASS_FRACTION because the
# material is a SOLID: an assay % of a solid reagent has no volume reading.
_MGSO4_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, basis=ConcentrationBasis.MASS_FRACTION,
    inputs=(_src("floor", "97", InputUnit.PERCENT, _SIGMA_MGSO4),),
    source_locators=(_SIGMA_MGSO4,),
    domain_of_validity=f"as-supplied sealed anhydrous MgSO4 (solid; assay % is by mass) ({_NOT_REFETCHED})",
)

# Isoamyl alcohol reagent grade: the Round-III record carried three mutually inconsistent labels, the 0.99
# ceiling was self-chosen, and a GC assay is area-% (basis unverified) -> ASSUMED on an UNKNOWN basis.
_ISOAMYL_REAGENT_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.ASSUMED_BAND_V1, basis=ConcentrationBasis.UNKNOWN,
    inputs=(TypedInput("low", "98", InputUnit.PERCENT_UNSTATED_BASIS, EvidenceKind.AUTHOR_INFERRED, _SIGMA_ISOAMYL),
            _assumed("high", "99", InputUnit.PERCENT_UNSTATED_BASIS)),
    source_locators=(_SIGMA_ISOAMYL,),
    domain_of_validity=(f"sealed reagent-grade isoamyl alcohol; floor read off a {_NOT_REFETCHED}; the 0.99 "
                        "ceiling is a self-chosen assumption; GC area-% basis unverified"),
)

# Isoamyl alcohol, dilute aqueous: PubChem CID 31260 reports 2 % @ 57 F (basis unstated), 2.67e4 mg/L @ 25 C,
# 26.7 mg/mL @ 25 C, 2.5 g/100 mL -- NEVER g/100 g water. No sourced density is on file, so no kernel can
# convert them (F72): the honest interval is UNKNOWN [0, 1]; the bottle's SOLUTION state + phase carry the negative.
_ISOAMYL_DILUTE_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.UNKNOWN_V1, basis=ConcentrationBasis.UNKNOWN,
    domain_of_validity=("no g/100 g-water solubility on file for 3-methyl-1-butanol (PubChem 31260 reports only "
                        "per-volume / unstated-basis figures) -- fraction UNKNOWN, never a relabelled mL"),
)
_ISOAMYL_DILUTE_WATER_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.UNKNOWN_V1, basis=ConcentrationBasis.UNKNOWN,
    domain_of_validity="balance of an unknown-composition dilute aqueous isoamyl alcohol -- UNKNOWN",
)

# Household vinegar: FDA's 4 g/100 mL floor is w/v (MASS_PER_VOLUME, g/mL); the 8 % ceiling is a chosen retail
# spread, so the whole band is ASSUMED (weakest link). Never a certifying interval -- the control BLOCKS on phase.
_VINEGAR_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.ASSUMED_BAND_V1, basis=ConcentrationBasis.MASS_PER_VOLUME,
    inputs=(_src("low", "4", InputUnit.PERCENT, _FDA_VINEGAR), _assumed("high", "8", InputUnit.PERCENT)),
    source_locators=(_FDA_VINEGAR,),
    domain_of_validity="US retail white vinegar, g acetic acid per mL (w/v); 8 g/100 mL ceiling ASSUMED",
)

# 5 % NaHCO3 wash: the source says only "5% sodium bicarbonate solution" -- no basis, no tolerance (Lane C,
# F68). Band [0.045, 0.055] and its w/w-reading water balance are ASSUMED on an UNKNOWN basis: never certifying.
_NAHCO3_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.ASSUMED_BAND_V1, basis=ConcentrationBasis.UNKNOWN,
    inputs=(TypedInput("nominal", "5", InputUnit.PERCENT_UNSTATED_BASIS, EvidenceKind.SOURCE_QUOTED, _ISOPENTYL_URL),
            _assumed("half_width", "0.5", InputUnit.PERCENT_UNSTATED_BASIS)),
    source_locators=(_ISOPENTYL_URL,),
    domain_of_validity="bench-prepared '5%' NaHCO3 wash; basis unstated by the source; +-0.5 width ASSUMED",
)
_NAHCO3_WATER_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.ASSUMED_BAND_V1, basis=ConcentrationBasis.UNKNOWN,
    inputs=(_assumed("low", "0.945"), _assumed("high", "0.955")),
    domain_of_validity="water balance under an ASSUMED binary w/w reading of the unstated '5%' -- ASSUMED",
)

# Saturated NaCl brine: the ONE sourced g/100 g-water figure is 36.0 at 25 C (PubChem 5234 / CRC). The old lower
# input 35.7 was per-VOLUME ('1 g dissolves in 2.8 mL water', 3.57e5 mg/L) and is dropped, not relabelled; the
# interval collapses to the single sourced value, 36/136 outward-rounded to [0.264705, 0.264706].
_NACL_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, basis=ConcentrationBasis.MASS_FRACTION,
    inputs=(_src("low", "36.0", InputUnit.G_PER_100G_SOLVENT, _PC_NACL, "298.15"),
            _src("high", "36.0", InputUnit.G_PER_100G_SOLVENT, _PC_NACL, "298.15")),
    source_locators=(_PC_NACL,),
    domain_of_validity="aqueous NaCl at saturation, 25 C, 1 atm (binary NaCl-water; no other T sourced)",
)
_NACL_WATER_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.COMPLEMENT_V1, basis=ConcentrationBasis.MASS_FRACTION, parent=_NACL_EVIDENCE,
    domain_of_validity="water balance of a BINARY saturated NaCl-water brine, 25 C",
)

# Wash water: the source says only "water" / "cold water" (never "distilled"); [0.99, 1.0] is an ASSUMED purity.
_WATER_EVIDENCE = IntervalEvidence.build(
    kernel=DerivationKernel.ASSUMED_BAND_V1, basis=ConcentrationBasis.UNKNOWN,
    inputs=(_assumed("low", "0.99"), _assumed("high", "1")),
    domain_of_validity="bench water of unstated grade; purity ASSUMED, nothing numeric sourced",
)

#: Public handle: every production interval's evidence, keyed ``material_id/component``.
INTERVAL_EVIDENCE: "dict[str, IntervalEvidence]" = {
    "glacial-acetic-acid-reagent-grade/acetic acid": _GLACIAL_EVIDENCE,
    "sulfuric-acid-concentrated-acs/sulfuric acid": _H2SO4_EVIDENCE,
    "magnesium-sulfate-anhydrous/magnesium sulfate": _MGSO4_EVIDENCE,
    "isoamyl-alcohol-reagent-grade/isoamyl alcohol": _ISOAMYL_REAGENT_EVIDENCE,
    "isoamyl-alcohol-dilute-aqueous/isoamyl alcohol": _ISOAMYL_DILUTE_EVIDENCE,
    "isoamyl-alcohol-dilute-aqueous/water": _ISOAMYL_DILUTE_WATER_EVIDENCE,
    "household-white-vinegar/acetic acid": _VINEGAR_EVIDENCE,
    "sodium-bicarbonate-5pct-aqueous/sodium bicarbonate": _NAHCO3_EVIDENCE,
    "sodium-bicarbonate-5pct-aqueous/water": _NAHCO3_WATER_EVIDENCE,
    "sodium-chloride-saturated-aqueous/sodium chloride": _NACL_EVIDENCE,
    "sodium-chloride-saturated-aqueous/water": _NACL_WATER_EVIDENCE,
    "wash-water/water": _WATER_EVIDENCE,
}


def _declared(state: "DilutionState | HydrationState | SaturationState", note: str) -> StateClaim:
    return StateClaim(state, EvidenceKind.USER_DECLARED, note)


#: Round V X-high (D18): the grade of every curated bottle's PHASE -- the same USER_DECLARED convention the
#: StateClaims above use, because this module IS the operator's bench declaration (the operator vouches for the
#: form of their own bottle; nobody else in this library does).
_BENCH_PHASE_EVIDENCE = EvidenceKind.USER_DECLARED


def isoamyl_alcohol_reagent_grade(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Isoamyl alcohol (3-methyl-1-butanol, CAS 123-51-3), reagent grade, ``[0.98, 0.99]`` -- ASSUMED, basis UNKNOWN.

    Round V: the Round-III record called this band DERIVED_WITH_ERROR, SOURCE_QUOTED and a "+-0.5% tolerance" at
    once; the 0.99 ceiling was self-chosen and a GC assay is area-%, so the band is ASSUMED on an UNKNOWN basis
    (it certifies nothing). The bottle is a neat reagent, declared ``NEAT`` by the bench (``USER_DECLARED``).
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "isoamyl-alcohol-reagent-grade",
        "Isoamyl alcohol (3-methyl-1-butanol), reagent grade",
        (MaterialComponent.evidenced(_ISOAMYL_ALCOHOL, "active", _ISOAMYL_REAGENT_EVIDENCE, states=(_declared(DilutionState.NEAT, "reagent-grade bottle, undiluted"),)),),
        Phase.LIQUID,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "assay interval [0.98, 0.99], basis UNKNOWN (GC area-%), evidence ASSUMED (ASSUMED_BAND_V1): floor read "
            f"off a {_NOT_REFETCHED}, ceiling self-chosen. Citation: {_SIGMA_ISOAMYL}"
        ),
        assay_method="GC (supplier); area-% basis not verified -- the carried band is ASSUMED",
        quantity=quantity,
        formulation_notes=("neat reagent bottle (Phase.LIQUID), NEAT declared by the bench",),
    )


def isoamyl_alcohol_dilute_aqueous(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Isoamyl alcohol as a DILUTE AQUEOUS formulation -- the wrong-phase targeted negative.

    Round V (F72): the Round-IV interval fed per-volume solubility figures (PubChem 31260: 2.5 g/100 mL, 26.7
    mg/mL, 2.67e4 mg/L, "2 %" of unstated basis) into a g/100 g-SOLVENT kernel. With no sourced density on file
    nothing converts them, so both components are UNKNOWN ``[0, 1]`` (``UNKNOWN_V1``). The negative is carried by
    what IS known: ``Phase.AQUEOUS_SOLUTION`` and the bench's ``SOLUTION`` declaration (contrary to NEAT).
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "isoamyl-alcohol-dilute-aqueous",
        "Isoamyl alcohol, dilute aqueous (wrong formulation)",
        (
            MaterialComponent.evidenced(_ISOAMYL_ALCOHOL, "active", _ISOAMYL_DILUTE_EVIDENCE, states=(_declared(DilutionState.SOLUTION, "dilute aqueous solution of the alcohol"),)),
            MaterialComponent.evidenced("water", "solvent", _ISOAMYL_DILUTE_WATER_EVIDENCE),
        ),
        Phase.AQUEOUS_SOLUTION,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "composition UNKNOWN [0, 1] (UNKNOWN_V1): PubChem CID 31260 reports aqueous solubility only per volume "
            "(g/100 mL, mg/L, mg/mL) or with unstated basis, and no sourced solution density is on file, so no "
            "mass fraction can be derived (F72). Built as the gate #18 WRONG-PHASE negative. Citation: "
            "https://pubchem.ncbi.nlm.nih.gov/compound/31260"
        ),
        quantity=quantity,
        formulation_notes=("dilute aqueous (Phase.AQUEOUS_SOLUTION) -- not the neat reagent",),
    )


def glacial_acetic_acid(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Glacial acetic acid (CAS 64-19-7), USP/ACS reagent grade, ``[0.995, 1.0]`` MASS_FRACTION -- CLAMPED.

    The cited compendial titrimetric range 99.5-100.5 % w/w is clipped to the physical bound 1.0 by
    ``CLAMP_TO_UNIT_INTERVAL_V1`` (a titration can read over 100 %; a mass fraction cannot). The bottle is
    declared ``NEAT`` by the bench (``USER_DECLARED``) -- "glacial" on a supplier label means undiluted acid,
    and the bench, not the compiler, is the one who says so.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "glacial-acetic-acid-reagent-grade",
        "Glacial acetic acid, USP/ACS reagent grade",
        (MaterialComponent.evidenced(_ACETIC_ACID, "active", _GLACIAL_EVIDENCE, states=(_declared(DilutionState.NEAT, "supplier label 'glacial' -- undiluted acid"),)),),
        Phase.LIQUID,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "assay [0.995, 1.0] MASS_FRACTION, CLAMPED (CLAMP_TO_UNIT_INTERVAL_V1) from the cited titrimetric "
            f"99.5-100.5 % w/w ({_NOT_REFETCHED}). Citations: {_FISHER_GLACIAL} ; {_SIGMA_GLACIAL}"
        ),
        assay_method="compendial titration, 99.5-100.5 % w/w clamped to <= 1.0",
        quantity=quantity,
        formulation_notes=("glacial (undiluted) acid, Phase.LIQUID; NEAT declared by the bench",),
    )


def concentrated_sulfuric_acid(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Concentrated sulfuric acid (CAS 7664-93-9), ACS reagent grade, ``[0.95, 0.98]`` MASS_FRACTION -- SOURCE_QUOTED.

    The cited ACS spec 95.0-98.0 % w/w quoted as-is (``IDENTITY_SOURCE_QUOTED_V1``). No state is declared: a
    95-98 % acid contains water, so it is neither honestly "neat" nor a declared "solution" here. Its GHS
    hazard (H314) feeds the containment axis.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "sulfuric-acid-concentrated-acs",
        "Sulfuric acid, concentrated, ACS reagent grade",
        (MaterialComponent.evidenced(_SULFURIC_ACID, "active", _H2SO4_EVIDENCE),),
        Phase.LIQUID,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "assay [0.95, 0.98] MASS_FRACTION, SOURCE_QUOTED (IDENTITY_SOURCE_QUOTED_V1) from the cited ACS "
            f"alkalimetric-titration spec 95.0-98.0 % w/w ({_NOT_REFETCHED}). Citation: {_SIGMA_H2SO4}"
        ),
        assay_method="ACS alkalimetric titration, 95.0-98.0 % w/w",
        quantity=quantity,
        formulation_notes=("concentrated acid catalyst, Phase.LIQUID; hazard (H314) feeds containment",),
    )


def household_white_vinegar() -> StockMaterial:
    """Household white vinegar -- the acetic-acid CONTROL bottle. ``[0.04, 0.08]`` MASS_PER_VOLUME, ASSUMED.

    FDA CPG 525.825's floor is 4 g acetic acid per 100 mL -- a w/v figure (``MASS_PER_VOLUME``, g/mL), not a
    mass fraction; the 8 g/100 mL ceiling is a chosen retail spread, so the band is ASSUMED. Keyed on the SAME
    canonical acetic-acid structure as :func:`glacial_acetic_acid`; declared ``Phase.AQUEOUS_SOLUTION`` and
    ``SOLUTION`` -- the control BLOCKS on phase/state, never on an assumed number.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "household-white-vinegar",
        "Household white vinegar (acetic acid, aqueous)",
        (MaterialComponent.evidenced(_ACETIC_ACID, "active", _VINEGAR_EVIDENCE, states=(_declared(DilutionState.SOLUTION, "vinegar is an aqueous solution"),)),),
        Phase.AQUEOUS_SOLUTION,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "acetic acid [0.04, 0.08] g/mL (MASS_PER_VOLUME), ASSUMED (ASSUMED_BAND_V1): floor = FDA CPG 525.825 "
            "4 g/100 mL minimum, ceiling = assumed retail spread. Citations: https://www.fda.gov/media/71937/download ; "
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC7353505/"
        ),
        assay_method="FDA 4 g/100 mL statutory minimum; retail ceiling assumed -- a condiment, never a reagent",
        formulation_notes=("aqueous solution (Phase.AQUEOUS_SOLUTION), a few % acetic acid",),
    )


# -- procedure-only auxiliaries: ionic or mixtures, unresolvable to a covalent Molecule, so NAME-keyed. -------


def sodium_bicarbonate_wash_5pct(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """"5%" aqueous sodium bicarbonate -- the neutralising wash. ``Phase.AQUEOUS_SOLUTION``, NAME-keyed.

    Round V (F68/F71/M76): the source's "25 mL of 5% sodium bicarbonate solution" states NO basis and NO
    tolerance. The carried band ``[0.045, 0.055]`` (and the water balance) is therefore ASSUMED on an UNKNOWN
    basis -- it can never certify a composition requirement, and ASSUMED-vs-ASSUMED agreement is UNKNOWN.
    The bench declares it a ``SOLUTION``.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "sodium-bicarbonate-5pct-aqueous",
        "Sodium bicarbonate, '5%' aqueous (neutralising wash)",
        (
            MaterialComponent.evidenced("sodium bicarbonate", "active", _NAHCO3_EVIDENCE, states=(_declared(DilutionState.SOLUTION, "bench-prepared aqueous wash"),)),
            MaterialComponent.evidenced("water", "solvent", _NAHCO3_WATER_EVIDENCE),
        ),
        Phase.AQUEOUS_SOLUTION,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "'5%' sodium bicarbonate in water, band [0.045, 0.055], basis UNKNOWN, ASSUMED (ASSUMED_BAND_V1): the "
            "nominal '5%' is quoted from the procedure, which states no basis (w/w vs w/v) and no tolerance; the "
            f"+-0.5 width is assumed. Citation: {_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=("'5%' aqueous NaHCO3 wash (basis unstated); ionic, name-keyed",),
    )


def sodium_chloride_saturated_wash(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Saturated aqueous sodium chloride (brine) -- the layer-separation wash. ``Phase.AQUEOUS_SOLUTION``.

    Round V: the ONE sourced g/100 g-water solubility is 36.0 g at 25 C (PubChem 5234, HSDB citing CRC). Through
    ``SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1`` (x = s/(s+100)) that is 36/136, outward-rounded to
    ``[0.264705, 0.264706]`` MASS_FRACTION, DERIVED; the water is its COMPLEMENT (binary brine). The Round-IV
    lower input 35.7 was a per-VOLUME figure and is dropped. The bench declares SATURATED + SOLUTION.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "sodium-chloride-saturated-aqueous",
        "Sodium chloride, saturated aqueous (brine wash)",
        (
            MaterialComponent.evidenced("sodium chloride", "active", _NACL_EVIDENCE, states=(
                _declared(SaturationState.SATURATED, "brine prepared to saturation by the bench"),
                _declared(DilutionState.SOLUTION, "aqueous brine"),
            )),
            MaterialComponent.evidenced("water", "solvent", _NACL_WATER_EVIDENCE),
        ),
        Phase.AQUEOUS_SOLUTION,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "NaCl [0.264705, 0.264706] MASS_FRACTION, DERIVED (SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1) "
            "from 36.0 g/100 g water at 25 C; water = COMPLEMENT. Valid at 25 C only (no other temperature "
            f"sourced). Citations: https://pubchem.ncbi.nlm.nih.gov/compound/5234 ; {_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=("saturated aqueous NaCl brine (layer-separation wash); ionic, name-keyed",),
    )


def magnesium_sulfate_anhydrous(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Anhydrous magnesium sulfate -- the drying agent. ``Phase.SOLID``, NAME-keyed.

    Assay ``[0.97, 1.0]`` MASS_FRACTION, CLAMPED from the cited ">=97 %" floor (the open upper end clipped to 1).
    The ANHYDROUS hydration state is a separate, positive bench declaration (D5) -- the assay number never
    discharges it (a heptahydrate can assay high as "magnesium sulfate").
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "magnesium-sulfate-anhydrous",
        "Magnesium sulfate, anhydrous (drying agent)",
        (MaterialComponent.evidenced("magnesium sulfate", "active", _MGSO4_EVIDENCE, states=(_declared(HydrationState.ANHYDROUS, "bottle labelled anhydrous"),)),),
        Phase.SOLID,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "assay [0.97, 1.0] MASS_FRACTION (solid), CLAMPED (CLAMP_TO_UNIT_INTERVAL_V1) from the cited >=97 % "
            f"floor ({_NOT_REFETCHED}). Citations: {_SIGMA_MGSO4} ; {_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=("anhydrous solid drying agent (Phase.SOLID); ionic, name-keyed",),
    )


def wash_water(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Water of unstated grade -- the aqueous partition and wash medium. ``Phase.LIQUID``, structure-keyed.

    Round V: the source says only "water" / "cold water", never "distilled"; the Round-IV "distilled/deionised"
    claim (and ``material_id`` ``wash-water-distilled``) are withdrawn. ``[0.99, 1.0]`` is an ASSUMED purity on
    an UNKNOWN basis -- possession, not an assay claim.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "wash-water",
        "Water (grade unstated)",
        (MaterialComponent.evidenced(_WATER, "solvent", _WATER_EVIDENCE),),
        Phase.LIQUID,
        phase_evidence=_BENCH_PHASE_EVIDENCE,
        provenance=(
            "bench water, grade unstated; [0.99, 1.0] purity ASSUMED (ASSUMED_BAND_V1), basis UNKNOWN -- the "
            f"procedure names only 'water'. Citation: {_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=("partition + wash water; grade unstated",),
    )


# -- inventories --------------------------------------------------------------------------------------------


def isopentyl_fully_declared_inventory() -> "tuple[StockMaterial, ...]":
    """The Round-III fully-declared Custom bench that stocks the WHOLE procedure.

    Every reactant AND every procedure-only auxiliary, each with a declared amount above its per-run draw:
    glacial acetic acid (20 mL drawn), isoamyl alcohol (15 mL), conc. H2SO4 (4 mL), '5%' NaHCO3 wash
    (2 x 25 mL), water, saturated NaCl (5 mL), anhydrous MgSO4 (2 g).
    """
    return (
        glacial_acetic_acid(quantity=StockQuantity.of("500", "mL")),
        isoamyl_alcohol_reagent_grade(quantity=StockQuantity.of("500", "mL")),
        concentrated_sulfuric_acid(quantity=StockQuantity.of("500", "mL")),
        sodium_bicarbonate_wash_5pct(quantity=StockQuantity.of("500", "mL")),
        sodium_chloride_saturated_wash(quantity=StockQuantity.of("250", "mL")),
        magnesium_sulfate_anhydrous(quantity=StockQuantity.of("250", "g")),
        wash_water(quantity=StockQuantity.of("1000", "mL")),
    )


def isopentyl_lab_inventory() -> "tuple[StockMaterial, ...]":
    """The two-bottle stocked bench: isoamyl alcohol + glacial acetic acid (reactants only)."""
    return (isoamyl_alcohol_reagent_grade(), glacial_acetic_acid())


def isopentyl_vinegar_inventory() -> "tuple[StockMaterial, ...]":
    """The CONTROL bench: isoamyl alcohol + household vinegar standing in for glacial acetic acid."""
    return (isoamyl_alcohol_reagent_grade(), household_white_vinegar())


def isopentyl_insufficient_quantity_inventory() -> "tuple[StockMaterial, ...]":
    """Targeted negative: the fully-declared bench with too LITTLE glacial acetic acid (10 mL vs the 20 mL draw)."""
    return (
        glacial_acetic_acid(quantity=StockQuantity.of("10", "mL")),  # < the 20 mL the source draws
        isoamyl_alcohol_reagent_grade(quantity=StockQuantity.of("500", "mL")),
        concentrated_sulfuric_acid(quantity=StockQuantity.of("500", "mL")),
        sodium_bicarbonate_wash_5pct(quantity=StockQuantity.of("500", "mL")),
        sodium_chloride_saturated_wash(quantity=StockQuantity.of("250", "mL")),
        magnesium_sulfate_anhydrous(quantity=StockQuantity.of("250", "g")),
        wash_water(quantity=StockQuantity.of("1000", "mL")),
    )


def isopentyl_wrong_phase_inventory() -> "tuple[StockMaterial, ...]":
    """Targeted negative: the fully-declared bench with a MIS-PHASED alcohol (dilute aqueous, declared SOLUTION)."""
    return (
        glacial_acetic_acid(quantity=StockQuantity.of("500", "mL")),
        isoamyl_alcohol_dilute_aqueous(quantity=StockQuantity.of("500", "mL")),  # wrong phase: aqueous, not neat
        concentrated_sulfuric_acid(quantity=StockQuantity.of("500", "mL")),
        sodium_bicarbonate_wash_5pct(quantity=StockQuantity.of("500", "mL")),
        sodium_chloride_saturated_wash(quantity=StockQuantity.of("250", "mL")),
        magnesium_sulfate_anhydrous(quantity=StockQuantity.of("250", "g")),
        wash_water(quantity=StockQuantity.of("1000", "mL")),
    )
