# SmartChem 0.7 — Production Chemical Algebra, Round III (closure + promotion decision record)

**Date:** 2026-09-27 · **Branch:** `feat/v0.7-production-chemical-algebra` (off `main@9798ed3`)
· **Gate:** 0.7 in the finite 1.0 ladder — CLOSE the residual semantic holes, measure the default-promotion blast
radius, and promote `certified-route-v07` to the normal route algebra *iff* the gate survives.

Round II built the selectable, content-bound, use-indexed multi-family route algebra as an **opt-in** capability and
deferred the default flip. Round III closes the residual holes that made the flip unsafe, measures the blast radius
of the flip, and — the gate having closed — promotes the certified algebra to the default in a separate commit. The
promotion + version bump are recorded here; the durable release record is
`V0_7_PRODUCTION_CHEMICAL_ALGEBRA_RELEASE_2026-09-27.md`.

## 1. Reagent policy is now identity-bearing (§1A)

`TransformProvider.reagentless_capable` gates whether an empty helper-reagent pool is a runnable search or an
`INVALID_INPUT` refusal (`service.py` `_run_recompile`, the single production read). Round II left it **out** of
`ProviderSemanticDescriptor`, so two registries differing only in this flag accepted/rejected the same empty-pool
request differently yet carried a **byte-identical digest** — a leak in the one-way "equal digest ⇒ same executed
search" law. Round II's docstring called it "deliberately NOT part of identity"; that was wrong (it conflated the
request-time fact of *which reagent is on hand* with the family-structural fact of *whether the family can run
reagentless*, which is intrinsic and gates whether a search executes at all). Fixed: `reagentless_capable` is a field
of `ProviderSemanticDescriptor` (schema tag bumped `provider-semantic-descriptor-v1` → `-v2`), populated once in the
base `semantic_descriptor` builder (so all 8 DA families inherit it via `_da_semantic_descriptor`'s `replace`). A flip
now moves the descriptor digest → identity → `registry.digest`. Calibrated: mutant **M11**.

## 2. Provider identity is now PROSE-INDEPENDENT (§1B)

Round II identity was `(provider_id, provider_version, capability_manifest, semantic_descriptor.digest)` — the raw
manifest (carrying human `mechanism` prose) sat in slot 2, so a **spelling edit** moved `registry.digest`. Round III
drops the manifest from identity: it is now `(provider_id, provider_version, semantic_descriptor.digest)`. A full
manifest census (Wave-A) classified every key on every provider as semantic / authority / presentation-prose and
proved that dropping the manifest loses **no** behaviour-bearing field, with one exception: `AuditedCappedScission`'s
`structural_replay` tag (a verification-discipline declaration) was the one load-bearing string key neither
prose-dropped nor name-extracted. Rather than accept the loss, it is folded into the descriptor's `authority`
field, so a relabel still moves the digest. Result: a `mechanism`-prose edit moves **nothing**; every load-bearing
edit (typed knob, supported-use, witness/projection, rule/guard, reagent policy, `structural_replay`,
`provider_version`) moves the identity. Calibrated: mutants **M1, M2, M11, M12**; discriminator tests in
`tests/test_v0_7_production_algebra.py`. The imperative-enumerator-body blind spot is unchanged and still tracked by
`provider_version` (the descriptor docstring's stated epistemic boundary).

## 3. Frozen wire-migration law (§5) — decoupled from the promotable default

Three constants with distinct meanings, all `"legacy-capped-v1"` this round (`algebra_profiles.py`):
- `DEFAULT_ALGEBRA_PROFILE` — the conservative low-level default (raw `CompilationRequest` field default; the profile
  a DECOMPILE request is pinned to). **Stays legacy across promotion.**
- `LEGACY_MISSING_ALGEBRA_PROFILE` — a LITERAL: what a pre-0.7 serialized request with **no** `algebra_profile` field
  historically meant. `request_from_payload` maps a missing field to THIS, **forever**, decoupled from the build
  default, so promotion can never silently reinterpret an old payload as the wider algebra.
- `DEFAULT_ROUTE_ALGEBRA_PROFILE` — the route/DAG **build** default the SERVICE/CLI front door stamps. This is the ONE
  constant the promotion commit flips.

Calibrated: mutant **M16** (a missing-field payload stays legacy even with `DEFAULT_ROUTE_ALGEBRA_PROFILE` patched to
certified). This ordering is mandatory: the migration law had to land **before** the promotion.

## 4. `certified-decompile-v07` is a live algebra on an empty pool (§3)

`decompile_structure_to_ir` refused `reagents=()` before enumeration (`or not reagents`), which is wrong for a
reagentless-only algebra. An empty reagent tuple is a legitimate declared set; the clause is dropped (genuinely-wrong
types — `None`, a list, non-Molecule elements — are still refused). PROBED and CONFIRMED live: on ethanol,
`certified-decompile-v07` enumerates **18** transforms `{HETEROLYTIC_SCISSION, REDOX_HALF_REACTION}` and materialises
**18** `StructuralCandidate`s (1:1), **all 18 reconstitute** (`reconstitute_parent()`), and the IR serialises →
deserialises with digest equality. (Round II §10's worry that the candidate layer filtered to zero on ethanol is
**refuted** by the filesystem — the candidates are live.) The strengthened positive test replaces the old
"did-not-raise-with-water" check. Calibrated: mutant **M14**.

## 5. Response algebra-rebind is refused on LOAD (§4)

The runtime binding invariant proves a search ran under the selected algebra at PRODUCE time, but a transported
`CompilationResponse` independently deserialises its request, IR digest, and receipt digest. `response_from_payload`
now re-derives, for a RECOMPILE response carrying an IR:
`ir.transform_registry_digest == ir.search_receipt.transform_registry_digest == search_algebra_digest(topology,
resolve(request.algebra_profile))`, refusing any mismatch. The IR's own `__post_init__` already forced the first
equality; the missing leg (both vs the algebra the *request* names) is closed here. This is internal semantic
coherence, NOT cryptographic authentication — a fully controlling forger who rebuilds a self-consistent response is
the `producer_signature`/`expected_request_digest` threat model, unchanged. Verified layering: a *naive* tamper is
caught by the pre-existing round-trip `result_digest` check; a *coherent* cross-profile rebind (result_digest
recomputed) is caught only by this new guard. Calibrated: mutant **M15**; tests in `test_v0_7_transport_algebra.py`.

## 6. The human CLI can express an empty helper pool (§2)

`--no-helper-reagents` (on `recompile`, `compile`, and `plan`) declares an explicit empty pool: the emitted request
carries `helper_reagents=[]` with **EXPLICIT** origin; omitted/bare `--reagents` stays the water **DEFAULT**; an
explicit non-empty `--reagents` stays as declared. It is mutually exclusive with **any** `--reagents` (Wave-C F3: even
a bare empty `--reagents`, so the empty pool is never a silent override — one loud choice). The service already
supported `helper_reagents=()` with EXPLICIT origin, so this is a CLI-only fix; the legacy `compile` dossier's
empty→water re-injection is gated (`default_reagents_when_empty`) so it does not silently re-water an explicit empty
pool. Verified end-to-end: `recompile --algebra certified-route-v07 --no-helper-reagents` runs the reagentless DA
search (exit 0); legacy + empty pool fails closed (exit 2). Calibrated: mutant **M13**.

## 7. Fresh post-freeze holdouts, one per DA family (§6)

An independent (non-author) adversary designed and live-verified one genuinely-fresh substituted holdout for **each**
of the 8 admitted families, canonically distinct from every committed fixture (dedup by
`canonical_digest(Molecule.canonical())`, not string diff — ring symmetry aliases spellings): `CC1=CCCCC1`,
`C1=CC(C)C=CC1`, `CC1C=CCCN1`, `CC1C=CCCO1`, `CC1C=CCCS1`, `N1C=CCC(C)C1`, `O1C=CCC(C)C1`, `S1C=CCC(C)C1`. Each fires
**exactly** its own witness kind, no sibling cross-poach, default silent, oracle-vouched. Tests in
`test_v0_7_forcing_corpus.py`. Calibrated: mutant **M17**.

## 8. Re-adjudicated 0.7 blockers under the use-index (§7)

Round II §10 listed "class recognizers for redox/heterolytic/bond-order" as a blocker to default promotion. Under the
use-index this was a conflation: heterolytic and redox-half are `STRUCTURE_DECOMPILE`-only, bond-order-edit is
route-capable but **not** admitted to `certified-route-v07`. `certified-route-v07`'s route members are exactly
capped-scission (the legacy default) + the 8 DA families (all oracle-recognised). **None** requires a non-DA route
recognizer for the ROUTE default to be sound. Confirmed empirically by the blast radius (every certified route is
oracle-vouched; every non-DA target is byte-identical). The non-DA recognizers remain future work for admitting
those families to a route profile — not a blocker to promoting the DA route algebra.

## 9. Default-promotion blast radius + performance (§8/§9)

`experiments/v0_7_promotion_blast_radius.py`, predeclared corpus of 22 targets + 3 co-ranking targets, driven through
the real `run_compilation`; only `algebra_profile` varies. Result: **0 unacceptable deltas, 0 to inspect, 2 NOTABLE
(allowed/documented)**.
- Every **legacy route preserved** (`legacy_route_digests ⊆ certified` on every target). Exercised NON-VACUOUSLY on
  the co-ranking targets (Wave-C F1) — ester/amide-on-cyclohexene, where a legacy capped route and certified DA
  candidates co-exist with stock present.
- Every **non-DA target byte-identical** under both profiles (same exit + same route set).
- Every **new certified step oracle-vouched** (Wave-C F2: the fiction guard checks *every* step, not just the first).
- **No false COMPLETE**, **no top-1 eviction** (`max_routes=1` probe preserves legacy's top route), **no runtime
  explosion** (worst per-target slowdown 3.95×; certified median 18ms vs legacy 12ms; transforms-considered max 458
  unchanged).
- **2 NOTABLE (allowed) deltas**: certified can honestly downgrade a *complete* legacy search to *incomplete* (exit
  0→4) on a DA-ring-bearing target, because the wider union enumerates more and hits the default `cut_budget`. The
  legacy route is **preserved**; this is the reverse of the forbidden false-COMPLETE — higher bounded work honestly
  reported, not a soundness loss. Documented as the promotion's cost; a follow-up may scale the default budget.

Stocked promotion demo: cyclohexene + stock(butadiene, ethylene) → legacy `NO_ROUTE` becomes a certified,
class-vouched DA route — exactly the promotion's benefit.

## 10. Mutation gate + hostile review

- Calibrated mutation gate `experiments/v0_7_mutation_calibration.py` — **17/17 killed** (M1–M10 Round II; M11–M17
  Round III: reagent-policy binding, prose-independence, CLI empty-pool, decompile empty-pool, response
  algebra-rebind, frozen missing-field law, fresh-holdout absence). M8 was re-pointed at `DEFAULT_ROUTE_ALGEBRA_PROFILE`
  (the promotable build default) — its surviving the old patch confirmed the §5 decoupling took effect.
- **Wave-C hostile review (a non-author adversary): no verified product break** on any of the seven closed holes. Its
  findings were all in the promotion *evidence*, not the code: **F1** (the blast radius rested partly on empty route
  sets) → closed with the co-ranking corpus + eviction probe; **F2** (fiction guard inspected only `steps[0]`) →
  closed (all-steps guard); **F3** (bare `--reagents` + `--no-helper-reagents` silently resolved) → closed (any
  `--reagents` now conflicts). Residual it noted and could not break: the guard-2c whole-fragment-neutral DA boundary
  is a pre-existing Round-II boundary, unchanged and ridden into the default consciously, not a Round-III regression.

## 11. Full suite

OOM-safe full suite (`scripts/run_suite.sh`), rdkit absent, closure state: **5561 passed / 0 failed / 0 errors / 46
skipped (5607 collected)**. The only goldens that moved were the 5 `cli_json` response fixtures, verified leaf-by-leaf
to be **digest-only** (request/result/transform-registry digests) with **zero** structural/chemistry drift — the
intended one-time consequence of the identity re-canonicalisation (§1/§2) — and regenerated via the repo's own
`regen_cli_json.py`. (A second full-suite pass is run post-promotion before merge.)

## 12. Promotion verdict + version

**Gate CLOSED.** All six semantic holes closed and shell-verified; migration law in place *before* the flip; blast
radius shows zero unacceptable deltas with the "no legacy route lost" invariant exercised non-vacuously; Wave-C clean
(no P0); full suite green; 17/17 mutants. Per the mission's 0.7 exit law, `certified-route-v07` is **promoted to the
default route algebra** (`DEFAULT_ROUTE_ALGEBRA_PROFILE = "certified-route-v07"`) in a **separate, auditable commit**,
with `--algebra legacy-capped-v1` reproducing the old capped behaviour, and the low-level `DEFAULT_TRANSFORM_REGISTRY`
+ the DECOMPILE default left as the explicitly-named legacy registry (defaults are use-dependent). The version is then
bumped to **`0.7.0a1`** (a third commit) — the 0.7 contract now holds for *ordinary* SmartChem use.
