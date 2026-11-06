"""PROBE B -- two-region thermal coupling.  IDEALIZED constant-heat-capacity, Fourier two-point conduction."""
import dataclasses
import math

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from experiments.sandbox_foundation import references as ref
from experiments.sandbox_foundation.fixtures import thermal_system
from experiments.sandbox_foundation.twocell import (
    DeclaredController, Ledger, NonPhysicalTemperatureError, State, System, ThermalBoundary, TimestepError,
    UndeclaredControllerError, apply_controller, audit, run, thermal_step, transport_report)


def _st(sysm, TA=400.0, TB=300.0):
    return State.make(sysm, np.zeros((2, 0)), [TA, TB])


def test_closed_system_energy_consistent_and_matches_closed_form():
    sysm = thermal_system()
    s0 = _st(sysm)
    res = run(sysm, s0, 20.0, 2000, ("thermal",))                    # dt = 0.01 << dt_max = 5
    assert abs(res.state.U.sum() - s0.U.sum()) < 1e-9
    assert abs(audit(sysm, s0, res.state, res.ledger)["energy_residual"]) < 1e-9
    xa, xb = ref.two_node_relaxation(400.0, 300.0, 10.0, 30.0, sysm.G, 20.0)  # independent closed form (T = U/C)
    T = res.state.temperature(sysm)
    assert abs(T[0] - xa) < 0.05 and abs(T[1] - xb) < 0.05              # declared: first-order Euler, ~0.05 K here
    ya, yb = ref.two_node_solve_ivp(400.0, 300.0, 10.0, 30.0, sysm.G, 20.0)
    assert abs(xa - ya) < 1e-8 and abs(xb - yb) < 1e-8                  # references agree with each other


def test_heat_flows_hot_to_cold_and_never_crosses():
    sysm = thermal_system()
    led = Ledger()
    s1, _ = thermal_step(sysm, _st(sysm), 1.0, ledger=led)
    assert led.filter(kind="INTERFACE", cell=0).entries[0].amount < 0   # hot A loses
    assert led.filter(kind="INTERFACE", cell=1).entries[0].amount > 0   # cold B gains
    T = s1.temperature(sysm)
    assert T[0] < 400.0 and T[1] > 300.0 and T[0] >= T[1]
    swapped = thermal_step(sysm, _st(sysm, 300.0, 400.0), 1.0, ledger=Ledger())[0].temperature(sysm)
    assert swapped[0] > 300.0 and swapped[1] < 400.0                   # gradient reversed -> flow reversed


def test_equal_temperatures_zero_conduction():
    sysm = thermal_system()
    led = Ledger()
    s0 = _st(sysm, 300.0, 300.0)
    s1, _ = thermal_step(sysm, s0, 1.0, ledger=led)
    assert all(e.amount == 0.0 for e in led.filter(kind="INTERFACE").entries)
    assert np.array_equal(s1.U, s0.U)


def test_interface_heat_cancels_exactly():
    sysm = thermal_system()
    res = run(sysm, _st(sysm), 5.0, 100, ("thermal",))
    assert transport_report(res.ledger, operator="thermal")["interface_residual"] == 0.0


def test_heater_changes_energy_by_exactly_the_recorded_injection():
    tb = (ThermalBoundary("heater", power_W=5.0), ThermalBoundary())
    sysm = thermal_system(thermal_boundaries=tb)
    s0 = _st(sysm)
    res = run(sysm, s0, 10.0, 1000, ("thermal",))
    injected = transport_report(res.ledger, operator="thermal")["external"]["energy"]
    assert injected == pytest.approx(50.0, rel=1e-12)
    assert res.state.U.sum() - s0.U.sum() == pytest.approx(injected, abs=1e-8)
    assert abs(audit(sysm, s0, res.state, res.ledger)["energy_residual"]) < 1e-8


def test_removing_the_heater_record_is_detected_by_the_energy_audit():   # mutation: lose the bookkeeping
    tb = (ThermalBoundary("heater", power_W=5.0), ThermalBoundary())
    sysm = thermal_system(thermal_boundaries=tb)
    s0 = _st(sysm)
    res = run(sysm, s0, 10.0, 100, ("thermal",))
    res.ledger.entries[:] = [e for e in res.ledger.entries if e.note != "heater"]
    assert audit(sysm, s0, res.state, res.ledger)["energy_residual"] == pytest.approx(50.0, rel=1e-9)


def test_reservoir_accounts_for_its_own_exchange_and_drives_cells_to_its_temperature():
    tb = (ThermalBoundary(), ThermalBoundary("reservoir", T_res_K=300.0, G_res_W_per_K=1.5))
    sysm = thermal_system(thermal_boundaries=tb)
    s0 = _st(sysm, 400.0, 350.0)
    res = run(sysm, s0, 300.0, 1200, ("thermal",))
    cell_side = res.ledger.filter(kind="EXTERNAL")
    own = res.ledger.filter(kind="RESERVOIR_ACCOUNT")
    assert len(cell_side.entries) == len(own.entries) == 1200
    assert all(c.amount == -o.amount for c, o in zip(cell_side.entries, own.entries))   # exact mirror
    d_res = own.total()
    assert res.state.U.sum() - s0.U.sum() + d_res == pytest.approx(0.0, abs=1e-8)       # supersystem closed
    assert d_res > 0   # the cold reservoir absorbed heat from the hot cells (energy moved, was not lost)
    T = res.state.temperature(sysm)
    assert np.all(np.abs(T - 300.0) < 1e-2)   # measured ~1.6e-3 K at t=300 s (slow tail)
    # independent method: scipy on the explicit 2-node + reservoir linear ODE
    C, G, Gr = np.array([10.0, 30.0]), 2.0, 1.5

    def f(_t, U):
        return [G * (U[1] / C[1] - U[0] / C[0]), G * (U[0] / C[0] - U[1] / C[1]) + Gr * (300.0 - U[1] / C[1])]

    mid = run(sysm, s0, 20.0, 2000, ("thermal",)).state
    sol = solve_ivp(f, (0, 20.0), s0.U, method="DOP853", rtol=1e-12, atol=1e-10)
    assert np.max(np.abs(mid.U - sol.y[:, -1]) / C) < 0.05


def test_temperature_cannot_be_set_independently_of_energy():
    sysm = thermal_system()
    s0 = _st(sysm)
    assert "T" not in {f.name for f in dataclasses.fields(State)}         # no independent T degree of freedom
    with pytest.raises(dataclasses.FrozenInstanceError):
        s0.U = np.zeros(2)
    with pytest.raises(ValueError):
        s0.U[0] = 1.0                                                       # arrays are read-only
    for bad in (None, "thermostat", object(), lambda: 0):
        with pytest.raises(UndeclaredControllerError):
            apply_controller(sysm, s0, bad, 0, 350.0)
    with pytest.raises(UndeclaredControllerError):
        apply_controller(sysm, s0, DeclaredController(""), 0, 350.0)


def test_declared_controller_works_and_books_its_energy():
    sysm = thermal_system()
    s0 = _st(sysm)
    led = Ledger()
    s1 = apply_controller(sysm, s0, DeclaredController("ideal-thermostat"), 0, 350.0, ledger=led)
    assert s1.temperature(sysm)[0] == pytest.approx(350.0, abs=1e-12)
    e = led.filter(kind="CONTROLLER").entries[0]
    assert e.amount == pytest.approx(10.0 * (350.0 - 400.0)) and e.note == "ideal-thermostat"
    assert audit(sysm, s0, s1, led)["energy_residual"] == pytest.approx(0.0, abs=1e-9)


# ---- negatives / mutants ----------------------------------------------------------------------------------
def test_too_large_dt_raises_and_second_layer_blocks_nonphysical_T(monkeypatch):
    sysm = thermal_system()
    with pytest.raises(TimestepError):
        thermal_step(sysm, _st(sysm), 100.0)
    s, rep = thermal_step(sysm, _st(sysm), 100.0, policy="substep")
    assert rep.substepped and np.all(s.temperature(sysm) > 0)
    monkeypatch.setattr(System, "thermal_dt_max", lambda self: math.inf)
    with pytest.raises(NonPhysicalTemperatureError):
        thermal_step(sysm, _st(sysm), 100.0)


def test_mutant_wrong_sign_conduction_creates_energy_and_is_caught():
    def bug(coef, x_self, x_other, side):
        v = coef * (x_other - x_self)
        return -v if side == 1 else v
    sysm = thermal_system()
    s0 = _st(sysm)
    led = Ledger()
    s1, _ = thermal_step(sysm, s0, 0.5, flux_fn=bug, ledger=led)
    assert abs(audit(sysm, s0, s1, led)["energy_residual"]) > 1.0
    assert transport_report(led, operator="thermal")["interface_residual"] > 1.0


def test_mutant_uphill_heat_conserves_energy_but_direction_test_catches_it():
    sysm = thermal_system()
    s0 = _st(sysm)
    led = Ledger()
    s1, _ = thermal_step(sysm, s0, 0.5, flux_fn=lambda c, xs, xo, side: c * (xs - xo), ledger=led)
    assert abs(audit(sysm, s0, s1, led)["energy_residual"]) < 1e-9       # conservation is blind to it...
    assert s1.temperature(sysm)[0] > 400.0                                 # ...the direction check is not (hot got hotter)


@pytest.mark.parametrize("kw", [dict(C=(0.0, 1.0)), dict(k=-1.0), dict(C=(1.0, float("inf")))])
def test_invalid_thermal_parameters_raise(kw):
    with pytest.raises(Exception) as ei:
        thermal_system(**kw)
    assert ei.value.__class__.__name__ == "InvalidParameterError"


def test_nonpositive_temperature_rejected():
    sysm = thermal_system()
    with pytest.raises(NonPhysicalTemperatureError):
        State.make(sysm, np.zeros((2, 0)), [0.0, 300.0])


# ---- F3 coverage closer: the reservoir conductance must enter the stability bound -------------------------------
def test_reservoir_conductance_binds_the_thermal_stability_bound():
    tb = (ThermalBoundary("reservoir", T_res_K=300.0, G_res_W_per_K=8.0), ThermalBoundary())
    sysm = thermal_system(thermal_boundaries=tb)             # C=(10,30), G=2:  A couples with G+G_res = 10 W/K
    assert sysm.thermal_dt_max() == pytest.approx(10.0 / (2.0 + 8.0))     # 1.0 s, set by the reservoir-coupled cell
    assert thermal_system().thermal_dt_max() == pytest.approx(5.0)         # without the reservoir the bound is 5 s
    s0 = _st(sysm, 400.0, 350.0)
    with pytest.raises(TimestepError):                       # 1 < 2 < 5: admitted if the G_res term were dropped
        thermal_step(sysm, s0, 2.0)
    s1, rep = thermal_step(sysm, s0, 1.0)                    # at the bound: convex combination, no overshoot
    T = s1.temperature(sysm)
    assert 300.0 <= T.min() and T.max() <= 400.0 and not rep.substepped
    s2, rep2 = thermal_step(sysm, s0, 2.0, policy="substep")
    assert rep2.substepped and rep2.substeps == 2
    assert 300.0 <= s2.temperature(sysm).min() and s2.temperature(sysm).max() <= 400.0
