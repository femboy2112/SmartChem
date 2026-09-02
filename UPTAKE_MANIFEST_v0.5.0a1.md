# SmartChem chemical compiler uptake manifest — v0.5.0a1

**Manifest date:** 2026-09-01  
**Target:** `0.5.0a1`  
**Audit base:** `main` at `b5faf7da460377e37f3a6ab70cdcbe542d88b666`  
**Work branch:** `codex/chemical-compiler-standard-2026-09-01`  
**Normative contract:** `CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md`  
**Evidence and rationale:** `AUDIT_CHEMICAL_COMPILER_2026-09-01.md`

## 1. How to use this manifest

This is an uptake contract, not a wish list. An item is complete only when its code, adversarial
test, public rendering, and truth label agree. Passing the pre-existing suite is necessary but
does not close a new semantic gate.

Status vocabulary:

| Status | Meaning |
|---|---|
| `IMPLEMENTED_AND_VERIFIED` | Code and named acceptance test pass on the branch. |
| `PATCHED_NEEDS_GREEN` | Code and usually a test edit exist, but a post-change verification result was not recorded when this manifest was written. |
| `IN_PROGRESS` | Partial implementation exists; a known residual defect prevents closure. |
| `TODO` | No conforming implementation is known on the branch. |
| `DECISION` | A public semantic choice must be fixed before implementation. |
| `DEFERRED` | Explicitly outside the alpha only if the release boundary remains honest without it. |
| `BLOCKED` | A dependency or contradiction prevents responsible uptake. |

Priority vocabulary:

- `P0`: blocks the `0.5.0a1` public chemical-compiler contract;
- `P1`: required before broader material/procedure claims, but may remain an explicit alpha
  limitation where named;
- `P2`: strengthening or coverage work after the honesty gates.

No item below should be marked complete solely by editing this file. Replace the status and add
the exact test/commit evidence in the same change that closes it.

**Reconciled verification:** the targeted chemistry/CLI/safety suite completed with **405 passed
in 144.24 seconds**. The final post-change full suite completed with **2510 passed, 51 skipped,
1 expected failure in 205.04 seconds**.
`IMPLEMENTED_AND_VERIFIED` applies only to the exact scoped row; a broader
cross-path requirement remains `IN_PROGRESS` when formula, DAG, JSON, material, or shared-service
coverage is absent.

**Continuation (branch `chem-compiler-mainline-2026-08-31`, off `codex/chemical-compiler-standard-2026-09-01`
at `bb4b238`):** the truth-envelope work continues on a new non-main branch. Its own baseline on this
environment measured **2551 passed, 14 skipped, 1 expected failure** — the higher pass / lower skip counts
vs the 2510/51 above reflect PySCF and slow paths being *available* here rather than skipped, not a
regression; the collected total (2566) reconciles across both environments. Continuation increments so far:
`4a958b8` (DAG search receipt, +11 tests) -> 2562 passed; `454d2a0` (formula receipt + the shared
`smartchem.search.SearchStatus`, +15 tests) -> 2577 passed; `a34cc69` (two render-honesty fixes -- empty box
!= FITS, ideal K != practical yield; +5 tests) -> 2582 passed; `09b3072` (ChemicalCompilationIR first brick, the
shared artifact emitted by the formula decompiler; +13 tests) -> 2595 passed; `7d27e3c` (StockMaterial first
brick -- a chemical identity is not a material; +14 tests) -> **2609 passed, 14 skipped, 1 expected failure**.
See the uptake records after §3.1, §3.2, §3.5 and §4.

## 2. Audit-branch patches already present

These are the scoped uptake items credited to the working branch at the reconciled snapshot.
They passed focused regressions and the final full suite; none implies release completion.

| ID | Priority | Branch change | Snapshot status | Verification / residual boundary |
|---|:---:|---|---|---|
| `EVD-DIR-01` | P0 | Direction-tagged condition records and exact structure-keyed assembly lookup after primitive formula indexing | `IMPLEMENTED_AND_VERIFIED` | Same-formula isomer and reverse-hydrolysis regressions pass; broader evidence-key fields remain in `EVD-KEY-01`. |
| `UNIT-ENV-01` | P0 | `ConditionEnvelope` refuses temperature units other than K and pressure units other than atm | `IMPLEMENTED_AND_VERIFIED` | Construction/unit regressions pass; conversion UX remains future service work. |
| `SAFE-HEAT-01` | P0 | Strong heat requests controlled electric heater/furnace; no automatic Bunsen recommendation | `IMPLEMENTED_AND_VERIFIED` | Targeted equipment/render regressions pass. |
| `SAFE-FLAM-01` | P0 | Positive flammability data veto open flame independently of medium spelling | `IMPLEMENTED_AND_VERIFIED` | Alias-independent hazard regression passes. |
| `SAFE-HOOD-01` | P1 | Benign hazard records such as water no longer trigger fume-hood containment merely by existing | `IMPLEMENTED_AND_VERIFIED` | Benign-water and positive-hazard regressions pass. |
| `TERM-COM-01` | P0 | Target commodity short-circuit is limited to the active commodity inventory | `IMPLEMENTED_AND_VERIFIED` | `commodities=()` regression passes; shared policy remains `TERM-POL-01`. |
| `MAT-CAVEAT-01` | P0 | Human commodity render states identity-only match and disclaims purity/concentration/phase/grade/impurity equivalence | `IMPLEMENTED_AND_VERIFIED` | Human render regression passes; JSON equivalent remains `CLI-JSON-01`. |
| `SHOP-LEAF-01` | P0 | Linear shopping list excludes a reactant made by an internal route step | `IMPLEMENTED_AND_VERIFIED` | Two-step regression passes; DAG quantity/fan-out remains `SHOP-LEAF-02`. |
| `EVD-GRADE-01` | P0 | Free-text conditions remain declared constraints; accounting/equipment do not relabel them sourced | `IMPLEMENTED_AND_VERIFIED` | “because I said so” and structural-toy regressions stay below `KNOWN_SOURCED`; equipment render carries its bucket. |
| `EVD-SEL-01` | P0 | Selectivity promotion requires an accepted typed `SourceCitation`; weak statuses, malformed locators and unreviewed citations cannot promote | `IMPLEMENTED_AND_VERIFIED` | Free-text, locator-shell, unreviewed, `UNSUPPORTED`, and `STRUCTURAL_TOY` regressions pass. |
| `SRCH-LIN-01` | P0 | Linear `search_routes` returns a receipt and partial/complete human no-route rendering | `IMPLEMENTED_AND_VERIFIED` | Cut-budget and result-limit regressions pass; formula/DAG/shared JSON remain `SRCH-RCT-01`. |
| `STO-SCALE-01` | P0 | Primitive coefficients drive feasibility/equilibrium/kinetics and scale-normalized selectivity | `IMPLEMENTED_AND_VERIFIED` | Named scaling regressions pass; global identity remains `STO-PRIM-01`. |
| `ROUTE-NET-01` | P0 | Linear continuity requires positive net consumption | `IMPLEMENTED_AND_VERIFIED` | Equal-spectator regression passes. |
| `TERM-FORM-01` | P0 | Formula inventory entries terminate and are canonicalized/deduplicated | `IMPLEMENTED_AND_VERIFIED` | Target-terminal and inventory permutation/duplication regressions pass. |
| `TERM-ACTIVE-01` | P0 | Exact target in active structural terminal stock returns a zero-expansion inventory result | `IMPLEMENTED_AND_VERIFIED` | Receipt records zero expansions; render disclaims quantity/assay/fitness. |
| `FORM-VAL-01` | P0 | Formula parsing uses the complete periodic table and positive integer counts/bounds | `IMPLEMENTED_AND_VERIFIED` | Representative element and invalid-count regressions pass. |
| `SCISS-ID-01` | P0 | Rooted open-valence scission identity; neutral-only refusal; duplicate reagent-type deduplication | `IMPLEMENTED_AND_VERIFIED` | Root/charge/duplicate-reagent regressions pass; broad identity layers remain TODO. |
| `FEED-CLI-01` | P0 | Identity-only CLI inventory no longer invents a one-mole feed/ceiling | `IMPLEMENTED_AND_VERIFIED` | Poor-man route dossier renders without ceiling or crash. |
| `READY-DOSS-01` | P0 | Renderer emits `FORMAL_CANDIDATE` evidence dossier and missing-operation checklist | `IMPLEMENTED_AND_VERIFIED` | Golden readiness/render regressions pass; `ProcedureIR` remains TODO. |
| `SAFE-AUTH-BR-01` | P0 | `PROCEED_UNATTENDED` is not emitted; compatibility enum remains | `IMPLEMENTED_AND_VERIFIED` | Handling/render regressions pass. |
| `CONSTR-BR-01` | P0 | Constraints require finite, positive, ordered values | `IMPLEMENTED_AND_VERIFIED` | Invalid/nonfinite/inverted bound regressions pass. |
| `CLI-BR-01` | P0 | Registered names, entry point/version, strict bounds/diagnostics, and codes 0/2/3/4/5 on named synthesis outcomes | `IMPLEMENTED_AND_VERIFIED` | Subprocess probes cover complete route, invalid input, complete no-route, partial search and model refusal; shared service, code 70, input breadth and JSON remain. |

## 3. P0 truth-envelope backlog

### 3.1 Search completeness and result semantics

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `SRCH-RCT-01` | Every formula, route, and DAG search returns a `SearchReceipt` | All three searches now return a first-class receipt over the shared `smartchem.search.SearchStatus` vocabulary: `search_routes`->`RouteSearchReceipt`, `search_dags`->`DAGSearchReceipt`, `search_decomposition`->`FormulaSearchReceipt` (`454d2a0`); the `build_*`/`enumerate_*` calls stay graph/tuple wrappers. Folding the three receipts into one response object is separate (`CLI-JSON-01`) | Unify the three receipts under one response schema | Low cut budget reports partial for all three search kinds | None | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-RCT-02` | Preserve `capped_scissions.complete` across recursion | Linear and DAG searches both aggregate `capped_scissions.complete` across recursion into their receipts (`4a958b8`); the formula descent keeps its own loud `REFUSED_BUDGET` | Carry the same aggregation into any future shared search | Acetic-anhydride budget fixture is partial in linear and DAG paths; high budget complete within bounds | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-CAP-01` | Route/DAG result-cap saturation is visible | Linear and DAG result-cap saturation are both receipt-visible and tested (`4a958b8`); DAG saturation is conservative — a cap equal to the true distinct count flags `PARTIAL_RESULT_LIMIT`, never a false complete | Add shared JSON exposure of the saturation flag | Low linear and DAG result caps are partial; caps above fixture count are complete | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-NO-01` | No-route wording distinguishes complete from incomplete | Linear human output distinguishes partial absence, and DAG `search_dags` distinguishes complete-empty from incomplete-empty at the receipt level (`4a958b8`); the formula receipt reports partial-vs-complete too (though a formula graph always has edges, so it has no empty-candidate no-route case). No human/JSON renderer surfaces the four-outcome matrix uniformly yet | Implement the four-outcome matrix in the shared response and all renderers | Empty incomplete -> `INCOMPLETE_NO_ROUTE_OBSERVED`; empty complete -> `NO_ROUTE_IN_DECLARED_SPACE` everywhere | `SRCH-RCT-01` | `IN_PROGRESS` |
| `SRCH-BUD-01` | Budget scope is accurately named | All three receipts name their budget scope: linear/DAG say cut budget per expansion; the formula receipt names its per-node search-node budget and whole-graph edge cap distinctly (`PARTIAL_SEARCH_BUDGET` vs `PARTIAL_RESULT_LIMIT`, `454d2a0`) | Keep the named scopes when the receipts fold into a shared response | Every receipt says `PER_NODE`/per-expansion or enforces one global counter | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-DEPTH-01` | A depth-limited search is never laundered into a complete one | A route/DAG search that cut an expandable branch at the `max_depth` bound reported `COMPLETE_WITHIN_BOUNDS` with no diagnostic; a depth-1 "complete" hid routes that provably exist at depth 2+. Fixed (`ba69169`): `SearchStatus.PARTIAL_DEPTH_LIMIT` (this codebase's name for the standard's `INCOMPLETE_DEPTH_LIMIT`, section 8.2) plus a `depth_truncated_branches` counter on both receipts, folded into `status`/`complete_within_bounds`. A >=2-missing linear branch stays a grammar boundary (not depth); a node with no cleavages stays genuinely complete | Carry the depth-limit signal into the future shared response/JSON and the four-outcome renderer | Lowering `max_depth` below a fixture's true route depth reports `PARTIAL_DEPTH_LIMIT`, never a complete/no-route | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-RCT-8.1` | The search receipt carries the full section 8.1 engine counters | `RouteSearchReceipt` now records the section 8.1 telemetry (`2e4fbea`, schema -> v1alpha2): `nodes_visited`, `transforms_considered`, `candidates_emitted`, `candidates_rejected_by_reason{}` (sorted (reason,count): `duplicate`/`result_limit`), `search_kind`/`cut_budget_scope`, and derived `cut_enumeration_complete`/`candidate_enumeration_complete`. `search_routes` instruments them; every counter is a real measurement or explicit UNKNOWN (None), never a silent zero (section 8.1 "null, not zero"). The invariant `candidates_emitted == results_returned + sum(rejected)` is enforced and caught a real double-counting bug in the same change. **All three receipts now carry the counters** (`dc9bd21`) **and the three section 8.1 identity digests** (`453331a`: target/terminal/transform-registry, schemas v1alpha3; the transform-registry layering wrinkle resolved by a shared leaf `smartchem/transform_registry.py` so receipts and the IR stamp the SAME registry digest). **Section 8.2 status-vocabulary reconciliation now BUILT** (`5c5b619`, sub-brick 4): all three receipts gain a `standard_status` that speaks the section 8.2 vocabulary via `SearchStatus.standard_name` + `primary_standard_status` (additive, no rename); the non-1:1 residue is pinned by tests, and a 3-bearing adversarial red-team confirmed the mapping faithful (no laundering, no None leak, precedence section-8.2-legitimate) and caught 3 comment-faithfulness defects, all fixed | `IR-8.2-01` (the IR still renders the native status word; give it a section 8.2 face) and the section 8.1 receipt-on-refusal path -- **now BUILT for the two REFUSED_\* statuses** (`SRCH-REFUSE-8.1`): `decompiler.decompile_or_refuse` returns a `RefusalReceipt` carrying the section 8.2 refusal status instead of raising; ERROR_INTERNAL (a top-level guarded service) and the full null-counter SearchReceipt-on-refusal schema remain | All three engines report honest counters (emitted==results+rejected; transforms>=edges), name their target/terminal/transform-registry, AND speak the section 8.2 terminal-status vocabulary; the receipt and IR registry digests agree cross-layer | `SRCH-RCT-01` (done) | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-DIG-01` | Equivalent inventory order has equal request/result digest | Formula inventory is now canonicalized/deduplicated and permutation-tested; shared request identity does not exist | Extend canonical set/multiset inputs to structural/material request IR | Formula permutations match now; future request/result digests also match | Shared request IR | `IN_PROGRESS` |

**Uptake record — DAG search receipt** (closes `SRCH-RCT-02`, `SRCH-CAP-01` for the DAG path; advances
`SRCH-RCT-01`, `SRCH-NO-01`, `SRCH-BUD-01`):

```text
ID:                  SRCH-RCT-02, SRCH-CAP-01 (DAG path)
commit:              4a958b8064c4b54017d816836e226c1dd7e93054
files:               smartchem/experiment/routes.py, smartchem/experiment/__init__.py, tests/test_routes.py
tests:               tests/test_routes.py::TestConvergentDAGReceipt (11 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2562 passed, 14 skipped, 1 xfailed (baseline 2551/14/1; +11 = the new tests).
                     ruff check clean; git diff --check clean; py_compile clean.
falsifier fixture:   search_dags(PARA, reagents=(WATER,), max_depth=1, cut_budget=1) -> dags=(),
                     status PARTIAL_CUT_BUDGET, incomplete_expansions>0 (a budget-exhausted empty is never a
                     certified no-route); the SAME query at full budget -> status COMPLETE_WITHIN_BOUNDS, so
                     only the receipt tells the two empties apart. search_dags(ETAC, DAG_REAGENTS, max_depth=2,
                     max_dags=5) -> PARTIAL_RESULT_LIMIT; max_dags=5000 -> COMPLETE_WITHIN_BOUNDS (47 DAGs).
                     SUPERSEDED by SRCH-DEPTH-01 (ba69169): the "full budget -> COMPLETE" and the "max_dags=5000
                     -> COMPLETE" claims held only while depth truncation was unreported. Both fixtures are in
                     fact depth-limited, so they now honestly report PARTIAL_DEPTH_LIMIT / PARTIAL_MULTIPLE_LIMITS;
                     the cut-budget vs depth flags still tell the two empties apart. See the SRCH-DEPTH-01 block.
human-output check:  none new -- no production human/JSON path consumes the DAG search yet (only search_routes
                     reaches the CLI). The receipt makes the truth available to the future shared renderer.
JSON/schema check:   n/a -- shared JSON response is CLI-JSON-01 (TODO). DAGSearchReceipt/DAGSearchResult are
                     frozen Digestible values with pinned schema strings
                     (smartchem.experiment/dag-search-receipt-v1alpha1, .../dag-search-result-v1alpha1).
residual limitations:
  1. Formula DecompositionGraph still uses status/refusal_reason, not the unified receipt (SRCH-RCT-01 open).
  2. DAG result-limit saturation is CONSERVATIVE: the level-wise max_dags cap means a cap equal to the true
     distinct count flags PARTIAL_RESULT_LIMIT while still returning the whole set -- it errs toward "there may
     be more", never toward a false COMPLETE. Pinned by test_result_cap_saturation_is_conservative_at_the_exact_count.
  3. No shared response/JSON unifies the three search kinds (SRCH-NO-01 renderer, CLI-JSON-01 both open).
  4. SEMANTIC CHANGE: enumerate_dags now terminates a target already in available/reagents/commodities before
     expansion, returning () (standard section 7; matches search_routes). No prior test exercised this; it is
     covered by test_target_in_exact_terminal_stock_stops_before_expansion.
```

**Next verdict-changing probes (immediate):** (a) give the formula `DecompositionGraph` the same receipt shape
so `SRCH-RCT-01` can close (`build_decomposition` already tracks complete/`REFUSED_BUDGET`; it needs the unified
receipt object + a partial-vs-complete-empty distinction). (b) A shared response object + `--json` that renders
the four-outcome no-route matrix for all three search kinds (`SRCH-NO-01`, `CLI-JSON-01`). (c) Then the shared
`ChemicalCompilationIR` (`IR-CHEM-01`) that lets the recompiler consume a decompile artifact — the point at
which "one coherent compiler" becomes a single typed calculation rather than two adjacent search kinds.

**Uptake record — formula search receipt + shared vocabulary** (closes `SRCH-RCT-01`, `SRCH-BUD-01`; advances
`SRCH-NO-01`) — this is probe (a) above, now done:

```text
ID:                  SRCH-RCT-01, SRCH-BUD-01
commit:              454d2a01c7201df14aaee71f653801d48c87c0e0
files:               smartchem/search.py (new), smartchem/decompiler.py, smartchem/experiment/routes.py,
                     smartchem/__init__.py, tests/test_decompiler.py
tests:               tests/test_decompiler.py::TestFormulaSearchReceipt (15 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2577 passed, 14 skipped, 1 xfailed (baseline 2562; +15 = the new tests). ruff clean; git
                     diff --check clean.
falsifier fixture:   search_decomposition("C8H9NO2", example_inventory(), budget=1) -> status
                     PARTIAL_SEARCH_BUDGET, graph REFUSED_BUDGET (a starved formula search is a loud partial, not
                     a complete-looking graph); max_edges=1 -> PARTIAL_RESULT_LIMIT (the two W2 walls are named
                     distinctly). build_decomposition(...) == search_decomposition(...).graph (compat).
human-output check:  none new -- the formula CLI already renders the graph's COMPLETE/REFUSED_BUDGET status; the
                     receipt adds the shared-vocabulary object for the future unified response.
JSON/schema check:   n/a -- shared JSON is CLI-JSON-01 (TODO). FormulaSearchReceipt/DecompositionSearchResult are
                     frozen Digestible values with pinned schema strings.
architecture:        SearchStatus now lives in smartchem/search.py (a stdlib-only leaf module), shared by the
                     top-level decompiler and the experiment package with no layering cycle; re-exported from
                     experiment.routes for compatibility. All three search kinds speak one status vocabulary.
residual limitations:
  1. No fake per-node counter on the formula receipt: the v1 closed-inventory descent is structurally depth-1
     (every product is a declared bucket or an element bucket, both terminal), so a nodes_expanded field would be
     a constant 1. Dropped rather than shipped as dishonest noise; it becomes meaningful only if v2 adds open
     generative intermediates (OPEN-SEARCH-01, DEFERRED).
  2. The three receipts share a vocabulary but are not yet one response object (SRCH-NO-01 renderer / CLI-JSON-01
     still open); the formula path has no empty-candidate no-route case (a formula graph always has edges).
```

**Uptake record — depth-limit truncation status** (closes `SRCH-DEPTH-01`; found by an adversarial red-team of
`recompile_to_ir`):

```text
ID:                  SRCH-DEPTH-01
commit:              ba69169
files:               smartchem/search.py, smartchem/experiment/routes.py, tests/test_routes.py, tests/test_cli.py
tests:               tests/test_routes.py (test_depth_truncation_is_reported_not_laundered_into_complete + the
                     corrected rich-api/cap/no-route assertions); tests/test_compilation_ir.py
                     (test_depth_truncation_is_never_laundered_to_complete_in_the_ir, in the recompile brick)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2632 passed, 14 skipped, 1 xfailed (with the recompile + stock bricks on the tree). ruff
                     clean on every changed file; git diff --check clean.
defect:              search_routes/search_dags dropped a branch when depth == max_depth with a still-missing
                     precursor, and NO counter recorded it. The SearchStatus enum had no depth member, so a
                     depth-truncated search reported COMPLETE_WITHIN_BOUNDS with empty diagnostics. Confirmed
                     repro: recompile_to_ir(PARA, reagents=(WATER,ACOH,ANH), available=(AMP,), max_depth=d) returns
                     2/5/9 route candidates at d=1/2/3, yet every one reported COMPLETE -- routes existed one bound
                     away and vanished silently (standard section 8.2 mandates a distinct INCOMPLETE_DEPTH_LIMIT).
fix:                 SearchStatus.PARTIAL_DEPTH_LIMIT + depth_truncated_branches:int on RouteSearchReceipt and
                     DAGSearchReceipt (trailing default 0, so existing positional constructions are unchanged),
                     folded into status/complete_within_bounds. A linear >=2-missing branch is a GRAMMAR boundary
                     (search_dags' job), not depth, so it is not counted; a node with no cleavages stays complete.
falsifier fixture:   search_routes(PARA, reagents=(WATER,ACOH,ANH), available=(AMP,), max_depth=1).receipt.status
                     is PARTIAL_DEPTH_LIMIT with depth_truncated_branches>0; at max_depth=3 it is
                     COMPLETE_WITHIN_BOUNDS with depth_truncated_branches==0 and strictly more routes. The
                     acetic-anhydride elemental no-route is PARTIAL_DEPTH_LIMIT at --max-depth 1 (a route may exist
                     deeper) and a genuine COMPLETE no-route at --max-depth 2 (nothing left to expand).
human-output check:  the experiment CLI receipt render and exit codes key off complete_within_bounds, so a
                     depth-truncated search with candidates now exits 4 (partial), and its render names
                     PARTIAL_DEPTH_LIMIT / PARTIAL_MULTIPLE_LIMITS -- never a false COMPLETE. Pinned by the
                     corrected test_cli tests.
residual limitations:
  1. depth_truncated_branches is CONSERVATIVE like the result cap: it fires whenever an expandable branch is cut
     by depth, even if that branch would have dead-ended deeper -- it errs toward "there may be more", never a
     false COMPLETE.
  2. Not yet in a shared JSON response (CLI-JSON-01) or the four-outcome renderer (SRCH-NO-01), both still open.
```

**Uptake record — section 8.1 engine counters on the route receipt** (opens `SRCH-RCT-8.1`; sub-brick 1 of the
full section 8.1 SearchReceipt arc):

```text
ID:                  SRCH-RCT-8.1 (linear route receipt)
commit:              2e4fbea
files:               smartchem/experiment/routes.py, tests/test_routes.py
tests:               tests/test_routes.py::TestSection81RouteReceiptTelemetry (8 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2675 passed, 14 skipped, 1 xfailed (baseline 2667; +8). ruff clean on every changed file;
                     git diff --check clean.
built:               RouteSearchReceipt gains the section 8.1 telemetry -- nodes_visited, transforms_considered,
                     candidates_emitted, candidates_rejected_by_reason{} (a sorted (reason,count) tuple:
                     "duplicate" for deduped routes, "result_limit" for the cap-triggering emission), search_kind
                     ("LINEAR_ROUTE"), cut_budget_scope ("PER_NODE"), and the derived cut_enumeration_complete /
                     candidate_enumeration_complete flags. search_routes instruments them; the schema bumps to
                     v1alpha2. Every counter is a real measurement or an explicit UNKNOWN (None) -- never a silent
                     zero for "not measured" (section 8.1). Additive/nullable: all new fields default to
                     UNKNOWN/empty, and zero tests construct the receipt directly or pin its schema string, so no
                     existing construction breaks.
found-and-fixed:     the honest invariant candidates_emitted == results_returned + sum(rejected) -- enforced at
                     construction AND pinned by test -- caught a real bug in the first cut of this change:
                     candidates_emitted was counted at EVERY recursion level (519, double-counting intermediate
                     sub-route assemblies) instead of the complete routes the generator emits to be collected
                     (183). Moved the count to the collection loop; the invariant now holds.
falsifier fixture:   a real para search reports nodes_visited>=expansions, transforms_considered>0,
                     candidates_emitted>=results_returned, rejected["duplicate"]>0, and cut/candidate enumeration
                     complete. max_routes=2 records rejected["result_limit"]>=1, status PARTIAL_RESULT_LIMIT, and
                     candidate_enumeration_complete=False. An in-stock target records genuine zeros (measured, not
                     UNKNOWN). A hand-built receipt with unmeasured counters reports UNKNOWN and render() says so.
                     Construction guards reject emitted<results, nodes<expansions, a bad cut_budget_scope, an empty
                     search_kind, a zero-count reason, and an unsorted rejection tuple.
residual limitations:
  1. LINEAR receipt only. The DAG receipt (search_dags) and the formula receipt (search_decomposition) carry the
     same instrumentation in the next sub-bricks.
  2. The three section 8.1 identity digests (target_identity_digest, terminal_policy_digest,
     transform_registry_digest) are NOT on the receipt yet -- transform_registry_digest lives in compilation_ir
     (a layering wrinkle: the search layer cannot import the IR layer), so it needs the registry descriptors
     relocated to a shared leaf first. A later sub-brick.
  3. The receipt status vocabulary is this engine's (COMPLETE_WITHIN_BOUNDS/PARTIAL_*), not section 8.2's
     (COMPLETE_WITHIN_DECLARED_SPACE/INCOMPLETE_*); reconciling the two names is a later sub-brick.
  4. nodes_visited currently equals expansions_attempted (the depth guard never trips: recursion stops at
     depth < max_depth). Honest and equal today; the field is meaningfully distinct and would diverge under a
     guard-tripping grammar.
```

**Uptake record — section 8.1 counters on the DAG and formula receipts** (advances `SRCH-RCT-8.1`; sub-brick 2 --
all three searches now carry the counters):

```text
ID:                  SRCH-RCT-8.1 (DAG + formula receipts)
commit:              dc9bd21
files:               smartchem/experiment/routes.py, smartchem/decompiler.py, tests/test_routes.py,
                     tests/test_decompiler.py
tests:               tests/test_routes.py::TestSection81DAGReceiptTelemetry (5) +
                     tests/test_decompiler.py::TestSection81FormulaReceiptTelemetry (4) -- 9 new adversarial items
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2684 passed, 14 skipped, 1 xfailed (baseline 2675; +9). ruff clean; git diff --check clean.
built:               DAGSearchReceipt (schema v1alpha2) gains the same counters as the route receipt -- rejection
                     reasons "duplicate" (digest dup), "dag_invalid" (DAGError-refused), "result_limit" (final-loop
                     cap trigger); search_kind "CONVERGENT_DAG". search_dags instruments them; the
                     emitted==results+sum(rejected) invariant holds at the final collection loop (a per-level
                     internal cap still sets result_limit_saturated, carried by the status, not a rejection count).
                     FormulaSearchReceipt (schema v1alpha2) is formula-shaped: each admissible edge is one
                     transform application, edges_emitted is the distinct collected result, so
                     transforms_considered (pre-dedup) >= edges_emitted; search_decomposition instruments
                     nodes_visited/transforms_considered/duplicate-rejections (the edge-cap incompleteness stays in
                     the status). The route/DAG telemetry validation is extracted to a shared module-level
                     _validate_section_8_1_telemetry; the formula receipt (a lower module that cannot import
                     experiment.routes) keeps its own.
falsifier fixture:   a real DAG search reports nodes>=expansions, transforms>0, emitted>=results, and the
                     emitted==results+rejected invariant; an in-stock DAG target records genuine zeros. A real
                     decomposition reports nodes>=1 and transforms>=edges_emitted. Every schema ends v1alpha2; a
                     hand-built receipt reports UNKNOWN; construction guards reject emitted<results (DAG),
                     transforms<edges (formula), and an unsorted/zero-count rejection tuple on both.
residual limitations (the remaining SRCH-RCT-8.1 sub-bricks):
  1. The three section 8.1 identity digests (target_identity_digest, terminal_policy_digest,
     transform_registry_digest) are still NOT on any receipt -- the transform_registry_digest layering wrinkle
     (search layer cannot import the IR layer) needs the registry descriptors relocated to a shared leaf first.
  2. The receipts' status vocabulary is still this engine's (COMPLETE_WITHIN_BOUNDS/PARTIAL_*), not section 8.2's;
     reconciling the names is the last sub-brick.
```

**Uptake record — section 8.1 identity digests + shared transform-registry leaf** (advances `SRCH-RCT-8.1`;
sub-brick 3 -- every receipt now names WHAT it searched):

```text
ID:                  SRCH-RCT-8.1 (identity digests)
commit:              453331a
files:               smartchem/transform_registry.py (new), smartchem/compilation_ir.py, smartchem/decompiler.py,
                     smartchem/experiment/routes.py, tests/test_routes.py, tests/test_decompiler.py,
                     tests/test_compilation_ir.py
tests:               tests/test_routes.py::TestSection81IdentityDigests (6) + formula digest items (2) + the
                     relocated registry test (test_compilation_ir.py::TestTransformRegistryDigest) -- 12 new/moved
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2692 passed, 14 skipped, 1 xfailed (the full run was 2690 + 2 stale v1alpha2 assertions this
                     session had written in sub-bricks 1-2, which the run flagged; fixed to v1alpha3 and confirmed,
                     no shipped code changed since). ruff clean; git diff --check clean.
built:               all three receipts (RouteSearchReceipt/DAGSearchReceipt/FormulaSearchReceipt, schemas
                     v1alpha3) gain target_identity_digest, terminal_policy_digest, transform_registry_digest,
                     populated by search_routes/search_dags/search_decomposition (UNKNOWN None when a receipt is
                     hand-built; a genuine value even for an in-stock/trivial termination). RESOLVES THE LAYERING
                     WRINKLE: the transform-registry identity moved to a new shared leaf
                     smartchem/transform_registry.py (below both the search and IR layers), imported by both, so
                     the receipts and the IR stamp the SAME registry digest. compilation_ir re-exports
                     transform_registry_digest under its historical private name; the monkeypatch test targets the
                     shared dict.
falsifier fixture:   recompile_to_ir(...).transform_registry_digest == search_routes(...).receipt
                     .transform_registry_digest (cross-layer agreement -- the relocation's payoff). Each receipt's
                     transform_registry_digest == transform_registry_digest(<its kind>). terminal_policy_digest
                     changes when the on-hand set changes. Every schema ends v1alpha3; an empty identity digest is
                     refused on all three receipts.
residual limitations (the last SRCH-RCT-8.1 sub-brick):
  1. The receipts' status vocabulary is still this engine's (COMPLETE_WITHIN_BOUNDS/PARTIAL_*), not section 8.2's
     (COMPLETE_WITHIN_DECLARED_SPACE/INCOMPLETE_*); reconciling the two names is sub-brick 4, the last one.
```

**Uptake record — section 8.2 status-vocabulary reconciliation** (CLOSES `SRCH-RCT-8.1`; sub-brick 4 -- every
receipt now speaks the standard's terminal-status vocabulary):

```text
ID:                  SRCH-RCT-8.1 (section 8.2 status vocabulary)
commit:              5c5b619
files:               smartchem/search.py, smartchem/experiment/routes.py, smartchem/decompiler.py,
                     tests/test_search.py (new), tests/test_routes.py, tests/test_decompiler.py
tests:               test_search.py::TestStandardNameMap (8) + ::TestPrimaryStandardStatus (7) +
                     test_routes.py::TestSection82StandardStatus (8) + test_decompiler.py::
                     TestSection82FormulaStandardStatus (5) -- 28 new
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2720 passed, 14 skipped, 1 xfailed. ruff clean; git diff --check clean.
built:               ADDITIVE section 8.2 reconciliation (no rename -- SearchStatus is referenced across the
                     decompiler/routes/DAG/IR layers). smartchem/search.py: SearchStatus.standard_name property,
                     STANDARD_8_2_STATUSES (the standard's 8 names verbatim), primary_standard_status(active).
                     RouteSearchReceipt/DAGSearchReceipt/FormulaSearchReceipt each gain a standard_status property;
                     route/DAG share a new _active_limits property so native status and standard_status read ONE
                     source. Non-1:1 BOTH ways: PARTIAL_CUT_BUDGET + PARTIAL_SEARCH_BUDGET collapse onto section
                     8.2's single INCOMPLETE_CUT_BUDGET; INCOMPLETE_CANDIDATE_LIMIT + REFUSED_* + ERROR_INTERNAL
                     have no engine source. PARTIAL_MULTIPLE_LIMITS.standard_name is None (the bare enum cannot
                     name one primary), but the receipt resolves the one primary section 8.2 requires from its
                     recorded limit flags via a most-severe-first precedence that always yields an INCOMPLETE_*
                     member -- never laundered toward complete (W2).
falsifier fixture:   a receipt with cut+result both firing has native status PARTIAL_MULTIPLE_LIMITS
                     (standard_name None) yet standard_status == INCOMPLETE_CUT_BUDGET (in STANDARD_8_2_STATUSES);
                     a total-coverage tripwire iterates the live enum (a future member with no mapping -> KeyError);
                     the documented residue is asserted EXACTLY equal to the four unsourced 8.2 names;
                     primary_standard_status is exercised over all 15 non-empty subsets and raises on the empty set.
red-team:            3 attack bearings + 6 verify agents (workflow, 784k subagent tokens). The mapping OUTPUT
                     survived every attack (3 boundaries: no laundering, no None leak, vocabulary byte-exact,
                     precedence 8.2-permitted). It CONFIRMED 3 comment-faithfulness defects, all fixed in 5c5b619:
                     (1) the cut_budget_scope disambiguation was inoperative -- the field is uniformly PER_NODE and
                     orthogonal to the cut-vs-search distinction; the real discriminator is search_kind + native
                     status. (2) the REFUSED_*/ERROR_INTERNAL residue was mislabeled "by design" -- section 8.1
                     mandates a receipt on refusal, but the engine RAISES; reworded to an acknowledged unbuilt gap.
                     (3) the precedence rationale wrongly said result-limit means "fully enumerated" -- false for
                     the conservative DAG cap; reworded to a severity convention with the DAG caveat.
residual limitations / next probes:
  1. IR-8.2-01: ChemicalCompilationIR.render() still emits the native status word (and one refusal string cites
     section 8.2 while printing a native token). The IR stores only receipt.status, not the per-limit flags, so
     resolving a MULTIPLE primary needs a schema field set at construction -- a digest-changing IR brick.
  2. The section 8.1 receipt-on-refusal path is unbuilt: an invalid/unsupported request (e.g. a charged decompile
     target, section 5.3) RAISES rather than returning a REFUSED_IDENTITY_UNSUPPORTED / REFUSED_INVALID_REQUEST
     receipt. Building it would give the three REFUSED_*/ERROR_INTERNAL statuses a real engine source.
```

**Uptake record — section 8.1 receipt on refusal** (`SRCH-REFUSE-8.1`; closes the receipt-on-refusal residual
noted in the SB4 record above, for the two REFUSED_* statuses):

```text
ID:                  SRCH-REFUSE-8.1 (section 8.1 receipt on refusal -- REFUSED_* return-path source)
commit:              1c4241f
files:               smartchem/search.py, smartchem/decompiler.py, tests/test_search.py, tests/test_decompiler.py
tests:               test_search.py::TestRefusalReceiptVocabulary (4) + ::TestRefusalReceipt (9) +
                     test_decompiler.py::TestSection81ReceiptOnRefusal (11) -- 24 new (35 counting parametrize)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2767 passed, 14 skipped, 1 xfailed. ruff clean; git diff --check clean.
built:               ADDITIVE, on a separate axis from the SearchStatus completeness receipts. smartchem/search.py:
                     RefusalReceipt (a frozen value carrying a section 8.2 REFUSED_*/ERROR_INTERNAL standard_status
                     + reason + request echo), the REFUSED_8_2_STATUSES / ERROR_8_2_STATUSES / NON_SEARCH_8_2_STATUSES
                     groupings, a construction guard (a completeness status or a whitespace-only reason is refused),
                     and render() whose lead word tracks is_refusal. REFUSED_*/ERROR_INTERNAL are deliberately NOT
                     SearchStatus members -- adding them would mis-bucket a refusal in every "COMPLETE else partial"
                     branch. smartchem/decompiler.py: IdentityUnsupportedError(DecompilerError) at the four charge
                     refusals (so REFUSED_IDENTITY_UNSUPPORTED and REFUSED_INVALID_REQUEST get DISTINCT sources),
                     classify_decompiler_refusal, and decompile_or_refuse -- a receipt-returning front door that
                     catches DecompilerError and returns a RefusalReceipt instead of raising. Malformed-formula
                     CONTENT (zero/negative subscript, empty formula) was widened from a bare ValueError to a
                     DecompilerError, so the whole malformed-formula category returns a receipt.
falsifier fixture:   decompile_or_refuse(Formula.of({"Na":1}, charge=1)) -> RefusalReceipt REFUSED_IDENTITY_UNSUPPORTED;
                     "C0"/{"C":0}/{"C":-1}/{} -> RefusalReceipt REFUSED_INVALID_REQUEST (not a raw ValueError);
                     a valid or budget-truncated target -> DecompositionSearchResult, standard_status NOT in
                     NON_SEARCH_8_2_STATUSES (a real search is never laundered into a refusal); budget=0 / a
                     wrong-Python-type target still RAISE (a caller bug, not a chemical refusal); a whitespace-only
                     RefusalReceipt reason and a completeness-status standard_status are both refused at construction.
red-team:            3 attack bearings + 6 verify agents (workflow, 638k subagent tokens). 5 CONFIRMED + 1 PLAUSIBLE,
                     0 refuted -- all fixed IN this commit before it landed: (1/2) the axis-escape -- malformed
                     formula CONTENT raised a bare ValueError from Formula.of that the front door's
                     `except DecompilerError` missed, escaping with NO receipt (fixed: the content checks now raise
                     DecompilerError); (3) a whitespace-only reason passed `if not self.reason` (fixed: .strip());
                     (4) three docstrings/comments called RefusalReceipt "a section 8.1 receipt", overclaiming the
                     full section 8.1 SearchReceipt schema (fixed: reworded to "sources the section 8.2 STATUS on the
                     refusal axis"); (PLAUSIBLE) render() printed "refused:" for an ERROR_INTERNAL whose is_refusal
                     is False (fixed: the lead word tracks is_refusal).
residual limitations / next probes:
  1. ERROR_INTERNAL still has no source here: turning an uncaught bug into an ERROR_INTERNAL receipt belongs to a
     top-level guarded service, not this domain front door (which catches only DecompilerError). A later brick.
  2. The full section 8.1 SearchReceipt schema on refusal (the ~20 mandated counters pinned to UNKNOWN/None) is not
     emitted; RefusalReceipt carries the section 8.2 status only. Emitting a null-counter SearchReceipt-on-refusal
     is the fuller conformance step.
  3. Scoped to the FORMULA decompiler front door. The route/DAG searches operate over already-parsed structures and
     raise only constructor/contract ValueErrors (not chemical-identity refusals), so a route/DAG decompile_or_refuse
     twin is a follow-on only if a domain refusal is added there.
  4. INCOMPLETE_CANDIDATE_LIMIT remains the one section 8.2 status with NO engine source (a genuine SearchStatus
     gap, not a refusal-axis one): no search here stops on a distinct emitted-candidate cap.
```

### 3.2 Decompiler/recompiler unity

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `IR-CHEM-01` | One `ChemicalCompilationIR` connects both directions | The shared IR envelope exists (`smartchem/compilation_ir.py`) and the formula decompiler emits it via `decompile_to_ir` (`09b3072`): a versioned value with a presentation-invariant, semantic-input-sensitive digest (a search-bound change alters it even when the candidate set is identical, via `request_digest`), carrying a typed target identity, terminal-policy digest, search status/receipt digest, and canonical digest-sorted candidates. The structural (route/DAG) producer now exists too: `recompile_to_ir` (`43dbcb1`) packages `search_routes`/`search_dags` as canonical `ROUTE`/`DAG` candidates over a STRUCTURE-layer identity, with the same presentation-invariant/semantic-sensitive digest (a bound change alters it via `request_digest`; the reagent helper pool is distinguished from plain stock). IR (de)serialization now round-trips digest-stably too (`serialize_ir`/`deserialize_ir`, canonical JSON; deserialize re-validates and refuses a tampered payload). The recompiler now CONSUMES a serialized decompile artifact end to end via `recompile_from_serialized` (`2e21490`, `IR-INV-01` closed on the refusal clause): it gates the structural hypothesis on the decompiled formula and classifies the inverse outcome, with water rendering a precise mode+bounds-scoped no-route refusal (no fabricated transform). The IR now also carries a first-class `transform_registry_digest` (`7268231`) naming WHICH grammar produced its candidates (section 8.4) and making the IR digest sensitive to the grammar version (section 4.1). First-class typed `IdentityLoss` records now ride INSIDE the IR (`IR-LOSS-01` first brick landed; IR schema `v1alpha3`, `identity_losses` is `array[object]`, loss content in the IR digest, tampered/vacuous loss refused on read); the fuller section 8.1 SearchReceipt (the other ~15 counters) remains | Carry the full section 8.1 SearchReceipt; wire `loss.blocks()` into evidence consumers (`EVD-KEY-01`) | `SRCH-RCT-01` (done), `ID-LAYER-01` | `IN_PROGRESS` |
| `IR-LOSS-01` | Formula/structure forgetting is explicit | First brick landed (`IR-LOSS-01`): `ChemicalCompilationIR.identity_losses` is now a tuple of first-class typed section-5.3 `IdentityLoss` records, not summary strings (IR schema `v1alpha2`→`v1alpha3`, an `array[str]`→`array[object]` shape change). A consumer reads `severity`/`affected_claims` structurally; the loss's semantic content RIDES the IR digest (a WARNING and a BLOCKER over the same feature are different IRs); `ir_from_payload` refuses a tampered/vacuous-BLOCKER loss on read; the human/JSON one-line agreement is preserved via the derived `identity_loss_summaries` + the descriptor's new `identity_loss_fields`. Acceptance MET: `CCO` vs `COC` SMILES decompilations share ONE formula target yet stay distinct (each input survives in its loss record) and each announces the collapse as a BLOCKER. The evidence CONSUMERS checking `loss.blocks()` to refuse a dependent sourced claim are now BUILT and threaded to production (`EVD-KEY-01`) | Consumer gate DONE (`EVD-KEY-01`); ID-STEREO-01 losses now also ride the IR | `CCO` vs `COC` remain distinct as input identities; formula view announces collapse — **DONE** (`tests/test_ir_loss.py`) | `ID-LAYER-01` | `IN_PROGRESS` |
| `IR-INV-01` | Claimed inverse scope is executable | `recompile_from_serialized` (`2e21490`) consumes a serialized decompile artifact end to end: it gates the structural hypothesis on the decompiled formula (section 5.4) and classifies the inverse outcome (six-way `InverseStatus`). Water (H2O from H2/O2) renders a PRECISE unsupported-transform refusal (`NO_ROUTE_IN_GRAMMAR`), scoped to the mode+bounds, with no fabricated transform (W3) — the acceptance's refusal clause. An EXHAUSTIVE empty search is distinguished from a TRUNCATED one (`INCONCLUSIVE_BOUNDS_HIT`) | Refusal clause met; a named inter-grammar transform registry that SUCCEEDS on water remains a future, SOURCED brick (narrowed naming/docs, never a fabricated reaction) | Water renders a precise unsupported-transform refusal (**met**) OR succeeds within a named transform registry (future) | `IR-CHEM-01` | `DONE` (refusal clause) |
| `IR-8.2-01` | The IR speaks the section 8.2 terminal-status vocabulary | `ChemicalCompilationIR` now carries a stored `standard_status` (a section 8.2 name) set at construction from the live `receipt.standard_status` -- the only place `PARTIAL_MULTIPLE_LIMITS` resolves to one primary (`54d5731`, schema -> v1alpha2). A `__post_init__` guard makes it impossible to carry a section 8.2 status contradicting the native `search_status` (single-limit: exactly `search_status.standard_name`; MULTIPLE: a resolvable primary from `PRIMARY_RESOLVABLE_8_2_STATUSES`, never a completion, never `INCOMPLETE_CANDIDATE_LIMIT`). `render()` leads with the section 8.2 status and labels the native one `engine:`; the `INCONCLUSIVE_BOUNDS_HIT` refusal now prints an actual section 8.2 status (closing the SB4 red-team's finding 4) and cross-references section 8.3's `INCOMPLETE_NO_ROUTE_OBSERVED`. Round-trip digest-stable. A 3-bearing red-team found the code faithful on every reachable path (no W2 laundering, no section-4.1 digest-law break, no reachable guard hole, schema bump safe) + 2 comment-precision fixes | The section 8.1 receipt-on-refusal path (now BUILT for REFUSED_* via `decompile_or_refuse`/`RefusalReceipt`, `SRCH-REFUSE-8.1`; ERROR_INTERNAL still RAISEs); adopting section 8.3's four required no-route/candidate tokens across ALL cells is a separate systemic brick | The IR renders a section 8.2 status for every producer; a hand-built IR whose section 8.2 status contradicts its native one is refused; the section-8.2-citing refusal prints a real section 8.2 token | `SRCH-RCT-8.1` (done), `IR-CHEM-01` | `IMPLEMENTED_AND_VERIFIED` |

**Uptake record — ChemicalCompilationIR first brick** (advances `IR-CHEM-01` TODO -> IN_PROGRESS):

```text
ID:                  IR-CHEM-01 (first brick)
commit:              09b3072
files:               smartchem/compilation_ir.py (new), smartchem/__init__.py, tests/test_compilation_ir.py
tests:               tests/test_compilation_ir.py (13 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2595 passed, 14 skipped, 1 xfailed (baseline 2582; +13). ruff clean; git diff --check clean.
built:               ChemicalCompilationIR (the section 4.1 envelope), ChemicalIdentity (minimal formula/structure
                     layer tag), CandidateSummary, and decompile_to_ir (the first producer: the formula decompiler
                     emits the IR from search_decomposition).
falsifier fixture:   decompile_to_ir("C8H9NO2", inv, budget=100_000).digest != (...budget=90_000).digest WHILE the
                     two candidate sets are byte-for-byte identical -- the section 4.1 rule that a search-bound
                     change alters the digest holds via request_digest. Reordering the inventory does NOT change
                     the digest (presentation invariance). Changing the target or inventory DOES.
residual limitations (the rest of IR-CHEM-01, named in code and its row):
  1. Only the FORMULA producer exists; the structural (route/DAG) producer is TODO.
  2. The IR is an in-memory value; serialize/deserialize + the recompiler consuming a SERIALIZED artifact
     (the IR-CHEM-01 acceptance) is TODO, as is the water-from-buckets inverse (IR-INV-01).
  3. identity_losses is empty: formula decompile forgets topology, but first-class IdentityLoss records need
     ID-LAYER-01 (IR-LOSS-01, TODO). ChemicalIdentity is a layer TAG, not the full section 5.1 identity model.
  4. search is carried as status + receipt digest, not the full embedded receipt; registry receipts are absent.
```

**Uptake record — ChemicalCompilationIR structural producer** (advances `IR-CHEM-01`; the recompiler now emits
the same shared artifact the decompiler does):

```text
ID:                  IR-CHEM-01 (structural producer)
commit:              43dbcb1
files:               smartchem/compilation_ir.py, smartchem/__init__.py, tests/test_compilation_ir.py
tests:               tests/test_compilation_ir.py::TestRecompileToIR (12 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2632 passed, 14 skipped, 1 xfailed (with the depth-fix + stock bricks on the tree). ruff
                     clean on every changed file; git diff --check clean.
built:               recompile_to_ir (mode='routes'|'dags') packaging search_routes/search_dags as canonical
                     digest-sorted ROUTE/DAG CandidateSummary values; ChemicalIdentity.of_molecule (STRUCTURE
                     layer, byte-congruent with the pipeline's _ident); a structural terminal-policy digest
                     (frozenset of the on-hand identities) and a request_digest that also distinguishes the
                     reagent helper pool from plain stock.
falsifier fixture:   permuting reagents/available does NOT change ir.digest (frozenset terminal + digest-sorted
                     candidates); a cut_budget change DOES change request_digest (hence ir.digest) while the
                     candidate set is byte-identical; PARA vs its O-acetyl isomer (same formula C8H9NO2) get
                     distinct target identity_digests and distinct IRs (section 5.4); a depth-1 recompile reports
                     PARTIAL_DEPTH_LIMIT + a diagnostic, never a laundered COMPLETE (the SRCH-DEPTH-01 regression
                     at the IR layer); a target already in terminal stock yields 0 candidates + an explicit
                     "no synthesis is required" diagnostic.
adversarial review:  an independent red-team (evil-morty) attacked presentation-invariance, semantic-sensitivity,
                     the reagent-pool/terminal-set distinction, isomer distinctness, and no-silent-laundering.
                     Four survived; the fifth (depth laundering) was a real defect in the search layer beneath,
                     now fixed as SRCH-DEPTH-01 and regression-pinned here.
residual limitations (the rest of IR-CHEM-01, unchanged and named):
  1. Still an in-memory value: serialize/deserialize + the recompiler consuming a SERIALIZED artifact (IR-INV-01,
     water-from-buckets) is the next brick.
  2. identity_losses is empty for the structural path too (assembly forgets nothing at the structure layer);
     first-class IdentityLoss records are IR-LOSS-01 (gated on ID-LAYER-01).
  3. search is carried as status + receipt digest; registry receipts are absent.
```

**Uptake record — ChemicalCompilationIR serialization** (advances `IR-CHEM-01`; the IR is now a transportable
artifact, not just an in-memory value):

```text
ID:                  IR-CHEM-01 (serialization)
commit:              3819f75
files:               smartchem/compilation_ir.py, smartchem/__init__.py, tests/test_compilation_ir.py
tests:               tests/test_compilation_ir.py::TestIRSerialization (7 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2643 passed, 14 skipped, 1 xfailed (baseline 2632; +11 = the IR-serialize + bridge tests).
                     ruff clean on every changed file; git diff --check clean.
built:               ir_to_payload / ir_from_payload (JSON-compatible dict, enums by value, tuples as lists) and
                     serialize_ir / deserialize_ir (canonical sort_keys JSON string).
falsifier fixture:   deserialize_ir(serialize_ir(ir)).digest == ir.digest for BOTH the formula (decompile) and
                     structural (recompile) producers -- the round trip is identity. deserialize RE-VALIDATES:
                     a payload with candidates reversed out of canonical digest order raises "canonical order";
                     an unknown operation enum value raises. serialize is presentation-invariant (permuted inputs
                     -> identical string). Type guards on both ends.
residual limitations:
  1. Serializes the IR VALUE (target, terminal/request digests, status + receipt digest, candidates); it does not
     yet embed the full SearchReceipt or the transform/evidence registry receipts (still IR-CHEM-01 residuals).
  2. The recompiler does not yet CONSUME a serialized decompile artifact end to end (IR-INV-01); this brick is the
     serialize/deserialize primitive that makes that wiring possible.
```

**Uptake record — IR-INV-01: the recompiler consumes a SERIALIZED decompile artifact end to end** (advances
`IR-CHEM-01`; closes `IR-INV-01` on the refusal clause):

```text
ID:                  IR-INV-01
commit:              2e21490
files:               smartchem/compilation_ir.py, smartchem/__init__.py, tests/test_compilation_ir.py
tests:               tests/test_compilation_ir.py::TestRecompileFromSerialized (12 items) +
                     ::TestRecompileNoRouteDiagnostic (5 items) -- 17 new adversarial items
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2660 passed, 14 skipped, 1 xfailed (baseline 2643; +17). ruff clean on every changed file;
                     git diff --check clean.
built:               recompile_from_serialized(text, structure=, reagents=, ...) -- deserializes a DECOMPILE
                     artifact, gates the structural hypothesis on the decompiled formula (section 5.4 coherence),
                     runs recompile_to_ir, and classifies the inverse outcome as an InverseStatus:
                     NOT_A_DECOMPILE_ARTIFACT / FORMULA_MISMATCH (pre-search refusals, no recompile IR) |
                     TARGET_ALREADY_TERMINAL / ROUTES_FOUND (successes) | NO_ROUTE_IN_GRAMMAR (EXHAUSTIVE empty
                     within THIS mode+bounds) | INCONCLUSIVE_BOUNDS_HIT (TRUNCATED empty: cannot conclude).
                     InverseResult bundles the consumed decompile IR + the produced recompile IR + verdict +
                     precise refusal, and enforces its OWN coherence (each slot carries the operation its name
                     advertises; NOT_A_DECOMPILE_ARTIFACT is the one exemption -- it reports the offending
                     artifact). ALSO fixed recompile_to_ir: a complete-within-bounds, zero-candidate,
                     not-in-stock search now emits a precise "exhaustive within THIS mode at THESE bounds"
                     diagnostic instead of a SILENT empty (the SRCH-DEPTH-01 laundering one layer up).
acceptance (IR-INV-01, refusal clause): water. decompile_to_ir("H2O") -> serialize -> recompile_from_serialized(
                     text, structure=water, reagents=(H2, O2)) returns NO_ROUTE_IN_GRAMMAR with a precise
                     unsupported-transform refusal and a recompile IR with ZERO candidates. NO water reaction is
                     invented (W3): elemental redox is outside the capped-scission grammar, and the compiler SAYS
                     SO -- but scoped to what the receipt proves. The manifest's first clause (a named transform
                     registry that SUCCEEDS on water) is deliberately NOT taken: fabricating a transform violates W3.
falsifier fixture:   the EXHAUSTIVE-vs-TRUNCATED split is load-bearing and pinned: water (complete, empty) ->
                     NO_ROUTE_IN_GRAMMAR; the SAME shape starved to PARTIAL_CUT_BUDGET -> INCONCLUSIVE_BOUNDS_HIT,
                     never a dead end. A structure whose formula != the decompiled formula -> FORMULA_MISMATCH
                     BEFORE any search. Same-formula isomers (PARA vs its O-acetyl ester, both C8H9NO2) both PASS
                     the formula gate and key on DISTINCT structure identities. A RECOMPILE artifact fed as input
                     -> refused. A tampered artifact (candidates out of canonical order) -> refused on read.
adversarial review:  an independent red-team (evil-morty) attacked the no-route diagnostic's truthfulness, the
                     six-way classifier, the formula-digest gate, W3, and the InverseResult invariants. Two
                     VERIFIED findings, both fixed and regression-pinned here:
                     (1) MEDIUM -- the no-route refusal claimed a REGISTRY-WIDE dead end, but complete_within_bounds
                         proves only exhaustion of THIS mode's grammar at THESE bounds; the SAME request under
                         mode='dags' reaches PARTIAL. Fix: both the recompile_to_ir diagnostic and the bridge
                         refusal now scope the claim to the mode+bounds and explicitly do NOT exclude a different
                         mode / higher bounds. Pinned by test_the_no_route_diagnostic_does_not_overclaim_registry_wide.
                     (2) LOW -- InverseResult did not enforce that its two IR slots carry the right operation;
                         a DECOMPILE artifact could sit in the recompile slot. Fix: __post_init__ now checks it
                         (NOT_A_DECOMPILE_ARTIFACT exempted). Pinned by test_result_enforces_operation_coherence.
                     The classifier's target-terminal agreement, the formula gate, the guard (op AND layer), and
                     W3 (no fabricated candidate) all survived. The render() "reconstituted" wording was softened
                     to "routes for the supplied structure" so a formula-level success does not read as isomer-
                     level identity confirmation.
residual limitations:
  1. The formula gate is FORMULA-layer by construction (section 5.4): any same-formula isomer is a legitimate
     structural hypothesis for a formula-level decompile artifact -- the bridge reconstitutes the ISOMER THE
     CALLER SUPPLIES, honestly labeled, never a claim it is THE decompiled structure (a formula does not fix
     one). Structure-layer artifacts + isomer-exact matching is ID-LAYER-01 / IR-LOSS-01.
  2. The refusal clause is taken, not the transform-registry clause: no named inter-grammar transform (e.g.
     elemental redox) exists yet; adding one is a future brick, and it must be SOURCED, never fabricated.
  3. Degenerate inputs (reagents=(), max_depth/max_results/cut_budget <= 0) raise the underlying search's own
     precise ValueError/TypeError from a lower frame rather than a bridge-level message -- a documented boundary
     (red-team finding 3, LOW): the errors are already exact, so no ceremony re-guard was added.
  4. identity_losses is still empty (IR-LOSS-01, gated on ID-LAYER-01); registry receipts still absent.
```

**Uptake record — ChemicalCompilationIR transform-registry identity** (advances `IR-CHEM-01`; the IR now names
WHICH grammar produced its candidates, section 8.4, and its digest is sensitive to the grammar version,
section 4.1):

```text
ID:                  IR-CHEM-01 (transform-registry identity)
commit:              7268231
files:               smartchem/compilation_ir.py, tests/test_compilation_ir.py
tests:               tests/test_compilation_ir.py::TestTransformRegistryDigest (7 new adversarial items) +
                     round-trip/construction updates
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2667 passed, 14 skipped, 1 xfailed (baseline 2660; +7). ruff clean on every changed file;
                     git diff --check clean.
built:               transform_registry_digest -- a first-class ChemicalCompilationIR field naming the transform
                     grammar (registry) that generated the candidates. _TRANSFORM_REGISTRIES declares one
                     descriptor per search kind (formula-decomposition / capped-scission-linear /
                     capped-scission-convergent); _transform_registry_digest(kind) is its canonical digest. Both
                     producers stamp it AND fold it into request_digest, so a grammar-version change alters the
                     IR digest (section 4.1) even when target/terminals/bounds/candidates are byte-identical. This
                     is the identity section 8.4's "all pathways generated by transform registry <digest>" names.
falsifier fixture:   monkeypatching a registry descriptor's version token to 'v2-TEST' leaves the candidate set
                     byte-identical yet changes transform_registry_digest, request_digest, AND the full IR digest
                     (the section 4.1 provider-version sensitivity, pinned). The three grammars carry DISTINCT
                     registry digests. The digest is presentation-invariant (permuting the inventory never changes
                     it -- it is a property of the grammar, not the request order). Round-trip preserves it; an
                     empty registry digest is refused at construction; an unknown kind is refused.
residual limitations:
  1. A grammar here is imperative code (no enumerable rule table to hash), so the registry identity is a DECLARED
     version token -- operator-maintained, the same discipline as every schema_version. The digest changes only
     when the descriptor's version is bumped; a structural output change is caught downstream (it bumps STEP/ROUTE
     candidate schemas), but a pure rule-set change with identical output structure needs the manual bump. This is
     documented in code (W3) and is the honest limit until the grammar becomes a hashable rule set.
  2. The digest lives on the IR; the full section 8.1 SearchReceipt (which also mandates transform_registry_digest
     plus ~15 other counters -- nodes_visited, transforms_considered, candidates_rejected_by_reason{}, the
     enumeration-complete flags) is a broader, later conformance arc. This brick surfaces the ONE field section 4.1
     requires for digest sensitivity, not the whole receipt schema.
```

**Uptake record — the IR speaks section 8.2** (`IR-8.2-01`; the SB4 follow-up: the IR now renders the standard's
terminal-status vocabulary, not the engine's native word):

```text
ID:                  IR-8.2-01 (section 8.2 status face on ChemicalCompilationIR)
commit:              54d5731
files:               smartchem/compilation_ir.py, smartchem/search.py, tests/test_compilation_ir.py
tests:               tests/test_compilation_ir.py::TestSection82IRFace (12 new) + the 3 positional constructions
                     threaded; tests/test_search.py unchanged but re-exercises PRIMARY_RESOLVABLE_8_2_STATUSES
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2732 passed, 14 skipped, 1 xfailed (baseline 2720; +12). ruff clean on every changed file;
                     git diff --check clean.
built:               a stored standard_status:str field on ChemicalCompilationIR (schema v1alpha1 -> v1alpha2),
                     set at construction from the LIVE receipt.standard_status -- the only place a
                     PARTIAL_MULTIPLE_LIMITS receipt resolves to one section 8.2 primary (the IR keeps only the
                     receipt DIGEST, not the per-limit flags).  A __post_init__ guard forbids a section 8.2 status
                     that contradicts the native search_status: single-limit must equal search_status.standard_name;
                     PARTIAL_MULTIPLE_LIMITS must be one of PRIMARY_RESOLVABLE_8_2_STATUSES (= INCOMPLETE_CUT_BUDGET
                     / INCOMPLETE_DEPTH_LIMIT / INCOMPLETE_RESULT_LIMIT), so a completion status or an unsourced
                     INCOMPLETE_CANDIDATE_LIMIT / REFUSED_* / ERROR_INTERNAL is refused.  render() leads with the
                     section 8.2 status and labels the native one 'engine:'; ir_to_payload/ir_from_payload thread
                     the field (round-trip digest-stable).  The InverseResult render + the INCONCLUSIVE_BOUNDS_HIT
                     refusal now print standard_status -- closing the SB4 red-team's finding 4 (the refusal cited
                     section 8.2 while printing a native token) -- and that refusal now also names section 8.3's
                     INCOMPLETE_NO_ROUTE_OBSERVED for its zero-candidate/incomplete no-route cell, matching its
                     sibling NO_ROUTE_IN_GRAMMAR branch.
falsifier fixture:   a decompile IR reports COMPLETE_WITHIN_DECLARED_SPACE, a depth-limited recompile IR reports
                     INCOMPLETE_DEPTH_LIMIT; a hand-built IR pairing COMPLETE native with an INCOMPLETE_* label is
                     refused, as is a MULTIPLE native with COMPLETE_WITHIN_DECLARED_SPACE or INCOMPLETE_CANDIDATE_
                     LIMIT; the engine's own native token (e.g. PARTIAL_CUT_BUDGET) is refused as not a section 8.2
                     name; deserialize(serialize(ir)).digest == ir.digest with the new field; the INCONCLUSIVE
                     refusal contains a section 8.2 status, contains no 'PARTIAL_' token, and names section 8.3 +
                     INCOMPLETE_NO_ROUTE_OBSERVED.
red-team:            3 attack bearings + 3 verify agents (workflow, 513k subagent tokens). The CODE survived every
                     attack on every reachable path (3 boundaries: the guard rejects exactly the right set and
                     never crashes a real producer; standard_status never leaks into request_digest and never
                     splits two semantically-equal producer IRs; the schema bump has no dangling v1alpha1 ref and
                     old payloads fail closed).  It CONFIRMED (PARTIAL) 2 comment-precision over-claims, both fixed
                     in 54d5731: the guard docstring's unconditional 'tampered payload is refused' is now scoped to
                     what the guard can pin (MULTIPLE cannot pin WHICH primary without the flags -- reachable only
                     by a hand-built, internally-inconsistent, still-INCOMPLETE payload, never a real producer,
                     never toward complete); and the refusal gained its section 8.3 cross-reference.  One finding
                     REFUTED (a diagnostic printing a native token -- conceded acceptable, no iron-rule breach).
residual limitations / next probes:
  1. The MULTIPLE-case guard checks the primary is one resolution CAN legally produce, not the one THIS receipt's
     flags imply -- structurally, because the IR carries only search_receipt_digest.  This is W2-safe (every value
     is INCOMPLETE_*), never reachable by a real producer (which passes receipt.standard_status), and documented in
     the guard comment.  True per-receipt pinning would need the IR to carry the per-limit flags (a later schema).
  2. A superseded v1alpha1 IR payload fails closed with KeyError('standard_status') rather than the schema-version
     ValueError (ir_from_payload reads the field before __post_init__ runs).  Both fail closed; there is no
     backward-compat contract for a pre-release alpha and no persisted v1alpha1 payloads, so this is a documented
     boundary, not a defect.
  3. Adopting section 8.3's four Required no-route/candidate tokens (NO_ROUTE_IN_DECLARED_SPACE /
     INCOMPLETE_NO_ROUTE_OBSERVED / COMPLETE_CANDIDATE_SET / PARTIAL_CANDIDATE_SET) uniformly across every renderer
     is a separate systemic brick; this change added the one where it was directly editing.
```

### 3.3 Identity and evidence

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `ID-LAYER-01` | Formula, molecule/formula-unit, and stock material are distinct values | First brick landed (`67b4715`): `smartchem/identity.py` provides the section 5.1 `MatchLayer` lattice (FORMULA<CONSTITUTION<CONFIGURATION<ISOTOPIC + `refines`), `LayeredIdentity` (per-layer digests byte-congruent with `ChemicalIdentity.of_molecule`/`of_formula`; FORMULA carries total charge; perceives FORMULA+CONSTITUTION, finer layers ABSENT not guessed), `same_identity_at` (section 5.4 layer-relative equality, honest `None` when a layer is unperceived — a formula match is NEVER promoted to structure), and the section 5.3 `IdentityLoss` record + `formula_reduction_loss` (a BLOCKER over the four named evidence classes + structure claims; a blocker that blocks nothing is refused). Consumer: `decompile --smiles` records the typed loss on every path. **`MatchLayer`→`IdentityPolicy` wiring is now BUILT (`ID-LAYER-02`)**: `IdentityPolicy` carries a `match_layer` (part of the `semantic_digest`), so a request DECLARES its comparison layer, and `run_compilation` ENFORCES it — a layer the engine cannot honestly honor (a finer, unperceived CONFIGURATION/ISOTOPIC, or the coarser FORMULA for a structure search per section 5.4/G3) is a REFUSED response (exit 5, `REFUSED_IDENTITY_UNSUPPORTED`), never a silent match at the wrong layer; a `--match-layer` CLI flag declares it end to end. Stereo/isotope DETECTION+BLOCKER is now BUILT (`ID-STEREO-01`: the finer features are recorded as typed section-5.3 losses, never silently dropped); sound stereo/isotope PERCEPTION (a canonical CONFIGURATION/ISOTOPIC digest) and salt/mixture COMPONENT identity remain | Add typed layers and conversion/loss rules | Disconnected salt, chiral, isotope and mixture fixtures preserve identity or refuse — section 5.4 probe DONE (same-formula isomers agree at FORMULA, distinct at CONSTITUTION; unperceived layers UNKNOWN not fabricated); ID-LAYER-02 layer-declare+enforce DONE (`tests/test_identity.py`) | None | `IN_PROGRESS` |
| `ID-PARSE-01` | Explicit name/SMILES/InChI/formula parsing with echoed normalization | **The ONE parser service is BUILT.** `identity_parse.py` `resolve_identity` resolves EVERY section-14.2 form: NAME/SMILES → a Molecule (CONSTITUTION); FORMULA and an InChI FORMULA SUBLAYER → a FORMULA-layer identity (the InChI's `/q`,`/p` CHARGE layers are CONSUMED into a correctly-charged `Formula` — `[NH4+]` never collapses to neutral NH3, F1 red-team fold — while `/c`,`/h` connectivity, `/t`,`/b`,`/m`,`/s` stereo and `/i` isotope become typed section-5.3 BLOCKERS and any other layer is NAMED in a note); TARGET_FILE dispatches its contents. Each resolution carries a typed `ParseReceipt` (requested/resolved kind, `ParseSource`, normalised Hill form, layer, notes) ECHOED into the response `diagnostics` — surfaced in BOTH the human render and `--json` (RECEIPT-HUMAN-DROP red-team fold). Explicit `name:`/`smiles:`/`inchi:`/`formula:` prefixes + a bare `InChI=` header disambiguate; a bare formula/InChI (composition, not structure) is refused for a structure search (section 5.4). `resolve_target`/`resolve_target_with_features` are thin wrappers. REMAINING: collapsing `name:X`≡`X` into the `semantic_digest` (alias-collapse) needs the receipt's provenance-vs-search-identity status resolved first (a named design step) | Alias-collapse in `semantic_digest` (the receipt-vs-collapse design) | Registered names pass; every explicit form round-trips; ambiguity is disambiguated not guessed; InChI charge is not dropped — **DONE** (`tests/test_id_parse.py`) | `ID-LAYER-01` | `IN_PROGRESS` |
| `ID-STEREO-01` | Stereo/isotope/local-charge/component loss never silent | **Parse-boundary DETECTION + typed section-5.3 BLOCKER BUILT.** `smiles.py` `parse_smiles_features` now CAPTURES the isotope labels, tetrahedral (`@`/`@@`) and double-bond (`/`/`\`) stereochemistry and net-neutral local-charge separation a SMILES declares but the constitution-only `Molecule` drops (`parse_smiles` still returns the byte-identical Molecule; the feature door agrees on it). `identity.py` `stereo_loss`/`isotope_loss`/`local_charge_loss`/`representation_losses_for` lower each PRESENT feature to a typed BLOCKER (a flat/unlabelled/neutral input yields `()`, never a vacuous blanket). Wired on BOTH the recompile path (constitution kept, finer features dropped → the losses ride the IR via `recompile_to_ir`'s new `identity_losses`) and the decompile path (beside the formula-reduction blocker); the decompile render prints them from the response so human == JSON. An enantiomer/isotopologue/zwitterion no longer SILENTLY collides — it shares the flat analogue's constitution but carries a distinguishing BLOCKER; a disconnected salt stays a LOUD refusal. HONEST BOUNDARY (correcting the ID-LAYER-02 record's forward projection): this is the "record blocker" arm, NOT stereo/isotope PERCEPTION — a sound CONFIGURATION/ISOTOPIC digest needs canonical CIP / positioned-isotopologue keys and the atom-coloured `Molecule`, so `--match-layer configuration` REMAINS refused (perception deferred, not made honorable by detection). The double-bond scan is a conservative presence-check (fail-CLOSED over-detection of a redundant directional bond, documented). **Sound ISOTOPE PERCEPTION now BUILT**: `smiles.py` `isotope_refined_key`/`_isotopic_identity` compute a canonical isotope-refined-CONSTITUTION key by running the SAME proven graph canonicaliser (`_canonical_by_individualisation`) over an ISOTOPE-COLOURED copy of the graph — presentation-invariant, symmetric-position-invariant, positionally-distinct, resonance-canonical (it commits to the EXACT Kekulé structure the constitution does, so a fused benzenoid does NOT split across aromatic-vs-Kekulé spelling — ID-STEREO-01-SPLIT-KEKULE red-team fold), and it REFINES constitution. `SmilesFeatures.isotopic_digest` carries it. HONEST BOUNDARY (never faked): the key is the isotope refinement of CONSTITUTION, MODULO stereochemistry (chirality is a reflection, invisible to graph canonicalisation), so it does NOT fill the MatchLayer lattice ISOTOPIC slot (which sits above CONFIGURATION and additionally needs sound CIP-parity stereo perception) — that + CONFIGURATION remain the deferral | Sound CONFIGURATION (CIP-parity stereo) perception + the MatchLayer lattice ISOTOPIC slot is the remaining piece | Enantiomer/isotope/zwitterion/disconnected-salt do not silently collide; isotopologues are distinguishable by a sound canonical key that never splits one species — **DONE** (`tests/test_id_stereo.py`) | `ID-LAYER-01` | `IN_PROGRESS` |
| `ID-SCISS-01` | Structural scission preserves the represented rooted open valence and refuses unsupported charge | Rooted open-valence identity and neutral-only refusal are implemented; duplicate reagent types are deduplicated | Keep this scoped refusal while broader identity layers are built | Rooted isomers remain distinct; non-neutral target refuses; duplicate reagent spellings do not multiply candidates | None | `IMPLEMENTED_AND_VERIFIED` |
| `EVD-KEY-01` | Evidence key includes structure, primitive stoichiometry, direction, context and source | **The section-5.3 consumer gate is BUILT and reaches production.** `identity.py` `blocking_losses`/`is_blocked`/`blocked_claim_classes` are the consumer primitive; the sourced-evidence providers (`selectivity_of_step`/`verify_selectivity`, `reaction_conditions`/`assembly_conditions`, `kinetics_of_step`/`verify_kinetics`) take a `losses=` gate that downgrades a SOURCED verdict to a loud UNKNOWN when a BLOCKER forbids its claim class — claim-class-PRECISE (an isotope blocker gags kinetics but not selectivity; a stereo blocker does NOT touch the constitution-level handling hazard) and NON-VACUOUS. The gate is THREADED END-TO-END through the production dossier (`compile_synthesis`→`rank_routes`→`fit_route`, the public `classify_step`/`classify_route`/`classify_dag`, `draft_route_dossier`) and the `compile` CLI supplies the target's losses, so a stereo/isotope target's sourced selectivity/kinetics verdict is gated on a REAL compile/classify run — not just under direct injection. **The unified `ReactionEvidenceKey` is now BUILT** (`smartchem/evidence_key.py`): the section-9.1 value — canonical reactant/product STRUCTURE identities + PRIMITIVE (gcd-reduced) stoichiometry + direction-by-side + optional context (phase/standard-state) — isomer-distinct, scale-invariant, context-refinable. It is LIVE in the SOUND rate anchor, not a dead switch: `kinetics.py` `reaction_evidence_key`/`record_evidence_key` and `eyring.py` `_resolve_barrier` resolve sourced records THROUGH it, byte-congruent to the `(reactants, products)` tuple they replaced (`reaction_key_of` is now its `.sides` view). REMAINING: migrating the FORMULA-keyed providers (`decompiler_conditions` decomposition path, `selectivity`, `decompiler_review`) onto it — which would close their isomer-borrow hazard — and populating `context`; those do NOT key on it yet (the formula-edge review path lacks structural certainty) | Migrate the FORMULA-keyed providers (conditions/selectivity/review) onto `ReactionEvidenceKey` | Same-formula isomer passes; a stereo/isotope/charge BLOCKER downgrades a sourced verdict end-to-end (consumer gate); the unified key is isomer-distinct/direction-specific/scale-invariant and live in kinetics/eyring — **DONE** (`tests/test_evd_key.py`, `tests/test_evidence_key.py`) | `STO-PRIM-01`, `ID-LAYER-01` | `IN_PROGRESS` |
| `EVD-DIR-02` | Decomposition evidence cannot promote reverse assembly | Direction-specific exact-structure assembly lookup is implemented and tested | Preserve through general provider/serialization work | Hydrolysis source yields unknown reverse-condensation envelope unless separately sourced | `EVD-KEY-01` | `IMPLEMENTED_AND_VERIFIED` |
| `EVD-SRC-01` | Sourced records have inspectable exact locators and context | Conditions/selectivity now distinguish typed accepted citations from unreviewed/free-text declarations; other providers and full context keys remain uneven | Generalize `SourceCitation` and exact context validation across providers | Missing/malformed/unreviewed locator cannot promote now; add phase/context/provider fixtures | `EVD-KEY-01` | `IN_PROGRESS` |
| `EVD-CONF-01` | Provider conflicts are visible | First-loaded/first-wins behavior can hide disagreement | Emit `ProviderConflict`; serialize priority choice | Conflicting fixture never changes silently with provider order | `EVD-SRC-01` | `TODO` |
| `EVD-GRADE-02` | Assumptions cannot raise evidence tier | Free-text conditions map to declared constraint buckets; selectivity needs an accepted typed citation | Audit future provider/import promotion paths under the same rule | Free text and unreviewed citation never exceed declared/formal grade | None | `IMPLEMENTED_AND_VERIFIED` |

### 3.4 Stoichiometry, continuity, and route identity

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `STO-PRIM-01` | Canonical primitive signed stoichiometry drives identity and intensive physics | Primitive coefficient vector now drives feasibility/equilibrium/kinetics and scale-normalized selectivity; not yet every provider/digest/DAG/extent identity | Promote the canonicalizer to the single public reaction/evidence identity | Named scaling regressions pass; add provider/digest/DAG-wide invariance | None | `IN_PROGRESS` |
| `ROUTE-CONT-01` | Prior target must have positive net consumption in next step | Net-consumption check is implemented; equal spectator no longer connects steps | Preserve when roles/DAG IR are generalized | Equal amount on both sides fails continuity | `STO-PRIM-01` | `IMPLEMENTED_AND_VERIFIED` |
| `ROUTE-ID-01` | Structural route ID, not displayed equation, deduplicates alternatives | Rendered equation can collapse isomer-distinct routes | Use ordered generator/structure identity or DAG semantic digest | Same formula/different structure alternatives both survive | `ID-LAYER-01` | `TODO` |
| `DAG-FLOW-01` | Fan-out conserves intermediate quantities | Merge/dedup can mint usable intermediate copies | Add quantity-flow edges or block quantitative claims | One mole produced and two consumed yields deficit/blocker | Material quantities | `TODO` |

### 3.5 Terminal, feed, and material truth

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `TERM-POL-01` | One explicit terminal policy powers formula and route search | Formula inventory terminates; exact structural active stock now stops before expansion; commodities/available still use separate policy machinery | Implement shared `TerminalPolicy` with layer/match mode | Formula and structural target-terminal tests pass now; add equal material-policy fixtures | Shared request IR | `IN_PROGRESS` |
| `TERM-ELEM-01` | Element bucket packaging is explicit | “elements” can mean atom counts, standard-state species or stock | Serialize packaging policy in request/artifact | H/O atom buckets cannot be rendered as H2/O2 stock without declared conversion | `TERM-POL-01` | `TODO` |
| `TERM-COM-02` | Disabled/custom commodity inventory is authoritative everywhere | Current linear compile shortcut/termination/shopping respects the active inventory and `commodities=()` regression passes | Preserve through shared terminal/material policy and DAG work | `commodities=()` never uses global catalogue to stop/rank/shop | `TERM-POL-01` | `IMPLEMENTED_AND_VERIFIED` |
| `FEED-AMT-01` | Identity-only flags never invent quantity | Experimental CLI no longer maps identities to one mole and emits no finite ceiling without feed | Add explicit quantity+unit/assay input and optional symbolic ceiling separately | Identity-only poor-man fixture has no finite ceiling and no crash | `STOCK-01` desirable | `IMPLEMENTED_AND_VERIFIED` |
| `FEED-ERR-01` | Missing feed cannot abort an otherwise valid dossier | Route dossier now renders without a ceiling when feed is absent | Preserve structured diagnostic in shared response/JSON | Missing commodity amount preserves route dossier and non-internal exit status | `FEED-AMT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `STOCK-01` | `StockMaterial` represents mixture, assay, quantity, source and cost | `StockMaterial` + `MaterialComponent` + `FitnessVerdict` exist (`smartchem/experiment/stock.py`, `7d27e3c`): a typed material of components (each a fraction INTERVAL), a phase, and provenance, with a rigorous `satisfies(identity, min_assay)` interval gate (vinegar -> `INSUFFICIENT_ASSAY`, a straddling requirement -> `UNKNOWN_ASSAY`, an unknown fraction never passes). The full section 10.2 schema is now built too (`3ace975`): typed `StockQuantity` (positive-finite value+unit), a `CostObservation` that cannot be constructed unless dated AND sourced (section 10.4, no invented price), plus assay method, container/storage, opened/age, jurisdiction/availability, formulation notes and known impurities -- every field keyword-optional and defaulting to an honest UNKNOWN. The `CommodityReagent` -> `StockMaterial` source-lead bridge is now built too (`stock_material_from_commodity`, §10.1): a commodity maps to an UNKNOWN-fraction, phase-UNKNOWN material so it can never silently satisfy a pure requirement. Canonical-structure component keying and recompiler/shopping integration remain | Key components by canonical structure; wire the gate into route/shopping selection | Vinegar cannot satisfy pure acetic-acid input without assay/preprocessing | `ID-LAYER-01` | `IN_PROGRESS` |
| `SHOP-LEAF-02` | Shopping list is external, quantity-aware route input | Linear external-leaf identity logic is implemented and tested; quantities, DAG fan-out and purchased supplements are absent | Extend across DAGs, purchased supplements and quantity | Internally produced acid is absent now; purchased deficits must later include amount/unknown | `DAG-FLOW-01`, `STOCK-01` | `IN_PROGRESS` |

**Uptake record — StockMaterial first brick** (advances `STOCK-01` TODO -> IN_PROGRESS):

```text
ID:                  STOCK-01 (first brick)
commit:              7d27e3c
files:               smartchem/experiment/stock.py (new), smartchem/experiment/__init__.py, tests/test_stock.py
tests:               tests/test_stock.py (14 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2609 passed, 14 skipped, 1 xfailed (baseline 2595; +14). ruff clean; git diff --check clean.
built:               StockMaterial (typed material: components x fraction interval, phase, provenance),
                     MaterialComponent (fraction interval [lo,hi]; unknown -> [0,1]), FitnessVerdict, and the
                     satisfies(identity, min_assay) interval gate.
falsifier fixture:   vinegar (acetic acid 0.04-0.07 in water).satisfies("acetic acid", min_assay=0.99)
                     -> INSUFFICIENT_ASSAY; min_assay=0.05 -> UNKNOWN_ASSAY (straddles, must measure);
                     min_assay=0.03 -> SATISFIES. glacial acetic acid (0.99-1.0) vs 0.99 -> SATISFIES.
                     An unknown-fraction component never SATISFIES a real requirement.
residual limitations (the rest of STOCK-01, named in code and its row):
  1. First-brick schema only: quantity, container/storage, cost, jurisdiction/availability, impurity profile,
     assay method (the full section 10.2 fields) are absent.
  2. Components are keyed by a normalized name/formula string, not canonical structure (ID-LAYER-01).
  3. Not yet wired into the recompiler / shopping / affordability (SHOP-LEAF-02, COST-VEC-01), and there is no
     CommodityReagent -> StockMaterial source-lead bridge yet (a commodity match must map to UNKNOWN assay).
```

**Uptake record — StockMaterial full section 10.2 schema** (advances `STOCK-01`; the first-brick assay gate is
now backed by the full typed material record):

```text
ID:                  STOCK-01 (full schema)
commit:              3ace975
files:               smartchem/experiment/stock.py, smartchem/experiment/__init__.py, tests/test_stock.py
tests:               tests/test_stock.py::TestFullSchemaFields (10 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2632 passed, 14 skipped, 1 xfailed (with the depth-fix + recompile bricks on the tree). ruff
                     clean on every changed file; git diff --check clean.
built:               StockQuantity (positive-finite value+unit, value kept as an exact string), CostObservation
                     (amount+currency+date+source, region optional -- unconstructible without being dated AND
                     sourced), and the StockMaterial section 10.2 fields quantity / assay_method /
                     container_and_storage / opened_or_age_state / jurisdiction_and_availability / cost_observation
                     / formulation_notes[] / known_impurities[]. All keyword-optional, defaulting to UNKNOWN.
falsifier fixture:   CostObservation.of("1","USD","2026-01-01","   ") raises (a price must be sourced); a blank
                     amount/currency/date each raise; a negative/nonnumeric amount raises -- there is no path to a
                     fabricated price, the honest state is cost_observation=None -> render "cost: UNKNOWN".
                     StockQuantity.of("0"/"-5"/"inf"/"nan","g") each raise. Two materials differing only in the
                     declared quantity have distinct digests (quantity is semantic). The 6-positional-arg
                     first-brick form still constructs with every extra defaulting to UNKNOWN (backward compat).
residual limitations:
  1. MaterialComponent is still keyed by a normalized name/formula string; canonical-structure keying is
     ID-LAYER-01. The component fraction INTERVAL encodes its uncertainty; a separate point-value +/- uncertainty
     field was deliberately NOT added as a hollow null (it would churn every digest for no honesty gain).
  2. Still not wired into recompiler / shopping / affordability, and no CommodityReagent -> StockMaterial bridge
     yet -- the next two bricks (SHOP-LEAF-02, COST-VEC-01, and the source-lead bridge).
```

**Uptake record — CommodityReagent -> StockMaterial source-lead bridge** (advances `STOCK-01`; enforces the
section 10.1 rule that a commodity match is a lead, not a proven material):

```text
ID:                  STOCK-01 (commodity bridge)
commit:              92a80a0
files:               smartchem/experiment/stock.py, smartchem/experiment/__init__.py, tests/test_stock.py
tests:               tests/test_stock.py::TestCommodityBridge (4 new adversarial items)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2643 passed, 14 skipped, 1 xfailed (baseline 2632; +11 = the bridge + IR-serialize tests).
                     ruff clean on every changed file; git diff --check clean.
built:               stock_material_from_commodity(CommodityReagent) -> StockMaterial: the commodity identity
                     becomes ONE component of UNKNOWN fraction [0,1] in a phase-UNKNOWN material, with the
                     everyday-source note carried as provenance/formulation and explicitly labelled a curated
                     editorial obtainability judgment, not an assay.
falsifier fixture:   stock_material_from_commodity(<acetic acid commodity>).satisfies("acetic acid",
                     min_assay=0.99) -> UNKNOWN_ASSAY (and min_assay=0.50 -> UNKNOWN_ASSAY) -- a commodity match
                     NEVER stands in for a proven pure material (section 10.1); quantity and cost stay None
                     (UNKNOWN), never invented from the commodity record. Works on the real COMMODITY_REAGENTS
                     registry; rejects a non-CommodityReagent.
residual limitations:
  1. Still keyed by the commodity name string (canonical-structure keying is ID-LAYER-01).
  2. Not yet consumed by the shopping list / affordability ranking (SHOP-LEAF-02, COST-VEC-01, blocked on the
     DAG quantity-flow accounting DAG-FLOW-01).
```

### 3.6 Readiness and safety

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `READY-TIER-01` | Every current route dossier states its readiness | `ProcedureReadiness` exists; current drafter deliberately emits only `FORMAL_CANDIDATE` and cannot self-promote | Preserve this floor; `ProcedureIR` must govern any future higher tier | Missing operational fields produce `FORMAL_CANDIDATE`, never `BENCH_DRAFT` | Procedure IR for future promotion | `IMPLEMENTED_AND_VERIFIED` |
| `READY-NAME-01` | Sparse output is called route dossier, not runnable/full procedure | Canonical API is `RouteDossier`/`draft_route_dossier`; renderer/docs use formal-candidate language. `DraftedProcedure`/`draft_procedure` and `Composability.is_runnable` remain explicit deprecated aliases | Remove compatibility aliases in a future breaking release | Canonical type/render carry readiness boundary and unresolved checklist | `READY-TIER-01` | `IMPLEMENTED_AND_VERIFIED` |
| `PROC-IR-01` | Typed procedure operations underlie any bench draft | Essential scale/addition/quench/workup/purification/analysis/waste fields absent | Add `ProcedureIR` with completeness validator | Delete any required field from fixture -> lower tier or construction failure | `STOCK-01`, hazard work | `TODO` |
| `SAFE-AUTH-01` | No emitted `PROCEED_UNATTENDED` or automatic safety authorization | Output no longer emits the label; enum member remains for compatibility only | Deprecate/remove compatibility symbol later without restoring output authority | Missing hazard record cannot yield authorization; rendered label absent | None | `IMPLEMENTED_AND_VERIFIED` |
| `SAFE-HEAT-02` | Open flame never inferred from temperature alone | Controlled electric heat is used; known flammability vetoes flame | Preserve across future equipment providers | Hot unknown/flammable medium has no flame recommendation | None | `IMPLEMENTED_AND_VERIFIED` |
| `SAFE-HAZ-01` | Missing hazard/stability data are visible blockers/unknowns | Registry missing 7/15 hazard and 13/15 stability records | Add coverage report and missing-data semantics; source records | Every commodity has positive record or explicit unknown; no unknown clears a route | `STOCK-01` | `TODO` |
| `SAFE-PROC-01` | Safety considers quantity, concentration, conditions, incompatibility, off-gas and waste | Current checks are species/free-text heuristics | Typed process hazard inputs and qualified-review gate | Same species at different concentration/scale can yield different scoped assessment | `PROC-IR-01`, `STOCK-01` | `TODO` |

### 3.7 CLI and service

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `SVC-REQ-01` | One typed request/service powers chemical commands | First brick landed (`67b8ae4`): `smartchem/service.py` provides the typed `CompilationRequest`/`CompilationResponse`, an alias-independent `semantic_digest` (equal flags across aliases → equal search identity → equal result), per-field `origin` provenance, `run_compilation` + the section 14.4 exit map, and canonical serialization; the two synthesis aliases still build their own requests (routing the live CLI argv through the service is `CLI-CAN-01`) | Implement `CompilationRequest/Response`; route aliases through it | Equal flags across aliases produce equal request/result digests | `IR-CHEM-01` | `IN_PROGRESS` |
| `CLI-CAN-01` | Canonical `decompile` and `recompile`; legacy aliases share defaults | Canonical `recompile` verb landed (`df93b8c`), routed through the typed service (`run_compilation`); `decompile` gained `--json`/`--emit-request` through the same service; the legacy `compile` alias now builds the SAME typed request from the ONE shared builder (no divergent defaults) + prints a deprecation notice, so `compile … --emit-request` and `recompile … --emit-request` are byte-identical. `synthesize`'s deeper uptake (its `--max-temp`/`--max-pressure` constraints + `--offline` provider levers) is the named follow-on `CLI-CAN-02` | Add canonical verbs; deprecate aliases without duplicate logic | Command matrix gives equal request JSON — DONE (7-row grid, `--emit-request` byte-identical) | `SVC-REQ-01` | `IN_PROGRESS` |
| `CLI-NAME-01` | Normal names accepted without private formatting | Registered offline names and explicit `name:`/`smiles:` prefixes work in synthesis CLIs; InChI/formula/echo/shared parser are incomplete | Finish unified identity parser and echo receipt | Registered-name and SMILES tests pass; add InChI/formula/ambiguity matrix | `ID-PARSE-01` | `IN_PROGRESS` |
| `CLI-EXIT-01` | Stable exit codes separate route/no-route/partial/refusal/invalid/internal | The top-level guarded service is now BUILT: `main()` wraps command dispatch and maps ANY escaping exception to exit 70 (`ERROR_INTERNAL`) with a concise stderr line — never a raw traceback, never Python's default exit 1; argparse's own `SystemExit` (a `BaseException`, not `Exception`) passes through, so `--help` stays 0 and a bad flag stays 2. The full 0/2/3/4/5 table is observed both in-process AND through a real `python -m smartchem` subprocess, plus the controlled internal-error fixture for 70 (`tests/test_cli_exit.py`). Acceptance MET. Central error mapping across every format/path is `CLI-ERR-01`; the decompile human path still returns 0/2/4 by its own status | Central error mapping (`CLI-ERR-01`) | Codes 0/2/3/4/5 observed; controlled internal-error fixture for 70 — **DONE** (`tests/test_cli_exit.py`) | `SRCH-RCT-01`, `SVC-REQ-01` | `IN_PROGRESS` |
| `CLI-ERR-01` | Invalid chemistry/numeric input yields domain error without traceback | **One central error-classification authority BUILT.** `cli.py` `_domain_exit` maps a raised domain exception to its section-14.4 code — a chemistry-MODEL-boundary refusal (`ScissionError`/`IdentityUnsupportedError`, checked FIRST since both are `ValueError` subclasses) → exit 5; an INVALID input (`IdentityParseError`/`DecompilerError`/`SmilesError`/`ValueError`/`TypeError`) → exit 2, concise stderr, NEVER a traceback; an exception in NEITHER family is RE-RAISED, so a genuine internal bug reaches `main()`'s exit-70 guard and is never laundered into a domain 2/5. `recompile`/`decompile`/`compile` all route through it (no per-command hand-rolled mapping). A `--input-kind`{auto,name,smiles,inchi,formula,target-file} flag surfaces the section-14.2 kinds; inchi/formula/target-file are a loud INVALID_INPUT (exit 2) on the human AND `--json` path of BOTH `recompile` and `compile` (the `compile`-human `--input-kind`-bypass red-team finding is fixed), never a mis-parse. REMAINING: full ID-PARSE-01 resolution of those kinds; a nonfinite-float constraint matrix awaits the synthesize constraint uptake (CLI-CAN-02) | Full ID-PARSE-01 kinds; nonfinite-float constraints (CLI-CAN-02) | Invalid/refusal probes concise + no traceback; InChI/formula/target-file subprocess matrix exit 2 — **DONE** (`tests/test_cli_err.py`) | `ID-PARSE-01`, constraints | `IN_PROGRESS` |
| `CLI-VERS-01` | Package installs `smartchem`, supports `--version`, exposes consistent `__version__` | Entry point, package metadata and `__version__` report `0.5.0a1` | Preserve single-source consistency in release packaging | Targeted script/module/version tests pass | None | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-JSON-01` | Stable JSON contains request, identity, receipt, tier, blockers and route IDs | Landed (`67b4715`): `recompile`/`decompile` `--json` emit the versioned response schema; `response_schema()` is a first-class versioned descriptor of the SHAPE, cross-checked against a real payload so a golden cannot certify a drifted schema; golden fixtures (schema + 6 command responses) + an idempotent regen script; a human↔JSON agreement matrix + `response_semantic_fields()` prove neither view drops or contradicts a semantic field. `ranked_route_dossiers`/`affordability_frontier` still empty (READY-TIER/COST-VEC); the receipt is a digest, not the full object | Add versioned serializer/schema and golden fixtures | Human and JSON agree on all semantic fields — DONE (agreement matrix over recompile + decompile, incl. the SMILES-reduction BLOCKER carried identically to both views) | `SVC-REQ-01`, `READY-TIER-01` | `IN_PROGRESS` |

**Uptake record — typed compilation service, first brick** (`SVC-REQ-01` `TODO` → `IN_PROGRESS`; the lever the
CLI rows `CLI-CAN`/`CLI-JSON`/`CLI-EXIT`/`CLI-ERR` hang off):

```text
ID:                  SVC-REQ-01 (first brick -- the typed request/response + digest law + producer)
commit:              67b8ae4
files:               smartchem/service.py (new), smartchem/identity_parse.py (new), smartchem/cli.py,
                     tests/test_service.py (new)
tests:               tests/test_service.py -- TestAliasEquality, TestOrigins, TestOutcomes, TestCoherenceGuard,
                     TestValidation, TestSerialization, TestIdentityParse, TestRedTeamRegressions (81 total,
                     counting parametrize)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2848 passed, 14 skipped, 1 xfailed (baseline 2767; +81). ruff clean on every changed file;
                     git diff --check clean.
built:               smartchem/service.py -- the typed CompilationRequest (section 13.1) and CompilationResponse
                     (section 13.2). The load-bearing law is a TWO-DIGEST split: `semantic_digest` is the
                     alias-independent SEARCH identity (it excludes the per-field `origins` provenance and the
                     `output_policy` display choice), and the inherited `digest` is the full identity including
                     provenance. build_recompile_request/build_decompile_request record a `FieldOrigin`
                     (EXPLICIT/DEFAULT) per knob, so a default is a VISIBLE field, never an invisible command branch
                     (section 13.1). run_compilation delegates to the existing IR producers
                     (recompile_to_ir/decompile_to_ir), classifies a TOTAL ResponseOutcome, and maps it to the
                     section 14.4 exit codes (0/2/3/4/5; 70 is reserved for the top-level guarded service). The
                     CompilationResponse coherence guard reads only STRUCTURED facts (complete_within_bounds,
                     candidate_count, standard_status) -- never diagnostic text -- so a partial can never surface as
                     complete and a no-route claim rests on a genuinely complete+empty search (section 8.3).
                     smartchem/identity_parse.py -- the ONE shared target parser (resolve_target/InputKind/
                     IdentityParseError); cli._parse_molecule now delegates to it, so the CLI and the service cannot
                     drift on the same string (the exact failure this brick exists to prevent).
falsifier fixture:   a `compile`-style request (defaults grammar/kind) and a `recompile`-style request (states them,
                     equal to the defaults) with equal flags -> equal semantic_digest AND equal run_compilation
                     result_digest, but DIFFERENT origins/full-digest; two requests differing only in output_policy
                     -> equal semantic_digest; changing any one semantic field -> different semantic_digest (a
                     12-case tripwire). run_compilation: methyl acetate (smiles:CC(=O)OC) -> ROUTES_FOUND/exit 0;
                     benzene, commodities off -> NO_ROUTE_COMPLETE/exit 3; paracetamol, max_depth=2 ->
                     INCOMPLETE/exit 4; ethanol (a commodity) -> TARGET_ALREADY_AVAILABLE/exit 0; an unknown name ->
                     INVALID_INPUT/exit 2 (REFUSED_INVALID_REQUEST); H2O decompile -> ROUTES_FOUND/exit 0. Request
                     and response serialize/deserialize with a stable digest; a tampered payload (negative bound,
                     unknown enum, contradictory standard_status, off-operation bound-names) is REFUSED on read.
red-team:            3 attack bearings + 10 verify agents (workflow, 13 agents, 557k subagent tokens). 9 CONFIRMED
                     + 1 PLAUSIBLE, 0 refuted -- ALL folded in before this commit landed: (F5, MEDIUM) _run_decompile
                     silently discarded a declared non-formula input_kind -> a formula-parseable NAME/SMILES could
                     ship a WRONG species at exit 0; now fails CLOSED (INVALID_INPUT) on any kind but AUTO/FORMULA.
                     (F3, MEDIUM) the response standard_status was never cross-checked against its wrapped IR, so a
                     hand-built/deserialized response could smuggle an engine-impossible stop reason
                     (INCOMPLETE_CANDIDATE_LIMIT) past the family checks; now standard_status MUST equal the IR's.
                     (F6, MEDIUM) operation<->search-bound-name coherence was unchecked -> a crafted RECOMPILE
                     payload carrying DECOMPILE bound-names deserialized and then crashed run_compilation with a raw
                     KeyError; now refused at construction (with terminal-mode and direction-field coherence too,
                     closing F2's spurious recompile split). (F4, LOW) a decompile target that is itself a declared
                     bucket was miscoded NO_ROUTE_COMPLETE (exit 3, a section 8.3 claim of absence) with an empty
                     diagnostic; now TARGET_ALREADY_AVAILABLE (exit 0), keyed by canonical FORMULA identity.
                     (F7, LOW) _parse_smiles dropped the "smiles:" prefix from its error string vs the old helper;
                     restored to message-identical. (F1/F8/PLAUSIBLE, LOW) the semantic_digest docstrings asserted a
                     false biconditional ("exactly the fields that change the search, and nothing else") while the
                     digest is a section-4.1 semantic SUPERSET (it hashes not-yet-wired policy placeholders and
                     input_kind on a formula descent); reworded to the TRUE one-way law -- equal digest => same
                     search -- with the over-inclusion named as safe (it can only SPLIT, never MERGE two searches).
                     (F9, LOW) the CompilationResponse docstring said search_receipt "reads through" to the IR, but
                     only its DIGEST is exposed; reworded. Each fix is pinned by a test in TestRedTeamRegressions.
residual limitations / next bricks:
  1. The live CLI argv is NOT yet routed through the service; `compile`/`synthesize` still build their own requests.
     Routing them (and adding the canonical `decompile`/`recompile` verbs) is CLI-CAN-01, and the versioned JSON
     view is CLI-JSON-01 -- both now unblocked by this service.
  2. run_compilation reads the target as typed (raw target_input + input_kind); collapsing `name:X` and `X` to one
     normalised identity inside the digest is ID-PARSE-01, as is resolving INCHI/FORMULA/name-normalised decompile
     targets. The service decompile path currently reads the target as FORMULA text only.
  3. ranked_route_dossiers and affordability_frontier are present-and-empty (READY-TIER-01 / COST-VEC-01); the
     section 13.2 search_receipt is exposed as a digest, not the full receipt object. Quantitative StockMaterial
     binding is STOCK-01. The exit-code 70 path awaits the top-level guarded service.

**Uptake record — canonical CLI verbs routed through the typed service** (`CLI-CAN-01` `TODO` → `IN_PROGRESS`;
the first row the SVC-REQ-01 lever actually pulls):

```text
ID:                  CLI-CAN-01 (canonical recompile/decompile verbs + alias-equal request construction)
commit:              df93b8c
files:               smartchem/cli.py, smartchem/service.py, tests/test_cli_canonical.py (new)
tests:               tests/test_cli_canonical.py -- TestCommandMatrixEqualRequestJson, TestCliOriginLaw,
                     TestRecompileOutcomes, TestRecompileJson, TestQuietNeverHidesABlocker,
                     TestCrossEngineExitCoherence, TestDecompileServiceViews, TestDeprecationAndUsage,
                     TestRedTeamRegressions (49 total, counting parametrize)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2895 passed, 14 skipped, 1 xfailed (baseline 2848; +47). ruff clean on every changed file;
                     git diff --check clean.
built:               the canonical `recompile` verb, routed through run_compilation (SVC-REQ-01's service). ONE
                     shared argv->request builder (_recompile_request_from_args) feeds compile AND recompile from
                     the service's single default table, so equal flags -> byte-identical requests (standard 14.1:
                     a legacy alias MUST construct the same typed request and MUST NOT keep divergent defaults).
                     recompile renders the typed response (retaining status/receipt-digest/identity-losses/candidate
                     IDs), and gains --json (versioned response schema), --emit-request (a DRY request echo -- no
                     search), --quiet (drops narrative but NEVER a blocker in a successful-looking result, 14.3) and
                     the section 14.4 exit codes 0/2/3/4/5 from one service authority. `compile` keeps its rich
                     graded dossier (deprecated one cycle) but sources its request from the shared builder + prints
                     a stderr deprecation notice. `decompile` gained --json/--emit-request through the service, with
                     example_inventory()'s Formula OBJECTS normalised to canonical formula text (the typed request
                     keys on text). Both recompile-engines (the legacy graded compile_synthesis and the service's
                     recompile_to_ir) wrap the SAME search_routes, so their exit codes provably agree -- a
                     cross-engine coherence tripwire guards that seam.
acceptance:          the command matrix -- compile vs recompile with equal flags -> byte-identical --emit-request
                     JSON across a 7-row grid; a differing semantic flag SPLITS the request; a default-vs-explicit
                     equal value shares semantic_digest but differs in origins/full-digest (the section-13.1 law at
                     the CLI surface); cross-engine exit coherence (compile human vs recompile --json) across the
                     outcome grid.
red-team:            3 attack bearings + 6 verify agents (workflow, 9 agents, 788k subagent tokens). 4 CONFIRMED
                     real (2 refuted correctly: the SMILES->formula loss is the documented IR-LOSS-01 TODO; an
                     --emit-request exit 0 is a request-echo, not a false search success) -- ALL folded before this
                     commit: (CLI-CAN-01-B, HIGH) an empty `--reagents` list emitted an IDENTICAL request across
                     compile/recompile but executed two DIFFERENT searches -- compile silently injected water,
                     recompile searched () -- the exact "invisible default branch" (section 13.1) this brick exists
                     to kill; fixed so the CLI coerces an empty pool to the VISIBLE water default (both aliases
                     agree, and the emitted request shows the water). (CLI-CAN-01-A, MEDIUM) that same empty pool
                     crashed recompile with a raw TypeError to exit 1 (no section-14.4 code), because _run_recompile
                     caught only ScissionError; fixed so the service refuses a genuinely-empty reagent pool as exit-2
                     INVALID_INPUT (defense-in-depth for programmatic callers). (F1 + DEC-ELEM-EXIT-DIVERGE, HIGH) a
                     bare element (a universal terminal bucket the decompiler bottoms out at, absent from the DECLARED
                     inventory) decompiled to human exit 0 (already a bucket) but service --json exit 3
                     (NO_ROUTE_COMPLETE) -- a confident section-8.3 claim of absence over elemental oxygen, and a
                     drift the routing promises cannot happen; fixed so a COMPLETE decompile with zero edges is
                     TARGET_ALREADY_AVAILABLE (exit 0), matching the human path. Each fix is pinned in
                     TestRedTeamRegressions.
residual / follow-on: synthesize's full uptake is CLI-CAN-02 (its constraints §11 + provider §9 levers). recompile's
                     human render is the typed response; the rich graded compile_synthesis dossier stays under legacy
                     `compile` one cycle -- unifying run_compilation to RETURN the dossier (so there is literally one
                     calculation, not two views over the same search_routes) is future. The exit-70 internal path
                     still awaits the top-level guarded service. --json is the response schema, but
                     ranked_route_dossiers/affordability_frontier remain empty (READY-TIER-01 / COST-VEC-01). The
                     target still enters the digest as typed (ID-PARSE-01).
```

**Uptake record — versioned --json schema + the layered identity model** (`CLI-JSON-01` and `ID-LAYER-01`
`TODO` → `IN_PROGRESS`; two bricks that meet at the decompile agreement surface, landed together in `67b4715`):

```text
ID:                  CLI-JSON-01 (versioned --json response schema) + ID-LAYER-01 first brick (layered identity)
commit:              67b4715
files:               smartchem/identity.py (new), smartchem/service.py, smartchem/compilation_ir.py, smartchem/cli.py,
                     tests/test_identity.py (new), tests/test_cli_json.py (new), tests/regen_cli_json.py (new),
                     tests/fixtures/cli_json/*.json (new: schema descriptor + 6 command responses)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2942 passed, 14 skipped, 1 xfailed (baseline 2895; +47). ruff clean on every changed file.
CLI-JSON-01:         response_schema() -- a versioned descriptor of the --json response SHAPE (14.3 "stable versioned
                     response schema"), cross-checked field-for-field against a REAL response_to_payload output so a
                     golden can never certify a schema that drifted from what is emitted. response_semantic_fields()
                     -- the projection both the JSON and the human render must agree on (identity/receipt/tier/
                     blockers/route-IDs + outcome/exit/status). Golden fixtures compared parsed-equal + an idempotent
                     regen script (tests/regen_cli_json.py). The acceptance ("human and JSON agree on all semantic
                     fields") is a matrix over recompile AND decompile: outcome/exit agree, the human render surfaces
                     every JSON route ID (as a prefix) and every identity loss, and neither view silently drops a field.
ID-LAYER-01:         smartchem/identity.py -- the section 5.1 MatchLayer lattice + refines(); LayeredIdentity with
                     per-layer digests byte-congruent with the pipeline's identities (does NOT fork a new identity),
                     FORMULA carrying total charge; same_identity_at() = section 5.4 layer-relative equality returning
                     an honest None at any layer the current Molecule model cannot perceive (CONFIGURATION/ISOTOPIC),
                     so a formula match is never promoted to a structure match. IdentityLoss (section 5.3 record, the
                     one IR-LOSS-01 will carry) + formula_reduction_loss. The section 5.4 probe is mechanized:
                     ethanol vs dimethyl ether agree at FORMULA, differ at CONSTITUTION, UNKNOWN above.
acceptance:          section 5.4 -- same-formula isomers share formula balance, distinct wherever a structural claim
                     is made, unperceived layers UNKNOWN not fabricated; CLI-JSON-01 -- human and JSON agree.
red-team:            3 attack bearings + 6 verify agents (workflow, 9 agents, 617k subagent tokens). The verify phase
                     mis-fired on an authoring bug in my OWN workflow script (an unsubstituted prompt template -- the
                     verifiers correctly refused to invent findings), so the 6 attack findings were self-reproduced
                     and folded before this commit: (HIGH) decompile --smiles dropped its BLOCKER identity loss from
                     --json (identity_losses []) -- human and JSON disagreed and structure was silently discarded on
                     the machine path (5.3/5.4); fixed -- the service resolves the SMILES and records the loss into
                     the IR, both views carrying the identical summary() string. (HIGH) the FORMULA layer dropped
                     total charge (matched [NH4+] to neutral NH4, against its own "counts + total charge" definition);
                     fixed with Formula.of(counts, charge). (MEDIUM) the legacy decompile human render omitted the
                     outcome + section 8.2 status the --json view carries; fixed -- both surfaced from the same
                     service request. (MEDIUM) aromatic-vs-Kekule naphthalene distinct at CONSTITUTION -- an inherited
                     shared-canonicalizer limitation, now named honestly in the docstrings rather than over-claimed
                     past. (LOW) a BLOCKER IdentityLoss with empty affected_claims blocked nothing (the recurring
                     vacuous-guard fail-open); fixed -- a BLOCKER must name >=1 affected claim; also folded
                     kinetics+hazard into the loss (the four evidence classes section 5.3 names). Each pinned in
                     TestRedTeamRegressions.
residual / follow-on: ID-LAYER-02 (MatchLayer into the service IdentityPolicy so a request declares its comparison
                     layer); stereo/isotope PERCEPTION (CONFIGURATION/ISOTOPIC are declared but return UNKNOWN);
                     salt/mixture COMPONENT identity (material model, section 10); typed IdentityLoss records INSIDE
                     the IR (IR-LOSS-01; today the IR carries the loss as a string). CLI-JSON-01: the receipt is a
                     digest not the full object; ranked_route_dossiers/affordability_frontier stay empty (READY-TIER/
                     COST-VEC); the decompile human edge-list and its --json view remain two calculations over the
                     same search (the two-view seam named for recompile).
```

**Uptake record — first-class IR losses + the exit-code table + MatchLayer in the IdentityPolicy** (`IR-LOSS-01`
`TODO` → `IN_PROGRESS`; `CLI-EXIT-01` advanced, acceptance MET; `ID-LAYER-02`, the ID-LAYER-01 follow-on, BUILT):

```text
ID:                  IR-LOSS-01 (typed loss records inside the IR) + CLI-EXIT-01 (section 14.4 table + exit-70
                     guard) + ID-LAYER-02 (MatchLayer wired into the service IdentityPolicy)
files:               smartchem/identity.py, smartchem/compilation_ir.py, smartchem/service.py, smartchem/cli.py,
                     tests/test_ir_loss.py (new), tests/test_cli_exit.py (new), tests/test_identity.py,
                     tests/test_cli_json.py, tests/test_compilation_ir.py, tests/fixtures/cli_json/*.json (regen)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider tests/
result:              2993 passed, 14 skipped, 1 xfailed (baseline 2942; +51). ruff clean on every changed file.
IR-LOSS-01:          ChemicalCompilationIR.identity_losses is now a tuple of first-class typed section-5.3
                     IdentityLoss records, not summary strings -- a genuine serialized-shape change (array[str] ->
                     array[object]), so the IR schema bumped v1alpha2 -> v1alpha3. A machine consumer reads
                     severity/affected_claims STRUCTURALLY; the loss's semantic content now RIDES the IR digest (a
                     WARNING and a BLOCKER over the same feature are different IRs). ir_to_payload emits the
                     structured record; ir_from_payload re-validates it, so a tampered loss (the vacuous BLOCKER
                     that names no claim) is refused on read. The human/JSON one-line agreement (CLI-JSON-01) is
                     preserved via identity_loss_summaries -- the derived summary() the human render prints and the
                     descriptor's new identity_loss_fields cross-check. Acceptance (CCO vs COC): the two isomers'
                     SMILES decompilations share ONE formula target but stay distinct (each input survives in its
                     loss record) and each announces the collapse as a BLOCKER (test_ir_loss.py, 21 tests).
CLI-EXIT-01:         the top-level guarded service: main() wraps command dispatch and maps ANY escaping exception
                     to exit 70 (ERROR_INTERNAL) with a concise stderr line -- never a raw traceback, never Python's
                     default exit 1. argparse's own SystemExit (a BaseException, not Exception) passes through, so
                     --help stays 0 and a bad flag stays 2. tests/test_cli_exit.py observes the FULL section-14.4
                     table 0/2/3/4/5 both in-process AND through a real `python -m smartchem` subprocess, plus the
                     controlled internal-error fixture for 70 (a monkeypatched engine fault). Acceptance MET.
ID-LAYER-02:         IdentityPolicy carries a match_layer (section 5.1 MatchLayer), part of the semantic_digest, so
                     a request DECLARES its comparison layer. run_compilation ENFORCES it: the engine matches only
                     at the layer it can honestly honor (recompile CONSTITUTION, decompile FORMULA); a finer,
                     unperceived layer (CONFIGURATION/ISOTOPIC) OR the coarser FORMULA for a structure search
                     (section 5.4 / gate G3) is a REFUSED response (exit 5, REFUSED_IDENTITY_UNSUPPORTED) -- never a
                     silent match at the wrong layer. A `--match-layer` CLI flag declares it end to end; the human
                     render surfaces it. The request schema bumped v1alpha1 -> v1alpha2 for the new field.
red-team:            3 attack bearings (one per brick) + per-finding adversarial verify (workflow wwac5sp63, 10
                     agents, 791k subagent tokens): 7 findings, 5 CONFIRMED and folded before this commit (each
                     self-reproduced first), 2 correctly REFUTED. (MEDIUM) CLI-EXIT-01 laundered a routine broken
                     pipe (`| head`/`| less` close) into exit 70 + a FALSE "ERROR_INTERNAL" -- a SIGPIPE is not an
                     internal software error; fixed -- BrokenPipeError is caught specifically -> exit 141 (the
                     SIGPIPE convention), stdout redirected to devnull to silence the shutdown flush, no false
                     message. (MEDIUM) ID-LAYER-02 refused a decompile declaring CONSTITUTION with a FALSE reason
                     ("stereo/isotope perception is unbuilt") -- constitution IS perceivable (it is the
                     recompile-honored layer); fixed -- the finer-refusal reason now distinguishes a
                     genuinely-unperceived layer (CONFIGURATION/ISOTOPIC) from a perceivable layer this engine does
                     not build (CONSTITUTION on a formula descent), the latter citing section 5.4 / "no structure"
                     honestly. (LOW) CLI-EXIT-01's `from .service import EXIT_INTERNAL` sat OUTSIDE the try, so a
                     broken .service import escaped as a raw traceback / exit 1 -- the exact class the guard exists
                     for; fixed -- the exit-70 code is a LOCAL literal `_EXIT_INTERNAL`, test-pinned equal to
                     service.EXIT_INTERNAL. (LOW) IdentityLoss.summary() docstring falsely claimed the summary is
                     "carried verbatim into the machine identity_losses field" (now structured records); fixed --
                     it names the derived identity_loss_summaries surface (the sibling cli.py comment tightened
                     too). (LOW) the IR-CHEM-01 manifest row still listed first-class loss records as remaining,
                     contradicting the updated IR-LOSS-01 row; fixed -- the cross-reference is refreshed. The 2
                     REFUTED: a cli.py comment phrasing nit with a defensible reading, and "decompile with the
                     IdentityPolicy default CONSTITUTION refuses" being the INTENDED, tested fail-closed behavior
                     (re-defaulting an explicitly-declared layer would be the section-5.3 silent downgrade the
                     brick forbids). Each fold pinned in a regression test.
residual / follow-on: IR-LOSS-01 -- the evidence CONSUMERS (EVD-KEY-01) do not yet check loss.blocks() to refuse a
                     dependent sourced claim; the IR carries and exposes the blocker, the enforcement in providers
                     is EVD-KEY-01. CLI-EXIT-01 -- central error mapping across every format/path is CLI-ERR-01;
                     the decompile human path still returns 0/2/4 by its own status. ID-LAYER-02 -- the honored
                     layer is a single fixed value per operation because stereo/isotope PERCEPTION is unbuilt
                     (ID-STEREO-01); when it lands, CONFIGURATION/ISOTOPIC become honorable and the flag works
                     without a code change.
```

**Uptake record — stereo/isotope/charge loss detection + the loss-consumer gate + central CLI error mapping**
(`ID-STEREO-01` `TODO` → `IN_PROGRESS`; `EVD-KEY-01` consumer gate BUILT + threaded to production; `CLI-ERR-01`
central authority BUILT). NB: this CORRECTS the forward projection two records above — ID-STEREO-01 built
DETECTION, not PERCEPTION, so `--match-layer configuration` does NOT become honorable and REMAINS refused:

```text
ID:                  ID-STEREO-01 (parse-boundary feature detection + typed section-5.3 blockers) + EVD-KEY-01
                     (the loss.blocks() consumer gate, threaded end-to-end) + CLI-ERR-01 (one central error map)
files:               smartchem/smiles.py, smartchem/identity.py, smartchem/identity_parse.py, smartchem/service.py,
                     smartchem/compilation_ir.py, smartchem/experiment/{selectivity,kinetics,classify,drafter,
                     compile}.py, smartchem/decompiler_conditions.py, smartchem/cli.py, tests/test_id_stereo.py
                     (new), tests/test_evd_key.py (new), tests/test_cli_err.py (new)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3073 passed, 14 skipped, 1 xfailed (baseline 2998; +75). ruff clean on every changed file;
                     git diff --check clean.
ID-STEREO-01:        smiles.py parse_smiles_features CAPTURES the isotope labels, tetrahedral (@/@@) and double-bond
                     (/ \) stereochemistry and net-neutral local-charge separation a SMILES declares but the
                     constitution-only Molecule drops (parse_smiles returns the byte-identical Molecule; the feature
                     door shares its Kekulé path). identity.py stereo_loss/isotope_loss/local_charge_loss/
                     representation_losses_for lower each PRESENT feature to a typed section-5.3 BLOCKER (a
                     flat/unlabelled/neutral input yields (), never a vacuous blanket). Wired on BOTH the recompile
                     path (constitution kept -> the losses are the only signal, via recompile_to_ir's new
                     identity_losses param) and the decompile path (beside formula_reduction_loss); the decompile CLI
                     render prints them from the response so human == JSON. Enantiomer/isotopologue/zwitterion no
                     longer SILENTLY collide; a disconnected salt stays a LOUD refusal. HONEST BOUNDARY: this is the
                     "record blocker" arm, NOT PERCEPTION -- --match-layer configuration REMAINS refused (a sound
                     CONFIGURATION/ISOTOPIC digest needs canonical CIP / positioned-isotopologue keys + an
                     atom-coloured Molecule, deferred, never faked).
EVD-KEY-01:          identity.py blocking_losses/is_blocked/blocked_claim_classes are the consumer primitive; the
                     sourced-evidence providers (selectivity_of_step/verify_selectivity, reaction_conditions/
                     assembly_conditions, kinetics_of_step/verify_kinetics) gate on losses= and downgrade a SOURCED
                     verdict to a loud UNKNOWN under a matching BLOCKER -- claim-class-PRECISE and NON-VACUOUS.
                     THREADED END-TO-END through compile_synthesis -> rank_routes/fit_route, the public classify_step/
                     route/dag, and draft_route_dossier, with the compile CLI supplying the target's losses, so a
                     stereo/isotope target's sourced selectivity/kinetics verdict is gated on a REAL compile/classify
                     run (proven in test_evd_key.py::TestProductionPathBite), not only under direct injection.
CLI-ERR-01:          cli.py _domain_exit is the ONE classifier: a MODEL-boundary refusal (ScissionError/
                     IdentityUnsupportedError, checked FIRST as they are ValueError subclasses) -> exit 5; an INVALID
                     input (IdentityParseError/DecompilerError/SmilesError/ValueError/TypeError) -> exit 2, concise,
                     no traceback; anything else RE-RAISES to main()'s exit-70 guard (never laundered into 2/5).
                     recompile/decompile/compile all route through it. A --input-kind flag surfaces the section-14.2
                     kinds; inchi/formula/target-file are a loud exit-2 on human AND --json of both verbs.
red-team:            3 attack bearings + per-finding adversarial verify (workflow w7dzso0xz, 9 agents, 800k subagent
                     tokens): 6 findings, ALL 6 CONFIRMED, 0 refuted -- every one folded before this commit, each
                     self-reproduced first. (HIGH) EVD-KEY-DEADSWITCH-01 + (MED) ID-STEREO-EVD-UNWIRED: the gate was
                     a DEAD SWITCH -- no production caller threaded losses, so a sourced verdict still shipped next to
                     a blocker in a real compile run, while the in-code docstrings CLAIMED the bite was delivered (the
                     iron-rule "faithful not plausible" violation); FIXED by threading losses end-to-end through
                     kinetics/classify/drafter/compile + the compile CLI, so the bite reaches production (regression:
                     TestProductionPathBite). (HIGH) CLIERR-COMPILE-INPUTKIND-BYPASS: the compile HUMAN path ignored
                     --input-kind and AUTO-mis-parsed an inchi target to a confident exit-0 dossier while --json/
                     recompile gave exit 2; FIXED -- compile now resolves the target honouring request.input_kind ->
                     exit 2, human == json. (MED) EVD-KEY-CLASSGAP-02: verify_kinetics emitted KNOWN_SOURCED
                     unconditionally so an isotope/stereo blocker's "kinetics" class was ungated; FIXED -- the
                     kinetics consumer is now gated. The finding also noted stereo_loss listed "hazard" while a hazard
                     consumer (verify_handling) exists ungated; FIXED by ACCURACY -- "hazard" removed from stereo_loss
                     (the modeled handling hazard is a CONSTITUTION-level physical class two enantiomers share, so a
                     dropped stereocentre does not change it; enantiomer-specific toxicology is a deferred
                     configuration-keyed model, not faked). (MED) ID-STEREO-LOCALCHARGE-DOCSTRING: the
                     has_local_charge_structure docstring falsely claimed a net-charged species never reaches the
                     record and that the decompiler refuses charged targets as REFUSED_IDENTITY_UNSUPPORTED (decompile
                     does not refuse charged targets; the recompile refusal carries standard_status None); FIXED --
                     rewritten to the true two-case predicate. (LOW) ID-STEREO-DBSTEREO-FALSEPOS: the / \ scan is a
                     text-presence check that over-flags a redundant directional bond; ACKNOWLEDGED + DOCUMENTED as
                     intentional fail-CLOSED conservatism (never misses a declared marker; real geometric-isomer
                     perception deferred) + pinned by test.
residual / follow-on: EVD-KEY-01 -- the full ReactionEvidenceKey (structure+stoich+direction+context+source unified)
                     and the decompiler_review conditions provider remain to migrate. ID-STEREO-01 -- sound
                     CONFIGURATION/ISOTOPIC PERCEPTION (canonical keys + atom-coloured Molecule) is the deferred
                     piece; --match-layer configuration stays refused until then. CLI-ERR-01 -- full ID-PARSE-01
                     resolution of inchi/formula/target-file; a nonfinite-float constraint matrix awaits CLI-CAN-02.
```

**Uptake record — finishing ID-PARSE-01 (the parser service), ID-STEREO-01 (sound isotope perception), and
EVD-KEY-01 (the unified `ReactionEvidenceKey`)** (all three `IN_PROGRESS`; each closes its clearest remaining piece
with an honest, stated boundary):

```
ID:                  ID-PARSE-01 (the ONE parser service, every form + receipt) + ID-STEREO-01 (sound isotope
                     perception) + EVD-KEY-01 (first-class ReactionEvidenceKey, live in the sound rate anchor)

ID-PARSE-01:         identity_parse.py resolve_identity resolves EVERY section-14.2 form to a typed
                     ResolvedIdentity + ParseReceipt: NAME/SMILES -> Molecule (CONSTITUTION); FORMULA and an InChI
                     FORMULA SUBLAYER -> a FORMULA-layer identity (the InChI /q,/p CHARGE layers are CONSUMED into
                     a correctly-charged Formula; /c,/h -> a constitution BLOCKER, /t,/b,/m,/s -> stereo, /i ->
                     isotope, any other layer NAMED in a note); TARGET_FILE dispatches its contents. The receipt is
                     echoed into the response diagnostics, surfaced in BOTH the human render and --json. A bare
                     formula/InChI is refused for a structure search (section 5.4). REMAINING: semantic_digest
                     alias-collapse (name:X == X), a named design step (the receipt is provenance, not search id).

ID-STEREO-01:        smiles.py isotope_refined_key/_isotopic_identity compute a canonical isotope-refined-
                     CONSTITUTION key by running the SAME proven graph canonicaliser (_canonical_by_
                     individualisation) over an ISOTOPE-COLOURED copy of the graph -- presentation-invariant,
                     symmetric-position-invariant, positionally-distinct, resonance-canonical (commits to the EXACT
                     Kekule structure the constitution does), refines constitution. SmilesFeatures.isotopic_digest
                     carries it. BOUNDARY: modulo stereochemistry (chirality is a reflection, invisible to graph
                     canonicalisation), so it is NOT the lattice ISOTOPIC slot -- that + CONFIGURATION stay deferred.

EVD-KEY-01:          evidence_key.py ReactionEvidenceKey is the section-9.1 value (canonical structure identities +
                     primitive gcd stoichiometry + direction-by-side + optional context). LIVE in the sound rate
                     anchor (kinetics.py reaction_evidence_key/record_evidence_key, eyring.py _resolve_barrier),
                     byte-congruent to the tuple key it replaced -- NOT a dead switch. REMAINING: migrating the
                     FORMULA-keyed providers (conditions decomposition path, selectivity, decompiler_review) onto it.

verify:              +5 new/rebuilt adversarial test files/classes (tests/test_id_parse.py 30, test_id_stereo.py
                     TestSoundIsotopePerception, test_evidence_key.py 13, plus test_service/test_cli_err updates).
                     Red-team via workflow (wmz8ef63t, 5 attack bearings + per-finding refute-by-default verify, 12
                     agents, ~1.0M tokens): 6 findings CONFIRMED, 1 correctly REFUTED, ALL 6 FOLDED pre-commit --
                     F1/HIGH InChI /q,/p charge fail-open (charged species collapsed to neutral) -> charge now
                     consumed; ID-STEREO-01-SPLIT-KEKULE/HIGH naphthalene split -> Kekule chosen by the constitution
                     digest so it never splits a species; RECEIPT-HUMAN-DROP/MED -> receipt now in the human render;
                     two vacuous-green EVD gate tests -> real positive controls (N2O5 sourced rate, FAVORED->UNKNOWN
                     draft); IRON-EVDKEY-OVERCLAIM/MED "everywhere" -> honest "kinetics/eyring only" docstring.

result:              3127 passed, 14 skipped, 1 xfailed (baseline 3073; +54). ruff clean on every changed file;
                     git diff --check clean.

residual / follow-on: ID-PARSE-01 -- semantic_digest alias-collapse. ID-STEREO-01 -- sound CONFIGURATION (CIP
                     parity) stereo perception + the MatchLayer lattice ISOTOPIC slot. EVD-KEY-01 -- migrate the
                     FORMULA-keyed providers (conditions/selectivity/review) onto ReactionEvidenceKey to close their
                     isomer-borrow; the formula-edge review path lacks structural certainty until it carries graphs.
```

## 4. P1 physical, data, and affordability backlog

These items may remain explicit alpha limitations only where the public renderer cannot imply a
stronger result.

| ID | Requirement | Present issue | Acceptance test | Status |
|---|---|---|---|---|
| `PTABLE-01` | Formula validation uses one supported periodic-table authority and positive integer counts | Complete table is now used; zero/negative/non-integer formula counts are refused | CaO, representative heavy elements and invalid-count regressions pass | `IMPLEMENTED_AND_VERIFIED` |
| `THERMO-UNC-01` | Carry reported uncertainty, phase, standard state and source | `ThermoRef` already carries phase, provenance and grade; the missing piece is a reported UNCERTAINTY field. Assessed and DEFERRED from the P2 honesty batch: real values need sourced CODATA/JANAF uncertainties (fabricating them is forbidden), and a hollow null-field add would change every `ThermoRef` digest for no honesty gain -- this is a focused sourcing pass, not a render fix | Round-trip fixture preserves every field; incompatible phases do not match | `TODO` |
| `THERMO-DIG-01` | Evidence grade/provider semantics affect artifact digest | Some grade fields are excluded from comparison/digest | Change grade/source fixture -> semantic digest changes | `TODO` |
| `EQUIL-NAME-01` | Equilibrium diagnostic is not called practical extent/yield | The ideal K/conversion render now names the ideal model and denies practical yield explicitly (`a34cc69`): the reason reads "ideal-model equilibrium extent, NOT a rate and NOT an expected isolated/practical yield" (section 9.5) and the standalone conversion finding carries the same denial | Golden render names ideal model and denies expected yield | `IMPLEMENTED_AND_VERIFIED` |
| `KIN-CTX-01` | Kinetics key includes conditions, order, units and composition requirements | Rate can be reused outside context; higher-order half-life underdetermined | Wrong temperature/order/unit refuses; missing concentration stays unknown | `TODO` |
| `SELECT-SRC-01` | Curated selectivity paths have accepted exact source locators | Default promoted records carry accepted DOI locators; missing/malformed/unreviewed citations remain `UNKNOWN`; acceptance still lacks curator/date/provider identity | Add review metadata and exact reaction-context governance | `IN_PROGRESS` |
| `CONSTR-VAL-01` | Constraints are finite, physical and ordered | Finite, positive and ordered validation is implemented | Negative/nonfinite/inverted T/P bounds fail in targeted regressions | `IMPLEMENTED_AND_VERIFIED` |
| `FIT-SEM-01` | `UNCONSTRAINED` differs from assessed fit | An empty `ConstraintBox` now yields `UNCONSTRAINED`, never `FITS`; `FITS` requires the box to actually constrain a dimension the route satisfies, and an undeclared constrained dimension stays `UNKNOWN` (`a34cc69`). NAMING RESIDUAL: SmartChem keeps the shorter `FITS`/`UNKNOWN` where the standard section 11 says `ASSESSED_FIT`/`UNKNOWN_FIT`; the user-visible rename (and `BLOCKED`) is deferred to the shared-response work under the section 18 migration-alias discipline | Empty box -> `UNCONSTRAINED`; unknown bounded dimension -> `UNKNOWN`(_FIT) | `IMPLEMENTED_AND_VERIFIED` |
| `COST-VEC-01` | Rank affordability by sourced multi-objective cost vector | No cost/price ranking exists | Unknown price stays unknown; hard blocker dominates cheapest route | `TODO` |
| `COST-PROV-01` | Price/availability have region, currency, date and source | Availability is editorial/static | Snapshot round-trip and stale-data warning | `TODO` |
| `POOR-PARETO-01` | Poor-man mode exposes Pareto frontier, not one opaque score | Accessibility not integrated into ranking | Two trade-off fixtures both appear on frontier; dominated route removed | `TODO` |
| `MAT-PRE-01` | Commodity mixtures can add explicit preprocessing/analysis | Pure identity currently stands in for source mixture | Dilute/impure source requires typed operation and revised balance/cost/waste | `TODO` |

**Uptake record — two render-honesty defects** (closes `FIT-SEM-01`, `EQUIL-NAME-01`):

```text
ID:                  FIT-SEM-01, EQUIL-NAME-01
commit:              a34cc69
files:               smartchem/experiment/drafter.py, tests/test_drafter.py,
                     smartchem/experiment/equilibrium.py, tests/test_equilibrium.py
tests:               tests/test_drafter.py::TestConstraintFitting (3 new), tests/test_equilibrium.py::
                     TestEquilibriumRenderDeniesYield (2 new)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              2582 passed, 14 skipped, 1 xfailed (baseline 2577; +5). ruff clean; git diff --check clean.
falsifier fixture:   fit_route(anhydride_route, ConstraintBox()) -> UNCONSTRAINED, .fits False (an empty box is
                     not a pass); the same route against a real temp/pressure box -> FITS.
                     equilibrium_of_step(water_gas_shift()).reason contains "ideal-model equilibrium extent, NOT a
                     rate and NOT an expected isolated/practical yield".
residual limitations:
  1. FIT-SEM-01 naming: SmartChem keeps FITS/UNKNOWN where the standard section 11 says ASSESSED_FIT/UNKNOWN_FIT;
     the user-visible rename (and the BLOCKED tier, which belongs to the readiness/safety layer) is deferred to
     the shared-response work under the section 18 migration-alias discipline.
  2. THERMO-UNC-01 was assessed and left TODO in this batch (see its row): real uncertainties need sourced
     CODATA/JANAF values, and a hollow null-field add would churn every ThermoRef digest for no honesty gain.
```

## 5. P2 strengthening backlog

| ID | Direction | Why it matters | Status |
|---|---|---|---|
| `TRANSFORM-REG-01` | Versioned reaction transform/provider plugin registry | Makes the bounded candidate space extensible and receipt-addressable | `TODO` |
| `OPEN-SEARCH-01` | Optional generative intermediates behind explicit stronger bounds | Broadens decompiler without pretending a closed registry is nature-complete | `DEFERRED` |
| `MECH-IR-01` | Mechanism/elementary-step representation distinct from net equations | Prevents net balance from masquerading as mechanism | `DEFERRED` |
| `ACTIVITY-01` | Phase/activity/solvent-aware equilibrium model | Needed before practical conversion claims | `DEFERRED` |
| `RATE-MODEL-01` | Condition-sensitive kinetic/rate-law integration | Needed before time-to-completion claims | `DEFERRED` |
| `PROC-EXEC-01` | Execution log and observations distinct from planned procedure | Enables learn/compare loop without retroactive evidence inflation | `DEFERRED` |
| `LIT-IMPORT-01` | Structured ORD-like import with identity/context validation | Scales source coverage while preserving provenance | `DEFERRED` |
| `AFFORD-SNAP-01` | User-controlled regional material/price snapshots | Makes affordability reproducible rather than universally asserted | `DEFERRED` |

## 6. Uptake sequence

The sequence is dependency-driven. Adding reaction breadth before the truth envelope would make
the system more persuasive without making it more reliable.

### Milestone A — Stabilize the audit branch

The direction/isomer/selectivity, receipt, formula, scission, CLI, dossier, constraint,
affordability and safety regressions are green. The final full suite completed with **2510
passed, 51 skipped, 1 expected failure in 205.04 seconds**; `git diff --check` and bytecode
compilation are also clean.

Implementation commit: `834db704d3425cb2ab9b34b3644e0cada3aaba4c`

Remaining stabilization work is to preserve every audit fix as a focused regression and never
weaken a verdict-changing test merely to extend chemistry coverage.

Exit criterion: all branch patches are either `IMPLEMENTED_AND_VERIFIED` or honestly reverted/
returned to `TODO`.

### Milestone B — Build the truth envelope

Implement together:

- extend linear `SearchReceipt` and no-route semantics to formula/DAG/shared JSON;
- extend primitive stoichiometry from the tested physics/selectivity paths to global
  reaction/evidence/digest identity;
- identity layers/loss records;
- generalize the tested exact structural/directional assembly key to all evidence contexts;
- generalize tested formula-terminal behavior into `TerminalPolicy`;
- retain tested route-dossier readiness and non-authorizing safety language while adding the
  missing typed identity/material boundaries.

Exit criterion: gates G1–G5 and the non-procedure half of G7 pass.

### Milestone C — One public compiler

Implement `CompilationRequest/Response`, versioned JSON, unified parser, canonical CLI, exit
codes, package entry point and `0.5.0a1` version.

Exit criterion: G0 and G8 pass; legacy aliases generate equal request digests.

### Milestone D — Material reality and poor-man mode

Implement `StockMaterial`, typed quantities/assay, inventory flow, source-lead migration,
quantity-safe shopping, cost vectors and Pareto ranking.

Exit criterion: G6 passes. An identity-only source can help discovery but never manufacture an
amount, purity, fitness or price claim.

### Milestone E — Bench-draft ladder

Implement `ProcedureIR`, hazard/process fields, completeness validation and qualified-review
state. Expand evidence and transform coverage only through exact provider contracts.

Exit criterion: G7 passes. No automatic path can earn `BENCH_DRAFT` from a balanced equation and
condition envelope alone.

## 7. Required test matrix

Every milestone should add tests at four layers:

| Layer | Required evidence |
|---|---|
| Value construction | Invalid identity, evidence, units, bounds and readiness states refuse. |
| Algorithm | Completeness, invariance, termination, deduplication and quantity-flow properties hold. |
| Service/serialization | Request digest, JSON schema, provider snapshots and result semantics round-trip. |
| CLI/golden render | Exit code and human text cannot contradict JSON truth state. |

Property tests should include:

- coefficient rescaling invariance;
- input/inventory permutation invariance;
- same-formula structural non-equivalence;
- cap monotonicity: raising a bound cannot turn a formerly complete receipt into another complete
  receipt with fewer candidates under the same registry;
- source-order invariance or explicit provider conflict;
- route/DAG atom, charge and quantity flow;
- all unknowns remain unknown across render/serialize/parse.

## 8. Evidence record for closing an item

When an item moves to `IMPLEMENTED_AND_VERIFIED`, append a compact record:

```text
ID:
commit:
files:
tests:
command:
result:
falsifier fixture:
human-output check:
JSON/schema check:
residual limitations:
```

Do not paste a passing count without naming the new verdict-changing test. Do not mark a human
wording fix complete if the machine schema still claims the stronger state.

## 9. Alpha definition of done

The `0.5.0a1` uptake is complete when:

- every P0 row is `IMPLEMENTED_AND_VERIFIED`, or a narrower release contract removes the claim
  that made it P0;
- the full non-optional suite and all new adversarial tests pass;
- canonical and legacy CLIs use the same typed service and version;
- every result carries exact identity/loss, terminal policy, search receipt, readiness, blockers,
  provider versions and stable IDs;
- incomplete search never looks complete, and incomplete empty search never looks like a proof
  of absence;
- reverse equations do not inherit forward evidence;
- common stoichiometric scaling cannot change intensive verdicts;
- identity-only commodities cannot invent purity, quantity, price or fitness;
- sparse output is a route dossier with missing operations visible;
- no route is automatically authorized as safe or unattended;
- the release declaration in the standard document is true for every public code path.

Anything less can still be valuable development work. It is not yet the standard-setting
chemical compiler release described here.
