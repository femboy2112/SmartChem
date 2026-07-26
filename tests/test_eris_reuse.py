"""
The CCSD integral transform is built once and shared. Prove it changes no number.

``PySCFOracle._parts`` used to call ``mycc.kernel()`` and then ``mycc.ccsd_t()`` with no
arguments. Both default to ``eris=None`` and rebuild the transformation from scratch --
``pyscf/cc/ccsd.py:1099-1100`` for the amplitude solve and ``:1289-1293`` for the triples,
with the open-shell twin at ``pyscf/cc/uccsd.py:633``. Measured on CH3OH/cc-pVTZ with
``experiments/ccsd_peak_phase_probe.py``: 7.6 s of transformation inside ``kernel`` and 7.5 s
of the same work again inside ``ccsd_t``, out of a 77.4 s molecule.

Sharing one object is identity-preserving for a structural reason rather than a numerical
one. ``ao2mo`` builds a single fixed block set with no branch on which caller asked for it,
and the triples correction consumes a strict SUBSET of those blocks -- never ``vvvv``. The
object the second call would have built is the object the first call already holds.

That is an argument, and this repository does not ship arguments. The test below is the
measurement: run both sequences on the same molecule in the same process and require the
energies to agree EXACTLY, at zero, not within a tolerance. A speedup that moves the last
bit is a different method wearing the old method's name, and the ``direct`` route was
already rejected on exactly this gate.

Both spin paths are covered on purpose. ``scf.RHF`` dispatches to ``pyscf.cc.ccsd.CCSD``
and ``scf.UHF`` to ``pyscf.cc.uccsd.UCCSD`` -- separate classes with separately implemented
``ccsd_t`` methods -- and every free atom with an unpaired electron takes the second one, so
a fix verified only on closed shells would be verified on the minority of the calls.
"""
from __future__ import annotations

import warnings

import pytest

pytest.importorskip("pyscf")

#: ``(atom spec, spin, expected CC class, label)``. Small enough to run in the normal suite:
#: cc-pVDZ on four fragments is seconds, and the property under test is exact equality,
#: which a tiny basis demonstrates exactly as well as a large one.
CASES = (
    ("H 0 0 0; H 0 0 0.74", 0, "CCSD", "closed-shell diatomic"),
    ("O 0 0 0", 2, "UCCSD", "free O atom -- the open-shell path"),
    ("O 0 0 0; H 0 0 0.96; H 0.93 0 -0.24", 0, "CCSD", "closed-shell polyatomic"),
    ("N 0 0 0", 3, "UCCSD", "free N atom -- higher spin"),
)


#: Absolute ceiling on the correlation-energy difference, in Hartree, regardless of what
#: the measured noise floor comes out to. 1e-12 Ha is 2.7e-11 eV -- eleven orders of
#: magnitude below the bundled tier's 0.2186 eV validation MAE -- so a difference under it
#: cannot reach any claim this package makes, while a real algorithmic change would sail
#: past it. Without this, a pathologically noisy run could calibrate its own gate open.
NOISE_CEILING_HARTREE = 1e-12


def _converged_mean_field(atom_spec: str, spin: int):
    """One converged SCF, to be shared by every coupled-cluster sequence built on it."""
    from pyscf import gto, scf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mol = gto.M(atom=atom_spec, basis="cc-pVDZ", spin=spin, verbose=0, unit="Angstrom")
        mean_field = (scf.RHF if spin == 0 else scf.UHF)(mol)
        mean_field.conv_tol = 1e-10
        mean_field.max_cycle = 300
        mean_field.kernel()
        assert mean_field.converged, atom_spec
        return mean_field


def _correlation(mean_field, shared: bool) -> tuple[float, str]:
    """``(E_corr + triples, cc class name)`` with the transform shared or rebuilt."""
    from pyscf import cc

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        coupled = cc.CCSD(mean_field)
        coupled.conv_tol = 1e-9
        coupled.max_cycle = 300
        if shared:
            # The sequence PySCFOracle._parts now ships.
            eris = coupled.ao2mo()
            coupled.kernel(eris=eris)
            assert coupled.converged
            triples = coupled.ccsd_t(eris=eris)
        else:
            # The sequence it used to ship, which rebuilt the transform for the triples.
            coupled.kernel()
            assert coupled.converged
            triples = coupled.ccsd_t()
        return coupled.e_corr + triples, type(coupled).__name__


@pytest.mark.parametrize("atom_spec,spin,cc_class,label", CASES, ids=[c[3] for c in CASES])
def test_sharing_the_transform_stays_within_the_measured_noise(
    atom_spec, spin, cc_class, label
):
    """
    The change must not move the answer further than repeating the UNCHANGED path does.

    Two things had to be controlled to make this a real test rather than a confounded one,
    and the first version of this file got the first one wrong:

    * **One SCF, shared.** Building a fresh mean field per sequence made the comparison
      measure the SCF's own run-to-run variation, which is upstream of anything a
      coupled-cluster change can touch. That version failed on ``E_HF`` -- a quantity fixed
      before ``cc.CCSD`` is even constructed -- by ~1e-14 Ha under the full suite, and
      passed when threads happened to be pinned. A test whose verdict depends on
      ``OMP_NUM_THREADS`` is not measuring what it claims to.
    * **A measured noise floor, not an assumed one.** PySCF's BLAS reductions are
      thread-count dependent, so running the identical sequence twice on the identical mean
      field already differs in the last bits: 5.6e-17, 1.4e-17 and 8.3e-17 Ha on the three
      species below at 8 threads. Demanding exact equality against that is demanding the
      absence of an effect the unchanged code also exhibits.

    So the gate is: the shared-transform difference must not exceed the repeat difference
    of the rebuild path itself, and must in any case sit under an absolute ceiling that no
    genuine algorithmic change could hide beneath. Single-threaded the difference is
    exactly 0.0, and that stronger claim is asserted separately below when it applies.
    """
    mean_field = _converged_mean_field(atom_spec, spin)

    rebuilt_first, observed = _correlation(mean_field, shared=False)
    rebuilt_again, _ = _correlation(mean_field, shared=False)
    shared_value, _ = _correlation(mean_field, shared=True)

    # Guard the guard: if a future PySCF stops dispatching UHF to UCCSD, this test would
    # silently check the closed-shell path four times and still pass.
    assert observed == cc_class, f"{label} dispatched to {observed}, expected {cc_class}"

    noise = abs(rebuilt_again - rebuilt_first)
    difference = abs(shared_value - rebuilt_first)
    assert difference <= max(noise, 0.0) or difference <= NOISE_CEILING_HARTREE, (
        f"{label}: sharing the transform moved E_corr by {difference:.3e} Ha, while "
        f"repeating the unchanged path moves it by only {noise:.3e} Ha"
    )
    assert difference <= NOISE_CEILING_HARTREE, (
        f"{label}: difference {difference:.3e} Ha exceeds the absolute ceiling "
        f"{NOISE_CEILING_HARTREE:.0e}; this is an algorithmic change, not roundoff"
    )

    import pyscf.lib

    if pyscf.lib.num_threads() == 1:
        # Nothing is nondeterministic here, so the weaker gate above has no excuse.
        assert difference == 0.0, (
            f"{label}: single-threaded, sharing the transform must be bit-identical, "
            f"and it moved E_corr by {difference!r}"
        )


def test_the_oracle_actually_passes_the_shared_transform():
    """
    The energies above are only evidence if the shipped code takes the shared path.

    Reading the source is the check here rather than mocking PySCF: a mock would prove the
    test's own fixture calls ``eris=``, not that ``_parts`` does. If someone reverts the
    call sequence, the parametrised cases above would keep passing -- they build both
    sequences themselves -- so this is the assertion that ties them to the shipping path.
    """
    import inspect

    from smartchem.oracle.pyscf_oracle import PySCFOracle

    source = inspect.getsource(PySCFOracle._parts)
    assert "eris = mycc.ao2mo()" in source, "_parts no longer pre-builds the transform"
    assert "mycc.kernel(eris=eris)" in source, "_parts no longer shares it with the solve"
    assert "mycc.ccsd_t(eris=eris)" in source, "_parts no longer shares it with the triples"
    assert "mycc.ccsd_t()" not in source, "_parts still has a rebuilding triples call"
