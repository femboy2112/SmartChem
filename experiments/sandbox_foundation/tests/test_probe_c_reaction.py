"""PROBE C -- a finite SYNTHETIC reaction (abstract P<->Q, R+ + S- -> RS) with USER-SUPPLIED rate constants.
Nothing here is real laboratory chemistry."""
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from experiments.sandbox_foundation import references as ref
from experiments.sandbox_foundation.fixtures import bimolecular_mechanism, isomer_mechanism, single_cell_system
from experiments.sandbox_foundation.twocell import (
    ConstitutionError, InfeasibleExtentError, InvalidParameterError, Ledger, Mechanism, MissingKineticParameter,
    NegativeAmountError, ReactionRate, SolverSettings, State, audit, reaction_report, reaction_step)


def _iso_state(nP=1.0, nQ=0.0):
    return State(np.array([[nP, nQ], [nP, nQ]]), np.ones(2))


def _react(mech, state, dt, **kw):
    sysm = single_cell_system(mech)
    led = Ledger()
    s, rep = reaction_step(sysm, state, dt, ledger=led, **kw)
    return sysm, s, rep, led


# ---- (1) stoichiometric source term agrees with N -------------------------------------------------------
def test_source_term_equals_N_times_rate_hand_computed():
    m = isomer_mechanism(1.5, 0.5)
    c = np.array([2.0, 1.0])
    r = 1.5 * 2.0 - 0.5 * 1.0
    assert np.allclose(m.source_density(c), [-r, +r], atol=0, rtol=1e-15)
    b = bimolecular_mechanism(2.0)
    assert np.allclose(b.source_density(np.array([3.0, 0.5, 0.0])), 2.0 * 3.0 * 0.5 * np.array([-1, -1, 1]))


def test_integrated_change_equals_N_times_extent_and_matches_independent_species_space_solve():
    m = isomer_mechanism()
    s0 = _iso_state(1.0, 0.2)
    sysm, s1, rep, led = _react(m, s0, 1.3)
    xi = rep.extents["A"]
    assert np.allclose(s1.n[0] - s0.n[0], (m.N @ xi), atol=1e-14)       # dn = N xi
    # independent: integrate dn/dt = V N r(n/V) directly in SPECIES space with a different method (DOP853)
    sol = solve_ivp(lambda _t, n: m.N @ m.rate_vector(n), (0, 1.3), s0.n[0], method="DOP853", rtol=1e-12, atol=1e-14)
    assert np.max(np.abs(sol.y[:, -1] - s1.n[0])) < 1e-8


# ---- (2) element AND charge inventory invariant --------------------------------------------------------------
@pytest.mark.parametrize("mech,n0", [(isomer_mechanism(), [1.0, 0.2]), (bimolecular_mechanism(), [1.0, 0.3, 0.0])])
def test_element_and_charge_inventory_invariant(mech, n0):
    assert np.array_equal(mech.E @ mech.N, np.zeros((3, 1)))             # E.N = 0 exactly
    s0 = State(np.array([n0, n0]), np.ones(2))
    sysm, s1, _, led = _react(mech, s0, 2.0)
    assert not np.allclose(s1.n, s0.n)                                      # it actually reacted
    assert np.max(np.abs(mech.E @ (s1.n - s0.n).T)) < 1e-12
    assert audit(sysm, s0, s1, led)["inventory_residual"] < 1e-12
    assert reaction_report(led, mech)["element_charge_residual"] < 1e-12


def test_mutant_unbalanced_stoichiometry_is_refused_at_construction():
    rate = (ReactionRate(1.0, 1.0),)
    with pytest.raises(ConstitutionError):   # element X not balanced (P loses 1, Q gains 2)
        Mechanism(("P", "Q"), [[-1.0], [2.0]], ("X", "charge"), [[1, 1], [1, 1]], rate)
    with pytest.raises(ConstitutionError):   # elements balanced, CHARGE not (a lone electron appears)
        Mechanism(("P", "Q"), [[-1.0], [1.0]], ("X", "charge"), [[1, 1], [1, 0]], rate)


def test_mutant_unbalanced_row_that_bypasses_validation_is_caught_by_the_conservation_assertions():
    bad = Mechanism(("P", "Q"), [[-1.0], [2.0]], ("X", "charge"), [[1, 1], [1, 1]],
                    (ReactionRate(1.0, 1.0),), validate=False)           # deliberately smuggled in
    assert np.max(np.abs(bad.constitution_residual())) > 0.5
    s0 = _iso_state()
    sysm, s1, _, led = _react(bad, s0, 1.0)
    assert reaction_report(led, bad)["element_charge_residual"] > 1e-3
    assert audit(sysm, s0, s1, led)["inventory_residual"] > 1e-3


# ---- (3) bounded progress ---------------------------------------------------------------------------------------
def test_extent_capped_by_limiting_reactant_and_amounts_never_negative():
    m = bimolecular_mechanism(2.0)
    s0 = State(np.array([[1.0, 0.3, 0.0]] * 2), np.ones(2))
    assert m.extent_bounds(s0.n[0], 0) == (-0.0, pytest.approx(0.3))
    _, s1, rep, _ = _react(m, s0, 1000.0)
    assert rep.extents["A"][0] <= 0.3 + 1e-11
    assert np.all(s1.n >= 0.0)
    assert s1.n[0, 1] < 1e-9 and s1.n[0, 2] == pytest.approx(0.3, abs=1e-9)   # S- is limiting & exhausted
    assert rep.clamped            # the sub-pos_tol roundoff overshoot was clamped AND flagged, not hidden


def test_forced_extent_beyond_limiting_reactant_is_refused():
    m = bimolecular_mechanism()
    n = np.array([1.0, 0.3, 0.0])
    assert np.allclose(m.apply_extent(n, 0, 0.3), [0.7, 0.0, 0.3])
    with pytest.raises(InfeasibleExtentError):
        m.apply_extent(n, 0, 0.30001)
    with pytest.raises(InfeasibleExtentError):
        m.apply_extent(n, 0, -0.1)          # no RS yet to run backwards (irreversible window)


def test_integrator_error_too_large_to_clamp_raises_not_silent():
    m = bimolecular_mechanism(2.0)
    s0 = State(np.array([[1.0, 0.3, 0.0]] * 2), np.ones(2))
    with pytest.raises(NegativeAmountError):
        _react(m, s0, 100.0, settings=SolverSettings(rtol=1e-6, atol=1e-9))   # measured overshoot -4.7e-10 < -pos_tol (1e-11)


# ---- (4) missing kinetic parameters are UNKNOWN, never a silent zero --------------------------------------------
@pytest.mark.parametrize("rate", [
    ReactionRate(), ReactionRate(k_f=1.0), ReactionRate(k_r=1.0), ReactionRate(k_f=None, k_r=None, reversible=True)])
def test_missing_rate_parameter_raises(rate):
    m = Mechanism(("P", "Q"), [[-1.0], [1.0]], ("X",), [[1, 1]], (rate,))
    sysm = single_cell_system(m)
    with pytest.raises(MissingKineticParameter):
        reaction_step(sysm, _iso_state(), 1.0)
    with pytest.raises(MissingKineticParameter):
        m.rate_vector(np.array([1.0, 1.0]))     # also at the rate-evaluation layer, not only the stepper


def test_irreversible_reaction_does_not_need_a_reverse_constant_but_still_needs_forward():
    ok = Mechanism(("P", "Q"), [[-1.0], [1.0]], ("X",), [[1, 1]], (ReactionRate(k_f=1.0, reversible=False),))
    assert ok.rate_vector(np.array([2.0, 1.0]))[0] == 2.0
    no = Mechanism(("P", "Q"), [[-1.0], [1.0]], ("X",), [[1, 1]], (ReactionRate(reversible=False),))
    with pytest.raises(MissingKineticParameter):
        no.rate_vector(np.array([2.0, 1.0]))


def test_negative_rate_constant_is_invalid():
    m = isomer_mechanism(kf=-1.0)
    with pytest.raises(InvalidParameterError):
        m.require_complete()


# ---- (5) independent methods -------------------------------------------------------------------------------------
@pytest.mark.parametrize("kf,kr,t", [(1.5, 0.5, 2.0), (1e4, 1e3, 1.0)])   # second row: STIFF (fast relaxation 1.1e4 /s)
def test_isomerization_matches_closed_form_within_declared_error(kf, kr, t):
    s0 = _iso_state(1.0, 0.2)
    _, s1, _, _ = _react(isomer_mechanism(kf, kr), s0, t)
    P, Q = ref.isomerization_analytic(1.0, 0.2, kf, kr, t)
    declared = 1e-8
    assert abs(s1.n[0, 0] - P) < declared and abs(s1.n[0, 1] - Q) < declared


def test_bimolecular_matches_closed_form_for_unequal_initial_amounts():
    m = bimolecular_mechanism(2.0)
    s0 = State(np.array([[1.0, 0.3, 0.0]] * 2), np.ones(2))
    _, s1, rep, _ = _react(m, s0, 1.0)
    assert abs(rep.extents["A"][0] - ref.bimolecular_analytic(1.0, 0.3, 2.0, 1.0, 1.0)) < 1e-8
    # volume dependence is real (second order): V=2 changes the answer, still matches the closed form
    sysm2 = single_cell_system(m, V=(2.0, 2.0))
    _, rep2 = reaction_step(sysm2, s0, 1.0)
    assert abs(rep2.extents["A"][0] - ref.bimolecular_analytic(1.0, 0.3, 2.0, 2.0, 1.0)) < 1e-8
    assert abs(rep2.extents["A"][0] - rep.extents["A"][0]) > 1e-3


def test_mutant_reversed_stoichiometry_sign_disagrees_with_closed_form():
    flipped = Mechanism(("P", "Q"), [[1.0], [-1.0]], ("X", "Y", "charge"), [[2, 2], [1, 1], [1, 1]],
                        (ReactionRate(1.5, 0.5),))   # balanced, but P->Q has become Q->P under the SAME rates
    _, s1, _, _ = _react(flipped, _iso_state(1.0, 0.2), 2.0)
    P, _ = ref.isomerization_analytic(1.0, 0.2, 1.5, 0.5, 2.0)
    assert abs(s1.n[0, 0] - P) > 1e-2      # element conservation is BLIND to this one; the independent check is not


# ---- (6) a rate parameter moves ONLY the dynamics ------------------------------------------------------------------
def test_changing_rate_constant_moves_dynamics_but_not_stoichiometric_conservation():
    s0 = _iso_state(1.0, 0.0)
    base, fast = isomer_mechanism(1.5, 0.5), isomer_mechanism(3.0, 0.5)
    assert np.array_equal(base.N, fast.N) and np.array_equal(base.E, fast.E)
    sysm_b, sb, _, lb = _react(base, s0, 1.0)
    sysm_f, sf, _, lf = _react(fast, s0, 1.0)
    assert abs(sf.n[0, 1] - sb.n[0, 1]) > 0.05                                # dynamics moved...
    Pf, _ = ref.isomerization_analytic(1.0, 0.0, 3.0, 0.5, 1.0)
    assert abs(sf.n[0, 0] - Pf) < 1e-8                                         # ...exactly as predicted
    for sysm, s, led in ((sysm_b, sb, lb), (sysm_f, sf, lf)):                 # ...while conservation is identical
        assert audit(sysm, s0, s, led)["inventory_residual"] < 1e-12
        assert reaction_report(led, sysm.mechanism)["element_charge_residual"] < 1e-12


def test_scaling_both_rate_constants_is_pure_time_rescaling():
    s0 = _iso_state(1.0, 0.0)
    _, a, _, _ = _react(isomer_mechanism(3.0, 1.0), s0, 0.5)     # (k * 2) over t
    _, b, _, _ = _react(isomer_mechanism(1.5, 0.5), s0, 1.0)     # (k) over 2 t
    assert np.max(np.abs(a.n - b.n)) < 1e-8


def test_reaction_step_is_deterministic_and_reports_its_solver_settings():
    s0 = _iso_state()
    _, a, ra, _ = _react(isomer_mechanism(), s0, 1.0)
    _, b, _, _ = _react(isomer_mechanism(), s0, 1.0)
    assert np.array_equal(a.n, b.n)
    assert ra.solver == {"method": "Radau", "rtol": 1e-10, "atol": 1e-13, "pos_tol": 1e-11, "seed": None}
