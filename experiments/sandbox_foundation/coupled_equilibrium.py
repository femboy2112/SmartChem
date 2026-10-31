"""Wave VI-A -- the COUPLED vinegar / bicarbonate zero-dimensional aqueous equilibrium.

The separate acetate (:mod:`aqueous_equilibrium`) and carbonate (:mod:`carbonate_equilibrium`) 0-D solvers
each compute their speciation at a given [H+]. A MIXED vinegar + baking-soda system is NOT the superposition
of their two independently-computed pH values: both families share ONE hydrogen-ion activity and ONE charge
balance. This module couples them -- same sourced constants, same Davies activity model, same two-independent-
routes discipline -- and solves the shared [H+] that closes the combined charge balance.

CONSERVED ANALYTICAL COMPONENTS (closed liquid, fixed total carbon -- the core VI-A case):
    total acetate      C_Ac = [HAc] + [Ac-]
    total inorg carbon C_C  = [CO2(aq)] + [HCO3-] + [CO3(2-)]          (CO2(aq) == H2CO3* lumped)
    sodium             Na   = [Na+]      (conservative cation from NaAc / NaHCO3 / Na2CO3 / NaOH, >= 0)
SPECIES (fixed, explicit; the #105 single-global-charge wall sidestepped by enumeration, as both parents do):
    HAc 0 | Ac- -1 | CO2(aq) 0 | HCO3- -1 | CO3(2-) -2 | H+ +1 | OH- -1 | Na+ +1
EQUILIBRIA (concentration basis, Davies-rescaled): Ka (acetic), K1/K2 (carbonic), Kw.
SHARED CHARGE BALANCE:   [Na+] + [H+] = [OH-] + [Ac-] + [HCO3-] + 2 [CO3(2-)]

Speciation at fixed h (D = h^2 + K1_c h + K1_c K2_c):
    [Ac-]  = Ka_c C_Ac / (h + Ka_c)                 [HAc]  = C_Ac - [Ac-]
    [CO2]  = C_C h^2 / D   [HCO3-] = C_C K1_c h / D  [CO3]  = C_C K1_c K2_c / D
    [OH-]  = Kw_c / h

TWO INDEPENDENT ROUTES (must agree, or the gate refuses):
  Route 1  brentq bisection on the charge-balance residual f(h) above.
  Route 2  the positive real root of the polynomial obtained by clearing h (h+Ka_c) D from f(h) -- a DIFFERENT
           algorithm (companion-matrix eigenvalues), not a re-run of the bracket.

LIMITING-CASE VALIDATION (free, against the already-PHREEQC-benchmarked parents): C_C=0 reduces EXACTLY to
:func:`aqueous_equilibrium.solve`; C_Ac=0 reduces EXACTLY to :func:`carbonate_equilibrium.solve` (closed). The
mixed case is the genuinely new object; a preregistered MIXED PHREEQC benchmark is the documented next step
(PHREEQC is an optional dependency, absent on the committed baseline).

SCIENTIFIC RESTRICTION (inherited, stated loudly): agreement between two numerical routes, or against PHREEQC,
is NUMERICAL-MODEL verification, NOT independent measured-chemistry validation. The NaAc(aq) ion pair is OMITTED
from this coupled base (as the acetate BASE model omits it), so beyond I ~ 0.1 M the result carries the parents'
activity caveat. No measured mixed-system pH datum has been compared; external validation remains UNKNOWN.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from experiments.sandbox_foundation.aqueous_equilibrium import (
    C_REF,
    DAVIES_A_25C,
    DAVIES_FIXED_POINT_TOL,
    DAVIES_I_MAX,
    DAVIES_MAX_ITERS,
    EXTERNAL_VALIDATION_UNAVAILABLE,
    KA_ACETIC_25C,
    KW_25C,
    NUMERICALLY_UNVERIFIED,
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    SOLVED_WITHIN_IDEAL_MODEL,
    BenchmarkObligation,
    InvalidParameterError,
    NumericalVerificationError,
    _require_constant_at_source_state,
    _require_source_temperature,
)
from experiments.sandbox_foundation.carbonate_equilibrium import (
    K1_CARBONIC_25C,
    K2_CARBONIC_25C,
    _effective_constants,
    _gammas,
)

CHARGE_BALANCE_ATOL = 1e-12
NONNEGATIVITY_ATOL = 1e-12
ROUTE_AGREEMENT_RTOL = 1e-6   # |h1-h2| <= this * h : the two routes must agree on [H+]
CONSERVATION_RTOL = 1e-9


@dataclass(frozen=True)
class VinegarBicarbonateSystem:
    """A curated mixed acetate + carbonate (closed, fixed total carbon) system at fixed T.
    total_acetate_M = C_Ac >= 0; total_carbon_M = C_C >= 0; sodium_M = Na+ >= 0;
    activity_model in {'ideal', 'davies'}."""

    total_acetate_M: float = 0.0
    total_carbon_M: float = 0.0
    sodium_M: float = 0.0
    activity_model: str = "davies"
    T_K: float = 298.15
    Ka: object = KA_ACETIC_25C
    K1: object = K1_CARBONIC_25C
    K2: object = K2_CARBONIC_25C
    Kw: object = KW_25C

    def __post_init__(self) -> None:
        for name in ("total_acetate_M", "total_carbon_M", "sodium_M"):
            v = getattr(self, name)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise InvalidParameterError(f"{name} must be finite and >= 0")
        if self.activity_model not in ("ideal", "davies"):
            raise InvalidParameterError("activity_model must be 'ideal' or 'davies'")
        _require_source_temperature(self.T_K)
        for const, role in ((self.Ka, "Ka"), (self.K1, "K1"), (self.K2, "K2"), (self.Kw, "Kw")):
            _require_constant_at_source_state(const, role=role)


@dataclass(frozen=True)
class CoupledSpeciationResult:
    pH: float
    pH_concentration: float
    pH_activity: float
    verdict: str
    h_plus_M: float
    oh_minus_M: float
    hac_M: float
    ac_minus_M: float
    co2aq_M: float
    hco3_M: float
    co3_M: float
    na_plus_M: float
    ionic_strength_M: float
    gamma_monovalent: float
    gamma_divalent: float
    activity_model: str
    solver_agreement_residual: float   # |h_route1 - h_route2|
    charge_balance_residual: float
    carbon_conservation_residual: float
    acetate_conservation_residual: float
    davies_iterations: int
    caveats: tuple = field(default_factory=tuple)


def _speciate(h: float, Ka_c: float, K1_c: float, K2_c: float, Kw_c: float, C_Ac: float, C_C: float):
    """Every species concentration at fixed [H+] = h and fixed effective constants."""
    ac = Ka_c * C_Ac / (h + Ka_c) if C_Ac > 0 else 0.0
    hac = C_Ac - ac
    D = h * h + K1_c * h + K1_c * K2_c
    co2 = C_C * h * h / D if C_C > 0 else 0.0
    hco3 = C_C * K1_c * h / D if C_C > 0 else 0.0
    co3 = C_C * K1_c * K2_c / D if C_C > 0 else 0.0
    oh = Kw_c / h
    return ac, hac, co2, hco3, co3, oh


def _charge_residual(h: float, Ka_c: float, K1_c: float, K2_c: float, Kw_c: float, C_Ac: float, C_C: float, Na: float) -> float:
    ac, _hac, _co2, hco3, co3, oh = _speciate(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C)
    return (Na + h) - (oh + ac + hco3 + 2.0 * co3)


def _brentq_root(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na) -> float:
    """Route 1: bracketed bisection on the charge-balance residual (monotone decreasing in h)."""
    lo, hi = 1e-18, 10.0   # pH in [-1, 18]: wide enough to bracket a strongly basic solution so the domain gate,
    #                         not a bracket miss, is what refuses an out-of-Davies-domain input (fail-closed via verdict)
    try:
        return float(brentq(_charge_residual, lo, hi, args=(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na),
                            xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _polynomial_root(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na) -> float:
    """Route 2: the positive real root of  f(h) * [h (h+Ka_c) D] = 0, cleared to a polynomial in h, solved by
    numpy.roots (companion-matrix eigenvalues) -- an algorithm wholly independent of the route-1 bracket.

        f(h) = (Na+h) - Kw_c/h - Ka_c C_Ac/(h+Ka_c) - C_C K1_c h / D - 2 C_C K1_c K2_c / D,   D = h^2+K1_c h+K1_c K2_c
    multiply by h (h+Ka_c) D  (all strictly positive for h>0):
        (Na+h) h (h+Ka_c) D  -  Kw_c (h+Ka_c) D  -  Ka_c C_Ac h D  -  C_C K1_c h^2 (h+Ka_c)  -  2 C_C K1_c K2_c h (h+Ka_c) = 0
    """
    D = [1.0, K1_c, K1_c * K2_c]
    hKa = [1.0, Ka_c]
    h1 = [1.0, 0.0]
    lhs = np.polymul(np.polymul([1.0, Na], h1), np.polymul(hKa, D))
    rhs = np.polyadd(
        np.polyadd(
            np.polymul([Kw_c], np.polymul(hKa, D)),
            np.polymul([Ka_c * C_Ac], np.polymul(h1, D)),
        ),
        np.polyadd(
            np.polymul([C_C * K1_c], np.polymul([1.0, 0.0, 0.0], hKa)),
            np.polymul([2.0 * C_C * K1_c * K2_c], np.polymul(h1, hKa)),
        ),
    )
    poly = np.polysub(lhs, rhs)
    roots = np.roots(poly)
    real = [r.real for r in roots if abs(r.imag) < 1e-9 and r.real > 0]
    if not real:
        return float("nan")
    # the physical root minimises the DIRECT residual (independent of route 1's bracket)
    return float(min(real, key=lambda h: abs(_charge_residual(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na))))


def solve(system: VinegarBicarbonateSystem, *, tol: float = DAVIES_FIXED_POINT_TOL) -> CoupledSpeciationResult:
    """Solve the coupled closed-system equilibrium by TWO independent routes under the ideal or Davies model."""
    C_Ac, C_C, Na = float(system.total_acetate_M), float(system.total_carbon_M), float(system.sodium_M)
    Ka0, K10, K20, Kw0 = system.Ka.value, system.K1.value, system.K2.value, system.Kw.value
    A = DAVIES_A_25C.value
    g1 = g2 = 1.0
    davies_iters = 0
    h1 = h2 = h = ionic = float("nan")
    Ka_c = K1_c = K2_c = Kw_c = float("nan")
    davies_converged = system.activity_model == "ideal"
    for i in range(1, DAVIES_MAX_ITERS + 1):
        davies_iters = 0 if system.activity_model == "ideal" else i
        K1_c, K2_c, Kw_c = _effective_constants(K10, K20, Kw0, g1, g2)
        Ka_c = Ka0 / (g1 * g1)                       # HAc -> H+ + Ac-, HAc neutral (g ~ 1): Ka_c = Ka / g1^2
        h1 = _brentq_root(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
        h2 = _polynomial_root(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
        h = h1
        if not (math.isfinite(h) and h > 0):
            break
        ac, hac, co2, hco3, co3, oh = _speciate(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C)
        ionic = 0.5 * (h + oh + ac + hco3 + Na + 4.0 * co3)   # 0.5 sum c_i z_i^2 ; CO3(2-) carries z^2 = 4
        if system.activity_model == "ideal":
            break
        g1_new, g2_new = _gammas(ionic, A)
        if abs(g1_new - g1) <= tol * g1:
            g1, g2 = g1_new, g2_new
            K1_c, K2_c, Kw_c = _effective_constants(K10, K20, Kw0, g1, g2)
            Ka_c = Ka0 / (g1 * g1)
            h1 = _brentq_root(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
            h2 = _polynomial_root(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
            h = h1
            if math.isfinite(h) and h > 0:
                ac, hac, co2, hco3, co3, oh = _speciate(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C)
                ionic = 0.5 * (h + oh + ac + hco3 + Na + 4.0 * co3)
                davies_converged = True
            break
        g1, g2 = g1_new, g2_new

    if not (math.isfinite(h) and h > 0):
        raise NumericalVerificationError("the coupled charge-balance root solve did not return a positive [H+]")

    ac, hac, co2, hco3, co3, oh = _speciate(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C)
    charge_resid = abs((Na + h) - (oh + ac + hco3 + 2.0 * co3))
    carbon_resid = abs(C_C - (co2 + hco3 + co3))
    acetate_resid = abs(C_Ac - (hac + ac))
    agreement = abs(h1 - h2) if (math.isfinite(h1) and math.isfinite(h2)) else float("inf")

    # admission gate: both routes agree, charge/carbon/acetate conserve, species nonnegative, Davies converged + in-domain.
    problems = []
    if agreement > ROUTE_AGREEMENT_RTOL * h:
        problems.append(f"the two independent routes disagree on [H+] (|h1-h2|={agreement:.3e} > {ROUTE_AGREEMENT_RTOL}*h)")
    if charge_resid > CHARGE_BALANCE_ATOL + 1e-9 * max(Na + h, oh + ac + hco3 + 2 * co3):
        problems.append(f"charge balance does not close (residual {charge_resid:.3e})")
    if carbon_resid > CONSERVATION_RTOL * max(C_C, 1.0):
        problems.append(f"total carbon not conserved (residual {carbon_resid:.3e})")
    if acetate_resid > CONSERVATION_RTOL * max(C_Ac, 1.0):
        problems.append(f"total acetate not conserved (residual {acetate_resid:.3e})")
    for name, val in (("ac", ac), ("hac", hac), ("co2", co2), ("hco3", hco3), ("co3", co3), ("oh", oh)):
        if val < -NONNEGATIVITY_ATOL:
            problems.append(f"negative concentration {name}={val:.3e}")
    if system.activity_model == "davies":
        if not davies_converged:
            problems.append(f"the Davies ionic-strength fixed point did not converge within {DAVIES_MAX_ITERS} iters")
        if not math.isfinite(ionic) or ionic > DAVIES_I_MAX:
            problems.append(f"ionic strength {ionic} outside the Davies-model domain (<= {DAVIES_I_MAX} M)")
    if problems:
        verdict = NUMERICALLY_UNVERIFIED
    else:
        verdict = SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL if system.activity_model == "davies" else SOLVED_WITHIN_IDEAL_MODEL

    c_ref = C_REF.value
    pH_conc = -math.log10(h / c_ref)
    pH_act = -math.log10(g1 * h / c_ref)
    pH = pH_act if system.activity_model == "davies" else pH_conc
    caveats = tuple(problems)
    if not problems and system.activity_model == "davies" and math.isfinite(ionic) and ionic > 0.1:
        caveats = ("ionic strength exceeds the parents' demonstrated PHREEQC-agreement domain (I <= 0.1 M); the "
                   "NaAc(aq) ion pair is omitted from this coupled base, so the activity pH is Davies-model-only here",)
    return CoupledSpeciationResult(
        pH=pH, pH_concentration=pH_conc, pH_activity=pH_act, verdict=verdict,
        h_plus_M=h, oh_minus_M=oh, hac_M=hac, ac_minus_M=ac, co2aq_M=co2, hco3_M=hco3, co3_M=co3,
        na_plus_M=Na, ionic_strength_M=ionic, gamma_monovalent=g1, gamma_divalent=g2,
        activity_model=system.activity_model, solver_agreement_residual=agreement,
        charge_balance_residual=charge_resid, carbon_conservation_residual=carbon_resid,
        acetate_conservation_residual=acetate_resid, davies_iterations=davies_iters, caveats=caveats)


# --------------------------------------------------------------------------------- the independent-benchmark obligation
def mixed_phreeqc_benchmark_obligation() -> BenchmarkObligation:
    """The mixed acetate+carbonate interior is the object with no limiting-case free check (the parents each have
    their own benchmark; the mixed interior is new).  Its independent cross-check is two-tiered (Operation XIII P0):
    an arbitrary-precision Decimal holdout (`coupled_reference_hp.cross_check`, already run -> NUMERICALLY_VERIFIED,
    a SOLVE cross-check) AND a PHREEQC comparison which is EXTERNAL_VALIDATION_UNAVAILABLE until run (PHREEQC absent
    on the committed baseline; the reproducible decks are `benchmarks/coupled_phreeqc/inputs/*.pqi`).  The MIXED
    family needs a database carrying BOTH acetate and carbonate -- minteq.v4.dat (primary), llnl.dat (secondary);
    phreeqc.dat has no acetate and must not be patched with the code's own constant."""
    return BenchmarkObligation(
        tool="PHREEQC",
        verdict=EXTERNAL_VALIDATION_UNAVAILABLE,
        recipe={
            "import": "phreeqpython in an ISOLATED scratch venv (never the committed baseline)",
            "database": "minteq.v4.dat (carries acetate AND carbonate; primary) + llnl.dat (secondary); pin sha256",
            "species": ("CH3COOH(aq)/H(Acetate)", "CH3COO-/Acetate-", "CO2(aq)", "HCO3-", "CO3-2",
                        "H+", "OH-", "Na+", "Na(Acetate)"),
            "cases": "benchmarks/coupled_phreeqc/cases.py (M1..M11, closed liquid; open/sealed arrive with P1)",
            "compare": "PHREEQC pH (pH <guess> charge) vs VinegarBicarbonateSystem.solve().pH_activity; |dpH| AGREE "
                       "<= 0.02",
            "independence_caveat": "PHREEQC and this model share the Ka/K1/K2/Kw lineage AND PHREEQC's DB traces to "
                                   "the same classical EMF work, so a match is solver/activity-model VERIFICATION "
                                   "(common-mode), NOT independent measured-chemistry validation; a MEASURED mixed "
                                   "pH would be the stronger rung and is not fabricated if unavailable.",
        },
        comparison=None)
