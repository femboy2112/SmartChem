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

### 3.2 Decompiler/recompiler unity

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `IR-CHEM-01` | One `ChemicalCompilationIR` connects both directions | The shared IR envelope exists (`smartchem/compilation_ir.py`) and the formula decompiler emits it via `decompile_to_ir` (`09b3072`): a versioned value with a presentation-invariant, semantic-input-sensitive digest (a search-bound change alters it even when the candidate set is identical, via `request_digest`), carrying a typed target identity, terminal-policy digest, search status/receipt digest, and canonical digest-sorted candidates. The structural (route/DAG) producer now exists too: `recompile_to_ir` (`43dbcb1`) packages `search_routes`/`search_dags` as canonical `ROUTE`/`DAG` candidates over a STRUCTURE-layer identity, with the same presentation-invariant/semantic-sensitive digest (a bound change alters it via `request_digest`; the reagent helper pool is distinguished from plain stock). IR serialization + recompiler consumption of a SERIALIZED artifact, first-class loss records, and registry receipts remain | Serialize/deserialize the IR and have the recompiler consume it; add `IdentityLoss` records (`IR-LOSS-01`) and registry receipts | `SRCH-RCT-01` (done), `ID-LAYER-01` | `IN_PROGRESS` |
| `IR-LOSS-01` | Formula/structure forgetting is explicit | `--smiles` formula path discards topology without a first-class loss record | Add `IdentityLoss`; downgrade or refuse dependent claims | `CCO` vs `COC` remain distinct as input identities; formula view announces collapse | `ID-LAYER-01` | `TODO` |
| `IR-INV-01` | Claimed inverse scope is executable | Route compiler cannot construct water from H/O or H2/O2 terminals | Either add an explicit transform that bridges the shared IR or narrow naming/docs | Water fixture succeeds within named transform registry or renders a precise unsupported-transform refusal | `IR-CHEM-01` | `TODO` |

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

### 3.3 Identity and evidence

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `ID-LAYER-01` | Formula, molecule/formula-unit, and stock material are distinct values | Molecule/formula boundaries are partial; mixtures and salts are unsafe | Add typed layers and conversion/loss rules | Disconnected salt, chiral, isotope and mixture fixtures preserve identity or refuse | None | `TODO` |
| `ID-PARSE-01` | Explicit name/SMILES/InChI/formula parsing with echoed normalization | Synthesis CLIs now accept registered offline names and explicit `name:`/`smiles:` prefixes; no one parser/receipt or InChI/formula parity | Build one parser service with source/policy receipt and every identity form | Registered names pass now; add ambiguous name and all explicit-form round trips | `ID-LAYER-01` | `IN_PROGRESS` |
| `ID-STEREO-01` | Stereo/isotope/local-charge/component loss never silent | Unsupported features may be erased or represented misleadingly | Detect features at parse/canonicalize boundary; refuse or record blocker | Enantiomer, isotope, zwitterion, disconnected salt do not collide with simplified analogues | `ID-LAYER-01` | `TODO` |
| `ID-SCISS-01` | Structural scission preserves the represented rooted open valence and refuses unsupported charge | Rooted open-valence identity and neutral-only refusal are implemented; duplicate reagent types are deduplicated | Keep this scoped refusal while broader identity layers are built | Rooted isomers remain distinct; non-neutral target refuses; duplicate reagent spellings do not multiply candidates | None | `IMPLEMENTED_AND_VERIFIED` |
| `EVD-KEY-01` | Evidence key includes structure, primitive stoichiometry, direction, context and source | Assembly conditions now require exact represented structures and direction after a primitive formula candidate index; broader identity/context/source key is absent | Generalize into `ReactionEvidenceKey`; migrate all evidence providers | Same-formula isomer test passes now; add stereo/isotope/charge/phase/context/source fixtures | `STO-PRIM-01`, `ID-LAYER-01` | `IN_PROGRESS` |
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
| `STOCK-01` | `StockMaterial` represents mixture, assay, quantity, source and cost | `StockMaterial` + `MaterialComponent` + `FitnessVerdict` exist (`smartchem/experiment/stock.py`, `7d27e3c`): a typed material of components (each a fraction INTERVAL), a phase, and provenance, with a rigorous `satisfies(identity, min_assay)` interval gate (vinegar -> `INSUFFICIENT_ASSAY`, a straddling requirement -> `UNKNOWN_ASSAY`, an unknown fraction never passes). The full section 10.2 schema (quantity, container, cost, jurisdiction, impurity profile), canonical-structure component keying, and recompiler/shopping integration remain | Extend to the full section 10.2 schema; key components by canonical structure; bridge `CommodityReagent` -> `StockMaterial` as an UNKNOWN-assay source lead; wire the gate into route/shopping selection | Vinegar cannot satisfy pure acetic-acid input without assay/preprocessing | `ID-LAYER-01` | `IN_PROGRESS` |
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
| `SVC-REQ-01` | One typed request/service powers chemical commands | `compile` and `synthesize` bypass/share different rungs and defaults | Implement `CompilationRequest/Response`; route aliases through it | Equal flags across aliases produce equal request/result digests | `IR-CHEM-01` | `TODO` |
| `CLI-CAN-01` | Canonical `decompile` and `recompile`; legacy aliases share defaults | Current commands diverge | Add canonical verbs; deprecate aliases without duplicate logic | Command matrix gives equal request JSON | `SVC-REQ-01` | `TODO` |
| `CLI-NAME-01` | Normal names accepted without private formatting | Registered offline names and explicit `name:`/`smiles:` prefixes work in synthesis CLIs; InChI/formula/echo/shared parser are incomplete | Finish unified identity parser and echo receipt | Registered-name and SMILES tests pass; add InChI/formula/ambiguity matrix | `ID-PARSE-01` | `IN_PROGRESS` |
| `CLI-EXIT-01` | Stable exit codes separate route/no-route/partial/refusal/invalid/internal | Synthesis front doors now use 0/2/3/4/5 for named outcomes; decompile uses 0/2/4; shared code 70/internal mapping is absent | Finish standard table through one shared service and subprocess matrix | Codes 0/2/3/4/5 observed; add controlled internal-error fixture for 70 | `SRCH-RCT-01`, `SVC-REQ-01` | `IN_PROGRESS` |
| `CLI-ERR-01` | Invalid chemistry/numeric input yields domain error without traceback | Invalid formula/name/SMILES and charged-model refusal are concise and mapped to 2/5; no one central mapping covers every format/path | Centralize error mapping and strict validation | Current invalid/refusal probes pass; add InChI/formula-file/nonfinite subprocess matrix | `ID-PARSE-01`, constraints | `IN_PROGRESS` |
| `CLI-VERS-01` | Package installs `smartchem`, supports `--version`, exposes consistent `__version__` | Entry point, package metadata and `__version__` report `0.5.0a1` | Preserve single-source consistency in release packaging | Targeted script/module/version tests pass | None | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-JSON-01` | Stable JSON contains request, identity, receipt, tier, blockers and route IDs | Human-oriented paths dominate | Add versioned serializer/schema and golden fixtures | Human and JSON agree on all semantic fields | `SVC-REQ-01`, `READY-TIER-01` | `TODO` |

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
