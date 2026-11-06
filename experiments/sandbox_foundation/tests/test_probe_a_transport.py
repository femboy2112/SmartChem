"""PROBE A -- passive-tracer transport, NO chemistry.  Positive / negative / mutation / independent-method."""
import math

import numpy as np
import pytest

from experiments.sandbox_foundation import references as ref
from experiments.sandbox_foundation.fixtures import tracer_system
from experiments.sandbox_foundation.twocell import (
    InvalidParameterError, Ledger, NegativeAmountError, SpeciesBoundary, State, System, TimestepError,
    audit, run, transport_report, transport_step)


def _start(system, nA=4.0):
    return State(np.array([[nA], [0.0]]), np.array([1.0, 1.0]))


def test_closed_system_conserves_total_tracer():
    sysm = tracer_system()
    s0 = _start(sysm)
    res = run(sysm, s0, 5.0, 500, ("transport",))
    assert abs(res.state.n.sum() - s0.n.sum()) < 1e-13
    a = audit(sysm, s0, res.state, res.ledger)
    assert a["inventory_residual"] < 1e-13
    assert res.state.n[1, 0] > 0.5  # and tracer actually moved (not a vacuous "nothing happened")


def test_interface_fluxes_cancel_exactly_at_ledger_level():
    sysm = tracer_system()
    res = run(sysm, _start(sysm), 5.0, 100, ("transport",))
    assert transport_report(res.ledger)["interface_residual"] == 0.0  # exact, not "close"
    face = res.ledger.filter(kind="INTERFACE")
    assert len(face.entries) == 2 * 100 and any(e.amount != 0 for e in face.entries)


def test_open_boundary_changes_inventory_by_exactly_recorded_external_flow():
    b = (SpeciesBoundary("prescribed_flow", (0.3,)), SpeciesBoundary("prescribed_flow", (-0.1,)))
    sysm = tracer_system(boundaries=b)
    s0 = State(np.array([[1.0], [1.0]]), np.array([1.0, 1.0]))
    res = run(sysm, s0, 4.0, 200, ("transport",))
    expected = (0.3 - 0.1) * 4.0
    assert res.state.n.sum() - s0.n.sum() == pytest.approx(expected, abs=1e-12)
    rec = transport_report(res.ledger)["external"]["T"]
    assert rec == pytest.approx(expected, abs=1e-12)           # recorded flow == what we asked for
    assert audit(sysm, s0, res.state, res.ledger)["inventory_residual"] < 1e-12
    # the interface alone still cancels exactly even with an open boundary present
    assert transport_report(res.ledger)["interface_residual"] == 0.0


def test_equal_concentrations_give_zero_diffusive_flux():
    sysm = tracer_system()  # V = (1,2): c = 0.5 each -> n = (0.5, 1.0), all dyadic -> exact
    s0 = State(np.array([[0.5], [1.0]]), np.array([1.0, 1.0]))
    led = Ledger()
    s1, _ = transport_step(sysm, s0, 1.0, ledger=led)
    assert all(e.amount == 0.0 for e in led.filter(kind="INTERFACE").entries)
    assert np.array_equal(s1.n, s0.n)


def test_reversing_gradient_reverses_flux():
    sysm = tracer_system(V=(1.0, 1.0))
    fwd, rev = Ledger(), Ledger()
    transport_step(sysm, State(np.array([[3.0], [1.0]]), np.ones(2)), 0.5, ledger=fwd)
    transport_step(sysm, State(np.array([[1.0], [3.0]]), np.ones(2)), 0.5, ledger=rev)
    inflow_B_fwd = fwd.filter(kind="INTERFACE", cell=1).entries[0].amount
    inflow_A_rev = rev.filter(kind="INTERFACE", cell=0).entries[0].amount
    assert inflow_B_fwd > 0 and inflow_A_rev > 0          # always downhill
    assert inflow_B_fwd == inflow_A_rev                     # mirror image, bitwise


def test_downhill_direction_matches_physics():
    sysm = tracer_system()
    s1, _ = transport_step(sysm, _start(sysm), 0.5)
    assert s1.n[0, 0] < 4.0 and s1.n[1, 0] > 0.0  # tracer leaves A, enters B


# ---- (6) negative concentration can never appear silently --------------------------------------------
def test_too_large_timestep_raises_and_unguarded_euler_would_have_gone_negative():
    sysm = tracer_system(V=(1.0, 1.0), D=1.0)  # g=1, dt_max=1
    s0 = _start(sysm)
    dt = 10.0
    # PROOF the guard is load-bearing: the raw forward-Euler update with the same numbers IS negative in B-or-A
    cA, cB = s0.n[0, 0] / 1.0, s0.n[1, 0] / 1.0
    raw_A = s0.n[0, 0] + dt * 1.0 * (cB - cA)
    assert raw_A < 0
    with pytest.raises(TimestepError):
        transport_step(sysm, s0, dt)


def test_substep_policy_is_explicitly_flagged_and_stays_nonnegative():
    sysm = tracer_system(V=(1.0, 1.0), D=1.0)
    s0 = _start(sysm)
    s1, rep = transport_step(sysm, s0, 10.0, policy="substep")
    assert rep.substepped and rep.substeps >= 10 and rep.dt_limit == pytest.approx(1.0)
    assert np.all(s1.n >= 0) and abs(s1.n.sum() - s0.n.sum()) < 1e-13
    _, rep_ok = transport_step(sysm, s0, 0.5)
    assert not rep_ok.substepped


def test_second_layer_guard_catches_negative_even_if_dt_bound_is_bypassed(monkeypatch):
    sysm = tracer_system(V=(1.0, 1.0), D=1.0)
    monkeypatch.setattr(System, "transport_dt_max", lambda self: math.inf)  # disable layer 1
    with pytest.raises(NegativeAmountError):
        transport_step(sysm, _start(sysm), 10.0)


def test_overlarge_prescribed_outflow_is_refused_not_clamped():
    b = (SpeciesBoundary("prescribed_flow", (-5.0,)), SpeciesBoundary())
    sysm = tracer_system(boundaries=b)
    with pytest.raises(NegativeAmountError):
        transport_step(sysm, _start(sysm, nA=1.0), 1.0)


@pytest.mark.parametrize("bad", [
    dict(D=-1.0), dict(V=(0.0, 1.0)), dict(V=(1.0, float("nan"))),
])
def test_invalid_parameters_raise(bad):
    with pytest.raises(InvalidParameterError):
        tracer_system(**bad)


@pytest.mark.parametrize("dt", [-1.0, float("nan"), float("inf")])
def test_invalid_dt_raises(dt):
    sysm = tracer_system()
    with pytest.raises(InvalidParameterError):
        transport_step(sysm, _start(sysm), dt)


def test_invalid_state_raises():
    with pytest.raises(NegativeAmountError):
        State(np.array([[-1.0], [0.0]]), np.ones(2))
    with pytest.raises(InvalidParameterError):
        State(np.array([[np.nan], [0.0]]), np.ones(2))


# ---- mutation controls ---------------------------------------------------------------------------------
def _one_sided_sign_bug(coef, x_self, x_other, side):
    """MUTANT: side 1 gets the wrong sign, so J_AB + J_BA != 0 (tracer is created from nothing)."""
    v = coef * (x_other - x_self)
    return -v if side == 1 else v


def _reversed_both(coef, x_self, x_other, side):
    """MUTANT: anti-diffusion (uphill).  Conserves tracer perfectly -> only the direction test can catch it."""
    return coef * (x_self - x_other)


def test_mutant_one_sided_sign_is_caught_by_conservation_and_ledger():
    sysm = tracer_system()
    s0 = State(np.array([[4.0], [2.0]]), np.ones(2))  # B non-empty so the mutant does not just trip the neg-guard
    led = Ledger()
    s1, _ = transport_step(sysm, s0, 0.5, flux_fn=_one_sided_sign_bug, ledger=led)
    assert transport_report(led)["interface_residual"] > 1e-3
    assert abs(s1.n.sum() - s0.n.sum()) > 1e-3
    assert audit(sysm, s0, s1, led)["inventory_residual"] > 1e-3


def test_mutant_reversed_flux_conserves_but_direction_test_catches_it():
    sysm = tracer_system(V=(1.0, 1.0))
    s0 = State(np.array([[4.0], [2.0]]), np.ones(2))
    led = Ledger()
    s1, _ = transport_step(sysm, s0, 0.2, flux_fn=_reversed_both, ledger=led)
    assert transport_report(led)["interface_residual"] == 0.0     # conservation alone is BLIND to this mutant
    assert abs(s1.n.sum() - s0.n.sum()) < 1e-13
    assert not (s1.n[1, 0] > s0.n[1, 0])                            # direction check: B must gain from A -- it doesn't


def test_mutant_reversed_flux_on_empty_neighbour_trips_the_negativity_guard():
    sysm = tracer_system(V=(1.0, 1.0))
    with pytest.raises(NegativeAmountError):
        transport_step(sysm, _start(sysm), 0.2, flux_fn=_reversed_both)


def test_tampered_ledger_is_detected():
    sysm = tracer_system()
    res = run(sysm, _start(sysm), 1.0, 10, ("transport",))
    led = res.ledger
    e = led.entries[0]
    led.entries[0] = type(e)(**{**e.__dict__, "amount": -e.amount})
    assert transport_report(led)["interface_residual"] > 0.0


# ---- independent methods -------------------------------------------------------------------------------
def test_agrees_with_closed_form_and_solve_ivp_within_declared_error():
    sysm = tracer_system()
    s0 = _start(sysm)
    t = 2.0
    cA0, cB0 = s0.n[0, 0] / 1.0, 0.0
    g = sysm.g[0]
    xa, xb = ref.two_node_relaxation(cA0, cB0, 1.0, 2.0, g, t)
    ya, yb = ref.two_node_solve_ivp(cA0, cB0, 1.0, 2.0, g, t)
    assert abs(xa - ya) < 1e-9 and abs(xb - yb) < 1e-9          # the two references agree with each other
    res = run(sysm, s0, t, 400, ("transport",))                   # dt = 5e-3
    declared_tol = 5e-3 * s0.n.sum()                              # first-order Euler: err ~ O(dt)
    assert abs(res.state.n[0, 0] / 1.0 - xa) < declared_tol
    assert abs(res.state.n[1, 0] / 2.0 - xb) < declared_tol


def test_run_is_bitwise_deterministic():
    sysm = tracer_system()
    a = run(sysm, _start(sysm), 1.0, 50, ("transport",)).state
    b = run(sysm, _start(sysm), 1.0, 50, ("transport",)).state
    assert np.array_equal(a.n, b.n)


# ---- F1/F2 coverage closers: asymmetric volumes and non-unit geometry ----------------------------------------
def test_dt_bound_is_set_by_the_smaller_cell_and_a_dt_between_min_and_max_bounds_is_refused():
    sysm = tracer_system(D=1.0, V=(1.0, 2.0))               # g = 1 m^3/s: min-bound 1.0 s, max-bound 2.0 s
    assert sysm.transport_dt_max() == pytest.approx(1.0)    # the SMALLER cell binds
    s0 = State(np.array([[4.0], [1.0]]), np.ones(2))
    with pytest.raises(TimestepError):                       # 1.0 < 1.5 < 2.0: a max-based bound would admit it
        transport_step(sysm, s0, 1.5)
    # and the refused step really would have gone wrong: raw Euler on the small cell undershoots below zero
    assert s0.n[0, 0] + 1.5 * sysm.g[0] * (s0.n[1, 0] / 2.0 - s0.n[0, 0] / 1.0) < 0


def test_asymmetric_volumes_obey_the_discrete_maximum_principle():
    sysm = tracer_system(D=1.0, V=(1.0, 2.0))
    s0 = State(np.array([[4.0], [1.0]]), np.ones(2))        # c = (4.0, 0.5)
    lo, hi = 0.5, 4.0
    for dt, kw in ((1.0, {}), (1.5, {"policy": "substep"})):   # at the bound, and over it (substepped, flagged)
        s1, rep = transport_step(sysm, s0, dt, **kw)
        c = s1.n[:, 0] / np.array([1.0, 2.0])
        assert lo - 1e-12 <= c.min() and c.max() <= hi + 1e-12   # no new extremum, no under/overshoot
        assert abs(s1.n.sum() - s0.n.sum()) < 1e-13
    assert rep.substepped and rep.substeps == 2


def test_interface_coefficients_use_area_over_distance_with_nonunit_geometry():
    sysm = System(("T",), (1.0, 2.0), (10.0, 30.0), (0.3,), 2.0, 0.5, 1.7)   # A=2 m^2, d=0.5 m
    assert sysm.g[0] == pytest.approx(0.3 * 2.0 / 0.5)       # 1.2  (dropped area -> 0.6, dropped d -> 0.6, A^2 -> 2.4)
    assert sysm.G == pytest.approx(1.7 * 2.0 / 0.5)          # 6.8
    assert sysm.transport_dt_max() == pytest.approx(1.0 / 1.2)
    led = Ledger()
    transport_step(sysm, State(np.array([[1.0], [0.5]]), np.ones(2)), 0.1, ledger=led)
    inflow_B = led.filter(kind="INTERFACE", cell=1).entries[0].amount
    assert inflow_B == pytest.approx(1.2 * (1.0 / 1.0 - 0.5 / 2.0) * 0.1)   # g * (c_A - c_B) * dt
