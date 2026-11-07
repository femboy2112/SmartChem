# XXIII S4 -- activity-based solid dissolution (`solid_equilibrium.py`): validation notes

Reproduce: `PYTHONPATH=. .venv/bin/python -m experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii.run_solid_equilibrium_xxiii`
(~35 s; writes `result_solid_equilibrium_xxiii.json`). Nothing is fitted. `k_diss = 1e-6` and `kf = 1e8` are ASSUMED kinetic scales.

## (a) Calcite in CO2-free water, closed system -- MODEL-vs-MODEL, not a measurement
Network (kernel `CoupledWorld`, one compartment, 1 L, 0.01 mol CaCO3(s), 6000 s, 60 macro-steps, rtol 1e-10): calcite dissolution
(`ActivitySolubilityRate`, logKsp -8.48 = `minteq.v4.dat` line 11693 `Calcite`, equal to `phreeqc.dat` `Calcite`) plus Davies-activity
speciation (`ActivityReversibleRate`): CO3^2-/HCO3-/CO2(aq)/H+/OH-, and the Ca ion pairs CaCO3(aq), CaHCO3+, CaOH+ (all constants read
from `phreeqc.dat`; the water block has only `-analytic`, so its 25 C analytic value is used). No gas phase (closed).

| quantity | kernel | PHREEQC (phreeqc.dat, EQUILIBRIUM_PHASES Calcite SI=0) | diff |
|---|---|---|---|
| dissolved Ca total | 1.23009e-4 mol/L | 1.23007e-4 mol/kgw | +0.0017% raw numbers; **+0.30%** after mol/L -> mol/kgw with PHREEQC's density 0.99706 |
| pH (Davies activity) | 9.90687 | 9.90681 | +6.2e-5 |
| ionic strength | 3.8570e-4 | 3.8560e-4 | +0.027% |

The 0.30% spread between the raw and density-converted comparisons IS the molar-vs-molal convention slack (the same dimensionless K is used
on either scale); it is not a model discrepancy and the sign of the "true" residual is not identifiable at that level. Using PHREEQC's
*effective* 25 C constants (its `-analytic` values) instead of the nominal `-log_k` moves Ca by <1e-4 relative. Species-level, Davies vs
PHREEQC's WATEQ Debye-Huckel differ by up to ~12% on the trace CaHCO3+ (1.007e-7 vs 1.142e-7) and 0.3% on CaCO3(aq); they barely move total Ca.
The test is weak by design: shared constants + I ~ 4e-4 (gamma ~ 0.96/0.86), where every Debye-Huckel variant agrees. It validates the
integration + the activity bookkeeping, NOT Davies beyond I ~ 1e-3 and NOT nature.
Steady state is invariant to the assumed kinetics: k_diss 1e-5 -> +4e-6 relative; kf 1e9 -> +8e-5 relative (solver-tolerance level).
Last-step relative change of Ca: 2.9e-6 (steady).

## (b) Time-step refinement (N = 60, 120, 240 macro-steps, 100/50/25 s)
| tolerance | steady Ca (N, 2N, 4N) | diffs N->2N, 2N->4N | Ca at t=100 s |
|---|---|---|---|
| rtol 1e-10 | 1.230089603389e-4, 1.230089603411e-4, 1.230089603412e-4 | 2.3e-15, 4.6e-17 (monotone) | 7.44724577e-5 for all N; spread 7e-15 |
| rtol 1e-5 | 1.230089517e-4, 1.230089488e-4, 1.230089480e-4 | -3.0e-12, -7.3e-13 | spread ~1.5e-9, non-monotone |

Honest reading: this world has ONE operator (reaction), so there is no splitting error; `n_steps` only changes restart points of the
BDF solve. The refinement shows convergence to the solver floor (monotone at steady state for rtol 1e-10), NOT a method order. The
"observed order" fields in the JSON (5.6 / 2.0 / noisy) are ratios of noise-level differences and are not claimed.

## (c) Independent conservation (this file's own sums over the trajectory, not the receipt)
Ca and C: max drift 7.1e-17 mol (n0 = 0.01); H 2.8e-13, O 1.4e-13 (of ~110 / ~55 mol); net charge: max |sum z n| = 1.1e-18 mol, n0 = 0.
Receipt: STRUCTURALLY_CONSERVING, positivity held, `execution_identity_basis = AUDITED_BUILTIN`, certified = True, admitted tier ASSUMED_PARAMETER
(k, kf assumed).

## (d) Hostile holdout -- nahcolite NaHCO3(s), WATEQ4F logK -0.548 (`wateq4f_PWN.dat` line 2242): must FAIL CLOSED
Davies-activity saturation in pure water: solve m*gamma(I=m) = 10^(-0.548/2) = 0.5321 -> **m = 0.7086 mol/kg** (I = 0.7086).
Repo-sourced bulk solubility (`NAHCO3_SOLUBILITY_25C`): 1.2 +/- 0.15 mol/L (CRC / PubChem CID 516892, ~25 C).
**Disagreement: 1.69x** (1.48x - 1.91x over the stated uncertainty). Davies, with the WATEQ4F Ksp, under-predicts solubility by ~40%; the
literature-bearing cause is that Davies carries no specific-ion terms and is not meant for I ~ 0.7-1.2.
Kernel behaviour: with the default domain `ionic_strength_max = 0.1` the dissolution world raises `OutOfDomainError` (verdict
`OUT_OF_DOMAIN`) as I crosses 0.1 (observed I = 0.1026), long before the 0.71 saturation. Counterfactual only: with the domain hand-raised
to 5.0 the same world silently integrates to Na+ = 0.7086 M (1.69x off the sourced value). The guard, not a tuned constant, is the fix.
molality (Davies solve) vs molarity (repo value) differ by a few % at ~1 M, negligible against 1.69x.

## (e) Phase / charge
CaCO3(s) is `Phase.SOLID`, charge 0, contributes nothing to ionic strength; the dissolution products are charged aqueous species; net charge
per compartment stays 0 to 1e-18 mol.

## NOT done / limits (plainly)
* No gas phase / CO2 exchange (closed system only). No nucleation (precipitation needs solid present). No temperature dependence: 25 C only,
  and the law is not handed the world temperature, so nothing enforces it -- the Ksp's `T_K` provenance is the only statement.
* Activity model is Davies on molarity; neutral species gamma = 1; no ion-pair-in-activity double-count correction (Phase III: pairs + Davies
  was 0.08-0.15 pH off for buffers at I ~ 0.1 -- calcite here is at I ~ 4e-4 where that does not bite, and says nothing about I ~ 0.1).
* The SourcedConstant uncertainties on the logK values are the 2-decimal TABULATION floor (half the last printed digit), not measured errors.
* Only one external reference (PHREEQC, shared constants). Not validated against any measured calcite solubility here.
* The audit pin covers each class's source only; module-level imports and `OutOfDomainError` sit outside it.
