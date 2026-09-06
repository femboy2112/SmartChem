# SmartChem: Process Observation and Transport Contract v0.1

**Status:** proposed research contract  
**Date:** 2026-09-06  
**Research branch:** aletheia/creator-process-research-2026-09-06  
**Baseline:** main at 574a3e29584770c10608dfaff596119ce30e18a6  
**Scope:** evidence architecture and planning semantics only. This document does not add laboratory procedures, execution authority, or a claim that any route is safe, practical, legal, or suitable for a particular person or facility.

## Decision

SmartChem should treat chemistry-creator footage as a source of scoped operational observations, not as a recipe corpus.

The next high-value seam is a read-only evidence-ingress layer named **ProcessObservationIR**. It records what a source actually shows or states about one run, under one context, with explicit gaps. A reviewed projection may enrich existing condition and resource records only when identity, direction, and context match. It must never manufacture a complete procedure by splicing unrelated clips, infer omitted details, or lift a route above its existing readiness tier.

This is the durable version of the poor-man ethos:

> Affordable chemistry is not a cheap reagent list. It is a whole-path capability claim: material identity, controllable operations, measurement, containment, separation, verification, and responsible closure all have to be present or explicitly blocked.

## What the current main already gets right

This proposal extends rather than replaces the current chemical-compiler discipline.

- ConditionEnvelope and ProcessRequirements already model declared whole-step process facts: workup scope, time, attention, agitation, equipment, and whole-process temperature/pressure extrema.
- A process FITS result only means that supplied requirements fit declared bounds. It is not a finding of reaction feasibility, yield, safety, legal compliance, unattended suitability, or bench readiness.
- ConditionRecord carries reaction direction and exact structure-aware selection. Algebraic reversal does not reverse experimental evidence.
- StockMaterial prevents a commodity/source lead from silently becoming a pure, suitable reagent.
- The handling layer preserves the rule that UNKNOWN is not safe and does not emit an unattended-operation clearance.
- The Chemical Compiler Standard already reserves ProcedureIR for a reviewed BENCH_DRAFT and requires workup, purification, verification, waste, hazards, stop conditions, and scale exclusions. ProcessObservationIR is a precursor evidence layer for that future object, not a shortcut around it.

Current source-backed process records and combined DAG admission exist in main. Older audit text that says the catalog has no such records or that DAG process admission is wholly unassessed is historical, not a current baseline.

## Research source map

The source families below are deliberately non-identical. Creator material reveals how a real project exposes hidden operational seams; institutional, regulatory, and metrology sources constrain what may be claimed from those observations.

| Source family | What it supports here | What it does not support |
|---|---|---|
| [NileRed](https://www.youtube.com/@NileRed) creator cases, listed below | Context-bound observations about iteration, measurement, separation, functional acceptance, and infrastructure burden | General route validity, a safe procedure, scale transfer, or a substitute for a reviewed source record |
| [NileBlue: Chemistry is dangerous](https://www.youtube.com/watch?v=ftACSEJ6DZA) | Explicit prerequisites should not be assumed merely because a project is presented as a home or maker activity | A complete hazard assessment or authorization to replicate an experiment |
| [Applied Science: DIY scanning electron microscope](https://benkrasnow.blogspot.com/2011/03/diy-scanning-electron-microscope.html) | Commission the limiting subsystem with a relevant measurement before trusting the integrated apparatus | That a generic apparatus name proves a specific capability |
| [Applied Science: Measuring human digestive efficiency vs. a flame](https://benkrasnow.blogspot.com/2021/02/measuring-human-digestive-efficiency-vs.html) | A measurement needs a stated measurand and an equally clear non-claim | That an observed scalar automatically establishes the user-facing outcome |
| [MIT OCW Digital Lab Techniques Manual](https://ocw.mit.edu/courses/res-5-0001-digital-lab-techniques-manual-spring-2007/pages/videos/) | A technique taxonomy that includes measurement, workup, filtration, purification, analysis, and reporting | Suitability of any technique for an arbitrary reaction or user context |
| [Open Reaction Database schema](https://docs.open-reaction-database.org/en/latest/schema.html) | Separate representations for inputs, setup, conditions, observations, workups, outcomes, analyses, and provenance | Completeness of SmartChem's future procedure semantics by importing a schema unchanged |
| [LearnChemE](https://learncheme.com/) | Unit-operation, stream, separation, control, and model-boundary thinking | A simple process model proving an uncontrolled or nonideal bench route will work |
| [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/) and [NIST uncertainty guidance](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-7-reporting-uncertainty) | Conditioned property provenance, source citation, uncertainty components, and method-reporting discipline | A pure-substance reference proving complex-mixture behavior, product identity, or route success |
| [OSHA laboratory standard](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1450), [NIOSH hierarchy of controls](https://www.cdc.gov/niosh/hierarchy-of-controls/about/index.html), and [Prudent Practices](https://www.ncbi.nlm.nih.gov/books/NBK55880/) | Route-specific hazard/control reasoning, engineered controls before administrative controls/PPE, and explicit hygiene/waste concerns | Home-lab legal advice or universal jurisdictional compliance |
| [AppliedEngineering](https://www.youtube.com/@AppliedEngineering) | An orientation corpus for concept-design-test work | A factual source in this round; individual videos were not reliably inspectable and therefore supply no imported claim |

### NileRed creator cases

These are source-led case studies. Their claims remain **Observed in the shown context** until a curator captures the relevant fragment, date/version, exact timecode or quotation, and a transport review.

| Source | Process lesson observed | SmartChem implication | Boundary |
|---|---|---|---|
| [Making transparent wood](https://www.youtube.com/watch?v=uUU3jW7Y9Ak) | Revisiting linked procedures with changed material/process choices yields different quality outcomes | Preserve source version, material equivalence, substitution risk, and acceptance criteria; do not flatten a source into a reaction equation | A creator iteration is not a generalized protocol or a chemical mechanism proof |
| [I still can't believe that Epsom Salt is mostly water](https://www.youtube.com/watch?v=8GVSuKkuLzY) | A hydrate-composition claim is checked by a mass-balance style measurement rather than trusted from a label/formula | Model hydrate/solvate form, input state, theoretical composition, measured change, and mass-closure error separately; a low-cost screening check is not a purity certificate | One result does not certify arbitrary material identity or suitability |
| [Taking the caffeine out of Red Bull so I can drink it at night](https://www.youtube.com/watch?v=oY8tz1paj6o) | Separation/identity evidence and safe intended use are separable; the creator explicitly warns against reproduction because residual contamination can matter | Keep separation achieved, identity evidence, residual-risk coverage, and intended-use suitability as independent fields | Partial removal or recovery must never become a safe-consumable claim |
| [Making superconductors](https://www.youtube.com/watch?v=RS7gyZJg5nc) | Good appearance can fail an objective functional test; a known-good intermediate can narrow a fault hypothesis before rework/retest | Every route needs an end-to-end acceptance test, evidence of what it measures, and named control/diagnostic states; success is not a boolean | The demonstration does not establish a transferable materials procedure |
| [Making liquid nitrogen from scratch](https://www.youtube.com/watch?v=GmwaJnj6pfY) | A nominally simple target can be dominated by utility, containment, pressure/thermal, energy, component, and testability constraints | Add apparatus/utility capability gates and an explicit acquisition/outsourcing boundary; return not feasible in this bucket rather than an invented household substitute | This is an infrastructure lesson, not a model for bypassing control or containment requirements |

## The missing object: ProcessObservationIR

ProcessObservationIR is an immutable source-fragment record. It is not a procedure, an instruction list, a safety clearance, or an authority to perform an operation.

    ProcessObservationIR {
      schema_version
      observation_id

      reaction_identity
      reaction_direction
      run_context_id
      phase

      source_fragment {
        locator
        source_role
        publication_or_capture_date
        source_version_or_content_digest
        quote_or_timecode
        reviewer
      }

      claims[] {
        status: OBSERVED | QUOTED | DERIVED | UNKNOWN
        subject
        value_and_unit
        uncertainty_or_resolution
        what_it_supports
        what_it_does_not_establish
      }

      context_scope {
        material_identity_and_assay
        scale_and_geometry
        apparatus_capabilities
        medium_and_atmosphere
        controlled_intervals
      }

      transport {
        disposition: EXACT | PARTIAL | OUT_OF_SCOPE | UNKNOWN
        mismatches[]
        reviewed_bridge_id
      }

      explicit_unknowns[]
      provenance_digest
    }

The proposed phase vocabulary is classification only:

    SETUP | CHARGE | ADDITION | REACTION | QUENCH | WORKUP |
    ISOLATION | PURIFICATION | ANALYSIS | WASTE

It makes omitted stages visible without supplying an action sequence. The primary value is that a source can honestly say, for example, “analysis was observed, but the source does not document the waste path,” rather than silently treating a visual success as a complete route.

## Non-negotiable invariants

1. **No Frankenprocedure.** Claims from different run_context_id values remain separate source fragments. They may only be combined through a reviewed transport bridge that names the preserved facts, changed facts, and residual unknowns.

2. **Direction is load-bearing.** A source fragment for a decomposition cannot fill an assembly record merely because a formal reaction edge reverses.

3. **Unknown stays unknown.** A video cut, a generic apparatus label, an absent workup, an unlabeled material grade, or missing scale must not be inferred into a positive field.

4. **Evidence never promotes by itself.** ProcessObservationIR may enrich provenance and expose a process fit/exclusion/gap. It may not turn FORMAL_CANDIDATE into BENCH_DRAFT, emit SAFE or PROCEED_UNATTENDED, or create a prescriptive sequence.

5. **Observables have scope.** Every measurement declares what it supports and what it cannot establish. A rapid screen can be consistent with an identity; it cannot silently become identity confirmed, purity established, or endpoint proven.

6. **Evidence affects identity.** Source fragment, scope, transport disposition, and claims must contribute to the evidence/provenance digest so a changed observation cannot masquerade as the same planning artifact.

7. **No scalar truth score.** Evidence status, context match, resource fit, handling coverage, verification coverage, and readiness remain separate axes. They may disagree.

## From equipment list to capability passport

SmartChem currently has two useful but unbridged equipment languages: free-form exact identifiers in ProcessBounds and inferred EquipmentKind candidates in the drafting layer. The next object should bridge them without pretending that objects are interchangeable.

    BenchCapability {
      capability_id
      function
      qualified_operating_range
      compatible_materials_or_unknown
      containment_or_emission_control
      measurement_resolution_and_calibration_state
      qualification_evidence
      status: FITS | UNKNOWN | EXCLUDED
      provenance
    }

A name such as “flask,” “pump,” “heater,” or “scale” cannot satisfy a capability by itself. The capability comparison must retain ratings, calibration/functional-check evidence, condition range, and unknowns. SmartChem must never recommend a makeshift substitution merely to make a low-cost route fit.

## Poor-man buckets become whole-path capability bundles

The existing commodity/material work remains useful. This contract adds three non-price bundles before any affordability ranking:

| Bundle | Required question | Failure result |
|---|---|---|
| Material bucket | Is the exact material, assay/grade, quantity, and storage state evidenced? | material or assay gap |
| Capability bucket | Can the actual bench provide the required containment, control, separation, and measurement functions? | CAPABILITY_BLOCKED |
| Verification bucket | Is there an evidence-backed observable/acceptance plan with known limits, calibration/QC state, and an honest non-claim? | VERIFICATION_BLOCKED |
| Closure bucket | Are byproduct, emissions, decontamination, waste disposition, and applicable review dependencies represented? | REVIEW_REQUIRED or closure gap |
| Scale bucket | Does the requested scale/geometry remain inside the source and control envelope? | SCALE_UNVALIDATED |

These are **orthogonal planning findings**, not replacements for the readiness tiers in the Chemical Compiler Standard. Cost is a Pareto dimension after hard capability and closure blockers; a route that is cheap in reagents but lacks verification, containment, or waste closure is not poor-man preferred.

## One-way projection into existing SmartChem records

ProcessObservationIR should initially be a read-only sibling of the compiler and project only after review:

1. The reaction identity and direction match the target ConditionRecord exactly.
2. The claim is reviewer-approved and its source fragment is available.
3. The context transport is EXACT or a reviewed PARTIAL bridge explicitly licenses the specific field.
4. The projection fills only an observed/quoted/derived field and carries its source linkage; it never fills omitted facts.
5. A mismatch, missing scope, or unreviewed creator source produces UNKNOWN, PARTIAL, OUT_OF_SCOPE, or a blocker—not a soft positive.

The existing ConditionEnvelope.process and ProcessRequirements fields are appropriate first projection targets for scoped resource facts. ProcedureIR remains the later, reviewed assembly object required by the standard; this ingestion layer must not bypass it.

## Route-state display

The user interface should keep four independent bands visible:

| Band | Question answered |
|---|---|
| Formal candidate | Is there a conservation-valid candidate within the declared finite search? |
| Evidence/context match | What source claims exist, and do their identities, direction, material, scale, and apparatus contexts transport? |
| Resource comparison | Does the declared bench capability/profile fit the sourced requirements? |
| Handling and verification coverage | What hazards, controls, observables, uncertainty, acceptance criteria, waste, and unresolved fields remain? |

Avoid labels such as “easy,” “safe,” “low-risk,” or “poor-man approved.” A process FITS display must explicitly say it fits declared resource limits only.

## Implementation ladder

### P0 — this branch

Publish the source map, contract, boundaries, and falsifiers. No chemistry catalog expansion and no procedure generation.

### P1 — read-only evidence ingress

Add immutable ProcessObservationIR and source-fragment validation. It must be possible to represent a source that has an exact title and link but missing timecode, version, material grade, or endpoint; those fields remain unknown.

### P2 — transport and capability validation

Add reviewed TransportBridge and BenchCapability objects, with no automatic apparatus substitution. Build one small, benign, independently sourced holdout set before attaching creator-derived observations to live planning records.

### P3 — verified route-operation modeling

Only after P1/P2 validation, add a separate operation graph that can represent setup, process, workup, isolation, purification, analysis, and closure as individual evidence-bearing stages. It should feed the future ProcedureIR requirements without changing the present FORMAL_CANDIDATE ceiling.

## Acceptance probes for the first implementation round

| Probe | Expected result |
|---|---|
| Remove workup, scale, endpoint, or waste evidence from an otherwise good source record | Relevant field is UNKNOWN; no route readiness promotion |
| Present a reverse-direction fragment | It cannot support the opposite direction |
| Combine fragments from two run contexts without a bridge | Construction is refused; no merged operational bundle exists |
| Supply a generic equipment name with no qualification/rating evidence | Capability is UNKNOWN, not FITS |
| Replace calibration/QC evidence with a stale, missing, or failed record | Numeric conclusion is downgraded to UNVERIFIED |
| Change material grade, scale, vessel geometry, or thermal environment outside scope | Transport becomes PARTIAL/OUT_OF_SCOPE and SCALE_UNVALIDATED or REASSESS_REQUIRED |
| Delete a waste/decontamination closure record | Route cannot be marked operationally complete |
| Present creator-video evidence only | It may appear as a demonstrated source record but cannot enter a validated corpus or bypass safety/capability gates |
| Find a cheap reagent basket that relies on PPE/administrative discipline where an engineered control is required | It does not outrank a controlled route as poor-man preferred |
| Mutate a source fragment, claim, or transport bridge | Provenance digest changes and cached admission is invalidated |

## Claim ledger

| Claim | State | Boundary |
|---|---|---|
| SmartChem already has strong process constraints, direction-aware condition records, material truth, and fail-closed handling primitives | Disclosed | Checked against main at the baseline commit named above |
| Creator projects expose recurring differences between a reaction arrow and a runnable whole path: fidelity, measurement, separation, acceptance, and infrastructure | Observed | The named public sources show cases; no claim of universal frequency or transportability |
| ProcessObservationIR plus reviewed transport is the best next architecture seam | Conjectured | Needs a small implementation and hostile source-splicing tests |
| Creator records can be safely ingested into a live chemistry catalog at useful coverage | Unverified | Lamp: reviewed source-fragment capture, exact scope matching, and independent holdouts |
| A fully capability-aware, low-resource route planner can make broad practical recommendations | Dark | Lamp: larger curated evidence corpus, independently verified apparatus/capability profiles, jurisdiction-specific closure data, and chemist review |

## Final boundary

The productive lesson from NileRed, Applied Science, and the engineering/chemistry training corpus is not that chemistry becomes easy when equipment is cheap. It is that real work becomes legible when every hidden dependency is forced into the open: what is being controlled, what is being measured, what the observation proves, what it cannot prove, and what has to be true for the next operation to be meaningful.

SmartChem should make that legibility computational. It should not impersonate the missing apparatus, measurement, training, evidence, or review.
