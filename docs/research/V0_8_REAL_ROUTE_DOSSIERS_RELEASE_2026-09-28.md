# SmartChem 0.8 Real Route Dossiers — RELEASE RECORD (2026-09-28)

**Version:** `0.7.0a1` → **`0.8.0a1`**. **Branch:** `feat/v0.8-real-route-dossiers`, cut from `main@2d5c8a3`.
Round I (`17add53`) built the readiness-obligation core; Round II (this record) closed the two remaining
blockers and met the 13-condition release gate. This record states RELEASE TRUTH — what the code does now,
not the design intent (that is `docs/research/V0_8_ROUND_II_PROCEDURE_EVIDENCE_PLAN_v0.1.md`).

## What 0.8 delivers
SmartChem now says, per route and per step, exactly how much *real procedural evidence* backs it — as a typed,
orthogonal obligation ladder, not a confidence score:

- **FORMAL_CANDIDATE** — conservation-certified only.
- **REACTION_VOUCHED** — the reaction type is recognized by the production oracle.
- **CONDITIONS_SUPPORTED** — reaction vouched *and* an accepted-source `ConditionEnvelope`.
- **PROCESS_SPECIFIED** — reaction vouched, conditions sourced, *and* a typed `ProcedureEvidence` that is both
  structurally COMPLETE and backed by an accepted source, with workup/isolation discharged.

Obligations are the truth; the coarse tier is their derived, cumulative, weakest-link projection. Ranking, ΔG,
kinetics, selectivity, and `ProcessFitStatus.FITS` are firewalled out of readiness (M20, two independent audits).

## Architecture (Round II additions)
- **`smartchem/procedure_evidence.py`** (NEW): `EvidenceField` tri-state (PRESENT / EXPLICIT_NOT_APPLICABLE /
  UNKNOWN_MISSING), `OperationKind` (10), `OperationRole`, `ProcedureOperation`, `ProcedureEvidence`. A SEPARATE
  type from `ProcessRequirements` (which the 0.9 capability gate reads); `ConditionEnvelope` gained a
  digest-covered `procedure` field, so procedure evidence is bound to the envelope identity and
  replay-reconstructed on load.
- **`procedure_representation_is_complete(evidence)`** (readiness.py): a pure structural predicate over status
  tags + operation kinds/roles — never free text, never `ProcessRequirements`/`ProcessFit`/ΔG. Requires every
  whole-procedure field resolved, workup/isolation actually DESCRIBED (not merely N/A), a reaction operation
  that states its completion, and every heated/cooled reaction op to state its thermal condition. `process` is
  SATISFIED iff complete AND the procedure's OWN accepted source backs it; the reported provenance is the
  procedure's own locator, never the envelope's conditions citation.
- **Tier workup gate** (readiness.py): `workup_isolation` not discharged → capped at CONDITIONS_SUPPORTED. The
  Round-I forward hazard is closed by construction (M18).
- **Canonical transport** (service.py): `serialize_response`/`response_to_payload` default `include_replay=True`;
  a top-level `transport_mode {CANONICAL_VERIFIED, THIN_ADVISORY}` is folded into the wire `result_digest`. On
  load, a CANONICAL_VERIFIED above-FORMAL claim missing replay fails closed; a PROCESS_SPECIFIED claim on a
  THIN_ADVISORY wire fails closed unconditionally (regardless of replay-presence — Wave C fix). Schema
  `COMPILATION_RESPONSE` v1alpha14→v1alpha15, descriptor v1alpha17→v1alpha18.

## Empirical result — the forcing matrix (live, promoted `certified-route-v07` default)
| Route | reaction_type | conditions | procedure | derived tier | why |
|---|---|---|---|---|---|
| **isopentyl acetate** | SATISFIED | SATISFIED | complete + sourced | **PROCESS_SPECIFIED** | the round's real positive |
| **methyl salicylate** | SATISFIED | SATISFIED | none (source is a qualitative smell-test) | **CONDITIONS_SUPPORTED** | sourced-but-incomplete control |
| **aspirin** | **UNSATISFIED** | SATISFIED | complete + sourced | **FORMAL_CANDIDATE** | anhydride transacylation ∉ oracle; non-monotonic |
| **paracetamol-anhydride** | **UNSATISFIED** | SATISFIED | complete + sourced | **FORMAL_CANDIDATE** | flagship non-monotonicity witness |

The aspirin/paracetamol rows show `process` AND `workup_isolation` visibly SATISFIED while the coarse tier stays
FORMAL — the Round-I non-monotonicity principle one rung higher, and the exit gate's poster child. **No reaction
class #18 was added** to prettify them: the unrecognized reaction type is a structural fact (`feasibility.py`'s
acyl-condensation shape guard requires net water production; anhydride transacylation expels acetic acid). The
three preparative procedures were authored from their ACCEPTED primary sources (re-fetched and quoted).

## Gates (all measured, all green)
- **Funnel** (`experiments/v0_8_readiness_funnel.py`): routes **44 → 7 → 2 → 1**, steps **102 → 24 → 2 → 1**;
  12/12 properties; PROCESS_SPECIFIED reachable (isopentyl), no longer pinned dark.
- **Mutation gate** (`experiments/v0_8_mutation_calibration.py`): **M1–M20, 20/20 killed**, each non-vacuous
  (honest pass + a real in-memory code mutation; M18/M20 assert directly on the derivation).
- **Full OOM-safe suite** (`scripts/run_suite.sh`, RDKit absent — the committed baseline): **5674 collected /
  5628 passed / 0 failed / 0 errors / 46 skipped.**
- **No 0.7 regression:** goldens moved only for the digest-covered `procedure` field, the replay/transport_mode
  additions, the schema bumps, and the version bump (`tool_version` + folded `result_digest`) — no chemistry.

## Wave C hostile gate (two fresh non-authors)
- **evil-morty (transport):** F1 (VERIFIED, gate #7) — the THIN-wire PROCESS_SPECIFIED refusal was gated on
  replay-absence, so a THIN payload keeping its replay delivered PROCESS_SPECIFIED. **FIXED** (hoisted; regression
  pinned). F2 keyless MITM downgrade, F3 isomer-blind `reaction_conditions` — **VERIFIED-DEFER** (F3 gets a
  standing guard test). Clean bills: codec integrity, capability firewall, human/JSON parity.
- **amber (readiness/procedure):** shipped corpus CLEAN (isopentyl's quench N/A defensible; aspirin/paracetamol
  FORMAL anyway). F1/F2 (latent, no machine backstop for the N/A discipline) — **FIXED** by hardening the
  completeness theorem (isolation must be described; a reaction must state its endpoint). Her nag (an authored
  N/A justification used chemistry reasoning, which the contract forbids) — **FIXED** (reworded to the source's
  operation sequence). F3 locator-correspondence — **VERIFIED-DEFER**. Clean bills: tier law, weakest-link,
  sourcing conjunct, digest coverage.

## VERIFIED-DEFERs carried forward
1. Keyless-consumer transport residual — a fully-controlling forger who fabricates a coherent complete+sourced
   procedure and recomputes `result_digest` is closed only by `verification_key` (every axis in this module
   shares this residual).
2. `reaction_conditions` is isomer-blind; procedure evidence never flows through it today (a standing guard test
   pins that every procedure-bearing record is ASSEMBLY-only). Live only if a future readiness consumer is
   pointed at that path.
3. `ProcedureEvidence.is_sourced` does not check locator-correspondence between the source and the operations.
4. DAG readiness — `RankedDAGSummary` carries no readiness field (0.9).

## Commits (on `main@2d5c8a3`, Round I `17add53` + Round II)
`8251b7c` procedure-evidence + plan · `2a53f50` source migration · `4ac7b78` readiness close · `7d7da80`
dossier close · `441bb38` transport close · `70c9f78` CLI human/JSON parity · `74cc917` release evidence
(census/funnel/M12–M20) · `21609ce` Wave C fixes · (version bump commit follows).

## Next
0.9 Capability Compiler: project the SAME route through `ResearchLabProfile` / `PoorManProfile` / `CustomProfile`
without changing the chemistry. `CAPABILITY_ASSESSED` / `CAPABILITY_FIT` join the ladder only after the capability
model genuinely exists.
