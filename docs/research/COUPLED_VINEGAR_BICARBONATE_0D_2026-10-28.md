# Coupled Vinegar / Bicarbonate 0-D Equilibrium — Wave VI-A (2026-10-28)

The flagship physicalization objective (`V3_0_VINEGAR_BICARBONATE_FLAGSHIP.md`): a **coupled** acetic-acid +
carbonate aqueous equilibrium, not two independently-computed pH values. Both families share ONE hydrogen-ion
activity and ONE charge balance, so a mixed vinegar + baking-soda system cannot be the superposition of the
separate acetate and carbonate solver outputs. This Wave couples them.

Module: `experiments/sandbox_foundation/coupled_equilibrium.py` (`VinegarBicarbonateSystem`, `solve`).
Tests: `experiments/sandbox_foundation/tests/test_coupled_equilibrium.py` (16, green).

## 1. The coupled model (closed liquid, fixed total carbon — the core case)

Conserved analytical components:

- total acetate `C_Ac = [HAc] + [Ac⁻]`
- total inorganic carbon `C_C = [CO2(aq)] + [HCO3⁻] + [CO3²⁻]` (CO2(aq) ≡ H2CO3* lumped)
- sodium `Na = [Na⁺]` (conservative cation, ≥ 0)

Shared charge balance: `[Na⁺] + [H⁺] = [OH⁻] + [Ac⁻] + [HCO3⁻] + 2[CO3²⁻]`.

Speciation at fixed `h` (`D = h² + K1_c·h + K1_c·K2_c`): `[Ac⁻]=Ka_c·C_Ac/(h+Ka_c)`,
`[HCO3⁻]=C_C·K1_c·h/D`, `[CO3²⁻]=C_C·K1_c·K2_c/D`, `[CO2]=C_C·h²/D`, `[OH⁻]=Kw_c/h`. Constants, Davies
activity model (monovalent γ₁ and divalent γ₂), tolerances and the verdict vocabulary are IMPORTED from the
two parent solvers — no re-derivation, no fork.

## 2. Two independent routes (the "two blind paths" discipline)

- **Route 1** — `scipy.optimize.brentq` bisection on the charge-balance residual `f(h)`.
- **Route 2** — the positive real root of the polynomial obtained by clearing `h·(h+Ka_c)·D` from `f(h)`, via
  `numpy.roots` (companion-matrix eigenvalues) — a wholly different algorithm, not a re-run of the bracket.

Measured agreement `|h₁ − h₂|` is machine-zero (≤ ~1e-20·h) across every admitted case; the admission gate
refuses (verdict `NUMERICALLY_UNVERIFIED`, or a fail-closed raise) if the routes disagree, charge/carbon/
acetate fail to conserve, a species goes negative, or the Davies fixed point leaves its domain (I > 0.5 M).

## 3. Validation record (Observed, 2026-10-28; `.venv/bin/python`)

| case | C_Ac | C_C | Na | pH | route agree | C/Ac/charge residual |
|---|---|---|---|---|---|---|
| water-only (ideal) | 0 | 0 | 0 | 7.0000 | 2.6e-23 | ~1e-22 |
| vinegar-only (davies) | 0.1 | 0 | 0 | 2.8815 | 1.7e-18 | ~3e-18 |
| bicarbonate-only (davies) | 0 | 0.1 | 0.1 | 8.1249 | 1.2e-22 | 0 |
| **mixed** 0.1 HAc + 0.1 NaHCO3 | 0.1 | 0.1 | 0.1 | **5.4465** | 2.5e-21 | ≤1.4e-17 |
| acid-limiting 0.2 HAc + 0.05 NaHCO3 | 0.2 | 0.05 | 0.05 | 4.1905 | 5.4e-20 | ≤6.9e-18 |

**Limiting-case validation against the already-PHREEQC-benchmarked parents (the free check):**
- vinegar-only (C_C = 0) reduces to `aqueous_equilibrium.solve` — **|ΔpH| = 0.00e+00** (exact).
- bicarbonate-only (C_Ac = 0) reduces to `carbonate_equilibrium.solve(mode="closed")` — **|ΔpH| = 0.00e+00** (exact).

So the two end-states inherit the parents' demonstrated PHREEQC agreement (acetate |ΔpH| ≤ 0.015 to I ≤ 0.1 M;
carbonate per its benchmark) for free. The MIXED interior is the genuinely new object; its numerical soundness
(route agreement + conservation) is pinned, but see §4.

## 4. Scientific boundaries (stated loudly — the plan's non-negotiables)

- **Numerical ≠ experimental.** Two agreeing routes, and even agreement with PHREEQC, are numerical-MODEL
  verification, never independent measured-chemistry validation. **External validation against a measured mixed
  vinegar/bicarbonate pH is UNKNOWN.**
- **Shared provenance.** The coupled model shares its Ka/K1/K2/Kw lineage with the parent solvers AND with
  PHREEQC's own thermodynamic databases, so a future mixed-PHREEQC comparison is **common-mode**, not an
  independent bearing — it checks the solve, not the chemistry.
- **No bubbles.** This is a CLOSED 0-D equilibrium: CO2 stays dissolved (`[CO2(aq)]` is an output). It is **not**
  a bubbly-fluid simulator; supersaturation, nucleation and gas-liquid transfer are NOT modeled. The dissolved-
  CO2 observable is published; any "fizzing" visual would be illustrative only (plan VI-C).
- **NaAc ion pair omitted** in this coupled base (as the acetate BASE model omits it); beyond I ~ 0.1 M the
  result carries the parents' activity caveat (flagged in `caveats`).

## 5. Documented next steps (not done here)

1. A preregistered **mixed** PHREEQC benchmark (new `.pqi` inputs: acid-limiting, bicarbonate-limiting, open-CO2,
   sealed-headspace), mirroring `benchmarks/{acetate,carbonate}_phreeqc/`. PHREEQC is an optional dependency,
   absent on the committed baseline, so this is deferred with its preregistration recorded here.
2. **Open** (fixed P_CO2) and **sealed** (finite-headspace) coupled modes — the carbonate parent already has the
   open/sealed machinery; coupling it to acetate is the extension.
3. Feeding the coupled state into the conservative spatial chamber (plan VI-B): evolve the conserved components
   `(C_Ac, C_C, Na)` between cells, recompute local equilibrium after transport, preserving electroneutrality.
