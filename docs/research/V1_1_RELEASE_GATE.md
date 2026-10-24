# SmartChem 1.1.0 — Release Gate

*The exact-SHA gate for the 1.1.0 production release. Every claim here is verified on the filesystem / via `gh`;
fields that only exist after a downstream step are marked `⟨PENDING …⟩` and filled at that step. This document
authorises nothing by itself — the maintainer authorised the gated full run; this is the evidence ledger for it.*

## 0. Coordinates

| | value | how verified |
|---|---|---|
| release branch | `release/1.1.0` | cut from the green production RC `pr101/production-1-1-rc` @ `0dde33a` |
| release HEAD | `⟨PENDING — set at commit/push⟩` | — |
| production RC base | `0dde33a9fab3b182f88a51010c7d12ddd4ef4a92` | `git rev-parse` |
| stable `main` | `99fce3475a4b502fdaedc409954d8a1c7fb53da2` | `git rev-parse main` |
| previously released | `v1.0.0` = `8345bbb` | tag |
| version this release | `1.1.0` | `smartchem/__init__.py:33` |
| merged-`main` SHA | `⟨PENDING — set at merge⟩` | — |
| release CI run | `⟨PENDING — set after the PR event⟩` | — |
| merged-`main` CI run | `⟨PENDING — set after the push:main event⟩` | — |

## 1. Scope of the release (what ships in `smartchem/`)

The 20-class production stream, **clean of the experimental 2.0 sandbox**: `git ls-tree -r <HEAD> | grep -c
sandbox_foundation` → **0**; no `V2_0_*` / `V3_0_*` / `PHYSICALIZATION_*` docs. 20 recognizers in
`reaction_type_oracle.py::_RECOGNIZERS` (counted). The additive, non-contract `graph` CLI verb; the opt-in
`bond-order-edit-v1` profile (demoted to `FORMAL_CANDIDATE`, not a default); the optional `depiction` extra. No
default-algebra change. Existing 1.0 public contracts preserved (§3).

## 2. Review-finding dispositions (from `V1_1_PRODUCTION_CANDIDATE_REVIEW_0dde33a.md`)

| finding | disposition | evidence |
|---|---|---|
| #111 / #115 lacked a #110-grade differential (§3) | **CLOSED** | `V1_1_COVERAGE_EXPANSION_111_115.md` + `experiments/v1_1_coverage_expansion_111_115_probe.py` (both families `None`→class, 17→20; `semantic_digest` 0/15 moves) |
| RDKit "dev-only" doc drift (§6) | **CLOSED** | COMPATIBILITY.md §8, V1_5_RELEASE_PROGRAM.md §9, README reconciled to optional two-role (dev oracle + runtime `depiction` extra), never changes a verdict |
| stale poor-man route-count comment (§5) | **CLOSED** | `experiments/poor_man_etherification_recognizer_probe.py` comment corrected (conjecture refuted, dangling sandbox-doc ref removed); `FROZEN_HASH` untouched |

## 3. Version-transition proof (`1.1.0a1 → 1.1.0`, pure package bump)

Verified locally against the worktree (editable install shadowed with `-S` + worktree/site-packages on
`PYTHONPATH`; `smartchem.__file__` confirmed in the worktree):

- **`experiments/v1_0_version_transition.py --diff` (1.1.0a1 → 1.1.0):** `UNEXPECTED moves (0)`;
  "VERSION TRANSITION PROVEN: only the declared tool-version-bound fields moved."
- **`--check-golden` (version-independent fingerprint):** `NO DRIFT (semantic content unmoved by the version bump)` — no re-freeze.
- **`experiments/v1_0_public_contract.py --check`:** `NO DRIFT`.
- **CLI goldens** (`tests/regen_cli_json.py`): the only changed leaves are `tool_version` (×10) and
  `result_digest` (×10); no verdict / `semantic_digest` / schema-id move.
- **`--version` banner and single-source** are asserted dynamically against `smartchem.__version__` (no literal golden).

### Coverage transition `1.0.0 → 1.1` (the sanctioned MINOR)

The v1.0.0 → 1.1 diff moves only the version-bound set + the #110 paracetamol readiness promotion (30 moves, all
confined to `paracetamol` / `paracetamol@research-lab`); `semantic_digest` byte-invariant on all 15 corpus cases
(explicit per-case check, 0 mismatches). #111/#115 add zero corpus-visible drift (no corpus target routes through
them; exhibited independently in `V1_1_COVERAGE_EXPANSION_111_115.md`).

## 4. Local verification (targeted)

- Version / contract / CLI tests (`test_cli_json`, `test_v1_0_version_transition`, `test_v1_0_public_contract`,
  `test_v0_9_5_release_invariants`, `test_cli`): **66 passed**, exit 0.
- Full OOM-safe suite (`scripts/run_suite.sh`): `⟨PENDING — step 3⟩`.
- Fresh wheel/sdist build + install matrix (3.10–3.13) from the committed release branch: `⟨PENDING — step 3⟩`.
- Pure-Python operation (no RDKit / PySCF): `⟨PENDING — step 3⟩`.

## 5. Artifacts (built from the merged-`main` SHA via `scripts/build_release.py --ref <merged-sha>`)

| artifact | version | SHA-256 |
|---|---|---|
| wheel | `1.1.0` | `⟨PENDING — build⟩` |
| sdist | `1.1.0` | `⟨PENDING — build⟩` |

Reproducibility manifest + `SHA256SUMS`: `⟨PENDING — build⟩`.

## 6. Release BLOCK conditions (halt publication, do not override)

Required CI red/incomplete · final version or artifact metadata wrong · a stable-contract change outside the
declared MINOR allowance · sandbox research in the release branch · a demonstrated new false-VOUCH · a required
review / protection rule blocking merge · artifact identity unestablished · `main` advanced by another agent in a
way that invalidates the evaluated candidate.

## 7. Disposition

`⟨PENDING⟩` — set to SHIP (with merged SHA, CI run, tag + release URLs, artifact hashes) or BLOCKED (with the exact
blocker) at the end of the gated run. No PyPI publication is part of this gate.
