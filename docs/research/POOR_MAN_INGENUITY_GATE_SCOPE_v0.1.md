# Poor-man ingenuity gate — scope & VERIFIED DEFER (R49 + R50, PR-2)

**Status: VERIFIED DEFER (twice).** R49 killed a *feasibility-layer* reaction-class recognizer that mints a
positive "reality-respecting / poor-man-reachable" reward from functional-group topology (below). **R50 then
killed the redux itself** — the frontier-recognizer + per-class-envelope + capability-gate design at the bottom
of this doc — with its own four-bearing adversarial gate, and proved a deeper result: the **ingenuity scissors**
(§R50). The sound ingenuity reward is deferred until a real *substrate-aware feasibility model* exists. Both
kills were caught on paper before any wiring; zero production code changed either round. Evidence:
R49 `experiments/poor_man_ingenuity_gate_defer_probe.py` (`d7c613ab…`); **R50
`experiments/poor_man_ingenuity_scissors_probe.py` (`e2189bdc…`) + `tests/test_poor_man_ingenuity_scissors.py`.**

## The directive
Poor-man ethos is a **HUNTING** objective: actively surface reality-respecting-but-unconventional routes
("wtf how — OK it works"), gated hard on *actually-works*, never fabricated. The reality-respect gate must be a
DERIVED reaction-class recognizer carrying **each class's real feasibility envelope**, fail-closed on unrecognized
— because thermo + conservation are a RUBBER STAMP (necessary, not sufficient). Don't hard-code reactions;
hard-code STRUCTURE/reality, DERIVE the chemistry.

## The scoped design (what was proposed, then killed)
Over the elementary intermolecular shape (2 non-water reactants → 1 non-water product + water), classify each
step by functional-group context into `{VOUCHED heteroatom dehydrative alkylation | GUARDED free-acid
dehydrative acylation (= R48) | UNRECOGNIZED}`, then:
- **L1 (honesty):** GUARDED classes fail feasibility closed (subsuming R48).
- **L2 (the hunt):** a route earns a "reality-respecting, poor-man-reachable" reward iff every step is VOUCHED.

## The four-bearing gate (evil-morty + dalembert soundness · birdperson scope · butter-robot YAGNI)

### KILL-1 — FATAL (evil-morty + dalembert, converged, verified against real `feasibility.py`)
"VOUCHED" is a pure **graph-topology** predicate that carries **zero** information about catalysis or
kitchen-reachability — yet L2 spends it as an "actually-works, poor-man" signal. Even keyed CORRECTLY on the
formed C-heteroatom bond (dalembert's KILL-3 refinement), the predicate VOUCHES catalysis-required reactions:

| step | topological VOUCHED | actually needs |
|---|---|---|
| theophylline + methanol → caffeine + water | **True** | borrowing-hydrogen Ru/Ir catalysis, ~150–180 °C |
| aniline + ethanol → N-ethylaniline + water | **True** | Ru/Ir catalytic amination |

The poor-man reward would decorate metal-catalyzed reactions as "poor-man-reachable" — a **fabricated capability
claim**, the exact rubber stamp the directive forbids. Worse, the caffeine N-methylation was the design's own
cited non-vacuity example. **Tombstone: VOUCHED (topological) ⊬ kitchen-reachable, ⊬ proceeds-uncatalyzed; the
reward gate reads a signal that does not encode the property it rewards.**

### The rival law (dalembert) — the taxonomy earns nothing at the feasibility layer
"Free acid net-consumed + water out → GUARDED" is cheaper and more complete than the conjunction; it reproduces
R48's entire firing set. So the three-way recognizer's ONLY new feasibility-layer work was the L2 VOUCHED reward
— which KILL-1 kills. There is **no sound new feasibility-layer capability to ship.**

### What SURVIVED (kept untouched)
R48's `_is_intermolecular_acyl_condensation` guard — the aqueous free-acid dehydrative-acylation domain guard —
is sound, target-independent, single-water locality holds. It is a **negative** fail-closed guard (fires on the
acid class, silent on alcohol donors), not a positive reward. Unchanged by this PR.

### Two non-kills (verified so they are not chased)
- **Anhydride "leak" is harmless:** R48 does not guard `2 acetic acid → acetic anhydride + water`, but the ΔG
  estimator already returns **UNKNOWN** there (not a fabricated FAVORABLE) — no lie to catch, so R48's
  conjunction is right to leave alone.
- **Friedel-Crafts C-C** (`benzene + ethanol → ethylbenzene + water`) is correctly **not** vouched by the
  corrected formed-bond predicate — KILL-3(i) is recoverable, so it is not the fatal defect.

### Scope (butter-robot + birdperson)
L1 is already R48 (no over-fire bug: R48 correctly stays silent on caffeine's alcohol donor). The "taxonomy" is
two classes. A per-route reward with no sound reader is gold-plating. **Ship nothing at the feasibility layer;
record the defer + redux.**

## THE REDUX — PR-2-real (the sound hunter; blast on the user's go)
The sound reality-respect / ingenuity gate is a bigger build and belongs where the information it needs actually
lives:

1. **Recognizer at the ENUMERATION FRONTIER** (`routes.py` ~line 526, where each `ExperimentStep` is built from
   an `EnumeratedTransform`). There the transform object (`CappedScission` / `BondOrderEdit`) still carries the
   **exact local bond edit** — atom-map-sound, immune to the molecule-set non-locality that powers KILL-1/KILL-3.
   `ExperimentStep` drops the transform, so this recognizer cannot live at the feasibility layer.
2. **Per-class REAL FEASIBILITY ENVELOPES** — the conditions each recognized class needs (activation / catalyst /
   water removal / solvent), encoded as sourced/textbook REALITY (the allowed "ISA of chemistry" — a per-CLASS
   requirement keyed on the DERIVED class, never a per-reaction lookup). This is the "real feasibility envelope"
   the directive named; the ΔG estimator is NOT it.
3. **The ingenuity / poor-man reward gated on the KITCHEN CAPABILITY MODEL** (`kitchen-is-the-lab`, the
   `smartchem/observation/` + equipment layer) checking (2)'s conditions against household + outdoors equipment —
   **never** on graph topology or a ΔG proxy. A route is "poor-man ingenuity" iff every step's class is
   recognized AND its condition envelope is satisfiable in the kitchen. Every route still `FORMAL_CANDIDATE`.
4. **Then** the deferred reachability pieces stack on cleanly: mediator widening (the measured depth-exponential
   cost bomb, now prunable by the frontier recognizer), a `--kitchen-only` filter, and the ranking demotion of
   non-kitchen tiers — all consumers of (1)–(3).

### Boundaries / open questions for PR-2-real
- (2)'s per-class condition data must be honest known-chemistry, sourced or textbook — the anti-fabrication line
  ([[known-physics-not-new-physics]]). Start with the classes the frontier recognizer can soundly identify.
- The frontier recognizer changes route pruning → route-OUTPUT-changing, test-churny; needs its own frozen-probe
  re-baseline and its own adversarial gate (do not bundle with anything else).
- Keep the reward strictly ranking/annotation, never entering `RouteFitStatus`/`feas_verdict` (the R47
  `derived_rank` discipline).

## Lesson
[[a-capability-reward-must-be-gated-on-the-capability-model]] — a reward for a CAPABILITY property (reachability,
feasibility-in-context) must be gated on a model that MEASURES that property; a topological or thermodynamic
proxy that does not ENCODE it will confidently reward things that lack it (here: VOUCHing metal-catalyzed
reactions as poor-man-reachable). The proxy's silence on the property is not neutrality — it is a fabricated pass.

---

# R50 — THE REDUX IS KILLED: the ingenuity scissors

**Status: VERIFIED DEFER.** The redux above (frontier recognizer → per-class envelope → reward gated on the
existing capability stack) was killed by a second four-bearing adversarial DESIGN gate — dalembert + evil-morty
(soundness), birdperson (architecture), a daniel empirical census — **before any wiring**. The frontier premise
was re-verified true first (the transform *is* live at `routes.py:529`/`:764` via `_conditions_for(cs)`;
`ExperimentStep.from_transform` drops `cut`/`caps`, so the recognizer genuinely cannot live at the feasibility
layer), and the capability substrate is richer than the redux knew (`reagents.py` INDUSTRIAL tier,
`process_constraints.py` FITS engine, `equipment.py`, `observation/*`). It died anyway, at three layers.

## The three converged kills (all recomputed from live code at `c409e7a` — probe `e2189bdc…`)

**KILL-1 (dalembert, fatal — the recognizer itself).** The condition envelope of a reaction is an
*unbounded-radius* property (chemoselectivity, sterics, remote electronics all live arbitrarily far from the
reaction center), but any frontier recognizer reads a *bounded-radius* local edit (`cut`/`caps` + local
context). So the class key **must** collide across the kitchen boundary. Verified minimal family, one Fischer
esterification class, byte-identical atom-mapped edit `cut={(C,O,1):1,(H,O,1):1}`, `caps=` same, across **all**
of {pentyl acetate, heptyl acetate, 5-aminopentyl acetate, 7-aminoheptyl acetate}: pentyl/heptyl are kitchen
"banana-oil" esters; the amino members are NOT kitchen (the amine outcompetes the alcohol → N-acyl amide →
selective O-ester needs protection/deprotection). Invariance across chain length *and* terminal group is the
structure theorem made live: no fixed radius separates them. Atom-mapping fixed R49's *molecule-set*
non-locality; it does nothing about *graph-distance* non-locality. Corollary (fabrication): a per-CLASS key is
strictly coarser than `assembly_conditions`' per-reaction key, so it reintroduces exactly the guess
`decompiler_conditions.py` was built to refuse (tert-butanol dehydrates instead of esterifying; mesitoic acid
needs fuming H₂SO₄ — same class label, inverted envelope).

**KILL-2 (evil-morty — the reward gate).** Even granting a perfect recognizer AND a perfectly honest, complete
envelope with the metal catalyst and forcing temperature DECLARED, **not one leg** of the named capability stack
returns EXCLUDED: `evaluate_process` → UNKNOWN/UNKNOWN/UNCONSTRAINED (no catalyst field, no temperature ceiling),
`equipment.py` names no catalyst (its one `envelope.catalysts` read at `:176` is vacuous), reagent tiers gate
only *consumed* species (a catalyst is not consumed). The stack is **structurally blind to catalysis**. And
KILL-2b: every `SEED_CONDITIONS` record has an empty structured `catalysts=()` (catalyst in free-text `medium`)
— so even the sourced path is blind, and it is the authoring template a per-class table would copy. A reward
gated on this stack VOUCHes `theophylline + methanol → caffeine` — R49's KILL-1, relocated one storey down.

**birdperson (architecture, SOUND-WITH-FOLDS → the folds that bind).** The recognizer must be one shared
function (both `routes.py` call sites, or it drifts like the old duplicated ranker); it must not overload
`_conditions_for`; a per-class table survives the `SEED_CONDITIONS` no-guess discipline only if it carries
qualitative *requirements* (not fabricated setpoints), sourced + `EvidenceStatus`, fail-closed, silence-filling
only; and the reward must stay off the `_score_tuple` scalar — its only new info (catalyst/water-removal
reachability) belongs on the affordability Pareto frontier as a distinct axis or it double-counts
`access_difficulty`/`new_equipment`.

## The ingenuity scissors (why the bearings together prove more than a wiring bug)

- To be **ingenious** ("wtf how — OK it works") a route must be **unconventional** → it carries **no**
  per-reaction sourced record. That is what makes it unconventional.
- Sound reachability for an **unsourced** route can only come from a **derived** model (topology → class →
  envelope).
- KILL-1 proves that derived model is **unsound across the kitchen boundary**.
- daniel's census: of the 45 registered targets, the only route that is both per-reaction-sourced **and**
  commodity-terminated is a **conventional** textbook ester — methyl salicylate (`methanol[hardware] +
  salicylic acid[pharmacy] → methyl salicylate + water`, one EXPERIMENTAL step). Both flagships (caffeine,
  paracetamol) have **no** fully-sourced route.

So the only **sound, non-vacuous** poor-man signal available today fires exclusively on **already-documented
conventional** routes — the opposite of ingenuity. **The ingenuity objective is unrealizable soundly until a
substrate-aware feasibility model exists.** This is strictly stronger than R49: R49 said "topology can't be the
reward"; R50 says "for the *unconventional* routes ingenuity is *about*, no sound reachability signal exists
on today's models at all."

## The exact unlock conditions (what a future PR-2-real needs, in order)

1. **A real substrate-aware feasibility / catalyst-availability model** — declared `catalysts` → an
   `Availability` tier (metal/INDUSTRIAL ⇒ EXCLUDE), a forcing-temperature ceiling in `ProcessBounds`, and the
   whole-molecule chemoselectivity/steric check KILL-1 shows is required. Fail-**closed on incompleteness**, not
   merely on unrecognized-class (silence about a requirement is UNKNOWN, never "no requirement"). This is a NEW
   capability model, not "the existing stack." (It also needs the structured-`catalysts` data populated —
   today's SEED records bury catalysts in `medium`, so a catalyst-aware gate would see `()` and read "none".)
2. **A recognizer that fails closed to UNRECOGNIZED on any out-of-center functional group / steric feature** —
   fire a class only on a globally FG-monofunctional, unhindered substrate matching the prototype (dalembert's
   repair). This converts every false-VOUCH into the safe false-UNRECOGNIZED, at the cost of the reward speaking
   only about single-FG textbook substrates — which no registered *drug* target is.
3. **A proven reachable consumer** — a route set where the reward reorders a poor-man route above a
   buy-the-reagent route, and that reordering is currently absent or wrong. daniel showed the current registry
   does not supply one for the ingenuity case (only the conventional methyl-salicylate case).
4. **Then** the reward, on the affordability Pareto frontier as a distinct axis (never a `_score_tuple` scalar),
   ranking/annotation only, never entering `RouteFitStatus`/`feas_verdict`.

## A sound-but-not-ingenuity option that DID survive (recorded, not built)

daniel's signal — *every step per-reaction-sourced (`EXPERIMENTAL`) × every leaf non-INDUSTRIAL commodity tier*
— is sound and non-vacuous (methyl salicylate; correctly refuses the flagships). It is a legitimate poor-man
**confidence** annotation, but it is **not the ingenuity hunter** (it rewards conventional documented routes),
it fires on 1 of 45 targets, and it risks overlapping the affordability frontier's existing `access_difficulty`
axis (birdperson FOLD 5). Left unbuilt pending a decision that it earns its surface over the existing axes.

## Lesson (R50)
[[a-derived-estimate-must-guard-its-domain-of-validity]] applied to *classification*: a class label is a sound
carrier of per-class facts only where the classifying feature (a bounded-radius local edit) determines those
facts; when the fact depends on unbounded-radius structure, the label collides and the per-class value inverts,
not degrades. And the ingenuity twist: a "surface the clever unconventional route" objective cannot be made
sound by any signal that requires the route to already be documented — ingenuity and sourced-ness are the two
blades of the scissors. [[a-capability-reward-must-be-gated-on-the-capability-model]]
[[a-whole-set-count-classifier-is-fooled-by-non-locality]]
