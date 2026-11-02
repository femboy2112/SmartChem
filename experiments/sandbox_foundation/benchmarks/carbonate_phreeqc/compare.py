"""Compare the SmartChem carbonate model to PHREEQC and write the committed reference `comparison_table.json`.

Metric (PRE-REGISTERED, PREREGISTRATION.md section 5): dpH = |pH_activity(code, davies) - pH(PHREEQC)|.  The code
side's PRIMARY comparison is the Davies activity pH (both sides nonideal); the ideal pH is reported for context.
Classification thresholds, fixed before the comparison and justified by the activity-model difference (a Davies vs a
WATEQ/Debye-Huckel model on solutions up to I ~ 0.3 differs by O(0.1) pH by construction):
    AGREE    dpH <= 0.05
    MARGINAL dpH <= 0.15
    DIVERGE  dpH  > 0.15
This is VERIFICATION (did we solve the same equations right?), NOT independent experimental validation -- PHREEQC and
the model share the carbonic-acid constant lineage, so agreement corroborates the SOLVER, not the constants.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
AGREE_MAX = 0.05
MARGINAL_MAX = 0.15


def classify(dph):
    return "AGREE" if dph <= AGREE_MAX else ("MARGINAL" if dph <= MARGINAL_MAX else "DIVERGE")


def main():
    ph = json.load(open(os.path.join(HERE, "phreeqc_results.json")))
    code = json.load(open(os.path.join(HERE, "code_results.json")))
    rows = {}
    worst = 0.0
    for cid, pc in ph["cases"].items():
        cc = code["cases"][cid]
        dav = cc["davies"]
        if "refused" in dav:
            rows[cid] = {"desc": pc["desc"], "outcome": "CODE_REFUSED", "code_reason": dav["reason"],
                         "ph_phreeqc": pc["pH"]}
            continue
        dph = abs(dav["pH_activity"] - pc["pH"])
        worst = max(worst, dph)
        rows[cid] = {
            "desc": pc["desc"],
            "ph_phreeqc": pc["pH"], "I_phreeqc": pc["I"],
            "ph_code_davies": dav["pH_activity"], "ph_code_ideal": cc["ideal"].get("pH"),
            "I_code_davies": dav["I"],
            "dpH": dph, "class": classify(dph),
        }
    table = {
        "metric": "dpH = |pH_activity(code, davies) - pH(PHREEQC)|",
        "database": ph["database"], "database_sha256": ph["database_sha256"],
        "thresholds": {"AGREE_max": AGREE_MAX, "MARGINAL_max": MARGINAL_MAX},
        "rung": "VERIFICATION (shared constant lineage; not independent experimental validation)",
        "worst_dpH": worst,
        "rows": rows,
    }
    with open(os.path.join(HERE, "comparison_table.json"), "w") as f:
        json.dump(table, f, indent=2, allow_nan=False)
    print(f"wrote comparison_table.json; worst dpH = {worst:.4f}")
    for cid, r in rows.items():
        if "dpH" in r:
            print(f"  {cid:3s} {r['desc']:42s} phreeqc={r['ph_phreeqc']:.3f} code={r['ph_code_davies']:.3f} "
                  f"dpH={r['dpH']:.4f} {r['class']}")
        else:
            print(f"  {cid:3s} {r['desc']:42s} {r['outcome']}")


if __name__ == "__main__":
    main()
