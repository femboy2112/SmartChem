# SmartChem roadmap

> **The single source of truth for what is done, what is queued, and what is deliberately not being built.**
> `verified @ 376d186` · suite **4265 passed / 14 skipped / 1 xfailed** (PySCF-present dev venv) · updated **2026-09-06**
>
> This file is canonical. `MEMORY.md` and `UPTAKE_MANIFEST_v0.5.0a1.md §N` point *here* rather than duplicating the
> queue — one list, not three that drift. Full per-round build history lives in the manifest (`§1`–`§16`); this file is
> the forward-looking plan plus a compact done-ledger. Sizes and first-steps were ground-truthed against the source and
> the load-bearing claims independently re-verified at their file:line anchors; each shipped item was red-teamed by an
> independent evil-morty before it landed.

## Governance — the 3-lane projection (authoritative)

Every item is tagged with the lane it advances. **Progress in one lane never implies another.** (Audit:
`AUDIT_GENERIC_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md`.)

- **Lane A — Alpha-conformance.** Does it conform to the v0.5.0a1 alpha contract / laws?
- **Lane B — Chemical genericity.** The transform algebra (capped / bond-order / heterolytic / redox IR-COMMUTE
  families) driven through the **unchanged** bounded SEARCH core.
- **Lane C — Bench-readiness.** Section-11 bench fit (composability[E1] + physical box + process) and section-10.4
  pricing (dated **and** sourced, never invented).

**Poor-man ethos (the bench is a kitchen).** "The kitchen" and "my lab and equipment" mean the same thing: the
whole-path capability model satisfies-or-BLOCKS against **household + outdoors** equipment by default, never assumed
lab infrastructure. "Poor man's fume hood = experiment done outside" — outdoors is a valid *ventilation* control, but
ventilation ≠ hazard clearance (a toxic/corrosive vapour like Br₂/Cl₂ is still surfaced). Affordability is a whole-path
capability claim (material identity, controllable operations, measurement, containment, separation, verification,
closure), not a cheap-reagent list — a route cheap in reagents but needing a control the kitchen can't provide is
`CAPABILITY_BLOCKED`, surfaced, never papered over. See `docs/research/PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md`.
**Cheap epistemology counts too:** the ethos prefers chemistry that *tells you what it is doing* — a route whose
success/failure is legible from cheap, redundant, chemistry-supplied signals (colour change, precipitate, gas evolution,
pH/temperature excursion) beats one that fails silently and needs a $20k instrument to notice. That is a *ranking*
objective (the Observability Score, shipped ROUND 18), kept honest by the rule that a visible checkpoint is **not** chemical
proof (process-indicator / identity / purity stay separate axes — invariants 5 & 7).

## North-star litmus tests (the acceptance gates that keep the lanes honest)

- **Paracetamol litmus (Lane C):** *could a real chemist use our paracetamol decompilation to pick real steps?* Tests
  step-level usefulness.
- **DOW bromine litmus (Lanes B + C + EM) — NEW:** *can we predict Br₂'s decomposition and synthesis, enumerate the
  synthesis paths, rank them **quantitatively on cost**, and reproduce why Herbert Dow's brine-bromine process undercut
  the German bromine cartel?* It forces the WHOLE stack at once — the **redox** IR-COMMUTE family (Cl₂ + 2Br⁻ → Br₂ +
  2Cl⁻), the **electromagnetic** scope (electrolytic oxidation of bromide — electrons at an anode; the one litmus that
  bridges the chemistry core and the electron/circuit layer), **thermodynamics/feasibility**, and the **cost/affordability
  buckets** (`cash_floor`, `affordability_frontier`, `material_quantity`) — down to the humble "poor-man's" evidence
  buckets. A pass quantitatively shows the cheap-brine route beats the mineral route. **Sourcing is favorable:** bromine
  is a USGS-priced inorganic (same pattern as NaCl/Na₂CO₃), so unlike the organic-price wall this litmus's cost axis is
  genuinely achievable. Spawns the queue items marked *(DOW)* below.
  **The litmus is now two-thirds standing:** **✅ Phase 1 — pricing (ROUND 16, DOW-BROMINE-01):** elemental bromine is a
  first-class SOURCED, USGS-priced commodity ($2.70/kg 2024, MCS 2026), INDUSTRIAL-tier (the DOW insight encoded), costed
  end-to-end through the buckets. **✅ Phase 2 — mechanism (ROUND 17, REDOX-DISPLACE-01):** the coupled half-reaction
  combiner enumerates `Cl₂ + 2 Br⁻ → Br₂ + 2 Cl⁻`, the reaction no prior mechanism could reach. **✅ Phase 3 —
  electrochemistry (ROUND 18, ELECTROCHEM-01):** sourced standard potentials prove that displacement is SPONTANEOUS
  (E°cell = +0.271 V, ΔG° = −52.3 kJ/mol) and reproduce why chlorine displaces bromide but not the reverse; the
  electrolytic anode leg is modelled (minimum decomposition voltage + Faraday charge). **Remaining — the cost ranking:**
  the brine-vs-mined *quantitative cost ranking* is still gated on a sourced Cl₂ price + a NaBr feedstock (deferred — the
  aggregator wall; see DEFERRED).

---

## ✅ DONE — current shipped capability

**ROUND 19** (branch `cip-load-stability-2026-09-06`) — 3 builds + 1 recorded decision; each build `design → recon →
build → reproduce → evil-morty → fold → verify`; **additive** (5 new files + additive edits to `service.py`, no existing
behaviour changed); two evil-morty passes found real weaknesses, all folded or documented and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| CIP-ORACLE-01 (item 1, the oracle) | B | The committed **geometric handedness oracle** (`experiments/cip_geometry_oracle_probe.py` + test) — meeting item 1's oracle gate. Builds synthetic tetrahedron coordinates from the OpenSMILES sense bit, reads R/S off a real signed volume (lowest priority away, trace 1→2→3), takes priorities as an INPUT so it decouples geometry from priority-ranking. Green on an exhaustive 48-case {F,Cl,Br,I} battery + two textbook absolute anchors ([C@H](F)(Cl)Br = S, L-alanine = S from one derived convention). **evil-morty (MED-HIGH) right-sized the claim:** it is algebraically `perm_parity ^ sense`, so the 48-case sweep confirms ONE constant, not 48 bearings — it buys one independent bit (a global convention-flip guard) + the decoupling instrument, NOT a ranking-bug catch. Folded: docstrings corrected to that honest scope, `cip_labels` pinned into the frozen hash (so a regression in the *audited* slice reddens it too), the algebraic identity + an external-absolute pipeline check baked into the tests, the dead degeneracy-guard overclaim fixed. |
| DURATION-STABILITY-01 (item 3, the primitive) | B·C | The duration-aware **survival primitive** (`smartchem/experiment/stability_horizon.py` + harness + test) — the time axis on known physics. `f = exp(-k t)`, k = A·exp(-Ea/RT) mirroring the L1 rate engine (R pinned equal, no drift); non-vacuous on N₂O₅ (SURVIVES 60 s → MARGINAL 1 h → DEGRADES 6 h at 298 K), DERIVED/PREDICTED graded, instrument-calibrated (k(298) reproduces the measured 3.38e-5 to ~5%). Fail-closed UNKNOWN with no sourced rate; the compound→rate bridge is structure-keyed + direction-specific (cyclopropane/propene C₃H₆ collision proves no isomer or product borrows a rate). Standalone — NOT wired into core E1 (a stated boundary). **evil-morty SIGNED the anti-fabrication core** (no fail-open, no overflow/NaN reaches a verdict); folded 3 LOW: `is_sourced` docstring softened, an `isfinite` guard added (fail-closed on a non-finite injected record), the "decomposition"→"first-order consumption" naming fixed; documented the reactant-coefficient rate-convention assumption (tracked debt). |
| DAG-HOLD-MR-01 (item 2b) | C | `serial_holds` on `RankedDAGSummary` — the DAG-HOLD-01 serial-schedule hold made machine-readable as `(producer, consumer, minutes)` triples (was a human note only). **Digest-EXCLUDED** (`compare=False`): fully determined by `edges` + `process_requirements`, so it adds no identity and every existing DAG digest stays byte-stable; schema `v1alpha3→v1alpha4`, descriptor `v1alpha15→v1alpha16`, one golden (`response_schema.json`) regenerated, non-vacuous (the 40-min DAG carries `(0,2,40.0)`). |
| ONLOAD-REDERIVE (item 2, decided not built) | C | **Scope decision recorded, build-ready** (`docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`) — item 2's gate was "a scope decision". Resolved: opt-in **digest-excluded** thick per-step payload + a load-time coherence check (mirroring PROCESS-ADMIT-01), protection-equivalent to folding into `result_digest` without changing every route identity. The build (new Molecule/Envelope serializers + conservation-certified route reconstruction + 4 coherence checks) is larger than items 1+2b+3 combined and touches the module that gates every compile, so it is scheduled as its own round rather than rushed. |

**ROUND 18** (commit `5f83f6a` on branch `observability-electrochem-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; **additive** (6 new files + 1 package `__init__` re-export — new exports
only, no schema/golden/compiler-behaviour change); a 6-lens evil-morty workflow found **6 real weaknesses**, all folded
(4 code) or documented (1 boundary + 1 docstring) and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| OBSERVABILITY-01 | C·B | The **three-axis Observability Score** (`smartchem/observation/observability.py`) — cheap epistemology as a ranking objective. A SOURCED `OBSERVABLE_SIGNATURES` table keyed on **canonical structure** (Br₂ the DOW flagship: orange-red colour + phase separation; I₂ the contrast with the starch test), citations REQUIRED (§10.4). The `ObservabilityProfile` keeps **process / identity / purity as three SEPARATE axes**, never one number (invariants 5 & 7 — there is no `overall_score`); Pareto ranking (`observability_dominates`/`_frontier`) that refuses to collapse (a process-strong route does NOT dominate an identity-strong one — incomparable). Non-vacuous: Br₂ (2,1,0) dominates I₂ (1,1,0). Negation-aware bridge to ROUND-17's VERIFICATION bucket. Self-contained (NOT wired into the CostVector — that axis wire-in is a deferred schema bump). Folds: **(HIGH)** corroboration read "colourless" as corroborating COLOUR (the ROUND-17 negation fold via morphological absence) → word-boundary + extended veto; **(MED)** corroboration ignored the signature axis (process→identity leak) → axis-aware evidence; **(MED)** `sourced` was a stored forgeable flag → a computed table-provenance property. |
| ELECTROCHEM-01 | B·EM | The **electrochemical/EM bridge** (`smartchem/electrochemistry.py`) — SOURCED standard reduction potentials (CRC / Bard & Faulkner, known physics) → cell potential, ΔG° = −nFE°, spontaneity, Nernst, electrolysis voltage. Fills the documented fail-closed `open_circuit_voltage` hole in `smartchem/cell.py` for the standard-state case; reuses that module's Faraday law. **Closes the DOW loop with ROUND-17**: `Cl2 + 2 Br- -> Br2 + 2 Cl-` is not only enumerable but **SPONTANEOUS** (E°cell = +0.271 V, ΔG° = −52.3 kJ/mol), the reverse non-spontaneous — the known-answer calibration. Keyed on the couple's structural digest, fail-closed UNKNOWN, W3 (thermodynamic tendency, never rate). Folds: **(MED)** `gibbs_j_per_mol` took n as an unvalidated guess → derive n = lcm(cathode.e, anode.e), refuse a wrong one; **(MED, documented)** aqueous phase-scope boundary (F5, tracked debt); **(LOW)** citation-guarantee docstring overclaim corrected. |

**ROUND 17** (commit `6761350` on branch `process-observation-redox-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; **purely additive** (`git diff --stat main` empty — six new files, zero
edits to existing code, so no schema/golden blast radius); both evil-morty red-teams found REAL weaknesses, all folded and
pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| PROCESS-OBS-01 | C | The **read-only `ProcessObservationIR` evidence-ingress layer** (contract P1) — the poor-man ethos made computational. A new `smartchem/observation/` sibling package (like `smartchem/evidence/`: reuses `Digestible`+`ReactionDirection`, never enters the executor registry, drags zero heavy modules): an immutable source-fragment IR, the five whole-path **capability bundles** (MATERIAL/CAPABILITY/VERIFICATION/CLOSURE/SCALE → EVIDENCED/GAP/BLOCKED, fail-closed), a **no-Frankenprocedure** merge, and a read-only **projection gate**. All 7 contract invariants enforced in code (`provenance_digest` computed not stored; NO readiness field). NOT wired into the response — no schema/golden change. Folds: **(CRITICAL)** negation-blind matcher read "no containment" as containment → whole-support-text negation veto; **(HIGH)** silently-omitted calibration passed a numeric conclusion → fail-closed (positive calibration required), test corrected; **(MEDIUM)** merge spliced different reactions under one self-declared context → identity+direction agreement required. |
| REDOX-DISPLACE-01 | B | The **coupled half-reaction combiner** — the DOW enumeration wall falls. `HalfReactionCouple` (molecular redox couple) + `combine_half_reactions` (electron-balanced by LCM) → a conservation-checked `RedoxDisplacementEdge` that rides the **unchanged** search through an opt-in `RedoxDisplacementProvider` (absent from `DEFAULT_TRANSFORM_REGISTRY`, like heterolytic/redox). Enumerates `Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻` — the 1:2 recon proved unreachable by `redox_edges` (single-species) or `capped_scissions` (1:1). Committed harness (`experiments/redox_displacement_probe.py`, FROZEN_HASH). Fold: **(MEDIUM)** the certificate proved conservation but not redox-ness (a hand-built edge accepted a fabricated electron count / fictitious labels / an identity `Na→Na`) → an electron-ledger verification ties `electrons_transferred` + labels to the actual charge redistribution. |

**ROUND 16** (commit `c9e0fed` on branch `dag-thermo-bromine-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; both evil-morty findings folded and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| DAG-THERMO-01 | C·B | A **per-node thermochemical roll-up** feeds convergent-DAG ranking, so a DAG ranking is now as rich as a linear one. `dag_thermo_rollup` aggregates the four sourced per-reaction verdicts (selectivity/feasibility/equilibrium/kinetics) worst-node-dominated — reusing the *same* per-step providers, default tables, and worst-folds the linear `fit_route` runs; `_dag_score` now mirrors `_route_score` tier-for-tier; `RankedDAGSummary` (schema v1alpha3) surfaces all five verdicts, parity with the route summary. RANKING-ONLY — never changes a section-11 status. Folds: non-vacuous selectivity/kinetics wiring test (a real FAVORED DAG, was all-UNKNOWN); reverted a `rank_dags` table-param trap that re-opened the exact ROUND-15 divergence. |
| DOW-BROMINE-01 | B·C | **Phase 1 of the DOW-bromine litmus:** elemental bromine is now a first-class **SOURCED, USGS-priced** commodity ($2.70/kg 2024, MCS 2026, bromine content), added to both the frozen provenance seed and the live copy; new `INDUSTRIAL` availability tier (not a kitchen commodity — the DOW insight, encoded); costed end-to-end through `basket_cost_vector`/`cash_floor`. Folds: the basis now discloses the figure is a compound-dominated import blend normalized to contained bromine, not an elemental-Br₂ spot price. |

**ROUND 15** (merge `978da9b`) — DAG-HOLD-01 (serial-hold disclosure), DAG-RANK-01 (best-first DAG ranking, structural).
**ROUND 14** (`574a3e2`) — DAG-BENCH-01, STEREO-DOSSIER-01, ORGANIC-PRICE-01 (methanol/Methanex) + 2 refutations.
**Prior rounds (R5–R13):** resonance-canonical identity + caps, the 4 IR-COMMUTE families, per-route/DAG process
re-derivation, cost/affordability, USGS inorganic pricing, combined-verdict HMAC, the sound distinct-Z CIP slice. Full
ledger: `UPTAKE_MANIFEST_v0.5.0a1.md §5`–`§16`.

---

## 🎯 QUEUE — what needs doing, ranked

Ranked by value ÷ cost. **Size** = build effort (S/M/L). **Horizon** = short (cheap, self-contained) / medium (needs a
scope decision or a real build) / long (blocked on a sourcing or oracle wall). *(DOW)* = advances the DOW-bromine litmus.

> ROUND 19 advanced all three: item 1's **oracle** shipped (the namer remains), item 3's duration-aware **primitive**
> shipped (the core wire-in + the DOW-Br₂ primary remain), item 2b (**serial_holds**) shipped, and item 2's **scope
> decision is now resolved** (see `docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`). The queue stays L-heavy.

| # | Item | Lane | Size | Horizon | Gate / blocker |
|---|---|---|---|---|---|
| 1 | **General CIP — the breadth-first namer** (oracle shipped R19) | B | **L** | medium | a correct sphere-by-sphere digraph, validated against the committed oracle |
| 2 | **Composability + physical re-derivation on load — DAG *and* linear** | C | **L** | medium | ~~a scope decision~~ **DECIDED R19** — now a pure build |
| 3 | **Wire the duration-aware verdict into core E1 + the DOW-Br₂ primary** (primitive shipped R19) | B·C | **L** | long | a route intermediate with sourced kinetics + a Br₂ decomposition primary |

### 1 · General CIP — the breadth-first namer (the oracle is now committed) — **L, correctness-critical**
**The oracle gate is met** (ROUND 19, `experiments/cip_geometry_oracle_probe.py`): a committed geometric signed-volume
handedness instrument, green on an exhaustive {F,Cl,Br,I} battery + textbook anchors, that takes priorities as an INPUT
so it decouples "are the priorities right" (the namer) from "is the geometry right" (the oracle). **Honest scope of what
it buys** (an adversarial review right-sized it, baked into the tests): it is algebraically `perm_parity ^ sense`, so it
buys ONE independent bit (a global convention-flip guard) + the decoupling instrument — NOT a ranking-bug catch on the
distinct-Z slice. So the namer build is: the correct **breadth-first / sphere-by-sphere** hierarchical digraph (the exact
DFS-vs-BFS bug that killed R14) + phantom atoms for multiple bonds + Rule 1b/2, validated by
`namer(mol) == geometric_handedness(true_priorities, sense)` on textbook cases where priorities are known. A wrong R/S is
worse than none. *Absorbs E/Z.* **Tracked seam:** the shared parser `@`/`@@` → written-order convention has no external
(RDKit) oracle in the dependency-light core — validated only against hand-checkable textbook absolutes.

### 2 · Composability + physical re-derivation on load — DAG **and** linear — **L, scope DECIDED**
On load only the **process** component is re-derived; composability + physical ride as free-text (closed only by the
opt-in HMAC). **The scope fork is resolved (ROUND 19):** carry the thick per-step payload (target `Molecule`, reactants,
products, reagents, full `ConditionEnvelope`) **opt-in and digest-EXCLUDED** (`compare=False`, like `provider_snapshots`
and R19's `serial_holds`), and close the trust gap via a **load-time coherence check** that re-derives both axes and
compares to the digest-protected claimed verdicts — protection-equivalent to folding into the digest, without changing
every existing route identity. Full rationale + the measured build (new Molecule/Envelope serializers +
conservation-certified route reconstruction + 4 coherence checks + schema bumps + goldens) in
`docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`. It is now a pure build (larger than R19's items 1+2b+3
combined, in the module that gates every compile — so its own round).

### 3 · Wire the duration-aware verdict into core E1 + source the DOW-Br₂ primary — **L, sourcing wall** *(DOW)*
**The primitive shipped (ROUND 19, `smartchem/experiment/stability_horizon.py`):** a duration-aware survival verdict
`f = exp(-k t)`, k from the sourced Arrhenius fit, non-vacuous on N₂O₅ (SURVIVES→MARGINAL→DEGRADES across the hold),
fail-closed UNKNOWN with no sourced rate, structure-keyed (no isomer/product borrows a rate). **What remains:** (a) wire
it into `_judge_transition`'s COMPOSABLE/DEGENERATE flip — needs a route intermediate that carries a sourced
decomposition rate **and** the unit-lock on `ConditionEnvelope.duration` (an unconsumed, unit-unchecked field today); and
(b) the **DOW-Br₂ decomposition primary** — no Br₂ decomposition Arrhenius record is sourceable yet (the DOW half of the
time axis is walled on that primary, independent of the machinery).

### 2b (DONE R19) · machine-readable `serial_holds` on `RankedDAGSummary`
Shipped — the DAG-HOLD-01 serial hold is now a `(producer, consumer, minutes)` triple field (digest-excluded disclosure),
not just a human note. See the DONE ledger.

---

## ⏸️ DEFERRED — attempted at full effort, honestly walled (not fabricated)

- **The DOW brine-vs-mined *cost ranking*** (the DOW litmus's last lane, Lane C). Pricing (R16), mechanism (R17), and
  electrochemistry (R18) all shipped; ranking the brine route against the mined/market route quantitatively needs a
  sourced **Cl₂ price** (the oxidant) and a sourced **NaBr feedstock** price. Chlorine hits the same aggregator wall as
  the organics (no directly-readable dated absolute); NaBr's price would be DERIVED from the bromine-content figure via
  mass fraction (a known-physics derivation, but a different epistemic class than the sourced seed — it does not belong in
  the sourced-absolute table). Deferred until a Cl₂ primary is found or a labelled-DERIVED price path is built. **Only the
  sourced pricing remains a blocker** — the mechanism (ROUND 17's REDOX-DISPLACE-01 enumerates `Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻`)
  and its feasibility (ROUND 18's ELECTROCHEM-01: E°cell = +0.271 V, spontaneous) are both done.
- **A second sourced organic price** (was ROUND-15 item 3; Lane C). Attempted acetic acid (highest value — it ripples
  the methyl-acetate golden) and ethanol. **Wall:** organic producers post price *increases* (Celanese: +$50/MT Feb,
  +$0.10/lb Mar 2026), not absolute reference sheets; absolutes are aggregator-walled (Intratec/ChemAnalyst). Ethanol's
  only primaries are a government *projection* (EIA AEO Table 12 — a forecast, not an observed price) or a *foreign,
  regulated, denatured fuel-grade* price (IPART NSW, needing FX+density+unit conversions for a weak match). None clears
  the bar methanol set (a directly-readable, dated, observed absolute for the exact chemical), so per §10.4
  anti-fabrication this is a **DEFER, not a fabricated price** — the same call R13 made. Revisit if the bar is
  explicitly relaxed, or pivot to **bromine (USGS-priced)** via DOW litmus item 2.

---

## 🚫 NOT BUILDING — deliberately parked (with the reason, so nobody re-walks it)

- **The >64-heavy work-metered resonance escape valve.** Characterized and **refused** (RESONANCE-WORK-01). Reinforced
  YAGNI: the largest *real* target is 13 heavy (aspirin); the 24-heavy figure is a benchmark (coronene); a **72-heavy**
  fixture already proves the >64 path falls back to literal identity in ms — the door is tested-shut. Even built it
  can't separate malice from legit, and it entangles `Molecule.canonical()` (system-wide identity hot path) with an
  uncached meter that conflicts with `resonance_canonical`'s `@lru_cache`. Pinned by `tests/test_resonance_actual_work.py`.
  Re-open only when a real >64-heavy target appears — then re-measure the branch *before* touching core code.

---

## ⚠️ TRACKED DEBT — known, carried, not silently

- **Interchange-law xfail** (Lane A) — `tests/test_laws.py:330`: linear histories cannot quotient independent events by
  interchange. Orthogonal architecture debt; 1 xfail.
- **Load-time free-text trust boundary** (Lane C) — composability/physical claims ride unsigned unless a consumer opts
  into the COMBINED-VERDICT-AUTH HMAC; applies to both DAG and linear. Structural closure = queue item 2.
- **DAG `dag_bench_fit` compute multiplicity** (perf, correctness-neutral) — a DAG-mode compile runs `dag_bench_fit`
  ~3×N (rank_dags key + `of_dag` + `_dag_bench_note`), and each call now ALSO computes the four-provider thermo roll-up
  per node (DAG-THERMO-01), so it is heavier. Still bounded and compile-time (real DAGs are small). Reduce by threading
  one computed fit through all three if it ever matters; not worth a refactor today.
- **Phase-specific electrode potentials** (Lane B·EM; ROUND-18 evil-morty F5) — the halogen couple is phaseless, so the
  sourced `STANDARD_REDUCTION_POTENTIALS` are the AQUEOUS standard values. This is CORRECT for the aqueous DOW displacement
  (+1.087 V) and fail-closed for an explicitly-phased couple (returns UNKNOWN, never a wrong number), but a liquid-phase
  value (Br₂(l) = +1.066 V) is unreachable until a phase-carrying couple API exists. YAGNI today; revisit if a route ever
  reasons about the liquid product.
- **Observability Score → CostVector verification axis** (Lane C; ROUND-18) — the Observability Score is a self-contained
  ranking primitive; feeding its process/identity/purity strengths into the affordability `CostVector` as a verification
  axis needs a new `_AXES` entry + a frontier-entry schema bump + golden regen (a deliberate deferral, not an oversight —
  the score is honest and usable standalone now).
- **CIP oracle's parser-convention seam** (Lane B; ROUND-19, evil-morty) — the geometric oracle validates the geometry→
  label convention against textbook absolutes, but the shared parser's `@`/`@@` → written-neighbour-ORDER convention has
  **no external (RDKit) oracle** in the dependency-light core; it is asserted from the OpenSMILES spec, not cross-checked
  by a third party. A future namer validated against this oracle would inherit a silent parser-convention error. Revisit
  if an external stereo oracle ever enters the toolchain.
- **Duration-stability reactant-coefficient rate convention** (Lane B·C; ROUND-19, evil-morty) — `surviving_fraction`
  assumes the sourced `k` is the per-species rate (`-d[A]/dt = k[A]`), which both seeded records pin in their provenance;
  a future first-order record with coefficient > 1 sourced under the *reaction-rate* convention would be off by the
  stoichiometric factor. The module can't detect the convention from the data — documented boundary, not a silent guess.
- **`ConditionEnvelope.duration` unconsumed + unit-unlocked** (Lane B·C; ROUND-19) — the field is validated but has NO
  consumer in `smartchem/` and (unlike temperature/pressure) NO unit guard. Wiring item 3's duration-aware verdict into
  core E1 must close the unit lock first, or a caller mixing `min`/`h`/`s` durations feeds a silent unit error.

---

## How this file stays current (so it never needs a workflow to rebuild)

Updating `ROADMAP.md` is part of the per-round ritual, the same reflex as bumping `UPTAKE_MANIFEST §N` and the README
suite count:

1. Ship a round → move each shipped item from **QUEUE** to the **DONE** ledger with its commit.
2. Re-stamp `verified @ <commit>` and the suite count at the top.
3. Add any new queue items with lane + size + gate + cheapest first step. Anything walled → **DEFERRED**; anything
   refused → **NOT BUILDING**; anything carried → **TRACKED DEBT**.

Next session: read *this file*, not a 5-agent recon.
