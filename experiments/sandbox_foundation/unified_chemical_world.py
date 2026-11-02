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

from experiments.sandbox_foundation.carbonate_equilibrium import KH_CO2_25C, R_GAS_L_ATM
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER, weakest
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
    EquilibriumCoupling,
    ExternalBoundary,
    InterfaceTransfer,
)
from experiments.sandbox_foundation.general_equilibrium import MixedAcetateCarbonateEquilibriumOperator
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    Phase,
    RateLaw,
    Reaction,
    Species,
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


def build_unified_world(params: UnifiedParams, sp: _Species, *, valve_open: bool, sealed: bool) -> _Build:
    """Assemble the two-liquid-cell + gas-headspace CoupledWorld for one phase (valve open/closed, vessel sealed/open).

    The generic integrator is reused verbatim; the only thing that changes between phases is WHICH interfaces/boundaries
    are present -- the typed external commands the op calls step 1."""
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
    if valve_open:
        # selective membrane: only neutral HAc and CO2(aq) cross (charge-safe), A <-> B
        interfaces.append(InterfaceTransfer("valve_HAc", "A", "B", sp.HAc, sp.HAc, k_transfer=params.k_valve_Lps))
        interfaces.append(InterfaceTransfer("valve_CO2", "A", "B", sp.CO2aq, sp.CO2aq, k_transfer=params.k_valve_Lps))

    boundaries = []
    if not sealed:
        boundaries.append(ExternalBoundary("co2_export", "gas", sp.CO2g, "fixed_activity",
                                           k_transfer=params.k_export_Lps, target_conc=0.0))
    return _Build(CoupledWorld([cell_a, cell_b, gas], interfaces=interfaces, boundaries=boundaries), sp)


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
    """pH = -log10([H+]); [H+] = n(H+)/V.  None if H+ is non-positive (below the model's resolution)."""
    h = frame[cell].get(sp.Hp, 0.0)
    c = h / volume_L
    return -math.log10(c) if c > 0 else None


def _finite(x):
    return float(x) if (isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)) else None


def world_identity(params: UnifiedParams, phases: tuple) -> dict:
    """MODEL/RUN identity: every operative parameter + the phase schedule, bound so a frame ties to its governing
    configuration.  (Chemistry identities live in the kernel systems' own digests; here we bind the world config.)"""
    return {
        "identity_version": "xviii-5",
        "params": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in params.__dict__.items()},
        "phases": [[p.name, bool(p.valve_open), bool(p.sealed), float(p.duration_s), int(p.n_steps)] for p in phases],
        "constants": {"KH_CO2_25C": float(KH_CO2_25C.value), "R_GAS_L_ATM": float(R_GAS_L_ATM.value),
                      "Qsp_NaHCO3": float(KSP_NAHCO3_25C.value)},
    }


def world_identity_digest(params: UnifiedParams, phases: tuple) -> str:
    return hashlib.sha256(json.dumps(world_identity(params, phases), sort_keys=True).encode()).hexdigest()


def simulate(params: UnifiedParams, phases: tuple, *, acid_mol: float, bicarb_solid_mol: float,
             bicarb_dissolved_mol: float = 0.0, n_samples: int | None = None) -> dict:
    """Run the phase schedule through ONE unified world, stitching the end state of each phase into the next.  Every
    phase's conservation + signed-flux ledger is MEASURED (XVIII-3); the whole-run external flux is the sum over
    phases.  Returns a strict-JSON-able result."""
    sp = _build_species()
    state = initial_state(sp, acid_mol=acid_mol, bicarb_solid_mol=bicarb_solid_mol,
                          bicarb_dissolved_mol=bicarb_dissolved_mol)
    vols = {"A": params.V_A_L, "B": params.V_B_L, "gas": params.V_gas_L}

    t0 = 0.0
    frames = []
    phase_reports = []
    combined_external = {}
    combined_raw = {}
    worst_residual = 0.0
    tiers = []
    all_closed = True
    all_positive = True
    for ph in phases:
        build = build_unified_world(params, sp, valve_open=ph.valve_open, sealed=ph.sealed)
        traj = build.world.integrate(state, duration=ph.duration_s, n_steps=ph.n_steps, scheme="strang",
                                     n_samples=n_samples)
        rc = traj.receipt
        # stitch: the phase's final amounts become the next phase's initial state; clamp float-dust negatives at solid
        # exhaustion (the per-phase positivity_held / min_inventory independently surface any REAL negative excursion).
        state = {c: {s: max(0.0, float(v)) for s, v in traj.amounts[c][-1].items()} for c in traj.compartments}
        # frames (time-shifted onto the global clock)
        for j, t in enumerate(traj.times):
            fr = {c: traj.amounts[c][j] for c in traj.compartments}
            frames.append({
                "time_s": _finite(t0 + t), "phase": ph.name,
                "pH_A": _finite(_ph_of_cell(fr, sp, "A", params.V_A_L)),
                "pH_B": _finite(_ph_of_cell(fr, sp, "B", params.V_B_L)),
                "solid_NaHCO3_mol": _finite(fr["B"].get(sp.solid, 0.0)),
                "CO2aq_B_mol": _finite(fr["B"].get(sp.CO2aq, 0.0)),
                "CO2_gas_mol": _finite(fr["gas"].get(sp.CO2g, 0.0)),
                "p_CO2_atm": _finite(fr["gas"].get(sp.CO2g, 0.0) / params.V_gas_L * R_GAS_L_ATM.value
                                     * params.temperature_K),
                "HAc_A_mol": _finite(fr["A"].get(sp.HAc, 0.0)), "HAc_B_mol": _finite(fr["B"].get(sp.HAc, 0.0)),
            })
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
            "admitted_tier": rc.admitted_tier, "tolerance": _finite(rc.tolerance),
            "caveats": list(traj.caveats),
        })
        t0 += ph.duration_s

    return {
        "scenario_inputs": {"acid_mol": _finite(acid_mol), "bicarb_solid_mol": _finite(bicarb_solid_mol),
                            "bicarb_dissolved_mol": _finite(bicarb_dissolved_mol)},
        "volumes_L": {k: _finite(v) for k, v in vols.items()},
        "frames": frames,
        "phase_reports": phase_reports,
        "whole_run": {
            "external_flux_total": {k: _finite(v) for k, v in combined_external.items()},
            "raw_material_change_total": {k: _finite(v) for k, v in combined_raw.items()},
            "worst_ledger_residual": _finite(worst_residual),
            "material_balance_closed_every_phase": bool(all_closed),
            "positivity_held_every_phase": bool(all_positive),
            "admitted_tier": weakest(*tiers) if tiers else ASSUMED_PARAMETER,
        },
        "identity": {"model_run_digest": world_identity_digest(params, phases),
                     "world_identity": world_identity(params, phases)},
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
    out.write("=== SmartChem unified vinegar/bicarbonate world (OPERATION XVIII §5) ===\n")
    si = result["scenario_inputs"]
    out.write(f"inputs: acid={si['acid_mol']} mol, solid NaHCO3={si['bicarb_solid_mol']} mol, "
              f"dissolved={si['bicarb_dissolved_mol']} mol\n")
    f0, fN = result["frames"][0], result["frames"][-1]
    out.write(f"start:  pH_A={f0['pH_A']}  pH_B={f0['pH_B']}  solid={f0['solid_NaHCO3_mol']:.4g}  "
              f"CO2(g)={f0['CO2_gas_mol']:.3g}\n")
    out.write(f"end:    pH_A={fN['pH_A']}  pH_B={fN['pH_B']}  solid={fN['solid_NaHCO3_mol']:.4g}  "
              f"CO2(g)={fN['CO2_gas_mol']:.3g}  p_CO2={fN['p_CO2_atm']:.3g} atm\n")
    wr = result["whole_run"]
    out.write(f"ledger: material balance closed every phase = {wr['material_balance_closed_every_phase']}  "
              f"worst residual = {wr['worst_ledger_residual']:.2e}\n")
    out.write(f"        external flux total (component -> mol) = {wr['external_flux_total']}\n")
    out.write(f"        admitted tier = {wr['admitted_tier']}  (charge: "
              f"{result['phase_reports'][-1]['charge_balance_claim'].split(':')[0]})\n")
    out.write(f"identity: {result['identity']['model_run_digest'][:16]}...\n")
    return out.getvalue()


def _write_csv(result: dict, path: str) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        cols = ["time_s", "phase", "pH_A", "pH_B", "solid_NaHCO3_mol", "CO2aq_B_mol", "CO2_gas_mol", "p_CO2_atm",
                "HAc_A_mol", "HAc_B_mol"]
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
