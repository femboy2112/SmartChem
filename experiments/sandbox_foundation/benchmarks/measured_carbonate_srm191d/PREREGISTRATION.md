# Preregistration — OPERATION XIX §4: first MEASURED-validation rung (NIST SRM 191d)

**Registered before comparison; the prediction is deterministic and fully reproducible from the repo.**

## Hypothesis
The SmartChem carbonate closed-system solver, run with its **pre-sourced 25 °C constants** (K1, K2, Kw, Davies-A) and
**no fitted parameter**, reproduces the **certified** pH(S) of NIST SRM 191d (a real Harned-cell emf measurement) to
within the certificate's expanded uncertainty.

## Why this is a *blind* prediction, not a fit
Nothing is calibrated. K1/K2/Kw/Davies-A were sourced long before this benchmark (see `carbonate_equilibrium.py`).
The buffer composition is fixed by the certificate. So the predicted pH is a single determined number — there is no
free parameter to tune toward 10.014, and therefore no p-hacking surface. The test is simply: does the pre-existing
model land inside the measured band?

## Fixed protocol
- Model input: `CarbonateWaterSystem(mode="closed", total_carbon_M=0.05, sodium_M=0.075, activity_model="davies")`.
  - `C_T = 0.05` = carbon from 0.025 mol/kg NaHCO₃ + 0.025 mol/kg Na₂CO₃.
  - `Na = 0.075` = 0.025 (NaHCO₃) + 2·0.025 (Na₂CO₃).
  - Molalities treated as molarities (dilute; stated units caveat).
- Comparator: the model's **activity** pH (pH(S) = −log₁₀ a_H⁺), against certified **10.014 ± 0.010** (U, k=1.96).

## Decision rule (registered)
- **CORROBORATED_WITHIN_U**: |model − 10.014| ≤ 0.010.
- **MARGINAL**: 0.010 < |residual| ≤ 0.020.
- **DIVERGENT**: |residual| > 0.020 → the model is refuted at this composition and the cause must be found
  (first suspects, in order: the omitted Na-carbonate ion pairs, then the Davies closure at I ≈ 0.1).

## What agreement does and does NOT establish (registered, so it can't be inflated after the fact)
- It establishes that **K2 + Davies reproduce a Harned-cell result to within its uncertainty**.
- It does **not** independently derive K2: our K1/K2 are Harned-lineage, and Davies shares the Debye–Hückel family
  with the certificate's Bates–Guggenheim convention — which is itself the certificate's dominant uncertainty
  (0.0050 pH). This is **partial common-mode**, stated up front.

## Holdout plan (registered) and its access gap
A true fresh holdout would be a **different 25 °C composition** measured by the same primary method. The reachable
candidates (APMP.QM-K18 close-to-standard carbonate buffer; Wu/Koch/Marinenko lot-to-lot 10.010) either do not
publish exact recoverable molalities or are the *same* composition on a different lot. **The other certified
temperatures (10/15/20/30/35 °C) are not a holdout for us** — every repo constant is 25 °C-sourced and the model
fail-closes off 25 °C (XIX-1C). So this is a single validated point, honestly labelled, not a multi-point calibration.

## Next probe (registered)
Add a **sourced** Na-carbonate association constant (NaCO₃⁻, and/or NaHCO₃⁰) to the carbonate model as an opt-in
refinement — mirroring the NaAc(aq) opt-in the acetate model already carries — and re-run this rung with/without it,
reporting whether it moves the residual toward 10.014 **without** breaking the acetate/carbonate PHREEQC domain.
