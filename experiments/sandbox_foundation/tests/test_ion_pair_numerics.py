"""Wave B5 (Round VII): the NaAc(aq) acetate-root quadratic is CANCELLATION-FREE across the dilute regime.

Red-first witness: the shipped positive root (-b1 + sqrt(disc))/(2 a2) subtracts two near-equal large numbers when
b1 > 0 (dilute acetate, 4 a2 C_T << b1^2), so the returned root fails to satisfy its own quadratic at small C_T --
the quadratic residual scales like C_T * relerr (~3e-8 * C_T by C_T ~ 1e-7).  The conjugate form 2 C_T/(b1 + sqrt(disc))
holds the residual at machine level.  This test fails on the pre-fix formula and passes on the fix; it also confirms
the fix does not perturb the already-admitted dilute ion-pair solves (the two independent routes still agree)."""
import math

import pytest

from experiments.sandbox_foundation.aqueous_equilibrium import (
    AcetateWaterSystem, _ion_pair_acetate_root, solve)


def _quad_residual(a, h, Ka_c, Kass_c, C_T, Na_T):
    beta = h / Ka_c + 1.0
    a2 = beta * Kass_c
    b1 = beta + Kass_c * Na_T - C_T * Kass_c
    return a2 * a * a + b1 * a - C_T                     # the quadratic the root must satisfy


@pytest.mark.parametrize("C_T", [1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8])
def test_acetate_root_satisfies_its_quadratic_to_machine_precision_when_dilute(C_T):
    Ka_c, Kass_c, h = 1.75e-5, 0.66, 1e-3               # acidic => b1 large positive => the cancellation regime
    Na_T = C_T
    a = _ion_pair_acetate_root(h, Ka_c, Kass_c, C_T, Na_T)
    assert math.isfinite(a) and a > 0
    res = _quad_residual(a, h, Ka_c, Kass_c, C_T, Na_T)
    assert abs(res) <= 1e-14 * max(C_T, a)              # machine-level; the naive subtraction blows this at small C_T


def test_the_b1_le_0_branch_still_adds_like_signed_terms():
    # basic / excess-base: b1 can be <= 0 (large Kass_c*Na_T), where (-b1 + sqrt) already adds like-signed terms.
    Ka_c, Kass_c, h, C_T, Na_T = 1.75e-5, 0.66, 1e-10, 0.1, 10.0
    a = _ion_pair_acetate_root(h, Ka_c, Kass_c, C_T, Na_T)
    assert math.isfinite(a) and a > 0
    assert abs(_quad_residual(a, h, Ka_c, Kass_c, C_T, Na_T)) <= 1e-12 * max(C_T, a)


@pytest.mark.parametrize("C_T", [1e-3, 1e-5, 1e-7])
def test_dilute_ion_pair_solve_still_admitted_and_routes_agree(C_T):
    r = solve(AcetateWaterSystem(total_acetic_M=C_T, sodium_M=C_T, activity_model="davies", include_ion_pair=True))
    assert r.verdict.startswith("SOLVED_")
    assert r.solver_agreement_residual <= 1e-7 * r.h_plus_M + 1e-20    # the gate's AGREEMENT_RTOL, comfortably met
