# SmartChem Chemical Compiler 1.0 Program

**Status:** normative release-program proposal  
**Version:** v0.1  
**Date:** 2026-09-26  
**Baseline:** `main@9db02e549104e0abc3e0d5b6840094df8e12ee03` (PR #88 merged)  
**Scope:** the chemistry compiler, especially generic chemical input -> decomposition -> synthesis candidates -> evidence/process/capability projections.  
**Supersedes:** no historical audit, experiment, or roadmap result. This document is a release-level projection over them.

---

## 0. Why this document exists

SmartChem has accumulated substantial verified capability, but its work queue has mostly been organized as a sequence
of local scientific and architectural frontiers: a parser edge case, a chemistry family, a ranking defect, a
provenance hardening, a poor-man disposition leak, a new physical model, and so on. That mode has produced real
progress, but it has no intrinsic stopping rule.

The 1.0 program changes the unit of progress.

**1.0 is not "enough rounds". 1.0 is satisfaction of one stable end-to-end compiler contract.**

From this point, chemistry work should be evaluated primarily by which end-to-end release gate it moves and by how
much it changes the measured funnel from user input to a justified result. New reaction families remain valuable, but
they are no longer the default next move merely because they are available to build.

The release program is intentionally finite:

- **0.6.0 — Human Chemical Front Door**
- **0.7.0 — Production Chemical Algebra**
- **0.8.0 — Real Route Dossiers**
- **0.9.0 — Capability Compiler**
- **0.9.5 — Coverage / Adversarial Release Candidate**
- **1.0.0 — Stable Chemical Compiler Contract**

A version advances only when its acceptance gates are satisfied. A later scientific frontier may remain open without
blocking 1.0 if the stable contract can represent it honestly as unknown, unsupported, ambiguous, incomplete, or
outside the declared model.

---

# 1. The 1.0 product object

The chemistry compiler's primary user-facing object is:

```text
human chemical input
    -> lossless/tolerant syntax normalization
    -> composition
    -> identity resolution / explicit ambiguity
    -> structure-aware decomposition and transform search
    -> reaction-class / structural validity evidence
    -> conditions / process / thermodynamic / kinetic / selectivity evidence
    -> capability projection
         -> research/lab profile
         -> poor-man profile
         -> custom profile
    -> ranked route dossiers
    -> shopping / equipment / hazards / unknowns / provenance / receipts
```

The compiler is **total as an answering system**, not universal as a synthesis oracle.

For every admissible request, SmartChem 1.0 must return one of:

1. a typed successful result with the strongest claims the evidence supports;
2. a typed ambiguous result that names what information is missing;
3. a typed incomplete search result carrying its receipt and bounds;
4. a typed unsupported/refused result naming the model boundary;
5. a typed invalid-input result naming the syntax/identity defect;
6. an internal error only for an actual implementation failure.

"No route" is not the same thing as "no route exists". Formula identity is not structural identity. Structural validity
is not process feasibility. Process fit is not safety certification. Missing evidence is not a zero or a pass.

---

# 2. The identity law: formula -> structure is a relation, not a function

A molecular formula does not, in general, identify a unique molecular constitution. `C8H9NO2` names a composition,
not a single molecule.

Therefore 1.0 MUST NOT silently promote a bare formula to one structure.

The front door must instead expose the identity ladder:

```text
raw spelling
    -> FormulaExpr / normalized syntax
    -> Formula composition
    -> zero / one / many known structural candidates
    -> selected/established constitution, if available
    -> finer stereo/isotope/configuration identity only where actually perceived
```

A valid formula-only request may therefore terminate successfully as:

```text
FORMULA_PARSED
ELEMENTAL_DECOMPOSITION_COMPLETE
STRUCTURAL_IDENTITY_AMBIGUOUS
STRUCTURAL_SYNTHESIS_NOT_STARTED
reason: constitution required
```

That is a successful answer. Guessing a structure would be a compiler defect.

This law is load-bearing for hazards, sourcing, pricing, selectivity, process conditions, and synthesis: same-formula
isomers may differ on every one of those axes.

---

# 3. The syntax law: preserve before quotienting

The current `Formula` object is an atom-count multiset. That is the correct quotient for conservation, but it is too
early a quotient for tolerant human input.

0.6 introduces a lossless syntax object, provisionally `FormulaExpr`, before `Formula`.

Example:

```text
CuSO4·5H2O

FormulaExpr
  Component(CuSO4, 1)
  Component(H2O, 5)

composition()
  -> Cu1 H10 O9 S1
```

The component/adduct/hydrate boundary may disappear under elemental conservation while remaining relevant to
material identity, phase, formulation, preprocessing, procurement, or user display. The parser therefore preserves
the source structure and records the projection that forgets it.

The normalizer should support the practical "copy from Wikipedia" surface within an explicit grammar, including:

- ordinary ASCII formulas;
- Unicode subscript digits;
- Unicode middle-dot and accepted hydrate/adduct separators;
- leading component multipliers after a separator;
- nested round/square grouping where unambiguous;
- common charge spellings such as `SO4^2-`, `SO₄²⁻`, and bracketed ions where the grammar supports them;
- harmless whitespace;
- a normalization receipt carrying original spelling, normalized spelling, and any lossy or unsupported feature.

Parametric or polymer-like expressions such as `(C2H4)n`, `MxOy`, interval counts, or prose-contaminated strings
must be classified explicitly. They may be represented as a future parametric syntax, or refused as outside the
finite 1.0 formula grammar. They must never be coerced into a concrete formula.

---

# 4. Three different "bucket" objects

The word "bucket" currently spans different semantic layers. 1.0 should separate them.

## 4.1 ElementalCompositionBucket

A conservation object such as C, H, O, Na with multiplicity. This is mathematical bookkeeping. It answers how much
of each element the target contains and supplies the elemental floor of formula decomposition.

## 4.2 ChemicalCommodityBucket

A specific chemical identity that may terminate structural route search: water, acetic acid, sodium bicarbonate,
salicylic acid, etc. It is structure/identity keyed. Availability is an independent property.

## 4.3 MaterialBucket

A real obtainable material/formulation:

```text
MaterialBucket
    chemical identity / identities
    formulation
    concentration / assay
    phase
    grade
    package quantity
    availability/source class
    dated price observations
    preprocessing needed before use
    provenance
```

"White vinegar, 5-8% aqueous" is not interchangeable with neat acetic acid. A chemical identity may be one component
of a purchasable material. The 0.9 capability layer should make that distinction explicit rather than treating a
common-source note as an implicit pure reagent.

---

# 5. The chemistry-generation law

At the 2026-09-26 baseline the architecture has outrun the default planner configuration:

- the transform-provider seam exists and parameterizes route/DAG search;
- the rule calculus and related family machinery can express significantly richer chemistry;
- the production reaction-type oracle recognizes 17 classes;
- lateral, rank-flat chemistry has its own sound bounded search;
- but `DEFAULT_TRANSFORM_REGISTRY` still contains exactly `CappedScissionProvider()`.

So:

```text
chemistry SmartChem can recognize != chemistry its default planner can generate
```

This is the central 0.7 gap.

The 1.0 strategy is NOT "add recognizer #18, #19, #20 forever." It is to make a certified rule/provider description
the common origin of generative structure, replay/witness data, and reaction-class evidence wherever that can be
done soundly.

A production-capable rule definition should eventually carry or induce at least:

```text
RuleDefinition
    source pattern / L
    preserved interface / K
    result pattern / R
    atom transport
    charge/state transport where represented
    application guards
    reaction-class semantic identity
    declared directionality
    scope constraints
    provider/version identity
    provenance / evidence hooks
```

and compile into distinct views:

```text
                 RuleDefinition
                 /     |      \
                /      |       \
        generator    witness    replay/verifier
```

The verifier must not become a vacuous "the generator says this is valid" loop. Independent representation,
re-derivation, external/specification evidence, hostile near-misses, and mutation tests remain required according to
claim strength.

Legacy recognizers remain during migration. Delete one only after the replacement agrees on the declared corpus,
survives hostile near-misses, kills calibrated mutants, and has fresh holdouts. Disagreement is investigated, not
relabeled away.

---

# 6. Strict descent and lateral chemistry are intentionally different

The existing rank-descending route search has a well-founded atom-count measure. Rank-flat isomerization does not
satisfy that measure.

PR #88's bounded lateral search is therefore not an awkward exception. It is the correct architectural answer:
rank-flat chemistry carries its own visited-state/budget termination proof and must not be forced into a recursion
whose proof it violates.

1.0 may orchestrate strict-descent and lateral search, but MUST preserve their distinct completeness semantics. A
combined planner must expose where each subsearch was complete/incomplete and cannot launder one search's receipt
through the other.

---

# 7. Route readiness is a ladder of discharged obligations

A graph rewrite that balances is not yet a real procedure.

The 0.8 release should make route readiness machine-visible as separate obligations rather than one vague label.
A useful initial ladder is:

```text
FORMAL_CANDIDATE
    -> REACTION_VOUCHED
    -> CONDITIONS_SUPPORTED
    -> PROCESS_SPECIFIED
    -> CAPABILITY_ASSESSED
    -> CAPABILITY_FIT
```

These are NOT truth probabilities and need not be a single enum if orthogonal fields are more faithful. The rule is
that the UI/API must let a consumer distinguish at least:

- conservation/structural candidate status;
- reaction-type validity status;
- conditions/procedure evidence status;
- thermodynamic evidence;
- kinetic/selectivity evidence;
- process completeness, including workup/isolation where required;
- capability fit under the selected profile;
- remaining unknowns.

A route that is structurally real but has unknown conditions remains useful to a research chemist, but it must not be
rendered as an executable procedure. A route with sourced conditions but unresolved separation is still incomplete
as a bench plan.

---

# 8. Capability is a projection, not a second chemistry engine

Professional and poor-man chemistry should share the SAME chemistry and route objects.

Introduce one general `CapabilityProfile` carrying declared resources and constraints, for example:

- inventory / material buckets;
- budget;
- temperature range;
- pressure range;
- equipment;
- containment / ventilation;
- measurement capability;
- separation / purification capability;
- operator attention;
- time;
- waste handling;
- procurement constraints;
- any future jurisdiction/user policy declaration needed by the product.

Then:

```text
ResearchLabProfile
PoorManProfile
CustomProfile
```

are values/presets of the same semantic type.

The poor-man ethos remains:

> optimize aggressively inside reality, but do not trade away a hard chemistry, identity, containment, equipment,
> legal, verification, or other declared capability constraint merely because a route is cheap.

The existing affordability vector, disposition split, commodity inventory, catalyst obtainability, handling,
equipment, process, DAG shopping, thermodynamics, kinetics/selectivity and sourcing layers are the substrate for this
projection.

---

# 9. Poor-man 1.0 contract

"Poor man" does not mean unsafe, imaginary, or "assume the user has a lab".

It means: **find unusually accessible routes under a declared low-resource capability profile while preserving every
ordinary truth and evidence boundary.**

The default poor-man profile should model household/outdoor resources conservatively. Outdoors may satisfy a
ventilation requirement where explicitly modeled; it does not erase toxic/corrosive/flammable exposure, containment,
environmental, waste, or legality constraints.

A poor-man-fit route is a whole-path claim. It includes, where relevant:

- obtainable material identities and formulations;
- amount/assay/concentration compatibility;
- catalysts and auxiliaries;
- equipment and control range;
- process duration/operator attention;
- containment/ventilation;
- workup;
- separation/purification;
- verification/measurement;
- waste handling;
- priced or explicitly unknown material burden.

Unknowns stay unknown. A cheap reagent list is not a capability result.

---

# 10. Safety and claim boundary

SmartChem is a scientific planning/compiler project, not an authority to certify a procedure safe merely because its
stored hazard checks do not fire.

The 1.0 product must preserve the existing fail-closed philosophy:

- no missing hazard record becomes "safe";
- no favorable delta-G becomes "bench-capable";
- no known reaction type becomes "safe to perform";
- no consumer availability note becomes a purity/assay/legal guarantee;
- no procedure evidence silently transfers outside its scale, substrate, conditions, or equipment scope;
- no low-resource recommendation trades away required controls.

User-facing route dossiers should surface hazards, unknowns, required controls, and evidence scope prominently.

---

# 11. The version ladder

## 0.6.0 — Human Chemical Front Door

### Goal

A human can paste ordinary chemical formula notation, names, SMILES, supported InChI input, or a target file into one
front door and SmartChem determines the strongest identity layer it can actually perceive.

### Required capabilities

1. Add the lossless `FormulaExpr` (name negotiable after code audit) before `Formula`.
2. Implement tolerant formula normalization for the declared Wikipedia-style grammar.
3. Preserve original spelling and emit a normalization/parse receipt.
4. Extend AUTO discrimination so obvious formulas can resolve as formulas without stealing strings that are valid
   registered names or valid SMILES under the existing precedence contract.
5. Keep explicit `formula:`, `name:`, `smiles:`, `inchi:` forms authoritative.
6. Add first-class identity ambiguity/result semantics.
7. Introduce a high-level human command/API (candidate name: `plan`) OR prove that the canonical existing service
   can supply the same total-answer behavior without a new verb.
8. Create the first machine-readable 1.0 funnel harness.
9. Freeze a hostile parser corpus with Unicode, hydrates/adducts, charges, whitespace, malformed/parametric controls,
   and alias-collision controls.
10. Preserve all existing explicit-input behavior unless a migration is deliberately documented.

### Exit gate

A predeclared front-door corpus produces only expected typed outcomes; no formula is silently treated as a structure;
normalization is deterministic/idempotent; old explicit NAME/SMILES requests remain semantically stable; the whole
suite is green in the established environment; every new failure mode has a typed receipt.

---

## 0.7.0 — Production Chemical Algebra

### Goal

The default structural planner is parameterized by a certified production transform algebra rather than remaining,
in practice, a capped-scission-only engine with richer recognition living beside it.

### Required capabilities

1. Inventory every transform family: generative, recognition-only, lateral, decompile-only, opt-in research.
2. Define the production-provider admission contract.
3. Migrate a representative cross-section of already-verified families onto that contract.
4. Make provider/rule bodies content-addressed or otherwise bind their semantic version strongly enough that grammar
   identity cannot silently stay constant while rules change.
5. Derive class witnesses from actual rule applications where sound.
6. Retain independent verification/re-derivation rather than trusting arbitrary rule labels.
7. Orchestrate lateral search separately while exposing one coherent result.
8. Preserve honest aggregate completeness across providers/searches.
9. Measure coverage on the frozen 1.0 corpus.
10. Do not widen defaults with a family whose evidence/guards are weaker than the claim the default planner will make.

### Exit gate

Default `recompile/plan` demonstrably generates multiple qualitatively distinct certified chemistry families without
a search fork, route receipts bind the actual algebra configuration, legacy recognizers agree on the migration
corpus, and hostile/held-out probes show no new false-vouch path.

---

## 0.8.0 — Real Route Dossiers

### Goal

A returned route has a typed distinction between formal structural possibility and evidence-backed real synthesis.

### Required capabilities

1. Define route/step readiness obligations.
2. Attach reaction-class evidence/witness status.
3. Attach condition/procedure evidence with provenance and scope.
4. Represent missing condition evidence explicitly.
5. Represent workup/isolation/separation requirements instead of treating "reaction occurred" as "product obtained".
6. Bind all verdict-bearing evidence into replay/provenance.
7. Ensure replay/load re-derives every claim that can be re-derived.
8. Make the human render visibly distinguish formal candidates from procedure-backed candidates.
9. Add independent literature/source fixtures to a benign validation corpus.
10. Preserve research usefulness: unknown procedure evidence does not delete a structurally interesting candidate; it
    lowers/blocks the readiness claim.

### Exit gate

SmartChem can show, for a nontrivial corpus, which routes are merely formal, which are reaction-vouched, which have
sourced conditions/process support, and exactly why a stronger label is unavailable.

---

## 0.9.0 — Capability Compiler

### Goal

One route set can be projected through research, poor-man, and custom resource profiles.

### Required capabilities

1. Introduce `CapabilityProfile` and migrate existing bench/process knobs into it without semantic loss.
2. Define `PoorManProfile` as a conservative preset.
3. Introduce `MaterialBucket` / formulation-aware terminals.
4. Thread amount, concentration/assay, phase/grade where evidence and model support them.
5. Connect equipment/containment/measurement/separation/waste constraints to whole-route assessment.
6. Improve source/pricing coverage enough that the poor-man frontier has real discrimination on the release corpus.
7. Keep price observations dated and sourced; keep mixed/incommensurate units incomparable.
8. Make professional/research capability a different profile, not a bypass around unknowns.
9. Bind profile identity into the compilation request/result provenance.
10. Preserve all hard-disposition rules: no cheap route can dominate its way around a blocked capability.

### Exit gate

At least one corpus has meaningful divergence among ResearchLab, PoorMan, and custom profiles, with the same underlying
chemistry and different justified capability outcomes. Material formulations are no longer silently pure chemicals.

---

## 0.9.5 — Coverage and adversarial release candidate

### Goal

Measure genericity and failure modes before stabilizing the contract.

### Frozen funnel

Every target reports denominators independently:

```text
input received
 -> syntax represented
 -> composition resolved
 -> identity resolved / ambiguity classified
 -> structure representable
 -> transforms enumerated
 -> reaction classes vouched
 -> route reaches terminal material set
 -> conditions/procedure supported
 -> process dossier complete
 -> research capability fit
 -> poor-man capability fit
```

Zero-step purchase must remain distinct from a synthesized route.

### Required validation

- a predeclared benign target corpus spanning:
  - inorganic / organic;
  - acyclic / ring / fused/aromatic;
  - neutral / supported charge;
  - hydrate/adduct formula syntax;
  - same-formula isomers;
  - names / SMILES / formula / supported InChI;
  - commodity and non-commodity targets;
  - strict-descent and lateral chemistry;
- parser/property fuzzing;
- structure-identity differential checks;
- reaction-family hostile near-misses;
- mutation tests for the new front door / rule admission / readiness / capability layers;
- transport/tamper tests;
- fresh holdouts that were not used to build the rule;
- reproducible suite/benchmark receipts;
- a source-map review for procedure/cost/hazard claims.

### Exit gate

All release claims can be stated as measured funnel properties with exact corpus/bounds. No fitted showcase target is
used as the sole validation of the feature that was built for it.

---

## 1.0.0 — Stable Chemical Compiler

1.0 means the semantics and compatibility contract are stable enough for downstream consumers.

### Mandatory 1.0 laws

1. **Total front door.** Every admissible input reaches a typed result or typed refusal.
2. **No identity hallucination.** Formula equality never implies structural identity.
3. **No false completeness.** Every bounded search retains its receipt and bounds.
4. **No unsourced practical claim.** Formal structure is not silently promoted to a real procedure.
5. **Generation and verification are distinguishable.**
6. **Poor-man fit is whole-route fit.**
7. **Unknown is never free, safe, feasible, pure, or zero.**
8. **Every strong recommendation is replayable/provenance-bound.**
9. **Every genericity claim is measured on holdouts.**
10. **Stable semantics, incomplete chemistry.** New post-1.0 families extend coverage without changing what existing
    verdict words mean.

### Release engineering

Before tagging 1.0:

- version metadata and package docs agree;
- README capability claims match current main;
- ROADMAP points to this finite version ladder;
- stale historical comments are corrected without falsifying history;
- CI/workflow state is green or an exact external infrastructure blocker is recorded;
- supported Python versions are tested;
- installed CLI behavior is tested from a built wheel/sdist, not only editable source;
- schemas are versioned with migration notes;
- the release corpus and validation receipts are committed;
- there are no unexplained xfails;
- there is a documented compatibility/deprecation policy.

---

# 12. What is explicitly NOT a 1.0 blocker

Unless a frozen release corpus exposes a direct dependency, the following research fronts do not gate chemistry 1.0:

- generalized cross-domain PhysicalIR perfection;
- chemistry/circuit ranker unification;
- additional water-wave executors;
- port-Hamiltonian semantics;
- complete CIP coverage of every exotic recursive tie;
- universal mechanism discovery;
- universal synthesis success;
- perfect yield prediction;
- every optional quantum-chemistry backend/tier;
- forcing delta-G or equilibrium drive into a bench-capability gate without a separately validated mapping.

A 1.0 system may correctly answer UNKNOWN/DEFERRED/UNSUPPORTED on these surfaces.

---

# 13. Current baseline and debt snapshot

Baseline inspected: `9db02e549104e0abc3e0d5b6840094df8e12ee03`, merge of PR #88.

Verified architectural observations at this baseline:

- centralized identity resolution exists for NAME/SMILES/FORMULA/partial InChI/target-file;
- formula input is composition-only by design and structural recompile refuses it;
- `Formula.parse` handles ASCII element/count/group syntax and simple separators but is not yet a Wikipedia-copy/paste
  grammar;
- formula decomposition has exact conservation and completeness receipts;
- structure-preserving decompile IR exists;
- route/DAG search is parameterized by `TransformProviderRegistry`;
- `DEFAULT_TRANSFORM_REGISTRY` still contains only `CappedScissionProvider`;
- the reaction-type oracle has 17 fail-closed positive classes after PR #88;
- bounded lateral search exists separately from strict rank descent;
- poor-man infrastructure includes commodity terminals, catalyst obtainability, affordability vectors, dispositions,
  quantities, equipment/process constraints, handling/hazards, thermodynamic/kinetic/selectivity evidence and DAG
  shopping;
- material formulation/purity/assay remains under-modeled;
- many practical cost/process axes remain data-sparse;
- `pyproject.toml` still reports `0.5.0a1`;
- historical README/ROADMAP/CI prose contains some stale counters/comments after later merges;
- GitHub connector inspection at this baseline found no workflow run/status attached to the exact merge commit, so
  current hosted CI success is not independently claimed here.

---

# 14. Release governance: how to stop the infinite-round loop

Every future mega-round MUST declare:

1. which release version/gate it advances;
2. which funnel denominator it is intended to move;
3. the exact acceptance and kill criteria before implementation;
4. a negative/mutation control;
5. a fresh holdout or independent verifier appropriate to the claim;
6. what it will deliberately NOT build;
7. the resulting measured change.

A round that cannot name a release gate is research, not release-critical work. It may still be worth doing, but it
must not silently consume the 1.0 train.

Until 0.6 is complete, **new reaction-family expansion is frozen by default**. An exception requires a concrete
0.6 blocker or a regression fix. The point is not to stop chemistry research; it is to finish the front door before
making the engine wider behind an unfinished entrance.

---

# 15. Immediate next mega-round

The next implementation round is:

**v0.6 Human Chemical Front Door**

Canonical implementation plan:

[`V0_6_HUMAN_CHEMICAL_FRONT_DOOR_PLAN_v0.1.md`](V0_6_HUMAN_CHEMICAL_FRONT_DOOR_PLAN_v0.1.md)

The first required deliverables are:

1. reconcile release/documentation truth at current main;
2. implement the lossless formula-expression/normalization layer;
3. integrate it through the existing single identity service;
4. add explicit ambiguity/result semantics without guessing structure;
5. create the 1.0 funnel harness and hostile front-door corpus;
6. validate old explicit name/SMILES behavior and all existing tests;
7. update versioning only as justified by the completed release gate.

---

# 16. Completion criterion for the whole program

SmartChem 1.0 is ready when a user can supply an ordinary chemical identity/formula and the program reliably says:

- what it understood;
- what it cannot know from that input;
- how the composition decomposes;
- which structural identities/routes are actually represented;
- which candidate reactions are structurally/chemically vouched;
- which routes have real evidence for conditions/process;
- which route obligations remain unknown;
- what the chosen capability profile can and cannot support;
- what materials/equipment/controls the route requires;
- what hazards/unknowns/provenance attach to the result;
- whether each search was complete within its declared bounds.

The system does not need to know all chemistry.

It needs to **never lie about how much chemistry it knows** while being useful enough that both a research chemist and
a low-resource independent experimenter can get materially different, evidence-respecting value from the same
compiler.

That is the 1.0 finish line.
