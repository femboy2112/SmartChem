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

**Audited, and those two were the only ones.** Every `tests/<file>.py::<Class>` citation in
`smartchem/` and `experiments/` (6 distinct), every bare `Test*` class name referenced from
source (7 distinct), and every `::test_<name>` function citation now resolves to something
that exists. A negative result worth writing down, because the next person to wonder should
not have to re-run the grep.

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
| CH3OH / cc-pVQZ | conventional | 22.163760672 | 1334.38 s | **4.726 GB** |
| CH3OH / cc-pVQZ | direct | *running at time of writing* | | |

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

### Where the `direct` measurement stands, and what finishes it

`CH3OH / cc-pVQZ conventional` is the first case in this file where `vvvv` is genuinely
load-bearing: **4.726 GB peak RSS against a 7 GB box**, 1334.38 s. That is the regime the
whole acceleration question is about — one species, alone, using two thirds of the machine.
The two cc-pVTZ cases above show exactness but cannot show a memory saving, because their
`vvvv` is tens of megabytes inside a peak dominated by the integral transform.

**The outstanding measurement is `CH3OH / cc-pVQZ direct`**, running as this was written, via
`scratchpad/run_accel.sh` writing to `scratchpad/accel.txt`. It decides two things at once:

1. **Exactness at scale.** `direct` must return `22.163760672` eV. It has been bit-identical
   at cc-pVDZ and cc-pVTZ; QZ is where the AO-driven contraction does the most work and so is
   the strongest test of the claim.
2. **Whether the saving is real.** The model in `basis_size_probe.py` puts CH3OH's `vvvv` at
   2.24 GB of that 4.726 GB peak. If `direct` lands near 2.5 GB, the wall moves by roughly a
   factor of two on this species and the C2H5OH/C3H8 tier becomes reachable; if it lands near
   4.7 GB, the peak is dominated by something else and `direct` buys wall clock debt for
   nothing. Either result is worth having and only one of them is a speedup.

The decision rule, filed before the number: **wire `mycc.direct = True` into `_parts` only if
the QZ run is bit-identical AND its peak drops by more than the 1.23× wall-clock price is
worth** — i.e. only if it converts species that cannot run into species that can. A route that
is merely slower and equally large is not adopted, however elegant its mechanism.

### The `direct` verdict: exact, faster, and BIGGER — the memory hypothesis is refuted

`CH3OH / cc-pVQZ direct` landed. Both rows, from `scratchpad/accel.txt`:

```
route         D_e (eV)        wall        peak RSS
conventional  22.163760672   1334.38 s    4.7263 GB
direct        22.163760672   1119.42 s    4.8924 GB
```

Calibration `0.000e+00 Ha` over 3 free atoms on both runs, as on every run in this file.

**Criterion 1 — exactness: PASSED, at the hardest size.** `22.163760672` eV to the last
printed digit, at the basis where the AO-driven contraction does the most work. `direct` is
now bit-identical at cc-pVDZ, cc-pVTZ and cc-pVQZ. That claim is settled.

**Criterion 2 — the memory saving: REFUTED, and it went the wrong way.** The peak did not
fall to the predicted ~2.5 GB. It *rose*, from 4.7263 GB to 4.8924 GB — **+0.1661 GB, 3.5%
larger**. Not a small saving; a small penalty.

**So the filed rule applies and the answer is NO.** `mycc.direct = True` is **not wired into
`_parts`.** The rule required the peak to drop enough to convert species that cannot run into
species that can. It did not drop at all, so the C2H5OH/C3H8 tier is exactly as unreachable as
it was this morning, and [the cbs gate](#the-cbstzqz-holdout-closed-at-n3--and-the-gate-stays-shut)
stays blocked on memory with its named remedy removed.

**The correction this forces, which is larger than the route question.** The reasoning chain
was: the wall is `vvvv`, `vvvv` is 2.24 GB of CH3OH/cc-pVQZ's 4.726 GB peak, `direct` never
builds `vvvv`, therefore `direct` halves the peak. The measurement kills the *conclusion*,
which means one of the premises is false — and the one that fails is the third-to-last:

> **The peak for CH3OH / cc-pVQZ is not set by `vvvv`.**

The `vvvv` array may well be 2.24 GB; deleting it changed the high-water mark by nothing. A
model calibrated against peak RSS was being read as a model *of the peak's composition*, and
those are different claims. This is the same species of error as the ZPE fraction — a
quantity fitted for one purpose, consumed as though it answered another.

**The leading suspect, named but NOT claimed.** `direct` alters only the CCSD amplitude
iteration. `ccsd_t()` runs afterward, allocates its own arrays, and is untouched by the flag —
so if the triples step sets the high-water mark, both routes peak at the same place and the
3.5% is transient noise around a shared ceiling. That is *consistent* with what was measured
and is not evidence for it. **The discriminating probe:** run both routes with the `(T)` step
disabled and compare peaks. If the gap opens to ~2 GB, `vvvv` was real and `(T)` was hiding
it; if both fall together, the transform sets it. One run each, not yet done, and no
conclusion is recorded here until it is.

**The unanticipated result, kept separate because the rule did not cover it.** `direct` was
1.295× slower at cc-pVDZ and 1.2277× at cc-pVTZ. At cc-pVQZ it is **1.1920× FASTER**
(1.1945× on the molecule alone) — 214.96 s saved on a 1334 s run. The sign flipped somewhere
between TZ and QZ.

That is interesting and it is **n = 1**. A sign reversal resting on a single paired
measurement is precisely the kind of result this file exists to not act on. It is recorded as
an observation, not a finding, and it is *not* what the filed rule was about — stretching a
memory rule to ratify a speed result would be answering a question nobody pre-registered.

**Pre-registered, before the next run:** the speed reversal is confirmed if a second species
at cc-pVQZ shows `direct` faster than `conventional` by more than 5%, as a paired run on the
same box. `C2H5OH / cc-pVQZ direct` is running now and **cannot settle this** — no
conventional partner was queued for it, so it produces a wall-clock number with nothing to
compare against. It is a memory-scaling datapoint and should not be read as anything else.

---

## What actually sets the CCSD(T) peak: measured, and it is neither `vvvv` nor `(T)`

`experiments/ccsd_peak_phase_probe.py`, committed. The previous section left a named
suspect — the triples step — and an explicit instruction not to believe it until run. It
has now been run, and the suspect is wrong.

**The instrument.** `resource.getrusage(...).ru_maxrss` is a high-water mark and therefore
monotone, so over any interval `maxrss(exit) - maxrss(enter)` is *exactly* the amount by
which that interval raised the peak, and those increases are additive over any partition
of the timeline. Partition the run into nested phases and attribution becomes arithmetic
rather than sampling:

    inclusive(phase) = maxrss at exit - maxrss at entry
    exclusive(phase) = inclusive(phase) - sum(inclusive of its direct children)

A phase with `exclusive == 0` did not set the peak. Not *probably* did not — did not.
There is no sampling interval for a spike to hide in, because a spike would have moved the
high-water mark and the high-water mark is read at both ends.

Phase boundaries are recorded by wrappers installed on PySCF's own methods; each reads a
clock and a counter, calls through, and returns the value untouched. That is an argument,
not evidence, so the calibration runs *with the wrappers active* and bit-identity against
the real `PySCFOracle._parts` is required before any attribution is reported.

**CH3OH / cc-pVTZ / conventional, peak 1.0868 GB:**

```
SEGMENT molecule                     77.4 s   peak +0.0000 GB
  SCF.kernel                          2.0 s   peak +0.1672 GB
  CCSDBase.kernel                    44.0 s   peak +0.0000 GB
    CCSDBase.ao2mo                    7.6 s   peak +0.6860 GB    <-- 63.1% of the peak
  CCSD.ccsd_t                        31.3 s   peak +0.0000 GB
    CCSDBase.ao2mo                    7.5 s   peak +0.0797 GB
```

**The peak is set by the integral transformation.** `CCSDBase.ao2mo` owns 0.6860 GB of a
1.0868 GB peak. Two phases raised it by *nothing at all*, exactly:

* `CCSDBase.kernel` — the CCSD amplitude iterations, 44.0 s of arithmetic, `+0.0000 GB`.
  Everything they need was already resident when `ao2mo` returned.
* `CCSD.ccsd_t` — the triples, 31.3 s, `+0.0000 GB` of its own. **The filed suspect is
  refuted.** `(T)` does not allocate the peak.

**What the timeline caught that nobody was looking for: the integrals are transformed
twice.** `ccsd_t` raised nothing directly, but it called `ao2mo` *again* — a second full
7.5 s transform, adding 0.0797 GB. `_parts` calls `mycc.ccsd_t()` with no `eris` argument,
and PySCF rebuilds them from scratch when none is supplied. At cc-pVTZ that is 7.5 s of a
77.4 s molecule, ~9.7%, spent recomputing something that had just been computed. Filed as
task #13, not acted on here: it is a candidate identity-preserving speedup and it is owed
the same bit-identity gate as `direct`, which failed that gate on memory.

**What this does NOT settle.** One run, one basis. `vvvv` grows quartically in the virtual
count and the triples arrays do not, so the owner of the peak can change with basis — and
cc-pVQZ is the basis the open question is actually about, because that is where `direct`
*raised* the peak by 3.5%. The paired cc-pVQZ attribution, both routes, is queued behind
the running job. Nothing here should be carried to cc-pVQZ before it lands.

---

## The F2 refusal, re-diagnosed: it is a nuclear collision, not fragile chemistry

Task #8 asked whether F2's collapsed-step refusal is worth fixing. The answer is that F2
is not the bug, and the diagnosis recorded earlier in this file is wrong in a way that
would misdirect whoever picked it up.

**Confirmed, in pure scipy, no PySCF involved.** `relax` calls L-BFGS-B with no `bounds=`
(`geometry.py:454-458`). Its first trial step has Euclidean norm **exactly 1.0** over the
flattened Cartesian vector, at every gradient magnitude tested (`1e-3`, `1.0`, `1e3` — all
`|step| = 1.0000000000`). For a diatomic the gradient is exactly antisymmetric, so each
atom moves `1/sqrt(2) = 0.7071068` in opposite directions and the bond changes by
`sqrt(2)`.

**The direction was assumed and is now measured.** HF/cc-pVDZ at F2's tabulated
`r_e = 1.41193 A` gives `dE/dr = +5.055117e-02 Ha/Bohr` — positive, so the step pulls the
nuclei **together**. The bond after trial 1 is `|r_e - sqrt(2)|`:

    F2   r_e = 1.41193   ->   0.002284 A     two fluorine nuclei, 0.0023 A apart
    N2   r_e = 1.09768   ->   0.316534 A

**The number 0.002284 A was read as the wrong quantity.** This file previously described
F2 as landing 0.002284 A *from the correct answer*, which reads as "so close, and the SCF
is still fragile there." It is not that. 0.002284 A is the **resulting bond length** — a
nuclear singularity. The coincidence is exact and nasty: `|r_e - sqrt(2)|` is
simultaneously "the distance from `r_e` to `sqrt(2)`" and "the bond length after a
collapse through `sqrt(2)`", so both readings produce the identical figure while
describing utterly different physics. SCF failing with two nuclei 0.0023 A apart requires
no explanation about near-degenerate frontier orbitals. It is the only correct outcome.

**F2 is not marginal, it is an extreme outlier.** Ranking every tabulated diatomic by
`|r_e - sqrt(2)|`, the collapsed bond it would be driven to:

    F2    0.002284 A      SiO   0.095526 A      CS    0.120686 A      HCl   0.139614 A

The runner-up is **42x further** from the singularity. The earlier note that "the 21
species that pass do so on per-species SCF luck, not margin" is right and understates it:
the margin is `|r_e - sqrt(2)|`, and the hazard exists only because a unit-norm step in a
routine that thinks in Angstroms happens to be 1.0. Nothing about `sqrt(2) A` is chemical.

**Verdict on #8: not worth fixing as an F2 fix, and it should not be filed as one.** The
blast radius is zero — no public path reaches it (diatomics never call `_relaxed_geometry`
through `energy()`; polyatomics decline first on `nominal_accuracy_ev`), and its only
present effect is narrowing the `ZPE_BIAS_FRACTION` calibration roster from 23 species to
22. The remedy already named in this file — a penalty return on `ConvergenceFailure`
rather than `bounds=` — remains the right one and still deserves its own scoped change.
What changes is the reason: it is not there to rescue F2's chemistry, it is there because
the optimizer walks into nuclei and 21 species avoid that by arithmetic accident.

---

## The peak owner CHANGES with basis, and at cc-pVQZ it is the SCF

The cc-pVTZ attribution above named `CCSDBase.ao2mo` and closed the section with a caveat:
`vvvv` is quartic in the virtual count and the triples arrays are not, so the owner can
change with basis, and cc-pVQZ is the basis that matters. It changes. It does not change to
either candidate.

`CH3OH`, `conventional`, both bases, exclusive `ru_maxrss` deltas:

| phase | cc-pVTZ | cc-pVQZ |
|---|---:|---:|
| `SCF.kernel` | +0.1672 GB (15.4%) | **+2.2763 GB (48.9%)** |
| `CCSDBase.ao2mo` (inside `kernel`) | **+0.6860 GB (63.1%)** | +1.8488 GB (39.7%) |
| `CCSDBase.kernel` — the amplitude iterations | +0.0000 GB | +0.0000 GB |
| `CCSD.ccsd_t` — the triples | +0.0000 GB | +0.0000 GB |
| `CCSDBase.ao2mo` again, inside `ccsd_t` | +0.0797 GB | +0.0000 GB |
| **measured peak** | 1.0868 GB | 4.6580 GB |

```
PHASE_RESULT CH3OH cc-pVQZ conventional CCSD(T) 22.163760672 4.6580 SCF.kernel 2.2763
```

**At the basis that actually matters, the peak is set by the mean field.** The arithmetic
that explains it is not subtle: the incore AO integral tensor is `nao^4 / 8` doubles, which
is 2.8 GB at 230 basis functions and 0.18 GB at 116. It was a rounding error at cc-pVTZ and
it is half the peak at cc-pVQZ, which is exactly why three probes and two wrong guesses
never went near it.

Every memory lever considered in this document so far — `vvvv`, the triples, `direct`,
sharing the transform — targets the coupled-cluster layer. At cc-pVQZ the coupled-cluster
layer is not what sets the mark. The untried lever is `direct_scf` or density fitting on
the SCF, filed as task #14, and it is explicitly NOT presumptively identity-preserving: it
changes the convergence path, so it owes the same bit-identity gate `direct` failed.

**The instrument cross-checks.** `ccsd_acceleration_probe.py` measured this same case at
4.7263 GB by separate instrumentation; the phase probe says 4.6580 GB, 1.4% apart, and the
two report the identical energy 22.163760672 to every printed digit. Two harnesses, one
number.

## Task #13, closed: the integral transform is built once

`_parts` called `mycc.kernel()` and `mycc.ccsd_t()` with no arguments. Both default to
`eris=None` and rebuild the transformation (`pyscf/cc/ccsd.py:1099-1100` and `:1289-1293`;
`uccsd.py:633` for the open-shell twin). The cost, measured rather than estimated:

    cc-pVTZ :  7.5 s of a 77.4 s molecule    (~9.7%)
    cc-pVQZ :  294.6 s

Now built once and shared. It is identity-preserving for a structural reason: `ao2mo` builds
one fixed block set with no branch on the caller, and the triples correction consumes a
strict subset of it — never `vvvv`. Verified three independent ways, because a structural
argument is still an argument:

* `tests/test_eris_reuse.py`, both spin paths (`CCSD` and `UCCSD`), single-threaded
  difference exactly **0.000e+00 Ha**.
* That gate had to be rebuilt once, and the failure is worth recording. The first version
  compared two separate SCF runs and failed on `E_HF` — a quantity fixed before `cc.CCSD` is
  constructed, which this change cannot touch — by ~1e-14 Ha under the full suite, while
  passing standalone where threads happened to be pinned. **A test whose verdict depends on
  `OMP_NUM_THREADS` is not measuring what it claims to.** It now shares one mean field and
  calibrates its own noise floor by repeating the *unchanged* path: 5.6e-17, 1.4e-17 and
  8.3e-17 Ha at 8 threads, with an absolute ceiling so a pathologically noisy run cannot
  calibrate its own gate open.
* `ccsd_peak_phase_probe.py`'s calibration compares its replica — which still rebuilds —
  against the real `PySCFOracle._parts`, and reports 0.000e+00 Ha at **cc-pVQZ** over three
  UHF free atoms. Independent, on the shipping path, at a larger basis than the unit test.

Note what the peak table says about the memory side of this: at cc-pVTZ the second transform
raised the high-water mark by 0.0797 GB, at cc-pVQZ by **exactly zero**. So #13 is a
wall-clock win that happens to shed a little memory at TZ and none at QZ — not a memory fix,
and it was filed as one.

## What was NOT measured, and the arithmetic that killed it

`C2H5OH / cc-pVQZ / direct` ran for 58 minutes and was killed at 16:52:39 rather than
allowed to finish. Recorded here because a silently abandoned run reads as one that was
never planned.

`nao` for C2H5OH over CH3OH is exactly **1.500** at every basis (345 vs 230 at cc-pVQZ).
CH3OH/QZ/direct spent 1108.3 s on the molecule; splitting that at the TZ-measured 58/42
between the amplitude solve and the triples, and scaling by N^6 (11.39x) and N^7 (17.09x)
respectively, projects **≈15,280 s = 4.24 h** against the job's own `timeout 14400`. It was
on course to be killed by its own clock having printed nothing, since the probe emits
`ROUTE_RESULT` only at the end. Even the charitable pure-N^6 read is 3.51 h.

Against that it was holding the box — the cc-pVQZ phase attribution needs ~4.7 GB and could
not start — for a datapoint with **no partner**: the `conventional` half of the pair would
need roughly 24 GB and cannot run on a 7 GB machine at all. A route comparison with one arm
is not a route comparison. The paired CH3OH/QZ measurement was worth more than an unpairable
C2H5OH one, and that is the whole justification.

---

## The `direct` half of the cc-pVQZ pair, and it dissolves the question it was run to answer

The pair is complete. `PHASE_BATCH_DONE`. CH3OH, cc-pVQZ, CCSD(T), one process per route,
`OMP_NUM_THREADS=1`, both routes calibrated against `PySCFOracle._parts` at
`0.000e+00 Ha` over three free atoms before either molecule ran.

| phase | conventional | direct |
|---|---:|---:|
| `SCF.kernel` | +2.2763 GB (48.9%) | +2.2791 GB (51.4%) |
| `CCSDBase.ao2mo` (in kernel) | +1.8488 GB, 229.9 s | +1.6311 GB, **35.9 s** |
| `CCSDBase.kernel` | +0.0000 GB, 750.5 s | +0.0000 GB, 754.0 s |
| `CCSD.ccsd_t` | +0.0000 GB, 691.8 s | +0.0000 GB, 469.7 s |
| molecule wall | 1469.0 s | **1248.8 s** |
| **peak** | **4.6580 GB** | **4.4356 GB** |
| D_e | 22.163760672 eV | 22.163760672 eV |

**The question was "why did `direct` RAISE the peak 3.5% at cc-pVQZ". It did not raise it.
By this instrument it LOWERED it by 0.2224 GB, 4.8%, and it was 220 s faster.**

### Two instruments, one sign disagreement

| instrument | conventional | direct | verdict on `direct` |
|---|---:|---:|---|
| `ccsd_acceleration_probe.py` | 4.7263 GB | 4.8924 GB | **+3.5%** |
| `ccsd_peak_phase_probe.py` | 4.6580 GB | 4.4356 GB | **−4.8%** |

They agree on `conventional` to **1.5%** and disagree on `direct` by **10.3%**, in opposite
directions. All four runs report the identical energy `22.163760672` and both agree `direct`
is faster, so this is not a numerical drift — it is a disagreement about peak RSS alone.
**The +3.5% was one instrument's unreplicated number, and every statement built on it was
built on that.** No claim about `direct`'s memory effect at cc-pVQZ is supportable until the
disagreement is resolved; a replication of the accel arm is the cheapest discriminator and
is the open item.

### What survives the disagreement, and it is the part that matters

**`SCF.kernel` owns the peak on BOTH routes, at +2.2763 and +2.2791 GB — 0.12% apart.**
That is the same allocation twice, and it must be: `direct` is `mycc.direct`, a
coupled-cluster flag. PySCF's `RHF.get_jk` (`pyscf/scf/hf.py:2504-2508`) never consults it.
So `direct` cannot move the thing that owns half the peak, whatever the residual 10%
disagreement turns out to be about. Both routes also confirm again that the amplitude
iterations and the triples raise the high-water mark by **exactly zero** — 754.0 s and
469.7 s of arithmetic that costs nothing at the mark.

## Task #14 was filed wrong, the same way #13 was

The task said the untried lever is `mf.direct_scf`. **It is not.** `mf.direct_scf` defaults
to `True` already and is irrelevant on this path: `RHF.get_jk` decides incore-vs-direct on
memory headroom alone and never reads it; `direct_scf` only reaches the base-class
`SCF.get_jk`, which is the branch *not* taken. The literal gate is `_is_mem_enough`,
`pyscf/scf/hf.py:2248-2250`:

```python
def _is_mem_enough(self):
    nbf = self.mol.nao_nr()
    return nbf**4/1e6 + lib.current_memory()[0] < self.max_memory*.95
```

CH3OH/cc-pVQZ: `nao_nr()` is 230, `230**4/1e6` is **2798.41 MB** — exactly the incore
8-fold-symmetric tensor, no fudge factor — against `max_memory*0.95 = 3800`. It fits, so
`mf._eri = mol.intor('int2e', aosym='s8')` fires and is cached for the whole SCF. **The real
lever is `mf.max_memory`**, and `smartchem/oracle/pyscf_oracle.py` sets neither it nor
`direct_scf`, `density_fit` or `incore_anyway` anywhere — the 2.28 GB is stock PySCF at
`max_memory=4000`.

**And it is not a shell game.** `CCSDBase.ao2mo` (`pyscf/cc/ccsd.py:1194-1198`) has
`self._scf._eri is not None` as a hard `and`-prerequisite for its incore branch, so with
`_eri` unbuilt it falls to `_make_eris_outcore`, which streams shell-quartet blocks to an
HDF5 swap file and never holds the full `nao**4` array. The memory does not relocate into
`ao2mo`; it is traded for recomputed J/K builds and disk I/O.

> **REFUTED 2026-07-26 by measurement — the last two sentences above are wrong, and they
> are left standing because deleting them would hide how the error was made.** The memory
> DOES relocate into `ao2mo`, and 87.4% of it does. The paragraph reasoned from *which
> branch* runs (outcore, correctly predicted, `Dataset` confirmed in every arm) to *how much
> that branch allocates*, and those are different questions: the outcore path streams the
> RESULT to HDF5 while sizing its in-RAM working buffers from `max_memory`. See
> "Task #17" below for the three-arm measurement and the source that explains it.

**GATE, unchanged and now sharper:** lowering `max_memory` forces Schwarz screening at
`direct_scf_tol=1e-13` (`hf.py:2124-2133`), which the full incore tensor does not apply. So
this is **NOT** presumptively identity-preserving and owes the same bit-identity gate. Given
the instrument disagreement above, it also owes a peak measured by *both* probes before any
number from it is carried anywhere.

---

## Task #15 CLOSED: the +3.5% was an artifact, and the instrument's noise floor is 13%

`experiments/ccsd_acceleration_probe.py`, CH3OH/cc-pVQZ/direct, re-run 2026-07-26 in a
fresh process:

```
ROUTE_RESULT CH3OH cc-pVQZ direct 22.163760672 1539.42 4.3164
```

Against its own original **4.8924 GB**. Same probe, same species, same basis, same route,
same D_e to every printed digit — and **13.3% apart in peak RSS**.

| run | instrument | route | peak RSS | D_e (eV) |
|---|---|---|---:|---:|
| original | accel | conventional | 4.7263 | 22.163760672 |
| original | accel | direct | **4.8924** | 22.163760672 |
| replication | accel | direct | **4.3164** | 22.163760672 |
| phase | phase | conventional | 4.6580 | 22.163760672 |
| phase | phase | direct | 4.4356 | 22.163760672 |

**The verdict.** `direct` does not raise the peak. Both replications (4.3164, 4.4356) sit
below both `conventional` readings (4.7263, 4.6580), and the two instruments now agree on
sign. The +3.5% that refuted `vvvv` and launched this entire phase hunt was one
instrument's unreplicated number.

**And the noise floor is larger than every effect these probes were used to detect.** A
13.3% run-to-run spread on the same instrument means the 3.5% `direct` result, and the 1.5%
cross-probe agreement on `conventional` that was cited as evidence of trustworthy
attribution, were both inside the noise. The agreement was luck.

**What survives, because it does not depend on a memory number.** `direct` is `mycc.direct`,
a CC-layer flag, and `RHF.get_jk` never reads it. It therefore *cannot* move the SCF's
contribution to the peak, which is the half that matters at cc-pVQZ. That was an argument
from the source, not from a reading, which is why it is the part still standing.

**RULE: no peak-RSS claim from a single run.** Energies were always cross-checked between
probes. Memory numbers never were, and that is precisely where the one bad number lived.

---

## Task #14: the AO integral tensor is 2.6290 GB, and it was never a memory measurement

`experiments/ao_storage_probe.py`, new this round. It stops after `mycc.ao2mo()` — the
amplitude iterations and the triples were both measured at exactly +0.0000 GB of peak at
cc-pVQZ, so running them costs ~24 minutes per arm to re-measure two zeros.

**THE ANSWER, and it needed no instrument at all.**

```
mf._eri built    : True  (2.6290 GB tensor)
```

`mf._eri.nbytes`, read off the array itself. Exact, no baseline, no high-water mark, no
repeats, no noise floor. Three probes and a week of RSS forensics were spent chasing a
quantity that was sitting on an attribute the whole time. **Ask the object before
instrumenting the process.**

`nao_nr()` is 230 and `230**4/1e6 = 2798.41 MB` is the model figure; the array is 2.6290 GB
= 2692 MiB. Those agree to 3.8%, the difference being MB-vs-MiB and the 8-fold symmetry
packing, which is the first time the floor model and a real allocation have been checked
against each other directly.

**The lever fires, verified at the branch rather than at the memory.** H2O/cc-pVDZ, one
process per arm:

| `mf.max_memory` | `mf._eri` built | `eris.vvvv` type | E_SCF (Ha) |
|---|---|---|---:|
| stock (4000 MB) | **True** | `ndarray` | -76.027053512765 |
| 100 MB | **False** | `Dataset` | -76.027053512765 |

Two things worth separating out of that table. The `ndarray`-vs-`Dataset` column confirms
the chain claimed from source last round: with `_eri` unbuilt, `CCSDBase.ao2mo` falls to
`_make_eris_outcore` and streams to HDF5 rather than rebuilding the tensor. And the SCF
energy is **bit-identical** across the two arms at this basis, so Schwarz screening at
`direct_scf_tol=1e-13` costs nothing here — which is a measurement, not a promise, and it
does not transfer to cc-pVQZ without being run there.

**A boolean would have lied.** `eris.vvvv is not None` is `True` on *both* paths — the
outcore branch makes an h5py dataset where the incore branch makes a numpy array. A
truthiness test agrees with the incore answer whenever the incore answer is right, which is
exactly the shape of check that gets believed. The probe reports `type(...).__name__`.

**cc-pVQZ, arm A (stock), and the probe's own defect that the data exposed.**

| run (same process) | `_eri` | `SCF.kernel` | `CCSD.ao2mo` | "peak" |
|---|---|---:|---:|---:|
| 1 | 2.6290 GB | +2.6758 GB, 25.5 s | +1.0617 GB, 319.1 s | 3.8568 GB |
| 2 | 2.6290 GB | **+0.0000 GB**, 30.3 s | +0.7442 GB, 630.4 s | 4.6010 GB |

**The zero is the tell.** An SCF that builds a 2.6290 GB tensor cannot add nothing to the
peak. It "added nothing" because run 1 had already pushed `ru_maxrss` to 3.8568 GB and a
monotone counter cannot come back down. The 19.30% "spread" between the two peaks was the
watermark **accumulating**, not variance.

This file's own opening paragraph says a process-wide high-water mark cannot report two
things honestly, and `--repeat` then looped in-process and did exactly that. Fixed:
`--repeat` now spawns a subprocess per run. **A monotone instrument has exactly one reading
per process**, and when a phase you know is large reports zero, the first hypothesis is that
the mark was already past it — never that the phase is free.

The same property is why the earlier `+0.0000 GB` readings for the amplitude iterations and
the triples still stand: they were only ever read as *"did not SET the peak"*, which is what
a zero delta on a monotone counter means, and never as *"allocates nothing"*.

**Arm B (`mf.max_memory=500`) at cc-pVQZ — PARTIAL, still running at time of writing.**
Read live from `/proc/<pid>/status`:

```
VmHWM: 2.0236 GB   after 525 s
```

against arm A's 3.8568 GB — a **47.5% reduction**, and that figure is a LOWER BOUND on arm
B's final peak because the run had not finished. The price is already visible and it is
steep: arm A's SCF took **25.5 s**, arm B was still inside the SCF at **525 s**, so the
wall-clock cost is at least 20x on that phase. Arms B and C were left running.

**STILL OWED before any of arm B is carried anywhere:** the finished peak, the wall-clock
total, and the cc-pVQZ bit-identity check. The DZ arms were bit-identical; QZ has 230 basis
functions instead of 24 and a screening threshold does not scale by wishing.

---

## Task #17 CLOSED: `max_memory` is two levers, and the AO tensor is the smaller one

All three arms finished. CH3OH/cc-pVQZ, 230 basis functions, `ru_maxrss` deltas per phase,
one arm per process.

| arm | `mf.max_memory` | cc budget | `mf._eri` | `SCF.kernel` | `CCSD.ao2mo` | peak RSS |
|---|---|---|---|---:|---:|---:|
| A — stock | 4000 MB | 4000, inherited | **True**, 2.6290 GB | +2.6758 | +1.0617 | **3.8568** |
| B — throttled | 500 MB | 500, inherited | False | +0.0266 | +1.9238 | **2.0671** |
| C — SCF only | 500 MB | 4000, restored | False | +0.0267 | +3.3783 | **3.5233** |
| C′ — replicate | 500 MB | 4000, restored | False | +0.0265 | +3.3805 | **3.5244** |

**The bit-identity gate PASSES at cc-pVQZ.** `E_SCF = -115.099552400814 Ha` in every arm and
every run, to all fifteen figures. The DZ result transfers: Schwarz screening at
`direct_scf_tol=1e-13` costs nothing on this energy at 230 basis functions either. **Its
boundary, stated because this is exactly the claim that gets silently upgraded:** the probe
stops after `mycc.ao2mo()`, so no correlation energy was ever computed in these arms. Bit-
identity of `E_CCSD(T)` or of `D_e` under `max_memory` throttling is **UNVERIFIED.**

**Arm C is the finding, and it refutes the "not a shell game" paragraph above.** With the
SCF throttled but the CC layer left at stock, unbuilding a 2.6290 GB AO tensor moves the
peak by **8.6%**, not 68%. The accounting closes to a thousandth of a GB:

```
A -> C   SCF gave up  -2.6491 GB      ao2mo took back  +2.3166 GB      net  -0.3325
         measured change in peak                                            -0.3335
C -> B   ao2mo alone                                   -1.4545 GB
         measured change in peak                                            -1.4562
```

**87.4% of what the SCF stopped allocating reappeared in the transform.** So the 46.4%
reduction arm B delivers is not one lever, it is two, and they split **18.6% / 81.4%** —
unbuilding the AO tensor is the *smaller* contribution by a factor of four. Arm B only works
because `cc.CCSD(mf)` copies the budget at construction (`pyscf/cc/ccsd.py:967`,
`self.max_memory = mf.max_memory`), so setting `mf.max_memory` once silently throttles both
layers. Restore the CC budget and four fifths of the saving evaporates.

**Why, from source — and it is a thermostat, not a coincidence.** `_make_eris_outcore`
computes its budget twice (`ccsd.py:1559` and `ccsd.py:1566`) as

```python
max_memory = max(MEMORYMIN, mycc.max_memory-lib.current_memory()[0])
```

and `lib.current_memory()` reads **live RSS from `/proc/self/statm`**
(`pyscf/lib/misc.py:163-169`) — not a high-water mark. A resident `_eri` therefore subtracts
from the transform's own budget, so **PySCF allocates less in `ao2mo` precisely because it
already allocated more in the SCF.** The phases are not independent; they negotiate over one
live figure. That is why the peak is so much less than the sum of what each phase would take
alone, and why freeing 2.63 GB upstream buys only 0.33 GB downstream.

The budget then sizes real in-RAM arrays — `blksize` at `ccsd.py:1573-1574`, and
`numpy.empty` at `ccsd.py:1579`, `1580`, `1586` — which is where the earlier reasoning went
wrong. It correctly predicted *which branch* runs (`eris.vvvv` is an h5py `Dataset` in all
four readings above, never an `ndarray`) and then treated that as an answer about *how much
the branch allocates*. Outcore means the RESULT streams to HDF5. It does not mean the working
set is small.

**`max_memory` is advisory, and it has a floor that can overrule you upward.**
`MEMORYMIN = 2000` (`ccsd.py:39`) is the first argument of both `max()` calls, so a request
of 500 MB is silently serviced as 2000 MB. Arm B asked for 500 and `ao2mo` allocated
1.9238 GB — 3.9× over — which is the floor behaving exactly as written, not an overrun.

**OPEN, and named rather than smoothed over.** That same formula predicts arm A ≈ arm B:
both floor to `MEMORYMIN` (A because `4000 − ~2750` undercuts 2000, B because `500 − ~120`
undercuts it harder), so both should compute the same `blksize` and allocate the same
buffers. Measured, they are **1.81× apart** (1.0617 vs 1.9238 GB). Nor do the three
documented buffers close it by hand: at `blksize = 174` with `nocc = 9`, `nmo = nao = 230`,
no frozen core, `ccsd.py:1579/1580/1586` come to ≈1.33 GB, between the two measurements and
matching neither. Both facts point the same way — there is a second sizing path,
almost certainly the buffers inside `ao2mo.full` (`ccsd.py:1561`) and
`ao2mo.outcore.half_e1` (`ccsd.py:1568`), which receive the same `max_memory` and were not
read. **The discriminating probe, so nobody has to re-derive it:** log
`lib.current_memory()[0]`, `mycc.max_memory`, and the computed `blksize` at `ccsd.py:1566`
and `1573` in each arm. Filed as task #19.

**Instrument note — the probe now replicates, and that is new.** Arms A and B were launched
before the `--repeat` fix and looped in-process, so their run 2 is the monotone-instrument
artifact: A reports `SCF.kernel +0.0000 GB` and B reports a **0.00% spread**, and the zero
and the zero-spread are the *same* defect wearing opposite disguises. Only run 1 of each is
a reading. Arm C ran post-fix, one subprocess per repeat, and its two independent readings
are **3.5233 and 3.5244 GB — 0.031% apart**. Against `ccsd_acceleration_probe.py`
disagreeing with itself by 13.3% on the same quantity, that is a real instrument improvement
and it localises the 13.3% to that probe rather than to peak RSS as a measurable.

**No wall-clock claim survives this batch.** Arm A's own two runs took 319.1 s and 630.4 s
for the identical `ao2mo` call in the identical process — 1.98× apart — because a 910-test
mutation sweep was running on the same 8-core box. `ru_maxrss` is immune to that; a stopwatch
is not. The only timing statement that clears the contamination is directional and coarse:
the throttled SCF is several-fold slower than the incore one (25.5 s stock against 165.2 and
83.9 s), and the exact factor is **UNVERIFIED**.

**Lastly, the small vindication.** The live `VmHWM` reading taken while arm B was still
running was 2.0236 GB and was published as a lower bound. The finished peak is 2.0671 GB.
The bound held.

---

## Task #19 CLOSED: the only sizing formula visible in `ccsd.py` sizes buffers that never set the peak

Measured 2026-07-26 with `experiments/ao2mo_sizing_probe.py`, committed. CH3OH/cc-pVQZ, 230
basis functions, one arm per process, `OMP_NUM_THREADS=1`. The probe wraps `ao2mo.full`,
`ao2mo.outcore.half_e1` and `ao2mo.outcore.guess_e1bufsize` and records, at the **call
boundary**, the `max_memory` each site was handed together with its exclusive `ru_maxrss`
delta. The budgets are therefore read as they cross the call, not reconstructed from a
memory reading — which matters, because the memory reading is the quantity under suspicion.

| arm | `mycc.max_memory` | live RSS at `ao2mo` entry | budget at `:1561` (vvvv) | budget at `:1568` | `ao2mo.full` Δpeak | outer `half_e1` Δpeak | `ao2mo` total | peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A — stock | 4000 | 2931.3 MB | **2000.0** *(floored)* | 3690.3 | **+0.7663** | **+0.0000** | 0.7663 | 3.5596 |
| B — throttled | 500 | 155.9 MB | **2000.0** *(floored)* | 2000.0 *(floored)* | **+1.8784** | **+0.0000** | 1.8784 | 2.0234 |
| C — SCF only | 4000 | 155.5 MB | 3844.5 | 3946.0 | **+3.3712** | **+0.0000** | 3.3712 | 3.5157 |

**THE HEADLINE, AND IT INVALIDATES THE HAND-DERIVATION IN #17.** In all three arms
`ao2mo.full`'s delta *equals the entire* `CCSD.ao2mo` delta, and the `half_e1` nested inside
it equals that in turn. So **100% of the transform's contribution to the peak is the vvvv
transform at `ccsd.py:1561`**, and — `ru_maxrss` deltas being additive over any partition of
the timeline — everything after it contributes exactly zero. That includes the `blksize`
loop at `ccsd.py:1573-1586`, whose three documented buffers come to **1.2371 GB** at a
2000 MB budget and **1.6353 GB** at arm C's. Task #17 hand-derived those buffers, got
1.33 GB, and reported that it "matched neither arm". It matched neither arm because it was
computing a set of arrays that **never set the mark**. The only sizing formula visible in
the `ccsd` source is the one that does not own the peak.

**THE UNREAD PATHS, NAMED.** Below `ccsd.py:1573` there are at least three more, none
mentioned by the ccsd source:

* `guess_e1bufsize` (`ao2mo/outcore.py:690`) — and it carries **a second floor**.
  `iobuf_words = max(int(mem_words//6), IOBUF_WORDS)` with `IOBUF_WORDS = 1e8` words
  = **800 MB**. `mem_words//6 ≥ 1e8` requires `max_memory ≥ 4800 MB`, so **below a 4800 MB
  budget this buffer is a constant and `max_memory` does not control it at all.** Observed
  `floored at IOBUF_WORDS: True` in all six calls across the three arms, and at cc-pVDZ too.
  `MEMORYMIN = 2000` was not the only floor; it was the only floor anyone had read.
* The `e1buflen` **override** at `outcore.py:442`: `e1buflen = max([x[2] for x in shranges])`.
  The value `guess_e1bufsize` returns is fed to `guess_shell_ranges` and then **discarded** —
  the buffers at `outcore.py:453-455` are sized from the shell ranges, not from the guess.
  Any derivation that stops at the guess is computing a number the code throws away.
* `guess_e2bufsize` (`outcore.py:702`) driving **four** further arrays at `outcore.py:294-297`,
  off `ioblk_size = max(max_memory*.1, 256)` — 0.8528 GiB at a 2000 MB budget.

**THE A-vs-C GAP IS THE THERMOSTAT, NOW READ OFF THE CALL RATHER THAN INFERRED.** Arm C is
handed **3844.5 MB** at the vvvv site and arm A is handed **2000.0**. Same
`mycc.max_memory = 4000`; the difference is `lib.current_memory()`, 155.5 MB against
2931.3 MB, because arm A is carrying a resident `mf._eri`. `4000 − 2931.3 = 1068.7`, which
floors to `MEMORYMIN`. So a resident AO tensor costs the transform **1.92× of its own
budget**, and that is the mechanism #17 described from the source printed as a number.

**AND THE A-vs-B ANOMALY THAT OPENED THIS TASK IS DISSOLVED RATHER THAN EXPLAINED.** #19 was
filed because the budget formula predicted arms A and B would be equal and they measured
1.81× apart. The formula was right: **both arms are handed exactly 2000.0 MB at the same
site**, both floored to `MEMORYMIN`. There is no second budget. The peak deltas differ
anyway — 0.7663 against 1.8784, 2.45× — so the discrepancy was never about sizing.

**CONJECTURED, not measured, with the discriminating probe named.** `numpy.empty` reserves
address space; RSS grows only as pages are first touched. Arm A enters the transform with
2.73 GB already resident, so part of the request can be served from already-faulted pages;
arm B enters with 0.145 GB and faults everything. If that is right, **a `ru_maxrss` delta is
not an allocation**, and the two questions come apart: *which phase owns the peak* is
answerable from a monotone counter, *how much does this phase need* is not. The supporting
observation is that the arm with the largest resident pool is the least reproducible —
across the two probes, arm C agrees with itself to **0.2%** (3.5157 vs 3.5233/3.5244), arm B
to **2.1%** (2.0234 vs 2.0671), and arm A to **7.7%** (3.5596 vs 3.8568), with A's `ao2mo`
delta alone 38% apart (0.7663 vs 1.0617). **The probe that decides it:** record
`/proc/self/statm` at exit as well as entry for each wrapped call, so live growth and peak
growth can be compared directly. Until that runs, no per-phase memory *requirement* is
established here — only per-phase *peak ownership*, which is what the instrument measures.

**THE PREDICTION REGISTERED IN THE PROBE'S DOCSTRING WAS REFUTED, ON BOTH HALVES.** It said
`half_e1`'s exclusive delta would be roughly equal across arms A and B, and that the loop
after `blksize` was where they diverge. The loop contributes **zero in every arm**, and
`half_e1` is exactly where they diverge (0.77 against 1.88). Right suspect function, wrong
role for it — which is the same error shape as #17's refuted claim, one level down: reasoning
about *which* code runs instead of measuring *what it allocates*.

**Bit-identity holds across this probe too.** `E_SCF = -115.099552400814 Ha` in all three
arms, all fifteen figures, matching `ao_storage_probe.py`'s four readings exactly — seven
runs across two independent instruments. The boundary is unchanged and still stands: both
probes stop after `ao2mo()`, so bit-identity of `E_CCSD(T)` or `D_e` under throttling remains
**UNVERIFIED**.

**Instrument limitation, stated because this probe does NOT replace the other one.** One run
per arm. It measures *attribution* — which sub-phase, handed which budget — which is a
within-run comparison and is sound from a monotone counter. Its peak figures are
corroboration of `ao_storage_probe.py`'s replicated ones, not a refinement of them, and the
7.7% arm-A disagreement between the two probes is exactly why that distinction is kept.

---

## Task #20 CLOSED: a `ru_maxrss` delta is not an allocation, and #19's attribution was of a nested call

Three arms, CH3OH/cc-pVQZ, one process each, `experiments/ao2mo_sizing_probe.py` extended to
read **both** boundaries with **both** gauges plus `ru_minflt`. Three predictions were
registered in the docstring before the run. **All three are refuted, and the refutation is
the finding.**

| arm | `mycc.max_memory` | live at entry | headroom | inner `half_e1` budget | inner Δpeak | **inner minor faults** | outer `half_e1` Δpeak | live Δ over `ao2mo` | peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A stock | 4000 | 2970.6 MB | 0.0392 | **2000.0** floored | **+0.7608** | **2,932,916** | +0.0000 | **−2.6670** | 3.5666 |
| B throttled | 500 | 156.2 MB | −0.0001 | **2000.0** floored | **+1.8799** | **2,872,059** | +0.0000 | +0.0401 | 2.0522 |
| C cc restored | 4000 | 156.3 MB | −0.0002 | 3843.6 | **+3.2994** | 3,213,531 | +0.0000 | −0.0302 | 3.4448 |

### The answer, in one comparison

Arms A and B are handed **exactly the same 2000.0 MB**, do the same transform on the same
molecule, and touch **2,932,916 against 2,872,059 pages — 2.1% apart**. Their `ru_maxrss`
deltas differ by **2.47×**. Same budget, same work, same page traffic, and the high-water
mark reports it two and a half times apart.

**A `ru_maxrss` delta is therefore not an allocation.** It is the amount by which one phase
happened to breach a mark set by the whole process history, and two phases doing identical
work report differently because of what was resident around them.

### The mechanism, and it is not the one that was registered

The prediction was **headroom**: that arm A entered `ao2mo` with the mark already above its
resident level, so its allocation partly fit underneath for free. **Measured: there is no
headroom.** All three arms enter with 0.0392, −0.0001 and −0.0002 GB — zero to within the
gap between two `/proc/self/statm` reads. The registered mechanism is dead.

What the numbers show instead is **overlap**. Arm A's live RSS *falls 2.6670 GB across the
call* — the 2.6290 GB `_eri` tensor is released while the transform's buffers are being
allocated, so the allocator hands back pages that were already resident and the mark barely
moves. Arm B has nothing to release, so every buffer page is genuinely new residency. Arm A
faults 2.1% **more** pages than arm B and raises the mark 2.47× **less**. That is
free-and-reallocate overlap, not a stale watermark, and it is **CONJECTURED** — the fault
counts are consistent with it and do not prove it.

### The registered predictions, each with its verdict

* **P1 — `peak_delta == max(0, rss_exit − maxrss_entry)` to within 0.05 GB. REFUTED at every
  site in every arm**, residuals +0.7608, +1.8799, +3.2994. The identity assumed RSS grows
  monotonically through the call. It does not: the buffers are freed *inside* the call, so
  the exit reading is at or below the entry reading while the mark genuinely rose in
  between. **Neither boundary reading sees a mid-call peak**, which means the live-RSS delta
  is not a repair for `ru_maxrss` — it is a different blind spot.
* **P2 — the live delta is roughly equal in arms A and B. REFUTED**, −2.5026 against −0.0027
  at `ao2mo.full`. And the refutation is uninformative in the way that matters: over this
  call the live delta is dominated by a *free*, not by an allocation, so it was never
  measuring the quantity the prediction was about.
* **P3 — `ru_minflt` tracks the live delta. REFUTED as stated, and it is the one that pays.**
  2.93M faults is 12.0 GB of page-touching against buffers of order 1 GB, because a page
  freed and re-touched is counted again. So minflt measures *traffic*, not footprint — and
  traffic is exactly the invariant across arms A and B that identifies them as the same work.
  The prediction was wrong about what the counter means and right that the counter was worth
  reading.

### A correction to task #19: those two sites were nested, not siblings

`ao2mo.full` and the first-logged `half_e1` have **identical** peak deltas in all three arms
— 0.7608/0.7608, 1.8799/1.8799, 3.2994/3.2994 — because `ao2mo.full` *calls* `half_e1`
internally, and a wrapper that logs on exit records the inner call first. #19 reported
"`ao2mo.full` owns 100% of the ao2mo peak contribution" and treated that delta as exclusive.
It is not exclusive: **100% of `ao2mo.full` is inside its nested `half_e1`.** The site that
sets the peak is `ao2mo.outcore.half_e1` *called from within `ao2mo.full`*, not the outer
`half_e1` at `ccsd.py:1568`.

What survives #19 unchanged: the outer `half_e1` contributes **+0.0000 GB in all three
arms**, three for three, so the `blksize` loop at `ccsd.py:1573-1586` still contributes
exactly zero, and the one sizing formula visible in the `ccsd` source still does not own the
peak. What does not survive is the attribution *within* `ao2mo.full`, which was reading a
call tree as a flat list.

### Arm C is the control, and it says the budget does still size the buffers

C is handed 3843.6 MB where B is floored to 2000.0 — a 1.92× budget ratio — and its peak
delta is 3.2994 against 1.8799, a 1.75× ratio, with 11.9% more page faults. So `max_memory`
genuinely controls the allocation, exactly as #19 concluded. It was never the sizing that was
misread; it was the *measurement* of it.

### What this bounds

Every per-phase memory figure in this file derived from a `ru_maxrss` delta is a statement
about **what a phase added to the process high-water mark in the context it ran in**, and not
about what that phase allocates. Within-run attribution across a partition of one timeline
stays sound — the deltas are still additive over that partition. **Cross-arm comparison of
two `ru_maxrss` deltas is not sound**, and the 2.47× at identical budget is the measured size
of the error. Where a cross-arm claim is wanted, `ru_minflt` is the counter that survived: it
is monotone, it cannot be masked by an earlier phase, and it was 2.1% reproducible across the
two arms that were doing the same work.

`E_SCF = -115.099552400814 Ha` in all three arms again — ten runs now, across three
instruments, all fifteen figures. The boundary is unchanged: every probe here stops after
`ao2mo()`, so bit-identity of `E_CCSD(T)` or `D_e` under throttling remains **UNVERIFIED**.
