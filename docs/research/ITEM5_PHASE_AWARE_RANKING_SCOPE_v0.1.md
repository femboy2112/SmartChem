# ITEM5-PHASE-RANK-01 — phase-aware public route ranking (the item-5 forcing consumer)

**Round:** R43 (item-5 brick). **Lane:** B·C. **Status:** linear `rank_routes` threaded + forcing consumer built;
DAG ranker phase-threading a documented DEFER (pending-review at time of writing; merge state recorded in the round's
PR). **Evidence:** `experiments/item5_phase_aware_ranking_probe.py` (FROZEN_HASH `34b26e69…d216d17c`, RDKit-free
`validate()`) + `tests/test_item5_phase_aware_ranking.py`.

## The mandate

R37 threaded `phases` through `verify_feasibility` (feasibility.py) but deliberately STOPPED below the public ranking
API, with the reason recorded verbatim (ROADMAP.md item-5 row / R37 boundary note):

> the drafter's public ranking API is deliberately NOT threaded (no dual-phase ranked route exists — the
> zero-call-sites trap); unparks when one does.

This round builds the forcing consumer — a route whose *ranking order* moves on the declared phase — and threads
`phases` up to serve it. The whole lower thermo stack (`verify_feasibility` → `feasibility_of_step` → `resolve_thermo`;
and `route_net_delta_g`) was already phase-aware from R36/R37; the break was purely at the ranking layer.

## What shipped (all additive `phases: dict[Molecule, str] | None = None`, default byte-identical)

`smartchem/experiment/drafter.py`:
- `rank_routes(..., phases=None)` → `fit_routes(..., phases=phases)` → `fit_route(..., phases=phases)` →
  `verify_feasibility(route, thermo=thermo, phases=phases)` (drafter.py:328 — previously phase-blind).

That single thread makes BOTH linear ranking drives phase-aware, because the ranker reads
`RouteFeasibility.net_delta_g_kj`, a property over the per-step results `verify_feasibility` computes:
1. the worst-node feasibility **SIGN** tier (`feas_rank` in `_score_tuple`), and
2. the M2b additive net-ΔG **MAGNITUDE** tier (`_score_tuple`, applied only in the FAVORABLE class).

### The forcing consumer (the sign-tier ranking-ORDER flip) — robust, default thermo

`Br₂ → 2 Br·` (Br₂ dual-phase in the seed) vs the phase-INERT, unsourced `I₂ → 2 I·`. `phases=None` → both
feasibility=UNKNOWN → tie on every tier → discovery order `[Br₂, I₂]`. `phases={Br₂:"gas", Br:"gas"}` → the Br₂ route
resolves to UNFAVORABLE (net ΔG = **+161.65**, the sourced CODATA dissociation) and sinks a tier → order flips to
`[I₂, Br₂]`. **This is the dual-phase ranked route the brick was waiting for.** The flip rides on a **+161.65 kJ**
effect — orders of magnitude above any thermochemical noise — so it is a real, robust reorder, not a knife-edge.

### The magnitude tier is phase-FED too — a plumbing proof, NOT a real-chemistry reorder (adversarial-fold honesty)

`Br₂ + H₂ → 2 HBr` is FAVORABLE in BOTH phases with a phase-dependent net ΔG (gas −109.83, liquid −106.72), so the M2b
additive net-ΔG magnitude tier reads a phase-dependent value — the plumbing reaches it. **But the split is only 3.11
kJ/mol** (exactly Br₂'s ΔG_vap at 298 K), *below* the thermochemical noise floor of the estimates this stack derives.
An earlier draft demonstrated a magnitude-tier *order flip* against a sibling tuned to net −107.98 (a chemically false
`HCl` ΔfH° of −51.0 vs the real −92.31); **dalembert and evil-morty (R43) correctly flagged that flip as a fitting
artifact** — with real `HCl` chemistry there is no rival within the lever, so nothing flips. It was removed. What the
probe now pins is the honest claim: the magnitude tier is *phase-fed* (the net differs by phase, both FAVORABLE); it is
**not** claimed that a real-chemistry ranking reorders on the sub-noise lever. The robust forcing consumer is the SIGN
tier above.

### The phase lever is non-monotone in T — it reverses sign at 331.45 K (adversarial fold)

The phase effect on ΔG is **ΔG_gas − ΔG_liq = −30.91 + 0.093258·T** (kJ/mol), zero at **T = 331.45 K**. Below the
crossover gas is the more favorable phase; above it liquid is (dalembert R43, reproduced: gas favored at 298 K, liquid
favored at 350 K). A caller reaches T through the step `ConditionEnvelope`; `rank_routes` exposes no `temperature_k` of
its own (a named follow-up below). **Consequence for any DIRECTIONAL claim:** "declaring gas floats a Br₂-reactant
route / liquid sinks it" is a **298 K** statement, false above 331.45 K — a hot bromination routinely exceeds it. The
probe pins the sign reversal; the tests pin the 298 K direction only.

`phases=None` (and the no-arg call) is byte-identical to the pre-brick behaviour for every existing caller; a phase
declaration for a species a route does not carry leaves that route's fit untouched (each step filters the dict to its
own species). **Full suite green: 4841 passed / 29 skipped / 1 xfailed** (foreground alphabetical batches per the
box-OOM discipline; +11 vs the 4830 baseline = the new item-5 tests; the 1 xfail is the pre-existing interchange-law
debt, orthogonal). The F1 hardening below (a `feasibility.py` `resolve_thermo` change) is covered by the same green
run.

## Hardening (evil-morty R43) — the fail-closed guarantee now holds at the specific-phase fallback layer

Making `rank_routes` phase-aware armed a latent leak in the phase-resolution guard it now depends on. The R36 guard
(`feasibility.py`, `resolve_thermo`) fail-closed a multiphase species to UNKNOWN only for `phase is None`; a **specific
declared phase the table did not hold** (an untabulated `"solid"`, or a mis-cased `"Gas"`) fell through to the
phase-BLIND Benson estimate — answering a *different* phase than asked and silently reinstating the wrong-phase-ΔG debt
one layer down. Latent on shipped `DEFAULT_THERMO` (Br₂ is the only multiphase species and is Benson-uncoverable, so it
fell to `None` anyway), but it would fabricate a KNOWN ranking verdict for any injected multiphase Benson-coverable
species (an ordinary two-phase solvent) reached through the new public ranker.

**Fixed** ([[a-fail-closed-guarantee-must-hold-at-every-fallback-layer]]): the guard now fires for **any** missed
sourced phase on a multiphase species — `if table.is_multiphase(...): return None` at the point where both the named
and formula-level sourced lookups (with the requested phase) have already missed. A tabulated phase still hits and
returns before the guard; a SINGLE-phase species is not phase-ambiguous, so an untabulated phase still derives (the
legitimate condensed-derive path, e.g. paracetamol, is untouched — `is_multiphase` is False there). Pinned by
`test_fail_closed_guarantee_holds_at_the_specific_phase_layer` + `test_single_phase_species_still_derives_for_an_untabulated_phase` and the probe's `guard_closes_on_untabulated_phase`. This is what makes "rank on the declared phase"
mean *rank on a sourced phase or fail closed*, never *rank on whatever the fallback guessed*.

## Named follow-ups (adversarial folds not built this round, with reasons)

1. **An explicit `temperature_k` on `rank_routes` + the 331.45 K crossover as a first-class boundary** (dalembert). T
   already reaches feasibility via the step `ConditionEnvelope`, so this is a convenience/legibility improvement, not a
   soundness gap; adding a ranker-level `temperature_k` override is its own small scope decision. Until then the
   crossover is documented (above) and pinned by `test_phase_lever_reverses_sign_with_temperature`.
2. **Uncertainty-gate the M2b net-ΔG magnitude tier** (dalembert) — don't let a sub-propagated-uncertainty ΔG delta
   break a ranking tie. This is a **pre-existing M2b property** (the magnitude tier already ranks on raw ΔG magnitude
   without an uncertainty floor, for *any* input, not just phase), so gating it is a separate M2b-hardening round with
   golden churn, out of scope for a phase-threading brick. The robust forcing consumer (the +161.65 kJ SIGN-tier flip)
   is immune to it; the sub-noise magnitude case is explicitly demoted to a plumbing proof above.

## Boundaries (deliberate DEFERS, documented so nobody re-walks them)

### 1. The DAG ranker `rank_dags` does NOT expose `phases` — the ROUND-15 fold, verbatim

`rank_routes` could accept `phases` **soundly** because it RETURNS the scored `RouteFit`s and
`RankedRouteSummary.of_fit` projects THOSE (phase-aware) fits — rank and dossier cannot disagree. `rank_dags` instead
returns the DAGs, which `RankedDAGSummary.of_dag` **RE-PROJECTS under the default tables** (no phases). Exposing
`phases` on `rank_dags` alone would rank under a declared phase while every dossier projected the phase-blind
(fail-closed-UNKNOWN) verdict — the exact latent divergence the ROUND-15 fold prevents ("`of_dag` takes none either,
so accepting a table here would let a caller rank under one table while the dossiers project under the defaults — a
latent divergence with no consumer … BOTH move together or neither does"). So the DAG ranker unparks for phases only
when the service `of_dag` projection carries them too; until then the DAG ranking CALL PATH stays phase-blind:
`rank_dags` does not FORWARD `phases` into `route_net_delta_g` (which already accepts one — `functorial_physics.py:55` —
but the `rank_dags` call passes none) nor into `dag_bench_fit` / `dag_thermo_rollup` (which carry no `phases` param at
all), so no phase reaches the DAG feasibility verdicts or the additive drive. No phase param is grown where no consumer
can use it soundly (the zero-call-sites discipline — the SAME lesson this brick just discharged for the linear side).
**Unlock:** a service API that carries a phase declaration into both `rank_dags` and `of_dag`.

### 2. The equilibrium axis stays phase-blind — the R37 precedent

`verify_equilibrium` has no `phases` parameter; this brick threads only feasibility, exactly as R37 made only
feasibility phase-aware. A multiphase species therefore fail-closes its **equilibrium extent** to UNKNOWN even when a
phase is declared for feasibility — a sound refusal (never a wrong-phase K), not a wrong answer. **Unlock:** a
follow-up brick that threads `phases` through `verify_equilibrium` → `equilibrium_of_step` (a new capability, its own
scope decision).

## Tracked observation (birdperson) — the linear consistency is convention-held, not guarded

The linear rank-vs-dossier consistency holds because `RankedRouteSummary.of_fit` *consumes* the phase-aware
`RouteFit` `rank_routes` returns, rather than re-deriving it. That is a property of the current call graph, not an
enforced guard: a future caller that took a phase-ranked `RouteFit` and projected it through some *other* path that
re-derived phase-blind would reintroduce exactly the divergence the DAG defer avoids. Not exploited today (`of_fit` is
the projection seam, and it consumes), but it is the [[a-fail-closed-guarantee-must-hold-at-every-fallback-layer]]
shape — a guarantee resting on incidental structure. If a second linear projection seam appears, it needs its own
consume-the-fit discipline or an explicit guard. Carried, not silent.

## Why this is the sound scope, not half a job

Threading the half that is soundly threadable now (the linear ranker, consistent end-to-end via `of_fit`) and
deferring the half that would reintroduce a known hazard (the DAG ranker, per the ROUND-15 `of_dag` fold) — each with
the reason committed — is the repo's standard verified-defer discipline (R32/R36/R38). The item-5 remaining brick is
discharged: the drafter's public LINEAR ranking API is phase-aware, the forcing consumer exists, and the DAG residual
has a named unlock.
