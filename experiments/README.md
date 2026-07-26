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
| `decay_analogy_probe.py` | On what set is a cross-scale metaphor actually true? Worked example for `THE_COMPILER.md` §V/§VIII, using "a human life is an isotope" as the specification under test. Analytic, seconds, no PySCF. |

Results and their interpretation live in `RESULTS_polyatomic_cost.md`, which is written in
passes and keeps superseded numbers rather than overwriting them. The last three scripts in
the table above are self-reporting instead — each prints its own verdict, its own boundary,
and (for the last two) an explicit section on what it does *not* establish.

## Running

```bash
OMP_NUM_THREADS=1 .venv/bin/python experiments/polyatomic_cost_probe.py --species H2O
```

Pin the threads and check `uptime` first. This repo has already been burned once by timing
on a contended machine (task #15); a wall-clock number from a loaded box is fiction.
