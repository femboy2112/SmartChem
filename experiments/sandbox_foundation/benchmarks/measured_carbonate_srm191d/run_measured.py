"""OPERATION XIX section 4 -- the first MEASURED-validation rung: the repo carbonate solver vs NIST SRM 191d.

A BLIND prediction: NO parameter is fit.  The model's 25 C constants (K1/K2/Kw, Davies-A) are all pre-sourced; the
carbonate closed-system solver is run at the SRM 191d buffer composition and compared to the CERTIFIED pH(S) of a
real primary (Harned-cell emf) measurement.  This is the first rung above reference-solver corroboration (PHREEQC):
a comparison to an actual instrument, not another model.

SOURCE (certified values read directly from the certificate, page 1 Table 1):
  NIST Standard Reference Material 191d -- Sodium Bicarbonate (191d-I) / Sodium Carbonate (191d-II) (pH Standard),
  Certificate of Analysis, NIST Office of Reference Materials; Date of Issue 05 February 2025; valid to 30 Nov 2032.
  URL: https://tsapps.nist.gov/srmext/certificates/191D.pdf
  SHA256 of the retrieved certificate PDF: ea316fb1368d0563882a2b6926fe8a6bb07736e9d5fc1b24bb70c2317cc02d38
  Buffer: 0.025 mol/kg NaHCO3 + 0.025 mol/kg Na2CO3, CO2-free, closed; pH(S) on the molality scale, p0 = 1 atm, by
  the primary Harned-cell (cells without liquid junction) method.  Certified pH(S) at 25 C = 10.014 (u_c = 0.0052,
  U = 0.010 at k = 1.96); u_c includes the Bates-Guggenheim convention uncertainty 0.0050 (the dominant component).

HONEST SCOPE (every claim inherits its weakest premise):
  * PARTIAL common-mode, not an independent derivation of K2.  Our K1/K2 trace to the Harned lineage; Davies is a
    Debye-Huckel-family single-ion-activity closure; the certified pH(S) uses the Bates-Guggenheim convention (also
    Debye-Huckel family), and that convention IS the certificate's dominant uncertainty (0.0050 pH).  Agreement
    corroborates "K2 + Davies reproduce a Harned-cell result to within its stated uncertainty"; it does not measure
    the single-ion activity of H+ independently.
  * UNITS: the 0.025 mol/kg molalities are treated as mol/L (dilute, rho ~ 1.00 kg/L -> ~0.1-0.3% in C_T, an
    estimated ~0.001-0.002 pH effect) -- a stated approximation, not a density-corrected conversion.
  * CONFOUND omitted: the Na-carbonate ion pairs (NaCO3-, NaHCO3(0)) are NOT in the carbonate base model.  At
    Na ~ 0.075 mol/kg they are a genuine second-order effect; the base model already lands within U, so the pair is
    a refinement, not a rescue (the next probe -- a sourced carbonate-pair association constant, like the opt-in NaAc
    pair the acetate model already carries).
  * TEMPERATURE: the certificate tabulates pH(S) at 10/15/20/25/30/35 C, but every repo constant is 25 C-sourced and
    the model fail-closes off 25 C (XIX-1C), so ONLY the 25 C row is a validatable prediction for us; the others are
    an access gap pending temperature-dependent constants.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from experiments.sandbox_foundation import carbonate_equilibrium as C

# ---- the certified measurement (independently read from the certificate; see module docstring) ----
SRM191D = {
    "material": "NIST SRM 191d (0.025 mol/kg NaHCO3 + 0.025 mol/kg Na2CO3, pH standard)",
    "certificate_issue_date": "2025-02-05",
    "certificate_url": "https://tsapps.nist.gov/srmext/certificates/191D.pdf",
    "certificate_sha256": "ea316fb1368d0563882a2b6926fe8a6bb07736e9d5fc1b24bb70c2317cc02d38",
    "method": "primary Harned-cell emf (cells without liquid junction); pH(S) on the molality scale",
    "certified_pH_S_25C": 10.014,
    "u_c": 0.0052,
    "U_k1_96": 0.010,
    "coverage_factor_k": 1.96,
}

# SRM 191d composition -> model inputs (molal treated as molar; see UNITS caveat).
TOTAL_CARBON = 0.025 + 0.025          # C_T = NaHCO3 + Na2CO3 carbon, mol/(kg~L)
SODIUM = 0.025 + 2 * 0.025            # Na = Na(NaHCO3) + 2*Na(Na2CO3), mol/(kg~L)


def predict() -> dict:
    """Run the repo carbonate closed-system solver at the SRM 191d composition, ideal and Davies.  Returns the
    comparison record (strict-JSON-able).  No parameter is fit -- this is a blind prediction."""
    out = {}
    for model in ("ideal", "davies"):
        sysc = C.CarbonateWaterSystem(mode="closed", total_carbon_M=TOTAL_CARBON, sodium_M=SODIUM,
                                      activity_model=model)
        r = C.solve(sysc)
        ph = float(r.pH_activity)                       # pH(S) is -log10 a_H+ -> compare the ACTIVITY pH
        residual = ph - SRM191D["certified_pH_S_25C"]
        within_U = abs(residual) <= SRM191D["U_k1_96"]
        out[model] = {
            "pH_activity": ph,
            "pH_concentration": float(r.pH_concentration),
            "ionic_strength_M": float(r.ionic_strength_M),
            "verdict": r.verdict,
            "residual_vs_certified": residual,
            "abs_residual": abs(residual),
            "within_certified_U": bool(within_U),
        }
    return {
        "operation": "XIX-4 measured-validation rung",
        "conditions": {"total_carbon_M": TOTAL_CARBON, "sodium_M": SODIUM, "temperature_K": 298.15,
                       "mode": "closed (no gas phase), CO2-free"},
        "certified": SRM191D,
        "model": out,
        "headline": {
            "comparator": "davies activity pH vs certified pH(S) 10.014 +/- 0.010 (U, k=1.96)",
            "model_pH": out["davies"]["pH_activity"],
            "residual": out["davies"]["residual_vs_certified"],
            "within_U": out["davies"]["within_certified_U"],
            "status": ("MEASURED_CORROBORATED_WITHIN_U (blind prediction, zero fitted parameters; PARTIAL "
                       "common-mode via the shared Debye-Huckel/Bates-Guggenheim activity-convention family -- NOT an "
                       "independent derivation of K2)"),
        },
        "caveats": [
            "PARTIAL common-mode: our K1/K2 are Harned-lineage and Davies shares the Debye-Huckel family with the "
            "certificate's Bates-Guggenheim convention (the certificate's dominant uncertainty, 0.0050 pH).",
            "UNITS: 0.025 mol/kg molalities treated as mol/L (dilute; ~0.001-0.002 pH effect).",
            "Na-carbonate ion pairs (NaCO3-, NaHCO3(0)) omitted from the carbonate base model (second-order here).",
            "Only the 25 C row is validatable (the model is 25 C-sourced and fail-closes off-domain, XIX-1C).",
        ],
    }


def main(argv=None) -> int:
    result = predict()
    text = json.dumps(result, indent=2, allow_nan=False)
    out_path = Path(__file__).with_name("result.json")
    out_path.write_text(text + "\n")
    hd = result["headline"]
    sys.stdout.write(
        f"NIST SRM 191d (carbonate pH standard) -- blind model prediction vs certified measurement\n"
        f"  certified pH(S) 25 C = {SRM191D['certified_pH_S_25C']}  (U = {SRM191D['U_k1_96']}, k=1.96)\n"
        f"  model (Davies) pH_activity = {hd['model_pH']:.4f}   residual = {hd['residual']:+.4f}   "
        f"within U = {hd['within_U']}\n"
        f"  status: {hd['status']}\n"
        f"  wrote {out_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
