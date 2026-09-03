# SmartChem generic chemical compiler audit and roadmap reorientation

**Audit date:** 2026-09-03  
**Repository:** `femboy2112/SmartChem`  
**Audited base:** `main` at `4774a26f2d2153bab3a98d0da5013e416b221ad5`  
**Audit branch:** `aletheia/smartchem-genericity-audit-2026-09-03`  
**Primary contract:** `CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md`  
**Implementation ledger:** `UPTAKE_MANIFEST_v0.5.0a1.md`  
**Scope:** the chemical decompiler, synthesis recompiler, shared IR, transform/search architecture, identity, evidence, material flow, and the shortest route from the current alpha to a genuinely extensible chemical compiler.

## 1. Evidence boundary

This is a source-, history-, and architecture-level audit of the repository at the exact base above. It does not claim an independent local execution of the suite. The repository reports a maintained fast-suite result of:

```text
3397 passed, 14 skipped, 2 xfailed
```

Those numbers are **repo-reported verification**, not a test run performed by this audit. Before release or merge decisions, rerun the relevant focused tests, the complete fast suite, lint, and any explicitly gated integrations in a clean environment.

The September 1 audit base was `b5faf7da460377e37f3a6ab70cdcbe542d88b666`. Current `main` is 96 commits ahead of that snapshot. The volume matters less than the semantic shift: several deficiencies identified on September 1 are no longer accurate descriptions of the current architecture.

## 2. Executive verdict

SmartChem has crossed an important boundary.

It is no longer best described as two adjacent chemistry experiments. It now contains the recognizable core of a disciplined compiler:

- one typed request/response service;
- one versioned `ChemicalCompilationIR` vocabulary used by both directions;
- explicit search receipts and bounded-completeness semantics;
- typed identity losses and evidence gates;
- canonical semantic digests separated from provenance/display identity;
- structure-aware route and DAG enumeration;
- exact conserved DAG flow and inverse shopping quantities;
- a real `StockMaterial` model that distinguishes chemical identity from material fitness;
- fail-closed refusal and error classifications.

For the stated `v0.5.0a1` contract, SmartChem is a **late alpha approaching a defensible release boundary**.

For the larger objective—an actually generic chemical decompiler followed by a generic synthesis recompiler—the architecture is becoming strong enough that the remaining obstruction is sharply visible:

> SmartChem is currently a generic bounded chemical-search compiler parameterized by a still-narrow transform algebra.

The search, receipt, IR, DAG, evidence, and material machinery are becoming more generic than the chemistry-generating language they serve. That is a favorable obstruction: the shell is no longer the toy. The next phase should widen the transformation algebra without weakening the truth contract or rewriting the compiler around each new reaction family.

The project must therefore keep three finish lines separate:

1. **Alpha conformance:** a truthful bounded compiler matching `v0.5.0a1`.
2. **Chemical genericity:** an extensible transform-provider algebra plus structure-preserving decompile/recompile semantics.
3. **Bench readiness:** a `ProcedureIR`, material quantities/assays, process-scale hazards, operations, analytical acceptance, waste, and qualified review.

The first is near. The second is the next research-and-engineering frontier. The third remains deliberately outside the current alpha and must not be implied by progress on the first two.

## 3. Claim ledger

### Corroborated within the repository architecture

- Both directions emit a shared `ChemicalCompilationIR` schema.
- The IR carries typed identity-loss records and the content of the unified Section 8.1 search-receipt view, not merely a receipt digest.
- Search partiality is represented rather than silently laundered into completion.
- The CLI/service layer has a typed request and response, explicit defaults, semantic digest discipline, and stable outcome/exit classifications.
- Linear and convergent route search are structurally separated but share receipt semantics.
- DAG fan-out quantity conservation is no longer approximated by the old never-decremented propagation; the reported number is computed by an exact-rational linear program and checked against conservation.
- The inverse DAG shopping calculation includes net consumption and by-product credits and refuses its known coupled underdetermined case.
- Formula, constitutional structure, and stock material are represented as different semantic layers.
- Sourced claims can be downgraded by identity-loss blockers instead of surviving a forgotten identity feature silently.

### Observed from repository records, not independently rerun here

- The current fast-suite count is reported as 3,397 passing tests, 14 skips, and 2 expected failures.
- The current continuation branch and `main` are aligned at the audited head.
- The latest expected failure records fused-aromatic aromatic/Kekulé canonical non-invariance.

### Conjectured with unpaid truth debt

- The current compiler shell can support multiple qualitatively different transform families without a major redesign.
- A typed provider registry can become the dominant chemistry-extension seam while preserving current IR and receipt contracts.
- Structural decompile artifacts can be made directly recompilable by lifting existing `ScissionEdge` witnesses into the shared IR.

These are plausible because the necessary components exist, but they require discriminating implementation probes. They are not established merely because suitable types can be imagined.

### Unverified

- Broad reaction-family coverage on a frozen, family-diverse holdout set.
- Provider locality: adding a transform family without modifying the core route/DAG search engines.
- A true structure-preserving decompile/recompile round trip that does not require a second externally supplied structural hypothesis.
- Sound configuration-level stereochemical identity and the full isotopic lattice slot.
- Bench-procedure completeness or process-scale safety.

## 4. Current capability map

| Layer | Current state | Audit verdict |
|---|---|---|
| Compiler/service architecture | Typed requests/responses, canonical serialization, explicit defaults, stable outcomes | **Strong** |
| Shared chemical IR | Both directions emit it; search receipt and identity losses are transported | **Strong** |
| Formula decompiler | Exact finite AND–OR decomposition under declared inventory and bounds | **Strong within its formal model** |
| Structural decompiler | Bond-graph scission, rooted open valence, rings, valence witnesses, recursive structure descent | **Substantial but not yet the canonical decompile IR** |
| Linear synthesis search | Receipt-bearing reverse capped-scission search | **Strong within its grammar** |
| Convergent synthesis DAGs | Implemented with exact quantity-flow accounting | **Strong infrastructure** |
| Identity/provenance | Formula/constitution separation, typed losses, isotope-refined key, structural evidence keys | **Good; configuration/component coverage remains incomplete** |
| Generic reaction coverage | Dominated by formula decomposition and whole-bond capped-scission families | **Primary blocker** |
| Material-aware recompilation | `StockMaterial` and DAG shopping mathematics exist | **Key pieces built; production integration incomplete** |
| Bench compilation | Route dossiers remain `FORMAL_CANDIDATE`; `ProcedureIR` absent | **Correctly not claimed** |

## 5. What changed since the September 1 audit

The September 1 audit's central criticism was that formula decomposition and structural route generation were only partly connected. That criticism has been substantially answered.

### 5.1 Shared IR became real

`ChemicalCompilationIR` is now a transportable value rather than a display façade. It carries:

- a typed target identity;
- semantic request identity;
- typed identity losses;
- terminal-policy and transform-registry digests;
- native and standard search status;
- a full unified search-receipt view;
- canonical candidate summaries;
- diagnostics;
- canonical serialization with revalidation on read.

The decompile and recompile producers now speak the same artifact vocabulary. This closes the architectural part of the former “two unrelated systems” finding.

### 5.2 The request/service seam became authoritative

The request layer now has a meaningful two-digest law:

- the semantic digest identifies the search meaning;
- the full digest also includes provenance such as explicit/default field origin.

Aliases and equivalent feature-free target spellings are normalized so that equal semantic requests execute the same search. The CLI is increasingly a renderer over this service rather than a second chemical engine.

### 5.3 Search truth is first-class

Formula, linear-route, and convergent-DAG searches expose bounded-completeness receipts. The IR now transports the receipt content. This is a major gain: “no route,” “partial candidate set,” and “complete within a declared grammar” are distinguishable machine states.

### 5.4 Identity and evidence now have teeth

Identity-loss records are not merely annotations. They can block dependent evidence claims. Structural evidence keys include direction and context, and known composition-only evidence borrowing has been closed on live paths. This is the correct compiler principle:

> weakening identity may weaken a claim; it may not silently preserve a stronger claim.

### 5.5 DAG quantities stopped being topology-shaped guesses

The exact LP ceiling and inverse shopping requirement are some of the strongest recent work. The development sequence was healthy:

1. expose the old quantity mint;
2. block it;
3. derive the correct optimization problem;
4. implement exact rational arithmetic;
5. compare independent derivations;
6. red-team by-product reuse and net-consumption cases;
7. fold the defects into permanent tests.

This is not just feature accumulation. It is a calibrated movement from topology to conserved quantitative semantics.

## 6. The principal obstruction: transform-algebra genericity

The public compiler vocabulary currently selects among three effective search grammars:

- formula decomposition;
- capped-scission linear routes;
- capped-scission convergent DAGs.

The route engine is generic over combinations of transforms it receives, but the structural chemistry generator remains concentrated in one broad family:

```text
target structure
  -> cut whole bonds in target and declared reagents
  -> rematch equal-order open valences
  -> derive closed products
  -> read the conserving rewrite backward as an assembly candidate
```

This family has been widened intelligently—multi-cut behavior, rings, multiple reagents, arbitrary whole-bond order, perfect matching, linear and convergent composition—but it is still one reaction algebra.

The current `transform_registry.py` is also an identity registry, not yet a provider architecture. It hashes declared descriptors and depends on an operator manually bumping a version token when the imperative grammar changes. That is useful for current reproducibility, but it is not yet the seam through which independent chemical transform families can register capabilities and candidate generators.

The important correction is therefore:

> Do not confuse a generic search over one rewrite algebra with a generic chemical rewrite algebra.

Increasing depth, cut budget, result limits, or reagent pools can explore more of the present closure. It cannot construct a pathway whose elementary transform family is absent.

This is a **pathway gap**, not principally a search-budget gap.

## 7. The remaining inverse-semantics boundary

`recompile_from_serialized()` now consumes a serialized formula-level decompile artifact. That is genuine progress. However, it also requires a caller-supplied structural hypothesis and checks only that the supplied structure has the same formula as the decompiled target before recompiling that structure.

The present logical shape is:

```text
structure S
  -> forget topology -> formula artifact F

then

formula artifact F + externally supplied structure S'
  -> require formula(S') == F
  -> search synthesis routes for S'
```

This is not yet a structure-preserving inverse:

```text
structure S
  -> structural decompile artifact D(S)
  -> recompile D(S) back toward S
```

The distinction is not cosmetic. Formula equality constrains composition but does not recover constitutional identity. The current bridge proves that a decompile artifact constrains a subsequent structural search. It does not prove that the artifact itself contains the target structure and transform witnesses needed to drive recompilation.

Fortunately, most of the missing mathematical machinery already exists in `structure_descent.py`:

- structural scission edges;
- exact parent/fragment witnesses;
- rooted open-valence identity;
- valence conservation;
- recursive structural descent;
- a forgetful map from `ScissionEdge` to formula-level `DecompositionEdge`.

The next major IR step should lift that machinery into the shared chemical compiler.

## 8. Load-bearing risks discovered at the current head

### 8.1 `CANON-KEKULE-01` is foundational, not cosmetic

The latest red-team found that fused aromatic structures can receive different canonical digests when written in aromatic versus explicit-Kekulé form. This is currently pinned as a strict expected failure.

That defect affects the shared identity quotient used by routes, DAGs, steps, shopping, and stock. A molecule can fail to match itself across two representations SmartChem intends to treat as equivalent. This should be handled as an identity-foundation repair with a dedicated design, differential test matrix, blast-radius audit, and post-fix red-team.

Do not patch one caller. Repair or replace the canonical equivalence relation at its source.

### 8.2 Missing evidence and internal provider faults are currently confusable

`experiment/routes.py::_conditions_for()` catches `Exception` around `assembly_conditions()` and turns every failure into `ConditionEnvelope.unknown()`.

That correctly keeps a missing evidence record from killing formal route generation, but it also risks laundering:

- an assertion failure;
- corrupt provider state;
- an index/key bug;
- a schema defect;
- another unexpected software failure

into the epistemic statement “conditions are unknown.”

A controlled fault-injection test should split these outcomes. Expected lookup absence may yield `UNKNOWN`; unexpected implementation failures should propagate to the existing `ERROR_INTERNAL` boundary.

This is a **probe gap** and a small, high-value housekeeping brick.

### 8.3 The uptake ledger is accumulating stale projections

The manifest is impressively detailed but increasingly append-only. Some earlier “remaining” clauses survive after later records report the corresponding work as landed. For example, one identity-parse row still describes semantic alias collapse as remaining while a later service record says it is implemented.

Historical evidence should be retained, but the current state must have one authoritative projection. Otherwise the ledger becomes a source that itself requires archaeology.

The remedy is not deletion of history. Use a machine-readable requirement ledger or a generated current-state table with append-only uptake records beneath it.

## 9. Required architectural invariants for the next phase

The next phase should be governed by explicit laws rather than feature names.

### G1 — Semantic request law

Equal semantic request digests must execute the same search and use the same transform/evidence/material policies, regardless of CLI alias or presentation spelling.

### G2 — Structural forgetful square

Every structural decompile transform must project to a valid formula-level conserving transform, and the projection must commute with serialization and canonical identity:

```text
structural target --structural decompile--> structural candidate
      |                                      |
      | forget structure                     | forget structure
      v                                      v
formula target    --formula projection----> formula candidate
```

A failed square is a compiler bug or an explicitly refused unsupported case.

### G3 — Provider locality

Adding a new transform family should require:

- a provider implementation;
- provider-specific tests and fixtures;
- registry inclusion;
- optional rendering/schema additions if the provider introduces a genuinely new witness type;

and should not require rewriting the core route or DAG search recursion.

### G4 — Search honesty

Every provider contribution remains inside the existing receipt contract. Provider exhaustion, provider-local budgets, rejections, and unsupported applicability must not disappear inside one aggregate “complete” bit.

### G5 — Identity monotonicity

A claim may use only identity layers perceived and preserved by its path. Forgetting a layer may preserve a weaker claim, lower its tier, or refuse. It may not strengthen or silently retain a layer-dependent claim.

### G6 — Evidence separation

A formal transform witness and a sourced reaction record remain distinct. Algebraic reversibility does not reverse conditions, kinetics, selectivity, mechanism, or literature evidence.

### G7 — Material non-substitutability

A structural identity match is not a stock-material fitness match. Assay, formulation, phase, quantity, age, provenance, and availability remain first-class gates.

### G8 — Failure separation

“Unknown evidence,” “unsupported model,” “incomplete search,” “invalid input,” and “internal software failure” must remain distinct outcomes.

## 10. Roadmap reorientation

The roadmap should be split into three lanes. Do not allow progress in one lane to silently promote another.

### Lane A — Finish the `v0.5.0a1` truth contract

Keep this lane narrow. Close only requirements that block the alpha's public bounded-compiler claims:

- reconcile the authoritative P0 status table;
- unify remaining no-route/candidate wording across human and JSON views;
- finish the material-aware terminal/shopping production wiring promised by existing P0 rows;
- preserve current error and receipt contracts;
- rerun clean verification and freeze a release candidate.

A generic transform-provider architecture is valuable but should not be retroactively declared mandatory for an alpha standard that explicitly disclaims arbitrary reaction discovery.

### Lane B — Build actual chemical genericity

This becomes the main research lane after the alpha truth envelope is stable.

#### `CANON-KEKULE-01` — canonical identity repair

Repair fused-aromatic representation invariance before making canonical structure identity even more load-bearing. Require differential fixtures across aromatic/Kekulé spellings, relabelings, constitutional isomers, isotopologues, and negative controls.

#### `ERR-EVIDENCE-01` — failure/unknown separation

Replace broad exception swallowing in evidence lookup with an expected absence result/exception and a fault-injection test proving internal defects reach `ERROR_INTERNAL`.

#### `IR-STRUCT-01` — structural decompile candidates in `ChemicalCompilationIR`

Add a first-class structural candidate transform carrying:

- parent structure identity;
- cut/formed-bond witness or provider-specific edit witness;
- product structure identities;
- primitive stoichiometry and direction;
- identity layer;
- formal/evidence status;
- exact formula-level projection;
- provider ID/version;
- loss records.

The structural target itself must ride the artifact at the supported identity layer.

#### `IR-FORGET-01` — commuting projection

Implement and test the structural-to-formula projection over serialized IR values. The existing `ScissionEdge.forget()` is the seed, not the entire solution.

#### `TRANSFORM-PROVIDER-01` — real typed provider registry

Replace the current descriptor-only concept with a closed, reviewed provider interface. A provider should declare at least:

```text
TransformProvider
  provider_id
  provider_version
  transform_family
  supported_directions
  required_identity_layer
  preserved_identity_layers
  supported_charge/electron/stereo features
  applicability contract
  candidate generator
  provider-local bounds and counters
  candidate witness schema
  evidence-key requirements
  formal claim boundary
```

The registry receipt must derive from the complete provider manifests and versions. Manual version bumps may remain part of the process, but a provider set or manifest change must automatically alter the registry identity.

#### `HOLDOUT-RXN-01` — frozen family-diverse benchmark

Before adding several providers, freeze a holdout corpus stratified by transformation family and identity demand. The benchmark should classify each target as:

- constructible under the declared provider closure;
- structurally representable but unsupported;
- blocked by identity loss;
- blocked by missing evidence only;
- incomplete under bounds;
- genuinely outside the current transform closure.

Do not use fitted examples as validation. Keep train/dev fixtures separate from the holdout.

#### `CHEM-ALG-01` — first diverse provider set

Demonstrate at least several qualitatively different formal transform families through the same registry and search machinery. Candidate families may include whole-bond substitution/reconnection, partial bond-order edits, ionic/heterolytic transforms, electron-transfer/redox transforms, and ring-forming/opening transforms. The acceptance condition is architectural diversity, not a large example count.

Every provider may remain `FORMAL_CANDIDATE`. Physical applicability and evidence are downstream gates.

#### `TERM-MAT-01` — material-aware terminal unification

Wire `StockMaterial.satisfies()` into terminal and shopping decisions so a structural route requirement is checked against actual material fitness. Preserve unknown assay as unknown; never convert a commodity source lead into a pure-reagent claim.

### Lane C — Bench compilation, later

Do not let this lane block the formal compiler unless a public claim crosses into bench readiness. It includes:

- `ProcedureIR`;
- scale and material quantities;
- addition order/rate, agitation, endpoints, quench, workup, purification;
- analytical acceptance criteria;
- equipment ratings;
- process-scale incompatibility, off-gas, waste, and concentration hazards;
- qualified review and promotion rules.

The current `FORMAL_CANDIDATE` floor is correct and should remain immovable until these obligations exist.

## 11. Verdict-changing probes

| Probe | Pass | Fail | Ambiguous |
|---|---|---|---|
| Fused aromatic equivalence | Aromatic and explicit-Kekulé forms produce one constitutional digest across relabelings | Any equivalent representation splits | Representation equivalence itself is outside the declared model and explicitly refused |
| Evidence fault injection | Expected missing record yields `UNKNOWN`; injected internal defect reaches `ERROR_INTERNAL` | Both collapse to `UNKNOWN` or both abort as internal | Provider cannot be deterministically fault-injected |
| Structural IR round trip | A structural decompile artifact can drive recompilation of its own stored target without a second external structural hypothesis | Recompile still depends on caller-supplied structure not bound by artifact identity | Search finds no route but artifact identity and failure classification remain correct |
| Forgetful square | Every structural candidate projects to the exact expected formula candidate and survives serialization | Projection violates balance, direction, or identity | Provider explicitly declares no formula projection and is refused from this IR lane |
| Provider locality | New transform family is added without editing core route/DAG recursion | Core search must gain provider-specific branches | New witness shape requires only generic schema extension, not search semantics change |
| Holdout family split | Coverage increases on untouched holdout families without regressions or claim promotion | Gains occur only on fitted fixtures or through looser identity/evidence gates | Search becomes incomplete; bounds must be raised before interpreting coverage |
| Material terminal gate | Wrong isomer/insufficient assay/unknown assay cannot satisfy a route requirement | Commodity/name match terminates as sufficient material | Identity matches but assay/fitness is genuinely unknown and remains unresolved |
| Registry identity | Any provider set/version/semantic manifest change changes the registry digest | Provider behavior changes while registry identity remains byte-identical | Pure refactor proven behavior-identical by locked provider tests |

## 12. Housekeeping required before the next large feature arc

1. Add one authoritative “current conformance projection” generated from structured requirement data or maintained as the sole editable status table. Preserve historical uptake records below it.
2. Reconcile stale `REMAINING`, `TODO`, and `IN_PROGRESS` language against current code and tests. A row must not contradict a later uptake record.
3. Separate requirement status from historical commit narrative. One says what is true now; the other says how it became true.
4. Add dependency edges between the three roadmap lanes. Do not allow bench-readiness work to silently become an alpha blocker, or alpha completion to imply genericity.
5. Add the new roadmap IDs from this audit with exact acceptance tests and named dependencies.
6. Record current known xfails as explicit debt with owner, scope, and removal condition.
7. Keep `main` protected by branch work. Do not use this audit branch for unrelated features.
8. Review stale branches and draft PRs separately; do not close or rewrite them merely as incidental cleanup.

## 13. Recommended execution order

The weakest valid sequence is:

1. **Roadmap/ledger reconciliation** — establish one truthful current state.
2. **`ERR-EVIDENCE-01`** — small, decisive separation of unknown evidence from internal failure.
3. **`CANON-KEKULE-01` design and differential tests** — repair the quotient before adding more consumers.
4. **`IR-STRUCT-01` + `IR-FORGET-01`** — make structural decomposition a first-class compiler artifact with a commuting formula projection.
5. **`TRANSFORM-PROVIDER-01`** — introduce the actual extension seam.
6. **Freeze `HOLDOUT-RXN-01`** before provider proliferation.
7. **Implement the first diverse provider set** and test provider locality.
8. **Wire material terminals and shopping into production** using existing `StockMaterial` and DAG quantity machinery.
9. **Cut the alpha release candidate** when its own conformance lane is green; do not wait for arbitrary chemical genericity unless the advertised release claim is broadened.
10. **Begin `ProcedureIR` only under a separate readiness contract.**

## 14. Things to stop doing

- Do not describe a larger search budget as broader chemical semantics.
- Do not call formula-artifact plus externally supplied structure a full structural inverse.
- Do not add more identity consumers while a known canonical equivalence defect remains unplanned.
- Do not catch implementation failures and relabel them as scientific unknowns.
- Do not create provider-shaped types that no live path consumes.
- Do not use same-model red-team agreement as independent verification; retain concrete falsifiers and differential implementations.
- Do not let the detailed uptake history substitute for a single current roadmap state.
- Do not promote `FORMAL_CANDIDATE` because a route looks chemically familiar.

## 15. Dominance assessment

The current framing dominates the September 1 architecture because it explains both the earlier successes and the earlier failures with fewer contradictions:

- formula and structural compilation now share an IR rather than merely sharing prose;
- search incompleteness has a transportable representation;
- identity loss can actually weaken evidence;
- route topology now has conserved quantity semantics;
- commodity identity no longer automatically means suitable material.

The residual failures also become more coherent under the new frame:

- water-from-elements and other missing pathways are primarily absent-transform problems, not evidence that the search machinery is broken;
- formula-level inversion cannot recover topology because topology was intentionally forgotten;
- canonical representation defects compromise all identity-keyed consumers;
- material and procedure truth require layers beyond molecular structure.

Therefore the preferred current frame is:

> SmartChem is a truth-preserving bounded compiler architecture with a strong search/runtime shell, a substantial but specialized chemical rewrite kernel, and an explicit path toward an extensible transform algebra.

This conclusion is **corroborated architecturally**, not a declaration of generic chemical coverage. The next verdict-changing result is not another thousand internal tests over the current grammar. It is a clean demonstration that one new, qualitatively distinct transform family can be added through a typed provider registry, composed by the unchanged core search, transported by the shared IR, projected through the forgetful square, and honestly evaluated by the existing evidence/material layers.
