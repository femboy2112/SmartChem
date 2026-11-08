# Post-3.0 milestone — LibGibson-powered Chemical Synthesis Path Explorer / Tester

**Created:** 2026-11-08. **Status:** PLANNED, NOT IMPLEMENTED. **Parent:** [ROADMAP.md](../../ROADMAP.md).
**Entry gate:** complete and accept the 3.0 falling-sand / spatial reactive-transport milestone first. This is a **post-3.0 milestone** (precise 3.x/4.x version intentionally deferred until public compatibility is designed), not evidence that 3.0 or 2.0 is released.
**Owner/consumer:** SmartChem; UI runtime: LibGibson. The chemical compiler/decompiler and evidence verifier remain the authorities; LibGibson is only an observer and interaction surface.

## North star

A user supplies a chemically typed target and optional available starting materials, selects a declared bounded search grammar and capability profile, and explores a **proof/evidence-carrying synthesis hypergraph** through an interactive LibGibson UI. They can inspect, compare, and virtually test candidate routes **only to the degree of evidence supported**. The UI never manufactures a route, reaction-class recognition, physical mechanism, completeness assertion, calibrated yield, affordability, or safety verdict.

**Non-negotiable distinction:** a conserving graph rewrite is not a chemical reaction; a recognized reaction class is not a practical process; a solvable mathematical model is not an empirically validated prediction; and a visualization is not evidence.

## Dependency graph and sequencing

1. **Production 1.x chemical compiler/decompiler remains independently useful.** Continue improving the general synthesis algebra, recognizers, stock/terminal matching, linear and DAG routes, typed event search, and verified transport while 2.0/3.0 research progresses. The post-3.0 explorer does not block core chemistry improvements.
2. **Synthesis correctness/coverage gates:** audit [issue #103](https://github.com/femboy2112/SmartChem/issues/103) and its remaining [#104](https://github.com/femboy2112/SmartChem/issues/104), [#105](https://github.com/femboy2112/SmartChem/issues/105), [#108](https://github.com/femboy2112/SmartChem/issues/108), [#109](https://github.com/femboy2112/SmartChem/issues/109), [#125](https://github.com/femboy2112/SmartChem/issues/125), [#130](https://github.com/femboy2112/SmartChem/issues/130) gaps. Existing 25-class production oracle, v0.8 legacy-read-only transport, no-false-VOUCH, source-conditional feasibility, and bounded completeness receipts stay intact. Charge- or configuration-aware grammar must be an explicitly versioned opt-in with its own tests; no silent 1.x semantics change.
3. **2.0 physical kernel:** structural conservation, typed execution/precision/source-domain receipts, calibrated-versus-assumed parameters, source provenance, and independently measured holdouts where a prediction is claimed. No unvalidated model is promoted to experimental truth.
4. **3.0 falling-sand acceptance:** spatial cells/faces, gravity/transport, grain-to-inventory accounting, reactive chemistry, conservation/positivity, convergence, deterministic replay, and a typed, read-only visual projection are accepted. A neutral-only, non-reacting ≤9×9 transport demonstration is a precursor, **not** completion. No synthesis-path explorer is claimed complete before this milestone passes.
5. **LibGibson boundary:** resolve or explicitly version the missing wire fields in [libgibson#290](https://github.com/femboy2112/libgibson/issues/290): quantity id, units, kind, model/evidence identity, trust label, and face-centred state. No data-smuggling through colors or a fake physics layer. A headless, renderer-independent reader remains available if LibGibson is not yet ready.

Pre-3.0 work may create schemas, acceptance fixtures and renderer-neutral mocks, but not an installed or advertised end-user explorer. **Post-3.0** means the full interactive exploration/testing integration starts after the accepted falling-sand milestone.

## Architecture — compiler is the authority; UI is the observer

**Versioned input:** `ExplorationSpec` declares target identity layer (constitution/configuration/isotope), available stock and provenance, reagent/catalyst/condition constraints, search grammar/providers, max depth/routes/event budgets, capability profile, optional process box, evidence policy, and optional physical simulator/scenario. No implicit switch of identity layer.

**Search object:** an AND–OR reaction **hypergraph** whose nodes are chemical identities with phase/charge/configuration as actually supported; hyperedges carry stoichiometry, atom/charge conservation, producer and independent recognizer records, step/route digests, declared mechanism limitations, source status, optional conditions, resource and hazard obligations. Linear paths are projections of this graph; convergent DAGs keep shared precursor identity and do not double-count stock. Cyclic no-stock plans are refused.

**Verdicts remain separate and typed:**
- generation/reachability within a declared grammar;
- reaction-type recognition (including ABSTAIN and internal-error);
- search completeness, budget truncation and coverage gaps;
- sourced reaction conditions and process readiness;
- material/equipment/capability and cost suitability;
- simulator structural and numerical certification;
- empirical validation, source domain and uncertainty;
- visualization/inspection status.

No aggregate "true" or "safe" score collapses these. A no-route result under an incomplete grammar must be called INCOMPLETE, not "impossible." A versioned JSON receipt must bind the request, the emitted route and verified admission facts; untrusted or thin payloads remain advisory. Version-bound result digests are not cross-release stable.

**Virtual testing:** simulate only supported, declared physical models with explicit initials, phases, boundaries, temperatures, rate/thermo data, units, and numerical receipts. If a reaction has no supported kinetic/thermodynamic law, display `UNKNOWN / NOT MODELED`; never improvise a yield, time course, pressure, heat, or safety clearance. Distinguish a proposed lab pathway from any executed experiment. No automatic execution of real-world reactions.

**LibGibson UX:** interactive target/stock explorer, expandable AND–OR/DAG route graph, branch/compare overlays, step-by-step transformation animation generated from admitted structure, evidence inspection, explicit unknowns and blockers, budget controls and provenance, side-by-side hypothetical parameter changes and model-relative trajectories. Toggle availability/conditions only by issuing a new `ExplorationSpec` and **recomputing** claims; a visual filter must not change the certified underlying record. Accessible keyboard, terminal and mobile-first layouts, with deterministic, exportable receipts. Visual state is always a one-way function of verified/declared data.

## Acceptance matrix — each gate requires hostile controls

| Gate | PASS condition | Required adversarial control |
|---|---|---|
| Dependency | 3.0 falling-sand gate already accepted; LibGibson contract versioned | a 3.0-only neutral transport demo cannot count as done |
| Core identity | constitution, stereo/isotope/charge scope explicit; same-formula isomers never silently conflated | ethanol vs dimethyl ether; enantiomer/unspecified-stereo/isotope under an unsupported identity layer must refuse |
| Chemistry | independent per-step conservation and recognition; false-VOUCH = 0 on pinned corpus | forged center, fake organometallic, impossible carbonyl transformation, mechanism collision, mutated coproduct |
| Path/stock | bounded linear and convergent DAG routes; no phantom stock; completeness and truncation receipts truthful | reversible A→B→A no-stock cycle, two branches sharing one precursor, budget cut at a viable successor |
| Conditions | missing catalyst/activator/process conditions demote, never silently pass | hydrogenation without valid activation, structurally SN2-compatible but unsupported conditions |
| Model testing | one admitted scenario with numerical/source/uncertainty evidence and one missing-data refusal | off-temperature constants, unbound kinetics, solver tolerance manipulation, invalid phase, charged transport |
| Viewer | LibGibson wire carries units/kind/claims; never modifies physics; replay stable | drop trust label, forge stronger badge, change units, mutate a frame, send unknown schema |
| Usability | deterministic local/headless exports and interactive cross-reference to original compiler receipts | two browsers/versions render same pinned receipt without changing validity |
| Release | full CI/contract test, scientific scope disclosure, source-to-artifact provenance, compatible SemVer and independent audit | published-demo and release-tag reproducibility, no unearned readiness/safety/empirical claim |

Begin with **two genuinely distinct, benign typed target scenarios** and one deliberate failed route. Do not hand-register a reaction as a "successful" test when the point is to establish general grammar-driven synthesis. A nonreproducible or unverifiable claim fails closed.

## Release boundary / roadmap checkpoints

- **Checkpoint P0 (now):** author these acceptance contracts, keep the general compiler/decompiler/path-synthesis development alive alongside 2.0 and 3.0. No explorer implementation is represented as complete.
- **Checkpoint P1:** establish a renderer-neutral `ExplorationSpec` / `ExplorationReceipt` prototype with read-only cross-references to *existing* production compiler outputs; no LibGibson dependency necessary yet.
- **Checkpoint P2:** complete the 3.0 falling-sand acceptance gates and LibGibson metadata wire.
- **Checkpoint P3 (after P2):** interactive LibGibson hypergraph explorer with route/step inspection, stock/condition changes, and certified visual truth display.
- **Checkpoint P4:** model-relative virtual testing, headless replay, hostile source/identity/budget corpus, phone/terminal interaction review and publishable documentation.
- **Checkpoint P5:** choose the appropriate 3.x/4.x version from the actual compatibility impact, build and independently audit the exact release candidate, only then consider tag/release.

**Not in scope:** claiming experimental synthesis was performed; inventing a chemical procedure, reaction yield or chemical safety approval; modifying frozen 1.x wire contracts without a major-version migration; promising that 3.0 or the explorer already exists.

Track this milestone in ROADMAP.md even if all implementation remains deferred. Its acceptance is determined by falsifiable tests, not visual polish.
