"""Wave VI-A -- the coupled vinegar / bicarbonate 0-D equilibrium.

Pins the scientific checks: two independent routes agree; carbon / acetate / charge conserve; and -- the
load-bearing free validation -- the LIMITING cases reduce EXACTLY to the already-PHREEQC-benchmarked parent
solvers (vinegar-only == acetate solver; bicarbonate-only == carbonate closed solver). The mixed system is the
genuinely new object; its numerical soundness (route agreement + conservation) is checked here, while an
independent MIXED PHREEQC benchmark remains the documented next step (PHREEQC is an optional dependency).
"""
from __future__ import annotations

import math

import pytest

from experiments.sandbox_foundation.aqueous_equilibrium import AcetateWaterSystem
from experiments.sandbox_foundation.aqueous_equilibrium import solve as acetate_solve
from experiments.sandbox_foundation.carbonate_equilibrium import CarbonateWaterSystem
from experiments.sandbox_foundation.carbonate_equilibrium import solve as carbonate_solve
from experiments.sandbox_foundation.coupled_equilibrium import (
    NUMERICALLY_UNVERIFIED,
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    SOLVED_WITHIN_IDEAL_MODEL,
    VinegarBicarbonateSystem,
    solve,
)
from experiments.sandbox_foundation.twocell import InvalidParameterError


def test_water_only_is_neutral():
    r = solve(VinegarBicarbonateSystem(activity_model="ideal"))
    assert abs(r.pH - 7.0) < 1e-6
    assert r.verdict == SOLVED_WITHIN_IDEAL_MODEL


def test_two_routes_agree_and_everything_conserves_on_the_mixed_system():
    r = solve(VinegarBicarbonateSystem(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1, activity_model="davies"))
    assert r.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL
    assert r.solver_agreement_residual < 1e-9 * r.h_plus_M   # the brentq and polynomial routes agree on [H+]
    assert r.charge_balance_residual < 1e-9
    assert r.carbon_conservation_residual < 1e-9
    assert r.acetate_conservation_residual < 1e-9
    for v in (r.hac_M, r.ac_minus_M, r.co2aq_M, r.hco3_M, r.co3_M, r.oh_minus_M):
        assert v >= -1e-12


def test_carbon_mass_balance_sums_to_total():
    r = solve(VinegarBicarbonateSystem(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1, activity_model="davies"))
    assert math.isclose(r.co2aq_M + r.hco3_M + r.co3_M, 0.1, rel_tol=1e-9)
    assert math.isclose(r.hac_M + r.ac_minus_M, 0.1, rel_tol=1e-9)


@pytest.mark.parametrize("C_Ac", [0.01, 0.1, 0.25])
def test_vinegar_only_reduces_exactly_to_the_acetate_parent(C_Ac):
    coupled = solve(VinegarBicarbonateSystem(total_acetate_M=C_Ac, total_carbon_M=0.0, sodium_M=0.0, activity_model="davies"))
    parent = acetate_solve(AcetateWaterSystem(total_acetic_M=C_Ac, sodium_M=0.0, activity_model="davies"))
    assert abs(coupled.pH - parent.pH) < 1e-9, f"C_Ac={C_Ac}: coupled {coupled.pH} vs acetate parent {parent.pH}"
    assert abs(coupled.ac_minus_M - parent.ac_minus_M) < 1e-12


@pytest.mark.parametrize("C_C,Na", [(0.05, 0.05), (0.1, 0.1), (0.1, 0.2)])
def test_bicarbonate_only_reduces_exactly_to_the_carbonate_closed_parent(C_C, Na):
    coupled = solve(VinegarBicarbonateSystem(total_acetate_M=0.0, total_carbon_M=C_C, sodium_M=Na, activity_model="davies"))
    parent = carbonate_solve(CarbonateWaterSystem(mode="closed", total_carbon_M=C_C, sodium_M=Na, activity_model="davies"))
    assert abs(coupled.pH - parent.pH) < 1e-9, f"C_C={C_C},Na={Na}: coupled {coupled.pH} vs carbonate parent {parent.pH}"
    assert abs(coupled.hco3_M - parent.hco3_M) < 1e-12
    assert abs(coupled.co3_M - parent.co3_M) < 1e-12


def test_more_acid_lowers_the_mixed_ph_monotonically():
    # a preregistered ordering control: at fixed carbonate + sodium, adding acetic acid can only lower the pH.
    phs = [
        solve(VinegarBicarbonateSystem(total_acetate_M=a, total_carbon_M=0.1, sodium_M=0.1, activity_model="davies")).pH
        for a in (0.0, 0.05, 0.1, 0.2)
    ]
    assert phs == sorted(phs, reverse=True), f"pH must fall as acid rises: {phs}"


def test_the_mixed_vinegar_baking_soda_ph_is_mildly_acidic():
    # 0.1 M acetic acid + 0.1 M NaHCO3 (the volcano, closed): the proton balance lands in the mildly-acidic
    # region between the vinegar-only (~2.9) and bicarbonate-only (~8.1) end states.
    r = solve(VinegarBicarbonateSystem(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1, activity_model="davies"))
    assert 4.0 < r.pH < 7.0


def test_davies_domain_refusal_is_fail_closed():
    # far past the Davies domain (I >> 0.5 M), the result must be flagged NUMERICALLY_UNVERIFIED, never a quietly
    # extrapolated activity pH.
    r = solve(VinegarBicarbonateSystem(total_acetate_M=0.0, total_carbon_M=0.0, sodium_M=5.0, activity_model="davies"))
    assert r.verdict == NUMERICALLY_UNVERIFIED


@pytest.mark.parametrize("bad", [{"total_acetate_M": -0.1}, {"total_carbon_M": -1.0}, {"sodium_M": -0.01},
                                 {"activity_model": "pitzer"}])
def test_invalid_inputs_are_refused(bad):
    with pytest.raises(InvalidParameterError):
        VinegarBicarbonateSystem(**bad)
