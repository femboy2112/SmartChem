"""Wave F -- a SOURCE-BACKED zero-dimensional aqueous equilibrium: acetic acid / acetate / water.

Ooh yeah, can do -- but NO guessing.  This is the first real-chemistry foothold toward 3.0: a CURATED, closed
species set (NOT arbitrary chemistry by formula similarity) whose equilibrium constants are SOURCED from defensible
tertiary references and carry a stated uncertainty.  Nothing here is a fabricated number; where an independent
benchmark cannot be run in this environment it is preserved as an explicit UNKNOWN obligation, never faked.

Wave A surgery (intellectual-honesty pass -- I am Beth; I do not leave a patient claiming a vitality it does not
have).  Four things were quietly lying and have been cut out:
  * pH was reported as -log10([H+]) even under a nonideal activity model -- a molarity number wearing the IUPAC
    pH label.  pH is defined on H+ ACTIVITY (IUPAC Gold Book P04524: pH = -log10(a_H+), molality/activity-based).
    We now distinguish p[H] (concentration) from pH_activity, declare the reference concentration c_ref explicitly,
    and in a nonideal model the PRIMARY pH is the activity value.  This is a molarity approximation to the
    molality/activity definition with a declared reference concentration -- it does NOT claim exact thermodynamic
    authority.  And one approximation it DOES make is now disclosed rather than denied: the Davies coefficient A is
    a molal quantity (kg^1/2 mol^-1/2) and it is applied to an ionic strength carried in molar units (mol/L).  That
    molal-A / molar-I mix is NOT removed -- for dilute aqueous solution the solvent density rho ~ 1 kg/L so molar ~
    molal and the discrepancy is second-order, which is why the Davies result is honestly flagged
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL and never called exact.  (An earlier draft of this header wrongly claimed
    the mix had been eliminated; it had not, and pretending otherwise was itself the kind of over-claim this file
    exists to stamp out.)
  * the 25 C source-temperature restriction only fired for the Davies branch -- ideal mode silently reused 25 C
    Ka/Kw at any temperature.  The restriction is a property of the SOURCED DATA, not of a rendering toggle, so it
    is now enforced for EVERY activity model.
  * solve() averaged two roots and never refused on disagreement or on a Davies fixed point that fell through its
    iteration cap -- a numerical failure could be presented as an admitted prediction.  There is now an explicit
    admission gate (below) that fails CLOSED.
  * the uncertainty discipline conflated "zero error bar" with "missing source", and the benchmark was labelled
    "validation" when it is equation/implementation verification against the SAME Ka -- both relabelled honestly.

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
environment, so the independent cross-check verdict is permanently EXTERNAL_VALIDATION_UNAVAILABLE and the shipped
"textbook anchors" are relabelled as equation/implementation VERIFICATION (they were computed from the SAME Ka and
the SAME ideal approximation -- that is not independent experimental validation).

SCOPE (Wave D, PHREEQC + Round VI "The Salt Bridge"): by DEFAULT the curated species set OMITS the NaAc(aq) ion pair
that the PHREEQC minteq.v4 / llnl databases carry.  In that default, an independent PHREEQC benchmark agrees with the
Davies activity pH to |dpH| <= 0.015 for ionic strength I <= 0.10 M, then drifts to |dpH| ~ 0.052 by I ~ 0.45 M -- the
cause is the MISSING ion pair, NOT Davies-equation breakdown (I = 0.5 M is the standard Davies limit, so the solver
legitimately admits up to DAVIES_I_MAX).  Round VI adds that ion pair as an OPT-IN refinement (include_ion_pair=True,
association constant K_NAAC_ION_PAIR_25C, logK -0.18 from NIST46.4 via PHREEQC minteq.v4): with it modeled, the
ion-pair-omission divergence is closed (C5 |dpH| ~ 0.052 -> ~0.026, and no case DIVERGEs; the ~0.026 residual is the
Davies-vs-Debye-Huckel activity-model + molal/molar difference, which the pair does NOT touch, not the species set).
Two DIFFERENT domains stay distinct and both honoured: the Davies validity domain (DAVIES_I_MAX = 0.5 M, enforced by
the admission gate) and the DEMONSTRATED independent-agreement domain (BENCHMARK_AGREEMENT_I_MAX ~ 0.1 M without the
pair; wider with it, BENCHMARK_AGREEMENT_I_MAX_WITH_ION_PAIR).  A result past its agreement domain still earns
SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL but CARRIES a caveat (SpeciationResult.caveats) naming what is, and is not,
independently benchmarked.  Independent experimental VALIDATION against a MEASURED acetate-buffer pH remains UNKNOWN
(the acetate buffer is not an NBS/NIST primary pH standard, and the dissociation-constant literature shares the Ka
EMF lineage, so it is not an independent check of Ka); no measured datum and no ion pair is fabricated to hide this.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.optimize import brentq

from experiments.sandbox_foundation.twocell import InvalidParameterError


# --------------------------------------------------------------------------------- claim ledger / verdict vocabulary
# The verdict a result CARRIES, in the file's existing SOURCED/DERIVED/UNKNOWN uppercase-string style.  These names
# are load-bearing tokens -- a caller branches on them -- so they are plain string constants, exact and stable.
# What each one actually promises (and, as important, what it does NOT):
SOLVED_WITHIN_IDEAL_MODEL = "SOLVED_WITHIN_IDEAL_MODEL"
#   the equations were solved and admitted under the ideal-dilute (activity = concentration) model.  Says nothing
#   about whether the ideal model is physically adequate -- only that the math closed.
SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL = "SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL"
#   solved and admitted under the Davies activity model, inside its declared ionic-strength domain.
NUMERICALLY_UNVERIFIED = "NUMERICALLY_UNVERIFIED"
#   the admission gate could not certify the solution (routes disagreed, a fixed point fell through, a balance did
#   not close, a concentration went negative, or I left the Davies domain).  A solver failure, NOT a prediction.
OUT_OF_SOURCE_DOMAIN = "OUT_OF_SOURCE_DOMAIN"
#   a constant/temperature was requested outside the regime the sourced data covers (here: 25 C).  We refuse to
#   extrapolate sourced numbers; silence is not a licence.
EXTERNAL_VALIDATION_UNAVAILABLE = "EXTERNAL_VALIDATION_UNAVAILABLE"
#   no INDEPENDENT experimental/second-tool cross-check has been run (Reaktoro absent).  Permanent and honest;
#   never a stand-in for a fabricated comparison.

VERDICTS = frozenset({
    SOLVED_WITHIN_IDEAL_MODEL, SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    NUMERICALLY_UNVERIFIED, OUT_OF_SOURCE_DOMAIN, EXTERNAL_VALIDATION_UNAVAILABLE,
})


# --------------------------------------------------------------------------------- declared domains & tolerances
# Everything the admission gate judges against lives here, out in the open.  The rule of this surgery: a tolerance
# is chosen to reflect what the solver GENUINELY achieves across the deployment regime, never widened to drag a red
# fixture green.  The empirical basis for each is noted -- that is the difference between a bound and a fudge.
SOURCE_T_K = 298.15            # the temperature the Ka/Kw/Davies-A records are tabulated at (25 C)
SOURCE_T_TOL_K = 0.01          # admitted band around the source temperature; outside => OUT_OF_SOURCE_DOMAIN

AGREEMENT_RTOL = 1e-7          # the two independent [H+] routes must agree to this, relatively.  Observed worst
#   honest disagreement across the tested regimes was ~5e-11 (basic NaOH limit); a wrong/divergent root is order 1.
#   1e-7 sits ~2000x above the honest floor yet still catches any genuine route divergence.
CHARGE_BALANCE_ATOL = 1e-12    # absolute floor for charge-balance closure (mol/L)
CHARGE_BALANCE_RTOL = 1e-9     # plus a term scaled by the dominant charged-species magnitude -- the residual grows
#   with the absolute concentrations (~2.7e-12 at ~0.1 M in the basic limit), so a pure abs tol would mis-reject it.
MASS_BALANCE_RTOL = 1e-9       # total-acetate closure, relative to C_T (observed residual is machine-zero)
NONNEGATIVITY_ATOL = 1e-12     # a species may dip this far below zero on roundoff only; more is a real failure

DAVIES_FIXED_POINT_TOL = 1e-12  # gamma self-consistency; the fixed point reaches this in 3-4 iterations in-domain
DAVIES_MAX_ITERS = 100          # the cap is NOT the convergence criterion -- falling through it => unverified
DAVIES_I_MAX = 0.5              # mol/L; declared upper bound of Davies-equation validity.  Beyond this the model
#   is out of its domain and the result is NUMERICALLY_UNVERIFIED rather than a quietly-extrapolated activity.
BENCHMARK_AGREEMENT_I_MAX = 0.1  # mol/L; the DEMONSTRATED independent-benchmark (PHREEQC) agreement domain, where
#   the Davies activity pH matched to |dpH| <= 0.015.  This is STRICTLY INSIDE DAVIES_I_MAX: the solver still admits
#   up to 0.5 M, but past 0.1 M the agreement degrades (to ~0.052 pH by 0.45 M) because the NaAc ion pair is omitted,
#   so a result out here is flagged "not independently benchmarked", NOT silently presented as corroborated.
BEYOND_BENCHMARK_CAVEAT = (
    "ionic strength exceeds the demonstrated independent-benchmark agreement domain "
    "(I <= 0.1 M, |dpH| <= 0.015 vs PHREEQC); the NaAc(aq) ion pair is omitted from the species set, so out here the "
    "activity pH is Davies-model-only and NOT independently benchmarked (PHREEQC drift reaches ~0.052 pH by 0.45 M)")

# Round VI ("The Salt Bridge"): with the NaAc(aq) ion pair MODELED (opt-in, include_ion_pair=True) the independent-
# benchmark picture changes -- the omission that drove the C5 divergence is closed, so a wider agreement domain is
# demonstrated.  These are set from the benchmarks/acetate_phreeqc re-run (code side re-run against the committed
# PHREEQC-with-pair reference; the reference already included the pair).
BENCHMARK_AGREEMENT_I_MAX_WITH_ION_PAIR = 0.1   # mol/L; with the pair modeled, AGREE (|dpH| <= 0.02 vs PHREEQC) is
#   CONFIRMED to I ~ 0.1 (benchmark case C4: |dpH| = 0.0058), the same grid resolution as the no-pair domain -- BUT
#   the meaning BEYOND it differs sharply: without the pair, I > 0.1 DIVERGEs (C5, I ~ 0.4: |dpH| ~ 0.052); WITH the
#   pair that divergence is closed and the worst case is only MARGINAL (C5 with pair: measured 0.023, a Davies-vs-
#   Debye-Huckel activity-model + molal/molar residual the pair does NOT touch).  So beyond 0.1 a pair-included result
#   still carries a caveat -- but one about a MARGINAL activity-model residual, not an ion-pair OMISSION.
BEYOND_BENCHMARK_CAVEAT_WITH_ION_PAIR = (
    "ionic strength exceeds the demonstrated AGREE domain (I <= 0.1 M); the NaAc(aq) ion pair IS modeled here, so the "
    "former ion-pair-omission DIVERGENCE is closed (no benchmark case diverges), but a residual Davies-vs-Debye-Huckel "
    "activity-model + molal/molar difference vs PHREEQC grows with ionic strength to a MARGINAL ~0.023 pH by I ~ 0.4 M "
    "-- Davies-model-only, never independently validated against a measured datum")

# Accepted MOLAR standard-state spellings and the MOLAL tokens that disqualify a units string.  An explicit
# allowlist/blocklist -- adequate for this curated, fixed species set -- replaces the old `"molar" in units` test,
# which both wrongly ACCEPTED a molal string that merely contained the substring "molar" and wrongly REFUSED
# correctly-labelled molar spellings like "mol/L", "M", or "mol dm^-3".  Blocklist wins: a string carrying any molal
# token is refused even if it also says "molar".
_MOLAL_UNIT_TOKENS = ("molal", "mol/kg", "mol kg", "mol kg^-1", "mol kg-1", "/kg", "per kg", "mol.kg")
_MOLAR_UNIT_SUBSTRINGS = ("mol/l", "mol l", "mol/dm", "mol dm", "mol.l", "molar", "molarity")


def _is_molar_standard_state(units: str) -> bool:
    """True iff `units` names a MOLAR (mol/L) standard state.  Molal/per-kg tokens veto first; then an explicit list
    of molar spellings is accepted, plus the bare molar symbol 'M' as a standalone (case-sensitive) token."""
    u = units.lower()
    if any(tok in u for tok in _MOLAL_UNIT_TOKENS):
        return False
    if any(sp in u for sp in _MOLAR_UNIT_SUBSTRINGS):
        return True
    return re.search(r"\bM\b", units) is not None


class OutOfSourceDomainError(InvalidParameterError):
    """Raised when a request leaves the regime the sourced data covers (temperature/standard-state).  Carries the
    OUT_OF_SOURCE_DOMAIN verdict so a caller catching it can read the claim status off the exception, not guess."""

    def __init__(self, message: str):
        super().__init__(message)
        self.verdict = OUT_OF_SOURCE_DOMAIN


class NumericalVerificationError(InvalidParameterError):
    """Raised by the admission gate when the solver cannot CERTIFY its own answer.  Fail closed: this is thrown
    instead of returning a SpeciationResult, so a numerical failure can never be handed back as a prediction."""

    def __init__(self, message: str):
        super().__init__(message)
        self.verdict = NUMERICALLY_UNVERIFIED


# --------------------------------------------------------------------------------- sourced constants (provenance)
@dataclass(frozen=True)
class SourcedConstant:
    """A physical quantity with its PROVENANCE: value, +/- uncertainty, units, temperature, citation, and a status.
    status is one of:
      SOURCED  -- a defensible tertiary reference; a MEASURED constant.  Must carry a POSITIVE uncertainty.
      DERIVED  -- computed from sourced values by a stated method; likewise carries a positive uncertainty.
      EXACT    -- exact BY DEFINITION (e.g. a declared reference concentration).  Carries EXACTLY zero uncertainty;
                  a nonzero error bar on a defined quantity is as fabricated as a decorative one on a measured one.
      UNKNOWN  -- not available; never fabricated.  value/uncertainty may be absent (NaN) and are not constrained.
    A decorative / fabricated uncertainty is banned.  For a MEASURED (SOURCED/DERIVED) constant that means a zero
    error bar is REFUSED -- a measurement with exactly zero spread is a fiction, and the directive ranks a fabricated
    error bar as worse than an honest UNKNOWN.  Exact-by-definition quantities are the ONLY things allowed zero, and
    they are tagged EXACT precisely so the two cannot be confused."""
    name: str
    value: float
    uncertainty: float
    units: str
    T_K: float
    source: str
    status: str = "SOURCED"
    note: str = ""

    def __post_init__(self):
        if self.status not in ("SOURCED", "DERIVED", "EXACT", "UNKNOWN"):
            raise InvalidParameterError("status must be SOURCED / DERIVED / EXACT / UNKNOWN")
        if self.status == "UNKNOWN":
            return  # an honest blank: nothing to validate, nothing to fabricate
        if not (math.isfinite(self.value) and self.value > 0):
            raise InvalidParameterError("a SOURCED/DERIVED/EXACT constant must be finite and > 0")
        if not self.source.strip():
            raise InvalidParameterError("a SOURCED/DERIVED/EXACT constant must cite its source or definition")
        if not self.units.strip():
            raise InvalidParameterError("a SOURCED/DERIVED/EXACT constant must state its units/standard state")
        if self.status == "EXACT":
            # exact BY DEFINITION: zero uncertainty is mandatory, and a nonzero one is the fabrication to catch.
            if self.uncertainty != 0.0:
                raise InvalidParameterError(
                    "an EXACT (by-definition) quantity must carry exactly zero uncertainty; a nonzero error bar on "
                    "a defined quantity is fabricated")
        else:
            # SOURCED / DERIVED: a MEASURED quantity.  A zero (or non-finite) spread is a decorative/fabricated bar.
            if not (math.isfinite(self.uncertainty) and self.uncertainty > 0):
                raise InvalidParameterError(
                    "a SOURCED/DERIVED (measured) constant must carry a POSITIVE uncertainty; a zero/decorative "
                    "error bar is banned (worse than UNKNOWN)")


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

# The reference concentration c_ref for p[H] / pH_activity = -log10(a / c_ref).  IUPAC pH is molality/activity-based
# (Gold Book P04524); this model works on MOLARITY, so we fix a molar reference concentration BY DEFINITION and say
# so.  Exactly 1 mol/L, exactly zero uncertainty -- hence EXACT, not SOURCED.  It makes the logarithm dimensionless
# honestly instead of smuggling in the "activity of a 1 M ideal solution = 1" assumption unlabelled.
C_REF = SourcedConstant(
    "c_ref", 1.0, 0.0, "mol/L (molar reference concentration, by definition)", 298.15,
    "IUPAC convention for the standard reference concentration in -log10(a/c_ref); defined, not measured.",
    "EXACT",
    "Molarity approximation to the IUPAC molality/activity pH definition, with the reference concentration stated "
    "explicitly rather than assumed.  Numerically 1 mol/L so p-values are unchanged in magnitude -- the point is "
    "the declared standard-state approximation, not a new number.")

# Round VI: the NaAc(aq) ion-pair ASSOCIATION constant, Na+ + Ac- <-> NaAc(aq), K_assoc = [NaAc]/([Na+][Ac-]).
# logK = -0.18 at 25 C (K ~ 0.661 L/mol) from the NIST Critically Selected Stability Constants (NIST 46.4), the value
# carried by the PHREEQC minteq.v4 database ("Na+ + Acetate- = Na(Acetate) log_k -0.18").  Corroborated by the LLNL
# thermodynamic database (effective 25 C logK ~ -0.079 from its -analytic terms) and by measured potentiometry
# (Archer & Monk, Trans. Faraday Soc. 60 (1964); Daniele et al. 1985).  The minteq<->llnl logK spread (-0.18 vs ~-0.079,
# ~0.10 in logK => K ~ 0.52..0.83 L/mol) sets the ~+/-0.17 uncertainty on K ~ 0.66.  This is a WEAK pair (K < 1);
# omitting it is the documented cause of the model's ~0.052 pH divergence from PHREEQC at I ~ 0.45 M.  It is OPT-IN
# via AcetateWaterSystem(include_ion_pair=True) -- the default species set stays exactly as Wave A/D shipped it.
K_NAAC_ION_PAIR_25C = SourcedConstant(
    "K_NaAc_ion_pair", 10 ** (-0.18), 0.17, "dimensionless (molar association constant, 1 M reference)", 298.15,
    "NIST Critically Selected Stability Constants (NIST 46.4) via PHREEQC minteq.v4 'Na+ + Acetate- = Na(Acetate) "
    "log_k -0.18'; corroborated by the LLNL DB (effective logK ~ -0.079) and measured potentiometry (Archer & Monk "
    "1964; Daniele et al. 1985).  The minteq/llnl logK spread sets the +/-0.17 (on K) uncertainty.", "SOURCED",
    "Weak Na+/Ac- ion-pair association (K < 1 L/mol); opt-in via include_ion_pair=True.")


def _require_source_temperature(T_K: float) -> None:
    """The sourced constants are a 25 C record.  Refuse any temperature outside the admitted band for EVERY activity
    model -- extrapolating a sourced number is not the model's call to make.  (A2: this used to fire for Davies only;
    ideal mode silently reused 25 C constants at any T.  No longer.)"""
    if not math.isfinite(T_K):
        raise InvalidParameterError("temperature_K must be finite")
    if abs(T_K - SOURCE_T_K) > SOURCE_T_TOL_K:
        raise OutOfSourceDomainError(
            f"temperature {T_K} K is outside the sourced-data domain {SOURCE_T_K} +/- {SOURCE_T_TOL_K} K; the Ka/Kw "
            f"records are 25 C only, so this is refused (fail closed) in EVERY activity model rather than extrapolated")


def _require_constant_at_source_state(const: SourcedConstant, *, role: str) -> None:
    """A SOURCED record that is at the wrong temperature, or in the wrong standard state, has no authority here --
    refuse it rather than silently borrow a rate.  (A4 d/e: an off-temperature or mismatched-units constant.)"""
    if const.status not in ("SOURCED", "DERIVED"):
        raise InvalidParameterError(f"the {role} constant must be SOURCED or DERIVED, got status {const.status!r}")
    if abs(const.T_K - SOURCE_T_K) > SOURCE_T_TOL_K:
        raise OutOfSourceDomainError(
            f"the {role} constant is tabulated at {const.T_K} K but this system is anchored at {SOURCE_T_K} K; "
            f"refusing to use an off-temperature record")
    if not _is_molar_standard_state(const.units):
        raise InvalidParameterError(
            f"the {role} constant units {const.units!r} do not name the MOLAR (mol/L) standard state this model "
            f"solves in; refusing to silently mix standard states (e.g. a molal constant with molar ionic strength)")


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
    include_ion_pair: bool = False        # Round VI opt-in: model the NaAc(aq) ion pair (default off = Wave A/D set)
    K_assoc: SourcedConstant = K_NAAC_ION_PAIR_25C

    def __post_init__(self):
        if not (math.isfinite(self.total_acetic_M) and self.total_acetic_M >= 0):
            raise InvalidParameterError("total_acetic_M must be finite and >= 0")
        if not (math.isfinite(self.sodium_M) and self.sodium_M >= 0):
            raise InvalidParameterError("sodium_M must be finite and >= 0")
        if self.activity_model not in ("ideal", "davies"):
            raise InvalidParameterError("activity_model must be 'ideal' or 'davies'")
        if not isinstance(self.include_ion_pair, bool):
            raise InvalidParameterError("include_ion_pair must be a bool")
        # the source-domain guard now binds in ALL modes, not just davies.
        _require_source_temperature(self.temperature_K)
        _require_constant_at_source_state(self.Ka, role="Ka")
        _require_constant_at_source_state(self.Kw, role="Kw")
        if self.include_ion_pair:
            # the association constant must itself be a sourced, source-state-consistent record, exactly like Ka/Kw --
            # an opt-in refinement is not an excuse to admit an unsourced or off-state number.
            _require_constant_at_source_state(self.K_assoc, role="K_assoc")


@dataclass(frozen=True)
class SpeciationResult:
    pH: float                             # the PRIMARY pH: activity-based in davies mode, = p[H] in ideal mode
    pH_concentration: float               # p[H] = -log10([H+]/c_ref); a concentration number, NOT the IUPAC pH
    pH_activity: float                    # -log10(gamma_H*[H+]/c_ref); the activity-based (IUPAC-style) value
    c_ref_M: float                        # the declared reference concentration (mol/L) the p-values are taken over
    verdict: str                          # one of VERDICTS -- the claim this result is entitled to make
    h_plus_M: float
    oh_minus_M: float
    hac_M: float
    ac_minus_M: float
    ionic_strength_M: float
    activity_model: str
    solver_agreement_residual: float      # |route1 - route2| on [H+]; a SOLVER cross-check, not a DB cross-check
    gamma_monovalent: float               # activity coefficient of a +/-1 ion (1.0 in the ideal model)
    charge_balance_residual: float        # |[Na+]+[H+]-[OH-]-[Ac-]| at the solution (must be ~0)
    davies_iterations: int                # fixed-point iterations actually taken (0 for ideal); transparency, not fluff
    na_plus_M: float = 0.0                # free [Na+] (mol/L); == total sodium in the base model, < it with the pair
    naac_M: float = 0.0                   # [NaAc(aq)] neutral ion pair (mol/L); 0 in the base model / ideal mode
    caveats: tuple = ()                   # honest qualifiers on an ADMITTED result (e.g. beyond the demonstrated
    #   independent-benchmark domain / ion-pairing omitted).  Empty = no qualifier; the verdict is the claim, these
    #   are the asterisks on it.  A result with the benchmark caveat is still SOLVED_*, just not corroborated out there.


def _cubic_positive_root(Ka: float, Kw: float, C_T: float, Na: float) -> float:
    """Route 1: numpy.roots on h^3 + (Ka+Na) h^2 - (Kw + Ka*C_T - Ka*Na) h - Ka*Kw = 0; the unique positive real.
    Returns NaN rather than raising if no positive real root is found -- the admission gate is the single fail-closed
    decision point, so a route that cannot deliver simply reports an unusable number and the gate refuses."""
    coeffs = [1.0, Ka + Na, -(Kw + Ka * C_T - Ka * Na), -Ka * Kw]
    try:
        roots = np.roots(coeffs)
    except (np.linalg.LinAlgError, ValueError):
        return float("nan")
    real = [float(r.real) for r in roots if abs(r.imag) < 1e-18 * max(1.0, abs(r.real)) and r.real > 0]
    if not real:
        return float("nan")
    return min(real)   # the physically relevant root (the others, if any, are spurious large roots)


def _charge_balance_residual(h: float, Ka: float, Kw: float, C_T: float, Na: float) -> float:
    ac = Ka * C_T / (h + Ka)
    oh = Kw / h
    return (Na + h) - (oh + ac)


def _brentq_root(Ka: float, Kw: float, C_T: float, Na: float) -> float:
    """Route 2: bracketed bisection on the charge-balance residual (an independent ALGORITHM, same sourced data).
    Returns NaN on a bracketing/convergence failure -- again, the gate decides, not an exception from down here."""
    lo, hi = 1e-20, max(1.0, C_T + Na + 1.0)
    try:
        return float(brentq(_charge_balance_residual, lo, hi, args=(Ka, Kw, C_T, Na), xtol=1e-18, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _davies_gamma(ionic: float, A: float) -> float:
    """Davies activity coefficient of a +/-1 ion: log10 g = -A (sqrt(I)/(1+sqrt(I)) - 0.3 I), I = ionic strength."""
    if not math.isfinite(ionic) or ionic <= 0:
        return 1.0
    s = math.sqrt(ionic)
    return float(10.0 ** (-A * (s / (1.0 + s) - 0.3 * ionic)))


# ----------------------------------------------------------------------- Round VI: the NaAc(aq) ion-pair extension
# With the pair, Na+ is no longer a fixed charge-balance term: some sodium is sequestered as the neutral NaAc(aq),
# so BOTH a sodium mass balance (Na_T = [Na+] + [NaAc]) and an extra acetate sink ([NaAc]) appear, and the neutral
# pair drops OUT of charge balance.  The clean cubic in [H+] no longer holds; the system is solved as two coupled
# equations (acetate mass balance, charge balance).  Two INDEPENDENT routes, same sourced data, must agree -- exactly
# the Wave A discipline, re-earned for the harder system.
def _ion_pair_acetate_root(h: float, Ka_c: float, Kass_c: float, C_T: float, Na_T: float) -> float:
    """Free [Ac-] from the acetate mass balance WITH the NaAc pair, at fixed [H+]=h and effective constants.
    C_T = a*h/Ka_c + a + Kass_c*Na_T*a/(1+Kass_c*a).  Multiplying by (1+Kass_c*a) gives a QUADRATIC in a:
        (beta*Kass_c) a^2 + (beta + Kass_c*Na_T - C_T*Kass_c) a - C_T = 0,   beta = h/Ka_c + 1.
    The constant term -C_T < 0, so the two roots have opposite sign; the physical (positive) one is the '+' root.
    Kass_c == 0 degenerates to the linear base balance a = C_T/beta.  Returns NaN on a non-real/invalid discriminant."""
    if not (math.isfinite(h) and h > 0 and math.isfinite(Ka_c) and Ka_c > 0):
        return float("nan")
    beta = h / Ka_c + 1.0
    if not (math.isfinite(Kass_c) and Kass_c > 0.0):
        return C_T / beta
    a2 = beta * Kass_c
    b1 = beta + Kass_c * Na_T - C_T * Kass_c
    disc = b1 * b1 + 4.0 * a2 * C_T          # == b1^2 - 4*a2*C0 with C0 = -C_T
    if disc < 0 or a2 <= 0:
        return float("nan")
    return (-b1 + math.sqrt(disc)) / (2.0 * a2)


def _ion_pair_charge_residual(h: float, Ka_c: float, Kw_c: float, Kass_c: float, C_T: float, Na_T: float) -> float:
    """Charge-balance residual (Na+ + H+) - (OH- + Ac-) at [H+]=h, with the neutral NaAc pair excluded from charge
    and free [Na+] = Na_T/(1+Kass_c*[Ac-]).  NaN if the inner acetate root is unusable (lets the caller fail closed)."""
    a = _ion_pair_acetate_root(h, Ka_c, Kass_c, C_T, Na_T)
    if not (math.isfinite(a) and a >= 0):
        return float("nan")
    na_plus = Na_T / (1.0 + Kass_c * a)
    oh = Kw_c / h
    return (na_plus + h) - (oh + a)


def _ion_pair_h_route_brentq(Ka_c: float, Kw_c: float, Kass_c: float, C_T: float, Na_T: float) -> float:
    """Route 1: bracketed bisection (brentq) on the charge residual, with [Ac-] eliminated analytically per h.
    Returns NaN on a bracketing/convergence failure -- the admission gate is the single fail-closed decision point."""
    lo, hi = 1e-20, max(1.0, C_T + Na_T + 1.0)
    try:
        return float(brentq(_ion_pair_charge_residual, lo, hi, args=(Ka_c, Kw_c, Kass_c, C_T, Na_T),
                            xtol=1e-18, rtol=1e-14))
    except (ValueError, RuntimeError):
        return float("nan")


def _ion_pair_h_route_acetate(Ka_c: float, Kw_c: float, Kass_c: float, C_T: float, Na_T: float) -> float:
    """Route 2: the DUAL decomposition, and a genuinely independent cross-check of route 1.  Route 1 eliminates [Ac-]
    via the ACETATE quadratic and brackets the CHARGE residual in h; this route does the REVERSE -- it brackets the
    ACETATE mass-balance residual in a, getting [H+] from the CHARGE-balance quadratic h^2 + (na_plus - a) h - Kw_c = 0
    (na_plus = Na/(1+Kass_c a), neutral pair excluded from charge).  The two routes therefore use DIFFERENT analytic
    eliminations: a bug in either one's algebra shows up as a route disagreement the admission gate will refuse on.
    Both are robust bracketed (brentq) solves, so neither inherits fsolve's stiffness/scaling fragility.  NaN on failure."""
    def h_of_a(a: float) -> float:
        # positive root of the charge-balance quadratic h^2 + b h - Kw_c = 0, b = na_plus - a.  The naive
        # 0.5*(-b + sqrt(b^2 + 4 Kw_c)) CATASTROPHICALLY CANCELS when basic (b > 0, b^2 >> 4 Kw_c: subtracting two
        # near-equal large numbers), which made this route inaccurate and spuriously disagree with route 1, refusing
        # the whole excess-base regime.  Use the numerically-stable branch per sign of b (the standard trick: pick the
        # form that ADDS like-signed terms, then recover the other root from the product-of-roots = -Kw_c).
        na_plus = Na_T / (1.0 + Kass_c * a)
        b = na_plus - a
        disc = math.sqrt(b * b + 4.0 * Kw_c)
        if b > 0.0:
            return 2.0 * Kw_c / (b + disc)        # == 0.5*(-b + disc), but cancellation-free for basic solutions
        return 0.5 * (-b + disc)                  # acidic/neutral (b <= 0): -b + disc adds like-signed terms, stable

    def acetate_residual(a: float) -> float:
        h = h_of_a(a)
        if not (math.isfinite(h) and h > 0):
            return float("nan")
        na_plus = Na_T / (1.0 + Kass_c * a)
        return a * h / Ka_c + a + Kass_c * na_plus * a - C_T   # acetate mass balance (incl. the NaAc pair sink)

    try:
        a = float(brentq(acetate_residual, 0.0, C_T, xtol=1e-18, rtol=1e-14))    # R(0) = -C_T < 0, R(C_T) > 0
    except (ValueError, RuntimeError):
        return float("nan")
    h = h_of_a(a)
    return h if (math.isfinite(h) and h > 0) else float("nan")


def _speciate(Ka_c: float, Kw_c: float, Kass_c: float, C_T: float, Na: float, include_ion_pair: bool):
    """Solve the speciation at FIXED effective (concentration-basis) constants by two independent routes.  Returns
    (h1, h2, h, ac, oh, hac, na_plus, naac).  Base model (or nothing to pair): Na+ fully free, NaAc = 0, the Wave A
    cubic+brentq pair.  Ion-pair model (include_ion_pair and C_T>0 and Na>0): route 1 = analytic-acetate + bracketed
    charge root; route 2 = raw 2-equation Newton.  h is their mean; the gate decides whether they agree."""
    if include_ion_pair and C_T > 0.0 and Na > 0.0 and Kass_c > 0.0:
        h1 = _ion_pair_h_route_brentq(Ka_c, Kw_c, Kass_c, C_T, Na)
        h2 = _ion_pair_h_route_acetate(Ka_c, Kw_c, Kass_c, C_T, Na)
        h = 0.5 * (h1 + h2)
        if not (math.isfinite(h) and h > 0):
            return h1, h2, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"), float("nan")
        ac = _ion_pair_acetate_root(h, Ka_c, Kass_c, C_T, Na)
        if not (math.isfinite(ac) and ac >= 0):
            return h1, h2, h, float("nan"), Kw_c / h, float("nan"), float("nan"), float("nan")
        na_plus = Na / (1.0 + Kass_c * ac)
        naac = Kass_c * na_plus * ac
        oh = Kw_c / h
        hac = C_T - ac - naac
        return h1, h2, h, ac, oh, hac, na_plus, naac
    # base: no ion pair, or nothing to pair (no acetate / no sodium) -- the Wave A cubic, Na+ fully free.
    h1 = _cubic_positive_root(Ka_c, Kw_c, C_T, Na)
    h2 = _brentq_root(Ka_c, Kw_c, C_T, Na)
    h = 0.5 * (h1 + h2)
    if not (math.isfinite(h) and h > 0):
        return h1, h2, float("nan"), float("nan"), float("nan"), float("nan"), Na, 0.0
    ac = Ka_c * C_T / (h + Ka_c)
    oh = Kw_c / h
    hac = C_T - ac
    return h1, h2, h, ac, oh, hac, Na, 0.0


def _verify_admission(*, h1: float, h2: float, h: float, oh: float, ac: float, hac: float,
                      C_T: float, Na: float, Ka_c: float, Kw_c: float, activity_model: str,
                      ionic_strength: float, davies_converged: bool, davies_iterations: int,
                      include_ion_pair: bool = False, Kass_c: float = 0.0,
                      na_plus: float = float("nan"), naac: float = float("nan")) -> str:
    """The admission gate.  A result is entitled to a SOLVED_* verdict ONLY if every one of these holds; otherwise
    this raises NumericalVerificationError (verdict NUMERICALLY_UNVERIFIED) and no prediction is handed back.  This
    is the whole point of Wave A: a solver failure must never wear a success label.  Conditions, all against the
    DECLARED tolerances above (never widened to pass a fixture):
      (1) both independent routes produced a finite positive [H+];
      (2) the two routes agree within AGREEMENT_RTOL;
      (3) charge balance closes (abs floor + a term scaled by the dominant charged-species magnitude);
      (4) total-acetate balance closes within MASS_BALANCE_RTOL;
      (5) every admitted species concentration is >= 0 (bar NONNEGATIVITY_ATOL of roundoff);
      (6) for davies, the ionic-strength fixed point demonstrably converged (did not fall through the cap);
      (7) for davies, the ionic strength is inside the Davies-equation domain (<= DAVIES_I_MAX).
    With include_ion_pair, the gate RE-DERIVES [Ac-]/[Na+]/[NaAc] from the adopted [H+] and the constants (its own
    independent check, not a rubber stamp of what solve() passed), closes charge balance with the neutral NaAc pair
    EXCLUDED, additionally closes a sodium mass balance (Na_T = [Na+] + [NaAc]) and the acetate balance WITH the pair
    sink, and refuses if solve()'s reported [Na+]/[NaAc]/[Ac-] disagree with that re-derivation."""
    problems = []
    if not (math.isfinite(h1) and h1 > 0 and math.isfinite(h2) and h2 > 0):
        problems.append(f"a solver route failed to deliver a finite positive [H+] (route1={h1}, route2={h2})")
    elif abs(h1 - h2) > AGREEMENT_RTOL * max(h1, h2):
        problems.append(
            f"the two independent routes disagree beyond AGREEMENT_RTOL={AGREEMENT_RTOL:g} "
            f"(|{h1}-{h2}|={abs(h1 - h2):g})")
    if not math.isfinite(h):
        problems.append("the adopted [H+] is not finite")
    elif include_ion_pair:
        # the single source of truth is the adopted h: re-derive the speciation from it and check balances + that
        # solve()'s reported numbers match.  A bug that fabricated [Na+]/[NaAc] would be caught here, not trusted.
        ac_d = _ion_pair_acetate_root(h, Ka_c, Kass_c, C_T, Na)
        if not (math.isfinite(ac_d) and ac_d >= -NONNEGATIVITY_ATOL):
            problems.append("the ion-pair acetate re-derivation is not a usable nonnegative number")
        else:
            nap_d = Na / (1.0 + Kass_c * ac_d)
            naac_d = Kass_c * nap_d * ac_d
            oh_d = Kw_c / h
            cb = abs((nap_d + h) - (oh_d + ac_d))
            if cb > CHARGE_BALANCE_ATOL + CHARGE_BALANCE_RTOL * (abs(nap_d) + h + oh_d + abs(ac_d)):
                problems.append(f"ion-pair charge balance does not close (residual {cb:g})")
            # Sodium mass balance on the REPORTED split (na_plus, naac), NOT the re-derived (nap_d, naac_d): the
            # latter satisfy nap_d + naac_d = Na/(1+Kass_c*ac_d)*(1+Kass_c*ac_d) == Na IDENTICALLY, so a check on them
            # is a dead tautology (the "check derived from its own subject" trap).  Checked on solve()'s actual output
            # it is a genuine statement about what was produced -- belt-and-suspenders with the reported-vs-re-derived
            # consistency check below (which is the finer guard), caught here if solve ever reports a non-conserving split.
            sb = abs((na_plus + naac) - Na) if (math.isfinite(na_plus) and math.isfinite(naac)) else float("inf")
            if sb > CHARGE_BALANCE_ATOL + CHARGE_BALANCE_RTOL * (Na + abs(naac if math.isfinite(naac) else 0.0)) + 1e-9 * max(1.0, Na):
                problems.append(f"sodium mass balance does not close on the reported split (Na+ + NaAc = {na_plus + naac}, Na = {Na})")
            if (not (math.isfinite(na_plus) and math.isfinite(naac) and math.isfinite(ac))
                    or abs(na_plus - nap_d) > 1e-9 * max(1.0, Na)
                    or abs(naac - naac_d) > 1e-9 * max(1.0, Na)
                    or abs(ac - ac_d) > 1e-9 * max(1.0, C_T)):
                problems.append("reported ion-pair speciation disagrees with the re-derivation from [H+]")
    else:
        cb = abs(_charge_balance_residual(h, Ka_c, Kw_c, C_T, Na))
        cb_allow = CHARGE_BALANCE_ATOL + CHARGE_BALANCE_RTOL * (Na + h + oh + ac)
        if cb > cb_allow:
            problems.append(f"charge balance does not close (residual {cb:g} > allowed {cb_allow:g})")
    acetate_total = (hac + ac + naac) if include_ion_pair else (hac + ac)
    naac_bad = include_ion_pair and not math.isfinite(naac)
    if (not math.isfinite(hac) or not math.isfinite(ac) or naac_bad
            or abs(acetate_total - C_T) > MASS_BALANCE_RTOL * max(1.0, C_T)):
        problems.append(f"total-acetate balance does not close (sum = {acetate_total}, C_T = {C_T})")
    conc_tuple = (h, oh, ac, hac, na_plus, naac) if include_ion_pair else (h, oh, ac, hac)
    finite_concs = [c for c in conc_tuple if math.isfinite(c)]
    if len(finite_concs) < len(conc_tuple) or min(finite_concs, default=float("nan")) < -NONNEGATIVITY_ATOL:
        problems.append(f"a species concentration is negative or non-finite (min = {min(finite_concs, default=float('nan'))})")
    if activity_model == "davies":
        if not davies_converged:
            problems.append(f"the Davies ionic-strength fixed point did not converge within {DAVIES_MAX_ITERS} iters "
                            f"(took {davies_iterations})")
        if not math.isfinite(ionic_strength) or ionic_strength > DAVIES_I_MAX:
            problems.append(f"ionic strength {ionic_strength} is outside the Davies-model domain (<= {DAVIES_I_MAX} M)")
    if problems:
        raise NumericalVerificationError("admission refused: " + "; ".join(problems))
    return (SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL if activity_model == "davies"
            else SOLVED_WITHIN_IDEAL_MODEL)


def solve(system: AcetateWaterSystem, *, tol: float = DAVIES_FIXED_POINT_TOL) -> SpeciationResult:
    """Solve the 0-D equilibrium for [H+] / pH / speciation by TWO independent algorithms (which must agree), under
    the ideal or Davies activity model.  For 'davies' the effective Ka/Kw are the thermodynamic constants divided by
    the relevant activity-coefficient product, iterated to a self-consistent ionic strength (a fixed point).

    The result is handed back ONLY if the admission gate certifies it; a numerical failure raises
    NumericalVerificationError rather than returning a dressed-up answer.  pH is reported honestly: p[H] (a molarity
    number) and pH_activity are both exposed, and in a nonideal model the PRIMARY pH is the activity value."""
    C_T, Na = float(system.total_acetic_M), float(system.sodium_M)
    Ka0, Kw0 = system.Ka.value, system.Kw.value
    Kass0 = system.K_assoc.value if system.include_ion_pair else 0.0
    A = DAVIES_A_25C.value
    gamma = 1.0
    davies_converged = (system.activity_model == "ideal")  # ideal has no fixed point to converge; gamma is fixed at 1
    davies_iterations = 0
    h1 = h2 = h = ac = oh = ionic = hac = float("nan")
    na_plus, naac = Na, 0.0
    Ka_c, Kw_c, Kass_c = Ka0, Kw0, Kass0
    for i in range(1, DAVIES_MAX_ITERS + 1):
        davies_iterations = 0 if system.activity_model == "ideal" else i
        # concentration-basis constants: Ka_c = Ka/gamma^2, Kw_c = Kw/gamma^2 (dissociations; HAc neutral, g_HAc ~ 1);
        # the ASSOCIATION constant scales the OTHER way, Kass_c = Kass * gamma^2 (K = a_NaAc/(a_Na a_Ac), g_NaAc ~ 1).
        g2 = gamma * gamma
        Ka_c, Kw_c, Kass_c = Ka0 / g2, Kw0 / g2, Kass0 * g2
        h1, h2, h, ac, oh, hac, na_plus, naac = _speciate(Ka_c, Kw_c, Kass_c, C_T, Na, system.include_ion_pair)
        if not (math.isfinite(h) and h > 0):
            break  # a route gave up; stop iterating and let the gate refuse rather than spin on NaN
        ionic = 0.5 * (h + oh + ac + na_plus)    # 0.5 sum c_i z_i^2; all charged species monovalent, NaAc neutral
        if system.activity_model == "ideal":
            break
        g_new = _davies_gamma(ionic, A)
        if abs(g_new - gamma) <= tol * gamma:
            # converged: re-solve ONCE at the accepted gamma so every reported number is mutually consistent with it
            gamma = g_new
            g2 = gamma * gamma
            Ka_c, Kw_c, Kass_c = Ka0 / g2, Kw0 / g2, Kass0 * g2
            h1, h2, h, ac, oh, hac, na_plus, naac = _speciate(Ka_c, Kw_c, Kass_c, C_T, Na, system.include_ion_pair)
            if math.isfinite(h) and h > 0:
                ionic = 0.5 * (h + oh + ac + na_plus)
                davies_converged = True
            break
        gamma = g_new

    # The gate runs BEFORE the result exists: a refused solve returns nothing to present.
    verdict = _verify_admission(
        h1=h1, h2=h2, h=h, oh=oh, ac=ac, hac=hac, C_T=C_T, Na=Na, Ka_c=Ka_c, Kw_c=Kw_c,
        activity_model=system.activity_model, ionic_strength=ionic,
        davies_converged=davies_converged, davies_iterations=davies_iterations,
        include_ion_pair=system.include_ion_pair, Kass_c=Kass_c, na_plus=na_plus, naac=naac)

    c_ref = C_REF.value
    pH_concentration = -math.log10(h / c_ref)              # p[H]: a molarity number, honestly labelled
    pH_activity = -math.log10(gamma * h / c_ref)           # activity-based: the IUPAC-style value
    pH = pH_activity if system.activity_model == "davies" else pH_concentration
    # admitted, but is it still inside the region an INDEPENDENT tool corroborated?  Without the pair, beyond ~0.1 M
    # the omitted NaAc ion pair drives PHREEQC drift; WITH the pair modeled that omission is closed and agreement
    # holds across a wider domain -- so the caveat (and its threshold) depend on whether the pair is modeled.
    caveats = ()
    if system.include_ion_pair:
        if math.isfinite(ionic) and ionic > BENCHMARK_AGREEMENT_I_MAX_WITH_ION_PAIR:
            caveats = (BEYOND_BENCHMARK_CAVEAT_WITH_ION_PAIR,)
    elif math.isfinite(ionic) and ionic > BENCHMARK_AGREEMENT_I_MAX:
        caveats = (BEYOND_BENCHMARK_CAVEAT,)
    charge_resid = (abs((na_plus + h) - (oh + ac)) if system.include_ion_pair
                    else abs(_charge_balance_residual(h, Ka_c, Kw_c, C_T, Na)))
    return SpeciationResult(
        pH=pH, pH_concentration=pH_concentration, pH_activity=pH_activity, c_ref_M=c_ref, verdict=verdict,
        h_plus_M=h, oh_minus_M=oh, hac_M=hac, ac_minus_M=ac,
        ionic_strength_M=ionic, activity_model=system.activity_model,
        solver_agreement_residual=abs(h1 - h2), gamma_monovalent=gamma,
        charge_balance_residual=charge_resid,
        davies_iterations=davies_iterations, na_plus_M=na_plus, naac_M=naac, caveats=caveats)


# --------------------------------------------------------------------------------- the independent-benchmark obligation
@dataclass(frozen=True)
class BenchmarkObligation:
    """The record the directive requires for an independent-tool cross-check.  Its verdict is permanently
    EXTERNAL_VALIDATION_UNAVAILABLE here -- the tool is absent, so there is no comparison and we never fabricate one.
    `verdict` is the honest claim status; `comparison` would hold numbers only once Reaktoro is actually run."""
    tool: str
    verdict: str
    recipe: dict = field(default_factory=dict)
    comparison: Optional[dict] = None


def reaktoro_benchmark_obligation() -> BenchmarkObligation:
    """Reaktoro is NOT installed in this environment, so the independent cross-check is EXTERNAL_VALIDATION_UNAVAILABLE
    and carries the EXACT recipe to run it later -- the directive's 'preserve UNKNOWN, deliver the research
    instrument' path.  No numerical comparison is fabricated to fill it.  Note: the shipped 'textbook anchors' are
    equation/implementation VERIFICATION against the same Ka + ideal approximation, NOT this independent validation."""
    return BenchmarkObligation(
        tool="Reaktoro",
        verdict=EXTERNAL_VALIDATION_UNAVAILABLE,
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
                                   "numerical cross-check, and the textbook anchors are equation VERIFICATION (same "
                                   "Ka), not independent experimental validation.",
        },
        comparison=None)
