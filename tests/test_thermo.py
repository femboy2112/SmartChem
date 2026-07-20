"""
The oracle layer and its join to the categorical core.

These tests pin the discipline that keeps the accuracy dial honest: an oracle may decline
but may not invent, partial pricing is refused rather than silently understated, and a
verdict never outruns its own error bar.

Nothing here requires an optional quantum-chemistry backend. A stub oracle exercises the
contract, so the rules stay enforced on a bare numpy/scipy install.
"""
from __future__ import annotations

import math

import pytest

from smartchem.category import Bond, Config, Molecule, Reaction
from smartchem.oracle import HeuristicOracle
from smartchem.oracle.base import BaseOracle, EnergyOracle, Estimate
from smartchem.thermo import (
    bonding_energy,
    favourability,
    is_exothermic,
    reaction_energy,
)


class StubOracle(BaseOracle):
    """Deterministic oracle over a fixed table. Declines anything it does not know."""

    name = "stub"
    nominal_accuracy_ev = 0.1

    def __init__(self, table: dict[frozenset[str], float] | None = None):
        self.table = table if table is not None else {
            frozenset({"H"}): 4.5,
            frozenset({"H", "Cl"}): 4.4,
            frozenset({"Na", "Cl"}): 4.2,
            frozenset({"C", "O"}): 11.2,
        }
        self.calls: list[tuple[str, ...]] = []

    def estimate(self, symbols):
        self.calls.append(symbols)
        key = frozenset(symbols)
        if key not in self.table:
            return None
        return Estimate(self.table[key], self.nominal_accuracy_ev, self.name, 0.0, "stub")


class TestOracleContract:
    def test_stub_satisfies_protocol(self):
        assert isinstance(StubOracle(), EnergyOracle)

    def test_heuristic_satisfies_protocol(self):
        assert isinstance(HeuristicOracle(), EnergyOracle)

    def test_declining_returns_none_not_a_number(self):
        assert StubOracle().estimate(("Xe", "Xe")) is None

    def test_bond_energy_delegates_to_estimate(self):
        o = StubOracle()
        assert o.bond_energy(("H", "H")) == pytest.approx(4.5)
        assert o.bond_energy(("Xe", "Xe")) is None

    def test_estimate_carries_provenance(self):
        est = StubOracle().estimate(("H", "H"))
        assert est.method
        assert est.uncertainty_ev > 0


class TestBondingEnergy:
    def test_free_atoms_have_zero_bonding_energy(self):
        """Zero, not unknown. Free atoms genuinely have no bonds."""
        est = bonding_energy(Config.atoms("H", "H"), StubOracle())
        assert est is not None
        assert est.value_ev == 0.0

    def test_single_bond_is_negative(self):
        est = bonding_energy(Config.of(Molecule.diatomic("H", "H")), StubOracle())
        assert est is not None
        assert est.value_ev == pytest.approx(-4.5)

    def test_unpriceable_bond_refuses_the_whole_configuration(self):
        """
        Partial pricing would silently understate the energy, which is the failure mode
        where a wrong number looks like a right one.
        """
        cfg = Config.of(Molecule.diatomic("H", "H"), Molecule.diatomic("Xe", "Xe"))
        assert bonding_energy(cfg, StubOracle()) is None

    def test_uncertainty_adds_in_quadrature(self):
        cfg = Config.of(Molecule.diatomic("H", "H"), Molecule.diatomic("Na", "Cl"))
        est = bonding_energy(cfg, StubOracle())
        assert est is not None
        assert est.uncertainty_ev == pytest.approx(math.sqrt(0.1**2 + 0.1**2))


class TestBondOrderIsNotAMultiplier:
    """
    Regression: an earlier version of thermo.py multiplied the oracle's value by bond
    order, which triple-counted CO -- the oracle already returns the ground-state
    diatomic's full dissociation energy, triple bond included.
    """

    def test_triple_bond_not_scaled(self):
        o = StubOracle()
        single = Config.of(Molecule(("C", "O"), frozenset({Bond(0, 1, 1)})))
        triple = Config.of(Molecule(("C", "O"), frozenset({Bond(0, 1, 3)})))
        e_single = bonding_energy(single, o)
        e_triple = bonding_energy(triple, o)
        assert e_single is not None and e_triple is not None
        assert e_triple.value_ev == pytest.approx(e_single.value_ev)
        assert e_triple.value_ev == pytest.approx(-11.2)

    def test_declared_order_is_recorded_in_notes(self):
        triple = Config.of(Molecule(("C", "O"), frozenset({Bond(0, 1, 3)})))
        est = bonding_energy(triple, StubOracle())
        assert est is not None
        assert "multiple bonds" in est.notes


class TestReactionEnergy:
    def test_bond_formation_is_exothermic(self):
        rxn = Reaction(Config.atoms("Na", "Cl"),
                       Config.of(Molecule.diatomic("Na", "Cl")))
        est = reaction_energy(rxn, StubOracle())
        assert est is not None
        assert est.value_ev == pytest.approx(-4.2)
        assert is_exothermic(rxn, StubOracle()) is True

    def test_bond_breaking_is_endothermic(self):
        rxn = Reaction(Config.of(Molecule.diatomic("Na", "Cl")),
                       Config.atoms("Na", "Cl"))
        est = reaction_energy(rxn, StubOracle())
        assert est is not None
        assert est.value_ev == pytest.approx(+4.2)
        assert is_exothermic(rxn, StubOracle()) is False

    def test_unknown_is_none_not_false(self):
        """
        'Cannot price this' and 'this is uphill' are different facts. Collapsing the
        first into the second reports an unpriceable reaction as unfavourable.
        """
        rxn = Reaction(Config.atoms("Xe", "Xe"),
                       Config.of(Molecule.diatomic("Xe", "Xe")))
        assert is_exothermic(rxn, StubOracle()) is None
        assert reaction_energy(rxn, StubOracle()) is None

    def test_same_reaction_different_oracles(self):
        """The dial: identical structure, different accuracy tiers."""
        rxn = Reaction(Config.atoms("Na", "Cl"),
                       Config.of(Molecule.diatomic("Na", "Cl")))
        precise = StubOracle()
        vague = StubOracle()
        vague.nominal_accuracy_ev = 3.0
        a = reaction_energy(rxn, precise)
        b = reaction_energy(rxn, vague)
        assert a is not None and b is not None
        assert a.value_ev == pytest.approx(b.value_ev)
        assert a.uncertainty_ev < b.uncertainty_ev


class TestVerdictRespectsUncertainty:
    def test_verdict_within_error_bar_is_undecided(self):
        """A prediction smaller than its own error bar has not earned a direction."""
        o = StubOracle({frozenset({"Na", "Cl"}): 0.05})
        o.nominal_accuracy_ev = 3.0
        rxn = Reaction(Config.atoms("Na", "Cl"),
                       Config.of(Molecule.diatomic("Na", "Cl")))
        assert "UNDECIDED" in favourability(rxn, o)

    def test_confident_verdict_states_direction(self):
        rxn = Reaction(Config.atoms("Na", "Cl"),
                       Config.of(Molecule.diatomic("Na", "Cl")))
        assert "exothermic" in favourability(rxn, StubOracle())

    def test_declined_verdict_says_so(self):
        rxn = Reaction(Config.atoms("Xe", "Xe"),
                       Config.of(Molecule.diatomic("Xe", "Xe")))
        assert "UNKNOWN" in favourability(rxn, StubOracle())


class TestLegacyBaselineIsMeasurable:
    """The legacy heuristic is kept precisely so it can be measured, not trusted."""

    def test_legacy_still_refuses_carbon_monoxide(self):
        assert HeuristicOracle().estimate(("C", "O")) is None

    def test_legacy_overshoots_sodium_chloride(self):
        est = HeuristicOracle().estimate(("Na", "Cl"))
        assert est is not None
        assert est.value_ev > 10.0, "documented ~3x overshoot against 4.23 eV experimental"
