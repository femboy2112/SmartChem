"""The derivation layer, rung 1: a SOURCED periodic table + a calibrated ideal-gas RRHO entropy.

The load-bearing test is ``TestDiatomicCalibration``: the RRHO derivation must reproduce measured
standard molar entropies (sourced, with provenance) from independently-sourced structural inputs.
That is the instrument rule -- a computation that measures physics earns trust only by recovering
known answers first.  It reproduces CODATA/JANAF standard entropies to <= 0.2 J/mol/K.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from smartchem.data import periodic_table as pt
from smartchem.data.reference import GEOMETRY
from smartchem.thermo_entropy import (
    STANDARD_PRESSURE_PA,
    diatomic_entropy,
    ideal_gas_entropy,
    principal_moments_of_inertia,
)

# ---------------------------------------------------------------------------------------------------
# SOURCED experimental standard molar entropies S deg(gas, 298.15 K, 1 bar), the calibration targets.
# Fetched from the NIST Chemistry WebBook with provenance -- NOT recalled (the repo's anti-poisoning
# discipline).  Each: (value J/mol/K, source).
# ---------------------------------------------------------------------------------------------------
_EXPERIMENTAL_S298 = {
    # CODATA Key Values for Thermodynamics: Cox, J.D.; Wagman, D.D.; Medvedev, V.A. (1984), via NIST WebBook.
    "N2": (191.609, "CODATA (Cox, Wagman & Medvedev 1984); NIST WebBook"),
    "CO": (197.660, "CODATA (Cox, Wagman & Medvedev 1984); NIST WebBook"),
    # NIST-JANAF Thermochemical Tables, 4th ed.: Chase, M.W. (1998), J. Phys. Chem. Ref. Data Monograph 9.
    "HCl": (186.90, "NIST-JANAF (Chase 1998); NIST WebBook"),
}

# Structural inputs (symmetry number, ground-state electronic degeneracy) for each calibration species.
# sigma: 2 for a homonuclear diatomic (A2), 1 for a heteronuclear one (AB) -- a point-group fact.
# g0: 2S+1 for the spin-only ground term (all singlets here).  Geometry/frequency come from the sourced
# GEOMETRY table (NIST Diatomic Spectral DB; Huber & Herzberg 1979).
_STRUCTURE = {
    "N2": ("N", "N", 2, 1),
    "CO": ("C", "O", 1, 1),
    "HCl": ("H", "Cl", 1, 1),
}

_CALIBRATION_TOL = 0.5   # J/mol/K -- generous vs the <=0.2 actually demonstrated below.


class TestPeriodicTable:
    def test_all_118_elements_present_and_contiguous(self):
        assert len(pt.STANDARD_ATOMIC_WEIGHT) == 118
        assert sorted(pt.ATOMIC_NUMBER.values()) == list(range(1, 119))

    def test_carbon_finally_has_a_mass(self):
        # The whole reason this module exists: before it, Atom('C').mass_amu was 0.0.
        assert pt.standard_atomic_weight("C") == pytest.approx(12.011)

    def test_cross_checked_stable_values(self):
        # Spot values that BOTH sources (CIAAW abridged + Wikipedia/IUPAC) agreed on exactly.
        assert pt.standard_atomic_weight("H") == pytest.approx(1.0080)
        assert pt.standard_atomic_weight("N") == pytest.approx(14.007)
        assert pt.standard_atomic_weight("O") == pytest.approx(15.999)
        assert pt.standard_atomic_weight("Cl") == pytest.approx(35.45)

    def test_zirconium_uses_the_2024_ciaaw_revision(self):
        # The one cross-check discrepancy: CIAAW 2024 revised Zr to 91.222 (Wikipedia still showed
        # the older 91.224).  The newer sourced value wins.
        assert pt.standard_atomic_weight("Zr") == pytest.approx(91.222)

    def test_radioactive_elements_are_flagged_as_mass_numbers(self):
        # Tc/Pm/... and the synthetics carry a most-stable-isotope MASS NUMBER, not a standard weight.
        assert pt.has_standard_atomic_weight("C") is True
        assert pt.has_standard_atomic_weight("Tc") is False
        assert pt.has_standard_atomic_weight("Og") is False
        assert pt.standard_atomic_weight("Tc") == pytest.approx(97.0)

    def test_unknown_symbol_is_loud_not_silent_zero(self):
        with pytest.raises(KeyError):
            pt.standard_atomic_weight("Xx")

    def test_mass_of_one_molecule_uses_codata_constant(self):
        # one N2 molecule = 2 * 14.007 u * m_u
        expected = 2 * 14.007 * pt.ATOMIC_MASS_CONSTANT_KG
        assert pt.mass_kg_per_molecule(2 * 14.007) == pytest.approx(expected)


class TestDiatomicCalibration:
    """THE instrument gate: derived S deg(gas) reproduces measured standard entropies within tolerance."""

    @pytest.mark.parametrize("formula", sorted(_EXPERIMENTAL_S298))
    def test_reproduces_sourced_experimental_entropy(self, formula):
        exp_value, _source = _EXPERIMENTAL_S298[formula]
        a, b, sigma, g0 = _STRUCTURE[formula]
        r_e, omega_e, _spin = GEOMETRY[formula]
        s = diatomic_entropy(a, b, bond_length_angstrom=r_e, frequency_cm=omega_e,
                             symmetry_number=sigma, electronic_degeneracy=g0)
        assert s.grade == "DERIVED"
        assert abs(s.value_j_per_mol_k - exp_value) < _CALIBRATION_TOL
        # the demonstrated accuracy is far tighter than the reported band
        assert s.value_j_per_mol_k == pytest.approx(exp_value, abs=0.2)

    def test_o2_triplet_electronic_term_is_load_bearing(self):
        # O2's ground state is a triplet: g0 = 3.  The electronic term R*ln3 ~ 9.13 J/mol/K is the
        # difference between a right answer (~205) and a wrong one (~196).
        r_e, omega_e, _ = GEOMETRY["O2"]
        with_triplet = diatomic_entropy("O", "O", bond_length_angstrom=r_e, frequency_cm=omega_e,
                                        symmetry_number=2, electronic_degeneracy=3)
        without = diatomic_entropy("O", "O", bond_length_angstrom=r_e, frequency_cm=omega_e,
                                   symmetry_number=2, electronic_degeneracy=1)
        assert with_triplet.electronic == pytest.approx(8.314462618 * math.log(3), abs=1e-6)
        assert (with_triplet.value_j_per_mol_k - without.value_j_per_mol_k) == pytest.approx(
            with_triplet.electronic, abs=1e-9
        )
        # sourced O2 standard entropy is ~205.15 J/mol/K; only the triplet reaches it
        assert abs(with_triplet.value_j_per_mol_k - 205.15) < 1.0


class TestComponents:
    def test_sackur_tetrode_grows_with_mass_and_temperature(self):
        light = diatomic_entropy("H", "H", bond_length_angstrom=0.741, frequency_cm=4401.0,
                                 symmetry_number=2, electronic_degeneracy=1)
        heavy = diatomic_entropy("Cl", "Cl", bond_length_angstrom=1.988, frequency_cm=559.7,
                                 symmetry_number=2, electronic_degeneracy=1)
        assert heavy.translational > light.translational
        hot = diatomic_entropy("N", "N", bond_length_angstrom=1.098, frequency_cm=2358.6,
                               symmetry_number=2, electronic_degeneracy=1, temperature_k=500.0)
        cool = diatomic_entropy("N", "N", bond_length_angstrom=1.098, frequency_cm=2358.6,
                                symmetry_number=2, electronic_degeneracy=1, temperature_k=200.0)
        assert hot.translational > cool.translational

    def test_symmetry_number_lowers_rotational_entropy_by_r_ln2(self):
        # Same molecule, sigma 1 vs 2: the homonuclear penalty is exactly R*ln2.
        hetero = diatomic_entropy("C", "O", bond_length_angstrom=1.128, frequency_cm=2170.0,
                                  symmetry_number=1, electronic_degeneracy=1)
        homo = diatomic_entropy("C", "O", bond_length_angstrom=1.128, frequency_cm=2170.0,
                                symmetry_number=2, electronic_degeneracy=1)
        assert (hetero.rotational - homo.rotational) == pytest.approx(8.314462618 * math.log(2), abs=1e-9)

    def test_vibration_negligible_when_stiff_grows_when_soft(self):
        stiff = diatomic_entropy("H", "F", bond_length_angstrom=0.917, frequency_cm=4138.0,
                                 symmetry_number=1, electronic_degeneracy=1)
        soft = diatomic_entropy("I", "I", bond_length_angstrom=2.666, frequency_cm=214.5,
                                symmetry_number=2, electronic_degeneracy=1)
        assert stiff.vibrational < 0.05
        assert soft.vibrational > 5.0


class TestGradeAndBand:
    def test_predicted_when_extrapolated_outside_regime(self):
        hot = diatomic_entropy("N", "N", bond_length_angstrom=1.098, frequency_cm=2358.6,
                               symmetry_number=2, electronic_degeneracy=1, temperature_k=3000.0)
        assert hot.grade == "PREDICTED"
        assert any("PREDICTED" in n for n in hot.notes)

    def test_computed_frequency_bias_widens_the_band(self):
        # An experimental-frequency derivation carries only the model floor; a +9.1%-biased computed
        # frequency source propagates extra uncertainty into S_vib.
        exp = diatomic_entropy("I", "I", bond_length_angstrom=2.666, frequency_cm=214.5,
                               symmetry_number=2, electronic_degeneracy=1)
        computed = diatomic_entropy("I", "I", bond_length_angstrom=2.666, frequency_cm=214.5,
                                    symmetry_number=2, electronic_degeneracy=1,
                                    frequency_bias_fraction=0.091)
        assert computed.uncertainty_j_per_mol_k > exp.uncertainty_j_per_mol_k
        assert any("bias" in n for n in computed.notes)

    def test_standard_pressure_is_one_bar(self):
        assert STANDARD_PRESSURE_PA == 100000.0
        one_bar = diatomic_entropy("N", "N", bond_length_angstrom=1.098, frequency_cm=2358.6,
                                   symmetry_number=2, electronic_degeneracy=1)
        one_atm = diatomic_entropy("N", "N", bond_length_angstrom=1.098, frequency_cm=2358.6,
                                   symmetry_number=2, electronic_degeneracy=1, pressure_pa=101325.0)
        # higher pressure -> lower translational entropy, by R*ln(101325/100000)
        assert (one_bar.value_j_per_mol_k - one_atm.value_j_per_mol_k) == pytest.approx(
            8.314462618 * math.log(101325.0 / 100000.0), abs=1e-6
        )


class TestGeometryMoments:
    def test_collinear_atoms_are_detected_linear(self):
        # three atoms on the z-axis -> linear; one principal moment ~ 0
        masses = [12.011, 15.999, 15.999]                       # CO2-like masses, arbitrary spacing
        coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.16], [0.0, 0.0, -1.16]])
        moments, linear = principal_moments_of_inertia(masses, coords)
        assert linear is True
        assert moments[0] < 1e-6 * moments[-1]

    def test_bent_molecule_is_nonlinear_with_three_moments(self):
        masses = [15.999, 1.008, 1.008]                         # water-like, bent
        coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.757, 0.587], [0.0, -0.757, 0.587]])
        moments, linear = principal_moments_of_inertia(masses, coords)
        assert linear is False
        assert all(m > 0 for m in moments)

    def test_diatomic_moment_matches_reduced_mass_formula(self):
        # I = mu * r^2 for a 2-atom system, computed two ways.
        r = 1.09768
        masses = [14.007, 14.007]
        coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, r]])
        moments, linear = principal_moments_of_inertia(masses, coords)
        assert linear is True
        mu_kg = (14.007 * 14.007) / (14.007 + 14.007) * pt.ATOMIC_MASS_CONSTANT_KG
        i_expected = mu_kg * (r * 1e-10) ** 2
        assert moments[-1] == pytest.approx(i_expected, rel=1e-9)


class TestFiniteGuards:
    """A NaN/inf must raise a clean ValueError, never leak into a value dressed as DERIVED (red-team-found)."""

    def test_nan_frequency_raises_not_a_nan_value(self):
        with pytest.raises(ValueError):
            ideal_gas_entropy(molar_mass_u=18.0, frequencies_cm=[float("nan")],
                              moments_of_inertia_kg_m2=[1e-46], linear=True, symmetry_number=1,
                              electronic_degeneracy=1)

    def test_infinite_temperature_raises_cleanly(self):
        with pytest.raises(ValueError):
            ideal_gas_entropy(molar_mass_u=18.0, frequencies_cm=[100.0],
                              moments_of_inertia_kg_m2=[1e-46], linear=True, symmetry_number=1,
                              electronic_degeneracy=1, temperature_k=float("inf"))

    def test_nonfinite_moment_raises(self):
        with pytest.raises(ValueError):
            ideal_gas_entropy(molar_mass_u=18.0, frequencies_cm=[100.0],
                              moments_of_inertia_kg_m2=[float("inf")], linear=True, symmetry_number=1,
                              electronic_degeneracy=1)

    def test_ultra_stiff_mode_is_finite_zero_not_an_overflow(self):
        # a 1e10 cm^-1 mode is infinitely stiff -> 0 vibrational entropy, computed, not an OverflowError
        s = ideal_gas_entropy(molar_mass_u=1.0, frequencies_cm=[1e10], moments_of_inertia_kg_m2=[1e-46],
                              linear=True, symmetry_number=1, electronic_degeneracy=1)
        assert math.isfinite(s.value_j_per_mol_k)
        assert s.vibrational == 0.0


class TestInputValidation:
    def test_nonpositive_temperature_refused(self):
        with pytest.raises(ValueError):
            diatomic_entropy("N", "N", bond_length_angstrom=1.1, frequency_cm=2000.0,
                             symmetry_number=2, electronic_degeneracy=1, temperature_k=0.0)

    def test_bad_symmetry_number_refused(self):
        with pytest.raises(ValueError):
            ideal_gas_entropy(molar_mass_u=28.0, frequencies_cm=[2000.0],
                              moments_of_inertia_kg_m2=[1e-46], linear=True,
                              symmetry_number=0, electronic_degeneracy=1)

    def test_bad_electronic_degeneracy_refused(self):
        with pytest.raises(ValueError):
            ideal_gas_entropy(molar_mass_u=28.0, frequencies_cm=[2000.0],
                              moments_of_inertia_kg_m2=[1e-46], linear=True,
                              symmetry_number=1, electronic_degeneracy=0)

    def test_linear_needs_one_moment_nonlinear_needs_three(self):
        with pytest.raises(ValueError):
            ideal_gas_entropy(molar_mass_u=44.0, frequencies_cm=[1000.0],
                              moments_of_inertia_kg_m2=[1e-46, 2e-46], linear=False,
                              symmetry_number=1, electronic_degeneracy=1)

    def test_unknown_element_in_diatomic_is_loud(self):
        with pytest.raises(KeyError):
            diatomic_entropy("Xx", "O", bond_length_angstrom=1.1, frequency_cm=2000.0,
                             symmetry_number=1, electronic_degeneracy=1)
