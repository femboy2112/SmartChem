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
| `service` | 23 corpus requests (below): request payload sha + semantic digest + question digest; response outcome, exit code, search-space status, result / wire / thin-wire digests, `response_semantic_fields` sha, admissible set, ranked route digests IN ORDER with fit status, readiness tier and all 11 capability axes + overall, DAG dossiers, frontier sha, IR sha, thick + thin payload sha; load behaviour (plain thick, request pin + question pin + verified admission, plain thin → accepted? round-trip byte-identical?) | 23 |

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
