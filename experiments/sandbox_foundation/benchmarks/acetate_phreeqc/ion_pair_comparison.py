"""Round VI ("The Salt Bridge") -- re-run the CODE side with the NaAc(aq) ion pair modeled and re-compare to the
COMMITTED PHREEQC-with-pair reference (comparison_table.json).

PHREEQC already INCLUDED the NaAc ion pair; its SOLUTION inputs and its two databases (minteq.v4 / llnl, pinned by
sha256 in README.md) are unchanged, and PHREEQC is deterministic -- so its pH values are the fixed external reference
and are reused verbatim here.  Only the SmartChem code side changed (adding include_ion_pair).  Hence NO PHREEQC
re-run, NO scratch venv, NO database refetch: this is pure numpy/scipy code plus a read of the committed reference.

Run:  python experiments/sandbox_foundation/benchmarks/acetate_phreeqc/ion_pair_comparison.py
It writes ion_pair_comparison.json and prints the table used in README.md.
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))   # repo root (contains experiments/)
from experiments.sandbox_foundation import aqueous_equilibrium as ae   # noqa: E402

HERE = Path(__file__).resolve().parent
REF = json.load(open(HERE / "comparison_table.json"))          # committed PHREEQC-with-pair reference


def _cls(d):
    return "AGREE" if d <= 0.02 else ("MARGINAL" if d <= 0.05 else "DIVERGE")


def code_pH(CT, Na, include_ion_pair):
    try:
        r = ae.solve(ae.AcetateWaterSystem(total_acetic_M=CT, sodium_M=Na, activity_model="davies",
                                           include_ion_pair=include_ion_pair))
        return r.pH, r.naac_M, r.verdict
    except Exception as e:                                     # a refused solve IS the recorded outcome
        return None, None, type(e).__name__


def main():
    rows = []
    hdr = ("%-16s %-9s | %8s | %8s %7s %-8s | %8s %7s %-8s | %7s %6s"
           % ("case", "DB", "pH_ph", "noPair", "dpH", "cls", "withPair", "dpH", "cls", "closed", "NaAc%"))
    print(hdr)
    print("-" * len(hdr))
    for r in REF:
        ph, CT, Na = r["pH_ph"], r["CT"], r["Na"]
        pn, _n, vn = code_pH(CT, Na, False)
        pp, naac, vp = code_pH(CT, Na, True)
        if pn is None or pp is None:
            print("%-16s %-9s | %8.4f | code refused (noPair=%s withPair=%s)" % (r["case"], r["db"], ph, vn, vp))
            rows.append(dict(case=r["case"], db=r["db"], CT=CT, Na=Na, pH_phreeqc_with_pair=ph,
                             code_no_pair=None, code_with_pair=None, refused_no_pair=vn, refused_with_pair=vp))
            continue
        dn, dp = abs(pn - ph), abs(pp - ph)
        frac = (naac / CT * 100.0) if CT > 0 else 0.0
        print("%-16s %-9s | %8.4f | %8.4f %7.4f %-8s | %8.4f %7.4f %-8s | %7.4f %6.1f"
              % (r["case"], r["db"], ph, pn, dn, _cls(dn), pp, dp, _cls(dp), dn - dp, frac))
        rows.append(dict(case=r["case"], db=r["db"], CT=CT, Na=Na, pH_phreeqc_with_pair=ph,
                         code_no_pair=pn, dpH_no_pair=dn, cls_no_pair=_cls(dn),
                         code_with_pair=pp, dpH_with_pair=dp, cls_with_pair=_cls(dp),
                         naac_M=naac, naac_frac_pct=frac, gap_closed=dn - dp))
    json.dump(rows, open(HERE / "ion_pair_comparison.json", "w"), indent=1)

    solved = [x for x in rows if x.get("code_with_pair") is not None]
    worst_no = max((x["dpH_no_pair"] for x in solved), default=0.0)
    worst_with = max((x["dpH_with_pair"] for x in solved), default=0.0)
    ndiv_no = sum(1 for x in solved if x["cls_no_pair"] == "DIVERGE")
    ndiv_with = sum(1 for x in solved if x["cls_with_pair"] == "DIVERGE")
    print("\nwrote ion_pair_comparison.json (%d rows)" % len(rows))
    print("HEADLINE: worst |dpH| no-pair = %.4f (%d DIVERGE) -> with-pair = %.4f (%d DIVERGE)"
          % (worst_no, ndiv_no, worst_with, ndiv_with))


if __name__ == "__main__":
    main()
