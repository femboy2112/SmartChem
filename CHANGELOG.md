# Changelog

All notable changes to **SmartChem** are recorded here. The project follows [SemVer 2.0](https://semver.org/) and the
stability contract in [COMPATIBILITY.md](COMPATIBILITY.md): from 1.0, new chemistry may widen coverage but must not
silently change the meaning of an existing verdict word.

This file summarises the finite chemical-compiler release arc. The exhaustive per-round evidence lives in the linked
`docs/research/` records; a downstream adopter should be able to understand the 1.0 contract from this page alone.

---

## [1.5.0] — 2026-10-30 (release candidate — unreleased; not tagged or published)

**Minor release candidate: the full 20 → 24 reaction-class coverage expansion, consolidated from four review
forks, under an unchanged 1.x machine contract.** From 1.0.0 the stable wire schema ids, `semantic_digest`, route
digests, the verdict vocabulary and the readiness/capability semantics remain **byte-invariant**; only the declared
version-bound identity moves (`result_digest`, `tool_version`, the implementation digest, the `--version` banner).
The version-independent payload golden is verified **unmoved** by the coverage expansion (the oracle is a
readiness-layer demoter; a recognizer changes readiness, never a search identity). Full differential + gate ledger:
[`V1_5_CONSOLIDATION_2026-10-30.md`](docs/research/V1_5_CONSOLIDATION_2026-10-30.md).

### Corrected — hostile scientific review (OPERATION XII, 2026-10-31)

A scientific hardening pass on the candidate, all on the feasibility axis (version-independent golden **NO DRIFT**,
recognizer registry digest untouched). Full record:
[`OPERATION_SMARTCHEM_XII_2026-10-31.md`](docs/research/OPERATION_SMARTCHEM_XII_2026-10-31.md).

- **Metal-free hydrogenation (1A).** The universal "a hydrogenation requires a transition metal" was scientifically
  false: metal-free frustrated-Lewis-pair catalysts hydrogenate imines (C=N) and nitriles (C≡N) — Stephan et al.,
  Angew. Chem. Int. Ed. 2007, 46, 8050 — but not aldehydes (C=O). The requirement is now **step-conditional** on the
  reduced bond, with a new `HYDROGEN_ACTIVATION_CATALYST` role (transition metal **or** metal-free FLP) for the
  C=N / C≡N domain, scoped by a structural imine/nitrile witness (an adversarial review proved the element pair
  `{C,N}` alone false-CLEARs oximes / hydrazones / amidines / cumulenes; now excluded).
- **SN2 is a structural type claim (1B).** The recognizer no longer implies it establishes the SN2 *mechanism*: it
  certifies SN2-*compatibility* (a necessary structural condition), resolves no SN1/SN2/E2 competition, and mints no
  stereochemical (inversion) claim. The vouch is the oracle's existential "a mechanism of the SN2 type is
  structurally available".
- **Base-regime classifier (1C).** Verified sound (no fix) against a preregistered source-backed corpus + hostile
  holdouts: the mild/strong split keys on the hydroxyl carbon's own bond, so an allyl alcohol / β-hydroxy carbonyl
  (unsaturation *near* the OH-carbon) correctly stays strong, never false-cleared by a mild base.
- **Event-type certificates (P1).** `classify_event` (the opt-in #123 typed-event search) now **certifies** each
  class's invariants rather than guessing from shape: a `SCISSION` is recognized only when every fragment is
  strictly smaller than the target (the W1 rank-descent the class asserts), so a conserving 2→2 step whose
  principal reactant exceeds the target (e.g. an ester hydrolysis) is refused fail-closed, not mislabeled an
  assembly. The recognition projection is thus independent of the search grammar (reachability) and grammar-safe.
  The deferred `INTRAMOLECULAR_COPRODUCT` class is documented as a **shape** certificate only — it cannot
  distinguish an intramolecular condensation from an intermolecular retro-fragmentation (no atom-map), so
  connectivity-preservation is the future generator's proof obligation.

### Added — reaction-type coverage (20 → 24 recognized classes)

- **#114 hydrogenation** (21st) — `precursor + H2 -> saturated` (a partial bond-order edit; one unsaturation
  reduced). Needs an H2-activation catalyst, keyed on the reduced bond (see the activator ledger): a C=N / C≡N
  reduction (imine / nitrile) clears with a transition metal **or** a metal-free frustrated-Lewis-pair catalyst
  (Stephan 2007); a C=C / C=O reduction needs a transition metal.
- **#111 oxoacid ester condensation** (22nd) — `alcohol + nitric/phosphoric acid -> nitrate/phosphate ester +
  water` (Z ∈ {N, P}; disjoint from the #111 sulfonate recognizer, which owns C–S oxoacid esters).
- **#112 SN2 substitution** (23rd) — `R-X + O/N/S-nucleophile -> R-Nu + halide-salt/HX` at an sp3, non-tertiary
  carbon; locked by the #106 radius-1 environment predicate (sp3 ∧ tetravalent ∧ ≥1 H ∧ single heteroatom
  neighbour) plus an independent single-cut re-derivation. Neutral-graph subset (counterion explicit; the #105
  charge wall is untouched).
- **#119 imine condensation** (24th) — `carbonyl + amine/hydroxylamine/hydrazine -> imine/oxime/hydrazone + water`
  via a new opt-in C=N generator, recognised by an independent retro re-derivation (the C=N must hydrolyse into
  exactly the two declared precursors).

Each class ships its no-false-vouch adversarial corpus. Per-fork evidence:
[`REACTION_ALGEBRA_1_3_P3_FINDINGS_2026-10-30.md`](docs/research/REACTION_ALGEBRA_1_3_P3_FINDINGS_2026-10-30.md),
[`MEGA_ROUND_IX_EXECUTION_REPORT_2026-10-28.md`](docs/research/MEGA_ROUND_IX_EXECUTION_REPORT_2026-10-28.md).

### Added — feasibility, search and admission organs

- **Activator ledger (#107)** — a class-keyed, base-rate-safe **demoter** mapping a recognized class to the
  stoichiometric activator / catalyst it requires (Claisen condensation → enolizing base; the hydrogenation and
  neutral-oxygen SN2 requirements are **step-conditional**, keyed on the step's content rather than its class), so a
  route that names no such reagent sinks to `REAL_BUT_HARD` instead of reading as kitchen-runnable. Pure feasibility layer (rides the `hard_blockers` channel, excluded from `semantic_digest`); it
  can only demote, never false-VOUCH. Carries an import-time re-review guard that fails loud on registry growth.
  Also carries a **conditional** requirement keyed on a step's content, not its class: a neutral-oxygen **SN2**
  (#112) whose nucleophile is protonated (`R-O-H`) needs a stoichiometric base to form the oxy-anion in situ, so a
  baseless such step sinks to `REAL_BUT_HARD` — pKa-regime-aware, so an alcohol (pKa ~16) requires a strong
  alkoxide/hydride base while a carboxylic acid / phenol (pKa ~5 / ~10) clears with a mild carbonate/hydroxide base.
  A metal-salt alkoxide, a neutral amine and a neutral thiol are competent base-free and carry no requirement.
- **Bounded typed-event route search (#123)** — an opt-in `search_event_routes` that makes the oracle-vouched
  [3,3]-sigmatropic / electrocyclic families reachable from retrosynthesis, with a separate well-founded
  termination proof. `search_routes` and its frozen receipt are untouched; `lateral_hops=0` reproduces the exact
  scission route set. [`BOUNDED_EVENT_SEARCH_1_4_P4_FINDINGS_2026-10-30.md`](docs/research/BOUNDED_EVENT_SEARCH_1_4_P4_FINDINGS_2026-10-30.md).
- **DAG-admission recognition gate (#144)** — re-derives recognition from the thick replay payload at admission,
  identity-bound, so a DAG step cannot be admitted on `fit_status` alone.
- **#106 radius-1 environment predicate** (`smartchem/radius1_environment.py`) — a recognizer-local atom-environment
  discriminator (the SN2 lock); not a general molecular-representation rewrite.

---

## [1.1.0] — 2026-10-23

**Minor release: wider chemical recognition and a graph/synthesis workbench, under an unchanged 1.x machine
contract.** From 1.0.0 the stable wire schema ids, `semantic_digest`, route digests, the verdict vocabulary and the
readiness/capability semantics are **byte-invariant**; only the declared version-bound identity moves
(`result_digest`, `tool_version`, the implementation digest, the `--version` banner). The transition is proved
field-by-field — see *Compatibility* below.

### Added — reaction-type coverage (17 → 20 recognized classes)

The reaction-type oracle is a readiness-layer **demoter** (it never generates routes and never changes a search
identity); a new recognizer can only clear a `reaction_type: not recognized` obligation on a route that already
exists, widening coverage in the promotion direction (COMPATIBILITY §7).

- **#110 activated acyl transfer** (18th) — `anhydride/acyl-halide + R-OH/R-NH/R-SH -> ester/amide/thioester +
  acid/HX`. Graduates the real paracetamol route (4-aminophenol + acetic anhydride) from `FORMAL_CANDIDATE` to
  `PROCESS_SPECIFIED`. Forensic record:
  [`V1_1_COVERAGE_EXPANSION_110.md`](docs/research/V1_1_COVERAGE_EXPANSION_110.md).
- **#111 alkyl sulfonate-ester transfer** (19th) — `sulfonyl halide + R-OH -> sulfonate ester + HX` (alkyl-O only;
  aryl-O deferred).
- **#115 Claisen condensation** (20th) — `ester/ketone + ester/carbonate -> 1,3-dicarbonyl + alcohol`
  (type-validity only; the stoichiometric enolate base is #107). Distinct from the Claisen [3,3] sigmatropic
  rearrangement, which remains a separate recognizer. #111/#115 independent before/after:
  [`V1_1_COVERAGE_EXPANSION_111_115.md`](docs/research/V1_1_COVERAGE_EXPANSION_111_115.md).

Each class ships its no-false-vouch adversarial corpus (cross-poach, forged-centre and per-guard mutation
controls); the cardinal "coverage loss, never a false vouch" invariant holds.

### Added — chemical-graph / synthesis workbench

- A new **`smartchem graph`** CLI verb and the `graph_projection` / `graph_cli` modules — a typed, additive,
  non-contract projection surface (its own `smartchem/graph-projection-v0a1` schema id; it does not
  touch the stable compiler wire).
- An optional **`depiction`** extra (`pip install smartchem[depiction]`, RDKit) that draws a reaction scheme for
  `smartchem graph … --format scheme`; without it the scheme degrades to a readable name/formula label. A
  depiction is built from the engine's own atom/bond graph, asserts no chemistry the engine did not already hold,
  and never changes a verdict.
- An opt-in **`bond-order-edit-v1`** algebra profile (#114): reachability only, its routes demoted to
  `FORMAL_CANDIDATE`; not a default and not a recognizer.

### Fixed / hardened

- #124 refuses an ancestor-as-leaf cyclic route dependency; #126 retires the forged-centre vouch (recognition is
  content-deterministic, never caller-settable); #131 typed recognition outcomes; #132 pericyclic
  content-determinism. `single_cut_capped_scissions` added in `structure_descent.py`.

### Compatibility

- **No change** to any stable wire schema id, `semantic_digest`, request digest, route digest, verdict vocabulary,
  or readiness/capability meaning. Verified: the version-independent fingerprint and the public-contract freeze
  both report **NO DRIFT**; the version transition moves **only** the declared tool-version-bound fields
  (`experiments/v1_0_version_transition.py`, `tests/test_v1_0_version_transition.py`).
- The paracetamol-class readiness promotion (#110) is a declared MINOR coverage move that rides the readiness
  layer under an unchanged `semantic_digest`. **Pin requests and verdicts, not `result_digest`, across the
  upgrade** (COMPATIBILITY §2.2).
- Optional backends never change a verdict. RDKit is now additionally a runtime `depiction` extra (previously
  dev-only); the core still runs on `numpy` + `scipy` alone. Supported Python **3.10–3.13**.
- **This release does not ship a validated physics sandbox.** The experimental 2.0 physicalization work is tracked
  on a separate research branch and is NOT part of the installed 1.1 package.

The exact release gate — merged-`main` SHA, hosted CI run, full-suite counts and artifact SHA-256 — is
[`V1_1_RELEASE_GATE.md`](docs/research/V1_1_RELEASE_GATE.md).

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

[1.1.0]: https://github.com/femboy2112/SmartChem/releases/tag/v1.1.0
[1.0.0]: https://github.com/femboy2112/SmartChem/releases/tag/v1.0.0
[1.0.0rc1]: https://github.com/femboy2112/SmartChem/tree/release/1.0.0
