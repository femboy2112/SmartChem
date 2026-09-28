# SmartChem 0.9 — Capability Compiler ROUND II · PARENT-BARRIER DESIGN FREEZE (2026-09-28)

**Branch** `feat/v0.9-capability-compiler` (off `main@df1b38d`, `0.8.0a1`). **Version stays `0.8.0a1`** until the 0.9
gate closes. This document is the frozen contract Wave B builds against; it supersedes the Round I plan
(`V0_9_CAPABILITY_COMPILER_PLAN_v0.1.md`) wherever they disagree, and every disagreement below is a deliberate
correction forced by the four independent Wave-A recon bearings (equipment/process API; handling/cost/procurement
API; service/transport seam; independent forcing-corpus verdict oracle).

The 0.9 law, unchanged: **the SAME `ExperimentRoute` is projected through `ResearchLab`/`PoorMan`/`Custom`
profiles; the chemistry is identical, only the capability verdict differs.** Capability is a projection, not a
second chemistry engine; intrinsic `RouteReadiness` stays profile-independent.

---

## Wave-A findings that OVERTURN or SHARPEN the Round I plan (read first)

- **F1 (equipment source).** `equipment_for_step`/`equipment_for_envelope` (`experiment/equipment.py`) reads ONLY
  `ConditionEnvelope.medium` free-text + peak-T/pressure; it NEVER reads the sourced apparatus tuples. Verified live:
  on the isopentyl route it returns only `"reaction flask (Erlenmeyer or round-bottom) + a few beakers"`, silently
  dropping the reflux condenser and fractional-distillation apparatus the source demands. **RULING: the equipment
  REQUIREMENT is derived from `ProcedureEvidence.apparatus` (per-op, quote-sourced) + `ProcessRequirements.equipment`
  (whole-step) — NOT from `equipment_for_step`.** `equipment_for_step`'s hazard→`CONTAINMENT` inference
  (`equipment.py:242-244`) IS reused, but ONLY for the containment axis (see F-nag).
- **Coarse-kind collapse.** The 8-member `EquipmentKind` enum is TOO COARSE for capability comparison: reflux
  condenser, separatory funnel, and fractional distillation all collapse to `SEPARATION`/`VESSEL`, so a PoorMan
  owning any one separation tool would false-FIT a distillation requirement. **RULING (overturns Round I's
  `frozenset[EquipmentKind]`): equipment identity is a finer closed `EquipmentCapability` enum (specific apparatus,
  corpus-forced), each carrying a coarse `EquipmentKind` for display/grouping. Comparison is on the specific
  capability, never the coarse kind, never fuzzy substring (kills M5).**
- **F2 (material is UNKNOWN everywhere today).** Zero `StockMaterial` is seeded on any route. The material/assay axis
  is therefore UNKNOWN by construction for every route/profile, and "unknown assay never rounds up to FIT." **RULING:
  the CAPABILITY_FIT positive (gate #18) is reachable ONLY via a Custom profile carrying real declared
  `StockMaterial`s whose assays satisfy the route's inputs. `ResearchLabProfile` (no declared stock) stays a truthful
  UNKNOWN on isopentyl — a truthful UNKNOWN beats a gamed gate.**
- **F-nag (containment is a hazard lane).** No source procedure names "fume hood"; containment is derived from GHS
  hazards on the balanced-equation species. **RULING: apparatus tuples → equipment axis; GHS hazards → containment
  axis. Two evidence lanes, never crossed, never double-counted.**
- **F3 (blind spot, logged for Wave C).** `handling_of_step` scans only stoichiometric `reactants`/`products`;
  free-text catalysts/solvents (H2SO4, ethyl acetate) are invisible to the hazard scan. Moot in this corpus
  (H2SO4 has no GHS record) but structural — a Wave C candidate finding, NOT a 0.9 blocker.
- **F5 (search noninterference).** Confirmed: one `search_routes` result feeds all three profile projections; zero
  profile references in `readiness.py`/`routes.py`.

---

## THE EIGHT FROZEN DECISIONS

### 1. `CapabilityProfile` schema
ONE frozen `Digestible` type (new package `smartchem/capability/`). Fields:
- `profile_id: str`
- `material_inventory: tuple[StockMaterial, ...]` — ADOPT `StockMaterial` (it IS the MaterialBucket); `()` = no
  declared stock ⇒ material axis UNKNOWN.
- `equipment: frozenset[EquipmentCapability]` — the NEW closed specific-apparatus enum (decision 4).
- `physical_bounds: PhysicalBounds` — REUSE (`constraints.py`); T/P ceiling.
- `process_bounds: ProcessBounds` — REUSE (`process_constraints.py`); time/attention/agitation ONLY. Its
  string `available_equipment` is IGNORED for the equipment axis (decision 4 supersedes it).
- `containment: frozenset[ContainmentCapability]` — NEW (fume hood / sealed vessel / pressure / none).
- `ventilation: frozenset[VentilationCapability]` — NEW (indoor / outdoor). NEVER clears a containment requirement.
- `measurement: frozenset[MeasurementCapability]` — NEW, keyed on `SignalCost` tier + specific method.
- `waste_handling: frozenset[WasteCapability]` — NEW (aqueous-neutral / offgas-capture / hazardous).
- `procurement: frozenset[Availability]` — REUSE `Availability` tiers = the profile's `allowed_tiers` (decision 3+6).
- `budget: CostVector | None` — REUSE; a ceiling.
- `provenance: str` — declaration origin.
Separation/purification is NOT a separate field — distillation/filtration/sep-funnel ARE `EquipmentCapability`
members. `@classmethod` presets `research_lab()`, `poor_man(budget=...)`, `custom(...)` build this ONE type; NEVER
separate evaluators. Disambiguate the `HazardFlag`/`Bucket`/`CapabilityBucket` name collisions in the module
docstring; the type is `CapabilityProfile` (no "Bucket").

### 2. `RouteCapabilityRequirements`
A PURE `compile_capability_requirements(route) -> RouteCapabilityRequirements` projection that reads NO profile.
Independent axes, each UNKNOWN-capable as a first-class result:
- `material: tuple[MaterialRequirement, ...]` (decision 3)
- `equipment: frozenset[EquipmentCapability]` — resolved from `ProcedureEvidence.apparatus` (+ `ProcessRequirements.
  equipment` cross-check) via the closed resolver (decision 4).
- `physical` — T/P from `ProcessRequirements`/envelope extrema (feed `PhysicalBounds`).
- `process: tuple[ProcessRequirements | None, ...]` — DELEGATE time/attention/agitation to
  `evaluate_process_requirements(reqs, profile.process_bounds)`; do NOT reimplement (kills duplicate-authority risk).
- `containment: frozenset[ContainmentCapability]` — HAZARD-driven (reuse `equipment_for_step`'s GHS→CONTAINMENT).
- `measurement: frozenset[MeasurementCapability]` — from `VERIFY` operations (see decision-4 note on empty apparatus).
- `waste: WasteRequirement` — from `RouteHandling.all_byproducts`/`all_offgases` + `Fate` (NOT `CostVector.
  waste_disposal`, which is unpopulated).
- `procurement` — the route's catalysts/commodity leads via the generalized `route_catalyst_blockers` (decision 3).
- `attention_care: CareLevel` — from `RouteHandling.care` (hazard-driven DEMAND), kept STRUCTURALLY SEPARATE from
  the process/attention axis (operator CAPABILITY) so two attention axes can never silently disagree.
- `monetary` — `CostVector` known lower bounds only.
The compiler NEVER reads a `CapabilityProfile`; it asks only "what does the evidence say this route requires?"

### 3. `MaterialRequirement` semantics + procurement generalization
`MaterialRequirement` = requirement-side object (NOT a second inventory type): `structure identity`, `required_assay:
float | None` (None = UNKNOWN — never assume 100%), `phase | None`, `quantity | None`, `role`, `evidence_source`.
Assessed via `StockMaterial.satisfies(identity, min_assay)` (already interval-sound: worst-case fraction must clear
the requirement; same-formula constitutional isomer never borrows an assay; commodity lead ⇒ UNKNOWN_ASSAY). A
route reactant with no sourced assay requirement ⇒ `required_assay=UNKNOWN` ⇒ an assessment CANNOT claim a household
formulation FITS. Commodity availability informs PROCUREMENT only, never material fitness.
**Procurement generalization:** parameterize `catalyst_availability.KITCHEN_TIERS` → a profile-supplied
`allowed_tiers: frozenset[Availability]` via a new `is_obtainable_under(tier, allowed_tiers)` and a profile-aware
blocker path; PRESERVE the existing `is_kitchen_obtainable`/kitchen-default (LIVE-wired at `service.py:1830/1885/
2427/2457` → `hard_blockers` → `Disposition`) unchanged.

### 4. Equipment identity system (NEW, overturns Round I)
A closed `EquipmentCapability(str, Enum)` of corpus-forced SPECIFIC apparatus, each mapped to a coarse
`EquipmentKind`. Minimum members forced by the 5-route corpus:
`CONTROLLED_HEATING`(HEATING), `WATER_BATH`(HEATING), `ICE_BATH`(COOLING), `REACTION_VESSEL`(VESSEL),
`REFLUX_CONDENSER`(VESSEL), `SEPARATORY_FUNNEL`(SEPARATION), `FRACTIONAL_DISTILLATION`(SEPARATION),
`SIMPLE_DISTILLATION`(SEPARATION), `GRAVITY_FILTRATION`(SEPARATION), `VACUUM_FILTRATION`(SEPARATION+PRESSURE),
`THERMOMETER`(MEASURING), `BALANCE`(MEASURING). A closed `apparatus-string → EquipmentCapability` resolver reads the
sourced `ProcedureEvidence.apparatus` tuples; an UNRECOGNIZED apparatus string ⇒ the requirement axis is UNKNOWN for
that item (fail-closed, never silently satisfied). Comparison: `requirement.equipment ⊆ profile.equipment` on the
SPECIFIC capability. Measurement note: `VERIFY` ops carry `apparatus=()` in today's corpus ("weigh + IR" is
free-text in `analytical_verification`), so the STRUCTURED measurement requirement is empty ⇒ measurement axis is
NOT_APPLICABLE structurally (do NOT conjure an IR requirement from free text; that would fabricate a requirement —
log as a representational gap for a later round).

### 5. Capability verdict algebra
Per-axis `CapabilityStatus(str, Enum)`: `FIT / BLOCKED / UNKNOWN / NOT_APPLICABLE` (+ `UNCONSTRAINED` where the
profile declares no constraint on an axis that also has no requirement). Overall fold, order fixed:
`any hard BLOCKED → BLOCKED; else any required UNKNOWN → UNKNOWN; else FIT`. Retain the FULL per-axis reason set —
never hide multiple blockers behind a first error (kills M21: one fitting step never promotes a route with another
blocked step; weakest-link over steps AND over axes). Derived headlines: `CAPABILITY_ASSESSED` = an assessment
exists; `CAPABILITY_FIT` = overall FIT. **HARD LAW: `CAPABILITY_FIT` requires route tier ≥ `PROCESS_SPECIFIED`
AND every required axis FIT.** A route < PROCESS_SPECIFIED (aspirin/paracetamol FORMAL, methyl salicylate
CONDITIONS_SUPPORTED, DA REACTION_VOUCHED) may be ASSESSED but can NEVER be overall FIT (kills M9/M10/M11/M22).
`CAPABILITY_FIT` is NOT a safety certificate — every human/JSON surface carries the scope note; missing hazards
stay UNKNOWN.

### 6. Preset semantics
Closed preset registry (`"research-lab"`, `"poor-man"`) for named strings; inline `CapabilityProfile` for custom;
NO dynamic import from an arbitrary string.
- `research_lab()`: explicit well-equipped bench — `{CONTROLLED_HEATING, WATER_BATH, ICE_BATH, REACTION_VESSEL,
  REFLUX_CONDENSER, SEPARATORY_FUNNEL, FRACTIONAL_DISTILLATION, SIMPLE_DISTILLATION, GRAVITY_FILTRATION,
  VACUUM_FILTRATION, THERMOMETER, BALANCE}`, containment `{FUME_HOOD}`, ventilation `{INDOOR}`, procurement all
  tiers EXCEPT nothing special (industrial only if explicitly declared — default excludes INDUSTRIAL unless the
  caller adds it), measurement common. NO arbitrary industrial reactor / unlimited pressure / every catalyst /
  every chemical / unlimited money / unknown material purity. `material_inventory=()` by default ⇒ material UNKNOWN
  unless the caller supplies stock.
- `poor_man(budget=CostVector(cash=200,currency="USD",...))`: household/hardware/pharmacy + low-resource equipment
  `{CONTROLLED_HEATING, WATER_BATH, ICE_BATH, REACTION_VESSEL, GRAVITY_FILTRATION, THERMOMETER}` — explicitly NO
  `REFLUX_CONDENSER`, NO `FRACTIONAL_DISTILLATION`/`SIMPLE_DISTILLATION`, NO `VACUUM_FILTRATION`, NO `BALANCE`
  (kitchen scale ≠ analytical). containment `{}` (none), ventilation `{OUTDOOR}` (never clears containment),
  procurement `{GROCERY, PHARMACY, HARDWARE, POOL_GARDEN}` (NOT INDUSTRIAL). Budget is a parameter, not a hardcoded
  $200 forever.
- `custom(...)`: fully explicit; the forcing tool. The gate #18 FIT positive is a Custom profile carrying declared
  `StockMaterial`s for the isopentyl inputs + the full glassware + `{FUME_HOOD}` + waste `{AQUEOUS_NEUTRAL}`.

### 7. Request / service / canonical transport
- `CompilationRequest.capability_profile: str = DEFAULT_CAPABILITY_PROFILE` — new defaulted field. Enters the FULL
  `.digest` (provenance) via `Digestible` auto-hash; MUST NOT enter the hand-built `semantic_digest` tuple
  (`service.py:737-758`) — that exclusion IS the search-noninterference mechanism (mirror-image of `algebra_profile`,
  which DOES enter it). Structurally cannot reach the search receipt (produced in `compilation_ir.py` before
  request wrapping); do NOT thread it into `recompile_to_ir`/`decompile_to_ir`.
- `CapabilityAssessment` — `compare=True` per-route field on `RankedRouteSummary` (the `readiness` pattern), so it
  enters `result_digest` transitively via the summary's own digest. Thick re-derivable per-step evidence rides as a
  separate `compare=False` field (the `replay_payload` pattern). It carries the `profile_digest` it was computed
  under.
- Load-time `CAPABILITY-REBIND-ON-LOAD` (mirror `ALGEBRA-REBIND-ON-LOAD`, `service.py:4002-4027`): re-derive the
  assessment from carried evidence + `resolve_capability_profile(request.capability_profile)`; refuse on mismatch
  (kills M19: assessment relabeled under another profile; M20: custom content changes but digest doesn't).
- **`capability_question_digest = canonical_digest((semantic_digest, capability_profile))`** — a NEW pin closing the
  `expected_request_digest` hole (which keys on `semantic_digest` alone and would let a fully-coherent forger swap
  the capability question). The consumer request-pin binds the capability question, not just the search identity.
- CLI: `--capability-profile research-lab|poor-man` on `plan` (and `recompile`/`compile`), threading the `--algebra`
  four-hop (`cli.py:705-713 → plan.py:103 → service.py:855`). Human render shows READINESS and CAPABILITY[profile]
  as SEPARATE lines + the "fits modeled axes; not a safety certification" scope note.

### 8. File ownership (Wave B, ONE writer per file, dependency-ordered)
1. **v09-capability-core** — NEW `smartchem/capability/` package: the five capability enums + `EquipmentCapability`
   +`EquipmentKind` map + apparatus resolver, `MaterialRequirement`, `RouteCapabilityRequirements`,
   `compile_capability_requirements`, `CapabilityProfile`, `CapabilityStatus`, `CapabilityAssessment`, the pure
   `assess(profile, requirements)` evaluator; pure unit tests. NO `service.py`. (CRITICAL PATH — builds first.)
2. **v09-profile-presets** — preset builders + closed registry + `resolve_capability_profile` + preset tests.
   Consumes frozen core.
3. **v09-procurement** — generalize `catalyst_availability.py` (`allowed_tiers`); owns that file; preserves kitchen
   default. (Parallel with 2.)
4. **v09-service-transport** — `service.py` field + assessment attach + `CAPABILITY-REBIND-ON-LOAD` +
   `capability_question_digest`; `plan.py`/`cli.py` flag; canonical transport tests/goldens. Starts after 1+2 freeze.
5. **v09-measurement** — `experiments/v0_9_mutation_calibration.py` (M1-M22), `experiments/v0_9_capability_funnel.py`
   + `RESULTS`; README/ROADMAP/`V0_9_CAPABILITY_COMPILER_RELEASE_*.md` after behavior freezes. Also owns the
   forcing-corpus fixture (the fully-declared Custom StockMaterial inventory for the FIT positive).
Cross-file needs go to the owner as a failing discriminator + required invariant, never a competing edit.

---

## The frozen forcing matrix (independent oracle — implementers MUST match this, not their own expectations)

| route | tier | ResearchLab (no stock) | PoorMan | Custom |
|---|---|---|---|---|
| **isopentyl acetate** | PROCESS_SPECIFIED | **UNKNOWN** (material F2) | **BLOCKED** — equipment: no reflux condenser / no fractional distillation | teaching-bench-no-hood → **BLOCKED** containment; fully-declared → **CAPABILITY_FIT** (the gate #18 positive) |
| aspirin | FORMAL | **UNKNOWN** (tier caps FIT; resources present) | **BLOCKED** — equipment: no vacuum filtration | no-hood → **BLOCKED** containment (acetic anhydride) |
| paracetamol (anhydride) | FORMAL | **UNKNOWN** (tier caps FIT) | **BLOCKED** — no vacuum filtration | no-hood → **BLOCKED** containment (anhydride + Cat-2 mutagen) |
| methyl salicylate | CONDITIONS_SUPPORTED | **UNKNOWN** (tier<PS; data gaps) | **BLOCKED** containment (methanol) / equipment FIT-eligible | **BLOCKED** containment (methanol — same axis as PoorMan here) |
| retro-Diels-Alder | REACTION_VOUCHED | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** (null case: profiles MUST NOT diverge — nothing sourced to project) |

Anti-laundering laws encoded: tier<PROCESS_SPECIFIED ⇒ never overall FIT; outdoors ≠ containment; unknown
assay/hazard/price stays UNKNOWN; identical search feeds all three; the null (unsourced) route forbids divergence.

## Mutation-gate mapping (experiments/v0_9_mutation_calibration.py — M1-M22)
M1 commodity-lead-satisfies-material, M2 UNKNOWN-assay-sufficient, M3 same-formula-isomer-satisfies, M4 unspecified-
purity=100%, M5 equipment-fuzzy-substring, M6 outdoors-clears-containment, M7 profile-changes-search-candidates,
M8 profile-changes-receipt, M9 PROCESS_SPECIFIED→auto-FIT, M10 CONDITIONS_SUPPORTED→FIT, M11 unrecognized-reaction→
FIT-on-equipment, M12 missing-verification-ignored, M13 unknown-waste-passes, M14 unknown-price=0, M15 cash-floor<
budget=FIT, M16 mixed-currency-summed, M17 unrecognized-catalyst=poor-man-obtainable, M18 industrial-catalyst-free-
under-lab, M19 assessment-under-another-profile-no-refusal, M20 custom-content-changes-digest-doesn't, M21 one-
fitting-step-promotes-blocked-route, M22 FIT-survives-readiness-demotion.
