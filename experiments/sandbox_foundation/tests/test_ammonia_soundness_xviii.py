"""OPERATION XVIII section 8 -- the ammonia-equilibrium soundness repairs.

Three defects the scout verified in ammonia_equilibrium.py, each now pinned to its CURED behaviour:

  1. NO temperature-domain guard -- temperature_K was validated finite>0 then never read, so 298.15 / 373.15 / 1.0 K
     all returned the 25 C pH.  Now an off-domain temperature is fatal at construction (fail closed, out of source
     domain), because pKa(NH4+)=9.25 / pKw=14.0 are a 25 C record and solve() never corrects them.
  2. A silent CIRCULAR fallback -- when the algebraic cubic (route 2) found no real-positive root the code seeded
     Newton from h1 (route 1's own root), so the "two routes agree" cross-check was route 1 agreeing with itself.
     Now the degeneration refuses the independence claim and carries a loud caveat.
  3. A 1-mol-floor tolerance -- the closure gate was `1e-9 * max(1.0, scale)`, a whole mole of absolute slack, so a
     trace-scale system was graded against a tolerance a trillion times its own inventory.  Now atol + rtol*scale,
     no floor, scale = the actual inventory.
"""
import math

import numpy as np
import pytest

from experiments.sandbox_foundation import ammonia_equilibrium
from experiments.sandbox_foundation.ammonia_equilibrium import (
    REFUSED_VERDICT,
    SOLVED_IDEAL,
    SOURCE_T_K,
    SOURCE_T_TOL_K,
    AmmoniaError,
    AmmoniaWaterSystem,
    _closure_tol,
    solve,
)


# ---- Defect 1: temperature-domain guard (fail closed outside the sourced 25 C band) ----

@pytest.mark.parametrize("T", [373.15, 1.0, 310.0, SOURCE_T_K + 10 * SOURCE_T_TOL_K])
def test_temperature_outside_sourced_band_is_refused(T):
    # The constants are a 25 C record and solve() never corrects them; an off-domain T must RAISE, not quietly
    # return the 25 C answer wearing a different temperature's label.
    with pytest.raises(AmmoniaError):
        AmmoniaWaterSystem(0.01, temperature_K=T)


@pytest.mark.parametrize("T", [SOURCE_T_K, SOURCE_T_K + SOURCE_T_TOL_K, SOURCE_T_K - SOURCE_T_TOL_K])
def test_temperature_inside_sourced_band_is_admitted(T):
    r = solve(AmmoniaWaterSystem(0.01, temperature_K=T))
    assert r.verdict == SOLVED_IDEAL


def test_the_old_silent_off_domain_symptom_is_gone():
    # The scout's probe: the same pH at 298.15 and 373.15 was the tell.  373.15 no longer produces a pH at all.
    base = solve(AmmoniaWaterSystem(0.01)).pH
    with pytest.raises(AmmoniaError):
        solve(AmmoniaWaterSystem(0.01, temperature_K=373.15))
    assert 7.0 < base < 12.0   # a basic ammonia solution, as a sanity floor on the in-domain answer


# ---- Defect 2: the independent cross-check must not degenerate into a circular self-check ----

def test_route2_degeneration_refuses_instead_of_falling_back_to_h1(monkeypatch):
    # Force route 2 (np.roots) to yield NO real-positive root.  The old code would seed Newton from h1 and report a
    # near-zero agreement -> a CIRCULAR SOLVED_IDEAL.  The cure: refuse the independence claim, loudly.
    monkeypatch.setattr(ammonia_equilibrium.np, "roots",
                        lambda coeffs: np.array([-1.0 + 0j, -2.0 + 0j, -3.0 + 0j]))
    r = solve(AmmoniaWaterSystem(0.1))
    assert r.verdict == REFUSED_VERDICT
    assert r.tier == "REFUSED"
    assert math.isinf(r.solver_agreement_residual)          # no witness => no finite agreement
    assert any("CIRCULAR" in c and "no real-positive" in c for c in r.caveats)


def test_same_system_is_solved_when_route2_is_genuinely_independent():
    # Control: WITHOUT the sabotage the algebraic cubic has its real-positive root, so the agreement is earned.
    r = solve(AmmoniaWaterSystem(0.1))
    assert r.verdict == SOLVED_IDEAL
    assert r.solver_agreement_residual < 1e-8


# ---- Defect 3: scale-aware closure tolerance, NO 1-mol floor ----

def test_closure_tolerance_has_no_one_mol_floor():
    # Trace-scale inventory: the gate must grade against the inventory, not a floored 1e-9.
    trace_scale = 1e-12
    new_tol = _closure_tol(trace_scale)
    old_floored_tol = 1e-9 * max(1.0, trace_scale)          # the removed behaviour
    assert new_tol < old_floored_tol
    assert new_tol < 1e-10                                   # a 1e-10 trace imbalance is now CAUGHT (exceeds tol)...
    assert old_floored_tol >= 1e-10                          # ...whereas the old floor would have waved it through


def test_closure_tolerance_is_scale_aware():
    assert _closure_tol(0.0) == pytest.approx(1e-12)                 # atol only at zero inventory
    assert _closure_tol(1.0) == pytest.approx(1e-12 + 1e-9)          # atol + rtol*scale
    assert _closure_tol(10.0) > _closure_tol(1.0)                    # grows with the inventory it grades


def test_trace_scale_solve_still_closes_legitimately():
    # The genuine picomolar solve still closes (brentq zeroes the charge balance), so the stricter gate is not a
    # false refusal -- it only removes the slack that let a BROKEN trace solve pass.
    r = solve(AmmoniaWaterSystem(1e-12))
    assert r.verdict == SOLVED_IDEAL
    assert r.charge_balance_residual < _closure_tol(1e-12)
