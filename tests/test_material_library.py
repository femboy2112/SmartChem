"""Gate #18 material library (Round III, D1/D3/D4/D9) -- the certificate-of-analysis fixture.

These pin the honesty that gate #18 rests on: glacial acetic acid is a suitable feed and household vinegar
is NOT (BLOCKED on phase AND assay), the fully-declared Custom bench actually stocks the whole isopentyl-
acetate procedure, and the H2SO4 catalyst now carries a real GHS corrosion record (H314). A structure key
is not an argument; a phase is not a rounding error; a fabricated pass is worse than an admitted gap.
"""
from smartchem.data import material_library as ml
from smartchem.data.hazards import hazards_for, hazards_for_named
from smartchem.experiment.stock import FitnessVerdict, Phase
from smartchem.identity_parse import InputKind, resolve_target

_ACETIC_ACID = resolve_target("acetic acid", InputKind.NAME).canonical()


class TestGlacialVsVinegarDiscrimination:
    def test_glacial_acetic_satisfies_a_high_assay_liquid_requirement(self):
        glacial = ml.glacial_acetic_acid()
        # assay: worst case 99.5% clears a 99% pure-reagent requirement -> SATISFIES, no measurement needed.
        assert glacial.satisfies(_ACETIC_ACID, min_assay=0.99) is FitnessVerdict.SATISFIES
        # phase: a neat LIQUID reagent, the D1 formulation that discriminates it from vinegar.
        assert glacial.phase is Phase.LIQUID

    def test_vinegar_does_not_satisfy_and_is_the_wrong_phase(self):
        vinegar = ml.household_white_vinegar()
        # assay: even the BEST case (8%) falls short of 99% -> INSUFFICIENT_ASSAY, never a silent pass.
        assert vinegar.satisfies(_ACETIC_ACID, min_assay=0.99) is FitnessVerdict.INSUFFICIENT_ASSAY
        # phase: aqueous, so it also BLOCKS a neat-LIQUID phase requirement. Two independent BLOCKs.
        assert vinegar.phase is Phase.AQUEOUS_SOLUTION
        assert vinegar.phase is not Phase.LIQUID

    def test_vinegar_and_glacial_share_the_structure_key(self):
        # the whole point: same acetic-acid structure, so the fitness verdict is a real comparison, not a
        # name strawman. The interval is what separates them, never the label.
        glacial = ml.glacial_acetic_acid()
        vinegar = ml.household_white_vinegar()
        assert glacial.active_fraction_interval(_ACETIC_ACID) is not None
        assert vinegar.active_fraction_interval(_ACETIC_ACID) is not None


class TestFullyDeclaredInventory:
    def test_covers_every_reactant_and_auxiliary(self):
        inv = ml.isopentyl_fully_declared_inventory()
        # names collected off components (structure-keyed reactants carry a struct: key, so key on the
        # material_id set instead -- the stable, human-declared handle).
        ids = {m.material_id for m in inv}
        expected = {
            "glacial-acetic-acid-reagent-grade",
            "isoamyl-alcohol-reagent-grade",
            "sulfuric-acid-concentrated-acs",
            "sodium-bicarbonate-5pct-aqueous",
            "sodium-chloride-saturated-aqueous",
            "magnesium-sulfate-anhydrous",
            "wash-water",
        }
        assert expected <= ids

    def test_every_bottle_declares_a_quantity(self):
        # D3: a fully-declared bench declares amounts; an unspecified stock quantity is never assumed
        # sufficient, so the FIT positive must actually state one for each bottle.
        inv = ml.isopentyl_fully_declared_inventory()
        assert all(m.quantity is not None for m in inv)

    def test_reactant_phases_are_correct(self):
        by_id = {m.material_id: m for m in ml.isopentyl_fully_declared_inventory()}
        assert by_id["glacial-acetic-acid-reagent-grade"].phase is Phase.LIQUID
        assert by_id["isoamyl-alcohol-reagent-grade"].phase is Phase.LIQUID
        assert by_id["sulfuric-acid-concentrated-acs"].phase is Phase.LIQUID
        assert by_id["sodium-bicarbonate-5pct-aqueous"].phase is Phase.AQUEOUS_SOLUTION
        assert by_id["sodium-chloride-saturated-aqueous"].phase is Phase.AQUEOUS_SOLUTION
        assert by_id["magnesium-sulfate-anhydrous"].phase is Phase.SOLID
        assert by_id["wash-water"].phase is Phase.LIQUID


class TestTargetedNegatives:
    def test_insufficient_quantity_stocks_too_little_acid(self):
        by_id = {m.material_id: m for m in ml.isopentyl_insufficient_quantity_inventory()}
        acid = by_id["glacial-acetic-acid-reagent-grade"]
        # the ONE broken axis: 10 mL stocked against the sourced 20 mL draw. Everything else is fine.
        assert acid.quantity is not None
        assert acid.quantity.unit == "mL"
        assert float(acid.quantity.value) < 20.0
        # the alcohol is still fully phase/assay/quantity-correct -- a clean single-axis negative.
        assert by_id["isoamyl-alcohol-reagent-grade"].phase is Phase.LIQUID

    def test_wrong_phase_mis_phases_the_alcohol(self):
        by_id = {m.material_id: m for m in ml.isopentyl_wrong_phase_inventory()}
        # the mis-phased alcohol substitutes an aqueous bottle for the neat LIQUID reagent.
        assert "isoamyl-alcohol-dilute-aqueous" in by_id
        assert by_id["isoamyl-alcohol-dilute-aqueous"].phase is Phase.AQUEOUS_SOLUTION
        # the acid is untouched here -- the broken axis is phase, and it is the alcohol's.
        assert by_id["glacial-acetic-acid-reagent-grade"].phase is Phase.LIQUID


class TestSulfuricAcidHazard:
    def test_record_loads_and_carries_h314(self):
        rec = hazards_for_named("sulfuric acid")
        assert rec is not None
        assert "H314" in rec.ghs_codes  # skin corrosion 1A -- the non-negotiable call

    def test_record_is_formula_addressable_as_a_single_isomer(self):
        # canonical Formula repr is alphabetical (H, O, S): "H2O4S", NOT "H2SO4". D9 wires the containment
        # axis off this formula-keyed lookup, so the key must be the one the decompiler produces.
        rec = hazards_for("H2O4S")
        assert rec is not None
        assert rec.name == "sulfuric acid"
        assert "H314" in rec.ghs_codes
