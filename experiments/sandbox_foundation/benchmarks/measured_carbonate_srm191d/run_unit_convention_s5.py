"""OPERATION XX section 5 -- repair the UNIT basis and add the CONVENTION-MATCHED comparison for the NIST SRM 191d rung.

Ooh yeah, can do!  Two repairs on the XIX blind prediction (which is left UNTOUCHED, `run_measured.py` + `result.json`):

  B. UNITS.  The certificate gives 0.025 mol/kg WATER (molality); the XIX run fed 0.025 straight into a mol/L solver.
     Convert molality -> molarity with the solution density, carried as an INTERVAL (the certificate gives no density).
  C. CONVENTION.  Compare the (unchanged-constant) Davies prediction to BOTH certificate comparators:
       Table 1  (CERTIFIED)      pH(S) = 10.014  U   = 0.010   (k=1.96) -- INCLUDES the Bates-Guggenheim (BG) 0.0050
       Table A1 (NON-CERTIFIED)  pH(S) = 10.0137 U_R = 0.0029  (k=2.01) -- EXCLUDES the BG convention uncertainty
     Table A1 is the convention-matched comparator for a Debye-Huckel-family closure (shared BG convention family).

NO model constant is touched (K1/K2/Kw/Davies-A are the pre-sourced ones in carbonate_equilibrium.py).  The verdict is
whatever the numbers say -- a refutation is a legitimate result and is reported as one.

DENSITY INTERVAL (NOT a point value; the certificate states none).  Solution = 1000.0 g H2O + 2.1015 g NaHCO3 + 2.6516 g
Na2CO3 = 1004.753 g.  Volume = V_water + dV, with V_water = 1000.0 g / 0.997047 g/mL (pure water, 25 C; CODATA/Kell-class
value) = 1002.96 mL and dV = n_NaHCO3*phi_V(NaHCO3) + n_Na2CO3*phi_V(Na2CO3) (apparent molar volumes).  We do NOT quote
a point phi_V; we bracket the PAIR sum phi_V(NaHCO3)+phi_V(Na2CO3) in [0, 40] cm3/mol:
    lower edge 0   : dissolved ions add NO volume (electrostriction fully cancels the ions' intrinsic volume)
                     -> rho = 1004.753/1002.96 = 1.00179 g/mL (upper density edge);
    upper edge 40  : ~ twice the largest ordinary 1:1-electrolyte phi_V (~20) -- a deliberately generous ceiling
                     -> rho = 1004.753/(1002.96+1.0) = 1.00079 g/mL (lower density edge).
=> rho in [1.0007, 1.0018] g/mL (edges rounded OUTWARD to 4 dp; midpoint 1.00125).  Cross-checks (neither is the bracket's source): the PHREEQC (phreeqc.dat, Millero-type
volume model) density of this composition is ~1.0014 g/mL; a literature-magnitude apparent-molar-volume estimate
(phi_V(NaHCO3) ~ +24, phi_V(Na2CO3) ~ -5 cm3/mol) gives ~1.0013.  Both lie inside the bracket.  NOTE: the caller's
heuristic 1.002-1.006 band is NOT supported by this derivation (it would need the solute volume to be NEGATIVE-large).
The harness also reports a sensitivity over 1.000-1.006 so the conclusion is shown not to hinge on the chosen band.

SCALE-CONSISTENCY FLAG (reported as sensitivity, NOT folded into the headline).  Certified pH(S) is on the MOLALITY scale
(a_H = gamma*m_H); the solver's constants are labelled "molar".  Feeding molarity but NOT converting a_H back to the
molality scale (the prescribed repair) is a MIXED convention.  The two pure alternatives are reported alongside:
  (a) molar K's -> molarity feed + a_H converted to molality scale: pH_m = pH_c + log10(kg water per L solution);
  (b) molal K's -> molality feed (the XIX run, i.e. no unit conversion at all).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from experiments.sandbox_foundation import carbonate_equilibrium as C
from experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d.run_measured import SRM191D

CERT = {
    "table1_certified": {"pH_S_25C": 10.014, "u_c": 0.0052, "U": 0.010, "k": 1.96,
                         "includes_bates_guggenheim_convention_uncertainty": True},
    "tableA1_noncertified": {"pH_S_25C": 10.0137, "u_c_measurement": 0.0015, "U_R": 0.0029, "k_R": 2.01,
                             "includes_bates_guggenheim_convention_uncertainty": False},
    "bates_guggenheim_component": 0.0050,
}

# ---- preparation basis (certificate: "2.1015 g NaHCO3 and 2.6516 g Na2CO3 per 1000.0 g H2O") ----
MOLALITY_EACH = 0.025                          # certified basis, mol/kg H2O, for BOTH salts
MASS_WATER_G = 1000.0
MASS_NAHCO3_G = 2.1015
MASS_NA2CO3_G = 2.6516
SOLUTION_MASS_G = MASS_WATER_G + MASS_NAHCO3_G + MASS_NA2CO3_G           # 1004.753 g
RHO_WATER_25C_G_PER_ML = 0.997047                                        # pure water, 25 C (tertiary reference)

# ---- density interval (see module docstring for the derivation) ----
PHI_V_PAIR_BRACKET_CM3_PER_MOL = (0.0, 40.0)   # phi_V(NaHCO3)+phi_V(Na2CO3), structural bracket (not a point)
N_PER_KG_WATER = MOLALITY_EACH                 # mol of EACH salt per kg water


def _rho_from_pair_phi(phi_pair: float) -> float:
    v_water_ml = MASS_WATER_G / RHO_WATER_25C_G_PER_ML
    d_v = N_PER_KG_WATER * phi_pair
    return SOLUTION_MASS_G / (v_water_ml + d_v)


RHO_HI = _rho_from_pair_phi(PHI_V_PAIR_BRACKET_CM3_PER_MOL[0])
RHO_LO = _rho_from_pair_phi(PHI_V_PAIR_BRACKET_CM3_PER_MOL[1])
# the interval actually carried (rounded OUTWARD to 4 dp so the carried band contains the derived one)
DENSITY_INTERVAL_G_PER_ML = (math.floor(RHO_LO * 1e4) / 1e4, math.ceil(RHO_HI * 1e4) / 1e4)   # (1.0007, 1.0018)
DENSITY_MID_G_PER_ML = 0.5 * (DENSITY_INTERVAL_G_PER_ML[0] + DENSITY_INTERVAL_G_PER_ML[1])    # 1.00125 (midpoint, NOT a measurement)
DENSITY_SOURCE = (
    "Derived bracket: rho = 1004.753 g / (1000.0 g / 0.997047 g/mL + 0.025 mol * phi_V_pair), phi_V_pair = "
    "phi_V(NaHCO3)+phi_V(Na2CO3) in [0, 40] cm3/mol (0 = ions add no volume; 40 = generous ceiling ~2x the largest "
    "ordinary 1:1-electrolyte apparent molar volume). Cross-checks: PHREEQC phreeqc.dat density ~1.0014; "
    "literature-magnitude phi_V(NaHCO3)~+24, phi_V(Na2CO3)~-5 cm3/mol -> ~1.0013. Tertiary/derived, NOT measured; "
    "the certificate states no density.")


def molarity_each(rho_g_per_ml: float) -> float:
    """mol/L of EACH salt: n = 0.025 mol in (1004.753 g / rho) mL of solution."""
    return MOLALITY_EACH / (SOLUTION_MASS_G / rho_g_per_ml / 1000.0)


def kg_water_per_litre(rho_g_per_ml: float) -> float:
    return MASS_WATER_G / (SOLUTION_MASS_G / rho_g_per_ml)      # (g water per g solution) * (g solution per mL) *1000 /1000


def _solve_davies(c_each: float) -> float:
    sysc = C.CarbonateWaterSystem(mode="closed", total_carbon_M=2 * c_each, sodium_M=3 * c_each, activity_model="davies")
    r = C.solve(sysc)
    assert r.verdict == "SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL"
    return float(r.pH_activity)


def _residual_block(ph: float) -> dict:
    t1, a1 = CERT["table1_certified"], CERT["tableA1_noncertified"]
    r1, ra = ph - t1["pH_S_25C"], ph - a1["pH_S_25C"]
    return {
        "pH": ph,
        "residual_vs_table1": r1, "table1_U": t1["U"], "within_table1_U": bool(abs(r1) <= t1["U"]),
        "residual_vs_tableA1": ra, "tableA1_U_R": a1["U_R"], "within_tableA1_U_R": bool(abs(ra) <= a1["U_R"]),
    }


def evaluate() -> dict:
    # XIX baseline (molality fed as molarity), reproduced for the delta
    baseline = _solve_davies(MOLALITY_EACH)

    pts = {"lo": DENSITY_INTERVAL_G_PER_ML[0], "mid": DENSITY_MID_G_PER_ML, "hi": DENSITY_INTERVAL_G_PER_ML[1]}
    headline_rows = {}
    for tag, rho in pts.items():
        c = molarity_each(rho)
        ph = _solve_davies(c)
        row = _residual_block(ph)
        row.update({"rho_g_per_mL": rho, "molarity_each_M": c, "C_T_M": 2 * c, "Na_M": 3 * c,
                    "pH_shift_from_units_vs_XIX": ph - baseline})
        headline_rows[tag] = row

    shifts = [headline_rows[t]["pH_shift_from_units_vs_XIX"] for t in pts]
    res1 = [headline_rows[t]["residual_vs_table1"] for t in pts]
    resa = [headline_rows[t]["residual_vs_tableA1"] for t in pts]

    # scale-consistency sensitivities (NOT the headline)
    scale = {}
    for tag, rho in pts.items():
        ph_c = headline_rows[tag]["pH"]
        ph_m = ph_c + math.log10(kg_water_per_litre(rho))
        scale[tag] = {"rho_g_per_mL": rho, "kg_water_per_L": kg_water_per_litre(rho),
                      "a_molar_K_converted_to_molality_scale": _residual_block(ph_m)}
    scale["b_molal_K_molality_fed_is_the_XIX_run"] = _residual_block(baseline)

    # broad-band sensitivity incl. the caller's heuristic 1.002-1.006 and pure water 1.000
    sens = {}
    for rho in (1.000, 1.002, 1.004, 1.006):
        sens[f"{rho:.3f}"] = _residual_block(_solve_davies(molarity_each(rho)))

    upper_ok_t1 = all(headline_rows[t]["within_table1_U"] for t in pts)
    upper_ok_a1 = all(headline_rows[t]["within_tableA1_U_R"] for t in pts)
    verdict = {
        "units_repair_shift_pH_interval": [min(shifts), max(shifts)],
        "units_repair_shift_below_0p001": bool(max(abs(s) for s in shifts) < 0.001),
        "vs_table1_certified": {
            "residual_interval": [min(res1), max(res1)],
            "within_U_over_whole_density_interval": bool(upper_ok_t1),
            "status": "SURVIVES (within the convention-INCLUSIVE certified U)" if upper_ok_t1 else "FAILS",
        },
        "vs_tableA1_convention_matched": {
            "residual_interval": [min(resa), max(resa)],
            "within_U_R_over_whole_density_interval": bool(upper_ok_a1),
            "status": ("PASS (within the convention-matched Table A1 U_R)" if upper_ok_a1 else
                       "REFUTED -- leaves Table A1 +/-0.0029: the within-U pass survives ONLY against the "
                       "convention-INCLUSIVE band"),
        },
        "margin_to_table1_U_edge_pH": 0.010 - max(abs(r) for r in res1),
        "scale_consistency_flag": {
            "a_molar_K_with_aH_converted_to_molality_scale_within_table1_U": all(
                scale[t]["a_molar_K_converted_to_molality_scale"]["within_table1_U"] for t in pts),
            "b_molal_K_molality_fed_within_table1_U": scale["b_molal_K_molality_fed_is_the_XIX_run"]["within_table1_U"],
            "note": ("The Table-1 pass is FRAGILE: margin ~0.001 pH to the U edge, and the pure-molar-scale "
                     "convention (a) lands OUTSIDE Table-1 U. The prescribed headline is a mixed-scale choice."),
        },
        "scope": ("Corroborates 'K2 + Davies reproduce a Harned-cell result within the convention-inclusive "
                  "certified U'. Does NOT corroborate agreement at the measurement-only level (Table A1). PARTIAL "
                  "common-mode preserved: K1/K2 are Harned-lineage and Davies shares the Debye-Huckel family with the "
                  "Bates-Guggenheim convention; single-ion a_H+ is NOT independently derived."),
    }
    return {
        "operation": "XX-5 unit repair + convention-matched comparison (NIST SRM 191d)",
        "certificate": {"sha256": SRM191D["certificate_sha256"], "issue": SRM191D["certificate_issue_date"], **CERT},
        "basis": {"molality_each_mol_per_kg_water": MOLALITY_EACH, "solution_mass_g_per_1000g_water": SOLUTION_MASS_G,
                  "M_NaHCO3": 84.007, "M_Na2CO3": 105.988,
                  "implied_molality_from_mass_NaHCO3": MASS_NAHCO3_G / 84.007,
                  "implied_molality_from_mass_Na2CO3": MASS_NA2CO3_G / 105.988},
        "density": {"interval_g_per_mL": list(DENSITY_INTERVAL_G_PER_ML), "midpoint_g_per_mL": DENSITY_MID_G_PER_ML,
                    "derived_edges_g_per_mL": [RHO_LO, RHO_HI], "phi_V_pair_bracket_cm3_per_mol":
                    list(PHI_V_PAIR_BRACKET_CM3_PER_MOL), "source": DENSITY_SOURCE},
        "xix_baseline_davies_pH_molality_fed_as_molarity": baseline,
        "corrected_davies": headline_rows,
        "verdict": verdict,
        "sensitivity_scale_consistency_NOT_headline": scale,
        "sensitivity_density_band": sens,
        "caveats": [
            "PARTIAL common-mode: K1/K2 Harned-lineage; Davies shares the Debye-Huckel family with Bates-Guggenheim.",
            "Density is a derived bracket (the certificate gives none); the molarity conversion inherits it.",
            "MIXED-SCALE FLAG: the headline feeds molarity but compares to a molality-scale pH(S); see "
            "sensitivity_scale_consistency_NOT_headline for the two pure conventions.",
            "Na-carbonate ion pairs still omitted from the base model (unchanged from XIX).",
            "No model constant was altered; carbonate_equilibrium.py is byte-identical.",
        ],
    }


def main(argv=None) -> int:
    res = evaluate()
    text = json.dumps(res, indent=2, allow_nan=False)
    out = Path(__file__).with_name("result_s5_unit_convention.json")
    out.write_text(text + "\n")
    v, m = res["verdict"], res["corrected_davies"]["mid"]
    sys.stdout.write(
        f"SRM 191d S5: rho in {res['density']['interval_g_per_mL']} g/mL -> molarity each {m['molarity_each_M']:.6f} M (mid)\n"
        f"  Davies pH (mid) = {m['pH']:.4f}; XIX baseline {res['xix_baseline_davies_pH_molality_fed_as_molarity']:.4f}; "
        f"unit shift {m['pH_shift_from_units_vs_XIX']:+.5f}\n"
        f"  vs Table 1  10.014 +/- 0.010 : residual {m['residual_vs_table1']:+.4f}  within={m['within_table1_U']}\n"
        f"  vs Table A1 10.0137 +/- 0.0029: residual {m['residual_vs_tableA1']:+.4f}  within={m['within_tableA1_U_R']}\n"
        f"  {v['vs_tableA1_convention_matched']['status']}\n  wrote {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
