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

TASK #20: IS A ``ru_maxrss`` DELTA AN ALLOCATION?
--------------------------------------------------
Task #19 closed by measuring, and left one number unexplained. Arms A and B are handed
**exactly the same 2000.0 MB** at ``ccsd.py:1561`` -- both floored at ``MEMORYMIN`` -- and
``ao2mo.full``'s exclusive peak delta still came out 2.45x apart (+0.7663 vs +1.8784 GB).
Identical budget, identical molecule, identical basis, different number. So the difference
is not a sizing decision at all, and every per-phase memory model in this repository is
built on ``ru_maxrss`` deltas.

THE MECHANISM, STATED AS ARITHMETIC RATHER THAN AS A STORY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``ru_maxrss`` is a HIGH-WATER MARK. If an earlier phase pushed it above the level RSS has
since fallen back to, the next phase can allocate into that gap and raise the mark by
nothing at all. Call that gap the HEADROOM::

    headroom = maxrss_at_entry - live_rss_at_entry

Arm A enters ``ao2mo`` with a 2.63 GB ``_eri`` resident and an SCF that transiently went
higher still; arm B enters at 155.9 MB having built no ``_eri``. If the peak delta is
under-reporting by the headroom, then it is not measuring the allocation, and the honest
additive quantity is the LIVE RSS delta -- which needs no high-water mark and therefore
has no one-reading-per-process limit either.

PREDICTIONS, REGISTERED BEFORE THE RUN
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
P1 (the identity, and the sharp one). At every wrapped site::

        peak_delta == max(0, live_rss_at_exit - maxrss_at_entry)

    to within a few MB. If RSS grows monotonically through the call, the new mark is
    ``max(old_mark, rss_exit)`` and nothing else. Refuted if any site's residual exceeds
    ~0.05 GB -- which would mean RSS peaked mid-call and fell back before exit, i.e. the
    live reading has its own blind spot and neither instrument is additive.

P2 (the consequence that matters). ``ao2mo.full``'s LIVE RSS delta is approximately equal
    in arms A and B, because both are handed exactly 2000.0 MB. Refuted if they differ by
    more than ~15%, which would mean a second mechanism really is sizing those buffers and
    #19's closure named the site but not the cause.

P3 (the direct observable). ``ru_minflt`` delta x 4096 bytes tracks the live RSS delta at
    each site, confirming the growth is first-touch page faulting rather than accounting.
    This one is corroboration, not a discriminator: it can agree while P1 fails.

``ru_minflt`` is a monotonically increasing COUNTER, not a high-water mark, so unlike
``ru_maxrss`` its deltas are honestly additive over a partition of the timeline.
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


def _minflt() -> int:
    """
    Minor page faults so far: a monotone COUNTER, not a high-water mark.

    This is the distinction task #20 exists to test. ``ru_maxrss`` deltas are only
    additive when no earlier phase left headroom under the mark; a fault count has no
    such caveat, because a page can only be first-touched once.
    """
    return resource.getrusage(resource.RUSAGE_SELF).ru_minflt


def _gauges() -> tuple[float, float, int]:
    """(high-water mark, live RSS, minor faults) -- read as close together as possible."""
    return _maxrss_gb(), _rss_gb(), _minflt()


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

    def _record(site: str, budget, entry: tuple[float, float, int], wall: float) -> dict:
        """
        Both instruments, read at both boundaries, plus P1's residual.

        ``peak_delta_gb`` is the number every earlier probe in this repository reported.
        ``live_delta_gb`` is the same call measured by a gauge with no memory of the past.
        ``p1_residual_gb`` is what task #20 registered as its discriminator: if the peak
        delta is nothing more than the live level breaching an OLD mark, this is zero.
        """
        entry_max, entry_rss, entry_flt = entry
        exit_max, exit_rss, exit_flt = _gauges()
        return {
            "site": site,
            "budget_mb": budget,
            "live_rss_gb": entry_rss,
            "exit_rss_gb": exit_rss,
            "maxrss_entry_gb": entry_max,
            # Space under the existing high-water mark, free to allocate into unseen.
            "headroom_gb": entry_max - entry_rss,
            "peak_delta_gb": exit_max - entry_max,
            "live_delta_gb": exit_rss - entry_rss,
            "minflt_delta": exit_flt - entry_flt,
            "minflt_gb": (exit_flt - entry_flt) * 4096 / 1024.0 ** 3,
            "p1_residual_gb": (exit_max - entry_max) - max(0.0, exit_rss - entry_max),
            "wall": wall,
        }

    def full(mol, mo_coeff, erifile, *args, **kwargs):
        entry = _gauges()
        t0 = time.perf_counter()
        out = real_full(mol, mo_coeff, erifile, *args, **kwargs)
        log.append(_record("ao2mo.full (ccsd.py:1561, vvvv)", kwargs.get("max_memory"),
                           entry, time.perf_counter() - t0))
        return out

    def half_e1(mol, mo_coeffs, swapfile, intor="int2e", aosym="s4", comp=1,
                max_memory=2000, *args, **kwargs):
        entry = _gauges()
        t0 = time.perf_counter()
        out = real_half_e1(mol, mo_coeffs, swapfile, intor, aosym, comp,
                           max_memory, *args, **kwargs)
        log.append(_record("ao2mo.outcore.half_e1 (ccsd.py:1568)", max_memory,
                           entry, time.perf_counter() - t0))
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

        arm_max, arm_rss, arm_flt = _gauges()
        t0 = time.perf_counter()
        eris = mycc.ao2mo()
        ao2mo_wall = time.perf_counter() - t0
        exit_max, exit_rss, exit_flt = _gauges()
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
        # Task #20: the whole ao2mo() call read by both instruments, so the sub-phase
        # records below can be checked for additivity against their own container.
        "arm_headroom_gb": arm_max - arm_rss,
        "arm_entry_rss_gb": arm_rss,
        "arm_exit_rss_gb": exit_rss,
        "arm_live_delta_gb": exit_rss - arm_rss,
        "arm_peak_delta_gb": exit_max - arm_max,
        "arm_minflt_delta": exit_flt - arm_flt,
        "arm_p1_residual_gb": (exit_max - arm_max) - max(0.0, exit_rss - arm_max),
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
            print(f"      live RSS         : {entry['live_rss_gb']:.4f} -> "
                  f"{entry['exit_rss_gb']:.4f} GB")
            print(f"      headroom at entry: {entry['headroom_gb']:.4f} GB "
                  f"(mark {entry['maxrss_entry_gb']:.4f} above live)")
            print(f"      raised peak by   : +{entry['peak_delta_gb']:.4f} GB, "
                  f"{entry['wall']:.1f} s")
            print(f"      live RSS grew by : +{entry['live_delta_gb']:.4f} GB   "
                  f"<- the additive one")
            print(f"      minor faults     : {entry['minflt_delta']:,} "
                  f"({entry['minflt_gb']:.4f} GB of first-touched pages)")
            print(f"      P1 residual      : {entry['p1_residual_gb']:+.4f} GB "
                  f"({'HOLDS' if abs(entry['p1_residual_gb']) <= 0.05 else 'REFUTED'} "
                  f"at the 0.05 GB threshold registered in the docstring)")

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

    print(f"\n  -- task #20: the whole ao2mo() call, both instruments " + "-" * 17)
    print(f"      headroom at entry: {record['arm_headroom_gb']:.4f} GB")
    print(f"      live RSS         : {record['arm_entry_rss_gb']:.4f} -> "
          f"{record['arm_exit_rss_gb']:.4f} GB")
    print(f"      peak delta       : +{record['arm_peak_delta_gb']:.4f} GB")
    print(f"      live delta       : +{record['arm_live_delta_gb']:.4f} GB")
    print(f"      minor faults     : {record['arm_minflt_delta']:,}")
    print(f"      P1 residual      : {record['arm_p1_residual_gb']:+.4f} GB "
          f"({'HOLDS' if abs(record['arm_p1_residual_gb']) <= 0.05 else 'REFUTED'})")

    tag = "stock" if args.max_memory is None else f"{args.max_memory:.0f}MB"
    if args.restore_cc_memory:
        tag += "+ccstock"
    parts = " ".join(
        f"{e['site'].split()[0]}={e['peak_delta_gb']:.4f}/{e['budget_mb']}"
        f"/live={e['live_delta_gb']:.4f}/head={e['headroom_gb']:.4f}"
        f"/flt={e['minflt_delta']}/p1={e['p1_residual_gb']:+.4f}"
        for e in record["sizing"] if "peak_delta_gb" in e)
    print(f"SIZING_RESULT {args.species} {args.basis} {tag} "
          f"ao2mo={record['ao2mo_gb']:.4f} peak={record['peak_gb']:.4f} "
          f"entry_live={record['entry_live_mb']:.1f} "
          f"arm_head={record['arm_headroom_gb']:.4f} "
          f"arm_live={record['arm_live_delta_gb']:.4f} "
          f"arm_p1={record['arm_p1_residual_gb']:+.4f} {parts} "
          f"etot={record['e_tot']:.12f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
