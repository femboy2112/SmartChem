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
            cost_observation=CostObservation.of("42.50", "USD", "each", "2026-08-31", "vendor catalogue X"),
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

    def test_stock_quantity_uses_the_one_strict_exact_grammar(self):
        # Round V D1: float()/epsilon are banned from quantity parsing -- these all parsed under float().
        for bad in ("1/3", "1_000", " 5 ", "5 ", "+5", "0.0", "1e999"):
            with pytest.raises(ValueError):
                StockQuantity.of(bad, "mL")
        with pytest.raises(TypeError, match="float"):
            StockQuantity.of(0.1, "mL")  # a float's spelling is not the source's

    def test_stock_quantity_exact_is_a_fraction(self):
        from fractions import Fraction

        assert StockQuantity.of("20.00004", "mL").exact() == Fraction(2000004, 100000)
        assert StockQuantity.of("20", "mL").exact() < StockQuantity.of("20.00004", "mL").exact()
        assert StockQuantity.of(500, "mL").exact() == 500
        assert StockQuantity.of("1e-12", "mL").exact() == Fraction(1, 10 ** 12)


    def test_cost_observation_cannot_be_built_without_being_dated_and_sourced(self):
        # section 10.4: prices MUST be dated and sourced; an unpriced material uses cost_observation=None.
        for missing in ("amount", "currency", "unit", "observed_date", "source"):
            kwargs = {"amount": "1", "currency": "USD", "unit": "each", "observed_date": "2026-01-01",
                      "source": "vendor X"}
            kwargs[missing] = "   "
            with pytest.raises(ValueError):
                CostObservation.of(kwargs["amount"], kwargs["currency"], kwargs["unit"], kwargs["observed_date"],
                                   kwargs["source"])

    def test_cost_observation_refuses_a_negative_or_nonnumeric_amount(self):
        with pytest.raises(ValueError, match="amount"):
            CostObservation.of("-1", "USD", "each", "2026-01-01", "vendor X")
        with pytest.raises(ValueError, match="amount"):
            CostObservation.of("cheap", "USD", "each", "2026-01-01", "vendor X")

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
            CostObservation("wrong", "1", "USD", "metric ton", "2026-01-01", "vendor X")


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
        (lo, hi) = mat.active_fraction_interval(self._lead().molecule)   # STRUCTURE-keyed now (ID-LAYER-01)
        assert (lo, hi) == (0.0, 1.0)                          # unknown fraction -- the honest full interval
        assert "source lead" in mat.provenance.lower() and "section 10.1" in mat.provenance

    def test_a_bridged_commodity_never_silently_satisfies_a_pure_requirement(self):
        # THE section 10.1 falsifier: a commodity identity match must NOT stand in for a proven pure material.
        mat = stock_material_from_commodity(self._lead())
        mol = self._lead().molecule
        assert mat.satisfies(mol, min_assay=0.99) is FitnessVerdict.UNKNOWN_ASSAY
        assert mat.satisfies(mol, min_assay=0.50) is FitnessVerdict.UNKNOWN_ASSAY
        # ...and its cost/quantity are honestly UNKNOWN, never invented from the commodity record
        assert mat.quantity is None and mat.cost_observation is None

    def test_bridge_works_on_the_real_commodity_registry(self):
        from smartchem.data.reagents import COMMODITY_REAGENTS
        mat = stock_material_from_commodity(COMMODITY_REAGENTS[0])
        assert mat.satisfies(COMMODITY_REAGENTS[0].molecule, min_assay=0.99) is FitnessVerdict.UNKNOWN_ASSAY

    def test_bridge_rejects_a_non_commodity(self):
        with pytest.raises(TypeError, match="CommodityReagent"):
            stock_material_from_commodity("acetic acid")


class TestCanonicalStructureKeying:
    """STOCK-01 canonical keying (ID-LAYER-01): fitness is judged on canonical STRUCTURE, not a fragile name.

    The lesson made LIVE: a component keyed by canonical structure never lets a same-formula isomer borrow its
    assay (the "keyed by formula fails open" hazard), matches across name synonyms, and is the key a route/shopping
    Molecule is checked against.  A bare name can never stand in for a proven structure, nor a structure for a name.
    """

    def _ethanol_bottle(self, lo=0.99, hi=1.0):
        from smartchem.smiles import parse_smiles
        return StockMaterial(
            STOCK_MATERIAL_SCHEMA, "etoh", "anhydrous ethanol",
            (MaterialComponent.of_molecule(parse_smiles("CCO"), "active", lo, hi),), Phase.LIQUID, "reagent label",
        )

    def test_a_structure_query_matches_across_a_fresh_molecule_object(self):
        from smartchem.smiles import parse_smiles
        # a DIFFERENT Molecule object of the same structure still matches -- structure, not object identity.
        assert self._ethanol_bottle().satisfies(parse_smiles("CCO"), min_assay=0.99) is FitnessVerdict.SATISFIES

    def test_a_same_formula_isomer_never_borrows_the_assay(self):
        from smartchem.smiles import parse_smiles
        # ethanol (CCO) and dimethyl ether (COC) share the formula C2H6O but NOT the structure: no borrow.
        assert self._ethanol_bottle().satisfies(parse_smiles("COC"), min_assay=0.5) is FitnessVerdict.IDENTITY_ABSENT

    def test_the_isomer_guard_is_live_on_the_bridge_default_data(self):
        from smartchem.smiles import parse_smiles
        from smartchem.data.reagents import Availability, CommodityReagent
        # acetic acid (CC(=O)O) and glycolaldehyde (OCC=O) are both C2H4O2 -- a bridged acetic material must NOT
        # satisfy a glycolaldehyde requirement.  The guard is on the LIVE bridge path, not just injectable.
        lead = CommodityReagent("acetic acid", parse_smiles("CC(=O)O"), Availability.GROCERY, "vinegar", "reg")
        mat = stock_material_from_commodity(lead)
        assert mat.satisfies(parse_smiles("CC(=O)O"), min_assay=0.99) is FitnessVerdict.UNKNOWN_ASSAY
        assert mat.satisfies(parse_smiles("OCC=O"), min_assay=0.99) is FitnessVerdict.IDENTITY_ABSENT

    def test_a_name_key_cannot_satisfy_a_structure_query(self):
        from smartchem.smiles import parse_smiles
        # a human-declared NAME component cannot prove a structure -- a Molecule query does not match it (sound).
        named = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "n", "named bottle",
            (MaterialComponent.known("ethanol", "active", 0.99, 1.0),), Phase.LIQUID, "label",
        )
        assert named.satisfies(parse_smiles("CCO"), min_assay=0.99) is FitnessVerdict.IDENTITY_ABSENT

    def test_a_structure_key_cannot_satisfy_a_name_query(self):
        # the reverse: a structure-keyed component is not matched by a bare name string (the namespaces are disjoint).
        assert self._ethanol_bottle().satisfies("ethanol", min_assay=0.99) is FitnessVerdict.IDENTITY_ABSENT

    def test_the_name_constructors_reject_a_reserved_structure_prefix(self):
        with pytest.raises(ValueError, match="structure-key prefix"):
            MaterialComponent.known("struct:deadbeef", "active", 0.0, 1.0)
        with pytest.raises(ValueError, match="structure-key prefix"):
            MaterialComponent.unknown_fraction("struct-asgiven:x", "active")

    def test_active_fraction_interval_rejects_a_bad_required_type(self):
        with pytest.raises(TypeError, match="Molecule.*or a str|str.*declared name"):
            self._ethanol_bottle().active_fraction_interval(42)

    def test_of_molecule_carries_the_full_assay_interval(self):
        from smartchem.smiles import parse_smiles
        bottle = self._ethanol_bottle(0.90, 0.95)
        assert bottle.active_fraction_interval(parse_smiles("CCO")) == pytest.approx((0.90, 0.95))
        assert bottle.satisfies(parse_smiles("CCO"), min_assay=0.99) is FitnessVerdict.INSUFFICIENT_ASSAY

    def test_stereoisomers_share_a_key_the_documented_ID_STEREO_limitation(self):
        from smartchem.smiles import parse_smiles
        # HONEST SCOPE: the canonical digest is CONSTITUTIONAL (connectivity), stereo-BLIND. R and S alanine share a
        # key, so a material of one currently satisfies a query for the other. Distinguishing configuration needs
        # real CIP R/S-parity -- the BLOCKED ID-STEREO layer -- which this key does not claim. Pinned so no future
        # change silently claims stereo-soundness (and so the limitation is visible, not a hidden fails-open).
        r_ala = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "r-ala", "R-alanine",
            (MaterialComponent.of_molecule(parse_smiles("N[C@@H](C)C(=O)O"), "active", 0.99, 1.0),),
            Phase.SOLID, "reagent label",
        )
        assert r_ala.satisfies(parse_smiles("N[C@H](C)C(=O)O"), min_assay=0.99) is FitnessVerdict.SATISFIES

    def test_isotopologues_share_a_key_the_canonical_digest_is_isotope_blind(self):
        from smartchem.smiles import parse_smiles
        # HONEST SCOPE (cf. stereo): the digest is also isotope-blind -- H2O and D2O share a key, so a material of
        # one currently satisfies a query for the other. An isotope-aware digest is a separate deferred layer.
        light = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "h2o", "water",
            (MaterialComponent.of_molecule(parse_smiles("O"), "active", 0.99, 1.0),), Phase.LIQUID, "label",
        )
        assert light.satisfies(parse_smiles("[2H]O[2H]"), min_assay=0.99) is FitnessVerdict.SATISFIES

    def test_a_material_satisfies_its_own_identity_written_kekule(self):
        from smartchem.smiles import parse_smiles
        # CANON-KEKULE-01 (now FIXED): a naphthalene material satisfies a query for naphthalene written as an
        # explicit Kekule -- it is the SAME molecule, and the canonicalizer now normalises the pi-bond placement so
        # the aromatic and explicit-Kekule spellings of a fused aromatic share ONE identity.  (Was a strict-xfail.)
        naph = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "naph", "naphthalene",
            (MaterialComponent.of_molecule(parse_smiles("c1ccc2ccccc2c1"), "active", 0.99, 1.0),), Phase.SOLID, "GC",
        )
        assert naph.satisfies(parse_smiles("C1=CC=C2C=CC=CC2=C1"), min_assay=0.9) is FitnessVerdict.SATISFIES


class TestRoundVMaterialFields:
    def test_schemas_are_current_and_older_ids_refused(self):
        """component v1alpha2 (Round V D8); stock-material v1alpha3 (Round V X-high D18: +phase_evidence). Every older
        id is refused -- none was ever released on a wire, so there is nothing to migrate."""
        from smartchem.experiment.stock import MATERIAL_COMPONENT_SCHEMA

        assert STOCK_MATERIAL_SCHEMA.endswith("stock-material-v1alpha3")
        assert MATERIAL_COMPONENT_SCHEMA.endswith("material-component-v1alpha2")
        with pytest.raises(ValueError, match="schema_version"):
            MaterialComponent("smartchem.experiment/material-component-v1alpha1", "x", "active", 0.0, 1.0)
        for stale in ("smartchem.experiment/stock-material-v1alpha1", "smartchem.experiment/stock-material-v1alpha2"):
            with pytest.raises(ValueError, match="schema_version"):
                StockMaterial(stale, "m", "m", (MaterialComponent.unknown_fraction("x", "active"),), Phase.LIQUID, "p")

    def test_basis_defaults_unknown_and_evidence_defaults_none(self):
        from smartchem.material_spec import ConcentrationBasis, EvidenceKind

        c = MaterialComponent.known("acetic acid", "active", 0.99, 1.0)
        assert c.basis is ConcentrationBasis.UNKNOWN and c.evidence is None
        view = _glacial().spec_view("acetic acid")
        assert view.interval_evidence is EvidenceKind.UNKNOWN and view.basis is ConcentrationBasis.UNKNOWN

    def test_evidence_must_match_the_fraction_slots_exactly(self):
        from dataclasses import replace

        from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
        from smartchem.material_spec import ConcentrationBasis, EvidenceKind

        ev = IntervalEvidence.build(
            kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
            inputs=(TypedInput("low", "0.3", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                    TypedInput("high", "0.7", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
            domain_of_validity="my own bottle")
        good = MaterialComponent.evidenced("acetic acid", "active", ev)
        assert (good.min_fraction, good.max_fraction) == (0.3, 0.7)
        assert good.basis is ConcentrationBasis.MASS_FRACTION
        # 0.1 + 0.2 is NOT 0.3 in binary float; the exact comparison refuses the drifted slot
        with pytest.raises(ValueError, match="does not equal"):
            replace(good, min_fraction=0.1 + 0.2)
        with pytest.raises(TypeError, match="IntervalEvidence"):
            replace(good, evidence="SOURCE_QUOTED")

    def test_minimum_fraction_sum_is_exact(self):
        # 0.1 + 0.2 + 0.7 sums to 1.0000000000000002 in float but exactly 1 through the shortest repr
        StockMaterial(STOCK_MATERIAL_SCHEMA, "m", "m", (
            MaterialComponent.known("a", "x", 0.1, 0.1), MaterialComponent.known("b", "x", 0.2, 0.2),
            MaterialComponent.known("c", "x", 0.7, 0.7)), Phase.LIQUID, "p")
        with pytest.raises(ValueError, match="sum above"):
            StockMaterial(STOCK_MATERIAL_SCHEMA, "m", "m", (
                MaterialComponent.known("a", "x", 0.5, 0.5),
                MaterialComponent.known("b", "x", 0.500000001, 0.6)), Phase.LIQUID, "p")


class TestPhaseEvidence:
    """Round V X-high (barrier D18, I3): the bottle phase is an EVIDENCE-GRADED claim. Round V graded composition and
    every material state, then left phase an ungraded scalar that certified FIT on a match and BLOCKED on a mismatch
    whoever asserted it -- the F71 sin. The capability compiler now reads only ``phase_claim``."""

    @staticmethod
    def _bottle(phase=Phase.LIQUID, **kw):
        return StockMaterial(STOCK_MATERIAL_SCHEMA, "m", "m", (MaterialComponent.known("a", "active", 0, 1),),
                             phase, "src", **kw)

    def test_schema_is_v1alpha3(self):
        assert STOCK_MATERIAL_SCHEMA == "smartchem.experiment/stock-material-v1alpha3"
        with pytest.raises(ValueError, match="schema_version"):
            StockMaterial("smartchem.experiment/stock-material-v1alpha2", "m", "m",
                          (MaterialComponent.known("a", "active", 0, 1),), Phase.LIQUID, "src")

    def test_default_phase_evidence_is_unknown_and_certifies_nothing(self):
        from smartchem.material_spec import (EvidenceKind, PhaseClaim, SpecVerdict, compare_phase)
        bottle = self._bottle()
        assert bottle.phase_evidence is EvidenceKind.UNKNOWN
        assert bottle.phase_claim == PhaseClaim(Phase.LIQUID, EvidenceKind.UNKNOWN)
        sourced = PhaseClaim(Phase.LIQUID, EvidenceKind.SOURCE_QUOTED)
        # an ungraded bottle phase can neither discharge a sourced phase demand ...
        assert compare_phase(sourced, bottle.phase_claim)[0] is SpecVerdict.UNDETERMINED
        # ... nor refute one
        assert compare_phase(PhaseClaim(Phase.SOLID, EvidenceKind.SOURCE_QUOTED), bottle.phase_claim)[0] \
            is SpecVerdict.UNDETERMINED

    def test_a_user_declared_phase_certifies_against_a_sourced_demand(self):
        from smartchem.material_spec import EvidenceKind, PhaseClaim, SpecVerdict, compare_phase
        bottle = self._bottle(phase_evidence=EvidenceKind.USER_DECLARED)
        assert compare_phase(PhaseClaim(Phase.LIQUID, EvidenceKind.SOURCE_QUOTED), bottle.phase_claim)[0] \
            is SpecVerdict.SATISFIES
        assert compare_phase(PhaseClaim(Phase.SOLID, EvidenceKind.SOURCE_QUOTED), bottle.phase_claim)[0] \
            is SpecVerdict.VIOLATES

    def test_an_unknown_phase_is_no_claim_and_carries_no_evidence(self):
        from smartchem.material_spec import EvidenceKind
        assert self._bottle(Phase.UNKNOWN).phase_claim is None
        with pytest.raises(ValueError, match="phase UNKNOWN cannot carry"):
            self._bottle(Phase.UNKNOWN, phase_evidence=EvidenceKind.USER_DECLARED)

    def test_phase_evidence_must_be_an_evidence_kind(self):
        with pytest.raises(TypeError, match="phase_evidence"):
            self._bottle(phase_evidence="USER_DECLARED")

    def test_phase_evidence_moves_the_digest_and_shows_in_render(self):
        from smartchem.material_spec import EvidenceKind
        ungraded, declared = self._bottle(), self._bottle(phase_evidence=EvidenceKind.USER_DECLARED)
        assert ungraded.digest != declared.digest
        assert "phase evidence USER_DECLARED" in declared.render()
        assert "phase evidence UNKNOWN" in ungraded.render()

    def test_the_commodity_bridge_stays_phase_unknown_evidence_unknown(self):
        from smartchem.data.reagents import COMMODITY_REAGENTS
        from smartchem.material_spec import EvidenceKind
        mat = stock_material_from_commodity(COMMODITY_REAGENTS[0])
        assert mat.phase is Phase.UNKNOWN and mat.phase_evidence is EvidenceKind.UNKNOWN and mat.phase_claim is None

    def test_the_legacy_assay_helpers_ignore_phase_evidence(self):
        from smartchem.material_spec import EvidenceKind
        a, b = self._bottle(), self._bottle(phase_evidence=EvidenceKind.USER_DECLARED)
        assert a.satisfies("a", min_assay=0.5) is b.satisfies("a", min_assay=0.5)
        assert a.satisfies_band("a", low=0.1, high=0.9) is b.satisfies_band("a", low=0.1, high=0.9)
