"""Wave A2: Descriptive vs Executable authority.  A recognizer naming a family is not a rate law.
SYNTHETIC/experimental sandbox."""
import numpy as np
import pytest

from experiments.sandbox_foundation.mechanism_adapter import adapt_step, derive_inventory
from experiments.sandbox_foundation.mechanism_types import (
    ConversionRefusal, ConversionRefusalKind as K, DescriptiveMechanism, ExecutableMechanism, KineticLaw,
    Provenance, expected_rate_constant_units)
from experiments.sandbox_foundation.twocell import Mechanism
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

A, B, W = parse_smiles("CCO"), parse_smiles("COC"), parse_smiles("O")
OMIT = ("competing dehydration to ethene not modelled",)


def isomerization_descriptive(**kw):
    step = ExperimentStep.assembling(B, (A,), (B,))
    return DescriptiveMechanism.from_derivations([adapt_step(step)], **kw)


def sourced_law(**kw):
    base = dict(k_f=2.0e-3, k_r=1.0e-3, reversible=True, provenance=Provenance.SOURCED, k_f_units="s^-1",
                k_r_units="s^-1", source="Imaginary Handbook, tbl 4.2 (placeholder citation for a test)")
    base.update(kw)
    return KineticLaw(**base)


def synthetic_law(**kw):
    base = dict(k_f=0.5, k_r=0.1, reversible=True, provenance=Provenance.SYNTHETIC, k_f_units="s^-1",
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
        for laws in ([None], [sourced_law(k_r=None)], [sourced_law(k_f=None)], []):
            with pytest.raises(ConversionRefusal) as ei:
                d.to_executable(laws, omissions=OMIT)
            assert ei.value.kind is K.KINETICS_UNAVAILABLE

    def test_sourced_law_converts_and_is_a_scientific_claim(self):
        ex = isomerization_descriptive().to_executable([sourced_law()], omissions=OMIT)
        assert isinstance(ex, ExecutableMechanism) and ex.is_executable
        assert ex.provenance is Provenance.SOURCED and ex.scientific_claim is True
        mech = ex.to_twocell()
        assert isinstance(mech, Mechanism) and mech.label == "SOURCED"
        mech.require_complete()
        assert not np.any(mech.constitution_residual())

    def test_synthetic_law_runs_but_is_never_a_scientific_claim(self):
        ex = isomerization_descriptive().to_executable([synthetic_law()], omissions=OMIT)
        assert ex.is_executable and ex.scientific_claim is False
        assert ex.provenance is Provenance.SYNTHETIC and ex.to_twocell().label == "SYNTHETIC"

    def test_one_synthetic_law_taints_the_whole_mechanism(self):
        s1 = ExperimentStep.assembling(B, (A,), (B,))
        d = DescriptiveMechanism.from_derivations([adapt_step(s1), adapt_step(
            ExperimentStep.assembling(A, (B,), (A,)))])
        ex = d.to_executable([sourced_law(), synthetic_law()], omissions=OMIT)
        assert ex.scientific_claim is False

    def test_provenance_statements_are_mandatory(self):
        with pytest.raises(ConversionRefusal) as ei:
            sourced_law(source="  ")
        assert ei.value.kind is K.PROVENANCE_MISSING
        with pytest.raises(ConversionRefusal) as ei:
            synthetic_law(assumption="")
        assert ei.value.kind is K.PROVENANCE_MISSING

    def test_omissions_must_be_declared(self):
        for om in ((), ("  ",)):
            with pytest.raises(ConversionRefusal) as ei:
                isomerization_descriptive().to_executable([sourced_law()], omissions=om)
            assert ei.value.kind is K.OMISSIONS_UNDECLARED

    def test_bad_rate_values_are_refused(self):
        d = isomerization_descriptive()
        for bad in (-1.0, float("nan"), float("inf"), True):
            with pytest.raises(ConversionRefusal) as ei:
                d.to_executable([sourced_law(k_f=bad)], omissions=OMIT)
            assert ei.value.kind is K.INVALID_KINETIC_LAW

    def test_units_are_dimension_checked(self):
        with pytest.raises(ConversionRefusal) as ei:
            isomerization_descriptive().to_executable([sourced_law(k_f_units="m^3 mol^-1 s^-1")], omissions=OMIT)
        assert ei.value.kind is K.DIMENSION_MISMATCH
        assert expected_rate_constant_units(1) == "s^-1"
        assert expected_rate_constant_units(2) == "m^3 mol^-1 s^-1"
        assert expected_rate_constant_units(0) == "m^-3 mol s^-1"

    def test_bimolecular_elementary_needs_second_order_units(self):
        step = ExperimentStep.assembling(parse_smiles("CCOC(C)=O"), (parse_smiles("CCO"), parse_smiles("CC(=O)O")),
                                         (parse_smiles("CCOC(C)=O"), W))
        d = DescriptiveMechanism.from_derivations([adapt_step(step)])
        good = sourced_law(k_f_units="m^3 mol^-1 s^-1", k_r_units="m^3 mol^-1 s^-1")
        assert d.to_executable([good], omissions=OMIT).is_executable
        with pytest.raises(ConversionRefusal) as ei:
            d.to_executable([sourced_law()], omissions=OMIT)       # first-order units on a bimolecular law
        assert ei.value.kind is K.DIMENSION_MISMATCH

    def test_selection_of_a_subset_of_reactions(self):
        d = DescriptiveMechanism.from_derivations([
            adapt_step(ExperimentStep.assembling(B, (A,), (B,))),
            adapt_step(ExperimentStep.assembling(A, (B,), (A,)))])
        ex = d.to_executable([sourced_law()], omissions=OMIT, selected=[1])
        assert ex.reaction_labels == ("R1",) and ex.N.shape[1] == 1
        for bad in ([], [5], [0, 0], [True]):
            with pytest.raises(ConversionRefusal) as ei:
                d.to_executable([sourced_law()], omissions=OMIT, selected=bad)
            assert ei.value.kind is K.SELECTION_INVALID

    def test_empirical_law_needs_explicit_orders(self):
        d = isomerization_descriptive()
        with pytest.raises(ConversionRefusal) as ei:
            d.to_executable([sourced_law(kinetics="empirical")], omissions=OMIT)
        assert ei.value.kind is K.INVALID_KINETIC_LAW
        law = sourced_law(kinetics="empirical", forward_orders=(1.5, 0.0), reverse_orders=(0.0, 1.0),
                          k_f_units=expected_rate_constant_units(1.5), k_r_units="s^-1")
        mech = d.to_executable([law], omissions=OMIT).to_twocell()
        assert mech.kinetics == "empirical" and mech.order_f[:, 0].tolist() == [1.5, 0.0]

    def test_executable_cannot_be_forged_by_hand_either(self):
        d = isomerization_descriptive()
        comps = ((("C", 1), ("H", 4)), (("C", 1), ("O", 2)))
        with pytest.raises(ConversionRefusal) as ei:
            ExecutableMechanism(("CH4", "CO2"), comps, (0, 0), np.array([[1], [0]]), np.array([[0], [1]]),
                                ("R0",), (sourced_law(),), OMIT)
        assert ei.value.kind is K.INVENTORY_REFUSED
        with pytest.raises(TypeError):
            ExecutableMechanism(d.species, d.compositions, d.charges, d.reactant, d.product, ("R0",),
                                (sourced_law(),), OMIT, E=d.E)

    def test_exact_integers_survive_to_the_float_boundary_unchanged(self):
        ex = isomerization_descriptive().to_executable([sourced_law()], omissions=OMIT)
        assert ex.E.dtype == ex.reactant.dtype == ex.product.dtype == np.int64
        mech = ex.to_twocell()
        assert np.array_equal(mech.E, ex.E) and np.array_equal(mech.N, ex.N)


class TestAdapterIntegration:
    def test_forged_E_never_reaches_the_type_layer(self):
        # the adapter refuses before a DescriptiveMechanism can exist
        from experiments.sandbox_foundation.mechanism_adapter import AdapterRefusal
        with pytest.raises(AdapterRefusal):
            derive_inventory((parse_smiles("C"), parse_smiles("O=O")), (parse_smiles("O=C=O"),),
                             supplied_E=[[1, 0, 1], [0, 0, 0], [0, 2, 2], [0, 0, 0]],
                             supplied_labels=("C", "H", "O", "charge"))
