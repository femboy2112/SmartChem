# OPERATION XXII — final handoff dossier (the chemical universe goes mainline)

Research record for the mega-round after OPERATION XXI. Live `main` = `9d04894`. Everything below is MERGED or
committed+pushed code and verified evidence, not PR prose.

## A. Git and merge ledger

| Ref | SHA | What |
|---|---|---|
| `main` before | `c3d0d01` | released v1.5.0 (24-class oracle) |
| `integration/2.0-alpha` → | `d63d94c` | XXII-A P0 soundness merged onto the alpha (`research/operation-xxii` `d1bba90`) |
| **`main` after** | **`9d04894`** | **PR #156 merged (normal, provenance-preserving): parents `c3d0d01` + `d63d94c`** |
| `research/operation-xxii` | `d1bba90` | §1/§2/§3 P0 fixes + 39 hostile tests (pushed) |
| `research/operation-xxii-reactor` | (tip) | §5 reactor + §7 categorical + §9/§10/§13 docs (pushed) |
| `research/operation-xxii-s6` | `35f4f12` | §6 Na-pairing 2³ factorial (pushed) |
| `feat/1.6-candidate-xxii` | `13c8bab` | **PR #157** — the 1.6.0 candidate (gated on CI) |

- **Merges performed:** `research/operation-xxii` → `integration/2.0-alpha` (`--no-ff`); PR #156 (`integration/2.0-alpha`)
  → `main` (the authorized research-only merge, v1.5.0 retained). Post-merge hosted CI on `9d04894`: **9/9 job-level
  success**; the local full sandbox suite: **1057/1057**.
- **Tags NOT made, releases NOT published:** no `v1.6`/`v2.*` tag, no GitHub Release, no PyPI — all require separate
  authorization and were not taken.
- **Protected-main discipline:** `enforce_admins=false` would have allowed bypass; no gate was waived. The merge met
  all 7 required status checks + up-to-date + conversation-resolution on the exact head before merging.
- **Release status:** production remains **v1.5.0** on `main` (the research merge kept the package byte-identical). The
  1.6.0 bump is a separate PR (#157) that merges only if its own gates pass.

## B. Numerical / categorical bug ledger (RED → fix → control)

| § | RED counterexample (on `07afeff`) | Fix | Mutation / controls | Residual risk |
|---|---|---|---|---|
| **1** bulk completeness | Na⁺-only `ElectroneutralBulkExchange` accepted → after 1 step local charge A −0.00476 / B +0.00476, global ≈0 | completeness+phase gate in `CoupledWorld.__init__`: carry the COMPLETE aqueous roster of both cells, aqueous-only; partial/solid/gas refused | 16 tests incl. complete NaCl parcel neutral, buffer bulk, reversed flow, 3-cell, volume ratios, refinement | a restricted multi-species *selective* operator is future work (declare InterfaceTransfer per species meanwhile) |
| **2** execution identity | lying `descriptor()` → `execution_identity_certified=True`, strict mode did not raise, 10× mutation ran different physics under one cert | audited rate-law registry: CERTIFIABLE only if the type is registered (audited-faithful descriptor); unregistered → EXECUTABLE-UNVERIFIED/refused | 11 tests incl. registered-law mutation caught by the cert backstop, registry fail-closed, the explicit promotion route | a registered law's faithfulness rests on human audit (that is the point of the registry) |
| **3** numerical resolution | a 100×-of-inventory trace loss (1e-13 vs 1e-15) stamped `material_balance_closed=True`; negative dip passed positivity | typed per-component `VERIFIED_WITHIN_RESOLUTION` / `VIOLATED` / `NUMERICALLY_UNRESOLVED_AT_REQUESTED_SCALE`; fail-closed when scale ≤ ~2·atol; positivity resolution audit | 12 tests across the 1 / 1e-6 / 1e-12 / 1e-15 / zero / open-feed matrix + large-spectator isolation | the resolution threshold (RESOLUTION_FRACTION=0.5) is a declared policy, not a derived bound |

All three RED-proven empirically before the fix; full suite 1057/1057 after; the §6 no-tune git guard was tightened
(bounded to the XXI range) rather than weakened.

## C. Mathematical guarantees

- **`E·N = 0`** proven EXACTLY at `ChemicalSystem` construction (unbounded Python-int arithmetic; the XXI-7 bridge
  cross-checks it integer-exactly, no float+round).
- **Internal flux cancellation:** interface + bulk transport are a→b internal transfers (what leaves A enters B for
  every species), so every global component total is untouched by transport; only external boundaries inject flux.
- **Local & global charge:** a complete electroneutral bulk parcel sweeps the solution's TOTAL charge density (0 for a
  neutral cell) → no cell left charged (XXII-1); global charge conserved by every internal operator; where charge is
  implicit-water-reservoir-coupled the conservation claim is DEMOTED, never silently exempted.
- **Material balance:** per-component, per-step, against a signed external-flux ledger integrated as augmented ODE
  state (observer-invariant, XX-3); closes iff every conserved component is VERIFIED_WITHIN_RESOLUTION (XXII-3).
- **Numerical adjustments:** phase-stitch roundoff clamps are explicit signed events in the whole-run balance (XX-4);
  the coupled integrator applies none (A_i ≡ 0 there).
- **Projection constraints:** every fast-equilibrium projection passes a fail-closed admission gate (completeness,
  finiteness, nonnegativity, accepted solver verdict, posed-problem match, and TWO independent conservation recomputes).
- **Categorical composition:** structural laws (identity/associativity/tensor/gluing/conservation/port correspondence/
  catalyst/mechanism-not-reduced-to-net) hold on the exact-integer bridge (XXI-7); the map is a faithful STRUCTURAL
  functor within its tested domain, NOT a dynamics functor (XXII-7 three-layer separation).

## D. Scientific results

- **NIST SRM 191d (XXI-4, unchanged):** NOT a robust prediction — within convention-inclusive Table 1 only (thin),
  REFUTED at Table A1 (~3× U_R) and under molar-K scale transport. Hinges on the unresolved molar-vs-molal K-scale.
- **Na-pairing 2³ factorial (XXII-6, NEW, verdict-changing):** the two Na-carbonate associations act in OPPOSITE
  directions on the NIST pH — NaHCO₃ (B) **+0.0115 TOWARD** 10.014, NaCO₃⁻ (C) **−0.153 AWAY** — so XXI's single
  "both pairs" factor masked a cancellation. All interactions |E| < 6e-4 (the pairings superpose; H5 unsupported).
  The best-to-NIST variant (B present, C removed; residual −0.0033, inside U) is a DIAGNOSTIC, not a correction
  (reached only by deleting a real NIST-sourced association). Deletion-only DBs, all constants DB-sourced, no tuning.
- **Provenance:** all three Na-pair constants are NIST-sourced (A NIST46.4, B/C NIST46.3) on a shared b-dot/molal
  basis; the ablation isolates the association equilibria only — activity-model / molal-vs-molar / lineage stay
  common-mode (the DARK residual).

## E. The new reactor (§5)

`python -m experiments.sandbox_foundation.general_reactor_demo` — one vinegar/bicarbonate flagship, three transport
modes from one initial state on the one generic integrator. Measured endpoints:

| mode | pH_A | pH_B | Na gradient | acetate in B | charge A/B |
|---|---|---|---|---|---|
| closed | 2.88 | 8.29 | 0.10 (trapped) | 0 | ~0 |
| membrane | 3.48 | 5.85 (differ) | 0.10 (ions can't cross) | 0.094 (neutral HAc) | ~0 |
| bulk | 5.57 | 5.57 (equal) | 0.00 (whole solution mixes) | 0.050 (Ac⁻ crosses) | ~0 |

Distinct by MECHANISM, not coefficient; every mode charge-neutral (|q| < 8e-18) and material-balance-closed; tier
capped at ASSUMED_PARAMETER (dissolution kinetics unsourced — honest). 20 hostile controls.

## F. Generality matrix (one kernel, many chemistries)

| System | Reuses | Additional physics supplied |
|---|---|---|
| synthetic reaction-diffusion (2 cells) | kernel + transport | mass-action kinetics only (non-commuting R,T for the splitting study) |
| acetate buffer under acid feed | + fast-equilibrium projection | acid-base speciation, open feed |
| NaCl bulk-exchange world | + electroneutral bulk | whole-solution parcel transport, charge bookkeeping |
| vinegar/bicarbonate reactor | + solid dissolution + Henry gas | mixed acetate/carbonate equilibrium, solid phase, gas headspace, vent, 3 transport modes |
| categorical bridge outputs | kernel construction | structural diagrams → kernel systems (exact E·N, identity) |

The integrator's code never mentions acetate, CO₂, or any species — the architectural gate held across all of these.

## G. Release-readiness matrix

| Track | State |
|---|---|
| v1.5.0 | RELEASED (`main` package = v1.5.0, tag `v1.5.0`) |
| 2.0 research on `main` | MERGED (research-only, `9d04894`, CI 9/9; package unchanged) |
| 1.6.0 (25th class) | CANDIDATE — PR #157; merges with the version bump iff full-suite + hosted-CI green (else 1.5.0 retained) |
| 2.0 public API | GATE DOCUMENTED (§9); no `2.0.0a1` cut |
| scientific calibration | PARTIAL/REFUTED — no measurement-level validation; molar/molal basis unresolved |
| 3.0 falling-sand / LibGibson | FUTURE |

## H. Three highest-value next probes (predeclared outcomes)

1. **Resolve the molar-vs-molal K-scale for K1/K2.** PASS: the self-consistent-scale NIST residual lands within
   Table A1 U_R (±0.0029) → the corroboration is real. FAIL: it stays outside → the NIST agreement was a convention
   artefact. AMBIGUOUS: the primary source does not fix the scale → the claim is permanently UNKNOWN, not corroborated.
2. **A second independently-sourced MEASURED buffer (non-NIST, ideally non-carbonate).** PASS: the model predicts it
   within its stated domain WITHOUT refitting → first genuine predictive-holdout evidence. FAIL: it misses → the
   domain is narrower than claimed. AMBIGUOUS: only model-derived "measurements" available → does not count (common-mode).
3. **A sourced NaCO₃⁻ activity/standard-state correction (NOT deletion).** PASS: a defensible, sourced correction to the
   C-term moves NIST toward 10.014 AND does not worsen the §6 holdouts → a real model improvement. FAIL: no sourced
   correction helps without worsening a holdout → the gap is activity/convention, not the association constant.
   AMBIGUOUS: the correction is not independently sourced → it is tuning, and is refused.
