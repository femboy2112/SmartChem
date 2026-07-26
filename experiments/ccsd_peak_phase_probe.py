"""
Attribute the CCSD(T) peak RSS to the phase that actually sets it.

    OMP_NUM_THREADS=1 python experiments/ccsd_peak_phase_probe.py \
        --species CH3OH --basis cc-pVTZ --route conventional

WHY THIS EXISTS
---------------
``experiments/basis_size_probe.py`` models CCSD storage and finds ``vvvv`` dominant --
quartic in the virtual count. ``experiments/ccsd_acceleration_probe.py`` then removed
``vvvv`` outright with ``mycc.direct = True`` and measured CH3OH / cc-pVQZ:

    conventional   22.163760672 eV   1334.38 s   4.7263 GB
    direct         22.163760672 eV   1119.42 s   4.8924 GB

Bit-identical, and the peak went UP by 3.5%. Deleting the term the model calls dominant
moved the high-water mark by nothing, so the peak is not set by ``vvvv`` and the model was
being read as a decomposition of a measurement it only bounds from below.

The suspect on file was the triples step. This probe does not test that suspect one route
at a time -- it measures the whole timeline at once, because there is a sharper instrument
available than an on/off comparison.

THE INSTRUMENT: ru_maxrss IS MONOTONE
-------------------------------------
``resource.getrusage(RUSAGE_SELF).ru_maxrss`` is a high-water mark. It never decreases. So
over any interval, ``maxrss(exit) - maxrss(enter)`` is exactly the amount by which that
interval RAISED the peak -- and because a high-water mark is monotone, those increases are
ADDITIVE over any partition of the timeline. Partition the run into nested phases and the
attribution is exact arithmetic, not a sample:

    inclusive(phase) = maxrss at exit - maxrss at entry
    exclusive(phase) = inclusive(phase) - sum(inclusive(direct children))

A phase with ``exclusive == 0`` did not set the peak. Not "probably did not" -- did not.
No sampling interval to miss a spike, because the spike would have moved the high-water
mark and the high-water mark is read at both ends.

A SAMPLED TIMELINE RUNS ALONGSIDE, AND IT ANSWERS A DIFFERENT QUESTION
----------------------------------------------------------------------
``ru_maxrss`` cannot distinguish "this phase allocated 3 GB and freed it" from "this phase
allocated 3 GB and is still holding it". Both leave the same high-water mark. That
difference decides whether the peak is a live requirement or an allocator that never
returned pages, so a daemon thread also samples CURRENT resident size from
``/proc/self/statm``. If current RSS stays pinned at the high-water mark after the phase
that set it, the memory is held or the allocator kept it; if it falls back, the peak was a
genuine transient.

The sampled numbers are secondary and are labelled as such in the output. The load-bearing
measurement is the exclusive ru_maxrss delta, which is exact.

THE INSTRUMENT RULE
-------------------
This probe calls ``ccsd_acceleration_probe._parts`` UNMODIFIED -- it does not re-implement
it a second time. Phase boundaries are recorded by wrappers installed on PySCF's own
methods; each wrapper reads a clock and a counter, calls through to the original, and
returns its value untouched. Nothing numerical is in the wrapper.

That is an argument, not evidence, so the calibration runs with the wrappers ACTIVE: the
free atoms are computed through the instrumented path and through the real
``PySCFOracle._parts``, and bit-identity is REQUIRED before any attribution is believed.
A run that fails calibration prints the residual and exits non-zero. The wrappers being
numerically inert is therefore measured on every single run rather than asserted here.

WHAT THIS PROBE DOES NOT ESTABLISH
----------------------------------
It attributes the peak of ONE run to a phase. It does not establish how that attribution
scales with basis or species -- ``vvvv`` grows quartically in the virtual count while the
triples arrays grow more slowly, so a phase that owns the peak at cc-pVTZ need not own it
at cc-pVQZ. A verdict quoted from one basis and applied to another is exactly the error
this probe exists to correct. Run it at the basis you intend to conclude about.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import resource
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smartchem.oracle.pyscf_oracle import (                                # noqa: E402
    ATOM_SPIN,
    HARTREE_EV,
    PySCFOracle,
)

from ccsd_acceleration_probe import ROUTES, _geometry, _parts, _spec       # noqa: E402

_PAGE = os.sysconf("SC_PAGE_SIZE")


def _maxrss_gb() -> float:
    """Peak resident set so far, in GB. Linux reports ru_maxrss in kilobytes."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0)


def _rss_gb() -> float:
    """CURRENT resident set, in GB. Field 2 of /proc/self/statm is resident pages."""
    with open("/proc/self/statm", "rb") as handle:
        return int(handle.read().split()[1]) * _PAGE / (1024.0 ** 3)


class _Frame:
    __slots__ = ("name", "depth", "t_enter", "t_exit", "rss_enter", "rss_exit",
                 "child_inclusive")

    def __init__(self, name: str, depth: int) -> None:
        self.name = name
        self.depth = depth
        self.t_enter = time.perf_counter()
        self.t_exit = self.t_enter
        self.rss_enter = _maxrss_gb()
        self.rss_exit = self.rss_enter
        self.child_inclusive = 0.0

    @property
    def inclusive(self) -> float:
        return self.rss_exit - self.rss_enter

    @property
    def exclusive(self) -> float:
        return self.inclusive - self.child_inclusive

    @property
    def wall(self) -> float:
        return self.t_exit - self.t_enter


class PhaseRecorder:
    """
    Nested phase timing with exact high-water-mark attribution.

    The stack discipline is what makes ``exclusive`` meaningful: a child's inclusive delta
    is added to its parent's ``child_inclusive`` on exit, so the parent's exclusive share
    is the increase that happened in the parent and in none of its children.
    """

    def __init__(self, echo: bool = True) -> None:
        self.stack: list[_Frame] = []
        self.done: list[_Frame] = []
        self.echo = echo
        self.t_zero = time.perf_counter()

    @contextlib.contextmanager
    def phase(self, name: str):
        frame = _Frame(name, len(self.stack))
        self.stack.append(frame)
        try:
            yield frame
        finally:
            self.stack.pop()
            frame.t_exit = time.perf_counter()
            frame.rss_exit = _maxrss_gb()
            if self.stack:
                self.stack[-1].child_inclusive += frame.inclusive
            self.done.append(frame)
            if self.echo:
                # A cc-pVQZ run is twenty minutes of silence otherwise, which is
                # indistinguishable from a hang. Flushed, because this is usually
                # being tailed from a file.
                print(f"    [{frame.t_exit - self.t_zero:8.1f}s] {'  ' * frame.depth}"
                      f"{frame.name:<26} {frame.wall:8.1f}s "
                      f"peak {frame.exclusive:+.4f} GB  now {_rss_gb():.3f} GB",
                      flush=True)


class RSSSampler:
    """Daemon thread recording CURRENT resident size, so held memory is distinguishable."""

    def __init__(self, interval: float = 0.25) -> None:
        self.interval = interval
        self.samples: list[tuple[float, float]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.samples.append((time.perf_counter(), _rss_gb()))
            self._stop.wait(self.interval)

    def __enter__(self) -> RSSSampler:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def window(self, t0: float, t1: float) -> tuple[float, float, int]:
        """``(min, max, n)`` of current RSS over ``[t0, t1]``; ``(nan, nan, 0)`` if unsampled."""
        inside = [r for t, r in self.samples if t0 <= t <= t1]
        if not inside:
            return float("nan"), float("nan"), 0
        return min(inside), max(inside), len(inside)


#: ``(module attribute path, method name)`` pairs wrapped to mark a phase boundary.
#: Both the closed- and open-shell classes are listed because a molecule runs RHF/RCCSD
#: while its free atoms run UHF/UCCSD, and the atoms must not silently escape the timeline.
_HOOKS = (
    ("pyscf.scf.hf", "SCF", "kernel"),
    ("pyscf.cc.ccsd", "CCSDBase", "kernel"),
    ("pyscf.cc.ccsd", "CCSDBase", "ao2mo"),
    ("pyscf.cc.ccsd", "CCSD", "ccsd_t"),
    ("pyscf.cc.uccsd", "UCCSD", "kernel"),
    ("pyscf.cc.uccsd", "UCCSD", "ao2mo"),
    ("pyscf.cc.uccsd", "UCCSD", "ccsd_t"),
)


def install_hooks(recorder: PhaseRecorder) -> list[tuple[type, str, object]]:
    """
    Wrap PySCF entry points so each one opens and closes a phase.

    The wrapper reads a clock and ``getrusage``, calls the original with the arguments it
    was handed, and returns its result. It does no arithmetic on any array. Calibration in
    ``main`` is what turns that from a claim into a measurement.
    """
    import importlib

    restore: list[tuple[type, str, object]] = []
    for module_name, class_name, method_name in _HOOKS:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name, None)
        if cls is None or method_name not in cls.__dict__:
            print(f"  hook MISSING     : {module_name}.{class_name}.{method_name} "
                  f"-- not defined on that class in this PySCF; timeline will not "
                  f"resolve it")
            continue
        original = cls.__dict__[method_name]
        label = f"{class_name}.{method_name}"

        def make(original=original, label=label):
            def wrapper(self, *args, **kwargs):
                with recorder.phase(label):
                    return original(self, *args, **kwargs)
            wrapper.__name__ = getattr(original, "__name__", label)
            return wrapper

        setattr(cls, method_name, make())
        restore.append((cls, method_name, original))
    return restore


def remove_hooks(restore) -> None:
    for cls, method_name, original in restore:
        setattr(cls, method_name, original)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species", required=True)
    parser.add_argument("--basis", default="cc-pVDZ")
    parser.add_argument("--method", default="CCSD(T)",
                        help="CCSD disables the triples entirely, which is the "
                             "originally filed on/off discriminator")
    parser.add_argument("--route", default="conventional", choices=ROUTES)
    parser.add_argument("--sample-interval", type=float, default=0.25)
    args = parser.parse_args(argv)

    molecule, coordinates, digest = _geometry(args.species)
    symbols = molecule.atoms
    elements = tuple(sorted(set(symbols)))

    print("=" * 78)
    print(f"CCSD PEAK PHASE PROBE -- route={args.route}")
    print("=" * 78)
    print(f"  species          : {args.species}  ({len(symbols)} atoms)")
    print(f"  energy tier      : {args.method}/{args.basis}")
    print(f"  geometry         : HF/cc-pVDZ, sha256[:16]={digest}")
    print(f"  question          : which phase RAISES the high-water mark, and by how much")
    print()

    recorder = PhaseRecorder()
    restore = install_hooks(recorder)
    try:
        with RSSSampler(args.sample_interval) as sampler:
            t_zero = time.perf_counter()

            atoms = {}
            with recorder.phase("SEGMENT free atoms"):
                for element in elements:
                    with recorder.phase(f"atom {element}"):
                        hf, corr = _parts(f"{element} 0 0 0", (element,), args.basis,
                                          ATOM_SPIN[element], args.method, args.route)
                    atoms[element] = hf + corr

            # -- calibration, run WITH the hooks installed, so this measures that the
            #    wrappers are numerically inert rather than assuming it
            oracle = PySCFOracle(args.method, args.basis, max_atoms=len(symbols))
            worst = 0.0
            with recorder.phase("SEGMENT calibration"):
                for element in elements:
                    hf, corr = _parts(f"{element} 0 0 0", (element,), args.basis,
                                      ATOM_SPIN[element], args.method, "conventional")
                    reference = sum(oracle._parts(f"{element} 0 0 0", (element,),
                                                  args.basis, ATOM_SPIN[element]))
                    worst = max(worst, abs((hf + corr) - reference))
            calibrated = worst == 0.0
            print(f"  calibration      : max |instrumented - PySCFOracle._parts| = "
                  f"{worst:.3e} Ha over {len(elements)} free atoms  "
                  f"[{'PASS' if calibrated else 'FAIL'}]")
            if not calibrated:
                print("  ABORTING: the instrumented path no longer reproduces the shipping")
                print("  path bit for bit, so the wrappers are not inert and every")
                print("  attribution below would be measuring the instrument.")
                return 2
            print()

            with recorder.phase("SEGMENT molecule"):
                if len(symbols) == 1:
                    e_mol = atoms[symbols[0]]
                else:
                    hf, corr = _parts(_spec(symbols, coordinates), symbols, args.basis,
                                      0, args.method, args.route)
                    e_mol = hf + corr
    finally:
        remove_hooks(restore)

    d_e = (sum(atoms[s] for s in symbols) - e_mol) * HARTREE_EV
    peak = _maxrss_gb()

    print(f"  D_e (electronic) : {d_e:.6f} eV")
    print(f"  peak RSS         : {peak:.4f} GB   <-- the number being attributed")
    print()

    frames = sorted(recorder.done, key=lambda f: f.t_enter)
    print("  PHASE TIMELINE -- 'raised peak by' is the EXACT increase owed to that phase")
    print("  " + "-" * 74)
    print(f"  {'phase':<34}{'wall s':>9}{'raised peak by':>16}{'held RSS max':>15}")
    print("  " + "-" * 74)
    for frame in frames:
        _lo, hi, n = sampler.window(frame.t_enter, frame.t_exit)
        held = f"{hi:.3f} GB" if n else "unsampled"
        indent = "  " + "  " * frame.depth
        name = f"{indent}{frame.name}"[:34]
        print(f"  {name:<34}{frame.wall:>9.1f}{frame.exclusive:>13.4f} GB{held:>15}")
    print("  " + "-" * 74)

    charged = [f for f in frames if f.exclusive > 0.0005]
    charged.sort(key=lambda f: -f.exclusive)
    print()
    if not charged:
        print("  NO PHASE raised the peak by a measurable amount, which means the peak")
        print("  was already set before the first instrumented boundary -- most likely")
        print("  by the interpreter, the imports, or geometry relaxation. Re-run with a")
        print("  larger basis before concluding anything about CCSD.")
    else:
        owner = charged[0]
        share = 100.0 * owner.exclusive / peak if peak else float("nan")
        print(f"  VERDICT: the peak is set by  {owner.name}")
        print(f"           it raised the high-water mark by {owner.exclusive:.4f} GB, "
              f"{share:.1f}% of the {peak:.4f} GB peak")
        print()
        print("  full ranking of phases that raised the peak:")
        for frame in charged:
            print(f"    {frame.exclusive:8.4f} GB  {frame.name}")
        # Group by name before declaring anything innocent. A phase name occurs once per
        # invocation -- once per free atom, once for the molecule -- and one invocation
        # raising nothing says nothing about the others. Only a name whose LARGEST
        # exclusive delta over every invocation is zero has been exonerated.
        worst_by_name: dict[str, float] = {}
        for frame in frames:
            if frame.name.startswith(("CCSD", "UCCSD", "SCF")):
                worst_by_name[frame.name] = max(worst_by_name.get(frame.name, 0.0),
                                                frame.exclusive)
        zero = sorted(n for n, worst in worst_by_name.items() if worst <= 0.0005)
        if zero:
            print()
            print("  phases that raised the peak by NOTHING on ANY invocation")
            print("  (exact, not approximate -- a high-water mark cannot hide a spike):")
            for name in zero:
                print(f"      {name}")

    print()
    print("  This attributes ONE run at ONE basis. vvvv grows quartically in the virtual")
    print("  count and the triples arrays do not, so the owner of the peak can change")
    print("  with basis. Do not carry this verdict to a basis it was not measured at.")
    owner_name = charged[0].name.replace(" ", "_") if charged else "NONE"
    owner_gb = charged[0].exclusive if charged else 0.0
    print(f"PHASE_RESULT {args.species} {args.basis} {args.route} {args.method} "
          f"{d_e:.9f} {peak:.4f} {owner_name} {owner_gb:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
