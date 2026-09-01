# SmartChem chemical decompiler and synthesis recompiler audit

**Audit date:** 2026-09-01  
**Repository:** `femboy2112/SmartChem`  
**Audited upstream:** `main` at `b5faf7da460377e37f3a6ab70cdcbe542d88b666`  
**Audit branch:** `codex/chemical-compiler-standard-2026-09-01`  
**Declared package version at the audited base:** `0.4.0`  
**Package version on the reconciled audit branch:** `0.5.0a1`  
**Proposed next contract:** `0.5.0a1`; see `CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md`  
**Uptake ledger:** `UPTAKE_MANIFEST_v0.5.0a1.md`

## 1. Executive verdict

SmartChem has a real and unusually disciplined kernel: exact conservation types, immutable
reaction objects, bounded formula and structure search, explicit evidence statuses, route
classification, and a growing collection of chemistry-facing reports. Those are credible
compiler ingredients. The repository is already more honest than a typical reaction-string
generator because it has types with which to say “formal only,” “unknown,” and “refused.”

The current chemical feature is nevertheless **not yet one decompiler/recompiler pair**, and
its rendered “procedure” is **not yet a bench procedure**. It is two only partly connected
systems:

1. a formula-level decomposition hypergraph that conserves atom counts and can descend to
   elemental buckets; and
2. a structure-level, capped-scission retrosynthesis enumerator that reverses selected bond
   cuts, ranks the resulting routes, and decorates them with sparse evidence.

The first discards topology. The second does not consume the first system's decomposition
graph and cannot generally reconstruct a target from elemental buckets. As a concrete
falsifier, the route compiler does not find a synthesis of water from hydrogen/oxygen or from
bare H/O buckets: no matching structural scission exists. Conversely, structure inputs such
as ethanol and dimethyl ether collapse to the same formula graph in formula mode. Calling the
systems inverses overstates what the implementation proves.

There are also several claim-integrity defects at the audit base:

- a search cut off by the scission budget or route cap can be returned exactly like a complete
  search, so “no route” can mean “the search stopped before finding one”;
- decomposition conditions were attached to reversed assembly steps, including hydrolysis
  conditions copied onto the reverse condensation;
- condition lookup lacked an exact structural gate after its formula index, so isomers could
  borrow evidence;
- an inventory supplied to the formula CLI is displayed as terminal stock but is still
  decomposed;
- the experimental poor-man CLI invents one mole of every named item and can fail its ceiling
  calculation after printing part of a report;
- coefficients that merely rescale an equation can change thermodynamic class, equilibrium
  estimate, kinetics/selectivity lookup, and therefore ranking;
- the current draft omits operational fields a chemist needs: scale, assay, stoichiometric
  amounts, addition order/rate, agitation, endpoint, quench, workup, purification, analytical
  acceptance criteria, waste routing, and equipment ratings;
- poor-man buckets identify a pure molecule, while their cited retail sources are often
  mixtures with variable concentration, additives, phase, grade, and jurisdiction-dependent
  availability.

The appropriate verdict is therefore:

> **SmartChem currently produces bounded, conservation-valid candidate route dossiers. It
> does not yet produce a completeness-certified decomposition of arbitrary chemicals, a
> physically validated optimum synthesis, or instructions ready for unaided bench execution.**

That is not a dismissal. It is a tractable boundary. The proposed `0.5.0a1` standard makes
that boundary machine-readable and defines the shortest path to a chemist-editable output
without manufacturing confidence.

## 2. Audit method and truth vocabulary

The audit combined source inspection, full and targeted test execution, adversarial input
probes, and independent reviews of the decompiler, route compiler, CLI, affordability layer,
safety layer, and provenance model. Important claims were reproduced against the code rather
than accepted from comments.

At the audited base, after installing the declared development dependencies:

- the chemistry-focused slice completed with **236 passed**;
- the full suite completed with **2449 passed, 51 skipped, 1 expected failure**;
- the optional/slow skips were chiefly PySCF or explicitly slow paths.

After the audit-branch corrections described below, the targeted chemistry/CLI/safety suite
completed with **405 passed in 144.24 seconds**. After the final provenance, terminal-target,
diagnostic, and exit-status falsifiers were added, the full post-change suite completed with
**2510 passed, 51 skipped, 1 expected failure in 205.04 seconds**. These are the verification
bases for branch-status claims in this document; they do not prove semantic properties the tests
do not ask about.

A green baseline is evidence that the present contract is internally stable. It is not
evidence that an absent assertion is true. Several defects below are semantic holes that the
suite did not ask about.

This report uses the following labels:

| Label | Meaning |
|---|---|
| **ENFORCED** | Construction or validation makes a violation fail. |
| **MEASURED** | Observed on a named finite test/probe domain. It is not a universal theorem. |
| **DERIVED** | Calculated from stated inputs and a stated model; validity is limited by that model. |
| **SOURCED** | Attached to an exact identity, direction, context, and inspectable source. |
| **ASSUMED** | User or program supplied; useful for exploration but not independent evidence. |
| **UNKNOWN** | The system lacks the information needed for the claim. |
| **INCOMPLETE** | A bounded search stopped before its declared space was exhausted. |
| **REFUSED** | The system intentionally emits no answer across a validity boundary. |
| **NOT IMPLEMENTED** | No model or operation exists, even if a nearby type or label does. |

“Falsifier” below means a test or observation that would overturn a claimed property. A
recommendation without a falsifier is a preference; a compiler standard needs verdict-changing
tests.

## 3. What exists today

### 3.1 Formula decomposition

`smartchem.decompiler` represents a formula as an atom multiset and enumerates primitive,
conserving descending hyperedges over a declared inventory. The output is an AND–OR graph:
each compound is an OR node and each decomposition is an AND hyperedge whose entire product
multiset is required. Strict descent prevents cycles. Conservation is checked exactly.

This layer proves useful formal facts:

- every emitted edge balances the supported elemental inventory exactly;
- admitted edges strictly decrease the declared complexity measure;
- the graph is finite under the declared inventory and bounds;
- elemental leaves represent atom-count buckets, not a claim about molecular standard state;
- isomers are intentionally indistinguishable because the value is a formula, not a structure.

It does **not** prove that an edge is thermodynamically favorable, kinetically reachable,
mechanistically meaningful, selective, safe, or observed. Its condition-aware decoration does
not change this formal base.

### 3.2 Structure descent and route enumeration

`smartchem.structure_descent` produces capped structural scissions of a `Molecule` using
declared cutting reagents. `smartchem.experiment.routes` reads those scissions backwards as
assembly candidates. The linear enumerator recurses only when at most one precursor is missing;
the DAG enumerator attempts convergent branches.

This layer preserves more identity than formula decomposition and refuses some unsupported
structures. It still represents a small transform language: bond cuts plus cap reagents are not
an arbitrary reaction template corpus or a mechanism engine. A balanced reversed cut is a
formal candidate, not evidence that the reverse reaction occurs.

### 3.3 Ranking, classification, and drafting

The experimental stack evaluates candidate steps through composability, declared condition
envelopes, thermochemistry where data exist, equilibrium and kinetics approximations,
selectivity tables, equipment heuristics, hazards, and a conservation ceiling. It ranks and
renders the leading route and alternative equations.

This is valuable as an evidence worksheet. At the audited base, phrases such as “runnable,”
“full detail,” and procedure-like formatting made a sparse, hypothesized route look operationally
mature. The audit branch now renders a `FORMAL_CANDIDATE` route evidence dossier and names its
missing operation groups. A chemist-editable dossier still requires every missing operation and
material assumption to remain visible; unknowns cannot be left implicit in prose.

### 3.4 Front doors at the audited base and on the branch

There are overlapping command paths. `compile` and the experimental `synthesize` command have
different defaults, different constraint surfaces, and different failure behavior. At the
audited base, the package declared only the `smartchem-verify-probes` console script, exposed no
package `__version__`, and had no main CLI `--version` contract. The branch now installs the
`smartchem` script and reports `0.5.0a1`; the command paths are still not one typed service.

This fragmentation is more than cosmetic. It means two users can ask the apparent same question
and search different spaces. A compiler front door must serialize the request and defaults so a
result is reproducible.

## 4. What is already strong

The audit should not erase the useful work already present.

| Capability | Current truth | Boundary |
|---|---|---|
| Exact atom/charge balance in core reaction types | **ENFORCED** | Balance does not imply realizability. |
| Formula descent termination | **ENFORCED** for admitted edges | Completeness still depends on inventory and budget. |
| Structural identity for route inventory termination | **ENFORCED** in route search | Exact represented structures now gate assembly conditions; broader stereo/isotope/charge/material identity remains. |
| Immutable, digestible intermediate values | Broadly **ENFORCED** | Some digests include presentation/order or omit evidence semantics. |
| Evidence-status vocabulary | Implemented | Free-text conditions remain declared constraints, not sourced values; selectivity promotion requires a typed DOI/URL locator. General context/conflict governance remains. |
| Unknown condition envelope | Implemented | Rendering must keep unknowns from reading as clearance. |
| Commodity catalogue and source leads | Implemented | It is not yet a material inventory or price database. |
| Constraint-box concept | Implemented | Numeric validation is now strict; “unconstrained” fit semantics still need strengthening. |
| Conservation ceiling | Useful as a theoretical upper bound | Requires explicit feed quantities and is not an expected yield. |
| Independent safety/equipment layer | Useful architecture | Current heuristics are too sparse for operational safety claims. |
| Regression evidence | Healthy audited base; post-change full suite: 2510 passed, 51 skipped, 1 expected failure | Semantic omissions still require adversarial tests. |

The repo's best design instinct is its insistence that exact mathematics, physical models,
empirical evidence, and operator assumptions remain different things. The `0.5.0a1` work should
make those separations visible at every public boundary.

## 5. Priority-zero findings

These issues can turn an incomplete or purely formal result into a plausible physical claim.

### P0-1 — Search completeness was discarded; linear search now carries a receipt

`capped_scissions` returns `(edges, complete)`. Both linear and DAG route enumeration ignore the
`complete` flag. Route and DAG result caps also stop enumeration without a receipt. Empty and
non-empty tuples therefore carry no information about how much of the declared space was
searched.

The preceding paragraph describes the audited base. On the audit branch, the new
`search_routes` API returns a `RouteSearchResult` plus `RouteSearchReceipt` for **linear** route
search. It preserves incomplete scission expansions, reports the per-expansion cut budget,
detects unique-result-limit saturation, and distinguishes complete-within-bounds from partial
results in the human no-route path. The legacy `enumerate_routes` tuple wrapper remains for
compatibility and deliberately carries no receipt. Formula decomposition and `enumerate_dags`
still lack the same receipt-bearing public contract, and no stable JSON response unifies these
paths. This P0 is therefore **partially corrected, not closed**.

Measured probe for acetic anhydride plus water:

| Cut budget | Scissions | Cut complete | Routes | DAGs |
|---:|---:|:---:|---:|---:|
| 1 | 0 | no | 0 | 0 |
| 2 | 1 | no | 0 | 0 |
| 5 | 3 | no | 0 | 0 |
| 20,000 | 16 | yes | 1 | 1 |

An ethyl-acetate probe returned one, two, then three routes as `max_routes` rose from one to five,
but no returned value said that the earlier sets were cap-limited.

**Consequence:** “no route found” can be a false negative, and “all routes” can be a silent
sample. Ranking a sampled set is not the same operation as finding the best route in the
declared space.

**Required correction:** every search returns results plus a `SearchReceipt` naming inventory,
transform set, depth, cut budget, candidate/result caps, visited counts, rejection counts,
completion flags, and stop reason. `NO_ROUTE` is permitted only with a complete receipt;
otherwise the result is `INCOMPLETE_NO_ROUTE_OBSERVED`.

**Falsifier:** set the cut budget below the measured required value. Any human or JSON output
that says only “no route,” or a complete/certified result, fails the standard.

### P0-2 — Evidence direction and structural identity were laundered through reversal

The route enumerator obtains a decomposition scission and reverses it to make an assembly step.
At the audited base, it looked up conditions for the decomposition equation before reversal and
attached them to the assembly. Hydrolysis conditions such as aqueous acidic medium were thereby
presented as conditions for the reverse condensation.

**Audit-branch correction:** condition records now declare `DECOMPOSITION` and/or `ASSEMBLY`;
route generation requests assembly evidence, and that assembly lookup requires exact canonical
reactant/product structures after a primitive formula-stoichiometric candidate index. The
formula index is not itself accepted as evidence. The paracetamol/O-acetyl same-formula-isomer
regression now remains undeclared for the isomer. Temperature and pressure envelopes also
require explicit K and atm units, respectively. These paths passed the targeted branch suite.

**Residual boundary:** the exact assembly key is a strong correction for the represented neutral
structures, but the general evidence model still needs first-class stereo, isotope, local-charge,
phase/standard-state, participant-role, condition-domain, and source/conflict fields. Formula-only
decomposition hints must remain below structure-specific sourced evidence.

**Required correction:** a sourced condition key must contain canonical reactant/product
structures (including local charge, stereo and isotope state when present), primitive
stoichiometry, direction, role/context, and source. Formula fallback may yield an ambiguous
formal hint only; it must never yield `SOURCED` or `KNOWN` for a structural route.

**Falsifier:** replace the intended product with a same-formula isomer. Any retained exact
condition/selectivity attestation is a failure.

### P0-3 — The decompiler and recompiler are not inverse views of one IR

Formula decomposition discards connectivity. Structural route search uses capped bond
scissions and never imports the formula graph as a proof object. The two sides use different
identities, terminal semantics, candidate generators, and completeness behavior.

**Consequence:** the advertised loop “arbitrary chemical → all routes to buckets → choose the
best route back” does not exist as a single typed calculation. This is also why elemental mode
can short-circuit or fail in surprising ways.

**Required correction:** define a shared `ChemicalCompilationIR` whose candidate transform
records preserve both formula conservation and the strongest available structure identity.
Decompiler output must be a consumable input to the recompiler, with explicit loss markers when
structure is forgotten. Alternatively, name the current operations distinctly: formula
decomposition and structural capped-scission route search.

**Falsifiers:** (a) ask the compiler to reconstruct water from permitted H/O or H2/O2 terminals;
(b) compare the formula decompilations of `CCO` and `COC`. If the product claims one arbitrary
inverse semantics for both probes, the claim is false.

### P0-4 — CLI inventory did not implement terminal semantics

At the audited base, the formula decompile CLI described and rendered supplied inventory molecules as terminal
buckets, but the graph builder still expands them; only elements actually terminate. A probe
equivalent to `decompile CO2 --inventory CO2` emits the decomposition `CO2 -> C + 2 O`.

**Consequence:** the displayed request and executed search differ. Reproducibility and
affordability claims both fail if a user cannot say what is already on hand.

**Audit-branch correction:** formula inventory entries now terminate matching formula nodes,
and inventory inputs are canonicalized and deduplicated so order/duplication does not change the
graph meaning. Target-as-terminal and permutation regressions passed the targeted suite.

**Residual boundary:** this is formula inventory semantics, not yet one typed `TerminalPolicy`
shared with structural routes and `StockMaterial` inventories. Element packaging and exact
structure/material match modes remain separate design work.

**Required correction:** replace ad hoc inventory tuples with a `TerminalPolicy` containing
exact identities and explicit match mode. The search must either stop at a matching node or
state why that identity cannot be represented at the current layer.

**Falsifier:** include the target itself as an exact terminal. Any emitted child edge for that
node fails the policy.

### P0-5 — Poor-man synthesis invented feed quantities

At the audited base, the experimental CLI converted every `--have` and `--reagent` molecule into an implicit one-mole
feed. This is not a parsing convenience: it is a physical assertion that drives the conservation
ceiling. It can also omit the commodity leaf and raise a `CeilingError` after partial output.

Measured example: a poor-man offline synthesis request for `CCO` at depth one printed partial
route information and then crashed in the ceiling calculation.

**Audit-branch correction:** identity-only `--have` and `--reagent` arguments no longer create an
implicit one-mole feed. The CLI drafts the route dossier without a quantitative ceiling when no
amounts were supplied, avoiding the prior partial-output `CeilingError`. The regression passed in
the targeted branch suite.

**Residual boundary:** typed amount/assay CLI inputs, symbolic limiting-reagent output, and
quantity-aware `StockMaterial`/DAG flow are still TODO.

**Required correction:** never calculate a quantitative ceiling unless the user supplied typed
amounts and assays. With identities only, return `QUANTITY_UNKNOWN`, list the symbolic limiting
reagent relationship if derivable, and keep the rest of the dossier usable.

**Falsifier:** provide only identity flags. Any finite mole or mass ceiling is invented.

### P0-6 — Stoichiometric rescaling changed the physical verdict

At the audited base, equivalent equations with all coefficients multiplied by a common factor were treated as
different physical extents. Thermochemical totals, `log K`, equilibrium extent labels, and
some table keys change with that spelling. A reproduced probe changed a route from borderline/
balanced to favorable and then essentially complete when the same equation was multiplied by
six and one hundred.

**Consequence:** rendering choices can alter ranking and evidence lookup.

**Audit-branch correction:** a primitive coefficient vector now feeds feasibility, equilibrium,
and kinetics calculations; selectivity lookup is also scale-normalized. Scaling regressions pass
for these paths in the targeted branch suite.

**Residual boundary:** the primitive form still needs to be the single public reaction/evidence
identity across every provider, digest, serializer, DAG calculation, and future quantitative
extent API. Only explicitly extensive totals may scale with a declared extent.

**Required correction:** every reaction evidence key and per-reaction physical calculation must
use a primitive signed stoichiometric vector. Extensive totals may be reported for an explicitly
declared extent only. Selectivity and kinetics keys must be scale invariant too.

**Falsifier:** for every positive integer `n`, classification and intensive route ranking for
`R` and `nR` must agree. Only explicitly extensive totals may scale by `n`.

### P0-7 — Route continuity accepted a spectator as consumption

At the audited base, linear route continuity required the previous target to occur on the next step's left side. It
did not require a positive net consumption. A species could therefore appear unchanged on both
sides and falsely connect two unrelated steps.

**Audit-branch correction:** route continuity now requires strictly positive net consumption of
the prior target. The equal-spectator counterexample is rejected and passed the targeted suite.

**Required correction:** continuity requires a strictly positive net reactant coefficient for
the prior target, using exact identity and primitive stoichiometry. Catalysts/spectators need
separate roles and must not establish a data dependency.

**Falsifier:** place the previous target on both sides of the next step with equal coefficients.
The route must be rejected as disconnected.

### P0-8 — Arbitrary declarations could earn a high evidence grade

An arbitrary `ConditionEnvelope(provenance="because I said so")` could promote a reaction to
`KNOWN`. A `SelectivityRecord` with status `UNSUPPORTED` could also be admitted and used in that
promotion path.

**Audit-branch correction:** a declared envelope is now context, not proof. Conditions distinguish
operator-declared provenance from an accepted typed `SourceCitation`; accounting and equipment no longer
launder free text or `STRUCTURAL_TOY` values into `KNOWN_SOURCED`. `KNOWN` selectivity requires a
direction-specific record with a reviewable DOI/URL locator. Unsupported or structural-toy
selectivity records are rejected, and the unsupported acetic-acid condensation seed was removed.
The arbitrary-provenance, toy-accounting, and unsupported-record regressions pass. Broader
source-context and provider-conflict governance remains open.

**Falsifier:** user-authored prose, without an accepted source record, must never increase the
route's evidence grade.

### P0-9 — Procedure-like output is missing the procedure IR

The current draft can include a balanced equation, broad condition envelope, derived quantities,
equipment heuristics, and warnings. It does not require:

- target scale and material assays;
- exact charged quantities and stoichiometric excesses;
- vessel size/material/pressure and temperature rating;
- atmosphere, drying and containment assumptions;
- order and rate of addition, agitation and heat-transfer controls;
- endpoint or hold-time basis;
- quench sequence and contingency;
- phase separation, extraction, washing and drying operations;
- purification method and bounds;
- analytical identity/purity/yield acceptance criteria;
- waste streams, incompatibilities, and disposal route;
- emergency stop conditions and scale-up exclusions.

**Consequence:** prose can be mistaken for a directly executable protocol even while essential
operations are unknown.

**Audit-branch correction:** the renderer now calls this artifact a `ROUTE EVIDENCE DOSSIER`,
assigns `FORMAL_CANDIDATE`, says it is not bench-ready, and lists the missing operational groups
before the route steps. Current code cannot promote this aggregate beyond formal candidate.

**Residual boundary:** there is still no typed `ProcedureIR`, material/scale completeness proof,
or qualified-review record with which to earn `BENCH_DRAFT`.

**Required correction:** rename current output to a route dossier and introduce typed readiness
tiers. The renderer must print a checklist of unresolved fields before any step narrative.
`BENCH_DRAFT` is available only when every required operational/material field is present and
each hazard-sensitive claim has qualified review. SmartChem must not emit “safe,” “guaranteed,”
or “proceed unattended.”

**Falsifier:** remove any required field from a nominal bench draft. Construction must fail or
readiness must fall below `BENCH_DRAFT`.

### P0-10 — Chemical identity boundaries are silently erased

The current model does not safely preserve arbitrary stereochemistry, isotopes, local formal
charge/resonance, disconnected ionic components, coordination, polymorph/phase, or mixtures.
Examples include disconnected salts being refused while connected covalent-looking salt graphs
can collapse to a misleading neutral structure.

**Audit-branch correction:** structural scission now preserves rooted open-valence identity,
refuses non-neutral structural scission rather than pretending charge support, and deduplicates
duplicate reagent types before search. These are tested narrowing/refusal improvements, not a
general salt, isotope, stereo, phase, or mixture model.

This is not solved by selecting one identifier string. Standard InChI has explicit
normalization/representation boundaries, and mixtures are outside a single InChI; see the
[InChI technical paper](https://link.springer.com/article/10.1186/s13321-015-0068-4) and
[technical FAQ](https://www.inchi-trust.org/technical-faq/). SmartChem needs typed identity and
material layers around such identifiers.

**Required correction:** distinguish `MoleculeIdentity`, `FormulaUnit`, and `StockMaterial`.
Refuse or downgrade when parsing loses a represented identity feature. Never silently remove a
SMILES stereo/isotope/charge marker and then call the result exact.

**Falsifier:** round-trip a chiral, isotopically labeled, charged/disconnected input. Any digest
collision with its unlabeled/neutral/connected analogue without a loud loss record fails.

## 6. Safety audit

### 6.1 What changed on the audit branch

Two unsafe equipment heuristics were tightened:

- high-temperature steps now request a controlled electric heater/furnace and explicitly leave
  open-flame compatibility unassessed, instead of automatically recommending a Bunsen burner;
- a positive flammability hazard vetoes open flame independently of medium spelling;
- benign records such as water no longer cause a fume-hood recommendation merely because a
  hazard record exists; positive GHS codes drive that containment path.

These are narrow correctness fixes, not a safety model.

### 6.2 Remaining safety boundary

The hazard registry is sparse. At audit time, seven of fifteen commodity entries lacked hazard
coverage and thirteen lacked stability coverage, including important corrosive/oxidizing
materials. Free-text aliases and a few GHS flags cannot establish process safety. The current
model does not combine concentration, quantity, temperature, pressure, addition rate, solvent,
incompatibilities, off-gas, runaway potential, relief capacity, exposure route, legal control,
or waste chemistry.

That wider operational scope is consistent with the US
[OSHA Laboratory Standard](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1450)
and its [Appendix A laboratory-safety guidance](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1450AppA),
which are cited as an authoritative example rather than assumed to govern every jurisdiction.

`PROCEED_UNATTENDED` is therefore an unearned action label. The audit branch no longer emits it;
the enum member remains only for compatibility. The strongest automatic statement supported by
the present data is narrower: `NO_LOADED_TRIGGER_IDENTIFIED`. Absence of a loaded trigger is not
evidence of safety.

The proposed readiness tiers are:

| Tier | Meaning | Operational permission |
|---|---|---|
| `FORMAL_CANDIDATE` | Balanced candidate with explicit identity/search boundaries. | None. Do not execute from this output. |
| `LITERATURE_SUPPORTED` | Exact-direction evidence exists for the represented identities and context. | Still a route dossier, not a bench procedure. |
| `BENCH_DRAFT` | Required operational/material fields are complete and reviewed; unresolved items are zero. | Qualified chemist review is still required before execution. |
| `BLOCKED` | A contradiction, missing safety-critical field, unsupported identity, or violated constraint blocks the route. | Do not execute. |

No current automatic path earns `BENCH_DRAFT` merely from a balanced equation and a condition
envelope.

## 7. Affordability and poor-man buckets

Lowering the cost of participation in chemistry is a valid design goal, but affordability must
not be implemented as synonym replacement: “ethanol occurs in spirits” is not the material
claim “this bottle is a suitable ethanol feedstock.” Vinegar, bleach, spirits, sanitizer, fuels,
fertilizers, cleaners, and pool products are mixtures with variable assay and formulation.

At the audited base, a `CommodityReagent` is mainly a molecule plus a common-source description
and editorial availability label. It lacks quantity, concentration, formulation, phase, grade,
price, region, date, supplier/source provenance, contaminant profile, and purification burden.
Cost is not part of route ranking.

The audit branch now states that commodity matches are identity-level source leads, not pure
reagent equivalence. It also fixes shopping-list logic so a commodity made by an earlier route
step is not listed as an external purchase, and it prevents a globally known commodity from
short-circuiting compilation when the caller explicitly disables the commodity inventory.

The stronger model is a `StockMaterial`:

| Field group | Minimum fields |
|---|---|
| Identity | material name, components, canonical molecular/formula-unit identities, phase |
| Assay | concentration or mass fraction interval, active-equivalent definition, uncertainty |
| Formulation | stabilizers, denaturants, counterions, water, known additives/contaminants |
| Inventory | amount, unit, container, age/opened state, storage condition |
| Access | region/jurisdiction, source type, availability evidence, date checked |
| Cost | currency, package price, usable amount, purification/testing/disposal estimates, provenance |
| Fitness | required purity/assay, incompatibilities, required preprocessing, acceptance test |

Poor-man mode should optimize a **cost vector**, not a single cheapness score. At minimum it
should report cash outlay, new equipment burden, time/labor, energy, purification burden,
analytical burden, waste burden, supply confidence, and evidence/readiness. Pareto-front output
keeps a nominally cheap but hazardous or analytically expensive route from hiding a more robust
alternative.

Honest encouragement looks like this:

- prefer accessible materials when fitness is demonstrated;
- show substitutions and preprocessing as explicit operations;
- expose uncertainty and the measurement that would resolve it;
- never infer concentration or one-mole availability from a product name;
- never rank price above a safety or identity blocker;
- distinguish source leads from procurement recommendations and legal availability.

## 8. CLI and service audit

### 8.1 Current inconsistency

At the audited base, the main `compile` path and experimental `synthesize` path did not share one
typed request. Among the observed differences:

- different default commodity policies and search depths;
- constraints and provider autoloading available in only one path;
- different handling of no-route and invalid-input outcomes;
- name inputs are not accepted consistently (`compile acetic anhydride` fails as an unparsed
  structure string despite an offline name registry);
- `--elements` could still trigger a global commodity short-circuit at the audited base and its
  name falsely implied automatic elemental terminals in structural search;
- invalid numeric and structure input can surface implementation exceptions;
- no main `smartchem` console script or `--version` contract existed.

The audit branch now accepts registered offline names plus explicit `name:`/`smiles:` prefixes in
the synthesis CLIs, installs the `smartchem` entry point, reports `0.5.0a1` through `--version`,
validates positive search bounds, and implements codes 0/2/3/4 for complete success, invalid input,
complete no-route, and partial search in the synthesis front doors. `H0` and charged-structure
requests produce concise domain errors. The misleading option is now `--no-commodities`, with
`--elements` retained only as an explicitly described legacy alias that does not add element
terminals. The branch still lacks one typed request, canonical `recompile`, InChI/formula/
structured-target parity, stable JSON, refusal/internal codes 5/70, and equal defaults across aliases.

### 8.2 Required front door

`0.5.0a1` should have one `CompilationRequest` service and two canonical user verbs:

- `smartchem decompile`: enumerate transformations from target toward a declared terminal policy;
- `smartchem recompile`: rank candidate routes from a decompile artifact or perform the same
  bounded search with explicit buckets and constraints.

`compile` and `synthesize` may remain documented aliases during migration, but they must produce
the same request object and defaults. Inputs should accept explicit `--name`, `--smiles`,
`--inchi`, `--formula`, and structured files; a conservative auto mode may resolve an unambiguous
name or prefixed value and must echo the chosen interpretation. Users should not be forced to
learn a private delimiter grammar.

Every output mode—human, JSON, or future table—must contain:

- tool/schema version and request digest;
- normalized identity plus any information-loss record;
- terminal/material policy;
- transform/evidence-provider versions;
- search receipt and completion state;
- candidate readiness and evidence tier;
- all constraints and default origins;
- unresolved fields and blockers;
- stable route IDs independent of display labels.

Exit status must distinguish success with complete results, success with incomplete results,
complete no-route, invalid input, and internal error. The proposed exact contract is in the
standard document.

## 9. Additional high-priority findings

The following are not all release-blocking for an alpha, but each needs a named truth state.

| Finding | Present consequence | Required direction |
|---|---|---|
| Formula parser validated against a legacy 29-element table despite a 118-element data source | At the base, common formulas such as CaO could be refused. The branch now uses the complete table and requires strictly positive integer counts; targeted tests pass. | Keep the one-authority and supported-element property tests as permanent gates. |
| Formula graph digest depended on inventory order | At the base, equivalent requests could get different identities. Branch formula inventory is canonicalized/deduplicated and permutation-tested. | Extend canonical request identity to the future shared structural/material request IR. |
| “Budget” was ambiguous between per-node and global scope | Displayed budget could understate total work. Linear `RouteSearchReceipt` now names its cut budget per expansion. | Carry equally explicit scope/counts into formula and DAG receipts or implement a true global counter. |
| DAG merging can duplicate/overcertify intermediates | Fan-out material requirements can be understated. | Quantity-aware dependency DAG and flow conservation. |
| Alternative routes are deduplicated by rendered equation | Same-formula isomer routes can disappear. | Deduplicate by canonical structural route ID only. |
| Thermochemical source uncertainty is discarded | Precision and ranking overstate evidence. | Carry value, uncertainty, covariance/source, phase, standard state. |
| Phase/standard state are weakly represented | ΔG comparisons can mix unlike states. | Make phase/state part of key and calculation context. |
| `K` is rendered as an “extent” too strongly | Ideal equilibrium relation can look like expected conversion. | Call it an idealized equilibrium diagnostic; require activities/model for conversion. |
| Higher-order kinetics lack enough concentration context | Half-life/rate labels can be underdetermined. | Require rate law, units, temperature and composition context. |
| Kinetics are weakly condition-sensitive | Ranking can reuse a rate outside its context. | Exact condition-domain key and refusal outside it. |
| Provider conflicts use first-wins behavior | Source order can silently decide truth. | Conflict object, source priority policy, or explicit refusal. |
| Selectivity source coverage is not exact enough | A curated path can carry an unclear attestation. | Exact citation and identity/direction/context matching. |
| Thermochemical grade is omitted from some semantic digests | Evidence-relevant changes can fail to change identity. | Include evidence semantics in artifact digest/version. |
| Constraint fields accepted semantically invalid ranges | Negative/nonfinite/inverted bounds could leak at the base. Branch constraints now require finite, positive, ordered values; targeted tests pass. | Preserve validation through the shared request, CLI error, and JSON paths. |
| `FITS` may mean no constraint was supplied | Users can read “fits” as confirmed equipment compatibility. | Distinguish `UNCONSTRAINED`, `ASSESSED_FIT`, `UNKNOWN`, `EXCLUDED`. |

Thermochemical records in particular must retain their property and condition context; the
[NIST Chemistry WebBook guide](https://webbook.nist.gov/chemistry/guide/) is a primary example
of phase-, property-, condition-, and unit-specific chemical data rather than context-free
numbers. Structured reaction-evidence work should likewise be informed by the
[Open Reaction Database schema](https://docs.open-reaction-database.org/en/latest/schema.html),
which separates reaction inputs, conditions, outcomes and workups.

## 10. Changes made during this audit

The branch contains focused honesty/safety corrections. They should be treated as work toward,
not completion of, the larger standard.

| Change | Reconciled branch state | Remaining boundary |
|---|---|---|
| Linear `search_routes` returns a receipt and human output distinguishes partial/complete no-route | Implemented and targeted-tested | Formula and DAG receipts, shared response/JSON, richer counters. |
| Direction-tagged conditions plus exact structure-keyed assembly lookup after primitive formula indexing | Implemented and targeted-tested, including same-formula isomer | General stereo/isotope/charge/phase/role/context/source evidence key. |
| Condition temperature/pressure require K/atm | Implemented and targeted-tested | Explicit conversion UX and shared request serialization. |
| Primitive coefficient vector feeds feasibility, equilibrium and kinetics; selectivity lookup is scale invariant | Implemented and targeted-tested for named paths | One global canonical reaction/evidence/digest/extent identity. |
| Route continuity requires positive net consumption | Implemented and targeted-tested | Typed catalyst/spectator roles and DAG quantity flow. |
| Formula inventory terminates matching nodes and is canonicalized/deduplicated | Implemented and targeted-tested | Shared structural/material `TerminalPolicy`. |
| Formula parser uses the complete periodic table and strictly positive integer counts/bounds | Implemented and targeted-tested | Shared parser/request diagnostics across all formats. |
| Structural scission preserves rooted open-valence identity, refuses non-neutral targets, and deduplicates reagent types | Implemented and targeted-tested | Stereo/isotope/salt/mixture/phase identity layers. |
| Identity-only CLI inventory no longer creates a one-mole feed or erroneous ceiling | Implemented and targeted-tested | Typed amounts, assays, symbolic balance and DAG flow. |
| Route renderer emits a `FORMAL_CANDIDATE` evidence dossier with missing bench operations | Implemented and targeted-tested | `ProcedureIR` and any path capable of earning `BENCH_DRAFT`. |
| High heat uses controlled electric heat; flammability vetoes open flame; benign records do not imply a hood | Implemented and targeted-tested | Quantity/concentration/process hazard model; no safety certification implied. |
| `PROCEED_UNATTENDED` is no longer emitted | Implemented and targeted-tested; enum retained for compatibility | Eventually deprecate/remove the compatibility symbol. |
| Constraints require finite, positive, ordered values | Implemented and targeted-tested | Shared request/JSON validation and `UNCONSTRAINED` fit semantics. |
| Commodity shortcut respects active inventory; output carries identity-only caveat; shopping uses external leaves | Implemented and targeted-tested for current linear path | `StockMaterial`, DAG quantities, regional cost/availability. |
| Free-text conditions stay declared constraints; selectivity promotion requires DOI/URL; unsupported/toy records are rejected | Implemented and full-suite tested | Exact general source/context/conflict governance. |
| Exact active-stock target stops before expansion and renders an identity/quantity caveat | Implemented and full-suite tested | Shared material-aware terminal policy. |
| Registered names, `smartchem` entry point, `--version 0.5.0a1`, strict diagnostics, and exit codes 0/2/3/4/5 | Implemented and full-suite tested | One service, canonical `recompile`, full input formats, code 70 and JSON. |

The final branch state completed the full suite with **2510 passed, 51 skipped, 1 expected
failure in 205.04 seconds**. The uptake manifest keeps broader rows `IN_PROGRESS` when only the
linear, formula, or human-rendering slice is complete.

## 11. Proposed `0.5.0a1` acceptance boundary

The first alpha need not solve arbitrary synthetic chemistry. It must stop overstating the
bounded system it does solve. The alpha is acceptable when all of the following hold:

1. One typed request/service powers all chemical CLI aliases.
2. Every route/decomposition result includes a search receipt; incomplete search cannot render
   as complete or as a definitive no-route.
3. Exact identity and information loss are explicit; unsupported stereo/isotope/charge/
   mixture boundaries refuse or downgrade.
4. Evidence is keyed by primitive stoichiometry, structure, direction, context, and source.
5. Reaction classification/ranking is invariant under common coefficient scaling.
6. Inventory terminals actually terminate under an explicit policy.
7. Identity-only inventory never produces invented quantities or yields.
8. Current output is called a route dossier and carries readiness/unresolved-field lists.
9. Commodity matches are source leads; material fitness requires assay/formulation data.
10. “Proceed unattended,” automatic open-flame clearance, and equivalent unearned action labels
    are absent.
11. Name/SMILES/InChI/formula parsing is explicit, echoed, and tested; CLI exit statuses are
    stable and machine-readable.
12. The complete non-optional test suite is green, with adversarial tests for every gate above.

The alpha may still use a small transform/evidence registry, return many unknowns, and decline
most arbitrary targets. Honest refusal is compatible with the goal. Silent substitution,
completion claims without receipts, and procedure-ready prose without a procedure IR are not.

## 12. Dominance boundary and recommended order of work

The tempting path is to add more reaction records. That does not dominate the current blockers.
More records passing through ambiguous identity, reversed evidence, incomplete search, and
procedure-like rendering would increase the rate at which plausible falsehoods are emitted.

The highest-leverage sequence is:

1. **Truth envelope:** search receipts, exact terminal policy, direction/identity evidence keys,
   primitive stoichiometry, continuity fix, readiness tiers.
2. **One compiler service:** shared request/defaults, CLI names and explicit formats, stable JSON,
   exit statuses and versioning.
3. **Material reality:** `StockMaterial`, quantities, assay/formulation, inventory flow, cost
   vectors and affordability Pareto ranking.
4. **Procedure IR:** operational fields, hazard gates, qualified-review state, analytical and
   waste operations.
5. **Chemistry breadth:** new transforms, sourced conditions/selectivity/kinetics, provider
   conflict resolution, stronger thermodynamic and phase models.

The dominance boundary is explicit: **breadth is worth adding only after the artifact can say
what was searched, what identity was represented, why an evidence item applies, and whether the
output is merely formal or operationally complete.**

## 13. Final assessment

The project can become a useful chemical compiler precisely because it does not need to invent
new physics. Its novelty can live in composition: enumerating formal candidates, joining known
models and evidence without laundering them, optimizing under a real person's inventory and
budget, and exposing the exact experiment or measurement that would resolve an unknown.

For a chemist, the desired output is not false certainty. It is a dossier with enough structure
to edit: exact identities and amounts where known, every assumption visible, alternatives and
trade-offs preserved, and a sharp distinction between a balanced idea, a literature-supported
route, and a reviewed bench draft. The proposed standard makes that distinction the mainline
feature rather than a disclaimer at the bottom.
