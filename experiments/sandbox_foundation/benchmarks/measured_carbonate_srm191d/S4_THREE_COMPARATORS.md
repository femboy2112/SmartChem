# OPERATION XXI §4 — three comparators + claim ledger (NIST SRM 191d)

Harness: `run_three_comparators_s4.py` → `result_s4_three_comparators.json`; pinned by `tests/test_xxi_s4_three_comparators.py`.
Builds ON `run_unit_convention_s5.py` (XX-5), importing its computations verbatim. **No model constant changed**
(`carbonate_equilibrium.py` byte-identical to the XXI base `774429e`; `smartchem/` untouched — asserted by the test via git).

XX-5 established the unit repair and the convention-matched Table A1 refutation but kept the **scale-transported** basis
in a "NOT headline" sensitivity block. XXI-4 promotes it to a first-class **Comparator C**, because that is where the
decisive finding lives: the Table-1 "pass" is **contingent on an unresolved standard-state (molar vs molal) scale**
for the model's equilibrium constants.

## The three comparators (same unchanged Davies prediction; densities over the XX-5 derived interval 1.0007–1.0018 g/mL)

| | comparator | measurement | model basis | residual (interval) | band | verdict |
|---|---|---|---|---|---|---|
| **A** | Table 1, convention-**inclusive** | 10.014 ± **0.010** (incl. BG 0.0050) | mixed scale (molarity fed, molality-scale pH(S)) | −0.00895 … −0.00885 | 0.010 | **WITHIN U, thin** (margin ≈0.0011) |
| **B** | Table A1, convention-**matched** | 10.0137 ± **0.0029** (BG removed) | same mixed-scale prediction | −0.00865 … −0.00855 | 0.0029 | **REFUTED** (~3× U_R) |
| **C** | Table 1, **scale-consistent** | 10.014 ± **0.010** | molar-K reading, a_H transported to molality scale | −0.01060 … −0.01022 | 0.010 | **REFUTED** (outside U) under molar-K; **survives** under molal-K |

A and B share the *prescribed* mixed-scale prediction; C transports a_H onto the measurement's molality scale
(`pH_m = pH_c + log10(kg water / L)`). The alternative molal-K reading is the XIX run (molality fed, pH 10.00479,
residual −0.00921 vs Table 1 → within U, thin).

## Transported basis, declared explicitly (§4B)

1. **Model standard concentration** — 1 mol/L (the solver's concentration basis).
2. **Equilibrium constants** — K1/K2/Kw labelled *molar*; their provenance traces to **molal** Harned-cell work (UNRESOLVED; see decisive measurement).
3. **Proton activity convention (model)** — Davies activity coefficients (Debye–Hückel family); single-ion a_H⁺.
4. **Measurement standard state** — molality scale (mol/kg water), Harned cell, CO₂-free, 25 °C, p°=1 atm.
5. **Activity-coefficient convention (measurement)** — Bates–Guggenheim single-ion convention.
6. **Conversion** — molality→molarity via the derived density interval (XX-5); scale transport of a_H molar↔molal via `log10(kg water/L) ≈ −0.0015`.
7. **Irreducible conventionality** — single-ion a_H⁺ is a *conventional* quantity on both sides; a fully transported Comparator C is only constructible once the K-scale is pinned, otherwise it is **unresolved at the 0.003-pH precision**.

## Claim ledger (§4D)

- **A — CORROBORATED (thin, scale-contingent).** *Measured:* certified pH(S) 10.014. *Modeled:* Davies closure, unchanged constants. *Transported:* units only (a mixed-scale comparison). *Assumed:* molar K's comparable to a molality-scale pH(S) without transporting a_H; derived density bracket. *Uncertainty retained:* full U=0.010 (includes BG 0.0050). *Passes:* yes. *Refuted:* nothing. *Corroborated:* "K2 + Davies reproduce a Harned-cell pH within the convention-inclusive certified U" (thinly). *Decisive next:* a measured solution density; resolve the K-scale (the pass is scale-contingent).
- **B — REFUTED.** *Measured:* Table A1 10.0137 (BG removed). *Modeled/Transported:* identical to A. *Assumed:* Table A1 is the like-for-like convention-matched comparator (not an independent measurement). *Uncertainty retained:* U_R=0.0029 (excludes BG). *Passes:* no (~3× U_R). *Refuted:* agreement at the measurement-only (~0.003-pH) level — the A pass exists only because BG slack (0.0050) is inside A's band. *Decisive next:* an independent single-ion a_H⁺ not sharing the BG convention, or a second measured buffer on a convention the model does not also assume.
- **C — REFUTED (under the molar-K label); UNRESOLVED overall.** *Measured:* certified 10.014 (molality scale). *Modeled:* same Davies prediction made scale-consistent. *Transported:* a_H from the molar to the molality scale — the step A omitted. *Assumed:* the "molar" label literal; alternative is molal K's (Harned provenance) → the XIX run, which survives. *Uncertainty retained:* full U=0.010 (only the scale changed vs A). *Passes:* no (|residual| ≈ 0.0104 > 0.010) under molar-K; the molal-K reading survives. *Refuted:* that the Table-1 corroboration is robust — it flips with a convention the sources do not pin. *Decisive next:* resolve the **standard-state scale (molar vs molal) of K1/K2** from their primary Harned-cell source; that one fact decides molal (survives Table 1) vs molar (refuted).

## Headline

SmartChem's SRM 191d corroboration is **not a robust physical prediction**: it holds only against the
convention-inclusive Table 1 (A), is refuted at the measurement-only Table A1 level (B), and is refuted against Table 1
itself once the molar-K scale is made self-consistent (C). The single unresolved fact that decides the measurement-level
verdict is the **standard-state scale of K1/K2**. **PARTIAL common-mode preserved**: K1/K2 are Harned-lineage and Davies
shares the Debye–Hückel family with the BG convention; single-ion a_H⁺ is not independently derived, so agreement is not
an independent derivation of K2. **No constant tuned.**
