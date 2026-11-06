# Physicalization Round VIII -- the carbonate / CO2 gas-partition 0-D equilibrium (MEGA-ROUND VIII, Phase III)

*The carbonate half of the vinegar+bicarbonate flagship's smallest checkable slice. Source-backed, PHREEQC-benchmarked,
adversarially hardened. Every claim carries a ledger label.*

| field | value |
|---|---|
| status | **research. A new standalone 0-D equilibrium module + an independent benchmark. Branch-only, NOT merged.** |
| branch | `research/physicalization-2x` (off the released 1.1.0 `main` `9e8fa5f`); draft PR #134 |
| new code | `experiments/sandbox_foundation/carbonate_equilibrium.py` (+ tests, + `benchmarks/carbonate_phreeqc/`) |
| scope | the equilibrium END-STATE only -- no time evolution, no kinetics, no bubbles. V3_0 section 3's "spawn bubbles on contact" anti-pattern stays banned; gas here is an OUTPUT of coupled equilibria + a Henry partition |

## 1. What was built

A source-backed, zero-dimensional **carbonate / CO2 aqueous equilibrium with gas partition** -- the sibling of the
acetic-acid/acetate model (`aqueous_equilibrium.py`), built to the same discipline and re-using its machinery
(`SourcedConstant`, the verdict vocabulary, the tolerances, the Davies monovalent kernel, the source-temperature
guards, `Kw`/`c_ref`). A NEW module rather than an extension, because the acetate model's activity bookkeeping is
monovalent-only and **CO3(2-) is the first divalent species** in the sandbox (gamma_2 = gamma_1^4; I weights it x4).

- **Species:** CO2(aq) == H2CO3* (lumped), HCO3-, CO3(2-), H+, OH-, Na+.
- **Equilibria:** K1 (pK1 6.35), K2 (pK2 10.33), Kw, Henry K_H (0.0344 mol/L/atm). Charge balance carries the divalent
  factor: `[Na+]+[H+] = [OH-]+[HCO3-]+2[CO3(2-)]`.
- **Three gas-partition modes** (the open/sealed distinction is PHREEQC Example 7's fixed-partial-pressure vs
  fixed-volume gas phase, applied to a clean carbonate system):
  - `open` -- fixed P_CO2 (infinite reservoir); C_T is an output; reduces to a CUBIC in [H+].
  - `closed` -- fixed dissolved total carbon; no gas exchange; reduces to a QUARTIC in [H+].
  - `sealed` -- fixed total carbon across liquid + a finite headspace; P_CO2 and the dissolved/gas split are outputs;
    solved as two independent eliminations (bracket h vs bracket P_CO2).
- **Solver + fail-closed admission gate**, mirroring the acetate model: two independent algorithmic routes that must
  agree, charge balance, the mode's carbon closure, nonnegativity, Davies convergence + domain. A solver failure
  raises `NumericalVerificationError` -- never returned as a prediction.

## 2. Sourced constants (provenance + uncertainty; nothing fabricated)

| constant | value (25 C) | uncertainty | source |
|---|---|---|---|
| K1 | 10^-6.35 | 5e-8 (pK1 6.35-6.38 inter-source spread) | Harned & Davis JACS 65, 2030 (1943) via CRC / Stumm & Morgan |
| K2 | 10^-10.33 | 5e-12 (pK2 10.32-10.33) | Harned & Scholes JACS 63, 1706 (1941) via CRC / Stumm & Morgan |
| K_H | 0.0344 mol/L/atm | 3e-3 (inter-source 0.031-0.0345) | Sander compilation v5.0.0, ACP 23, 10901 (2023); CO2 top entry Hcp 3.4e-4 mol/m^3/Pa (Burkholder et al. 2019) |
| R | 0.0820574 L*atm/mol/K | 0 (EXACT) | SI 2019 (R, atm both defined) |

**Provenance regime (stated, per [[a-label-is-not-a-binding]]):** these are `SourcedConstant`s -- *label-level*
provenance (citation + the positive-uncertainty discipline, a zero/fabricated error bar refused), NOT the
verifier-minted `SourceBinding` of mechanism_types.py (which is kinetics-only and cannot hold an equilibrium
constant). A caller could inject a fabricated value; the chamber consuming any of this stays structurally SYNTHETIC,
so nothing downstream over-claims. Documented in the module docstring; confirmed as a known edge by the adversary
(finding F2 below).

## 3. Claim ledger

Labels: DEMONSTRATED (independent re-derivation / machine-precision), VERIFIED (equation/implementation benchmark),
OBSERVED (single route this round), EXTERNAL_VALIDATION_UNAVAILABLE, REFUTED.

| # | claim | label | basis |
|---|---|---|---|
| L1 | The open cubic and closed quartic are algebraically exact; the charge-aware Davies algebra (gamma_2=gamma_1^4, K2_c=K2/gamma_2, I with 4*co3) and the sealed carbon conservation are correct | DEMONSTRATED | d'Alembert re-derived all four against a 60-digit Decimal reference; term-by-term identical, machine-precision |
| L2 | pure water + atmospheric CO2 -> pH ~ 5.66; 0.1 M NaHCO3 -> 8.34 (and ~concentration-independent); 0.1 M Na2CO3 -> 11.66; 0.01 M CO2 -> 4.18 | VERIFIED | reproduced by the model AND by PHREEQC; equation verification against the same constants, not experiment |
| L3 | The admission gate never admits a chemically/numerically wrong answer (no false VOUCH) | OBSERVED (strong) | Evil Morty: ~27,000 cases, 9k+ independently cross-checked, zero false SOLVED; gate's per-mode real-check design validated |
| L4 | Model vs PHREEQC (phreeqc.dat, a DIFFERENT activity model + DB): 9 AGREE, 2 MARGINAL, 0 DIVERGE, worst dpH 0.128 | VERIFIED (V1/V2) | `benchmarks/carbonate_phreeqc/comparison_table.json`; open cases agree to <=0.005 pH; the 2 MARGINAL are the high-I Davies-vs-WATEQ gap, honestly labelled |
| L5 | Independent *measured* carbonate end-state validation | EXTERNAL_VALIDATION_UNAVAILABLE | PHREEQC shares the Harned constant lineage (solver verification, not constant validation); no measured datum fabricated |
| L6 | The sealed finite-headspace mode is self-consistent (two eliminations agree ~1e-20; carbon conserves liquid+headspace to machine precision) | DEMONSTRATED (internal) | tests; its PHREEQC cross-check is DEFERRED with an exact GAS_PHASE recipe (PREREGISTRATION.md section 7) |
| L7 | The initial two-route cross-check FALSELY REFUSED strongly basic solutions (washing soda, NaOH, basic open) | REFUTED (and fixed) | both adversaries, independently; see section 4 |

## 4. The adversarial pass, and the one real defect (RED-first, now fixed)

Two orthogonal read-only adversaries ran on the module (authorized own-code hardening): **Evil Morty** (implementation
/ gate exploits) and **d'Alembert** (structure-theorem refutation of the chemistry/algebra).

- **No false VOUCH exists** -- Evil Morty could not produce a single wrong-but-admitted answer in ~27k cases; the
  gate's soundness holds. The algebra is exact (d'Alembert, vs a 60-digit reference).
- **One real defect, failing CLOSED (availability, not soundness):** the two solver routes lost *relative* precision
  for the tiny [H+] of strongly basic solutions -- `np.roots` eigenvalue conditioning on the quartic, plus an
  *absolute* brentq xtol floor -- so the two-route agreement (and the charge residual, amplified by Kw_c/h^2) tripped
  the gate and FALSELY REFUSED legitimate chemistry (1 M Na2CO3 washing soda, 0.01 M NaOH, basic open CO2).
- **Fix (not a loosened gate):** Newton-polish the polynomial root against the exact polynomial, and drive brentq's
  xtol -> 0 so its *relative* rtol governs. `AGREEMENT_RTOL` is UNCHANGED -- the routes now meet it by genuine
  accuracy (~1e-14 relative), so the cross-check keeps its full power to catch a real coefficient bug. The five
  previously-refused cases now solve to their reference pH (washing soda 12.162, NaOH 12.000, ...) and are locked in
  as non-vacuous regression tests (`test_strongly_basic_solutions_solve_not_falsely_refused`).

Lesson: a numerical tolerance calibrated on one system (the acetate CUBIC) does not transfer to a harder one (the
carbonate QUARTIC, worse-conditioned for tiny roots). The gate was sound; the root-finder feeding it needed the
precision the gate assumed. [[a-shared-assumption-cross-check-is-not-independent]] [[checks-derived-from-their-own-subject]]

## 5. Scope and non-goals
- Standalone 0-D equilibrium. NOT wired into the living chamber (that is acetate/sodium-hardwired and pinned by
  tests; a third conserved component is a separate, later step).
- No coupling to the acetate model yet (the full vinegar+bicarbonate fizz couples both; this is the carbonate
  primitive, benchmarked first, exactly as the acetate model shipped standalone first).
- No kinetics, transport, bubbles, or temperature dependence (25 C anchor only; off-T is refused).
