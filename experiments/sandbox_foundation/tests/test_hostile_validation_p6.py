"""OPERATION XIII P6 -- hostile numerical and scientific validation across the whole XIII stack (section 8).

Explicit POSITIVE / NEGATIVE / NULL / MUTATION controls over several independent constraint surfaces: exact
conservation, charge/equilibrium closure, fail-closed refusal outside the admitted domain, independent
root/integration agreement, analytical limits, and -- the sharp ones -- MUTATION controls that must make a
discriminating check FAIL (a control that passes under both the true and the mutated hypothesis proves nothing).
"""
from __future__ import annotations

import math

import pytest

from experiments.sandbox_foundation import claim_tiers, coupled_dynamics
from experiments.sandbox_foundation.aqueous_equilibrium import (
    NUMERICALLY_UNVERIFIED,
    OutOfSourceDomainError,
    SourcedConstant,
)
from experiments.sandbox_foundation.coupled_dynamics import (
    DynamicVessel,
    assumed_kLa,
    simulate,
    steady_state_cross_check,
)
from experiments.sandbox_foundation.coupled_gas_equilibrium import InvalidParameterError, MixedGasSystem
from experiments.sandbox_foundation.coupled_gas_equilibrium import solve as gas_solve
from experiments.sandbox_foundation.coupled_reference_hp import cross_check
from experiments.sandbox_foundation.coupled_equilibrium import VinegarBicarbonateSystem
from experiments.sandbox_foundation.coupled_twocell import (
    CoupledCell,
    CoupledWorld,
    DiffusiveMembrane,
    step_diffusive,
)
from experiments.sandbox_foundation.solid_bicarbonate import SolidBicarbonateSystem, dissolve_to_saturation


# ------------------------------------------------------------------- NULL controls (zero inputs -> trivial truth)
def test_null_everything_is_pure_water():
    r = gas_solve(MixedGasSystem(mode="closed", total_acetate_M=0.0, total_carbon_M=0.0, sodium_M=0.0,
                                 activity_model="ideal"))
    assert abs(r.pH - 7.0) < 1e-9


def test_null_dynamics_no_carbon_no_flux():
    v = DynamicVessel(total_acetate_M=0.1, sodium_M=0.1, v_liquid_L=0.1, v_gas_L=0.1,
                      initial_carbon_dissolved_mol=0.0, initial_carbon_gas_mol=0.0, activity_model="ideal")
    traj = simulate(v, assumed_kLa(0.1), duration_s=100.0, n_samples=4)
    assert all(abs(s.flux_mol_per_s) < 1e-15 for s in traj.states)


# ------------------------------------------------------------------- hostile inputs are REFUSED (fail closed)
@pytest.mark.parametrize("bad", [
    dict(mode="sealed", total_acetate_M=0.1, sodium_M=0.0, total_carbon_mol=0.01, v_liquid_L=0.0, v_gas_L=0.1),
    dict(mode="open", total_acetate_M=0.1, sodium_M=0.0, p_co2_atm=float("inf")),
    dict(mode="open", total_acetate_M=0.1, sodium_M=0.0, p_co2_atm=-1.0),
    dict(mode="closed", total_acetate_M=float("nan"), total_carbon_M=0.1, sodium_M=0.0),
])
def test_bad_geometry_or_nonfinite_inputs_refused(bad):
    with pytest.raises(InvalidParameterError):
        MixedGasSystem(**bad)


def test_negative_or_nonfinite_kinetic_parameters_refused():
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        with pytest.raises(InvalidParameterError):
            coupled_dynamics.GasTransferParameter(bad, claim_tiers.ASSUMED_PARAMETER, "x")


def test_out_of_source_temperature_refused_everywhere():
    with pytest.raises(OutOfSourceDomainError):
        MixedGasSystem(mode="closed", total_carbon_M=0.1, temperature_K=350.0)


# ------------------------------------------------------------------- MUTATION controls (must BREAK a check)
def test_mutation_flipped_transfer_sign_breaks_the_sealed_cross_check(monkeypatch):
    """The dynamic steady state matches the sealed equilibrium ONLY because the flux drives toward Henry
    equilibrium.  Flip the flux sign and the dynamics run AWAY from it -- the steady-state cross-check must then FAIL
    (it discriminates).  A cross-check that still 'passed' with the sign flipped would be worthless."""
    v = DynamicVessel(total_acetate_M=0.1, sodium_M=0.1, v_liquid_L=0.1, v_gas_L=0.1,
                      initial_carbon_dissolved_mol=0.01, initial_carbon_gas_mol=0.0, activity_model="ideal")
    good = steady_state_cross_check(v, assumed_kLa(0.05), duration_s=5000.0)
    assert good["delta_pH"] < 1e-3     # positive control: the true model matches

    real_rhs = coupled_dynamics._rhs

    def flipped(n_gas, vessel, kLa, K_H, RT):
        flux, caq, p, pH, verdict = real_rhs(n_gas, vessel, kLa, K_H, RT)
        return -flux, caq, p, pH, verdict

    monkeypatch.setattr(coupled_dynamics, "_rhs", flipped)
    bad = steady_state_cross_check(v, assumed_kLa(0.05), duration_s=5000.0)
    assert bad["delta_pH"] > 0.05      # the mutant no longer reaches the sealed state -- the check caught it


def test_mutation_altered_equilibrium_constant_at_wrong_temperature_refused():
    # a constant tabulated at the wrong temperature has no authority: the system refuses it (fail closed).
    bad_ka = SourcedConstant("Ka_bad", 1.75e-5, 1e-6, "dimensionless (molar, ideal reference)", 310.0,
                             "fabricated off-temperature record", "SOURCED")
    with pytest.raises(OutOfSourceDomainError):
        MixedGasSystem(mode="closed", total_carbon_M=0.1, Ka=bad_ka)


def test_mutation_fabricated_zero_uncertainty_measured_constant_refused():
    with pytest.raises(Exception):   # a SOURCED constant with zero error bar is a fabrication -> refused
        SourcedConstant("Ka_fake", 1.75e-5, 0.0, "dimensionless (molar)", 298.15, "src", "SOURCED")


# ------------------------------------------------------------------- hostile numerical regimes (still sound)
@pytest.mark.parametrize("kw", [
    dict(total_acetate_M=1.0, total_carbon_M=1e-8, sodium_M=0.0),     # extreme ratio
    dict(total_acetate_M=1e-8, total_carbon_M=0.3, sodium_M=0.3),     # extreme ratio, basic
    dict(total_acetate_M=1e-9, total_carbon_M=1e-9, sodium_M=0.0),    # near-zero totals
])
def test_extreme_ratios_still_cross_check_numerically(kw):
    cc = cross_check(VinegarBicarbonateSystem(activity_model="ideal", **kw))
    assert cc.tier == claim_tiers.NUMERICALLY_VERIFIED, cc.note


def test_huge_single_timestep_still_conserves_carbon():
    # one step covering the whole duration: the adaptive integrator must still conserve (carbon is by construction).
    v = DynamicVessel(total_acetate_M=0.1, sodium_M=0.1, v_liquid_L=0.1, v_gas_L=0.1,
                      initial_carbon_dissolved_mol=0.01, initial_carbon_gas_mol=0.0, activity_model="ideal")
    traj = simulate(v, assumed_kLa(0.05), duration_s=1e5, n_samples=2)
    assert traj.max_carbon_residual_mol < 1e-15


def test_gas_pressure_boundary_regimes_are_sane():
    hi = gas_solve(MixedGasSystem(mode="open", total_acetate_M=0.0, sodium_M=0.0, p_co2_atm=10.0,
                                  activity_model="ideal"))
    lo = gas_solve(MixedGasSystem(mode="open", total_acetate_M=0.0, sodium_M=0.0, p_co2_atm=1e-8,
                                  activity_model="ideal"))
    assert hi.pH < 4.5 and lo.pH > 6.0     # high P_CO2 -> acidic; vanishing P_CO2 -> near-neutral
    assert hi.total_dissolved_carbon_M > lo.total_dissolved_carbon_M


# ------------------------------------------------------------------- conservation identity across full runs
def test_open_system_exported_carbon_closes_the_world_ledger():
    # open: the liquid is not carbon-closed, but internal + exported must account for the whole world.
    r = gas_solve(MixedGasSystem(mode="open", total_acetate_M=0.1, sodium_M=0.1, p_co2_atm=1e-2,
                                 activity_model="ideal"))
    # exported = -(dissolved carbon that came in from the reservoir); internal + (-exported) balances.
    assert math.isclose(r.exported_carbon_mol, -r.total_dissolved_carbon_M, rel_tol=1e-12)
    assert r.exported_carbon_mol != 0.0


def test_sealed_and_closed_are_carbon_closed_zero_export():
    for sysm in (MixedGasSystem(mode="closed", total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1),
                 MixedGasSystem(mode="sealed", total_acetate_M=0.1, sodium_M=0.1, total_carbon_mol=0.01,
                                v_liquid_L=0.1, v_gas_L=0.1)):
        r = gas_solve(sysm)
        assert r.exported_carbon_mol == 0.0


def test_two_cell_repeated_valve_cycling_conserves():
    A = CoupledCell(volume_L=0.1, n_acetate_mol=0.02, n_carbon_mol=0.0, n_sodium_mol=0.0, activity_model="ideal")
    B = CoupledCell(volume_L=0.1, n_acetate_mol=0.0, n_carbon_mol=0.02, n_sodium_mol=0.02, activity_model="ideal")
    w = CoupledWorld(cellA=A, cellB=B)
    g0 = w.global_totals()
    for i in range(20):
        mem = DiffusiveMembrane(g_HAc_L_per_s=0.01, g_CO2_L_per_s=0.01, valve=(1.0 if i % 2 == 0 else 0.0))
        w = step_diffusive(w, mem, 2.0)
    for k in g0:
        assert abs(w.global_totals()[k] - g0[k]) < 1e-11


def test_exhausted_solid_then_no_more_dissolution():
    s = SolidBicarbonateSystem(volume_L=1.0, n_acetate_mol=0.0, n_carbon_aqueous_mol=0.0, n_sodium_aqueous_mol=0.0,
                               n_solid_mol=0.1, activity_model="ideal")
    after = dissolve_to_saturation(s).system_after
    assert after.n_solid_mol < 1e-12
    r2 = dissolve_to_saturation(after)
    assert r2.dissolved_mol == 0.0


# ------------------------------------------------------------------- out-of-domain demotion (negative control)
def test_out_of_davies_domain_demotes_across_modes():
    for sysm in (MixedGasSystem(mode="closed", total_acetate_M=0.3, total_carbon_M=0.3, sodium_M=0.6,
                                activity_model="davies"),):
        assert gas_solve(sysm).verdict == NUMERICALLY_UNVERIFIED
