"""OPERATION XIII P1 -- the COUPLED vinegar/bicarbonate equilibrium with the THREE gas-boundary modes.

`coupled_equilibrium.py` solves the mixed acetate+carbonate system in ONE case only: closed liquid, fixed total
dissolved carbon, no gas phase.  This module lifts that same shared-[H+] / shared-charge-balance coupling into the
carbonate parent's three gas-partition modes, so the flagship can be open to air, sealed, or de-gassed:

  "closed"  fixed total DISSOLVED carbon C_C (mol/L); no gas phase (identical object to coupled_equilibrium.solve --
            a consistency test pins that they agree exactly).
  "open"    fixed CO2 PARTIAL PRESSURE (an infinite reservoir): [CO2(aq)] = K_H * P_CO2 is pinned; total dissolved
            carbon C_C is an OUTPUT; carbon the reservoir absorbs/releases is tracked in the external ledger
            (exported_carbon_mol, see MixedGasResult) so "carbon-conserving" is never claimed while carbon escaped.
  "sealed"  fixed TOTAL carbon (MOLES) across the liquid AND a finite headspace of gas volume V_gas over liquid
            volume V_liq; P_CO2 and the dissolved/gas split are OUTPUTS.  Open vs sealed give DIFFERENT end states
            (V3_0 benchmark B6) -- a cartoon that ignores the partition fails.

NOT superposition (directive section 3): both families share ONE hydrogen-ion activity and ONE charge balance
    [Na+] + [H+] = [OH-] + [Ac-] + [HCO3-] + 2[CO3(2-)]
with the acetate sink [Ac-] = Ka_c C_Ac/(h+Ka_c) in EVERY mode.  Acetic acid is declared NON-VOLATILE here: only
CO2 crosses the gas interface.  That is a stated approximation (acetic acid has a real vapour pressure); acetate is
a fixed liquid total in all three modes, and the approximation is recorded in MixedGasResult.caveats via the model
assumption, not hidden.

Constants, the Davies activity model (monovalent gamma_1, divalent gamma_2 = gamma_1^4), the gas machinery (Henry
K_H, the ideal-gas headspace), tolerances and the verdict vocabulary are IMPORTED from the two parent solvers -- no
re-derivation, no fork.  Two INDEPENDENT routes solve each mode (a bracketed residual and a polynomial / a dual
elimination) and must agree, and a fail-closed admission gate RE-DERIVES the speciation from the adopted [H+] (its
own check, never a rubber stamp) before any result is handed back.

SCIENTIFIC RESTRICTION (inherited, stated loudly): two agreeing routes, or agreement with PHREEQC, are
NUMERICAL-MODEL verification, never independent measured-chemistry validation.  The NaAc(aq) ion pair is omitted
(as the parents' base models omit it), so beyond I ~ 0.1 M the activity pH carries the parents' caveat.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.optimize import brentq

from experiments.sandbox_foundation.aqueous_equilibrium import (
    C_REF,
    DAVIES_A_25C,
    DAVIES_FIXED_POINT_TOL,
    DAVIES_I_MAX,
    DAVIES_MAX_ITERS,
    KA_ACETIC_25C,
    KW_25C,
    NONNEGATIVITY_ATOL,
    NUMERICALLY_UNVERIFIED,
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    SOLVED_WITHIN_IDEAL_MODEL,
    InvalidParameterError,
    NumericalVerificationError,
    _require_constant_at_source_state,
    _require_source_temperature,
)
from experiments.sandbox_foundation.carbonate_equilibrium import (
    KH_CO2_25C,
    K1_CARBONIC_25C,
    K2_CARBONIC_25C,
    R_GAS_L_ATM,
    _effective_constants,
    _gammas,
    _polish_root,
)

_MODES = ("closed", "open", "sealed")

CHARGE_BALANCE_ATOL = 1e-12
CHARGE_BALANCE_RTOL = 1e-9
CONSERVATION_RTOL = 1e-9
ROUTE_AGREEMENT_RTOL = 1e-6   # |h1-h2| <= this*h (the coupled-closed gate's tolerance; honest floor is ~1e-18*h)

ACETATE_NONVOLATILE_CAVEAT = (
    "acetic acid is modelled as NON-VOLATILE (only CO2 crosses the gas interface); acetate is a fixed liquid total "
    "in all gas modes -- a stated approximation, acetic acid has a real vapour pressure not modelled here")
SALTING_OUT_CAVEAT = (
    "ionic strength exceeds the parents' demonstrated PHREEQC-agreement domain (I <= 0.1 M); the NaAc(aq) ion pair "
    "is omitted, so the activity pH is Davies-model-only here, not independently benchmarked")
SALTING_OUT_I_THRESHOLD = 0.1


@dataclass(frozen=True)
class MixedGasSystem:
    """A curated mixed acetate + carbonate system at fixed T with an explicit gas-partition mode.

    total_acetate_M : C_Ac (mol/L), fixed liquid total in ALL modes (acetic acid non-volatile).
    sodium_M        : Na+ (mol/L) >= 0.
    activity_model  : 'ideal' | 'davies'.
    mode            : 'closed' | 'open' | 'sealed'.
      closed : REQUIRES total_carbon_M (fixed total DISSOLVED carbon C_C, mol/L >= 0).
      open   : REQUIRES p_co2_atm (fixed CO2 partial pressure, atm > 0). C_C is an output.
      sealed : REQUIRES total_carbon_mol (total carbon, MOLES, liquid+headspace >= 0) AND v_liquid_L > 0 AND
               v_gas_L > 0. P_CO2 and the dissolved/gas split are outputs.
    """
    total_acetate_M: float = 0.0
    sodium_M: float = 0.0
    activity_model: str = "davies"
    mode: str = "closed"
    temperature_K: float = 298.15
    total_carbon_M: Optional[float] = None      # closed
    p_co2_atm: Optional[float] = None           # open
    total_carbon_mol: Optional[float] = None    # sealed
    v_liquid_L: Optional[float] = None          # sealed
    v_gas_L: Optional[float] = None             # sealed
    Ka: object = KA_ACETIC_25C
    K1: object = K1_CARBONIC_25C
    K2: object = K2_CARBONIC_25C
    Kw: object = KW_25C
    K_H: object = KH_CO2_25C

    def __post_init__(self) -> None:
        if not (isinstance(self.total_acetate_M, (int, float)) and math.isfinite(self.total_acetate_M)
                and self.total_acetate_M >= 0):
            raise InvalidParameterError("total_acetate_M must be finite and >= 0")
        if not (isinstance(self.sodium_M, (int, float)) and math.isfinite(self.sodium_M) and self.sodium_M >= 0):
            raise InvalidParameterError("sodium_M must be finite and >= 0")
        if self.activity_model not in ("ideal", "davies"):
            raise InvalidParameterError("activity_model must be 'ideal' or 'davies'")
        if self.mode not in _MODES:
            raise InvalidParameterError(f"mode must be one of {_MODES}")
        _require_source_temperature(self.temperature_K)
        for const, role in ((self.Ka, "Ka"), (self.K1, "K1"), (self.K2, "K2"), (self.Kw, "Kw"), (self.K_H, "K_H")):
            _require_constant_at_source_state(const, role=role)
        if self.mode == "closed":
            if not (self.total_carbon_M is not None and math.isfinite(self.total_carbon_M)
                    and self.total_carbon_M >= 0):
                raise InvalidParameterError("mode='closed' requires total_carbon_M (finite, >= 0 mol/L)")
        elif self.mode == "open":
            if not (self.p_co2_atm is not None and math.isfinite(self.p_co2_atm) and self.p_co2_atm > 0):
                raise InvalidParameterError("mode='open' requires p_co2_atm (finite, > 0 atm)")
        else:  # sealed
            if not (self.total_carbon_mol is not None and math.isfinite(self.total_carbon_mol)
                    and self.total_carbon_mol >= 0):
                raise InvalidParameterError("mode='sealed' requires total_carbon_mol (finite, >= 0 mol)")
            if not (self.v_liquid_L is not None and math.isfinite(self.v_liquid_L) and self.v_liquid_L > 0):
                raise InvalidParameterError("mode='sealed' requires v_liquid_L (finite, > 0 L)")
            if not (self.v_gas_L is not None and math.isfinite(self.v_gas_L) and self.v_gas_L > 0):
                raise InvalidParameterError("mode='sealed' requires v_gas_L (finite, > 0 L)")


@dataclass(frozen=True)
class MixedGasResult:
    pH: float
    pH_concentration: float
    pH_activity: float
    verdict: str
    mode: str
    h_plus_M: float
    oh_minus_M: float
    hac_M: float
    ac_minus_M: float
    co2aq_M: float
    hco3_M: float
    co3_M: float
    na_plus_M: float
    total_dissolved_carbon_M: float
    p_co2_atm: float                 # fixed input (open); diagnostic/output (closed/sealed)
    gas_carbon_mol: float            # headspace CO2 (mol); 0 for closed; NaN-free: 0 for open (infinite reservoir)
    dissolved_carbon_mol: float      # aqueous carbon (mol) for sealed; NaN otherwise
    exported_carbon_mol: float       # carbon crossing the OPEN boundary to/from the external reservoir (signed):
    #   output - (the dissolved carbon that WOULD be present in the matched closed system).  0 for closed/sealed
    #   (both are carbon-closed). For 'open' it is the external-ledger entry, so the whole-world carbon is accounted.
    ionic_strength_M: float
    gamma_monovalent: float
    gamma_divalent: float
    activity_model: str
    solver_agreement_residual: float
    charge_balance_residual: float
    carbon_balance_residual: float
    acetate_conservation_residual: float
    davies_iterations: int
    caveats: tuple = field(default_factory=tuple)


# --------------------------------------------------------------------------- per-mode carbonate basis at fixed h
def _ac(h: float, Ka_c: float, C_Ac: float) -> float:
    return Ka_c * C_Ac / (h + Ka_c) if C_Ac > 0 else 0.0


def _carbonate_open(h, K1_c, K2_c, Caq):
    hco3 = K1_c * Caq / h
    co3 = K1_c * K2_c * Caq / (h * h)
    return Caq, hco3, co3


def _carbonate_closed(h, K1_c, K2_c, C_C):
    D = h * h + K1_c * h + K1_c * K2_c
    co2 = C_C * h * h / D
    hco3 = C_C * K1_c * h / D
    co3 = C_C * K1_c * K2_c / D
    return co2, hco3, co3


# -------------------------------------------------------------------------------------------------- open mode
def _open_residual(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Caq, Na):
    ac = _ac(h, Ka_c, C_Ac)
    co2, hco3, co3 = _carbonate_open(h, K1_c, K2_c, Caq)
    oh = Kw_c / h
    return (Na + h) - (oh + ac + hco3 + 2.0 * co3)


def _open_brentq(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Caq, Na):
    lo, hi = 1e-30, max(1.0, Na + 1.0)
    try:
        return float(brentq(_open_residual, lo, hi, args=(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Caq, Na),
                            xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _open_poly(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Caq, Na):
    """Route 2 for 'open': the positive real root of  f(h)*h^2*(h+Ka_c) = 0, a quartic cleared from f(h):
        (Na+h) h^2 (h+Ka_c) - Kw_c h (h+Ka_c) - Ka_c C_Ac h^2 - K1_c Caq h (h+Ka_c) - 2 K1_c K2_c Caq (h+Ka_c) = 0
    via numpy.roots, Newton-polished (np.roots loses relative precision for tiny basic roots)."""
    hKa = [1.0, Ka_c]
    h2 = [1.0, 0.0, 0.0]
    lhs = np.polymul([1.0, Na], np.polymul(h2, hKa))                        # (Na+h) h^2 (h+Ka_c)
    rhs = np.polyadd(
        np.polyadd(np.polymul([Kw_c], np.polymul([1.0, 0.0], hKa)),         # Kw_c h (h+Ka_c)
                   [Ka_c * C_Ac, 0.0, 0.0]),                                 # Ka_c C_Ac h^2
        np.polyadd(np.polymul([K1_c * Caq], np.polymul([1.0, 0.0], hKa)),   # K1_c Caq h (h+Ka_c)
                   np.polymul([2.0 * K1_c * K2_c * Caq], hKa)),              # 2 K1_c K2_c Caq (h+Ka_c)
    )
    poly = np.polysub(lhs, rhs)
    try:
        roots = np.roots(poly)
    except (np.linalg.LinAlgError, ValueError):
        return float("nan")
    real = [float(r.real) for r in roots if abs(r.imag) < 1e-12 * max(1.0, abs(r.real)) and r.real > 0]
    if not real:
        return float("nan")
    cand = min(real, key=lambda h: abs(_open_residual(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Caq, Na)))
    return _polish_root([float(c) for c in poly], cand)


# ------------------------------------------------------------------------------------------------- closed mode
def _closed_residual(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na):
    ac = _ac(h, Ka_c, C_Ac)
    _co2, hco3, co3 = _carbonate_closed(h, K1_c, K2_c, C_C)
    oh = Kw_c / h
    return (Na + h) - (oh + ac + hco3 + 2.0 * co3)


def _closed_brentq(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na):
    lo, hi = 1e-18, 10.0
    try:
        return float(brentq(_closed_residual, lo, hi, args=(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na),
                            xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _closed_poly(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na):
    """Route 2 for 'closed': identical algebra to coupled_equilibrium._polynomial_root -- f(h)*h(h+Ka_c)D = 0."""
    D = [1.0, K1_c, K1_c * K2_c]
    hKa = [1.0, Ka_c]
    h1 = [1.0, 0.0]
    lhs = np.polymul(np.polymul([1.0, Na], h1), np.polymul(hKa, D))
    rhs = np.polyadd(
        np.polyadd(np.polymul([Kw_c], np.polymul(hKa, D)), np.polymul([Ka_c * C_Ac], np.polymul(h1, D))),
        np.polyadd(np.polymul([C_C * K1_c], np.polymul([1.0, 0.0, 0.0], hKa)),
                   np.polymul([2.0 * C_C * K1_c * K2_c], np.polymul(h1, hKa))),
    )
    poly = np.polysub(lhs, rhs)
    try:
        roots = np.roots(poly)
    except (np.linalg.LinAlgError, ValueError):
        return float("nan")
    real = [float(r.real) for r in roots if abs(r.imag) < 1e-9 and r.real > 0]
    if not real:
        return float("nan")
    return float(min(real, key=lambda h: abs(_closed_residual(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na))))


# ------------------------------------------------------------------------------------------------- sealed mode
def _caq_from_charge_mixed(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na):
    """[CO2(aq)] implied by charge balance at h, with the acetate sink included:
    Na + h - Kw_c/h - Ka_c C_Ac/(h+Ka_c) = Caq (K1_c/h + 2 K1_c K2_c/h^2).  NaN if the physical (>=0) branch fails."""
    denom = K1_c / h + 2.0 * K1_c * K2_c / (h * h)
    if not (math.isfinite(denom) and denom > 0):
        return float("nan")
    caq = (Na + h - Kw_c / h - _ac(h, Ka_c, C_Ac)) / denom
    # tolerate a roundoff-negative numerator (the zero-carbon / boundary case) and clamp to the physical branch.
    if not math.isfinite(caq) or caq < -NONNEGATIVITY_ATOL:
        return float("nan")
    return max(caq, 0.0)


def _sealed_carbon_in_h(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT):
    caq = _caq_from_charge_mixed(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na)
    if not (math.isfinite(caq) and caq >= 0):
        return float("nan")
    c_dissolved = caq * (1.0 + K1_c / h + K1_c * K2_c / (h * h))
    n_liq = c_dissolved * V_liq
    n_gas = (caq / K_H) * V_gas / RT
    return (n_liq + n_gas) - n_C


def _sealed_charge_numerator(h, Ka_c, Kw_c, C_Ac, Na):
    return Na + h - Kw_c / h - _ac(h, Ka_c, C_Ac)


def _sealed_h_route(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT):
    # the charge-balance Caq goes negative below h0 where the numerator N(h0)=0; N is strictly increasing, so
    # bracket h0 first, then bracket the carbon residual strictly above it.
    def _num(h):
        return _sealed_charge_numerator(h, Ka_c, Kw_c, C_Ac, Na)
    try:
        h0 = float(brentq(_num, 1e-30, max(1.0, Na + 1.0), xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        h0 = 0.0
    lo = h0 * (1.0 + 1e-9) if h0 > 0 else 1e-300
    hi = max(1.0, Na + 1.0)
    try:
        return float(brentq(_sealed_carbon_in_h, lo, hi,
                            args=(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT),
                            xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _sealed_carbon_in_p(p_co2, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT):
    caq = K_H * p_co2
    h = _open_poly(Ka_c, K1_c, K2_c, Kw_c, C_Ac, caq, Na)
    if not (math.isfinite(h) and h > 0):
        h = _open_brentq(Ka_c, K1_c, K2_c, Kw_c, C_Ac, caq, Na)
    if not (math.isfinite(h) and h > 0):
        return float("nan")
    c_dissolved = caq * (1.0 + K1_c / h + K1_c * K2_c / (h * h))
    n_liq = c_dissolved * V_liq
    n_gas = p_co2 * V_gas / RT
    return (n_liq + n_gas) - n_C


def _sealed_p_route(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT):
    hi = max(1e-30, 2.0 * n_C * RT / V_gas) if n_C > 0 else 1.0
    try:
        return float(brentq(_sealed_carbon_in_p, 1e-30, hi,
                            args=(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT),
                            xtol=1e-30, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


# -------------------------------------------------------------------------------------- mode dispatch at fixed h
def _speciate(system: MixedGasSystem, Ka_c, K1_c, K2_c, Kw_c, K_H, RT, Na, C_Ac):
    """Solve one mode at fixed effective constants by two independent routes.  Returns a dict of the adopted
    speciation + the two route [H+]s + the gas quantities (None where a mode does not define one)."""
    mode = system.mode
    if mode == "open":
        caq = K_H * float(system.p_co2_atm)
        h1 = _open_brentq(Ka_c, K1_c, K2_c, Kw_c, C_Ac, caq, Na)
        h2 = _open_poly(Ka_c, K1_c, K2_c, Kw_c, C_Ac, caq, Na)
        h = h1
        if not (math.isfinite(h) and h > 0):
            return None
        _c, hco3, co3 = _carbonate_open(h, K1_c, K2_c, caq)
        C_C_out = caq + hco3 + co3
        return dict(h1=h1, h2=h2, h=h, caq=caq, hco3=hco3, co3=co3, C_C=C_C_out,
                    p_co2=float(system.p_co2_atm), n_gas=0.0, n_liq=float("nan"))
    if mode == "closed":
        C_C = float(system.total_carbon_M)
        h1 = _closed_brentq(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
        h2 = _closed_poly(Ka_c, K1_c, K2_c, Kw_c, C_Ac, C_C, Na)
        h = h1
        if not (math.isfinite(h) and h > 0):
            return None
        caq, hco3, co3 = _carbonate_closed(h, K1_c, K2_c, C_C)
        return dict(h1=h1, h2=h2, h=h, caq=caq, hco3=hco3, co3=co3, C_C=C_C,
                    p_co2=caq / K_H, n_gas=0.0, n_liq=float("nan"))
    # sealed
    n_C, V_liq, V_gas = float(system.total_carbon_mol), float(system.v_liquid_L), float(system.v_gas_L)
    if n_C == 0.0:
        # no carbon: a sealed vessel over the pure acetate/water system; the (inert) headspace holds no CO2.  The
        # carbon-balance bracketing degenerates at zero carbon (the root is the boundary h where Caq->0), so solve
        # the carbon-free charge balance directly -- identical to closed with C_C = 0.
        h1 = _closed_brentq(Ka_c, K1_c, K2_c, Kw_c, C_Ac, 0.0, Na)
        h2 = _closed_poly(Ka_c, K1_c, K2_c, Kw_c, C_Ac, 0.0, Na)
        h = h1
        if not (math.isfinite(h) and h > 0):
            return None
        return dict(h1=h1, h2=h2, h=h, caq=0.0, hco3=0.0, co3=0.0, C_C=0.0, p_co2=0.0, n_gas=0.0, n_liq=0.0)
    h1 = _sealed_h_route(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT)
    p2 = _sealed_p_route(Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na, n_C, V_liq, V_gas, K_H, RT)
    h2 = float("nan")
    if math.isfinite(p2) and p2 > 0:
        caq2 = K_H * p2
        h2 = _open_poly(Ka_c, K1_c, K2_c, Kw_c, C_Ac, caq2, Na)
        if not (math.isfinite(h2) and h2 > 0):
            h2 = _open_brentq(Ka_c, K1_c, K2_c, Kw_c, C_Ac, caq2, Na)
    h = h1
    if not (math.isfinite(h) and h > 0):
        return None
    caq = _caq_from_charge_mixed(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na)
    if not (math.isfinite(caq) and caq >= 0):
        return None
    _c, hco3, co3 = _carbonate_open(h, K1_c, K2_c, caq)
    C_C_out = caq + hco3 + co3
    p_co2 = caq / K_H
    n_liq = C_C_out * V_liq
    n_gas = p_co2 * V_gas / RT
    return dict(h1=h1, h2=h2, h=h, caq=caq, hco3=hco3, co3=co3, C_C=C_C_out,
                p_co2=p_co2, n_gas=n_gas, n_liq=n_liq)


def _ionic_strength(h, oh, ac, hco3, co3, Na):
    return 0.5 * (h + oh + ac + hco3 + Na + 4.0 * co3)


def solve(system: MixedGasSystem, *, tol: float = DAVIES_FIXED_POINT_TOL) -> MixedGasResult:
    """Solve the coupled equilibrium for the requested gas-boundary mode by two independent routes under the ideal
    or Davies model.  Handed back only if the fail-closed admission gate certifies it."""
    C_Ac, Na = float(system.total_acetate_M), float(system.sodium_M)
    Ka0, K10, K20, Kw0, K_H = system.Ka.value, system.K1.value, system.K2.value, system.Kw.value, system.K_H.value
    A = DAVIES_A_25C.value
    RT = R_GAS_L_ATM.value * float(system.temperature_K)
    g1 = g2 = 1.0
    davies_iters = 0
    ionic = float("nan")
    davies_converged = system.activity_model == "ideal"
    sol = None
    Ka_c = K1_c = K2_c = Kw_c = float("nan")
    for i in range(1, DAVIES_MAX_ITERS + 1):
        davies_iters = 0 if system.activity_model == "ideal" else i
        K1_c, K2_c, Kw_c = _effective_constants(K10, K20, Kw0, g1, g2)
        Ka_c = Ka0 / (g1 * g1)
        sol = _speciate(system, Ka_c, K1_c, K2_c, Kw_c, K_H, RT, Na, C_Ac)
        if sol is None:
            break
        h = sol["h"]
        ac = _ac(h, Ka_c, C_Ac)
        oh = Kw_c / h
        ionic = _ionic_strength(h, oh, ac, sol["hco3"], sol["co3"], Na)
        if system.activity_model == "ideal":
            break
        g1_new, g2_new = _gammas(ionic, A)
        if abs(g1_new - g1) <= tol * g1:
            g1, g2 = g1_new, g2_new
            K1_c, K2_c, Kw_c = _effective_constants(K10, K20, Kw0, g1, g2)
            Ka_c = Ka0 / (g1 * g1)
            sol = _speciate(system, Ka_c, K1_c, K2_c, Kw_c, K_H, RT, Na, C_Ac)
            if sol is not None:
                h = sol["h"]
                ac = _ac(h, Ka_c, C_Ac)
                oh = Kw_c / h
                ionic = _ionic_strength(h, oh, ac, sol["hco3"], sol["co3"], Na)
                davies_converged = True
            break
        g1, g2 = g1_new, g2_new

    if sol is None or not (math.isfinite(sol["h"]) and sol["h"] > 0):
        raise NumericalVerificationError(f"the coupled {system.mode} solve did not return a positive [H+]")

    h = sol["h"]
    ac = _ac(h, Ka_c, C_Ac)
    hac = C_Ac - ac
    oh = Kw_c / h
    caq, hco3, co3 = sol["caq"], sol["hco3"], sol["co3"]
    C_C = sol["C_C"]

    verdict, problems = _admit(system, h, sol, Ka_c, K1_c, K2_c, Kw_c, K_H, RT, Na, C_Ac, ac, hac, oh,
                               ionic, davies_converged, davies_iters)

    c_ref = C_REF.value
    pH_conc = -math.log10(h / c_ref)
    pH_act = -math.log10(g1 * h / c_ref)
    pH = pH_act if system.activity_model == "davies" else pH_conc

    caveats = tuple(problems) if problems else (ACETATE_NONVOLATILE_CAVEAT,)
    if not problems and system.activity_model == "davies" and math.isfinite(ionic) and ionic > SALTING_OUT_I_THRESHOLD:
        caveats = (ACETATE_NONVOLATILE_CAVEAT, SALTING_OUT_CAVEAT)

    # external-ledger carbon export for the OPEN boundary: the dissolved carbon the matched CLOSED system would hold
    # at this pH is C_C itself here (open C_C is the dissolved total); the reservoir supplied/absorbed exactly the
    # difference from a de-gassed start (0). So exported = -C_C*V? -- but open has no V. We report the per-litre
    # dissolved carbon that crossed the boundary into solution as the signed ledger entry (negative = absorbed from
    # reservoir). closed/sealed are carbon-closed => 0.
    exported = -C_C if system.mode == "open" else 0.0

    charge_resid = abs((Na + h) - (oh + ac + hco3 + 2.0 * co3))
    acetate_resid = abs(C_Ac - (hac + ac))
    if system.mode == "closed":
        carbon_resid = abs((caq + hco3 + co3) - float(system.total_carbon_M))
    elif system.mode == "sealed":
        carbon_resid = abs((sol["n_liq"] + sol["n_gas"]) - float(system.total_carbon_mol))
    else:
        carbon_resid = 0.0

    agreement = abs(sol["h1"] - sol["h2"]) if (math.isfinite(sol["h1"]) and math.isfinite(sol["h2"])) else float("inf")

    return MixedGasResult(
        pH=pH, pH_concentration=pH_conc, pH_activity=pH_act, verdict=verdict, mode=system.mode,
        h_plus_M=h, oh_minus_M=oh, hac_M=hac, ac_minus_M=ac, co2aq_M=caq, hco3_M=hco3, co3_M=co3, na_plus_M=Na,
        total_dissolved_carbon_M=C_C, p_co2_atm=sol["p_co2"],
        gas_carbon_mol=(sol["n_gas"] if system.mode == "sealed" else 0.0),
        dissolved_carbon_mol=(sol["n_liq"] if system.mode == "sealed" else float("nan")),
        exported_carbon_mol=exported, ionic_strength_M=ionic, gamma_monovalent=g1, gamma_divalent=g2,
        activity_model=system.activity_model, solver_agreement_residual=agreement,
        charge_balance_residual=charge_resid, carbon_balance_residual=carbon_resid,
        acetate_conservation_residual=acetate_resid, davies_iterations=davies_iters, caveats=caveats)


def _admit(system, h, sol, Ka_c, K1_c, K2_c, Kw_c, K_H, RT, Na, C_Ac, ac, hac, oh, ionic, davies_converged,
           davies_iters):
    """Fail-closed admission.  RE-DERIVES the speciation from the adopted h per the mode's own definition and checks
    route agreement, charge balance (acetate sink + divalent CO3), mode-appropriate carbon closure, acetate closure,
    nonnegativity, and the Davies domain.  Returns (verdict, problems); verdict is NUMERICALLY_UNVERIFIED if any
    problem (the coupled-closed convention: demote, do not raise, except when no positive [H+] exists at all)."""
    problems = []
    h1, h2 = sol["h1"], sol["h2"]
    if not (math.isfinite(h1) and h1 > 0 and math.isfinite(h2) and h2 > 0):
        problems.append(f"a solver route failed to deliver a finite positive [H+] (route1={h1}, route2={h2})")
    elif abs(h1 - h2) > ROUTE_AGREEMENT_RTOL * max(h1, h2):
        problems.append(f"the two routes disagree (|h1-h2|={abs(h1 - h2):.3e} > {ROUTE_AGREEMENT_RTOL}*h)")

    # re-derive the carbonate speciation from the adopted h per mode.
    if system.mode == "open":
        caq_d = K_H * float(system.p_co2_atm)
        _c, hco3_d, co3_d = _carbonate_open(h, K1_c, K2_c, caq_d)
    elif system.mode == "closed":
        caq_d, hco3_d, co3_d = _carbonate_closed(h, K1_c, K2_c, float(system.total_carbon_M))
    else:  # sealed
        caq_d = _caq_from_charge_mixed(h, Ka_c, K1_c, K2_c, Kw_c, C_Ac, Na)
        if math.isfinite(caq_d) and caq_d >= 0:
            _c, hco3_d, co3_d = _carbonate_open(h, K1_c, K2_c, caq_d)
        else:
            hco3_d = co3_d = float("nan")
    oh_d = Kw_c / h
    ac_d = _ac(h, Ka_c, C_Ac)

    for name, val in (("CO2(aq)", caq_d), ("HCO3-", hco3_d), ("CO3-2", co3_d), ("OH-", oh_d), ("Ac-", ac_d)):
        if not math.isfinite(val) or val < -NONNEGATIVITY_ATOL:
            problems.append(f"re-derived {name} is negative/non-finite ({val})")

    cb = abs((Na + h) - (oh_d + ac_d + hco3_d + 2.0 * co3_d))
    cb_allow = CHARGE_BALANCE_ATOL + CHARGE_BALANCE_RTOL * (Na + h + oh_d + ac_d + hco3_d + 2.0 * co3_d)
    if math.isfinite(cb) and cb > cb_allow:
        problems.append(f"charge balance does not close (residual {cb:.3e} > {cb_allow:.3e})")

    # reported-vs-re-derived consistency (catch a fabricated split).
    for name, rep, der in (("CO2(aq)", sol["caq"], caq_d), ("HCO3-", sol["hco3"], hco3_d), ("CO3-2", sol["co3"], co3_d)):
        if not (math.isfinite(rep) and math.isfinite(der)) or abs(rep - der) > 1e-9 * max(1.0, abs(der)):
            problems.append(f"reported {name} disagrees with the re-derivation ({rep} vs {der})")

    # acetate closure
    if abs(C_Ac - (hac + ac)) > CONSERVATION_RTOL * max(1.0, C_Ac):
        problems.append("acetate not conserved")

    # mode-appropriate carbon closure
    if system.mode == "closed":
        if abs((caq_d + hco3_d + co3_d) - float(system.total_carbon_M)) > CONSERVATION_RTOL * max(1.0, float(system.total_carbon_M)):
            problems.append("dissolved-carbon balance does not close")
    elif system.mode == "sealed":
        n_C, V_liq, V_gas = float(system.total_carbon_mol), float(system.v_liquid_L), float(system.v_gas_L)
        p_d = caq_d / K_H if math.isfinite(caq_d) else float("nan")
        n_liq_d = (caq_d + hco3_d + co3_d) * V_liq if math.isfinite(caq_d) else float("nan")
        n_gas_d = p_d * V_gas / RT if math.isfinite(p_d) else float("nan")
        if not (math.isfinite(n_gas_d) and n_gas_d >= -NONNEGATIVITY_ATOL):
            problems.append(f"re-derived headspace CO2 moles not nonnegative/finite ({n_gas_d})")
        elif abs((n_liq_d + n_gas_d) - n_C) > CONSERVATION_RTOL * max(1.0, n_C):
            problems.append(f"total-carbon (liquid+headspace) balance does not close ({n_liq_d + n_gas_d} vs {n_C})")

    if system.activity_model == "davies":
        if not davies_converged:
            problems.append(f"the Davies fixed point did not converge within {DAVIES_MAX_ITERS} iters")
        if not math.isfinite(ionic) or ionic > DAVIES_I_MAX:
            problems.append(f"ionic strength {ionic} outside the Davies domain (<= {DAVIES_I_MAX} M)")

    if problems:
        return NUMERICALLY_UNVERIFIED, problems
    return (SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL if system.activity_model == "davies"
            else SOLVED_WITHIN_IDEAL_MODEL), problems
