#!/usr/bin/env python
"""
Re-derive ZPE_BIAS_FRACTION from scratch, and decide whether the code over-applies it.

THE QUESTION
------------
``ZPE_BIAS_FRACTION = 0.091`` (``pyscf_oracle.py``) is the measured tendency of an HF
harmonic ZPE to come out too high. It is carried in ``systematic_terms`` and -- this
matters -- is NOT applied to ``value_ev``, so it cannot make an energy wrong. It can make
an *uncertainty* wrong, and for four of the six original polyatomics the term it reports is
larger than the residual it is meant to explain.

The script that fitted it, ``scratchpad/geom_calibrate.py``, is in no commit on any branch
and no longer exists. Only its roster survived, recovered as ``ZPE_BIAS_TRAIN_SPECIES``.
So the constant is a number nobody can reproduce, sitting in the uncertainty budget of
every polyatomic estimate this project will ever publish. This harness is the instrument
that makes it reproducible; it is deliberately committed, unlike its ancestor.

THE SPECIFIC DEFECT THIS IS BUILT TO DECIDE
--------------------------------------------
A percentage needs a denominator, and there are two candidates:

    f_A = (zpe_comp - zpe_ref) / zpe_ref      fraction of the REFERENCE ZPE
    f_B = (zpe_comp - zpe_ref) / zpe_comp     fraction of the COMPUTED ZPE

``pyscf_oracle.py:809`` applies the constant to the COMPUTED ZPE::

    zpe_bias = ZPE_BIAS_FRACTION * zpe        # zpe here is the computed harmonic value

Pooled, the two satisfy ``f_B = f_A / (1 + f_A)`` exactly. So if the fit measured f_A and
the code treats it as f_B, the reported systematic is too large by exactly ``1 + f_A``.
Concretely, if zpe_comp = 1.091 * zpe_ref then the true overestimate is

    zpe_comp - zpe_ref = 0.091 * zpe_ref = (0.091 / 1.091) * zpe_comp = 0.0834 * zpe_comp

and applying ``0.091 * zpe_comp`` overstates it by **1.091x**. On CH3OH's 1.4896 eV ZPE
that is 0.0113 eV -- a quarter of chemical accuracy, in the wrong direction of confidence.

Whichever estimator lands on 0.091 tells you which denominator the lost script used.

WHY BOTH A MEAN AND A POOLED ESTIMATE
--------------------------------------
The mean of per-species ratios and the ratio of summed quantities are different estimators
and they weight the roster differently: the pooled form is dominated by H2 and the hydrides,
which carry the largest ZPEs, while the mean gives Na2 (0.0099 eV) the same vote as H2
(0.2728 eV). The lost script's choice is unrecoverable, so both are reported and the
verdict is only taken when they agree.

WHAT THIS SCRIPT DOES NOT DO
-----------------------------
It does not change ``ZPE_BIAS_FRACTION`` and it does not touch the oracle. It measures, it
prints, and it states which denominator the code's usage matches. Acting on a mismatch is a
separate deliberate edit -- this is the instrument, not the verdict.

It also cannot prove it has reproduced the ORIGINAL fit. The selection rule survived only
as prose, PySCF's version and convergence thresholds then are unknown, and prose can be
written to describe a known result rather than to specify the predicate that was run. If
this refit misses 0.091 on BOTH denominators, that is evidence the protocol has drifted --
NOT proof the old number was wrong, and NOT a licence to overwrite it from here.

Run:
    OMP_NUM_THREADS=1 python experiments/zpe_bias_refit.py
    OMP_NUM_THREADS=1 python experiments/zpe_bias_refit.py --protocol fixed
"""
from __future__ import annotations

import argparse
import math
import time

from smartchem.category import Molecule
from smartchem.data.reference import BOND_REFS, GEOMETRY, zero_point_energy_ev
from smartchem.geometry import GeometryError, harmonic_analysis
from smartchem.oracle.pyscf_oracle import (PYSCF_AVAILABLE, ZPE_BIAS_FRACTION,
                                           ZPE_BIAS_TRAIN_SPECIES, ConvergenceFailure,
                                           PySCFOracle)

#: The tier the constant was fitted at, per the surviving docstring.
GEOMETRY_METHOD = "HF"
GEOMETRY_BASIS = "cc-pVDZ"

#: Bond orders come from ``BOND_REFS``, not from a table written here. That is deliberate:
#: a hand-written order table in a calibration harness would be a hidden variable in the
#: constant it produces, and the repository already carries the curated value.
_BOND_ORDER = {ref.formula: ref.bond_order for ref in BOND_REFS}
_ATOMS = {ref.formula: ref.atoms for ref in BOND_REFS}


def _relaxed_zpe(formula: str) -> tuple[float, float]:
    """PROTOCOL R -- relax, then Hessian. Exactly the path ``_polyatomic_energy`` uses."""
    molecule = Molecule.diatomic(*_ATOMS[formula], order=_BOND_ORDER[formula])
    spin = GEOMETRY[formula][2]
    engine = PySCFOracle(GEOMETRY_METHOD, GEOMETRY_BASIS, max_atoms=2)
    t0 = time.perf_counter()
    _coords, zpe = engine._relaxed_geometry(molecule, spin)
    return zpe, time.perf_counter() - t0


def _fixed_zpe(formula: str) -> tuple[float, float]:
    """
    PROTOCOL F -- Hessian at the TABULATED r_e, no relaxation.

    This isolates the electronic method's frequency error from the geometry error. It is
    NOT the path production takes, so it cannot settle the denominator question on its own;
    it is here because it succeeds on all 23 species where Protocol R loses two, which
    makes it a useful control on whether those two losses skew the roster.
    """
    from pyscf import gto, scf

    a, b = _ATOMS[formula]
    r_e, _omega, spin = GEOMETRY[formula]
    t0 = time.perf_counter()
    mol = gto.M(atom=f"{a} 0 0 0; {b} 0 0 {r_e}", basis=GEOMETRY_BASIS, spin=spin,
                verbose=0)
    # RHF/UHF exactly as production selects them at pyscf_oracle.py:624 and :866. ROHF was
    # the obvious-looking choice and it is wrong twice: it does not match the production
    # path, and PySCF has no ROHF Hessian, so it silently reduced this control to the
    # closed-shell species -- which are precisely the ones with the SMALLEST bias.
    mf = scf.RHF(mol) if spin == 0 else scf.UHF(mol)
    mf.kernel()
    if not mf.converged:
        raise ConvergenceFailure(f"SCF did not converge for {formula} at fixed r_e")
    hessian = mf.Hessian().kernel()
    import numpy as np
    coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, r_e]])
    analysis = harmonic_analysis(mol.atom_mass_list(isotope_avg=True), coords, hessian)
    return analysis.zero_point_energy_ev, time.perf_counter() - t0


def run_refit(species: tuple[str, ...], protocol: str) -> int:
    measure = _relaxed_zpe if protocol == "relaxed" else _fixed_zpe
    print("=" * 88)
    print("ZPE BIAS REFIT -- re-deriving a constant whose original script no longer exists")
    print("=" * 88)
    print(f"  protocol         : {protocol}"
          f"{'  (the path production actually takes)' if protocol == 'relaxed' else '  (control; NOT the production path)'}")
    print(f"  geometry tier    : {GEOMETRY_METHOD}/{GEOMETRY_BASIS}")
    print(f"  roster           : {len(species)} species (ZPE_BIAS_TRAIN_SPECIES, committed literal)")
    print(f"  constant in code : ZPE_BIAS_FRACTION = {ZPE_BIAS_FRACTION}")
    print(f"  reference ZPE    : 0.5 * omega_e, reference.zero_point_energy_ev")
    print()
    print(f"  {'species':<8} {'zpe_ref':>9} {'zpe_comp':>9} {'delta':>9} "
          f"{'f_A':>8} {'f_B':>8} {'wall s':>8}")
    print("  " + "-" * 70)

    refs: list[float] = []
    comps: list[float] = []
    failures: list[tuple[str, str]] = []

    for formula in species:
        zpe_ref = zero_point_energy_ev(formula)
        if zpe_ref is None:
            failures.append((formula, "no omega_e tabulated"))
            print(f"  {formula:<8} {'--':>9}  DECLINED: no experimental omega_e")
            continue
        if formula not in _ATOMS:
            failures.append((formula, "no BOND_REFS row (atoms/bond order unavailable)"))
            print(f"  {formula:<8} {zpe_ref:>9.5f}  DECLINED: no BOND_REFS row")
            continue
        try:
            zpe_comp, wall = measure(formula)
        except (ConvergenceFailure, GeometryError, RuntimeError, ValueError) as exc:
            failures.append((formula, f"{type(exc).__name__}: {str(exc)[:70]}"))
            print(f"  {formula:<8} {zpe_ref:>9.5f}  FAILED: {type(exc).__name__}")
            continue
        refs.append(zpe_ref)
        comps.append(zpe_comp)
        delta = zpe_comp - zpe_ref
        print(f"  {formula:<8} {zpe_ref:>9.5f} {zpe_comp:>9.5f} {delta:>9.5f} "
              f"{delta / zpe_ref:>8.4f} {delta / zpe_comp:>8.4f} {wall:>8.1f}")

    print()
    n = len(refs)
    if n < 2:
        print("  too few species survived to fit anything. Nothing is concluded.")
        return 1

    a_each = [(c - r) / r for c, r in zip(comps, refs)]
    b_each = [(c - r) / c for c, r in zip(comps, refs)]
    a_mean = sum(a_each) / n
    b_mean = sum(b_each) / n
    a_pool = (sum(comps) - sum(refs)) / sum(refs)
    b_pool = (sum(comps) - sum(refs)) / sum(comps)
    a_sd = math.sqrt(sum((x - a_mean) ** 2 for x in a_each) / (n - 1))
    b_sd = math.sqrt(sum((x - b_mean) ** 2 for x in b_each) / (n - 1))

    print("=" * 88)
    print(f"  n fitted : {n} of {len(species)}")
    print()
    print(f"  {'estimator':<34} {'mean':>9} {'sd':>9} {'pooled':>9} {'|pooled-0.091|':>15}")
    print("  " + "-" * 78)
    print(f"  {'f_A  delta / REFERENCE zpe':<34} {a_mean:>9.5f} {a_sd:>9.5f} "
          f"{a_pool:>9.5f} {abs(a_pool - ZPE_BIAS_FRACTION):>15.5f}")
    print(f"  {'f_B  delta / COMPUTED  zpe':<34} {b_mean:>9.5f} {b_sd:>9.5f} "
          f"{b_pool:>9.5f} {abs(b_pool - ZPE_BIAS_FRACTION):>15.5f}")
    print()
    print(f"  identity check  f_A/(1+f_A) = {a_pool / (1.0 + a_pool):.6f}  vs "
          f"f_B pooled = {b_pool:.6f}   (must agree)")
    print(f"  the code applies ZPE_BIAS_FRACTION to the COMPUTED zpe, i.e. as an f_B")
    print()

    d_a = abs(a_pool - ZPE_BIAS_FRACTION)
    d_b = abs(b_pool - ZPE_BIAS_FRACTION)
    agree = (a_mean < b_mean) == (a_pool < b_pool)

    print("  VERDICT")
    print("  -------")
    if not agree:
        print("  The mean and pooled estimators disagree about which denominator is closer.")
        print("  Undecided; the roster weighting is doing the work, not the physics.")
    elif d_a < d_b:
        print("  0.091 is closer to f_A, the REFERENCE-denominator fit, while the oracle")
        print("  applies it to the COMPUTED ZPE. That is the suspected mismatch, and this")
        print(f"  is evidence FOR it: the systematic is overstated by ~{1 + a_pool:.3f}x.")
        print(f"  The value consistent with the code's own usage would be {b_pool:.4f}.")
    else:
        print("  0.091 is closer to f_B, the COMPUTED-denominator fit, which is the")
        print("  denominator the oracle actually applies it to. The suspected 1.091x")
        print("  over-application is REFUTED on this evidence.")

    if min(d_a, d_b) > 0.01:
        print()
        print(f"  CAUTION -- this refit does not reproduce 0.091 on EITHER denominator")
        print(f"  (nearest is {min(d_a, d_b):.4f} away). The protocol has drifted since")
        print(f"  505c972: PySCF version, convergence thresholds and the exact roster")
        print(f"  weighting of the lost script are all unknown. Read the verdict above as")
        print(f"  'which denominator is nearer', NOT as a reproduction. Do not overwrite")
        print(f"  ZPE_BIAS_FRACTION from this run alone.")

    if failures:
        print()
        print(f"  {len(failures)} species did not contribute. Named, not silently dropped:")
        for formula, why in failures:
            print(f"    {formula:<8} {why}")
        print("  A mean over a roster that lost members is a different estimator than one")
        print("  over the full roster. Compare --protocol fixed, which loses none.")
    print("=" * 88)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--species", nargs="*", default=None,
                   help="override the roster (default: all of ZPE_BIAS_TRAIN_SPECIES)")
    p.add_argument("--protocol", choices=("relaxed", "fixed"), default="relaxed",
                   help="relaxed = production path; fixed = Hessian at tabulated r_e")
    args = p.parse_args()

    if not PYSCF_AVAILABLE:
        raise SystemExit("PySCF is not installed; this harness measures, it cannot pretend.")

    roster = tuple(args.species) if args.species else ZPE_BIAS_TRAIN_SPECIES
    return run_refit(roster, args.protocol)


if __name__ == "__main__":
    raise SystemExit(main())
