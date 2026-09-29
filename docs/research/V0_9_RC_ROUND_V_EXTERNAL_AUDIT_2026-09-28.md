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

### §1.1 Per-finding adjudication (the external audit's F64–F79 + F81; filled at the X-high close)

Note on numbering: the audit text defines F64–F79 and F81; no finding carries the numbers F80 or F82 (the "F64–F82"
range in the PR hold banner was the parent's shorthand). Every verdict below was reproduced on the real object path
before any fix; every fix has a discriminating regression test and a calibrated mutant that is ACTIVE and KILLED.

| finding | verdict | reproducer (before) | root cause | fix (barrier) | guard |
|---|---|---|---|---|---|
| F64 known + unknown use launders the unknown | **VERIFIED** | `scratchpad/r5/repro_quantity.py`: sum([25 mL] + unknown) = 25 mL | `requirements.py` appended only non-None quantities | typed `QuantityDemand` EXACT / LOWER_BOUND_PLUS_UNKNOWN / UNKNOWN (D1) | M63; core tests |
| F65 mixed units → no gate | **VERIFIED — P0** | 10 g + 20 mL demand vs a 0.001 mL bottle → overall `CAPABILITY_FIT` | mixed units summed to `None` = no gate | per-unit-domain demand + allocation, exact `Fraction` (D1/D2) | M64 |
| F66 per-species, not per-package, conservation | **VERIFIED — P0** | A 80 mL + B 80 mL from one 100 mL two-component bottle → FIT | independent per-requirement witnesses | ONE flow network per unit domain, one capacity edge per package, G⁻/G⁺ (D2); X-high: commensurability earned (D24.5), internal supply metered (D24.6) | M65, M77; B-battery (Wave C′) |
| F67 adjective semantics chemically false | **VERIFIED** (live in corpus) | conc. HCl → [0.95, 1]; 20.5 % NaCl FITs "saturated"; MgSO4·7H2O FITs "anhydrous" | the global `_FORMULATION_SPECS` oracle | oracle DELETED; source-authored `MaterialSpecification` (D3); states are positive claims (D5) | M66–M69 |
| F68 invented percent basis | **VERIFIED** | "5 % NaHCO3" compared as w/w | no basis on any compare-path object | `ConcentrationBasis` incl. UNKNOWN; nominal/unstated tolerance → UNDETERMINED (D4) | M70 |
| F69 unknown formulation dropped | **VERIFIED** | "fuming", "6 M", "absolute", "98 %" → no constraint → FIT | unmatched words returned `(None, None, None)` | `unresolved_terms` → UNKNOWN (D3); X-high: non-empty formulation beside an EMPTY spec also unresolved (D24.1) | M72 + D24 mutants |
| F70 derivation evidence unbound to its material | **VERIFIED** | source/method/domain/kernel swaps leave material + profile digests unmoved | callable `DerivedIntervalEvidence`, not digestible | digestible `IntervalEvidence` with a CLOSED kernel registry bound to `MaterialComponent` (D7/D8); X-high kernel semantic identity lock (D19, D24.9) | M73, M142–M143 + D24 mutants |
| F71 self-certifying assumptions / method labels | **VERIFIED** | ASSUMED req vs ASSUMED stock → zero-margin FIT; BROADENED label over arbitrary width | no evidence-strength law | certifying sets + `compare_specification` (D6); kernels emit only their declared kind (D7); X-high extends the law to PHASE (D18) | M71, M74, M137–M140 |
| F72 unit-premise mismatch (isoamyl negative) | **VERIFIED as premise** (verdict-neutral: true value inside the band) | g/100 mL fed to a g/100 g kernel | kernel accepted any unit | per-kernel input-unit whitelist; per-mL/per-L refused (D7) | M75 |
| F73 derived-data coverage incomplete | **VERIFIED** (19 intervals, 6/12 evidenced, 0 digest-bound) | Lane C `source_map.json` (scratch) | intervals without records | every curated interval re-evidenced or relabelled ASSUMED/UNKNOWN (Wave B); X-high: committed, machine-checked map `docs/research/V0_9_RC_ROUND_V_MATERIAL_SOURCE_MAP.md` (12/12 components carry a record; every sourced record + input names its locator) | `tests/test_v0_9_round_v_material_source_map.py` |
| F74 false schema versions | **VERIFIED** | all four wire ids identical to `main@df1b38d` while shapes changed | shapes changed without bumps | honest bumps + explicit legacy dispatch (D11); X-high final freeze (D22) incl. the silently-changed DAG summary | M80, M81 |
| F75 allocation must be GLOBAL across packages | **PARTIAL → FIXED** (same-species split refuted; structure-key + name-key double spend VERIFIED) | two-key bottle 40 from 25 mL | per-key allocation | D2 global graph; X-high D24.8 name-key presence → UNKNOWN (never a false BLOCK) | M77; B-battery |
| F76 AQUEOUS_NEUTRAL by absence | **VERIFIED** | isopentyl water byproduct `Fate.UNKNOWN` emitted as AQUEOUS_NEUTRAL | empty GHS read as a benign STREAM | categories earned only from positive stream evidence; AQUEOUS_NEUTRAL unreachable today (D9) | M78, M50 |
| F77 residual materials missing from waste | **VERIFIED** | excess AcOH, H2SO4 catalyst, unreacted alcohol, bicarbonate CO2 never entered waste | spent streams keyed only off optional typed uses | residual + operation-derived spent streams (D9); X-high F-6 untyped-material conservation + F-7 role consistency (D17) | M79, M92, M131–M134 |
| F78 ProcessBounds `None` overloaded | **VERIFIED** | same bounds: legacy FITS, capability UNKNOWN; "no limit" inexpressible | one `None` for two meanings | `DimensionDeclaration` UNDECLARED / DECLARED_BOUND / NO_LIMIT via `capability/declarations.py`, ProcessBounds unchanged (D10); X-high process axis independently correct (D15) | M82, M93, M121–M122 |
| F79 dishonest mutation denominator | **VERIFIED** | retired mechanisms counted as kills; M50 vacuous | no ACTIVE / RETIRED / DEFERRED split | honest denominator, retirement void unless replacements KILLED, M50 made non-vacuous (Round V); X-high: all 4 survivors diagnosed as fixture faults and rebuilt | the harness itself (§7.6 tally) |
| F81 a real v0.8 response read as native 0.9 | **PARTIAL → FIXED** (routes-mode v0.8 responses were REFUSED with a misleading digest error; a v0.8-id request with an injected profile was ACCEPTED) | real `git archive df1b38d` fixtures | no version dispatch | explicit legacy dispatch + frozen v0.8 digest rule (D11); X-high: legacy `semantic_digest` under the frozen rule, v0.8 DAG + stereo fixtures, identity-loss re-derivation (D22/D24.11) | M81, M94, M94b |

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

---

## §7 X-HIGH CONTINUATION (resumed 2026-09-28 on `78554a2`)

The first half of Round V ran at MEDIUM effort and was paused mid-Wave-C (§6). This continuation re-runs the
unfinished proofs at X-HIGH. It does **not** restart the round: every §3 barrier decision (D1–D13) stands unless a
counterexample below disproves it. Governing principle: *MEDIUM built most of the machine; X-HIGH must prove there
is nowhere left for a demand, resource, evidence grade or transport context to disappear between its parts.*

### §7.0 Recovered baseline (independently re-measured before any edit)

| item | value |
|---|---|
| tip | `78554a258bce9ec3db9a9c1cdf01e070e6527e35` == origin; 19 ahead / 0 behind `main@df1b38d`; package `0.9.0a1` |
| PR #93 | OPEN, unmerged, `[ROUND V EXTERNAL AUDIT HOLD — DO NOT MERGE]` |
| hosted CI on `78554a2` | run 36490673856: `test (3.10)`, `test (3.12)`, `Optional PySCF backend (smoke)` all `runner_id=0`, `steps=0` → **INFRASTRUCTURE-DEAD** (no code executed; neither green nor code-red) |
| mutation harness | `ACTIVE 98/102 killed, 4 survived (M38, M86, M94, M104) \| RETIRED 4 (0 void) \| DEFERRED 0`, exit 1, 5:07 wall — the WIP claim VERIFIED exactly |
| targeted tests (the 22 test files changed on the branch vs main) | **594 passed / 0 failed / 0 errors / 0 skipped** (7:43) |
| full OOM-safe suite on `78554a2` | **NOT RUN** — no full-suite claim is made for this tip |
| held-out oracle | Lane F's blind saponification oracle survived in scratch; preserved byte-identical as `docs/research/V0_9_RC_ROUND_V_HELDOUT_ORACLE_2026-09-28.md` (sha256 `eb01d67c9b761af3ae257f4cdf3c1ce119a500ccd1e78250ba9d6876c8ac95df`, scratch mtime 2026-09-28 16:42 -0400, i.e. written BEFORE any implementation agent saw a projected requirement) |

### §7.1 Wave A′ (read-only, seven lanes) — digest

| lane | headline |
|---|---|
| A-SURV (M38/M86/M94/M104) | **All four survivors are FIXTURE faults, none a code hole; every rebuilt mutant was run and KILLS.** M86: the route record declared no attention/agitation, so the delegate's own gaps kept the axis UNKNOWN for another reason. M94: the T1 fixture injects a stale `capability-profile-v1alpha1` snapshot, refused by the profile's own schema check (not the legacy law) — rebuilt with a current v1alpha2 snapshot, both legacy layers severed → loads; M94b pins the any-depth scan. M38: the attacker recomputed only `capability_question_digest`, so the PUBLIC `result_digest` refused it — rebuilt with an attacker that rewrites every carried `profile_digest` and re-serializes through the public codec (all unkeyed digests recomputed): honest REFUSED by the rebind re-derivation alone; one anchor (`if r.capability_assessment != rederived:`) severs it → the stale assessment loads. M38b pins the profile-digest binding (no mutant before). M104: **proved unkillable as a single guard** — FIT ⇒ tier == PROCESS_SPECIFIED (top rung) ⇒ the 0.8 thin-PS law refuses first; rebuilt as a 2-factor mutant (thin-FIT guard × tier binding; each single-factor cell still refuses = mutual defence-in-depth); M104b pins the tier binding alone. Side defects: `_check_verified_admission` re-projects summaries WITHOUT the capability profile; an unknown readiness tier raises `KeyError` not `ValueError`; the 0.8 thin law tests `== PROCESS_SPECIFIED` (safe only while PS is the top rung). |
| A-PHYS (F-1/F-10/F-11-phys) | F-1 VERIFIED (typed 77 K COOL op → FIT; the low side is structurally unread). F-10 VERIFIED (prose "650 C furnace"/"50 atm autoclave" "covered" by any process extremum → FIT). **NEW P4/P5**: MAX-over-stated is unsound — a HEAT/DISTILL op with NO temperature is masked by an unrelated lower statement (non-monotone UNKNOWN→FIT). **NEW P-X2**: isopentyl `peak_temperature_k=416.15` is DERIVED from the distillate HEAD range — a lower bound on the heat demand, so it can certify a 420 K bench FIT. **NEW P-X3**: aspirin's record claims `min_pressure_atm=1.0` although its own source vacuum-filters; `research_lab` owns VACUUM_FILTRATION yet declares a 1.0 atm floor (self-contradictory declared world). F-11 physical REFUTED (a declared finite 1e300 K ceiling is the user's declaration; physical dims can never be NO_LIMIT). |
| A-TIME (F-2/F-3/F-8/F-11-proc) | F-2 VERIFIED ("3 weeks" prose → FIT). F-3 VERIFIED (3×60-min ops vs a 90-min record ceiling → FIT; F-3b: a provable 180-min floor never BLOCKs). F-8 VERIFIED in seven shapes (None/empty record → UNCONSTRAINED passes the fold; `workup_included=False` under NO_LIMIT → FIT; PERIODIC with no check interval → FIT). Corpus census: no prose `op.duration`; every process record SUMMARIZES its ops (summing would double count). F-11 process REFUTED (time dims are operator PREFERENCES; a declared 1e300 is the operator's word). |
| A-LEDGER (F-4/F-9) | Full field ledger. D13 holes reproduced on real `compile`+`assess`: PRESENT `rate`, `agitation`, `endpoint`, prose `duration`, prose `temperature/pressure` reach no axis (FIT/NA); F-4 (consumable masks a missing still, non-monotone) + **F-4b** (a thermometer discharges a DISTILL op); **P5b** a second VERIFY op with no apparatus is masked by step-pooling (live in the corpus: aspirin's "ferric-chloride purity test" has no typed VERIFY op); the corpus files one axis's demand inside another axis's prose field (paracetamol op2 quantity "swirl on a steam bath for 4-8 minutes"; op6 temperature "sit ~1 hour"). |
| A-WASTE (F-6/F-7/medium/zero-FIT) | F-6 VERIFIED (untyped materials of ADD/QUENCH/MIX/HEAT/HOLD/COOL ops produce no waste obligation). F-7 VERIFIED (a net-consumed reactant relabelled CATALYST converts an unresolved residual into a RESOLVED `HAZARDOUS` category). Part IV VERIFIED (every corpus `medium` is condition prose; the isopentyl sentence becomes a fake species, a hazard-unresolved entry and a fake spent stream). **Zero-FIT theorem PROVEN** for every route (HARD LAW; T0 spent-stream: PROCESS_SPECIFIED ⇒ workup PRESENT ⇒ a SEPARATE/FILTER/DRY/WASH op ⇒ an unresolved stream, exhaustive over the closed enums; T1 leaf complementarity; T2 empty-GHS byproducts). **Evaluator-reachability witness**: a real PROCESS_SPECIFIED route (2 MeOH → DME + H2O via the real capped-scission transform, sourced complete procedure) is FIT on every axis except waste, and overall FIT once only waste is discharged. **NEW S1/S2** (material axis): route-wide leaf suppression hides a later step's consumption; `leaf_inputs` ignores step order. |
| A-PHASE (Part III/Part V/F-5) | Phase evidence finding VERIFIED (ungraded phase certifies FIT on a match and BLOCKED on a mismatch; the corpus comment admitting an author inference is itself wrong — the page says "5% aqueous sodium bicarbonate", line 124). Kernel identity VERIFIED (editing a V1 kernel's arithmetic leaves every stored record/digest verifying). K1–K6 held; **NEW partial break**: `CLAMP_TO_UNIT_INTERVAL_V1` over an assay range ≥ 100% mints CLAMPED [1, 1], which the pure-material witness accepts. |
| A-WIRE (C2/noninterference/schemas/goldens) | C2 items ALL LANDED + tested (table §7.3); binding mutants missing for route/profile/readiness bindings, the question→`result_digest` fold and the frozen v0.8 omission set. Public-hash attack matrix: every stale-assessment tamper is refused by a SEMANTIC re-derivation (stock strip → rebind; tier transplant → readiness re-derivation; replay quantity edit → route-identity bind / rebind). **(d) P1 (latent P0 once FIT is reachable)**: a coherent profile swap (every assessment honestly re-derived under another bench) loads even under `expected_request_digest` — the consumer has no capability-question pin. **(g) P1**: `capability_profile_origin` is outside every digest (incl. the signed one) yet is rendered as `CAPABILITY[origin]`. (c3) boundary: a self-consistent replay of a TAMPERED procedure (readiness + assessment honestly re-derived) loads without FIT — coherence ≠ authenticity; only the producer HMAC binds the shipped source. P2: `test_rebind_refuses_an_altered_profile_snapshot_on_the_wire` passes for the wrong reason (public `result_digest`, not the rebind). P3: `RankedDAGSummary` replay ops now REQUIRE `material_uses` with no schema bump. **Search noninterference HOLDS on the current tree**: isopentyl acetate (27 candidates) and methyl acetate (2) — normalized target, semantic_digest, transform registry, search receipt (incl. telemetry: 307 nodes / 12560 transforms / 410 emitted / 27 returned), IR digest, candidate order, completeness and search_space_status byte-identical across no-profile / research-lab / poor-man / custom; request digest, capability_question_digest, result_digest and assessments differ as designed. Goldens: all 6 regenerated byte-identical (current); none exercises `--capability-profile`. `test_v0_9_round_v_schema_migration.py` 60 passed. |

### §7.2 Parent barrier — decisions D14–D23 (Wave B′ builds ONLY against these)

**D14 — The physical range is a RANGE (F-1, F-10, P4/P5, P-X2, P-X3).**
* `PhysicalBounds` (the ONE shared leaf — no second T model) gains `min_temperature_k: float | None = None`,
  appended LAST (two positional call sites). Validation: finite, positive, `<= max_temperature_k` when both set.
  `constrains_anything`/`describe` include it (`T>=… K`). `PHYSICAL_BOUNDS_SCHEMA` → `physical-bounds-v1alpha2`;
  `v1alpha1` stays constructible/decodable ONLY with `min_temperature_k is None` (legacy); `_V08_OMITTED_FIELDS`
  gains the field so real v0.8 payloads re-encode byte-for-byte. Legacy `None == unconstrained` is unchanged for
  every legacy caller. `ConstraintBox` applies the floor exactly like `min_pressure_atm` (env `temperature is None`
  → gap; `temperature.lo < floor` → EXCLUDED; a process branch has no whole-step minimum → gap). `--min-temp` on
  both CLIs.
* Route projection (requirements): HIGH = max(process peak, envelope `.hi`, op Interval `.hi`); LOW = min(envelope
  `.lo`, op Interval `.lo`). **Unread demands → `physical_unresolved`:** (i) any PRESENT op temperature/pressure
  that is not a typed K/atm `Interval` — NO same-step coverage, NO typed "summarized-by" relation (F-10);
  (ii) a HEAT/HOLD/DISTILL op with no typed temperature on a step whose process record has no
  `peak_temperature_k` (the record's own docstring defines the peak as the whole-step extremum — the only
  legitimate cover); (iii) a COOL/HOLD op with no typed temperature (no whole-step minimum exists to cover the low
  side); (iv) a step with no `ProcedureEvidence` — its HIGH side is covered only by a process peak, its LOW side is
  unread. `ProcessRequirements` (a 0.8 type inside every route digest) is NOT extended.
* Assess: a min-temperature block + a per-dimension row (route LOW vs profile floor: undeclared floor against a
  real low demand → UNKNOWN; LOW < floor → BLOCKED). FIT requires `floor <= LOW` and `HIGH <= ceiling`.
* Data (P-X2/P-X3, truth over a prettier matrix): isopentyl `peak_temperature_k` → `None` (the source states only
  the distillate head range, a LOWER bound on the heat demand; a whole-step peak is not derivable — one-sided
  lower-bound demands are a 0.9.5 item); aspirin `min_pressure_atm` → `None` (its own source vacuum-filters).
  Presets: a floor follows ONLY from the preset's own declared equipment — both presets own `ICE_BATH` →
  `min_temperature_k = 273.15` (DERIVED: ice–water equilibrium at 1 atm); `research_lab` owns VACUUM_FILTRATION,
  so its `min_pressure_atm` becomes `None` (reachable vacuum undeclared) instead of the self-contradictory 1.0.
* F-11 (physical): REFUTED — a declared finite bound is the declared world; no magnitude threshold.

**D15 — The per-step procedure TIMELINE and an independently-correct process axis (F-2, F-3, F-8, F-11, M86).**
* Timeline (requirements, pure): ops are a TOTAL order (concurrency is inexpressible → never invented). Per step:
  `op_floor = Σ lo` over typed-minutes op durations; a PRESENT op duration that is not a typed `min` Interval →
  `process_unresolved` (F-2). Floors from different representations of the SAME wall-clock combine by **MAX**
  (op_floor, `envelope.duration.lo`, record `min_elapsed_minutes`, record `elapsed.lo`) — never summed across
  representations (no double count). Only the record's `elapsed_minutes.hi` is a ceiling (an op sum is never a
  ceiling). `floor > ceiling` → contradictory time evidence → `process_unresolved` (UNKNOWN, never a guessed
  BLOCK). The effective record handed to the UNCHANGED delegate carries `min_elapsed_minutes = floor`
  (`dc.replace`), so the delegate's existing floor exclusions now see ordered ops (F-3b: 3×60 with a 30-min record
  floor vs a 120-min bench → BLOCKED).
* Process axis law (F-8), always applied, NO_LIMIT waives ONLY the three time preferences:
  (1) whole-step coverage gate — a step whose record is `None`, not `is_declared`, or `workup_included=False` →
  UNKNOWN; (2) profile declaration gaps — each of `max_step/max_total/max_active` UNDECLARED (not NO_LIMIT),
  `allowed_attention is None`, `allowed_agitation is None`, or `min_check_interval_minutes is None` while any step's
  attention is PERIODIC or undeclared → UNKNOWN; (3) the UNCONSTRAINED→FIT branch is DELETED: the process axis is
  never UNCONSTRAINED for a route with ≥1 step (every real step spends time, attention and an agitation mode);
  (4) a PRESENT `op.rate` → `process_unresolved` (no rate-control coordinate exists; no pump ontology); a PRESENT
  `op.agitation` → `process_unresolved` (no typed relation to the record's `Agitation`); (5) timeline unresolved
  caps at UNKNOWN; a provable EXCLUDED still wins. Presets are NOT given new time numbers (no convenient values):
  preset process honestly stays UNKNOWN.
* Retained 0.8 semantics (documented, not deferred): the delegate EXCLUDES when a step's elapsed CEILING exceeds
  the operator's limit — under the time-preference reading the operator's limit is a guarantee the route cannot
  give (a possible false BLOCK, never a false FIT).
* F-11 (process): REFUTED — the three time dims are operator preferences.

**D16 — The D13 field-coverage theorem is MACHINE-CHECKED (F-4, F-9, F-10).**
* New `smartchem/capability/coverage.py`: `FieldOwner{MATERIAL, PHYSICAL, PROCESS, EQUIPMENT, MEASUREMENT, WASTE,
  READINESS_ONLY, PRESENTATION_ONLY, OUTSIDE_0_9_SCOPE, CONTAINER, ROUTING_KEY}` and `FIELD_COVERAGE` keyed by
  (type, field) over `ProcedureEvidence`, `ProcedureOperation`, `ProcedureMaterialUse`, `EvidenceField`,
  `ConditionEnvelope`, `ProcessRequirements`, `ExperimentStep`, `ExperimentRoute`, each entry = primary owner + the
  fail-closed law for a PRESENT untyped value; `missing_coverage()` returns every dataclass field absent from the
  table and every stale entry. A test fails on any uncovered field, so a new field cannot be added silently.
* Per-owner laws: EQUIPMENT — per-OP post-resolution guard: every hardware op (HEAT/HOLD/COOL/DISTILL/SEPARATE/
  FILTER/DRY) must resolve ≥1 recognized NON-consumable capability ADMISSIBLE for its kind (closed table: HEAT
  {CONTROLLED_HEATING, WATER_BATH}; HOLD {CONTROLLED_HEATING, WATER_BATH, REFLUX_CONDENSER, ICE_BATH}; COOL
  {ICE_BATH}; DISTILL {SIMPLE_DISTILLATION, FRACTIONAL_DISTILLATION}; SEPARATE {SEPARATORY_FUNNEL}; FILTER
  {GRAVITY_FILTRATION, VACUUM_FILTRATION}; DRY: any non-consumable), else unrecognized; the step record's
  `equipment` never discharges an op (F-4, F-4b). MEASUREMENT — per-VERIFY-op guard (each VERIFY op must resolve ≥1
  method or be unrecognized — kills P5b); a PRESENT prose `op.endpoint` → `measurement_unrecognized` (no typed
  endpoint carrier; `PH_INDICATOR` is NOT added — a member no evidence path can emit would be decorative).
  PROCESS/PHYSICAL — D14/D15. MATERIAL — F69-analog: raw text is display ONLY where a typed representation exists:
  `op.quantity` PRESENT on an op that carries NO quantified typed use → material unresolved; otherwise it is the
  display form of the typed uses (typed fields are authoritative — the same trust model as `formulation` vs
  `specification`). `scale`, the whole-procedure summary values (`separation/wash/drying/purification`),
  `unresolved_omissions`, `evidence_scope`, `reaction_scope` → READINESS/PRESENTATION (the HARD LAW is the
  backstop; recorded in the ledger).
* Theorem boundary (stated, not hidden): every PRESENT prose field forces UNKNOWN on its OWN axis, so the fold
  guarantees overall ≤ UNKNOWN; a demand MISFILED into another axis's prose field is caught on the host axis, not
  attributed to its owning axis. Authored corpus data is re-filed by hand (paracetamol op2 "4-8 minutes" →
  `Interval(4, 8, "min")`) and a curated corpus lint pins filing, verification-method ↔ VERIFY-op pairing and
  summary-technique ↔ op pairing. Aspirin gains the sourced FeCl3 VERIFY op (`materials=("ferric chloride",)`,
  `apparatus=()`) → measurement + material honestly UNKNOWN.

**D17 — Material conservation, role consistency, medium, step order (F-6, F-7, Part IV, S1, S2).**
* F-6: every `op.materials` string not covered (exact-fold `_name_covers`) by a typed use OF THAT OP yields an
  unresolved waste obligation ("step s op #n K/R introduces untyped material 'X'"), on every op kind incl. spent-
  stream ops; import-time totality guard `{CATALYST} ∪ _CONSUMED_ROLES ∪ _SPENT_STREAM_ROLES == set(ProcedureMaterialRole)`.
* F-7: a known-identity CATALYST use that its own step `net_consumes` → the material requirement carries an
  unresolved term "role contradiction" and waste treats it as an unresolved residual (never a resolved catalyst
  category); converse: a known-identity SUBSTRATE/REACTANT use its step does NOT net-consume → unresolved term.
  Caught at requirement compilation (fail closed), NOT in `ExperimentStep` (would perturb search) and NOT as a
  raise (one bad field must not become a service error).
* Part IV: `envelope.medium` is provenance ONLY — both medium readers are DELETED. A step WITHOUT
  `ProcedureEvidence` gets a text-free `material_unresolved` remainder on `RouteCapabilityRequirements` ("step s
  has no ProcedureEvidence: its auxiliary/medium material demand is unread") → material UNKNOWN (BLOCKED wins). A
  corpus review test lists each medium's material words against their typed uses.
* S1/S2: the capability projection computes external inputs PER STEP IN ORDER (an input is internal only if an
  EARLIER step produced it); a step that net-consumes an external input with no stoichiometric typed use OF ITS
  OWN keeps its own `unstated(1)` requirement. `ExperimentRoute.leaf_inputs` itself is not changed (search/ranking
  consumers); the monetary basket uses the same order-aware set.
* **Zero-FIT theorem (Part VII): PROVEN; ceiling = a missing EVIDENCE TYPE, not a broken evaluator.** Pinned by
  tests: T0 enumeration over the closed op enums, T1 property test, and the evaluator-reachability witness (the
  real DME route's compiled requirements with only `waste` replaced by a discharged `WasteRequirement` → overall
  FIT under the fully-declared profile — which also proves D14–D17 leave FIT reachable in a fully-typed world).
  `StreamDisposition` (typed consumption/recovery/routing with a closed subject binding, certifying-evidence-only
  discharge) is PARKED to 0.9.5 with an exact boundary: no cited corpus page states disposal (no fake data), and
  byproduct→stream binding needs its own adversarial pass.

**D18 — Phase is an evidence-graded claim (Part III, F-5 CLAMP).**
* Parent-authored in `material_spec.py`: `PhaseClaim(phase: Phase, evidence: EvidenceKind, note="")` (no new phase
  enum; `Phase.UNKNOWN` refused as a claim — unknown is absence) and `compare_phase(required, stock)` with
  `_compare_state`'s exact law: match/mismatch decide ONLY with certifying evidence on both sides, else
  UNDETERMINED; no stock claim → UNDETERMINED.
* `ProcedureMaterialUse.phase: PhaseClaim | None` (replaces the scalar in place — stale callers fail loudly);
  `MaterialRequirement.phase: PhaseClaim | None`; `StockMaterial` keeps legacy `phase: Phase` and gains
  `phase_evidence: EvidenceKind = UNKNOWN` (invariant: phase UNKNOWN ⇒ evidence UNKNOWN) + a `phase_claim`
  property; `_edge` consumes ONLY claims. Library bench bottles → USER_DECLARED. Corpus phases classified per use
  (SOURCE_QUOTED only where the cited page says it; else AUTHOR_INFERRED).
* The pure-material G⁻ witness excludes CLAMPED evidence (a clamp to [1, 1] proves the quoted quantity was not a
  fraction, not that there is no impurity).
* Honest consequence, accepted: the vinegar-for-glacial and wrong-phase isopentyl benches move BLOCKED → UNKNOWN
  (their BLOCK rested only on an ungraded phase).

**D19 — Derivation-kernel semantic identity (Part V).** `derived_evidence.KERNEL_KNOWN_ANSWERS` (frozen vectors per
kernel incl. boundary and refusal cases) verified at import; a test pins per-kernel semantic-descriptor digests and
AST digests of every kernel fn and its arithmetic helpers. Contract (1.0 compatibility docs): *a DerivationKernel
member names ONE immutable function; any change — including a bug fix — mints `X_V2` with its own vectors; `X_V1`
keeps its implementation forever; retiring a member (refusing NEW records) is allowed, changing one is not.*
Content-addressing the descriptor digest inside `IntervalEvidence` is PARKED to 0.9.5.

**D20 — Transport (Part VI): semantic coherence under a keyless attacker; authenticity only where a key exists.**
* Threat model restated: every unkeyed digest is recomputable by an attacker; `producer_signature` (HMAC) is an
  OPTIONAL authenticity layer, never a substitute for semantic coherence. A carried assessment must be refused
  whenever it is stale relative to the carried evidence, after the attacker recomputes every public pin.
* Fixes: (1) `_check_verified_admission` re-projects summaries WITH the request's capability profile;
  (2) `CapabilityAssessment` refuses an unknown `readiness_tier` with `ValueError` (never `KeyError`); (3) the 0.8
  thin law uses `tier_rank(tier) >= tier_rank(PROCESS_SPECIFIED)` (survives a ladder extension); (4) **(d)**
  `response_from_payload(..., expected_capability_question_digest=...)` — the consumer's capability-question pin,
  fail-closed on None-vs-set mismatch (the capability analogue of `expected_request_digest`); (5) **(g)**
  `capability_profile_origin` must be `""` or equal the snapshot's `profile_id` (content-bound through the profile
  digest) — enforced at `CompilationRequest` construction, so a relabel cannot load; (6) `RankedDAGSummary` bumps
  (its replay ops now require `material_uses`) with an explicit legacy decode; (7) the snapshot-tamper transport test
  is rebuilt as the full public-hash attacker with `match="replayed evidence does not support"`; (8) a CLI golden
  exercising `--capability-profile` is added after the freeze.
* VERIFIED BOUNDARY (not a defect of coherence): (c3) a keyless attacker can ship a self-consistent response for a
  TAMPERED procedure (route digest re-bound, readiness + assessment honestly re-derived from the tampered replay).
  It describes a DIFFERENT route (its `route_digest` is not the corpus route's) and is coherent; binding a replayed
  `ProcedureEvidence` to the SHIPPED source table (source-subject binding) is a 0.9.5 item; until then only the
  producer HMAC or a consumer route-digest pin authenticates the source.

**D21 — Mutation gate.** Rebuild M38 (+M38b), M86 (law-level, refactor-robust anchor), M94 (+M94b), M104 (2-factor,
+M104b) exactly as A-SURV ran them; add M106+ for every D14–D19 law (list in §7.4); harness fixture defaults move
to certifying phase claims and a clean fully-declared process pair so no mutant survives for a fixture reason.
ACTIVE/RETIRED/DEFERRED reported separately; target ACTIVE X/X, DEFERRED 0.

**D22 — Schema freeze (every changed shape bumps ONCE; WIP-only ids are never migrated — they were never released).**

| artifact | main@df1b38d | WIP `78554a2` | final | change in this continuation |
|---|---|---|---|---|
| PhysicalBounds | v1alpha1 | v1alpha1 | **v1alpha2** | +`min_temperature_k` (v1alpha1 accepted only with it `None`; `_V08_OMITTED_FIELDS` entry) |
| StockMaterial | v1alpha1 | v1alpha2 | **v1alpha3** | +`phase_evidence` |
| MaterialComponent | v1alpha1 | v1alpha2 | v1alpha2 | — |
| CapabilityProfile | — | v1alpha2 | **v1alpha3** | embeds PhysicalBounds v2 + StockMaterial v3 |
| CapabilityAssessment | — | v1alpha2 | v1alpha2 | shape unchanged (tier validation is a law, not a shape) |
| CompilationRequest | v1alpha5 | v1alpha6 | **v1alpha7** | embeds PhysicalBounds v2 + profile v3; origin law |
| RankedRouteSummary | v1alpha3 | v1alpha4 | **v1alpha5** | replay use `phase` → PhaseClaim |
| RankedDAGSummary | v1alpha4 | v1alpha4 (P3: silently changed) | **v1alpha5** | replay ops require `material_uses`; v1alpha4 decoded as legacy |
| CompilationResponse | v1alpha15 | v1alpha16 | **v1alpha17** | embeds the above |
| response descriptor | `…schema-v1alpha18` | v1alpha19 | **v1alpha20** | disclosure text + fields |
| ProcessBounds / ProcessRequirements / ConditionEnvelope | unchanged | unchanged | unchanged | — |

Legacy acceptance stays EXACTLY the released v0.8 set (request v1alpha5, response v1alpha15 + their embedded
v1alpha1/v1alpha3/v1alpha4 shapes), re-verified byte-for-byte against the REAL `git archive df1b38d` fixtures.

**D23 — Wave B′ file ownership (one writer per file; a writer needing a change in another's file asks the parent).**

| writer | owns (code + its tests) | decisions |
|---|---|---|
| parent | `smartchem/material_spec.py` (`PhaseClaim`, `compare_phase` — frozen law), this audit doc, integration, `tests/test_v0_9_round_v_wave_c_fixes.py` | D18 law |
| W-BOUNDS | `smartchem/constraints.py`, `smartchem/experiment/drafter.py`, `smartchem/experiment/cli.py`, their tests | D14 leaf + ConstraintBox + experiment CLI |
| W-STOCK | `smartchem/experiment/stock.py`, `smartchem/data/material_library.py`, `smartchem/data/derived_evidence.py`, stock/library/kernel tests (NEW `tests/test_v0_9_kernel_semantic_lock.py`) | D18 stock side, D19 |
| W-SOURCE | `smartchem/procedure_evidence.py`, `smartchem/decompiler_conditions.py`, procedure/authoring/corpus-lint tests | D18 use side, D14 data (P-X2/P-X3), D16 corpus re-filing + FeCl3 VERIFY op + lint, D17 medium review test |
| W-CORE | `smartchem/capability/requirements.py`, `assess.py`, `quantity.py`, `equipment_resolver.py`, `measurement_resolver.py`, NEW `coverage.py`, core capability tests (NEW `tests/test_v0_9_round_v_xhigh_core.py`, NEW `tests/test_v0_9_round_v_field_coverage.py`) | D14 route/assess, D15, D16, D17 material side, D18 `_edge` + CLAMP |
| W-WASTE | `smartchem/capability/waste.py`, `declarations.py`, `profile.py`, `presets.py`, `enums.py`, their tests | D17 waste side, D14 preset floors/P-X3 preset, profile v1alpha3 |
| W-WIRE | `smartchem/service.py`, `smartchem/cli.py`, `tests/fixtures/**`, wire/CLI/migration/transport tests, goldens (regenerated ONLY after the parent announces the freeze) | D20, D22, `--min-temp` on `smartchem` CLI, PhaseClaim codec |
| W-GATES | `experiments/v0_9_mutation_calibration.py`, `experiments/v0_9_capability_funnel.py` (+ results doc), NEW held-out probe harness + results, NEW `tests/test_v0_9_round_v_zero_fit_theorem.py`, ROADMAP, 0.9.5 plan, release record | D21, Part VII pins, Part VIII, Part XI |

### §7.3 Part VI — C2 transport table (read from CURRENT code at `78554a2`, before Wave B′)

| C2 item | landed | test | mutant | boundary / action |
|---|---|---|---|---|
| assessment self-fold validation | YES `assess.py` `CapabilityAssessment.__post_init__`, re-checked service-side | wave_c_fixes; migration `test_smith_P0_thin_wire_forged_capability_fit_is_refused`; transport verdict-alteration test | M101 | unknown tier raises `KeyError` → D20(2) |
| readiness tier/digest binding | YES `_check_assessment_bindings` | migration parametrized binding test | none (M90 pins only that `assess` records the tier) | add M104b |
| profile digest binding | YES | same | only M19 (whole-method) | add M38b |
| route digest binding | YES | same | none | add a route-binding mutant |
| capability_question_digest folded into result_digest | YES | `test_smith_P2_signature_binds_the_capability_question_with_zero_dossiers` | none | add a fold mutant |
| no CAPABILITY_FIT on THIN | YES | unit-level stand-in | M104 survived (dominated by the 0.8 thin-PS law) | 2-factor M104 |
| all-depth legacy-key refusal | YES (request + response) | T1/T4b + any-depth tests | M94 survived (stale fixture) | rebuilt M94 + M94b |
| newly-resolvable legacy name hint | YES | `test_smith_P2_real_v08_name_the_resolver_now_registers_…` | none (message quality, not a law) | — |
| legacy v1alpha15 response admission | YES | real-fixture tests (incl. verified admission, procedure routes) | M81, M59 | — |
| frozen v0.8 digest rule | YES `_V08_OMITTED_FIELDS` / `_v08_digest` | frozen-rule tests | M81 (dispatch only) | add an omission-set-widening mutant |

Public-hash attacker (unsigned; every unkeyed pin recomputed) — outcome at `78554a2`: stock strip → REFUSED by the
capability rebind; PS-tier transplant → REFUSED by the readiness re-derivation; replay quantity edit → REFUSED by the
route-identity bind (and, with the route digest re-bound, by the rebind); forged FIT on thin → REFUSED by the 0.8
thin-PS law; forged FIT on thick → REFUSED by the rebind; forged FIT below PS → unconstructible (fold). LOADED:
(c3) a self-consistent tampered-procedure replay (no FIT; coherence ≠ authenticity — D20 boundary); (d) a coherent
profile swap under the consumer's request pin (D20(4) closes it for pinning consumers); (g) an origin relabel, even
under a verified producer signature (D20(5) closes it).

### §7.4 Wave C′ — fresh non-author hostile review of the integrated D14–D22 tree (`941946a`)

Six NEW adversaries, none of whom authored any Wave B′ code: A dalembert (demand coverage), B amber (conservation),
C smith (evidence laundering), D evil-morty (transport), E kutner (seeded per-axis chaos), F citadel-rick
(genericity). Brief: `scratchpad/r5x/WAVE_C2_BRIEF.md`; probes in `scratchpad/r5x/waveC2/<lane>/`. No reachable
OVERALL false FIT was found (the zero-FIT theorem holds). Per-axis false FITs were found and are P0-LATENT by the
brief's rule — every one is FIXED by D24 below; nothing is waved through because "overall stayed UNKNOWN anyway".

| id | sev | finding (Verified by the adversary with a reproducer) | disposition |
|---|---|---|---|
| A1 | P0-latent | `op.quantity` "display trust": "5 L methanol" / "+ 2 g sodium metal" / "sealed tube 650 K 50 atm 3 days" beside a typed quantified use → material/containment/physical/process FIT on a REAL PROCESS_SPECIFIED route; the D16 corpus lint is a foolable word blacklist | D24.1 |
| A2 | P0-latent | `analytical_verification` value ("1H NMR and HPLC ≥ 99.5 %") ignored once any VERIFY op names any apparatus → measurement FIT | D24.1 |
| A3 | P0-latent | PRESENT whole-procedure summary values (vacuum distillation at 1 mmHg, vacuum oven 0.01 atm 390 K 48 h, dry-ice quench 195 K, 5 L scale) reach no axis; D16's "HARD LAW backstop" rationale is inverted (a PRESENT summary is what EARNS PROCESS_SPECIFIED) | D24.1 |
| A4 | P0-latent | `EvidenceField(EXPLICIT_NOT_APPLICABLE, value=Interval(650 K))` is schema-valid, `is_present=False`, and every reader skips it → FIT | D24.2 |
| A5 | P0-latent | `envelope.medium="benzene"` on a step WITH ProcedureEvidence → material FIT (Part IV over-corrected) | D24.3 |
| A6 | P0-latent | a MIX op reaches no axis (record agitation NONE, bench NONE → process FIT) | D24.4 |
| A9 | P2 | non-empty `formulation` + EMPTY `MaterialSpecification()` → material FIT | D24.1 |
| A-P3 | P3 | a demand misfiled into a PRESENTATION host (evidence_scope, justification, locator, provenance) escapes | D24.1 boundary text |
| B1 | P0-latent | a STATE-only spec (NEAT/ANHYDROUS/SATURATED) makes ANY bottle listing the species a proven 1:1 G⁻ draw — incl. a 1 % bottle, a `[0, 0]` phantom component and the CLAMPED library MgSO4 (D18 bypass); non-monotone; the LIVE corpus brine spec is armed | D24.5 |
| B2 | P0-latent | internal supply unmetered: ANY earlier product (byproducts included) feeds every later consumer with no demand; one water byproduct spent twice (D17 S1/S2 text defective) | D24.6 |
| B3 | P2 | a material named only in `op.quantity` / `medium` prose on a procedure step reaches no axis | D24.1 / D24.3 |
| C1 | P0-latent | the pure witness reads only the matched species: water `[1, 1]` USER_DECLARED beside NaCl 0.3 g/mL (or 6 M) is a "pure" water bottle → FIT; the K3 feasibility sum skips non-fraction bases | D24.5 |
| C2 | P2 | a certified NEAT claim is never checked against the same bottle's certified composition (50 % acid + 50 % water "NEAT") | D24.5 |
| C3 | P2 | the D19 kernel lock misses helpers on the recompute path (`TypedInput.exact`, `IntervalEvidence.interval`, `exact_fraction`) and binds kernel→fn only by `__name__`: a rounding drift passes all 12 lock tests and flips UNKNOWN→FIT | D24.9 |
| C4 | P3 | CLAMPED `[1, 1]` still certifies a composition FLOOR (the D18 exclusion applied only to the purity witness) | D24.7 |
| C5 | P3 (false BLOCK) | AQUEOUS_SOLUTION demand vs a truthfully LIQUID brine → VIOLATES (AQUEOUS_SOLUTION ⊂ LIQUID) | D24.7 |
| C6 | P3 (false BLOCK) | identity requirement vs a bottle keyed only by the same NAME → "absent" BLOCKED (weaker evidence ≠ proof of absence) | D24.8 |
| C7 | P3 | the library's bench bottles are repo-authored "USER_DECLARED" worlds; a stale fit-positive docstring claims material FIT | D24.10 (documented boundary + docstring) |
| C8 | P3 | stock-side SOURCE_QUOTED/DERIVED/CLAMPED phase/state kinds carry no locator (no power gain: USER_DECLARED already certifies) | VERIFIED DEFER → 0.9.5 source-subject binding (no verdict changes; exact boundary: stock-side sourced kinds certify exactly as USER_DECLARED) |
| D-L1 | **P1 / P0-latent** | `compilation_ir.identity_losses` is trusted, never re-derived from the carried request: a keyless attacker strips the stereo loss, forges readiness PROCESS_SPECIFIED on the canonical wire, keeps the corpus route's own `route_digest`; loads under request pin + question pin + verified admission | D24.11 |
| D-O1/O2 | P2 | `profile_id` is free text, so the D20 origin law binds to nothing: `research_lab()` relabelled `profile_id="poor-man"` loads and renders `CAPABILITY[poor-man]: UNKNOWN` (refused only under the question pin) | D24.12 |
| D-G1 | P2 | capability profile + CAPPED_SCISSION_CONVERGENT (a pair the producer REFUSES) loads with DAG dossiers and no assessment | D24.13 |
| D-D1 | P2 | a BLOCKED dossier can be deleted (ranked ⊆ IR candidates only) — the loaded answer silently omits a verdict | D24.14 |
| D-B2 | P3 | `CapabilityProfile` v1alpha3 accepts an embedded PhysicalBounds v1alpha1 (split digests for identical benches) | D24.15 |
| D-T1 | P3 | a THIN plain load keeps no trust marker (an advisory assessment is indistinguishable after load; FIT/PS on thin still refused, verified admission refuses) | VERIFIED DEFER → 0.9.5 (exact boundary: thin plain loads are ADVISORY by contract; trust requires the canonical wire or `require_verified_admission`; the loaded object does not record which — a trust-tier field is a 0.9.5 shape change) |
| F1 | P2 (false BLOCK) | `"distillation apparatus" → FRACTIONAL_DISTILLATION` alias (a Round-III forcing-matrix convenience; the page says "Set up the distillation apparatus as described by your instructor … collect the fraction between 134 and 143 °C" — a boiling-range cut, not a fractionating column) BLOCKs a SIMPLE-only bench | D24.16 |
| F-gen | held | two held-out non-corpus procedures (benzoic-acid recrystallization; cyclohexene bromination) fail closed on every axis for structural reasons; zero compiler literals in decision logic | — |

### §7.5 Barrier amendment D24 (post-Wave-C′; supersedes the D16 "display trust" model and D17 S1/S2 text)

**D24.1 — Prose is DISPLAY only when it is byte-equal to the CANONICAL RENDERING of the typed fields it summarizes;
otherwise it is an unread demand on a NAMED host axis.** (No prose parser; a mechanism a word cannot fool.) Canonical
renderings (pure functions in `capability/coverage.py`, used by the projection and by authors):
* `op.quantity` ↔ `render_op_quantity(op)` = the op's QUANTIFIED typed uses, in use order, `"<value> <unit> <name>"`
  joined by `" + "` (empty when none) → else `material_unresolved`;
* `analytical_verification.value` ↔ `render_verification(procedure)` = the sorted resolved `MeasurementMethod`
  values of the VERIFY ops joined by `"; "` → else `measurement_unrecognized`;
* `quench/workup_isolation/separation/wash/drying/purification` value ↔ `render_summary(procedure, field)` = the
  realizing ops `"op <n> <KIND>/<ROLE>"` joined by `"; "` → else `process_unresolved` (host = PROCESS: the procedure
  as summarized cannot be certified executable);
* `scale` value ↔ `render_scale(procedure)` = the quantified SUBSTRATE/REACTANT uses (op order) → else
  `material_unresolved`;
* a non-empty `formulation` beside an EMPTY specification → an unresolved term (F69 extended); a non-empty spec keeps
  D3's author-transcription contract (the mission's endorsed "raw formulation prose is provenance only");
* a vacuum-capable op (resolved `VACUUM_FILTRATION`) with no typed pressure is an unread LOW-pressure demand unless
  the step record's `min_pressure_atm < 1` covers it; a record `min_pressure_atm >= 1` beside a vacuum op is
  contradictory → `physical_unresolved` (vacuum means sub-atmospheric by definition, not a tuned threshold).
Theorem boundary restated: every PRESENT slot is either read into its axis, canonically rendered from typed fields,
or unread on its named host axis; PRESENTATION-only hosts (`evidence_scope`, `justification`, locators, notes,
provenance) are OUTSIDE the theorem and carry no demand by contract.

**D24.2** `EvidenceField(EXPLICIT_NOT_APPLICABLE, …)` must carry `value is None` (a closing-out claim cannot state a
value). Real v0.8 fixtures and the corpus were checked for N/A-with-value before the tightening.

**D24.3** A non-empty `envelope.medium` on a step WITH ProcedureEvidence that is not exact-fold-covered by a typed use
of that step → a text-free `material_unresolved` note ("step s: envelope.medium is untyped condition prose; any
material it names is unread"). It is still NEVER a species, a hazard entry or a waste stream (Part IV stands).

**D24.4** A MIX op on a step whose record agitation is `None` or `Agitation.NONE` → `process_unresolved`.

**D24.5 — Commensurability (G⁻) is earned, never implied by a state word.** A matched component whose certified upper
bound is 0 is ABSENT. The pure witness additionally requires every OTHER component of the bottle to have lower bound
exactly 0 on ANY basis (C1). Spec-commensurability: a SATISFIED composition constraint, OR a SATISFIED formulation-
defining state (SOLUTION / SATURATED / UNSATURATED) with the matched component's certified lower bound > 0; NEAT /
ANHYDROUS / HYDRATE never make an edge commensurable on their own (they describe the species; the pure witness or a
satisfied composition must carry the quantity). A NEAT claim is dropped (UNDETERMINED) when another component of the
same bottle has a certified lower bound > 0 (a positive diluent contradicts it, C2).

**D24.6 — Internal supply is metered.** For step k of a linear route, a species is internal ONLY if it is step k−1's
carried TARGET; byproducts and non-immediate targets that a later step consumes are external (their own
`unstated(1)` demand; the monetary basket uses the same set). Byproduct recovery is a typed-disposition question
(0.9.5 StreamDisposition), never assumed.

**D24.7** (parent, `material_spec.py`) CLAMPED stock evidence degenerate at a bound (`[1, 1]` or `[0, 0]`) never
certifies a composition (C4); phase comparison VIOLATES only for DISJOINT phases — AQUEOUS_SOLUTION ⊂ LIQUID, so
that pair is UNDETERMINED (C5).

**D24.8** An identity-keyed requirement whose species is absent under the structure key but present under a name key
equal to the requirement's own name → UNKNOWN, not BLOCKED (C6).

**D24.9** The kernel lock pins AST digests of EVERY helper on the recompute path (`TypedInput.exact`,
`IntervalEvidence.interval`, `material_spec.exact_fraction`, …), pins the kernel→fn `__qualname__` map, and adds a
>6-decimal vector (`0.9999995 → [0.999999, 1]`) (C3).

**D24.10** C7: documented boundary — `material_library` bench bottles are an EXAMPLE declared world authored by the
repository (their USER_DECLARED is the example operator's word); every CLI/service preset ships an EMPTY inventory;
stale fit-positive docstring corrected.

**D24.11 — Transport re-derives identity losses.** On load, `compilation_ir.identity_losses` must equal the losses
re-derived from the carried request's `target_input` (recompile and decompile paths); mismatch → refused. Legacy v0.8
payloads are checked the same way against the REAL fixtures (a legitimate v0.8 loss set that today's resolver derives
differently fails closed as "legacy; recompile", never loads as current).

**D24.12** The human/JSON capability render shows the content identity next to the label
(`CAPABILITY[<origin>@<profile_digest[:12]>]`); origin/profile_id are labels, the profile digest is the identity,
and the consumer's question pin is the authenticating check (documented).

**D24.13** The loader mirrors the producer: a capability-profile request with the convergent-DAG grammar must be
REFUSED-outcome with no DAG dossiers.

**D24.14** Routes mode: the ranked dossier set must EQUAL the IR candidate set whenever the producer never truncates
(verify against the producer; if it truncates, require ranked == the producer's deterministic prefix).

**D24.15** `CapabilityProfile` requires `physical_bounds.schema_version == PHYSICAL_BOUNDS_SCHEMA` (v1alpha2).

**D24.16** `"distillation apparatus"` is UNRECOGNIZED (the page's configuration is "as described by your instructor"
— unknown; fail closed instead of claiming either SIMPLE or FRACTIONAL); corpus prose that says "fractional
distillation" is corrected to what the page says (a 134–143 °C fraction collected by distillation).

**D24.17** (W-GATES-EVID observation) A step with NO `ProcedureEvidence` yields a text-free unread note on the
EQUIPMENT and MEASUREMENT axes too ("step s has no ProcedureEvidence: its equipment / verification demand is
unread"), matching the D14 physical and D17 material treatment of the same absence — never NOT_APPLICABLE.
