# OPERATION XX §5 — unit repair + convention-matched comparison (NIST SRM 191d)

Harness: `run_unit_convention_s5.py` → `result_s5_unit_convention.json`; pinned by `tests/test_xx_s5_unit_convention.py`.
The XIX harness/result (`run_measured.py`, `result.json`) are untouched. **No model constant changed**
(`carbonate_equilibrium.py` byte-identical; `smartchem/` untouched).

## Certificate basis (SHA256 `ea316fb1…2d38`, issued 2025-02-05)
- 0.025 mol/kg **water** each of NaHCO₃ and Na₂CO₃ (2.1015 g + 2.6516 g per 1000.0 g H₂O → 1004.753 g solution), CO₂-free, closed, p°=1 atm, Harned cell, molality-scale pH(S).
- **Table 1 (certified)**: 10.014, u_c 0.0052, U = 0.010 (k=1.96) — *includes* the Bates–Guggenheim (BG) convention 0.0050.
- **Table A1 (non-certified)**: 10.0137, u_c 0.0015, U_R = 0.0029 (k_R=2.01) — *excludes* the BG convention uncertainty.

## Density (the certificate gives none) — an interval, not a point
ρ = 1004.753 g / (1000.0 g / 0.997047 g mL⁻¹ + 0.025 mol·φ_V,pair), φ_V,pair = φ_V(NaHCO₃)+φ_V(Na₂CO₃) bracketed in [0, 40] cm³/mol
(0 = ions add no volume; 40 = generous ceiling, ≈2× the largest ordinary 1:1-electrolyte φ_V). Derived edges 1.00079 – 1.00179,
carried outward-rounded as **ρ ∈ [1.0007, 1.0018] g/mL** (midpoint 1.00125, *not* a measurement).
Cross-checks (not the source of the bracket): PHREEQC `phreeqc.dat` density ≈ 1.0014; literature-magnitude φ_V(NaHCO₃)≈+24, φ_V(Na₂CO₃)≈−5 cm³/mol → ≈1.0013.
Tertiary/derived. **The suggested 1.002–1.006 band is not supported** (would need negative-large solute volume); it is run as a sensitivity only and changes nothing qualitative.

## Conversion
c_each = 0.025·ρ/1.004753 → **0.024899 – 0.024927 M** (mid 0.024913 M); C_T = 2c, Na = 3c.
**pH shift from units: +0.00026 … +0.00036** (mid +0.00031) — tiny (< 0.001) as expected in magnitude, but ~+0.0003, **not** the "~0.0001–0.0002" guessed; and positive.

## Comparisons (Davies, unchanged constants; XIX baseline 10.00479 → corrected mid 10.00510, range 10.00505–10.00515)
| comparator | residual (mid; range) | band | within |
|---|---|---|---|
| Table 1 certified 10.014 ± 0.010 | −0.00890 (−0.00895 … −0.00885) | 0.010 | **TRUE** (margin ≈ 0.0011 pH) |
| Table A1 10.0137 ± 0.0029 | −0.00860 (−0.00865 … −0.00855) | 0.0029 | **FALSE** (≈ 3× U_R) |

## Verdict
- **Survives the unit correction**: the Table-1 within-U result holds (unit shift is only +0.0003).
- **REFUTED against the convention-matched Table A1**: the model sits ≈ 0.0086 pH below the measurement-only value, ≈ 3× its U_R. The earlier pass exists **only** against the convention-*inclusive* band; the BG-convention slack (0.0050) is what carried it. Not a bug to fix — a scope result.
- **What is corroborated**: "K2 + Davies reproduce a Harned-cell result within the convention-inclusive certified U" (thinly).
  **What is refuted**: agreement at the measurement-only (≈ 0.003 pH) level.
- **PARTIAL common-mode preserved**: K1/K2 are Harned-lineage, Davies shares the Debye–Hückel family with BG; single-ion a_H⁺ is not independently derived. Agreement (or its absence) is not an independent derivation of K2.

## Flags (not folded into the headline)
1. **Mixed scale**: the prescribed repair feeds molarity but compares to a *molality*-scale pH(S). Pure alternatives: (a) molar K's + convert a_H to molality scale (pH_m = pH_c + log₁₀ kg-water/L ≈ −0.0015) → pH 10.0034–10.0038, residual −0.0102…−0.0106 vs Table 1 → **outside Table-1 U**; (b) molal K's + molality fed (= the XIX run) → 10.00479, −0.0092 → inside. So the Table-1 pass has a ~0.001 margin and is sensitive to the scale convention; the K's are labelled "molar" but trace to molal Harned work (unresolved).
2. Na-carbonate ion pairs still omitted (unchanged from XIX); with a sourced pair constant the sign of the residual could change — not tried (no tuning).
