# SmartChem five-cycle campaign handoff

**Prepared:** 2026-07-27
**Branch:** `main`
**Implementation baseline after Cycle 5:** `45885f2`
**Remote state at that baseline:** `main == origin/main`

This is the compact continuation artifact for the 2026-07-27 campaign. The detailed
scientific and product contract remains
[`DIRECTION_AUDIT_2026-07-27.md`](DIRECTION_AUDIT_2026-07-27.md); the compact priority list is
[`ROADMAP_2026-07-27.md`](ROADMAP_2026-07-27.md).

## Governing objective

Build a shepherded-to-valid-simulation meta-compiler and reality-respecting simulation
language that:

- collaborates with the scientist to resolve incomplete, cross-domain, and cross-scale
  meaning;
- distinguishes derived, checked, searched, hypothesized, experimental, validated, and
  unknown claims;
- makes source theory, target, transport, assembly, calibration, and casualties explicit;
- optimizes execution aggressively only after physical applicability and the complete output
  contract are frozen;
- never reduces observable membership, support, resolution, precision, coverage,
  uncertainty, diagnostics, provenance, or retained artifacts without explicit scientist
  approval;
- preserves refusals, invalid runs, resource walls, and falsified claims as results rather
  than rewriting them into success.

## Five completed cycles

| Cycle | Commit | Result | Durable evidence |
|---:|---|---|---|
| 1 | `adf1575` | Sealed the closed lazy runtime registry, full shipped-source compiler identity, and exclusive atomic run-journal ownership; re-ran the existing verticals. | `experiments/RESULTS_runtime_registry_migration.md` |
| 2 | `8f8d2ba` | Added the separate finite-section water compatibility v2 executor and tightened v1's negative claim to supplied samples only. | `experiments/RESULTS_compiled_water_wave_validation.md` |
| 3 | `f176e41` | Added a separate synthetic interval-cohort survival recovery executor with TRAIN-only fitting, post-fit truth assessment, locked HOLDOUT scoring, and explicit no-transfer authority. | `experiments/RESULTS_compiled_human_survival_recovery.md` |
| 4 | `72a6a37` | Made the already-shipped reaction residue shortcut a typed, runtime-model-bound, independently verified Class-A transform and removed false raw-domain over-refusal. | `experiments/RESULTS_compiled_class_a_optimizer.md` |
| 5 | `45885f2` | Added the exact finite C3 Ising/lattice-gas map with all eight states, formal partition identity, zero output reduction, and a separately implemented direct verifier. | `experiments/RESULTS_compiled_ising_lattice_gas_vertical.md` |

Every cycle was analyzed, attacked, fixed where necessary, tested, committed, and pushed
before the next began. No Grok model was used.

## Calculation ledger

No calculation is in progress.

| Calculation family | Terminal state | Scope note |
|---|---|---|
| H2 compiled chemistry | `COMPLETE` | One fixed public oracle protocol; not broad chemistry validation. |
| Water-wave v1 | `COMPLETE` | Prescribed-profile `STRUCTURAL_TOY`; no continuous solution or measured flume. |
| Water finite-section v2 | `COMPLETE` | Manufactured compatibility preflight; no measured validation. |
| Human-isotope D2a | `COMPLETE` lifecycle, `UNDERIDENTIFIED/UNVALIDATED` science | Negative identifiability result; no human prediction or LD50-to-rate conversion. |
| Synthetic survival D2b-S | `COMPLETE` | Same-generator synthetic implementation evidence only. |
| Class-A optimizer probe, transformed and reference arms | `COMPLETE` | Certification/domain-admission correction; not a newly measured speedup. |
| Finite C3 Ising/lattice-gas | `COMPLETE` | `ANALOGUE/ESTABLISHED/CERTIFIED` finite algebra only. |

Ignored JSON journals are local, terminal run artifacts. New calculations require fresh
write-once paths, new plan identities, and new approvals. No checkpoint or partial output is
being carried forward as a completed result.

## Final verification state

```text
.venv/bin/python -m pytest -q
1266 passed, 14 skipped, 1 xfailed in 20.40s
```

- The 14 slow tests were not run and are not represented as passing.
- The strict xfail is the known true-parallel-interchange architecture debt.
- `python -m compileall -q smartchem experiments tests` passed.
- `git diff --check` passed at each publication gate.
- Science/algebra and runtime/release reviewers both returned `SHIP` for Cycles 4 and 5.
- The Cycle 5 payload validator survived a constructor bypass, forged Hamiltonian row, and
  forced postcondition pass; the result was `INVALID` and artifacts were quarantined.
- These are local verification claims. No remote CI result is inferred from them.

## What the project can now honestly say

SmartChem has six closed executors behind one source/IR/plan/approval/run/certificate seam.
It can:

- require a closed typed shepherd session before cross-domain execution;
- keep claim referent separate from evidence strength;
- enforce exact output contracts and quarantine non-complete results;
- bind plans to compiler/runtime and calculation identities;
- carry experimental proxies without promoting them;
- carry an established exact analogue without making its referents literal;
- expose and verify one narrow Class-A transform without claiming a general optimizer.

It still cannot honestly say that it is a general simulation language, general model-chain
planner, multiphysics runtime, empirical human model, continuous water-wave solver, general
optimizer, or conversational scientific environment.

## Best next midterm: continuous water-background rung

This is the best-shot next midterm because the typed water semantics, finite compatibility
gates, sign/orientation logic, uncertainty fields, output contract, and runtime lifecycle
already exist. It should be decomposed into these short-term gates:

1. Define a typed continuous background representation with domain, boundary, discharge,
   head/energy, friction/source, uncertainty, and regularity semantics.
2. State the steady governing residuals and critical-point compatibility conditions
   independently of any solver.
3. Add manufactured subcritical, supercritical, and regular transcritical solutions with
   exact or high-precision reference residuals.
4. Implement one bounded solver that retains every requested field, residual, iteration
   diagnostic, and mesh identity.
5. Require mesh-refinement/spatial-convergence evidence; a converged nonlinear solve on one
   mesh is not a continuum result.
6. Compare the continuous result with the existing finite-section preflight and explain every
   disagreement rather than treating v2 as ground truth.
7. Add mutation attacks for omitted friction, wrong critical sign, false regularity, hidden
   interpolation, dropped uncertainty, and reduced output.
8. Run a manufactured compiled vertical and retain `STRUCTURAL_TOY` until measured
   regime-matched evidence exists.

Do not jump directly to a dispersive scattering solver. The continuous stationary background
and its convergence evidence are prerequisites.

## Following midterm queue

1. **Traffic kinematic waves:** next regime-valid metaphor control. Preserve conservation-law
   structure and shock/characteristic semantics; discard literal fluid identity and add
   traffic-specific closure/calibration.
2. **Remaining optimizer:** persistent reuse, shared electronic intermediates, lossless
   storage choice, and deterministic scheduling. Each slice needs exact applicability and
   full-output equivalence before it can be Class A.
3. **Empirical survival rung:** independent data authority, censoring, cause-specific
   competing risks where requested, profile/bootstrap uncertainty, external locked
   validation, and explicit applicability/extrapolation. No human data access or
   experimentation authority is presumed.
4. **Port-Hamiltonian control:** typed effort/flow ports, power-conserving interconnection,
   and domain-local constitutive laws as the architectural control for open cross-substrate
   composition.
5. **Chemistry expansion:** xTB fast tier and broader polyatomic/state/conformer validation
   remain separate from compiler plumbing.

Other metaphor candidates already considered include groundwater/electrical potential,
SIR/reaction networks, optics/quantum-wave mappings, and reliability/population survival.
They are stress tests with distinct casualty/evidence needs, not an exhaustive language menu.

## Long-term direction

- domain-extensible Physical IR with typed open ports and state identity;
- verified model/adaptor-chain planning across scale and domain;
- general precondition, convergence, postcondition, validation, and refinement transitions;
- reusable evidence and calibration objects with explicit applicability;
- only then, a conversational language that explains and asks without impersonating those
  semantics.

## Resume protocol

1. Confirm `main`, `origin/main`, and a clean worktree.
2. Read this handoff, the direction audit, and the roadmap before choosing work.
3. Inspect current receipts and live tests rather than trusting a stale recap.
4. Decompose the continuous-water midterm into the short gates above.
5. Keep each calculation's terminal state and journal path explicit.
6. Preserve unrelated work; stage only the intended slice.
7. Require science and runtime attacks before a public receipt.
8. Commit and push only after the full local gate and exact scope audit pass.
