# Move 5(b) (the cross-domain shared ranker) — scope decision v0.2

> **Status:** SCOPE DECISION — **DEFER the cross-domain shared ranker, CONFIRMED with the landscape moved; SHIP the
> one sound intra-chemistry consolidation the re-recon surfaced.** Supersedes
> `MOVE5_DOMAIN_NEUTRAL_PARAMETERIZATION_SCOPE_DECISION_v0.1.md` (which deferred the whole Move 5 pipeline lift and
> predated R37/R38). v0.1 called the lift a zero-call-sites abstraction; R37 (the circuit `CircuitRoute` pipeline)
> and R38 (the `select_within_spec` ranker) then built the genuine second-domain consumer v0.1 said was missing, so
> the "one shared ranker" half of Move 5(b) was re-opened and re-run here. The verdict holds — but now it is
> *proven*, not merely predicted, with two code-run counterexamples.
>
> Bearings: a 4-bearing adversarial re-recon (2026-09-10) — cartography (`citadel-rick`), YAGNI (`butter-robot`),
> consumer-existence (`citadel-rick`), structure-theorem (`dalembert`). All four independently returned DEFER.
> Evidence pinned in `experiments/move5b_shared_ranker_probe.py` (FROZEN_HASH `9547c422`) +
> `tests/test_move5b_shared_ranker.py`.

## What Move 5(b) asks for

Retrofit BOTH domains — chemistry synthesis routes and circuit designs — onto **ONE shared ranker**, so
`ExperimentStep`/`ExperimentRoute` and `CircuitRoute` become instances of a domain-neutral "conserved-inventory
transition + survival predicate + cost" ranking, realizing `[[electromagnetic-scope]]` as a theorem rather than two
parallel implementations. (The full pipeline-type lift off `Molecule` — v0.1's subject — stays deferred for the
same unchanged reason: 27+ nominal `type(x) is Molecule` guards + a chemistry-specific `Reaction`/`Config`
conservation certificate; genuinely Size L; circuits do not want `ExperimentRoute`. This doc is only about the
**ranker** half.)

## The recon verdict: DEFER — the two rankers do not share a domain-neutral law richer than `sorted(key=...)`

The two ranking entry points look superficially alike (both "score candidates, present a legible order"), but the
only law both genuinely obey is *totality / never-silently-drop* — which is exactly `sorted(key=...)` plus a
disclose-don't-drop convention, carrying no marginal machinery worth a shared module. Everything richer **diverges**,
and two of the divergences make a forced unification unsound, not merely awkward:

### CE-1 — chemistry's ranking is SET-RELATIVE; circuit's is per-candidate (run on real code)
`rank_routes`' 5th ranking tier, `front_index`, is the Pareto non-dominated **layer** computed by
`_pareto_front_indices` over the *whole* candidate set. A route's layer is a function of its siblings:

```
_pareto_front_indices((P1=(-10,.9), P2=(-5,.8), P3=(-1,.7)))  ==  (0, 1, 2)
_pareto_front_indices((            P2,          P3         ))  ==  (0, 1)      # P2's layer: 1 -> 0
```

Removing the dominator `P1` promotes `P2` from layer 1 to layer 0. Circuit's `(resistance, name)` key is strictly
per-candidate and set-invariant. A generic `key: Callable[[T], K]` evaluated per-candidate **cannot** reproduce
`rank_routes`. The lossless signature is `Callable[[Sequence[T]], Callable[[T], K]]` (annotate-the-whole-set, then
score each item) — which is *entirely chemistry's* requirement: circuit's key would ignore the outer `Sequence`
argument on every call, forever. Symmetrically, circuit needs a `survives`/partition knob chemistry never exercises
(chemistry ranks-all, dropping nothing). **Each of the two "generalizing" knobs is permanently pinned by exactly
one of the two callers** — that is not a shared law, it is one domain's shape with the other folded in as an unused
special case.

### CE-2 — the fail-closed polarity on "unknown" is OPPOSITE (run on real code)
The same abstract event — *the ranking quantity is unknown / undefined* — is handled in opposite directions:

```
_pareto_front_indices((good=(-10,.9), dominated=(-1,.1), unknown=(None,None)))  ==  (0, 1, 0)
```

The **unknown** objective lands the TOP layer (0), *above* the complete-but-dominated route (layer 1) — chemistry's
deliberate neutral-on-ignorance policy (the M2b reward-for-ignorance fix). Circuit does the reverse: an out-of-band
(or `None`-cost) candidate is **ejected** to the disclosed-reject channel (`within_spec` returns `False` before it
can ever float; `within_spec(resistor(20), 0, 10) is False`). A single primitive with ONE unknown-policy is
therefore **either unsound for circuits** (it would float an open/short into the survivors) **or wrong for
chemistry** (it would invert M2b). There is no neutral choice; the policy is domain-semantic, not domain-generic.

### Corroborating divergences (from cartography / consumer-existence bearings)
- **Output contract:** `select_within_spec` PARTITIONS into `(survivors, rejected)`; `rank_routes` RANKS-ALL into one
  ordered tuple (EXCLUDED merely sorts last, never dropped). Confirmed at the real call sites (`service.py:1899`,
  `compile.py:429` consume the full tuple).
- **Three-bucket chemistry admissibility:** chemistry preserves a distinct FITS / **UNKNOWN-retained-for-evidence** /
  EXCLUDED trichotomy (`compile.py:454`, `service.py:1548-1597`); circuit's boolean survive/reject has no slot for
  "retained but not selected" — collapsing it is lossy.
- **No shared call site exists today:** nothing calls both rankers through one interface; chemistry admissibility is
  itself three independent implementations, none blocked or strained for want of a shared primitive.

## What WAS earned and shipped this round (the constructive finding)

The re-recon's one constructive result is **intra-chemistry**, not cross-domain, and it is sound, lossless, and
already needed: `_route_score` and `_dag_score` duplicated the 10-tier score tuple + the M2b gating **verbatim**, and
`rank_routes`/`rank_dags` duplicated the Pareto-product + front + sort wiring — kept in lockstep only by a comment
`drafter.py` itself feared would drift (*"M2b grows BOTH scorers together … or the divergence reopens"*; the M2b tier
had in fact to be threaded into both copies by hand). Both scorers are multi-objective + neutral-on-unknown, so ONE
shared core is sound with two real call sites.

`smartchem/experiment/drafter.py` now factors:
- `_score_tuple(...)` — the 10 ranking tiers + the M2b Pareto/ΔG-magnitude gating, in ONE place.
- `_physics_ranked_order(fits, nets, survivals, score_fn)` — the shared set-relative front + stable score sort.

`_route_score` (nested `fit.selectivity.verdict`) and `_dag_score` (flat `fit.selectivity_verdict`) are now thin
verdict-extractors over `_score_tuple`; `rank_routes` and `rank_dags` both call `_physics_ranked_order`. A future
ranking tier grows **once**, and the two rankings cannot diverge by omission — the DAG-RANK-01 no-divergence promise
is now structural, not a hand-kept comment. **Byte-identical** to the prior output (the merged `comp_rank` keeps the
DAG-only `NO_TRANSITIONS` key, which a linear route's verdict never takes). Verified: the full ranking + pipeline +
paracetamol-north-star test surface stays green.

This does **not** advance the cross-domain categorical arc — it is a code-health consolidation that eliminates a
stated drift hazard and prepares the *chemistry-side* multi-objective primitive a future genuinely-chemistry-shaped
consumer could ride.

## What would UNLOCK the cross-domain shared ranker (the trigger to revisit)

Build it only when a **third ranking consumer is itself multi-objective + neutral-on-unknown + rank-all** — i.e.
genuinely *chemistry-shaped*, exercising the set-relative Pareto tier and the neutral-on-ignorance policy — so the
shared primitive has ≥2 real call sites that both need its full contract. Concretely: a second synthesis-like domain
(a staged materials/assembly process ranked on a Pareto product of conserved quantities), NOT the circuit selector
(scalar cost + boolean partition + opposite fail-closed polarity — a permanent degenerate special case). Absent that,
a cross-domain ranker is a zero-content wrapper (`THE_DIFFERENCE.md`'s falsified pattern) or a lossy one; the honest
common primitive between chemistry and circuits remains `sorted(key=...)`, which needs no module.

## Recommendation

**Defer the cross-domain shared ranker; the intra-chemistry consolidation is the earned increment and is shipped.**
The categorical arc's better-earned next steps are unchanged: the item-5 drafter-ranking `phases` brick (unparks at a
dual-phase ranked route), and — for the DOW north star — the modern bromine sourcing basis. Every structure earns its
call sites; the cross-domain ranker waits for the domain that will actually use its full contract.
