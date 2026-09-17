# POOR_MAN_TAMPER_HARDENING_v0.1

Closing the R59 disposition **serialized-tamper** forgery — the cheap, honest way a gate finding opened up.
No R58 reversal, no route/step hash break.

## The hole (proven)

The section-10.4 affordability frontier is **deliberately excluded** from
`CompilationResponse.result_digest` (a price is dated data, not search identity), and until now no load-time
guard re-derived it. So a hand-edited serialized response could **strip** a frontier entry's `hard_blockers`
(or `fiction_blockers`), and the entry's `Disposition` would flip **up** to a better tier — `REAL_BUT_HARD`
or `NOT_A_REACTION` silently becoming `CLEAN` — with `result_digest` **byte-identical** and every other
coherence gate silent. The disposition *is* the ranking answer (a lower tier dominates cost at any price), so
that is a forged verdict, not a cosmetic edit.

Reproduced live (isopentyl acetate on a kitchen bench with no reflux condenser → the Fischer esterification is
process-`EXCLUDED`, i.e. `REAL_BUT_HARD`):

```
strip affordability_frontier[i].cost_vector.hard_blockers -> []
response_from_payload(tampered, require_verified_admission=True)
```

Before the fix: no exception, `result_digest` unchanged, disposition `CLEAN`. The reviewer's replay command
is `tests/test_poor_man_tamper_hardening.py::test_the_reproduced_hard_tamper_is_refused_on_load`.

## The two incisions

### Piece 1 — `CompilationResponse._check_frontier_coherence` (service.py)

Invoked in `__post_init__` alongside the other `_check_*` methods (so it fires on **every** load, not only
under verified admission). For each frontier entry it **re-derives the same blockers**
`_affordability_frontier` computes, and refuses (fail-closed, one-directional) any entry whose claimed
blockers are **looser** than the re-derivation:

- `hard_blockers` (REAL_BUT_HARD): process exclusions re-derived from the matching summary's digest-covered
  per-step `process_requirements` (the same authority PROCESS-ADMIT-01 uses — no replay needed), **plus**
  `route_catalyst_blockers` over the route reconstructed from the thick `replay_payload`.
- `fiction_blockers` (NOT_A_REACTION): `route_reaction_type_blockers` over that reconstructed route.

Polarity: raise iff a re-derived blocker is **missing** from the claimed tuple. A claim with *extra* blockers
(a worse disposition than reality) is a self-suppression, out of scope — exactly as the process / verified-
admission checks treat hide-good. An honest response is self-consistent (re-derived == claimed) and passes.

Schema bumped `v1alpha13` (descriptor `v1alpha17`): **no field change**, a new on-load refusal — so a
pre-guarantee `v1alpha12` payload is refused by the strict schema-version gate.

### Piece 2 — the reaction-TYPE oracle fails closed on an absent centre

`_acyl_condensation` and `_etherification` now `return False` when `reaction_center is None`, extending the
R60 N-methylation gate finding to all three recognizers. A tamperer who **nulls** `reaction_center` in a
replay payload now gets the step **demoted** (unrecognized → `fiction_blocker`), never census-only vouched —
so centre-omission can only cause false-EXCLUDE (safe), never false-VOUCH (catastrophic). This defuses the
fiction channel **without** digest-binding the centre (no R58 reversal), and en passant closes the
pre-existing acyl/ether centre-absent homologation debt Evil-Morty flagged. It is the same
whole-set-count non-locality lesson: a census over the whole molecule can be forged by a homologation that
migrates a group; only a readable elementary centre is trustworthy.

The sharp case: a k=2 bundle the **census** vouches but the **span** demotes. With its centre nulled, the
census alone would vouch it (pre-hardening) — now it fails closed. That is the exact evasion Piece 2 shuts.

## What is closed, and the residual (stated, not hidden)

Closed on load:

- REAL_BUT_HARD → CLEAN (`hard_blockers` strip) — the proven hole.
- NOT_A_REACTION → CLEAN (`fiction_blockers` strip), and its two-step **centre-null evasion**.

Residual boundaries, **not** closed here:

- **Off a process box**, `hard_blockers` are the summary's *free-text* physical/composability `exclusions`
  (not re-derivable from the thin projection), so a non-process hard blocker stripped off-box is not caught —
  the same free-text boundary `_check_process_admission_coherence` carries. Catalyst and fiction channels are
  re-derived on or off the box.
- A frontier entry whose summary carries **no** `replay_payload` has its catalyst/fiction channels
  unverifiable (only the digest-covered process channel is checked). A verified-admission producer serialises
  with `include_replay=True`, so this bites only a replay-stripped payload with zero FITS routes.
- A **fully-coherent forger** who fabricates a self-consistent `replay_payload` (a valid route + a valid
  centre passing `is_elementary_condensation`) re-derives to the tampered verdict and is **not** caught. The
  digest is an identity aid, not an authentication boundary (`smartchem/contracts.py`). Closing this needs
  HMAC signing (COMBINED-VERDICT-AUTH) — out of scope, and honestly the same irreducible residual every other
  structural check carries.

## Evidence

- Probe: `experiments/poor_man_tamper_hardening_probe.py`
  (`FROZEN_HASH = 1bffd2321939a073dd291ba3c51e33c1e1ae5cdb88f999c1ff44529a76c3c766`).
- Tests: `tests/test_poor_man_tamper_hardening.py`.
- Probe hash movement from Piece 2: only `poor_man_etherification_recognizer_probe` moved
  (`ae5de300… → 6d783d59…`) — its positive control was rebuilt centre-less → centre-carrying and gained a
  `dme_step_carries_centre` assertion. R56 / R58 / R60 probes stayed byte-stable (all their positive controls
  were already centre-carrying; the frontier soundness sweeps read reconstructed centre-carrying routes, so
  `false_vouch_count == 0` and the collision proofs are intact and unchanged).
