# SmartChem direction audit

*Scientific invariants, efficiency policy, and the path to a
reality-respecting simulation language.*

**Status:** project-direction audit, 2026-07-27. The non-negotiable laws below encode the
scientist's stated brief. The milestone order began as a proposal, not as evidence of an
earlier ratification. On 2026-07-27 the user explicitly directed execution of Milestones A and
B, the narrow H2 instance of Milestone C, and then the best-shot next midterm beginning with
the water-wave half of Milestone D and continuing through the human-identifiability D2a
slice. The completion record below is therefore a user directive, not a retroactive claim
about what Leah or Claude had previously intended.

**Audited baseline head:** `b85135a6849b78c507bb472752fc314116046b73`
(`main == origin/main` before this implementation)

**Companion:** `AUDIT_2026-07-20.md` remains the detailed scientific and multiphysics audit.

This document tightens that audit around one product direction:

> A scientist writes an incomplete physical program. The compiler shepherds it into a
> coherent, executable specification; proves or checks every claim it can; identifies every
> claim it cannot; chooses the cheapest execution that preserves the scientist's requested
> output; and returns a result whose physical scope, numerical evidence, provenance, and
> casualties are inseparable from the result.

This is the target. It is not a description of what SmartChem can do today.

---

## 1. Executive verdict

SmartChem now has a credible set of components from which such a system could grow. It is not
yet the system.

What exists is unusually valuable:

- a conserving path category of closed sequential chemical histories;
- narrow energy oracles that decline work outside their public evidence;
- exact stoichiometric derivation and checking over a saturated integer kernel;
- explicit oracle-domain and refusal diagnoses;
- a terminating shepherd loop that rejects menus lacking a derivation string;
- an exact result for complete distance constraints and a measured boundary for partial
  non-linear constraints;
- adversarial and mutation testing that has repeatedly falsified stronger-looking claims.

The 2026-07-27 implementation added that connection for three deliberately narrow verticals:

- a closed executor registry, a full shipped-source approval identity, and exclusive
  run-owned journals that prevent one calculation from erasing another;
- immutable source, resolved-program, thin Physical IR, request, plan, approval, run, and
  certificate artifacts;
- typed shepherd bindings and named validity obligations;
- one fixed reaction-energy compiler/executor with output-inventory, resource-wall, quarantine,
  and approval-integrity checks;
- one real `2 H -> H2` execution at existing public oracle coverage.
- one typed, branch-specific, prescribed-background shallow-water characteristic diagnostic,
  executed on a synthetic profile as `ANALOGUE/STRUCTURAL_TOY`, with every input/derived point,
  omission, and literal-gravity casualty retained.
- one typed human–isotope structural identifiability diagnostic, executed on a completely
  synthetic endpoint/protocol as `EXPERIMENTAL_PROXY/STRUCTURAL_TOY/UNVALIDATED`, which
  constructs two incompatible mathematical probability families satisfying the same median
  endpoint and emits no empirically calibrated or actual-human/population mortality
  probability or prediction.

What still does not exist is the general version: a language covering arbitrary worlds,
open-process and multiphysics semantics, a planner choosing among multiple valid model chains,
general cross-domain transport/assembly compilation, a general post-run validity/refinement
runtime, or a conversational surface. The executable bridges accept one typed `Reaction`, one
typed `WaterWaveSpec`, or one typed `HumanIsotopeSpec` from an outright-compiled `Session`;
this trio is still not a general `SimulationPlan` compiler, continuum wave solver,
toxicology model, or mortality simulator.

**This audit set the contract seam before the conversational UI.** That narrow seam is now
implemented and exercised across three deliberately narrow calculations. The same ordering
still governs the remaining general work:
build and test semantics before adding a fluent surface that could make missing semantics look
complete.

---

## 2. Non-negotiable project laws

### 2.1 Reality outranks completion

A coherent program is not necessarily a physically valid model. A converged solve is not
necessarily a validated result. A validated result is not necessarily scientifically useful.
The system must keep these verdicts distinct:

1. **well-formed** — syntax, units, identity, and references resolve;
2. **coherent** — declared invariants, conservation laws, and boundary contracts hold;
3. **applicable** — every model's a-priori validity predicates hold;
4. **converged** — the numerical method met its declared solver criteria;
5. **valid-after-run** — every a-posteriori model diagnostic passed;
6. **validated** — comparison evidence supports the claimed domain and error statement;
7. **useful** — a judgment reserved to the scientist.

No lower verdict may be silently promoted to a higher one.

### 2.2 No silent reduction of simulation output

Efficiency is maximally important, but it is optimized **under a frozen output contract**.
It is not permission to weaken that contract.

For this project, “simulation output” is interpreted broadly. It includes:

- which observables are returned;
- spatial, temporal, frequency, parameter, and ensemble support;
- resolution, sampling, duration, and precision;
- physical model, state, conformer, spin, phase, and coupling coverage;
- numerical tolerances and refinement requirements;
- uncertainty, residuals, validity diagnostics, and convergence evidence;
- provenance, discarded alternatives, warnings, and failure records;
- requested raw fields, trajectories, checkpoints, or intermediate artifacts.

Reducing any of these is an output change. It requires explicit approval from the scientist
before execution. A cost limit, timeout, memory cap, default setting, backend limitation, or
agent recommendation is not approval.

If the requested output cannot be produced within available resources, the compiler may:

1. find an identity-preserving execution;
2. present one or more explicitly different output contracts with predicted cost and
   casualties;
3. checkpoint or defer the unchanged request;
4. refuse and state the blocking resource or validity condition.

It may not silently return less.

### 2.3 Efficiency is lexicographically subordinate

The optimization order is:

1. preserve physical coherence and applicability;
2. preserve the approved output contract;
3. preserve the evidence and certificate needed to interpret the output;
4. minimize compute, memory, I/O, latency, energy, and monetary cost.

Within the first three constraints, efficiency is not merely desirable; it is a primary
compiler responsibility.

### 2.4 Derived, checked, searched, and guessed are different result types

Brick 5 established that the two halves of the original derived-menu law have different
computability:

- some admissible sets can be derived completely;
- a scientist-written candidate can often be checked even when the admissible set cannot be
  enumerated;
- a heuristic or bounded search can find candidates without certifying completeness;
- some claims cannot be decided with the available language or algorithms.

The language and compiler must encode those distinctions. A search result must never acquire
the word “all.” A checked candidate must never imply that alternatives were enumerated. An
inconclusive result must not become `False`.

### 2.5 The scientist owns meaning and tradeoffs

The compiler may certify coherence, applicability under declared rules, numerical evidence,
and the exact output delta between plans. It cannot certify that a question is meaningful or
that a fidelity/cost tradeoff is scientifically acceptable.

Approval must therefore be:

- affirmative and machine-recorded, not inferred from silence;
- attached to an immutable plan and output-contract digest;
- scoped to the particular inputs, models, tolerances, outputs, and run policy shown;
- invalidated by any material plan or output change;
- included in the result certificate.

A pre-authorized policy may approve a class of plans only when its machine-checkable bounds
are themselves explicit. It must bind the plan-generator, transform, backend, validation-data,
and error-model digests; the input-domain predicate; maximum deltas and resource bounds; the
specific output dimensions it may relax; and expiry/revocation conditions. Any digest or
scope change invalidates it. “Use reasonable defaults” is not such a policy.

Approval authorizes the disclosed tradeoff. It does not establish physical applicability,
convergence, validation, or truth.

### 2.6 Negative results are deliverables

Refusals, falsified predictions, failed validations, incomplete searches, and resource walls
remain in the record. They are not cleaned away to make the product surface smoother.

The project already owes much of its present rigor to this law. It must become a language and
runtime property, not only a working habit.

### 2.7 Cross-domain and cross-scale hypotheses are first-class programs

The language must accept a scientist's cross-domain metaphor or incomplete analogy as a
legitimate starting program. Its job is not to choose between literal acceptance and
rejection. Its job is to work with the scientist until it can separate:

- the **source theory** whose language supplied the metaphor;
- the **target phenomenon** the scientist is actually trying to model;
- the structural commitments intended to cross between them;
- the assembly that builds the target whole from its parts;
- the target scale and scientist-chosen degree of differentiation;
- the source axioms preserved, modified, or discarded;
- the calibration evidence and experimental outputs that could falsify the refined model.

The compiler may propose translations, vocabulary, candidate interpretations, and questions.
Those are language acts, not claims that the proposed physics is true. The scientist selects,
corrects, or replaces the interpretation, and the resulting choice becomes typed model
authority in the plan.

An unidentified assembly or unproved transport blocks a **certified** cross-scale claim. It
does not force the compiler to abandon the idea. The compiler may instead construct an
explicit `AssemblyHypothesis` or `ExperimentalModel`, expose the missing proof/calibration,
and run it in an experimental lane. Its outputs remain `EXPERIMENTAL/UNVALIDATED` until the
named evidence gates are met.

This is what “reality-respecting” means at the frontier: experimental approximations are
allowed, but the language never erases the difference between a useful hypothesis, a
calibrated approximation, and an established model. Claim scope and evidence status are
independent: an analogue can be well validated while remaining an analogue, and a literal
target can remain an unsupported hypothesis.

---

## 3. Efficiency classes

Every optimization should be classified before it becomes policy.

| Class | Meaning | Compiler authority |
|---|---|---|
| **A — identity-preserving** | Same physical problem and approved output under the contract's declared equivalence relation; only evaluation strategy changes. | May apply automatically only when its eligibility evidence and its applicability predicate both pass for this plan. |
| **B — contract-preserving numerical choice** | Different algorithm or backend, but every requested tolerance, coverage requirement, and diagnostic is met. | May apply within a scientist-approved output contract; certificate records the choice and evidence. |
| **C — approved tradeoff** | Changes the model, fidelity, coverage, tolerance, observable set, resolution, horizon, ensemble, diagnostics, or retained artifacts. | Must be proposed as an explicit output-contract delta and approved before execution. |
| **D — unsupported or unverifiable for certified output** | No established valid plan or no evidence that a plan meets the certified contract. | Refuse certified execution, request missing evidence, or execute only through an explicitly approved experimental hypothesis contract whose result cannot be promoted beyond `EXPERIMENTAL/UNVALIDATED`. |

Current examples:

- structural rejection before an oracle call, reuse of a validated value under an immutable
  per-call calculation identity, shared CCSD intermediates, lossless compression, and
  deterministic parallel scheduling are candidate Class A work;
- a different sparse solver meeting an already approved residual and refinement contract is
  Class B;
- density fitting, a cheaper geometry tier, frozen-core changes, coarser meshes, fewer
  conformers, shorter trajectories, looser thresholds, bounded pathway depth, and suppressed
  diagnostics are Class C unless equivalence to the requested output is actually established;
- an unvalidated polyatomic profile or a model whose validity predicate cannot be evaluated
  is Class D for certified public scientific output; it may still be studied in a separately
  approved experimental lane.

“Faster on one case” does not establish a class. The repository's distinction between the
identity-preserving `direct` CCSD route and density fitting, which changes the reported
number, is the right pattern (`experiments/ccsd_acceleration_probe.py`).

Cached refusals are not Class A by default. A transient convergence failure must not become a
durable omission. A refusal may be reused only when it has a typed stable reason, a validity
scope, and independent evidence that repeating inside that scope cannot change the decision;
the reuse and scope remain visible in the certificate.

Every `OutputContract` must declare the relevant equivalence relation. It may require
byte-identical artifacts, or it may permit semantic equivalence with explicit numeric
tolerances, ordering rules, RNG seed/state, checkpoint/retention requirements, and allowed
provenance differences. A transform defaults to Class C when it can affect a retained artifact
and the contract has not authorized that difference.

Regression tests make a transform **eligible** for a class. They do not prove it applies to a
particular plan. Every applied transform must also carry a machine-evaluated applicability
predicate, an exactness or discrepancy reference, and an emitted transform record.

---

## 4. Current-state truth table

| Capability | Live state | What the evidence licenses |
|---|---|---|
| Closed chemical histories | **Enforced** | `Reaction` construction enforces atom and net-charge conservation and path continuity. It does not establish kinetics, open-system physics, or parallel composition. |
| Stoichiometric menu | **Built and exact for its declared invariants** | `stoichiometry.py` derives a saturated integer-kernel basis and checks written balances. State and energy remain outside those invariants and are reported as blind spots. |
| Non-linear distance constraints | **Built with a negative boundary** | Complete rational distance data can be refused or forced exactly up to isometry. Distance data cannot distinguish chiral mirror images. Partial fixed-dimensional completion is not enumerated; linearised nonzero freedom is inconclusive. |
| Oracle domain declarations | **Built, narrow, one-way** | Declared-outside implies refusal. Declared-inside does not promise a value. Present axes do not express general physical validity or dimensionless regime tests. |
| Refusal diagnosis | **Built** | Obstructions are derived from conservation and domain facts. There is no model router or executable remedy graph. |
| Shepherd termination | **Built, syntactic** | A well-founded multiset rank prevents endless rephrasing/deepening, and menus require a non-empty derivation string. It proves termination, not that new subquestions semantically descend from the old one. Legacy slots remain textual; the first executable vertical additionally requires typed bindings and machine derivation references. |
| Section I loop | **Demonstrated, not compiled** | Four rounds close a hard-coded example and the category accepts its fixed reaction. The closed `Session` is not interpreted into a general runtime plan. |
| Contract seam and typed bindings | **Built, narrow vertical slices** | Immutable source/program, request, plan, approval, run, certificate, typed binding, and validity-obligation artifacts now support the H2, structural water, and structural human-identifiability verticals. They do not yet make a general simulation language. |
| Approved H2 vertical | **Executed once, complete** | `2 H -> H2` ran through the approved source-to-certificate path at the existing CCSD(T)/cc-pVTZ protocol. The durable receipt and its limitations are in `experiments/RESULTS_compiled_h2_vertical.md`. |
| Water-wave cross-domain slice | **Executed structural compiler test** | The typed language distinguishes target, regime, branch, flow direction, and black/white/pair orientation; the runtime retains every prescribed SI profile point, independently rechecks every crossing, and binds an exact analogue/casualty scope. The synthetic run is `STRUCTURAL_TOY`, not a measured flume, validated horizon, continuum wave evolution, or astrophysical result. |
| Human–isotope cross-scale slice | **Executed structural underidentification test** | The typed language binds target, population, granularity, assembly, environment, hazard effect, toxicokinetic link, LD50/LC50 protocol, and calibration evidence. The runtime independently rechecks that distinct exponential and Weibull probability witnesses share the one median endpoint while disagreeing away from it. The run is `EXPERIMENTAL_PROXY/STRUCTURAL_TOY/UNVALIDATED`; individual, cause-specific, observed-data, and empirically calibrated or predictive probability outputs remain blocked. |
| Public quantum-chemistry output | **Implemented in a narrow domain** | Enabled neutral atoms and fixed neutral diatomics under measured protocols; broader internal code fails closed rather than inheriting evidence. |
| General simulation runtime | **Unbuilt** | No general state evolution, boundary/reservoir semantics, time integration, mesh, ensemble, or coupled solver system. |
| Typed Physical IR and language | **Built for three narrow verticals; otherwise unbuilt** | The minimal source/IR records support H2, the prescribed-background water diagnostic, and a human-proxy identifiability record including typed calibration and model patches. They do not yet cover general worlds, typed ports, validated cross-scale dynamics, or a general simulation language. |
| Output contract and approval gate | **Built for three narrow verticals** | All three executors require their exact output contracts; changing membership, support, resolution, precision, coverage, diagnostics, or retention blocks execution until a different executor exists. Broader policy and tradeoff negotiation remain unbuilt. |
| Post-run validity transition | **Built for three narrow verticals** | Named obligations and complete/incomplete/invalid/refused/failed records exist on all three; no general solver/result-state runtime exists. |
| Result certificate | **Built for three narrow verticals** | Receipts bind the H2, structural water, and structural human-identifiability runs to their scope, evidence, omissions, and casualties; this is not yet a general artifact system. |

The strongest honest summary is:

> SmartChem is a tested, fail-closed compositional chemistry and specification-tooling
> prototype. It is not yet a simulation language or a shepherded simulation compiler.

---

## 5. Required language and artifact model

The reality-respecting simulation programming language should make four things separately
spellable:

1. **world description** — components, states, geometry, materials, connections, boundaries,
   reservoirs, sources, frames, and conditions;
2. **model commitments** — governing equations, constitutive laws, assemblies, adapters,
   approximations, and validity predicates;
3. **requested evidence** — observables and the complete output contract;
4. **authority** — which assumptions and tradeoffs the scientist has approved.

A minimum immutable artifact chain is:

```text
SourceProgram
  -> ResolvedProgram
  -> PhysicalIR
  -> SimulationRequest
  -> CandidatePlan(s)
  -> ApprovedPlan
  -> RunRecord
  -> SimulationResult
  -> Certificate
```

Each arrow is a checked transition. Backend execution accepts an `ApprovedPlan`, not a raw
request or a conversational `Session`.

### 5.1 Minimum records

- `Quantity`: value/range, dimension, unit, frame/orientation, source and uncertainty.
- `Identity`: stable physical identity including state, isotope, spin/multiplicity,
  conformer/stereochemistry, phase, and reference convention where relevant.
- `Component`, `Port`, `Connection`, `Reservoir`, `Boundary`: typed open-system structure.
- `SourceTheory` and `TargetIntent`: the source vocabulary/axioms and the target question as
  understood and confirmed by the scientist.
- `TransportMap`: source/target entities, observables, operations, and axioms, with each marked
  preserved, modified, discarded, unknown, or proposed-for-test.
- `ClaimScope`: literal target, analogue of a named source/target relation, experimental proxy,
  or another non-aliasing referent; this never doubles as an evidence grade.
- `AssemblySpec` or `AssemblyHypothesis`: how target-scale wholes arise from parts, the chosen
  granularity, aggregation/quorum/interaction rules, and the evidence status of each rule.
- `TransportEvidence` and `AssemblyEvidence`: proof/derivation, regime predicates,
  calibration/validation records, counterexamples, and remaining obligations needed to
  certify the map or assembly.
- `ModelPatch`: every deliberate change to the source theory, including environment-dependent
  rates, memory, coupling, repair, or state dependence.
- `CalibrationSpec`: data population, exposure/measurement protocol, endpoints, likelihood or
  constraints, identifiability, validation split, and uncertainty treatment.
- `EvidenceStatus`: established, calibrated, experimental, structural-toy, or unsupported;
  refinability and truth remain separate axes.
- `Invariant`: the quantity/law, operation under which it is preserved, scope, and checker or
  derivation.
- `ModelSpec`: equations, inputs, outputs, assumptions, a-priori and a-posteriori validity,
  conserved quantities, calibration/validation evidence, and version.
- `SolverSpec`: algorithm, discretization, tolerances, stopping/refinement policy, backend,
  hardware/thread policy, and deterministic/reproducibility contract.
- `CalculationSpec`: immutable per-execution composition of model, solver, inputs,
  environment, implementation/data digests, and cache identity.
- `ObservableRequest`: identity, support, aggregation, resolution, precision, coverage,
  diagnostics, and retention.
- `OutputContract`: the immutable collection of observable and evidence requirements.
- `EquivalenceContract`: byte or semantic equality, tolerances, ordering, RNG, retention,
  checkpoint, and permitted provenance differences.
- `Transform`: exactness class, input/output model, proof or discrepancy evidence, and
  casualty list.
- `CandidatePlan`: complete model/solver chain, predicted resources, unresolved predicates,
  output contract, and digest.
- `Approval`: scientist/principal, plan digest, scope, approved deltas, and timestamp.
- `ApprovedPlan`: an API capability with a private construction path, binding an approval to
  exactly one candidate-plan digest. It is not a hostile-process security boundary.
- `RunRecord`: actual execution environment, cache decisions, checkpoints, resource use,
  status transitions, and complete/partial artifact inventory.
- `Certificate`: source/request/plan/approval digests, versions, decisions, residuals,
  refinements, claim scope, evidence status, validity outcomes, output inventory, omissions,
  and failures.

Strings remain valuable as preserved source text and explanations. They must not be the
semantic payload that authorizes a run.

### 5.2 Canonical cross-domain program — the human–isotope model

The canonical language test is the scientist's statement:

> Model a generic human as a scientist-chosen bundle of differentiated molecular or
> higher-scale components, using a modified radioactive-decay model whose failure or death
> hazard responds to environmental exposure and is constrained, where available, by
> ethically and legally obtained human mortality, toxicokinetic, clinical, or epidemiologic
> evidence.

The source phrase “based on the LD-50 of humans given environmental constraints” must remain
in `SourceProgram`; the resolved program must not silently reinterpret it as authority for a
direct human experiment or as an existing universal constant. The shepherd asks whether the
scientist means a human evidence synthesis, an explicit nonhuman-to-human extrapolation, or a
hypothetical median-endpoint constraint, and records that answer and its evidence separately.

The compiler must not answer that statement with either “humans are not isotopes” or a
ready-made mortality equation. It must recover the intended structure collaboratively.

At minimum it must ask or derive:

1. **Target and observable.** Is this an individual stochastic lifetime, a cohort survival
   curve, a hazard function, expected lifespan, time to a functional threshold, or several of
   these?
2. **Granularity.** Which molecular classes, cells, tissues, organs, repair systems, or lumped
   functional units are differentiated? Which remain aggregate populations? The scientist's
   choice belongs in the output contract; changing it is a model/output change.
3. **Assembly.** What constitutes a living whole: redundancy, quorum, repair capacity,
   competing subsystem failures, state transitions, or another declared rule?
4. **Environmental exposure.** Which agent or condition, route, concentration/dose, duration,
   schedule, interactions, and recovery dynamics drive the target model?
5. **Meaning of “modified decay rate.”** Does environment change part-level failure hazards,
   whole-organism hazard, repair/redundancy state, transition intensities, or more than one?
   The existing probe chose fixed part hazard plus redundancy; that is one hypothesis, not the
   language's answer.
6. **LD50 semantics.** An [LD50 is a fitted median lethal **dose** endpoint, while an LC50 is
   a median lethal **concentration** endpoint](https://www.epa.gov/haps/health-effects-notebook-glossary),
   each for a specified experimental population, route, exposure protocol, endpoint, and
   observation window. Neither is itself a per-time decay constant or a universal human
   parameter. Any LD50/LC50-derived constraint must state species or population, route,
   administered versus internal dose metric, exposure duration, endpoint definition,
   observation window, and uncertainty. Animal LD50 evidence is not directly portable to a
   human target. It may constrain a dose-response or hazard model only after provenance,
   target-population applicability, toxicokinetic transport, and time dependence are
   explicit. A single median endpoint does not identify the requested dynamic model; the
   compiler must name the missing information rather than manufacture it.
7. **Preserved and discarded source structure.** Stochastic survival and state transitions
   may transport. Nuclear memorylessness, constant rate, independent parts, a material
   half-life, and daughter-process semantics need not. Every modification and casualty is
   emitted.
8. **Evidence status.** Unless calibrated and validated on a declared population, the result
   is an experimental approximation and must not be reported as a mortality model, a
   prediction for an actual person, or proof that the metaphor is true.

A permissible target family could use a state-dependent survival model:

```text
state dynamics:        dz/dt = F(z, environment(t), parameters)
cause-specific hazard: h_k(t) = G_k(z(t), environment(t), parameters)
all-cause hazard:      h(t) = sum_k h_k(t)
all-cause survival:    S(t) = exp(-integral_0^t h(u) du)
assembly:              organism_alive = A(component states, quorum/repair rules)
```

This is a schema, not the chosen physics. `F`, `G`, `A`, component granularity, and calibration
are holes for the shepherd and scientist to close. A molecularly differentiated program may
instantiate component populations; a tissue- or subsystem-level program may use explicit
coarse-graining. The compiler records the map between them and never treats a cheaper
granularity as equivalent without evidence and approval. The exponential survival expression
is valid only when `h` is the complete conditional hazard for the stated event. If the target
is a cause-specific failure in the presence of competing risks, the compiler reports
cumulative incidence under the declared competing-risk model rather than substituting the
cause-specific hazard into an all-cause survival equation.

**Canonical acceptance tests**

- preserve the original human–isotope statement and every subsequent scientist correction;
- present candidate interpretations as questions, not as an exhaustive admissible menu;
- require a typed source theory, target intent, transport map, assembly, and granularity;
- distinguish LD50 dose from LC50 concentration and reject treating either endpoint as a
  time-rate constant;
- declare time origin, event/failure definition, competing risks, censoring and truncation
  treatment, baseline/population strata, and the administered-dose-to-internal-exposure
  toxicokinetic link;
- treat an LD50/LC50 endpoint, under its stated model assumptions and observation window, as
  at most a constraint near 50% cumulative mortality—not as an identification of `F`, `G`,
  `A`, an individual risk, or the separation of background and exposure hazards;
- require multi-dose/time calibration, uncertainty intervals, and held-out validation before
  emitting a probability claim;
- allow environment to affect failure hazard, redundancy/repair state, or both when the
  scientist selects and specifies the mechanism;
- emit every preserved, modified, discarded, and unknown source axiom;
- require at least one load-bearing prediction or discriminating experiment beyond fitted
  calibration targets;
- execute an approved incomplete theory only with `EXPERIMENTAL/UNVALIDATED` status;
- prevent successful refinement from promoting the original metaphor to truth;
- invalidate approval when granularity, assembly, environmental protocol, calibration data,
  or output support changes.

### 5.3 Canonical cross-domain program — a black-hole analogue in water

The complementary language test is:

> Simulate a black hole in water.

This is a real analogue-gravity research program, but the sentence remains radically
underdetermined. Surface waves on moving water can experience a wave horizon when the
background flow crosses the relevant wave-propagation speed. Open-channel experiments have
measured horizon-induced mode conversion and scattering in both white-hole and black-hole
orientations:

- [Measurement of Stimulated Hawking Emission in an Analogue System, *Physical Review
  Letters* 106, 021302 (2011)](https://doi.org/10.1103/PhysRevLett.106.021302) used surface
  waves over an obstacle and studied a white-hole-oriented wave-blocking analogue;
- [Scattering of Co-Current Surface Waves on an Analogue Black Hole, *Physical Review
  Letters* 124, 141101 (2020)](https://doi.org/10.1103/PhysRevLett.124.141101) measured
  scattering on a transcritical flow with an effective black-hole horizon;
- [Observation of negative-frequency waves in a water tank: a classical analogue to the
  Hawking effect?, *New Journal of Physics* 10, 053015
  (2008)](https://doi.org/10.1088/1367-2630/10/5/053015) reported
  positive-to-negative-frequency mode conversion in a moving medium.

The language must use that literature to supply vocabulary, not to assume which experiment
the scientist means. It must ask:

1. **Target structure.** Is the intended observable wave blocking, the effective metric,
   horizon location, mode conversion, scattering coefficients, a thermal spectral relation,
   backreaction, or a proposed black-hole-laser cavity?
2. **Orientation.** Is this a black-hole horizon, a white-hole horizon, or a black/white pair?
   Flow direction, incident-wave direction, and time orientation are semantic inputs, not
   display choices.
3. **Fluid model.** What are the channel geometry, depth and velocity profiles, gravity,
   density, viscosity, surface tension, boundary forcing, and dimensionality?
4. **Wave regime.** Are the shallow-water, linear-perturbation, stationary-background, weak
   dissipation, and continuum assumptions applicable? In a one-dimensional, stationary,
   inviscid, irrotational, gravity-only shallow-water model, the signed normal
   characteristics are `dx/dt = U_n +/- sqrt(g h)`. A selected characteristic is critical
   where `|U_n| = sqrt(g h)` (`|Fr_n| = 1`); whether that is a black- or white-hole
   orientation depends on the declared coordinates, flow direction, and incident/outgoing
   branch. In dispersive gravity-capillary water waves, horizons must instead be determined
   from the full Doppler-shifted dispersion relation for the requested laboratory frequency
   and branch. Wavepacket blocking is a group-velocity condition, and multiple
   frequency-dependent horizons may occur.
5. **Transport.** Which part of the source black-hole theory is being mapped to which
   hydrodynamic variable and operation? The perturbation wave equation and horizon/scattering
   kinematics may transport in a declared regime. Einstein dynamics do not follow from that
   analogue and may not be imported without a separate model and evidence.
6. **Casualties.** Water does not create an astrophysical black hole, literal spacetime
   curvature, a singularity, or an event horizon for matter. Classical stimulated mode
   conversion does not by itself establish spontaneous quantum Hawking radiation.
7. **Scope and evidence.** A reproduced, regime-matched water-wave result may have
   `ClaimScope = ANALOGUE_OF(BLACK_HOLE_WAVE_KINEMATICS)` and
   `EvidenceStatus = VALIDATED_WITHIN_REGIME`. Those are independent fields. Its scope never
   becomes `ASTROPHYSICAL`; a proposed extension may retain analogue scope while carrying
   `EvidenceStatus = EXPERIMENTAL`.

This case complements the human–isotope model. The water-wave transport has a comparatively
sharp mathematical sub-theory and experimental precedent; the human model asks the compiler
to help formulate an underidentified experimental assembly. The language must handle both
without flattening them into the same confidence class.

**Canonical acceptance tests**

- accept “black hole in water” as an underdetermined analogue program, not a literal object
  construction and not a reason for immediate rejection;
- require the scientist to select the transported phenomenon and black/white orientation;
- derive or numerically check the branch-specific horizon condition from the approved
  fluid/wave model;
- report `NO_HORIZON_IN_DECLARED_REGIME` when the flow never crosses the relevant wave speed;
- distinguish nondispersive, gravity-capillary, viscous, nonlinear, and turbulent regimes;
- record the applicability of stationarity, dimensionality, irrotational/barotropic or
  shallow-water assumptions, depth and capillarity regime, vorticity/shear,
  viscosity/dissipation, nonlinearity, forcing/reflections, and slow-background/WKB
  assumptions; failure of the nondispersive effective-metric gates invalidates that claim.
  A full-dispersion branch/group-velocity horizon remains a possible weaker analogue claim
  only when it is derived from the frequency- and branch-specific dispersion relation;
  otherwise report only the actually established classical wave-scattering result;
- emit the complete source-to-target transport and casualty map;
- prevent classical stimulated scattering from being labeled spontaneous quantum emission;
- for a thermal-spectrum target, normalize positive- and negative-norm modes; calibrate
  forcing, background noise, and instrument transfer; establish a stationary ensemble; and
  propagate dispersion and dissipation uncertainty;
- require a quantized-field state and an explicit nonclassical occupation/correlation
  criterion before making a quantum-Hawking claim;
- for a black-hole-laser target, require a black/white horizon pair, a trapped
  negative-norm branch and cavity boundary conditions, plus gain/loss and linear-stability
  calculations;
- for backreaction, require coupled wave/mean-flow evolution and energy/momentum accounting;
  a fixed-background test-wave simulation cannot claim it;
- preserve requested wavefields, spectra, modes, scattering coefficients, resolution, and
  frequency support under the no-output-reduction contract;
- require both non-aliasing fields on every result: claim scope (analogue versus literal
  referent) and evidence status (hypothesis, calibrated, or validated-within-regime);
- prevent either field from promoting an analogue result to an astrophysical prediction.

### 5.4 Cross-domain portfolio beyond the canonical pair

The human–isotope and water-wave cases are not meant to become two hard-coded metaphors.
They are the first two points in a test portfolio. Future cases should be chosen because they
exercise a materially different kind of transport, assembly, or evidence boundary:

| Candidate program | Structure that may transport | Mandatory casualties/evidence gate | Portfolio role |
|---|---|---|---|
| **Traffic jam as a kinematic fluid shock** | Vehicle conservation, characteristics, shocks/rarefactions, and Rankine–Hugoniot shock speed under a declared flux law. The gas-kinetic route can also derive macroscopic equations from driver/vehicle assumptions. | Cars are not fluid molecules; momentum closure, driver memory, lane changing, junctions, and stop–go behavior do not follow automatically. Require measured fundamental diagrams, boundary/sensor provenance, uncertainty, and held-out shock trajectories. | Best next regime-valid analogue after D2. See [Treiber, Hennecke, and Helbing (1999)](https://arxiv.org/abs/cond-mat/9901240). |
| **SIR epidemic as a chemical reaction network** | `S + I -> 2 I`, `I -> R` has a mass-action deterministic/stochastic reaction interpretation under a well-mixed abstraction. | Contacts are not molecular collisions; chemical thermodynamics and detailed balance do not transport. Networks, behavior, latency, infectious-period distributions, demography, observation bias, and causal claims require their own models and evidence. | Strong reuse test for the chemistry syntax, but higher-stakes than traffic. |
| **Electrical, mechanical, hydraulic, and thermal systems through bond graphs / port-Hamiltonian structure** | Effort-flow power pairing, storage, dissipation, and power-conserving port interconnection compose across substrates. | Voltage is not force, pressure, or temperature; constitutive laws, parasitics, field radiation, saturation, distributed effects, and regime limits remain domain-specific. | Best architectural test of typed ports and open-process composition. See the [automated multi-bond-graph formulation](https://arxiv.org/abs/1909.02848). |
| **Ising magnet as a lattice gas** | The occupation/spin substitution can give an exact equilibrium Hamiltonian and partition-function map. | Spins are not particles; dynamical rules, transport, ensemble, boundary, and finite-size interpretation do not follow from the equilibrium equivalence. | Theorem-level transport control against which the compiler's map/casualty machinery can be checked. |
| **Option pricing as heat diffusion** | Under the Black–Scholes assumptions, log-price, discounting, and reversed time transform the pricing PDE into a heat equation. | Temperature is not value; risk-neutral price is not an actual-return forecast. Constant volatility, continuous trading, frictionlessness, and diffusion assumptions are load-bearing. | Adversarial non-physical-domain boundary; avoid until the interface cannot turn it into financial prediction. |
| **Groundwater flow as an electrical conductor/network** | Darcy flux and Ohmic current share a linear potential-gradient/conservation structure in the declared regime. | Water is not charge; unsaturated, multiphase, non-Darcy, deformable, transient-storage, and reactive-transport behavior require additional models. | Low-risk port/field validation case with clear field-evidence gates. |

The portfolio should deliberately contain three controls:

1. a **regime-valid analogue**, where a useful sub-theory transports only under measured
   predicates (traffic);
2. a **theorem-level equivalence**, where the mathematical map is exact but target semantics
   still need a casualty boundary (Ising/lattice gas);
3. a **substrate-independent composition**, where shared power/port structure is the point
   and constitutive laws stay domain-local (port-Hamiltonian systems).

Candidate rankings are architecture choices, not validations. The compiler must still ask
what observable and map the scientist intends. It must not advertise this table—or any
generated list—as an exhaustive menu of legitimate metaphors.

---

## 6. Required compiler pipeline

1. **Preserve source.** Retain the scientist's words and source spans verbatim.
2. **Parse source and target language.** Produce syntax without inventing missing physics;
   retain which terms came from the source metaphor and which describe the target.
3. **Resolve and type.** Establish identities, units, dimensions, states, frames, ports,
   boundaries, references, and evidence status.
4. **Interpret collaboratively.** Offer vocabulary and candidate source-to-target readings as
   questions. Record the scientist's confirmation/correction; do not claim the candidates are
   complete physical possibilities.
5. **Name transport and assembly.** State which structure is preserved, modified, discarded,
   unknown, or hypothesized, and how target-scale wholes arise from their parts.
6. **Shepherd holes.** Derive complete menus where possible; ask open questions where not;
   check scientist-written candidates against the same declared rules.
7. **Build Physical IR.** Make every invariant, model commitment, assembly, observable, and
   dependency explicit.
8. **Freeze the output contract.** If fidelity or completeness is unspecified, ask. Do not
   infer permission to reduce.
9. **Evaluate applicability and evidence status.** Check a-priori validity predicates,
   preserve a-posteriori predicates as executable obligations, and keep experimental
   hypotheses distinct from certified models.
10. **Enumerate candidate model chains.** A certified candidate exists only if its inputs,
    references, domain obligations, transport evidence, and assembly evidence can all be
    satisfied. Missing transport/assembly proof forces the experimental lane; it cannot be
    downgraded to a note. An experimental candidate exposes every unsatisfied evidence
    obligation.
11. **Apply Class A transforms.** Prove/check identity and retain the transformation record.
12. **Optimize within the contract.** Choose the cheapest Class A/B plan satisfying every
    output and evidence requirement.
13. **Propose tradeoffs when necessary.** Show every Class C output delta, predicted resource
    change, validation basis, uncertainty effect, and casualty.
14. **Acquire approval.** Bind permission to the immutable plan digest and experimental or
    certified execution lane.
15. **Execute.** Record actual backend, environment, resource use, cache state, and all emitted
    artifacts.
16. **Check after-run obligations.** Convergence alone is insufficient. Failed validity or
    refinement checks invalidate the result; they do not become warnings on a nominal
    success. Any re-plan invalidates the old approval. Only a byte-identical Class A
    re-execution may continue under it; every changed model, solver, tolerance, support,
    retention rule, or stopping policy returns to planning and approval.
17. **Emit result and certificate.** Claim scope and evidence status are both mandatory. The
    output inventory and any omission must be machine-comparable to the approved contract.

A timeout, cancellation, or resource failure produces `INCOMPLETE`, never a smaller success.
Partial grids, trajectories, cache entries, and checkpoints are hashed, inventoried, and
quarantined as non-substitutable artifacts. Publishing them as scientific output requires a
new approved partial-analysis contract; resuming them requires an approved resume plan.

The conversational layer is an interface to these transitions. It never substitutes for one.

---

## 7. Milestone status and build order

For the roadmap horizons requested on 2026-07-27, Milestones A and B are completed
short-term goals. The H2 instance of Milestone C is complete. The selected next midterm was
decomposed: water-wave D1 is complete as a structural toy, and human–isotope D2a is complete
as a structural underidentification result. D2b—the first empirically fitted
probability-bearing data-bound reliability/survival executor—remains open. Milestones E and F
follow. Physical flume validation, dispersive wave solving, and broader multiphysics work
remain separate
longer-horizon validation/runtime work.

### Milestone A — freeze the contracts — EXECUTED 2026-07-27 by user directive

Implement the complete minimal vertical-slice chain as immutable, serializable types:

- `SourceProgram` and `ResolvedProgram`;
- a thin typed Physical IR sufficient for the first chemistry vertical, including
  `ModelSpec`, `SolverSpec`, and immutable per-call `CalculationSpec`;
- `SourceTheory`, `TargetIntent`, `TransportMap`, `AssemblySpec`/`AssemblyHypothesis`,
  `TransportEvidence`, `AssemblyEvidence`, `ClaimScope`, `ModelPatch`, `CalibrationSpec`, and
  `EvidenceStatus`;
- `SimulationRequest`;
- `ObservableRequest`;
- `OutputContract`;
- `EquivalenceContract`;
- `ValidityObligation`;
- `CandidatePlan`;
- `Approval`;
- `ApprovedPlan`;
- `RunRecord` and explicit complete/incomplete/failure result states;
- `Certificate`.

This milestone performs no expensive simulation. Its job is to make silent output loss and
unapproved execution unavailable through the supported local API.

**Completion scope.** The immutable vertical-slice records and approved-execution boundary
were implemented for the first chemistry vertical. This is execution of the proposed
milestone by user directive, not evidence that the proposed roadmap had previously been
ratified. The H2 receipt records the resulting plan, approval, run, outputs, and certificate:
`experiments/RESULTS_compiled_h2_vertical.md`.

**Exit tests**

- changing any input, model, tolerance, requested observable, output support, or approximation
  changes the plan digest and invalidates approval;
- backend execution through the supported API cannot be called with an unapproved plan;
- approval can be created only for a candidate digest and execution can consume only the
  resulting `ApprovedPlan` capability;
- a cache lookup derives its key from an immutable per-call `CalculationSpec` digest; changing
  mutable wrapper state cannot serve a stale value;
- a memory/time shortfall returns `INCOMPLETE` after a durable run is created, without changing
  the output contract;
- a run that already started and then hits a memory/time limit becomes `INCOMPLETE`; its
  artifacts are inventoried and quarantined, never substituted for completed output;
- the certificate's output inventory exactly covers the approved contract or names the run
  incomplete/failed—never partial success.

### Milestone B — typed bindings over the existing shepherd — EXECUTED 2026-07-27 by user directive

Keep the proven termination machinery, but make slots carry a schema and typed binding.
Replace `checkable_after: bool` with named executable `ValidityObligation` values.

**Completion scope.** The first vertical uses typed binding and named obligations instead of
authorizing execution from a string-only closed session. This does not prove that every future
slot, cross-domain interpretation, or solver obligation is already expressible.

**Exit tests**

- `"<answered>"` cannot close a physical slot;
- a bound value must validate against its slot schema;
- each derived option carries a machine reference to its invariant and derivation;
- checked, derived-complete, searched-incomplete, and undecidable outcomes cannot alias;
- interpretations offered by the compiler remain questions until the scientist confirms them;
- an unproved transport or assembly can close only into an experimental hypothesis, never a
  certified model;
- a failed a-posteriori obligation transitions the run to invalid/refine/refuse.

### Milestone C — compile the first narrow vertical — EXECUTED FOR H2, 2026-07-27

Compile one deliberately small chemistry request into the existing oracle runtime. Do not
claim generality. The vertical should exercise the whole artifact chain:

```text
source -> resolved program -> Physical IR -> shepherd/request -> candidate plan
       -> ApprovedPlan -> PySCF/heuristic execution -> RunRecord/result
       -> validity checks -> certificate
```

The first target should stay inside an already measured public oracle domain so the milestone
tests the compiler, not new chemistry.

**Completed instance.** `2 H -> H2` used the existing fixed-geometry
CCSD(T)/cc-pVTZ public protocol and reached `COMPLETE` with all four recorded obligations
passing. Its endpoint delta-E was `-4.427005898711 eV`; compared by magnitude with the
repository H2 D0 of `4.478 eV`, the difference is `0.050994 eV`. This is one vertical
execution, not a recalibration, an MAE, a bound, a Gibbs result, or new chemistry coverage.
See `experiments/RESULTS_compiled_h2_vertical.md` for the run, plan, approval, artifact, and
certificate digests.

### Milestone D — compile the canonical cross-domain pair — D1 AND D2a EXECUTED; D2b OPEN

Compile both canonical requests through the same artifact chain:

1. the water-wave black-hole analogue as the comparatively sharp, literature-anchored
   transport; then
2. the human–isotope request as the underidentified experimental transport.

The pair is deliberate. The first tests whether the language can preserve a known sub-theory
without turning an analogue into a literal claim. The second tests whether it can help the
scientist formulate a new approximation without turning refinement into validation.

**Completed D1 scope.** `water_wave_slot` refuses to close the original phrase through text;
the scientist must bind a typed target, nondispersive/dispersive/etc. regime, characteristic
branch, flow direction, black/white/pair orientation, explicit assumption vector, gravity,
and complete SI profile. The current executor implements only the classical nondispersive
`U +/- sqrt(g h)` characteristic diagnostic. Unsupported scattering, thermal, quantum,
laser, backreaction, viscous, nonlinear, turbulent, and gravity-capillary requests are
planning blockers. A synthetic four-point run reached `COMPLETE` with a
`KINEMATIC_CROSSING_IN_DECLARED_MODEL` at the independently reproduced interpolated position;
its scope is `ANALOGUE` and its evidence is `STRUCTURAL_TOY`. The certificate explicitly
records that the profile is synthetic and that wavelength/frequency, capillarity, stationary
continuity/momentum, measurement/resolution uncertainty, and interpolation discrepancy were
not established. See `experiments/RESULTS_compiled_water_wave_vertical.md`.

For the human case, reuse `experiments/decay_analogy_probe.py` only as one prior hypothesis and
not as the predetermined answer. The compiler must support a scientist-selected
environmentally conditioned hazard, redundancy/repair mechanism, component granularity, and
LD50 calibration constraint while keeping the result explicitly experimental.

**Completed D2a scope.** `human_isotope_slot` leaves the original metaphor open until a
scientist binds a typed target, population/event/censoring/truncation protocol, component
granularity, assembly hypothesis, environmental route and schedule, hazard-effect choice,
toxicokinetic link, LD50/LC50 endpoint, and calibration-evidence inventory. The executor
accepts one hypothetical median endpoint and emits a complete identifiability diagnostic,
constraint inventory, and two normalized family witnesses. Both witnesses satisfy 50%
cumulative mortality at the endpoint; they disagree at half the observation window. The
result is therefore `UNDERIDENTIFIED_DYNAMIC_MODEL`, `UNVALIDATED`, and
`EXPERIMENTAL_PROXY/STRUCTURAL_TOY`. It emits no actual-person or population mortality
probability or prediction derived from evidence; its retained numbers are mathematical
counterexamples under a synthetic constraint. Individual-lifetime, cause-specific
cumulative-incidence, observed/cross-species evidence, functional-threshold endpoints, and
richer calibration requests are planning
blockers until their distinct endpoint semantics, data-governance, competing-risk,
calibration, validation, and output executors exist. See
`experiments/RESULTS_compiled_human_isotope_vertical.md`.

**Open D2b scope.** An empirically fitted probability-bearing model must add a
scientist-selected dynamic family, multi-dose and multi-time data, uncertainty, held-out
validation, and identified assembly/toxicokinetic evidence. Cause-specific probability
additionally requires every
competing hazard and a cumulative-incidence calculation. D2a's successful negative result is
not calibration evidence for D2b.

**Exit tests**

- every question and choice in Sections 5.2 and 5.3 is represented in the source/target/
  transport/assembly/calibration artifacts;
- the water-wave program distinguishes black/white orientation, derives or checks its horizon,
  and preserves the analogue/literal casualty boundary;
- reproduced analogue-scattering evidence cannot promote the result to an astrophysical
  black-hole claim or an unmeasured quantum-emission claim;
- the human program represents every question and choice in its source/target/transport/
  assembly/calibration artifacts;
- at least two materially different target interpretations can be posed and selected without
  either being advertised as an exhaustive physics menu;
- LD50/LC50 endpoint, protocol, provenance, and dimensional checks prevent either from being
  inserted as a decay constant;
- insufficient calibration returns an identified family or missing-evidence obligation, not
  a fabricated unique model;
- running the model produces falsifiable experimental outputs and a complete casualty list;
- no result can lose `EXPERIMENTAL/UNVALIDATED` status merely because it converged or refined
  successfully.

### Milestone E — optimizer and no-loss ratchet

Add a planner with Class A transformations first: cache/reuse, exact structural cancellation
inside the declared separable model, shared intermediates, lossless storage, and bounded
parallel scheduling. Add Class B choices only against explicit tolerances and refinement
evidence. Class C remains proposal-only until approved.

**Exit tests**

- every Class A transform is tested against an independent or mutation-capable oracle;
- optimization order cannot change requested values, coverage, diagnostics, or provenance;
- finite search depth, grids, caps, or early stopping emit truncation/coverage metadata and
  cannot be reported as complete;
- warm-cache and cold-compute performance are measured separately;
- a faster plan that violates one output requirement loses to a slower valid plan.

### Milestone F — conversational surface

Only now add the fluent language interface. It should explain:

- what the scientist wrote;
- what was forced, chosen, assumed, searched, or left unknown;
- why each plan is applicable;
- what each cheaper plan changes;
- which approval is required;
- what the completed run established and did not establish.

This ordering preserves the rule already learned in `THE_COMPILER.md`: dialogue is last because
dialogue is the part that can most easily fake a working compiler.

---

## 8. Audit and verification gates

Every scientific or performance milestone must include:

1. a declared claim with a named scope;
2. the cheapest counterexample or mutation that could falsify it;
3. an independent check that does not reuse the implementation's decisive intermediate;
4. exact commands, versions, inputs, resource limits, and raw outputs;
5. passed, failed, skipped, and deferred work reported separately;
6. performance measured only after output equivalence or output delta is established;
7. no tuning of acceptance thresholds on the evaluation population;
8. preservation of failed runs and falsified predictions.

Automation and lower-capability models may inventory, generate fixtures, run bounded probes,
perform repetitive implementation, and mechanically assemble/hash a certificate from trusted
records. They may propose plans. They do not fabricate certificate contents, assert
unsupported scientific validity, or approve fidelity reductions. Approval and evidence remain
separate: scientist authority licenses a disclosed tradeoff, while independent checks support
validity claims.

### Current verification record

Run after the implemented narrow vertical and its adversarial fixes, in the repository virtual
environment:

```text
.venv/bin/python -m pytest -q -rs
1169 passed, 14 skipped, 1 xfailed in 19.72s
```

The 14 tests marked slow were not run and are not counted as passed. PySCF was installed, so
the unmarked real-oracle tests and the separate compiled H2 smoke did execute real wavefunction
work. The water-wave and human-identifiability structural calculations have no PySCF
dependency. The strict xfail is the intentional true-parallel-interchange architecture debt.
This no-`--runslow` result plus the scoped H2, water, and human-identifiability receipts
supports the implemented narrow contracts only; it does not validate the unbuilt general
language/compiler, promote the water profile beyond `STRUCTURAL_TOY`, or validate a human
mortality model.

---

## 9. Known live risks that the next work must not hide

- legacy `Slot.binding`, menus, and derivation explanations remain strings for compatibility.
  Schema-bearing physical slots require typed bindings, and the first executable bridge refuses
  legacy text, but future verticals must adopt that boundary rather than bypass it.
- `COMPILED_SUBJECT_TO` names a boundary and is refused by the first executable bridge; its
  obligations cannot yet be mapped into a general post-run evaluator registry.
- no router joins multiple oracle domains or proves compatible reference zeros.
- public quantum output remains narrow; internal polyatomic and optimized-geometry paths are
  not public validated capabilities.
- finite pathway depth, finite Store grids, solver iteration caps, and experiment-specific
  candidate sets have no shared output-coverage contract.
- persistent cache identity is strong but cannot fingerprint undeclared external state,
  every transitive dependency, or all hardware/numerical nondeterminism. Existing cache
  wrappers are mutable compatibility machinery; the compiled runtime needs frozen execution
  objects and a calculation-spec digest checked on every lookup.
- the inspected benchmark population is not an independent holdout.
- open systems, ports, Gibbs thermodynamics, kinetics, full state identity, coupled fields,
  continuum free-surface evolution, dispersive analogue-gravity wave propagation, and general
  multiphysics validity remain roadmap work; the built water slice is only a prescribed-profile
  algebraic characteristic diagnostic.
- the arbitrary cross-scale “assembly” needed to justify structural transport remains a
  research problem. If it cannot be identified, certified transport must be declined; an
  explicit assembly hypothesis may still enter the experimental lane.
- no useful middle ground has yet been found between linear invariants with complete finite
  generators and non-linear invariants whose partial completion cannot be enumerated.

These are not reasons to pause the compiler project. They are the facts its types must carry.

---

## 10. Directional acceptance statement

Future work is aligned when it makes the following end state more true:

> SmartChem accepts an intentionally incomplete physical program; preserves the scientist's
> intent; collaboratively interprets cross-domain and cross-scale language; turns useful
> metaphors into explicit, falsifiable experimental models without treating refinability as
> truth; shepherds missing structure without inventing physics; distinguishes derivation,
> checking, search, hypothesis, and ignorance; constructs only appropriately labeled model
> chains; aggressively optimizes their execution without changing the approved output; asks
> explicitly before any fidelity or coverage loss; verifies preconditions, convergence, and
> postconditions; and returns every result with a reproducible certificate and casualty list.

Work that only makes the dialogue more fluent, adds a solver without a validity contract,
makes a benchmark faster by returning less, or turns an unvalidated internal route into a
public capability is not progress toward that end.
