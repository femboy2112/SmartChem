# Measured validation — NIST SRM 191d carbonate pH standard (OPERATION XIX §4)

The first SmartChem comparison against a **real physical measurement** rather than another solver. A blind prediction
(no fitted parameter) of the repo carbonate model, compared to the NIST-certified pH(S) of SRM 191d.

## Result

| model | pH (activity) | residual vs 10.014 | within U (±0.010)? |
|---|---|---|---|
| **Davies** | **10.0048** | **−0.009** | **yes** |
| ideal (no activity) | 10.323 | +0.309 | no |

**Status: `MEASURED_CORROBORATED_WITHIN_U`** — a zero-parameter blind prediction lands inside the certified
uncertainty band. The ideal model (no activity correction) misses by 0.31, so the Davies closure is doing real work.

## Source (read directly from the certificate)

NIST **Standard Reference Material 191d** — Sodium Bicarbonate (191d-I) / Sodium Carbonate (191d-II) (pH Standard),
*Certificate of Analysis*, NIST Office of Reference Materials. **Date of issue 05 February 2025**, valid to
30 November 2032. <https://tsapps.nist.gov/srmext/certificates/191D.pdf>
(SHA256 of the retrieved PDF: `ea316fb1368d0563882a2b6926fe8a6bb07736e9d5fc1b24bb70c2317cc02d38`.)

Buffer: 0.025 mol/kg NaHCO₃ + 0.025 mol/kg Na₂CO₃, CO₂-free, closed. pH(S) on the **molality scale**, p° = 1 atm,
by the **primary Harned-cell** (cells without liquid junction) **emf** method — i.e. NOT back-computed from any Ka.

Certified pH(S), Table 1 (u_c = 0.0052 and U = 0.010 at k = 1.96 at every temperature):

| T / °C | 10 | 15 | 20 | **25** | 30 | 35 |
|---|---|---|---|---|---|---|
| pH(S) | 10.179 | 10.118 | 10.063 | **10.014** | 9.968 | 9.926 |

u_c **includes** the Bates–Guggenheim convention uncertainty (0.0050 pH) — the dominant component.

## How independent is this, really?

**Partially.** Honest separation of independent vs shared provenance:

- **Independent:** the certified value is a 2025 NIST **emf** measurement on a specific material lot, decades after the
  Harned-era work that underlies our constants; it is not computed from our Ka/K2. Two national labs (NMIJ, PTB)
  reproduce this buffer type to ≈0.002 (APMP.QM-K18), so the method is reproducible.
- **Shared / common-mode:** our K1/K2 trace to the Harned lineage; **Davies** is a Debye–Hückel-family single-ion
  activity closure, and the certified pH(S) uses the **Bates–Guggenheim** convention (also Debye–Hückel family),
  which is the certificate's dominant uncertainty. So agreement corroborates *"K2 + Davies reproduce a Harned-cell
  result to within its uncertainty"*; it does **not** independently measure the single-ion activity of H⁺.

This is therefore the **first rung above** the PHREEQC reference-solver benchmark (which is common-mode on the
constants *and* on the activity family) — a real-instrument comparison, with its residual partial-common-mode
honestly flagged.

## Caveats (every claim inherits its weakest premise)

- **Units:** 0.025 mol/kg molalities treated as mol/L (dilute, ρ ≈ 1.00 kg/L → ~0.1–0.3 % in C_T, est. ~0.001–0.002
  pH). Not a density-corrected conversion.
- **Na-carbonate ion pairs** (NaCO₃⁻, NaHCO₃⁰) are omitted from the carbonate base model — a genuine second-order
  confound at Na ≈ 0.075; the base model already lands within U, so the pair is a refinement, not a rescue.
- **Single point:** 25 °C only (the model is 25 °C-sourced; off-25 °C is refused by XIX-1C). The other certified
  temperatures are an access gap for us until temperature-dependent constants exist.
- A one-point blind hit is **validation of a rung**, not a multi-point calibration.

## Access gaps for the other §4 targets (established, not fabricated)

- **Acetate buffer pH** (Harned & Ehlers 1932; Partanen & Covington 2003; IUPAC 2002 Table 3): the primary tables are
  ACS-paywalled / IUPAC server Cloudflare-403 to automated clients. A human browser can likely fetch the IUPAC PDF.
- **CO₂ gas-transfer (kLa) time course:** no primary experimental table with a matching apparatus was reached.
- **NaHCO₃ solubility:** no primary source reached; vendor figures (~10 g/100 g H₂O) disagree and are not a dataset.

## Reproduce

```
python -m experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d.run_measured
```

Writes `result.json` (strict JSON) and prints the headline. Deterministic; no network, no PDF needed (the certified
values are recorded in the harness with the certificate URL + SHA). See `PREREGISTRATION.md` for the registered
protocol and decision rule.
