# Synthesis-Coverage Campaign Ledger (2026-10-13)

**The durable record of OPERATION SMARTCHEM — the generative-synthesis-algebra campaign.**
Companion to `REACTION_ALGEBRA_COVERAGE_AUDIT_2026-10-12.md` (the family-by-family obstruction audit that
opened epic #103 + issues #104–#123); this ledger tracks what was *repaired and verified*, issue by issue,
with reproducer, root-cause class, fix, commit, and evidence.

- **Base (campaign fork point):** `main` @ `99fce34` (SmartChem 1.0.0).
- **Working branch:** `feat/chemical-graph-projections` (draft PR #101), campaign commits on top of `af66ef3`.
- **Governing contract:** `COMPATIBILITY.md` 1.0. New behaviour rides versioned providers/fields; the frozen
  verbs/schemas/digests do not move. Every `compare=False` field added here is outside identity + every digest.

## The scientific contract (held throughout)

A conserved equation is not a reaction; a valid rewrite is not a recognized class; a recognized class is not
feasible; a feasible reaction is not safe/affordable/sourced. The four statuses — `FORMAL_CANDIDATE`,
`REACTION_VOUCHED`, `CONDITIONS_SUPPORTED`, `PROCESS_SPECIFIED` — are not reinterpreted. **No false-VOUCH** is the
cardinal invariant: coverage loss (a real reaction demoted-as-unrecognized) is acceptable; a fabricated pass is not.

## Obstruction taxonomy (every "no route" is classified as exactly one)

`generated-but-demoted` · `not-generated` · `unrepresentable` · `not-recognizable` · `not-feasible` ·
`budget-truncated` · `internal-error`. The campaign refuses to report all seven as "no synthesis route".

---

## Phase 1 — foundational soundness / truthfulness (P0 + graph P1)

This phase closes holes where the engine could **assert more than it can defend** — false-VOUCH, over-claimed
naming, over-claimed completeness, phantom self-supply. These are truthfulness repairs; they add **no** new
coverage (that is Phase 2: the infra walls + recognizers). The objective is to keep every later expansion honest.

### #126 — forged `ReactionCenter` trusted as recognition evidence  ·  `generated-but-demoted` (false-VOUCH) ·  FIXED `eacc086`

- **Reproducer:** `scratchpad/probe_126.py` (committed as `tests/test_issue_126_forged_center.py`). A bundled
  double condensation `2 lactic acid -> lactide + 2 H₂O` passes the whole-molecule acyl census but is NOT an
  elementary single condensation. Honest/absent centre → demoted; a **forged elementary centre** → VOUCHED
  "acyl condensation". The vouch tracked the *supplied* centre while the molecules were held fixed.
- **Root cause:** the acyl/ether/N-alkylation recognizers read `step.reaction_center` as their locality witness,
  and `ReactionCenter.is_elementary_condensation` inspects only the centre's own declared bonds. `ExperimentStep`
  type-checked the centre but never verified it against the molecules. ([[a-verifier-that-cannot-verify-must-fail-closed]])
- **Fix:** a centre is vouch evidence ONLY when the engine derived/authenticated it. `ExperimentStep.center_trusted`
  (compare=False; set by `from_transform` and the replay deserialization seam) gates it; the oracle reads the centre
  through one `_vouchable_center` helper that fails closed on an untrusted-or-absent centre. Closes the DIRECT
  public-API hole; the verified-replay path (which already authenticates centres `in centres`) is unchanged.
- **Evidence:** 7 new tests; 89 passed across the poor-man oracle / span-local / etherification / N-methylation /
  tamper-hardening (incl. the thick-replay round-trip no-false-reject) / DA-oracle suites. ruff clean.
- **Compatibility:** no wire/digest change (compare=False field; bare-load advisory contract preserved).

### #128 — graph named a family from reaction-centre equality, not re-derivation  ·  `not-recognizable` (mislabel) ·  FIXED `246fbd2`

- **Reproducer:** a synthetic `H + H -> H2` step carrying a verbatim copy of `_DA_CENTER` (reaction_center ==
  `_DA_CENTER`) was named "Diels–Alder" by the scheme; the oracle, which re-derives [4+2]-ness from the molecules
  (Layer A), correctly abstains. (`tests/test_synthesis_scheme.py::test_family_naming_is_rederived_by_the_oracle_never_centre_equality`.)
- **Root cause:** `_reaction_family_for_step` matched a `(formed, broken) -> name` table *before* the oracle.
- **Fix:** the oracle is the sole naming authority; the centre-equality table is deleted. Genuine provider DA is
  still named (verified on the cyclohexene litmus); an unmatched step shows its neutral bond-change description.
- **Evidence:** scheme suite 14 passed / 3 RDKit-skipped; graph_projection suite green. ruff clean.

### #129 — scheme green-lit `UNATTESTED` completeness  ·  (presentation over-claim) ·  FIXED `246fbd2`

- **Reproducer:** `render_scheme_html(route, search_result=None)` → `UNATTESTED`; the banner predicate put
  `UNATTESTED` in its `COMPLETE` set, rendering it green/"ok" and suppressing the incompleteness notice.
- **Root cause:** `const COMPLETE = {COMPLETE, COMPLETE_WITHIN_BOUNDS, UNATTESTED}` in the scheme template.
- **Fix:** three distinct states — complete (ok) / UNATTESTED (amber "completeness UNKNOWN", an explicit
  disclosure, *not* a failed search) / partial (warn). New `--unknown` token + class; aligns with the ordinary
  renderer. Tested via the generated display predicate over its own emitted `COMPLETE` object, not string presence.

### #124 — ancestor precursor silently treated as stocked leaf (phantom self-supply)  ·  `not-generated` (latent soundness) ·  FIXED `474e018`

- **Reproducer:** `tests/test_issue_124_cyclic_refusal.py` — a minimal rank-flat reciprocal provider (ethanol ⇌
  dimethyl ether). An UNSTOCKED search over it reached the ancestor-exclusion branch and yielded a self-supplying
  route (A←B←A with no external feed), which then crashed the linearity invariant with an uncaught `StepError`.
- **Root cause:** `missing = [m for k,m in distinct if k not in on_hand and k not in ancestors]` (routes.py L543
  linear, L787 DAG) dropped an ancestor precursor from the still-needed set, treating it as available.
- **Reachability:** **unreachable under the W1 strict-rank capped-scission grammar** (an ancestor can never
  reappear as a lower-rank precursor), so the clause was dead *today*; it becomes a phantom the moment a rank-flat
  / reversible provider exists (#104/#123). Proven reachable only with the fake reversible provider.
- **Fix:** an ancestor precursor that is not external stock is a cyclic dependency → the branch is refused
  (`continue`), never folded into "available". Provably a no-op under W1 (identical `missing` when no
  ancestor-precursor exists); the safety net #104/#123 require. Both searchers (linear + DAG) guarded.
- **Evidence:** 3 new tests (unstocked → 0 routes/DAGs, no crash; stocked positive control → 1 route; W1
  capped-scission unaffected). Core route/DAG regression: **144 passed / 0 failed** (test_routes, test_dag,
  test_graph_projection incl. the 9-route + 47-DAG ensembles, test_v0_7_production_algebra, test_dag_flow,
  test_reagents) — the guard is a confirmed no-op on every W1 search.

### #131 — oracle exceptions masked as NOT_A_REACTION  ·  `internal-error` (observability) ·  FIXED `d8adf19`

- **Reproducer:** `tests/test_issue_131_typed_outcomes.py` — a deterministically-poisoned recognizer; the old
  `recognize_reaction_type` returned `None` for both a genuine non-match and an internal fault, indistinguishably.
- **Root cause:** `recognize_reaction_type` caught every `Exception` and `continue`d; `route_reaction_type_blockers`
  then labelled a faulted step with the same "unrecognized reaction type" demotion as a clean non-match.
- **Fix (additive, contract-stable):** `RecognitionOutcome` + `recognize_reaction_type_outcome` expose typed
  `MATCH` / `ABSTAIN` / `INTERNAL_RECOGNIZER_ERROR(faults)`; `recognize_reaction_type` delegates (identical
  `str|None`, both abstain and error → `None`, fail-closed preserved — an exception NEVER becomes a MATCH);
  `route_reaction_type_diagnostics` surfaces the per-step distinction. `route_reaction_type_blockers` byte-unchanged.
- **Evidence:** 4 new tests; 51 passed across the poor-man recognizer suites (the delegate refactor preserved the
  exact `str|None` output). No wire/verdict-string change. ruff clean.

### Benchmark corpus — SYNTHESIS-COVERAGE-CORPUS-01 (`experiments/synthesis_coverage_corpus.py`)

The campaign's baseline instrument: POSITIVE / NEGATIVE / NULL / MUTATION cases through the oracle, measuring
recall and the must-be-zero false-vouch rate. **Baseline (post Phase 1): recall 3/3, FALSE-VOUCH 0/2, null 1/1,
mutation 1/1 — PASS.** Pinned by `tests/test_synthesis_coverage_corpus.py`.

---

## Coverage impact so far

**Families newly generable / recognizable / searchable: none yet** — Phase 1 is truthfulness, not coverage. The
value is a hardened floor: no forged-centre false-VOUCH (#126), no centre-equality mislabel (#128), no green
UNATTESTED (#129), no phantom self-supply when rank-flat providers land (#124). The coverage expansion lives in
Phase 2 (the Tier-0 infra walls #104–#109/#125 and the recognizer/grammar tiers #110–#123), characterised in
`REACTION_ALGEBRA_COVERAGE_AUDIT_2026-10-12.md`.

## Remaining (by directive priority)

- **P0 soundness/infra (open):** #104 (W1 rank redesign), #105 (per-atom charge rail), #106 (radius-1 centre
  context), #107 (catalyst/activator ledger), #108 (organometallic elements), #109 (latent-fiction audit),
  #125 (scission arity vs intramolecular).
- **P1 (open):** #127 (result-cap starvation — a measurement task), #131 (typed oracle outcomes vs
  internal-error conflation — observability).
- **P2 (open):** #130 (stereo-aware route identity).
- **Chemistry tiers (gated on the infra):** #110–#123.

## Next most discriminating step

`#131` (typed recognition outcomes) is the cheapest remaining truthfulness win and extends the oracle work
directly. The highest *coverage*-unlocking step is `#106` (radius-1 centre context) or `#105` (charge rail),
each of which gates whole families; both are architectural and will be scoped with their own soundness gates.
