# OPERATION XXIII Phase III — preregistration: the carbonate convention barrier + a chemically distinct holdout

*Committed BEFORE the harness `run_convention_bridge_xxiii.py` was first executed. Nothing below is tuned after a
number is seen; no constant is fitted to any measured value in this file.*

## 0. Sources (fetched and hashed in this operation)

| source | sha256 of the fetched PDF | what is read |
|---|---|---|
| NIST SRM 191d certificate (issued 2025-02-05), `https://tsapps.nist.gov/srmext/certificates/191D.pdf` | `ea316fb1368d0563882a2b6926fe8a6bb07736e9d5fc1b24bb70c2317cc02d38` (= the XIX pin) | Table 1 (25 °C): pH(S) 10.014, u_c 0.0052, U 0.010 (k 1.96). Table A1: pH(S) 10.0137, u_c(measurement) 0.0015, k_R 2.01, U_R 0.0029. Appendix A, verbatim: *"The respective pH(S) values in Table A1 are identical to those in Table 1"*, with the Bates–Guggenheim (BG) convention *"taken as an exact value with no uncertainty"*. pH(S) is on the molality scale. |
| NIST SRM 186g certificate (phosphate), `https://tsapps.nist.gov/srmext/certificates/186g.pdf` | `4a228c1b30ccf2a2d2eaca589d06d77b2fb7c2f7ba3b35f6d144c01eb6743116` | Table 1 equimolal 0.025 mol/kg KH2PO4 + 0.025 mol/kg Na2HPO4: 25 °C pH(S) 6.8640, u_c(measurement) 0.00080, k 2.0. Table 2 "physiological" 0.008695 mol/kg KH2PO4 + 0.03043 mol/kg Na2HPO4: 25 °C pH(S) 7.4157, u_c(measurement) 0.0011, k 2.0. |

## 1. What is wrong with the XXI-4 framing (stated before computing anything new)

XXI-4 treated Table A1 (±0.0029) as a *measurement-only* comparator and scored the Davies model against it. The
certificate says the A1 central value **is** the Table 1 value: A1 only removes the BG-convention uncertainty, because
it treats the BG convention as exact. A band that is exact *within the BG convention* can only judge a model that
applies the same convention. Scoring a Davies-γ_H model against it compares two different single-ion conventions with
the convention slack deleted. That is a category error, not a measurement-level refutation.

The truly convention-free measured quantity is the zero-chloride acidity function p(a_H γ_Cl)° of the Harned cell. NIST
obtains pH(S) from it by `pH(S) = p(a_H γ_Cl)° + log γ_Cl(BG)`, with `−log γ_Cl(BG) = A√I / (1 + 1.5√I)`. Inverting that
definition recovers the measured acidity function exactly, with the measurement uncertainty only. The product
`a_H γ_Cl = m_H γ_H γ_Cl` is a mean-ionic quantity, so a model predicts it without any single-ion convention.

## 2. The three comparisons (per buffer, 25 °C)

* **C1 — published, convention-inclusive.** Model `pH = −log(m_H γ_H)` under the model's own single-ion convention
  (Davies), against Table 1 pH(S) ± U (k ≈ 2). The BG uncertainty in U is what absorbs the convention mismatch.
* **C2 — measurement-only, convention-free.** Model `p(a_H γ_Cl) = −log(m_H γ_H γ_Cl)` (trace-Cl⁻ γ from the model's own
  activity law at the model's ionic strength) against the measured `pH(S)_A1 − log γ_Cl(BG)(I)` ± U_R = k·u_c(measurement).
* **C3 — fully internally consistent.** Molal composition, molal (I = 0, infinite-dilution) constants, the model's
  activity law on the molal scale, and the BG convention applied to the model output:
  `pH(S)_model = p(a_H γ_Cl)_model + log γ_Cl(BG)`, against the Table A1 value ± U_R.

C2 and C3 differ by the same additive constant `log γ_Cl(BG)(I)` on both sides, so **their residuals are identical by
construction**. That is reported as a structural fact, not as two independent passes.

The molar reading (composition `c = m·ρ_w`) is reported as a sensitivity only. Every constant used is molal.

## 3. Models (no constant fitted; every constant read from a committed source)

* **M0 — the frozen XIX baseline.** The repo's own `carbonate_equilibrium` constants (pK1 6.35, pK2 10.33, Kw 1e-14,
  Davies A 0.509), no ion pairs. Phosphate uses the same model class (Davies, I = 0 constants, no pairs) with the
  in-repo `minteq.v4.dat` constants (pK1 2.148, pK2 7.198, pK3 12.375).
* **M1 — M0 + the database's sodium/potassium ion pairs** (minteq.v4: NaCO3⁻ log K 1.27, NaHCO3° −0.25; NaHPO4⁻ 1.07
  [**the database references it at I = 0.10 and 20 °C, not at I = 0**], KHPO4⁻ 0.88).
* **Reference (model-vs-model, common-mode on the constant lineage):** PHREEQC through `phreeqpython` with
  `phreeqc.dat` (carbonate and phosphate) and `pitzer.dat` (carbonate only; it carries no phosphate).

**Instrument calibration (gate):** the generic Davies solver must reproduce the repo `carbonate_equilibrium.solve`
pH for the 191d composition to |Δ| < 1e-9 before any phosphate reading counts.

## 4. Decision rule (fixed now)

Let r_c, r_e and r_p be the **C2 residuals of M0** (model − measured) for carbonate 191d, phosphate equimolal and
phosphate physiological, each judged against its own U_R.

* **SYSTEMATIC** (activity model / convention at I ≈ 0.1 is the cause): r_e and r_p both have the sign of r_c, and
  both satisfy |r| > U_R and |r| ≥ 0.5·|r_c|.
* **CARBONATE-SPECIFIC** (K2 / Na–carbonate pairing is the cause): |r_e| ≤ U_R(e) and |r_p| ≤ U_R(p) while
  |r_c| > U_R(c).
* **MIXED / UNRESOLVED**: anything else.

Ionic-strength sensitivity of the BG inversion is reported (I ± 0.003). The verdict must hold at both ends, or it is
reported as I-dependent.

## 5. What would NOT change the verdict

A model–model agreement (PHREEQC vs M0) is solver corroboration, never measurement validation. The phosphate pH(S)
values share the Harned-cell and BG lineage with 191d. The holdout is distinct **chemistry**, not independent
**metrology**, and the ledger says so.
