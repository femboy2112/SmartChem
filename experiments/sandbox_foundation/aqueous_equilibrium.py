"""Wave F -- a SOURCE-BACKED zero-dimensional aqueous equilibrium: acetic acid / acetate / water.

Ooh yeah, can do -- but NO guessing.  This is the first real-chemistry foothold toward 3.0: a CURATED, closed
species set (NOT arbitrary chemistry by formula similarity) whose equilibrium constants are SOURCED from defensible
tertiary references and carry a stated uncertainty.  Nothing here is a fabricated number; where an independent
benchmark cannot be run in this environment it is preserved as an explicit UNKNOWN obligation, never faked.

SPECIES (explicit chemical identities + net charges -- the #105 single-global-charge wall is sidestepped by
enumerating a FIXED set, not by solving general local-charge structural chemistry):
    HAc  acetic acid     charge  0
    Ac-  acetate         charge -1
    H+   hydronium       charge +1
    OH-  hydroxide       charge -1
    (H2O the solvent, activity 1 in the dilute reference)

EQUILIBRIA (ideal-dilute reference, activity = concentration unless a Davies correction is requested):
    HAc <-> H+ + Ac-      Ka = [H+][Ac-]/[HAc]
    H2O <-> H+ + OH-      Kw = [H+][OH-]
MASS BALANCE:   C_T = [HAc] + [Ac-]              (total acetate)
CHARGE BALANCE: [Na+] + [H+] = [OH-] + [Ac-]     ([Na+] = added sodium from NaAc / NaOH, >= 0)

Eliminating the minor species gives a CUBIC in h = [H+]:
    h^3 + (Ka + Na) h^2 - (Kw + Ka*C_T - Ka*Na) h - Ka*Kw = 0.
Two INDEPENDENT numerical routes solve it and must agree (this is a cross-check of the SOLVER, not a second
thermodynamic database -- the directive's warning that two solvers on one database are not independent is
respected; the database here is the single sourced constant set, and the two routes are different ALGORITHMS):
  (1) numpy.roots on the exact cubic coefficients, take the unique positive real root;
  (2) a bracketed bisection (scipy.optimize.brentq) on the charge-balance residual f(h).

NONIDEALITY: the ideal model is the baseline.  An optional DAVIES activity correction (a fixed-point in ionic
strength) is provided and DOCUMENTED to shift the predicted pH -- it is the first nonideal refinement, not a claim
that the ideal model is exact.

INDEPENDENT BENCHMARK: Reaktoro is named by the directive as the cross-tool.  It is NOT installed in this
environment, so `reaktoro_benchmark_obligation()` returns the EXACT recipe + an UNKNOWN verdict rather than a
fabricated comparison.  The shipped validation instead uses (a) the two-route solver agreement and (b) SOURCED
textbook pH anchors (0.1 M acetic acid -> pH ~ 2.87; an equimolar acetate buffer -> pH = pKa).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.optimize import brentq

from experiments.sandbox_foundation.twocell import InvalidParameterError


# --------------------------------------------------------------------------------- sourced constants (provenance)
@dataclass(frozen=True)
class SourcedConstant:
    """A physical constant with its PROVENANCE: value, +/- uncertainty, units, temperature, citation, and a status
    (SOURCED = a defensible tertiary reference; DERIVED = computed from sourced values with a method; UNKNOWN = not
    available, never fabricated).  A decorative / fabricated uncertainty is banned -- the uncertainty must be a real
    spread from the source or a conservative bound."""
    name: str
    value: float
    uncertainty: float
    units: str
    T_K: float
    source: str
    status: str = "SOURCED"
    note: str = ""

    def __post_init__(self):
        if self.status not in ("SOURCED", "DERIVED", "UNKNOWN"):
            raise InvalidParameterError("status must be SOURCED / DERIVED / UNKNOWN")
        if self.status != "UNKNOWN":
            if not (math.isfinite(self.value) and self.value > 0):
                raise InvalidParameterError("a SOURCED/DERIVED constant must be finite and > 0")
            if not (math.isfinite(self.uncertainty) and self.uncertainty >= 0):
                raise InvalidParameterError("uncertainty must be finite and >= 0 (a fabricated error bar is banned)")
            if not self.source.strip():
                raise InvalidParameterError("a SOURCED/DERIVED constant must cite its source")


# Ka(acetic acid) = 1.75e-5, pKa = 4.756 at 25 C.  CRC Handbook of Chemistry and Physics, 84th ed. (2004),
# as tabulated by multiple independent textbook/LibreTexts compilations (corroborated, tertiary).  Uncertainty:
# the common tabulated spread is pKa 4.74-4.76 across sources -> ~+/-1e-6 on Ka (a conservative inter-source bound).
KA_ACETIC_25C = SourcedConstant(
    "Ka_acetic_acid", 1.75e-5, 1.0e-6, "dimensionless (molar, ideal reference)", 298.15,
    "CRC Handbook of Chemistry and Physics, 84th ed. (2004); corroborated by LibreTexts E1 acid-dissociation table "
    "and multiple general-chemistry appendices (pKa = 4.756).", "SOURCED",
    "Ideal-dilute thermodynamic Ka at 25 C; the inter-source pKa spread (~4.74-4.76) sets the uncertainty.")

# Kw = 1.0e-14 at 25 C (pKw ~ 14.00; high-precision tables give pKw ~ 13.995, Kw ~ 1.01e-14).  Standard reference.
KW_25C = SourcedConstant(
    "Kw_water", 1.0e-14, 1.0e-16, "dimensionless (molar, ideal reference)", 298.15,
    "Standard aqueous ion product at 25 C (LibreTexts Water Ionization; general-chemistry references); "
    "high-precision value pKw = 13.995.", "SOURCED",
    "The high-precision pKw ~ 13.995 (Kw ~ 1.01e-14) sets the ~1e-16 uncertainty band around 1.0e-14.")

# Debye-Huckel/Davies A parameter at 25 C (mol^-1/2 L^1/2), standard aqueous value ~0.509-0.510.
DAVIES_A_25C = SourcedConstant(
    "davies_A", 0.509, 0.001, "kg^1/2 mol^-1/2", 298.15,
    "Debye-Huckel limiting-law coefficient A at 25 C (standard electrolyte-chemistry value ~0.509-0.511).",
    "SOURCED", "Used by the optional Davies activity correction; the ideal model does not use it.")


# --------------------------------------------------------------------------------- the curated system
@dataclass(frozen=True)
class AcetateWaterSystem:
    """A curated acetic-acid / acetate / water system at fixed T.  total_acetic_M = total acetate C_T (mol/L);
    sodium_M = added Na+ (from NaAc or NaOH, >= 0).  activity_model in {'ideal','davies'}."""
    total_acetic_M: float
    sodium_M: float = 0.0
    temperature_K: float = 298.15
    Ka: SourcedConstant = KA_ACETIC_25C
    Kw: SourcedConstant = KW_25C
    activity_model: str = "ideal"

    def __post_init__(self):
        if not (math.isfinite(self.total_acetic_M) and self.total_acetic_M >= 0):
            raise InvalidParameterError("total_acetic_M must be finite and >= 0")
        if not (math.isfinite(self.sodium_M) and self.sodium_M >= 0):
            raise InvalidParameterError("sodium_M must be finite and >= 0")
        if self.activity_model not in ("ideal", "davies"):
            raise InvalidParameterError("activity_model must be 'ideal' or 'davies'")
        if abs(self.temperature_K - 298.15) > 0.01 and self.activity_model != "ideal":
            raise InvalidParameterError("the sourced constants are 25 C only; a davies correction off 25 C is "
                                        "out of the sourced domain (fail closed rather than extrapolate)")


@dataclass(frozen=True)
class SpeciationResult:
    pH: float
    h_plus_M: float
    oh_minus_M: float
    hac_M: float
    ac_minus_M: float
    ionic_strength_M: float
    activity_model: str
    solver_agreement_residual: float      # |route1 - route2| on [H+]; a SOLVER cross-check, not a DB cross-check
    gamma_monovalent: float               # activity coefficient of a +/-1 ion (1.0 in the ideal model)
    charge_balance_residual: float        # |[Na+]+[H+]-[OH-]-[Ac-]| at the solution (must be ~0)


def _cubic_positive_root(Ka: float, Kw: float, C_T: float, Na: float) -> float:
    """Route 1: numpy.roots on h^3 + (Ka+Na) h^2 - (Kw + Ka*C_T - Ka*Na) h - Ka*Kw = 0; the unique positive real."""
    coeffs = [1.0, Ka + Na, -(Kw + Ka * C_T - Ka * Na), -Ka * Kw]
    roots = np.roots(coeffs)
    real = [float(r.real) for r in roots if abs(r.imag) < 1e-18 * max(1.0, abs(r.real)) and r.real > 0]
    if not real:
        raise InvalidParameterError("no positive real root for [H+]; inputs are unphysical")
    return min(real)   # the physically relevant root (the others, if any, are spurious large roots)


def _charge_balance_residual(h: float, Ka: float, Kw: float, C_T: float, Na: float) -> float:
    ac = Ka * C_T / (h + Ka)
    oh = Kw / h
    return (Na + h) - (oh + ac)


def _brentq_root(Ka: float, Kw: float, C_T: float, Na: float) -> float:
    """Route 2: bracketed bisection on the charge-balance residual (an independent ALGORITHM, same sourced data)."""
    lo, hi = 1e-20, max(1.0, C_T + Na + 1.0)
    return float(brentq(_charge_balance_residual, lo, hi, args=(Ka, Kw, C_T, Na), xtol=1e-18, rtol=1e-14))


def _davies_gamma(ionic: float, A: float) -> float:
    """Davies activity coefficient of a +/-1 ion: log10 g = -A (sqrt(I)/(1+sqrt(I)) - 0.3 I), I = ionic strength."""
    if ionic <= 0:
        return 1.0
    s = math.sqrt(ionic)
    return float(10.0 ** (-A * (s / (1.0 + s) - 0.3 * ionic)))


def solve(system: AcetateWaterSystem, *, tol: float = 1e-9) -> SpeciationResult:
    """Solve the 0-D equilibrium for [H+] / pH / speciation by TWO independent algorithms (which must agree), under
    the ideal or Davies activity model.  For 'davies' the effective Ka/Kw are the thermodynamic constants divided by
    the relevant activity-coefficient product, iterated to a self-consistent ionic strength (a fixed point)."""
    C_T, Na = float(system.total_acetic_M), float(system.sodium_M)
    Ka0, Kw0 = system.Ka.value, system.Kw.value
    A = DAVIES_A_25C.value
    gamma = 1.0
    for _ in range(100):
        # concentration-basis constants: Ka_c = Ka / (gamma_H gamma_Ac / gamma_HAc) = Ka / gamma^2 (HAc neutral,
        # gamma_HAc ~ 1); Kw_c = Kw / (gamma_H gamma_OH) = Kw / gamma^2.
        g2 = gamma * gamma
        Ka_c, Kw_c = Ka0 / g2, Kw0 / g2
        h1 = _cubic_positive_root(Ka_c, Kw_c, C_T, Na)
        h2 = _brentq_root(Ka_c, Kw_c, C_T, Na)
        h = 0.5 * (h1 + h2)
        ac = Ka_c * C_T / (h + Ka_c)
        oh = Kw_c / h
        ionic = 0.5 * (h + oh + ac + Na)         # 0.5 * sum c_i z_i^2 ; all monovalent so z^2 = 1
        if system.activity_model == "ideal":
            break
        g_new = _davies_gamma(ionic, A)
        if abs(g_new - gamma) <= tol * gamma:
            gamma = g_new
            break
        gamma = g_new
    hac = C_T - ac
    return SpeciationResult(
        pH=-math.log10(h), h_plus_M=h, oh_minus_M=oh, hac_M=hac, ac_minus_M=ac,
        ionic_strength_M=ionic, activity_model=system.activity_model,
        solver_agreement_residual=abs(h1 - h2), gamma_monovalent=gamma,
        charge_balance_residual=abs(_charge_balance_residual(h, Ka_c, Kw_c, C_T, Na)))


# --------------------------------------------------------------------------------- the independent-benchmark obligation
@dataclass(frozen=True)
class BenchmarkObligation:
    """The record the directive requires for an independent-tool cross-check, with the verdict UNKNOWN until the
    tool is actually run -- never a fabricated number."""
    tool: str
    status: str                 # RUN / UNAVAILABLE_UNKNOWN
    recipe: dict = field(default_factory=dict)
    verdict: Optional[str] = None


def reaktoro_benchmark_obligation() -> BenchmarkObligation:
    """Reaktoro is NOT installed in this environment, so the independent cross-check is an explicit UNKNOWN
    obligation carrying the EXACT recipe to run it later -- the directive's 'preserve UNKNOWN, deliver the research
    instrument' path.  No numerical comparison is fabricated to fill it."""
    return BenchmarkObligation(
        tool="Reaktoro",
        status="UNAVAILABLE_UNKNOWN",
        recipe={
            "import": "reaktoro (ABSENT in this venv; do not install into the committed baseline)",
            "database": "to record: the exact thermodynamic database + version (e.g. PHREEQC / SUPCRT)",
            "activity_model": "to record: the aqueous activity model chosen (must be consistent with the database)",
            "species": ("H2O", "H+", "OH-", "CH3COOH(aq)", "CH3COO-", "Na+"),
            "conditions": "T = 298.15 K, P = 1 bar, total acetate C_T, added Na+ sodium_M",
            "compare": "Reaktoro equilibrium pH + speciation vs AcetateWaterSystem.solve(); record |dpH| and the "
                       "temperature/concentration/ionic-strength domain of agreement",
            "independence_caveat": "Reaktoro and this model sharing an underlying thermodynamic database would NOT "
                                   "be independent corroboration of that database (directive); the sourced-constant "
                                   "provenance above is the primary evidence, the two-route solver agreement the "
                                   "numerical cross-check.",
        },
        verdict=None)
