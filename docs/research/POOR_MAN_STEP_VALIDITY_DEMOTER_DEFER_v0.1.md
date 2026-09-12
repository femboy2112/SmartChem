# Poor-man ingenuity reward — step-validity demoter, R55 → DEFER #6 (with a PROVEN consumer)

> **Canonical record for ROUND 55.** The sixth verified defer of the ingenuity reward — and the first that
> lifts the blocker every prior defer was gated on. Evidence:
> `experiments/poor_man_step_validity_demoter_defer_probe.py` (FROZEN_HASH
> `a008811ec2642535cd81f2875f1a722ced32e11969c51db0d2bb765f4810024d`) +
> `tests/test_poor_man_step_validity_demoter_defer.py` (9 pins). Plan:
> `POOR_MAN_ARCH_COMPLETION_PLAN_v0.1.md`. RDKit-free; suite unaffected (docs + experiment + test only).

## 1. The two questions this round answered

The user asked to run, in coherent order, the two teed-up forks from R54: **(1)** build the different-KIND
reward model, and **(2)** manufacture / prove a live consumer — with the consumer gating the model. Answers:

- **Increment 2 (consumer) — the premise is REFUTED by measurement.** A live consumer does not need to be
  *manufactured*; it is already **shipping, surfaced, and dominant**. On the full production path
  (`run_compilation(...).affordability_frontier`), **21 of 29 affordability-frontier routes across the registry
  (72%) are chemically fictional and carry empty `hard_blockers`** — presented to a user as real, cheap,
  fully-commodity routes today. Isopentyl acetate alone ships **10** such routes at ~4.5¢ each. The reward's
  home (`_affordability_frontier` hard_blockers → G6) has a proven, dominant job.
- **Increment 1 (model) — DEFER #6.** The natural Problem-A demoter broke at a 5-bearing adversarial design
  gate the same way its five predecessors did, one alphabet over (§4).

## 2. The reframe: Problem A ≠ Problem B (the arch chased the wrong problem for five rounds)

The compiler DERIVES reactions by capped-scission graph surgery that conserves molecular **formula**, not
feasibility, so the search **over-generates** formula-balanced-but-fake steps. Two orthogonal failure kinds:

- **Problem A — reaction-TYPE fiction:** the step is *no real reaction at all* (a formula-balanced graph move
  with no mechanism). Example: `propan-2-ol + ethyl acetate → isopentyl acetate + water` — gluing two alkyl
  fragments with a new C–C bond and calling the two departing atoms "water".
- **Problem B — substrate feasibility:** the step *is* a real reaction type but the substrate misbehaves
  (polymerises, decomposes, side-reacts). This is the R49–R54 keystone — **verified-DEFER ×5**.

Three independent instruments (ΔC–C net count; induced-subgraph-isomorphism join recovery; exact
`capped_scissions` provenance replay) agree the frontier pollution is **~100% Problem A**. **Problem B — the
substrate-inertness keystone the arch spent five rounds on — was never what polluted the frontier.**

## 3. The candidate model (Increment 1) and its positive result

The natural Problem-A demoter: **recover each step's formed JOIN BOND** (the `CappedScission.cut` re-joined in
the assembly direction — an *exact* datum, a total function of the cut) and **demote any route with a step whose
join is a new C–C bond formed with small-molecule loss** (a skeleton fusion); **abstain** on C–O/C–N/C–S joins.
On the current registry this looked clean:

- **complete** — all 21 fictional frontier routes carry ≥1 C–C-fusion step → all sunk;
- **sound-as-surfaced** — all 8 surviving (non-C–C) routes are real reaction types (esterification, amidation,
  etherification, and caffeine's untabulated N-methylation — the R45 genericity win is **kept**);
- 0 surfaced false-VOUCH and 0 surfaced false-EXCLUDE on the 19-commodity / 45-target deployment.

That "clean" result is a **check-derived-from-its-own-subject**: it holds only on the deployment subset the
battery happened to cover.

## 4. Why it is still a defer — the FATAL refutation (5-bearing gate, author-reproduced)

The join-bond element is exactly computable, but it **does not map to fake/real**. Both failure directions are
reachable and were reproduced against live code:

| Failure | Reproduced case (compiled through the real search) | Join | RAW rule | Truth |
|---|---|---|---|---|
| **FALSE-VOUCH** | `isopentane + H2O2 → isopentyl alcohol + water` | C–O | abstains → **VOUCH** | fake (C–H hydroxylation, no mechanism) |
| **FALSE-VOUCH** | `ammonia + 4-aminophenol → p-phenylenediamine + water` (both commodities) | C–N | abstains → **VOUCH** | fake (aromatic amination, Bucherer) |
| **FALSE-EXCLUDE** | `benzene + acetic acid → acetophenone` | C–C | blocks → **SINK** | real (Friedel-Crafts acylation) |
| **FALSE-EXCLUDE** | `benzene + methanol → toluene` | C–C | blocks → **SINK** | real (Friedel-Crafts alkylation) |
| **FALSE-EXCLUDE** | `2 ethyl acetate → ethyl acetoacetate + ethanol` | C–C | blocks → **SINK** | real (Claisen condensation) |

So **"C–C join" is neither necessary nor sufficient for "fake".** The fake set (C–H functionalisation dressed
as C–O, aromatic amination dressed as C–N, …) and the real set (Friedel-Crafts, Kolbe-Schmitt, Claisen) both
straddle the join-element boundary. Every bounded-local refinement (join-element → +leaving-group →
+aromaticity) is met by a new leak — the R53/R54 patch spiral. The five gate bearings:
dalembert **FATAL** (the C–O/C–N false-VOUCH structure theorem, reproduced), evil-morty **FOLD** (multi-cut
join-recovery gap; the claimed cut/caps threading does not exist — must re-derive via `capped_scissions`),
daniel **FOLD** (base rate confirmed; the surviving frontier is not fully clean — the p-phenylenediamine C–N
fake), birdperson **FOLD** (the join feature is exact but insufficient; and a fiction is *not* a bench-blocked
route — the `hard_blocker`→EXCLUDED channel misnames *why* it sinks), butter-robot **FOLD** (consumer real; cut
the Claisen refinement as speculative; prefer re-derive over a production schema change).

## 5. The theorem (this defer's contribution)

> **Reaction-TYPE validity resists bounded-radius local recognition, exactly as reaction FEASIBILITY did
> (R49–R54).** A bounded-local feature of the reaction center (substrate element census R53/R54; join-bond
> element R55) cannot carry an UNBOUNDED property. For R49–R54 the property was "does the substrate cooperate";
> for R55 it is "does a mechanism exist" — both live in the open reaction-mechanism space (electrophilicity,
> aromaticity, activation, leaving groups, bond-order changes) that no local census of the center can read.

The escape for **both** problems is the one the prior defers already named: an **external reaction oracle**
(match each derived step to a known reaction TYPE, fail-closed, demote unmatched) — at the cost of the
"derive untabulated reactions" genericity (the R45 caffeine-methylation win would need its template registered).
That genericity tradeoff is the real R56 design question, now **gated on a proven consumer (met)**.

## 6. What is banked (this defer carries the most forward of the six)

1. **The "zero live consumers" blocker is LIFTED** — proven, surfaced, dominant (72% frontier pollution). Every
   prior defer (R49–R54) was gated on a consumer that did not exist and could not be manufactured by the
   reachability lane. It exists.
2. **The problem is correctly decomposed** — Problem A (reaction-type fiction) vs Problem B (substrate
   feasibility); the pollution is A, not the 5×-deferred B.
3. **Sound sub-components** — the formed join bond is *exactly* recoverable from `CappedScission.cut` (no schema
   change: re-run `capped_scissions` on the step and match products on canonical identity, reading only the
   heavy-atom cut). The ΔC–C / join-element instrument is a valid **measurement** instrument (it correctly
   measures the join element and the base rate) even though the join element is the wrong **feature** for the
   fake/real decision.

## 7. Next escape (R56, gated on the now-proven consumer)

Build a **reaction-TYPE oracle gate**: recognize a derived step by matching it to a known reaction TEMPLATE
(the `SEED_CONDITIONS` pattern promoted from *decoration* to a *fail-closed gate*, generalised to abstract
templates), demote the unmatched, feed the block into `_affordability_frontier`. The load-bearing design
question is the **genericity tradeoff** (abstract structural templates keep untabulated-but-real reactions;
specific templates are sound but sink the R45 win) — and the **disposition-honesty** fold (a fiction should sink
as *"not a reaction"*, which may want its own channel rather than the bench `hard_blocker`). Do **not** re-attempt
a bounded-radius local recognizer of the join or the substrate — R49–R55 collide the same way at every polarity
and every alphabet.

## 8. What ships this round, and the boundaries

Ships: this doc, the frozen probe, the 9-pin test, and the ROADMAP/plan/memory updates. **No production code** —
the RAW rule is deliberately left UNWIRED (shipping a proven-unsound blacklist recurs the theorem). Boundaries:
the false-VOUCH/false-EXCLUDE counterexamples require non-commodity feedstocks (isopentane, benzene) or an
unregistered target to *surface*, so on today's exact registry the RAW rule has zero *surfaced* false-VOUCH —
but it is proven unsound the moment the commodity set grows, which is a stated project direction. The base rate
(21/29) is over `CAPPED_SCISSION_LINEAR` routes mode with the default water reagent; other reagent pools and the
k≥2 / ring-aware grammar expand the fiction space further. Kitchen-truth labels ("fake", "real") are
textbook-asserted named-reaction chemistry (rdkit intentionally absent), not wet-lab.
