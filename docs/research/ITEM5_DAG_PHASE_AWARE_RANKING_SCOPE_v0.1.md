# ITEM5-DAG-PHASE-01 — phase-aware convergent-DAG ranking (the R43 defer, discharged)

**Round:** R44 (item-5 DAG residual). **Lane:** B·C. **Status:** `rank_dags` + `of_dag` phase-threaded through one
seam; forcing consumer built (single-step AND convergent); the R43 defer DISCHARGED. **Evidence:**
`experiments/item5_dag_phase_aware_ranking_probe.py` (FROZEN_HASH `68b15e1a…08c4bfb5`, RDKit-free `validate()`) +
`tests/test_item5_dag_phase_aware_ranking.py`.

## The mandate

R43 (ITEM5-PHASE-RANK-01) made the LINEAR ranker (`rank_routes`) phase-aware but left the DAG ranker a documented
DEFER, with the reason recorded verbatim (that round's scope doc §Boundaries 1, and the `rank_dags` docstring):

> `rank_routes` could accept `phases` **soundly** because it RETURNS the scored `RouteFit`s and
> `RankedRouteSummary.of_fit` projects THOSE (phase-aware) fits — rank and dossier cannot disagree. `rank_dags`
> instead returns the DAGs, which `RankedDAGSummary.of_dag` **RE-PROJECTS under the default tables** (no phases).
> Exposing `phases` on `rank_dags` alone would rank under a declared phase while every dossier projected the
> phase-blind verdict — the exact latent divergence the ROUND-15 fold prevents. **Unlock:** a service API that
> carries a phase declaration into both `rank_dags` and `of_dag`.

This round builds exactly that unlock and discharges the defer.

## What shipped (all additive `phases=None`, default byte-identical)

The whole lower thermo stack (`feasibility_of_step` → `resolve_thermo`; `route_net_delta_g`) was already phase-aware
from R36/R37. The break was purely at the DAG rollup + ranker + projection layer:

- `smartchem/experiment/dag.py` — `dag_thermo_rollup(..., phases=None)` forwards `phases` into the per-node
  `feasibility_of_step` fold ONLY (equilibrium stays phase-blind — see Boundary 2).
- `smartchem/experiment/drafter.py` — `dag_bench_fit(..., phases=None)` → `dag_thermo_rollup(..., phases=phases)`;
  `rank_dags(..., phases=None)` → `dag_bench_fit(dag, box, phases=phases)` **and** `route_net_delta_g(dag, phases=phases)`
  (the M2b additive drive).
- `smartchem/service.py` — `RankedDAGSummary.of_dag(dag, box, *, phases=None)` → `dag_bench_fit(dag, box, phases=phases)`;
  **the new seam** `ranked_dag_dossiers(dags, box, *, phases=None)` = `of_dag(d, box, phases) for d in rank_dags(dags, box, phases)`
  — one declaration into BOTH sides. `_run_recompile`'s DAG-mode path now calls the seam (with no phases, see Boundary 3).

### Why the seam is the sound shape (not `phases` bolted onto each side independently)

The whole hazard the ROUND-15 fold named is a caller ranking under one phase while the dossiers project under another.
Making both `rank_dags` and `of_dag` *able* to take `phases` is necessary but not sufficient — a caller could still
pass different dicts (or one and not the other) and silently reopen the divergence. `ranked_dag_dossiers` is the seam
that takes ONE dict and feeds both, so "rank and dossier move together" is **structural**, not a per-call-site
convention (the birdperson alignment discipline the codebase applies repeatedly). `_run_recompile` uses the seam, so the
live path can never drift.

### The forcing consumer (the sign-tier ranking-ORDER flip) — robust, default thermo

Two flips, both on the default sourced table, no injection:

1. **Single-step** (both DAGs UNCONSTRAINED under an empty box, so the feasibility SIGN tier decides): `Br₂ → 2 Br·`
   (dual-phase) vs the phase-INERT, unsourced `I₂ → 2 I·`. `phases=None` → both feasibility=UNKNOWN → tie → discovery
   order `[Br₂, I₂]`. `phases={Br₂:"gas", Br:"gas"}` → the Br₂ DAG rolls up to UNFAVORABLE and sinks → order flips to
   `[I₂, Br₂]`.
2. **Genuinely convergent** (two 3-step DAGs of the SAME status and equal gap counts, so the feasibility tier — not
   the status tier — decides): a Br₂-carrying convergent DAG (`Br₂→2Br·` ; `I₂→2I·` ; `Br·+I·→IBr`, a real join,
   in-degree 2) vs a phase-inert convergent sibling (`I₂→2I·` ; `Cl₂→2Cl·` ; `I·+Cl·→ICl`). Both UNKNOWN status →
   `phases=None` ties → `[C, X]`; `phases={Br₂:gas}` → C's Br₂ node rolls up UNFAVORABLE → `[X, C]`. This proves the
   reorder is real over the **multi-node convergent rollup**, not an artifact of a linear-shaped single-step fixture.

Both flips ride the sourced **+161.65 kJ** Br–Br dissociation (the R26 DOW-thermo CODATA add) reached through the DAG
feasibility fold — orders of magnitude above any thermochemical noise, a real robust reorder, not a knife-edge.

### No rank-vs-dossier divergence — the load-bearing soundness property

`of_dag(dag_Br₂, box)` (phase-blind) carries `feasibility_verdict=UNKNOWN`; `of_dag(dag_Br₂, box, phases={Br₂:gas})`
carries `UNFAVORABLE` — the SAME verdict the ranker used. So a dossier's feasibility verdict agrees with the rank that
produced it **iff both read the same declaration**, which the seam guarantees. Pinned by
`test_of_dag_reprojects_the_declared_phase_no_divergence` and `test_ranked_dag_dossiers_seam_moves_rank_and_dossier_together`.

## Boundaries (deliberate, documented so nobody re-walks them)

### 1. The status is phase-INVARIANT — so verified-admission stays sound

A phase moves only the ranking-only feasibility verdict; it NEVER changes a section-11 `fit_status`
(FITS/EXCLUDED/UNKNOWN), exactly as DAG-THERMO-01 guarantees the thermo verdicts never touch status. Pinned by
`test_phase_never_changes_the_section11_status`.

### 2. The equilibrium axis stays phase-blind — the R37 precedent

`equilibrium_of_step` has no `phases` param; the rollup threads only feasibility, exactly as R37 made only feasibility
phase-aware on the linear side. A multiphase species therefore fail-closes its **equilibrium extent** to UNKNOWN even
when a phase is declared for feasibility — a sound refusal (never a wrong-phase K), not a wrong answer. **Unlock:** a
follow-up brick that threads `phases` through `equilibrium_of_step` (a new capability, its own scope decision — shared
with the linear-side equilibrium follow-up).

### 3. `_run_recompile` passes no phases — at parity with the linear side

The compile request carries no phase field, so `_run_recompile`'s DAG-mode path calls `ranked_dag_dossiers(_dags, _box)`
with no phases — exactly as its linear `rank_routes(routes, box=…, losses=…)` call passes none. Phase declaration is
today a DIRECT-CALLER capability (the seam), not a request field. This is why the verified-admission re-projection
(`_check_verified_admission`, `of_dag(dag, box)` phase-blind on load) stays consistent: production is phase-blind there
too, so a FITS DAG re-derives the identical summary. **Unlock (the next brick):** a request-level phase declaration,
which would additionally need `phases` carried into the replay payload and the verified-admission re-projection so a
phase-declared FITS DAG re-derives against its declared phase — a strictly larger soundness surface, correctly deferred.

### 4. A phase-declared dossier fails verified-admission — FAIL-CLOSED, at R43 parity (evil-morty/dalembert R44)

The verified-admission re-projection (`_check_verified_admission`) reconstructs a DAG from its `replay_payload` and
recomputes `of_dag(dag, box)` **phase-blind** (the payload carries the steps, not the phase declaration), requiring
`resummary == dossier`. So a phase-DECLARED FITS dossier — one a DIRECT caller produced via the public
`ranked_dag_dossiers` seam with a non-None `phases` — does NOT equal its phase-blind re-projection (its
`feasibility_verdict` differs, e.g. UNFAVORABLE vs UNKNOWN) and is **REFUSED** on a `require_verified_admission`
round-trip.

This is a deliberate, bounded limitation, not a soundness hole:
- **FAIL-CLOSED.** It is a false-REJECT, never a false-ACCEPT. A phase can only ever move the ranking-only
  feasibility verdict, never a section-11 `fit_status` (Boundary 1), so a phase declaration can never turn an
  EXCLUDED route into an admitted FITS one — verified-admission can only ever *refuse* a genuine phase-declared
  dossier, never *admit* a forged one. Pinned by
  `test_verified_admission_refuses_a_phase_declared_dossier_fail_closed`.
- **At exact R43 parity.** The linear side has the identical behaviour: `_check_verified_admission` re-projects
  `rank_routes` without phases, so a phase-declared FITS *route* dossier also fails closed. R44 extends the same
  posture to DAGs; it introduces no new asymmetry. (Tracked debt: a linear-side pin of the same fail-closed fact.)
- **Unreachable from production.** `_run_recompile` passes no phases (Boundary 3), so no shipped path emits a
  phase-declared dossier into a verified-admission round-trip.

**Unlock (same brick as Boundary 3):** the request-level phase field would carry `phases` into the replay payload
and the on-load re-projection, closing this for BOTH the linear and DAG sides at once — the correct place for the
larger serialization/digest surface, built where a production consumer finally exists.

## Why this is the sound scope, not half a job

The R43 defer's stated unlock ("a service API carrying a phase declaration into both `rank_dags` and `of_dag`") is now
built and exercised by a real forcing consumer whose rank order flips on the declared phase — single-step AND
convergent — with the dossier re-projection proven consistent. The residual (a request-level phase field + its
replay/verified-admission carry) has a named unlock and a stated reason. This is the repo's standard verified-defer
discipline (R32/R36/R38/R43): thread the half that is soundly threadable now, defer the half that would enlarge the
soundness surface, each with the reason committed.
