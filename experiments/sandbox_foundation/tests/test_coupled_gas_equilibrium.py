"""OPERATION XIII P1 -- the coupled vinegar/bicarbonate system in three gas-boundary modes (section 3 test list).

Load-bearing pins:
  * mode='closed' reproduces the already-verified coupled_equilibrium.solve EXACTLY (no fork, no drift);
  * mode='open' on pure water to atmospheric CO2 hits the textbook pH ~ 5.6 anchor;
  * open vs sealed give DIFFERENT end states for identical contents (B6: the partition is real, not a cartoon);
  * carbon conserves across liquid+gas in closed/sealed; the OPEN boundary's exported carbon appears in the ledger
    (never "carbon-conserving" while carbon escaped);
  * nonnegative inventories, pressure units, vanishing/large headspace limits, no gas when carbon is absent, and a
    fail-closed demotion outside the Davies domain.
"""
from __future__ import annotations

import math

import pytest

from experiments.sandbox_foundation.aqueous_equilibrium import (
    NUMERICALLY_UNVERIFIED,
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    SOLVED_WITHIN_IDEAL_MODEL,
)
from experiments.sandbox_foundation.coupled_equilibrium import VinegarBicarbonateSystem
from experiments.sandbox_foundation.coupled_equilibrium import solve as coupled_closed_solve
from experiments.sandbox_foundation.coupled_gas_equilibrium import (
    InvalidParameterError,
    MixedGasSystem,
    solve,
)

_P_ATM = 10 ** -3.5   # atmospheric CO2 partial pressure (~316 ppm)


# ---------------------------------------------------------------------------------- closed consistency
@pytest.mark.parametrize("kw", [
    dict(total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1, activity_model="davies"),
    dict(total_acetate_M=0.2, total_carbon_M=0.05, sodium_M=0.05, activity_model="davies"),
    dict(total_acetate_M=0.0, total_carbon_M=0.1, sodium_M=0.1, activity_model="ideal"),
    dict(total_acetate_M=0.05, total_carbon_M=0.2, sodium_M=0.2, activity_model="davies"),
])
def test_closed_mode_reproduces_the_coupled_closed_solver_exactly(kw):
    a = coupled_closed_solve(VinegarBicarbonateSystem(**kw))
    b = solve(MixedGasSystem(mode="closed", **kw))
    assert abs(a.pH - b.pH) < 1e-10
    assert abs(a.ac_minus_M - b.ac_minus_M) < 1e-12
    assert abs(a.hco3_M - b.hco3_M) < 1e-12


# ---------------------------------------------------------------------------------- open mode
def test_open_pure_water_to_atmosphere_is_pH_5p6():
    r = solve(MixedGasSystem(mode="open", p_co2_atm=_P_ATM, activity_model="ideal"))
    assert 5.5 < r.pH < 5.7
    assert r.verdict == SOLVED_WITHIN_IDEAL_MODEL
    assert r.total_dissolved_carbon_M > 0   # carbon absorbed from the reservoir


def test_open_boundary_records_exported_carbon_in_the_ledger():
    # the open reservoir supplies/absorbs carbon; that crossing MUST appear in the external ledger, so the whole
    # world is accounted even though the liquid alone is not carbon-closed.
    r = solve(MixedGasSystem(mode="open", p_co2_atm=_P_ATM, activity_model="ideal"))
    assert r.exported_carbon_mol != 0.0
    # it equals -(dissolved carbon): carbon came IN from the reservoir (negative export) to reach C_C.
    assert math.isclose(r.exported_carbon_mol, -r.total_dissolved_carbon_M, rel_tol=1e-12)
    # closed/sealed are carbon-closed: zero export.
    closed = solve(MixedGasSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.1))
    assert closed.exported_carbon_mol == 0.0


def test_open_higher_pco2_lowers_pH_and_raises_dissolved_carbon():
    lo = solve(MixedGasSystem(mode="open", p_co2_atm=1e-4, activity_model="ideal"))
    hi = solve(MixedGasSystem(mode="open", p_co2_atm=1e-1, activity_model="ideal"))
    assert hi.pH < lo.pH
    assert hi.total_dissolved_carbon_M > lo.total_dissolved_carbon_M


# ---------------------------------------------------------------------------------- open vs sealed (B6)
def test_open_and_sealed_give_different_end_states():
    contents = dict(total_acetate_M=0.1, sodium_M=0.1, activity_model="davies")
    op = solve(MixedGasSystem(mode="open", p_co2_atm=_P_ATM, **contents))
    se = solve(MixedGasSystem(mode="sealed", total_carbon_mol=0.01, v_liquid_L=0.1, v_gas_L=0.1, **contents))
    assert abs(op.pH - se.pH) > 0.1   # the partition changes the answer -- a cartoon would not


# ---------------------------------------------------------------------------------- sealed mode
def test_sealed_conserves_total_carbon_across_liquid_and_gas():
    n_C = 0.01
    se = solve(MixedGasSystem(mode="sealed", total_acetate_M=0.1, sodium_M=0.1,
                              total_carbon_mol=n_C, v_liquid_L=0.1, v_gas_L=0.1, activity_model="davies"))
    assert se.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL
    assert abs((se.dissolved_carbon_mol + se.gas_carbon_mol) - n_C) < 1e-9 * n_C
    assert abs(se.carbon_balance_residual) < 1e-9 * n_C


def test_sealed_varying_headspace_changes_the_gas_partition():
    base = dict(mode="sealed", total_acetate_M=0.1, sodium_M=0.1, total_carbon_mol=0.01, v_liquid_L=0.1,
                activity_model="davies")
    tiny = solve(MixedGasSystem(v_gas_L=1e-6, **base))
    huge = solve(MixedGasSystem(v_gas_L=100.0, **base))
    assert tiny.gas_carbon_mol < huge.gas_carbon_mol          # larger headspace holds more gas CO2
    assert tiny.gas_carbon_mol >= -1e-15 and huge.gas_carbon_mol >= -1e-15


def test_sealed_no_gas_when_total_carbon_is_absent():
    se = solve(MixedGasSystem(mode="sealed", total_acetate_M=0.1, sodium_M=0.1,
                              total_carbon_mol=0.0, v_liquid_L=0.1, v_gas_L=0.1, activity_model="ideal"))
    assert abs(se.gas_carbon_mol) < 1e-15
    assert abs(se.total_dissolved_carbon_M) < 1e-15
    assert se.p_co2_atm < 1e-12


def test_sealed_pressure_is_positive_and_finite():
    se = solve(MixedGasSystem(mode="sealed", total_acetate_M=0.1, sodium_M=0.0,
                              total_carbon_mol=0.02, v_liquid_L=0.1, v_gas_L=0.05, activity_model="ideal"))
    assert math.isfinite(se.p_co2_atm) and se.p_co2_atm > 0


# ---------------------------------------------------------------------------------- invariants across modes
@pytest.mark.parametrize("sysm", [
    MixedGasSystem(mode="closed", total_acetate_M=0.1, total_carbon_M=0.1, sodium_M=0.1),
    MixedGasSystem(mode="open", total_acetate_M=0.1, sodium_M=0.1, p_co2_atm=1e-2),
    MixedGasSystem(mode="sealed", total_acetate_M=0.1, sodium_M=0.1, total_carbon_mol=0.01,
                   v_liquid_L=0.1, v_gas_L=0.1),
])
def test_every_mode_closes_charge_and_keeps_species_nonnegative(sysm):
    r = solve(sysm)
    assert r.charge_balance_residual < 1e-9 * max(1.0, r.na_plus_M + r.h_plus_M)
    assert r.acetate_conservation_residual < 1e-9 * max(1.0, 0.1)
    for c in (r.hac_M, r.ac_minus_M, r.co2aq_M, r.hco3_M, r.co3_M, r.oh_minus_M, r.h_plus_M):
        assert c >= -1e-12


# ---------------------------------------------------------------------------------- fail-closed domain / inputs
def test_out_of_davies_domain_is_demoted_not_vouched():
    r = solve(MixedGasSystem(mode="closed", total_acetate_M=0.3, total_carbon_M=0.3, sodium_M=0.6,
                             activity_model="davies"))
    assert r.verdict == NUMERICALLY_UNVERIFIED
    assert any("Davies domain" in c for c in r.caveats)


@pytest.mark.parametrize("bad", [
    dict(mode="open"),                                            # missing p_co2_atm
    dict(mode="open", p_co2_atm=0.0),                             # nonpositive pressure
    dict(mode="closed"),                                          # missing total_carbon_M
    dict(mode="sealed", total_carbon_mol=0.01, v_liquid_L=0.1),   # missing v_gas_L
    dict(mode="sealed", total_carbon_mol=0.01, v_gas_L=0.1, v_liquid_L=0.0),  # zero liquid volume
    dict(mode="bogus", total_carbon_M=0.1),                       # unknown mode
])
def test_mode_requires_its_inputs(bad):
    with pytest.raises(InvalidParameterError):
        MixedGasSystem(total_acetate_M=0.1, sodium_M=0.1, **bad)


def test_temperature_outside_the_sourced_domain_is_refused():
    from experiments.sandbox_foundation.aqueous_equilibrium import OutOfSourceDomainError
    with pytest.raises(OutOfSourceDomainError):
        MixedGasSystem(mode="closed", total_carbon_M=0.1, temperature_K=310.0)
