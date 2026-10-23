# Wave D -- PREREGISTRATION (written BEFORE any speciation run; only DB *inspection* preceded it)

Target under test: `experiments/sandbox_foundation/aqueous_equilibrium.py` @ repo HEAD 22ef51713cbcd83377c39f16020622b76e514a69
(`AcetateWaterSystem.solve`, Wave A: `pH_activity`, `pH_concentration`, `verdict`).
Instrument: PHREEQC (IPhreeqc VIPhreeqc.so) via `phreeqpython` 1.6.2 in isolated venv `wave-d/venv`.

## 0. Pre-run discovery that changed the plan (recorded, not hidden)
The four databases bundled with phreeqpython (phreeqc.dat, pitzer.dat, vitens.dat, wateq4f_PWN.dat) contain NO acetate
species (grep for acetate/CH3COO/Ac-/HAcet: empty; phreeqc.dat sha256 6bb5ebc1...bdf5). The brief's "phreeqc.dat" route is
therefore impossible without hand-adding acetate (which would re-import the code's own constant -> not independent).
Substitute: official USGS phreeqc3 databases that DO carry acetate, fetched from
https://raw.githubusercontent.com/usgs-coupled/phreeqc3/master/database/ :
  * PRIMARY   `minteq.v4.dat`  sha256 4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3
              H+ + Acetate- = H(Acetate) log_k 4.757 (NIST46.4); H2O = OH- + H+ log_k -13.997; Na+ + Acetate- = Na(Acetate) log_k -0.18
  * SECONDARY `llnl.dat`       sha256 1324b807f0f864806fc42df308f6ca7c5e8ce2ed8060d76351452f76beeb819b
              HAcetate = Acetate- + H+ log_k -4.7572; H2O = OH- + H+ log_k -13.9951; Na+ + HAcetate = NaAcetate + H+ log_k -4.8606
              (=> Na+ + Ac- = NaAc, logK ~ -0.1034)
Code constants for contrast: Ka = 1.75e-5 (pKa 4.75696, CRC 84th), Kw = 1.0e-14 (pKw 14.000), Davies A = 0.509.

INDEPENDENCE CAVEAT (pre-declared): the acetic-acid pKa ~4.757 in every database traces to the same classical EMF/conductance
work (Harned & Ehlers 1932; MacInnes & Shedlovsky 1932), so agreement of *Ka* is NOT independent evidence for Ka.
What IS independent here: (i) the PHREEQC solver/implementation, (ii) the activity-coefficient model & its parameters,
(iii) the species set (PHREEQC includes the NaAc ion pair; the code does not), (iv) Kw/pKw value choice.
A match on Ka-driven quantities is therefore EQUATION/IMPLEMENTATION VERIFICATION + activity-model cross-check,
not validation of Ka. Genuine independent validation = comparison to a MEASURED datum (section 7).

## 1. Cases (all T = 298.15 K, P = 1 atm; PHREEQC input in mol/L solution, `units mol/l`)
Required five:
 C1 pure water                 C_T=0      Na=0
 C2 dilute acetic acid         C_T=0.10   Na=0
 C3 half-neutralised buffer    C_T=0.10   Na=0.05
 C4 sodium acetate             C_T=0.10   Na=0.10
 C5 near Davies boundary       C_T=0.45   Na=0.45   (ionic strength ~0.45 <= DAVIES_I_MAX=0.5, expected still admitted)
Extended domain grid (C_T in {0.001, 0.01, 0.1}) x (Na/C_T in {0, 0.5, 1.0}), plus
 C6 refusal probe  C_T=0.60 Na=0.60 (I>0.5: code is expected to REFUSE; PHREEQC computed for information only).
PHREEQC pH solved by `pH <guess> charge` (pH adjusted to electroneutrality) -- same closure as the code's charge balance.

## 2. Species
Code: H2O(solvent), H+, OH-, HAc, Ac-, Na+ (Na+ fully dissociated; no ion pair).
PHREEQC minteq.v4: H+, OH-, Acetate-, H(Acetate), Na+, Na(Acetate) ion pair (+ trace others in DB; ignored).
PHREEQC llnl: H+, OH-, Acetate-, HAcetate, Na+, NaAcetate ion pair.
Total-acetate mass balance in PHREEQC = Acetate- + HAc + NaAc (all acetate-bearing species).

## 3. Standard states / activity models (DIFFERENCES RECORDED, not papered over)
* Concentration scale: PHREEQC works in molality (mol/kgw); code works in molarity (mol/L) with c_ref=1 mol/L.
  I convert PHREEQC species to mol/L as n_i / V_solution (V from PHREEQC's own density/mass). Residual molal-vs-molar
  difference is inherent (<~3% in concentration, <~0.013 pH at 0.5 M) and is part of the budget, not corrected away.
* Activity model: code = Davies (log g = -A(sqrt(I)/(1+sqrt(I)) - 0.3 I), A=0.509 fixed, all ions same g, HAc g=1);
  PHREEQC minteq.v4 = Davies for ions lacking `-gamma` (A from PHREEQC's T-dependent DH-A, ~0.5114 at 25 C) with some
  species carrying `-gamma a b` (WATEQ DH); llnl.dat = `-llnl_gamma` extended DH (B-dot). Actual per-species gammas are
  READ OUT of PHREEQC and recorded, not assumed.
* pH: code `pH_activity` = -log10(g * [H+]/c_ref) (molar, Davies) ; `pH_concentration` = -log10([H+]/c_ref).
  PHREEQC `pH` = -log10(a_H+), a = gamma*molality (molal). I compare code `pH_activity` <-> PHREEQC pH (primary),
  and report code `pH_concentration` <-> PHREEQC -log10(molarity H+) as secondary.
  Ideal-mode (`activity_model="ideal"`) is also run and compared to PHREEQC *concentration* pH, labeled "ideal-vs-nonideal baseline".
* Ionic strength: code I=0.5*(H+OH+Ac+Na) (molar); PHREEQC I = 0.5 sum m z^2 over ALL species incl. pairs (molal).

## 4. Domain bounds
T = 298.15 K only (code refuses otherwise; I do not test other T). Ionic strength: code admits I<=0.5 M; grid spans I ~ 1e-5..0.60.

## 5. Numerical tolerances / metrics (fixed now, NOT tuned after seeing data)
* PRIMARY metric: |dpH| = |pH_code_primary - pH_PHREEQC|.
    AGREE      : |dpH| <= 0.02   (~ practical glass-electrode pH reproducibility; a model-resolution scale, not a solver tolerance)
    MARGINAL   : 0.02 < |dpH| <= 0.05
    DIVERGE    : |dpH| > 0.05
* Species: relative error |c_code - c_ph|/c_ph for H+, Ac-, HAc (PHREEQC molar, HAc & Ac- NOT merged with NaAc); agree <= 5%.
* PHREEQC internal mass balance (sum of acetate species vs C_T) and charge balance must close to <= 1e-6 relative / 1e-9 M abs, or the PHREEQC point is discarded.
* Code admission: if solve() raises NumericalVerificationError that IS the recorded outcome (not an error to hide).
* Both PHREEQC DBs run; I report each separately and the spread between the two DBs (a measure of instrument-model uncertainty).
  A "domain of agreement" = the cases where |dpH| <= 0.02 against BOTH DBs.

## 6. Explanatory diagnostics (allowed, but labelled DIAGNOSTIC, never used for the agree/diverge verdict)
 D1 code re-run with PHREEQC-DB pKa/pKw (SourcedConstant built in scratch) to isolate constants vs activity model.
 D2 PHREEQC minteq run with the NaAc ion pair removed (scratch copy of DB) to isolate the species-set difference.
Sign/size of the two effects is NOT predicted in advance beyond: pair effect grows with Na and C_T; Davies-vs-DH difference grows with I.

## 7. Verification vs validation labelling
* PHREEQC agreement at dilute C_T / Na=0 (activity ~ 1, Ka-dominated): EQUATION/IMPLEMENTATION VERIFICATION only (same Ka lineage).
* PHREEQC agreement/divergence at higher I: genuine independent cross-check of the ACTIVITY MODEL + SPECIES SCOPE.
* Measured-datum comparison (web literature, 25 C acetic acid/acetate pH): the only item eligible to be called VALIDATION;
  if no defensible measured datum with traceable provenance is found => UNKNOWN. No datum is back-computed from the code's Ka.

---
# AMENDMENTS & RUN RECORD (appended after the runs; each labelled with whether it preceded the code-vs-PHREEQC comparison)

A0 (before any run) The brief's phreeqc.dat has no acetate; USGS minteq.v4.dat (primary) and llnl.dat (secondary) were substituted. See section 0.
A1 (before comparison) `get_volume()` in these DBs is the WATER volume (1.0030 L/kg in minteq, 1.0000 in llnl), not the solution volume,
   so n_i/V is not molarity. Molarity := m_i * rho_PHREEQC / (1 + sum m_j M_j/1000).
A2 (before comparison) PHREEQC `units mol/l` converts to molality assuming density 1.0 g/mL (observed: Na_total_molarity / input = rho_calc, e.g. 1.0353 at C5),
   so it is NOT a true molar input. Replaced by "molar-matched": fixed-point on mol/kgw input until sum-of-species molarities reproduce the requested C_T, Na
   (control: max deviation 3.2e-9 M over all 120 runs; max |charge residual| 2.4e-9 mol/kgw). The raw mol/kgw numerical-identification run is kept as a sensitivity
   (|pH(matched)-pH(kgw)| <= 0.0005 at C3-C5 in minteq, <= 0.00005 in llnl).
A3 (before comparison) llnl.dat species used by PHREEQC at 25 C come from `-analytic`, which OVERRIDES the printed `log_k`. Effective 25 C values computed from the analytic terms
   (python): logK(H2O=H+ + OH-) = -14.0162 (printed -13.9951); logK(HAc=Ac- + H+) = -4.7722 (printed -4.7572); logK(Na+ + Ac- = NaAc) = -0.0785.
   Check: PHREEQC llnl pure-water pH = 7.0081 = 14.0162/2 (Observed, matches). So llnl carries pKa ~4.772 and pKw ~14.016 at 25 C -> deviates from the consensus pKa 4.757 / pKw 13.995.
   llnl species set also includes Na(Acetate)2- and NaOH (added to my species table; runner errors if any unmodelled species > 1e-12 mol/kgw).
A4 (before comparison) noNaAcPair scratch variants: minteq `Na+ + Acetate- = Na(Acetate)` log_k -0.18 -> -40; llnl `Na+ + HAcetate = NaAcetate + H+` log_k & -analytic -> -40, and `2 HAcetate + Na+ = Na(Acetate)2- + 2 H+` -> -80.
   (First llnl attempt failed silently because -analytic overrides log_k; caught because noPair == pair to 4 digits at C3 while I != nominal.)
A5 (AFTER seeing C5 DIVERGE; post-hoc, exploratory) 1-D scans (NaAc series, buffer series, HAc series; grid_scan.json) to locate where |dpH| crosses 0.02 and 0.05. Not part of the pre-registered verdict set.
A6 Tolerance for the molar-matching control (1e-8 M) and "charge-residual" are my choices; prereg said <=1e-6 relative.
