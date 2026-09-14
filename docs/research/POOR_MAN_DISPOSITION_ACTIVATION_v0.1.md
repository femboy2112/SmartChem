# Poor-man ingenuity — activating R59's REAL_BUT_HARD disposition tier (DISPOSITION-ACTIVATE-01)

**Round:** poor-man arch, R59 follow-on · **Status:** SHIP · **Probe:** `experiments/poor_man_disposition_activation_probe.py` (FROZEN_HASH `5e992095d053c1617b341a83f22cc306a8caa33584c40983c2a837d1cece5f50`) · **Tests:** `tests/test_poor_man_disposition_activation.py`

## The problem: R59's REAL_BUT_HARD tier was *structurally* unpopulated

R59 built a 3-tier `Disposition` (`CLEAN < REAL_BUT_HARD < NOT_A_REACTION`) on two disjoint `CostVector` channels and shipped it **correct-ahead-of-data** — the `REAL_BUT_HARD` tier never fired. This round asked (per the user's steer) whether the disposition could be made to **drop out of the categorical structure** rather than hand-hacked, and — before building anything — verified the pillars with a 4-bearing read-only workflow.

**The verified finding was not what the framing assumed.** Two things, both confirmed against the code:

1. **The disposition already drops out of the math.** `CostVector.disposition` is *literally* the join(max) homomorphism over per-step functorial tiers (proven identical across 64 routes by the workflow). Adding an `open_core` decoration object to "re-derive" it would be a **zero-call-sites mirror** — the forbidden failure mode (`compile_open` is test-only; the decoration slot is off the live compile path). **No new categorical machinery is warranted.**

2. **The tier was unpopulated for a *structural* reason, not a missing calculation.** `service._affordability_frontier` already wires a real-but-hard source — a section-11 bench **EXCLUSION** becomes `hard_blockers` (→ `REAL_BUT_HARD`, `service.py:2019`). But whenever a process box is active (the *only* way to produce an `EXCLUDED` route), `run_compilation` rebuilt the frontier from **FITS-only** routes (a deliberate soundness invariant, `service.py:1362`, `:1856`). So every `EXCLUDED` route was filtered out **before** it reached the frontier — the wiring was effectively dead code, and its own docstring ("ranked above a fiction") contradicted the gate that starved it.

The FITS-only gate's *reason* is the deserialization trust boundary: a `FITS` verdict is re-derived on load (PROCESS-ADMIT-01), but `EXCLUDED` carried only untrusted free-text.

## The fix (DISPOSITION-ACTIVATE-01): lift the gate for the *authenticated* process axis

Admit a route to the process-constrained affordability frontier iff it is **FITS OR its RE-DERIVED process status is EXCLUDED** — ranked below runnable `CLEAN` routes, above `NOT_A_REACTION` fictions.

This is **sound** because the process exclusion is re-derived from the route's carried per-step `process_requirements` via `evaluate_process_requirements` — the *same* authority PROCESS-ADMIT-01 re-checks on load — so a `REAL_BUT_HARD` route's hardness is trust-boundary-safe. The physical/composability exclusion axes stay diagnostics-only (not re-derivable from the thin projection → **not** admitted). It dissolves the gate's own stated reason for exactly the axis where it no longer applies.

Edits (all in `smartchem/service.py`, additive — **no schema bump**; the `AffordabilityFrontierEntry` shape is unchanged from R59):
- `run_compilation` frontier admission: `FITS` → `FITS ∪ re-derived-process-EXCLUDED`, passing the `ProcessBounds` to the frontier builder.
- `_affordability_frontier`: source channel-1 `hard_blockers` from the **re-derived** process exclusions (authenticated), not the free-text `summary.exclusions`, when a process box is active.
- the load-time frontier invariant (`__post_init__`): widened from `⊆ admissible_route_digests` (FITS-only) to `⊆ _frontier_admissible_route_digests` (`{FITS ∪ re-derived-process-EXCLUDED}`), a new property re-derived on load.
- `admissible_route_digests` (bench-readiness, FITS-only) is **unchanged** — a `REAL_BUT_HARD` route is *shown*, never claimed to fit.

## What it activates — and what it honestly does NOT

**Flagship (live-verified):** isopentyl alcohol + acetic acid → isopentyl acetate on a poor-man kitchen bench with **no reflux condenser** → the recognized Fischer esterification is process-EXCLUDED and now appears on the frontier at `REAL_BUT_HARD` (*"required equipment unavailable: reflux condenser, heating mantle, distillation apparatus…"*). Before the lift, this frontier was **empty** (FITS-only gate). The tier goes from *structurally impossible* to **populated** — the poor man now sees "this real route exists, your bench can't run it" instead of nothing.

**The honest headline — the RANKING INVERSION stays data-dark.** R59's *distinctive* effect (`REAL_BUT_HARD` strictly dominating a **co-occurring** `NOT_A_REACTION`, differing from the old 2-tier frontier) needs both tiers on one frontier. It cannot happen:
- **Under** process bounds, derived fictions carry no process record → they fit `UNKNOWN` → they are (correctly) not admitted. A fiction and a `REAL_BUT_HARD` route cannot co-occur.
- **Without** process bounds, there is no `REAL_BUT_HARD` source at all.

The catch-22: the inversion is reachable **only** through a *non-process* real-but-hard source — a declared metal catalyst — which is the deferred **escape-#7** wall (no metal-catalyzed reaction class is both derivable-by-capped-scission and recognized; C–C coupling collides). So this round delivers the tier's **visibility/reachability**, honestly deferring the ranking inversion, exactly like R59's correct-ahead-of-data posture. The probe **asserts** the inversion is dark, so it flips loudly if a co-occurrence ever becomes reachable.

## Soundness boundary (verified, carried as known debt)

The workflow surfaced a **pre-existing** latent hole (R58/R59, *not* introduced here): R59's disposition is forgeable on a tampered **serialized** response — `reaction_center` is `compare=False` (digest-invisible) and the frontier `CostVector` is excluded from `result_digest`. This round does **not** worsen it: a tamperer already reaches `CLEAN` (the *best* tier), so `REAL_BUT_HARD` grants no new capability, and the widened frontier invariant is authenticated on the process axis (a non-controlling forger cannot admit a route without process evidence that re-derives to `FITS`/`EXCLUDED`). Closing the forgery hole (digest-binding the `reaction_center` + a load-time frontier-disposition coherence check) is a **separate**, schema-breaking round that reverses a deliberate R58 decision — deliberately **not** bundled here. It is the clear next step if load-tamper-resistance of the disposition is required.
