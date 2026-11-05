# OPERATION XXI section 6 -- Na-carbonate ION-PAIR ablation (PREREGISTRATION)

Ooh yeah, can do!  Written BEFORE any PHREEQC run of this section (the only things done before this file existed were
reading the database text with grep/sed and copying `minteq.v4.dat` into `db/`).  Existence is pain, so: one question,
one instrument, one ablation.

## 1. The question (not prejudged)

`carbonate_equilibrium.py` treats Na+ as fully dissociated -- there are NO Na-carbonate ion pairs.  PHREEQC's
`minteq.v4.dat` carries two.  How much of any SmartChem-vs-PHREEQC high-Na pH gap is attributable to those two pairs?

## 2. Hypotheses

* **H2 (the hypothesis under test):** the Na-carbonate / Na-bicarbonate pairs (NaCO3-, NaHCO3) dominate the high-Na
  SmartChem-vs-PHREEQC pH gap.
* **Rivals (any of which fits a gap with H2 absent):**
  * R-act: the ACTIVITY MODEL (SmartChem = Davies; minteq.v4 = WATEQ/b-dot Debye-Hueckel ion-size model).
  * R-unit: MOLAL vs MOLAR (the grid feeds identical numerics as mol/L to SmartChem and mol/kgw to PHREEQC).
  * R-db: DATABASE CONVENTIONS / constant lineage (minteq.v4 K1,K2 vs the SmartChem K1,K2; phreeqc.dat vs minteq.v4).
* The ablation below isolates ONLY the pair contribution (everything else in PHREEQC is held fixed).  It does NOT
  by itself separate R-act, R-unit, R-db from each other; those remain in the residual SmartChem-vs-PHREEQC-no-pairs gap.

## 3. The instrument and the two databases (NO custom solver)

PHREEQC (via `phreeqpython`) is the ablation instrument.  Both runs use the SAME program, SAME input, SAME everything
except the database.

| DB | file | sha256 |
|---|---|---|
| WITH pairs | `db/minteq.v4.dat` (verbatim copy, PHREEQC 3 release database) | `4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3` |
| NO pairs | `db/minteq.v4.nopairs.dat` (built from the above by the harness) | pinned in `result_s6_na_pair_ablation.json` and the test |

The NO-pairs DB is the WITH-pairs DB with EXACTLY these two SOLUTION_SPECIES reactions (each = its equation line plus
its indented `log_k` / `delta_h` / `-gamma` / comment lines up to the next un-indented line) removed, and NOTHING else:

```
Na+ + CO3-2 = NaCO3-           log_k 1.27     delta_h -20.35 kJ    (minteq.v4.dat line 4872)
Na+ + H+ + CO3-2 = NaHCO3      log_k 10.079   delta_h -28.3301 kJ  (minteq.v4.dat line 4880)
```

(`Na+ + HCO3- = NaHCO3` is therefore log K = 10.079 - 10.329 ~ -0.25.)  The test asserts (by parsing/line-diff) that
the removed text is exactly those two reaction blocks.  Constants are used VERBATIM from the database; never edited.

## 4. Definition of "pair contribution"

Per case, at T = 298.15 K, 1 atm:

* `delta_pH = pH(WITH pairs) - pH(NO pairs)`   (the pair contribution to pH, in database-sourced constants)
* `delta_I  = I(WITH) - I(NO)`
* `Na speciation` (WITH pairs): molal free Na+, NaCO3-, NaHCO3, and the bound fraction
  `(m_NaCO3- + m_NaHCO3) / m_Na_total`.

Three-way table for the carbonate grid: SmartChem (Davies, `pH_activity`, unchanged `carbonate_equilibrium.py`) vs
PHREEQC-NO-pairs vs PHREEQC-WITH-pairs.  The existing `phreeqc.dat` PHREEQC pH (from the committed
`comparison_table.json`; `phreeqc.dat` has no Na-carbonate pairs) is carried as a CONTEXT column only.

## 5. Cases (all declared here, before running)

1. **Carbonate grid:** the existing `../carbonate_phreeqc/grid.json`, as-is (11 cases O1-O6 open pure water, C1-C5
   closed).  Same PHREEQC input conventions as the existing `run_phreeqc.py` (closed: `units mol/kgw`, `Na`, `C(4)`,
   `pH 7 charge`; open: `EQUILIBRIUM_PHASES CO2(g) logP 10.0`), only the database differs.
2. **NIST SRM 191d composition:** 0.025 mol/kg water EACH of NaHCO3 and Na2CO3, CO2-free closed system
   (Na = 0.075 mol/kgw, C(4) = 0.05 mol/kgw, `pH 7 charge`, i.e. PHREEQC adjusts pH to charge balance, as in the grid).  Compared against
   Table 1 pH(S) = 10.014 (U = 0.010) and Table A1 pH(S) = 10.0137 (U_R = 0.0029).  SmartChem's unchanged prediction
   (S5 harness: molality-fed XIX run, and the molarity-fed density interval [1.0007, 1.0018] g/mL) is carried alongside.
3. **FRESH HOLDOUT Na-sweep (declared before running):** closed carbonate system, total carbon C_T = 0.05 (mol/kgw for
   PHREEQC, mol/L numerics for SmartChem as in the grid), no gas phase, charge-balanced pH, with
   **Na / C_T in {0.5, 1.0, 1.5}**, i.e. Na = {0.025, 0.05, 0.075}.  (Na/C = 1.0 is NaHCO3 and Na/C = 1.5 is the NIST
   composition at the same C_T.)  Declared **out-of-domain** (recorded, not forced) if: ionic strength > 0.5 (Davies /
   b-dot domain), or pH > 12 (bare-Na-alkalinity extreme), or PHREEQC fails to converge.  Expected in-domain: I ~ 0.03-0.1.
   The monotonicity expectation (pair contribution grows with Na and with the carbonate fraction) is a stated EXPECTATION to
   be checked, not assumed.

## 6. Reporting and non-verdict commitment

The harness writes raw numbers.  This section produces NUMBERS AND OBSERVATIONS; the corroborated/refuted claim
verdict is NOT written here (left to the orchestrator).  A finding that the pairs do NOT explain the gap is an
acceptable, reportable result.

## 7. NO-TUNING commitment

No constant -- SmartChem's or the database's -- is adjusted, fitted, or re-chosen to improve any agreement.  The DB
`log_k` / `delta_h` values are used verbatim; the NO-pairs DB differs by deletion only.  `carbonate_equilibrium.py`,
`general_coupled.py`, `open_diagram_bridge.py`, `smartchem/`, and the existing `carbonate_phreeqc` benchmark are
byte-identical to `e18e134` (asserted by the test via `git diff`).
