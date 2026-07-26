# Polyatomic cost and accuracy — first measurement

Produced by `polyatomic_cost_probe.py` on 2026-07-26. **Every accuracy number here is
UNVALIDATED**: n=6 is a profile sketch, not a validation profile, and the public oracle
still declines these species — correctly.

## Protocol

```
geometry   seed (VSEPR) -> relax (HF/cc-pVDZ, L-BFGS-B) -> Eckart-projected Hessian
energy     CCSD(T)/cc-pVTZ single point at that geometry, plus free atoms at the same tier
ZPE        harmonic, from the cheap-tier Hessian, +9.1% measured bias carried as systematic
reference  experimental D0 derived in code from tabulated 0 K formation enthalpies
machine    8 cores, OMP_NUM_THREADS=1, pyscf 2.14.0
```

## Cost — the planning assumption was wrong by orders of magnitude

| species | atoms | wall clock | note |
|---|---:|---:|---|
| H2O | 3 | 5.7 s | |
| NH3 | 4 | 22.4 s | |
| CH4 | 5 | 25.5 s | |
| H2O2 | 4 | 46.5 s | saddle-descent path exercised |
| CO2 | 3 | 52.2 s | two heavy atoms |
| CH3OH | 6 | 115.9 s | |
| **total** | | **268.2 s** | the whole profile, cold, in 4.5 minutes |

**These are upper bounds.** Load average ran 2.6–3.9 throughout, and this repository has
already been burned once by timing on a contended machine. Contention only inflates a
wall-clock number, so the conclusion — that this is cheap — is safe in the measured
direction. A rerun from the persistent cache costs 0.0 s.

Polyatomic work had been scoped as multi-session on the strength of two *HF*/cc-pVTZ+d
timings, C3H8 at 2515.9 s and CH3OC2H5 at 3444.2 s, where HF served as both geometry engine
and final tier. Separating the tiers is what collapses the cost: the geometry and the
curvature are bought at cc-pVDZ, and only the energy is paid for at cc-pVTZ.

## Accuracy — n=6, plain cc-pVTZ, every error the same sign

| species | predicted D0 (eV) | experiment D0 (eV) | error (eV) | error (kcal/mol) |
|---|---:|---:|---:|---:|
| H2O | 9.1961 | 9.5113 | −0.3153 | −7.27 |
| NH3 | 11.6297 | 11.9988 | −0.3691 | −8.51 |
| CH4 | 16.8523 | 17.0161 | −0.1639 | −3.78 |
| CO2 | 16.1625 | 16.5611 | −0.3986 | −9.19 |
| H2O2 | 10.4328 | 10.9374 | −0.5046 | −11.64 |
| CH3OH | 20.4605 | 20.8540 | −0.3935 | −9.07 |

```
MAE            0.3575 eV   (8.24 kcal/mol)
mean signed   -0.3575 eV   -- all six negative, no cancellation
range          0.1639 (CH4) to 0.5046 (H2O2)
```

## What this establishes, and what it does not

**Establishes:** the fail-closed boundary was right, and now empirically rather than by
argument. The published diatomic MAE is 0.0562 eV. Had the polyatomic path inherited that
bar, the stated uncertainty would have understated the observed error by roughly six times
— on every species, in the same direction, so no amount of averaging would have hidden it.
Declining was not conservatism; it was correct.

**Does not establish:** a validation profile. Six species with no held-out split is a
sketch. It also is **not a tier-matched comparison** — 0.0562 eV was measured at
CCSD(T)/CBS(TZ,QZ) and this is plain cc-pVTZ, one basis short of the extrapolation. The
uniformly negative sign is the signature of basis-set incompleteness, which is precisely
what the CBS extrapolation exists to remove, so the tier-matched number is expected to be
materially better and must be measured before any comparison is quoted.

**Still unknown:** whether CCSD(T) at cc-pVQZ is affordable at C3 size. `_parts` builds
`cc.CCSD(mf)` with no frozen core and no density fitting and never sets `max_memory`
(PySCF default 4000 MB). At 405–520 basis functions the intermediates may not fit. Nothing
here tests that; the largest species measured is 6 atoms at 58–130 basis functions.

## The tier-matched rerun — partial, 3 of 6 in

The extrapolation does what the uniform negative sign predicted it would.

| species | wall clock | error (eV) | error (kcal/mol) | vs. its own cc-pVTZ error | TZ→CBS cost |
|---|---:|---:|---:|---:|---:|
| H2O | 56.5 s | −0.0300 | −0.69 ✓ | 10.5× smaller | 9.9× |
| NH3 | 187.1 s | −0.0609 | −1.40 | 6.1× smaller | 8.4× |
| CH4 | 284.7 s | −0.0364 | −0.84 ✓ | 4.5× smaller | 11.2× |
| CO2 | 608.0 s | −0.0396 | −0.91 ✓ | 10.1× smaller | 11.6× |
| H2O2 | 452.5 s | −0.1090 | −2.51 | 4.6× smaller | 9.73× |
| CH3OH | 1614.3 s | −0.0588 | −1.36 | 6.7× smaller | 13.93× |

```
MAE            0.0558 eV   (1.28 kcal/mol)
published diatomic MAE at the same tier   0.0562 eV      -- 0.74% below it
mean signed   -0.0558 eV   -- all six still negative, no cancellation
range          0.0300 (H2O) to 0.1090 (H2O2)
total wall     3203.1 s = 53.4 minutes for the whole tier-matched profile
```

Three of the six are inside chemical accuracy (1 kcal/mol = 0.0433 eV). The six-species MAE
lands within 1% of the published diatomic figure at the same tier — polyatomic accuracy here
is of the same order as the validated diatomic number, not six times worse as plain cc-pVTZ
implied.

Every error is still negative. Residual underbinding survives the extrapolation; it is now
small rather than dominant, and that it is uniform means it is still systematic rather than
scatter. A 6-species MAE that coincides with the diatomic MAE to within 1% is a striking
number and should be treated with suspicion proportional to how convenient it is: n=6, no
held-out split, and one shared protocol whose ZPE bias is itself a fitted quantity carried
from a different species class.

**H2O2 is the outlier at both tiers** — worst at cc-pVTZ (−0.5046) and worst here. It is
also the one species whose relaxation exercised the saddle-descent path. A harmonic ZPE for
a hindered internal rotor is the obvious suspect and it is not tested here; do not average
it away without looking at it.

**This is 5 of 6 and no held-out split.** It is not a validation profile and must not be
quoted as one.

## Pre-registered predictions for the rest of the run

Written before the remaining species finished, so they can be scored honestly. Recorded in
commit history rather than edited in afterwards.

**P-Q1 — CH3OH at cbs(TZ,QZ) will not follow the observed cost ratio.** The TZ→CBS
wall-clock ratios so far are 9.9× (H2O), 8.4× (NH3), 11.2× (CH4). Naively CH3OH would be
115.9 s × ~10 ≈ 1160 s. But CH3OH needs cc-pVQZ at 230 basis functions / 221 virtual, which
`basis_size_probe.py` models at 2.635 GB and the calibration says to multiply by roughly
five — around 13 GB, against a machine with 7 GB total and ~2 GB free. *Predict: it either
exceeds the harness's 1800 s per-species timeout and is killed, or it completes at a ratio
materially above 11×.* **Falsifier:** completion in ≲1300 s.
**→ CONFIRMED, on its weaker branch, and the margin is modest.** 1614.3 s, a ratio of
13.93× against a prior maximum of 11.65×. The falsifier did not occur. But the prediction's
*stronger* branch — that it would be killed outright — did not happen either, so the ×5
calibration factor was pessimistic at this size. That is consistent rather than lucky: the
calibration ratio was already noted as falling with size (6.1× → 5.2×), and a species that
hits memory pressure, swaps rather than dies, and pays for it in wall clock is exactly the
20%-over-band signature observed. Scored as a hit, but a soft one: "materially above 11×"
was a threshold I set myself, and 13.93× clears it without drama.

**P-Q2 — CO2 and H2O2 both complete.** Modelled at 0.703 and 0.790 GB, so ~3.5–4 GB
calibrated: tight on this box but not over. *Predict both finish inside 1800 s.*
**Falsifier:** either one is killed by the timeout.
**→ CONFIRMED.** CO2 608.0 s, H2O2 452.5 s, both well inside. Cost ratios 11.6× and 9.7×,
both inside the observed 8–11× band, so the memory model's implied cost behaviour holds
where it predicted headroom.

**P-Q3 — the six-species CBS MAE lands between 0.03 and 0.08 eV**, i.e. comparable to the
published 0.0562 eV rather than to the 0.3575 eV measured at plain cc-pVTZ.
**Falsifier:** MAE above 0.15 eV.
**→ CONFIRMED.** 0.0558 eV, mid-band, and 0.74% below the published diatomic figure.

**All three scored: 3 confirmed, 0 falsified.** Worth stating plainly that a clean sweep is
weaker evidence than it feels — these were predictions about a run whose mechanism was
already partly understood, not blind ones, and P-Q1's threshold was self-set. The
falsifiable record exists so the *next* set can be judged against a known calibration, not
so this one can be claimed as vindication.

## The cc-pVQZ affordability question, answered

`basis_size_probe.py` prices it exactly, because basis-function counts depend only on the
elements and never on the geometry. C3H8 at cc-pVQZ is 405 functions and **25.2 GB**, of
which the `vvvv` integral block alone is 22.1 GB. This machine has 7 GB.

The calibration matters more than the number. Run against real CCSD on water,
baseline-subtracted, the model **understates** actual peak RSS by 6.1× at TZ and 5.2× at QZ,
with the ratio still falling as size grows. It is a floor, not an estimate — which makes the
verdict robust to its own uncertainty: even read as an exact lower bound with no multiplier,
25.2 GB against 7 GB is not close.

**And the obvious remedy does not work.** Frozen core is the first thing anyone reaches for,
and it is named in this probe's own docstring:

```
C3H8  cc-pVQZ   occ 13 -> fc 10   t2 0.193 -> 0.114 GB   vvvv 22.103 -> 22.103 GB
```

It cuts the amplitudes 41% and moves the binding constraint by exactly zero, because the
dominant term is quartic in the *virtual* count and contains no occupied index at all.
Density fitting is the remedy that applies — DF-CCSD never forms `vvvv`, and
`pyscf.cc.dfccsd.RCCSD` is present in PySCF 2.14.0. That choice is now a decision on a
number instead of on folklore.

---

# 2026-07-26, second pass: three items worked, two hypotheses dead, one defect found

The three blockers named at the end of the first pass were: the welded gate, the missing
holdout, and H2O2. All three moved, and **one of the three claims below was simply wrong.**

## Item 1 — the gate is now a lock, and the lock is still shut

`validated_profile` had `max_atoms <= 2` as a term in the boolean that produced the accuracy
bar, so "we have not measured this" and "this cannot be measured" were the same state.
Replaced with three protocols consulting three tables (`pyscf_oracle.py`, commit `ea18bab`).
`_RELAXED_GEOMETRY_MAE` is **empty**, so behaviour is byte-identical; evidence now has
somewhere to live. Entries carry `(mae_ev, max_validated_atoms)` because a profile measured
on 4-atom species says nothing about 12.

**The 0.0558 eV above is deliberately NOT entered.** All six species were used to develop and
inspect the protocol, so it is a training error — see item 2 for how badly that matters.

## Item 2 — I was wrong: a holdout exists, and the training MAE understates the error

The first pass asserted "there is no held-out set and none can be assembled from the current
tables." That is true of the **diatomics** and false about everything else. `POLYATOMIC_REFS`
carries **sixteen** species. Only six had ever been computed here. The other ten have curated
thermochemistry and had never been touched by any prediction, timing, or residual inspection.
The only missing input was a bond graph.

Nine added to `TOPOLOGY`, each validated against its own reference row. `C3H7OH` declined:
propan-1-ol and propan-2-ol are both C3H8O, their formation enthalpies differ by more than
this protocol's entire error budget, and `PolyatomicRef` records no structure. That is a
latent defect in the reference table, not an oversight here.

**Holdout at cc-pVTZ, 4 of 9 in** (same protocol, same geometry tier, cache shared):

| species | error (eV) | kcal/mol |
|---|---:|---:|
| CH2O | −0.2901 | −6.69 |
| CH3NH2 | −0.4900 | −11.30 |
| HCOOH | −0.6725 | −15.51 |
| N2H4 | −0.6808 | −15.70 |

```
holdout MAE so far   0.5334 eV   (n=4)
profile MAE          0.3575 eV   (n=6, the set the protocol was developed on)
ratio                1.49x
```

Every error is negative, so the systematic underbinding **does** transfer — that is the
validation signal, and it is the good news. But **two holdout species are worse than anything
in the profile**, and the six-species figure understates the spread by about half. A training
MAE quoted as an accuracy tier would have been optimistic by 1.5x at this tier. This is
exactly why the 0.0558 eV was not entered into the table in item 1.

> **Superseded — see the third pass below.** C2H6 landed at −0.2769 eV and moved the holdout
> MAE from 0.5334 (n=4) to 0.4821 (n=5) and the ratio from 1.49x to 1.35x. The four remaining
> species were dropped against the memory wall, priced there. The table above is the n=4
> snapshot and is kept as the record of what was known at the time.

The remaining five (C2H6, C2H5OH, CH3OCH3, C3H8, CH3OC2H5) are still running. The
tier-matched cbs(TZ,QZ) holdout is affordable only for CH2O, N2H4 and HCOOH — CH3NH2 at
4.3 GB modelled is a stretch and C2H6 upward is out, per `basis_size_probe.py`.

## Item 3 — H2O2: both suspects refuted

**The hindered rotor is dead, by its own upper bound.** `vibrational_probe.py` dumps every
harmonic mode. H2O2's torsion is **377.8 cm⁻¹ carrying 0.0234 eV — 2.9% of its ZPE**, at a
dihedral of −115.0° (the trans-planar saddle is 180°, so the saddle descent did its job).
The cbs(TZ,QZ) error is −0.1090 eV. Deleting the mode outright — far more than any
hindered-rotor correction can do — leaves −0.0856 eV, still the worst species by a
comfortable margin over NH3's −0.0609. **The mode cannot carry the error.**

**Multireference character is dead too.** H2O2 is the only species with an O–O single bond,
the textbook single-determinant failure. `multireference_probe.py` reads the CCSD(T)
amplitudes:

| species | T1 | D1 | (T)/E_corr | err eV |
|---|---:|---:|---:|---:|
| H2O2 | 0.00794 | 0.01913 | 0.03364 | −0.1090 |
| NH3 | 0.00550 | 0.00959 | 0.02957 | −0.0609 |
| CH3OH | 0.00736 | 0.01683 | 0.03129 | −0.0588 |
| CO2 | **0.01458** | **0.04400** | **0.04423** | −0.0396 |
| CH4 | 0.00676 | 0.01211 | 0.02745 | −0.0364 |
| H2O | 0.00564 | 0.01028 | 0.02740 | −0.0300 |

Nothing exceeds the conventional T1 > 0.02 or D1 > 0.05. H2O2 sits at 0.00794, comfortably
single-reference, and the species with the **highest** diagnostic on all three columns is
only fourth in error. The ordering runs against the hypothesis.

**And the holdout killed the peroxide framing outright.** `N2H4` was added specifically as
the N–N single-bond analogue of H2O2 — the discriminating species, written into `TOPOLOGY`
with that stated purpose before the sweep was launched. It came back at **−0.6808 eV, worse
than H2O2's −0.5046 at the same tier.** So whatever this is, it is not about the O–O bond.
(Weaker evidence than the P-Q series: written before the data arrived, but not
git-committed first.)

## What the red-team found instead: a silent wrong answer

An adversarial review aimed at the ZPE-bias transfer went looking for a competing explanation
and found a defect in `harmonic_analysis`. Verified independently here on a real HF/cc-pVDZ
Hessian rather than the synthetic case reported:

```
CO2 at r(C-O)=1.1430 A, one oxygen displaced perpendicular by delta

delta <= 1e-8 A   5 external  4 modes  ZPE 0.3466 eV  [768.3 768.3 1500.5 2554.1]
delta >= 1e-7 A   6 external  3 modes  ZPE 0.2990 eV  [768.3 1500.5 2554.1]
```

Two linearity criteria in one file, five orders of magnitude apart — `_external_modes` at
1e-8, `is_linear` at 1e-3 — and between them a physically linear molecule loses a genuine
degenerate bend with no error and no warning. **0.0476 eV**, larger than chemical accuracy
and larger than the whole polyatomic MAE. Fixed in `050e6f6` by refusing when the two
disagree. Not reachable by the six measured species; it arms for near-linear geometries that
do not land exactly on axis.

## Two things the red-team is right about that are not yet acted on

1. **The 9.1% ZPE bias is evaluated entirely outside its fitted range.** The 23 training ZPEs
   run 0.00986–0.27284 eV. Every polyatomic ZPE is *above* the maximum: CO2 1.28×, CH3OH
   5.46×. A one-parameter model, 5.5× out of range, on six points. That is a sharper problem
   than the bends-versus-stretches framing, which the data actually anti-supports.
2. **Two systematics are omitted and unnamed.** `grep -rE "spin.orbit|relativis|counterpoise|BSSE" smartchem/`
   returns zero hits, and `cc.CCSD(mf)` at `pyscf_oracle.py:637` is all-electron in a
   valence-only basis whose correlation energy is then X⁻³-extrapolated. Both push the same
   direction as the observed residual and both scale with heavy-atom count.

## The live suspect

A CCSD(T) single point evaluated off the true minimum is **strictly above** it, second order
in the displacement — so it cannot change sign, and every error measured here is negative.
The geometry is HF/cc-pVDZ with a measured 0.0255 Å r_e MAE. `_GEOMETRY_METHODS = ("HF",)`
is the boundary: only the geometry *basis* can be varied through the public constructor, so
the clean test is HF/cc-pVDZ versus HF/cc-pVTZ on the same species. That is the next probe,
and it has not been run.

---

# 2026-07-26, third pass: the holdout closes, the live suspect dies, and a prediction is filed

## The cc-pVTZ holdout, final at n=5 — and what was dropped, priced

| species | error (eV) | kcal/mol |
|---|---:|---:|
| C2H6 | −0.2769 | −6.39 |
| CH2O | −0.2901 | −6.69 |
| CH3NH2 | −0.4900 | −11.30 |
| HCOOH | −0.6725 | −15.51 |
| N2H4 | −0.6808 | −15.70 |

```
holdout MAE   0.4821 eV   (n=5)
profile MAE   0.3575 eV   (n=6, the set the protocol was developed on)
ratio         1.35x
```

C2H6 landing at −0.2769 matters: it is the largest species measured and among the *best*, which
kills "error grows with size" as a simple story. The 1.49x ratio reported at n=4 was an artefact
of which four had finished first; at n=5 it is 1.35x. The direction of the finding is unchanged —
the training MAE understates the holdout — but the magnitude moved by a seventh on one added
species, which is the honest measure of how little n=5 constrains.

**Four species were dropped, and this is the reason, not a rounding of the roster.** Modelled
CCSD(T) `vvvv` storage at cc-pVTZ against a 7 GB box that was concurrently committed to the
higher-value cbs(TZ,QZ) run:

| dropped | vvvv GB @ cc-pVTZ |
|---|---:|
| C2H5OH | 5.0 |
| CH3OCH3 | 5.0 |
| C3H8 | 9.5 |
| CH3OC2H5 | 15.9 |

C2H5OH was killed in flight at 785 s with 1560 MB resident and the box down to 411 MB available.
C3H8 and CH3OC2H5 cannot be run on this hardware at this tier at all. **The holdout is n=5 of a
possible 9, and every number that follows is a statement about those five.**

## The live suspect is refuted — and it fails in the informative direction

Same energy tier (CCSD(T)/cc-pVTZ), only the geometry basis varied. One cache file **per
geometry tier**, so a stale HF/cc-pVDZ answer cannot alias into an HF/cc-pVTZ slot — the
failure mode that would have manufactured a difference of exactly zero and published
"geometry does not matter."

| species | geom HF/cc-pVDZ | geom HF/cc-pVTZ | Δ | Δ as % of error |
|---|---:|---:|---:|---:|
| H2O | −0.3153 | −0.3259 | −0.0106 | 3.4% |
| H2O2 | −0.5046 | −0.5327 | −0.0281 | 5.6% |

**The geometry tier is not the dominant cause.** It moves 3–6% of an error that needs to move
by 100%. But it does not move to zero, and it moves the *wrong way*: upgrading the geometry
basis makes the atomization energy worse, consistently, in both species. That is a real
finding and it inverts the obvious remedy — "use a better geometry" is a *degradation* here.

Two collateral results:

* The DZ-geometry H2O2 number reproduced as **−0.5046 eV from a cold cache**, bit-identical to
  the value recorded above. The pipeline is deterministic and the earlier figure is
  reproducible — a regression anchor obtained for free.
* The H2O ZPE moved 0.6262 → 0.6265 eV across the geometry-basis change (0.0003 eV). The
  concern that a changed Hessian basis would confound the geometry-position effect — and
  silently void the provenance of `ZPE_BIAS_FRACTION`, which was fitted at HF/cc-pVDZ — does
  not bite at this magnitude for H2O.

**And the claim this probe was testing has no surviving evidence.** `pyscf_oracle.py:714` says
the geometry-delegation design is `MEASURED -- see scratchpad/geometry_tier.py`. That file is
in **no commit on any branch** (`git log --all --diff-filter=A` finds nothing) and `scratchpad/`
does not exist. It is the same pattern as the lost `geom_calibrate.py` behind
`ZPE_BIAS_FRACTION`. The measurement above re-establishes the claim's *direction*
independently — geometry position really is a small effect — which is the only reason the
delegation design survives contact with its own missing evidence.

## Pre-registered prediction for the cbs(TZ,QZ) holdout

**Filed before any cbs number for these three existed.** Basis: across the 11 species measured
at cc-pVTZ, the best structural correlate of the error is **valence electron pairs correlated**
(Pearson r = 0.662 against |error|; Spearman ρ = 0.66, p = 0.029). Bond count (r = 0.11) and
π-bond count (r = 0.09) are dead — and in this all-acyclic set bond count is an affine
restatement of atom count, so it was never an independent axis. ZPE is *exactly* uncorrelated
with the error (Spearman ρ = 0.000), which kills "big-ZPE species have big errors."

The correlate's strongest evidence is that it transfers across the split it was not fitted on:
err/valence-pair is −0.06503 eV on the profile and −0.06598 eV on the holdout.

| species | predicted cbs(TZ,QZ) error | interval |
|---|---:|---|
| CH2O | −0.05 eV | −0.03 to −0.07 |
| HCOOH | −0.10 eV | −0.07 to −0.13 |
| N2H4 | −0.10 eV | −0.08 to −0.17 |

**N2H4's interval is deliberately wider and skewed deep.** It is already the worst species at
cc-pVTZ and already off the valence-pair trend by 49%; the only other known outlier, H2O2, was
underpredicted by ~0.04 eV in leave-one-out. If N2H4 lands past −0.17 the correlate is refuted
outright, not merely loose.

**The honest caveat, filed with the prediction rather than after it:** the correlate explains
under half the variance (R² = 0.44), and it gets *looser* at the CBS tier, not tighter — the
coefficient of variation of err/valence-pair rises from 0.290 at cc-pVTZ to 0.390 at
cbs(TZ,QZ). H2O2 and CH3OH have identical valence-pair counts (7) and CBS errors of −0.1090
and −0.0588, nearly 2x apart. So "countable, additive, removed by CBS" is a first-order truth
with a real second-order residual this prediction does not capture. A separate unexplained
pattern: the three nitrogen species (NH3, N2H4, CH3NH2) average −0.087 eV per valence pair
against −0.058 for the rest, and nothing here explains why.

## The gate decision rule, also filed before the numbers

`_RELAXED_GEOMETRY_MAE` is empty and every lookup misses, so the public oracle declines every
polyatomic. The cbs(TZ,QZ) holdout now running is the evidence that could populate it. The
temptation, once three tidy numbers exist, will be to enter their mean. **The rule below is
written now so that decision is made against a standard rather than against a result.**

An entry `(mae_ev, max_validated_atoms)` may be added only when **all** of these hold:

1. The MAE comes from species **never used to develop the protocol**. The six profile species
   are permanently disqualified as evidence for their own gate.
2. **n ≥ 8.** Three species is a data point cluster, not a validation profile. The n=4 → n=5
   move above shifted the holdout ratio by a seventh on one species; at n=3 the standard error
   of the mean is not meaningfully bounded, and a bar quoted from it would be a plausible
   number with nothing behind it.
3. `max_validated_atoms` is the atom count of the **largest species actually measured**, never
   extrapolated. A profile earned on 4-atom species does not license a 12-atom one.
4. The spread is reported alongside the mean. A 3x range across the holdout makes the MAE a
   summary statistic of a distribution nobody has characterised, and the `uncertainty_ev` it
   would feed is a per-species claim, not an average one.

**On this session's evidence the expected outcome is that the gate stays shut**, because the
affordable cbs holdout is n=3 and criterion 2 fails by construction on this hardware. That is
not a failure of the run — the run's job is to measure the residual and price what a real
profile would cost, and a measurement that says "not yet" is the correct output of a protocol
whose entire thesis is that a plausible wrong number is worse than no number.
