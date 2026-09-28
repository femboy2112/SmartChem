# SmartChem 0.9 — Capability Compiler (PLAN v0.1, Round I recon + design)

**Branch** `feat/v0.9-capability-compiler`, cut from `main@df1b38d` (the merged 0.8.0a1 release). **Version stays
`0.8.0a1`** — 0.9 is not bumped until a capability gate is met (this is Round I: substrate census + design +
one measured forcing vertical, per the mega-round stop point). Aligns to the user's own design in
`docs/research/CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md` §8 ("Capability is a projection, not a second chemistry
engine") and §9 (the poor-man 1.0 contract).

**0.9's first principle:** the SAME `ExperimentRoute` / Real Route Dossier is projected through
`ResearchLabProfile` / `PoorManProfile` / `CustomProfile`. The chemistry is identical; only the capability verdict
differs. No second retrosynthesis engine, no second chemistry, no readiness change — 0.8's ladder stays
capability-blind (`readiness.py` reads no fit/bounds/ΔG, by law).

---

## 1. The two decisive recon findings (both verified against the filesystem)

### Finding A — the `MaterialBucket` is ALREADY BUILT, and unwired (STOCK-01)
`smartchem/experiment/stock.py` already contains a fully-typed, red-team-folded real-material model that is exactly
the `MaterialBucket` §8 asks for:
- `StockMaterial` (`stock.py:265`): structure-keyed `MaterialComponent`s with fraction **intervals** `[min,max]`, a
  `Phase` enum (`stock.py:58`: SOLID / LIQUID / GAS / AQUEOUS_SOLUTION / UNKNOWN), `assay_method`,
  `known_impurities`, `formulation_notes`, `quantity`, `cost_observation`, `jurisdiction_and_availability`.
- `FitnessVerdict` (`stock.py:66`: SATISFIES / INSUFFICIENT_ASSAY / UNKNOWN_ASSAY / IDENTITY_ABSENT) +
  `StockMaterial.satisfies(required_identity, *, min_assay)` (`stock.py:344`) — a verdict that provably refuses to
  let "vinegar" satisfy a pure-acetic-acid query (the exact §8 law: formulation must not silently collapse to pure
  reagent identity).
- `stock_material_from_commodity()` (`stock.py:390`) — bridges a `CommodityReagent` lead to a `StockMaterial` with
  `Phase.UNKNOWN` + unknown assay, so a commodity lead can never silently satisfy a purity-critical query.
- `sourcing.plan_sourcing` (`sourcing.py`) → `SourcingPlan` / `QuantityCoverage` — "does what I HAVE satisfy what
  the route NEEDS," the exact 0.9 procurement question.

**It is wired into NOTHING** (verified: zero call sites outside `stock.py`/`sourcing.py`/their tests; only
`experiment/__init__.py` re-exports + docstring mentions). `service.py:43` names it as an explicit parked
follow-on: *"It does NOT yet ... bind quantitative StockMaterial (STOCK-01)."* **So 0.9's material work is WIRING
an existing, reviewed type — not designing a new one.** Building a second `MaterialBucket` would duplicate ~500
lines + 537 lines of tests already folded through two red-team passes (`0964c4b`, `8a8c46f`).

### Finding B — two live "material == pure Molecule" collapse points to close
1. `commodity_for(molecule)` (`data/reagents.py:198`) is keyed on `_identity(m) = canonical_digest(m.canonical())`
   — pure structure. "acetic acid the identity" and "a bottle of vinegar" return the SAME `CommodityReagent`; the
   only trace of dilution is a free-text `common_source` string nothing parses.
2. `CompilationRequest.stock_materials: tuple[str,...]` (`service.py:583`) resolves each name straight to
   `resolve_target(...).canonical()` — a pure `Molecule` (`service.py:2552`). A declared stock material carries no
   phase/concentration.
`CostVector` (`affordability.py`) is LIVE and wired (`_affordability_frontier`, `service.py:2400/2649`) — it is a
cost/access axis over pure-Molecule leaves, orthogonal to concentration/phase, safe to compose (the stale memory
note "CostVector wire-in deferred" is about a different axis; COST-VEC-01 for the frontier is done for routes mode).

---

## 2. Capability substrate census (machine-readable map, condensed; full rows in the Wave-A lane reports)

**Resource / equipment / process-capability axis (Lane 1):**
| concept | file:line | typed? | in a verdict? | 0.9 gap / hazard |
|---|---|---|---|---|
| `PhysicalBounds` | `constraints.py:31` | ✅ | ✅ RouteFit (T/P) | pure leaf, reuse as-is |
| `ProcessRequirements` (per-step DEMAND) | `process_constraints.py:80` | ✅ | ✅ ProcessFit | the 0.9 per-step demand vector already |
| `ProcessBounds` (operator LIMITS) | `process_constraints.py:220` | ✅ | ✅ ProcessFit | closest half of a CapabilityProfile; `quick()`/`low_touch()` = preset analogue (time/attention only) |
| `EquipmentKind`/`EquipmentItem` | `equipment.py:51` | ✅ (8-kind enum) | ✅ via `ConstraintBox.available_equipment` | **DUP HAZARD #1** |
| `ProcessBounds.available_equipment: tuple[str,...]` | `process_constraints.py:245` | ✅ (string ids) | ✅ ProcessFit | **DUP HAZARD #1**: two incompatible equipment reps, never reconciled |
| `handling.py` `CareLevel`/`RouteHandling` | `handling.py:87` | ✅ | ❌ **ORPHAN** (no live caller in drafter/service/readiness) | a half-built "can it run unattended" axis — gift or landmine |
| `ObservabilityScore`/`SignalCost` | `observation/observability.py:66` | ✅ | ranks, never gates | reuse `SignalCost` (FREE/CHEAP/INSTRUMENT) as the measurement-capability vocabulary |
| `procedure_evidence.apparatus` (0.8) | `procedure_evidence.py:190` | ✅ | readiness (not capability) | "never compared against an inventory" — that comparison IS 0.9's job |
| containment / ventilation / waste (operator side) | — | ❌ | — | **genuinely unrepresented** (only `EquipmentKind.CONTAINMENT`, hazard-triggered) |
| `CapabilityBucket` | `observation/process_observation.py:135` | ✅ | P1 evidence gate | **NAME LANDMINE** — documentation-evidence axis, NOT operator capability |

**Material / affordability / procurement axis (Lane 2):** `StockMaterial`/`MaterialComponent`/`Phase`/
`FitnessVerdict`/`plan_sourcing` (Finding A, unwired); `CostVector` (live); `catalyst_availability` (separate
catalyst-by-name obtainability axis, `catalyst_availability.py:166` — reuse its burden-of-proof-flip *pattern*, not
its machinery); `Availability` enum (`reagents.py:47`); `commodity_for` collapse point (Finding B).

---

## 3. `CapabilityProfile` design (§8-aligned; resolves the census hazards)

ONE frozen `Digestible` type carrying declared resources, projected onto a route to produce a capability verdict.
Fields (from §8): `material_inventory: tuple[StockMaterial,...]`; `budget` (a `CostVector` ceiling / access-tier
allowance); `temperature_range` + `pressure_range` (reuse `PhysicalBounds`); `equipment`; `containment`;
`ventilation`; `measurement_capability` (reuse `SignalCost` tiers); `separation_purification`;
`operator_attention` (reuse `Attention`/`Agitation`); `time` (reuse the `ProcessBounds` minutes fields);
`waste_handling`; `procurement` (reuse `Availability` tiers). `ResearchLabProfile` / `PoorManProfile` /
`CustomProfile` are `@classmethod` preset builders of this ONE type (the shape `ProcessBounds.preset()` already
models), NEVER separate evaluators.

**Frozen design rulings for the build round (from the census):**
- **DUP HAZARD #1 — equipment.** Pick ONE representation and migrate the other two onto it. Ruling: the
  `EquipmentKind` enum (`equipment.py`, 8 kinds) is the sound capability granularity (an operator owns *a kind of
  apparatus*, and `equipment_for_step` already infers a step's needed kinds); the free-text `ProcessBounds`/
  `ProcessRequirements` equipment strings + `procedure_evidence.apparatus` names are RESOLVED to `EquipmentKind`s
  at the capability seam. `CapabilityProfile.equipment` is a `frozenset[EquipmentKind]`; do NOT add a third string
  set.
- **Containment / ventilation / waste** are genuinely new axes (unrepresented today). Add them as explicit
  capability fields. §9's law is binding: outdoors satisfies a *ventilation* requirement only where explicitly
  modeled; it NEVER erases containment, waste, environmental, or legality constraints.
- **The `handling.py` orphan.** `RouteHandling`/`CareLevel` (hazard-driven "needs active control") is built and
  wired to nothing. Round II must decide: fold it in as the attention-capability driver, or keep it orthogonal to
  `Attention`/`allowed_attention`. Do NOT wire a second attention axis that could disagree with the first without
  reconciling them (base-rate-dependent-fail-closed-polarity discipline applies).
- **Naming.** Disclaim the `CapabilityBucket` (documentation-evidence) and `Bucket` (epistemic) collisions in the
  new type's docstring; prefer `CapabilityProfile` (no "Bucket") to avoid the `bucket.py` landmine.
- **Verdict vocabulary.** Reuse the `ProcessFitStatus` shape (UNCONSTRAINED/FITS/EXCLUDED/UNKNOWN) as
  `CAPABILITY_*` verdicts; readiness stays orthogonal (§6).

## 4. `MaterialBucket` design = **adopt `StockMaterial`** (do not rebuild)
`MaterialBucket` IS `StockMaterial`. Round II's material work:
1. Wire STOCK-01: let `CompilationRequest` carry a `tuple[StockMaterial,...]` inventory (alongside or superseding
   the bare-string `stock_materials`), and route it into `plan_sourcing` at the capability seam. Resolve the
   naming clash (`stock_materials: tuple[str,...]` field vs `StockMaterial` class).
2. Close Finding B's collapse points: a material query goes through `StockMaterial.satisfies(identity, min_assay)`,
   not `commodity_for(molecule)` structure-equality, wherever concentration/phase is capability-relevant.
3. The concentration-not-collapsing law is ALREADY enforced by `satisfies()`; the round PROVES it end-to-end
   (vinegar cannot satisfy a step needing anhydrous/high-assay acetic acid).

## 5. The measured forcing vertical (Round I deliverable — measured, NOT designed to diverge)
Read from the real 0.8 `ProcedureEvidence.apparatus` + `ProcessRequirements.equipment`:
| route | tier (0.8) | source-specified apparatus | ResearchLab | PoorMan (household/outdoor) |
|---|---|---|---|---|
| **isopentyl acetate** | PROCESS_SPECIFIED | round-bottom flask, **reflux condenser**, heating mantle, boiling stones, separatory funnel, **fractional distillation apparatus**, thermometer | **CAPABILITY_FIT** | **CAPABILITY_BLOCKED/UNKNOWN** — no reflux condenser / fractional distillation |
| aspirin | FORMAL (reaction unrecognized) | Erlenmeyer, steam bath, ice bath, **Buchner (vacuum) funnel**, ethyl acetate/petroleum-ether recrystallization | CAPABILITY_FIT | BLOCKED — vacuum filtration / recrystallization solvents |
| methyl salicylate | CONDITIONS_SUPPORTED | hot plate, beaker water bath, test tubes | CAPABILITY_FIT | plausibly FIT — but tier < PROCESS_SPECIFIED, so capability is moot until the procedure is complete |

**The vertical:** isopentyl acetate is the same PROCESS_SPECIFIED route under both profiles; the ResearchLab
profile owns a distillation apparatus and reflux condenser (→ FIT), the conservative PoorMan profile does not
(→ BLOCKED/UNKNOWN). Same chemistry, divergent capability projection, measured from what the accepted source
actually specified — no profile gerrymandered to force it (§: "Measure what exists").

## 6. The 0.9 readiness boundary
`CAPABILITY_ASSESSED` / `CAPABILITY_FIT` join the ladder ONLY after the capability model genuinely exists. None of
cheap / available / favorable / sourced / **PROCESS_SPECIFIED** may automatically mean capability fit — capability
is whole-path. Readiness (0.8) stays capability-blind: the capability verdict is a SEPARATE projection over the
same dossier, never folded back into `readiness.tier` (mirrors how ranking/ΔG/FITS are firewalled today).

## 7. Round I scope + stop point
DELIVERED this round: this plan, the substrate census (both lane maps), the `CapabilityProfile` design, the
`MaterialBucket=StockMaterial` adoption ruling, and the measured isopentyl forcing vertical + the STOCK-01
decisive obstruction. **Not built this round:** the `CapabilityProfile` type, the STOCK-01 wiring, the capability
verdict evaluator. **Do NOT bump to 0.9** — types are not a gate. Round II builds `CapabilityProfile` +
projects the isopentyl vertical to a real divergent verdict.

**Next highest-value move:** build `CapabilityProfile` (EquipmentKind-based, §8 fields) + wire STOCK-01, and turn
the isopentyl forcing vertical from a measured table into a real `ResearchLab→FIT / PoorMan→BLOCKED` verdict pair
over the identical route — the 0.9 analogue of 0.8's isopentyl PROCESS_SPECIFIED positive.
