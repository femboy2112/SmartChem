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

## Running

```bash
OMP_NUM_THREADS=1 .venv/bin/python experiments/polyatomic_cost_probe.py --species H2O
```

Pin the threads and check `uptime` first. This repo has already been burned once by timing
on a contended machine (task #15); a wall-clock number from a loaded box is fiction.
