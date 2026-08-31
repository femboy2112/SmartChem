"""Rung C -- gas->condensed: the phase-change module and the paracetamol litmus closure.

The documented paracetamol wall was its missing standard molar entropy S°(cr): only an entropy of fusion was
ever measured, so the acetylation ΔG stayed UNKNOWN.  Here S°(cr) = S°(gas, Benson) − ΔsubS is DERIVED, and
the enthalpy leg is a THREE-way cross-validation -- the Benson gas ΔfH° minus the sourced ΔsubH reconstructs
paracetamol's independently-sourced crystal ΔfH° (Picciochi 2010) to within the combined band.
"""
from __future__ import annotations

import pytest

from smartchem.data.phase_change import (
    DEFAULT_PHASE_CHANGE,
    PhaseChangeRef,
    PhaseTransition,
    to_condensed,
)
from smartchem.data.thermo import DEFAULT_THERMO
from smartchem.experiment.feasibility import resolve_thermo
from smartchem.smiles import parse_smiles


class TestPhaseChangeModel:
    def test_to_condensed_subtracts_the_difference(self):
        ref = PhaseChangeRef("X", "x", PhaseTransition.SUBLIMATION, 100.0, 200.0, "test")
        dhf, s, phase = to_condensed(-300.0, 400.0, ref)
        assert dhf == -400.0 and s == 200.0 and phase == "solid"

    def test_vaporization_targets_liquid(self):
        assert PhaseTransition.VAPORIZATION.condensed_phase == "liquid"
        assert PhaseTransition.SUBLIMATION.condensed_phase == "solid"

    def test_a_negative_phase_change_is_refused(self):
        # ΔH/ΔS gas−condensed are >= 0 by definition; a negative one is a data/sign error, refused loudly
        with pytest.raises(ValueError):
            PhaseChangeRef("X", "x", PhaseTransition.SUBLIMATION, -10.0, 5.0, "bad")

    def test_paracetamol_sublimation_is_sourced(self):
        ref = DEFAULT_PHASE_CHANGE.for_named("C8H9NO2", "paracetamol")
        assert ref is not None and ref.transition is PhaseTransition.SUBLIMATION
        assert 110.0 < ref.dh_kj_per_mol < 135.0  # ΔsubH ~118 kJ/mol


class TestParacetamolLitmusClosure:
    """The last mile: paracetamol gets a CONDENSED-phase record, its crystal entropy derived, and its
    crystal enthalpy reconstructed in agreement with an independent calorimetric source."""

    def test_paracetamol_resolves_to_a_condensed_record(self):
        apap = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        r = resolve_thermo(apap, DEFAULT_THERMO, derive=True, condensed=True)
        assert r is not None
        assert r.phase == "solid"        # corrected from the gas estimate to the crystalline standard state
        assert r.grade == "PREDICTED"    # a gas estimate + a sourced Δsub is a two-step estimate

    def test_three_way_enthalpy_cross_validation(self):
        # Benson gas ΔfH° (−311) − sourced ΔsubH (117.9) must reconstruct Picciochi's crystal ΔfH° (−410.4)
        # to within the combined band: three unrelated sources agreeing on one number.
        apap = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        r = resolve_thermo(apap, DEFAULT_THERMO, derive=True, condensed=True)
        picciochi_cr = -410.4
        assert abs(r.dhf_kj_per_mol - picciochi_cr) <= 25.0  # within the stacked (gas ±21 + Δsub) band

    def test_crystal_entropy_is_now_supplied(self):
        # the wall was a missing S°(cr); it is now S°(gas) − ΔsubS, a real positive number (not UNKNOWN)
        apap = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        gas = resolve_thermo(apap, DEFAULT_THERMO, derive=True, condensed=False)
        solid = resolve_thermo(apap, DEFAULT_THERMO, derive=True, condensed=True)
        assert solid.s_j_per_mol_k > 0.0
        assert solid.s_j_per_mol_k < gas.s_j_per_mol_k  # crystal entropy is lower than gas

    def test_condensed_off_by_default_keeps_gas(self):
        apap = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        gas = resolve_thermo(apap, DEFAULT_THERMO, derive=True, condensed=False)
        assert gas is not None and gas.phase == "gas"


class TestFormulaCollisionGuard:
    """Red-team: PhaseChangeTable must be keyed on structural identity, never bare formula -- else an isomer
    steals another compound's Δsub/Δvap (dimethyl ether, C2H6O, borrowing ethanol's ΔvapH)."""

    def test_dimethyl_ether_does_not_borrow_ethanol_vaporization(self):
        # dimethyl ether (a GAS, bp -24 C) shares formula C2H6O with ethanol (a liquid). It must resolve to a
        # GAS record, NOT be "corrected" to a liquid via ethanol's ΔvapH.
        dme = parse_smiles("COC")
        r = resolve_thermo(dme, DEFAULT_THERMO, derive=True, condensed=True)
        assert r is not None and r.phase == "gas"

    def test_paracetamol_still_gets_its_own_correction(self):
        # the fix (name-match only) must not break the litmus target's real correction
        apap = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        r = resolve_thermo(apap, DEFAULT_THERMO, derive=True, condensed=True)
        assert r is not None and r.phase == "solid"
