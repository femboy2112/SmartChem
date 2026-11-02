# Operation SmartChem XIV — P0 scientific repairs + the general chemical-system carrier (2.0 research track)

**Date:** 2026-10-31. **Branch:** `research/physical-vinegar-xiii` (off #142 → #134 → released `main` `9e8fa5f`), PR #150
(draft, research). **Separate from** the production lactonization track (that is on `feat/lactonization-exhaustiveness`,
PR #151 — see `OPERATION_SMARTCHEM_XIV_LACTONIZATION_2026-10-31.md`). All work in `experiments/sandbox_foundation/`.
**Nothing merged, tagged, or published.** This is research-grade 2.0, outside the stable 1.x contract.

This round (a) repaired the three load-bearing numerical/scientific defects the external audit flagged, and (b) built
the general chemical-system carrier — a reusable kernel in which vinegar+bicarbonate is ONE declared system among
many, proven by running two UNRELATED chemistries through the same integrator with no solver edit.

---

## B. Bug verdicts (plan section 1 — reproduced / repaired)

| defect | verdict | repair |
|---|---|---|
| **1A** open-boundary carbon ledger has wrong units (`exported_carbon_mol = -C_C`, mol/L assigned to a mol field) | **REPRODUCED → REPAIRED** | open-mode `exported_carbon_mol` is now `None` (UNKNOWN: an instantaneous fixed-P_CO2 equilibrium does not identify a cumulative mole transfer without a volume + initial inventory). Added `open_boundary_carbon_ledger(result, volume_L, initial_carbon_mol)` → moles (`mol/L × L`), enforcing `internal_after − internal_before = −exported`. closed/sealed stay a measured `0.0`. |
| **1B** `Ksp = S²` disguised as a transferable thermodynamic solubility product | **REPRODUCED → REPAIRED (fallback path)** | re-framed as an EMPIRICAL ion-CONCENTRATION product (not an activity-based Ksp), valid only in the dilute regime S was measured in; an ionic-strength applicability guard DEMOTES the saturation tier to UNVERIFIED outside the Davies domain, independent of activity_model — so it can never present a source-validated out-of-domain prediction. (At saturation ~1.2 M the claim is honestly UNVERIFIED; conservation + the SI=1 bound still hold.) |
| **1C** RK45 described as "stiff-capable"; positivity clamp could hide an invalid excursion | **REPRODUCED → REPAIRED** | corrected the docstring (RK45 is explicit/non-stiff-stable); added a `method` param (BDF/Radau/LSODA for stiff regimes); measure the RAW pre-clamp negative excursion + overshoot and report them SEPARATELY on the Trajectory (a clamped violation is MEASURED, never hidden) + a caveat when they exceed tolerance; added `stiffness_stress()` comparing explicit vs implicit integrators, reporting success / excursions / conservation residual / failures per method. |

## C. Generality verdict (plan section 16.C — which distinct chemistries run on the SAME kernel)

`general_kernel.py` provides typed `Species` (identity = name + composition + charge + phase, never formula alone),
`Reaction` (signed stoichiometry + rate law), and `ChemicalSystem` (builds the stoichiometric matrix `N` and the
element-charge matrix `E`, proves `E N = 0` exactly at construction). The generic integrator evolves
`dn/dt = N r(n) + q`. **Two unrelated chemistries run through the same `ChemicalSystem.integrate` with NO solver
edit** (`general_chemistry_demo.py`):

- **Consumer B** — a synthetic `A⇌B, B+C→D` network (no acetate / CO2 / sodium anywhere): conserves components X, Y
  to ~1e-13, limiting reagent and reversible equilibrium (`[B]/[A] = kf/kr`) correct.
- **Consumer C** — a weak-acid dissociation `HA ⇌ H⁺ + A⁻` whose kinetic fixed point matches the ANALYTIC weak-acid
  equilibrium to <1e-3, with charge balance `[H⁺] = [A⁻]` and elements+charge conserved to machine zero.

The architectural gate is MET (the kernel imports no species-specific constant; the same bound method runs both).

## D. Mathematical invariants (executable, not prose)

1. `E N = 0` — every reaction conserves every element AND charge; checked EXACTLY (integer arithmetic) at
   construction; an unbalanced OR charge-imbalanced reaction is REFUSED (`ConservationError`).
2. Closed-system conservation — with `q = 0`, `E n` is invariant along the trajectory (verified; drift < 1e-9).
3. External ledger — with `q ≠ 0`, the conserved totals change by exactly `∫ E q dt` (tested: total = feed × time).
4. Positivity — reported (`min_amount`); a negative excursion raises a caveat, never silent.
5. Fail-closed missing data — `RATE_UNKNOWN` ⇒ `integrate()` refuses (`MissingKineticsError`); never a silent k=0.
6. Detailed balance — a reversible reaction's `kf/kr` IS its (inventory-space) equilibrium constant; it relaxes to it.

## E. Scientific claims (kept distinct)
Formal conservation (CERTIFIED by `E N = 0`) · numerical verification (solver success + conservation drift +
analytic cross-check for the weak acid) · sourced thermodynamics (the weak acid's `kf/kr` encodes a sourced Ka; the
synthetic network's rates are DECLARED) · assumed kinetics (all rates are ASSUMED/synthetic, never measured) ·
measured validation (**UNAVAILABLE** — none used or fabricated). These are reported per-facet in the demo frames.

## F. Working demonstration
`python -m experiments.sandbox_foundation.general_chemistry_demo [--json OUT --csv OUT --scenario synthetic|weak_acid]`
emits strict-JSON frames (no NaN/Infinity), a CSV time series, a terminal dashboard, and a deterministic model digest.
A quantity the model does not supply is null; conservation and positivity are reported as verified numerical facts.

## G. External verification (PHREEQC) — the load-bearing debt, UNRESOLVED
PHREEQC is **ABSENT** on this box (confirmed 2026-10-31: `command not found`, no `phreeqpython`, no database dirs).
Operation XIII's 22 preregistered mixed `.pqi` decks remain committed with a null reference column
(`EXTERNAL_VALIDATION_UNAVAILABLE`); **no reference numbers are fabricated**. Running them needs an isolated scratch
environment with PHREEQC + `minteq.v4.dat`/`llnl.dat` and pinned DB sha256s — the smallest decisive next experiment
for the mixed benchmark. Independent high-precision numerical controls (the `decimal` holdout) continue in parallel;
that is solver VERIFICATION of the equations, never measured validation of the constants.

## I. Release status (not conflated)
1.1.0 published (`main` `9e8fa5f`) · 1.5 candidate PR #149 (undisturbed; the lactonization recognizer is its own PR
#151 stack) · **2.0 experimental** = THIS track (P0-hardened numerics + a general kernel with ≥2 consumers;
research-grade, experimental schema) · 2.0 calibrated predictive domain = NONE (no PHREEQC run, no measured
calibration) · 3.0 falling-sand = the renderer-neutral frame remains the LibGibson seam.

## J. Remaining blockers / the smallest decisive next experiments (honest scope-forward)
- **Consumer A (acetate/carbonate through the kernel) + the integrated solid–liquid–gas–two-cell flagship (Track C)**
  need an ALGEBRAIC fast-equilibrium projection (`g(n)=0`) attached to the kernel — the acetate/carbonate system is an
  equilibrium system, not a kinetic one, so it does not fit the kinetic integrator as-is. This is the clear next
  build; the typed interfaces are designed to carry it. (The architectural gate is already met by B+C.)
- **Multidimensional evidence facets (P7)** — `claim_tiers.py` is a scalar ladder; the demo already reports several
  facets (conservation / solver / kinetic / measured-validation) as separate fields, but a structured composite
  receipt that inherits each supporting facet's limitation is not yet a first-class object.
- **PHREEQC run (Track D)** — blocked as above; decks are ready.
- **Full hostile battery (P8)** and the **P10 domain-frontier adequacy matrix** are partially covered (the kernel's
  fail-closed controls + conservation adversaries are tested); a comprehensive numerical-adversary sweep and the
  per-domain representational-gap table are scoped forward.
