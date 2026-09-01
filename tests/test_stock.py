"""STOCK-01 (first brick) -- StockMaterial: a chemical IDENTITY is not a MATERIAL claim (standard section 10).

The core falsifier: household vinegar cannot satisfy a pure-acetic-acid requirement without a proven assay --
the honest verdicts are INSUFFICIENT_ASSAY / UNKNOWN_ASSAY, never a silent SATISFIES.
"""
import pytest

from smartchem.experiment.stock import (
    STOCK_MATERIAL_SCHEMA,
    FitnessVerdict,
    MaterialComponent,
    Phase,
    StockMaterial,
)


def _vinegar():
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA, "vinegar-household", "household vinegar",
        (MaterialComponent.known("acetic acid", "active", 0.04, 0.07),
         MaterialComponent.known("water", "solvent", 0.93, 0.96)),
        Phase.AQUEOUS_SOLUTION, "household vinegar is a few % acetic acid in water (common commodity knowledge)",
    )


def _glacial():
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA, "acetic-glacial", "glacial acetic acid",
        (MaterialComponent.known("acetic acid", "active", 0.99, 1.0),),
        Phase.LIQUID, "reagent-grade label",
    )


class TestMaterialFitness:
    def test_vinegar_does_not_satisfy_pure_acetic_acid(self):
        # THE STOCK-01 falsifier: an identity match (both contain acetic acid) is NOT a material claim.
        assert _vinegar().satisfies("acetic acid", min_assay=0.99) is FitnessVerdict.INSUFFICIENT_ASSAY

    def test_glacial_acetic_acid_does_satisfy_pure_acetic_acid(self):
        assert _glacial().satisfies("acetic acid", min_assay=0.99) is FitnessVerdict.SATISFIES

    def test_a_requirement_inside_the_interval_is_unknown_never_a_pass(self):
        # 5% requirement vs a 4-7% assay straddles the threshold -> must MEASURE, never assume the good end.
        assert _vinegar().satisfies("acetic acid", min_assay=0.05) is FitnessVerdict.UNKNOWN_ASSAY

    def test_a_requirement_below_the_worst_case_is_satisfied(self):
        assert _vinegar().satisfies("acetic acid", min_assay=0.03) is FitnessVerdict.SATISFIES

    def test_an_absent_identity_is_identity_absent(self):
        assert _vinegar().satisfies("ethanol", min_assay=0.5) is FitnessVerdict.IDENTITY_ABSENT

    def test_an_unknown_fraction_never_satisfies_a_real_requirement(self):
        mystery = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "mystery", "unlabelled bottle",
            (MaterialComponent.unknown_fraction("acetic acid", "active"),), Phase.LIQUID, "no assay on the label",
        )
        assert mystery.satisfies("acetic acid", min_assay=0.9) is FitnessVerdict.UNKNOWN_ASSAY

    def test_active_fraction_interval_sums_shared_components(self):
        m = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "two-part", "two acetic sources", (
                MaterialComponent.known("acetic acid", "active", 0.10, 0.20),
                MaterialComponent.known("acetic acid", "active", 0.05, 0.10),
            ), Phase.LIQUID, "test",
        )
        assert m.active_fraction_interval("acetic acid") == pytest.approx((0.15, 0.30))

    @pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
    def test_min_assay_must_be_a_fraction_in_the_unit_interval(self, bad):
        with pytest.raises(ValueError, match="min_assay"):
            _glacial().satisfies("acetic acid", min_assay=bad)


class TestConstructionInvariants:
    def test_component_fraction_interval_must_be_ordered_and_in_range(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            MaterialComponent.known("x", "active", 0.5, 0.2)
        with pytest.raises(ValueError, match="fraction in"):
            MaterialComponent.known("x", "active", 0.0, 1.5)

    def test_material_needs_at_least_one_component(self):
        with pytest.raises(TypeError, match="non-empty"):
            StockMaterial(STOCK_MATERIAL_SCHEMA, "empty", "empty", (), Phase.LIQUID, "src")

    def test_material_refuses_infeasible_minimum_fractions(self):
        # two components each claiming >= 60% is impossible (sum of minima > 1)
        with pytest.raises(ValueError, match="above 1.0"):
            StockMaterial(STOCK_MATERIAL_SCHEMA, "bad", "over-full", (
                MaterialComponent.known("a", "active", 0.6, 0.7),
                MaterialComponent.known("b", "active", 0.6, 0.7),
            ), Phase.LIQUID, "src")

    def test_material_and_component_reject_bad_schema(self):
        with pytest.raises(ValueError, match="schema_version"):
            MaterialComponent("wrong", "x", "active", 0.0, 1.0)
        with pytest.raises(ValueError, match="schema_version"):
            StockMaterial("wrong", "id", "name", (MaterialComponent.known("a", "active", 0, 1),), Phase.LIQUID, "s")
