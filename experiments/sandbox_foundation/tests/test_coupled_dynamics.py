"""OPERATION XIII P2 -- time-resolved CO2 gas transfer coupled to acid-base equilibrium (section 4 test list).

Load-bearing pins:
  * a supersaturated liquid DEGASSES (n_gas up, pH up, flux -> 0); a CO2-rich headspace over carbon-poor liquid
    ABSORBS (n_gas down, pH down) -- the source of gas is the dissolved carbon and the SIGN is set by the driving
    force, never a trigger (no hard-coded fizz);
  * total carbon is conserved across liquid+gas at every step (machine-zero residual);
  * the dynamic steady state EQUALS the static sealed equilibrium (the fixed-point cross-check of P1 and P2);
  * an independent fixed-step integrator agrees with RK45 and the solution converges under timestep refinement;
  * the trajectory's claim tier is weakest(equilibrium tier, kLa tier) -- a Level-A run is capped ASSUMED_PARAMETER;
  * no fake kinetic constant: kLa must be supplied with a tier + provenance, and the Level-B band is an
    order-of-magnitude placeholder (CALIBRATION_REQUIRED), not a measured datum; Level C is not fabricated.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.aqueous_equilibrium import InvalidParameterError
from experiments.sandbox_foundation.coupled_dynamics import (
    LITERATURE_KLA_BAND,
    DynamicVessel,
    GasTransferParameter,
    assumed_kLa,
    integrate_fixed_step,
    simulate,
    steady_state_cross_check,
)

# a supersaturated liquid (0.1 M dissolved carbon) over an empty headspace -- it must degas
_SUPERSAT = DynamicVessel(total_acetate_M=0.1, sodium_M=0.1, v_liquid_L=0.1, v_gas_L=0.1,
                          initial_carbon_dissolved_mol=0.01, initial_carbon_gas_mol=0.0, activity_model="ideal")
_KLA = assumed_kLa(0.05)


def test_supersaturated_liquid_degasses_and_relaxes():
    traj = simulate(_SUPERSAT, _KLA, duration_s=3000.0, n_samples=12)
    first, last = traj.states[0], traj.states[-1]
    assert last.n_carbon_gas_mol > first.n_carbon_gas_mol    # CO2 leaves the liquid
    assert last.pH > first.pH                                # losing carbonic acid raises pH
    assert abs(last.flux_mol_per_s) < 1e-7                   # relaxes toward equilibrium (flux -> 0)
    assert first.flux_mol_per_s > 0                          # initially supersaturated: liquid -> gas


def test_co2_rich_headspace_absorbs_into_carbon_poor_liquid():
    v = DynamicVessel(total_acetate_M=0.1, sodium_M=0.1, v_liquid_L=0.1, v_gas_L=0.1,
                      initial_carbon_dissolved_mol=0.0, initial_carbon_gas_mol=0.01, activity_model="ideal")
    traj = simulate(v, _KLA, duration_s=3000.0, n_samples=8)
    first, last = traj.states[0], traj.states[-1]
    assert last.n_carbon_gas_mol < first.n_carbon_gas_mol    # CO2 dissolves
    assert last.pH < first.pH                                # gaining carbonic acid lowers pH
    assert first.flux_mol_per_s < 0                          # undersaturated liquid: gas -> liquid


def test_total_carbon_is_conserved_at_every_step():
    traj = simulate(_SUPERSAT, _KLA, duration_s=3000.0, n_samples=20)
    assert traj.max_carbon_residual_mol < 1e-15
    for s in traj.states:
        assert abs((s.n_carbon_liquid_mol + s.n_carbon_gas_mol) - s.n_carbon_total_mol) < 1e-15
        assert -1e-15 <= s.n_carbon_gas_mol <= s.n_carbon_total_mol + 1e-15   # positivity / inventory bound


def test_dynamic_steady_state_equals_the_sealed_equilibrium():
    cc = steady_state_cross_check(_SUPERSAT, _KLA, duration_s=6000.0)
    assert cc["delta_pH"] < 1e-3
    assert cc["delta_n_gas"] < 1e-6 * _SUPERSAT.n_carbon_total_mol + 1e-9
    assert abs(cc["residual_flux"]) < 1e-7


def test_independent_integrator_agrees_with_rk45():
    traj = simulate(_SUPERSAT, _KLA, duration_s=3000.0, n_samples=3)
    rk45_end = traj.states[-1].n_carbon_gas_mol
    be = integrate_fixed_step(_SUPERSAT, _KLA, duration_s=3000.0, dt=5.0, method="backward_euler")[-1][1]
    rk4 = integrate_fixed_step(_SUPERSAT, _KLA, duration_s=3000.0, dt=1.0, method="rk4")[-1][1]
    n_tot = _SUPERSAT.n_carbon_total_mol
    assert abs(be - rk45_end) < 1e-4 * n_tot
    assert abs(rk4 - rk45_end) < 1e-4 * n_tot


def test_timestep_refinement_converges():
    # a faster kLa so an explicit coarse step has visible truncation error to converge away.
    fast = assumed_kLa(0.5)
    ref = simulate(_SUPERSAT, fast, duration_s=200.0, n_samples=3, rtol=1e-11, atol=1e-18).states[-1].n_carbon_gas_mol
    errs = [abs(integrate_fixed_step(_SUPERSAT, fast, duration_s=200.0, dt=d, method="rk4")[-1][1] - ref)
            for d in (8.0, 4.0, 2.0)]
    assert errs[0] > errs[1] > errs[2]                       # error shrinks monotonically with dt
    assert errs[2] < 1e-3 * _SUPERSAT.n_carbon_total_mol     # and is small at the finest step


def test_no_gas_source_when_carbon_is_absent():
    v = DynamicVessel(total_acetate_M=0.1, sodium_M=0.1, v_liquid_L=0.1, v_gas_L=0.1,
                      initial_carbon_dissolved_mol=0.0, initial_carbon_gas_mol=0.0, activity_model="ideal")
    traj = simulate(v, _KLA, duration_s=1000.0, n_samples=5)
    for s in traj.states:
        assert abs(s.flux_mol_per_s) < 1e-15
        assert abs(s.n_carbon_gas_mol) < 1e-15


def test_claim_tier_is_the_weakest_premise():
    traj = simulate(_SUPERSAT, _KLA, duration_s=100.0, n_samples=3)
    # equilibrium solve is NUMERICALLY_VERIFIED; the Level-A kLa is ASSUMED_PARAMETER -> the weakest caps it.
    assert traj.claim_tier == claim_tiers.ASSUMED_PARAMETER
    assert any("CALIBRATION_REQUIRED" in c or "assumed" in c.lower() for c in traj.caveats)


def test_gas_transfer_parameter_demands_a_positive_kLa_and_provenance():
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        with pytest.raises(InvalidParameterError):
            GasTransferParameter(bad, claim_tiers.ASSUMED_PARAMETER, "x")
    with pytest.raises(InvalidParameterError):
        GasTransferParameter(0.01, claim_tiers.ASSUMED_PARAMETER, "   ")   # empty source
    with pytest.raises(claim_tiers.InvalidClaimTierError):
        GasTransferParameter(0.01, "PRETTY_SURE", "x")                     # bogus tier


def test_level_B_band_is_an_honest_placeholder_not_a_measured_constant():
    assert LITERATURE_KLA_BAND.tier == claim_tiers.ASSUMED_PARAMETER
    assert "CALIBRATION_REQUIRED" in LITERATURE_KLA_BAND.source
    assert "band" in LITERATURE_KLA_BAND.applicability.lower()


def test_level_A_helper_is_assumed_parameter():
    p = assumed_kLa(0.02)
    assert p.tier == claim_tiers.ASSUMED_PARAMETER
    assert p.kLa_per_s == 0.02
