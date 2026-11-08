"""OPERATION XXV Phase III-B -- typed, SOURCED temperature laws for equilibrium constants (research code only).

    log10 K(T) = a + b*T + c/T + d*log10(T) + e/T**2 + f*T**2          (T in kelvin; the PHREEQC "-analytic" form)

WHAT THIS ADDS.  Until now every sandbox constant was a 25 C record, and admissibility (XXIV-2A) refused any other world
temperature because "no temperature law is validated".  An ``AnalyticTemperatureLaw`` is such a law, typed: exact
coefficient transcription (decimal strings), the reaction as written, the temperature domain (and WHO declared it), the
standard-state basis (molal, as tabulated), the citation, the provenance tier and the stated uncertainty -- or the
explicit token UNSTATED.  It never extrapolates: evaluating outside [T_min_K, T_max_K] raises
``TemperatureLawDomainError`` (a ``general_kernel.SourceDomainError``).

It does NOT replace the XXIV-2A discipline, it feeds it.  ``sourced_constant(T_K)`` returns an ordinary
``aqueous_equilibrium.SourcedConstant`` stamped with that T_K, so a constant produced for 295.15 K is valid only at
295.15 K and the existing off-temperature refusal keeps firing for any other world temperature.  Molal -> molar
transport reuses ``standard_state.molal_to_molar_logK`` with the pure-water density at the SAME temperature.

SOURCES AND TIERS.
  Plummer, L.N. & Busenberg, E. (1982) Geochim. Cosmochim. Acta 46, 1011-1040, doi:10.1016/0016-7037(82)90056-4.
  The abstract was read: log Kc(25 C) = -8.480 +/- 0.020, log K(CaHCO3+) = 1.11 +/- 0.07, log K(CaCO3 aq) = 3.22 +/- 0.14,
  CO2-H2O expressions valid at 1 atm total pressure, 0-100 C; calcite 0-90 C; the K2 coefficients are printed in the
  abstract.  The equation images for Kc, KH, K1 and the ion pairs were NOT read; those coefficient sets are transcribed
  from the vendored, sha-pinned PHREEQC databases (tier SOURCED_VIA_DATABASE_TRANSCRIPTION) and the transcription is
  re-checked against the file bytes by ``database_transcription_check()``.
  Stated uncertainty exists only for Kc and the two ion pairs (25 C values, from the abstract).  KH, K1, K2, Kw and the
  O2 law carry UNSTATED; the SourcedConstant they produce must hold a positive error bar (that class refuses zero), so it
  carries the COEFFICIENT-TRANSCRIPTION RESOLUTION FLOOR (half a unit in the last printed digit of every coefficient,
  propagated) and says so in its note.  That floor is a lower bound on transcription error, NOT a measurement
  uncertainty; it must never be quoted as one.

  Kw is not a Plummer & Busenberg expression: it is the phreeqc.dat ``H2O = OH- + H+`` fit, whose primary source the file
  does not name and whose domain it does not state.  Its domain here is ASSERTED_BY_THIS_MODULE (the liquid-water range
  of the CO2 system), recorded as such.

  ``water_density_kg_per_L`` (Kell 1975 form) and ``davies_A`` (Debye-Huckel A from the Malmberg & Maryott 1956 dielectric
  constant) are correlations whose coefficients were reproduced from the literature, not re-read in this session.  Davies A
  is ANCHORED to the sandbox's existing ``DAVIES_A_25C`` (0.509) and only its temperature RATIO is computed, so a 298.15 K
  world uses the same A as every existing 25 C world.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation

from experiments.sandbox_foundation.aqueous_equilibrium import (
    DAVIES_A_25C,
    OUT_OF_SOURCE_DOMAIN,
    SourcedConstant,
)
from experiments.sandbox_foundation.general_kernel import SourceDomainError
from experiments.sandbox_foundation.standard_state import molal_to_molar_logK

# ------------------------------------------------------------------------------------------------ vocabulary
SOURCED_PRIMARY_ABSTRACT = "SOURCED_PRIMARY_ABSTRACT"                    # read in the primary paper's abstract
SOURCED_VIA_DATABASE_TRANSCRIPTION = "SOURCED_VIA_DATABASE_TRANSCRIPTION"  # copied from a pinned database file
RECALLED_LITERATURE_CORRELATION = "RECALLED_LITERATURE_CORRELATION"      # literature form, coefficients not re-read
TIERS = frozenset({SOURCED_PRIMARY_ABSTRACT, SOURCED_VIA_DATABASE_TRANSCRIPTION, RECALLED_LITERATURE_CORRELATION})

UNSTATED = "UNSTATED"                       # the source states no uncertainty; never replaced by an invented one
STATED = "STATED"
TRANSCRIPTION_FLOOR_ONLY = "TRANSCRIPTION_FLOOR_ONLY"

DOMAIN_STATED_BY_SOURCE = "STATED_BY_SOURCE"
DOMAIN_ASSERTED_BY_THIS_MODULE = "ASSERTED_BY_THIS_MODULE"
DOMAIN_BASES = frozenset({DOMAIN_STATED_BY_SOURCE, DOMAIN_ASSERTED_BY_THIS_MODULE})

PB82_CITATION = ("Plummer, L.N. & Busenberg, E. (1982) The solubilities of calcite, aragonite and vaterite in CO2-H2O "
                 "solutions between 0 and 90 C, and an evaluation of the aqueous model for the system CaCO3-CO2-H2O. "
                 "Geochim. Cosmochim. Acta 46, 1011-1040. doi:10.1016/0016-7037(82)90056-4")

_N_COEFF = 6


class TemperatureLawDomainError(SourceDomainError):
    """A temperature law was asked to evaluate outside its declared domain.  Carries the OUT_OF_SOURCE_DOMAIN verdict."""

    def __init__(self, message: str, T_K: float = float("nan"), T_min_K: float = float("nan"),
                 T_max_K: float = float("nan")):
        super().__init__(message)
        self.verdict = OUT_OF_SOURCE_DOMAIN
        self.T_K = T_K
        self.T_min_K = T_min_K
        self.T_max_K = T_max_K


def _parse_decimal(s: str) -> Decimal:
    if type(s) is not str:
        raise ValueError("coefficients must be decimal strings (exact transcription)")
    try:
        d = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"coefficient {s!r} is not a decimal literal") from exc
    if not d.is_finite():
        raise ValueError(f"coefficient {s!r} is not finite")
    return d


def _half_unit(s: str) -> float:
    """Half a unit in the last printed digit of a decimal literal ('-0.077993' -> 5e-7; '669365' -> 0.5)."""
    d = _parse_decimal(s)
    if d == 0 and not re.search(r"[1-9]", s):
        return 0.0                              # an absent term ("0") is structurally zero, not a rounded number
    return 0.5 * 10.0 ** d.as_tuple().exponent


def _negate(s: str) -> str:
    s = s.strip()
    if _parse_decimal(s) == 0:
        return s
    return s[1:] if s.startswith("-") else "-" + s.lstrip("+")


def _basis_functions(T: float) -> tuple:
    return (1.0, T, 1.0 / T, math.log10(T), 1.0 / (T * T), T * T)


def _require_finite_T(T_K) -> float:
    if isinstance(T_K, bool) or not isinstance(T_K, (int, float)) or not math.isfinite(T_K) or T_K <= 0:
        raise TemperatureLawDomainError(f"temperature {T_K!r} must be a finite kelvin value > 0", float("nan"))
    return float(T_K)


@dataclass(frozen=True)
class AnalyticTemperatureLaw:
    """log10 K(T) for ONE reaction as written, on the MOLAL standard state as tabulated.  Immutable; see module doc.

    ``nu_aq`` is the net stoichiometric coefficient of the AQUEOUS SOLUTES of the reaction as written (products +,
    reactants -; solids, gases and the solvent excluded): the exponent of the molal -> molar transport.  For a gas
    solubility law (gas = dissolved species) ``nu_aq`` is +1 and the result is a Henry constant in mol/(kg atm)."""
    name: str
    reaction: str
    coefficients: tuple            # (a, b, c, d, e, f) as decimal STRINGS, exactly as printed by the source
    nu_aq: int
    T_min_K: float
    T_max_K: float
    domain_basis: str
    source: str
    tier: str
    stated_uncertainty_log10: float | None   # None == UNSTATED
    uncertainty_note: str
    units_molal: str = "dimensionless (activity quotient, molal standard state 1 mol/kg, as tabulated)"
    basis: str = "molal"

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip() or not isinstance(self.reaction, str) \
                or not self.reaction.strip():
            raise ValueError("a temperature law needs a name and a reaction")
        if type(self.coefficients) is not tuple or len(self.coefficients) != _N_COEFF:
            raise ValueError(f"coefficients must be a tuple of {_N_COEFF} decimal strings (a, b, c, d, e, f)")
        for s in self.coefficients:
            _parse_decimal(s)
        if type(self.nu_aq) is not int or isinstance(self.nu_aq, bool):
            raise ValueError("nu_aq must be an int")
        for v in (self.T_min_K, self.T_max_K):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                raise ValueError("T_min_K / T_max_K must be finite kelvin values > 0")
        if not self.T_min_K < self.T_max_K:
            raise ValueError("T_min_K must be < T_max_K")
        if self.domain_basis not in DOMAIN_BASES:
            raise ValueError(f"domain_basis must be one of {sorted(DOMAIN_BASES)}")
        if self.tier not in TIERS:
            raise ValueError(f"tier must be one of {sorted(TIERS)}")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("a temperature law must cite its source")
        u = self.stated_uncertainty_log10
        if u is not None and (isinstance(u, bool) or not isinstance(u, (int, float)) or not math.isfinite(u) or u <= 0):
            raise ValueError("stated_uncertainty_log10 must be a positive number or None (UNSTATED)")
        if self.basis != "molal":
            raise ValueError("laws are carried on the molal basis as tabulated; transport happens in sourced_constant")
        if not ("mol/kg" in self.units_molal or "molal" in self.units_molal):
            raise ValueError("units_molal must name the molal standard state")

    # ---------------------------------------------------------------------------------------- evaluation
    @property
    def coefficient_values(self) -> tuple:
        return tuple(float(_parse_decimal(s)) for s in self.coefficients)

    @property
    def uncertainty_status(self) -> str:
        return UNSTATED if self.stated_uncertainty_log10 is None else STATED

    def require_domain(self, T_K) -> float:
        T = _require_finite_T(T_K)
        if not (self.T_min_K <= T <= self.T_max_K):
            raise TemperatureLawDomainError(
                f"{self.name}: T = {T} K is outside the law's domain [{self.T_min_K}, {self.T_max_K}] K "
                f"({self.domain_basis}); refusing to extrapolate", T, self.T_min_K, self.T_max_K)
        return T

    def log10_K(self, T_K) -> float:
        """log10 K on the MOLAL basis at T_K (refuses outside the domain)."""
        T = self.require_domain(T_K)
        return float(sum(c * f for c, f in zip(self.coefficient_values, _basis_functions(T))))

    def transcription_floor_log10(self, T_K) -> float:
        """Half a unit in the last printed digit of every coefficient, propagated in absolute value at T_K."""
        T = self.require_domain(T_K)
        return float(sum(_half_unit(s) * abs(f) for s, f in zip(self.coefficients, _basis_functions(T))))

    def uncertainty_log10(self, T_K) -> tuple:
        """(u_log10, kind): the STATED uncertainty if the source gives one, else the transcription floor and
        TRANSCRIPTION_FLOOR_ONLY (never a measurement uncertainty)."""
        if self.stated_uncertainty_log10 is not None:
            self.require_domain(T_K)
            return float(self.stated_uncertainty_log10), STATED
        return self.transcription_floor_log10(T_K), TRANSCRIPTION_FLOOR_ONLY

    def reversed(self, name: str, reaction: str) -> "AnalyticTemperatureLaw":
        """The same law for the reverse reaction: every coefficient negated (exactly, as strings), nu_aq negated."""
        return AnalyticTemperatureLaw(
            name=name, reaction=reaction, coefficients=tuple(_negate(s) for s in self.coefficients),
            nu_aq=-self.nu_aq, T_min_K=self.T_min_K, T_max_K=self.T_max_K, domain_basis=self.domain_basis,
            source=self.source + f" [reversed from {self.reaction!r}]", tier=self.tier,
            stated_uncertainty_log10=self.stated_uncertainty_log10, uncertainty_note=self.uncertainty_note,
            units_molal=self.units_molal, basis=self.basis)

    def sourced_constant(self, T_K, *, basis: str = "molar", name: str | None = None) -> SourcedConstant:
        """A SourcedConstant stamped with T_K.  basis 'molal' = as tabulated; 'molar' = transported by
        standard_state.molal_to_molar_logK with nu_aq and the pure-water density at T_K."""
        T = self.require_domain(T_K)
        logk_m = self.log10_K(T)
        u, kind = self.uncertainty_log10(T)
        if basis == "molal":
            logk, units, transport = logk_m, self.units_molal, "as tabulated (molal)"
        elif basis == "molar":
            rho = water_density_kg_per_L(T)
            logk = molal_to_molar_logK(logk_m, self.nu_aq, rho)
            units = ("dimensionless (activity quotient, molar standard state 1 mol/L; transported from molal)"
                     if "dimensionless" in self.units_molal else
                     "mol/L/atm (molar; transported from molal mol/kg/atm)")
            transport = (f"molal->molar via standard_state.molal_to_molar_logK(nu_aq={self.nu_aq}, "
                         f"rho_w={rho:.7f} kg/L at {T} K)")
        else:
            raise ValueError("basis must be 'molar' or 'molal'")
        K = 10.0 ** logk
        if kind == STATED:
            unc_note = f"uncertainty: STATED +/-{u} in log10 K (source, 25 C value; carried unchanged at {T} K)"
        else:
            unc_note = (f"uncertainty: {UNSTATED} by the source; the error bar carried ({u:.3g} in log10 K) is the "
                        f"coefficient-transcription resolution FLOOR only, NOT a measurement uncertainty")
        return SourcedConstant(
            name or self.name, K, K * math.log(10.0) * u, units, T, self.source, "SOURCED",
            f"temperature law {self.name} [{self.tier}] evaluated at T_K={T}; {transport}; {unc_note}; domain "
            f"[{self.T_min_K}, {self.T_max_K}] K ({self.domain_basis}); valid ONLY at T_K={T}")

    def descriptor(self) -> tuple:
        return tuple((f.name, getattr(self, f.name)) for f in fields(self))

    def digest(self) -> str:
        return hashlib.sha256(repr(self.descriptor()).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ water properties
#: Kell (1975) J. Chem. Eng. Data 20, 97: rho(t) = (sum_k a_k t^k) / (1 + b t), t in C, kg/m^3, 0-150 C, 1 atm.
KELL_1975_NUM = ("999.83952", "16.945176", "-7.9870401e-3", "-46.170461e-6", "105.56302e-9", "-280.54253e-12")
KELL_1975_DEN = "16.879850e-3"
KELL_T_MIN_K, KELL_T_MAX_K = 273.15, 423.15
KELL_SOURCE = ("Kell, G.S. (1975) J. Chem. Eng. Data 20, 97-105, pure-water density at 1 atm, 0-150 C "
               f"[{RECALLED_LITERATURE_CORRELATION}: form + coefficients reproduced, not re-read this session; "
               "corroborated against standard_state.RHO_W_25C_KG_PER_L at 298.15 K]")

#: Malmberg & Maryott (1956) J. Res. Natl. Bur. Stand. 56, 1-8: eps_r(t) = 87.740 - 0.40008 t + 9.398e-4 t^2
#: - 1.410e-6 t^3, t in C, 0-100 C.
MALMBERG_MARYOTT_1956 = ("87.740", "-0.40008", "9.398e-4", "-1.410e-6")
MM_T_MIN_K, MM_T_MAX_K = 273.15, 373.15
DAVIES_A_SOURCE = (
    "Debye-Huckel A(T) = DAVIES_A_25C * sqrt(rho_w(T)/rho_w(298.15)) * (eps_r(298.15)*298.15/(eps_r(T)*T))^1.5; "
    "A is proportional to sqrt(rho_w)/(eps_r T)^1.5 (Debye-Huckel theory).  eps_r: Malmberg & Maryott (1956) "
    "J. Res. NBS 56, 1-8; rho_w: Kell (1975) "
    f"[{RECALLED_LITERATURE_CORRELATION}]; anchor: aqueous_equilibrium.DAVIES_A_25C")
REFERENCE_T_K = 298.15


def _water_T_check(T_K, lo, hi, what) -> float:
    T = _require_finite_T(T_K)
    if not (lo <= T <= hi):
        raise TemperatureLawDomainError(f"{what}: T = {T} K outside [{lo}, {hi}] K; refusing to extrapolate",
                                        T, lo, hi)
    return T


def water_density_kg_per_L(T_K) -> float:
    """Pure-water density (kg/L) at 1 atm, Kell (1975) form, 273.15-423.15 K."""
    t = _water_T_check(T_K, KELL_T_MIN_K, KELL_T_MAX_K, "water density") - 273.15
    num = sum(float(c) * t ** k for k, c in enumerate(KELL_1975_NUM))
    return num / (1.0 + float(KELL_1975_DEN) * t) / 1000.0


def water_dielectric_constant(T_K) -> float:
    """Relative permittivity of water, Malmberg & Maryott (1956), 273.15-373.15 K."""
    t = _water_T_check(T_K, MM_T_MIN_K, MM_T_MAX_K, "dielectric constant") - 273.15
    return sum(float(c) * t ** k for k, c in enumerate(MALMBERG_MARYOTT_1956))


def davies_A(T_K) -> SourcedConstant:
    """Davies/Debye-Huckel A (kg^1/2 mol^-1/2) at T_K, anchored to DAVIES_A_25C; status DERIVED, valid only at T_K."""
    T = _water_T_check(T_K, MM_T_MIN_K, MM_T_MAX_K, "Davies A")
    ratio = (math.sqrt(water_density_kg_per_L(T) / water_density_kg_per_L(REFERENCE_T_K))
             * ((water_dielectric_constant(REFERENCE_T_K) * REFERENCE_T_K)
                / (water_dielectric_constant(T) * T)) ** 1.5)
    return SourcedConstant(
        "davies_A", DAVIES_A_25C.value * ratio, DAVIES_A_25C.uncertainty * ratio, DAVIES_A_25C.units, T,
        DAVIES_A_SOURCE, "DERIVED",
        f"A(T)/A(298.15) = {ratio:.8f}; the 25 C anchor's +/-{DAVIES_A_25C.uncertainty} is scaled by the same ratio "
        f"(the correlations' own error is not quantified); valid ONLY at T_K={T}")


# ------------------------------------------------------------------------------------------------ the laws
_PB_CO2_DOMAIN = (273.15, 373.15)        # abstract: CO2-H2O expressions 0-100 C at 1 atm
_PB_CALCITE_DOMAIN = (273.15, 363.15)    # abstract: calcite 0-90 C

PB82_LOG_KC = AnalyticTemperatureLaw(
    name="log_Kc_calcite_PB82", reaction="CaCO3(calcite) = Ca+2 + CO3-2",
    coefficients=("-171.9065", "-0.077993", "2839.319", "71.595", "0", "0"), nu_aq=2,
    T_min_K=_PB_CALCITE_DOMAIN[0], T_max_K=_PB_CALCITE_DOMAIN[1], domain_basis=DOMAIN_STATED_BY_SOURCE,
    source=PB82_CITATION + "; coefficients transcribed from phreeqc.dat 'Calcite' -analytic (vendored, sha-pinned) "
           "and identical in wateq4f_PWN.dat 'Calcite 12'; 25 C value and +/-0.020 from the abstract",
    tier=SOURCED_VIA_DATABASE_TRANSCRIPTION, stated_uncertainty_log10=0.020,
    uncertainty_note="+/-0.020 is the abstract's stated 25 C uncertainty; its temperature dependence was not read")

PB82_KH_CO2 = AnalyticTemperatureLaw(
    name="log_KH_CO2_PB82", reaction="CO2(g) = CO2(aq)",
    coefficients=("108.3865", "0.01985076", "-6919.53", "-40.45154", "669365.0", "0"), nu_aq=1,
    T_min_K=_PB_CO2_DOMAIN[0], T_max_K=_PB_CO2_DOMAIN[1], domain_basis=DOMAIN_STATED_BY_SOURCE,
    source=PB82_CITATION + "; coefficients transcribed from wateq4f_PWN.dat 'CO2(g)' -analytical (vendored, "
           "sha-pinned).  NOTE: phreeqc.dat's CO2(g) is a DIFFERENT 6-term fit (not P&B)",
    tier=SOURCED_VIA_DATABASE_TRANSCRIPTION, stated_uncertainty_log10=None,
    uncertainty_note="UNSTATED in what was read", units_molal="mol/kg/atm (molal Henry constant, p in atm)")

PB82_K1 = AnalyticTemperatureLaw(
    name="log_K1_CO2_PB82", reaction="CO2(aq) + H2O = HCO3- + H+",
    coefficients=("-356.3094", "-0.06091964", "21834.37", "126.8339", "-1684915", "0"), nu_aq=1,
    T_min_K=_PB_CO2_DOMAIN[0], T_max_K=_PB_CO2_DOMAIN[1], domain_basis=DOMAIN_STATED_BY_SOURCE,
    source=PB82_CITATION + "; reconstructed as (phreeqc.dat 'CO3-2 + H+ = HCO3-') - (phreeqc.dat 'CO3-2 + 2 H+ = "
           "CO2 + H2O') -analytic, coefficient by coefficient (identical blocks in wateq4f_PWN.dat)",
    tier=SOURCED_VIA_DATABASE_TRANSCRIPTION, stated_uncertainty_log10=None, uncertainty_note="UNSTATED")

PB82_K2 = AnalyticTemperatureLaw(
    name="log_K2_CO2_PB82", reaction="HCO3- = CO3-2 + H+",
    coefficients=("-107.8871", "-0.03252849", "5151.79", "38.92561", "-563713.9", "0"), nu_aq=1,
    T_min_K=_PB_CO2_DOMAIN[0], T_max_K=_PB_CO2_DOMAIN[1], domain_basis=DOMAIN_STATED_BY_SOURCE,
    source=PB82_CITATION + "; coefficients printed in the abstract; equal (sign-reversed) to phreeqc.dat "
           "'CO3-2 + H+ = HCO3-' -analytic",
    tier=SOURCED_PRIMARY_ABSTRACT, stated_uncertainty_log10=None, uncertainty_note="UNSTATED")

PB82_CAHCO3 = AnalyticTemperatureLaw(
    name="log_K_CaHCO3+_PB82", reaction="Ca+2 + HCO3- = CaHCO3+",
    coefficients=("1209.12", "0.31294", "-34765.05", "-478.782", "0.0", "0"), nu_aq=-1,
    T_min_K=_PB_CALCITE_DOMAIN[0], T_max_K=_PB_CALCITE_DOMAIN[1], domain_basis=DOMAIN_ASSERTED_BY_THIS_MODULE,
    source=PB82_CITATION + "; coefficients transcribed from wateq4f_PWN.dat '#CaHCO3+ 77' -analytical; 25 C value "
           "and +/-0.07 from the abstract.  phreeqc.dat carries it combined with K2 with b = 0.34546894 (implies "
           "0.31294045, not 0.31294)",
    tier=SOURCED_VIA_DATABASE_TRANSCRIPTION, stated_uncertainty_log10=0.07,
    uncertainty_note="+/-0.07 stated at 25 C; domain asserted = the calcite 0-90 C range (not read for the pair)")

PB82_CACO3 = AnalyticTemperatureLaw(
    name="log_K_CaCO3aq_PB82", reaction="Ca+2 + CO3-2 = CaCO3(aq)",
    coefficients=("-1228.732", "-0.299444", "35512.75", "485.818", "0.0", "0"), nu_aq=-1,
    T_min_K=_PB_CALCITE_DOMAIN[0], T_max_K=_PB_CALCITE_DOMAIN[1], domain_basis=DOMAIN_ASSERTED_BY_THIS_MODULE,
    source=PB82_CITATION + "; coefficients transcribed from wateq4f_PWN.dat '#CaCO3 78' -analytical; 25 C value and "
           "+/-0.14 from the abstract.  phreeqc.dat prints b = -0.299440 (differs in the 6th decimal)",
    tier=SOURCED_VIA_DATABASE_TRANSCRIPTION, stated_uncertainty_log10=0.14,
    uncertainty_note="+/-0.14 stated at 25 C; domain asserted = the calcite 0-90 C range (not read for the pair)")

PHREEQC_DAT_KW = AnalyticTemperatureLaw(
    name="log_Kw_phreeqc_dat", reaction="H2O = OH- + H+",
    coefficients=("293.29227", "0.1360833", "-10576.913", "-123.73158", "0", "-6.996455e-5"), nu_aq=2,
    T_min_K=273.15, T_max_K=373.15, domain_basis=DOMAIN_ASSERTED_BY_THIS_MODULE,
    source="phreeqc.dat (PHREEQC 3, as shipped by phreeqpython 1.6.2; vendored, sha-pinned) 'H2O = OH- + H+' "
           "-analytic.  NOT Plummer & Busenberg; the file names no primary source and states no domain",
    tier=SOURCED_VIA_DATABASE_TRANSCRIPTION, stated_uncertainty_log10=None, uncertainty_note="UNSTATED")

PHREEQC_DAT_O2_HENRY = AnalyticTemperatureLaw(
    name="log_KH_O2_phreeqc_dat", reaction="O2(g) = O2(aq)",
    coefficients=("-7.5001", "7.8981e-3", "0.0", "0.0", "2.0027e5", "0"), nu_aq=1,
    T_min_K=273.15, T_max_K=373.15, domain_basis=DOMAIN_ASSERTED_BY_THIS_MODULE,
    source="phreeqc.dat 'O2(g)' -analytic (vendored, sha-pinned); wateq4f_PWN.dat marks the same law 'log K from "
           "llnl.dat Aug 23, 2005'.  No primary source or domain is stated in the file",
    tier=SOURCED_VIA_DATABASE_TRANSCRIPTION, stated_uncertainty_log10=None, uncertainty_note="UNSTATED",
    units_molal="mol/kg/atm (molal Henry constant, p in atm)")

PB82_LAWS = (PB82_LOG_KC, PB82_KH_CO2, PB82_K1, PB82_K2, PB82_CAHCO3, PB82_CACO3)
ALL_LAWS = PB82_LAWS + (PHREEQC_DAT_KW, PHREEQC_DAT_O2_HENRY)


# ------------------------------------------------------------------------------------------------ transcription check
def _db_paths():
    from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import run_solid_equilibrium_xxiii as H
    return H, H.PHREEQC_DAT, H.WATEQ_DAT


def _analytic_after(text: str, reaction_line: str, *, file_label: str, header: str | None = None) -> tuple:
    """The -analytic / -analytical tokens (as STRINGS) in the block whose reaction line is ``reaction_line`` (and, if
    ``header`` is given, whose preceding line is that phase header).  Commented lines are skipped; the scan stops at
    the next non-indented header."""
    lines = text.replace("\r\n", "\n").split("\n")
    target = " ".join(reaction_line.split())
    hits = [i for i, ln in enumerate(lines) if " ".join(ln.split()) == target and not ln.lstrip().startswith("#")
            and (header is None or (i > 0 and lines[i - 1].split() and lines[i - 1].split()[0] == header))]
    if len(hits) != 1:
        raise ValueError(f"{file_label}: expected exactly one line {reaction_line!r}, found {len(hits)}")
    i = hits[0]
    for j in range(i + 1, min(i + 10, len(lines))):
        s = lines[j].strip()
        if not s or s.startswith("#"):
            continue
        tok = s.split("#")[0].split()
        if tok[0].lower() in ("-analytic", "-analytical", "-analytical_expression"):
            return tuple(tok[1:]), j + 1
        if not lines[j].startswith((" ", "\t")):
            break
    raise ValueError(f"{file_label}: no -analytic under {reaction_line!r}")


def _dec_eq(strs_a, strs_b) -> bool:
    a = [_parse_decimal(s) for s in strs_a] + [Decimal(0)] * (_N_COEFF - len(strs_a))
    b = [_parse_decimal(s) for s in strs_b] + [Decimal(0)] * (_N_COEFF - len(strs_b))
    return a == b


def database_transcription_check() -> dict:
    """Re-read every transcribed coefficient set from the vendored, sha-pinned databases (exact decimal arithmetic)."""
    H, pdat, wdat = _db_paths()
    ptxt = H._pinned_bytes(pdat).decode("latin-1")
    wtxt = H._pinned_bytes(wdat).decode("latin-1")
    out = {}

    def rec(law, ok, detail):
        out[law.name] = {"match": bool(ok), "law": list(law.coefficients), **detail}

    cal_p, lp = _analytic_after(ptxt, "CaCO3 = CO3-2 + Ca+2", file_label="phreeqc.dat", header="Calcite")
    cal_w, lw0 = _analytic_after(wtxt, "CaCO3 = Ca+2 + CO3-2", file_label="wateq4f_PWN.dat", header="Calcite")
    rec(PB82_LOG_KC, _dec_eq(cal_p, PB82_LOG_KC.coefficients) and _dec_eq(cal_w, PB82_LOG_KC.coefficients),
        {"phreeqc.dat": [list(cal_p), lp], "wateq4f_PWN.dat": [list(cal_w), lw0]})
    kh_w, lw = _analytic_after(wtxt, "CO2 = CO2", file_label="wateq4f_PWN.dat")
    kh_p, lp2 = _analytic_after(ptxt, "CO2 = CO2", file_label="phreeqc.dat")
    rec(PB82_KH_CO2, _dec_eq(kh_w, PB82_KH_CO2.coefficients),
        {"wateq4f_PWN.dat": [list(kh_w), lw], "phreeqc.dat_DIFFERENT_FIT": [list(kh_p), lp2]})
    h1, l1 = _analytic_after(ptxt, "CO3-2 + H+ = HCO3-", file_label="phreeqc.dat")
    h2, l2 = _analytic_after(ptxt, "CO3-2 + 2 H+ = CO2 + H2O", file_label="phreeqc.dat")
    pad = lambda t: [_parse_decimal(s) for s in t] + [Decimal(0)] * (_N_COEFF - len(t))  # noqa: E731
    k1 = [a - b for a, b in zip(pad(h1), pad(h2))]
    rec(PB82_K1, k1 == pad(PB82_K1.coefficients),
        {"phreeqc.dat_HCO3_formation": [list(h1), l1], "phreeqc.dat_CO2_formation": [list(h2), l2],
         "difference": [str(x) for x in k1]})
    rec(PB82_K2, [-x for x in pad(h1)] == pad(PB82_K2.coefficients), {"phreeqc.dat_negated": [list(h1), l1]})
    cah_w, lw3 = _analytic_after(wtxt, "Ca+2 + HCO3- = CaHCO3+", file_label="wateq4f_PWN.dat")
    cah_p, lp3 = _analytic_after(ptxt, "Ca+2 + CO3-2 + H+ = CaHCO3+", file_label="phreeqc.dat")
    implied = [a - b for a, b in zip(pad(cah_p), pad(h1))]
    rec(PB82_CAHCO3, _dec_eq(cah_w, PB82_CAHCO3.coefficients),
        {"wateq4f_PWN.dat": [list(cah_w), lw3], "phreeqc.dat_combined": [list(cah_p), lp3],
         "phreeqc.dat_implied_pair": [str(x) for x in implied],
         "phreeqc.dat_implied_equals_law": implied == pad(PB82_CAHCO3.coefficients)})
    cac_w, lw4 = _analytic_after(wtxt, "Ca+2 + CO3-2 = CaCO3", file_label="wateq4f_PWN.dat")
    cac_p, lp4 = _analytic_after(ptxt, "Ca+2 + CO3-2 = CaCO3", file_label="phreeqc.dat")
    rec(PB82_CACO3, _dec_eq(cac_w, PB82_CACO3.coefficients),
        {"wateq4f_PWN.dat": [list(cac_w), lw4], "phreeqc.dat": [list(cac_p), lp4],
         "phreeqc.dat_equals_law": _dec_eq(cac_p, PB82_CACO3.coefficients)})
    kw_p, lp5 = _analytic_after(ptxt, "H2O = OH- + H+", file_label="phreeqc.dat")
    rec(PHREEQC_DAT_KW, _dec_eq(kw_p, PHREEQC_DAT_KW.coefficients), {"phreeqc.dat": [list(kw_p), lp5]})
    o2_p, lp6 = _analytic_after(ptxt, "O2 = O2", file_label="phreeqc.dat")
    rec(PHREEQC_DAT_O2_HENRY, _dec_eq(o2_p, PHREEQC_DAT_O2_HENRY.coefficients), {"phreeqc.dat": [list(o2_p), lp6]})
    return out
