# experiments — the scripts that produced the numbers

Every "MEASURED" claim in this repository is supposed to be reproducible. Until
2026-07-26 that was not true of a single one of them.

The measurements were real, but each was run from a session-scoped `scratchpad/` that was
never committed — not once, in the whole history. The 33.5x caching result, the diatomic
geometry-tier MAE of 0.0255 A, the 10-parameter bond-additive ZPE fit at RMS 0.0113 eV:
each is cited in a docstring or a commit message, and each names a script that no longer
exists anywhere.

The consequence is concrete rather than philosophical. The out-of-sample ZPE test needs to
hold data *out* of that fit, and the fit's species roster now survives only as a
commit-message pull-quote — so a legitimately held-out set cannot currently be constructed,
because the training set cannot be enumerated. A project whose entire position is
*measured, not argued* had made its own measurements unfalsifiable.

**So: a script that produces a number worth quoting lives here, committed, before the
number gets quoted.** Scratch exploration still belongs in scratch. The moment a run's
output is going to be cited in a docstring, a README, or a commit message, the thing that
produced it is a research artifact and it comes here.

These are research harnesses, not tests. They are not collected by `pytest`, they may cost
hours of CPU, and several of them deliberately drive internal paths that the public oracle
declines — that is precisely their job, since measuring what a declined path actually does
is how it earns the validation profile that would let it stop declining.

Anything printing a number that is not yet validated must say so, loudly, in its own
output. A harness that produces a confident-looking unvalidated number is worse than no
harness at all.

## Contents

| Script | Question it answers |
|---|---|
| `polyatomic_cost_probe.py` | What does one real polyatomic cost end to end at CCSD(T), and how far off is it? Go/no-go for the whole polyatomic validation plan. |
| `basis_size_probe.py` | Where does CCSD(T) run out of memory, and does frozen core fix it? Prices `t2`/`ovvv`/`vvvv` per species and basis, and calibrates the model against real peak RSS. |
| `vibrational_probe.py` | What is in the harmonic spectrum, mode by mode, and how much ZPE does each mode carry? Built to price H2O2's hindered rotor; it cost 2.9% of the ZPE and the hypothesis died. |
| `multireference_probe.py` | Is a species multireference? Reads CCSD(T) amplitudes at the pipeline geometry for T1, D1, max\|t1\|, max\|t2\| and (T)/E_corr. |
| `zpe_bias_refit.py` | Re-derives `ZPE_BIAS_FRACTION` from the 23-species roster, and decides whether the code applies it to the wrong denominator. Replaces the lost `scratchpad/geom_calibrate.py`. |
| `ccsd_acceleration_probe.py` | Is a candidate CCSD speedup identity-preserving or a measured tradeoff? Runs one species through `conventional`/`direct`/`df`/`df-ri` and **recalibrates itself against the real `PySCFOracle._parts` on every run** before any route number is believed. |
| `stoichiometry_menu_rank.py` | Can the meta-compiler's "here are X admissible completions" menu be *derived* rather than guessed? Exact integer kernel of the composition matrix; backs `THE_COMPILER.md` §IV. Seconds, no PySCF. |
| `nonlinear_menu_rank.py` | Does the derived-menu law survive a non-linear (position/distance) invariant? REFUSE and FILL_IN survive as theorems on complete constraint sets; ENUMERATE has no analogue. Maxwell count and rigidity-matrix rank both give confident wrong answers in opposite directions. Exact arithmetic; seconds, no PySCF. |
| `ccsd_peak_phase_probe.py` | Which phase actually sets the CCSD(T) peak RSS? Partitions one run into nested phases and reads `ru_maxrss` at every boundary; because a high-water mark is monotone, the exclusive delta per phase is exact attribution rather than a sample. Calibrates with its own instrumentation active. |
| `decay_analogy_probe.py` | On what set is a cross-scale metaphor actually true? Worked example for `THE_COMPILER.md` §V/§VIII, using "a human life is an isotope" as the specification under test. Analytic, seconds, no PySCF. |
| `ao_storage_probe.py` | What does the AO integral tensor actually cost, and does `max_memory` control it? Prices `mf._eri` directly instead of inferring it from a peak. |
| `ao2mo_sizing_probe.py` | Which sub-phase of `CCSD.ao2mo` sets the peak, on what budget, and **is a `ru_maxrss` delta even an allocation?** Wraps three PySCF sizing sites and reads the budget at the call boundary rather than reconstructing it from the memory reading that is under suspicion. Registers falsifiable predictions in its docstring before running. |
| `ledger_mutation_probe.py` | Does the test suite notice a wrong implementation? Writes plausible wrong versions of `ledger.py` and `stoichiometry.py` and counts survivors. Restores each target and **verifies byte-identity before exit**; a stale anchor is reported as an error, never as a survivor. |
| `ledger_rank_blowup.py` | How long can a *legal* shepherding dialogue run? Measures rounds against `round_bound` as a function of one declared rank, to keep a termination argument from being read as a practical guard. Exact round counts; wall times are shape, not benchmark. |
| `section_i_end_to_end.py` | Does `THE_COMPILER.md` §I's loop actually run? Four rounds on a real spec including one genuine refinement, every menu derived, ending in an object the category constructs. Backs Brick 4. Seconds, no PySCF. |
| `compiled_h2_vertical.py` | Executes the first approved compiled chemistry vertical: preserved source -> typed request/plan -> approval -> CCSD(T)/cc-pVTZ H2 run -> obligations -> RunRecord/certificate. The durable result note is `RESULTS_compiled_h2_vertical.md`; the JSON journal is an ignored run artifact. |
| `compiled_water_wave_vertical.py` | Executes the first approved cross-domain structural-toy vertical: underidentified phrase -> scientist-confirmed typed water profile/branch/regime/orientation -> exact output contract -> prescribed-background characteristic calculation -> independent recheck -> RunRecord/certificate. It is not a measured flume or continuum wave simulation. The durable receipt is `RESULTS_compiled_water_wave_vertical.md`; the JSON journal is ignored. |
| `compiled_water_wave_validation.py` | Executes the v2 manufactured finite-section compatibility preflight: nominal discharge/head, declared `kh` and Bond-number screens, sign-aware branch/orientation, uncertainty-resolved adjacent-sample bracket, and complete output/casualty retention. It is not a continuous stationary solution or measured validation. Receipt: `RESULTS_compiled_water_wave_validation.md`. |
| `compiled_human_isotope_vertical.py` | Executes the D2a cross-scale structural-identifiability vertical: underidentified metaphor -> scientist-confirmed cohort/population/assembly/exposure/endpoint choices -> exact output contract -> two independently rechecked dynamic-family probability witnesses -> RunRecord/certificate. It emits an underidentification result, not an empirically calibrated mortality model or actual-human/population prediction. The durable receipt is `RESULTS_compiled_human_isotope_vertical.md`; the JSON journal is ignored. |
| `compiled_human_survival_recovery.py` | Executes the separate D2b-S synthetic recovery vertical: content-addressed seeded-binomial independent interval cohorts -> structurally TRAIN-only fixed-family likelihood -> gradient/curvature gates -> conditional likelihood-curvature intervals -> locked HOLDOUT binomial scores -> post-fit same-generator recovery. The intervals are not calibrated confidence coverage; the run is not empirical human calibration, biological validation, toxicology, causality, LD50/LC50 evidence, or transfer authority. Receipt: `RESULTS_compiled_human_survival_recovery.md`. |

Results and their interpretation live in `RESULTS_polyatomic_cost.md`, which is written in
passes and keeps superseded numbers rather than overwriting them — `ao_storage_probe.py` and
`ao2mo_sizing_probe.py` report there too. The rest are self-reporting instead: each prints
its own verdict and its own boundary, and `decay_analogy_probe.py`,
`stoichiometry_menu_rank.py`, `ledger_rank_blowup.py` and `section_i_end_to_end.py` carry an
explicit section on what they do *not* establish. `ledger_mutation_probe.py` and
`section_i_end_to_end.py` exit non-zero when their own checks fail, so they can be run as
gates rather than read as reports.

The compiled H2 vertical is different from a research probe: it exercises the new approval and
certificate seam at existing public coverage. Its durable receipt records the run's relevant
source, plan, approval, calculation, result-artifact, and certificate digests, the one-run
magnitude comparison with repository H2 D0, and what that comparison does **not** establish:
`RESULTS_compiled_h2_vertical.md`.

The compiled water-wave vertical exercises the same seam across domains, but its scientific
evidence is intentionally weaker: `STRUCTURAL_TOY`. The full profile and derived
characteristics are retained, while missing profile provenance, wavelength/capillarity
gates, stationary balance checks, uncertainty, and interpolation validation are certificate
omissions rather than hidden assumptions: `RESULTS_compiled_water_wave_vertical.md`.

The human–isotope D2a vertical exercises the shepherding boundary on a deliberately
underidentified cross-scale metaphor. Its one hypothetical LD50 endpoint is retained as a
dose/protocol/window constraint, never a rate. Two normalized survival families agree at
that endpoint and disagree away from it, so the only executable result is
`UNDERIDENTIFIED_DYNAMIC_MODEL/UNVALIDATED`. The current executor accepts only a synthetic
cohort all-cause target; functional-threshold, cause-specific, individual, observed-data, and
empirically calibrated or predictive probability requests require different semantics and
executors:
`RESULTS_compiled_human_isotope_vertical.md`.

The three executors were then migrated to the closed runtime registry and re-run with fresh,
write-once journal paths. `RESULTS_runtime_registry_migration.md` records that infrastructure
regression; it adds no scientific evidence to the three domain receipts.

## Running

```bash
OMP_NUM_THREADS=1 .venv/bin/python experiments/polyatomic_cost_probe.py --species H2O

# first approved compiled vertical; every run requires a fresh journal path
OMP_NUM_THREADS=1 .venv/bin/python experiments/compiled_h2_vertical.py \
  --journal /tmp/smartchem-h2-run.json

# structural-toy cross-domain acceptance vertical; no PySCF required
.venv/bin/python experiments/compiled_water_wave_vertical.py \
  --journal /tmp/smartchem-water-wave-run.json

# manufactured finite-section compatibility preflight; requires a fresh path
.venv/bin/python experiments/compiled_water_wave_validation.py \
  --journal /tmp/smartchem-water-preflight-run.json

# structural-toy cross-scale identifiability vertical; no PySCF required
.venv/bin/python experiments/compiled_human_isotope_vertical.py \
  --journal /tmp/smartchem-human-isotope-run.json

# selected-family synthetic recovery; no human/animal data or PySCF required
.venv/bin/python experiments/compiled_human_survival_recovery.py \
  --journal /tmp/smartchem-human-survival-run.json
```

Pin the threads and check `uptime` first. This repo has already been burned once by timing
on a contended machine (task #15); a wall-clock number from a loaded box is fiction.
