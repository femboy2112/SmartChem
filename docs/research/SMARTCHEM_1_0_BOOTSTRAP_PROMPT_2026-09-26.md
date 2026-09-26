# Claude Code Bootstrap — SmartChem 1.0 Program + v0.6 Mega-Round

Use this prompt after the planning branch is available remotely.

---

You are working on:

`femboy2112/SmartChem.git`

The 1.0 planning branch is:

`aletheia/smartchem-1.0-release-program-2026-09-26`

It was intentionally based on:

`9db02e549104e0abc3e0d5b6840094df8e12ee03`

Do not trust those refs blindly. Inspect repository truth first.

## Mission

There are TWO phases in this session.

### Phase I — land the 1.0 release program coherently

1. Fetch all remotes.
2. Inspect current `main` and the planning branch.
3. Read, in full:
   - `docs/research/CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md`
   - `docs/research/V0_6_HUMAN_CHEMICAL_FRONT_DOOR_PLAN_v0.1.md`
   - `ROADMAP.md`
   - `README.md`
   - `CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md`
   - `AUDIT_GENERIC_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md`
   - `docs/research/RULE_CALCULUS_COURSE_CORRECTION_2026-09-19.md`
   - `docs/research/TRANSFORM_ALGEBRA_EXPANSION_ROUND_2026-09-20.md`
   - `docs/research/POOR_MAN_ARCH_COMPLETION_PLAN_v0.1.md`
   - `docs/research/POOR_MAN_DEFER_LEDGER_2026-09-17.md`
4. Compare the planning branch to current main.
5. If main has moved since `9db02e549104e0abc3e0d5b6840094df8e12ee03`, inspect every intervening commit that affects chemistry/compiler semantics.
6. Review the planning docs against current source. Fix factual drift on the planning branch if needed; do not weaken
   epistemic boundaries just to make the plan prettier.
7. Run lightweight relevant checks for doc/link truth.
8. Merge the planning branch into main only when coherent.
9. Push main.
10. Do NOT tag a release merely for planning docs.

Historical records are evidence. Do not rewrite old audit outcomes to look current; update current pointers instead.

### Phase II — immediately start the v0.6 Human Chemical Front Door mega-round

After Phase I lands, create a fresh non-main feature branch, preferably:

`feat/v0.6-human-chemical-front-door`

Then execute the v0.6 plan aggressively but soundly.

The product goal is:

> A human can paste ordinary chemical notation, including common Wikipedia-style formula typography, into one
> SmartChem front door; SmartChem preserves/normalizes the syntax, determines composition, states the strongest
> identity layer actually known, exposes ambiguity instead of guessing structure, and continues only into operations
> justified by that identity layer.

## Non-negotiable architecture

- `identity_parse.resolve_identity` is the single identity authority unless repository truth demonstrates a better
  existing seam. Do not create parser drift.
- Formula -> structure is a RELATION, not a function.
- Add a lossless syntax layer before `Formula`; do not destroy hydrate/adduct/grouping information before the
  composition projection.
- Explicit input kinds/prefixes remain authoritative.
- Old registered-name and SMILES behavior must not be accidentally stolen by AUTO formula detection.
- Formula-only targets must not enter structural synthesis by guess.
- Preserve search receipts, identity losses, provenance, request digests, and fail-closed behavior.
- Do not add reaction family #18 in this round.
- Do not turn RDKit/PySCF into mandatory parser dependencies.
- Do not conflate parser success with chemical identity success.

## Required implementation surface

### A. Formula expression / normalization layer

Implement the smallest durable representation that can preserve and normalize the declared finite human formula
grammar. It must handle and test at least:

- `H2O`
- `C8H10N4O2`
- `C₈H₁₀N₄O₂`
- `(NH4)2SO4`
- `(NH₄)₂SO₄`
- `CuSO4·5H2O`
- `CuSO₄·5H₂O`
- whitespace/separator variants
- supported charge spellings, if admitted after audit

Boundary/control inputs must include parametric/polymer forms, malformed grouping, unknown elements, dangling
separators, zero counts, and ambiguous notation.

Pin:
- normalization idempotence;
- Unicode/ASCII projection equality;
- conservation of element counts/charge;
- component-boundary preservation;
- render/reparse equivalence;
- fail-closed malformed syntax.

### B. Identity integration

Extend the current typed identity result/receipt rather than creating a parallel universe.

Add first-class semantics for:
- composition known;
- structure known;
- known registry ambiguity set;
- structure not established.

A registry candidate set is NOT an exhaustive isomer theorem.

### C. Human orchestration

Audit whether the existing service can express the total-answer workflow.

If yes, extend it.

If no, add a THIN `plan` command/API that delegates to the existing identity/decompile/recompile machinery and only
orchestrates which operations are justified. It must not fork search/ranking engines.

### D. 1.0 funnel harness

Commit a durable corpus and machine-readable harness measuring at least:

`input -> syntax -> composition -> identity layer -> ambiguity -> structure -> planning eligibility`

Produce both aggregate counts and per-case records.

### E. Truth/release cleanup

Reconcile current release-facing truth you encounter:
- package version policy;
- README current counts/capabilities;
- ROADMAP current pointers;
- stale CI comments (especially the retired interchange xfail);
- hosted CI status if available.

Do not make up CI success. If GitHub Actions is unavailable due to account/runner state, record that exact access
boundary and run the established local/OOM-safe suite.

## Adversarial gate

Do not stop at happy-path tests.

Kill mutants equivalent to:
1. dropping Unicode subscripts;
2. dropping hydrate coefficients;
3. flattening component boundaries before the receipt;
4. inferring one structure from formula equality;
5. AUTO formula stealing a registered name/SMILES;
6. formula-only target entering structural recompile;
7. provenance/receipt disappearing in serialization;
8. unsupported parametric syntax becoming a concrete count.

Use fresh holdouts after implementation choices are fixed.

## Acceptance

Before asking to merge:
- targeted tests green;
- full established suite green in safe partitions;
- parser/property/fuzz tests green;
- mutation controls killed;
- funnel corpus committed and reproducible;
- old explicit name/SMILES behavior checked;
- no accidental default chemistry/ranking changes;
- docs accurately describe what shipped;
- version bump only if the v0.6 gate is actually complete.

## Working style

Go full blast, but keep the architecture narrow.

When you find an apparent extra opportunity, classify it:
- required to make the v0.6 contract sound -> build it;
- valuable but orthogonal -> record it as a later-gate item;
- unsupported by evidence -> defer explicitly.

Prefer structural fixes over case tables. Preserve raw evidence and exact receipts. A generated rule/parser path is not
its own independent verifier. Use hostile controls that can actually distinguish the competing implementations.

## Deliverable at the end of the session

Report:
1. exact branch/commit state;
2. whether the planning branch was merged and the merge SHA;
3. implementation commits;
4. tests/probes/fuzz/mutations actually run, with exact counts;
5. before/after v0.6 funnel;
6. any semantics/schema/version changes;
7. every remaining blocker to v0.6;
8. the single highest-value next move toward 0.7.

Do not merge the v0.6 feature branch to main unless its declared acceptance gate is genuinely met. If it is not met,
leave a coherent non-main branch with a precise blocker ledger rather than fabricating completion.
