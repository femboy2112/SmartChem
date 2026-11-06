"""OPERATION XV Wave D -- the ammonia / ammonium aqueous equilibrium solver (NH3 / NH4+ / H+ / OH-).

A DISTINCT chemistry from the acetate work: a weak BASE buffer.  Given a total ammonia inventory and an optional net
strong base (NaOH) and/or strong acid (HCl / the chloride of NH4Cl), it speciates NH3 / NH4+ / H+ / OH- at
equilibrium on the IDEAL concentration standard state (activities == concentrations), consistent with the rest of the
XV kinetic kernel (whose kf/kr is the concentration quotient Kc, not an activity-based K-degree).  Davies/activity
corrections are a declared P4 extension, not faked here.

THE EQUATIONS (h = [H+], T_N = total ammonia, S = strong_base - strong_acid):
    Ka  = [NH3][H+] / [NH4+]                       (pKa(NH4+) = 9.25, sourced tertiary)
    Kw  = [H+][OH-]                                 (1e-14)
    mass:   [NH3] + [NH4+] = T_N
    charge: [NH4+] + [H+] + strong_base = [OH-] + strong_acid
with  [NH4+] = T_N h/(h+Ka),  [NH3] = T_N Ka/(h+Ka),  [OH-] = Kw/h, the charge balance is one equation in h:
    f(h) = T_N h/(h+Ka) + h + S - Kw/h = 0,
strictly increasing in h (so the physical root is unique), equivalently the cubic
    h^3 + (T_N + Ka + S) h^2 + (S Ka - Kw) h - Kw Ka = 0.

TWO INDEPENDENT ROUTES (the NUMERICALLY_VERIFIED discipline, section 1 claim-tier ladder): a bracketed transcendental
root-find on f(h) (scipy.brentq) AND the algebraic cubic root (numpy.roots), refined by one high-precision Newton step
on the cubic so the polynomial route does not lose the tiny physical root to coefficient scaling.  Agreement of the
two routes earns NUMERICALLY_VERIFIED; a disagreement, or a residual that does not close, is REFUSED.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

# ---- sourced tertiary constants (25 C); used to SET equilibria, exactly as the acetate work used its Ka ----
PKA_NH4 = 9.25
KA_NH4 = 10.0 ** (-PKA_NH4)
PKW = 14.0
KW = 10.0 ** (-PKW)

# The constants above are a 25 C record and nothing in here corrects them for temperature.  An untreated patient
# can't be sent home at 373 K with a 298 K prescription -- so the admitted band is the only temperature we may answer.
SOURCE_T_K = 298.15            # the temperature pKa(NH4+)=9.25 / pKw=14.0 are tabulated at (25 C)
SOURCE_T_TOL_K = 0.01          # admitted band around the source temperature; outside => OUT OF SOURCE DOMAIN


def _require_source_temperature(T_K: float) -> None:
    """XVIII-8 defect 1 (mirrors aqueous_equilibrium._require_source_temperature).  The Ka/Kw records are 25 C only
    and solve() never corrects them, so any temperature outside the sourced band is refused -- fail closed, out of
    source domain -- rather than silently handed a 25 C answer wearing a different temperature's label."""
    if not math.isfinite(T_K):
        raise AmmoniaError("temperature_K must be finite")
    if abs(T_K - SOURCE_T_K) > SOURCE_T_TOL_K:
        raise AmmoniaError(
            f"temperature {T_K} K is outside the sourced-data domain {SOURCE_T_K} +/- {SOURCE_T_TOL_K} K; "
            f"pKa(NH4+)=9.25 / pKw=14.0 are 25 C records, so this is refused (fail closed) rather than extrapolated")

SOLVED_IDEAL = "SOLVED_IDEAL"
REFUSED_VERDICT = "REFUSED"
VERDICTS = frozenset({SOLVED_IDEAL, REFUSED_VERDICT})


class AmmoniaError(ValueError):
    """Fail-closed error for the ammonia equilibrium solver."""


@dataclass(frozen=True)
class AmmoniaWaterSystem:
    """A declared ammonia speciation problem (concentration basis, mol/L)."""
    total_ammonia_M: float
    strong_base_M: float = 0.0        # net strong base (e.g. NaOH), Na+ spectator, >= 0
    strong_acid_M: float = 0.0        # net strong acid (e.g. HCl / NH4Cl's Cl-), Cl- spectator, >= 0
    temperature_K: float = 298.15

    def __post_init__(self):
        for nm, v in (("total_ammonia_M", self.total_ammonia_M), ("strong_base_M", self.strong_base_M),
                      ("strong_acid_M", self.strong_acid_M)):
            if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise AmmoniaError(f"{nm} must be a finite mol/L value >= 0")
        if isinstance(self.temperature_K, bool) or not (isinstance(self.temperature_K, (int, float))
                                                        and math.isfinite(self.temperature_K) and self.temperature_K > 0):
            raise AmmoniaError("temperature_K must be a finite temperature > 0")
        # XVIII-8 defect 1: finite>0 was the ONLY check -- T was then never read in solve(), so 373 K and 1 K both
        # returned the 25 C pH.  Pin the system to the sourced-data band at construction; off-domain is now fatal.
        _require_source_temperature(float(self.temperature_K))


@dataclass(frozen=True)
class AmmoniaResult:
    nh3_M: float
    nh4_M: float
    h_M: float
    oh_M: float
    na_M: float
    cl_M: float
    pH: float
    charge_balance_residual: float
    mass_balance_residual: float
    solver_agreement_residual: float     # |h_route1 - h_route2| / h  -- two INDEPENDENT routes
    ionic_strength_M: float
    verdict: str
    tier: str
    caveats: tuple = field(default_factory=tuple)


# XVIII-8 defect 3: scale-aware closure tolerance, matching the XVII sandbox projection policy -- atol + rtol*scale
# with NO 1-mol floor.  The old `1e-9 * max(1.0, scale)` pinned a whole mole of absolute slack, so a trace-scale
# system (micromoles, picomoles) was graded against a tolerance a trillion times its own inventory.  The floor is
# the anesthetic that let a dead-on-arrival solve look like it closed; removed.
_CLOSE_ATOL = 1e-12
_CLOSE_RTOL = 1e-9


def _closure_tol(scale: float) -> float:
    """Absolute tolerance a balance residual must beat to count as closed: atol + rtol*scale, scale = actual inventory."""
    return _CLOSE_ATOL + _CLOSE_RTOL * scale


def _charge_residual(h: float, T_N: float, S: float, Ka: float, Kw: float) -> float:
    return T_N * h / (h + Ka) + h + S - Kw / h


def _cubic_newton_refine(h0: float, T_N: float, S: float, Ka: float, Kw: float, iters: int = 60) -> float:
    """Refine a root of  h^3 + (T_N+Ka+S) h^2 + (S Ka - Kw) h - Kw Ka = 0  by Newton from h0 (independent of brentq)."""
    b, c, d = T_N + Ka + S, S * Ka - Kw, -Kw * Ka
    h = h0
    for _ in range(iters):
        fh = ((h + b) * h + c) * h + d
        dfh = (3.0 * h + 2.0 * b) * h + c
        if dfh == 0.0:
            break
        step = fh / dfh
        h -= step
        if h <= 0.0:
            h = h0 * 0.5
        if abs(step) <= 1e-18 * max(h, 1e-30):
            break
    return h


def solve(system: AmmoniaWaterSystem) -> AmmoniaResult:
    T_N = float(system.total_ammonia_M)
    strong_base = float(system.strong_base_M)
    strong_acid = float(system.strong_acid_M)
    S = strong_base - strong_acid
    Ka, Kw = KA_NH4, KW

    # ROUTE 1: bracketed transcendental root of the charge balance (monotone increasing -> unique root)
    lo, hi = 1e-20, 1e6
    try:
        h1 = brentq(lambda h: _charge_residual(h, T_N, S, Ka, Kw), lo, hi, xtol=1e-300, rtol=8.9e-16, maxiter=300)
    except Exception as exc:
        raise AmmoniaError(f"charge-balance root-find failed: {exc}") from None

    # ROUTE 2: algebraic cubic root (numpy), refined by an independent Newton so the tiny root survives coeff scaling
    coeffs = [1.0, T_N + Ka + S, S * Ka - Kw, -Kw * Ka]
    roots = np.roots(coeffs)
    real_pos = [float(r.real) for r in roots if abs(r.imag) <= 1e-12 * max(1.0, abs(r.real)) and r.real > 0.0]
    degenerate_caveat = None
    if real_pos:
        seed = min(real_pos, key=lambda r: abs(math.log10(r) - math.log10(h1)))
        h2 = _cubic_newton_refine(seed, T_N, S, Ka, Kw)
        agreement = abs(h1 - h2) / h1 if h1 > 0 else float("inf")
    else:
        # XVIII-8 defect 2: the algebraic cubic found NO independent real-positive root.  The old code seeded Newton
        # from h1 -- route 1's own answer -- and reported the result as a second witness, so "routes agree" was really
        # route 1 agreeing with itself.  A cross-check that borrows the thing it checks isn't a cross-check.  Refuse
        # the independence claim outright: no witness, no agreement.
        h2 = float("nan")
        agreement = float("inf")
        degenerate_caveat = ("independent cross-check degenerated: the algebraic cubic route found no real-positive "
                             "root, so there is NO independent witness; refusing to call a Newton polish of route 1's "
                             "own root an agreement (this would be CIRCULAR)")

    h = h1
    nh4 = T_N * h / (h + Ka)
    nh3 = T_N * Ka / (h + Ka)
    oh = Kw / h
    charge_res = abs(nh4 + h + strong_base - oh - strong_acid)
    mass_res = abs((nh3 + nh4) - T_N)
    ionic = 0.5 * (nh4 + h + oh + strong_base + strong_acid)   # all species monovalent

    # XVIII-8 defect 3: scale is the ACTUAL inventory, graded by atol + rtol*scale with no 1-mol floor.
    scale = T_N + strong_base + strong_acid
    tol = _closure_tol(scale)
    ok = (agreement < 1e-8 and charge_res < tol and mass_res < tol
          and math.isfinite(h) and h > 0)
    verdict = SOLVED_IDEAL if ok else REFUSED_VERDICT
    # two INDEPENDENT routes (transcendental bracket + algebraic cubic Newton) agreeing -> NUMERICALLY_VERIFIED
    tier = "NUMERICALLY_VERIFIED" if ok else "REFUSED"
    caveats = ()
    if degenerate_caveat is not None:
        caveats += (degenerate_caveat,)
    if not ok:
        caveats += (f"ammonia solve did not close (agreement {agreement:.2e}, charge {charge_res:.2e}, "
                    f"mass {mass_res:.2e}); refusing",)
    caveats += ("ideal concentration standard state (activities == concentrations); Davies/activity is a declared "
                "P4 extension",)
    return AmmoniaResult(
        nh3_M=nh3, nh4_M=nh4, h_M=h, oh_M=oh, na_M=strong_base, cl_M=strong_acid,
        pH=-math.log10(h) if h > 0 else float("nan"), charge_balance_residual=charge_res,
        mass_balance_residual=mass_res, solver_agreement_residual=agreement, ionic_strength_M=ionic,
        verdict=verdict, tier=tier, caveats=caveats)
