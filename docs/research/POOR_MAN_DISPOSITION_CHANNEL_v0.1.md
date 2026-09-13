# Poor-man ingenuity — the distinct disposition channel (R59, DISPOSITION-01)

**Status:** SHIPPED (correct-ahead-of-data), with an honestly-frozen data-dark boundary.
**Probe:** `experiments/poor_man_disposition_channel_probe.py` (FROZEN_HASH `df4eb70798026ab73f5a7155c25bb3d09ccc77bddd748681b6a516b06b49b41e`).
**Tests:** `tests/test_poor_man_disposition_channel.py`; dominance lattice in `tests/test_affordability.py`.

## The debt this closes

The R56 oracle docstring named it "DISPOSITION FLATTENING". The affordability frontier G6-sinks a route on **any**
hard blocker, but two **kinds** of blocker shared one `hard_blockers` tuple:

- **REAL-BUT-HARD** — a genuine reaction merely needing an unobtainable catalyst, or barred by a section-11 bench
  bound (safety / identity / legal / equipment). A real option, just costly or out of reach.
- **NOT-A-REACTION** — a reaction-TYPE **fiction** (Problem A): a formula-balanced graph move that is no real
  reaction at all (the compiler over-generates these by formula-conserving capped-scission surgery).

Sharing one tuple **flattened** them: "real reaction, needs an industrial catalyst" and "not a reaction at all"
were G6-sunk **equally**, and the partial order *real-but-hard strictly outranks not-a-reaction* was lost.

## What shipped

Two **disjoint** channels on `CostVector` — `hard_blockers` (real-but-hard) and `fiction_blockers`
(not-a-reaction) — driving a 3-tier `Disposition` (`CLEAN < REAL_BUT_HARD < NOT_A_REACTION`) that `dominates`
reads **instead of** a 2-valued blocked bit:

- **disposition dominates cost (G6, 3-valued):** the better-disposed tier wins at any price; only an equal tier falls
  through to the numeric axes. This subsumes the old clean/blocked rule and adds the strict
  `REAL_BUT_HARD ≻ NOT_A_REACTION` order. Proven a sound strict partial order (irreflexive / asymmetric /
  transitive) by a seeded brute force over all three tiers.
- **serialized** through the replay payload (schema bump `affordability-frontier-entry-v1alpha2 → v1alpha3`); the
  disposition round-trips (it is ranking-load-bearing, so it is part of identity — *not* hidden like the R58 centre).
- the wiring in `service._affordability_frontier` splits the reaction-type fictions onto `fiction_blockers`, leaving
  section-11 exclusions + catalyst obtainability on `hard_blockers`.

## ⚠️ The honest headline: the RANKING effect is data-dark today

The 3-tier ranking **differentiates** one route from another only when a `REAL_BUT_HARD` route and a
`NOT_A_REACTION` route **coexist**. An exhaustive sweep of all 45 registered targets
(`probe.full_registry_scan()`) measures:

| metric | value |
|---|---|
| reachable REAL_BUT_HARD routes | **0** |
| reachable NOT_A_REACTION routes | 24 |
| mixed-tier (both) targets | **0** |
| targets whose frontier membership differs (new 3-tier vs old 2-tier) | **0** |

There is **no reachable real-but-hard route in the production system**: the only two sources are both dark — **no
registered reaction declares a metal catalyst**, and **no route is section-11 EXCLUDED at depth 3** (every ranked
route is `UNCONSTRAINED` or `UNKNOWN`). So the new 3-tier frontier is **verdict-identical** to the old 2-tier
frontier for every target: **the split is verdict-neutral in production today.**

This is not hidden — it is the finding, and the probe **asserts** it (`ranking_verdict_neutral_in_production`), so
the day a real-but-hard route becomes reachable the pin **flips** and R59 must be re-stated (a genuine ranking
consumer will have appeared).

## Why ship it anyway (correct-ahead-of-data)

- **It fixes a latent misranking.** The flattening is a real bug that fires the moment a real-but-hard route
  coexists with a fiction. The channel is the correct contract, ready — exactly like the catalyst-obtainability
  guard beside it, shipped as "a guard ahead of its data".
- **The classification IS reachable and served.** 24 fiction routes now carry a **distinct** `NOT_A_REACTION`
  disposition, legible via `cost_vector.disposition` / `fiction_blockers`, that the old flat `hard_blockers` could
  not express. The payload self-describes the disposition.
- **Proven correct when reachable.** A constructed real-but-hard + fiction pair shows the split drops the (cheaper)
  fiction below the real-but-hard route, and both below any clean route.

## What activates the ranking effect

A reachable `REAL_BUT_HARD` source: **feasibility wiring** (Problem B — a type-vouched but feasibility-blocked
route becomes real-but-hard; still deferred, with its own soundness questions), a **declared metal catalyst** in a
registered reaction, or a **section-11 bench exclusion** of a real route.

## No regression

- The 24 fiction routes stay demoted (dominated by any clean route) exactly as before the split.
- Prior poor-man probes (R55/R56/R57/R58) had their frontier channel-read corrected to the **union** of both
  channels; because `content_hash` pins the measured payload (not the source), their frozen hashes are **stable** —
  the byte-identical measurement is preserved. No re-freeze, no supersession.
