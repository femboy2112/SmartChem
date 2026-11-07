# OPERATION XXIII Phase II — trust-boundary audit of the 2.0 research kernel

*Research-only. Everything here lives under `experiments/sandbox_foundation/`, which is excluded from the installable
package. Every fix below has a RED example observed on the unfixed code, a GREEN result, a negative control, and a
reproducible receipt.*

## 1. Priority probe — rate-law registration authority (predeclared)

**Predeclared outcomes**, fixed before the first run in `experiments/sandbox_foundation/xxiii_registry_authority_probe.py`:
* **PASS** — untrusted self-registration cannot elevate a class to certified execution without an explicit trusted
  authority boundary.
* **FAIL** — registering the class alone lets the same forged descriptor obtain a certified trajectory.
* **AMBIGUOUS** — the contract intentionally trusts caller registration but does not expose it.

The probe class `Lying` has a `descriptor()` that returns the frozen claim `("Lying", "frozen-claim")`, while
`evaluate()` reads a mutable `secret`. It self-declares the tier `BENCHMARKED_AGAINST_REFERENCE_SOLVER`.

**RED** — the pre-fix kernel, byte-identical to `main` `6a2686e`. Run `python -m experiments.sandbox_foundation.xxiii_registry_authority_probe`:

```
unregistered_certified: false   unregistered_strict: REFUSED          <- the unregistered instance IS demoted
self_registration: ACCEPTED     registered_strict: RAN
registered_certified: true      registered_tier: STRUCTURALLY_CONSERVING   <- tier ROSE from ASSUMED_PARAMETER
mutated_certified: true         certificate_unchanged_after_10x_mutation: true
B_final_before: 0.393469        B_final_after: 0.993262
verdict: FAIL
```

The XXII-2 "audited registry" was a public `set.add`. Its "audit" existed only in a docstring.

**GREEN** — `3ead466`; the same harness run unchanged gives `verdict: PASS`. The authority is now three explicit
tiers:

| authority | how a class gets it | what it buys |
|---|---|---|
| `AUDITED_BUILTIN` | only through the **closed, in-tree** `_AUDITED_BUILTIN_PINS` table: (module, qualname) → sha256 of the reviewed class source. Sealing checks three things: the pin, that the canonical module attribute is that very class, and that `evaluate`/`descriptor` were compiled from the audited lines. | certified execution identity (`execution_identity_basis='AUDITED_BUILTIN'`) |
| `CALLER_ATTESTED_EXTENSION` | `register_attested_rate_law(cls, attested_by=...)` | a **bound** descriptor (mutations of bound parameters still raise `StaleCertificateError`). It is **never** certified: basis `CALLER_ATTESTED`, the tier is floored to UNVERIFIED, and strict mode refuses unless `accept_attested_extensions=True`. The receipt names the attester. |
| `UNVERIFIABLE` | everything else | XXI-2 behaviour, unchanged |

Demoted, with a test for each: a subclass of an audited class, an instance-level `evaluate` override, a post-seal
method swap, a stale pin (the class is demoted and `audit_status()` names the reason), and a spoofed class claiming an
audited name.

**Boundary (pinned by a test so nobody reads it as more).** This is an in-process, trusted-code authority. It is not
cryptographic and not independent validation. Code that writes the private tables, rebinds module attributes or forges
code-object filenames sits inside the trust boundary.

## 2. Red-team findings (directed adversary, then re-run independently by the orchestrator)

A directed adversarial bearing produced five findings. The orchestrator re-ran the first four repro scripts
independently and observed every false claim before any fix. Fixes are on `fix/xxiii-s2b-ledger-integrity`, merged in
`4f2ec70`; there are 26 tests in `experiments/sandbox_foundation/tests/test_xxiii_s2b_ledger_integrity.py`.

| # | false certification (RED, observed) | fix | GREEN (re-run on the merged head) |
|---|---|---|---|
| F1 | Rebinding `ChemicalSystem.reactions` (A→B becomes 2A→2B) ran different kinetics; both certificates were unchanged and the receipt read `AUDITED_BUILTIN` (A_end 0.036788 → 0.090909). | The kernel certificate binds every reaction re-derived from the current list, and `_verify_certificate` re-derives N (`66827c6`). | `StaleCertificateError` on both the kernel and coupled paths. |
| F2 | `include_ion_pair` on the equilibrium operator sat outside the certificate. Two different worlds shared one certificate, and a toggle ran different physics while certified. | Every in-tree operator has a `descriptor()` binding its solve parameters. An operator without one makes the world's execution identity UNVERIFIED (`6e75fe6`). | Distinct certificates; the toggle raises `StaleCertificateError`. |
| F3 | A single-species charged `InterfaceTransfer` left the cells at ±0.4908 mol while `charge_balance_claim` read `CONSERVED`. | A per-compartment charge-separation verifier judges charge moved by the run against the compartment's ionic inventory (`bb56196`). | `GLOBAL_ONLY_LOCAL_VIOLATED`, tier `REFUSED`, and a caveat on the charged interface. |
| F4 | The ledger baseline was taken after the t=0 projection, so a lossy projection deleted a 5e-10 mol trace and the run was certified `VERIFIED_WITHIN_RESOLUTION`. | The baseline is the declared pre-projection state, judged per component (`15532bb`). | `VIOLATED`, `material_balance_closed False`, tier `REFUSED`. |
| F5 | (safe direction) A neutral multivalent system was refused `NUMERICALLY_UNRESOLVED` because the charge scale was \|net\| ≈ 3e-17. | The charge resolution scale is the ionic inventory Σ\|z n\| (`cbcc672`). | `VERIFIED_WITHIN_RESOLUTION`; a genuine 1e-4 mol leak is still `VIOLATED`. |

**Deliberate design decisions** (accepted by the orchestrator):
* F3 judges the charge the run **moves**, not the absolute charge. A caller-seeded non-neutral compartment gets a
  caveat, not a refusal (an existing XXII-7 test seeds bare bicarbonate on purpose).
* F4 keeps the implicit-solvent components (H, O and charge under a fast equilibrium) reporting from the equilibrated
  start.

**Still open**:
* **(F2-gap)** A user equilibrium operator with a self-defined but dishonest `descriptor()` is still trusted. This is
  the operator-side twin of XXIII-2. The fix is to extend the closed audit table to operators.
* **(p6b)** The positivity floor scales with the caller's atol.
* **(kernel-path)** The single-system `ChemicalSystem.integrate` has no local-charge check.
* **Adversary residue, CONJECTURED, not exploited:**
  * `CoupledWorld._Eg` is writable;
  * the stitch budget is sized by the largest species;
  * the feed ledger shares its integrator with the inventory, so it proves bookkeeping, not accuracy;
  * a trace species sharing an element with a bulk species has no separate conservation check.

What the adversary attacked and could **not** break: bulk-roster completeness (7 species including ±3 ions, volume
ratio 5000:1, Q up to 1e9 L/s, traces down to 3e-13 mol, and same-name / different-identity collisions), certificate
rebinds of species/volume/temperature/interfaces/boundaries/Q/species tables, signed flux cancellation, positivity
under loose tolerances, and unreported phase-stitch clamps.

## 3. Two drifting no-tune guards (found while re-running the sandbox suite)

`test_xx_s5_unit_convention::test_no_model_constant_was_touched` and
`test_xxi_s4_three_comparators::test_no_model_constant_was_touched` compared a historical base against the **working
tree**, including `smartchem/`. The legitimate 1.6.0 change therefore failed them on `main` `6a2686e`, reproduced
locally. Hosted CI skipped them, because its shallow checkout lacks the base SHA, so the guards ran only where they
were wrong.

Both were bounded to their own ranges (`c811a77`). `git diff 0d2ab65 676bcfc` and `git diff 774429e 07afeff` over the
model files plus `smartchem/` are both empty, so the historical "tuned nothing" claims are permanent. A separate
forward guard keeps the carbonate model files frozen.
