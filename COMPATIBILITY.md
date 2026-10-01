# SmartChem Compatibility Contract

This document is the stability contract for SmartChem from **0.9.5** through the **1.x** series. It says what a
consumer may rely on, what moves only with a declared version change, and what is explicitly *not* stable.

**The core promise:** *new chemistry may widen coverage. It must not silently change the meaning of an existing verdict
word.* Every rule below is a consequence of that sentence.

The architecture these rules protect is described in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); the 0.9.5 design
decisions and their evidence are in [`docs/research/V0_9_5_ARCHITECTURE_FREEZE.md`](docs/research/V0_9_5_ARCHITECTURE_FREEZE.md).

---

## 1. Package versioning (SemVer)

* `MAJOR.MINOR.PATCH` per [SemVer 2.0](https://semver.org/). The version has ONE source: `smartchem.__version__`
  (the build reads it; `tests/test_v0_9_5_release_invariants.py` pins that).
* **Pre-releases** (`0.9.0a1`, `0.9.5a1`, …) carry **no compatibility promise** between each other: their wire
  generations are not migrated (see section 3).
* From **1.0.0**: a PATCH fixes a defect without changing any stable surface below (a fix that makes a previously
  *wrong* verdict right is a defect fix — it is listed in the release notes with the before/after); a MINOR may widen
  coverage (new rules, providers, evidence vocabulary, CLI options) under section 7; anything that changes the meaning
  of a stable surface is a MAJOR.

## 2. What is stable (machine semantics)

The stable surface is the **machine** surface: the versioned JSON wire, its enums, its schema ids, its digests *as
defined by rule*, the exit codes, the refusal *classes*, and the public Python entry points
(`build_recompile_request`, `build_decompile_request`, `run_compilation`, `response_to_payload`, `load_response`,
`load_response_text`, `response_from_payload`, `deserialize_response`, `request_to_payload`, `request_from_payload`,
`response_schema`, `smartchem.verification.VerificationPolicy` / `VerificationBudget` / `VerifiedLoad`, the
`smartchem` CLI verbs `plan`, `recompile`, `decompile`, `compile`).

### 2.1 The stable verdict vocabulary

| surface | words | meaning that will not change |
|---|---|---|
| `outcome` (exit code) | `ROUTES_FOUND` (0), `TARGET_ALREADY_AVAILABLE` (0), `NO_ROUTE_COMPLETE` (3), `INCOMPLETE` (4), `REFUSED` (5), `INVALID_INPUT` (2), `INTERNAL_ERROR` (70) | the classification of the search under the request's declared space; `NO_ROUTE_COMPLETE` only for a complete-within-bounds search with no candidate. The exit code of `ROUTES_FOUND` is 5 when the declared bench admits no returned candidate (a process box with no combined-`FITS` route or DAG; with no process box, every ranked candidate hard-`EXCLUDED`): the search found routes, none is bench-usable |
| `search_space_status` | `COMPLETE_CANDIDATE_SET`, `PARTIAL_CANDIDATE_SET`, `INCOMPLETE_NO_ROUTE_OBSERVED`, `NO_ROUTE_IN_DECLARED_SPACE` | completeness is *within the declared bounded grammar only*; absence of a route in an incomplete search is never evidence of absence |
| readiness tier | `FORMAL_CANDIDATE` < `REACTION_VOUCHED` < `CONDITIONS_SUPPORTED` < `PROCESS_SPECIFIED` | the weakest-link derived obligation ladder; `PROCESS_SPECIFIED` requires a structurally complete, *sourced* procedure |
| route / process fit | `FITS`, `UNKNOWN`, `EXCLUDED`, `UNCONSTRAINED` | a box verdict; `UNCONSTRAINED` (nothing declared) is never a pass |
| capability status (per axis + overall) | `FIT`, `BLOCKED`, `UNKNOWN`, `NOT_APPLICABLE`, `UNCONSTRAINED` | `FIT` = every modeled axis is satisfied by the *declared* bench under *certifying* evidence; a real demand on an unmodeled or unevidenced capacity is `UNKNOWN`, never `FIT`; `CAPABILITY_FIT` is a profile-fit claim, **never a safety certificate** |
| transport mode | `CANONICAL_VERIFIED`, `THIN_ADVISORY` | canonical ships re-derivable evidence; thin is advisory by contract |

A verdict word is **never** reinterpreted. If a future version needs a different meaning, it adds a new word (a MINOR
when additive and ignorable, a MAJOR otherwise) and leaves the old one meaning what it meant.

### 2.2 What is NOT stable

* **Human prose:** the human render of every CLI verb, diagnostics text, the wording of refusal messages, docstrings.
  The *refusal class* (a `ValueError` — including `MalformedPayloadError`, also a `TypeError`, for a payload whose shape
  a decoder cannot read — / `VerificationBudgetExceeded` / typed parse error, and the exit code) is stable;
  the message text and the law tag it carries (e.g. `(D29.1)`, `(0.9.5 S1)`) are informative, not contractual.
* **Timing and resource use** (the verification budget is counted in deterministic work units precisely so that no
  verdict depends on wall-clock time).
* **Private names** (leading underscore) and module layout below the public entry points.
* **The `result_digest` of a given answer across package versions:** it binds the producing tool version
  (`compilation_ir.tool_version`), so a version bump moves every `result_digest` while the request's `digest` /
  `semantic_digest`, the route digests and every verdict stay put. Pin requests and verdicts, not result digests, across
  upgrades.
* **Non-stable verbs:** `synthesize` (and the other experiment-layer commands outside section 2's list) are not part of
  this contract; `synthesize --offline` reads a local stability cache (`$SMARTCHEM_DATA_DIR` or `~/.cache/smartchem`)
  that is not authenticated and can change its handling notes.
* **Search telemetry** inside the receipt (`nodes_visited`, `transforms_considered`, …): descriptive, advisory.

## 3. Wire schema policy

* Every wire record carries its own `schema_version` id. Loaders dispatch **explicitly**; an unknown id is refused
  precisely (`unsupported … schema_version`), never guessed.
* **A change of meaning bumps the id even when the Python field shape does not** (e.g. 0.9.5 bumped the material
  component id when the structure key coarsened to the resonance class).
* Exact keys: every current container refuses an unknown key and requires every required key (no silent default, no
  unenforced "claim" riding the digest).

### 3.1 Supported generations (0.9.5)

| generation | ids | status |
|---|---|---|
| **current** | request `compilation-request-v1alpha7`; response `compilation-response-v1alpha18`; route summary `ranked-route-summary-v1alpha6`; DAG summary `ranked-dag-summary-v1alpha6`; descriptor `compilation-response-schema-v1alpha21`; stock `stock-material-v1alpha4`; material component `material-component-v1alpha3` | full read/write, every re-derivation |
| **legacy v0.8** (main@`df1b38d`) | request `v1alpha5`, response `v1alpha15`, their summaries | **read-only**: loads under the FROZEN v0.8 digest rule; capability is `NOT_REQUESTED` (never fabricated); ranking/frontier/diagnostics are v0.8's (advisory); corpus evidence and replayed steps are re-derived only under verified admission; never re-emitted; refused under `require_canonical_transport` and `require_reexecution` |
| **0.9.x pre-release** | the merged 0.9.0a1 generation: response `v1alpha17`, route summary `v1alpha5`, DAG summary `v1alpha5`, descriptor `v1alpha20`, stock `v1alpha3`, material component `v1alpha2` (plus the never-released WIP ids response `v1alpha16`, route summary `v1alpha4`); and the Round-III-era 0.9.0a1 payloads, which reused the v0.8 ids (request `v1alpha5`, response `v1alpha15`, summaries `v1alpha3` / `v1alpha4`) while carrying 0.9-only keys | **not supported** (SemVer pre-release). The first group is refused as an unsupported schema version with a recompile hint; the Round-III-era group is refused by the legacy leg's 0.9-only-key smuggling scan (a v0.8 id cannot carry a capability question) — recompile either way |

**Support duration:** the v0.8 read-only leg is supported for the whole **1.x** series. Removing it is a MAJOR change,
announced (deprecation warning + release note) at least one MINOR release before.

### 3.2 What requires recompilation

A payload of any unsupported generation; a legacy v0.8 payload whenever the consumer needs canonical verification,
re-execution, or verified admission of corpus evidence; any payload whose request names a TARGET_FILE (the loader never
reads a payload-supplied path — recompile locally from the file).

## 4. Verification (load) contract

* `load_response(payload, policy) -> VerifiedLoad(response, receipt)` is the verifying loader; `response_from_payload`
  is the same load with the receipt discarded (its legacy keyword arguments map onto ONE `VerificationPolicy`).
* The **receipt is out of band**: it is issued only by the loader, is never on the wire and never a field of the
  response, cannot be constructed, copied into a stronger one, pickled or deserialized; it states facet by facet what the
  load established (wire mode, pins checked, signature state, dossiers actually re-derived, re-execution, legacy
  migration, work consumed). `receipt.satisfies(policy)` answers a downstream requirement without reloading.
* **Trust tiers**, weakest to strongest: thin (advisory) → canonical (`require_canonical_transport`) → pinned
  (`expected_request_digest`, `expected_capability_question_digest`) → verified admission → authenticated
  (`verification_key` + `require_signature`, producer HMAC over the whole-body wire digest) → re-executed
  (`require_reexecution`). What a *keyless* consumer must still treat as advisory is machine-checked in
  `smartchem/transport_ledger.py` (notably: what the bounded search *found* — a consistent rewrite of it is refused only
  by re-execution or the HMAC).
* **Verification work is budgeted** in deterministic units (`VerificationBudget`); exhaustion raises
  `VerificationBudgetExceeded` and means *verification did not complete* — it never skips, clamps or weakens a check.
  The default budget admits every honest payload of the frozen corpus with headroom; a MINOR may raise the default, never
  lower it below that corpus; a caller raises it explicitly (`VerificationBudget(...)` or the explicit
  `VerificationBudget.unlimited()`).
* **The budget's counters (0.9.5 defaults; each charged BEFORE the work it bounds):**
  * `canonical_work`, in passes over a graph (atoms + 2 × bonds per refinement round and per block-path candidate),
    each distinct canonicalisation charged once per load whether the process cache is cold or warm. Default 2^30, 9.2×
    the honest maximum (117,006,226 units, an isopentyl DAG answer under pinned re-execution, over 117 honest loads).
    At the slowest measured rate (≈0.8M units/s on a dense hostile graph, ±30% on a shared box) the default admits
    about 22 minutes of canonicalisation per load.
  * `capability_work`, one unit per declared bottle per capability assessment. Default 2^13, 14.4× the honest maximum
    (567). A bench above roughly 100 bottles on a 27-route answer needs an explicit raise.
* **Shape before meaning:** every public loader (`load_response`, `load_response_text`, `response_from_payload`,
  `deserialize_response`, `request_from_payload`, `deserialize_request`, the summary / frontier / snapshot decoders,
  `compilation_ir.ir_from_payload` / `deserialize_ir`, `identity.identity_loss_from_payload`) refuses a type-confused
  payload as `MalformedPayloadError` — never a bare `TypeError` / `AttributeError` / `KeyError` / `IndexError`. A
  payload nested more than 128 containers deep (the honest maximum is 28) is refused before any decode; a wire molecule
  of more than 1,024 atoms is refused before its graph is built; `producer_signature` is `null` or 64 lowercase hex
  digits on every load, keyless and legacy included.
* A key shorter than 16 bytes, a malformed pin, or `require_signature` without a key is refused when the policy is
  constructed; a producer cannot sign with a key shorter than 16 bytes either.
* **Signature timing boundary:** a keyed consumer checks `producer_signature` against the payload's CLAIMED wire digest
  before decoding anything, so a keyless forgery of a new digest is refused for the price of one HMAC. An AUTHENTIC
  (digest, signature) pair copied onto a different body passes that pre-check and is refused only after decode, when the
  reconstructed body no longer matches the signed digest — within the verification budget, never accepted.
* **Search identity vs capability question:** equal `semantic_digest` means the same chemistry SEARCH; whether a
  capability question can be answered on top of it (a convergent-DAG search under a capability profile is refused) is
  decided at the capability layer, not by the search identity.

## 5. Identity-layer boundaries (declared, stable)

* **Material identity is constitution-level**: two structures are the same material iff their resonance class
  (`resonance_identity`) is equal — alternate Kekulé spellings are one material; constitutional isomers and tautomers are
  distinct.
* **Not perceived by material matching:** stereochemistry and isotopic labels (a target's stereo/isotope features are
  disclosed as identity losses on the request), per-atom charge beyond the molecule's one global charge, and salts /
  disconnected species (name-keyed). Molecules above the resonance canonicaliser's size limits fall back to their literal
  graph key.
* **Names are closed-world:** a name resolves only through the offline name table; there is no synonym layer (a bottle
  labelled "baking soda" does not satisfy a "sodium bicarbonate" requirement). Name comparison folds whitespace; only a
  whitespace-folded match certifies a supply, covers a raw source string or merges two obligations. A match that holds
  only after also folding case is a *possible* source (`UNKNOWN`), never a certification — `CO` (carbon monoxide) is
  not `Co` (cobalt). The same rule governs every case-folding lookup that certifies (hazard records, catalyst tiers):
  a case-only agreement never certifies a string whose letter case carries meaning — one that reads as a formula, as a
  whole or token by token. `WAtEr` (W·At·Er), `CoNC H2SO4` and `sulfuric AcID` get no hazard record and no catalyst
  tier (`UNKNOWN`; a declared catalyst `BLOCKS`), while `Water`, `WATER` and `SULFURIC ACID` resolve.
* **One species, two keys (a declared split):** hypervalent and charge-separated spellings of one species are
  *different* material keys — `CN(=O)=O` vs `C[N+](=O)[O-]` (nitro), `CS(C)=O` vs `C[S+](C)[O-]` (sulfoxide), and
  likewise N-oxides, phosphine oxides, sulfones, nitrate; so are resonance forms that move a charge or an unpaired
  electron (enolate `[O-]C=C` vs `O=C[CH2-]`). The resonance class re-places multiple bonds at fixed per-atom
  pi-demand only. The error runs in one direction: a bottle spelled one way does not satisfy a requirement spelled the
  other (false `BLOCKED` / `UNKNOWN`); two different species are never merged.
* **Front door:** a formula spelling that is ambiguous (a bare trailing sign after a count, whitespace that would join
  two counts) is refused with the explicit form to use — never silently read one way. A SMILES that is not well
  formed is refused, never repaired: a lowercase (aromatic) atom outside an aromatic ring (`Co`, `Cc`, `c1CCCCC1`), an
  explicit hydrogen that is not one terminal single-bonded atom (`C1C[H]1`, `C[H][H]`, `[O]#[H]`), two bond symbols in
  a row or one with no atom to bind (`C=#C`, `CC=`, `C(=)C`), a ring bond whose two ends disagree (`C=1CCCC-1`), more
  than one charge in a bracket atom (`[O-+]`, `[Fe+2+]`), a non-ASCII element letter (`[ı]`, `[ſ]`). In a formula,
  every Unicode decimal digit reads as its ASCII twin, refusals included (`C٦.5H12` is the refused decimal `C6.5H12`),
  and a superscript charge written against ASCII digits (`SO⁴2-`) is ambiguous. A bracket atom's hydrogen count is ONE
  digit (`[CH10]` is refused as SMILES); a ring closure onto a pair already bonded is refused (`C1C1`, `[CH3]1[CH3]1`,
  `C1=C1`); an explicit `:` bond is legal only on a ring bond between two lowercase atoms (`C:C`, `c1cc1:c1cc1` are
  refused). An InChI is read only with version `1S` or `1`, one ASCII Hill formula, each of `/q` `/p` at most once,
  and no `/f` or `/r` sublayer. Every front-door parse failure is typed invalid input (exit 2), never an internal
  error.
* **Canonicaliser bounds (front door and wire alike):** a structure of more than 1,024 atoms (hydrogens included) is
  refused before it is built; one canonicalisation is bounded at 2^25 work units, and the resonance placement search
  of an explicit-Kekulé π-system at 2^27. Past a bound the front door answers `IdentityOutOfBounds` (exit 2) — a
  refusal to assign an identity, never a guessed one.
* **AUTO fallthrough (declared):** under AUTO, a string refused as SMILES is still offered to the formula grammar
  (`[CH10]` reads as the formula CH10, `[CH3]1[CH3]1` as C2H6, `C12CC12` as C25). The result is a FORMULA-layer
  identity with no structure, and every verb that needs a structure refuses it. Write `smiles:` to forbid the
  fallthrough.
* **AUTO precedence on expert paths (declared):** the `plan` front door never guesses between input-kind readings in
  any string it reads — its target *and* each helper-reagent string (`plan --reagents`, `plan(helper_reagents=...)`)
  refuse an input-kind ambiguity (`detect_auto_ambiguity`): the target reports `INPUT_KIND_AMBIGUOUS`, a reagent
  `INVALID_INPUT` naming the string, both exit 2; a `--target-file` / `TARGET_FILE` is held to the same rule on the
  file's contents. The expert verbs (`recompile`, `compile`, `synthesize`, ...) keep
  the legacy AUTO precedence for their positional target and every stock / helper-reagent string they read (CLI
  `--have` / `--reagents`, human and `--json` alike, through the one front-door parser; request fields
  `stock_materials` / `helper_reagents`) — offline name, then SMILES, then formula. There, `CO` is methanol (not carbon monoxide), `O` is water, `NO` is hydroxylamine, `CCO` is ethanol. The
  reading is deterministic but not echoed per bench string; write `smiles:` / `formula:` (or a registered name) to
  make the choice explicit.

## 6. Evidence contract

* Evidence records prove **arithmetic** (a derived interval must be reproduced by its declared kernel), not subject or
  source. A claim's subject is fixed by its placement; requirement-side claims come only from the shipped corpus, which
  the canonical loader re-derives; every stock-side claim is the operator's declaration (stock-side states and phase
  claims are `USER_DECLARED` / `ASSUMED` / `UNKNOWN`). A locator is a provenance string, never a verification.
* **StreamDisposition** (0.9.5) is the one vocabulary through which a waste obligation can be discharged: it binds to ONE
  structurally identified subject and requires `SOURCE_QUOTED` evidence with an accepted source and a locator.
  `CAPABILITY_FIT` is therefore *representable*; no current corpus page states a disposal, so **no production route
  reaches `CAPABILITY_FIT` today** — that is the honest state, not a defect. `CONSUMED_COMPLETELY` on an excess reagent
  is a sourced claim the model cannot cross-check without a unit engine. `RECOVERED` needs a recovery operation after
  the stream exists, a certified subject phase, and an operation that can recover that phase. `ROUTED` also carries
  the categories the species' hazard record implies, so routing a GHS-hazardous species to `AQUEOUS_NEUTRAL` still
  demands a hazardous-waste route.
* **Library callers of `assess()`:** a `RouteReadiness` carries no route identity, so `assess()` cannot bind it to
  `requirements.route_digest` and trusts its caller. The service re-derives readiness on every compile and load;
  library callers must pass `evaluate_route(route)` of the same route.
* Deferred, with exact boundaries (post-1.0): evidence *subject* binding records; temperature domain-of-validity laws
  (today the only consumer of a temperature-scoped derived interval is temperature-invariant); lower-bound-only physical
  requirements; typed endpoints / pH indicators.

## 7. What post-1.0 rule / provider / vocabulary additions may change

* **May:** add routes and candidates (a wider algebra), add evidence vocabulary that turns an `UNKNOWN` into `FIT` or
  `BLOCKED` *only through new typed, certifying evidence*, add CLI options, add capability axes' modeled capacities.
* **Structurally visible:** a provider's identity is content-bound (its semantic descriptor digest), so changing a
  rule, guard or provider changes the algebra digest and therefore the request's `semantic_digest` — a different search
  identity, never a silent change under the old one. Consumers that pin a request keep getting answers to *that* search.
* **May not:** reinterpret an existing verdict word; relax a fail-closed law (an unread demand stays `UNKNOWN`);
  make an absence of evidence count as evidence; let any optional backend change a verdict.

## 8. Optional backends

* **RDKit** is a development-only oracle; the committed baseline runs without it and its tests skip. It never changes a
  verdict.
* **PySCF** (`pip install smartchem[qc]`) is an optional high-accuracy energy oracle; the categorical core, the route
  compiler and the capability compiler run without it, and its presence does not change a route, readiness or
  capability verdict.
* Supported Python: **3.10–3.13** (every one verified from a clean wheel install; see the install matrix).

## 9. Implementation digest (approved programs)

`_compiler_implementation_digest` binds an approved program to the package's own `.py` source (sorted relative paths +
content hashes) and `__version__`; it is identical for a source checkout, an editable install, a wheel and an sdist
install of the same code, and it refuses (rather than hashing nothing) when the package is not a real directory (a
zipped install). Boundary: it hashes `.py` source only — anyone with write access to the installed package (a planted
`.pyc` in `__pycache__`, a symlinked subdirectory) is outside its threat model, as is an editable install's stale
`importlib.metadata` version after a hand edit (reinstall). `python -m smartchem` resolves the package from the current
directory first, like any `-m` invocation; the `smartchem` console script does not.

## 10. Deprecation policy

Deprecate in a MINOR (a warning where a call site exists, plus a release note naming the replacement); remove no
earlier than the next MAJOR. The v0.8 legacy read leg follows the same rule (section 3.1).
