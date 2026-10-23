# V1.1 Coverage Expansion — the 1.0.0 → 1.1 semantic transition (#111, #115)

**Status:** sanctioned MINOR coverage expansion. Forensic, field-by-field. This is the companion to
[`V1_1_COVERAGE_EXPANSION_110.md`](V1_1_COVERAGE_EXPANSION_110.md): it supplies the **independent before/after
case** for the two recognizers that #110's corpus-based differential could not exercise, because no golden-corpus
target routes through a sulfonate-ester transfer or a Claisen condensation. Per the 1.1 release-candidate review
([`V1_1_PRODUCTION_CANDIDATE_REVIEW_0dde33a.md`](V1_1_PRODUCTION_CANDIDATE_REVIEW_0dde33a.md) §3), #111/#115
previously had no equivalent committed differential; this record is it.

## Baselines

| ref | SHA | role |
|---|---|---|
| published release | `v1.0.0` = `8345bbb` | the differential's `pre` (17 recognizers) |
| release branch | `release/1.1.0` (on the `0dde33a` production prefix) | the differential's `post` (20 recognizers) |

`post` was captured at `__version__ = 1.1.0a1` (the production prefix's declared pre-release). Promoting the string
to the final `1.1.0` moves **only** the version-bound digest set and is proven separately by
`experiments/v1_0_version_transition.py` / `tests/test_v1_0_version_transition.py` — it does not touch any finding
below.

## The change in one sentence

Two new recognizers — **#111 alkyl sulfonate-ester transfer** (`sulfonyl halide + R-OH -> sulfonate ester + HX`,
the oracle's 19th class) and **#115 Claisen condensation** (`ester/ketone + ester/carbonate -> 1,3-dicarbonyl +
alcohol`, the 20th; **not** the Claisen [3,3] sigmatropic rearrangement, which remains a distinct recognizer) —
recognize steps that were *honest non-recognition* at v1.0.0, each promoting recognition/readiness **under a
byte-invariant search identity**, because the reaction-type oracle is a readiness-layer DEMOTER
(`route_reaction_type_blockers`), never a route-generation provider.

Per [`COMPATIBILITY.md`](../../COMPATIBILITY.md) §1 + §7 a new rule that widens coverage is a **MINOR**.

## The forensic differential

### Part A — global search-identity invariance (the whole fast corpus)

Reproduce (the editable install registers a meta-path finder that shadows a worktree — defeat it with `-S` + the
worktree and site-packages on `PYTHONPATH`, run from inside the worktree; verify `smartchem.__file__` points into
the worktree before trusting any capture):

```sh
SP=.venv/lib/python3.12/site-packages
git worktree add --detach /tmp/wt-v1.0.0 v1.0.0
( cd /tmp/wt-v1.0.0 && PYTHONPATH="/tmp/wt-v1.0.0:$PWD/$SP" .venv/bin/python -S experiments/v1_0_version_transition.py --capture /tmp/pre.json )
# ... and the same --capture from the release worktree -> /tmp/post.json
.venv/bin/python -S experiments/v1_0_version_transition.py --diff /tmp/pre.json /tmp/post.json
```

Result over the fast corpus (15 cases): the **expected** version-bound set moved on every case (`tool_version`,
`result_digest`), and the harness reported **30 "unexpected" moves — every one confined to `paracetamol` and
`paracetamol@research-lab`**, i.e. the #110 activated-acyl promotion already recorded in
`V1_1_COVERAGE_EXPANSION_110.md` (that harness's expected-set is version-bound-only by design, so a sanctioned
chemistry promotion registers as "unexpected" and is blessed by the coverage record, not the harness).

The decisive facts for #111/#115:

* **Zero unexpected moves outside paracetamol.** #111 and #115 added **no** corpus-visible drift — no corpus
  target routes through either family.
* **`semantic_digest` byte-invariant on all 15 cases** (explicit check: `request_payload.semantic_digest` and
  `request_payload.digest` — **0 mismatches / 15**). A consumer that pins any of these requests keeps getting
  answers to the identical search.
* **No schema-id reinterpretation.** The only `schema_version` leaf in the diff is a *new* affordability-frontier
  row appearing at the same `smartchem.experiment/affordability-frontier-entry-v1alpha3` id (a #110 effect, a new
  row — not a changed id).

### Part B — the family-specific recognition pivot (the independent before/after)

The two families are exercised on the vetted positive exemplars lifted verbatim from their regression files
(`tests/test_sulfonate_ester_transfer_111.py`, `tests/test_claisen_condensation_115.py`), constructed the
checkout-agnostic way (`ExperimentStep.assembling`, present at v1.0.0) and classified by
`recognize_reaction_type`. Reproduce: `experiments/v1_1_coverage_expansion_111_115_probe.py` under each checkout.

| exemplar step | `recognize_reaction_type` @ v1.0.0 | @ release |
|---|---|---|
| #111  MeOH + TsCl → methyl tosylate + HCl  (`CO`,`Cc1ccc(cc1)S(=O)(=O)Cl` → `Cc1ccc(cc1)S(=O)(=O)OC`,`Cl`) | `None` | `sulfonate-ester transfer (sulfonyl halide + R-OH -> sulfonate ester + HX)` |
| #115  2 EtOAc → ethyl acetoacetate + EtOH  (`CC(=O)OCC`,`CC(=O)OCC` → `CC(=O)CC(=O)OCC`,`CCO`) | `None` | `Claisen condensation (ester/ketone + ester/carbonate -> 1,3-dicarbonyl + alcohol)` |
| `len(_RECOGNIZERS)` | 17 | 20 |

Both families were `None` (honest non-recognition) at v1.0.0 and recognize at release. On a route carrying such a
step this clears the single G6 demotion blocker `reaction_type: not recognized by the production oracle` and lets
the weakest-link readiness ladder climb — the identical mechanism `V1_1_COVERAGE_EXPANSION_110.md` proved
field-by-field for paracetamol.

## Why this is a coverage expansion and not a backward-compatibility violation — three proofs

1. **Byte-invariant search identity.** The oracle is a readiness-layer demoter (`route_reaction_type_blockers`),
   not a rule/guard/provider in the route algebra, so adding recognizers does not move the algebra's semantic
   descriptor. Proven: `semantic_digest` unchanged on all 15 corpus cases (COMPATIBILITY §7 — the §7 "digest
   moves" insulation does not apply to a readiness-layer demoter, which is exactly why the promotion needs an
   explicit MINOR declaration).
2. **Strictly the promotion direction.** Both families were honest non-recognition at v1.0.0 (Part B, `None`), so
   recognition is new *positive, certifying* recognition — weaker → stronger — which §7 blesses for a MINOR. No
   verdict word is reinterpreted; the readiness vocabulary and the search identity are unchanged.
3. **No existing consumer's answer changed.** The corpus diff shows zero non-paracetamol moves, so no search in
   the golden corpus routes through #111/#115; the move is exhibited only on the independent hand-step cases.

## Scope and no-false-vouch (unchanged from the branch audit)

* **#111** covers **alkyl**-O sulfonylation only; aryl-O is deferred (a `_MUST_NOT_VOUCH` control,
  `phenol_aryl_O_coverage_loss`). The cardinal no-false-vouch is pinned by
  `tests/test_sulfonate_ester_transfer_111.py` (4 recognized positives, `false_vouch_as_sulfonate == 0`,
  cross-poach + forged-centre + 7 mixed-anhydride/masked-carbonyl kills).
* **#115** is **type-validity only**; the stoichiometric enolate base is Problem B / #107. The no-false-vouch is
  pinned by `tests/test_claisen_condensation_115.py` (10 positives, 11 named fictions, each a mutation control of
  one guard). The Claisen *condensation* is kept distinct from the Claisen [3,3] *rearrangement* by both.

## Claim ledger

| claim | label |
|---|---|
| `semantic_digest` / request digest byte-invariant across the corpus, v1.0.0 vs release | `Verified[explicit per-case check, 0/15 mismatches]` |
| Only paracetamol moved semantically in the corpus (the #110 effect); 0 #111/#115 corpus drift | `Verified[version_transition --diff, v1.0.0 vs release]` |
| #111 & #115 move `None` → their class on the vetted exemplars (17 → 20 recognizers) | `Verified[recognize_reaction_type under each checkout]` |
| No schema id reinterpreted (the lone `schema_version` leaf is a new row at the same id) | `Verified[field-level diff]` |
| #111/#115 vouch no neighbouring family | `Observed[committed no-false-vouch corpora in the two regression files]` |
| The recognition is exhibited on hand-constructed conserving steps, not a full bounded search | `Observed[the corpus has no #111/#115 target; the recognizer is exercised as its own regression files do]` |
