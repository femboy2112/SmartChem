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
#:
#: THE FIRST SIX ARE THE TRAINING PROFILE. THE REST ARE THE HOLDOUT.
#: ----------------------------------------------------------------
#: H2O, NH3, CH4, CO2, H2O2 and CH3OH are the six that
#: ``RESULTS_polyatomic_cost.md`` measured at cc-pVTZ and at cbs(TZ,QZ). Every claim in
#: that file was fitted-or-inspected on them, so no number computed for them can validate
#: anything. The nine below have curated thermochemistry in ``POLYATOMIC_REFS`` and have
#: NEVER been computed by anything in this repository -- no prediction, no timing, no
#: inspection of a residual. That is what makes them a holdout for THIS protocol,
#: independently of the ``split`` labels in ``reference.py``, which its own header
#: (lines 20-24) says are no longer pristine.
#:
#: WHY C3H7OH IS ABSENT, AND WHY THAT IS NOT AN OVERSIGHT
#: ------------------------------------------------------
#: ``POLYATOMIC_REFS`` carries ``C3H7OH`` with composition {C:3, H:8, O:1} and a value from
#: ATcT 1.202. That label does not determine a molecule. Propan-1-ol and propan-2-ol are
#: both C3H8O, both stable, and their formation enthalpies differ by more than this
#: protocol's entire error budget -- so guessing which one the row means would silently
#: compare a computed number against the wrong experiment. Every other formula here either
#: has exactly one stable isomer (N2H4, C2H6, CH2O, C3H8) or is written as an explicit
#: connectivity string (CH3OCH3, CH3NH2, CH3OC2H5, HCOOH, C2H5OH -- the last disambiguated
#: by CH3OCH3 being tabulated separately). ``C3H7OH`` is neither, and no field in
#: ``PolyatomicRef`` records structure. Declining is the same rule the oracles follow.
TOPOLOGY: dict[str, tuple[tuple[str, ...], frozenset]] = {
    # -- the six the profile was measured on -------------------------------------------
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

    # -- the holdout: tabulated, never computed ----------------------------------------
    # formaldehyde, H2C=O -- the only C=O double bond outside CO2, and the cheapest
    # holdout species at 170 basis functions in cc-pVQZ.
    "CH2O":     (("C", "O", "H", "H"),
                 frozenset({Bond(0, 1, 2), Bond(0, 2), Bond(0, 3)})),
    # hydrazine, H2N-NH2 -- the N-N single-bond analogue of H2O2, and therefore the one
    # species that can say whether H2O2's outlier status is about peroxide or about a
    # skewed heavy-atom single bond in general.
    "N2H4":     (("N", "N", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3),
                            Bond(1, 4), Bond(1, 5)})),
    # formic acid, H-C(=O)-O-H: carbonyl O at 1, hydroxyl O at 2.
    "HCOOH":    (("C", "O", "O", "H", "H"),
                 frozenset({Bond(0, 1, 2), Bond(0, 2), Bond(0, 3), Bond(2, 4)})),
    # methylamine, CH3-NH2.
    "CH3NH2":   (("C", "N", "H", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4),
                            Bond(1, 5), Bond(1, 6)})),
    # ethane, H3C-CH3.
    "C2H6":     (("C", "C", "H", "H", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1),
                            Bond(0, 2), Bond(0, 3), Bond(0, 4),
                            Bond(1, 5), Bond(1, 6), Bond(1, 7)})),
    # ethanol, CH3-CH2-OH: C0 methyl, C1 methylene, O2 hydroxyl.
    "C2H5OH":   (("C", "C", "O", "H", "H", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1), Bond(1, 2),
                            Bond(0, 3), Bond(0, 4), Bond(0, 5),
                            Bond(1, 6), Bond(1, 7), Bond(2, 8)})),
    # dimethyl ether, CH3-O-CH3 -- constitutional isomer of ethanol, which is why both
    # are tabulated and why neither label is ambiguous.
    "CH3OCH3":  (("C", "O", "C", "H", "H", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1), Bond(1, 2),
                            Bond(0, 3), Bond(0, 4), Bond(0, 5),
                            Bond(2, 6), Bond(2, 7), Bond(2, 8)})),
    # propane, CH3-CH2-CH3.
    "C3H8":     (("C", "C", "C", "H", "H", "H", "H", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1), Bond(1, 2),
                            Bond(0, 3), Bond(0, 4), Bond(0, 5),
                            Bond(1, 6), Bond(1, 7),
                            Bond(2, 8), Bond(2, 9), Bond(2, 10)})),
    # methyl ethyl ether, CH3-O-CH2-CH3.
    "CH3OC2H5": (("C", "O", "C", "C", "H", "H", "H", "H", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1), Bond(1, 2), Bond(2, 3),
                            Bond(0, 4), Bond(0, 5), Bond(0, 6),
                            Bond(2, 7), Bond(2, 8),
                            Bond(3, 9), Bond(3, 10), Bond(3, 11)})),
}

#: The six the accuracy profile in ``RESULTS_polyatomic_cost.md`` was measured on. Named
#: explicitly so "holdout" is a set difference against a written roster rather than a
#: recollection -- the same discipline ``ZPE_BIAS_TRAIN_SPECIES`` exists to enforce.
PROFILE_SPECIES: tuple[str, ...] = ("H2O", "NH3", "CH4", "CO2", "H2O2", "CH3OH")

#: Everything with a bond graph that the profile was not measured on.
HOLDOUT_SPECIES: tuple[str, ...] = tuple(
    formula for formula in TOPOLOGY if formula not in PROFILE_SPECIES
)


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
            "this configuration already carries a finite accuracy bar. Since 2026-07-26 "
            "that no longer means the constructor was edited: it means somebody put a "
            "measured entry in _RELAXED_GEOMETRY_MAE for this exact protocol. If that is "
            "real, this probe's sentinel is obsolete for it and the public oracle should "
            "be measured directly instead. Re-read the table before trusting anything below."
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
