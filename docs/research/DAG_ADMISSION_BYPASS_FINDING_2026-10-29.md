# DAG-ADMIT-BYPASS — convergent-DAG reaction-type admission bypass (finding + repair design)

**Date:** 2026-10-29 · **Baseline:** released `main` `9e8fa5f` (SmartChem 1.1.0) · **Status of repair:** DESIGNED,
NOT IMPLEMENTED (a release-contract change — see §4; needs operator sign-off).

## 1. The finding (verdict: FAIL)

Linear route search demotes a conserved-but-fictional step through the reaction-TYPE oracle: the readiness
layer runs `route_reaction_type_blockers` → `recognize_reaction_type` per step (`readiness.py`
`_reaction_type_obligation`), so an unrecognized step is blocked. The **convergent-DAG path does not**.
`dag_bench_fit` (`smartchem/experiment/drafter.py`) and its projection `RankedDAGSummary.of_dag`
(`smartchem/service.py`), consumed by `admissible_dag_digests` (`service.py`), judge a DAG on composability +
the physical box + the process axis and **never consult the recognizer**.

**Reproduced** (not testimony — `experiments/dag_admission_bypass_probe.py`): a conserved fiction
`EtOH + CH4 → ethyl-methyl-ether + H2` (C3H10O both sides) given a satisfying condition envelope reaches
`FITS`, while `recognize_reaction_type` returns `None` and `route_reaction_type_blockers` yields a blocker the
DAG path ignores. The genuine ester control is `FITS` + recognized. This matches `tests/test_dag_rank.py::_single_step_fits_dag`
exactly but for the fiction target.

This closes the open question PR #139 left and that the Round-IX report under-stated: the containing wall was
mis-identified as "missing process conditions." The real situation is that a *condition-bearing* fiction reaches
FITS; the only accidental containment is the composability "no sourced stability data" gap for multi-step DAGs,
which **shrinks as stability coverage grows**.

## 2. Production reachability (not merely an API probe)

A DAG-mode recompile of a real target (`recompile smiles:CC(=O)OC` under the convergent grammar — the
`methyl_acetate_dag` case in `experiments/v0_9_5_baseline_freeze.py`) emits generator-derived capped-scission
steps, some matching no attested reaction class. Those unrecognized steps reach `FITS` and enter
`admissible_dag_digests` exactly as the hand-built fiction does. So the bypass is reachable on a production path,
not only through the direct `dag_bench_fit` API.

## 3. Why the naive fix is wrong (rejected approach)

Folding `route_reaction_type_blockers(dag)` into `dag_bench_fit`'s **gap** channel (unrecognized → `UNKNOWN`
`fit_status`) closes the hole but is architecturally wrong and breaks correctly-passing tests:

- It **reinterprets a stable field.** On the linear side, *fit* (section-11 physical/process) and
  *readiness/recognition* are **separate axes** — an unrecognized linear route can be `FITS` physically yet not
  `REACTION_VOUCHED`. Folding recognition into `fit_status` conflates them (the plan's explicit "do not conflate
  reaction recognition with process fit").
- It breaks `tests/test_item5_dag_phase_aware_ranking.py` **unrepairably**: every phase-aware fixture there is a
  halogen homolysis (`Br2/I2/Cl2 → 2·`), all genuinely unrecognized, all demoted FITS→UNKNOWN. The
  `_check_verified_admission` fail-closed test needs a `FITS` DAG with phase-dependent feasibility, and there is
  no recognized substitute (recognized organic reactions carry no phase-dependent feasibility data). Demotion
  here is *correct* (honest coverage loss), but it dissolves the test's vehicle.
- It moves the `methyl_acetate_dag` semantic invariant (`tests/test_v1_0_version_transition.py`) at the
  `fit_status` level — a broad, field-reinterpreting move.

(Measured: this approach turned the full suite to 3 failures — item5 ×2, version-transition ×1 — all legitimate
corrected verdicts, but via the wrong axis.)

## 4. Recommended repair (DAG-ADMIT-02) — and why it needs sign-off

Mirror the **linear fit/readiness separation**: keep `fit_status` pure (physical/process/composability), and gate
the **admission decision** on recognition — the plan's actual "reaches an admissible state" is
`admissible_dag_digests`, not the fit label.

- Carry a per-step recognition verdict on `RankedDAGSummary` (derived in `of_dag` via
  `route_reaction_type_blockers`), and gate `admissible_dag_digests` on
  `d.fit_status == "FITS" and not d.reaction_type_blockers`.
- `Br2`-style unrecognized reactions keep `fit_status == FITS` (item5 stays green) but leave *admission* — exactly
  the linear semantics.

**The contract catch (why this is an operator decision, not a quiet patch).** For the gate to be **forge-safe on
the verified-admission wire**, the recognition verdict must be **identity-bearing** — folded into the DAG
`result_digest` (not `compare=False`), or `admissible_dag_digests` must re-derive recognition from each dossier's
thick `replay_payload` at the admission point. The identity-bearing form is the clean one, but it **bumps the DAG
dossier `schema_version` and moves every DAG `route_digest`/golden** — a declared MINOR coverage/contract move
requiring the field-by-field re-freeze `tests/test_v1_0_version_transition.py` gates behind human sign-off. A
`compare=False` field is NOT forge-safe (excluded from `__eq__`, so `_check_verified_admission`'s `resummary != d`
would not catch a forged "recognized" relabel).

A *subtly* wrong soundness fix is worse than a documented hole, and this one is entangled with DAG identity +
the verified-admission wire. It is therefore scoped and staged here rather than rushed: **recommend DAG-ADMIT-02
as its own PR** — identity-bearing recognition field, `schema_version` bump, field-by-field golden re-freeze,
an adversarial test proving neither a forged condition envelope nor an altered serialized dossier bypasses
admission, and a COMPATIBILITY.md declaration of the semantic move.

## 5. Status (original, 2026-10-29 — superseded by §6)

- **Hole:** CONFIRMED, reproduced. (`experiments/dag_admission_bypass_probe.py`.)
- **Repair:** DESIGNED (DAG-ADMIT-02, §4). NOT yet implemented at the time this was written.

## 6. UPDATE — IMPLEMENTED (DAG-ADMIT-02, Candidate A, no sign-off needed)

**Date:** 2026-10-29 (Mega-Round XI). The repair is now IMPLEMENTED in `smartchem/service.py`, as the **re-derive**
variant §4 itself named ("*or* `admissible_dag_digests` must re-derive recognition from each dossier's thick
`replay_payload` at the admission point"). Measuring the two candidates (the round's P0) showed this one is the
**weakest sound repair and needs NO sign-off** — §4's "contract catch" over-stated the cost. The identity-bearing
STORED field (Candidate B) remains a legitimate, stronger, sign-off-gated option (see the boundary below).

### 6.1 What was built
- `_dag_dossier_steps_recognized(dossier)` — re-derives recognition from the thick `replay_payload` (reconstruct the
  `SynthesisDAG`, bind `reconstruct.digest == route_digest` like `_check_frontier_coherence` KILL 1, then
  `route_reaction_type_blockers`). No stored field; nothing forgeable to relabel.
- `admissible_dag_digests` now admits a FITS dossier only when every step is positively recognized. `fit_status`
  keeps its pure physical/process/composability meaning (the plan's "do not conflate recognition with process fit").

### 6.2 Field-by-field compatibility differential (MEASURED, the round's P0 deliverable)
| axis | moves? | why |
|---|---|---|
| request `semantic_digest` | **no** | unchanged; search identity untouched |
| search/transform registry digest | **no** | no new recognizer, no registry change |
| `SynthesisDAG.digest` / DAG `route_digest` | **no** | recognition is re-derived, never a dossier field |
| `RankedDAGSummary.digest` | **no** | no `compare=True` field added |
| response `result_digest` | **no** | admission list is a derived property, not serialized, not hashed |
| DAG dossier `schema_version` | **no** | no schema change |
| serialized payload / goldens | **no** | `admissible_dag_digests` is not a serialized key |
| `process_selection_status` / `exit_code` | only for an unrecognized-only FITS set | correct, and transport-invariant for recognized responses (advisory on thin — §6.4) |

Confirmed by the full OOM-safe suite and by `tests/test_v1_0_version_transition.py` (no version-transition move) —
so §4's `schema_version` bump + golden re-freeze + sign-off are **not** required for Candidate A.

### 6.3 Production reachability — refined (honest correction of §2)
§2 claimed the bypass was "production-reachable" via the methyl-acetate DAG recompile. Measured end-to-end through
`run_compilation`, it is **latent, not live**: every *generator-derived* DAG step is `UNKNOWN`-fit, contained by
TWO accidental walls — the composability "no sourced stability data" gap (multi-step) and a process-axis **workup
gap** (single-step: generator steps carry no explicit workup). Neither is a recognition gate; both shrink as
coverage/seeding grows. The only FITS DAGs on the current search are *seeded recognized* reactions (paracetamol via
Ac₂O). So the hole is a real **contract** defect (a FITS-unrecognized DAG → admissible) demonstrable at the
`admissible_dag_digests`/`of_dag` level; its production exposure opens as the containing gaps close. DAG-ADMIT-02
closes the contract regardless. (`experiments/dag_admission_recognition_gate_probe.py`,
`tests/test_dag_admission_recognition_gate.py`.)

### 6.4 The one boundary, and the stronger (sign-off) option
On an explicit `THIN_ADVISORY` wire the replay is stripped, so recognition cannot be re-derived; there the claim
stays ADVISORY (admitted on `fit_status`), exactly as the linear frontier's fiction channel is advisory on thin
transport, keeping `process_selection_status`/`exit_code` transport-invariant. The strong guarantee for the thin
wire is `_check_verified_admission`, which under `require_verified_admission` already REFUSES a FITS DAG with no
replay (fail-closed). A gate that ALSO withholds an unverifiable DAG on a *plain* thin load would need recognition
**stored** on the dossier — Candidate B's `schema_version` bump + golden re-freeze + operator sign-off. That is the
documented, available upgrade; Candidate A is the weakest repair that closes the production/default-transport hole
with zero contract movement.

- **Hole:** CONFIRMED, contract defect; production exposure latent (contained, not a recognition gate).
- **Repair:** IMPLEMENTED (DAG-ADMIT-02, Candidate A). No schema/digest/golden/sign-off. Stronger always-fail-closed
  variant (Candidate B) staged for sign-off.
