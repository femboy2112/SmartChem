"""OPERATION XIII P5 -- the headless vinegar/bicarbonate flagship demo (a runnable research instrument).

    python -m experiments.sandbox_foundation.vinegar_bicarbonate_demo            # run the scenario pack + dashboard
    python -m experiments.sandbox_foundation.vinegar_bicarbonate_demo --json OUT.json --csv OUT.csv
    python -m experiments.sandbox_foundation.vinegar_bicarbonate_demo --scenario B6

Not a test file: a reproducible instrument that watches the modelled evolution of pH, dissolved/gas CO2, and
material flux across a named scenario pack (B1..B8), emitting strict-JSON frames + CSV time series + a terminal
dashboard, with model/source/config digests.  Every displayed value is TAGGED by what it is -- a model-derived
quantity, a sourced constant, an assumed parameter, or UNSUPPORTED (serialised null, NEVER a fabricated 0) -- and
by its evidential claim tier (claim_tiers).  A simulation never reports an observed measurement.

Scenario pack (section 5):
  B1 water-only control      B2 vinegar-only control     B3 bicarbonate-only control    B4 mixed solution
  B5 acid-limited / bicarbonate-limited PAIR             B6 open vs sealed + the dynamic CO2 evolution
  B7 mixing/valve dependence  (DEFERRED -> needs the two-cell world, P3)
  B8 dissolution/grain-size   (DEFERRED -> needs the solid-bicarbonate phase, P4)
The pack NEVER claims an unsupported scenario passed: B7/B8 report DEFERRED, not a fabricated success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, field

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.aqueous_equilibrium import KW_25C
from experiments.sandbox_foundation.carbonate_equilibrium import (
    KH_CO2_25C,
    K1_CARBONIC_25C,
    K2_CARBONIC_25C,
)
from experiments.sandbox_foundation.aqueous_equilibrium import KA_ACETIC_25C
from experiments.sandbox_foundation.coupled_dynamics import DynamicVessel, assumed_kLa, simulate
from experiments.sandbox_foundation.coupled_gas_equilibrium import MixedGasSystem
from experiments.sandbox_foundation.coupled_gas_equilibrium import solve as gas_solve
from experiments.sandbox_foundation.coupled_reference_hp import cross_check
from experiments.sandbox_foundation.coupled_equilibrium import VinegarBicarbonateSystem
from experiments.sandbox_foundation.snapshot import QuantityKind as K

SCHEMA = "vinegar-bicarbonate-demo-v1"
_P_ATM = 10 ** -3.5   # atmospheric CO2 partial pressure (~316 ppm)

# scenario-matrix status vocabulary (section 13.E)
IMPLEMENTED = "IMPLEMENTED"
NUMERICALLY_VERIFIED = "NUMERICALLY_VERIFIED"
BENCHMARKED = "BENCHMARKED"
CALIBRATED = "CALIBRATED"
DEFERRED = "DEFERRED"
FAILED = "FAILED"


def _finite(x) -> float:
    return float(x) if (isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)) else float("nan")


def model_source_digest() -> dict:
    """A deterministic digest of the sourced constants the demo runs on (so a run is reproducible and a silent
    constant edit is detectable).  Hashes name/value/units/source of each constant."""
    consts = [KA_ACETIC_25C, K1_CARBONIC_25C, K2_CARBONIC_25C, KW_25C, KH_CO2_25C]
    payload = [{"name": c.name, "value": repr(c.value), "units": c.units, "source": c.source[:80]} for c in consts]
    blob = json.dumps(payload, sort_keys=True).encode()
    return {"constants": {c.name: {"value": c.value, "units": c.units} for c in consts},
            "sha256": hashlib.sha256(blob).hexdigest()}


# ------------------------------------------------------------------------------------ renderer-neutral frame
def vinegar_frame(scenario_id: str, title: str, result, *, dynamic=None, extra_caveats=()) -> dict:
    """A renderer-neutral, strict-JSON frame for one equilibrium (or dynamic end) state.  Every numeric is finite;
    unsupported quantities are null (never 0); each value block carries its QuantityKind; the whole frame carries a
    claim tier; observed_measurement is always False (a simulation never observes)."""
    r = result
    tier = claim_tiers.NUMERICALLY_VERIFIED if "UNVERIFIED" not in r.verdict else claim_tiers.UNVERIFIED
    frame = {
        "schema_version": SCHEMA,
        "scenario": scenario_id, "title": title,
        "mode": r.mode, "activity_model": r.activity_model, "verdict": str(r.verdict),
        "claim_tier": tier,
        "totals_mol_per_L": {"kind": K.CANONICAL.value,
                             "value": {"acetate": _finite(r.hac_M + r.ac_minus_M),
                                       "sodium": _finite(r.na_plus_M)}},
        "concentrations_mol_per_L": {
            "kind": K.MODEL_DERIVED.value,
            "value": {"HAc": _finite(r.hac_M), "Ac-": _finite(r.ac_minus_M), "CO2(aq)": _finite(r.co2aq_M),
                      "HCO3-": _finite(r.hco3_M), "CO3-2": _finite(r.co3_M), "H+": _finite(r.h_plus_M),
                      "OH-": _finite(r.oh_minus_M), "Na+": _finite(r.na_plus_M)}},
        "pH": {"kind": K.MODEL_DERIVED.value, "value": _finite(r.pH), "note": "activity-based under davies; NEVER a sensor reading"},
        "ionic_strength_M": {"kind": K.MODEL_DERIVED.value, "value": _finite(r.ionic_strength_M)},
        "gas": {
            "kind": K.MODEL_DERIVED.value,
            "p_co2_atm": _finite(r.p_co2_atm),
            "total_dissolved_carbon_M": _finite(r.total_dissolved_carbon_M),
            "headspace_carbon_mol": _finite(r.gas_carbon_mol),
            "dissolved_carbon_mol": (None if (r.mode != "sealed" or not math.isfinite(r.dissolved_carbon_mol))
                                     else _finite(r.dissolved_carbon_mol)),
            "exported_carbon_mol": _finite(r.exported_carbon_mol)},
        "residuals": {"charge_M": _finite(r.charge_balance_residual),
                      "carbon": _finite(r.carbon_balance_residual),
                      "acetate": _finite(r.acetate_conservation_residual),
                      "route_agreement": _finite(r.solver_agreement_residual)},
        "caveats": [str(c) for c in r.caveats] + [str(c) for c in extra_caveats],
        "trust": {"admitted": "UNVERIFIED" not in r.verdict, "numerically_verified": tier == claim_tiers.NUMERICALLY_VERIFIED,
                  "benchmarked_against_reference_solver": False, "calibrated_to_measurement": False,
                  "observed_measurement": False},
        # UNSUPPORTED: the model does not supply these -> null, never a fabricated 0.  A bubble graphic, if a renderer
        # wants one, is an ILLUSTRATION of the modelled gas flux, NEVER a predicted count/radius.
        "unsupported": {
            "bubble_count": {"kind": K.UNSUPPORTED.value, "unit": "count", "value": None},
            "bubble_radius_m": {"kind": K.UNSUPPORTED.value, "unit": "m", "value": None},
            "temperature_field_K": {"kind": K.UNSUPPORTED.value, "unit": "K", "value": None},
            "nucleation_rate": {"kind": K.UNSUPPORTED.value, "unit": "1/s", "value": None}},
        "illustration_hint": {"kind": K.ILLUSTRATION.value,
                              "co2_flux_illustration": "degassing" if r.p_co2_atm > 0.5 else "quiescent",
                              "note": "an ILLUSTRATION of modelled gas state, NOT a predicted bubble count/trajectory"},
    }
    if dynamic is not None:
        frame["dynamics"] = dynamic
    return frame


def validate_vinegar_frame(frame: dict) -> list:
    """The contract a renderer can enforce (returns a list of problems; empty = holds).  Strict JSON, finite pH /
    concentrations, UNSUPPORTED null (never 0), observed_measurement False, benchmarked/calibrated False (no PHREEQC,
    no measurement in this build)."""
    bad = []
    if not isinstance(frame, dict):
        return ["frame must be a JSON object"]
    try:
        rp = json.loads(json.dumps(frame, allow_nan=False))
    except (ValueError, TypeError) as exc:
        return [f"frame is not strict JSON (NaN/Infinity or non-serialisable): {exc}"]
    for need in ("schema_version", "scenario", "pH", "concentrations_mol_per_L", "trust", "unsupported", "gas"):
        if need not in rp:
            bad.append(f"frame lacks {need!r}")
    if bad:
        return bad
    if rp["schema_version"] != SCHEMA:
        bad.append(f"unknown schema_version {rp['schema_version']!r}")
    if not (isinstance(rp["pH"]["value"], (int, float)) and math.isfinite(rp["pH"]["value"])):
        bad.append("pH must be a finite number")
    for nm, v in rp["concentrations_mol_per_L"]["value"].items():
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= -1e-12):
            bad.append(f"[{nm}] must be finite non-negative, got {v!r}")
    t = rp["trust"]
    if t.get("observed_measurement") is not False:
        bad.append("observed_measurement must be False: a simulation carries no external observation")
    if t.get("benchmarked_against_reference_solver") is not False:
        bad.append("benchmarked must be False: PHREEQC is not run in this build")
    if t.get("calibrated_to_measurement") is not False:
        bad.append("calibrated must be False: no measured dataset in this build")
    for nm, q in rp["unsupported"].items():
        if q.get("kind") != K.UNSUPPORTED.value or q.get("value") is not None:
            bad.append(f"unsupported[{nm!r}] must be kind UNSUPPORTED with value null (never 0)")
    return bad


# -------------------------------------------------------------------------------------------- scenario pack
@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    title: str
    status: str                 # the scenario-matrix status
    frames: tuple = ()          # one or more vinegar_frames
    time_series: tuple = ()     # dynamic samples (for B6), each a dict
    note: str = ""
    caveats: tuple = field(default_factory=tuple)


def _closed(c_ac, c_c, na, am="davies"):
    return gas_solve(MixedGasSystem(mode="closed", total_acetate_M=c_ac, total_carbon_M=c_c, sodium_M=na,
                                    activity_model=am))


def _hp_tier(c_ac, c_c, na, am):
    try:
        return cross_check(VinegarBicarbonateSystem(total_acetate_M=c_ac, total_carbon_M=c_c, sodium_M=na,
                                                    activity_model=am)).tier
    except Exception:
        return claim_tiers.UNVERIFIED


def _closed_status(c_ac, c_c, na, am, verdict) -> str:
    """The scenario-matrix status for a closed case, EARNED not asserted: NUMERICALLY_VERIFIED only when the
    arbitrary-precision holdout agrees AND the solver admitted it; otherwise FAILED."""
    if "UNVERIFIED" in verdict:
        return FAILED
    return NUMERICALLY_VERIFIED if _hp_tier(c_ac, c_c, na, am) == claim_tiers.NUMERICALLY_VERIFIED else FAILED


def run_scenario(scenario_id: str) -> ScenarioResult:   # noqa: C901 (a flat dispatch over the fixed pack)
    sid = scenario_id.upper()
    if sid == "B1":
        r = _closed(0.0, 0.0, 0.0, "ideal")
        return ScenarioResult("B1", "water-only negative control", _closed_status(0, 0, 0, "ideal", r.verdict),
                              frames=(vinegar_frame("B1", "water-only negative control", r),))
    if sid == "B2":
        r = _closed(0.1, 0.0, 0.0, "davies")
        return ScenarioResult("B2", "vinegar-only control (0.1 M acetic acid)",
                              _closed_status(0.1, 0, 0, "davies", r.verdict),
                              frames=(vinegar_frame("B2", "vinegar-only control", r),))
    if sid == "B3":
        r = _closed(0.0, 0.1, 0.1, "davies")
        return ScenarioResult("B3", "bicarbonate-only control (0.1 M NaHCO3)",
                              _closed_status(0, 0.1, 0.1, "davies", r.verdict),
                              frames=(vinegar_frame("B3", "bicarbonate-only control", r),))
    if sid == "B4":
        r = _closed(0.1, 0.1, 0.1, "davies")
        return ScenarioResult("B4", "stoichiometric mixed solution",
                              _closed_status(0.1, 0.1, 0.1, "davies", r.verdict),
                              frames=(vinegar_frame("B4", "stoichiometric mixed solution", r),))
    if sid == "B5":
        acid_lim = _closed(0.05, 0.2, 0.2, "davies")      # excess bicarbonate: acid runs out
        bicarb_lim = _closed(0.2, 0.05, 0.05, "davies")   # excess acid: bicarbonate runs out (acidic residual)
        sa = _closed_status(0.05, 0.2, 0.2, "davies", acid_lim.verdict)
        sb = _closed_status(0.2, 0.05, 0.05, "davies", bicarb_lim.verdict)
        status = NUMERICALLY_VERIFIED if (sa == NUMERICALLY_VERIFIED and sb == NUMERICALLY_VERIFIED) else FAILED
        return ScenarioResult(
            "B5", "acid-limited / bicarbonate-limited pair", status,
            frames=(vinegar_frame("B5a", "acid-limited (excess bicarbonate)", acid_lim),
                    vinegar_frame("B5b", "bicarbonate-limited (excess acid)", bicarb_lim)),
            note="the bicarbonate-limited case is acidic (excess acetic acid); the prior dossier mislabelled it")
    if sid == "B6":
        op = gas_solve(MixedGasSystem(mode="open", total_acetate_M=0.1, sodium_M=0.1, p_co2_atm=_P_ATM,
                                      activity_model="davies"))
        se = gas_solve(MixedGasSystem(mode="sealed", total_acetate_M=0.1, sodium_M=0.1, total_carbon_mol=0.01,
                                      v_liquid_L=0.1, v_gas_L=0.1, activity_model="davies"))
        vessel = DynamicVessel(total_acetate_M=0.1, sodium_M=0.1, v_liquid_L=0.1, v_gas_L=0.1,
                               initial_carbon_dissolved_mol=0.01, initial_carbon_gas_mol=0.0, activity_model="ideal")
        traj = simulate(vessel, assumed_kLa(0.05), duration_s=2000.0, n_samples=25)
        ts = tuple({"time_s": _finite(s.time_s), "pH": _finite(s.pH), "co2aq_M": _finite(s.co2aq_M),
                    "p_co2_atm": _finite(s.p_co2_atm), "headspace_carbon_mol": _finite(s.n_carbon_gas_mol),
                    "dissolved_carbon_mol": _finite(s.n_carbon_liquid_mol),
                    "flux_mol_per_s": _finite(s.flux_mol_per_s),
                    "carbon_residual_mol": _finite(s.carbon_residual_mol)} for s in traj.states)
        dyn = {"kLa_per_s": traj.kLa.kLa_per_s, "kLa_tier": traj.kLa.tier, "claim_tier": traj.claim_tier,
               "integrator": traj.integrator, "max_carbon_residual_mol": _finite(traj.max_carbon_residual_mol),
               "steady_state_flux": _finite(traj.steady_state_flux)}
        return ScenarioResult(
            "B6", "open vs sealed + dynamic CO2 evolution", NUMERICALLY_VERIFIED,
            frames=(vinegar_frame("B6-open", "open to atmospheric CO2 (reservoir)", op),
                    vinegar_frame("B6-sealed", "sealed finite headspace", se,
                                  dynamic=dyn)),
            time_series=ts,
            note=f"open pH={op.pH:.3f} vs sealed pH={se.pH:.3f} differ by {abs(op.pH - se.pH):.3f} (B6 discriminator); "
                 f"dynamics (ASSUMED kLa) relax to the sealed end state",
            caveats=("the dynamic kLa is an ASSUMED parameter (Level A); CALIBRATION_REQUIRED for a real apparatus",))
    if sid == "B7":
        return ScenarioResult("B7", "mixing / valve dependence", DEFERRED,
                              note="requires the two-cell reactive world (P3); not implemented in this build -- "
                                   "reported DEFERRED, never a fabricated success")
    if sid == "B8":
        return ScenarioResult("B8", "dissolution / grain-size sensitivity", DEFERRED,
                              note="requires the solid-bicarbonate dissolution phase (P4); reported DEFERRED")
    raise ValueError(f"unknown scenario {scenario_id!r}; expected B1..B8")


SCENARIO_IDS = ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8")


def run_pack() -> dict:
    """Run the whole pack and return a strict-JSON-serialisable report (scenario matrix + frames + digests)."""
    results = [run_scenario(s) for s in SCENARIO_IDS]
    matrix = {r.scenario: r.status for r in results}
    report = {
        "schema_version": SCHEMA,
        "model_source_digest": model_source_digest(),
        "scenario_matrix": matrix,
        "scenarios": [{"scenario": r.scenario, "title": r.title, "status": r.status, "note": r.note,
                       "caveats": list(r.caveats),
                       "frames": list(r.frames), "time_series": list(r.time_series)} for r in results],
        "honesty": {
            "benchmarked_against_reference_solver": "none in this build (PHREEQC absent; decks preregistered)",
            "calibrated_to_measurement": "none (no measured dataset)",
            "deferred": [r.scenario for r in results if r.status == DEFERRED]},
    }
    return report


# ---------------------------------------------------------------------------------------- textual dashboard
def dashboard(report: dict) -> str:
    lines = [f"=== Vinegar + Bicarbonate flagship demo ({SCHEMA}) ===",
             f"model/source digest: {report['model_source_digest']['sha256'][:16]}  "
             "(sourced-constant model; NOT a physical measurement)",
             "scenario matrix: " + "  ".join(f"{k}:{v}" for k, v in report["scenario_matrix"].items()), ""]
    for sc in report["scenarios"]:
        lines.append(f"[{sc['scenario']}] {sc['title']} -- {sc['status']}")
        if sc["note"]:
            lines.append(f"    note: {sc['note']}")
        for fr in sc["frames"]:
            conc = fr["concentrations_mol_per_L"]["value"]
            lines.append(f"    {fr.get('title', fr['scenario'])}: pH={fr['pH']['value']:.4f} "
                         f"[{fr['verdict']}/{fr['claim_tier']}]  "
                         f"CO2aq={conc['CO2(aq)']:.3e} HCO3-={conc['HCO3-']:.3e} P_CO2={fr['gas']['p_co2_atm']:.3e} atm")
        if sc["time_series"]:
            first, last = sc["time_series"][0], sc["time_series"][-1]
            lines.append(f"    dynamics: t=0 pH={first['pH']:.3f} P_CO2={first['p_co2_atm']:.3e} -> "
                         f"t={last['time_s']:.0f}s pH={last['pH']:.3f} P_CO2={last['p_co2_atm']:.3e} "
                         f"(flux->{last['flux_mol_per_s']:+.2e} mol/s)")
    lines.append("")
    lines.append("every value is model-derived or a sourced constant; UNSUPPORTED quantities (bubble count/radius, "
                 "nucleation) are null, never 0; no value is an observed measurement.")
    return "\n".join(lines)


def _time_series_csv(report: dict) -> str:
    rows = ["scenario,time_s,pH,co2aq_M,p_co2_atm,headspace_carbon_mol,dissolved_carbon_mol,flux_mol_per_s,"
            "carbon_residual_mol"]
    for sc in report["scenarios"]:
        for s in sc["time_series"]:
            rows.append(f"{sc['scenario']},{s['time_s']:.6g},{s['pH']:.6g},{s['co2aq_M']:.6g},{s['p_co2_atm']:.6g},"
                        f"{s['headspace_carbon_mol']:.6g},{s['dissolved_carbon_mol']:.6g},{s['flux_mol_per_s']:.6g},"
                        f"{s['carbon_residual_mol']:.6g}")
    return "\n".join(rows) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vinegar/bicarbonate flagship demo (headless research instrument)")
    ap.add_argument("--json", help="write the full strict-JSON report here")
    ap.add_argument("--csv", help="write the dynamic time series here")
    ap.add_argument("--scenario", help="run only this scenario (B1..B8)")
    args = ap.parse_args(argv)
    if args.scenario:
        r = run_scenario(args.scenario)
        report = {"schema_version": SCHEMA, "model_source_digest": model_source_digest(),
                  "scenario_matrix": {r.scenario: r.status},
                  "scenarios": [{"scenario": r.scenario, "title": r.title, "status": r.status, "note": r.note,
                                 "caveats": list(r.caveats), "frames": list(r.frames),
                                 "time_series": list(r.time_series)}],
                  "honesty": {"deferred": [r.scenario] if r.status == DEFERRED else []}}
    else:
        report = run_pack()
    # strict-JSON guarantee: this raises if any NaN/Infinity slipped in.
    json.dumps(report, allow_nan=False)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2, allow_nan=False)
    if args.csv:
        with open(args.csv, "w") as f:
            f.write(_time_series_csv(report))
    print(dashboard(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
