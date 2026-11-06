# OPERATION XXII §6 — Na-pairing 2³ factorial: ORCHESTRATOR VERDICT (6A/6B/6E)

**Instrument:** PHREEQC via phreeqpython, 25 °C, 1 atm; minteq.v4 with each of three Na-pairing associations toggled by
DELETION ONLY (no constant edited). Raw tables: `result_s6b_factorial.json` (sha256 `a1aa9ff3…`, reproducible).
Factors: **A** Na-acetate (`Na+ + Acetate- = Na(Acetate)`, log K −0.18), **B** Na-bicarbonate (`Na+ + H+ + CO3-2 =
NaHCO3`, log K 10.079), **C** Na-carbonate (`Na+ + CO3-2 = NaCO3-`, log K 1.27). All effects below are PHREEQC runs I
re-ran and read from the JSON myself (DB shas, 23-test suite, and result sha independently verified).

## 6E — model-selection verdict (the headline, verdict-CHANGING)

**XXI's "the two Na-carbonate pairs move PHREEQC ~0.14 pH AWAY from NIST" was the NET of two OPPOSING effects, and the
single "both-pairs" factor MASKED a cancellation.** The 2³ factorial separates them on the NIST SRM 191d point
(certified Table-1 pH 10.014, U 0.010):

| factor toggled | NIST pH effect | direction vs 10.014 | holds in all 4 contexts of the other factors? |
|---|---|---|---|
| **A** Na-acetate | 0.000 | — (no acetate present) | yes (exactly 0) |
| **B** Na-bicarbonate (NaHCO₃) | **+0.0115** | **TOWARD** (|resid| −0.0115) | yes |
| **C** Na-carbonate (NaCO₃⁻) | **−0.1534** | **AWAY** (|resid| +0.1534) | yes |

Per-variant residual vs 10.014: `---`/`A--` −0.0148; **`-B-`/`AB-` −0.0033 (INSIDE U=0.010)**; `--C`/`A-C` −0.168;
`-BC`/`ABC` −0.157. XXI's "with" = `ABC` and "no" = `A--` reproduce to 0.0.

So the measurement discrepancy lives almost entirely in the **C (NaCO₃⁻)** term; the **B (NaHCO₃)** association actually
improves the NIST agreement. **This refutes the implicit XXI framing** (both carbonate pairs as one block that moves
away) — the two act in opposite directions and their XXI-combined effect was C-dominated.

**But the best-fitting variant is a DIAGNOSTIC, not a model correction.** `-B-`/`AB-` reaches NIST only by DELETING a
real, NIST46.3-sourced association (NaCO₃⁻). Dropping a sourced ion-pair to fit one measurement is the banned move
(no tuning, no reality-bending). The factorial *locates* the discrepancy in C; it does not license removing C. The
residual that survives even the best ablation (−0.0033) sits inside Table-1 U but does **not** resolve the XXI §4
activity/convention/standard-state refutations (Table A1 ±0.0029 and the molar-vs-molal scale transport), which this
ablation holds fixed and cannot touch.

**Interactions are negligible — the Na-pairings SUPERPOSE.** At NIST every two- and three-factor effect is |E| < 6e-4;
in the concentrated mixed holdout the largest interaction is AC = +0.0036 (a weak Na-acetate↔Na-carbonate competition
for free Na⁺) and ABC ≈ −9e-6. **Hypothesis H5 (an interaction term is required) is NOT supported** on this system:
the three contributions add. This is itself a finding the XXI 1-factor experiment could not make.

## 6A — source provenance (which assumptions are shared vs independent)

All three association constants carry the SAME lineage in minteq.v4: log K from **NIST46** (A: 46.4; B,C: 46.3),
ΔH from NIST (2.1.1 / 46.4), on the DB's **b-dot/Debye–Hückel** activity model (`-gamma`) and **molal** standard state.
K1/K2 and the H⁺ single-ion convention are likewise the DB's own. The ablation changes ONLY whether each association
equilibrium is present; it does **not** separate activity-model, molal-vs-molar, or K-lineage contributions — those are
common-mode across every cell and remain the unresolved DARK residual (the SmartChem-vs-PHREEQC-no-pairs ~0.002 offset
on Na-free cases confirms a non-pair discrepancy floor).

## 6B — thermodynamic common basis

A common-basis comparison with the NIST **measurement** still requires the molar↔molal↔standard-state transform left
open in XXI §4; the factorial is a **model-vs-model** decomposition on a fixed (molal, b-dot) basis, so it re-attributes
the model gap (B vs C) but leaves the measurement-level verdict where XXI §4 put it: corroborated only within Table 1
(thin), refuted at Table A1 and under scale transport. No invented transform substitutes for that law.

## Predeclared-outcome flips (honest)

Two preregistered outcomes came out FAIL on mechanical application: the sign of B/C on the holdout and the NIST
direction were predicted from the XXI "both pairs move away" expectation. **The factorial overturning that expectation
is the verdict-changing result** — a preregistered prediction was refuted by a no-tune, reproducible experiment. That
is scientific progress recorded, not a failure hidden.

## Status

Verified both ways by the orchestrator: deletion-only DB construction (8 sha-pinned variants; `ABC`==original,
`A--`==the XXI nopairs pin), 23/23 tests re-run, result JSON reproducible. No tuning, no fabricated constants, PHREEQC
the only instrument. The §6E verdict and the 6A/6B provenance notes are the orchestrator's; the harness wrote no
conclusion.
