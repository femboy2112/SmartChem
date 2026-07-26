#!/usr/bin/env python
"""
What does one real polyatomic actually cost, end to end, and how far off is it?

THE QUESTION
------------
The public ``PySCFOracle.energy()`` declines polyatomic species. That is correct: the
seven-neutral-diatomic MAE does not quantify the seed/relax/Hessian/single-point protocol,
and inheriting it would be the "invent rather than decline" failure this project refuses.

Re-opening it needs a measured validation profile, and building that profile needs two
numbers nobody in this repository has ever measured:

  * what a CCSD(T) polyatomic single point on a relaxed geometry actually COSTS, and
  * how far its atomization energy lands from experiment.

Every polyatomic timing on record (C3H8 at 2515.9 s, CH3OC2H5 at 3444.2 s) is an *HF*
number where HF served as both geometry engine and final tier. No CCSD(T) polyatomic has
ever been run here, at any basis, on anything.

WHY THIS IS THE FIRST THING TO RUN, NOT THE FIFTH
-------------------------------------------------
It is a go/no-go, and it is cheap. Water is 58 basis functions at cc-pVTZ against 24 at
cc-pVDZ for the geometry, so this should finish in minutes.

What it is really probing is affordability at the top of the ladder. ``_parts`` builds
``cc.CCSD(mf)`` with no frozen core and no density fitting, and never sets ``max_memory``
(PySCF's default is 4000 MB). At the cc-pVQZ that the recommended ``cbs(TZ,QZ)`` tier
requires, a C3-sized organic is 405-520 basis functions and the CCSD(T) intermediates
plausibly do not fit. If that is true, the entire polyatomic validation plan needs a
different protocol -- frozen core, density fitting, or a smaller target tier -- and it is
worth an hour to find that out before committing a session to a multi-hour run that dies.

THE SENTINEL, AND WHY IT IS DELIBERATELY ABSURD
-----------------------------------------------
``_polyatomic_energy`` returns None whenever ``nominal_accuracy_ev`` is not finite, and the
constructor guarantees it is not finite for any polyatomic-capable configuration. That weld
is intentional and this script does not remove it: it sets a probe sentinel on one local
instance so the mechanics can be measured at all.

The sentinel is 999.0 eV -- three orders of magnitude past any physical bar -- precisely so
that it can never be mistaken for a measured uncertainty if it ever escapes into an output.
Producing this measurement is how the real bar eventually gets earned; until then every
number below is UNVALIDATED and this script says so on every line that carries one.

Run:
    OMP_NUM_THREADS=1 python experiments/polyatomic_cost_probe.py --species H2O
"""
from __future__ import annotations

import argparse
import math
import os
import platform
import time

from smartchem.category import Bond, Molecule
from smartchem.data.reference import atomization_energy_ev, polyatomic
from smartchem.oracle.caching import CachingOracle
from smartchem.oracle.persistent import PersistentCache
from smartchem.oracle.pyscf_oracle import PYSCF_AVAILABLE, PySCFOracle

#: An obviously-not-a-real-uncertainty value. If this ever appears in a published estimate,
#: something has leaked and it should be visible from across the room.
PROBE_SENTINEL_EV = 999.0

#: Explicit bond topology per species. ``PolyatomicRef`` carries composition but not
#: connectivity, and the seeder consumes a bond graph -- so the graph is written here,
#: conventionally, rather than inferred by a heuristic that would become a hidden variable.
TOPOLOGY: dict[str, tuple[tuple[str, ...], frozenset]] = {
    "H2O":    (("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)})),
    "NH3":    (("N", "H", "H", "H"),
               frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3)})),
    "CH4":    (("C", "H", "H", "H", "H"),
               frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4)})),
    "CO2":    (("C", "O", "O"), frozenset({Bond(0, 1, 2), Bond(0, 2, 2)})),
    "H2O2":   (("O", "O", "H", "H"),
               frozenset({Bond(0, 1), Bond(0, 2), Bond(1, 3)})),
    "CH3OH":  (("C", "O", "H", "H", "H", "H"),
               frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4), Bond(1, 5)})),
}


def build(formula: str) -> Molecule:
    if formula not in TOPOLOGY:
        raise SystemExit(
            f"no bond topology on file for {formula}. Known: {', '.join(sorted(TOPOLOGY))}. "
            f"Add it to TOPOLOGY explicitly rather than inferring one."
        )
    atoms, bonds = TOPOLOGY[formula]
    molecule = Molecule(atoms, bonds)
    ref = polyatomic(formula)
    if ref is not None:
        # The topology written above must agree with the curated composition, or this
        # script is measuring a different species than the one it compares against.
        from collections import Counter
        if dict(Counter(atoms)) != dict(ref.composition):
            raise SystemExit(
                f"{formula}: TOPOLOGY composition {dict(Counter(atoms))} disagrees with "
                f"reference composition {dict(ref.composition)}"
            )
    return molecule


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--species", default="H2O", help=f"one of {', '.join(sorted(TOPOLOGY))}")
    p.add_argument("--method", default="CCSD(T)")
    p.add_argument("--basis", default="cc-pVTZ")
    p.add_argument("--geometry-tier", default="HF/cc-pVDZ",
                   help="method/basis for seed+relax+Hessian, or 'none' for self")
    p.add_argument("--cache", default=None, metavar="PATH",
                   help="persist species energies here; a rerun then costs almost nothing")
    args = p.parse_args(argv)

    if not PYSCF_AVAILABLE:
        raise SystemExit("this probe needs the backend: pip install 'smartchem[qc]'")

    tier = None
    if args.geometry_tier.lower() != "none":
        if args.geometry_tier.count("/") < 1:
            raise SystemExit("--geometry-tier must look like HF/cc-pVDZ")
        method, _, basis = args.geometry_tier.partition("/")
        tier = (method, basis)

    molecule = build(args.species)
    reference_d0 = atomization_energy_ev(args.species)

    base = PySCFOracle(args.method, args.basis, max_atoms=len(molecule.atoms),
                       geometry_tier=tier)
    if math.isfinite(base.nominal_accuracy_ev):
        raise SystemExit(
            "this configuration already carries a finite accuracy bar -- the weld this "
            "probe exists to measure around is gone, so re-read the constructor before "
            "trusting anything below"
        )
    base.nominal_accuracy_ev = PROBE_SENTINEL_EV
    if base._geom_oracle is not None:
        base._geom_oracle.nominal_accuracy_ev = PROBE_SENTINEL_EV

    oracle = CachingOracle(base)
    if args.cache:
        oracle = PersistentCache(oracle, args.cache)

    print("=" * 78)
    print("POLYATOMIC COST PROBE -- every number below is UNVALIDATED")
    print("=" * 78)
    print(f"  species          : {args.species}  ({len(molecule.atoms)} atoms)")
    print(f"  energy tier      : {args.method}/{args.basis}")
    print(f"  geometry tier    : {args.geometry_tier}")
    print(f"  machine          : {platform.processor() or platform.machine()}, "
          f"{os.cpu_count()} cpus, OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS', 'unset')}")
    try:
        print(f"  load average     : {', '.join(f'{x:.2f}' for x in os.getloadavg())}"
              f"   (a timing from a contended box is fiction)")
    except OSError:
        pass
    print(f"  reference D0     : "
          + ("not tabulated" if reference_d0 is None else f"{reference_d0:.4f} eV"))
    print()
    print("  running. A relaxation prints nothing while it works; see the module logger.")

    t0 = time.perf_counter()
    estimate = oracle.atomization_energy(molecule)
    wall = time.perf_counter() - t0

    print()
    print(f"  wall clock       : {wall:.1f} s")
    if estimate is None:
        print("  RESULT           : DECLINED -- the pipeline refused somewhere.")
        print("                     Not a failure of the probe: a decline is a real result.")
        print("                     Re-run with logging.basicConfig(level=logging.INFO) to see where.")
        return 1

    print(f"  predicted D0     : {estimate.value_ev:.4f} eV   [UNVALIDATED]")
    if reference_d0 is not None:
        error = estimate.value_ev - reference_d0
        print(f"  experiment D0    : {reference_d0:.4f} eV")
        print(f"  error            : {error:+.4f} eV  ({error * 23.060548:+.2f} kcal/mol)")
        print("                     n=1. This is a data point, not an MAE, and one species")
        print("                     cannot establish a validation profile for a protocol.")
    print(f"  systematic       : {estimate.systematic_ev:+.4f} eV")
    for source, value in estimate.systematic_terms:
        print(f"      {source:52} {value:+.4f} eV")
    print(f"  notes            : {estimate.notes}")
    print()
    print("  reminder: uncertainty_ev on this estimate is the 999.0 eV probe sentinel,")
    print("  not a measured bar. The public oracle still declines this species, correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
