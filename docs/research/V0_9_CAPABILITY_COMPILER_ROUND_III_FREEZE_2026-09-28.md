# SmartChem 0.9 — Capability Compiler ROUND III · PARENT-BARRIER SEMANTIC-HARDENING FREEZE (2026-09-28)

**Branch** `feat/v0.9-capability-compiler` (off `main@df1b38d`, `0.8.0a1`). **Version stays `0.8.0a1`** until the
0.9 gate closes. This is the frozen contract Wave B builds against; it **supersedes**
`V0_9_CAPABILITY_COMPILER_ROUND_II_FREEZE_2026-09-28.md` wherever they disagree, and every disagreement below is a
deliberate correction forced by the Round-III read-only hostile gate (four independent Wave-A bearings + the parent's
own source read of `requirements.py`, `assess.py`, `enums.py`, `stock.py`, `presets.py`, `profile.py`,
`affordability.py`).

Round II shipped a *real* capability core and a *reachable* `CAPABILITY_FIT` positive. It also shipped six lies of
omission and one lie of convenience. Round III is not "invent more capability types." It is: **make the machine mean
what it says.** The gate is allowed to get harder. Truth beats a prettier matrix.

The 0.9 law, unchanged and inviolable: **the SAME `ExperimentRoute` is projected through profiles; capability is a
projection, never a second chemistry engine; intrinsic `RouteReadiness` and chemistry search stay profile-independent.**

---

## Baseline pinned before any edit (regression anchor)

- `Observed[.venv pytest → tests/test_v0_9_capability_core.py + _fit_positive + _presets + test_stock + test_v0_8_procedure_evidence → 93 passed, exit 0, 26.13s]`.
- `Observed[git: tip 14311a9, main df1b38d, branch ahead 9 / behind 0, tree clean, no 0.9 PR, no hosted CI run on 14311a9]`. The "hosted CI has no status" distinction is preserved.

---

## Wave-A findings that OVERTURN or SHARPEN Round II (read first — receipts attached)

- **G1 (RF3) — UNCONSTRAINED rides to FIT. `Verified[assess.py:298-299, 471-490]` + runnable exploit.** `_physical_axis`
  returns `UNCONSTRAINED` the instant the profile ceiling is all-`None`, *without ever reading the route's real demand*.
  The fold diverts only on `BLOCKED`/`UNKNOWN`; `UNCONSTRAINED` falls through to `FIT`. A route declaring a 383 K peak +
  a profile with no thermal ceiling → physical `UNCONSTRAINED` → overall `FIT`. **Aggravator `Verified[presets.py:88,124,171]`:**
  research_lab(), poor_man(), AND custom() default `physical_bounds`/`process_bounds` to `unconstrained()`, so physical
  AND process go `UNCONSTRAINED` for *every* front-door assessment. False-FIT is caught only by an accidental other-axis
  block. This is the "bench silently claims it can hit any temperature/time" fabricated pass — NOT the legitimate "axis
  outside the question."
- **G2 (RF4) — budget denomination unenforced. `Verified[assess.py:388 vs affordability.py:281]`.** `_monetary_axis` guards
  `currency` but never reads `route_cost.unit`/`budget.unit`. `CostVector` *carries* the `unit` denominator, and
  `dominates` (`affordability.py:281`) already refuses `(currency,unit)` mismatch — the capability axis forgot the guard
  its own module documents as a known red-team trap. poor_man budget `unit="USD"` (total) vs `basket_cost_vector` output
  `unit="metric ton"`/package → compared by raw number → false FIT/BLOCKED.
- **G3 (RF1) — universal esterification assay floor. `Verified[requirements.py:234-294]`.** The `0.98` floor fires on
  *every* leaf of *any* step the oracle stamps `"acyl condensation (esterification/amidation)"` — class-scoped, not
  source-scoped. It fabricates a universal material requirement from one procedure's `glacial`-acetic evidence, and the
  entire gate-#18 FIT positive is load-bearing on it.
- **G4 (RF2) — measurement disappears. `Verified[requirements.py:433, enums.py:120-135]`.** `measurement=frozenset()`
  always; `MeasurementCapability` is 3 coarse tiers its own docstring calls "structurally UNUSED." VERIFY ops carry
  `apparatus=()`; the method lives in free-text `analytical_verification`. Corpus census: exactly 3 `ProcedureEvidence`
  objects (isopentyl / aspirin / paracetamol); methods named = weigh (all 3), melting point (aspirin+paracetamol), IR
  (isopentyl only), FeCl₃ spot test (aspirin only, reagent-based). `IR → ANALYTICAL_INSTRUMENT` is the one discriminating
  method poor_man lacks.
- **G5 (RF5) — ventilation decorative. `Verified[assess.py:453-464]`.** `assess()` folds 10 axes; ventilation is not one.
  `profile.ventilation` is never read. M6 (outdoors≠hood) *does* hold structurally (containment reads `profile.containment`
  only).
- **G6 (RF6 / Round-II F3) — procedure-only species escape. `Verified[requirements.py:263-294, 297-316]` + census.**
  Material reads `route.leaf_inputs` only; hazard/containment reads balanced species only. Procedure-only auxiliaries
  (H₂SO₄ catalyst, NaHCO₃/NaCl/MgSO₄ washes+drier, water) are invisible to every structured axis. **Structural constraint:**
  the salts are ionic → unresolvable to `Molecule` (SMILES parser refuses disconnected species, `Verified` by live probe);
  H₂SO₄ resolves but has no `hazards.py` GHS record.
- **G7 (M25/M26) — quantity/phase inert. `Verified[assess.py:250, stock.py:344]`.** `_material_item_status` passes only
  `(identity, min_assay)` to `satisfies()`. `MaterialRequirement.quantity`/`.phase` are always `None` and never read.
  `StockQuantity` is `(value:str, unit:str)` with NO comparison/conversion layer.

---

## THE THIRTEEN FROZEN DECISIONS

### D1. Material requirement SOURCE LAW (kills M23; retires the universal floor)

**RETIRE** `_ESTERIFICATION_CLASS_NAME`/`_ESTERIFICATION_REQUIRED_ASSAY`/`_esterification_required_leaves` — the
class-keyed `0.98` floor is deleted. No reaction-class label may ever manufacture a material assay requirement.

Assay/formulation requirements are **source-scoped per input**, in descending preference:
1. **Sourced formulation term → formulation requirement (option B).** "glacial acetic acid" is a compendial term with a
   defensible assay domain (USP/ACS glacial ≥ 0.99 mass fraction). The acetic-acid leaf gets a `DERIVED_WITH_ERROR`
   assay tied to the *sourced word* "glacial" (cite the compendial spec), NOT to the reaction class. This is the gate-#18
   discriminator: it is what makes vinegar (≈5%) BLOCK and glacial (≥0.995) FIT.
2. **Sourced quantity+moles → derived near-neat (option A).** Where the source gives a per-material mass/volume **and** a
   molar amount whose ratio through the sourced molar mass implies a near-neat reagent within honest sig-fig+density
   uncertainty, derive a `DERIVED_WITH_ERROR` interval (wide, honest). The material writer resolves whether the isopentyl
   source page gives per-material moles for the alcohol; **if it does not, the alcohol assay requirement is `None`.**
3. **Neither → `required_assay=None` (honest UNKNOWN).** Never assume 100%. An input with `None` assay yields material-axis
   `UNKNOWN` unless established another sound way (D3 possession/formulation).

**Consequence, embraced:** the FIT positive migrates off `research_lab(material_inventory=…)` onto a **fully-declared
Custom** whose declared `StockMaterial`s satisfy the source-scoped requirements. If an input honestly cannot earn a
source-scoped requirement and that leaves it UNKNOWN, **the positive stays UNKNOWN and the release record says exactly
why. Do not fabricate a number to force FIT.**

**The isopentyl-acetate positive, concretely (the mechanism that keeps FIT honest AND preserves gate-#18 discrimination
without the retired floor):** compatibility is established by **phase/formulation (D4)**, which is the mission's option-C
"some OTHER sound way," NOT a fabricated assay:
- **acetic acid** — the sourced word "glacial" is a compendial formulation: a NEAT `Phase.LIQUID` reagent (≥0.99 by the
  USP/ACS glacial spec, `DERIVED_WITH_ERROR`, cited). A phase-`LIQUID` (+ high-assay) requirement is satisfied by glacial
  stock (`Phase.LIQUID`, `[0.995,1.0]`) and **BLOCKED by vinegar** — which is a `Phase.AQUEOUS_SOLUTION` at a few percent.
  Phase alone discriminates glacial from vinegar; assay reinforces it. Gate #18's whole point, preserved.
- **isopentyl (isoamyl) alcohol** — the source names a neat reagent with no numeric purity. Its requirement is
  **phase/formulation** (`Phase.LIQUID`, neat reagent), satisfied by declared reagent-grade `Phase.LIQUID` stock. Only if
  the source's own stoichiometry (its % yield arithmetic treating the alcohol as the near-neat limiting reagent) yields an
  honest, source-backed `DERIVED_WITH_ERROR` assay interval does the material writer add one — and it MUST be
  source-defensible with an honest width, never a decorative ± to force FIT (anti-fabrication rail). Absent that, phase is
  the compatibility mechanism and `required_assay=None` is honest.
- **washes/drier (NaHCO₃, NaCl, MgSO₄)** — `identity=None` (ionic, unresolvable), so matched by the weaker declared-NAME
  key + formulation/phase against name-keyed declared stock (possession, not assay). Undeclared → the material axis for
  that auxiliary is UNKNOWN, never silently skipped.
- **Net:** the FIT positive's material axis is FIT only when the Custom bench declares stock covering every reactant AND
  every procedure-only auxiliary with matching phase/formulation. That is the "$200 and a dream / source-compatible
  inventory" contract, and it is strictly harder than the retired-floor positive.

### D2. Procedure-material TYPE (kills M24)

New typed, SOURCE-authored record (name suggestion `ProcedureMaterialUse`; final name the material writer's) carried on
the procedure evidence (either on `ProcedureOperation` or as a typed companion on `ProcedureEvidence` — **owner's call,
but it is SOURCE evidence, never `CapabilityProfile` data**). Minimum fields forced by the corpus:
- `name: str` — the exact sourced material name.
- `role` — a material-level role **distinct from `OperationRole`**: `CATALYST` / `WASH` / `DRY` / `SOLVENT` / `RINSE` /
  `NEUTRALIZE` (closed vocab; extend only on corpus force). Forced hard: op1 of isopentyl AND aspirin glues a catalyst
  (H₂SO₄) into a REACTION-role op beside true reactants — nothing distinguishes them by type today.
- `identity: Molecule | None` — **honestly optional.** `None` when the species is ionic/mixture/unresolvable (NaHCO₃,
  NaCl, MgSO₄, petroleum ether, charcoal, buffers). A representation that *requires* a resolved structure is unsatisfiable
  for ~half this corpus. Mirrors `required_assay: float | None`.
- `formulation: str | None` / `phase: Phase | None` — the load-bearing adjective ("glacial"/"conc."/"anhydrous"/"5%"/
  "saturated aqueous") as structured data, never re-parsed from prose at runtime.
- `quantity: StockQuantity | None` — populated only where the source gives a cleanly-separable per-material amount
  (see D3); `None` where the source glues quantities ambiguously.
- `evidence_source: str` — the sourced locator.

**Authoring, not parsing:** the 3 `ProcedureEvidence` records in `decompiler_conditions.py` are enriched by hand with
these typed uses (the F3 auxiliaries). `compile_capability_requirements` projects BOTH leaf-reactant material needs AND
procedure-material needs into the ONE material axis — no duplicate inventory type; all assessed against `StockMaterial`.
A procedure material that cannot be structurally resolved is **carried as an explicit requirement, never silently
skipped** (M24 kill = the carry, not a fabricated pass).

### D3. Quantity LAW (kills M25 — participate where sourced, UNKNOWN on unit mismatch)

`MaterialRequirement.quantity` participates. New assess-side unit-aware comparison (a small helper, **no conversion
engine**):
- requirement `quantity` set AND a candidate `StockMaterial.quantity` set AND **same `unit`** → numeric compare (stock ≥
  required → contributes FIT-eligible; stock < required → BLOCKED/INSUFFICIENT).
- units differ with no sound conversion → **UNKNOWN** (never compare incompatible units by number).
- requirement `quantity` is `None` → not a quantity gate (nothing to check; never invents one).
- an unspecified *stock* quantity is **never** assumed sufficient against a real requirement → UNKNOWN.

Where sourced: attribute the cleanly-separable reactant volumes (isopentyl "15 mL alcohol", "20 mL acid") as per-material
`StockQuantity`; leave genuinely-ambiguous glued quantities `None`. This gives M25 a non-vacuous kill and feeds a
targeted-negative (a Custom declaring too little stock → quantity BLOCKED/UNKNOWN).

### D4. Formulation / phase LAW (kills M26)

`MaterialRequirement.phase` (and formulation, where a controlled sourced term forces it) participates in assessment:
- requirement `phase` declared AND `StockMaterial.phase` known → compare; mismatch → BLOCKED.
- `StockMaterial.phase` is `Phase.UNKNOWN` against a declared phase requirement → **UNKNOWN** (unknown phase never silently
  fits a known phase requirement).
- requirement `phase` is `None` → not a phase gate (never fabricate a phase requirement the source doesn't state).

### D5. Measurement capability IDENTITY (kills M27, M28 — specific method, not tier)

New closed **specific** enum (name suggestion `MeasurementMethod`) mirroring `EquipmentCapability`, + a
`MEASUREMENT_TIER_OF: dict[MeasurementMethod, MeasurementCapability]` map mirroring `EQUIPMENT_KIND_OF`. Minimum
corpus-forced members: **`MASS`, `MELTING_POINT`, `INFRARED_SPECTROSCOPY`** — the three genuine *instrument* methods.
- **Comparison is on the specific method, never the coarse tier** (kills M28: a profile with NMR-but-not-IR, both
  `ANALYTICAL_INSTRUMENT`, must not false-FIT an IR requirement). `CapabilityProfile.measurement` is **promoted** to the
  specific `MeasurementMethod` set; the coarse `MeasurementCapability` tier survives as display/grouping via the map.
- **VERIFIED DEFER — the ferric-chloride spot test.** It is reagent + naked eye, not an instrument; forcing it into a
  balance/spectrometer-shaped enum is a category error. Excluded from `MeasurementMethod` for 0.9. **Release boundary:**
  a later round may model reagent-based confirmation as a MATERIAL possession requirement (FeCl₃ solution), not a
  measurement instrument. `PERCENT_YIELD` likewise excluded (arithmetic over `MASS`, not a method).
- **Data enrichment (authoring, not runtime parsing):** the 3 VERIFY ops in `decompiler_conditions.py` get typed
  `apparatus=(…)` strings ("analytical balance", "infrared spectrometer", "melting point apparatus"); a new
  `measurement_resolver.py` mirrors `equipment_resolver.py` (closed alias table, fail-closed 3-way cut). A new
  `_measurement_requirement(route)` filters `op.kind is VERIFY`, collects `op.apparatus`, classifies. A profile missing a
  required specific method → BLOCKED. **Non-vacuous on the forcing positive:** IR makes isopentyl BLOCKED-on-measurement
  under poor_man, FIT under a bench declaring `INFRARED_SPECTROSCOPY`.

### D6. UNCONSTRAINED SEMANTICS (kills M29 — real requirement + no bound → UNKNOWN)

Split the current fall-through. The fold and the axes are corrected so an `UNCONSTRAINED` axis can **no longer contribute
to FIT when the route carries a real requirement on that axis**:
- `_physical_axis`: if the route requirement constrains *something* (a real T/P extremum) AND the profile ceiling is
  all-`None` → **UNKNOWN** ("the bench declared no bound against a real demand"), NOT `UNCONSTRAINED`. Only when the route
  has **no** requirement on the axis → `NOT_APPLICABLE`. `UNCONSTRAINED` is retained **only** for "no route requirement AND
  no profile bound" (genuinely outside the question) — and even that must not, by itself, license overall FIT if any axis
  with a real requirement is unmet.
- `_process_axis`: same law. `evaluate_process_requirements` returning `UNCONSTRAINED` while the route carries real
  time/attention/agitation requirements must relabel to `UNKNOWN`, not ride through. (Delegation preserved; the relabel
  guards the empty-bounds-with-real-requirement case.)
- `_monetary_axis`: budget is genuinely OPTIONAL. No declared budget → the monetary axis is **outside the capability
  question** and does not force UNKNOWN (a caller who didn't ask about money isn't blocked on money). This is the one axis
  where "no bound declared" legitimately rides through — because there is no *safety/feasibility* claim hiding in silence,
  unlike temperature.
- **Fold rule (frozen):** overall `CAPABILITY_FIT` requires every axis that has a *real route requirement* to be `FIT`,
  every axis to be non-`BLOCKED` and non-`UNKNOWN`, AND tier ≥ `PROCESS_SPECIFIED`. An `UNCONSTRAINED`/`NOT_APPLICABLE`
  axis is FIT-compatible **only because it certifies there was nothing to meet** — never because a real demand went
  unread.
- **Presets:** a preset that genuinely *claims* a physical/process capability must declare a **real, finite, defensible
  bound** (a research bench that can reach reflux declares e.g. a real max-temperature ceiling), never all-`None`
  masquerading as capability. All-`None` now honestly reads as UNKNOWN against a real demand. The fully-declared Custom
  FIT positive **must** declare real physical + process bounds ≥ the route's demand. `research_lab`/`poor_man` staying
  UNKNOWN/BLOCKED on physical/process where they declare no bound is the honest, intended outcome. **No preset becomes an
  omnipotent lab through all-`None` bounds.**

### D7. Budget / DENOMINATION SEMANTICS (kills M30, M31)

`_monetary_axis` enforces the same `(currency, unit)` law `dominates` already holds:
- currency mismatch → UNKNOWN (existing, retained).
- **unit/denomination mismatch → UNKNOWN** (new: `route_cost.unit != budget.unit` → incomparable, never compared by raw
  number). A `$/mol-product` or `$/metric-ton` cost vs a total-`$` budget is a denomination mismatch → UNKNOWN, absent a
  production-quantity bridge (which 0.9 does **not** build — no currency/quantity engine).
- matching denomination only → the existing cash/floor comparison.
- unknown price is never `$0` (existing, retained — M14).

poor_man's `unit="USD"` total budget therefore **stops participating** against per-package/per-mol route costs (→ UNKNOWN),
exactly as the mission requires — no calculator error wearing an affordability verdict.

### D8. Ventilation DECISION (kills M32 — explicit reserved, visible)

**Explicit defer, made visible** (option B). No sourced evidence in this corpus forces a ventilation requirement distinct
from containment/off-gas (the waste axis already carries `OFFGAS_CAPTURE`). Therefore:
- 0.9 derives **no** ventilation requirement. `assess()` emits an explicit `ventilation` `AxisResult` with status
  `NOT_APPLICABLE` and a reason that **names it reserved/deferred** ("ventilation: RESERVED — declared but not assessed in
  0.9; no sourced ventilation requirement; OUTDOOR never substitutes for containment"). It is **surfaced**, never a silent
  green check and never dropped.
- `profile.ventilation` is retained as declaration data (the poor-man "outside = poor man's fume hood" ethos), but its
  presence no longer implies an assessed capability — the reserved label makes the scope explicit.
- **M6 stays hard:** OUTDOOR / ventilation NEVER clears a `FUME_HOOD` / containment requirement (containment axis reads
  `profile.containment` only). A test pins it.

### D9. Procedure-material HAZARD POLICY (kills M33; makes it non-vacuous)

Once procedure-material uses are typed (D2), their hazards feed containment/waste **where the identity resolves and a GHS
record exists**:
- procedure-only material with a **resolved identity + a real GHS hazard** → contributes its containment/waste requirement
  (never omitted because it's "procedure-only"). This is the M33 kill.
- procedure-only material that is **unresolvable OR has no GHS record** → its hazard status is **explicit UNKNOWN**, carried
  as a visible `hazard_unresolved` note in the requirement and surfaced in the containment/waste axis reasons + human/JSON
  output. It does **not** fabricate a containment requirement out of ignorance (that would invent a requirement), and it
  does **not** force overall UNKNOWN — because `CAPABILITY_FIT` is explicitly **NOT a safety certification** and the visible
  note bounds the scope honestly ("hazard status of {…} is UNKNOWN"). Silent skipping is the sin; visible-UNKNOWN is the
  fix.
- **Make M33 non-vacuous:** add a **sourced** GHS record for concentrated sulfuric acid to `hazards.py` (H₂SO₄ is genuinely
  corrosive — H314; a citable, DERIVED-with-source enrichment, the exact F3 material the Round-II freeze flagged). With it,
  isopentyl's H₂SO₄ catalyst (procedure-only, resolvable) → contributes a containment requirement → a no-hood profile
  BLOCKS on it, and a mutant that drops procedure-only hazards is caught by a real discriminator. Adding known chemistry is
  not fabrication; the *absence* of the record was the data gap.

### D10. Request profile representation (kills M34, M37) — `Verified[service.py:558,595; 737-758]`

**OVERTURNS Round-II decision 7's `capability_profile: str` field.** A stored name re-resolved against tomorrow's mutable
preset is exactly the M34 drift the mission forbids. Instead, the request stores the **resolved exact content**:
- New field on `CompilationRequest` (service.py:558): `capability_profile: CapabilityProfile | None = None` (the resolved,
  immutable snapshot) + `capability_profile_origin: str = ""` (optional display/preset-origin name, non-load-bearing).
  `CapabilityProfile` is a frozen `Digestible`, so it enters the full `.digest` automatically (`contracts.py:146-154`
  dataclass branch) and is **excluded from the hand-built `semantic_digest` tuple** (service.py:737-758) — the identical
  mechanism that keeps `algebra_profile` (which DOES enter `semantic_digest` via its resolved digest at :753) out is used
  in reverse here: capability is simply never added to that tuple. That exclusion IS search noninterference.
- **DEFAULT = `None` = NOT_REQUESTED (single constant, no legacy split).** Capability has no legacy-compat history, so
  unlike algebra's `DEFAULT_ALGEBRA_PROFILE`/`DEFAULT_ROUTE_ALGEBRA_PROFILE` split there is ONE default and it is "no
  question asked." `smartchem plan TARGET` with no `--capability-profile` performs **no** capability assessment and assumes
  **no** bench (kills M37). A CLI `--capability-profile poor-man` resolves **once** at request-build via
  `resolve_capability_profile(name)` → the resolved `CapabilityProfile` is stored; replay uses that exact stored content,
  never re-resolves (kills M34).

### D11. Custom profile serialization (kills the two-compiler split) — `Verified[service.py:1065 replay_payload pattern]`

Because D10 stores a resolved `CapabilityProfile` (not a name), inline custom and named-preset requests are **the same wire
shape** — a resolved profile is a resolved profile. The transport writer adds JSON codecs for `CapabilityProfile` /
`StockMaterial` / `CapabilityAssessment` (mirroring existing `Digestible` payload round-trips; the seam probe flagged
`request_from_payload`/`response_to_payload` as needing new entries — this is that work). No architecture where named works
through the service but custom only through direct `assess()`. One capability compiler.

### D12. Capability-question digest + rebind (kills M35, M38) — `Verified[service.py:4013-4027 ALGEBRA-REBIND template]`

- `capability_question_digest = canonical_digest((semantic_digest, resolved_capability_profile.digest))` when a profile is
  requested; binds the capability question, not a preset string. The chemistry `semantic_digest` **must not** move under
  profile selection; the full request `.digest` may. The transport writer resolves whether this pin is additive to the
  existing `expected_request_digest` consumer-pin (service.py:~4036) or extends it — **invariant (non-negotiable): the pin
  MOVES when profile content changes and does NOT move when only the search question changes, and never lets the search
  question move under a profile change.**
- `CapabilityAssessment` rides as a new `compare=True` field on `RankedRouteSummary` (real collection name:
  **`ranked_route_dossiers`**, service.py:1018/1043/2138) — so it enters `result_digest` transitively for free, mirroring
  `readiness`. Thick re-derivable evidence rides via the existing `replay_payload` (`compare=False`, service.py:1065).
  `capability_profile` threads as a NEW parameter into `_ranked_summaries()` (service.py:2336) and `of_fit()`
  (service.py:1112), resolved at the service.py:2646 call site from `request.capability_profile` — `of_fit` already has
  `fit.route` and `evaluate_route(...)` in scope, so `compile_capability_requirements(fit.route)` + `assess(profile, reqs,
  readiness)` compute there.
- **`CAPABILITY-REBIND-ON-LOAD`** mirrors `ALGEBRA-REBIND-ON-LOAD` (service.py:4013-4027) but PER-ROUTE against
  `replay_payload` (the same on-load-rederive pattern already used for readiness/process): re-derive the assessment from
  carried evidence + `resolve_capability_profile(request.capability_profile)` and refuse on mismatch — profile A assessment
  under profile B, altered snapshot, altered stock, altered readiness, altered route, altered result (kills M35, M38).
  Thin/advisory mode must not claim `CAPABILITY_FIT` as verified.

### D12a. Human-render + CLI-surface scope (kills M-consistency; criterion 29) — `Verified[cli.py:326-425; plan.py:263-320]`

The seam probe found the freeze prose glossed a real gap: **three CLI surfaces**, only ONE with per-route readiness text.
Round-III scope, frozen:
- `--capability-profile` is accepted on **`plan`** (four-hop cli.py:705→plan.py:103→service.py:855, mirrored 1:1) and
  **`recompile`** (its own `_add_recompile_flags`/`_recompile_request_from_args` threading, cli.py:168/253 — a SECOND
  mirror). `compile` (deprecated alias, separate `compile_synthesis` engine) accepts the flag via the shared request
  builder but its human render is **not** extended (JSON carries the assessment; documented as deprecated-surface).
- **Human render (criterion 29 — human ≡ JSON):** `_render_recompile_response` (cli.py:392-419) gets a `CAPABILITY[profile]`
  line inside its per-route loop, after the READINESS elif-chain, with the scope note. `render_plan_human` (plan.py:263-320,
  the 0.6 front door) gains a per-route READINESS + CAPABILITY block for the first time — this is NEW surface, not a mirror,
  but the front door is the mission's own example (`smartchem plan TARGET --capability-profile …`) and human≡JSON parity
  demands it. Both surfaces render the same capability semantics the JSON exposes; an unassessed/unconstrained/reserved axis
  is shown explicitly, never a green check by omission.

### D13. FILE OWNERSHIP (Wave B — ONE writer per file, dependency-ordered)

Cross-file needs go to the owner as a failing discriminator + required invariant, never a competing edit. Shared
`decompiler_conditions.py` (VERIFY apparatus + ProcedureMaterialUse authoring) has **ONE** designated owner: the
**measurement/procedure-data** writer, which the material writer feeds via invariant, never edits directly.

1. **`agent/v09-material-close`** — `MaterialRequirement` extension (quantity/phase/formulation participation), the
   `ProcedureMaterialUse` type + its material-axis projection in `requirements.py::_material_requirements`, retire the
   esterification floor, source-scoped assay derivation, the `material_library.py` fixture (fully-declared Custom stock +
   targeted negatives). Owns material tests. Does NOT own `service.py`. Does NOT edit `decompiler_conditions.py` (sends the
   procedure-material authoring spec to the measurement/procedure-data owner).
2. **`agent/v09-measurement-close`** — the `MeasurementMethod` enum + `MEASUREMENT_TIER_OF`, `measurement_resolver.py`,
   `_measurement_requirement`, AND the **sole ownership of `decompiler_conditions.py` procedure enrichment** (VERIFY
   `apparatus=` strings + the `ProcedureMaterialUse` records the material owner specs). Owns measurement + procedure-data
   tests. Coordinates all `procedure_evidence.py`/`decompiler_conditions.py` edits.
3. **`agent/v09-capability-core-close`** — `requirements.py` (wire the new axes) + `assess.py` (D3 quantity, D4 phase, D6
   UNCONSTRAINED fix, D7 denomination guard, D8 ventilation axis, D9 hazard-unresolved carry) + `enums.py` additions.
   Consumes the frozen material + measurement interfaces. Owns capability-core tests.
4. **`agent/v09-profile-close`** — `presets.py`/`profile.py`: real finite physical/process bounds where a preset claims
   capability, the fully-declared Custom FIT profile builder, ventilation reserved wiring, measurement-set promotion. Owns
   profile/preset tests. (Also owns the `hazards.py` H₂SO₄ record UNLESS the seam probe reassigns; provisional: material
   owner, since it's material/hazard data — **assign to `v09-material-close`**.)
5. **`agent/v09-service-transport`** — `service.py`/`plan.py`/`cli.py`: request field + `CapabilityProfileSelection` +
   assessment attach on `RankedRouteSummary` + `CAPABILITY-REBIND-ON-LOAD` + `capability_question_digest` + CLI four-hop +
   human render (READINESS / CAPABILITY[profile] separate lines + scope note). **Starts only after 1–4 freeze.** Owns
   transport tests/goldens.
6. **`agent/v09-release-evidence`** — `experiments/v0_9_mutation_calibration.py` (M1–M38), `experiments/v0_9_capability_funnel.py`
   + RESULTS, forcing-matrix test, README/ROADMAP/`V0_9_CAPABILITY_COMPILER_RELEASE_*.md`. After behavior freezes.

---

## The Round-III forcing matrix (independent oracle — implementers MUST match THIS, not their own expectations)

Same real searched routes. The release FIT positive is a **fully-declared Custom**, not a preset.

| route | tier | research-lab (no stock) | poor-man | fully-declared Custom (release positive) | targeted-negative Customs |
|---|---|---|---|---|---|
| **isopentyl acetate** | PROCESS_SPECIFIED | **UNKNOWN** — material (no stock); physical/process may also be UNKNOWN if the preset declares no real bound | **BLOCKED** — equipment (no reflux condenser / no fractional distillation) **and** measurement (no IR) **and** containment (H₂SO₄, once D9 record lands) | **CAPABILITY_FIT** — declared stock (glacial acetic ≥0.995, reagent alcohol, name-keyed washes/drier) + full glassware + IR + FUME_HOOD + real T/process bounds + AQUEOUS_NEUTRAL + commensurable-or-absent budget | each fails on its ONE axis: −containment→BLOCKED containment; −fractional-distillation→BLOCKED equipment; −IR→BLOCKED measurement; vinegar-not-glacial→BLOCKED material; too-little-stock→UNKNOWN/BLOCKED quantity; −procurement-reach→BLOCKED procurement |
| aspirin | FORMAL | **UNKNOWN** (tier caps FIT) | **BLOCKED** — equipment (no vacuum filtration) | **cannot FIT** (tier < PROCESS_SPECIFIED) — assessable, never overall FIT | — |
| paracetamol (anhydride) | FORMAL | **UNKNOWN** (tier caps FIT) | **BLOCKED** — no vacuum filtration | **cannot FIT** (tier) | — |
| methyl salicylate | CONDITIONS_SUPPORTED | **UNKNOWN** (tier<PS) | **BLOCKED** containment (methanol) | **cannot FIT** (tier) | — |
| retro-Diels-Alder | REACTION_VOUCHED | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** (null: nothing sourced to project; profiles MUST NOT diverge) | — |

Anti-laundering laws encoded: tier < PROCESS_SPECIFIED ⇒ never overall FIT; outdoors ≠ containment; unknown
assay/hazard/price/phase stays UNKNOWN; UNCONSTRAINED-with-a-real-demand ⇒ UNKNOWN; mismatched budget denomination ⇒
UNKNOWN; identical search feeds all profiles; the null route forbids divergence; a below-PROCESS_SPECIFIED route with
every resource still cannot FIT.

---

## Mutation gate — M1–M38 (M1–M22 from Round II retained; M23–M38 new this round)

M23 reaction-class-label manufactures a universal assay floor · M24 procedure-only consumables vanish from material ·
M25 required quantity ignored · M26 known phase/formulation mismatch still FITs · M27 required analytical method ignored ·
M28 generic ANALYTICAL_INSTRUMENT substitutes for the wrong specific method · M29 UNCONSTRAINED physical/process silently
means unlimited bench → FIT · M30 budget compares different CostVector units · M31 $/mol compared to total-$ with no
production quantity · M32 ventilation present but falsely clears containment / silently claims an assessed axis ·
M33 procedure-only hazardous material omitted from containment/waste · M34 named-preset request stores only the name →
silently changes meaning · M35 custom content changes without capability_question_digest moving · M36 profile selection
changes search candidate/receipt identity · M37 no-profile request silently receives a bench assumption · M38 canonical
CAPABILITY_FIT loads after its profile/material evidence is altered. Each: real code passes; in-memory mutant fails a
discriminator; mutation restored. No ceremonial counts.

---

## What Round III does NOT do (scope fence)

No new reaction classes. No new chemistry family. No currency-exchange or unit-conversion engine (unit mismatch →
UNKNOWN, full stop). No runtime free-text parsing of procedure prose (all enrichment is authored code). No ionic-salt
`Molecule` invention (a fabricated covalent spelling of an ionic lattice is banned — `identity=None` is the honest
carrier). The FeCl₃ reagent-confirmation model and per-material quantity re-attribution from source are VERIFIED DEFERS
with the boundaries named above.
