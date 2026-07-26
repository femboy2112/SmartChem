"""
Price the incore AO integral tensor, the thing that actually owns the cc-pVQZ peak.

    OMP_NUM_THREADS=1 python experiments/ao_storage_probe.py \
        --species CH3OH --basis cc-pVQZ --max-memory 500

One arm per process. ``ru_maxrss`` is a process-wide high-water mark, so two arms in one
invocation would report the larger of them twice and neither honestly.

WHY THIS LEVER AND NOT ``direct_scf``
--------------------------------------
Three probes chased the CCSD(T) peak through ``vvvv``, the triples, and ``mycc.direct``,
and all three were aimed at the coupled-cluster layer. At cc-pVQZ the coupled-cluster
layer does not set the mark: ``SCF.kernel`` does, at +2.2763 GB of a 4.6580 GB peak
(``ccsd_peak_phase_probe.py``, CH3OH/cc-pVQZ/conventional). The arithmetic is the incore
AO integral tensor, ``nao**4 / 8`` doubles -- 2.8 GB at 230 basis functions.

``mf.direct_scf`` is NOT the switch, and this file exists partly to stop that being filed
a third time. ``RHF.get_jk`` (``pyscf/scf/hf.py:2504-2508``) decides incore-versus-direct
on memory headroom alone and never reads ``direct_scf``; that flag only reaches the base
class ``SCF.get_jk``, which is the branch not taken. The literal gate is ``_is_mem_enough``
(``hf.py:2248-2250``)::

    nbf**4/1e6 + lib.current_memory()[0] < self.max_memory * .95

At 230 basis functions that is 2798.41 MB against the stock 4000 MB budget, so
``mol.intor('int2e', aosym='s8')`` fires and is cached on ``mf._eri``. This repository sets
``max_memory``, ``direct_scf``, ``density_fit`` and ``incore_anyway`` nowhere, so the
2.28 GB is stock PySCF and the lever is ``mf.max_memory``.

THE OBSERVABLE IS THE BRANCH, NOT THE MEMORY
---------------------------------------------
``mf._eri is not None`` after the SCF says *directly* which branch fired. That matters more
than it looks: every earlier attempt at this question inferred the branch from the memory
reading, and a memory reading is exactly the quantity now known to be unreliable (below).
Reading the branch off the object and the memory off ``ru_maxrss`` gives two independent
observables for one claim.

THE NOISE FLOOR, MEASURED, AND WHY THIS PROBE REPEATS
------------------------------------------------------
``ccsd_acceleration_probe.py`` measured CH3OH/cc-pVQZ/direct twice and got **4.8924 GB and
4.3164 GB** -- the same instrument, the same species, the same basis, the same route, the
same energy to every printed digit, and a 13.3% spread in peak RSS. That spread is larger
than every effect those probes were being used to detect, and it is why the "``direct``
raises the peak 3.5%" result that launched this whole hunt was an artifact.

So: ``--repeat`` defaults to 2, and it spawns a SUBPROCESS per run rather than looping --
see the comment at the loop, which is where the first version of this file got it wrong.
A single-run peak-RSS number from this box is not evidence.

AND THE READING THAT DOES NOT DEPEND ON ANY OF THAT
----------------------------------------------------
``mf._eri.nbytes`` is the AO integral tensor's size, exactly, taken from the array itself.
Measured at CH3OH/cc-pVQZ: **2.6290 GB**. It needs no high-water mark, no baseline, and no
repeats, and it is the number this task was actually asking for. The RSS columns are
corroboration; this is the measurement.

WHAT IS AND IS NOT ISOLATED
----------------------------
``cc.CCSD(mf)`` inherits ``max_memory`` from the mean field, so lowering it for the SCF
also constrains ``ao2mo``'s blocking. That is a genuine confound and it is not hidden:
``--restore-cc-memory`` puts the stock budget back on the CC object so the SCF's incore
decision is the only thing that changed. Run both. The unrestored arm is what a user who
sets ``max_memory`` actually gets; the restored arm is what the SCF alone costs.

NOT IDENTITY-PRESERVING, AND THE PROBE MEASURES THE DIFFERENCE RATHER THAN ASSUMING IT
---------------------------------------------------------------------------------------
The direct path applies Schwarz screening at ``direct_scf_tol`` (1e-13 by default) that the
incore path does not, so ``mf.e_tot`` is not required to be bit-identical between arms. The
size of that difference is a deliverable, not a nuisance: it is what separates "free memory
win" from "measured tradeoff". The stock arm's repeats ARE required to be bit-identical to
each other, and a failure there means the run is not deterministic and no arm comparison
means anything.

Stops after ``mycc.ao2mo()``. The amplitude iterations and the triples were both measured
at exactly +0.0000 GB of peak at cc-pVQZ, so running them would cost ~24 minutes per arm to
re-measure two zeros.
"""
from __future__ import annotations

import argparse
import resource
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smartchem.oracle.pyscf_oracle import (                                # noqa: E402
    ConvergenceFailure,
    resolve_basis,
)

from ccsd_acceleration_probe import _geometry, _peak_gb, _spec             # noqa: E402


def _one_arm(atom_spec: str, symbols, basis: str, max_memory, restore_cc: bool) -> dict:
    """
    One SCF plus one integral transformation, with every phase's ru_maxrss delta.

    ``ru_maxrss`` is monotone, so ``maxrss(exit) - maxrss(enter)`` is exactly what an
    interval added to the high-water mark, and those deltas are additive over any
    partition of the timeline. A phase whose delta is 0 did not set the peak, with no
    sampling interval for a spike to hide in.
    """
    from pyscf import cc, gto, scf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mol = gto.M(atom=atom_spec, basis=resolve_basis(symbols, basis, False),
                    spin=0, verbose=0, unit="Angstrom")

        stock_memory = mol.max_memory
        mf = scf.RHF(mol)
        if max_memory is not None:
            mf.max_memory = max_memory
        mf.conv_tol = 1e-10
        mf.max_cycle = 300

        base = _peak_gb()
        t0 = time.perf_counter()
        mf.kernel()
        scf_wall = time.perf_counter() - t0
        scf_peak = _peak_gb()
        if not mf.converged:
            raise ConvergenceFailure(f"SCF did not converge for {atom_spec} / {basis}")

        # The branch, read off the object rather than inferred from the memory reading.
        eri_built = mf._eri is not None
        eri_gb = (mf._eri.nbytes / 1024.0 ** 3) if eri_built else 0.0

        mycc = cc.CCSD(mf)
        if restore_cc and max_memory is not None:
            mycc.max_memory = stock_memory
        t0 = time.perf_counter()
        eris = mycc.ao2mo()
        ao2mo_wall = time.perf_counter() - t0
        ao2mo_peak = _peak_gb()

        # ``eris`` is held to its own line so the transform's allocation is inside the
        # measured interval rather than freed by an early collection.
        #
        # The TYPE, not a truthiness test. ``eris.vvvv is not None`` is true on both
        # paths -- ``_make_eris_outcore`` creates an h5py dataset where the incore branch
        # creates a numpy array -- so a boolean here would have reported "incore" for the
        # outcore run and been believed, since it agrees with the incore answer whenever
        # the incore answer is right. Measured at H2O/cc-pVDZ: True on both arms.
        vvvv = getattr(eris, "vvvv", None)
        vvvv_kind = "absent" if vvvv is None else type(vvvv).__name__

    return {
        "nbf": mol.nao_nr(),
        "budget_mb": mf.max_memory,
        "cc_budget_mb": mycc.max_memory,
        "eri_built": eri_built,
        "eri_gb": eri_gb,
        "vvvv_kind": vvvv_kind,
        "e_tot": mf.e_tot,
        "scf_gb": scf_peak - base,
        "ao2mo_gb": ao2mo_peak - scf_peak,
        "peak_gb": ao2mo_peak,
        "scf_wall": scf_wall,
        "ao2mo_wall": ao2mo_wall,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species", required=True)
    parser.add_argument("--basis", default="cc-pVQZ")
    parser.add_argument("--max-memory", type=float, default=None,
                        help="mf.max_memory in MB; omit for stock PySCF")
    parser.add_argument("--restore-cc-memory", action="store_true",
                        help="put the stock budget back on the CC object, isolating the "
                             "SCF's incore decision from ao2mo's blocking")
    parser.add_argument("--repeat", type=int, default=2,
                        help="runs per arm; the measured peak-RSS spread is ~13%%, so one "
                             "run is not evidence")
    args = parser.parse_args(argv)

    molecule, coordinates, source = _geometry(args.species)
    symbols = tuple(molecule.atoms)
    atom_spec = _spec(symbols, coordinates)

    print("=" * 78)
    print("AO STORAGE PROBE")
    print("=" * 78)
    print(f"  species          : {args.species}  ({len(symbols)} atoms, {source})")
    print(f"  basis            : {args.basis}")
    print(f"  mf.max_memory    : "
          f"{'stock' if args.max_memory is None else f'{args.max_memory:.0f} MB'}")
    print(f"  cc budget        : "
          f"{'restored to stock' if args.restore_cc_memory else 'inherited from mf'}")
    print(f"  repeats          : {args.repeat}")

    # ONE measured run per process, always -- repeats are subprocesses.
    #
    # This file's own opening paragraph says a process-wide high-water mark cannot report
    # two things honestly, and the first version of --repeat then looped in-process and
    # did exactly that. Measured, CH3OH/cc-pVQZ/stock: run 1 gave SCF +2.6758 GB and a
    # 3.8568 GB peak; run 2 in the same process gave SCF +0.0000 GB and a 4.6010 GB
    # "peak". The zero is the tell -- a 2.6 GB SCF cannot add nothing -- and the 19.30%
    # "spread" between the two was the watermark accumulating, not variance. A monotone
    # instrument has no second reading.
    if args.repeat > 1:
        import subprocess
        base = [sys.executable, __file__, "--species", args.species,
                "--basis", args.basis, "--repeat", "1"]
        if args.max_memory is not None:
            base += ["--max-memory", str(args.max_memory)]
        if args.restore_cc_memory:
            base += ["--restore-cc-memory"]
        for index in range(args.repeat):
            print(f"\n  == subprocess {index + 1} of {args.repeat} " + "=" * 40)
            sys.stdout.flush()
            subprocess.run(base, check=True)
        return 0

    records = []
    for index in range(args.repeat):
        record = _one_arm(atom_spec, symbols, args.basis,
                          args.max_memory, args.restore_cc_memory)
        records.append(record)
        print(f"\n  -- run {index + 1} " + "-" * 60)
        print(f"  basis functions  : {record['nbf']}")
        print(f"  budget seen      : SCF {record['budget_mb']:.0f} MB, "
              f"CC {record['cc_budget_mb']:.0f} MB")
        print(f"  mf._eri built    : {record['eri_built']}"
              + (f"  ({record['eri_gb']:.4f} GB tensor)" if record["eri_built"] else ""))
        print(f"  eris.vvvv type   : {record['vvvv_kind']}")
        print(f"  E_SCF            : {record['e_tot']:.12f} Ha")
        print(f"  SCF.kernel       : +{record['scf_gb']:.4f} GB, "
              f"{record['scf_wall']:.1f} s")
        print(f"  CCSD.ao2mo       : +{record['ao2mo_gb']:.4f} GB, "
              f"{record['ao2mo_wall']:.1f} s")
        print(f"  peak RSS         : {record['peak_gb']:.4f} GB")

    peaks = [r["peak_gb"] for r in records]
    energies = {r["e_tot"] for r in records}
    spread = (max(peaks) - min(peaks)) / min(peaks) * 100.0 if len(peaks) > 1 else 0.0
    print(f"\n  peak spread      : {spread:.2f}% over {len(peaks)} runs "
          f"({min(peaks):.4f} .. {max(peaks):.4f} GB)")
    print(f"  E_SCF reproduced : {'BIT-IDENTICAL' if len(energies) == 1 else 'DIFFERS'}"
          + ("" if len(energies) == 1
             else f"  spread {max(energies) - min(energies):.3e} Ha"))

    tag = "stock" if args.max_memory is None else f"{args.max_memory:.0f}MB"
    if args.restore_cc_memory:
        tag += "+ccstock"
    for record in records:
        print(f"AO_RESULT {args.species} {args.basis} {tag} "
              f"eri={record['eri_built']} peak={record['peak_gb']:.4f} "
              f"scf={record['scf_gb']:.4f} ao2mo={record['ao2mo_gb']:.4f} "
              f"etot={record['e_tot']:.12f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
