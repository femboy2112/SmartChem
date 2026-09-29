# SmartChem 0.9.5 — Adversarial Release Candidate PLAN (v0.1)

**Status:** PLAN only. Do NOT implement until 0.9 merges and external review clears it. 0.9.5's job is **not new
features** — it is to FREEZE the complete product and systematically attack it end to end, until the whole pipeline
demonstrably means what it says. No new reaction classes. No new chemistry family. No capability-fit by omission.

The finite ladder: `0.6 ✅ → 0.7 ✅ → 0.8 ✅ → 0.9 (Round III + Round IV + Round V external audits; on external-review HOLD, not merged) → 0.9.5 Adversarial RC → 1.0 Stable`.

Round III proved the *capability projection* is sound under a fresh hostile review (two adversaries converged on
F1/F2, both fixed; everything else held). 0.9.5 widens that discipline to the ENTIRE pipeline, from raw human input
to the final dossier, with denominator accounting at every stage — nothing graded on the pretty cases.

---

## Round IV audit — the findings 0.9.5 must keep dead (folded in 2026-09-28)

0.9's external audit (Round IV) found and closed a NEW class of composition / whole-path overclaim beyond Round
III's F1/F2 (F41–F56). 0.9.5 re-attacks the FROZEN product against every one; each already has a calibrated mutant
(M41–M61) that must stay dead, and the attack surfaces below are enriched accordingly:

- **Resource conservation (F41/F42/F50)** — repeated procedure materials must SUM (25 mL ×2 = 50 mL; 55+10+25 = 90);
  finite stock is a POOL a bottle cannot be spent twice from (a small max-flow allocation); distinct-spec uses of
  one species never collapse. Attack the allocation with knife-edge inventories + multi-bottle aggregation.
- **Material semantics / identity (F43/F44)** — a formulated wash needs a TWO-SIDED composition band (100% bicarbonate
  ⊬ "5% wash"); a structure-known requirement matches ONLY structure-keyed stock (a bare name never stands in).
  Re-attack every substitution (hydrated⊬anhydrous, unsaturated⊬saturated, wrong-%⊬5%, name⊬structure).
- **Typed derived data (F46/F55/M57/M58)** — every interval flows through `DerivedIntervalEvidence`, whose
  construction REFUSES a value its own `derivation_fn(inputs)` does not reproduce; `unit` distinguishes
  mass-fraction-of-solution from mass-per-100g-solvent (the NaCl bug). Attack a decorative/unsupported band.
- **Unknownness (F47/F48/F49) + the FOLD CONTRACT (F56/Decision 11)** — the per-dimension fail-closed law (*a real
  demand on an unmodeled or exhausted capacity → UNKNOWN, never FIT*) must hold on EVERY axis, not one: process time
  (F56), material capacity (F42), hazard→containment (F47), spent-stream→waste (F48/F49). Re-attack for any axis that
  still launders an omission into a pass.
- **Topology / CLI / transport (F51/F52/F54)** — a capability request under convergent DAG is typed-REFUSED, not
  silently unassessed; `compile` human ≡ `--json` ≡ `recompile` on every capability field; a legacy v0.8 RESPONSE
  loads additive-optional (profile/assessment None, no crash, no fabricated FIT) — 0.9.5 must land a real
  v0.8-producer-emitted RESPONSE fixture (not only the request fixture already committed).
- **Held-out genericity (F45)** — a benign held-out `ProcedureEvidence` with typed reactant/auxiliary
  `ProcedureMaterialUse`s must project correctly WITHOUT adding its identity to `requirements.py`.
- **Source substitution (M60)** — a swapped `ProcedureMaterialUse` (species/quantity/formulation) must move the
  digest and be refused on rebind.

**The vanished FIT positive is a 0.9.5 target.** 0.9 ships with `CAPABILITY_FIT` rigorously defined but UNREACHED on
the current corpus: the one PROCESS_SPECIFIED route (isopentyl) reads UNKNOWN because its sourced procedure
under-specifies whole-process DURATION (only the 1-hr reflux floor is timed), the ionic auxiliaries' HAZARDS, and the
spent-stream DISPOSAL. 0.9.5 must determine whether ANY corpus member can HONESTLY reach FIT once those three are
sourced (a fully-timed, disposal-declared, benign-auxiliary procedure), or confirm the ceiling and carry it to 1.0.
Fabricating a duration/hazard/disposal remains banned.

**Round V sharpened this from "the corpus" to "the model" (the zero-FIT THEOREM).** Under the current evidence
vocabulary NO route of ANY corpus can reach overall `CAPABILITY_FIT`: PROCESS_SPECIFIED requires workup, workup
requires a SEPARATE/FILTER/DRY/WASH op, and every such op leaves a spent stream no evidence type can discharge (T0);
every leaf reactant is either an untyped residual or an unsized demand (T1); every empty-GHS byproduct stream is
unresolved (T2). The evaluator itself is NOT overconstrained (a real PROCESS_SPECIFIED route reaches FIT the moment
only its waste is discharged). So the 0.9.5 FIT question is a VOCABULARY question first: land `StreamDisposition`
(below) or ship 1.0 stating "CAPABILITY_FIT: defined, evaluator-reachable, unreachable from any current evidence
vocabulary".

---

## Round V audit + X-high continuation — lessons 0.9.5 must keep dead or finish (folded in 2026-09-28)

Round V (audit `V0_9_RC_ROUND_V_EXTERNAL_AUDIT_2026-09-28.md`, barriers D1–D13 in §3, D14–D23 in §7) replaced every
"one representation meaning two things" and then, at X-high effort, attacked every capability axis IN ISOLATION --
because a universal zero-FIT ceiling MASKS per-axis false FITs that the day disposal becomes typeable would unmask.
**0.9.5 stays FEATURE-FROZEN: no new reaction family, no new chemistry.** Each item below is either a law 0.9.5 must
re-attack on the frozen product, or a named representation gap with an exact boundary.

**Laws to re-attack (each has calibrated mutants in `experiments/v0_9_mutation_calibration.py`):**
- **D13 field-coverage theorem** -- every `ProcedureEvidence` / `ProcedureOperation` / `ProcedureMaterialUse` /
  `EvidenceField` / `ConditionEnvelope` / `ProcessRequirements` / `ExperimentStep` / `ExperimentRoute` field has ONE
  owner in the machine-checked ledger `smartchem/capability/coverage.py`; a PRESENT untyped value fails its owner
  closed. **Stated boundary to attack:** a demand MISFILED into another axis's prose field is caught on the HOST axis
  (the fold stays <= UNKNOWN), not attributed to its owning axis -- authored data is re-filed by hand and pinned by a
  curated corpus lint. Attack: a schema-valid object whose real demand reaches NO axis (Adversary A's brief).
  The X-high funnel's observation (a step with NO `ProcedureEvidence` read equipment/measurement NOT_APPLICABLE while
  physical/material read the same absence as an unread demand) is CLOSED by D24.17: every axis now carries a
  text-free "no ProcedureEvidence: unread" note. Re-attack it for any axis that still passes on a missing procedure.
- **Global package conservation (D1/D2)** -- exact `Fraction` per unit domain, ONE capacity node per bottle, G⁻/G⁺.
  Attack cross-species, cross-unit, multi-component and unknown-capacity double-spends at knife edges.
- **Temperature RANGE (D14)** -- `PhysicalBounds.min_temperature_k` on the ONE shared leaf; route LOW = min of typed
  `.lo`; prose T/P and untyped thermal ops are unread demands; preset floors follow only from declared equipment.
- **Process timeline (D15)** -- ordered op floors ADD, representations combine by MAX (no double count), only a
  whole-step record ceiling bounds a step; the process axis is never UNCONSTRAINED for a real step; NO_LIMIT waives
  only the three time preferences. **Retained 0.8 semantics (documented, not a bug):** the delegate EXCLUDES a step
  whose elapsed CEILING exceeds the operator's limit (a time GUARANTEE reading -- a possible false BLOCK, never a
  false FIT). 0.9.5 decides whether capability wants the guarantee or the "can finish within" reading.
- **Phase evidence (D18)** -- a `PhaseClaim` certifies only with requirement-certifying (SOURCE_QUOTED/DERIVED/
  CLAMPED) AND stock-certifying (+USER_DECLARED) evidence; CLAMPED never proves purity. Attack every laundering path.
- **Evidence-kernel semantic identity (D19)** -- `KERNEL_KNOWN_ANSWERS` + pinned descriptor/AST digests lock every
  `*_V1`; any change mints `*_V2`. **Parked:** content-addressing the descriptor digest INSIDE `IntervalEvidence`
  (records would then carry the identity of the arithmetic they were minted under).
- **Transport under a keyless attacker (D20)** -- every public digest is recomputable; a stale assessment must be
  refused by SEMANTIC re-derivation (rebind, readiness re-derivation, route-identity bind), never by a hash alone.
  Re-run the public-hash-recomputed attack matrix (stock strip, tier transplant, replay quantity edit, forged FIT
  thin/thick, profile swap under the request pin, origin relabel) on the frozen product.
- **Real v0.8 producer fixtures** (`tests/fixtures/v08/**`, incl. the DAG-mode response, all regenerated only from a
  clean `git archive df1b38d`) verify byte-for-byte under the frozen v0.8 digest rule. Never simulate one by deleting
  keys.

**Wave-C′ / D24 laws to re-attack (audit doc §7.4–§7.5; the fresh non-author review of the integrated D14–D22 tree
found no reachable OVERALL false FIT, and every per-axis false FIT it found is fixed by D24):**
- **Canonical-rendering display law (D24.1)** -- prose is DISPLAY only when it is byte-equal to the canonical
  rendering of the typed fields it summarizes (`capability/coverage.py`: `render_op_quantity`,
  `render_verification`, `render_summary`, `render_scale`); anything else is an unread demand on a NAMED host axis
  (material / measurement / process). No prose parser anywhere -- the mechanism is one a word cannot fool (it replaced
  the D16 "display trust" model and its foolable word-blacklist lint: "5 L methanol" beside a typed 20 mL use, "1H
  NMR and HPLC ≥ 99.5 %" beside a balance, "vacuum oven 0.01 atm 390 K 48 h" in a summary all reached FIT per axis).
  A vacuum-capable op with no typed pressure is an unread LOW-pressure demand; a record floor ≥ 1 atm beside it is a
  contradiction. Stated boundary: PRESENTATION-only hosts (`evidence_scope`, `justification`, locators, notes,
  provenance) are OUTSIDE the theorem and carry no demand BY CONTRACT -- attack whether any consumer reads them.
- **The missing `(value)` of EXPLICIT_NOT_APPLICABLE (D24.2)** -- `EvidenceField(EXPLICIT_NOT_APPLICABLE, value=...)`
  was schema-valid, `is_present=False`, and skipped by every reader (a 650 K "N/A" op read FIT). A closing-out claim
  now cannot carry a value. Re-attack every tri-state slot for a status whose payload no reader inspects.
- **`envelope.medium` on a procedure step (D24.3)** -- Part IV over-corrected (benzene as a procedure step's medium
  read material FIT); an uncovered medium is now a text-free material unread note, still NEVER a species, hazard entry
  or waste stream. **A MIX op (D24.4)** on a step whose record agitation is None/NONE is an unread process demand.
- **Commensurability is EARNED, never implied (D24.5)** -- a state word (NEAT / ANHYDROUS / HYDRATE) never makes a
  bottle a proven 1:1 G⁻ draw (the live corpus brine spec was armed: a 1 % bottle, a `[0, 0]` phantom component and
  the CLAMPED library MgSO4 all read as proven draws); only a SATISFIED composition, or a satisfied formulation-defining
  state (SOLUTION / SATURATED / UNSATURATED) with a certified positive lower bound, or the pure witness (which now also
  needs every OTHER component's lower bound exactly 0 on ANY basis) earns it; a certified NEAT claim beside a certified
  positive diluent is dropped. Re-attack with knife-edge multi-component bottles on mixed bases.
- **Internal supply = the carried target only (D24.6)** -- for step k of a linear route a species is internal ONLY if
  it is step k−1's carried TARGET; byproducts and non-immediate targets consumed later are EXTERNAL (their own
  `unstated(1)` demand). One water byproduct could previously feed every later consumer twice. Byproduct recovery is a
  typed-disposition question (StreamDisposition), never assumed. The DAG path is refused under a profile today --
  re-attack when it is not.
- **Evidence-grade holes closed (D24.7/D24.8/D24.9)** -- CLAMPED stock evidence degenerate at a bound never certifies a
  composition; phase VIOLATES only for DISJOINT phases (AQUEOUS_SOLUTION ⊂ LIQUID is UNDETERMINED); an identity
  requirement whose species exists in a bottle only under its own NAME key is UNKNOWN, not "absent"; the kernel lock
  now pins every helper on the recompute path + the kernel→fn `__qualname__` map + a >6-decimal vector (a rounding
  drift previously passed all lock tests and flipped UNKNOWN→FIT).
- **Identity-loss re-derivation on load (D24.11)** -- `compilation_ir.identity_losses` was trusted: a keyless attacker
  stripped the stereo loss, forged PROCESS_SPECIFIED on the canonical wire, kept the corpus route's own digest, and
  loaded under request pin + question pin + verified admission. Losses are now re-derived from the carried request's
  `target_input` (legacy v0.8 payloads checked against the REAL fixtures; a legitimate loss set today's resolver derives
  differently fails closed as "legacy; recompile"). General lesson for 0.9.5: EVERY carried field that feeds a verdict
  must be either re-derived on load or covered by a semantic binding -- enumerate them.
- **Transport labels vs identity (D24.12–D24.15)** -- `profile_id`/origin are labels, the profile DIGEST is the
  identity (rendered as `CAPABILITY[<origin>@<digest12>]`; the consumer's question pin authenticates); the loader
  mirrors the producer's profile+convergent-DAG refusal; a ranked dossier set must equal the producer's IR candidate
  set (a BLOCKED dossier can no longer be silently deleted); a v1alpha3 profile refuses an embedded v1alpha1
  PhysicalBounds.
- **"distillation apparatus" (D24.16)** -- the Round-III alias to FRACTIONAL_DISTILLATION was a forcing-matrix
  convenience the page does not support ("as described by your instructor"); it is UNRECOGNIZED (fail closed). Audit
  every closed-resolver alias against its source page.

**D24 VERIFIED DEFERs (exact boundaries):**
- **D-T1 thin trust marker** -- a THIN plain load keeps no trust marker: an advisory assessment is indistinguishable
  after load (FIT/PROCESS_SPECIFIED on thin are still refused; verified admission refuses). Boundary: thin plain loads
  are ADVISORY by contract; trust requires the canonical wire or `require_verified_admission`; recording which on the
  loaded object is a trust-tier field (a 0.9.5 shape change).
- **C8 stock-side sourced-kind locator** -- stock-side SOURCE_QUOTED / DERIVED / CLAMPED phase and state claims carry
  no locator (no power gain: USER_DECLARED already certifies on the stock side). Boundary: stock-side sourced kinds
  certify EXACTLY as USER_DECLARED (no verdict changes); binding a stock claim to a checkable locator + subject belongs
  to the source-subject-binding work below.
- **StreamDisposition: unchanged** -- D24 does not touch the zero-FIT ceiling; the disposal vocabulary (and its
  subject binding) remains the 0.9.5 FIT question stated above.

**Named representation gaps (exact boundaries):**
- **`StreamDisposition` (the FIT vocabulary)** -- typed CONSUMED_COMPLETELY / RECOVERED / ROUTED(WasteCapability) with
  a CLOSED subject binding (a use, an op stream, a byproduct, an untyped op material) that discharges an obligation
  ONLY under requirement-certifying evidence with a locator. Kill criterion: any disposition that discharges an
  obligation it does not bind to, or under non-certifying evidence. No cited corpus page states disposal today (no
  fake data); byproduct→stream binding needs its own adversarial pass.
- **Source-subject binding (the c3 boundary)** -- a replayed `ProcedureEvidence` is bound only to its own content
  digest, never to the SHIPPED source table: a keyless attacker can ship a self-consistent response for a TAMPERED
  procedure (a different route digest; coherent, not authentic). Close it by binding replayed evidence to the shipped
  source-table digest (or require the producer HMAC / a consumer route-digest pin).
- **Source temperature / domain scope** -- `TypedInput.temperature_k` is carried (e.g. the NaCl 36.0 g/100 g at
  298.15 K) but no law checks a solubility-derived interval against the route's operating temperature; evidence also
  carries no SUBJECT (which material/species it is about) beyond its placement.
- **One-sided (lower-bound) physical demands (P-X2)** -- a distillation HEAD temperature is only a LOWER bound on the
  heat demand; the isopentyl whole-step peak was withdrawn rather than overclaimed, losing BLOCK power. A typed
  lower-bound demand would restore "BLOCKED below it, UNKNOWN above it".
- **Endpoint / pH-indicator carrier** -- a prose endpoint ("basic to litmus", "until homogeneous") is an unread
  measurement demand; there is no typed endpoint→method relation and no `PH_INDICATOR` method (a member no evidence
  path can emit would be decorative).
- **Held-out material semantics** (from the X-high saponification probe vs the BLIND oracle,
  `V0_9_RC_ROUND_V_HELDOUT_PROBE_RESULTS_2026-09-28.md`: 12 PASS / 1 lawful divergence / 0 FAIL, no compiler edit):
  no PRECIPITANT/SALTING_OUT material role; no APPROXIMATE quantity ('~5 mL' -> UNKNOWN); MOLAR and w/v stock claims
  have no certifying kernel input unit (6 M NaOH(aq) can never be USER_DECLARED); no disjunctive equipment demand
  ('any filtration'); containment vocabulary is `{FUME_HOOD}` only (no corrosive-handling/PPE; ventilation RESERVED);
  no PREPROCESSING edge status (NaOH pellets vs 6 M NaOH(aq) is a certified phase VIOLATION -- a false-BLOCK risk in
  the safe direction); a mixture substrate needs a model Molecule in the balanced step.
- **Synonym absence** -- a typed name-keyed requirement against a bench bottle under another name ("sodium
  bicarbonate" vs "baking soda") BLOCKS under declared-world closed semantics; decide whether 0.9.5 wants a curated
  synonym layer or keeps the closed-world reading explicit.

---

## The frozen end-to-end corpus (the spine of 0.9.5)

Freeze one corpus and drive it through EVERY stage, counting the denominator at each:

```
raw human input  →  identity (parse/resolve)  →  search  →  real route  →  procedure readiness
                 →  capability projection  →  final dossier (canonical transport)
```

At each arrow, record: how many inputs entered, how many survived, how many were correctly refused, and WHY each
drop happened. A stage that only ever sees the friendly inputs is not tested. The corpus MUST include:
the 0.6 human front-door phrasings; the ester/analgesic teaching corpus (isopentyl acetate, aspirin, paracetamol,
methyl salicylate); the DOW bromine + paracetamol litmus targets; ambiguous / mis-parseable names; below-tier
routes (FORMAL / CONDITIONS_SUPPORTED / REACTION_VOUCHED); the null retro-DA; and a held-out route NEVER seen during
0.6-0.9 development (the generalization probe).

---

## Attack surfaces (each gets a directed adversary + a structure-theorem adversary + a seeded fuzzer)

1. **Front-door parser** — malformed, adversarial, Unicode-confusable, and over-long human inputs; injection-shaped
   strings; the silent-mis-parse class 0.6 already closed — re-attacked for regressions.
2. **Ambiguity** — inputs with >1 plausible identity; does the compiler refuse / disambiguate / never silently pick?
3. **Identity** — same-formula constitutional isomers, stereo/isotope blindness (the declared ID-layer boundaries),
   resonance/Kekulé spellings, ionic species the SMILES parser refuses.
4. **Search completeness** — does the bounded search's completeness receipt mean what it claims? Attack the
   `search_space_status` and the transform-registry/algebra digest.
5. **Transform algebra** — the 0.7 production algebra; can a profile/algebra selection perturb search identity (it
   must not); can the certified-vs-legacy default boundaries be crossed silently?
6. **Procedure evidence** — the 0.8 ProcedureEvidence + the 0.9 ProcedureMaterialUse; source-substitution attacks
   (swap a sourced procedure/material and demand the digest/rebind refuses); the F3 hazard-scan blind spot.
7. **Material / profile evidence** — StockMaterial interval logic, name-vs-structure keying, the DERIVED_WITH_ERROR
   intervals (anti-fabrication: every interval must trace to a citable source), the capability profile snapshots.
8. **Capability projection** — re-run the full Round-III false-FIT hunt (F1/F2 regressions + the axes that held) on
   the FROZEN product; attack the D9 hazard name/resolution asymmetry the release record defers; the
   process-time-as-unlimited-patience boundary.
9. **Source substitution** — across procedure, material, hazard, and price data: any altered source must move the
   relevant digest and be refused on canonical load.
10. **Schema migration + legacy payloads** — every pre-0.9 serialized request/response must load safely (no assumed
    bench, no crash); every schema-version bump must be honored; a payload from 0.7/0.8 must not silently gain 0.9
    semantics.
11. **Canonical replay** — the thick/thin wire discipline; CAPABILITY-REBIND-ON-LOAD + ALGEBRA-REBIND + readiness
    rebind, all fail-closed under tamper; the generic canonical decoder whitelist (Round-III Wave-C flagged it sound
    only because no live Molecule is in the graph — re-attack if any new capability type embeds one).
12. **Deterministic output** — same input → byte-identical output across runs/processes; the digests are stable.
13. **Optional-backend matrix** — RDKit present (dev) vs absent (committed baseline): the committed behavior must be
    identical; rdkit-only tests importorskip-skip; NO backend may change a verdict.
14. **Performance** — the amide-heavy `Molecule.canonical()` resonance cost; the OOM-safe suite batching; search
    bounds under adversarial depth/branching; no pathological blowup on the frozen corpus.
15. **Held-out chemistry** — a route/target never seen in 0.6-0.9 dev: does identity/search/readiness/capability
    behave honestly (correct refusal or correct projection), or does it expose a corpus-coincidence?
16. **CLI / API / human / JSON equivalence** — the three CLI surfaces (plan/recompile/compile); human render ≡ JSON
    semantics on every field; no surface exposes a verdict another hides.

---

## Method (inherit Round III's, widened)

- **Parent barrier freezes the attack corpus + expected-result oracle FIRST** (an independent oracle, blind to the
  implementation, like Round-III Lane F).
- **Fan out fresh non-author adversaries** per surface (directed exploit + structure-theorem refutation + seeded
  fuzzer with minimized repros). Every finding: FIXED / REFUTED-WITH-EVIDENCE / VERIFIED-DEFER-WITH-EXACT-BOUNDARY.
- **Any false-FIT, any silent-mis-parse, any digest that fails to move under a real change, any legacy payload that
  gains new semantics — is release-blocking.**
- **Denominator accounting at every stage** — report the full funnel, not the survivors.
- **The mutation gate grows** — every 0.9.5 finding earns a calibrated mutant (M62+), and the M1-M61 gate is re-run
  on the frozen product.
- **Full OOM-safe suite green + no 0.6/0.7/0.8/0.9 regression** is the floor, not the ceiling.

## Exit criterion

0.9.5 earns its tag when the frozen corpus survives the entire adversarial battery with no unresolved
release-blocking finding, every stage's denominator is accounted for, and the end-to-end pipeline is demonstrably
deterministic, fail-closed, and honest from raw input to final dossier. Then, and only then, 1.0 is the stable
contract freeze.
