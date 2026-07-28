# Research round: bounded StructureIR adapter — 2026-07-28

## Selected goal and ordinary-cause check

The inherited short-term list contained maintenance gates only: keep the E2 receipt and
refusal language frozen, keep all nine executors green, preserve exact output contracts,
and keep raw journals write-once. The live tree was clean at pushed commit `ae60a25`;
`main == origin/main`; no SmartChem calculation or benchmark process was active. The only
SmartChem process started in this round was the test suite.

The best-shot midterm was the deliberate `StructureIR` adapter because S0, E1, and E2
already supplied a topology kernel and two concrete semantic consumers. W2 dispersive
water, traffic shocks, empirical survival, and port-Hamiltonian work all require wider new
domain semantics or unavailable data authority.

## Unknown and rival designs

The latent object was the smallest useful category-theoretic migration that would not
silently rewrite current subjects or models.

| Candidate | Result |
|---|---|
| Put the raw `OpenDiagram` inside `StructureIR` | Refuted: raw values retain declaration order for model alignment and are not quotient values. |
| Treat canonicalization as a total functor | Refuted: S0 operations are total, but exact canonical observation has an explicit factorial budget refusal. |
| Infer model-edge transport from canonical topology | Refuted: graph automorphisms make occurrence identity non-unique; E1/E2 correctly retain presentation digests and explicit bindings. |
| One general SmartChem structure category | Refuted in this slice: chemistry scheduling lacks parallel interchange, and seven executors have no S0 electrical subject. |
| Versioned quotient value plus presentation witness and plan attachment | Selected: it preserves the exact distinctions while creating a useful migration seam. |

Three Codex workers independently audited the category, API/digest migration, and roadmap.
They shared the same repository and model family, so their agreement is reasoner diversity,
not independent experimental evidence. The main thread re-read the live code, reproduced
the baseline, selected between their conflicting storage proposals, implemented the slice,
and reran the decisive probes.

## Implemented dependency cut

`smartchem/structure_ir.py` adds:

- typed canonical `StructureIREdge` and versioned `StructureIR`;
- exact canonical encode/decode and a normalized S0 presentation for quotient operations;
- resource-bounded `then`, `tensor`, identity, and braid;
- `StructureAdapterWitness`, which binds one source-presentation digest, observation
  budget, outcome, and successful StructureIR digest;
- `StructureAttachment`, whose status is `OBSERVED`, `REFUSED`, or `NOT_APPLICABLE`;
- exact subject-derived attachment construction and revalidation.

`CandidatePlan` now carries the attachment as a compared/digestible field. Construction
derives or checks the exact attachment after closed-registry subject extraction. Execution
rederives it before runner dispatch and before any journal exists. All nine plan types are
therefore bound to the adapter schema: E1/E2 receive S0 observations or explicit budget
refusals; the other seven explicitly record non-applicability.

A circuit plan with a `REFUSED` attachment may still be approved so the existing runtime
can create its durable zero-engine-call refusal. That approval authorizes no canonical
StructureIR and no calculation; it preserves refusal as an outcome rather than converting
resource exhaustion into a missing record.

No existing subject class, output contract, registry descriptor, executor ID, `PhysicalIR`
record, E1/E2 model binding, or raw run receipt was rewritten.

## Category audit

### Disclosed within the implementation boundary

The intended S0 quotient has:

- objects: finite ordered electrical interfaces;
- morphisms: finite typed open undirected multigraphs modulo local names and declaration
  order;
- composition: boundary gluing;
- monoidal product: disjoint union with ordered boundary concatenation;
- unit: empty interface;
- symmetry: braid.

The adapter is a representation isomorphism between successful undecorated
`CanonicalDiagram` observations and `StructureIR`. Observation from raw presentations is a
partial runtime operation because of the declared resource budget. The implementation
tests identity, associativity, tensor laws, interchange, symmetry, and naturality on finite
constructed controls; this is not a formal proof for every finite diagram.

### Explicitly not disclosed

- a universal category across all nine domains;
- a functor from raw presentation equality;
- automatic transport of R/L/C/resistance parameters;
- a natural transformation between domain models;
- an AC semantic functor, because `ComplexBoundaryRelation` lacks composition/tensor;
- port-Hamiltonian, traced, dagger, compact-closed, causal, or dynamic-state structure;
- a general circuit, device, multiphysics, or scientific-validation claim.

## Calculation and verification ledger

No new scientific calculation was started. Existing calculation states remain:

- E2 damped control: terminal `COMPLETE`;
- E2 exact lossless series-LC control: terminal `REFUSED` before an engine call;
- heuristic chemistry smoke: terminal with incomplete coverage;
- old cold optional benchmark PID `151446`: terminal-unclassified, with no journal or
  durable stdout;
- no live SmartChem calculation at the round boundary.

The migration identity probe instantiated existing E1/E2 subjects and plans without
executing either engine. Exact identities and results are frozen in
`experiments/RESULTS_structure_ir_adapter.md`.

Verification:

```text
focused StructureIR/S0/P0/registry/E1/E2: 90 passed in 2.05s
python -m pytest: 1476 passed, 14 skipped, 1 xfailed in 179.25s
console pytest: 1476 passed, 14 skipped, 1 xfailed in 182.71s
Ruff on the four touched Python files: passed
```

The repository-wide optional real-oracle tests remain skipped unless `--runslow` is
provided. This architectural slice does not create new empirical evidence.

## Claim ledger

| ID | Claim | Status | Evidence | Falsifier / boundary | Next lamp |
|---|---|---|---|---|---|
| SIR-1 | Successful S0 canonical observations have an exact versioned StructureIR representation. | Disclosed for the implemented finite records | encode/decode and normalized round trips | differing decoded canonical form | mutation/property controls on larger generated families |
| SIR-2 | The adapter preserves the tested S0 symmetric-monoidal laws. | Observed on finite controls | identity/associativity/tensor/interchange/braid/naturality tests | generated counterexample | randomized or exhaustive bounded graph generator |
| SIR-3 | Raw presentation identity remains distinct from quotient structure. | Disclosed by construction and controls | same StructureIR, distinct presentation witnesses | witness accepts the wrong presentation | retain exact digest check |
| SIR-4 | All nine plan types bind the adapter schema without changing their output contracts or registry. | Corroborated by construction and full regression | exact registry and nine contract digests; all vertical tests | changed digest/observable inventory or admitted forged attachment | CI on the pushed commit |
| SIR-5 | StructureIR is a general cross-domain physics category. | Refuted for this slice | seven subjects are explicitly `NOT_APPLICABLE`; reaction tensor counterexample remains | new verified domain-specific adapter family | domain-indexed categories, not relabeling |
| SIR-6 | E2 black-boxing is already a symmetric-monoidal functor. | UNVERIFIED / currently unexpressible | exact object-level relation exists | missing complex relation composition/tensor | implement exact `Q(i)` LinRel operations and preservation tests |

## Roadmap decomposition

### Short term

1. Freeze this receipt, schema strings, registry digest, all nine output-contract digests,
   and the exact plan-admission refusal.
2. Add `ComplexBoundaryRelation.identity`, composition, and tensor with exact elimination
   controls; test E2 black-box preservation separately from driven solver success.
3. Extend generated StructureIR law attacks within explicit canonicalization budgets.

### Mid term

1. Introduce a circuit-local decorated `ModelIR` with explicit presentation permutation
   witnesses; do not infer parameter transport from undecorated topology.
2. State and test DC and AC black-box functors into rational/complex linear relations.
3. In parallel, build W2 as the next scientific vertical: declared dispersive PDE,
   boundary conditions, support, branch/scattering outputs, N/2N/4N convergence, and an
   independent verifier. Keep it `STRUCTURAL_TOY` until measured regime-matched evidence.
4. Follow with traffic kinematic waves under conservation, weak/shock, entropy, closure,
   calibration, and held-out trajectory gates.
5. Admit optimizer changes one Class-A transform at a time with exact output/provenance
   equality and separate cold/warm timing.

Empirical D2b remains behind independent data authority, censoring and competing-risk
semantics, uncertainty validation, and a locked external set.

### Long term

1. Use a domain-indexed family of structure categories and verified adapters; do not force
   chemistry, fields, circuits, and survival into one untyped graph category.
2. Separate `StructureIR`, domain `ModelIR`, claim-bearing `EvidenceIR`, and a
   feedback-preserving `ExecutionDAG`.
3. Add model-chain planning only after adapter composition, applicability, and output
   preservation laws are executable.
4. Add general validity/refinement/checkpoint/evidence transitions.
5. Introduce dynamic state and an operational effort/flow power pairing before any
   port-Hamiltonian composition claim.
6. Admit distributed/full-wave, electrothermal, mechanics, kinetics, particle/radiation,
   and relativistic extensions only behind domain-specific regime and validation gates.
7. Build the conversational surface last, exposing rather than impersonating plans,
   approvals, evidence, results, refusals, and uncertainty.

## Compact-resume cut

Publication gate: commit the exact verified scope, push `main`, confirm the remote commit
and CI, then resume from that pushed state rather than a `/tmp` artifact. Read:

1. `RESEARCH_ROUND_STRUCTURE_IR_2026-07-28.md`;
2. `experiments/RESULTS_structure_ir_adapter.md`;
3. `smartchem/structure_ir.py`;
4. `ROADMAP_2026-07-27.md`;
5. live git/remote/test/calculation state.

The next bounded category task is exact complex linear-relation composition/tensor plus E2
black-box preservation. The next scientific vertical is W2 dispersive water. No SmartChem
calculation remains in progress.
