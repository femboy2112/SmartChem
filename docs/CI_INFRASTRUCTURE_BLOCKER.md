# Hosted CI billing outage (2026-09-28 to 2026-10-01): RESOLVED, kept as the incident record

**Status (2026-10-01): RESOLVED.** Hosted runners allocate again. The current CI evidence for 0.9.5 lives in the
release record ([`V0_9_5_ADVERSARIAL_RC_RELEASE_2026-10-01.md`](research/V0_9_5_ADVERSARIAL_RC_RELEASE_2026-10-01.md),
row "Hosted CI"). This file keeps the record of the outage, the workflow changes written while it lasted, and what
the first live run found. (The file keeps its name so existing links still resolve.)

## The outage

From run `36490673856` (tip `78554a2`), every job of every run carried GitHub's check-run annotation:

> The job was not started because recent account payments have failed or your spending limit needs to be
> increased. Please check the 'Billing & plans' section in your settings

On every affected job, `runner_id` was `0` and `steps` was empty: nothing executed, so those runs were neither green
nor a code failure. The last dead run was `36621668530`, on `main` at `d26f0eb` (the 0.9 merge, 2026-09-29; jobs
`109588320460`, `109588320776`, `109588320815`). Corroboration at the time: the repository was private on a free plan, and the branch-protection API
answered HTTP 403 `Upgrade to GitHub Pro or make this repository public`. No workflow edit could change that. The
condition cleared on the account side: the repository is still private, and on 2026-10-01 the branch-protection API
still answers that 403, so `main` has no protection rule.

## Workflow changes written during the outage, now executed on hosted runners

These were written and checked locally while no runner existed:

- the `test` job runs `scripts/run_suite.sh` (OOM-safe batches) instead of monolithic `pytest`;
- `timeout-minutes` on every job (was the 360-minute default on `test`);
- `runs-on: ubuntu-24.04` pinned (was `ubuntu-latest`);
- the `wheel-install-matrix` job builds the reproducible wheel/sdist (`scripts/build_release.py`) and runs
  `experiments/v0_9_5_install_matrix.py` on 3.10, 3.11, 3.12 and 3.13.

Run `36922045140` (2026-10-01, tip `31316ea`) was the first since the outage to get runners, and it executed all of
them. The `pyscf-smoke` job still runs a different population (monolithic `pytest -m "not slow"` with PySCF
installed) from the `test` job's batched suite without PySCF.

## What the first live run found

Run `36922045140`: six of seven jobs passed; `test (3.10)` failed. In batch 31, 78 tests failed, every one of them
`tests/test_transport_ledger.py::test_every_non_advisory_ledger_entry_refuses_its_keyless_forgery` raising
`AttributeError: 'code' object has no attribute 'co_qualname'`. `code.co_qualname` exists only from Python 3.11, and
the test's own-law lock used it to name the raising frame. This was a test-harness incompatibility, with no production
code involved, and it was invisible locally because the local gates ran on 3.12. Fixed in `d8146c7`: frames are matched
by code-object identity against the code each ledger-named check resolves to.

The run also showed a diagnosability gap: `run_suite.sh` printed only the path of the failed batch's log, and that
path vanished with the runner. Since `d8146c7`, a failed batch prints a bounded excerpt (first traceback, distinct
exception lines with counts, short summary). The `test` job also writes its logs to `$RUNNER_TEMP/smartchem-suite`
and uploads them as an artifact on failure.

## The local gates

While runners were down, the full suite, install matrix, mutation gate and artifact hashes all ran locally and were
recorded in each round's release or audit record under `docs/research/`. Hosted CI now runs the full suite on 3.10 and
3.12, the install matrix on 3.10–3.13, and the PySCF smoke test. The mutation gate, behaviour freeze, funnels,
differential and fuzzers are not in CI; they stay local, receipt-based gates.
