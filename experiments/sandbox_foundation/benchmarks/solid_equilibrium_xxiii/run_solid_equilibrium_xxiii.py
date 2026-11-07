"""OPERATION XXIII S4 -- validation harness for the activity-based solid dissolution law (solid_equilibrium.py).

    PYTHONPATH=. .venv/bin/python -m experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii.run_solid_equilibrium_xxiii

(a) calcite dissolving into CO2-free water, CLOSED system, integrated by the kernel (CoupledWorld) to steady state and
    compared to PHREEQC (phreeqpython, phreeqc.dat, EQUILIBRIUM_PHASES Calcite SI=0).  MODEL-vs-MODEL: both use the
    same thermodynamic constants (calcite logKsp -8.48 = in-repo minteq.v4.dat == phreeqc.dat; the carbonate / water /
    Ca ion-pair constants are read from phreeqc.dat), so agreement tests the ACTIVITY MODEL (Davies vs PHREEQC's WATEQ
    Debye-Huckel) + the kernel integration, NOT the constants and NOT nature.
(b) time-step refinement N, 2N, 4N;  (c) independent conservation from the trajectory;
(d) HOSTILE HOLDOUT nahcolite NaHCO3 (must FAIL CLOSED);  (e) phase / charge audit.
Nothing is fitted.  k_diss and kf are ASSUMED kinetic scales that set how fast, never where, the steady state sits
(tested: steady state is invariant to them).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from experiments.sandbox_foundation.aqueous_equilibrium import DAVIES_A_25C, SourcedConstant, _davies_gamma
from experiments.sandbox_foundation.general_coupled import Compartment, CoupledWorld
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Reaction, Species
from experiments.sandbox_foundation.solid_bicarbonate import NAHCO3_SOLUBILITY_25C
from experiments.sandbox_foundation.solid_equilibrium import (
    ActivityReversibleRate,
    ActivitySolubilityRate,
    OutOfDomainError,
)

HERE = Path(__file__).resolve().parent
SANDBOX = HERE.parent.parent
RESULT = HERE / "result_solid_equilibrium_xxiii.json"
MINTEQ = SANDBOX / "benchmarks" / "carbonate_na_pair_s6" / "db" / "minteq.v4.dat"
PHREEQC_DAT = Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / \
    "site-packages" / "phreeqpython" / "database" / "phreeqc.dat"
WATEQ_DAT = PHREEQC_DAT.parent / "wateq4f_PWN.dat"

T_K = 298.15
K_DISS = 1.0e-6        # mol L^-1 s^-1  ASSUMED dissolution kinetic scale (steady state independent of it)
KF_FAST = 1.0e8        # ASSUMED fast-speciation rate scale (steady state independent of it)
DURATION_S = 6000.0
N_BASE = 60
N_SOLID_MOL = 0.01     # calcite supplied (excess: ~1.2e-4 mol/L dissolves)
N_WATER_MOL = 55.34    # mol H2O in 1 L (997 g/L / 18.015)
TABULATION_HALF_UNIT = 0.5e-2   # half of the last tabulated decimal of a 2-decimal logK (see _constant)


# --------------------------------------------------------------------------------------------- database readers
def _read_block(path: Path, header: str, occurrence: int = 0) -> dict:
    """The log_k (and -analytic coefficients, if any) of the block whose header line is exactly ``header``."""
    lines = path.read_text(encoding="latin-1").replace("\r\n", "\n").split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.strip() == header and not ln.startswith(("\t", " "))]
    if len(hits) <= occurrence:
        raise ValueError(f"{header!r} not found in {path}")
    i = hits[occurrence]
    out = {"header": header, "file": str(path.name), "line": i + 1, "log_k": None, "analytic": None}
    for ln in lines[i + 1:i + 12]:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if not ln.startswith(("\t", " ")):
            break                                   # next block header: this block is over (never read past it)
        tok = s.replace("#", " # ").split()
        key = tok[0].lower().lstrip("-")
        if key == "log_k":
            out["log_k"] = float(tok[1])
        elif key == "analytic":
            vals = []
            for t in tok[1:]:
                if t == "#":
                    break
                vals.append(float(t))
            out["analytic"] = vals
    if out["log_k"] is None and out["analytic"] is None:
        raise ValueError(f"no log_k / analytic under {header!r}")
    return out


def _logk_at_25(block: dict) -> float:
    """PHREEQC's EFFECTIVE logK at 298.15 K (uses -analytic when present, as PHREEQC does)."""
    a = block["analytic"]
    if not a:
        return block["log_k"]
    a = list(a) + [0.0] * (6 - len(a))
    return a[0] + a[1] * T_K + a[2] / T_K + a[3] * math.log10(T_K) + a[4] / T_K ** 2 + a[5] * T_K ** 2


def _constant(name: str, logk: float, source: str) -> SourcedConstant:
    """A SourcedConstant for 10**logk.  Uncertainty = the TABULATION-RESOLUTION FLOOR only (half the last printed
    decimal, propagated to K) -- an honest lower bound, NOT a measurement uncertainty (which is larger, unquantified)."""
    K = 10.0 ** logk
    return SourcedConstant(name, K, K * math.log(10.0) * TABULATION_HALF_UNIT, "dimensionless (activity, 1 mol/L std)",
                           T_K, source, "SOURCED",
                           "uncertainty is the 2-decimal tabulation-resolution floor, NOT a measured error bar")


def load_constants(mode: str = "nominal") -> dict:
    """logK of every reaction the calcite world uses, as WRITTEN in the kernel network.  mode 'nominal' uses the
    tabulated -log_k; 'phreeqc_effective' uses what PHREEQC actually evaluates at 25 C (-analytic where present)."""
    cal = _read_block(MINTEQ, "Calcite")
    blocks = {
        "calcite_ksp": cal,
        "carbonate_h": _read_block(PHREEQC_DAT, "CO3-2 + H+ = HCO3-"),
        "carbonate_2h": _read_block(PHREEQC_DAT, "CO3-2 + 2 H+ = CO2 + H2O"),
        "water": _read_block(PHREEQC_DAT, "H2O = OH- + H+"),
        "caco3_aq": _read_block(PHREEQC_DAT, "Ca+2 + CO3-2 = CaCO3"),
        "cahco3": _read_block(PHREEQC_DAT, "Ca+2 + CO3-2 + H+ = CaHCO3+"),
        "caoh": _read_block(PHREEQC_DAT, "Ca+2 + H2O = CaOH+ + H+"),
        "calcite_phreeqc": _read_block(PHREEQC_DAT, "Calcite"),
    }
    # nominal = tabulated -log_k; a block with ONLY -analytic (water) has no nominal log_k, so its 25 C analytic value is used
    pick = (lambda b: b["log_k"] if b["log_k"] is not None else _logk_at_25(b)) if mode == "nominal" else _logk_at_25
    lk = {k: pick(b) for k, b in blocks.items()}
    lk["calcite_ksp"] = pick(cal)                     # minteq has no -analytic: nominal either way
    return {"logk": lk, "blocks": blocks}


# --------------------------------------------------------------------------------------------- the calcite world
def calcite_species() -> dict:
    A, L, S = Phase.AQUEOUS, Phase.PURE_LIQUID, Phase.SOLID
    return {
        "Ca": Species.of("Ca+2", {"Ca": 1}, 2, A), "CO3": Species.of("CO3-2", {"C": 1, "O": 3}, -2, A),
        "HCO3": Species.of("HCO3-", {"C": 1, "H": 1, "O": 3}, -1, A), "CO2": Species.of("CO2(aq)", {"C": 1, "O": 2}, 0, A),
        "H": Species.of("H+", {"H": 1}, 1, A), "OH": Species.of("OH-", {"H": 1, "O": 1}, -1, A),
        "CaCO3aq": Species.of("CaCO3(aq)", {"Ca": 1, "C": 1, "O": 3}, 0, A),
        "CaHCO3": Species.of("CaHCO3+", {"Ca": 1, "C": 1, "H": 1, "O": 3}, 1, A),
        "CaOH": Species.of("CaOH+", {"Ca": 1, "O": 1, "H": 1}, 1, A),
        "H2O": Species.of("H2O", {"H": 2, "O": 1}, 0, L), "calcite": Species.of("CaCO3(s)", {"Ca": 1, "C": 1, "O": 3}, 0, S),
    }


def build_calcite_world(mode: str = "nominal", *, k_diss: float = K_DISS, kf: float = KF_FAST,
                        ionic_strength_max: float = 0.1, allow_precipitation: bool = False):
    sp = calcite_species()
    consts = load_constants(mode)
    lk = consts["logk"]
    src = f"{MINTEQ.name} / {PHREEQC_DAT.name} ({mode})"
    # reactions AS WRITTEN (all with K >= 1 so the reverse coefficients stay finite); K = products/reactants.
    k2 = lk["carbonate_2h"] - lk["carbonate_h"]                        # HCO3- + H+ = CO2 + H2O
    spec = [
        ("HCO3 formation", ((sp["CO3"], -1), (sp["H"], -1), (sp["HCO3"], 1)), (), lk["carbonate_h"]),
        ("CO2 formation", ((sp["HCO3"], -1), (sp["H"], -1), (sp["CO2"], 1), (sp["H2O"], 1)), (sp["H2O"],), k2),
        ("water", ((sp["H"], -1), (sp["OH"], -1), (sp["H2O"], 1)), (sp["H2O"],), -lk["water"]),
        ("CaCO3(aq) pair", ((sp["Ca"], -1), (sp["CO3"], -1), (sp["CaCO3aq"], 1)), (), lk["caco3_aq"]),
        ("CaHCO3+ pair", ((sp["Ca"], -1), (sp["CO3"], -1), (sp["H"], -1), (sp["CaHCO3"], 1)), (), lk["cahco3"]),
        ("CaOH+ formation (reverse)", ((sp["CaOH"], -1), (sp["H"], -1), (sp["Ca"], 1), (sp["H2O"], 1)), (sp["H2O"],),
         -lk["caoh"]),
    ]
    rxns = [Reaction(
        "calcite dissolution",
        ((sp["calcite"], -1), (sp["Ca"], 1), (sp["CO3"], 1)),
        ActivitySolubilityRate(k_diss, _constant("Ksp_calcite", lk["calcite_ksp"], f"{src}: Calcite log_k {lk['calcite_ksp']:.4f}"),
                               ((sp["calcite"], -1), (sp["Ca"], 1), (sp["CO3"], 1)),
                               allow_precipitation=allow_precipitation, ionic_strength_max=ionic_strength_max))]
    for nm, st, unit, logk in spec:
        rxns.append(Reaction(nm, st, ActivityReversibleRate(kf, _constant("K " + nm, logk, f"{src}: logK {logk:.4f}"), st,
                                                            unit_activity=unit, ionic_strength_max=ionic_strength_max)))
    species = list(sp.values())
    world = CoupledWorld([Compartment("cell", ChemicalSystem(species, rxns, 1.0))])
    initial = {"cell": {sp["calcite"]: N_SOLID_MOL, sp["H2O"]: N_WATER_MOL, sp["H"]: 1e-7, sp["OH"]: 1e-7}}
    return world, sp, initial, consts


def _total_ca(amounts: dict, sp: dict) -> float:
    return sum(amounts[sp[k]] for k in ("Ca", "CaCO3aq", "CaHCO3", "CaOH"))


def run_calcite(n_steps: int, *, mode: str = "nominal", rtol: float = 1e-10, atol: float = 1e-18,
                duration: float = DURATION_S, **kw):
    world, sp, initial, consts = build_calcite_world(mode, **kw)
    traj = world.integrate(initial, duration=duration, n_steps=n_steps, rtol=rtol, atol=atol,
                           require_certified_execution=True)
    return world, sp, initial, traj, consts


def _state_at(traj, idx):
    return traj.amounts["cell"][idx]


def davies_I(amounts: dict, species_list) -> float:
    return 0.5 * sum(amounts[s] * s.charge ** 2 for s in species_list)


def kernel_summary(traj, sp) -> dict:
    fin = _state_at(traj, -1)
    ionic = davies_I(fin, sp.values())
    g1 = _davies_gamma(ionic, DAVIES_A_25C.value)
    pH = -math.log10(g1 * fin[sp["H"]])
    return {"Ca_total_M": _total_ca(fin, sp), "Ca2+": fin[sp["Ca"]], "CO3": fin[sp["CO3"]], "HCO3": fin[sp["HCO3"]],
            "CaCO3aq": fin[sp["CaCO3aq"]], "CaHCO3+": fin[sp["CaHCO3"]], "CaOH+": fin[sp["CaOH"]],
            "CO2aq": fin[sp["CO2"]], "pH_activity": pH, "I_M": ionic, "calcite_left_mol": fin[sp["calcite"]]}


# --------------------------------------------------------------------------------------------- PHREEQC reference
def phreeqc_reference() -> dict:
    from phreeqpython import PhreeqPython
    pp = PhreeqPython(database="phreeqc.dat")
    s = pp.add_solution({"units": "mmol/kgw", "temp": 25})
    s.saturate("Calcite", 0.0, 10)           # EQUILIBRIUM_PHASES Calcite SI=0, 10 mol available
    m = s.species_molalities
    rho = float(s.density)                   # kg/L
    return {"Ca_total_molal": s.total("Ca", "mol"), "density_kg_per_L": rho, "pH": s.pH, "I_molal": s.I,
            "SI_calcite": s.si("Calcite"),
            "species_molal": {k: m[k] for k in ("Ca+2", "CO3-2", "HCO3-", "CO2", "CaCO3", "CaHCO3+", "CaOH+", "H+", "OH-")},
            "database": "phreeqc.dat (phreeqpython)", "Ca_total_molar_via_density": s.total("Ca", "mol") * rho}


# --------------------------------------------------------------------------------------------- (c) conservation
def independent_conservation(traj, species) -> dict:
    """E n(t) for every element + charge, re-summed here from the trajectory with this file's own arithmetic."""
    elements = sorted({e for s in species for e in s.elements})
    series = {e: [] for e in elements + ["charge"]}
    for st in traj.amounts["cell"]:
        for e in elements:
            series[e].append(sum(st[s] * s.count(e) for s in species))
        series["charge"].append(sum(st[s] * s.charge for s in species))
    out = {}
    for lab, ser in series.items():
        out[lab] = {"n0": ser[0], "max_abs_drift": max(abs(v - ser[0]) for v in ser), "max_abs_charge_or_total": max(abs(v) for v in ser)}
    return out


# --------------------------------------------------------------------------------------------- (d) nahcolite holdout
def _nahcolite_world(ionic_strength_max: float, solid_mol: float = 2.0, V: float = 1.0):
    Na = Species.of("Na+", {"Na": 1}, 1, Phase.AQUEOUS)
    HCO3 = Species.of("HCO3-", {"C": 1, "H": 1, "O": 3}, -1, Phase.AQUEOUS)
    solid = Species.of("NaHCO3(s)", {"Na": 1, "C": 1, "H": 1, "O": 3}, 0, Phase.SOLID)
    wl = _read_block(WATEQ_DAT, "Nahcolite           58")
    ksp = _constant("Ksp_nahcolite", wl["log_k"], f"{WATEQ_DAT.name} line {wl['line']}: Nahcolite log_k {wl['log_k']}")
    st = ((solid, -1), (Na, 1), (HCO3, 1))
    rl = ActivitySolubilityRate(1.0e-3, ksp, st, ionic_strength_max=ionic_strength_max)
    world = CoupledWorld([Compartment("cell", ChemicalSystem([solid, Na, HCO3], [Reaction("nahcolite dissolution", st, rl)], V))])
    return world, {"cell": {solid: solid_mol}}, wl["log_k"]


def nahcolite_holdout() -> dict:
    from scipy.optimize import brentq
    log_k = _read_block(WATEQ_DAT, "Nahcolite           58")["log_k"]
    target = 10.0 ** (log_k / 2.0)                                      # m * gamma(I=m) at saturation
    m_sat = brentq(lambda m: m * _davies_gamma(m, DAVIES_A_25C.value) - target, 1e-6, 5.0, xtol=1e-14)
    S = NAHCO3_SOLUBILITY_25C
    out = {"wateq4f_log_k": log_k, "target_m_gamma": target, "davies_saturation_molality_pure_water": m_sat,
           "davies_I_at_saturation": m_sat, "measured_bulk_solubility_M": S.value, "measured_uncertainty_M": S.uncertainty,
           "measured_source": S.source, "disagreement_factor_measured_over_davies": S.value / m_sat,
           "disagreement_factor_range_over_measured_unc": [(S.value - S.uncertainty) / m_sat, (S.value + S.uncertainty) / m_sat],
           "note": "molality (Davies solve) vs molarity (repo solubility) differ by a few % at ~1 M; far smaller than the factor"}
    # the guarded kernel REFUSES on approach; the same world with a hand-raised domain runs and mispredicts silently
    world, init, _ = _nahcolite_world(0.1)
    try:
        world.integrate(init, duration=20000.0, n_steps=20, require_certified_execution=True)
        out["guarded_run"] = {"refused": False}
    except OutOfDomainError as e:
        out["guarded_run"] = {"refused": True, "error": type(e).__name__, "verdict": e.verdict,
                              "ionic_strength": e.ionic_strength, "ionic_strength_max": e.ionic_strength_max, "message": str(e)}
    wide, init2, _ = _nahcolite_world(5.0)
    tr = wide.integrate(init2, duration=200000.0, n_steps=20, rtol=1e-10, atol=1e-14)
    fin = tr.amounts["cell"][-1]
    na = [s for s in fin if s.name == "Na+"][0]
    out["unguarded_counterfactual_I_max_5"] = {"steady_Na_M": fin[na], "vs_measured_S": S.value, "factor_vs_measured": S.value / fin[na],
                                               "label": "COUNTERFACTUAL ONLY -- shows what a hand-raised domain would silently predict; not a result"}
    return out


# --------------------------------------------------------------------------------------------- main
def main() -> dict:
    res = {"label": "MODEL-vs-MODEL (kernel vs PHREEQC phreeqc.dat); shared constants; not a measurement", "T_K": T_K}
    ref = phreeqc_reference()
    res["phreeqc"] = ref
    # (a)
    world, sp, initial, traj, consts = run_calcite(N_BASE)
    k = kernel_summary(traj, sp)
    rho = ref["density_kg_per_L"]
    k["Ca_total_molal_equiv"] = k["Ca_total_M"] / rho
    res["kernel_nominal"] = k
    res["constants_nominal"] = {n: {"log_k": b["log_k"], "analytic": b["analytic"], "src": f"{b['file']}:{b['line']}"} for n, b in consts["blocks"].items()}
    res["agreement_nominal"] = {"Ca_total_rel_diff": k["Ca_total_molal_equiv"] / ref["Ca_total_molal"] - 1.0,
                                "Ca_total_rel_diff_numbers_unconverted": k["Ca_total_M"] / ref["Ca_total_molal"] - 1.0,
                                "pH_diff": k["pH_activity"] - ref["pH"], "I_rel_diff": k["I_M"] / ref["I_molal"] - 1.0}
    _, sp2, _, traj2, consts2 = run_calcite(N_BASE, mode="phreeqc_effective")
    k2 = kernel_summary(traj2, sp2)
    k2["Ca_total_molal_equiv"] = k2["Ca_total_M"] / rho
    res["kernel_phreeqc_effective_constants"] = k2
    res["agreement_phreeqc_effective"] = {"Ca_total_rel_diff": k2["Ca_total_molal_equiv"] / ref["Ca_total_molal"] - 1.0,
                                          "Ca_total_rel_diff_numbers_unconverted": k2["Ca_total_M"] / ref["Ca_total_molal"] - 1.0,
                                          "pH_diff": k2["pH_activity"] - ref["pH"], "I_rel_diff": k2["I_M"] / ref["I_molal"] - 1.0}
    # invariance of the steady state to the assumed kinetic scales
    inv = []
    for kd, kf in ((1e-6, 1e8), (1e-5, 1e8), (1e-6, 1e9)):
        _, s3, _, t3, _ = run_calcite(N_BASE, k_diss=kd, kf=kf, duration=DURATION_S)
        inv.append({"k_diss": kd, "kf": kf, "Ca_total_M": _total_ca(_state_at(t3, -1), s3)})
    res["kinetic_scale_invariance"] = inv
    # steady-state witness
    ca = [_total_ca(st, sp) for st in traj.amounts["cell"]]
    res["scale_note"] = ("Ca_total_rel_diff converts the kernel's mol/L to mol/kgw with PHREEQC's solution density; the "
                         "*_numbers_unconverted value compares the raw numbers.  The activity quotient uses the SAME dimensionless "
                         "K on either scale, so the ~0.3% spread between the two IS the molar-vs-molal convention slack (rho), "
                         "not a model discrepancy.")
    res["steady_state"] = {"Ca_last_step": ca[-1], "rel_change_last_step": (ca[-1] - ca[-2]) / ca[-1], "duration_s": DURATION_S}
    # (b) refinement
    ref_rows = {}
    for tolname, (rt, at) in {"tight(rtol1e-10,atol1e-18)": (1e-10, 1e-18), "loose(rtol1e-5,atol1e-12)": (1e-5, 1e-12)}.items():
        rows = []
        for n in (N_BASE, 2 * N_BASE, 4 * N_BASE):
            _, s4, _, t4, _ = run_calcite(n, rtol=rt, atol=at)
            dt = DURATION_S / n
            idx100 = int(round(100.0 / dt))
            rows.append({"n_steps": n, "dt_s": dt, "Ca_total_steady_M": _total_ca(_state_at(t4, -1), s4),
                         "Ca_total_t100s_M": _total_ca(_state_at(t4, idx100), s4), "t_sample_s": t4.times[idx100]})
        for key in ("Ca_total_steady_M", "Ca_total_t100s_M"):
            d1 = rows[1][key] - rows[0][key]
            d2 = rows[2][key] - rows[1][key]
            rows[2][key + "_diff_N_to_2N"] = d1
            rows[2][key + "_diff_2N_to_4N"] = d2
            rows[2][key + "_observed_order"] = (math.log2(abs(d1) / abs(d2)) if d1 != 0 and d2 != 0 else None)
        ref_rows[tolname] = rows
    res["refinement"] = ref_rows
    # (c) conservation
    res["conservation_independent"] = independent_conservation(traj, list(sp.values()))
    rc = traj.receipt
    res["receipt"] = {"admitted_tier": rc.admitted_tier, "execution_identity_basis": rc.execution_identity_basis,
                      "execution_identity_certified": rc.execution_identity_certified, "max_conserved_drift": rc.max_conserved_drift,
                      "positivity_held": rc.positivity_held, "min_inventory": rc.min_inventory, "structural_tier": rc.structural_tier}
    # (e) phase / charge audit
    fin_charge = [sum(st[s] * s.charge for s in sp.values()) for st in traj.amounts["cell"]]
    res["phase_charge"] = {"solid_species": [s.name for s in sp.values() if s.phase is Phase.SOLID],
                           "solid_charge": [s.charge for s in sp.values() if s.phase is Phase.SOLID],
                           "max_abs_net_charge_mol": max(abs(c) for c in fin_charge),
                           "ionic_strength_in_domain": res["kernel_nominal"]["I_M"] <= 0.1}
    # (d)
    res["nahcolite_holdout"] = nahcolite_holdout()
    RESULT.write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ("agreement_nominal", "agreement_phreeqc_effective", "steady_state", "phase_charge")}, indent=2))
    print(json.dumps(r["nahcolite_holdout"], indent=2, default=str))
