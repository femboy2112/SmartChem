# OPERATION XIX — consolidate the universe (the road to 2.0-alpha)

**Date:** 2026-11-02. **Branch:** `research/unified-world-xix` (off the XVIII head `9311526`); consolidated onto
`integration/2.0-alpha`. **Status:** research + integration. ⛔ Nothing wired into `smartchem/`, nothing merged to
protected `main`, nothing tagged or published. Every claim inherits its weakest premise; a reference-solver
comparison is not a measured validation, and a green research branch is not a release.

OPERATION XVIII built the first unified solid–liquid–gas chemical world. XIX makes it **scientifically honest and
coherently integrated**: it closes the new P0 correctness holes, pays down one unit of the measured-evidence debt,
makes the categorical layer executable, and consolidates the 2.0 research stack onto one reviewable integration
branch — without inflating any claim.

---

## A. Git graph & exact SHAs

```
main 9e8fa5f  v1.1.0  (RELEASED)
  └─ #134 → #142 → #150(dc87979) → #152(f5eb2b0) → #153(59c3143) → #154 XVIII(9311526)
                                                                      └─ XIX research/unified-world-xix:
        1a74ac3  Track A P0 core      (1C temperature, 1D world cert, 1B derived scalars)
        b512565  Track A P0 flagship  (1A identity, 1B activity-pH frame, 1C off-25C refusal, 1E phase stitch)
        e0b61f4  §4 measured rung     (carbonate vs NIST SRM 191d, blind, within U)
        0ed9f04  §5 categorical bridge (OpenChemDiagram → kernel ChemicalSystem)
        <docs>   §8 roadmap + this dossier

integration/2.0-alpha  7be045c (+re-merge of the XIX head)
  = main 9e8fa5f  ⊕(--no-ff)  research/unified-world-xix   — ONE merge, full ancestry, no cherry-picks

Production/compiler line (separate, unchanged by this operation):
  main 9e8fa5f ── #149 integration/v1.5-candidate (61d91aa, 24 classes) ── #151 feat/lactonization-exhaustiveness (38e9186, 25th class, DRAFT)
```

Ancestry verified by `merge-base --is-ancestor`, not by name: `9e8fa5f`, `dc87979`, `f5eb2b0`, `59c3143`, `9311526`
are all ancestors of the XIX head.

## B. Merge ledger — what merged where, and what did NOT

| action | where | authority |
|---|---|---|
| XIX Track A / §4 / §5 / docs commits | `research/unified-world-xix` (research) | development work |
| `--no-ff` merge of the XIX head | `integration/2.0-alpha` (new staging branch off `main`) | **authorized** integration-branch dev work |
| **NOT** merged to `main` | 1.5 (#149), the 25th class (#151), the 2.0 stack | **requires explicit maintainer sign-off** |
| **NOT** tagged / published / force-pushed | anything | requires separate authorization |
| **NOT** modified | `smartchem/` (0-file diff vs `main`), LibGibson | untouched by design |

## C. Bug ledger — OPERATION XIX Track A (each reproduced RED first, then repaired, then pinned)

| id | defect (confirmed from source) | repair | evidence |
|---|---|---|---|
| **1A** | `world_identity_digest(params, phases)` did not bind the initial inventories → two runs (acid 0.5 vs 1.0) returned the IDENTICAL `model_run_digest` `2f82c736…` over different IVPs; the equilibrium K-set was also unbound. | split MODEL / RUN / EVIDENCE identity; run digest binds inventories + schedule + solver config; model digest binds the full species keys + Ka/K1/K2/Kw; lossless `float.hex()`. | run digest now varies per inventory; model digest invariant under inventory, moves with a rate coefficient. |
| **1B** | `_ph_of_cell` recomputed concentration pH `−log10[H+]` and the frame reported it under a plain `pH` label while the model is Davies-based (a 0.13 pH error: activity 5.08 vs concentration 4.95). | `_project` now returns the solver's authoritative derived scalars; the trajectory carries them per sample; the frame reports the activity pH with BOTH conventions + ionic strength + model labelled. | frame `pH_B == pH_B_activity`; activity ≠ concentration; `pH_concentration == −log10[H+]` cross-check. |
| **1C** | `CoupledWorld._project` hard-coded `T=298.15`, so a world with gas physics at `params.temperature_K` solved its equilibria at 25 °C (mixed-temperature). | one first-class `temperature_K` threaded into every projection; the 25 °C-only operator fail-closes off-domain (`OutOfSourceDomainError`); the flagship refuses off-25 °C up front (K-set, Henry constant AND Qsp are all 25 °C-sourced). | 310 K world refused at core + flagship. |
| **1D** | the coupled path consumed compartment N / rate-laws / interfaces / boundaries directly, bypassing the single-compartment stale-certificate guard (XVIII-2). | a WORLD execution certificate snapshotted at construction (each compartment's kernel cert + species order + volume + operator identity + every interface/boundary descriptor + temperature), re-verified at `integrate()` (plus each system's own cert). | boundary-append, interface-append, N-rebind, compartment-swap all raise `StaleCertificateError`; unmutated world integrates. |
| **1E** | the phase-stitch `max(0.0, v)` silently clipped any negative; `simulate` validated no input. | `_restitch` records a bounded, scale-aware roundoff clamp (per-phase + whole-run totals) and REFUSES a negative beyond budget as a real excursion; `simulate` validates a non-empty schedule, duration > 0, integer n_steps ≥ 1, finite ≥ 0 inventories, finite/positive params. | dust clamped + logged (≈1.6e-14); empty/zero/negative inputs refused; a real excursion flagged. |

**Verification:** OOM-safe sandbox suite **884/884** at the integration merge commit (two runs); ruff clean on all
changed files; all result JSON strict (`allow_nan=False`).

## D. §4 — the first MEASURED-validation rung (NIST SRM 191d)

A **blind, zero-parameter** prediction of the repo carbonate closed-system solver vs a certified **Harned-cell emf**
measurement (not another solver):

| model | pH(activity) | vs certified 10.014 | within U (±0.010)? |
|---|---|---|---|
| **Davies** | **10.0048** | **−0.009** | **yes** |
| ideal (control) | 10.323 | +0.309 | no |

Source read directly from the certificate (NIST SRM 191d, 05 Feb 2025; SHA256 `ea316fb1…`). **Partial common-mode**,
stated up front: our K1/K2 are Harned-lineage and Davies shares the Debye–Hückel family with the certificate's
Bates–Guggenheim convention (the certificate's dominant uncertainty, 0.0050 pH). So this corroborates *"K2 + Davies
reproduce a Harned-cell result to within its uncertainty"* — the first rung ABOVE reference-solver corroboration,
**not** an independent derivation of K2. Harness + preregistration + README committed under
`experiments/sandbox_foundation/benchmarks/measured_carbonate_srm191d/`. Access gaps (acetate pH, CO₂ kLa,
NaHCO₃ solubility) established exactly, not fabricated.

## E. §5 — executable categorical composition

`experiments/sandbox_foundation/open_diagram_bridge.py`: `bridge_to_kernel(OpenChemDiagram) → ChemicalSystem`, built
to be trusted LESS than the diagram. One Species per registry entry, `substance` **minted** from the Molecule's
state-stripped `resonance_identity` (CO₂(aq)/CO₂(g) share a substance; ethanol/DME do not — closing the
`InterfaceTransfer` caller-string hole). One Reaction per internal hyperedge. The kernel re-proves `E·N=0` in
unbounded ints; the diagram's decoration is only CROSS-CHECKED (decoration net == column-summed E·N; N·1 == net
reaction). Fail-closed on unsaturated / empty-or-duplicate id / net-zero / unmappable-state / isomer-collision /
contradicting-override. Demo: CH₃COOH + HCO₃⁻ → CH₃COO⁻ + H₂CO₃ glued at H₂CO₃ to H₂CO₃ → CO₂ + H₂O, bridging to
6 species / 2 reactions with E·N = 0. 31 pin-tests.

### Composition-law status
| law | status |
|---|---|
| `E·N = 0` (kernel re-proved at construction) | **enforced** (demo + unbounded-int check) |
| decoration net == column-summed E·N; N·1 == net reaction | **enforced** (cross-checked; forged decoration refused) |
| identity / associativity of composition | tested at the quotient level (pre-existing) |
| gluing-invariance of the bridged system | **tested** (glued/tensor/unglued → same kernel signature) |
| rejection of isomer-changing passive interface | **tested** (ethanol/DME refused; CO₂(aq)↔CO₂(g) admitted) |
| equilibrium projection `C(P(n))=C(n)` | enforced by `_admit_projection` (XVI); `P(P(n))≈P(n)` tested for acetate only |
| diagram-level equilibrium / Δ_rG functor | **unproven** (the categorical layer has no thermodynamic notion) |

## F. §2 — conservation & evidence contract (honest status)

- **Checked throughout the trajectory (2A, partial):** the signed external-flux ledger checks `Δ(E·n) = E·∫q_ext`
  at the macro-step level already (XVIII-3); the whole-run balance is a step-count-independent identity. An explicit
  per-recorded-state residual series in the receipt (to catch a transient creation that later cancels) remains a
  clean next addition.
- **Charge (2B):** the flagship world is **charge-safe by construction** — the valve passes only neutral HAc/CO₂,
  Henry moves neutral CO₂, dissolution is `NaHCO₃(s)→Na⁺+HCO₃⁻` (net 0), the export boundary moves neutral CO₂(g);
  no operation sources net charge, so global net charge is invariant (= 0). It is still **DEMOTED** because the
  per-cell H⁺/OH⁻ split rests on the equilibrium operator's implicit-water electroneutrality assumption. The clean
  upgrade: an INDEPENDENT global-neutrality assertion (the kernel charge row stays at its initial value within tol),
  separating the *checkable* global invariant from the *assumed* single-ion split. Scoped, not yet implemented.
- **Per-operator evidence (2C, partial):** `evidence_identity` now records per-parameter tiers (k_diss/kLa/k_export
  ASSUMED, Qsp empirical, KH/K-set sourced, external-validation status) as a separate digest. A fully multidimensional
  per-frame receipt is the next step.
- **Positivity under solid exhaustion (2D, partial):** `_restitch` records + bounds the stitch clamp and refuses a
  real excursion; the integrator's per-step positivity is measured. An inventory-constrained dissolution extent
  (rather than clamp-after) remains the stronger method.

## G. §3 — PHREEQC model-debt (status)

The XVIII benchmark's divergences localize (per the XIX recon) to the omitted Na-cation ion pairing at high sodium.
The carbonate base model has no Na-carbonate pair (only the acetate model carries the opt-in NaAc pair). The SRM 191d
rung (§D) already lands within the measured band WITHOUT the carbonate pair, so the pair is a refinement, not a
rescue. The controlled ablation (add a sourced NaCO₃⁻/NaHCO₃⁰ association constant; re-run with/without; fresh
holdout) is the registered next probe — not performed this round.

## G′. Generality (unchanged kernel across chemistries)
One unchanged general kernel + operator-split integrator runs: acetate buffer; mixed acetate/carbonate; ammonia base
buffer + stripping; the unified solid/liquid/gas vinegar/bicarbonate world; and now any bridged OpenChemDiagram. Zero
chemistry branches in the integrator.

## H. Runnable outputs
```
python -m experiments.sandbox_foundation.unified_chemical_world [--scenario …] [--json OUT] [--csv OUT]
python -m experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d.run_measured
python -m experiments.sandbox_foundation.open_diagram_bridge
```
Strict JSON + CSV; declared physical limitations in every result's `assumptions` / `evidence_identity`.

## I. Release-readiness matrix

| rung | state |
|---|---|
| 1.1 | **RELEASED** (`v1.1.0`, `9e8fa5f`) |
| 1.5 (24 classes, #149) | **release candidate — Option A recommended**; CI 7/7 green on `61d91aa`; awaiting maintainer sign-off for the protected-main merge + tag |
| 25th-class feature (#151) | **review-only**, DRAFT, held for 1.6 |
| 2.0-alpha integration (`integration/2.0-alpha`) | **research integration**, sandbox 884/884, package byte-identical to 1.1.0; NOT a release |
| 2.0 predictive validation | **one** measured rung (SRM 191d, within U, partial common-mode); otherwise solver/structure corroboration |
| 3.0 | ambition (LibGibson downstream observer) |

### §6 — the 1.5 release verdict (maintainer-ready)
**Recommend Option A: release 1.5 with the 24 classes; hold the 25th class (#151) for 1.6.** Rationale: #149 is
review-ready (not draft), its final-SHA hosted CI is 7/7 green (run `41198440406`), and its gate evidence is recorded
(OOM suite 8127/0/0/50, frozen wire-contract, version-independent semantic golden, DAG admission/replay, false-VOUCH
corpus — per the 1.5 program docs). #151 is still DRAFT, introduces its own schema/registry transition, and a prior
audit flagged a MEDIUM common-mode fragility in its recognizer; folding it in would re-open every gate and delay an
otherwise-ready release for no proportionate gain. **Remaining maintainer sign-offs (not automatable):** the
protected-`main` merge of #149, the `v1.5.0` tag, and any publication. Do NOT merge the 25th class silently.

## J. Next three verdict-changing probes (prioritized, not a wish list)
1. **Carbonate Na-ion-pairing ablation** (closes both §3 high-Na divergence and the §4 residual): add a sourced
   NaCO₃⁻/NaHCO₃⁰ association constant as an opt-in refinement, re-run the SRM 191d rung + the PHREEQC cases
   with/without, and a fresh preregistered holdout — does it move the residual toward 10.014 without breaking the
   agreement domain?
2. **Independent global-charge-neutrality assertion** (§2B): verify the world's kernel charge row stays at its initial
   value within tol, upgrading the charge claim from "DEMOTED (operator assumption)" to "global neutrality
   independently checked; single-ion split assumed."
3. **A second reachable measured rung** — pull the IUPAC-2002 / Partanen-Covington acetate buffer pH tables (a human
   browser can fetch the IUPAC PDF the automated clients were 403'd from) to give the acetate chemistry its own
   blind-prediction check, and widen the measured regime beyond the single carbonate point.
```
