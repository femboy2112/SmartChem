# Move 6 — conditions distribute through a route's causal order (the withdrawn λ, re-aimed) — design contract v0.1

> **Status:** BUILD (a verified-bug fix + a formalized invariance law), spec-as-contract FIRST per the ROADMAP gate.
> This is **not** a formalization-only target (the live operation is not already correct — it is live but
> *incoherent*), and **not** a defer (unlike Move 5, a real live consumer exists). The deliverable is a minimal
> correctness fix to one live verdict path + the coherence law it satisfies pinned as a test + the naming — **no new
> runtime abstraction, no `Conditioned`-comonad resurrection** (the zero-call-sites trap this repo has already
> falsified, `THE_DIFFERENCE.md:9`).
>
> Bearings: a 3-way read-only recon (2026-09-07: the effect-monad reality, the condition-composition reality, the
> distributive-law consumer) + a first-hand live reproduction of the bug. Then two pre-build design reviews
> (birdperson soundness + butter-robot YAGNI) and one post-build adversarial pass (evil-morty).

## 1. What Move 6 / `THE_ORBITAL §IX` asks

`THE_ORBITAL.md:339-343` withdraws a claim rather than restate it:

> **No adjunction between the environment comonad and an effect monad.** … Establishing it requires a distributive
> law `λ : T∘W ⇒ W∘T`, which has not been constructed or checked here. The claim is withdrawn rather than restated.

The project reframe (memory `categorical-reorientation`, ROADMAP Move 6): *"a distributive law so conditions compose
lawfully through routes."* T = the route/effect structure; W = the per-step condition context
(`smartchem/conditions.py ConditionEnvelope`).

## 2. The recon verdict: the literal T∘W⇒W∘T is the zero-call-sites trap; the honest λ is at the route level

A literal construction between §IX's own pairing is a dead end, and building it would reincarnate the exact
falsification this repo is built against:

- **T literal = `smartchem/pathway.py` (`Pathway a ~ WriterT Tally []`, §V) is a dead island.** Zero production
  call edges into or out of `smartchem/experiment/`; only its own tests + one comparative docstring line
  (`conditions.py:9`) touch it.
- **W literal = `smartchem/conditions.py Conditioned` (the Env comonad) is dead.** Zero call sites outside its own
  module and its own self-verifying law test (`tests/test_conditions.py::TestComonadLaws` — a common-mode mirror,
  the precise anti-pattern of `docs/research/PROVIDER_ALGEBRA_AS_SMC_GENERATORS_v0.1.md`). Its docstring promise
  (`conditions.py:17-19`) — `extend` "lets a *whole chain* be judged co-valid under one shared envelope" — is
  **unfulfilled**; the live pipeline does the textbook opposite (independent per-edge checks, worst-folded,
  `experiment/assembly.py:148`).

So the deliverable is neither the pathway/comonad adjunction (which stays **correctly withdrawn**) nor a new
comonad runtime. It is the *route-level* realization of the same shape, where conditions and effects actually meet
live: **the condition-derived effect a route imposes on an intermediate must be a function of the route's causal
partial order — invariant under how that order is linearized into a schedule.**

## 3. The consumer: a verified order-dependence bug in a live verdict path

Conditions are *not* composed across a route today — they are compared pairwise per adjacent transition and
worst-status folded (`composability.py:591-610`, `dag.py:840-858`). The one place ≥2 steps' conditions drive a
whole-DAG verdict is the serial-hold / duration-survival mechanism (R15 DAG-HOLD-01 disclosure → R23
DURATION-SURVIVAL-01 gate), and it is **not coherent**.

`_serial_hold_segments` (`dag.py:809-837`) charges an intermediate on edge `(i,j)` the elapsed time of every step
`k` with `pos[i] < pos[k] < pos[j]` in **one arbitrary topological order** (`_topological_order`, `dag.py:143-165`,
Kahn with a step-**index** tie-break). R23's `_apply_duration_gate` (`composability.py:412-486`) then lets that hold
**affirmatively flip** the verdict to `DEGENERATE`. So an arbitrary, chemically-inert choice — which independent
branch a caller lists first in `SynthesisDAG.of(...)` — decides pass/fail.

**Reproduced first-hand** (the shipped `_convergent_40min_dag` fixture, two independent 40-min branches → a join,
with the shipped synthetic acetic-acid decomposition rate injected; only the branch *listing order* permuted):

```
SynthesisDAG.of(s_acoh, s_etoh, s_join)  ->  verdict DEGENERATE   (acoh at index 0; etoh sorts "between" 0 and 2)
SynthesisDAG.of(s_etoh, s_acoh, s_join)  ->  verdict UNKNOWN       (acoh at index 1; nothing sorts "between" 1 and 2)
```

Same edges, same chemistry, only the tuple order swapped. This is the **"spurious linearization of independent
steps"** pathology the project already named and quotiented in the open-SMC backbone
(`OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md`, R24 congruence, `[[a-quotient-must-be-a-congruence]]`) — but that
quotient was never extended to `dag.py`'s serial-hold / duration-survival mechanism. It is live-reachable through
the shipped `assemble_synthesis` → `SynthesisDAG.of` path (branch order passed through verbatim, uncanonicalized),
and it is currently **untested** (R15 pinned "disclosure never degrades a verdict" for the pre-R23 static note, but
there is no R23-era sibling for the duration gate that now legitimately does degrade verdicts).

## 4. The law (the distributive-law coherence, honestly scoped)

> **LINEAR-EXTENSION INVARIANCE.** The whole-DAG composability / duration-survival verdict — and the machine-readable
> holds it discloses — must be **invariant under every linear extension of the DAG's causal partial order.**
> Equivalently: the condition-derived hold an intermediate experiences must factor through the *quotient that
> identifies all linearizations of the same causal order*, not through the incidental total order Kahn's algorithm
> happens to pick.

This is the route-level realization of §IX's `λ`: it is the coherence condition under which the condition context
(W) distributes through the route's causal composition (T) — the whole-route reading `W∘T` (one coherent
hold-per-intermediate over the causal order) agrees with any per-linearization reading `T∘W`. It is the **same
discipline** as the open-SMC interchange law (order among *independent* steps is a spurious distinction to be
quotiented; order among *causally dependent* steps is real and preserved), now extended to the duration mechanism.

**Honesty on the categorical claim (the Move-3 discipline — do not over-name):** we do **not** claim to have
constructed the literal `T∘W⇒W∘T` natural transformation between the pathway monad and the Store/Env comonad; those
stay withdrawn (§2). The earned claim is precisely the invariance law above. If review finds "distributive law"
over-names it, the fallback name is **linear-extension invariance / the linearization quotient** — still a real,
non-vacuous, falsifiable law, just without unearned vocabulary.

## 5. The fix design

Two order-independent quantities, each a function of the causal partial order (the transitive closure of
`dag.edges` on step indices; `n` is small, plain reachability BFS per node or Floyd–Warshall):

- **Forced-between** for edge `(i,j)`: `{ k ∉ {i,j} : i →* k  and  k →* j }` — the steps that occur after `i` and
  before `j` in **every** linear extension (unavoidable). This drives the **GATE** (`_serial_hold_segments` →
  `_apply_duration_gate`): only an unavoidable hold may flip a verdict to `DEGENERATE`.
- **Possibly-between** for edge `(i,j)`: the siblings schedulable strictly between `i` and `j` in **some** linear
  extension (`not(k →* i) and not(j →* k)`). This drives the **DISCLOSURE** only (the R15 serial-hold note and the
  R19 machine-readable `serial_holds` triples) — a schedule-relative caveat that **never** flips a verdict,
  restoring R15's "disclosure never degrades a verdict" while making it order-independent (reported over all
  extensions, not one Kahn order).

**Why forced-between (min), not worst-case interleaving (max), for the gate.** The project already decided this
direction: the DAG process-fit aggregates over the **critical path (an achievable schedule), not the serial sum**
(`test_dag_process_fit_uses_a_sound_critical_path_not_a_serial_sum`, "it stops OVER-excluding a concurrent route").
Gating on the unavoidable (best-schedule) hold is the same optimistic-but-achievable reading: a route is
`DEGENERATE` only if *no valid schedule* saves the intermediate (even the minimal forced hold destroys it). A
worst-case-max gate would re-introduce the over-exclusion the critical-path decision removed, and would let an
arbitrary *worst* interleaving condemn a route a good chemist would simply schedule around. The residual 2nd-order
concern — whether *all* intermediates can be scheduled-last *simultaneously* (a makespan question) — is explicitly
out of scope (§6); the first-order fix is to kill the arbitrary-order dependence.

## 6. What this does NOT claim (boundaries; anti-fabrication)

- **§IX's literal adjunction stays withdrawn.** No `T∘W⇒W∘T` between `pathway.Pathway` and `Store`/`Conditioned`; no
  resurrection of the dead `Conditioned` comonad; no new categorical runtime object.
- **No makespan / global-schedule feasibility claim.** Forced-between is per-edge; whether a single schedule makes
  every intermediate survive at once is a 2nd-order scheduling question, not decided here. The gate stays a
  per-edge tendency, `W3`.
- **Anti-fabrication (`known-physics-not-new-physics`).** Removing a *spurious* hold (one caused by an arbitrary
  linearization, not forced by the causal order) is a bug fix, not a loosening of sound physics — the intermediate
  provably does not sit through an independent branch in every schedule. The gate still `DEGENERATE`s on any
  *unavoidable* sourced degradation; it never launders a real one. `SURVIVES` never upgrades a verdict (R23 rule
  preserved). The disclosure never fabricates a hold (an unknown floor stays 0, a sound lower bound, as today).

## 7. Blast radius

- **Byte-stable on default data / no golden moved.** The default kinetics seed
  (`smartchem/data/kinetics.py`) holds only N₂O₅ and cyclopropane — neither a synthesis-DAG intermediate — so no
  default-data DAG is duration-assessed (the gate is off by default). Changing which steps are charged changes no
  observable default verdict. `serial_holds` is `compare=False` (`service.py:1123`, digest-excluded) and
  `response_schema.json` carries only a field *descriptor*, so no digest/schema golden moves.
- **Tests to update (expected, additive-or-corrective):** any test asserting the *old* (arbitrary-order) hold
  values on a convergent DAG (e.g. the R19 `serial_holds` 40-min triple, the R23 `_convergent_40min_dag`
  DEGENERATE-flip test) must be re-pinned to the *forced-between / possibly-between* values — a correctness
  re-pin, disclosed, not a silent regression.

## 8. Acceptance gate

1. The order-dependence probe (§3) is GREEN both ways: the verdict is invariant under permuting independent
   branches — pinned as a committed property test over a family of DAGs (linear chain, the convergent join, a
   diamond, a 3-branch join), not one fixture.
2. A genuine forced-between hold (a real causal-chain interposition) still flips `DEGENERATE` under the injected
   rate — the gate is not neutered, only made order-independent (non-vacuity control).
3. Full suite green in 4 batches; no golden moved (digests byte-stable); ruff clean on changed files.
4. birdperson (soundness: is forced-between the right invariant? min-vs-max? anti-fabrication + only-tightens
   preserved?) + butter-robot (YAGNI: minimal fix, no edifice) folded pre-build; evil-morty (can the verdict still
   be made order-dependent? a diamond? a laundered real degradation?) folded post-build.
