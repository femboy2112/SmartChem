#!/usr/bin/env python
"""
Why is H2O2 the outlier? The hindered rotor is dead; this tests the next suspect.

WHAT THIS REPLACES
------------------
``RESULTS_polyatomic_cost.md`` named H2O2's harmonic treatment of its internal torsion as
"the most likely place this protocol is quietly wrong". ``vibrational_probe.py`` measured
that torsion: 377.8 cm^-1, contributing 0.0234 eV -- 2.9% of H2O2's zero-point energy.
The species' cbs(TZ,QZ) error is -0.1090 eV. Deleting the mode outright, which is a far
larger change than any hindered-rotor correction could produce, moves the error to
-0.0856 eV and leaves H2O2 still the worst species by a comfortable margin. The hypothesis
is refuted by its own upper bound.

THE NEXT SUSPECT, AND WHY
-------------------------
H2O2 is the only species in the profile with an O-O single bond. A peroxide linkage is the
textbook case of a bond where a single Slater determinant is a poor zeroth order: the
sigma* orbital is low-lying, its occupation is non-negligible, and CCSD(T) -- a
single-reference method -- degrades. If that is what is happening, it is not a bug in this
pipeline at all. It is the method's own domain boundary, and the correct response is to
detect and declare it rather than to keep tuning geometry and ZPE machinery that are
innocent.

WHAT IS MEASURED
----------------
From one CCSD(T) run per species, at the geometry this pipeline actually produces:

  T1        ||t1||_F / sqrt(n_correlated_electrons). The standard single-reference
            diagnostic. Above ~0.02 for closed-shell organics is the conventional signal
            that CCSD(T) results deserve suspicion.
  D1        the largest singular value of the t1 matrix. More sensitive than T1 to a
            single badly-behaved orbital pair, which is exactly the peroxide failure shape.
  max|t1|   the single worst amplitude, unaveraged.
  max|t2|   likewise for the doubles.
  (T)/Ecorr the perturbative triples as a fraction of the correlation energy. A large
            share means the CCSD reference is leaning on a correction it was not designed
            to lean on.

These are DIAGNOSTICS, not corrections. Nothing here changes a reported energy. The point
is to find out whether the six-species error ordering has an electronic-structure
explanation that the vibrational data does not supply.

HONEST LIMITS
-------------
The thresholds above (T1 > 0.02, and so on) are community conventions, not calibrated
decision boundaries measured in this repository. They are printed as a flag for the eye.
Six species is not enough to fit a boundary and this script does not try to. What it can
do is say whether the ordering of the diagnostic matches the ordering of the error -- and
if it does not, that suspect dies too, which is worth knowing before more effort is spent.

Run:
    OMP_NUM_THREADS=1 python experiments/multireference_probe.py --all
"""
from __future__ import annotations

import argparse
import os
import platform
import time
import warnings

import numpy as np

from smartchem.oracle.pyscf_oracle import (
    PYSCF_AVAILABLE,
    PySCFOracle,
    _closed_shell_spin,
)

from polyatomic_cost_probe import TOPOLOGY, build  # noqa: E402  (same directory)
from vibrational_probe import CBS_ERROR_EV  # noqa: E402

#: Conventional single-reference thresholds from the quantum-chemistry literature. NOT
#: measured here, NOT calibrated here, and deliberately not used to gate anything.
T1_CONVENTIONAL_LIMIT = 0.02
D1_CONVENTIONAL_LIMIT = 0.05


def diagnose(formula: str, geometry_tier: tuple[str, str], basis: str) -> dict | None:
    """Relax at the cheap tier, then read the CCSD(T) amplitudes at the expensive one."""
    from pyscf import cc, gto, scf

    molecule = build(formula)
    spin = _closed_shell_spin(molecule)
    if spin is None:
        return None

    engine = PySCFOracle(geometry_tier[0], geometry_tier[1],
                         max_atoms=len(molecule.atoms))
    t0 = time.perf_counter()
    coordinates, _zpe = engine._relaxed_geometry(molecule, spin)
    spec = "; ".join(f"{s} {x:.10f} {y:.10f} {z:.10f}"
                     for s, (x, y, z) in zip(molecule.atoms, coordinates))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mol = gto.M(atom=spec, basis=basis, spin=spin, charge=0, verbose=0)
        mf = scf.RHF(mol).run()
        if not mf.converged:
            raise RuntimeError(f"SCF did not converge for {formula}")
        ccsd = cc.CCSD(mf).run()
        if not ccsd.converged:
            raise RuntimeError(f"CCSD did not converge for {formula}")
        triples = ccsd.ccsd_t()
    wall = time.perf_counter() - t0

    t1 = np.asarray(ccsd.t1)
    t2 = np.asarray(ccsd.t2)
    # PySCF's RCCSD correlates every electron by default (no frozen core here, matching
    # ``_parts``), so the electron count is the full one.
    n_correlated = mol.nelectron
    t1_diag = float(np.linalg.norm(t1) / np.sqrt(n_correlated))
    d1_diag = float(np.linalg.svd(t1, compute_uv=False)[0])

    return {
        "formula": formula,
        "n_atoms": len(molecule.atoms),
        "nao": int(mol.nao_nr()),
        "e_corr": float(ccsd.e_corr),
        "e_triples": float(triples),
        "t1_diagnostic": t1_diag,
        "d1_diagnostic": d1_diag,
        "max_t1": float(np.abs(t1).max()),
        "max_t2": float(np.abs(t2).max()),
        "seconds": wall,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--species", default="H2O2",
                   help=f"one of {', '.join(sorted(TOPOLOGY))}")
    p.add_argument("--all", action="store_true", help="every species in TOPOLOGY")
    p.add_argument("--basis", default="cc-pVTZ",
                   help="the correlation basis; diagnostics are basis-sensitive")
    p.add_argument("--geometry-tier", default="HF/cc-pVDZ")
    args = p.parse_args(argv)

    if not PYSCF_AVAILABLE:
        raise SystemExit("this probe needs the backend: pip install 'smartchem[qc]'")

    method, _, basis = args.geometry_tier.partition("/")
    tier = (method, basis)
    targets = sorted(TOPOLOGY) if args.all else [args.species]

    print("=" * 90)
    print("MULTIREFERENCE PROBE -- is CCSD(T) itself the thing failing on H2O2?")
    print("=" * 90)
    print(f"  correlation tier : CCSD(T)/{args.basis}")
    print(f"  geometry tier    : {args.geometry_tier}")
    print(f"  machine          : {platform.processor() or platform.machine()}, "
          f"{os.cpu_count()} cpus, "
          f"OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS', 'unset')}")
    try:
        print(f"  load average     : {', '.join(f'{x:.2f}' for x in os.getloadavg())}")
    except OSError:
        pass
    print(f"  conventional flags: T1 > {T1_CONVENTIONAL_LIMIT}, D1 > {D1_CONVENTIONAL_LIMIT}"
          "  (community convention, NOT calibrated here)")
    print()

    rows = []
    for formula in targets:
        print(f"  {formula} ... ", end="", flush=True)
        result = diagnose(formula, tier, args.basis)
        if result is None:
            print("DECLINED (no closed-shell spin)")
            continue
        print(f"{result['seconds']:.1f} s")
        rows.append(result)

    print()
    print("=" * 90)
    print(f"  {'species':<8} {'nao':>4} {'T1':>8} {'D1':>8} {'max|t1|':>9} "
          f"{'max|t2|':>9} {'(T)/Ecorr':>10} {'err eV':>9}")
    print("-" * 90)
    for result in sorted(rows, key=lambda r: -abs(CBS_ERROR_EV.get(r["formula"], 0.0))):
        share = result["e_triples"] / result["e_corr"]
        error = CBS_ERROR_EV.get(result["formula"])
        flag = ""
        if result["t1_diagnostic"] > T1_CONVENTIONAL_LIMIT:
            flag += " T1!"
        if result["d1_diagnostic"] > D1_CONVENTIONAL_LIMIT:
            flag += " D1!"
        print(f"  {result['formula']:<8} {result['nao']:>4} "
              f"{result['t1_diagnostic']:>8.5f} {result['d1_diagnostic']:>8.5f} "
              f"{result['max_t1']:>9.5f} {result['max_t2']:>9.5f} "
              f"{share:>10.5f} "
              f"{'n/a' if error is None else f'{error:+.4f}':>9}{flag}")
    print("=" * 90)
    print()
    print("  Rows are ordered by |error|, worst first. If a diagnostic column is also")
    print("  monotone down the page, it is a candidate explanation. If it is not, that")
    print("  suspect is dead and should be recorded as dead rather than quietly reused.")
    print("  n=6. An ordering that matches is suggestive; it is not a calibration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
