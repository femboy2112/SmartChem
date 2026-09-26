# SmartChem v0.6 Human Chemical Front Door — Mega-Round Plan

**Status:** ready to execute after the 1.0 program lands on main  
**Version:** v0.1  
**Date:** 2026-09-26  
**Program:** `CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md`  
**Starting baseline for the planning branch:** `main@9db02e549104e0abc3e0d5b6840094df8e12ee03`

---

# 1. Mission

Build the first finite release gate on the road to SmartChem 1.0:

> A human can paste ordinary chemical notation — especially formula strings copied from a source such as Wikipedia —
> into one SmartChem front door, and SmartChem deterministically preserves the syntax, resolves the strongest identity
> layer it actually knows, computes composition, and either continues to structural planning or returns an explicit
> ambiguity/model-boundary result.

This round is primarily **front-door + identity + release-instrumentation work**.

Do NOT use it as an excuse to add reaction family #18.

---

# 2. Baseline truths to preserve

At the baseline:

- `identity_parse.resolve_identity` is the one shared identity-resolution authority.
- NAME and SMILES can resolve to `Molecule` / CONSTITUTION.
- FORMULA resolves to `Formula` / FORMULA only.
- InChI support intentionally resolves only the formula/charge sublayer and records losses for unconsumed structure,
  stereo, and isotope layers.
- `recompile` is structural and correctly refuses a formula-only target rather than guessing a constitution.
- `decompile` can operate at formula level.
- explicit `name:`, `smiles:`, `inchi:`, `formula:` and the explicit CLI flags have defined precedence and
  must remain authoritative.
- service/CLI alias unification and request digests are already carefully tested.
- search receipts and identity losses are load-bearing and may not be silently bypassed.

Any design that creates a second parser authority or a second CLI identity path is presumptively wrong.

---

# 3. Acceptance object

A new front-door parse should return enough information to answer:

```text
What did the user type?
What normalized syntax did SmartChem understand?
What exact composition follows?
Was any syntax information forgotten to reach composition?
What is the strongest identity layer perceived?
Is there a unique known structure, an ambiguity set, or no represented structure?
What operation can honestly continue from that layer?
```

The exact Python type names may change after repository audit, but the semantic content may not.

---

# 4. Build A — lossless FormulaExpr

## 4.1 Requirement

Introduce a syntax-level representation before `Formula`.

Candidate shape:

```python
@dataclass(frozen=True)
class FormulaExpr:
    components: tuple[FormulaComponent, ...]
    charge: int = 0
    original: str = ""
    normalized: str = ""
```

This is illustrative, not an API command. Prefer the smallest representation that preserves the real syntax
distinctions needed by the release contract.

A component must at minimum preserve:

- grouped atom-count expression;
- leading component multiplier;
- component ordering as input provenance if appropriate;
- separators/adduct boundaries;
- overall/component charge if admitted by the grammar.

The projection `FormulaExpr -> Formula` MUST be deterministic and conservation-correct.

## 4.2 Required syntax corpus

Positive controls should include at minimum:

```text
H2O
C8H10N4O2
C₈H₁₀N₄O₂
(NH4)2SO4
(NH₄)₂SO₄
CuSO4·5H2O
CuSO₄·5H₂O
CuSO4 . 5 H2O
CaCl2·2H2O
Al2(SO4)3
K4[Fe(CN)6]          if square grouping is admitted
SO4^2-
SO₄²⁻                if Unicode charge grammar is admitted
NH4+
[NH4]+               if bracket-ion grammar is admitted
```

Do not claim support for a spelling until it has a committed test.

Negative/boundary controls:

```text
(C2H4)n
MxOy
C6H(12±2)O6
2
()
CuSO4·
5H2O                 decide whether leading whole-formula multiplier is a formula or a stoichiometric coefficient
garbage prose
unbalanced brackets
zero/negative counts
unknown element symbols
ambiguous superscript/minus placements
```

For every boundary, choose one of:

- represented exactly;
- represented parametrically under an explicit type;
- refused with a typed reason.

Never silently strip unknown syntax.

## 4.3 Normalization laws

Pin at least:

- idempotence: normalize(normalize(x)) == normalize(x);
- Unicode/ASCII equivalent spellings project to the same `Formula`;
- source component boundaries survive in `FormulaExpr`;
- projection conserves every element and admitted charge;
- normalized rendering reparses to an equivalent expression;
- whitespace normalization does not alter semantics;
- malformed input cannot normalize to a valid unrelated formula.

Use property-based tests where the representation permits it.

---

# 5. Build B — one identity front door

## 5.1 AUTO discrimination

Today AUTO is name-first then SMILES, with explicit formula/inchi prefixes. Add formula auto-detection only if it can
be done without destabilizing valid name/SMILES behavior.

Required precedence principle:

1. explicit kind/prefix wins;
2. registered name behavior remains stable;
3. unambiguous structured syntax remains stable;
4. an obvious formula may resolve as FORMULA;
5. ambiguous strings must produce an ambiguity result or retain an established precedence with an explicit receipt;
6. never run two parsers and quietly pick whichever result is more convenient downstream.

Build a collision corpus including short strings that might plausibly be chemical symbols, names, or SMILES.

## 5.2 Parse receipt

Extend the existing `ParseReceipt` rather than inventing a second receipt system unless code truth proves that
extension would violate its contract.

The receipt should carry, directly or through a nested formula-normalization receipt:

- requested kind;
- resolved kind;
- original source;
- normalized representation;
- identity layer;
- notes/losses;
- ambiguity information where applicable.

A different spelling of the same resolved structural identity may still collapse to one semantic search request, but
the parse receipt should preserve how the input was read.

---

# 6. Build C — explicit identity ambiguity

Introduce a first-class result for:

```text
composition known
constitution not uniquely established
```

Do not represent this as an internal exception.

The simplest acceptable implementation can begin with:

- formula-only target -> composition known, no selected structure;
- if the offline registry contains multiple known structures with that formula, report the known ambiguity set;
- if zero/one registered structures are known, do NOT infer that the chemistry has zero/one real isomers. Label the
  set as registry-known candidates, not an exhaustive isomer enumeration.

This is a key epistemic distinction.

A future structure enumerator can widen the candidate set; 0.6 only needs the typed semantics.

---

# 7. Build D — high-level human entry point

Audit whether the canonical `run_compilation` service can directly provide the desired total-answer orchestration.

If it can, prefer extending the existing service.

If the current DECOMPILE/RECOMPILE operation split prevents a clean human workflow, add a thin high-level command/API,
provisionally:

```text
smartchem plan TARGET
```

Its job is orchestration only:

1. resolve input;
2. always expose composition if known;
3. run formula-level decomposition when valid/requested;
4. run structural recompile only when a constitution is actually selected/perceived;
5. otherwise return the typed ambiguity/boundary result.

It MUST NOT fork search logic, duplicate identity parsing, or create a second ranking engine.

Keep `decompile` and `recompile` as expert primitives.

---

# 8. Build E — 1.0 funnel instrument

Create a committed machine-readable harness under `experiments/` or another established validation location.

The first version only needs the early funnel:

```text
input
 -> syntactically represented?
 -> composition resolved?
 -> identity layer?
 -> ambiguity classified?
 -> structure represented?
 -> structural planning eligible?
```

Define a stable row schema with:

- case id;
- raw input;
- requested kind;
- expected normalized composition;
- expected identity layer/outcome;
- flags for each funnel stage;
- receipt digest / result digest where useful.

The harness must produce aggregate denominators and retain per-case failures.

Do not optimize percentages yet. First make the measurement durable.

---

# 9. Build F — release-truth reconciliation

Before declaring 0.6 done, reconcile stale release metadata discovered during the 1.0 audit:

- `pyproject.toml` version policy;
- README suite/current-capability prose;
- ROADMAP top pointers/current round;
- CI comments that still describe the retired interchange xfail;
- any other factually stale release-facing statement found during the branch audit.

Do not rewrite historical audit records to make them look current. Add/update current pointers and leave historical
receipts intact.

Version bump policy:

- landing the planning docs alone is NOT a package capability bump;
- completing the v0.6 gate should produce the corresponding package version only after all acceptance tests pass;
- if project semantics prefer another pre-1.0 numbering convention, document the mapping in one place and keep the
  finite 0.6/0.7/0.8/0.9/0.9.5 conceptual gates.

---

# 10. Tests and adversarial gate

At minimum, the round is not complete without:

## Positive

- ASCII formula controls;
- Unicode subscript controls;
- hydrate/adduct controls;
- supported charge controls;
- old registered-name controls;
- old SMILES controls;
- explicit input-kind controls;
- target-file controls.

## Negative

- malformed grouping;
- unsupported parametric formula;
- unknown element;
- dangling adduct separator;
- conflicting explicit-kind/prefix;
- formula-vs-SMILES/name collision cases;
- same-formula different-structure cases;
- formula-only request trying to enter structural search.

## Mutation controls

Kill mutants such as:

1. strip Unicode subscripts instead of translating them;
2. drop a hydrate multiplier;
3. merge component boundaries before the syntax receipt;
4. infer a registered structure merely because its formula matches;
5. let AUTO formula detection steal a registered name;
6. let a formula-only target enter `recompile_to_ir`;
7. drop parse/normalization provenance from the request/result;
8. turn unsupported parametric syntax into a concrete count.

## Fresh holdout

Prepare a small holdout set after implementation details are frozen. It must contain formula spellings/families not
used to design the parser branches.

---

# 11. Performance / dependency constraints

- The front door should remain lightweight.
- Do not make RDKit or PySCF mandatory runtime dependencies merely to parse ordinary formulas.
- Prefer deterministic local parsing.
- Maintain supported Python versions.
- Avoid algorithmic blowups on malformed/nested input; set explicit depth/size guards if needed.
- A user-pasted formula is a short object. Retain a reasonable input-size bound and test it.

---

# 12. Files likely involved

Audit first; do not treat this as a forced file list.

Likely:

```text
smartchem/decompiler.py              Formula today
smartchem/identity_parse.py          one identity authority
smartchem/cli.py                     human CLI
smartchem/service.py                 typed request/result
smartchem/compilation_ir.py          identity/IR semantics
tests/test_decompiler.py
tests/test_id_parse.py
tests/test_cli*.py
tests/test_service.py
tests/test_compilation_ir.py
experiments/...                      funnel corpus/probe
README.md
ROADMAP.md
pyproject.toml                       only at actual release gate
.github/workflows/ci.yml             stale truth / packaging gates if justified
```

A separate `smartchem/formula_expr.py` is likely cleaner than making `decompiler.py` larger, but repository fit
wins over this suggestion.

---

# 13. Deliberate non-goals of this mega-round

Do NOT build unless required by a front-door correctness bug:

- reaction class #18;
- a universal isomer generator;
- full InChI inversion;
- a new retrosynthesis algorithm;
- poor-man MaterialBucket implementation (0.9);
- procedure evidence ingestion (0.8);
- generalized capability profiles (0.9);
- cross-domain PhysicalIR work;
- new circuit/water executors;
- a chemistry/circuit shared ranker;
- a delta-G-to-capability gate.

Document discovered dependencies instead of smuggling them into this round.

---

# 14. Merge gate

Before merging the implementation branch:

1. rebase/update from current main;
2. inspect every main change since the planning baseline;
3. run the established OOM-safe full suite;
4. run targeted front-door/identity/CLI/service tests;
5. run parser property/fuzz tests;
6. run mutation controls;
7. run the frozen funnel harness;
8. confirm existing explicit name/SMILES semantic digests or expected migration notes;
9. confirm no default chemistry/ranking behavior changed accidentally;
10. update docs/version only to the capability actually delivered;
11. make a clean PR with exact before/after funnel numbers.

---

# 15. Success definition

v0.6 succeeds when SmartChem has a user-facing entrance whose semantics are strong enough that the rest of the 1.0
program can build behind it without later discovering that "formula", "compound", "material", and "structure" were
collapsed at the first line of input.

The most important result is not that more strings parse.

It is that **human chemical notation becomes a typed, replayable, non-hallucinatory compiler input**.
