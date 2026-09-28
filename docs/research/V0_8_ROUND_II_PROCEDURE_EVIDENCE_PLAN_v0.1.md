# SmartChem 0.8 Round II — Procedure-Evidence Closure + Verifiable Canonical Transport (PLAN v0.1)

**Branch** `feat/v0.8-real-route-dossiers` (off `main` `2d5c8a3`, 9 commits from Round I @ `17add53`).
**Version** stays `0.7.0a1` until the release gate (§10) closes; the bump to `0.8.0a1` and the merge to
`main` are conditional on that gate and are the operator's authorization (§11).

This is Round II. Round I built the pure obligation evaluator, the derived cumulative tier, the
weakest-link route aggregation, the typed wire representation, and thick-replay re-derivation. **Round I is
preserved, not redesigned.** Round II has two load-bearing jobs:

- **Blocker A — canonical transport is verifiable by default.** Today ordinary `serialize_response` /
  CLI `--json` ship above-FORMAL readiness with the replay stripped; only an opt-in
  `require_verified_admission=True` (that nothing in shipping code sets) fails closed. Fix structurally.
- **Blocker B — procedure evidence is representable enough that `PROCESS_SPECIFIED` can HONESTLY light**
  for at least one benign sourced route, without weakening the word.

---

## 1. Wave A findings (read-only investigation, six lanes, all reported)

| Lane | Bearing | Verdict |
|---|---|---|
| A | procedure-evidence model + completeness theorem + op vocab | minimal `ProcedureEvidence` model delivered |
| B | source reconstruction (isopentyl/aspirin/paracetamol/methyl-salicylate) | ground truth + the source-asymmetry, live-probed |
| C | transport/replay | fix = option (a) + a digest-bound `transport_mode`; measured +4.3% |
| D | readiness integration + workup semantics | option (a) AND-gate; tier workup gate with impossibility proof |
| E | fit/capability firewall | no leak today (rests on `return False`); M20 real+unpinned |
| F | hostile structure-theorem | current code survives; naïve Round II direction KILLED 3 ways |

**Load-bearing facts established (file:line verified by the lanes):**

1. `readiness.py:99-112` `process_representation_is_complete` is a hard `return False` — the single gate that
   keeps `PROCESS_SPECIFIED` dark. `readiness.py:202-204` `workup_isolation = SATISFIED iff process.workup_included`
   **regardless of source** — the laundering hole. The tier `@property` (`readiness.py:321-340`) does **not**
   branch on `workup_isolation` (the documented FORWARD HAZARD, `readiness.py:330-333`).
2. **Source asymmetry (Lane B, live-probed):** of the four target routes, ONLY paracetamol-anhydride sets its
   nested `ProcessRequirements.source` to an accepted citation (`decompiler_conditions.py:193-197`). Isopentyl
   acetate, aspirin, methyl salicylate all default `process.source=None` — `is_sourced` prints `False` — even
   though their **envelope** is accepted-sourced and the process facts are genuinely quoted from that same page.
   This is a committed inconsistency, **NOT** to be laundered by container inheritance.
3. **Aspirin & paracetamol-anhydride are reaction-type UNRECOGNIZED for a structural reason** (`feasibility.py:323`
   `_is_intermolecular_acyl_condensation` requires net water production; anhydride transacylation expels acetic
   acid, not water). **No family #18 can or should "fix" this** — they stay `FORMAL_CANDIDATE` honestly.
4. **Lane F KILL 1 (LETHAL):** patching the completeness predicate to `lambda p: True` awards `PROCESS_SPECIFIED`
   to the methyl-salicylate step with `workup=UNSATISFIED`, `process.source=None`, and the **conditions DOI shown
   as the procedure's provenance** (`readiness.py:230-232` merges `envelope.source.locator`). M15+M17+M18 in one.
5. **Lane F KILL 2 (HIGH, M19):** `reaction_conditions` keys on `_reaction_signature` = composition-only
   (`decompiler_conditions.py:85-106`), isomer-blind, and returns `record.envelope` unguarded
   (`decompiler_conditions.py:378-385`). Off the live readiness axis today only because `assembly_conditions`
   (structurally guarded, `:388-420`) is the sole live search caller and the DECOMPOSITION seed carries no process.
6. **Lane C/E/F agree:** `RankedDAGSummary` (`service.py:1220-1249`) has NO readiness field. DAG readiness = 0.9.
7. **Lane F design condition:** the step/route digest COVERS `envelope.process`; the replay codec round-trips the
   full envelope incl. nested `source`. Anything hung inside the envelope is automatically digest-bound and
   re-derivation-checked — but this protection evaporates for a `compare=False` field or a field not
   reconstructed into the replayed step. `evaluate_step/route` must stay a pure function of the replayed step.

---

## 2. FROZEN barrier decisions

### D1 — `ProcedureEvidence` is a NEW separate type, hung inside `ConditionEnvelope`
A new module `smartchem/procedure_evidence.py`. `ConditionEnvelope` gains one field
`procedure: ProcedureEvidence | None = None` (sibling to the existing `process: ProcessRequirements | None`).

- **Separate from `ProcessRequirements`** (Lane E's seam B): the completeness predicate reads
  `ProcedureEvidence`'s own fields and NEVER `ProcessRequirements` capability fields
  (`equipment`, `peak_temperature_k`, pressures, times) or `ProcessBounds`.
- **Inside the digest-covered, replay-reconstructed envelope** (Lane F design condition): it is `compare=True`
  (digest-bound) and the envelope codec round-trips it, so `_check_readiness_coherence` re-derives it and refuses
  tamper. NO `compare=False` procedure field. NO parallel evidence engine. NO external lookup in the evaluator.

### D2 — types (frozen signatures; a writer may rename a private helper, never a public field/enum member)
```python
class EvidenceFieldStatus(str, Enum):
    PRESENT = "PRESENT"                                  # a structured value IS represented, tied to a locator
    EXPLICIT_NOT_APPLICABLE = "EXPLICIT_NOT_APPLICABLE"  # the source AFFIRMATIVELY closes this out (see D3)
    UNKNOWN_MISSING = "UNKNOWN_MISSING"                  # the source is silent; no claim either way

@dataclass(frozen=True)
class EvidenceField(Digestible):        # not Generic in v0.1 -- value carried as a normalized str/Interval
    status: EvidenceFieldStatus
    value: "str | Interval | None"      # populated iff PRESENT or EXPLICIT_NOT_APPLICABLE, else None
    locator: "str | None"               # non-empty iff PRESENT/EXPLICIT_NOT_APPLICABLE; None iff UNKNOWN_MISSING
    justification: str = ""             # REQUIRED (non-empty) for EXPLICIT_NOT_APPLICABLE; else ""
    # __post_init__ enforces status<->value/locator/justification coherence.

class OperationKind(str, Enum):
    ADD = "ADD"; MIX = "MIX"; HEAT = "HEAT"; COOL = "COOL"; HOLD = "HOLD"
    SEPARATE = "SEPARATE"; FILTER = "FILTER"; DRY = "DRY"; DISTILL = "DISTILL"; VERIFY = "VERIFY"

class OperationRole(str, Enum):
    REACTION = "REACTION"; QUENCH = "QUENCH"; WASH = "WASH"
    RECRYSTALLIZATION = "RECRYSTALLIZATION"; OTHER = "OTHER"

@dataclass(frozen=True)
class ProcedureOperation(Digestible):
    ordinal: int                               # 1-based, contiguous+unique within a ProcedureEvidence
    kind: OperationKind
    role: OperationRole = OperationRole.REACTION
    materials: tuple[str, ...] = ()
    quantity: "EvidenceField | None" = None    # amount OR ratio ("1:3.3 molar excess")
    rate: "EvidenceField | None" = None        # meaningful for kind=ADD
    agitation: "EvidenceField | None" = None   # meaningful for kind in {ADD,MIX,HEAT,HOLD,COOL}
    temperature: "EvidenceField | None" = None # EvidenceField(value=Interval unit 'K')
    pressure: "EvidenceField | None" = None
    duration: "EvidenceField | None" = None    # EvidenceField(value=Interval unit 'min'), per-OPERATION
    endpoint: "EvidenceField | None" = None    # meaningful for kind in {HOLD,HEAT,DISTILL}
    apparatus: tuple[str, ...] = ()            # source-quoted equipment nouns (describes the PAPER's bench)
    locator: str = ""                          # non-empty; the source locator this op traces to

@dataclass(frozen=True)
class ProcedureEvidence(Digestible):
    reaction_scope: str                        # exact reaction/structural scope this evidence is FOR
    source: "SourceCitation | None"            # the accepted citation backing the operations
    scale: EvidenceField
    operations: "tuple[ProcedureOperation, ...]"     # non-empty; ordinals 1..N contiguous/unique
    quench: EvidenceField
    workup_isolation: EvidenceField            # DISTINCT from ProcessRequirements.workup_included
    separation: EvidenceField
    wash: EvidenceField
    drying: EvidenceField
    purification: EvidenceField                # distinct from workup_isolation
    analytical_verification: EvidenceField
    evidence_scope: str = ""                   # human gloss; NEVER read by the predicate
    unresolved_omissions: "tuple[str, ...]" = ()

    @property
    def is_sourced(self) -> bool:              # mirrors ProcessRequirements.is_sourced / ConditionEnvelope.is_sourced
        return self.source is not None and self.source.accepted
```
`__post_init__` (in `procedure_evidence.py`) enforces structural well-formedness: contiguous/unique ordinals;
`EvidenceField` status↔value/locator/justification coherence; at least one `OperationKind.ADD` with
`role=REACTION`; a whole-procedure field marked `PRESENT` requires ≥1 matching operation, `EXPLICIT_NOT_APPLICABLE`
requires zero. **Well-formedness is NOT completeness** (that is D3) and NOT sourcing (that is the readiness gate).

### D3 — the completeness theorem (frozen)
`readiness.py` gains `procedure_representation_is_complete(evidence: ProcedureEvidence) -> bool` (superseding the
old `process_representation_is_complete(process)` stub, whose Round-I test is updated by the readiness writer). It
reads **only** `EvidenceFieldStatus` tags + operation kinds/ordinals — never prose (`evidence_scope`, `justification`
text), never `ProcessRequirements.workup_included`/`is_sourced`, never `ConditionEnvelope.is_sourced`, never
ΔG/rate/selectivity/`ProcessFit`/`ProcessBounds`:
```python
_WHOLE_PROCEDURE_FIELDS = ("scale","quench","workup_isolation","separation","wash","drying",
                           "purification","analytical_verification")
def procedure_representation_is_complete(evidence) -> bool:
    if evidence.unresolved_omissions:                 return False
    if not evidence.operations:                       return False
    for name in _WHOLE_PROCEDURE_FIELDS:
        if getattr(evidence, name).status is EvidenceFieldStatus.UNKNOWN_MISSING:  return False
    for op in evidence.operations:
        if op.kind in _AGITATION_KINDS and _unknown(op.agitation):  return False
        if op.kind is OperationKind.ADD and _unknown(op.rate):      return False
        if op.kind in _THERMAL_KINDS   and _unknown(op.temperature):return False
        if op.kind is OperationKind.HOLD and (_unknown(op.duration) or _unknown(op.endpoint)): return False
    return True   # (_unknown(f) := f is None or f.status is UNKNOWN_MISSING)
```
**`EXPLICIT_NOT_APPLICABLE` semantics (frozen, and the thing Wave C attacks hardest):** it means the source presents
a COMPLETE preparative procedure in which the field's operation genuinely does not occur, and the field carries a
locator + a non-empty `justification` pointing at the source text that closes it out. It is **never** derived from
chemistry or phase, and **never** a synonym for silence. Mere silence is `UNKNOWN_MISSING` (blocks). *Never weaken
`EXPLICIT_NOT_APPLICABLE` to make a route climb.*

### D4 — the readiness gate + tier law (frozen)
In `_process_and_workup_obligations` (reading `step.envelope.procedure`):
- `process = SATISFIED` **iff** `procedure is not None AND procedure_representation_is_complete(procedure) AND
  procedure.is_sourced`. The `is_sourced` conjunct is mandatory (Lane F KILL 1) — completeness alone never suffices.
- `workup_isolation = SATISFIED` **iff** `procedure is not None AND procedure.workup_isolation.status is PRESENT AND
  procedure.is_sourced` (Lane D option (a); replaces the legacy `process.workup_included` bool gate).
  `NOT_APPLICABLE` iff `procedure.workup_isolation.status is EXPLICIT_NOT_APPLICABLE AND procedure.is_sourced`.
- **provenance for a SATISFIED process/workup axis = `procedure.source.locator`** — NEVER the envelope's conditions
  DOI (Lane F KILL 1(c)). A SATISFIED axis always carries its own accepted locator.
- `conditions` is **byte-identical to Round I** — untouched.

New `StepReadiness.tier` (one guard added before the final return; Lane D impossibility proof):
```python
if self.reaction_type is not SATISFIED:      return FORMAL_CANDIDATE
if self.conditions   is not SATISFIED:       return REACTION_VOUCHED
if self.process      is not SATISFIED:       return CONDITIONS_SUPPORTED
if self.workup_isolation is not SATISFIED:   return CONDITIONS_SUPPORTED   # NEW: closes the forward hazard
return PROCESS_SPECIFIED
```
Proof: the final return executes iff every guard is False, in particular iff `workup_isolation is SATISFIED`;
contrapositive over the closed 4-member `ObligationStatus` — `workup != SATISFIED ⟹ tier != PROCESS_SPECIFIED`,
by construction. Landed in the SAME commit that makes `process` reachable. Weakest-link `min_tier` route
aggregation is unchanged and inherits the cap automatically.

### D5 — canonical transport (frozen; Lane C option (a) + Lane F thin-wire ruling)
- Flip `include_replay` default to `True` on the **canonical** producer path (CLI `recompile`/`decompile --json`
  and the `serialize_response`/`response_to_payload` calls the CLI uses). Do NOT invent a second evidence payload
  (option (b) is the duplicate-authority trap). Cost measured: +464 B / +4.3% on a 2-route response; `replay_payload`
  is `compare=False`, so **zero digests move**.
- Add a top-level `transport_mode: {CANONICAL_VERIFIED, THIN_ADVISORY}` on the response payload, **folded into
  `result_digest`** (a downgrade-strip is caught like readiness tamper). Bumps `COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR`
  v1alpha17→v1alpha18 and `COMPILATION_RESPONSE_SCHEMA`.
- On ordinary load, re-derivation is **mandatory when the payload declares `CANONICAL_VERIFIED`** (keyed off the
  payload's own declared mode, not a caller flag): a `CANONICAL_VERIFIED` payload carrying an above-FORMAL claim with
  missing/insufficient replay evidence **fails closed**. `THIN_ADVISORY` remains explicit and labeled.
- **PROCESS_SPECIFIED is not admissible on an unsigned thin wire** (Lane F forward ruling): a `THIN_ADVISORY` payload
  whose tier is `PROCESS_SPECIFIED` **fails closed on ordinary load**, unconditionally. Lower above-FORMAL tiers keep
  their documented thin residual (VERIFIED-DEFER #3) — that boundary is unchanged.
- Re-derivation stays at `response_from_payload` (`service.py:3781`), ordered after `_check_verified_admission` — do
  not move it. `_check_frontier_coherence` shares the pattern and improves for free.

### D6 — same-formula isomer guard (frozen; Lane F KILL 2 / M19)
`ProcedureEvidence` is attached to seed records reached ONLY through the structurally-guarded assembly path
(`assembly_conditions`, `resolve_structure().name` selector). It is NEVER attached to a DECOMPOSITION seed record and
NEVER served through the isomer-blind `reaction_conditions`/`decompiler_review` path. The live census/funnel/dossier
stays on the structurally-guarded live search path.

---

## 3. Source-migration plan — the honest forcing matrix

The 4 SEED records are hand-built `ProcessRequirements` + free-text provenance; NONE is in `ProcedureEvidence` shape.
Migration authors `ProcedureEvidence` from facts **already quoted in the repo** (the seed provenance strings +
comments Lane B surfaced) — no new network scraping. Each field's status/justification is defended against the actual
source text; Wave C attacks every `EXPLICIT_NOT_APPLICABLE`.

| Route | reaction_type | conditions | procedure complete? | expected tier | why |
|---|---|---|---|---|---|
| **isopentyl acetate** | SATISFIED | SATISFIED (sourced) | **target: complete + sourced** | **PROCESS_SPECIFIED** *(if honest)* | full preparative LibreTexts prep: reflux→extraction→MgSO₄ dry→fractional distillation, quoted apparatus, timed reflux; accepted LibreTexts citation re-attached to the `ProcedureEvidence.source` |
| **methyl salicylate** | SATISFIED | SATISFIED (sourced) | NO — source stops at a qualitative smell-test | **CONDITIONS_SUPPORTED** | no preparative isolation/purification/analytical acceptance → those fields honestly `UNKNOWN_MISSING` (a fragment, NOT gerrymandered N/A) → predicate False |
| **aspirin** | **UNSATISFIED** | SATISFIED | (rich; irrelevant to tier) | **FORMAL_CANDIDATE** | anhydride transacylation ∉ oracle (`feasibility.py:323`); non-monotonic control, richer procedure evidence stays visibly SATISFIED |
| **paracetamol-anhydride** | **UNSATISFIED** | SATISFIED | (rich; irrelevant to tier) | **FORMAL_CANDIDATE** | same as aspirin; the flagship non-monotonicity witness |

**Honest-outcome clause:** if, after rigorous extraction, isopentyl acetate cannot reach a *defensible* complete +
sourced procedure (e.g. `quench`/`scale` genuinely `UNKNOWN_MISSING`, or an `EXPLICIT_NOT_APPLICABLE` that cannot be
justified against the source), then `PROCESS_SPECIFIED` **stays dark**, the census reports WHY, and the release gate
condition §10.3 fails — we do NOT bump/merge and we do NOT weaken the theorem. That is an acceptable Round II result.

---

## 4. Mutation gate — keep M1–M11, add M12–M20 (each injected AND killed; non-vacuous)

Lane F left runnable repros in scratchpad (`m17_full.py`, `m19_probe.py`, `m12_probe.py`, `m12b_probe.py`,
`digest_probe.py`) — the M-tests harden those exact scenarios. Note (Lane E): `_check_readiness_coherence`
re-derives with the SAME evaluator, so a SYSTEMATIC evaluator mutation is NOT caught by round-trip byte-equality —
M18/M20 kill-tests must assert **directly** on the derivation.

- **M12** — canonical (`CANONICAL_VERIFIED`) above-FORMAL payload with replay removed still loads → must be REFUSED.
- **M13** — a merely-declared, unsourced workup counts as evidence-backed `workup_isolation=SATISFIED` → must die.
- **M14** — `workup_included=True` alone (legacy bool) makes `PROCESS_SPECIFIED` → must die.
- **M15** — a missing required procedure operation / a gap in ordinals is silently treated as complete/N/A → must die.
- **M16** — free-text provenance is parsed/inferred into a structured operation → must die.
- **M17** — one sourced field (or the envelope's source) makes the whole procedure count as source-backed → must die.
- **M18** — `PROCESS_SPECIFIED` ignores workup/isolation completeness → must die (assert on the tier property directly).
- **M19** — procedure evidence from another same-formula isomer is substituted (via `reaction_conditions`) → must die.
- **M20** — `ProcessFitStatus.FITS` (or `available_equipment`/ΔG) promotes process completeness → must die.

Plus reinforce M10's analogue: a `ProcedureEvidence`-bearing route whose replayed step's procedure is stripped
re-derives to a LOWER tier and is refused.

---

## 5. Wave B ownership map (ONE writer per file; cross-lane findings are failing tests + patches to the owner)

| Writer | Owns | Depends on |
|---|---|---|
| **W1 procedure-core** | NEW `smartchem/procedure_evidence.py` + `tests/test_v0_8_procedure_evidence.py` | — |
| **W2 source-migration** | `smartchem/conditions.py` (add `procedure` field + codec-adjacent guards), `smartchem/decompiler_conditions.py` (author `ProcedureEvidence` for the 4 routes via the assembly path) + source tests | W1 |
| **W3 readiness-close** | `smartchem/experiment/readiness.py` + readiness tests | W1, W2 |
| **W4 transport-close** | `smartchem/service.py`, `smartchem/cli.py` + schema/golden tests (regen 5 CLI-JSON goldens + `response_schema`) | W2, W3 |
| **W5 dossier-close** | `smartchem/experiment/drafter.py` + dossier tests | W3 |
| **W6 release-evidence** | `experiments/v0_8_*` (census/funnel add procedure; mutation M12–M20), RESULTS regen, docs/ROADMAP | all |

**Build order (dependency pipeline):** W1 → W2 → W3 → W4 → (W5 ∥ W6). The parent (integration authority) writes or
tightly supervises the semantic spine (W1–W3, W5) and verifies every writer against the filesystem; W4 and W6 are
the well-specified, disjoint, mechanically-heavy pieces suitable for delegation. Goldens: **explain every changed
digest/output**; never regenerate to suppress an unexplained diff.

---

## 6. The 0.8 release gate (ALL must hold; else do NOT bump or merge)

1. Round-I readiness semantics intact (obligations are truth; tier derived; ranking/ΔG/FITS firewalled).
2. Ordinary route responses distinguish FORMAL / VOUCHED / CONDITIONS / PROCESS.
3. ≥1 real benign route reaches `PROCESS_SPECIFIED` from accepted structured procedure evidence (target: isopentyl).
4. ≥1 sourced-but-incomplete route stays `CONDITIONS_SUPPORTED` (methyl salicylate).
5. ≥1 process-rich but reaction-UNRECOGNIZED step keeps its richer evidence visibly SATISFIED while its coarse tier
   stays lower (aspirin / paracetamol-anhydride).
6. Canonical machine transport carries sufficient evidence for readiness re-derivation on ordinary load.
7. A `CANONICAL_VERIFIED` above-FORMAL payload with missing/altered evidence fails closed; `PROCESS_SPECIFIED` is not
   admissible on an unsigned thin wire.
8. Same-formula evidence cannot transfer (M19 dead; `ProcedureEvidence` behind the structural selector).
9. Human (`drafter` render) and JSON render identical readiness semantics.
10. M1–M20 all die (injected + killed, non-vacuous).
11. Full OOM-safe suite green (`scripts/run_suite.sh`).
12. No 0.7 algebra/default regression.
13. No capability/profile logic leaked backward into readiness (M20 pinned).

## 7. Version + merge authorization
Iff §6 closes: bump `0.7.0a1 → 0.8.0a1` coherently (`pyproject.toml`, `smartchem.__version__`, README, ROADMAP, CLI
version goldens, schemas as needed), write the release record
`docs/research/V0_8_REAL_ROUTE_DOSSIERS_RELEASE_2026-09-27.md`, review every golden semantically, open
`feat/v0.8-real-route-dossiers → main`, and merge (branch current with main, hostile gate clean, M1–M20 kill, suite
green). Record the merge SHA. Then begin `feat/v0.9-capability-compiler` from the NEW main.

---
*Frozen at the Wave A barrier by the parent integration authority. Wave B builds against this contract; deviations
are raised as failing tests to the file owner, never as competing edits.*
