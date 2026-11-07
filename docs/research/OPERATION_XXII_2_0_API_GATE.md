# OPERATION XXII §9 — the 2.0 public simulation-API gate

**Status:** gate definition only. **No `2.0.0a1` is cut this round.** This document fixes the smallest installable
simulation interface a 2.0 consumer would depend on, and the promotion criteria every one of which must hold before
any public 2.0 version is tagged. Today the simulator lives under `experiments/` (outside the installable package);
promotion means lifting a *small, stable* surface into `smartchem/` — not renaming the project or exposing arbitrary
experimental internals.

## The minimal consumer surface (what a 2.0 user must be able to do)

A prospective consumer should be able to, through a stable public API:

1. **Declare** typed species (name, composition, charge, phase, substance) and the conserved components.
2. **Build** a reaction network (stoichiometry; `E·N = 0` enforced exactly at construction).
3. **Attach** kinetic laws (from the audited registry) and equilibrium/activity operators.
4. **Define** compartments (control volumes) and attach physically-typed transport boundaries — selective interface,
   electroneutral bulk exchange, external feed/fixed-activity — each refusing an identity-changing or incomplete
   declaration at construction.
5. **Supply** initial inventories and a world temperature (off-domain temperature fails closed).
6. **Run** the simulation through the one generic operator-split integrator.
7. **Inspect** immutable observations (per-compartment species series, authoritative derived pH/ionic-strength).
8. **Inspect** the numerical + scientific receipt (per-component resolution verdict, execution-identity certification,
   external-flux ledger, splitting error, claim tier).
9. **Reproduce** the run from complete model/run/evidence identities.

Every one of these already exists as a *research* capability (`general_kernel`, `general_equilibrium`,
`general_coupled`, `unified_chemical_world`, `general_reactor_demo`); the gate is about which subset becomes a
*supported, versioned contract*.

## Promotion criteria (ALL required before any `2.0.0a1`)

- [ ] A coherent public source package / API (a named module surface in `smartchem/`, not `experiments/` imports).
- [ ] A **versioned schema** for the model/run/observation/receipt wire, with explicit loader dispatch (as the 1.x
      wire already does).
- [ ] **Stable model / run / evidence identities** (the XIX injective digests) as the reproduction contract.
- [ ] **Typed failure contracts** — every refusal is a named, catchable error (CoupledError / StaleCertificateError /
      the resolution + execution-identity tokens), never a bare exception or a silent default.
- [ ] **No false scientific authority** — the claim-tier ladder is exposed, and a prediction never reports a tier its
      weakest premise cannot support (the ASSUMED-kinetics cap, the DEMOTED charge claim, the UNRESOLVED verdict).
- [ ] **Multiple distinct chemistry consumers** driving the same kernel (today: a synthetic reaction-diffusion world,
      the acetate buffer, the vinegar/bicarbonate reactor, the NaCl bulk-exchange world) — generality earned, not
      asserted.
- [ ] A production **compatibility review** (the 1.x contract is untouched; the 2.0 surface is additive and isolated).
- [ ] **Installation / wheel tests** for the new surface across the supported Python matrix.
- [ ] Appropriate **documentation** (a consumer can build and run a world from the docs alone).
- [ ] **Full exact-head CI green**, job-level, on the promotion commit.

## What a 2.0 alpha may and may not claim

A 2.0 alpha may legitimately have a **bounded physical validity domain** (a labeled, narrow regime where its sourced
constants + activity model hold, with every out-of-domain request refused). It may **not** present itself as a fully
calibrated universal chemical model, a fizzing-rate predictor, or a validated-against-measurement simulator — the
NIST/PHREEQC limitations (XXI-4, XXII-6) and the ASSUMED dynamic parameters forbid that claim. **No automatic final
`2.0.0`** follows from this gate; a public alpha is a separate, explicitly-authorized step.
