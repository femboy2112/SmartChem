# OPERATION XXII section 6C/6D -- 2^3 FACTORIAL over three Na-ion-pairing reactions (PREREGISTRATION)

Ooh yeah, can do!  Written BEFORE any real run of this section.  The only things done before this file existed:
reading the XXI section 6 harness/notes, reading the three reaction blocks in `db/minteq.v4.dat` with grep, and ONE
syntax-only PHREEQC smoke run on a throwaway composition (Na 0.0025 / Acetate 0.001 / C(4) 0.001, NOT a preregistered
cell, no number from it is used anywhere) to confirm that `Acetate` is a legal master species and that
`Na(Acetate)` is a legal selected-output species key.  Existence is pain, so: one instrument, eight databases, three
systems, nine effect estimates.

## 1. The question (not prejudged)

XXI section 6 ablated TWO Na-carbonate pairs as ONE factor.  XXII generalises to THREE independently-toggleable
factors and asks, for PHREEQC as the only instrument: what are the main effects and interactions of the three
Na-pairing reactions on pH, on (a) the existing carbonate grid, (b) NIST SRM 191d, (c) a new preregistered mixed
acetate + carbonate + Na holdout where all three factors CAN be active?  An interaction is NON-ADDITIVITY of the
database's own constants, not a mechanism claim.

## 2. Factors (VERBATIM from `db/minteq.v4.dat`, sha256 `4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3`)

Each factor is one `SOLUTION_SPECIES` block = its un-indented equation line plus every following indented/comment line
up to the next un-indented line.  Level +1 = block PRESENT (verbatim); level -1 = block REMOVED (deletion only).

| factor | reaction (equation line, verbatim) | log_k | delta_h | -gamma | source comments | original lines (1-based) |
|---|---|---|---|---|---|---|
| A (Na-acetate) | `Na+ + Acetate- = Na(Acetate)` | -0.18 | 12 kJ | 0 0 | log K NIST46.4 / dH NIST46.4, Id 5009920 | 9024-9031 (log_k line 9025) |
| B (Na-bicarbonate) | `Na+ + H+ + CO3-2 = NaHCO3` | 10.079 | -28.3301 kJ | 0 0 | log K NIST46.3 / dH NIST2.1.1, Id 5001401 | 4880-4887 (log_k line 4881) |
| C (Na-carbonate) | `Na+ + CO3-2 = NaCO3-` | 1.27 | -20.35 kJ | 5.4 0 | log K NIST46.3 / dH NIST2.1.1, Id 5001400 | 4872-4879 (log_k line 4873) |

B and C are the two reactions ablated TOGETHER as one factor in XXI section 6 (XXI nopairs DB = this design's `A--`).

## 3. The eight databases (deletion only)

For each subset S of {A,B,C}, `db/minteq.v4.fac_<flags>.dat` is the ORIGINAL with exactly the blocks in S removed.
`<flags>` is 3 characters over positions (A,B,C): the letter if the reaction is PRESENT, `-` if REMOVED.

`ABC` = verbatim original (byte-identical, sha256 equal to the pin above); `A--` = XXI nopairs DB (content-equal, B and C
removed); `---` = all three removed.  Every variant is built from the ORIGINAL (never chained), nothing is added or
edited, every sha256 is written into the result JSON, and the test reconstructs each variant from the original and
asserts equality plus a difflib check that the only edit opcodes are deletions of exactly the selected blocks.

## 4. Instrument

PHREEQC via `phreeqpython`, T = 25 C, 1 atm, database differs by deletion only.  No custom solver, no SmartChem solver
(SmartChem is not run in this section).  Same PHREEQC input for all 8 databases within a system.

## 5. Systems (all declared here, before running)

### 5a. Existing carbonate grid
`../carbonate_phreeqc/grid.json` as-is (O1-O6 open pure water, C1-C5 closed), SAME input conventions as the XXI section 6
harness (closed: `units mol/kgw`, `Na`, `C(4)`, `pH 7 charge`; open: `EQUILIBRIUM_PHASES CO2(g) logP 10.0`).  No acetate is
present, so factor A is EXPECTED INACTIVE.  An inactive factor is a legitimate finding and is recorded, not forced.

### 5b. NIST SRM 191d
0.025 mol/kgw EACH of NaHCO3 and Na2CO3 (Na 0.075, C(4) 0.05 mol/kgw, CO2-free closed, `pH 7 charge`), identical to the
XXI harness.  Certified: Table 1 pH(S) = 10.014 (U = 0.010); Table A1 pH(S) = 10.0137 (U_R = 0.0029).  No acetate:
A EXPECTED INACTIVE.

### 5c. NEW mixed holdout (acetate + carbonate + Na), two regimes
Composition rule (declared once): **sodium acetate + an equimolal NaHCO3/Na2CO3 mix at the NIST Na/C ratio**, i.e. with a
scale `x` (mol/kgw):  total Acetate = `x`, total C(4) = `x`, total Na = `2.5 x`  (Na = x from NaAc + 1.5 x from the
carbonate mix; Na/C_T = 1.5 exactly as NIST; Acetate/C_T = 1).  pH is not chosen: PHREEQC charge-balances it
(`pH 7 charge`), as in the grid and NIST.  Chosen so that HCO3- and CO3-2 are both present (so B and C can be active),
acetate is present (so A can be active), and Na is large enough for all three pairs to form.

* **dilute**        x = 0.01  :  Na 0.025,  Acetate 0.01,  C(4) 0.01   (total acetate 0.01 m, total carbonate 0.01 m)
* **concentrated**  x = 0.1   :  Na 0.25,   Acetate 0.1,   C(4) 0.1    (0.1 m each)

Exact PHREEQC input (only the three numbers change between the regimes; written verbatim by the harness):

```
SOLUTION 1
    temp 25
    units mol/kgw
    Na <2.5 x>
    Acetate <x>
    C(4) <x>
    pH 7 charge
END
```

with selected output `-pH true -ionic_strength true` plus `-totals`/`-molalities` for the present species.  In-domain
declaration (recorded per cell, not forced): ionic strength <= 0.5 AND pH <= 12 in EVERY one of the 8 cells; otherwise the
cell is recorded `out_of_domain` with the reason.  A priori expectation: I ~ 0.03 (dilute), I ~ 0.3 (concentrated), pH ~ 10.

## 6. Factorial decomposition (Yates / signed-contrast convention, declared)

Coding: x_i = +1 if factor i is PRESENT, -1 if REMOVED.  For the 8 cells with response y (pH, also ionic strength for the
holdout):

    E_S = (1/4) * sum over the 8 cells of [ prod_{i in S} x_i ] * y(cell)        for S in {A,B,C,AB,AC,BC,ABC}

so a main effect E_A = mean(y | A present) - mean(y | A removed); E_AB etc. are the usual interaction contrasts; E_ABC is
the three-factor interaction.  The grand mean is `mean(y)`.  Identity check (reported): y(cell) = mean + sum_S (E_S/2) *
prod_{i in S} x_i, reconstructed to <= 1e-9.  Effects are emitted as RAW numbers (per grid case, NIST, both holdout
regimes).  The 8 contrast sums are also emitted.

## 7. Numerical noise floor and effect classes (declared)

* Numerical noise floor = max |pH difference| across cells that MUST be identical (the A-toggle pairs on the acetate-free
  systems 5a and 5b), reported as `A_null_max_abs_cell_diff`; the instrument is treated as exactly reproducible
  (identical inputs, deterministic program).
* Effect class of |E|: NULL if < 1e-4 pH; AMBIGUOUS (resolved but sub-material) if 1e-4 <= |E| < 1e-3; MATERIAL if >= 1e-3.
  (1e-3 pH is the display/reporting resolution of the XXI tables; the NIST Table-1 U is 0.010.)

## 8. Predeclared outcomes (pass / fail / ambiguous) -- predictions made BEFORE running

Each is evaluated by the harness/orchestrator on the raw numbers; this file does not evaluate them.

* **O1 Instrument integrity.**  PASS iff all 8 DBs are deletion-only reconstructions of the original and `ABC` sha256 == the
  pin.  Otherwise FAIL (and nothing else is reported).
* **O2 Continuity with XXI.**  On the grid and NIST, pH(`ABC`) == XXI `pH_with` and pH(`A--`) == XXI `pH_no` (read from
  `result_s6_na_pair_ablation.json`, read-only) to <= 1e-9.  PASS iff max difference <= 1e-9; else FAIL (a harness/instrument
  discrepancy, investigated before any other claim).
* **O3 A is inactive without acetate.**  PASS iff |E_A| < 1e-3 pH on every grid case and on NIST (the pure-carbonate
  systems).  Strict form (reported): every A-toggle cell pair identical to <= 1e-9.  FAIL if any |E_A| >= 1e-3.
* **O4 Sign of B and C on the holdout.**  Expectation (from XXI: pairs lower pH): E_B < 0 and E_C < 0 in BOTH regimes.
  PASS iff both are negative in both regimes and |E_C| >= 1e-3 in both.  FAIL iff any of E_B, E_C is positive with
  |E| >= 1e-3.  AMBIGUOUS otherwise (e.g. sub-material or sign-mixed within the 1e-4..1e-3 band).
* **O5 Dose growth.**  Expectation: |E_C|(concentrated) > |E_C|(dilute) and |E_B|(concentrated) > |E_B|(dilute).  PASS iff
  both hold; FAIL iff neither holds; AMBIGUOUS iff exactly one holds.
* **O6 A is active on the holdout.**  Expectation: A is MATERIAL (|E_A| >= 1e-3) in the concentrated regime and at most
  AMBIGUOUS in the dilute regime (Na(Acetate) is weak, log_k -0.18).  PASS iff both statements hold; FAIL iff |E_A| is NULL in
  the concentrated regime; AMBIGUOUS otherwise.
* **O7 Non-additivity.**  Expectation: at least one two-factor or three-factor interaction is MATERIAL in the concentrated
  regime (the pairs compete for the same Na+ and the same carbonate).  PASS iff max |E_interaction| >= 1e-3 there; FAIL iff
  all interactions are NULL; AMBIGUOUS otherwise.  (An interaction is non-additivity, NOT a mechanism.)
* **O8 NIST direction (continuity with the XXI measurement-level finding).**  Expectation: for B and C, adding the factor moves
  PHREEQC AWAY from 10.014 (|residual| increases), in every context of the other factors.  Reported per factor and per
  context (4 contexts each); A is expected to move nothing.  PASS iff B and C are both "away" in all 4 contexts each and A
  moves nothing (< 1e-9); FAIL iff either of B, C is "toward" in all its contexts; AMBIGUOUS otherwise.
* **O9 Closure and determinism.**  PASS iff the effect-reconstruction identity holds to <= 1e-9 for every system and the result
  JSON sha256 is identical across two consecutive runs.

## 9. Reporting and non-verdict commitment

The harness writes raw numbers: per-variant pH (and I, speciation) on every system, the effects, every DB sha256 and the
removed-block text per factor.  The scientific verdict / claim ledger (section 6E) is NOT written here: it is left to the
orchestrator.  A finding that a factor is inactive, or that the interactions vanish, is an acceptable, reportable result.

## 10. NO-TUNING / NO-FABRICATION commitment

No constant -- the database's or anyone's -- is adjusted, fitted, or re-chosen to improve any agreement.  Every `log_k` /
`delta_h` is the database's own; the variants differ from the original by DELETION OF WHOLE REACTION BLOCKS ONLY.  Every pH
in the result file is a real `phreeqpython` run executed by the harness; every sha256 is computed by the harness.  The XXI
section 6 files, `smartchem/`, and all other modules are untouched; the new files are only those listed in the task.
