# SmartChem 0.9.5 — Baseline Behavior Freeze (merged 0.9)

**Status:** FROZEN 2026-09-29 on `main` @ `d26f0eb` (the PR #93 merge; tree `c0198772` == 0.9 docs tip `c75be57`,
code == Round V code tip `d6c7edc`). Package `0.9.0a1`.

**Machine-readable companion:** [`V0_9_5_BASELINE_BEHAVIOR_FREEZE.json`](V0_9_5_BASELINE_BEHAVIOR_FREEZE.json), produced by
[`experiments/v0_9_5_baseline_freeze.py`](../../experiments/v0_9_5_baseline_freeze.py).

This is the reference every 0.9.5 consolidation incision is judged against. **A refactor that cannot prove intended
equality against this freeze is not a refactor** — it is a semantic change and needs its own adjudication (a line in
the 0.9.5 architecture freeze naming the moved key and why).

## How to use it

```
.venv/bin/python experiments/v0_9_5_baseline_freeze.py --check --quick   # fast subset, ~1 min
.venv/bin/python experiments/v0_9_5_baseline_freeze.py --check           # everything, ~15 min (6 isopentyl compiles)
```

`--check` recomputes every fingerprint in a fresh process and prints each drifted key (exit 1 on any drift).
Wall-clock timings are recorded under `timings` and never compared. `--write` re-freezes and is only legitimate on a
tree whose every drift has been adjudicated.

**Determinism receipt:** a fresh-process `--check --quick` against the committed JSON reported
`NO DRIFT (15 service cases, 15 refusals, 15 legacy fixtures, 12 human renders)`.

## What is frozen

| section | content | count |
|---|---|---|
| `schema_ids` | package + request / response / route-summary / DAG-summary / descriptor ids | request v1alpha7, response v1alpha17, route summary v1alpha5, DAG summary v1alpha5, descriptor v1alpha20 |
| `ledgers` | transport ledger (canonical sha + entry count + status counts), capability field-coverage ledger (sha + count + `missing_coverage()`), response schema sha | transport 97 entries (48 RE / 21 REQ / 19 ADVISORY / 9 LEGACY_FROZEN); coverage 73 entries, 0 missing |
| `cli.goldens` | every committed CLI-JSON golden: file sha, exit code, **live regeneration == golden** | 7 / 7 live-equal |
| `cli.human` | human renders (stdout/stderr sha, exit code, line count): recompile, capability recompile, no-route, invalid, decompile, `plan` hydrate (`CuSO4·5H2O`), charged ion (`SO4^2-`), ambiguous formula (`C2H6O`), name, malformed, unknown-flag refusal, Diels–Alder `--json` | 12 |
| `legacy_v08` | every real `tests/fixtures/v08/**` fixture: file sha + load outcome (accepted + outcome/result digest, or exception class + message head) | 15 (+ descriptor doc hashed only) |
| `refusals` | a fixed 15-case tamper matrix on the methyl acetate poor-man canonical payload: unknown schema id, key delete/insert, digest flip, transport relabel, fit relabel (thick + thin), request / capability pin mismatch, signature policy (no key; unsigned-under-required), thin under verified admission, thin plain (advisory — ACCEPTED), dossier deletion, non-dict | 15 (14 refused, 1 accepted by contract) |
| `service` | 22 corpus requests (below): request payload sha + semantic digest + question digest; response outcome, exit code, search-space status, result / wire / thin-wire digests, `response_semantic_fields` sha, admissible set, ranked route digests IN ORDER with fit status, readiness tier and all 11 capability axes + overall, DAG dossiers, frontier sha, IR sha, thick + thin payload sha; load behaviour (plain thick, request pin + question pin + verified admission, plain thin → accepted? round-trip byte-identical?) | 23 |

### The service corpus (the exact requests the 0.9 gates already drive)

| case | outcome | exit | routes / DAGs | search space | capability overall | tiers |
|---|---|---|---|---|---|---|
| methyl_acetate (d2) | ROUTES_FOUND | 0 | 2 / 0 | COMPLETE | — | FORMAL, REACTION_VOUCHED |
| methyl_acetate@poor-man | ROUTES_FOUND | 0 | 2 / 0 | COMPLETE | BLOCKED | FORMAL, REACTION_VOUCHED |
| methyl_acetate@research-lab | ROUTES_FOUND | 0 | 2 / 0 | COMPLETE | UNKNOWN | FORMAL, REACTION_VOUCHED |
| methyl_acetate_dag | INCOMPLETE | 4 | 0 / 4 | PARTIAL | — | — |
| aspirin (d1, T≤350 K) | INCOMPLETE | 4 | 2 / 0 | PARTIAL | — | FORMAL, REACTION_VOUCHED |
| aspirin@poor-man | INCOMPLETE | 4 | 2 / 0 | PARTIAL | BLOCKED | FORMAL, REACTION_VOUCHED |
| paracetamol (d1) | INCOMPLETE | 4 | 2 / 0 | PARTIAL | — | FORMAL, REACTION_VOUCHED |
| paracetamol@research-lab | INCOMPLETE | 4 | 2 / 0 | PARTIAL | UNKNOWN | FORMAL, REACTION_VOUCHED |
| paracetamol_incomplete (cut 1) | INCOMPLETE | 4 | 0 / 0 | INCOMPLETE_NO_ROUTE_OBSERVED | — | — |
| methyl_salicylate (d1) | INCOMPLETE | 4 | 1 / 0 | PARTIAL | — | CONDITIONS_SUPPORTED |
| diels_alder_control | ROUTES_FOUND | 0 | 1 / 0 | COMPLETE | — | REACTION_VOUCHED |
| bromine (name) | INVALID_INPUT | 2 | — | — | — | — |
| bromine_smiles (`BrBr`) | TARGET_ALREADY_AVAILABLE | 0 | — | — | — | — |
| invalid_name | INVALID_INPUT | 2 | — | — | — | — |
| decompile_paracetamol | ROUTES_FOUND | 0 | — | COMPLETE | — | — |
| isopentyl (27 routes) | INCOMPLETE | 4 | 27 / 0 | PARTIAL | — | FORMAL, PROCESS_SPECIFIED |
| isopentyl@research-lab | INCOMPLETE | 4 | 27 / 0 | PARTIAL | UNKNOWN | FORMAL, PROCESS_SPECIFIED |
| isopentyl@poor-man | INCOMPLETE | 4 | 27 / 0 | PARTIAL | BLOCKED | FORMAL, PROCESS_SPECIFIED |
| isopentyl@custom-fit-bench | INCOMPLETE | 4 | 27 / 0 | PARTIAL | BLOCKED, UNKNOWN | FORMAL, PROCESS_SPECIFIED |
| isopentyl_dag_quick | INCOMPLETE | 4 | 0 / 16 | PARTIAL | — | — |
| isopentyl_dag (default process) | INCOMPLETE | 4 | 0 / 0 | PARTIAL | — | — |
| isopentyl_dag@poor-man | REFUSED | 5 | — | — | — | — |

**Zero CAPABILITY_FIT anywhere** (the 0.9 structural theorem, unchanged).

### Load behaviour frozen

Every honest canonical THICK payload loads under (a) a plain load and (b) request pin + capability-question pin +
verified admission, and re-emits **byte-identically**. Every THIN payload loads plainly (advisory) EXCEPT the four
isopentyl responses, refused by contract: *"claims readiness tier PROCESS_SPECIFIED on a THIN_ADVISORY transport —
PROCESS_SPECIFIED is not admissible on an unsigned thin wire"* (the documented D-T1 boundary).

### Notable frozen facts (behaviour, not bugs to fix in a refactor)

* `plan "methyl acetate"` → INVALID_INPUT (exit 2): the name is not in the OFFLINE name table (typed reason, explicit
  `name:/smiles:/formula:` hint). Names stay a closed-world boundary in 0.9.5 (no synonym intelligence).
* `recompile bromine` → INVALID_INPUT; `smiles:BrBr` → TARGET_ALREADY_AVAILABLE (bromine is a commodity terminal).
* A convergent-DAG request under a capability profile is typed-REFUSED (exit 5).
* The legacy v0.8 sulfuric-acid request/response fail closed ("the name resolver changed since v0.8 … recompile").

## Receipts carried (recorded, not recomputed by this harness)

Mutation ACTIVE 217/217 killed / RETIRED 4 (0 void) / DEFERRED 0; full suite 6529 / 6483 passed / 0 failed / 46 skipped
(35 batches); held-out 12 PASS / 1 lawful DIVERGE / 0 FAIL; noninterference HOLDS (isopentyl, 27 candidates); funnel
34/34, 7/7 profile divergence, zero FIT. Each has its own committed harness; the pre-merge smoke on 2026-09-29 re-ran the
held-out probe, noninterference, a live mutant subset (14/14, all retirements valid) and 373 Round-V tests.

## Honest note on the instrument

The first `--write` of this freeze recorded every pinned load as REFUSED — an instrument bug (the harness pinned
`request.digest`, not the `semantic_digest` the loader binds; the tests' own `_pins` helper is the authority). It was
caught by reading the frozen values (a pinned honest load cannot be refused), fixed, and re-frozen; the first isopentyl
DAG case also carried 0 DAGs, so two real DAG cases were added (4 and 16 DAGs). The committed JSON is the corrected one.

## Adjudicated re-freezes (the yardstick moves only here, one line per sanctioned semantic step)

| # | on commit | drifted keys (vs the previous freeze) | adjudication |
|---|---|---|---|
| 0 | `d26f0eb` (merged 0.9) | — | the original freeze (sha256 of the JSON: see git history of this file) |
| 1 | `a890e8a` | EXACTLY 11: `/ledgers/transport_ledger_sha` + 10 `isopentyl@custom-fit-bench` digest keys (`request_capability_question_digest`, `request_payload_sha`, `response/{capability_question_digest, result_digest, routes, semantic_fields_sha, thick_payload_sha, thin_payload_sha, thin_wire_result_digest, wire_result_digest}`) | **S11** (ledger text: `advisory_when` on outcome / standard_status / exit_code / search_space_status; the transport_mode note) and **S7/S9** (that case's profile carries structure-keyed stock under the bumped material-component / stock schema ids). Parent-verified: the verdict projection of all 27 routes (fit status, readiness tier, overall + 11 axes) and outcome / exit / search space / admissible set / DAGs / frontier / IR are IDENTICAL; `routes` moved only in `capability.digest` and `dossier_sha`. Loader wiring (`7c1f62e`) and S3/S4/S5 (`390ba03`) moved NOTHING (full `--check` NO DRIFT on `7c1f62e`; quick on `390ba03` drifted only the S11 ledger sha). |
| 2 | `f91de8e` | 173 keys: the four schema ids (response v1alpha18, route / DAG summary v1alpha6, descriptor v1alpha21), `response_schema_sha` + descriptor id, `field_coverage_sha` (StreamDisposition + StreamSubject rows), every response digest / payload hash / IR / frontier / dossier sha of every service case (the replayed `ProcedureEvidence` gained the digest-covered `stream_dispositions` field, so route and readiness digests move), the 6 CLI golden file hashes, 4 load-refusal messages that embed a moved route digest, and T01's refusal text (the S14 recompile hint) | **S10 + S14** (+ the D-C2 superset: a species feeding a second step is its own waste obligation — reason text only). **Adjudicated with `experiments/v0_9_5_freeze_adjudicate.py`** (the verdict projection; calibrated: re-freeze #1 vs #0 and a document vs itself report NO VERDICT MOVED, one forged route tier is caught): **NO VERDICT MOVED (27 projected groups)** — every outcome, exit code, search-space status, route order + fit / tier / capability overall + 11 axes, DAG fit, admissible-set size, load outcome, refusal class, legacy outcome, human exit code, golden currency and ledger count is identical. |
| 3 | `90393b5` (code = the 0.9.5a1 bump `74414eb` + one comment-only edit) | 147 keys: 133 service digests (the 19 IR-bearing cases × `response/{ir_sha, result_digest, semantic_fields_sha, thick_payload_sha, thin_payload_sha, thin_wire_result_digest, wire_result_digest}`), the 5 CLI goldens' `file_sha` + `live_sha`, `/schema_ids/package` (0.9.0a1 → 0.9.5a1), `/cli/human/plan_diels_alder_json/stdout_sha`, `/ledgers/transport_ledger_sha`, `/refusals/T05_relabel_transport_thin/msg` | **The version bump, plus Wave C8.** The 145 non-C8 keys are the bump alone, PROVEN by a control: the same `--check` on `74414eb` with only `__version__` reverted to `0.9.0a1` drifts in exactly 12 keys — the 5 golden `file_sha` and their 5 `live_equals_golden` (the regenerated goldens on disk) plus the 2 C8 keys — so every service digest, every live golden sha, the package id and the `plan --json` render move with `tool_version` and nothing else. The 3 cases without an IR (`bromine`, `invalid_name`: INVALID_INPUT; `isopentyl_dag@poor-man`: REFUSED) carry no tool version and did not drift. The two C8 keys (carried as known drift since the C8 integration): the transport ledger's text gained the C8 rows, and T05 (a canonical payload relabelled thin) is now refused by the earlier thin-carries-no-replay law ("a THIN_ADVISORY payload carries a replay_payload …") instead of the digest mismatch — still refused. Barriers A11, A13–A17 move no frozen value. Adjudicator: NO VERDICT MOVED (27 projected groups). |

Erratum: this document first said "23 corpus requests"; the corpus has 22 service cases.
