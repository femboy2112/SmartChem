"""Wave A1: the mechanism adapter derives its inventory from REAL SmartChem objects, and never trusts a caller's E.

Red-team battery item #1 lives in TestForgedE.  Everything is exact-integer; SYNTHETIC/experimental sandbox."""
import numpy as np
import pytest

from experiments.sandbox_foundation.mechanism_adapter import (
    AdapterRefusal, Claim, RefusalKind, UnsupportedClaim, adapt_step, derive_inventory)
from smartchem.category import Molecule
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

CH4, O2, CO2, H2O = (parse_smiles(s) for s in ("C", "O=O", "O=C=O", "O"))


def combustion_step():
    return ExperimentStep.assembling(CO2, (CH4, O2, O2), (CO2, H2O, H2O))


# ------------------------------------------------------------------ real conserving step -> exact inventory
class TestRealStepInventory:
    def test_species_complexes_N_and_E_are_exact_integers(self):
        d = adapt_step(combustion_step())
        assert d.species == ("CH4", "O2", "CO2", "H2O")
        assert d.element_labels == ("C", "H", "O", "charge")
        assert d.reactant.dtype == d.product.dtype == d.N.dtype == d.E.dtype == np.int64
        assert d.reactant[:, 0].tolist() == [1, 2, 0, 0]       # complexes keep per-side multiplicity
        assert d.product[:, 0].tolist() == [0, 0, 1, 2]
        assert d.N[:, 0].tolist() == [-1, -2, 1, 2]            # N = product - reactant
        assert d.E.tolist() == [[1, 0, 1, 0], [4, 0, 0, 2], [0, 2, 2, 1], [0, 0, 0, 0]]
        assert d.compositions[0] == (("C", 1), ("H", 4))
        assert not np.any(d.E @ d.N)                           # exact zero, no tolerance

    def test_inventory_round_trips_from_formulae(self):
        d = adapt_step(combustion_step())
        # rebuild per-species formulae FROM E and compare with the molecules' own formula dicts
        mols = {"CH4": CH4, "O2": O2, "CO2": CO2, "H2O": H2O}
        for j, name in enumerate(d.species):
            rebuilt = {d.element_labels[i]: int(d.E[i, j]) for i in range(len(d.element_labels) - 1) if d.E[i, j]}
            assert rebuilt == mols[name].formula
            assert int(d.E[-1, j]) == mols[name].charge

    def test_charge_row_uses_molecule_charge(self):
        # NH4+ + OH- -> NH3 + H2O  (ions carry only a net global charge)
        nh4, oh, nh3 = parse_smiles("[NH4+]"), parse_smiles("[OH-]"), parse_smiles("N")
        d = derive_inventory((nh4, oh), (nh3, H2O))
        assert d.E[-1].tolist() == [1, -1, 0, 0]
        assert not np.any(d.E @ d.N)

    def test_catalyst_survives_in_complexes_but_vanishes_from_N(self):
        # A + C -> B + C: C has net 0 but must stay in the complexes
        d = derive_inventory((CH4, H2O), (CH4, H2O))
        assert d.N[:, 0].tolist() == [0, 0]
        assert d.reactant[:, 0].tolist() == [1, 1] and d.product[:, 0].tolist() == [1, 1]

    def test_isomers_get_distinct_species(self):
        ethanol, dme = parse_smiles("CCO"), parse_smiles("COC")
        d = derive_inventory((ethanol,), (dme,))
        assert len(set(d.species)) == 2 and not np.any(d.E @ d.N)

    def test_arrays_are_read_only(self):
        d = adapt_step(combustion_step())
        with pytest.raises(ValueError):
            d.E[0, 0] = 5


# ------------------------------------------------------------------ THE CENTRAL ACCEPTANCE LAW
class TestForgedE:
    """CH4 + O2 -> CO2 is genuinely NOT balanced (the 4 H and 2 O never appear on the right).  ExperimentStep would
    refuse to even construct it, so we present the raw multisets.  Species order: CH4, O2, CO2; N = [-1,-1,+1].

    The forged E zeroes the H row.  It is crafted so the naive check E_forged @ N == 0 PASSES."""
    REACT, PROD = (CH4, O2), (CO2,)
    LABELS = ("C", "H", "O", "charge")
    FORGED = [[1, 0, 1],      # C  (true)
              [0, 0, 0],      # H  FORGED: the true row is [4, 0, 0]
              [0, 2, 2],      # O  (true)
              [0, 0, 0]]      # charge (true)
    N = np.array([[-1], [-1], [1]])

    def test_the_forged_E_really_fools_the_naive_check(self):
        assert not np.any(np.array(self.FORGED) @ self.N)      # the forgery "certifies" E@N=0 ...
        true_E = np.array([[1, 0, 1], [4, 0, 0], [0, 2, 2], [0, 0, 0]])
        assert np.any(true_E @ self.N)                          # ... but the truth does not

    def test_step_constructor_independently_refuses_it_too(self):
        # corroboration only: the 1.x certificate agrees this is not a mechanism
        from smartchem.experiment.step import StepError
        with pytest.raises(StepError):
            ExperimentStep.assembling(CO2, self.REACT, self.PROD)

    def test_forged_E_cannot_certify_a_nonconserving_transformation(self):
        with pytest.raises(AdapterRefusal) as ei:
            derive_inventory(self.REACT, self.PROD, supplied_E=self.FORGED, supplied_labels=self.LABELS)
        assert ei.value.kind is RefusalKind.FORGED_INVENTORY
        assert "'H'" in ei.value.detail                         # names the row that lies

    def test_without_any_supplied_E_the_derived_inventory_catches_the_imbalance(self):
        with pytest.raises(AdapterRefusal) as ei:
            derive_inventory(self.REACT, self.PROD)
        assert ei.value.kind is RefusalKind.NON_CONSERVING
        assert "'H': -4" in ei.value.detail or "H" in ei.value.detail

    def test_honest_E_on_a_nonconserving_transformation_is_refused_by_the_derived_check(self):
        honest = [[1, 0, 1], [4, 0, 0], [0, 2, 2], [0, 0, 0]]
        with pytest.raises(AdapterRefusal) as ei:
            derive_inventory(self.REACT, self.PROD, supplied_E=honest, supplied_labels=self.LABELS)
        assert ei.value.kind is RefusalKind.NON_CONSERVING

    def test_forgery_with_dropped_or_invented_rows_is_refused(self):
        only_c = [[1, 0, 1]]                                    # E@N = 0, vacuously "conserved": H and O omitted
        for labels, E in ((("C",), only_c), (("X", "charge"), [[1, 1, 0], [0, 0, 0]])):
            with pytest.raises(AdapterRefusal) as ei:
                derive_inventory(self.REACT, self.PROD, supplied_E=E, supplied_labels=labels)
            assert ei.value.kind is RefusalKind.FORGED_INVENTORY

    def test_supplied_E_without_labels_is_refused(self):
        with pytest.raises(AdapterRefusal) as ei:
            derive_inventory(self.REACT, self.PROD, supplied_E=self.FORGED)
        assert ei.value.kind is RefusalKind.FORGED_INVENTORY

    def test_a_forged_E_cannot_even_fake_a_conserving_transformation_into_a_different_inventory(self):
        bad = [[1, 1, 0, 0], [4, 0, 0, 2], [0, 2, 2, 1], [0, 0, 0, 0]]   # a wrong C row on a good step
        with pytest.raises(AdapterRefusal) as ei:
            adapt_step(combustion_step(), supplied_E=bad, supplied_labels=self.LABELS)
        assert ei.value.kind is RefusalKind.FORGED_INVENTORY

    def test_a_correct_supplied_E_is_accepted_but_changes_nothing_and_row_order_is_free(self):
        d0 = adapt_step(combustion_step())
        perm = (2, 0, 3, 1)
        labels = tuple(d0.element_labels[i] for i in perm)
        d1 = adapt_step(combustion_step(), supplied_E=d0.E[list(perm)], supplied_labels=labels)
        assert np.array_equal(d0.E, d1.E)


# ------------------------------------------------------------------ representation walls
class TestRefusedClaims:
    @pytest.mark.parametrize("kind", list(UnsupportedClaim))
    def test_every_unsupported_claim_kind_is_a_typed_refusal(self, kind):
        with pytest.raises(AdapterRefusal) as ei:
            adapt_step(combustion_step(), claims=[Claim(kind, "CH4", "caller says so")])
        assert ei.value.kind is RefusalKind.UNSUPPORTED_CLAIM and ei.value.claim is kind

    def test_isotope_smiles_is_not_silently_flattened(self):
        with pytest.raises(AdapterRefusal) as ei:
            adapt_step(combustion_step(), source_smiles=["[13CH4]"])
        assert ei.value.claim is UnsupportedClaim.ISOTOPE

    def test_stereo_smiles_is_refused(self):
        with pytest.raises(AdapterRefusal) as ei:
            adapt_step(combustion_step(), source_smiles=["C[C@H](N)O"])
        assert ei.value.claim is UnsupportedClaim.STEREO

    def test_local_charge_placement_is_refused_but_a_plain_ion_is_fine(self):
        with pytest.raises(AdapterRefusal) as ei:
            adapt_step(combustion_step(), source_smiles=["C[N+](C)(C)[O-]"])    # N-oxide: +1 and -1 on atoms, net 0
        assert ei.value.claim is UnsupportedClaim.LOCAL_CHARGE
        adapt_step(combustion_step(), source_smiles=["[NH4+]", "[OH-]", "[Mg+2]"])   # global-charge ions pass

    def test_smuggled_atom_labels_are_refused(self):
        iso = Molecule(("13C",), frozenset(), 0)
        with pytest.raises(AdapterRefusal) as ei:
            derive_inventory((iso,), (iso,))
        assert ei.value.claim is UnsupportedClaim.ISOTOPE


# ------------------------------------------------------------------ input hygiene
class TestInputHygiene:
    def test_non_molecule_and_empty_sides_are_malformed(self):
        for r, p in (((), (CO2,)), ((CH4,), ()), (("CH4",), (CH4,))):
            with pytest.raises(AdapterRefusal) as ei:
                derive_inventory(r, p)
            assert ei.value.kind is RefusalKind.MALFORMED_INPUT

    def test_non_step_is_malformed(self):
        with pytest.raises(AdapterRefusal):
            adapt_step("CH4 + O2 -> CO2")

    def test_all_zero_inventory_is_vacuous(self):
        q = Molecule.quantum("photon")
        with pytest.raises(AdapterRefusal) as ei:
            derive_inventory((q,), (Molecule.quantum("phonon"),))
        assert ei.value.kind is RefusalKind.VACUOUS_INVENTORY


def test_same_sign_multisite_charge_is_refused_as_local_charge():
    # evil-morty KILL 2: the weaker heuristic `charged_atoms > |net|` MISSED a di-cation (two +1 sites, net +2);
    # the adapter now uses the codebase's own has_local_charge_structure, so it is refused on source_smiles.
    dication = parse_smiles("[NH3+]CC[NH3+]")          # ethylenediammonium: two +1 centres, net +2
    with pytest.raises(AdapterRefusal) as ei:
        derive_inventory((dication,), (dication,), source_smiles=["[NH3+]CC[NH3+]"])
    assert ei.value.kind is RefusalKind.UNSUPPORTED_CLAIM and ei.value.claim is UnsupportedClaim.LOCAL_CHARGE


def test_plain_monovalent_and_single_site_ions_still_pass():
    # the fix must NOT over-refuse: a single charged atom (representable by the one global charge) is fine.
    from experiments.sandbox_foundation.mechanism_adapter import smiles_claims
    for smi in ("[NH4+]", "[OH-]", "[Mg+2]"):
        assert smiles_claims(smi) == []
