"""STOCK-01 (first brick) -- StockMaterial: a chemical IDENTITY is not a MATERIAL claim (standard section 10).

The core falsifier: household vinegar cannot satisfy a pure-acetic-acid requirement without a proven assay --
the honest verdicts are INSUFFICIENT_ASSAY / UNKNOWN_ASSAY, never a silent SATISFIES.
"""
import pytest

from smartchem.experiment.stock import (
    STOCK_MATERIAL_SCHEMA,
    CostObservation,
    FitnessVerdict,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
    stock_material_from_commodity,
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


class TestFullSchemaFields:
    """STOCK-01 (full section 10.2 schema): quantity, cost, container, jurisdiction, impurities -- each a typed
    value or an honest UNKNOWN, and NEVER an invented one."""

    def test_first_brick_positional_form_still_constructs_with_unknown_extras(self):
        # backward compatibility: the 6-positional-arg form is unchanged and every new field defaults to UNKNOWN.
        m = _glacial()
        assert m.quantity is None
        assert m.assay_method is None
        assert m.cost_observation is None
        assert m.container_and_storage is None
        assert m.jurisdiction_and_availability is None
        assert m.known_impurities == () and m.formulation_notes == ()

    def test_a_fully_specified_material_carries_every_field(self):
        m = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "acetic-glacial-500", "glacial acetic acid",
            (MaterialComponent.known("acetic acid", "active", 0.99, 1.0),), Phase.LIQUID, "reagent-grade label",
            quantity=StockQuantity.of(500, "mL"),
            assay_method="titration",
            container_and_storage="amber glass, ambient",
            opened_or_age_state="unopened",
            jurisdiction_and_availability="US, general laboratory supply",
            cost_observation=CostObservation.of("42.50", "USD", "2026-08-31", "vendor catalogue X"),
            known_impurities=("water",),
            formulation_notes=("glacial (>99%)",),
        )
        assert m.quantity.render() == "500 mL"
        assert "titration" in m.render()
        assert "42.50 USD" in m.render()
        # satisfies() is unchanged by the richer schema
        assert m.satisfies("acetic acid", min_assay=0.99) is FitnessVerdict.SATISFIES

    def test_quantity_is_semantic_it_changes_the_digest(self):
        base = _glacial()
        with_qty = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "acetic-glacial", "glacial acetic acid",
            (MaterialComponent.known("acetic acid", "active", 0.99, 1.0),), Phase.LIQUID, "reagent-grade label",
            quantity=StockQuantity.of(500, "mL"),
        )
        assert base.digest != with_qty.digest
        # ...and two materials differing only in the declared amount are distinct
        other_qty = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "acetic-glacial", "glacial acetic acid",
            (MaterialComponent.known("acetic acid", "active", 0.99, 1.0),), Phase.LIQUID, "reagent-grade label",
            quantity=StockQuantity.of(250, "mL"),
        )
        assert with_qty.digest != other_qty.digest

    def test_stock_quantity_refuses_a_nonpositive_or_nonfinite_amount(self):
        for bad in ("0", "-5", "inf", "nan", "not-a-number"):
            with pytest.raises(ValueError):
                StockQuantity.of(bad, "g")
        with pytest.raises(ValueError, match="unit"):
            StockQuantity.of("5", "  ")

    def test_cost_observation_cannot_be_built_without_being_dated_and_sourced(self):
        # section 10.4: prices MUST be dated and sourced; an unpriced material uses cost_observation=None.
        for missing in ("amount", "currency", "observed_date", "source"):
            kwargs = {"amount": "1", "currency": "USD", "observed_date": "2026-01-01", "source": "vendor X"}
            kwargs[missing] = "   "
            with pytest.raises(ValueError):
                CostObservation.of(kwargs["amount"], kwargs["currency"], kwargs["observed_date"], kwargs["source"])

    def test_cost_observation_refuses_a_negative_or_nonnumeric_amount(self):
        with pytest.raises(ValueError, match="amount"):
            CostObservation.of("-1", "USD", "2026-01-01", "vendor X")
        with pytest.raises(ValueError, match="amount"):
            CostObservation.of("cheap", "USD", "2026-01-01", "vendor X")

    def test_impurities_and_notes_must_be_tuples_of_nonempty_strings(self):
        with pytest.raises(TypeError, match="known_impurities"):
            StockMaterial(
                STOCK_MATERIAL_SCHEMA, "m", "m", (MaterialComponent.known("a", "active", 0, 1),), Phase.LIQUID, "s",
                known_impurities="water",  # a bare string is not a tuple of impurity names
            )
        with pytest.raises(TypeError, match="formulation_notes"):
            StockMaterial(
                STOCK_MATERIAL_SCHEMA, "m", "m", (MaterialComponent.known("a", "active", 0, 1),), Phase.LIQUID, "s",
                formulation_notes=("",),  # an empty note
            )

    def test_optional_text_fields_reject_empty_but_accept_none(self):
        with pytest.raises(ValueError, match="assay_method"):
            StockMaterial(
                STOCK_MATERIAL_SCHEMA, "m", "m", (MaterialComponent.known("a", "active", 0, 1),), Phase.LIQUID, "s",
                assay_method="  ",
            )
        with pytest.raises(TypeError, match="quantity"):
            StockMaterial(
                STOCK_MATERIAL_SCHEMA, "m", "m", (MaterialComponent.known("a", "active", 0, 1),), Phase.LIQUID, "s",
                quantity="500 mL",  # must be a typed StockQuantity, not a string
            )

    def test_unpriced_material_renders_cost_unknown_never_a_guess(self):
        assert "cost: UNKNOWN" in _vinegar().render()

    def test_typed_values_reject_bad_schema(self):
        with pytest.raises(ValueError, match="schema_version"):
            StockQuantity("wrong", "5", "g")
        with pytest.raises(ValueError, match="schema_version"):
            CostObservation("wrong", "1", "USD", "2026-01-01", "vendor X")


class TestCommodityBridge:
    """STOCK-01 bridge (section 10.1): a commodity is a SOURCE LEAD, never a proven pure material."""

    def _lead(self):
        from smartchem.data.reagents import Availability, CommodityReagent
        from smartchem.smiles import parse_smiles
        return CommodityReagent(
            "acetic acid", parse_smiles("CC(=O)O"), Availability.GROCERY, "white vinegar, ~5% aqueous", "registry",
        )

    def test_bridge_maps_a_commodity_to_an_unknown_assay_material(self):
        mat = stock_material_from_commodity(self._lead())
        assert isinstance(mat, StockMaterial)
        assert mat.phase is Phase.UNKNOWN                      # a commodity record does not fix a phase
        assert len(mat.components) == 1
        (lo, hi) = mat.active_fraction_interval("acetic acid")
        assert (lo, hi) == (0.0, 1.0)                          # unknown fraction -- the honest full interval
        assert "source lead" in mat.provenance.lower() and "section 10.1" in mat.provenance

    def test_a_bridged_commodity_never_silently_satisfies_a_pure_requirement(self):
        # THE section 10.1 falsifier: a commodity identity match must NOT stand in for a proven pure material.
        mat = stock_material_from_commodity(self._lead())
        assert mat.satisfies("acetic acid", min_assay=0.99) is FitnessVerdict.UNKNOWN_ASSAY
        assert mat.satisfies("acetic acid", min_assay=0.50) is FitnessVerdict.UNKNOWN_ASSAY
        # ...and its cost/quantity are honestly UNKNOWN, never invented from the commodity record
        assert mat.quantity is None and mat.cost_observation is None

    def test_bridge_works_on_the_real_commodity_registry(self):
        from smartchem.data.reagents import COMMODITY_REAGENTS
        mat = stock_material_from_commodity(COMMODITY_REAGENTS[0])
        assert mat.satisfies(COMMODITY_REAGENTS[0].name, min_assay=0.99) is FitnessVerdict.UNKNOWN_ASSAY

    def test_bridge_rejects_a_non_commodity(self):
        with pytest.raises(TypeError, match="CommodityReagent"):
            stock_material_from_commodity("acetic acid")
