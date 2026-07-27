# SmartChem build/research round — live contract

**Remote base:** `femboy2112/SmartChem@247c060d4b2ead4690f952b270e334496b6b7d73`
**Working branch:** `agent/smartchem-roadmap-round-20260727`
**Initial local baseline:** `python -m pytest -q -rs` reported
`1225 passed, 51 skipped, 1 xfailed`; the extra skips are PySCF-dependent and are
not counted as passes. The equivalent console-entrypoint invocation exposed a
pre-existing packaging defect: the two tests importing public experiment harnesses
failed because `experiments` was not an installed package. Initial remote CI
confirmed the same two failures on Python 3.10, Python 3.12, and the PySCF-visible
job. The round therefore begins from a scientifically green local module run but a
red distribution/CI gate.

## Calculation ledger at entry

No calculation is in progress. The H2, water v1, finite water v2, human D2a,
synthetic-survival D2b-S, reaction-residue, and finite C3 Ising/lattice-gas
calculations are terminal. New calculations in this round require new identities,
paths, approvals, and receipts.

## Triangulated frontier

The completed chemistry layer is a conserving category of closed sequential
histories. It is load-bearing for that domain, but its left-first
`scheduled_product` cannot represent genuine parallel/open composition. The compiler
seam also has records for components, ports, connections, boundaries, models,
transforms, and evidence whose cross-reference and runtime ownership are not yet
fully enforced.

Three independent bearings were compared:

- the live handoff names a continuous steady-water background as the next
  midterm;
- an adversarial runtime audit reproduced successful execution of malformed IR,
  foreign models, arbitrary transforms, orphan evidence, and duplicate evidence
  shadowing;
- an independent category construction found that a credible open-diagram plus
  RLC/MNA slice is about three separate milestones—P0 ownership, exact open syntax,
  and a semantic interpreter—not one bounded round.

The decision is therefore:

1. close the P0 seam and distribution/CI defects as short-term work;
2. execute the roadmap-named manufactured continuous-water rung as the best-shot
   midterm;
3. leave a falsifiable design and migration boundary for the open-diagram kernel,
   rather than claiming that a few circuit examples constitute the new backbone.

This supersedes the initial RLC-first conjecture recorded before live
triangulation. The conjecture remains a serious follow-on, but it is not the
current implementation target.

## Midterm hole contract

### Proposed statement

For each of three declared manufactured constant-width, one-dimensional,
steady shallow-water families—subcritical, supercritical, and isolated
regular-transcritical—the compiler can:

1. retain typed domain, boundary, discharge, depth, velocity, bed, source,
   friction, uncertainty, regularity, mesh, and diagnostic records;
2. independently check
   \[
   q=b h U,\qquad
   H=z_b+h+\frac{U^2}{2g},\qquad
   (1-Fr^2)h'=S_0-S_f;
   \]
3. require \(S_0=S_f\) where \(Fr=1\), without evaluating a hidden \(0/0\)
   quotient;
4. run one bounded numerical reconstruction on \(N,2N,4N\) meshes, retain each
   field/residual/diagnostic, and expose honest spatial reconstruction convergence;
5. compare the result with the finite-section v2 diagnostics and explain, rather
   than suppress, disagreements caused by v2's finite/lossless assumptions;
6. reject or downgrade friction omission, a flipped critical sign, forged
   regularity, hidden interpolation, and dropped uncertainty/output evidence.

### Truth state

**Conjectured at entry; supported at the bounded finite/computational scope at
conclusion.** The balance laws and manufactured profiles are analytic. Numerical
convergence, lifecycle closure, and mutation resistance were discharged for the
declared families, mesh ladder, and runtime by the final receipt and directed tests;
they remain outside-scope for arbitrary profiles, meshes, and physical channels.

### Hypotheses and quantifiers

- Constant rectangular width, steady one-dimensional hydrostatic shallow-water
  structure, fixed gravity, prescribed discharge, and declared friction/source
  profiles.
- Quantification is over the three closed manufactured families and the declared
  finite mesh ladder, not arbitrary channels or arbitrary functions.
- The transcritical family has one declared isolated critical point and an analytic
  removable regularity condition.
- The result remains `ANALOGUE` / `STRUCTURAL_TOY`.

### Weakest sufficient form

A manufactured verifier/reconstructor with independent equation residuals,
critical compatibility, preregistered refinement, complete retained output, and an
approved calculation receipt is sufficient. A time-dependent PDE solver,
free-surface CFD code, or measured-flume calibration is not required.

### Dependency edges closed if true

- closes the continuous-background gap below the existing finite water v2
  preflight;
- gives future wave, scattering, and open-boundary components spatial fields,
  balance residuals, regularity, and boundary-state semantics;
- supplies a concrete conservation-law component for later typed port gluing;
- separates solver convergence from model validity and finite-v2 compatibility.

### Novelty tax

This is not a denser sampling of water v2. It must carry a continuous manufactured
profile, spatial derivatives, friction/source balance, critical compatibility, a
mesh ladder, and out-of-sample reconstruction error. It is not a general continuum
claim because the family and solver are explicitly bounded.

### Known failures it must evade

- one-mesh agreement masquerading as convergence;
- direct evaluation of the analytic profile masquerading as a numerical solve;
- division through \(1-Fr^2=0\) at the critical point;
- an omitted friction term being hidden by a manufactured bed profile;
- interpolation at undisclosed sample locations;
- treating finite v2 as truth or silently forcing agreement;
- dropping uncertainty, mesh, residual, or output-contract fields.

### Cheapest falsifiers

- failure of exact continuity, energy, momentum/balance, or critical-compatibility
  residuals on a manufactured family;
- nonpositive depth, branch misclassification, or more than one critical point;
- nondecreasing fixed-grid reconstruction error over \(N,2N,4N\);
- a mutation that preserves an authoritative `COMPLETE` result;
- an unexplained continuous-v2 diagnostic disagreement;
- a regression in the existing fast suite.

### Candidate proof/implementation languages

Frozen typed records, analytic manufactured profiles, specific-energy roots,
bounded branch selection, piecewise spatial reconstruction, finite-difference
diagnostics that do not share the exact derivative path, immutable execution
receipts, and property/mutation tests.

### Finite/computational boundary

Passing the finite mesh ladder does not prove convergence for arbitrary mesh size,
arbitrary geometry, or the full shallow-water PDE. Manufactured exactness does not
establish external physical validity. The evidence supports only the implemented
families, equations, solver, and declared reconstruction metric.

### Next lamp if Dark

If the regular-transcritical case cannot maintain the declared balance and
refinement without analytic truth leaking into the numerical branch selection,
preserve the counterexample, complete the sub/supercritical rung only, and keep
transcritical status explicitly blocked.

## Candidate short-term P0 gates

1. Enforce all `PhysicalIR` member types, IDs, references, port compatibility,
   boundary targets, and evidence references.
2. Make every executor reject non-owned models and transforms before journal
   creation; no-transform executors reject any nonempty transform inventory.
3. Bind exact transforms to the approved model and observation/equivalence
   contracts.
4. Hard-deprecate the misleading `Reaction.tensor` alias while preserving the
   explicitly named left-first schedule.
5. Add constructor-bypass and mutation tests for the model, transform, graph, and
   evidence boundaries.

All five were reproduced as live, compatible targets. Exact output-container and
subject gates already exist and are being preserved rather than relabeled as new
work.

## Category-backbone decision

The project is right to use category theory as binding structure rather than as
the physics inside every component. The current closed reaction category is
load-bearing for conservation, composition, and path-sensitive chemistry. It
should remain closed and explicit.

The global mistake is treating the same linear-history representation—or the
free-string records around it—as though it were already an open multiphysics
backbone. `Reaction.tensor` serializes the left history before the right and cannot
satisfy interchange. A scalar impedance cannot repair that defect because
series/parallel reduction is not a monoidal semantics for arbitrary topology.

The next backbone should therefore be layered:

1. **`StructureIR`:** exact typed open diagrams with ordered boundary interfaces,
   disjoint union, boundary gluing, canonical equality modulo internal names, and
   executable unit/associativity/symmetry/interchange laws;
2. **domain semantic algebras:** mass-action/Petri-net chemistry, shallow-water or
   finite-volume conservation laws, MNA/DAEs for circuits, FEEC/PDE operators for
   fields, censoring-aware likelihoods for survival, and port-Hamiltonian relations
   only where a real power pairing exists;
3. **`ModelIR`:** model/adaptor/refinement chains and exact transform ownership;
4. **`EvidenceIR`:** observations, contracts, uncertainties, residuals, and
   validity/refinement witnesses;
5. **`ExecutionDAG`:** computation scheduling only—physical feedback cycles stay
   in `StructureIR` and must not be flattened into an acyclic task graph.

The first open-diagram implementation should be staged after P0:

- exact syntax and quotient laws first;
- resistor-only DC MNA through one topology-generic stamping path second;
- bridges, AC/RLC, and port-Hamiltonian semantics only after the same diagram
  representation survives the earlier gates.

The continuous-water result in this round should be viewed as a future open
conservation-law component with boundary state \((q,H)\) and a local
source/friction relation. It must not yet be called port-Hamiltonian: the immediate
claim is steady balance plus dissipative regularity, not a proved
power-preserving interconnection theorem.

## Claim ledger

| Claim | Final state | Evidence or falsifier |
|---|---|---|
| Current reaction composition is useful | supported | existing conserving path laws and compiled reaction vertical |
| Current `Reaction.tensor` is a true tensor | refuted | strict interchange `xfail`; left-first history counterexample |
| Current global IR seam owns all typed references it claims | supported after repair | exact member/ID/reference/evidence checks and constructor-forgery regressions; free-string domain meaning is still not claimed |
| Every closed executor owns its model/transforms pre-journal | supported after repair | seven registry preflights, guarded dispatch, exact plan/approval admission, and zero-call/no-journal attacks |
| Open diagrams + MNA are the best immediate midterm | refuted as a scheduling claim | live handoff plus dependency/size comparison |
| Manufactured continuous water is the best immediate midterm | supported and completed | bounded dependency cut plus terminal compiled run |
| Continuous manufactured result is valid | supported at declared finite scope | `COMPLETE` receipt, six passing obligations, conservative two-pair refinement, root residuals, mutation controls, independent `SHIP` |

## Round outcome

All five P0 gates closed. Public experiment harnesses are now installed, removing the
module-vs-console `pytest` packaging split that made the initial remote branch red. The
seventh closed executor completed the regular-transcritical `32/64/128` control with
minimum depth/residual orders `1.0220072337077022` and `1.0315851382167684`, maximum
continuity residual `2.220446049250313e-16`, maximum energy-root residual
`1.1102230246251565e-16`, and exact critical compatibility at `x=4.3 m`.

Finite v2 independently evaluated nine retained finest-mesh samples. It is independent
code, not independent data. Its lossless head gate disagreed with the frictional
continuous model; the retained friction drop (`0.09921875000000001 m`) exceeds the
maximum reconstruction offset (`1.801707032789146e-6 m`) by far more than the
preregistered attribution threshold.

The terminal run is `d60a232aa9d74507bbc1127f38cc6315`; no calculation remains in
progress. Both supported pytest entry points report
`1279 passed, 51 skipped, 1 xfailed`. The deterministic harness and complete identity
ledger are in `experiments/RESULTS_compiled_water_wave_continuous.md`.
