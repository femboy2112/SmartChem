# SmartChem roadmap

> **The single source of truth for what is done, what is queued, and what is deliberately not being built.**
> `verified @ 574a3e2` · suite **4145 passed / 14 skipped / 1 xfailed** (PySCF-present dev venv) · updated **2026-09-06**
>
> This file is canonical. `MEMORY.md` and `UPTAKE_MANIFEST_v0.5.0a1.md §14.6` point *here* rather than duplicating the
> queue — one list, not three that drift. Full per-round build history lives in the manifest (`§1`–`§14`); this file is
> the forward-looking plan plus a compact done-ledger. Sizes and first-steps below were ground-truthed against the
> source (5-bearing recon, 2026-09-06); the load-bearing new claims were independently re-verified at the file:line
> anchors cited.

## Governance — the 3-lane projection (authoritative)

Every item is tagged with the lane it advances. **Progress in one lane never implies another.** (Audit:
`AUDIT_GENERIC_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md`.)

- **Lane A — Alpha-conformance.** Does it conform to the v0.5.0a1 alpha contract / laws?
- **Lane B — Chemical genericity.** The transform algebra (capped / bond-order / heterolytic / redox IR-COMMUTE
  families) driven through the **unchanged** bounded SEARCH core.
- **Lane C — Bench-readiness.** Section-11 bench fit (composability[E1] + physical box + process) and section-10.4
  pricing (dated **and** sourced, never invented). North star: *could a real chemist use this to pick real steps?*
  (the paracetamol litmus).

---

## ✅ DONE — current shipped capability (@ `574a3e2`)

**ROUND 14** (PR #9, merge `574a3e2`) — 3 builds + 2 honest refutations, each `design → recon → build → reproduce →
evil-morty → fold → verify`:

| Item | Lane | Commit | What shipped |
|---|---|---|---|
| DAG-BENCH-01 | C | `5fc3b2b` | Convergent DAGs get the **combined** section-11 bench fit (composability + physical + process); a combined-FITS DAG flips `exit_code` → SUCCESS. |
| STEREO-DOSSIER-01 | B | `4b05800` | First consumer of `cip_labels`/`configuration_complete`: perceived target R/S surfaced in the human dossier (**perception-only**, discloses named **and** deferred centres independently). |
| RESONANCE-WORK-01 | B | `ca51570` | **Refutation** — an actual-work meter fixes the nominal over-charge but a legit PAH still out-costs a crafted grind: a TIME bound, not a malice filter. Caps unchanged; tripwire pins it. |
| ORGANIC-PRICE-01 | C | `3919589` | First **sourced** organic price — methanol from the Methanex sheet (PDF read directly), frozen seed + byte-for-byte cross-check. Lights the cash floor. |
| ID-STEREO-CIP-WALL | B | `3485d35` | **Refutation** — the general recursive CIP was built, proven to mislabel branch-vs-chain (DFS vs breadth-first, ~740 flips), and **reverted**. The sound distinct-Z slice stands; the wall is pinned by a tripwire. |

**Prior rounds (R5–R13):** resonance-canonical identity + caps, per-route/DAG process re-derivation, the 4 IR-COMMUTE
families, cost/affordability (`cash_floor`, `material_quantity`, `affordability_frontier`), USGS inorganic pricing,
combined-verdict HMAC auth, configuration/chirality perception, the sound distinct-Z CIP slice. Full ledger:
`UPTAKE_MANIFEST_v0.5.0a1.md §5`–`§13`.

---

## 🎯 QUEUE — what needs doing, ranked

Ranked by value ÷ cost. **Size** = build effort (S/M/L). **Horizon** = short (cheap, self-contained wins) / medium
(needs a scope decision or a real build) / long (blocked on a sourcing or oracle wall).

| # | Item | Lane | Size | Horizon | Gate / blocker |
|---|---|---|---|---|---|
| 1 | **DAG hold-duration disclosure** (item 3, small half) | C·B | **S** | short | none — pure plumbing over numbers already computed |
| 2 | **`rank_dags` — DAG best-first ranking** (new; critic gap 1) | C | **M** | short | none — reuses existing scorers |
| 3 | **One more sourced organic price** (acetic acid) | C | **S** | short | a **primary** producer price sheet (else honest DEFER) |
| 4 | **General CIP — oracle first, then breadth-first namer** (item 1) | B | **L** | medium | a **committed, independent geometric oracle** (absent) |
| 5 | **Composability + physical re-derivation on load — DAG *and* linear** (item 2, widened by critic gap 2) | C | **L** | medium | a scope decision (full vs scoped-partial-with-honest-boundary) |
| 6 | **Duration-aware stability verdict** (item 3, large half) | B·C | **L** | long | sourced decomposition-kinetics per compound (none exist) |

### 1 · DAG hold-duration disclosure — **S, do first**
A convergent DAG's serial schedule holds an early branch's intermediate through its siblings; E1 composability is
**time-blind** (adjacent-handoff only, `composability.py:192-279`), so that hold's stability is silently unmodeled.
**Cheapest win on the board:** a `dag_hold_minutes(dag, edges)` helper summing `elapsed_minutes` of steps scheduled
between producer and consumer under `dag.topological_order()` (`dag.py:228-230`), threaded into `DAGComposability` as a
disclosed gap (mirrors `_pressure_note`, `composability.py:101-121`). **Zero sourced data, zero schema bump.** Turns a
silent boundary into a loud, non-vacuous disclosure — the same honest-widening move RESONANCE-WORK-01 made.

### 2 · `rank_dags` — DAG best-first ranking — **M, high value**
**Verified hole:** `service.py:2062` says *"DAG mode ranks nothing LINEARLY"*; `service.py:2073` is a straight unsorted
map over discovery order; `rank_dags`/`_dag_score` are **absent** while the linear analogue (`_route_score`
`drafter.py:450`, `rank_routes` `:490`) exists. `search_dags` (`max_dags=100`) can return many admissible DAGs, so a
chemist facing several convergent routes gets **no signal on which is best** — directly against the north star. Build a
`_dag_score`/`rank_dags` reusing `DAGBenchFit` + the existing selectivity/feasibility/equilibrium/kinetics providers per
node, analogous to `fit_route → rank_routes`. Arguably belongs *ahead of* items 4–6: a plain missing capability on a
surface ROUND 14 **just shipped**, not a refinement.

### 3 · One more sourced organic price (acetic acid) — **S engineering, sourcing-gated**
Today only **methanol** is priced (+ 2 USGS inorganics: NaCl, Na₂CO₃). Five registered organics stay unpriced
(`experiments/methanex_methanol_seed.py:78 UNPRICED_NO_PRIMARY_SOURCE`). Adding one = a frozen seed + one branch in
`cost_observation_for` + 2 tests, mirroring methanol line-for-line. **Acetic acid** is the highest-value pick (it
co-occurs in the methyl-acetate golden route → a genuine 2-axis Pareto). The cost driver is **sourcing, not code**:
find a **primary** producer sheet (WebFetch/READ directly, no aggregator/walled page — those failed twice). If the hunt
comes up empty, the honest outcome is a **DEFERRED**, not a fabricated price. Ripples the `recompile_routes_found.json`
CLI-JSON golden + `test_affordability_wire.py` cash-floor assertions.

### 4 · General CIP — the oracle first, then the breadth-first namer — **L, correctness-critical**
The distinct-Z slice (`_cip_labels` `smiles.py:930`, sphere-1 only) stands; the general R/S is a **named deferral**.
A correct general CIP needs breadth-first sphere-by-sphere comparison + phantom-0 padding (π-bonds/ring-closures) +
aromatic Rule-1b. **The wall isn't the namer — it's the oracle.** No chirality oracle exists in the dependency-light
core: `configuration_digest` is WL-graph-colour parity (spelling-invariance + enantiomer-inequality **only** — zero
ability to say an R/S *letter* is correct); `geometry.py seed_coordinates` is chirality-**blind**. An oracle was built
and discarded **twice** (R13 96/96, R14 13/13) and **both times missed** the systematic bug (evil-morty caught it, not
the oracle) — and neither was ever committed (a repeat violation of *[experiments are committed]*).
**First step (cheap, and it is *not* the namer):** write and **commit** to `experiments/` a standalone geometric
signed-volume handedness oracle — a genuinely *different* computation from any digraph, so it cannot share the
DFS/BFS bug class — green on a real textbook R/S battery (start from the L-alanine anchor, `test_cip_naming.py:26-39`).
**Do not write one line of the BFS digraph until that oracle is committed and green.** A wrong R/S is worse than none.
> **Absorbs E/Z:** the manifest grouped E/Z under item 6 (time axis), but that's wrong in code — E/Z is a
> constitutional/topology problem + this same CIP machinery, with **no** tie to time/decomposition. E/Z's real blocker
> is *this* breadth-first wall. Track E/Z here, not under stability.

### 5 · Composability + physical re-derivation on load — DAG **and** linear — **L**
On load, only the **process** component of a combined fit is re-derived; composability + physical/reagent/equipment
ride as **free-text**, closed only by the opt-in COMBINED-VERDICT-AUTH HMAC. **This is bigger than "mirror item 1":**
item 1's process axis was cheap only because `ProcessRequirements` was already a small self-contained record.
Composability + physical need **brand-new payload never carried in any ranked summary** — the per-edge intermediate
`Molecule` (discarded today at `service.py:1129`, the `_intermediate` underscore), the full `ConditionEnvelope` (T/P
Intervals, not just the process sub-object), and — for reagent/equipment checks — full per-step reactant/product
`Molecule` tuples, which **contradicts the deliberate "thin projection" design** (`service.py:895-897`). A scoped cut
(envelope + per-edge intermediate → closes composability + T/P bounds, leaves reagent/equipment as a *declared*
residual) is Medium; full closure is Large. **Widen the scope to DAG + linear in one pass** — the boundary is
identical on the linear side (`service.py:1504-1512`), and fixing DAGs alone would open a fresh avoidable asymmetry.

### 6 · Duration-aware stability verdict — **L, sourcing wall**
The full version of item 1: let E1 render a duration-aware COMPOSABLE/DEGENERATE verdict instead of an instantaneous
threshold. Needs sourced decomposition-kinetics (Eₐ/A or a half-life at a reference T) for the compounds in
`SEED_STABILITY_REFS` — and today there is **zero overlap** between that table (6 compounds) and `SEED_KINETIC_REFS`
(2 reactions). That's a per-compound **primary-source-read wall**, structurally identical to organic pricing (item 3),
which is what makes the full axis Long, not Medium. Do item 1 (the S diagnostic) first; this is the payoff, later.

---

## 🚫 NOT BUILDING — deliberately parked (with the reason, so nobody re-walks it)

- **The >64-heavy work-metered resonance escape valve.** Characterized and **refused** (RESONANCE-WORK-01). Reinforced
  YAGNI: the largest *real* target is **13 heavy** (aspirin); the 24-heavy figure is a resonance-cost *benchmark*
  (coronene); and a **72-heavy** fixture (`test_resonance_identity.py:113-124`) already proves the >64 path falls back
  to literal identity in milliseconds — the door is tested-shut, not open. Even if built, it would **not** separate
  malice from legit (a legit PAH out-costs the grind in actual work), and it entangles `Molecule.canonical()` (the
  system-wide identity hot path) with an uncached meter that conflicts with `resonance_canonical`'s `@lru_cache`. Pinned
  by `tests/test_resonance_actual_work.py`. **Re-open only when a real >64-heavy target appears** — and then re-measure
  which branch it lands in *before* touching core code.

---

## ⚠️ TRACKED DEBT — known, carried, not silently

- **Interchange-law xfail** (Lane A) — `tests/test_laws.py:330` `test_true_parallel_interchange_is_architecture_debt`:
  *"linear histories cannot quotient independent events by interchange."* Orthogonal architecture debt; 1 xfail.
- **Load-time free-text trust boundary** (Lane C) — composability/physical claims ride unsigned unless a consumer opts
  into the COMBINED-VERDICT-AUTH HMAC. Honestly labeled in-source (5 docstrings), applies to **both** DAG and linear
  (see item 5). Structural closure = item 5; cryptographic closure already exists (opt-in).

---

## How this file stays current (so it never needs a workflow to rebuild)

Updating `ROADMAP.md` is part of the per-round ritual, the same reflex as bumping `UPTAKE_MANIFEST §N` and the README
suite count:

1. Ship a round → move each shipped item from **QUEUE** to the **DONE** ledger with its commit.
2. Re-stamp `verified @ <commit>` and the suite count at the top.
3. Add any new queue items with lane + size + gate + cheapest first step.
4. Anything refused → **NOT BUILDING** with the reason. Anything carried → **TRACKED DEBT**.

Next session: read *this file*, not a 5-agent recon.
