# SmartChem

SmartChem is a research compiler for reality-respecting simulation programs.

A scientist may start with chemistry, an incomplete physical model, or cross-domain language
such as “black holes in water,” “a human as an environmentally affected isotope,” or “an
Ising magnet as a lattice gas.” SmartChem's intended job is to collaborate on the meaning,
make every consequential choice explicit, construct only a physically scoped executable
plan, and return results with their evidence, omissions, casualties, and approval history
attached.

The general language does not exist yet. The repository contains a rigorous compiler/runtime
seam, a chemistry core, and six deliberately narrow executors that test the design.

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
inherit authority by registration.

`ClaimKind` and `EvidenceStatus` are independent. An analogue can have established algebra
without becoming literal; a literal target can remain unsupported.

## Current executors

| Executor | What it establishes | Hard boundary |
|---|---|---|
| Reaction energy | Conserving closed endpoint-energy execution with exact output inventory and a verified spectator-residue transform under the runtime-owned separable model. | Public oracle coverage remains narrow; spectator cancellation is not licensed for interacting, solvated, field-coupled, or open models. |
| Shallow-water horizon v1 | Branch-specific `U ± sqrt(g h)` characteristics and sample-bracketed crossings on a typed prescribed profile. | `ANALOGUE/STRUCTURAL_TOY`; not a continuous background solution, measured flume, scattering calculation, or literal black hole. |
| Water finite-section preflight v2 | Manufactured discharge/head, `kh`, Bond-number, sign/orientation, uncertainty, and adjacent-sample compatibility gates. | Does not establish steady regularity, a continuous transcritical solution, or experimental validation. |
| Human-isotope D2a | A complete typed interpretation and proof that one hypothetical median-lethality endpoint is compatible with distinct survival families. | `EXPERIMENTAL_PROXY/STRUCTURAL_TOY/UNVALIDATED`; no LD50-to-rate conversion, human prediction, toxicology calibration, or experimentation authority. |
| Synthetic survival D2b-S | TRAIN-only fixed-family conditional-binomial recovery on content-addressed independent synthetic cohorts, with uncertainty diagnostics and locked HOLDOUT scoring. | Same-generator implementation evidence only; no human/animal evidence, biological validation, causality, or transfer authority. |
| Finite C3 Ising↔lattice gas | All eight states, `ε=4J`, `μ=2h−4J`, `H_I=H_LG+3(h−J)`, and the formal partition identity, checked with exact integers and a separate direct verifier. | `ANALOGUE/ESTABLISHED/CERTIFIED` for that finite algebra only; no material identity, dynamics, thermodynamic limit, or arbitrary-graph transfer. |

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
`scheduled_product`/`tensor` is a deterministic left-first compatibility schedule.

For the module-by-module map and scientific caveats, see [MANIFEST.md](MANIFEST.md).

## Reproduce

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

pytest -q
python -m smartchem.bench
```

Current maintained fast-suite result:

```text
1266 passed, 14 skipped, 1 xfailed
```

The skipped tests are marked slow and are not represented as passed. Run selected
real-wavefunction integration coverage with:

```bash
pytest -q --runslow
```

Every cited compiled run has a committed deterministic harness and durable receipt:

- [runtime-registry migration](experiments/RESULTS_runtime_registry_migration.md)
- [H2 compiled vertical](experiments/RESULTS_compiled_h2_vertical.md)
- [water-wave structural vertical](experiments/RESULTS_compiled_water_wave_vertical.md)
- [water finite-section preflight](experiments/RESULTS_compiled_water_wave_validation.md)
- [human-isotope identifiability](experiments/RESULTS_compiled_human_isotope_vertical.md)
- [synthetic survival recovery](experiments/RESULTS_compiled_human_survival_recovery.md)
- [verified Class-A reaction residue](experiments/RESULTS_compiled_class_a_optimizer.md)
- [exact finite Ising/lattice-gas map](experiments/RESULTS_compiled_ising_lattice_gas_vertical.md)

Raw journals are write-once local run artifacts. Receipts retain the relevant identities,
outcomes, scientific scope, evidence status, omissions, casualties, and negative claims.

## Roadmap

Short-term campaign work is complete: the runtime registry, finite water preflight,
synthetic survival recovery, first verified Class-A transform, and exact finite cross-domain
control are committed and reproduced.

Best next midterm work:

1. extend the water ladder to continuous steady compatibility/regularity and spatial
   convergence before any dispersive solver claim;
2. build the traffic kinematic-wave vertical as the next regime-valid analogue;
3. add persistent reuse/shared-intermediate/lossless-storage planner slices only where full
   output equivalence is established;
4. design the empirical survival rung around independent data authority, external validation,
   censoring/competing-risk semantics, and calibrated uncertainty—without assuming access to
   human data or authority for experimentation;
5. add typed open ports through a port-Hamiltonian control before claiming general
   multiphysics composition.

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

The standing standard is simple: a loud refusal is acceptable; a plausible, unearned answer
is not.
