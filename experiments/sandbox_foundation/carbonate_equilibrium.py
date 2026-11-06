"""A SOURCE-BACKED zero-dimensional carbonate / CO2 aqueous equilibrium WITH gas partition.

The sibling of `aqueous_equilibrium.py` (the acetic-acid / acetate / water model), built to the same discipline and
re-using its machinery -- but for the carbonate system, which is where the 3.0 "vinegar + baking soda" flagship
(`docs/research/V3_0_VINEGAR_BICARBONATE_FLAGSHIP.md`) actually gets its gas.  This module is the carbonate half of
that flagship's smallest checkable slice (V3_0 section 2.4): a well-mixed, isothermal, EQUILIBRIUM end-state model.

It is NOT a dynamical simulation.  It does not fizz, nucleate, or evolve in time.  V3_0 section 3 BANS the anti-pattern
"if acid touches bicarbonate: spawn bubbles": any gas here is an OUTPUT of coupled equilibria and a Henry partition,
never a switch.  The quantity this module computes -- how carbon partitions among CO2(aq), HCO3-, CO3(2-), and a CO2
gas phase, and the resulting pH -- is exactly what distinguishes a model from a cartoon (V3_0 benchmark B6: open vs
sealed give DIFFERENT answers).

Why a NEW module and not an extension of AcetateWaterSystem: that model's activity bookkeeping is monovalent-only
(ionic strength and the Davies coefficient assume |z| = 1).  CO3(2-) is DIVALENT, so the activity algebra genuinely
differs (gamma_z = gamma_1^(z^2)).  Re-using the acetate solver would have silently mis-weighted CO3(2-).  So the
shared, charge-agnostic machinery is IMPORTED (SourcedConstant, the verdict vocabulary, every tolerance, the
source-temperature guards, Kw, the Davies A parameter, c_ref, the monovalent gamma kernel) and only the
carbonate-specific chemistry -- a divalent-aware activity model and the three gas-partition modes -- is new here.

PROVENANCE REGIME (stated, not hidden): the carbonate constants are `SourcedConstant`s -- the SAME label-level
provenance the acetate model uses.  This is NOT the verifier-minted `SourceBinding` of mechanism_types.py (that
machinery is kinetics-only; its on-disk artifact schema is k_f/k_r and cannot even hold an equilibrium constant).  So
a caller could in principle construct a `SourcedConstant(..., status="SOURCED")` with any numbers; the authority here
is the citation + the positive-uncertainty discipline (a fabricated / zero error bar is refused), not a cryptographic
binding.  The default constants below carry real tertiary citations and genuine inter-source uncertainties.  Any
chamber consuming this remains structurally SYNTHETIC (`ModelRunReceipt`), so nothing downstream over-claims.

SPECIES (a curated, FIXED set of explicit chemical identities + net charges -- the #105 single-global-charge wall is
sidestepped exactly as the acetate model does it, by enumerating a closed set, not by solving general local-charge
structural chemistry):
    CO2(aq)  dissolved carbon dioxide == H2CO3* (the lumped convention: CO2(aq) and true H2CO3 together)   charge  0
    HCO3-    bicarbonate                                                                                   charge -1
    CO3(2-)  carbonate                                                                                     charge -2
    H+       hydronium                                                                                      charge +1
    OH-      hydroxide                                                                                      charge -1
    Na+      added conservative cation (from NaHCO3 / Na2CO3 / NaOH), >= 0                                  charge +1
    (H2O the solvent, activity 1 in the dilute reference; CO2(g) the gas phase in the open/sealed modes)

EQUILIBRIA (ideal-dilute reference unless a Davies activity correction is requested):
    CO2(aq) + H2O <-> H+ + HCO3-      K1 = [H+][HCO3-]/[CO2(aq)]      (the COMPOSITE first constant, pK1 ~ 6.35:
                                        it lumps CO2 hydration; the "true" H2CO3 pKa ~3.6 is a DIFFERENT quantity)
    HCO3-        <-> H+ + CO3(2-)     K2 = [H+][CO3(2-)]/[HCO3-]      (pK2 ~ 10.33)
    H2O          <-> H+ + OH-         Kw = [H+][OH-]
    CO2(g)       <-> CO2(aq)          K_H = [CO2(aq)] / P_CO2         (Henry solubility, mol L^-1 atm^-1)

CHARGE BALANCE:  [Na+] + [H+] = [OH-] + [HCO3-] + 2*[CO3(2-)]     (note the FACTOR OF 2 on the divalent)

GAS-PARTITION MODES (V3_0 benchmark B6; the open/sealed distinction is PHREEQC Example 7's fixed-partial-pressure vs
fixed-volume gas phase -- https://water.usgs.gov/.../phreeqc3-69.htm.  Example 7 itself decomposes ORGANIC matter; we
borrow only its gas-phase TREATMENT and apply it to a clean carbonate system, which PHREEQC computes natively):

  "open"   -- fixed CO2 PARTIAL PRESSURE (an infinite reservoir: ambient air, or a sparged headspace).  [CO2(aq)] is
              pinned by Henry (= K_H * P_CO2); total dissolved carbon C_T is an OUTPUT.  Reduces to a CUBIC in h:
                  h^3 + Na h^2 - (Kw_c + K1_c Caq) h - 2 K1_c K2_c Caq = 0,   Caq = K_H P_CO2.
              Famous checkable end-state: pure water (Na=0) open to atmospheric CO2 (P ~ 10^-3.5 atm) -> pH ~ 5.6.

  "closed"  -- fixed TOTAL DISSOLVED CARBON C_T, NO gas exchange (a de-gassed, sealed-full solution).  P_CO2 is a
              reported diagnostic ([CO2(aq)]/K_H), not an input.  Reduces to a QUARTIC in h.  Famous checkable
              end-states: 0.1 M NaHCO3 -> pH ~ 8.3 (the amphoteric buffer, ~ (pK1+pK2)/2, nearly C_T-independent);
              0.1 M Na2CO3 -> pH ~ 11.6.

  "sealed"  -- fixed TOTAL CARBON (moles, across the liquid AND a finite headspace) in a closed vessel of liquid
              volume V_liq and gas volume V_gas.  CO2 partitions between dissolved and headspace; P_CO2 (and the
              dissolved/gas split) are OUTPUTS.  This is B6's discriminator: for identical contents, "sealed" keeps
              MORE CO2 dissolved and builds pressure, "open" lets it escape to the fixed reservoir -- a cartoon that
              ignores the partition gives the two the same answer and FAILS.  Solved as two unknowns (h, P_CO2) by
              two independent eliminations (bracket h with Caq from charge balance / bracket P_CO2 with h from the
              open cubic), which must agree.

SOLVER + ADMISSION: every mode solves by TWO INDEPENDENT ALGORITHMS on the SINGLE sourced constant set (a cross-check
of the SOLVER, not a second thermodynamic database -- the directive's warning is respected), and the result is handed
back ONLY if the fail-closed admission gate certifies it (routes agree; charge balance closes; the relevant carbon
balance closes; no negative concentration or pressure; Davies converged and in-domain).  A numerical failure raises
NumericalVerificationError and is NEVER dressed up as a prediction.  pH is reported honestly (p[H] concentration and
pH_activity, c_ref declared; the activity value is primary under Davies) exactly as the acetate model does.

INDEPENDENT BENCHMARK: PHREEQC (the carbonate system IS native to its default database), run in an isolated scratch
venv -- see `benchmarks/carbonate_phreeqc/`.  Until that is run the independent cross-check is
EXTERNAL_VALIDATION_UNAVAILABLE; the "textbook anchors" (pH ~ 5.6 / 8.3 / 11.6) are equation/implementation
VERIFICATION against the SAME constants, NOT independent experimental validation, and are labelled as such.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.optimize import brentq

import experiments.sandbox_foundation.aqueous_equilibrium as aq
from experiments.sandbox_foundation.aqueous_equilibrium import (
    AGREEMENT_RTOL,
    BenchmarkObligation,
    CHARGE_BALANCE_ATOL,
    CHARGE_BALANCE_RTOL,
    C_REF,
    DAVIES_FIXED_POINT_TOL,
    DAVIES_I_MAX,
    DAVIES_MAX_ITERS,
    EXTERNAL_VALIDATION_UNAVAILABLE,
    KW_25C,
    MASS_BALANCE_RTOL,
    NONNEGATIVITY_ATOL,
    NumericalVerificationError,
    OutOfSourceDomainError,  # noqa: F401  (re-exported so callers catch it from either module)
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    SOLVED_WITHIN_IDEAL_MODEL,
    SourcedConstant,
    _davies_gamma,
    _require_constant_at_source_state,
    _require_source_temperature,
)
from experiments.sandbox_foundation.twocell import InvalidParameterError

# The carbonate module speaks the SAME verdict vocabulary as the acetate model -- no new tokens, so a caller that
# already branches on aqueous_equilibrium.VERDICTS needs no change.  (A frozenset mirror for local assertions.)
VERDICTS = frozenset({
    SOLVED_WITHIN_IDEAL_MODEL, SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    EXTERNAL_VALIDATION_UNAVAILABLE,
})

_MODES = ("open", "closed", "sealed")


# --------------------------------------------------------------------------------- sourced constants (provenance)
# pK1 = 6.35 (the COMPOSITE first dissociation constant of the CO2(aq)+H2CO3 pool at 25 C).  Primary lineage:
# Harned & Davis, J. Am. Chem. Soc. 65, 2030 (1943); as tabulated in the CRC Handbook of Chemistry and Physics and in
# Stumm & Morgan, Aquatic Chemistry (3rd ed.).  The inter-source spread is pK1 ~ 6.35-6.38 across general / aquatic
# references -> a conservative +/-0.04 in pK1 maps to ~+/-4.5e-8 on K1 = 10^-6.35 = 4.467e-7.
K1_CARBONIC_25C = SourcedConstant(
    "K1_carbonic", 10 ** (-6.35), 5.0e-8, "dimensionless (molar, ideal reference)", 298.15,
    "Composite first dissociation constant of carbonic acid (CO2(aq)+H2CO3*), pK1 = 6.35 at 25 C; Harned & Davis "
    "JACS 65, 2030 (1943) via CRC Handbook of Chemistry and Physics and Stumm & Morgan, Aquatic Chemistry 3rd ed.",
    "SOURCED",
    "LUMPED convention: K1 is for the CO2(aq)+H2CO3* pool, NOT the true H2CO3 (pKa ~ 3.6).  The inter-source pK1 "
    "spread (~6.35-6.38) sets the uncertainty, which is a MODEL/SOURCE spread, not a statistical 1-sigma.")

# pK2 = 10.33 at 25 C.  Harned & Scholes, J. Am. Chem. Soc. 63, 1706 (1941); CRC / Stumm & Morgan.  Spread
# ~10.32-10.33 -> +/-0.04 in pK2 -> ~+/-5e-12 on K2 = 10^-10.33 = 4.677e-11.
K2_CARBONIC_25C = SourcedConstant(
    "K2_carbonic", 10 ** (-10.33), 5.0e-12, "dimensionless (molar, ideal reference)", 298.15,
    "Second dissociation constant of carbonic acid (HCO3- <-> H+ + CO3(2-)), pK2 = 10.33 at 25 C; Harned & Scholes "
    "JACS 63, 1706 (1941) via CRC Handbook and Stumm & Morgan, Aquatic Chemistry 3rd ed.", "SOURCED",
    "The inter-source pK2 spread (~10.32-10.33) sets the uncertainty (a MODEL/SOURCE spread, not a statistical sigma).")

# Henry solubility of CO2 at 25 C.  Sander's compilation v5.0.0 (R. Sander, Atmos. Chem. Phys. 23, 10901-12440,
# 2023, doi:10.5194/acp-23-10901-2023) lists the top-reliability CO2 entry (Burkholder et al. 2019) as Hcp =
# 3.4e-4 mol m^-3 Pa^-1.  Convert to molar: 3.4e-4 mol m^-3 Pa^-1 * 101325 Pa/atm * 1e-3 m^3/L = 0.03445 mol L^-1
# atm^-1.  The listed references cluster at Hcp ~ 3.3-3.4e-4 (-> ~0.0334-0.0345 M/atm) with a wider full-table spread;
# common textbooks give ~0.031-0.034.  A conservative +/-0.003 M/atm covers that inter-source band.
KH_CO2_25C = SourcedConstant(
    "K_H_CO2", 0.0344, 0.003, "mol/L/atm (molar Henry solubility)", 298.15,
    "CO2 Henry solubility at 25 C: Sander compilation v5.0.0 (Atmos. Chem. Phys. 23, 10901, 2023), top CO2 entry "
    "Hcp = 3.4e-4 mol m^-3 Pa^-1 (Burkholder et al. 2019) -> 0.0344 mol L^-1 atm^-1.", "SOURCED",
    "Neutral-species solubility: the dissolved-CO2 activity salting-out (Sechenov) correction is OMITTED, so K_H is "
    "held ionic-strength-independent; that omission is a caveat at higher I, not a fabricated number.  The +/-0.003 "
    "is the inter-source/compilation spread (~0.031-0.0345 M/atm), a model/source spread, not a statistical sigma.")

# The molar gas constant, R = 8.31446 J mol^-1 K^-1 (SI 2019, exact) with the standard atmosphere = 101325 Pa (exact)
# -> R = 0.0820574 L atm mol^-1 K^-1.  EXACT by definition (both R and atm are defined), hence zero uncertainty --
# the ONLY kind of constant allowed a zero error bar.  Used only by the finite-headspace ("sealed") ideal-gas moles.
R_GAS_L_ATM = SourcedConstant(
    "R_gas", 0.082057366080960, 0.0, "L*atm/mol/K (molar gas constant)", 298.15,
    "Molar gas constant R = 8.314462618 J/mol/K (SI 2019 exact) with 1 atm = 101325 Pa (exact): "
    "R = 8.314462618/101.325 = 0.0820573661 L*atm/mol/K.", "EXACT",
    "Exact by definition; the ideal-gas headspace relation n = P*V/(R*T).  Ideal-gas law assumed (near-ambient P).")


# --------------------------------------------------------------------------------- the curated system
@dataclass(frozen=True)
class CarbonateWaterSystem:
    """A curated CO2 / bicarbonate / carbonate / water system at fixed T, with an explicit gas-partition mode.

    sodium_M        : added conservative cation [Na+] in mol/L (from NaHCO3 / Na2CO3 / NaOH), >= 0.
    activity_model  : 'ideal' or 'davies'.
    mode            : one of 'open' / 'closed' / 'sealed' (see the module docstring).
      mode='open'   : REQUIRES p_co2_atm (the fixed CO2 partial pressure, atm > 0).  C_T is an output.
      mode='closed' : REQUIRES total_carbon_M (fixed total DISSOLVED carbon C_T, mol/L >= 0).  No gas phase.
      mode='sealed' : REQUIRES total_carbon_mol (fixed total carbon, MOLES, liquid+headspace) AND v_liquid_L > 0 AND
                      v_gas_L > 0.  P_CO2 and the dissolved/gas split are outputs.
    """
    activity_model: str = "ideal"
    mode: str = "open"
    temperature_K: float = 298.15
    sodium_M: float = 0.0
    # mode-specific inputs (only the ones its mode needs are read / validated):
    p_co2_atm: Optional[float] = None        # 'open'
    total_carbon_M: Optional[float] = None    # 'closed'
    total_carbon_mol: Optional[float] = None  # 'sealed'
    v_liquid_L: Optional[float] = None         # 'sealed'
    v_gas_L: Optional[float] = None            # 'sealed'
    # constants (defaults are the sourced 25 C records; a caller may inject their own SourcedConstant):
    K1: SourcedConstant = K1_CARBONIC_25C
    K2: SourcedConstant = K2_CARBONIC_25C
    Kw: SourcedConstant = KW_25C
    K_H: SourcedConstant = KH_CO2_25C

    def __post_init__(self):
        if self.activity_model not in ("ideal", "davies"):
            raise InvalidParameterError("activity_model must be 'ideal' or 'davies'")
        if self.mode not in _MODES:
            raise InvalidParameterError(f"mode must be one of {_MODES}")
        if not (math.isfinite(self.sodium_M) and self.sodium_M >= 0):
            raise InvalidParameterError("sodium_M must be finite and >= 0")
        # the source-domain guard binds in ALL modes and ALL activity models (acetate-model discipline A2).
        _require_source_temperature(self.temperature_K)
        _require_constant_at_source_state(self.K1, role="K1")
        _require_constant_at_source_state(self.K2, role="K2")
        _require_constant_at_source_state(self.Kw, role="Kw")
        _require_constant_at_source_state(self.K_H, role="K_H")
        # mode-specific required inputs:
        if self.mode == "open":
            if not (self.p_co2_atm is not None and math.isfinite(self.p_co2_atm) and self.p_co2_atm > 0):
                raise InvalidParameterError("mode='open' requires p_co2_atm (finite, > 0 atm)")
        elif self.mode == "closed":
            if not (self.total_carbon_M is not None and math.isfinite(self.total_carbon_M) and self.total_carbon_M >= 0):
                raise InvalidParameterError("mode='closed' requires total_carbon_M (finite, >= 0 mol/L)")
        else:  # sealed
            if not (self.total_carbon_mol is not None and math.isfinite(self.total_carbon_mol)
                    and self.total_carbon_mol >= 0):
                raise InvalidParameterError("mode='sealed' requires total_carbon_mol (finite, >= 0 mol)")
            if not (self.v_liquid_L is not None and math.isfinite(self.v_liquid_L) and self.v_liquid_L > 0):
                raise InvalidParameterError("mode='sealed' requires v_liquid_L (finite, > 0 L)")
            if not (self.v_gas_L is not None and math.isfinite(self.v_gas_L) and self.v_gas_L > 0):
                raise InvalidParameterError("mode='sealed' requires v_gas_L (finite, > 0 L)")


@dataclass(frozen=True)
class CarbonateSpeciationResult:
    pH: float                     # PRIMARY pH: activity-based under davies, == p[H] under ideal
    pH_concentration: float       # p[H] = -log10([H+]/c_ref)
    pH_activity: float            # -log10(gamma_1*[H+]/c_ref)
    c_ref_M: float
    verdict: str
    mode: str
    # aqueous speciation (mol/L):
    co2aq_M: float                # [CO2(aq)] == [H2CO3*]
    hco3_M: float
    co3_M: float
    h_plus_M: float
    oh_minus_M: float
    na_plus_M: float
    total_dissolved_carbon_M: float   # [CO2(aq)] + [HCO3-] + [CO3(2-)]
    # gas phase:
    p_co2_atm: float              # fixed input ('open'); diagnostic/output ('closed'/'sealed')
    gas_carbon_mol: float         # CO2 in the headspace (mol); 0 for 'open'/'closed' (no modelled finite headspace)
    dissolved_carbon_mol: float   # aqueous carbon (mol) = total_dissolved_carbon_M * v_liquid_L ('sealed'); else NaN
    # activity / numerics:
    ionic_strength_M: float
    activity_model: str
    gamma_monovalent: float       # gamma(|z|=1); 1.0 ideal
    gamma_divalent: float         # gamma(|z|=2) == gamma_monovalent**4; 1.0 ideal
    solver_agreement_residual: float   # |route1 - route2| on the primary unknown (h, or P_CO2 for sealed)
    charge_balance_residual: float
    carbon_balance_residual: float     # mode-appropriate carbon closure residual
    davies_iterations: int
    caveats: tuple = ()


# ----------------------------------------------------------------------------------------- activity bookkeeping
def _gammas(ionic: float, A: float) -> tuple[float, float]:
    """(gamma_1, gamma_2): the Davies activity coefficients for |z|=1 and |z|=2.  log10 gamma_z = -A z^2 f(I), so
    gamma_2 = gamma_1^4.  The monovalent kernel is the ACETATE module's `_davies_gamma`, re-used verbatim so the two
    models share one activity law; the divalent weighting is the only addition."""
    g1 = _davies_gamma(ionic, A)
    return g1, g1 ** 4


def _effective_constants(K1: float, K2: float, Kw: float, g1: float, g2: float) -> tuple[float, float, float]:
    """Concentration-basis constants from thermodynamic ones at activity coefficients (g1, g2).
      K1_c = [H+][HCO3-]/[CO2aq] = K1 / (g_H g_HCO3) = K1 / g1^2         (CO2aq neutral, gamma ~ 1)
      K2_c = [H+][CO3]/[HCO3-]   = K2 * g_HCO3/(g_H g_CO3) = K2 * g1/(g1 g2) = K2 / g2
      Kw_c = [H+][OH-]           = Kw / (g_H g_OH) = Kw / g1^2
    K_H is a neutral-species solubility: the dissolved-CO2 activity coefficient (salting-out) is omitted, so K_H is
    NOT rescaled here (documented on KH_CO2_25C)."""
    g1sq = g1 * g1
    return K1 / g1sq, K2 / g2, Kw / g1sq


def _ionic_strength(h: float, oh: float, hco3: float, co3: float, na: float) -> float:
    """I = 0.5 * sum c_i z_i^2.  z: H+ +1, OH- -1, HCO3- -1, Na+ +1 (all z^2 = 1); CO3(2-) z^2 = 4."""
    return 0.5 * (h + oh + hco3 + 4.0 * co3 + na)


# ----------------------------------------------------------------------------- per-mode speciation at fixed constants
def _polish_root(coeffs, r: float, iters: int = 4) -> float:
    """Newton-polish a positive polynomial root `r` against the EXACT polynomial (coeffs highest-degree first, the
    np.roots convention).  np.roots' companion-matrix eigenvalue root loses RELATIVE precision for a root many orders
    of magnitude below the coefficient scale -- precisely the basic / small-[H+] regime of a carbonate solution, and
    worse for the quartic (closed) than the cubic (open).  2-4 Newton steps on the exact polynomial restore full
    double precision, so the polynomial route agrees with the bracketed charge-residual route to the gate's tolerance
    (d'Alembert's carbonate refutation: the eigenvalue root is a good initial guess, not a final answer).  This keeps
    the two routes INDEPENDENT -- a bug in these coefficients would still make the polished root disagree with the
    (separately-formulated) charge-residual bracket, so the cross-check's power to catch an algebra error is intact;
    only the np.roots conditioning noise is removed.  P and P' via one combined Horner sweep."""
    if not (math.isfinite(r) and r > 0):
        return r
    for _ in range(iters):
        p, dp = coeffs[0], 0.0
        for c in coeffs[1:]:
            dp = dp * r + p
            p = p * r + c
        if not (math.isfinite(p) and math.isfinite(dp)) or dp == 0.0:
            break
        step = p / dp
        r_new = r - step
        if not (math.isfinite(r_new) and r_new > 0):
            break
        r = r_new
        if abs(step) <= 1e-18 * r:
            break
    return r


def _open_cubic_root(Kw_c: float, K1_c: float, K2_c: float, Caq: float, Na: float) -> float:
    """Route 1 for 'open': the unique positive real root of h^3 + Na h^2 - (Kw_c + K1_c Caq) h - 2 K1_c K2_c Caq = 0,
    Newton-polished (np.roots loses precision for the tiny roots of basic solutions).  NaN (not an exception) if no
    usable root -- the admission gate is the single fail-closed decision point."""
    coeffs = [1.0, Na, -(Kw_c + K1_c * Caq), -2.0 * K1_c * K2_c * Caq]
    try:
        roots = np.roots(coeffs)
    except (np.linalg.LinAlgError, ValueError):
        return float("nan")
    real = [float(r.real) for r in roots if abs(r.imag) < 1e-18 * max(1.0, abs(r.real)) and r.real > 0]
    return _polish_root(coeffs, min(real)) if real else float("nan")


def _open_charge_residual(h: float, Kw_c: float, K1_c: float, K2_c: float, Caq: float, Na: float) -> float:
    oh = Kw_c / h
    hco3 = K1_c * Caq / h
    co3 = K1_c * K2_c * Caq / (h * h)
    return (Na + h) - (oh + hco3 + 2.0 * co3)


def _open_brentq_root(Kw_c: float, K1_c: float, K2_c: float, Caq: float, Na: float) -> float:
    """Route 2 for 'open': bracketed bisection on the charge-balance residual (independent ALGORITHM, same data).
    xtol is driven to ~0 so the RELATIVE rtol governs convergence: a basic root sits at h ~ 1e-13, where an absolute
    xtol of 1e-18 would be a coarse ~1e-5 relative, disagreeing with the polished polynomial route (d'Alembert)."""
    lo, hi = 1e-30, max(1.0, Na + 1.0)   # lo below any physical basic root but above where h*h underflows
    try:
        return float(brentq(_open_charge_residual, lo, hi, args=(Kw_c, K1_c, K2_c, Caq, Na), xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _closed_denominator(h: float, K1_c: float, K2_c: float) -> float:
    return h * h + K1_c * h + K1_c * K2_c


def _closed_charge_residual(h: float, Kw_c: float, K1_c: float, K2_c: float, C_T: float, Na: float) -> float:
    """Charge balance for 'closed' with Caq eliminated by the dissolved-carbon total:
    Caq = C_T h^2 / D, [HCO3-] = C_T K1_c h / D, [CO3] = C_T K1_c K2_c / D, D = h^2 + K1_c h + K1_c K2_c."""
    D = _closed_denominator(h, K1_c, K2_c)
    if not (math.isfinite(D) and D > 0):
        return float("nan")
    hco3 = C_T * K1_c * h / D
    co3 = C_T * K1_c * K2_c / D
    oh = Kw_c / h
    return (Na + h) - (oh + hco3 + 2.0 * co3)


def _closed_quartic_root(Kw_c: float, K1_c: float, K2_c: float, C_T: float, Na: float) -> float:
    """Route 2 for 'closed': the unique positive real root of the quartic obtained by clearing h*D from the charge
    balance: h^4 + (Na+a) h^3 + (Na a + b - Kw_c - C_T a) h^2 + (Na b - Kw_c a - 2 C_T b) h - Kw_c b = 0,
    with a = K1_c, b = K1_c K2_c."""
    a, b = K1_c, K1_c * K2_c
    coeffs = [1.0, Na + a, Na * a + b - Kw_c - C_T * a, Na * b - Kw_c * a - 2.0 * C_T * b, -Kw_c * b]
    try:
        roots = np.roots(coeffs)
    except (np.linalg.LinAlgError, ValueError):
        return float("nan")
    real = [float(r.real) for r in roots if abs(r.imag) < 1e-18 * max(1.0, abs(r.real)) and r.real > 0]
    return _polish_root(coeffs, min(real)) if real else float("nan")


def _closed_brentq_root(Kw_c: float, K1_c: float, K2_c: float, C_T: float, Na: float) -> float:
    """Route 1 for 'closed': bracketed bisection on the charge-balance residual.  xtol -> 0 so the RELATIVE rtol
    governs: a basic root (excess base over carbon) sits at h ~ 1e-13..1e-14, where the gate's charge residual is a
    difference of large numbers amplified by Kw_c/h^2, so h must be relative-accurate, not just absolute-accurate
    (the shared root cause both adversaries found for the basic regime)."""
    lo, hi = 1e-30, max(1.0, Na + C_T + 1.0)   # lo below any physical basic root but above where h*h underflows
    try:
        return float(brentq(_closed_charge_residual, lo, hi, args=(Kw_c, K1_c, K2_c, C_T, Na), xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _caq_from_charge_balance(h: float, Kw_c: float, K1_c: float, K2_c: float, Na: float) -> float:
    """[CO2(aq)] implied by charge balance at a given h (used by the 'sealed' coupling):
    Na + h - Kw_c/h = Caq (K1_c/h + 2 K1_c K2_c/h^2)  =>  Caq = (Na + h - Kw_c/h) / (K1_c/h + 2 K1_c K2_c/h^2).
    Returns NaN if the implied Caq is not a usable nonnegative number (the only physical branch)."""
    denom = K1_c / h + 2.0 * K1_c * K2_c / (h * h)
    if not (math.isfinite(denom) and denom > 0):
        return float("nan")
    caq = (Na + h - Kw_c / h) / denom
    return caq if (math.isfinite(caq) and caq >= 0) else float("nan")


def _sealed_carbon_residual_in_h(h: float, Kw_c: float, K1_c: float, K2_c: float,
                                 Na: float, n_C: float, V_liq: float, V_gas: float, K_H: float, RT: float) -> float:
    """Route 1 for 'sealed': bracket h.  Caq from charge balance; total carbon = liquid (all 3 dissolved species) +
    headspace CO2 (ideal gas, n = P V/(RT), P = Caq/K_H).  Residual = modelled total carbon - n_C."""
    caq = _caq_from_charge_balance(h, Kw_c, K1_c, K2_c, Na)
    if not (math.isfinite(caq) and caq >= 0):
        return float("nan")
    c_dissolved_M = caq * (1.0 + K1_c / h + K1_c * K2_c / (h * h))
    n_liq = c_dissolved_M * V_liq
    n_gas = (caq / K_H) * V_gas / RT        # P_CO2 = caq/K_H
    return (n_liq + n_gas) - n_C


def _sealed_h_route(Kw_c, K1_c, K2_c, Na, n_C, V_liq, V_gas, K_H, RT) -> float:
    # The charge-balance [CO2(aq)] goes NEGATIVE (-> NaN residual) below h0, the h where it hits zero:
    # Na + h0 - Kw_c/h0 = 0  =>  h0 = (-Na + sqrt(Na^2 + 4 Kw_c))/2.  Bracket STRICTLY above h0 (where the residual
    # is finite and = -n_C < 0) up to a large h (where the dissolved carbon alone overshoots n_C, residual > 0).
    h0 = 0.5 * (-Na + math.sqrt(Na * Na + 4.0 * Kw_c))
    lo = h0 * (1.0 + 1e-9) if h0 > 0 else 1e-300
    hi = max(1.0, Na + 1.0)
    try:
        return float(brentq(_sealed_carbon_residual_in_h, lo, hi,
                            args=(Kw_c, K1_c, K2_c, Na, n_C, V_liq, V_gas, K_H, RT), xtol=1e-300, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _sealed_carbon_residual_in_p(p_co2: float, Kw_c, K1_c, K2_c, Na, n_C, V_liq, V_gas, K_H, RT) -> float:
    """Route 2 for 'sealed': bracket P_CO2 (the GENUINELY independent elimination).  Caq = K_H P_CO2 pins the open
    cubic -> h(P_CO2); then total carbon = liquid + headspace.  Residual = modelled total carbon - n_C."""
    caq = K_H * p_co2
    h = _open_cubic_root(Kw_c, K1_c, K2_c, caq, Na)
    if not (math.isfinite(h) and h > 0):
        return float("nan")
    c_dissolved_M = caq * (1.0 + K1_c / h + K1_c * K2_c / (h * h))
    n_liq = c_dissolved_M * V_liq
    n_gas = p_co2 * V_gas / RT
    return (n_liq + n_gas) - n_C


def _sealed_p_route(Kw_c, K1_c, K2_c, Na, n_C, V_liq, V_gas, K_H, RT) -> float:
    # P_CO2 upper bound: if ALL carbon were gas, P = n_C RT / V_gas; the true P is below that.  Pad x2 for the bracket.
    hi = max(1e-30, 2.0 * n_C * RT / V_gas) if n_C > 0 else 1.0
    lo = 1e-30
    try:
        return float(brentq(_sealed_carbon_residual_in_p, lo, hi,
                            args=(Kw_c, K1_c, K2_c, Na, n_C, V_liq, V_gas, K_H, RT), xtol=1e-30, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


# ------------------------------------------------------------------------------------- mode dispatch + admission
# A small record the solver and gate pass around: the two independent route values for the PRIMARY unknown (always
# [H+]), the adopted speciation, and the mode-appropriate gas quantities.  (Plain tuple, documented, acetate-style.)
def _speciate(mode: str, Kw_c: float, K1_c: float, K2_c: float, K_H: float, Na: float, system: "CarbonateWaterSystem",
              RT: float):
    """Solve one mode at FIXED (concentration-basis) constants by two independent routes.  Returns
    (h1, h2, h, caq, hco3, co3, oh, na_free, p_co2, c_dissolved_M, n_liq, n_gas).  h1/h2 are the two route [H+]s
    (their agreement is the solver cross-check); h is their mean.  na_free == Na (no ion pairs in this system)."""
    if mode == "open":
        caq = K_H * float(system.p_co2_atm)
        h1 = _open_cubic_root(Kw_c, K1_c, K2_c, caq, Na)
        h2 = _open_brentq_root(Kw_c, K1_c, K2_c, caq, Na)
        h = 0.5 * (h1 + h2)
        if not (math.isfinite(h) and h > 0):
            return h1, h2, float("nan"), caq, *([float("nan")] * 8)   # 12-tuple with (h1,h2,nan,caq) + 8 NaN
        hco3 = K1_c * caq / h
        co3 = K1_c * K2_c * caq / (h * h)
        oh = Kw_c / h
        c_dissolved_M = caq + hco3 + co3
        return h1, h2, h, caq, hco3, co3, oh, Na, float(system.p_co2_atm), c_dissolved_M, float("nan"), 0.0

    if mode == "closed":
        C_T = float(system.total_carbon_M)
        h1 = _closed_brentq_root(Kw_c, K1_c, K2_c, C_T, Na)
        h2 = _closed_quartic_root(Kw_c, K1_c, K2_c, C_T, Na)
        h = 0.5 * (h1 + h2)
        if not (math.isfinite(h) and h > 0):
            return h1, h2, float("nan"), *([float("nan")] * 9)   # 12-tuple with (h1,h2,nan) + 9 NaN
        D = _closed_denominator(h, K1_c, K2_c)
        caq = C_T * h * h / D
        hco3 = C_T * K1_c * h / D
        co3 = C_T * K1_c * K2_c / D
        oh = Kw_c / h
        c_dissolved_M = caq + hco3 + co3
        p_co2 = caq / K_H
        return h1, h2, h, caq, hco3, co3, oh, Na, p_co2, c_dissolved_M, float("nan"), 0.0

    # sealed
    n_C, V_liq, V_gas = float(system.total_carbon_mol), float(system.v_liquid_L), float(system.v_gas_L)
    h1 = _sealed_h_route(Kw_c, K1_c, K2_c, Na, n_C, V_liq, V_gas, K_H, RT)
    p2 = _sealed_p_route(Kw_c, K1_c, K2_c, Na, n_C, V_liq, V_gas, K_H, RT)
    h2 = _open_cubic_root(Kw_c, K1_c, K2_c, K_H * p2, Na) if (math.isfinite(p2) and p2 > 0) else float("nan")
    h = 0.5 * (h1 + h2)
    if not (math.isfinite(h) and h > 0):
        return h1, h2, float("nan"), *([float("nan")] * 9)   # 12-tuple with (h1,h2,nan) + 9 NaN
    caq = _caq_from_charge_balance(h, Kw_c, K1_c, K2_c, Na)
    if not (math.isfinite(caq) and caq >= 0):
        return h1, h2, h, float("nan"), *([float("nan")] * 8)   # 12-tuple with (h1,h2,h,nan) + 8 NaN
    hco3 = K1_c * caq / h
    co3 = K1_c * K2_c * caq / (h * h)
    oh = Kw_c / h
    c_dissolved_M = caq + hco3 + co3
    p_co2 = caq / K_H
    n_liq = c_dissolved_M * V_liq
    n_gas = p_co2 * V_gas / RT
    return h1, h2, h, caq, hco3, co3, oh, Na, p_co2, c_dissolved_M, n_liq, n_gas


def _verify_admission(*, mode: str, h1: float, h2: float, h: float, caq: float, hco3: float, co3: float, oh: float,
                      na_free: float, p_co2: float, c_dissolved_M: float, n_liq: float, n_gas: float,
                      Kw_c: float, K1_c: float, K2_c: float, K_H: float, Na: float, system: "CarbonateWaterSystem",
                      RT: float, activity_model: str, ionic_strength: float, davies_converged: bool,
                      davies_iterations: int) -> str:
    """The fail-closed admission gate.  A result earns a SOLVED_* verdict ONLY if every check holds; otherwise this
    raises NumericalVerificationError and no prediction is returned.  The single source of truth is the adopted h:
    the gate RE-DERIVES the speciation from it and the constants (its own check, not a rubber stamp of _speciate)."""
    problems = []
    # (1) two independent routes delivered a finite positive [H+] and agree.
    if not (math.isfinite(h1) and h1 > 0 and math.isfinite(h2) and h2 > 0):
        problems.append(f"a solver route failed to deliver a finite positive [H+] (route1={h1}, route2={h2})")
    elif abs(h1 - h2) > AGREEMENT_RTOL * max(h1, h2):
        problems.append(f"the two routes disagree beyond AGREEMENT_RTOL={AGREEMENT_RTOL:g} "
                        f"(|{h1}-{h2}|={abs(h1 - h2):g})")
    if not (math.isfinite(h) and h > 0):
        problems.append("the adopted [H+] is not finite/positive")
        raise NumericalVerificationError("admission refused: " + "; ".join(problems))

    # re-derive [CO2(aq)] from the adopted h per the mode's own definition, then everything else from (h, caq).
    oh_d = Kw_c / h
    if mode == "open":
        caq_d = K_H * float(system.p_co2_atm)
    elif mode == "closed":
        D = _closed_denominator(h, K1_c, K2_c)
        caq_d = float(system.total_carbon_M) * h * h / D if (math.isfinite(D) and D > 0) else float("nan")
    else:  # sealed: caq is pinned by charge balance at the adopted h
        caq_d = _caq_from_charge_balance(h, Kw_c, K1_c, K2_c, Na)
    if not (math.isfinite(caq_d) and caq_d >= -NONNEGATIVITY_ATOL):
        problems.append("the re-derived [CO2(aq)] is not a usable nonnegative number")
        raise NumericalVerificationError("admission refused: " + "; ".join(problems))
    hco3_d = K1_c * caq_d / h
    co3_d = K1_c * K2_c * caq_d / (h * h)

    # (2) charge balance closes on the re-derivation (divalent CO3 weighted x2).
    cb = abs((na_free + h) - (oh_d + hco3_d + 2.0 * co3_d))
    cb_allow = CHARGE_BALANCE_ATOL + CHARGE_BALANCE_RTOL * (Na + h + oh_d + hco3_d + 2.0 * co3_d)
    if cb > cb_allow:
        problems.append(f"charge balance does not close (residual {cb:g} > allowed {cb_allow:g})")

    # (3) reported speciation matches the re-derivation (catch a fabricated split).
    for name, rep, der, scale in (("CO2(aq)", caq, caq_d, max(1.0, caq_d)), ("HCO3-", hco3, hco3_d, max(1.0, hco3_d)),
                                  ("CO3(2-)", co3, co3_d, max(1.0, co3_d)), ("OH-", oh, oh_d, max(1.0, oh_d))):
        if not math.isfinite(rep) or abs(rep - der) > 1e-9 * scale:
            problems.append(f"reported {name} disagrees with the re-derivation from [H+] ({rep} vs {der})")

    # (4) non-negativity of every admitted concentration.
    concs = [caq_d, hco3_d, co3_d, h, oh_d, na_free]
    if min((c for c in concs if math.isfinite(c)), default=float("nan")) < -NONNEGATIVITY_ATOL \
            or any(not math.isfinite(c) for c in concs):
        problems.append("a species concentration is negative or non-finite")

    # (5) mode-appropriate carbon closure.
    if mode == "closed":
        C_T = float(system.total_carbon_M)
        if abs((caq_d + hco3_d + co3_d) - C_T) > MASS_BALANCE_RTOL * max(1.0, C_T):
            problems.append(f"dissolved-carbon balance does not close (sum={caq_d + hco3_d + co3_d}, C_T={C_T})")
    elif mode == "sealed":
        n_C, V_liq, V_gas = float(system.total_carbon_mol), float(system.v_liquid_L), float(system.v_gas_L)
        p_d = caq_d / K_H
        n_liq_d = (caq_d + hco3_d + co3_d) * V_liq
        n_gas_d = p_d * V_gas / RT
        if not (math.isfinite(p_d) and p_d >= -NONNEGATIVITY_ATOL):
            problems.append(f"re-derived P_CO2 is not nonnegative/finite ({p_d})")
        if not (math.isfinite(n_gas_d) and n_gas_d >= -NONNEGATIVITY_ATOL):
            problems.append(f"re-derived headspace CO2 moles not nonnegative/finite ({n_gas_d})")
        if abs((n_liq_d + n_gas_d) - n_C) > MASS_BALANCE_RTOL * max(1.0, n_C):
            problems.append(f"total-carbon (liquid+headspace) balance does not close (sum={n_liq_d + n_gas_d}, n_C={n_C})")
        # the reported gas/liquid split must match too (not just the aqueous re-derivation).
        if not (math.isfinite(n_gas) and abs(n_gas - n_gas_d) <= 1e-9 * max(1.0, n_gas_d)
                and math.isfinite(n_liq) and abs(n_liq - n_liq_d) <= 1e-9 * max(1.0, n_liq_d)):
            problems.append("reported headspace/liquid carbon split disagrees with the re-derivation")

    # (6) Davies: converged, and inside the model's ionic-strength domain.
    if activity_model == "davies":
        if not davies_converged:
            problems.append(f"the Davies ionic-strength fixed point did not converge within {DAVIES_MAX_ITERS} iters "
                            f"(took {davies_iterations})")
        if not math.isfinite(ionic_strength) or ionic_strength > DAVIES_I_MAX:
            problems.append(f"ionic strength {ionic_strength} is outside the Davies-model domain (<= {DAVIES_I_MAX} M)")

    if problems:
        raise NumericalVerificationError("admission refused: " + "; ".join(problems))
    return SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL if activity_model == "davies" else SOLVED_WITHIN_IDEAL_MODEL


# ----------------------------------------------------------------------------------------------- caveats
# Beyond this ionic strength the omitted CO2 salting-out (and the Davies form itself) make the result model-only.
SALTING_OUT_CAVEAT = (
    "ionic strength is high enough that the OMITTED dissolved-CO2 salting-out (Sechenov) correction to K_H and the "
    "Davies activity form both matter; the result is activity-MODEL-only here, not independently benchmarked")
SALTING_OUT_I_THRESHOLD = 0.1   # mol/L; the same demonstrated-agreement scale the acetate model uses, pending the
#   carbonate PHREEQC benchmark that will set the real agreement domain.


def solve(system: CarbonateWaterSystem, *, tol: float = DAVIES_FIXED_POINT_TOL) -> CarbonateSpeciationResult:
    """Solve the 0-D carbonate equilibrium + gas partition for the given mode, under the ideal or Davies activity
    model, by two independent algorithms that must agree.  Handed back ONLY if the admission gate certifies it."""
    Na = float(system.sodium_M)
    K10, K20, Kw0, K_H = system.K1.value, system.K2.value, system.Kw.value, system.K_H.value
    A = aq.DAVIES_A_25C.value                      # read at call time (so an identifiability swap would be seen)
    RT = R_GAS_L_ATM.value * float(system.temperature_K)
    gamma1 = 1.0
    davies_converged = (system.activity_model == "ideal")
    davies_iterations = 0
    ionic = float("nan")
    last = None
    K1_c = K2_c = Kw_c = float("nan")
    for i in range(1, DAVIES_MAX_ITERS + 1):
        davies_iterations = 0 if system.activity_model == "ideal" else i
        g1, g2 = (1.0, 1.0) if system.activity_model == "ideal" else _gammas(ionic if math.isfinite(ionic) else 0.0, A)
        # on the FIRST davies pass ionic is NaN -> treat as 0 (gamma=1), exactly like starting from the ideal guess.
        if system.activity_model == "davies" and not math.isfinite(ionic):
            g1, g2 = 1.0, 1.0
        K1_c, K2_c, Kw_c = _effective_constants(K10, K20, Kw0, g1, g2)
        last = _speciate(system.mode, Kw_c, K1_c, K2_c, K_H, Na, system, RT)
        h = last[2]
        if not (math.isfinite(h) and h > 0):
            break
        caq, hco3, co3, oh = last[3], last[4], last[5], last[6]
        ionic = _ionic_strength(h, oh, hco3, co3, Na)
        if system.activity_model == "ideal":
            gamma1 = 1.0
            break
        g1_new, _ = _gammas(ionic, A)
        if abs(g1_new - gamma1) <= tol * gamma1:
            # converged: re-solve ONCE at the accepted gamma so every reported number is consistent with it.
            gamma1 = g1_new
            g1, g2 = gamma1, gamma1 ** 4
            K1_c, K2_c, Kw_c = _effective_constants(K10, K20, Kw0, g1, g2)
            last = _speciate(system.mode, Kw_c, K1_c, K2_c, K_H, Na, system, RT)
            h = last[2]
            if math.isfinite(h) and h > 0:
                # last = (h1,h2,h,caq,hco3,co3,oh,na_free,...): recompute I from oh=last[6], hco3=last[4], co3=last[5].
                ionic = _ionic_strength(h, last[6], last[4], last[5], Na)
                davies_converged = True
            break
        gamma1 = g1_new

    h1, h2, h, caq, hco3, co3, oh, na_free, p_co2, c_dissolved_M, n_liq, n_gas = last
    gamma2 = gamma1 ** 4

    verdict = _verify_admission(
        mode=system.mode, h1=h1, h2=h2, h=h, caq=caq, hco3=hco3, co3=co3, oh=oh, na_free=na_free,
        p_co2=p_co2, c_dissolved_M=c_dissolved_M, n_liq=n_liq, n_gas=n_gas,
        Kw_c=Kw_c, K1_c=K1_c, K2_c=K2_c, K_H=K_H, Na=Na, system=system, RT=RT,
        activity_model=system.activity_model, ionic_strength=ionic,
        davies_converged=davies_converged, davies_iterations=davies_iterations)

    c_ref = C_REF.value
    pH_concentration = -math.log10(h / c_ref)
    pH_activity = -math.log10(gamma1 * h / c_ref)
    pH = pH_activity if system.activity_model == "davies" else pH_concentration

    caveats = ()
    if math.isfinite(ionic) and ionic > SALTING_OUT_I_THRESHOLD:
        caveats = (SALTING_OUT_CAVEAT,)

    cb_resid = abs((na_free + h) - (oh + hco3 + 2.0 * co3))
    if system.mode == "closed":
        carbon_resid = abs((caq + hco3 + co3) - float(system.total_carbon_M))
    elif system.mode == "sealed":
        carbon_resid = abs((n_liq + n_gas) - float(system.total_carbon_mol))
    else:
        carbon_resid = 0.0   # open: C_T is an output, not a constraint

    return CarbonateSpeciationResult(
        pH=pH, pH_concentration=pH_concentration, pH_activity=pH_activity, c_ref_M=c_ref, verdict=verdict,
        mode=system.mode, co2aq_M=caq, hco3_M=hco3, co3_M=co3, h_plus_M=h, oh_minus_M=oh, na_plus_M=na_free,
        total_dissolved_carbon_M=c_dissolved_M, p_co2_atm=p_co2, gas_carbon_mol=(n_gas if system.mode == "sealed" else 0.0),
        dissolved_carbon_mol=(n_liq if system.mode == "sealed" else float("nan")),
        ionic_strength_M=ionic, activity_model=system.activity_model,
        gamma_monovalent=gamma1, gamma_divalent=gamma2,
        solver_agreement_residual=abs(h1 - h2), charge_balance_residual=cb_resid,
        carbon_balance_residual=carbon_resid, davies_iterations=davies_iterations, caveats=caveats)


# --------------------------------------------------------------------------------- the independent-benchmark obligation
def phreeqc_benchmark_obligation() -> BenchmarkObligation:
    """PHREEQC is the named independent cross-tool and the carbonate system is NATIVE to its default database
    (phreeqc.dat).  It is NOT installed in the committed baseline, so until the benchmark is run (in an isolated
    scratch venv -- see benchmarks/carbonate_phreeqc/) the independent cross-check is EXTERNAL_VALIDATION_UNAVAILABLE.
    The shipped textbook anchors (pH ~ 5.6 open-to-air / ~8.3 NaHCO3 / ~11.6 Na2CO3) are equation/implementation
    VERIFICATION against the SAME constants, NOT independent experimental validation."""
    return BenchmarkObligation(
        tool="PHREEQC",
        verdict=EXTERNAL_VALIDATION_UNAVAILABLE,
        recipe={
            "import": "phreeqpython in an ISOLATED scratch venv (never the committed baseline)",
            "database": "phreeqc.dat (carbonate system is native); pin the sha256, commit the reference column",
            "species": ("CO2(aq)", "HCO3-", "CO3-2", "H+", "OH-", "Na+", "CO2(g)"),
            "modes": {
                "open": "SOLUTION + EQUILIBRIUM_PHASES CO2(g) at the fixed log P_CO2; compare pH + C_T",
                "closed": "SOLUTION with C(4) total fixed, no gas phase; compare pH + speciation",
                "sealed": "SOLUTION + GAS_PHASE -fixed_volume at V_gas; compare pH + P_CO2 + dissolved/gas split",
            },
            "compare": "PHREEQC pH / P_CO2 / speciation vs CarbonateWaterSystem.solve(); record |dpH| and the domain",
            "independence_caveat": "PHREEQC and this model agreeing on a shared constant lineage is solver "
                                   "VERIFICATION, not independent validation of the constants (directive); a MEASURED "
                                   "end-state (e.g. NaHCO3-solution pH) would be the stronger V3 rung and is not "
                                   "fabricated if unavailable.",
        },
        comparison=None)

