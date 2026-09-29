# Hosted CI is blocked by an ACCOUNT/BILLING condition (not by this repository)

Status as of 0.9.5 (2026-09-29). Classification: **ACCOUNT / BILLING. Not repository-configurable.**

## The exact blocker

GitHub's own check-run annotation, on every job of every run since run `36490673856` (tip `78554a2`):

> The job was not started because recent account payments have failed or your spending limit needs to be
> increased. Please check the 'Billing & plans' section in your settings

Evidence (latest observed run `36536300449`):

| field | value |
|---|---|
| jobs | `109301026867`, `109301026905`, `109301026748` |
| `runner_id` | `0` (no runner was ever assigned) |
| `steps` | `0` (nothing executed) |
| first affected run | `36490673856` on `78554a2`; every later tip is the same |

Secondary corroboration: the repository is **private on a free plan**, and the branch-protection API answers
HTTP 403 `Upgrade to GitHub Pro or make this repository public`. Together these say the account's hosted-runner
entitlement, not any workflow file, is what stops jobs from starting.

## Why nothing in the repository can fix it

Jobs die at allocation, before a single workflow line runs. The workflow has no self-hosted runner label, no
`if:` gate, no secret or permission dependency that could cause a not-started job; the only workflow in the repo
is `.github/workflows/ci.yml`. Editing YAML, re-running, or pinning actions cannot change a billing decision.

## What restores it (account side only)

1. Resolve the failed payment / raise the Actions spending limit under Settings -> Billing & plans; or
2. make the repository public (hosted minutes for public repos are not metered); or
3. register a self-hosted runner and point `runs-on` at it (a repository change, but it needs a machine the
   owner provides).

Then re-run CI and treat the first green run as the *first* evidence for the workflow changes below.

## Workflow changes made in 0.9.5 -- UNVERIFIED on hosted runners

No hosted runner has allocated, so these were written and reviewed locally only. They are labelled in a YAML
comment at the top of `jobs:`:

- `test` job runs `scripts/run_suite.sh` (OOM-safe batches) instead of monolithic `pytest`, which is OOM-killed on
  a ~7 GB box (a standard private-repo runner is also ~7 GB; that equivalence is *conjectured*, not measured).
- `timeout-minutes` on every job (was the 360-minute default on `test`).
- `runs-on: ubuntu-24.04` pinned (was `ubuntu-latest`, a moving target).
- New `wheel-install-matrix` job: builds the reproducible wheel/sdist (`scripts/build_release.py`) and runs
  `experiments/v0_9_5_install_matrix.py` on the job's Python.

Known difference even when runners return: the `pyscf-smoke` job runs `pytest -m "not slow"` with PySCF
installed, a different population than the committed baseline receipt.

## The local release matrix that substitutes

Until a runner exists, the release gate is local and receipt-based:

| gate | how | where the receipt lives |
|---|---|---|
| full suite, OOM-safe | `scripts/run_suite.sh` (fresh pytest per batch, junit tally, RDKit absent) | the release/audit record under `docs/research/` for the round that ran it (0.9: `V0_9_CAPABILITY_COMPILER_RELEASE_2026-09-28.md`, the Round V audit) |
| clean-install matrix | `experiments/v0_9_5_install_matrix.py` against the artifacts of `scripts/build_release.py` | `install_matrix.json` / `.md` written to the caller-given out dir; the summary is quoted in the 0.9.5 release record |
| mutation gate | `experiments/v0_9_mutation_calibration.py` (+ 0.9.5 successor mutants) | the round's audit record under `docs/research/` |
| artifact identity | `SHA256SUMS` + `release_manifest.json` from `scripts/build_release.py` | out dir of the build; hashes are quoted in the release record |

This substitution is honest but weaker than hosted CI in one respect: it runs on one machine, one operator, at
one time; it proves the tip was green when it was run, not that every later push is.
