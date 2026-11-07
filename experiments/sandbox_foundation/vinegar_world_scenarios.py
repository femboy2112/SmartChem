"""OPERATION XXIII -- deterministic vinegar/bicarbonate SCENARIO HARNESS on the 2.0a0 research API.

ONE declared chemistry (acetic acid in cell A; dissolved + solid NaHCO3 in cell B; a CO2 headspace), TWO boundary
regimes that differ ONLY in what the headspace boundary is:

    VENTED  -- open vessel: the existing fixed-activity CO2 export boundary on the gas (unified_chemical_world).
    SEALED  -- no export boundary: the CO2 that leaves the liquid stays in the headspace.

Schedule (both regimes): "separate" (A and B not connected) then "mixing" (ElectroneutralBulkExchange, the whole
dissolved roster at one Q -- the pour).  Nothing is scripted: there is no hardcoded bubble or pressure curve.  The
headspace pressure is ONLY the ideal-gas projection of the modeled gas inventory,

    p_CO2 = n_CO2(g) * R * T / V_gas

and since air is NOT modeled, that is the CO2 partial pressure above the initial (CO2-free) headspace, not the total
pressure.  (Total pressure, bubble size and foam are UNSUPPORTED -> null, never invented.  I'm not drawing foam that
the model doesn't have, sorry.)

Every per-frame value is typed with a LibGibson QuantityKind (CANONICAL / MODEL_DERIVED / UNSUPPORTED / ILLUSTRATION)
and a claim tier, and the frames are strict-JSON (allow_nan=False).

    computational only — not a laboratory safety certification

CLI:  python -m experiments.sandbox_foundation.vinegar_world_scenarios [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

from experiments.sandbox_foundation.carbonate_equilibrium import KH_CO2_25C, R_GAS_L_ATM
from experiments.sandbox_foundation.claim_tiers import OUT_OF_DOMAIN
from experiments.sandbox_foundation.sim_api_v2alpha import (
    API_VERSION,
    BoundaryPhase,
    BoundarySchedule,
    ModelSpec,
    SimulationResult,
    SimulationSpec,
    SolverOptions,
    SpeciesInventory,
    global_totals,
    receipt_to_dict,
    run,
)
from experiments.sandbox_foundation.snapshot import QuantityKind
from experiments.sandbox_foundation.unified_chemical_world import UnifiedParams

K = QuantityKind
SAFETY_NOTICE = "computational only — not a laboratory safety certification"
REGIMES = ("vented", "sealed")
P_CO2_LABEL = ("CO2 partial pressure in the headspace = n_CO2(g)*R*T/V_gas (ideal gas).  Air is NOT modeled: this is "
               "the CO2 contribution above the initial (CO2-free) headspace, not the total pressure")
DIC_SPECIES = ("CO2(aq)", "HCO3-", "CO3-2")
ACETATE_SPECIES = ("HAc", "Ac-")
LIQUID_CELLS = ("A", "B")


# ============================================================ the ONE declared chemistry
@dataclass(frozen=True)
class DeclaredChemistry:
    """The shared model chemistry.  The flagship's own default inventories (unified_chemical_world 'default'), not
    numbers tuned for a pretty plot."""
    params: UnifiedParams = UnifiedParams()
    acid_mol: float = 0.5
    bicarb_solid_mol: float = 0.2
    bicarb_dissolved_mol: float = 0.1
    separate_s: float = 20.0
    mixing_s: float = 280.0
    steps_per_10s: int = 5          # dt = 2 s at the default resolution (few hundred steps total, per the RAM budget)

    def initial(self) -> tuple:
        return (SpeciesInventory("A", "HAc", "aqueous", self.acid_mol),
                SpeciesInventory("B", "NaHCO3(s)", "solid", self.bicarb_solid_mol),
                SpeciesInventory("B", "HCO3-", "aqueous", self.bicarb_dissolved_mol),
                SpeciesInventory("B", "Na+", "aqueous", self.bicarb_dissolved_mol),
                SpeciesInventory("gas", "CO2(g)", "gas", 0.0))


def scenario_spec(regime: str, chem: DeclaredChemistry = DeclaredChemistry(), *, n_samples: int | None = None):
    """The SimulationSpec for one regime.  The regime touches EXACTLY one field: BoundaryPhase.vented."""
    if regime not in REGIMES:
        raise ValueError(f"regime must be one of {REGIMES}")
    vented = regime == "vented"
    n1 = max(1, round(chem.separate_s / 10.0 * chem.steps_per_10s))
    n2 = max(1, round(chem.mixing_s / 10.0 * chem.steps_per_10s))
    schedule = BoundarySchedule((
        BoundaryPhase("separate", chem.separate_s, n1, transport_mode="closed", vented=vented),
        BoundaryPhase("mixing", chem.mixing_s, n2, transport_mode="bulk", vented=vented),
    ))
    return SimulationSpec(model=ModelSpec(params=chem.params), initial=chem.initial(), schedule=schedule,
                          solver=SolverOptions(n_samples=n_samples))


# ============================================================ typed frame projection
def _q(value, unit, kind: QuantityKind, tier, label=""):
    return {"value": value, "unit": unit, "kind": kind.value, "tier": tier, "label": label}


def _unsupported(unit, why):
    # UNSUPPORTED serialises to null, NEVER 0 (snapshot.QuantityKind contract); OUT_OF_DOMAIN = no number handed back
    return _q(None, unit, K.UNSUPPORTED, OUT_OF_DOMAIN, why)


def _typed_frames(res: SimulationResult) -> list:
    spec = res.spec
    p = spec.model.params
    RT = R_GAS_L_ATM.value * p.temperature_K
    henry_k = p.kLa_per_s * p.V_B_L                     # exactly what build_unified_world declares
    henry_partition = KH_CO2_25C.value * RT
    receipts = {r.phase: r for r in res.receipts}
    phase_vented = {ph.name: ph.vented for ph in spec.schedule.phases}
    phase_end_t = {}
    t = 0.0
    for ph in spec.schedule.phases:
        t += float(ph.duration_s)
        phase_end_t[ph.name] = t
    c0 = global_totals(res.frames[0]).get("C", 0.0)    # post-initial-projection carbon (projection conserves C)
    assumptions = [e for e in spec.provenance.entries if e.tier == "ASSUMED" and e.name.startswith("k")]
    qsp = spec.provenance.by_name()["Qsp_NaHCO3_empirical"]

    out = []
    for f in res.frames:
        rc = receipts[f.phase]
        tier = rc.admitted_tier                         # the weakest-premise DYNAMIC claim for this phase
        a = f.amounts
        q = {}
        q["solid_NaHCO3_mol"] = _q(a[("B", "NaHCO3(s)")], "mol", K.CANONICAL, tier, "undissolved NaHCO3(s) in cell B")
        for c in LIQUID_CELLS:
            q[f"DIC_{c}_mol"] = _q(sum(a[(c, s)] for s in DIC_SPECIES), "mol", K.MODEL_DERIVED, tier,
                                   f"dissolved inorganic carbon in {c}: CO2(aq)+HCO3-+CO3-2")
            q[f"total_acetate_{c}_mol"] = _q(sum(a[(c, s)] for s in ACETATE_SPECIES), "mol", K.MODEL_DERIVED, tier,
                                             f"total acetate in {c}: HAc+Ac-")
            d = f.derived.get(c, {})
            q[f"pH_{c}"] = _q(d.get("pH"), "1", K.MODEL_DERIVED, tier,
                              f"authoritative activity pH of {c} from the equilibrium solver "
                              f"({d.get('activity_model')}); not recomputed by the harness")
        n_g = a[("gas", "CO2(g)")]
        q["CO2_gas_mol"] = _q(n_g, "mol", K.CANONICAL, tier, "headspace CO2(g) inventory")
        # literally n*R*T/V, evaluated left to right -- the one and only pressure "model" in this file
        q["p_CO2_atm"] = _q(n_g * R_GAS_L_ATM.value * p.temperature_K / p.V_gas_L, "atm", K.MODEL_DERIVED, tier, P_CO2_LABEL)
        # instantaneous Henry flux, the declared InterfaceTransfer law evaluated on this (post-projection) sample
        c_aq, c_g = a[("B", "CO2(aq)")] / p.V_B_L, n_g / p.V_gas_L
        q["henry_flux_B_to_gas_mol_per_s"] = _q(henry_k * (c_aq - henry_partition * c_g), "mol/s", K.MODEL_DERIVED,
                                                tier, "kLa*V_B*(c_CO2aq - K_H*R*T*c_CO2g); + = degassing")
        if phase_vented[f.phase]:
            q["export_flux_mol_per_s"] = _q(p.k_export_Lps * c_g, "mol/s", K.MODEL_DERIVED, tier,
                                            "open-vessel CO2 export k_export*c_CO2g (out of the vessel)")
        else:
            q["export_flux_mol_per_s"] = _q(0.0, "mol/s", K.MODEL_DERIVED, tier,
                                            "sealed: no export boundary is declared, so the export flux is exactly 0")
        stitched_c = sum(ev.element_impact.get("C", 0.0) for ev in res.stitch_events if ev.time_s <= f.time_s
                         and not (ev.time_s == f.time_s and f.phase == ev.after_phase))
        q["cumulative_C_exported_mol"] = _q(c0 + stitched_c - global_totals(f).get("C", 0.0), "mol",
                                            K.MODEL_DERIVED, tier,
                                            "carbon deficit vs the start (+ recorded stitch adjustments); equals the "
                                            "receipt ledger's integrated export at every phase end")
        q["ledger_C_external_flux_phase_mol"] = (
            _q(rc.external_flux.get("C", 0.0), "mol", K.MODEL_DERIVED, rc.structural_tier,
               "the receipt's independently integrated external C flux over this whole phase (XVIII-3 ledger)")
            if f.time_s == phase_end_t[f.phase] else
            _unsupported("mol", "the integrator exposes the boundary ledger only per phase, not per sample"))
        q["numerical_balance"] = _q(
            {comp: {"max_residual_mol": rc.component_max_residual.get(comp),
                    "tolerance_mol": rc.component_tolerance.get(comp),
                    "resolution": rc.component_resolution.get(comp)} for comp in rc.component_resolution},
            "mol", K.MODEL_DERIVED, rc.structural_tier,
            "phase-level receipt: per-component ledger residual over EVERY step of this phase (not this frame alone)")
        q["material_balance_closed"] = _q(rc.material_balance_closed, "bool", K.MODEL_DERIVED, rc.structural_tier,
                                          "every checked component VERIFIED_WITHIN_RESOLUTION")
        q["active_assumptions"] = _q(
            [{"name": e.name, "value": e.value, "unit": e.unit, "provenance_tier": e.tier} for e in assumptions]
            + [{"name": qsp.name, "value": qsp.value, "unit": qsp.unit, "provenance_tier": qsp.tier,
                "note": "EMPIRICAL concentration-product saturation proxy S^2, not an activity Ksp"}],
            "-", K.CANONICAL, "ASSUMED_PARAMETER", "dynamic coefficients the trajectory depends on (uncalibrated)")
        q["claim_tier"] = _q(tier, "-", K.MODEL_DERIVED, tier,
                             f"receipt admitted_tier (weakest premise); rate-law identity basis "
                             f"{rc.execution_identity_basis}")
        q["bubble_diameter_m"] = _unsupported("m", "no bubble nucleation/size model -- would be fabrication")
        q["foam_height_m"] = _unsupported("m", "no foam model -- would be fabrication")
        q["total_headspace_pressure_atm"] = _unsupported("atm", "air is not modeled; only the CO2 partial pressure is")
        out.append({"api_version": API_VERSION, "index": f.index, "time_s": f.time_s, "phase": f.phase,
                    "quantities": q})
    return out


def run_scenario(regime: str, chem: DeclaredChemistry = DeclaredChemistry(), *, n_samples: int | None = None) -> dict:
    res = run(scenario_spec(regime, chem, n_samples=n_samples))
    frames = _typed_frames(res)
    end = frames[-1]["quantities"]
    return {
        "api_version": API_VERSION,
        "regime": regime,
        "safety_notice": SAFETY_NOTICE,
        "notices": [SAFETY_NOTICE,
                    "ASSUMED kinetics (k_diss, kLa, k_export, k_valve): a numerical simulation, not a fizzing-rate "
                    "prediction",
                    "pressure is the ideal-gas projection of the modeled CO2(g) inventory; air not modeled"],
        "boundary": {ph.name: {"transport_mode": ph.transport_mode, "vented": ph.vented}
                     for ph in res.spec.schedule.phases},
        "frames": frames,
        "receipts": [receipt_to_dict(r) for r in res.receipts],
        "stitch_events": len(res.stitch_events),
        "admitted_tier": res.admitted_tier,
        "identities": {k: res.identities[k] for k in ("model_digest", "run_digest", "evidence_digest",
                                                       "observation_digest")},
        "model_identity": json.loads(json.dumps(_plain_identity(res.identities["model"]))),
        "end_state": {k: end[k]["value"] for k in (
            "solid_NaHCO3_mol", "DIC_A_mol", "DIC_B_mol", "pH_A", "pH_B", "CO2_gas_mol", "p_CO2_atm",
            "henry_flux_B_to_gas_mol_per_s", "cumulative_C_exported_mol", "total_acetate_A_mol",
            "total_acetate_B_mol")},
    }


def _plain_identity(obj):
    if hasattr(obj, "items"):
        return {k: _plain_identity(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain_identity(v) for v in obj]
    return obj


def run_both(chem: DeclaredChemistry = DeclaredChemistry(), *, n_samples: int | None = None) -> dict:
    """Both regimes + the EMERGENT difference (measured, not asserted)."""
    out = {r: run_scenario(r, chem, n_samples=n_samples) for r in REGIMES}
    v, s = out["vented"]["end_state"], out["sealed"]["end_state"]
    out["difference_sealed_minus_vented"] = {k: (s[k] - v[k]) if (s[k] is not None and v[k] is not None) else None
                                             for k in v}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="vinegar/bicarbonate vented-vs-sealed scenarios (2.0a0 research API)")
    ap.add_argument("--json", metavar="OUT.json")
    args = ap.parse_args(argv)
    both = run_both()
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(both, fh, allow_nan=False, indent=1)
    for r in REGIMES:
        sys.stdout.write(f"{r:7s} end: " + ", ".join(f"{k}={v:.6g}" for k, v in both[r]["end_state"].items()) + "\n")
    sys.stdout.write("sealed-vented: " + ", ".join(f"{k}={v:+.4g}" for k, v in
                                                     both["difference_sealed_minus_vented"].items()) + "\n")
    sys.stdout.write(SAFETY_NOTICE + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
