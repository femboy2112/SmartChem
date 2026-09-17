# POOR_MAN_TAMPER_HARDENING_v0.1

Closing the R59 disposition **serialized-tamper** forgery — the cheap, honest way a gate finding opened up.
No R58 reversal, no route/step hash break. **Fully closed** on the process-exclusion channel (every transport)
and on the catalyst/fiction channels under the **thick** (digest-bound replay) transport; the **default thin
transport** carries **advisory** dispositions — an honest, tracked boundary, not a claimed closure.

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

Invoked from **`response_from_payload`** — the deserialization seam, after `_check_verified_admission`, and
unconditional on `require_verified_admission` — **not** `__post_init__`. It belongs at the load seam because,
like `_check_verified_admission`, it reconstructs routes from the replay payload (a load-time authority, not an
in-memory-construction invariant); ordering it after verified admission keeps that check's route-binding message
for a FITS-route substitution. For each frontier entry it **re-derives the same blockers**
`_affordability_frontier` computes, and refuses (fail-closed, one-directional) any entry whose claimed
blockers are **looser** than the re-derivation:

- `hard_blockers` (REAL_BUT_HARD): process exclusions re-derived from the matching summary's digest-covered
  per-step `process_requirements` (the same authority PROCESS-ADMIT-01 uses — **no replay needed**), **plus**
  `route_catalyst_blockers` over the route reconstructed from the thick `replay_payload`.
- `fiction_blockers` (NOT_A_REACTION): `route_reaction_type_blockers` over that reconstructed route.

**KILL 1 — digest-bind (gate finding).** The reconstructed route is bound to the entry identity:
`route.digest == e.route_digest` or it raises, mirroring `_check_verified_admission`'s FITS bind. Without it an
attacker substitutes **any** recognized route's replay under this entry's `route_digest` and the fiction/catalyst
re-derives to zero — a stripped disposition would pass. Every honest reconstructed replay binds (verified: 0
false-reject).

Polarity: raise iff a re-derived blocker is **missing** from the claimed tuple. A claim with *extra* blockers
(a worse disposition than reality) is a self-suppression, out of scope — exactly as the process / verified-
admission checks treat hide-good. An honest response is self-consistent (re-derived == claimed) and passes.

Schema bumped `v1alpha13`: **no field change**, a new on-load refusal — so a pre-guarantee `v1alpha12` payload is
refused by the strict schema-version gate. The **descriptor stays `v1alpha16`**: its embedded
`response_schema_version` value reads `v1alpha13`, but a value-only change does not bump the descriptor version
(it bumps only on a field-shape change — its own convention).

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

## What is closed, and where the boundary is (stated plainly, no edge-case framing)

**Fully closed, every transport — the process-exclusion `hard_blockers` channel.** It re-derives from the
digest-covered `process_requirements` and needs no replay, so a `REAL_BUT_HARD → CLEAN` process strip is caught
even on a **default (thin)** serialization. (The catalyst channel appends nothing today — no registered reaction
declares a metal catalyst — so process exclusions are the whole hard channel in practice.)

**Fully closed, thick transport — the catalyst and fiction channels**, when a digest-bound `replay_payload` is
present (`include_replay=True`, what a verified-admission consumer requests). KILL 1 binds the evidence to the
entry and Piece 2 demotes a centre-less step, so the re-derivation reads the **real** route: any strip — including
the two-step **centre-null evasion** — is caught, down to a SHA-256 collision on the route digest (cryptographic,
out of scope).

**The default-transport boundary — NOT an edge case, it is the DEFAULT.** `response_to_payload` emits the replay
only on `include_replay=True` (default `False`). On the **default thin transport** the catalyst/fiction channels
have no evidence to re-derive from, so a `fiction_blockers` (or catalyst) strip is **not detected** — the thin
frontier carries **advisory** dispositions. This is **deliberately not closed**: no fail-closed-on-thin, no default
`include_replay` flip, per the "honest + bounded" decision. Full thin-transport closure is a **tracked follow-up**
(needs replay-**mandatory**-for-disposition-claims, or HMAC signing). It is pinned honestly as an `xfail` so a
future round trips it green rather than discovering it.

**Off a process box**, `hard_blockers` are the summary's *free-text* physical/composability `exclusions` (not
re-derivable from the thin projection), so a non-process hard blocker stripped off-box is not caught — the same
free-text boundary `_check_process_admission_coherence` carries.

The residual on the thick path is a full hash collision or a producer-side forger — `smartchem/contracts.py`: the
digest is an identity aid, not an authentication boundary; that needs HMAC signing (COMBINED-VERDICT-AUTH).

## Evidence

- Probe: `experiments/poor_man_tamper_hardening_probe.py`
  (`FROZEN_HASH = c3839f7a837a79676c8437d93180ef16c9bf175ac93d7a328b5a961477ab5ebe`).
- Tests: `tests/test_poor_man_tamper_hardening.py`.
- Probe hash movement from Piece 2: only `poor_man_etherification_recognizer_probe` moved
  (`ae5de300… → 6d783d59…`) — its positive control was rebuilt centre-less → centre-carrying and gained a
  `dme_step_carries_centre` assertion. R56 / R58 / R60 probes stayed byte-stable (all their positive controls
  were already centre-carrying; the frontier soundness sweeps read reconstructed centre-carrying routes, so
  `false_vouch_count == 0` and the collision proofs are intact and unchanged).
