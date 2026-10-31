# MIXED vinegar/bicarbonate PHREEQC benchmark — PREREGISTRATION (Operation XIII P0, 2026-10-31)

Written BEFORE any PHREEQC run. **PHREEQC is ABSENT on the committed baseline**, so this is the reproducible
*recipe + inputs*; no reference pH is produced here and none is fabricated. The committed artifacts are the exact
`inputs/*.pqi` decks, the generator, the code-side runner, and `code_results.json` / `comparison_table.json` with
the PHREEQC column **null = `EXTERNAL_VALIDATION_UNAVAILABLE`**.

Target under test: `experiments/sandbox_foundation/coupled_equilibrium.py :: VinegarBicarbonateSystem.solve`
(closed liquid, fixed total dissolved carbon). Instrument: PHREEQC (IPhreeqc via `phreeqpython`) in an isolated
scratch venv.

## 0. Database determination (§2A: a DB that supports BOTH families)
The carbonate benchmark used `phreeqc.dat` (carbonate native, **no acetate**); the acetate benchmark used USGS
`minteq.v4.dat` / `llnl.dat` (acetate native). The MIXED system needs **both** acetate and carbonate in ONE
database. `minteq.v4.dat` carries both: acetate (`H+ + Acetate- = H(Acetate)` logK 4.757 NIST46.4; `Na+ +
Acetate- = Na(Acetate)` logK −0.18) AND the carbonate system (CO2 / HCO3⁻ / CO3²⁻). **Primary = `minteq.v4.dat`,
secondary = `llnl.dat`.** `phreeqc.dat` is NOT usable for the mixed system (no acetate) and MUST NOT be patched with
the code's own acetate constant (that would re-import the code's number → not independent). Pin each DB's sha256 on
the first real run (`run_phreeqc.py` prints it); record it in README.md.

## 1. Cases (all T = 298.15 K; closed liquid; see `cases.py` for the authoritative grid)
M1 pure water · M2 vinegar-only (acetate limit) · M3 bicarbonate-only (carbonate limit) · M4 stoichiometric mixed ·
**M5 acid-in-excess → BICARBONATE-LIMITED** (0.2 acetate / 0.05 carbon) · M6 bicarbonate-in-excess → acid-limited ·
M7 dilute mixed · M8 intermediate I (~0.3 M) · M9 high I near the Davies boundary (~0.45 M) · M10 extreme-basicity
numerical control · M11 refusal probe (I > 0.5 M: **code EXPECTED TO DEMOTE** to `NUMERICALLY_UNVERIFIED`).

**Label correction (directive §2B):** the prior coupled dossier called the 0.2/0.05 case "acid-limiting." It is
**bicarbonate-limited** — more weak acid than bicarbonate, bicarbonate is consumed first, residual pH is acidic
(code pH ≈ 4.19). M6 is the true acid-limited mirror. PHREEQC pH is solved by `pH 7 charge` (electroneutrality),
the same closure as the code's charge balance.

## 2. Species / totals
Code: HAc, Ac⁻, CO2(aq)≡H2CO3*, HCO3⁻, CO3²⁻, H⁺, OH⁻, Na⁺ (Na⁺ fully dissociated; no ion pair in the coupled base).
PHREEQC minteq.v4: H⁺, OH⁻, Acetate⁻, H(Acetate), Na⁺, Na(Acetate), CO2, HCO3⁻, CO3²⁻ (+ trace; ignored).
Total acetate (PHREEQC) = Acetate⁻ + H(Acetate) + Na(Acetate); total C(4) = CO2 + HCO3⁻ + CO3²⁻.

## 3. Standard states / concentration scale (differences recorded, not papered over)
Same molal(PHREEQC)-vs-molar(code) issue the acetate benchmark documented (A1/A2): `units mol/l` is not a true molar
input, so the committed decks carry totals as `mol/kgw` and the runner MUST molar-match (fixed point on mol/kgw
input until sum-of-species molarities reproduce the requested mol/L). Residual molal/molar difference (<~0.013 pH at
0.5 M) is part of the budget, not corrected away. Activity: code = Davies (A=0.509, divalent γ₂=γ₁⁴);
minteq.v4 = Davies/WATEQ; llnl = extended DH. Per-species γ read out of PHREEQC, never assumed.

## 4. Metrics / thresholds (fixed now, NOT tuned after data)
PRIMARY |ΔpH| = |code pH_activity − PHREEQC pH|: AGREE ≤ 0.02 · MARGINAL 0.02–0.05 · DIVERGE > 0.05 (the
glass-electrode resolution scale the acetate/carbonate benchmarks used). A "domain of agreement" = cases AGREE
against BOTH databases. Code admission: a `NUMERICALLY_UNVERIFIED` verdict (M11) IS the recorded outcome, not an
error to hide. The arbitrary-precision holdout (`coupled_reference_hp.cross_check`) is a SEPARATE, already-run
numerical cross-check (NUMERICALLY_VERIFIED) and is NOT the PHREEQC comparison.

## 5. Verification vs validation (the hard line)
PHREEQC and this model share the Ka/K1/K2/Kw lineage AND PHREEQC's own DB traces to the same classical EMF work, so
a PHREEQC match is **solver/activity-model VERIFICATION, common-mode on the thermodynamics — NOT independent
measured-chemistry validation** (`BENCHMARKED_AGAINST_REFERENCE_SOLVER`, never `CALIBRATED_TO_MEASUREMENT`). A
MEASURED mixed vinegar/bicarbonate pH would be the only item eligible to be called validation; none with defensible
provenance is used, and none is back-computed from the code's constants. **External validation remains UNKNOWN.**
