"""
Partition ``CCSD.ao2mo`` into its sub-phases and read the budget each one computed.

    OMP_NUM_THREADS=1 python experiments/ao2mo_sizing_probe.py \
        --species CH3OH --basis cc-pVQZ --max-memory 500 --restore-cc-memory

THE ANOMALY THIS EXISTS TO CLOSE (task #19)
--------------------------------------------
``ao_storage_probe.py`` measured three arms at CH3OH/cc-pVQZ and one number did not fit
the model built from them::

    arm A  mf.max_memory stock (4000), cc budget 4000, _eri resident   ao2mo +1.0617 GB
    arm B  mf.max_memory 500,  cc budget 500 inherited, no _eri        ao2mo +1.9238 GB
    arm C  mf.max_memory 500,  cc budget 4000 restored, no _eri        ao2mo +3.3783 GB

``_make_eris_outcore`` (``pyscf/cc/ccsd.py:1559``, ``:1566``) sizes itself as::

    max_memory = max(MEMORYMIN, mycc.max_memory - lib.current_memory()[0])

with ``MEMORYMIN = 2000`` (``ccsd.py:39``). Arm A: ``max(2000, 4000-2800) = 2000``. Arm B:
``max(2000, 500-150) = 2000``. **The formula says A and B get the same budget, and they
are measured 1.81x apart.** A hand-derivation of the three buffers documented at
``ccsd.py:1579-1586`` -- ``buf``, ``buf_prefetch``, ``outbuf`` at ``blksize=174`` -- gives
1.328 GB and matches neither. Two facts, one conclusion: something else is sizing memory,
and no per-phase model of this transform can predict a peak until it is read.

THE SUSPECT, NAMED BEFORE MEASURING SO THE PREDICTION IS FALSIFIABLE
---------------------------------------------------------------------
``ccsd.py``'s ``blksize`` is not the only budget consumer. Line 1568 hands ``max_memory``
to ``ao2mo.outcore.half_e1``, which does its own sizing at ``outcore.py:690``::

    def guess_e1bufsize(max_memory, ioblk_size, nij_pair, nao_pair, comp):
        mem_words = max(1, max_memory * 1e6 / 8)
        iobuf_words = max(int(mem_words//6), IOBUF_WORDS)      # IOBUF_WORDS = 1e8
        ...
        e1buflen = int(mem_words*.66/(comp*(nij_pair*2+nao_pair)))

``IOBUF_WORDS = 1e8`` words is **800 MB, and it enters as a floor, not a ceiling** -- the
same shape as ``MEMORYMIN``, one layer down and never mentioned by the ccsd source. Below
a 4800 MB budget the ``//6`` term loses to it outright, so this buffer is *constant across
arms A and B* while everything reasoned about so far scaled with the budget. And line 1561
hands a separately-computed ``max_memory`` to ``ao2mo.full`` for the vvvv transform, which
runs ``guess_e2bufsize`` on top.

PREDICTION, REGISTERED BEFORE THE RUN
--------------------------------------
If the anomaly is ``guess_e1bufsize``, then ``half_e1``'s exclusive peak delta is roughly
equal in arms A and B despite their different ``mycc.max_memory``, and the *loop* after
``blksize`` is where they diverge. If instead the divergence is in ``half_e1``, the floor
story is wrong and the budget is reaching further down than this docstring claims.

WHAT IS MEASURED, AND HOW
--------------------------
``pyscf.ao2mo.full``, ``pyscf.ao2mo.outcore.half_e1`` and
``pyscf.ao2mo.outcore.guess_e1bufsize`` are wrapped. The first two record the
``max_memory`` they were HANDED -- which is the value ``ccsd.py:1559`` and ``:1566``
computed, read at the boundary rather than inferred -- together with
``lib.current_memory()[0]`` at entry and their exclusive ``ru_maxrss`` delta. The third
records the four numbers it returns. Nothing here is derived from a memory reading; the
budgets come off the call, and the arithmetic is checked against the source formulas
printed alongside.

ONE ARM PER PROCESS. ``ru_maxrss`` is a high-water mark and has exactly one honest reading
per process; this file never loops in-process, for the reason written across
``ao_storage_probe.py``. It does NOT repeat, and that is a stated limitation: this probe
measures ATTRIBUTION (which sub-phase, what budget), not a reproducible peak. The peak
figures it prints are corroboration of ``ao_storage_probe.py``'s replicated ones, not a
replacement for them.

Stops after ``mycc.ao2mo()``, same boundary as ``ao_storage_probe.py``.
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


def _rss_gb() -> float:
    """Live RSS, the gauge PySCF itself budgets against -- NOT the high-water mark."""
    with open("/proc/self/statm") as handle:
        return int(handle.read().split()[1]) * 4096 / 1024.0 ** 3


def _maxrss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 ** 2


def _install_probes(log: list) -> None:
    """
    Wrap the three sizing sites. Every wrapper records at the CALL BOUNDARY.

    The budgets recorded here are the values ``ccsd.py:1559`` and ``:1566`` computed --
    taken as they cross the call, not reconstructed from a memory reading, because the
    memory reading is the quantity under suspicion.
    """
    from pyscf import ao2mo, lib

    real_full = ao2mo.full
    real_half_e1 = ao2mo.outcore.half_e1
    real_guess = ao2mo.outcore.guess_e1bufsize

    def full(mol, mo_coeff, erifile, *args, **kwargs):
        entry_max, entry_rss = _maxrss_gb(), _rss_gb()
        t0 = time.perf_counter()
        out = real_full(mol, mo_coeff, erifile, *args, **kwargs)
        log.append({
            "site": "ao2mo.full (ccsd.py:1561, vvvv)",
            "budget_mb": kwargs.get("max_memory"),
            "live_rss_gb": entry_rss,
            "peak_delta_gb": _maxrss_gb() - entry_max,
            "wall": time.perf_counter() - t0,
        })
        return out

    def half_e1(mol, mo_coeffs, swapfile, intor="int2e", aosym="s4", comp=1,
                max_memory=2000, *args, **kwargs):
        entry_max, entry_rss = _maxrss_gb(), _rss_gb()
        t0 = time.perf_counter()
        out = real_half_e1(mol, mo_coeffs, swapfile, intor, aosym, comp,
                           max_memory, *args, **kwargs)
        log.append({
            "site": "ao2mo.outcore.half_e1 (ccsd.py:1568)",
            "budget_mb": max_memory,
            "live_rss_gb": entry_rss,
            "peak_delta_gb": _maxrss_gb() - entry_max,
            "wall": time.perf_counter() - t0,
        })
        return out

    def guess_e1bufsize(max_memory, ioblk_size, nij_pair, nao_pair, comp):
        e1buflen, mem_words, iobuf_words, ioblk_words = real_guess(
            max_memory, ioblk_size, nij_pair, nao_pair, comp)
        log.append({
            "site": "guess_e1bufsize (outcore.py:690)",
            "budget_mb": max_memory,
            "nij_pair": nij_pair,
            "nao_pair": nao_pair,
            "e1buflen": e1buflen,
            "mem_words": mem_words,
            "iobuf_words": iobuf_words,
            "ioblk_words": ioblk_words,
            # The line the whole task is about: a floor one layer below MEMORYMIN.
            "iobuf_floored": iobuf_words >= 1e8 and int(mem_words // 6) < 1e8,
            "aobuflen": max(int((mem_words - 2 * comp * e1buflen * nij_pair)
                                // (nao_pair * comp)), 160),
        })
        return e1buflen, mem_words, iobuf_words, ioblk_words

    ao2mo.full = full
    ao2mo.outcore.half_e1 = half_e1
    ao2mo.outcore.guess_e1bufsize = guess_e1bufsize
    # ``ccsd.py`` reaches these through the ``ao2mo`` module object at call time, so
    # rebinding the module attribute is enough and no import order matters.
    assert lib is not None


def _one_arm(atom_spec: str, symbols, basis: str, max_memory, restore_cc: bool) -> dict:
    from pyscf import cc, gto, lib, scf

    sizing: list = []
    _install_probes(sizing)

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
        mf.kernel()
        scf_peak = _peak_gb()
        if not mf.converged:
            raise ConvergenceFailure(f"SCF did not converge for {atom_spec} / {basis}")

        eri_built = mf._eri is not None
        eri_gb = (mf._eri.nbytes / 1024.0 ** 3) if eri_built else 0.0

        mycc = cc.CCSD(mf)
        if restore_cc and max_memory is not None:
            mycc.max_memory = stock_memory

        # The two quantities ccsd.py:1559 reads, captured on this side of the call so the
        # arithmetic below can be checked against the source rather than trusted.
        entry_live = lib.current_memory()[0]
        entry_budget = mycc.max_memory

        t0 = time.perf_counter()
        eris = mycc.ao2mo()
        ao2mo_wall = time.perf_counter() - t0
        ao2mo_peak = _peak_gb()
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
        "nocc": mycc.nocc,
        "nmo": mycc.nmo,
        "entry_live_mb": entry_live,
        "entry_budget_mb": entry_budget,
        "scf_gb": scf_peak - base,
        "ao2mo_gb": ao2mo_peak - scf_peak,
        "peak_gb": ao2mo_peak,
        "ao2mo_wall": ao2mo_wall,
        "sizing": sizing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species", required=True)
    parser.add_argument("--basis", default="cc-pVQZ")
    parser.add_argument("--max-memory", type=float, default=None)
    parser.add_argument("--restore-cc-memory", action="store_true")
    args = parser.parse_args(argv)

    molecule, coordinates, source = _geometry(args.species)
    symbols = tuple(molecule.atoms)
    atom_spec = _spec(symbols, coordinates)

    print("=" * 78)
    print("AO2MO SIZING PROBE")
    print("=" * 78)
    print(f"  species          : {args.species}  ({len(symbols)} atoms, {source})")
    print(f"  basis            : {args.basis}")
    print(f"  mf.max_memory    : "
          f"{'stock' if args.max_memory is None else f'{args.max_memory:.0f} MB'}")
    print(f"  cc budget        : "
          f"{'restored to stock' if args.restore_cc_memory else 'inherited from mf'}")
    sys.stdout.flush()

    record = _one_arm(atom_spec, symbols, args.basis,
                      args.max_memory, args.restore_cc_memory)

    print(f"\n  basis functions  : {record['nbf']}  (nocc {record['nocc']}, "
          f"nmo {record['nmo']})")
    print(f"  mf._eri built    : {record['eri_built']}"
          + (f"  ({record['eri_gb']:.4f} GB tensor)" if record["eri_built"] else ""))
    print(f"  eris.vvvv type   : {record['vvvv_kind']}")
    print(f"  E_SCF            : {record['e_tot']:.12f} Ha")
    print(f"  SCF.kernel       : +{record['scf_gb']:.4f} GB")
    print(f"  CCSD.ao2mo       : +{record['ao2mo_gb']:.4f} GB, "
          f"{record['ao2mo_wall']:.1f} s")
    print(f"  peak RSS         : {record['peak_gb']:.4f} GB")

    print(f"\n  -- what ccsd.py:1559 had to work with " + "-" * 34)
    print(f"  mycc.max_memory  : {record['entry_budget_mb']:.1f} MB")
    print(f"  lib.current_memory() at ao2mo entry : {record['entry_live_mb']:.1f} MB")
    print(f"  max(2000, budget - live)            : "
          f"{max(2000.0, record['entry_budget_mb'] - record['entry_live_mb']):.1f} MB")

    print(f"\n  -- sub-phases, exclusive ru_maxrss deltas " + "-" * 30)
    for entry in record["sizing"]:
        if "e1buflen" in entry:
            print(f"  {entry['site']}")
            print(f"      budget handed in : {entry['budget_mb']:.1f} MB "
                  f"({entry['mem_words']:.4g} words)")
            print(f"      nij_pair {entry['nij_pair']}, nao_pair {entry['nao_pair']}")
            print(f"      e1buflen         : {entry['e1buflen']}")
            print(f"      aobuflen         : {entry['aobuflen']}")
            print(f"      iobuf_words      : {entry['iobuf_words']:.4g}"
                  f"  ({entry['iobuf_words'] * 8 / 1e6:.1f} MB)"
                  f"  floored at IOBUF_WORDS: {entry['iobuf_floored']}")
            print(f"      ioblk_words      : {entry['ioblk_words']:.4g}"
                  f"  ({entry['ioblk_words'] * 8 / 1e6:.1f} MB)")
        else:
            budget = entry["budget_mb"]
            print(f"  {entry['site']}")
            print(f"      budget handed in : "
                  + ("None (default)" if budget is None else f"{budget:.1f} MB"))
            print(f"      live RSS at entry: {entry['live_rss_gb']:.4f} GB")
            print(f"      raised peak by   : +{entry['peak_delta_gb']:.4f} GB, "
                  f"{entry['wall']:.1f} s")

    # The ccsd.py:1573 blksize, recomputed here from the budget half_e1 was handed, so the
    # documented formula and the second path can be compared on one line each.
    handed = [e for e in record["sizing"] if e["site"].startswith("ao2mo.outcore.half_e1")]
    if handed:
        mm = handed[0]["budget_mb"]
        nao = record["nbf"]
        nao_pair = nao * (nao + 1) // 2
        nmo, nocc = record["nmo"], record["nocc"]
        blksize = int(min(8e9, mm * .5e6) / 8 / (nao_pair + nmo ** 2) / nocc)
        blksize = min(nmo, max(4, blksize))
        buf = blksize * nocc * nao_pair * 8 / 1024 ** 3
        outbuf = blksize * nocc * nmo ** 2 * 8 / 1024 ** 3
        print(f"\n  -- ccsd.py:1573 blksize, from that same budget " + "-" * 25)
        print(f"      blksize          : {blksize}")
        print(f"      buf + buf_prefetch + outbuf : "
              f"{2 * buf + outbuf:.4f} GB  ({buf:.4f} x2 + {outbuf:.4f})")

    tag = "stock" if args.max_memory is None else f"{args.max_memory:.0f}MB"
    if args.restore_cc_memory:
        tag += "+ccstock"
    parts = " ".join(
        f"{e['site'].split()[0]}={e['peak_delta_gb']:.4f}/{e['budget_mb']}"
        for e in record["sizing"] if "peak_delta_gb" in e)
    print(f"SIZING_RESULT {args.species} {args.basis} {tag} "
          f"ao2mo={record['ao2mo_gb']:.4f} peak={record['peak_gb']:.4f} "
          f"entry_live={record['entry_live_mb']:.1f} {parts} "
          f"etot={record['e_tot']:.12f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
