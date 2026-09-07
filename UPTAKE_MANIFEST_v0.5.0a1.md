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

## 2A. Genericity reorientation — authoritative current-state projection (2026-09-03)

**This is the single authoritative current-state projection.** The detailed §3–§8 backlog and its append-only
uptake records remain below as the *historical* record of how each row became true; where a §3 row's prose still
carries a superseded "REMAINING" clause, **this section governs**. Do not read a stale clause in §3 as current
truth without checking it here.

**Snapshot.** Base `main` at `161ef0f` (branch `chem-compiler-mainline-2026-08-31`); reconciliation work on
`chem-genericity-reorient-2026-09-03`. Reproduced fast suite (2026-09-03, `.venv`, `-p no:cacheprovider`, exit 0):
**`3438 passed, 14 skipped, 1 xfailed`** in 603.96 s. Ruff: 46 pre-existing ambient errors (unused imports in
`tests/test_water_wave_validation_program.py` and siblings) — not introduced here, not gating this section.
**Governing reorientation doc:** `AUDIT_GENERIC_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md` (draft `4160fe8`,
selected over two sibling ChatGPT drafts; see its reconciliation note).

### 2A.1 The three finish lines (lanes)

Progress in one lane never implies completion of another. This is a hard rule, not a nicety.

| Lane | Finish line | State |
|---|---|---|
| **A — Alpha conformance** | A truthful bounded compiler conforming to `v0.5.0a1`. | **Near.** Shared IR, typed request/response, search receipts, identity/evidence gates, exact DAG flow + inverse shopping, `StockMaterial`, fail-closed errors all landed. Remaining: the final P0 integrations and a clean RC freeze (`ERR-EVIDENCE-01` is **DONE** — §2A.2 marks it `IMPLEMENTED_AND_VERIFIED`; the RC-readiness audit §2A.7 enumerates the actual remaining blockers). |
| **B — Chemical genericity** | A structure-preserving decompile/recompile IR + a typed `TransformProvider` registry supporting qualitatively distinct transform families through **unchanged** core search. | **Thesis DEMONSTRATED, loop CLOSED, coverage MEASURED.** `CANON-KEKULE-01`, `IR-STRUCT-01`, `IR-FORGET-01`, `TRANSFORM-PROVIDER-01`, `CHEM-ALG-01` are **DONE**. `IR-REPLAY-01` (the witness is a re-verifiable graph edit) and `IR-INVERT-01` (a STRUCTURE artifact reconstitutes its target with NO caller structure) closed the decompile→recompile loop at the graph level (`846e8bc`). `CHARGED-ALG-01` added the **first charged family** (heterolytic scission) with a charge-carrying `ChargedDecompositionEdge` forget — the algebra now reaches past neutral rewrites. `HOLDOUT-RXN-01` **froze the family-stratified coverage benchmark** and MEASURES the payoff (default capped 8/18, +bond-order +2, +heterolytic +5, 3/18 genuinely outside-closure). **All named Lane-B follow-ons now landed**: redox `757aeb4` (item 1), the recompile-IR registry threading `c70afc7` (item 4), the bond-order structure-rebuilding inverse `65af346` (item 3a); item 3b (the graph-scission witness replay for products) was already under `IR-REPLAY-01`. The algebra now spans **four qualitatively distinct families** through the unchanged core search — neutral capped scission, neutral bond-order edit, charged heterolytic scission, and charge-only redox (the chem↔EM bridge). |
| **C — Bench readiness** | `ProcedureIR`, quantities, assays, operations, process hazards, analytical acceptance, waste, equipment ratings, qualified review. | **Deliberately outside the alpha.** `TERM-MAT-01` down-paid by `sourcing.plan_sourcing`; **`THERMO-UNC-01` sourcing down-paid (item 5) + σ_ΔG PROPAGATION DONE (`8827306`): the sourced/derived ± now flows through `feasibility_of_step`/`equilibrium_of_step` in quadrature (UNKNOWN when any input lacks σ; a LOWER BOUND for correlated derived inputs) — see its §3 row + the propagation record; widening the seed past CODATA remains**; **`COST-VEC-01` price-data block LIFTED (item 5, 2026-09-04): the USGS Mineral Commodity Summaries 2026 figures are now VERIFIED in-sandbox (curl + `pdftotext -layout`, read off the primary chapter tables) and committed as a frozen, dated, cited seed (`experiments/usgs_commodity_seed.py`, 8 forms: salt×4, soda ash, lime×2, sulfur) with a non-vacuous validator — the sourced dated prices the row was blocked on now exist. **Price-WIRING DONE (2a, `72cdf7e`) + ENGINE CORE DONE (2b, `21264cd`): the verified prices attach as dated §10.4 `CostObservation`s (structure-keyed), and `experiment/affordability.py` is the `CostVector` + Pareto-frontier engine (hard-blocker-dominates-cost + UNKNOWN-incomparable, a sound strict partial order).** The LIVE route-level wiring (service `affordability_frontier`) + the coupled-shopping refusal remain = the 2b follow-on (COST-VEC-01 → `IN_PROGRESS`). `ProcedureIR` deferred. The `FORMAL_CANDIDATE` floor stays immovable until these obligations exist. |

### 2A.2 Reoriented roadmap IDs (the audit's additions + the elevated canonical repair)

| ID | P | Lane | Status | Acceptance test (verdict-changing) | Depends on |
|---|:---:|:---:|---|---|---|
| `CANON-KEKULE-01` | P0 | B | **`IMPLEMENTED_AND_VERIFIED`** | Aromatic and explicit-Kekulé spellings of a fused aromatic share one constitution digest; constitutional isomers stay distinct; relabel-invariant (`c126055`+`6a8c5a6`; `tests/test_canon_kekule.py`, `tests/test_stock.py::…kekule`). | shared `_ident` |
| `ERR-EVIDENCE-01` | P0 | A | **`IMPLEMENTED_AND_VERIFIED`** | A genuine no-record lookup → `UNKNOWN`; an injected internal provider fault → `ERROR_INTERNAL`/exit 70, no raw traceback and no false "conditions unknown". Fixed **both** `assembly_conditions` (the deep root the audit missed) and `_conditions_for`, and (red-team fold `69a1ffd`) the separate `synthesize` CLI's engine catch + its missing top-level exit-70 guard; proven non-vacuous. `1265efe`+`69a1ffd`; `tests/test_err_evidence.py`. | route search, `CLI-EXIT-01` |
| `IR-STRUCT-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | A first-class typed `StructuralCandidate` rides `ChemicalCompilationIR` (schema `v1alpha5`): parent/product STRUCTURE identities + exact formula + **canonical molecular graph** (each `StructuralSpecies` carries atoms/bonds/charge/state, so its identity/formula are RE-VERIFIABLE on read — a forged or isomer-swapped structure is refused, not a trusted label; red-team fold), primitive stoichiometry, the capped-scission edit witness (digest + equation), `DECOMPOSE` direction, provider id/version, `FORMAL_CANDIDATE` tier, loss records, and the exact forgetful projection. `decompile_structure_to_ir` emits the structure-preserving decompile (paracetamol's real amide hydrolysis is among the candidates — two distinct witnesses sharing one projection: the IR carries MORE than its formula image); round-trips digest-stably; a candidate whose parent is not the IR target, or on a non-STRUCTURE/non-DECOMPILE IR, is refused. `0aac8a1` + fold `fd10792`; `tests/test_ir_struct.py`. | `structure_descent`, `IR-CHEM-01` |
| `IR-FORGET-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | The forgetful square is a FORMULA-level invariant enforced across three layers so no single unverified field is load-bearing (red-team fold closed a vacuity where it trusted the structure identity blindly): (1) `StructuralCandidate.__post_init__` recomputes the projection from the stored species FORMULAS and refuses unless it equals the stored projection byte-for-byte (digest AND equation), commuting through serialization, mismatch refused-not-coerced; (2) each species' formula/identity are graph-backed (a forged isomer is refused at the species); (3) the parent is pinned to the IR target. `0aac8a1` + fold `fd10792`; `tests/test_ir_struct.py::{TestForgetfulSquare,TestRedTeamFold}`. Exact PRODUCT-isomer edit-fidelity (beyond formula) is the witness label; the cross-producer reconciliation (audit §7.3 `== D_formula(forget(S))`) and the graph-scission witness replay are named follow-ons. | `IR-STRUCT-01` |
| `TRANSFORM-PROVIDER-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | The bounded search is parameterized by a typed closed `TransformProviderRegistry` (`smartchem/transform_provider.py`): capped-scission enumeration runs EXCLUSIVELY inside `CappedScissionProvider` (the `routes.py` seams and the structural decompile reach it via `registry.enumerate`, never a direct call). The registry digest moves on any provider set / id / version / capability-manifest change; aggregate completeness is the AND of every provider's own, so provider-local partiality never fakes a complete. The DEFAULT registry (capped-only) is behavior-AND-digest identical — the whole 3483-test suite is transparent to the reroute. `ea47f3d` + red-team fold `5bdac74` (registry-blind receipt provenance); `tests/test_transform_provider.py`. | `IR-STRUCT-01` |
| `HOLDOUT-RXN-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | A FROZEN, family-stratified coverage benchmark (`experiments/holdout_rxn_benchmark.py`, guarded live by `tests/test_holdout_rxn.py`): 18 targets across an increasing registry chain (capped < +bond-order < +heterolytic), each attributed to the family that FIRST constructs a complete decomposition — or `OUTSIDE_CLOSURE` if none. MEASURES the payoff: default (capped) constructs **8/18**, +bond-order unlocks **+2** (ethylene, benzene), +heterolytic unlocks **+5** (HCl, HF, methane, water, acetylene), **3/18 genuinely outside-closure** (N₂, O₂, Ne). Non-vacuous by construction (every bucket populated, coverage < 100%); the target set + each attribution + a content hash + a separate holdout-subset hash are frozen, so a wrong provider change moves a frozen attribution and fails the test. `CHARGED-ALG-01`; `tests/test_holdout_rxn.py`. | `TRANSFORM-PROVIDER-01`, `CHEM-ALG-01`, `CHARGED-ALG-01` |
| `CHARGED-ALG-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | The first CHARGED family: single-bond heterolytic scission (`reactant(q) → ion⁺ + ion⁻`, localized-charge model) rides the transform algebra. `HeterolyticScission` gains the uniform transform interface (`reagents`/`products`/`forget`); a new **charge-carrying `ChargedDecompositionEdge`** is its forget target (the neutral `MediatedEdge`/`DecompositionEdge` refuse a charged species), so the forgetful square becomes a **charge-AND-mass** invariant (a charge-non-conserving edge is refused — proven non-vacuous). Registered via `HeterolyticScissionProvider`, it rides the SAME `StructuralCandidate`/`StructuralWitness` machinery with no engine fork (witness gains a `fragments` field for the ion graphs), obeys the graph-scission replay (`IR-REPLAY-01`) and the structure-rebuilding inverse (`IR-INVERT-01` generalizes — the ions rejoin across the cut → the parent, HCl reconstituted), and stays `FORMAL_CANDIDATE`. DECOMPILE-only (charged fragments do not terminate at neutral stock — not forced through the route search). Redox (electron-transfer) stays a NAMED follow-on. IR `v1alpha6`→`v1alpha7`, candidate `v1alpha2`→`v1alpha3`, witness `v1alpha1`→`v1alpha2`; `tests/test_charged_family.py`. | `TRANSFORM-PROVIDER-01`, `IR-REPLAY-01` |
| `REDOX-ALG-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | The CHARGE-ONLY family: a redox (electron-transfer) half-reaction (`reduced → oxidized + n e⁻`) rides the transform algebra — the chem↔EM bridge, and the first family whose "decomposition" does NOT reduce the species' size (same atoms, same bonds; only charge and electron count change). `RedoxHalfReaction` gains the uniform interface (`reactant`/`reagents`/`forget`); a new **charge-carrying `ElectronTransferEdge`** is its forget target — mass conserved trivially (electrons are massless), charge the conserved quantity. An electron is atom-less, so it can never be a `Formula` (`Formula.of` refuses it) nor a `StructuralSpecies`; it rides an explicit integer `electrons` count on the witness (digest-pinned), NOT a product species. Registered via `RedoxHalfReactionProvider` (opt-in, absent from the default registry; `max_electrons` on the manifest → a bump moves the registry digest), it rides the SAME `StructuralCandidate`/`StructuralWitness` machinery with no engine fork (the witness gains an `electrons` field, 0 for every other family → transparent), obeys the charge-AND-mass forgetful square + the graph replay (`IR-REPLAY-01`) + the structure-rebuilding inverse (`IR-INVERT-01` — the charge-only inverse re-adds the electrons → the reduced parent, Na⁺+e⁻→Na and NO⁺+e⁻→NO reconstituted), and stays `FORMAL_CANDIDATE`. DECOMPILE-only; ORTHOGONAL to `HOLDOUT-RXN-01` (charge-only → unlocks zero new decompositions, so the frozen benchmark is untouched). IR `v1alpha7`→`v1alpha8`, candidate `v1alpha3`→`v1alpha4`, witness `v1alpha2`→`v1alpha3`; `tests/test_redox_family.py`. | `CHARGED-ALG-01`, `IR-REPLAY-01` |
| `CHEM-ALG-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | A second, qualitatively distinct family — the partial bond-order edit (dehydrogenation `alkane → alkene + H2`, `smartchem/bond_order_edit.py`, distinct from the whole-bond rewrites capped-scission excludes) — registers through `BondOrderEditProvider` and composes through the UNCHANGED core route AND DAG search: with the extended algebra the hydrogenation route `H2 + C2H4 → C2H6` is found; with the default (capped-only) algebra it is NOT — no engine branch, only the registry parameter. It rides the structural IR (a `BOND_ORDER_EDIT` candidate with a `DECOMPOSITION_EDGE` projection, alongside capped scissions), obeys the forgetful square (recompute-verified, a tampered projection refused), and stays `FORMAL_CANDIDATE` — no sourced conditions → `unknown()` through the UNCHANGED conditions gate (the pipeline was already duck-typed on the uniform transform interface). `ea47f3d` + red-team fold `5bdac74` (the H2-node crash); `tests/test_bond_order_edit.py`. The frozen family-stratified benchmark `HOLDOUT-RXN-01` (MEASURES cross-family coverage) is a named follow-on — this brick delivers the family + composition, not the benchmark. | `IR-FORGET-01`; `HOLDOUT-RXN-01` (follow-on) |
| `IR-REPLAY-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | The scission witness is a RE-VERIFIABLE graph edit, not a one-way label. Each `StructuralCandidate` carries a first-class `StructuralWitness` (the family transform's own graph edit in its own index space); `__post_init__` reconstructs the exact transform (re-running its family certificate) and demands its GRAPH-level products/reagents/reactant equal the stored species and its digest equal `witness_digest`. This is strictly stronger than the formula square, which is blind to a product's same-formula isomers: the 4-aminophenol→2-aminophenol swap (same formula `C6H7NO`) that passes the formula square is REFUSED here (reproduced, proven non-vacuous). Rides + round-trips digest-stably (IR `v1alpha6`, candidate `v1alpha2`, witness `v1alpha1`). `846e8bc`; `tests/test_ir_struct.py::TestGraphScissionReplay`. | `IR-FORGET-01` |
| `IR-INVERT-01` | P1 | B | **`IMPLEMENTED_AND_VERIFIED`** | The structure-rebuilding inverse (audit B0 headline). `recompile_from_serialized` inverts a FORMULA artifact and REQUIRES a caller-supplied structure (a formula does not fix one); the new `recompile_structure_from_serialized` reads a STRUCTURE artifact whose candidates carry graphs + the re-verifiable witness, so the target is READ FROM the artifact — **NO caller structure** — and `StructuralCandidate.reconstitute_parent` inverts each capped scission (product graph + edit → the parent), reconstituting the target and closing the decompile→recompile loop at the graph level (paracetamol reconstitutes from all 14 decompositions). A FORMULA artifact routes out; the reagentless bond-order family's inverse is refused as a named follow-on (H2 carries no skeleton), never a vacuous echo. W3 unchanged: invertibility, never a validated synthesis. `846e8bc`; `tests/test_ir_struct.py::TestStructureRebuildingInverse`. | `IR-REPLAY-01`, `IR-STRUCT-01` |
| `TERM-MAT-01` | P1 | C | `IN_PROGRESS` | `StockMaterial.satisfies()` gates terminal/production selection: same-structure / sufficient-assay / insufficient / unknown / formulation mismatch / quantity known-unknown are all distinguished; a commodity lead stays UNKNOWN-assay, never terminates a route as a pure reagent; DAG shopping quantities wire in without relabeling a 100%-efficiency lower bound as a predicted purchase. | `STOCK-01`✓, `SHOP-LEAF-02`✓, `sourcing`✓ |
| `COST-VEC-01` | P1 | C | `IN_PROGRESS` | Vector affordability (cost/access/evidence/equipment/hazard/time as separate axes, a Pareto frontier not a hidden scalar), and the coupled/underdetermined shopping refusal resolved. **Price-data block LIFTED (item 5): the sourced dated prices §10.4 required now exist — a frozen, cited, hash-pinned USGS MCS 2026 seed (`experiments/usgs_commodity_seed.py`), verified in-sandbox. Price-WIRING DONE (2a, `72cdf7e`): each verified price attaches as a dated §10.4 `CostObservation` via `experiment/commodity_pricing.py` (transcribed from the seed, cross-checked to it on EVERY sourced field) + the `stock_material_from_commodity` bridge — structure-keyed (`commodity_for` + a composition check, no isomer/name borrow), NaCl→rock-salt 52.95 $/t, Na2CO3→soda-ash 169.35 $/t; lime/sulfur priced-but-unregistered, honestly unattached. `CostObservation` gained a required `unit` (schema v1alpha2, §9.2). ENGINE CORE DONE (2b, `21264cd`): `experiment/affordability.py` — a `CostVector` (the §10.4 axes, each None when UNKNOWN) + a Pareto `dominates`/`pareto_frontier` (proven a sound strict partial order 3 ways) with the two honest rules (a hard blocker DOMINATES cost per G6; UNKNOWN is INCOMPARABLE, so the frontier never over-ranks on absent data) + `basket_cost_vector` aggregating a route's commodity leaves over the 2a prices. LIVE ROUTE-LEVEL WIRING DONE (COST-VEC-01-wire, this round): `service._affordability_frontier` prices each ranked route's `ExperimentRoute.leaf_inputs` (a NEW extractor: the reactants produced by NO step — byproduct-safe, quantity-blind per-unit) into a `CostVector`, wraps it in a typed `AffordabilityFrontierEntry` (Digestible, keyed by the route_digest) and populates `CompilationResponse.affordability_frontier` on a routes-mode search — response schema v1alpha6, guard relaxed to a typed-tuple check, EXCLUDED from `result_digest` (dated data, not identity), goldens regenerated. Honest SIGNAL GATE (post-dominance): empty unless a surviving entry carries a known cost axis or a hard blocker — never a blank-vector list (red-team fold). An EXCLUDED route's exclusions ride as `hard_blockers` (G6). REMAINING (named POST-ALPHA follow-ons): the coupled/underdetermined shopping-refusal resolution (COST-VEC-01-coupled); a quantity/stoichiometry axis (the basket is per-unit today, TERM-MAT); widening priced commodities past the 2 (NaCl/Na2CO3).** | `TERM-MAT-01`, the USGS price seed (done) → the affordability engine |

### 2A.3 Architectural invariants for the next phase (carried from draft `c93b539` §9)

These govern by law, not by feature name. A violation is a compiler bug or an explicitly refused unsupported case.

- **G1 — Semantic request law.** Equal semantic request digests execute the same search and policies, regardless of CLI alias/spelling.
- **G2 — Structural forgetful square.** Every structural decompile transform projects to a valid formula-level conserving transform; the projection commutes with serialization and canonical identity.
- **G3 — Provider locality.** A new transform family needs a provider + tests + registry inclusion (and maybe a witness-schema extension) — **never** a rewrite of core route/DAG recursion.
- **G4 — Search honesty.** Provider exhaustion, provider-local budgets, rejections, and unsupported applicability never disappear into one aggregate "complete" bit.
- **G5 — Identity monotonicity.** A claim may use only identity layers its path perceived and preserved. Forgetting a layer may weaken/lower/refuse a claim; it may never strengthen or silently retain a layer-dependent one.
- **G6 — Evidence separation.** A formal transform witness ≠ a sourced reaction record. Algebraic reversibility does not reverse conditions, kinetics, selectivity, mechanism, or literature.
- **G7 — Material non-substitutability.** A structural identity match is not a stock-material fitness match. Assay, formulation, phase, quantity, age, provenance, availability stay first-class gates.
- **G8 — Failure separation.** "Unknown evidence," "unsupported model," "incomplete search," "invalid input," and "internal software failure" stay distinct outcomes. (`ERR-EVIDENCE-01` enforces the evidence/internal split.)

### 2A.4 Known expected-failure debt register

| xfail | Requirement | Exact test | Scope | Reason | Removal condition | Blast radius |
|---|---|---|---|---|---|---|
| Interchange law | (architecture debt; unassigned to a lane) | `tests/test_laws.py::TestObjectProductAndScheduledProduct::test_true_parallel_interchange_is_architecture_debt` | The categorical interchange law `(f∘g)⊗(k∘ℓ) == (f⊗k)∘(g⊗ℓ)` for true independent parallel events. | Linear reaction histories cannot quotient independent concurrent events by interchange. | A non-linear (partial-order / true-concurrency) history representation. | Contained to `scheduled_product`/`then`; does **not** touch identity, routes, DAGs, or any audit lane. |
| `synthesize` alias G8 | Lane A (standard §14.1 alias-unity / §16 gate G8) | `tests/test_cli_canonical.py::TestCommandMatrixEqualRequestJson::test_synthesize_is_request_equal_to_recompile_G8` | `synthesize <t> --emit-request` MUST equal `recompile <t> --emit-request` (same typed request, no divergent defaults). | The legacy `synthesize` alias keeps divergent defaults (max_depth 2 vs 3, commodities off vs on, provider NETWORK vs OFFLINE, EXPLICIT vs DEFAULT origins) — live-verified. Added (item 2) as a VISIBLE guard so the violation is no longer vacuously green (the compile/recompile matrix never ran `synthesize`). | An Operator decision: align `synthesize`'s defaults to `build_recompile_request` (erasing its distinct download-and-go behavior) OR revise the §14.1/§822 alias mandate. `strict=True`, so its resolution XPASS-fails the guard, forcing the xfail's removal. | **RC blocker** for Lane A (§2A.7); no truth-hole (the divergence is a defaults/labelling gap, not a wrong answer). |

The `CANON-KEKULE-01` strict xfail that existed at the audit base (`4774a26`, the second of "2 xfailed") is **removed** — the fix landed, dropping the count to 1.

### 2A.5 Reconciled stale rows

- **`ID-PARSE-01` (§3.3):** its "REMAINING: collapsing `name:X`≡`X` into the `semantic_digest` (alias-collapse)"
  clause is **stale** — the later `SVC-REQ-01` alias-collapse arc (uptake record after §3.7) landed it: the
  `semantic_digest` keys on normalized structure identity, so every spelling of one molecule collapses to one
  search identity and one result. The row's status is reconciled below in §3.3. This was the audit's §8.3 example.

### 2A.6 Lane dependency edges (execution order)

`roadmap/ledger reconciliation (this section)` → `ERR-EVIDENCE-01` → `CANON-KEKULE-01`✓(done) →
`IR-STRUCT-01` → `IR-FORGET-01` → `TRANSFORM-PROVIDER-01` → freeze `HOLDOUT-RXN-01` → `CHEM-ALG-01`
(first diverse provider) → `TERM-MAT-01` (production wiring) → **alpha RC when Lane A is green** →
`ProcedureIR` only under the separate Lane-C bench-readiness contract.

### 2A.7 Lane-A RC-readiness assessment (item 2, 2026-09-04)

**Verdict: NOT ready for an alpha RC freeze.** *(As of the 2026-09-04 audit. **SUPERSEDED** by the item-1 + item-4
UPDATE at the end of this section: both behavioral RC blockers are now resolved/narrowed; read that update for the
current state.)* A read-only multi-bearing audit (workflow `wv1svy3pt`) mapped the
§3 P0 rows against the code, judged the §2A.3 invariants for non-vacuous enforcement, and checked the §9 DoD;
**every load-bearing claim below was then independently reproduced against the filesystem**, not taken on the
audit's word. The truth-honesty core is genuinely solid — but three RC conditions fail.

**RC blockers (verified):**

1. **G8 / standard §14.1 alias-unity — RED (behavioral, live-confirmed).** The standard (§14.1 lines 662–663,
   release gate §16 G8, the §17 CLI-unity probe) mandates that the legacy alias `synthesize` "MUST construct the
   same typed request as `recompile` and MUST NOT keep divergent defaults." It does not: `synthesize <t>
   --emit-request` vs `recompile <t> --emit-request` differ in `search_bounds.max_depth` (2 vs 3),
   `terminal_policy.commodities_enabled` (false vs true), `evidence_provider_selection` (DEFAULT_NETWORK vs
   DEFAULT_OFFLINE), and per-field `origins` (EXPLICIT vs DEFAULT) — reproduced live via `--emit-request`. And it
   is **vacuously green**: `tests/test_cli_canonical.py::TestCommandMatrixEqualRequestJson` loops only
   `compile`-vs-`recompile` (both on the one `_add_recompile_flags` builder) and NEVER invokes `synthesize` — so
   the full suite passes OVER the violation ([[vacuous-green-over-an-empty-subject]]). This brick adds a **live
   xfail guard** (`test_synthesize_is_request_equal_to_recompile_G8`) that runs `synthesize` through the
   equal-request assertion, making the violation VISIBLE and tracked (an XPASS will flag its resolution).
   **The FIX is an Operator design decision, deliberately not taken here:** either align `synthesize`'s defaults to
   `recompile`'s — which ERASES `synthesize`'s distinct download-and-go (network), poor-man's-commodity, and
   shallow-depth defaults, i.e. makes it a pure alias, and revises the `--offline`/`--poor-mans` flag semantics —
   OR formally revise the standard's "synthesize is an alias" mandate (§822). Both change user-facing behavior or
   the standard, so they are the Operator's call, not a unilateral tail-of-round edit.

2. **§9 DoD bullet 1 — UNMET (open Lane-A P0 rows, no recorded narrowing).** In §3, `SRCH-NO-01` (no renderer
   surfaces the four-outcome no-route matrix uniformly), `SRCH-DIG-01` (no shared cross-path request/result digest
   beyond the formula path), and the CLI/service rows `SVC-REQ-01`, `CLI-CAN-01`, `CLI-EXIT-01`, `CLI-ERR-01`,
   `CLI-JSON-01` are all `IN_PROGRESS`. Bullet 1 requires each P0 either `IMPLEMENTED_AND_VERIFIED` or a recorded
   narrower release contract; only `ID-PARSE-01` was reconciled (§2A.5). The underlying truth-honesty already holds
   on the tested public paths (incomplete never looks complete; incomplete-empty never reads as proof of absence —
   §9 bullet 5, independently confirmed), so the residual is uniform four-outcome LABELING and cross-path request
   identity, not a truth hole — but the rows must be closed or narrowed before a freeze.

**Invariant enforcement (audit bearing 2, spot-verified):** the §2A.3 invariants G1/G2/G4/G5/G6/G7/G8 are
non-vacuously enforced by live tests (each has a test that reproduces the exact failure mode it forbids). The one
gap is **G3 (provider locality)**: its operational half is proven (a new family composes through the UNCHANGED
search, found only with an extended `registry=`), but its architectural "never a rewrite of core recursion" half
is demonstrated once, not regression-guarded — the current core seams (`experiment/routes.py`, `compilation_ir.py`
`decompile_structure_to_ir`) all route through `registry.enumerate`, so the code obeys G3 today. **Not an RC
blocker;** a structural/AST guard is a named follow-on.

**Doc-truth defects fixed this brick:** (a) §2A.1 listed `ERR-EVIDENCE-01` under "Remaining" though §2A.2 marks it
`IMPLEMENTED_AND_VERIFIED` and `tests/test_err_evidence.py` passes — corrected; (b) §2A.4 cited the interchange
xfail as `…::TestScheduledProduct::…`, a node-id pytest reports "not found" — corrected to the real enclosing class
`TestObjectProductAndScheduledProduct` (`tests/test_laws.py:257`). **Doc-hazard flagged (not a false enforcement
claim):** a tri-modal "G" numbering collision — manifest §2A.3 `G1–G8` (G5 = identity monotonicity) vs standard §16
`G0–G8` (G5 = **stoichiometric invariance and route topology**, standard line 774) vs informal per-test docstring
"G" numbers. The prior flag also mis-stated this: `tests/test_g5_coverage.py` does **not** enforce standard-G5
either — verified against the code, it tests decomposition-**byproduct hazard** evidence coverage, which is the
standard's **G4** (evidence/provenance discipline) applied to hazard records and feeds **G7** (safety), matching
NEITHER "G5". **RESOLVED this brick (2026-09-04, freeze-checklist step 4):** the file is renamed
`tests/test_byproduct_hazard_coverage.py` (the "G5" token removed from the filename) with a corrected docstring, and
the canonical **§2A.8 G-numbering cross-reference** below is the single authority a "G5" grep should land on.

**Freeze checklist (the ordered path to a clean alpha RC):**

1. Resolve the `synthesize` G8 decision (align defaults to `build_recompile_request`, OR revise the §14.1/§822
   alias mandate). Then flip the xfail guard to a passing equal-request assertion covering `synthesize`.
2. Close `SRCH-NO-01` (uniform four-outcome no-route matrix across all renderers + `--json`) and `SRCH-DIG-01`
   (shared cross-path request/result digest beyond the formula path) — OR record the narrower release contract §9
   bullet 1 permits and mark them explicit named alpha limitations; flip the status rows only in the closing commit
   with test evidence.
3. Reconcile the residual Lane-A CLI/service P0 rows (`SVC-REQ-01`, `CLI-CAN-01`, `CLI-EXIT-01`, `CLI-ERR-01`,
   `CLI-JSON-01`): promote each to `IMPLEMENTED_AND_VERIFIED` or record the narrowing for any deferred scope.
4. Relabel `test_g5_coverage.py` / annotate the tri-modal "G" numbering so a "G5" grep is not misattributed.
5. Confirm every standard §16 gate `G0–G8` passes (G8 now green) and every §9 DoD bullet is satisfied or explicitly
   narrowed; re-run the full non-optional suite; only THEN cut the RC freeze/tag.

The interchange-law xfail (§2A.4) is contained architecture debt off the compiler path — NOT an RC blocker.

**UPDATE — RC blockers 1 & 2 resolved/narrowed (item 1 + item 4, this round; supersedes the "NOT ready" verdict's
two behavioral blockers, checklist steps 1–3):**

* **Blocker 1 (G8 / §14.1 alias-unity) — RESOLVED (item 1).** The Operator's decision: make the output
  reality-respecting, fit the ethos, and revise the standard. `synthesize` now threads every OMITTED knob as `None`
  through the ONE `build_recompile_request`, so `synthesize <t> --emit-request` is BYTE-IDENTICAL to `recompile <t>
  --emit-request` (offline provider, depth 3, commodities on — the reproducible, complete default), verified live
  by byte-diff. Its distinctive download-and-go behavior is PRESERVED as the EXPLICIT `--network` opt-in
  (origin=EXPLICIT; a live fetch is never the default; `--poor-mans` → `--no-commodities`/`--elements`, mirroring
  `recompile`). The standard was REVISED: §14.1 (aliases build the same request under equal flags AND no verb
  reaches the network by default — a live fetch is an explicit opt-in; its dated §13.2 provider snapshot stays a
  separate, still-open conformance item, the alpha value-caches but does not stamp it), release gate
  §16 G8, and the §18 migration note. The strict-xfail guard is now a LIVE PASS parametrized across the full
  command matrix (`test_synthesize_is_request_equal_to_recompile_G8`), plus a non-vacuous `--network`-splits-the-
  request test. Full suite green.

* **Blocker 2 (§9 DoD bullet 1) — CLOSED-OR-NARROWED (item 4):**
  - `CLI-CAN-01` → **IMPLEMENTED_AND_VERIFIED**: with item 1 the acceptance "command matrix gives equal request
    JSON" holds for ALL THREE aliases (compile/recompile/synthesize), not just compile-vs-recompile — the
    vacuous-green subject ([[vacuous-green-over-an-empty-subject]]) is closed; the matrix test parametrizes over
    `synthesize` too.
  - `SRCH-DIG-01` → **IMPLEMENTED_AND_VERIFIED**: the "shared request identity does not exist" clause is STALE —
    SVC-REQ-01 landed it and canonicalizes the reagent/stock inventory, so equivalent inventory ORDER now yields a
    byte-identical request AND an equal `result_digest` on the structural/material path (proven end-to-end,
    `tests/test_cli_canonical.py::TestInventoryOrderInvariance`) — the order-invariance the formula path already had.
  - `SVC-REQ-01`, `SRCH-NO-01`, `CLI-JSON-01` → **recorded narrower alpha contract** (§9 DoD bullet 1's second
    path; the truth-honesty invariant is independently confirmed on the tested public paths, so these residuals are
    NOT truth holes but bounded, named post-alpha polish): (i) SVC-REQ-01 — chemical-command request unity +
    alias-collapse are the alpha obligation (DONE, now including `synthesize`); decompile-side alias-collapse and
    convergent-DAG bench ranking are named post-alpha. (ii) SRCH-NO-01 — the four §8.3 no-route/candidate tokens
    are carried on every receipt (`standard_status`, SRCH-RCT-8.1 ✓); surfacing them UNIFORMLY across every human
    renderer is the named post-alpha labeling polish. (iii) CLI-JSON-01 — human/JSON agree on every semantic field
    (DONE); `affordability_frontier` stays present-and-empty until COST-VEC-01 (a named, honest alpha limitation).
  - `CLI-EXIT-01`, `CLI-ERR-01`: their acceptance (the §14.4 exit map + concise domain diagnostics without
    tracebacks) holds and is tested (ERR-EVIDENCE-01 + its red-team fold); they carry the same shared-JSON/
    affordability narrowing recorded above.

**Updated verdict (item 1 + item 4):** both behavioral RC blockers are resolved (1) or narrowed to named,
non-truth-hole alpha limitations (2). The residual freeze-checklist items are the doc-hygiene "G" relabel (4) and
the final gate/DoD confirmation run (5) — **no behavioral RC blocker remains on Lane A.** The Operator still owns
the freeze/tag decision.

**UPDATE — freeze-checklist steps 4 & the G3 guard closed, step 5 confirmed (2026-09-04, this brick):**

* **G3 architectural regression guard — BUILT (closes the §2A.7 "named follow-on"), then red-team-hardened.**
  `tests/test_provider_locality.py` (`d100c3e`; AST-based, red-team `evil-morty`, 6 findings, ALL folded pre-commit) asserts:
  (a) neither core-recursion file (`experiment/routes.py`, `compilation_ir.py`) references a family enumerator, a
  concrete `*Provider` class, OR a second-recursion entry point (`structure_decompose`/`ionic_decompose`), NOR
  dynamic-dispatches to a family via a `getattr`/`import_module`/`__import__` STRING (the string-literal fork a bare
  identifier scan misses; scoped to those call args so `getattr(self, name)` reflection is untouched); (b) the
  `registry.enumerate` seam is present on a `registry` receiver in each; (c) repo-wide, a family enumerator is
  referenced in CODE only by its defining module + the provider module(s) that call it. The policed inventory is
  **DERIVED from the live provider layer** (every `class *(TransformProvider)`; the package-level functions each
  provider's `enumerate_transforms` calls), so a family #5 lands auto-policed — closing the red-team's silent-drift
  (F2) and provider-relocation false-red (F3) gaps. AST-based on purpose: a family name in a docstring (as
  `routes.py` has for `capped_scissions`) is invisible; a real import/call/getattr-string is not. Non-vacuity: the
  derivation is asserted to rediscover the known 4 families (a floor), and the guard is watched to REDDEN on four
  planted fork vectors (import+call, module.attr, getattr-string, second-recursion) then GREEN on the clean tree.
  **Honest boundary (stated, not over-claimed — the red-team's F1):** a static guard CANNOT catch a wholly inline,
  hand-rolled family written into core with NO shared symbol; that residual is covered by G3's behavioral half (a
  real family is found only with an extended `registry=`, `tests/test_bond_order_edit.py`) and code review. So G3's
  architectural "never a rewrite of core recursion" half is now regression-guarded, within a named boundary.
* **Freeze-checklist step 4 (doc-hygiene "G" relabel) — DONE.** See the corrected doc-hazard note above + **§2A.8**.
* **Freeze-checklist step 5 (final §16 G0–G8 / §9 DoD confirmation run) — see the item-1c confirmation record after
  §2A.8.** The freeze/tag itself remains the Operator's call.

### 2A.8 Canonical "G" numbering cross-reference (resolves the tri-modal collision)

Three unrelated numbering schemes share the "G" prefix. **They are independent; a shared number means nothing.**
This table is the single authority a "G5" (or any "G") grep should land on.

| # | **Standard §16 gate** (release gates for `0.5.0a1`) | **Manifest §2A.3 invariant** (architectural law) |
|---|---|---|
| G0 | Baseline and version (suite green; `0.5.0a1` reported consistently across package/CLI/JSON/artifact) | *(no manifest G0)* |
| G1 | Identity (explicit name/SMILES/InChI/formula paths; same-formula isomers distinct; losses refuse/record) | Semantic request law (equal semantic request digests ⇒ same search/policies) |
| G2 | Search receipt (every result has a receipt; low caps ⇒ incomplete; only complete-empty ⇒ NO_ROUTE) | Structural forgetful square (every structural decompile projects to a valid formula-level transform) |
| G3 | Terminal policy (an exact terminal is not decomposed; commodities-off blocks shortcuts) | **Provider locality** (a new family = provider + tests + registry inclusion, **never** a core-recursion rewrite) — guarded by `tests/test_provider_locality.py` |
| G4 | Direction and evidence (decomp conditions don't attach to reversed assembly; no isomer borrow; free-text can't earn KNOWN) | Search honesty (provider exhaustion/budgets/rejections never vanish into one aggregate "complete") |
| G5 | **Stoichiometric invariance and route topology** (R≡nR intensive; scale-invariant lookups; spectators don't connect; DAG fan-out can't mint) | **Identity monotonicity** (a claim uses only layers its path perceived; forgetting a layer may weaken/refuse, never strengthen) |
| G6 | Material and affordability honesty (identity-only ⇒ no invented amount/ceiling/price; unknown costs stay unknown) | Evidence separation (a formal transform witness ≠ a sourced reaction record; algebraic reversal doesn't reverse conditions) |
| G7 | Dossier readiness and safety (route dossier not full procedure; missing hazards can't clear safety) | Material non-substitutability (a structural identity match ≠ a stock-material fitness match) |
| G8 | CLI/service unity (aliases serialize equal requests under equal flags; no verb networks by default; codes/diagnostics) | Failure separation ("unknown evidence" / "unsupported model" / "incomplete search" / "invalid input" / "internal failure" stay distinct) |

**Guarding tests (verified this brick, not asserted):** **manifest §2A.3**-G3 provider-locality (NOT standard-G3, which is terminal policy) → `tests/test_provider_locality.py`;
manifest-G5 identity-monotonicity → `tests/test_identity.py` / `tests/test_id_stereo.py` (loss records → `tests/test_ir_loss.py`);
decomposition-byproduct hazard evidence (standard-G4 applied to hazards, feeds standard-G7) → `tests/test_byproduct_hazard_coverage.py`
(**formerly `test_g5_coverage.py`** — the renamed file whose old "G5" self-label caused the collision). The remaining
gates are guarded distributedly across the suite and the standard §17 falsification matrix; this table fixes the
NAME collision, it does not claim a single file per gate where the guard is genuinely distributed.

### 2A.9 Item-1c: the final §16 G0–G8 / §9 DoD confirmation run (2026-09-04)

Freeze-checklist step 5. This is a **confirmation of readiness**, not the freeze — the freeze/tag remains the
Operator's call. Every claim below was checked against the code/run this brick, not asserted.

**Suite (the final tree, `.venv`, `-p no:cacheprovider`, exit 0):** `3650 passed, 14 skipped, 1 xfailed`
(`suite_item1c.log`; +11 vs the 3639 base = the new `tests/test_provider_locality.py`; the 1 xfail is the
interchange-law architecture debt of §2A.4, off the compiler path — not an RC blocker).

**Standard §16 gates G0–G8:**

| Gate | Standard §16 name | Confirmation |
|---|---|---|
| G0 | Baseline and version | `0.5.0a1` reported consistently — package `__version__`, `python -m smartchem --version` (`smartchem 0.5.0a1`), `pyproject.toml`, and the `--json` fixtures all agree; `python -m smartchem` and the console script share one `__version__` (`cli.py:569`). Suite green. |
| G1 | Identity | explicit name/SMILES/InChI/formula paths (`ID-PARSE-01` ✓); same-formula isomers distinct (`CANON-KEKULE-01` ✓); losses refuse/record (`ID-LAYER`/`ID-STEREO` ✓). |
| G2 | Search receipt | every result carries a receipt; low caps ⇒ incomplete; complete-empty ⇒ `NO_ROUTE_IN_DECLARED_SPACE`; inventory order digest-invariant (`SRCH-RCT-8.1`, `SRCH-DIG-01`/`TestInventoryOrderInvariance` ✓). |
| G3 | Terminal policy | exact terminal not decomposed; commodities-off blocks shortcuts; structure search never terminates on formula-only isomer equality (`TERM-POL`/`terminal_policy` tests ✓). |
| G4 | Direction and evidence | reversed assembly doesn't inherit decomposition conditions; no same-formula isomer borrow; free-text can't earn `KNOWN`; unsupported evidence fails construction (`EVD-KEY-01`, `G4`/evidence tests ✓). |
| G5 | Stoichiometric invariance and route topology | R≡nR intensive; scale-invariant lookups; spectators don't connect; DAG fan-out can't mint (`DAG-FLOW-01` exact LP; §17 primitive-invariance/linear-continuity probes ✓). |
| G6 | Material and affordability honesty | identity-only ⇒ no invented amount/ceiling/price; unknown costs stay unknown (`STOCK-01`/`SHOP-LEAF-02`/`sourcing` ✓). **`affordability_frontier` stays present-and-empty** — a named, honest alpha limitation until `COST-VEC-01` (§2A.1 Lane C). |
| G7 | Dossier readiness and safety | sparse output renders as a route dossier, not a runnable procedure; missing hazards can't clear safety; no auto-`PROCEED_UNATTENDED` (`handling`/dossier tests ✓). |
| G8 | CLI/service unity | aliases serialize equal requests under equal flags **incl. `synthesize`** (item 1, the live `test_synthesize_is_request_equal_to_recompile_G8` pass); no verb networks by default (`--network` opt-in); §14.4 codes; concise domain diagnostics; human/JSON agree (`CLI-CAN-01`/`CLI-EXIT-01`/`CLI-ERR-01`/`CLI-JSON-01` ✓). |

**Manifest §9 Alpha-DoD:** every P0 row is `IMPLEMENTED_AND_VERIFIED` or carries a recorded narrower alpha contract
(§2A.7 item-1+4 UPDATE); the full non-optional suite + new adversarial tests pass; canonical and legacy CLIs use the
one typed service + version; incomplete never looks complete and incomplete-empty never reads as proof-of-absence
(§9 bullet 5, retested); reverse equations don't inherit forward evidence; scaling can't change intensive verdicts;
identity-only commodities invent no purity/quantity/price/fitness; sparse output is a dossier with missing operations
visible; no route is auto-authorized safe/unattended. The **release-declaration** bullet ("true for every public code
path") and the affordability/dated-provider-snapshot items are the named, honest alpha limitations (Lane C /
`COST-VEC-01`, and the §13.2 dated snapshot §16-G8 records as separate-and-open) — not truth holes.

**Verdict:** no behavioral RC blocker remains on Lane A; freeze-checklist steps 1–5 are addressed. The alpha RC
freeze/tag is the Operator's to cut.

### 2A.10 Uptake record — COST-VEC-01 (2a): the verified USGS prices wired into the material layer

Lane C. The item-5 price-data block was LIFTED (the frozen USGS seed exists); 2a spends that data: each verified
price becomes a section-10.4 `CostObservation` (dated AND sourced, never invented) attached to the compiler's
commodity materials.

```text
ID:      COST-VEC-01 (2a, the price-wiring half; the Pareto ENGINE is 2b)
commit:  72cdf7e (feat) + this docs record
files:   smartchem/experiment/commodity_pricing.py (new), smartchem/experiment/stock.py,
         tests/test_commodity_pricing.py (new), tests/test_stock.py
```

- `CostObservation` gained a required `unit` (schema `v1alpha1`→`v1alpha2`): section 9.2 requires the reported
  value's units be retained (a bare number is nonconformant), so amount+currency+unit are the full price.
- `commodity_pricing.py` is the package-resident price authority (the package cannot import `experiments/`),
  transcribed from the frozen seed and pinned to it by a both-directions cross-check over EVERY sourced field
  (formula, form, price, basis, chapter) — a drifted number OR a fabricated basis fails the test.
- `cost_observation_for(molecule)` keys by canonical structure (`commodity_for`) AND verifies the matched
  molecule's composition equals the priced form's — no same-formula-isomer or repointed-name price borrow;
  unpriced/unregistered → `None` (honest UNKNOWN). The price is a SPECIFIC named USGS form (NaCl→rock-salt
  52.95, Na2CO3→soda-ash 169.35 $/t), never the numeric min across incomparable forms (brine, a solution, is
  the cheapest NaCl value and is deliberately not attached).
- `stock_material_from_commodity` carries the price (lazy import breaks the stock↔pricing cycle). Lime/sulfur
  are priced in the seed but have no registered `CommodityReagent`, so they are transcribed (for the
  cross-check) but not attached — adding a commodity to the retrosynthesis inventory is a separate,
  behaviour-affecting change, out of this brick.
- Red-team (`evil-morty`): 4 findings, all reproduced + folded (basis/chapter pinned; structure-sound join;
  import-time form validation; docstring corrected). Blast-radius suite (stock/commodity/sourcing/reagents): 73
  passed; full-suite confirmation recorded on push.

### 2A.11 Uptake record — COST-VEC-01 (2b): the section-10.4 vector-affordability core

Lane C. The affordability ENGINE the row named, as a tested primitive — a multi-objective cost vector + a Pareto
frontier, never a hidden scalar (§10.4).

```text
ID:      COST-VEC-01 (2b, the engine core; the route-level service wiring is the follow-on)
commit:  21264cd (feat) + this docs record
files:   smartchem/experiment/affordability.py (new), tests/test_affordability.py (new)
```

- `CostVector`: the §10.4 axes (cash, access, evidence-tier, equipment, quantity, energy, labor, preprocessing,
  analytical, waste-disposal) + hard-constraint blockers. Every axis is `None` when UNKNOWN (§10.4 "unknown values
  remain unknown"; a bare 0 would be a fabricated free lunch). Only axes with real data are populated today (cash
  from a 2a `CostObservation`, access from a commodity's availability); the rest stay UNKNOWN, not invented.
- `dominates`/`pareto_frontier`: Pareto dominance with two honest rules — a HARD BLOCKER DOMINATES COST (a clean
  option beats a hard-blocked one at any price, even all-UNKNOWN; a hard constraint is never traded for cost, G6),
  and UNKNOWN IS INCOMPARABLE (a vector cannot claim to beat, or be beaten by, an axis it does not measure), so the
  frontier refuses to over-rank on absent data. Proven a sound strict partial order (irreflexive, antisymmetric,
  acyclic → order-independent frontier) THREE ways: a hand proof, a 20k-triple brute force, a committed property
  test; the red-team re-proved it exhaustively over the 3-axis lattice.
- `basket_cost_vector`: aggregate a route/basket's commodity leaves into one vector over the 2a prices — cash is the
  sum, KNOWN only if every leaf is priced AND commensurable (else UNKNOWN, never an under-count); access is the
  worst leaf, UNKNOWN if any leaf is not a known commodity; an empty basket is UNKNOWN, not free.
- Red-team (`evil-morty`): order theory sound (exhaustive); 2 LOW folded — the unmapped-availability fail-open
  (fail-SAFE + a coverage test that fails-fast on a future `Availability` member) and the untested incommensurable-
  unit path (a monkeypatched test) — + the hard-blocker/UNKNOWN precedence documented. `tests/test_affordability.py`:
  21 passed.
- **Boundary (named, not a truth hole):** the LIVE route-level wiring — populating
  `CompilationResponse.affordability_frontier` from each ranked route's commodity basket — is the follow-on (it needs
  the response schema bump + the `affordability_frontier != ()` guard relaxation + golden regen). This module is the
  correct, tested engine that wiring will call; it does not yet populate the service response. The mostly-UNKNOWN
  non-cash axes are honest: the engine ranks on what is measured and refuses to invent the rest.

### 2A.12 Uptake record — ROUND 5 (2026-09-04): the top-5 next-steps landed (SRCH-NO-01, COST-VEC-01-wire, SNAPSHOT-13.2, IR-COMMUTE-01, RC-STATUS-RECONCILE)

Each brick ran the full cycle (design → 4-way Citadel-Rick recon → build → blind `evil-morty` red-team, refute-by-default → REPRODUCED every finding → folded → verified). Response schema `v1alpha3 → v1alpha6` (descriptor `v1alpha5 → v1alpha8`), monotonic one bump per response-shape change; goldens regenerated and eyeballed to the intended diff only. `result_digest` was left UNCHANGED by every brick — the new fields are dated data / provenance, not search identity.

* **SRCH-NO-01 — CLOSED (§3 flip → `IMPLEMENTED_AND_VERIFIED`).** A pure `search.section_8_3_label(complete, count)` leaf + `SECTION_8_3_NOTE` + the four §8.3 tokens; a DERIVED `CompilationResponse.search_space_status` (from the IR's `complete_within_bounds`/`candidate_count`) surfaces the four-outcome matrix UNIFORMLY across the recompile + decompile `--json` and human renderers AND the compile Dossier. Red-team folds: the "uniformly everywhere" claim was an overclaim (the Dossier's complete-with-route case emitted no token) → the Dossier now emits all four + the claim narrowed to "every PUBLIC CLI renderer"; the shared note advised `--cut-budget/--max-routes/--max-depth` which don't exist on `decompile` → made flag-agnostic. Truth-core verified: an incomplete-empty search NEVER reads as a complete no-route on any tested path.
* **COST-VEC-01-wire — the LIVE route-level frontier (COST-VEC-01 → still `IN_PROGRESS`; coupled refusal remains).** `AffordabilityFrontierEntry(Digestible)` (route_digest + CostVector) + a new byproduct-safe `ExperimentRoute.leaf_inputs` (reactants produced by NO step) → `basket_cost_vector` → `pareto_frontier` populate `CompilationResponse.affordability_frontier` on a routes-mode search; the `!= ()` guard relaxed to a typed-tuple check (the pinned rejection test replaced). Red-team folds (both reproduced): the SIGNAL GATE was checked PRE-dominance, so G6 could strip the only signal-bearing entry and leave a blank-vector list → gate moved POST-dominance (blank survivors → `()`); `leaf_inputs` excluded step TARGETS only, so a re-consumed byproduct was double-billed → now excludes ALL step PRODUCTS; the wire test was vacuous on the two obvious mutants → made non-vacuous (asserts a non-empty linked Pareto frontier + a byproduct-exclusion regression + the post-dominance-gate regression). Named POST-ALPHA follow-ons: the coupled/underdetermined shopping refusal (COST-VEC-01-coupled); a quantity/stoichiometry axis (the basket is per-unit today); widening priced commodities past NaCl/Na2CO3.
* **SNAPSHOT-13.2 / G8 — the dated provider snapshot.** `ProviderSnapshot` (provider_ids, record_count, DETERMINISTIC `content_digest` over the sorted fetched-record digests, `fetched_at` wall-clock, allow_network) + `provider_snapshot()` factory; `autoload_stability` stamps the returned `StabilityTable` (a `compare=False` field — the table digest and cache are UNCHANGED) IFF a LIVE fetch produced a record (never a seed/cache/offline read); `CompilationResponse.provider_snapshots` (typed guard, serialize, `run_compilation(..., provider_snapshots=)` seam) EXCLUDED from `result_digest`; the synthesize HUMAN dossier renders the snapshot of the fetch that fed its grading. Red-team folds (the decisive one): the `--json` path had fetched a snapshot the offline-deterministic machine search does NOT consume — provenance for a result that ignored it, disagreeing with the human path's species set → **removed** (the honest state: the machine `--json` response depends on no fetch, so its `provider_snapshots` is present-and-empty, a named limitation; the field + `run_compilation` kwarg remain as the §13.2 shape + the seam for when the machine search consumes fetched evidence). Also: narrowed the broad `except`; added the two missing anti-fabrication tests (cache-hit → None, empty-fetch → None); render says "consulted" not "from".
* **IR-COMMUTE-01 — the cross-producer forgetful relation (audit §7.3 / B0).** A differential test: `forget(D_structure(S)) ⊆ D_formula(forget(S) | closure)` for the BOND_ORDER_EDIT family (the one family whose `forget()` yields a formula-layer `DecompositionEdge` `decompile_to_ir` can emit), the formula inventory DERIVED from the structural products, with two genuine negative controls (drop the precursor → not a subset; wrong family → not a subset). Red-team folds: the headline claimed `==` between "independent" producers → corrected to `⊆` within a derived closure (the honest content is that `BondOrderEdit.forget()`'s bucketing convention agrees byte-for-byte with `admissible_edges`); the wrong-family control's "by edge domain" mechanism was over-determined → the claim narrowed to "a different family does not commute" (the mechanism is not isolated); the filter comment corrected (H2 is single-element, inert in the inventory). Boundary NAMED: capped-scission's formula producer (`mediated_decompose`) is unwired and heterolytic/redox have none — extending the relation to them is the remaining IR-FORGET-01 follow-on; coverage is a single instance (ethane), a family sweep is a follow-on.
* **RC-STATUS-RECONCILE (§9 DoD bullet 1).** The Lane-A P0 §3 cells that were governed-as-done-or-narrowed by §2A.7/§2A.9 but still literally read `IN_PROGRESS` are flipped WITH test evidence: `SVC-REQ-01`, `CLI-EXIT-01`, `CLI-ERR-01`, `CLI-JSON-01`, `SRCH-NO-01` → `IMPLEMENTED_AND_VERIFIED`. `CLI-ERR-01`'s named nonfinite-float-constraint remainder is CLOSED non-vacuously (a nonfinite/non-positive T/P constraint → clean exit-2 domain error via the model-layer `PhysicalBounds` rule; `tests/test_cli_err.py::TestNonfiniteConstraintIsACleanDomainError`); full ID-PARSE-01 kinds remain a named post-alpha follow-on. So §9 DoD bullet 1 (every P0 `IMPLEMENTED_AND_VERIFIED` or a recorded narrowing) now reads TRUE in the ledger, not only in the §2A projection.

**Suite (the final tree, `.venv`, `-p no:cacheprovider`, exit 0):** `3715 passed, 14 skipped, 1 xfailed` (+31 vs the 3684 base = the four new test files `test_srch_no.py` / `test_affordability_wire.py` / `test_provider_snapshot.py` / `test_ir_commute.py` plus the strengthened regressions). The 1 xfail remains the §2A.4 interchange-law architecture debt (off the compiler path). One stale no-route wording assertion (`test_routes.py::test_cli_reports_no_route_loudly`) was updated to the §8.3 token in the same round.

**Effect on §2A.9's gate rows (addendum):** **G6** — `affordability_frontier` is now POPULATED (a §10.4 Pareto frontier over the ranked routes; empty only when no route carries affordability signal — honest, no longer "present-and-empty until COST-VEC-01"). **G8** — live-fetched provider data now carries a dated §13.2 snapshot (`autoload_stability` stamps the table; the synthesize human dossier renders it); the machine `--json` response's `provider_snapshots` is present-and-empty because the alpha machine search consumes no fetched evidence (a named limitation, not a truth hole). The release-declaration's two named limitations (affordability wiring, dated snapshot) are thereby DISCHARGED for the surfaces that exist; the machine-search-consumes-fetched-evidence path is the remaining named follow-on. No behavioral RC blocker on Lane A; the freeze/tag stays the Operator's.

### 2A.13 Uptake record — ROUND 6 (2026-09-04): the alpha SHIPPED (`0.5.0a1`) + the 5 post-alpha next-steps

**Alpha SHIPPED (item 1, RC-FREEZE-01).** The ROUND-5 merge gate was re-verified green on the clean tree at `beeab52`, then `main` was fast-forwarded `efbe54c → beeab52` and pushed, and the annotated tag **`0.5.0a1`** was cut at `beeab52` (the Lane-A-green point) and pushed. `main == origin/main == beeab52`; the alpha release candidate is out. The four post-alpha ROUND-6 bricks then landed ON TOP of the tag, on the branch (they are Lane B/C work, deliberately POST the alpha marker); merging ROUND 6 → main is the Operator's separate call.

Each brick ran design → build → blind `evil-morty` red-team (refute-by-default) → REPRODUCED every finding → folded → targeted-green → ruff → commit. `result_digest` was again left UNCHANGED by every brick (new fields are dated data / provenance, not search identity).

* **#5 IR-COMMUTE multi-family lift (Lane B) — `7939eb4`.** Extends the IR-COMMUTE-01 forgetful square from BOND_ORDER_EDIT to **CAPPED_SCISSION**: `forget(D_structure_capped(S)) ⊆ mediated_decompose(forget(S) | closure)` — a capped scission forgets to a `MEDIATED_EDGE`, so its formula-side oracle is `decompiler_mediated.mediated_decompose` (not `decompile_to_ir`), fed the derived product inventory PLUS a `medium` derived from the structural reagents (DEFAULT single-cut registry). Red-team fold (reproduced): the cross-producer digest-⊄ assertions were VACUOUS class-tag tautologies (`contracts.canonical_payload` embeds the fully-qualified class, so MediatedEdge and DecompositionEdge digests are disjoint by construction regardless of `forget()` convention — a wrong-convention mutant survives) → replaced with the load-bearing same-class positive subsets + the TYPE distinction on `projection_kind`; the docstring overclaim corrected. Boundary NAMED: k≥2 multi-cut conjectured; heterolytic/redox have no formula producer (IR-FORGET-01 follow-on).
* **#3 COST-VEC-01-coupled (Lane C; COST-VEC-01 advances, still `IN_PROGRESS`) — `09fc64d`.** `basket_cost_vector` collapsed cash to a bare UNKNOWN on any unpriced leaf, discarding the priced leaves' lower bound. Now a partially-priced basket reports a **`cash_floor`** — the sum of the priced, commensurable leaves, a PROVEN lower bound — never a fabricated total (audit §11.2: refuse the coupled scalar, report the honest range). The cash axis is now INTERVAL-valued in `dominates` (`_cash_interval`: known `[K,K]`, floor `[F,+∞)`) with NECESSARY dominance (`a_hi ≤ b_lo`), so a known-cheap route dominates a floored-dear one while a floor never claims a cost ordering it cannot guarantee. `has_cost_signal` counts a floor. Frontier-entry schema `v1alpha1 → v1alpha2`, response `v1alpha6 → v1alpha7`, descriptor `v1alpha8 → v1alpha9`; **`result_digest` UNCHANGED** (the frontier is excluded). Also fixed a latent cross-currency sum. Red-team: the interval order was PROVEN sound (2M-triple sweep + hand proof, 0 axiom violations, no fabrication, no misordering); two stale-doc folds (the module boundary still claimed the wiring unbuilt though ROUND 5 shipped it; the `dominates` docstring omitted the interval semantics). Named follow-ons: a per-unit quantity/stoich axis; a per-currency partial floor.
* **#2 THERMO-UNC-01-widen (Lane C) — `9afad8d`.** Wires the sourced ± the ROUND-4 σ-propagation needed but the live seed lacked: **N2's S° ± (0.004)** and **ammonia's ΔfH°+S° ± (0.35/0.05)** from the frozen, cross-checked CODATA seed (they ARE CODATA key values — the earlier NIST citation understated them), closing the gap the frozen seed's own docstring named as "the next brick". Widens PAST the CODATA set with **methane's ΔfH° ± (0.3)** — the Gurvich/JANAF value via the NIST WebBook, cross-checked against JANAF (Chase 1998, −74.87, within ±0.3); methane's S° keeps an honest `None` (the statistical vs calorimetric sources disagree), so it keeps σ(ΔG) UNKNOWN for any reaction using it. Effect: **Haber flips from σ(ΔG)=UNKNOWN to INFORMATIVE** (σ(ΔG) = 0.7006 kJ/mol, the exact quadrature); the no-σ→UNKNOWN honesty property moves to methane combustion. All ± are `compare=False` → VALUES byte-unchanged, no digest, no golden, no derived-ΔG test moves. A new live↔frozen cross-check pins the seed's σ AND value to the frozen source. Red-team: CLEAN BILL (fabrication angle first — every σ traced to a live/frozen source, no provenance staple, cross-check non-vacuous, honesty property genuinely on CH4); folded its residual (the cross-check now pins values too). Named follow-on: the organic past-CODATA widen is data-blocked (free-source S° ± for organics are too thin — NIST methanol is a ±10 nine-value average), so no tight σ is fabricated.
* **#4 PHASE-CHANGE-SIGMA (Lane C) — `1be1564`.** `PhaseChangeRef` gains sourced ΔH/ΔS ± (`compare=False`, guarded > 0 or None); `resolve_thermo` propagates the condensed σ PER LEG in quadrature and lifts the ROUND-4 lower-bound caveat ONLY when BOTH legs are sourced (proven correct and non-vacuous via an injected both-± ref — mutating either leg keeps the caveat). Ethanol's ΔvapH carries a sourced ± (0.4, the NIST inter-study band); paracetamol's ΔsubH ± stays None (the 117.9 Picciochi vs 138±3 Vecchio spread is a ~20 kJ/mol method disagreement — no tight ± honestly sits on the chosen value). Red-team: the math HELD (quadrature form correct, lift non-vacuous, zero value churn) but two REAL provenance folds — ethanol's ± was miscited to Majer & Svoboda (whose datum is 38.56@351.5 K), corrected to NIST's own 12/13-study average; naphthalene's ±5 was spliced onto 72.6 (it belongs to NIST's AVG value 71) AND `resolve_thermo` returns None for the fused aromatic so it was dead metadata, dropped; the "one sigma" overclaim corrected. HONEST boundaries recorded: the enthalpy-leg narrowing is small on today's seed (±0.4 vs a ~9.8 group band, ~25:1) so the mechanism's payoff is the LIFT once a sourced ΔS ± lands (THERMO-PHASE-ENTROPY-SIGMA follow-on); the quadrature's independence premise (group-band model error vs sublimation measurement) holds unless a Benson gas ref was back-computed from its own Δsub, which would slightly under-estimate — immaterial while σ_gas dominates.

**Suite (the final tree, `.venv`, `-p no:cacheprovider`, exit 0):** `3734 passed, 14 skipped, 1 xfailed` (+19 vs the 3715 ROUND-5 base = the new capped-scission commuting tests, the cash-floor unit + partial-order-with-floor coverage, the widened-σ + live↔frozen cross-check, and the phase-change-σ propagation/lift tests). The 1 xfail remains the §2A.4 interchange-law architecture debt (off the compiler path).

### 2A.14 Uptake record — ROUND 7 (2026-09-04): ROUND 6 merged to main + the next four best-next-steps

**ROUND 6 merged to main (item 1).** `main` was fast-forwarded `beeab52 → a1d15d7` (the delta since the ROUND-6 3734-green run was docs-only, so the gate covered it) and pushed; `main == origin/main == a1d15d7`. The alpha tag `0.5.0a1` stays at `beeab52` (ROUND 6/7 are post-alpha Lane B/C). The three ROUND-7 bricks then landed on the branch; merging ROUND 7 → main is the Operator's separate call.

Each brick ran 1–2 Citadel recon → build → REPRODUCED the recon finding myself → blind `evil-morty` red-team → folded → verified. `result_digest` again untouched by every brick.

* **#3 IR-COMMUTE k≥2 + the redox square (Lane B) — `82ba80f`.** (A) The capped-scission square is closed past the DEFAULT single cut: methanol+water under `max_reactant_cuts=2` yields a genuine k=2 projection (water consumed at multiplicity 2) that commutes into `mediated_decompose` ONLY at `max_reagent_instances=2` (a free non-vacuity control -- it is ABSENT at the single-cut default). (B) A THIRD family joins the relation: `redox_edges` (new, `structure_descent.py`) is the formula-layer analogue of `redox_couples`; redox is charge-only and mass-trivial (the oxidized formula is fully determined by the reactant atoms + n, so there is NO inventory/medium/search), and the square closes at `==` (set equality), stronger than the neutral families' `⊆`, proven for Na and NO. Red-team: CLEAN BILL (k=2 genuine, the `==` content-load-bearing, the two `8*atom` ceilings provably non-divergent since `sum(formula.counts) == len(atoms)`); folded two honesty nits (corrected the `==` mechanism comment -- charge bugs raise at ElectronTransferEdge's certificate, count bugs fail the set -- and dropped the vacuous "cross-family type-disjointness" claim from the docstring, a class-tag consequence). Heterolytic's formula producer needs a real atom-partition + charge-assignment search -- named follow-on, strictly more code than redox.
* **#4 COST-VEC-01 quantity/stoich axis (Lane C) — `8ff1aaa`.** `_route_material_quantity` populates the (previously-always-null) `material_quantity` axis with the route's total external-leaf MOLES per mol product -- a conserved 100%-efficiency LOWER BOUND from `dag_shopping_requirement(SynthesisDAG.of(*route.steps), 1)` (by-products credited) -- and the axis enters Pareto dominance (methyl acetate now ranks its two routes 2.0 vs 3.0 mol/product, dropping the heavier one, a discrimination the per-unit cash axis could not make). HONEST scope: a MOL count, NOT quantity-weighted cash -- weighted cash needs a molar-mass + price-unit-conversion layer this code lacks and treats as opaque (the kg-vs-ton incommensurability test proves it), a named follow-on. Response per-value `v1alpha7 → v1alpha8`; `result_digest` UNCHANGED (the frontier is excluded); descriptor stays `v1alpha9`. Red-team fold (reproduced): `except DAGError` was too NARROW -- `dag_shopping_requirement`'s balance check raises `CeilingError`, a SIBLING of `DAGError` (not a subclass), on a degenerate no-net-species step (an identity `2 H2O -> 2 H2O` route is a VALID DAG), which would crash the whole response; widened to `(DAGError, CeilingError)` -> honest None. Latent (0/117 search routes reach it) but the crash is real.
* **#2 THERMO widen (Lane C) — `502042e`.** The named ORGANIC widen is DATA-BLOCKED and was NOT faked: organic S° uncertainties are unreachable via the free tools (NIST WebBook gives BARE organic S° -- ethylene 219.32, ethane S° not even listed -- with no ±; ATcT, which does carry S°+±, 403s on fetch). Per §10.4 no tight organic S° σ is fabricated -- the block is the recorded finding. What IS delivered: two more CODATA key values with BOTH σ (fetched + cross-checked, NIST CODATA-Review tags vs Chase), added to the frozen seed (`FROZEN_HASH` regenerated) and the live seed -- HCl (−92.31 ± 0.10 / 186.902 ± 0.005) and Cl2 (element ref, 223.081 ± 0.010). These also FIX broken inorganic thermo: `resolve_thermo(HCl)` previously fell through to a degenerate Benson estimate (0/0) and `resolve_thermo(Cl2)` CRASHED (a negative group-additivity S°); the sourced rows are found by `for_formula` FIRST. Effect: `H2 + Cl2 -> 2 HCl` now has an INFORMATIVE σ(ΔG) = 0.20 kJ/mol. All ± compare=False (zero value/digest churn); the live↔frozen cross-check now pins nine species (σ AND value). Named follow-on: the organic widen awaits an ATcT bulk pull (if the 403 is worked around) or a JANAF S°-uncertainty source.

**Suite (the final tree, `.venv`, `-p no:cacheprovider`, exit 0):** `3745 passed, 14 skipped, 1 xfailed` (+11 vs the 3734 ROUND-6 base = the k≥2 capped + redox `==` commuting tests, the material_quantity unit/dominance/frontier + CeilingError-None tests, and the HCl/Cl2 resolve-to-sourced + H2+Cl2 informative-σ + widened cross-check tests). The 1 xfail remains the §2A.4 interchange-law architecture debt (off the compiler path).

### 2A.15 Uptake record — ROUND 8 (2026-09-04): the ROUND-7 report's items 2/3/4 (branch)

The three named ROUND-7 next-steps landed on the branch (post-alpha Lane B/C; the alpha tag `0.5.0a1` stays at `beeab52`). Each brick: 1–2 Citadel recon → build → REPRODUCED every finding myself → blind `evil-morty` red-team (refute-by-default) → folded → verified. `result_digest` untouched by all three (the affordability frontier is excluded; the thermo seed is not wired). Merging ROUND 8 → main is the Operator's separate call.

* **#4 Heterolytic FORMULA producer — the 4th/last IR-COMMUTE family (Lane B) — `79890dc`.** `heterolytic_formula_edges(reactant: Formula)` is the formula-layer analogue of `heterolytic_scissions`: an atom-multiset 2-partition + localized-charge search (pairs `(q-1,1)`/`(-1,q+1)`, mirroring the structure producer) building `ChargedDecompositionEdge`s BYTE-IDENTICALLY to `HeterolyticScission.forget()`. The forgetful square `{h.forget()}` closes at `⊆` (NOT `==`): the graph is forgotten, so the producer OVER-produces partitions no order-1 bridge realizes (the `H2|O` split of water a real O-H cut never makes) — the honest relation, like bond-order/capped, unlike redox's search-free `==`. Budget + `complete` flag (W2). All four transform families (bond-order/capped/redox/heterolytic) now close the commuting square. Red-team: CLEAN BILL on the core claim (⊆ soundness over 15 molecules + 24 charged cases, MISSING=0; byte-identity; budget exact). Folded 2 honesty nits: a DEAD charge-conservation assert (the `ChargedDecompositionEdge` certificate already RAISES on non-conservation — a check derived from its own subject) → a falsifiable localized-signature check; added charged-reactant coverage. `test_ir_commute.py` 11/11.
* **#3 Molar-mass + price-unit LAYER + quantity-weighted cash floor (Lane C) — `6943e35`.** New `smartchem/experiment/units.py`: KNOWN-physics conversions that FAIL to UNKNOWN, never a fabricated factor. `molar_mass` sums the sourced IUPAC/CIAAW standard atomic weights (`None` for any mass-number-only radioactive/synthetic element); `grams_per_unit` uses DEFINITIONAL mass-unit factors (SI tonne, 1959 international pound), `None` for a non-mass denominator; `price_per_gram`/`price_per_mol` and `grams_to_moles`/`moles_to_grams` (the SHOP-LEAF bridge). Wired: `basket_cost_vector(weighted_cash_leaves=...)` emits a quantity-weighted `cash_floor` (per-leaf moles × `price_per_mol`), an INFORMATIONAL per-mol-of-product material-cost lower bound; `service._affordability_frontier` passes the per-leaf shopping requirement. Gated — the default call is byte-identical (zero churn). Red-team: 4 findings, ALL reproduced + folded. (1) MEDIUM soundness: `dominates` compared cash ACROSS denominations (`$5/metric-ton` "dominated" `$10/mol-product`) → the `unit` field is now LOAD-BEARING on the cash axis (a different denomination is incomparable, like an unknown). (2) the weighted floor is honestly an INFORMATIONAL bound, NOT a dominance ranker (floor-vs-floor is incomparable by the necessary-dominance rule; `material_quantity` does the ranking) — overclaim corrected. (3) two stale docstrings. (4) a negative-moles guard. `test_units`/`test_affordability` 89/89.
* **#2 Organic thermo — both-σ gate CONFIRMED CLOSED + the enthalpy-σ half (Lane C) — `ae22715`.** The named organic widen's gate is CLOSED, four walls verified by live fetch: ATcT is behind a Cloudflare JS challenge (headless-unreachable), NIST gives organic S° BARE, Burcat carries ΔfH°±σ but NEVER an S° uncertainty, and NIST-JANAF's both-σ "Ten Organic Molecules" covers the wrong species. σ(ΔG) for these organics stays UNKNOWN and is NOT faked (§10.4). Delivered: `experiments/burcat_atct_seed.py`, a frozen dated SELF-VALIDATING seed of the achievable ENTHALPY half — methanol/ethanol/acetic-acid gas ΔfH°±σ from ATcT (quoted in the Burcat record, reproduced by my own 2.3 MB fetch, all three competing-value decoys dodged) — plus a NASA-7-DERIVED S° that recomputes from the record's own committed low-T coefficients AND cross-checks vs NIST within 0.36%. NOT wired into `data/thermo.py`: a gas seed collides with the existing LIQUID autoload path on the `(formula,name)` key and would churn ~8 test files, for a wire that cannot unblock σ(ΔG) anyway — a named next brick (resolve the phase-key + autoload interaction). Red-team: every ΔfH°/uncertainty/coefficient traced EXACTLY to the source file, no fabrication, gate claim confirmed against the file. Folded 4 guard-honesty nits: `validate()`'s 1% cross-check is a GROSS sanity gate (a subtle self-consistent coefficient slip can pass), not a transcription proof — overclaim corrected (the real guarantee is the commit-time audit + `FROZEN_HASH`); made the gate report a real structural computation not a literal; fixed a nonexistent-field docstring reference + a typo. `test_burcat_atct_seed.py` 14/14.

**Suite (ROUND 8 final tree, `.venv`, `-p no:cacheprovider`, exit 0):** `3785 passed, 14 skipped, 1 xfailed` (+40 vs the 3745 ROUND-7 base). The 1 xfail remains the §2A.4 interchange-law architecture debt (off the compiler path).

**Uptake record — ERR-EVIDENCE-01, the reoriented Lane-A first brick** (`ERR-EVIDENCE-01` `TODO` →
`IMPLEMENTED_AND_VERIFIED`; the failure/unknown separation the audit's §10 / G8 demands):

```text
ID:            ERR-EVIDENCE-01 (an internal provider fault is not a scientific "conditions unknown")
commit:        1265efe (fix) + this docs record
base:          161ef0f -> suite 3446 passed, 14 skipped, 1 xfailed (was 3438; +8 adversarial tests)

finding:       assembly_conditions() AND routes._conditions_for() each wrapped the sourced-conditions
               lookup in `except Exception: return ConditionEnvelope.unknown()`.  A bug in reaction-
               signature computation or structure resolution (AssertionError, AttributeError, ...) was
               therefore laundered into the epistemic statement "conditions unknown" -- a false bench
               fact.  The audit (§10) named only the OUTER routes._conditions_for; verification against
               the code found the DEEPER root is assembly_conditions' OWN `except Exception`, which fires
               first, so an outer-only fix would have been VACUOUS (the mutation control proves this).

fix:           removed BOTH blanket catches.  Every anticipated miss remains an explicit unknown()
               return (section-5.3 conditions blocker; no seed record; record carries no ASSEMBLY
               direction; unresolved reactant/precursor structure; selector-name mismatch) -- these
               explicit guards are now the SOLE path to unknown().  Any unexpected fault propagates to
               the existing ERROR_INTERNAL / exit-70 boundary (CLI-EXIT-01).  No new broad superclass
               was substituted; the expected-absence contract is the explicit guard set, documented in
               both functions' docstrings.

acceptance:    tests/test_err_evidence.py -- the audit's four controls:
                 POSITIVE   a seeded acetic-anhydride ASSEMBLY record still resolves to its sourced envelope;
                 NULL       a legitimate miss (paracetamol hydrolysis is DECOMPOSITION-only) is a quiet
                            unknown() that does not abort route generation; a section-5.3 blocker short-circuits;
                 MUTATION   an injected AssertionError propagates at BOTH layers (assembly_conditions directly,
                            and through search_routes) -- never becomes unknown();
                 END-TO-END through `recompile`, the injected fault is exit 70 / ERROR_INTERNAL, concise
                            message, no raw traceback; and a genuine miss is NOT a false 70.
non-vacuous:   git-stashing only the two source fixes and rerunning fails exactly the 3 fault controls
               (the end-to-end one as `assert 4 == 70` -- the laundering demonstrated live), 5 pass.
scope:         the conditions/evidence lookup path only; no chemistry behavior change on any success path.

red-team:      wl52pwo43 (5 blind orthogonal bearings, refute-by-default verify) -- 1 CONFIRMED HIGH, 1 REFUTED.
  CONFIRMED:   a RESIDUAL launderer the recompile-only end-to-end test missed.  `synthesize` is a SEPARATE CLI
               (smartchem/experiment/cli.py) that (a) wrapped the ENGINE (compile_synthesis -> _conditions_for)
               in `except (ScissionError, ValueError, TypeError)`, re-laundering an internal ValueError/TypeError
               fault into a false domain "invalid chemistry request" (exit 2) on the human path, and (b) had NO
               top-level exit-70 guard, so the --json path escaped as a raw traceback.  FOLDED (69a1ffd): the
               engine catch narrowed to the model-boundary family (ScissionError, IdentityUnsupportedError -> 5);
               main() gained the exit-70 guard smartchem/cli.py already had (body extracted to _run); both human
               and --json paths now map the fault to exit 70 (concise message, no traceback), while a genuine
               refusal stays 5 and invalid input stays 2.  4 regression tests (TestSynthesizeEntryPointRedTeamFold),
               proven non-vacuous; full suite 3450 passed, 14 skipped, 1 xfailed.
  REFUTED:     a "false docstring" claim on _syn_domain_exit -- the verifier confirmed the docstring accurately
               named its caught set; no defect.
```

**Uptake record — IR-STRUCT-01 + IR-FORGET-01, the reoriented Lane-B first brick** (`IR-STRUCT-01` /
`IR-FORGET-01` `TODO` → `IMPLEMENTED_AND_VERIFIED`; the structure-preserving decompile IR + the section-7.3
commuting square the audit's §7.2-7.3 / B0 / Probe P1 / G2 demand):

```text
ID:            IR-STRUCT-01 (structural decompilation is first-class on the IR, not reduced to a formula edge)
               IR-FORGET-01 (its forgetful projection is enforced, and a mismatch is refused not coerced)
commit:        0aac8a1 (feat) + this docs record
base:          0611f0a -> suite 3476 passed, 14 skipped, 1 xfailed (was 3450; +26 tests, tests/test_ir_struct.py)

finding:       (audit §7.2, line 476) structural decompilation reduced its target to a FORMULA as the sole
               shared artifact, so recompile_from_serialized had to be HANDED a caller-supplied structure --
               "a formula-compatibility-constrained structural search, not a structure-reconstructing inverse
               of the decompile artifact".  The structural scission machinery (structure_descent) and the
               forgetful maps (CappedScission.forget -> MediatedEdge) existed, but the structure never rode
               the shared IR: a CandidateSummary was a digest + a string, structurally blind.

fix:           StructuralCandidate + StructuralSpecies (compilation_ir.py): a first-class typed record carrying
               parent/product STRUCTURE identities + exact formula, primitive stoichiometry (species+multiplicity
               per side), the capped-scission edit witness (its own digest + human equation), DECOMPOSE
               direction, provider id/version (the TRANSFORM-PROVIDER-01 seam), FORMAL_CANDIDATE tier (W3),
               loss records, and the EXACT forgetful projection (edge.forget()).  It rides ChemicalCompilationIR
               as a new covered field structural_candidates (schema v1alpha4 -> v1alpha5).  New producer
               decompile_structure_to_ir runs capped_scissions and packages each cleavage over a STRUCTURE-layer
               target, with an honestly-sparse section-8.1 receipt (STRUCTURE_DECOMPOSITION: what the descent
               does not measure is UNKNOWN/null, never a false zero).  New closed-registry grammar
               "capped-scission-decompose" (transform_registry).  Full JSON (de)serialization; deserialize
               re-runs every __post_init__ so a tampered payload is refused on read.  response_schema() gains the
               structural_candidates descriptor field (its drift-guard caught the omission live).

               THE FORGETFUL SQUARE (IR-FORGET-01): StructuralCandidate.__post_init__ recomputes the forgetful
               composition edge from its OWN stored species formulas -- mirroring CappedScission.forget's
               element-bucket merge, a certificate independent of the live scission -- and refuses unless it
               equals the stored projection byte-for-byte (digest AND equation).  This makes the producer
               self-verifying (a mapping error fails construction on the first molecule) and makes a transported
               candidate whose projection contradicts its structure a REFUSAL on read, not a silent coercion.

acceptance:    tests/test_ir_struct.py (26 tests):
                 PRODUCER   a STRUCTURE-layer DECOMPILE with structural (not formula) candidates; the REAL amide
                            hydrolysis (-> 4-aminophenol + acetic acid) is among them, via two distinct witnesses
                            that share one forgetful projection (structure carries more than its formula image);
                 SQUARE     every stored projection IS the forget of the live edge; a tampered projection
                            (digest or equation) or a tampered product formula is REFUSED on read;
                 TRANSPORT  structure identities + edit witnesses survive serialization byte-for-byte, digest-stable;
                 DIGEST     the provider version and the search bounds are in the identity; reagent order is not;
                 GUARDS     canonical/distinct order, STRUCTURE-layer coherence, witness/projection pairing, W3
                            FORMAL_CANDIDATE tier, positive multiplicity -- each enforced and each refused when broken;
                 RECEIPT    the STRUCTURE_DECOMPOSITION receipt nulls what it does not measure; a budget-hit run is
                            PARTIAL_SEARCH_BUDGET (not a false complete); an exhausted-but-empty run (methane) is
                            said as exhaustion-within-bounds, never a false miss;
                 UNAFFECTED decompile_to_ir / recompile_to_ir still work, carry empty structural_candidates, and
                            round-trip under v1alpha5.
non-vacuous:   the crown guard (the forgetful square) proven by neutering ONLY its equality check: the two
               projection-tamper tests go red (they fall through to the weaker canonical-order guard with the
               wrong message), confirming the square is the precise first-line refusal; restored.
scope:         Lane B (chemical genericity) ONLY.  ONE structural family (capped-scission -> mediated edge) is
               first-class; the typed closed provider registry admitting qualitatively distinct families is
               TRANSFORM-PROVIDER-01 (the provider_id/version fields are its seam).  The structure-REBUILDING
               inverse (recompile a structural artifact with NO caller-supplied structure -- audit B0 headline)
               needs a Molecule graph serializer and is the next brick; this lands the necessary first half
               (the structure + witness now RIDE the artifact and survive transport).  Lanes A and C untouched.
               IR-FORGET-01 meets its manifest acceptance (projection == forget, commuting through serialization,
               refuse-on-mismatch); the stronger cross-producer reconciliation (audit §7.3 == D_formula(forget(S)))
               is a named follow-on, not claimed here.
ripple:        schema v1alpha4 -> v1alpha5 shifts every IR value digest, so the CLI-JSON goldens regenerated
               (tests/regen_cli_json.py): each IR-bearing fixture gained "structural_candidates": [] + a new
               result_digest; request_digest unchanged (the field is result, not request); no candidate/equation
               drift; no fixture hand-edited.
red-team:      w2qze2es3 / wf_86c0b53e-dc3 (5 blind orthogonal bearings, refute-by-default verify; 11 agents).
               6 raw findings -> 4 CONFIRMED, 2 REFUTED.  All four confirmed shared one spine: the STRUCTURE
               identity was an unverifiable one-way label, so a transported payload could lie about it.  Folded in
               fd10792; fold suite 3483 passed, 14 skipped, 1 xfailed; 7 regression tests (TestRedTeamFold).
  CONFIRMED 1 (HIGH, forgetful-square-evasion) + 2 (MEDIUM, serialization-tamper-surface), same root: the forgetful
               square was VACUOUS on the structure->formula link.  _recompute_projection forgets the stored
               FORMULAS only; StructuralSpecies stored `structure` (a one-way ChemicalIdentity digest) and `formula`
               as INDEPENDENT fields with no cross-check.  A payload swapping the parent/product structure identity
               for a DIFFERENT real isomer (o-acetamidophenol for paracetamol, same formula C8H9NO2) while leaving
               the formula PASSED the square byte-for-byte AND deserialize_ir -- defeating the exact isomer-level
               content IR-STRUCT-01 adds over a formula edge, and falsifying the brick's own docstring.  Reproduced
               on the filesystem myself (accepted pre-fold).  FIX: StructuralSpecies now carries its canonical
               molecular GRAPH (atoms/bonds/charge/state); __post_init__ rebuilds the Molecule and refuses unless
               the stored identity AND formula are exactly what that graph is -- the structure identity is no longer
               a trusted label, it is re-derived.  Species schema v1alpha1 -> v1alpha2.
  CONFIRMED 4 (HIGH, w3-coherence-scope): a candidate's parent identity was never cross-checked against the IR
               target, so an IR advertising target X deserialized clean while carrying a decomposition of Y (a
               same-formula isomer parent passes the formula-level square; ONLY a target pin catches it).  FIX:
               ChemicalCompilationIR.__post_init__ pins every candidate's parent.structure == target, and guards
               that structural candidates ride only a STRUCTURE-layer DECOMPILE IR.
  CONFIRMED 3 (MEDIUM, digest-identity-law): provider_id/version rode only inside each candidate, so an EMPTY
               structural decompile (methane, no cleavage) laundered the provider out of ir.digest entirely --
               section 4.1 names "transform/evidence provider version" a semantic input.  FIX: the provider is
               folded into request_digest, so it is in the IR identity regardless of the candidate set.
  REFUTED:     (a) "witness_digest/edit_equation are not re-derived" -- correctly a scoped provenance LABEL, no
               false claim (re-derivation needs the graph-scission replay, the inverse follow-on); (b) "operation
               not guarded" -- refuted as not-a-false-claim, but the guard was added anyway (cheap coherence).
  non-vacuous: each confirmed finding reproduced ACCEPTED pre-fold (the isomer swap I reproduced myself) and REFUSED
               post-fold by tests/test_ir_struct.py::TestRedTeamFold; the honest full IR still round-trips unchanged.
```

**Uptake record — TRANSFORM-PROVIDER-01 + CHEM-ALG-01, the genericity payoff** (`TRANSFORM-PROVIDER-01` /
`CHEM-ALG-01` `TODO` → `IMPLEMENTED_AND_VERIFIED`; the transform algebra becomes a PARAMETER of the bounded search
and a second family composes through it with no engine fork — the central genericity thesis, demonstrated):

```text
ID:            TRANSFORM-PROVIDER-01 (the search is parameterized by a typed closed provider registry)
               CHEM-ALG-01 (a second, qualitatively distinct family composes through the UNCHANGED search)
commit:        ea47f3d (feat) + this docs record
base:          785f2b7 -> suite 3508 passed, 14 skipped, 1 xfailed (was 3483; +25: test_transform_provider (10) +
               test_bond_order_edit (15))

thesis:        the reorientation's central verdict is that SmartChem is a generic bounded SEARCH compiler
               parameterized by a still-NARROW transform algebra -- a pathway gap, not a search-budget gap. This
               makes the algebra a PARAMETER and proves a second family widens it with NO search-engine fork.

TRANSFORM-PROVIDER-01 (smartchem/transform_provider.py):
  - StructuralTransform: the uniform interface every family exposes (reactant / reagents / products / forget() /
    equation() / digest); CappedScission already satisfies it. The recompiler step-builder
    (ExperimentStep.from_transform), the conditions gate (assembly_conditions), and the structural decompile were
    ALREADY duck-typed on exactly this interface, so no downstream change was needed -- the coupling was contained
    (from_capped_scission touched only .reactant/.reagents/.products; _reaction_signature getattr's reagents
    defaulting to ()).  This is the compiler validating its own layering.
  - TransformProvider (id/version/capability_manifest/enumerate_transforms) + CappedScissionProvider -- now the ONE
    place capped_scissions is called (exclusivity, grep-verified: routes.py + compilation_ir reroute through it).
  - TransformProviderRegistry: a CLOSED ordered set (order = dedup PRIORITY, a semantic parameter); digest over
    each provider's identity (id+version+manifest, section 8.4/4.1); enumerate() unions the families (dedup by
    transform digest, canonical order) with completeness = AND of every provider's own (partiality never fakes a
    complete).
  - Reroute: search_routes / search_dags / decompile_structure_to_ir gain a `registry` param (default =
    DEFAULT_TRANSFORM_REGISTRY = capped-only), which is behavior-AND-digest identical -- the full 3483-test suite
    passed on the reroute ALONE (confirmed) before CHEM-ALG-01 was added. The structural decompile now stamps the
    PROVIDER-registry digest (the whole algebra) as its transform_registry_digest.

CHEM-ALG-01 (smartchem/bond_order_edit.py):
  - BondOrderEdit + bond_order_edits: the dehydrogenation family (raise one bond's order, shed one H per endpoint
    as H2; reactant -> precursor + H2). Neutral, stable closed products (an alkene + H2, not radicals/ions, so it
    terminates a retro search at stock), forgets to a REAGENTLESS DecompositionEdge. Real chemistry: ethane ->
    ethene + H2, cyclohexane -> cyclohexene + H2, methane/acetylene -> nothing.
  - BondOrderEditProvider registers it; StructuralCandidate generalized: _WITNESS_PROJECTION gains BOND_ORDER_EDIT
    -> DECOMPOSITION_EDGE, _recompute_projection gains the reagentless DecompositionEdge branch, _check_stoich
    allows empty reagents for a reagentless family (a bond-order candidate MUST carry none; a capped candidate MUST
    NOT -- both enforced).
  - COMPOSES through the UNCHANGED route AND DAG search: with the extended algebra search_routes/search_dags on
    ethane over available=(ethene, H2) find the hydrogenation route H2 + C2H4 -> C2H6; the default capped-only
    algebra finds ZERO. Same search code, wider algebra, no engine branch -- the acceptance's "composes through
    unchanged core route/DAG search".
  - Rides the IR (BOND_ORDER_EDIT candidate alongside capped scissions in one decompile IR), obeys the forgetful
    square (recompute-verified; a tampered projection refused), stays FORMAL_CANDIDATE (no sourced conditions ->
    unknown() through the untouched gate). W3 unchanged.

acceptance:    tests/test_transform_provider.py (10): behavior-identity, provenance, registry-digest sensitivity
               (version/set/manifest), partiality-never-fakes-complete, closed-set.  tests/test_bond_order_edit.py
               (15): family enumeration + certificate, riding the IR + forgetful square (tamper refused), the
               compose-through-unchanged-search contrast (extended finds the hydrogenation route in routes AND
               DAGs, default finds neither), reagentless coherence.
scope:         Lane B. Two structural families now first-class. Follow-ons (named, not built): charged families
               (ionic/redox need a charged forget projection -- HeterolyticScission/RedoxHalfReaction exist but
               have no neutral composition edge); the recompile-IR registry threading (route/DAG IR stamping the
               algebra digest); the frozen family-stratified benchmark HOLDOUT-RXN-01 that MEASURES cross-family
               coverage; the structure-rebuilding inverse (unblocked by the graph-carrying species).
red-team:      whg2vhwtk / wf_cdcb0acd-9cc (5 blind orthogonal bearings, refute-by-default verify; 10 agents).
               5 raw findings -> 3 CONFIRMED (2 distinct defects; findings #1 HIGH and #3 MEDIUM are the SAME
               receipt-digest defect from two bearings), 2 REFUTED. Both defects reproduced on the filesystem
               myself and folded in 5bdac74; fold suite 3514 passed, 14 skipped, 1 xfailed.
  CONFIRMED A (HIGH): BondOrderEdit on H2 = Molecule(("H","H")) -- its ONLY candidate edit raises the H-H bond and
               sheds BOTH endpoints, yielding an EMPTY precursor whose forget() calls Formula.of({}) ->
               DecompilerError (a ValueError, NOT a ScissionError), which ESCAPED bond_order_edits' `except
               ScissionError` and crashed the enumerator AND any route/DAG search that had to EXPAND an H2 node (H2
               is a product of every bond-order edit; the demo masked it because H2 was always on-hand). FIX: a
               bond-order edit raises a bond between two NON-hydrogen atoms only (a hydrogen forms no higher-order
               bond); bond_order_edits(H2) now returns ((), True); a search recursing on H2 completes.
  CONFIRMED B (HIGH #1 + MEDIUM #3, same root): search_routes/search_dags gained a `registry=` param (a real
               SEMANTIC input) but stamped the receipt's section-8.4 transform_registry_digest from a FIXED string
               (transform_registry_digest("capped-scission-linear"/"convergent")) invisible to the registry. So an
               extended algebra whose bond-order provider generates the hydrogenation route H2 + C2H4 -> C2H6
               (which capped-scission cannot) left the receipt digest BYTE-UNCHANGED and naming the wrong grammar --
               a false section-8.4/4.1 provenance on the public, tested `registry=` parameter (production used only
               the default, so no shipped output was misled, but the tested param's provenance was false). FIX:
               search_algebra_digest(topology, registry) -- the receipt combines the search topology (linear-route /
               convergent-dag) with the transform ALGEBRA (registry.digest); recompile_to_ir gained a `registry`
               param and READS transform_registry_digest FROM the receipt (IR and receipt agree by construction and
               reflect the real algebra). The 2 recompile CLI-JSON goldens regenerated (only the registry +
               dependent request/result digests moved).
  REFUTED:     (a) "DEFAULT registry vacuously-complete on reagents=()" -- the empty-reagents short-circuit is the
               DOCUMENTED boundary contract (a provider never raises on an empty pool); identity holds byte-for-byte
               on every NON-empty pool (paracetamol 68/68, aspirin 83/83). (b) "ir_from_payload accepts a tampered
               bond-order candidate" -- the tampered candidate is mass-balanced, valence-valid, the forgetful square
               HOLDS (formula-level; products genuinely forget to the stored projection), stays FORMAL_CANDIDATE: a
               coherent differently-witnessed formal candidate, not a break. Exact product-isomer edit-fidelity is
               the witness-label follow-on (graph-scission replay), already named.
  non-vacuous: the H2 crash reproduced (DecompilerError) pre-fold and is gone post-fold; the receipt-digest
               default==extended reproduced pre-fold and now differs -- pinned by TestBondOrderEditDoesNotCrash-
               TheSearch + TestSearchReceiptProvenance + the extended-algebra receipt test.
```

**Uptake record — IR-REPLAY-01 + IR-INVERT-01, the graph-scission replay and its inverse** (`IR-REPLAY-01` /
`IR-INVERT-01` `TODO` → `IMPLEMENTED_AND_VERIFIED`; the two IR-STRUCT-01 follow-ons closed — the loop closes at
the graph level):

```text
ID:            IR-REPLAY-01 (the scission witness is a re-verifiable graph edit, not a one-way label)
               IR-INVERT-01 (the structure-rebuilding inverse: reconstitute a STRUCTURE target with no caller structure)
commit:        846e8bc (feat: item 4 + item 1)  |  IR schema v1alpha5 -> v1alpha6, candidate v1alpha1 -> v1alpha2,
               new StructuralWitness v1alpha1  |  suite 3514 -> 3528 (+14 adversarial), 14 skipped, 1 xfailed.
IR-REPLAY-01:  the gap the IR-STRUCT-01 red-team named (finding (b) above, "differently-witnessed formal candidate").
               The witness was stored only as a digest + equation, so a deserialized candidate could pair a
               witness_digest for edit A with product species that are edit B's SAME-FORMULA isomers; the
               formula-level forgetful square is blind to a product's structure, so it passed. FIX: each
               StructuralCandidate now carries a first-class StructuralWitness -- the family transform's own graph
               edit in ITS OWN index space (reactant graph, ordered reagent graphs, cut/caps for a capped scission,
               the raised bond + shed hydrogens for a bond-order edit). __post_init__ RECONSTRUCTS the exact
               transform (re-running its family certificate -- valence, closed products, descent) and demands
               (a) transform.digest == witness_digest, (b) the reactant canonical == the parent, (c) the reagent and
               PRODUCT canonical multisets == the stored species. (c) is the teeth: strictly stronger than the
               formula square. Reproduced the 4-aminophenol -> 2-aminophenol swap (same formula C6H7NO, different
               structure, itself a valid species): it passes the formula square and the species certificate, and is
               REFUSED by the graph replay. tests/test_ir_struct.py::TestGraphScissionReplay (7).
IR-INVERT-01:  the audit B0 headline. recompile_from_serialized inverts a FORMULA artifact and REQUIRES a caller
               structure (a formula does not fix one). recompile_structure_from_serialized reads a STRUCTURE
               artifact -- its candidates carry graphs + the re-verifiable witness -- so the target is READ FROM the
               artifact (NO structure= argument), and StructuralCandidate.reconstitute_parent inverts each capped
               scission (product graph + edit -> the joined parent+reagent graph, its reactant-atom component the
               parent, connectedness checked). Paracetamol reconstitutes from all 14 decompositions; a FORMULA
               artifact -> NOT_A_STRUCTURE_DECOMPILE; a bond-order-only artifact -> NO_INVERTIBLE_FAMILY (the
               reagentless family's inverse is a NAMED follow-on -- H2 carries no skeleton -- refused, never a
               vacuous echo of the stored reactant). tests/test_ir_struct.py::TestStructureRebuildingInverse (7).
square/W3:     both obey the existing invariants -- the candidate is still FORMAL_CANDIDATE (structure enumerates,
               evidence identifies), the forgetful square still holds, and a RECONSTITUTED verdict means the recorded
               decomposition is INVERTIBLE, never that any synthesis is validated.
fixtures:      the 4 structural CLI-JSON goldens regen (only the IR schema string + dependent digests moved; the CLI
               decompile is the FORMULA path so structural_candidates stays []); test_compilation_ir schema pin
               v1alpha5 -> v1alpha6; one TestRedTeamFold case rewritten to isolate the IR parent-pin (the new
               candidate-level witness-reactant check catches a bare parent-swap earlier -- correct, so the test now
               grafts a fully-coherent wrong-subject candidate).
next:          charged families (IR-INVERT-01 generalizes to a charged rejoin); HOLDOUT-RXN-01 measures the coverage.
```

**Uptake record — CHARGED-ALG-01 + HOLDOUT-RXN-01, the first charged family and the frozen coverage benchmark**
(`CHARGED-ALG-01` / `HOLDOUT-RXN-01` `TODO` → `IMPLEMENTED_AND_VERIFIED`; the algebra reaches past neutral rewrites,
and the payoff is now MEASURED on a frozen set):

```text
ID:            CHARGED-ALG-01 (the first CHARGED transform family rides the algebra)
               HOLDOUT-RXN-01 (a frozen, family-stratified benchmark MEASURES cross-family coverage)
CHARGED-ALG-01: HeterolyticScission/RedoxHalfReaction were charged structural certificates with NO forgetful
               projection -- the neutral MediatedEdge/DecompositionEdge REFUSE a charged species (they assert
               charge==0) -- so no charged family could ride the IR (the "charged forget" the reorientation named).
               FIX: (1) HeterolyticScission gains the uniform transform interface (reagents=(), products=(anion,
               cation), forget()); (2) a new ChargedDecompositionEdge (structure_descent.py) is the charge-carrying
               forget target -- it conserves mass AND charge (a charge-non-conserving edge is refused; reproduced),
               so the section-7.3 square becomes a charge-and-mass invariant, not merely mass; (3) a
               HeterolyticScissionProvider registers the family; (4) it rides the SAME StructuralCandidate/
               StructuralWitness machinery -- _WITNESS_PROJECTION gains HETEROLYTIC_SCISSION -> CHARGED_DECOMPOSITION_
               EDGE, the witness gains a `fragments` field carrying the two ion graphs, and _recompute_projection
               builds the charged edge WITHOUT the neutral element-bucketing that would drop an ion's charge. It
               obeys the graph-scission replay (IR-REPLAY-01) and the structure-rebuilding inverse (IR-INVERT-01
               generalizes: the ions rejoin across the cut bond -> the parent; HCl reconstituted), stays
               FORMAL_CANDIDATE (W3), and is DECOMPILE-only (charged fragments do not terminate at neutral stock, so
               it is NOT forced through the neutral route search -- honest). Redox is a NAMED follow-on (electrons as
               massless carriers complicate the species/forget). IR v1alpha6->v1alpha7, candidate v1alpha2->v1alpha3,
               witness v1alpha1->v1alpha2; the 4 structural CLI-JSON goldens regen (schema + digests only).
               tests/test_charged_family.py (17).
HOLDOUT-RXN-01: experiments/holdout_rxn_benchmark.py -- a FROZEN set of 18 family-stratified targets, each attributed
               to the family that FIRST constructs a complete decomposition across the increasing registry chain
               [capped] < [+bond-order] < [+heterolytic], or OUTSIDE_CLOSURE. Coverage MEASURED: default (capped) 8/18;
               +bond-order unlocks +2 (ethylene, benzene); +heterolytic unlocks +5 (HCl, HF, methane, water,
               acetylene); 3/18 genuinely outside-closure (N2, O2, Ne). Non-vacuous BY CONSTRUCTION: every bucket is
               populated and coverage is < 100% (a target outside the whole algebra is reported outside, not hidden).
               The target set + each attribution + a content hash + a separate HOLDOUT-subset hash are frozen;
               tests/test_holdout_rxn.py asserts the live compiler reproduces every frozen attribution and the hash
               matches -- a wrong provider change moves a frozen attribution and fails there, so the benchmark cannot
               drift and the holdout cannot be quietly re-labelled to flatter coverage. `--freeze` regenerates the
               frozen blocks deliberately after an intentional algebra change.
scope:         Lane B. THREE structural families now first-class (capped / bond-order / heterolytic), the loop closes
               at the graph level (IR-REPLAY-01 + IR-INVERT-01), and cross-family coverage is measured on a frozen
               benchmark. Named follow-ons: redox family; recompile-IR registry threading; the bond-order inverse.
```

**Red-team fold — items 4/1/3/2** (blind-bearing workflow `w7gfe6ljw`, 5 orthogonal bearings × refute-by-default
verify, 11 agents; **6 CONFIRMED** across 4 distinct defects, each reproduced on the filesystem before folding):

```text
CONFIRMED (2 crashes, 1 vacuity, 1 false-provenance -- 6 findings, 4 distinct roots):
  MEDIUM inverse-vacuity: StructuralCandidate.reconstitute_parent / StructuralWitness.rebuild_parent was a
    reactant ECHO -- rebuild_parent derives the product graph from the witness REACTANT (join - cut + caps == the
    reactant), never reading the stored products, so its `== parent` check could never fail and its connectivity
    guards were dead (swapping a candidate's products to aspirin still returned paracetamol). The inverse's
    soundness rested ENTIRELY on the separate item-4 __post_init__ replay. FIX: reconstitute_parent now RE-VERIFIES
    the stored products against the witness replay (step 1, the product-consuming step) BEFORE inverting the edit
    (step 2); a swapped product set is refused. rebuild_parent's docstring corrected to state its honest scope (it
    inverts the EDIT; it is not itself product-consuming). The false-assurance test reworded.
  MEDIUM charged-crash-A: a SYMMETRIC heterolytic split (O2(2-) -> O(-) + O(-), two IDENTICAL ions) merges to ONE
    formula x multiplicity 2, which ChargedDecompositionEdge's "count DISTINCT formulas >= 2" check REJECTED ->
    uncaught ScissionError crashed the whole charged decompile. FIX: require >= 2 INSTANCES (sum of multiplicities),
    so a symmetric split is a valid genuine split.
  MEDIUM charged-crash-B: CappedScissionProvider.enumerate_transforms RAISED on a charged reactant (CappedScission
    is neutral-only) instead of returning ((), True), so a MIXED (capped + heterolytic) registry crashed end-to-end
    on ANY charged target -- the heterolytic candidates were never reached. FIX: the capped provider yields nothing
    (complete) for a charged reactant (the boundary contract: a family that cannot apply never raises).
  LOW/MEDIUM edit_equation (2 bearings, one root): the human-readable edit_equation was a free string never
    cross-checked against the witness's OWN equation -- a candidate with an honest machine identity (digest, graph,
    products, projection all re-verified) could carry a readable equation stating false chemistry (the paracetamol
    litmus a chemist reads). FIX: __post_init__ now asserts witness_transform.equation() == edit_equation (the human
    twin of the witness_digest check). LOW recompile-note: the RECONSTITUTED note named decompile_ir.target.
    canonical_repr (a free field a tampered artifact can set to any string) instead of the ACTUAL rebuilt molecule;
    FIX: the note names ChemicalIdentity.of_molecule(reconstituted).canonical_repr.
non-vacuous:   each reproduced pre-fold (product-swap echo; O2(2-)/mixed-registry crashes; tampered edit_equation
    accepted; note naming a lie) and is refused/fixed post-fold; pinned by TestRedTeamFoldRound2 (tests/test_ir_
    struct.py) + TestChargedRedTeamFold (tests/test_charged_family.py). No serialized-shape change (validation +
    logic + docstrings only), so no schema bump and no golden regen.
REFUTED:       none reported -- every bearing that fired produced a reproducible finding; the machine-load-bearing
    identity (forgetful square, graph-scission replay, digest law) held under all five bearings.
```

**Uptake record — item 4: the recompile-IR registry threading** (a Lane-B follow-on named in §2A.1; the
serialized inverse now re-searches under the CALLER's transform algebra, not a hard-wired default):

```text
ID:            item 4 (recompile-IR registry threading; the last of the CHEM-ALG-01 fold's "search-receipt
               half did it, the serialized inverse did not")
commit:        c70afc7 (feat)  |  no schema bump (a new keyword param with a behaviour-preserving default)
gap:           recompile_from_serialized (the FORMULA-artifact inverse, IR-INV-01) re-ran recompile_to_ir with
               NO registry argument -> the DEFAULT capped-only algebra. recompile_to_ir and
               decompile_structure_to_ir already took `registry=`; the serialized inverse was the one search
               entry point that did not, so inverting an artifact produced under a WIDER algebra silently
               re-searched the narrow default and its NO_ROUTE_IN_GRAMMAR verdict named the wrong grammar
               (section 8.4: the exhaustion scope is only ever THIS registry at THESE bounds).
fix:           added `registry: TransformProviderRegistry = DEFAULT_TRANSFORM_REGISTRY` and threaded it into the
               recompile_to_ir call; the docstring states the algebra-scope obligation. The default keeps every
               existing caller behaviour- AND digest-identical (the whole suite is transparent to the param).
tests:         tests/test_compilation_ir.py::TestRecompileFromSerialized (+2):
                 - the bond-order registry finds the hydrogenation H2 + C2H4 -> C2H6 in the re-search
                   (ROUTES_FOUND); the default capped-only algebra does NOT (NO_ROUTE_IN_GRAMMAR). NON-VACUOUS:
                   the outcomes DIFFER and the returned IR's transform_registry_digest differs (it names WHICH
                   algebra it searched, not a fixed default).
                 - the default passed explicitly == left implicit (inverse_status AND recompile_ir.digest equal),
                   pinning behaviour-identity for the pre-threading callers.
command:       .venv/bin/python -m pytest -q -p no:cacheprovider
result:        3561 passed, 14 skipped, 1 xfailed (baseline 3559; +2 the new tests). EXIT=0. ruff clean on the
               changed files.
scope:         Lane B. This is a provenance-honesty completion, not a new family: recompile_from_serialized can
               now honestly invert a wider-algebra artifact under the SAME algebra. recompile_structure_from_
               serialized (the STRUCTURE-artifact inverse) needs no registry -- it inverts stored witnesses, it
               does not re-search. Next Lane-B follow-ons: the bond-order structure-rebuilding inverse (item 3a),
               the redox family (item 1).
```

**Uptake record — item 3a: the bond-order structure-rebuilding inverse** (a Lane-B follow-on named in §2A.1;
the reagentless bond-order family's inverse, previously deferred, is now built -- every current family inverts):

```text
ID:            item 3a (the bond-order structure-rebuilding inverse; item 3b -- the graph-scission witness
               replay for products -- was already landed under IR-REPLAY-01)
commit:        65af346 (feat)  |  no schema bump (a new rebuild_parent branch + a note fix; no serialized change)
gap:           StructuralWitness.rebuild_parent RAISED NotImplementedError for BOND_ORDER_EDIT. The refusal's
               reason ("H2 carries no skeleton, needs a canonical-precursor index recovery") is real ONLY for
               inverting from the STORED canonical PRODUCT species (the precursor is reindexed there, so the
               shed hydrogens' attachment sites are lost). But rebuild_parent works in the witness's OWN reactant
               index space (as the capped and heterolytic inverses do), where bond_i/bond_j/h_i/h_j ARE known
               indices -- so no recovery is needed and the refusal was over-cautious.
fix:           the BOND_ORDER_EDIT branch now derives the forward product connectivity (precursor + H2) in the
               reactant index space, inverts it (drop the shed pair's H-H bond, lower the raised bond one order,
               restore the two shed C-H bonds), and checks a single connected parent is reconstituted -- exactly
               parallel to the other two families. Product-consumption stays reconstitute_parent step 1's job (a
               swapped product set is still refused there), so this is NOT the vacuous reactant-echo the earlier
               refusal guarded against. The recompile_structure_from_serialized deferral note that named "the
               reagentless bond-order edit" is generalized (no CURRENT family defers -- the guard is for a FUTURE
               family whose products carry no reconstructable skeleton).
tests:         tests/test_ir_struct.py::TestStructureRebuildingInverse (2 refusal tests FLIPPED + 2 added, +2 net):
                 - a bond-order-ONLY ethane artifact now RECONSTITUTES ethane from ethene + H2, no caller
                   structure, no deferral (was: NO_INVERTIBLE_FAMILY);
                 - witness.rebuild_parent() == ethane.canonical() and agrees with reconstitute_parent (was: raises);
                 - NON-VACUOUS: swapping the bond-order candidate's products to aspirin is REFUSED at step 1
                   (soundness is not a reactant echo);
                 - the NO_INVERTIBLE_FAMILY deferral path stays LIVE-tested via a mock forcing rebuild_parent to
                   raise NotImplementedError (now that every real family inverts, an untested branch would be
                   vacuous-green -- [[vacuous-green-over-an-empty-subject]]).
command:       .venv/bin/python -m pytest -q -p no:cacheprovider
result:        3563 passed, 14 skipped, 1 xfailed (baseline 3561; flipped 2 + added 2 = +2 net). EXIT=0. ruff
               clean on the changed files.
scope:         Lane B. All three current families (capped, heterolytic, bond-order) now invert their decomposition
               to reconstitute the parent STRUCTURE with no caller structure. Next Lane-B follow-on: the redox
               (electron-transfer) family (item 1).
```

**Uptake record — item 1 / REDOX-ALG-01: the redox (electron-transfer) family** (`REDOX-ALG-01` `TODO` →
`IMPLEMENTED_AND_VERIFIED`; the last named Lane-B follow-on -- the charge-only family, the chem↔EM bridge):

```text
ID:            REDOX-ALG-01 (item 1)
commit:        757aeb4 (feat)  |  IR v1alpha7 -> v1alpha8, candidate v1alpha3 -> v1alpha4, witness v1alpha2 -> v1alpha3
what:          RedoxHalfReaction (reduced -> oxidized + n e-) existed as a charge-conserving certificate but had NO
               forgetful projection and no uniform transform interface, so no redox family could ride the IR. This
               brick completes the charged arc (after the heterolytic CHARGED-ALG-01) and reaches the
               electromagnetic scope: a redox step is CHARGE-ONLY (same atoms and bonds -- it makes/breaks nothing),
               the first family whose "decomposition" does not reduce a species' size.
design:        - structure_descent.py: the uniform interface (reactant/reagents/forget) + a charge-carrying
                 ElectronTransferEdge forget target (mass conserved trivially since electrons are massless; CHARGE
                 is the conserved quantity, per-unit oxidized.charge - electrons == reactant.charge).
               - THE electron representation: an electron is atom-less, so Formula.of refuses it AND
                 StructuralSpecies (>=1 atom) refuses it -- it can be NEITHER a product formula NOR a product
                 species. So it rides an explicit integer `electrons` count on the witness (digest-pinned) and the
                 ElectronTransferEdge, never as a species. The two product-multiset checks (the __post_init__ graph
                 replay and reconstitute_parent step 1) reconstruct `stored + n electrons` (0 for every non-redox
                 family -> byte-identical to before), so the check is EXACT and a tampered electron count is caught
                 by the witness_digest check.
               - transform_provider.py: RedoxHalfReactionProvider, OPT-IN (absent from the default registry);
                 max_electrons on the capability manifest so bumping it moves the registry digest. DECOMPILE-only.
               - the charge-only INVERSE: rebuild_parent re-adds the transferred electrons (lowers the oxidised
                 charge by n) -> the reduced parent; there is no bond skeleton to rebuild. Non-vacuity stays
                 reconstitute_parent step 1's job (a swapped product is refused), exactly as for the other families.
honesty:       redox is ORTHOGONAL to HOLDOUT-RXN-01. It is charge-only, not size-reducing, so it constructs ZERO
               new DECOMPOSITIONS -- it widens the algebra on the charge/EM axis, not the decomposition-coverage
               axis. The frozen family-stratified benchmark is therefore deliberately UNTOUCHED (adding a redox
               chain link would unlock nothing and be vacuous). Named, not faked.
tests:         tests/test_redox_family.py (20): uniform interface + charge-AND-mass forget (a charge/mass-non-
               conserving ElectronTransferEdge refused, non-vacuous); rides the IR (forgetful square recompute-
               verified, tampered projection refused, round-trip digest-stable for Na and NO, default registry
               emits none); graph replay + inverse (Na -> Na+ + e- and NO -> NO+ + e- reconstitute; a tampered
               witness electron count refused; a SWAPPED product refused -- soundness is not a reactant echo);
               electrons-are-not-species (StructuralSpecies refuses the atom-less electron; the oxidised product
               shares the parent graph, differing ONLY in charge); provider identity/scope (max_electrons moves the
               registry digest; a mixed capped+redox registry surfaces redox through the unchanged decompile seam).
               Also hardened test_ir_struct.py's witness-graft test: the schema-bump reorder revealed candidates[0]/
               [1] now share products via different edits (a legitimate "two witnesses, one projection" pair, NOT a
               tamper), so the test now explicitly selects a candidate with DIFFERING products. Regenerated the 4
               CLI fixtures (formula path, structural_candidates:[]) for the IR schema string + dependent digests.
command:       .venv/bin/python -m pytest -q -p no:cacheprovider
result:        3583 passed, 14 skipped, 1 xfailed (baseline 3563; +20 the redox tests). EXIT=0. ruff clean.
next:          Lane B's four-family algebra is complete for this arc. The genericity thesis stands: neutral capped
               scission, neutral bond-order edit, charged heterolytic scission, and charge-only redox all compose
               through the UNCHANGED core search and IR, each obeying the forgetful square + graph replay + inverse.
```

**Red-team fold — item 1 / REDOX-ALG-01** (blind-bearing workflow `we968mh0o`, 5 attack bearings × refute-by-default
verify, 9 agents; **1 CONFIRMED MEDIUM**, reproduced on the filesystem before folding; 4 bearings clean):

```text
CONFIRMED (1 MEDIUM: an unbounded-electrons DoS on the public deserialize path):
  The redox electron count was validated only with a LOWER bound (>= 1) at RedoxHalfReaction.__post_init__ and the
  StructuralWitness REDOX branch, and the charge certificate is TAUTOLOGICAL in n (oxidized.charge = reduced.charge
  + n makes "oxidized.charge - n == reduced.charge" hold for ANY n). The provider's max_electrons ceiling bounds
  only ENUMERATION, not the read path -- the codebase's own "injectable-but-not-live-guard" anti-pattern. So a
  crafted serialized artifact carrying electrons=10**18 passed the schema check, the field discipline, the witness
  graph-replay, the forgetful-square recompute, AND the witness_digest check (none of which touch the LAZY
  .products), and only THEN materialized a (ELECTRON,)*n tuple in the product-multiset checks -> a MemoryError
  (hard crash) or a slow-burn CPU DoS from a ~3.5 KB payload, reachable through the public deserialize_ir boundary
  (the IR-INVERT-01 / recompile_structure_from_serialized transport path). Reproduced here: n=2,000,000 constructs
  in ~0s (lower-bound-only) and .products materializes 2M items -- linear -> OOM at 10**18.
  FIX (structure_descent.py): a LIVE physical UPPER bound -- no atom exceeds the +8 oxidation state (Os/Ru/Xe), so
  a species of A atoms sheds at most 8*A electrons. Enforced at the RedoxHalfReaction CERTIFICATE (electrons <=
  8*len(reduced.atoms)), so it holds on EVERY construction incl. replay/deserialize, BEFORE .products is touched
  (the RedoxHalfReaction/witness __post_init__ never access the lazy .products). redox_couples caps its range at
  min(max_electrons, 8*atoms) so the enumerator and the certificate agree. No schema/serialized-shape change.
non-vacuous:   reproduced pre-fold (n=2M accepted, .products = 2M items); post-fold n=10**18 in a serialized witness
  is REFUSED instantly on deserialize_ir (ScissionError, before any tuple materialization). Pinned by
  tests/test_redox_family.py::TestRedTeamFold (the bound at the certificate for Na/NO; the deserialize attack
  refused fast; redox_couples capped at the ceiling).
REFUTED/clean: the other 4 bearings (redox conservation/forgetful-square, redox graph-replay + inverse vacuity,
  bond-order inverse over rings/multi-bond/higher-order, provider opt-in isolation & no-forced-route-recursion)
  found no defect -- the core soundness held.
commit:        071f4ba (fix)   |   suite 3586 passed, 14 skipped, 1 xfailed (fold-only; the item-2 G8 xfail
               guard lands separately -> 2 xfailed). EXIT=0. ruff clean.
```

**Uptake record — item 5 / THERMO-UNC-01: the sourced CODATA uncertainty seed** (`THERMO-UNC-01` `TODO` →
`IN_PROGRESS`; the Lane-C sourcing the Operator released "on go, if sources exist online" -- they do):

```text
ID:            THERMO-UNC-01 (item 5)  |  commit 59acf60 (feat)  |  decompiler_thermo schema tiered-v1 -> tiered-v2
source hunt:   workflow wwom7qo7j (3 data-class bearings x adversarial DO/BLOCKED adjudication). THERMO-UNC -> DO
               (CODATA Key Values 1989, real +/- , NIST-WebBook cross-verified); COST-VEC -> PARTIAL (USGS MCS
               commodity prices, dated/DOI'd, but the sandbox 403'd the fetch so the FIGURES are unverified);
               TERM-MAT -> PARTIAL (USGS MCS + USITC HTS commodity-existence leads).
did (verifiable, committed):
  * experiments/thermo_codata_seed.py -- a FROZEN, dated, cited, sha256-pinned reference dataset: 9 CODATA key
    species (H2O l/g, CO, CO2, NH3, O2, H2, N2, C-graphite) with +/- on dfH(298.15K) AND S(298.15K), transcribed
    from Cox/Wagman/Medvedev 1989 and cross-checked against the free NIST WebBook (access 2026-09-04). Values are
    textbook CODATA (H2O(l) -285.830+-0.040, CO2 -393.51+-0.13, ...), verifiable, not fabricated.
  * THE non-vacuity discipline (the source-hunt adjudicator's condition, and the standing vacuous-green lesson):
    the validator REFUSES a hollow uncertainty on a non-reference value -- and fires on the RECORD, not merely on
    an empty set -- while ACCEPTING a reference-state convention-zero (O2/H2/N2/graphite dfH=0+-0 is a definition;
    their S still carries a real +-). A zero/negative "uncertainty" on a sourced value is refused.
  * decompiler_thermo.ThermoRef gains a typed `uncertainty_kj: float | None`, populated from the +/- already cited
    in each entry's provenance (ketene 1.60, paracetamol 1.9) with honest None where the source gave none, same
    guard. Backward compatible (default None; the dfH consumers unchanged).
did NOT (held honest, no fabrication):
  * COST-VEC-01 stays BLOCKED: the only free dated price source (USGS Mineral Commodity Summaries) was found, but
    the sandbox could not fetch/verify the actual figures (pubs.usgs.gov 403s automation), and section 10.4 forbids
    committing a price this session did not verify. The sourcing PLAN is recorded; the numbers are not committed.
  * TERM-MAT-01 commodity-existence leads (USGS MCS chapters + USITC HTS headings) were found but likewise await
    an in-repo verification pass before any lead is written -- not committed on a search-index snippet.
  * CH4 and any non-CODATA-key species are ABSENT from the seed (not fabricated); widening needs ATcT/JANAF.
remaining (named): wire uncertainty_kj into data/thermo.py's ThermoRef (the phase/grade type the row first named)
               + its group-additivity/feasibility consumers; verify + commit the USGS commodity leads/prices.
tests:         tests/test_thermo_codata_seed.py (10) + tests/test_decompiler_thermo.py::TestUncertaintyField (4).
command:       .venv/bin/python -m pytest -q -p no:cacheprovider
result:        3600 passed, 14 skipped, 2 xfailed (baseline 3586; +14). EXIT=0. ruff clean.
```

**Uptake record — items 1 & 4 / Lane-A RC-readiness: the `synthesize` §14.1 alias-unity + the P0 close/narrow**
(`CLI-CAN-01` & `SRCH-DIG-01` `IN_PROGRESS` → `IMPLEMENTED_AND_VERIFIED`; §2A.7 freeze-checklist steps 1–3; the
Operator's directive "make the output reality-respecting, fit the ethos, and revise the standard"):

```text
ID:            item 1 (synthesize §14.1 alias-unity) + item 4 (Lane-A P0 close/narrow)  |  commits: feat + docs
decision:      Operator: reality-respecting output + fit ethos + REVISE the standard (the blocker's Operator call).
did (item 1 -- the reality-respecting fix + the standard revision):
  * smartchem/experiment/cli.py: `synthesize` (and `python -m smartchem.experiment`) now threads every OMITTED knob
    as None through the ONE build_recompile_request, so `synthesize X --emit-request` is BYTE-IDENTICAL to
    `recompile X` (offline provider, depth 3, commodities ON -- reproducible + complete), verified live by diff.
    The download-and-go network fetch is the EXPLICIT `--network` opt-in (origin=EXPLICIT; a live fetch is NEVER the
    default); `--offline` stamps the default; `--poor-mans` -> `--no-commodities`/`--elements` (mirrors recompile);
    the human dossier reads commodities from the REQUEST (one source of truth).
  * CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md REVISED: §14.1 (aliases build the same request under equal flags AND no
    verb reaches the network by default -- a live fetch is an explicit opt-in; its dated §13.2 provider snapshot is a
    separate, still-open conformance item, value-cached but not stamped -- red-team fold), the §16 G8 gate (a new offline-default bullet), the §18 migration note.
  * the strict-xfail G8 guard is now a LIVE PASS parametrized across the full 7-row command matrix; a non-vacuous
    `--network`-splits-the-request test proves the opt-in is honestly marked (the origin flip is asserted).
did (item 4 -- the Lane-A P0 reconciliation, each claim verified against code):
  * CLI-CAN-01 -> IMPLEMENTED_AND_VERIFIED: the command-matrix equal-request acceptance now holds for ALL THREE
    aliases incl. `synthesize` (the vacuous-green subject closed).
  * SRCH-DIG-01 -> IMPLEMENTED_AND_VERIFIED: the shared request canonicalizes the reagent/stock inventory, so
    inventory ORDER -> byte-identical request AND equal result_digest (structural/material path), proven end-to-end
    (tests/test_cli_canonical.py::TestInventoryOrderInvariance). Its "shared request identity does not exist" was STALE.
  * SVC-REQ-01 / SRCH-NO-01 / CLI-JSON-01 -> recorded narrower alpha contract (§9 DoD bullet 1's second path): the
    residuals are decompile-side / labeling / affordability-empty polish, NOT truth holes. See the §2A.7 item-1+4
    UPDATE for the per-row narrowing + the updated verdict (no behavioral RC blocker remains on Lane A).
blast radius:  synthesize's default flipped commodities OFF->ON, so two fixtures written for the old default
               (tests/test_routes.py::TestCLI end-to-end + no-route-loudly) went PARTIAL (exit 4); restored to their
               COMPLETE-search INTENT with --no-commodities (the partial case is covered by
               test_cli_returns_partial_status). Same one-flag fix applied to test_synthesize_provider._ROUTE_ARGV.
tests:         tests/test_cli_canonical.py (G8 matrix pass + network split + TestInventoryOrderInvariance),
               tests/test_synthesize_provider.py (offline-default + --network optin, rewritten), tests/test_routes.py.
result:        3639 passed, 14 skipped, 1 xfailed (baseline 3600/14/2; the G8 xfail is now a live pass). EXIT=0. ruff clean.
```

**Uptake record — item 3b / THERMO-UNC-01: `data/thermo.ThermoRef` carries the sourced CODATA uncertainty**
(the named "wire uncertainty into data/thermo.py's ThermoRef" step of `THERMO-UNC-01`):

```text
ID:            item 3b (data/thermo ThermoRef sourced uncertainty)  |  no schema/digest change (compare=False)
did:
  * smartchem/data/thermo.py ThermoRef gains uncertainty_dhf_kj / uncertainty_s_j_per_mol_k (float | None, both
    compare=False -> METADATA, OUT of the semantic digest and equality: adding a ± moves NO fingerprint and NO
    golden -- proven by a digest-equality test). Non-vacuous guard: None (honest absence) or a real ± (> 0); dfH's ±
    may be exactly 0.0 ONLY at a reference state (ΔfH°=0 convention); a hollow/zero/negative elsewhere is refused.
  * SEED_THERMO_REFS populated from the SAME CODATA ± (cross-checked to experiments/thermo_codata_seed.py), attached
    ONLY where it shares the VALUE's source (NO provenance mixing): H2O/CO/CO2 carry the CODATA ±, the reference
    states H2/O2/N2 carry the convention-zero dfH ±, and a NIST value with no stated ± (N2 S°, ammonia, CH4) stays
    honest None. resolve_thermo (the feasibility path) surfaces the ± to a consumer -- WIRED, not merely present.
  * item 3a (the electron-carrier witness-fidelity replay) was ALREADY built + non-vacuously tested under item-1
    REDOX-ALG-01 (compilation_ir.py appends the massless carriers to the product-multiset check; test_redox_family:
    witness-replays-to-oxidised-plus-electrons, tampered-electron-count-refused, non-vacuous inverse) -- reported,
    NOT re-done.
remaining (named): PROPAGATE the ± through the feasibility/equilibrium ΔG math (σ_ΔG in quadrature; the mixed
               sourced/DERIVED-group-additivity edge is real); widen the seed past the CODATA key set.
tests:         tests/test_thermo_uncertainty.py (10). thermo/feasibility regression (218) green, zero digest churn.
result:        3639 passed, 14 skipped, 1 xfailed (baseline 3600/14/2; the G8 xfail is now a live pass). EXIT=0. ruff clean.
```

**Uptake record — THERMO-UNC-01: σ(ΔG)/σ(log10 K) propagated through feasibility + equilibrium** (the named
"propagate the ± through the ΔG math" step; the seed-widening step remains):

```text
ID:            THERMO-UNC-01 (propagation)  |  commit 8827306 (feat) + this docs record
did:
  * resolve_thermo (feasibility.py) -- THE CRUX: it destructured 5 of estimate_thermo's 7 fields and DROPPED the
    group-additivity uncertainty band thermo_groups already computed by quadrature, so every DERIVED ThermoRef read
    sigma=None (indistinguishable from a sourced value with no stated ±). Now the band is threaded onto the ThermoRef
    (the [[a-dispatcher-that-drops-a-threaded-kwarg]] pattern). A phase-corrected record notes its ± is a LOWER BOUND.
  * feasibility_of_step: sigma(dG) in quadrature -- sigma(dH)^2=sum(nu_i sigma_dfH_i)^2, sigma(dS)^2=sum(nu_i
    sigma_S_i)^2, sigma(dG)^2=sigma(dH)^2+(T sigma(dS)/1000)^2. _coefficient_vector nets each species to one entry, so
    no sigma is double-counted (category.py:1071 spectator hazard pre-handled). Computable ONLY if EVERY species has
    that sigma -- one missing -> UNKNOWN (the honest mixed sourced/DERIVED edge, never a partial understating sum).
    LOWER BOUND when >=2 group-derived (common-mode group-additivity MODEL error -- NOT "shared anchors"; red-team
    fold 5b9e8d2), cross-phase, or a phase-corrected input whose band was not widened (cf. formation.DerivedFormation).
  * equilibrium_of_step: sigma(log10 K) = sigma(dG)*1000/(R T ln10) (log10 K linear in dG); lower-bound flag rides on.
  * StepFeasibility gains sigma_delta_g_kj + sigma_delta_g_is_lower_bound; StepEquilibrium gains sigma_log10_k +
    sigma_log10_k_is_lower_bound -- ALL compare=False METADATA (zero digest/golden churn, like ThermoRef's sigmas).
verified:      sigma(dG) for 2H2+O2->2H2O(l) == the exact hand quadrature of the CODATA ±; Haber (N2 S°/NH3 lack a
               sourced ±) -> sigma(dG) UNKNOWN while dG is known; >=2 derived (ethanol+ethylene) -> LOWER BOUND.
remaining:     widen the seed past the CODATA key set (version-pinned ATcT/JANAF, never fabricated; the
               thermo_extended.py prose-± lift is a candidate but needs an independent cross-check first).
tests:         tests/test_sigma_propagation.py (5); blast radius (feasibility/equilibrium/thermo/classify/dag): 205.
```

**Uptake record — item 5 / COST-VEC-01: the VERIFIED USGS commodity-price seed (price-data block LIFTED)**
(`COST-VEC-01` `BLOCKED` → `IN_PROGRESS`; supersedes last round's "USGS found but the sandbox couldn't verify"):

```text
ID:            item 5 (USGS commodity-price seed)  |  content sha256 dfc01d9f…e31e82 (frozen, tamper-evident)
source:        USGS Mineral Commodity Summaries 2026 (U.S. Geological Survey, February 2026), public domain.
verification:  the prior wall ("pubs.usgs.gov 403s automation") is GONE: WebFetch still 403s, but the PDFs were
               fetched with curl and parsed with `pdftotext -layout`, and EVERY figure was read off the primary
               chapter's Salient-Statistics price row BY ME (not on a subagent's word), checked against the
               column-year header (2021 2022 2023 2024 2025e) and the chapter narrative (sulfur "$180 from $46").
did (verifiable, committed):
  * experiments/usgs_commodity_seed.py -- a FROZEN, dated, cited, sha256-pinned seed: 8 priced forms (salt rock/
    solar/vacuum-open-pan/brine, soda ash, lime quicklime/hydrated, elemental sulfur), each the 2024 FINAL average
    unit value $/t + the 2025e estimate, with the sourced basis + chapter URL. Load-bearing pins: rock salt 52.95,
    soda ash 169.35, quicklime 261.4, sulfur 46.42 ($/t, 2024 final).
  * NON-VACUOUS validator: a hollow/zero/negative price is REFUSED (fires on the record), an unsourced (no USGS URL)
    row is refused, and a no-primary-source commodity (acetic acid / vinegar / sodium bicarbonate) CANNOT be
    fabricated into the priced seed -- the guard refuses it, not just a comment.
did NOT (held honest, no fabrication):
  * acetic acid / vinegar / sodium bicarbonate: NO primary-source per-ton price (USGS names bicarbonate only as an
    UNPRICED soda-ash coproduct); the only free per-ton figures were a commercial aggregator (IndexBox) with no
    traceable primary authority -> NOT committed (§10.4). Soda ash is the priced parent, a labelled proxy only.
  * COST-VEC-01's affordability ENGINE (the Pareto axes) + wiring each price into a dated STOCK-01 CostObservation
    on the CommodityReagent registry remain -- named, not built. This brick is the DATA the block waited on.
tests:         tests/test_usgs_commodity_seed.py (16).
result:        3639 passed, 14 skipped, 1 xfailed (baseline 3600/14/2; the G8 xfail is now a live pass). EXIT=0. ruff clean.
```

## 3. P0 truth-envelope backlog

### 3.1 Search completeness and result semantics

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `SRCH-RCT-01` | Every formula, route, and DAG search returns a `SearchReceipt` | All three searches now return a first-class receipt over the shared `smartchem.search.SearchStatus` vocabulary: `search_routes`->`RouteSearchReceipt`, `search_dags`->`DAGSearchReceipt`, `search_decomposition`->`FormulaSearchReceipt` (`454d2a0`); the `build_*`/`enumerate_*` calls stay graph/tuple wrappers. Folding the three receipts into one response object is separate (`CLI-JSON-01`) | Unify the three receipts under one response schema | Low cut budget reports partial for all three search kinds | None | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-RCT-02` | Preserve `capped_scissions.complete` across recursion | Linear and DAG searches both aggregate `capped_scissions.complete` across recursion into their receipts (`4a958b8`); the formula descent keeps its own loud `REFUSED_BUDGET` | Carry the same aggregation into any future shared search | Acetic-anhydride budget fixture is partial in linear and DAG paths; high budget complete within bounds | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-CAP-01` | Route/DAG result-cap saturation is visible | Linear and DAG result-cap saturation are both receipt-visible and tested (`4a958b8`); DAG saturation is conservative — a cap equal to the true distinct count flags `PARTIAL_RESULT_LIMIT`, never a false complete | Add shared JSON exposure of the saturation flag | Low linear and DAG result caps are partial; caps above fixture count are complete | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-NO-01` | No-route wording distinguishes complete from incomplete | Linear human output distinguishes partial absence, and DAG `search_dags` distinguishes complete-empty from incomplete-empty at the receipt level (`4a958b8`); the formula receipt reports partial-vs-complete too (though a formula graph always has edges, so it has no empty-candidate no-route case). The four-outcome §8.3 matrix is now surfaced UNIFORMLY (**CLOSED**, RC-STATUS-RECONCILE): a pure `search.section_8_3_label` leaf + the derived `CompilationResponse.search_space_status` carry the four labels (NO_ROUTE_IN_DECLARED_SPACE / INCOMPLETE_NO_ROUTE_OBSERVED / COMPLETE_CANDIDATE_SET / PARTIAL_CANDIDATE_SET) through the recompile + decompile `--json` AND human renderers and the compile Dossier, so an incomplete-empty search is never laundered into a complete no-route on any public path | Implemented the four-outcome matrix in the shared response + all public renderers | Empty incomplete -> `INCOMPLETE_NO_ROUTE_OBSERVED`; empty complete -> `NO_ROUTE_IN_DECLARED_SPACE`, distinctly, in human AND `--json` — **DONE** (`tests/test_srch_no.py`) | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-BUD-01` | Budget scope is accurately named | All three receipts name their budget scope: linear/DAG say cut budget per expansion; the formula receipt names its per-node search-node budget and whole-graph edge cap distinctly (`PARTIAL_SEARCH_BUDGET` vs `PARTIAL_RESULT_LIMIT`, `454d2a0`) | Keep the named scopes when the receipts fold into a shared response | Every receipt says `PER_NODE`/per-expansion or enforces one global counter | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-DEPTH-01` | A depth-limited search is never laundered into a complete one | A route/DAG search that cut an expandable branch at the `max_depth` bound reported `COMPLETE_WITHIN_BOUNDS` with no diagnostic; a depth-1 "complete" hid routes that provably exist at depth 2+. Fixed (`ba69169`): `SearchStatus.PARTIAL_DEPTH_LIMIT` (this codebase's name for the standard's `INCOMPLETE_DEPTH_LIMIT`, section 8.2) plus a `depth_truncated_branches` counter on both receipts, folded into `status`/`complete_within_bounds`. A >=2-missing linear branch stays a grammar boundary (not depth); a node with no cleavages stays genuinely complete | Carry the depth-limit signal into the future shared response/JSON and the four-outcome renderer | Lowering `max_depth` below a fixture's true route depth reports `PARTIAL_DEPTH_LIMIT`, never a complete/no-route | `SRCH-RCT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-RCT-8.1` | The search receipt carries the full section 8.1 engine counters | `RouteSearchReceipt` now records the section 8.1 telemetry (`2e4fbea`, schema -> v1alpha2): `nodes_visited`, `transforms_considered`, `candidates_emitted`, `candidates_rejected_by_reason{}` (sorted (reason,count): `duplicate`/`result_limit`), `search_kind`/`cut_budget_scope`, and derived `cut_enumeration_complete`/`candidate_enumeration_complete`. `search_routes` instruments them; every counter is a real measurement or explicit UNKNOWN (None), never a silent zero (section 8.1 "null, not zero"). The invariant `candidates_emitted == results_returned + sum(rejected)` is enforced and caught a real double-counting bug in the same change. **All three receipts now carry the counters** (`dc9bd21`) **and the three section 8.1 identity digests** (`453331a`: target/terminal/transform-registry, schemas v1alpha3; the transform-registry layering wrinkle resolved by a shared leaf `smartchem/transform_registry.py` so receipts and the IR stamp the SAME registry digest). **Section 8.2 status-vocabulary reconciliation now BUILT** (`5c5b619`, sub-brick 4): all three receipts gain a `standard_status` that speaks the section 8.2 vocabulary via `SearchStatus.standard_name` + `primary_standard_status` (additive, no rename); the non-1:1 residue is pinned by tests, and a 3-bearing adversarial red-team confirmed the mapping faithful (no laundering, no None leak, precedence section-8.2-legitimate) and caught 3 comment-faithfulness defects, all fixed | `IR-8.2-01` (the IR still renders the native status word; give it a section 8.2 face) and the section 8.1 receipt-on-refusal path -- **now BUILT for the two REFUSED_\* statuses** (`SRCH-REFUSE-8.1`): `decompiler.decompile_or_refuse` returns a `RefusalReceipt` carrying the section 8.2 refusal status instead of raising; ERROR_INTERNAL (a top-level guarded service) and the full null-counter SearchReceipt-on-refusal schema remain | All three engines report honest counters (emitted==results+rejected; transforms>=edges), name their target/terminal/transform-registry, AND speak the section 8.2 terminal-status vocabulary; the receipt and IR registry digests agree cross-layer | `SRCH-RCT-01` (done) | `IMPLEMENTED_AND_VERIFIED` |
| `SRCH-DIG-01` | Equivalent inventory order has equal request/result digest | Formula inventory is canonicalized/deduplicated and permutation-tested; **the shared request identity now EXISTS and canonicalizes the reagent/stock inventory** (the old "does not exist" clause is STALE — SVC-REQ-01 landed it): equivalent inventory ORDER yields a byte-identical request AND an equal `result_digest` on the structural/material path (item 4, `tests/test_cli_canonical.py::TestInventoryOrderInvariance`), the order-invariance the formula path already had | none for the alpha (decompile-side request-IR order-invariance is a named follow-on) | Formula permutations match; reagent/stock reorder → equal request AND result digest — **DONE** | `SVC-REQ-01` | `IMPLEMENTED_AND_VERIFIED` |

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
| `IR-CHEM-01` | One `ChemicalCompilationIR` connects both directions | The shared IR envelope exists (`smartchem/compilation_ir.py`) and the formula decompiler emits it via `decompile_to_ir` (`09b3072`): a versioned value with a presentation-invariant, semantic-input-sensitive digest (a search-bound change alters it even when the candidate set is identical, via `request_digest`), carrying a typed target identity, terminal-policy digest, search status/receipt digest, and canonical digest-sorted candidates. The structural (route/DAG) producer now exists too: `recompile_to_ir` (`43dbcb1`) packages `search_routes`/`search_dags` as canonical `ROUTE`/`DAG` candidates over a STRUCTURE-layer identity, with the same presentation-invariant/semantic-sensitive digest (a bound change alters it via `request_digest`; the reagent helper pool is distinguished from plain stock). IR (de)serialization now round-trips digest-stably too (`serialize_ir`/`deserialize_ir`, canonical JSON; deserialize re-validates and refuses a tampered payload). The recompiler now CONSUMES a serialized decompile artifact end to end via `recompile_from_serialized` (`2e21490`, `IR-INV-01` closed on the refusal clause): it gates the structural hypothesis on the decompiled formula and classifies the inverse outcome, with water rendering a precise mode+bounds-scoped no-route refusal (no fabricated transform). The IR now also carries a first-class `transform_registry_digest` (`7268231`) naming WHICH grammar produced its candidates (section 8.4) and making the IR digest sensitive to the grammar version (section 4.1). First-class typed `IdentityLoss` records now ride INSIDE the IR (`IR-LOSS-01` first brick landed; IR schema `v1alpha3`, `identity_losses` is `array[object]`, loss content in the IR digest, tampered/vacuous loss refused on read); the FULL section 8.1 SearchReceipt now rides INSIDE the IR too (`Section81ReceiptView`, IR schema `v1alpha4`): the ~20 mandated counters (nodes_visited, transforms_considered, candidates_rejected_by_reason, the enumeration-complete flags, stop_reason, ...) projected off any of the three engine receipts into one canonical shape, replacing the digest-only `search_receipt_digest` -- so a consumer reading the transported IR (and the `--json` response, which embeds it) sees the receipt CONTENT, not just a fingerprint; a lossy projection re-validates its OWN internal consistency on read (a tampered view -- a status contradicting its standard_status, a negative counter, an unsorted histogram -- is refused), and the IR requires the view to describe the SAME search (its status/standard_status must match the IR's). Absent counters are honest nulls (max_depth null for the formula descent, candidate_limit null everywhere -- no engine has that cap) | Wire `loss.blocks()` deeper into evidence consumers (`EVD-KEY-01`, largely done); surface the receipt content in the human render (currently a digest + the top counters) | `SRCH-RCT-01` (done), `ID-LAYER-01` | `IMPLEMENTED_AND_VERIFIED` |
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

**Uptake record — ChemicalCompilationIR carries the FULL section 8.1 SearchReceipt** (advances `IR-CHEM-01`
`IN_PROGRESS` → `IMPLEMENTED_AND_VERIFIED`; the receipt CONTENT now rides the IR, closing the "digest-only" residual
the prior IR-CHEM records named):

```text
ID:                  IR-CHEM-01 (full section 8.1 receipt -- the IR carries the ~20 mandated counters, not a digest)
files:               smartchem/compilation_ir.py, smartchem/decompiler.py, smartchem/service.py, smartchem/cli.py,
                     tests/test_compilation_ir.py, tests/test_cli_json.py, tests/test_ir_loss.py,
                     tests/fixtures/cli_json/*.json (regenerated), UPTAKE_MANIFEST_v0.5.0a1.md, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3329 passed, 14 skipped, 1 xfailed (baseline 3320; this brick + the DAG-FLOW fold). ruff clean.
the gap:             section 8.1 mandates that EVERY search return a SearchReceipt carrying ~20 counters
                     (nodes_visited, transforms_considered, candidates_rejected_by_reason{}, results_returned, the
                     three enumeration-complete flags, stop_reason, the identity/terminal/registry digests, the
                     bounds, ...), "null/UNKNOWN, not zero" for anything unmeasured. The three engine receipts
                     (RouteSearchReceipt / DAGSearchReceipt / FormulaSearchReceipt) already MEASURE these, but the
                     IR carried only their DIGEST (`search_receipt_digest`) -- a fingerprint a consumer cannot read.
built:               (1) Section81ReceiptView (compilation_ir.py, schema search-receipt-view-v1alpha1): the full
                     section-8.1 shape, with `from_receipt()` projecting off ANY of the three engine receipts. It is
                     a genuine per-TYPE bridge -- the receipts name the same section-8.1 field differently
                     (cut_budget_per_expansion vs budget; result_limit vs max_edges; results_returned vs
                     edges_emitted) and the formula descent lacks some entirely (max_depth null -- no depth bound;
                     candidates_emitted null; stop_reason is its own text while route/DAG synthesize it from the
                     section-8.2 status). candidate_limit is null on EVERY receipt -- no engine stops on a distinct
                     emitted-candidate cap (honest null, not a fake 0). FormulaSearchReceipt gained the same three
                     completeness PROPERTIES route/DAG expose, so the view reads ONE uniform surface. (2) The IR field
                     search_receipt_digest (str) -> search_receipt (Section81ReceiptView); IR schema v1alpha3 ->
                     v1alpha4; ir_to_payload/ir_from_payload carry the view; the response embeds it (its
                     search_receipt_digest is now a convenience digest OF the view). (3) Both producers pass
                     Section81ReceiptView.from_receipt(receipt) instead of receipt.digest.
why replace, not add: a section-8.1 projection is LOSSY relative to the native receipt (it drops engine-private
                     fields the standard does not ask for), so at deserialize time the view's digest CANNOT be
                     cross-checked against the native receipt.digest -- keeping both view AND digest would open a new
                     hole (an internally-consistent view beside an unrelated digest string, trusted). So the digest is
                     REPLACED by the view (the exact move IR-LOSS-01 made for identity_losses). Tamper-evidence comes
                     from the view's OWN __post_init__ re-validating its section-8.1 invariants (status<->standard_status
                     agreement, null-or-nonneg counters, sorted/distinct/positive rejection histogram, COMPLETE cannot
                     report a truncating limit) PLUS the IR requiring the view's status/standard_status to equal its
                     own (the two describe one search); as a Digestible field the view rides the IR digest.
faithfulness:        every bridged field is a real measurement or an honest null -- never a fabricated value; a
                     tampered payload is refused on read; the human render + --json now surface the receipt content
                     (the response embeds ir_to_payload), so the mandated receipt is recoverable, not hashed away.
verified:            per-type bridge pinned (route carries max_depth/cut_budget/result_limit; formula reports
                     max_depth/candidate_limit/candidates_emitted as null); candidate_limit null on every kind;
                     round-trip digest-stable; a tampered view (negative counter / contradicting standard_status /
                     unsorted histogram) refused; a view whose status contradicts the IR refused; a COMPLETE view
                     that reports result_limit_saturated refused; the CLI-JSON-01 agreement matrix + goldens
                     regenerated to the v1alpha4 shape.
residual / follow-on: the human render shows a digest + the top counters (nodes/transforms/results/stop_reason); a
                     fuller human table of the whole receipt is a display follow-on, not a semantics gap (the --json
                     view already carries every field). The response's search_receipt_digest is retained as a
                     convenience derived from the view (a stable section-13.2 surface), not a separate stored fact.
red-team:            workflow wo5cy5gnw, 4 blind bearings (bridge-correctness; tamper-soundness; faithfulness;
                     regression) + per-finding refute-by-default verify. The per-type field mapping came back a
                     PROVEN NEGATIVE (a non-circular type-aware oracle diffed every field over 15 cases + 2 real
                     searches: zero mismatches). 9 real defects CONFIRMED / 0 refuted, ALL folded before the merge:
                     (HIGH) the IR cross-checked only the view's status/standard_status, NOT its identity digests, so
                     a tampered view attributing the search to a FOREIGN target / terminal policy / transform grammar
                     (incl. a forged section-8.4 transform_registry_digest) rode inside the IR and passed
                     deserialize_ir -- the comment PROMISED "the same search" but did not ENFORCE it; now the view's
                     non-null target/terminal/transform digests MUST equal the IR's own (the InverseResult lesson:
                     enforce the coherence, do not merely document it). (MEDIUM) FormulaSearchReceipt.candidate_
                     enumeration_complete read `not result_limit_saturated`, so it was True on a PARTIAL_SEARCH_BUDGET
                     descent -- but the formula budget stop is a FATAL abort (zero candidates), so True over-claimed;
                     now `complete_within_bounds`, and the false docstring ("only max_edges can truncate") corrected.
                     (MEDIUM) the view dropped the native formula invariant transforms_considered >= edges_emitted
                     (the generic candidates_emitted>=results_returned check is vacuous for formula, where
                     candidates_emitted is None) -- now re-imposed for a FORMULA view. (LOW x4) search_kind was any
                     non-empty string (now the closed 3-kind set); candidate_limit / formula max_depth / formula
                     candidates_emitted were "honest nulls" only at projection time, not enforced on read (now
                     enforced); an old v1alpha3 payload failed with a bare KeyError not the clean schema message (now
                     schema_version is checked FIRST in ir_from_payload); Section81ReceiptView was in
                     compilation_ir.__all__ but not re-exported at the package level (now added). All pinned by
                     TestIRChemRedTeamRegressions. LESSON reaffirmed: the happy path was faithful (the NEGATIVE
                     proves it) -- every defect was a tamper-soundness / doc-truth gap on the untrusted deserialize
                     path, exactly where "a tampered payload is refused on read" had to be MADE true, not asserted.
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
| `ID-PARSE-01` | Explicit name/SMILES/InChI/formula parsing with echoed normalization | **The ONE parser service is BUILT.** `identity_parse.py` `resolve_identity` resolves EVERY section-14.2 form: NAME/SMILES → a Molecule (CONSTITUTION); FORMULA and an InChI FORMULA SUBLAYER → a FORMULA-layer identity (the InChI's `/q`,`/p` CHARGE layers are CONSUMED into a correctly-charged `Formula` — `[NH4+]` never collapses to neutral NH3, F1 red-team fold — while `/c`,`/h` connectivity, `/t`,`/b`,`/m`,`/s` stereo and `/i` isotope become typed section-5.3 BLOCKERS and any other layer is NAMED in a note); TARGET_FILE dispatches its contents. Each resolution carries a typed `ParseReceipt` (requested/resolved kind, `ParseSource`, normalised Hill form, layer, notes) ECHOED into the response `diagnostics` — surfaced in BOTH the human render and `--json` (RECEIPT-HUMAN-DROP red-team fold). Explicit `name:`/`smiles:`/`inchi:`/`formula:` prefixes + a bare `InChI=` header disambiguate; a bare formula/InChI (composition, not structure) is refused for a structure search (section 5.4). `resolve_target`/`resolve_target_with_features` are thin wrappers. REMAINING: none — the `semantic_digest` alias-collapse (`name:X`≡`X`) **LANDED** via the `SVC-REQ-01` arc (see the alias-collapse uptake record after §3.7, and §2A.5): the digest now keys on the NORMALIZED structure identity, so every spelling of one molecule collapses to ONE search identity and ONE result, the `ParseReceipt` provenance moved to its own excluded `parse_receipt_summary` field. Reconciled 2026-09-03 | none (alias-collapse closed under `SVC-REQ-01`) | Registered names pass; every explicit form round-trips; ambiguity is disambiguated not guessed; InChI charge is not dropped; alias-collapse end-to-end — **DONE** (`tests/test_id_parse.py`; alias-collapse under `SVC-REQ-01`) | `ID-LAYER-01` | `IMPLEMENTED_AND_VERIFIED` |
| `ID-STEREO-01` | Stereo/isotope/local-charge/component loss never silent | **Parse-boundary DETECTION + typed section-5.3 BLOCKER BUILT.** `smiles.py` `parse_smiles_features` now CAPTURES the isotope labels, tetrahedral (`@`/`@@`) and double-bond (`/`/`\`) stereochemistry and net-neutral local-charge separation a SMILES declares but the constitution-only `Molecule` drops (`parse_smiles` still returns the byte-identical Molecule; the feature door agrees on it). `identity.py` `stereo_loss`/`isotope_loss`/`local_charge_loss`/`representation_losses_for` lower each PRESENT feature to a typed BLOCKER (a flat/unlabelled/neutral input yields `()`, never a vacuous blanket). Wired on BOTH the recompile path (constitution kept, finer features dropped → the losses ride the IR via `recompile_to_ir`'s new `identity_losses`) and the decompile path (beside the formula-reduction blocker); the decompile render prints them from the response so human == JSON. An enantiomer/isotopologue/zwitterion no longer SILENTLY collides — it shares the flat analogue's constitution but carries a distinguishing BLOCKER; a disconnected salt stays a LOUD refusal. HONEST BOUNDARY (correcting the ID-LAYER-02 record's forward projection): this is the "record blocker" arm, NOT stereo/isotope PERCEPTION — a sound CONFIGURATION/ISOTOPIC digest needs canonical CIP / positioned-isotopologue keys and the atom-coloured `Molecule`, so `--match-layer configuration` REMAINS refused (perception deferred, not made honorable by detection). The double-bond scan is a conservative presence-check (fail-CLOSED over-detection of a redundant directional bond, documented). **Sound ISOTOPE PERCEPTION now BUILT**: `smiles.py` `isotope_refined_key`/`_isotopic_identity` compute a canonical isotope-refined-CONSTITUTION key by running the SAME proven graph canonicaliser (`_canonical_by_individualisation`) over an ISOTOPE-COLOURED copy of the graph — presentation-invariant, symmetric-position-invariant, positionally-distinct, resonance-canonical (it commits to the EXACT Kekulé structure the constitution does, so a fused benzenoid does NOT split across aromatic-vs-Kekulé spelling — ID-STEREO-01-SPLIT-KEKULE red-team fold), and it REFINES constitution. `SmilesFeatures.isotopic_digest` carries it. HONEST BOUNDARY (never faked): the key is the isotope refinement of CONSTITUTION, MODULO stereochemistry (chirality is a reflection, invisible to graph canonicalisation), so it does NOT fill the MatchLayer lattice ISOTOPIC slot (which sits above CONFIGURATION and additionally needs sound CIP-parity stereo perception) — that + CONFIGURATION remain the deferral | Sound CONFIGURATION (CIP-parity stereo) perception + the MatchLayer lattice ISOTOPIC slot is the remaining piece | Enantiomer/isotope/zwitterion/disconnected-salt do not silently collide; isotopologues are distinguishable by a sound canonical key that never splits one species — **DONE** (`tests/test_id_stereo.py`) | `ID-LAYER-01` | `IN_PROGRESS` |
| `ID-SCISS-01` | Structural scission preserves the represented rooted open valence and refuses unsupported charge | Rooted open-valence identity and neutral-only refusal are implemented; duplicate reagent types are deduplicated | Keep this scoped refusal while broader identity layers are built | Rooted isomers remain distinct; non-neutral target refuses; duplicate reagent spellings do not multiply candidates | None | `IMPLEMENTED_AND_VERIFIED` |
| `EVD-KEY-01` | Evidence key includes structure, primitive stoichiometry, direction, context and source | **The section-5.3 consumer gate is BUILT and reaches production.** `identity.py` `blocking_losses`/`is_blocked`/`blocked_claim_classes` are the consumer primitive; the sourced-evidence providers (`selectivity_of_step`/`verify_selectivity`, `reaction_conditions`/`assembly_conditions`, `kinetics_of_step`/`verify_kinetics`) take a `losses=` gate that downgrades a SOURCED verdict to a loud UNKNOWN when a BLOCKER forbids its claim class — claim-class-PRECISE (an isotope blocker gags kinetics but not selectivity; a stereo blocker does NOT touch the constitution-level handling hazard) and NON-VACUOUS. The gate is THREADED END-TO-END through the production dossier (`compile_synthesis`→`rank_routes`→`fit_route`, the public `classify_step`/`classify_route`/`classify_dag`, `draft_route_dossier`) and the `compile` CLI supplies the target's losses, so a stereo/isotope target's sourced selectivity/kinetics verdict is gated on a REAL compile/classify run — not just under direct injection. **The unified `ReactionEvidenceKey` is now BUILT** (`smartchem/evidence_key.py`): the section-9.1 value — canonical reactant/product STRUCTURE identities + PRIMITIVE (gcd-reduced) stoichiometry + direction-by-side + optional context (phase/standard-state) — isomer-distinct, scale-invariant, context-refinable. It is LIVE in the SOUND rate anchor, not a dead switch: `kinetics.py` `reaction_evidence_key`/`record_evidence_key` and `eyring.py` `_resolve_barrier` resolve sourced records THROUGH it, byte-congruent to the `(reactants, products)` tuple they replaced (`reaction_key_of` is now its `.sides` view). **The one LIVE formula-keyed borrow is now CLOSED** (red-team-hardened): `selectivity_of_step` fired a composition-only sourced record for ANY same-composition reactant — a same-composition isomer (3-aminophenol for 4-aminophenol) borrowed the verdict as `KNOWN_SOURCED`. A sourced verdict now fires ONLY when the record's `reactant_names` covers EVERY reactant and each reactant structurally resolves to a named isomer; a keyless, PARTIAL-names (naming only a safe co-reactant), or wrong-isomer reactant is a loud UNKNOWN — no composition borrow and no registry-completeness assumption. Set-based/scale-invariant; the default seed (all reactants named) is unaffected. A focused adversary broke a weaker first cut twice (partial-names reopened the borrow; "unique registered isomer" ≠ unique real isomer) — both folded (`193a3eb`). RESOLVED-as-DEAD-SWITCH (deep-scoped): the `decompiler_conditions` DECOMPOSITION path (`reaction_conditions`) and `decompiler_review` are TEST-ONLY (no live production caller — the review functions are never reached from a user command; the LIVE conditions path is `assembly_conditions`, already structure-keyed via EVD-DIR-01/02), and `reaction_conditions` structurally CANNOT build a `ReactionEvidenceKey` at its call site (it holds only `Formula`s). Migrating them would be a dead switch, so they are DEFERRED-with-reason, not built. **`context` population is now BUILT** (`EVD-KEY-CTX-01`, `77380a8`): the section-9.1 `context` field, declared-but-inert, is LIVE in the two sound rate providers via a SOURCED-or-DERIVED `phase` dimension (cyclopropane's provenance states "gas-phase" verbatim; N2O5 gas + saponification aqueous DERIVED from each record's order/units/mechanism — a step's phase from `envelope.medium` through a conservative `normalize_phase`), resolved by the new `ReactionEvidenceKey.applies_to` LOOKUP (structure+direction exact, context SUBSUMED — so a gas-phase rate is withheld from a step declared in a conflicting phase, the phase-borrow closed, while an unspecified/unrecognised medium is context-free and never regresses). `==` stays exact identity | The conditions-decomposition/review migration is deferred-with-reason (dead switch); a same-structure multi-phase table and a broader phase vocabulary are documented follow-ons | Same-formula isomer passes; a stereo/isotope/charge BLOCKER downgrades a sourced verdict end-to-end (consumer gate); the unified key is isomer-distinct/direction-specific/scale-invariant and live in kinetics/eyring; a composition-only/partial-names selectivity record cannot borrow across isomers — **DONE** (`tests/test_evd_key.py`, `tests/test_evidence_key.py`, `tests/test_selectivity.py::TestReactantSideMustBeFullyNamed`) | `STO-PRIM-01`, `ID-LAYER-01` | `IN_PROGRESS` |
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
| `DAG-FLOW-01` | Fan-out conserves intermediate quantities | The mint is now COMPUTED exactly, not blocked (the `DAGFlowError` block was the honest first cut; this is the real accounting the follow-on promised). `dag_ceiling` detects any BOUNDED reactant consumed by >=2 steps (a produced intermediate that fans out, or a finite leaf shared across steps -- feed-aware) and, instead of the naive never-decrementing propagation (which minted) or the interim block, solves the conserved MAX-YIELD LINEAR PROGRAM (new leaf `smartchem/experiment/exact_lp.py`, an exact-rational Bland's-rule simplex): maximize the final target's net production subject to per-species conservation (consumed <= fed + produced for every finite-bounded species; extents >= 0), allocating the shared reactant across its competing consumers. Choosing the yield-maximizing split invents NO allocation policy -- a ceiling is by definition the max over ALL conserved allocations, so the LP optimum IS the honest 100%-efficiency upper bound (fan-out DIOL = 1/2, exactly half the old 2x mint; shared-leaf CH4 = 1; convergent-shared = 1/2). A non-fan-out DAG keeps the byte-identical topological propagation (the LP EQUALS it -- a differential-oracle test guards the simplex); an unbounded target (no finite feed on a sink-reaching path) raises `CeilingError` rather than fabricate a number; a no-mint/no-deficit re-derivation self-checks every returned solution. `DAGCeiling.flow` (new `DAGFlow`) carries the LP extents + the fed reactants fully consumed; `per_step` stays the honest per-step breakdown for the non-coupled case (a single per-step `limiting_reactant` would misrepresent a coupled optimum). `DAGFlowError` is RETIRED. Still a latent path (no production caller; `service.py` declines DAG-mode ranking) | Wire into a DAG-mode caller: `SHOP-LEAF-02`/`STOCK-01` shopping-quantity + affordability | One mole produced and two consumed yields the exact conserved half (1/2), never a mint or a block; LP == propagation on non-fan-out; unbounded refuses — **DONE** (`tests/test_dag_flow.py`, `tests/test_exact_lp.py`) | Material quantities | `IMPLEMENTED_AND_VERIFIED` |

### 3.5 Terminal, feed, and material truth

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `TERM-POL-01` | One explicit terminal policy powers formula and route search | Formula inventory terminates; exact structural active stock now stops before expansion; commodities/available still use separate policy machinery | Implement shared `TerminalPolicy` with layer/match mode | Formula and structural target-terminal tests pass now; add equal material-policy fixtures | Shared request IR | `IN_PROGRESS` |
| `TERM-ELEM-01` | Element bucket packaging is explicit | “elements” can mean atom counts, standard-state species or stock | Serialize packaging policy in request/artifact | H/O atom buckets cannot be rendered as H2/O2 stock without declared conversion | `TERM-POL-01` | `TODO` |
| `TERM-COM-02` | Disabled/custom commodity inventory is authoritative everywhere | Current linear compile shortcut/termination/shopping respects the active inventory and `commodities=()` regression passes | Preserve through shared terminal/material policy and DAG work | `commodities=()` never uses global catalogue to stop/rank/shop | `TERM-POL-01` | `IMPLEMENTED_AND_VERIFIED` |
| `FEED-AMT-01` | Identity-only flags never invent quantity | Experimental CLI no longer maps identities to one mole and emits no finite ceiling without feed | Add explicit quantity+unit/assay input and optional symbolic ceiling separately | Identity-only poor-man fixture has no finite ceiling and no crash | `STOCK-01` desirable | `IMPLEMENTED_AND_VERIFIED` |
| `FEED-ERR-01` | Missing feed cannot abort an otherwise valid dossier | Route dossier now renders without a ceiling when feed is absent | Preserve structured diagnostic in shared response/JSON | Missing commodity amount preserves route dossier and non-internal exit status | `FEED-AMT-01` | `IMPLEMENTED_AND_VERIFIED` |
| `STOCK-01` | `StockMaterial` represents mixture, assay, quantity, source and cost | `StockMaterial` + `MaterialComponent` + `FitnessVerdict` exist (`smartchem/experiment/stock.py`, `7d27e3c`): a typed material of components (each a fraction INTERVAL), a phase, and provenance, with a rigorous `satisfies(identity, min_assay)` interval gate (vinegar -> `INSUFFICIENT_ASSAY`, a straddling requirement -> `UNKNOWN_ASSAY`, an unknown fraction never passes). The full section 10.2 schema is now built too (`3ace975`): typed `StockQuantity` (positive-finite value+unit), a `CostObservation` that cannot be constructed unless dated AND sourced (section 10.4, no invented price), plus assay method, container/storage, opened/age, jurisdiction/availability, formulation notes and known impurities -- every field keyword-optional and defaulting to an honest UNKNOWN. The `CommodityReagent` -> `StockMaterial` source-lead bridge is now built too (`stock_material_from_commodity`, §10.1): a commodity maps to an UNKNOWN-fraction, phase-UNKNOWN material so it can never silently satisfy a pure requirement. Canonical-structure component keying is now built too (ID-LAYER-01): `MaterialComponent.of_molecule`/`unknown_molecule` key a component on the canonical STRUCTURE digest (`_structure_key` -- the same `canonical_digest(m.canonical())` routes/shopping key on), and `satisfies`/`active_fraction_interval` accept a `Molecule` (structure query, the SOUND key) OR a name `str` (the weaker human-declaration key), namespaces disjoint: a same-formula CONSTITUTIONAL isomer never borrows another's assay (ethanol vs dimethyl ether; acetic vs glycolaldehyde LIVE on the bridge), a bare name never stands in for a proven structure, and the `stock_material_from_commodity` bridge is now structure-keyed (the LIVE default-data path, not merely injectable). The digest is stereo/isotope-BLIND (share a key -- the blocked ID-STEREO / deferred isotope layers; resonance/Kekule spellings ARE unified, CANON-KEKULE-01). The satisfies-gate is now WIRED to a shopping requirement: `sourcing.plan_sourcing` (a SHOP-LEAF-02 requirement judged against a StockMaterial inventory, structure-keyed) -- so a same-formula isomer on the shelf never sources a requirement. CLI surfacing + gram/volume->mol unit conversion remain | Surface the sourcing plan in the CLI; gram/volume->mol coverage (molar mass/density); COST-VEC-01 for affordability | Vinegar cannot satisfy pure acetic-acid input; a same-formula isomer never sources it | `ID-LAYER-01` | `IN_PROGRESS` |
| `SHOP-LEAF-02` | Shopping list is external, quantity-aware route input | The DAG-level quantity engine is now built (`dag_shopping_requirement`, `smartchem/experiment/dag.py`): the INVERSE of `dag_ceiling` -- given a desired final-target amount, the exact conserved per-species EXTERNAL-PURCHASE requirement. Unlike the forward ceiling's allocation range, the inverse is UNIQUELY determined: distinct-targets gives each intermediate one producer, so producing D forces every reaction extent by back-propagation, and the net (consumed minus produced, by-products CREDITED) is exact -- buy 1 mol H2 not 2 when a prior step liberates one; a fan-out is determined here though its forward ceiling is a range; a surplus co-product is reported, not bought. Each quantity is a 100%-efficiency LOWER BOUND on purchase (a real yield needs MORE), never a predicted amount. Two agreeing derivations, not the arithmetic's say-so: every step balance-checked, the final-target net asserted `== D`, and the requirement fed FORWARD through `dag_ceiling` must reproduce D exactly (the differential oracle). The ONE coupled case -- a species produced by >1 step (a target that is also a by-product) -- REFUSES (`ShoppingUnderdeterminedError`) rather than fabricate a range, naming `COST-VEC-01`. The requirement now has a CONSUMER: `sourcing.plan_sourcing` judges it against a StockMaterial inventory (the STOCK-01 integration). CLI surfacing, per-requirement commodity classification and purchased supplements remain | Surface the sourcing plan / shopping quantity in the CLI + classify each requirement against the commodity registry; the coupled range needs `COST-VEC-01` | Buy 1 mol H2 not 2 when a step liberates it; a coupled DAG refuses rather than fabricate; an inventory sources or gaps a requirement — **DONE** (`tests/test_dag_shopping.py`, `tests/test_sourcing.py`) | `DAG-FLOW-01`, `STOCK-01` | `IN_PROGRESS` |

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
| `READY-TIER-01` | Every current route dossier states its readiness | `ProcedureReadiness` exists; current drafter deliberately emits only `FORMAL_CANDIDATE` and cannot self-promote. The typed RESPONSE now carries this floor too: `ranked_route_dossiers` (CLI-CAN-02 brick 2) is populated with `RankedRouteSummary` records whose `readiness_tier` is guarded to `FORMAL_CANDIDATE` (a self-promoted tier is refused on construction) | Preserve this floor; `ProcedureIR` must govern any future higher tier | Missing operational fields produce `FORMAL_CANDIDATE`, never `BENCH_DRAFT`; the ranked response summary cannot self-promote | Procedure IR for future promotion | `IMPLEMENTED_AND_VERIFIED` |
| `READY-NAME-01` | Sparse output is called route dossier, not runnable/full procedure | Canonical API is `RouteDossier`/`draft_route_dossier`; renderer/docs use formal-candidate language. `DraftedProcedure`/`draft_procedure` and `Composability.is_runnable` remain explicit deprecated aliases | Remove compatibility aliases in a future breaking release | Canonical type/render carry readiness boundary and unresolved checklist | `READY-TIER-01` | `IMPLEMENTED_AND_VERIFIED` |
| `PROC-IR-01` | Typed procedure operations underlie any bench draft | Essential scale/addition/quench/workup/purification/analysis/waste fields absent | Add `ProcedureIR` with completeness validator | Delete any required field from fixture -> lower tier or construction failure | `STOCK-01`, hazard work | `TODO` |
| `SAFE-AUTH-01` | No emitted `PROCEED_UNATTENDED` or automatic safety authorization | Output no longer emits the label; enum member remains for compatibility only | Deprecate/remove compatibility symbol later without restoring output authority | Missing hazard record cannot yield authorization; rendered label absent | None | `IMPLEMENTED_AND_VERIFIED` |
| `SAFE-HEAT-02` | Open flame never inferred from temperature alone | Controlled electric heat is used; known flammability vetoes flame | Preserve across future equipment providers | Hot unknown/flammable medium has no flame recommendation | None | `IMPLEMENTED_AND_VERIFIED` |
| `SAFE-HAZ-01` | Missing hazard/stability data are visible blockers/unknowns | Registry missing 7/15 hazard and 13/15 stability records | Add coverage report and missing-data semantics; source records | Every commodity has positive record or explicit unknown; no unknown clears a route | `STOCK-01` | `TODO` |
| `SAFE-PROC-01` | Safety considers quantity, concentration, conditions, incompatibility, off-gas and waste | Current checks are species/free-text heuristics | Typed process hazard inputs and qualified-review gate | Same species at different concentration/scale can yield different scoped assessment | `PROC-IR-01`, `STOCK-01` | `TODO` |

### 3.7 CLI and service

| ID | Requirement | Current truth | Uptake action | Verdict-changing acceptance test | Dependencies | Status |
|---|---|---|---|---|---|---|
| `SVC-REQ-01` | One typed request/service powers chemical commands | First brick landed (`67b8ae4`): typed `CompilationRequest`/`CompilationResponse`, per-field `origin` provenance, `run_compilation` + the section 14.4 exit map, canonical serialization. **Alias-collapse landed** (this arc): the `semantic_digest` now keys on the NORMALIZED structure identity, not the raw spelling, so `paracetamol` / `name:paracetamol` / `smiles:CC(=O)Nc1ccc(O)cc1` collapse to ONE search identity AND one result (the ParseReceipt provenance moved to its own `parse_receipt_summary` field, excluded from `result_digest`; the recompile execution is canonicalised so the collapse is real end to end); a feature-bearing (stereo/isotope/charge) input keeps its own identity. `compile`/`recompile` route through the service (CLI-CAN-01); `synthesize`'s uptake is `CLI-CAN-02` (brick 1 EXPRESSED the §11 T/P constraint via a shared `PhysicalBounds` leaf; brick 2 APPLIED it to route grading + populated `ranked_route_dossiers`; the provider-lever brick (`83a078d`) made `synthesize` BUILD the shared request with its `--offline` as the LIVE §9 `EvidenceProviderSelection` that governs the network autoload, + `synthesize --emit-request`; the REMAINDER now landed -- `synthesize` renders its graded dossier through the SAME shared engine `compile` uses (`compile_synthesis`) built from the request, gained `--json`/`--emit-request` as run_compilation's machine views, and its second search/resolver is DELETED (the §9 provider lever drives the shared engine via a `stability_loader` seam; empty-reagents agrees across both views)) | Decompile-side alias-collapse (follow-on); convergent-DAG bench fitting (DAG-mode ranks nothing yet) | Equal flags across aliases → equal digests **DONE** (item 1: `synthesize`'s DEFAULT request is now byte-identical to `recompile`'s too — the last divergent-defaults gap closed, offline/depth-3/commodities-on with `--network` the explicit opt-in); every spelling of one molecule → equal request/result digest **DONE** (red-teamed: a non-canonical registry name matches its canonical SMILES on `result_digest` under real routes) | `IR-CHEM-01` | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-CAN-01` | Canonical `decompile` and `recompile`; legacy aliases share defaults | Canonical `recompile` verb landed (`df93b8c`), routed through the typed service (`run_compilation`); `decompile` gained `--json`/`--emit-request` through the same service; the legacy `compile` alias now builds the SAME typed request from the ONE shared builder (no divergent defaults) + prints a deprecation notice, so `compile … --emit-request` and `recompile … --emit-request` are byte-identical. `synthesize` now builds the shared request too (its `--max-temp`/`--max-pressure` ride the identity and its `--offline` is the LIVE §9 provider lever, `CLI-CAN-02` `83a078d`); and the CLI-CAN-02 remainder landed -- `synthesize` renders its dossier through the shared `compile_synthesis` engine (from the request) and gained `--json`/`--emit-request` through run_compilation, so its own second search/resolver is deleted | Add canonical verbs; deprecate aliases without duplicate logic | Command matrix gives equal request JSON — DONE for ALL THREE aliases incl. `synthesize` (item 1: the 7-row grid now parametrizes `synthesize` too, `--emit-request` byte-identical; the last divergence closed) | `SVC-REQ-01` | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-NAME-01` | Normal names accepted without private formatting | The full section-14.2 explicit-form surface is now exposed on the structure-search verbs. A shared resolver `identity_parse.resolve_cli_target` (the ONE place the positional target, `--input-kind`, and the explicit value-form flags `--name`/`--smiles`/`--inchi`/`--formula`/`--target-file` are reconciled -- so `recompile`/`compile`/`synthesize` cannot drift) maps every form to the ONE parser (ID-PARSE-01). Giving the target more than one way, or none, or a value-form together with `--input-kind`, is a loud INVALID_INPUT (exit 2), never a silent guess; a bare inchi/formula names composition not structure, so a STRUCTURE search refuses it (exit 2, section 5.4) -- resolved, never mis-parsed. `synthesize` gained `--input-kind` (it had none) and the value-form flags, and now ECHOES the section-14.2 ParseReceipt in its human dossier (it silently dropped it before). The stale `--input-kind` help ("inchi/formula not yet resolved offline") is corrected -- the parser resolves them; the refusal is the section-5.4 structure/composition boundary | Optional: value-forms on `decompile` (its `--smiles` is a formula-first boolean -- deferred to avoid the collision) | Registered-name and SMILES resolve; the explicit forms round-trip; ambiguity is a loud exit 2 not a guess; a bare InChI/formula is a section-5.4 exit 2 — **DONE** (`tests/test_cli_name.py`) | `ID-PARSE-01` | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-EXIT-01` | Stable exit codes separate route/no-route/partial/refusal/invalid/internal | The top-level guarded service is now BUILT: `main()` wraps command dispatch and maps ANY escaping exception to exit 70 (`ERROR_INTERNAL`) with a concise stderr line — never a raw traceback, never Python's default exit 1; argparse's own `SystemExit` (a `BaseException`, not `Exception`) passes through, so `--help` stays 0 and a bad flag stays 2. The full 0/2/3/4/5 table is observed both in-process AND through a real `python -m smartchem` subprocess, plus the controlled internal-error fixture for 70 (`tests/test_cli_exit.py`). Acceptance MET. Central error mapping across every format/path is `CLI-ERR-01`; the decompile human path still returns 0/2/4 by its own status | Central error mapping (`CLI-ERR-01`) | Codes 0/2/3/4/5 observed; controlled internal-error fixture for 70 — **DONE** (`tests/test_cli_exit.py`) | `SRCH-RCT-01`, `SVC-REQ-01` | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-ERR-01` | Invalid chemistry/numeric input yields domain error without traceback | **One central error-classification authority BUILT.** `cli.py` `_domain_exit` maps a raised domain exception to its section-14.4 code — a chemistry-MODEL-boundary refusal (`ScissionError`/`IdentityUnsupportedError`, checked FIRST since both are `ValueError` subclasses) → exit 5; an INVALID input (`IdentityParseError`/`DecompilerError`/`SmilesError`/`ValueError`/`TypeError`) → exit 2, concise stderr, NEVER a traceback; an exception in NEITHER family is RE-RAISED, so a genuine internal bug reaches `main()`'s exit-70 guard and is never laundered into a domain 2/5. `recompile`/`decompile`/`compile` all route through it (no per-command hand-rolled mapping). A `--input-kind`{auto,name,smiles,inchi,formula,target-file} flag surfaces the section-14.2 kinds; inchi/formula/target-file are a loud INVALID_INPUT (exit 2) on the human AND `--json` path of BOTH `recompile` and `compile` (the `compile`-human `--input-kind`-bypass red-team finding is fixed), never a mis-parse. REMAINING: full ID-PARSE-01 resolution of those kinds is a named POST-ALPHA follow-on. The **nonfinite-float constraint matrix is now CLOSED** (RC-STATUS-RECONCILE): with CLI-CAN-02 landed, a nonfinite/non-positive T/P constraint is a clean exit-2 domain error routed through the model-layer `PhysicalBounds` finite-and-positive rule (`constraints.py`) via the ONE classifier — no traceback (`tests/test_cli_err.py::TestNonfiniteConstraintIsACleanDomainError`) | Full ID-PARSE-01 kinds (post-alpha follow-on) | Invalid/refusal probes concise + no traceback; InChI/formula/target-file subprocess matrix exit 2; nonfinite constraint → clean exit 2 — **DONE** (`tests/test_cli_err.py`) | `ID-PARSE-01`, constraints | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-VERS-01` | Package installs `smartchem`, supports `--version`, exposes consistent `__version__` | Entry point, package metadata and `__version__` report `0.5.0a1` | Preserve single-source consistency in release packaging | Targeted script/module/version tests pass | None | `IMPLEMENTED_AND_VERIFIED` |
| `CLI-JSON-01` | Stable JSON contains request, identity, receipt, tier, blockers and route IDs | Landed (`67b4715`): `recompile`/`decompile` `--json` emit the versioned response schema; `response_schema()` is a first-class versioned descriptor of the SHAPE, cross-checked against a real payload so a golden cannot certify a drifted schema; golden fixtures (schema + 6 command responses) + an idempotent regen script; a human↔JSON agreement matrix + `response_semantic_fields()` prove neither view drops or contradicts a semantic field. **`ranked_route_dossiers` is now POPULATED** (CLI-CAN-02 brick 2): the descriptor carries a `ranked_route_summary_fields` block cross-checked against a REAL routes-found payload, the human render shows the per-route fit block, and `--json` carries the `RankedRouteSummary` objects, so the two views still agree. **`affordability_frontier` is now POPULATED** (COST-VEC-01 wired, RC-STATUS-RECONCILE): typed `AffordabilityFrontierEntry` values on a routes-mode search, empty when no route carries affordability signal (honest); and the **full §13.2 search_receipt already rides the machine payload** (`ir_to_payload`, the top-level `search_receipt_digest` is a convenience digest OF that full view — the earlier "digest not full object" clause was a false-open, corrected). Also added the §8.3 `search_space_status` field (SRCH-NO-01, carried uniformly to both the human and `--json` views) and the `provider_snapshots` field (SNAPSHOT-13.2, present-and-empty on `--json` — the alpha machine search consumes no fetched evidence; the synthesize human dossier renders a fetch's snapshot) | Add versioned serializer/schema and golden fixtures | Human and JSON agree on all semantic fields — DONE (agreement matrix over recompile + decompile, incl. the SMILES-reduction BLOCKER, the ranked fit disposition, and the §8.3 no-route label carried identically to both views) | `SVC-REQ-01`, `READY-TIER-01` | `IMPLEMENTED_AND_VERIFIED` |

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

**Uptake record — SVC-REQ-01 semantic_digest alias-collapse** (advances `SVC-REQ-01`; closes the ID-PARSE-01
follow-on the first brick's docstring confessed -- the target keyed on its raw spelling, so aliases split):

```text
ID:                  SVC-REQ-01 (alias-collapse -- the semantic digest keys on WHAT the target is, not how spelled)
files:               smartchem/service.py, smartchem/cli.py, tests/test_svc_collapse.py (new),
                     tests/test_id_parse.py, tests/test_cli_json.py, tests/fixtures/cli_json/*.json (regen)
tests:               tests/test_svc_collapse.py -- TestAliasCollapse, TestCollapseIsSound,
                     TestProvenanceExcludedFromResult, TestUnresolvableFallsBackToRawKeying, TestDecompileKeepsRawKeying,
                     TestRoundTrip, TestHumanJsonAgreeOnTheReceipt, TestRedTeamRegressions
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3158 passed, 14 skipped, 1 xfailed (baseline 3127; +31). ruff clean on every changed file;
                     git diff --check clean.
built:               The `semantic_digest` used to key on the raw `(target_input, input_kind)` pair, so
                     `paracetamol` / `name:paracetamol` / `smiles:CC(=O)Nc1ccc(O)cc1` -- which run the byte-identical
                     search -- got THREE different digests (the digest OVER-SPLIT relative to the execution).
                     (1) CompilationRequest gains a stored `normalized_identity` (schema v1alpha2->v1alpha3): the
                     builder resolves the target via the ONE parser and stores `_structure_ident(molecule)` (the
                     canonical STRUCTURE identity the engine already searches on) -- but ONLY for a FEATURE-FREE
                     molecule (empty parser-losses AND empty `representation_losses_for(...)`), else "" (raw keying).
                     `semantic_digest` keys on that via `_target_identity_key`, dropping `input_kind` (provenance)
                     once resolved -- so spellings of one molecule collapse, while a stereo/isotope/charge-declaring
                     input keeps its own identity (it can never MERGE two requests whose IRs differ by a loss).
                     (2) The ParseReceipt (provenance) is pulled OUT of `diagnostics` into a first-class
                     `CompilationResponse.parse_receipt_summary` (response schema v1alpha1->v1alpha2), surfaced in
                     both views (the section 14.3 receipt) but EXCLUDED from `result_digest`, so collapsed aliases --
                     which were READ differently -- still share a result (the section 13.1 one-way law).
                     (3) `_run_recompile` now CANONICALISES every molecule entering the search (target, reagents,
                     available, commodities), so the execution is presentation-invariant and the collapse the digest
                     claims is genuinely real end to end. Decompile keeps raw keying (no aliases; formula-layer
                     target) -- a documented follow-on.
falsifier fixture:   paracetamol / name:paracetamol / smiles:<paracetamol> -> ONE semantic_digest, ONE result_digest,
                     ONE `ir.digest` (not a hash coincidence); a ROUTES-producing molecule (dimethyl ether, acetic
                     anhydride, methylamine, all stored NON-CANONICALLY in the offline registry) matches its
                     canonical SMILES on `result_digest` -- the non-vacuous control. A stereo/isotope SMILES resolves
                     to "" and stays split from its flat twin. A TARGET_FILE never collapses. A forged
                     `normalized_identity` is refused on deserialize. Mutating only `parse_receipt_summary` leaves
                     `result_digest` unchanged.
red-team:            workflow wmw8d912y, 3 attack bearings + per-finding refute-by-default verify (7 agents, 660k
                     subagent tokens). 4 CONFIRMED, 0 refuted -- ALL folded before this commit (pinned by
                     TestRedTeamRegressions): (F1+F2, HIGH, one root) the search ran on the RAW molecule and the
                     route/candidate digests embed each Molecule POSITIONALLY, so a non-canonically-stored NAME and
                     its parser-canonicalised SMILES collapsed to one semantic_digest yet produced DIFFERENT
                     result_digests whenever the search yielded routes -- a one-way-law break the flagship paracetamol
                     example MASKED because its search is INCOMPLETE with zero candidates (a vacuous-green trap in my
                     own first test); fixed by canonicalising the search inputs (verifier-proven:
                     recompile_to_ir(name.canonical()).digest == recompile_to_ir(smiles.canonical()).digest) + a
                     ROUTES_FOUND positive control. (F3, MED) `normalized_identity` frozen at BUILD time from a
                     TARGET_FILE's then-contents could go stale vs run_compilation's re-read and MERGE with a name
                     request; fixed -- a TARGET_FILE (mutable source) never collapses. (F4, MED) request_from_payload
                     trusted a free-string `normalized_identity`, so a forged value could give one molecule's request
                     another's search identity (section 13.1 break); fixed -- deserialize RECOMPUTES it and refuses a
                     mismatch. LESSON reaffirmed: the digest collapse was sound in isolation, but it EXPOSED a latent
                     raw-order leak in the execution -- collapsing an identity ahead of the execution's real
                     invariance is itself the defect, and a positive control on the ACTUAL path (routes, not an
                     incomplete search) is what caught it.
residual / follow-on: `synthesize`'s uptake onto the shared request (CLI-CAN-02) is the remaining "route aliases
                     through it" clause; decompile-side collapse (formula-layer) is a named follow-on; the broader
                     recompile_to_ir raw-order leak is fixed at the service boundary here (a direct recompile_to_ir
                     caller still gets a raw-order-dependent digest -- canonicalising inside the IR producer is a
                     separate, wider-blast follow-on).
```

**Uptake record — CLI-CAN-02 brick 1: the typed request expresses the section-11 T/P constraint** (advances
`SVC-REQ-01`/`CLI-CAN-02`; the first step of bringing `synthesize`'s constraint levers onto the typed request):

```text
ID:                  CLI-CAN-02 (brick 1 -- the shared PhysicalBounds leaf + ConstraintPolicy carries it)
files:               smartchem/constraints.py (new), smartchem/service.py, smartchem/cli.py,
                     smartchem/experiment/drafter.py, tests/test_constraints.py (new), tests/test_service.py,
                     tests/test_cli_json.py, tests/fixtures/cli_json/*.json (regen)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3190 passed, 14 skipped, 1 xfailed (baseline 3158; +32). ruff clean on every changed file;
                     git diff --check clean.
built:               Constraints lived only in the synthesize path (experiment/cli.py -> ConstraintBox -> dossier);
                     the typed request's ConstraintPolicy was a placeholder `constraint_id` string. This makes the
                     request express a REAL section-11 T/P constraint, dodging both hazards: ONE model (no duplicate)
                     and NO layering drag.
                     (1) NEW leaf smartchem/constraints.py -- `PhysicalBounds` (max_temperature_k / min_pressure_atm /
                     max_pressure_atm), a Digestible with the CONSTR-VAL-01 finite/positive/ordered validation. It is
                     a pure leaf (contracts + stdlib only), so the service carries it WITHOUT importing drafter.py's
                     whole experiment stack.
                     (2) ConstraintBox (drafter.py) now DELEGATES its T/P validation to PhysicalBounds -- so the
                     finite/positive/ordered rules live in exactly ONE place -- while keeping its flat fields, so its
                     digest and every consumer are unchanged (verified: full raise-parity across a good/bad matrix).
                     (3) service ConstraintPolicy replaced its `constraint_id` placeholder with `bounds:
                     PhysicalBounds` (request schema v1alpha3 -> v1alpha4). It rides the `semantic_digest`, so two
                     requests declaring different bounds are different searches (section 4.1); build_recompile_request
                     grew `max_temperature_k`/`min_pressure_atm`/`max_pressure_atm` kwargs (a caller may pass a whole
                     `constraints=` policy OR bounds, not both); the CLI `recompile`/`compile` grew `--max-temp`/
                     `--max-pressure`, threaded through the ONE shared builder so the two aliases stay byte-identical.
                     HONESTY: run_compilation does NOT yet apply the constraint to route grading (verified: routes are
                     byte-identical with and without the bound); a `constraint_declared_note` disclosure rides the
                     response diagnostics AND the compile dossier, so the human AND --json views all say the bound is
                     declared-but-not-applied -- never implying the routes honor a bench limit they do not.
falsifier fixture:   PhysicalBounds refuses negative/zero/nonfinite/bool/inverted-window bounds; ConstraintBox raises
                     IFF PhysicalBounds raises on the same matrix (the ONE authority). A declared bound moves the
                     semantic_digest; the same bound shares it; the both-passed guard fires; serialize/deserialize
                     preserves the bounds + digest. CLI: `--max-temp 400 --emit-request` records the bound;
                     `compile`/`recompile` stay byte-identical under `--max-temp`; a bad `--max-temp` is exit 2 with no
                     traceback; the declared-not-applied caveat appears in recompile human, recompile --json, compile
                     --json, AND the compile human dossier.
red-team:            workflow woczmadde, 3 attack bearings + per-finding refute-by-default verify (7 agents, 507k
                     subagent tokens). 1 CONFIRMED, 3 refuted -- folded before this commit (pinned by
                     TestCliConstraintFlags): (HON-CLI-01, MED) the shared flag set let `compile` accept
                     --max-temp/--max-pressure, but `compile`'s HUMAN path renders a compile_synthesis dossier (not
                     the typed response), so it disclosed the caveat in recompile human/--json AND compile --json but
                     NOT the compile human dossier -- a silent, undisclosed constraint drop that falsified the
                     "the CLI render says so plainly" docstring claim; fixed by emitting the shared
                     `constraint_declared_note` in the compile dossier path too. Correctly REFUTED: (a)
                     PhysicalBounds.describe()'s 6-sig-fig rounding collapses 400.0 vs 400.00000001 in the human LABEL
                     -- by-design (a label, never an identity key; the digest still splits them, a 1e-8 K difference);
                     (b) an int `400` vs float `400.0` builder kwarg SPLITS the digest -- the SAFE direction of the
                     one-way law, and CLI-unreachable (--max-temp is type=float).
residual / follow-on: the constraint is DECLARED but not yet APPLIED -- run_compilation does not filter/rank routes by
                     it (bringing the dossier's ConstraintBox fitting onto the typed response is brick 2); the section-9
                     provider levers (`--offline`) and unifying run_compilation to RETURN the graded dossier are the
                     rest of CLI-CAN-02; min_pressure_atm is a builder kwarg with no CLI flag yet.
```

**Uptake record — CLI-CAN-02 brick 2: APPLY the section-11 constraint + populate `ranked_route_dossiers`** (advances
`CLI-CAN-02`, and converges `READY-TIER-01`'s "every route dossier states its readiness" onto the typed response):

```text
ID:                  CLI-CAN-02 (brick 2 -- apply the section-11 box to route ranking + the ranked response field)
files:               smartchem/service.py, smartchem/compilation_ir.py, smartchem/cli.py,
                     smartchem/experiment/compile.py, smartchem/experiment/drafter.py, tests/test_cli_can2.py (new),
                     tests/test_constraints.py, tests/test_service.py, tests/test_cli_json.py,
                     tests/fixtures/cli_json/*.json (regen)
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3222 passed, 14 skipped, 1 xfailed (baseline 3192; +30). ruff clean on every changed file.
built:               Brick 1 made the request DECLARE the T/P constraint; brick 2 APPLIES it and fills the response's
                     ranked_route_dossiers (empty since the first service brick -- the READY-TIER-01 floor).
                     (1) recompile_to_ir gains an additive `search_result=` (default None). The service searches ONCE
                     (search_routes) and reuses the SAME RouteSearchResult both to package the IR (constraint-FREE
                     candidates) and to rank the routes against the section-11 box (constraint-DEPENDENT) -- no double
                     search; a mode-mismatched precomputed result is a loud TypeError, never a silent foreign search.
                     The box stays OUT of the IR by design: the IR is the presentation-invariant search artifact two
                     different constraints share; the constraint lives in the RESPONSE.
                     (2) NEW `RankedRouteSummary` (service): a thin Digestible projection of a drafter RouteFit --
                     route_digest (== the IR candidate_digest), the fit_status (FITS/EXCLUDED/UNKNOWN/UNCONSTRAINED)
                     with exact exclusions/gaps, the READY-TIER-01 readiness floor (FORMAL_CANDIDATE, guarded against
                     self-promotion), and the ranking's four sourced verdicts so the order is inspectable. It is
                     coherence-guarded (EXCLUDED must give a reason; FITS cannot carry exclusions), (de)serialized, and
                     its digest is folded into result_digest (v1alpha1->v1alpha2) so the result identity is a TRUE
                     content hash. Response schema v1alpha2->v1alpha3; descriptor v1alpha4->v1alpha5.
                     (3) ONE note authority `constraint_note(bounds, fit_counts=...)` replaces constraint_declared_note:
                     APPLIED with the real (fit, excluded, unknown) tally when routes were ranked, DECLARED otherwise
                     (no routes, or DAG mode which does not rank yet). A constrained dimension a route leaves undeclared
                     is UNKNOWN-fit -- a GAP, never a silent pass (section 11).
                     (4) Alias coherence: compile_synthesis gains an optional `box=` (default None -> UNCONSTRAINED,
                     zero blast radius for every current caller), and `compile --max-temp` applies the SAME
                     ConstraintBox.of_bounds the recompile service uses. Both aliases surface the SAME applied note; the
                     recompile human render shows the per-route fit block and --json carries ranked_route_dossiers, so
                     the two views agree (CLI-JSON-01). The flag help text flipped from "NOT yet filtered" to APPLIED.
falsifier fixture:   RankedRouteSummary refuses a bad schema/status, a self-promoted tier, EXCLUDED-without-reason, and
                     FITS-with-exclusion; payload round-trip is identity. search_result reuse yields a byte-identical
                     IR to a fresh search; a routes/dags mode mismatch raises. A routes-found response populates ranked
                     (UNCONSTRAINED with no box; UNKNOWN under a T ceiling on an undeclared step -- never a silent
                     pass); the ranked route_digests equal the IR candidate_digests. A declared constraint moves
                     result_digest; the SAME constraint is deterministic; the SVC-REQ-01 alias-collapse SURVIVES the
                     ranked fold (name and canonical SMILES share byte-identical ranked summaries + result_digest,
                     constrained and unconstrained). serialize/deserialize preserves ranked + digest. `compile` and
                     `recompile` both report APPLIED for the same flag.
red-team:            workflow wo95gxk8l, 3 blind attack bearings (identity/one-way-law, honesty/vacuous-green,
                     guard/blast-radius) + per-finding refute-by-default verify (9 agents, 668k subagent tokens). 6
                     CONFIRMED, 0 refuted -- all folded in `3c41c6c` (pinned by TestRedTeamFolds). (HIGH) the
                     `--min-pressure` FLOOR in `_step_box_check` lacked the undeclared-dimension GAP the two ceilings
                     have, so a route whose step left pressure undeclared read as FITS -- a silent pass, and the "never
                     a silent pass" APPLIED note LIED; the floor now gaps an undeclared pressure -> UNKNOWN-fit.
                     (MED) RankedRouteSummary.__post_init__ enforced only EXCLUDED-needs-reason + FITS-no-exclusion;
                     now the FULL producer invariant (a PASS carries neither gap nor exclusion; UNKNOWN carries a gap
                     and no exclusion), so a deserialized summary cannot smuggle a silent pass. (MED)
                     _check_outcome_coherence guarded affordability-empty but not ranked-empty on the ir=None branch,
                     so a REFUSED response could smuggle a dossier into result_digest -> now refused. (MED/MED/LOW)
                     three docstrings (module scope, ConstraintPolicy HONESTY, CompilationResponse class) still
                     described the brick-1 declared-not-applied/empty behavior -> rewritten to the applied/populated
                     reality. Suite 3222 -> 3229.
residual / follow-on: DAG-mode bench fitting (convergent trees) still ranks nothing -- the note honestly says DECLARED
                     there. The section-9 provider levers (`--offline`) and returning the FULL graded dossier through
                     run_compilation are the rest of CLI-CAN-02. affordability_frontier stays empty until COST-VEC-01.
```

**Uptake record — CLI-CAN-02: `synthesize`'s `--offline` becomes the typed request's LIVE section-9 provider lever**
(advances `CLI-CAN-02`, `SVC-REQ-01` and `CLI-CAN-01`; closes the "section-9 provider levers" residual the brick-2
record named -- the last chemical verb joins the shared typed request):

```text
ID:                  CLI-CAN-02 (provider lever -- synthesize builds the shared request; --offline IS the section-9
                     EvidenceProviderSelection, and that field GOVERNS the real network autoload)
files:               smartchem/service.py, smartchem/experiment/cli.py, tests/test_synthesize_provider.py (new),
                     README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3279 passed, 14 skipped, 1 xfailed (baseline 3259; +12 feat, +8 red-team fold = +20). ruff clean.
scoped first:        `synthesize` was the ONE chemical verb still bypassing the typed request: it delegated wholesale to
                     smartchem/experiment/cli.py, whose `--offline` drove `autoload_stability(allow_network=not
                     args.offline)` DIRECTLY. recompile/compile/decompile already route through run_compilation; this
                     brick brings synthesize onto the shared request for the PROVIDER lever. Its own route engine still
                     runs below -- returning the FULL graded dossier THROUGH run_compilation is the remaining
                     CLI-CAN-02 follow-on, deliberately untouched here.
built:               (1) EvidenceProviderSelection keeps `selection_id` as its SOLE digested field, so the offline
                     default (`DEFAULT_OFFLINE`) digests byte-for-byte as before -- ZERO golden churn, every pinned
                     offline digest unmoved. It gains a fail-CLOSED `allow_network` PROPERTY (never a field, so it never
                     enters the digest): True only for an id in the closed `_NETWORK_PROVIDER_IDS` set (`DEFAULT_NETWORK`
                     today); the offline default AND any unrecognised id (even one that SOUNDS online, like "PUBCHEM")
                     resolve to offline -- an unknown provider can NEVER silently fetch, the same "decline the unknown
                     rather than guess" rule the phase normaliser uses. Module constants OFFLINE_PROVIDER/NETWORK_PROVIDER.
                     (2) synthesize builds the shared request via `_synthesize_request(args)` -> build_recompile_request,
                     threading its own resolved args (depth 2, commodities only under --poor-mans) with the provider
                     selection from --offline. Reagents/stock are passed as the RAW arg lists (tuple(args.reagents)/
                     tuple(args.have)) so --emit-request matches what the search receives even for an empty flag (a
                     red-team fold: the earlier `... if args.reagents else None` diverged for a valueless --reagents).
                     The autoload's allow_network is now READ FROM `request.evidence_provider_selection.allow_network`
                     -- ONE source of truth; the direct `not args.offline` is gone.
                     (3) synthesize gains `--emit-request`, echoing the canonical request identity (provider selection
                     included) and exiting WITHOUT searching, exactly as recompile/compile do.
digest law:          online is a genuinely different search (it may source evidence offline cannot), so NETWORK_PROVIDER
                     SPLITS `semantic_digest`; offline == the historical default on the search identity. This only ever
                     SPLITS identity, never MERGES -- the safe direction the one-way superset law (test_service) permits.
falsifier fixture:   allow_network is False for default/offline/unknown-id and True only for DEFAULT_NETWORK;
                     OFFLINE_PROVIDER is byte-identical to the default (digest unmoved); NETWORK splits semantic_digest
                     while offline leaves it unchanged. Through the PUBLIC synthesize main (a route-producing
                     invocation): --offline requests allow_network=False, no --offline requests True. The dropped-kwarg
                     KILLER forces the request to say NETWORK while argv says --offline and asserts the autoload followed
                     the REQUEST (True) -- the ONLY case where args.offline and the field disagree, so a silent revert to
                     `not args.offline` is caught. --emit-request carries the right selection_id and does NOT search.
red-team:            workflow wqpxvm0lh, 4 blind bearings (dead-switch/non-inertness, digest-law/fail-closed,
                     emit-faithfulness, regression) + per-finding refute-by-default verify (7 agents, 548k subagent
                     tokens). The two hardest bearings found the CORE SOUND: dead-switch proved the lever non-inert
                     with REAL network teeth (allow_network=True fired live pubchem/wikidata fetches, offline fired
                     zero) and the field -- not args.offline -- feeds the gate; digest-law byte-compared the pre/post
                     trees (git archive of 27bc9fd) and proved every offline digest UNMOVED + the fail-closed map robust
                     across 13 adversarial ids. 3 CONFIRMED, 0 refuted, all folded in `1ae5b14` (pinned by
                     TestRedTeamFolds). (MEDIUM) building the request BEFORE the exit-2/5 handler let an empty/whitespace
                     target or empty-string --reagents/--have regress from a clean exit 2 to exit 70 (ERROR_INTERNAL,
                     top level) / a raw traceback (exit 1, experiment entry) -- and `synthesize ''` disagreed with
                     `recompile ''` (2) on the SAME builder error, against SVC-REQ-01 alias-independence. Fixed: one
                     `_syn_domain_exit` authority wraps the build in the same 5/2 handler as the search (extended to
                     TypeError), so synthesize '' == recompile '' == exit 2 and the valueless-`--reagents` search
                     TypeError also maps to a clean 2. (LOW) --emit-request with a valueless --reagents emitted
                     helper_reagents:['water'] while the search runs with ZERO reagents -- a false identity; the manifest
                     + docstring "every knob EXPLICIT/faithful" claim was FALSE. Fixed (raw arg lists, and this record).
                     (LOW) the _synthesize_request docstring/comment "build never raises here" was false -> rewritten.
                     Suite 3271 -> 3279.
residual / follow-on: returning synthesize's FULL graded dossier THROUGH run_compilation (not just the shared request +
                     provider lever) is the remaining CLI-CAN-02 work; DAG-mode bench fitting still ranks nothing;
                     provider-VERSION sensitivity of the digest is still deferred; affordability_frontier stays empty
                     until COST-VEC-01.
```

**Uptake record — CLI-CAN-02 remainder: `synthesize`'s graded dossier renders through the ONE shared engine; its
second search + resolver are DELETED** (advances `CLI-CAN-02`, `SVC-REQ-01`, `CLI-CAN-01`; closes the "return
synthesize's FULL graded dossier through run_compilation" residual the provider-lever record named -- the last
chemical verb retires its own engine):

```text
ID:                  CLI-CAN-02 (remainder -- synthesize renders through compile_synthesis from the typed request;
                     --json/--emit-request ARE run_compilation's machine views; the second search+resolver is gone)
files:               smartchem/experiment/cli.py, smartchem/experiment/compile.py, tests/test_synthesize_provider.py,
                     tests/test_routes.py, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3287 passed, 14 skipped, 1 xfailed (baseline 3279; +8 net new tests). ruff clean on changed files.
scoped honestly:     "through run_compilation" here means exactly what it means for `compile`, the already-unified alias --
                     NOT that the dossier TEXT is produced by run_compilation (it is not, for `compile` either). The
                     MACHINE views (--emit-request, and the NEW --json) go through run_compilation; the HUMAN dossier
                     renders through the SAME shared engine `compile` uses (compile_synthesis) built from the REQUEST's
                     resolved params. What this brick removes is synthesize's OWN second engine: it no longer parses argv a
                     second time, resolves the target with a second resolver, or runs its own search_routes / rank_routes /
                     draft_route_dossier / shopping_list. `synthesize --emit-request` was already truthful about the
                     request; it is now truthful about the SEARCH too, because the search is the request's.
built:               (1) synthesize's main deletes the inline engine. The target resolves through the ONE parser service
                     (resolve_target_with_features -- the same resolution the request and run_compilation use), carrying
                     its section-5.3 losses; the dossier is compile_synthesis(target, reagents, available, commodities,
                     box=ConstraintBox.of_bounds(request.constraints.bounds), losses, ...) -- the pattern `_cmd_compile`
                     uses. So synthesize gains the brick-2 section-11 constraint bite (APPLIED + disclosed via the ONE
                     constraint_note authority) it previously lacked.
                     (2) --json: synthesize's machine contract IS run_compilation's typed response, returned with its
                     section-14.4 exit code -- identical to recompile/compile. --emit-request and --json describe the SAME
                     request (a falsifier pins request-equality across the two views).
                     (3) compile_synthesis gains an optional `stability_loader` callback, invoked AFTER its internal search
                     with exactly the species it discovered (route intermediates included), and ONLY when `stability` was
                     not passed. synthesize passes a loader that sources stability under the request's section-9 provider
                     lever (allow_network); every OTHER caller (compile) passes no loader, so its ranked result is
                     byte-identical -- ZERO golden churn, run_compilation UNTOUCHED. The section-9 lever now drives the
                     SHARED engine, not a CLI-only autoload: expressed ONCE (the request), read back in ONE place.
                     (4) the two corridors AGREE on an empty reagent pool: run_compilation (the --json path) returns
                     INVALID (exit 2) for zero helper reagents; the human path now does too (a guard mirroring
                     _run_recompile), so a valueless --reagents can never yield a water-defaulted human dossier that
                     disagrees with its own --json. The inert `--show` flag (meaningless once compile_synthesis renders the
                     alternatives itself) is REMOVED rather than left a dead switch.
falsifier fixture:   the second-engine names (search_routes/rank_routes/draft_route_dossier) are GONE from experiment.cli;
                     the human dossier carries the shared engine's COMPILED SYNTHESIS header + the L2 grade; --json returns
                     run_compilation's exit code and a typed response whose request == --emit-request's; empty --reagents
                     is exit 2 on BOTH --json and human (no traceback); the stability_loader is invoked with the ROUTE
                     species (target present) and, with NO loader, autoload is never called (it booms if it is).
                     test_routes TestCLI updated to the shared engine's output strings -- the engine changed, the facts and
                     exit codes did not (0 routes / 3 no-route complete / 4 partial / 2 bad-input).
red-team:            workflow wy3qd17qj, 4 blind orthogonal bearings (digest/golden-safety + one-way law; two-corridors
                     human<->--json consistency; provider-lever teeth / dead-switch; regression + faithfulness) +
                     per-finding refute-by-default verify. THREE bearings found the CORE SOUND: no golden churn and
                     run_compilation UNTOUCHED (compile_synthesis with no loader is byte-identical); the human and --json
                     corridors AGREE across the matrix; the section-9 lever has REAL teeth on the new path and the loader
                     covers the route species -- not a dead switch. 1 CONFIRMED, 0 refuted. (MEDIUM, faithfulness) the
                     `_synthesize_request` docstring still said "synthesize keeps its own route engine below" -- the exact
                     thing this brick DELETED -- contradicting the module docstring + the inline comment in the SAME file
                     (a stale line the provider-lever commit authored when it was true). Folded in `3640a76` (the docstring
                     now states it renders through the shared compile_synthesis engine; the two stale "the search"
                     references corrected). Docstring-only -- suite unchanged at 3287.
residual / follow-on: convergent-DAG bench fitting still ranks nothing (DAG-mode); the decompile-side alias-collapse and
                     provider-VERSION digest sensitivity stay deferred; affordability_frontier empty until COST-VEC-01.
```

**Uptake record — DAG-FLOW-01: block a fabricated quantitative ceiling over a fan-out DAG** (advances `DAG-FLOW-01`
`TODO` → `IN_PROGRESS`; the honest first cut -- BLOCK the unconserved claim, do not fabricate an allocation split):

```text
ID:                  DAG-FLOW-01 (fan-out block -- dag_ceiling refuses a conserved quantity over a fanned-out
                     intermediate; the real quantity-flow accounting is the named follow-on)
files:               smartchem/experiment/dag.py, tests/test_dag_flow.py, UPTAKE_MANIFEST_v0.5.0a1.md, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3297 passed, 14 skipped, 1 xfailed (baseline 3287; +10 new tests). ruff clean on changed files.
the defect:          `dag_ceiling` propagates the limiting-reagent max through the DAG in topological order via an
                     `available` cache set when a step produces its target but NEVER decremented when a step CONSUMES an
                     intermediate. A JOIN (a step fed by several intermediates -- convergence_points) is fine: it takes
                     the min over its branches. A FAN-OUT (one intermediate consumed by TWO steps) is NOT: each consumer
                     reads the FULL amount the single producer made, MINTING usable copies -- one mole produced, two
                     consumed, no deficit reported. Verified by a fan-out probe before the fix.
scoped honestly:     a LATENT-path guard, not a live-bug fix: `dag_ceiling` has NO production caller today (service.py
                     declines to rank DAG-mode results at all -- "DAG-mode ranks nothing"); its only callers are
                     test_dag.py and one experiments/ harness, both using JOIN-shaped (not fan-out) DAGs, so nothing in
                     the tree trips it. The brick closes the fabrication hazard BEFORE a future DAG-mode caller could.
built:               (1) SynthesisDAG.fanout_points -- the structural DUAL of convergence_points: producer indices whose
                     single produced intermediate is consumed by >=2 distinct steps (a producer's out-degree over the
                     edge list). (2) dag_ceiling raises the new DAGFlowError (a DAGError SUBCLASS, so an existing
                     `except DAGError` still catches it) when the DAG has any fan-out, naming the fanned-out
                     intermediate(s) and citing DAG-FLOW-01 -- the quantitative claim is BLOCKED, never a fabricated number.
why block, not conserve: a real conserved flow across a fan-out needs an ALLOCATION POLICY over the competing consumers
                     (proportional? priority by topological order? sourced?) -- a modeling decision the repo has not made.
                     Per the standing discipline (known physics not new; fabrication forbidden; section 10 material
                     reality), inventing a split would be fabrication. Blocking is the honest first cut; the real
                     quantity-flow accounting is the DAG-FLOW-01 follow-on.
falsifier fixture:   a constructed fan-out DAG (ethanol produced once, consumed by two steps, joined at a sink) is a
                     VALID structure (construction does not refuse it -- the STRUCTURE is admissible, only the ceiling is
                     unsound); fanout_points names the producer and is the DUAL of convergence_points (disjoint);
                     dag_ceiling RAISES DAGFlowError on it (the acceptance: one produced, two consumed -> blocker), the
                     message names the intermediate + cites the rule + says BLOCKED; DAGFlowError is a DAGError. NO false
                     positive: a join-shaped DAG (ethyl acetate) and a linear DAG WITHOUT a shared bounded reactant have
                     empty fanout_points and still ceiling exactly as before.
red-team:            workflow wr3itesl1, 4 blind bearings (detection soundness; block correctness/completeness;
                     faithfulness/latent-path; regression + other mint paths) + per-finding refute-by-default verify.
                     3 CONFIRMED, 0 refuted -- all three converged on ONE root: the block was LEAF-BLIND. fanout_points
                     (built from `_edges`, which SKIPS leaf reactants) sees only produced-intermediate fan-out, so a
                     shared BOUNDED LEAF reagent consumed by >=2 steps mints by the IDENTICAL never-decremented cache and
                     slipped through -- proven empirically (a leaf H2 fed at 1 mol, consumed by two steps, gave a ceiling
                     of 2 vs a true max of 1; a convergent DAG whose only finite charge is a shared leaf gave 1 vs 1/2).
                     Folded (`ba79c49`): the guard is now FEED-AWARE -- it blocks any BOUNDED reactant (a produced
                     intermediate, OR a leaf present in `feed`) consumed by >=2 distinct steps; a leaf ABSENT from feed is
                     excess and cannot mint, so it is not blocked (the same DAG with the leaf excess ceilings soundly).
                     Because the block now covers EVERY mint, any DAGCeiling that IS returned is genuinely conserved --
                     which keeps its "exact rational" label honest. Suite 3297 -> 3300 (+3 fold tests). The asymmetry with
                     route_ceiling (which LABELS a shared external reagent a loose upper bound rather than blocking) is
                     deliberate: the DAG ceiling promises exact conservation, so it BLOCKS what it cannot conserve.
residual / follow-on: the real conserved quantity-flow accounting across a fan-out (an allocation policy) is DAG-FLOW-01's
                     next brick, and it unblocks SHOP-LEAF-02 / STOCK-01 shopping-quantity + affordability; when DAG-mode
                     bench fitting lands (service.py), its caller must catch DAGFlowError and surface the BLOCK.
```

**Uptake record — DAG-FLOW-01: the real conserved quantity-flow accounting (max-yield LP)** (advances `DAG-FLOW-01`
`IN_PROGRESS` → `IMPLEMENTED_AND_VERIFIED`; the follow-on the block record promised -- COMPUTE the fan-out exactly,
retire the block):

```text
ID:                  DAG-FLOW-01 (fan-out real accounting -- dag_ceiling computes the conserved max-yield ceiling
                     via an exact-rational LP; DAGFlowError retired)
files:               smartchem/experiment/exact_lp.py (NEW), smartchem/experiment/dag.py,
                     smartchem/experiment/__init__.py, tests/test_exact_lp.py (NEW), tests/test_dag_flow.py,
                     UPTAKE_MANIFEST_v0.5.0a1.md, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3320 passed, 14 skipped, 1 xfailed (baseline 3300; +20 net: +13 exact_lp, test_dag_flow
                     reshaped block->compute + honesty tests). ruff clean on changed files.
the dissolved wall:  the block record said the real flow needs "an ALLOCATION POLICY over competing consumers
                     (proportional? priority? sourced?) -- a modeling decision the repo has not made", and blocking
                     until it was made. That framing was WRONG for a CEILING: a ceiling is the max achievable at 100%
                     efficiency, i.e. the maximum over ALL conserved allocations. The yield-maximizing allocation is a
                     CONSEQUENCE of that maximization, not a policy chosen ahead of it. So no policy is invented; the
                     honest ceiling is a linear program, and the LP's optimum IS the answer.
built:               (1) smartchem/experiment/exact_lp.py -- a pure leaf (stdlib + Fraction only): `maximize(c, A, b)`
                     solves `max c.x s.t. Ax <= b, x >= 0` with b >= 0 in EXACT Fraction arithmetic, single-phase
                     (the all-slack basis starts feasible), Bland's rule (no cycling), raising LPUnbounded on an
                     unbounded ray. Chosen over scipy.optimize (float) precisely to keep the CONSERVATION bound's
                     "exact rational" label true -- a float LP would import binary imprecision into a bound whose
                     whole claim is exactness. (2) dag_ceiling now ROUTES: no shared bounded reactant -> the existing
                     topological limiting-reagent propagation, BYTE-IDENTICAL (per_step StoichiometricCeilings, the
                     honest per-step limiting reagent); a shared bounded reactant -> _max_yield_ceiling, which builds
                     the conservation LP (one <= row per finite-bounded species: consumed - produced <= fed; the sink's
                     net production is the objective; coefficients are multiset multiplicity, each step cross-checked
                     via ceiling._verify_balances -- the module's two-agreeing-derivations discipline) and solves it.
                     (3) DAGCeiling gains `flow: DAGFlow | None`; DAGFlow carries the per-step extents (topological)
                     and the fed reactants fully consumed at the optimum. per_step is () in the coupled case because a
                     single limiting_reactant would be a FALSE local claim about a global optimum (a fan-out step's O2
                     at extent 1/2 is NOT what binds when 1 mol shared ethanol is split two ways). (4) DAGFlowError and
                     its detection-and-raise block are DELETED -- the fan-out is computed, not refused, so the class
                     has no remaining trigger.
hand-computed proof: fan-out fixture (1 mol ethanol -> two consumers -> join) at feed {ETHENE:1,WATER:2,O2:1,H2:1}:
                     max e3 s.t. e0<=1, e1<=1, e2<=1, e1+e2<=e0 (shared ethanol), e3<=e1, e3<=e2 -> e1=e2=1/2,
                     e3=1/2. So DIOL = 1/2 mol -- exactly HALF the old mint of 1 (each consumer had read the full
                     mole). Shared-leaf linear DAG (H2 shared, 2*CH4 per s2) at {ETHENE:10,H2:1}: max 2e2 s.t.
                     e1+e2<=1 (shared H2), e2<=e1 -> e1=e2=1/2, CH4 = 1 (mint would give 2). The SAME DAG with H2 in
                     excess ({ETHENE:10}) is not coupled -> propagation -> 20, UNCHANGED (a re-verified cross-check
                     that the LP formulation does not regress the currently-passing excess case).
faithfulness:        the LP is the faithful generalization of the "100%-efficiency idealised upper bound" the label
                     already claims -- it is that upper bound, now correctly conserved across contention instead of
                     minted. It never claims a predicted yield. Unboundedness is the ONE new honest refusal (a
                     sink-reaching path fed entirely in excess has no finite ceiling -> CeilingError), not a fabricated
                     infinity. Every returned solution is re-derived independently (no species over-consumed) before
                     it is trusted -- exactly the conservation the never-decrementing cache used to violate.
guards vs a silent-wrong simplex: (a) the exact-rational kernel is unit-pinned in isolation (tests/test_exact_lp.py:
                     known optima, a textbook anti-cycling degenerate LP, unbounded detection, exactness, shape/sign
                     contracts); (b) the DIFFERENTIAL ORACLE -- on any non-fan-out DAG the LP EQUALS the greedy
                     propagation by construction (nothing competes), asserted on the join-only and linear fixtures;
                     (c) the no-mint/no-deficit re-derivation asserted on every fan-out solution; (d) exact hand-
                     computed optima pinned for each fan-out fixture (a feasible-but-non-optimal answer would fail).
red-team:            workflow wonfm36zz, 4 blind bearings (silent-wrong-number; mint/refuse-escape; faithfulness;
                     regression) + per-finding refute-by-default verify. 7 CONFIRMED / 1 refuted -- ALL ONE ROOT,
                     folded before the merge: the FIRST cut's ROUTING was wrong. It routed to the exact LP only when
                     a shared bounded reactant was a step TARGET or was FED (a predicate `_shared_bounded_reactants`);
                     a shared bounded CO-PRODUCT / reused BY-PRODUCT (produced but no step's target, and not fed) was
                     invisible, so the DAG fell through to the naive propagation -- whose `available` cache credits
                     ONLY step targets, never by-products -- and MINTED, SILENTLY (the no-mint self-check lived only
                     on the LP path). Proven empirically: butene -> butadiene + H2 (H2 a by-product) then
                     butadiene + 2 H2 -> butane at feed {butene:1} returned 1 where the true conserved max is 1/2
                     (H2 over-consumed 2 vs 1); a co-product water reused by two hydration steps, the same 2x mint.
                     FOLD (bulletproof, no fragile predicate): the NUMBER is now ALWAYS the exact LP (`_max_yield_lp`,
                     which counts EVERY produced species -- by-products included -- so it cannot mint on any shape);
                     the propagation is kept ONLY for the per-step display and ONLY when its number MATCHES the LP (a
                     per-CALL agreement check -- two agreeing derivations); on any DAG where they differ the
                     propagation is discarded and `flow` carries the LP. This also fixed the MEDIUM: the
                     "LP == propagation on every non-fan-out DAG" claim was false (a by-product-reuse DAG is non-fan-out
                     yet mints), so the tests/docs now say "a simple tree/chain" and pin the by-product-reuse mint as a
                     regression (TestByproductReuseIsConservedNotMinted). LESSON: a structural routing predicate is a
                     place to be wrong; comparing the two derivations' NUMBERS on every call is not. Suite 3320 -> (see
                     the IR-CHEM-01 record for the combined count; +2 regression tests here).
residual / follow-on: still a latent path -- dag_ceiling has no production caller (service.py declines DAG-mode
                     ranking). This unblocks SHOP-LEAF-02 / STOCK-01 (shopping-quantity + affordability over a DAG):
                     a DAG-mode caller can now read a real conserved final-target ceiling. Non-uniqueness of the
                     optimal ALLOCATION (several vertices, same value) is expected and harmless -- the ceiling VALUE
                     is unique; only the reported extents may vary, and Bland's rule makes even those deterministic.
```

**Uptake record — CLI-NAME-01: the section-14.2 explicit-form CLI surface** (advances `CLI-NAME-01`
`IN_PROGRESS` → `IMPLEMENTED_AND_VERIFIED`; normal names accepted without private formatting, via the ONE parser):

```text
ID:                  CLI-NAME-01 (section-14.2 explicit forms --name/--smiles/--inchi/--formula/--target-file on
                     the structure-search verbs, one shared resolver, receipt echo, honest --input-kind help)
files:               smartchem/identity_parse.py, smartchem/cli.py, smartchem/experiment/cli.py,
                     tests/test_cli_name.py, UPTAKE_MANIFEST_v0.5.0a1.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              full suite green (see the combined count below). ruff clean on changed files.
the gap:             ID-PARSE-01's parser already resolves every section-14.2 form, but the CLI SURFACE lagged:
                     recompile/compile had only a positional + --input-kind; synthesize had NEITHER an --input-kind
                     nor the explicit forms and it SILENTLY DROPPED the ParseReceipt from its human dossier; and the
                     --input-kind help still claimed inchi/formula were "not yet resolved offline" -- a STALE LIE
                     (they resolve; a bare inchi/formula is refused because it names composition, not structure).
built:               (1) identity_parse.EXPLICIT_CLI_FORMS + resolve_cli_target -- the ONE resolver reconciling the
                     positional target, --input-kind, and the five value-form flags, shared by every chemical CLI so
                     they cannot drift. Exactly ONE source of the target is required: more than one, or none, or a
                     value-form combined with --input-kind (the form IS the kind), is a loud IdentityParseError ->
                     exit 2 (a concise domain error, never a silent guess). (2) recompile/compile: the positional is
                     now optional (nargs='?'), the five --name/--smiles/--inchi/--formula/--target-file flags added,
                     the request built from resolve_cli_target; the stale --input-kind help corrected to the true
                     section-5.4 structure/composition boundary. (3) synthesize: gained --input-kind + the value
                     forms (same resolver), and now resolves the target ONCE via resolve_identity and ECHOES the
                     section-14.2 ParseReceipt ("IDENTITY RESOLVED [...] via ...") in its human dossier -- the same
                     provenance recompile/decompile surface.
faithfulness:        a bare inchi/formula for a structure search is a section-5.4 exit 2 (resolved to a FORMULA-layer
                     identity that a structure search cannot use), NOT a fabricated structure and NOT a false
                     "unimplemented" -- the help now says so. An unregistered --name is a loud exit 2, never a guess.
                     One resolver = recompile/compile/synthesize cannot disagree on how a name is read.
scoped honestly:     decompile keeps its formula-first --smiles BOOLEAN idiom (a value-form --smiles there would
                     collide); the value forms live on the structure-search verbs where "a normal name" is the point.
verified:            tests/test_cli_name.py -- the resolver unit matrix (positional/kind/each form/none/two/positional+
                     form/form+kind); recompile + synthesize value-form round-trips (name/smiles resolve and search;
                     inchi/formula -> section-5.4 exit 2; ambiguity -> exit 2); synthesize --input-kind parity; the
                     synthesize receipt echo; and the --input-kind help no longer carries the stale "not yet resolved
                     offline" claim (iron-rule doc-truth).
residual / follow-on: value forms on decompile (deferred -- the --smiles-boolean collision); a fuller human render of
                     the receipt is a display nicety, not a gap (the summary line + --json already carry it).
red-team:            workflow wt52oqzwb, 4 blind bearings (resolver-soundness; cross-verb-drift; refusal-faithfulness;
                     regression) + refute-by-default verify. 2 CONFIRMED (both LOW) / 1 refuted. FOLDED: (LOW) the
                     shared resolve_cli_target was billed fail-closed but did NOT self-validate input_kind_flag --
                     an unknown/empty kind raised a bare KeyError (would launder to exit-70 for a future caller),
                     and an empty string was silently coerced to AUTO (truthiness) while the value-form branch used
                     `is not None`.  CLI-unreachable today (argparse `choices` pre-restricts), but a latent fail-open
                     in the ONE authority; now an unknown/empty kind is a loud IdentityParseError -> exit 2, checked
                     via `is not None` (pinned by test_cli_name.py). ACKNOWLEDGED, not folded (correct by design):
                     (LOW) a FEATURE-BEARING target (stereo/isotope/multi-charge) does not collapse across spellings
                     -- but that is the DELIBERATE SVC-REQ-01 boundary (`_recompile_normalized_identity` returns ''
                     on any feature loss so a loss-bearing input keeps its OWN identity and can never MERGE two
                     loss-differing searches); the one-way law holds (it over-splits, never wrongly merges), the
                     chemistry output is identical, and it is documented at the source -- "fixing" it would REINTRODUCE
                     the very merge hazard that boundary exists to prevent.  REFUTED (verifier's own conclusion): a
                     bare formula that is coincidentally valid SMILES (e.g. `CO`) resolving as SMILES on AUTO is the
                     DOCUMENTED intended AUTO behaviour and is NOT silent (the ParseReceipt echoes `AUTO->SMILES`);
                     the section-5.4 refusal guarantee is scoped to inputs DECLARED formula/inchi, and holds on every
                     path tested (--formula/--inchi/--input-kind/formula: prefix all exit 2).
```

## 4. P1 physical, data, and affordability backlog

These items may remain explicit alpha limitations only where the public renderer cannot imply a
stronger result.

| ID | Requirement | Present issue | Acceptance test | Status |
|---|---|---|---|---|
| `PTABLE-01` | Formula validation uses one supported periodic-table authority and positive integer counts | Complete table is now used; zero/negative/non-integer formula counts are refused | CaO, representative heavy elements and invalid-count regressions pass | `IMPLEMENTED_AND_VERIFIED` |
| `THERMO-UNC-01` | Carry reported uncertainty, phase, standard state and source | **Sourcing DONE + the non-vacuity discipline demonstrated (item 5, 2026-09-04); the block is LIFTED.** A fanned-out source hunt (workflow `wwom7qo7j`) established that the CODATA Key Values for Thermodynamics (Cox/Wagman/Medvedev 1989) carry REAL ± uncertainties for the common small molecules, cross-verifiable for free via the NIST WebBook -- so the old "no sourced uncertainties, fabrication forbidden" block no longer applies to that closed set. Committed as a FROZEN, dated, cited, hash-pinned reference dataset (`experiments/thermo_codata_seed.py`: 9 species with ± on both ΔfH and S°) whose validator is NON-VACUOUS -- it REFUSES a hollow uncertainty on a non-reference value while accepting a reference-state convention-zero (O2/H2/N2/graphite ΔfH=0±0 is a definition, not a hollow value). `decompiler_thermo.ThermoRef` gains a first-class `uncertainty_kj` (schema `tiered-v2`), populated from the ± already cited in each entry's provenance (ketene 1.60, paracetamol 1.9; honest `None` where the source gave none) under the same guard. **`data/thermo.py`'s `ThermoRef` wiring DONE (item 3b, this round):** it gains the same typed `uncertainty_dhf_kj` / `uncertainty_s_j_per_mol_k` (both `compare=False` → metadata, ZERO digest/golden churn, verified), populated from the SAME CODATA ± attached ONLY where it shares the value's source (no provenance mixing — reference-state ΔfH° carries the convention-zero, a NIST value with no stated ± stays honest `None`) under the same non-vacuous guard, and `resolve_thermo` surfaces it to a consumer (`tests/test_thermo_uncertainty.py`). **PROPAGATION DONE (this round, `8827306`):** σ_ΔG is now propagated through `feasibility_of_step` in quadrature (σ(ΔH)²=Σ(ν·σ_ΔfH)², σ(ΔS)²=Σ(ν·σ_S)², σ(ΔG)²=σ(ΔH)²+(T·σ(ΔS)/1000)²) and σ(log10 K) through `equilibrium_of_step` (linear in ΔG). The crux: `resolve_thermo` had DROPPED the group-additivity band `thermo_groups.estimate_thermo` already computed (destructured 5 of 7 fields) — now threaded, so a DERIVED value is distinguishable from a sourced one with no stated ±. σ is UNKNOWN when ANY species lacks a sourced σ (the honest mixed sourced/DERIVED edge — never a partial sum that understates it) and a LOWER BOUND when ≥2 species are group-derived (a **common-mode group-additivity MODEL error** — the shared Benson database + additivity assumption, present for ANY two derived estimates, NOT only ones sharing a specific group; red-team fold `5b9e8d2` corrected the earlier "shared anchors" overclaim), or a cross-phase sum, or a phase-corrected input whose band was not widened for the Δvap/Δsub correction (`ThermoRef.sigma_is_lower_bound`, the red-team's HIGH); all σ fields `compare=False` (zero digest/golden churn). A nonphysical T ≤ 0 gives σ UNKNOWN, never a negative uncertainty (red-team fold). REMAINING (named): widen the seed past the CODATA key set (CH4 etc. via version-pinned ATcT/JANAF, never fabricated — the `thermo_extended.py` prose-± lift is a candidate but needs an independent cross-check first). | The seed validates and its frozen hash matches; a hollow uncertainty is refused (non-vacuous); `data/thermo` ThermoRef carries the sourced ± identity-neutrally; σ(ΔG) matches the exact hand quadrature of the CODATA ± (2H2+O2→2H2O), is UNKNOWN when a species has no sourced σ (Haber), and is a LOWER BOUND for ≥2 derived species (`tests/test_sigma_propagation.py`, `tests/test_thermo_uncertainty.py`) | `IN_PROGRESS` |
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

**Uptake record — EVD-KEY-01: close the live selectivity composition-only reactant borrow** (advances
`EVD-KEY-01`; resolves the other two named providers as dead switches):

```text
ID:                  EVD-KEY-01 (the one LIVE formula-keyed borrow: composition-only selectivity records)
files:               smartchem/experiment/selectivity.py, tests/test_selectivity.py
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3229 -> 3232 -> 3235 passed, 14 skipped, 1 xfailed (after the red-team fold below). ruff clean.
scoped-first:        A decoupled read-only survey of the three FORMULA-keyed providers the manifest named
                     (conditions-decomposition, selectivity, decompiler_review) established which is a genuine
                     hazard-closer vs a DEAD SWITCH before any code: (a) `reaction_conditions` (the decompose path)
                     has NO live production consumer -- only `decompiler_review`'s four review functions call it, and
                     those are never reached from a user command (the LIVE conditions path is `assembly_conditions`,
                     already structure-keyed via EVD-DIR-01/02) -- AND it structurally cannot build a
                     ReactionEvidenceKey (it holds only Formulas). (b) `decompiler_review` is the same dead switch for
                     its keyed evidence. (c) `selectivity` is the ONE provider with a LIVE consumer (compile ->
                     rank_routes/classify -> dossier) and the structures to key on (`step.reactants`/`step.target`).
built:               `selectivity_of_step`: a record with empty `reactant_names` matched by reactant COMPOSITION
                     alone, so a same-composition isomer (3-aminophenol, C6H7NO, for the sourced 4-aminophenol
                     acetylation) BORROWED the verdict as KNOWN_SOURCED -- the exact "a-reaction-key-by-formula-
                     borrows-a-rate" fail-open, unclosed on the reactant side. The AIRTIGHT rule (after the red-team
                     below refuted a weaker first cut): a sourced verdict fires ONLY when the record's
                     `reactant_names` covers EVERY reactant and each reactant structurally resolves (by the registry's
                     exact canonical identity) to a named isomer. A keyless, partial-names, or wrong-isomer reactant
                     is a loud UNKNOWN -- no composition borrow, and NO registry-completeness assumption. Set-based
                     and scale-invariant (a coefficient>1 repeated reactant matches the same named isomer). The
                     default seed names all reactants, so shipped data fires exactly as before ([[a-reaction-key-by-
                     formula-borrows-a-rate]] "structural, live-not-merely-injectable" rule).
falsifier fixture:   keyless record -> UNKNOWN; partial-names (only the safe co-reactant) -> UNKNOWN (the substrate
                     borrow); a registry-lone-isomer composition-only match -> UNKNOWN (no registry assumption); a
                     fully-named correct record -> FAVORED; a fully-named record for the wrong isomer -> UNKNOWN; the
                     default seed (all reactants named) still FAVORED. tests/test_selectivity.py::
                     TestReactantSideMustBeFullyNamed.
red-team:            a focused adversary (grok-bitch:evil-morty, proportionate to a one-function guard) broke the
                     first cut TWICE (both Verified, 0 false): (HIGH) PARTIAL `reactant_names` -- naming only the
                     safe co-reactant took the names branch and skipped the check for the ambiguous substrate,
                     reopening the exact 3-aminophenol borrow (strictly WORSE than naming nothing). (MED) "unique
                     registered isomer" != unique REAL isomer -- `known_compounds` undercounts (C6H7NO has three real
                     aminophenols, one registered), so composition-only "unique" still borrowed from the unregistered
                     siblings. Folded in `193a3eb` by replacing the two mutually-exclusive branches with the one
                     airtight all-reactants-named rule above.
residual / follow-on: `ReactionEvidenceKey.context` (phase/standard-state) population; the conditions-decomposition
                     and decompiler_review migrations are DEFERRED-with-reason (dead switch: no live consumer, and
                     reaction_conditions cannot build the key). KIN-CTX-01 / SELECT-SRC-01 remain their own rows.
```

**Uptake record — EVD-KEY-CTX-01: `ReactionEvidenceKey.context` goes LIVE via a sourced phase dimension**
(advances `EVD-KEY-01`; closes the `context`-population residual the prior EVD-KEY-01 record named):

```text
ID:                  EVD-KEY-CTX-01 (the section-9.1 context field: declared-but-inert -> LIVE)
commit:              77380a8 (feat)
files:               smartchem/evidence_key.py, smartchem/data/kinetics.py, smartchem/data/eyring.py,
                     smartchem/experiment/kinetics.py, smartchem/experiment/eyring.py,
                     tests/test_evidence_key.py, tests/test_kinetics.py, tests/test_eyring.py
tests:               tests/test_evidence_key.py::TestPhaseNormalization (4), ::TestAppliesToLookup (8);
                     tests/test_kinetics.py::TestPhaseBorrow (4) + seed-phase assert; tests/test_eyring.py::
                     TestPhaseBorrow (3) + seed-phase assert
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3235 -> 3256 passed, 14 skipped, 1 xfailed (+21). ruff clean; git diff --check clean.
scoped-first:        The `context` field was fully built at the TYPE level (validated, sorted, dedup'd dimensions,
                     with_context) but line 15 of evidence_key.py named it plainly: "declared but not yet populated
                     by any provider" -- the classic dead-switch shape (capability exists, nothing produces it). A
                     read of both LIVE consumers established: (a) the field closes a REAL hazard only if BOTH sides
                     of a resolver match declare a phase -- a gas-phase sourced rate wrongly answering an aqueous
                     step (the phase-borrow, the condition-domain analogue of the isomer-borrow); (b) the step CAN
                     declare a phase -- `ConditionEnvelope.medium` -- and the records CAN carry a sourced one; (c)
                     the DECISIVE regression trap: switching the resolver to exact `==` on context turns every
                     phase-unspecified calibration step into a silent UNKNOWN. Subsumption, not equality, is the
                     sound resolver -- and every existing kinetics/eyring step is unspecified-medium, so the only
                     raw-`==` breakage in the whole suite was one assertion in test_evidence_key.py (fixed to the
                     lookup relation it now correctly asserts).
built:               (1) evidence_key.py: `normalize_phase` -- a conservative controlled-vocabulary
                     (gas/aqueous, case/space-insensitive) medium->phase map that DECLINES everything else, because
                     declining is the ONLY sound default (a context-free key matches any phase; a wrong map is the
                     sole way to manufacture a regression, and a fuzzy/substring match WOULD -- "non-aqueous"
                     contains "aqueous"). `phase_context` (the key-ready tuple or ()). `ReactionEvidenceKey.
                     applies_to` -- the LOOKUP relation: sides EXACT (structure+direction+primitive-stoich), context
                     SUBSUMED (a dimension both declare must AGREE; a dimension only one declares is unconstrained),
                     strictly weaker than `==` (which stays exact IDENTITY -- a context makes the key a finer value).
                     (2) data/kinetics.py + data/eyring.py: an OPTIONAL sourced `phase` field (default "" =
                     unspecified = context-free; backward-compatible with all positional/keyword construction).
                     Seed phases are SOURCED-or-DERIVED, never invented: cyclopropane (both providers) states
                     "gas-phase" VERBATIM in its provenance; N2O5 gas and saponification aqueous are DERIVED from
                     each record's own identity (first-order s^-1 Arrhenius; bimolecular OH- hydrolysis at molar
                     M^-1 s^-1) -- chemically compelled, but the provenance TEXT states the order/units/mechanism,
                     not the medium word (a distinction the red-team below caught the inline comments over-claiming).
                     (3) kinetics.py/eyring.py:
                     `reaction_evidence_key` populates context from `step.envelope.medium`, `record_evidence_key`
                     from the record's phase, and `_resolve_record`/`_resolve_barrier` match via `applies_to`, not
                     raw `==`.
falsifier fixture:   REAL seed data, three-way: an AQUEOUS N2O5 step -> loud UNKNOWN (the gas rate withheld -- the
                     phase-borrow closed); the SAME reaction gas-declared or phase-unspecified -> resolves (no
                     regression); an unrecognised medium ("aqueous, mild acid") -> context-free -> resolves (a
                     conservative decline never falsely refuses). Symmetric aqueous side: a gas-declared
                     saponification step does not borrow the aqueous barrier. tests/test_kinetics.py::TestPhaseBorrow,
                     tests/test_eyring.py::TestPhaseBorrow, tests/test_evidence_key.py::TestAppliesToLookup.
human-output check:  n/a at this layer (an internal resolver relation); the downstream rate verdict a phase-conflict
                     produces is the existing loud UNKNOWN reason ("no sourced ... for this exact reaction"), and the
                     full CLI-JSON golden suite is byte-unchanged (every fixture step is unspecified-medium).
JSON/schema check:   no response-schema change (context populates an INTERNAL evidence key, never a response field);
                     the CLI-JSON goldens are unchanged. The record `phase` field is additive (default "").
red-team:            workflow w7d0dcstw, 4 blind attack axes (normalizer, applies_to, regression, faithfulness) +
                     per-finding refute-by-default verify: the two HARDEST axes (normalizer soundness, applies_to
                     semantics) came back EMPTY -- the core logic held. 2 CONFIRMED, 0 refuted, both folded here:
                     (MEDIUM, regression) `with_records` dedup was phase-BLIND (keyed on (reactant,product) only),
                     so a caller injecting a gas AND an aqueous record for one structure silently lost one, and a
                     step in the dropped phase got an UNKNOWN whose reason string affirmatively LIED "no sourced
                     data ... inject a KineticRef" when the caller had injected exactly that -- the container could
                     not hold the phase-variants applies_to was built to distinguish. FIXED: the normalized phase
                     is now part of the dedup identity in both `KineticTable`/`EyringTable.with_records` (same
                     normalized phase still dedups; a real gas/aqueous pair co-resides). (LOW, faithfulness) the
                     N2O5 inline comment claimed "(provenance states so)" and the manifest said "tagged from their
                     PROVENANCE" -- but only cyclopropane's provenance states its phase verbatim; N2O5 gas and
                     saponification aqueous are DERIVED from order/units/mechanism, the text is silent on the
                     medium word (self-verified: 'gas'/'phase' not in the N2O5 provenance). FIXED: comments/tests/
                     manifest reworded to the true SOURCED-or-DERIVED status.
residual limitations:
  1. The controlled vocabulary is deliberately gas + aqueous only -- the two the seed exercises; extending it to
     more canonical phases (liquid/solid/melt/...) is a sound follow-on as sourced data needs them, never a fuzzy
     matcher.
  2. When a table holds BOTH phase-variants of one structure, a phase-UNSPECIFIED step resolves whichever the
     record iteration reaches first (both are subsumption-compatible with an unspecified step); an unspecified
     step made no phase claim, so any sourced match is defensible and its provenance names the phase, but a
     "most-specific" or ambiguity-flagging tiebreak is a documented future refinement, not built.
  3. The FORMULA-keyed providers (conditions-decomposition, decompiler_review) still do not populate context --
     they remain the EVD-KEY-01 dead-switch deferral, unchanged by this brick.
```

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

**Uptake record — SHOP-LEAF-02: the quantity-aware shopping requirement over a DAG (the inverse ceiling)**
(advances `SHOP-LEAF-02` -- the DAG quantity+by-product-credit dimensions land; CLI/commodity wiring remains, so
the row stays `IN_PROGRESS`; the first consumer DAG-FLOW-01's real accounting unblocked):

```text
ID:                  SHOP-LEAF-02 (dag_shopping_requirement -- given a target amount, the exact conserved
                     external-purchase requirement; the INVERSE of dag_ceiling)
files:               smartchem/experiment/dag.py, tests/test_dag_shopping.py (NEW),
                     UPTAKE_MANIFEST_v0.5.0a1.md, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3383 passed, 14 skipped, 1 xfailed (baseline 3361; +22, all tests/test_dag_shopping.py).
                     ruff clean on changed files (smartchem/experiment/dag.py, tests/test_dag_shopping.py).
the question:        DAG-FLOW-01 answered the FORWARD ceiling ("given this feed, what is the most final target I
                     can make?"), whose fan-out allocation is a RANGE. A chemist shops with the INVERSE ("to make
                     THIS much final target, how much of each external input must I buy?"). The non-obvious result:
                     the inverse is UNIQUELY DETERMINED for an admissible DAG even where the forward ceiling is a
                     range -- the distinct-targets invariant gives every intermediate exactly one producer, so
                     producing a fixed amount forces every reaction extent (demand propagates back uniquely), and
                     the per-species net is exact. No allocation policy, no LP-vertex ambiguity: the forward
                     range collapses because the OUTPUT is fixed, not the input.
built:               dag_shopping_requirement(dag, final_target_mol) -> DAGShoppingRequirement. (1) Back-propagate
                     the extents in REVERSE topological order: the sink's extent is fixed by the demanded amount /
                     its target multiplicity; each consumed intermediate adds to its unique producer's demand.
                     (2) Net accounting over the forced extents: consumed minus produced per species, so a
                     by-product is CREDITED against a downstream purchase (buy 1 mol H2, not 2, when the
                     dehydrogenation liberates one -- the DAG-FLOW-01 butadiene fold, inverted). requirements =
                     species with net > 0 (buy); co_products = species with net < 0 (surplus outputs), the final
                     target excluded (it is THE product). Each requirement is a 100%-efficiency LOWER BOUND on
                     purchase (a real yield needs MORE), Bucket.CONSERVATION, exact Fraction.
hand-computed proof: butadiene DAG (butene -> butadiene + H2 ; butadiene + 2 H2 -> butane), make 1 butane: the
                     hydrogenation needs 2 H2, the dehydrogenation liberates 1 -> buy butene 1, H2 1 (NOT 2).
                     Fan-out fixture (ethanol made once, consumed by two steps), make 1 DIOL: ethanol extent 2
                     (both consumers) -> buy ethene 2, O2 1, H2 1; the two by-product waters exactly feed the
                     hydration -> water net 0, neither bought nor surplus. Convergent tree with a 2-ACOH-per-run
                     branch, make 1 ester: that branch runs at extent 1/2 -> O2 = 1/2 mol (exact rational).
guards vs a silent-wrong number: (a) every step balance-checked (ceiling._verify_balances -- two agreeing
                     derivations, not the step's say-so); (b) self-check: the forced extents net EXACTLY the
                     requested amount of the final target (asserted == -D); (c) the DIFFERENTIAL ORACLE -- the
                     computed requirement is fed FORWARD through dag_ceiling and must reproduce D exactly, a
                     derivation sharing no arithmetic with the back-propagation; (d) non-vacuity: a real synthesis
                     consumes some external input, so an empty requirement is a bug (asserted).
the refusal:         the inverse is under-determined in exactly ONE case -- a species produced by MORE THAN ONE
                     step (a step's target that is ALSO a by-product of another step). Then how much to buy
                     depends on how that shared internal supply is allocated across its sources: a RANGE, not a
                     number. dag_shopping_requirement raises ShoppingUnderdeterminedError naming the species, the
                     offending steps and the follow-on (COST-VEC-01) -- it does not fabricate a number, exactly as
                     dag_ceiling refuses an unbounded target. Proven on a water DAG where water is the target of
                     one step and the by-product of another (TestCoupledRefuses).
faithfulness:        the quantities are the conservation-level inverse of the same 100%-efficiency bound
                     dag_ceiling reports, honestly labelled a LOWER BOUND on purchase (real yield < 100% needs
                     more; and a late by-product credited against an early consumption assumes recycling -- the
                     mass-balance floor, consistent with the forward LP's timing-blind global conservation). It
                     never claims a predicted purchase.
red-team:            workflow wj716si7g, 4 blind bearings (silent-wrong-number; refuse-escape; faithfulness;
                     guard-vacuity) + per-finding refute-by-default verify. 4 CONFIRMED / 1 refuted, ALL folded
                     before this commit -- two ROOTS. ROOT 1, the DETERMINACY GUARD counted GROSS producers: a
                     species merely written on both sides of a step while net-CONSUMED (a spectator / reaction
                     medium / partly-regenerated reagent) was miscounted as a producer, so a DETERMINED DAG was
                     over-REFUSED with a FALSE "it's a range" message (MEDIUM); AND the back-propagation charged the
                     GROSS consumption, so a consumer that regenerates part of its own input (water medium: consume
                     2, make 1) over-ran its producer. FOLD: the guard now counts NET producers (prod-cons>0) and the
                     back-prop charges NET consumption -- the spectator DAG now COMPUTES its unique floor (ETHENE 1,
                     H2 1, O2 1/2), not a refusal, not an over-buy (TestRedTeamFolds). ROOT 2, the DIFFERENTIAL
                     ORACLE was ONE-SIDED (sufficiency only): feeding the requirement made D, but so did an
                     OVER-report (a dropped by-product credit, H2=2 vs 1, still caps at D), so all four internal
                     guards were vacuous against the headline by-product credit (MEDIUM); a self-consuming
                     (autocatalytic) step (cyclopropane + propene -> 2 propene) slipped the guard and the docstring's
                     "distinct-targets => uniquely determined" inference was imprecise (HIGH/LOW). FOLD: the oracle is
                     now TWO-SIDED -- halving ANY bought species must strictly DROP the ceiling below D (TIGHTNESS),
                     certifying every quantity is BINDING (a real lower bound), which catches the dropped-credit
                     over-report AND certifies the autocatalytic floor is correct; and the docs now state the model
                     precisely (buy external leaves, make intermediates internally; a lower bound FOR THIS ROUTE, not
                     the cheapest alternative sourcing -- buying an intermediate is the deferred supplement feature).
                     LESSON (again, cf. DAG-FLOW-01): a structural predicate is a place to be wrong; a two-sided
                     numeric certificate on every call is not. Suite 3391 -> 3395 (+4 fold regressions).
residual / follow-on: latent, mirroring dag_ceiling -- no production caller yet. The remaining SHOP-LEAF-02
                     dimensions: wire into a DAG-mode CLI (shopping-quantity output), classify each requirement
                     against the commodity registry (commodity vs other-leaf, as compile.py already does for the
                     linear route), model purchased supplements, and -- the coupled range -- COST-VEC-01. STOCK-01
                     canonical-structure component keying + the satisfies-gate wiring is the adjacent material-
                     reality brick.
```

**Uptake record — STOCK-01: canonical-structure component keying (ID-LAYER-01)** (advances `STOCK-01`; the
sound-key dimension lands, the satisfies-gate WIRING into route/shopping selection remains, so the row stays
`IN_PROGRESS`):

```text
ID:                  STOCK-01 (canonical-structure keying -- MaterialComponent/satisfies key on structure, not a
                     fragile name; the LIVE commodity bridge is structure-keyed)
files:               smartchem/experiment/stock.py, tests/test_stock.py, UPTAKE_MANIFEST_v0.5.0a1.md, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3395 passed, 14 skipped, 1 xfailed (this brick's +8 over the 3383 SHOP-LEAF-02 baseline, plus
                     the concurrent SHOP-LEAF-02 red-team fold's +4). ruff clean on changed files.
the hazard closed:   fitness was keyed by a NAME string (casefold match).  A name is fragile both ways: a synonym
                     ("acetic acid" vs "ethanoic acid") fails to match a material it should, and -- the "keyed by
                     formula/name fails OPEN" hazard -- a query cannot be checked against a route's Molecule at all.
                     ID-LAYER-01 keys a component on the CANONICAL STRUCTURE digest instead (the same
                     canonical_digest(m.canonical()) routes/shopping use), so fitness is judged on structure.
built:               (1) `_structure_key(molecule)` -- the canonical structure digest, namespaced `struct:` so a
                     structure key and a NAME key never collide in identity_key (with the as-given fallback for a
                     molecule that cannot canonicalise). (2) `MaterialComponent.of_molecule` / `unknown_molecule` --
                     structure-keyed constructors; `known`/`unknown_fraction` stay the human-declaration NAME path
                     and now reject the reserved prefix. (3) `satisfies`/`active_fraction_interval` accept a
                     `Molecule` (structure query, matched by exact digest -- the SOUND key) OR a `str` name (matched
                     by casefold, the weaker key), the namespaces DISJOINT: a structure query matches only
                     structure-keyed components and a name query only name-keyed ones, so a bare name can never
                     stand in for a proven structure nor the reverse. (4) `stock_material_from_commodity` is now
                     STRUCTURE-keyed -- the LIVE default-data path, not merely an injectable option.
falsifier fixtures:  ethanol (CCO) and dimethyl ether (COC) share the formula C2H6O; an ethanol material does NOT
                     satisfy a dimethyl-ether Molecule query (IDENTITY_ABSENT -- no isomer borrow).  LIVE on the
                     bridge: a bridged acetic-acid commodity does NOT satisfy a glycolaldehyde (OCC=O, also C2H4O2)
                     query, while it DOES answer an acetic-acid Molecule query UNKNOWN_ASSAY (present, unproven
                     fraction).  A NAME-keyed "ethanol" component does not satisfy an ethanol Molecule query (a name
                     cannot prove a structure), and vice versa (TestCanonicalStructureKeying).
faithfulness:        the interval logic (SATISFIES only if the worst-case fraction clears the requirement, else
                     INSUFFICIENT/UNKNOWN) is unchanged -- only the KEY the components are matched on is now sound.
                     The name path is retained, honestly labelled the weaker human-declaration key, not removed.
scope (honest):      the canonical digest is CONSTITUTIONAL (connectivity), so it is STEREO-BLIND (R/S, cis/trans
                     share a key) and ISOTOPE-BLIND (H2O, D2O share a key): a material of one such isomer currently
                     satisfies a query for the other. Configuration is the BLOCKED ID-STEREO layer (real CIP
                     R/S-parity), isotopes a deferred isotope-aware digest -- NEITHER faked here; the docstrings/row
                     say "CONSTITUTIONAL isomer", not "isomer", and both limits are pinned as explicit tests so no
                     future change can silently claim soundness. Verified in-session: _structure_key IS relabel-
                     invariant (CCO==OCC; benzene aromatic==Kekule) and constitutional-isomer-distinct (ethanol/DME,
                     acetic/glycolaldehyde/methyl-formate, n-/iso-butane).
red-team:            workflow wg3b1u0ts, 4 blind bearings (fails-open; canonicalizer invariance; doc-honesty;
                     regression) + refute-by-default verify. 4 CONFIRMED / 0 refuted. THREE (fails-open + two
                     doc-honesty) were the SAME root -- the docstrings/row claimed "isomer-proof / a same-formula
                     isomer never borrows" UNQUALIFIED, but the key is stereo/isotope-blind, so a stereoisomer or
                     isotopologue query fails OPEN (SATISFIES against the other). FOLD: qualify every claim to
                     "CONSTITUTIONAL isomer" + pin stereo (test_stereoisomers...) and isotope
                     (test_isotopologues...) limitations. (This was ALSO caught in-session by my own probe before the
                     red-team returned; the working-tree fold predated the verdict.) The FOURTH (HIGH) is deeper and
                     NOT a STOCK-01 bug: `canonical()` is NON-INVARIANT across resonance spellings of FUSED aromatics
                     -- naphthalene/indole written AROMATIC vs explicit-KEKULE get DIFFERENT digests (benzene is
                     fine), so a material fails to satisfy its OWN identity written the other way (fails CLOSED). It
                     is in the shared smiles.py/category.py canonicalizer that EVERY _ident caller uses (routes,
                     DAGs, steps, shopping), predates STOCK-01, and a real fix is a deep, high-blast-radius change to
                     a foundational module needing its own design + red-team -- so it is NOT rushed into this fold:
                     filed as CANON-KEKULE-01 (P2 backlog), the desired invariant pinned as a STRICT xfail
                     (test_a_material_satisfies_its_own_identity_written_kekule...) so the fix turns it green and
                     forces removing the marker. The STOCK-01 docstrings now state this limitation honestly rather
                     than claim an invariance the canonicalizer does not provide. LESSON (recurring): a canonicalizer
                     invariant needs differential tripwires; soundness cannot self-certify it. Suite 3395 -> 3396
                     (+1 isotope test; +1 strict xfail: 1 -> 2 xfailed).
residual / follow-on: the satisfies-gate is not yet WIRED into route/shopping selection -- the payoff is matching a
                     SHOP-LEAF-02 requirement Molecule against a StockMaterial inventory (structure-keyed, so the
                     match is sound), the adjacent brick.  A structure-keyed component renders its identity as the
                     digest (a display-label resolver is a display follow-on).  COST-VEC-01 (sourced prices) and the
                     purchased-supplement range stay BLOCKED on real data / the follow-on, do NOT fake.
```

**Uptake record — CANON-KEKULE-01: resonance/Kekule-invariant canonical identity** (the STOCK-01 red-team's HIGH,
now RESOLVED at the source; a system-wide `_ident` correctness fix, `TODO` → `IMPLEMENTED_AND_VERIFIED`):

```text
ID:                  CANON-KEKULE-01 (canonical() normalises the pi-bond placement, so aromatic and explicit-Kekule
                     spellings of one molecule share one digest)
files:               smartchem/smiles.py, tests/test_canon_kekule.py (NEW), smartchem/experiment/stock.py (doc +
                     the pinned-invariant test flips xfail -> pass), UPTAKE_MANIFEST_v0.5.0a1.md, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3418 passed, 14 skipped, 1 xfailed (baseline 3397/2xfailed; +20 test_canon_kekule, +1 the
                     STOCK-01 Kekule xfail now PASSES, so 2 -> 1 xfailed). ZERO fixture churn. ruff clean on changed.
the defect:          the resonance-canonical R2 move ran ONLY over bonds the INPUT flagged aromatic (lowercase /
                     ':'). An explicit-Kekule spelling (uppercase atoms, '=' bonds) carried no flags, so a FUSED
                     aromatic (naphthalene, indole, anthracene) kept its authored double-bond graph and got a
                     DIFFERENT canonical_digest than its aromatic spelling -- a molecule failed to match itself
                     (fails CLOSED). In the shared canonicalizer EVERY _ident caller uses (routes/DAGs/steps/
                     shopping/stock), so a system-wide correctness gap, not a stock-only one. (Benzene was fine --
                     symmetric, one Kekule class.)
built:               _min_constitution_placement(atoms, bonds, charge) -- WITHOUT aromaticity perception (no Huckel,
                     no ring-aromaticity judgment, so nothing to get wrong). Each atom's pi-demand need[a] =
                     sum(order-1) is FIXED by the drawn structure; every assignment of double/triple bonds satisfying
                     that demand exactly is a resonance form of the SAME constitutional molecule; the identity is the
                     one MINIMISING canonical_digest(Molecule.canonical()) over them -- the exact R2 move, generalised
                     from aromatic-flagged bonds to the whole pi-system. Wired into the no-flag branch of BOTH
                     _build_molecule (constitution) and _isotopic_identity (the finer isotope key commits to the SAME
                     constitution-minimal placement, so it can never split what constitution unifies). A bounded
                     recursive enumeration; REFUSES (never truncates to a non-deterministic minimum) beyond the same
                     5000-placement cap the aromatic path uses.
soundness:           localised doubles are pi-demand-PINNED, so nothing over-collapses: 1-butene's double is forced
                     onto C1=C2 (need=[1,1,0,0]) and stays distinct from 2-butene (need=[0,1,1,0]); a keto/enol pair
                     keeps its distinct H-placement; a constitutional isomer keeps its skeleton. Only genuine
                     resonance (aromatic rings) has multiple placements and collapses. Verified: aromatic==Kekule for
                     benzene/naphthalene/anthracene/pyridine/furan/pyrrole/toluene/phenol/styrene/2-naphthol, and
                     ethanol!=DME, acetic!=glycolaldehyde, 1-!=2-butene, 1,3-!=1,4-cyclohexadiene, keto!=enol
                     (tests/test_canon_kekule.py). ZERO existing fixtures changed (the aromatic-flagged path is
                     byte-identical; only genuinely-resonant UNFLAGGED input moves), so the blast radius the row
                     feared did not materialise -- the fix is additive.
faithfulness:        the smiles.py module docstring's "any two Kekule drawings collapse to ONE identity" (the exact
                     claim the STOCK-01 red-team proved false for explicit-Kekule fused aromatics) is now TRUE and
                     says so, covering both the aromatic and explicit spellings; the STOCK-01 _structure_key/of_molecule
                     scope notes drop the "not yet normalised" caveat (stereo/isotope-blindness remains the honest
                     residual). The stereo/isotope walls are UNAFFECTED and still honestly named -- this fix is
                     constitutional-resonance only, not stereo perception.
red-team:            workflow wkt8s7k2j, 4 blind bearings (over-collapse; under-collapse; crash/determinism;
                     faithfulness/regression) + refute-by-default verify. The two HARDEST bearings came back EMPTY:
                     OVER-COLLAPSE **not broken** (no two distinct molecules merge -- the verifier confirmed the
                     invariant: same sigma-skeleton + same per-atom pi-demand => identical formula/H/valence, so
                     merged placements are provably resonance forms of ONE constitution; tautomers, positional
                     isomers, and even non-aromatic conjugated rings (cyclooctatetraene) stay distinct) and
                     UNDER-COLLAPSE **not broken** (every aromatic the parser accepts -- benzene, azulene, all
                     diazines, indole/quinoline/purine/carbazole, biphenyl -- unifies all its Kekule spellings to one
                     key). 1 CONFIRMED (MEDIUM) + 1 refuted, folded before this note: the pi-placement atom-walk
                     RECURSED O(n) deep and raised an UNCAUGHT RecursionError on a large cumulene/polyene ('C'+'=C'*329,
                     a UNIQUE placement far below the 5000 bound) -- a REGRESSION (such a molecule parsed fine before
                     the brick) breaking the "raises SmilesError, never crashes" contract. FOLD: the atom-walk is now
                     ITERATIVE (an explicit list stack; the per-atom distribution stays shallow-recursive over one
                     atom's few bonds), so an arbitrarily large pinned conjugated system parses correctly (330- and
                     800-cumlenes verified), no cap below the pipeline's size. Precision (verifier's non-defect note):
                     "genuine resonance" above means any conjugated/DELOCALISED-ring bond-shift, not only AROMATIC
                     rings -- those non-aromatic cases (COT) remain the SAME molecule, so identity is uncorrupted.
                     LESSON: an O(n)-deep recursion added to a foundational parser is a latent crash on valid input.
residual / follow-on: an aromatic bond is still reported against the chosen Kekule representative, not a delocalised
                     1.5-order bond (the pre-existing, stated R2 boundary -- unchanged). Stereo (ID-STEREO
                     CONFIGURATION) and isotope distinction stay their own deferred layers.
```

**Uptake record — SHOP-LEAF-02 x STOCK-01: can an inventory source a shopping requirement?** (the integration both
bricks named as their follow-on; advances `SHOP-LEAF-02` and `STOCK-01`, both stay `IN_PROGRESS` -- CLI surfacing +
unit conversion remain):

```text
ID:                  SHOP-LEAF-02 x STOCK-01 (sourcing.plan_sourcing -- a DAGShoppingRequirement judged against a
                     StockMaterial inventory, structure-keyed)
files:               smartchem/experiment/sourcing.py (NEW), tests/test_sourcing.py (NEW),
                     smartchem/experiment/__init__.py (exports), UPTAKE_MANIFEST_v0.5.0a1.md, README.md
command:             .venv/bin/python -m pytest -q -p no:cacheprovider
result:              3436 passed, 14 skipped, 1 xfailed (baseline 3418; +18 test_sourcing). ruff clean on changed.
the meeting:         SHOP-LEAF-02 says WHAT pure species to acquire and HOW MUCH; STOCK-01 says whether a real bottle
                     actually contains that species at a provable assay (keyed on canonical STRUCTURE). plan_sourcing
                     meets them: per required species, the best-matching inventory material, its FitnessVerdict, and
                     -- a SEPARATE axis -- its QuantityCoverage, exactly as the standard separates a chemical identity
                     from a material claim.
built:               plan_sourcing(requirement, inventory, *, min_assay=0.99) -> SourcingPlan of one
                     RequirementSourcing per species: (a) IDENTITY/ASSAY -- matched via
                     StockMaterial.active_fraction_interval(Molecule)/satisfies(Molecule), STRUCTURE-keyed, so a
                     same-formula isomer on the shelf is IDENTITY_ABSENT, never a source; (b) QUANTITY -- a
                     QuantityCoverage (COVERED/SHORT/UNKNOWN) computed ONLY from a mol amount with a known worst-case
                     fraction (available_lo = amount x lo), so COVERED is a PROVEN cover; a non-mol unit or undeclared
                     amount is UNKNOWN, never assumed (gram/volume->mol conversion is a named follow-on). is_sourced
                     requires BOTH proven (SATISFIES + COVERED); fully_sourced needs every line sourced AND the line
                     set non-empty -- an empty inventory makes every line IDENTITY_ABSENT and reads a gap, never green.
inherits CANON-KEKULE-01: a Kekule-drawn bottle sources an aromatic-drawn requirement (same molecule) -- the
                     resonance-invariant key flows through satisfies(Molecule) to the sourcing match
                     (test_a_kekule_drawn_bottle_sources_an_aromatic_drawn_requirement).
honesty pins:        DME (C2H6O) does NOT source an ethanol requirement (isomer soundness); a dilute structure-keyed
                     material is INSUFFICIENT_ASSAY not a source; an unknown fraction is UNKNOWN_ASSAY; a too-small
                     mol bottle is QUANTITY_SHORT; a grams bottle is coverage-UNKNOWN (SATISFIES but not sourced); an
                     empty inventory is non-vacuously all-gaps; min_assay governs the verdict (relaxed 0.90 SATISFIES
                     where strict 0.99 is UNKNOWN). tests/test_sourcing.py.
red-team:            workflow w6hqxlv8v, 4 blind bearings (false-source; coverage-honesty; doc-faithfulness;
                     crash-edge) + refute-by-default verify. 7 CONFIRMED / 0 refuted, all folded -- but ONE real
                     root (a HIGH fails-open) plus doc fixes. THE ROOT (#1 HIGH + 3 restatements): `_coverage`
                     computed the guaranteed worst-case as `amount * Fraction(lo).limit_denominator(10**9)`, and
                     limit_denominator returns the NEAREST bounded-denominator rational -- which can round the LOWER
                     bound UP (Fraction(0.9999999999).limit_denominator(1e9) == 1). So a 1 mol bottle declared at
                     worst-case 0.9999999999 against a 1 mol requirement read COVERED / is_sourced / fully_sourced
                     though the declared assay guarantees only 0.9999999999 mol -- a FALSE proven cover, falsifying
                     the "COVERED is a PROVEN cover" docstring. FOLD: drop limit_denominator entirely -- Fraction(lo)
                     is ALREADY the exact value of the (float) bound, so `available_lo = amount * Fraction(lo)` never
                     rounds above the declared worst case (regression test at fraction 0.9999999999 -> UNKNOWN, not
                     COVERED). DOC folds: the UNKNOWN enum doc now lists the reachable STRADDLE case (worst-case
                     short, best-case enough -> measure); the _best_source tie-break doc says "largest guaranteed
                     amount" (what the code ranks by), not "worst-case assay"; the _coverage except-ValueError branch
                     is marked defensive/unreachable (Fraction parses every numeric string StockQuantity's float()
                     accepts, incl. "1e3" -- the old comment's example was false). LESSON: a "cleanup" rounding on a
                     bound is a soundness bug when the bound is one-sided -- exactness beats prettiness. Suite 3437 ->
                     3438 (+1 fails-open regression).
residual / follow-on: latent like its inputs -- no CLI/service surface yet (surfacing the sourcing plan is the next
                     brick); gram/volume->mol coverage needs a molar-mass/density layer; affordability over the
                     sourced plan needs COST-VEC-01 (sourced prices, still BLOCKED -- do NOT fake). Picks ONE best
                     material per species (no multi-bottle aggregation yet).
```

## 5. P2 strengthening backlog

| ID | Direction | Why it matters | Status |
|---|---|---|---|
| `CANON-KEKULE-01` | `canonical()` normalises resonance/Kekule spellings of FUSED aromatics to one digest | **IMPLEMENTED_AND_VERIFIED** (`smiles._min_constitution_placement`): the AROMATIC and explicit-KEKULE spellings of the same molecule -- fused aromatics (naphthalene/indole/anthracene) and heteroaromatics (pyridine/furan/pyrrole) included -- now share one `canonical_digest`, WITHOUT aromaticity perception (each atom's pi-demand is fixed by the drawn structure, so localised doubles stay H-pinned and tautomers/constitutional isomers never collapse; the identity is the constitution-minimal placement over the pi-system, the R2 move generalised from aromatic-flagged bonds). Touches only the no-flag path, so aromatic-spelled molecules are byte-identical (zero fixture churn); the whole `_ident` layer (routes/DAGs/steps/shopping/stock) inherits it. `tests/test_canon_kekule.py` | `IMPLEMENTED_AND_VERIFIED` |
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

## 10. Process accessibility audit — 2026-09-05

ID: PROCESS-FIT-01 / ADMISSION-INTEGRITY-01 / AUDIT-CORRECTNESS-2026-09-05

State: IMPLEMENTED_AND_VERIFIED within the comparison and selection boundary below.

- Audited main: `2fc759542a2858605c25cd6bf660fdb56afe6975`.
- Repairs commit: `e038d734b5ef9444c389e20cbe3263f592b2f90c`.
- Process and integration commit: `5a71af75d3010bcdaf91e041cafb84c3d8af7f8d`.
- Files: `smartchem/process_constraints.py`, condition/service/CLI integration, experiment fitting and
  selection, selectivity, reagent identity, affordability/units, Arrhenius/Eyring no-net handling.
- Tests: process model/service/synthesis, workup-extrema mutations, imported-admission tampering,
  formula/isomer and sparse-registry controls, currency/invalid-number and no-net reaction regressions.
- Result: baseline 3,745 passed / 51 skipped / 1 xfailed; final 4,014 passed / 51 skipped / 1 xfailed.
  The final run partitions every test file into six deterministic shards; optional PySCF was absent.
- Human-output check: all three synthesis commands share process flags and retain no-fit blockers in
  quiet mode. No admissible candidate yields no best dossier or shopping recommendation. Complete
  no-fit searches refuse with exit 5; partial searches remain exit 4.
- JSON/schema check: request v1alpha5, response v1alpha9, descriptor v1alpha10. Unknown or excluded
  routes cannot enter the admitted route list or process-constrained affordability frontier. Returned
  candidate membership and derived admission fields are checked on import.
- Command/file inventory, environment, and raw final output:
  [validation receipt](experiments/validation/process-accessibility-2026-09-05/receipt.json).
- Residual limits: no shipped whole-process chemistry records or general importer; source applicability,
  material assays/scale, convergent process scheduling, and procedure readiness remain open. Filtering
  is over the bounded returned candidate set, not a proof that no fitting route exists elsewhere.

The complete design, audit scope, counterexamples, commands, and next acceptance contract are in
[the process accessibility audit](AUDIT_PROCESS_ACCESSIBILITY_2026-09-05.md). This does not close the
alpha's other P0 rows or promote formal candidates to bench procedures.

### 10.1 Integration-review fold — 2026-09-05 (uptake into the dev branch)

The `audit/process-accessibility-2026-09-05` work (commits `e038d73`/`5a71af7`/`327bd39`) was
fast-forwarded onto `chem-genericity-reorient-2026-09-03` (`main` untouched, nothing pushed) and
independently reviewed before acceptance.

- Independent reproduction: full suite **4055 passed / 14 skipped / 1 xfailed** (exit 0) in the dev
  venv (Python 3.12.3, PySCF 2.14.0 PRESENT — so this run's skip profile differs from the receipt's
  PySCF-absent 51-skip profile; the +270-passed delta over the local baseline is the new process/audit
  test files, `269 passed` when run alone). The 1 xfail is the pre-existing `test_laws.py` interchange
  debt (orthogonal). The live CLI path was exercised end to end: `recompile ... --process-profile quick`
  finds routes but admits none → `exit 5`, `NO_FIT_FOUND`, empty `admissible_route_digests` and frontier.
  UNKNOWN did not become FITS on the shipping path.
- Both LIVE selection predicates verified sound directly: `CompilationResponse.admissible_route_digests`
  filters `fit_status == "FITS"` (service.py), and `compile_synthesis` gates `admissible = not EXCLUDED and
  (not process_constrained or FITS)` with grade a strictly post-gate preference (compile.py) — grade
  cannot override a hard exclusion, and UNKNOWN is inadmissible under active bounds.
- **Red-team finding (CONFIRMED, folded):** the §10 line "derived admission fields are checked on import"
  OVERSTATES the guarantee on the DESERIALIZATION boundary. `response_from_payload` re-derives
  `process_selection_status`/`admissible_route_digests`/`exit_code`/`result_digest` and refuses an
  inconsistent payload, but all of them derive from the per-route `fit_status`, and the response IR carries
  no per-route `ProcessRequirements` to re-run `evaluate_process` against. So a LOCKSTEP forgery (relabel a
  REAL route's `fit_status` to `FITS`) is accepted through construction and a serialize round-trip — a
  relational check blind to a shared term, and an auditor trusting the field it polices. It is a
  trust-boundary overclaim, NOT a live exploit: the compiler never forges its own responses, and the path
  is dark on the real catalog (no route carries process metadata yet). Fix folded: honest scope docstrings
  on `admissible_route_digests` and `response_from_payload`, plus a pinning regression
  `tests/test_process_service.py::test_deserialized_admission_is_producer_declared_not_reverified`.
- **Deferred real fix (go-live milestone):** carry per-route process evidence in the response IR so
  admission is re-derived on load — this becomes load-bearing exactly when sourced whole-process records
  start flowing, and should be bundled with that work. A deserialized response is, until then, authoritative
  only from a trusted producer.

### 10.2 Process data fill — 2026-09-05 (ROUND 9)

ID: PROCESS-FIT-02 / PROCESS-DATA-SEED-01

State: IMPLEMENTED_AND_VERIFIED within the sourcing/comparison boundary below.

The process-fit gate was DARK (no shipped whole-process records, so every route was UNKNOWN-fit). This
round fills real, open-license data so the gate can honestly say FITS/EXCLUDED, not only refuse.

- **Sourcing (anti-fabrication).** A fan-out workflow extracted → cross-sourced → adversarially re-verified
  each record; the verify stage DROPPED every value not backed by a quote or a labeled derivation (it
  killed fabricated elapsed/active CEILINGS the extractor had invented). Every encoded value traces to an
  open source (LibreTexts CC BY-NC-SA 4.0, cross-checked where possible; provenance in
  `smartchem/decompiler_conditions.py`) or a labeled DERIVED constant (steam bath = 373.15 K; open vessel =
  1 atm; distillation fraction). No process fact was invented.
- **Records added (both producible by the real capped-scission search):**
  - Paracetamol acetic-anhydride acetylation — `process=` added to the existing seed record.
  - Isopentyl acetate (Fischer esterification) — new seed record. Honestly single-sourced (noted).
  - Aspirin + salicylic acid + isopentyl acetate + isopentyl alcohol registered as named structures
    (canonical-identity-invariant + Kekulé-stable, verified). Aspirin's route is NOT producible by the
    capped-scission grammar (exhaustive NO_ROUTE at depth 2-3), so it is structure-only this round
    (honest `NO_ROUTE`, not a dead seed) — a grammar-widening follow-on.
- **Floor enhancement (PROCESS-FIT-02).** Sources bound individual operations (10-min acetylation, 1-h
  reflux) but not whole-step elapsed (untimed workup/drying) — a floor with no ceiling. Added optional
  `min_elapsed_minutes`/`min_active_minutes` to `ProcessRequirements` + floor-based exclusion in
  `evaluate_process`: a SOURCED minimum already over the operator's limit EXCLUDES (the "too slow for the
  poor man" signal), while a missing ceiling stays a gap/UNKNOWN — a floor can only exclude, never confirm
  a fit. The route-total floor sum counts an interval's `.lo` as a known minimum too.
- **Acceptance (real search, not monkeypatched):** `tests/test_process_records.py` — paracetamol FITS a
  manual/periodic bench; EXCLUDED as too slow for `quick` (sourced 84-min floor > 60); EXCLUDED by missing
  equipment / stricter temperature; UNKNOWN when a constrained dimension is undeclared; does not leak to an
  unseeded reaction; isopentyl acetate FITS. Plus floor unit tests in `tests/test_process_constraints.py`.
- **Result:** full suite 4076 passed / 14 skipped / 1 xfailed (PySCF-present dev venv), exit 0.
- **Red-team (3-dimension workflow: fabrication / floor-soundness / unknown-leak+scope):** CLEAN BILLS on
  all three load-bearing dimensions (no fabricated fact; a floor cannot launder UNKNOWN→FITS; no scope or
  unknown leak). 3 confirmed findings, all LOW, all folded pre-commit: an under-documenting inline comment,
  a construction-time validation gap (`min_active` > declared elapsed ceiling now rejected), and the
  route-total floor sum now counting interval `.lo`.
- **Residual limits:** whole-step elapsed CEILINGS are UNKNOWN in the current benign-prep sources, so
  time-based FIT (vs EXCLUSION) needs sources that state total elapsed. Aspirin route needs a wider grammar.
  DAG-mode process admission stays UNASSESSED. The §10.1 deserialization boundary remains deferred.

### 10.3 Deserialization admission re-derivation — 2026-09-05 (ROUND 10, item 1)

ID: PROCESS-ADMIT-01

State: IMPLEMENTED_AND_VERIFIED on the PROCESS axis (scope + residual stated below); this is the go-live
fix the §10.1/§10.2 residual deferred ("the IR must carry per-route process evidence so admission is
re-derived on load").

The boundary §10.1 recorded: `response_from_payload`'s round-trip recompute of `admissible_route_digests`
was CIRCULAR over each route's `fit_status` (a relational check over a shared term), and the response IR
carried no per-route process evidence to re-derive from, so a LOCKSTEP relabel forgery (a real route's
`fit_status` → FITS) was accepted. Now closed on the process axis:

- **Carry the evidence.** `RankedRouteSummary` gains `process_requirements: tuple[ProcessRequirements|None]`
  — the exact per-step declared process facts the fit was computed from, one per route step in order. It is
  route identity (folded into `result_digest`), serialized/round-tripped (new `_process_requirements_*`,
  `_interval_*`, `_source_*` payload helpers). Schema bumps: response v1alpha9→v1alpha10, ranked-summary
  v1alpha1→v1alpha2, descriptor v1alpha10→v1alpha11 (request UNCHANGED).
- **Re-derive on load.** `process_constraints.evaluate_process_requirements` re-derives the process fit
  straight from carried requirements (byte-for-byte what `evaluate_process` computes from the matching
  envelopes — it now delegates through the shared `_evaluate_requirements` core).
  `CompilationResponse._check_process_admission_coherence` (in `__post_init__`, so it fires at construction
  AND on load) enforces the SOUND one-directional rule: the process component is a lower bound on the
  combined verdict, so a declared FITS/UNKNOWN whose PROCESS evidence re-derives to a stricter verdict is
  refused. Gated on `process.constrains_anything` (zero overhead on the default path). Verified it never
  false-rejects an honest response (rank-time bounds == load-time bounds, service.py:1692 vs :1100).
- **SCOPE (honest, not overclaimed).** `fit_status` is the COMBINED verdict (composability + physical bounds
  + process); this re-derives ONLY the process component. The blind `evil-morty` red-team CONFIRMED (I
  reproduced it independently, `scratchpad/verify_finding1.py`) that a route EXCLUDED for a NON-process
  reason (e.g. a reaction over a physical temperature cap) whose process evidence is FITS can still be
  bare-relabeled to FITS and admitted — the physical/reagent/equipment/composability axes carry only
  free-text exclusions/gaps, and re-deriving them needs the per-step physical conditions + the full
  ExperimentRoute graph the thin projection deliberately omits. The red-team's overclaim finding (my
  docstrings said the bare relabel was closed *generally*) is FOLDED: docstrings on
  `admissible_route_digests` / `response_from_payload` / `_check_process_admission_coherence` now state the
  process-axis scope precisely, and `tests/test_process_service.py::test_non_process_axis_relabel_is_not_yet_authenticated`
  PINS the true boundary. Red-team clean bills earned: soundness/no-false-reject, byte-for-byte
  re-derivation, no construction-skip read path, edge cases (empty tuple / None-vs-unknown), alias-collapse,
  no fabrication.
- **Tests.** `tests/test_process_service.py`: the old boundary-pin test INVERTED
  (`test_deserialized_admission_is_re_derived_not_blindly_trusted` — the bare process-axis relabel is now
  rejected at construction AND on load) + `test_admission_residual_needs_a_signature_to_close` (the
  controlling-forger residual) + the new non-process-axis boundary pin. Goldens regenerated.
- **Result:** full suite 4078 passed / 14 skipped / 1 xfailed (PySCF-present dev venv), exit 0. ruff clean.
- **Residual → next-step (COMBINED-VERDICT-AUTH):** full authentication of a deserialized
  `admissible_route_digests` (all three verdict axes + a fully controlling forger who fabricates coherent
  evidence and recomputes `result_digest`) needs a PRODUCER SIGNATURE over the payload, or a full
  re-derivation that carries the ExperimentRoute graph (contradicting the thin projection). Named on the
  roadmap; not attempted here.

### 10.4 Whole-step total-elapsed sourcing — 2026-09-05 (ROUND 10, item 2)

ID: PROCESS-TIME-CEILING-01

State: VERIFIED NEGATIVE (committed, reproducible). No code change to the gate — the honest outcome is that
no sound ceiling is sourceable, and the anti-fabrication directive forbids inventing one.

The §10.2 residual asked for whole-step total-elapsed data to unlock a time-based FIT (a ceiling), not just
floor-based EXCLUSION. A fan-out workflow (find → adversarial verify) swept five open-license source families
(LibreTexts, Organic Syntheses, OER lab manuals, Wikipedia/Wikibooks, PubChem/NIST) for a whole-process total
elapsed (start to dried product, INCLUDING untimed workup/drying) for the two seeded preps.

- **Result: 9 candidate values, 0 confirmed totals.** Every value the finders surfaced was a PARTIAL step
  time (reaction/reflux, ice-bath sit, decolorizing, recrystallization interval); the verify stage rejected
  all nine because none is a whole-process total — workup and drying are left untimed across the benign-prep
  literature. So no sound whole-step CEILING exists to encode.
- **Consequence.** Time-based process admission stays FLOOR-ONLY (a sourced minimum can EXCLUDE, never
  CONFIRM). The ROUND-9 floor-only model is thus DILIGENCE-BACKED, not a shortcut. The search also
  independently re-verified every sourced step time behind the ROUND-9 floors (paracetamol 84/14 min,
  isopentyl 60 min) — corroboration, not a change.
- **Anti-fabrication.** A DERIVED ceiling was refused: bounding the untimed manual workup/drying would
  require inventing operator behavior, which is not known-physics derivation.
- **Artifact (committed, reproducible):** `experiments/validation/total-elapsed-sourcing-2026-09-05/`
  (`receipt.json` with the five families, nine findings, all rejections, and the corroborated floors; plus
  the committed workflow script).
- **Residual → next-step:** a time-based FIT needs a source genre that states whole-process totals
  (industrial/pilot process docs with cycle times, patent examples with run+workup schedules) — none is an
  open-license benign teaching prep. Stays open on the roadmap.

## 11. ROUND 11 — the four-item full-blast round (2026-09-05)

Off ROUND 10 (`main` at `122a6b2`, untouched during the build). Four deliverables, each
design → Citadel recon → build → REPRODUCE the finding myself → evil-morty red-team → fold → verify.
Final full suite **4097 passed, 14 skipped, 1 xfailed** (dev venv, PySCF present). All committed on the dev
branch `chem-genericity-reorient-2026-09-03`; merged to `main` this round (see the release note below).

### 11.1 COMBINED-VERDICT-AUTH — the producer signature (★; `f32b0b4`)

The honest close of the evil-morty Finding-1 deserialization boundary (ROUND 10 §10.3 residual), for the ONE
threat a signature can actually address. `response_to_payload`/`serialize_response` take an optional
`signing_key` and emit a `producer_signature` (HMAC-SHA256 over `result_digest`, which transitively covers every
route's `fit_status`/`process_requirements`/`exclusions`); `response_from_payload`/`deserialize_response` take a
`verification_key` + `require_signature` and refuse a KEYLESS out-of-band tamper — even a coherent one that
recomputes `result_digest`, and even on the physical/composability axes PROCESS-ADMIT-01 cannot re-derive.
`resolve_producer_key()` reads an env var or an auto-created 0600 keyfile. **Strictly OPT-IN**: with no key the
payload is byte-identical (`producer_signature` null), so every existing caller and golden fixture is unchanged.
**Honest scope:** it does NOT close a key-holding / in-process forger (they construct-then-sign); NO signature
can, and `test_key_holding_forger_residual_is_not_closable_by_a_signature` pins that irreducible residual.
Schemas: response `v1alpha10 → v1alpha11`, descriptor `v1alpha11 → v1alpha12`. Verified: transport-tamper
rejection + wrong-key + require-signature enforcement (`tests/test_process_service.py`).

### 11.2 item 4 — a third sourced whole-process record (`2990717`)

Methyl salicylate (oil of wintergreen): salicylic acid + methanol → methyl salicylate, a Fischer esterification
the capped-scission search already produces. Sourced from LibreTexts "Experiment 731: Esters" (Los Medanos
College, **CC BY**, license re-confirmed verbatim). A find → adversarial-verify fan-out **killed a `agitation=MANUAL`
value** (misattributed from a post-reaction workup step, not the reaction) and **refused two candidates** —
acetanilide (license "not declared") and ethyl acetate (zero numeric process data) — as honest negatives, no
fabrication. `workup_included=False` (the source's only post-reaction step is a QUALITATIVE detection, not a
preparative isolation), so this record can EXCLUDE or be UNKNOWN, **never a false FITS**. Acceptance on the real
search (`tests/test_process_records.py`): UNKNOWN on a covering bench (workup + agitation undeclared), EXCLUDED
by stricter temperature / missing equipment / too-slow step budget.

### 11.3 item 5b — DAG-mode process admission (`f32b0b4`); item 5a — honest defer

`dag_process_fit` runs the linear process gate over a topological flattening of a convergent DAG — **sound**
(never a false FITS) but **over-conservative on time** (it serial-sums concurrent branches). A DAG-mode compile
now surfaces a clearly-bounded diagnostic reporting only the SOUND lower bound (how many DAGs fit even run
serially); `process_selection_status` stays UNASSESSED (DAGs get no formal admission yet). The correct
critical-path elapsed aggregation + full DAG RouteDossier admission remain a named next step (a genuine design
fork). **item 5a** (richer check_interval / drying modeling) is an honest DEFER: it needs a `ProcessPhase`
sub-step schema, not more data — fabricating a drying ceiling is refused (§10.4).

### 11.4 item 3 — resonance-canonical identity unblocks aspirin (CANON-KEKULE-01; `fb6dc4c`)

**The brief was re-diagnosed.** It asked to "widen the grammar for aspirin"; recon (reproduced) proved aspirin's
NO_ROUTE was NOT a grammar gap — capped-scission ALREADY emits aspirin + acetic acid → acetic anhydride +
salicylic acid (the reverse of the real industrial synthesis). The bug was in the CANONICALIZER: `Molecule.canonical()`
minimizes over literal bond orders with no resonance notion, so an ORTHO-disubstituted salicylate FRAGMENT cut
out of aspirin carried a different Kekulé pattern than the SAME species parsed from SMILES, and `_ident` called
them distinct (para/paracetamol survived by geometric accident; ortho/meta did not). Fix: `resonance_canonical`
lifts the parser's proven `_min_constitution_placement` onto an arbitrary Molecule; `resonance_identity` (now
shared byte-identical by `routes._ident`, `step._ident`, `dag._ident`, `compilation_ir._structure_ident`) unifies
a fragment with its parsed form. Aspirin compiles to its real route.

- **Sound, not over-unifying (evil-morty verified):** it only re-distributes multiple-bond orders preserving each
  atom's per-atom pi-demand + fixed H-envelope = one constitution; positional isomers / tautomers / constitutional
  isomers / regioisomers stay DISTINCT. **Idempotent on parsed molecules** — no existing digest, frozen hash, or
  golden fixture moves. Differential tripwires in `tests/test_resonance_identity.py` (relabel-invariance,
  over-unification guards, fragment/parse unification, idempotence, byte-identity).
- **evil-morty DoS fold (HIGH, verified + closed):** `_ident` is the search hot path and each Kekulé placement is
  a full canonicalization, so a submittable 122-atom oligophenylene ground ~18 s. Two O(1) guards now bound it —
  skip resonance over 64 heavy atoms, cap placements at 128 — falling back to the plain literal identity (no worse
  than pre-fix) above either. The 122-atom attack is now ~3 ms; pinned by a bounded-time regression test.
- **Residual:** a large conjugated fragment over the caps keeps its literal identity (won't unify across Kekulé
  spellings) — a non-issue for the current bounded drug-like targets, documented not hidden. A cheaper
  min-placement selection (avoiding a full canonicalization per placement) would lift the caps; named follow-on.

## 12. ROUND 12 — the four best-next-steps full-blast round (2026-09-05)

Off ROUND 11 (`main` at `7b99873`; the dev branch fast-forwarded onto it, untouched during the build). The four
deliverables are the ROUND-11 report's ranked best-next-steps: (1) cheaper resonance placement, (2) DAG
critical-path admission, (3) more sourced records + an organic-priced commodity, (4) ID-STEREO CONFIGURATION (the
flagship wall). Each: design → 4× Citadel recon → build → REPRODUCE every finding myself → evil-morty red-team →
fold → verify. Final full suite **4116 passed, 14 skipped, 1 xfailed** (dev venv, PySCF present). `result_digest` untouched (no response
schema shape change this round). evil-morty cleared items 2 and 3 with real differential fuzzing and caught a
CRITICAL ring-stereocentre bug in item 4 (fixed + pinned) and an over-reaching claim in item 1's tripwire
(corrected) — both folded below.

### 12.1 item 2 — sound critical-path DAG process gate (Lane C; `54404c0`)

The ROUND-11 `dag_process_fit` serial-summed a convergent DAG's branches (sound but over-conservative on time).
ROUND 12 makes it SOUND on the elapsed axis: **FITS** is certified by the serial-achievable ceiling (unchanged —
always achievable one step at a time), **EXCLUDED** now fires on the critical-path FLOOR (unfittable even with
fully concurrent branches — a strictly tighter, still-sound exclude), and the band between is an honest **UNKNOWN**
(fittable only if branches overlap, which the single-operator bounds cannot confirm). **ACTIVE time stays
serial-summed** — one operator's hands-on time does not shrink when vessels run in parallel, so parallelising it
would be an unsound relaxation (the recon's key correction). The per-step + active logic is extracted into
`_collect_step_checks` so the LINEAR gate is byte-identical (verified: 218 process tests; evil-morty
differential-fuzz **0 divergences**). `_critical_path` is a Kahn longest-path (evil-morty: **0 mismatches** vs
brute force over 3000 random DAGs; cycles raise cleanly). The DAG diagnostic now reports the sound
FITS/EXCLUDED/UNKNOWN tally and names the unmodeled joint-single-operator schedulability boundary.
`process_selection_status` stays UNASSESSED — formal RouteDossier admission is a named next-step (the
`ranked_route_dossiers`/frontier/fit_counts blast radius + the flat-re-derivation coherence fork are deferred
deliberately; the FITS case is fork-safe because a serial-sum FITS re-derives as FITS).

### 12.2 item 3 — aspirin sourced whole-process FITS demo on the flagship (Lane C; `4d52d7b`)

A FOURTH sourced record — **ASPIRIN** (salicylic acid + acetic anhydride → aspirin + acetic acid), LibreTexts
"Experiment 1: Synthesis of Aspirin" (CC BY-NC-SA 4.0, the same family as the paracetamol/isopentyl records).
Every value re-verified by fetching the page and grepping each quote from raw HTML: `min_elapsed_minutes=10.0`
("for at least 10 minutes"), `agitation=MANUAL` ("swirl the flask gently"), equipment nouns each quoted, and
crucially **`workup_included=True`** — the source describes a genuinely PREPARATIVE isolation (Buchner vacuum
filtration → recrystallise → dry → weigh → melting point), so this record produces the **first sourced FITS on the
flagship reaction** (ROUND-11 unblocked aspirin's compilation; this makes it FIT, not just UNKNOWN/EXCLUDE).

**Enabling fix (a ROUND-11 completeness gap):** the record could not attach because `resolve_structure` keyed on
plain `canonical()`, so the ortho-salicylate scission FRAGMENT did not resolve to registered salicylic acid. It now
keys on `resonance_identity` — SOUND because it is idempotent on the (already parse-canonical) registered
structures (**verified 0/41 registered identities move**), so only previously mis-split fragments now resolve;
`structure_identity` stays plain-canonical, unchanged. evil-morty confirmed no over-unification (isomer groups stay
distinct, unregistered isomers → None). Demo verified end to end (`tests/test_process_records.py`): covering bench →
FITS_FOUND; missing equipment / a 350 K ceiling / a 5-min step budget → EXCLUDED; an undeclared check interval →
UNKNOWN.

**Price half deferred, honestly:** salicylic acid $103.73/kg (Lab Alley, re-verified static JSON-LD) is a real,
mass-clean datum, but salicylic acid is NOT a registered `CommodityReagent` (pricing it is a search-behaviour
change with a dubious "commodity" claim), and every registered ORGANIC commodity is a LIQUID (volume-priced, needing
a sourced-density volume→mass layer). Both are self-contained follow-ons; no dead/mislabelled price was wired.

### 12.3 item 1 — resonance-cost investigation refuted the easy win (Lane B; `7e0e487`)

The ask was a cheaper resonance placement to lift the ROUND-11 caps. The investigation **refuted the two obvious
cheap wins** and ships tripwires, not a risky change (`smiles.py` unchanged from HEAD — no regression):

- The "canonicalise the DRAWN Kekulé form" shortcut is UNSOUND (naphthalene's two Kekulé forms are one molecule but
  have distinct plain-canonical digests — enumerate-and-minimise is required). **evil-morty fold:** the tripwire
  originally over-claimed that a constitution-SIGNATURE key is unsound; it is not (that partition unifies the forms
  correctly). The real barrier to a cheap win is that such a key emits different digest VALUES (fixture ripple), and
  reproducing the enumeration's minimum VALUE cheaply still needs the placement search. The claim was narrowed to
  the drawn-form shortcut only.
- No cheap PREDICTIVE cost proxy bounds per-placement `canonical()` cost (measured: a 72-heavy asymmetric phenylene
  grinds despite low symmetry; coronene proxy 72 = 62 ms vs triphenylene proxy 36 = 4 s — a symmetry-only gate both
  misses the former and mis-ranks the latter, and regressed a DoS on measurement). The robust fix is a running
  work-meter inside the canonicaliser, which conflicts with `Molecule.canonical()`'s `lru_cache` — a measured core
  change, named next-step.

Tripwires (`tests/test_resonance_cost.py`): the drawn-form falsification, the fused-aromatic
minimal-representative identity, a fused-aromatic unification regression net, and a `resolve_structure`
resonance-fragment resolution net.

### 12.4 item 4 — ID-STEREO CONFIGURATION: sound chirality-parity perception (Lane B; `825e367`)

The flagship stereo wall, advanced with a sound bounded slice — a canonical chirality-PARITY descriptor that
distinguishes enantiomers, the CONFIGURATION half of stereo perception the isotope work explicitly deferred ("a
canonical CIP parity, which graph canonicalisation cannot supply because chirality is a reflection"). The parser now
captures the tetrahedral SENSE losslessly (`chirality` bool → int: 0 none / 1 `@` / 2 `@@`), closing the recon's
"one-field-behind" hazard. `configuration_key` / `SmilesFeatures.configuration_digest` compute, for each perceivable
ACYCLIC tetrahedral centre with four 1-WL-distinct neighbours, `handedness = perm_parity(neighbours by WL colour)
XOR sense` — spelling-invariant (a neighbour transposition flips the SMILES sense) and opposite for the mirror.

- **Sound + verified:** enantiomers distinct; provably-same spellings agree (swap-flips-sense, re-rooting,
  F-ahead-of-centre, H-position); achiral reduces to constitution (**`Molecule`/`canonical_digest` UNTOUCHED → zero
  fixture ripple**); and — the conclusive subtle case — **meso == its own mirror while (R,R) ≠ (S,S)**. The `chirality`
  bool→int change breaks no consumer (`tetrahedral_stereo` stays a bool).
- **evil-morty CRITICAL fold (verified + fixed):** a ring-OPENING stereocentre slipped the incomplete `incoming>1`
  guard and got a WRONG descriptor — a false split AND a false conflation of ring enantiomers (latent: the key is
  not yet consumed downstream, but it was a landmine for the moment it is). `_on_cycle` now scopes EVERY ring
  stereocentre out to an honest `None` (its written neighbour order depends on the ring-closure digit position the
  bond list does not preserve); a ring SUBSTITUENT on an acyclic centre stays perceivable. Pinned by a ring-→-None
  tripwire (`tests/test_configuration_identity.py`), the coverage hole that let it ship.
- **Deferred, honest, named:** E/Z double-bond config, CIP R/S *naming*, ring stereocentres, and the match-layer
  wiring (`_PERCEIVABLE_LAYERS → CONFIGURATION` — deferred for the isotope layer too, they land together). The
  section-5.3 stereo BLOCKER is unchanged.

## 13. ROUND 13 — the next four best-next-steps full-blast round (2026-09-05)

Off ROUND 12 (`main` at `3251b16`). The four deliverables are the ROUND-12 report's ranked best-next-steps:
(1) formal DAG RouteDossier admission, (2) ID-STEREO match-layer wiring (config + isotope), (3) work-metered
canonicalizer, (4) organic-price wiring + CIP R/S naming. Each: design → 5× Citadel recon → build → REPRODUCE
every finding myself → evil-morty red-team → fold → verify. Two of the four are HONEST outcomes, not builds
(item 3 refuted by measurement; item 4a deferred on sourcing) — the anti-fabrication discipline over shipping a
demo. evil-morty broke TWO of item 1's soundness claims (both folded) and cleared items 2, 3, and 4b. Final full suite **4134 passed, 14 skipped, 1 xfailed** (dev venv, PySCF present; +18 vs the 4116 ROUND-12 base).

### 13.1 item 1 — formal DAG process admission (DAG-ADMIT-01; Lane C; `4e9ce06`)

Convergent-DAG routes were assessed only as a throwaway diagnostic; `process_selection_status` stayed
`UNASSESSED` for a DAG-mode compile. Now a FORMAL, load-re-derived PROCESS admission: a new
`RankedDAGSummary(Digestible)` carries the process axis ONLY (`process_fit_status` = `dag_process_fit`'s
verdict) + per-step `process_requirements` + the DAG `edges`; a new `ranked_dag_dossiers` response field; a
`_check_dag_process_admission_coherence` (the convergent analogue of PROCESS-ADMIT-01) re-derives each DAG's fit
via `evaluate_dag_process_requirements` on load and refuses a `process_fit_status` the evidence cannot support.
`_validate_dag_edges` shape-guards the carried edges (acyclic / single sink / all-reachable), closing the
"relabeled topology" forgery on SHAPE validity; the residual (edges not cryptographically bound to the molecule
graph) is closed by the SAME producer signature as the linear axis. Deliberately NOT a combined bench fit — the
composability/physical bench box for convergent DAGs is a named next-step. `result_digest` folds the DAG dossiers
ONLY when non-empty, so every linear/decompile/DAG-less response stays byte-identical (verified: **zero
result_digest drift** across all CLI-JSON fixtures). Schema: response v1alpha11→v1alpha12, descriptor
v1alpha12→v1alpha13, new `ranked-dag-summary-v1alpha1`.
- **evil-morty fold — Finding 1 (Medium, verified):** `_check_outcome_coherence` fenced `ranked_route_dossiers`
  against an unsearched outcome (ir None) but NOT the new `ranked_dag_dossiers` (the membership check is skipped
  when ir is None), so a REFUSED/INVALID response could smuggle a ghost dossier into `result_digest`. The fence is
  now extended to the DAG field.
- **evil-morty fold — Finding 2 (Medium, verified):** a DAG's process-only `FITS_FOUND` flipped `exit_code` to 0
  (success), where a linear route's success requires the COMBINED bench fit. `exit_code` now gates a
  process-constrained compile's success on `admissible_route_digests` (linear combined-FITS), so a process-FITS
  DAG stays REFUSED with its process admission reported separately — never over-read as a bench pass.
  Behaviour-preserving for linear mode.

### 13.2 item 2 — ID-STEREO match-layer wiring (ID-STEREO-02; Lane B; `b6c261d`)

The "enantiomers get distinct SYSTEM identities" goal in its full form is the §5.3 flagship wall (the search
identity `compilation_ir.ChemicalIdentity` runs on the achiral `Molecule` model). The SOUND, right-sized slice:
wire the ROUND-12 configuration perception (+ a proper isotope⊕chirality combined ISOTOPIC key — the bare
`isotopic_digest` is chirality-blind, so it can't refine CONFIGURATION as-is) into `LayeredIdentity.of_molecule`
via `SmilesFeatures`, so `same_identity_at(a, b, CONFIGURATION/ISOTOPIC)` returns a REAL enantiomer-distinguishing
answer. The subtle soundness win: **fail-closed on completeness**. `configuration_digest` is `None` for BOTH a
truly-achiral molecule AND one with an unperceived (ring / E/Z / degenerate) stereocentre — reducing to
constitution in the latter would FALSELY MERGE two enantiomers. A new `SmilesFeatures.configuration_complete`
(True iff every marked centre yielded a descriptor AND no E/Z) gates it: CONFIGURATION is perceived only when
fully determined, else absent (honest UNKNOWN). The combined ISOTOPIC key folds the isotope digest OVER the
configuration digest, closing the enantiomeric-isotopologue trap. Bare `of_molecule` (no features) is unchanged —
zero ripple. `_check_identity_layer`'s refusal reason is now operation-based and honest (the stale "stereo
perception is unbuilt" line — now false — replaced by "perceivable but not yet wired into the achiral search's
terminal matching, §5.3"); dead `_PERCEIVABLE_LAYERS` removed. Live-search threading stays the named §5.3 wall.

### 13.3 item 3 — work-metered canonicalizer REFUTED by measurement (Lane B; `787876f`)

The recon proposed lifting the resonance DoS caps with a per-placement work budget from `category._canonical_cost`.
**Measurement refutes the design** (harness: `experiments/resonance_cost_proxy_probe.py`): `_canonical_cost` is
the NOMINAL candidate-permutation count, not a runtime, and tracks runtime in NEITHER of `canonical()`'s two
regimes. In the INDIVIDUALISATION branch it OVER-predicts wildly (real coronene C24: `_canonical_cost` ~1.2e23 yet
~4.6 ms/call — a raw budget would bail a FAST molecule); in the PERMUTATION branch it UNDER-predicts (per-candidate
cost scales with molecule SIZE, so a 30-atom placement with count 16384 takes ~300 ms). Worst: the slow regime is
asymmetric permutation-branch PAHs, and LEGIT ones out-cost the crafted grind (triphenylene per-placement cost
32768 ≥ grind 16384), so no `_canonical_cost` cut separates crafted-slow from legit-slow without moving a frozen
resonance-identity fixture. Conclusion (mirrors ROUND-12 item 1): the only sound lift is a TRUE runtime meter
inside `canonical()`, which conflicts with its `lru_cache` (a budget-truncated result cached under `(self,)` alone
would poison every later unrelated caller) — the measured core change, deferred. Caps retained unchanged (zero
regression); `tests/test_resonance_cost.py` gains a structural (non-timing) tripwire pinning the refutation.

### 13.4 item 4b — CIP R/S naming, the distinct-atomic-number slice (ID-STEREO-01; Lane B; `d305421`)

`cip_labels` names a tetrahedral stereocentre's CIP R/S configuration WHEN its four directly-bonded atoms differ
by atomic number alone — there CIP priority is exactly descending atomic number and the recursive
hierarchical-digraph tie-break is categorically irrelevant. Every other centre (two same-element substituents —
the COMMON case: amino acids, sugars, any secondary/tertiary carbon; a ring centre; an E/Z bond) is a NAMED
DEFERRAL and gets NO label, never a guessed/unsound one. The label reuses the ROUND-12 handedness
(`perm_parity XOR sense`) that IDENTITY already uses, swapping the ordering key from 1-WL colour to CIP
atomic-number priority. The parity→R/S SIGN CONVENTION is ANCHORED to a known truth, not memory: L-alanine
(textbook (S)) has ranks [1,4,3,2] with `@@` (sense bit 1), so `perm_parity([1,4,3,2]) ^ 1 == 0` → handedness 0
maps to S; cross-checked, `[C@H](F)(Cl)Br` computes handedness 0 → (S). `tests/test_cip_naming.py` pins this
ABSOLUTE anchor (a globally-flipped convention passes every relational test — the anchor is the only guard). Zero
downstream consumers today (the parity bit already distinguishes enantiomers for identity; R/S is a human name).
The general recursive CIP digraph (for the excluded common centres) and E/Z naming remain the High-complexity wall.
- **evil-morty (clean bill):** built an INDEPENDENT 3D-geometry CIP oracle (never touching the parity code) and ran
  it against `cip_labels` over **96/96 exhaustive** {F,Cl,Br,I} permutations + **4000/4000 random** distinct-Z
  draws — **0 mismatches**. Sign convention derived correct from scratch, distinct-Z slice recursion-free, isotopes
  (same-Z pair) and low-coordinate/ring centres correctly excluded, written-order and multi-centre independence held.
  **Honest boundary:** a COMMON-MODE risk on the OpenSMILES `@` reading (if the oracle and the code share an inverted
  front/behind reading, the fuzz cannot catch it) is closed by the two EXTERNAL anchors (documented L-alanine = (S),
  hand geometry), but NOT machine-confirmed against a third-party parser — RDKit is absent in this environment. The
  L-alanine textbook fact is the load-bearing anchor; a future RDKit `CIPLabeler` cross-check would add the last 1%.

### 13.5 item 4a — organic-price wiring DEFERRED on sourcing (Lane C)

The path is clear (the recon mapped it): salicylic acid is a registered STRUCTURE, needs a `CommodityReagent`
entry + a priced-commodity module mirroring `commodity_pricing.py` + a pinning test; as a SOLID priced $/kg it
needs no density layer. But the price could not be SOURCED in this environment: the ROUND-12 memory's Lab Alley
$103.73/kg figure is committed nowhere and unverifiable via a static fetch (the retail price is behind
client-side JS — no JSON-LD, no meta price, no static dollar string in the page HTML), and USGS (the one committed
price provider) prices no organic acid. Per the anti-fabrication directive that outranks shipping a demo, no dead
or invented price was wired. Named next-step: source a citable static price (a supplier with server-rendered
pricing, or a published reference price) and wire the registration + frozen seed + pinning test.

### 13.6 next-steps (ROUND 13)
- **(a)** organic-price wiring once a citable static price is sourced (item 4a, unblocked by sourcing only).
- **(b)** wire `cip_labels` / `configuration_digest` into a downstream consumer (a human dossier render, or the
  match-layer's live search) — currently perception-only.
- **(c)** the general recursive CIP digraph (names real chirality: amino acids, sugars) + E/Z naming — the
  High-complexity wall item 4b's slice defers.
- **(d)** formal combined bench fit for convergent DAGs (composability/physical box over a DAG), so a DAG's
  `process_selection_status` FITS_FOUND becomes a full bench admission, not the process axis only (item 1 boundary).
- **(e)** the true runtime-metered canonicaliser (lift the resonance caps value-preservingly) — needs resolving
  the `lru_cache` conflict (item 3's deferred measured core change).

## 14. ROUND 14 — the next four best-next-steps full-blast round (2026-09-05)

Off ROUND 13 (`main` at `8006b71`, housekeeping PR #8 on top of ROUND-13's `f29f68c`). The four deliverables are
the ROUND-13 report's ranked best-next-steps: (1) formal combined DAG bench fit, (2) wire config/CIP into a
downstream consumer, (3) the runtime-metered canonicalizer, (4) organic-price + general CIP. Each: design → recon
→ build → REPRODUCE every finding myself → evil-morty red-team → fold → verify. TWO of the five commits are HONEST
outcomes, not builds (item 3 refined-refutation by measurement; item 4b's general CIP refuted by evil-morty and
reverted) — the "a wrong result is worse than none" discipline over shipping an unsound capability. evil-morty
broke a claim on THREE items (item 1's two prose folds, item 2's silent-omission HIGH, item 3's cache-warm
tripwire, item 4b's wrong-label HIGH → revert). Final full suite **4145 passed, 14 skipped, 1 xfailed** (dev venv,
PySCF present; +11 vs the 4134 ROUND-13 base).

### 14.1 item 1 — formal combined DAG bench fit (DAG-BENCH-01; Lane C; `5fc3b2b`)

The ROUND-13 boundary lifted: a convergent DAG was admitted on the PROCESS axis ONLY. Now the full COMBINED
section-11 bench fit, the true analogue of a linear route. New `dag_bench_fit(dag, box)` + `DAGBenchFit`
(`experiment/drafter.py`) folds E1 composability across the edges (`dag_composability`), the per-step physical box
(the identical `_step_box_check` the linear route runs — order-agnostic, transfers to a DAG node verbatim), and the
critical-path process axis (`dag_process_fit`) into one `RouteFitStatus`. `RankedDAGSummary.process_fit_status`
→ `fit_status` (now combined); `of_dag(dag, box)` takes the full `ConstraintBox`; new `admissible_dag_digests`;
`exit_code` flips a complete process-constrained compile to SUCCESS on a combined-FITS DAG — SOUND because
`dag_process_fit`'s FITS is the serial-sum ceiling = serial-achievable by one operator; the dossier build gate
widens from process- to `box.constrains_anything` (physical-only DAG mode admitted too). Schema:
`ranked-dag-summary-v1alpha1→v1alpha2`, descriptor v1alpha13→v1alpha14; response schema HELD at v1alpha12 (zero
linear ripple, verified). **evil-morty:** five soundness pillars all Verified (serial-sum pillar real, exit boolean
airtight across every route/dag combo, zero linear ripple, unsearched-outcome fence intact, no new smuggle path).
TWO honest folds: (a) the serial-hold-stability boundary now documented — a convergent DAG's serial schedule holds
an early branch's intermediate through its siblings and E1 is time-blind, so that hold's stability is UNVERIFIED (a
strengthening a linear FITS does not carry, unmodeled until a max-hold axis); (b) the physical-only note no longer
prints process-axis "serial-achievable" language.

### 14.2 item 2 — CIP/config wired into the human synthesis dossier (STEREO-DOSSIER-01; Lane B; `4b05800`)

`cip_labels`/`configuration_complete` were PERCEPTION-ONLY with ZERO consumers. The human synthesis dossier is now
the first: `SmilesFeatures` gains `cip_labels` + `stereocentres_marked`; `CompiledSynthesis.target_stereo_lines` +
`_target_stereo_lines(features)` build a "TARGET STEREOCHEMISTRY (…PERCEPTION ONLY…)" block; `compile_synthesis`
takes `target_features` (threaded from both CLI human paths, reusing the SAME resolved features the §5.3 losses
already ride); `render()` emits it under the header. Stamped PERCEPTION-ONLY (the search runs on the achiral
constitution — the §5.3 wall). **evil-morty:** four surfaces HELD (perception-only boundary does not leak — neither
new field feeds any identity/digest; parse mutation clean — molecule/configuration_digest byte-identical; no crash
on isotope/zwitterion/ring/E-Z/name inputs; no wrong R/S symbol). One HIGH fold: the deferral disclosure lived in
an `elif` that fired only when NO centre was nameable, so a target with one nameable AND one deferred centre
silently dropped the deferred one (a di-stereocentre read as mono). Fixed: named and deferred disclosed
INDEPENDENTLY against the marked count ("1 of 2 named … 1 of 2 NOT named"), the perception line separated from
naming, with a regression test on the exact multi-centre case.

### 14.3 item 3 — runtime-metered canonicalizer, refined refutation (RESONANCE-WORK-01; Lane B; `ca51570`)

ROUND-13 refuted a NOMINAL `_canonical_cost` proxy for lifting the resonance caps. ROUND-14 measures the ACTUAL
work meter directly (`experiments/resonance_actual_work_probe.py`) and characterizes it: (1) OVER-CHARGE FIXED —
coronene's real per-placement work is ~12 leaves vs its astronomical nominal cost, so actual-work IS a sound TIME
bound; (2) UNDER-SEPARATION PERSISTS — triphenylene (LEGIT) out-costs a crafted grind in actual total work too
(both permutation-branch, actual==nominal), so NO work budget separates legit-from-crafted; the meter is a TIME
bound, not a malice filter. The only sound lift (an additive >64-heavy escape valve) entangles the enumeration with
an uncached work meter (the lru_cache-conflicting core change ROUND-13 deferred) and never fires (repo max 24
heavy). Caps unchanged; `tests/test_resonance_actual_work.py` pins the two facts + a determinism guard. **evil-morty:**
the refutation is CORRECT and was strengthened (12 legit PAHs × 4 budget formulations, every table topped by legit
chemistry; the mirror bit-faithful; >64 valve never fires). One Verified defect FIXED: the harness claimed
"uncached" but `resonance_canonical` is `@lru_cache`'d and `measure()` never cleared it, so a warm cache zeroed the
reading and the tripwire was green only by cold-cache collection order. `measure()` now clears the cache (proven:
warm-then-measure still reports the true value), the tripwire pins that determinism, the mixed-unit / mirror-ceiling
caveats are documented.

### 14.4 item 4a — the first sourced ORGANIC price (ORGANIC-PRICE-01; Lane C; `3919589`)

ROUND-13 deferred the organic cash floor on SOURCING (USGS prices no organic acid; anti-fabrication outranks the
demo). This round a PRIMARY authority was found and verified in-sandbox: the Methanex Methanol Price Sheet (Aug 28,
2026) PDF was FETCHED AND READ DIRECTLY, the North America "Non-Discounted Reference Price" USD 1,414/MT read off
the sheet (cross-checked against the same sheet's USD 4.25/Gal at its own 332.6 Gal/MT). A frozen provenance seed
(`experiments/methanex_methanol_seed.py`, mirroring the USGS seed's validate/content_hash/FROZEN_HASH) + a
byte-for-byte cross-check test. `commodity_pricing.py` prices methanol from that DISTINCT source, structure-matched
to CH4O so a repointed name yields None; every other organic stays UNPRICED (fail-SAFE) until its own primary
source is READ. Verified: methanol's cash floor lights through the stock bridge, and correctly rippled the
methyl-acetate CLI-JSON golden (that route cuts to methanol).

### 14.5 item 4b — general recursive CIP REFUTED by evil-morty; the sound slice stands (ID-STEREO-CIP-WALL; `3485d35`)

Attempted the general recursive CIP (naming the common same-element centres the distinct-Z slice defers). A CIP
Rule-1a hierarchical digraph was built and validated 13/13 against textbook R/S (incl. the L-cysteine=(R)
exception) + spelling-invariance via `configuration_digest` (an independent in-repo oracle). But **evil-morty found
a VERIFIED HIGH wrong-label bug, systematic**: the digraph compared its nested-tuple keys LEXICOGRAPHICally
(DEPTH-first), while true CIP Rule 1a is BREADTH-first (sphere-by-sphere). On `C[C@H](CCC)C(C)C` (n-propyl vs
isopropyl) it emitted (S) when the truth is (R), consistently wrong across the whole branch-vs-chain alkyl motif
(~740 order-flips) — and STEREO-DOSSIER-01 would have surfaced that inverted descriptor to a chemist. A correct
general CIP needs the full breadth-first hierarchical comparison + phantom-0 padding + aromatic/Rule-1b handling: a
large correctness-critical build we cannot exhaustively validate WITHOUT an independent oracle (RDKit is out of the
dependency-light core), and a WRONG R/S is worse than none. REVERTED: the SOUND distinct-atomic-number slice stands
unchanged and DEFERS every branch-vs-chain centre (fail-closed). Pinned by a refutation tripwire so the naive DFS
digraph is never re-shipped.

### 14.6 next-steps (ROUND 14)

> **The live, ground-truthed queue is now pinned in [`ROADMAP.md`](ROADMAP.md) (the canonical source).** The list below
> is the ROUND-14 snapshot; `ROADMAP.md` supersedes it with recon-corrected sizes (items (a),(b),(c) are all **Large**,
> not Medium, once costed honestly), a new item — DAG best-first ranking (`rank_dags`, absent today) — and the
> correction that E/Z belongs under the CIP wall (a), not the time axis (c).

- **(a)** the FULL breadth-first hierarchical CIP (item 4b's wall) — needs an independent validation oracle
  (a from-scratch 3D-geometry chirality oracle, since RDKit is out of scope) to ship a chemist-facing R/S soundly.
- **(b)** the combined DAG PHYSICAL box / composability re-derivation on load (item 1 re-derives only the process
  component; composability/physical ride as free-text, same boundary as the linear axis — closed only by signature).
- **(c)** a time / max-hold stability axis in the stability model (item 1's serial-hold boundary; item 4b's E/Z).
- **(d)** the true runtime-metered canonicaliser as an additive >64-heavy escape valve (item 3's characterized sound
  path) — only worth building when a real >64-heavy target appears (repo max is 24 heavy today).
- **(e)** more sourced organic prices (item 4a lifted methanol only; each needs its own PRIMARY source READ).

## 15. ROUND 15 — DAG best-first ranking + serial-hold disclosure; organic-price DEFER (2026-09-06)

> Governed by [`ROADMAP.md`](ROADMAP.md) (the canonical live queue). 2 builds + 1 honest DEFER; each build
> `design → recon → build → reproduce → evil-morty → fold → verify`, red-teamed by an independent evil-morty; both
> MEDIUM findings folded and pinned by tests. Commit `96730ae`. Suite `4157/14/1` (+12 from the 4145 ROUND-14 base).

### 15.1 item 1 — DAG-HOLD-01, the serial-schedule hold disclosure (Lane C·B; `96730ae`)
A convergent DAG's serial schedule holds an early branch's intermediate through its sibling branches before the join
consumes it; E1 composability is time-blind (adjacent-handoff only), so DAG-BENCH-01 *documented* that hold's
UNVERIFIED stability but never surfaced it. Now `_serial_hold_minutes(dag)` (`dag.py`) computes each edge's hold as the
sum of the intervening steps' known-minimum elapsed (the same `_known_min(min_elapsed, elapsed.lo)` floor the process
gate uses; unknown floors → 0, a sound LOWER bound over the DAG's own `topological_order`); `dag_composability`
attaches it as an **observation-only** `serial-hold-minutes` finding (mirrors `_pressure_note` — it NEVER changes a
transition status or the composability verdict), exposed via `DAGComposability.serial_hold_notes` + `explain()`.
**evil-morty fold 1 (MEDIUM, Verified):** the disclosure reached NO product output path (`explain()` has no product
caller; `RankedDAGSummary` drops composability) — loud in an empty room. Fixed: `_dag_bench_note` (`service.py`, the one
human tally DAG mode emits) now surfaces the CONCRETE hold magnitude, not just the generic boundary sentence; a no-hold
DAG set keeps the byte-identical old sentence (zero ripple — why no golden moved). **evil-morty fold 2 (LOW-MED):**
schedule-relative wording, so a flagged edge never implies its sibling is safe (for independent branches, which one
waits is a topological tiebreak, not chemistry). `tests/test_dag_hold_disclosure.py`.

### 15.2 item 2 — DAG-RANK-01, best-first ranking of convergent DAGs (Lane C; `96730ae`)
DAG-BENCH-01 made a convergent DAG a first-class bench citizen but left the dossiers in raw discovery order
(`service.py` said so: "DAG mode ranks nothing LINEARLY"), so a chemist handed several admissible convergent routes got
no signal on which is best — the paracetamol-litmus asymmetry. `_dag_score`/`rank_dags` (`drafter.py`) are the DAG
analogue of `_route_score`/`rank_routes`: status → composability → gap → exclusion counts, on exactly what the combined
`DAGBenchFit` carries; `service.py` maps `of_dag` over `rank_dags(_dags, _box)`. The per-reaction thermochemical
tiebreakers a linear route gets are a NAMED next-step (a DAG does not aggregate them yet — ROADMAP queue item 1).
**evil-morty fold 1 (MEDIUM, Verified):** the service ranking test was vacuous twice (a singleton paracetamol fixture,
and a constant `fit_status` so the status-only assert never touched the real reorder) → replaced with a real
multi-dossier scenario (ethyl acetate → 5 UNKNOWN dossiers reordered on gap count 2,5,5,7,7). **evil-morty fold 2
(LOW):** removed `rank_dags`'s unused `stability=` param (`of_dag` cannot honor it → a latent divergence trap). Ranking
changes ORDER only, never membership; `result_digest` round-trips (verified). `tests/test_dag_rank.py`.

### 15.3 item 3 — a second sourced ORGANIC price: honest DEFER on sourcing (Lane C)
Attempted at full effort (acetic acid — highest value, ripples the methyl-acetate golden — and ethanol). Wall: organic
producers post price *increases* (Celanese +$50/MT Feb, +$0.10/lb Mar 2026), not absolute reference sheets; absolutes
are aggregator-walled. Ethanol's only primaries are a government *projection* (EIA AEO Table 12) or a foreign regulated
denatured fuel-grade price (IPART NSW, needing FX+density+unit conversions) — neither clears the bar methanol set. Per
§10.4, anti-fabrication OUTRANKS the demo → DEFER, not a fabricated price (the R13 item-4a call). Pivot candidate:
bromine (USGS-priced) via the DOW-bromine litmus.

### 15.4 the DOW bromine litmus (a second north star, folded into ROADMAP.md)
Recorded as a north-star acceptance gate alongside paracetamol: predict Br₂ decomposition/synthesis, enumerate + rank
the synthesis paths QUANTITATIVELY on cost, and reproduce why Dow undercut the German bromine cartel. Forces the whole
stack at once — the redox IR-COMMUTE family (Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻), the electromagnetic scope (electrolytic bromide
oxidation — the one litmus bridging chemistry and the electron layer), thermodynamics/feasibility, and the
cost/affordability buckets down to the poor-man's evidence buckets. Bromine is USGS-priced, so its cost axis is
sourceable (unlike the organic wall). Spawns ROADMAP queue items 2 (bromine synthesis + USGS pricing) and 6 (the
electrochemical/EM bridge).

### 15.5 next-steps (ROUND 15)
See [`ROADMAP.md`](ROADMAP.md) for the ranked live queue. Freshest: (1) a per-node thermochemical roll-up so `rank_dags`
tiebreaks like a linear route; (2) bromine synthesis paths + USGS bromine pricing (DOW litmus phase 1); then the
standing L items (general CIP oracle-first; DAG+linear re-derivation on load; the full duration-aware stability axis;
the electrochemical/EM bridge).

## 16. ROUND 16 — per-node DAG thermochemical roll-up + sourced USGS bromine (DOW phase 1) (2026-09-06)

Two builds, each `design → recon → build → reproduce → evil-morty → fold → verify`. Recon: 2 Citadel Ricks (thermo/DAG
terrain; cost/redox terrain) + the USGS bromine primary READ by hand + the creator-process research branch
`aletheia/creator-process-research-2026-09-06` pulled (its `docs/research/PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md`
brought onto `main`, its stale pre-ROUND-15 reverts left behind). Both items red-teamed by an independent evil-morty
(both sound; each yielded folds, pinned below).

### 16.1 item 1 — DAG-THERMO-01, the per-node thermochemical roll-up (Lane C·B)
`dag_thermo_rollup` (`smartchem/experiment/dag.py`) aggregates the four SOURCED per-reaction verdicts
(selectivity/feasibility/equilibrium/kinetics) worst-node-dominated over a convergent DAG's nodes — the DAG analogue of
the four `verify_*` folds `fit_route` runs, reusing the IDENTICAL per-step providers, default tables, and worst-folds
(the M4 `verify_dag` feas/equi fold was already present since `ec69eae`; this completes it to four axes and wires it into
ranking). `DAGBenchFit` gains the four verdict fields; `_dag_score` (`drafter.py`) now mirrors `_route_score`
tier-for-tier (status → composability → selectivity → feasibility → equilibrium → gaps → exclusions → kinetics-last);
`RankedDAGSummary` bumps to schema `ranked-dag-summary-v1alpha3` (descriptor v1alpha15) to surface all five verdicts,
reaching parity with `RankedRouteSummary`. RANKING-ONLY: the verdicts are computed AFTER status and never enter it (a
FITS stays a FITS). evil-morty folds: **(LOW-A)** the only real-DAG fixture was all-UNKNOWN on selectivity+kinetics, so
their wiring was proven only to "not raise" (the vacuous-green class) → added a non-vacuous test on a real FAVORED DAG +
a kinetics differential; **(LOW-B)** the `rank_dags` table params re-opened the exact ROUND-15 divergence trap (`of_dag`
can't thread them) → reverted `rank_dags` to defaults-only. `tests/test_dag_thermo_rollup.py`.

### 16.2 item 2 — DOW-BROMINE-01, elemental bromine as a first-class SOURCED commodity (Lane B·C; DOW phase 1)
Elemental bromine (Br₂) added to the commodity registry as a new `INDUSTRIAL` availability tier (`data/reagents.py` +
`affordability.py::_ACCESS_ORDINAL`) — honestly NOT a kitchen commodity (the DOW insight: you make bromine from cheap
bromide, you don't buy it). Priced from the USGS MCS 2026 bromine chapter (READ from the primary PDF): "average unit
value of imports (c.i.f.), $2.70/kg bromine content, 2024 final" ($3.00/kg 2025e), stored as $2700/t (×1000, a
definitional unit conversion) in BOTH the frozen provenance seed (`experiments/usgs_commodity_seed.py`, FROZEN_HASH
recomputed) and the live copy (`commodity_pricing.py`), structure-keyed to Br₂ (no isomer can borrow it), costed
end-to-end through `basket_cost_vector`/`cash_floor`. evil-morty (sound, could not break it) fold: the basis now
discloses the USGS figure is a COMPOUND-DOMINATED import blend (~90% bromide compounds) normalized to contained bromine,
not an elemental-Br₂ spot price — a caveat the future DOW synthesis-ranking phase must respect. `tests/test_bromine_pricing.py`.
The recompile golden (`recompile_routes_found.json`) regenerated: bromine legitimately joins the declared commodity
terminal set, shifting that recompile's `terminal_policy_digest` (→ `request_digest`/`result_digest`); digests-only diff.

### 16.3 creator-process research incorporated (the poor-man ethos, made computational)
The pulled contract reframes footage as **scoped operational observations**, never a recipe corpus, and the poor-man
buckets as **whole-path capability bundles** (material / capability / verification / closure / scale). Folded into
ROADMAP governance as the poor-man ethos: the bench is a **kitchen + outdoors** (kitchen = lab; "poor man's fume hood =
outside", a ventilation control but not a hazard clearance). Spawned queue item 1 (`ProcessObservationIR` read-only
evidence-ingress + capability passport). The redox-displacement enumeration gap recon found (no coupled half-reaction
combiner exists; `Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻` is unreachable by `redox_edges` or `capped_scissions`) spawned queue item 2.

### 16.4 next-steps (ROUND 16)
See [`ROADMAP.md`](ROADMAP.md) for the ranked live queue. Freshest: (1) `ProcessObservationIR` read-only evidence-ingress
+ whole-path capability passport (the poor-man ethos made computational); (2) the coupled half-reaction combiner that
makes the Br₂ displacement *enumerable* (DOW phase 2); then general CIP oracle-first, DAG+linear re-derivation, the full
duration-aware stability axis, and the electrochemical/EM bridge. DEFERRED: the DOW brine-vs-mined cost ranking (Cl₂
sourcing wall); a second organic price.

## 17. ROUND 17 — ProcessObservationIR evidence-ingress + the coupled half-reaction combiner (2026-09-06)

Two builds, each `design → recon → build → reproduce → evil-morty → fold → verify`. Recon: 4 Citadel Ricks (IR/dataclass/
digest idioms; the redox mechanism + search seam; capability/affordability/handling; test/schema/golden discipline). Both
items red-teamed by an INDEPENDENT evil-morty; each found REAL, sound weaknesses, all folded and pinned below. Both builds
are **purely additive** — `git diff --stat main` is empty; the six subjects are new files only, so nothing existing moved
and there is no schema/golden blast radius.

### 17.1 item 1 — PROCESS-OBS-01, the read-only ProcessObservationIR evidence-ingress layer (Lane C)
The poor-man ethos made computational (contract P1). A new read-only sibling package `smartchem/observation/` (modelled on
`smartchem/evidence/`: reuses `contracts.Digestible` + `ReactionDirection`, never enters the executor registry, is never
imported back, drags ZERO heavy modules). It carries: an immutable `ProcessObservationIR` (one source-fragment record —
reaction identity + direction + run-context + phase + scoped claims with explicit unknowns); source-fragment validation;
the five whole-path capability bundles (`capability_bundle` → MATERIAL / CAPABILITY / VERIFICATION / CLOSURE / SCALE, each
EVIDENCED / GAP / BLOCKED, mirroring `ProcessFitStatus`' three-way, never a binary); a no-Frankenprocedure `merge_observations`;
and a read-only `projection_gate`. All seven contract invariants are enforced in code — notably `provenance_digest` is a
COMPUTED property (never a stored field, so it cannot fail open), the IR carries NO readiness/safety field (invariant 4:
structurally cannot promote), and identity/direction are load-bearing in the projection gate. NOT wired into the
`CompilationResponse` (a read-only sibling), so no schema bump and no golden regen. evil-morty folds (all sound):
**(CRITICAL)** the capability engine routed through a bare-substring `_match` with no negation awareness, so a claim
HONESTLY NARRATING a missing control ("there was NO containment") was read as evidence FOR it — inverting the CAPABILITY /
CLOSURE / MATERIAL verdicts and erasing the hard-blocker `dominates()` relies on → fixed with `_claim_supports`, which
vetoes a keyword match if a negation/absence cue appears ANYWHERE in the whole support text (subject + what-it-supports),
fail-closed; **(HIGH)** a numeric conclusion with SILENTLY-omitted calibration reached VERIFICATION EVIDENCED (fail-open),
and the test itself had codified the bug (the "calibrated" fixture had no calibration claim) → fixed so a numeric
conclusion is UNVERIFIED/BLOCKED unless calibration/QC is POSITIVELY evidenced, and the test corrected to a real
missing/flagged/positive differential; **(MEDIUM)** `merge_observations` guarded only on a self-declared `run_context_id`,
so two different reactions (or a decomposition + an assembly) could splice under a forged shared label → fixed to also
require reaction-identity and direction agreement across the fragments. `smartchem/observation/`,
`tests/test_process_observation.py` (25 tests, the contract's own acceptance probes + the fold regressions).

### 17.2 item 2 — REDOX-DISPLACE-01, the coupled half-reaction combiner (Lane B; DOW phase 2 mechanism)
The DOW enumeration wall falls. `smartchem/redox_displacement.py` adds a `HalfReactionCouple` (a MOLECULAR redox couple
`oxidized + n e- <-> reduced`, e.g. `Cl2 + 2 e- <-> 2 Cl-` — a level above the single-species `RedoxHalfReaction`, which is
charge-only on identical atoms) and `combine_half_reactions`, which pairs a reduction couple (oxidant) with an oxidation
couple (reductant), BALANCES ELECTRONS by their LCM, and returns a conservation-checked `RedoxDisplacementEdge`. That edge
exposes the uniform transform interface, so it rides the UNCHANGED bounded search through a new `RedoxDisplacementProvider`
registered into a wider algebra — OPT-IN, absent from `DEFAULT_TRANSFORM_REGISTRY` (exactly like the heterolytic and
single-species redox families). It enumerates `Cl2 + 2 Br- -> Br2 + 2 Cl-` — the 1:2 displacement recon PROVED unreachable
by `redox_edges` (single-species, same atoms) or `capped_scissions` (cuts tied 1:1, charged input refused). The "2" is not
a hack: it falls out of electron-count balancing (Cl₂ gains 2 e⁻, each Br⁻ loses 1). Committed demonstration:
`experiments/redox_displacement_probe.py` (the DOW displacement + a non-trivial LCM case `2 Fe3+ + Sn2+ -> 2 Fe2+ + Sn4+`,
FROZEN_HASH-pinned). Lane-B genericity proof: `git diff --stat main` empty — the family was added with ZERO edits to
`search_routes` / `search_dags` / `from_transform` / `DEFAULT_TRANSFORM_REGISTRY` / the category core. evil-morty fold
(sound): the edge's `Reaction` certificate proved mass+charge but NOT redox-ness — a directly-built edge accepted a
fabricated `electrons_transferred` (999), fictitious element labels, or an identity `Na -> Na` as a "displacement", and
`electrons_transferred` rides the digest → fixed with an electron-ledger verification (`_electron_ledger`) that ties
`electrons_transferred` and the two element labels to the reaction's ACTUAL charge redistribution and rejects a no-op.
`tests/test_redox_displacement.py` (15 tests, incl. the wall differential + the electron-verification regression).

### 17.3 Observability Score folded into the roadmap (queue item 7)
Per the operator's steer + a distilled proposal: the poor-man ethos prefers cheap EPISTEMOLOGY, not only cheap reagents —
*can I tell, with low-cost observations, whether the process is behaving correctly?* Added as a ranked queue item (Lane C·B,
L): prefer routes with a multimodal, chemistry-supplied success signature (colour change, precipitate, gas evolution,
pH/temperature excursion) over one that fails silently. Kept honest by the rule a visible checkpoint is NOT chemical proof —
process-indicator / identity / purity stay three separate axes (invariants 5 & 7), never one collapsed score. Builds on this
round's `ProcessObservationIR` VERIFICATION bucket; gated on a SOURCED per-reaction observable-signature table (you cannot
fabricate "turns orange" — §10.4), the same curation wall as `SEED_CONDITIONS`. DOW tie-in: Br₂'s orange/red colour and
phase separation is a natural first observability testbed.

### 17.4 next-steps (ROUND 17)
See [`ROADMAP.md`](ROADMAP.md) for the ranked live queue. Freshest post-ROUND-17: the DOW displacement **cost ranking**
(now that the mechanism exists — still gated on a sourced Cl₂ price + a NaBr commodity); the **Observability Score** (item 7,
extends this round's VERIFICATION bucket); general CIP oracle-first; DAG+linear re-derivation on load; the full
duration-aware stability axis; and the electrochemical/EM bridge (now unblocked by the half-reaction combiner). DEFERRED:
the DOW brine-vs-mined cost ranking (Cl₂ sourcing wall); a second organic price.

## 18. ROUND 18 — the Observability Score + the electrochemical/EM bridge (2026-09-06)

Two builds, each `design → recon → build → reproduce → evil-morty → fold → verify`. Recon: read the exact seams inline
(the `ProcessObservationIR` VERIFICATION bucket, the `CostVector` axes, the `cell.py` electrochemical prior art, the
`redox_displacement` couples). Both items red-teamed by a 6-lens evil-morty workflow (3 attack lenses × 2 modules); it
found **6 real weaknesses**, all folded (4 code folds) or documented (1 boundary + 1 docstring) and pinned below.
**Additive**: 6 new files + 1 package `__init__` re-export (new exports only — no schema, no golden, no compiler-behaviour
change; the `smartchem/observation/` sibling is never imported by the compiler). Suite **4242 / 14 / 1**. Commit `5f83f6a`
on branch `observability-electrochem-2026-09-06`.

### 18.1 item 1 — OBSERVABILITY-01, the three-axis Observability Score (Lane C·B; DOW)
The poor-man ethos made a RANKING objective: affordable chemistry is also cheap EPISTEMOLOGY — prefer routes whose
success/failure is legible from cheap, redundant, chemistry-supplied signals over ones that fail silently.
`smartchem/observation/observability.py` (in the read-only observation sibling) adds a SOURCED `OBSERVABLE_SIGNATURES`
table keyed on **canonical product structure** (Br₂ the DOW flagship — orange-red colour + dense phase separation, the
free sensor Herbert Dow watched; I₂ the contrast, with the cheap starch-iodine identity test), an `ObservableSignature`
(modality × axis × cost, citation REQUIRED — you cannot fabricate "turns orange", §10.4), and an `ObservabilityProfile`
that keeps **three SEPARATE axes** — process-indicator / identity / purity — and NEVER collapses them to one number
(invariants 5 & 7: there is deliberately no `overall_score`). Ranking is Pareto over the three cheap-axis strengths
(`observability_dominates` / `observability_frontier`, the same shape as `affordability.dominates`), so a route strong on
PROCESS but weak on IDENTITY does NOT dominate one weak on PROCESS but strong on IDENTITY — they are incomparable, exactly
as the honesty requires. Non-vacuous: Br₂ = (2,1,0) Pareto-dominates I₂ = (1,1,0). Builds on ROUND-17's VERIFICATION
bucket via a negation-aware `observation_corroborates` bridge (an observation can corroborate that a sourced signal was
SEEN, but never mint a new signature). Does NOT wire into the `CostVector` (that would edit `_AXES` + the frontier-entry
schema + goldens) — a self-contained ranking primitive; the CostVector verification-axis wire-in is an honest deferred
schema bump. `tests/test_observability.py` (19 tests). evil-morty folds F1/F2/F4 (below).

### 18.2 item 2 — ELECTROCHEM-01, the electrochemical/EM bridge (Lane B·EM; DOW)
Dow's process reaches the electron/circuit layer ([electromagnetic scope]). Recon found the prior art:
`smartchem/cell.py` already models an electrochemical `Cell` (electron balancing), Faraday's law
(`theoretical_capacity_coulombs`) and a `VoltageEstimate` — but `Cell.open_circuit_voltage` FAILS CLOSED, documenting the
exact hole: "requires Gibbs free energy under specified thermodynamic/electrochemical conditions". `smartchem/electrochemistry.py`
fills it for the standard-state case: a SOURCED `STANDARD_REDUCTION_POTENTIALS` table (CRC Handbook 97th ed. / Bard &
Faulkner App. C — KNOWN physics, not invented; keyed on the couple's structural digest, fail-closed UNKNOWN elsewhere),
from which `standard_cell_potential` (E°cell = E°cathode − E°anode), `gibbs_free_energy_j_per_mol` (ΔG° = −nFE°),
`spontaneity`, `nernst_potential` (the 59.16 mV/decade slope), and `minimum_electrolysis_voltage` (the reversible drive
for the electrolytic anode leg) follow. **Closes the DOW loop with ROUND-17's REDOX-DISPLACE-01**: the enumerated
`Cl2 + 2 Br- -> Br2 + 2 Cl-` is not only reachable but SPONTANEOUS (E°cell = 1.358 − 1.087 = **+0.271 V**,
ΔG° = **−52.3 kJ/mol**), and the reverse pairing comes back −0.271 V (NON-spontaneous) — reproducing WHY chlorine
displaces bromide but bromine does not displace chloride (the known-answer instrument calibration). W3 unchanged: a
standard potential certifies a thermodynamic tendency, never a rate. Reuses `cell.FARADAY_C_PER_MOL` (pinned equal by
test). `tests/test_electrochemistry.py` (15 tests). evil-morty folds F3/F5/F6 (below).

### 18.3 evil-morty folds (ROUND 18) — 6 real findings, 6 lenses
- **F1 (HIGH, observability)** `observation_corroborates` was negation-blind to MORPHOLOGICAL absence: "the solution
  remained colourless" matched the COLOUR keyword by bare substring ("colour" ⊂ "colourless") with no cue firing, so a
  FAILURE signal was read as positive corroboration — the ROUND-17 fold reincarnated in a phrasing the hand-list missed.
  Fixed with a WORD-BOUNDARY modality match + an extended negation veto (morphological + phrasal), fail-closed.
  [[a-keyword-match-is-negation-blind]]
- **F2 (MEDIUM, observability)** corroboration used only `signature.modality`, never `signature.axis`, so a bare
  process-grade "a colour appeared" corroborated an IDENTITY signature — the process→identity upgrade the module forbids.
  Fixed to be AXIS-AWARE: an identity/purity signature additionally needs axis-appropriate discrimination/purity evidence.
- **F3 (MEDIUM, electrochemistry)** `CellPotential.gibbs_j_per_mol` took `n` as an unvalidated guess, so a caller passing
  one couple's own electron count silently got a ΔG off by an integer factor. Fixed to DERIVE `n = lcm(cathode.electrons,
  anode.electrons)` from the object and refuse a mismatched supplied `n`. [[a-conservation-check-does-not-prove-the-mechanism]]
- **F4 (MEDIUM, observability)** `ObservabilityProfile.sourced` was a stored, forgeable flag — a hand-built profile over
  FABRICATED signatures could claim `sourced=True` and evict the real route from the frontier. Fixed to a COMPUTED
  property checking table provenance (mirroring the sibling's `provenance_digest`-computed discipline), so a forgery is
  never sourced and stays incomparable. [[declarative-auditor-trusts-the-field-it-polices]]
- **F5 (MEDIUM, electrochemistry) — documented, not code-folded.** The Br₂ potential is aqueous-specific (Br₂(l) = +1.066 V),
  but the halogen couple is phaseless. This is already fail-closed for an explicitly-phased couple (returns UNKNOWN, never
  a wrong number), and the aqueous +1.087 V is the CORRECT value for the aqueous DOW displacement, so the module documents
  the aqueous scoping; phase-keyed potentials are YAGNI until a phase-carrying couple API exists (see ROADMAP tracked debt).
- **F6 (LOW, electrochemistry)** the `StandardReductionPotential` docstring overclaimed a citation is "refused at
  construction / must be a real reference" when only non-emptiness is checked. Corrected: the citation is caller-asserted
  provenance (content not machine-verified); `couple_potential`/the curated table is the sourced authority.

### 18.4 next-steps (ROUND 18)
See [`ROADMAP.md`](ROADMAP.md) for the ranked live queue. Post-ROUND-18 the queue is L-heavy: general CIP oracle-first;
DAG+linear composability/physical re-derivation on load; the full duration-aware stability axis; and — now that the
electrochemical primitive exists — the DOW litmus is two-thirds standing (pricing R16 ✓, mechanism R17 ✓, spontaneity +
electrolytic voltage R18 ✓), leaving the brine-vs-mined **cost ranking** gated only on a sourced Cl₂/NaBr price. DEFERRED:
that cost ranking (Cl₂ aggregator wall); a second organic price. TRACKED DEBT: phase-specific electrode potentials (F5);
the CostVector verification-axis wire-in for the Observability Score.

## §19 — ROUND 19 (branch `cip-load-stability-2026-09-06`): CIP oracle, duration-stability primitive, serial_holds, and the on-load re-derivation decision

3 builds + 1 recorded scope decision; **additive** (5 new files + additive edits to `service.py`; no existing behaviour
changed). Went full-blast on queue items 1, 2, 2b, 3 — three shipped, one (item 2) resolved to a build-ready decision
because its true cost (measured against the code) is larger than the other three combined and lives in the module that
gates every compile.

### 19.1 CIP-ORACLE-01 (item 1 — the oracle half) — Lane B
`experiments/cip_geometry_oracle_probe.py` + `tests/test_cip_geometry_oracle.py`. Meets item 1's oracle gate ("the wall
isn't the namer — it's the oracle", built and discarded twice R13/R14). `geometric_handedness(priorities, sense)` builds
synthetic tetrahedron coordinates from the OpenSMILES sense bit and reads R/S off a real signed volume (lowest priority
away, trace 1→2→3), taking priorities as an INPUT so it decouples geometry from priority-ranking. The sign convention is
DERIVED (V>0↔S) and reproduces two independent textbook absolutes ([C@H](F)(Cl)Br = S, L-alanine = S) with one rule.
Green on an exhaustive 48-case {F,Cl,Br,I} battery cross-checked against `cip_labels`. **Recon finding (load-bearing):**
`Molecule` is a pure graph with NO coordinates and the one coordinate system (`geometry.py:seed_coordinates`) is
deliberately stereo-blind — so the oracle is synthetic-coordinate, not `Molecule`-coordinate.

### 19.2 DURATION-STABILITY-01 (item 3 — the primitive half) — Lane B·C
`smartchem/experiment/stability_horizon.py` + harness + `tests/test_stability_horizon.py`. A duration-aware survival
verdict `f = exp(-k t)`, k = A·exp(-Ea/RT) mirroring the L1 rate engine (R pinned equal by test, no drift). Non-vacuous on
the sourced N₂O₅ record (SURVIVES 60 s → MARGINAL 1 h → DEGRADES 6 h at 298 K; faster at 338 K), DERIVED inside the
298-338 K fit window / PREDICTED outside, instrument-calibrated (k(298) reproduces the measured 3.38e-5 to ~5%).
Fail-closed UNKNOWN with no sourced rate; the compound→rate bridge is structure-keyed and direction-specific (the
cyclopropane/propene C₃H₆ collision proves no same-formula isomer or product borrows a rate). Standalone — NOT wired into
core E1 (a stated boundary; needs a route intermediate with sourced kinetics + a unit-lock on `ConditionEnvelope.duration`).
The DOW-Br₂ half stays walled on a missing Br₂ decomposition primary.

### 19.3 DAG-HOLD-MR-01 (item 2b) — Lane C
`serial_holds` on `RankedDAGSummary` — the DAG-HOLD-01 serial-schedule hold made machine-readable as
`(producer, consumer, minutes)` triples (was a human note only). **Digest-EXCLUDED** (`compare=False`): the triples are
fully determined by the digest-bearing `edges` + `process_requirements`, so they add no identity and every existing DAG
digest stays byte-stable (confirmed live). Schema `ranked-dag-summary v1alpha3→v1alpha4`, descriptor `v1alpha15→v1alpha16`;
one golden regenerated (`response_schema.json`), the other four command goldens byte-unchanged (empty DAG dossiers,
`COMPILATION_RESPONSE_SCHEMA` untouched). Non-vacuous: the 40-min DAG carries `(0,2,40.0)`.

### 19.4 ONLOAD-REDERIVE (item 2 — decided, not built) — Lane C
`docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`. Item 2's gate was literally "a scope decision"; resolved it.
**Decision:** carry the thick per-step re-derivation payload (target `Molecule`, reactants, products, reagents, full
`ConditionEnvelope`) **opt-in and digest-EXCLUDED** (`compare=False`, the `provider_snapshots`/`serial_holds` precedent),
and close the free-text trust boundary via a **load-time coherence check** that re-derives composability + physical and
compares to the digest-protected claimed verdicts (mirroring PROCESS-ADMIT-01). Protection-equivalent to folding the
evidence into `result_digest`, without changing every existing route identity. Measured build (why it is its own round):
new Molecule + full ConditionEnvelope serializers + conservation-certified `ExperimentStep`/`Route` reconstruction
(`ExperimentStep.__post_init__` refuses a non-conserving step, so no partial reconstruction) + 4 coherence checks
(composability/physical × linear/DAG) + schema bumps + golden regen — larger than items 1+2b+3 combined.

### 19.5 evil-morty folds (ROUND 19) — 2 passes, both real
- **CIP oracle (MED-HIGH → right-sized + hardened).** The adversary proved the oracle is ALGEBRAICALLY `perm_parity ^
  sense` (a signed volume of permuted vertices is alternating; the base tetrahedron's global sign ε is +, so it reduces
  bit-for-bit), so the 48-case agreement confirms ONE constant, not 48 independent bearings, and it is BLIND to a ranking
  bug on the distinct-Z slice (priorities are copied). Folded: docstrings corrected to the honest scope (it buys one
  independent bit — a global convention-flip guard checked against textbook reality — plus the decoupling instrument);
  `cip_labels` pinned into the frozen hash so a regression in the AUDITED slice reddens it too; a test pinning the
  algebraic identity + an external-absolute full-pipeline check baked in; the unreachable degeneracy-guard overclaim
  fixed. New lesson: [[a-reframed-check-can-be-the-same-quantity]].
- **Duration-stability (core SIGNED; 3 LOW folded + 1 boundary documented).** evil-morty signed the anti-fabrication core
  (no wrong compound borrows a rate, no overflow/NaN/out-of-range reaches a verdict, the spread is genuine, the
  calibration is honest). Folded: `is_sourced` docstring softened (computed-from-a-caller-field, not forge-proof against a
  self-authored lie); an `isfinite` guard added to `surviving_fraction` (fail-closed on a non-finite injected `KineticRef`,
  which the data layer accepts); the "decomposition"→"first-order consumption" naming corrected (a first-order
  isomerization also resolves). Documented (not code-folded): the reactant-coefficient rate-CONVENTION assumption
  (per-species `-d[A]/dt = k[A]`, which both seeds pin) — a latent trap for a future coeff>1 record, undetectable from the
  data, tracked in ROADMAP.

### 19.6 next-steps (ROUND 19)
See [`ROADMAP.md`](ROADMAP.md). The three L items advanced but none fully closed: item 1's NAMER remains (a correct
breadth-first digraph, validated against the now-committed oracle); item 2 is a pure build (decision recorded); item 3
needs the core E1 wire-in (+ the `ConditionEnvelope.duration` unit-lock) and a Br₂ decomposition primary. TRACKED DEBT
gained three (§ROADMAP): the CIP parser-convention seam (no external oracle), the duration-stability coefficient
convention, the unconsumed/unit-unlocked `ConditionEnvelope.duration`.

## §20 — ROUND 20 (branch `cip-load-stability-2026-09-06`): the general CIP breadth-first namer (queue item 1 closes)

1 build (ID-STEREO-CIP-NAMER), full-blast on queue **item 1**. R19 met item 1's *oracle* gate; this builds the *namer* —
the priority-ranking half that killed the R13/R14 attempts. **Additive to the engine** (new `_cip_*` functions in
`smiles.py` + `experiments/cip_namer_probe.py` + `tests/test_cip_namer.py`), plus a **conscious supersession**: the general
namer NAMES the common same-element case the distinct-Z slice deferred, so several ID-STEREO-01 *deferral* tests were
updated to their correct labels (the deferral was "not built yet", now built). Byte-identical on the distinct-Z slice.

### 20.1 the ranker (ID-STEREO-CIP-NAMER) — Lane B
`smartchem/smiles.py`: `_cip_digraph` / `_cip_compare` / `_cip_sorted_children` / `_cip_child_zs` / `_cip_ranks`, wired into
`_cip_labels`. CIP **Rule 1a** priority via a hierarchical digraph, **breadth-first, branch-by-branch with need-to-know
pruning** (Hanson et al., *J. Chem. Inf. Model.* 2018, 58(9), 1755) — the fix for the R13/R14 **depth-first** nested-tuple
key that mislabels branch-vs-chain (`C[C@H](CCC)C(C)C` → DFS says S, truth is **R**). Multiple bonds and ring closures
become duplicate/phantom leaf atoms (real atomic number, phantom-0 children — so a real atom out-ranks a same-Z duplicate
one sphere LATER, NOT the naive shortcut). The namer produces `ranks` (a permutation of {0,1,2,3}) and reuses the SHIPPED
`_perm_parity(ranks) ^ sense` emit line, so it is **byte-identical** to the old `sorted(z, reverse=True)` on the distinct-Z
slice (there the digraph decides at sphere 0) — a strict extension. **Memoised** + budget-bounded (fail-closed DEFER). It is
**SOUND, not complete**: a centre Rule 1a cannot fully order (isotope-only Rule 2, pseudoasymmetric/E-Z Rules 4/5, a true
constitutional duplicate) is a NAMED DEFERRAL — a wrong R/S is worse than none.

### 20.2 recon (4 Citadel-Rick bearings, read-only)
Parser data-structures (raw `bonds` preserve written direction + order, `Bond.order` is the phantom trigger, no phantom
machinery existed); the correct Rule-1a algorithm + a discriminating textbook set (incl. the **L-serine (S) / L-cysteine
(R) flip** — same skeleton and `@@` tag, opposite label because cysteine's real S out-ranks the carboxyl's phantom-O at
sphere 1); the R14 autopsy (the reverted `3485d35` was test-only; the bug was DFS lexicographic; `C[C@H](CCC)C(C)C` is the
exact discriminator); the soundness boundary + the six stereo test files not to regress.

### 20.3 the committed harness — five validation layers
`experiments/cip_namer_probe.py` (FROZEN_HASH): (1) ~18 textbook/PubChem absolutes incl. the serine/cysteine flip; (2)
**oracle cross-check** — every named centre's label == `geometric_handedness(namer's priorities, sense)` (geometry
validated independently of ranking, the exact decoupling R19's oracle was for); (3) the **R14 differential** — an inline
depth-first comparator MISLABELS `C[C@H](CCC)C(C)C` as (S) while the shipped namer names (R); (4) the **branch-paired
proof** — a synthetic divergence pair where a SPHERE-POOLING comparator (a different wrong bug) and the correct
need-to-know branch-paired comparator disagree, and `_cip_compare` takes the branch-paired side; (5) a **840-case
combinatorial alkyl pool** (the class the R14 bug hid in) — every named centre inverts under enantiomer reflection and is
invariant under re-spelling, twin-substituent false centres defer.

### 20.4 the conscious supersession (deferrals → names)
`tests/test_cip_naming.py`: the same-element deferral test and the branch-vs-chain "wall" test flipped from `== ()` to the
correct labels (alanine S, glyceraldehyde R, the R14 trio all R). `tests/test_stereo_dossier.py`: alanine now names;
still-deferred examples swapped to a genuine ring stereocentre. `tests/test_cip_geometry_oracle.py`: the "slice defers a
same-Z centre" test rewritten to "namer and oracle now agree". `smartchem/experiment/compile.py`: the dossier disclosure
text corrected ("by the CIP Rule-1a breadth-first hierarchical digraph"; deferral reason is now ring/isotope/pseudoasymmetric,
not same-element). No golden touched cip_labels or a chiral SMILES → zero golden regen.

### 20.5 the aromatic Kekulé soundness bug (self-caught, before evil-morty) + the lazy fix
Constructing the sharpest probe — a FALSE centre — surfaced a real unsoundness: `O[C@H](c1ccccn1)c1ccccn1` (two IDENTICAL
2-pyridyls) was NAMED `(R)`. Correct Rule 1a on a mancude ring needs Kekulé-invariant atomic-number AVERAGING (Hanson Fig.
3); the parser's one fixed Kekulé made the two identical pyridyls traverse to DIFFERENT digraphs and broke a true tie.
**Fix (lazy aromatic boundary):** an aromatic atom is a boundary node whose atomic number is still usable (so a ranking
decided before the ring still names — no regression on the distinct-Z slice, e.g. `Cl[C@H](F)CCc1ccccc1` = S) but whose
Kekulé-dependent onward connectivity is withheld; a comparison that must descend past it raises `_CipAromatic` → DEFER.
New lesson: [[comparing-fixed-representatives-fabricates-a-distinction]].

### 20.6 evil-morty — "I could not make it lie"
A full adversarial pass found **no wrong R/S**. It verified: all anchors; a **400-molecule parity-correct spelling fuzzer**
(400/400 named, 0 disagreements); the phantom-timing trap (vinyl > isopropyl, ethynyl > vinyl, nitrile triples); every
deferral obligation (isotope, constitutional-duplicate, pseudoasymmetric); and the aromatic hazard "closed and closed
well". Folds: **finding #1 (LOW, over-defer)** — `Cl[C@H](C)C=Cc1ccccc1` (styryl) spuriously deferred where its tBu twin
named, because `_cip_compare` eagerly full-sorted children before the atomic-number sphere check; **fixed** by comparing
the immediate sphere on known atomic numbers first (`_cip_child_zs`) and only ranking children if the sphere ties — which
also makes the code's own docstring true (a ranking decided before the ring now names). **Residual A** (exocyclic multiple
bond into an aromatic atom → Kekulé-dependent phantom count) **discharged** by an explicit `_cip_digraph` guard. **Residual
B** (comparator transitivity as a `cmp_to_key` sort key) **documented** — no counterexample, fuzzer-clean, the
`sorted(ranks)==[0,1,2,3]` guard catches top-level cycles, but no proof in hand.

### 20.7 tracked debt + next steps
NEW tracked debt (§ROADMAP): **aryl/heteroaryl naming needs Kekulé-averaging** (aromatic-reaching ties defer until built —
the clean completeness extension); the **comparator-transitivity residual**. Item 1's ORACLE + NAMER are both shipped;
what remains for full CIP completeness is Rules 1b/2/4/5 + aromatic averaging (all sound-deferred today). Queue now
L-heavy on items 2 (on-load re-derivation, decision recorded, a pure build) and 3 (duration wire-in + Br₂ primary).

## §21 — ROUND 21 (branch `cip-load-stability-2026-09-06`, code `6e14d51`): on-load re-derivation of composability + physical + ranking (queue item 2 closes)

The L round. Closes the free-text trust boundary PROCESS-ADMIT-01 left open: on load only the **process** component of a
route's combined `fit_status` was re-derived; **composability** (E1) and the **physical box** rode as free-text
`exclusions`/`gaps`, and the **ranking** verdicts rode unchecked — so a route non-FITS for one of those (or with fabricated
ranking) could be bare-relabeled to FITS and admitted. Item 2 closes it **structurally, no key**.

### 21.1 the external review, folded against the tree (not on faith)
The item-2 spec was taken to ChatGPT during the R20 compact (`docs/research/ONLOAD_REDERIVATION_CHATGPT_PROMPT_v0.1.md`).
Its response was **verified against the actual dev tree** (5 commits past the `main@8a312a5` it read) by an 8-agent
workflow (`wf_c2a0e0f8-732`: 6 read-only Citadel-Rick recon bearings + 2 evil-morty adversaries). Result:
`docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.2.md` (supersedes v0.1). The recon **confirmed** ChatGPT's central
premise with measured probes — `route_digest` (== `ExperimentRoute.digest`/`SynthesisDAG.digest`) already hashes every
`ExperimentStep` field incl. all 10 envelope fields + the reagent multiset, no collision — so binding to it binds
everything. It also found the fold `F` is a faithful abstraction of the real fitters (`drafter.py:347-356`/`457-465`).

### 21.2 the two holes v0.1 had (found before any code)
- **HOLE 1 — coherence ≠ route binding (ChatGPT).** v0.1's check re-derived from the DECLARED payload and compared to the
  DECLARED verdict; `route_digest` never entered the re-derivation (only a set-membership check, `service.py:1276-1282`).
  A substitution attack lands: another route's genuinely-FITS payload under a bad `route_digest` passes coherence. **Fix:**
  `reconstruct(payload).digest == route_digest`. Cheap (route_digest unchanged).
- **HOLE 2 — the deletion door (adversary, ChatGPT missed).** v0.1's "gated on payload presence (zero overhead)" is
  bypassable: a `compare=False` payload is invisible to `route_digest`, `result_digest`, AND the HMAC; the tree's uniform
  fail-open loader idiom (`.get(default)`) would skip an absent payload. Attack: relabel EXCLUDED→FITS, recompute the free
  public `result_digest`, DELETE the payload. **Fix:** verified admission is a **fail-CLOSED consumer policy** (a FITS route
  with no payload is UNVERIFIED, refused) — which needed **NO schema bump** (route identity byte-stable, no golden churn),
  strictly lower blast than the adversary's own schema-bump proposal.
- **CORRECTION — the HMAC conflation.** v0.1 lines 52-60 said the signature "closes the key-holding-forger residual"; the
  code's own `test_key_holding_forger_residual_is_not_closable_by_a_signature` says it is IRREDUCIBLE (a public digest
  recompute is free; only a keyless out-of-band edit is closed by a signature). Corrected inline + in v0.2 + the new docstrings.

### 21.3 what shipped (all in `smartchem/service.py`, additive; `tests/test_onload_rederivation.py`, 20 tests)
- **Codecs + reconstruction:** `_molecule_to/_from_payload` (mirrors `compilation_ir._graph_payload` — POSITIONAL,
  digest-preserving, no canonical remap; a re-parse-from-SMILES would false-reject an honest route), `_condition_envelope_to/_from_payload`
  (all 10 fields, through the real `__post_init__` — K/atm units, EvidenceStatus cap, provenance/source consistency),
  `_step_to/_from_payload`, `_steps_to_replay_payload`, `_reconstruct_route`/`_reconstruct_dag`. Reconstruction re-runs the
  real `ExperimentStep`/`ExperimentRoute`/`SynthesisDAG` constructors (conservation certificate, linearity, acyclicity), so
  a forged non-conserving step is refused at reconstruction.
- **`replay_payload` field** on `RankedRouteSummary` + `RankedDAGSummary`, `compare=False`/`repr=False` (digest-excluded →
  route identity byte-stable), built by `of_fit`/`of_dag`. **Emission opt-in** (`include_replay=False` default on
  `ranked_summary_to_payload`/`ranked_dag_summary_to_payload`/`response_to_payload`/`serialize_response`) → default wire
  byte-identical to pre-item-2, existing goldens unchanged.
- **`_check_verified_admission`:** for every FITS route/DAG dossier, reconstruct, re-project via the SAME producer path
  (`rank_routes`+`of_fit` / `of_dag`) under the response's pinned eval-context (`box` from `request.constraints`, `losses`
  from the IR, `DEFAULT_STABILITY`), and require `resummary == claimed`. ONE equality subsumes route-binding, the combined
  fold verdict, the composability + 4 ranking verdicts (fork resolved → INCLUDE), and the process/edge projections.
  Fail-CLOSED on a missing payload. Wired via `response_from_payload(require_verified_admission=True)`; off by default.
- **Edges int-coercion trap** (`service.py:2552`) fixed: `_exact_int_pair` validates wire types before coercion (a
  `True`/`1.9`/`"1"` index is refused, not silently truncated).

### 21.4 evil-morty fold (2 findings; everything else held "earned, not gifted")
- **F1 (MEDIUM, VERIFIED) eval-context relaxation.** The re-derivation box is built from the response's OWN request; a
  keyless attacker who relaxes that request (drops a temperature cap) + recomputes `result_digest` makes an out-of-bounds
  route re-derive FITS → admitted. Same *class* as the v1 HMAC conflation: authenticates coherence UNDER the stated
  context, not the context. **Fold:** docstring corrected (residuals are TWO — a key-holding forger AND a keyless request
  relaxer); added `expected_request_digest` to `response_from_payload`/`deserialize_response` (consumer pins its request;
  a `verification_key` closes it cryptographically). Not forced (the process axis trusts the request identically). Both
  directions pinned (`test_request_relaxation_is_admitted_unless_the_request_is_pinned`). NEW lesson
  [[a-keyless-check-trusts-the-context-it-reads]].
- **F2 (LOW) `serial_holds` unauthenticated.** `compare=False` → ignored by `==`; not an admission break (never touches
  `fit_status`) but a disclosure gap. **Fold:** the DAG branch re-derives + checks it (`test_serial_holds_are_re_derived_not_trusted`).
- **Held:** substitution (route-binding), deletion door (fail-closed), physical bare-relabel, codec field-drop (exact
  field-set + real constructors), reconstruction bypass, non-determinism/false-reject, edges coercion.

### 21.5 tracked debt + next steps
NEW tracked debt (§ROADMAP): the **keyless eval-context-relaxation boundary** (F1 — closed by `expected_request_digest` or a
signature; not forced); the **verified-admission compute cost** (the full `rank_routes` fold per FITS dossier on load). The
**load-time free-text trust boundary** debt is now STRUCTURALLY CLOSED for a verified-admission consumer. **Queue: only
item 3 remains** (wire the duration-aware verdict into core E1 + the DOW-Br₂ decomposition primary — an L whose true
rate-limiter is sourcing). Suite `4417 / 14 / 1` (+20 vs R20's 4397). NOT merged — held for the user's push/pr/merge go.


## 22. ROUND 22 — neutral mancude CIP, duration unit admission, and source-access corrections (2026-09-07 UTC)

Base `043a3cd`; isolated branch `codex/mancude-duration-sourcing-2026-09-07`. The original main checkout
was left unchanged because a Claude process remained attached. The implementation commit and aggregate
verification are recorded in `experiments/validation/round22_2026_09_07.json` and the ROADMAP header.

### 22.1 CIP-MANCUDE-01 (Lane B)

`smartchem/smiles.py` now recognizes bounded neutral mancude ring systems by cyclic topology and filled
valence on both aromatic and explicit Kekulé inputs. Multiple-bond duplicates carry exact `Fraction`
atomic numbers averaged over distinct feasible partner positions. Real atoms and ring-closure duplicates
retain integer atomic numbers. Match enumeration discovers partner membership; it does not weight
partners by their frequency across Kekulé drawings. Supported neutral C/N/O/S and fused examples are
pinned against IUPAC fractions and the authors' VS032/033 source anchors.

The external baseline found a real hole in ROUND 20's soundness claim: uppercase Kekulé spellings bypassed
its lowercase aromatic guard. `O[C@H](C1=CC=CC=N1)C1=NC=CN=C1` was named S but the accurate RDKit
reference says R; its mirror was also reversed. Both are now correct on aromatic and explicit inputs.
Identical di-2-pyridyl ligands remain a false centre and receive no label.

The new dependency-free probe covers 12 families and 96 spelling/reflection/tie cases plus the two source
anchors. Tests distinguish owner averages from ring-closure duplicates, exact 13/2 and 19/3 values, ring
bridges, unsupported charged/exocyclic systems, and zero/small exhaustion of each of three caps. Limits
are 30 atoms per ring component, 128 matchings, and 10,000 matching-search visits. No partial average is
admitted. The existing comparator, geometry convention, search core and molecular identity remain intact.

The external implementation panel uses optional RDKit 2026.03.6's accurate `rdCIPLabeler`, not its legacy
labeler. The same 1,224 representation cases change from 354 correct names / 136 true ties / 732 deferred /
2 wrong names to 1,088 correct names / 136 true ties / zero wrong names. A separate review panel of 1,134
fresh cases gives 900 correct names, 80 true ties, 101 deferrals, 53 parser refusals and zero wrong names.
Both external panels share the CIP specification and RDKit implementation family; they are finite
implementation evidence, not independent proof of chemical truth or complete CIP. Their scripts, row
hashes, wheel version and exact baseline counterexamples are retained in `experiments/validation/`.

Remaining: Rules 1b/2/3/4/5 tie resolution, ring stereocentres, general charged resonance, unsupported
ring valences, and the previously recorded comparator-transitivity proof gap. Some unsupported uppercase
inputs now defer; some charged aromatic inputs already fail at the parser and still do. Scope and primary
source pins: `docs/research/CIP_MANCUDE_SCOPE_2026-09-07.md`; external instrument audit:
`docs/research/CIP_EXTERNAL_ORACLE_2026-09-07.md`.

### 22.2 DURATION-UNIT-01 (Lanes B/C)

`ConditionEnvelope.duration` requires exactly `min`, matching all existing declarations. Other units
must be explicitly converted before construction. Replay uses the same constructor and rejects unit
swaps. The 59 new tests cover invalid units/types/bounds, zero and fractional minutes, direct/JSON/route
replay, explicit caller conversion, and exact pre-change envelope/route digests. The admission guard
adds no fields, silently converts nothing and preserves valid minute payloads. Core E1 still has no
duration consumer: choosing intermediate-hold bounds and converting minutes to the primitive's seconds
is a separate semantic implementation, not implied by this validation fix.

### 22.3 DOW-SOURCE-RECON-01 (Lanes B/C)

Both broad primary-access walls were corrected with recovered records, inspected PDF pages, source
hashes and arithmetic in `docs/research/SOURCING_RECON_2026-09-07.md` and
`experiments/sourcing_recon_2026_09_07.json`. No production kinetics or pricing seed was changed.

Warshay's NASA TN D-3502 (1966) reports initial gas-phase Br2 dissociation in Ar/Ne/Kr:
`-d[Br2]/dt = kD [Br2][M]`, with `kD = A sqrt(T) exp(-Ea/RT)` in L mol^-1 s^-1. This is an accessible
primary, but not a constant-A, concentration-free first-order hold law. Collider state, modified Arrhenius
units and reverse/hold scope need modeling. Later primary measurements should also be reviewed before
promoting this historical fit to a recommended modern reference.

Los Fresnos's 2025/2026 procurement record offers chlorine gas at $1.24/lb in a 2,000-lb cylinder
($2,480), plus $50/month cylinder rental. The September 9, 2025 minutes approve the bids by category;
the attached vendor/price agreement has blank signature lines. The evidence is an approved municipal
offer, not an invoice, delivered assay, industrial spot price, generally available current purchase price,
or historical Dow cost. Future price integration must retain its exact procurement basis and exclusions;
NaBr/feedstock coverage and whole-route quantitative cost superiority remain open. The proposed NaBr
proxy derived from the same contained-Br benchmark cannot show an undercut: its price mass fraction and
the stoichiometric feedstock mass cancel to the full benchmark cost before adding positive chlorine cost.
An independent brine/feedstock and extraction-cost basis is required for a cheaper-brine claim.

### 22.4 Verification and continuation

Focused duration/integration checks: 335 passed. Focused CIP checks: 168 passed. External panels:
zero wrong named labels after the patch, with deferrals and parser refusals separately counted.
A real optional PySCF smoke calculation of H at HF/cc-pVDZ returned approximately -13.5861 eV.
Aggregate baseline: **4417 passed, 14 skipped, 1 xfailed in 867.26 s**. Final implementation `07651a0`: **4493 passed, 14 skipped, 1 xfailed in 892.81 s**. Source hashes and exact commands are in the round receipt.
The canonical remaining-work list is ROADMAP.md; no human bench, historical cost-ranking, or universal
CIP claim is promoted by this round.

## 23. ROUND 23 — the duration-survival monoid functor wired into core E1 (2026-09-07 UTC)

Branch `categorical-duration-functor-2026-09-07`, from `main@404e863`, code `8e97664`. The first rung of the
categorical reorientation the user asked for (Move 2: physical quantities as functors, not bolted-on scalars),
and the core-E1 half of queue item 3. `design → recon (2 read-only mappers) → build → reproduce → evil-morty →
fold → verify`. Additive: 3 source files + 1 new test, no schema/golden churn.

### 23.1 DURATION-SURVIVAL-01 (Lanes B/C)

E1's composability verifier was instantaneous (onset-vs-exposure) and time-blind; DAG-HOLD-01 (ROUND 15)
computed the sourced serial-schedule hold but only DISCLOSED it as a note, never a verdict. This consumes it.
`smartchem/experiment/composability.py` gains `_apply_duration_gate`, a post-process on the instantaneous
per-transition verdict: where the intermediate has a SOURCED first-order decomposition rate (the ROUND-19
`stability_horizon` primitive, matched on CANONICAL STRUCTURE, never formula), the surviving fraction over the
hold MOVES the verdict. It only ever tightens — `DEGRADES → DEGENERATE` (even where the onset table was silent,
because a sourced kinetic refutation is stronger than a missing record), `MARGINAL → UNKNOWN`, `SURVIVES`
confirms the instantaneous verdict without upgrading it — and it never touches an already-`DEGENERATE` base.

The survival is a monoid functor `S: Process → ([0,1], ×)`: `Transition.surviving_fraction` (a `compare=False`,
digest-EXCLUDED disclosure, so an unassessed route keeps its exact prior digest) and `route_surviving_fraction`
on `Composability`/`DAGComposability` are the product of the per-transition fractions, and the hold survival
itself is the product over the hold's segments. `survival_verdict` was promoted from a private helper to a
shared public band-policy function so the standalone primitive and the gate cannot drift to different band edges.

`smartchem/experiment/dag.py` gains `_serial_hold_segments` (per edge, the intervening sibling steps'
`(temperature, minutes)`), and `dag_composability` threads an injectable decomposition-kinetics table.

Off by default and byte-stable: the seed kinetics hold only N₂O₅ and cyclopropane, so no existing route routes a
held intermediate with a sourced rate; every prior golden is unchanged (the +17 tests are the only suite delta).

### 23.2 Independent review (evil-morty) and the folds

An adversarial pass attacked seven load-bearing claims; five held clean (byte-stability/digest-exclusion,
only-tightens, structure-keying, the DAG kinetics-alias identity, and the fraction-range/fail-closed guards).
It found one real MEDIUM soundness bug and two minor issues, all folded before commit:

- **MEDIUM (folded):** the first cut applied the endpoint peak temperature (`exposed.hi`, max of producer/
  consumer) across the whole hold. But the intermediate idles during the intervening SIBLING steps, whose
  temperatures were never consulted — so the gate could mint a false `DEGENERATE` (hot producer, cool idle hold)
  and, worse, launder a real degradation into near-survival (cool endpoints, hot sibling). Fixed: survival now
  composes over each intervening step's OWN declared `(temperature, duration)` segment (`_hold_survival`), and
  fails closed (silent) when any hold-segment temperature is undeclared — the gate never renders a verdict on a
  temperature the model does not actually know. Pinned by a two-direction test.
- **LOW (folded):** a non-finite injected `KineticRef` (the data layer has no `isfinite` guard) matched on
  structure and then raised inside the gate, aborting the compile. The gate now checks the matched rate's
  finiteness and stays silent; the primitive's own raise-on-non-finite (`surviving_fraction`) is unchanged.
- **Docstring (folded):** `route_surviving_fraction` is the product over DURATION-ASSESSED handoffs only, not a
  whole-route survival probability (a route can carry a reassuring fraction while its verdict is `DEGENERATE`
  for a non-duration reason) — documented to be read alongside the verdict, never instead of it.

### 23.3 Boundaries carried (TRACKED DEBT in ROADMAP.md)

Only DAG serial holds carry a modeled hold — a linear route's adjacent handoff passes none, so its intermediates
are never duration-assessed. Each intervening segment uses the hi end of its declared temperature range. The R19
reactant-coefficient rate-convention residual still applies. The DOW-Br₂ half of item 3 remains: the recovered
Warshay primary is bimolecular `kD·[Br₂][M]` with a `√T` factor at shock-tube temperatures, not the
concentration-free first-order law the gate consumes (item 3b, a modeling wall, not missing access).

### 23.4 Verification

Full suite **4510 passed, 14 skipped, 1 xfailed** (= the pre-round 4493 plus 17 new tests; the 1 xfail is the
orthogonal interchange-law debt), run in four memory-bounded batches (the box OOM-killed a monolithic run under
memory pressure; the four alphabetical globs union to all 183 test files, confirmed). Ruff clean on all four
changed files. The canonical remaining-work list is ROADMAP.md.

## 24. ROUND 24 — Move-1 keystone Rung B: OpenChemDiagram on a generic open-SMC core (2026-09-07 UTC)

Branch `move1-rung-b-open-chem-diagram-2026-09-07` (docs-fold `de21c06` + code `944ad8c` + ROADMAP `bff0095`), MERGED
via **PR #19 → `main@5f1b3e3`**. The first buildable increment of the open-diagram chemistry-morphism backbone (the
categorical reorientation's Move 1), landing ALONGSIDE `Reaction` — additive, byte-stable, fail-closed. Contract:
`docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md` (v0.2, general monoidal-decoration slot).

`smartchem/open_core.py` is a domain-neutral open-SMC core: multi-terminal `Hyperedge`s, a monoidal `Decoration` slot,
`then`/`tensor`/`identity`/`braid`, and a hyperedge+decoration-aware `canonicalize` (WL refinement + bounded brute force,
`CanonicalizationBudgetExceeded` fail-closed). `smartchem/open_chem_diagram.py` is the chemistry layer: species-typed
ports, reaction hyperedges, three `PortState`s, a `from_reaction` functor, and `close()` to a byte-identical `Reaction`
(P3). `ExperimentStep.open()` is the real non-test consumer. The 3-part gate is GREEN: (1) interchange/braid/hexagon
under the `canonicalize` quotient + fail-closed budget refusal; (2) `.open().close()` reproduces the certificate
byte-for-byte; (3) P4 provenance round-trip + interchange-equivalent assemblies yield equal provenance.

Two apex kinds, of two different kinds: **conservation** is a genuine additive DECORATION (a homomorphic sum over the
generators — the Δ_rG/survival shape); **provenance** is a topology READ (not a decoration). The evil-morty **[HIGH]**
fold: the first cut's `canonicalize`-equality was NOT a congruence — a `compare=False` provenance frontier that
`then_combine` consumed to decide the compared `deps` made `f ≡ f;id` yet diverge under a later `then` (and `(f;id);g`
crashed on `close()`); FIXED by deriving provenance from the composed TOPOLOGY. birdperson SOUND-BUT-HEED. New lesson:
`a-quotient-must-be-a-congruence`. Suite **4536 / 14 / 1** (= 4510 + 26).

## 25. ROUND 25 — Move-1 keystone Rungs C + D and Move-2 M2-FP (2026-09-07 UTC)

Branch `move1-rungs-c-d-m2fp-2026-09-07` from `main@5f1b3e3`: Rung C `3e34265`, M2-FP `a8b61ce`, Rung D `35a5e64`,
review fold `d42d7a2`. Three rungs of the categorical reorientation in one round, each `design → recon → build →
reproduce → evil-morty/birdperson → fold → verify`. Additive/byte-stable/fail-closed. Suite **4579 / 14 / 1** (= 4536 +
43; skip/xfail unchanged ⇒ P2 holds, the legacy interchange xfail preserved).

### 25.1 Rung C — the pipeline speaks open-diagram (Lanes A·B)

`ExperimentRoute.open()` / `SynthesisDAG.open()` project a whole multi-step synthesis onto ONE `OpenChemDiagram`. The
genuine gap they fill: a real route step carries byproducts + fresh reagent leaf inputs, so its codomain never equals the
next step's domain — the whole-vessel `then`/`Reaction.then`/`scheduled_product` cannot chain it. The new primitive
`open_core.OpenDiagram.plug_all(pairs)` is a single PARTIAL PUSHOUT: it glues a chosen subset of output ports to input
ports and keeps the rest on the boundary (`then` is the special case that plugs every port). `_assemble` tensors all step
diagrams then plugs the shared intermediates — matched BY TOKEN (`_first_free`), never by port position. `net_reaction()`
is the conserving overall equation of any saturated diagram (multi-step route or convergent DAG), DISTINCT from `close()`
(which reduces only a whole-vessel linear chain and refuses a parallel history). Gates: saturation + conservation-as-
closure (P1/P3), provenance deps == `dag.edges` (P4), interchange invariance of provenance/net + a boundary-order
tripwire. **Closes 3 Rung-B debts:** (2) token-gluing beats a canonical species re-sort; (3) `_derive_provenance` fails
CLOSED on a structurally-identical-step collision; (5) `edge_incidence` (distinct generators) replaces the raw terminal
count, and `plug_all` refuses a self-plug.

### 25.2 M2-FP — functorial physics (Lanes B·C)

`Δ_rG` (`feasibility.feasibility_of_step().delta_g_kj`) recognized as the additive functor `G: Process → (ℝ,+,≤)` —
Hess's law IS the functoriality, pinned non-vacuously by `net_ΔG(route) == ΔG(single net reaction)` on a sourced
steam-reforming route (`CH₄ + H₂O → CO + 3H₂` then `CO + H₂O → CO₂ + H₂`, the CO intermediate cancelling). Surfaced as
the `RouteFeasibility.net_delta_g_kj` property (moves no digest/golden), DISTINCT from `verdict` (the worst-node sign).
`PhysicsProduct(ΔG, survival)` + `pareto_optimal` are the Pareto product — no scalar collapse ("favorable ≠ fast"), an
unknown axis incomparable (fail-closed). `FreeEnergyDecoration` is a second instance of the `open_core` decoration slot
(law-tested). **Anti-fabrication fix (evil-morty + birdperson converged, HIGH):** `estimate_thermo` treated an EMPTY
Benson-group assignment as a zero-sum, fabricating a `(ΔfH°=0, S°=0) DERIVED` record with a fake provenance for bare
halogens and HBr (the step `C₂H₄ + HBr → C₂H₅Br` returned a fabricated FAVORABLE −134 kJ, `missing=()`). Fixed: empty
groups → None (the loud gap). The DOW-Br₂ dissociation now fail-closes on Br• being GENUINELY unknown, not on Br₂'s
symmetry-number accident. The ranking scorer is UNCHANGED (survival still absent — tracked debt M2b).

### 25.3 Rung D — closing = compiling (Lanes A·B·C)

`compile_open(target, ...)` treats "synthesise this target from stock" as an open spec (the unfilled output), CLOSES it
with the shipped bounded route search, projects each candidate via Rung C, and scores by the M2-FP objective — the
**load-bearing call site** the zero-call-sites discipline demands for Rungs B/C + M2-FP. `MetaCompilation.by_free_energy`
is the LIVE additive-ΔG ranking (genuinely new over `compile_synthesis`, which computes no net ΔG); `frontier` is the
two-axis Pareto, DATA-GATED (survival sourced-kinetics-gated ⇒ usually empty, the honest DOW-Br₂ discipline).
Fail-closed: an uncompilable spec yields no closures; `ClosedCompilation` validates its route.

### 25.4 Reviews and folds

evil-morty (C+M2-FP) and evil-morty (D) plus birdperson (C+M2-FP). What held: the `canonicalize` congruence through
`plug_all`/`tensor` (the Rung-B disease is NOT present — no `compare=False` field consumed by a combine op), net
conservation soundness, `edge_incidence`, `PhysicsProduct.dominates` as a correct strict partial order. Folded (commit
`d42d7a2`): the empty-groups fabrication (25.2); `net_reaction` returning the identity for a cyclic transformation →
gate on hyperedges; the blanket `except ValueError` narrowed to an explicit physical-validity guard (a real band bug now
surfaces); `ClosedCompilation` route=None validation + the Pareto math moved to `pareto_optimal`; the `plug_all` self-plug
orphan guard; and the honest framing of the data-gated two-axis frontier. New lesson:
`an-aggregation-over-empty-support-fabricates`.

### 25.5 Verification

Full suite **4579 passed, 14 skipped, 1 xfailed** (= R24's 4536 plus 43 new C/D/M2-FP tests; skip/xfail unchanged ⇒ P2
byte-stability holds and the legacy interchange xfail is preserved), four memory-bounded batches. Ruff clean on all
changed files. The canonical remaining-work list is ROADMAP.md.
