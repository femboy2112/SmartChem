"""Waves A1-A3: Descriptive vs Executable authority + the ADMISSION model.  A recognizer naming a family is not a
rate law; a bare citation is not a verified source; a caller-declared composition is not a verified molecular
identity.  SYNTHETIC/experimental sandbox."""
import numpy as np
import pytest

from experiments.sandbox_foundation.mechanism_adapter import adapt_step, derive_inventory
from experiments.sandbox_foundation.mechanism_types import (
    AdmissionLevel, AdmissionReceipt, ConversionRefusal, ConversionRefusalKind as K, DescriptiveMechanism,
    ExecutableMechanism, KineticLaw, SourceRecord, SpeciesIdentity, VerificationStatus,
    expected_rate_constant_units)
from experiments.sandbox_foundation.twocell import Mechanism
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

A, B, W = parse_smiles("CCO"), parse_smiles("COC"), parse_smiles("O")
OMIT = ("competing dehydration to ethene not modelled",)


def isomerization_descriptive(**kw):
    step = ExperimentStep.assembling(B, (A,), (B,))
    return DescriptiveMechanism.from_derivations([adapt_step(step)], **kw)


def _record(version="3rd ed", model_form="elementary unimolecular"):
    return SourceRecord(citation="Imaginary Handbook, tbl 4.2", version=version, species=("ethanol", "DME"),
                        units="s^-1", conditions="298.15 K, 1 bar, ideal", model_form=model_form,
                        parameter_range="280-320 K")


def declared_law(**kw):
    """SOURCE_DECLARED: a bare citation string, nothing checked."""
    base = dict(k_f=2.0e-3, k_r=1.0e-3, reversible=True, admission=AdmissionLevel.SOURCE_DECLARED, k_f_units="s^-1",
                k_r_units="s^-1", source="Imaginary Handbook, tbl 4.2 (placeholder citation for a test)")
    base.update(kw)
    return KineticLaw(**base)


def verified_law(**kw):
    """SOURCE_VERIFIED: a structured, VERIFIED admission receipt."""
    base = dict(k_f=2.0e-3, k_r=1.0e-3, reversible=True, admission=AdmissionLevel.SOURCE_VERIFIED, k_f_units="s^-1",
                k_r_units="s^-1", receipt=AdmissionReceipt(_record(), VerificationStatus.VERIFIED,
                                                           reviewer="test evidence policy v1"))
    base.update(kw)
    return KineticLaw(**base)


def synthetic_law(**kw):
    base = dict(k_f=0.5, k_r=0.1, reversible=True, admission=AdmissionLevel.SYNTHETIC, k_f_units="s^-1",
                k_r_units="s^-1", assumption="user hypothesis: first-order both ways, made-up constants")
    base.update(kw)
    return KineticLaw(**base)


class TestDescriptive:
    def test_real_conserving_step_becomes_descriptive_with_unknown_kinetics(self):
        d = isomerization_descriptive()
        assert d.kinetics == (None,)
        assert d.is_executable is False
        assert d.unknowns == ("kinetics[R0]",)
        assert d.N[:, 0].tolist() in ([-1, 1], [1, -1]) and not np.any(d.E @ d.N)
        assert d.E.dtype == np.int64
        assert d.species_identity is SpeciesIdentity.VERIFIED           # bound to real Molecule identities

    def test_descriptive_has_no_run_surface(self):
        d = isomerization_descriptive()
        assert not hasattr(d, "to_twocell") and not hasattr(d, "rate_vector")

    def test_explicitly_unknown_thermo_is_listed_not_zeroed(self):
        d = isomerization_descriptive(thermo={"dH_J_per_mol": None})
        assert "thermo.dH_J_per_mol" in d.unknowns and d.thermo["dH_J_per_mol"] is None

    def test_recognizer_family_name_confers_no_authority(self):
        d = isomerization_descriptive(recognized_family="acyl-transfer (VOUCHED)")
        assert d.is_executable is False
        with pytest.raises(ConversionRefusal) as ei:
            d.to_executable(omissions=OMIT)
        assert ei.value.kind is K.KINETICS_UNAVAILABLE

    def test_E_cannot_be_injected(self):
        d = isomerization_descriptive()
        with pytest.raises(TypeError):
            DescriptiveMechanism(d.species, d.compositions, d.charges, d.reactant, d.product, ("R0",), (None,),
                                 E=np.zeros((1, 2), dtype=int))

    def test_nonconserving_structure_cannot_be_built_even_by_hand(self):
        comps = ((("C", 1), ("H", 4)), (("C", 1), ("O", 2)))
        with pytest.raises(ConversionRefusal) as ei:
            DescriptiveMechanism(("CH4", "CO2"), comps, (0, 0), np.array([[1], [0]]), np.array([[0], [1]]),
                                 ("R0",), (None,))
        assert ei.value.kind is K.INVENTORY_REFUSED


class TestConversion:
    def test_missing_kinetics_is_typed_unavailable(self):
        with pytest.raises(ConversionRefusal) as ei:
            isomerization_descriptive().to_executable(omissions=OMIT)
        assert ei.value.kind is K.KINETICS_UNAVAILABLE

    def test_none_or_incomplete_law_is_unavailable_never_zero(self):
        d = isomerization_descriptive()
        for laws in ([None], [declared_law(k_r=None)], [declared_law(k_f=None)], []):
            with pytest.raises(ConversionRefusal) as ei:
                d.to_executable(laws, omissions=OMIT)
            assert ei.value.kind is K.KINETICS_UNAVAILABLE

    def test_declared_law_converts_but_is_not_yet_a_scientific_claim(self):
        ex = isomerization_descriptive().to_executable([declared_law()], omissions=OMIT)
        assert isinstance(ex, ExecutableMechanism) and ex.is_executable
        assert ex.admission_level is AdmissionLevel.SOURCE_DECLARED
        assert ex.species_identity is SpeciesIdentity.VERIFIED          # species are real...
        assert ex.scientific_claim is False                            # ...but a bare citation is not verified (A2)
        assert ex.to_twocell().label == "SOURCE_DECLARED"

    def test_verified_law_with_verified_species_is_a_scientific_claim(self):
        ex = isomerization_descriptive().to_executable([verified_law()], omissions=OMIT)
        assert ex.admission_level is AdmissionLevel.SOURCE_VERIFIED
        assert ex.species_identity is SpeciesIdentity.VERIFIED
        assert ex.scientific_claim is True
        mech = ex.to_twocell()
        assert isinstance(mech, Mechanism) and mech.label == "SOURCE_VERIFIED"
        mech.require_complete()
        assert not np.any(mech.constitution_residual())

    def test_synthetic_law_runs_but_is_never_a_scientific_claim(self):
        ex = isomerization_descriptive().to_executable([synthetic_law()], omissions=OMIT)
        assert ex.is_executable and ex.scientific_claim is False
        assert ex.admission_level is AdmissionLevel.SYNTHETIC and ex.to_twocell().label == "SYNTHETIC"

    def test_one_weaker_law_taints_the_whole_mechanism(self):
        d = DescriptiveMechanism.from_derivations([adapt_step(ExperimentStep.assembling(B, (A,), (B,))),
                                                   adapt_step(ExperimentStep.assembling(A, (B,), (A,)))])
        ex = d.to_executable([verified_law(), synthetic_law()], omissions=OMIT)
        assert ex.admission_level is AdmissionLevel.SYNTHETIC       # the weakest law caps the mechanism
        assert ex.scientific_claim is False

    def test_provenance_statements_are_mandatory(self):
        with pytest.raises(ConversionRefusal) as ei:
            declared_law(source="  ")
        assert ei.value.kind is K.PROVENANCE_MISSING
        with pytest.raises(ConversionRefusal) as ei:
            synthetic_law(assumption="")
        assert ei.value.kind is K.PROVENANCE_MISSING

    def test_omissions_must_be_declared(self):
        for om in ((), ("  ",)):
            with pytest.raises(ConversionRefusal) as ei:
                isomerization_descriptive().to_executable([declared_law()], omissions=om)
            assert ei.value.kind is K.OMISSIONS_UNDECLARED

    def test_bad_rate_values_are_refused(self):
        d = isomerization_descriptive()
        for bad in (-1.0, float("nan"), float("inf"), True):
            with pytest.raises(ConversionRefusal) as ei:
                d.to_executable([declared_law(k_f=bad)], omissions=OMIT)
            assert ei.value.kind is K.INVALID_KINETIC_LAW

    def test_units_are_dimension_checked(self):
        with pytest.raises(ConversionRefusal) as ei:
            isomerization_descriptive().to_executable([declared_law(k_f_units="m^3 mol^-1 s^-1")], omissions=OMIT)
        assert ei.value.kind is K.DIMENSION_MISMATCH
        assert expected_rate_constant_units(1) == "s^-1"
        assert expected_rate_constant_units(2) == "m^3 mol^-1 s^-1"
        assert expected_rate_constant_units(0) == "m^-3 mol s^-1"

    def test_bimolecular_elementary_needs_second_order_units(self):
        step = ExperimentStep.assembling(parse_smiles("CCOC(C)=O"), (parse_smiles("CCO"), parse_smiles("CC(=O)O")),
                                         (parse_smiles("CCOC(C)=O"), W))
        d = DescriptiveMechanism.from_derivations([adapt_step(step)])
        good = declared_law(k_f_units="m^3 mol^-1 s^-1", k_r_units="m^3 mol^-1 s^-1")
        assert d.to_executable([good], omissions=OMIT).is_executable
        with pytest.raises(ConversionRefusal) as ei:
            d.to_executable([declared_law()], omissions=OMIT)       # first-order units on a bimolecular law
        assert ei.value.kind is K.DIMENSION_MISMATCH

    def test_selection_of_a_subset_of_reactions(self):
        d = DescriptiveMechanism.from_derivations([
            adapt_step(ExperimentStep.assembling(B, (A,), (B,))),
            adapt_step(ExperimentStep.assembling(A, (B,), (A,)))])
        ex = d.to_executable([declared_law()], omissions=OMIT, selected=[1])
        assert ex.reaction_labels == ("R1",) and ex.N.shape[1] == 1
        for bad in ([], [5], [0, 0], [True]):
            with pytest.raises(ConversionRefusal) as ei:
                d.to_executable([declared_law()], omissions=OMIT, selected=bad)
            assert ei.value.kind is K.SELECTION_INVALID

    def test_empirical_law_needs_explicit_orders(self):
        d = isomerization_descriptive()
        with pytest.raises(ConversionRefusal) as ei:
            d.to_executable([declared_law(kinetics="empirical")], omissions=OMIT)
        assert ei.value.kind is K.INVALID_KINETIC_LAW
        law = declared_law(kinetics="empirical", forward_orders=(1.5, 0.0), reverse_orders=(0.0, 1.0),
                           k_f_units=expected_rate_constant_units(1.5), k_r_units="s^-1")
        mech = d.to_executable([law], omissions=OMIT).to_twocell()
        assert mech.kinetics == "empirical" and mech.order_f[:, 0].tolist() == [1.5, 0.0]

    def test_executable_cannot_be_forged_by_hand_either(self):
        d = isomerization_descriptive()
        comps = ((("C", 1), ("H", 4)), (("C", 1), ("O", 2)))
        with pytest.raises(ConversionRefusal) as ei:
            ExecutableMechanism(("CH4", "CO2"), comps, (0, 0), np.array([[1], [0]]), np.array([[0], [1]]),
                                ("R0",), (declared_law(),), OMIT)
        assert ei.value.kind is K.INVENTORY_REFUSED
        with pytest.raises(TypeError):
            ExecutableMechanism(d.species, d.compositions, d.charges, d.reactant, d.product, ("R0",),
                                (declared_law(),), OMIT, E=d.E)

    def test_exact_integers_survive_to_the_float_boundary_unchanged(self):
        ex = isomerization_descriptive().to_executable([declared_law()], omissions=OMIT)
        assert ex.E.dtype == ex.reactant.dtype == ex.product.dtype == np.int64
        mech = ex.to_twocell()
        assert np.array_equal(mech.E, ex.E) and np.array_equal(mech.N, ex.N)


class TestA1StrictProvenance:
    """A1: the admission value is runtime-validated.  An unknown string / int / None / enum lookalike is a
    fail-closed refusal -- never silently folded to a sourced/verified classification."""

    @pytest.mark.parametrize("bad", ["FABRICATED", "SOURCED", "SOURCE_VERIFIED", None, 123, 1.0,
                                     VerificationStatus.VERIFIED])
    def test_invalid_admission_is_refused_not_folded(self, bad):
        with pytest.raises(ConversionRefusal) as ei:
            KineticLaw(k_f=1.0, k_r=1.0, reversible=True, admission=bad, k_f_units="s^-1", k_r_units="s^-1",
                       source="x", assumption="x")
        assert ei.value.kind is K.ADMISSION_INVALID

    def test_a_valid_but_bare_level_still_needs_its_statement(self):
        with pytest.raises(ConversionRefusal) as ei:      # SOURCE_DECLARED with no citation
            KineticLaw(k_f=1.0, k_r=1.0, reversible=True, admission=AdmissionLevel.SOURCE_DECLARED,
                       k_f_units="s^-1", k_r_units="s^-1")
        assert ei.value.kind is K.PROVENANCE_MISSING


class TestA2CitationDoesNotMintScience:
    def test_source_verified_requires_a_receipt_not_a_string(self):
        with pytest.raises(ConversionRefusal) as ei:
            KineticLaw(k_f=1.0, k_r=1.0, reversible=True, admission=AdmissionLevel.SOURCE_VERIFIED,
                       k_f_units="s^-1", k_r_units="s^-1", source="a citation string, not a receipt")
        assert ei.value.kind is K.ADMISSION_INVALID

    @pytest.mark.parametrize("status", [VerificationStatus.UNVERIFIED, VerificationStatus.REVOKED])
    def test_unverified_or_revoked_receipt_cannot_back_a_verified_level(self, status):
        with pytest.raises(ConversionRefusal) as ei:
            verified_law(receipt=AdmissionReceipt(_record(), status))
        assert ei.value.kind is K.ADMISSION_INVALID

    def test_benchmark_level_requires_a_named_benchmark(self):
        with pytest.raises(ConversionRefusal) as ei:
            KineticLaw(k_f=1.0, k_r=1.0, reversible=True, admission=AdmissionLevel.BENCHMARK_VALIDATED,
                       k_f_units="s^-1", k_r_units="s^-1",
                       receipt=AdmissionReceipt(_record(), VerificationStatus.VERIFIED))
        assert ei.value.kind is K.ADMISSION_INVALID

    def test_a_source_update_moves_admission_identity_but_not_model_content(self):
        ex1 = isomerization_descriptive().to_executable(
            [verified_law(receipt=AdmissionReceipt(_record(version="3rd ed"), VerificationStatus.VERIFIED))],
            omissions=OMIT)
        ex2 = isomerization_descriptive().to_executable(
            [verified_law(receipt=AdmissionReceipt(_record(version="4th ed, revised k"),
                                                   VerificationStatus.VERIFIED))], omissions=OMIT)
        assert ex1.admission_identities != ex2.admission_identities          # evidence identity moved
        m1, m2 = ex1.to_twocell(), ex2.to_twocell()
        assert np.array_equal(m1.N, m2.N) and np.array_equal(m1.E, m2.E)     # model content UNCHANGED


class TestA3NoForgedChemicalAuthority:
    def test_handbuilt_from_caller_compositions_is_untrusted_and_cannot_claim_science(self):
        # the adversary: label two species as different real chemicals, supply fabricated EQUAL inventories,
        # and attach a VERIFIED kinetic receipt.  The kinetics verify, but the species are caller-declared.
        comps = ((("C", 2), ("H", 6), ("O", 1)), (("C", 2), ("H", 6), ("O", 1)))   # 'ethanol'/'DME', both C2H6O
        ex = ExecutableMechanism(("ethanol", "dimethyl_ether"), comps, (0, 0),
                                 np.array([[1], [0]]), np.array([[0], [1]]), ("R0",), (verified_law(),), OMIT)
        assert ex.species_identity is SpeciesIdentity.UNTRUSTED
        assert ex.admission_level is AdmissionLevel.SOURCE_VERIFIED       # kinetics verified...
        assert ex.scientific_claim is False                             # ...but forged species -> NO claim (A3)

    def test_verified_species_via_the_adapter_do_carry_the_claim(self):
        ex = isomerization_descriptive().to_executable([verified_law()], omissions=OMIT)
        assert ex.species_identity is SpeciesIdentity.VERIFIED and ex.scientific_claim is True

    def test_species_identity_is_not_a_public_constructor_argument(self):
        # evil-morty Finding 1: a caller must NOT be able to DECLARE itself VERIFIED.  species_identity is
        # init=False, so passing it is a TypeError, and a plain hand construction is UNTRUSTED.
        comps = ((("C", 2), ("H", 6), ("O", 1)), (("C", 2), ("H", 6), ("O", 1)))
        with pytest.raises(TypeError):
            ExecutableMechanism(("ethanol", "dimethyl_ether"), comps, (0, 0),
                                np.array([[1], [0]]), np.array([[0], [1]]), ("R0",), (verified_law(),), OMIT,
                                SpeciesIdentity.VERIFIED, ("forged-key-A", "forged-key-B"))
        ex = ExecutableMechanism(("ethanol", "dimethyl_ether"), comps, (0, 0),
                                 np.array([[1], [0]]), np.array([[0], [1]]), ("R0",), (verified_law(),), OMIT)
        assert ex.species_identity is SpeciesIdentity.UNTRUSTED and ex.scientific_claim is False


class TestAdapterIntegration:
    def test_forged_E_never_reaches_the_type_layer(self):
        from experiments.sandbox_foundation.mechanism_adapter import AdapterRefusal
        with pytest.raises(AdapterRefusal):
            derive_inventory((parse_smiles("C"), parse_smiles("O=O")), (parse_smiles("O=C=O"),),
                             supplied_E=[[1, 0, 1], [0, 0, 0], [0, 2, 2], [0, 0, 0]],
                             supplied_labels=("C", "H", "O", "charge"))
