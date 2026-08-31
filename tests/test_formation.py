"""ΔfH°(0 K) DERIVED from a computed atomization energy -- the inverse-algebra proof + the fail-closed bounds.

The load-bearing test is the ROUND TRIP: the derivation is the exact inverse of
``reference.atomization_energy_ev``, so feeding back the atomization energy the forward map produces must
recover the original formation enthalpy to machine precision.  A stub oracle supplies the D0 so the ALGEBRA
is tested without invoking PySCF; the bounds tests prove it fails CLOSED (loud None) off its domain.
"""
from __future__ import annotations

from collections import Counter

import pytest

from smartchem.category import Bond, Molecule
from smartchem.data.reference import ATOM_FORMATION_KJ, KJ_PER_EV
from smartchem.experiment.formation import formation_enthalpy_0k
from smartchem.oracle.base import Estimate


class _StubOracle:
    """Returns a fixed atomization energy (eV), or None to model an oracle decline (fail-closed)."""

    name = "stub"

    def __init__(self, d0_ev, *, uncertainty_ev=0.05, declines=False):
        self._d0 = d0_ev
        self._u = uncertainty_ev
        self._declines = declines

    def atomization_energy(self, molecule):
        if self._declines:
            return None
        return Estimate(value_ev=self._d0, uncertainty_ev=self._u, method="stub")


def _water():
    return Molecule(atoms=("O", "H", "H"), bonds=frozenset({Bond(0, 1), Bond(0, 2)}))


def _d0_for(molecule, target_dfh_kj):
    """The atomization energy (eV) the forward map produces for a molecule with formation enthalpy target."""
    atoms_kj = sum(n * ATOM_FORMATION_KJ[s] for s, n in Counter(molecule.atoms).items())
    return (atoms_kj - target_dfh_kj) / KJ_PER_EV


class TestRoundTrip:
    @pytest.mark.parametrize("target_dfh", [-241.8, -100.0, 0.0, 50.0])
    def test_derivation_is_the_exact_inverse(self, target_dfh):
        mol = _water()
        oracle = _StubOracle(_d0_for(mol, target_dfh))
        derived = formation_enthalpy_0k(mol, oracle)
        assert derived is not None
        assert derived.grade == "DERIVED"
        assert derived.value_kj_per_mol == pytest.approx(target_dfh, abs=1e-9)

    def test_sign_is_load_bearing(self):
        # A more strongly bound molecule (larger D0) has a LOWER (more negative) formation enthalpy.
        mol = _water()
        loose = formation_enthalpy_0k(mol, _StubOracle(9.0))
        tight = formation_enthalpy_0k(mol, _StubOracle(10.0))
        assert tight.value_kj_per_mol < loose.value_kj_per_mol

    def test_band_propagates_from_oracle_error(self):
        mol = _water()
        derived = formation_enthalpy_0k(mol, _StubOracle(9.5, uncertainty_ev=0.1))
        assert derived.uncertainty_kj_per_mol == pytest.approx(0.1 * KJ_PER_EV, rel=1e-9)
        # and the note names the un-cancelled atomic-anchor systematic (honesty, not a fabricated number)
        assert any("anchor" in n for n in derived.notes)


class TestFailsClosed:
    def test_non_chno_element_is_a_loud_gap(self):
        nacl = Molecule(atoms=("Na", "Cl"), bonds=frozenset({Bond(0, 1)}))
        assert formation_enthalpy_0k(nacl, _StubOracle(4.0)) is None

    def test_charged_species_declined(self):
        hydroxide = Molecule(atoms=("O", "H"), bonds=frozenset({Bond(0, 1)}), charge=-1)
        assert formation_enthalpy_0k(hydroxide, _StubOracle(5.0)) is None

    def test_oracle_decline_propagates_as_none(self):
        assert formation_enthalpy_0k(_water(), _StubOracle(0.0, declines=True)) is None

    def test_empty_molecule_is_a_loud_gap(self):
        # a bare empty species -- no atoms, no formation enthalpy -> loud None, never a fabricated 0
        empty = Molecule(atoms=(), bonds=frozenset())
        assert formation_enthalpy_0k(empty, _StubOracle(0.0)) is None
