"""
Price the two routes past the CCSD ``vvvv`` memory wall, one exact and one approximate.

    OMP_NUM_THREADS=1 python experiments/ccsd_acceleration_probe.py \
        --species H2O --basis cc-pVDZ --route conventional

Run one route per process. Peak RSS is a high-water mark for the whole process, so two
routes in one invocation would report the larger of them twice and neither honestly.

WHAT IS BEING MEASURED, AND WHY IT IS THE ATOMIZATION ENERGY
-----------------------------------------------------------
``experiments/basis_size_probe.py`` models the wall: CCSD stores ``vvvv``, an intermediate
quartic in the VIRTUAL orbital count, and at cc-pVTZ it reaches 9.5 GB for C3H8 and 15.9 GB
for CH3OC2H5 against a 7 GB box. Frozen core does not move it -- freezing an occupied
orbital removes it from ``nocc`` and ``nmo`` alike, so ``nvir`` is arithmetically unchanged.
Two library routes do move it:

  direct   ``mycc.direct = True``. PySCF then never builds ``vvvv`` and instead recomputes
           the contraction from AO integrals every CC iteration (``pyscf/cc/ccsd.py:1558``
           guards the ``ao2mo.full(..., 'vvvv')`` call; ``pyscf/cc/uccsd.py:1172`` does the
           same for the open-shell blocks, so the atoms are covered too). Same arithmetic,
           different schedule. IDENTITY-PRESERVING -- and the point of measuring it is the
           wall clock, because it trades memory for repeated integral work.

  df       Density fitting. ``pyscf.cc.dfccsd`` (RHF) and ``pyscf.cc.dfuccsd`` (UHF) both
           exist in 2.14.0, ``cc.CCSD(mf)`` dispatches to them when the mean field carries
           ``with_df``, and ``ccsd_t()`` runs on top because the triples never touch
           ``vvvv`` at all -- they go through ``eris.get_ovvv``. This one CHANGES THE
           NUMBER. It is a MEASURED TRADEOFF and the measurement is the deliverable.

The reported quantity is the electronic atomization energy

    D_e = sum(E_atom) - E_molecule

and not a correlation energy, because D_e is what this project publishes and because a
density-fitting error that cancels between a molecule and its own atoms is not an error
this project pays for. Quoting the correlation-energy shift instead would overstate the
cost of the ``df`` route by whatever cancels -- and how much cancels is exactly the
unknown.

THE AUXBASIS TRAP, NAMED BEFORE IT BITES
----------------------------------------
``scf.RHF(mol).density_fit()`` fits with the ``-jkfit`` auxiliary set, which is designed
for Coulomb and exchange matrices. ``dfccsd``/``dfuccsd`` then REUSE that set for the
correlation energy (``dfccsd.py:35-38``, ``dfuccsd.py:33-37``: they adopt ``mf.with_df``
whenever the mean field has one, and only build the ``-ri`` correlation-fitting set when
it does not). The ``-ri`` sets exist and load for every element here. So the natural
spelling silently correlates with the wrong auxiliary basis. ``--route df-ri`` fits the
correlation with the ``-ri`` set explicitly; the gap between ``df`` and ``df-ri`` is how
much that default costs.

THE INSTRUMENT RULE
-------------------
This file re-implements ``PySCFOracle._parts`` rather than calling it, because the oracle
exposes no hook for the CC object. A re-implementation that has drifted from the original
measures nothing about the original. So every run CALIBRATES: the free atoms are computed
through the real ``PySCFOracle._parts`` as well, and bit-identity is REQUIRED before any
route number is believed. On an accelerated route the calibration still runs on the
conventional replica, so a drift is caught even when the route's own answer is expected to
differ. A run that fails calibration prints the residual and exits non-zero rather than
reporting a difference it cannot attribute.
"""
from __future__ import annotations

import argparse
import hashlib
import resource
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smartchem.category import Molecule                                    # noqa: E402
from smartchem.oracle.pyscf_oracle import (                                # noqa: E402
    ATOM_SPIN,
    HARTREE_EV,
    PySCFOracle,
    ConvergenceFailure,
    resolve_basis,
)

from polyatomic_cost_probe import TOPOLOGY, build                          # noqa: E402

ROUTES = ("conventional", "direct", "df", "df-ri")

#: Auxiliary-basis families PySCF maps a correlation-consistent orbital basis onto.
#: ``-jkfit`` is what ``.density_fit()`` picks; ``-ri`` is what a correlation treatment
#: is supposed to use. Named here so the difference between the two is a stated policy
#: rather than a library default nobody chose.
_RI_AUXBASIS = {
    "cc-pVDZ": "cc-pvdz-ri", "cc-pVTZ": "cc-pvtz-ri", "cc-pVQZ": "cc-pvqz-ri",
}

GEOMETRY_METHOD = "HF"
GEOMETRY_BASIS = "cc-pVDZ"


def _peak_gb() -> float:
    """Peak resident set for this process. Linux reports ru_maxrss in kilobytes."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0)


def _parts(atom_spec, symbols, basis, spin, method, route):
    """
    ``(E_HF, E_corr)`` in Hartree -- the replica of ``PySCFOracle._parts`` with a route.

    Every setting below is copied from that method deliberately and must stay copied:
    conv_tol 1e-10 and max_cycle 300 on the SCF, the newton fallback, conv_tol 1e-9 and
    max_cycle 300 on the CC. The calibration in ``main`` is what enforces that.
    """
    from pyscf import cc, gto, scf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mol = gto.M(atom=atom_spec, basis=resolve_basis(symbols, basis, False),
                    spin=spin, verbose=0, unit="Angstrom")
        mf = (scf.RHF if spin == 0 else scf.UHF)(mol)
        if route in ("df", "df-ri"):
            mf = mf.density_fit()
        mf.conv_tol = 1e-10
        mf.max_cycle = 300
        mf.kernel()
        if not mf.converged:
            mf = mf.newton()
            mf.kernel()
        if not mf.converged:
            raise ConvergenceFailure(f"SCF did not converge for {atom_spec} / {basis}")
        if method == "HF":
            return mf.e_tot, 0.0

        # A one-electron fragment has no correlation energy to compute, and PySCF's
        # DF-UCCSD cannot be asked for it: with zero beta electrons a spin block has
        # dimension 0 and h5py refuses the chunk ("All chunk dimensions must be
        # positive"). Every hydrogen-containing species hits this, which is nearly all
        # of them -- so it is reported, not swallowed.
        #
        # Falling back is not a fudge. Correlation vanishes identically for one electron,
        # and the conventional route MEASURES that: H/cc-pVDZ gives e_corr = -1.92e-32
        # Hartree and ccsd_t() = 0.0 exactly. No route can change zero.
        if route in ("df", "df-ri") and mol.nelectron <= 1:
            print(f"  note             : {atom_spec.split()[0]} has {mol.nelectron} "
                  f"electron; DF-UCCSD cannot run and correlation is identically zero")
            return mf.e_tot, 0.0

        mycc = cc.CCSD(mf)
        if route == "direct":
            mycc.direct = True
        if route == "df-ri":
            from pyscf import df
            aux = _RI_AUXBASIS.get(basis)
            if aux is None:
                raise KeyError(f"no -ri auxiliary basis registered for {basis}")
            mycc.with_df = df.DF(mol, auxbasis=aux)
        mycc.conv_tol = 1e-9
        mycc.max_cycle = 300
        mycc.kernel()
        if not mycc.converged:
            raise ConvergenceFailure(f"CCSD did not converge for {atom_spec} / {basis}")
        corr = mycc.e_corr
        if method == "CCSD(T)":
            corr += mycc.ccsd_t()
        return mf.e_tot, corr


def _geometry(formula: str) -> tuple[Molecule, np.ndarray, str]:
    """
    The structure every route is compared at, relaxed once at the geometry tier.

    Route-independent by construction -- the geometry engine is HF and no route touches
    HF -- but the coordinates are hashed and printed anyway, so two runs that claim to be
    comparable can be checked rather than assumed.
    """
    if formula in ATOM_SPIN and formula not in TOPOLOGY:
        molecule = Molecule.atom(formula)
        return molecule, np.zeros((1, 3)), "atom"
    molecule = build(formula)
    engine = PySCFOracle(GEOMETRY_METHOD, GEOMETRY_BASIS, max_atoms=len(molecule.atoms))
    coordinates, _zpe = engine._relaxed_geometry(molecule, 0)
    digest = hashlib.sha256(
        np.round(coordinates, 9).tobytes()).hexdigest()[:16]
    return molecule, coordinates, digest


def _spec(symbols, coordinates) -> str:
    return "; ".join(f"{s} {x:.10f} {y:.10f} {z:.10f}"
                     for s, (x, y, z) in zip(symbols, coordinates))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species", required=True)
    parser.add_argument("--basis", default="cc-pVDZ")
    parser.add_argument("--method", default="CCSD(T)")
    parser.add_argument("--route", default="conventional", choices=ROUTES)
    parser.add_argument("--skip-calibration", action="store_true",
                        help="report anyway if the replica has drifted (records WHY)")
    args = parser.parse_args(argv)

    molecule, coordinates, digest = _geometry(args.species)
    symbols = molecule.atoms
    elements = tuple(sorted(set(symbols)))

    print("=" * 78)
    print(f"CCSD ACCELERATION PROBE -- route={args.route}")
    print("=" * 78)
    print(f"  species          : {args.species}  ({len(symbols)} atoms)")
    print(f"  energy tier      : {args.method}/{args.basis}")
    print(f"  geometry         : {GEOMETRY_METHOD}/{GEOMETRY_BASIS}, sha256[:16]={digest}")
    print(f"  route class      : "
          f"{'IDENTITY-PRESERVING' if args.route in ('conventional', 'direct') else 'MEASURED TRADEOFF'}")
    print()

    t0 = time.perf_counter()
    atoms = {}
    for element in elements:
        spin = ATOM_SPIN[element]
        hf, corr = _parts(f"{element} 0 0 0", (element,), args.basis, spin,
                          args.method, args.route)
        atoms[element] = hf + corr
    t_atoms = time.perf_counter() - t0

    # -- calibration: the conventional replica must reproduce the shipping code exactly
    oracle = PySCFOracle(args.method, args.basis, max_atoms=len(symbols))
    worst = 0.0
    for element in elements:
        spin = ATOM_SPIN[element]
        hf, corr = _parts(f"{element} 0 0 0", (element,), args.basis, spin,
                          args.method, "conventional")
        reference = sum(oracle._parts(f"{element} 0 0 0", (element,), args.basis, spin))
        worst = max(worst, abs((hf + corr) - reference))
    calibrated = worst == 0.0
    print(f"  calibration      : max |replica - PySCFOracle._parts| = {worst:.3e} Ha "
          f"over {len(elements)} free atoms  [{'PASS' if calibrated else 'FAIL'}]")
    if not calibrated and not args.skip_calibration:
        print("  ABORTING: the replica has drifted from the shipping path, so any route")
        print("  difference below could be the drift rather than the route. Re-sync")
        print("  _parts against smartchem/oracle/pyscf_oracle.py before believing it.")
        return 2
    print()

    t1 = time.perf_counter()
    if len(symbols) == 1:
        e_mol = atoms[symbols[0]]
    else:
        hf, corr = _parts(_spec(symbols, coordinates), symbols, args.basis, 0,
                          args.method, args.route)
        e_mol = hf + corr
    t_mol = time.perf_counter() - t1

    d_e = (sum(atoms[s] for s in symbols) - e_mol) * HARTREE_EV
    print(f"  D_e (electronic) : {d_e:.6f} eV        <-- compare across routes")
    print(f"  E_molecule       : {e_mol * HARTREE_EV:.6f} eV")
    print(f"  wall: atoms      : {t_atoms:.1f} s")
    print(f"  wall: molecule   : {t_mol:.1f} s")
    print(f"  wall: total      : {t_atoms + t_mol:.1f} s")
    print(f"  peak RSS         : {_peak_gb():.3f} GB")
    print()
    print("  D_e here is ELECTRONIC and carries no ZPE, no CBS extrapolation and no")
    print("  spin-orbit term, so it is not comparable to a reference D0. It is a")
    print("  route-to-route contrast and nothing else.")
    print(f"ROUTE_RESULT {args.species} {args.basis} {args.route} "
          f"{d_e:.9f} {t_atoms + t_mol:.2f} {_peak_gb():.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
