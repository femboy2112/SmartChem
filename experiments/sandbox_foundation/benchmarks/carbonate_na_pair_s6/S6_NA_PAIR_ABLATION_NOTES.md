# OPERATION XXI section 6 -- Na-carbonate ion-pair ablation: RAW TABLES + OBSERVATIONS

Ooh yeah, can do!  Raw numbers from `run_na_pair_ablation_s6.py` -> `result_s6_na_pair_ablation.json` (deterministic: two consecutive re-runs gave an identical result-file sha256).  Observations are factual statements about the tables.  **No claim ledger here** (the verdict below was written by the orchestrator after verifying the DB diff, the no-tune git check, and re-running the suite).

**VERDICT (orchestrator): H2 CORROBORATED model-vs-model — the Na-carbonate pairs ARE the dominant high-Na SmartChem-vs-minteq.v4 gap; the measurement-level correction is REFUTED — adding the DB pairs moves PHREEQC ~0.14 pH AWAY from the NIST certified value (the §6D warning, realized). No constant tuned. Full ledger at the foot of this file.**

## 0. Instrument and databases

* PHREEQC via `phreeqpython`, T = 298.15 K, 1 atm; same input both ways, only the database differs.
* WITH pairs: `db/minteq.v4.dat` sha256 `4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3` (verbatim).
* NO pairs:   `db/minteq.v4.nopairs.dat` sha256 `6ada9d3f17bd1a101b446ed5eb67cb520bd923e842f3b0547a5261f3493a3082`.
* Removed (original lines 4872-4879 and 4880-4887; 16 lines total, deletion only, nothing added/edited -- asserted by the test):
  `Na+ + CO3-2 = NaCO3-` (log_k 1.27, delta_h -20.35 kJ, -gamma 5.4 0) and `Na+ + H+ + CO3-2 = NaHCO3` (log_k 10.079, delta_h -28.3301 kJ, -gamma 0 0).
* SmartChem column = unchanged `carbonate_equilibrium.solve`, Davies, `pH_activity` (identical to committed `carbonate_phreeqc/code_results.json`; re-solved for C1-C5 and matched to the last digit).  Numerics are fed as mol/L to SmartChem and mol/kgw to PHREEQC (the existing grid's convention).
* `phreeqc.dat` column = the committed `carbonate_phreeqc/comparison_table.json` PHREEQC pH (CONTEXT only; `phreeqc.dat` contains no Na-carbonate pair).

## 1. Three-way pH table, existing carbonate grid (11 cases)

pH; `with-no` = delta_pH = pH(WITH pairs) - pH(NO pairs); SC-no / SC-with = SmartChem minus PHREEQC.

| case | desc | Na | SmartChem | PHREEQC no pairs | PHREEQC with pairs | delta_pH (with-no) | SC - no | SC - with | phreeqc.dat (ctx) | I no | I with |
|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 | pure water, P_CO2 = 1e-4 atm | 0.0 | 5.9053 | 5.9077 | 5.9077 | +0.0000 | -0.0024 | -0.0024 | 5.9088 | 0.00000 | 0.00000 |
| O2 | pure water, atmospheric CO2 (log P = -3.5) | 0.0 | 5.6563 | 5.6586 | 5.6586 | +0.0000 | -0.0023 | -0.0023 | 5.6597 | 0.00000 | 0.00000 |
| O3 | pure water, P_CO2 = 1e-3 atm | 0.0 | 5.4066 | 5.4089 | 5.4089 | +0.0000 | -0.0023 | -0.0023 | 5.4099 | 0.00000 | 0.00000 |
| O4 | pure water, P_CO2 = 1e-2 atm | 0.0 | 4.9067 | 4.9090 | 4.9090 | +0.0000 | -0.0023 | -0.0023 | 4.9100 | 0.00001 | 0.00001 |
| O5 | pure water, P_CO2 = 1e-1 atm | 0.0 | 4.4067 | 4.4090 | 4.4090 | +0.0000 | -0.0023 | -0.0023 | 4.4101 | 0.00004 | 0.00004 |
| O6 | pure water, P_CO2 = 1 atm (soda) | 0.0 | 3.9067 | 3.9091 | 3.9091 | +0.0000 | -0.0024 | -0.0024 | 3.9113 | 0.00012 | 0.00012 |
| C1 | 0.01 M NaHCO3 | 0.01 | 8.2463 | 8.2466 | 8.2222 | -0.0244 | -0.0003 | +0.0240 | 8.2242 | 0.01011 | 0.01005 |
| C2 | 0.1 M NaHCO3 | 0.1 | 8.1249 | 8.1249 | 8.0167 | -0.1082 | -0.0001 | +0.1082 | 8.0159 | 0.10129 | 0.09719 |
| C3 | half-neutralized (0.1 C, 0.05 Na) CO2/HCO3 buffer | 0.05 | 6.2644 | 6.2701 | 6.2625 | -0.0076 | -0.0057 | +0.0019 | 6.2594 | 0.05001 | 0.04908 |
| C4 | 0.1 M Na2CO3 | 0.2 | 11.3893 | 11.3727 | 11.2633 | -0.1094 | +0.0165 | +0.1260 | 11.2610 | 0.29650 | 0.20574 |
| C5 | 0.01 M dissolved CO2, no base | 0.0 | 4.1765 | 4.1775 | 4.1775 | +0.0000 | -0.0010 | -0.0010 | 4.1775 | 0.00007 | 0.00007 |

### 1b. Na speciation (WITH pairs; molal) and carbonate species with/without pairs (closed Na-bearing cases)

| case | Na total | free Na+ | NaCO3- | NaHCO3 | bound fraction | HCO3- with | HCO3- no | CO3-2 with | CO3-2 no |
|---|---|---|---|---|---|---|---|---|---|
| C1 | 0.01000 | 0.00994 | 0.00001 | 0.00004 | 0.0057 | 0.00972 | 0.00978 | 0.00010 | 0.00011 |
| C2 | 0.10000 | 0.09623 | 0.00064 | 0.00313 | 0.0377 | 0.09366 | 0.09741 | 0.00096 | 0.00129 |
| C3 | 0.05000 | 0.04907 | 0.00000 | 0.00092 | 0.0185 | 0.04906 | 0.04998 | 0.00001 | 0.00001 |
| C4 | 0.20000 | 0.15411 | 0.04577 | 0.00012 | 0.2294 | 0.00249 | 0.00350 | 0.05163 | 0.09650 |

## 2. NIST SRM 191d (0.025 mol/kg water each NaHCO3 + Na2CO3; Na 0.075, C(4) 0.05 mol/kgw; CO2-free closed)

| quantity | value |
|---|---|
| pH, PHREEQC WITH pairs | 9.85731 |
| pH, PHREEQC NO pairs | 9.99916 |
| delta_pH (with - no) | -0.14185 |
| I with / no | 0.08316 / 0.09987 |
| SmartChem (unchanged Davies), molality-fed (XIX run) | 10.00479 |
| SmartChem, molarity-fed, rho lo/mid/hi | 10.00515 / 10.00510 / 10.00505 |

| vs certified | residual WITH | residual NO | within U (with / no) | pairs move PHREEQC toward measured? |
|---|---|---|---|---|
| Table 1: 10.014, U = 0.010 | -0.15669 | -0.01484 | False / False | NO (away) |
| Table A1: 10.0137, U_R = 0.0029 | -0.15639 | -0.01454 | False / False | NO (away) |

Na speciation (WITH pairs, molal): free Na+ 0.06633, NaCO3- 0.00809, NaHCO3 0.00058; bound fraction 0.1155.

## 3. Preregistered holdout Na-sweep (closed, C_T = 0.05 mol/kgw, charge-balanced pH, no gas phase)

| Na/C_T | Na | SmartChem | PHREEQC no | PHREEQC with | delta_pH | SC - no | SC - with | I with | NaCO3- | NaHCO3 | bound frac | in-domain |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 0.025 | 6.2842 | 6.2888 | 6.2846 | -0.0043 | -0.0047 | -0.0004 | 0.02475 | 0.00000 | 0.00026 | 0.0103 | True |
| 1.0 | 0.05 | 8.1679 | 8.1680 | 8.0948 | -0.0732 | -0.0001 | +0.0731 | 0.04940 | 0.00021 | 0.00089 | 0.0220 | True |
| 1.5 | 0.075 | 10.0048 | 9.9992 | 9.8573 | -0.1419 | +0.0056 | +0.1475 | 0.08316 | 0.00809 | 0.00058 | 0.1155 | True |

## 4. Factual observations (no verdict)

1. Zero-Na cases (O1-O6, C5): delta_pH = 0 to the printed precision (max |delta_pH| = 0.00e+00); the ablated species do not form without Na.
2. In the Na-bearing grid cases delta_pH is negative (pairs lower pH): C1 -0.0244, C3 -0.0076, C2 -0.1082, C4 -0.1094.
3. Where Na is present, SmartChem minus PHREEQC-NO-pairs is: C1 -0.0003, C2 -0.0001, C3 -0.0057, C4 +0.0165; SmartChem minus PHREEQC-WITH-pairs is: C1 +0.0240, C2 +0.1082, C3 +0.0019, C4 +0.1260.
4. Zero-Na cases show a near-constant SmartChem - PHREEQC(minteq.v4) offset in the range -0.0024 to -0.0023 pH (O1-O6) where the ablated pairs play no role (delta_pH = 0 there).
5. Fraction of Na bound in pairs rises with carbonate content: C1 0.0057, C3 0.0185, C2 0.0377, NIST 0.1155, C4 0.2294.  NaHCO3 dominates the bound Na in C1-C3; NaCO3- dominates in C4 and NIST.
6. Holdout (C_T 0.05): |delta_pH| grows monotonically with Na/C_T: 0.5 -> -0.0043, 1.0 -> -0.0732, 1.5 -> -0.1419; bound fraction 0.0103, 0.0220, 0.1155.  All three cells in-domain (max I = 0.0832).
7. SmartChem minus PHREEQC-NO-pairs across the holdout: -0.0047, -0.0001, +0.0056; SmartChem minus PHREEQC-WITH-pairs: -0.0004, +0.0731, +0.1475 (Na/C 0.5, 1.0, 1.5).
8. The NIST composition is the Na/C = 1.5 holdout cell (identical system); PHREEQC-with = 9.85731, PHREEQC-no = 9.99916.  Adding the pairs moves PHREEQC AWAY from Table 1 (|residual| 0.01484 -> 0.15669) and AWAY from Table A1 (|residual| 0.01454 -> 0.15639).  PHREEQC-no-pairs is outside Table-1 U = 0.010; PHREEQC-with is outside.
9. In the same ablation the ionic strength drops with pairs (fewer free ions): see `I no` vs `I with` (largest at C4).

## 5. Caveats on the instrument (facts, not conclusions)

* The ablation isolates ONLY the two pair reactions inside minteq.v4; it holds the b-dot/Debye-Huckel activity model, the K1/K2 lineage and the molal basis fixed.  It does not separate activity-model, molal-vs-molar, or database-convention contributions from each other; those live in the SmartChem-vs-PHREEQC-no-pairs column.
* minteq.v4's open-pure-water and Na-free numbers already differ from SmartChem by ~0.002 pH with no pairs involved.
* The pair `-gamma` entries (NaCO3-: 5.4 0; NaHCO3: 0 0) are database-sourced and untouched.
* minteq.v4.dat is not shipped with phreeqpython; the copy in `db/` is the PHREEQC 3 release file whose sha256 is pinned above.
* `get_selected_output_array` takes the LAST row for EQUILIBRIUM_PHASES runs (as in the existing benchmark); closed cases are single-row.

## VERDICT (orchestrator claim ledger)

Verified before writing: the no-pairs DB differs from minteq.v4 by exactly the two Na-carbonate reactions (16-line deletion, nothing added); no model constant touched (git diff empty for carbonate_equilibrium / general_coupled / bridge / smartchem); result JSON numbers reproduced; full suite re-run.

1. **H2 CORROBORATED (model-vs-model, within the PHREEQC comparison domain): the Na-carbonate pairs ARE the dominant cause of the high-Na SmartChem-vs-PHREEQC(minteq.v4) divergence.** The controlled contrast is clean: SmartChem (no pairs) tracks PHREEQC-NO-pairs to |SC−no| ≤ 0.017 pH across every in-domain case, while the SmartChem-vs-PHREEQC-WITH-pairs gap is almost entirely the pair term (C2: SC−with +0.108 vs SC−no −0.000; C4: SC−with +0.126 vs SC−no +0.017). Dose-response confirms mechanism: delta_pH and the Na-bound fraction grow monotonically with Na (holdout 0.5/1.0/1.5 → −0.004/−0.073/−0.142; bound 0.010/0.022/0.116), and the Na=0 cases are an exact null (delta_pH = 0). The pairs bind Na⁺ (up to 23% at C4) and lower pH; NaHCO3 dominates the binding at low-moderate Na, NaCO3⁻ at high Na.

2. **The pair correction is REFUTED at the measurement level (the §6D warning, realized).** For the NIST SRM 191d buffer, adding the pairs moves PHREEQC from 9.999 → 9.857, i.e. ~0.14 pH AWAY from the certified 10.014 (|residual| 0.015 → 0.157) and from Table A1 (0.015 → 0.156). A Na-pair model that improves agreement with minteq.v4's own self-consistent speciation DEGRADES agreement with the measured anchor. A correction preferred only because it matches another MODEL better, while moving away from the MEASUREMENT, is not an improvement in predictive validity — it must be co-calibrated with the activity model and the measured anchor, not bolted on.

3. **DISCLOSED — the low-Na floor offset is a SEPARATE, smaller effect, not resolved here.** SmartChem sits ~0.0023 pH below PHREEQC even at Na=0, where the pairs do nothing; and the ablation isolates ONLY the two pair reactions — the Davies-vs-b-dot activity model, the molal-vs-molar basis, and the K1/K2 lineage are NOT separated from one another (they sit, small, in the SC−no column). So H2 is corroborated as the dominant HIGH-Na cause; the residual low-Na offset is H3/H4 territory, DARK here.

4. **Domain admission (§6E).** Numerical-convergence domain: in-domain across the grid (max I 0.30). Activity-model / reference-solver-agreement domain: coincident here (PHREEQC is both the ablated model and the reference), so this is NOT an independent derivation of the pair constants. **Experimental-validation domain: EMPTY — the one measured anchor says the pairs move the wrong way.** Net: "Na-carbonate pairs explain the high-Na model-vs-model gap" is CORROBORATED; "Na-carbonate pairs improve the physical prediction" is REFUTED by the only measurement available.

This is a truth-debt result: the obvious "add the missing ion pairs" fix explains the benchmark divergence yet does NOT improve — it worsens — the measured prediction. Reported, not tuned away.
