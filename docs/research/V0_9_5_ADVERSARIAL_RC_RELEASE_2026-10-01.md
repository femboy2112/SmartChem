# SmartChem 0.9.5 — Adversarial Release Candidate ("Cutler Pass") — RELEASE RECORD (2026-10-01)

**Branch** `feat/v0.9.5-adversarial-rc` off `main@d26f0eb` (0.9, merged as PR #93). **Package** `0.9.5a1` (bump
`74414eb`). This record reports the release gate on the final tree. The design and every adjudicated amendment live in
[`V0_9_5_ARCHITECTURE_FREEZE.md`](V0_9_5_ARCHITECTURE_FREEZE.md) (§0–§13 the barrier, §14 rows A1–A17); the behavioural
yardstick is [`V0_9_5_BASELINE_BEHAVIOR_FREEZE.md`](V0_9_5_BASELINE_BEHAVIOR_FREEZE.md); the public contract is
[`COMPATIBILITY.md`](../../COMPATIBILITY.md); the stage map is [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).

## The five jobs, and where each one was discharged

1. **Shrink accidental complexity without semantic movement.** One verification pipeline with one per-load
   `VerificationContext`, one immutable `VerificationPolicy` (legacy keywords mapped onto it), an out-of-band
   loader-issued `VerifiedLoad` / `VerificationReceipt` (freeze §2–§4, §9). Judged against the baseline freeze: every
   drifted key classified, no verdict moved (re-freeze ledger rows 1–3).
2. **Bound all verification work.** Deterministic counters, each charged before the work it bounds; exhaustion refuses
   and never skips (§5). Canonicalisation bounded and budgeted (S16 → A7/A11, then A13: atom ceilings before any
   refinement, metered passes, a per-call ceiling, the placement search's aggregate, wire molecules refused before
   construction); capability re-derivation budgeted and nesting depth bounded (A16).
3. **Close the minimal pre-1.0 gaps.** `require_canonical_transport` (S1), resonance material identity (S7/S8),
   **StreamDisposition** — the one permitted semantic closure — with its synthetic `CAPABILITY_FIT` witness and
   deletion tests (§6, S10/S14).
4. **Attack end to end.** Waves C1–C8 and the non-author Wave D re-review found reachable defects; every one is fixed
   and pinned by a test and a killed mutant (A1–A17). The A13–A17 fix delta then faced a fresh non-author Wave E (two
   adversaries, front door + capability/loader): no false `CAPABILITY_FIT`, false VOUCH or acceptance-by-exception, but
   three P1s (an aromatic-bond hallucination, A17's own quadratic bound, `capability_work` blind to components) and
   several P2s — all fixed in A18 and re-gated below.
5. **Freeze public semantics.** `COMPATIBILITY.md`, `docs/ARCHITECTURE.md`, and re-freeze #3 at the release tree.

## Release gate (the final tree)

The gate ran twice: on the bump `74414eb`, and — after Wave E's fixes (A18) — again in full on `037a9fa`. The table
reports the final run; where the first run found something, the fix is named.

| gate (freeze §13) | result on the final tree | evidence |
|---|---|---|
| Full OOM-safe suite | **7505 passed, 0 failed, 0 errors, 46 skipped** (7551 collected) | `scripts/run_suite.sh` on `037a9fa`: 7503 / 2 failed — two A14 tests pinned the `:` law's old message, which A18 re-worded to name an *aromatic* ring; re-read (`b16749e`) and that batch re-run green (303 passed). The first run (`74414eb`) found an A15 comment naming reagents in the capability core (the Round V grep law), fixed comment-only (`5a75026`). Skips: 32 RDKit-gated, 14 `--runslow`; PySCF present |
| All ACTIVE mutants killed, 0 void | v0.9 **375 / 375** (full run on `b16749e`, exit 0), RETIRED 4 with **0 void**, DEFERRED 0 · v0.8 **20/20** · v0.7 **17/17** · v0.6 **14/14** | full v0.9 harness on `037a9fa`: 374/375, 0 void — M-A15-3's anchor line gained A18's ASCII prefix; re-anchored and KILLED. First run: M250's witness masked by A14's stronger law, re-read (`cc932b2`) |
| Baseline freeze: no unexplained drift | re-freeze #3 (147 keys = the version bump, proven by a version-revert control, + Wave C8); after A18 a fresh `--check` reads **NO DRIFT**; adjudicator **NO VERDICT MOVED** | behaviour-freeze ledger row 3 |
| Frozen RC funnel, every denominator | **63 / 63 MATCH** with `--require-landed S1,S7,S8,S10,S14` | `experiments/v0_9_5_rc_funnel.py` |
| Capability funnel | **34 / 34** properties hold; **zero production `CAPABILITY_FIT`** under every profile | `experiments/v0_9_capability_funnel.py` |
| Default verification work bounded | budgets refuse no honest corpus load; the only honestly-compiled payload a default budget refuses is the declared hostile large target (`work_per_target` 473,200 > 32,768, in **0.19 s**; ~130 s cold at 0.9.0a1); the 1,792-bottle hostile bench is refused by `capability_work` (20,480 > 16,384); measured honest maxima: `capability_work` 1,296, nesting depth 28 | `experiments/v0_9_5_loader_bounds.py` (full: 109 payloads / 108 loads) |
| Canonicalisation identity preserved | **PASS, 3,570 / 3,570 byte-identical**, 0 cold/warm disagreements, 0 honest loads refused, placement bound hits 8 (unchanged); A13 tree full run: PASS 4,467 / 4,467 | `experiments/v0_9_5_canonical_differential.py` |
| Loader shape safety | **18,599** inputs over 15 public entry points, **0 untyped escapes** (base tree: 4,116) | `experiments/v0_9_5_loader_bounds.py --fuzz` |
| Boundary fuzz | 1,725 cases, **0 new findings** (2 known-boundary hits, the declared A1-F3 convention) | `experiments/v0_9_5_boundary_fuzz.py` |
| Fresh adversarial review of the fixes | Wave E (two non-author adversaries on the A13–A17 delta): no false FIT / VOUCH / acceptance-by-exception; 3 P1 + P2s found and fixed (A18), every one pinned by a test and a killed mutant | freeze row A18 |
| Deterministic stress | **8 / 8 invariants PASS**, 0 fail, 0 pending, 0 vacuous | `RESULTS_v0_9_5_stress_AFTER.md` (BASELINE config, seed 20260929) |
| Performance (before → after) | every honest payload loads, **0.65–0.97×** the BASELINE time (box load 1.6–2.5; ±30%) | `RESULTS_v0_9_5_verification_performance_AFTER.md` vs `_BASELINE.md` (COLD n=3, WARM n=5) |
| Build / install on 3.10–3.13 | **ALL ENVIRONMENTS AGREE**, wheel + sdist × 3.10 / 3.11 / 3.12 / 3.13 (none unavailable) | `RESULTS_v0_9_5_install_matrix.md` (+ release SHA256SUMS at `037a9fa`) |
| README examples | every compiler example runs with its documented outcome | exit 0/2/3/4/5 as documented; the poor-man isopentyl example = its frozen INCOMPLETE/4 |
| CI | hosted CI is infrastructure-dead (runners never start; account billing) — the exact external blocker is documented | `docs/CI_INFRASTRUCTURE_BLOCKER.md` |

## Declared boundaries (stated, not hidden)

- **Worst cases are bounded, not small.** At the slowest measured rate (≈0.8M units/s, a dense hostile graph): ~41 s
  for one canonicalisation at the per-call ceiling, ~22 min of canonicalisation for one load at the default
  `canonical_work` (2^30, 9.2× the honest maximum), ~3.6 min for a resonance placement search at its ceiling (one
  search per parse). Per-leaf
  edge sorting is unmetered (the 5.3× rate spread). A caller may lower any budget.
- **AUTO fallthrough.** A string refused as SMILES is still offered to the formula grammar under AUTO (`[CH10]` →
  formula CH10); the result has no structure and every structural verb refuses it (COMPATIBILITY §5).
- **A17 weakened one leg.** The S5 DAG-height check now uses the proven search bound, so a deeper search's DAG whose
  height still fits that bound is not refused by this leg; the receipt bind stays the DAG depth's primary authority.
- **Zero production `CAPABILITY_FIT`.** `CAPABILITY_FIT` is representable (the synthetic StreamDisposition witness) and
  no corpus page states a disposal, so no production route reaches it. That is the honest state.
- **Not re-run:** `python -m smartchem.bench` (the quantum-accuracy benchmark, outside the compiler's gates) timed out
  at 900 s on the loaded box.
- Deferred representation gaps (evidence subject binding, temperature domain laws, lower-bound-only requirements):
  freeze §8.

## Coordinates

Commits after the 0.9 merge, in order: the S-wave consolidation and Wave C fixes (through `6c7501f`); `18e9d8b` S17;
`426c1f6`; `cf2018f` A12; `82cb188` + `cdcdf88` S16 follow-up; `1fc9068`; `376a836` A14; `96a8863` + `2ac01a9` A15;
`1d50348` A16; `9b95a12` A17; `5e286fe` + `ccefc0e` A13; `74414eb` bump; gate-found fixes (`5a75026` grep-law comment,
`cc932b2` M250 re-read), harness fixes, docs, re-freeze #3 (`90faf43`); `037a9fa` A18 (Wave E); then the re-gate and
docs.
