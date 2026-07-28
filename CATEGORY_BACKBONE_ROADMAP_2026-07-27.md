# Category backbone roadmap — 2026-07-27

## Status and decision

**The finite typed open-diagram S0 kernel, bounded StructureIR adapter, and narrow E1/E2
interpreters are now implemented; no general circuit executor or cross-domain category is.**
`smartchem/open_diagram.py` supplies topology-only presentations, total composition/tensor,
and a separate budgeted exact canonical observer. Generated and adversarial finite controls
support the implemented coherence claims; they are not a formal proof of the laws for all
finite graphs. The separate E1 stack supplies finite positive ideal-resistor DC relations
and one declared drive/reference. The separate E2 stack supplies fixed-positive-frequency
ideal passive-RLC relations and refuses exact lossless singular resonance. These remain
dependency cuts, not evidence that a general multiphysics category or general circuit
vertical exists. The manufactured
continuous-water runtime remains a domain-semantic rung and is not silently reinterpreted
through the new wiring kernel.

The repository has a load-bearing category of *closed sequential chemical histories*.
It does not have a true parallel morphism product: `Reaction.scheduled_product`/`tensor`
is intentionally a left-first linearisation, and the existing strict expected failure for
interchange is correct.  The next backbone must therefore be introduced beside that API,
not by relabelling it.

The completed structural target is a finite typed open-diagram syntax with total
composition and a budgeted canonical observer. Two semantic targets are now complete:
a passive lumped resistive-DC interpretation and a positive-frequency passive-RLC
interpretation, each with an independent implementation verifier. Together they establish
two topology-generic controls; neither is a promise of a universal physics language.
`smartchem/structure_ir.py` now gives successful undecorated S0 canonical observations a
versioned quotient value, retains raw-presentation identity in a separate adapter witness,
and binds every new plan to `OBSERVED`, `REFUSED`, or `NOT_APPLICABLE` before dispatch.
Canonical topology does not infer E1/E2 declaration-index model transport.

## Diagnosis

### What is load-bearing today

| Asset | Why it is load-bearing | Boundary that must remain visible |
|---|---|---|
| `Molecule`, `Config`, `Reaction` | `Reaction` makes atom/charge-violating closed histories unconstructible; path concatenation supplies genuine sequential associativity. | It has no open ports, node equations, rates, fields, or parallel interchange. |
| Frozen plan/approval/run/certificate seam | Approval binds a typed request, model, calculation identity, output contract, and implementation digest. | It is an API authority boundary, not hostile-process security or scientific validation. |
| Closed runtime registry | A known executable owns a known typed subject and exact output contract. | A new vertical must be registered and preflighted; a capability object must not self-authorize. |
| Exact finite Ising/lattice-gas control | It demonstrates that a cross-domain map can retain every finite state and distinct referents. | It does not generalize to arbitrary graph dynamics or material identity. |
| Water finite-section v2 | It retains all manufactured samples and compatibility gates while refusing a continuum claim. | It does not establish steady momentum, critical regularity, convergence, or measurement. |

### What is decorative or insufficient as a kernel

| Existing surface | Why it cannot be the new kernel |
|---|---|
| `Reaction.tensor` | It serializes independent histories and fails interchange by construction. |
| Scalar impedance series/parallel helpers | `tests/test_network.py` already falsifies scalar interchange; impedance is not the semantic object of an arbitrary open network. |
| `program.Port`, `Component`, `Connection` | They are useful IR records, but their free-string fields and historical lack of global reference ownership do not define topology or constitutive law. |
| A graph of opaque chemical labels | It can distinguish encodings but cannot enforce KCL, port compatibility, reference nodes, or a constitutive equation. |
| A converged grid solve | It is evidence about one finite numerical problem only; it does not establish a continuous solution or categorical law. |

The key distinction is that **syntax, topology, constitutive model, evidence, and execution
authority must not be stored in one record merely because all of them have IDs**.

## The target separation

The following separation should be explicit in code and in plan digests.  It prevents a
topology edit from silently becoming a model change, or a finite numerical outcome from
being mistaken for evidence of a continuum assertion.

| Layer | Owns | Must not own |
|---|---|---|
| `StructureIR` | Typed ports, junctions, boundary interfaces, component incidence, canonical topology, diagram composition/tensor. | Constitutive parameters' physical validity, source authority, solver tolerances, evidence status. |
| `ModelIR` | Equations, parameter values/units, regime assumptions, domain/refusal conditions, conserved quantities, named postconditions. | Internal topology IDs as semantic labels, output reduction, scientific approval. |
| `EvidenceIR` | Claim scope, transport/assembly evidence, validation gaps, casualties, calibration provenance, falsifiers. | A solver result as automatic validation, a model patch as an approved execution. |
| `ExecutionDAG` | Concrete engine calls, retained intermediate artifacts, dependencies, calculation identities, resource ceilings, exact output inventory. | A new physics interpretation, unapproved output loss, hidden optimization. |

`PhysicalIR` can eventually contain or reference these layers, but it is not the canonical
topology store. The completed bounded adapter places the precise StructureIR quotient value
beside existing `PhysicalIR`, preserves all current constructors/compiled verticals, and
binds the attachment only after closed-registry subject validation. The next cut is a
circuit-local decorated `ModelIR`, not a broad `PhysicalIR` rewrite.

## Exact open-diagram kernel

**Implementation state:** S0 is complete in `smartchem/open_diagram.py` and
`tests/test_open_diagram.py`. The public shape below remains intentionally electrical and
two-terminal, with no constitutive value in structural identity. Exact observation may
refuse above its explicit factorial candidate budget; `then` and `tensor` remain total and
never invoke that observer.

### Minimal public signature

Place this in a new `smartchem/open_diagram.py`; do not modify `category.py` for the first
slice.

```python
class PortKind(Enum):
    ELECTRICAL_NODE = "electrical-node"

@dataclass(frozen=True)
class Interface:
    ports: tuple[PortKind, ...]       # position is boundary identity

class BoundarySide(Enum):
    INPUT = "input"
    OUTPUT = "output"

@dataclass(frozen=True)
class BoundaryRef:
    side: BoundarySide
    index: int

class PassiveKind(Enum):
    RESISTOR = "R"
    INDUCTOR = "L"
    CAPACITOR = "C"

@dataclass(frozen=True)
class PassiveElement:
    element_id: str                   # construction-local only
    kind: PassiveKind
    value_si: float                   # finite, strictly positive

@dataclass(frozen=True)
class ElementPortRef:
    element_id: str
    terminal: Literal["a", "b"]

EndpointRef = BoundaryRef | ElementPortRef

@dataclass(frozen=True)
class Junction:
    junction_id: str                  # construction-local only
    kind: PortKind
    endpoints: tuple[EndpointRef, ...]

class OpenDiagram:
    @classmethod
    def build(cls, dom, cod, elements, junctions) -> "OpenDiagram": ...
    def then(self, other: "OpenDiagram") -> "OpenDiagram": ...
    def tensor(self, other: "OpenDiagram") -> "OpenDiagram": ...
```

Expose `identity(interface)`, `unit_interface()`, and `braid(a, b)` in this module's
namespace.  Construction should be smart-constructor-only (an internal token is adequate
for normal accidental-bypass protection).  A hostile Python caller can still subvert
objects; that is outside the local-library threat model already stated for the program
seam.

### Constructor invariants

At `OpenDiagram.build`:

1. Element and junction IDs are nonempty and unique in their separate local namespaces.
2. Each supported passive element has exactly the inferred electrical terminals `a` and
   `b`, and a finite positive SI parameter.
3. Every referenced element and terminal exists; every interface boundary index is in
   range; every element terminal and every boundary port occurs **exactly once** across
   all junctions.
4. A junction contains at least two endpoints and all its endpoints have its declared
   `PortKind`.  This rejects mixed-physics connections before a solver is involved.
5. No local ID is semantic.  A user who needs a stable scientific probe identity must
   introduce an explicit typed probe/output contract in a later slice, rather than
   relying on an internal graph spelling.

An internally closed connected component is not a syntactic orphan merely because it has
no boundary port.  It may be a legitimate diagram fragment.  A *driven circuit analysis*
must later refuse it if it floats relative to the selected reference.  Keeping these two
failures distinct is important.

### Canonical equality and alpha-renaming

The stored value must discard raw IDs and retain only:

- domain/codomain interface types and order;
- canonical numbered junction nodes;
- ordered maps from input/output boundary positions to nodes;
- sorted undirected passive-edge records
  `(kind, value_si, min(node_a,node_b), max(node_a,node_b))`.

For passive two-terminal elements, `a`/`b` has no physical polarity and is normalized as
an undirected edge.  Do not reuse this rule for a future directed/non-passive component.

Canonicalize as follows:

1. Give each junction an initial color consisting of `PortKind` plus all attached fixed
   boundary markers, such as `(input, 0)` and `(output, 1)`.
2. Run color refinement using the multiset of incident
   `(element kind, exact parameter, neighbor color)` records.
3. Enumerate only permutations within equal final-color cells, assign node labels in
   color order, and take the lexicographically least boundary-map/edge tuple.
4. Fix a candidate budget.  If the product of cell factorials exceeds it, raise a named
   canonicalization-budget refusal rather than returning an ID-dependent value.

Refinement is relabeling-equivariant, so restricting permutations to equal-color cells is
exact once the color sequence is included in the canonical prefix.  The residual search
is factorial for highly symmetric networks; that is a deliberately explicit finite
boundary, not a reason to quietly make equality approximate.

### Composition and laws

For `f : A -> B` and `g : B -> C`, require exact `f.cod == g.dom`, take a disjoint union,
and union-find identify output node `i` of `f` with input node `i` of `g`.  Retain the
input boundary of `f` and output boundary of `g`, then re-canonicalize.  Tensor is
disjoint union with interface concatenation and re-canonicalization.  `identity(A)` has
one junction per port, joining its input and output occurrences.  `braid(A,B)` preserves
wires and reorders the output attachment list.

These algorithms, not an assertion in a docstring, are the reason to expect:

\[
\operatorname{id};f=f=f;\operatorname{id},\qquad
(f;g);h=f;(g;h),\qquad
(f;g)\otimes(h;k)=(f\otimes h);(g\otimes k).
\]

The laws remain claims about every constructible finite diagram within the canonicalization
budget, not a formal proof about arbitrary Python values.

## Semantic ladder: DC first, then AC/RLC

### Why not start with scalar impedance

The semantic target is a boundary **linear relation** between terminal potentials and
currents.  Composing diagrams glues potentials and cancels the two boundary currents;
tensor takes a direct product.  This allows singular and floating cases to retain an
honest relation.  An input impedance is only a derived number after reference, drive, and
termination choices are declared.

That distinction is required by the existing scalar interchange counterexample.  A mapping
from categorical composition to scalar series addition and tensor to scalar parallel
reduction would demand an interchange equality that representative resistors already
violate.

### Stage E1: resistive DC MNA — completed

The shipped `smartchem/circuit.py` was added after the topology kernel passed its generated
laws. It supports positive resistors and a declared ideal-voltage boundary drive plus a
declared reference node. For each resistor between nodes `a,b`, it stamps conductance
`g=1/R` into sparse nodal matrix `G`:

\[
G_{aa}{+}=g,\quad G_{bb}{+}=g,\quad G_{ab}{-}=g,\quad G_{ba}{-}=g.
\]

With reference voltage removed and ideal source constraints collected in `B`, solve:

\[
\begin{bmatrix}G&B\\B^T&0\end{bmatrix}
\begin{bmatrix}v\\i_s\end{bmatrix}
=
\begin{bmatrix}0\\e\end{bmatrix}.
\]

Use sparse COO triplet assembly followed by CSC conversion and SciPy sparse solve.  Reject
any component not connected to the reference through passive/source constraints, rank
warnings, non-finite values, and scaled residual failure.  Check KCL and power balance;
each resistor must satisfy nonnegative absorbed real power.

Controls include one-resistor drive, series and parallel analytic cases, a five-edge bridge,
a cycle, nonidentity model-edge reindexing, seeded connected multigraphs, recursive nominal
record forgeries, and approved-input substitution. They compile through the same stamping
routine and a separate verifier independently derives the exact relation and physical
residuals. The durable receipt is
`experiments/RESULTS_compiled_resistive_dc.md`.

### Stage E2: positive-frequency passive RLC phasors — completed

Only after E1, admit finite `omega > 0` and the admittances

\[
y_R=1/R,\qquad y_L=1/(j\omega L),\qquad y_C=j\omega C.
\]

Use the same MNA assembly.  Return branch voltage/current/complex power and require:

\[
S_e=(V_a-V_b)\overline{y_e(V_a-V_b)},\qquad
\Re S_R\ge -\epsilon.
\]

Inductor/capacitor real power must be numerically zero at the declared tolerance; include
source absorbed power in the global complex-power residual.  A pure lossless resonant
subnetwork may be singular under an ideal drive.  Refusal is the required result, not a
numerical defect to be hidden by an arbitrary regularizer.

Controls: analytic series RLC, parallel RC, damped RLC resonance (reactive currents cancel
while resistor dissipation remains), and a deliberately singular undamped resonance.

The shipped E2 implementation is additive in `smartchem.rlc_ac_schema`,
`smartchem.rlc_ac_circuit`, `smartchem.rlc_ac`, and `smartchem.rlc_ac_verifier`. It retains
an exact `Q(i)` relation and exact driven-MNA rank before normalized sparse complex solving.
The direct verifier imports neither the production circuit interpreter nor executor. The
approved damped parallel `R=L=C=1`, `omega=1` fixture completes; an exact lossless series-LC
fixture refuses before an engine call and without regularization. The durable receipt is
`experiments/RESULTS_compiled_rlc_ac.md`. This is a finite ideal mathematical control, not
a general AC simulator, device, all-network theorem, or dynamic model.

## Continuous water as an open relation

The continuous-water milestone should not be shoehorned into a two-terminal resistor
diagram.  Its smallest honest open structure is a steady one-dimensional relation with
boundary variables such as discharge `q` and head `H` (plus declared geometry, bed, gravity,
and friction/model parameters).  A candidate structure is:

\[
q=bhU,\qquad H=z_b+h+\frac{U^2}{2g},
\]

with a declared steady momentum/friction equation supplying the spatial relation.  The
open semantic object contains boundary tuples `(q,H)` and retained interior state; serial
composition glues shared boundary discharge/head under a sign convention.  It is **not** a
claim that these two quantities exhaust free-surface, dispersive, turbulent, or
two-dimensional physics.

The current continuous reconstruction layer and any future solver must separately retain:

- the exact manufactured profile/forcing and boundary conditions;
- both the critical numerator and first-derivative regularity conditions rather than
  merely a sampled `Fr=1` crossing;
- discrete solutions at `N`, `2N`, and `4N` plus a declared norm and convergence ratios;
- a lossless-vs-friction comparison payload.  Disagreement is a model discrepancy to
  explain by the declared momentum/friction assumptions, not a verdict that either model
  is physically true;
- its residuals, regime predicates, grid identity, calculation specification, and every
  excluded physical effect.
- whether uncertainty is propagated or merely retained metadata, and a verifier path
  separate from the production reconstruction.

The existing finite v2 diagnostic remains an independent finite-sample screen.  It may
agree or disagree with the continuous model, but neither outcome upgrades a manufactured
test into measured validation.

## Dependency sequence

The scientific-validation ladder and the open-structure ladder are parallel after their
shared P0 prerequisite; continuous water does not depend on a circuit interpreter.

1. **P0 seam hardening — completed this round.** Global `PhysicalIR`
   ownership/reference/type checks, runtime-owned model/transform preflight, exact
   transform contract binding, guarded runner dispatch, and mutation tests now precede
   every journal and engine call.
2. **W1 manufactured continuous-water vertical — completed this round.** The typed
   regular-transcritical control retains 32/64/128-mesh fields, both refinement-pair
   convergence evidence, both critical compatibility conditions, metadata-only
   uncertainty, solver-independent direct verification, and a quantified finite-v2
   comparison at `STRUCTURAL_TOY`. It is a bounded cell-centred energy reconstruction,
   not a finite-volume/general stationary solver.
3. **S0 syntax only — completed.** Selectively ported `open_diagram.py` from remote
   `fdb906f`, retained total presentation operations and named
   canonicalization-budget refusal, and expanded the category-law harness over a
   deterministic generated structural family. No solver or physics claim was added.
4. **E1 resistive DC control — completed.** The older remote `fdb906f` attempt remains
   historical `NO-SHIP`; the shipped implementation instead uses shared immutable nominal
   records, separate production and direct-verifier computations, sparse MNA,
   topological-reference refusal, residual/passivity checks, complete outputs, and
   hostile common-mode/input-substitution controls.
5. **E2 AC/RLC control — completed.** Exact `Q(i)` relation/rank, RMS phasors, complete
   complex-MNA and power output, independent verification, damped resonance, and
   lossless singular refusal now pass through the ninth closed executor.
6. **`StructureIR` adapter — completed.** The versioned quotient value, separate
   presentation witness, typed budget-refusal/non-applicability states, plan/compiler
   binding, and pre-dispatch rederivation are implemented without changing any subject,
   registry descriptor, or output contract. Exact alpha/round-trip/law/model-binding/
   forgery controls and the all-nine regression pass.
7. **Complex linear-relation closure — next category milestone.** Add exact identity,
   composition, and tensor to E2's `ComplexBoundaryRelation`, then test RLC black-box
   preservation independently of whether a chosen drive admits a nonsingular MNA solve.
   Only after that should a circuit-local decorated `ModelIR` make a semantic-functor claim.

## Falsifiers and budgets

| Claim | Cheapest discriminating failure |
|---|---|
| Typed topology is real | Construct an unknown/duplicate terminal, mixed-kind junction, or unattached component port. |
| Equality is alpha-invariant | Rename every construction-local ID or reorder declarations and obtain a different canonical diagram. |
| Tensor is genuine | Generated associativity/unit/interchange counterexample. |
| Semantics is topology-generic | A bridge requires a `series`/`parallel` branch or cannot be stamped. |
| Passive solver is sound in scope | Material KCL residual, negative real resistor power, or failed global power balance. |
| Refusal path is honest | A floating or exact lossless-resonant circuit returns a finite authoritative result. |
| Continuous-water result is stronger than v2 in the right way | It lacks retained N/2N/4N records or claims continuum truth from a finite grid. |
| Existing behavior is preserved | Any chemistry/compiled-vertical regression or changed digest without an approved migration. |

The S0 implementation occupies 575 source lines plus its focused generated/adversarial
tests, inside the initial 500–700-line topology budget. E1 exceeded the initial sketch:
its schema, production relation/MNA, compiled lifecycle, and independent verifier occupy
about 2,590 source lines, with about 1,295 focused test lines. The added size is principally
the full-output lifecycle and genuinely separate verifier/hostile integrity gates; it is
recorded as complexity debt, not hidden as a small scalar circuit helper. E2 reused the
structural boundary but added another explicit schema, lifecycle, and independent verifier;
that duplication is visible complexity debt and motivates a bounded adapter rather than an
implicit abstraction. The bounded adapter now makes quotient structure, raw-presentation
identity, and plan authority explicit; it does not yet remove E1/E2 model-schema
duplication. The canonicalizer's candidate
cap must be measured and recorded; its worst case is factorial in symmetric node cells.
Sparse MNA storage is linear in edges/nodes before factorization, while solve cost is
topology-dependent and must be reported rather than predicted as universally linear.

## Dominance boundary

This program dominates the current false “parallel history” framing only if all of the
following hold: canonical open composition passes generated laws; bridge and cycle topology
compile through one sparse assembly path; solver residual/passivity/refusal controls pass;
and existing verticals remain unchanged.  It does **not** dominate current work merely by
introducing ports, an attributed graph, a scalar impedance helper, a converged grid, or a
more ambitious roadmap.  If any prerequisite fails, preserve the counterexample and stop at
the narrower completed layer.
