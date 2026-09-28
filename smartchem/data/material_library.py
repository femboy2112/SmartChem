"""smartchem/data/material_library.py -- a curated DERIVED_WITH_ERROR ``StockMaterial`` library (gate #18).

**Chart note.** A route's ``MaterialRequirement`` is a demand; a ``StockMaterial`` is a real bottle that
either meets it or doesn't (:mod:`smartchem.experiment.stock`). Nobody upstream is going to hand us a
supplier certificate of analysis, so this module IS the certificate: four bottles, each keyed on canonical
STRUCTURE (:meth:`~smartchem.experiment.stock.MaterialComponent.of_molecule`, never a fragile name string),
each assay interval traced to a public citation, each honestly labelled ``DERIVED_WITH_ERROR`` -- an
uncertainty band derived from a sourced spec, not a source-quoted point value, and never a fabricated 100%.

The whole point of the second bottle (household vinegar) is that it is keyed on the exact SAME acetic-acid
structure as the first (glacial). A structure key cannot be argued with the way a name can: this is what
lets :meth:`StockMaterial.satisfies` tell a real reagent bottle from a science-fair vinegar substitute
without anybody having to remember to check the label twice.

Coverage (from the swarm data files, isopentyl-acetate lane):

* isoamyl alcohol / 3-methyl-1-butanol, reagent grade -- ``[0.98, 0.99]``, LIQUID.
* glacial acetic acid, reagent grade -- ``[0.995, 1.0]`` LIQUID. The source cites a titrimetric assay of
  "99.5-100.5%" (titration against a base can legitimately read a hair over 100% on a real bottle); a MASS
  FRACTION cannot exceed 1.0 (:class:`~smartchem.experiment.stock.MaterialComponent` enforces
  ``0 <= fraction <= 1.0`` and raises on anything above it), so the upper bound is CLAMPED to 1.0. The clamp
  only ever throws away the physically-impossible sliver above 100%; it never manufactures headroom the
  source didn't report.
* concentrated sulfuric acid -- ``[0.95, 0.98]`` LIQUID (carried for completeness/reuse; no consumer in
  this round's gate #18 route treats it as a MATERIAL -- the isopentyl-acetate route declares it as a
  CATALYST, which the procurement axis prices, not the material axis; see
  :mod:`smartchem.capability.requirements`'s ``procurement_catalysts``).
* household white vinegar (acetic acid, aqueous) -- ``[0.04, 0.08]`` AQUEOUS_SOLUTION. The CONTROL bottle:
  same structure key as glacial acetic acid, so a route that actually needs the glacial-grade feed gets a
  real, honest BLOCKED against it -- not a free pass because "it's acetic acid too".

Two builder functions assemble the two competing isopentyl-acetate inventories gate #18 diffs against each
other; see :func:`isopentyl_lab_inventory` (the FIT-positive stock) and :func:`isopentyl_vinegar_inventory`
(the control, vinegar swapped in for glacial).
"""
from __future__ import annotations

from ..experiment.stock import MaterialComponent, Phase, STOCK_MATERIAL_SCHEMA, StockMaterial
from ..identity_parse import InputKind, resolve_target

__all__ = [
    "isoamyl_alcohol_reagent_grade",
    "glacial_acetic_acid",
    "concentrated_sulfuric_acid",
    "household_white_vinegar",
    "isopentyl_lab_inventory",
    "isopentyl_vinegar_inventory",
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


def isoamyl_alcohol_reagent_grade() -> StockMaterial:
    """Isoamyl alcohol (3-methyl-1-butanol, CAS 123-51-3), ACS/reagent grade, assay ``[0.98, 0.99]``.

    DERIVED_WITH_ERROR: three major suppliers converge on a 98-99.5% band; 0.98 is the conservative
    published floor, 0.99 the conservative ceiling below their upper spec (never rounding up past what was
    actually quoted).
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
        formulation_notes=("curated for SmartChem v0.9 gate #18 (isopentyl acetate CAPABILITY_FIT positive)",),
    )


def glacial_acetic_acid() -> StockMaterial:
    """Glacial acetic acid (CAS 64-19-7), reagent grade (USP/ACS), assay ``[0.995, 1.0]`` -- CLAMPED.

    DERIVED_WITH_ERROR: the source (USP/ACS/BP/Ph.Eur. compendial spec, titrimetric) reads "99.5-100.5%".
    A titration-verified assay CAN legitimately read a hair over 100% on a real bottle (non-volatile-residue
    and congealing-point checks bound the impurity, not the titration ceiling) -- but a MASS FRACTION cannot
    physically exceed 1.0, and ``MaterialComponent`` enforces exactly that (``0 <= fraction <= 1.0``, raises
    above it). The upper bound is therefore CLAMPED to 1.0 here: [0.995, 1.0], never [0.995, 1.005]. The
    clamp discards only the physically-impossible sliver; the lower bound is untouched.
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
        formulation_notes=("curated for SmartChem v0.9 gate #18 (isopentyl acetate CAPABILITY_FIT positive)",),
    )


def concentrated_sulfuric_acid() -> StockMaterial:
    """Concentrated sulfuric acid (CAS 7664-93-9), ACS reagent grade, assay ``[0.95, 0.98]``.

    DERIVED_WITH_ERROR: ACS Committee on Analytical Reagents published spec (alkalimetric titration; density
    is unreliable as an assay proxy above ~93%). Carried for completeness/future reuse -- the isopentyl-
    acetate route declares sulfuric acid as a CATALYST (``ConditionEnvelope.catalysts``), which the
    capability compiler's procurement axis prices, never the material axis, so this bottle has no consumer
    in gate #18 itself.
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
        formulation_notes=("curated for SmartChem v0.9 gate #18 (isopentyl acetate route); no material-axis consumer",),
    )


def household_white_vinegar() -> StockMaterial:
    """Household white vinegar, food-grade, assay ``[0.04, 0.08]`` -- the acetic-acid CONTROL bottle.

    DERIVED_WITH_ERROR: FDA CPG 525.825 mandates a 4% minimum; most retail vinegar sits 5-7%; the interval
    is widened to 8% to stay honest about the retail spread rather than quoting a single "typical" number.
    Keyed on the SAME canonical acetic-acid structure as :func:`glacial_acetic_acid` -- this is what makes
    it a real competing bottle in :meth:`~smartchem.experiment.stock.StockMaterial.satisfies` rather than a
    strawman: a pure-acetic-acid requirement gets to see BOTH bottles and correctly prefer neither by name.
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
            "curated for SmartChem v0.9 gate #18 vinegar CONTROL (same acetic-acid structure key as glacial)",
        ),
    )


def isopentyl_lab_inventory() -> "tuple[StockMaterial, ...]":
    """The FIT-positive stocked bench: isoamyl alcohol + glacial acetic acid, both reagent-grade.

    Feed this to ``smartchem.capability.presets.research_lab(material_inventory=...)`` for the gate #18
    positive demonstration.
    """
    return (isoamyl_alcohol_reagent_grade(), glacial_acetic_acid())


def isopentyl_vinegar_inventory() -> "tuple[StockMaterial, ...]":
    """The CONTROL bench: isoamyl alcohol + household vinegar standing in for glacial acetic acid.

    Same profile, same route, one bottle swapped -- proves the vinegar cannot masquerade as the reagent-
    grade feed the esterification's derived assay floor actually demands.
    """
    return (isoamyl_alcohol_reagent_grade(), household_white_vinegar())
