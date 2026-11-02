"""PROBE D -- compositionality: two-cell transport + the SYNTHETIC reaction (and conduction) in one Lie-split run."""
import dataclasses

import numpy as np
import pytest

from experiments.sandbox_foundation import references as ref
from experiments.sandbox_foundation.analysis import (
    apply_ops, assert_commute, commutator, convergence_ok, estimate_order, state_distance)
from experiments.sandbox_foundation.fixtures import bimolecular_mechanism, composite_system
from experiments.sandbox_foundation.twocell import (
    Ledger, State, System, audit, reaction_report, run, transport_report)

N0 = np.array([[1.0, 0.0, 1.0], [0.0, 0.0, 0.0]])   # P and tracer T start in A; B empty


def _s0(sysm=None):
    return State(N0, np.array([1.0, 1.0]))


def _one_sided_bug(coef, xs, xo, side):
    v = coef * (xo - xs)
    return -v if side == 1 else v


# ---- (1) global conservation survives composition ---------------------------------------------------------
def test_global_conservation_survives_composition():
    sysm = composite_system()
    res = run(sysm, _s0(), 2.0, 40, ("transport", "reaction"))
    a = audit(sysm, _s0(), res.state, res.ledger)
    assert a["inventory_residual"] < 1e-12                        # X, Tunit, charge
    assert abs(res.state.n[:, 2].sum() - 1.0) < 1e-13               # tracer total (passive T) exactly kept
    assert abs(res.state.n[:, :2].sum() - 1.0) < 1e-12              # P+Q total (reaction is isomerization)
    assert res.state.n[1, 1] > 1e-3                                  # Q was made AND moved: real coupling happened


# ---- (2) reports are separable ----------------------------------------------------------------------------------
def test_reaction_and_transport_reports_are_independently_inspectable():
    sysm = composite_system()
    res = run(sysm, _s0(), 2.0, 40, ("transport", "reaction"))
    tr_full, rx_full = transport_report(res.ledger), reaction_report(res.ledger, sysm.mechanism)
    only_tr = Ledger(res.ledger.filter(operator="transport").entries)
    only_rx = Ledger(res.ledger.filter(operator="reaction").entries)
    assert transport_report(only_tr) == tr_full and tr_full["interface_residual"] == 0.0
    assert reaction_report(only_rx, sysm.mechanism) == rx_full and rx_full["element_charge_residual"] < 1e-12
    assert transport_report(only_rx)["interface_residual"] == 0.0 and len(only_rx.entries) > 0
    assert {e.operator for e in only_tr.entries} == {"transport"} and {e.operator for e in only_rx.entries} == {"reaction"}


def test_a_transport_bug_shows_up_in_the_transport_report_only():
    sysm = composite_system()
    s0 = State(np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]), np.ones(2))
    res = run(sysm, s0, 1.0, 20, (("transport", {"flux_fn": _one_sided_bug}), "reaction"))
    assert transport_report(res.ledger)["interface_residual"] > 1e-3
    assert reaction_report(res.ledger, sysm.mechanism)["element_charge_residual"] < 1e-12   # fault is LOCALIZED
    assert audit(sysm, s0, res.state, res.ledger)["inventory_residual"] > 1e-3               # and the global audit sees it


# ---- (3) independent disjoint operations commute and keep their invariants -------------------------------------
def test_reaction_in_disjoint_cells_commutes_exactly():
    sysm = composite_system()
    s0 = State(np.array([[1.0, 0.2, 0.0], [0.5, 0.1, 0.0]]), np.ones(2))
    dt = 0.3
    ra, rb = ("reaction", {"cells": (0,)}), ("reaction", {"cells": (1,)})
    assert commutator(sysm, s0, ra, rb, dt) == 0.0
    # non-vacuous: each op really changes its own cell, and a SAME-cell pair is a different (non-commuting-check) story
    assert state_distance(s0, apply_ops(sysm, s0, dt, [ra, rb])) > 1e-2


def test_transport_of_immobile_reactants_and_mobile_tracer_commute_and_each_keeps_its_invariant():
    sysm = composite_system(D=(0.0, 0.0, 0.5))   # P,Q immobile; only T moves -> disjoint species supports
    s0 = State(np.array([[1.0, 0.2, 1.0], [0.0, 0.0, 0.0]]), np.ones(2))
    tr, rx = "transport", "reaction"
    assert_commute(sysm, s0, tr, rx, 0.4, tol=1e-12)
    for order in ((tr, rx), (rx, tr)):
        res = run(sysm, s0, 2.0, 10, order)
        assert abs(res.state.n[:, 2].sum() - 1.0) < 1e-13            # tracer invariant (transport's)
        assert np.max(np.abs(sysm.mechanism.E @ (res.state.n.sum(0) - s0.n.sum(0)))) < 1e-12   # reaction's


def test_conduction_commutes_with_transport_and_reaction_because_state_is_disjoint():
    sysm = dataclasses.replace(composite_system(), conductivity_W_per_mK=2.0)
    s0 = State.make(sysm, N0, [400.0, 300.0])
    for other in ("transport", "reaction"):
        assert commutator(sysm, s0, "thermal", other, 0.2) == 0.0


# ---- (4) coupled / state-dependent operations are NOT claimed to commute -------------------------------------
def test_coupled_transport_and_reaction_do_not_commute():
    sysm = composite_system(D=(0.5, 1.0, 0.25))   # D_P != D_Q: transport mixes the species the reaction couples
    s0 = _s0()
    c = commutator(sysm, s0, "transport", "reaction", 0.4)
    assert c > 1e-3, c
    with pytest.raises(AssertionError):          # this is the test that FAILS if somebody asserts they commute
        assert_commute(sysm, s0, "transport", "reaction", 0.4, tol=1e-6)


def test_commutation_is_structure_not_luck_equal_D_makes_the_linear_case_commute():
    sysm = composite_system(D=(0.7, 0.7, 0.7))
    assert commutator(sysm, _s0(), "transport", "reaction", 0.4) < 1e-9     # special: linear + identical D
    # ...but a NONLINEAR reaction does not, even with identical D:
    m = bimolecular_mechanism(2.0)
    nl = System(m.species, (1.0, 2.0), (1.0, 1.0), (0.7, 0.7, 0.7), 1.0, 1.0, 0.0, mechanism=m)
    s0 = State(np.array([[1.0, 0.5, 0.0], [0.0, 0.0, 0.0]]), np.ones(2))
    assert commutator(nl, s0, "transport", "reaction", 0.4) > 1e-3


# ---- (5) timestep refinement -> the monolithic model solution -------------------------------------------------------
def _split_errors(kf_split=1.5, steps=(8, 16, 32, 64), T=1.0):
    sysm = composite_system(kf=kf_split)
    sys_ref = composite_system(kf=1.5)
    truth = ref.composite_linear_reference(sys_ref.volumes_m3, sys_ref.g, 1.5, 0.5, N0, T)   # expm, un-split
    errs = [float(np.max(np.abs(run(sysm, _s0(), T, k, ("transport", "reaction")).state.n - truth))) for k in steps]
    return [T / k for k in steps], errs


def test_two_independent_monolithic_references_agree():
    s = composite_system()
    a = ref.composite_linear_reference(s.volumes_m3, s.g, 1.5, 0.5, N0, 1.0, "expm")
    b = ref.composite_linear_reference(s.volumes_m3, s.g, 1.5, 0.5, N0, 1.0, "ivp")
    assert np.max(np.abs(a - b)) < 1e-10


def test_timestep_refinement_converges_at_first_order_to_the_monolithic_solution():
    dts, errs = _split_errors()
    assert all(e > 0 for e in errs) and np.all(np.diff(errs) < 0)
    p = estimate_order(dts, errs)
    assert 0.8 <= p <= 1.3, (p, errs)          # DECLARED regime: first order (Lie splitting + forward Euler transport)
    assert convergence_ok(dts, errs)
    assert errs[-1] < errs[0] / 6               # refinement really shrinks the error


def test_mutant_inconsistent_scheme_fails_the_convergence_check():
    dts, errs = _split_errors(kf_split=1.65)   # splitting scheme solves a DIFFERENT model (kf off by 10%)
    assert not convergence_ok(dts, errs)         # error plateaus at the model bias instead of shrinking
    assert errs[-1] > 0.5 * errs[0]
