"""OPERATION XXV Phase III-B -- verification harness for open_calcite_xxv against PHREEQC (MODEL-vs-MODEL).

    PYTHONPATH=. .venv/bin/python -m experiments.sandbox_foundation.benchmarks.open_calcite_xxv.run_open_calcite_xxv

Compares the sandbox open calcite world (P&B constants, Davies activities, kernel integration to a certified steady
state) with PHREEQC (phreeqpython, the vendored sha-pinned phreeqc.dat) on an ALLOWED grid.  Both sides use the same
Plummer & Busenberg constants (PHREEQC's own CO2(g) fit is replaced by the P&B KH via a PHASES block; a second
"native" PHREEQC run keeps phreeqc.dat's CO2(g) and is reported for transparency).  The residual therefore measures the
activity model (Davies vs PHREEQC's WATEQ Debye-Huckel + Setschenow for neutral species), the CaOH+ / (CO2)2 species
the sandbox omits, and the molar/molal bookkeeping -- NOT the constants and NOT nature.  This is verification only.

RESERVED HOLDOUT REGION.  A preregistered measured holdout will be run at roughly room temperature in open air.  This
harness REFUSES (``assert_outside_reserved_box``) any state with T in [288.15, 303.15] K AND pCO2 in [1e-4, 1e-2] atm,
for the sandbox AND for PHREEQC, so no prediction inside that box can be produced here.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import run_solid_equilibrium_xxiii as H
from experiments.sandbox_foundation.open_calcite_xxv import build_open_calcite_world, model_identity_digest
from experiments.sandbox_foundation.temperature_law_xxv import PB82_KH_CO2, water_density_kg_per_L

HERE = Path(__file__).resolve().parent
RESULT = HERE / "result_open_calcite_xxv.json"

RESERVED_T_K = (288.15, 303.15)
RESERVED_PCO2_ATM = (1e-4, 1e-2)

GRID_T_K = (278.15, 313.15, 333.15)
GRID_PCO2_ATM = (10.0 ** -3.5, 1e-2, 0.1, 1.0)
EXTRA_POINTS = ((298.15, 0.1), (298.15, 1.0))


class ReservedRegionError(RuntimeError):
    """A state inside the reserved holdout region was requested; refused before any evaluation."""


def in_reserved_box(T_K: float, pCO2_atm: float) -> bool:
    return (RESERVED_T_K[0] <= T_K <= RESERVED_T_K[1]) and (RESERVED_PCO2_ATM[0] <= pCO2_atm <= RESERVED_PCO2_ATM[1])


def assert_outside_reserved_box(T_K: float, pCO2_atm: float) -> None:
    if in_reserved_box(T_K, pCO2_atm):
        raise ReservedRegionError(f"(T={T_K} K, pCO2={pCO2_atm} atm) lies in the reserved holdout region; refusing")


def allowed_grid() -> list:
    pts = [(T, p) for T in GRID_T_K for p in GRID_PCO2_ATM] + list(EXTRA_POINTS)
    for T, p in pts:
        assert_outside_reserved_box(T, p)
    return pts


# --------------------------------------------------------------------------------------------- PHREEQC reference
def _phreeqc():
    from phreeqpython import PhreeqPython
    H._pinned_bytes(H.PHREEQC_DAT)
    return PhreeqPython(database=H.PHREEQC_DAT.name, database_directory=H.DB_DIR)


_SPECIES = ("Ca+2", "CaHCO3+", "CaCO3", "CaOH+", "CO2", "HCO3-", "CO3-2", "(CO2)2", "H+", "OH-")


def phreeqc_open_calcite(T_K: float, pCO2_atm: float, *, co2_law: str = "pb82", pp=None) -> dict:
    """PHREEQC equilibrium of pure water with calcite (SI 0) and CO2(g) at log10 pCO2.  co2_law 'pb82' replaces the gas
    by a phase carrying the P&B KH -analytic (no Peng-Robinson parameters); 'native' uses phreeqc.dat's CO2(g)."""
    assert_outside_reserved_box(T_K, pCO2_atm)
    pp = pp or _phreeqc()
    if co2_law == "pb82":
        a = " ".join(PB82_KH_CO2.coefficients[:5])
        phases, gas = f"PHASES\nCO2_PB82(g)\n CO2 = CO2\n -analytic {a}\n", "CO2_PB82(g)"
    elif co2_law == "native":
        phases, gas = "", "CO2(g)"
    else:
        raise ValueError("co2_law must be 'pb82' or 'native'")
    inp = (f"{phases}SOLUTION 1\n temp {T_K - 273.15:.6f}\n units mol/kgw\n"
           f"EQUILIBRIUM_PHASES 1\n Calcite 0 10\n {gas} {math.log10(pCO2_atm):.12f} 10\n"
           "SELECTED_OUTPUT 1\n -reset false\n -temperature true\n -pH true\n -ionic_strength true\n"
           " -totals Ca C\n -molalities " + " ".join(_SPECIES) + f"\n -saturation_indices Calcite {gas}\n"
           "USER_PUNCH 1\n -headings rho_kg_per_L mass_water_kg\n 10 PUNCH RHO, TOT(\"water\")\nEND\n")
    pp.ip.run_string(inp)
    arr = pp.ip.get_selected_output_array()
    head, row = arr[0], arr[-1]
    d = dict(zip(head, row))
    return {"co2_law": co2_law, "T_C": d["temp(C)"], "pH": d["pH"], "I_molal": d["mu"],
            "Ca_total_molal": d["Ca(mol/kgw)"], "DIC_molal": d["C(mol/kgw)"],
            "species_molal": {s: d[f"m_{s}(mol/kgw)"] for s in _SPECIES},
            "si_calcite": d["si_Calcite"], "si_gas": d[f"si_{gas}"], "rho_kg_per_L": d["rho_kg_per_L"],
            "mass_water_kg": d["mass_water_kg"]}


def phreeqc_pure_water_density(T_K: float, pp=None) -> float:
    pp = pp or _phreeqc()
    pp.ip.run_string(f"SOLUTION 1\n temp {T_K - 273.15:.6f}\nSELECTED_OUTPUT 1\n -reset false\n"
                     "USER_PUNCH 1\n -headings rho\n 10 PUNCH RHO\nEND\n")
    return float(pp.ip.get_selected_output_array()[-1][0])


# --------------------------------------------------------------------------------------------- comparison
def compare_point(T_K: float, pCO2_atm: float, pp=None) -> dict:
    assert_outside_reserved_box(T_K, pCO2_atm)
    pp = pp or _phreeqc()
    m = build_open_calcite_world(T_K, pCO2_atm)
    ref = phreeqc_open_calcite(T_K, pCO2_atm, co2_law="pb82", pp=pp)
    nat = phreeqc_open_calcite(T_K, pCO2_atm, co2_law="native", pp=pp)
    ca_share_caoh = ref["species_molal"]["CaOH+"] / ref["Ca_total_molal"]
    return {
        "T_K": T_K, "pCO2_atm": pCO2_atm,
        "model": {"Ca_total_M": m.Ca_total_M, "DIC_M": m.DIC_M, "pH_activity_molar": m.pH_activity,
                  "Ca_total_molal_equiv": m.Ca_total_molal_equiv, "DIC_molal_equiv": m.DIC_molal_equiv,
                  "pH_molal_equiv": m.pH_molal_equiv, "I_M": m.ionic_strength_M,
                  "run_identity_digest": m.receipt["run_identity_digest"]},
        "phreeqc_pb82_co2": ref, "phreeqc_native_co2": nat,
        "rel_diff_vs_pb82": {"Ca_total": m.Ca_total_molal_equiv / ref["Ca_total_molal"] - 1.0,
                             "DIC": m.DIC_molal_equiv / ref["DIC_molal"] - 1.0,
                             "pH_abs_diff": m.pH_molal_equiv - ref["pH"]},
        "rel_diff_vs_native": {"Ca_total": m.Ca_total_molal_equiv / nat["Ca_total_molal"] - 1.0,
                               "DIC": m.DIC_molal_equiv / nat["DIC_molal"] - 1.0,
                               "pH_abs_diff": m.pH_molal_equiv - nat["pH"]},
        "phreeqc_CaOH+_share_of_Ca": ca_share_caoh,
        "label": "MODEL-vs-MODEL (P&B constants shared); verification, not validation",
    }


def main() -> dict:
    pp = _phreeqc()
    rows = [compare_point(T, p, pp=pp) for T, p in allowed_grid()]
    dens = {str(T): {"kell": water_density_kg_per_L(T), "phreeqc": phreeqc_pure_water_density(T, pp=pp)}
            for T in sorted({T for T, _ in allowed_grid()})}
    worst = {k: max(abs(r["rel_diff_vs_pb82"][k]) for r in rows) for k in ("Ca_total", "DIC", "pH_abs_diff")}
    res = {"label": "MODEL-vs-MODEL verification on the ALLOWED grid (reserved box T in [288.15, 303.15] K x pCO2 in "
                    "[1e-4, 1e-2] atm never evaluated)",
           "reserved_box": {"T_K": RESERVED_T_K, "pCO2_atm": RESERVED_PCO2_ATM},
           "grid": allowed_grid(), "rows": rows, "worst_abs_vs_pb82": worst, "water_density_check": dens,
           "model_identity_digest": model_identity_digest()}
    RESULT.write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(f"{'T_K':>7} {'pCO2':>9} {'Ca_mod(m)':>11} {'Ca_phq':>11} {'dCa':>8} {'DIC_mod':>11} {'DIC_phq':>11} {'dDIC':>8}"
          f" {'pH_mod':>7} {'pH_phq':>7} {'dpH':>7} {'dCa_nat':>8} {'CaOH%':>7} {'I':>7}")
    for row in r["rows"]:
        m, p, d = row["model"], row["phreeqc_pb82_co2"], row["rel_diff_vs_pb82"]
        print(f"{row['T_K']:7.2f} {row['pCO2_atm']:9.3g} {m['Ca_total_molal_equiv']:11.5e} {p['Ca_total_molal']:11.5e} "
              f"{100*d['Ca_total']:+7.3f}% {m['DIC_molal_equiv']:11.5e} {p['DIC_molal']:11.5e} {100*d['DIC']:+7.3f}% "
              f"{m['pH_molal_equiv']:7.4f} {p['pH']:7.4f} {d['pH_abs_diff']:+7.4f} "
              f"{100*row['rel_diff_vs_native']['Ca_total']:+7.3f}% {100*row['phreeqc_CaOH+_share_of_Ca']:7.4f} "
              f"{m['I_M']:7.4f}")
    print("worst |diff| vs PHREEQC(P&B CO2):", r["worst_abs_vs_pb82"])
    print("water density Kell vs PHREEQC:", r["water_density_check"])
    print("model_identity_digest:", r["model_identity_digest"])
