"""M1 -- thermodynamic feasibility (ΔG), calibrated on known reactions before its novel outputs are believed.

The Instrument rule (E41 discipline): the ΔG engine must recover textbook values on reactions whose answer
is KNOWN before any of its verdicts count. 2H2+O2->2H2O(l) must recover ΔG°=-474 kJ; Haber must recover
-33 kJ at 298 K and flip sign near ~465 K. These tests pin that, the DERIVED/PREDICTED grading, the loud
UNKNOWN on missing data, the injectability lever, and that ranking floats favorable above endergonic.
"""
import pytest

from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef, ThermoTable
from smartchem.experiment.drafter import draft_procedure, rank_routes
from smartchem.experiment.feasibility import (
    FeasibilityDirection,
    FeasibilityGrade,
    feasibility_of_step,
    verify_feasibility,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles

H2 = parse_smiles("[H][H]")
O2 = parse_smiles("O=O")
N2 = parse_smiles("N#N")
H2O = parse_smiles("O")
NH3 = parse_smiles("N")
ETHANOL = parse_smiles("CCO")   # off-seed (C2H6O)
CO2 = parse_smiles("O=C=O")


def water_synthesis():   # 2 H2 + O2 -> 2 H2O
    return ExperimentStep.assembling(H2O, (H2, H2, O2), (H2O, H2O))


def haber():             # N2 + 3 H2 -> 2 NH3
    return ExperimentStep.assembling(NH3, (N2, H2, H2, H2), (NH3, NH3))


class TestInstrumentCalibration:
    """Recover known ΔG values before believing any novel output."""

    def test_water_synthesis_recovers_the_textbook_delta_g(self):
        f = feasibility_of_step(water_synthesis())
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert f.grade is FeasibilityGrade.DERIVED
        assert abs(f.delta_g_kj - (-474.3)) < 1.0   # textbook ΔG° = -474.26 kJ
        assert f.finding.bucket.name == "KNOWN_SOURCED"

    def test_haber_recovers_its_298k_value_and_is_favorable(self):
        f = feasibility_of_step(haber())
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert abs(f.delta_g_kj - (-32.8)) < 1.0    # textbook ΔG° = -32.9 kJ

    def test_haber_flips_unfavorable_at_high_temperature_and_is_flagged_predicted(self):
        f = feasibility_of_step(haber(), temperature_k=700.0)
        assert f.direction is FeasibilityDirection.UNFAVORABLE   # entropy penalty wins at high T
        assert f.grade is FeasibilityGrade.PREDICTED             # extrapolated far from 298.15 K, flagged

    def test_the_reverse_reaction_is_unfavorable(self):
        split = ExperimentStep.assembling(H2, (H2O, H2O), (H2, H2, O2))
        f = feasibility_of_step(split)
        assert f.direction is FeasibilityDirection.UNFAVORABLE
        assert abs(f.delta_g_kj - 474.3) < 1.0


class TestHonestUnknown:
    def test_a_species_with_no_sourced_thermo_is_a_loud_unknown_not_a_guess(self):
        # paracetamol synthesis: none of these are in the thermo seed
        PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        AMP = parse_smiles("Nc1ccc(O)cc1")
        ANH = parse_smiles("CC(=O)OC(=O)C")
        ACOH = parse_smiles("CC(=O)O")
        f = feasibility_of_step(ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH)))
        assert f.direction is FeasibilityDirection.UNKNOWN
        assert f.delta_g_kj is None and f.missing
        assert f.finding.bucket.name == "UNKNOWN"


class TestInjectabilityLever:
    """Off-seed until the chemist injects sourced data, then DERIVED -- the universality lever."""

    def test_ethanol_combustion_unknown_until_injected_then_favorable(self):
        # C2H6O + 3 O2 -> 2 CO2 + 3 H2O ; ethanol is off-seed
        step = ExperimentStep.assembling(
            CO2, (ETHANOL, O2, O2, O2), (CO2, CO2, H2O, H2O, H2O)
        )
        assert feasibility_of_step(step).direction is FeasibilityDirection.UNKNOWN

        injected = DEFAULT_THERMO.with_records(
            ThermoRef("C2H6O", "ethanol", -277.6, 160.7, "liquid",
                      "test injection: NIST liquid ethanol ΔfH°/S°"),
        )
        f = feasibility_of_step(step, thermo=injected)
        assert f.direction is FeasibilityDirection.FAVORABLE   # combustion is strongly exergonic
        assert f.delta_g_kj < -1000.0


class TestRouteAndRanking:
    def test_route_verdict_and_ranking_float_favorable_above_unfavorable(self):
        synth = ExperimentRoute.of(water_synthesis())
        split = ExperimentRoute.of(ExperimentStep.assembling(H2, (H2O, H2O), (H2, H2, O2)))
        assert verify_feasibility(synth).verdict == "FAVORABLE"
        assert verify_feasibility(split).verdict == "UNFAVORABLE"
        ranked = rank_routes([split, synth])
        assert [verify_feasibility(f.route).verdict for f in ranked] == ["FAVORABLE", "UNFAVORABLE"]

    def test_the_draft_renders_the_derived_delta_g(self):
        text = draft_procedure(ExperimentRoute.of(water_synthesis())).render()
        assert "delta-G-rxn" in text
        assert "feasibility (thermodynamic" in text
        assert "FAVORABLE" in text

    def test_verify_feasibility_requires_a_route(self):
        with pytest.raises(TypeError):
            verify_feasibility(water_synthesis())


class TestSourcedDataDiscipline:
    def test_a_thermo_record_rejects_a_negative_entropy(self):
        with pytest.raises(ValueError):
            ThermoRef("X", "x", 0.0, -1.0, "gas", "bad")   # S° >= 0 by the third law

    def test_a_thermo_record_requires_a_provenance(self):
        with pytest.raises(ValueError):
            ThermoRef("X", "x", 0.0, 1.0, "gas", "")

    def test_for_formula_refuses_an_ambiguous_formula(self):
        t = ThermoTable((
            ThermoRef("C2H6O", "ethanol", -277.6, 160.7, "liquid", "a"),
            ThermoRef("C2H6O", "dimethyl ether", -184.1, 266.4, "gas", "b"),
        ))
        assert t.for_formula("C2H6O") is None          # two isomers -> ambiguous, a loud None
        assert t.for_named("C2H6O", "ethanol") is not None
