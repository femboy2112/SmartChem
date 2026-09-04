# SmartChem Chemical Compiler Standard — target v0.5.0a1

**Status:** proposed mainline contract  
**Target release:** `0.5.0a1`  
**Date:** 2026-09-01  
**Companion audit:** `AUDIT_CHEMICAL_COMPILER_2026-09-01.md`  
**Implementation ledger:** `UPTAKE_MANIFEST_v0.5.0a1.md`

## 1. Purpose

This standard defines the first coherent public contract for SmartChem's chemical decompiler
and synthesis recompiler.

The decompiler answers:

> Within a declared identity model, transform registry, terminal inventory, and finite search
> horizon, what conservation-valid decomposition candidates lead from this target toward those
> terminals, and how complete was the search?

The recompiler answers:

> Among the candidate assembly routes represented by that artifact, which routes best satisfy
> the declared materials, equipment, cost, evidence, and safety constraints, and what is still
> unknown before any route could become a bench draft?

The two operations share one intermediate representation and one truth vocabulary. SmartChem
MUST NOT claim an absolute enumeration of “all chemical pathways.” Completeness is meaningful
only relative to a finite, serialized search space.

The standard intentionally prioritizes claim integrity over coverage. A small compiler that
returns a precise refusal is conformant. A broad generator that silently loses identity, search
completeness, direction, or material context is not.

### 1.1 Audit-branch implementation snapshot (non-normative)

The branch `codex/chemical-compiler-standard-2026-09-01` implements and tests a useful subset of
this contract. The final recorded post-change verification is **2510 passed, 51 skipped, 1
expected failure in 205.04 seconds**; an earlier targeted chemistry/CLI/safety slice recorded
**405 passed in 144.24 seconds**. G0's test gate is met for this branch snapshot, while the
semantic conformance gaps named below remain open.

| Standard area | Verified branch uptake | Still required for conformance |
|---|---|---|
| Search truth | Linear `search_routes` returns `RouteSearchReceipt`, preserving cut-budget and result-limit partiality; human no-route output carries that distinction | Equivalent formula and DAG receipts, unified response/JSON, and complete cross-path counters |
| Conditions/evidence | Direction-specific exact structure-keyed assembly lookup; free-text stays declared; selectivity promotion requires an accepted typed citation | Curator/date/provider context, general identity/phase/role/conflict key |
| Stoichiometry/topology | Primitive coefficient vector in feasibility, equilibrium and kinetics; scale-invariant selectivity; positive-net-consumption route continuity | One canonical reaction identity across all providers/digests/DAGs and quantity flow |
| Formula/terminals | Formula inventory terminates; exact active structural stock yields zero expansion; inventory canonicalization and complete periodic-table parsing | Shared material-aware `TerminalPolicy` and explicit element packaging |
| Structural scission | Rooted open-valence identity, neutral-only refusal, duplicate reagent-type deduplication | Stereo/isotope/salt/mixture/phase identity layers |
| Inventory/affordability | No implicit one-mole CLI feed; active commodity policy, identity-only material caveat, and external-leaf shopping | `StockMaterial`, typed quantities/assays, DAG flow, cost vectors and Pareto ranking |
| Dossier/safety | `FORMAL_CANDIDATE` route evidence dossier with missing operations; controlled non-flame heat; no emitted `PROCEED_UNATTENDED`; strict constraint ranges | `ProcedureIR`, process-scale hazards, hazard coverage and qualified review |
| CLI/version | Registered names, entry point/version, strict diagnostics, and codes 0/2/3/4/5 on named outcomes | One typed service, canonical `recompile`, all identity formats, stable JSON and code 70 mapping |

This snapshot does not weaken any normative gate below. “Verified” is deliberately scoped to the
named branch path; broader rows remain `IN_PROGRESS` in the uptake manifest.

## 2. Normative language

The words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** are
normative.

The standard uses these truth labels:

- `ENFORCED`: guaranteed by validation or construction;
- `MEASURED`: observed on a finite named domain;
- `DERIVED`: calculated from explicit inputs and a named model;
- `SOURCED`: supported by an inspectable source matching identity, direction, and context;
- `ASSUMED`: supplied for exploration but not independent evidence;
- `UNKNOWN`: information required for a claim is missing;
- `INCOMPLETE`: a bounded search stopped before exhausting its declared space;
- `REFUSED`: a validity boundary intentionally prevents an answer.

An `ASSUMED` field MAY enable a scenario calculation. It MUST NOT promote an evidence or
readiness tier by itself.

## 3. Non-goals and scientific boundary

Version `0.5.0a1` is not required to:

- discover arbitrary mechanisms or reaction templates;
- predict that a formal reaction occurs;
- infer unrecorded kinetics, selectivity, yield, workup, purification, or safety;
- model every element, salt, coordination complex, phase, mixture, isotope, stereoisomer, or
  electronic state;
- guarantee the cheapest, safest, best, or successful synthesis outside a search space whose
  completion is certified;
- turn a retail product name into a pure-reagent specification;
- emit a protocol suitable for unaided execution.

SmartChem MAY derive consequences of a declared physical model. Every derived value MUST name
the model, inputs, context, units, uncertainty behavior, and validity/refusal boundary. A
balanced equation proves conservation, not realizability.

## 4. One compiler, two directions

### 4.1 Shared artifact

Both operations MUST consume or emit a versioned `ChemicalCompilationIR`.

At minimum, the IR contains:

```text
ChemicalCompilationIR
  schema_version
  tool_version
  request_digest
  target: ChemicalIdentity
  identity_losses[]
  terminal_policy: TerminalPolicy
  transform_registry: RegistryReceipt
  evidence_registry: RegistryReceipt
  search: SearchReceipt
  candidates[]: CandidateTransform | CandidateRoute | CandidateDAG
  diagnostics[]
```

The serialized digest MUST change when any semantic input changes, including identity state,
transform/evidence provider version, terminal policy, search bound, constraint, or evidence
grade. Display labels and ordering MUST NOT change a semantic digest.

### 4.2 Decompile

`decompile` traverses candidates from target toward terminals. Each emitted hyperedge MUST:

- conserve every represented element and total charge exactly;
- use primitive integer stoichiometry;
- record the identity layer at which it was generated;
- carry a transform generator ID and version;
- carry an explicit direction;
- distinguish formal admissibility from physical/literature evidence;
- pass the termination rule or be refused;
- expose any structure/phase/material information forgotten by the operation.

A formula-level edge MAY be `FORMAL_CANDIDATE`. It MUST NOT be silently upgraded to a
structure-specific chemical claim.

### 4.3 Recompile

`recompile` reads candidate edges in the assembly direction, forms routes or dependency DAGs,
and ranks them against a typed request. Reversal of a conserving equation does not reverse its
conditions, kinetics, selectivity, mechanism, or literature evidence. Assembly evidence MUST be
looked up independently in the assembly direction.

The recompiler MUST preserve every decompiler loss marker and search limit. It MUST NOT call a
best route “best” without the qualifier “among the returned candidates” unless the declared
candidate space is complete.

## 5. Identity model

### 5.1 Required identity layers

The compiler distinguishes at least three values:

1. `FormulaIdentity`: elemental counts and total charge, with no topology claim;
2. `MoleculeIdentity`: atom/bond graph plus every supported local charge, isotope,
   stereochemical, component, and electronic-state field;
3. `StockMaterial`: one or more chemical identities with phase, assay/formulation, quantity,
   provenance, access, and cost metadata.

A `FormulaUnit` or equivalent MUST represent salts/ionic solids when a connected molecular graph
would make a false covalent claim. A mixture MUST NOT be forced into a single molecule.
Standard InChI is useful as one identity representation, but it has defined normalization and
representation boundaries; the [InChI technical paper](https://link.springer.com/article/10.1186/s13321-015-0068-4)
and [InChI technical FAQ](https://www.inchi-trust.org/technical-faq/) are explicit that mixtures
are not represented as one InChI. SmartChem therefore MUST retain its own typed material and
loss records rather than treating one string identifier as the entire physical state.

### 5.2 Parsing and normalization

Every user input MUST declare or resolve to one of:

- name;
- SMILES;
- InChI;
- molecular formula;
- structured SmartChem identity/material document.

The CLI SHOULD support explicit flags and prefixes rather than a private positional grammar.
Conservative auto-detection MAY be offered when unambiguous. The normalized interpretation MUST
be echoed in human output and serialized in machine output before search begins.

Name resolution and standardization MUST report their source and policy. Different
standardization pipelines can choose different parent structures and representations; the
[PubChem standardization description](https://pmc.ncbi.nlm.nih.gov/articles/PMC6086778/) is a
useful primary example of why a normalization policy must be versioned, while the
[PubChem identity search help](https://pubchem.ncbi.nlm.nih.gov/search/help_search.html) shows
that identity searching itself has multiple modes.

### 5.3 Information-loss rule

If a parser or operation cannot preserve a represented feature, it MUST do exactly one of:

- `REFUSED_IDENTITY_UNSUPPORTED`;
- continue with an `IdentityLoss` record and lower the claim to a layer for which it is true.

It MUST NOT silently discard stereochemistry, isotope labels, formal charges, disconnected
components, phase, or material composition.

Each `IdentityLoss` contains:

```text
feature
input_representation
retained_representation
reason
affected_claims[]
severity: WARNING | BLOCKER
```

Sourced conditions, selectivity, kinetics, and hazard records MUST NOT survive a loss marked as
a blocker for their matching key.

### 5.4 Formula equality is not structure equality

Formula matching is permitted for atom-balance and formula-search operations. It MUST NOT:

- terminate a structure search as though an isomer were on hand;
- attach structure-specific conditions or selectivity;
- deduplicate structure routes;
- assert product identity or purity.

**Acceptance probe:** same-formula isomers must share formula balance where appropriate and
remain distinct everywhere a structural or material claim is made.

## 6. Stoichiometry and transform identity

### 6.1 Primitive canonical form

Every reaction MUST have a canonical signed coefficient vector. Divide all nonzero integer
coefficients by their greatest common divisor and choose one canonical direction sign.

The primitive vector is used for:

- reaction/evidence keys;
- route identity and deduplication;
- selectivity and kinetics lookup;
- per-reaction thermodynamic and equilibrium classification;
- invariance tests.

An explicitly declared extent MAY scale extensive values. Intensive classification MUST be
invariant under a common positive coefficient multiplier.

### 6.2 Roles and continuity

Participants MUST carry roles where known: reactant, product, catalyst, solvent, reagent,
workup material, quench, internal intermediate, byproduct, off-gas, waste.

A linear route dependency exists only when a prior product has strictly positive net
consumption in a later step. A catalyst or spectator appearing with equal coefficients on both
sides MUST NOT establish continuity.

A DAG MUST account for fan-out quantitatively. Reusing an intermediate in two branches does not
create two quantities of it. Until quantity-flow conservation is implemented, such a DAG MUST
be marked `FORMAL_TOPOLOGY_ONLY` and MUST NOT produce a quantitative ceiling.

## 7. Terminal and inventory policy

Every search uses an explicit `TerminalPolicy`:

```text
TerminalPolicy
  identity_layer
  match_mode: EXACT | FORMULA_ONLY
  terminals[]
  element_packaging_policy
  allow_reagents_as_terminals
  allow_commodities_as_terminals
```

`EXACT` is required for structure and material compilation. `FORMULA_ONLY` is allowed only for
formula analysis and MUST be visible in the readiness/claim tier.

When a node matches the active policy, it MUST terminate. If the target itself matches, the
system MAY return an already-available result, but only for the active inventory. A globally
known commodity not enabled by the request MUST NOT short-circuit the search.

The elemental policy MUST state whether a bucket is monatomic element count, a conventional
standard-state species such as O2, or an actual stock material. Those are different claims.

## 8. Search completeness contract

### 8.1 Search receipt is mandatory

Every decompile, recompile, linear route, and DAG search MUST return a `SearchReceipt`, including
when zero candidates are found or the request is refused.

Minimum schema:

```text
SearchReceipt
  schema_version
  search_kind
  target_identity_digest
  terminal_policy_digest
  transform_registry_digest
  max_depth
  cut_budget_scope: GLOBAL | PER_NODE
  cut_budget
  candidate_limit
  result_limit
  nodes_visited
  transforms_considered
  candidates_emitted
  candidates_rejected_by_reason{}
  results_returned
  cut_enumeration_complete
  candidate_enumeration_complete
  result_limit_saturated
  stop_reason
  status
```

Counters that are not yet available MUST be `null`/`UNKNOWN`, not zero.

### 8.2 Statuses

Allowed terminal statuses:

- `COMPLETE_WITHIN_DECLARED_SPACE`;
- `INCOMPLETE_CUT_BUDGET`;
- `INCOMPLETE_DEPTH_LIMIT`;
- `INCOMPLETE_CANDIDATE_LIMIT`;
- `INCOMPLETE_RESULT_LIMIT`;
- `REFUSED_INVALID_REQUEST`;
- `REFUSED_IDENTITY_UNSUPPORTED`;
- `ERROR_INTERNAL`.

More than one limit MAY be recorded, but one primary stop reason is required.

### 8.3 No-route semantics

The user-facing outcomes are:

| Candidates | Receipt | Required wording |
|---|---|---|
| none | complete | `NO_ROUTE_IN_DECLARED_SPACE` |
| none | incomplete | `INCOMPLETE_NO_ROUTE_OBSERVED` |
| one or more | complete | `COMPLETE_CANDIDATE_SET` |
| one or more | incomplete | `PARTIAL_CANDIDATE_SET` |

The bare phrase “no route found” MUST NOT appear without the receipt state and bounds.

### 8.4 Meaning of “all pathways”

SmartChem MAY say “all pathways” only as:

> all distinct candidates generated by transform registry `<digest>` over identity model
> `<version>`, terminal policy `<digest>`, and the stated bounds, with receipt status
> `COMPLETE_WITHIN_DECLARED_SPACE`.

It MUST NOT imply all pathways permitted by nature or all transformations known in chemistry.

**Acceptance probe:** reduce a cut/result budget below the value required for a known fixture.
Both human and JSON output must become partial/incomplete without changing any other input.

## 9. Evidence and provenance contract

### 9.1 Evidence key

A reaction evidence record is keyed by:

```text
ReactionEvidenceKey
  primitive_reaction_identity
  reactant_structure_identities[]
  product_structure_identities[]
  direction
  participant_roles[]
  phase_and_standard_state
  condition_domain
  transform_or_mechanism_scope
```

Formula-only records MAY decorate formula candidates as ambiguous hints. They MUST NOT earn a
structure-specific `SOURCED`, `KNOWN`, or `LITERATURE_SUPPORTED` label.

### 9.2 Source record

Every `SOURCED` value contains:

- stable source identifier or URL/DOI/accession;
- exact locator where practicable;
- extraction/curation date;
- curator or provider ID and version;
- reported value, units and uncertainty as published;
- phase, standard state and condition domain;
- transformation direction;
- independence/correlation group;
- any mapping or normalization performed.

Reaction data should be modeled as structured inputs, outcomes, conditions and workups rather
than a condition string attached to an equation. The
[Open Reaction Database schema](https://docs.open-reaction-database.org/en/latest/schema.html)
is a relevant primary reference for this separation and should inform, not be confused with,
SmartChem's own evidence schema.

For thermochemical values, provider records MUST retain phase, uncertainty, reference state and
source. The [NIST Chemistry WebBook guide](https://webbook.nist.gov/chemistry/guide/) illustrates
that thermochemical data are property-, unit-, phase-, and condition-specific; importing a bare
number is nonconformant.

### 9.3 Direction rule

Conditions and evidence are directional. A source for hydrolysis does not establish reverse
condensation conditions. Algebraic reversal MAY produce a `FORMAL_CANDIDATE` only. Promotion
requires an independent assembly-direction record.

### 9.4 Assumptions and conflicts

User-declared conditions have status `ASSUMED` unless accompanied by an accepted source record.
Free-text provenance MUST NOT earn a higher grade.

If providers disagree beyond their stated uncertainty/context, SmartChem MUST emit a
`ProviderConflict`. It MUST NOT silently take the first record. A configured priority policy MAY
choose one for an exploratory ranking, but the conflict and choice remain visible and cannot
earn a stronger tier than the selected record supports.

### 9.5 Derived quantities

Every derived value contains:

```text
value
unit
model_id_and_version
inputs_and_input_evidence
condition_context
uncertainty_or_unknown
assumptions[]
validity_domain
claim_status: DERIVED
```

`K = exp(-DeltaG/RT)` is an ideal thermodynamic relation under the represented standard-state
model. It MUST NOT be rendered as expected isolated yield or practical conversion without an
activity/composition model. Kinetic half-life/rate labels MUST be refused when reaction order,
rate-constant units, temperature, or required concentrations are missing.

## 10. Material, poor-man bucket, and affordability contract

### 10.1 Commodity records are source leads

A commodity record states that a chemical identity may occur in a type of accessible source.
It is not evidence that an arbitrary retail material has suitable assay, formulation, purity,
phase, grade, legal status, or quantity.

Human output MUST include that distinction. A commodity identity match MAY suggest a source; it
MUST NOT silently satisfy a `StockMaterial` requirement.

### 10.2 Stock material

Minimum `StockMaterial` schema:

```text
StockMaterial
  material_id
  display_name
  components[]:
    chemical_identity
    role
    fraction_or_concentration_interval
    uncertainty
  phase
  formulation_notes[]
  known_impurities[]
  assay_method
  quantity: value + unit | UNKNOWN
  container_and_storage
  opened_or_age_state
  provenance
  jurisdiction_and_availability
  cost_observation | UNKNOWN
```

Mixture component fractions need not be perfectly known; intervals and `UNKNOWN` are valid.
An operation that needs pure acetic acid cannot accept vinegar merely because both contain
acetic acid. It must either reject the material, prove the assay requirement is met, or add
explicit preprocessing, yield loss, hazards, analytical checks, waste, and cost.

### 10.3 Inventory flow

Shopping lists contain external route leaves only. An intermediate produced in the route MUST
NOT be listed as an external purchase unless extra purchased quantity is required.

Quantitative ceilings, material balances and costs require typed quantities and assay. An
identity-only inventory MUST return symbolic needs or `QUANTITY_UNKNOWN`; it MUST NOT assume one
mole, one bottle, 100% assay, or unlimited supply.

For DAG fan-out, produced and consumed quantities MUST balance across edges. Until then,
quantitative results are blocked.

### 10.4 Cost vector and route ranking

Affordability is multi-objective. A conformant `CostVector` contains, where available:

- cash outlay and currency/date/region;
- required new equipment;
- material quantity and package waste;
- energy estimate;
- labor/elapsed-time estimate;
- preprocessing/purification burden;
- analytical burden;
- waste-treatment/disposal burden;
- supply confidence;
- evidence/readiness tier.

Unknown values remain unknown. Price observations MUST be dated and sourced; the compiler MUST
NOT invent prices.

Default poor-man ranking SHOULD expose a Pareto frontier. It MUST NOT trade away a hard safety,
identity, legal, or equipment constraint for lower cost. User weights MAY order the non-blocked
frontier and MUST be serialized in the request.

## 11. Constraints and fit

A `ConstraintBox` is a validated target-bench description. Numeric limits MUST be real, finite,
in supported units, nonnegative where physically required, and internally ordered. Unit
conversion MUST be explicit.

Fit statuses are:

- `ASSESSED_FIT`: every constrained dimension required by the route is known and within bounds;
- `UNKNOWN_FIT`: a required dimension or equipment/material property is unknown;
- `UNCONSTRAINED`: no meaningful bench constraint was supplied;
- `EXCLUDED`: a hard constraint is violated;
- `BLOCKED`: a safety/identity/readiness blocker exists independent of preference.

`UNCONSTRAINED` MUST NOT render as `FITS`. An unknown condition under a temperature/pressure cap
is `UNKNOWN_FIT`, not a pass.

## 12. Route dossier and procedure readiness

### 12.1 Current output name

The output constructed from candidate steps, evidence decorations, equipment suggestions and
derived diagnostics is a **route dossier**. It MUST NOT be called a full, runnable, executable,
or guaranteed procedure.

Every dossier begins with:

- readiness tier;
- search completeness status;
- target identity and loss markers;
- blocking issues;
- unresolved operational/material fields;
- statement that qualified review is required before execution.

### 12.2 Readiness tiers

| Tier | Required facts | Meaning |
|---|---|---|
| `FORMAL_CANDIDATE` | Conservation-valid transform/route, explicit identity and search boundaries | Algebraically represented candidate; no occurrence claim. |
| `LITERATURE_SUPPORTED` | Exact identities and direction have accepted sources in the declared context | Evidence-supported route concept; still not operationally complete. |
| `BENCH_DRAFT` | All required procedure/material fields below are present, consistent, and reviewed; no blockers | Chemist-editable draft, not a guarantee of success or safety. |
| `BLOCKED` | Contradiction, unsupported identity, incomplete safety-critical field, or violated hard constraint | Do not execute from this artifact. |

Routes may be `INCOMPLETE_SEARCH` in addition to a readiness tier. A high evidence tier does not
repair an incomplete search claim, and complete search does not repair low evidence.

### 12.3 Procedure IR

A `BENCH_DRAFT` requires a typed `ProcedureIR` with, at minimum:

```text
target_scale_and_acceptance
stock_materials_with_assay_and_quantity
stoichiometric_table_and_limiting_reagent
vessel_material_volume_and_ratings
atmosphere_and_containment
temperature_pressure_and_control_method
order_and_rate_of_addition
mixing_and_heat_transfer
hold_time_or_endpoint_basis
sampling_and_monitoring
quench_sequence_and_stop_conditions
workup_operations
purification_operations
identity_purity_and_yield_checks
byproduct_offgas_and_waste_streams
hazards_incompatibilities_and_controls
emergency_and_scale_up_exclusions
sources_assumptions_and_unresolved_fields
qualified_review_record
```

Required fields MUST be typed values or explicit `UNKNOWN`. A safety-critical `UNKNOWN` makes the
tier `BLOCKED`; other unknowns keep the artifact below `BENCH_DRAFT`.

### 12.4 Safety semantics

SmartChem MUST NOT emit `SAFE`, `PROCEED_UNATTENDED`, automatic open-flame clearance, or an
equivalent action authorization from the present heuristic data.

Equipment suggestions are compatibility candidates. A high-temperature requirement SHOULD
default to controlled non-flame heat with compatibility unassessed. Positive flammability data
MUST veto open flame. Missing hazard data do not imply benign behavior.

Laboratory planning must account for chemical hygiene, exposure controls, quantities, emergency
procedures and training; the US [OSHA Laboratory Standard](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1450)
and its non-mandatory [Appendix A guidance](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1450AppA)
are authoritative examples of why a hazard name or apparatus suggestion is not a complete
operational safety assessment. SmartChem records jurisdiction and SHOULD link the applicable
local requirements; it MUST NOT imply that one jurisdiction's guidance is universal.

The strongest automatic negative finding is `NO_LOADED_TRIGGER_IDENTIFIED`, scoped to named
checks. It is not evidence that no hazard exists.

## 13. Service contract

### 13.1 Request types

One public service powers every CLI and library front door:

```text
CompilationRequest
  operation: DECOMPILE | RECOMPILE
  target_input
  input_kind
  identity_policy
  terminal_policy
  stock_materials[]
  helper_reagents[]
  transform_registry_selection
  evidence_provider_selection
  search_bounds
  constraints
  ranking_policy
  output_policy
```

Defaults MUST be explicit fields with `origin=DEFAULT`, not invisible branches in commands.
Two request objects with the same semantic digest MUST execute the same search regardless of
which CLI alias created them.

### 13.2 Response types

```text
CompilationResponse
  request
  normalized_target
  identity_losses[]
  search_receipt
  candidates[]
  ranked_route_dossiers[]
  affordability_frontier[]
  diagnostics[]
  status
```

Provider data and dynamic price/availability inputs MUST carry snapshot IDs or timestamps so a
response is reproducible.

## 14. CLI contract

### 14.1 Canonical commands

```text
smartchem decompile [TARGET] [identity and search options]
smartchem recompile [TARGET | --from ARTIFACT] [inventory and constraint options]
smartchem --version
```

`compile` and `synthesize` MAY remain aliases for one deprecation cycle. They MUST construct the
same typed request as `recompile` under equal flags and MUST NOT keep divergent defaults — in
particular, an alias MUST NOT default to a shallower search, a different terminal policy, or a
live-network provider that its canonical verb reaches only on request.

The default evidence provider MUST be the offline, reproducible seed/cache: a request built from
defaults is byte-reproducible and its response replayable. A live-network fetch is an explicit
opt-in (e.g. `--network`), and per §13.2 its provider data MUST carry snapshot IDs or timestamps
so the response stays reproducible. This holds for every verb; no command reaches the network by
default.

An `inspect ARTIFACT` convenience command MAY render an existing artifact, but it is not a
release gate for this alpha.

The package MUST install a `smartchem` console script. `python -m smartchem` and the script MUST
report the same version and behavior.

### 14.2 Input ergonomics

Supported explicit forms SHOULD include:

```text
--name "acetic anhydride"
--smiles "CC(=O)OC(C)=O"
--inchi "InChI=..."
--formula "C4H6O3"
--target-file request.json
```

Positional auto mode MUST echo its interpretation and provide an explicit override. Invalid or
ambiguous input yields a concise domain error, not a traceback.

Inventory accepts structured material files and repeated flags for names/identities. Quantities
MUST require units. Identity-only `--have` is permitted but cannot drive a numeric ceiling.

### 14.3 Output modes

- Human output is descriptive and editable, but must retain tiers, receipts, unknowns and IDs.
- `--json` emits the stable versioned response schema.
- Future table/Markdown output MUST be a view of the same response, not a separate calculation.
- `--quiet` MAY suppress narrative but MUST NOT suppress blockers in a successful-looking result.

### 14.4 Exit statuses

| Code | Meaning |
|---:|---|
| 0 | Valid request, one or more candidates, complete within declared space. |
| 2 | Invalid arguments or unparseable/ambiguous identity. |
| 3 | Valid request, complete search, no route in declared space. |
| 4 | Valid request, partial/incomplete search; candidates may or may not be present. |
| 5 | Request refused at identity, model, evidence, safety, or constraint boundary. |
| 70 | Internal software error. |

No-route MUST NOT exit zero. An incomplete result MUST NOT share the complete-success code.

## 15. Ranking contract

Ranking is a deterministic view over returned candidates. It MUST expose the ordering tuple and
all unknowns. The default precedence is:

1. hard identity/safety/legal/equipment blockers;
2. readiness/evidence tier;
3. assessed constraint fit;
4. material feasibility and inventory quantity;
5. Pareto cost vector;
6. thermodynamic/selectivity/kinetic diagnostics only where context-matched;
7. route complexity and presentation tiebreakers.

A candidate with missing evidence MUST NOT outrank a sourced candidate merely because missing
data were treated as zero cost or neutral risk. Conversely, `UNKNOWN` is not automatically
negative evidence; the ordering must state its policy.

If the search is incomplete, the renderer says “top returned candidate,” not “optimal route.”

## 16. Conformance and acceptance gates

The following are release gates for `0.5.0a1`.

### G0 — Baseline and version

- full non-optional suite passes;
- package, CLI, JSON schema and artifact all report `0.5.0a1` consistently;
- main `smartchem` script and `python -m smartchem` agree.

### G1 — Identity

- names, SMILES, InChI and formula inputs have explicit paths and echoed normalization;
- same-formula isomers remain structurally distinct;
- stereo/isotope/charge/component losses refuse or emit a tested loss record;
- salts/mixtures are not forged as connected neutral molecules.

### G2 — Search receipt

- every zero/nonzero route and DAG result has a receipt;
- low cut/depth/result caps produce an incomplete status;
- only a complete empty search produces `NO_ROUTE_IN_DECLARED_SPACE`;
- inventory order does not change semantic digest or result set.

### G3 — Terminal policy

- a target supplied as an exact terminal is not decomposed;
- disabling commodities prevents every commodity shortcut;
- structure search never terminates on formula-only isomer equality.

### G4 — Direction and evidence

- decomposition-only conditions do not attach to reversed assembly;
- a same-formula isomer does not borrow conditions/selectivity;
- arbitrary free-text provenance cannot earn `KNOWN`;
- unsupported evidence records fail construction;
- provider conflicts are visible and deterministic.

### G5 — Stoichiometric invariance and route topology

- `R` and `nR` have identical intensive classification/ranking for positive integer `n`;
- table lookups are scale invariant;
- spectators do not connect route steps;
- DAG fan-out cannot mint material quantity.

### G6 — Material and affordability honesty

- identity-only inventory yields no invented amount, ceiling, or price;
- commodity matches carry the material-equivalence warning;
- shopping lists contain external leaves only;
- mixture suitability depends on assay/formulation or explicit preprocessing;
- unknown costs remain unknown and hard blockers dominate cost.

### G7 — Dossier readiness and safety

- current sparse output renders as route dossier, not runnable/full procedure;
- missing procedure fields are listed and prevent `BENCH_DRAFT`;
- open flame is not auto-recommended; known flammability vetoes it;
- missing hazards cannot produce a safety clearance;
- `PROCEED_UNATTENDED` and equivalent labels are absent.

### G8 — CLI/service unity

- canonical and legacy aliases serialize equal request objects under equal flags;
- no verb reaches the network by default: the default provider is the offline, reproducible
  seed/cache, and a live fetch is an explicit, snapshot-stamped opt-in;
- no-route, partial, refusal, invalid input and internal error use the specified codes;
- bad numeric and chemical inputs yield concise domain diagnostics without tracebacks;
- human and JSON views agree on identity, receipt, tier, blockers, and route IDs.

## 17. Verdict-changing falsification matrix

| Claimed property | Probe | Required result |
|---|---|---|
| Complete search | Lower cut budget below known fixture requirement | `INCOMPLETE_*`, never complete/no-route. |
| Directional conditions | Reverse a sourced hydrolysis edge | Formal reverse has unknown assembly conditions unless separately sourced. |
| Structural evidence identity | Substitute a same-formula isomer | No exact condition/selectivity match. |
| Primitive invariance | Multiply every coefficient by 6 and 100 | Same intensive verdict and lookup result. |
| Real terminal inventory | Put target in active exact terminal policy | Zero expansion below target. |
| No invented feed | Supply identities but no amounts | No finite ceiling/yield/cost. |
| Linear continuity | Put previous product equally on both sides of next step | Route rejected as disconnected. |
| DAG material accounting | Consume one produced intermediate twice | Quantity deficit or blocked quantitative result. |
| Identity preservation | Round-trip stereo/isotope/charged/disconnected input | Distinct identity or explicit refusal/loss. |
| Commodity honesty | Use vinegar for pure acetic-acid requirement | Material check fails or explicit preprocessing is inserted. |
| Readiness tier | Remove addition order or quench from nominal bench draft | Tier falls below `BENCH_DRAFT` or construction fails. |
| Safety honesty | Remove hazard record from a hot/pressurized operation | Unknown/blocker, never cleared/safe. |
| CLI unity | Run canonical and legacy aliases with same flags | Equal request digest, result IDs and exit semantics. |

## 18. Migration from 0.4.0

The alpha may preserve source compatibility where it does not preserve a false claim.

- Existing formula decompiler APIs may return their old graph as `response.graph`, but MUST add
  the receipt and claim tier.
- Existing `enumerate_routes` / `enumerate_dags` may remain convenience wrappers only if the new
  result-bearing API is primary and wrappers cannot be mistaken for completion-certified calls.
- Existing `compile` and `synthesize` commands become aliases of `recompile` with no divergent
  defaults (offline provider, full depth, commodity terminals on); `synthesize`'s distinctive
  download-and-go behavior is an explicit `--network` opt-in, not a divergent default.
- Existing condition records need explicit direction and structural key migration; ambiguous
  formula records are downgraded.
- Current drafts become `RouteDossier`; `DraftedProcedure` MAY remain a deprecated type alias but
  MUST render the lower readiness truth.
- Commodity records migrate into source leads; typed `StockMaterial` is required for quantitative
  inventory claims.
- Existing result digests receive a schema/version boundary rather than silently changing meaning.

## 19. Release declaration

`0.5.0a1` is ready only when its release notes can truthfully say:

> SmartChem enumerates and ranks conservation-valid chemical route candidates within a declared,
> receipt-bearing search space. It preserves or explicitly reports chemical identity loss,
> treats evidence as direction- and context-specific, accepts real terminal/material constraints,
> and emits evidence-graded route dossiers with unresolved operations visible. It does not claim
> arbitrary chemical completeness, successful synthesis, or unaided bench readiness.

That statement is the standard's compact acceptance test. Any public path that contradicts it
blocks the release.
