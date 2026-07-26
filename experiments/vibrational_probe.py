#!/usr/bin/env python
"""
Where does the polyatomic ZPE actually come from, and is the 9.1% bias entitled to be there?

THE QUESTION
------------
``ZPE_BIAS_FRACTION = 0.091`` is a measured displacement between HF/cc-pVDZ harmonic
frequencies and experimental ``omega_e``. ``ZPE_BIAS_TRAIN_SPECIES`` names the 23 species
it was fitted on and **every one of them is diatomic**. A diatomic has exactly one
vibrational mode and that mode is a bond stretch.

The tier-matched polyatomic sweep applies that same 0.091 to H2O, NH3, CH4, CO2, H2O2 and
CH3OH -- species whose modes are mostly *not* stretches. CH4 has four stretches and five
bends; H2O2 has two stretches, two bends, and one large-amplitude internal torsion. The
implicit claim is that a scale factor fitted exclusively on stretching motion transfers to
bending and torsional motion. Nothing in this repository has ever tested that claim.

This probe does not settle it -- settling it needs experimental polyatomic frequencies,
which are not tabulated here. What it does is make the claim *quantitative*: it dumps
every harmonic mode of every measured polyatomic, so the size of the term, its
mode-by-mode composition, and its relation to the observed CBS error stop being
assertions and become numbers.

WHAT THE ANSWER CHANGES
-----------------------
The 9.1% is carried as a systematic term, not folded into the value (see
``pyscf_oracle.py`` line 739 and 751-756). So it cannot make the reported *energy* wrong.
It can make the reported *uncertainty* wrong in either direction, and an uncertainty that
is wrong low is the same class of defect as a wrong number wearing a confident face.

H2O2 IS THE REASON THIS EXISTS
------------------------------
It is the worst species at both tiers (-0.5046 eV at cc-pVTZ, -0.1090 eV at cbs(TZ,QZ)),
and the only one whose relaxation exercised the saddle-descent path: a symmetric bond-graph
seed relaxes to the trans-planar transition state for internal rotation, which the
curvature check catches and repairs. Its torsional mode is exactly the kind of motion a
diatomic-fitted stretch correction has no claim on.

SELF-CHECK
----------
The zero-point energy is computed twice by two different routes -- once inside
``_relaxed_geometry`` (which returns it) and once here from a freshly rebuilt Hessian at
the coordinates that came back. They must agree to within tight tolerance or the two runs
are not looking at the same stationary point and every number below is meaningless. The
probe says so and exits nonzero rather than reporting a table it cannot vouch for.

Run:
    OMP_NUM_THREADS=1 python experiments/vibrational_probe.py --species H2O2
    OMP_NUM_THREADS=1 python experiments/vibrational_probe.py --all
"""
from __future__ import annotations

import argparse
import os
import platform
import time
import warnings

import numpy as np

from smartchem.geometry import CM_TO_EV, harmonic_analysis, is_linear
from smartchem.oracle.pyscf_oracle import (
    PYSCF_AVAILABLE,
    ZPE_BIAS_FRACTION,
    ZPE_BIAS_TRAIN_SPECIES,
    PySCFOracle,
    _closed_shell_spin,
)

from polyatomic_cost_probe import TOPOLOGY, build  # noqa: E402  (same directory)

#: The tier-matched CBS(TZ,QZ) errors measured in RESULTS_polyatomic_cost.md, commit
#: 67d8243. Reproduced here so the ZPE term can be compared against the residual it would
#: have to explain. These are DATA, not a fit -- do not adjust them to make a story work.
CBS_ERROR_EV = {
    "H2O": -0.0300, "NH3": -0.0609, "CH4": -0.0364,
    "CO2": -0.0396, "H2O2": -0.1090, "CH3OH": -0.0588,
}

#: Frequency below which a mode is reported as a candidate large-amplitude motion. This is
#: a REPORTING threshold for the eye, not a physical classification and not used in any
#: arithmetic below. Torsions and ring puckers live here; so do soft bends.
SOFT_MODE_CM = 700.0


def dihedral_deg(coords: np.ndarray, i: int, j: int, k: int, m: int) -> float:
    """Signed dihedral i-j-k-m in degrees, by the standard three-vector construction."""
    b0 = coords[i] - coords[j]
    b1 = coords[k] - coords[j]
    b2 = coords[m] - coords[k]
    b1 = b1 / np.linalg.norm(b1)
    v = b0 - np.dot(b0, b1) * b1
    w = b2 - np.dot(b2, b1) * b1
    return float(np.degrees(np.arctan2(np.dot(np.cross(b1, v), w), np.dot(v, w))))


def analyse(formula: str, method: str, basis: str) -> dict | None:
    """Relax, certify, and re-derive the modes at the certified minimum."""
    molecule = build(formula)
    engine = PySCFOracle(method, basis, max_atoms=len(molecule.atoms))
    spin = _closed_shell_spin(molecule)
    if spin is None:
        return None

    t0 = time.perf_counter()
    coordinates, zpe_from_pipeline = engine._relaxed_geometry(molecule, spin)

    # Rebuild the Hessian at the coordinates the pipeline certified, by the same call the
    # pipeline's own ``certify`` makes. This is the second, independent route to the ZPE.
    spec = "; ".join(f"{s} {x:.10f} {y:.10f} {z:.10f}"
                     for s, (x, y, z) in zip(molecule.atoms, coordinates))
    mol, mf = engine._mean_field(spec, molecule.atoms, spin)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        hessian = mf.Hessian().kernel()
    analysis = harmonic_analysis(mol.atom_mass_list(isotope_avg=True),
                                 coordinates, hessian)
    wall = time.perf_counter() - t0

    return {
        "formula": formula,
        "atoms": molecule.atoms,
        "coordinates": coordinates,
        "frequencies_cm": analysis.frequencies_cm,
        "zpe_recomputed_ev": analysis.zero_point_energy_ev,
        "zpe_from_pipeline_ev": zpe_from_pipeline,
        "imaginary_modes": analysis.imaginary_modes,
        "linear": is_linear(coordinates),
        "seconds": wall,
    }


def report(result: dict) -> bool:
    """Print one species. Returns False if the self-check failed."""
    formula = result["formula"]
    freqs = np.asarray(result["frequencies_cm"], dtype=float)
    n_atoms = len(result["atoms"])
    expected_modes = 3 * n_atoms - (5 if result["linear"] else 6)

    zpe = result["zpe_recomputed_ev"]
    drift = abs(zpe - result["zpe_from_pipeline_ev"])
    ok = drift <= 1e-6 and result["imaginary_modes"] == 0

    print("=" * 78)
    print(f"{formula}   ({n_atoms} atoms, "
          f"{'linear' if result['linear'] else 'nonlinear'}, "
          f"{len(freqs)} modes reported, {expected_modes} expected)")
    print("=" * 78)

    print("  harmonic modes (cm^-1) and their zero-point contribution:")
    for index, nu in enumerate(freqs):
        share = 0.5 * nu * CM_TO_EV
        mark = "  <- soft" if 0.0 < nu < SOFT_MODE_CM else ""
        print(f"    {index + 1:>2}  {nu:>9.1f} cm^-1   {share:>8.4f} eV"
              f"   {100.0 * share / zpe:>5.1f}%{mark}")

    soft = [nu for nu in freqs if 0.0 < nu < SOFT_MODE_CM]
    soft_ev = sum(0.5 * nu * CM_TO_EV for nu in soft)
    bias = ZPE_BIAS_FRACTION * zpe

    print()
    print(f"  total harmonic ZPE          : {zpe:.4f} eV")
    print(f"  ZPE recomputed vs pipeline  : drift {drift:.2e} eV "
          f"({'AGREE' if drift <= 1e-6 else 'DISAGREE -- STOP'})")
    print(f"  imaginary modes             : {result['imaginary_modes']}")
    print(f"  modes below {SOFT_MODE_CM:.0f} cm^-1       : {len(soft)} "
          f"carrying {soft_ev:.4f} eV ({100.0 * soft_ev / zpe:.1f}% of the ZPE)")
    print(f"  {ZPE_BIAS_FRACTION:.1%} systematic term       : {bias:.4f} eV")

    error = CBS_ERROR_EV.get(formula)
    if error is not None:
        print(f"  measured cbs(TZ,QZ) error   : {error:+.4f} eV")
        print(f"  |bias| / |error|            : {abs(bias) / abs(error):.2f}x")
        print(f"      the systematic term is {'LARGER' if abs(bias) > abs(error) else 'smaller'} "
              f"than the residual it sits beside.")

    if formula == "H2O2":
        coords = np.asarray(result["coordinates"])
        # TOPOLOGY writes H2O2 as O0-O1, O0-H2, O1-H3, so the torsion is H2-O0-O1-H3.
        print(f"  HOOH dihedral               : {dihedral_deg(coords, 2, 0, 1, 3):.1f} deg")
        print("      the trans-planar saddle is 180 deg; a skewed minimum is not.")

    print(f"  wall clock                  : {result['seconds']:.1f} s")
    print()
    return ok


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--species", default="H2O2",
                   help=f"one of {', '.join(sorted(TOPOLOGY))}")
    p.add_argument("--all", action="store_true", help="every species in TOPOLOGY")
    p.add_argument("--method", default="HF")
    p.add_argument("--basis", default="cc-pVDZ",
                   help="the geometry tier -- this is where the ZPE is actually born")
    args = p.parse_args(argv)

    if not PYSCF_AVAILABLE:
        raise SystemExit("this probe needs the backend: pip install 'smartchem[qc]'")

    targets = sorted(TOPOLOGY) if args.all else [args.species]

    print("=" * 78)
    print("VIBRATIONAL PROBE -- what the polyatomic ZPE is made of")
    print("=" * 78)
    print(f"  tier             : {args.method}/{args.basis}")
    print(f"  ZPE bias         : {ZPE_BIAS_FRACTION:.1%}, fitted on "
          f"{len(ZPE_BIAS_TRAIN_SPECIES)} species, ALL DIATOMIC")
    print(f"  machine          : {platform.processor() or platform.machine()}, "
          f"{os.cpu_count()} cpus, "
          f"OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS', 'unset')}")
    try:
        print(f"  load average     : {', '.join(f'{x:.2f}' for x in os.getloadavg())}")
    except OSError:
        pass
    print()

    healthy = True
    rows = []
    for formula in targets:
        result = analyse(formula, args.method, args.basis)
        if result is None:
            print(f"{formula}: DECLINED (no closed-shell spin)")
            healthy = False
            continue
        healthy &= report(result)
        rows.append(result)

    if len(rows) > 1:
        print("=" * 78)
        print("SUMMARY -- is the bias term commensurate with the residual error?")
        print("=" * 78)
        print(f"  {'species':<8} {'modes':>5} {'soft':>5} {'ZPE eV':>9} "
              f"{'bias eV':>9} {'err eV':>9} {'bias/|err|':>11}")
        for result in rows:
            freqs = np.asarray(result["frequencies_cm"], dtype=float)
            zpe = result["zpe_recomputed_ev"]
            bias = ZPE_BIAS_FRACTION * zpe
            soft = sum(1 for nu in freqs if 0.0 < nu < SOFT_MODE_CM)
            error = CBS_ERROR_EV.get(result["formula"])
            ratio = f"{bias / abs(error):.2f}x" if error else "n/a"
            print(f"  {result['formula']:<8} {len(freqs):>5} {soft:>5} {zpe:>9.4f} "
                  f"{bias:>9.4f} {error if error is None else f'{error:+.4f}':>9} "
                  f"{ratio:>11}")
        print()
        print("  n=6, one tier, no experimental polyatomic frequencies to compare against.")
        print("  This sizes the term. It does not validate or refute the transfer.")

    if not healthy:
        print("SELF-CHECK FAILED -- do not quote any table above.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
