# Operation SmartChem XIII — the chemical universe becomes physical (2.0 research track)

**Date:** 2026-10-31. **Branch:** `research/physical-vinegar-xiii` (off #142 `research/coupled-vinegar-bicarbonate`
→ #134 `research/physicalization-2x` → released `main` `9e8fa5f` v1.1.0). **PR:** #150 (draft, research).
**Nothing is wired into the `smartchem/` production package; nothing merged, tagged or published.**

This round turned the mixed vinegar + baking-soda chemistry from a static 0-D equilibrium into a genuinely evolving,
conservative, source-grounded simulation, with an explicit gas boundary, real-time CO₂ transport, a two-cell
reactive world, a solid powder phase, a runnable headless demo, and a hostile-validation phase.

---

## A. Repository coordinates

| item | value |
|---|---|
| start SHA (base, #142 tip) | `e5698f9` |
| end SHA (XIII tip) | `ce3231c` (+ this dossier) |
| commits | P0 `fec75e7` · P1 `e91399e` · P2 `f9b0378` · P5 `5bab8ca` · P3 `a471724` · P4 `a2bc5c0` · P6 `8c85f5a` · pack `ce3231c` |
| baseline sandbox suite | 577 passed at `e5698f9` |
| final sandbox suite | **698 passed** (ruff clean on every changed file) |
| new modules | `claim_tiers.py`, `coupled_reference_hp.py`, `coupled_gas_equilibrium.py`, `coupled_dynamics.py`, `coupled_twocell.py`, `solid_bicarbonate.py`, `vinegar_bicarbonate_demo.py`, `benchmarks/coupled_phreeqc/` |

No protected-main merge, tag, publish, or other-repo mutation. All commits use the repo-local noreply identity, no
attribution trailers.

## B. Scientific claim ledger

Labels: **DISCLOSED** (equations/assumptions stated), **CORROBORATED** (cross-checked by an independent
algorithm/precision — numerical, not experimental), **OBSERVED** (a committed run produced it), **UNVERIFIED**
(assumed parameter / no external check), **DARK** (not attempted), **REFUTED**. Conclusions inherit their weakest
premise.

| # | result | label | boundary / evidence |
|---|---|---|---|
| 1 | Mixed closed equilibrium (pH, speciation) | **CORROBORATED** | 60-digit `decimal` independent-algorithm holdout agrees with the float64 two-route solve across the mixed interior + §2C hostile regimes (`test_coupled_reference_hp`). Common-mode on the shared constants → `NUMERICALLY_VERIFIED`, NOT reference-solver benchmarked. |
| 2 | Mixed PHREEQC benchmark | **UNVERIFIED (deferred)** | PHREEQC absent on the baseline; 22 reproducible `.pqi` decks + runner committed, reference column null (`EXTERNAL_VALIDATION_UNAVAILABLE`). minteq.v4 is the DB that carries both families. |
| 3 | Three gas-boundary modes (closed/open/sealed) | **CORROBORATED** | closed ≡ the verified coupled solver; open pure-water→air pH 5.656 (textbook anchor); each mode two-route-agreeing + re-deriving admission gate (`test_coupled_gas_equilibrium`). |
| 4 | Open vs sealed differ (B6) | **OBSERVED** | 1.810 pH for identical contents; a partition-ignoring cartoon would not. |
| 5 | Real-time CO₂ transfer dynamics | **CORROBORATED** | dynamic steady state = static sealed equilibrium to machine zero; RK45 vs independent backward-Euler/RK4 agree + timestep convergence (`test_coupled_dynamics`). |
| 6 | kLa gas-transfer coefficient | **UNVERIFIED** | Level A assumed (usable); Level B an order-of-magnitude geometry-class band (CALIBRATION_REQUIRED); Level C not attempted (no measured time series). A trajectory's tier = weakest(eq, kLa) = ASSUMED_PARAMETER. |
| 7 | Two-cell transport (diffusion + mixing) | **OBSERVED / UNVERIFIED params** | global acetate/carbon/sodium conserved, charge closed, dt-refinement converges; transport coefficients prescribed/ASSUMED. |
| 8 | Solid NaHCO₃ dissolution | **CORROBORATED (equilibrium) / UNVERIFIED (rate)** | sourced solubility S, DERIVED Ksp=S²; Na & C conserved 1:1:1; saturation bound holds; the finite rate k_diss is ASSUMED. |
| 9 | NaHCO₃ molar solubility 1.2±0.15 mol/L | **DISCLOSED (tertiary-sourced)** | CRC/PubChem; 25 °C-anchored; activity-corrected Ksp omitted (a caveat). |
| 10 | External measured validation of ANY pH | **DARK** | no defensible measured datum used or fabricated; UNKNOWN, as in the parent models. |

## C. Physical equations and units

State variables are conserved inventories (mol) over SI/declared volumes; concentrations are derived (mol/L).

- Shared charge balance (every aqueous state): `[Na⁺] + [H⁺] = [OH⁻] + [Ac⁻] + [HCO₃⁻] + 2[CO₃²⁻]`.
- Acetate (nonvolatile): `[Ac⁻] = Ka_c·C_Ac/(h+Ka_c)`. Carbonate closed: `[i] = C_C · {h², K1_c·h, K1_c·K2_c}/D`,
  `D = h² + K1_c·h + K1_c·K2_c`. Open: `[CO₂(aq)] = K_H·P_CO₂` pinned. Davies: `Ka_c=Ka/γ₁²`, `K2_c=K2/γ₂`,
  `γ₂=γ₁⁴`; domain `I ≤ 0.5 M`.
- Gas (ideal): `P_CO₂ = n_gas·R·T/V_gas`, `R=0.0820574 L·atm·mol⁻¹·K⁻¹` (EXACT).
- Gas transfer (constitutive, declared): `J_CO₂ = kLa·V_liq·(c_CO₂,aq − K_H·P_CO₂)` [mol/s]; `dn_gas/dt = J`,
  `n_liq = n_total − n_gas` (carbon conserved by construction).
- Two-cell selective diffusion: `J_X = g_X·valve·(c_X[A]−c_X[B])` for neutral X ∈ {HAc, CO₂(aq)}, moving the
  corresponding total; no charged-species flux (Nernst–Planck obstruction). Bulk mixing: symmetric swap of balanced
  volume parcels `dn = dV·(C[B]−C[A])` for every component (charge preserved).
- Dissolution: `NaHCO₃(s) → Na⁺ + HCO₃⁻` (1:1:1); SI `= [Na⁺][HCO₃⁻]/Ksp`; fast limit to SI=1 or exhaustion;
  finite rate `dn_s/dt = −k_diss·max(0,1−SI)` (k_diss ASSUMED).

## D. Numerical verification

- Two independent routes per equilibrium (bracket + polynomial / dual elimination), agreement-gated; a re-deriving
  fail-closed admission gate per mode. Out-of-Davies-domain demotes to `NUMERICALLY_UNVERIFIED`.
- Arbitrary-precision (60-digit `decimal`) holdout for the mixed interior, agreeing to the float64 floor.
- Dynamics: adaptive RK45 vs independent backward-Euler + RK4; timestep refinement converges; steady state = sealed
  equilibrium to machine zero; carbon residual 0 by construction.
- Two-cell: global conservation residual < 1e-12; dt-refinement first-order convergence.
- Mutation controls (P6): a sign-flipped transfer flux BREAKS the sealed cross-check (ΔpH 0→>0.05), proving the
  check discriminates; off-temperature / zero-uncertainty constants refused.

## E. Scenario matrix (B1–B8)

| scenario | status |
|---|---|
| B1 water control | NUMERICALLY_VERIFIED |
| B2 vinegar control | NUMERICALLY_VERIFIED |
| B3 bicarbonate control | NUMERICALLY_VERIFIED |
| B4 mixed | NUMERICALLY_VERIFIED |
| B5 acid-/bicarbonate-limited pair | NUMERICALLY_VERIFIED (label corrected: 0.2/0.05 is **bicarbonate-limited**, acidic) |
| B6 open vs sealed + dynamics | NUMERICALLY_VERIFIED |
| B7 mixing/valve (two cells) | IMPLEMENTED (transport ASSUMED) |
| B8 dissolution/grain-size | IMPLEMENTED (rate ASSUMED) |

No scenario is BENCHMARKED or CALIBRATED in this build (no PHREEQC run, no measured dataset). None FAILED; none
fabricated.

## F. Working demonstration

`python -m experiments.sandbox_foundation.vinegar_bicarbonate_demo [--json OUT.json --csv OUT.csv --scenario B6]`
emits strict-JSON frames (value-tagged by QuantityKind + claim tier; UNSUPPORTED→null, never 0; a bubble graphic
would be an ILLUSTRATION of modelled flux, never a count), a CSV time series of the CO₂ evolution, a terminal
dashboard, and a model/source digest. `observed_measurement`/`benchmarked`/`calibrated` are all False.

## G. Validation source map

- Equilibrium constants (shared with the parent solvers): Ka (CRC/LibreTexts), K1/K2 (Harned & Davis/Scholes via
  CRC/Stumm & Morgan), Kw, Davies A. Henry K_H (Sander ACP 2023). All `SourcedConstant` with positive uncertainty.
- NaHCO₃ solubility (CRC/PubChem CID 516892), Ksp DERIVED.
- PHREEQC: minteq.v4.dat (primary, both families), llnl.dat (secondary); decks preregistered, not run (absent).
- **Common-mode caveat:** PHREEQC and this model share the constant lineage, so a future match is solver
  verification, not independent validation. A measured mixed vinegar/bicarbonate pH remains the only item eligible
  to be called validation, and none is used or fabricated.

## H. Chemistry-algebra progress (parallel track)

Type-3 lactonization: the standalone `retro_lactonization_edges` generator from XII is unchanged in this round. The
smallest truthful integration increment — making enumeration report exhaustiveness (so a truncated enumeration
cannot feed a COMPLETE receipt) — is tracked separately on a branch off the 1.5 candidate (does not touch the
physicalization track). The full lactonization recognizer + `search_event_routes` wiring (which bumps the 24-class
registry digest) remains a separate, digest-delicate effort with its own soundness gate.

## I. Release readiness

- **1.1.0** — published (`main` `9e8fa5f`, tag `v1.1.0`). Untouched.
- **1.5 candidate** — PR #149, separate production milestone. Not destabilised by this round.
- **2.0 experimental numerical core** — THIS round: a conservative, numerically-verified mixed aqueous/gas/solid
  simulation with an explicit gas boundary and dynamic CO₂ transport. Research-grade; experimental schema; outside
  the stable 1.x contract.
- **2.0 calibrated predictive domain** — NONE yet (no PHREEQC run, no measured calibration). The path is preserved.
- **3.0 interactive falling-sand** — the renderer-neutral frame (`vinegar_frame`) is the LibGibson seam; it reads
  immutable data and never mints scientific authority.

These milestones are NOT conflated. A review-ready 2.0-alpha research PR (#150) is the output; it is not a published
SmartChem 2.0.
