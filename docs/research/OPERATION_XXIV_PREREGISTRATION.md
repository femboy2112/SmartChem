# OPERATION XXIV: preregistration of the Phase I/II P0 probes

**Status:** committed BEFORE any XXIV repair. The parent commit is `main` `7314e2a44157b27e27a528a0c4bd4efbcb7fb84c`.

**Harness:** `experiments/sandbox_foundation/xxiv_p0_probes.py`. It is version-agnostic: the same file runs on the pre-fix kernel and on the repaired kernel.

**RED receipt:** `experiments/sandbox_foundation/benchmarks/p0_xxiv/RED_receipt_7314e2a.json` (all five verdicts FAIL, see below).

**Command:**

```
PYTHONPATH=. python -m experiments.sandbox_foundation.xxiv_p0_probes
```

**Toolchain:** CPython 3.12.3, numpy 2.5.1, scipy 1.18.0.

The verdict rules below were fixed before the first run. They live in the harness docstring and in the code of each `probe_*` function. The repair must turn each FAIL into PASS **without editing these rules**. Any later harness change will be listed in the "Harness changes" section with its reason.

## Predeclared outcomes

| probe | PASS | FAIL | AMBIGUOUS |
|---|---|---|---|
| **P1 F2-gap** (equilibrium-operator authority) | A caller-defined operator whose own `descriptor()` omits an operative `speciate` parameter gets no certified execution identity, and strict certified execution refuses it. This must hold on a one-compartment world AND on a two-compartment transport world. | It obtains a certified identity: two worlds with different physics share one certificate and both run strict with `execution_identity_certified=True`. | It is not certified, but the receipt does not name the operator. |
| **P2 p6b** (caller-controlled positivity floor) | For every requested `atol`, a trajectory that conserves against its signed feed ledger but reaches a macroscopic negative inventory (≤ −0.2 mol of a 2 mol species) never gets `positivity_held=True` + `STRUCTURALLY_CONSERVING` with no resolution flag. This must hold on the coupled path AND the single-system kernel path. The non-negative controls stay conserving. | Some `atol` gives that unqualified strong verdict on some path. | The strong tier survives, but only with a resolution flag or caveat. |
| **P3 charge** (kernel vs one-compartment vs two-compartment) | Every path returns one shared typed charge-validity verdict that separates three things: reaction charge conservation (E_q N = 0), accounting of externally supplied charge, and bulk electroneutrality. An unbalanced charged feed is never "physically supported"; the neutral controls are. | Some path gives an unqualified admissible result for net charge injected with no counter-ion or electrode. | No path falsely admits, but the paths do not share a typed verdict. |
| **P4 closure** (dependency closure of audited rate-law pins) | A source edit to a module-level helper that an audited law's `descriptor()` executes either demotes the law or cannot make two physically different worlds share a certificate. | After the helper edit the law is still SEALED, two worlds with different Ksp share one certificate, and their trajectories differ. | It stays sealed and the certificate collides, but the trajectories coincide. |
| **P5 temperature** (source-domain transport of a 25 °C Ksp) | The world at the constant's sourced temperature runs. A 350 K world is refused, or demoted with a typed source-domain reason, on the coupled AND kernel paths. | The 350 K world runs the 25 °C constant certified, with no domain flag. | It runs with a caveat, but the tier is not demoted. |

P4 also carries a control: an edit **inside** the pinned class body must demote the class on every commit.

## RED receipt on `7314e2a` (all FAIL)

- **P1:**
  - The two worlds (frac 0.2 and 0.8) share one world certificate, yet their final X1 is 0.2 vs 0.8 mol.
  - Both receipts read `execution_identity_basis='AUDITED_BUILTIN'` and `certified=True`, and both run strict.
  - A post-construction `op.frac = 0.9` runs certified.
  - All of this holds on both topologies.
- **P2:**
  - Coupled path, `atol=1e-2`: `min_inventory=-0.5`, `positivity_held=True`, resolution flag False, `STRUCTURALLY_CONSERVING`.
  - Kernel path, `atol=1e-1`: the same.
  - With tighter `atol` both paths REFUSE. The floor is therefore caller-controlled (`pos_tol = max(atol*100, 1e-10)` coupled, `max(atol*10, 1e-12)` kernel).
- **P3:**
  - Kernel path, unbalanced Na⁺ feed: `STRUCTURALLY_CONSERVING`, with no charge field at all.
  - Coupled one-compartment unbalanced feed: REFUSED, but labelled `GLOBAL_ONLY_LOCAL_VIOLATED`. That is a transport-separation label applied to an external-supply cause.
  - No shared typed verdict exists on any path.
- **P4:**
  - Changing `_constant_key` so it no longer binds `c.value` leaves `ActivitySolubilityRate` SEALED.
  - Worlds with Ksp 1e-6 and 4e-6 then share one world certificate (both `certified=True`), while final [M+] is 1.037e-3 vs 2.104e-3 mol.
  - Control: an edit inside the class body demotes it (`source sha256 … != audited pin`).
- **P5:** at 350 K both paths run the 25 °C Ksp, producing an identical trajectory (final [M+] 1.0368606e-3 mol). The coupled run stays certified and neither path reports a domain field.

## Harness changes after the first run

- **P4 child.** The first run had the child integrate with `require_certified_execution=True`. In the CONTROL arm the demoted law was correctly refused, which crashed the child before it could report `audit_status`. The child now reads `audit_status()` first and integrates without strict mode. The verdict rules are unchanged; only the control's reporting path changed.
  - The demotion was already visible in the first run's error text.
  - The committed RED receipt is from the second run.

## Phase III preregistrations

These are separate dated sections, appended by later commits BEFORE their evaluation runs.
