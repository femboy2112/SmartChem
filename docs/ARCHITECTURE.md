# SmartChem Architecture (current — 0.9.5)

A map for reviewing 1.x changes: what each stage owns, what identity it stamps, how it fails, and what "complete"
means there. History lives in `docs/research/`; this page describes only what the code does today. The stability
promises built on it are in [`COMPATIBILITY.md`](../COMPATIBILITY.md).

SmartChem is a **bounded search compiler with an honest verifier**: a human chemical identity goes in; a set of route
candidates, each with a derived readiness ladder and (optionally) a capability assessment against a declared bench,
comes out as a versioned, digest-bound dossier that a consumer can re-verify without trusting the producer.

```
raw input ─▶ FRONT DOOR ─▶ IDENTITY ─▶ SEARCH ALGEBRA ─▶ SEARCH + RECEIPT ─▶ IR
                                                                               │
          CAPABILITY ASSESSMENT ◀─ CAPABILITY REQUIREMENTS ◀─ ROUTE DOSSIER / READINESS
                    │
                    ▼
              TRANSPORT (wire) ─▶ VERIFICATION (load) ─▶ VerifiedLoad(response, receipt)
```

## The stages

Each arrow is described by four things: **authority** (the ONE code path that owns the fact), **identity** (the digest
it stamps), **failure** (what happens on bad input) and **completeness** (what "done" claims).

### 1. Front door — `smartchem/identity_parse.py`, `formula_expr.py`, `smiles.py`, `plan.py`

* **Authority:** `resolve_identity(text, kind)` is the ONE parser service; `plan` (CLI `plan`) only resolves and routes
  to `recompile` (a perceived structure) or `decompile` (a bare formula).
* **Identity:** `ResolvedIdentity` (layer: STRUCTURE / FORMULA / NAME) + `features` (stereo / isotope / charge the input
  declared) → section-5.3 identity *losses* when the compiler cannot carry them.
* **Failure:** a typed `IdentityParseError` (exit 2, `INVALID_INPUT`) with the explicit form to use — every parse
  failure, including a digit run past the int limit, a non-decimal digit, a recursion-depth overflow and a canonicaliser
  bound (`IdentityOutOfBounds`); on the `plan` front door AUTO never guesses between readings — its target or any
  `--reagents` string (`detect_auto_ambiguity`). **Declared boundary:** the expert verbs' positional target and every
  stock / helper-reagent string they read keep the legacy AUTO precedence
  (name → SMILES → formula: `CO` there is methanol, `O` water) — see COMPATIBILITY §5. Ambiguous formula
  spellings (whitespace that would join counts, a bare trailing sign after a single-element count, a Unicode-digit twin
  of a refused spelling, a superscript charge against ASCII digits) and malformed SMILES (a lowercase atom outside an
  aromatic ring, a non-terminal or multiply bonded `[H]`, contradictory or dangling bond symbols, two charge runs, a
  non-ASCII element letter) are refused, never silently read one way.
* **Completeness:** n/a (a parse either perceives a layer or refuses).

### 2. Identity — `smiles.resonance_identity`, `compilation_ir._structure_ident`, `experiment/stock.structure_key`

* **Authority:** the resonance class of a `Molecule` (a pure graph: atoms, bonds, one global charge, one connected
  species). `stock.structure_key` (`"struct:" + resonance_identity`) is the ONE material key; `stock.py` owns both name
  folds: `collapse_material_name` (whitespace only — the only fold that certifies a supply, covers a raw string or
  merges two obligations) and `normalize_material_name` (also casefolds — a *possible* match, `UNKNOWN`).
* **Identity:** constitution-level. Alternate Kekulé spellings share a key; constitutional isomers and tautomers do not;
  stereo / isotopes are not perceived (disclosed as losses); salts are name-keyed.
* **Failure:** molecules beyond the canonicaliser's limits fall back to their literal graph key (`struct-asgiven:`).

### 3. Search algebra — `algebra_profiles.py`, `transform_provider.py`

* **Authority:** `resolve_algebra_profile(id)` → a `TransformProviderRegistry` of providers (capped scission, Diels–Alder
  families, …) whose identities are **content-bound** (semantic descriptor digests).
* **Identity:** `registry.digest` / `search_algebra_digest(topology, registry)` — enters the request's `semantic_digest`,
  so changing a rule, guard or provider changes the search identity (never silently under the old one).
* **Failure:** an unknown profile id is refused.

### 4. Search + receipt — `experiment/routes.search_routes` / `search_dags`, `compilation_ir.Section81ReceiptView`

* **Authority:** the bounded search (depth, cut budget, result limit) over the algebra; linear routes or convergent DAGs.
* **Identity:** the search receipt (bounds, counts, stop reason, completeness flags, identity digests) — the IR binds it.
* **Failure:** a search that stops at a bound reports it (`INCOMPLETE`, typed stop reason); nothing is truncated
  silently.
* **Completeness:** **within the declared bounded grammar only.** `COMPLETE_CANDIDATE_SET` / `NO_ROUTE_IN_DECLARED_SPACE`
  never mean "no chemistry exists"; `INCOMPLETE_NO_ROUTE_OBSERVED` is absence, not evidence.

### 5. IR — `compilation_ir.ChemicalCompilationIR` (`recompile_to_ir` / `decompile` path)

* **Authority:** the producer's compilation record: target identity, terminal-policy digest, request digest, registry
  digest, candidates (one per returned route/DAG/edge), identity losses, diagnostics, the receipt.
* **Identity:** candidate digests (route digests) and the IR's own digest.

### 6. Route dossier / readiness — `service.RankedRouteSummary` / `RankedDAGSummary`, `experiment/readiness.py`, `procedure_evidence.py`

* **Authority:** `evaluate_route` derives the obligation ladder per step (reaction type, conditions, process, workup)
  and the weakest-link tier `FORMAL_CANDIDATE < REACTION_VOUCHED < CONDITIONS_SUPPORTED < PROCESS_SPECIFIED`;
  `PROCESS_SPECIFIED` needs a structurally complete, **sourced** `ProcedureEvidence` on the step's condition envelope.
  The bench box (`ConstraintBox`) gives each route its `FITS / UNKNOWN / EXCLUDED / UNCONSTRAINED` status; routes are
  ranked (`rank_routes`, a stable sort on a set-relative key).
* **Identity:** the route digest; the dossier's digest folds into the response `result_digest`. The thick
  `replay_payload` (every step's molecules + envelope) rides outside the route identity (`compare=False`).

### 7. Capability requirements — `capability/requirements.compile_capability_requirements`, `capability/waste.derive_waste`

* **Authority:** ONE projection from a route's typed evidence to per-axis demands (material, equipment, physical,
  process, containment, ventilation, measurement, waste, procurement, attention, monetary). `derive_waste` is the single
  producer of waste obligations; a **StreamDisposition** (`stream_disposition.py`) discharges exactly ONE obligation
  whose structural subject it names, under `SOURCE_QUOTED` evidence with an accepted source (`RECOVERED` needs a later,
  phase-compatible recovery op; `ROUTED` also adds the categories its species' hazard record implies).
* **Failure:** a real demand on an unmodeled or unevidenced capacity is an *unread* demand → `UNKNOWN`, never a pass.
  The field-coverage ledger (`capability/coverage.py`, `missing_coverage() == ()`) gives every procedure field ONE owner.

### 8. Capability assessment — `capability/assess.assess`

* **Authority:** requirements vs the declared `CapabilityProfile` (equipment, stock with typed evidence, bench physical
  range, waste capabilities, …) → per-axis `FIT / BLOCKED / UNKNOWN / NOT_APPLICABLE / UNCONSTRAINED` and ONE overall
  fold (`_fold_overall`): any BLOCKED → BLOCKED; else any UNKNOWN → UNKNOWN; else FIT **only if the route's readiness
  tier is at least `PROCESS_SPECIFIED`** (the HARD LAW), otherwise UNKNOWN. `CapabilityAssessment` re-checks that fold
  on construction.
* **Identity:** `CapabilityAssessment.digest` (binds profile digest, route digest, readiness digest);
  `request.capability_question_digest` = `(semantic_digest, profile_digest)` — the capability pin. The profile never
  enters `semantic_digest` (**search noninterference**: the capability layer reads the search, never writes it).
* **Completeness:** `CAPABILITY_FIT` is representable (a synthetic witness reaches it) but no current corpus page states
  a disposal, so no production route reaches it.

### 9. Transport — `service.response_to_payload`, `transport_integrity.py`

* **Authority:** the versioned JSON wire (exact keys everywhere). `transport_mode`: `CANONICAL_VERIFIED` ships every
  dossier's replay; `THIN_ADVISORY` omits it (advisory by contract; `PROCESS_SPECIFIED` inadmissible on it).
* **Identity:** the wire `result_digest` = the response digest folded with the transport mode and the **whole-body**
  digest; optional producer HMAC over it (`producer_signature`).

### 10. Verification — `service.load_response` / `response_from_payload`, `verification.py`, `legacy_v08.py`, `transport_ledger.py`

* **Authority:** `load_response(payload, VerificationPolicy)` → `VerifiedLoad(response, receipt)`. The loader decodes
  exactly, re-derives every verdict-bearing field from carried evidence (the request, the replay, the shipped corpus, the
  algebra) or binds it to the request, and refuses any disagreement. `legacy_v08.py` holds the frozen v0.8 digest kernel
  (the one legacy read leg).
* **Order (cheap first):** schema dispatch → `require_canonical_transport` (S1) → payload-size budget and nesting depth
  → exact keys →
  thin-carries-no-replay → TARGET_FILE refusal (S6) → keyed: HMAC over the claimed digest → decode + construction laws (incl. result count ≤ limit, S3) → wire digest → algebra rebind →
  HMAC → request / capability pins → identity losses → request–answer binding (target, terminals, depth / DAG height
  under the proven search bound `1 + b + … + b^(D−1)` — branches sharing an intermediate stack heights, A17 — one
  chemistry per dossier) → bare-dossier check → every replayed step is a transform the algebra emits (D29.1, budgeted,
  cached) → corpus envelopes → verified admission → readiness → capability → frontier → ranking → optional re-execution.
* **Per-load context:** each load gets ONE `VerificationContext` (work meter + reconstruction memo — each replay is
  rebuilt once, not per guard). The process-level enumeration cache holds RAW `registry.enumerate` outputs keyed on the
  full argument values + `registry.digest` (bounded by transform weight; cleared around any in-process patch).
* **Work budget:** deterministic counters (payload nodes, dossiers, replay steps, enumeration targets, predicted
  enumeration work `W`, re-executions, canonicalisation work in passes, capability work in bottle-assessments);
  exhaustion raises `VerificationBudgetExceeded` — verification did not complete; it never skips a check. A
  type-confused payload is `MalformedPayloadError` (a `ValueError`) at every public loader.
* **Canonicalisation is bounded before it runs:** 1,024 atoms (checked before any refinement, in the parser and on the
  wire), 2^25 work units per call, 2^27 for a resonance placement search; every pass is charged before it runs.
* **Receipt:** out of band, loader-issued only; states wire mode, pins, signature, dossiers actually re-derived,
  re-execution, legacy migration, work consumed, and whether the search output is ADVISORY / AUTHENTICATED / REEXECUTED.

## The two machine-checked ledgers

| ledger | file | what it guarantees | checked by |
|---|---|---|---|
| **Capability field coverage** | `smartchem/capability/coverage.py` | every field of `ProcedureEvidence`, `ProcedureOperation`, `ProcedureMaterialUse`, `EvidenceField`, `ConditionEnvelope`, `ProcessRequirements`, `ExperimentStep`, `ExperimentRoute`, `StreamDisposition`, `StreamSubject` has exactly ONE owning axis (or is PRESENTATION-only by contract); a present untyped value fails its owner closed; prose is display only when byte-equal to the canonical rendering of the typed fields | `tests/test_v0_9_round_v_field_coverage.py` (`missing_coverage() == ()`) |
| **Transport verification** | `smartchem/transport_ledger.py` | every field / wire key / replayed-step key of the response is exactly one of RE_DERIVED_ON_LOAD, BOUND_TO_REQUEST, DIGEST_ONLY_ADVISORY, LEGACY_FROZEN (with `advisory_when` naming the cases a re-derived field is advisory after all) | `tests/test_transport_ledger.py`: coverage both ways, every named check resolves, the service docstring's advisory paragraph matches, and every non-advisory entry has a keyless forgery refused by its OWN law |

## Reviewing a 1.x change against this map

1. Which stage's **authority** does it touch? A second implementation of a fact that already has an authority is a
   defect; call the authority.
2. Does it change an **identity** (a digest's preimage)? Then a schema id bumps (COMPATIBILITY §3).
3. Does it add a field? It needs a coverage-ledger owner (capability types) and a transport-ledger status with a
   refusing forgery (wire types).
4. Does it add verification work? It must be charged to the budget *before* the work, outside any broad `except`.
5. Run `experiments/v0_9_5_baseline_freeze.py --check`: a refactor shows NO DRIFT; anything else is a semantic change
   that needs its own adjudication line.
