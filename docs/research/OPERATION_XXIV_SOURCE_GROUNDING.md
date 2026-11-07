# OPERATION XXIV: source grounding (Phases II and III)

This file records how temperature and standard state are carried through the simulator, what its declared domains do and do not certify, and where it stands against measurement.

Three different achievements are kept apart throughout:
- **a correct equation**;
- **a certified execution**;
- **an empirically validated prediction**.

Nothing below promotes one into another.

## II-A. Temperature transport

**Before (probe P5 RED):** a world at 350 K executed a 25 °C `SourcedConstant` unchanged. The world certificate bound the temperature, yet the law ran a constant from a different temperature. The coupled run stayed certified, and neither path carried a domain flag.

**After:**
- Every `SourcedConstant` a rate law executes is inventoried from its dataclass fields (`admissibility.law_source_temperatures`).
- A run whose temperature differs from a constant's sourced `T_K` by more than 0.01 K is REFUSED on both paths: `SourceDomainError` on the kernel, `CoupledSourceDomainError` on the coupled world.
- The 2.0 API refuses such a world at `SimulationSpec` construction (`SOURCE_DOMAIN_UNSUPPORTED`).
- Receipts carry `source_domain`: either "SUPPORTED … within-formula-domain only — NOT an empirical-validation claim" or `NO_SOURCED_CONSTANTS`.

**Status:** no validated temperature law exists in the sandbox, so nothing is extrapolated. A sourced van 't Hoff or `-analytic` transport, with its own validation, is an open item. PHREEQC's `-analytic` expressions would count as sourced, but agreeing with PHREEQC on them would still be model-vs-model.

## II-B. Activity and standard-state common basis

The full derivation is in `experiments/sandbox_foundation/standard_state.py`. Its core:

- The chemical potential is the same on either basis: μ_i = μ_i°(m) + RT ln(γ^(m) m/m°) = μ_i°(c) + RT ln(γ^(c) c/c°).
- Taking the ideal-dilute limit (c/m → ρ_w*) gives the transport of the **whole activity product**:
  **log K^(c) = log K^(m) + Σ_aq ν_i · log10(ρ_w* m°/c°)**, with ρ_w*(25 °C) = 0.997047 kg/L.
- Pure phases (solids, the solvent) drop out of the exponent.
- At finite concentration the activity coefficients transform as γ^(c) = γ^(m) · m ρ_w*/c.

**Tests** (`test_xxiv_standard_state.py`):
- Dimensional: the factor is dimensionless.
- Round trip.
- Σν counts aqueous solutes only.
- **Independent check:** one dilute state written on both bases gives an identical saturation index once K is transported. It gives a different one, by exactly −2·log10 0.997047, if the molal K is reused on molar concentrations.

**Measured consequence (model-vs-model, same database):**
- XXIII's calcite world fed molal-basis log K into molar activities, a disclosed but uncorrected mismatch.
- Against PHREEQC's Ca (1.23007e-4 mol/kgw, multiplied by ρ_w* to give mol/L), that world is **+0.298%** off.
- With every constant transported (`CalciteParams(standard_state_basis="converted_to_molar")`), it is **−0.0071%** off.
- So the XXIII "0.30% after density conversion" was the standard-state basis, not chemistry. This is **CORROBORATED**.
- Both sides use the same PHREEQC constants, so this is verification of a common basis, **not** validation against nature.
- The default stays `as_tabulated_molal`, because XXIII's committed results must remain reproducible. Its provenance entry discloses the mismatch.

## II-C. What the ionic-strength ceiling certifies

`ionic_strength_max = 0.1` is a declared **applicability limit**. Above it, the law refuses (`OutOfDomainError`). It is **not** an accuracy claim across [0, 0.1]: the NIST probes at I ≈ 0.1 show the Davies model refuted by 2–4× U_R.

Every 2.0-API result now carries a four-rung `validation_ladder` (`admissibility.CLAIM_LADDER`):

| rung | calcite world | vinegar world |
|---|---|---|
| NUMERICALLY_EXECUTABLE | per-phase receipts | per-phase receipts |
| WITHIN_DECLARED_FORMULA_DOMAIN | I ≤ I_max, T = 298.15 K | 25 °C K-set, Davies I-domain |
| COMPARED_TO_REFERENCE_IMPLEMENTATION | PHREEQC, same constants (model-vs-model) | PHREEQC benchmarks (model-vs-model) |
| EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND | **False** | **False** |

A model can pass the first three and fail the fourth. Both worlds do exactly that today.

## III-A. NIST provenance, re-read from the primary PDFs

The certificate SHA-256 values match the repo's pins:
- 191d: `ea316fb1…2d38`
- 186g: `4a228c1b…6116`

| claim | finding (verbatim where quoted) | status |
|---|---|---|
| 191d Table 1, 25 °C | 10.014, U 0.010, k 1.96 (BG uncertainty 0.0050 included) | MATCH |
| 191d Table A1 | 10.0137, u_c(meas) 0.0015, k_R 2.01, ν_eff 49.6, **U_R 0.0029 printed**; "identical to those in Table 1"; **non-certified** | the repo used U_R = 0.0030 (2.01 × 0.0015); the refutation is −3.9× rather than −3.7× (stronger) |
| "Table A1 = measurement-only" (S4/S5) | the same measurement, with the convention treated as exact | MISDESCRIBED; correction appended |
| 191d date | reissue 5 Feb 2025 (editorial); original 1 Dec 2009; valid to 30 Nov 2032 | README's "2025 measurement" corrected |
| **186g validity** | "valid … until 30 April 2023" | **EXPIRED; was not disclosed**. It is now a historical record. The NIST catalog lists no successor (186h/i/j certificate URLs return 404) |
| 186g method | "cells without liquid junction by the primary measurement method"; BG convention; the word "Harned" never appears | the Harned lineage for 186g is INFERRED, not quoted |
| 186g U_R values | page 3 "Reference Values" are **non-certified**, k_R 2.0 | was described as "one column" |
| lot variation | "a few thousandths" between renewals, in both certificates | not in any U_R verdict (an open caveat of the same size as the bands) |

**Scope of the corrections:**
- Corrections were **appended** (dated) to the five affected documents. No raw benchmark result was altered.
- **Not re-verified by me (from the delegated audit):** that the 191d preparation masses are buoyancy-uncorrected balance readings, so the "implied molality 0.025016" is a misread. Its pH effect is negligible. The APMP/lot 10.010 figures remain UNVERIFIED.

## III-B. The pitzer.dat −0.074 anomaly is EXPLAINED (a database parameter)

**Harness:** `benchmarks/pitzer_anomaly_xxiv/` uses a vendored copy of `pitzer.dat` (sha256 `eb5051…a5c9`), the exact bytes behind XXIII's number. It runs single-factor ablations on temporary copies and leaves the pinned file unedited.

| cell | C2 (191d) |
|---|---|
| P0 pinned | **−0.07406745913108281** (bit-identical to XXIII) |
| P1 β2(Na⁺,HCO₃⁻) = 8.22 → 0 | **+0.0051433** (attribution +0.0792) |
| P2 `-MacInnes false` | Δ = 6e-12 (the acidity function is convention-free, as designed) |

- **Mechanism:** the `-B2` line `HCO3- Na+ 8.22 … -0.049` ("ref. 3 + new -analytic for calcite") was added by the 2015 re-parameterization of Na–HCO₃ (Appelo 2015, *Appl. Geochem.* 55:62, as cited by the delegated history scan). It is the only 1-1 pair with a β2, and with α2 = 12 it makes γ(HCO₃⁻) strongly Na-dependent at I = 0.1.
- **Who reproduced what:**
  - I reproduced P0 and P1 independently in a scratch copy before committing the harness.
  - Reported by the delegated scan, not re-run by me: pitzer.dat files before 2015-02 (Na–HCO₃ 0.0277/0.0411, no β2) give +0.0004 to +0.0008; the 2015-02-06 edit introduced −0.0741.
- **What this means:** XXIII's "DARK" anomaly is a reference-database artifact, **not** evidence of a model-class limit. The raw XXIII result stands as recorded.
- **What it does not mean:**
  - P1 (+0.0051) is still outside U_R (0.0029), so zeroing β2 does not "pass".
  - Even the pre-2015 agreement is Harned-lineage common-mode if those Pitzer parameters were fitted to Harned-cell EMFs. That fitting history is INFERRED, not read.

## III-C. Phosphate composition discriminator: NOT RUN (underpowered as sourced)

The XXIII differential to explain is **0.0078 pH**, between the equimolal and physiological residuals.

**Parameter sources found** (delegated search; none read primary — Pitzer & Mayorga 1973 returned HTTP 403):
- Binary β0/β1/Cφ for NaH2PO4, KH2PO4, Na2HPO4 and K2HPO4, from two fits: PM73 via pytzer, and May et al. 2011 via pyEQL.
- Mixing terms θ(Cl,H2PO4) and ψ(Na/K,Cl,H2PO4/HPO4), from Pitzer & Silvester 1976 and Hershey et al. 1989.

**Why it was not run:**
- The two binary fits differ by up to **0.0055 in log γ±** at I = 0.1. That is the same size as the effect to be explained.
- θ(H2PO4,HPO4), ψ(Na/K,H2PO4,HPO4) and ψ(Na,K,·) were **not found**.
- So a fixed-parameter run could not separate the hypotheses. I could not honestly predeclare its **sign**, and a preregistration that cannot fail is not one.
- The discriminator therefore stays **OPEN**. The next probe is a preregistration fixing one primary-read parameter set, the predicted sign and the magnitude band, before any computation.

## III-D. Independent measured holdout: the 2.0-alpha gate stays OPEN

**Where the model's constants come from:**
- Calcite log Ksp −8.48: Plummer & Busenberg 1982, fitted to **their own** ~350 measurements.
- K1 and K2: P&B 1982's critical evaluation. A Harned lineage is CONJECTURED.
- Any calcium-vs-pCO₂ datum tests the combination Ksp·K1·K_H/K2 plus the ion pairs, and cannot isolate Ksp alone.

**Best independent candidate:**
- **Kline's 25 °C Ca-vs-pCO₂ series**, published in Frear & Johnston 1929 (*JACS* 51:2082), read via the public-domain compilation Linke 1958, p. 540.
- It predates the Harned work and uses no pH. It was not used in P&B's Ksp fit, according to their abstract.

**Why it does not qualify (yet):**
- The **analytical method is unread**: the primary paper is paywalled.
- **No uncertainty is stated**, so no measured error band exists.
- The CO₂-open world would also need a sourced CO₂(g) Henry boundary, which the calcite builder does not declare and refuses.

**Disclosure:** a delegated scratch run compared the model to these points before any registration (residuals −5.8% … +3.3%, monotone in pCO₂). That makes any rule chosen now post-hoc. The numbers are not committed and are not claimed.

**The gate is not met:** no bounded physical domain has been validated against an independent measurement with a stated uncertainty. Unchanged from XXIII.
