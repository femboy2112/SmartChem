# SmartChem roadmap

> **The single source of truth for what is done, what is queued, and what is deliberately not being built.**
> `verified @ 6761350` · suite **4209 passed / 14 skipped / 1 xfailed** (PySCF-present dev venv) · updated **2026-09-06**
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
objective (the Observability Score, queue item 7), kept honest by the rule that a visible checkpoint is **not** chemical
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
  **✅ Phase 1 DONE (ROUND 16, DOW-BROMINE-01):** elemental bromine is now a first-class SOURCED, USGS-priced commodity
  ($2.70/kg 2024, MCS 2026), INDUSTRIAL-tier (not kitchen-obtainable — the DOW insight encoded), costed end-to-end
  through the buckets. **Phase 2 (queued/deferred):** the Br₂ synthesis-path *enumeration* needs a coupled
  half-reaction combiner no mechanism has today (queue #2), and the brine-vs-mined *cost ranking* is blocked on a
  sourced Cl₂ price (deferred — the aggregator wall).

---

## ✅ DONE — current shipped capability

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

> ROUND 17 shipped queue items 1 (`ProcessObservationIR`) and 2 (the coupled half-reaction combiner) — see DONE above.
> The remaining items are renumbered; the **DOW displacement now has its enumeration mechanism**, so its remaining gate is
> purely the sourced Cl₂/NaBr pricing (see DEFERRED).

| # | Item | Lane | Size | Horizon | Gate / blocker |
|---|---|---|---|---|---|
| 1 | **Observability Score — prefer routes with cheap, visible, redundant success/failure signatures** *(DOW)* | C·B | **L** | medium | a sourced per-reaction observable-signature table + the process/identity/purity axis separation |
| 2 | **General CIP — oracle first, then breadth-first namer** | B | **L** | medium | a committed, independent geometric oracle |
| 3 | **Composability + physical re-derivation on load — DAG *and* linear** | C | **L** | medium | a scope decision |
| 4 | **Duration-aware stability verdict** (the full time axis) *(DOW)* | B·C | **L** | long | sourced decomposition-kinetics per compound |
| 5 | **Electrochemical / EM bridge** (electrolytic bromide oxidation) *(DOW)* | B·EM | **L** | long | an electrolysis model (mechanism now unblocked by REDOX-DISPLACE-01) |

### 1 · Observability Score — prefer routes whose success/failure is cheaply visible — **L** *(DOW)*
The poor-man ethos is not only cheap reagents + cheap apparatus; it is cheap **epistemology** — *can I tell, with
low-cost observations, whether the process is behaving correctly?* A route that needs chromatography/NMR/MS after every
step is structurally hostile to the ethos even when its reagents are cheap. So make **observability a first-class ranking
objective**: prefer a route with a *multimodal success signature* — an expected colour change AND a precipitate AND a
pH/temperature excursion AND a yield window — over one that fails silently. A 70 %-yield route with three obvious
checkpoints can beat a 90 % route that needs a $20k instrument to notice a silent failure.

**Builds directly on ROUND-17's `ProcessObservationIR` VERIFICATION bucket** (PROCESS-OBS-01, shipped): that bucket already
asks whether an evidence-backed observable/acceptance plan exists; the Observability Score *ranks* on how cheap,
redundant, and chemistry-supplied those observables are — colour, gas evolution start/stop, precipitate, phase
separation, crystal formation, a pH threshold crossing, conductivity, a temperature excursion, melting/freezing
behaviour, mass change: free sensors the chemistry itself supplies.

**The load-bearing honesty (why it is an L, not a quick win):** a visible checkpoint is **not** chemical proof. A blue
solution turning clear is good evidence a *state changed*; it does not establish that the final material *is* the target
or is *pure*. So the score keeps three axes SEPARATE and never collapses them to one number (contract invariants 5 & 7):
**process indicators** ("something happened as expected") vs **identity tests** ("this behaves like target X") vs
**purity tests** ("little enough else present"). A poor-man route ideally has redundant cheap indicators at all three
levels; the score reports the three independently, and a strong process signal never silently upgrades to an
identity/purity claim. **Gate/blocker:** the observable signatures are themselves CLAIMS that need SOURCING (you cannot
fabricate "turns orange" — §10.4 anti-fabrication), so this needs a *sourced per-reaction observable-signature table*,
tiny by design and UNKNOWN elsewhere — the same curation wall as `SEED_CONDITIONS`. It feeds the affordability cost
vector's verification / failure-ambiguity terms as a new axis (never a hard blocker unless a *required* observable is
absent). *(Further, P3-flavoured: a self-diagnosing step — advance / recover / abort gated on whether observables
O₁..Oₙ fall in expected ranges — a poor-man's macroscopic process-control language, built on the operation graph of
contract P3.)* **DOW tie-in:** bromine displacement (now enumerable, REDOX-DISPLACE-01) has a gorgeous cheap signature —
elemental Br₂'s orange/red colour appearing and phase-separating into an organic/vapour layer (Herbert Dow literally
blew it out as red vapour) — a natural first observability testbed.

### 2 · General CIP — the oracle first, then the breadth-first namer — **L, correctness-critical**
The distinct-Z slice stands; the general R/S is a named deferral. **The wall isn't the namer — it's the oracle** (built
and discarded twice, R13/R14, both times missing the bug). First step, committed to `experiments/`: a standalone
geometric signed-volume handedness oracle (a genuinely *different* computation from any digraph), green on a textbook
battery, **before one line of the BFS namer**. A wrong R/S is worse than none. *Absorbs E/Z* (a constitutional + CIP
problem, no tie to a time axis).

### 3 · Composability + physical re-derivation on load — DAG **and** linear — **L**
On load only the **process** component is re-derived; composability + physical ride as free-text (closed only by the
opt-in HMAC). Needs brand-new payload (per-edge intermediate `Molecule`, full `ConditionEnvelope`, per-step
reactant/product tuples) that contradicts the thin-projection design. Widen the fix to DAG **and** linear in one pass
(the boundary is symmetric). *(Also optional, S: make the DAG-HOLD-01 hold **machine-readable per-route** via a
`serial_hold_notes` field on `RankedDAGSummary` — a schema bump + golden regen; today the hold is in the human note only.)*

### 4 · Duration-aware stability verdict — **L, sourcing wall** *(and DOW: Br₂ decomposition)*
The full version of the time axis: let E1 render a duration-aware COMPOSABLE/DEGENERATE verdict instead of an
instantaneous threshold (ROUND 15 shipped only the *diagnostic* half — the hold disclosure). Needs sourced
decomposition-kinetics (Eₐ/A or half-life) — zero overlap today between `SEED_STABILITY_REFS` and `SEED_KINETIC_REFS`; a
per-compound primary-source wall. Also the home for the DOW litmus's Br₂-decomposition prediction.

### 5 · Electrochemical / EM bridge — **L, long horizon** *(DOW)*
Dow's process is *electrolytic* oxidation of bromide — the DOW litmus's demand that we reach the electron/circuit layer
([electromagnetic scope]). Model anodic oxidation (electrons at an electrode) so bromide→bromine can be costed and
ranked as an electrochemical route, bridging the chemistry core and the EM layer. **The half-reaction primitive now
exists** (REDOX-DISPLACE-01's `HalfReactionCouple` / electron-balancing, ROUND 17) — the remaining work is the electrode
potential / current model. The most ambitious lane; long horizon.

---

## ⏸️ DEFERRED — attempted at full effort, honestly walled (not fabricated)

- **The DOW brine-vs-mined *cost ranking*** (DOW phase 2, Lane C). Phase 1 (sourced bromine pricing) shipped; ranking
  the brine route against the mined/market route quantitatively needs a sourced **Cl₂ price** (the oxidant) and a sourced
  **NaBr feedstock** price. Chlorine hits the same aggregator wall as the organics (no directly-readable dated absolute);
  NaBr's price would be DERIVED from the bromine-content figure via mass fraction (a known-physics derivation, but a
  different epistemic class than the sourced seed — it does not belong in the sourced-absolute table). Deferred until a
  Cl₂ primary is found or a labelled-DERIVED price path is built. **The enumeration mechanism is no longer a blocker** —
  ROUND 17's REDOX-DISPLACE-01 makes `Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻` enumerable; only the sourced pricing remains.
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
  into the COMBINED-VERDICT-AUTH HMAC; applies to both DAG and linear. Structural closure = queue item 4.
- **DAG `dag_bench_fit` compute multiplicity** (perf, correctness-neutral) — a DAG-mode compile runs `dag_bench_fit`
  ~3×N (rank_dags key + `of_dag` + `_dag_bench_note`), and each call now ALSO computes the four-provider thermo roll-up
  per node (DAG-THERMO-01), so it is heavier. Still bounded and compile-time (real DAGs are small). Reduce by threading
  one computed fit through all three if it ever matters; not worth a refactor today.

---

## How this file stays current (so it never needs a workflow to rebuild)

Updating `ROADMAP.md` is part of the per-round ritual, the same reflex as bumping `UPTAKE_MANIFEST §N` and the README
suite count:

1. Ship a round → move each shipped item from **QUEUE** to the **DONE** ledger with its commit.
2. Re-stamp `verified @ <commit>` and the suite count at the top.
3. Add any new queue items with lane + size + gate + cheapest first step. Anything walled → **DEFERRED**; anything
   refused → **NOT BUILDING**; anything carried → **TRACKED DEBT**.

Next session: read *this file*, not a 5-agent recon.
