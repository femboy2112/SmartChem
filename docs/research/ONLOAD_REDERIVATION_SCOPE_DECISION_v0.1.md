# On-load re-derivation of composability + physical — scope decision (ROADMAP queue item 2)

> Status: **DECIDED, build-ready** (ROUND 19). This resolves the "scope decision" gate the roadmap attached to
> item 2, and measures the build so it can be executed cleanly in a dedicated round rather than rushed into the
> central response module. No code shipped for item 2 in ROUND 19 (items 1, 2b, 3 did); this is the decision that
> unblocks it.

## The problem

`CompilationResponse.__post_init__` re-derives, on load, only the **process** component of each route/DAG's
combined section-11 `fit_status` (PROCESS-ADMIT-01 for linear, DAG-BENCH-01 for convergent — `service.py:1294`,
`service.py:1357`). The **composability** (E1) and **physical box** (reagent/equipment/hazard) components ride as
free-text `exclusions`/`gaps`. So a route that is non-`FITS` for a composability or physical reason can be
**bare-relabeled to `FITS`** and admitted on load, unless a consumer opts into the COMBINED-VERDICT-AUTH HMAC. Item 2
closes that free-text trust boundary structurally (no shared key needed), the same way PROCESS-ADMIT-01 already does
for the process axis.

## Why it needs a decision (not a mechanical add)

Re-deriving those two components on load needs inputs the **thin projection deliberately omits**
(`RankedRouteSummary`/`RankedDAGSummary` carry only identity-relevant scalars + `process_requirements`):

- `verify_composability(route, stability)` (`composability.py:388`) reads `route.steps[k].target` (the intermediate
  `Molecule`) and the **full** `ConditionEnvelope` of each step (temperature via `_temperature_union`), not just
  `.process`.
- `_step_box_check` (`drafter.py:236`) + `equipment_for_step` (`equipment.py:206`) read `step.reactants` and
  `step.products` (available-reagent + hazard/equipment lookup).
- Reconstructing an `ExperimentStep` to re-run either is **not partial-able**: `ExperimentStep.__post_init__`
  (`step.py:92`) builds a real `Reaction(Config.of(*reactants), Config.of(*products))` conservation certificate and
  **refuses** a non-conserving step, so a reconstruction must carry a complete, valid `(reactants, products, reagents,
  target, envelope)` per step.

That is a **wider, denser per-step payload** than the thin projection's design intent ("without dragging the full
ExperimentRoute/thermo object graph into the response"). Fattening it is a real reversal of a deliberate choice, and it
raises one load-bearing question.

## The fork: does the thick evidence fold into `result_digest`?

- **Fold IN** (like `process_requirements`, `service.py:928`): tampering with the evidence becomes a detectable
  identity change. **But** it makes every route/DAG identity denser and, critically, **changes every existing route
  digest** (a huge golden blast radius and a real change to what "route identity" means).
- **Ride OUTSIDE** (like `provider_snapshots`/`parse_receipt_summary`, `service.py:1179` — "dated data, not search
  identity"): existing digests stay byte-stable.

### Decision: **ride OUTSIDE the digest (digest-excluded), close via a load-time coherence check.**

Carry the thick per-step re-derivation payload as an **opt-in, `compare=False`** field on both summaries, and add a
load-time coherence check that **re-derives** composability + physical from it and **compares to the claimed verdicts**
(`composability_verdict`, the physical `exclusions`/`gaps` — which ARE folded into `result_digest`), raising on
incoherence. This mirrors PROCESS-ADMIT-01's *check* shape exactly.

**Why this is protection-equivalent for the re-derivation purpose:**
- A tamperer who edits the thick payload so it re-derives to a *different* verdict than the claimed (digest-protected)
  one is **caught by the coherence check** (mismatch → raise).
- A tamperer who edits *both* the thick payload *and* the claimed verdict changes `result_digest` → the existing
  key-holding-forger residual, closed only by the opt-in producer signature — **unchanged by item 2**, exactly as
  PROCESS-ADMIT-01 leaves it.
- So folding into the digest buys no additional protection *for this purpose* while costing every existing identity.
  The `compare=False` + coherence-check design is the minimal-blast, protection-equivalent choice — and it is the same
  pattern ROUND 19's item 2b used for `serial_holds` (digest-excluded disclosure, digests byte-stable).

Boundary preserved: even after item 2, "the evidence is not cryptographically bound to the structure" residual stands
and still needs the HMAC to close fully — item 2 is a *structural* closure that complements, never replaces, the
authentication layer.

## Measured build (why it is its own round, an L)

1. **New serializers** (none exist in the payload layer today): `_molecule_to_payload`/`_from_payload` and a **full**
   `_condition_envelope_to_payload`/`_from_payload` (10 fields: temperature/pressure/duration `Interval`s, medium,
   catalysts, applied_field, status, provenance, source, process).
2. **A thick per-step payload** `(reactants, products, reagents, target, envelope)` carried opt-in + `compare=False` on
   `RankedRouteSummary` and `RankedDAGSummary`.
3. **Reconstruction** of conservation-certified `ExperimentStep`/`ExperimentRoute` from the thick payload (must pass
   `ExperimentStep.__post_init__`).
4. **Re-derivation coherence checks** — `_check_composability_admission_coherence` + `_check_physical_admission_coherence`,
   each for **linear and DAG**, enforcing the same one-direction lower-bound PROCESS-ADMIT-01 uses (an honest combined
   status is at least as severe as any component), gated on the thick payload being present (zero overhead otherwise).
5. **Schema bumps** (`RANKED_ROUTE_SUMMARY_SCHEMA`, `RANKED_DAG_SUMMARY_SCHEMA`, the descriptor) + **golden regen**
   (`response_schema.json` field docs + `recompile_routes_found.json` if it carries a populated dossier).
6. **Tests** + an evil-morty pass (the obvious attack: a thick payload that re-derives coherent-but-lenient, and the
   reconstruction refusing a non-conserving forged step).

This is larger than ROUND 19's items 1, 2b, and 3 combined and touches the module that gates every compile, so it is
scheduled as its own round rather than rushed. (Optional first slice, if a smaller landing is wanted: the two
serializers + reconstruction + the **composability** coherence check only, deferring the physical box — but note both
axes ride on the same reconstruction, so the marginal cost of the second is small once the first exists.)
