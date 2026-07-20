"""
The AA battery litmus: one cell, several scenarios, and the demand that they COHERE.

Any single scenario is easy to fake. A lookup table returns 1.5 V and looks like a
battery. The test that means something is whether the SAME object, evaluated across
several different environments, gives answers that do not contradict each other -- and
whether the limits line up where physics says they must.

So the scenarios here are chosen to constrain one another:

    structure   the cell is two half-reactions that compose; the electrons cancel
    n           recoverable from the FACTORISATION, and provably not from the composite
    voltage     E = -dE/n, and what an actual oracle predicts for it
    load        an operating point, which must -> the open-circuit value as R -> infinity
    power       ocv * I == P_load + P_internal, at every load, exactly
    matching    maximum power at R_load == R_internal, where efficiency is exactly 1/2
    capacity    charge from stoichiometry, which a real cell can approach and never exceed

The failures are pinned as hard as the successes. The heuristic oracle predicts 8.5 V for
this cell and its error bar excludes the truth; that is recorded here with a number on it
rather than left as a caveat in prose.

Reference data for the alkaline Zn/MnO2 cell
--------------------------------------------
    ZnO + H2O + 2 e-      -> Zn + 2 OH-        E0 = -1.260 V   (CRC, alkaline)
    2 MnO2 + H2O + 2 e-   -> Mn2O3 + 2 OH-     E0 = +0.15  V   (CRC, alkaline)
    cell                                        E0 =  1.41  V
Nominal AA rating is 1.5 V and a fresh cell reads nearer 1.6 V open-circuit; those are
three different quantities and this file does not blur them. Internal resistance of a
fresh AA alkaline is ~0.15-0.3 ohm; rated capacity ~2000-3000 mAh.
"""
from __future__ import annotations

import pytest

from smartchem.category import Bond, Config, Molecule, Reaction, conserves
from smartchem.cell import (
    Cell,
    OperatingPoint,
    coulombs_to_mah,
    matched_load_ohms,
    theoretical_capacity_coulombs,
)
from smartchem.oracle.heuristic import HeuristicOracle

# -- the species ---------------------------------------------------------------------
Zn = Molecule.atom("Zn")
OH = Molecule(("O", "H"), frozenset({Bond(0, 1)}), charge=-1)
H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
ZnO = Molecule(("Zn", "O"), frozenset({Bond(0, 1)}))
MnO2 = Molecule(("Mn", "O", "O"), frozenset({Bond(0, 1), Bond(0, 2)}))
Mn2O3 = Molecule(("Mn", "Mn", "O", "O", "O"),
                 frozenset({Bond(0, 2), Bond(0, 3), Bond(1, 3), Bond(1, 4)}))
E = Molecule.carrier("e-", charge=-1)

#: experiment, from the standard reduction potentials quoted in the module docstring
E0_CELL_VOLTS = 1.41
#: a fresh AA alkaline: ~0.2 ohm internal, ~4 g of zinc
AA_INTERNAL_OHMS = 0.20
AA_ZINC_GRAMS = 4.0
ZINC_MOLAR_MASS = 65.38
#: what the cell is sold as delivering
AA_RATED_MAH = 2500.0


def aa_cell() -> Cell:
    anode = Reaction(Config.of(Zn, OH, OH), Config.of(ZnO, H2O, E, E), name="anode")
    cathode = Reaction(Config.of(MnO2, MnO2, H2O, E, E),
                       Config.of(Mn2O3, OH, OH), name="cathode")
    return Cell(anode, cathode, name="alkaline AA")


# ======================================================================================
class TestTheCellIsAStructure:
    """Before any number: is a battery something this category can hold at all?"""

    def test_the_cell_constructs_from_two_half_reactions(self):
        cell = aa_cell()
        assert cell.electrons == 2

    def test_the_overall_reaction_is_the_chemistry_without_the_electrons(self):
        consumed, produced = aa_cell().net_reaction()
        assert consumed == Config.of(Zn, MnO2, MnO2)
        assert produced == Config.of(ZnO, Mn2O3)
        assert conserves(aa_cell().overall())

    def test_n_is_invisible_in_the_composite_and_present_in_the_factorisation(self):
        """
        The load-bearing structural claim. If ``n`` were recoverable from (dom, cod), a
        cell voltage would be a function of the overall reaction -- and it is not, in
        physics as well as here. Two cell designs running the same overall chemistry
        through different numbers of electrons have different voltages.
        """
        cell = aa_cell()
        overall = cell.overall()
        endpoints = overall.dom.species + overall.cod.species
        assert not any(m.state == "e-" for m in endpoints), "composite forgot the electrons: good"
        intermediate = overall.path[0][1]
        assert any(m.state == "e-" for m in intermediate.species), "path remembers them"
        assert cell.electrons == 2

    def test_a_cell_whose_electrons_do_not_balance_is_unconstructible(self):
        """Same discipline as a mass-violating reaction: refused at construction."""
        anode = Reaction(Config.of(Zn, OH, OH), Config.of(ZnO, H2O, E, E))
        one_electron_cathode = Reaction(
            Config.of(MnO2, MnO2, H2O, E, E), Config.of(Mn2O3, OH, OH))
        Cell(anode, one_electron_cathode)                       # balanced: fine
        # a perfectly legal one-electron cathode -- Na+ + e- -> Na -- which simply does
        # not consume what this anode produces
        na_plus = Molecule.atom("Na", charge=1)
        half = Reaction(Config.of(na_plus, E), Config.of(Molecule.atom("Na")))
        with pytest.raises(ValueError, match="circuit does not close"):
            Cell(anode, half)

    def test_an_anode_that_produces_no_carriers_is_not_an_anode(self):
        plain = Reaction(Config.of(Zn, MnO2, MnO2), Config.of(ZnO, Mn2O3))
        with pytest.raises(ValueError, match="must produce charge carriers"):
            Cell(plain, plain)


# ======================================================================================
class TestTheHeuristicOracleFailsThisLitmus:
    """
    Pinned as a measured failure, not hidden as a caveat.

    The heuristic oracle prices ZnO, MnO2 and Mn2O3 through the legacy ligand-field path
    and DECLINES water -- confident on the hard case, silent on the easy one. The result
    is a 1.5 V cell predicted at 8.5 V.

    What makes it a defect rather than merely a bad number: the stated uncertainty does
    not cover the truth. 8.52 - 4.92 = 3.60 V, and the cell is 1.41 V. An oracle whose
    error bar excludes the right answer is not imprecise, it is inventing -- and this
    repository's one unforgivable defect is a plausible unearned number.

    This test exists to make that visible and to fail loudly if anyone "improves" the
    oracle without fixing it, or fixes it without noticing this got better.
    """

    def test_the_predicted_voltage_is_wrong_by_more_than_five_fold(self):
        volts = aa_cell().open_circuit_voltage(HeuristicOracle())
        assert volts is not None, "the oracle does price these species, wrongly"
        assert volts.value_ev == pytest.approx(8.52, abs=0.02)
        assert volts.value_ev / E0_CELL_VOLTS > 5.0

    def test_the_error_bar_does_not_cover_the_truth(self):
        """The specific thing that makes this inventing rather than approximating."""
        volts = aa_cell().open_circuit_voltage(HeuristicOracle())
        low = volts.value_ev - volts.uncertainty_ev
        assert low > E0_CELL_VOLTS, (
            f"one-sigma low end {low:.2f} V is still above the true {E0_CELL_VOLTS} V")

    def test_the_sign_is_right_even_though_the_magnitude_is_not(self):
        """The cell does at least discharge in the correct direction. Small mercies."""
        assert aa_cell().open_circuit_voltage(HeuristicOracle()).value_ev > 0


# ======================================================================================
class TestTheScenariosCohere:
    """
    The heart of the litmus. Every scenario below uses the SAME experimental open-circuit
    voltage and the SAME internal resistance, and the demand is that they agree at the
    limits and satisfy the conservation identity everywhere in between.
    """

    def test_an_open_circuit_reads_the_full_cell_voltage(self):
        """Scenario 1: no load. The definition, and the limit every other scenario must
        approach."""
        op = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, load_ohms=1e12)
        assert op.terminal_volts == pytest.approx(E0_CELL_VOLTS, rel=1e-9)
        assert op.current_amps == pytest.approx(0.0, abs=1e-9)

    def test_a_load_sags_the_terminal_voltage(self):
        """Scenario 2: a 10 ohm load, which is a modest drain for a AA."""
        op = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, load_ohms=10.0)
        assert 0 < op.terminal_volts < E0_CELL_VOLTS
        assert op.current_amps == pytest.approx(1.41 / 10.2, rel=1e-6)

    def test_the_load_scenario_converges_on_the_open_circuit_scenario(self):
        """
        THE coherence test. Two scenarios written independently must be the same scenario
        in the limit. A model where "under load" and "open circuit" are separate lookups
        passes each of them alone and fails this.
        """
        previous = 0.0
        for decade in range(1, 9):
            op = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, load_ohms=10.0 ** decade)
            assert op.terminal_volts > previous, "monotone in load resistance"
            previous = op.terminal_volts
        assert previous == pytest.approx(E0_CELL_VOLTS, rel=1e-7)

    def test_a_dead_short_delivers_no_power_to_the_load_and_all_of_it_as_heat(self):
        """The other limit, and the reason a shorted cell gets hot rather than useful."""
        op = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, load_ohms=0.0)
        assert op.terminal_volts == pytest.approx(0.0, abs=1e-12)
        assert op.current_amps == pytest.approx(E0_CELL_VOLTS / AA_INTERNAL_OHMS)
        assert op.power_load_watts == pytest.approx(0.0, abs=1e-12)
        assert op.power_internal_watts > 9.0
        assert op.efficiency == pytest.approx(0.0, abs=1e-12)

    @pytest.mark.parametrize("load", [0.01, 0.1, 0.2, 1.0, 10.0, 100.0, 1e6])
    def test_power_balances_at_every_load(self, load):
        """
        Conservation, in its electrical costume: the chemical power leaving the cell
        equals the power in the load plus the power dissipated inside it. Exactly, at
        every operating point, or the scenarios are not describing one system.
        """
        op = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, load)
        chemical = op.ocv_volts * op.current_amps
        assert chemical == pytest.approx(
            op.power_load_watts + op.power_internal_watts, rel=1e-12)

    def test_maximum_power_is_at_the_matched_load_and_costs_half_the_energy(self):
        """
        The counterintuitive consequence worth having a test for: the load that draws the
        most POWER wastes exactly half the chemical energy as internal heat. Maximum power
        and maximum efficiency are different operating points, and a cell designed for one
        is not designed for the other.
        """
        matched = matched_load_ohms(AA_INTERNAL_OHMS)
        best = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, matched)
        for other in (matched * 0.5, matched * 0.9, matched * 1.1, matched * 2.0):
            assert OperatingPoint(
                E0_CELL_VOLTS, AA_INTERNAL_OHMS, other).power_load_watts \
                < best.power_load_watts
        assert best.efficiency == pytest.approx(0.5, rel=1e-12)

    def test_efficiency_rises_with_load_while_power_does_not(self):
        """Two figures of merit that disagree -- which is why both scenarios are needed."""
        light = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, 100.0)
        heavy = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, 0.2)
        assert light.efficiency > heavy.efficiency
        assert light.power_load_watts < heavy.power_load_watts


# ======================================================================================
class TestCapacityComesFromStoichiometry:
    """
    The scenario that ties the electrical picture back to the chemical one: how long the
    battery lasts is a fact about how much zinc is in it, via ``n`` and Faraday.
    """

    def test_the_theoretical_capacity_of_a_AA_is_the_right_order(self):
        moles = AA_ZINC_GRAMS / ZINC_MOLAR_MASS
        q = theoretical_capacity_coulombs(moles, aa_cell().electrons)
        mah = coulombs_to_mah(q)
        assert 3000 < mah < 3600, f"got {mah:.0f} mAh from {AA_ZINC_GRAMS} g Zn"

    def test_the_rated_capacity_never_exceeds_the_stoichiometric_ceiling(self):
        """
        The electrical analogue of a mass-violating reaction. A cell rated above its own
        stoichiometry would be producing more electrons than its chemistry allows, and
        this is the check that would catch a reference number transcribed wrong.
        """
        moles = AA_ZINC_GRAMS / ZINC_MOLAR_MASS
        ceiling = coulombs_to_mah(theoretical_capacity_coulombs(moles, aa_cell().electrons))
        assert AA_RATED_MAH < ceiling, (
            f"rated {AA_RATED_MAH} mAh exceeds the stoichiometric ceiling {ceiling:.0f} mAh")
        assert AA_RATED_MAH / ceiling > 0.6, "and is within a plausible fraction of it"

    def test_capacity_scales_with_the_electrons_the_reaction_transfers(self):
        """``n`` is doing real work here, not decorating the formula."""
        moles = 1.0
        assert theoretical_capacity_coulombs(moles, 2) == pytest.approx(
            2 * theoretical_capacity_coulombs(moles, 1))

    def test_the_energy_a_full_discharge_delivers(self):
        """
        Closing the loop: charge x voltage is energy, and it should land near the few
        watt-hours a AA is actually sold as holding.
        """
        moles = AA_ZINC_GRAMS / ZINC_MOLAR_MASS
        joules = theoretical_capacity_coulombs(moles, 2) * E0_CELL_VOLTS
        watt_hours = joules / 3600.0
        assert 4.0 < watt_hours < 5.5, f"got {watt_hours:.2f} Wh"
