"""Run the MIXED vinegar/bicarbonate grid through the SmartChem coupled solver + the arbitrary-precision holdout.

Read-only against the repo modules.  For each case: solve the coupled closed system (ideal and Davies), attach the
high-precision cross-check tier (claim_tiers.NUMERICALLY_VERIFIED when the production float64 solve agrees with the
60-digit Decimal holdout), and record the expected refusal for the out-of-Davies-domain case.  Writes
`code_results.json` (the code column) and `comparison_table.json` (code column filled; PHREEQC column null ==
EXTERNAL_VALIDATION_UNAVAILABLE -- never a fabricated reference).

Usage:  PYTHONPATH=<repo-root> python run_code.py
"""
from __future__ import annotations

import json
import os

from cases import CASES

from experiments.sandbox_foundation.aqueous_equilibrium import (
    NumericalVerificationError,
    OutOfSourceDomainError,
)
from experiments.sandbox_foundation.coupled_equilibrium import VinegarBicarbonateSystem, solve
from experiments.sandbox_foundation.coupled_reference_hp import cross_check

HERE = os.path.dirname(os.path.abspath(__file__))


def _solve(c_ac, c_c, na, activity_model):
    try:
        sysm = VinegarBicarbonateSystem(total_acetate_M=c_ac, total_carbon_M=c_c, sodium_M=na,
                                        activity_model=activity_model)
        r = solve(sysm)
    except (NumericalVerificationError, OutOfSourceDomainError) as e:
        return {"refused": type(e).__name__, "reason": str(e)[:160]}
    rec = {
        "pH": r.pH, "pH_activity": r.pH_activity, "pH_concentration": r.pH_concentration,
        "I": r.ionic_strength_M, "verdict": r.verdict,
        "hac": r.hac_M, "ac": r.ac_minus_M, "co2aq": r.co2aq_M, "hco3": r.hco3_M, "co3": r.co3_M,
        "oh": r.oh_minus_M, "gamma1": r.gamma_monovalent,
        "charge_balance_residual": r.charge_balance_residual,
        "carbon_conservation_residual": r.carbon_conservation_residual,
        "acetate_conservation_residual": r.acetate_conservation_residual,
        "caveats": list(r.caveats),
    }
    try:
        cc = cross_check(sysm)
        rec["hp_cross_check"] = {"delta_pH": cc.delta_pH, "rel_delta_h": cc.rel_delta_h, "tier": cc.tier}
    except Exception as e:   # the holdout is a diagnostic; its failure is recorded, never silently dropped
        rec["hp_cross_check"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    return rec


def main() -> None:
    out = {"cases": {}}
    table = {
        "target": "experiments/sandbox_foundation/coupled_equilibrium.py :: VinegarBicarbonateSystem.solve",
        "reference_solver": "PHREEQC (minteq.v4.dat primary, llnl.dat secondary)",
        "reference_status": "EXTERNAL_VALIDATION_UNAVAILABLE",
        "note": ("PHREEQC is absent on the committed baseline; the inputs/*.pqi decks are the reproducible probe. "
                 "The code column + the arbitrary-precision holdout tier are filled; the PHREEQC pH column is null "
                 "until an external run signs it (never fabricated)."),
        "rows": {},
    }
    for case_id, desc, c_ac, c_c, na, exp in CASES:
        ideal = _solve(c_ac, c_c, na, "ideal")
        davies = _solve(c_ac, c_c, na, "davies")
        out["cases"][case_id] = {"desc": desc, "C_Ac": c_ac, "C_C": c_c, "Na": na, "expectation": exp,
                                 "ideal": ideal, "davies": davies}
        table["rows"][case_id] = {
            "desc": desc, "C_Ac": c_ac, "C_C": c_c, "Na": na,
            "code_pH_davies": davies.get("pH"), "code_verdict_davies": davies.get("verdict",
                                                                                   davies.get("refused")),
            "hp_tier_davies": davies.get("hp_cross_check", {}).get("tier"),
            "phreeqc_pH": None, "abs_dpH": None,
        }
    with open(os.path.join(HERE, "code_results.json"), "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    with open(os.path.join(HERE, "comparison_table.json"), "w") as f:
        json.dump(table, f, indent=2, allow_nan=False)
    print(f"wrote code_results.json + comparison_table.json ({len(out['cases'])} cases)")


if __name__ == "__main__":
    main()
