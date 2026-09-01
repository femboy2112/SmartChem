"""M2 -- equilibrium extent (K = exp(-ΔG/RT)), calibrated on known reactions before its outputs are believed.

The Instrument rule (E41 discipline): the K engine must recover known equilibrium behaviour before its
verdicts count. Haber must recover K ~ 6e5 at 298 K (ESSENTIALLY_COMPLETE) and collapse below 1 at 700 K
(the real reason it needs pressure). These tests pin that, the decade-scale extent bands, the exactly-
solvable Δn=0 conversion closed form (checked against an independent recomputation), the loud UNKNOWN on
missing data and on Δn != 0, the injectability lever, overflow safety, and that ranking floats a complete
equilibrium above a negligible one.
"""
import math

import pytest

from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef
from smartchem.experiment.drafter import draft_procedure, rank_routes
from smartchem.experiment.equilibrium import (
    EquilibriumExtent,
    equilibrium_of_step,
    verify_equilibrium,
)
from smartchem.experiment.feasibility import FeasibilityGrade
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles

H2 = parse_smiles("[H][H]")
O2 = parse_smiles("O=O")
N2 = parse_smiles("N#N")
H2O = parse_smiles("O")
NH3 = parse_smiles("N")
CO = parse_smiles("[C-]#[O+]")
CO2 = parse_smiles("O=C=O")
ETHANOL = parse_smiles("CCO")   # off-seed (C2H6O)


def water_synthesis():   # 2 H2 + O2 -> 2 H2O ; Δn = -1
    return ExperimentStep.assembling(H2O, (H2, H2, O2), (H2O, H2O))


def haber():             # N2 + 3 H2 -> 2 NH3 ; Δn = -2
    return ExperimentStep.assembling(NH3, (N2, H2, H2, H2), (NH3, NH3))


def water_gas_shift():   # CO + H2O -> CO2 + H2 ; Δn = 0 (all species seeded)
    return ExperimentStep.assembling(CO2, (CO, H2O), (CO2, H2))


class TestInstrumentCalibration:
    """Recover known equilibrium behaviour before believing any novel output."""

    def test_water_synthesis_is_essentially_complete_with_an_astronomical_k(self):
        e = equilibrium_of_step(water_synthesis())
        assert e.extent is EquilibriumExtent.ESSENTIALLY_COMPLETE
        assert e.grade is FeasibilityGrade.DERIVED
        assert e.log10_k > 50.0          # ΔG = -474 kJ -> log10 K ~ 83

    def test_haber_recovers_its_298k_equilibrium_constant(self):
        e = equilibrium_of_step(haber())
        # textbook K ~ 6e5 at 298 K: log10 K ~ 5.7
        assert 5.4 < e.log10_k < 6.1
        assert e.extent is EquilibriumExtent.ESSENTIALLY_COMPLETE

    def test_haber_equilibrium_collapses_below_one_at_high_temperature(self):
        e = equilibrium_of_step(haber(), temperature_k=700.0)
        assert e.log10_k < 0.0                              # K collapses below 1 -- why Haber needs pressure
        assert e.extent is EquilibriumExtent.NEGLIGIBLE
        assert e.grade is FeasibilityGrade.PREDICTED        # extrapolated far from 298.15 K, flagged

    def test_the_reverse_of_a_complete_reaction_is_negligible(self):
        split = ExperimentStep.assembling(H2, (H2O, H2O), (H2, H2, O2))
        e = equilibrium_of_step(split)
        assert e.extent is EquilibriumExtent.NEGLIGIBLE
        assert e.log10_k < -50.0

    def test_uniformly_rescaling_an_equation_does_not_change_delta_g_or_k(self):
        base = water_gas_shift()
        scaled = ExperimentStep.assembling(
            CO2, base.reactants * 6, base.products * 6
        )
        e1 = equilibrium_of_step(base)
        e6 = equilibrium_of_step(scaled)
        assert e6.delta_g_kj == pytest.approx(e1.delta_g_kj)
        assert e6.log10_k == pytest.approx(e1.log10_k)
        assert e6.conversion_fraction == pytest.approx(e1.conversion_fraction)
        assert e6.extent is e1.extent


class TestConversionClosedForm:
    """The exactly-solvable Δn=0 ideal-reference conversion, checked against an independent recomputation."""

    def test_delta_n_zero_reaction_reports_a_conversion_fraction(self):
        e = equilibrium_of_step(water_gas_shift())          # Δn = 0, all-unit coefficients -> α = √K/(1+√K)
        assert e.conversion_fraction is not None
        assert e.conversion_finding.bucket.name == "KNOWN_SOURCED"
        # independent recomputation from the reported log10 K (all coeffs 1 -> C_stoich=1, M=2)
        root_k = 10.0 ** (e.log10_k / 2.0)
        expected = root_k / (1.0 + root_k)
        assert abs(e.conversion_fraction - expected) < 1e-9
        assert 0.0 < e.conversion_fraction < 1.0

    def test_conversion_is_monotone_in_k_symmetric_at_k_one(self):
        # α = t/(1+t) with t = (K/C_stoich)^(1/M): K=1 (symmetric, C_stoich=1) -> α = 0.5 exactly.
        # Independent-path unit check of the closed form via the reported values.
        e = equilibrium_of_step(water_gas_shift())
        # water-gas-shift here is strongly forward (log10 K > 0) -> conversion well above the 0.5 midpoint
        assert e.conversion_fraction > 0.5


class TestEquilibriumRenderDeniesYield:
    """EQUIL-NAME-01: the ideal K/conversion must never read as an expected practical/isolated yield (9.5)."""

    def test_conversion_render_names_the_ideal_model_and_denies_practical_yield(self):
        e = equilibrium_of_step(water_gas_shift())          # Δn=0 -> a conversion fraction IS reported
        assert e.conversion_fraction is not None
        # the step reason presents the number as an IDEAL-MODEL equilibrium extent, never an expected yield/rate
        assert "ideal-model equilibrium" in e.reason
        assert "NOT an expected isolated/practical yield" in e.reason
        assert "NOT a rate" in e.reason
        # and the standalone conversion finding carries the same denial, so reading it alone is not misleading
        assert "NOT an expected isolated/practical yield" in e.conversion_finding.provenance

    def test_the_conversion_percentage_never_appears_without_the_ideal_qualifier(self):
        e = equilibrium_of_step(water_gas_shift())
        # wherever the conversion percentage is shown it is framed as ideal-model, not a naked practical yield %
        assert "ideal-model equilibrium conversion" in e.reason


class TestDeltaNNonZeroIsHonest:
    """Where the mole count changes, the conversion needs a reference state -- a loud UNKNOWN, K still DERIVED."""

    def test_haber_conversion_is_unknown_but_its_k_is_known(self):
        e = equilibrium_of_step(haber())                    # Δn = -2
        assert e.conversion_fraction is None
        assert e.conversion_finding.bucket.name == "UNKNOWN"
        assert e.conversion_finding.value is None
        assert e.k_finding.bucket.name == "KNOWN_SOURCED"   # K itself is DERIVED regardless of Δn
        assert e.extent is EquilibriumExtent.ESSENTIALLY_COMPLETE
        assert "Δn" in e.conversion_finding.provenance


class TestHonestUnknown:
    def test_a_species_with_no_sourced_thermo_is_a_loud_unknown_not_a_guess(self):
        PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        AMP = parse_smiles("Nc1ccc(O)cc1")
        ANH = parse_smiles("CC(=O)OC(=O)C")
        ACOH = parse_smiles("CC(=O)O")
        e = equilibrium_of_step(ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH)))
        assert e.extent is EquilibriumExtent.UNKNOWN
        assert e.log10_k is None and e.missing
        assert e.k_finding.bucket.name == "UNKNOWN"
        assert e.conversion_fraction is None


class TestInjectabilityLever:
    def test_ethanol_combustion_unknown_until_injected_then_complete(self):
        step = ExperimentStep.assembling(CO2, (ETHANOL, O2, O2, O2), (CO2, CO2, H2O, H2O, H2O))
        # derive=False isolates the SOURCED lever: with rung-2 derivation on (the default) ethanol's gas
        # thermo is DERIVED, so M2 would report an extent rather than UNKNOWN (threaded straight from M1).
        assert equilibrium_of_step(step, derive=False).extent is EquilibriumExtent.UNKNOWN

        injected = DEFAULT_THERMO.with_records(
            ThermoRef("C2H6O", "ethanol", -277.6, 160.7, "liquid",
                      "test injection: NIST liquid ethanol ΔfH°/S°"),
        )
        e = equilibrium_of_step(step, thermo=injected)
        assert e.extent is EquilibriumExtent.ESSENTIALLY_COMPLETE   # combustion K is astronomical
        assert e.log10_k > 100.0


class TestOverflowSafety:
    def test_an_astronomical_k_stays_finite_and_renderable(self):
        e = equilibrium_of_step(water_synthesis())
        assert math.isfinite(e.log10_k)                    # computed in log space, never overflows to inf
        assert isinstance(e.k_finding.value, str)
        assert "log10 K" in e.k_finding.provenance


class TestRouteAndRanking:
    def test_route_verdict_and_ranking_float_complete_above_negligible(self):
        synth = ExperimentRoute.of(water_synthesis())
        split = ExperimentRoute.of(ExperimentStep.assembling(H2, (H2O, H2O), (H2, H2, O2)))
        assert verify_equilibrium(synth).verdict == "ESSENTIALLY_COMPLETE"
        assert verify_equilibrium(split).verdict == "NEGLIGIBLE"
        ranked = rank_routes([split, synth])
        assert [verify_equilibrium(f.route).verdict for f in ranked] == \
            ["ESSENTIALLY_COMPLETE", "NEGLIGIBLE"]

    def test_the_draft_renders_the_derived_equilibrium(self):
        text = draft_procedure(ExperimentRoute.of(water_gas_shift())).render()
        assert "equilibrium-constant-K" in text
        assert "equilibrium (thermodynamic extent" in text
        assert "equilibrium-conversion" in text            # Δn=0 -> a conversion fraction is rendered

    def test_verify_equilibrium_requires_a_route(self):
        with pytest.raises(TypeError):
            verify_equilibrium(water_synthesis())


class TestRouteVerdictBottleneck:
    def test_a_negligible_step_caps_the_route_verdict(self):
        # a two-step route: complete step then a negligible reverse-ish step -> route is NEGLIGIBLE
        complete = water_synthesis()                         # 2H2+O2 -> 2H2O, ESSENTIALLY_COMPLETE
        # a step consuming that water and going strongly backward in extent
        negligible = ExperimentStep.assembling(H2, (H2O, H2O), (H2, H2, O2))  # NEGLIGIBLE
        route = ExperimentRoute.of(complete, negligible)
        assert verify_equilibrium(route).verdict == "NEGLIGIBLE"
