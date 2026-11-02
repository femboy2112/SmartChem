# Bounded typed-event route search — Phase IV (1.4) findings (2026-10-30)

**Issues:** #104 (W1 rank-descent redesign), #123 (lateral-hop route search), #125 (typed event classes + arity).
**Deliverable:** an opt-in, finite, **sound** bounded typed-event route search that makes the oracle-vouched
[3,3]-sigmatropic / electrocyclic families **reachable** from retrosynthesis, with a *separate* well-founded
termination proof — exactly the V1_5 program's 1.4 scope (*"an opt-in, finite, SOUND lateral search; fusion into
`search_routes` stays deferred"*).
**Module:** `smartchem/experiment/event_search.py`. **Base:** released `main` `9e8fa5f` (depends only on released
modules — `routes`, `lateral_rewrite`, `transform_provider`, `step`; nothing from the P2/#112 or P3/#119 branches).

---

## 1. The obstruction, read across the three issues

`search_routes` (`smartchem/experiment/routes.py`) is a bounded retrosynthesis whose **only** event is a capped
scission, and whose termination rests on invariant **W1**: every precursor has *strictly fewer atoms* than the
target (`structure_descent.py` enforces `len(product.atoms) < len(reactant.atoms)`). Two independent walls follow:

- **#104 — the rank wall.** A rank-FLAT isomerization (a [3,3] shift, an electrocyclization) preserves atom count,
  so W1 is unsatisfiable for it; forcing one through the decompiler calls `forget()`, which a `LateralRewriteEdge`
  refuses *by design*. The sigmatropic/electrocyclic families are therefore oracle-**vouched**
  (`smartchem/lateral_rewrite.py`) yet **unreachable** from the route search (#123 sub-gap a).
- **#125 — the arity wall.** Even with the rank relaxed, a `CappedScission` structurally requires ≥2 disconnected
  product components **and** a consumed mediator, so it can represent neither a connected 1→1 rearrangement nor an
  intramolecular conversion that keeps its skeleton together and expels a coproduct. Relaxing the rank measure
  alone does **not** close this — it is an independent *representability* obstruction.

The codebase anticipated this: `routes.py:~549` (the ISSUE-124 cyclic-ancestor guard) is documented as *"the safety
net that keeps a future rank-flat/reversible provider (#104/#123) sound … a NO-OP today"*. This work is that future.

## 2. The typed-event taxonomy (#125 acceptance clause 1 — scission NOT overloaded)

`EventType` with a fail-closed structural classifier `classify_event(step)` (arity by **multiplicity**, not distinct
identity — a scission into two identical fragments, `AcOH + AcOH → Ac₂O + H₂O`, is still arity-2):

| class | shape | status |
|---|---|---|
| `SCISSION` | assembled from ≥2 fragment molecules; rank-descending | wired (the inherited W1 grammar) |
| `CONNECTED_LATERAL` | one connected precursor, **same** atom count, no coproduct ([3,3] / electrocyclic) | **wired** (the forcing consumers) |
| `INTRAMOLECULAR_COPRODUCT` | one connected principal precursor **larger** than the target, expelling a conserved coproduct | **DEFERRED** (defined, no producer) |

The strict scission contract is untouched; the laterals are a separate typed class, not an overloaded scission.

## 3. The termination proof (#125 clause 4; the #104 "well-founded non-atom-count measure")

Termination is **overdetermined** — two independent well-founded measures each strictly decrease on every recursion
edge. Being precise about *which one the code operatively enforces* (d'Alembert's correction, verified; the prose
below matches what executes):

- **The operative bound (what the recursion enforces): `max_depth − depth`.** *Every* recursion edge — SCISSION and
  CONNECTED_LATERAL alike — recurses through `_branch` at `depth + 1` (**a lateral hop costs a depth increment, not
  only a hop**), and `routes_making` returns at `depth > max_depth`. So `max_depth − depth` strictly decreases on
  every edge and bounds the recursion depth; with finite branching per node (`cut_budget` bounds scission
  candidates, `lateral_match_budget` × the family set bounds lateral candidates), the whole tree is finite. This is
  the guard that halts the search in practice.
- **The independent chemical certificate: the lexicographic pair `M(t, hops_left) = (len(t.atoms), hops_left)` on
  ℕ×ℕ.** A SCISSION edge recurses onto a precursor with `len(atoms) < len(t.atoms)` (W1) at the same `hops_left`
  (first component drops); a CONNECTED_LATERAL edge recurses onto an isomer of the same atom count with
  `hops_left − 1` (first component unchanged, second drops). `M` strictly decreases on every edge, so **the search
  would terminate even with `max_depth` unbounded** — a single monotone atom-count measure could not admit a
  rank-flat hop, but this lexicographic pair does, *without weakening* W1 for scission. `M` is what makes
  `lateral_hops` a meaningful *completeness* parameter rather than a termination crutch.

**Consequence (stated, not hidden):** because a lateral hop consumes a depth increment as well as a hop, a route of
k scissions plus a lateral whose *combined* recursion depth exceeds `max_depth` is unreachable even though `M` alone
would admit it — handled honestly (`depth_truncated` increments, receipt `complete == False`; verified: paracetamol
at `max_depth=1,2` is incomplete, `max_depth=3≡4` complete; a ring/no-stock target with 2 hops budgeted but
`max_depth=1` is `depth_truncated`). The ISSUE-124 ancestor guard additionally **cuts** a rank-flat inverse cycle
`A→B→A` outright (belt and suspenders — though `M` already kills it, since every lateral hop spends a hop).

The executable form is `tests/test_event_search_123.py::test_every_returned_route_is_measure_monotone_and_hop_bounded`
(every returned route is monotone under `M` and uses ≤ `lateral_hops` lateral steps).

> **Adversary note (d'Alembert, structure-theorem refutation, run separately from acceptance):** SURVIVED — could
> not kill termination; attacked lateral atom-count invariance across all 6 families (drift 0), W1 for scission
> (0 violations on live paracetamol routes), guard-reliance (the measure terminates a guard-less inverse cycle),
> and frontier blow-up (saturates, no exponential regime found). Its one finding was this attribution correction,
> now applied. Boundary: only `DEFAULT_TRANSFORM_REGISTRY` — a caller-supplied `LINEAR_ROUTE` provider that emits a
> non-W1-checked "scission" would break the measure's scission leg; all shipped scission transforms hard-enforce
> `len(product) < len(reactant)` (`structure_descent.py`), so this is a registry-contract assumption, not a bug.

## 4. The forcing consumer (#123 sub-gap a, discharged)

Target 1,3-cyclohexadiene (`C1=CCCC=C1`), with its rank-flat open isomer 1,3,5-hexatriene (`C=CC=CC=C`) on hand:

- `search_routes` → **0 routes** (the ring←open step is rank-flat; no W1 scission can reach it);
- `search_event_routes(…, lateral_hops=1)` → **1 route**, a single `CONNECTED_LATERAL` step the oracle vouches as
  *"electrocyclization 6pi"* — the [3,3]/electrocyclic family is now reachable from retrosynthesis.

## 5. Opt-in / replay integrity (#125 clause 4; V1_5 1.4 scope)

`search_routes` and its frozen `RouteSearchReceipt` schema are **not touched**. `search_event_routes` is a separate
entry point with its own `EventRouteSearchReceipt` (not part of the 1.0 replay surface). A `CONNECTED_LATERAL` step
is assembled via `ExperimentStep.from_transform(edge, envelope=None)` — the **`forget()`-free** path (#123) — so a
lateral edge never enters the decompiler/conditions path. **`lateral_hops=0` reproduces exactly the pure-scission
route set of `search_routes`** (tested on paracetamol via amino-phenol + Ac₂O: identical digests; `lateral_hops=1`
is a superset).

## 6. The control battery (#125 clause 3 + the plan's required list)

All in `tests/test_event_search_123.py` (19 tests, ~9 s) + the frozen-hash probe `experiments/event_search_probe.py`
(drift-guarded by `tests/test_event_search_probe.py`):

inverse pairs · rank-flat cycles terminate · identity-only fake rewrites yield no event (benzene) ·
ancestor-as-stock (genuine termination when the isomer *is* stock; refusal when it is a non-stock ancestor) ·
nonconserving steps refused at construction (so none can enter a route) · repeated-state dedup by route digest ·
genuine stock termination · intramolecular event arity (the 3-way classifier, fail-closed) · budget exhaustion →
honest `complete=False` · the `forget()`-free boundary preserved.

**Adversarial hardening (run *separately* from acceptance).**

- **d'Alembert (structure-theorem refutation): SURVIVED** — could not kill termination. One finding, a proof-
  *attribution* defect (the docstring led with the lexicographic measure as the reason the search halts, when the
  operative bound the code enforces is `max_depth − depth`); applied as a prose correction (§3), no code change.
- **evil-morty (directed exploit): no verified kill** on termination, no-false-reach (CONNECTED_LATERAL steps are
  oracle-vouched *by construction* — the search builds the edge via `guarded_isomer_edges`, whose `__post_init__`
  runs the same `_reactant_rewrites_to` the oracle's `_sigmatropic_rearrangement` re-runs), hops=0 parity, or the
  `forget()`-free boundary. **One real latent honesty hole found and FIXED:** the hops-exhausted completeness probe
  discarded the completeness flag from `guarded_isomer_edges`, so a `hops_left==0` node whose lateral enumeration is
  budget-truncated *to zero edges* could record no truncation and let `receipt.complete` over-claim. Today the
  window is unreachable (an accident of enumeration cost — a valid edge is found before the enumeration completes —
  keeps it honest, and no shipped lateral family has a 2-hop chain to even reach such a node), so it is a *latent*
  Conjectured hole, not a live false-COMPLETE. The fix (the live-hop branch already honored the flag; the probe now
  does too — a truncated probe flags `lateral_match_truncated` even when it found nothing) removes the dependence on
  that unasserted accident, per "a fail-closed guarantee must hold at every fallback layer." Residual boundaries
  evil-morty flagged and left as-is (documented, not bugs): a charged `target` raises `ScissionError` raw from the
  generator (parity with `search_routes`, a loud model-boundary refusal, not a silent wrong answer); and
  `candidates_emitted` is not bounded by `max_routes` when many histories collapse to one digest (termination still
  guaranteed by the measure + ancestor guard; not triggerable with the low-branching shipped families).

## 7. Deferred **with evidence**

- **`INTRAMOLECULAR_COPRODUCT` (event type 3) — representation deferred to 2.0.** The category is *defined* and the
  classifier *recognizes* its shape (a hand-built lactonization `4-hydroxybutanoic acid → γ-butyrolactone + H₂O`
  classifies correctly), but **no generator emits it**: `CappedScission`'s ≥2-component contract (#125) structurally
  forbids a connected-1→1-with-coproduct event, and no lateral family expels a coproduct. Over the whole paracetamol
  route set, zero type-3 events appear. Wiring a connected-intramolecular-coproduct *generator* (lactone/lactam/
  Dieckmann/intramolecular-aldol) is the 2.0 reaction-event-calculus obligation — the search architecture and the
  termination theory are **ready for it** (the measure extends to `(coproduct_events_left, len(atoms), hops_left)`
  once such a generator exists), but shipping the plumbing now would be machinery with zero producers.
- **Fusion into the default `search_routes`** stays deferred (the V1_5 scope): this is an opt-in sibling, not a
  default-path change.
- **The oxidation / Wittig-carrier / RCM rank-*increasing* cases** (#104's heavier-precursor list) need the type-3
  (coproduct/carrier) representation above; same deferral.

## 8. Performance note (honest bound)

The lateral branch enumerates up to 6 families per node (only when `lateral_hops > 0`; `lateral_hops=0` pays
nothing, matching `search_routes`). On large aromatic substrates the kernel match enumeration is the cost, not the
interleaving — measured: paracetamol at `max_depth=3` is ~15 s for `search_routes` itself, and the lateral addition
is within noise (~13 s). Keep `lateral_hops` modest (default 1); this is a bounded cost, never a hang (the
termination proof guarantees it), and it is the same class of bounded-branching caveat the #114 profile carries.

## 9. Gate

- Targeted: `tests/test_event_search_123.py` (19) + `tests/test_event_search_probe.py` (2) green; ruff clean on the
  four changed files; full OOM-safe suite on the final SHA; hosted CI the independent second gate.
- Adversarial hardening (evil-morty directed + d'Alembert structure-theorem) run **separately** from acceptance.
- **No golden / `semantic_digest` move** (opt-in; no provider registered in the default algebra; `search_routes`
  and its receipt schema untouched). No merge / tag / publish.
