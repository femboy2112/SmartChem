# Carbonate / CO2 model vs PHREEQC — pre-registration

Independent cross-check of `experiments/sandbox_foundation/carbonate_equilibrium.py` (`CarbonateWaterSystem.solve`)
against **PHREEQC** via `phreeqpython`, run in an **isolated scratch venv** (never the SmartChem `.venv`). Mirrors the
acetate benchmark's discipline: sections 0–7 fixed before the comparison; amendments recorded after.

## 0. What is being compared, and the epistemic rung

PHREEQC solves the same *kind* of equations (carbonate acid–base + Henry gas partition) from its **own** database
(phreeqc.dat) with its **own** activity model (an extended Debye–Hückel / WATEQ form, distinct from this model's
Davies). Agreement is therefore **equation/implementation VERIFICATION** (did we solve the chemistry right?), and —
because phreeqc.dat's carbonic constants share the broad Harned lineage this model cites — at most *partial*
corroboration of the constants. It is **not** independent experimental validation (that needs a measured datum; it
stays `EXTERNAL_VALIDATION_UNAVAILABLE`). The two activity models differing by O(0.1) pH at I ~ 0.1–0.3 is expected
and is the dominant source of any residual.

## 1. Database and provenance
- Database: **phreeqc.dat** (PHREEQC default; the carbonate system CO2(aq)/HCO3-/CO3-2/CO2(g) is native to it).
- Pinned by sha256 in `README.md` and recorded in `phreeqc_results.json` / `comparison_table.json`.
- `phreeqpython` version is recorded by `reproduce.sh`; the run is deterministic.

## 2. Case grid (fixed in `grid.json`, 25 °C)
- **OPEN** (fixed P_CO2, pure water): P_CO2 ∈ {1e-4, 10^-3.5, 1e-3, 1e-2, 1e-1, 1.0} atm.
- **CLOSED** (fixed dissolved total carbon): 0.01 M NaHCO3; 0.1 M NaHCO3; half-neutralized (0.1 C / 0.05 Na) buffer;
  0.1 M Na2CO3; 0.01 M dissolved CO2 (no base).
- **SEALED** (finite headspace) is **out of scope for this run** — see section 7.

## 3. Units convention (declared)
The code side is molar (mol/L); PHREEQC is molal (mol/kgw). The same numeric values are used on both sides. At ≤ 0.2 M
and 25 °C, ρ ≈ 1 kg/L, so the molar/molal difference contributes **< 0.01 pH** — sub-dominant to the activity-model
difference (section 0). No density match is performed (unlike the acetate benchmark); this is recorded as a known,
bounded, sub-dominant offset, not a hidden assumption.

## 4. PHREEQC recipes (fixed)
- OPEN: `SOLUTION` pure water + `EQUILIBRIUM_PHASES CO2(g) <log P> 10.0` (10 mol available ≈ infinite reservoir). The
  equilibrated (last) SELECTED_OUTPUT row is read.
- CLOSED: `SOLUTION` with `Na`, `C(4)` totals and `pH 7 charge` (pH found by charge balance; no gas phase).

## 5. Metric and thresholds (fixed BEFORE the comparison)
- Metric: **dpH = |pH_activity(code, Davies) − pH(PHREEQC)|**. Both sides nonideal; the code ideal pH is reported for
  context only.
- Classification: **AGREE dpH ≤ 0.05 · MARGINAL dpH ≤ 0.15 · DIVERGE dpH > 0.15**.
- Justification (physics, not tuning): two *different* activity models on solutions to I ~ 0.3 differ by O(0.1) pH by
  construction, so AGREE is set at the low-I floor and MARGINAL spans the expected activity-model gap. A DIVERGE would
  signal a real equation/constant error beyond the activity-model difference.
- Secondary: any CODE refusal is recorded as an outcome, not scored as agreement.

## 6. Verification vs validation (the ladder)
V0 the model's own always-on invariants (charge/carbon balance, route agreement) → **V1/V2 this benchmark**
(code-vs-PHREEQC, different activity model + database: solver verification + partial constant corroboration) → V3 an
independent *measured* end-state (NOT available here; never fabricated).

## 7. Scope boundary — SEALED deferred (with the exact recipe)
The sealed finite-headspace mode is **validated internally** (two independent eliminations — bracket h vs bracket
P_CO2 — agree to ~1e-20, and carbon conserves across liquid + headspace to machine precision; see
`tests/test_carbonate_equilibrium.py`). Its PHREEQC cross-check is deferred because the carbon-accounting semantics
must be matched carefully: a first attempt with `GAS_PHASE -fixed_volume` had PHREEQC report solution `C(4)` equal to
the *input* total while also equilibrating a gas phase, i.e. the "total carbon" convention did not line up
apples-to-apples with the model's "total carbon = liquid + headspace". The pre-registered recipe for the future run:
`SOLUTION` (all carbon as C(4)) + `GAS_PHASE 1 -fixed_volume -volume <V_gas> CO2(g) 0.0`, reconciling that PHREEQC's
solution-`C(4)` is the *aqueous* carbon and the gas carbon must be added to it to equal the model's total. Until that
is run, the sealed PHREEQC rung is `EXTERNAL_VALIDATION_UNAVAILABLE`.

---

## Amendments (recorded AFTER the first comparison)
- **A0 (setup, before any pH was scored):** the PHREEQC OPEN recipe initially used `pH 7 charge` together with
  `EQUILIBRIUM_PHASES`, which suppressed the CO2 equilibration (every open case returned pH 7). Corrected to a plain
  pure-water `SOLUTION` + `EQUILIBRIUM_PHASES`, reading the *last* SELECTED_OUTPUT row (the equilibrated state, not the
  initial solution). This is a harness-correctness fix, not a tolerance change.
- **A1 (transparency):** calibration probes (OPEN water at log P=−3.5 → PHREEQC 5.660; CLOSED NaHCO3 → 8.016) were run
  while debugging the harness, so the section-5 thresholds are physics-justified rather than fully blind. The AGREE/
  MARGINAL split (0.05 / 0.15) reflects the expected activity-model gap and was not moved to reclassify any case.
