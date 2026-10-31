"""OPERATION XIII P0 -- the arbitrary-precision holdout that independently verifies the coupled mixed-interior solve.

The load-bearing pins:
  * the 60-digit Decimal bisection holdout agrees with the production float64 two-route solve across the mixed
    INTERIOR (the object with no PHREEQC column and no limiting-case free check) -> NUMERICALLY_VERIFIED;
  * it holds through the §2C hostile numerical-conditioning regimes (tiny [H+] strongly basic, widely separated
    totals, near-zero totals) where a float64 cancellation SHARED by both production routes would hide -- the
    holdout's independent precision is exactly what would expose it;
  * the holdout is an independent-ALGORITHM, independent-PRECISION witness of the SOLVE, not of the chemistry:
    agreement earns NUMERICALLY_VERIFIED and explicitly NOT BENCHMARKED_AGAINST_REFERENCE_SOLVER.
"""
from __future__ import annotations

import math

import pytest

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.coupled_equilibrium import VinegarBicarbonateSystem, solve
from experiments.sandbox_foundation.coupled_reference_hp import (
    CROSS_CHECK_H_RTOL,
    CROSS_CHECK_PH_ATOL,
    cross_check,
    solve_hp,
)

# the mixed INTERIOR grid: neither parent limit (both C_Ac>0 and C_C>0), spanning acid/bicarbonate excess and both
# activity models.  These are the cases §2 says need an independent interior check.
_MIXED_INTERIOR = [
    dict(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1, activity_model="davies"),
    dict(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1, activity_model="ideal"),
    dict(total_acetate_M=0.2, total_carbon_M=0.05, sodium_M=0.05, activity_model="davies"),  # bicarbonate-limited
    dict(total_acetate_M=0.05, total_carbon_M=0.2, sodium_M=0.2, activity_model="davies"),   # acid-limited
    dict(total_acetate_M=0.01, total_carbon_M=0.01, sodium_M=0.005, activity_model="ideal"),
    dict(total_acetate_M=0.3, total_carbon_M=0.1, sodium_M=0.15, activity_model="davies"),
]


@pytest.mark.parametrize("kw", _MIXED_INTERIOR)
def test_production_agrees_with_high_precision_holdout_across_the_mixed_interior(kw):
    cc = cross_check(VinegarBicarbonateSystem(**kw))
    assert cc.tier == claim_tiers.NUMERICALLY_VERIFIED, cc.note
    assert cc.delta_pH <= CROSS_CHECK_PH_ATOL
    assert cc.rel_delta_h <= CROSS_CHECK_H_RTOL


# §2C hostile numerical conditioning: these are the regimes where a float64 cancellation shared by production's two
# routes would be invisible to their mutual agreement, and only an independent-precision witness exposes it.
_CONDITIONING = [
    dict(total_acetate_M=1e-6, total_carbon_M=0.1, sodium_M=0.1, activity_model="ideal"),    # widely separated totals
    dict(total_acetate_M=0.1, total_carbon_M=1e-6, sodium_M=0.0, activity_model="ideal"),    # widely separated totals
    dict(total_acetate_M=0.0, total_carbon_M=0.1, sodium_M=0.2, activity_model="ideal"),     # strongly basic (tiny h)
    dict(total_acetate_M=1e-7, total_carbon_M=1e-7, sodium_M=0.0, activity_model="ideal"),   # near-zero totals
    dict(total_acetate_M=0.0, total_carbon_M=0.0, sodium_M=0.0, activity_model="ideal"),     # pure water
]


@pytest.mark.parametrize("kw", _CONDITIONING)
def test_holdout_agrees_in_the_hostile_conditioning_regimes(kw):
    cc = cross_check(VinegarBicarbonateSystem(**kw))
    assert cc.tier == claim_tiers.NUMERICALLY_VERIFIED, cc.note


def test_pure_water_ideal_is_exactly_pH_7_in_the_holdout():
    hp = solve_hp(VinegarBicarbonateSystem(activity_model="ideal"))
    assert abs(hp.pH - 7.0) < 1e-12
    assert abs(hp.h_plus_M - 1e-7) < 1e-18


def test_holdout_conserves_and_closes_charge_in_decimal():
    s = VinegarBicarbonateSystem(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1, activity_model="davies")
    hp = solve_hp(s)
    # carbon, acetate, charge all close on the Decimal re-derivation reported back as float
    assert abs((hp.co2aq_M + hp.hco3_M + hp.co3_M) - 0.1) < 1e-12
    assert abs((hp.hac_M + hp.ac_minus_M) - 0.1) < 1e-12
    assert hp.charge_balance_residual < 1e-12
    assert all(c >= -1e-18 for c in (hp.hac_M, hp.ac_minus_M, hp.co2aq_M, hp.hco3_M, hp.co3_M, hp.oh_minus_M))


def test_holdout_matches_production_speciation_not_just_pH():
    s = VinegarBicarbonateSystem(total_acetate_M=0.2, total_carbon_M=0.05, sodium_M=0.05, activity_model="davies")
    p, hp = solve(s), solve_hp(s)
    for pv, hv in ((p.ac_minus_M, hp.ac_minus_M), (p.hco3_M, hp.hco3_M), (p.co3_M, hp.co3_M),
                   (p.co2aq_M, hp.co2aq_M), (p.oh_minus_M, hp.oh_minus_M)):
        assert math.isclose(pv, hv, rel_tol=1e-8, abs_tol=1e-15), (pv, hv)


def test_cross_check_is_honest_about_what_it_does_not_establish():
    # the tier the holdout can award tops out at NUMERICALLY_VERIFIED -- it must never claim reference-solver
    # benchmarking or measurement calibration (common-mode on the shared chemistry).
    cc = cross_check(VinegarBicarbonateSystem(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1))
    assert cc.tier == claim_tiers.NUMERICALLY_VERIFIED
    assert not claim_tiers.is_at_least(cc.tier, claim_tiers.BENCHMARKED_AGAINST_REFERENCE_SOLVER)
    assert "NOT" in cc.note and ("benchmark" in cc.note.lower() or "reference" in cc.note.lower())
