# SmartChem exact open-syntax round — release record

> **Historical S0 cut.** Its seven-executor/E1-next statements are superseded by
> `RESEARCH_ROUND_RESISTIVE_DC_2026-07-27.md`: E1 is now complete, the registry has eight
> executors, positive-frequency passive AC/RLC E2 is next, and former PID `151446` is
> terminal-unclassified rather than active. The remote `fdb906f` E1 rejection below remains
> valid history.

**Base:** `ff41f018338886949c3e57657495e77f91e3fcc3`

**Remote input audited:** `origin/agent/smartchem-open-semantics-round-20260727`
at `fdb906f`

## Decision

All authoritative short-term/P0 goals were already terminal, so this round selected the
first remaining category midterm: S0 finite typed open-diagram syntax. The remote branch
was not fast-forwarded. Only its topology kernel was selectively ported and its fixed law
tests were expanded over a deterministic generated family.

The remote circuit, runtime, experiment, receipt, and documentation stack was rejected.
Its completion postcondition and payload validation call the same production
`analyze_resistive_dc` path as the engine, while its numerical residuals also derive from
the production MNA matrix and exact-relation function. That is deterministic
recomputation, not an independent verifier against common-mode defects.

## Implemented S0 boundary

`smartchem/open_diagram.py` now provides:

- one exact electrical port kind and one undirected two-terminal structural component
  signature;
- ordered input/output interfaces whose positions are boundary identities;
- smart construction with unique local component/junction IDs and exact once-only
  ownership of every boundary occurrence and component terminal;
- total compatible-boundary gluing and total disjoint-union tensor;
- unit interfaces, identities, and braids;
- an exact alpha-invariant canonical observer that preserves parallel multiplicity and
  self-loops and names `CanonicalizationBudgetExceeded` when its factorial residual
  search exceeds the declared candidate budget.

Composition and tensor never invoke the bounded observer. Construction-local IDs are
discarded, while structural edge declaration order remains available for a future explicit
model-reindex witness. Opaque observer labels are not physical parameters or such a
witness.

The package exports the new API under `Open*`/`open_*` names so the existing closed
reaction `identity`, `braid`, and deliberately left-first scheduled product remain
semantically distinct.

## Generated and adversarial controls

The focused suite retains malformed/duplicated/missing endpoint refusals,
alpha/declaration invariance, parallel multiplicity, self-loop incidence, an independent
brute-small permutation oracle, identity/braid/hexagon controls, and explicit
observer-budget refusal.

Its generated family adds eight distinct `1 -> 1` presentations: one-, two-, and
three-edge chains; two-, three-, and four-edge parallel networks; a three-edge feedback
triangle; and a path tensored with a disconnected closed self-loop. It checks:

- left/right identity for every member;
- all `8^3 = 512` ordered associativity triples;
- 64 structurally varied interchange controls;
- 64 structurally varied braid-naturality controls.

These are finite executable controls, not a formal proof over arbitrary graphs.

## Calculation ledger

No compiled simulation was started by S0 and no scientific result receipt was created.
All seven existing executor runs remain historical terminal calculations tied to their
original compiler identities. Any new compiled run needs a fresh plan, approval, and
write-once journal because adding shipped source changes the compiler implementation
identity.

The optional cold all-oracle chemistry benchmark at OS PID `151446` was preserved while
this round ran. It is unjournaled, not a release gate, and its timing is unpublishable
because it overlapped other load.

## Claim ledger

| Claim | State | Evidence | Boundary / falsifier |
|---|---|---|---|
| S0 constructs well-owned finite presentations | Supported in implemented scope | smart-constructor rejection tests and exact stored-invariant checks | unknown/duplicate/missing/mixed endpoint constructs |
| `then` and `tensor` are structural and total on compatible finite presentations | Supported in implemented scope | direct union-find/disjoint-union implementation; high-symmetry tensor survives before observer refusal | either operation calls canonicalization or loses incidence |
| Successful canonical observations are alpha/declaration invariant | Supported on fixed, generated, brute-small, and independent metamorphic controls | canonical equality, opaque-label alignment, permutation oracle | an isomorphic presentation observes differently without budget refusal |
| Open composition satisfies the tested symmetric-monoidal laws | Supported on the declared finite controls | identity, associativity, interchange, braid involution/naturality, and hexagon tests | any generated exact counterexample |
| S0 is a circuit or multiphysics semantics | Refuted as a present claim | no constitutive values, equations, solver, evidence, executor, or `PhysicalIR` adapter exist | N/A |
| Remote E1 is independently verified | Refuted | engine, postcondition, and payload checks reuse production analysis; solver residuals reuse production assemblies | a separate direct verifier and forced common-mode mutation gate |

## Verification

```text
.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_open_diagram.py tests/test_runtime_registry.py \
  tests/test_p0_runtime_seam.py tests/test_laws.py
108 passed, 1 xfailed

.venv/bin/python -m pytest -q -rs
.venv/bin/pytest -q -rs
1345 passed, 14 skipped, 1 xfailed
```

The 14 slow tests were not run and are not represented as passing. The strict xfail is the
preserved closed-reaction interchange counterexample, not an S0 failure.

A deterministic independent metamorphic probe generated 500 accepted finite multigraph
presentations from 918 attempts at seed `20260727`; component naming/order, junction order,
endpoint order, and undirected terminal orientation were changed before exact comparison.
All observed canonical forms agreed. A separate read-only reviewer enumerated 761
constructible zero-to-three-component presentations and declaration-aligned opaque-label
variants and found no mismatch. These are additional finite controls, not proof.

Package import checks preserve distinct closed/open identities. The runtime registry remains
seven executors with semantic digest
`aed56d04625e864e2ed029375ceb663c4d242a152a2b7ccfbb5f4890d44623e0`.
The new shipped-source compiler implementation digest is
`84577e497d48d48685bf44e8a4777cc25c4583e3dd7630de8f19184af8910669`.
`python -m compileall -q smartchem experiments tests`, `git diff --check`, and the relative
Markdown-link audit passed.

## Compact-resume cut

The next category milestone is E1, not AC/RLC and not a conversational layer. Before
importing any production MNA code, implement a separate direct verifier that independently
traverses public structure/model/result fields and recomputes complete branch inventory,
Ohm-law currents, per-node KCL including the reference, drive voltage, source sign,
source-inclusive power, and passivity without importing production solver, stamping,
analysis, or exact-relation helpers. Then force production and ordinary postconditions to
return forged outputs and require the untouched direct verifier to end the run `INVALID`
with artifacts quarantined.

After that gate, one topology-generic sparse stamping path may be considered for single,
series, parallel, bridge, cycle, and signed rational controls, with floating/singular/
non-finite refusal. AC/RLC follows only after E1; port-Hamiltonian language follows only
after an actual effort/flow power pairing is established.
