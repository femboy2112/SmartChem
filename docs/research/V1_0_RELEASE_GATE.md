# SmartChem 1.0 Release Gate

The ten mandatory 1.0 laws (from
[`CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md`](CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md) §1.0.0), each bound to CURRENT
machine evidence. This is a release ledger, not an essay: every row points to a real gate/test/receipt. A law without
evidence is a 1.0 blocker.

**Scope note — why most evidence is inherited and valid.** The 1.0.0rc1 tree is the merged 0.9.5 product
(`main` @ `83d33fd`) with a package-version bump and release engineering ONLY. `experiments/v1_0_version_transition.py`
proves the 0.9.5a1 → 1.0.0rc1 transition moves EXACTLY the tool-version-bound fields (`tool_version`, `result_digest`,
the implementation digest, the `--version` banner) and ZERO production-semantic fields. Every mutation gate, funnel,
differential, and fuzz receipt therefore targets UNCHANGED source and carries over; the final-gate run below
re-confirms the fast gates fresh at 1.0rc1 and validates the expensive receipts' integrity rather than re-burning
hours on an unchanged SHA (program §Release engineering; the impact-based validation rule).

Package: `1.0.0rc1` · branch `release/1.0.0` · base `main` @ `83d33fd` (PR #94 merge) ·
source implementation digest `680fc1479a53d37656e56a98ade1be0944cdc7a731082a86b53b9d5e0047c2b5`.

---

## The ten laws

### 1. Total front door — every admissible input reaches a typed result or typed refusal
- **Production authority:** `smartchem/cli.py` `_dispatch` + the ONE error classifier `_domain_exit` (exit 2/5/70
  identically on every verb); `smartchem/identity_parse.py` `resolve_identity`; `ResponseOutcome` is TOTAL and the
  sole exit-code driver (`service.py` `_EXIT_BY_OUTCOME`).
- **Negative control / mutant:** `experiments/v0_6_mutation_calibration.py`; the baseline refusal matrix
  (`experiments/v0_9_5_baseline_freeze.py`, 15 tamper inputs → typed refusal class); `tests/test_cli.py`
  (unknown command → exit 2).
- **Release corpus evidence:** `experiments/v0_6_front_door_funnel.py` (36 cases, every malformed/parametric input a
  correct typed refusal); baseline freeze `--check` NO DRIFT.
- **Known boundary:** AUTO fall-through and expert-path AUTO precedence are DECLARED (COMPATIBILITY §5); a non-blocker.
- **Status: MET.**

### 2. No identity hallucination — formula equality never implies structural identity
- **Production authority:** `smartchem/identity_parse.py` + `FormulaExpr` (a formula is a composition, not a
  constitution); a bare formula never launches structural synthesis; material identity is resonance-class level
  (COMPATIBILITY §5).
- **Negative control / mutant:** `experiments/v0_6_mutation_calibration.py`; the hostile parser corpus in the v0.6
  funnel.
- **Release corpus evidence:** v0.6 front-door funnel (36 cases); `tests/test_v0_6_funnel.py`; baseline (`plan C2H6O`
  → composition + registry candidates, never a guessed structure; `plan CO` → INPUT_KIND_AMBIGUOUS).
- **Known boundary:** stereochemistry/isotopes/salts not perceived by material matching (declared, COMPATIBILITY §5).
- **Status: MET.**

### 3. No false completeness — every bounded search retains its receipt and bounds
- **Production authority:** `smartchem/search.py` `SearchReceipt` + `section_8_3_label` (the 2×2: empty-COMPLETE vs
  empty-INCOMPLETE never collapsed); `CompilationResponse.__post_init__` cross-checks outcome vs search status so an
  INCOMPLETE outcome can never wear a completion status.
- **Negative control / mutant:** `experiments/v0_7_mutation_calibration.py`, `v0_8_mutation_calibration.py`.
- **Release corpus evidence:** `experiments/v0_7_service_funnel.py` (4 cases); `v0_8_readiness_funnel.py`; baseline
  (methyl_acetate COMPLETE/ROUTES_FOUND vs aspirin INCOMPLETE/exit 4).
- **Known boundary:** completeness is within the DECLARED bounded grammar only; absence in an incomplete search is
  never evidence of absence (COMPATIBILITY §2.1).
- **Status: MET.**

### 4. No unsourced practical claim — formal structure is not silently promoted to a real procedure
- **Production authority:** `smartchem/experiment/readiness.py` — the weakest-link readiness ladder; `PROCESS_SPECIFIED`
  requires a structurally COMPLETE **and** SOURCED procedure (`procedure_representation_is_complete` + a strictly
  separate sourcing conjunct, Lane F KILL 1).
- **Negative control / mutant:** `experiments/v0_8_mutation_calibration.py`; `tests/test_v0_8_procedure_evidence.py`.
- **Release corpus evidence:** `experiments/v0_8_readiness_funnel.py` (44 routes / 102 steps, all FORMAL_CANDIDATE;
  downstream tiers shrink exactly as evidence coverage requires).
- **Known boundary:** evidence-subject binding records deferred post-1.0 (COMPATIBILITY §6).
- **Status: MET.**

### 5. Generation and verification are distinguishable
- **Production authority:** generation (`run_compilation` / the search) vs verification (`load_response` /
  `VerificationPolicy` / `smartchem/transport_ledger.py`); the `VerificationReceipt` is OUT OF BAND (never on the wire,
  cannot be forged); verification work is budgeted in deterministic units.
- **Negative control / mutant:** `experiments/v0_9_5_canonical_differential.py`; the baseline tamper matrix;
  `tests/test_v0_9_5_loader_laws.py`, `tests/test_v0_9_5_loader_hardening.py`.
- **Release corpus evidence:** canonical differential (CI 3570/3570); `tests/test_v1_0_compatibility.py` (a
  consistent rewrite of what the search FOUND is refused except by re-execution/HMAC).
- **Known boundary:** thin transport is advisory by contract; a keyless consumer must treat the search output as
  advisory (COMPATIBILITY §4).
- **Status: MET.**

### 6. Poor-man fit is whole-route fit
- **Production authority:** `smartchem/capability/` — the capability compiler projects the WHOLE route through the
  declared bench, axis by axis, with weakest-link aggregation; `CAPABILITY_FIT` requires `PROCESS_SPECIFIED`.
- **Negative control / mutant:** `experiments/v0_9_mutation_calibration.py`; `tests/test_v0_9_5_evidence_soundness.py`
  (a REACHABLE false `CAPABILITY_FIT` is release-blocking).
- **Release corpus evidence:** `experiments/v0_9_capability_funnel.py` (7 routes, cumulative-AND funnel, per-axis
  census never narrowed).
- **Known boundary:** zero production `CAPABILITY_FIT` today (honest ceiling — no corpus page states a disposal;
  representability proven by a synthetic witness). `CAPABILITY_FIT` is a profile-fit claim, never safety (law 7, 10).
- **Status: MET.**

### 7. Unknown is never free, safe, feasible, pure, or zero
- **Production authority:** the fail-closed verdict rules — `UNKNOWN`/`UNCONSTRAINED` never pass; a real demand on an
  unmodeled/unevidenced capacity reads `UNKNOWN`; `StreamDisposition` is the one discharge vocabulary and requires
  `SOURCE_QUOTED` evidence bound to one subject.
- **Negative control / mutant:** `tests/test_v0_9_5_evidence_soundness.py`, `tests/test_v0_9_5_stream_disposition.py`,
  `tests/test_v0_9_5_disposition_consumption.py`; `experiments/v0_9_mutation_calibration.py`.
- **Release corpus evidence:** v0.9 capability funnel (every unmodeled/unevidenced axis → non-FIT);
  `experiments/v0_9_5_stress.py`.
- **Known boundary:** `CONSUMED_COMPLETELY` on an excess reagent is a sourced claim the model cannot cross-check
  without a unit engine (declared, COMPATIBILITY §6).
- **Status: MET.**

### 8. Every strong recommendation is replayable / provenance-bound
- **Production authority:** `result_digest` binds `tool_version`; canonical transport ships RE-DERIVABLE evidence;
  `load_response` re-derives or binds every verdict-bearing field; pinned / verified-admission / authenticated /
  re-executed trust tiers.
- **Negative control / mutant:** the baseline tamper matrix (digest flip, transport relabel, verdict relabel, dossier
  deletion, pin mismatch, signature policy); `experiments/v0_9_5_canonical_differential.py`.
- **Release corpus evidence:** `tests/test_v1_0_compatibility.py` (re-execution across the version boundary is
  REFUSED, not silently accepted); canonical differential (CI 3570/3570); stress `cross_process_result_digest`.
- **Known boundary:** pin requests and verdicts, not result digests, across version upgrades (COMPATIBILITY §2.2).
- **Status: MET.**

### 9. Every genericity claim is measured on holdouts
- **Production authority:** the genericity reorientation — a generic bounded SEARCH compiler parameterized by a
  narrowing transform algebra; genericity is MEASURED on blind held-out cases, never asserted.
- **Negative control / mutant:** the Round-V blind held-out oracle + probe
  ([`V0_9_RC_ROUND_V_HELDOUT_ORACLE_2026-09-28.md`](V0_9_RC_ROUND_V_HELDOUT_ORACLE_2026-09-28.md),
  [`…_HELDOUT_PROBE_RESULTS_2026-09-28.md`](V0_9_RC_ROUND_V_HELDOUT_PROBE_RESULTS_2026-09-28.md)).
- **Release corpus evidence:** the frozen 1.0 funnels (v0.6/0.7/0.8/0.9) measured on predeclared corpora; the Round-V
  blind held-out result (12/1/0).
- **Known boundary:** genericity is claimed only over the measured transform algebra (Lane B), never beyond it.
- **Status: MET.**

### 10. Stable semantics, incomplete chemistry
- **Production authority:** [COMPATIBILITY.md](../../COMPATIBILITY.md) (the stability contract); the executable
  public-contract freeze [`V1_0_PUBLIC_CONTRACT_FREEZE.json`](V1_0_PUBLIC_CONTRACT_FREEZE.json); the single version
  source `smartchem.__version__`.
- **Negative control / mutant:** `tests/test_v1_0_public_contract.py` (fires on ANY stable-surface drift);
  `tests/test_v1_0_version_transition.py` (fires on ANY semantic move under a package bump).
- **Release corpus evidence:** public contract `--check` NO DRIFT; version transition PROVEN (29 expected moves, 0
  unexpected); install matrix (all 4 Pythons agree with source).
- **Known boundary:** chemistry is intentionally incomplete; `UNKNOWN`/unsupported is a valid 1.0 answer; new families
  are a post-1.0 MINOR under the contract (§12 non-blockers).
- **Status: MET.**

**Ledger verdict: 10 / 10 MET. No law lacks machine evidence; no 1.0 blocker among the laws.**

---

## Final 1.0rc1 gate run

Validation at the 1.0rc1 code tip (`release/1.0.0`). Fresh = re-run at 1.0rc1 this round; Inherited = receipt over
unchanged source, carried by the version-transition proof.

| gate | result | freshness |
|---|---|---|
| OOM-safe full suite (`scripts/run_suite.sh`, 311 files, PySCF present, RDKit absent) | **7523 passed, 0 failed, 0 errors, 47 skipped** (7570 collected), 37 batches | Fresh @ 1.0rc1 |
| v0.9 mutation calibration | ACTIVE **375/375 killed, 0 survived**; RETIRED 4 (0 void); DEFERRED 0 | Fresh @ 1.0rc1 |
| v0.8 mutation calibration | **20/20 killed** | Fresh @ 1.0rc1 |
| v0.7 mutation calibration | **17/17 killed** (M1–M17) | Fresh @ 1.0rc1 |
| v0.6 mutation calibration | **14/14 killed** (all mutation-control tests non-vacuous) | Fresh @ 1.0rc1 |
| v0.6 front-door funnel | 36 cases; every malformed/parametric input a correct typed refusal (exit 0) | Fresh @ 1.0rc1 |
| v0.7 algebra + service funnels | algebra 6 cases + service 4 cases (exit 0) | Fresh @ 1.0rc1 |
| v0.8 readiness funnel | 44 routes / 102 steps, all FORMAL_CANDIDATE; downstream tiers shrink by evidence (exit 0) | Fresh @ 1.0rc1 |
| v0.9 capability funnel (zero-FIT theorem) | **34/34 properties hold**; 7/7 routes diverge; exactly 1 PROCESS_SPECIFIED; isopentyl under Custom bench overall UNKNOWN, never FIT | Fresh @ 1.0rc1 |
| RC funnel (`v0_9_5_rc_funnel.py`) | **63/63 MATCH** (0 mismatch, 0 pending) | Fresh @ 1.0rc1 |
| search noninterference (`v0_9_search_noninterference.py`) | **HOLDS** — all must-equal search fields identical across 4 capability contexts | Fresh @ 1.0rc1 |
| canonical differential (`v0_9_5_canonical_differential.py`) | verdict **PASS**; relabel-invariant (the 2 refused / 5 timeout literals that now resolve are a performance widening vs the differential's own reference, invariance preserved) | Fresh @ 1.0rc1 |
| stress (`v0_9_5_stress.py`) | **8/8 invariants PASS** (roundtrip 31, replay 31, cross-process-result-digest 6, profile-noninterference 80, kekule 10, receipt-consistency 120, cache-on/off 31, policy-only-promised-changes 186); 0 fail, 0 pending, 0 vacuous | Fresh @ 1.0rc1 |
| boundary fuzz (`v0_9_5_boundary_fuzz.py`) | 18,599 inputs, zero untyped escapes (0.9.5 CI receipt) | Inherited (receipt; source unchanged) |
| baseline behaviour freeze (`v0_9_5_baseline_freeze.py --check`) | NO DRIFT at merge; version-bound-only drift at 1.0rc1 | Fresh @ 1.0rc1 |
| version-transition differential (`v1_0_version_transition.py`) | PROVEN: 29 expected moves, 0 unexpected | Fresh @ 1.0rc1 |
| public-contract freeze (`v1_0_public_contract.py --check`) | NO DRIFT | Fresh @ 1.0rc1 |
| dependency-floor (numpy 1.24.0 / scipy 1.10.0 / py3.10) | pip-check clean; 73 numpy/scipy tests pass; CLI smoke OK | Fresh @ 1.0rc1 |
| reproducible build (`scripts/build_release.py` ×2) | byte-identical wheel + sdist; generator `setuptools (84.0.0)` recorded | Fresh @ 1.0rc1 |
| wheel/sdist install matrix (3.10/3.11/3.12/3.13) | ALL ENVIRONMENTS AGREE (13 commands × 8 envs, byte-identical to source) | Fresh @ 1.0rc1 |
| hosted CI | <!--CI--> | pending push (Phase 13) |

---

## Release-engineering checklist (program §Release engineering)

- [x] version metadata and package docs agree (`__version__` = `1.0.0rc1`, dynamic; description corrected)
- [x] README capability claims match current main (current-tense updated; history preserved)
- [x] ROADMAP points to the finite ladder with the stopping rule explicit
- [x] stale current-tense comments corrected without falsifying history
- [ ] CI/workflow state green on the actual RC (recorded under "hosted CI" above) <!--CI_CHECK-->
- [x] supported Python versions tested (3.10–3.13 install matrix, fresh)
- [x] installed CLI behavior tested from a built wheel/sdist, not editable source (install matrix)
- [x] schemas versioned with migration notes (COMPATIBILITY §3; public-contract freeze)
- [x] release corpus and validation receipts committed (`experiments/`, this file)
- [x] no unexplained xfails (the suite carries zero xfail markers; PR #79 discharged the last)
- [x] documented compatibility/deprecation policy (COMPATIBILITY §10)

---

## Not a 1.0 blocker (program §12 — declared, not reopened)

Zero production `CAPABILITY_FIT` (representability proven); evidence-subject binding beyond current; temperature
domain-of-validity modeling; lower-bound-only physical requirements; synonym support; perfect CIP; universal mechanism
discovery; broader transform coverage; perfect yields; additional QC tiers; expert-path AUTO precedence; the declared
formula fall-through; worst-case verifier work bounded-but-not-tiny; DAG capability projection beyond its declared
boundary. A 1.0 system may correctly answer UNKNOWN / DEFERRED / UNSUPPORTED on these.
