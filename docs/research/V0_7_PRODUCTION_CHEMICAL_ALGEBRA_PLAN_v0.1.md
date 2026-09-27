# SmartChem 0.7 — Production Chemical Algebra (plan v0.1)

**Date:** 2026-09-27 · **Branch:** `feat/v0.7-production-chemical-algebra` (off `main@9798ed3`, the v0.6 merge)
· **Gate this round advances:** 0.7 in the finite 1.0 ladder (0.6 → **0.7** → 0.8 → 0.9 → 0.9.5 → 1.0).
· **Version policy:** stays `0.6.0a1`. A 0.7.x bump is earned only when the 0.7 gate below is actually met;
the inventory / plan / forcing vertical do **not** bump it.

## 0. The one-line problem (measured, not asserted)

`experiments/v0_7_provider_inventory.py` (live introspection) reports: the reaction-type oracle recognises
**17** classes; `DEFAULT_TRANSFORM_REGISTRY` generates with **1** provider (`capped-scission-mediated`,
`transform_provider.py:274`). Recognition is a *downstream demoter* — `recognize_reaction_type` is called only
by `route_reaction_type_blockers` (`reaction_type_oracle.py:580,599`), from `service.py:1664,2242`, on
*already-ranked* steps; it never calls `.enumerate()` and never touches the registry. Of the 20 live families,
1 is a production default, **13 are opt-in providers that never run unless a caller builds a wider registry**,
and **6 lateral families cannot enter the registry seam at all** (see §3). So:

> **Chemistry SmartChem can recognise ≠ chemistry its default planner can generate.**

0.7 closes that gap by making a *certified* provider the unit of the production algebra — without forking the
search, without flipping the global default on reachability alone, and without collapsing the strict-rank and
lateral termination proofs into one recursion.

## 1. Round I inventory (before abstraction)

The machine-readable inventory is committed: `experiments/v0_7_provider_inventory.py` →
`experiments/RESULTS_v0_7_provider_inventory.md`. LIVE columns (id/version/witness/in_default/manifest) are
read from instantiated providers; the rest are source-cited. Summary
(`providers_live=14 in_default=1 opt_in=13 lateral_only=6 oracle_recognizers=17`):

- **Generator + provider + DEFAULT (production-live):** `capped-scission-mediated` (backs the 3 dehydrative
  condensation recognizer classes).
- **Generator + provider, OPT-IN:** 8 Diels–Alder families (`diels_alder.py`), `heterolytic-scission`,
  `redox-half-reaction`, `redox-displacement`, `bond-order-edit`, `audited-capped-scission`.
- **Generator, NO provider possible (registry-excluded, W1):** the 6 lateral families (4 sigmatropic +
  2 electrocyclic, `lateral_rewrite.py`). `LateralRewriteEdge.forget()` raises by design; strict-rank descent
  (`decompiler.py:342`, `product.rank >= reactant.rank → raise`) makes a rank-flat isomerization unsound inside
  the recursive search. They live in `lateral_search.py`'s standalone bounded BFS.
- **Opt-in but the oracle does NOT recognise it:** `heterolytic-scission`, `redox-half-reaction`,
  `redox-displacement`, `bond-order-edit`. Widening the default with one of these would make the oracle demote
  every resulting route as "unrecognized reaction type" though a certified provider generated it. **This is a
  first-class admission-contract requirement (§2.4): a family may not enter the production algebra until an
  independent class recognizer exists for it, or the demoter is made class-aware in lockstep.**

## 2. The production-provider admission contract (design)

A family must not enter the production algebra merely by subclassing `TransformProvider`. The contract requires
evidence equivalent to the following; each maps to existing machinery where it exists, and names the gap where
it does not:

1. **Generation witness** — a real structural rewrite/match. *Have:* `enumerate_transforms → (transforms,
   complete)`; each transform exposes `reactant/reagents/products/forget()/equation()/digest`.
2. **Conservation / representation guards** — *Have:* `ExperimentStep.__post_init__` builds a conservation cert
   and refuses non-conserving steps; the DA edge self-verifies conservation **and** DA-ness (a mass-balancing
   non-DA edge is refused — `test_diels_alder.py:162`).
3. **Rule/provider identity strong enough that changing the semantic rule cannot leave the grammar identity
   unchanged unnoticed** — *GAP (§4).* Today identity = a hand-declared `(id, version, capability_manifest)`
   hashed by `registry.digest`; the honor-system bump is undefended (`transform_registry.py:13-19` W3). This is
   the round's central hardening target.
4. **Reaction-class witness** derived from the applied rule or re-derived from endpoints — *Have (partial):*
   `reaction_type_oracle.recognize_reaction_type` re-derives the class from endpoints for the 8 DA + 6 lateral +
   3 condensation classes; **absent** for redox/heterolytic/bond-order (see §1). Admission requires the family's
   generated step to be class-vouched, so an opt-in family with no recognizer is inadmissible to the *default*
   until one exists.
5. **Independent / redundant verification** — *Have (pattern):* `AuditedCappedScissionProvider`
   (`rule_calculus_bridge.py:158`) overlays an independent replay via `rule_calculus.apply/verify` and fails
   closed. The admission contract adopts this "generator + independent verifier" shape as mandatory for a
   default-eligible family.
6. **Declared directionality / reversibility scope** — *Have:* manifests carry `state_domain` /
   `chemical_authority` (e.g. DA: `neutral-empty-state-carbocyclic-only`, `structural-type-validity-only-problem-A`).
7. **Termination / search-topology compatibility** — *Have:* strict-rank families satisfy the `decompiler.py:342`
   descent; lateral families are structurally excluded (W1) and must NOT be forced into the registry (§3).
8. **Provider-local completeness propagated into aggregate completeness** — *Have:* `registry.enumerate`
   completeness = AND of provider completenesses (`transform_provider.py:252-268`); a provider hitting its budget
   makes the aggregate incomplete.
9. **Hostile near-misses** — *Have (per family):* e.g. DA guard-2b kills the enone→ketene false-vouch
   (`test_diels_alder.py:199`). Admission requires a committed adversarial corpus per family.
10. **Fresh holdout** — a set assembled after the family's design stabilised.

**Admission verdict (this round):** the alkene Diels–Alder family satisfies 1,2,4,5,6,7,8,9 and has fuzz/
holdout coverage; its only shared gap is (3), the grammar-identity honor system, which is common to *all*
providers. So it is a sound **forcing vertical** (§5) while (3) is the round's design target (§4).

## 3. Lateral chemistry stays separate (not a regression to fix — a proof boundary)

0.7 does **not** force Cope/Claisen/electrocyclization into the strict atom-rank descent. PR #88 established the
reason: `LateralRewriteEdge.forget()` raises, and the descent's `product.rank >= reactant.rank → raise` (W1)
makes a rank-flat isomerization unsound in the recursive route search. 0.7 may later define
*orchestration/composition* between strict-descent search and bounded lateral closure (`lateral_search.py`),
but their **termination proofs and completeness receipts remain distinct**. A unified UX does not imply one
recursion. This is scope for a later 0.7 sub-round, explicitly not this one.

## 4. Strengthening grammar identity (the central hardening target)

**Problem (measured):** `TransformProvider.identity = (provider_id, provider_version, capability_manifest)` —
three hand-authored values (`transform_provider.py:94-96`); `registry.digest` SHA-256's *that declared
metadata*. Nothing checks the manifest against the actual rewrite body. A developer who changes
`retro_da_disconnections`'s logic without bumping `provider_version` produces a **byte-identical digest for a
semantically different grammar** — a silent algebra change that route receipts (`search_algebra_digest`) would
misname. Meanwhile `rule_calculus.py` *already* computes real content digests over rewrite structure
(`BondGraph.digest`/`BondRule.digest`, lines 82-83/149-150) — but those are **disconnected** from provider
identity.

**Strategy (design; prototype next sub-round):** give a provider a **rule-descriptor content digest** that
necessarily changes when the structural rule changes, and fold it into `identity` alongside the declared
version (which still tracks implementation/schema changes):

`identity = (provider_id, provider_version, capability_manifest, rule_content_digest)`

where `rule_content_digest` is derived from a *declarative* descriptor of the family's rewrite — for families
already expressible as `rule_calculus` rules, the existing `BondRule.digest`; for imperative enumerators, a
generated descriptor (e.g. the family's canonical retro-pattern / centre signature) whose digest is a function
of the actual match, not a hand-typed string. Goal (verbatim from the round contract): *a developer cannot
alter the actual chemistry rule while forgetting to bump an unrelated hand-maintained version token and still
receive the same transform-algebra identity.* We do **not** hash Python source text for ceremony — a smaller
semantic representation is preferred where one exists.

**Open sub-question (to resolve before wiring):** does any downstream consumer already cross-check the declared
manifest against the rule body end-to-end (`compilation_ir.py` receipt stamping)? The recon believes the gap is
open and undefended but did not trace every `registry.digest` consumer; the admission contract must either close
it or accept-it-as-scope explicitly. **Tests to add:** a "semantic grammar identity" test that mutates a family's
rewrite and asserts the identity/digest MOVES (today it would not — that is the calibrated failure this target
fixes).

## 5. First forcing vertical (alkene Diels–Alder, non-default candidate registry)

Chosen on evidence (§2 admission verdict), not because it is the obvious one. Build a **non-default** candidate
registry `TransformProviderRegistry((CappedScissionProvider(), DielsAlderProvider()))` and prove, through the
UNCHANGED `search_routes`/`search_dags` shell, the eight properties:

1. a target unreachable under capped-scission-only becomes reachable under the wider algebra
   (cyclohexene `C1CC=CCC1` → butadiene + ethylene; the default finds 0 routes);
2. the generated step is vouched by independent/re-derived class evidence (oracle class 4, DA-ness cert);
3. no unrelated existing route changes when the wider family is inapplicable;
4. search receipts bind the actual algebra (`search_algebra_digest` differs for the wider registry);
5. aggregate completeness cannot become falsely complete;
6. hostile near-misses stay absent/demoted (the enone→ketene false-vouch stays empty);
7. a fresh holdout works;
8. all existing default behaviour remains byte/semantic stable until the wider registry is deliberately selected.

Committed as `experiments/v0_7_forcing_vertical.py` (+ `RESULTS_...md`) and pinned by
`tests/test_v0_7_forcing_vertical.py`. **The global `DEFAULT_TRANSFORM_REGISTRY` is NOT flipped** — reachability
is demonstrated with an explicitly-selected registry; promotion toward a production default is a later step
gated on the admission contract (esp. §4).

## 6. Measurement — the 0.7 funnel extension

Extend the 1.0 funnel after v0.6's identity stages with the generative stages, on a predeclared benign corpus:

`structure represented → transform family enumerated → reaction type vouched → route reaches terminal set`

recording before/after denominators under DEFAULT vs the candidate registry. Success is judged on the corpus
denominators, never one showcase target.

## 7. Non-goals (this round)

Reaction family #18; forcing lateral families into the strict recursion (§3); flipping the global default;
a new retrosynthesis engine; MaterialBucket/formulation (0.9); procedure evidence (0.8); a ΔG→bench-capability
gate; any version bump.

## 8. Round I status & ledger

- **Done:** the machine-readable inventory (§1), this plan (§2–§7), the forcing vertical (§5) + its tests, the
  0.7 funnel extension (§6), ROADMAP 0.7 status.
- **Next sub-round (highest-value):** grammar-identity content digest (§4) — add the failing "semantic identity"
  discriminator first (mutate a rewrite, assert the digest MUST move), then wire `rule_content_digest` into
  `TransformProvider.identity`, starting with the audited-capped and DA families that already have structural
  descriptors. This is the single change that turns "opt-in provider" into "certified production-eligible
  grammar", because without it the admission contract's requirement #3 cannot be honestly met.
- **Then:** class-recognizer coverage for redox/heterolytic/bond-order (admission requirement #4) before any of
  them is considered for the default; and the strict/lateral orchestration seam (§3) with distinct receipts.
