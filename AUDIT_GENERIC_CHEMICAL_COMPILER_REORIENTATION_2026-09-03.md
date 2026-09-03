# SmartChem generic chemical compiler reorientation audit

**Audit date:** 2026-09-03  
**Repository:** `femboy2112/SmartChem`  
**Audited base:** `main` at `4774a26f2d2153bab3a98d0da5013e416b221ad5`  
**Audit branch:** `audit/compiler-reorientation-2026-09-03`  
**Current package target:** `0.5.0a1`  
**Primary object:** generic chemical decompiler -> synthesis recompiler  
**Governing existing documents:** `CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md`, `UPTAKE_MANIFEST_v0.5.0a1.md`, `AUDIT_CHEMICAL_COMPILER_2026-09-01.md`

---

## 0. Evidence boundary and claim ledger

This audit inspected the current repository state, recent commit history, the compiler standard and uptake ledger, and the load-bearing implementation surfaces around:

- formula and structure descent;
- route and DAG search;
- `ChemicalCompilationIR`;
- the typed request/response service;
- transform-registry identity;
- identity parsing and loss tracking;
- evidence keys and route ranking;
- stock-material and quantitative DAG accounting;
- current tests and documented red-team folds.

The audit did **not** independently clone the repository or execute the test suite. The current README and latest commits report:

```text
3397 passed, 14 skipped, 2 xfailed
```

That result is therefore **repo-reported and commit-attested**, not independently reproduced by this audit. No current GitHub combined status checks were exposed for the audited head. The two expected failures are not treated as passes.

Claim vocabulary used here:

| Label | Meaning in this audit |
|---|---|
| **DISCLOSED** | Directly established by source structure or a narrow mathematical invariant within the stated boundary. |
| **CORROBORATED** | Supported by mutually constraining code, tests, receipts, commit history, and red-team records, without pretending those share no provenance. |
| **OBSERVED** | Present at the audited commit or reported by a named finite run. |
| **CONJECTURED** | Architecturally plausible, but still owing a discriminating implementation or holdout probe. |
| **UNVERIFIED** | A suitable independent run or probe was not performed in this audit. |
| **REFUTED** | A concrete counterexample or code path defeats the broader claim. |

Conclusions inherit the weakest load-bearing premise. In particular, a large green suite does not establish chemical coverage that the suite does not ask about.

---

## 1. Executive verdict

SmartChem has crossed an important threshold.

At the September 1 audit base, the chemical feature was accurately described as two partly connected systems:

1. a formula-level elemental decomposition hypergraph; and
2. a structure-level capped-scission route generator and evidence dossier stack.

At the current audited head, that description is no longer sufficient. The project now has:

- one typed `CompilationRequest` / `CompilationResponse` service;
- one serialized `ChemicalCompilationIR` vocabulary used by both directions;
- explicit search receipts with bounded-completeness semantics;
- typed identity losses and evidence-consumer gates;
- canonical request/result identity discipline;
- receipt-bearing formula, linear-route, and convergent-DAG searches;
- exact conserved fan-out accounting through a rational linear program;
- an inverse DAG shopping calculation with by-product credit;
- a real `StockMaterial` representation rather than a pure-molecule commodity fiction;
- a CLI surface whose aliases increasingly share one semantic execution path.

Those are not decorative schemas around a toy. They are credible compiler machinery.

The central verdict is now:

> **SmartChem is becoming a generic bounded chemical-search compiler parameterized by a still-narrow transform algebra.**

Equivalently:

```text
SmartChem today
  = generic request / IR / search / receipt / ranking / accounting machinery
    over
    a specialized set of chemical rewrite generators.
```

This creates two distinct finish lines.

### 1.1 Finish line A — `v0.5.0a1`

For the intentionally narrow `0.5.0a1` contract, SmartChem is a **late alpha approaching a defensible release boundary**. The standard explicitly does not require arbitrary mechanism discovery, arbitrary reaction-template coverage, complete stereochemical perception, or unaided bench procedures. It requires a truthful bounded compiler that can state what it searched, what it forgot, what it found, and what it refuses.

The project is materially close to that finish line, subject to the remaining P0 integration rows and the canonical-identity fracture discussed below.

### 1.2 Finish line B — generic chemical decompiler -> synthesis recompiler

For the larger research goal, SmartChem is **not yet generic in chemical transformation coverage**. Its compiler substrate is becoming generic faster than its chemistry algebra.

The principal obstruction is no longer “we lack a coherent compiler.” It is:

> **The current transform closure is too narrow, and the transform registry is an identity table rather than an extensible typed provider system.**

That is a major improvement in problem shape. The architecture has localized the next difficulty.

### 1.3 Architecture-win criterion

The architecture has genuinely won when a qualitatively new reaction-transform family can be added by registering a provider and its tests, without rewriting:

- the service;
- the shared IR envelope;
- search-receipt semantics;
- route/DAG composition;
- terminal-policy logic;
- evidence-loss propagation;
- material accounting;
- CLI result classification.

The current system is close enough to test this criterion. It has not yet passed it.

---

## 2. Recovered object, constraints, and acceptance criteria

### 2.1 Object

The target object is not merely a retrosynthesis script. It is a bidirectional compiler whose two directions operate over one typed chemical program representation:

```text
chemical/material target
  -> identity resolution and loss accounting
  -> bounded decomposition/search artifact
  -> candidate transforms/routes/DAGs
  -> evidence-, material-, cost-, equipment-, and safety-aware recompilation
  -> explicit readiness and unresolved obligations
```

### 2.2 Required constraints

The existing constitutional rules remain correct and should not be weakened:

1. A formal balance or graph rewrite is not evidence that chemistry occurs.
2. Search completeness is relative to a serialized transform closure and finite bounds.
3. Formula equality is not structure equality.
4. Structural identity is not material fitness.
5. Reversing a conserving equation does not reverse evidence, conditions, kinetics, or selectivity.
6. Unknown data remain unknown; assumptions do not promote evidence grade.
7. No result may become a bench procedure without a complete typed operation layer and process-scale review.
8. A canonical identity must be invariant under every representation equivalence SmartChem claims to quotient by, while remaining distinct across every feature SmartChem claims to preserve.

### 2.3 Acceptance criteria for genericity

A future generic-compiler claim should require all of the following:

- **One structure-preserving IR path.** Structural decompilation emits an artifact that retains the structural target and structural edit witnesses, rather than reducing the target to formula as the sole shared artifact.
- **A typed provider registry.** The live transform set is a concrete registry of providers with versioned capabilities and application boundaries, not only three manually versioned grammar descriptors.
- **Qualitatively diverse transform closure.** At least several independent rewrite families compose in the same route/DAG search.
- **Provider-relative completeness.** Receipts identify the exact provider closure, bounds, exclusions, and candidate counts.
- **Holdout coverage.** New transform families are evaluated against frozen positive, negative, null, and mutation controls that were not used to design them.
- **Identity soundness.** Equivalent representations collapse; non-equivalent configurations/materials do not borrow identity or evidence.
- **Material closure.** Required external species from a route/DAG are resolved against typed stock materials and assays, not a parallel name catalogue.
- **No readiness laundering.** Generic candidate generation does not imply physical validation or a bench draft.

---

## 3. Current architecture map

| Layer | Current implementation | Audit verdict |
|---|---|---|
| Identity parsing | Name, SMILES, InChI/formula sublayers, target files, parse receipts, typed losses | **Substantial; configuration/component perception remains incomplete** |
| Formula decompiler | Exact primitive atom-conserving AND-OR descent over declared inventory and bounds | **Strong within formula semantics** |
| Structure decompiler | Bond-graph scissions, rooted open valences, ring-aware cuts, forgetful projection | **Strong machinery, but not the canonical shared decompile IR path** |
| Structural transform generator | Capped scissions with whole-bond cuts/caps and valence-preserving perfect matchings | **Powerful but specialized** |
| Linear route search | Receipt-bearing bounded reverse search | **Strong within the active grammar** |
| Convergent DAG search | Receipt-bearing synthesis DAG enumeration | **Strong within the active grammar** |
| Shared IR | Versioned, serialized, digestible, both directions emit it, full receipt content included | **Strong compiler substrate** |
| Service | Typed requests/responses, explicit defaults, semantic/full digests, total outcome map | **Strong compiler substrate** |
| Evidence | Directional structure keys, typed source grades, identity-loss gates, phase-context work | **Good; provider conflict/source uniformity incomplete** |
| Quantitative DAG flow | Exact rational max-yield LP with conservation checks | **Strong mathematical core** |
| DAG shopping inverse | Exact external lower-bound requirements with by-product credit and refusal on coupled ambiguity | **Strong but not yet a production-integrated material path** |
| Stock material | Assay intervals, quantity, sourced/date-bound cost, phase/provenance, fitness verdicts | **Real material model; integration incomplete** |
| Bench procedure | Formal-candidate dossiers and missing-operation checklist | **Correctly not a bench compiler yet** |
| Safety | Some hazard/equipment constraints and fail-closed labels | **Useful architecture; insufficient for process authorization** |
| Transform registry | Three manually versioned grammar descriptors and digest function | **Identity mechanism, not yet a provider architecture** |

---

## 4. Progress since the September 1 audit

GitHub comparison places current `main` 96 commits ahead of the September 1 audit base `b5faf7d`. Commit count is not quality, but the semantic changes are material.

### 4.1 The shared artifact is now real

`ChemicalCompilationIR` is no longer a planned envelope. It now carries:

- operation and tool version;
- typed target identity;
- request identity;
- first-class `IdentityLoss` values;
- terminal-policy identity;
- transform-registry identity;
- native and standard search status;
- the full normalized Section 8.1 receipt view;
- canonical candidate summaries;
- diagnostics;
- canonical serialization with read-time invariant checks.

Both `decompile_to_ir` and `recompile_to_ir` produce this value. Tamper resistance has been strengthened beyond hash comparison: nested receipt fields and cross-layer target/terminal/registry coherence are rechecked during deserialization.

**Verdict:** `IR-CHEM-01` has moved from a conceptual bridge to a credible compiler IR envelope.

### 4.2 The request/service seam is now real

The typed service has established an important law:

```text
equal semantic_digest => same search
```

The full digest retains provenance, while the semantic digest excludes display and default-origin differences that do not alter execution. CLI aliases increasingly build one request and consume one service result rather than carrying parallel hidden defaults.

This is a compiler-grade reproducibility invariant.

### 4.3 Search truth has improved sharply

Formula, route, and DAG searches now expose receipt-bearing paths. The system distinguishes:

- complete candidate set within the declared closure;
- partial candidate set;
- complete no-route within the declared closure;
- incomplete no-route observation;
- model or identity refusal;
- internal error at the guarded boundary.

Depth, cut, result-limit, and search-budget effects are no longer silently conflated with exhaustive search.

### 4.4 DAG accounting became mathematically serious

The fan-out progression is one of the strongest parts of the repository:

1. a naive propagation path minted shared intermediates;
2. the first fix blocked fan-out rather than fabricate a quantity;
3. the block was found to be leaf-blind;
4. an exact rational max-yield LP replaced the routing predicate as the quantitative authority;
5. a reused by-product exposed a second path where naive propagation still minted;
6. the LP became the number on every DAG, while the independent propagation is retained only as an agreeing display derivation where valid;
7. no-mint/no-deficit checks and differential fixtures constrain the implementation.

This is good triangulation: the project did not stop at a plausible structural predicate.

### 4.5 The inverse shopping problem is now a first-class calculation

`dag_shopping_requirement` answers the inverse quantity problem:

> To produce a declared final amount along this fixed DAG, what external species quantities are forced by exact conservation?

It credits internally produced by-products, computes net rather than gross consumption, and applies both sufficiency and tightness checks. It refuses the coupled multi-producer case rather than fabricate uniqueness.

### 4.6 Identity and evidence are less likely to borrow illegitimately

The project has added:

- explicit formula/constitution/configuration/isotopic lattice concepts;
- structure-keyed reaction evidence;
- typed loss blockers;
- production-path evidence downgrades when a claim depends on a lost feature;
- direction-specific assembly evidence;
- phase-context applicability in the sound rate providers;
- structure-keyed stock components;
- explicit documentation of stereo- and isotope-blind boundaries where they remain.

The latest red-team correctly caught that “same-formula isomer never borrows” was too broad when the key only represented constitutional identity.

### 4.7 The CLI is converging on one compiler rather than several scripts

`compile`, `recompile`, and `synthesize` have moved toward:

- one identity resolver;
- one typed request;
- one shared route engine;
- one response schema;
- stable exit classification;
- machine/human agreement;
- explicit provider and physical-bound levers.

This closes a major source of version skew and divergent semantics.

---

## 5. What is now strongest

### 5.1 Truthful boundedness

SmartChem increasingly knows the difference between:

- “no candidate exists in this finished finite search”; and
- “nothing was observed before a limit stopped the search.”

That distinction is foundational. A route compiler that cannot state its closure is not auditable.

### 5.2 Exact arithmetic at conservation boundaries

The formula engine, primitive stoichiometry work, exact rational LP, and inverse DAG requirement calculation place exact arithmetic where it matters most: conservation and identity of the finite mathematical model.

This does not establish chemistry, but it substantially reduces internal bookkeeping fiction.

### 5.3 Separation of identity layers

The project no longer casually treats formula, molecular constitution, finer configuration, and stock material as one value. The model is incomplete, but the direction is correct: unsupported refinement is blocked or recorded as a loss rather than silently forgotten.

### 5.4 Compiler-style provenance

Requests, registries, terminals, bounds, candidates, and receipts are increasingly content-addressed and transported together. This makes stale-artifact and hidden-default errors much easier to detect.

### 5.5 Red-team folds with real teeth

The best recent work follows a useful pattern:

```text
claim
  -> adversarial fixture
  -> reproduce defect
  -> identify root rather than patch symptom
  -> add a second derivation or fail-closed boundary
  -> record residual scope
```

The DAG-flow, shopping, service, IR-deserialization, identity, and stock arcs all benefited from this pattern.

---

## 6. Primary obstruction: the transform closure is still narrow

### 6.1 Current live closure

The service currently selects among three grammar identities:

```text
FORMULA_DECOMPOSITION
CAPPED_SCISSION_LINEAR
CAPPED_SCISSION_CONVERGENT
```

The latter two are different route topologies over the same capped-scission family, not independent chemical transform bases.

The structural generator is much broader than a single hard-coded hydrolysis rule. It can:

- cut one or more whole bonds;
- cut declared reagent bonds;
- preserve valence by rematching opened ends;
- use perfect matchings rather than a fixed reactant-to-reagent bijection;
- emit ring-forming and ring-opening whole-bond rewrites;
- enumerate chemically odd but graph-valid candidates for downstream evidence filtering.

That is valuable. It is still a specialized algebra.

The code itself names important exclusions:

- partial bond-order changes;
- addition across a multiple bond when not representable as a whole-bond rewrite;
- heterolytic/charged capped transformations in the main route grammar;
- general electronic-state and charge-localization transport;
- a broad sourced transformation-template corpus;
- mechanism-level elementary steps.

### 6.2 Why larger search bounds do not solve this

Increasing depth, cut count, result caps, or candidate budgets explores more of:

```text
Cl(current capped-scission operators)
```

It does not add a missing operator.

This is a **pathway gap**, not merely a search-budget gap.

A route absent because the current provider closure cannot express its defining bond-order, charge-transfer, rearrangement, or component transition will remain absent at arbitrarily large route depth. More search can only compose the available vocabulary.

### 6.3 Genericity claim boundary

The current defensible claim is:

> SmartChem provides generic bounded search and compilation machinery over its declared formula-decomposition and capped-scission grammars.

The current indefensible claim would be:

> SmartChem generically decompiles arbitrary chemistry into all relevant synthetic transformations.

The gap between those statements is now localized and testable.

---

## 7. The remaining inverse gap

### 7.1 What the current serialized inverse establishes

`recompile_from_serialized` is a meaningful bridge. It:

1. deserializes and revalidates a formula-level decompile IR;
2. receives a caller-supplied structural hypothesis;
3. verifies that the structural hypothesis has the same formula as the decompile artifact;
4. recompiles that supplied structure under declared terminals and bounds;
5. distinguishes routes-found, target-already-terminal, exhaustive grammar dead-end, and truncated inconclusive outcomes.

This proves that the decompile artifact constrains a later recompilation request.

### 7.2 What it does not establish

The current operation is logically:

```text
structure S
  -> forget topology -> formula F

then later:

serialized formula artifact F
  + caller-supplied structure S'
  + proof that formula(S') = F
  -> synthesis search for S'
```

It is not yet:

```text
structure S
  -> structure-preserving decomposition artifact D(S)
  -> recompile D(S)
  -> candidate reconstructions of S
```

The formula artifact cannot choose among constitutional isomers. The supplied structure does that work.

Therefore:

> The current inverse is a formula-compatibility-constrained structural search, not a structure-reconstructing inverse of the decompile artifact.

This is not a defect if stated accurately. It is the next architectural rung.

### 7.3 Recommended structural-IR commuting square

SmartChem already contains the ingredients for a stronger relation:

```text
Structural target  --D_structure-->  Structural decomposition IR
      |                                   |
      | forget topology                   | forget structural witnesses
      v                                   v
Formula target     --D_formula---->  Formula decomposition IR
```

The square should commute:

```text
forget(D_structure(S)) == D_formula(forget(S))
```

within the common declared inventory, transform subset, and bounds.

The structure-side candidate must retain:

- parent structure identity;
- exact cut/edit witness;
- structural fragments/products;
- rooted open-valence or charge/electron witness as applicable;
- the exact formula/charge-conservation projection;
- provider identity and direction;
- identity losses;
- formal/evidence grade;
- applicability and refusal facts.

This would turn `structure_descent.py` from strong adjacent machinery into a first-class compiler direction.

---

## 8. The transform registry is not yet a transform-provider registry

### 8.1 Current truth

`smartchem/transform_registry.py` currently supplies stable identities for three imperative grammars. Its own documentation correctly says that:

- there is no enumerable rule table being hashed;
- identity is a declared version token;
- an operator must remember to bump the descriptor when semantics change.

This is adequate for naming the current closed grammars. It is not sufficient for generic extensibility.

### 8.2 Required provider model

A real provider registry should make the live transform closure inspectable. A provider descriptor should include at least:

```text
TransformProviderDescriptor
  provider_id
  provider_version
  schema_version
  transform_family
  supported_operation: DECOMPOSE | ASSEMBLE | BOTH
  strongest_input_identity_layer
  strongest_output_identity_layer
  charge_model
  isotope_model
  stereochemistry_model
  component_model
  electronic_state_model
  participant_role_model
  context_requirements
  conservation_obligations
  termination_measure
  completeness_semantics
  evidence_scope
  implementation_or_manifest_digest
```

A provider invocation should return:

```text
TransformEnumerationResult
  applications[]
  receipt
  refusal_or_exclusion_reasons[]
```

Each `TransformApplication` should contain a witness that can be independently revalidated from the stored inputs.

### 8.3 Provider laws

Every provider should satisfy common laws:

1. **Determinism under canonical input and fixed bounds.**
2. **Presentation invariance** under the representation equivalences claimed by the selected identity policy.
3. **Conservation** of every quantity the provider claims to represent.
4. **No silent identity downgrade.**
5. **Explicit applicability.** “Not applicable,” “unsupported identity,” and “no candidate” are distinct.
6. **Receipt truth.** A budgeted enumeration cannot report complete after truncation.
7. **Provider-disable monotonicity.** Disabling a provider can remove candidates but cannot leave a receipt claiming the same closure digest.
8. **Registry sensitivity.** Adding, removing, or semantically changing a provider changes the transform-closure identity.
9. **Formal/evidence separation.** Provider generation alone cannot promote a candidate to sourced physical support.
10. **Independent witness validation.** A candidate is not certified solely by the same routine that generated it.

### 8.4 Migration probe

The existing capped-scission engine should be migrated behind the provider interface first, with byte-stable or intentionally versioned outputs.

That migration is the positive control. A second, qualitatively different provider is the real test.

If adding the second provider requires modifying the shared service, search result classification, base IR envelope, and CLI dispatch, then the provider boundary is not yet correct.

---

## 9. Canonical identity is now the most urgent foundational defect

### 9.1 Observed defect

The latest red-team found that fused aromatic structures such as naphthalene- or indole-like systems can receive different canonical digests when written in aromatic versus explicit Kekule form, while benzene passes.

The same represented species can therefore fail to match itself across equivalent spellings.

The repository correctly:

- classified this as deeper than `StockMaterial`;
- avoided a local stock-layer patch;
- filed `CANON-KEKULE-01`;
- pinned the desired invariant as a strict expected failure;
- documented stereo/isotope boundaries separately.

### 9.2 Why this has high blast radius

The shared canonical identity participates in:

- route terminal matching;
- DAG node identity;
- step and route deduplication;
- shopping requirements;
- stock-material component lookup;
- evidence lookup;
- request/result alias collapse;
- cache and artifact identity.

A fractured quotient relation propagates through every downstream compiler layer.

### 9.3 Required resolution strategy

Do not patch individual callers. Define the canonicalization contract first.

The contract must state which distinctions are:

- quotient-equivalent;
- preserved;
- unsupported and therefore refused or loss-marked.

At minimum, differential identity tests should cover:

- atom-index permutations;
- alternate ring numbering and traversal;
- aromatic versus valid Kekule spellings;
- resonance-equivalent representations included in policy;
- disconnected-component ordering;
- constitutional isomers;
- explicit isotope placement;
- tetrahedral and double-bond configuration where represented;
- formal/local charge distinctions;
- tautomer/protomer distinctions, with an explicit decision whether they are equal or distinct at each layer;
- salts, formula units, and mixtures, without forcing them into one connected molecule.

A canonicalizer must not infer an equivalence the identity policy has not declared.

### 9.4 Priority recommendation

`CANON-KEKULE-01` should be moved ahead of most transform-family expansion. Adding providers on top of an unstable identity quotient multiplies migration cost and can contaminate holdout results.

---

## 10. A specific error-semantics gap: `_conditions_for` swallows internal faults

The route search currently treats every exception raised by condition lookup as an unknown condition envelope.

Conceptually:

```python
try:
    return assembly_conditions(capped)
except Exception:
    return ConditionEnvelope.unknown()
```

The desired semantic distinction is:

```text
no matching evidence record
  !=
provider unavailable by declared policy
  !=
malformed provider data
  !=
programming error
```

A broad `except Exception` can launder an assertion failure, schema defect, index error, or corrupt provider state into the scientific statement “conditions unknown.”

This is a **probe gap** and a claim-integrity issue.

### Required correction

Introduce a narrow, typed absence/refusal result or exception for expected lookup misses. Only that case becomes `ConditionEnvelope.unknown()`.

Unexpected exceptions should propagate to the existing guarded `ERROR_INTERNAL` boundary, preserving the distinction between missing knowledge and broken software.

### Verdict-changing probe

Inject a deliberate internal fault into the assembly-condition provider through a test seam.

Pass:

```text
compile/search result -> ERROR_INTERNAL or propagated internal fault classification
```

Fail:

```text
route remains successful with conditions merely reported UNKNOWN
```

The positive control is a genuine no-record case, which must still produce an unknown envelope without aborting candidate generation.

---

## 11. Material and shopping integration is the next large payoff

The project now has two strong but partly latent calculations:

1. `StockMaterial.satisfies(...)`, which can distinguish sufficient, insufficient, and assay-unknown material fitness at the represented identity layer; and
2. `dag_shopping_requirement(...)`, which computes exact theoretical external species requirements for a fixed route/DAG.

They are not yet one production path.

### 11.1 Required integration

For each required external molecular identity and theoretical amount:

```text
route requirement
  -> material candidates
  -> identity-layer match
  -> assay/phase/quantity fitness
  -> required gross material range
  -> source/access/cost observations
  -> deficits and supplements
```

The compiler must preserve these distinctions:

- theoretical 100%-efficiency mole floor;
- expected reaction yield, if sourced or explicitly assumed;
- stock-material assay interval;
- available physical quantity;
- package quantity and cost observation;
- waste/excess/by-product disposition;
- alternative intermediate purchase versus internal manufacture.

### 11.2 Coupled optimization

The existing shopping inverse is route-fixed. The broader sourcing question is not always unique:

- buy an intermediate or synthesize it;
- choose among stock materials with different assay/cost/access profiles;
- trade money, risk, evidence quality, time, and equipment;
- allocate shared materials across alternate branches.

That is naturally a vector/Pareto problem, not one scalar “best route.” `COST-VEC-01` should therefore remain a separate optimization layer above exact conservation.

### 11.3 Acceptance probe

A route requiring pure acetic acid must not be declared stocked by an unknown-assay vinegar lead. The system should emit:

- the exact chemical requirement;
- the candidate stock material;
- `UNKNOWN_ASSAY` or `INSUFFICIENT_ASSAY` as appropriate;
- the unresolved measurement or supplement obligation;
- no fabricated purchasable quantity or cost.

---

## 12. Evidence and readiness remain separate lanes

### 12.1 Evidence strengths

The direction-specific structure-key work, loss-consumer gates, typed source citations, and phase-context applicability are strong. They make it harder for a plausible formula match to borrow structure-specific support.

### 12.2 Remaining evidence gaps

The current ledger still names:

- uneven source-record fields across providers;
- provider conflict visibility;
- broader context vocabulary;
- incomplete configuration/isotopic identity integration;
- formula-only legacy/test-only paths;
- some primitive reaction identity migration.

These matter, but they should not block the transform-provider architecture from being designed correctly.

### 12.3 Procedure readiness

`ProcedureIR` and process-scale hazard semantics remain absent. That means the compiler should continue to emit `FORMAL_CANDIDATE` route dossiers rather than executable bench procedures.

This is not the primary blocker for a generic **candidate compiler**. It is the primary blocker for a generic **bench recompiler**.

The roadmap should separate those products:

```text
candidate compiler
  -> evidence-qualified route compiler
  -> material-aware planning compiler
  -> chemist-editable bench-draft compiler
  -> validated procedure system
```

Skipping rungs would recreate the exact claim laundering the current architecture was built to prevent.

---

## 13. Obstruction classification

| Obstruction | Class | Why |
|---|---|---|
| Missing transform families | **Pathway gap** | No amount of search over current operators constructs an absent reaction family. |
| Structural decompile not first-class IR | **Pathway gap** | The formula artifact cannot retain the structure needed for a true structural inverse. |
| No frozen cross-family benchmark | **Probe gap** | There is no independent discriminator between “generic architecture” and “fit to current examples.” |
| Fused aromatic canonical non-invariance | **Defect / boundary violation** | Claimed same-object spellings split in the shared identity layer. |
| Broad condition-provider exception swallowing | **Probe/semantic gap** | Evidence absence and internal failure are observationally collapsed. |
| Stock/shopping not production-integrated | **Pathway gap** | The exact quantity and material-fitness routes exist but do not yet compose end to end. |
| Stereo/configuration/component identity | **Model boundary** | Current constitution model cannot honestly answer the finer identity question. |
| Procedure/safety incompleteness | **Declared product boundary** | Candidate dossiers are not bench procedures; this is real and should remain explicit. |
| Ledger stale residues | **State/provenance defect** | Historical “remaining” text can contradict later closure records. |
| No independent suite run in this audit | **Access gap** | Connector inspection did not execute the code. |

---

## 14. Roadmap reorientation

The roadmap should be split into three lanes so release closure, genericity, and bench readiness stop competing for one undifferentiated priority list.

## Lane A — stabilize and close the truthful alpha

### A0. Reconcile the governing ledger

- Reconcile rows whose “remaining” text was superseded by later bricks.
- In particular, remove stale claims that semantic alias collapse or full receipt transport remain absent where later records say they landed.
- Separate historical uptake records from current status fields.
- Generate summary tables from one machine-readable source if possible.
- Record audited base SHA and suite environment with every status snapshot.

**Acceptance:** no current row contradicts a later current row; historical narrative is clearly marked historical.

### A1. Fix canonical identity before broadening the provider set

- Resolve `CANON-KEKULE-01` at the shared canonicalizer.
- Add differential corpus tests across equivalent and non-equivalent representations.
- Re-run route, DAG, stock, shopping, service digest, evidence, and serialization tests.
- Do not local-patch each `_ident` consumer.

**Acceptance:** aromatic and valid explicit-Kekule forms of fused aromatics share the declared constitution digest; constitutional isomers remain distinct.

### A2. Split missing evidence from internal provider failure

- Replace the broad condition lookup catch.
- Add positive absence, negative internal-fault, and malformed-provider controls.
- Preserve top-level exit/status semantics.

**Acceptance:** genuine no-record -> UNKNOWN; injected internal fault -> ERROR_INTERNAL.

### A3. Finish the remaining `0.5.0a1` P0 integrations without broadening claims

Focus only on rows that block the published alpha contract. Do not pull `ProcedureIR` or arbitrary mechanisms into the release solely because they are important future work.

**Acceptance:** every P0 row is either `IMPLEMENTED_AND_VERIFIED` or the release contract is narrowed explicitly.

---

## Lane B — make the chemical algebra genuinely extensible

### B0. Add a structure-preserving decompile IR mode

- Promote structural scission candidates into `ChemicalCompilationIR`.
- Preserve edit witnesses and formula projections.
- Add the commuting-square oracle against formula descent.
- Keep formula mode as a legitimate coarser analysis, not as the only shared artifact.

**Acceptance:** a structural target can be decompiled, serialized, deserialized, and recompiled without requiring a second caller-supplied structure to recover constitutional identity.

### B1. Introduce the typed `TransformProvider` registry

- Define provider capability and receipt schemas.
- Derive the registry closure digest from the actual provider manifest.
- Migrate current capped scission as the positive control.
- Preserve current route/DAG outputs or version every intentional semantic change.

**Acceptance:** current capped-scission searches run exclusively through the provider boundary and retain receipt truth.

### B2. Freeze a transform-coverage benchmark before adding new families

Build a versioned corpus containing:

- positive cases each intended family should express;
- negative cases it must refuse or mark not applicable;
- null cases with no transformation;
- mutation controls differing by one identity/context feature;
- mixed-route cases requiring composition of two provider families;
- equivalent-representation controls;
- budget truncation controls;
- charge and component-boundary controls.

Split the corpus into development, validation, and holdout groups before implementation.

**Acceptance:** benchmark digests are frozen; holdout cases are not edited to rescue a provider.

### B3. Add the first genuinely independent transform family

The first new provider should not be a cosmetic wrapper around capped scission. Candidate families include, at an abstract graph/ledger level:

- partial bond-order change with exact electron/valence accounting;
- heterolytic/ionic transformation with explicit charge localization;
- redox/electron-transfer transformation using the existing carrier idiom;
- component association/dissociation where a connected molecule is not the right identity;
- a sourced reaction-template provider whose formal application remains separate from empirical support.

Choose one narrow family with a clean certificate and strong negative controls.

**Acceptance:** it passes its frozen holdout slice and can compose with capped scission without changes to the common compiler shell.

### B4. Demonstrate mixed-provider route composition

A target should require at least two qualitatively different provider families in one route or DAG.

The receipt must name the full provider closure and per-provider application/rejection counts.

**Acceptance:** disabling either provider removes the mixed route, changes the registry digest, and never leaves a false complete claim for the old closure.

### B5. Expand only after the provider laws survive

Do not add a large reaction corpus before:

- provider identity is stable;
- application witnesses are revalidated;
- mixed composition works;
- holdout discipline exists;
- identity canonicalization is sound at the claimed layer.

---

## Lane C — connect candidate compilation to real materials and eventual bench drafts

### C0. Wire DAG requirements into `StockMaterial`

- Convert route/DAG external molecular requirements into material-fitness queries.
- Preserve assay and quantity uncertainty.
- Emit deficits and measurement obligations.

### C1. Build vector affordability/sourcing

- Represent cost, access, evidence, equipment, hazard, and time as separate axes.
- Produce a Pareto frontier rather than a hidden scalar preference.
- Keep unknown dimensions visible.

### C2. Add `ProcedureIR`

Only after material requirements are real, define typed operations for:

- scale and vessel;
- addition order/rate;
- temperature/pressure trajectory;
- agitation;
- atmosphere;
- endpoint and sampling;
- quench;
- workup;
- purification;
- analytical acceptance;
- waste/off-gas routing;
- equipment ratings;
- operator review obligations.

### C3. Add process-scale hazard semantics and qualified review

Species-level hazard labels are not sufficient. Safety must depend on amount, concentration, conditions, incompatibilities, containment, off-gas, pressure, waste, and procedure ordering.

No automatic authorization should be introduced.

---

## 15. Frozen transform-coverage benchmark design

A genericity benchmark should test the compiler, not reward memorizing famous reactions.

### 15.1 Unit of evaluation

Each case should declare:

```text
case_id
input identity and representation
required identity layer
active providers and versions
terminal/material policy
bounds
expected applicability by provider
required conserved quantities
allowed candidate equivalence class
forbidden candidates or merges
expected completeness/refusal status
expected identity losses
expected evidence ceiling
```

### 15.2 Metrics

Report separately:

- parse and identity fidelity;
- canonical representation invariance;
- provider applicability precision;
- candidate coverage within the curated formal target set;
- false application rate;
- conservation-certificate success;
- duplicate collapse correctness;
- receipt/status correctness;
- route/DAG composition success;
- identity-loss propagation;
- evidence non-promotion;
- material-resolution outcome;
- runtime/search growth.

Do not collapse these into one “chemistry score.”

### 15.3 Controls

Every family should include:

- **positive control:** a supported transform;
- **negative control:** a near-neighbor outside its applicability;
- **null control:** no transform should be emitted;
- **mutation control:** one feature changes the expected decision;
- **representation control:** equivalent spelling, same result;
- **identity control:** same formula but distinct structure, no borrow;
- **budget control:** deliberately truncate, receipt becomes incomplete;
- **provider-ablation control:** disable provider, closure and candidates change coherently.

### 15.4 Holdout rule

Examples used to design a provider cannot validate the provider's genericity. Holdout results must be reported even when they are poor. A provider may be valuable with low coverage if its supported boundary is exact.

---

## 16. Machine-readable claim and roadmap ledger

The current uptake manifest is rich but increasingly susceptible to historical sediment. A generated ledger would reduce contradictions.

A minimal record could be:

```yaml
id: CANON-KEKULE-01
title: Canonical constitution identity is invariant across supported aromatic/Kekule spellings
priority: P0
lane: A
status: TODO
claim_scope: constitution identity
implementation_commits: []
acceptance_tests:
  - tests/test_stock.py::test_a_material_satisfies_its_own_identity_written_kekule
positive_controls: []
negative_controls: []
known_boundaries:
  - configuration identity remains separate
  - tautomer equivalence is not implied
supersedes: []
superseded_by: []
last_verified_commit: 4774a26f2d2153bab3a98d0da5013e416b221ad5
verification_command: null
verification_result: UNVERIFIED_IN_THIS_AUDIT
```

Generate:

- current status tables;
- dependency graph;
- stale/superseded warnings;
- P0 release gate;
- roadmap lane views;
- test references;
- unresolved claim boundaries.

Historical narrative can remain in Markdown, but current truth should have one authority.

---

## 17. Recommended implementation sequence

The next branch sequence should be deliberately narrow:

### Commit 1 — roadmap and ledger reconciliation

- Integrate this audit into the roadmap.
- Correct stale current-status text.
- Add Lane A/B/C separation.
- Do not change chemistry behavior.

### Commit 2 — canonicalization contract and differential corpus

- Write the identity equivalence policy.
- Add controls before the implementation change.
- Keep the fused-aromatic xfail strict until the fix lands.

### Commit 3 — canonicalizer fix

- Fix the shared root.
- Remove the strict xfail only when the desired invariant passes.
- Run broad identity-sensitive tests.

### Commit 4 — condition-provider error semantics

- Introduce typed absence/refusal.
- Add internal-fault injection.
- Remove the broad exception laundering.

### Commit 5 — structural IR design and first producer

- Define structural candidate schema and witnesses.
- Emit from existing structure descent.
- Serialize and round-trip.
- Add formula-projection commuting test.

### Commit 6 — structural inverse

- Recompile from the structure-preserving artifact.
- Prove the supplied-structure parameter is no longer required for the structural mode.
- Keep formula-mode compatibility bridge separately named.

### Commit 7 — provider registry skeleton and capped-scission migration

- No new chemistry yet.
- Pass regression and provider-ablation tests.

### Commit 8 — freeze benchmark

- Commit development/validation/holdout manifests.
- Record hashes before new provider implementation.

### Commit 9+ — first independent provider

- Implement one narrow family.
- Pay truth debt on frozen holdouts.
- Do not broaden its stated domain after seeing failures without recording a benchmark version change.

---

## 18. Explicit anti-goals for the next round

Do **not**:

1. call larger capped-scission searches “generic chemistry”;
2. implement dozens of reaction templates before the provider contract and holdout benchmark exist;
3. fix canonical identity only in stock, routes, or one evidence caller;
4. treat formula decompile + supplied structure as a structure-reconstructing inverse;
5. swallow internal provider bugs as scientific UNKNOWN;
6. convert exact theoretical stoichiometric floors into predicted purchase amounts without yield/assay handling;
7. scalarize cost, safety, evidence, access, and equipment into one undocumented score;
8. promote route dossiers above `FORMAL_CANDIDATE` because the compiler shell is mature;
9. mark a row complete through documentation alone;
10. let a fitted example validate the provider designed from it;
11. rename a boundary away instead of building the discriminating probe;
12. broaden the alpha release contract merely to absorb future research goals.

---

## 19. Verdict-changing probes

The following probes would materially change this audit's verdict.

### Probe P1 — structural artifact inverse

**Question:** Can a structure-preserving decompile artifact be recompiled without a separately supplied target structure?

- **Pass:** structural identity and edit witnesses survive serialization; recompilation consumes them directly.
- **Fail:** the artifact still reduces to formula and requires an external structure to choose the isomer.
- **Ambiguous:** structure is serialized only as an opaque label not used by the search.

### Probe P2 — second-provider architecture

**Question:** Can a qualitatively different transform family be added without changing the compiler shell?

- **Pass:** provider-only implementation plus provider tests; mixed routes work.
- **Fail:** service/IR/search/CLI require family-specific branches.
- **Ambiguous:** provider exists but is never reached from production search.

### Probe P3 — provider closure receipt

**Question:** Does the receipt identify the actual live provider set?

- **Pass:** adding/removing/changing a provider changes registry identity and per-provider telemetry.
- **Fail:** manual version token remains unchanged while behavior changes.

### Probe P4 — frozen holdout

**Question:** Does the new provider survive examples not used to design it?

- **Pass:** predeclared positive/negative/null/mutation outcomes are reported without benchmark edits.
- **Fail:** cases are changed after implementation or only fitted examples are reported.

### Probe P5 — canonical quotient

**Question:** Do equivalent fused-aromatic spellings collapse while real constitutional differences remain?

- **Pass:** differential suite establishes both sides.
- **Fail:** same species split or different isomers merge.

### Probe P6 — provider fault versus evidence absence

**Question:** Can the system distinguish “no evidence” from “provider crashed”?

- **Pass:** absence -> UNKNOWN; injected fault -> ERROR_INTERNAL.
- **Fail:** both -> UNKNOWN.

### Probe P7 — material integration

**Question:** Does a route requirement resolve against actual material fitness and amount?

- **Pass:** assay/quantity intervals govern satisfaction and deficits.
- **Fail:** commodity name or molecular identity alone clears the requirement.

---

## 20. Updated project statement

The most accurate current public framing is:

> SmartChem is a bounded, receipt-bearing chemical compiler research system. It parses chemical identity with explicit losses, enumerates conservation- and represented-valence-valid candidates within declared formula-decomposition and capped-scission transform closures, forms linear routes or convergent DAGs, ranks formal candidates against typed evidence and constraints, and preserves uncertainty, provenance, material, and readiness boundaries. It does not yet implement a generic chemical transform-provider algebra, a structure-reconstructing inverse for arbitrary targets, or bench-ready procedures.

The most useful future framing is:

> SmartChem is a problem-oriented chemical compiler whose generic substrate is fixed while its chemical vocabulary is supplied by versioned, typed transform providers with independently checkable witnesses and closure-relative search receipts.

---

## 21. Final assessment

### Disclosed within the current model

- The compiler has a substantial typed service and IR seam.
- Formula decomposition is exact within its declared finite formal space.
- Structural capped-scission candidates preserve the represented graph/valence accounting they certify.
- Route and DAG search can report bounded completeness.
- DAG fan-out and fixed-route shopping quantities have exact conservation machinery.
- Stock materials are distinguished from pure molecular identity.
- Formal candidates remain below bench readiness.

### Corroborated but not independently rerun here

- The current repo-reported 3,397-pass suite supports the stability of these contracts.
- Recent adversarial folds materially improved IR tamper checks, search truth, DAG accounting, identity keys, and CLI coherence.

### Conjectured, with named truth debt

- The existing compiler shell can support a genuinely extensible transform algebra without major redesign.
- Structural descent can be promoted into a first-class IR while preserving the formula projection.
- Mixed-provider search can reuse the current route/DAG and receipt machinery.

### Refuted in the broad form

- SmartChem does not yet generically enumerate arbitrary chemistry.
- The current formula artifact is not a structure-reconstructing inverse.
- The current transform registry is not yet an inspectable transform-provider registry.
- Equivalent fused-aromatic spellings do not yet always share one canonical identity.

### Dominance verdict

The current frame dominates the September 1 frame because it explains both the large architectural progress and the remaining failures without contradiction:

```text
The compiler substrate is becoming generic.
The active chemical operator basis is not yet generic.
```

That is the reorientation.

The next milestone is not “more routes from the same grammar.” It is:

```text
structure-preserving IR
  + typed provider registry
  + frozen cross-family benchmark
  + one independent provider
  + mixed-provider route composition
```

When those survive the named probes, SmartChem can responsibly move from:

```text
generic compiler machinery over capped scissions
```

into:

```text
a genuinely extensible generic chemical decompiler/recompiler architecture.
```
