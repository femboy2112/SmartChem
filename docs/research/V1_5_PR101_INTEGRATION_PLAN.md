# PR #101 integration plan -- split / stacked order for the 1.1 candidate vs the 2.0 sandbox

Ooh yeah, can do! This is a PLAN, not an action: nothing here was committed, pushed, merged, tagged, versioned or
rewritten. Every claim below is grounded in git/file evidence gathered on **2026-10-20** against
`feat/chemical-graph-projections` @ `c1b8e36` (PR #101: `OPEN`, `isDraft: true`, base `main`, `MERGEABLE`, per
`gh pr view 101`). `main` = `origin/main` = `99fce34` (`__version__ = "1.0.0"` there; tag `v1.0.0` exists).

## 0. Hard constraints (stated before the proposal, because the proposal is bounded by them)

1. **No destructive rewrite of the shared branch.** `feat/chemical-graph-projections` is the PR #101 head. No
   `rebase`, `reset --hard`, `commit --amend`, squash or filter on it.
2. **No force-push.** Every proposed unit below is a NEW branch name whose tip is an EXISTING commit SHA already
   on the PR branch (a pure `git branch <name> <sha>` pointer). Pushing a new branch name needs no force.
3. **No duplicated historical fixes.** No cherry-pick: a cherry-pick re-mints a commit under a new SHA and the same
   fix would then exist twice (once in the stacked unit, once in PR #101's history). Contiguous-prefix cuts of the
   existing linear history avoid that by construction.
4. **Branch-based issue reconciliation is preserved.** Issues #103-#132 are OPEN on `main` and correctly so
   (`V1_5_RELEASE_PROGRAM.md` section 6 and its "Issue-state reconciliation" table). A fix that is `Verified` on an
   unmerged branch is NOT resolved on `main`. Close each issue when the unit that carries its fix MERGES to `main`,
   never on the claim. Splitting the PR changes WHICH merge closes which issue (table in section 4); it never
   permits an earlier close.
5. **No merge, tag, release or version change without explicit authorization.** In particular
   `__version__ = "1.1.0a1"` (set at `2f9bd11`) is an ALPHA string; turning it into a stable `1.1.0` is a separate
   authorized act, not part of this plan.
6. **Repo convention noted, not silently overridden.** `ROADMAP.md` records "one non-stacked PR/item off fresh
   `main`, `--merge --delete-branch`" as the standing practice. PR #101 itself already violates that (46 commits,
   one branch), so the options below are offered for the owner to choose; section 5 lists the decision needed.

## 1. Evidence base (what the branch actually is)

| fact | value | evidence |
|---|---|---|
| commits `main..HEAD` | **46**, linear (single-parent chain, merge-base = `main` = `99fce34`) | `git log --oneline main..HEAD`; `git merge-base main HEAD` = `99fce34...` |
| size | 92 files, +10361 / -346 | `git diff --stat main..HEAD` |
| `main..34e1891` (#114) | **39** commits, 73 files, +7146 / -346 | `git diff --shortstat main..34e1891` |
| `34e1891..c1b8e36` | **7** commits, 22 files, +3216 / -1 | `git diff --shortstat 34e1891..HEAD` |
| files under `smartchem/` | 14 files changed, all introduced at or before `34e1891` | per-commit `--name-only` walk; `git diff --name-only 34e1891..HEAD` lists NO `smartchem/` path |
| sandbox/2.0 files at `34e1891` | **0** | `git ls-tree -r --name-only 34e1891 \| grep -E "sandbox_foundation\|V2_0\|V3_0\|PHYSICALIZATION"` -> 0 lines |
| sandbox imports of `smartchem` | **none** (imports: numpy, scipy, pytest, stdlib, sibling sandbox modules) | `grep` of `from`/`import` lines across `experiments/sandbox_foundation/*.py` |
| `experiments/` packaging | kept in git for reproducibility, not part of the installable | `pyproject.toml` comment at line 58 |
| working tree | **dirty**: `experiments/sandbox_foundation/twocell.py` and `.../tests/test_probe_e_complexes.py` modified, uncommitted | `git status --short` -- another lane's in-flight work; it is NOT in `c1b8e36` and this plan does not touch it |

The load-bearing finding: **the history is already a clean prefix split.** Everything production-scoped is in
`main..34e1891`; everything experimental/2.0 is in `34e1891..c1b8e36`. No commit in the first range touches the
sandbox, and no commit in the second range touches `smartchem/`.

## 2. Production-release scope vs experimental 2.0 scope

### 2a. Production-release scope -- `main..34e1891` (the minimum stable 1.1 candidate)

`smartchem/` (14 files): `graph_projection.py` (+1227), `graph_cli.py` (+179), `depiction.py` (+141),
`cli.py` (+4), `experiment/reaction_type_oracle.py` (+792 net churn, the recognizer registry), `experiment/step.py`,
`experiment/routes.py`, `service.py`, `structure_descent.py`, `diels_alder.py`, `lateral_rewrite.py`,
`algebra_profiles.py` (+19, the `bond-order-edit-v1` profile), `__init__.py` (the `1.1.0a1` bump).
Plus `tests/` (36 files, +2026 / -106), the production `experiments/*.py` harnesses (`activated_acyl_transfer_110`,
`sulfonate_ester_transfer_111`, `bond_order_edit_profile_114`, `pericyclic_layer_a_fuzz_132`,
`independent_recognition_corpus_s3`, `candidate_starvation_127`, `lateral_reachability_s6`,
`synthesis_coverage_corpus`, three hardened `poor_man_*` probes), `pyproject.toml` (+4, optional `depiction`
extra), `scripts/graph_projection_demo.py`, the CI PySCF-smoke fix (`3a37d46`), `docs/ARCHITECTURE.md`,
`ROADMAP.md`, and the production research docs (graph handoff/checkpoint, coverage audit, coverage ledger,
`V1_1_COVERAGE_EXPANSION_110.md`, the two re-frozen JSON goldens, `V1_5_RELEASE_PROGRAM.md`).

### 2b. Experimental 2.0 scope -- `34e1891..c1b8e36`

| commit | what | paths |
|---|---|---|
| `b070ee0` | 2.0 contract + 3.0 flagship plan | `docs/research/V2_0_PHYSICAL_MECHANISM_CONTRACT.md`, `V3_0_VINEGAR_BICARBONATE_FLAGSHIP.md` |
| `2802213` | two-cell universe prototype | `experiments/sandbox_foundation/` (13 files, +1817) |
| `b4a8411` | reaction complexes (not just net stoichiometry) | `experiments/sandbox_foundation/` (5 files) |
| `52efd13` | detailed-balance / Wegscheider instrument | `experiments/sandbox_foundation/` (2 files) |
| `d7c2e87` | separate CI job `sandbox-foundation` (py3.10, 3.12) | `.github/workflows/ci.yml` only (+36) |
| `c1b8e36` | Physicalization Round II record | `docs/research/PHYSICALIZATION_ROUND_II_2026-10-20.md` |
| `8d327c9` | roadmap / issue-state reconciliation | `ROADMAP.md`, `docs/research/V1_5_RELEASE_PROGRAM.md` -- **mixed**, see note |

Note on `8d327c9`: it is documentation about the 1.1 candidate, but its table says #105/#130 are deferred to
`V2_0_PHYSICAL_MECHANISM_CONTRACT.md`, a file that only exists from `b070ee0`. Placed in the 1.1 unit it would
point at a document not in that unit, so it travels with the 2.0 unit (it is a docs-only commit; no behavior).

### 2c. Isolation proofs already in the repo

* The sandbox is outside `testpaths = ["tests"]` and outside `scripts/run_suite.sh` (which collects only
  `tests/test_*.py`) -- stated in the `d7c2e87` CI comment -- so the core runner and the released package never
  execute it.
* The sandbox job in `ci.yml` is its own job (`fail-fast: false` matrix), so a red sandbox cannot be confused with
  a red core.
* `git diff --name-only 34e1891..HEAD` contains no `smartchem/` or `tests/` path. Dropping the 2.0 unit leaves the
  production tree byte-identical to `34e1891`.

## 3. Production 1.1 candidate -- internal dependency order

The 39 production commits are contiguous and form five dependency bands. Dependencies are derived from which
files each commit touches and which module it reads (evidence column), not assumed.

| band | commits (chronological) | n | theme | depends on | evidence |
|---|---|---|---|---|---|
| **A** workbench | `118d180` `f4d2620` `0c7538f` `20a3ad7` `86b3ebe` `d02fd18` `71e98dd` `f8412d0` `704db44` `b53feeb` `1463617` `281f514` `d1f734c` `414f622` `83bee16` `c345e95` `9b44234` `af66ef3` | 18 | typed graph projection, exporters, `smartchem graph` verb, drawn scheme, coverage audit | `main` only | `git diff --name-only main..af66ef3 \| grep ^smartchem/` -> only `cli.py`, `depiction.py`, `graph_cli.py`, `graph_projection.py`; `graph_projection.py` reads the oracle lazily via `recognize_reaction_type` (line 283), which already exists on `main` (1 definition) |
| **B** soundness + measurement | `eacc086` `246fbd2` `474e018` `d8adf19` `d6c2b3c` `bb11c48` `e5049a2` `151966f` `cbe008f` | 9 | #126 forged-centre retired, #128/#129 family naming + UNATTESTED, #124 cyclic refusal, #131 typed outcomes, #103/#109/#127 corpora and guards | A (graph naming in `246fbd2` rides on A's `graph_projection.py`) | `eacc086`/`e5049a2` touch oracle + `step.py` + `service.py`; `246fbd2` touches `graph_projection.py`; `474e018` touches `routes.py` |
| **C** coverage + version boundary | `a067f4a` `cb79877` `4981a80` `d547e6e` `2f9bd11` | 5 | #132 pericyclic determinism, **#110 18th class**, opt-in lateral reachability, ledger, **1.1.0a1 MINOR declaration** | B (oracle re-derivation discipline) | `cb79877` touches only the oracle; `2f9bd11` touches `__init__.py`, `step.py`, the version-independent golden, 5 CLI-JSON fixtures and 8 test files -- it MUST follow `cb79877` because it is the declaration of that promotion |
| **D** hardening + 19th class | `4f84875` `1473d1d` `415c5d5` `22ea54e` `eb51d88` | 5 | program doc, workbench hardening (forged-centre honesty, three-state completeness, sandboxed SVG), #105 scope pin, **#111 19th class** | C (and B for forged-centre honesty) | `1473d1d` touches `graph_cli.py`+`graph_projection.py`; `22ea54e` touches oracle + `step.py` |
| **E** CI + opt-in profile | `3a37d46` `34e1891` | 2 | OOM-safe PySCF-smoke job; **#114 `bond-order-edit-v1`** | `3a37d46` independent; `34e1891` independent of oracle | `3a37d46` touches only `ci.yml`; `34e1891` touches only `smartchem/algebra_profiles.py` (+19) among `smartchem/` |

Honest limits of this table: the band boundaries are file-overlap evidence on a linear history. They are NOT a
proof that every prefix is independently green. Section 6 states what must be re-run per tip.

## 4. Proposed reviewable split / stacked order

History is linear, so any of these is a set of branch pointers at existing SHAs -- no rewrite, no force-push, no
duplicated fix. All tips below are existing commits.

### Option 1 -- stacked ladder (recommended: smallest review units, zero rewriting)

| PR (new branch name, proposed) | tip SHA | base | contains | issues whose fix this unit carries (close ONLY on this unit's merge to `main`) |
|---|---|---|---|---|
| U1 `pr101/u1-graph-workbench` | `af66ef3` | `main` | band A (18 commits; 12 files, +2816 / -1) | graph PR #101 workbench scope |
| U2 `pr101/u2-soundness-measurement` | `cbe008f` | U1 | band B (9) | #124, #126, #128, #129, #131, #103 (corpus), #109, #127 |
| U3 `pr101/u3-110-version-boundary` | `2f9bd11` | U2 | band C (5) | #132, #110 (and the MINOR-boundary record) |
| U4 `pr101/u4-111-hardening` | `eb51d88` | U3 | band D (5) | #111, #105 (scope DOCUMENTED only -- #105 stays open, deferred to 2.0) |
| U5 `pr101/u5-114-profile-ci` | `34e1891` | U4 | band E (2) | #114 (reachability gain only; recognition gap stays open) |
| U6 `pr101/u6-sandbox-2-0` | `c1b8e36` | U5 | the 7 commits of section 2b | none (no production issue; #105/#130 are deferred *documentation* here) |

Merge order is U1 -> U6. U1..U5 together are exactly `main..34e1891`: the **minimum stable 1.1 candidate**. U6 is
independently droppable.

### Option 2 -- two PRs (coarser, least ceremony)

| PR | tip | base | contains |
|---|---|---|---|
| P-prod `pr101/production-1-1` | `34e1891` | `main` | all 39 production commits (U1..U5) |
| P-sandbox `pr101/sandbox-2-0` | `c1b8e36` | P-prod | the 7 experimental/doc commits |

Choose this if the reviewer prefers one production diff. It still satisfies all constraints in section 0.

### Option 3 -- leave PR #101 intact

Valid only if the owner accepts a 46-commit, 92-file review. The 1.5 gate in `V1_5_RELEASE_PROGRAM.md` section 4
(item 5) already requires the full suite and clean wheel installs "on the FINAL branch SHA -- not an ancestor";
Option 3 makes that trivially the PR head, Options 1-2 require it per merged tip (section 6).

### What a re-target does and does not change

PR #101's own head and history stay as they are. The new branches are additional refs. Whether #101 is later
closed in favor of the split, or converted into the top of the stack, is an owner decision (section 5) -- not
something this plan performs.

## 5. Decisions that belong to the owner (this plan does not make them)

1. Option 1, 2 or 3 above.
2. Whether `ROADMAP.md`'s "non-stacked, one PR off fresh `main`" convention is waived for this program (it is only
   respected by Option 3, or by merging U1 before cutting U2 off the updated `main`, which re-bases U2 and so is NOT
   a pure pointer -- avoid unless authorized).
3. Whether `1.1.0a1` becomes a stable `1.1.0`, and when. No version/tag/release action is in this plan.
4. Whether the dirty working-tree edits in `experiments/sandbox_foundation/` (owned by another lane) land as a
   further commit in U6.

## 6. Verification state and what a split still owes

### 6a. E3 hard-gate check at `c1b8e36` (run 2026-10-20, scoped files only, FOREGROUND, no full suite)

| gate | command | result |
|---|---|---|
| a. 19 recognizers + #110 | `pytest -q -p no:cacheprovider tests/test_transform_algebra_expansion.py tests/test_activated_acyl_transfer_110.py` | **22 passed**, 0 failed, 0 skipped |
| b. #111 false-vouch controls | `pytest ... tests/test_sulfonate_ester_transfer_111.py` | **15 passed**, 0 failed, 0 skipped |
| c. #114 opt-in profile | `pytest ... tests/test_bond_order_edit_profile_114.py` | **32 passed**, 0 failed, 0 skipped |
| d1. fingerprint | `python experiments/v1_0_version_transition.py --check-golden` | exit 0: `version-independent fingerprint: NO DRIFT (semantic content unmoved by the version bump)` |
| d2. version/contract tests | `pytest ... tests/test_v1_0_version_transition.py tests/test_v1_0_public_contract.py` | **11 passed**, 0 failed, 0 skipped |
| e. readiness laws | `pytest ... tests/test_v0_8_readiness_core.py tests/test_v0_9_capability_round_iii.py` | **47 passed**, 0 failed, 0 skipped |

Independent recognizer count: `len(smartchem.experiment.reaction_type_oracle._RECOGNIZERS)` = **19** (read from
the live module; the tuple at `reaction_type_oracle.py` line 995 lists 5 acyl/ether/N-alkyl/acyl-transfer/sulfonate
classes, 8 Diels-Alder variants, 4 sigmatropic ([3,3]) classes, and 2 electrocyclizations).
These are scoped checks, NOT the 1.5 acceptance gate: the OOM-safe full suite (`scripts/run_suite.sh`) and clean
wheel installs on Python 3.10-3.13 were deliberately not run here. Last recorded full-suite figure (project memory,
at `34e1891`): 7655 passed / 0 failed / 50 skipped.

### 6b. What each new tip owes before it is proposed for merge

Each of U1..U5 (and U6) is a NEW tip that has not been tested as a standalone head. Before any is opened for merge
it needs: (i) the full OOM-safe suite on that exact SHA, (ii) CI green on that exact SHA (the project's own rule:
an ancestor's green does not count), (iii) for U3 onward, the version-independent golden check. Known intentional
state per tip: U1..U2 carry `__version__ = "1.0.0"` (the bump lands at `2f9bd11` in U3); the 19-class oracle count
exists only from U4 (`22ea54e`) and 18 at U3 (`cb79877` adds #110); the pre-#110 count of 17 is the figure the
project's own docs record and was NOT re-measured here on a prefix tip. A test or doc asserting "19" is
only valid at U4 and later -- if any pre-U4 tip fails such an assertion, that is the cut point being wrong, not the
code, and the cut moves later (never edit a golden to make a prefix pass).

### 6c. Unverified in this plan

* No intermediate tip (`af66ef3`, `cbe008f`, `2f9bd11`, `eb51d88`) was checked out or tested; band independence is
  file-overlap evidence only.
* CI state of `c1b8e36` (the new `sandbox-foundation` job) was not re-queried here.
* `gh pr view` was used read-only; no PR/branch/ref was created or changed.

---

## 7. Round IV reconciliation (2026-10-22, HEAD `0a761b9`, `main..HEAD` = 62 commits)

The 2026-10-20 analysis above was written at `c1b8e36` (46 commits). Physicalization Rounds III and IV added
16 more commits. The load-bearing finding is **reconciled, not overturned**: the history is STILL a clean
production/experimental split, with ONE explicit exception that is itself cleanly separable.

**What changed since `c1b8e36`:**
- Round III (6 commits) + Round IV (6 commits, this round) are almost entirely `experiments/sandbox_foundation/`
  and `docs/` — the 2.0 physical-mechanism engine. `git diff --name-only 34e1891..HEAD -- smartchem/` now lists
  **exactly one** production file.
- That one file is `smartchem/experiment/reaction_type_oracle.py`, changed by the **single** Round IV production
  commit **`cf3d942`** (1.5 #115, the Claisen-condensation recognizer = 20th class). It touches that one source
  file plus four production test files (`test_claisen_condensation_115.py` new; `test_sulfonate_ester_transfer_111`,
  `test_transform_algebra_expansion`, `test_v0_7_production_algebra` count-gate updates 19->20) and two
  `experiments/poor_man_*_probe.py` frozen-hash re-freezes + `test_poor_man_reaction_type_oracle.py`.

**The reconciled seam:**
- **1.1 production lane** = `main..34e1891` (the original 39-commit stable candidate) **plus the single commit
  `cf3d942`**. `cf3d942` is cleanly cherry-pickable onto the `34e1891` prefix: it is additive (a new recognizer +
  its controls), the version-transition golden is UNMOVED (no corpus case is a Claisen condensation, verified via
  `fingerprint_invariant()`), and it carries an explicit MINOR coverage disposition (count 19->20, no default
  flip). It depends only on the #110/#111 recognizers already in the prefix.
- **experimental 2.0 lane** = everything else after `34e1891` — the entire `experiments/sandbox_foundation/`
  engine (two-cell, mesh, detailed_balance, rate_units, lyapunov, mechanism adapter/types, snapshot, aqueous
  equilibrium, LibGibson frame example) and its docs. Still **zero** production `smartchem/` impact.

**So the options in sections 3-5 are unchanged in shape**; the only update is that the production unit is now
"`main..34e1891` + `cf3d942`" rather than "`main..34e1891`". The experimental unit grew but stayed disjoint from
`smartchem/`. No merge/tag/release/force-push performed; this remains a plan.
