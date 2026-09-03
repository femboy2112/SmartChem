# SmartChem

SmartChem is a research compiler for reality-respecting simulation programs.

A scientist may start with chemistry, an incomplete physical model, or cross-domain language
such as “black holes in water,” “a human as an environmentally affected isotope,” or “an
Ising magnet as a lattice gas.” SmartChem's intended job is to collaborate on the meaning,
make every consequential choice explicit, construct only a physically scoped executable
plan, and return results with their evidence, omissions, casualties, and approval history
attached.

The general language does not exist yet. The repository contains a rigorous compiler/runtime
seam, a chemistry core, nine deliberately narrow executors that test the design, and a
separate finite typed open-diagram syntax with independently verified ideal-resistor DC and
positive-frequency passive-RLC interpretations.

## Non-negotiable contract

SmartChem follows four rules:

1. **Reality outranks completion.** Well-formed, coherent, applicable, converged,
   valid-after-run, validated, and scientifically useful are different verdicts.
2. **Output is frozen before optimization.** Observable membership, support, resolution,
   precision, coverage, uncertainty, diagnostics, provenance, and retained artifacts may not
   be reduced without explicit scientist approval.
3. **Efficiency is mandatory inside that boundary.** The compiler should use the cheapest
   identity- or contract-preserving execution it can establish. If resources are insufficient,
   it checkpoints, proposes a disclosed alternative contract, or refuses; it does not return
   a smaller success.
4. **Meaning belongs to the scientist.** The compiler may derive, check, search, propose, and
   expose unknowns. It may not silently choose scientific meaning or promote a metaphor,
   finite check, converged calculation, or synthetic recovery into physical validation.

The full policy is in [DIRECTION_AUDIT_2026-07-27.md](DIRECTION_AUDIT_2026-07-27.md).

## The executable seam

```text
incomplete source
    → typed shepherd session
    → resolved source/target/transport/assembly meaning
    → Physical IR + frozen OutputContract
    → candidate plan + blockers + predicted resources
    → scientist approval bound to the exact plan digest
    → closed-registry execution
    → pre/post validity obligations
    → COMPLETE | INCOMPLETE | INVALID | REFUSED | FAILED
    → typed outputs + certificate
```

Plans bind the shipped compiler/runtime implementation and the calculation identity. Run
journals have exclusive path ownership, persist atomically, and quarantine artifacts from
non-complete runs. The runtime registry is closed and reviewed: no third-party executor can
inherit authority by registration. A pre-backend execution-admission snapshot is rechecked
after in-process backend callbacks and before certification, so a callback cannot silently
rewrite the approved plan, resolved subject, output contract, calculation identity, or
compiler identity and still complete.

`ClaimKind` and `EvidenceStatus` are independent. An analogue can have established algebra
without becoming literal; a literal target can remain unsupported.

## Current executors

| Executor | What it establishes | Hard boundary |
|---|---|---|
| Reaction energy | Conserving closed endpoint-energy execution with exact output inventory and a verified spectator-residue transform under the runtime-owned separable model. | Public oracle coverage remains narrow; spectator cancellation is not licensed for interacting, solvated, field-coupled, or open models. |
| Shallow-water horizon v1 | Branch-specific `U ± sqrt(g h)` characteristics and sample-bracketed crossings on a typed prescribed profile. | `ANALOGUE/STRUCTURAL_TOY`; not a continuous background solution, measured flume, scattering calculation, or literal black hole. |
| Water finite-section preflight v2 | Manufactured discharge/head, `kh`, Bond-number, sign/orientation, uncertainty, and adjacent-sample compatibility gates. | Does not establish steady regularity, a continuous transcritical solution, or experimental validation. |
| Continuous steady-water control | Manufactured subcritical, supercritical, and isolated regular-transcritical backgrounds; bounded cell-centred energy-root reconstruction on 32/64/128 meshes; binary64 roundings of a separate 60-digit Decimal reference evaluation; retained balance residuals, both refinement-pair rates, both critical compatibility conditions, metadata-only uncertainty, and an exact finite-v2 comparison. | `ANALOGUE/STRUCTURAL_TOY`; not a finite-volume/general stationary solver, continuum theorem, propagated uncertainty analysis, measured flume, dispersive/scattering result, or literal gravity. |
| Human-isotope D2a | A complete typed interpretation and proof that one hypothetical median-lethality endpoint is compatible with distinct survival families. | `EXPERIMENTAL_PROXY/STRUCTURAL_TOY/UNVALIDATED`; no LD50-to-rate conversion, human prediction, toxicology calibration, or experimentation authority. |
| Synthetic survival D2b-S | TRAIN-only fixed-family conditional-binomial recovery on content-addressed independent synthetic cohorts, with uncertainty diagnostics and locked HOLDOUT scoring. | Same-generator implementation evidence only; no human/animal evidence, biological validation, causality, or transfer authority. |
| Finite C3 Ising↔lattice gas | All eight states, `ε=4J`, `μ=2h−4J`, `H_I=H_LG+3(h−J)`, and the formal partition identity, checked with exact integers and a separate direct verifier. | `ANALOGUE/ESTABLISHED/CERTIFIED` for that finite algebra only; no material identity, dynamics, thermodynamic limit, or arbitrary-graph transfer. |
| Finite resistive DC E1 | Exact rational passive boundary relation plus one topology-generic sparse-MNA drive, explicit model-to-edge binding, complete node/branch/source output, and a production-independent direct verifier. | `LITERAL/VALIDATED_WITHIN_REGIME/CERTIFIED` only for finite positive ideal resistors and the declared drive/reference; no device, AC/RLC, thermal, safety, nonlinear, distributed, or port-Hamiltonian claim. |
| Positive-frequency passive RLC E2 | Exact `Q(i)` boundary relation, exact driven-rank preflight, one normalized sparse complex-MNA path, complete phasor/power/diagnostic output, explicit model-to-edge binding, and a production-independent direct verifier. | `LITERAL/VALIDATED_WITHIN_REGIME/CERTIFIED` only for the declared finite ideal mathematical networks at one positive frequency; exact lossless singular resonance is refused without regularization. No device, transient, nonlinear/active, tolerance, safety, distributed, or port-Hamiltonian claim. |

The Ising/lattice-gas control is intentionally important: it proves that SmartChem can carry
an exact cross-domain map without confusing exact mathematics with literal physical identity.
Every one of the eight microstates remains output; no grouped summary replaces them.

## Cross-domain and cross-scale language

A metaphor is accepted as an under-specified program, not as truth. Shepherding separates:

- source theory and target phenomenon;
- target scale and scientist-selected granularity;
- structures intended to transfer;
- preserved, modified, discarded, and unknown axioms;
- target assembly and its evidence;
- calibration, validation, falsifiers, and requested outputs.

Where transport or assembly is not established, SmartChem may construct a typed experimental
hypothesis with explicit missing evidence. It must not enter the certified lane or lose its
experimental status merely because it runs successfully.

The current portfolio deliberately spans three cases:

- water/black-hole language: a regime-bounded structural analogue;
- human/isotope language: an underidentified cross-scale experimental proxy;
- Ising/lattice-gas language: an exact finite map between distinct referents.

Next controls under consideration include traffic kinematic waves, port-Hamiltonian
cross-substrate composition, groundwater/electrical potential, and SIR/reaction-network
mappings. These are research candidates, not an exhaustive menu generated by the language.

## Auditing an external project's probes

`smartchem.evidence` is a decoupled sibling of the compiler: it points SmartChem's own
discipline — *a check derived from its own subject checks nothing* — at another project's
numerical probes, auditing the contract around them (teeth, provenance independence, source
locks, scope, tier boundary) and either certifying or refusing. It reuses `contracts.py`
primitives but never enters the closed executor registry and never raises a declared
evidence status; every certificate prints a hygiene-not-physics banner.

The integration is decoupled by design. A consumer emits a JSON manifest conforming to
`smartchem/evidence/manifest.schema.json` and runs

    smartchem-verify-probes --example > my-probes.json   # a certifying template to edit
    smartchem-verify-probes my-probes.json               # audit it
    # equivalently: python -m smartchem.evidence my-probes.json

importing nothing else from SmartChem — and the subpackage itself imports only the standard
library, so the auditor never pulls in the numeric stack (`import smartchem` stays light;
numpy loads only when a numeric domain is actually used). Exit code `0` = every manifest
certified, `1` = at least one refused, `2` = a manifest could not be loaded. See
`smartchem/evidence/README.md` for the manifest format and
`FINEMAN_VERIFICATION_BRIDGE_2026-08-06.md` for the full bridge rationale.

## Chemistry core

The older core remains useful and actively tested:

- structured `Molecule`, multiset `Config`, and conserving sequential `Reaction`;
- exact stoichiometric completion/checking over integer kernels;
- declared oracle domains and typed refusal diagnosis;
- pluggable heuristic, persistent-cache, photon, and PySCF oracle layers;
- pathway search, Store-based finite surveys, geometry/harmonic tooling, and benchmark
  infrastructure.

Reactions form a category under sequential composition. The object product is commutative,
but reaction histories do not yet form a true parallel symmetric monoidal product:
`scheduled_product` is a deterministic left-first schedule. The old `tensor` compatibility
name now emits a deprecation warning because it is not a parallel tensor.

`smartchem.open_diagram` remains a separate topology-only layer: ordered typed boundaries,
two-terminal component slots, exact endpoint ownership, total boundary gluing, true
disjoint-union tensor, identities, and braids. A budgeted exact observer compares successful
finite presentations modulo internal naming and refuses explicitly above its candidate
budget. `smartchem.resistive_dc_schema`, `smartchem.circuit`, and
`smartchem.resistive_dc` add one narrow positive ideal-resistor DC semantics beside it.
`smartchem.rlc_ac_schema`, `smartchem.rlc_ac_circuit`, `smartchem.rlc_ac`, and
`smartchem.rlc_ac_verifier` add a separate positive-frequency passive-RLC semantics with
exact singular preflight. Topology itself still does not imply either set of equations.
This is not a `PhysicalIR` migration, general AC system, device model, or proof of a
general multiphysics category.

For the module-by-module map and scientific caveats, see [MANIFEST.md](MANIFEST.md).

## Chemical compiler (v0.5.0a1 — an alpha in progress)

A newer line of work turns the chemistry core into a bidirectional *chemical compiler*: a
**decompiler** that descends a target compound to its elemental buckets as an AND–OR
hypergraph (conservation- and valence-respecting — formal accounting, not a physical
mechanism claim), and a **recompiler** that reads that descent back into candidate synthesis
routes, ranked by sourced evidence and terminated on real commodity buckets rather than
pretending every reagent is elemental. Both directions share one typed
`ChemicalCompilationIR` and one honesty contract:

- a bounded search returns a **SearchReceipt** that says whether it *exhausted its declared
  space* or stopped at a budget/depth/result cap; an incomplete search never looks complete,
  and an empty incomplete search never looks like a proof of absence;
- terminal outcomes speak the standard's fixed vocabulary (§8.2), including a receipt-bearing
  refusal path — a charged or malformed request returns a `RefusalReceipt` carrying a
  `REFUSED_*` status, not a bare exception;
- a candidate is a `FORMAL_CANDIDATE`, never a validated bench procedure; missing operations
  are shown, not hidden;
- a declared bench constraint (§11 temperature/pressure) is part of the request identity **and
  applied** to route ranking: each route is reported as fitting, excluded, or — when it leaves
  a constrained dimension undeclared — *unknown-fit*, which is a gap, never a silent pass;
- chemical identity is never equated with purity, concentration, grade, phase, availability,
  or price; every price is dated and sourced or it is `UNKNOWN`;
- derived, estimated, and unsupported claims are labelled distinctly — a loud refusal beats a
  plausible, unearned answer.

This is an **alpha under active construction, not a finished release.** The normative
contract is
[CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md](CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md);
[UPTAKE_MANIFEST_v0.5.0a1.md](UPTAKE_MANIFEST_v0.5.0a1.md) is an honest, per-requirement
ledger of exactly what is implemented-and-verified versus still open (the alpha is *done*
only when every P0 row is verified); and
[AUDIT_CHEMICAL_COMPILER_2026-09-01.md](AUDIT_CHEMICAL_COMPILER_2026-09-01.md) records the
evidence and rationale.

## Reproduce

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

pytest -q
python -m smartchem.bench
```

Current maintained fast-suite result (in a dev environment with the optional PySCF stack
installed; environments without it skip additional real-wavefunction tests):

```text
3300 passed, 14 skipped, 1 xfailed
```

The skipped tests require the explicit slow-test gate and are not represented as passed.
Run selected real-wavefunction integration coverage with:

```bash
pytest -q --runslow
```

Every cited compiled run has a committed deterministic harness and durable receipt:

- [runtime-registry migration](experiments/RESULTS_runtime_registry_migration.md)
- [H2 compiled vertical](experiments/RESULTS_compiled_h2_vertical.md)
- [water-wave structural vertical](experiments/RESULTS_compiled_water_wave_vertical.md)
- [water finite-section preflight](experiments/RESULTS_compiled_water_wave_validation.md)
- [continuous steady-water control](experiments/RESULTS_compiled_water_wave_continuous.md)
- [human-isotope identifiability](experiments/RESULTS_compiled_human_isotope_vertical.md)
- [synthetic survival recovery](experiments/RESULTS_compiled_human_survival_recovery.md)
- [verified Class-A reaction residue](experiments/RESULTS_compiled_class_a_optimizer.md)
- [exact finite Ising/lattice-gas map](experiments/RESULTS_compiled_ising_lattice_gas_vertical.md)
- [independently verified resistive-DC bridge](experiments/RESULTS_compiled_resistive_dc.md)
- [independently verified positive-frequency passive-RLC bridge](experiments/RESULTS_compiled_rlc_ac.md)
- [bounded StructureIR adapter migration](experiments/RESULTS_structure_ir_adapter.md)

Raw journals are write-once local run artifacts. Receipts retain the relevant identities,
outcomes, scientific scope, evidence status, omissions, casualties, and negative claims.

## Roadmap

The current short-term seam is hardened: `PhysicalIR` owns member/reference/evidence
integrity, transforms bind the approved model and contracts, all nine executors own their
model/transform inventory before a calculation or journal, and resolved runners cannot be
used as an alternate authoritative dispatch path. The manufactured continuous-water
midterm, finite open-diagram S0, independently verified resistive-DC E1, and
positive-frequency passive-RLC E2 are complete. The bounded `StructureIR` migration is
also complete: successful S0 canonical observations have a versioned quotient value,
raw-presentation/model alignment remains in a separate witness, every new plan records
`OBSERVED`, `REFUSED`, or `NOT_APPLICABLE`, and execution rederives the attachment before
any journal or engine call.

Best next work:

1. add exact identity/composition/tensor to E2's complex boundary relations and test
   black-box preservation; unlike DC, AC does not yet expose a semantic functor;
2. introduce a circuit-local decorated `ModelIR` only with explicit presentation
   permutation witnesses—undecorated topology cannot infer parameter transport;
3. keep port-Hamiltonian semantics later until dynamic state and an effort/flow power
   pairing are explicit and verified;
4. extend water only after the stationary manufactured rung: bounded dispersive branches
   first, then measured regime-matched evidence before any promotion beyond `STRUCTURAL_TOY`;
5. build the traffic kinematic-wave vertical as the next regime-valid analogue;
6. add persistent reuse/shared-intermediate/lossless-storage planner slices only where full
   output equivalence is established;
7. design the empirical survival rung around independent data authority, external validation,
   censoring/competing-risk semantics, and calibrated uncertainty—without assuming access to
   human data or authority for experimentation.

Long term: a domain-extensible Physical IR, open-process semantics, model-chain planner,
general validity/refinement runtime, and finally a conversational language that exposes rather
than impersonates those transitions.

The compact continuation sheet is [ROADMAP_2026-07-27.md](ROADMAP_2026-07-27.md).

## Research record

- [DIRECTION_AUDIT_2026-07-27.md](DIRECTION_AUDIT_2026-07-27.md) — governing scientific,
  efficiency, shepherding, and cross-domain language audit.
- [AUDIT_2026-07-20.md](AUDIT_2026-07-20.md) — detailed earlier scientific/multiphysics audit.
- [THE_COMPILER.md](THE_COMPILER.md) — derived-menu, typed-ledger, termination, and compiler
  construction record.
- [experiments/README.md](experiments/README.md) — reproducible probes and compiled harnesses.
- [CAMPAIGN_HANDOFF_2026-07-27.md](CAMPAIGN_HANDOFF_2026-07-27.md) — five-cycle state,
  calculations, commits, and next work.
- [RESEARCH_ROUND_2026-07-27.md](RESEARCH_ROUND_2026-07-27.md) — this build/research
  round's target, falsifiers, calculation ledger, and claim state.
- [RESEARCH_ROUND_OPEN_SYNTAX_2026-07-27.md](RESEARCH_ROUND_OPEN_SYNTAX_2026-07-27.md)
  — selective S0 port, generated-law evidence, rejected remote E1, and compact-resume cut.
- [RESEARCH_ROUND_RESISTIVE_DC_2026-07-27.md](RESEARCH_ROUND_RESISTIVE_DC_2026-07-27.md)
  — independently verified E1 implementation, hostile repairs, calculation receipt, and
  compact-resume cut.
- [RESEARCH_ROUND_RLC_AC_2026-07-28.md](RESEARCH_ROUND_RLC_AC_2026-07-28.md)
  — independently verified E2 implementation, exact singular refusal, calculation ledger,
  decomposed roadmap, and compact-resume cut.
- [RESEARCH_ROUND_STRUCTURE_IR_2026-07-28.md](RESEARCH_ROUND_STRUCTURE_IR_2026-07-28.md)
  — bounded quotient adapter, plan-identity migration, category audit, and next semantic rung.
- [CATEGORY_BACKBONE_ROADMAP_2026-07-27.md](CATEGORY_BACKBONE_ROADMAP_2026-07-27.md) —
  the staged open-diagram/domain-algebra architecture and its dominance boundary.
- [ROADMAP_CHEMICAL_DECOMPILER_2026-08-30.md](ROADMAP_CHEMICAL_DECOMPILER_2026-08-30.md) —
  proposal (M-4): the chemical decompiler / elemental-descent hypergraph, its formal-not-physical
  frame, termination/budget walls, reuse map, and B0–B4 build ladder.

The standing standard is simple: a loud refusal is acceptable; a plausible, unearned answer
is not.
