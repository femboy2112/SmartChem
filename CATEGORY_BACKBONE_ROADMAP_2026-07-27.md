# Category backbone roadmap — 2026-07-27, open-semantics checkpoint

## Decision

SmartChem should use category theory as typed composition glue, not as the numerical or
physical content of every domain. The most useful architecture is therefore not one giant
“category of physics.” It is:

1. a small typed language of open structure;
2. domain models indexed by that structure;
3. one or more domain-specific semantic functors into the mathematical category best
   suited to the problem;
4. evidence and execution layers that remain outside structural equality.

This round implements the first narrow instance:

- `smartchem.open_diagram` supplies total finite presentation-level composition and tensor;
- a separate budgeted observer supplies exact alpha-invariant canonical forms when its
  declared search succeeds;
- `smartchem.circuit` assigns exact positive-rational resistor data and maps a diagram to a
  boundary linear relation over potentials and inward currents;
- a separate sparse MNA evaluator computes one grounded, voltage-driven numerical point;
- `smartchem.resistive_dc` carries that control through the closed
  source/plan/approval/journal/certificate runtime.

The result is a real load-bearing slice, not a general multiphysics category, a universal
proof of the category/functor laws, an AC/RLC solver, or a port-Hamiltonian implementation.

## What changed from the inherited design

Two inherited proposals were wrong and are now explicitly superseded.

First, `then` and `tensor` must not canonicalize. A fixed factorial search budget would make
those operations partial: two individually observable symmetric fragments can be tensored
into a diagram whose exact canonical observation exceeds the same budget. The corrected
API keeps presentation operations total and makes canonical observation separately
resource-bounded.

Second, resistance kind/value must not be part of structural identity. The implemented
structure contains electrical node kinds and two-terminal component slots only. Exact
resistance values belong to `ResistiveDCModel`; drive, reference, and tolerance belong to
`DCSolveSpec`.

The current separation is:

| Layer | Current owner | Semantic role |
|---|---|---|
| structural presentation | `OpenDiagram` | ordered boundaries, junction incidence, two-terminal slots, total gluing/disjoint union |
| quotient observer | `canonicalize` | exact alpha-invariant observation or named budget refusal |
| model decoration | `ResistiveDCModel` | exact positive-rational resistance aligned to structural edge slots |
| exact semantics | `BoundaryLinearRelation` | relation on ordered boundary potentials and inward currents |
| experiment | `DCSolveSpec` | drive polarity/voltage, reference, numerical tolerance |
| numerical evaluator | `solve_resistive_dc` | one sparse MNA point with retained KCL, constraint, power, and relation gates |
| evidence/execution | `PhysicalIR`, plan, approval, journal, certificate | claim boundary, authority, artifacts, resource limits, terminal state |

One remaining placement debt is visible rather than hidden:
`ResistiveDCSubject.canonicalization_budget` is safe and approval-bound, but it is observer
resource policy, not topology, constitutive data, or experiment physics. Move it into a
future explicit analysis/execution specification.

## The actual categorical core

### Closed chemistry remains useful but is not parallel

`Molecule`, `Config`, and `Reaction` remain a useful category of closed conserving
sequential histories. Construction makes atom/charge violations unrepresentable, and
sequential composition is genuinely associative.

`Reaction.tensor` is not a parallel tensor. It is a left-first schedule and fails strict
interchange. Keeping that counterexample and deprecating the misleading name were correct.
Do not retrofit open-system meaning into this class.

### S0 is a symmetric-monoidal presentation, not yet a full hypergraph API

For compatible interfaces, `OpenDiagram.then` glues ordered boundary nodes and
`OpenDiagram.tensor` takes disjoint union. Identity and braid diagrams are explicit.
Finite tests cover identities, associativity, tensor units/associativity, interchange,
braid involution/naturality, and both hexagons.

The mathematical quotient by internal names is total. The practical canonical observer is
not: it performs relabeling-equivariant color refinement followed by exact residual
permutation search and names a budget refusal. Passing finite tests is evidence for the
implementation, not a formal theorem over every finite graph.

The present constructor also requires at least two incidences per retained junction. That
is closed under the implemented operations and sufficient for the resistor control, but it
omits nullary/unary junctions and therefore should not yet be advertised as the full free
hypergraph category of typed cospans. Add Frobenius unit/counit structure only when a domain
actually needs it and its semantics are specified.

### E0 is relation-valued because functions and scalars are too weak

The exact electrical semantic object is a homogeneous linear relation in the ordered
coordinates

```text
(V_dom, V_cod, I_inward_dom, I_inward_cod).
```

Serial composition shares interface potentials, imposes
`I_left + I_right = 0`, and existentially eliminates the glued variables. Tensor is direct
product. This handles singular or floating passive networks honestly; an input impedance
or driven solution is only a derived observation after additional boundary choices.

This is why the old scalar-impedance idea could not be made monoidal. Series addition and
parallel reduction do not obey the interchange equation required of one scalar-valued
strict monoidal semantics.

The implementation uses exact rational RREF/elimination for the relation and a separate
binary64 sparse solve for one experiment. Bridge, cycle, splitter–tensor–merger parallel,
floating, and finite rational controls test that separation. They do not prove a theorem
for all networks.

## Is the category theory now maximally useful?

No. It is finally useful, but it is still a first slice.

### What is now right

- Structural composition is executable and tested rather than asserted in prose.
- Resource-bounded equality no longer contaminates closure of composition.
- Internal IDs are construction-local; successful canonical observation is alpha-invariant.
- Parallel multiplicity and self-loops survive canonicalization.
- Constitutive parameters, experiment choices, evidence, and runtime authority are
  separated.
- Electrical semantics lands in linear relations, which can represent nonfunctional and
  singular boundary behavior.
- Exact and numerical interpreters are distinct, so MNA can be checked against a stronger
  boundary invariant.
- The bridge control prevents a hidden series/parallel dispatcher from masquerading as a
  topology-generic solver.
- Refusal remains first-class: a floating exact relation may be valid while a particular
  grounded evaluator refuses.

### What is still wrong or inefficient

- `ResistiveDCModel` is bound to an order-sensitive presentation digest. This is safe, but
  an alpha-renamed/reordered diagram requires explicit model rebinding. It is not yet an
  ergonomic model transport or a canonical structural cache key.
- Dense `Fraction` RREF is correctness-first and can grow badly in time and coefficient
  size. It is not the eventual large-network exact engine.
- Exact canonicalization has factorial worst cases. It should be used at equality/cache
  boundaries, not inserted into every construction or solve.
- `PhysicalIR` still contains legacy free-string structural records. The typed diagram is
  retained in the subject, but there is no general `StructureIR v2` adapter yet.
- There is no explicit `SemanticFunctor` protocol or law witness connecting syntax,
  exact semantics, and approximate evaluators.
- There is no model-reindexing witness under structural isomorphism.
- Tests establish strong finite controls, not universal laws or machine-checked proofs.
- The current node-arity restriction means “hypergraph category” would overstate the API.
- Category theory is still absent from the open chemical, kinetic, stochastic, and PDE
  domains where it could provide more reuse.

## The more load-bearing design

### 1. Treat models as an indexed family over structures

For each structure `S`, let `Model(S)` be the allowed domain models on its component slots.
An isomorphism `u: S ≅ S'` must carry an explicit reindexing map
`u_*: Model(S) -> Model(S')`.

In code, the next seam should contain:

```text
StructurePresentation
StructureIsomorphismWitness
ModelDecoration[Structure]
reindex_model(witness, model)
DecoratedCanonicalIdentity
```

This keeps topology and parameters separate while making alpha-renaming/reordering usable
instead of merely safe-to-refuse. A decorated canonical identity can then key result
caches, while the raw presentation digest continues to defend declaration-order tuples.

Categorically, this is closer to an indexed category/fibration of models over structures
than to one record that owns everything.

### 2. Make semantic targets domain-specific

Do not force every interpreter into matrices, scalar costs, or port-Hamiltonian form.

| Domain | Structural glue | Useful internal mathematics / semantic target |
|---|---|---|
| passive DC circuits | typed open wiring | exact rational linear relations; sparse MNA as an evaluator |
| AC/RLC circuits | same wiring plus typed element model | complex linear relations, positive-real/passivity predicates, sparse complex MNA |
| dynamical energy systems | typed effort/flow ports | Dirac/Lagrangian relations and port-Hamiltonian state dynamics, only after a power pairing is proved |
| chemical reaction networks | open species interfaces | stoichiometric matrices, open Petri nets, mass-action ODEs, stochastic CTMCs, thermodynamic constraints |
| water/traffic conservation laws | boundary state/flux interfaces | finite-volume/PDE relations, entropy and shock conditions, convergence/error records |
| Ising/lattice systems | graph boundaries | transfer operators, tensor-network or exact finite-state semantics where justified |
| survival/reliability | cohort/state interfaces | stochastic kernels, likelihoods, censoring/competing-risk models, calibration evidence |
| quantum models | typed state/process interfaces | linear maps or completely positive maps only where the physical interpretation supports them |

Category theory supplies composition and translation laws. The objects inside each box
should use the best mathematics for that domain.

### 3. Represent interpreters and approximations explicitly

A future protocol should distinguish:

```text
exact_semantics: DecoratedDiagram -> ExactSemanticObject
evaluate: ExactSemanticObject × Experiment -> NumericalWitness
verify: ExactSemanticObject × NumericalWitness -> Diagnostic
```

Exact-to-numerical comparisons are then natural-transformation/refinement candidates rather
than claims that floating output is the exact functor. For discretized PDEs, a refinement
map should carry mesh identity and an error/convergence obligation; it need not be strictly
functorial if the honest structure is only lax or approximate.

### 4. Use composition to improve efficiency

The useful performance consequences are concrete:

- cache canonical decorated subdiagrams, not raw user IDs;
- reuse symbolic sparse ordering/factorization metadata when topology and grounding are
  unchanged;
- compose cached boundary Schur complements/relations rather than re-solving unchanged
  interiors;
- retain the construction DAG as an incremental Merkle identity, invoking expensive graph
  canonicalization only when cross-presentation equality is needed;
- use exact isomorphism witnesses to transport model tuples and cached results;
- replace dense rational RREF, after profiling, with sparse fraction-free elimination or
  modular reconstruction while preserving exact outputs;
- express execution cost/resource estimates as a separate lax monoidal accounting functor,
  never as physical semantics.

These optimizations are authorized only when the output contract and exact/numerical
verification remain unchanged.

### 5. Use categorical laws as metamorphic tests

Every domain functor should inherit generated tests:

- semantics of identity equals semantic identity;
- whole-diagram semantics equals semantics composed at a cut;
- tensor/disjoint union maps to the target product;
- alpha-isomorphic decorated diagrams agree after model reindexing;
- exact and numerical interpreters commute within declared error gates;
- a semantics-preserving compiler pass leaves every requested observable unchanged.

This is one of the highest-value uses of category theory here: it manufactures adversarial
test oracles for wiring, sign, ordering, conservation, and optimization bugs.

## Roadmap

### Short term

1. Keep the completed S0/E0/E1 controls and their counterexample boundaries in CI.
2. Move canonicalization budget from `ResistiveDCSubject` to an explicit analysis/execution
   policy without changing completed plan semantics silently.
3. Add `StructureIsomorphismWitness` and explicit `reindex_model`; test resistance
   transport under edge/junction declaration permutations.
4. Add generated small decorated-diagram law tests with reproducible seeds and preserved
   minimal counterexamples.
5. Benchmark canonicalization candidates, dense rational elimination, coefficient growth,
   sparse MNA assembly/factorization, and cache hit boundaries before optimizing.
6. Specify `StructureIR v2`, `ModelDecoration`, and `SemanticFunctor` protocols beside the
   current compiled verticals; do not rewrite legacy `PhysicalIR` in place.

### Mid term

1. **E2 AC/RLC:** reuse the open wiring and sparse stamping path; add complex boundary
   relations, branch complex power, positive-frequency assumptions, damped resonance, and
   explicit singular lossless-resonance refusal.
2. **StructureIR v2 adapter:** compile one existing typed subject through the new layered
   structure/model/evidence/execution records with exact digest and output-contract
   migration tests.
3. **Open chemical-network control:** model one finite open Petri net and provide distinct
   stoichiometric, deterministic mass-action, and stochastic semantics without weakening
   the closed `Reaction` API.
4. **Composable exact/numerical verification:** make exact relation, sparse evaluator, and
   diagnostic checker explicit interpreter layers and add reusable functor-law harnesses.
5. **Water or traffic boundary relation:** choose typed conserved state/flux ports and keep
   finite-volume closure, entropy, calibration, and validation mathematics inside the
   domain model.

### Long term

- use a double category/equipment when horizontal open-system composition and vertical
  refinement/model maps both become first-class;
- add port-Hamiltonian/Dirac structure only for dynamic domains with explicit state,
  Hamiltonian, effort/flow pairing, and power-conserving interconnection;
- support compositional sensitivity/adjoint information for calibration and inverse design;
- make uncertainty/error transport explicit rather than attaching one scalar “uncertainty”
  to arbitrary semantic objects;
- add proof-producing or proof-assistant verification for the small structural kernel if it
  becomes security- or science-critical;
- keep evidence applicability and execution authority separate even when structural and
  semantic reuse becomes broad.

## Dominance and falsifiers

The new backbone dominates the old “parallel history” framing only while:

- presentation composition remains total when canonical observation refuses;
- alpha-renaming and declaration reorderings preserve successful canonical observations;
- model transport is explicit and cannot silently permute parameters;
- whole-network exact semantics agrees with cutwise relational composition;
- numerical evaluators retain dimension-separated residuals and source-inclusive power;
- bridges/cycles use the same topology-generic path;
- floating/singular cases refuse only at the layer that actually requires uniqueness;
- existing chemistry and compiled verticals do not regress.

A violation is a counterexample to preserve, not a reason to weaken equality, regularize a
singularity silently, or rename a schedule “tensor.”

## Primary mathematical bearings

- Baez and Fong, [A Compositional Framework for Passive Linear
  Networks](https://arxiv.org/abs/1504.05625): passive circuits black-box to boundary
  potential/current linear relations.
- Baez and Courser, [Structured Cospans](https://arxiv.org/abs/1911.04630): typed open
  systems composed by structured cospans.
- Baez, Courser, and Vasilakopoulou,
  [Structured versus Decorated Cospans](https://arxiv.org/abs/2101.09363): the distinction
  between structural and decorated open-system constructions.
- Baez and Master, [Open Petri Nets](https://arxiv.org/abs/1808.05415): open reaction
  networks, gluing, and distinct operational/reachability semantics.

These papers guide the architecture. They do not prove SmartChem's Python implementation;
that evidence remains the code, exact controls, hostile tests, and explicit limitations.
