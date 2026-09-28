# SmartChem 0.9 RC — Round V External Audit

**Evidence-Bound Material Semantics · Quantity Conservation · Wire-Schema Freeze**

Status: **IN PROGRESS — PR #93 on ROUND V EXTERNAL AUDIT HOLD (DO NOT MERGE).**

> *The enemy is no longer missing features. The enemy is one representation silently meaning two things.*
> No magic adjectives. No disappearing quantities. No reusable bottles. No invisible migrations. No evidence
> that certifies itself.

## §0 Repository truth (fetched at round start)

| item | value |
|---|---|
| branch | `feat/v0.9-capability-compiler` |
| starting tip | `4b8f8c2e2fbfb5b6be3ba691004305c36c6bda78` (== origin; no intervening commits) |
| main | `df1b38d132433444583eae954c3962c775399d8c` |
| divergence | 18 ahead / 0 behind |
| package | `0.9.0a1` (unchanged by this round — no ceremonial churn) |
| PR #93 | OPEN, unmerged; retitled `[ROUND V EXTERNAL AUDIT HOLD — DO NOT MERGE]` at round start |
| hosted CI on `4b8f8c2` | run 36472671245 `failure` — INFRASTRUCTURE-DEAD class (`runner_id=0`, `steps=[]`): neither green nor a code failure |

Round IV wins preserved as invariants (finite pools, repeated uses represented, structure > name, unknown hazards
cap containment, unresolved spent streams cap waste, no benign-by-negation, five process dimensions fail closed,
capability+DAG REFUSED, `compile` → canonical recompile, search noninterference, zero-FIT accepted over gaming).

## §1 Findings ledger (F64+)

Parent-reproduced before any lane returned (script `scratchpad/r5/repro_quantity.py`, real API, `.venv` python):

```
F64 sum([25 mL] + unknown use dropped upstream): 25 mL   (requirements.py:332 appends only non-None quantities)
F65 sum([10 g, 20 mL]): None
F65 axis (10 g + 20 mL demand vs 0.001 mL bottle): CapabilityStatus.FIT          <-- false material FIT
F66 axis (A 80 mL + B 80 mL from one 100 mL bottle): CapabilityStatus.FIT      <-- package double-spend
F74 versions: compilation-request-v1alpha5 compilation-response-v1alpha15
              compilation-response-schema-v1alpha18 ranked-route-summary-v1alpha3   (identical to main@df1b38d)
```

_(Per-finding adjudication table filled in §7 after the Wave-A lanes return.)_

## §2 Wave A (read-only) — lane verdict digest

| lane | bearing | headline (reproducers in `scratchpad/r5/lane*/`) |
|---|---|---|
| A quantity | known+unknown, mixed unit, package double-spend, exact arithmetic | F64/F65/F66 VERIFIED **P0** (`assess()` returns overall `CAPABILITY_FIT` for F65 and F66 on a clear-axes record at PROCESS_SPECIFIED); F75 PARTIAL (same-species F50 split refuted; structure-key + name-key of one bottle double-spent VERIFIED); `%g`/float/`1e-9` epsilon false FITs (20.00004 mL vs 20 mL; 5e-10 mL vs 1e-12 mL); NEW: quantity check measures the BOTTLE, not the species (A at unknown fraction [0,1] in a 10 mL bottle FITs 10 mL of A). Prototype allocator 17/17 knife-edges. |
| B formulation | conc./neat/saturated/anhydrous/basis + outside-corpus attacker | F67 VERIFIED (in-corpus: paracetamol conc. HCl → [0.95,1] band; real 37% HCl BLOCKs, impossible 96% aq. HCl FITs; 10% isoamyl-in-hexane FITs "neat"; 20.5% NaCl FITs "saturated", saturated limewater BLOCKs; MgSO4·7H2O FITs "anhydrous"); F68 code side VERIFIED (no basis on any compare-path object); F69 VERIFIED ("fuming", "6 M", "absolute", "concentrated", "98%" silently dropped → FIT). |
| C evidence | binding, method label, units, source re-fetch, coverage map | F68 source VERIFIED (LibreTexts page, fetched, sha256 20fc5ff4…: "25 mL of 5% sodium bicarbonate solution twice" — **no basis, no tolerance**; "4 mL of conc. H2SO4" — no %; no disposal text; "Remember, you used an excess of glacial acetic acid."); F70 VERIFIED (source/method/domain/kernel swaps leave all material + profile digests unmoved; `canonical_digest` refuses the record outright); F71/F63 VERIFIED (BROADENED+arbitrary width, SOURCE_QUOTED+conversion kernel all construct; shipped NaHCO3 water record labelled COMPLEMENT over an ASSUMED parent); M76 VERIFIED (ASSUMED req vs ASSUMED stock → zero-margin FIT; also conc. H2SO4 0.95 floor vs stock 0.95 and MgSO4 0.97 vs the SAME Sigma spec); F72 VERIFIED-as-premise (g/100 mL / mg/L inputs fed to a g/100 g kernel; true value inside band → verdict-neutral); F73 VERIFIED (`source_map.json`, 19 intervals, 6/12 stock intervals evidenced, 0 digest-bound). |
| D schema | fixtures, request/response diff, migration attacker, digests | F74 VERIFIED (request +capability_profile/origin; response +capability_question_digest; summary +capability_assessment + replay `material_uses`; descriptor +2 fields — none bumped). F81 PARTIAL-but-worse: v0.8 requests load as native (profile None — correct meaning, wrong identity); **v0.8 routes-mode responses are REFUSED with a misleading digest error** (refutes Round IV's F54 "additive-optional" claim); a v0.8-id request with an injected capability profile is ACCEPTED as native. Real v0.8 fixtures generated from `git archive df1b38d` (deterministic sha). `semantic_digest` hashes the request schema id. |
| E waste/process | aqueous-neutral, residuals, ProcessBounds law, ventilation | F76 VERIFIED (isopentyl water byproduct `Fate.UNKNOWN` emitted as "ASSESSED-benign condensed … AQUEOUS_NEUTRAL"; waste FIT on no-procedure routes 0/1/5); F77 VERIFIED (excess AcOH ≥0.212 mol, 4 mL H2SO4 catalyst, unreacted alcohol, CO2 from bicarbonate never enter waste; spent streams keyed only off OPTIONAL typed uses); **LATENT P0**: a schema-legal counterfactual of the isopentyl source (auxiliaries only in `materials=` strings + a declared elapsed ceiling + one missing hazard record) reaches overall `CAPABILITY_FIT` with waste {AQUEOUS_NEUTRAL}; F78 VERIFIED (same ProcessBounds: legacy FITS, capability UNKNOWN; "no time limit" inexpressible; 1e300 ceiling is the only FIT). Ventilation reserved + M6 hold. |
| F oracle (blind) | held-out saponification | predicts UNKNOWN in teaching-lab and kitchen worlds, never FIT; checklist P1–P12 (95% basis UNSTATED, 6 M stays MOLAR, saturated stays a state, oil identity None, vodka UNKNOWN not BLOCKED, no neutral filtrate, no compiler literals). |
| G structure theorem | locally-valid, globally-overclaiming states | **KILLED — 4 P0 overall-FIT families** from locally-valid states (all round-trip the wire replay; identical on a clean `git archive 4b8f8c2`): **P0-1** an op with `material_uses=()` (constructor default / 0.8 shape) while `op.materials`, WASH/DRY ops and `catalysts=('sulfuric acid',)` stand → vinegar + alcohol bench FITs (control with uses kept BLOCKS); **P0-2** partial typing (real aspirin/paracetamol shape) → FIT, catalyst waste never reaches waste, balanced species with no hazard record silently skipped; **P0-3** possession-only commodity lead ([0,1], phase UNKNOWN) → material FIT; **P0-4** unread demands: 3-week `envelope.duration`/HOLD vs 10080-min bench, apparatus-stripped ops → equipment/measurement NOT_APPLICABLE; envelope 600 K / 50 atm while the process record says 416 K / 1 atm → physical FIT. P1: two-key bottle 40 from 25 mL; vinegar 25 mL meets 20 mL acetic acid; readiness not bound to requirements; two axes read two temperatures. P2: `medium` (benzene) and `applied_field` unread; budget None → UNCONSTRAINED over a proven cost floor. Structure theorem: T1 unread demand, T2 collapse to the smaller representation, T3 per-group capacity. |

## §3 Parent barrier — twelve frozen decisions (Wave B builds ONLY against these)

**D1 — Quantity-knowledge algebra.** `MaterialRequirement.quantity` is NEVER `None`. It is a typed `QuantityDemand`
(`smartchem/capability/quantity.py`): `known: tuple[(unit, exact decimal str), ...]` (one entry per unit domain,
exact `Fraction` sums, sorted) + `unstated_uses: int`. Derived knowledge: `EXACT` (unstated_uses == 0 and known
non-empty), `LOWER_BOUND_PLUS_UNKNOWN` (both), `UNKNOWN` (unstated only). A leaf reactant with no typed use gets
`UNKNOWN` (unstated_uses=1) — a consumed material's demand is real and positive. Mixed units keep BOTH per-unit
components; nothing ever collapses to "no gate". Units are compared by exact string equality (no conversion engine;
no density/molar-mass bridge). Exact parsing via `material_spec.exact_fraction` (strict grammar); `%g`, `float()`
and the `1e-9` epsilon are banned from every quantity path. `StockQuantity.value` is validated by the same grammar.

**D2 — Global package-allocation theorem.** One flow network PER UNIT DOMAIN `u`; each STOCK PACKAGE is ONE node with
ONE capacity edge (its declared quantity, only in its own unit domain); requirement nodes carry their exact demand in
`u`. Two graphs, exact Edmonds–Karp, no epsilon:
* **G⁻ (pessimistic)** — edges only from bottles whose composition/phase/spec verdict is FIT **and** whose draw is
  commensurable with the demanded species (the bottle IS the formulated material: the requirement carries a
  composition/state spec the bottle satisfies, or the species is the bottle's ONLY component); capacity = declared
  quantity in `u`, else 0.
* **G⁺ (optimistic)** — edges from FIT or UNKNOWN-compatible bottles; capacity = declared quantity in `u`, or the total
  demand of `u` (finite stand-in for ∞) when the bottle's quantity is unknown or in another unit.
Verdict: **BLOCKED** ⇔ some `u` has F⁺_u < T_u, or a positive-demand requirement has no G⁺ edge; **FIT** ⇔ every
requirement is EXACT and F⁻_u = T_u for every `u`; else **UNKNOWN**. A bottle's known capacity appears in exactly one
domain, so no FIT can spend a package twice (across species, spec splits, name/structure keys, or unit domains).

**D3 — MaterialSpecification at the evidence origin.** Frozen in `smartchem/material_spec.py` (parent-authored):
`MaterialSpecification{composition: CompositionConstraint|None, states: tuple[StateClaim], unresolved_terms}`.
`ProcedureMaterialUse` gains `specification: MaterialSpecification | None`; its `formulation` string becomes
provenance/display ONLY. Phase stays ONLY on `ProcedureMaterialUse.phase` (one representation). The capability
compiler projects the spec and must not contain any formulation vocabulary: `_FORMULATION_SPECS` and
`_formulation_spec` are DELETED. **F69 law:** a use with a non-empty raw `formulation` and `specification is None`
projects as `MaterialSpecification(unresolved_terms=(formulation,))` → UNKNOWN.

**D4 — Concentration basis.** `ConcentrationBasis{MASS_FRACTION, MASS_PER_VOLUME, VOLUME_FRACTION, MOLAR, UNKNOWN}` on
both sides (requirement `CompositionConstraint.basis`; stock `MaterialComponent.basis`, default `UNKNOWN`). Either side
UNKNOWN → UNDETERMINED; different bases → UNDETERMINED; `NOMINAL_UNSTATED_TOLERANCE` → UNDETERMINED. The isopentyl
"5% sodium bicarbonate solution" is `0.05/0.05, basis UNKNOWN, NOMINAL_UNSTATED_TOLERANCE, SOURCE_QUOTED` → UNKNOWN.

**D5 — Hydration / saturation / neat.** Positive-declaration `StateClaim`s (`DilutionState.NEAT|SOLUTION`,
`HydrationState.ANHYDROUS|HYDRATE`, `SaturationState.SATURATED|UNSATURATED`), one per family. The stock must POSITIVELY
declare the required state (`StockMaterial.states`); phase, purity bands and numeric floors never discharge a state;
a contrary certified declaration VIOLATES; absence → UNDETERMINED.

**D6 — Evidence-strength vocabulary.** `EvidenceKind{SOURCE_QUOTED, DERIVED, CLAMPED, USER_DECLARED, AUTHOR_INFERRED,
ASSUMED, UNKNOWN}`. Requirement claims certify only at SOURCE_QUOTED/DERIVED/CLAMPED; stock claims at those or
USER_DECLARED. ASSUMED/AUTHOR_INFERRED/UNKNOWN on either side can neither certify FIT nor prove VIOLATES (F71: ASSUMED-
only agreement is UNKNOWN). The law is the single function `material_spec.compare_specification`.

**D7 — Derived-evidence kernel identity.** `DerivedIntervalEvidence` with a Python callable is RETIRED. Replacement
`IntervalEvidence` (stable, digestible, exact decimal strings — no `Fraction`/callable in the record):
`{kind: EvidenceKind, low, high, basis: ConcentrationBasis, source_locators: tuple[str], kernel: DerivationKernel,
inputs: tuple[TypedInput], domain_of_validity: str}` with a CLOSED `DerivationKernel` registry, each entry declaring
its required input units and the ONLY `EvidenceKind` it may emit:
`IDENTITY_SOURCE_QUOTED_V1→SOURCE_QUOTED`, `SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1→DERIVED` (inputs must be
g/100 g solvent; per-mL/per-L inputs refused — F72), `COMPLEMENT_V1→`(kind of its parent, parent evidence embedded),
`CLAMP_TO_UNIT_INTERVAL_V1→CLAMPED` (must actually clip), `ASSUMED_BAND_V1→ASSUMED`, `USER_DECLARED_V1→USER_DECLARED`,
`UNKNOWN_V1→UNKNOWN` ([0,1]). Construction recomputes via the registry and refuses any mismatch of value, input
units or kind (closes F63/F71: a label cannot claim BROADENED/SOURCE_QUOTED over arithmetic that isn't).

**D8 — Evidence-to-material binding.** `MaterialComponent` gains `basis: ConcentrationBasis = UNKNOWN` and
`evidence: IntervalEvidence | None = None` (None ≡ UNKNOWN strength); when present the evidence endpoints must equal
`min_fraction/max_fraction` exactly. `StockMaterial` gains `states: tuple[StateClaim, ...] = ()`. Both enter the
material → profile → request/question → result digests automatically. Schemas bump: `material-component-v1alpha2`,
`stock-material-v1alpha2`. Every production interval gets a real record or is relabelled ASSUMED/UNKNOWN (§ per Lane C
table); no source is fabricated.

**D9 — Waste classification.** A waste category is earned only from positive evidence about the STREAM:
unassessed → unresolved; off-gas → OFFGAS_CAPTURE (+HAZARDOUS if real GHS); real GHS any fate → HAZARDOUS (+unresolved
if fate UNKNOWN); empty-GHS byproduct (any fate) → **unresolved** ("benign species, untyped stream"). `AQUEOUS_NEUTRAL`
requires a typed aqueous stream with a sourced neutral endpoint and every component assessed benign — nothing in the
corpus qualifies, so it is unreachable today (honest). **Residuals (F77):** every CATALYST use / envelope catalyst is a
certain residual (HAZARDOUS if its resolved hazard has real GHS, else unresolved); every SUBSTRATE/REACTANT use (and
every leaf of a step without procedure) is an unresolved residual unless full consumption/recovery is typed.
**Spent streams** are derived from OPERATIONS (role WASH/RECRYSTALLIZATION, kind SEPARATE/FILTER/DRY/DISTILL), typed
uses only refine them — an op whose auxiliaries live only in `materials=` strings still yields an unresolved stream
(closes Lane E's latent P0). Reason strings quote the real `Fate`.

**D10 — ProcessBounds/PhysicalBounds declaration semantics.** `ProcessBounds`/`PhysicalBounds` are NOT changed
(legacy "None = unconstrained" stays true for legacy callers). The capability layer reads them through
`capability/declarations.py`: `DimensionDeclaration{UNDECLARED, DECLARED_BOUND, NO_LIMIT}`; `CapabilityProfile` gains
`no_limit_dimensions: frozenset[str]` (only the PREFERENCE dimensions `max_step_minutes`, `max_total_minutes`,
`max_active_minutes` may be NO_LIMIT; a NO_LIMIT dimension must carry a `None` bound; physical T/P, attention, agitation,
check-interval and equipment may never be NO_LIMIT — construction error). Law per dimension: UNDECLARED + real demand →
UNKNOWN; DECLARED_BOUND → compare; NO_LIMIT + demand → FIT on that dimension, reason tagged "operator NO_LIMIT
preference, not measured capability". Presets never emit NO_LIMIT. Schemas bump: `capability-profile-v1alpha2`,
`capability-assessment-v1alpha2`.

**D11 — Schema-version migration map** (bump relative to released `main@df1b38d`; new-in-0.9 schemas bumped only where
Round V changes them):

| artifact | 0.8 id | 0.9 id | shape change | migration | guarantee |
|---|---|---|---|---|---|
| CompilationRequest | `compilation-request-v1alpha5` | `v1alpha6` | +capability_profile, +capability_profile_origin | v1alpha5 accepted as legacy → capability NOT_REQUESTED; a v1alpha5 payload carrying any capability key is REFUSED | legacy digests verify under the stored id |
| CompilationResponse | `compilation-response-v1alpha15` | `v1alpha16` | +capability_question_digest; embeds new request/summary | v1alpha15 accepted as legacy: no assessment, no question, readiness preserved; verified with the v0.8 digest rule (0.9-added default fields excluded); a v1alpha15 payload carrying any 0.9-only key is REFUSED; unreplayable legacy → fail closed under verified admission ("legacy; recompile") | readiness preserved exactly |
| response descriptor | `…-schema-v1alpha18` | `v1alpha19` | +capability fields | pin | shape pin |
| RankedRouteSummary | `ranked-route-summary-v1alpha3` | `v1alpha4` | +capability_assessment; replay ops +material_uses (+specification) | decoded with None/() | — |
| MaterialComponent / StockMaterial | `v1alpha1` | `v1alpha2` | +basis/+evidence; +states | — | — |
| CapabilityProfile / Assessment | (new in 0.9) `v1alpha1` | `v1alpha2` | +no_limit_dimensions; typed quantity/spec reasons | — | — |
The request id is hashed into `semantic_digest`; the bump moves every `semantic_digest` ONCE (declared); capability
context still never enters it. Real v0.8 fixtures are copied from Lane D's `git archive df1b38d` output (never simulated).

**D13 — (amendment after Lane G) Every stated demand reaches its owning axis, or that axis fails closed.** Untyped
`op.materials` names, uncovered `envelope.catalysts`, and `envelope.medium` become name-keyed requirements with
`QuantityDemand((),1)` + `unresolved_terms` (never FIT) and enter the hazard scan / procurement / waste; balanced
species with no hazard record are carried as `hazard_unresolved` (parity with F47). Physical demand = MAX over the
process record, the envelope intervals and every op interval; a duration stated outside the process record, an
apparatus-less HEAT/HOLD/COOL/DISTILL/SEPARATE/FILTER/DRY op, an analytical verification with no VERIFY apparatus, and
an `applied_field` all fail closed (UNKNOWN). A G⁻ allocation edge needs a satisfied non-empty spec or a provably pure
bottle (matched species lower fraction == 1). `budget=None` is UNDECLARED → monetary UNKNOWN unless the profile
declares NO_LIMIT for `budget`. The assessment records the readiness tier it was folded under.

**D12 — File ownership (one writer per file).**

| writer | owns |
|---|---|
| parent | `smartchem/material_spec.py` (frozen), audit doc, integration |
| procedure-material | `smartchem/procedure_evidence.py`, source authoring in `smartchem/decompiler_conditions.py`, procedure-evidence tests |
| material-evidence | `smartchem/experiment/stock.py`, `smartchem/data/derived_evidence.py`, `smartchem/data/material_library.py`, data/evidence tests |
| capability-core | `smartchem/capability/requirements.py`, `smartchem/capability/assess.py`, NEW `smartchem/capability/quantity.py`, core capability tests |
| waste-process | NEW `smartchem/capability/waste.py`, NEW `smartchem/capability/declarations.py`, `smartchem/capability/profile.py`, `smartchem/capability/presets.py`, their tests |
| wire-migration | `smartchem/service.py`, `smartchem/cli.py`, `tests/fixtures/v08/**`, codec/migration tests, CLI goldens (after freeze) |
| gates | `experiments/v0_9_mutation_calibration.py`, `experiments/v0_9_capability_funnel.py`, held-out probe, ROADMAP / 0.9.5 plan / release record |

## §4 Wave B — writers (all landed, uncommitted until the WIP commit below)

| writer | delivered | own tests |
|---|---|---|
| procedure-material | typed `MaterialSpecification` on every formulated use (glacial→NEAT, conc.→`unresolved_terms`, "5%"→nominal/basis UNKNOWN, saturated/anhydrous→states); isopentyl "neat" removed (not in source); NaCl 5 mL added; paracetamol HCl = 1.5 mL + unstated; aspirin reprecipitation ops 6–9 typed from source | 14 + 16 + 15 + 5 green |
| material-evidence | `IntervalEvidence` + closed `KERNELS` registry (callable retired); `MaterialComponent.basis/evidence`; schemas `material-component-v1alpha2`, `stock-material-v1alpha2`; `StockQuantity` exact grammar + `.exact()`; every production interval re-evidenced (NaHCO3 ASSUMED/basis UNKNOWN, isoamyl-dilute → UNKNOWN_V1 (F72), NaCl collapsed to the single sourced 36.0 g/100 g, wash-water "distilled" claim withdrawn) | 45 + 10 + 38 green |
| capability-core | `capability/quantity.py` `QuantityDemand` (EXACT / LOWER_BOUND_PLUS_UNKNOWN / UNKNOWN, never None); `_FORMULATION_SPECS`/`_formulation_spec`/`_sum_commensurable`/`required_assay`/`composition_band` DELETED; G⁻/G⁺ exact per-unit-domain allocation; D13 unread-demand law; assessment `v1alpha2` + `readiness_tier/readiness_digest`; all Lane-G P0 constructions now UNKNOWN/BLOCKED | 111 green (at hand-back) |
| waste-process | `capability/waste.py` `derive_waste` (AQUEOUS_NEUTRAL never derived; residual + op-derived spent streams; medium); `capability/declarations.py` (UNDECLARED / DECLARED_BOUND / NO_LIMIT; eligible = 3 time dims + budget); profile `v1alpha2` + `no_limit_dimensions` | 40 green |
| wire-migration | request `v1alpha6`, response `v1alpha16`, descriptor `v1alpha19`, summary `v1alpha4`; explicit legacy dispatch + frozen v0.8 digest rule (`_V08_OMITTED_FIELDS`); REAL v0.8 fixtures in `tests/fixtures/v08/` verify byte-for-byte incl. isopentyl procedure routes under verified admission; tamper T1/T4b refused; goldens regenerated once | 44 migration + 432 across 17 wire/CLI files green |

## §5 Wave C — fresh non-author hostile review (IN PROGRESS at pause)

**C1 (amber — quantity/material):** allocator sound (exact arithmetic, one node per package, max-flow held). Breaks, all
FIXED by the parent and pinned in `tests/test_v0_9_round_v_wave_c_fixes.py` (24 tests):
K1 **P0** bottle-level state claims certified a trace/absent species → states are now COMPONENT-scoped
(`MaterialComponent.states`; `StockMaterial.states` removed); K2 **P0** "provably pure" ignored basis/evidence (MOLAR
[1,1], bare 1.0, ASSUMED [1,1], float→1) → needs fraction basis + certifying evidence + exact record lower bound 1;
K3 MOLAR/w-v capped at 1 → uncapped (6 M expressible); K4 substring coverage hid a second species → EXACT-name
coverage + corpus `op.materials` aligned to typed names; K5 duplicate package → refused by `CapabilityProfile`;
K6 non-ASCII digits → ASCII grammar. Nags fixed: glacial→NEAT relabelled AUTHOR_INFERRED (the page never says
"undiluted"); leaf reactant suppressed only by SUBSTRATE/REACTANT uses.

**C2 (smith — evidence/schema/migration):** D11 matrix held (21 attacks refused; real v0.8 fixtures incl. DAG path
load as legacy; F70 closed end-to-end; semantic_digest capability-invariant). Breaks: (1) thin-wire forged
`CAPABILITY_FIT` loads on a plain load (P0 by contract) — parent added `CapabilityAssessment.__post_init__` fold
check (overall must equal the fold of axes + readiness tier; pinned); **service-side replay-free checks
(readiness/profile/route binding, no FIT on THIN) handed to the wire writer — status at pause: see §6**;
(2) legacy names newly resolvable today refused with a misleading error → wire writer (precise legacy hint);
(3) producer signature doesn't bind the capability question when no dossiers → wire writer (fold into
result_digest); (4) TypedInput DERIVED/CLAMPED without locator → FIXED (locator required); FRACTION/PERCENT on
MOLAR → FIXED; COMPLEMENT inherits sourced kind → FIXED (emits ASSUMED); (6) legacy request nested keys → wire
writer. Residuals for 0.9.5: evidence has no subject binding; solubility temperature unread; rebind uses today's
tables; library `_declared` labels bench fixtures USER_DECLARED.

**C3 (evil-morty — waste/process/D13/genericity/search noninterference; stopped early, partial, all verified):**
**No P0 / no reachable overall false FIT** — but soundness currently rests on ONE universal rule: every op that can
make `workup_isolation` PRESENT is a D9 spent-stream op (always unresolved), and PROCESS_SPECIFIED requires it, so
PROCESS_SPECIFIED ⇒ waste ≤ UNKNOWN ⇒ no FIT (`waveC3/p6_theorem.py`). Behind that blanket, P1-LATENT per-axis
false FITs (become overall false FITs the day disposal routing is typeable) — **ALL OPEN, must be fixed before the
gate closes:** F-1 low-temperature (cryogenic) demand unread — `PhysicalBounds` has no T-min (77 K certifies vs an
ice bath); F-2 prose `op.duration` unread ("3 weeks" → process FIT); F-3 op durations compared by max not sum;
F-4 whitelisted consumable ("boiling stones") in a DISTILL op's apparatus masks the "no apparatus" D13 rule
(UNKNOWN → FIT, non-monotone); F-6 ADD/QUENCH (and ADD/MIX/HEAT carrying materials) ops produce no waste stream;
F-7 CATALYST role never checked against `ExperimentStep.net_consumes` (consumed reactants relabelled CATALYST drop
the residuals); F-8 NO_LIMIT branch silences non-time gaps (`workup_included=False`; a `ProcessRequirements()`
counts as a record); F-9 typed EvidenceField slots unread by any axis (`op.agitation`, `op.rate`, `op.endpoint`,
`analytical_verification.value`, `scale`/`op.quantity` contradicting uses); F-10 prose T/P "covered" by a
contradicting process record (650 C furnace vs 416 K record; 50 atm autoclave vs 1 atm) — extend D13 beyond
Intervals; F-11 (P3) absurd DECLARED_BOUND (1e300) accepted = disguised NO_LIMIT. F-5 (pure ignored basis) was
fixed by Wave-C K2 mid-review — needs a separate re-review of K1–K4. Residual: isopentyl `envelope.medium` holds
condition prose → projected as untyped material/hazard/waste (fail-closed but overdetermines the flagship UNKNOWN;
re-author the field). HELD: D10 construction guards + M82; D9 otherwise; **held-out genericity (methyl salicylate
via public API only — "absolute"→ANHYDROUS, "0.1 M" MOLAR, "95% (v/v)" VOLUME_FRACTION, vodka/conc. unresolved —
NO compiler edit needed; grep clean)**; search noninterference on the pre-fix tree (semantic_digest,
search_receipt_digest, 27 candidates identical across 5 profiles) — **unconfirmed on the current tree**.

## §6 PAUSE STATE (WIP) — resume checklist

Paused at the user's request mid-Wave-C. **Gate NOT closed. PR #93 stays ROUND V HOLD — DO NOT MERGE.** WIP commit
pushed so the tree is durable. To resume:

1. Collect/adjudicate: C3 report; gates-writer hand-back (mutation harness port + M50 closure + M63–M8x + Wave-C
   mutants, funnel, held-out saponification probe vs Lane F oracle `scratchpad/r5/laneF/ORACLE.md`, ROADMAP + 0.9.5
   plan); wire-writer C2 items (1)(2)(3)(6) + golden regeneration (goldens are STALE after the parent's Wave-C
   authoring changes unless the wire writer regenerated them).
2. Re-run ruff on changed files; regenerate CLI goldens via `tests/regen_cli_json.py` if stale.
3. Run the mutation harness end-to-end; require ACTIVE X/X killed, 0 survived, M50 non-vacuous, retired reported
   separately.
4. Full OOM-safe suite `scripts/run_suite.sh` (never pkill); hosted CI classification.
4b. Fix C3 F-1…F-4, F-6…F-11 (owners: capability-core for requirements/assess, waste-process for waste.py,
   material/physical bounds need a T-min dimension decision), re-review K1–K4, re-confirm search noninterference on
   the current tree, then a FRESH Wave-C pass (new non-authors) over the whole Round-V diff.
5. Fill §1 per-finding table (F64–F82 + Lane G + Wave C: VERIFIED/PARTIAL/REFUTED, reproducer, root cause, fix,
   guard), schema migration table (D11), funnel + profile-divergence adjudication, release record, PR body; STOP.

### §6.1 Gates writer status at pause

`experiments/v0_9_mutation_calibration.py` fully rewritten against the Round-V API (source-anchored patches with
asserted counts; F79 honest denominator; retirement void unless every replacement is ACTIVE+KILLED). Last tally
(pre-pause run): **`ACTIVE 98/102 killed, 4 survived | RETIRED 4 (0 void) | DEFERRED 0`** (exit 1).
* RETIRED: M23→M55/M56/M66; M45→M68/M46b; M47→M67/M46b; M58→M74/M57 (all replacements KILLED).
* **M50 CLOSED + KILLED** (real isopentyl route + real RouteHandling, water byproduct replaced by an unassessed
  CONDENSED entry, served through the real `verify_handling` call in `derive_waste`).
* New ACTIVE: M63–M82 (Round V), M83–M94 (D13/Lane G), M95–M105 (Wave C).
* **4 SURVIVORS — undiagnosed, must be resolved before the gate closes:** M38 (stock-stripped canonical wire —
  likely layered defence: new replay-free bindings refuse it), M86 (envelope duration — likely fixture fault:
  another UNDECLARED process dimension), M94 (legacy request injected capability — likely a third refusal layer,
  anchor must widen), M104 (thin-wire FIT — likely a second binding/digest layer; wire writer was mid-edit). Each
  must be shown killed or honestly re-scoped (a layered defence means the mutant must disable every layer).
* NOT DONE: funnel re-run + profile-divergence write-up; held-out saponification probe (+ blind compare vs
  `scratchpad/r5/laneF/ORACLE.md`, P11 grep); ROADMAP + 0.9.5 plan.
* Carry-forward: **structural zero-FIT theorem** (by reading) — under D9 every SUBSTRATE/REACTANT use and uncovered
  reactant is an unresolved residual with no "fully consumed/recovered" type, so overall CAPABILITY_FIT is
  unreachable for EVERY route, not just this corpus; pin with a test and state it in the funnel doc + 0.9.5 plan.
  MOLAR stock claims can never certify (no MOLAR input unit) — representation gap for 0.9.5.
