"""Run the carbonate benchmark grid through the SmartChem model (`carbonate_equilibrium.solve`).

Read-only against the repo module.  Runs each case under BOTH the ideal and the Davies activity model and records
pH (the activity pH is the one compared to PHREEQC), speciation, verdict, and any refusal.  Writes
`code_results.json`.  Run from the repo (sandbox) venv; it only needs numpy/scipy.

Usage:  PYTHONPATH=<repo-root> python run_code.py
"""
import json
import os

from experiments.sandbox_foundation.aqueous_equilibrium import (
    NumericalVerificationError,
    OutOfSourceDomainError,
)
from experiments.sandbox_foundation.carbonate_equilibrium import CarbonateWaterSystem, solve

HERE = os.path.dirname(os.path.abspath(__file__))


def _solve_case(c, activity_model):
    kw = {"mode": c["mode"], "activity_model": activity_model, "sodium_M": c["sodium"]}
    if c["mode"] == "open":
        kw["p_co2_atm"] = c["p_co2_atm"]
    else:
        kw["total_carbon_M"] = c["total_carbon"]
    try:
        r = solve(CarbonateWaterSystem(**kw))
    except (NumericalVerificationError, OutOfSourceDomainError) as e:
        return {"refused": type(e).__name__, "reason": str(e)[:160]}
    return {
        "pH": r.pH, "pH_activity": r.pH_activity, "pH_concentration": r.pH_concentration,
        "I": r.ionic_strength_M, "verdict": r.verdict,
        "co2aq": r.co2aq_M, "hco3": r.hco3_M, "co3": r.co3_M, "oh": r.oh_minus_M,
        "total_dissolved_carbon": r.total_dissolved_carbon_M, "p_co2_atm": r.p_co2_atm,
        "gamma1": r.gamma_monovalent, "gamma2": r.gamma_divalent,
        "charge_balance_residual": r.charge_balance_residual, "caveats": list(r.caveats),
    }


def main():
    grid = json.load(open(os.path.join(HERE, "grid.json")))
    out = {"cases": {}}
    for c in grid["cases"]:
        out["cases"][c["id"]] = {
            "mode": c["mode"], "desc": c["desc"],
            "ideal": _solve_case(c, "ideal"), "davies": _solve_case(c, "davies"),
        }
    with open(os.path.join(HERE, "code_results.json"), "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    print(f"wrote code_results.json ({len(out['cases'])} cases)")


if __name__ == "__main__":
    main()
