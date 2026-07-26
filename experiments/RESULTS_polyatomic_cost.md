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

## The one thing to do next

Rerun this table at `--basis 'cbs(TZ,QZ)'` over the same six species. It is the
tier-matched number, it is the one that can legitimately be compared against 0.0562 eV, and
it doubles as the cc-pVQZ affordability test at small size before anything larger is tried.

Re-opening the public path needs a code edit as well as a measurement: `validated_profile`
in `PySCFOracle.__init__` requires `max_atoms <= 2`, while `_polyatomic_energy` is only
reachable above 2 — so no argument combination can publish a polyatomic energy today, no
matter what gets measured.
