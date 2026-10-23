"""Wave C -- free-energy / Lyapunov dissipation: the adversarial test matrix.

SYNTHETIC / idealized.  The theorems live in lyapunov.py's docstring (C1 reaction, C2 diffusion, C3 discrete
Jensen); here we (a) verify the analytical derivative equals the sum of the proved closed forms INDEPENDENTLY
of any integrator, (b) corroborate with a refined finite difference, and (c) hunt the adversarial cases:
zero dissipation at equal compartments, strict dissipation otherwise, discrete monotonicity under unequal
volumes, an anti-diffusion flux that conserves matter yet VIOLATES dissipation, a driven/open system that
legitimately escapes the closed theorem, the near-zero log limit, and a refusal without a detailed-balanced c*."""
import numpy as np
import pytest

from experiments.sandbox_foundation.lyapunov import (
    diffusion_dissipation_rate, dPhi_dt_chain_rule, is_closed_passive, is_detailed_balance_equilibrium,
    reaction_dissipation_rate, relative_free_energy, total_dissipation_rate)
from experiments.sandbox_foundation.twocell import (
    InvalidParameterError, Ledger, Mechanism, ReactionRate, SolverSettings, SpeciesBoundary, State, System,
    ThermalBoundary, audit, reaction_step, transport_step)


def _sys(mech=None, V=(1.0, 1.0), D=(0.1, 0.1), sb=None):
    return System(("A", "B"), V, (1.0, 1.0), D, area_m2=1.0, distance_m=1.0, conductivity_W_per_mK=0.0,
                  species_boundaries=sb if sb is not None else (SpeciesBoundary(), SpeciesBoundary()),
                  mechanism=mech)


def _ab_mech(k_f=2.0, k_r=1.0):
    # A <-> B elementary; X carries A and B; detailed balance at c* with k_f c*_A = k_r c*_B.
    return Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X", "charge"),
                     [[1, 1], [0, 0]], (ReactionRate(k_f=k_f, k_r=k_r, reversible=True),))


def _state(system, n, T=(300.0, 300.0)):
    return State.make(system, np.array(n, float), list(T))


# ---- the analytical derivative IS the proof (checked without a time integrator) -----------------------------
def test_analytical_derivative_equals_sum_of_closed_forms_and_is_nonpositive():
    system = _sys(_ab_mech(), V=(1.0, 1.0), D=(0.15, 0.25))
    cstar = np.array([1.0, 2.0])
    assert is_detailed_balance_equilibrium(system, cstar)                 # v_f(c*) = v_r(c*)
    s = _state(system, [[2.0, 1.0], [0.5, 2.5]])                          # positive, unequal across the face
    lhs = dPhi_dt_chain_rule(system, s, cstar)                            # grad Phi . (dc/dt), generic
    rhs = diffusion_dissipation_rate(system, s) + reaction_dissipation_rate(system, s, cstar)  # proved closed forms
    assert lhs == pytest.approx(rhs, abs=1e-9)                            # the proof's algebra, numerically
    assert lhs <= 1e-12                                                   # closed passive world: dPhi/dt <= 0


def test_finite_difference_corroborates_the_analytical_rate():
    system = _sys(_ab_mech(), V=(1.0, 1.0), D=(0.15, 0.25))
    cstar = np.array([1.0, 2.0])
    s = _state(system, [[2.0, 1.0], [0.5, 2.5]])
    rate = total_dissipation_rate(system, s, cstar)
    phi0 = relative_free_energy(system, s, cstar)
    fd = None
    for dt in (1e-3, 1e-4, 1e-5):                                         # refine: (Phi(dt)-Phi(0))/dt -> dPhi/dt
        s1, _ = transport_step(system, s, dt)
        s1, _ = reaction_step(system, s1, dt, settings=SolverSettings())
        fd = (relative_free_energy(system, s1, cstar) - phi0) / dt
    assert fd == pytest.approx(rate, rel=0.05, abs=1e-6)                  # a real sign, not an integration artifact


# ---- C1: detailed-balanced reaction relaxes Phi monotonically to 0 ------------------------------------------
def test_detailed_balanced_reaction_decreases_phi_monotonically_toward_zero():
    system = _sys(_ab_mech(), D=(0.0, 0.0))                               # isolate the reaction
    cstar = np.array([1.0, 2.0])                                         # ODE equilibrium of a closed A<->B, total 3
    s = _state(system, [[3.0, 0.0], [3.0, 0.0]])                         # far from equilibrium, same total
    phis = [relative_free_energy(system, s, cstar)]
    for _ in range(8):
        s, _ = reaction_step(system, s, 0.3)
        phis.append(relative_free_energy(system, s, cstar))
    assert all(phis[i + 1] <= phis[i] + 1e-9 for i in range(len(phis) - 1))   # non-increasing
    assert phis[-1] < phis[0] and phis[-1] < 1e-3                             # relaxes toward c* (Phi -> 0)


# ---- C2: zero at equal compartments, strict otherwise -------------------------------------------------------
def test_identical_compartments_have_exactly_zero_diffusive_dissipation():
    system = _sys(D=(0.3, 0.1))
    assert diffusion_dissipation_rate(system, _state(system, [[2.0, 1.0], [2.0, 1.0]])) == 0.0


def test_unequal_concentrations_strictly_dissipate():
    system = _sys(D=(0.3, 0.1))
    assert diffusion_dissipation_rate(system, _state(system, [[3.0, 1.0], [1.0, 2.0]])) < 0.0


# ---- C3: discrete monotonicity, including unequal cell volumes ----------------------------------------------
def test_discrete_diffusion_step_never_increases_phi_even_with_unequal_volumes():
    system = _sys(V=(1.0, 3.0), D=(0.2, 0.2))
    n0 = np.array([[3.0, 0.5], [0.3, 2.0]])
    s = _state(system, n0)
    cstar = n0.sum(axis=0) / sum(system.volumes_m3)                      # closed-diffusion uniform equilibrium
    phi0 = relative_free_energy(system, s, cstar)
    s1, _ = transport_step(system, s, system.transport_dt_max() * 0.9)   # supported positivity-preserving step
    assert relative_free_energy(system, s1, cstar) <= phi0 + 1e-12


# ---- anti-diffusion: conserves matter, violates dissipation (red-team #7) -----------------------------------
def test_anti_diffusion_conserves_matter_but_increases_phi():
    def anti(coef, x_self, x_other, side):
        return coef * (x_self - x_other)                                 # uphill: antisymmetric (conserves), anti-dissipative

    system = _sys(V=(1.0, 1.0), D=(0.1, 0.1))
    n0 = np.array([[3.0, 1.0], [1.0, 3.0]])
    s = _state(system, n0)
    cstar = n0.sum(axis=0) / sum(system.volumes_m3)                      # uniform reference
    phi0 = relative_free_energy(system, s, cstar)
    led = Ledger()
    s1, _ = transport_step(system, s, system.transport_dt_max() * 0.3, flux_fn=anti, ledger=led)
    assert audit(system, s, s1, led)["inventory_residual"] < 1e-12       # matter conserved...
    assert relative_free_energy(system, s1, cstar) > phi0                # ...yet Phi ROSE (conservation != dissipation)


# ---- a driven/open system legitimately escapes the closed theorem -------------------------------------------
def test_driven_open_system_is_outside_the_closed_theorem():
    sb = (SpeciesBoundary(kind="prescribed_flow", flow_mol_per_s=(1.0, 0.0)), SpeciesBoundary())
    system = _sys(D=(0.0, 0.0), sb=sb)
    cstar = np.array([2.0, 2.0])
    s = _state(system, [[2.0, 2.0], [2.0, 2.0]])                         # start AT c* (Phi minimal)
    phi0 = relative_free_energy(system, s, cstar)
    s1, _ = transport_step(system, s, 0.1)                               # external pump drives A into cell 0
    assert relative_free_energy(system, s1, cstar) > phi0                # Phi rose: driven, not covered by the law


# ---- near-zero concentration: the log limit is handled explicitly -------------------------------------------
def test_near_zero_concentration_log_limit_is_handled():
    system = _sys(D=(0.1, 0.1))
    r = diffusion_dissipation_rate(system, _state(system, [[1e-9, 1.0], [1.0, 1.0]]))
    assert r <= 0.0 and np.isfinite(r)
    assert diffusion_dissipation_rate(system, _state(system, [[0.0, 1.0], [0.0, 1.0]])) == 0.0   # 0*log0 -> 0, not nan


# ---- the reaction law refuses to certify dissipation without a detailed-balanced reference (ties to B3) -----
def test_reaction_dissipation_refuses_without_a_detailed_balanced_reference():
    system = _sys(_ab_mech(k_f=2.0, k_r=1.0), D=(0.0, 0.0))
    bad = np.array([1.0, 1.0])                                           # k_f*1 != k_r*1: not detailed balance
    assert not is_detailed_balance_equilibrium(system, bad)
    with pytest.raises(ValueError):
        reaction_dissipation_rate(system, _state(system, [[2.0, 1.0], [2.0, 1.0]]), bad)


def test_empirical_kinetics_are_refused_by_the_reaction_dissipation_theorem():
    # evil-morty KILL 1: an EMPIRICAL (non-elementary) law with a detailed-balanced c* must NOT receive a
    # dissipation verdict -- the closed form -(v_f-v_r)log(v_f/v_r) is derived from orders == complexes and
    # INVERTS the sign otherwise (the module reported dPhi/dt = -0.575 while Phi rose at +0.811).
    mech = Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X", "charge"), [[1, 1], [0, 0]],
                     (ReactionRate(k_f=1.0, k_r=1.0, reversible=True),),
                     kinetics="empirical", forward_orders=[[2.0], [0.0]], reverse_orders=[[0.0], [1.0]])
    system = _sys(mech, D=(0.0, 0.0))
    cstar = np.array([1.0, 1.0])
    assert is_detailed_balance_equilibrium(system, cstar)               # v_f(c*)=1*1^2 == v_r(c*)=1*1 -> True
    s = _state(system, [[2.0, 3.0], [2.0, 3.0]])
    with pytest.raises(ValueError):                                     # elementary hypothesis now ENFORCED
        reaction_dissipation_rate(system, s, cstar)
    with pytest.raises(ValueError):
        total_dissipation_rate(system, s, cstar)


# ======================================================================================================
# Round IV -- C1/C2 hardening: zero-diffusivity limit + open-system passivity refusal.
# ======================================================================================================
def test_RIV_C1_zero_diffusivity_and_zero_concentration_limits():
    # (a) zero diffusivity, nonzero concentration difference -> EXACTLY 0 (no flux, no dissipation; never NaN)
    sysz = System(("A",), (1.0, 1.0), (1.0, 1.0), (0.0,), area_m2=1.0, distance_m=1.0, conductivity_W_per_mK=0.0)
    r = diffusion_dissipation_rate(sysz, State.make(sysz, [[1.0], [0.0]], [300.0, 300.0]))
    assert r == 0.0 and not np.isnan(r)
    # (b) positive diffusivity, a zero-concentration region -> ideal-dilute log singularity: -inf, still <= 0
    sysp = System(("A",), (1.0, 1.0), (1.0, 1.0), (1.0,), area_m2=1.0, distance_m=1.0, conductivity_W_per_mK=0.0)
    rp = diffusion_dissipation_rate(sysp, State.make(sysp, [[1.0], [0.0]], [300.0, 300.0]))
    assert rp == -np.inf and rp <= 0.0
    # (c) equal concentrations, both zero -> 0
    r0 = diffusion_dissipation_rate(sysp, State.make(sysp, [[0.0], [0.0]], [300.0, 300.0]))
    assert r0 == 0.0
    # (d) a species that is immobile (g=0) does not poison a mobile one's finite dissipation
    sysm = System(("A", "B"), (1.0, 1.0), (1.0, 1.0), (0.0, 1.0), area_m2=1.0, distance_m=1.0,
                  conductivity_W_per_mK=0.0)
    rm = diffusion_dissipation_rate(sysm, State.make(sysm, [[1.0, 2.0], [0.0, 1.0]], [300.0, 300.0]))
    assert np.isfinite(rm) and rm <= 0.0            # A (g=0, empty cell) contributes 0; B contributes finite < 0


def test_RIV_C1_nonfinite_concentration_is_refused():
    # a real State is already finite-checked at construction; the dissipation guard is defense-in-depth against a
    # duck-typed caller, exercised here with a minimal mock whose concentration() returns a non-finite value.
    class _Sys:
        g = np.array([1.0])

    class _St:
        def concentration(self, system):
            return np.array([[np.inf], [1.0]])

    with pytest.raises(InvalidParameterError):
        diffusion_dissipation_rate(_Sys(), _St())


def test_RIV_C2_externally_driven_species_cannot_be_certified_passive():
    sb = (SpeciesBoundary("prescribed_flow", (0.5,)), SpeciesBoundary())
    syso = System(("A",), (1.0, 1.0), (1.0, 1.0), (1.0,), area_m2=1.0, distance_m=1.0, conductivity_W_per_mK=0.0,
                  species_boundaries=sb)
    sto = State.make(syso, [[1.0], [1.0]], [300.0, 300.0])
    assert is_closed_passive(syso) is False
    with pytest.raises(InvalidParameterError):
        total_dissipation_rate(syso, sto, [1.0])                     # no closed-passivity certificate for an open system
    # ...but the labelled INTERNAL diffusion contribution is still available and makes no whole-system claim:
    assert diffusion_dissipation_rate(syso, sto) <= 0.0


def test_RIV_C2_thermal_drive_breaks_passivity_certificate():
    syst = System(("A",), (1.0, 1.0), (1.0, 1.0), (1.0,), area_m2=1.0, distance_m=1.0, conductivity_W_per_mK=0.0,
                  thermal_boundaries=(ThermalBoundary("heater", power_W=5.0), ThermalBoundary()))
    assert is_closed_passive(syst) is False
    with pytest.raises(InvalidParameterError):
        total_dissipation_rate(syst, State.make(syst, [[1.0], [2.0]], [300.0, 300.0]), [1.0])
