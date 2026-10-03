# Public branch audit — 2026-10-03

Recorded at the public launch of SmartChem 1.0.0 (`main` at `3dbcdc7`, tag `v1.0.0` →
`8345bbb`). This is a snapshot for future maintainers: which remote branches carry unique
history, which are safe to prune, and one branch that needs attention. No branch was
deleted or modified when this was written — pruning is left to the maintainer.

## Summary

The remote (`origin`) had 36 branch heads at launch. Recomputed from git
(`git rev-list --count origin/main..<branch>`):

- **29 branches are fully contained in `main`** (0 unique commits) — safe cleanup candidates.
- **7 branches carry commits not in `main`.** Of those, one (`move4-cip-rule2-enrichment-2026-09-07`)
  is a merge commit whose *tree* already equals a `main` commit, so by content only **6**
  branches carry unique material. None is active; the most recent unique commit is 2026-09-19.

No secrets, keys, `.env`, or credential-named files were found in any unique branch diff
(this is corroborated by a full-history scanner pass over all reachable refs).

## Branches with unique commits

| Branch | Classification | Unique content |
| ------ | -------------- | -------------- |
| `agent/smartchem-open-semantics-round-20260727` | obsolete but unique | Early (2026-07-27) open-diagram / resistive-DC attempt; `main` has a divergent re-implementation of the same modules. Only `RESEARCH_ROUND_OPEN_SEMANTICS_2026-07-27.md` exists nowhere else. |
| `aletheia/chemical-rule-calculus-2026-09-19` | unique (⚠ live workflow) | Adds only `.github/workflows/rule-calculus-snapshot.yml`. The rule-calculus research itself is already in `main`. **See the note below.** |
| `aletheia/creator-process-research-2026-09-06` | superseded | Its process-contract doc is byte-identical to `main`'s; only a README index line differs. Nothing is lost by pruning. |
| `aletheia/smartchem-genericity-audit-2026-09-03` | unique historical | An earlier, shorter draft of the generic-compiler reorientation audit whose final form is in `main`. |
| `audit/chemical-compiler-reorientation-2026-09-03` | unique historical | A distinct audit draft (`AUDIT_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md`) whose exact filename is not in `main`. |
| `audit/compiler-reorientation-2026-09-03` | unique historical | An earlier snapshot of the generic-reorientation audit; `main` has a later, extended version of the same file. |
| `move4-cip-rule2-enrichment-2026-09-07` | no unique content | A merge commit; its tree equals a `main` commit. Unique by SHA only. |

## Attention item

`aletheia/chemical-rule-calculus-2026-09-19` carries a GitHub Actions workflow
(`rule-calculus-snapshot.yml`) that becomes a live workflow file once the repository is
public. Its trigger is narrow (a push to that branch touching that file) and it declares
`permissions: contents: read` with `persist-credentials: false`, so it does not run on
`main` or on pull requests and references no secrets. It is low risk, but the cleanest
resolution is to delete the branch; its research is already preserved in `main`.

## Cleanup notes

- The 29 fully-contained branches (including `release/1.0.0` and `release/1.0.0-stable`,
  both 0 unique and merged) can be deleted without losing any commit from `main`'s history.
- **Do not mirror-push.** There are local-only `worktree-agent-*` branches (agent scratch
  history) that are not on the remote and should stay that way; `git push --all` /
  `--mirror` would publish them. Only intended branches should be pushed.
- Deleting `agent/smartchem-open-semantics-round-20260727` will **not** remove its commit
  from the public repo: that commit is also reachable via `refs/pull/3/head`, which GitHub
  retains. There are no secrets there, so this is a note, not a hazard.
