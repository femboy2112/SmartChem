"""
The photon oracle: the first non-chemical energy source in the package.

Two things are under test here. The obvious one is that ``E = hc/lambda`` is arithmetically
right. The one that matters more is that extending the oracle contract into a new domain did
not weaken it -- the new oracle declines everything outside its competence, the old oracles
still decline quanta, and the derived quantities that were only ever exercised on matter do
not silently produce a number when handed a photon.
"""
from __future__ import annotations

import math

import pytest

from smartchem.category import Molecule
from smartchem.oracle import HeuristicOracle, PhotonOracle, available_oracles
from smartchem.oracle.base import EnergyOracle
from smartchem.oracle.photon import HC_EV_NM, H_EV_S


class TestTheArithmetic:
    def test_the_defining_wavelength_is_exactly_one_electronvolt(self):
        """hc in eV*nm is by construction the wavelength of a 1 eV photon."""
        est = PhotonOracle(HC_EV_NM).energy(Molecule.quantum())
        assert est is not None
        assert est.value_ev == pytest.approx(1.0, abs=1e-12)

    @pytest.mark.parametrize("wavelength_nm,expected_ev", [
        (532.0, 2.330530),     # frequency-doubled Nd:YAG, the standard green laser line
        (589.0, 2.104994),     # sodium D
        (1064.0, 1.165265),    # Nd:YAG fundamental
        (121.567, 10.198834),  # hydrogen Lyman-alpha
    ])
    def test_known_lines(self, wavelength_nm, expected_ev):
        est = PhotonOracle(wavelength_nm).energy(Molecule.quantum())
        assert est is not None
        assert est.value_ev == pytest.approx(expected_ev, abs=1e-5)

    def test_energy_is_inverse_in_wavelength(self):
        a = PhotonOracle(400.0).energy(Molecule.quantum())
        b = PhotonOracle(800.0).energy(Molecule.quantum())
        assert a is not None and b is not None
        assert a.value_ev == pytest.approx(2.0 * b.value_ev, rel=1e-12)

    def test_the_frequency_constructor_agrees_with_h_nu(self):
        """The wavelength and frequency routes have to be the same physics."""
        nu = 5.0e14
        oracle = PhotonOracle.from_frequency_hz(nu)
        est = oracle.energy(Molecule.quantum())
        assert est is not None
        assert est.value_ev == pytest.approx(H_EV_S * nu, rel=1e-12)
        assert oracle.frequency_hz == pytest.approx(nu, rel=1e-12)

    def test_a_nonpositive_wavelength_is_rejected_not_infinite(self):
        for bad in (0.0, -1.0, -532.0):
            with pytest.raises(ValueError):
                PhotonOracle(bad)

    def test_negative_uncertainty_is_rejected(self):
        with pytest.raises(ValueError):
            PhotonOracle(532.0, uncertainty_nm=-1.0)


class TestUncertaintyIsPropagatedNotInvented:
    def test_an_exact_wavelength_gives_exactly_zero(self):
        """
        Zero here is a claim, not a default: hc is exact by SI definition, so an exactly
        stated wavelength leaves nothing to be uncertain about.
        """
        oracle = PhotonOracle(532.0)
        assert oracle.nominal_accuracy_ev == 0.0
        est = oracle.energy(Molecule.quantum())
        assert est is not None
        assert est.uncertainty_ev == 0.0

    def test_fractional_uncertainty_is_preserved(self):
        """dE/E = dlambda/lambda, because E is a reciprocal in lambda."""
        oracle = PhotonOracle(532.0, uncertainty_nm=0.532)  # exactly 0.1%
        est = oracle.energy(Molecule.quantum())
        assert est is not None
        assert est.uncertainty_ev / est.value_ev == pytest.approx(1e-3, rel=1e-12)

    def test_a_wider_wavelength_band_is_a_wider_energy_band(self):
        narrow = PhotonOracle(532.0, uncertainty_nm=0.1).energy(Molecule.quantum())
        wide = PhotonOracle(532.0, uncertainty_nm=1.0).energy(Molecule.quantum())
        assert narrow is not None and wide is not None
        assert wide.uncertainty_ev > narrow.uncertainty_ev
        assert narrow.value_ev == pytest.approx(wide.value_ev, rel=1e-12)


class TestItDeclinesWhatItCannotValue:
    """
    The whole contract. This oracle knows one formula, and every species that formula does
    not describe has to come back ``None`` rather than a plausible number.
    """

    def test_it_conforms_to_the_oracle_protocol(self):
        assert isinstance(PhotonOracle(532.0), EnergyOracle)

    @pytest.mark.parametrize("molecule", [
        Molecule.atom("H"),
        Molecule.diatomic("H", "H"),
        Molecule.diatomic("C", "O", order=3),
    ])
    def test_matter_is_declined(self, molecule):
        assert PhotonOracle(532.0).energy(molecule) is None

    def test_an_electron_is_declined(self):
        """
        A charged zero-atom carrier is how this package spells an electron. It has rest
        mass and is not a quantum of radiation; hc/lambda is the wrong physics, and the
        atom count alone does not distinguish the two cases.
        """
        assert PhotonOracle(532.0).energy(Molecule.carrier("e-", charge=-1)) is None

    def test_a_foreign_label_is_declined_rather_than_answered(self):
        """
        The enforced form of this design's limitation. A 532 nm oracle handed a token
        labelled ``1064nm`` must not price it at 532 nm just because it is a quantum -- the
        label may well mean what it says, but nothing checks that, and answering would turn
        a naming coincidence into a wrong number.
        """
        oracle = PhotonOracle(532.0)
        assert oracle.energy(Molecule.quantum("1064nm")) is None
        assert oracle.energy(Molecule.quantum("hv")) is None
        assert oracle.energy(Molecule.quantum("green")) is None

    def test_its_own_label_and_the_unlabelled_quantum_are_both_valued(self):
        oracle = PhotonOracle(532.0)
        assert oracle.energy(Molecule.quantum()) is not None
        assert oracle.energy(Molecule.quantum(oracle.label)) is not None

    def test_two_instances_do_not_answer_for_each_other(self):
        green, infrared = PhotonOracle(532.0), PhotonOracle(1064.0)
        assert green.energy(Molecule.quantum(infrared.label)) is None
        assert infrared.energy(Molecule.quantum(green.label)) is None


class TestTheOldContractStillHolds:
    def test_the_chemistry_oracles_still_decline_a_quantum(self):
        """
        Adding a radiation oracle must not have taught anything else to price radiation.
        The existing invariant is that an oracle which does not model a species declines it.
        """
        assert HeuristicOracle().energy(Molecule.quantum("hv")) is None
        for name, oracle in sorted(available_oracles().items()):
            assert oracle.energy(Molecule.quantum("hv")) is None, name

    def test_the_photon_oracle_is_not_in_the_benchmark_registry(self):
        """
        There is no canonical wavelength, so there is no instance that belongs in a
        name-to-instance registry. Any entry here would be an invented default.
        """
        assert "photon" not in available_oracles()


class TestAtomizationEnergyOfSomethingWithNoAtoms:
    """
    A latent defect this oracle is what arms, pinned here where the connection is legible.

    ``atomization_energy`` computes ``E(free atoms) - E(molecule)`` by summing over
    ``Counter(molecule.atoms)``. For a zero-atom species that loop body never runs, the sum
    stays at zero, and the method returns ``0 - E`` -- the species' own energy, negated,
    labelled as a different observable. It was unreachable only because every oracle in the
    package declined zero-atom species; the first one that values them makes it reachable.

    A photon of +2.33 eV coming back as an atomization energy of -2.33 eV is a wrong number
    rather than a refusal, which is the one failure mode this package does not tolerate.
    """

    def test_a_photon_has_no_atomization_energy(self):
        oracle = PhotonOracle(532.0)
        quantum = Molecule.quantum()
        assert oracle.energy(quantum) is not None      # it CAN value the species
        assert oracle.atomization_energy(quantum) is None  # and still declines the derived one

    def test_the_guard_is_not_just_the_energy_declining(self):
        """
        Distinguish the two reasons this could return None. If it only declined because
        ``energy`` declined, the guard would evaporate the moment an oracle valued quanta --
        which is precisely the case under test.
        """
        oracle = PhotonOracle(532.0)
        est = oracle.energy(Molecule.quantum())
        assert est is not None and est.value_ev > 0.0
        assert oracle.atomization_energy(Molecule.quantum()) is None

    def test_matter_still_gets_an_atomization_energy(self):
        """The guard must not have made the normal path decline."""
        assert HeuristicOracle().atomization_energy(Molecule.diatomic("H", "H")) is not None

    def test_a_charged_carrier_is_still_declined(self):
        assert PhotonOracle(532.0).atomization_energy(Molecule.carrier("e-", charge=-1)) is None


class TestTheConstantsAreTheDefinedOnes:
    def test_hc_is_consistent_with_h_and_c(self):
        """
        Guard against a typo in either digit string: the two constants are not independent,
        so one can check the other. c = 299792458 m/s exactly.
        """
        assert HC_EV_NM == pytest.approx(H_EV_S * 299792458.0 * 1e9, rel=1e-14)

    def test_hc_is_not_the_legacy_magic_number(self):
        """
        ``legacy.py`` carries a bare 1240.0 for this quantity. Nothing new should inherit
        it; this pins that the new constant is the defined value, not the rounded one.
        """
        assert HC_EV_NM != 1240.0
        assert math.isclose(HC_EV_NM, 1239.8419843320025, rel_tol=1e-15)
