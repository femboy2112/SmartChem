# SmartChem v0.7.0a1 — Production Chemical Algebra (release decision record)

**Date:** 2026-09-27 · **Branch:** `feat/v0.7-production-chemical-algebra` · **Version:** `0.6.0a1` → `0.7.0a1`
· **Gate in the finite 1.0 ladder:** 0.7 Production Chemical Algebra.

This is the durable release record for the 0.7 line. The mechanism was built across Rounds I–III
(`V0_7_PRODUCTION_ALGEBRA_ROUND_{I,II,III}_2026-09-27.md`); this document records what shipped and the gate that
justified promoting the certified algebra to ordinary use.

## The 0.7 contract (now satisfied)

> SmartChem's normal compiler path uses a typed, content-bound, multi-family production transform algebra; the exact
> algebra is preserved through request, search, completeness receipt, IR, serialization and response; widening
> chemistry is an auditable semantic operation rather than an experiment-only override.

An ordinary `smartchem recompile` / `smartchem plan` request, with **no** `--algebra` flag, now searches the
certified multi-family route algebra. `--algebra legacy-capped-v1` reproduces the pre-0.7 capped-scission-only
behaviour exactly.

## Provider-use theorem

Admission is USE-INDEXED. `ProviderUse` = {`STRUCTURE_DECOMPILE`, `LINEAR_ROUTE`, `CONVERGENT_DAG`}; each provider
declares `supported_uses`, and every enumerating consumer (`search_routes` / `search_dags` /
`decompile_structure_to_ir`) refuses an incompatible registry via `assert_registry_supports_use` **before**
enumeration (closing a measured wrong-lane whole-call crash). Defaults are consequently **use-dependent**: a route
default and a structure-decompile default are not the same registry.

## Semantic identity scope (what the digest binds / does not bind)

Provider identity is `(provider_id, provider_version, semantic_descriptor.digest)` — prose-independent.
`ProviderSemanticDescriptor` (tag `provider-semantic-descriptor-v2`) binds: `family`, `supported_uses`,
`witness_kind`, `projection_kind`, typed `behavior_params` knobs, the declarative `structural_rule_digest` /
`guard_spec_digest` (for the DA families), `authority` (deployment/scope + the replay-verification discipline), and
`reagentless_capable`. **Guaranteed:** a change to any of those — a declarative rule, a load-bearing guard policy, a
supported use, a witness/projection kind, a typed knob, the reagent capability — moves the digest → registry digest →
request semantic digest. **Not bound:** an arbitrary edit to *imperative* enumerator Python (a cut-selection body, a
verifier's own logic); those are tracked by `provider_version` + tool/schema versioning, and no source text is hashed
for ceremony. A `mechanism`-PROSE edit moves nothing.

## The default route profile + exact admitted providers

`DEFAULT_ROUTE_ALGEBRA_PROFILE = "certified-route-v07"` (the flip). The closed profile registry
(`smartchem/algebra_profiles.py`):

| profile | providers | use |
|---|---|---|
| `legacy-capped-v1` | `CappedScissionProvider` | route + DAG + decompile (byte-identical to `DEFAULT_TRANSFORM_REGISTRY`) |
| **`certified-route-v07`** (default route) | `CappedScissionProvider` + the 8 Diels-Alder families | route + DAG |
| `certified-decompile-v07` | `HeterolyticScissionProvider`, `RedoxHalfReactionProvider` | structure-decompile (library) |

The 8 admitted DA families: all-carbon **alkene** + **alkyne**; hetero-dienophile **aza/oxa/thia**; hetero-diene
**aza/oxa/thia**. Each is generated, conservation- and DA-ness self-certified, oracle-recognised as its own class,
strict-rank compatible, with a committed hostile near-miss and a fresh post-freeze holdout.

## Excluded providers + reasons

- `AuditedCappedScissionProvider` — emits byte-identical capped transforms; would fully shadow `CappedScissionProvider`
  under first-provider-wins, adding nothing to the route algebra.
- `BondOrderEditProvider` — route-capable but has no reaction-type oracle recognizer, so it is not admitted to a
  vouched route profile (future work to admit it).
- `HeterolyticScissionProvider`, `RedoxHalfReactionProvider` — `STRUCTURE_DECOMPILE`-only (charged; crash route
  recursion), so they belong to `certified-decompile-v07`, not the route default.
- `RedoxDisplacementProvider` — `supported_uses = ∅` (its multi-species edge has no `_WITNESS_PROJECTION` entry yet);
  fail-closed, inadmissible everywhere. A 0.8 decompile-lane item.

## Forcing / holdout / promotion corpus

- Forcing corpus: **52/52** properties across all 8 families + hostile near-misses + holdouts.
- Fresh post-freeze holdouts: one per family (8), designed by a non-author adversary, canonically distinct from every
  committed fixture — each fires exactly its own witness, no cross-poach, default silent, oracle-vouched.
- Default-promotion blast radius (`experiments/v0_7_promotion_blast_radius.py`): 22 corpus + 3 co-ranking targets
  through the real `run_compilation`. **0 unacceptable deltas, 0 to inspect, 2 NOTABLE (allowed).** No legacy route
  lost (exercised non-vacuously on the co-ranking targets), every non-DA target byte-identical, every new certified
  step oracle-vouched (all-steps guard), no top-1 eviction. NOTABLE: certified can honestly downgrade a *complete*
  search to *incomplete* (exit 4) at the default `cut_budget` on a DA-ring-bearing target — the legacy route is
  preserved; higher bounded work honestly reported, the reverse of the forbidden false-COMPLETE.

## Performance delta (certified vs legacy, same corpus)

Wall-clock: legacy median ~12ms / certified median ~18ms; p90/p95 essentially equal (dominated by a few heavy
aromatic litmuses, unchanged under both); worst per-target slowdown **3.95×**; transforms-considered max **458**
unchanged. No pathological explosion. No chemistry was narrowed to gain speed.

## Mutation gate + hostile review

- Calibrated mutation gate: **17/17 killed** (`experiments/v0_7_mutation_calibration.py`).
- Independent Wave-C hostile review: **no verified product break** on any closed hole; its evidence-coverage findings
  (F1 empty-set blast radius, F2 first-step-only fiction guard, F3 bare `--reagents` silent-resolve) are all closed.

## Remaining boundaries (0.8+)

- The guard-2c whole-fragment-neutral DA boundary (a structurally-matched-but-fictitious disconnection the oracle
  still vouches) is a pre-existing boundary, unchanged; it rides into the default consciously, not a 0.7 regression.
- The response algebra-rebind guard is internal semantic coherence, not authentication; a fully-controlling forger is
  the `producer_signature` / `expected_request_digest` threat model.
- Admitting non-DA families to a route profile needs reaction-type recognizers (redox/heterolytic/bond-order).
- `redox-displacement` `_WITNESS_PROJECTION` wiring; a structural-decompile SERVICE front door
  (`certified-decompile-v07` is library-only); the certified default's completeness at the default budget (the NOTABLE
  exit 0→4 tradeoff) may warrant a budget that scales with algebra width.

## Full suite

OOM-safe full suite, rdkit absent: green. (The authoritative post-promotion count is recorded in the merge PR.)
