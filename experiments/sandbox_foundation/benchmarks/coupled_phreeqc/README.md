# coupled_phreeqc — the MIXED vinegar/bicarbonate independent benchmark (Operation XIII P0)

The mixed acetate+carbonate interior is the object with **no PHREEQC column** and **no limiting-case free check**
(the acetate and carbonate parents each have their own benchmark; the mixed interior is the genuinely new thing).
This directory is its independent-benchmark rig, mirroring `../acetate_phreeqc/` and `../carbonate_phreeqc/`.

**PHREEQC is absent on the committed baseline.** So the independent cross-check here is TWO-tiered and honest:

1. **Already run, committed:** an arbitrary-precision (60-digit `decimal`) independent-ALGORITHM holdout —
   `coupled_reference_hp.cross_check` — agrees with the production float64 two-route solve across the whole mixed
   grid (`hp_tier_davies == NUMERICALLY_VERIFIED` in `comparison_table.json`). This catches a float64 cancellation
   that production's two shared-precision routes could both miss (§2C). It is `NUMERICALLY_VERIFIED`, not
   `BENCHMARKED_AGAINST_REFERENCE_SOLVER` — common-mode on the shared constants/Davies law.
2. **Deferred, reproducible:** the exact PHREEQC `inputs/*.pqi` decks (minteq.v4 primary, llnl secondary) + the
   runner `run_phreeqc.py`. The PHREEQC pH column stays null (`EXTERNAL_VALIDATION_UNAVAILABLE`) until a real run
   signs it. **No PHREEQC number is fabricated.**

## Files
- `cases.py` — the authoritative case grid (imported by both runners; single source of truth).
- `generate_inputs.py` → `inputs/*.pqi` — the committed PHREEQC decks (11 cases × 2 databases = 22).
- `run_code.py` → `code_results.json`, `comparison_table.json` — the code column + the HP cross-check tier.
- `run_phreeqc.py` → `phreeqc_results.json` (NOT committed) — run in an isolated scratch venv WITH `phreeqpython`.
- `PREREGISTRATION.md` — written before any PHREEQC run; database determination, cases, metrics, the hard
  verification-vs-validation line.

## Reproduce
```
bash reproduce.sh         # regenerates decks + code_results.json + comparison_table.json (no PHREEQC needed)
```
To add the PHREEQC column later, in an isolated venv with `phreeqpython`: `python run_phreeqc.py`, pin each
database sha256 here, then merge the pH column into `comparison_table.json`.

## Database sha256 (to pin on the first real PHREEQC run)
- `minteq.v4.dat`: _UNPINNED — no run yet_
- `llnl.dat`: _UNPINNED — no run yet_
