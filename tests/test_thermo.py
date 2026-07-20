"""
The oracle contract and the quantities derived from it.

The *functor laws* live in ``tests/test_functor.py``. This file pins the surrounding
discipline that keeps the accuracy dial honest: an oracle may decline but may not invent,
partial pricing is refused rather than silently understated, a verdict never outruns its
own error bar, and derived quantities agree with the primitive they are derived from.

Nothing here requires an optional quantum-chemistry backend. A stub exercises the contract,
so the rules stay enforced on a bare numpy/scipy install.
"""
from __future__ import annotations

import pytest

from smartchem.category import Bond, Config, Molecule, Reaction
from smartchem.oracle import HeuristicOracle
from smartchem.oracle.base import BaseOracle, EnergyOracle, Estimate
from smartchem.thermo import (
    bonding_energy,
    configuration_energy,
    favourability,
    is_exothermic,
    reaction_energy,
)


class StubOracle(BaseOracle):
    """
    Deterministic oracle over a fixed per-element table, with a bond term.

    Keeps the arbitrary-zero contract: one consistent reference for every species. Declines
    anything containing an element it has no entry for.
    """

    name = "stub"
    nominal_accuracy_ev = 0.1

    def __init__(self, offsets=None, bond_ev: float = 4.5):
        self.offsets = offsets if offsets is not None else {
            "H": -100.0, "Cl": -300.0, "Na": -200.0, "C": -500.0, "O": -700.0,
        }
        self.bond_ev = bond_ev
        self.calls: list[Molecule] = []

    def energy(self, molecule: Molecule) -> Estimate | None:
        self.calls.append(molecule)
        if any(s not in self.offsets for s in molecule.atoms):
            return None
        value = sum(self.offsets[s] for s in molecule.atoms)
        value -= self.bond_ev * sum(b.order for b in molecule.bonds)
        return Estimate(value, self.nominal_accuracy_ev if molecule.bonds else 0.0,
                        self.name, 0.0, "stub")


class TestOracleContract:
    def test_stub_satisfies_protocol(self):
        assert isinstance(StubOracle(), EnergyOracle)

    def test_heuristic_satisfies_protocol(self):
        assert isinstance(HeuristicOracle(), EnergyOracle)

    def test_declining_returns_none_not_a_number(self):
        assert StubOracle().energy(Molecule.diatomic("Xe", "Xe")) is None

    def test_estimate_carries_provenance(self):
        est = StubOracle().energy(Molecule.diatomic("H", "H"))
        assert est.method
        assert est.uncertainty_ev > 0

    def test_the_primitive_receives_the_whole_species(self):
        """
        The interface asks about a species, not an atom pair. That is what lets an oracle
        see topology, charge and order at all -- the old ``estimate(symbols)`` could not.
        """
        o = StubOracle()
        configuration_energy(Config.of(Molecule.diatomic("C", "O", order=3)), o)
        assert o.calls, "the oracle was never consulted"
        seen = o.calls[0]
        assert isinstance(seen, Molecule)
        assert seen.bonds, "topology must reach the oracle"


class TestDerivedQuantities:
    """``atomization_energy`` and ``bond_energy`` are derived from ``energy``, not parallel
    to it. If they ever disagree with the primitive, the derivation is wrong."""

    def test_atomization_is_positive_for_a_bound_species(self):
        est = StubOracle().atomization_energy(Molecule.diatomic("H", "H"))
        assert est is not None
        assert est.value_ev == pytest.approx(4.5)

    def test_atomization_scales_with_bond_order(self):
        o = StubOracle()
        single = o.atomization_energy(Molecule.diatomic("C", "O", order=1)).value_ev
        triple = o.atomization_energy(Molecule.diatomic("C", "O", order=3)).value_ev
        assert triple == pytest.approx(3 * single)

    def test_a_free_atom_has_zero_atomization_energy(self):
        est = StubOracle().atomization_energy(Molecule.atom("H"))
        assert est.value_ev == pytest.approx(0.0)

    def test_bond_energy_agrees_with_atomization(self):
        o = StubOracle()
        assert o.bond_energy(("H", "H")) == pytest.approx(
            o.atomization_energy(Molecule.diatomic("H", "H")).value_ev)

    def test_bond_energy_declines_for_unknown_elements(self):
        assert StubOracle().bond_energy(("Xe", "Xe")) is None

    def test_atomization_declines_when_the_species_declines(self):
        assert StubOracle().atomization_energy(Molecule.diatomic("Xe", "Xe")) is None


class TestBondingEnergy:
    def test_free_atoms_have_zero_bonding_energy(self):
        """Zero, not unknown. Free atoms genuinely have no bonding energy."""
        est = bonding_energy(Config.atoms("H", "H"), StubOracle())
        assert est is not None
        assert est.value_ev == pytest.approx(0.0)

    def test_a_bound_species_is_negative(self):
        est = bonding_energy(Config.of(Molecule.diatomic("H", "H")), StubOracle())
        assert est is not None
        assert est.value_ev == pytest.approx(-4.5)

    def test_unpriceable_species_refuses_the_whole_configuration(self):
        """
        Partial pricing would silently understate the energy, which is the failure mode
        where a wrong number looks like a right one.
        """
        cfg = Config.of(Molecule.diatomic("H", "H"), Molecule.diatomic("Xe", "Xe"))
        assert bonding_energy(cfg, StubOracle()) is None

    def test_uncertainty_accumulates_across_species(self):
        cfg = Config.of(Molecule.diatomic("H", "H"), Molecule.diatomic("Na", "Cl"))
        est = bonding_energy(cfg, StubOracle())
        assert est is not None
        assert est.uncertainty_ev > 0.1, "two uncertain species must exceed one"


class TestBondOrderReachesTheOracle:
    """
    Supersedes ``TestBondOrderIsNotAMultiplier``, whose premise was inverted by the move to
    a species primitive.

    Under bond additivity the oracle was asked about an atom *pair*, which carries no
    order, so a C-C single and a C=C double bond were necessarily identical -- and the old
    test correctly asserted that. Now the object carries its topology and the oracle sees
    it, so they must differ.

    Caveat, stated rather than implied: whether order *changes the answer* is up to the
    oracle. ``PySCFOracle`` still resolves geometry from a table keyed by formula, so it
    does not yet distinguish them. That is now a backend limitation rather than an
    interface one, which is the whole point of the change.
    """

    def test_single_and_triple_differ(self):
        o = StubOracle()
        single = Config.of(Molecule(("C", "O"), frozenset({Bond(0, 1, 1)})))
        triple = Config.of(Molecule(("C", "O"), frozenset({Bond(0, 1, 3)})))
        assert (configuration_energy(triple, o).value_ev
                < configuration_energy(single, o).value_ev)

    def test_higher_order_is_more_strongly_bound(self):
        o = StubOracle()
        single = Config.of(Molecule(("C", "O"), frozenset({Bond(0, 1, 1)})))
        triple = Config.of(Molecule(("C", "O"), frozenset({Bond(0, 1, 3)})))
        assert bonding_energy(triple, o).value_ev == pytest.approx(3 * bonding_energy(
            single, o).value_ev)


class TestReactionEnergy:
    def test_bond_formation_is_exothermic(self):
        rxn = Reaction(Config.atoms("Na", "Cl"),
                       Config.of(Molecule.diatomic("Na", "Cl")))
        est = reaction_energy(rxn, StubOracle())
        assert est is not None
        assert est.value_ev == pytest.approx(-4.5)
        assert is_exothermic(rxn, StubOracle()) is True

    def test_bond_breaking_is_endothermic(self):
        rxn = Reaction(Config.of(Molecule.diatomic("Na", "Cl")),
                       Config.atoms("Na", "Cl"))
        est = reaction_energy(rxn, StubOracle())
        assert est is not None
        assert est.value_ev == pytest.approx(+4.5)
        assert is_exothermic(rxn, StubOracle()) is False

    def test_unknown_is_none_not_false(self):
        """
        'Cannot price this' and 'this is uphill' are different facts. Collapsing the first
        into the second reports an unpriceable reaction as unfavourable.
        """
        rxn = Reaction(Config.atoms("Xe", "Xe"),
                       Config.of(Molecule.diatomic("Xe", "Xe")))
        assert is_exothermic(rxn, StubOracle()) is None
        assert reaction_energy(rxn, StubOracle()) is None

    def test_same_reaction_different_oracles(self):
        """The dial: identical structure, different accuracy tiers."""
        rxn = Reaction(Config.atoms("Na", "Cl"),
                       Config.of(Molecule.diatomic("Na", "Cl")))
        precise, vague = StubOracle(), StubOracle()
        vague.nominal_accuracy_ev = 3.0
        a, b = reaction_energy(rxn, precise), reaction_energy(rxn, vague)
        assert a.value_ev == pytest.approx(b.value_ev)
        assert a.uncertainty_ev < b.uncertainty_ev


class TestVerdictRespectsUncertainty:
    def test_verdict_within_error_bar_is_undecided(self):
        """A prediction smaller than its own error bar has not earned a direction."""
        o = StubOracle(bond_ev=0.05)
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
        assert HeuristicOracle().bond_energy(("C", "O")) is None

    def test_legacy_overshoots_sodium_chloride(self):
        got = HeuristicOracle().bond_energy(("Na", "Cl"))
        assert got is not None
        assert got > 10.0, "documented ~3x overshoot against 4.23 eV experimental"

    def test_legacy_is_bond_additive_and_says_so(self):
        """
        Bond additivity is now a property of THIS oracle, not of the framework. A free atom
        sits at exactly zero on its reference, which is what makes it additive.
        """
        est = HeuristicOracle().energy(Molecule.atom("Na"))
        assert est is not None
        assert est.value_ev == 0.0
