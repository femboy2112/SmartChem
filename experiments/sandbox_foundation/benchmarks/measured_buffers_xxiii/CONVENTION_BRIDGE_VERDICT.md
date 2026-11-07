# OPERATION XXIII Phase III — the carbonate convention barrier: verdict and claim ledger

*Raw numbers: `result_convention_bridge_xxiii.json`, written by `run_convention_bridge_xxiii.py`. The rule was fixed
in `PREREGISTRATION.md`, committed (`09504f9`) before the harness first ran. No constant was fitted. The verdict is
written by hand from the JSON; the harness emits only the mechanical rule outcome.*

## 1. The question, answered

> *What exact standard-state convention is used for the K1/K2 carbonate constants underlying the NIST SRM 191d
> comparison?*

* **K1/K2 are molal, infinite-dilution (I = 0) thermodynamic constants.** This holds for the repo values (pK1 6.35,
  pK2 10.33), the in-repo `minteq.v4.dat` values (pK1 6.352, pK2 10.329, labelled NIST46.4, I = 0, 25 °C) and the
  Plummer–Busenberg `-analytic` fits in `phreeqc.dat`/`pitzer.dat` (log K2 = −10.32885 at 298.15 K, recomputed by the
  literature bearing). The lineage is the Harned cell (Harned & Davis 1943; Harned & Scholes 1941). The primary texts
  are paywalled, so that lineage claim is **UNVERIFIED** beyond secondary citation. The repo's "molar" label on these
  constants was a mislabel. Every computation here is on the molal scale.
* **pH(S) is conventional: −log a_H on the molality scale, from Harned cells with the Bates–Guggenheim convention.**
  Fetched and hashed by us: certificate `ea316fb1…` = the XIX pin.
* **The molar/molal distinction cannot explain the miss.** `c = m·ρ_w` gives `pH_m = pH_c + log ρ_w`. For this solution
  ρ_w = 0.9960–0.9971 kg water per L, so |Δ| ≤ 0.0018 pH. That is DERIVED, by two independent derivations (the
  literature bearing and ours). The residual below is 0.011, so scale is **REFUTED** as the cause.

## 2. The XXI-4 framing was a category error, but the negative result survives on the correct footing

The 191d certificate, Appendix A, states verbatim: *"The respective pH(S) values in Table A1 are identical to those in
Table 1."* Table A1 only drops the BG-convention uncertainty, treating the convention *"as an exact value"*. Scoring a
Davies-γ_H model against that band compares two single-ion conventions after deleting the convention slack. That is
not a measurement-level test.

The convention-free measured quantity is the zero-chloride acidity function `p(a_H γ_Cl)° = pH(S) − log γ_Cl(BG)`.
The product `a_H γ_Cl` is mean-ionic, so a model predicts it with no single-ion convention. Results for the frozen XIX
baseline M0 (repo constants, Davies, no pairs; instrument-gated against the repo solver, Δ = 3.6e-15):

| buffer (25 °C) | I (model) | C1: Davies pH vs Table 1 ± U | C2 ≡ C3: convention-free vs ± U_R |
|---|---|---|---|
| carbonate 191d | 0.09987 | −0.0092 (U 0.010) **thin pass** | **−0.0113** (U_R 0.0030, −3.7×) **REFUTED** |
| phosphate 186g equimolal | 0.10000 | **+0.0130** (U 0.010) **FAIL** | **+0.0106** (U_R 0.0016, +6.6×) **REFUTED** |
| phosphate 186g physiological | 0.09999 | +0.0052 (U 0.010) pass | +0.0028 (U_R 0.0022, +1.3×) marginal **REFUTED** |

* **C2 ≡ C3 by construction.** Applying BG to the model output (C3) and inverting BG on the measurement (C2) add the
  same constant to both sides. The residuals are identical (`C2_equals_C3: true` for every row). This is one test, not
  two passes.
* **The carbonate C2 result is robust.** It spans −0.0101 to −0.0124 over I ± 0.003 (the certificate does not state the
  ionic strength fed to BG) and −0.0111 to −0.0116 over BG A ∈ [0.5091, 0.5115].
* **Preserved.** The thin Table 1 pass (−0.0092) and the measurement-level refutation are two distinct claims. Neither
  is erased. The measurement-level refutation now rests on the right comparator.

## 3. The holdout: chemically distinct, and it discriminates

The predeclared rule, applied mechanically, gives **MIXED/UNRESOLVED** at every ionic-strength setting. The residual
signs are opposite: carbonate −, phosphate +. So the model does **not** fail by a uniform activity offset at I ≈ 0.1,
and the carbonate miss is **not** carbonate-specific, because phosphate misses too.

The sharper fact comes from the phosphate pair. Both formulations sit at I = 0.100 with the same constants, and
dp(a_Hγ_Cl)/dpK2 = 0.9999 and 0.9997. A pK2 error moves both by the same amount. Their residuals differ by 0.0078,
about 2.9× the combined U_R. **No single constant shift fixes both.** The miss depends on composition: the
HPO₄²⁻:H₂PO₄⁻ ratio (1:1 vs 3.5:1) and the Na:K mix differ. Specific-ion interactions, which Davies ignores by
construction, are the CONJECTURED mechanism.

Adding the database's ion pairs to Davies (M1) makes every buffer far worse: −0.155, −0.084, −0.089. This matches the
XXI/XXII "pairs push ~0.14 away" and the S6 factorial. Davies' empirical linear term already absorbs part of the
association that the pair constants re-add. The CONJECTURED reading is double counting. Mixing an ion-association set
with an activity law it was not fitted with is not a refinement.

Reference solvers (model-vs-model, common-mode on the constant lineage):
* `phreeqc.dat` gives carbonate −0.142, phosphate +0.008 / +0.002.
* `pitzer.dat` gives carbonate −0.074.

The pitzer.dat number is an **unexplained anomaly**. An internally consistent Pitzer model at I = 0.1 should do far
better. The literature bearing flagged a 0.0104 gap between pitzer.dat's `log_k` and `-analytic` for HCO₃⁻, which is
too small to account for 0.074. Not investigated further, so labelled DARK below.

## 4. Claim ledger

| tier | claim |
|---|---|
| **DISCLOSED** | 191d Table A1 pH(S) values are identical to Table 1; A1 takes BG as exact (certificate text, sha256 `ea316fb1…`). pH(S) is on the molality scale, from Harned cells + BG. 186g: equimolal 6.8640 (u_meas 0.00080), physiological 7.4157 (u_meas 0.0011), k 2.0 (sha256 `4a228c1b…`). minteq.v4 carbonate/phosphate constants are I = 0, 25 °C, except NaHPO₄⁻ (I = 0.10, 20 °C). |
| **CORROBORATED** | The generic Davies solver equals the repo carbonate solver (Δ 3.6e-15). Phosphate M0 by two independent algorithms (nested bracketing + fixed point vs simultaneous MINPACK) agrees to ~1e-15. The molar↔molal bound |Δ| ≤ 0.0018 pH was derived twice independently. |
| **OBSERVED** | Table 1 C1 thin pass for carbonate (−0.0092). Convention-free C2 residuals −0.0113 / +0.0106 / +0.0028, robust to I ± 0.003 and BG A. dp/dpK2 ≈ 1 for all three. M1 (pairs + Davies) off by 0.08–0.15. PHREEQC phreeqc.dat −0.142 / +0.008 / +0.002 and pitzer.dat −0.074 (carbonate). |
| **REFUTED** | (a) Molar vs molal scale as the cause of the carbonate miss. (b) XXI-4's reading of Table A1 as a measurement-only comparator (category error). (c) "Davies + Harned-lineage I = 0 constants reproduce primary pH standards within measurement uncertainty at I ≈ 0.1" (fails on 3 of 3 buffers at the convention-free level). (d) "The carbonate miss is carbonate-specific". (e) "One systematic activity offset explains all three" (opposite signs). (f) "A single pK2 error explains phosphate" (composition-dependent gap of 0.0078). |
| **CONJECTURED** | Specific-ion interactions (absent from Davies) drive the composition-dependent residuals. M1's large miss is double counting of association within an empirically-fitted Davies law. The residual magnitude (~0.01) is the accuracy class of Davies at I ≈ 0.1. |
| **UNVERIFIED** | The Harned & Davis / Harned & Scholes and Bates & Acree primary texts and their stated uncertainties (paywalled). The IUPAC 2002 BG constant A = 0.5100 (HTTP 403; bracketed, verdict-insensitive). The ionic strength NIST used in the BG inversion (unstated; bracketed, verdict-insensitive). |
| **DARK** | The pitzer.dat −0.074 carbonate anomaly. Every temperature but 25 °C. Any non-Harned (independent-metrology) measurement of these buffers or of K2. A Pitzer-consistent phosphate model. |

The independence boundary: both holdouts share the Harned-cell + Bates–Guggenheim metrology lineage with 191d. They
test distinct **chemistry**, not independent **metrology**.

## 5. The next three verdict-changing probes

1. **A specific-interaction model on the phosphate pair.** Run a Pitzer (or SIT) model with sourced Na/K–H₂PO₄⁻/HPO₄²⁻
   parameters on both 186g formulations. If it closes the 0.0078 composition gap within U_R, the activity model is the
   cause (CONJECTURED → CORROBORATED). If it does not, the constants or the metrology are back in play.
2. **Resolve the pitzer.dat carbonate anomaly.** Determine which `log_k` PHREEQC applies at 25 °C and whether pitzer.dat
   carries Na–CO₃²⁻/HCO₃⁻ interaction parameters. A validated Pitzer reference within U_R on 191d would show the gap is
   model-class, not data.
3. **Break the common mode.** Obtain one non-Harned measurement: a spectrophotometric pH (purified indicator) in an
   Na-carbonate or phosphate medium, or a conductimetric K2. Until then, every "measurement" comparison here shares the
   Harned/BG lineage, and the ledger keeps that boundary.

---

## XXIV provenance correction (2026-11-07; appended, historical text above unchanged)

The certificates were re-read against their pinned SHA-256 bytes (full record:
`docs/research/OPERATION_XXIV_SOURCE_GROUNDING.md` §III-A). No raw benchmark result changes. Four corrections follow;
correct each of these wherever the text above states it:

1. **SRM 191d Table A1 is not a separate measurement.** It is the same pH(S) as Table 1, given to more decimals
   (certificate: "identical to those in Table 1"), with an uncertainty that leaves out the Bates–Guggenheim term.
   Wherever it is called "measurement-only", read "the same measurement, convention treated as exact".
   - The certificate PRINTS U_R = 0.0029 at 25 °C. The value 0.0030 used above is 2.01 × 0.0015; the printed figure
     comes from the unrounded u_c. So the XXIII carbonate C2 refutation is −3.9×U_R, not −3.7×, and stronger.
2. **The 191d "2025" date is an editorial reissue.** The original certificate is dated 1 December 2009.
3. **SRM 186g certification EXPIRED on 30 April 2023** (certificate, verbatim). Its values are used here as a
   historical measurement record. The NIST catalog (checked 2026-11-07) lists no successor.
   - 186g's U_R-type values are non-certified "Reference Values" (kR = 2.0), not a separate table.
   - 186g names no Harned cell. It cites "cells without liquid junction by the primary measurement method" and the
     Bates–Guggenheim convention. The Harned lineage for 186g is inferred, not quoted.
4. **Both certificates warn of lot-to-lot pH(S) variation "on the order of a few thousandths".** That is the same size
   as the U_R bands (0.0016–0.003), and none of the U_R verdicts includes it.
