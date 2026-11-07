"""OPERATION XXIII Phase III -- the carbonate convention bridge + the SRM 186g phosphate holdout.

Preregistered in PREREGISTRATION.md (committed before this file first ran).  This harness writes RAW numbers plus the
mechanical decision-rule outcome; the scientific verdict is written by hand in CONVENTION_BRIDGE_VERDICT.md.

    python -m experiments.sandbox_foundation.benchmarks.measured_buffers_xxiii.run_convention_bridge_xxiii

NOTHING is fitted.  Every constant is read from a committed source (the repo's carbonate_equilibrium records, the
in-repo minteq.v4.dat, the two NIST certificates whose hashes PREREGISTRATION.md records).
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from scipy.optimize import brentq

from experiments.sandbox_foundation import aqueous_equilibrium as aq
from experiments.sandbox_foundation import carbonate_equilibrium as C

HERE = Path(__file__).resolve().parent
RESULT = HERE / "result_convention_bridge_xxiii.json"

# ------------------------------------------------------------------------------------------- measured holdouts
# Read from the fetched certificates (sha256 in PREREGISTRATION.md section 0).  U = expanded (with the BG convention);
# U_R = k * u_c(measurement) (the convention treated as exact).
MEASURED = {
    "carbonate_191d": {"pH_S_table1": 10.014, "U": 0.010, "pH_S_A1": 10.0137, "u_meas": 0.0015, "k_R": 2.01,
                       "composition_mol_per_kg": {"NaHCO3": 0.025, "Na2CO3": 0.025},
                       "certificate_sha256": "ea316fb1368d0563882a2b6926fe8a6bb07736e9d5fc1b24bb70c2317cc02d38"},
    "phosphate_186g_equimolal": {"pH_S_table1": 6.8640, "U": 0.010, "pH_S_A1": 6.8640, "u_meas": 0.00080, "k_R": 2.0,
                                 "composition_mol_per_kg": {"KH2PO4": 0.025, "Na2HPO4": 0.025},
                                 "certificate_sha256": "4a228c1b30ccf2a2d2eaca589d06d77b2fb7c2f7ba3b35f6d144c01eb6743116"},
    "phosphate_186g_physiological": {"pH_S_table1": 7.4157, "U": 0.010, "pH_S_A1": 7.4157, "u_meas": 0.0011,
                                     "k_R": 2.0,
                                     "composition_mol_per_kg": {"KH2PO4": 0.008695, "Na2HPO4": 0.03043},
                                     "certificate_sha256":
                                         "4a228c1b30ccf2a2d2eaca589d06d77b2fb7c2f7ba3b35f6d144c01eb6743116"},
}
# 186g lists ONE pH(S) column (no separate non-certified table); its u_c(measurement) column excludes the BG term, so
# the same value with U_R = k*u_c(measurement) is the convention-exact band, exactly as 191d's Table A1.

# Bates-Guggenheim convention: -log10 gamma_Cl = A sqrt(I) / (1 + 1.5 sqrt(I)).  A(25 C) = 0.5100 kg^1/2 mol^-1/2 is the
# IUPAC-2002 value as quoted by a SECONDARY source (the primary text was not retrievable: HTTP 403); the A-range below
# brackets the literature spread so the verdict's sensitivity to it is explicit.
BG_A = 0.5100
BG_A_RANGE = (0.5091, 0.5115)

# minteq.v4.dat (in-repo, NIST46.4 lineage, I = 0, 25 C unless noted):
PHOS_LOGBETA = (0.0, 12.375, 19.573, 21.721)          # PO4-3 + jH+ = HjPO4 (j = 0..3)
CARB_MINTEQ_LOGBETA = (0.0, 10.329, 16.681)          # CO3-2 + jH+ = HjCO3
PAIR_LOGK = {  # M+ + HjL = M(HjL): log K derived from the database's cumulative constants
    ("Na", "carbonate", 0): 1.27,                     # NaCO3-       (I=0, 25 C)
    ("Na", "carbonate", 1): 10.079 - 10.329,          # NaHCO3(0)    (I=0, 25 C)
    ("Na", "phosphate", 1): 13.445 - 12.375,          # NaHPO4-      (database: I=0.10, 20 C -- NOT an I=0 constant)
    ("K", "phosphate", 1): 13.255 - 12.375,           # KHPO4-       (I=0, 25 C)
}


def davies_log_gamma(z: int, ionic: float, A: float) -> float:
    if z == 0 or ionic <= 0:
        return 0.0
    s = math.sqrt(ionic)
    return -A * z * z * (s / (1.0 + s) - 0.3 * ionic)


def bg_minus_log_gamma_cl(ionic: float, A: float = BG_A) -> float:
    s = math.sqrt(ionic)
    return A * s / (1.0 + 1.5 * s)


# ------------------------------------------------------------------------------------------- generic Davies solver
@dataclass
class AcidBuffer:
    """One polyprotic ligand L (charge z_L) with cumulative protonation log-betas, conservative cations, optional
    cation-ligand pairs.  Molal throughout; neutral species gamma = 1; Davies for every ion."""
    ligand: str
    z_L: int
    log_beta: tuple                       # index j: L + jH+ = HjL
    total_L: float
    cations: dict                         # {name: total molal}, all z = +1
    pairs: dict = field(default_factory=dict)   # {(cation, j): log K}
    log_kw: float = -14.0
    A: float = 0.509

    def _speciate(self, h: float, ionic: float):
        g = lambda z: 10.0 ** davies_log_gamma(z, ionic, self.A)          # noqa: E731
        aH = h * g(1)
        zj = [self.z_L + j for j in range(len(self.log_beta))]
        coef = [10.0 ** self.log_beta[j] * aH ** j * g(self.z_L) / g(zj[j]) for j in range(len(zj))]  # [HjL]/[L]
        free_m = dict(self.cations)
        for _ in range(200):
            pair_coef = {k: 10.0 ** lk * g(1) * free_m[k[0]] * coef[k[1]] * g(zj[k[1]]) / g(zj[k[1]] + 1)
                         for k, lk in self.pairs.items()}
            L = self.total_L / (sum(coef) + sum(pair_coef.values()))
            new_m = {}
            for m, tot in self.cations.items():
                bound_per_free = sum(10.0 ** lk * g(1) * L * coef[j] * g(zj[j]) / g(zj[j] + 1)
                                     for (mm, j), lk in self.pairs.items() if mm == m)
                new_m[m] = tot / (1.0 + bound_per_free)
            if all(abs(new_m[m] - free_m[m]) <= 1e-16 + 1e-15 * free_m[m] for m in free_m):
                free_m = new_m
                break
            free_m = new_m
        species = {}
        for j in range(len(zj)):
            species[f"H{j}{self.ligand}"] = (L * coef[j], zj[j])
        for (m, j), lk in self.pairs.items():
            species[f"{m}H{j}{self.ligand}"] = (10.0 ** lk * g(1) * free_m[m] * L * coef[j] * g(zj[j]) / g(zj[j] + 1),
                                               zj[j] + 1)
        for m, v in free_m.items():
            species[m] = (v, 1)
        species["H+"] = (h, 1)
        species["OH-"] = (10.0 ** self.log_kw / (aH * g(1)), -1)
        return species

    def solve(self) -> dict:
        ionic = 0.0
        for _ in range(500):
            f = lambda lh: sum(c * z for c, z in self._speciate(10.0 ** lh, ionic).values())   # noqa: E731
            lh = brentq(f, -14.5, 0.0, xtol=1e-15, rtol=4 * sys.float_info.epsilon, maxiter=500)
            sp = self._speciate(10.0 ** lh, ionic)
            new_I = 0.5 * sum(c * z * z for c, z in sp.values())
            if abs(new_I - ionic) <= 1e-15:
                ionic = new_I
                break
            ionic = new_I
        h = 10.0 ** lh
        lg1 = davies_log_gamma(1, ionic, self.A)
        return {"ionic_strength": ionic, "pmH": -math.log10(h), "pH_davies": -math.log10(h) - lg1,
                "p_aH_gCl": -math.log10(h) - 2.0 * lg1, "species": {k: v[0] for k, v in sp.items()}}


def carbonate_buffer(*, constants: str, pairs: bool) -> AcidBuffer:
    na = 0.025 + 2 * 0.025
    if constants == "repo_frozen_XIX":
        pk1 = -math.log10(C.K1_CARBONIC_25C.value)
        pk2 = -math.log10(C.K2_CARBONIC_25C.value)
        logbeta = (0.0, pk2, pk1 + pk2)
        log_kw = math.log10(aq.KW_25C.value)
        A = aq.DAVIES_A_25C.value
    else:
        logbeta, log_kw, A = CARB_MINTEQ_LOGBETA, -13.997, aq.DAVIES_A_25C.value
    pr = {("Na", j): PAIR_LOGK[("Na", "carbonate", j)] for j in (0, 1)} if pairs else {}
    return AcidBuffer("CO3", -2, logbeta, 0.05, {"Na": na}, pr, log_kw, A)


def phosphate_buffer(kh2po4: float, na2hpo4: float, *, pairs: bool) -> AcidBuffer:
    pr = {("Na", 1): PAIR_LOGK[("Na", "phosphate", 1)], ("K", 1): PAIR_LOGK[("K", "phosphate", 1)]} if pairs else {}
    return AcidBuffer("PO4", -3, PHOS_LOGBETA, kh2po4 + na2hpo4, {"Na": 2 * na2hpo4, "K": kh2po4}, pr,
                      -13.997, aq.DAVIES_A_25C.value)


# ------------------------------------------------------------------------------------------- comparisons
def compare(model: dict, meas: dict, *, bg_ionic: float, bg_A: float = BG_A) -> dict:
    UR = meas["k_R"] * meas["u_meas"]
    bg = bg_minus_log_gamma_cl(bg_ionic, bg_A)
    meas_acidity = meas["pH_S_A1"] + bg                          # p(aH gCl)0 = pH(S) - log gCl(BG)
    r1 = model["pH_davies"] - meas["pH_S_table1"]
    r2 = model["p_aH_gCl"] - meas_acidity
    r3 = (model["p_aH_gCl"] - bg) - meas["pH_S_A1"]               # BG applied to the model output
    return {"C1_residual": r1, "C1_U": meas["U"], "C1_within": abs(r1) <= meas["U"],
            "C2_measured_acidity_function": meas_acidity, "C2_residual": r2, "C2_U_R": UR,
            "C2_within": abs(r2) <= UR, "C2_over_U_R": r2 / UR,
            "C3_model_pH_S_BG": model["p_aH_gCl"] - bg, "C3_residual": r3, "C3_within": abs(r3) <= UR,
            "C2_equals_C3": abs(r2 - r3) < 1e-12, "bg_ionic_strength": bg_ionic, "bg_A": bg_A}


def phreeqc_reference(db: str, solution: str) -> dict | None:
    """PHREEQC (phreeqpython) convention-free acidity function via a 1e-7 mol/kgw NaCl trace.  None if unavailable."""
    try:
        from phreeqpython import PhreeqPython
    except Exception:                                            # pragma: no cover - optional reference
        return None
    pp = PhreeqPython(database=db)
    sel = """
SELECTED_OUTPUT 1
    -reset false
    -pH true
    -ionic_strength true
    -activities H+ Cl-
    -molalities Cl-
"""
    pp.ip.run_string(sel + solution)
    rows = pp.ip.get_selected_output_array()
    head, last = rows[0], rows[-1]
    d = dict(zip(head, last))
    log_g_cl = d["la_Cl-"] - math.log10(d["m_Cl-(mol/kgw)"])
    return {"database": db, "pH_phreeqc": d["pH"], "ionic_strength": d["mu"],
            "p_aH_gCl": -d["la_H+"] - log_g_cl, "log_gamma_Cl": log_g_cl}


def _phreeqc_solution(case: str) -> str:
    trace = 1e-7
    if case == "carbonate_191d":
        body = f"    Na {0.075 + trace}\n    C(4) 0.05\n    Cl {trace}\n"
    elif case == "phosphate_186g_equimolal":
        body = f"    Na {0.05 + trace}\n    K 0.025\n    P 0.05\n    Cl {trace}\n"
    else:
        body = f"    Na {2 * 0.03043 + trace}\n    K 0.008695\n    P {0.008695 + 0.03043}\n    Cl {trace}\n"
    return f"SOLUTION 1\n    temp 25\n    units mol/kgw\n{body}    pH 7 charge\nEND\n"


def run() -> dict:
    out: dict = {"preregistration": "PREREGISTRATION.md", "measured": MEASURED, "models": {}, "comparisons": {},
                 "instrument_calibration": {}, "references": {}, "sensitivity": {}}
    # ---- instrument gate: the generic solver must reproduce the repo carbonate solver (frozen XIX baseline)
    repo = C.solve(C.CarbonateWaterSystem(activity_model="davies", mode="closed", total_carbon_M=0.05,
                                          sodium_M=0.075))
    mine = carbonate_buffer(constants="repo_frozen_XIX", pairs=False).solve()
    delta = mine["pH_davies"] - repo.pH_activity
    out["instrument_calibration"] = {"repo_carbonate_pH_activity": repo.pH_activity,
                                     "generic_solver_pH_davies": mine["pH_davies"], "delta": delta,
                                     "gate_abs_delta_lt_1e-9": abs(delta) < 1e-9}
    if not abs(delta) < 1e-9:
        raise SystemExit(f"instrument calibration FAILED: delta {delta}")

    models = {
        "carbonate_191d": {"M0": mine,
                           "M0_minteq_constants": carbonate_buffer(constants="minteq", pairs=False).solve(),
                           "M1": carbonate_buffer(constants="minteq", pairs=True).solve()},
        "phosphate_186g_equimolal": {"M0": phosphate_buffer(0.025, 0.025, pairs=False).solve(),
                                     "M1": phosphate_buffer(0.025, 0.025, pairs=True).solve()},
        "phosphate_186g_physiological": {"M0": phosphate_buffer(0.008695, 0.03043, pairs=False).solve(),
                                         "M1": phosphate_buffer(0.008695, 0.03043, pairs=True).solve()},
    }
    for case, ms in models.items():
        out["models"][case] = {name: {k: v for k, v in m.items() if k != "species"} for name, m in ms.items()}
        out["comparisons"][case] = {}
        for name, m in ms.items():
            out["comparisons"][case][name] = compare(m, MEASURED[case], bg_ionic=m["ionic_strength"])
        # sensitivity of the BG inversion to the (unstated) ionic strength and to A
        m0 = ms["M0"]
        out["sensitivity"][case] = {
            f"I{d:+.3f}": compare(m0, MEASURED[case], bg_ionic=m0["ionic_strength"] + d)["C2_residual"]
            for d in (-0.003, 0.0, 0.003)}
        out["sensitivity"][case].update({
            f"A={a}": compare(m0, MEASURED[case], bg_ionic=m0["ionic_strength"], bg_A=a)["C2_residual"]
            for a in BG_A_RANGE})
        out["references"][case] = {}
        dbs = ["phreeqc.dat", "pitzer.dat"] if case.startswith("carbonate") else ["phreeqc.dat"]
        for db in dbs:
            ref = phreeqc_reference(db, _phreeqc_solution(case))
            if ref is not None:
                meas = MEASURED[case]
                ref["C2_residual_vs_measured"] = ref["p_aH_gCl"] - (meas["pH_S_A1"]
                                                                   + bg_minus_log_gamma_cl(ref["ionic_strength"]))
                ref["C2_U_R"] = meas["k_R"] * meas["u_meas"]
            out["references"][case][db] = ref

    # ---- mechanical decision rule (PREREGISTRATION.md section 4), M0, C2
    rc = out["comparisons"]["carbonate_191d"]["M0"]
    re_ = out["comparisons"]["phosphate_186g_equimolal"]["M0"]
    rp = out["comparisons"]["phosphate_186g_physiological"]["M0"]

    def classify(dI: float) -> str:
        def r(case, base):
            m0 = models[case]["M0"]
            return compare(m0, MEASURED[case], bg_ionic=m0["ionic_strength"] + dI)["C2_residual"], base["C2_U_R"]
        (c, uc), (e, ue), (p, up) = r("carbonate_191d", rc), r("phosphate_186g_equimolal", re_), \
            r("phosphate_186g_physiological", rp)
        same_sign = (e * c > 0) and (p * c > 0)
        if same_sign and abs(e) > ue and abs(p) > up and abs(e) >= 0.5 * abs(c) and abs(p) >= 0.5 * abs(c):
            return "SYSTEMATIC"
        if abs(e) <= ue and abs(p) <= up and abs(c) > uc:
            return "CARBONATE-SPECIFIC"
        return "MIXED/UNRESOLVED"

    out["decision_rule"] = {f"I{d:+.3f}": classify(d) for d in (-0.003, 0.0, 0.003)}
    out["no_constant_fitted"] = True
    return out


def main() -> int:
    res = run()
    RESULT.write_text(json.dumps(res, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    ic = res["instrument_calibration"]
    print(f"instrument gate: repo {ic['repo_carbonate_pH_activity']:.12f} generic {ic['generic_solver_pH_davies']:.12f}"
          f" delta {ic['delta']:.2e}")
    for case, cm in res["comparisons"].items():
        for name, c in cm.items():
            m = res["models"][case][name]
            print(f"{case:30s} {name:20s} I={m['ionic_strength']:.5f} pH={m['pH_davies']:.4f} "
                  f"C1 {c['C1_residual']:+.4f} (U {c['C1_U']}) | C2 {c['C2_residual']:+.4f} (U_R {c['C2_U_R']:.4f}, "
                  f"{c['C2_over_U_R']:+.1f}x) C2==C3 {c['C2_equals_C3']}")
        for db, ref in res["references"][case].items():
            if ref:
                print(f"{'':30s} ref {db:16s} I={ref['ionic_strength']:.5f} pH={ref['pH_phreeqc']:.4f} "
                      f"C2 {ref['C2_residual_vs_measured']:+.4f}")
        print(f"{'':30s} sensitivity {res['sensitivity'][case]}")
    print("decision rule (M0, C2):", res["decision_rule"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
