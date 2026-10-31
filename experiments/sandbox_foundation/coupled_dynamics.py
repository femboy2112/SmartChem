"""OPERATION XIII P2 -- time-resolved CO2 gas transfer coupled to the vinegar/bicarbonate acid-base equilibrium.

The first genuine DYNAMIC capability.  A finite headspace over a liquid is NOT assumed to be in Henry equilibrium;
dissolved CO2 and headspace CO2 relax toward it through a finite-rate interfacial flux, and the acid-base chemistry
re-equilibrates (fast) at each instant.  No hard-coded fizz, no contact trigger: the source of gas is the DISSOLVED
inorganic carbon, and whether it degasses (supersaturated liquid) or dissolves (CO2-rich headspace) is decided by
the driving force, never a switch (V3_0 section 3 anti-pattern).

GOVERNING LAW (section 4A, a declared constitutive approximation):

    J_CO2 = kLa * V_liquid * (c_CO2,aq - c_CO2,eq(P_CO2))        [mol/s, liquid -> gas when positive]
    c_CO2,eq(P_CO2) = K_H * P_CO2                                 [Henry, the sourced carbonate K_H]
    P_CO2 = n_CO2,gas * R * T / V_gas                            [ideal gas]

STATE (conserved inventories; everything else is derived):
    n_C_gas   headspace CO2 (mol)
    n_C_liq   total inorganic carbon in the liquid (mol) = n_C_total - n_C_gas   (total carbon CONSERVED by
              construction: we evolve n_C_gas and set n_C_liq = n_C_total - n_C_gas, equal-and-opposite transfer)
    C_Ac, Na  fixed liquid totals (acetic acid non-volatile; only CO2 crosses the interface)
At each instant the liquid speciation (and [CO2(aq)] = c_CO2,aq) is the CLOSED coupled equilibrium at
C_C = n_C_liq / V_liq (fast acid-base equilibrium nested inside the slow gas transfer).

STEADY STATE == SEALED EQUILIBRIUM (the built-in cross-check): dn_C_gas/dt = 0 iff c_CO2,aq = K_H P_CO2 with carbon
conserved -- exactly the sealed-mode equilibrium (coupled_gas_equilibrium, mode='sealed').  So the dynamic
trajectory MUST relax to the static sealed solver's end state; `steady_state_cross_check` pins it.

kLa PROVENANCE (section 4B, three evidential levels, never conflated):
  * Level A  caller-declared positive kLa, tier ASSUMED_PARAMETER -- the usable synthetic-dynamics path (tests the
             numerics + conservation).  This is the primary path here.
  * Level B  an applicability-bounded ORDER-OF-MAGNITUDE band for a NAMED geometry class (LITERATURE_KLA_BAND).  It
             is NOT a precise calibrated value and carries tier ASSUMED_PARAMETER with CALIBRATION_REQUIRED: section
             4A forbids inventing a universal vinegar/baking-soda kLa, and a precise apparatus value requires the
             specific gas-liquid correlation, not recoverable offline here.
  * Level C  calibrated to a measured time series -- UNVERIFIED: no independent measured CO2-evolution dataset is
             recovered or fabricated.

CLAIM TIER of a trajectory = weakest(equilibrium-solve tier, kLa tier) (section 13.B): a Level-A run is capped at
ASSUMED_PARAMETER no matter how well the numerics converge.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.aqueous_equilibrium import InvalidParameterError
from experiments.sandbox_foundation.carbonate_equilibrium import KH_CO2_25C, R_GAS_L_ATM
from experiments.sandbox_foundation.coupled_gas_equilibrium import MixedGasSystem
from experiments.sandbox_foundation.coupled_gas_equilibrium import solve as gas_solve


# ------------------------------------------------------------------------------------- the transfer parameter
@dataclass(frozen=True)
class GasTransferParameter:
    """A volumetric mass-transfer coefficient kLa (1/s) WITH its evidential tier and provenance.  kLa depends on the
    physical geometry, mixing, and gas-liquid contact; this object forces the caller to state WHERE the value came
    from and how far it may be trusted, so a trajectory can never silently claim a confidence its kLa lacks."""
    kLa_per_s: float
    tier: str
    source: str
    applicability: str = ""

    def __post_init__(self):
        if not (isinstance(self.kLa_per_s, (int, float)) and math.isfinite(self.kLa_per_s) and self.kLa_per_s > 0):
            raise InvalidParameterError("kLa_per_s must be finite and > 0 (1/s)")
        claim_tiers.rank(self.tier)   # raises InvalidClaimTierError on an unknown tier
        if not self.source.strip():
            raise InvalidParameterError("a GasTransferParameter must state its source/provenance")


def assumed_kLa(kLa_per_s: float, *, note: str = "caller-declared synthetic value") -> GasTransferParameter:
    """Level A: a caller-declared kLa, explicitly ASSUMED_PARAMETER.  The honest default for synthetic dynamics."""
    return GasTransferParameter(kLa_per_s, claim_tiers.ASSUMED_PARAMETER, f"Level A (section 4B): {note}",
                                "synthetic; not tied to a measured apparatus")


# Level B: an applicability-bounded band, NOT a precise sourced value (section 4A forbids a universal value).  CO2
# volumetric mass-transfer coefficients span ~1e-4/s (quiescent surface, open beaker) to ~1e-1/s (vigorously
# aerated/stirred) across the gas-liquid-engineering literature; the geometric mean ~3e-3/s is a stirred-open-vessel
# order-of-magnitude placeholder.  Tier ASSUMED_PARAMETER + CALIBRATION_REQUIRED: for a real apparatus, fit it.
LITERATURE_KLA_BAND = GasTransferParameter(
    3e-3, claim_tiers.ASSUMED_PARAMETER,
    "Level B (section 4B): order-of-magnitude band for CO2 kLa, ~1e-4/s (quiescent open surface) to ~1e-1/s "
    "(vigorous aeration), from general gas-liquid mass-transfer engineering; CALIBRATION_REQUIRED for any specific "
    "apparatus (a precise value needs the geometry's own correlation, e.g. doi:10.1016/j.cherd.2025.04.013, not "
    "recoverable offline here -- so this is a geometry-class estimate, not a measured constant).",
    "stirred open vessel, near-ambient T/P; calibrate per apparatus (the value is a BAND midpoint, not a datum)")


# ------------------------------------------------------------------------------------- the dynamic vessel + state
@dataclass(frozen=True)
class DynamicVessel:
    """A sealed vessel (liquid + finite headspace) whose CO2 is OUT of Henry equilibrium and relaxes by finite-rate
    transfer.  Acetate/Na are fixed liquid totals; the carbon is split between dissolved (liquid) and headspace gas,
    the split evolving in time.  The initial carbon inventory is given explicitly as (dissolved, gas) moles."""
    total_acetate_M: float
    sodium_M: float
    v_liquid_L: float
    v_gas_L: float
    initial_carbon_dissolved_mol: float
    initial_carbon_gas_mol: float
    activity_model: str = "ideal"
    temperature_K: float = 298.15

    def __post_init__(self):
        for name in ("total_acetate_M", "sodium_M", "v_liquid_L", "v_gas_L",
                     "initial_carbon_dissolved_mol", "initial_carbon_gas_mol"):
            v = getattr(self, name)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise InvalidParameterError(f"{name} must be finite and >= 0")
        if self.v_liquid_L <= 0 or self.v_gas_L <= 0:
            raise InvalidParameterError("v_liquid_L and v_gas_L must be > 0")
        if self.activity_model not in ("ideal", "davies"):
            raise InvalidParameterError("activity_model must be 'ideal' or 'davies'")

    @property
    def n_carbon_total_mol(self) -> float:
        return float(self.initial_carbon_dissolved_mol + self.initial_carbon_gas_mol)


@dataclass(frozen=True)
class DynamicState:
    time_s: float
    n_carbon_liquid_mol: float
    n_carbon_gas_mol: float
    n_carbon_total_mol: float
    co2aq_M: float
    p_co2_atm: float
    pH: float
    flux_mol_per_s: float          # J_CO2, liquid -> gas (signed)
    carbon_residual_mol: float     # |(n_liq + n_gas) - n_total|; machine-zero by construction
    equilibrium_verdict: str


@dataclass(frozen=True)
class Trajectory:
    states: tuple
    kLa: GasTransferParameter
    claim_tier: str                # weakest(equilibrium tier, kLa tier)
    steady_state_flux: float
    max_carbon_residual_mol: float
    integrator: str
    note: str = ""
    caveats: tuple = field(default_factory=tuple)


# ----------------------------------------------------------------------------------- the coupled RHS + speciation
def _speciate_liquid(vessel: DynamicVessel, n_C_liq: float):
    """Closed coupled equilibrium of the liquid at the current dissolved-carbon inventory.  Returns (caq, pH, verdict)
    -- the fast acid-base equilibrium reconstructed at each instant.  n_C_liq is clamped to >= 0 (a transfer that
    would overshoot the liquid's carbon is physically a full degas, not negative carbon)."""
    C_C = max(n_C_liq, 0.0) / vessel.v_liquid_L
    r = gas_solve(MixedGasSystem(mode="closed", total_acetate_M=vessel.total_acetate_M, sodium_M=vessel.sodium_M,
                                 total_carbon_M=C_C, activity_model=vessel.activity_model,
                                 temperature_K=vessel.temperature_K))
    return r.co2aq_M, r.pH, r.verdict


def _rhs(n_C_gas: float, vessel: DynamicVessel, kLa: float, K_H: float, RT: float) -> tuple:
    """dn_C_gas/dt = J_CO2 = kLa V_liq (c_CO2,aq - K_H P_CO2).  Returns (dn_gas_dt, caq, p_co2, pH, verdict)."""
    n_C_gas = min(max(n_C_gas, 0.0), vessel.n_carbon_total_mol)   # positivity / inventory clamp
    n_C_liq = vessel.n_carbon_total_mol - n_C_gas
    caq, pH, verdict = _speciate_liquid(vessel, n_C_liq)
    p_co2 = n_C_gas * RT / vessel.v_gas_L
    c_eq = K_H * p_co2
    flux = kLa * vessel.v_liquid_L * (caq - c_eq)
    return flux, caq, p_co2, pH, verdict


def simulate(vessel: DynamicVessel, kLa: GasTransferParameter, *, duration_s: float, n_samples: int = 50,
             rtol: float = 1e-8, atol: float = 1e-14) -> Trajectory:
    """Integrate the coupled gas-transfer / acid-base dynamics with an adaptive stiff-capable RK (scipy RK45) and
    sample it at n_samples uniform times.  Total carbon is conserved by construction; positivity is enforced in the
    RHS.  The trajectory's claim tier is weakest(equilibrium-solve tier, kLa tier)."""
    if not (math.isfinite(duration_s) and duration_s > 0):
        raise InvalidParameterError("duration_s must be finite and > 0")
    if n_samples < 2:
        raise InvalidParameterError("n_samples must be >= 2")
    K_H = KH_CO2_25C.value
    RT = R_GAS_L_ATM.value * float(vessel.temperature_K)
    n_tot = vessel.n_carbon_total_mol

    def ode(_t, y):
        flux, *_ = _rhs(y[0], vessel, kLa.kLa_per_s, K_H, RT)
        return [flux]

    t_eval = np.linspace(0.0, duration_s, n_samples)
    sol = solve_ivp(ode, (0.0, duration_s), [vessel.initial_carbon_gas_mol], method="RK45",
                    t_eval=t_eval, rtol=rtol, atol=atol, max_step=duration_s / 10.0)
    if not sol.success:
        raise InvalidParameterError(f"integration failed: {sol.message}")

    states = []
    eq_tier = claim_tiers.NUMERICALLY_VERIFIED   # the equilibrium solve is cross-checked (P0); capped by kLa below
    max_resid = 0.0
    for t, n_gas in zip(sol.t, sol.y[0]):
        n_gas = min(max(float(n_gas), 0.0), n_tot)
        n_liq = n_tot - n_gas
        flux, caq, p_co2, pH, verdict = _rhs(n_gas, vessel, kLa.kLa_per_s, K_H, RT)
        resid = abs((n_liq + n_gas) - n_tot)
        max_resid = max(max_resid, resid)
        states.append(DynamicState(
            time_s=float(t), n_carbon_liquid_mol=n_liq, n_carbon_gas_mol=n_gas, n_carbon_total_mol=n_tot,
            co2aq_M=caq, p_co2_atm=p_co2, pH=pH, flux_mol_per_s=flux, carbon_residual_mol=resid,
            equilibrium_verdict=verdict))

    tier = claim_tiers.weakest(eq_tier, kLa.tier)
    caveats = ()
    if vessel.activity_model == "davies":
        caveats += ("activity pH is Davies-model-only; see the equilibrium solver's own caveats",)
    if kLa.tier == claim_tiers.ASSUMED_PARAMETER:
        caveats += ("kLa is an assumed/uncalibrated parameter (CALIBRATION_REQUIRED for a real apparatus)",)
    return Trajectory(states=tuple(states), kLa=kLa, claim_tier=tier,
                      steady_state_flux=states[-1].flux_mol_per_s, max_carbon_residual_mol=max_resid,
                      integrator="scipy.solve_ivp/RK45", caveats=caveats)


# ------------------------------------------------------------------------- independent integrator cross-check
def integrate_fixed_step(vessel: DynamicVessel, kLa: GasTransferParameter, *, duration_s: float,
                         dt: float, method: str = "backward_euler") -> list:
    """A SEPARATE, fixed-step integrator used only to cross-check `simulate` (RK45) and for timestep refinement.
    'backward_euler' is A-stable (robust for a stiff transfer) and solves its implicit step by scalar bisection on
    n_gas; 'rk4' is the explicit comparator.  Returns the (time, n_gas) samples.  No scipy adaptive machinery, so a
    bug shared with RK45's stepping would still show up as a disagreement."""
    K_H = KH_CO2_25C.value
    RT = R_GAS_L_ATM.value * float(vessel.temperature_K)
    n_tot = vessel.n_carbon_total_mol

    def f(n_gas):
        flux, *_ = _rhs(n_gas, vessel, kLa.kLa_per_s, K_H, RT)
        return flux

    n_gas = vessel.initial_carbon_gas_mol
    t = 0.0
    out = [(0.0, n_gas)]
    n_steps = max(1, int(round(duration_s / dt)))
    for _ in range(n_steps):
        if method == "rk4":
            k1 = f(n_gas)
            k2 = f(n_gas + 0.5 * dt * k1)
            k3 = f(n_gas + 0.5 * dt * k2)
            k4 = f(n_gas + dt * k3)
            n_gas = n_gas + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        else:  # backward_euler: solve g(x) = x - n_gas - dt f(x) = 0 by bisection on [0, n_tot]
            from scipy.optimize import brentq
            g = lambda x: x - n_gas - dt * f(x)  # noqa: E731
            glo, ghi = g(0.0), g(n_tot)
            n_gas = brentq(g, 0.0, n_tot) if (glo <= 0 <= ghi or ghi <= 0 <= glo) else n_gas + dt * f(n_gas)
        n_gas = min(max(n_gas, 0.0), n_tot)
        t += dt
        out.append((t, n_gas))
    return out


def steady_state_cross_check(vessel: DynamicVessel, kLa: GasTransferParameter, *, duration_s: float) -> dict:
    """Integrate to (near) steady state and compare the end state to the STATIC sealed-mode equilibrium -- an
    independent verification that the dynamics relax to the right fixed point (dn/dt=0 <=> Henry equilibrium <=>
    the sealed equilibrium with carbon conserved).  Returns the two end states and the pH/split agreement."""
    traj = simulate(vessel, kLa, duration_s=duration_s, n_samples=3)
    end = traj.states[-1]
    sealed = gas_solve(MixedGasSystem(
        mode="sealed", total_acetate_M=vessel.total_acetate_M, sodium_M=vessel.sodium_M,
        total_carbon_mol=vessel.n_carbon_total_mol, v_liquid_L=vessel.v_liquid_L, v_gas_L=vessel.v_gas_L,
        activity_model=vessel.activity_model, temperature_K=vessel.temperature_K))
    return {
        "dynamic_pH": end.pH, "sealed_pH": sealed.pH, "delta_pH": abs(end.pH - sealed.pH),
        "dynamic_n_gas": end.n_carbon_gas_mol, "sealed_n_gas": sealed.gas_carbon_mol,
        "delta_n_gas": abs(end.n_carbon_gas_mol - sealed.gas_carbon_mol),
        "residual_flux": end.flux_mol_per_s,
    }
