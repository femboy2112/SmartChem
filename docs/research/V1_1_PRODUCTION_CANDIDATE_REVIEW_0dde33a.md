# Production 1.1 Release-Candidate Review — `pr101/production-1-1-rc` @ `0dde33a`

*Round VII Wave E1. Exact-SHA review dossier for the 20-class production candidate. Every load-bearing number below
was verified on the filesystem / via `gh` (not taken on a subagent's word). No merge, tag, release, or push is
authorized by this document — it is the review packet the owner decides on.*

## 0. Coordinates (verified)

| | value | how verified |
|---|---|---|
| Candidate branch | `pr101/production-1-1-rc` | `git ls-remote origin` → `0dde33a9fab3b182f88a51010c7d12ddd4ef4a92` |
| Candidate HEAD | `0dde33a` | worktree `git rev-parse HEAD` |
| Stable `main` | `99fce3475a4b502fdaedc409954d8a1c7fb53da2` | `git rev-parse main` |
| Candidate version | `1.1.0a1` | `smartchem/__init__.py:33` |
| `main` version | `1.0.0` | — |
| CI run | `39897599474` — **success**, 7 jobs, event `workflow_dispatch`, head `0dde33a` | `gh run view 39897599474` |
| Commits over `main` | 41 | `git rev-list --count 99fce34..0dde33a` |
| Diff over `main` | 77 files, +7422/−352 (production `smartchem/`: 13 files, +2525/−175) | `git diff --stat` |

The candidate is the 20-class production stream **without** the experimental `experiments/sandbox_foundation/`
package: `git ls-files | grep -c sandbox_foundation` → **0**. It carries no `V2_0_*` / `V3_0_*` / `PHYSICALIZATION_*`
docs. It has no PR of its own; PR #101 tracks the mixed-scope feature branch (`feat/chemical-graph-projections`,
head `3ffc2fd`), of which `0dde33a` is **not** an ancestor (the #110/#111/#115 chemistry was replayed onto the
clean production prefix — the Round V Option-B candidate).

## 1. What ships in 1.1 (`main..0dde33a`)

- **Version boundary.** `__version__` 1.0.0 → 1.1.0a1 (a declared MINOR coverage boundary). The version-independent
  fingerprint golden (`V1_0_VERSION_INDEPENDENT_FINGERPRINT.json`) re-freezes only the two paracetamol
  `invariant_sha` leaves; the anchor hashes soundness-relevant verdict invariants, not a volatile route count.
- **Oracle growth 17 → 20.** #110 activated acyl transfer (18th), #111 alkyl sulfonate-ester transfer (19th),
  #115 Claisen condensation (20th); plus #126 forged-centre retirement, #131 typed recognition outcomes, #132
  pericyclic content-determinism, an `is_closed_shell_neutral` scope doc.
- **Search / routes.** #124 refuses ancestor-as-leaf cyclic dependencies (a no-op under the current strict-rank
  rule, by its own comment); `single_cut_capped_scissions` in `structure_descent.py`; #114 opt-in
  `bond-order-edit-v1` algebra profile (NOT a default; its routes are demoted to `FORMAL_CANDIDATE`).
- **Graph workbench.** New `graph_projection.py`, `graph_cli.py`, `depiction.py`; a new `smartchem graph` CLI verb;
  an optional `depiction = ["rdkit>=2024.3"]` extra.
- **CI.** The PySCF smoke job now uses the batched `scripts/run_suite.sh` (120-min timeout).

## 2. The 20-class recognition boundary (verified: 20 entries in `reaction_type_oracle.py::_RECOGNIZERS`)

3 condensations (acyl / etherification / N-alkylation) · activated acyl transfer (#110) · sulfonate-ester transfer
(#111) · Claisen **condensation** (#115) · 8 Diels–Alder (alkene/alkyne/aza/oxa/thia/1-aza/1-oxa/1-thia) · 4 [3,3]
(Cope / Claisen **rearrangement** / aza-Claisen / thia-Claisen) · 2 electrocyclizations (4π / 6π) = **20**, of which
14 are pericyclic. The Claisen **condensation** (#6) is kept distinct from the Claisen **rearrangement** (#16) by
both recognizer names and tests. A VOUCH means "a mechanism of this reaction TYPE exists" — it is a reaction-type
claim, **not** a feasibility/yield claim; the oracle only ADDS readiness blockers.

## 3. Version / API / wire disposition

- `pyproject.toml` reads the version dynamically from `smartchem/__init__.py` (single-source). `1.1.0a1` is a
  pre-release string → COMPATIBILITY §1 grants no inter-prerelease compatibility promise.
- **No change** to any stable wire schema id, `semantic_digest`, request digest, or verdict vocabulary: the oracle
  is a readiness-layer DEMOTER (`route_reaction_type_blockers`), not a digest provider. The only new schema id is the
  new graph projection's own (`smartchem/graph-projection-v0a1`).
- **Does** move with the version (documented non-stable, COMPATIBILITY §2.2): `result_digest`, `tool_version`, and
  the readiness of paracetamol-class routes (the Ac2O route goes `FORMAL_CANDIDATE` → `PROCESS_SPECIFIED`, a declared
  MINOR promotion). Additive public surface: the `graph` CLI verb (listed under `present_noncontract`), the new
  modules, the opt-in algebra profile.
- **Forensic strength gap (SOURCE_INSPECTED, not fully verified):** the field-by-field `semantic_digest`-invariance
  differential exists for **#110** (`V1_1_COVERAGE_EXPANSION_110.md`, route digest byte-identical). #111 and #115 have
  **no** equivalent committed differential against the 1.0.0 baseline — the evidence is "the golden was not re-frozen
  by those commits + CI green". Weaker than the #110 proof; flagged, not hidden.

## 4. Soundness / regression evidence (on the candidate)

Adversarial corpora + gates present on `0dde33a`: per-class tests for #110/#111/#115 (the Claisen file carries 10
positives + 11 named fictions with per-guard mutation controls); `test_pericyclic_layer_a_fuzz_132.py` (14×14 identity,
no cross-poach); `test_issue_126_forged_center.py` (no caller-settable centre mints a vouch);
`test_independent_recognition_corpus_s3.py` (held-out, `false_vouch == 0`, recall 10/10); the poor-man R56–R63 gates;
`chem_differential_fuzzer.py` (frozen hash). **#115 independence caveat:** the strong adversarial evidence
(principal-run 0-false-VOUCH; 3920-step fuzz) lives on the *feature branch* docs, not the candidate; the held-out S3
corpus predates #111/#115 and contains no Claisen-condensation case; the oracle re-uses the generator's own scission
machinery (`V1_5_RELEASE_PROGRAM.md §1`: "an internal consistency witness, explicitly NOT an independent
external-chemistry witness"). So #115's candidate-side evidence is its own test file — honest-strength, not a proof.

## 5. Frozen-hash provenance

`V1_0_VERSION_INDEPENDENT_FINGERPRINT.json` (living regression anchor) — only the two paracetamol `invariant_sha`
leaves moved; it hashes verdict invariants, not a bare route count. The poor-man probe `FROZEN_HASH` was re-frozen
(`poor_man_reaction_type_oracle_probe.py`) over a payload that includes frontier route counts; its `validate()`
asserts the real invariants (`false_vouch_count == 0`, `reals_vouched >= 1`) separately. Its sibling
etherification-probe comment still blames "pre-existing route-count nondeterminism" — a stale rationale: the feature
branch later REFUTED that (total_frontier_routes stable at 29 over ~25 sweeps; the hash diffs were deterministic
code-state effects). Whether the candidate's poor-man anchors flake run-to-run is **UNKNOWN** on the candidate (not
re-run here); the feature-branch evidence says they do not.

## 6. Optional backends

Core deps: `numpy>=1.24`, `scipy>=1.10` only. PySCF is an optional `qc` extra, import-guarded (`pyscf_oracle.py`
try/except, raises at use); its `slow` tests skip without `--runslow`. RDKit is import-guarded in `depiction.py`
(degrades to name/formula boxes) and `importorskip`-skipped in tests. **Doc drift:** `COMPATIBILITY.md §8` and
`V1_5_RELEASE_PROGRAM.md §9` still call RDKit "development-only", but the candidate now ships a user-facing
`depiction` extra and runtime RDKit use — worth reconciling before a final 1.1.0.

## 7. CI + wheel parity

CI run `39897599474`: all 7 jobs success on `0dde33a` — `test (3.10)`, `test (3.12)`,
`Wheel install matrix (3.10/3.11/3.12/3.13)`, `Optional PySCF backend (smoke)`. The wheel-install-matrix job runs
`build_release.py` + `v0_9_5_install_matrix.py` (console scripts, package data, implementation digest). **Pass count
UNKNOWN for this run** — `gh run view --log` returns nothing (logs unavailable); the "7655 passed" figure in the PR
body belongs to the older `34e1891`, not `0dde33a`.

## 8. Known limitations (candidate's own docs)

`is_closed_shell_neutral` is a representation-relative heuristic with documented false-accepts (O₂, `O=[N]=O`) and
representation dependence — the real fix is #105 (2.0). #111 covers alkyl-O only (aryl-O deferred). #114 is
reachability, not recognition (routes stay `FORMAL_CANDIDATE`; promotion's search-cost blast radius unmeasured at
scale). Stereochemistry and per-atom charge are not perceived by material matching (COMPATIBILITY §5). #115 is
type-validity only; the stoichiometric base is Problem B / #107.

## 9. Disposition

The candidate is a **real, separately reviewable, green** 1.1 release candidate: 20-class production oracle, clean of
the experimental 2.0 stream, CI-green on its exact SHA. It is **not merged, tagged, or released**, and this document
authorizes none of those. Recommended before a final `1.1.0`: (a) reconcile the RDKit "dev-only" doc drift (§6);
(b) decide whether #111/#115 need a #110-grade `semantic_digest` differential (§3); (c) refresh the poor-man anchor
rationale comment (§5). None is a blocker for review; all are truth-in-labeling.

---

## Appendix — drafted replacement for the stale PR #101 body (owner to approve posting; NOT posted by this review)

> The current PR #101 body (head `3ffc2fd`) still claims the sandbox has "78 tests", is "numpy/scipy only, no
> `smartchem` coupling", and reports CI/suite at `34e1891` — all stale. Verified stale on the live body
> (lines 15, 21, 23). Suggested corrected body:

**Scope — draft, branch only.** Post-1.0 development arc on `feat/chemical-graph-projections` (head `3ffc2fd`,
`__version__ = 1.1.0a1`). `main` (`99fce34`) and the `v1.0.0` tag are untouched. Intentionally mixed-scope: a
production 1.1 stream and an experimental 2.0 stream.

**Production 1.1 stream** (`smartchem/`). Oracle now recognizes **20 reaction classes** (main: 17): #110 activated
acyl transfer (18th), #111 sulfonate-ester transfer (19th), #115 Claisen condensation (20th). #114 (opt-in
`bond-order-edit-v1`) is reachability, not a recognizer. Oracle is a readiness DEMOTER → recognizers move readiness
but not `semantic_digest` (declared MINOR boundary documented for #110 in `V1_1_COVERAGE_EXPANSION_110.md`; #111/#115
have no equivalent differential). Plus graph/synthesis workbench and #124/#126/#128/#129/#131/#132 fixes.

**Experimental 2.0 stream** (`experiments/sandbox_foundation/`, not in the production package). ~500 sandbox tests at
`3ffc2fd` (earlier descriptions said 78). It **imports `smartchem`** in its mechanism-adapter modules, so it is not
decoupled. Carries a committed PHREEQC benchmark of the aqueous model; it does **not** validate the real oracle
against measured data.

**1.1 release candidate.** Branch `pr101/production-1-1-rc` @ `0dde33a` is the 20-class production stream without the
sandbox. CI run `39897599474` (workflow_dispatch) green, 7 jobs on exactly `0dde33a`. Not merged, tagged, or released.

**Verification.** Head `3ffc2fd`: CI run `39986004902` (pull_request) green, 9 jobs incl. both Sandbox-foundation
jobs. The older `34e1891` "7655 passed" figure is not current.

**Non-goals.** No change to the stable 1.x wire schema ids, `semantic_digest`, request digest, or verdict vocabulary.
`result_digest` / `tool_version` move with the version bump (documented non-stable, COMPATIBILITY §2.2). One additive
non-contract CLI verb (`graph`) and one opt-in algebra profile. No new empirical feasibility claims.
