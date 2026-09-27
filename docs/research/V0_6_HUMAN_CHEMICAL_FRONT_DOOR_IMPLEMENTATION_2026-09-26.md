# v0.6 Human Chemical Front Door — implementation decision record

**Status:** implemented on `feat/v0.6-human-chemical-front-door`
**Date:** 2026-09-26
**Program:** [`CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md`](CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md)
**Plan:** [`V0_6_HUMAN_CHEMICAL_FRONT_DOOR_PLAN_v0.1.md`](V0_6_HUMAN_CHEMICAL_FRONT_DOOR_PLAN_v0.1.md)
**Release gate advanced:** 0.6 (Human Chemical Front Door)
**Funnel denominator moved:** `input -> syntax represented -> composition resolved -> identity layer -> ambiguity classified -> structure represented -> structural-planning eligible`

This record captures WHAT was built and WHY the shape was chosen. It supersedes no historical audit; it is the
implementation companion to the v0.6 plan.

---

## 1. The identity law, made executable

> A molecular formula names a **composition**, not a **constitution**. `formula -> structure` is a RELATION,
> not a function.

Before v0.6 this was documentation. It is now an executable property:

- a bare formula resolves to a FORMULA-layer identity with `molecule is None` and
  `constitution_established is False`, and the structural `recompile` primitive refuses it;
- the registry-known structures that share a formula are exposed as a **candidate set**, explicitly labelled
  NOT exhaustive — a single registered candidate (e.g. `water` for `H2O`) never promotes the identity to a
  constitution, and an empty set is never read as "no such molecule exists" (anti-Mutant-4).

## 2. The lossless syntax layer — `smartchem/formula_expr.py` (FORMULA-EXPR-01)

A new representation sits **before** `Formula`:

```
raw spelling  ->  FormulaExpr (components + charge + provenance)  ->  Formula (atom multiset)
```

- `FormulaExpr` retains the component/hydrate/adduct boundary, the original spelling, the normalized spelling,
  and ordered notes naming every non-trivial normalization. Its **identity** (digest / equality) is
  `(components, charge)` — the raw/normalized/notes strings are `field(compare=False)` provenance, so
  `CuSO4·5H2O` and `CuSO₄·5H₂O` are the SAME expression.
- `to_formula()` is the deterministic, conservation-correct forgetful projection (the hydrate boundary is
  dropped **only** here).
- The finite grammar (each spelling has a committed test): ASCII formulas, Unicode subscript counts, a
  **Unicode middle-dot (`·`) or SPACED ASCII-dot** hydrate separator with a leading component multiplier,
  whitespace tolerance, nested `()` and `[]` grouping, and the charge spellings `NH4+`, `[NH4]+`, `SO4^2-`,
  `SO₄²⁻`, `[Fe(CN)6]4-`. (A **compact ASCII `digit.digit`** is a decimal and is refused, never coerced into
  an adduct — see the hostile-review addendum, P0-C.)
- **Charge rule (revised in the hostile-review round, P0-B):** a caret (`SO4^2-`), a Unicode superscript
  (`SO₄²⁻`/`Fe³⁺`), or a bracket-ion (`[Fe(CN)6]4-`, `[Fe]3+`) carries any magnitude, unambiguously. A **bare**
  trailing sign is ±1; a preceding **single** digit on a **multi-element** body is that body's last-element
  count (`NH4+` → NH4⁺, `NO3-` → NO3⁻). Two cases are refused with `AmbiguousChargeError` (naming the
  unambiguous spelling): a **single-element** body with a trailing digit run (`Fe3+`, `Ca2+`, `O2-`, `C60-` —
  count vs magnitude), and **any** body with a **≥2-digit** trailing run before a bare sign (`SO42-`, `PO43-`,
  `Cr2O72-` — unclear how to split count from magnitude). Fail closed over a silent mis-charge; never
  special-cased by element name.
- **Parametric forms are refused, never coerced:** `(C2H4)n`, `C6H(12±2)O6` raise `ParametricFormulaError`
  (a subclass of `FormulaSyntaxError`), so a caller can tell "outside the grammar because parametric" from
  "malformed". Nothing is downgraded to a concrete count. `MxOy` is refused as a plain `FormulaSyntaxError`
  (its `Mx`/`Oy` read as unknown two-letter element symbols — syntactically indistinguishable from a genuine
  typo, so it fails as an unknown element, exactly as `tests/test_formula_expr.py::test_MxOy_is_refused_not_coerced`
  pins). Distinguishing a variable subscript from a mistyped element is not possible at the syntax layer, so
  the classifier does not attempt it.
- **Guards:** a 512-char input bound and a 32-deep nesting bound — a pasted identity is a short string, not a
  program. No RDKit, no PySCF, no network.

## 3. Integration through the ONE identity service (no second front door)

`smartchem/identity_parse.resolve_identity` remains the single authority. Changes:

- the explicit `formula:` branch now parses through `parse_formula_expr` (so hydrates/Unicode/charges resolve);
- **AUTO** gains formula detection **strictly last** — after a registered name and after SMILES both decline —
  so it can never steal a valid name or SMILES (anti-Mutant-5, structural not case-based). An explicit
  `smiles:` failure stays a SMILES failure.
- `ResolvedIdentity` gains two defaulted fields: `formula_expr` (the syntax object) and `registry_candidates`
  (the ambiguity set). These are **not** on the digested `ParseReceipt`, so existing NAME/SMILES/ASCII-formula
  receipts and their digests do not drift; a note is added to a receipt only for a genuinely new feature
  (Unicode translated, a hydrate boundary, a charge consumed).

The only golden that changed is `tests/fixtures/cli_json/recompile_invalid.json`: an unresolvable AUTO string's
diagnostic now honestly lists three attempted forms (name, SMILES, formula) instead of two. Exit code
unchanged (2). The change was verified field-by-field before the golden was regenerated.

## 4. First-class ambiguity (Build C)

`registry_candidates` (from the existing `structure.known_compounds`, keyed by `Formula`) is the registry-known
candidate set. It is surfaced by `plan` and the funnel, always labelled non-exhaustive. `C2H6O` correctly
reports `{ethanol, dimethyl ether}`; `C8H9NO2` reports `{4-aminophenyl acetate, paracetamol}`.

## 5. The human total-answer verb — `smartchem/plan.py` + `smartchem plan TARGET` (PLAN-01)

`plan` is **thin orchestration only** — it forks no search, duplicates no parser, builds no second ranker:

1. resolve the identity once (the one front door);
2. report the strongest identity layer, normalized syntax, composition, and the ambiguity set;
3. route to the EXISTING primitive the identity layer makes eligible — a perceived constitution to
   `recompile`, a bare formula to `decompile` — via `build_*_request` + `run_compilation`;
4. a charged species has no neutral formula descent, so decomposition is skipped and only the identity is
   reported (exit 0 — the identity question WAS answered);
5. an unresolvable input returns a typed invalid `PlanResult`, never a raised traceback.

**Layering note (a documented 0.7 boundary):** for a formula-layer target, `plan` hands the descent the
RESOLVED composition (`repr(formula)`), not the raw human spelling, because the `decompile` primitive still
parses a strict formula with `Formula.parse`. So `smartchem plan "CuSO4·5H2O"` works while the expert
`smartchem decompile "CuSO4·5H2O"` does not (yet). Routing the expert `decompile`/`recompile` argv through the
tolerant grammar is recorded as a **0.7 Production Chemical Algebra** item, not smuggled into v0.6.

## 6. The measurement instrument (Build E) — `experiments/v0_6_front_door_funnel.py`

The permanent 1.0 funnel harness: a stable 32-case design corpus recording each front-door stage, producing
per-case records and aggregate denominators, and writing `experiments/RESULTS_v0_6_front_door_funnel.md`. The
meter is built to be trustworthy first — a typed refusal of a malformed/parametric input is a correct outcome,
and `structure/eligible = -` for a bare formula is the identity law, not a miss. `tests/test_v0_6_funnel.py`
pins the aggregate and adds a **fresh holdout** of spellings/families not used to design any parser branch.

## 7. The adversarial gate (Build G)

`tests/test_plan_front_door.py` pins the eight required mutants; `experiments/v0_6_mutation_calibration.py`
INJECTS each mutation and proves the matching test goes red (8/8 killed), so the gate is not vacuous:

1. subscripts dropped → composition wrong; 2. hydrate multiplier dropped → H/O wrong; 3. component boundary
flattened → one component / no note; 4. structure inferred from a formula match → `molecule` set; 5. AUTO
formula steals a SMILES → `CO` resolves as formula; 6. formula routed to `recompile` → wrong operation; 7.
provenance dropped in the payload → original/notes empty; 8. parametric coerced → `(C2H4)n` parses.

## 8. Version policy

- Landing the planning docs (PR #89) was **not** a version bump.
- Development proceeds at `0.5.0a1`; on satisfaction of the v0.6 gate the package moves to **`0.6.0a1`** — a
  pre-release that preserves the conceptual 0.6 gate and matches the existing `a1` convention. The conceptual
  ladder (0.6 → 0.7 → 0.8 → 0.9 → 0.9.5 → 1.0) is unchanged. This policy is stated once, here, and reflected in
  `pyproject.toml`, `README.md`, and the CLI `--version`.

## 9. Explicitly NOT built (per plan §13 non-goals)

reaction class #18; a universal isomer enumerator; full InChI structural inversion; a new retrosynthesis
engine; MaterialBucket/formulation (0.9); procedure-evidence ingestion (0.8); generalized CapabilityProfile
(0.9); new circuit/water executors; a chemistry/circuit shared ranker; a ΔG→bench-capability gate. No default
transform/ranking behaviour changed.

## 10. Discovered later-gate work

- **0.7:** route the expert `decompile`/`recompile` argv through the tolerant grammar (close the plan-vs-expert
  asymmetry in §5); collapse the FORMULA-layer decompile alias in `semantic_digest` (already a named follow-on).
- **0.7:** a parametric-syntax first-class type (rather than a typed refusal) if a consumer needs `(C2H4)n`.
- **0.8/0.9:** an isomer enumerator to widen `registry_candidates` beyond the offline registry.

## 11. Hostile merge-readiness round (2026-09-26) — P0 fixes before merge

A hostile pre-merge review found six silent mis-parses (each reproduced against source before repair; see
`experiments/v0_6_mutation_calibration.py` mutants 9–14 and `tests/test_formula_expr.py` /
`tests/test_plan_front_door.py`). All were structural fixes with a failing discriminator first, and none
touched search/ranking/transform chemistry.

- **P0-A cross-kind input ambiguity.** `AUTO "CO"` silently resolved to SMILES methanol though `CO` is also a
  valid formula (carbon monoxide). The legacy `resolve_identity` AUTO precedence is *preserved* for the expert
  commands (the anti-Mutant-5 ordering, and `test_mutant_5` still pins `CO → SMILES`). The **human `plan`
  surface** now calls the new `identity_parse.detect_auto_ambiguity`: when >1 input-kind reading resolves to a
  materially-distinct identity (differing layer or composition), `plan` returns `PlanStatus.INPUT_KIND_AMBIGUOUS`
  and refuses to launch structural planning until an explicit kind (`smiles:`/`formula:`/`--input-kind`) is
  given. Not a precedence flip (that would just move the bug).
- **P0-B ambiguous ASCII ionic charge.** `Fe3+` read as `Fe3`(+1). A **single-element** body with a digit run
  before a bare sign is now refused (`AmbiguousChargeError`); a **multi-element** body (`NH4+`, `NO3-`) keeps
  the count reading. General syntax rule, no per-element table (§ charge rule above).
- **P0-C decimal / degree separator.** A compact ASCII `digit.digit` (`C1.5H2`) silently became `C + 5(H2)`.
  It is now refused as a decimal (checked on the *raw* spelling, before normalization folds the distinction
  away). The Unicode middle-dot and the spaced ASCII dot remain valid hydrate separators; `render()` now emits
  the middle-dot so it round-trips through the guard. The degree sign `°` was removed from the separator set.
- **P0-D leading coefficient.** `5H2O` folded into composition `H10O5`. A leading whole-expression multiplier
  (component index 0) is now refused as a stoichiometric quantity; a multiplier *after* a separator (the hydrate
  `5`) stays valid.
- **P0-E TARGET_FILE transport.** `_resolve_target_file` reconstructed the identity without `formula_expr` /
  `registry_candidates`; both (and `registry_lookup_ok`) are now forwarded, so a file and its inline text
  perceive the same identity, differing only in file provenance.
- **P0-F registry error laundering.** `_registry_candidates` caught `except Exception: return ()`, turning any
  internal failure into the epistemic claim "no candidate known". It now catches only `ImportError` (the
  registry genuinely unavailable → `registry_lookup_ok=False`); a real bug propagates. Three states are
  distinguished (queried-N / queried-zero / unavailable), and the funnel's `ambiguity_classified` is gated on
  `registry_lookup_ok` so it cannot silently equal `composition_resolved` when the classifier failed.

### The "lossless" claim, resolved honestly (P1)

`FormulaExpr` identity does **not** preserve *intra-component* grouping: `(NH4)2SO4` ≡ `N2H8SO4` (same digest).
Rather than build a group-aware AST (which would cascade into `render`, the round-trip property, and the
digest), the claim is **narrowed to exactly what is preserved** — the component/hydrate-adduct boundary, the
composition, the supported charge, and the raw/normalized spelling as provenance — and the intra-component
grouping quotient is stated as deliberate: promoting a parenthesization to an identity distinction would smuggle
in the bond-graph claim v0.6 explicitly refuses. Grouping stays visible in `original`/`source`, and a
grouping-as-identity (MaterialBucket) is a 0.9 boundary. The quotient and the preserved boundary are both pinned
in `tests/test_formula_expr.py` (`test_P1_intra_component_grouping_is_a_documented_composition_quotient`,
`test_P1_the_component_boundary_is_NOT_quotiented_away`).

### Typed plan outcome (P1)

`PlanResult` now carries an explicit `PlanStatus` (`STRUCTURAL_PLANNING` / `FORMULA_DECOMPOSITION` /
`IDENTITY_ONLY` / `INPUT_KIND_AMBIGUOUS` / `INVALID_INPUT`) instead of overloading the `(operation, response,
exit_code)` triple to imply why planning did or did not continue. The `--json` payload gains `status` and (for
an ambiguous input) `input_kind_ambiguity`.

### Adversarial-review round (2026-09-26, same day) — two further breaks fixed

An adversarial pass on the P0 fixes found two that shared one root pattern (digit-run reasoning on the wrong
representation); both are now fixed and pinned:

- **P0-C subscript bypass.** The decimal guard scanned the *raw* string for an ASCII `digit.digit`, but subscript
  translation ran afterward, so `C₁.5H₂` (subscript-1) slipped past and became `CH10`. The guard now runs on the
  **subscript-folded** spelling (`str.translate(_SUBSCRIPTS)`) but *before* separator folding / whitespace
  stripping — so `C₁.5H₂` is caught while `CuSO4·5H2O` (middle dot) and `CuSO4 . 5 H2O` (spaced) are not. Pinned
  in `test_P0C_compact_ascii_decimal_is_refused_not_an_adduct`.
- **P0-B ≥2-digit oxoanions.** The ambiguity guard fired only for a single-element body, so a multi-element body
  with a **≥2-digit** trailing run (`SO42-`, `PO43-`, `CO32-`, `Cr2O72-`) took the count reading and produced an
  absurd 42-oxygen composition. The guard now also refuses **any** ≥2-digit trailing run before a bare sign (it
  is unclear how to split count from magnitude); a single trailing digit on a multi-element body (`NH4+`,
  `NO3-`) stays the unambiguous count reading. Pinned in `test_P0B_multi_element_two_digit_run_is_ambiguous`.
