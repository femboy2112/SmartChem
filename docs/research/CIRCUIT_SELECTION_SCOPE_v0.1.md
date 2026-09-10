# The circuit-route selector — the open-circuit pipeline's first non-test caller (brick a, EM scope)

Status: **built, sound, bounded.** Lane B. `[[electromagnetic-scope]]` `[[categorical-reorientation]]`

ROUND 37's circuit pipeline (`smartchem/open_circuit_pipeline.py`) supplied the second-domain
`ingest -> generic core -> cost -> survival` shape, and its own docstring named the residual honestly:
*"nothing OUTSIDE this module + its test/probe plans, ranks, or verifies a circuit through this shape … this
pipeline still awaits its first non-test caller."* This round supplies that caller.

## What is built (`smartchem/circuit_selection.py`)

A circuit-route **selector** — the EM-scope analogue of the chemistry `drafter`'s route ranker. It PLANS /
RANKS / VERIFIES circuit designs through the pipeline shape:

- **`select_within_spec(candidates, low_ohms, high_ohms) -> CircuitSelection`** — reads each candidate's domain
  COST (`equivalent_resistance`), gates on the Move-5 SURVIVAL predicate (`within_spec`), and presents the
  survivors ordered ascending by EXACT resistance then name. This is a real total order on an exact `Fraction`,
  so `best` is reproducible, never float-fragile. It is NOT a claimed "optimum" (the R26 Pareto-front discipline:
  present the honest datum, do not collapse — here there is genuinely one cost axis, resistance, so a total order
  is honest, and every in-band survivor meets spec).
- **`CircuitCandidate` / `RankedCandidate` / `CircuitSelection`** — the typed input/output shape.
  `CircuitSelection.rejected` DISCLOSES every non-survivor as `(name, cost-or-None)` — an out-of-band finite
  cost, or `None` for an open / short / non-two-terminal apex — so nothing is dropped silently. `best` is the
  head of the deterministic order, or `None`.
- **`main(argv)` / `python -m smartchem.circuit_selection`** — a minimal, fail-closed user-facing driver: rank
  `--candidate NAME=SPEC` designs against a `--band LOW HIGH` resistance spec. This is the SELECTOR's own earned
  call site (so the selector is not itself a zero-call-sites structure), and it keeps the circuit domain OFF the
  chemistry front door (`smartchem.cli` is explicitly *"the front door to SmartChem's chemistry verticals"*) —
  circuits are the SECOND domain, their own EM-scope vertical, mirroring `smartchem.experiment` /
  `smartchem.evidence` as their own `python -m` entry points. Zero edits to existing production files; zero help/
  golden regression surface.

The spec grammar is deliberately tiny and fail-closed: a spec is a comma-separated SERIES of stages, a stage is a
single non-negative integer resistance or a `|`-separated PARALLEL block, e.g. `"2,3,4|4"` = `2 -> 3 -> (4||4)` =
`7` ohms. Any non-integer token is refused (no floats — resistances are exact). Exit codes mirror the chemistry
front door: `0` a survivor was selected, `3` none met spec, `2` invalid input.

## Fail-closed discipline

- The spec band is validated FIRST, before the candidate loop and regardless of candidate count, so a malformed
  band is refused even on an EMPTY candidate set (the `vacuous-green-over-an-empty-subject` lesson: a check that
  only fires on a non-empty subject passes a bad spec vacuously).
- A candidate whose cost is `None` never survives — disclosed in `rejected`, never silently dropped. A
  `RankedCandidate` provably carries a finite cost (the explicit `cost is not None` before ranking).
- Bounds are EXACT (`int` / `Fraction` / `Rational`, or `+-math.inf` for a one-sided band); a finite float bound
  is refused; `low <= high` is required. Bound validation reuses `open_circuit_pipeline._spec_bound` — a single
  source of truth, never a duplicated rule that could drift.

## The Move-5 claim, bounded honestly (the last-round over-claim lesson)

This advances the Move-5 case by exactly **ONE concrete step**: the pipeline's stated residual (*"awaits its
first non-test caller"*) is now discharged — the pipeline has a PRODUCTION consumer of the same KIND the
chemistry side has (a route ranker with a user-facing entry point). The full ingest → generic-core → cost →
survival → **select → CLI** chain is now live, with no dead link. But that is a single step, **NOT proximity to
completion** (heeding birdperson's warning that "closer-to-complete" invites a generous misread): the distance
from here to actual Move-5 completion is the ENTIRE deferred domain-neutral refactor, not one more brick.

It does **not complete** Move 5. Recon confirmed the chemistry ranker `smartchem.experiment.drafter.rank_routes`
is **hard-typed to `ExperimentRoute`** (its `fit_routes` path raises `TypeError` on anything else), and the only
genuinely domain-neutral primitives (`experiment.functorial_physics.pareto_optimal`,
`experiment.affordability.pareto_frontier`) are each bound to a chemistry VALUE type (`PhysicsProduct`'s axes are
semantically ΔG/survival; `CostVector`'s are cash/energy) — so forcing a circuit route through them would be a
semantic stretch, not literal reuse, and was deliberately NOT done (it would over-claim genericity the axes do
not support). Completion requires making the CHEMISTRY `ExperimentStep` / `ExperimentRoute` literally parametric
over a "conserved-inventory transition + survival predicate" AND retrofitting BOTH domains onto ONE shared ranker
— its own large round. No chemistry code and no shared primitive flows through any of this brick; the cross-domain
UNIFICATION that would COMPLETE Move 5 is untouched.

So: the genericity is now exercised end to end by a real consumer WITH a real caller in the circuit domain; the
two domains are not yet unified under one primitive. Bounded honestly against the last-round over-claim lesson.

## Boundary (sound deferrals)

- **Ideal DC resistor networks only** (no RLC/AC) — the item-6 / pipeline scope, inherited.
- **The cost axis is scalar equivalent resistance** — defined for 1→1 (two-terminal) routes. A multi-port
  network has no single scalar "resistance" (its full relation is its apex); such candidates are out of scope for
  this selector (the pipeline's `equivalent_resistance` already fail-closes to `None` on them → disclosed).
- **No cross-domain shared ranker** — the honest Move-5 residual above.

## Files

- `smartchem/circuit_selection.py` — the selector (`select_within_spec`, `CircuitCandidate`, `RankedCandidate`,
  `CircuitSelection`) + the `python -m` driver.
- `tests/test_circuit_selection.py` — selector logic, fail-closed band/open-circuit/type gates, the ingest path
  reaching the selector, the parser, and the driver's exit codes.

## Adversarial review — two orthogonal bearings before merge

**The core selector is sound; every fold was at the human-facing edges or a framing/dead-code tidy.** No bearing
found a wrong `best`, a mis-ordered survivor, or an out-of-spec/`None`-cost admission.

- **evil-morty (directed break):** the selector survived 4000 randomized selections (0–6 candidates, ties on
  resistance and name, bands including `inf`/exact `Fraction` edges) against an independent expected-survivor
  oracle — **0 mismatches**; the order is total and stable; band validation fails closed on every path
  (empty candidates, `NaN`, `bool`, finite float, inverted band); `main()` exit codes correct across ~15 hostile
  argv sets; `0|0` parallel wires to `0`, no ZeroDivision. Two LOW folds, neither a wrong-circuit path: (1) the
  `--band` help promised `-inf` but argparse's tokenizer stranded a leading-dash value → the CLI floor is now a
  non-negative integer and the help matches (a `-inf` floor is meaningless for a non-negative resistance;
  `select_within_spec` keeps `-inf` for its domain-general one-sided band); (2) the parser's `isdigit()` admitted
  non-ASCII decimals (`'٣'`→3, always the correct value, never a wrong circuit) → tightened to
  `isascii() and isdigit()`, comment corrected.
- **birdperson (principled soundness):** SOUND-BUT-HEED. Verified the residual is genuinely discharged (exactly
  one real non-test caller — the selector; `main()` is a real CLI terminus, not zero-call-sites cover), the order
  is honestly framed (not a fabricated optimum), the `_spec_bound` private import is the correct single-source
  reuse, and the Move-5 boundary is honest. Two folds: (1) `CircuitCandidate.equivalent_resistance` was a dead
  property (no consumer) → the selector now ranks through it, giving it a live call site AND removing a redundant
  second apex solve per candidate (the "speed without losing rigor" directive) — byte-identical output; (2) the
  "closer-to-complete" wording invited a generous misread → relabeled to "one concrete step, NOT proximity to
  completion" (above), so the residual distance to real Move-5 unification is stated plainly.
