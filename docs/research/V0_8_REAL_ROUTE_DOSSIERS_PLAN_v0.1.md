# SmartChem v0.8 — Real Route Dossiers — Round I Plan

**Status:** implementation plan, living document (updated as discoveries change it)
**Version:** v0.1 (Wave-A adjudication frozen 2026-09-27)
**Baseline:** `main@2d5c8a3ecb3b310203719a9acbaf6cbb46d781e1` (PR #91 merged — v0.7 Production Chemical Algebra)
**Branch:** `feat/v0.8-real-route-dossiers`
**Package version during the round:** stays `0.7.0a1` (no ceremonial bump; `0.8.0a1` is earned only when the gate in §11 is met)
**Governing contract:** `CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md` §7 (route readiness is a ladder of discharged obligations) and §11's `0.8.0` block.

---

## 0. What 0.8 asks

0.7 answered: *what chemistry can the compiler generate, and exactly which algebra generated it?* 0.8 asks: **what does SmartChem actually KNOW about the reality of each generated step and route, and what obligations remain undischarged before the route can be treated as a real synthesis dossier?**

This round removes the artificial wall (`readiness_tier` hard-coded `FORMAL_CANDIDATE`, refused-if-stronger) and replaces it with a **typed readiness obligation system** — obligations first, coarse tier as a *derived cumulative projection* second. No single confidence score. No probabilities.

---

## 1. Evidence taxonomy

| Grade | Meaning | Source |
|---|---|---|
| SOURCE-backed | typed `SourceCitation` with `review == ACCEPTED` | `ConditionEnvelope.source`, `ProcessRequirements.source` |
| DERIVED | model output with its own soundness burden | feasibility ΔG, kinetics |
| DECLARED | asserted, free-text provenance, no accepted source | `ConditionEnvelope` declared but `source` unaccepted/absent |
| ranking-only | ordering/presentation, never a tier | affordability, observability, the 5 verdicts, §11 `fit_status` |
| UNKNOWN | absent; never a silent zero/pass/safe | missing envelope / process |

---

## 2. The non-negotiable epistemic law (kept executable)

Orthogonal; one NEVER auto-implies another:
`structurally-valid-rewrite / reaction-type-recognized / conditions-sourced / process-described / workup-described / thermo-favorable / kinetics-characterized / selectivity-sourced / bench-fit / capability-fit`.

Corollaries: favorable ΔG ⇏ reaction-vouched; reaction-vouched ⇏ conditions known; conditions known ⇏ complete procedure; `fit_status == FITS` ⇏ procedural readiness; an accepted citation validates *what it covers*, not every statement in a route; `workup_included=True` is evidence the source covered workup, not proof our representation is a complete procedure. **Capability fit is 0.9, not 0.8.**

---

## 3. Obligation model (FROZEN — Wave A Lane A)

New module `smartchem/experiment/readiness.py`. New enum (does NOT reuse `EvidenceStatus`, a strength axis, nor `Route/ProcessFitStatus`, the fit axis):

```python
class ObligationStatus(str, Enum):
    SATISFIED; UNSATISFIED; UNKNOWN; NOT_APPLICABLE

@dataclass(frozen=True)
class StepReadiness(Digestible):
    formal_candidate: ObligationStatus       # always SATISFIED (a built step passed its conservation cert)
    reaction_type: ObligationStatus          # SATISFIED | UNSATISFIED (2-valued; the oracle is total, never "refuted")
    reaction_class_name: str | None          # verbatim recognize_reaction_type() output
    conditions: ObligationStatus             # SATISFIED | UNSATISFIED | UNKNOWN (see §4 field logic)
    process: ObligationStatus                # SATISFIED | UNSATISFIED | UNKNOWN (process-completeness — DARK, §5)
    workup_isolation: ObligationStatus       # SATISFIED | UNSATISFIED | UNKNOWN
    provenance: tuple[str, ...]              # accepted-source locators backing a SATISFIED axis (audit trail)
    open_obligations: tuple[str, ...]        # one sorted reason per non-SATISFIED axis
    # tier: @property, DERIVED — never stored/settable

@dataclass(frozen=True)
class RouteReadiness(Digestible):
    per_step: tuple[StepReadiness, ...]
    route_open_obligations: tuple[str, ...]  # dedup+sorted union of per-step open_obligations
    # tier: @property = min(step.tier) over per_step
```

The **per-obligation fields are the source of truth**; `tier` is a derived projection (§4). The typed record is stored on the wire (digest-covered), and both the tier and the legacy `readiness_tier` string are derived properties over it (§7).

---

## 4. Derived tier law (FROZEN)

Total order `FORMAL_CANDIDATE < REACTION_VOUCHED < CONDITIONS_SUPPORTED < PROCESS_SPECIFIED`. Per-step tier is **cumulative**:

- **FORMAL_CANDIDATE** — always (a constructed `ExperimentStep` already passed its conservation certificate, `step.py:130-139`).
- **REACTION_VOUCHED** — `reaction_type == SATISFIED`: `recognize_reaction_type(step)` (`reaction_type_oracle.py:580-596`) returns a class name. The oracle is *total* (swallows every recognizer exception, never raises, never returns "refuted"); the evaluator wraps the call in its own `try/except → None` for belt-and-suspenders. **UNRECOGNIZED retains its honest meaning — not "proven impossible."** A step built via `.assembling` (centre `None`) can never be vouched by design; the evaluator's inputs must come from real search steps (`.from_transform`/`.from_capped_scission`, real `reaction_center`).
- **CONDITIONS_SUPPORTED** — `REACTION_VOUCHED` AND `conditions == SATISFIED` AND no identity-loss blocker on conditions (see below).
- **PROCESS_SPECIFIED** — `CONDITIONS_SUPPORTED` AND `process == SATISFIED`. **DARK this round** (§5): no record meets the representation-completeness predicate, so this tier is defined but never awarded.

Route coarse tier = `min` over `per_step` (bounded by the weakest step). Reaction-vouch aggregation **reuses `route_reaction_type_blockers` (`reaction_type_oracle.py:599-627`)** — route vouched iff *every* step recognized, fail-closed — never an "any-step" OR.

**Field logic (obligation status from facts that already exist):**
- `conditions`: `step.envelope.is_sourced` (`conditions.py:209-212`) → SATISFIED; declared-but-unsourced → UNSATISFIED; not-declared (UNSUPPORTED) → UNKNOWN. **Read `step.envelope.is_sourced` directly — NOT `ExperimentStep.is_declared`, whose docstring lies (it returns DECLARED, not SOURCED).**
- `process`: `ProcessRequirements.is_sourced` (new; mirrors ConditionEnvelope) is *necessary but not sufficient* for `process == SATISFIED`; the sufficient predicate is the representation-completeness contract of §5, which nothing meets → `process` never SATISFIED this round.
- `workup_isolation`: `process is None` → UNKNOWN; else `process.workup_included` → SATISFIED / UNSATISFIED.
- **identity-loss blocker (contract clause):** the evaluator receives the route's already-computed `identity_losses` and caps `conditions` (→ UNSATISFIED/blocked) when any active loss's `affected_claims` contains `"conditions"` (`stereo_loss`/`local_charge_loss`, `identity.py:398-418,442-453`). Un-exercised by today's corpus (no SEED target declares stereo/charge) but contract-mandated and cheap; a synthetic test pins it.

**The tier is a cumulative projection; the obligations are the truth.** A step may report `conditions == SATISFIED` while its coarse tier is only `FORMAL_CANDIDATE` (because `reaction_type == UNSATISFIED`). Richer evidence stays visible at every lower tier.

### 4.1 The non-monotonicity finding (Lane E) — the design's vindication

The two best-sourced, process-richest steps in the corpus — **paracetamol + acetic anhydride** and **aspirin** — are **reaction-type UNRECOGNIZED**: they emit acetic acid (an anhydride-mediated transacylation), not water, so `_acyl_condensation` genuinely does not fit, and none of the other 16 recognizers match. Result: `conditions == SATISFIED` while `reaction_type == UNSATISFIED`, so the coarse ladder is **not monotonic** on these members.

This is handled — not patched — by the architecture: obligations are orthogonal and independently visible; the coarse tier is a conservative cumulative headline. Paracetamol/aspirin report coarse `FORMAL_CANDIDATE` with `conditions=SATISFIED, workup=SATISFIED` visible and an `open_obligations` string stating exactly why the coarse tier is capped ("reaction type not recognized by the production oracle; anhydride transacylation is outside the 17-class set"). **This is the 0.8 exit gate's poster child** ("exactly why a stronger label is unavailable"). Per scope (§10) we do **NOT** add reaction family #18 to promote them.

---

## 5. Process-completeness decision (FROZEN — Wave A Lane C): PROCESS_SPECIFIED stays DARK

No structured representation exists for the operational obligations a real bench procedure requires. Grep-confirmed absent from `smartchem/` (present only as free-text provenance or in the old `_MISSING_BENCH_FIELDS` list): scale/amount/assay, addition order/rate, endpoint, quench, purification (distinct from workup), analytical/endpoint acceptance, waste routing, equipment ratings, emergency controls. `workup_included` is one undecomposed boolean; time fields are documented **floors only** ("can only EXCLUDE, never confirm a fit", `process_constraints.py:106-109`).

**Ruling:** the honest ceiling on the strongest records (aspirin, isopentyl acetate, paracetamol+anhydride) is `CONDITIONS_SUPPORTED`. `PROCESS_SPECIFIED` is defined but unreachable; the `process`/`workup_isolation` obligations are still computed and shown as visible evidence and reported in the census, but they never award the dark tier. This satisfies the mission's blessed "successful dark result" and honors "never weaken the word." Building the process representation is a later 0.8 sub-round (with a tri-state workup field: needed-absent vs needed-undescribed), not Round I.

Two fixes this exposes: (a) `RouteDossier.render()` (`drafter.py:778-782,93-98`) is disconnected from the `SEED_CONDITIONS` process layer (hard-FORMAL, static `_MISSING_BENCH_FIELDS`) — Writer 4 rewires it to the shared evaluator; (b) `ProcessFitStatus.FITS` must stay a visibly separate field from `readiness_tier` (fit ≠ readiness).

---

## 6. Evidence / provenance boundaries (FROZEN — Wave A Lane B/F)

- **CONDITIONS_SUPPORTED gates on `step.envelope.is_sourced`**; `SourceCitation.accepted` = `review is ACCEPTED` (`provenance.py:57-60`).
- **Isomer safety — live path is provably clean.** `assembly_conditions` (`decompiler_conditions.py:388-420`, the *only* live caller at `routes.py:453`) is structurally guarded. The unguarded `reaction_conditions` composition-keyed leak is real (a wrong C8H9NO2 isomer borrows paracetamol's DOI, `is_sourced=True`) **but dead code** (only `decompiler_review.py`, no cli/service/routes import). The evaluator consumes only the guarded live-attached envelope; a forged swapped envelope is caught by the load-time coherence check + digest (M9). The negative control (4-aminophenyl-acetate cut with acetic acid) DOES structurally emit the same product pair but `assembly_conditions` returns `is_sourced=False` (name-guard fails) — confirmed live.
- **SEED_CONDITIONS (6 records):** 5 sourced; **ketene acetylation (`:139-152`, `source=None`) is the built-in DECLARED-but-unsourced negative control.**

---

## 7. Transport / tamper (FROZEN — Wave A Lane D)

Transplant the shipped `process_requirements` precedent. Store `RouteReadiness`/`StepReadiness` on `RankedRouteSummary` (`service.py:994-1020`), **digest-covered, `compare=True`**; keep `readiness_tier: str` (`:998`) as a DERIVED property; flip `__post_init__` (`:1029-1030`) from constant-refusal to a coherence check; `of_fit` (`:1067`) derives from the typed record.

Schema bumps: `RANKED_ROUTE_SUMMARY_SCHEMA` `:196` v1alpha2→v1alpha3; `COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR` `:191` v1alpha16→v1alpha17; `COMPILATION_RESPONSE_SCHEMA` `:167` v1alpha13→v1alpha14. Codecs modeled on `_process_requirements_to/from_payload` (`:2718-2761`); wire into `ranked_summary_to/from_payload` (`:3056-3101`, reconstruct via real ctor).

**Re-derivation on load** (the replayed step is verified thick enough — carries `reaction_center` + full `ConditionEnvelope` incl `status`/`source`/`process`): add `_check_readiness_coherence`, modeled on `_check_process_admission_coherence` (`:1484-1546`) and `_check_frontier_coherence` (`:1601`), wired into `response_from_payload` (`:3489-3543`), **unconditional** (not FITS-scoped), refusing any claimed tier stricter than the re-derivation supports and checking `route_digest == reconstruct(replay).digest`. FITS routes are additionally caught free by `_check_verified_admission` (`:3367`) once `RouteReadiness` is `compare=True`.

Render: `cli.py:392` `f"[{fit}/{tier}]"` gets a per-tier disclaimer (symmetric to the `TARGET_ALREADY_AVAILABLE` note at `:378-380`) so a `FORMAL_CANDIDATE` route is never rendered as a bench procedure; JSON field docs (`service.py:3672,3679`) rewritten off the stale "READY-TIER-01 floor".

**Documented non-goal (doctrine):** a fully self-consistent forgery with a recomputed `result_digest` can mint an unearned tier — the irreducible keyless-consumer residual every axis already lives with (`:1499-1508`), closed only by producer signatures. The tamper suite must not chase it.

---

## 8. The pure-evaluator law

`smartchem/experiment/readiness.py` accepts an already-built `ExperimentStep`/`ExperimentRoute` (+ the route's `identity_losses`) and MUST NOT: rerun search; mutate the route; invent conditions; query the network; change ranking/algebra/affordability; read `RouteFit`/`Composability`/feasibility/equilibrium/kinetics/selectivity/`ProcessFit`/`fit_status`. **One evaluator** — the service (`RankedRouteSummary`) and the dossier (`experiment.drafter.RouteDossier`) consume the same core; no second engine. Ranking-noninterference is a signature/dependency property (the evaluator never receives the ranking machinery), with precedent in `fit_route` (`drafter.py:316-368`, status built only from `comp`/`process_fit`).

---

## 9. Forcing corpus (FROZEN — Wave A Lane E; all reachable via the live `certified-route-v07` default)

| # | target | reachable via | rung exercised |
|---|---|---|---|
| 1 | cyclohexene ← butadiene+ethylene (retro-DA) | `have=(smiles:C=CC=C, smiles:C=C)`, reagents=(), depth=2 → exit 0 | REACTION_VOUCHED, conditions UNSUPPORTED |
| 2 | paracetamol + acetic anhydride | `have=('4-aminophenol',), reagents=('water','acetic acid'), depth=2` | **sourced + workup, reaction-type UNRECOGNIZED** → coarse FORMAL, conditions=SATISFIED (the non-monotonic exemplar) |
| 3 | aspirin | `have=('salicylic acid',), reagents=('water','acetic acid'), depth=2` | same as #2; process `source` unset |
| 4 | isopentyl acetate | `have=('isopentyl alcohol',), reagents=('water','acetic acid')` | recognized + sourced + workup → CONDITIONS_SUPPORTED (recognized contrast to #2/#3) |
| 5 | methyl salicylate | `reagents=('water','methanol'), have=('salicylic acid',)`, depth=1 | recognized + sourced, **`workup_included=False`** → clean CONDITIONS_SUPPORTED ceiling |
| 6 | default unsourced surrogate (e.g. aspirin's `water`-only `C2H4O2+C7H6O3→C9H8O4+H2O`) | default reagents | FORMAL-vs-plausible-fake contrast |
| 7 | 4-aminophenyl-acetate isomer cut w/ acetic acid | direct probe | same-formula negative control (non-inheritance) |
| 8 | paracetamol/aspirin depth-2 route | rows 2/3 | multi-step weakest-link aggregation |

**Process-source asymmetry:** only 1 of 4 SEED process records sets a process-level `source=` (paracetamol-anhydride); isopentyl/methyl-salicylate/aspirin process blocks default `source=None` even though their envelope is sourced. The census reports this honestly.

---

## 10. Gates

### 10.1 Mutation harness `experiments/v0_8_mutation_calibration.py` — inject AND kill each:
M1 every formal route is reaction-vouched · M2 any recognized reaction auto-CONDITIONS_SUPPORTED · M3 any declared envelope counts as sourced · M4 an accepted source on one step promotes the whole route · M5 favorable thermo substitutes for reaction-vouch · M6 FITS bench status substitutes for readiness · M7 `process is not None` ⇒ PROCESS_SPECIFIED · M8 `workup_included=False` ignored · M9 same-formula isomer borrows another compound's condition evidence · M10 serialized tier edited without evidence moving · **M11 obligations derived FROM the coarse tier (collapsing orthogonality) instead of the tier from obligations — must die (else paracetamol's visible `conditions=SATISFIED` disappears when coarse tier = FORMAL).**

### 10.2 Funnel `experiments/v0_8_readiness_funnel.py` + census `experiments/v0_8_readiness_census.py` (+ `RESULTS_*.md`)
Per-step AND per-route denominators kept separate: `formal → every step reaction-vouched → every step conditions-supported → every step process-specified`. A lower downstream denominator is EXPECTED — this measures evidence coverage, not a target.

### 10.3 Tamper coherence (7 cases) — §7. Prefer re-derivation over trusting the label.

### 10.4 Wave C fresh hostile review — non-authors attack every tier transition, sourced/unsourced boundary, weakest-link aggregation, condition-identity matching, serialization, digest relation, human/JSON agreement. Each finding → FIXED / REFUTED-with-evidence / VERIFIED-DEFER-with-boundary.

---

## 11. Release exit criteria (the 0.8 gate)

Per §11's `0.8.0` exit gate: SmartChem can show, for the nontrivial corpus, **which routes are merely formal, which are reaction-vouched, which have sourced conditions/process support, and exactly why a stronger label is unavailable** — readiness typed, transported, re-derived on load, tamper-refusing, and visible in the human/JSON render. `0.8.0a1` earned only when ordinary route responses expose trustworthy typed readiness obligations and meaningful real-route evidence beyond the formal floor across the declared corpus.

---

## 12. Explicit 0.9 boundaries (NOT built this round)

No reaction family #18; no transform-algebra widening; no `MaterialBucket`/`CapabilityProfile`/`PoorManProfile`; no kitchen-vs-lab ranking; no safety declaration; no ΔG→capability conversion; no procedure scraping; no generated bench instructions from incomplete data; no universal procedure language; no stoichiometry reasoning off the composition `_sig` key. **DAG readiness (`RankedDAGSummary`) is a VERIFIED DEFER this round** — no convergent-route corpus member exercises it and it currently carries no tier field (an honest omission, not a false claim); the trigger to add it is a convergent route with sourced conditions.

---

## 13. Fan-out ledger + barrier decisions

**Wave A (read-only, 6 orthogonal bearings, all landed 2026-09-27):** A readiness model + tier law + reaction-vouch mechanics; B conditions/provenance contract + isomer boundary; C process-completeness crux (→ DARK); D transport/schema/tamper; E empirical corpus (→ k=2 nag corrected, non-monotonicity found); F adversary (10 laundering traps → M1–M11, one earned negative on #6). Full synthesis in the session scratchpad barrier notes.

**Barrier decisions (frozen):** (1) `process==SATISFIED` gated on §5 representation-completeness → PROCESS_SPECIFIED DARK (Lane C over Lane A). (2) workup-gates-process moot (dark rung). (3) tier = derived property over a stored+digested typed record (Lane A ∪ D). (4) DAG readiness deferred (§12). (5) identity-loss blocker on conditions enforced (§4). (6) IR-level `CandidateSummary`/`StructuralCandidate` stay FORMAL (their honest floor) with the M10 hole closed (pin FORMAL + re-derive/refuse on load); the real ladder lives on `RankedRouteSummary`; `:1391` FORMULA_EDGE stays pinned (W3).

**File-ownership ledger (Wave B — one writer per file set):**
- Parent: `smartchem/process_constraints.py` (`ProcessRequirements.is_sourced` addition), `smartchem/compilation_ir.py` (IR-site FORMAL pin + load guard), final schema/golden reconciliation, this plan.
- Writer 1 — readiness core: NEW `smartchem/experiment/readiness.py` + `tests/test_v0_8_readiness_core.py`. Does not touch service/drafter.
- Writer 3 — service transport: `smartchem/service.py` + serialization/CLI-golden tests. Starts after Writer 1's interface is frozen.
- Writer 4 — dossier: `smartchem/experiment/drafter.py` + dossier tests. Consumes the SAME evaluator.
- Writer 5 — measurement/docs: `experiments/v0_8_*` + `RESULTS_*.md` + ROADMAP after behavior freezes.

*[Wave B/C outcomes appended as the round proceeds.]*
