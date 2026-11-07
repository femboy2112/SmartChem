"""OPERATION XVIII §5 -- THE UNIFIED VINEGAR / BICARBONATE WORLD.

ONE evolving simulation that composes liquid acid-base equilibrium, solid dissolution, gas-liquid (Henry) transfer,
inter-cell transport and an external CO2 boundary through the SINGLE generic operator-split integrator
(general_coupled.CoupledWorld) -- not three unrelated demos packaged together.  The headline architectural gate: the
integrator holds NO chemistry.  Every chemistry-specific law lives in a typed declaration:

  * fast acid-base + carbonate speciation  -> MixedAcetateCarbonateEquilibriumOperator (a fast-equilibrium projection P
    on each liquid cell; CO2(aq) is a LIQUID species here);
  * solid NaHCO3 dissolution                -> a KERNEL REACTION  NaHCO3(s) -> Na+ + HCO3-  with a declared finite-rate
    law r = k_diss * max(0, 1 - SI), SI = [Na+][HCO3-]/Qsp (the solid is a TABLE-FREE species the projection never
    touches; only its dissolved products re-speciate);
  * gas-liquid CO2 exchange                 -> a Henry InterfaceTransfer (B-liquid <-> gas) with partition = K_H*R*T,
    k_transfer = kLa*V_liq;
  * inter-cell acid transport (the valve)   -> a SELECTIVE membrane passing only the NEUTRAL carriers HAc and CO2(aq)
    (charge-safe: no ionic transfer, so global charge is not laundered); valve open/closed is a phase-level command
    (we integrate the world WITH or WITHOUT the valve interface and stitch states -- the generic integrator carries no
    time-varying coefficients and no valve logic);
  * open/sealed vessel                      -> an optional fixed-activity CO2 export boundary on the gas, whose flux is
    INDEPENDENTLY ledgered (XVIII-3): exported carbon is accounted, never hidden.

THE GAS EMERGES FROM EQUILIBRIUM + TRANSPORT, the pH shift from the coupled acid/base system, the material balances
from the conserved-component state and the signed boundary ledger -- there is no `if vinegar` and no
`if baking_soda: produce_CO2()` anywhere.

CRITICAL SCIENTIFIC LIMITATIONS (stated, never papered over):
  * the NaHCO3 saturation proxy is an EMPIRICAL concentration product Qsp = S^2, not an activity-based phase
    equilibrium (OPERATION XIV P0-1B); it is defensible only in the dilute regime.
  * k_diss (dissolution), kLa (gas transfer) and k_export are ASSUMED/synthetic coefficients, NOT calibrated to any
    apparatus -- so this is a genuine numerical SIMULATION, not a predictor of real fizzing RATES.  No bubble
    nucleation, bubble size or foam dynamics is modelled (those would be fabrication).
  * fast equilibrium is applied as a once-per-macro-step SNIA projection (first order); dissolution SI is evaluated on
    the pre-projection aqueous composition, a first-order lag.  The dynamical tier is capped at the weakest premise.

CLI:  python -m experiments.sandbox_foundation.unified_chemical_world [--scenario NAME] [--json OUT] [--csv OUT]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from dataclasses import dataclass

from experiments.sandbox_foundation.aqueous_equilibrium import (
    SOURCE_T_K,
    SOURCE_T_TOL_K,
    OutOfSourceDomainError,
)
from experiments.sandbox_foundation.carbonate_equilibrium import KH_CO2_25C, R_GAS_L_ATM
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER, weakest
from experiments.sandbox_foundation.coupled_equilibrium import (   # the 25 C K-set the mixed operator defaults to
    KA_ACETIC_25C,
    K1_CARBONIC_25C,
    K2_CARBONIC_25C,
    KW_25C,
)
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
    ElectroneutralBulkExchange,   # XXII-5: the completeness-gated whole-solution bulk-exchange mode
    EquilibriumCoupling,
    ExternalBoundary,
    InterfaceTransfer,
    _canon_num,          # XIX-1A: lossless float.hex() identity encoding (one source of truth with the world cert)
    _species_key,        # XIX-1A: full species identity key (name/phase/charge/composition/substance)
)
from experiments.sandbox_foundation.general_equilibrium import MixedAcetateCarbonateEquilibriumOperator
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    Phase,
    RateLaw,
    Reaction,
    Species,
    _seal_audited_builtin,
)
from experiments.sandbox_foundation.solid_bicarbonate import KSP_NAHCO3_25C

# the implicit-solvent reservoir components for an aqueous liquid cell (the acetate/carbonate operators set H/O/charge
# against the implicit water + electroneutrality -- so they are reported, not independently conserved; XVIII-3 demotes
# the charge claim rather than silently exempting it).
_WATER_RESERVOIR = frozenset({"H", "O", "charge"})


# ============================================================ the declared chemistry (typed, not in the integrator)
class BicarbonateDissolutionRate(RateLaw):
    """Finite-rate solid dissolution r_vol = k_diss * max(0, 1 - SI) (mol L^-1 s^-1), SI = [Na+][HCO3-]/Qsp.  A
    DISSOLUTION-ONLY law (no precipitation term): it fires only while undersaturated (SI < 1) AND solid remains; once
    the solid is exhausted (n_solid <= 0) the rate is 0.  k_diss and Qsp are ASSUMED/empirical (tier ASSUMED_PARAMETER,
    CALIBRATION_REQUIRED) -- this sets a dissolution TIMESCALE, it does not predict a real dissolution rate."""
    tier = ASSUMED_PARAMETER

    def __init__(self, *, k_diss: float, Qsp: float, solid: Species, na: Species, hco3: Species):
        if not (math.isfinite(k_diss) and k_diss > 0):
            raise ValueError("k_diss must be finite and > 0 (ASSUMED synthetic rate)")
        if not (math.isfinite(Qsp) and Qsp > 0):
            raise ValueError("Qsp must be finite and > 0")
        self.k_diss = float(k_diss)
        self.Qsp = float(Qsp)
        self.solid = solid
        self.na = na
        self.hco3 = hco3
        self.source = "k_diss ASSUMED synthetic (CALIBRATION_REQUIRED per apparatus); Qsp = empirical S^2 (not an activity Ksp)"

    def evaluate(self, reaction, concentrations):
        if concentrations[self.solid] <= 0.0:           # solid exhausted -> no dissolution (fail-closed on the phase)
            return 0.0
        si = (concentrations[self.na] * concentrations[self.hco3]) / self.Qsp
        return self.k_diss * max(0.0, 1.0 - si)          # undersaturated only; never precipitates

    def descriptor(self):
        # XX-2B: bind every operative parameter (k_diss, Qsp) AND the species the RHS reads (solid/Na+/HCO3-),
        # so a post-construction mutation of any of them moves the world certificate (general_coupled XIX-1D).
        return ("BicarbonateDissolutionRate", _canon_num(self.k_diss), _canon_num(self.Qsp),
                _species_key(self.solid), _species_key(self.na), _species_key(self.hco3),
                self.tier, self.source)


# XXII-2 / XXIII-2: BicarbonateDissolutionRate is an AUDITED built-in.  It is mutable (not a frozen dataclass), but its
# descriptor() FAITHFULLY binds every operative parameter (k_diss, Qsp, and the solid/Na+/HCO3- species the RHS
# reads), so the general_coupled XIX-1D cert-recompute catches any post-construction mutation of those parameters.
# XXIII-2: the audit is the source pin in general_kernel's CLOSED table; sealing checks it (fail-closed on mismatch).
_seal_audited_builtin(BicarbonateDissolutionRate)


@dataclass(frozen=True)
class _Species:
    """The shared species objects of the unified world (built once; the same objects populate both liquid cells, so a
    valve interface moves ONE substance between (cellA, sp) and (cellB, sp) slots)."""
    HAc: Species
    Ac: Species
    CO2aq: Species
    HCO3: Species
    CO3: Species
    Hp: Species
    OHm: Species
    Nap: Species
    CO2g: Species
    solid: Species


def _build_species() -> _Species:
    return _Species(
        HAc=Species.of("HAc", {"C": 2, "H": 4, "O": 2}, 0, Phase.AQUEOUS, substance="HAc"),
        Ac=Species.of("Ac-", {"C": 2, "H": 3, "O": 2}, -1, Phase.AQUEOUS, substance="Ac-"),
        CO2aq=Species.of("CO2(aq)", {"C": 1, "O": 2}, 0, Phase.AQUEOUS, substance="CO2"),
        HCO3=Species.of("HCO3-", {"C": 1, "H": 1, "O": 3}, -1, Phase.AQUEOUS, substance="HCO3-"),
        CO3=Species.of("CO3-2", {"C": 1, "O": 3}, -2, Phase.AQUEOUS, substance="CO3-2"),
        Hp=Species.of("H+", {"H": 1}, 1, Phase.AQUEOUS, substance="H+"),
        OHm=Species.of("OH-", {"H": 1, "O": 1}, -1, Phase.AQUEOUS, substance="OH-"),
        Nap=Species.of("Na+", {"Na": 1}, 1, Phase.AQUEOUS, substance="Na+"),
        CO2g=Species.of("CO2(g)", {"C": 1, "O": 2}, 0, Phase.GAS, substance="CO2"),       # same substance as CO2(aq)
        solid=Species.of("NaHCO3(s)", {"Na": 1, "H": 1, "C": 1, "O": 3}, 0, Phase.SOLID, substance="NaHCO3"),
    )


def _liquid_species_table(sp: _Species) -> dict:
    """Map the mixed operator's species NAMES to the kernel Species objects a liquid cell tracks (XVI-P0.2 faithful)."""
    return {"HAc": sp.HAc, "Ac-": sp.Ac, "CO2(aq)": sp.CO2aq, "HCO3-": sp.HCO3, "CO3-2": sp.CO3,
            "H+": sp.Hp, "OH-": sp.OHm, "Na+": sp.Nap}


# ============================================================ world configuration
@dataclass(frozen=True)
class UnifiedParams:
    """All physical parameters of the unified world (every coefficient tagged ASSUMED where it is not sourced)."""
    V_A_L: float = 1.0           # acid cell volume
    V_B_L: float = 1.0           # bicarbonate cell volume
    V_gas_L: float = 1.0         # headspace volume
    temperature_K: float = 298.15
    k_valve_Lps: float = 0.2     # selective-membrane transfer coefficient (ASSUMED)
    kLa_per_s: float = 0.05      # gas-liquid transfer coefficient (ASSUMED)
    k_diss_molpLps: float = 0.05  # solid dissolution rate coefficient (ASSUMED)
    k_export_Lps: float = 0.05   # open-vessel CO2 export coefficient (ASSUMED)
    activity_model: str = "davies"


@dataclass(frozen=True)
class _Build:
    world: CoupledWorld
    sp: _Species


#: XXII-5: the complete dissolved (aqueous) roster both liquid cells share -- the bulk parcel carries exactly this set.
_AQUEOUS_ORDER = ("HAc", "Ac", "CO2aq", "HCO3", "CO3", "Hp", "OHm", "Nap")


def _resolve_transport_mode(transport_mode, valve_open) -> str:
    """Back-compatible resolution: an explicit ``transport_mode`` wins; otherwise the legacy ``valve_open`` bool maps to
    the selective MEMBRANE (open) or CLOSED (shut).  XXII-5 adds BULK as a third interchangeable declaration."""
    if transport_mode is None:
        return "membrane" if valve_open else "closed"
    if transport_mode not in ("closed", "membrane", "bulk"):
        raise ValueError(f"transport_mode must be 'closed' | 'membrane' | 'bulk' (got {transport_mode!r})")
    return transport_mode


def build_unified_world(params: UnifiedParams, sp: _Species, *, valve_open: bool = False, sealed: bool,
                        transport_mode: str | None = None) -> _Build:
    """Assemble the two-liquid-cell + gas-headspace CoupledWorld for one phase.  The inter-chamber mechanism is ONE of
    three interchangeable physical declarations (XXII-5) -- the generic integrator is reused verbatim; only WHICH
    interfaces / bulk-exchanges are present changes:

      * "closed"   -- no A<->B transport (valve shut).
      * "membrane" -- a SELECTIVE membrane: InterfaceTransfer of the NEUTRAL carriers HAc and CO2(aq) only (charge-safe;
                      ions cannot cross, so the Na+ gradient never relaxes).  (legacy ``valve_open=True``.)
      * "bulk"     -- an ElectroneutralBulkExchange swapping equal LIQUID PARCELS carrying the COMPLETE dissolved roster
                      (all 8 aqueous species at one Q), so Na / total acetate / total inorganic carbon ALL relax toward
                      a common well-mixed composition and no cell is left charged (XXII-1 completeness-gated).

    The Henry gas-liquid CO2 transfer (B<->gas) and the optional open-vessel CO2 export are independent of the A<->B
    mechanism and present in every mode."""
    mode = _resolve_transport_mode(transport_mode, valve_open)
    op = MixedAcetateCarbonateEquilibriumOperator(activity_model=params.activity_model)
    table = _liquid_species_table(sp)
    aqueous = (sp.HAc, sp.Ac, sp.CO2aq, sp.HCO3, sp.CO3, sp.Hp, sp.OHm, sp.Nap)

    cell_a = Compartment(
        "A", ChemicalSystem(list(aqueous), [], volume_L=params.V_A_L),
        equilibrium=EquilibriumCoupling(op, table, reservoir_components=_WATER_RESERVOIR))

    dissolution = Reaction(
        "NaHCO3(s)->Na+ + HCO3-", ((sp.solid, -1), (sp.Nap, 1), (sp.HCO3, 1)),
        BicarbonateDissolutionRate(k_diss=params.k_diss_molpLps, Qsp=KSP_NAHCO3_25C.value,
                                   solid=sp.solid, na=sp.Nap, hco3=sp.HCO3),
        elementary=False)
    cell_b = Compartment(
        "B", ChemicalSystem([*aqueous, sp.solid], [dissolution], volume_L=params.V_B_L),
        equilibrium=EquilibriumCoupling(op, table, reservoir_components=_WATER_RESERVOIR))

    gas = Compartment("gas", ChemicalSystem([sp.CO2g], [], volume_L=params.V_gas_L))   # passive CO2 reservoir

    RT = R_GAS_L_ATM.value * params.temperature_K
    henry = InterfaceTransfer("henry_B_gas", "B", "gas", sp.CO2aq, sp.CO2g,
                              k_transfer=params.kLa_per_s * params.V_B_L, partition=KH_CO2_25C.value * RT)
    interfaces = [henry]
    bulk_exchanges = ()
    if mode == "membrane":
        # selective membrane: only neutral HAc and CO2(aq) cross (charge-safe), A <-> B
        interfaces.append(InterfaceTransfer("valve_HAc", "A", "B", sp.HAc, sp.HAc, k_transfer=params.k_valve_Lps))
        interfaces.append(InterfaceTransfer("valve_CO2", "A", "B", sp.CO2aq, sp.CO2aq, k_transfer=params.k_valve_Lps))
    elif mode == "bulk":
        # bulk-liquid exchange: the COMPLETE dissolved roster advects at one Q (XXII-1 completeness-gated, charge-safe)
        bulk_exchanges = (ElectroneutralBulkExchange(
            "bulk_mix", "A", "B", species_pairs=tuple((s, s) for s in aqueous),
            Q_L_per_s=params.k_valve_Lps),)

    boundaries = []
    if not sealed:
        boundaries.append(ExternalBoundary("co2_export", "gas", sp.CO2g, "fixed_activity",
                                           k_transfer=params.k_export_Lps, target_conc=0.0))
    return _Build(CoupledWorld([cell_a, cell_b, gas], interfaces=interfaces, boundaries=boundaries,
                               bulk_exchanges=bulk_exchanges,
                               temperature_K=params.temperature_K), sp)   # XIX-1C: ONE temperature, no 298.15 hard-code


# ============================================================ initial state + the phase-driven simulation
def initial_state(sp: _Species, *, acid_mol: float, bicarb_solid_mol: float,
                  bicarb_dissolved_mol: float = 0.0) -> dict:
    """A clean initial inventory: acetic acid in cell A; dissolved + solid NaHCO3 in cell B; empty gas.  Dissolved
    NaHCO3 is entered as HCO3- + Na+ (electroneutral); the fast-equilibrium projection re-speciates it on step 0."""
    return {
        "A": {sp.HAc: acid_mol},
        "B": {sp.HCO3: bicarb_dissolved_mol, sp.Nap: bicarb_dissolved_mol, sp.solid: bicarb_solid_mol},
        "gas": {sp.CO2g: 0.0},
    }


@dataclass(frozen=True)
class Phase_:
    name: str
    valve_open: bool
    sealed: bool
    duration_s: float
    n_steps: int


def _ph_of_cell(frame: dict, sp: _Species, cell: str, volume_L: float):
    """CONCENTRATION pH = -log10([H+]), [H+] = n(H+)/V.  Kept ONLY as an internal cross-check against the solver's own
    pH_concentration (XIX-1B); it is NOT the value the frame reports.  The AUTHORITATIVE pH comes from the equilibrium
    solver's activity model (captured in the trajectory's equilibrium_derived), never recomputed in the renderer."""
    h = frame[cell].get(sp.Hp, 0.0)
    c = h / volume_L
    return -math.log10(c) if c > 0 else None


def _finite(x):
    return float(x) if (isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)) else None


# XIX-1E: the phase-stitch clamp is a MEASURED, BOUNDED roundoff correction, not a silent clip.  A phase-final negative
# within this scale-aware budget is numerical dust (clamped to 0 and its magnitude logged); a larger negative is a REAL
# positivity excursion and is REFUSED, never clipped away and reported as a clean state.
_STITCH_ATOL = 1e-12
_STITCH_RTOL = 1e-9

# XIX-1A: the solver configuration the flagship integrates with -- bound into the RUN identity so it can never drift
# from what simulate() actually passes to CoupledWorld.integrate.
_SCHEME = "strang"
_RTOL = 1e-10
_ATOL = 1e-14


def _require_params(params: UnifiedParams) -> None:
    """XIX-1E: refuse a physically invalid world configuration up front; XIX-1C: refuse an off-25 C temperature -- the
    acid/carbonate K-set, the CO2 Henry constant AND the empirical NaHCO3 Qsp are ALL sourced only at 25 C."""
    for name in ("V_A_L", "V_B_L", "V_gas_L"):
        v = getattr(params, name)
        if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
            raise ValueError(f"UnifiedParams.{name} must be a finite volume > 0 (got {v!r})")
    for name in ("k_valve_Lps", "kLa_per_s", "k_diss_molpLps", "k_export_Lps"):
        v = getattr(params, name)
        if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
            raise ValueError(f"UnifiedParams.{name} must be a finite coefficient >= 0 (got {v!r})")
    T = params.temperature_K
    if isinstance(T, bool) or not (isinstance(T, (int, float)) and math.isfinite(T) and T > 0):
        raise ValueError(f"UnifiedParams.temperature_K must be a finite temperature > 0 (got {T!r})")
    if abs(float(T) - SOURCE_T_K) > SOURCE_T_TOL_K:
        raise OutOfSourceDomainError(
            f"temperature {T} K is outside the 25 C sourced-data domain {SOURCE_T_K} +/- {SOURCE_T_TOL_K} K; the "
            f"acid/carbonate Ka/K1/K2/Kw, the CO2 Henry constant and the empirical NaHCO3 Qsp are ALL tabulated at "
            f"25 C only -- an off-domain temperature is refused rather than run as a mixed-temperature simulation "
            f"(scaling Henry's law while pinning Ka/K1/K2/Kw at 25 C).  Extending beyond 25 C needs a sourced "
            f"temperature dependence threaded through every constant (XIX-1C).")


def _require_phases(phases) -> tuple:
    """XIX-1E: a non-empty schedule of well-formed phases (duration > 0, integer n_steps >= 1)."""
    if not isinstance(phases, (tuple, list)) or len(phases) == 0:
        raise ValueError("phases must be a non-empty sequence of Phase_")
    for p in phases:
        if type(p) is not Phase_:
            raise ValueError(f"every phase must be a Phase_ (got {type(p).__name__})")
        if isinstance(p.duration_s, bool) or not (isinstance(p.duration_s, (int, float))
                                                  and math.isfinite(p.duration_s) and p.duration_s > 0):
            raise ValueError(f"phase {p.name!r} duration_s must be finite and > 0 (got {p.duration_s!r})")
        if isinstance(p.n_steps, bool) or not (isinstance(p.n_steps, int) and p.n_steps >= 1):
            raise ValueError(f"phase {p.name!r} n_steps must be an int >= 1 (got {p.n_steps!r})")
    return tuple(phases)


def _require_inventories(acid_mol, bicarb_solid_mol, bicarb_dissolved_mol) -> None:
    """XIX-1E: initial inventories must be finite and >= 0 (the kernel refuses negatives/NaN too, but a clear flagship
    message beats a deep traceback)."""
    for name, v in (("acid_mol", acid_mol), ("bicarb_solid_mol", bicarb_solid_mol),
                    ("bicarb_dissolved_mol", bicarb_dissolved_mol)):
        if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
            raise ValueError(f"{name} must be a finite mol value >= 0 (got {v!r})")


def _component_totals(amounts_by_comp: dict) -> dict:
    """XX-4: the global element/charge inventory of a state {compartment: {species: mol}}, summed over every compartment
    from each species' exact composition -- the same E @ n the per-phase ledger uses, computed here at the flagship
    level so the whole-run balance can be closed explicitly."""
    tot: dict = {}
    for inv in amounts_by_comp.values():
        for s, v in inv.items():
            fv = float(v)
            for el, cnt in s.composition:
                tot[el] = tot.get(el, 0.0) + fv * cnt
            tot["charge"] = tot.get("charge", 0.0) + fv * float(s.charge)
    return tot


def _restitch(final_amounts: dict, vols: dict):
    """XIX-1E / XX-4: re-pack a phase's final amounts as the next phase's initial inventory.  Each negative amount is a
    BOUNDED roundoff correction: within a scale-aware budget it is clamped to 0 and recorded as an EXPLICIT numerical-
    adjustment EVENT; a negative beyond the budget is a REAL positivity excursion returned as a violation (the caller
    raises -- never clipped away silently).  Clamping a negative UP to 0 ADDS matter, so each event carries the signed
    amount AND its per-element/charge impact (XX-4) -- a numerical adjustment is a distinct ledger category, never
    disguised as chemistry or as physical boundary flux.  Returns (clean_state, clamp_total_mol, clamp_max_mol,
    violations, adjustment_events)."""
    clean, clamp_total, clamp_max, violations, events = {}, 0.0, 0.0, [], []
    for c, inv in final_amounts.items():
        scale = max([0.0] + [abs(float(v)) for v in inv.values()])
        budget = _STITCH_ATOL + _STITCH_RTOL * scale
        cc = {}
        for s, v in inv.items():
            fv = float(v)
            if fv < 0.0:
                mag = -fv                                   # matter ADDED by clamping this negative up to 0
                clamp_total += mag
                clamp_max = max(clamp_max, mag)
                if mag > budget:
                    violations.append((c, getattr(s, "name", str(s)), fv, budget))
                else:
                    events.append({
                        "compartment": c,
                        "species": getattr(s, "name", str(s)),
                        "added_mol": mag,                   # signed: positive == created to reach 0
                        "element_impact": {el: mag * cnt for el, cnt in s.composition},
                        "charge_impact": mag * float(s.charge),
                        "budget": budget,
                        "reason": "positivity roundoff clamp: a negative inventory within the scale-aware stitch "
                                  "budget was set to 0 -- a numerical adjustment, NOT chemistry or boundary flux",
                    })
                cc[s] = 0.0
            else:
                cc[s] = fv
        clean[c] = cc
    return clean, clamp_total, clamp_max, violations, events


# ============================================================ XIX-1A model / run / evidence identity
def model_identity(params: UnifiedParams, phases: tuple) -> dict:
    """XIX-1A MODEL identity: the physical model, independent of initial inventories.  Binds the FULL species identity
    keys, the dissolution reaction + its rate-law parameters, the equilibrium operator + its 25 C K-set (Ka/K1/K2/Kw),
    the Henry/gas constants, every operative parameter, and the phase TOPOLOGY (which interfaces/boundaries are live).
    Lossless float.hex() encoding.  The XVIII digest bound neither the inventories nor the K-set; this does."""
    sp = _build_species()
    species = sorted(_species_key(s) for s in sp.__dict__.values())
    dissolution = {
        "name": "NaHCO3(s)->Na+ + HCO3-",
        "stoich": sorted([[list(_species_key(sp.solid)), -1], [list(_species_key(sp.Nap)), 1],
                          [list(_species_key(sp.HCO3)), 1]]),
        "rate_law": {"type": "BicarbonateDissolutionRate", "k_diss": _canon_num(params.k_diss_molpLps),
                     "Qsp": _canon_num(KSP_NAHCO3_25C.value)},
    }
    return {
        "identity_version": "xix-1",
        "species": [list(k) for k in species],
        "reactions": [dissolution],
        "equilibrium_operator": {
            "type": "MixedAcetateCarbonateEquilibriumOperator",
            "activity_model": params.activity_model,
            "K_set": {"Ka": _canon_num(KA_ACETIC_25C.value), "K1": _canon_num(K1_CARBONIC_25C.value),
                      "K2": _canon_num(K2_CARBONIC_25C.value), "Kw": _canon_num(KW_25C.value)},
        },
        "constants": {"KH_CO2_25C": _canon_num(KH_CO2_25C.value), "R_GAS_L_ATM": _canon_num(R_GAS_L_ATM.value),
                      "Qsp_NaHCO3": _canon_num(KSP_NAHCO3_25C.value)},
        "params": {k: (_canon_num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                   for k, v in params.__dict__.items()},
        "phase_topology": [[p.name, bool(p.valve_open), bool(p.sealed)] for p in phases],
    }


def run_identity(params: UnifiedParams, phases: tuple, *, acid_mol: float, bicarb_solid_mol: float,
                 bicarb_dissolved_mol: float, n_samples, scheme: str, rtol: float, atol: float) -> dict:
    """XIX-1A RUN identity: the MODEL identity PLUS everything defining the specific initial-value problem -- the
    initial inventories (the XVIII collision), the full temporal schedule (durations + step counts), the sample
    cadence and the solver config.  Two runs differing in ANY operative input get distinct run digests."""
    return {
        "model": model_identity(params, phases),
        "initial_inventories": {"acid_mol": _canon_num(acid_mol), "bicarb_solid_mol": _canon_num(bicarb_solid_mol),
                                "bicarb_dissolved_mol": _canon_num(bicarb_dissolved_mol)},
        "schedule": [[p.name, _canon_num(p.duration_s), int(p.n_steps)] for p in phases],
        "solver": {"scheme": scheme, "rtol": _canon_num(rtol), "atol": _canon_num(atol),
                   "n_samples": (int(n_samples) if n_samples is not None else None)},
    }


def evidence_identity(params: UnifiedParams) -> dict:
    """XIX-1A EVIDENCE identity: the model's SOURCE/scope provenance, separate from its physical identity.  A change in
    evidence (a calibration, a re-sourced constant) moves THIS digest without touching the model identity, and vice
    versa.  No caller-provided tier mints authority -- this records what is sourced vs assumed vs unvalidated."""
    return {
        "scope": "25 C aqueous, dilute-to-moderate ionic strength; Davies activity; closed-liquid speciation",
        "parameter_tiers": {
            "k_diss": "ASSUMED_PARAMETER (synthetic dissolution timescale; CALIBRATION_REQUIRED per apparatus)",
            "kLa": "ASSUMED_PARAMETER (synthetic gas-transfer coefficient)",
            "k_export": "ASSUMED_PARAMETER (synthetic open-vessel export coefficient)",
            "Qsp_NaHCO3": "EMPIRICAL concentration product S^2 (NOT an activity Ksp); dilute-regime only",
            "KH_CO2_25C": "SOURCED (Henry constant, 25 C)",
            "K_set(Ka,K1,K2,Kw)": "SOURCED (25 C; Harned-lineage, shared with PHREEQC -- common-mode)",
        },
        "external_validation": "BENCHMARKED_AGAINST_REFERENCE_SOLVER (PHREEQC, common-mode on constants); no "
                               "independent MEASURED validation wired in (candidate rung: NIST SRM 191d carbonate pH "
                               "10.014 +/- 0.010 at 25 C -- not yet calibrated against)",
        "activity_model": params.activity_model,
    }


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# Back-compat aliases: the old world_identity/world_identity_digest signature (params, phases) is preserved as the
# MODEL identity (a pure function of params+phases, as before -- but now richer and collision-resistant).
def world_identity(params: UnifiedParams, phases: tuple) -> dict:
    return model_identity(params, phases)


def world_identity_digest(params: UnifiedParams, phases: tuple) -> str:
    return _digest(model_identity(params, phases))


def simulate(params: UnifiedParams, phases: tuple, *, acid_mol: float, bicarb_solid_mol: float,
             bicarb_dissolved_mol: float = 0.0, n_samples: int | None = None) -> dict:
    """Run the phase schedule through ONE unified world, stitching the end state of each phase into the next.  Every
    phase's conservation + signed-flux ledger is MEASURED (XVIII-3); the whole-run external flux is the sum over
    phases.  Returns a strict-JSON-able result."""
    sp = _build_species()
    # XIX-1E: fail-closed input validation (clear messages) + XIX-1C off-25 C refusal, BEFORE any integration.
    _require_params(params)
    phases = _require_phases(phases)
    _require_inventories(acid_mol, bicarb_solid_mol, bicarb_dissolved_mol)

    state = initial_state(sp, acid_mol=acid_mol, bicarb_solid_mol=bicarb_solid_mol,
                          bicarb_dissolved_mol=bicarb_dissolved_mol)
    vols = {"A": params.V_A_L, "B": params.V_B_L, "gas": params.V_gas_L}

    run_initial_totals = _component_totals(state)      # XX-4: the TRUE initial global inventory (before any phase)
    t0 = 0.0
    frames = []
    phase_reports = []
    combined_external = {}
    combined_raw = {}
    worst_residual = 0.0
    tiers = []
    all_closed = True
    all_positive = True
    stitch_total_run = 0.0
    stitch_max_run = 0.0
    numerical_adjustments = []          # XX-4: explicit per-species roundoff-clamp events over the whole run
    numerical_adjustment_total = {}     # XX-4: per-component (element/charge) matter ADDED by clamping, summed
    run_reservoir = frozenset()         # XX-4: implicit-solvent reservoir components (captured from the world)
    max_phase_tol = 0.0                 # XX-4: the loosest per-phase material tolerance (for the whole-run gate)
    for ph in phases:
        build = build_unified_world(params, sp, valve_open=ph.valve_open, sealed=ph.sealed)
        traj = build.world.integrate(state, duration=ph.duration_s, n_steps=ph.n_steps, scheme=_SCHEME,
                                     rtol=_RTOL, atol=_ATOL, n_samples=n_samples)
        rc = traj.receipt
        der = traj.equilibrium_derived      # XIX-1B: the solver's AUTHORITATIVE per-cell pH/ionic strength, per sample
        dA_series, dB_series = der.get("A", ()), der.get("B", ())
        # frames (time-shifted onto the global clock)
        for j, t in enumerate(traj.times):
            fr = {c: traj.amounts[c][j] for c in traj.compartments}
            dA = dA_series[j] if j < len(dA_series) else {}
            dB = dB_series[j] if j < len(dB_series) else {}
            frames.append({
                "time_s": _finite(t0 + t), "phase": ph.name,
                # XIX-1B: primary pH = the solver's CHOSEN convention (its activity model); both conventions are
                # emitted explicitly so the reported value can never be read as the wrong one.
                "pH_A": _finite(dA.get("pH")), "pH_B": _finite(dB.get("pH")),
                "pH_A_activity": _finite(dA.get("pH_activity")), "pH_B_activity": _finite(dB.get("pH_activity")),
                "pH_A_concentration": _finite(dA.get("pH_concentration")),
                "pH_B_concentration": _finite(dB.get("pH_concentration")),
                "ionic_strength_A_M": _finite(dA.get("ionic_strength_M")),
                "ionic_strength_B_M": _finite(dB.get("ionic_strength_M")),
                "activity_model": dA.get("activity_model") or dB.get("activity_model"),
                "temperature_K": _finite(params.temperature_K),
                "solid_NaHCO3_mol": _finite(fr["B"].get(sp.solid, 0.0)),
                "CO2aq_B_mol": _finite(fr["B"].get(sp.CO2aq, 0.0)),
                "CO2_gas_mol": _finite(fr["gas"].get(sp.CO2g, 0.0)),
                "p_CO2_atm": _finite(fr["gas"].get(sp.CO2g, 0.0) / params.V_gas_L * R_GAS_L_ATM.value
                                     * params.temperature_K),
                "HAc_A_mol": _finite(fr["A"].get(sp.HAc, 0.0)), "HAc_B_mol": _finite(fr["B"].get(sp.HAc, 0.0)),
            })
        # XIX-1E: stitch the phase's final state into the next phase, recording the bounded roundoff clamp and
        # REFUSING any clamp beyond the scale-aware dust budget (a real positivity excursion, never clipped silently).
        last = {c: traj.amounts[c][-1] for c in traj.compartments}
        state, clamp_total, clamp_max, violations, adj_events = _restitch(last, vols)
        if violations:
            w = min(violations, key=lambda v: v[2])     # most negative
            raise ValueError(
                f"phase {ph.name!r} ended with a negative inventory beyond the roundoff budget -- a REAL positivity "
                f"excursion, not dust: compartment {w[0]!r} species {w[1]!r} = {w[2]:.3e} mol (budget {w[3]:.3e} "
                f"mol).  Refusing to clip it away and report a clean state (XIX-1E).")
        stitch_total_run += clamp_total
        stitch_max_run = max(stitch_max_run, clamp_max)
        if run_reservoir == frozenset():
            run_reservoir = frozenset(build.world.reservoir_components)
        max_phase_tol = max(max_phase_tol, float(rc.tolerance))
        # XX-4: each roundoff clamp is an explicit numerical-adjustment EVENT in the whole-run ledger -- time-stamped at
        # the phase boundary where it was applied, kept a DISTINCT category from external_flux (never disguised as
        # boundary flux), carrying the per-element/charge matter it added (which feeds the whole-run balance below).
        t_boundary = _finite(t0 + ph.duration_s)
        phase_events = []
        for ev in adj_events:
            pub = {"phase": ph.name, "time_s": t_boundary, "compartment": ev["compartment"], "species": ev["species"],
                   "added_mol": _finite(ev["added_mol"]), "charge_impact": _finite(ev["charge_impact"]),
                   "element_impact": {k: _finite(v) for k, v in ev["element_impact"].items()},
                   "budget": _finite(ev["budget"]), "reason": ev["reason"]}
            phase_events.append(pub)
            numerical_adjustments.append(pub)
            for el, d in ev["element_impact"].items():
                numerical_adjustment_total[el] = numerical_adjustment_total.get(el, 0.0) + d
            numerical_adjustment_total["charge"] = numerical_adjustment_total.get("charge", 0.0) + ev["charge_impact"]
        for comp, v in rc.external_flux.items():
            combined_external[comp] = combined_external.get(comp, 0.0) + v
        for comp, v in rc.raw_material_change.items():
            combined_raw[comp] = combined_raw.get(comp, 0.0) + v
        # the material-balance residual is over the CHECKED (non-implicit-reservoir) components only -- the implicit
        # water reservoir legitimately exchanges H/O/charge, so those residuals are reported, not a conservation fault.
        checked = [v for k, v in rc.ledger_adjusted_residual.items() if k not in rc.reservoir_exchange]
        worst_residual = max(worst_residual, max([0.0] + checked))
        tiers.append(rc.admitted_tier)
        all_closed = all_closed and rc.material_balance_closed
        all_positive = all_positive and rc.positivity_held
        phase_reports.append({
            "phase": ph.name, "valve_open": ph.valve_open, "sealed": ph.sealed,
            "duration_s": _finite(ph.duration_s), "n_steps": ph.n_steps,
            "material_balance_closed": bool(rc.material_balance_closed),
            "external_flux": {k: _finite(v) for k, v in rc.external_flux.items()},
            "raw_material_change": {k: _finite(v) for k, v in rc.raw_material_change.items()},
            "ledger_adjusted_residual": {k: _finite(v) for k, v in rc.ledger_adjusted_residual.items()},
            "reservoir_exchange": {k: _finite(v) for k, v in rc.reservoir_exchange.items()},
            "charge_balance_claim": rc.charge_balance_claim,
            "positivity_held": bool(rc.positivity_held), "min_inventory": _finite(rc.min_inventory),
            "stitch_clamp_total_mol": _finite(clamp_total), "stitch_clamp_max_mol": _finite(clamp_max),
            "numerical_adjustments": phase_events,
            "admitted_tier": rc.admitted_tier, "tolerance": _finite(rc.tolerance),
            "caveats": list(traj.caveats),
        })
        t0 += ph.duration_s

    run_id = run_identity(params, phases, acid_mol=acid_mol, bicarb_solid_mol=bicarb_solid_mol,
                          bicarb_dissolved_mol=bicarb_dissolved_mol, n_samples=n_samples,
                          scheme=_SCHEME, rtol=_RTOL, atol=_ATOL)

    # XX-4 WHOLE-RUN GLOBAL BALANCE.  The true end-to-end inventory change (final clamped state vs the true initial)
    # equals the integrated external flux PLUS the numerical adjustments.  The flux-ONLY residual is therefore left
    # EXACTLY equal to the numerical-adjustment total -- the roundoff clamps are the gap you get if you pretend they
    # were not there -- and accounting for them explicitly closes the balance.  Checked (non-implicit-reservoir)
    # components only; the implicit solvent reservoir legitimately exchanges H/O/charge.  `state` is the last clamped
    # state after the final phase.
    run_final_totals = _component_totals(state)
    comp_keys = (set(run_initial_totals) | set(run_final_totals)
                 | set(combined_external) | set(numerical_adjustment_total)) - set(run_reservoir)
    gb_measured, gb_flux_only, gb_accounted = {}, {}, {}
    global_balance_closed = True
    gb_tol = len(phases) * max_phase_tol + _STITCH_ATOL
    for k in sorted(comp_keys):
        measured = run_final_totals.get(k, 0.0) - run_initial_totals.get(k, 0.0)
        ext = combined_external.get(k, 0.0)
        adj = numerical_adjustment_total.get(k, 0.0)
        gb_measured[k] = _finite(measured)
        gb_flux_only[k] = _finite(measured - ext)             # == adj: the clamp is the gap flux alone cannot explain
        gb_accounted[k] = _finite(measured - ext - adj)       # ~0 once the numerical adjustment is counted
        if abs(measured - ext - adj) > gb_tol + 1e-6 * abs(measured):
            global_balance_closed = False
    return {
        "scenario_inputs": {"acid_mol": _finite(acid_mol), "bicarb_solid_mol": _finite(bicarb_solid_mol),
                            "bicarb_dissolved_mol": _finite(bicarb_dissolved_mol)},
        "volumes_L": {k: _finite(v) for k, v in vols.items()},
        "temperature_K": _finite(params.temperature_K),
        "activity_model": params.activity_model,
        "frames": frames,
        "phase_reports": phase_reports,
        "whole_run": {
            "external_flux_total": {k: _finite(v) for k, v in combined_external.items()},
            "raw_material_change_total": {k: _finite(v) for k, v in combined_raw.items()},
            "worst_ledger_residual": _finite(worst_residual),
            "material_balance_closed_every_phase": bool(all_closed),
            "positivity_held_every_phase": bool(all_positive),
            "stitch_clamp_total_mol": _finite(stitch_total_run),
            "stitch_clamp_max_mol": _finite(stitch_max_run),
            "numerical_adjustments": numerical_adjustments,
            "numerical_adjustment_total": {k: _finite(v) for k, v in numerical_adjustment_total.items()},
            "global_balance": {
                "checked_components": sorted(comp_keys),
                "measured_change": gb_measured,
                "external_flux_total": {k: _finite(combined_external.get(k, 0.0)) for k in sorted(comp_keys)},
                "residual_flux_only": gb_flux_only,       # XX-4: equals numerical_adjustment_total over checked comps
                "residual_accounted": gb_accounted,       # XX-4: ~0 -- the clamps are explicitly accounted, not hidden
                "closed": bool(global_balance_closed),
                "tolerance": _finite(gb_tol),
            },
            "admitted_tier": weakest(*tiers) if tiers else ASSUMED_PARAMETER,
        },
        "identity": {
            "model_digest": _digest(model_identity(params, phases)),
            "run_digest": _digest(run_id),
            "evidence_digest": _digest(evidence_identity(params)),
            "model_run_digest": _digest(run_id),   # back-compat alias = run_digest (NOW varies with inventories)
            "model_identity": model_identity(params, phases),
            "run_identity": run_id,
            "evidence_identity": evidence_identity(params),
        },
        "assumptions": [
            "k_diss, kLa, k_export are ASSUMED synthetic coefficients (CALIBRATION_REQUIRED); this is a numerical "
            "simulation, not a predictor of real fizzing RATES",
            "NaHCO3 saturation is an EMPIRICAL concentration product Qsp = S^2, defensible only in the dilute regime, "
            "not an activity-based phase equilibrium",
            "fast equilibrium is a once-per-step SNIA projection (first order); dissolution SI uses the pre-projection "
            "aqueous composition (first-order lag)",
            "no bubble nucleation/size/foam dynamics is modelled",
        ],
    }


# ============================================================ scenarios + CLI
def _scenario(name: str) -> dict:
    """The named minimum scenarios (OPERATION XVIII §5).  Each returns the simulate(...) kwargs."""
    base = UnifiedParams()
    closed = Phase_("valve_closed", valve_open=False, sealed=False, duration_s=60.0, n_steps=120)
    opened = Phase_("valve_open", valve_open=True, sealed=False, duration_s=240.0, n_steps=480)
    sealed_open = Phase_("valve_open_sealed", valve_open=True, sealed=True, duration_s=240.0, n_steps=480)
    scenarios = {
        # acid meets bicarbonate once the valve opens; open vessel exports CO2
        "default": dict(params=base, phases=(closed, opened), acid_mol=0.5, bicarb_solid_mol=0.2,
                        bicarb_dissolved_mol=0.1),
        "excess_acid": dict(params=base, phases=(closed, opened), acid_mol=1.0, bicarb_solid_mol=0.05,
                            bicarb_dissolved_mol=0.05),
        "excess_bicarbonate": dict(params=base, phases=(closed, opened), acid_mol=0.1, bicarb_solid_mol=0.5,
                                   bicarb_dissolved_mol=0.1),
        "sealed": dict(params=base, phases=(closed, sealed_open), acid_mol=0.5, bicarb_solid_mol=0.2,
                       bicarb_dissolved_mol=0.1),
        "no_carbon": dict(params=base, phases=(closed, opened), acid_mol=0.5, bicarb_solid_mol=0.0,
                          bicarb_dissolved_mol=0.0),
    }
    if name not in scenarios:
        raise ValueError(f"unknown scenario {name!r}; choose from {sorted(scenarios)}")
    return scenarios[name]


def _dashboard(result: dict) -> str:
    out = io.StringIO()
    out.write("=== SmartChem unified vinegar/bicarbonate world (OPERATION XIX §7) ===\n")
    si = result["scenario_inputs"]
    out.write(f"inputs: acid={si['acid_mol']} mol, solid NaHCO3={si['bicarb_solid_mol']} mol, "
              f"dissolved={si['bicarb_dissolved_mol']} mol  |  T={result['temperature_K']} K  "
              f"activity={result['activity_model']}\n")
    f0, fN = result["frames"][0], result["frames"][-1]
    out.write("pH convention = ACTIVITY (-log10 a_H+); concentration pH also emitted per frame\n")
    out.write(f"start:  pH_A(act)={f0['pH_A']}  pH_B(act)={f0['pH_B']}  I_B={f0['ionic_strength_B_M']}  "
              f"solid={f0['solid_NaHCO3_mol']:.4g}  CO2(g)={f0['CO2_gas_mol']:.3g}\n")
    out.write(f"end:    pH_A(act)={fN['pH_A']}  pH_B(act)={fN['pH_B']}  I_B={fN['ionic_strength_B_M']}  "
              f"solid={fN['solid_NaHCO3_mol']:.4g}  CO2(g)={fN['CO2_gas_mol']:.3g}  "
              f"p_CO2={fN['p_CO2_atm']:.3g} atm\n")
    wr = result["whole_run"]
    out.write(f"ledger: material balance closed every phase = {wr['material_balance_closed_every_phase']}  "
              f"worst residual = {wr['worst_ledger_residual']:.2e}\n")
    out.write(f"        external flux total (component -> mol) = {wr['external_flux_total']}\n")
    out.write(f"        stitch clamp total = {wr['stitch_clamp_total_mol']:.2e} mol "
              f"(max {wr['stitch_clamp_max_mol']:.2e}); positivity every phase = "
              f"{wr['positivity_held_every_phase']}\n")
    out.write(f"        admitted tier = {wr['admitted_tier']}  (charge: "
              f"{result['phase_reports'][-1]['charge_balance_claim'].split(':')[0]})\n")
    idy = result["identity"]
    out.write(f"identity: model={idy['model_digest'][:16]}  run={idy['run_digest'][:16]}  "
              f"evidence={idy['evidence_digest'][:16]}\n")
    return out.getvalue()


def _write_csv(result: dict, path: str) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        cols = ["time_s", "phase", "pH_A", "pH_B", "pH_A_concentration", "pH_B_concentration",
                "ionic_strength_A_M", "ionic_strength_B_M", "activity_model", "temperature_K",
                "solid_NaHCO3_mol", "CO2aq_B_mol", "CO2_gas_mol", "p_CO2_atm", "HAc_A_mol", "HAc_B_mol"]
        w.writerow(cols)
        for fr in result["frames"]:
            w.writerow([fr[c] for c in cols])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SmartChem unified vinegar/bicarbonate world (OPERATION XVIII §5)")
    ap.add_argument("--scenario", default="default",
                    help="default | excess_acid | excess_bicarbonate | sealed | no_carbon")
    ap.add_argument("--json", metavar="OUT.json", help="write the strict-JSON result here")
    ap.add_argument("--csv", metavar="OUT.csv", help="write the CSV time series here")
    args = ap.parse_args(argv)

    result = simulate(**_scenario(args.scenario))
    text = json.dumps(result, allow_nan=False, indent=2)
    if args.json:
        with open(args.json, "w") as fh:
            fh.write(text)
    if args.csv:
        _write_csv(result, args.csv)
    sys.stdout.write(_dashboard(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
