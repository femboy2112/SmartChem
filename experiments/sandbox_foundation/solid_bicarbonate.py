"""OPERATION XIII P4 -- a first-class SOLID sodium-bicarbonate phase that dissolves into the reacting aqueous system.

The flagship starts with a POWDER, not a dissolved inventory.  This module adds an explicit solid inventory
n_NaHCO3,solid (mol) that dissolves, supplying BOTH sodium and total inorganic carbon to the aqueous phase in the
correct 1:1:1 stoichiometry:

    NaHCO3(s) -> Na+ + HCO3-         (one mole of solid -> one mole Na, one mole inorganic carbon)

No atom or charge appears from nowhere: total sodium (aqueous + solid) and total carbon (aqueous + solid) are
conserved across any dissolution; the solid is electroneutral, so dissolving it preserves charge balance.

EQUILIBRIUM vs RATE are different questions and kept separate (section 6):

  * EQUILIBRIUM (thermodynamic): a solubility / saturation limit.  NaHCO3(s) <-> Na+ + HCO3-, Ksp = [Na+][HCO3-]
    (ideal-solubility-product approximation; activity corrections omitted -> a stated caveat).  Ksp is DERIVED from
    the SOURCED molar solubility S (Ksp = S^2).  The saturation index SI = [Na+][HCO3-]/Ksp: SI < 1 undersaturated
    (solid can dissolve), SI >= 1 saturated (no net dissolution).  `dissolve_to_saturation` is the fast-dissolution
    limit: dissolve until SI = 1 or the solid is exhausted.

  * RATE (kinetic): the dissolution TIMESCALE depends on particle size, surface area, agitation, temperature and
    mass transfer -- apparatus-specific.  `dissolution_step` implements a finite first-order-in-undersaturation
    rate dn_solid/dt = -k_diss * max(0, 1 - SI), but k_diss is an ASSUMED/synthetic parameter
    (claim_tiers.ASSUMED_PARAMETER), explicitly NOT a measured constant: no baking-soda particle-size distribution
    or universal dissolution rate is invented.

The acid coupling is automatic and is the flagship's whole point: in a vinegar (acidic) solution, HCO3- dissolving
is consumed by H+ (HCO3- + H+ -> CO2 + H2O), keeping [HCO3-] -- and thus SI -- low, so the solid keeps dissolving
until the ACID is spent or the SOLID is exhausted (the bicarbonate-limited / acid-limited distinction, now with a
real powder).  That emerges from the coupled equilibrium; it is not scripted.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from scipy.optimize import brentq

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.aqueous_equilibrium import InvalidParameterError, SourcedConstant
from experiments.sandbox_foundation.coupled_gas_equilibrium import MixedGasSystem
from experiments.sandbox_foundation.coupled_gas_equilibrium import solve as gas_solve

# Sodium bicarbonate molar solubility at ~25 C.  Tertiary: ~9.6 g/100 mL (20 C) to ~10.3 g/100 mL (25 C); MW 84.007
# g/mol -> ~1.14-1.23 mol/L.  A conservative +/-0.15 covers the inter-source + 20-25 C spread.  Solubility RISES with
# temperature (a caveat: this is 25 C-anchored).
NAHCO3_SOLUBILITY_25C = SourcedConstant(
    "S_NaHCO3", 1.2, 0.15, "mol/L (molar solubility)", 298.15,
    "Aqueous solubility of NaHCO3 at ~25 C: ~9.6 g/100 mL (20 C)-10.3 g/100 mL (25 C) (CRC Handbook / PubChem CID "
    "516892) with MW 84.007 g/mol -> ~1.14-1.23 mol/L.", "SOURCED",
    "Solubility rises with temperature; this value is 25 C-anchored.  The +/-0.15 is an inter-source/temperature "
    "spread, not a statistical sigma.")

# Ksp = S^2 (ideal solubility product), DERIVED from the sourced solubility; uncertainty propagated 2 S sigma_S.
KSP_NAHCO3_25C = SourcedConstant(
    "Ksp_NaHCO3", NAHCO3_SOLUBILITY_25C.value ** 2, 2 * NAHCO3_SOLUBILITY_25C.value * NAHCO3_SOLUBILITY_25C.uncertainty,
    "mol^2/L^2 (molar solubility product)", 298.15,
    f"DERIVED Ksp = S^2 from the sourced NaHCO3 molar solubility S = {NAHCO3_SOLUBILITY_25C.value} mol/L.", "DERIVED",
    "IDEAL solubility product [Na+][HCO3-]; the activity-coefficient (Davies) correction to Ksp is OMITTED -- a "
    "stated approximation, so the saturation limit is model-level, not independently validated.")


class SolidBicarbonateError(InvalidParameterError):
    """Fail-closed refusal in the solid-dissolution layer."""


@dataclass(frozen=True)
class SolidBicarbonateSystem:
    """Aqueous mixed system (totals, mol) over a liquid volume, plus an undissolved NaHCO3 solid inventory (mol)."""
    volume_L: float
    n_acetate_mol: float
    n_carbon_aqueous_mol: float
    n_sodium_aqueous_mol: float
    n_solid_mol: float
    activity_model: str = "ideal"   # saturated NaHCO3 (~1.2 M) is far outside the Davies domain (0.5 M); the bulk
    #   solubility S is itself an empirical saturation value, so the ideal model is the consistent default for the
    #   dissolution/SI calculation.  Davies is available but DEMOTES near saturation (honest -- see _tier).
    temperature_K: float = 298.15

    def __post_init__(self):
        for name in ("volume_L", "n_acetate_mol", "n_carbon_aqueous_mol", "n_sodium_aqueous_mol", "n_solid_mol"):
            v = getattr(self, name)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= -1e-15):
                raise SolidBicarbonateError(f"{name}={v!r} must be finite and >= 0")
        if self.volume_L <= 0:
            raise SolidBicarbonateError("volume_L must be > 0")
        if self.activity_model not in ("ideal", "davies"):
            raise SolidBicarbonateError("activity_model must be 'ideal' or 'davies'")

    @property
    def total_sodium_mol(self) -> float:
        return self.n_sodium_aqueous_mol + self.n_solid_mol          # solid carries 1 Na each

    @property
    def total_carbon_mol(self) -> float:
        return self.n_carbon_aqueous_mol + self.n_solid_mol          # solid carries 1 C each

    def speciate(self):
        return gas_solve(MixedGasSystem(
            mode="closed", total_acetate_M=self.n_acetate_mol / self.volume_L,
            total_carbon_M=self.n_carbon_aqueous_mol / self.volume_L,
            sodium_M=self.n_sodium_aqueous_mol / self.volume_L,
            activity_model=self.activity_model, temperature_K=self.temperature_K))


def saturation_index(system: SolidBicarbonateSystem) -> float:
    """SI = [Na+][HCO3-] / Ksp at the current aqueous composition.  SI < 1 undersaturated; >= 1 saturated."""
    sp = system.speciate()
    na = system.n_sodium_aqueous_mol / system.volume_L
    return (na * sp.hco3_M) / KSP_NAHCO3_25C.value


def _tier(system: SolidBicarbonateSystem) -> str:
    """NUMERICALLY_VERIFIED only if the after-state speciation is admitted; else UNVERIFIED (e.g. a near-saturated
    solution outside the Davies activity domain -- the model demotes rather than vouch)."""
    return (claim_tiers.NUMERICALLY_VERIFIED if "UNVERIFIED" not in system.speciate().verdict
            else claim_tiers.UNVERIFIED)


@dataclass(frozen=True)
class DissolutionResult:
    dissolved_mol: float            # amount of solid that dissolved (mol)
    saturated: bool                 # dissolution stopped at the solubility limit
    exhausted: bool                 # the solid ran out (all dissolved)
    saturation_index_after: float
    system_after: SolidBicarbonateSystem
    claim_tier: str
    note: str = ""


def _si_after_dissolving(system: SolidBicarbonateSystem, x: float) -> float:
    """SI if x mol of solid dissolves (adds x to aqueous Na and C)."""
    trial = replace(system, n_carbon_aqueous_mol=system.n_carbon_aqueous_mol + x,
                    n_sodium_aqueous_mol=system.n_sodium_aqueous_mol + x,
                    n_solid_mol=max(system.n_solid_mol - x, 0.0))
    return saturation_index(trial)


def dissolve_to_saturation(system: SolidBicarbonateSystem) -> DissolutionResult:
    """Fast-dissolution (thermodynamic) limit: dissolve solid until SI = 1 or the solid is exhausted.  Conserves
    total sodium and total carbon (1:1 transfer solid -> aqueous); charge preserved (solid is electroneutral)."""
    if system.n_solid_mol <= 0:
        return DissolutionResult(0.0, False, False, saturation_index(system), system,
                                 _tier(system), "no solid present")
    si_all = _si_after_dissolving(system, system.n_solid_mol)
    if si_all <= 1.0:
        # even dissolving everything stays undersaturated -> all dissolves, exhausted.
        x = system.n_solid_mol
        exhausted, saturated = True, False
    else:
        # SI crosses 1 before the solid is exhausted -> dissolve to saturation.
        f = lambda x: _si_after_dissolving(system, x) - 1.0  # noqa: E731
        if f(0.0) >= 0.0:
            x = 0.0                                  # already saturated: nothing dissolves
        else:
            x = float(brentq(f, 0.0, system.n_solid_mol, xtol=1e-15, rtol=1e-14))
        exhausted, saturated = False, True
    after = replace(system, n_carbon_aqueous_mol=system.n_carbon_aqueous_mol + x,
                    n_sodium_aqueous_mol=system.n_sodium_aqueous_mol + x,
                    n_solid_mol=max(system.n_solid_mol - x, 0.0))
    return DissolutionResult(
        dissolved_mol=x, saturated=saturated, exhausted=exhausted,
        saturation_index_after=saturation_index(after), system_after=after,
        claim_tier=_tier(after),
        note="fast-dissolution (thermodynamic) limit: equilibrium saturation, no kinetic timescale")


def dissolution_step(system: SolidBicarbonateSystem, *, k_diss_mol_per_s: float, dt: float) -> DissolutionResult:
    """Finite-RATE dissolution over dt: dn_solid/dt = -k_diss * max(0, 1 - SI).  k_diss is an ASSUMED/synthetic
    parameter (NOT a measured constant; grain size / surface area / agitation set it per apparatus), so the result
    is tier ASSUMED_PARAMETER.  The step is bounded so it neither over-dissolves the solid nor overshoots SI = 1."""
    if not (math.isfinite(k_diss_mol_per_s) and k_diss_mol_per_s > 0):
        raise SolidBicarbonateError("k_diss_mol_per_s must be finite and > 0 (ASSUMED synthetic rate)")
    if not (math.isfinite(dt) and dt > 0):
        raise SolidBicarbonateError("dt must be finite and > 0")
    si = saturation_index(system)
    if system.n_solid_mol <= 0 or si >= 1.0:
        return DissolutionResult(0.0, si >= 1.0, system.n_solid_mol <= 0, si, system,
                                 claim_tiers.weakest(_tier(system), claim_tiers.ASSUMED_PARAMETER),
                                 "no net dissolution (saturated or no solid)")
    dx = k_diss_mol_per_s * max(0.0, 1.0 - si) * dt
    dx = min(dx, system.n_solid_mol)
    # do not overshoot saturation: if dissolving dx would push SI past 1, cap at the saturation amount.
    if _si_after_dissolving(system, dx) > 1.0:
        sat = dissolve_to_saturation(system)
        return replace(sat, claim_tier=claim_tiers.weakest(sat.claim_tier, claim_tiers.ASSUMED_PARAMETER),
                       note="finite-rate step capped at the solubility limit (k_diss ASSUMED)")
    after = replace(system, n_carbon_aqueous_mol=system.n_carbon_aqueous_mol + dx,
                    n_sodium_aqueous_mol=system.n_sodium_aqueous_mol + dx,
                    n_solid_mol=max(system.n_solid_mol - dx, 0.0))
    return DissolutionResult(
        dissolved_mol=dx, saturated=False, exhausted=after.n_solid_mol <= 0,
        saturation_index_after=saturation_index(after), system_after=after,
        claim_tier=claim_tiers.weakest(_tier(after), claim_tiers.ASSUMED_PARAMETER),
        note=f"finite-rate dissolution, k_diss={k_diss_mol_per_s} mol/s ASSUMED (CALIBRATION_REQUIRED per apparatus)")
