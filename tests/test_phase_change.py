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


class TestPhaseChangeSigma:
    """PHASE-CHANGE-SIGMA: a phase-change record carries its SOURCED ΔH/ΔS ± (compare=False metadata), guarded
    non-vacuously.  Free sources reliably state ΔH ± but rarely ΔS ±, so ΔS ± is usually an honest None today."""

    def test_ethanol_vaporization_carries_its_sourced_enthalpy_pm(self):
        # ethanol is the ONE live-propagating case (group-derived gas + a vaporization ref).  Its ±0.4 is the NIST
        # WebBook Δvap H° inter-study band (average of 12/13 studies, centered on 42.3), NOT a single study's 1σ and
        # NOT Majer & Svoboda's 38.56@351.5 K datum (the red-team's D1 fold: the citation named the wrong source).
        ref = DEFAULT_PHASE_CHANGE.for_named("C2H6O", "ethanol")
        assert ref is not None and ref.uncertainty_dh_kj_per_mol == 0.4
        assert ref.uncertainty_ds_j_per_mol_k is None  # ΔvapS ± not cleanly reported -> honest None

    def test_naphthalene_carries_no_pm_it_would_be_mislabeled_and_dead(self):
        # red-team fold (D2/D3): NIST's ±5 is centered on its AVG value 71, not the stored 72.6 (Kruif 1980) --
        # attaching it splices a band onto a value it is not centered on; and resolve_thermo has no group estimate for
        # the fused aromatic, so it would never propagate.  Honest None over a mislabeled, dead ±.
        ref = DEFAULT_PHASE_CHANGE.for_named("C10H8", "naphthalene")
        assert ref is not None and ref.uncertainty_dh_kj_per_mol is None

    def test_paracetamol_enthalpy_pm_is_an_honest_none(self):
        # paracetamol ΔsubH is CONTENTIOUS (117.9 Picciochi calorimetry vs 138±3 Vecchio Fus+Vap -- a ~20 kJ/mol
        # method spread), so no tight ± can honestly sit on the chosen value; None, never a borrowed/fabricated ±.
        ref = DEFAULT_PHASE_CHANGE.for_named("C8H9NO2", "paracetamol")
        assert ref is not None and ref.uncertainty_dh_kj_per_mol is None

    def test_a_hollow_or_negative_phase_change_pm_is_refused(self):
        for bad in (0.0, -1.0):
            with pytest.raises(ValueError, match="sourced ±|> 0|refused"):
                PhaseChangeRef("X", "x", PhaseTransition.SUBLIMATION, 100.0, 200.0, "s", uncertainty_dh_kj_per_mol=bad)
            with pytest.raises(ValueError, match="sourced ±|> 0|refused"):
                PhaseChangeRef("X", "x", PhaseTransition.SUBLIMATION, 100.0, 200.0, "s", uncertainty_ds_j_per_mol_k=bad)

    def test_the_pm_is_compare_false_metadata_no_digest_moves(self):
        # a ± is provenance, not identity: two refs identical but for their ± share a digest (so adding one to the
        # seed moves no golden), mirroring ThermoRef.
        bare = PhaseChangeRef("X", "x", PhaseTransition.SUBLIMATION, 100.0, 200.0, "s")
        with_pm = PhaseChangeRef("X", "x", PhaseTransition.SUBLIMATION, 100.0, 200.0, "s",
                                 uncertainty_dh_kj_per_mol=2.0, uncertainty_ds_j_per_mol_k=3.0)
        assert bare == with_pm and bare.digest == with_pm.digest


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
