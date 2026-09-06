# SmartChem roadmap

> **The single source of truth for what is done, what is queued, and what is deliberately not being built.**
> `verified @ 96730ae` · suite **4157 passed / 14 skipped / 1 xfailed** (PySCF-present dev venv) · updated **2026-09-06**
>
> This file is canonical. `MEMORY.md` and `UPTAKE_MANIFEST_v0.5.0a1.md §N` point *here* rather than duplicating the
> queue — one list, not three that drift. Full per-round build history lives in the manifest (`§1`–`§15`); this file is
> the forward-looking plan plus a compact done-ledger. Sizes and first-steps were ground-truthed against the source (a
> 5-bearing recon, 2026-09-06) and the load-bearing claims independently re-verified at their file:line anchors; each
> shipped item was red-teamed by an independent evil-morty before it landed.

## Governance — the 3-lane projection (authoritative)

Every item is tagged with the lane it advances. **Progress in one lane never implies another.** (Audit:
`AUDIT_GENERIC_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md`.)

- **Lane A — Alpha-conformance.** Does it conform to the v0.5.0a1 alpha contract / laws?
- **Lane B — Chemical genericity.** The transform algebra (capped / bond-order / heterolytic / redox IR-COMMUTE
  families) driven through the **unchanged** bounded SEARCH core.
- **Lane C — Bench-readiness.** Section-11 bench fit (composability[E1] + physical box + process) and section-10.4
  pricing (dated **and** sourced, never invented).

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

---

## ✅ DONE — current shipped capability

**ROUND 15** (commit `96730ae` on branch `roadmap-pin-2026-09-06`) — 2 builds; each `design → recon → build →
reproduce → evil-morty → fold → verify`; both evil-morty MEDIUM findings folded and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| DAG-HOLD-01 | C·B | A convergent DAG's serial-schedule **hold** (an early branch's intermediate waiting through its siblings) is now **disclosed concretely** in the emitted DAG bench note — a sound lower bound over the DAG's own topological schedule, observation-only (never changes a verdict), schedule-relative (a sibling isn't implied safe). Folds: surfaced to a real product surface (was a dead `explain()`); schedule-relative wording. |
| DAG-RANK-01 | C | `rank_dags`/`_dag_score` rank convergent DAGs **best-first** (the DAG analogue of `rank_routes`), closing the "DAG mode ranks nothing" gap DAG-BENCH-01 left open. Folds: non-vacuous service test (real multi-dossier reorder); removed an unused `stability=` divergence trap. |

**ROUND 14** (PR #9, merge `574a3e2`) — DAG-BENCH-01 (combined DAG bench fit), STEREO-DOSSIER-01 (perceived R/S in the
dossier), ORGANIC-PRICE-01 (first sourced organic price, methanol/Methanex), + 2 honest refutations (RESONANCE-WORK-01;
general-CIP wall). **Prior rounds (R5–R13):** resonance-canonical identity + caps, the 4 IR-COMMUTE families, per-route/
DAG process re-derivation, cost/affordability, USGS inorganic pricing, combined-verdict HMAC, the sound distinct-Z CIP
slice. Full ledger: `UPTAKE_MANIFEST_v0.5.0a1.md §5`–`§15`.

---

## 🎯 QUEUE — what needs doing, ranked

Ranked by value ÷ cost. **Size** = build effort (S/M/L). **Horizon** = short (cheap, self-contained) / medium (needs a
scope decision or a real build) / long (blocked on a sourcing or oracle wall). *(DOW)* = advances the DOW-bromine litmus.

| # | Item | Lane | Size | Horizon | Gate / blocker |
|---|---|---|---|---|---|
| 1 | **Per-node thermochemical roll-up for `rank_dags`** | C | **M** | short | none — reuses the per-reaction providers |
| 2 | **Bromine synthesis paths + USGS bromine pricing** *(DOW)* | B·C | **M** | short | a USGS bromine price READ (sourceable) |
| 3 | **General CIP — oracle first, then breadth-first namer** | B | **L** | medium | a committed, independent geometric oracle |
| 4 | **Composability + physical re-derivation on load — DAG *and* linear** | C | **L** | medium | a scope decision |
| 5 | **Duration-aware stability verdict** (the full time axis) | B·C | **L** | long | sourced decomposition-kinetics per compound |
| 6 | **Electrochemical / EM bridge** (electrolytic bromide oxidation) *(DOW)* | B·EM | **L** | long | an electrolysis model reaching the electron layer |

### 1 · Per-node thermochemical roll-up for `rank_dags` — **M, the natural next win**
DAG-RANK-01 ranks on the **structural** tiers only (status → composability → gap/exclusion counts) — the three sourced
thermochemical tiebreakers a *linear* route gets (selectivity / feasibility / equilibrium) and the kinetics tie are
**per-reaction** verdicts a DAG does not aggregate yet (`DAGBenchFit` carries none). Aggregate them per node so a DAG
ranking is as rich as a linear one. Reuses the existing selectivity/feasibility/equilibrium/kinetics providers; extends
what ROUND 15 just shipped. *(Also optional, S: make the DAG-HOLD-01 hold **machine-readable per-route** via a
`serial_hold_notes` field on `RankedDAGSummary` — a schema bump + golden regen; today the hold is in the human note only.)*

### 2 · Bromine synthesis paths + USGS bromine pricing — **M, opens the DOW litmus** *(DOW)*
The first concrete step of the DOW-bromine litmus, and cheap because bromine is **USGS-priced** (same seed pattern as
NaCl/Na₂CO₃ in `commodity_pricing.py` — no organic-price wall). First move: source the USGS bromine price (READ the
primary), then enumerate the Br₂ synthesis paths (Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻ redox displacement first) and rank them on
cost. Exercises the redox IR-COMMUTE family + the cost/affordability buckets end to end.

### 3 · General CIP — the oracle first, then the breadth-first namer — **L, correctness-critical**
The distinct-Z slice stands; the general R/S is a named deferral. **The wall isn't the namer — it's the oracle** (built
and discarded twice, R13/R14, both times missing the bug). First step, committed to `experiments/`: a standalone
geometric signed-volume handedness oracle (a genuinely *different* computation from any digraph), green on a textbook
battery, **before one line of the BFS namer**. A wrong R/S is worse than none. *Absorbs E/Z* (a constitutional + CIP
problem, no tie to a time axis).

### 4 · Composability + physical re-derivation on load — DAG **and** linear — **L**
On load only the **process** component is re-derived; composability + physical ride as free-text (closed only by the
opt-in HMAC). Bigger than "mirror item 1": needs brand-new payload (per-edge intermediate `Molecule`, full
`ConditionEnvelope`, per-step reactant/product tuples) that contradicts the thin-projection design. Widen the fix to
DAG **and** linear in one pass (the boundary is symmetric).

### 5 · Duration-aware stability verdict — **L, sourcing wall** *(and DOW: Br₂ decomposition)*
The full version of the time axis: let E1 render a duration-aware COMPOSABLE/DEGENERATE verdict instead of an
instantaneous threshold (ROUND 15 shipped only the *diagnostic* half — the hold disclosure). Needs sourced
decomposition-kinetics (Eₐ/A or half-life) — zero overlap today between `SEED_STABILITY_REFS` and `SEED_KINETIC_REFS`; a
per-compound primary-source wall. Also the home for the DOW litmus's Br₂-decomposition prediction.

### 6 · Electrochemical / EM bridge — **L, long horizon** *(DOW)*
Dow's process is *electrolytic* oxidation of bromide — the DOW litmus's demand that we reach the electron/circuit layer
([electromagnetic scope]). Model anodic oxidation (electrons at an electrode) so bromide→bromine can be costed and
ranked as an electrochemical route, bridging the chemistry core and the EM layer. The most ambitious lane; long horizon.

---

## ⏸️ DEFERRED — attempted at full effort, honestly walled (not fabricated)

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
  ~3×N (rank_dags key + `of_dag` + `_dag_bench_note`), bounded and compile-time. Reduce by threading one computed fit
  through all three if it ever matters; not worth a refactor today.

---

## How this file stays current (so it never needs a workflow to rebuild)

Updating `ROADMAP.md` is part of the per-round ritual, the same reflex as bumping `UPTAKE_MANIFEST §N` and the README
suite count:

1. Ship a round → move each shipped item from **QUEUE** to the **DONE** ledger with its commit.
2. Re-stamp `verified @ <commit>` and the suite count at the top.
3. Add any new queue items with lane + size + gate + cheapest first step. Anything walled → **DEFERRED**; anything
   refused → **NOT BUILDING**; anything carried → **TRACKED DEBT**.

Next session: read *this file*, not a 5-agent recon.
