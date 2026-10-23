# V1.1 Coverage Expansion — the 1.0.0 → 1.1.0a1 semantic transition (#110)

**Status:** sanctioned MINOR coverage expansion. Forensic, field-by-field. This is the 1.0.0 → 1.1.0a1
analogue of the 0.9.5a1 → 1.0.0rc1 record in [`V1_0_RELEASE_GATE.md`](V1_0_RELEASE_GATE.md), and it is the
human sign-off that authorises the re-freeze of the version-independent fingerprint golden
(`V1_0_VERSION_INDEPENDENT_FINGERPRINT.json`).

## Baselines

| ref | SHA | role |
|---|---|---|
| published release | `v1.0.0` = `8345bbb` | the differential's `pre` |
| `origin/main` | `99fce34` | merge-base of the branch; 5 commits past `v1.0.0`, **all docs/launch — `git diff v1.0.0 -- smartchem/` is empty**, so `main` ≡ `v1.0.0` semantically |
| branch | `feat/chemical-graph-projections` @ `d547e6e` (+ this P0 fix) | the differential's `post` |

## The change in one sentence

A single new recognizer — **#110 activated acyl transfer** (`anhydride/acyl-halide + R-OH/R-NH/R-SH ->
ester/amide/thioester + acid/HX`), the oracle's 18th class — recognizes the step `paracetamol <-
4-aminophenol + acetic anhydride`, which was previously *honest non-recognition*, promoting that one route's
readiness `FORMAL_CANDIDATE -> PROCESS_SPECIFIED` **under an unchanged search identity**.

Per [`COMPATIBILITY.md`](../../COMPATIBILITY.md) §1 + §7 a new RULE that widens coverage is a **MINOR**. The
bug this P0 repairs is that the branch shipped the new rule while `__version__` still read `1.0.0`, so the
durable version-transition gate (`tests/test_v1_0_version_transition.py`) correctly fired against an
undeclared semantic move.

## The forensic differential

Reproduce (the editable install registers a `MapImporter` meta-path finder that shadows a worktree — defeat
it with `-S` + an explicit site-packages `PYTHONPATH`, and run from inside the worktree so it is `sys.path[0]`):

```sh
SITE=.venv/lib/python3.12/site-packages
git worktree add --detach /tmp/wt-v1.0.0 v1.0.0
( cd /tmp/wt-v1.0.0 && PYTHONPATH="$SITE" python -S experiments/v1_0_version_transition.py --capture /tmp/pre.json )
python experiments/v1_0_version_transition.py --capture /tmp/post.json
python experiments/v1_0_version_transition.py --diff /tmp/pre.json /tmp/post.json
```

Result over the fast corpus (15 cases): **EXPECTED moves 29** (every `tool_version`, `result_digest`,
`package_version`, `cli_version_banner`, `implementation_digest` — the declared version-bound set) and
**UNEXPECTED moves 30, ALL confined to `paracetamol` and `paracetamol@research-lab`.** Non-paracetamol
non-version-bound drift: **0**. Every one of the 30 is one of:

* `readiness.per_step[0].reaction_type: UNSATISFIED -> SATISFIED` and `reaction_class_name: None ->
  'activated acyl transfer (...)'` — the recognizer firing;
* both `open_obligations` / `route_open_obligations` `'reaction_type: not recognized ...' -> None` — the
  single G6 demotion blocker clearing;
* `readiness_tier: FORMAL_CANDIDATE -> PROCESS_SPECIFIED` (and the @research-lab capability_assessment field
  that mirrors it, plus its dossier digest);
* the `affordability_frontier` gaining a second row — the un-demoted route surfacing at `[0]`, the prior
  sole entry dropping to `[1]` (the `None -> value` leaves are a *new row*, not a changed meaning; same
  `affordability-frontier-entry-v1alpha3` schema on both).

## Why this is a coverage expansion and not a backward-compatibility violation — three proofs

1. **The route is identical; only recognition moved.** The Ac₂O route carries the *same route_digest*
   `fe7e7768d3a830fb45a892597ad4b2ee324cf7006a3592b1ff022b38697b57a3` at v1.0.0 (dossier #0,
   `FORMAL_CANDIDATE`) and at HEAD (dossier #0, `PROCESS_SPECIFIED`). Same digest ⟹ identical steps. #110
   minted no route — `fe7e7768` already existed at v1.0.0, G6-dominated and off the frontier. The oracle is
   a readiness-layer **demoter**, not a search provider (`route_reaction_type_blockers`).
2. **The search identity is byte-invariant.** The exhaustive flattened-leaf diff moved **zero** request-side
   fields (including `semantic_digest`) for every case. A consumer that pins the paracetamol request keeps
   getting answers to the identical search (COMPATIBILITY §7). The readiness promotion rides entirely in the
   ranking/readiness layer *under the unchanged digest* — which is exactly why it needs an explicit MINOR
   declaration (the §7 "digest moves" insulation does not apply to a readiness-layer demoter).
3. **The procedure source was not fabricated.** The sourced procedure `10.1021/acs.jchemed.0c01512`
   (J. Chem. Educ.) lives in the **identical file set** at v1.0.0 and HEAD. The Ac₂O route was held at
   `FORMAL_CANDIDATE` *solely* by the unrecognized reaction type; conditions, process, workup and the sourced
   procedure were already satisfiable at v1.0.0. Clearing the single weakest link let the cumulative
   weakest-link ladder climb to the top rung — which also proves no fail-closed obligation was relaxed.

No verdict word was reinterpreted; the readiness vocabulary and the search identity are unchanged. The move
is strictly in the **promotion** direction (weaker → stronger, driven by new positive, certifying
recognition), which is what §7 blesses for a MINOR.

## Resolution (what this P0 changed)

* `smartchem/__init__.py`: `__version__` `1.0.0 -> 1.1.0a1` (declares the MINOR boundary; `pyproject.toml`
  reads it dynamically, so no second edit).
* Re-froze `V1_0_VERSION_INDEPENDENT_FINGERPRINT.json` at the 1.1.0a1 boundary (the golden is a living
  regression anchor that tracks the current 1.x baseline; the 1.0.0 content stays recoverable at the
  `v1.0.0` tag). Only the two paracetamol `invariant_sha` leaves moved.
* Recognizer-count pins `17 -> 18` (`test_v0_7_production_algebra`, `test_transform_algebra_expansion`) and
  the stale `17`/`seventeen` docstrings in `smartchem/experiment/step.py`,
  `tests/test_issue_126_forged_center.py`.
* Re-pinned the paracetamol *fixtures* without loosening any *law*: the non-monotonicity exemplar became
  `test_paracetamol_anhydride_step_graduates_to_process_specified_under_110` (the win, as a de-promotion
  anchor), and the weakest-link-cap law is preserved by
  `test_reaction_type_gate_caps_the_ladder_even_with_a_complete_procedure` (monkeypatches recognition to
  `None` on the richest `PROCESS_SPECIFIED` fixture and proves the tier collapses to `FORMAL_CANDIDATE`).
  Dropped paracetamol from the below-top control sets in `test_v0_8_readiness_core` and
  `test_v0_9_capability_round_iii` (aspirin + methyl salicylate still witness the law).

## Claim ledger

| claim | label |
|---|---|
| Only `paracetamol`/`paracetamol@research-lab` moved semantically, 0 other drift | `Verified[forensic --diff over fast corpus, v1.0.0 vs HEAD]` |
| Ac₂O route steps identical across versions (same `route_digest fe7e7768`) | `Verified[capture digest equality]` |
| `semantic_digest` / entire request payload byte-invariant | `Verified[exhaustive flattened-leaf diff]` |
| JCE procedure source present at v1.0.0 (not fabricated) | `Verified[git grep v1.0.0 vs HEAD, identical file set]` |
| The promotion is a lab-real route (paracetamol litmus) | `Observed[route is 4-aminophenol + Ac₂O -> paracetamol + AcOH, the real industrial acetylation]` |
| #110 does not false-vouch a neighbouring family | `Observed[existing #110 cross-poach + forged-centre suites pass]` — adversarial re-audit is Wave B |
