"""
The AA battery litmus: one cell, several scenarios, and the demand that they COHERE.

Any single scenario is easy to fake. A lookup table returns 1.5 V and looks like a
battery. The test that means something is whether the SAME object, evaluated across
several different environments, gives answers that do not contradict each other -- and
whether the limits line up where physics says they must.

So the scenarios here are chosen to constrain one another:

    structure   the cell is two half-reactions that compose; the electrons cancel
    n           recoverable from the FACTORISATION, and provably not from the composite
    diagnostic  -dE/n, explicitly not an electrochemical open-circuit voltage
    load        an operating point, which must -> the open-circuit value as R -> infinity
    power       ocv * I == P_load + P_internal, at every load, exactly
    matching    maximum power at R_load == R_internal, where efficiency is exactly 1/2
    capacity    charge from stoichiometry, which a real cell can approach and never exceed

The deliberately unlike-quantity comparison is pinned as a warning: the heuristic's
``-dE/n`` diagnostic is 8.5 V while the illustrative electrochemical value is 1.41 V.
That mismatch shows the energy-equivalent proxy must not be used as OCV. It is not a
calibration or falsification test for the oracle's own electronic-energy measurand.

Simplified alkaline Zn/MnO2 example
------------------------------------
    ZnO + H2O + 2 e-      -> Zn + 2 OH-        illustrative E0 = -1.260 V
    2 MnO2 + H2O + 2 e-   -> Mn2O3 + 2 OH-     illustrative E0 = +0.15 V
    cell                                               E0 =  1.41 V
Nominal AA rating is 1.5 V and a fresh cell reads nearer 1.6 V open-circuit; those are
three different quantities and this file does not blur them. The lumped Mn2O3 product is
a textbook idealization, not a complete commercial-AA discharge mechanism; manufacturer
descriptions commonly resolve MnOOH formation. Internal resistance and usable capacity
also vary with construction, state of charge, load, temperature, and cutoff voltage.
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
from smartchem.oracle.base import BaseOracle, Estimate
from smartchem.thermo import reaction_energy

# -- the species ---------------------------------------------------------------------
Zn = Molecule.atom("Zn")
OH = Molecule(("O", "H"), frozenset({Bond(0, 1)}), charge=-1)
H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
ZnO = Molecule(("Zn", "O"), frozenset({Bond(0, 1)}))
MnO2 = Molecule(("Mn", "O", "O"), frozenset({Bond(0, 1), Bond(0, 2)}))
Mn2O3 = Molecule(("Mn", "Mn", "O", "O", "O"),
                 frozenset({Bond(0, 2), Bond(0, 3), Bond(1, 3), Bond(1, 4)}))
E = Molecule.carrier("e-", charge=-1)

#: illustrative electrochemical comparison value; not an oracle target for ``dE``
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

    def test_cell_fields_are_typed_before_inventory_logic_runs(self):
        cell = aa_cell()
        with pytest.raises(TypeError, match="Reaction"):
            Cell("not a reaction", cell.cathode)
        with pytest.raises(TypeError, match="name"):
            Cell(cell.anode, cell.cathode, name=7)

    def test_the_overall_reaction_is_the_chemistry_without_the_electrons(self):
        consumed, produced = aa_cell().net_reaction()
        assert consumed == Config.of(Zn, MnO2, MnO2)
        assert produced == Config.of(ZnO, Mn2O3)
        assert conserves(aa_cell().overall())

    def test_n_is_invisible_in_the_composite_and_present_in_the_factorisation(self):
        """
        The load-bearing structural claim: the closed endpoints erase which carrier
        exchange connected the half-reactions. Physical half-reaction admissibility and
        normalization constrain ``n``; it is not an arbitrary dial. The factorisation is
        where this implementation retains the chosen balanced electron transfer.
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

    def test_electron_count_uses_charge_quanta_not_carrier_objects(self):
        calcium = Molecule.atom("Ca")
        calcium_2 = Molecule.atom("Ca", charge=2)
        pair = Molecule.carrier("electron pair", charge=-2)
        with_pair = Cell(
            Reaction(Config.of(calcium), Config.of(calcium_2, pair)),
            Reaction(Config.of(calcium_2, pair), Config.of(calcium)),
        )
        electron = Molecule.carrier("e-", charge=-1)
        with_two = Cell(
            Reaction(Config.of(calcium), Config.of(calcium_2, electron, electron)),
            Reaction(Config.of(calcium_2, electron, electron), Config.of(calcium)),
        )
        assert with_pair.electrons == with_two.electrons == 2

    def test_positive_holes_are_not_silently_counted_as_electrons(self):
        chlorine = Molecule.atom("Cl")
        chloride = Molecule.atom("Cl", charge=-1)
        hole = Molecule.carrier("h+", charge=1)
        anode = Reaction(Config.of(chlorine), Config.of(chloride, hole))
        cathode = Reaction(Config.of(chloride, hole), Config.of(chlorine))
        with pytest.raises(ValueError, match="positive holes"):
            Cell(anode, cathode)

    def test_equal_charge_with_different_carrier_types_does_not_close(self):
        calcium = Molecule.atom("Ca")
        calcium_2 = Molecule.atom("Ca", charge=2)
        pair = Molecule.carrier("electron pair", charge=-2)
        electron = Molecule.carrier("e-", charge=-1)
        anode = Reaction(Config.of(calcium), Config.of(calcium_2, pair))
        cathode = Reaction(
            Config.of(calcium_2, electron, electron), Config.of(calcium)
        )
        with pytest.raises(ValueError, match="circuit does not close"):
            Cell(anode, cathode)


# ======================================================================================
class TestAnEnergyEquivalentProxyIsNotOCV:
    """
    Pinned as a cross-measurand warning, not hidden as a caveat.

    The heuristic oracle prices ZnO, MnO2 and Mn2O3 through the legacy ligand-field path
    and DECLINES water -- confident on the hard case, silent on the easy one. The result
    is a 1.5 V cell predicted at 8.5 V.

    ``-dE/n`` and electrochemical OCV are different quantities, so their mismatch cannot
    establish an electronic-energy error or coverage failure. It establishes the API
    boundary: a raw energy oracle cannot be validated against, or presented as, OCV.
    """

    def test_the_predicted_voltage_is_wrong_by_more_than_five_fold(self):
        volts = aa_cell().energy_equivalent_voltage(HeuristicOracle())
        assert volts is not None, "the oracle does price these species, wrongly"
        assert volts.value_volts == pytest.approx(8.52, abs=0.02)
        assert volts.value_volts / E0_CELL_VOLTS > 5.0
        assert "not electrochemical OCV" in volts.notes

    def test_scale_comparison_is_reported_without_a_coverage_claim(self):
        """Keep the warning visible without treating it as statistical validation."""
        volts = aa_cell().energy_equivalent_voltage(HeuristicOracle())
        low = volts.value_volts - volts.uncertainty_volts
        assert low > E0_CELL_VOLTS, (
            f"value minus reported scale {low:.2f} V still exceeds {E0_CELL_VOLTS} V")

    def test_the_sign_is_right_even_though_the_magnitude_is_not(self):
        """The cell does at least discharge in the correct direction. Small mercies."""
        assert aa_cell().energy_equivalent_voltage(HeuristicOracle()).value_volts > 0

    def test_a_raw_energy_oracle_is_not_mislabelled_as_ocv(self):
        with pytest.raises(NotImplementedError, match="Gibbs"):
            aa_cell().open_circuit_voltage(HeuristicOracle())


class SystematicOracle(BaseOracle):
    """Deterministic test double with species-keyed sensitivity sources."""

    name = "systematic-test"
    nominal_accuracy_ev = 0.2

    def energy(self, molecule: Molecule) -> Estimate:
        bond_order = sum(bond.order for bond in molecule.bonds)
        return Estimate(
            value_ev=-float(bond_order),
            uncertainty_ev=0.2,
            method=self.name,
            systematic_terms=((f"species:{molecule!r}", 0.1 * (bond_order + 1)),),
        )


class TestVoltageProvenance:
    def test_named_systematic_sources_survive_energy_to_voltage_conversion(self):
        oracle = SystematicOracle()
        delta = reaction_energy(aa_cell().overall(), oracle)
        voltage = aa_cell().energy_equivalent_voltage(oracle)
        expected = {
            source: -coefficient / aa_cell().electrons
            for source, coefficient in delta.systematic_terms
        }
        assert dict(voltage.systematic_terms) == pytest.approx(expected)
        assert voltage.systematic_volts == pytest.approx(sum(expected.values()))
        assert voltage.systematic_magnitude_volts == pytest.approx(
            sum(abs(value) for value in expected.values())
        )


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
        Conservation in the fixed ideal Thevenin model: source power equals load power
        plus internal dissipation. This is an instantaneous circuit identity, not a full
        electrochemical energy balance over a real discharge.
        """
        op = OperatingPoint(E0_CELL_VOLTS, AA_INTERNAL_OHMS, load)
        ideal_source = op.ocv_volts * op.current_amps
        assert ideal_source == pytest.approx(
            op.power_load_watts + op.power_internal_watts, rel=1e-12)

    def test_maximum_power_is_at_the_matched_load_and_splits_source_power(self):
        """
        The counterintuitive consequence worth having a test for: the load that draws the
        most instantaneous power receives half the ideal source power while the other half
        is internally dissipated. This does not say half a real battery's chemical capacity
        is lost over discharge. Maximum power and maximum efficiency are different points.
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

    @pytest.mark.parametrize("args", [
        (1.5, -0.1, 1.0),
        (1.5, 0.1, -1.0),
        (1.5, 0.0, 0.0),
        (float("nan"), 0.1, 1.0),
    ])
    def test_invalid_operating_points_fail_at_construction(self, args):
        with pytest.raises((TypeError, ValueError)):
            OperatingPoint(*args)


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

    def test_capacity_divides_by_limiting_reagent_coefficient(self):
        """Two moles consumed per reaction event support half as many reaction extents."""
        assert theoretical_capacity_coulombs(
            2.0, electrons=4, stoichiometric_coefficient=2
        ) == pytest.approx(theoretical_capacity_coulombs(2.0, electrons=2))

    @pytest.mark.parametrize("coefficient", [0.0, -1.0, float("nan"), True])
    def test_invalid_stoichiometric_coefficient_is_rejected(self, coefficient):
        with pytest.raises((TypeError, ValueError)):
            theoretical_capacity_coulombs(1.0, 2, coefficient)

    def test_the_energy_a_full_discharge_delivers(self):
        """
        Closing the loop: charge x voltage is energy, and it should land near the few
        watt-hours a AA is actually sold as holding.
        """
        moles = AA_ZINC_GRAMS / ZINC_MOLAR_MASS
        joules = theoretical_capacity_coulombs(moles, 2) * E0_CELL_VOLTS
        watt_hours = joules / 3600.0
        assert 4.0 < watt_hours < 5.5, f"got {watt_hours:.2f} Wh"
