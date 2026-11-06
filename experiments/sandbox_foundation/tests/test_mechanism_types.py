"""Waves A1-A3: Descriptive vs Executable authority + the ADMISSION model.  A recognizer naming a family is not a
rate law; a bare citation is not a verified source; a caller-declared composition is not a verified molecular
identity.  SYNTHETIC/experimental sandbox."""
import copy
import dataclasses
import json
import pickle
import tempfile
from pathlib import Path

import numpy as np
import pytest

from experiments.sandbox_foundation.mechanism_adapter import adapt_step, derive_inventory
from experiments.sandbox_foundation.mechanism_types import (
    AdmissionDomainError, AdmissionLevel, AdmissionPolicy, AdmissionReceipt, ConversionRefusal,
    ConversionRefusalKind as K, DEFAULT_POLICY, DescriptiveMechanism, ExecutableMechanism, KineticLaw, SourceBinding,
    SourceRecord, SourceStore, SpeciesIdentity, VerificationStatus, expected_rate_constant_units)
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


def write_source(root, record_id="iso", version="3rd ed", *, k_f=2.0e-3, k_r=1.0e-3, T=(280.0, 320.0),
                 conc_max=None, status="current", supersedes=None, validation=None, entry="iso",
                 reactants=("CCO",), products=("COC",), units="s^-1", reversible=True):
    """Write one source ARTIFACT (the thing a SourceStore actually opens) -- test-side curator."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    e = {"reactants": [{"smiles": x, "count": 1} for x in reactants],
         "products": [{"smiles": x, "count": 1} for x in products],
         "kinetics": "elementary", "reversible": reversible, "k_f": {"value": k_f, "units": units},
         "conditions": {"T_K": list(T), "phase": "liquid", "standard_state": "pure liquid, 1 bar"},
         "assumptions": ["ideal dilute", "no catalyst"]}
    if reversible:
        e["k_r"] = {"value": k_r, "units": units}
    if conc_max is not None:
        e["conditions"]["conc_max_mol_m3"] = conc_max
    if validation is not None:
        e["validation"] = validation
    art = {"record_id": record_id, "version": version, "title": f"Imaginary Handbook {version}", "status": status,
           "entries": {entry: e}}
    if supersedes is not None:
        art["supersedes"] = supersedes
    path = root / f"{record_id}@{version}.json"
    path.write_text(json.dumps(art))
    return path


# a shared TEST store the policy below trusts (the default policy trusts only the repo's DEFAULT_STORE)
SRC_DIR = Path(tempfile.mkdtemp(prefix="sc_sources_"))
write_source(SRC_DIR)
STORE = SourceStore(SRC_DIR)
POLICY = AdmissionPolicy((STORE,))
_ISO = dict(k_f=2.0e-3, k_r=1.0e-3, reversible=True, k_f_units="s^-1", k_r_units="s^-1",
            validity_T_K=(280.0, 320.0))
ISO_RECEIPT = STORE.issue_receipt("iso", "3rd ed", "iso", **_ISO)


def declared_law(**kw):
    """SOURCE_DECLARED: a bare citation string, nothing checked."""
    base = dict(k_f=2.0e-3, k_r=1.0e-3, reversible=True, admission=AdmissionLevel.SOURCE_DECLARED, k_f_units="s^-1",
                k_r_units="s^-1", source="Imaginary Handbook, tbl 4.2 (placeholder citation for a test)")
    base.update(kw)
    return KineticLaw(**base)


def verified_law(**kw):
    """SOURCE_VERIFIED: backed by a receipt a SourceStore ISSUED from an inspected artifact (not caller-assembled)."""
    base = dict(k_f=2.0e-3, k_r=1.0e-3, reversible=True, admission=AdmissionLevel.SOURCE_VERIFIED, k_f_units="s^-1",
                k_r_units="s^-1", receipt=ISO_RECEIPT, validity_T_K=(280.0, 320.0))
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
        assert ex.admission_level_under(POLICY) is AdmissionLevel.SOURCE_VERIFIED
        assert ex.species_identity is SpeciesIdentity.VERIFIED
        assert ex.admitted_under(POLICY) is True
        assert ex.scientific_claim is False           # DEFAULT_POLICY trusts only the repo store, not this test store
        mech = ex.to_twocell(POLICY)
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

    def test_benchmark_level_requires_the_artifact_to_carry_a_validation_block(self):
        with pytest.raises(ConversionRefusal) as ei:        # a caller-built receipt "naming" a benchmark: declaration
            KineticLaw(k_f=1.0, k_r=1.0, reversible=True, admission=AdmissionLevel.BENCHMARK_VALIDATED,
                       k_f_units="s^-1", k_r_units="s^-1",
                       receipt=AdmissionReceipt(_record(), VerificationStatus.VERIFIED, benchmark="NIST run 7"))
        assert ei.value.kind is K.ADMISSION_INVALID
        with pytest.raises(ConversionRefusal) as ei2:       # a REAL inspected source, but with no validation block
            STORE.law_from_source("iso", "3rd ed", "iso", level=AdmissionLevel.BENCHMARK_VALIDATED)
        assert ei2.value.kind is K.ADMISSION_INVALID

    def test_a_source_update_moves_admission_identity_but_not_model_content(self, tmp_path):
        st = SourceStore(tmp_path)
        write_source(tmp_path, version="3rd ed")
        write_source(tmp_path, version="4th ed")                 # re-issued edition, SAME numbers (no supersedes)
        ex1 = isomerization_descriptive().to_executable([st.law_from_source("iso", "3rd ed", "iso")], omissions=OMIT)
        ex2 = isomerization_descriptive().to_executable([st.law_from_source("iso", "4th ed", "iso")], omissions=OMIT)
        assert ex1.admission_identities != ex2.admission_identities          # evidence identity moved
        assert ex1.model_identity == ex2.model_identity                      # no parameter changed -> model did not
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
        assert ex.law_levels(POLICY)[0] is AdmissionLevel.SOURCE_DECLARED  # a hand-built mechanism has no structure
        # binding: the verified law is CAPPED, not silently strengthened (Wave B2); and the species are forged anyway
        assert ex.admitted_under(POLICY) is False and ex.scientific_claim is False   # forged species -> NO claim (A3)

    def test_verified_species_via_the_adapter_do_carry_the_claim(self):
        ex = isomerization_descriptive().to_executable([verified_law()], omissions=OMIT)
        assert ex.species_identity is SpeciesIdentity.VERIFIED and ex.admitted_under(POLICY) is True

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


# ===================================================================================== Wave B (red-team #6 / #7 / #8)
class TestWaveB_FabricatedReceiptCannotMintScience:
    """#6: a receipt is a DECLARATION until a SourceStore (the verifier) issues the binding.  Pre-fix, a hand-made
    AdmissionReceipt(VERIFIED) with an invented handbook/reviewer minted scientific_claim=True."""

    def test_invented_structured_receipt_cannot_back_a_verified_law(self):
        fake = AdmissionReceipt(_record(), VerificationStatus.VERIFIED, reviewer="Dr. Totally Real, PhD")
        with pytest.raises(ConversionRefusal) as ei:
            verified_law(receipt=fake)
        assert ei.value.kind is K.ADMISSION_INVALID

    def test_invented_receipt_does_not_reach_scientific_claim_through_the_pipeline(self):
        fake = AdmissionReceipt(_record(), VerificationStatus.VERIFIED, reviewer="Dr. Totally Real, PhD")
        try:
            law = verified_law(receipt=fake)
        except ConversionRefusal:
            return                                  # refused at the law: the strong outcome
        ex = isomerization_descriptive().to_executable([law], omissions=OMIT)
        assert ex.scientific_claim is False


def _iso_ex(law):
    return isomerization_descriptive().to_executable([law], omissions=OMIT)


class TestWaveB_VerifierOwnsTheBinding:
    """#6 (continued).  The binding can be neither constructed, copied, pickled, nor loaded from a dict."""

    def test_binding_has_no_public_constructor_copy_or_pickle(self):
        b = ISO_RECEIPT.binding
        assert isinstance(b, SourceBinding)
        with pytest.raises(TypeError):
            SourceBinding(record_id="x")
        with pytest.raises(TypeError):
            dataclasses.replace(b, version="9")
        for fn in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                fn(b)

    def test_binding_is_not_a_constructor_argument_of_the_receipt(self):
        with pytest.raises(TypeError):
            AdmissionReceipt(_record(), VerificationStatus.VERIFIED, "r", "", ISO_RECEIPT.binding)

    def test_deserialised_receipt_never_carries_authority(self):
        d = ISO_RECEIPT.to_dict()
        d["binding"] = "forged"                              # a hostile dict claims whatever it likes
        d["inspected"] = True
        back = AdmissionReceipt.from_dict(d)
        assert back.binding is None and back.is_inspected is False
        with pytest.raises(ConversionRefusal) as ei:
            verified_law(receipt=back)
        assert ei.value.kind is K.ADMISSION_INVALID

    def test_no_artifact_means_no_receipt(self, tmp_path):
        with pytest.raises(ConversionRefusal) as ei:
            SourceStore(tmp_path).issue_receipt("iso", "3rd ed", "iso", **_ISO)
        assert ei.value.kind is K.PROVENANCE_MISSING

    def test_inspected_store_that_the_policy_does_not_trust_is_not_admitted(self, tmp_path):
        st = SourceStore(tmp_path)
        write_source(tmp_path)
        ex = _iso_ex(st.law_from_source("iso", "3rd ed", "iso"))
        assert ex.admitted_under(AdmissionPolicy((st,))) is True        # trusted by an explicit policy
        assert ex.admitted_under(POLICY) is False                       # a different trust root: not admitted
        assert ex.scientific_claim is False                             # the default policy trusts only DEFAULT_STORE
        assert DEFAULT_POLICY.stores[0].root.name == "verified_sources"
        assert ex.to_twocell().label == "SOURCE_DECLARED"               # label never over-claims

    def test_path_traversal_in_source_ids_is_refused(self, tmp_path):
        with pytest.raises(ConversionRefusal):
            SourceStore(tmp_path).issue_receipt("../etc", "1", "x", **_ISO)


class TestWaveB2_ParameterToSourceBinding:
    """#8 (i): a correct source for ONE rate must not certify another rate under the same citation."""

    @pytest.mark.parametrize("change", [dict(k_f=9.9e-3), dict(k_r=7.0e-3), dict(k_f_units="m^3 mol^-1 s^-1"),
                                        dict(validity_T_K=(200.0, 900.0)), dict(validity_T_K=None),
                                        dict(kinetics="empirical", forward_orders=(1.0, 0.0))])
    def test_keep_the_receipt_change_a_parameter_and_certification_is_refused(self, change):
        with pytest.raises(ConversionRefusal) as ei:
            verified_law(**change)                                       # same receipt, different numbers
        assert ei.value.kind is K.ADMISSION_INVALID

    def test_replace_on_a_certified_law_cannot_keep_the_certificate(self):
        law = verified_law()
        with pytest.raises(ConversionRefusal) as ei:
            dataclasses.replace(law, k_f=9.9e-3)
        assert ei.value.kind is K.ADMISSION_INVALID

    def test_store_will_not_issue_for_numbers_the_source_does_not_state(self):
        with pytest.raises(ConversionRefusal) as ei:
            STORE.issue_receipt("iso", "3rd ed", "iso", **dict(_ISO, k_f=5.0e-3))
        assert ei.value.kind is K.SOURCE_MISMATCH

    def test_a_source_for_a_different_reaction_cannot_certify_this_one(self):
        # the 3rd-ed 'iso' entry is CCO -> COC.  Use it on the REVERSE reaction COC -> CCO: same species, wrong sides.
        rev = DescriptiveMechanism.from_derivations([adapt_step(ExperimentStep.assembling(A, (B,), (A,)))])
        with pytest.raises(ConversionRefusal) as ei:
            rev.to_executable([verified_law()], omissions=OMIT)
        assert ei.value.kind is K.SOURCE_MISMATCH
        other = DescriptiveMechanism.from_derivations(
            [adapt_step(ExperimentStep.assembling(parse_smiles("CCOC(C)=O"),
                                                  (parse_smiles("CCO"), parse_smiles("CC(=O)O")),
                                                  (parse_smiles("CCOC(C)=O"), W)))])
        with pytest.raises(ConversionRefusal):                          # also wrong arity/units -> refused one way or another
            other.to_executable([verified_law()], omissions=OMIT)

    def test_empirical_orders_are_part_of_what_the_source_certifies(self, tmp_path):
        st = SourceStore(tmp_path)
        p = write_source(tmp_path)
        art = json.loads(p.read_text())
        art["entries"]["iso"]["kinetics"] = "empirical"
        art["entries"]["iso"]["forward_orders"] = [1.0, 0.0]
        art["entries"]["iso"]["reverse_orders"] = [0.0, 1.0]
        p.write_text(json.dumps(art))
        law = st.law_from_source("iso", "3rd ed", "iso")
        with pytest.raises(ConversionRefusal):
            dataclasses.replace(law, forward_orders=(2.0, 0.0))


class TestWaveB2_RevisionAndObsolescence:
    """#8 (ii): a revision changes the right identity and invalidates an obsolete receipt."""

    def test_superseded_source_stops_certifying_and_evidence_identity_changes(self, tmp_path):
        st = SourceStore(tmp_path)
        pol = AdmissionPolicy((st,))
        write_source(tmp_path, version="1")
        ex_old = _iso_ex(st.law_from_source("iso", "1", "iso"))
        assert ex_old.admitted_under(pol) is True
        write_source(tmp_path, version="2", supersedes="1")              # the curator publishes a superseding edition
        assert ex_old.admitted_under(pol) is False                       # the obsolete receipt no longer certifies
        assert ex_old.admission_level_under(pol) is AdmissionLevel.SOURCE_DECLARED
        ex_new = _iso_ex(st.law_from_source("iso", "2", "iso"))
        assert ex_new.admitted_under(pol) is True
        assert ex_new.admission_identities != ex_old.admission_identities        # evidence identity moved

    def test_in_place_edit_of_the_artifact_invalidates_the_issued_receipt(self, tmp_path):
        st = SourceStore(tmp_path)
        pol = AdmissionPolicy((st,))
        p = write_source(tmp_path, version="1")
        ex = _iso_ex(st.law_from_source("iso", "1", "iso"))
        art = json.loads(p.read_text())
        art["title"] = "quietly rewritten"
        p.write_text(json.dumps(art))                                    # content digest no longer the one bound
        assert ex.admitted_under(pol) is False

    def test_retracted_source_stops_certifying(self, tmp_path):
        st = SourceStore(tmp_path)
        pol = AdmissionPolicy((st,))
        p = write_source(tmp_path, version="1")
        ex = _iso_ex(st.law_from_source("iso", "1", "iso"))
        art = json.loads(p.read_text())
        art["status"] = "retracted"
        p.write_text(json.dumps(art))
        assert ex.admitted_under(pol) is False
        with pytest.raises(ConversionRefusal):
            st.law_from_source("iso", "1", "iso")                        # and a retracted source issues nothing new

    def test_an_actually_revised_parameter_moves_model_identity_too(self, tmp_path):
        st = SourceStore(tmp_path)
        write_source(tmp_path, version="1", k_f=2.0e-3)
        write_source(tmp_path, version="2", k_f=3.5e-3)                   # the revision CHANGES the rate
        a = _iso_ex(st.law_from_source("iso", "1", "iso"))
        b = _iso_ex(st.law_from_source("iso", "2", "iso"))
        assert a.model_identity != b.model_identity                       # parameter moved the model...
        assert a.admission_identities != b.admission_identities           # ...and the evidence (orthogonal, linked)
        # and the old rate cannot ride the new edition's receipt:
        with pytest.raises(ConversionRefusal):
            KineticLaw(2.0e-3, 1.0e-3, True, AdmissionLevel.SOURCE_VERIFIED, "s^-1", "s^-1",
                       receipt=st.law_from_source("iso", "2", "iso").receipt, validity_T_K=(280.0, 320.0))

    def test_benchmark_validated_comes_only_from_the_artifacts_own_validation_block(self, tmp_path):
        st = SourceStore(tmp_path)
        write_source(tmp_path, validation={"benchmark": "stopped-flow, 3 labs", "rel_uncertainty": 0.05})
        law = st.law_from_source("iso", "3rd ed", "iso", level=AdmissionLevel.BENCHMARK_VALIDATED)
        assert _iso_ex(law).admission_level_under(AdmissionPolicy((st,))) is AdmissionLevel.BENCHMARK_VALIDATED


def _run_one_step(mech, T_K, *, dt=1.0, conc=1.0):
    from experiments.sandbox_foundation.twocell import State, System, reaction_step
    S = len(mech.species)
    sysm = System(mech.species, (1.0, 1.0), (1.0, 1.0), (0.0,) * S, 1.0, 1.0, 0.0, mechanism=mech)
    n = np.zeros((2, S))
    n[:, 0] = conc
    return sysm, State.make(sysm, n, [T_K, T_K]), reaction_step


class TestWaveB3_AdmissionTravelsIntoExecution:
    """#7: the admitted domain survives the float boundary and is re-checked on EVERY reaction transition."""

    def test_the_numerical_mechanism_carries_its_applicability(self):
        mech = _iso_ex(verified_law()).to_twocell(POLICY)
        assert mech.applicability is not None
        assert mech.label == "SOURCE_VERIFIED"

    def test_inside_the_window_runs(self):
        sysm, st, step = _run_one_step(_iso_ex(verified_law()).to_twocell(POLICY), 300.0)
        st1, _ = step(sysm, st, 1.0)
        assert float(st1.n[0, 1]) > 0.0                                  # it actually reacted

    @pytest.mark.parametrize("T", [250.0, 500.0])
    def test_outside_the_sourced_window_is_refused_not_silently_run(self, T):
        sysm, st, step = _run_one_step(_iso_ex(verified_law()).to_twocell(POLICY), T)
        with pytest.raises(AdmissionDomainError):
            step(sysm, st, 1.0)

    def test_a_changing_temperature_is_rechecked_every_transition(self):
        from experiments.sandbox_foundation.twocell import run
        mech = _iso_ex(verified_law()).to_twocell(POLICY)
        sysm, st, _ = _run_one_step(mech, 300.0)
        hot = st.evolve(U=np.asarray(sysm.heat_capacity_J_per_K) * 600.0)       # the state heated up mid-campaign
        assert run(sysm, st, 1.0, 2, sequence=("reaction",)).state.n.sum() > 0   # fine at 300 K
        with pytest.raises(AdmissionDomainError):
            run(sysm, hot, 1.0, 2, sequence=("reaction",))                      # same mechanism, now outside window

    def test_a_synthetic_window_is_enforced_too(self):
        mech = _iso_ex(synthetic_law(validity_T_K=(280.0, 320.0))).to_twocell()
        sysm, st, step = _run_one_step(mech, 900.0)
        with pytest.raises(AdmissionDomainError):
            step(sysm, st, 1.0)

    def test_a_caller_that_supplies_no_temperature_cannot_run_a_windowed_law(self):
        from experiments.sandbox_foundation.twocell import SolverSettings, reaction_cell
        mech = _iso_ex(verified_law()).to_twocell(POLICY)
        with pytest.raises(AdmissionDomainError):
            reaction_cell(mech, np.array([1.0, 0.0]), 1.0, 1.0, SolverSettings())     # fail closed on T=None

    def test_concentration_cap_from_the_source_is_enforced(self, tmp_path):
        st = SourceStore(tmp_path)
        write_source(tmp_path, conc_max=10.0)
        mech = _iso_ex(st.law_from_source("iso", "3rd ed", "iso")).to_twocell(AdmissionPolicy((st,)))
        sysm, s0, step = _run_one_step(mech, 300.0, conc=5.0)
        step(sysm, s0, 1.0)                                                       # 5 mol/m^3 <= 10: fine
        sysm, s1, step = _run_one_step(mech, 300.0, conc=50.0)
        with pytest.raises(AdmissionDomainError):
            step(sysm, s1, 1.0)

    def test_source_superseded_mid_run_refuses_the_next_transition(self, tmp_path):
        st = SourceStore(tmp_path)
        pol = AdmissionPolicy((st,))
        write_source(tmp_path, version="1")
        mech = _iso_ex(st.law_from_source("iso", "1", "iso")).to_twocell(pol)
        sysm, s0, step = _run_one_step(mech, 300.0)
        step(sysm, s0, 1.0)
        write_source(tmp_path, version="2", supersedes="1")
        with pytest.raises(AdmissionDomainError):
            step(sysm, s0, 1.0)                                                   # an obsolete receipt does not certify

    def test_plain_unwindowed_synthetic_mechanism_is_unaffected(self):
        mech = _iso_ex(synthetic_law()).to_twocell()
        sysm, st, step = _run_one_step(mech, 900.0)
        st1, _ = step(sysm, st, 1.0)
        assert float(st1.n[0, 1]) > 0.0
        assert mech.label == "SYNTHETIC"                                          # not strengthened

    def test_status_is_never_strengthened_across_the_layers(self):
        d = isomerization_descriptive().to_executable([declared_law()], omissions=OMIT)
        assert d.to_twocell(POLICY).label == "SOURCE_DECLARED"
        hand = ExecutableMechanism(("ethanol", "dimethyl_ether"),
                                   ((("C", 2), ("H", 6), ("O", 1)),) * 2, (0, 0), np.array([[1], [0]]),
                                   np.array([[0], [1]]), ("R0",), (verified_law(),), OMIT)
        assert hand.to_twocell(POLICY).label == "SOURCE_DECLARED"                 # hand-built: verified law capped


class TestWaveA1_AdmittedLawHoldsAcrossTheTrajectory:
    """Wave A1: an admitted concentration cap is enforced over the WHOLE reaction trajectory, not only at n0.  A law
    admitted at a safe start cannot be integrated past its validity ceiling and handed back as a supported prediction
    -- the step fails CLOSED (red-first: before the fix, reaction_cell returned the breaching endpoint unrefused)."""

    @staticmethod
    def _capped_AB(cap, *, k_f=10.0):
        """A -> B, elementary first-order irreversible, one element X conserved (E@N=0), carrying an admitted
        concentration cap (mol/m^3) and NO temperature window -- so the only admitted condition that VARIES along the
        trajectory is the cap (isolates A1 from the up-front T-window check)."""
        from experiments.sandbox_foundation.mechanism_types import Applicability
        from experiments.sandbox_foundation.twocell import ReactionRate
        mech = Mechanism(("A", "B"), np.array([[1.0], [0.0]]), np.array([[0.0], [1.0]]), ("X",),
                         np.array([[1.0, 1.0]]), (ReactionRate(k_f=k_f, k_r=None, reversible=False),),
                         label="SYNTHETIC")
        return dataclasses.replace(mech, applicability=Applicability((("A->B", None, cap),), (None,), None))

    def test_growth_through_the_cap_mid_step_is_refused(self):
        # [A, B] = [0.6, 0.4] mol/m^3 are BOTH <= cap 0.75 at t=0 (admitted start), but B -> ~1.0 over dt = 1 s: the
        # law leaves its validity domain mid-step, so the step must fail closed instead of returning the endpoint.
        from experiments.sandbox_foundation.twocell import SolverSettings, reaction_cell
        with pytest.raises(AdmissionDomainError):
            reaction_cell(self._capped_AB(0.75), np.array([0.6, 0.4]), 1.0, 1.0, SolverSettings(), T_K=None)

    def test_an_in_domain_trajectory_still_runs(self):
        # [A, B] = [0.3, 0.1]: B climbs only to 0.4 < cap 0.75 -- no breach anywhere, so no false refusal.
        from experiments.sandbox_foundation.twocell import SolverSettings, reaction_cell
        n1, _xi, _cl, _cr = reaction_cell(self._capped_AB(0.75), np.array([0.3, 0.1]), 1.0, 1.0,
                                          SolverSettings(), T_K=None)
        assert float(n1[1]) > 0.1 and float(np.max(n1)) <= 0.75              # it reacted AND stayed under the cap

    def test_a_trajectory_that_only_approaches_the_cap_is_admitted(self):
        # total = cap = 0.75: B asymptotes to 0.75 FROM BELOW and never strictly exceeds it over finite dt (the cap
        # is inclusive -- assert_applicable uses strict >), so an approach to the boundary must NOT be refused.
        from experiments.sandbox_foundation.twocell import SolverSettings, reaction_cell
        n1, _xi, _cl, _cr = reaction_cell(self._capped_AB(0.75), np.array([0.5, 0.25]), 1.0, 1.0,
                                          SolverSettings(), T_K=None)
        assert float(np.max(n1)) <= 0.75

    def test_a_tighter_cap_just_above_the_start_still_refuses(self):
        # cap 0.61 is only just above the start max 0.6: the breach happens almost immediately, exercising the
        # terminal event rather than only the endpoint re-check.  Still fail closed.
        from experiments.sandbox_foundation.twocell import SolverSettings, reaction_cell
        with pytest.raises(AdmissionDomainError):
            reaction_cell(self._capped_AB(0.61), np.array([0.6, 0.4]), 1.0, 1.0, SolverSettings(), T_K=None)

    def test_a_plain_mechanism_without_a_cap_is_unaffected(self):
        # No applicability -> no cap, no event, no endpoint admission gate: the old path, B reaches ~1.0, unrefused.
        from experiments.sandbox_foundation.twocell import ReactionRate, SolverSettings, reaction_cell
        mech = Mechanism(("A", "B"), np.array([[1.0], [0.0]]), np.array([[0.0], [1.0]]), ("X",),
                         np.array([[1.0, 1.0]]), (ReactionRate(k_f=10.0, k_r=None, reversible=False),),
                         label="SYNTHETIC")
        n1, _xi, _cl, _cr = reaction_cell(mech, np.array([0.6, 0.4]), 1.0, 1.0, SolverSettings(), T_K=None)
        assert float(n1[1]) > 0.75                     # unrefused: a plain mechanism makes no admitted claim to hold
