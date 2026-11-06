"""OPERATION XXI section 4 -- separate the NIST SRM 191d comparison into THREE explicit comparators and a claim ledger.

XX-5 repaired the units and added the convention-matched Table A1 comparison, but kept the scale-transported basis in a
"NOT headline" sensitivity block.  XXI-4 promotes it to a first-class comparator, because that is where the decisive
scientific finding lives: the Table-1 "pass" is CONTINGENT on an unresolved standard-state (molar vs molal) scale
convention for the model's equilibrium constants.

This harness changes NO model constant -- it reuses the XX-5 harness's computations verbatim (same unchanged Davies
prediction from carbonate_equilibrium.py) and only RE-FRAMES them into three comparators with an explicit claim ledger
(what was measured / modeled / transported / assumed / which uncertainty was retained / passes / refuted / corroborated
/ which measurement would decide the remaining ambiguity).  carbonate_equilibrium.py is byte-identical; smartchem/ is
untouched (asserted by test_xxi_s4_three_comparators.py via git).

THE THREE COMPARATORS (all against the SAME unchanged Davies prediction; densities over the XX-5 derived interval):
  A  Table 1   (certified, convention-INCLUSIVE)  10.014  +/- U   = 0.010   -- includes the Bates-Guggenheim convention
  B  Table A1  (non-certified, convention-MATCHED) 10.0137 +/- U_R = 0.0029  -- excludes the BG convention uncertainty
  C  Table 1 under a SCALE-CONSISTENT transport    10.014  +/- U   = 0.010   -- model a_H transported to the MOLALITY
     scale (the pH(S) scale), i.e. the molar-K reading made self-consistent instead of the prescribed mixed-scale one.

A and B share the model's PRESCRIBED (mixed-scale) prediction; C transports it to the measurement's scale.  The point
of C is that the measurement-level verdict FLIPS with a convention the sources do not pin down.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d import run_unit_convention_s5 as S5


def _interval(vals):
    return [min(vals), max(vals)]


def _verdict_vs(residuals, U):
    """Given residuals over the density interval and an expanded uncertainty U, is |residual| <= U everywhere?"""
    worst = max(abs(r) for r in residuals)
    return {"residual_interval_pH": _interval(residuals), "worst_abs_residual_pH": worst,
            "U_pH": U, "within_U_over_interval": bool(worst <= U), "abs_residual_over_U": worst / U}


def evaluate() -> dict:
    pts = {"lo": S5.DENSITY_INTERVAL_G_PER_ML[0], "mid": S5.DENSITY_MID_G_PER_ML, "hi": S5.DENSITY_INTERVAL_G_PER_ML[1]}

    # --- the model's PRESCRIBED (mixed-scale) prediction: molarity fed, compared to a molality-scale pH(S) (A, B) ---
    ph_mixed = {t: S5._solve_davies(S5.molarity_each(rho)) for t, rho in pts.items()}
    # --- the SCALE-CONSISTENT transport for comparator C: molar-K reading -> transport a_H onto the molality scale ---
    #     pH_m = pH_c + log10(kg water per litre of solution).  (The alternative molal-K reading is the XIX run.)
    import math
    ph_transported = {t: ph_mixed[t] + math.log10(S5.kg_water_per_litre(pts[t])) for t in pts}
    ph_molal_K_reading = S5._solve_davies(S5.MOLALITY_EACH)   # molal K's + molality fed == the XIX run (no unit conv.)

    t1, a1 = S5.CERT["table1_certified"], S5.CERT["tableA1_noncertified"]
    T1, A1 = t1["pH_S_25C"], a1["pH_S_25C"]
    U1, UR = t1["U"], a1["U_R"]

    res_A = [ph_mixed[t] - T1 for t in pts]
    res_B = [ph_mixed[t] - A1 for t in pts]
    res_C = [ph_transported[t] - T1 for t in pts]
    res_C_molalK = ph_molal_K_reading - T1

    comparators = {
        "A_table1_certified_convention_inclusive": {
            "what_measured": "NIST SRM 191d certified pH(S) = 10.014, Harned cell, molality scale, 25 C.",
            "what_modeled": "Davies-closure carbonate speciation (carbonate_equilibrium.py, UNCHANGED constants), "
                            "0.025 mol/kg each NaHCO3/Na2CO3 fed as molarity via the XX-5 density interval.",
            "what_transported": "NONE beyond the molality->molarity unit conversion; a_H left on the solver's scale "
                                "and compared directly to the molality-scale pH(S) (a MIXED-scale comparison).",
            "what_assumed": "the model 'molar' K's may be compared to a molality-scale pH(S) without transporting a_H; "
                            "density interval [1.0007,1.0018] g/mL (derived bracket, not measured).",
            "uncertainty_retained": "the FULL certified U = 0.010 (k=1.96), which INCLUDES the Bates-Guggenheim "
                                    "convention component 0.0050.",
            "comparison": _verdict_vs(res_A, U1),
            "passes": bool(max(abs(r) for r in res_A) <= U1),
            "conclusion": None,   # filled below
        },
        "B_tableA1_noncertified_convention_matched": {
            "what_measured": "NIST SRM 191d Table A1 pH(S) = 10.0137 with the BG convention uncertainty REMOVED.",
            "what_modeled": "identical to A (same mixed-scale Davies prediction).",
            "what_transported": "NONE beyond units; same mixed-scale comparison as A.",
            "what_assumed": "Table A1 is the convention-matched comparator for a Debye-Huckel-family closure (both "
                            "share the BG convention family), so removing BG slack from the measurement side is the "
                            "like-for-like test; NOT reclassified as an independent measurement.",
            "uncertainty_retained": "U_R = 0.0029 (k_R=2.01), EXCLUDING the BG convention uncertainty.",
            "comparison": _verdict_vs(res_B, UR),
            "passes": bool(max(abs(r) for r in res_B) <= UR),
            "conclusion": None,
        },
        "C_table1_scale_transported": {
            "what_measured": "NIST SRM 191d certified pH(S) = 10.014 (molality scale), as in A.",
            "what_modeled": "same Davies prediction, but made SCALE-CONSISTENT: taking the model K's at their 'molar' "
                            "label at face value, a_H is transported onto the molality scale "
                            "(pH_m = pH_c + log10(kg water / L)) before comparison.",
            "what_transported": "the proton activity from the molar (per-litre) scale to the molality (per-kg-water) "
                                "scale -- the step the prescribed mixed-scale headline omitted.",
            "what_assumed": "the labelled 'molar' standard state is taken literally; the alternative is that K1/K2 are "
                            "actually MOLAL-scale (their Harned-cell provenance), under which the consistent prediction "
                            "is the XIX molality-fed run (pH 10.00479) -- see conclusion.",
            "uncertainty_retained": "the FULL certified U = 0.010 (same band as A), so only the SCALE changed vs A.",
            "comparison": _verdict_vs(res_C, U1),
            "passes": bool(max(abs(r) for r in res_C) <= U1),
            "alternative_molal_K_reading": {
                "pH": ph_molal_K_reading, "residual_vs_table1": res_C_molalK,
                "within_table1_U": bool(abs(res_C_molalK) <= U1),
                "note": "molal K's + molality fed (the XIX run): survives Table 1 thinly (margin ~0.001 pH).",
            },
            "conclusion": None,
        },
    }

    # --- fill the per-comparator conclusions (refuted / corroborated / decisive next measurement) ---
    comparators["A_table1_certified_convention_inclusive"]["conclusion"] = {
        "corroborated": "K2 + Davies reproduce a Harned-cell pH within the convention-INCLUSIVE certified U (thinly, "
                        "margin ~0.0011 pH).",
        "refuted": None,
        "decisive_next_measurement": "tighten or replace the density assumption with a measured solution density; "
                                     "resolve the K-scale (comparator C) -- the pass is scale-contingent.",
    }
    comparators["B_tableA1_noncertified_convention_matched"]["conclusion"] = {
        "corroborated": None,
        "refuted": "agreement at the MEASUREMENT-ONLY level (~0.003 pH): the model sits ~0.0086 pH below Table A1, "
                   "~3x U_R.  The A pass exists ONLY because the BG convention slack (0.0050) is in A's band.",
        "decisive_next_measurement": "an independent single-ion a_H+ determination not sharing the BG convention, or a "
                                     "second measured buffer on a convention that the model does not also assume.",
    }
    _C = comparators["C_table1_scale_transported"]
    _C["conclusion"] = {
        "corroborated": None,
        "refuted": ("under the 'molar' K label taken at face value, scale-consistency REFUTES even Table 1 "
                    f"(residual ~{res_C[1]:+.4f} pH, |.|>{U1}); the measurement-level corroboration in A is "
                    "convention-and-scale-CONTINGENT, surviving only under the molal-K reading."),
        "decisive_next_measurement": ("resolve the standard-state SCALE (molar vs molal) of K1/K2 in "
                                      "carbonate_equilibrium.py from their primary Harned-cell source; that single "
                                      "fact decides whether the model survives (molal) or is refuted (molar) vs Table 1."),
    }

    overall = {
        "A_within_table1_U": comparators["A_table1_certified_convention_inclusive"]["passes"],
        "B_within_tableA1_U_R": comparators["B_tableA1_noncertified_convention_matched"]["passes"],
        "C_within_table1_U_under_molar_label": _C["passes"],
        "C_within_table1_U_under_molal_reading": _C["alternative_molal_K_reading"]["within_table1_U"],
        "headline": ("SmartChem's SRM 191d corroboration is NOT a robust physical prediction: it holds only against "
                     "the convention-INCLUSIVE Table 1 (A), is REFUTED at the measurement-only Table A1 level (B), and "
                     "is REFUTED against Table 1 itself once the molar-K scale is made self-consistent (C).  The single "
                     "unresolved fact that decides the measurement-level verdict is the standard-state SCALE of K1/K2."),
        "no_constant_tuned": True,
        "common_mode": ("PARTIAL: K1/K2 are Harned-lineage and Davies shares the Debye-Huckel family with the "
                        "Bates-Guggenheim convention; single-ion a_H+ is NOT independently derived -- agreement is not "
                        "an independent derivation of K2."),
    }

    return {
        "operation": "XXI-4 three-comparator separation + claim ledger (NIST SRM 191d)",
        "certificate": {"sha256": S5.SRM191D["certificate_sha256"], "issue": S5.SRM191D["certificate_issue_date"]},
        "model_predictions_pH": {
            "mixed_scale_molarity_fed_vs_molality_pH_S": ph_mixed,   # comparators A, B
            "scale_transported_molar_K_to_molality_scale": ph_transported,  # comparator C
            "molal_K_molality_fed_XIX_run": ph_molal_K_reading,
        },
        "density_interval_g_per_mL": list(S5.DENSITY_INTERVAL_G_PER_ML),
        "comparators": comparators,
        "overall": overall,
    }


def main(argv=None) -> int:
    res = evaluate()
    out = Path(__file__).with_name("result_s4_three_comparators.json")
    out.write_text(json.dumps(res, indent=2, allow_nan=False) + "\n")
    o = res["overall"]
    A = res["comparators"]["A_table1_certified_convention_inclusive"]["comparison"]
    B = res["comparators"]["B_tableA1_noncertified_convention_matched"]["comparison"]
    C = res["comparators"]["C_table1_scale_transported"]["comparison"]
    sys.stdout.write(
        "SRM 191d XXI-4 three comparators (no constant tuned):\n"
        f"  A Table 1  (incl. BG)   residual {A['residual_interval_pH']} vs U={A['U_pH']}  within={A['within_U_over_interval']}\n"
        f"  B Table A1 (excl. BG)   residual {B['residual_interval_pH']} vs U={B['U_pH']}  within={B['within_U_over_interval']}  -> REFUTED\n"
        f"  C Table 1  (scale-txp)  residual {C['residual_interval_pH']} vs U={C['U_pH']}  within={C['within_U_over_interval']}  -> REFUTED under molar-K; survives under molal-K\n"
        f"  {o['headline']}\n  wrote {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
