"""Round V (barrier D7/D8): typed, digestible, re-computable interval evidence.

Retires the callable-bearing ``DerivedIntervalEvidence``. These pin: every production interval carries a record
that recomputes exactly through the CLOSED kernel registry; a label can never claim more than its kernel
(F63/F71: arbitrary width only as ASSUMED; SOURCE_QUOTED never over a conversion); per-volume solubility can
never enter the per-100-g-solvent kernel (F72/M75); the evidence enters the material AND profile digests
(F70/M73); and an ASSUMED stock interval is reported ASSUMED by ``spec_view`` (M76).
"""
from dataclasses import replace
from fractions import Fraction

import pytest

from smartchem.contracts import canonical_digest
from smartchem.data import material_library as ml
from smartchem.data.derived_evidence import (
    KERNELS,
    PRECISION_DP,
    DerivationKernel,
    InputUnit,
    IntervalEvidence,
    TypedInput,
    canonical_decimal,
)
from smartchem.experiment.stock import STOCK_MATERIAL_SCHEMA, MaterialComponent, Phase, StockMaterial
from smartchem.material_spec import (
    CERTIFYING_STOCK_EVIDENCE,
    CompositionConstraint,
    ConcentrationBasis,
    DilutionState,
    EvidenceKind,
    HydrationState,
    MaterialSpecification,
    SaturationState,
    SpecVerdict,
    StateClaim,
    Tolerance,
    compare_specification,
)

LOC = "https://example.org/fixture-source"
MF = ConcentrationBasis.MASS_FRACTION


def _q(name, value, unit=InputUnit.PERCENT, kind=EvidenceKind.SOURCE_QUOTED):
    return TypedInput(name, value, unit, kind, LOC)


def _ev(kind, low, high, kernel, inputs=(), basis=MF, locators=(LOC,), parent=None):
    return IntervalEvidence(kind, low, high, basis, locators, kernel, inputs, "fixture domain", parent)


# ---------------------------------------------------------------------------------------------------------------
class TestRecordShape:
    def test_record_is_digestible_and_has_no_callable_or_fraction(self):
        for key, ev in ml.INTERVAL_EVIDENCE.items():
            canonical_digest(ev)  # would raise on a callable / Fraction field (F70)
            assert isinstance(ev.low, str) and isinstance(ev.high, str), key
            assert ev.verify(), key

    def test_registry_is_closed_over_the_enum(self):
        assert set(KERNELS) == set(DerivationKernel)

    def test_canonical_decimal_spelling(self):
        assert canonical_decimal(Fraction(1)) == "1"
        assert canonical_decimal(Fraction(199, 200)) == "0.995"
        assert canonical_decimal(Fraction(0)) == "0"
        with pytest.raises(ValueError):
            canonical_decimal(Fraction(1, 3))

    def test_non_canonical_spelling_refused(self):
        # "1.0" and "1" are the same number; only the canonical spelling constructs, so equal intervals digest equal.
        with pytest.raises(ValueError, match="recomputes"):
            _ev(EvidenceKind.CLAMPED, "0.995", "1.0", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1,
                (_q("low", "99.5"), _q("high", "100.5")))

    def test_input_value_uses_the_strict_grammar(self):
        for bad in ("1/3", "1_000", " 5 ", "nan", "-1"):
            with pytest.raises(ValueError):
                TypedInput("low", bad, InputUnit.PERCENT, EvidenceKind.ASSUMED)

    def test_source_quoted_input_needs_a_locator(self):
        with pytest.raises(ValueError, match="source_locator"):
            TypedInput("low", "5", InputUnit.PERCENT, EvidenceKind.SOURCE_QUOTED, "")


# ---------------------------------------------------------------------------------------------------------------
class TestKernelKindCoherence:
    def test_identity_source_quoted_constructs(self):
        ev = _ev(EvidenceKind.SOURCE_QUOTED, "0.95", "0.98", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1,
                 (_q("low", "95"), _q("high", "98")))
        assert ev.interval == (Fraction(19, 20), Fraction(49, 50))

    def test_arbitrary_width_refused_unless_assumed(self):
        # F63/F71: the retired BROADENED label -- a nominal widened by an unsourced width -- cannot be dressed as
        # SOURCE_QUOTED / DERIVED; the only kernel expressing a free width is ASSUMED_BAND_V1 -> ASSUMED.
        nominal = (_q("nominal", "5"), TypedInput("half_width", "0.5", InputUnit.PERCENT, EvidenceKind.ASSUMED))
        for kind in (EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.CLAMPED, EvidenceKind.USER_DECLARED):
            with pytest.raises(ValueError, match="may only emit ASSUMED"):
                _ev(kind, "0.045", "0.055", DerivationKernel.ASSUMED_BAND_V1, nominal)
        ok = _ev(EvidenceKind.ASSUMED, "0.045", "0.055", DerivationKernel.ASSUMED_BAND_V1, nominal)
        assert ok.kind is EvidenceKind.ASSUMED
        # and the width cannot be smuggled through the identity kernel (no 'nominal' inputs there)
        with pytest.raises(ValueError, match="inputs named"):
            _ev(EvidenceKind.SOURCE_QUOTED, "0.045", "0.055", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, nominal)

    def test_source_quoted_with_a_conversion_kernel_refused(self):
        inputs = (_q("low", "36.0", InputUnit.G_PER_100G_SOLVENT), _q("high", "36.0", InputUnit.G_PER_100G_SOLVENT))
        good = IntervalEvidence.build(kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1,
                                      basis=MF, inputs=inputs, source_locators=(LOC,), domain_of_validity="25 C")
        assert good.kind is EvidenceKind.DERIVED
        with pytest.raises(ValueError, match="may only emit DERIVED"):
            replace(good, kind=EvidenceKind.SOURCE_QUOTED)

    def test_identity_kernel_refuses_non_source_quoted_inputs(self):
        with pytest.raises(ValueError, match="refuses input"):
            _ev(EvidenceKind.SOURCE_QUOTED, "0.95", "0.98", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1,
                (_q("low", "95", kind=EvidenceKind.ASSUMED), _q("high", "98")))

    def test_value_mismatch_refused(self):
        with pytest.raises(ValueError, match="recomputes"):
            _ev(EvidenceKind.SOURCE_QUOTED, "0.95", "0.99", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1,
                (_q("low", "95"), _q("high", "98")))

    def test_clamp_must_actually_clip(self):
        with pytest.raises(ValueError, match="must actually clip"):
            _ev(EvidenceKind.CLAMPED, "0.95", "0.98", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1,
                (_q("low", "95"), _q("high", "98")))
        clipped = _ev(EvidenceKind.CLAMPED, "0.995", "1", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1,
                      (_q("low", "99.5"), _q("high", "100.5")))
        assert clipped.interval == (Fraction(199, 200), Fraction(1))
        floor = _ev(EvidenceKind.CLAMPED, "0.97", "1", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, (_q("floor", "97"),))
        assert floor.kind is EvidenceKind.CLAMPED

    def test_clamp_refused_on_a_non_fraction_basis(self):
        with pytest.raises(ValueError, match="not valid on basis"):
            _ev(EvidenceKind.CLAMPED, "0.97", "1", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, (_q("floor", "97"),),
                basis=ConcentrationBasis.UNKNOWN)

    def test_sourced_kind_needs_locators_covering_its_inputs(self):
        with pytest.raises(ValueError, match="cite at least one"):
            _ev(EvidenceKind.SOURCE_QUOTED, "0.95", "0.98", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1,
                (_q("low", "95"), _q("high", "98")), locators=())
        with pytest.raises(ValueError, match="not among"):
            _ev(EvidenceKind.SOURCE_QUOTED, "0.95", "0.98", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1,
                (_q("low", "95"), _q("high", "98")), locators=("https://elsewhere.example",))

    def test_user_declared_and_unknown_kernels(self):
        ud = _ev(EvidenceKind.USER_DECLARED, "0.9", "0.95", DerivationKernel.USER_DECLARED_V1,
                 (TypedInput("low", "0.9", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                  TypedInput("high", "0.95", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)), locators=())
        assert ud.kind is EvidenceKind.USER_DECLARED
        unk = _ev(EvidenceKind.UNKNOWN, "0", "1", DerivationKernel.UNKNOWN_V1, locators=())
        assert unk.interval == (Fraction(0), Fraction(1))
        with pytest.raises(ValueError, match="recomputes"):
            _ev(EvidenceKind.UNKNOWN, "0", "0.5", DerivationKernel.UNKNOWN_V1, locators=())

    def test_complement_is_assumed_never_an_inherited_sourced_strength(self):
        # Wave-C1/C2: 1 - x is the solvent only under an unsourced BINARY-mixture premise -> ASSUMED, never the
        # parent's DERIVED/SOURCE_QUOTED (the complement of a sourced H2SO4 assay is not a sourced water assay).
        parent = ml.INTERVAL_EVIDENCE["sodium-chloride-saturated-aqueous/sodium chloride"]
        water = ml.INTERVAL_EVIDENCE["sodium-chloride-saturated-aqueous/water"]
        assert parent.kind is EvidenceKind.DERIVED and water.kind is EvidenceKind.ASSUMED
        assert water.interval == (1 - parent.interval[1], 1 - parent.interval[0])
        with pytest.raises(ValueError, match="may only emit ASSUMED"):
            replace(water, kind=EvidenceKind.SOURCE_QUOTED)
        assumed_parent = ml.INTERVAL_EVIDENCE["sodium-bicarbonate-5pct-aqueous/sodium bicarbonate"]
        with pytest.raises(ValueError, match="not valid on basis"):  # UNKNOWN basis: 1-x means nothing
            IntervalEvidence.build(kernel=DerivationKernel.COMPLEMENT_V1, basis=ConcentrationBasis.UNKNOWN,
                                   parent=assumed_parent, domain_of_validity="x")
        with pytest.raises(TypeError, match="parent"):
            _ev(EvidenceKind.DERIVED, "0.7", "0.8", DerivationKernel.COMPLEMENT_V1)


# ---------------------------------------------------------------------------------------------------------------
class TestSolubilityKernelUnits:
    @pytest.mark.parametrize("unit", [InputUnit.G_PER_100ML_SOLVENT, InputUnit.G_PER_100ML_SOLUTION,
                                      InputUnit.MG_PER_L, InputUnit.MG_PER_ML, InputUnit.PERCENT,
                                      InputUnit.PERCENT_UNSTATED_BASIS, InputUnit.FRACTION])
    def test_per_volume_or_other_units_refused_M75(self, unit):
        # F72/M75: a per-VOLUME solubility (isoamyl 2.5 g/100 mL, NaCl '1 g in 2.8 mL') is not g/100 g solvent.
        with pytest.raises(ValueError, match="refuses input"):
            IntervalEvidence.build(
                kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, basis=MF,
                inputs=(_q("low", "2.5", unit), _q("high", "2.5", unit)), source_locators=(LOC,),
                domain_of_validity="x")

    def test_assumed_inputs_refused(self):
        with pytest.raises(ValueError, match="refuses input"):
            IntervalEvidence.build(
                kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, basis=MF,
                inputs=(TypedInput("low", "36", InputUnit.G_PER_100G_SOLVENT, EvidenceKind.ASSUMED),
                        _q("high", "36", InputUnit.G_PER_100G_SOLVENT)),
                source_locators=(LOC,), domain_of_validity="x")

    def test_non_terminating_result_is_rounded_outward(self):
        ev = ml.INTERVAL_EVIDENCE["sodium-chloride-saturated-aqueous/sodium chloride"]
        exact = Fraction(36, 136)
        lo, hi = ev.interval
        assert lo <= exact <= hi and hi - lo == Fraction(1, 10 ** PRECISION_DP)
        assert (ev.low, ev.high) == ("0.264705", "0.264706")

    def test_old_band_over_the_real_kernel_fails(self):
        # the retired [0.23, 0.27] (and the g/100g-as-fraction 0.36) cannot be built over the solubility kernel
        inputs = (_q("low", "36.0", InputUnit.G_PER_100G_SOLVENT), _q("high", "36.0", InputUnit.G_PER_100G_SOLVENT))
        for lo, hi in (("0.23", "0.27"), ("0.36", "0.36")):
            with pytest.raises(ValueError, match="recomputes"):
                _ev(EvidenceKind.DERIVED, lo, hi, DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1,
                    inputs)


# ---------------------------------------------------------------------------------------------------------------
class TestLibraryBinding:
    _MATERIALS = {
        "glacial-acetic-acid-reagent-grade": ml.glacial_acetic_acid,
        "sulfuric-acid-concentrated-acs": ml.concentrated_sulfuric_acid,
        "magnesium-sulfate-anhydrous": ml.magnesium_sulfate_anhydrous,
        "isoamyl-alcohol-reagent-grade": ml.isoamyl_alcohol_reagent_grade,
        "isoamyl-alcohol-dilute-aqueous": ml.isoamyl_alcohol_dilute_aqueous,
        "household-white-vinegar": ml.household_white_vinegar,
        "sodium-bicarbonate-5pct-aqueous": ml.sodium_bicarbonate_wash_5pct,
        "sodium-chloride-saturated-aqueous": ml.sodium_chloride_saturated_wash,
        "wash-water": ml.wash_water,
    }

    def test_every_production_component_carries_its_evidence(self):
        seen = set()
        for mid, build in self._MATERIALS.items():
            mat = build()
            assert mat.material_id == mid
            for comp in mat.components:
                assert comp.evidence is not None, (mid, comp.role)
                assert comp.basis is comp.evidence.basis
                assert (comp.min_fraction, comp.max_fraction) == comp.evidence.as_floats()
                seen.add(id(comp.evidence))
        assert seen == {id(e) for e in ml.INTERVAL_EVIDENCE.values()}

    def test_expected_kinds_and_bases(self):
        e = ml.INTERVAL_EVIDENCE
        expect = {
            "glacial-acetic-acid-reagent-grade/acetic acid": (EvidenceKind.CLAMPED, MF),
            "sulfuric-acid-concentrated-acs/sulfuric acid": (EvidenceKind.SOURCE_QUOTED, MF),
            "magnesium-sulfate-anhydrous/magnesium sulfate": (EvidenceKind.CLAMPED, MF),
            "isoamyl-alcohol-reagent-grade/isoamyl alcohol": (EvidenceKind.ASSUMED, ConcentrationBasis.UNKNOWN),
            "isoamyl-alcohol-dilute-aqueous/isoamyl alcohol": (EvidenceKind.UNKNOWN, ConcentrationBasis.UNKNOWN),
            "household-white-vinegar/acetic acid": (EvidenceKind.ASSUMED, ConcentrationBasis.MASS_PER_VOLUME),
            "sodium-bicarbonate-5pct-aqueous/sodium bicarbonate": (EvidenceKind.ASSUMED, ConcentrationBasis.UNKNOWN),
            "sodium-bicarbonate-5pct-aqueous/water": (EvidenceKind.ASSUMED, ConcentrationBasis.UNKNOWN),
            "sodium-chloride-saturated-aqueous/sodium chloride": (EvidenceKind.DERIVED, MF),
            "sodium-chloride-saturated-aqueous/water": (EvidenceKind.ASSUMED, MF),  # COMPLEMENT -> ASSUMED
            "wash-water/water": (EvidenceKind.ASSUMED, ConcentrationBasis.UNKNOWN),
        }
        for key, (kind, basis) in expect.items():
            assert (e[key].kind, e[key].basis) == (kind, basis), key

    def test_isoamyl_dilute_is_unknown_not_a_relabelled_per_volume_figure(self):
        mat = ml.isoamyl_alcohol_dilute_aqueous()
        for comp in mat.components:
            assert comp.evidence.kernel is DerivationKernel.UNKNOWN_V1
            assert (comp.min_fraction, comp.max_fraction) == (0.0, 1.0)

    def test_nacl_uses_only_the_sourced_g_per_100g_figure(self):
        ev = ml.INTERVAL_EVIDENCE["sodium-chloride-saturated-aqueous/sodium chloride"]
        assert {i.value for i in ev.inputs} == {"36.0"}
        assert all(i.unit is InputUnit.G_PER_100G_SOLVENT and i.temperature_k == "298.15" for i in ev.inputs)

    def test_wash_water_no_longer_claims_distilled(self):
        w = ml.wash_water()
        text = " ".join((w.display_name, w.provenance, w.material_id, *w.formulation_notes)).lower()
        assert "distilled" not in text and "deionised" not in text

    def test_mismatched_evidence_cannot_bind(self):
        ev = ml.INTERVAL_EVIDENCE["sulfuric-acid-concentrated-acs/sulfuric acid"]
        with pytest.raises(ValueError, match="does not equal the component"):
            MaterialComponent(MaterialComponent.known("x", "active", 0.95, 0.99).schema_version,
                              "x", "active", 0.95, 0.99, MF, ev)
        with pytest.raises(ValueError, match="basis"):
            MaterialComponent(MaterialComponent.known("x", "active", 0.95, 0.98).schema_version,
                              "x", "active", 0.95, 0.98, ConcentrationBasis.UNKNOWN, ev)


# ---------------------------------------------------------------------------------------------------------------
class TestDigestsAndComparison:
    def test_evidence_change_moves_material_and_profile_digest_M73(self):
        from smartchem.capability.presets import research_lab

        base = ml.concentrated_sulfuric_acid()
        comp = base.components[0]
        # same interval, different kernel/kind/locator: the NUMBER is unchanged, the EVIDENCE is not (F70)
        alt_ev = IntervalEvidence.build(
            kernel=DerivationKernel.ASSUMED_BAND_V1, basis=MF,
            inputs=(TypedInput("low", "95", InputUnit.PERCENT, EvidenceKind.ASSUMED),
                    TypedInput("high", "98", InputUnit.PERCENT, EvidenceKind.ASSUMED)),
            domain_of_validity="fixture")
        assert alt_ev.interval == comp.evidence.interval
        swapped = replace(base, components=(replace(comp, evidence=alt_ev),))
        assert swapped.digest != base.digest
        relocated = replace(base, components=(replace(comp, evidence=replace(
            comp.evidence, source_locators=comp.evidence.source_locators + ("https://another.example",))),))
        assert relocated.digest != base.digest
        assert research_lab(material_inventory=(swapped,)).digest != research_lab(material_inventory=(base,)).digest
        assert research_lab(material_inventory=(relocated,)).digest != research_lab(material_inventory=(base,)).digest

    def test_assumed_stock_is_reported_assumed_by_spec_view_M76(self):
        wash = ml.sodium_bicarbonate_wash_5pct()
        view = wash.spec_view("sodium bicarbonate")
        assert view.interval_evidence is EvidenceKind.ASSUMED
        assert view.interval_evidence not in CERTIFYING_STOCK_EVIDENCE
        assert view.basis is ConcentrationBasis.UNKNOWN
        # even against a (hypothetically) sourced requirement on the same numbers, ASSUMED stock never certifies
        req = MaterialSpecification(composition=CompositionConstraint(
            "0.04", "0.06", MF, Tolerance.STATED_INTERVAL, EvidenceKind.SOURCE_QUOTED))
        verdict, _ = compare_specification(req, view)
        assert verdict is SpecVerdict.UNDETERMINED

    def test_assumed_band_on_a_known_basis_still_cannot_certify(self):
        # F71 on the stock side alone: an ASSUMED interval inside a SOURCE_QUOTED requirement is UNDETERMINED.
        ev = IntervalEvidence.build(
            kernel=DerivationKernel.ASSUMED_BAND_V1, basis=MF,
            inputs=(TypedInput("low", "0.99", InputUnit.FRACTION, EvidenceKind.ASSUMED),
                    TypedInput("high", "1", InputUnit.FRACTION, EvidenceKind.ASSUMED)),
            domain_of_validity="fixture")
        mat = StockMaterial(STOCK_MATERIAL_SCHEMA, "a", "a", (MaterialComponent.evidenced("acid", "active", ev),),
                            Phase.LIQUID, "fixture")
        req = MaterialSpecification(composition=CompositionConstraint(
            "0.98", "1", MF, Tolerance.FLOOR, EvidenceKind.SOURCE_QUOTED))
        assert compare_specification(req, mat.spec_view("acid"))[0] is SpecVerdict.UNDETERMINED

    def test_sourced_stock_can_certify_against_a_sourced_requirement(self):
        # the discriminating control: the same shape with a CLAMPED stock DOES certify (so the M76 UNDETERMINED
        # above is the evidence law, not a comparison that can never say yes).
        from smartchem.identity_parse import InputKind, resolve_target
        glacial = ml.glacial_acetic_acid()
        view = glacial.spec_view(resolve_target("acetic acid", InputKind.NAME).canonical())
        assert view.interval_evidence is EvidenceKind.CLAMPED and view.basis is MF
        req = MaterialSpecification(
            composition=CompositionConstraint("0.99", "1", MF, Tolerance.FLOOR, EvidenceKind.SOURCE_QUOTED),
            states=(StateClaim(DilutionState.NEAT, EvidenceKind.SOURCE_QUOTED),))
        assert compare_specification(req, view)[0] is SpecVerdict.SATISFIES

    def test_states_declared_only_where_provenance_states_them(self):
        def fam(m):  # Wave-C K1: states live on the ACTIVE component (the species they describe), not the bottle
            return {type(c.state): (c.state, c.evidence) for c in m.components[0].states}
        assert fam(ml.glacial_acetic_acid())[DilutionState] == (DilutionState.NEAT, EvidenceKind.USER_DECLARED)
        assert fam(ml.magnesium_sulfate_anhydrous())[HydrationState][0] is HydrationState.ANHYDROUS
        brine = fam(ml.sodium_chloride_saturated_wash())
        assert brine[SaturationState][0] is SaturationState.SATURATED and brine[DilutionState][0] is DilutionState.SOLUTION
        assert fam(ml.sodium_bicarbonate_wash_5pct())[DilutionState][0] is DilutionState.SOLUTION
        assert fam(ml.isoamyl_alcohol_dilute_aqueous())[DilutionState][0] is DilutionState.SOLUTION
        assert all(c.states == () for c in ml.concentrated_sulfuric_acid().components)
        assert all(c.states == () for c in ml.wash_water().components)

    def test_state_change_moves_the_digest(self):
        m = ml.magnesium_sulfate_anhydrous()
        stripped = replace(m, components=tuple(replace(c, states=()) for c in m.components))
        assert stripped.digest != m.digest
