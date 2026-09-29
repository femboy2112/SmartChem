# SmartChem 0.9 RC — Round IV External Audit & Semantic Barrier

**Date:** 2026-09-28
**Branch:** `feat/v0.9-capability-compiler` · **tip at audit open:** `f8fe8bd`
**Base:** `main@df1b38d` · branch 17 ahead / 0 behind
**PR:** #93 — OPEN, **NOT merged**, flipped to `[EXTERNAL AUDIT HOLD — Round IV]`
**Package:** stays `0.9.0a1` (not released to `main`)

> Round IV thesis: **make the word FIT obey conservation, evidence strength, and unknownness all the way down.** An external hostile review opened a new class of silent-overclaim findings (F41–F55) that M1–M40 never calibrated against. These are *composition* bugs. Until each is reproduced-and-fixed, rigorously refuted, or explicitly shown not to affect the release contract, PR #93 must not merge. **Any false `CAPABILITY_FIT` is P0.**

This document is the **parent semantic barrier**: Wave-B writers do not begin until the decisions in §4 are frozen. It also records each finding's adjudication (VERIFIED / REFUTED / PARTIAL / PENDING) with reproduction evidence — never the prompt's word as proof.

---

## 1. Repository & CI truth (verified, not assumed)

- HEAD `f8fe8bd`, working tree clean, local == `origin/feat/v0.9-capability-compiler`. Branch did not move; the prompt's coordinates are real.
- **Hosted CI on `f8fe8bd` is INFRASTRUCTURE-DEAD, not a code result.** All three jobs (`test (3.10)`, `test (3.12)`, `Optional PySCF backend (smoke)`): `runner_id=0`, `runner_name=""`, `steps_count=0`, `steps=[]`, started+completed within 2 s (13:15:24→:26). **No runner ever executed a step.** This is neither a passing suite nor a code-test failure. Preserve the distinction; never launder it either direction. Gate evidence is from the local OOM-safe runner (`scripts/run_suite.sh`), re-run under this audit.

---

## 2. Findings ledger

Legend: **VERIFIED** (reproduced on the real branch) · **PENDING** (delegated Wave-A lane running) · **REFUTED** · **PARTIAL**.

### Resource conservation

| ID | Claim | Status | Evidence (file:line) | Root cause |
|----|-------|--------|----------------------|------------|
| **F41** | Repeated procedure-material quantities undercounted | **VERIFIED** (read) | `requirements.py:358` — `if group["quantity"] is None and use.quantity is not None: group["quantity"]=use.quantity` | First-value-wins grouping; commensurable repeated uses are never summed (25 mL twice → 25; water 55+10+25 → 55). |
| **F42** | Finite stock spent more than once | **VERIFIED** (read) | `assess.py:358` `_material_axis` loops each requirement independently; `:312` `_material_item_status` checks each vs the WHOLE inventory for the best verdict — no depletion, no capacity ledger | One 30 mL bottle witnesses two 20 mL demands = FIT twice; whole path needs 40 mL. |
| **F50** | Grouping loses distinct uses | **VERIFIED** (read) | `requirements.py:332-374` — group key = structure/name only; phase/formulation/quantity take first non-None | Two uses of one species at different role/phase/concentration collapse to one requirement carrying the first values. |

### Material semantics / identity

| ID | Claim | Status | Evidence | Root cause |
|----|-------|--------|----------|------------|
| **F43** | Formulation authored then erased | **VERIFIED** (read) | `requirements.py:354-355` reads `use.formulation` into the group; `MaterialRequirement` (`:60-82`) has **no** formulation field; `assess._material_item_status_one` (`:249`) gates only assay/phase/quantity | Formulation never reaches assessment → 1% NaHCO₃ clears a 5% wash, unsaturated brine clears saturated, hydrated MgSO₄ clears anhydrous. |
| **F44** | Structure-known requirement downgrades to name matching | **VERIFIED** (read) | `assess.py:242-246` `_match_interval` — identity present but absent from the bottle → falls through to the name key and returns a FIT | A bare name stands in for proven structure. |
| **F53** | Structure-keyed stock must remain stronger than name-keyed (end-to-end) | **VERIFIED** (read, same mechanism as F44) | as F44, through `assess()` | Same downgrade, surfaced end-to-end. |

### Derived data

| ID | Claim | Status | Evidence | Root cause |
|----|-------|--------|----------|------------|
| **F46** | `DERIVED_WITH_ERROR` is prose, not machine-checkable; NaCl mass-fraction arithmetic wrong; NaHCO₃ `±0.5%` decorative | **VERIFIED** (Lane C / daniel, exact-rational + mpmath, instrument calibrated on Basel/log2) | `material_library.py:316` NaCl `[0.23,0.27]`; `:286` NaHCO₃ `±0.5%` | NaCl: `26.3/(26.3+100)=263/1263=`**`0.2082`**, entirely below the coded band (used g/100g-solvent as solution mass fraction). NaHCO₃ `±0.5%`: no derivation behind the width → ASSUMED/decorative. Bonus: isoamyl-dilute `[0.02,0.03]` has the same division bug (`2/102,3/103`, small mag, phase-gated so doesn't flip a verdict). `wash_water [0.99,1.0]` has no number at all → assumed. 5 intervals (acetic/H₂SO₄/vinegar/isoamyl-assay/MgSO₄) reproduce exactly. |
| **F55** | Derived arithmetic belongs in the mutation family | **PENDING** (Lane C informs; gate work) | — | Property tests for the standard transforms; a wrong formula must be killable. |

### Unknownness

| ID | Claim | Status | Evidence | Root cause |
|----|-------|--------|----------|------------|
| **F47** | Unresolved hazard coexists with `CAPABILITY_FIT` | **VERIFIED** (read) | `assess.py:657-660` passes `hazard_unresolved` as `extra_reasons` (display only); `_membership_axis` computes status from the subset check alone; `requirements.py:425` docstring admits "never an overall UNKNOWN" | An unresolved required-material hazard never caps containment → FIT rides over it. |
| **F48** | Unknown condensed byproduct classified `AQUEOUS_NEUTRAL` | **VERIFIED** (read) | `requirements.py:527-535` — `elif is_real_hazard: HAZARDOUS else: AQUEOUS_NEUTRAL`; `is_real_hazard=False` includes `hazard_name is None` (unassessed) | UNKNOWN laundered to benign-by-negation. Violates "UNKNOWN ≠ safe/benign/zero". |
| **F49** | Workup waste missing from the capability question | **VERIFIED** (read) | `requirements.py:508-536` `_waste_requirement` iterates `handling.all_byproducts` only; never consumes procedure `material_uses` | Washes, brine, drier, spent organic layers contribute zero waste obligation. |

### Genericity

| ID | Claim | Status | Evidence | Root cause |
|----|-------|--------|----------|------------|
| **F45** | Isopentyl-specific logic embedded in the generic requirements compiler | **VERIFIED** (read) | `requirements.py:225-239` `_KNOWN_LEAF_IDS={acetic_acid,isoamyl}`; `:299` `"glacial" in text`; `:304`/`:312` hard-coded `StockQuantity.of("20"/"15","mL")` | A corpus adapter squatting inside the generic layer; reactant specs computed by leaf-digest match + runtime prose scan instead of authored source evidence. |

### Topology / API / transport

| ID | Claim | Status | Evidence | Root cause |
|----|-------|--------|----------|------------|
| **F51** | Convergent-DAG capability request accepted but silently unassessed | **VERIFIED** (Lane E) | `RankedDAGSummary` (service.py:1291) has no capability field; `of_dag`/`ranked_dag_dossiers` (:1400/:1456) take no `capability_profile`; DAG call site `service.py:2870` never threads `request.capability_profile`; no refusal in `build_recompile_request`. Live: request carries the profile, response has no capability trace, not even a diagnostic line | Silent drop. Fix = Option-B typed REFUSAL (small, localized); full DAG capability impl is NOT small. |
| **F52** | `compile --capability-profile` honored in JSON, ignored in human output | **VERIFIED** (Lane E) | `_cmd_compile` (cli.py:586) builds the resolved request; `--json` → `run_compilation` carries capability; human falls through to legacy `compile_synthesis()` (experiment/compile.py:306) with ZERO capability refs. Contrast `recompile` human → `_render_recompile_response`→`render_capability_lines` (cli.py:420). Live: human grep "capab" = 0 matches; `--json` = full assessment | Two execution paths; capability question depends on output mode. Fix = delegate `compile` human to `_render_recompile_response`. |
| **F54** | Legacy v0.8 response migration unproven | **PARTIAL** (Lane E) | codecs read every capability field via `.get(key, None)` → live-probed stripped-v0.8 response loads with profile/digest/assessment = None, no crash, no fabrication. BUT the 4 schema constants (REQUEST/RESPONSE/RANKED_ROUTE_SUMMARY/RESPONSE_DESCRIPTOR) were NOT bumped when capability landed (`b79f4dc`), so the "strict schema gate" gives zero protection; only a request-level old-payload test exists (`test_v0_9_capability_transport.py:116`), no response-level test, no committed v0.8 fixture | No live correctness bug today; a real convention/coverage gap. Fix = bump the 4 schema constants + add response-side migration test; real v0.8 fixture → 0.9.5 corpus. |

### New holes (beyond F41–F55)

| ID | Claim | Status |
|----|-------|--------|
| **F56** | Process-axis per-dimension launder (NEW) | **VERIFIED** (Lane G) — real `assess()` on the real route | `_process_axis` (assess.py:493-516) relabels UNCONSTRAINED→UNKNOWN only when `ProcessBounds.constrains_anything`==False; once ANY dim is bounded, the delegate checks each dim only `if bounds.<dim> is not None` (process_constraints.py:401+), so a demand on an unbounded dim is silently unchecked → FIT. `_bench_process_bounds()` (used by EVERY preset incl. the FIT positive; presets.py:85-93) bounds attention+agitation but NO time → a ~69-day route rode to FIT. The Wave-C F1 per-dim loop was never ported here. | Per-dimension fail-close missing on the process axis; same class as F1. Fix: mirror the F1 loop (Decision 11). |

Lane G also proved **F42** and **F47** end-to-end against the real searched isopentyl route + real `assess()` (one 20 mL bottle certifies two 15 mL draws = FIT; an HF-class unresolved hazard rides to FIT), and **refuted** the sibling worries (`_MATERIAL_RANK` cross-bottle laundering — per-bottle gates combine before the best-across rank, so the hole is strictly CROSS-requirement = F42; monetary/physical residuals; gated-but-silently-FIT). **Search noninterference CONFIRMED CLEAN — PRESERVE.**

---

## 3. Nine findings already VERIFIED by reading, before any subagent reports

F41, F42, F43, F44, F45, F47, F48, F49, F50 — structurally confirmed at `f8fe8bd` (§2). The mechanical discriminator repros (real objects, real functions, actual wrong output) are in flight to become the M41–M60 gate. The "never a false pass" claim is therefore already false and is retracted on the PR.

---

## 4. Parent semantic barrier — frozen decisions

Writers consume these as frozen APIs. `PENDING` decisions await a Wave-A lane and are finalized before the owning writer starts.

1. **Material-use conservation law (F41/F50).** Material demand is conserved across procedure operations: repeated *commensurable* uses of one species **sum**. The evaluator never parses "twice"/"55+10" from prose — fix the **source** representation (individual `ProcedureMaterialUse`s, or a typed multiplicity). Distinct semantic specs (different phase/formulation/role) do **not** collapse; the grouping key includes the material specification, or individual uses are retained and only provably-compatible demands are combined by the allocation layer. **No "first value wins."**

2. **Stock-allocation law (F42).** Material inventory is a **finite resource**: a requirement consumes quantity; a stock item has finite capacity and cannot be double-spent; several compatible bottles may jointly satisfy a demand when units/specs are commensurable; unknown stock amount → UNKNOWN where quantity matters; incompatible units → UNKNOWN (no conversion engine). **Algorithm:** for the current semantic domain (same-unit commensurable demands) a per-unit **aggregation** suffices — group demands by commensurable unit + compatible spec, sum required, sum compatible-stock capacity, compare; total demand > available compatible capacity → BLOCKED; unknown/incompatible → UNKNOWN. Bipartite max-flow is the general form, adopted only if multi-spec compatibility graphs actually appear. **Invariant:** one 30 mL bottle must NOT satisfy two independent 20 mL demands; two compatible 25 mL bottles MAY satisfy 40 mL.

3. **Material specification type (F43).** `MaterialRequirement` gains a typed spec (never string equality, never fuzzy prose): required phase; component-fraction constraint (interval/floor); assay interval/floor; hydration/formulation state where independently load-bearing; saturation requirement where represented. Physically-meaningful constraints preferred over vocabulary tags. `StockMaterial` minimally extended (not a new material type) to carry the matching typed fields. Unknown formulation stays UNKNOWN. **Compatibility:** a stock spec satisfies a requirement spec iff each constrained dimension is provably within/compatible; any unprovable dimension → UNKNOWN; any provable violation → BLOCKED. Kills M44/M45/M46/M47.

4. **Structure-vs-name evidence order (F44/F53).** If `requirement.identity` is a known Molecule, a **FIT requires structure-keyed evidence**. Name fallback may supply provenance/display or UNKNOWN candidate info — **never** a structure-level FIT. Name-keyed matching is valid only where `requirement.identity is None` (unresolved ionic/mixture). Kills M48.

5. **Typed derived-evidence representation (F46/F55) — FROZEN (Lane C).** `DerivedIntervalEvidence`: exact-rational value/interval; **`unit` as a TYPE** distinguishing *mass-fraction-of-solution* from *mass-per-100 g-solvent* (the exact confusion behind the NaCl bug); source locator(s); `derivation_method` enum (SOURCE_QUOTED | UNIT_CONVERTED | CLAMPED | COMPLEMENT | BROADENED | ASSUMED); `derivation_inputs`; a **callable, testable `derivation_fn`** (a test asserts `derivation_fn(inputs) == interval`); domain of validity; derivation id. Concrete fixes owed (Writer 4): NaCl `[0.23,0.27]` → honest value (`263/1263=0.208` from its own premise, or re-source as solution-wt%; recompute the water complement); NaHCO₃ `±0.5%` → source a real bench-prep tolerance or relabel ASSUMED; isoamyl-dilute `[0.02,0.03]` → fix the same division bug; `wash_water [0.99,1.0]` → relabel ASSUMED. **No inventing precision to keep a fixture pretty.**

6. **Hazard-unknown propagation (F47).** The capability question is "what containment/waste capability does this route **require**?", not "is it safe?". If a required procedure-material's hazard status is insufficient to determine its containment/waste requirement, that axis = **UNKNOWN**, not FIT. A safety disclaimer cannot turn an unassessed capability *need* into a pass. `hazard_unresolved` must move the axis to UNKNOWN, not merely append a reason. Kills M49.

7. **Waste-unknown / spent-stream semantics (F48/F49).** `AQUEOUS_NEUTRAL` is earned **only** from positive evidence sufficient for that classification. "No non-empty GHS record" → **UNKNOWN** waste stream, never benign-by-negation. Extend `WasteRequirement` with an unresolved-streams channel; the waste axis becomes UNKNOWN if any required stream's routing is unresolved. Workup/spent streams contribute a waste obligation where the source shows spent material; unknown composition → UNKNOWN (no guessed chemistry). Kills M50/M51. **This may turn the isopentyl FIT positive UNKNOWN if the source supplies no disposal info — accept that. A vanishing positive is scientific information.**

8. **DAG capability scope (F51) — FROZEN (Lane E).** `capability_profile is not None AND grammar == CAPPED_SCISSION_CONVERGENT` → **typed REFUSED** with a precise diagnostic, guarded at `build_recompile_request` or the top of the `_run_recompile` DAG branch (~service.py:2860). The search engine still runs DAG without a profile (not a regression). A full DAG capability impl is NOT small (needs DAG-topology-aware requirements) — refuse now, build post-1.0. Kills M53.

9. **CLI alias authority (F52) — FROZEN (Lane E).** The deprecated `compile` alias's HUMAN path delegates to the same `_render_recompile_response`/`render_capability_lines` path `recompile` already uses (cli.py:420), not the legacy `compile_synthesis()` that carries no capability. Pin: same request, same exit code, same overall + per-axis capability, human ≡ JSON, under every profile. Kills M54.

11. **Per-dimension fail-closed is a FOLD CONTRACT, not a per-axis afterthought (F56; the shape of F42/F47).** The Wave-C F1 law — *a modeled route demand on a dimension the profile leaves unmodeled → UNKNOWN, never FIT* — currently lives only in `_physical_axis`. It must be a contract every axis honors: (a) `_process_axis` gets the same per-dimension loop (kills F56); (b) F42 is the same law over material CAPACITY (demand meets exhausted/unmodeled stock → BLOCKED/UNKNOWN); (c) F47 is the same law over the hazard/containment channel (an unresolved required hazard is an unmodeled demand → UNKNOWN). A demand that meets an unmodeled or exhausted capacity never rides to FIT.

10. **Held-out genericity law (F45).** The generic requirements compiler carries **no** target/reagent-specific identities and **no** runtime prose scans. Reactant material semantics move to the **source** `ProcedureEvidence`: typed `ProcedureMaterialUse`s for REACTANT/SUBSTRATE/CATALYST/SOLVENT/WASH/DRY/RINSE. The generic compiler joins route structural identity + procedure material spec without knowing what "isopentyl" is. Remove `_KNOWN_LEAF_IDS`, the `"glacial"` scan, and hard-coded 15/20 mL logic **iff** the replacement proves equivalent. Kills M55/M56. **Held-out control (Lane F):** a benign held-out `ProcedureEvidence` built only from public types must project its material requirements correctly without adding its identity to `requirements.py`.

---

## 5. Mutation gate growth — canonical M41–M60

> Reconciliation: the mission prose under F45 references `M47`/`M48` for held-out-genericity controls, which **collide** with the M41–M60 list's `M47`/`M48`. The **M41–M60 list below is authoritative**; the F45 held-out controls are **M55/M56**. No colliding mutant is authored.

M41 repeated `ProcedureMaterialUse` keeps first, not whole-route sum (F41) · M42 one finite bottle satisfies two demands exceeding capacity (F42) · M43 compatible bottles fail to combine toward one demand (F42/allocation) · M44 formulation erased before assessment (F43) · M45 hydrated drying agent satisfies ANHYDROUS (F43) · M46 wrong concentration satisfies 5% wash (F43) · M47 unsaturated salt solution satisfies saturated-brine (F43) · M48 structure-known requirement FITs name-only evidence (F44) · M49 `hazard_unresolved` merely displayed while containment stays FIT (F47) · M50 unknown condensed byproduct becomes `AQUEOUS_NEUTRAL` (F48) · M51 workup waste streams omitted, overall waste FIT (F49) · M52 two distinct uses of one material deduped by identity alone (F50) · M53 DAG capability request accepted but assessment absent (F51) · M54 `compile --capability-profile` human ignores capability while JSON honors it (F52) · M55 generic requirements compiler knows special target/reagent identities (F45) · M56 runtime `"glacial"` free-text manufactures a requirement (F45) · M57 NaCl solubility `g/100 g water` treated as total-solution mass fraction (F46) · M58 unsupported/decorative uncertainty accepted as `DERIVED_WITH_ERROR` (F46) · M59 old v0.8 response silently gains v0.9 capability semantics (F54) · M60 source-substituted `ProcedureMaterialUse` remains semantically unchanged (F43/F50). Continue beyond M60 for every Lane-G finding. **M1–M40 retained and re-run.** No mutant counts unless honest code passes AND the injected bad behavior fails on a real discriminator.

---

## 6. Wave-B writer ownership (one writer per file)

1. **procedure/material evidence** — `smartchem/procedure_evidence.py` (typed reactant uses, repeated quantities/multiplicity, eliminate runtime prose semantics; no fabrication).
2. **material specification + allocation** — capability material-requirement model + allocation evaluator + tests (formulations, quantity conservation, no double-spend, structure/name authority, commensurable-unit allocation).
3. **capability requirements/assessment** — `smartchem/capability/requirements.py` + `smartchem/capability/assess.py` (generic projection, hazard UNKNOWN, waste UNKNOWN, spent-stream, no target-specific identities).
4. **derived evidence/data** — typed derived-observation helper + `smartchem/data/material_library.py` + data-validation tests (correct every verified arithmetic defect; do not change intervals merely to keep the FIT positive alive).
5. **service/topology/CLI** — `smartchem/service.py` + `smartchem/cli.py` + `smartchem/plan.py` + transport tests/goldens (DAG fail-closed or full impl; compile alias parity; legacy wire behavior; no search-interference regression).
6. **adversarial evidence** — mutation harness + funnel + hostile corpus + audit/ROADMAP/PR release evidence after semantics freeze (no production files).

Integration order (parent = integration authority): procedure evidence → material semantics → capability core → service → gates/docs. Focused tests after every integration. PR #93 stays open + unmerged throughout.

---

## 7. Wave-A lane returns + critical integration laws

**⚠ CRITICAL INTEGRATION LAW (F41 ↔ F42 coupling).** F41's undercount currently *masks* F42: a same-species-same-key auxiliary charged twice is collapsed to one demand, so the double-spend never fires. **Fixing F41 (sum) without F42 (finite-pool allocation) in the SAME change converts an undercount into an unguarded double-spend — net safety goes DOWN.** Land M41 and M42 together or not at all.

**Fold contract (Decision 11).** F56 (process), F42 (material capacity), F47 (hazard channel) are the *same* per-dimension fail-closed law leaking through three axes. The F1 physical loop is the correct pattern — generalize it, don't admire it.

**Search noninterference — CONFIRMED CLEAN (preserve):** `compile_capability_requirements` reads only `route`; `routes.py`/`step.py` import nothing from `smartchem.capability`; no capability module references `semantic_digest`/`search_routes`.

**Mutation gate addition: M61** — a partial `ProcessBounds` launders an unmet time/active/equipment/check-interval demand from UNKNOWN to FIT (F56). Mirror-of-F1 fix must kill it.

## 8. Status log

- 2026-09-28 16:36Z — PR #93 → `[EXTERNAL AUDIT HOLD]` (REST PATCH; `gh pr edit` blocked by GraphQL projectCards deprecation). 9 findings VERIFIED by reading; barrier decisions 1–4, 6, 7, 10 frozen.
- 2026-09-28 ~16:5xZ — all 4 Wave-A lanes returned. F46/F51/F52 VERIFIED, F54 PARTIAL, **F56 NEW+VERIFIED**; search noninterference confirmed clean; sibling worries refuted. Decisions 5, 8, 9 frozen; Decision 11 (per-dimension fold contract) added. **Wave B dispatched:** parent takes the capability core (`requirements.py`+`assess.py`+ material spec/allocation + `stock.py` two-sided band); Writer 1 `procedure_evidence.py`+isopentyl source uses; Writer 4 `material_library.py`+`DerivedIntervalEvidence`; Writer 5 `service.py`/`cli.py` (F51/F52/F54). PR #93 stays open + unmerged.
- 2026-09-28 (core landed) — Parent CORE implemented + re-adjudicated on the real searched route. Writer A (material_library + `DerivedIntervalEvidence`) + Writer B (service/CLI F51/F52/F54) integrated. Fixes verified in place: F41 summation, F42 finite-pool max-flow allocation, F43 `satisfies_band`, F44 `_species_key_in` (structure-only for resolved identities), F45 generic `_material_requirements` (+ REACTANT/SUBSTRATE roles, `_FORMULATION_SPECS`; `_KNOWN_LEAF_IDS` + glacial scan deleted), F47 containment→UNKNOWN, F48/F49 `WasteRequirement.unresolved`→UNKNOWN, F50 spec-in-key, F56 `_process_axis` per-dimension + honest preset time bounds. ruff clean. Data fix: `wash-water-distilled` structure-keyed (F44 correctly demanded it). Test/gate reconciliation + mutation gate M41–M61 dispatched.
- 2026-09-28 (Round IV CLOSED) — all Wave-B writers + Wave-C integrated. **Mutation gate re-run INDEPENDENTLY by the parent: 60/62 killed, 0 survived** (M23 RETIRED — F45 deleted the mechanism it patched; M50 VERIFIED-DEFER — F48 branch real but corpus emits no unassessed byproduct, its cap killed on the real path by M51); the committed M1–M40 harness was found BROKEN on the new core (7 mutants patched deleted functions / asserted the retired FIT contract) and repaired. **Funnel 86/86 properties, zero `CAPABILITY_FIT` under every profile**, denominators never narrowed. Wave C (amber): **F62** (P0) FIXED — the process per-dimension fail-close is now a COMPLETE table `_PROCESS_FAILCLOSE_DIMENSIONS` (attention + agitation were dropped); **F63** (LOW) deferred to 0.9.5; else HELD, search noninterference re-confirmed clean. 4 stale contract tests in other files reconciled to the new contract (`test_procedure_material_use` roles/census — F45; `test_process_synthesis` compile render — F52). **Full OOM-safe suite GREEN.** Docs finalized (this record + ROADMAP Round-IV block + PR #93 body + 0.9.5 plan). Package stays `0.9.0a1`; PR #93 OPEN + UNMERGED for another external-review pass — the vanished FIT positive is external review's material call.

---

## 9. Re-adjudication — the FIT positive collapses to UNKNOWN (the round's pivotal outcome)

Re-run on the **real searched isopentyl-acetate route** with every fail-closed gate live:

| profile | overall | non-clearing axes |
|---|---|---|
| `isopentyl_capability_fit_bench()` (fully-declared) | **UNKNOWN** | process, containment, waste |
| `research_lab(material_inventory=…)` | **UNKNOWN** | process, containment, waste |
| `poor_man()` | **BLOCKED** | containment + measurement (hard); material/process/waste |

**No corpus route reaches `CAPABILITY_FIT`.** The fully-declared bench clears material, equipment, physical, measurement, procurement (monetary UNCONSTRAINED; ventilation/attention_care N/A) — but collapses to UNKNOWN on exactly the three axes where the **source under-specifies**:

- **process (F56)** — the sourced procedure times only the 1-hour reflux **floor** (`min_elapsed_minutes=60`); the whole-step elapsed **ceiling** (untimed workup + fractional distillation) is undeclared. No bench can certify it completes a process of unknown duration → UNKNOWN. The Round-III FIT rode the "process-time omission = unlimited patience" reading that F56 retires; fabricating a duration is banned.
- **containment (F47)** — the ionic auxiliaries (NaHCO₃/NaCl/MgSO₄, `identity=None`, no sourced GHS record) have unresolved hazards, so the containment capability they require cannot be determined → UNKNOWN (not a safety-disclaimered pass).
- **waste (F49)** — the spent workup streams have no sourced disposal routing → UNKNOWN (not `AQUEOUS_NEUTRAL` by negation).

This is **accepted, per the mission** ("a vanishing positive is scientific information … do not weaken the gate to preserve the positive … truth over version aesthetics"). Sourcing the (genuinely benign) auxiliary hazards would clear containment but **not** process → no honest FIT exists on this corpus. **0.9's release statement reflects this ceiling:** `CAPABILITY_FIT` is rigorously defined and every axis fails closed; no corpus route currently reaches it because the sourced procedures under-specify whole-process duration, auxiliary hazards, and spent-stream disposal — which names exactly what 1.0 must source. The forcing matrix's discriminating power is preserved: each targeted negative still **BLOCKS** on its removed axis (containment / equipment / measurement / material / material / procurement), proving the removal bites.

---

## 10. Wave C — fresh non-author hostile review (amber)

A fresh adversary that authored none of the fixes attacked the frozen core and found ONE P0 + one LOW residual; everything else HELD under real probes:

- **F62 (P0, VERIFIED → FIXED)** — `_process_axis`'s per-dimension fail-close (F56) enumerated only 3 of the 5 process-unique dimensions (elapsed, active, check-interval) and DROPPED attention + agitation. A `custom()` bench that bounds some process dimension but leaves `allowed_attention`/`allowed_agitation` = None let a route demanding `Attention.CONTINUOUS`/`Agitation.CONTINUOUS` ride to process FIT → overall `CAPABILITY_FIT` (proven on the real `assess()` path; the 3 shipped presets were NOT vulnerable — `_bench_process_bounds()` declares all modes). **FIXED:** the per-dimension fail-close is now driven off a COMPLETE module-level table `_PROCESS_FAILCLOSE_DIMENSIONS` (attention + agitation included), so no dimension can silently fall off a hand-written checklist (the F62 root cause). Verified: the exploit → UNKNOWN; the isopentyl positive + presets unchanged. Mutant **M62** added.
- **F63 (LOW, VERIFIED → DEFERRED to 0.9.5)** — `DerivedIntervalEvidence.__post_init__` enforces `derivation_fn(inputs) == interval` (arithmetic reconstruction — kills the NaCl unit bug, M57/M58) but NOT the provenance of a band's WIDTH: a decorative-but-arithmetically-consistent band mislabeled `DERIVED`/`BROADENED` (should be `ASSUMED`) constructs fine. A data-layer mislabel that does NOT by itself yield a false capability FIT (the numeric gate is identical whatever the method label), so **not release-blocking**; the honest guard (a `width_source`, or requiring `ASSUMED` for an unsourced `symmetric_band`) is a 0.9.5 item.
- **HELD under real probes:** the finite-pool allocation (no cross-spec double-spend; float-epsilon sound; an unknown-capacity bottle only degrades BLOCKED→UNKNOWN, never lifts to FIT); `satisfies_band` (straddle→UNKNOWN, degenerate `low==high` correct); F44 keying (no name-for-structure path); F45 generic projection (no target identity / prose scan on the live path); the fold contract on the other axes; **search noninterference re-confirmed clean** under Round IV.

**Structural lesson (amber's nag, adopted):** the per-dimension fail-close law was a hand-enumerated checklist in two places (physical F1, process F56) — one forgotten line from a false FIT, and F62 was exactly that. The process axis is now table-driven; the physical axis is complete by construction over its three `_BOUND_NAMES`. 0.9.5 re-attacks any future added dimension.
