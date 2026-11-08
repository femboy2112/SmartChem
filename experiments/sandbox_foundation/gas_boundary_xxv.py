"""OPERATION XXV Phase III-B -- a GENERIC gas-liquid (Henry) boundary operator (research code only).

A dissolved NEUTRAL species in one compartment exchanges with an external gas reservoir held at a fixed partial
pressure p (atm).  At the interface the dissolved activity is fixed by Henry's law, a = K_H(T) * p, and the transfer is
first-order in the departure from it:

    J = kLa * V * (c_sat - c)        (mol/s into the compartment),    c_sat = K_H(T) * p   (mol/L)

This is the existing ``general_coupled.ExternalBoundary(mode="fixed_activity", target_conc=c_sat, k_transfer=kLa*V)``
pattern, so the CoupledWorld integrates it as transport and LEDGERS it: the boundary's flux is integrated alongside the
inventory, and the receipt's material balance closes only with the boundary term (``external_flux``).

WHAT THIS MODULE ADDS ON TOP OF ExternalBoundary.
  * K_H is a ``SourcedConstant`` stamped with the temperature it was produced for, either evaluated from a temperature
    law at T_K (``from_law``) or supplied directly (a single-temperature record).  It is stored on the MOLAL basis
    (mol/kg/atm) or the MOLAR basis (mol/L/atm), declared explicitly; molal values are transported to molar with
    ``standard_state.molal_to_molar_logK`` (nu_aq = +1) and the pure-water density at the constant's own T_K.
  * TEMPERATURE COVERAGE.  ``admissibility.temperature_domain_violations`` only scans reaction rate laws; an
    ExternalBoundary carries a bare float.  ``boundary_temperature_violations`` is the matching check for these
    boundaries, and ``build_open_world`` / ``verify_world_boundaries`` refuse a world whose temperature differs from any
    boundary constant's T_K by more than ``admissibility.TEMPERATURE_MATCH_TOL_K`` (the same tolerance), or whose
    installed ExternalBoundary no longer matches the declared boundary.
  * kLa is a RATE SCALE, tier ASSUMED_PARAMETER: it sets how fast the dissolved species approaches c_sat, never where the
    steady state sits (at steady state J = 0, so c = c_sat for any kLa > 0).

The module is chemistry-agnostic by construction: it names no substance.  Ideal gas reservoir (fugacity = p), the
dissolved neutral species at activity coefficient 1 (no salting-out) -- the same assumptions as the sandbox elsewhere.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from experiments.sandbox_foundation.admissibility import TEMPERATURE_MATCH_TOL_K
from experiments.sandbox_foundation.aqueous_equilibrium import SourcedConstant, _is_molar_standard_state
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER
from experiments.sandbox_foundation.general_coupled import CoupledWorld, ExternalBoundary, _canon_num, _species_key
from experiments.sandbox_foundation.general_kernel import Phase, SourceDomainError, Species
from experiments.sandbox_foundation.standard_state import molal_to_molar_logK
from experiments.sandbox_foundation.temperature_law_xxv import AnalyticTemperatureLaw, water_density_kg_per_L

HENRY_BASES = ("molal", "molar")


class GasBoundaryError(ValueError):
    """A malformed gas-liquid boundary declaration."""


class GasBoundaryTemperatureError(SourceDomainError):
    """A boundary's Henry constant would execute at a temperature other than the one it was produced for."""


def _finite_pos(v, what, *, allow_zero=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or (v == 0 and not allow_zero):
        raise GasBoundaryError(f"{what} must be a finite number {'>= 0' if allow_zero else '> 0'}")
    return float(v)


@dataclass(frozen=True)
class GasLiquidBoundary:
    """Fixed-partial-pressure gas reservoir over one dissolved neutral species (see module docstring)."""
    name: str
    compartment: str
    dissolved: Species
    henry: SourcedConstant           # K_H at henry.T_K; mol/kg/atm (molal) or mol/L/atm (molar)
    henry_basis: str                 # "molal" | "molar"
    p_atm: float
    kLa_per_s: float
    volume_L: float
    kLa_tier: str = ASSUMED_PARAMETER

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip() or not isinstance(self.compartment, str) \
                or not self.compartment.strip():
            raise GasBoundaryError("a gas boundary needs a name and a compartment")
        if type(self.dissolved) is not Species or self.dissolved.phase is not Phase.AQUEOUS or self.dissolved.charge:
            raise GasBoundaryError("the dissolved species must be a NEUTRAL AQUEOUS Species")
        if type(self.henry) is not SourcedConstant or self.henry.status == "UNKNOWN":
            raise GasBoundaryError("henry must be a SourcedConstant with a value (an UNKNOWN K_H cannot drive a flux)")
        if self.henry_basis not in HENRY_BASES:
            raise GasBoundaryError(f"henry_basis must be one of {HENRY_BASES}")
        units = self.henry.units
        if "atm" not in units:
            raise GasBoundaryError(f"henry units {units!r} must be per atm")
        is_molar = _is_molar_standard_state(units)
        if (self.henry_basis == "molar") != is_molar:
            raise GasBoundaryError(f"henry_basis {self.henry_basis!r} contradicts the constant's units {units!r}")
        _finite_pos(self.henry.T_K, "henry.T_K")
        _finite_pos(self.p_atm, "p_atm", allow_zero=True)
        _finite_pos(self.kLa_per_s, "kLa_per_s")
        _finite_pos(self.volume_L, "volume_L")
        if not isinstance(self.kLa_tier, str):
            raise GasBoundaryError("kLa_tier must be a string")

    @classmethod
    def from_law(cls, law: AnalyticTemperatureLaw, T_K: float, *, name: str, compartment: str, dissolved: Species,
                 p_atm: float, kLa_per_s: float, volume_L: float) -> "GasLiquidBoundary":
        """K_H from a gas-solubility temperature law (gas = dissolved, nu_aq = +1) evaluated at T_K, molal basis."""
        if type(law) is not AnalyticTemperatureLaw:
            raise GasBoundaryError("law must be an AnalyticTemperatureLaw")
        if law.nu_aq != 1:
            raise GasBoundaryError(f"a Henry law has exactly one aqueous product (nu_aq = +1); {law.name} has "
                                   f"{law.nu_aq}")
        return cls(name, compartment, dissolved, law.sourced_constant(T_K, basis="molal"), "molal", p_atm, kLa_per_s,
                   volume_L)

    @property
    def T_K(self) -> float:
        return float(self.henry.T_K)

    def henry_molar(self) -> float:
        """K_H in mol/L/atm at the constant's own T_K."""
        if self.henry_basis == "molar":
            return float(self.henry.value)
        return 10.0 ** molal_to_molar_logK(math.log10(self.henry.value), 1, water_density_kg_per_L(self.T_K))

    def target_conc_molar(self) -> float:
        """c_sat = K_H * p (mol/L): the dissolved concentration the reservoir holds at the interface."""
        return self.henry_molar() * self.p_atm

    def temperature_violation(self, T_K) -> tuple:
        """() if the boundary may execute at T_K, else (name, field, sourced T_K)."""
        ok = (isinstance(T_K, (int, float)) and not isinstance(T_K, bool) and math.isfinite(T_K)
              and abs(float(T_K) - self.T_K) <= TEMPERATURE_MATCH_TOL_K)
        return () if ok else (self.name, "henry", self.T_K)

    def require_temperature(self, T_K) -> None:
        bad = self.temperature_violation(T_K)
        if bad:
            raise GasBoundaryTemperatureError(
                f"gas boundary {self.name!r}: its Henry constant was produced for T_K={self.T_K} but the world runs at "
                f"{T_K!r} K (tol {TEMPERATURE_MATCH_TOL_K} K); refusing to execute it off-temperature")

    def external_boundary(self, T_K) -> ExternalBoundary:
        """The ledgered kernel boundary at world temperature T_K (refused off the constant's temperature)."""
        self.require_temperature(T_K)
        return ExternalBoundary(self.name, self.compartment, self.dissolved, mode="fixed_activity",
                                k_transfer=self.kLa_per_s * self.volume_L, target_conc=self.target_conc_molar())

    def descriptor(self) -> tuple:
        h = self.henry
        return ("GasLiquidBoundary", self.name, self.compartment, _species_key(self.dissolved),
                (h.name, _canon_num(h.value), _canon_num(h.uncertainty), h.units, _canon_num(h.T_K), h.source,
                 h.status, h.note),
                self.henry_basis, _canon_num(self.p_atm), _canon_num(self.kLa_per_s), _canon_num(self.volume_L),
                self.kLa_tier)

    def digest(self) -> str:
        return hashlib.sha256(repr(self.descriptor()).encode()).hexdigest()


def boundary_temperature_violations(gas_boundaries, T_K) -> list:
    """[(name, field, sourced T_K)] for every gas boundary whose constant does not belong to T_K."""
    return [v for v in (gb.temperature_violation(T_K) for gb in gas_boundaries) if v]


def require_boundary_temperatures(gas_boundaries, T_K) -> None:
    bad = boundary_temperature_violations(gas_boundaries, T_K)
    if bad:
        raise GasBoundaryTemperatureError(
            f"world temperature {T_K!r} K is outside the sourced temperature of gas boundary constant(s) {bad} "
            f"(name, field, sourced T_K); refusing (no extrapolation)")


def build_open_world(compartments: list, gas_boundaries: list, T_K: float, *, interfaces: list = (),
                     boundaries: list = ()) -> CoupledWorld:
    """A CoupledWorld at T_K with each gas boundary installed as its ledgered ExternalBoundary (refused off-T)."""
    if any(type(gb) is not GasLiquidBoundary for gb in gas_boundaries):
        raise GasBoundaryError("gas_boundaries must be GasLiquidBoundary objects")
    require_boundary_temperatures(gas_boundaries, T_K)
    ext = [gb.external_boundary(T_K) for gb in gas_boundaries]
    return CoupledWorld(list(compartments), list(interfaces), list(boundaries) + ext, temperature_K=T_K)


def verify_world_boundaries(world: CoupledWorld, gas_boundaries) -> None:
    """Re-check, immediately before integration, that the world's temperature matches every gas boundary constant and
    that each installed ExternalBoundary is exactly the one the declaration produces."""
    require_boundary_temperatures(gas_boundaries, world.temperature_K)
    installed = {b.name: b for b in world.boundaries}
    for gb in gas_boundaries:
        if installed.get(gb.name) != gb.external_boundary(world.temperature_K):
            raise GasBoundaryError(f"world boundary {gb.name!r} does not match its gas-boundary declaration")


def boundary_ledger(trajectory) -> dict:
    """The receipt's material-balance evidence: per conserved component, the integrated external flux, the measured
    inventory change, and their residual; plus the overall closure flag."""
    r = trajectory.receipt
    return {"material_balance_closed": bool(r.material_balance_closed),
            "external_flux_mol": dict(r.external_flux), "raw_material_change_mol": dict(r.raw_material_change),
            "ledger_adjusted_residual_mol": dict(r.ledger_adjusted_residual)}
