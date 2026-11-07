# SmartChem 1.6.0 — Release Gate

*The exact-SHA gate for the 1.6.0 production release (OPERATION XXIII Phase I). Every claim is verified on the
filesystem or through `gh`. Fields that only exist after a later step are marked `⟨PENDING …⟩`; the post-release
record fills them. This document authorises nothing by itself. The maintainer's conditional authorisation
(OPERATION XXIII) is to merge, tag and publish 1.6.0 only when every gate below passes. No PyPI publication.*

## 0. Coordinates

| | value | how verified |
|---|---|---|
| production source merged | PR #157 → `main` `6a2686edde8368a773de29f7a8228c0d7843e294` (2026-11-06) | `git rev-parse origin/main` |
| previous release | `v1.5.0` → `c3d0d01920175ba9024a594e248ce6dd3412c3df` (annotated tag, unchanged) | `git tag` |
| version this release | `1.6.0` (`smartchem/__init__.py`) | `smartchem.__version__` |
| release-hygiene branch | `release/1.6.0-hygiene` (docs only: README, ROADMAP, CITATION, this file, two cherry-picked XXII roadmap/docs commits) | `git diff --stat main` |
| merged-`main` SHA (the tag target) | `⟨PENDING — set at merge⟩` | — |
| merged-`main` CI run | `⟨PENDING — set after the push:main event⟩` | — |

## 1. Scope — what ships in the wheel and sdist

* `git diff v1.5.0 6a2686e -- smartchem/` touches exactly six files:
  * `__init__.py` (version);
  * `experiment/activator_ledger.py`, `experiment/event_search.py`, `experiment/reaction_type_oracle.py`;
  * `intramolecular_condensation.py`;
  * the new `lactonization_witness.py`.
* **Exactly 25 recognizers:** `len(smartchem.experiment.reaction_type_oracle._RECOGNIZERS) == 25`, observed on
  `6a2686e`.
* **Package isolation.** The 2.0 research simulator lives under `experiments/sandbox_foundation/` (197 tracked files
  on `main`). It is kept out of the artifacts by `pyproject.toml` `[tool.setuptools.packages.find] include =
  ["smartchem*"]` and `MANIFEST.in` `prune experiments`. A trial `scripts/build_release.py` build of `6a2686e` gave
  wheel = 203 files under `smartchem/` + `smartchem-1.6.0.dist-info/`, and sdist = `smartchem/`, `smartchem.egg-info/`
  and top-level metadata only. Zero paths matched `experiments|sandbox|tests/|general_kernel|unified_chemical|libgibson`.
  The final artifacts are re-checked in section 4.
* The release-hygiene change is docs-only. `git diff 6a2686e <release head> -- smartchem/ tests/ pyproject.toml
  MANIFEST.in` is empty, so the production code under test is byte-identical to `6a2686e`.

## 2. Semantic and adversarial gate (P1)

| gate | evidence | result |
|---|---|---|
| complete OOM-safe production suite | `scripts/run_suite.sh` (fresh process per batch, junit tally) on a detached worktree of `6a2686e`; Python 3.12.3, numpy 2.5.1, scipy 1.18.0, PySCF 2.14.0 present, RDKit absent | `⟨PENDING — tally⟩` |
| compatibility / version-transition | `tests/test_v1_0_compatibility.py`, `test_v1_0_version_transition.py`, `test_v0_9_5_release_invariants.py`, `test_v1_0_public_contract.py` | in the suite tally |
| frozen version-independent JSON / `semantic_digest` | the version-independent payload golden in `test_v1_0_version_transition.py` + `test_v1_0_public_contract.py`; the PR #157 golden regeneration moved only `tool_version` + `result_digest` (integrity-guarded) | in the suite tally |
| lactonization positive + adversarial corpora | `test_lactonization_recognizer_xiv.py`, `test_lactonization_masked_carbonyl_xv.py` | in the suite tally |
| independent witness disagreement control | `test_xx_s10_lactonization_witness.py` keeps the hemiacetal-lactone case as a DISAGREEMENT (witness: lactone; oracle: refuses the VOUCH) | in the suite tally |
| typed-event search termination + completeness | `test_event_search_123.py`, `test_event_search_probe.py` | in the suite tally |
| truncation / exhaustion receipt mutation | `test_v0_9_5_loader_hardening.py`, `test_event_search_123.py`, `test_intramolecular_condensation_p2.py` | in the suite tally |
| legacy v0.8 read-only transport | `test_v0_9_round_v_schema_migration.py`, `test_v0_8_readiness_transport.py`, `test_v0_8_procedure_migration.py` | in the suite tally |
| installed wheel / console entry points | the CI wheel-install matrix (3.10–3.13) runs `experiments/v0_9_5_install_matrix.py` against the built artifacts. A local fresh-venv matrix on 3.10/3.11/3.12/3.13 runs `smartchem --version` and `smartchem-verify-probes --help` | `⟨PENDING — final artifacts⟩` |
| hosted CI on the final candidate | 7 required contexts, job-level, on the exact merged SHA | `⟨PENDING⟩` |

**Independent-witness boundary (honest).** The witness `smartchem/lactonization_witness.py` imports only `Molecule`.
An AST audit shows it references no production recognizer symbol. It decides through Tarjan bridges, its own
stoichiometry and its own isomorphism. That proves **implementation** separation, not full **epistemic**
independence. Witness and oracle still share four premises:
* the `Molecule` graph model and its valence/charge conventions;
* the parsed input (the same SMILES front door builds both graphs);
* the same notion of "lactone" as a ring ester;
* the same fixture corpus authors.

A defect in any of those is common-mode. The intentional disagreement — a hemiacetal-bearing lactone formed from a
gem-diol acid, where the witness says *lactone* and the oracle refuses the *carbinol lactonization* VOUCH — is
**preserved** as a documented domain boundary (`docs/research/OPERATION_XXII_LACTONIZATION_WITNESS_VERDICT.md`). It is
not erased by forcing agreement.

## 3. The v1.5 → v1.6 transition

1.6.0 is a MINOR under `COMPATIBILITY.md`. It widens coverage (24 → 25 classes) without changing the meaning of any
verdict word. What moves:
* the version-bound fields (`tool_version`, `result_digest`, the `--version` banner) — five CLI goldens regenerated in
  `13c8bab`, with only those fields moving.

What does not move:
* stable wire schema ids, `semantic_digest`, route digests, the verdict vocabulary;
* the legacy-v0.8 read-only contract;
* the refusal classes.

## 4. Artifact gate (P2)

`scripts/build_release.py --ref <tag target>` (clean `git archive` export, `SOURCE_DATE_EPOCH` = commit time, canonical
sdist repack). The builder environment is recorded from `release_manifest.json` `wheel_generator`. The trial build
resolved `setuptools (84.2.1)` under `uv 0.11.8`.

| artifact | sha256 | size |
|---|---|---|
| `smartchem-1.6.0-py3-none-any.whl` | `⟨PENDING⟩` | — |
| `smartchem-1.6.0.tar.gz` | `⟨PENDING⟩` | — |

Acceptance:
* two independent rebuilds are byte-identical;
* the manifest `commit` equals the tag target;
* the wheel's hashes match the ones the hosted wheel-install-matrix jobs print for the same SHA;
* fresh installs on 3.10/3.11/3.12/3.13 report `smartchem 1.6.0`;
* `smartchem/evidence/manifest.schema.json` and `smartchem/evidence/README.md` (package data) are present;
* no `experiments/` path appears in either artifact.

## 5. v1.5.0 — why the GitHub Release has no assets, and the backfill decision

**Cause (OBSERVED).** The 1.5.0 GitHub Release (published 2026-11-02) carries no assets. Its body has no install/hash
section, unlike 1.1.0's (which lists the wheel URL and both SHA-256s), and no `V1_5_RELEASE_GATE.md` exists. The 1.5
release procedure omitted the build-and-upload step. No failed upload is recorded anywhere.

**Binding evidence (VERIFIED, three independent routes).**
1. `scripts/build_release.py --ref v1.5.0` exports the immutable annotated tag's commit `c3d0d01` (manifest
   `commit` = `c3d0d01920175ba9024a594e248ce6dd3412c3df`).
2. Two local rebuilds are byte-identical: wheel `8fd1e138c944d5eaf0384700b932488972c555e736de9a880af80b784e0a432a`,
   sdist `1ce6182c830e5e4d0ad47288f4f62ce941381ddc69af3b91c4b5e0d4b26274d8`, builder `setuptools (84.2.1)`.
3. The four hosted `Wheel install matrix` jobs of CI run `41400482598` on `c3d0d01` (2026-11-02, at release time:
   jobs `125131028211`, `125131028422`, `125131028326`, `125131028241`) printed **the same two hashes** in their
   build step.

**Decision.** The backfill is bound rigorously enough. The four files are uploaded to the existing v1.5.0 release, and
its notes gain a dated disclosure that they were attached after the initial publication, together with the three
binding routes above. The tag is not touched.
