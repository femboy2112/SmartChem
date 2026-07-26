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
| H2O2 | 452.5 s | −0.1090 | −2.51 | 4.6× smaller | 9.7× |
| CH3OH | *running* | | | | |

```
MAE (5 of 6)   0.0552 eV   (1.27 kcal/mol)
published diatomic MAE at the same tier   0.0562 eV
```

Three of the five are inside chemical accuracy (1 kcal/mol = 0.0433 eV). The five-species
MAE sits within 2% of the published diatomic figure — the first evidence that polyatomic
accuracy at this tier is of the same order as the validated diatomic number rather than six
times worse. Every error is still negative, so residual underbinding survives the
extrapolation; it is now small rather than dominant.

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

**P-Q2 — CO2 and H2O2 both complete.** Modelled at 0.703 and 0.790 GB, so ~3.5–4 GB
calibrated: tight on this box but not over. *Predict both finish inside 1800 s.*
**Falsifier:** either one is killed by the timeout.
**→ CONFIRMED.** CO2 608.0 s, H2O2 452.5 s, both well inside. Cost ratios 11.6× and 9.7×,
both inside the observed 8–11× band, so the memory model's implied cost behaviour holds
where it predicted headroom.

**P-Q3 — the six-species CBS MAE lands between 0.03 and 0.08 eV**, i.e. comparable to the
published 0.0562 eV rather than to the 0.3575 eV measured at plain cc-pVTZ.
**Falsifier:** MAE above 0.15 eV.

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

## The one thing to do next

Finish scoring P-Q1 through P-Q3, then decide the protocol for anything above 6 atoms on
the DF-vs-tier evidence rather than on the assumption that frozen core buys headroom.

Re-opening the public path needs a code edit as well as a measurement: `validated_profile`
in `PySCFOracle.__init__` requires `max_atoms <= 2`, while `_polyatomic_energy` is only
reachable above 2 — so no argument combination can publish a polyatomic energy today, no
matter what gets measured.
