"""Merge the PHREEQC reference pH into comparison_table.json for the MIXED benchmark.

There was no compare.py here; Toxic Rick wrote one. Metric and thresholds are PRE-REGISTERED
(PREREGISTRATION.md:44-47) and fixed BEFORE the data, not tuned to it:
    abs_dpH = |code pH_activity(davies) - PHREEQC pH(molar-matched)|, PER DATABASE
    AGREE <= 0.02 . MARGINAL <= 0.05 . DIVERGE > 0.05   (glass-electrode resolution scale)
A "domain of agreement" = cases the code ADMITS that AGREE vs BOTH databases.

This is solver / activity-model VERIFICATION, common-mode on the shared Ka/K1/K2/Kw lineage --
NOT independent measured-chemistry validation (PREREGISTRATION.md:51-56). The acetate
compare.py's %7.2f-on-None crash is deliberately NOT inherited: every print goes through a
None-safe formatter, so a null column prints "None", it does not take the whole run down.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGREE_MAX = 0.02
MARGINAL_MAX = 0.05
SOLVED = "SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL"


def classify(d):
    if d is None:
        return None
    return "AGREE" if d <= AGREE_MAX else ("MARGINAL" if d <= MARGINAL_MAX else "DIVERGE")


def _f(x):
    return "   None" if x is None else f"{x:7.4f}"


def main():
    ph = json.loads((HERE / "phreeqc_results.json").read_text())
    code = json.loads((HERE / "code_results.json").read_text())
    databases = list(ph["databases"].keys())

    # PHREEQC molar-matched pH indexed by (case, db) -- molar-matched is the code's own basis.
    phmap = {(r["case"], r["db"]): r for r in ph["cases"] if r["units"] == "molar-matched"}

    rows = {}
    for cid, cc in code["cases"].items():
        dav = cc["davies"]
        code_pH = dav.get("pH")
        code_verdict = dav.get("verdict", dav.get("refused"))
        ph_pH, ph_I, dpH, cls = {}, {}, {}, {}
        for db in databases:
            p = phmap.get((cid, db))
            ph_pH[db] = p["pH"] if p else None
            ph_I[db] = p["I_molal"] if p else None
            dpH[db] = abs(code_pH - p["pH"]) if (p and code_pH is not None) else None
            cls[db] = classify(dpH[db])
        rows[cid] = {
            "desc": cc["desc"], "C_Ac": cc["C_Ac"], "C_C": cc["C_C"], "Na": cc["Na"],
            "code_pH_davies": code_pH,
            "code_verdict_davies": code_verdict,
            "hp_tier_davies": dav.get("hp_cross_check", {}).get("tier"),
            "phreeqc_pH": ph_pH,
            "phreeqc_I_molal": ph_I,
            "abs_dpH": dpH,
            "phreeqc_class": cls,
        }

    # Domain of agreement: code ADMITS it (verdict SOLVED) AND it AGREEs vs BOTH databases.
    # A code-demoted case (M11, NUMERICALLY_UNVERIFIED) is reported but NEVER counted here.
    admitted = [cid for cid, r in rows.items() if r["code_verdict_davies"] == SOLVED]
    agree_both = [cid for cid in admitted
                  if all(rows[cid]["phreeqc_class"][db] == "AGREE" for db in databases)]
    demoted = [cid for cid, r in rows.items() if r["code_verdict_davies"] != SOLVED]

    table = {
        "target": "experiments/sandbox_foundation/coupled_equilibrium.py :: VinegarBicarbonateSystem.solve",
        "reference_solver": f"PHREEQC via phreeqpython ({', '.join(databases)}; minteq.v4 primary)",
        "reference_status": "BENCHMARKED_AGAINST_REFERENCE_SOLVER",
        "status_caveat": (
            "Solver / activity-model CORROBORATION ONLY. PHREEQC and this model share the "
            "Ka/K1/K2/Kw thermodynamic lineage, so agreement is COMMON-MODE on the constants: it "
            "verifies the SOLVER, not the chemistry. This is NOT measured-chemistry validation -- "
            "that would require a MEASURED mixed vinegar/bicarbonate pH with defensible provenance; "
            "none is used and none is back-computed from the code's constants. External "
            "(experimental) validation remains UNKNOWN."),
        "metric": "abs_dpH = |code pH_activity(davies) - PHREEQC pH(molar-matched)|, per database",
        "thresholds": {"AGREE_max": AGREE_MAX, "MARGINAL_max": MARGINAL_MAX, "rule": "DIVERGE > MARGINAL_max"},
        "databases": {db: {"sha256": ph["databases"][db]["database_sha256"],
                           "role": ("primary" if "minteq" in db else "secondary")} for db in databases},
        "molar_match": "fixed point on mol/kgw input until sum-of-species molarity reproduces requested mol/L (PREREGISTRATION.md:39-41)",
        "domain_of_agreement": {
            "definition": "code verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL AND class == AGREE vs BOTH databases",
            "cases": agree_both,
            "code_demoted_excluded": demoted,
        },
        "rows": rows,
    }
    (HERE / "comparison_table.json").write_text(json.dumps(table, indent=2, allow_nan=False))

    print(f"wrote comparison_table.json; domain of agreement (AGREE vs BOTH DBs) = {agree_both or 'EMPTY'}")
    for cid, r in rows.items():
        seg = " | ".join(f"{db.split('.dat')[0]}: ph={_f(r['phreeqc_pH'][db])} dpH={_f(r['abs_dpH'][db])} {str(r['phreeqc_class'][db]):8s}"
                         for db in databases)
        print(f"  {cid:4s} C_Ac={r['C_Ac']:<5g} C_C={r['C_C']:<5g} Na={r['Na']:<5g} code={_f(r['code_pH_davies'])} || {seg} [{r['code_verdict_davies']}]")


if __name__ == "__main__":
    main()
