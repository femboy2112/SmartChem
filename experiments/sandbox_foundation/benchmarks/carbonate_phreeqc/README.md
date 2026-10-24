# Carbonate/CO2 model vs PHREEQC — independent benchmark (Phase III, 2026-10-24)

An independent cross-check of `experiments/sandbox_foundation/carbonate_equilibrium.py`
(`CarbonateWaterSystem.solve`) against **PHREEQC** (via `phreeqpython`), using PHREEQC's own default database
(**phreeqc.dat**) and its own activity model — a *different* activity model (extended Debye–Hückel / WATEQ) and a
*different* constant set than the SmartChem model's Davies + cited constants — so agreement is evidence of
implementation correctness rather than a tautology.

Run in an **isolated scratch venv** (never the SmartChem `.venv`, which stays free of `phreeqpython`). It is
**outside `testpaths`** and does not run in the core suite or the sandbox CI job. See `PREREGISTRATION.md` for the
pre-registered cases, metric, and thresholds; `comparison_table.json` is the committed reference (strict JSON,
`allow_nan=false`).

## Database provenance
- phreeqc.dat, **sha256 `6bb5ebc1d0ecca0e921c13a2241d05d3a3333b142d1d740b2ed03a786442bdf5`**.
- Metric: `dpH = |pH_activity(code, Davies) − pH(PHREEQC)|`. Thresholds (fixed before the comparison): AGREE ≤ 0.05,
  MARGINAL ≤ 0.15, DIVERGE > 0.15.

## Verdict (what the numbers support)

**VERIFICATION-grade (Verified).** Across 11 pre-registered cases (6 open, 5 closed): **9 AGREE, 2 MARGINAL, 0
DIVERGE**, worst `dpH = 0.128`.

| case | setup | PHREEQC pH | code pH (Davies) | dpH | class |
|---|---|---|---|---|---|
| O1 | water, P_CO2 1e-4 | 5.909 | 5.905 | 0.0035 | AGREE |
| O2 | water, atmospheric (log P −3.5) | 5.660 | 5.656 | 0.0034 | AGREE |
| O3 | water, P_CO2 1e-3 | 5.410 | 5.407 | 0.0034 | AGREE |
| O4 | water, P_CO2 1e-2 | 4.910 | 4.907 | 0.0033 | AGREE |
| O5 | water, P_CO2 1e-1 | 4.410 | 4.407 | 0.0034 | AGREE |
| O6 | water, P_CO2 1 atm | 3.911 | 3.907 | 0.0046 | AGREE |
| C1 | 0.01 M NaHCO3 | 8.224 | 8.246 | 0.0221 | AGREE |
| C2 | 0.1 M NaHCO3 | 8.016 | 8.125 | 0.1090 | MARGINAL |
| C3 | half-neutralized buffer | 6.259 | 6.264 | 0.0050 | AGREE |
| C4 | 0.1 M Na2CO3 | 11.261 | 11.389 | 0.1283 | MARGINAL |
| C5 | 0.01 M dissolved CO2 | 4.177 | 4.176 | 0.0010 | AGREE |

- **The open (gas-partition) cases agree to ≤ 0.005 pH** across four decades of P_CO2 — the Henry partition + the
  carbonic equilibria are reproduced essentially exactly at low ionic strength, where the two activity models
  coincide.
- **The two MARGINAL cases (C2, C4) are the high-ionic-strength ones** (I ~ 0.1–0.3). Their ~0.11–0.13 pH offset is
  the genuine difference between this model's **Davies** activity form and PHREEQC's **WATEQ Debye–Hückel**, not a
  solver error — exactly the activity-model gap pre-registered in section 5. The ideal-model code pH is further from
  PHREEQC (as expected), confirming the gap is activity-model, not constant, dominated.
- **No case DIVERGEs**, so no equation or gross constant error is present beyond the activity-model difference.

## Independence is partial (shared-provenance discipline)
PHREEQC and this model both descend from the broad Harned carbonic-acid lineage, so this benchmark corroborates the
**solver**, not independently the **constants**. A genuinely independent *measured* carbonate end-state would be the
stronger V3 rung; none is used or fabricated. The model's `phreeqc_benchmark_obligation()` and this rung both record
`EXTERNAL_VALIDATION_UNAVAILABLE` for that measured datum.

## Scope
Open and closed modes only. The **sealed** finite-headspace mode is validated *internally* (two independent
eliminations agree to ~1e-20; carbon conserves across liquid + headspace to machine precision) and its PHREEQC
cross-check is deferred with an exact `GAS_PHASE -fixed_volume` recipe (PREREGISTRATION.md section 7), pending a
careful reconciliation of PHREEQC's carbon-accounting convention.

## Reproduce
See `reproduce.sh`. In short: make an isolated venv, `pip install phreeqpython`, run `run_phreeqc.py` (writes
`phreeqc_results.json`, not committed), then `run_code.py` (SmartChem venv) and `compare.py` (writes the committed
`comparison_table.json`).
