# SmartChem chemical-compiler reorientation audit

**Audit date:** 2026-09-03  
**Repository:** `femboy2112/SmartChem`  
**Audited ref:** `main` at `4774a26f2d2153bab3a98d0da5013e416b221ad5`  
**Audit branch:** `audit/chemical-compiler-reorientation-2026-09-03`  
**Current declared target:** `0.5.0a1`  
**Companion documents:** [CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md](CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md), [UPTAKE_MANIFEST_v0.5.0a1.md](UPTAKE_MANIFEST_v0.5.0a1.md), [AUDIT_CHEMICAL_COMPILER_2026-09-01.md](AUDIT_CHEMICAL_COMPILER_2026-09-01.md)

## 1. Audit method and verification boundary

This audit reviewed the current repository, recent commit history, the chemical-compiler standard and uptake ledger, and the principal implementation seams in:

- `smartchem/compilation_ir.py`;
- `smartchem/service.py`;
- `smartchem/decompiler.py`;
- `smartchem/structure_descent.py`;
- `smartchem/experiment/routes.py`;
- `smartchem/experiment/dag.py`;
- `smartchem/experiment/stock.py`;
- `smartchem/transform_registry.py`;
- the corresponding adversarial tests and recent red-team records.

The repository reports a maintained fast-suite result of:

```text
3397 passed, 14 skipped, 2 xfailed
```

This audit did **not** execute that suite in a fresh local checkout. The count is therefore a repository-reported observation tied to the audited commit, not an independently reproduced run. The two expected failures include a newly pinned fused-aromatic canonicalization defect discussed below.

The audit distinguishes two acceptance objects that must not be collapsed:

1. **The `0.5.0a1` truth-contract milestone:** a bounded, explicit, reproducible chemical compiler that reports its identity model, transform grammar, search closure, evidence status, material assumptions, and refusals honestly.
2. **The broader generic chemical decompiler -> synthesis recompiler:** a compiler whose transformation algebra is expressive and extensible enough to represent materially different classes of chemical transformation without redesigning the compiler shell.

SmartChem is much closer to the first target than the second.

---

## 2. Executive verdict

SmartChem has crossed an important architectural threshold:

> **The compiler shell is no longer the weak link. The dominant obstruction is now the chemical transformation algebra supplied to that shell.**

For `0.5.0a1`, the project is best described as a **late alpha approaching a defensible contract boundary**. The repository now has a real typed request/service layer, a shared transportable chemical IR, full search-receipt content, explicit loss records, stable outcome classification, adversarially tested identity/evidence gates, exact DAG material accounting, and a first-class stock-material model.

For the larger genericity claim, the accurate description is:

```text
SmartChem is a generic bounded chemical-search compiler
parameterized by a still-narrow transform algebra.
```

The current search machinery is generic over combinations of the transforms it knows. It is not yet generic over a sufficiently expressive family of chemical transformations.

### 2.1 Current-state matrix

| Layer | Current state | Audit verdict |
|---|---|---|
| Typed compiler service | Canonical request/response values, explicit defaults, semantic/full digests, stable outcomes and exits | Strong |
| Shared chemical IR | Both directions emit `ChemicalCompilationIR`; full search receipt and typed identity losses are transported | Strong |
| Formula decompiler | Exact finite AND-OR decomposition over declared inventory and bounds | Strong within the formal formula model |
| Structure descent | Real bond-graph scission, rooted open-valence identity, ring-aware enumeration, valence witnesses | Substantial, but not yet the canonical decompile artifact |
| Linear route search | Receipt-bearing reverse capped-scission search | Strong within the current grammar |
| Convergent DAG search | Implemented with explicit completeness and exact quantitative flow | Strong infrastructure |
| Identity/evidence | Formula/constitution separation, typed losses, structure-specific evidence keys, phase context | Good; configuration/component identity remains incomplete |
| Material accounting | `StockMaterial`, exact DAG ceilings, inverse shopping requirements | Strong pieces; production integration incomplete |
| Transform coverage | Primarily whole-bond valence-preserving capped scissions plus formula decomposition | Dominant genericity blocker |
| Bench procedure lane | `FORMAL_CANDIDATE` boundary is enforced; `ProcedureIR` and process-scale safety remain absent | Correctly not bench-ready |

---

## 3. Progress since the 2026-09-01 audit

The September 1 audit found two only partly connected systems: a formula-level decomposition graph and a structure-level capped-scission route enumerator. That criticism is now materially outdated.

### 3.1 The shared IR is real

`smartchem/compilation_ir.py` now provides a versioned `ChemicalCompilationIR` used by both directions. The IR carries:

- the strongest represented target identity;
- first-class typed `IdentityLoss` records;
- a request digest sensitive to semantic bounds and registry identity;
- terminal-policy and transform-registry digests;
- the full canonical Section 8.1 search-receipt view, not merely a receipt hash;
- digest-identified formula, route, or DAG candidate summaries;
- standard and engine-native completion statuses;
- canonical serialization with tamper checks on read.

This is no longer a display struct. It is an actual transport boundary with meaningful identity laws.

### 3.2 Search truth is substantially hardened

Formula, route, and DAG searches now expose receipt-bearing APIs. Recent work repaired several important defects:

- depth truncation can no longer masquerade as complete search;
- result-cap saturation is visible;
- formula and structural searches name the target, terminal policy, and transform grammar they searched;
- the IR carries receipt content and checks cross-layer coherence;
- complete-empty and incomplete-empty results are distinguishable;
- tampered receipt fields fail closed rather than being trusted.

The project has moved from "a tuple of candidates" toward a proper compiler result: candidates plus a certificate of what search was actually performed.

### 3.3 The service and CLI now share one authority

`smartchem/service.py` establishes a useful law:

```text
equal semantic_digest => the same search
```

Defaults are explicit values with provenance rather than invisible CLI branches. `compile`, `recompile`, and `synthesize` have been progressively collapsed onto the shared request/service and shared rendering engine. Identity parsing is centralized, machine and human views are cross-checked, and internal errors have a dedicated top-level outcome rather than being silently classified as ordinary no-route results.

This is exactly the kind of seam a serious compiler needs.

### 3.4 Identity and evidence are no longer formula-string decorations

The project now distinguishes formula and constitution-level identities, records losses when a representation contains unsupported stereo/isotope/local-charge information, and uses those losses to block dependent sourced claims. The `ReactionEvidenceKey` introduces structural sides, primitive stoichiometry, direction, and context. Recent work also closed composition-only isomer borrowing in a live selectivity path and made phase context active in rate lookups.

The remaining identity gaps are real but named: sound configuration identity, the full isotopic lattice above configuration, disconnected components/formula units, mixtures, and material-state matching.

### 3.5 DAG flow and shopping arithmetic are genuine advances

The most impressive recent progression is the quantitative DAG work:

1. a naive propagation minted shared intermediates;
2. the first honest response was to refuse fan-out;
3. the deeper observation was that a 100%-efficiency ceiling is an optimization over all conserved allocations;
4. an exact rational LP was introduced;
5. a reused-byproduct counterexample exposed a bad routing predicate;
6. the LP became the authoritative number and a second derivation became the per-call differential oracle;
7. the inverse shopping calculation was added and then strengthened with both sufficiency and tightness checks.

This is not documentation theater. It is meaningful quantitative compiler machinery.

### 3.6 `StockMaterial` is now a real value

`StockMaterial` separates chemical identity from assay, phase, quantity, source, cost, age/storage, availability, formulation, and impurities. Commodity entries become source leads with unknown assay rather than silently becoming pure reagents. Structure-keyed component matching now prevents constitutional isomers from borrowing one another's assay.

The payoff is not yet fully wired into route/shopping selection, but the underlying value and fitness gate are credible.

---

## 4. Dominant obstruction classification

The main obstruction is a **pathway gap**, not a missing compiler shell.

### 4.1 Pathway gap: the transformation algebra is too narrow

The active request grammar currently distinguishes only:

- formula decomposition;
- linear capped-scission assembly;
- convergent capped-scission assembly.

The structural route generator is powerful within the capped-scission family: it can cut multiple whole bonds, consume declared reagent molecules, rematch open valences, open rings, and compose results into linear or convergent searches. Nevertheless, its fundamental move remains a whole-bond, valence-preserving graph rewrite generated from bond cuts and capping matchings.

That does not yet provide a generic chemical transformation language. Important abstract classes remain outside or beside the main grammar, including:

- partial bond-order changes;
- charge-localizing ionic or heterolytic transforms;
- redox/electron bookkeeping integrated into route search;
- transformations whose graph edit is not naturally represented as capped cleavage;
- provider-defined reaction families with their own applicability and evidence domains.

The search engine can explore a large closure of a small algebra. Increasing search depth or cut budgets does not dissolve this wall.

### 4.2 Probe gap: no frozen transform-class holdout

The project has many excellent local falsifiers but lacks one frozen, transformation-diverse benchmark that answers:

> Which qualitatively different transformation classes are constructible under the current provider closure, and which fail because of identity, grammar, evidence, or terminal boundaries?

Without such a holdout, implementation can repeatedly fit the currently failing examples while genericity remains unmeasured.

### 4.3 Demonstrated information boundary: formula loss is not invertible

A formula-level artifact cannot uniquely reconstruct a structure. This is not a software defect; it is an information-theoretic boundary.

The current `recompile_from_serialized()` correctly requires both:

- a serialized formula-decompile artifact; and
- a caller-supplied structural hypothesis whose formula matches that artifact.

The artifact constrains the recompile, but it does not contain the structural target being regenerated. Thus the current loop is approximately:

```text
structure S -> forget topology -> formula artifact F
(F, supplied structure S') -> verify formula(S') == F -> search routes for S'
```

It is not yet a self-contained structural round trip:

```text
structure S -> structural decompile artifact D(S) -> recompile D(S) toward S
```

The current implementation is honest about this boundary. The roadmap should now make the stronger structural artifact the target rather than stretching the word "inverse."

### 4.4 Foundational defect: canonical identity is fractured for fused aromatics

The latest red-team found that equivalent aromatic and explicit-Kekule spellings of some fused aromatic systems can produce different canonical digests. This affects the shared `_ident` layer used by routes, DAGs, steps, shopping, and stock. The consequence is severe even though it fails closed: one species can fail to match itself under another equivalent representation.

The defect is correctly pinned as `CANON-KEKULE-01` with a strict expected failure rather than patched locally in `StockMaterial`.

A compiler whose quotient relation is wrong cannot make reliable cache, deduplication, terminal, evidence, or material decisions. This should be treated as a foundational identity repair, not cosmetic cleanup.

### 4.5 Integration gap: material truth is not yet the terminal/search truth

The route engine can compute external molecular requirements. `StockMaterial` can decide whether an actual material satisfies a structural identity/assay requirement. These two capabilities are still adjacent rather than one production path.

The remaining seam includes:

- converting DAG shopping requirements into typed material requirements;
- checking those requirements against the active material inventory;
- preserving `UNKNOWN_ASSAY` and insufficiency rather than treating identity as fitness;
- representing purchased supplements explicitly;
- integrating quantity, assay, units, jurisdiction, and sourced cost into the ranking frontier;
- replacing parallel commodity/on-hand shortcuts with one material-aware terminal policy.

### 4.6 Documentation/ledger gap: historical truth has accumulated sediment

The uptake manifest is valuable, but it now contains historical records whose "remaining" text is superseded by later work. For example, some earlier rows still describe alias collapse or receipt content as open after later records say they landed.

The problem is not merely prose polish. A roadmap/claim ledger that cannot be queried for its current effective state becomes a second source of ambiguity.

The long-term correction is a small machine-readable requirement ledger from which the current status table is generated, while retaining historical uptake records as an append-only audit trail.

### 4.7 Boundary, not blocker: a formal compiler is not a bench-procedure generator

`PROC-IR-01`, process-scale hazard evaluation, broad hazard/stability coverage, and qualified operational review remain open. Therefore SmartChem is not close to emitting procedures for unaided execution.

That is not a blocker for the bounded formal compiler milestone if the output remains `FORMAL_CANDIDATE` and missing operations remain visible. It is a separate readiness lane and should not be allowed to consume the transform-algebra roadmap prematurely.

---

## 5. Load-bearing findings and required actions

### F1 — Generic search, specialized algebra

**Finding:** The route/DAG machinery is generic over a specialized capped-scission algebra. Calling the whole system a generic chemical recompiler without this qualifier overstates the current closure.

**Impact:** More search depth can produce more candidates without covering qualitatively different chemistry.

**Required action:** Introduce an executable typed `TransformProvider` interface and migrate the current formula/capped-scission grammars behind it. Search should depend on provider contracts, not hard-coded grammar branches.

**Acceptance:** At least two materially different transform families can participate in one search without changing the IR, receipt, terminal, route/DAG, evidence, or service architecture.

**Claim status:** **Observed** for the narrow current closure; generic chemical coverage remains **UNVERIFIED**.

### F2 — The transform registry is an identity registry, not yet a provider registry

**Finding:** `smartchem/transform_registry.py` currently hashes declared descriptors and manual version tokens. It does not enumerate executable providers or derive identity from a typed provider manifest.

**Impact:** The compiler can name a grammar but cannot yet inspect, compose, enable/disable, or audit a general set of transform generators through one authority. A rule-set change with no schema-shape change depends on a human remembering to bump a token.

**Required action:** Define a manifest-backed registry whose digest covers the canonical set of enabled provider manifests. Each provider should state at least:

```text
provider_id
provider_version
supported operation/direction
required and produced identity layers
charge/stereo/isotope/component capabilities
transform family and formal claim scope
bounds schema
applicability/refusal contract
evidence-key requirements
implementation/version fingerprint policy
```

A provider invocation should return candidates plus provider-local telemetry/refusals that fold into the global `SearchReceipt`.

**Acceptance:** Adding, removing, reordering, or version-changing an enabled provider changes the registry/request digest exactly when semantic search closure changes; presentation order does not.

### F3 — Structural decompile must become a first-class IR producer

**Finding:** The repository already has substantial structure-descent machinery, including exact graph surgery, rooted open-valence identities, and a forgetful projection to formula edges. It remains adjacent to the canonical formula decompile path rather than represented as a first-class `ChemicalCompilationIR` grammar/candidate.

**Impact:** The serialized decompile/recompile bridge requires the caller to re-supply a structure, so it is constrained recompilation rather than a self-contained structural inverse artifact.

**Required action:** Add a structural-decompile operation/grammar that emits candidate transforms containing:

- structural reactant/product identities;
- the exact graph-edit witness;
- primitive stoichiometry;
- the formula-conservation projection/witness;
- open-valence or charge bookkeeping appropriate to the provider;
- provider identity/version;
- identity losses and claim scope;
- search receipt and terminal policy.

The existing formula decompiler should remain a deliberate lower-resolution projection, not be deleted.

**Acceptance:** A commuting-square test verifies that forgetting every structural candidate produces a valid formula candidate with the same conserved composition, while constitutionally distinct targets remain distinct in the structural IR.

### F4 — Fused-aromatic canonicalization must be repaired at the root

**Finding:** Equivalent fused-aromatic representations can receive different canonical digests.

**Impact:** Identity-based matching, deduplication, caching, evidence lookup, terminal decisions, shopping, and stock fitness inherit the fracture.

**Required action:** Design and test one aromaticity/Kekule normalization policy at the shared canonicalizer boundary. Do not add caller-specific equivalence exceptions.

**Required controls:**

- positive controls: equivalent aromatic/Kekule spellings collapse;
- negative controls: constitutional isomers remain distinct;
- relabeling controls: atom-index permutations collapse;
- idempotence: canonicalizing an already canonical value is stable;
- corpus controls: fused benzenoids and heteroaromatics, not benzene alone;
- mutation controls: deliberately damaged aromatic/bond assignments do not collapse merely because formulas agree.

**Acceptance:** The strict xfail turns green and the same invariant holds across a broader differential corpus. Every `_ident` consumer observes the same corrected quotient.

### F5 — Missing evidence and internal failure are currently too easy to conflate

**Finding:** `smartchem.experiment.routes._conditions_for()` catches `Exception` and returns `ConditionEnvelope.unknown()`.

**Impact:** A legitimate evidence miss and an internal provider defect can produce the same scientific statement: `UNKNOWN`. This launders some software failures into epistemic absence.

**Required action:** Introduce an explicit no-record/unavailable result or narrow expected exception. Only that state may become `ConditionEnvelope.unknown()`. Unexpected exceptions must reach the guarded `ERROR_INTERNAL` boundary with provenance.

**Acceptance:**

- no matching condition record -> route survives with conditions `UNKNOWN`;
- deliberate provider bug/schema exception -> `ERROR_INTERNAL`, not `UNKNOWN`;
- malformed external record -> typed provider refusal/conflict, according to policy;
- ordinary candidate generation remains independent of mere evidence absence.

### F6 — Wire material fitness into route termination and shopping

**Finding:** Exact external requirements and real stock fitness exist, but the production path still terminates and shops primarily by molecular identity/commodity collections.

**Required action:** Introduce one material-aware inventory/terminal evaluation path. A molecular requirement should be transformed into a typed material requirement with identity layer, minimum assay, amount/unit, and contextual constraints. The active inventory should answer `SATISFIES`, `INSUFFICIENT`, or `UNKNOWN`, and the unresolved remainder should become an explicit purchase/supplement requirement.

**Acceptance:**

- vinegar cannot satisfy a pure acetic-acid requirement;
- an unknown-assay commodity cannot silently terminate a pure route;
- a constitutional isomer cannot satisfy the requirement;
- internal intermediates are not purchased;
- byproduct credits and net consumption remain correct;
- supplement purchase changes the material/cost frontier but not the underlying formal route identity.

### F7 — Reconcile the current ledger before adding more historical prose

**Finding:** The append-only uptake narrative and current status table are beginning to disagree.

**Required action:**

1. Re-read every current P0/P1 row against the live code and tests.
2. Update stale "remaining" clauses without deleting historical records.
3. Add explicit `superseded_by` or `closed_by` links from historical records.
4. Introduce a compact machine-readable current ledger, for example:

```text
requirement_id
priority
current_status
implementation_commits[]
acceptance_tests[]
open_dependencies[]
supersedes[]
last_verified_commit
```

5. Generate or validate the human current-state table from this source.

**Acceptance:** No requirement has two conflicting current statuses; every `IMPLEMENTED_AND_VERIFIED` row names a live test and commit; historical prose is clearly historical.

---

## 6. Recommended target architecture

The next architecture should preserve the successful shell and replace hard-coded chemistry growth with provider growth.

```text
user identity/material input
    -> one normalization service + ParseReceipt
    -> strongest supported typed identity
    -> structural decompile/search over enabled TransformProviders
    -> CandidateTransform hypergraph + full SearchReceipt
         |-> exact forgetful projection to formula/conservation view
         |-> route/DAG composition in assembly direction
    -> evidence providers keyed by structure + primitive stoichiometry + direction + context
    -> material/terminal fitness and exact quantity accounting
    -> constraint/ranking frontier
    -> FORMAL_CANDIDATE dossier
    -> future ProcedureIR lane only after operational completeness gates
```

### 6.1 Candidate transform, not reaction string

The shared unit should be a typed candidate transform, not merely a displayed equation:

```text
CandidateTransform
  provider_id/version
  direction
  reactant identities + roles
  product identities + roles
  primitive signed stoichiometry
  structural edit/witness, when represented
  conservation witness
  charge/electron/open-valence witness, when represented
  identity losses
  applicability/refusal scope
  formal evidence tier
  source/evidence references, if any
  digest
```

The route and DAG layers should compose these values. Rendering an equation is a view, never the identity.

### 6.2 One provider protocol, heterogeneous internals

Providers do not need one chemical theory internally. They need one compiler contract externally. A formula partitioner, graph rewrite generator, redox balancer, or curated reaction-template source can have different algorithms while agreeing on:

- typed inputs and required identity layers;
- bounded enumeration;
- deterministic/canonical candidate identity;
- explicit refusal and loss behavior;
- telemetry;
- conservation and witness obligations;
- evidence non-promotion.

This is how SmartChem becomes extensible without turning every new chemistry family into a service/IR rewrite.

### 6.3 Preserve the forgetful hierarchy

The formula engine remains valuable. It should become a certified projection of stronger candidates where possible:

```text
configuration/isotopic/material identity
    -> constitution/structure identity
    -> formula identity
    -> element accounting
```

Every downward move should either preserve the needed claim or emit a typed loss that blocks it. Formula conservation can then certify a lower-resolution invariant without pretending it identifies a reaction mechanism or product structure.

---

## 7. Reoriented roadmap

### Phase 0 — Stabilize the identity and truth substrate

**Goal:** do not build a broader provider system atop a fractured identity quotient or ambiguous error channel.

1. Reconcile the uptake ledger and current README claims.
2. Preserve a fresh baseline test receipt for the exact branch commit.
3. Repair `CANON-KEKULE-01` through a differential corpus and root canonicalizer change.
4. Split ordinary evidence absence from internal provider failure.
5. Re-run all alias, identity, route, DAG, stock, serialization, and golden-response tests.

**Exit criterion:** equivalent representations have stable identity across every consumer; internal faults cannot become scientific `UNKNOWN`; the current ledger has one effective truth.

### Phase 1 — Promote structural descent into the chemical IR

**Goal:** make decompilation preserve structure when structure is available.

1. Define the structural candidate-transform schema.
2. Add structural decompile as a grammar/operation in the request and IR.
3. Carry graph-edit/open-valence witnesses.
4. Implement the exact forgetful projection to formula candidates.
5. Add structural serialized round-trip and formula-commutation tests.

**Exit criterion:** the decompile artifact itself contains the structural target/candidates needed for structural recompilation; callers do not need to re-invent the lost target except when they deliberately chose formula-only decompilation.

### Phase 2 — Make the transform registry executable

**Goal:** convert the current declared digest table into one typed provider authority.

1. Define `TransformProviderManifest` and provider invocation/result contracts.
2. Derive the enabled-registry digest from canonical provider manifests.
3. Migrate formula decomposition and capped-scission grammars behind the interface without changing outputs.
4. Make request selection, receipts, IR, and CLI report the actual enabled provider set.
5. Add provider conflict and failure semantics.

**Exit criterion:** the current behavior is byte/semantically stable under the new abstraction, and a test-only second provider can be enabled without changing compiler architecture.

### Phase 3 — Pay the genericity debt with distinct transform families

**Goal:** demonstrate architecture dominance, not merely abstraction elegance.

Add a small number of sharply different formal provider families, each with explicit boundaries. Candidate families include:

- partial bond-order-change transforms;
- ionic/heterolytic charge-localizing transforms;
- redox/electron-transfer bookkeeping;
- another graph-edit family not reducible to capped cleavage.

Do not begin by chasing broad literature coverage. First prove that heterogeneous providers compose through the same IR/search/evidence/material machinery.

**Exit criterion:** a frozen mixed-class benchmark contains cases solved by different providers, cases requiring provider composition, and cases correctly refused by every provider.

### Phase 4 — Unite terminal policy, material inventory, and shopping

**Goal:** make "on hand" mean a material that is actually fit for the route requirement.

1. Convert external DAG requirements into typed material requirements.
2. Evaluate the active `StockMaterial` inventory.
3. Represent unresolved purchase supplements.
4. Populate the affordability frontier with sourced dated costs or `UNKNOWN`.
5. Keep theoretical 100%-efficiency requirements distinct from practical yield assumptions.

**Exit criterion:** route termination, shopping, stock fitness, quantity, and cost read one material policy rather than parallel identity lists.

### Phase 5 — Establish a frozen transform-coverage holdout

**Goal:** measure genericity without fitting the validation set.

The benchmark should stratify failures by:

- identity unsupported;
- transform provider absent;
- search bound hit;
- terminal/material unavailable;
- evidence absent/conflicted;
- formal route found but not bench-ready.

It should include positive, negative, null, mutation, representation-invariance, and provider-ablation controls. Provider leave-one-out runs should demonstrate which provider actually supplies each capability.

**Exit criterion:** SmartChem can state the exact provider closure and holdout coverage it has earned, without saying "all chemistry."

### Phase 6 — ProcedureIR remains a later readiness lane

Only after the transform/material core is stable should the project promote any output above `FORMAL_CANDIDATE`. `ProcedureIR` must require scale, material specs, operations, addition order/rate, control/endpoint, quench, workup, purification, analysis, waste, equipment ratings, process hazards, and qualified review. Missing any required field lowers the tier or refuses construction.

---

## 8. Verdict-changing probe suite

| Probe ID | Question | Pass | Fail | Ambiguous |
|---|---|---|---|---|
| `REOR-CANON-01` | Is the identity quotient representation-invariant for fused aromatics? | Aromatic/Kekule/relabelings collapse; isomers remain distinct | Equivalent species split or distinct species merge | Parser refuses a representation outside declared support |
| `REOR-ERR-01` | Can an internal evidence-provider bug become `UNKNOWN`? | No-record -> `UNKNOWN`; injected bug -> `ERROR_INTERNAL` | Injected bug silently becomes `UNKNOWN` | Provider returns a typed malformed/conflict state needing policy |
| `REOR-STRUCT-IR-01` | Does decompile preserve structure when requested? | Serialized IR contains structural target and candidate witnesses | Recompile still requires an unrelated re-supplied target | User deliberately requested formula-only mode |
| `REOR-COMMUTE-01` | Does structural decompile project consistently to formula conservation? | Every structural candidate forgets to a valid formula candidate | Any candidate loses atoms/charge or projects inconsistently | A provider explicitly has no structural witness and is formula-only |
| `REOR-REG-01` | Is registry identity tied to executable provider closure? | Provider add/remove/version changes digest; order does not | Semantic closure changes without digest change | Implementation changes with contract-identical behavior under an explicitly declared policy |
| `REOR-MIXED-01` | Can heterogeneous providers compose through one search? | One route/DAG uses candidates from distinct provider families | New family requires special-case IR/service/search plumbing | No mixed route exists in the selected fixture |
| `REOR-MAT-01` | Does real material fitness govern terminal/shopping decisions? | Assay/isomer/quantity gates affect supplements and frontier | Identity-only match terminates an unfit material | Required assay/context was not declared and remains `UNKNOWN` |
| `REOR-HOLDOUT-01` | Does claimed genericity survive a fresh transform-class holdout? | Predeclared success/refusal classes match outcomes | Fitted examples pass but fresh classes collapse unexpectedly | Bound-limited outcomes require larger declared resources |
| `REOR-LEDGER-01` | Is there one effective current roadmap truth? | Every row has one status, live tests, commits, dependencies | Current table contradicts later records or code | A deliberate `DECISION` row remains unresolved |

---

## 9. Claim ledger

### Disclosed

- Exact conservation and descent properties enforced by the current formula/structure value constructors, within their stated models.
- Exact rational DAG ceiling/shopping arithmetic for the accepted graph classes and constraints encoded by the current implementation.
- Search-receipt and IR coherence properties enforced by the current types and adversarial tests, within the serialized schemas.

### Corroborated

- The compiler/service/IR shell has become substantially stronger than the September 1 audited base.
- The project consistently favors explicit refusal/unknown/incomplete states over plausible fabrication.
- The DAG flow progression survived multiple independently motivated counterexamples and improved through differential checks.

### Observed

- The repository reports `3397 passed, 14 skipped, 2 xfailed` at the audited head.
- Formula, linear-route, and convergent-DAG search are the enabled high-level grammar modes.
- Stock fitness and DAG shopping exist but are not yet one production terminal/material path.

### Conjectured

- A typed provider registry can broaden chemical coverage without redesigning the successful compiler shell.
- Structural descent can become the stronger decompile IR while preserving the formula engine as a forgetful projection.

These conjectures carry truth debt until migrated implementations and fresh mixed-provider holdouts pass.

### UNVERIFIED

- Broad or generic chemical transformation coverage.
- Stable behavior across a representative external reaction corpus.
- Correct stereo/configuration identity.
- Material-aware end-to-end route ranking and affordability.
- Any output tier above `FORMAL_CANDIDATE`.

### Refuted

- The claim that the current formula decompile artifact alone is a self-contained structural inverse input. It requires a supplied structure and can only verify formula agreement.
- The unqualified claim that current structure digests are fully "isomer-proof" or representation-invariant. They are constitution-level, stereo-blind, isotope-blind in some consumers, and currently fractured for some fused-aromatic spellings.

### Dark

- The size and shape of the useful chemical space reachable after adding several heterogeneous providers.

**Lamp:** a frozen transform-class holdout with provider ablations, representation controls, and explicit failure taxonomy.

---

## 10. Immediate recommendation

The next work should not be another long sequence of narrowly local capped-scission hardening unless a new falsifier exposes a soundness defect. The highest-leverage order is:

1. **housekeeping and truth repair:** reconcile the ledger, freeze the exact baseline, and split evidence absence from internal failure;
2. **identity root repair:** solve `CANON-KEKULE-01` with a differential corpus and cross-consumer regressions;
3. **structural IR promotion:** make structure descent a first-class decompile artifact with an exact formula projection;
4. **provider architecture:** migrate the existing grammars behind one executable typed registry;
5. **genericity proof by difference:** add distinct transform families and a frozen holdout;
6. **material integration:** make stock fitness and exact shopping drive the production terminal/ranking path;
7. **procedure readiness later:** preserve the `FORMAL_CANDIDATE` boundary until `ProcedureIR` and process-safety obligations genuinely exist.

The project should continue to advertise the `0.5.0a1` object precisely:

> SmartChem compiles bounded, explicitly identified chemical search spaces into conservation-valid candidate artifacts, receipts, and evidence/material diagnostics. It does not enumerate all chemistry, validate that a formal transform occurs, or emit an unaided bench procedure.

The deeper moonshot remains credible, but the next proof obligation is no longer "can we build a compiler?" It is:

> **Can the same compiler architecture absorb a heterogeneous chemical transformation algebra without weakening identity, conservation, search truth, provenance, materials, or refusal semantics?**

That is the decisive next checkpoint.