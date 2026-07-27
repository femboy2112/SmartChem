# SmartChem open-semantics build/research round — live contract

**Remote parent:** `femboy2112/SmartChem@521e7192b8914022bedbdaccaa41ed708ae974fc`

**Stacked branch:** `agent/smartchem-open-semantics-round-20260727`

**Entry baseline:** `1279 passed, 51 skipped, 1 xfailed`; the skipped tests require
optional PySCF or the explicit slow-test gate and are not counted as passes. The parent
commit's GitHub Actions run was green on Python 3.10, Python 3.12, the PySCF-visible fast
suite, one real PySCF calculation, and the real-backend benchmark.

## Calculation ledger at entry

No calculation is in progress. All chemistry, water v1/v2/continuous, human-proxy,
synthetic-survival, reaction-residue, and finite Ising/lattice-gas calculations listed in
`CAMPAIGN_HANDOFF_2026-07-27.md` are terminal. This round may not reuse a terminal journal
as a new result. Any cited resistive-DC evaluation requires a new calculation identity,
approval, write-once journal, and receipt.

### Live updates

- Smoke run `4a1e845448e041d79e7bee34ca4a638b` reached `COMPLETE` at
  `/tmp/smartchem-resistive-dc.5SI4vM/run.json`. It is terminal and will not be reused as
  the final result; it exposed and led to a formatter-only repair in the committed harness.
- Run `a81b652df9404cd0a566c662f2d3be3e` reached `COMPLETE` at
  `/tmp/smartchem-resistive-dc-final.JUij6f/run.json`, but the surrounding console
  formatter then failed on the shepherd outcome's string representation. The journal is
  terminal and valid but will not be reused or cited as the final harness receipt.
- Repaired run `c1fbd28a8d6146828a4717123bf35df6` reached `COMPLETE` at
  `/tmp/smartchem-resistive-dc-final.D77uoy/run.json`. A subsequent package-docstring
  correction deliberately changed the compiler implementation digest, so this terminal
  run will not be reused as the final cited source state.
- The source-final bridge calculation `4ae82cdc60464cc7be231ba2015bdfa1`
  reached `COMPLETE` at `/tmp/smartchem-resistive-dc-final.redHXx/run.json`.
  All six obligations and all three outputs passed; no calculation is now in progress.

## Recovered dependency cut

The inherited roadmap named:

1. S0: exact typed open-diagram syntax;
2. E1: a topology-generic passive resistor DC control.

Three separately tasked bearings converged on S0 followed by E1 as the strongest pair
presently available: both are deterministic, finite, locally falsifiable, require no
missing data authority, and directly test the proposed category backbone. Their agreement
is prioritization input, not evidence for the mathematical claims; the evidence must come
from implementation, exact controls, independent arithmetic, and hostile tests.
Dispersive water has a larger PDE and validation surface; empirical survival is blocked on
independent-data authority; traffic needs a new closure/calibration model; and the next
optimizer lacks a currently identified exact reusable artifact.

The bearings also found two defects in the inherited formulation:

- a fixed canonicalization budget makes canonical observation partial, so an executable
  API that canonicalizes during every `then` or `tensor` is not closed under composition;
- storing resistor kind/value in `StructureIR` makes a constitutive-parameter edit look
  like a topology edit.

The corrected separation is:

| Layer | This round's owner |
|---|---|
| structural presentation | typed interfaces, component slots/arity, junction incidence, total presentation composition and tensor |
| exact quotient observer | alpha-invariant canonical form when the declared finite search budget succeeds; named resource refusal otherwise |
| resistive model | exact positive rational resistance assigned to every structural slot |
| exact semantics | boundary linear relation over potentials and inward currents |
| experiment | signed voltage drive, reference, sparse numerical solve, tolerances, retained residuals and power |

The underlying finite open-diagram quotient is a mathematical category. The practical
canonical observer is resource-bounded. Category laws in this repository therefore mean
exact equal canonical forms for every tested presentation whose observation succeeds;
they are not a formal proof over arbitrary finite graphs.

## Hole contract S0′ — total typed wiring presentation

### Proposed statement

There is a finite typed presentation with ordered input/output interfaces,
two-terminal electrical component slots, and multiway junction incidence such that:

1. malformed, missing, duplicated, out-of-range, or mixed-kind occurrences are
   unconstructible;
2. presentation-level `then` and `tensor` are total for every pair with compatible
   interfaces and never depend on canonicalization;
3. a separate exact observer discards local IDs and declaration order, preserves
   multiplicity and self-loops, and either returns the same canonical value for
   isomorphic presentations or names a search-budget refusal;
4. identity, associativity, tensor unit/associativity, interchange, braid involution,
   braid naturality, and symmetric-monoidal coherence survive generated and adversarial
   exact controls.

### Truth state at entry

**Conjectured.** The inherited roadmap describes an algorithm but no implementation
exists. Its original closure claim is refuted by tensor powers of symmetric closed
fragments that individually fit but jointly exceed any fixed factorial budget.

### Weakest sufficient form and quantifiers

One electrical port kind and one undirected two-terminal component signature are
sufficient. The statement ranges over constructible finite presentations. Exact
alpha-equality is asserted only when observation succeeds within its declared budget.
No R/L/C constitutive value belongs to structural identity.

### Dependency edges closed if supported

- replaces the false parallel-history metaphor with explicit wiring;
- provides the topology shared by exact resistor semantics and sparse MNA;
- makes topology hashes available for safe caching when canonical observation succeeds;
- supplies the structural half of later domain-specific open components.

### Novelty tax and boundary

This is not a relabeling of `Reaction.tensor`: it introduces junction incidence and
genuine disjoint-union/gluing operations that can satisfy interchange. It is not yet a
general hypergraph/process language, a proof assistant theorem, a circuit solver, or a
multiphysics runtime.

### Cheapest falsifiers

- alpha-renaming or declaration reordering changes a successful canonical value;
- a duplicated or missing endpoint constructs successfully;
- parallel equal edges collapse;
- a self-loop is counted once rather than twice in refinement;
- presentation tensor/composition invokes the budgeted observer or refuses for resource
  reasons;
- either side of a generated category/coherence law observes to a different exact value.

### Candidate construction

Frozen records, union-find boundary gluing, disjoint-union tensor, color refinement with
fixed boundary markers, exhaustive permutations within final color cells, and an explicit
factorial candidate budget.

### Next lamp if Dark

Retain the total presentation and counterexample, narrow the quotient observer to a
smaller graph class, and do not proceed to E1 as a categorical semantics claim.

## Hole contract E0/E1 — exact resistor relation plus sparse evaluator

### Proposed statement

For a typed wiring presentation and an exact positive-rational resistance on every
component slot:

1. exact elimination yields a boundary linear relation in variables
   `(V_boundary, I_boundary_inward)`;
2. serial gluing identifies shared potentials and cancels inward currents, while tensor
   is direct product;
3. exact black-boxing respects those operations on identity, series, parallel, bridge,
   cycle, and generated small controls;
4. a separate grounded, voltage-driven sparse MNA evaluator uses one stamping path,
   retains every node/branch/source quantity, and passes dimensionally separate KCL-A,
   voltage-constraint-V, exact-relation, and source-inclusive power-W checks;
5. floating, shorted inconsistent, singular, non-finite, or materially residual-bearing
   evaluations refuse rather than returning an authoritative finite result.

### Truth state at entry

**Conjectured.** The existing scalar-impedance tests refute a scalar monoidal semantics.
No open resistor relation or MNA implementation exists.

### Hypotheses and quantifiers

Finite undirected ideal resistors with strictly positive exact rational ohmic values.
Boundary currents are oriented inward. The numerical evaluator covers one signed ideal
voltage source and one declared reference at finite tolerances. It does not cover
capacitors, inductors, dependent/nonlinear sources, dynamics, temperature, parasitics, or
measured hardware.

### Weakest sufficient form

An exact rational relation implementation plus a binary64 sparse evaluator independently
checked against it on analytic, bridge, cyclic, mutation, and small generated cases. A
general AC/RLC or port-Hamiltonian implementation is unnecessary.

### Dependency edges closed if supported

- supplies the first real domain semantic algebra for the open structural glue;
- falsifies hidden series/parallel dispatch using a bridge;
- establishes a safe boundary for topology-hash/factorization reuse;
- provides the control required before AC/RLC and before any power-pairing claim.

### Novelty tax and boundary

The exact boundary relation is materially stronger than another impedance helper because
it composes by elimination and retains all boundary variables. The driven numerical
solution is one constrained evaluation of that relation, not itself proof of a general
semantic functor. Passing finite generated controls is not a universal formal proof.

### Cheapest falsifiers

- exact black-boxing disagrees with relational composition or tensor;
- bridge evaluation requires a topology-specific branch;
- an alpha-renamed/reordered structure changes the exact relation or physical outputs;
- KCL, source constraint, exact relation, or power fails beyond declared scales;
- a floating or solver-mutated problem completes;
- one raw residual mixes amperes and volts.

### Candidate construction

Exact rational row reduction and existential linear elimination for boundary relations;
SciPy COO-to-CSC sparse MNA for the independent numerical path; analytic and exact-small
controls as holdouts.

### Next lamp if Dark

Preserve the first failing exact relation or numerical counterexample. Stop at S0′ if the
semantic failure is real; do not jump to AC/RLC or hide it behind regularization.

## Claim ledger at entry

| Claim | State | Evidence or falsifier |
|---|---|---|
| Closed reaction paths remain useful | Disclosed | constructor conservation and sequential path laws |
| `Reaction.tensor` is parallel composition | Refuted | strict interchange counterexample |
| A fixed-budget canonicalizing `then`/`tensor` is a total category API | Refuted | symmetric tensor-power factorial counterexample |
| Structure and constitutive parameter identity should be separate | Corroborated design constraint | topology edits and resistance edits have different downstream effects |
| S0′ can supply exact open wiring | Conjectured | implementation and hostile law probes pending |
| Exact resistor black-boxing is compositional in this implementation | Unverified | relation-composition holdouts pending |
| Sparse MNA agrees with the exact relation | Unverified | analytic, bridge, generated, and mutation probes pending |
| This yields a general multiphysics category | Refuted as a present claim | only finite two-terminal electrical wiring/resistors are in scope |

## Exit state

### Implemented

- `smartchem/open_diagram.py`: total typed finite presentations, exact budgeted observer,
  identities/braid, and no constitutive parameters.
- `smartchem/circuit.py`: presentation-bound exact rational resistor model, exact boundary
  linear relations, relational composition/direct product, and one sparse DC MNA path.
- `smartchem/resistive_dc.py`: eighth closed executor and complete lifecycle.
- `experiments/compiled_resistive_dc.py`: deterministic typed-shepherd harness.
- `experiments/RESULTS_compiled_resistive_dc.md`: durable final receipt.

### Exit claim ledger

| Claim | Exit state | Evidence and boundary |
|---|---|---|
| S0 supplies total open wiring presentations | Supported within implemented finite signature | malformed incidence refusals; category/coherence controls; `then`/`tensor` survive before a separate observer budget refusal |
| Successful canonical observation is alpha/declaration invariant | Supported on named and brute-small controls | exact WL-plus-residual form; multiplicity/self-loop retention; no claim of total observation for arbitrary graphs |
| Exact resistor black-boxing is compositional | Supported on identity, series, tensor, splitter–parallel–merger, bridge cuts, cycles, and finite chains | exact rational relation; finite tests, not a universal formal proof |
| Sparse MNA agrees with exact/analytic controls | Supported within declared tolerance | single/series/parallel/bridge/cycle and rational signed-drive grid; separate KCL/V/power/relation gates |
| Floating syntax and exact semantics imply a unique grounded solve | Refuted | exact floating relation succeeds while the driven MNA evaluator refuses |
| A presentation digest is an alpha-canonical cache key | Refuted | it is intentionally declaration-order-sensitive and prevents silent model-tuple permutation |
| The practical canonical observer belongs in topology/model identity | Refuted | resource policy is safe but currently misplaced in the combined subject; move it to analysis/execution policy |
| E1 establishes AC/RLC, hardware, or port-Hamiltonian semantics | Refuted | finite positive ideal resistors and one DC experiment only |

### Verification at exit

```text
focused structure/circuit/runtime/registry/P0: 90 passed
python -m pytest -q -rs: 1328 passed, 51 skipped, 1 xfailed
pytest -q -rs:           1328 passed, 51 skipped, 1 xfailed
python -m compileall -q smartchem experiments tests: passed
git diff --check: passed
```

The skips are the inherited absent-PySCF or explicit slow-test groups. The strict xfail is
the preserved closed-reaction parallel-interchange counterexample. Separately tasked
construction, semantics, and hostile acceptance bearings returned `SHIP`; code, exact
controls, retained counterexamples, and lifecycle artifacts—not report count—support the
claims.

The final cited calculation is run `4ae82cdc60464cc7be231ba2015bdfa1`,
`COMPLETE`, with all six obligations and all three output identities retained. No
calculation is in progress.

### Compact-resume cut

Resume from `CAMPAIGN_HANDOFF_2026-07-27.md`. The next category work is not “more category
terminology.” It is explicit structure-isomorphism/model-reindex witnesses, observer-policy
separation, `StructureIR v2` plus semantic-functor law harnesses, then AC/RLC. The best
orthogonal domain control is an open chemical Petri net with distinct stoichiometric,
mass-action, and stochastic semantics. Water dispersive validation, traffic, remaining
optimizer slices, and empirical survival remain separate evidence/model programs.
