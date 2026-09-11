# CATALYST-OBTAIN-01 — the poor man's kitchen can see its catalysts (R51, PR)

> **Status: SHIPPED.** A sound catalyst-obtainability gate for the poor-man capability model, built after a
> four-bearing adversarial DESIGN gate. Closes the catalyst-availability half of R50's KILL-2 (the capability
> stack was blind to catalysis); the ingenuity *reward* stays deferred on R50's KILL-1 (untouched).

## The user's ask and the reading

> "keep on blasting, lets give the poor man more capability"

Read as: build out the kitchen **capability model** in the sound direction R50 pointed at. R50 (the second verified
defer of the poor-man ingenuity reward) named the exact organ the poor man was missing — **the capability stack is
blind to catalysis** (KILL-2). A reaction's declared catalyst was checked by *no* gate, so a route needing an
un-buyable metal catalyst (Ru/Ir/Pd) read as poor-man-reachable. This PR builds that organ. It is sound because it
only ever gains power to **EXCLUDE** (a catalyst the kitchen cannot get) or stay **NEUTRAL** (a positively-recognized
kitchen catalyst) — never to VOUCH. That is the safe direction: `false-VOUCH ≫ false-UNRECOGNIZED`.

## The gap (R50 KILL-2, re-verified in live source)

- `ProcessBounds` (`process_constraints.py`) gates time / attention / agitation / equipment — **no catalyst field, no
  temperature ceiling**.
- `equipment.py` names no catalyst as a gate (it even had a dead `or envelope.catalysts` disjunct that appended
  nothing — removed here).
- The affordability model (`affordability.py` `basket_cost_vector`, wired at `service.py:_affordability_frontier`)
  prices only the **consumed leaves** a route buys (`route.leaf_inputs`). A catalyst is *regenerated*, so it is never
  a purchased leaf and never reaches the cost vector.
- `ConditionEnvelope.catalysts` is a real structured field, but it was read only for serialization
  (`service.py:2508`) and accounting (`accounting.py:181`) — never for obtainability.
- Every `SEED_CONDITIONS` record carried `catalysts=()` (the catalyst was buried in free-text `medium`).

So the gap was triple-confirmed against real bytes: a declared catalyst was invisible to every gate.

## The four-bearing DESIGN gate (run BEFORE wiring)

Per the R48/R49/R50 discipline, a soundness-relevant capability that can EXCLUDE real routes earns an adversarial
design gate before a line is wired. Unlike R49/R50 (which the gate *killed*), this design **survived — with folds**.

| Bearing | Verdict | The load-bearing fold it forced |
|---|---|---|
| **dalembert** (soundness refutation) | KILLED-with-repair | **KILL-1 — the false-VOUCH-by-omission.** The naive "UNKNOWN → not a blocker" is fail-OPEN: the eponymous-metal class (Wilkinson's, Crabtree's, Grubbs II, Lindlar…) has no element token and isn't in a small table → classified `None` → not blocked → sits on the frontier as catalyst-clean *next to* a genuinely-clean route (a false distinction, an affirmative false signal). **Repair (adopted whole): the burden-of-proof flip** — a *declared* catalyst passes ONLY if positively classified kitchen-obtainable; a declared-but-unrecognized catalyst BLOCKS. Also **KILL-2 (latent): the metal guard** must run before any kitchen-tier return, over a closed set of catalytic metals. |
| **evil-morty** (wiring / byte-identity) | sound-with-gaps | The substring/element-token scan is a false-EXCLUDE cannon (`"palladium-free"`→blocked; `"os"` in *phosphoric*) — **dropped entirely**. The R50 probe's tripwire flips on the seed population — **must be retired deliberately in-PR** (done). Frontier interaction (G6 dominance + honest-emptiness gate) verified **sound**. Digest churn from the seed population lands in **empty field** (zero golden hits). |
| **birdperson** (architecture) | SOUND-WITH-FOLDS | Wanted it first-class in the combined `fit_status`, both modes; flagged reusing `Availability` as a verdict and the fuzzy scan as a smell. See the adjudication below. |
| **daniel** (empirical) | data | Battery: eponymous metals caught by the curated table; `RuCl3`→None and `"palladium-free"`→false-positive both *dissolved* by the flip + dropping the scan. Census: **45 registered structures, 29 routes, 59 steps → 0 carry any catalyst today** (the EXCLUDE path is a guard ahead of its data). Golden impact: **exactly the R50 probe flips**, nothing else. Non-vacuity: the isopentyl route carries `("sulfuric acid",)` end-to-end → HARDWARE → correctly not blocked. |

## The architectural adjudication — why the affordability frontier, not the general `fit_status`

Birdperson's *instinct* (surface it first-class, reach both modes) is right; his proposed *mechanism* (fold into the
combined `fit_status`) is subtly wrong, and this is recorded as a deliberate disagreement-with-a-bearing:

- `fit_status` (composability + physical box + process, `drafter.py:fit_route`/`dag_bench_fit`) serves an **arbitrary
  bench box** — a real, well-equipped lab may own palladium. An *unconditional* catalyst exclusion there would
  falsely EXCLUDE a metal catalyst for a lab. A correct fold would have to be **box-gated** on a kitchen constraint —
  new surface with no consumer today.
- The **affordability frontier** (§10.4) is the *unconditionally poor-man* obtainability model. Catalyst
  obtainability belongs there exactly as `access_difficulty` (the consumed-leaf obtainability axis) does. A
  non-kitchen catalyst becomes a §10.4 **hard blocker** (G6: a hard blocker dominates cost), so a route needing an
  un-buyable catalyst sinks on the poor-man frontier even when it FITS the bench box. evil-morty verified this
  channel sound.

So the affordability frontier is the semantically-correct poor-man home; keeping the general `fit_status`
catalyst-agnostic is *correct*, not a gap. The box-gated `fit_status` fold and DAG-mode reach are **named
follow-ups**, not gold-plating bolted on unasked.

## What shipped

1. **`smartchem/experiment/catalyst_availability.py`** — the classifier + gate:
   - `catalyst_availability(name) -> Availability | None`: exact case-normalized lookup against the grounded
     commodity catalog → a grounded **transition/heavy/precious-metal guard** over the real composition (before any
     kitchen tier is returned) → a small curated table of common named catalysts (kitchen acids/bases + industrial
     metal catalysts, keyed by exact name/alias) → **fail-closed `None`**. No fuzzy substring scan.
   - `route_catalyst_blockers(route)`: the **burden-of-proof flip** — a declared catalyst blocks unless positively
     kitchen-obtainable; an undeclared catalyst is genuine silence.
   - `NON_KITCHEN_METALS`: the d-block + platinum-group + coinage + heavy + f-block metals (periodic-table reality),
     **excluding the s-block** so kitchen base salts (NaOH/K₂CO₃) are never false-excluded.
2. **Sourced seed** (`decompiler_conditions.py`): isopentyl acetate → `catalysts=("sulfuric acid",)`, a quote-read of
   its sourced `conc. H2SO4` medium → HARDWARE → the **neutral litmus** (correctly not blocked). The other Fischer
   records name no specific catalyst species in their quotes and stay `catalysts=()` (naming one would be inference).
3. **Wiring** (`service.py:_affordability_frontier`): `hard += route_catalyst_blockers(route)`. Byte-identical for
   every current route (0 declare a metal catalyst; the one that declares H2SO4 is kitchen → no block).
4. **Cleanup** (`equipment.py`): removed the dead `or envelope.catalysts` disjunct that gated nothing.
5. **R50 probe discharge** (`experiments/poor_man_ingenuity_scissors_probe.py`, re-frozen
   `e2189bdc…` → `56fa061c…`): KILL-2b **discharged** (a SEED record now carries a structured catalyst); the KILL-2
   blindness **discharged at the obtainability layer** (the new gate blocks the declared Ru/Ir catalyst); the OLD
   process/equipment legs stay catalyst-agnostic **by design** (a boundary, not a kill). **KILL-1 (the recognizer
   radius collision) and the census are UNTOUCHED**, so the ingenuity *reward* stays deferred.
6. **New probe + tests**: `experiments/catalyst_availability_probe.py` (FROZEN_HASH `a2a55d3f…`),
   `tests/test_catalyst_availability.py`, updated `tests/test_poor_man_ingenuity_scissors.py`.

## Honest boundaries (say the quiet part)

- **Guard ahead of its data.** No registered reaction declares a metal catalyst today, so the EXCLUDE path changes no
  live route's output — it is proven on constructed routes and benign on every real one. Stated, not hidden.
- **Routes-mode only.** The affordability frontier populates in routes mode; a DAG/decompile compile does not see the
  catalyst block. This is the *existing* frontier boundary, inherited — a named follow-up (a DAG affordability
  frontier), not a new hole.
- **The general `fit_status` stays catalyst-agnostic by design** (lab boxes exist). A box-gated `fit_status` fold is a
  named follow-up.
- **Obtainability ≠ feasibility.** "The catalyst can be bought" is a narrow claim about a substance. It does NOT claim
  the reaction proceeds — chemoselectivity/sterics stay unmodeled (R50 KILL-1). This gate never vouches feasibility.

## Unlock relationship to the deferred ingenuity reward (PR-2)

This is the first increment of the "real substrate-aware feasibility/catalyst-availability model" R50's ordered
unlock named. It retires unlock condition #1's **catalyst-availability half**. The reward remains **deferred**: R50's
KILL-1 (the enumeration-frontier recognizer cannot carry an unbounded-radius envelope on a bounded-radius edit),
condition #2 (a fail-closed recognizer), and #3 (a proven reachable consumer) are all untouched.
