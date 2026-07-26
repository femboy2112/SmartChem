#!/usr/bin/env python
"""
Where does CCSD(T) run out of memory, and does the obvious remedy fix it?

THE QUESTION
------------
``_parts`` in the PySCF oracle builds ``cc.CCSD(mf)`` with no frozen core, no density
fitting, and never sets ``max_memory`` (PySCF's default is 4000 MB). The polyatomic cost
probe measured cc-pVTZ and cbs(TZ,QZ) at 3-6 atoms and found them cheap. The open question
it could not answer is whether the same protocol survives at C3 size, where the recommended
``cbs(TZ,QZ)`` tier needs a cc-pVQZ single point on a 405-basis-function molecule.

Running that to find out costs hours and may simply die. So price it first.

WHY THIS IS A MODEL AND NOT A GUESS
-----------------------------------
Basis-function counts are exact -- they depend only on the elements and the basis, never on
the geometry -- so ``nao`` here is measured, not estimated. What is *modelled* is how many
bytes PySCF then needs, and a model that has never been checked against a real process is
worth nothing. So this script does both:

  * ``--model``  counts nao exactly and applies the storage formulas below, and
  * ``--calibrate``  runs real CCSD on small cases and reports peak RSS, so the model can
    be scored against a number instead of against confidence.

THE STORAGE MODEL
-----------------
For closed-shell RHF-CCSD with ``o`` occupied and ``v`` virtual spatial orbitals, the
arrays that dominate are

    t2          o^2 v^2 * 8 bytes        the doubles amplitudes (several copies live at once)
    ovvv        o v * v(v+1)/2 * 8       integral block
    vvvv        [v(v+1)/2]^2 / 2 * 8     integral block, 4-fold packed

``vvvv`` is quartic in the virtual count and dominates everything else by orders of
magnitude the moment a molecule stops being tiny. That single fact is the whole reason this
script exists, because it predicts something counter-intuitive about the fix.

FROZEN CORE DOES NOT FIX THIS
-----------------------------
Freezing the core removes occupied orbitals: ``o`` drops, ``v`` is untouched (or rises by
one per frozen orbital, depending on convention -- either way it does not fall). Since the
dominant term has no ``o`` in it at all, frozen core cannot reduce the binding constraint.
It is a real speedup on the ``o``-scaling terms and it is nearly useless here.

Density fitting is the remedy that actually applies, because DF-CCSD never forms ``vvvv``.
This script quantifies the gap so that choice is made on a number.

USAGE
-----
    python experiments/basis_size_probe.py --model
    python experiments/basis_size_probe.py --calibrate

Nothing here is a validated result. It is a cost model with a calibration attached.
"""

from __future__ import annotations

import argparse
import resource
import sys
import time

from pyscf import cc, gto, scf

sys.path.insert(0, ".")

from smartchem.data.reference import POLYATOMIC_REFS  # noqa: E402

BASES = ("cc-pVDZ", "cc-pVTZ", "cc-pVQZ")

# Enough of a geometry to build a Mole. Basis-function counts do not depend on positions,
# so a linear chain at 2 Angstrom is not an approximation -- it is irrelevant to the count.
# It IS irrelevant only for counting; never reuse this stub for an energy.
_STUB_SPACING = 2.0


def _stub_atoms(composition: dict[str, int]) -> list[tuple[str, tuple[float, float, float]]]:
    atoms: list[tuple[str, tuple[float, float, float]]] = []
    i = 0
    for symbol, count in composition.items():
        for _ in range(count):
            atoms.append((symbol, (i * _STUB_SPACING, 0.0, 0.0)))
            i += 1
    return atoms


def count(composition: dict[str, int], basis: str) -> tuple[int, int, int]:
    """Return (nao, n_occupied, n_virtual) for a closed-shell molecule. Exact."""
    mol = gto.M(atom=_stub_atoms(composition), basis=basis, spin=0, verbose=0)
    nao = mol.nao_nr()
    n_occ = mol.nelectron // 2
    return nao, n_occ, nao - n_occ


def storage_bytes(n_occ: int, n_virt: int) -> dict[str, float]:
    o, v = float(n_occ), float(n_virt)
    vpair = v * (v + 1.0) / 2.0
    return {
        "t2": o * o * v * v * 8.0,
        "ovvv": o * v * vpair * 8.0,
        "vvvv": vpair * vpair / 2.0 * 8.0,
    }


def _gb(n_bytes: float) -> float:
    return n_bytes / (1024.0**3)


def run_model() -> None:
    print(f"{'species':<10} {'basis':<9} {'nao':>5} {'occ':>4} {'virt':>5} "
          f"{'t2 GB':>8} {'ovvv GB':>9} {'vvvv GB':>10} {'total GB':>9}")
    print("-" * 82)
    for ref in POLYATOMIC_REFS:
        for basis in BASES:
            nao, n_occ, n_virt = count(ref.composition, basis)
            s = storage_bytes(n_occ, n_virt)
            total = sum(s.values())
            print(f"{ref.formula:<10} {basis:<9} {nao:>5} {n_occ:>4} {n_virt:>5} "
                  f"{_gb(s['t2']):>8.3f} {_gb(s['ovvv']):>9.3f} "
                  f"{_gb(s['vvvv']):>10.3f} {_gb(total):>9.3f}")
        print()

    print("Frozen-core counterfactual: freeze one 1s per non-hydrogen, v unchanged.")
    print(f"{'species':<10} {'basis':<9} {'occ':>4} {'-> fc':>6} "
          f"{'t2 GB':>8} {'-> fc GB':>10} {'vvvv GB':>10} {'-> fc GB':>10}")
    print("-" * 76)
    for ref in POLYATOMIC_REFS:
        if ref.formula not in ("C3H8", "CH3OC2H5", "C3H7OH"):
            continue
        n_core = sum(c for sym, c in ref.composition.items() if sym != "H")
        for basis in ("cc-pVTZ", "cc-pVQZ"):
            nao, n_occ, n_virt = count(ref.composition, basis)
            full = storage_bytes(n_occ, n_virt)
            froz = storage_bytes(n_occ - n_core, n_virt)
            print(f"{ref.formula:<10} {basis:<9} {n_occ:>4} {n_occ - n_core:>6} "
                  f"{_gb(full['t2']):>8.3f} {_gb(froz['t2']):>10.3f} "
                  f"{_gb(full['vvvv']):>10.3f} {_gb(froz['vvvv']):>10.3f}")


def _peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0**2)


def run_calibrate(cases: list[tuple[str, str]]) -> None:
    """Run real CCSD on small cases and report peak RSS against the model.

    A model of memory that has never been compared to a process is a story. These cases are
    chosen small on purpose: the point is to score the v^4 scaling law, not to be impressive.
    """
    print(f"{'case':<18} {'nao':>5} {'occ':>4} {'virt':>5} "
          f"{'model GB':>9} {'peak RSS GB':>12} {'ratio':>7} {'wall s':>8}")
    print("-" * 76)
    baseline = _peak_rss_gb()
    for formula, basis in cases:
        ref = next((r for r in POLYATOMIC_REFS if r.formula == formula), None)
        if ref is None:
            print(f"{formula:<18} no reference row; skipped")
            continue
        nao, n_occ, n_virt = count(ref.composition, basis)
        model = _gb(sum(storage_bytes(n_occ, n_virt).values()))
        # Real geometry is irrelevant to memory but a stub geometry can make SCF diverge, so
        # spread the atoms far enough that the guess converges. This is a MEMORY probe; the
        # energies it produces are meaningless and are deliberately not printed.
        mol = gto.M(atom=_stub_atoms(ref.composition), basis=basis, spin=0, verbose=0)
        t0 = time.time()
        mf = scf.RHF(mol).run()
        cc.CCSD(mf).run()
        wall = time.time() - t0
        peak = _peak_rss_gb()
        ratio = peak / model if model > 0 else float("nan")
        print(f"{formula + '/' + basis:<18} {nao:>5} {n_occ:>4} {n_virt:>5} "
              f"{model:>9.3f} {peak:>12.3f} {ratio:>7.2f} {wall:>8.1f}")
    print(f"\nprocess baseline RSS before any case: {baseline:.3f} GB")
    print("peak RSS is process-cumulative, so each row includes every earlier row's high-water mark.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", action="store_true", help="count nao and apply the storage model")
    p.add_argument("--calibrate", action="store_true", help="run real CCSD and measure peak RSS")
    args = p.parse_args()
    if not args.model and not args.calibrate:
        p.error("pick --model, --calibrate, or both")
    if args.model:
        run_model()
    if args.calibrate:
        print()
        run_calibrate([("H2O", "cc-pVDZ"), ("H2O", "cc-pVTZ"), ("H2O", "cc-pVQZ")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
