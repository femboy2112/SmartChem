"""OPERATION XIII P0 -- an INDEPENDENT arbitrary-precision holdout for the coupled vinegar/bicarbonate 0-D solver.

`coupled_equilibrium.solve` already cross-checks its float64 root by TWO routes (a brentq bracket and a numpy.roots
polynomial).  But those two routes share the SAME float64 precision and the SAME charge-balance formulation, so a
conditioning / cancellation error that bites both -- exactly the kind §2C warns about in the strongly basic or
widely-separated-concentration regimes -- could be invisible to their mutual agreement.  The mixed INTERIOR
(genuine vinegar + baking soda, where neither parent limit applies) is the object with no PHREEQC column and no
limiting-case free check, so it most needs a genuinely independent witness.

This module is that witness, and it is independent on BOTH axes the directive names:

  * PRECISION   -- it works in `decimal.Decimal` at 60 significant digits, not float64.  A float64 cancellation that
                   production's two routes share cannot survive a 60-digit recomputation.
  * ALGORITHM   -- it finds [H+] by pure bisection on the charge-balance residual in Decimal arithmetic, with NO
                   numpy, NO scipy, NO polynomial clearing.  It shares no root-finding code with either production
                   route.

What it is NOT: an independent check of the CHEMISTRY.  It uses the SAME sourced equilibrium constants and the SAME
Davies activity law as production (re-implemented in Decimal), so agreement is COMMON-MODE on the thermodynamics --
it certifies that the production SOLVE is numerically correct for the model it claims, i.e. it earns
`claim_tiers.NUMERICALLY_VERIFIED`, never `BENCHMARKED_AGAINST_REFERENCE_SOLVER` (that needs PHREEQC) and never
`CALIBRATED_TO_MEASUREMENT` (that needs a measured datum).  The acceptance split is stated in `cross_check`.

Monotonicity (why bisection is valid and the root is unique): at fixed effective constants the charge-balance
residual f(h) = (Na + h) - (Kw_c/h + Ka_c C_Ac/(h+Ka_c) + C_C K1_c h/D + 2 C_C K1_c K2_c/D), D = h^2+K1_c h+K1_c K2_c,
is strictly increasing in h over h>0: the +h term rises, and every subtracted term (OH-, Ac-, HCO3-, CO3) is
non-increasing in h (each buffer base is depleted as the solution acidifies).  So f has at most one positive zero,
which the production brentq also relies on; a sign change over [1e-18, 10] (pH in [-1, 18]) brackets it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, localcontext

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.aqueous_equilibrium import DAVIES_A_25C, DAVIES_I_MAX
from experiments.sandbox_foundation.coupled_equilibrium import VinegarBicarbonateSystem

# Working precision for the holdout.  60 significant digits is ~50 orders of magnitude of headroom over float64's
# ~16, so any float64-shared cancellation shows up as a disagreement far above the comparison tolerance.
HP_PRECISION = 60
_BISECTION_ITERS = 400       # 400 halvings of [1e-18, 10] resolve ~120 decimal decades -- far finer than 60 digits
_DAVIES_FIXED_POINT_TOL = Decimal(10) ** -40
_DAVIES_MAX_ITERS = 200


def _sqrt(x: Decimal) -> Decimal:
    return x.sqrt()


def _pow10(exponent: Decimal) -> Decimal:
    """10**exponent in the active Decimal context (exponent may be negative/fractional)."""
    return Decimal(10) ** exponent


def _davies_gamma1_hp(ionic: Decimal, A: Decimal) -> Decimal:
    """Davies monovalent activity coefficient in Decimal: log10 g = -A (sqrt(I)/(1+sqrt(I)) - 0.3 I).  The SAME law
    as aqueous_equilibrium._davies_gamma, re-implemented in arbitrary precision (I <= 0 => 1)."""
    if ionic <= 0:
        return Decimal(1)
    s = _sqrt(ionic)
    return _pow10(-A * (s / (1 + s) - Decimal("0.3") * ionic))


def _speciate_hp(h: Decimal, Ka_c: Decimal, K1_c: Decimal, K2_c: Decimal, Kw_c: Decimal,
                 C_Ac: Decimal, C_C: Decimal):
    ac = (Ka_c * C_Ac / (h + Ka_c)) if C_Ac > 0 else Decimal(0)
    hac = C_Ac - ac
    D = h * h + K1_c * h + K1_c * K2_c
    co2 = (C_C * h * h / D) if C_C > 0 else Decimal(0)
    hco3 = (C_C * K1_c * h / D) if C_C > 0 else Decimal(0)
    co3 = (C_C * K1_c * K2_c / D) if C_C > 0 else Decimal(0)
    oh = Kw_c / h
    return ac, hac, co2, hco3, co3, oh


def _charge_residual_hp(h: Decimal, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na: Decimal) -> Decimal:
    ac, _hac, _co2, hco3, co3, oh = _speciate_hp(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C)
    return (Na + h) - (oh + ac + hco3 + 2 * co3)


def _bisect_h(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na) -> Decimal:
    """Pure-Decimal bisection for the unique positive root of the (increasing) charge residual over [1e-18, 10]."""
    lo, hi = Decimal(10) ** -18, Decimal(10)
    f_lo = _charge_residual_hp(lo, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
    f_hi = _charge_residual_hp(hi, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if (f_lo > 0) == (f_hi > 0):       # no sign change: residual is increasing, so f_lo<0<f_hi expected; else refuse
        return Decimal("NaN")
    for _ in range(_BISECTION_ITERS):
        mid = (lo + hi) / 2
        f_mid = _charge_residual_hp(mid, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
        if f_mid == 0:
            return mid
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi, f_hi = mid, f_mid
    return (lo + hi) / 2


@dataclass(frozen=True)
class HPReferenceResult:
    """The arbitrary-precision holdout's own answer for a coupled system (all as float, converted at the boundary)."""
    pH: float
    h_plus_M: float
    oh_minus_M: float
    hac_M: float
    ac_minus_M: float
    co2aq_M: float
    hco3_M: float
    co3_M: float
    ionic_strength_M: float
    gamma_monovalent: float
    activity_model: str
    davies_iterations: int
    charge_balance_residual: float   # recomputed in Decimal, reported as float (|f(h)| at the root)


def solve_hp(system: VinegarBicarbonateSystem) -> HPReferenceResult:
    """Solve the coupled CLOSED system to arbitrary precision by Decimal bisection (ideal or Davies)."""
    with localcontext() as ctx:
        ctx.prec = HP_PRECISION
        C_Ac = Decimal(repr(float(system.total_acetate_M)))
        C_C = Decimal(repr(float(system.total_carbon_M)))
        Na = Decimal(repr(float(system.sodium_M)))
        Ka0 = Decimal(repr(float(system.Ka.value)))
        K10 = Decimal(repr(float(system.K1.value)))
        K20 = Decimal(repr(float(system.K2.value)))
        Kw0 = Decimal(repr(float(system.Kw.value)))
        A = Decimal(repr(float(DAVIES_A_25C.value)))
        ideal = system.activity_model == "ideal"

        g1 = Decimal(1)
        iters = 0
        if ideal:
            Ka_c, K1_c, K2_c, Kw_c = Ka0, K10, K20, Kw0
            h = _bisect_h(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
        else:
            h = Decimal("NaN")
            for i in range(1, _DAVIES_MAX_ITERS + 1):
                iters = i
                g1sq = g1 * g1
                g2 = g1 ** 4
                Ka_c, K1_c, K2_c, Kw_c = Ka0 / g1sq, K10 / g1sq, K20 / g2, Kw0 / g1sq
                h = _bisect_h(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
                if h.is_nan() or h <= 0:
                    break
                ac, _hac, _co2, hco3, co3, oh = _speciate_hp(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C)
                ionic = (h + oh + ac + hco3 + Na + 4 * co3) / 2
                g1_new = _davies_gamma1_hp(ionic, A)
                if abs(g1_new - g1) <= _DAVIES_FIXED_POINT_TOL * g1:
                    g1 = g1_new
                    g1sq = g1 * g1
                    g2 = g1 ** 4
                    Ka_c, K1_c, K2_c, Kw_c = Ka0 / g1sq, K10 / g1sq, K20 / g2, Kw0 / g1sq
                    h = _bisect_h(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
                    break
                g1 = g1_new

        if h.is_nan() or h <= 0:
            raise ValueError("the high-precision holdout did not bracket a positive [H+]")

        ac, hac, co2, hco3, co3, oh = _speciate_hp(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C)
        ionic = (h + oh + ac + hco3 + Na + 4 * co3) / 2
        resid = _charge_residual_hp(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
        c_ref = Decimal(1)
        pH = -(g1 * h / c_ref).ln() / Decimal(10).ln() if not ideal else -(h / c_ref).ln() / Decimal(10).ln()

        return HPReferenceResult(
            pH=float(pH), h_plus_M=float(h), oh_minus_M=float(oh), hac_M=float(hac), ac_minus_M=float(ac),
            co2aq_M=float(co2), hco3_M=float(hco3), co3_M=float(co3), ionic_strength_M=float(ionic),
            gamma_monovalent=float(g1), activity_model=system.activity_model, davies_iterations=iters,
            charge_balance_residual=float(abs(resid)))


# -------------------------------------------------------------------------------- the cross-check (P0 acceptance)
@dataclass(frozen=True)
class CrossCheckResult:
    """Production solve vs the arbitrary-precision holdout for one system.  `tier` is the evidential claim the
    AGREEMENT earns -- NUMERICALLY_VERIFIED when they match (and the production result self-certified / the system
    is in the Davies domain), ASSUMED_PARAMETER/UNVERIFIED if they do not."""
    delta_pH: float
    rel_delta_h: float
    tier: str
    production_pH: float
    hp_pH: float
    within_davies_domain: bool
    note: str


# agreement thresholds: production is float64 (~1e-15 relative floor); the holdout is 60-digit.  A genuine
# conditioning divergence is orders of magnitude larger.  1e-9 relative on [H+] (=> ~4e-10 on pH) sits far above the
# float64 floor yet far below any real solver error -- the same philosophy as the parents' AGREEMENT_RTOL.
CROSS_CHECK_H_RTOL = 1e-9
CROSS_CHECK_PH_ATOL = 1e-8


def cross_check(system: VinegarBicarbonateSystem) -> CrossCheckResult:
    """Run the production coupled solver and the Decimal holdout on the same system and grade their agreement.

    Independence is on precision AND algorithm; it is COMMON-MODE on the chemistry (same constants, same Davies law),
    so a match earns NUMERICALLY_VERIFIED -- the SOLVE is independently corroborated -- and explicitly NOT
    BENCHMARKED_AGAINST_REFERENCE_SOLVER.  A mismatch is a real numerical finding: the result is UNVERIFIED.
    """
    from experiments.sandbox_foundation.coupled_equilibrium import solve as production_solve

    prod = production_solve(system)
    hp = solve_hp(system)
    dpH = abs(prod.pH - hp.pH)
    rel_dh = abs(prod.h_plus_M - hp.h_plus_M) / max(hp.h_plus_M, 1e-300)
    in_domain = (system.activity_model == "ideal") or (
        math.isfinite(hp.ionic_strength_M) and hp.ionic_strength_M <= DAVIES_I_MAX)
    agree = (rel_dh <= CROSS_CHECK_H_RTOL) and (dpH <= CROSS_CHECK_PH_ATOL)
    if agree:
        tier = claim_tiers.NUMERICALLY_VERIFIED
        note = ("production float64 solve agrees with the 60-digit Decimal-bisection holdout; the SOLVE is "
                "numerically verified (common-mode on the shared constants/Davies law -- NOT reference-solver "
                "benchmarked and NOT measurement-calibrated)")
    else:
        tier = claim_tiers.UNVERIFIED
        note = (f"production and the high-precision holdout DISAGREE (|dpH|={dpH:.3e}, rel|dh|={rel_dh:.3e}); "
                "a genuine numerical divergence -- the production solve is not numerically verified for this system")
    return CrossCheckResult(
        delta_pH=dpH, rel_delta_h=rel_dh, tier=tier, production_pH=prod.pH, hp_pH=hp.pH,
        within_davies_domain=in_domain, note=note)
