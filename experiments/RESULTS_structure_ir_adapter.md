# StructureIR adapter migration — 2026-07-28

## Verdict

**COMPLETE as a bounded architecture migration.** SmartChem now has a versioned,
alpha-invariant `StructureIR` representation of successful S0 canonical observations, a
separate presentation-specific adapter witness, and an exact plan attachment. The
attachment is rederived before execution and records one of `OBSERVED`, `REFUSED`, or
`NOT_APPLICABLE`.

This result adds no scientific calculation and no new executor. It does not establish a
general physics language, a universal structure category, or a semantic functor for every
domain.

## Exact categorical scope

The represented category is the S0 quotient:

- objects are finite ordered electrical `Interface` values;
- morphisms are finite typed undirected open multigraphs modulo construction-local names
  and declaration order, retaining ordered boundaries, node/component kinds, incidence,
  parallel multiplicity, and self-loops;
- composition is boundary gluing;
- tensor is disjoint union with ordered boundary concatenation;
- the tensor unit is the empty interface and the symmetry is S0 `braid`.

The runtime observer is resource-bounded even though the underlying finite presentation
operations are total. A canonicalization-budget refusal remains a typed refusal; it does
not become approximate or ID-dependent equality.

## Migration identities

The probe used the committed E1/E2 experiment subjects without executing either engine.

| Item | Digest / status |
|---|---|
| Adapter schema | `smartchem.structure-adapter/s0-canonical-v1` |
| Structure schema | `smartchem.structure-ir/open-diagram-v1` |
| Plan attachment schema | `smartchem.structure-attachment/plan-v1` |
| E1 subject | `af51f2d9d2c2f8062bf6db6f1988d76edef98f38140f1163456265328ce8a2dc` |
| E1 raw presentation | `97059bf7b52e174e7ccba77d1c2fd5d1d7f6987586ff51b3dff87c58800996c9` |
| E1 StructureIR | `a3353d9ea51c0939b43f9b5d5300d969f45f2934cd5ec4e2b557781dbc235e92` |
| E1 witness | `5caac07537d6aa15fe1cd996b109bcbf02a82161c417907ff39ea1a35df640f7` |
| E1 attachment status | `OBSERVED` |
| E2 damped subject | `33bad6b923d602eacfc79eb1b954fe68b991d81c2e6740d91daa248e81f3fe18` |
| E2 raw presentation | `03e954904655eab5961646c0aed2b9539c74ded7c49a26965e3591a6caf51d67` |
| E2 StructureIR | `3ec4cac57d5fe83f661b870ea5a9649550a3fdd82b3145eee7955a4ab8fd6ec5` |
| E2 witness | `6e6a836cf0e00e39eb0e498e8b010793bc20fbeb8ecac1b39ec3113b461a770a` |
| E2 attachment status | `OBSERVED` |
| Closed registry | `a9b8b4f8e0dd698cd018dec31517a3c0c25de4f8569b098bbac15c3e0246359a` |
| Compiler/runtime after migration | `7b69fabaead12184738266262013ca3969092ebd04332dc558e8e90428a85523` |

The registry digest and all nine exact output-contract digests are frozen by regression
tests and remain unchanged. The compiler digest changes intentionally because the shipped
source manifest now includes `structure_ir.py` and the plan-admission seam. Newly compiled
plan digests include the exact attachment. Historical approvals are therefore not silently
reused.

## Falsifying controls

- canonical encode/decode and normalized-presentation round trip;
- component/junction alpha-renaming and declaration-order invariance;
- distinct raw-presentation witnesses for the same quotient structure;
- unit, associativity, tensor unit/associativity, interchange, symmetry, and naturality on
  finite controls;
- parallel multiplicity and self-loop retention;
- explicit canonicalization-cap refusal with total raw tensor preserved;
- unchanged E1/E2 subject digests and nonidentity E2 model-to-edge binding;
- `OBSERVED`, `REFUSED`, and `NOT_APPLICABLE` plan states;
- forged attachment rejection at construction and again before journal/engine dispatch;
- exact closed-registry and all-nine output-contract digest regression.

Focused migration/category/runtime selection after hostile-construction and callback-mutation
repairs:

```text
90 passed in 2.05s
```

Full suites after the final hostile-construction repair:

```text
python -m pytest: 1476 passed, 14 skipped, 1 xfailed in 179.25s
console pytest: 1476 passed, 14 skipped, 1 xfailed in 182.71s
```

The skips remain the declared `--runslow` real-oracle geometry/finding cases. The xfail
remains the intentional counterexample to treating closed sequential reaction scheduling
as a true parallel morphism tensor.

## Boundary and next discriminating probe

`StructureIR` is not the raw E1/E2 model-alignment record. Canonical quotient structure
cannot uniquely recover declaration indices across graph automorphisms, so the raw
presentation digest and explicit model-edge bindings remain authoritative.

A `REFUSED` attachment is intentionally approvable only as part of the existing
run-to-refusal lifecycle. It authorizes no canonical StructureIR and cannot reach an engine:
the runtime creates a durable refused record for the exhausted/exceeded budget. Turning
this state into a planning blocker would erase the already-shipped explicit refusal path.

DC already has exact rational linear-relation `identity`/composition/tensor operations and
finite black-box preservation controls. E2's exact `ComplexBoundaryRelation` currently has
no corresponding operations. The cheapest next category-semantic probe is therefore:

1. implement exact `Q(i)` linear-relation identity, composition, and tensor;
2. test E2 black-box preservation under S0 composition/tensor, including relations for
   cases where a selected drive would be singular;
3. only after that, specify a circuit-local `ModelIR` whose decorated morphisms and explicit
   presentation permutations make the semantic functor claim meaningful.

Port-Hamiltonian, traced, compact-closed, dynamic, and cross-domain claims remain out of
scope until operational state and effort/flow power pairings exist.
