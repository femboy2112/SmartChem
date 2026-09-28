"""smartchem/data/material_library.py -- a curated DERIVED_WITH_ERROR ``StockMaterial`` library (gate #18).

**Chart note.** A route's ``MaterialRequirement`` is a demand; a ``StockMaterial`` is a real bottle that
either meets it or doesn't (:mod:`smartchem.experiment.stock`). Nobody upstream is going to hand us a
supplier certificate of analysis, so this module IS the certificate -- each bottle keyed on canonical
STRUCTURE where the species resolves (:meth:`~smartchem.experiment.stock.MaterialComponent.of_molecule`,
never a fragile name string), each assay interval traced to a public citation, each honestly labelled
``DERIVED_WITH_ERROR`` -- an uncertainty band derived from a sourced spec, not a source-quoted point value,
and never a fabricated 100%.

Round III (D1) retires the reaction-class assay floor and moves the isopentyl-acetate FIT positive onto a
**fully-declared Custom bench**: every reactant AND every procedure-only auxiliary (the H2SO4 catalyst, the
bicarbonate/water/brine washes, the magnesium-sulfate drier) is declared with a matching phase/formulation
and, where the source gives an amount, a :class:`StockQuantity`. That is strictly harder than the retired
floor -- the bench earns FIT only by actually stocking the whole procedure.

The discrimination that is gate #18's whole point survives, and now on PHASE first (D1/D4):

* **glacial acetic acid** -- ``[0.995, 1.0]`` NEAT ``Phase.LIQUID`` (the compendial "glacial" formulation).
* **household white vinegar** -- ``[0.04, 0.08]`` ``Phase.AQUEOUS_SOLUTION``. Keyed on the SAME canonical
  acetic-acid structure as glacial, so it is a real competing bottle in
  :meth:`~smartchem.experiment.stock.StockMaterial.satisfies`, not a strawman: a pure-acetic requirement
  BLOCKS against it on assay, and a LIQUID-phase requirement BLOCKS against it on phase. A structure key
  cannot be argued with the way a name can.

The procedure-only auxiliaries (NaHCO3, NaCl, MgSO4, water) are IONIC / mixtures, unresolvable to a
covalent :class:`~smartchem.category.Molecule` (fabricating one would be an ionic-lattice lie, banned by
D1). They are therefore NAME-keyed (``MaterialComponent.known`` / ``unknown_fraction``) -- the weaker but
honest possession key -- and matched by name + phase/formulation, not by a proven assay.

Sourced amounts (all quoted from the LibreTexts isopentyl-acetate experiment page,
https://chem.libretexts.org/.../Experiments/5:_Synthesis_of_Isopentyl_Acetate_(Experiment)): 15 mL alcohol,
20 mL glacial acetic acid, 4 mL conc. H2SO4, 2 x 25 mL 5% NaHCO3, 25 mL water, 5 mL saturated NaCl, 2 g
anhydrous MgSO4. Each stocked bottle declares an amount comfortably above its per-run draw.

Builders:

* :func:`isopentyl_fully_declared_inventory` -- the Round-III FIT positive (every reactant + auxiliary).
* :func:`isopentyl_lab_inventory` / :func:`isopentyl_vinegar_inventory` -- the pre-existing two-bottle
  positive/control pair, exported names preserved.
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
]

# -- canonical structures, resolved once through the SAME name-resolution path a route's search uses -----------
# (resolve_target(name, InputKind.NAME).canonical()) -- so a StockMaterial's structure key is built off the
# identical Molecule identity a searched route's leaf_inputs carries, never a hand-rolled lookalike.

_ISOAMYL_ALCOHOL = resolve_target("isoamyl alcohol", InputKind.NAME).canonical()
_ACETIC_ACID = resolve_target("acetic acid", InputKind.NAME).canonical()
# "sulfuric acid" has no registered offline NAME entry (it exists only as a smartchem.data.reagents
# CommodityReagent, constructed in-place there) -- resolved via its canonical SMILES instead, verified to
# share the identical canonical digest as that CommodityReagent's own constructed molecule.
_SULFURIC_ACID = resolve_target("OS(=O)(=O)O", InputKind.SMILES).canonical()

_ISOPENTYL_URL = (
    "https://chem.libretexts.org/Ancillary_Materials/Laboratory_Experiments/Wet_Lab_Experiments/"
    "Organic_Chemistry_Labs/Experiments/5:_Synthesis_of_Isopentyl_Acetate_(Experiment)"
)


def isoamyl_alcohol_reagent_grade(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Isoamyl alcohol (3-methyl-1-butanol, CAS 123-51-3), ACS/reagent grade, assay ``[0.98, 0.99]``.

    DERIVED_WITH_ERROR: three major suppliers converge on a 98-99.5% band; 0.98 is the conservative
    published floor, 0.99 the conservative ceiling below their upper spec (never rounding up past what was
    actually quoted). Per D1 the alcohol's COMPATIBILITY mechanism is PHASE (a neat ``Phase.LIQUID``
    reagent, which the source names without a numeric purity); the assay here is a real, cited supplier
    spec that reinforces it, not a fabricated ceiling invented to force FIT. ``quantity`` is optional --
    ``None`` keeps the bare pre-Round-III bottle; the fully-declared bench passes a stocked amount.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "isoamyl-alcohol-reagent-grade",
        "Isoamyl alcohol (3-methyl-1-butanol), ACS reagent grade",
        (MaterialComponent.of_molecule(_ISOAMYL_ALCOHOL, "active", 0.98, 0.99),),
        Phase.LIQUID,
        provenance=(
            "DERIVED_WITH_ERROR assay interval [0.98, 0.99] (mass fraction), source class: chemical-"
            "supplier product spec (Sigma-Aldrich, Fisher Scientific, Scharlab ACS), confidence HIGH. "
            "Citations: https://www.sigmaaldrich.com/US/en/product/sigald/320021 ; "
            "https://www.scharlab.com/in/en/chemicals/solvents-reagent-grade/"
            "isoamyl_alcohol_for_analysis_expertq_r_acs_7836"
        ),
        assay_method=(
            "DERIVED_WITH_ERROR: +-0.5% ACS reagent-grade tolerance band around a GC assay per Sigma-Aldrich "
            "product sheet -- derived from the published spec, not a single source-quoted point value"
        ),
        quantity=quantity,
        formulation_notes=(
            "neat reagent (Phase.LIQUID) -- the D1 compatibility mechanism for the alcohol",
            "curated for SmartChem v0.9 gate #18 (isopentyl acetate CAPABILITY_FIT positive)",
        ),
    )


def isoamyl_alcohol_dilute_aqueous(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Isoamyl alcohol as a DILUTE AQUEOUS formulation -- the wrong-phase targeted negative.

    Isoamyl alcohol is only sparingly water-soluble (~2-3 g / 100 mL at 20 C), so a genuinely aqueous
    bottle sits at a couple of percent by mass. This is not a reagent feed: it is the honest "wrong
    formulation" bottle for the forcing matrix -- ``Phase.AQUEOUS_SOLUTION`` fails the alcohol's neat-LIQUID
    phase requirement (D4). No fabricated physical fact (isoamyl alcohol is not somehow a solid); a real,
    inferior formulation that BLOCKS on the one axis the alcohol carries a requirement for.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "isoamyl-alcohol-dilute-aqueous",
        "Isoamyl alcohol, dilute aqueous (wrong formulation)",
        (
            MaterialComponent.of_molecule(_ISOAMYL_ALCOHOL, "active", 0.02, 0.03),
            MaterialComponent.known("water", "solvent", 0.97, 0.98),
        ),
        Phase.AQUEOUS_SOLUTION,
        provenance=(
            "DERIVED_WITH_ERROR assay interval [0.02, 0.03] (mass fraction, at/near the aqueous solubility "
            "limit ~2-3 g/100 mL at 20 C), source class: solubility reference, confidence MEDIUM. Citation: "
            "https://pubchem.ncbi.nlm.nih.gov/compound/31260 (3-methyl-1-butanol, water solubility). Built "
            "as the gate #18 WRONG-PHASE negative -- an aqueous formulation cannot stand in for the neat "
            "reagent"
        ),
        quantity=quantity,
        formulation_notes=(
            "dilute aqueous (Phase.AQUEOUS_SOLUTION) -- fails the neat-LIQUID phase requirement (D4)",
        ),
    )


def glacial_acetic_acid(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Glacial acetic acid (CAS 64-19-7), reagent grade (USP/ACS), assay ``[0.995, 1.0]`` -- CLAMPED.

    DERIVED_WITH_ERROR: the source (USP/ACS/BP/Ph.Eur. compendial spec, titrimetric) reads "99.5-100.5%".
    A titration-verified assay CAN legitimately read a hair over 100% on a real bottle (non-volatile-residue
    and congealing-point checks bound the impurity, not the titration ceiling) -- but a MASS FRACTION cannot
    physically exceed 1.0, and ``MaterialComponent`` enforces exactly that (``0 <= fraction <= 1.0``, raises
    above it). The upper bound is therefore CLAMPED to 1.0 here: [0.995, 1.0], never [0.995, 1.005]. The
    clamp discards only the physically-impossible sliver; the lower bound is untouched. Per D1 "glacial" is
    a sourced compendial FORMULATION -- a neat ``Phase.LIQUID`` reagent -- and it is that phase, not only
    the assay, that BLOCKS the vinegar control.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "glacial-acetic-acid-reagent-grade",
        "Glacial acetic acid, USP/ACS reagent grade",
        (MaterialComponent.of_molecule(_ACETIC_ACID, "active", 0.995, 1.0),),
        Phase.LIQUID,
        provenance=(
            "DERIVED_WITH_ERROR assay interval [0.995, 1.0] (mass fraction; CLAMPED from the source's "
            "titrimetric 99.5-100.5% -- a mass fraction cannot exceed 1.0), source class: compendial spec "
            "(USP/ACS/BP), confidence HIGH. Citations: "
            "https://www.fishersci.com/shop/products/glacial-acetic-acid-usp-99-5-100-5-spectrum-11/18602907 ; "
            "https://www.sigmaaldrich.com/US/en/product/sigald/695092"
        ),
        assay_method=(
            "DERIVED_WITH_ERROR: USP/ACS/BP/Ph.Eur. compendial titration, source range 99.5-100.5% clamped "
            "to <=1.0 mass fraction (titrimetric assay can read fractionally over 100% on a real bottle; a "
            "fraction cannot)"
        ),
        quantity=quantity,
        formulation_notes=(
            "glacial = neat reagent (Phase.LIQUID) per the USP/ACS compendial term -- the D1 formulation "
            "that discriminates glacial from vinegar on phase, not only assay",
            "curated for SmartChem v0.9 gate #18 (isopentyl acetate CAPABILITY_FIT positive)",
        ),
    )


def concentrated_sulfuric_acid(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Concentrated sulfuric acid (CAS 7664-93-9), ACS reagent grade, assay ``[0.95, 0.98]``, LIQUID.

    DERIVED_WITH_ERROR: ACS Committee on Analytical Reagents published spec (alkalimetric titration; density
    is unreliable as an assay proxy above ~93%). The isopentyl-acetate route declares H2SO4 as the acid
    CATALYST; under Round III (D9) it is a procedure-only, resolvable species whose GHS hazard (H314, now in
    :mod:`smartchem.data.hazards`) feeds the containment axis -- so a no-hood bench BLOCKS on it. Its
    obtainability is priced by the procurement axis, not the material assay axis.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "sulfuric-acid-concentrated-acs",
        "Sulfuric acid, concentrated, ACS reagent grade",
        (MaterialComponent.of_molecule(_SULFURIC_ACID, "active", 0.95, 0.98),),
        Phase.LIQUID,
        provenance=(
            "DERIVED_WITH_ERROR assay interval [0.95, 0.98] (mass fraction), source class: compendial spec "
            "(ACS), confidence HIGH. Citations: "
            "https://www.sigmaaldrich.com/US/en/product/sigald/258105 ; "
            "https://www.laballey.com/products/sulfuric-acid-acs-grade"
        ),
        assay_method=(
            "DERIVED_WITH_ERROR: ACS Committee on Analytical Reagents alkalimetric-titration spec, "
            "95-98% nominal (density unreliable as an assay proxy at this concentration)"
        ),
        quantity=quantity,
        formulation_notes=(
            "concentrated (Phase.LIQUID) acid catalyst; hazard (H314) feeds containment per D9",
        ),
    )


def household_white_vinegar() -> StockMaterial:
    """Household white vinegar, food-grade, assay ``[0.04, 0.08]`` -- the acetic-acid CONTROL bottle.

    DERIVED_WITH_ERROR: FDA CPG 525.825 mandates a 4% minimum; most retail vinegar sits 5-7%; the interval
    is widened to 8% to stay honest about the retail spread rather than quoting a single "typical" number.
    Keyed on the SAME canonical acetic-acid structure as :func:`glacial_acetic_acid` and declared
    ``Phase.AQUEOUS_SOLUTION`` -- so a route needing the glacial-grade feed BLOCKS against it TWICE over: on
    assay (best case 8% << 99%) AND on phase (aqueous, not neat LIQUID). Not a free pass because "it's
    acetic acid too".
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "household-white-vinegar",
        "Household white vinegar (acetic acid, aqueous)",
        (MaterialComponent.of_molecule(_ACETIC_ACID, "active", 0.04, 0.08),),
        Phase.AQUEOUS_SOLUTION,
        provenance=(
            "DERIVED_WITH_ERROR assay interval [0.04, 0.08] (mass fraction), source class: FDA regulation + "
            "supplier labeling, confidence HIGH. Citations: "
            "https://www.fda.gov/media/71937/download ; "
            "https://ucanr.edu/site/uc-master-food-preservers-central-sierra/article/"
            "central-sierra-about-vinegar-read-label-edc ; "
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC7353505/"
        ),
        assay_method=(
            "DERIVED_WITH_ERROR: FDA CPG 525.825 4% statutory minimum, retail range widened to 8% (titration "
            "/ enzymatic quantification per PMC7353505) -- a food condiment, never a reagent-grade feedstock"
        ),
        formulation_notes=(
            "aqueous solution (Phase.AQUEOUS_SOLUTION), a few % acetic acid -- fails glacial on BOTH phase "
            "and assay",
            "curated for SmartChem v0.9 gate #18 vinegar CONTROL (same acetic-acid structure key as glacial)",
        ),
    )


# -- procedure-only auxiliaries (D1/D2): ionic or mixtures, unresolvable to a covalent Molecule, so NAME-keyed.
# Matched by name + phase/formulation (possession), never a proven assay. A fabricated covalent SMILES for an
# ionic lattice is banned (D1); identity-by-name is the honest carrier. The sourced formulation words ("5%",
# "saturated", "anhydrous") and phases come straight from the LibreTexts procedure.


def sodium_bicarbonate_wash_5pct(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """5% aqueous sodium bicarbonate -- the neutralising wash. ``Phase.AQUEOUS_SOLUTION``, NAME-keyed.

    The procedure calls for "5% sodium bicarbonate solution" and uses it twice (2 x 25 mL). "5%" is taken
    as a mass fraction with an honest +-0.5% band (a bench-prepared wash is not assayed to better); the
    balance is water. Ionic (Na+ / HCO3-), so ``identity=None``-class and name-keyed per D1.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "sodium-bicarbonate-5pct-aqueous",
        "Sodium bicarbonate, 5% aqueous (neutralising wash)",
        (
            MaterialComponent.known("sodium bicarbonate", "active", 0.045, 0.055),
            MaterialComponent.known("water", "solvent", 0.945, 0.955),
        ),
        Phase.AQUEOUS_SOLUTION,
        provenance=(
            "DERIVED_WITH_ERROR composition 5% +-0.5% (mass fraction) sodium bicarbonate in water, source "
            "class: the procedure's own sourced formulation term (LibreTexts isopentyl-acetate experiment, "
            "'wash with 5% sodium bicarbonate'), confidence HIGH for the formulation. Citation: "
            f"{_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=(
            "5% aqueous NaHCO3 neutralising wash; ionic (identity unresolvable to a covalent Molecule), "
            "name-keyed per D1",
        ),
    )


def sodium_chloride_saturated_wash(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Saturated aqueous sodium chloride (brine) -- the layer-separation wash. ``Phase.AQUEOUS_SOLUTION``.

    The procedure calls for "saturated aqueous sodium chloride" (5 mL, to break the emulsion). NaCl
    saturation is ~26.3 g / 100 g water at 20-25 C -> ~26% mass fraction; the interval [0.23, 0.27] carries
    an honest band around it. Ionic (Na+ / Cl-), NAME-keyed.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "sodium-chloride-saturated-aqueous",
        "Sodium chloride, saturated aqueous (brine wash)",
        (
            MaterialComponent.known("sodium chloride", "active", 0.23, 0.27),
            MaterialComponent.known("water", "solvent", 0.73, 0.77),
        ),
        Phase.AQUEOUS_SOLUTION,
        provenance=(
            "DERIVED_WITH_ERROR composition [0.23, 0.27] (mass fraction) NaCl at saturation, source class: "
            "solubility reference (~26.3 g/100 g water at 20-25 C, CRC Handbook / PubChem CID 5234) + the "
            "procedure's 'saturated aqueous sodium chloride' formulation term, confidence HIGH. Citations: "
            f"https://pubchem.ncbi.nlm.nih.gov/compound/5234 ; {_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=(
            "saturated aqueous NaCl brine (layer-separation wash); ionic, name-keyed per D1",
        ),
    )


def magnesium_sulfate_anhydrous(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Anhydrous magnesium sulfate -- the drying agent. ``Phase.SOLID``, NAME-keyed.

    The procedure calls for "2 g anhydrous magnesium sulfate" to dry the organic layer. Reagent-grade
    anhydrous MgSO4 drier is >=97% (the balance being residual water / trace sulfate salts); [0.97, 1.0] is
    the honest band. Ionic (Mg2+ / SO4 2-), NAME-keyed; the load-bearing formulation word is "anhydrous"
    (a hydrated drier cannot dry).
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "magnesium-sulfate-anhydrous",
        "Magnesium sulfate, anhydrous (drying agent)",
        (MaterialComponent.known("magnesium sulfate", "active", 0.97, 1.0),),
        Phase.SOLID,
        provenance=(
            "DERIVED_WITH_ERROR assay [0.97, 1.0] (mass fraction) anhydrous MgSO4, source class: reagent-"
            "supplier spec (anhydrous magnesium sulfate ReagentPlus, >=97%) + the procedure's 'anhydrous "
            "magnesium sulfate' formulation term, confidence HIGH. Citations: "
            f"https://www.sigmaaldrich.com/US/en/product/sigald/m7506 ; {_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=(
            "ANHYDROUS solid drying agent (Phase.SOLID); ionic, name-keyed per D1; a hydrated grade cannot "
            "dry",
        ),
    )


def wash_water(*, quantity: "StockQuantity | None" = None) -> StockMaterial:
    """Distilled / deionised water -- the aqueous partition and wash medium. ``Phase.LIQUID``, NAME-keyed.

    The procedure draws water for the aqueous partition and a wash (55 mL + 10 mL rinse + 25 mL wash). It is
    keyed by NAME here (not the water Molecule) so it matches the same name-keyed auxiliary demand the other
    washes use -- possession, not an assay claim.
    """
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA,
        "wash-water-distilled",
        "Distilled / deionised water",
        (MaterialComponent.known("water", "solvent", 0.99, 1.0),),
        Phase.LIQUID,
        provenance=(
            "Distilled/deionised water, [0.99, 1.0] mass fraction (trace dissolved solids), source class: "
            "laboratory-grade water spec, confidence HIGH. Curated for the gate #18 procedure partition/wash "
            f"medium. Citation: {_ISOPENTYL_URL}"
        ),
        quantity=quantity,
        formulation_notes=("distilled/DI water partition + wash medium; name-keyed per D1",),
    )


# -- inventories --------------------------------------------------------------------------------------------


def isopentyl_fully_declared_inventory() -> "tuple[StockMaterial, ...]":
    """The Round-III FIT positive: a fully-declared Custom bench that stocks the WHOLE procedure.

    Covers every reactant AND every procedure-only auxiliary at a matching phase/formulation, each with a
    declared amount comfortably above its per-run draw (D1/D3/D4): glacial acetic acid (20 mL drawn),
    isoamyl alcohol (15 mL), conc. H2SO4 catalyst (4 mL), 5% NaHCO3 wash (2 x 25 mL), water (>= 90 mL),
    saturated NaCl (5 mL), anhydrous MgSO4 (2 g). This is the "$200-and-a-dream / source-compatible
    inventory" contract -- FIT is earned only by actually possessing the whole procedure, never by a
    reaction-class label manufacturing a floor.
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
    """The two-bottle stocked bench: isoamyl alcohol + glacial acetic acid, both reagent-grade.

    The pre-Round-III positive (reactants only). Retained as an exported name; the full FIT positive that
    also covers the procedure-only auxiliaries is :func:`isopentyl_fully_declared_inventory`.
    """
    return (isoamyl_alcohol_reagent_grade(), glacial_acetic_acid())


def isopentyl_vinegar_inventory() -> "tuple[StockMaterial, ...]":
    """The CONTROL bench: isoamyl alcohol + household vinegar standing in for glacial acetic acid.

    Same route, one bottle swapped -- proves the vinegar cannot masquerade as the reagent-grade feed: it
    BLOCKS on phase (aqueous, not neat LIQUID) AND on assay (a few % vs >= 99%).
    """
    return (isoamyl_alcohol_reagent_grade(), household_white_vinegar())


def isopentyl_insufficient_quantity_inventory() -> "tuple[StockMaterial, ...]":
    """Targeted negative: the fully-declared bench, but with too LITTLE glacial acetic acid.

    Everything phase/assay-correct; the ONE broken axis is quantity -- 10 mL of glacial acetic stocked
    against the procedure's 20 mL draw (D3: stock < required -> INSUFFICIENT / UNKNOWN, never a silent
    pass). Feeds the M25 quantity discriminator.
    """
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
    """Targeted negative: the fully-declared bench, but with a MIS-PHASED alcohol.

    Everything sufficiently stocked; the ONE broken axis is phase/formulation -- the alcohol is declared as
    a dilute AQUEOUS solution rather than the neat LIQUID reagent (D4: known-phase mismatch -> BLOCKED).
    Feeds the M26 phase discriminator.
    """
    return (
        glacial_acetic_acid(quantity=StockQuantity.of("500", "mL")),
        isoamyl_alcohol_dilute_aqueous(quantity=StockQuantity.of("500", "mL")),  # wrong phase: aqueous, not neat
        concentrated_sulfuric_acid(quantity=StockQuantity.of("500", "mL")),
        sodium_bicarbonate_wash_5pct(quantity=StockQuantity.of("500", "mL")),
        sodium_chloride_saturated_wash(quantity=StockQuantity.of("250", "mL")),
        magnesium_sulfate_anhydrous(quantity=StockQuantity.of("250", "g")),
        wash_water(quantity=StockQuantity.of("1000", "mL")),
    )
