# SmartChem finite resistive-DC E1 round — release record

**Base:** `6087c9dfddba4361b09aa2a8e49b92a9ee4bdae3`
**Branch:** `main`
**Date:** 2026-07-27/28 (America/New_York)
**Decision:** `SHIP` for the declared E1 mathematical regime only

## Governing boundary

This round implements the first semantic interpreter over the exact finite open-diagram
syntax. It admits finite positive ideal resistors, one exact-rational ideal-voltage drive,
one declared reference boundary, an exact passive boundary relation, and a binary64 sparse
modified-nodal-analysis witness.

It does **not** establish a physical device, component tolerances, grounding or safety,
forward accuracy for arbitrarily ill-conditioned systems, AC/RLC or transient behaviour,
thermal/noise/failure physics, active or nonlinear devices, distributed fields, general
circuit simulation, port-Hamiltonian composition, or a general multiphysics language.

The scientist-approved output contract remains complete: structural and
resistance-decorated canonical forms, the model-to-structural-edge witness, every exact
relation row, every node/branch/source value, all production diagnostics, and the complete
direct-verification report. No scalar equivalent resistance replaces those outputs.

## Remote-branch decision

`origin/agent/smartchem-open-semantics-round-20260727` at `fdb906f` was inspected but not
merged. Its E1 completion gate reused production analysis, so it remains historical
`NO-SHIP`. Only the already-shipped S0 topology work derived selectively from that line.
The E1 implementation and receipt in this round were built and executed anew.

## Implemented seam

- `smartchem/resistive_dc_schema.py` owns shared immutable nominal records and exact
  linear-relation algebra. It owns no sparse solve, compiled executor, or direct physics
  verifier.
- `smartchem/circuit.py` owns exact network black-boxing and the one topology-generic
  COO-to-CSC sparse-MNA path.
- `smartchem/resistive_dc.py` owns the closed compiled lifecycle and its exact four-output
  contract.
- `smartchem/resistive_dc_verifier.py` imports neither production circuit nor executor
  code. It independently eliminates the rational boundary relation and recomputes
  canonical content, inventory, Ohm law, KCL, source constraint, power, passivity, and
  all eight diagnostics.
- `smartchem/open_diagram.py` exposes a stable structural-edge view; the explicit finite
  reindex witness prevents model tuple order from being treated as topology identity.
- The closed registry now contains eight executors. Its semantic digest is
  `b1ff8c0f89e279b923513404a39eb87aa305f3fa0941a64267e8bc51b1b7393a`.
- The frozen shipped-source compiler digest is
  `9b265acd7051d1e174f5b41c05c85fd0602bc71cf2f3fc457367eb7c9f0c1512`.

The initial E1 size sketch was exceeded: schema, production relation/MNA, lifecycle, and
the intentionally separate direct verifier total about 2,590 source lines, with about
1,295 focused test lines. The cost is principally complete-output lifecycle logic and
non-common-mode verification. It is explicit complexity debt; E2 should reuse these
boundaries rather than duplicate them.

## Falsifying probes and repairs

Independent reviewers repeatedly returned `NO-SHIP` until these concrete holes were
closed:

1. Production postconditions and payload checks that repeated production analysis were
   rejected in favor of a separately implemented verifier.
2. Canonical forms, presentation binding, edge reindexing, and every retained diagnostic
   gained direct content/equality checks.
3. Dynamically created dataclasses with genuine module/name strings could spoof nominal
   checks. Shared schema class identity plus recursive exact checks now reject forged
   analysis, relation, result, binding, model, experiment, drive, rational, resistance,
   and branch-resistance records.
4. An engine could replace the approved model with a coherent doubled-resistance model.
   A pre-backend execution-admission snapshot now binds plan, approval, resolved subject,
   calculation, and compiler identities. All eight runners recheck it after successful
   and exceptional backend callbacks, after post-call calculation-spec reads, and
   immediately before certification. Drift is `INVALID`, with no result/certificate and
   quarantined retained artifacts.
5. A coherent 11 V production result plus false relation against the approved 10 V
   subject is rejected by the untouched direct verifier.

Additional controls include analytic single/series/parallel cases, bridge and cycle
topologies through one stamping path, a nonidentity reindex witness, 64 deterministic
connected multigraphs at seed `20260727`, floating/singular/nonfinite/refusal paths,
production-disabled verifier execution, output-family mutations, and mutation-then-raise
callbacks.

Final read-only review passes from two independent reviewers returned `SHIP` for the
numerical/semantic E1 boundary, adversarial nominal/input integrity, and the shared
cross-executor execution-admission gate. Their verdict is bounded by the regime above,
not a theorem over arbitrary Python attackers or arbitrary circuits.

## Verification

Both maintained no-slow-test entrypoints passed on the frozen source:

```text
.venv/bin/python -m pytest -q -rs
1434 passed, 14 skipped, 1 xfailed

.venv/bin/pytest -q -rs
1434 passed, 14 skipped, 1 xfailed
```

The 14 explicitly slow real-oracle tests were not run and are not represented as passing.
The one expected failure is the known true-parallel-interchange architecture debt.

Additional gates:

```text
focused lifecycle/admission matrix: 222 passed
resistive verifier under both pytest entrypoints: 42 passed + 42 passed
python -m compileall -q smartchem experiments tests: pass
git diff --check: pass
public exports: 331, all unique and resolvable
closed executors: 8
```

Post-push GitHub Actions run
[`30329968359`](https://github.com/femboy2112/SmartChem/actions/runs/30329968359)
completed successfully for source commit
`b43c77744343defe028abb441e0e465a9316e2cb`: Python 3.10, Python 3.12, and
the optional PySCF discovery/real-calculation/fast-suite/benchmark job all passed.
The conditional manual real-wavefunction geometry integration step was skipped by the
workflow and is not represented as executed.

The first broad suite attempt was deliberately interrupted at 90% when the host was
actively swapping under unrelated multi-gigabyte workloads. It is not counted as a
completed gate. The two completed runs above were performed later with one test process at
a time and adequate memory headroom.

## Calculation ledger

The authoritative write-once E1 run is:

| Field | Value |
|---|---|
| status | `COMPLETE` |
| run | `253854ae0cb443f4abab86d0d009e90a` |
| journal | `/tmp/smartchem-e1-release.EidAwH/run.json` |
| started | `2026-07-28T04:46:12.553364+00:00` |
| ended | `2026-07-28T04:46:12.655526+00:00` |
| engine calls | `1` |
| artifacts/checkpoints/obligations | `8 / 1 / 6` |
| failures | none |
| receipt | `experiments/RESULTS_compiled_resistive_dc.md` |

The bridge relation is exactly

```text
V_input - V_output + (7750/37) I_inward_output = 0
I_inward_input + I_inward_output = 0
```

All direct gates passed. The largest scaled residual was the KCL value
`4.360250899076838e-16`, far below the approved `1e-9` tolerance and the verifier's
stricter certification margin. The receipt retains the complete numerical fields and
artifact digests.

The older cold chemistry benchmark formerly tracked as PID `151446` is gone. It had no
journal, stdout capture, recovered exit code, or final report. Its correct state is
**terminal-unclassified**; it is not `COMPLETE`, `INCOMPLETE`, or publishable timing
evidence. No calculation is now in progress.

## Next roadmap cut

- **Short term:** E1 and the shared execution-admission gate are complete; maintain the
  exact output/no-silent-reduction contract and keep source-bound receipts reproducible.
- **Best-shot midterm:** positive-frequency passive AC/RLC E2—finite `omega > 0`,
  phasor branch values, complex power, positive-real/passivity checks, damped resonance,
  and explicit refusal of ideal lossless singular resonance.
- **Other midterm:** bounded dispersive water then regime-matched measurement; empirical
  survival only with independent data authority/validation; traffic kinematic waves as
  the next regime-valid metaphor; remaining Class-A reuse/planning slices.
- **Long term:** layered `StructureIR`/`ModelIR`/`EvidenceIR`/`ExecutionDAG`, verified
  cross-domain/cross-scale transports and assemblies, broader physics verticals, then a
  conversational surface that asks and explains without inventing meaning or validity.

Port-Hamiltonian composition stays after E2 and after dynamic state plus an explicit,
verified effort/flow power pairing exist.
