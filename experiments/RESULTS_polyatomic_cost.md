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

That aliasing turns out **not** to have been live, and this is now measured rather than
assumed: `persistent._fingerprint` hashes a descriptor built from `calculation_spec`, which
carries `geometry_tier` (`pyscf_oracle.py:598`). Three configurations, three distinct
fingerprints — `d87102f1…` for HF/cc-pVDZ, `35104e4d…` for HF/cc-pVTZ, `5eb177b3…` for no
geometry tier. The separate cache files were therefore redundant. They were also free, and
the choice to make the failure structurally impossible rather than merely checked is the
one worth repeating: the check came back clean, but it came back *after* the experiment
would have been run.

| species | geom HF/cc-pVDZ | geom HF/cc-pVTZ | Δ | Δ as % of error |
|---|---:|---:|---:|---:|
| H2O | −0.3153 | −0.3259 | −0.0106 | 3.4% |
| H2O2 | −0.5046 | −0.5327 | −0.0281 | 5.6% |
| N2H4 | −0.6808 | −0.6974 | −0.0166 | 2.4% |

**The geometry tier is not the dominant cause.** It moves 2–6% of an error that needs to move
by 100%. But it does not move to zero, and it moves the *wrong way*: upgrading the geometry
basis makes the atomization energy worse, consistently, in both species. That is a real
finding and it inverts the obvious remedy — "use a better geometry" is a *degradation* here.

**The mechanism, confirmed rather than asserted.** Relaxing through the pipeline's own
`_relaxed_geometry` at both bases (H2O2 hit the trans-planar saddle first at *both*, and the
descent recovered the skewed minimum at both — documented behaviour, not a failure):

| coordinate | HF/cc-pVDZ | HF/cc-pVTZ | experiment | \|DZ err\| | \|TZ err\| |
|---|---:|---:|---:|---:|---:|
| H2O r(O–H) / Å | 0.9463 | 0.9406 | 0.9572 | 0.0109 | 0.0166 |
| H2O2 r(O–O) / Å | 1.3925 | 1.3873 | 1.4556 | 0.0631 | 0.0683 |
| H2O2 r(O–H) / Å | 0.9482 | 0.9422 | 0.9670 | 0.0188 | 0.0248 |

Every bond shrinks DZ→TZ (3 of 3) and every DZ bond is closer to experiment (3 of 3). HF
bonds are too short because HF has no correlation to pull them out; a larger basis converges
HF toward its own even-shorter limit; cc-pVDZ's incompleteness lengthens bonds and partially
cancels the deficiency. A CCSD(T) single point at a too-short bond lies **above** the true
minimum, which underbinds, which is negative — and the shorter TZ geometry lies further out.
That reproduces the sign and the rough magnitude of both energy deltas above, so the
mechanism is not a story fitted after the fact.

**The counterexample, which is not being buried.** Generalised past bond length the framing
breaks. The H2O2 H–O–O–H dihedral is 115.04° at cc-pVDZ against 111.70° at cc-pVTZ, and
experiment is 111.5° — for the torsional coordinate that actually governs this molecule's
non-planarity, **cc-pVTZ is better by an order of magnitude** (0.20° vs 3.54°). So the
correct statement is narrow: *bond lengths* benefit from a fortuitous cancellation at
cc-pVDZ. "cc-pVDZ is the better geometry basis" is false as stated, and the angular degrees
of freedom are driven by something else entirely.

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

## The midterm goal, done: `ZPE_BIAS_FRACTION` is re-derivable, and it does not re-derive

`experiments/zpe_bias_refit.py` is committed. It is the replacement for
`scratchpad/geom_calibrate.py`, which was never committed and is gone, and it makes 0.091
reproducible for the first time in this repository's history. Bond orders come from
`BOND_REFS` rather than a table written in the harness, so the calibration carries no
hand-authored hidden variable.

**It does not come back as 0.091 on any protocol or denominator.**

| protocol | n | f_A = Δ/reference | f_B = Δ/computed |
|---|---:|---:|---:|
| relax + Hessian — *the production path* | 21 / 23 | **0.0801** (sd 0.0812) | 0.0742 |
| Hessian at tabulated r_e — control | 23 / 23 | 0.0390 | 0.0375 |

Pooled, `f_B = f_A/(1+f_A)` holds to six decimals, as the algebra requires. Both protocols
were reproduced independently by a second, separately-written script before being believed;
the two agreed to the digits shown.

**Three findings, and none of them is "the old number was wrong."** PySCF's version, the
convergence thresholds and the lost script's roster weighting are unrecoverable, so this is
drift of unknown origin. What it does establish:

1. **The denominator is probably wrong.** f_A is nearer 0.091 than f_B on *both* protocols,
   and `pyscf_oracle.py:809` applies the constant to the **computed** ZPE — i.e. as an f_B.
   If the lost fit measured against the reference ZPE, the file overstates the systematic
   by ~1.09x. This is the suspicion recorded in the second pass, and it now has evidence
   on both sides of a protocol change rather than none.
2. **The scatter is as large as the constant.** Per-species sd is 0.0812 against a mean of
   0.0801, and **four of the 21 species have the opposite sign** — CN −0.039, MgO −0.053,
   Na2 −0.022, NaCl −0.030 — while O2 reaches +0.264. A "9.1% systematic" is the mean of a
   distribution that straddles zero. Combined with the second pass's finding that every
   polyatomic ZPE lies *above* the training maximum, this term is a one-parameter model
   evaluated out of range **and** fitted on data it barely describes.
3. **About half of it is geometry, not method.** The production path is **2.05x** the
   fixed-geometry control. Relaxing at HF/cc-pVDZ — whose bonds are measurably too short,
   established above — stiffens the molecule and inflates the harmonic frequencies roughly
   as much as the electronic method does. The "HF harmonic bias" is not purely an HF
   harmonic bias.

**A live fragility surfaced on the way.** CS and F2 do not survive the production path at
all: the unconstrained Cartesian L-BFGS-B line search in `geometry.py:357` takes a trial
step that drives the two atoms nearly coincident (C–S separation 0.12 Å against an
equilibrium 1.53 Å) and SCF diverges. This is the same `_relaxed_geometry` polyatomics use.
It fails loudly, with `ConvergenceFailure`, so it is not a silent-wrong-answer path — but it
means the roster that produced 0.0801 is 21 species, not the 23 the constant claims.

**Nothing was changed.** `ZPE_BIAS_FRACTION` is still 0.091 and is still not applied to
`value_ev`. Overwriting a calibration constant from a run that does not reproduce it would
substitute one unexplained number for another. The comment block above the constant now
records all of this, so the figure's weakness is visible where it is used rather than only
here.

### The reconstruction that was reported and did not reproduce

An independent pass reported re-deriving the constant as **+0.0906 mean at n=23/23**, which
would have made 0.091 reproduce and would have made the paragraphs above wrong. It is
recorded here because it was not reproducible, not because it was ignored.

Re-run under a third protocol — relaxation **seeded at the tabulated r_e** rather than at
`seed_coordinates`' bond-graph seed — the result is **f_A mean 0.08161, sd 0.07956, n=22/23**
(CS recovers, F2 still fails). That is 0.0094 from 0.091, not 0.0004. Three protocols now
sit at 0.0390, 0.0801 and 0.0816, and none reaches 0.091. The reported 23/23 is also
inconsistent with the F2 failure, which two other passes and both of the harness's protocols
reproduce deterministically. **The conclusion stands: 0.091 does not re-derive here.** What
is not established is why the reported figure differed, and that is left open rather than
explained away.

## A silent wrong answer, found in the cache and closed

`persistent._fingerprint` hashed only `inspect.getmodule(type(oracle))`. The ordinary
composition this project uses — `PersistentCache(CachingOracle(PySCFOracle(...)))`, which is
literally `polyatomic_cost_probe.py:224-226` — meant the implementation digest covered
`caching.py` and **never `pyscf_oracle.py`**.

`calculation_spec` delegates to the inner oracle correctly, which is why this looked safe.
But it carries *settings*, and `_model_inputs_sha256` is a deliberate whitelist. Anything
off that list — `conv_tol`, `max_cycle`, `_DESCENT_STEP_ANGSTROM`, `_MAX_DESCENTS`, the CBS
extrapolation algebra, or adding frozen core or density fitting to `_parts` — changed every
number the oracle produced and changed the cache key not at all.

Measured on a copied tree with `mycc.frozen = 1` added to `_parts`:

```
pristine   bare d87102f11f384b24   wrapped 34e5368ef7bf3d4c
+ frozen   bare 2ebcc929b73d639e   wrapped 34e5368ef7bf3d4c   <-- unchanged
```

The bare oracle invalidated correctly; the wrapped one served the pre-edit number with
`rejected=0`. Closed by digesting every module in the `.inner` chain rather than
special-casing `CachingOracle`, because the hazard is composition itself. Six regression
tests. **Every persistent cache file on disk is invalidated by this, correctly — they were
keyed by a rule that could not distinguish the code that produced them.**

Note the irony worth keeping: the geometry probe earlier today was designed around a
*suspected* cache hazard that turned out not to exist, and a real one was sitting one layer
further out the whole time.

## Every diatomic relaxation evaluates one nonphysical geometry

`geometry.py:454` calls scipy L-BFGS-B unbounded. With no bounds, scipy sets the first step
length to `1/||d||`, so the first trial displacement has Euclidean norm **exactly 1.0** in
the optimiser's variables — which are Ångström. For a diatomic the gradient is exactly
antisymmetric, so each atom moves 1/√2 = 0.70711 Å in opposite directions and **the bond
length changes by exactly √2 = 1.414214 Å on trial 1, for every diatomic, regardless of how
small the gradient is.**

That is visible in this repository's own failure message without any instrumentation: the CS
`ConvergenceFailure` prints `C 0.7071067812 -0.0000000000 0.0000000000`. The two failures
are then pure arithmetic:

```
CS  1.534900 - 1.414214 = 0.120686 A     <- matches the error message to the digit
F2 |1.411930 - 1.414214| = 0.002284 A
```

**The seed is not the culprit** — `seed_bond_length` reaches its tabulated branch and returns
the experimental r_e exactly for both, so bond order never enters. **F2 fails *because* its
seed is perfect:** its r_e of 1.41193 Å agrees with the fixed 1.414214 Å step to 0.0023 Å. A
worse reference value would have survived.

**And there is no distance boundary.** SiO lands at 0.0955 Å — *closer* than CS's fatal
0.1207 Å — and its SCF converges. The 21 species that pass do so on per-species SCF luck,
not margin. Polyatomics are affected too: the 1 Å budget is normalised over the whole 3N
vector, and production water drives an O and an H to **0.164 Å** apart on every relaxation it
has ever run.

Production impact is bounded — `pyscf_oracle.py:829` catches `ConvergenceFailure` and returns
`None`, so this costs coverage, not correctness, and it fails loudly. It is not fixed here.
The `bounds=` remedy is disqualified: it works only by tripping scipy's boxed branch, the
bound *values* provably do nothing, and it perturbs currently-working species by up to
3.1e-5 eV. The defensible fix is a penalty return on `ConvergenceFailure` — provably inert on
paths that already work — and it deserves its own scoped change, not a hurried one at the end
of a session.

## Correction to the section above: for CS the wall was ours, not the surface's

The √2 first-step finding stands exactly as measured. The *conclusion drawn from it* did not
survive being asked one more question, and the question was "if the SCF converges at CS's
collapsed geometry, why is CS refused?"

It is refused by the retry. `_mean_field` warm-starts each relaxation step from the previous
step's converged density and promises, in its own docstring, that a bad guess "can only ever
cost time, never an answer" — implemented as `kernel(dm0=usable)`, and on failure
`kernel(dm0=None)` on the **same object**. `pyscf/scf/hf.py:2092` reads

```python
if dm0 is None and self.mo_coeff is not None and self.mo_occ is not None:
    dm0 = self.make_rdm1()          # "Initial guess from existing wavefunction"
```

so `dm0=None` means "start from scratch" only on a *fresh* object. On a used one it means
"reuse what you have". The fallback re-fed the failed run's own density straight back in.

MEASURED at `C 0.7071067812 0 0; S 0.8277932188 0 0`, the 0.1206864376 Å geometry CS's own
relaxation reaches on trial 1:

| | | |
|---|---|---|
| A | warm start | `converged=False` |
| B | then `dm0=None` on the same object | `converged=False` ← the old fallback |
| C | then `dm0=None` after clearing MOs | `converged=True`, e = −220.797973 |
| D | cold on a brand-new object | `converged=True`, e = −220.797973 |

C and D agree exactly, so nothing about that geometry is unconvergeable — only the poisoned
object was. Fixed in `081390c` by rebuilding the mean field for the retry rather than clearing
fields by hand: the fields PySCF consults for its implicit restart are its business and may
grow, whereas a new object has no history by construction. The branch is reached only after an
SCF has already failed, so every calculation that works today is bit-identical.

**CS now relaxes**, r = 1.5259590402 Å against a tabulated r_e of 1.5349 — shorter, like every
other HF/cc-pVDZ bond measured in this file.

**F2 still declines, and that one is real.** Its tabulated r_e is 1.411930 Å, the first
unbounded L-BFGS-B trial step moves a diatomic bond by exactly √2 = 1.414214 Å, and the
resulting 0.002284 Å separation fails from *any* guess — cold included. F2 fails **because its
reference geometry is accurate**. So the penalty-return fix proposed above is still the right
remedy for F2 and is no longer needed for CS, and the two cases were indistinguishable from
outside: both came back `None`. One was a wall; one was us.

### Two docstrings cited tests that did not exist

Grepped, not assumed:

| citation | site | status |
|---|---|---|
| `TestTheFinalGradientIsNotRecomputed` | `geometry.py:404` | absent from the tree |
| `TestTheGuessDoesNotMoveTheAnswer` | `pyscf_oracle.py:886` | absent from the tree |

Both underlying claims are TRUE. The first was re-measured here over 200 randomised quadratic
surfaces plus Rosenbrock — `result.jac` and a fresh evaluation at `result.x` agree to **0.0
exactly**, round trip through the Bohr/Ångström division and multiplication included. Only the
proof was missing. Both classes now exist, along with one pinning the retry. This is the
`experiments/`-are-committed problem one layer in: a claim can cite a test by name and the
name can be fiction.

## `ZPE_BIAS_FRACTION`, re-derived again and then deliberately not changed

The retry fix recovered CS, so the production roster moved 21/23 → 22/23. CS lands at f_A
**0.1122**, above the mean — repairing the SCF moved the fit *toward* the inherited constant.

| estimator | pooled | mean | sd | \|pooled − 0.091\| |
|---|---:|---:|---:|---:|
| f_A = Δ / **reference** ZPE | 0.08116 | 0.08158 | 0.07956 | 0.00984 |
| f_B = Δ / **computed** ZPE | 0.07507 | 0.07066 | 0.06821 | 0.01593 |

Identity check `f_A/(1+f_A) = 0.075067` against `f_B` pooled `= 0.075067`. The code applies
the constant to the computed ZPE, i.e. as an f_B, so **as used it overstates the systematic by
1.21×**; the f_B-consistent value is 0.0751.

**Decision: hold 0.091.** Substituting swaps an unreproduced number for a reproduced but
unjustified one — 0.0751 is the mean of a distribution whose sd is 91% of its own mean, with
four sign reversals, fitted on diatomics and applied to polyatomics, the exact transfer this
project records getting wrong once with basis augmentation. It is not applied to `value_ev`,
so the digits change nobody's action. And the error runs the conservative way:
`systematic_magnitude_ev` feeds `Estimate.with_sensitivity_floor`, where a larger term
**widens** the reported bar. Wide is the safe direction to be wrong in here.

Measured, not assumed: the constant is **inert in production today**.
`PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", optimize_geometry=True, max_atoms=6).nominal_accuracy_ev`
is `inf`, `_RELAXED_GEOMETRY_MAE` is empty, and `_polyatomic_energy` returns `None` before it
ever reaches `zpe_bias`. Only the probe executes that line, by force-assigning the 999.0 eV
sentinel.

The real defect is not the value. A one-parameter multiplicative model is the wrong **shape**
for data whose sd equals its mean, and refitting the one parameter does not address that.

## The cbs(TZ,QZ) holdout, closed at n=3 — and the gate stays shut

| species | atoms | TZ error | **cbs error** | TZ→CBS shrink | wall |
|---|---:|---:|---:|---:|---:|
| CH2O | 4 | −0.2901 | **−0.0575** | 5.05× | 681.5 s |
| N2H4 | 6 | −0.6808 | **−0.1279** | 5.32× | 1750.8 s |
| HCOOH | 5 | −0.6725 | **−0.2546** | **2.64×** | 2115.3 s |

```
cbs holdout MAE (n=3) : 0.1467 eV   spread 0.0575 .. 0.2546  (4.43x range)
cbs profile MAE (n=6) : 0.0558 eV
ratio                 : 2.63x       (it was 1.66x at n=2)
```

**One species moved the ratio from 1.66× to 2.63×.** That is the second time in this file a
single addition has moved a summary statistic by more than half its own value — the cc-pVTZ
ratio went 1.49× → 1.35× on C2H6 — and it is the honest measure of how little n=3 constrains.
Neither number should be quoted as stable.

### Scoring the pre-registered prediction: two hits and one clear miss

Filed in `d5d19d5` before any of these three numbers existed.

| species | predicted | interval | actual | |
|---|---:|---|---:|---|
| CH2O | −0.05 | −0.07 … −0.03 | −0.0575 | **HIT** |
| N2H4 | −0.10 | −0.17 … −0.08 | −0.1279 | **HIT**, deep, as the wider interval anticipated |
| HCOOH | −0.10 | −0.13 … −0.07 | **−0.2546** | **MISS** — nearly 2× past the deep edge |

**The valence-electron-pair correlate is refuted at the CBS tier.** It was fitted at
cc-pVTZ, where err/valence-pair transferred across the split at −0.06503 (profile) against
−0.06598 (holdout) — the very fact quoted as its strongest evidence. At cbs(TZ,QZ) the same
quantity over these three species runs −0.0096 (CH2O), −0.0183 (N2H4), −0.0283 (HCOOH): a
**2.95× spread**, monotone in atom count, and a factor of two to seven below the coefficient
it was fitted with. The filed caveat said the correlate gets *looser* at the CBS tier rather
than tighter (coefficient of variation 0.290 → 0.390); the caveat was right and understated.

**HCOOH is the anomaly and it is worth naming precisely.** Its TZ→CBS shrink is 2.64×
against 5.05× and 5.32× for the other two — the extrapolation removes roughly half as much of
its error as it removes of theirs. It is also the only species here carrying two oxygens, and
the only one with both a C=O and an O–H. Nothing in this file explains that, and it should not
be explained by whichever story is nearest to hand; it is a filed anomaly, alongside the
unexplained nitrogen offset already recorded above.

### The gate decision rule, applied

The rule was filed in `6280de2` before these numbers existed. Against it:

| criterion | status |
|---|---|
| 1. holdout-only evidence | **met** — none of these three developed the protocol |
| 2. **n ≥ 8** | **FAILS** — n = 3 |
| 3. `max_validated_atoms` never extrapolated | would be 6, met |
| 4. spread reported with the mean | spread is **4.43×**, and reporting it is what condemns the mean |

**`_RELAXED_GEOMETRY_MAE` stays empty. No entry is made.** That was the pre-registered
expected outcome, and the evidence for it came in stronger than expected: criterion 2 fails by
construction on this hardware, and criterion 4 turns out to fail on the merits as well. A
0.1467 eV bar quoted from a distribution spanning 0.0575 to 0.2546 would be a plausible
number with nothing behind it — which is the exact failure this project exists to refuse.

The run's job was never to open the gate. It was to measure the residual and price what a
real profile would cost, and it did both: the tier-matched holdout error is **2.6× the
training figure**, so entering 0.0558 eV would have understated the bar by more than half.

## Speed: sorting the routes into identity-preserving and measured tradeoff

The gate above is blocked on n ≥ 8, and n ≥ 8 at cbs(TZ,QZ) is blocked on memory, not on
ideas. So the prerequisite for ever opening that gate is the `vvvv` wall, and the question is
which routes past it change the answer.

Five independent probes of PySCF 2.14.0 and of this repo's own configuration. Harness:
`experiments/ccsd_acceleration_probe.py`, which **calibrates itself every run** — it
re-implements `_parts` because the oracle exposes no hook for the CC object, so bit-identity
against the real `PySCFOracle._parts` on the free atoms is required before any route number is
believed. A drifted replica exits 2 rather than reporting a difference it cannot attribute.

### Identity-preserving

| lever | evidence | verdict |
|---|---|---|
| `mycc.direct = True` | never builds `vvvv`; recomputes the contraction from AO integrals each iteration (`ccsd.py:1558`, mirrored for open shells at `uccsd.py:1172`) | **the answer to the wall** |
| cross-species parallelism | nothing in `smartchem/` pins threads; `lib.num_threads()` is 8 by default and `OMP_NUM_THREADS=1` is a *timing* discipline, not a limit | free, RAM-bound |
| MO projection across the CBS pair | `scf.addons.project_dm_nr2nr`; H2O/cc-pVQZ went 10 → 8 SCF cycles, energies agreeing to 1.07e-12 Ha | real, small share |
| atom-energy reuse | already live inside one process via the instance `_cache`, keyed molecule-independently | already switched on |

**`direct = True` measured, and it is exact where it matters — on the atomization energy:**

| species / basis | route | D_e (eV) | wall | peak RSS |
|---|---|---:|---:|---:|
| H2O / cc-pVDZ | conventional | 9.046975604 | 0.44 s | 0.115 GB |
| H2O / cc-pVDZ | direct | **9.046975604** | 0.57 s | 0.114 GB |
| H2O2 / cc-pVTZ | conventional | 11.227822491 | 27.53 s | 0.485 GB |
| H2O2 / cc-pVTZ | direct | **11.227822491** | 33.80 s | 0.502 GB |

Bit-identical to all printed digits at both sizes, calibration 0.000e+00 Ha both times. The
price so far is **1.23× wall clock** at cc-pVTZ. The memory saving does not show at either
size and is not expected to: `vvvv` for H2O2/cc-pVTZ is a few tens of MB against a peak
dominated by the AO integral transform. The wall lives at cc-pVQZ, where the model in
`basis_size_probe.py` puts `vvvv` at 2.24 GB for CH3OH and 22.1 GB for C3H8.

### Measured tradeoff

Density fitting works, including for the open-shell atoms — `dfccsd` **and** `dfuccsd` both
exist, `cc.CCSD(mf)` dispatches off `with_df`, and `ccsd_t()` runs on top because the triples
reach integrals through `eris.get_ovvv` and never touch `vvvv` at all.

| route | D_e (H2O/cc-pVDZ) | Δ vs conventional | as a fraction of chemical accuracy |
|---|---:|---:|---:|
| df (`-jkfit`, the default) | 9.047561507 | +0.000586 eV | 1.4% |
| df-ri (`-ri`, the correct tier) | 9.047913744 | +0.000938 eV | 2.2% |

Two findings outrank those numbers.

**DF-UCCSD cannot run on a hydrogen atom.** One electron means a zero-dimension spin block and
h5py refuses the chunk (`ValueError: All chunk dimensions must be positive`). Every
hydrogen-containing species hits it, which is nearly all of them. Correlation is identically
zero for one electron and the conventional route measures that — H/cc-pVDZ gives
`e_corr = -1.92e-32` Hartree and `ccsd_t() = 0.0` exactly — so falling back is the defined
answer rather than a patch, but a shipping integration would have to carry that branch
knowingly.

**The `-ri` auxiliary basis is *farther* from the conventional answer than the `-jkfit`
default here, not nearer.** `.density_fit()` fits with `-jkfit`, and `dfccsd`/`dfuccsd` reuse
that set for the correlation energy rather than building the `-ri` set (`dfccsd.py:35-38`).
That is a wrong-tier default nobody chose and it deserved naming — but on this case correcting
it moves the answer away by 0.00035 eV. One species at one basis proves nothing about which
set is right; it does prove the two differ, and that the trap is not self-evidently costly.

### Refuted — do not spend time here

- **Point-group symmetry.** `pyscf.cc.ccsd`'s amplitude iterations ignore it entirely; only
  the RHF (T) step exploits it, and `uccsd_t.py` hardcodes `orbsym = zeros`, so it is worth
  exactly nothing on the open-shell atoms. A speedup that covers the molecule but not its own
  atoms does not help an atomization energy.
- **Frozen core** does not move the wall. `nocc` and `nmo` both drop by the frozen count, so
  `nvir` is arithmetically unchanged — confirmed by probe, not inferred.
- **CCSD(T)-F12 and local/PNO correlation are absent from PySCF 2.14.0.** The only F12 code in
  the tree is `mp/mp2f12_slow.py`, self-flagged "in testing", and it is MP2. There is no
  cheap route to CBS quality from a TZ calculation in this library.
