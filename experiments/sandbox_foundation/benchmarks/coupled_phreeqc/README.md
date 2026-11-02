# coupled_phreeqc — the MIXED vinegar/bicarbonate independent benchmark (Operation XIII P0 / XVIII Track D)

The mixed acetate+carbonate interior is the object with **no limiting-case free check** (the acetate and
carbonate parents each have their own benchmark; the mixed interior is the genuinely new thing). This directory
is its independent-benchmark rig, mirroring `../acetate_phreeqc/` and `../carbonate_phreeqc/`.

**PHREEQC is absent on the committed baseline.** The cross-check here is TWO-tiered and honest:

1. **Already run, committed:** an arbitrary-precision (60-digit `decimal`) independent-ALGORITHM holdout —
   `coupled_reference_hp.cross_check` — agrees with the production float64 two-route solve across the whole mixed
   grid (`hp_tier_davies == NUMERICALLY_VERIFIED`). It is `NUMERICALLY_VERIFIED`, **not** reference-solver
   benchmarked — common-mode on the shared constants/Davies law.
2. **Reference solver (XVIII Track D):** the mixed grid was run through PHREEQC (minteq.v4 primary, llnl secondary)
   via `phreeqpython`, molar-matched to the code's mol/L basis, and the pH column was merged into
   `comparison_table.json`. `reference_status` is now **`BENCHMARKED_AGAINST_REFERENCE_SOLVER`**.
   **This is solver / activity-model corroboration only — common-mode on the shared Ka/K1/K2/Kw lineage. It is
   NOT independent measured-chemistry validation; external (experimental) validation remains UNKNOWN.** No PHREEQC
   number is fabricated: the column is signed by a real run or it stays null.

## Files
- `cases.py` — the authoritative case grid (imported by every runner; single source of truth).
- `generate_inputs.py` → `inputs/*.pqi` — the committed PHREEQC decks (11 cases × 2 databases).
- `run_code.py` → `code_results.json`, `comparison_table.json` — the code column + the HP cross-check tier.
- `run_phreeqc.py` → `phreeqc_results.json` (gitignored) — molar-matched PHREEQC run; run in a phreeqpython venv.
- `compare.py` → merges the PHREEQC pH + `abs_dpH` + per-DB classification into `comparison_table.json`.
- `PREREGISTRATION.md` — written before any PHREEQC run; databases, cases, metrics, the verification-vs-validation line.

## Metric & thresholds (PRE-REGISTERED, PREREGISTRATION.md §4)
`abs_dpH = |code pH_activity(davies) − PHREEQC pH(molar-matched)|`, per database.
**AGREE ≤ 0.02 · MARGINAL ≤ 0.05 · DIVERGE > 0.05.** Domain of agreement = cases the code ADMITS that AGREE vs
BOTH databases. High-Na cases diverge because the code omits the Na⁺ ion-pairing (NaHCO₃/NaCO₃⁻/Na-acetate) that
PHREEQC includes — a known, documented boundary, not a tuned pass.

## Reproduce
```
bash reproduce.sh         # code side (no PHREEQC) + PHREEQC side (needs phreeqpython + network)
```
To regenerate only the PHREEQC column from an existing `code_results.json` + fetched `db_dl/`:
`python -I run_phreeqc.py && python -I compare.py`.

## Database sha256 (pinned on the XVIII Track D run; USGS phreeqc3 master, 2026-10-22)
- `minteq.v4.dat`: `4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3`
- `llnl.dat`: `1324b807f0f864806fc42df308f6ca7c5e8ce2ed8060d76351452f76beeb819b`
