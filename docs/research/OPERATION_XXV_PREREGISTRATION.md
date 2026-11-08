# OPERATION XXV: preregistration of a measured calcite holdout (Guidone et al. 2025)

**Status:** RULES FROZEN. This file is committed before the open-air calcite model it will test exists, and long before
that model is evaluated at the holdout state. A second, dated addendum (§9) will pin the exact model identity before the
run. Nothing in §1–§8 may be edited after this commit; corrections go in a dated addendum that says what changed and why.

## 1. The measurement

- **Source:** Guidone et al., *RSC Advances* 2025, 15, 38762–38773, DOI 10.1039/D5RA05547D, Table 1 (calcite-saturated
  solution, CSS, under air).
- **Frozen dataset:** `experiments/sandbox_foundation/holdouts/guidone2025_table1_transcription.json`,
  sha256 `9f33b5407bf775bc4cf18afbf43961fb9e1011e45796fca2c51f5ac912a819ea`.
- **Primary quantity:** [Ca]tot = (5.79 ± 0.27) × 10⁻⁴ M, where ± is 2σ of mean values. Measured interval
  **M = [5.52, 6.06] × 10⁻⁴ mol/L**. Replicate count: not stated.
- **Read twice:** two independent readers (different tools; the second was given no numbers) agree on every Table 1
  value and on the conditions. The article bytes could not be pinned (bot-challenge pages), so the transcription is the
  frozen dataset.

## 2. Independence and shared source families

| quantity used by the model | fitted to | relation to the holdout |
|---|---|---|
| log Kc (calcite), CaHCO₃⁺, CaCO₃° | Plummer & Busenberg 1982's own ~350 Ca–pCO₂ measurements, 0–90 °C | independent: the measurement is from 2025 |
| K_H, K₁, K₂ (CO₂–H₂O) | critical evaluation of pre-1982 literature (P&B 1982) | independent by date |
| Davies activity model | no fit to this system | — |

- The holdout is **not** common-mode by data: no constant was fitted to it.
- It **is** common-mode by physics with any PHREEQC comparison: phreeqc.dat carries the same P&B expressions. A PHREEQC
  agreement is verification (model-vs-model), never validation.
- The holdout tests a combination (Kc·K₁·K_H/K₂, ion pairs, activity model, the open-system boundary), not Kc alone.

## 3. Disclosures (things known before this registration)

1. A research subagent computed a **PHREEQC proxy at the holdout state before registration**: 5.71 × 10⁻⁴ M at
   22 °C and 425.6 ppm (phreeqc.dat, WATEQ Debye–Hückel, with ion pairs). The registrant knows that number. The rule
   below is the standard interval construction from stated uncertainties; it was not tuned to that proxy. The sandbox
   model (Davies activity, its own species set) has never been evaluated at this state.
2. pCO₂ was **not measured** (PROBE-GAP). Lab pressure and humidity are not stated.
3. The ±2 °C convention is not stated; it is treated as a **bound**.
4. [Cl]tot = 8.4 × 10⁻⁵ M (an unmeasured counter-cation) is omitted from the primary prediction (estimated
   effect +0.2%, a model estimate).
5. The measured-vs-modeled row mapping comes from the caption and typography (reader 1) and from the text (reader 2).
   Both readers agree.

## 4. Modeled state and envelope

- System: calcite + pure water + CO₂(g) at fixed partial pressure, at equilibrium (open system).
- Constants: Plummer & Busenberg 1982 analytic temperature laws, evaluated at the stated T inside their validity ranges,
  transported molal → molar by the existing standard-state transport.
- **Envelope (the prediction grid):**
  - T ∈ {293.15, 295.15, 297.15} K (22 ± 2 °C as a bound);
  - log Kc shift ∈ {−0.020, 0, +0.020} (P&B's stated ±0.020);
  - pCO₂ ∈ {4.00 × 10⁻⁴, 4.2562 × 10⁻⁴} atm.
- **pCO₂ floor:** 4.2562 × 10⁻⁴ is the NOAA 2025 global marine annual mean (425.62 ppm). 4.00 × 10⁻⁴ atm covers
  humidity, barometric pressure and local variation below that mean.
- **Premise (CONJECTURED, declared):** indoor air in an occupied laboratory is not depleted below the outdoor background,
  so the true pCO₂ ≥ 4.00 × 10⁻⁴ atm. With dCa/dpCO₂ > 0 (checked by the runner), every model prediction at this
  floor is a lower bound on the model's prediction at the true pCO₂.
- **Uncertainty propagation:** the prediction interval P = [min, max] over the full grid (2 × 3 × 3 = 18 points).
  The uncertainties of K_H, K₁ and K₂ are **unstated** in the source and are not propagated; P is therefore a lower bound
  on the model's own uncertainty, and this is stated in the receipt.

## 5. Verdict rule (applied mechanically by the runner)

- **PASS** iff P ∩ M ≠ ∅.
- **FAIL_HIGH** iff min(P) > max(M). The model predicts more Ca than was measured even at the lowest admissible
  pCO₂; no unmeasured indoor CO₂ can rescue it.
- **FAIL_LOW** iff max(P) < min(M) and the pCO₂ the model needs to reach min(M) (bisection at T = 293.15 K,
  log Kc + 0.020) exceeds the declared ceiling of **2.0 × 10⁻³ atm** (2000 ppm, CONJECTURED as implausible for the
  stated lab air).
- **AMBIGUOUS** otherwise.

## 6. Mutated-source controls (the instrument must be fail-capable)

The run is **INVALID**, and no verdict is reported, unless every control behaves as predicted:

| control | mutation | predicted outcome |
|---|---|---|
| C1 | log Kc shift +0.60 on every grid point | FAIL_HIGH |
| C2 | log Kc shift −1.50 on every grid point | FAIL_LOW |

The shifts are sized so that each predicted outcome holds even if the unmutated model differs from the PHREEQC proxy by
±30% (Ca scales roughly as Kc^(1/3)).
| C3 | 25 °C constants evaluated at 295.15 K without the temperature law | REFUSED (source-domain error) |
| C4 | T = 370 K (outside the calcite law's 273.15–363.15 K range) | REFUSED |

## 7. Declared parameter-dependence predictions (model properties, reported, not verdict-bearing)

- d ln Ca/dT ≈ −1.6 %/K near 22 °C.
- Ca ∝ pCO₂^≈0.32.
- ±0.020 in log Kc gives ≈ ±1.5 % in Ca.
- Secondary informational comparisons (no verdict weight): the model's [HCO₃⁻] + [CO₃²⁻] vs measured Ctot
  (1.21 ± 0.10) × 10⁻³ M, and model pH vs 8.3 ± 0.1 (electrode convention unstated).
- The point prediction at (295.15 K, 4.2562 × 10⁻⁴ atm, no shift) and its relative deviation from 5.79 × 10⁻⁴ are
  reported as information only.

## 8. What any outcome is allowed to mean (fixed now)

- This holdout is registered at **tier W (weak, nuisance-limited)**. pCO₂ is unmeasured and the replicate count is
  unstated, so it **cannot by itself satisfy the 2.0-alpha independent-measurement gate, whatever the outcome**.
- **PASS** → CORROBORATED (weak): the model is not falsified at 22 °C in air. It does not validate Kc, a
  temperature slope, or the activity model separately. The run must also state the power: roughly, only a model biased
  high by about 15% or low by about 40% could fail this rule.
- **FAIL_HIGH / FAIL_LOW** → REFUTED at this state. The failure is kept and published, with no re-tuning under this
  registration.
- **AMBIGUOUS** → recorded as such; nothing is upgraded.
- **INVALID** (a control misbehaved) → the instrument is broken; fix it, re-register and disclose.

## 9. Model-identity addendum

To be appended, dated, before the run: the commit SHA of the model, its `model_identity_digest`, the frozen runner JSON
(an encoding of §4–§6 with its sha256), and confirmation that §1–§8 are unchanged since this commit.

---

## 9. Model-identity addendum (2026-11-08, written before any evaluation at the holdout state)

§1–§8 are byte-identical to commit `150225022e703c2f14a766c637b1552309d58a64`, which was pushed to
`origin/research/operation-xxv` before the model existed. The transcription is unchanged (sha256 `9f33b540…19ea`).

### 9.1 Pins

| item | value |
|---|---|
| model `model_identity_digest` (default `model_config {}`) | `0f89db30b9f161d4174876bc2489152726349ce039bd3c495a40a2bc7b5be3e4` |
| runner `runner_sha256` (`experiments/sandbox_foundation/holdout_guidone_xxv.py`) | `c3aed503081f0b4cc5a5981d77746c7f9bdb00cb7419d8c5ac43c161e290385f` |
| frozen runner JSON | `experiments/sandbox_foundation/holdouts/guidone2025_ca_prereg_xxv.json`, sha256 `9f054d207f6a25397a4e39797fdd319aaeaa76419a8877775e1fb721c8ac9485` |
| model code | integration tree `7522711` (the runner refuses to run if either pin differs) |
| run command | `python -m experiments.sandbox_foundation.holdout_guidone_xxv <frozen JSON> <its sha256> <receipt path>` (re-executes itself in a fresh interpreter with an empty bytecode cache) |

Both pins were recomputed by the registrant at `7522711`; the runner sha also matches an independent hash of the file.
A load-only validation of the frozen JSON (no model evaluation) computed M = [5.52, 6.06] × 10⁻⁴ M from the
transcription.

### 9.2 Instrument clarifications (fixed now, before the run)

None of these changes the §5 outcome logic. Each makes §5–§6 precise or stricter.
1. All controls run first. If any control misbehaves, the run is INVALID and the main grid is not evaluated.
2. The C1/C2 shifts are added to every grid shift value.
3. C3 injects seven 25 °C values one at a time at 295.15 K: Kc, the two carbonate formation constants, Kw, K_H, a
   298.15 K Davies A, and a 298.15 K water density. Each must be REFUSED, and the same slot must accept the value made
   at 295.15 K. The second check shows the refusal comes from the temperature, not the injection route.
4. Ca must rise strictly with pCO₂ at every (T, shift) pair, and from the top of the grid to the ceiling. A violation
   makes the run INVALID.
5. The FAIL_LOW bisection tolerance is 0.001 in log₁₀ pCO₂. It affects only the reported pCO₂, not the verdict.
6. A model error anywhere on the main grid makes the run INVALID.

### 9.3 Corrections to §2–§3 (recorded here; the frozen text is not edited)

- **§2 is wrong about phreeqc.dat.** It does not carry the P&B K_H: its CO₂(g) is a different six-term fit. One
  CaCO₃° digit also differs (b = −0.299440 there vs −0.299444 in wateq4f_PWN.dat). The model uses the wateq4f_PWN.dat
  P&B transcriptions. So the §3 PHREEQC proxy (5.71 × 10⁻⁴ M) did not use the model's K_H. On the allowed grid, that
  difference moves Ca by at most 0.27 percentage points.
- **§2 omits constants that are not from P&B 1982.** None of them was fitted to the holdout:
  - Kw is a phreeqc.dat analytic fit; its primary source is not identified.
  - Davies A is anchored at 0.509 at 25 °C and scaled with the Malmberg & Maryott (1956) dielectric correlation.
  - Water density uses the Kell (1975) correlation.
  - The coefficients of both correlations were reproduced from memory (tier `RECALLED_LITERATURE_CORRELATION`).
  - The Kell polynomial was checked in this session against tabulated densities: ≤ 3 × 10⁻⁶ relative over 0–80 °C.
- **Tiers of the P&B sets.** Kc, K_H and K₁ were transcribed from the vendored database files; the equation images in
  P&B were not read. K₂ is printed in the abstract.

### 9.4 Further disclosures

- 425.62 ppm is a dry-air mole fraction. In wet air at 1 atm it is about 4.15–4.20 × 10⁻⁴ atm, which the
  4.00 × 10⁻⁴ atm floor covers. Lab barometric pressure is not stated.
- **In-process trust boundary.** A temperature tag is checked, not believed: a constant stamped with the right T but
  carrying a 25 °C value is not refused. numpy, scipy and site-packages code are not covered by the running-code check.
- **Two independent pre-run reviews** (a numerical red-team, then a provenance red-team) each state that they did not
  evaluate the reserved box.
  - The provenance reviewer re-solved the system from the raw coefficients with its own equations. At four states
    outside the box it agrees with the model to ≤ 7.2 × 10⁻⁴ relative in Ca and ≤ 2 × 10⁻⁴ in pH.
  - That review found five defects in the instrument (no INVALID path; C3/C4 not expressible; an unchecked 25 °C
    Davies A; an interval not bound to the transcription; an unpinned runner). All five were repaired before this pin.
- **Registry.** `holdouts/REGISTRY.json` gains entry `GUIDONE2025-CA-XXV`, recorded as qualified false, tier W,
  outcome PENDING. Tier W can never qualify (§8).
