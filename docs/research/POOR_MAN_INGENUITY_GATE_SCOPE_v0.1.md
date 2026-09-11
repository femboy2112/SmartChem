# Poor-man ingenuity gate — scope & VERIFIED DEFER (R49, PR-2)

**Status: VERIFIED DEFER.** The scoped PR-2 (a feasibility-layer reaction-class recognizer that mints a positive
"reality-respecting / poor-man-reachable" reward from functional-group topology) was **killed by a four-bearing
adversarial DESIGN gate before it was wired**. The sound ingenuity hunter is redesigned below (PR-2-real) and
deferred to the enumeration frontier + the kitchen capability model. Evidence:
`experiments/poor_man_ingenuity_gate_defer_probe.py` (FROZEN_HASH `d7c613ab…`) + `tests/test_poor_man_ingenuity_gate_defer.py`.

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
