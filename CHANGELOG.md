# Changelog

All notable changes to **SmartChem** are recorded here. The project follows [SemVer 2.0](https://semver.org/) and the
stability contract in [COMPATIBILITY.md](COMPATIBILITY.md): from 1.0, new chemistry may widen coverage but must not
silently change the meaning of an existing verdict word.

This file summarises the finite chemical-compiler release arc. The exhaustive per-round evidence lives in the linked
`docs/research/` records; a downstream adopter should be able to understand the 1.0 contract from this page alone.

---

## [1.0.0] — 2026-10-02

**Stable promotion from `1.0.0rc1`. No compiler-semantic change.** The chemical-compiler semantics — identity,
bounded search completeness, the readiness ladder, capability projection, the evidence / `StreamDisposition` contract,
and verified transport — are exactly those frozen and proven in `1.0.0rc1` (below). This release moves only the
package/release identity that is permitted to move: `smartchem.__version__` (`1.0.0rc1` → `1.0.0`), the `tool_version`
and `result_digest` fields it binds, the implementation digest, the `--version` banner, and the artifact
filenames/hashes.

The promotion is proven, not asserted. The version-transition differential
(`experiments/v1_0_version_transition.py --diff`) reports **29 expected moves and 0 unexpected**; the
version-independent fingerprint (`--check-golden`) and the public contract (`v1_0_public_contract.py --check`) both
report **NO DRIFT** with no re-freeze — the RC contract *is* the stable contract — and the regenerated CLI goldens
moved only `tool_version` and `result_digest`. Full evidence remains the RC gate:
[`docs/research/V1_0_RELEASE_GATE.md`](docs/research/V1_0_RELEASE_GATE.md).

## [1.0.0rc1] — 2026-10-02

The first release candidate for **SmartChem 1.0** — the finite chemical-compiler program, frozen, packaged, and proven
to survive installation and a version transition. No new chemistry; the 1.0 line is a stability and packaging line.

Detailed gate: [`docs/research/V1_0_RELEASE_GATE.md`](docs/research/V1_0_RELEASE_GATE.md). Program:
[`docs/research/CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md`](docs/research/CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md).

### The release arc (0.6 → 0.9.5, all merged)

- **0.6 Human Chemical Front Door** — one tolerant entrance for ordinary chemical notation; a lossless `FormulaExpr`
  layer and one identity authority; a formula is a *composition, not a constitution*, and ambiguity is reported, never
  guessed. ([record](docs/research/V0_6_HUMAN_CHEMICAL_FRONT_DOOR_IMPLEMENTATION_2026-09-26.md))
- **0.7 Production Chemical Algebra** — generation became a typed, content-bound *compiler algebra* (the default
  certified multi-family route algebra); a chemistry-bearing change moves the request `semantic_digest`, a prose edit
  does not. ([record](docs/research/V0_7_PRODUCTION_CHEMICAL_ALGEBRA_RELEASE_2026-09-27.md))
- **0.8 Real Route Dossiers** — every candidate carries a *derived*, weakest-link readiness ladder
  (`FORMAL_CANDIDATE` < `REACTION_VOUCHED` < `CONDITIONS_SUPPORTED` < `PROCESS_SPECIFIED`); the top tier needs a
  structurally complete, *sourced* procedure. ([record](docs/research/V0_8_REAL_ROUTE_DOSSIERS_RELEASE_2026-09-28.md))
- **0.9 Capability Compiler** — `--capability-profile` projects each route through a declared bench, axis by axis; a
  real demand on an unmodeled or unevidenced capacity reads `UNKNOWN`, never a pass.
  ([record](docs/research/V0_9_CAPABILITY_COMPILER_RELEASE_2026-09-28.md))
- **0.9.5 Coverage / Adversarial RC** — consolidation, bounded verification work, the minimum pre-1.0 representation
  gaps (notably `StreamDisposition`), and a whole-product adversarial attack; the public semantics were frozen here.
  ([record](docs/research/V0_9_5_ADVERSARIAL_RC_RELEASE_2026-10-01.md),
  [architecture freeze](docs/research/V0_9_5_ARCHITECTURE_FREEZE.md))

### Stable machine semantics (frozen — [COMPATIBILITY.md](COMPATIBILITY.md) §2)

The **machine** surface is stable: the versioned JSON wire and its schema ids, the exit codes, the refusal *classes*,
and the public Python entry points (`build_recompile_request`, `build_decompile_request`, `run_compilation`,
`response_to_payload`, `load_response` / `load_response_text`, `response_from_payload`, `deserialize_response`,
`request_to_payload`, `request_from_payload`, `response_schema`, and `smartchem.verification.VerificationPolicy` /
`VerificationBudget` / `VerifiedLoad`), plus the CLI verbs `plan`, `recompile`, `decompile`, `compile`. The exact
stable verdict vocabulary (`ResponseOutcome`, `search_space_status`, the readiness ladder, process/route fit,
capability status, transport mode) is frozen as an executable invariant in
[`docs/research/V1_0_PUBLIC_CONTRACT_FREEZE.json`](docs/research/V1_0_PUBLIC_CONTRACT_FREEZE.json)
(enforced by `tests/test_v1_0_public_contract.py`). Human prose, timing, telemetry, private names, and the
non-contract verbs (`synthesize`, `audit`) are **not** stable.

### Bounded search completeness

Completeness is *within the declared bounded grammar only*. A `SearchReceipt` states whether the search exhausted its
declared space or stopped at a budget/depth/result cap; an incomplete search never looks complete, and the absence of
a route in an incomplete search is never evidence of absence.

### Verification / trust model

`load_response(payload, VerificationPolicy) -> VerifiedLoad(response, receipt)` re-derives or binds every
verdict-bearing field; the **receipt is out of band** (never on the wire, cannot be forged or copied into a stronger
one). Trust tiers run thin (advisory) → canonical → pinned → verified-admission → authenticated (HMAC) → re-executed.
Verification work is **budgeted in deterministic units** (`VerificationBudget`); exhaustion raises
`VerificationBudgetExceeded` and means verification *did not complete* — it never skips, clamps, or weakens a check.

### Known boundaries (honest, not defects)

- **Zero production `CAPABILITY_FIT`.** `CAPABILITY_FIT` is *representable* — a synthetic witness proves the verdict is
  reachable — but no current corpus page states a stream disposal, so **no production route reaches `CAPABILITY_FIT`
  today**. `CAPABILITY_FIT` is a profile-fit claim, **never a safety certificate**.
- Deferred with exact boundaries (post-1.0, [COMPATIBILITY.md](COMPATIBILITY.md) §6): evidence *subject*-binding
  records, temperature domain-of-validity laws, lower-bound-only physical requirements, typed endpoints / pH
  indicators. Chemistry coverage is intentionally incomplete; `UNKNOWN` / unsupported is a valid 1.0 answer.

### Compatibility

- **Legacy v0.8 wire** (request `…-v1alpha5`, response `…-v1alpha15`) is **read-only** and supported for the whole
  **1.x** series; removing it is a MAJOR, announced one MINOR in advance.
- **0.9.x pre-release wires** carry no compatibility promise and are **refused** with a recompile hint — the package
  version becoming 1.0 does not migrate them.
- A **version bump moves `result_digest` and the implementation digest** (they bind `tool_version`), while the
  request `semantic_digest`, route digests, verdicts, readiness, capability assessments, and schema ids **stay put**.
  Pin requests and verdicts across upgrades, not result digests. This transition is proven field-by-field by
  `experiments/v1_0_version_transition.py` and gated by `tests/test_v1_0_version_transition.py`.

### 1.0 release-candidate engineering (this line, no production-semantic change)

- version bumped to `1.0.0rc1` at the single source `smartchem.__version__`; `pyproject` consumes it dynamically.
- executable **public-contract freeze** and **version-transition** gates added (above).
- package metadata corrected to describe the product as it exists; classifiers and project URLs added.
- **reproducible release build** proven: two builds from a clean `git archive` export produce byte-identical wheel and
  sdist; the resolved setuptools generator is recorded in `release_manifest.json` (the build backend floats at
  `setuptools>=77`, so "same source + same builder → same bytes" is the reproducibility contract).
- clean-install matrix exercised across Python **3.10 / 3.11 / 3.12 / 3.13**, wheel and sdist, with no source tree on
  `sys.path`.

[1.0.0]: https://github.com/femboy2112/SmartChem/releases/tag/v1.0.0
[1.0.0rc1]: https://github.com/femboy2112/SmartChem/tree/release/1.0.0
