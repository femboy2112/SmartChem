# SmartChem 0.7 — Production Chemical Algebra, Round II (decision record)

**Date:** 2026-09-27 · **Branch:** `feat/v0.7-production-chemical-algebra` (off `main@9798ed3`)
· **Gate:** 0.7 in the finite 1.0 ladder. · **Version policy:** see §9 (promotion/version verdict).

Round I *demonstrated* a wider transform algebra in an experiment harness. Round II turns it into a real, typed,
selectable **compiler capability**: content-bound provider semantics, use-indexed admission, a closed request-level
algebra profile, and an end-to-end selectable certified route algebra through the actual
`plan/recompile → service → search → IR → response` path. This is production `smartchem/` work, not another
probe-only round.

## 1. Course-Correction 1 — provider admission is USE-INDEXED

`ProviderUse` (`transform_provider.py`) = {`STRUCTURE_DECOMPILE`, `LINEAR_ROUTE`, `CONVERGENT_DAG`} (values coincide
with the receipt topology strings). Each provider declares `supported_uses`; a consumer validates its registry with
`assert_registry_supports_use(registry, use)` **before enumeration**, raising `UnsupportedProviderUseError`.

This is not cosmetic. Wave-A Lane B measured that a wrong-lane provider on the pre-0.7 code did **not** fail
gracefully: it enumerated cleanly (the registry even reported `complete=True`), then crashed DOWNSTREAM (step-build /
conditions-lookup / witness dispatch), taking the other providers' valid candidates down with the whole call. So the
guard is a real safety property, and silently *filtering* the bad provider would be the other lie (a receipt naming a
caller-selected algebra while a hidden subset ran). Measured, honest use table:

| provider | STRUCTURE_DECOMPILE | LINEAR_ROUTE | CONVERGENT_DAG |
|---|---|---|---|
| capped-scission (+audited) | ✓ | ✓ | ✓ |
| bond-order-edit | ✓ | ✓ | ✓ (not profile-admitted: no oracle recognizer) |
| 8 Diels-Alder families | — (no `_WITNESS_PROJECTION` entry) | ✓ | ✓ |
| heterolytic-scission | ✓ | — (charged, crashes route recursion) | — |
| redox-half-reaction | ✓ | — | — |
| redox-displacement | ∅ (double-broken today — ledger §10) | — | — |

The declared use-set enters provider identity (§3), so a change to it moves the semantic digest.

## 2. Course-Correction 2 — SEARCH TOPOLOGY split from TRANSFORM ALGEBRA

`service.TransformGrammar` conflated the two (its members are `FORMULA_DECOMPOSITION` /
`CAPPED_SCISSION_LINEAR` / `CAPPED_SCISSION_CONVERGENT` — a topology axis with one algebra hard-baked into the name).
Round II keeps `transform_grammar` as the **topology** axis (wire-compat) and adds an orthogonal request field
`algebra_profile` as the **algebra** axis. A closed, versioned profile registry (`smartchem/algebra_profiles.py`)
maps a stable ID to an exact provider registry — never a dynamic import from a deserialized string:

- `legacy-capped-v1` → `(CappedScissionProvider,)` — byte-identical to `DEFAULT_TRANSFORM_REGISTRY` (verified: same
  `.digest`). This is the default (`DEFAULT_ALGEBRA_PROFILE`); the default is **not** flipped.
- `certified-route-v07` → `(CappedScissionProvider, + the 8 admitted Diels-Alder families)` in deterministic order.
- `certified-decompile-v07` → `(HeterolyticScissionProvider, RedoxHalfReactionProvider)` — a certified
  structure-decompile-only algebra (the two decompile-only families that are fully IR-wired; §8).

The request's `semantic_digest` folds the **resolved registry digest** of the profile, so the search identity moves
when the algebra changes (the pre-0.7 gap: identity was frozen to one algebra, so "equal digest ⇒ same search" was
only accidentally true). An unknown/incompatible profile is a typed refusal at construction, never a `KeyError`.

## 3. Semantic provider identity — built, and NOT overclaimed

`ProviderSemanticDescriptor` (frozen; `.digest`) binds `family, supported_uses, witness_kind, projection_kind,
behavior_params, structural_rule_digest, guard_spec_digest, authority`, and is folded into
`TransformProvider.identity` (now a 4-tuple: `(id, version, manifest, descriptor.digest)`).

For the Diels-Alder families the descriptor carries **real** content: `structural_rule_digest = retro_rule.digest`
(the declarative `BondRule` content digest) and `guard_spec_digest = DAGuardSpec.digest`.

**Epistemic boundary (deliberate):** the digest GUARANTEES that a change to a *declarative* rewrite rule, a typed
guard policy, the supported-use set, the witness/projection kinds, or a typed knob **forces** an identity change. It
does **not** and cannot detect an arbitrary edit to *imperative* enumerator Python (the capped-scission
cut-selection body, a verifier's own logic); for those, `structural_rule_digest`/`guard_spec_digest` are `None` and
the honest tracker is `provider_version` + tool/schema versioning. No source text is hashed for ceremony.

Note: the plan v0.1 §2/§4 cited `transform_registry.py:13-19` for the honor-system identity; the true site is
`transform_provider.py:94-96` (`TransformProvider.identity`). Corrected here.

## 4. DA guard semantics — one shared spec, consumed (no drift)

Wave-A Lane A found that the DA rule IS declarative (a `_FORWARD` `BondRule`), but the guards that make it *sound*
lived OUTSIDE it as module constants: guard 2c (`_NEUTRAL_VALENCE`), guard 2b (exocyclic-order, hard-coded `!= 1`),
and guard 5's diene/dienophile partition (`_DIENE`/`_DIENOPHILE`). A relaxation of any of those changed the chemistry
while leaving the hand-declared identity byte-identical. So a `BondRule.digest` alone is necessary but **insufficient**.

`DAGuardSpec` (frozen; `retro_rule, forward_rule, class_label, diene_vertices, dienophile_vertices, neutral_valence,
exocyclic_max_order`; `.digest`) is now **consumed by** `_guarded_retro` (one enforcement point, no second metadata
copy that can drift), and its digest rides the provider's semantic descriptor. `retro_signature` is derived from the
rule inside `_guarded_retro`, so a hand-edited rule can never carry a stale signature. Behaviour is byte-preserved
(the `!= 1` → `> exocyclic_max_order` swap is identical for bond orders ≥ 1); **132 DA tests pass unchanged**.

Calibrated (v0_7_mutation_calibration M1/M2): mutate the rule → digest moves; mutate a guard setting → digest moves;
prose-only manifest change → digest stable; identical construction → stable.

## 5. Provenance honesty — generator vs verifier (Round-I terminology corrected)

Wave-A Lane F traced the DA "three independent witnesses" claim and found it is, at runtime, **one code path**:

| check | what it is | honest classification |
|---|---|---|
| generator | `retro_da_disconnections → _guarded_retro` | the thing being checked |
| oracle "Layer A" | `_reactant_da_disconnects_to` → **re-calls** `retro_da_disconnections` | FRESH RE-DERIVATION (shared family code — NOT independent) |
| oracle "Layer B" | `step.reaction_center == _DA_CENTER` | a **tautology** for DA-generated steps (`reaction_center()` hard-returns `_DA_CENTER`) |
| `verify()` + `independently_reconstructs` | no `apply()`, replays a pair→order table | REPRESENTATION-DIVERSE VERIFIER (algorithm-diverse, but keyed on the SAME rule object) |
| SMILES ground truth | `tests/test_diels_alder.py` | the only PROVENANCE-INDEPENDENT source — **offline, not on the hot path** |

Honest count: **~one-and-a-fraction** independent runtime witnesses, not three. Single point of failure: the
hand-typed `_FORWARD` `BondRule` literal per family (a bond-order typo propagates to generator + both "witnesses" and
they all agree; only the offline SMILES test catches it). Round I's "independent re-derived class witness" wording
overstated this and is retracted: it is a *fresh re-derivation through shared code*, valuable but not independent
evidence. This is diagnostics, not a probability score.

## 6. The forcing consumer — the selected algebra reaches the REAL service

`run_compilation` now resolves `request.algebra_profile → registry` and threads that exact registry through
`search_routes`/`search_dags` **and** `recompile_to_ir`. A **binding invariant** refuses packaging unless
`search_result.receipt.transform_registry_digest == search_algebra_digest(topology, resolved_registry)` — a
profile-A search can never be packaged/replayed as profile-B. Serialization round-trips `algebra_profile`
(back-compat via `.get`); a tampered/unknown profile fails closed on deserialize. `--algebra <profile>` is exposed on
`recompile` and `plan`; `--emit-request`/`--json` carry the selection.

Reagent handling is now algebra-aware: an empty helper pool is refused only when NO provider in the selected algebra
is reagentless-capable — `legacy-capped-v1` + empty → refused (exit 2, no invented water); `certified-route-v07` +
empty → runs (DA is reagentless). Verified through the real service: cyclohexene → butadiene + ethylene, reagentless,
`exit 0`, while the default stays `exit 3`.

## 7. Admitted DA families (Wave-A Lane D audit, live-probed)

All eight strict-rank DA families pass the admission contract (reqs 1,2,4,5,6,7,8,9; req-3 identity is what §3/§4
closed): all-carbon **alkene** + **alkyne**, hetero-dienophile **aza/oxa/thia**, hetero-diene **aza/oxa/thia**. Each
generates, is conservation+DA-ness self-certified, oracle-recognized as its own class, strict-rank compatible, with a
committed hostile near-miss. Order in the profile is not load-bearing (transform digests are class-tagged). Coverage
asymmetry recorded: the 6 hetero families have an exhaustive ring-space fuzzer; the 2 all-carbon families have
hand-picked hostile corpora + fresh holdouts (see the forcing corpus). `AuditedCappedScissionProvider` is
deliberately **excluded** from `certified-route-v07`: it emits byte-identical capped transforms and would fully
shadow `CappedScissionProvider` under first-provider-wins.

## 8. Structure-decompile lane + lateral lane

`certified-decompile-v07` is a certified STRUCTURE_DECOMPILE-only profile of the two charged families that are fully
IR-wired (`_WITNESS_PROJECTION` + independent-recompute): `heterolytic-scission`, `redox-half-reaction`. The use-guard
makes it a negative control: `search_routes` refuses it, `decompile_structure_to_ir` accepts it. **`redox-displacement`
is excluded** — its multi-species edge has no `_WITNESS_PROJECTION` entry (it fails loud, never silent), a bounded
decompile-lane ledger item, not fixed this round. The **lateral** families stay a separate bounded search by theorem
(`LateralRewriteEdge.forget()` raises); Round II derived, but did not implement, the orchestration contract: an
orchestrator ABOVE both engines carrying independent artifacts/receipts, with a NEW cross-seam visited-set + a
seam-crossing (alternation) budget that must have its own termination proof — folded into neither `decompiler.py:342`
nor the lateral budgets.

## 9. Measurement, mutation gate, hostile review

- **Generative funnel (low-level, Round-I)**: DEFAULT `6/1/1/1` vs candidate `6/4/2/2` (family/vouched/terminal).
- **Production-service funnel (Round II, through `run_compilation`)**: `legacy-capped-v1` `4/1/1` vs
  `certified-route-v07` `4/2/2` (structure / family-enumerated / terminal); the DA target's `search_receipt_digest`
  differs between profiles (the algebra is bound into the receipt). Proof the improvement is in the real compiler.
- **Forcing corpus (8 families + hostile near-misses + fresh holdouts)**: `experiments/v0_7_forcing_corpus.py` →
  **52/52 properties hold** — every one of the 8 admitted families fires its own `DIELS_ALDER*` witness under
  `certified-route-v07`, is class-vouched, and does not cross-poach; the hostile block (enone / saturated ring /
  benzene) emits zero DA witnesses under both registries; two fresh SUBSTITUTED all-carbon holdouts
  (`CCC1CCC=CC1`, `CC1=CCC=CC1`) fire while the default stays silent (`tests/test_v0_7_forcing_corpus.py`, 5 tests).
- **Calibrated mutation gate**: `experiments/v0_7_mutation_calibration.py` — **10/10 mutants killed** (rule/guard→id,
  wrong-use refusal, profile-ignored, A-packaged-as-B, tampered profile, reagentless flag, silent default widen,
  class-witness strip, completeness AND-not-OR).
- **Independent hostile review (Wave C, a non-author adversary)**: **clean bill — zero verified breaks** across
  all five surfaces. It confirmed: content-binding moves the identity for every declarative rule/guard edit tried and
  could find no valid degree-preserving silent rewrite; every enumerating consumer path is behind the use-guard; an
  unknown/tampered profile is always a typed refusal (no KeyError, no dynamic import, no silent default); the
  reagentless DA path skips no conservation check and legacy never invents water; no cross-poach, no
  enone/oxocarbenium/thiocarbenium/aromatic false-vouch, no false "complete" under a starved budget, and AuditedCapped
  cannot sneak into the certified route. Three non-break items recorded:
  - **(LOW, verified defer) declaration-trust boundary**: a hand-built provider subclass that LIES about its
    `supported_uses` sails past the guard and crashes downstream as the pre-0.7 code did. Not reachable via the closed
    `ALGEBRA_PROFILES` nor any shipped provider; the guard is honestly a *declared-lane* check (its docstring says so).
    A boundary, not a hole — if provider registration is ever opened to untrusted input, this guard is not the defense.
  - **(residual) `certified-decompile-v07` has no service front door**: service DECOMPILE is formula descent
    (`decompile_to_ir`), not `decompile_structure_to_ir`; service RECOMPILE refuses a decompile-only profile by
    topology-coherence. The profile is LIBRARY-ONLY BY DESIGN, exercised by the use-guard controls and a live
    enumerate positive control (it enumerates 18 real transforms — 16 heterolytic + 2 redox-half — on ethanol, while
    the default capped-only algebra does not). A structural-decompile SERVICE front door is 0.8+ scope (§10).
  - **(residual, deferred) serialized-response cross-profile rebind on load**: the run-time binding invariant is
    airtight, but a *persisted* response's on-load re-derivation of its IR registry digest against the request's
    `algebra_profile` was not exercised (the response carries both, so the information is present for a checker). This
    is the TAMPER-HARDENING arc, orthogonal to the Round-II diff — ledgered for 0.8, no demonstrated failure.

## 10. Ledger & promotion/version verdict

**Remaining 0.7 work (unresolved, recorded):**
- Grammar-identity for *imperative* families beyond the declarative binding (bounded by §3's epistemic boundary).
- Class recognizers for redox/heterolytic/bond-order before any of them is considered for the default.
- `redox-displacement` `_WITNESS_PROJECTION` wiring (multi-species witness fields) for `certified-decompile-v07`.
- A structural-decompile SERVICE front door (today `certified-decompile-v07` is library-only; §9 residual) + the
  charged-fragment IR candidate build (heterolytic/redox-half enumerate 18 transforms on ethanol but the IR
  `StructuralCandidate` layer currently filters them to zero on that target — a decompile-lane detail to verify).
- Serialized-response on-load algebra re-binding (§9 residual) — TAMPER-HARDENING arc (0.8).
- The strict/lateral orchestration seam (§8) with distinct receipts.

**Promotion verdict (Wave C clean; final confirmation gated only on the full OOM-safe suite):** keep
`certified-route-v07` an OPT-IN profile; **do NOT flip the default this round.** Rationale: (1) a default flip is a
deliberate, separately-auditable behavioral change, not something to slip into the round that builds the mechanism —
the mission is explicit; (2) the mission's "certified algebra as the generative spine of NORMAL use" additionally
requires class-recognizer coverage for the non-DA families (redox/heterolytic/bond-order), which is not done, so the
FULL multi-family algebra is not yet default-eligible. The opt-in candidate — content-bound, use-correct, selectable
end-to-end, hostile-clean — is itself a major 0.7 advance.

**Version verdict:** **stay `0.6.0a1`** (no bump). Per the mission's rule, `0.7.0a1` is earned only when the 0.7
contract holds for *ordinary* SmartChem use (the certified algebra as the default spine). The default remains
`legacy-capped-v1`, so the opt-in capability is ready but default promotion is deferred (blocker: the two items
above). This is the mission's explicit "opt-in candidate ready, default promotion blocked → remain 0.6.0a1 + state
the blocker" branch — not a ceremonial bump.
