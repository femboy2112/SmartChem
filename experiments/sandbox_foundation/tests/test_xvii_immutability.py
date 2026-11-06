"""OPERATION XVII Wave D (P0.4) -- the certified execution basis must be immutable + numerically admitted.

A ChemicalSystem proves E.N = 0 EXACTLY (unbounded Python ints) at construction, THEN casts to the float matrices the
integrator executes against (self.E, self.N).  Two gaps the XVII plan names:

  D2 immutability -- self.E and self.N were plain WRITABLE numpy arrays.  A caller could mutate self.N in place AFTER
     the certificate was proven, so the EXECUTED stoichiometry diverged from the CERTIFIED stoichiometry, silently.
     The certificate must describe the exact matrix execution uses -> freeze the arrays read-only.

  D3 numerical-input admission -- both the kernel integrate and the coupled _pack guarded only `amounts < 0`, which a
     NaN slips through (NaN < 0 is False).  A non-finite initial inventory is not a physically admissible state and
     must be refused before integration, not propagated into the solver.

RED on the pre-XVII kernel; GREEN after the freeze + finiteness gate.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
)
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    KernelError,
    MassActionReversible,
    Reaction,
    Species,
)


def _rev_system():
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    sysm = ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=1.0, kr=1.0))])
    return A, B, sysm


# ---------------------------------------------------------------- D2: the execution basis is frozen
def test_stoichiometric_matrix_is_frozen():
    """self.N is read-only: defeating the proven E.N=0 by an in-place mutation after construction is impossible, so
    the executed stoichiometry cannot diverge from the certified one."""
    _A, _B, sysm = _rev_system()
    assert sysm.N.flags.writeable is False
    with pytest.raises(ValueError):
        sysm.N[0, 0] = -5.0


def test_element_matrix_is_frozen():
    _A, _B, sysm = _rev_system()
    assert sysm.E.flags.writeable is False
    with pytest.raises(ValueError):
        sysm.E[0, 0] = 99.0


def test_frozen_system_still_integrates():
    """Regression: freezing the matrices does not break execution (they are read in the RHS, never written)."""
    A, _B, sysm = _rev_system()
    traj = sysm.integrate({A: 1.0}, duration=5.0, n_samples=5)
    assert traj.solver_success
    c0 = sysm.component_amounts({A: 1.0})["X"]
    cf = sysm.component_amounts(traj.amounts[-1])["X"]
    assert abs(cf - c0) < 1e-9       # the conserved X total is unchanged through the frozen-matrix integration


# ---------------------------------------------------------------- D3: non-finite initial inventory is refused
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_kernel_integrate_refuses_nonfinite_initial(bad):
    """A NaN/Inf initial inventory is not an admissible state; the kernel refuses it at the input gate (not via a
    downstream solver failure).  NaN in particular slipped the old `amounts < 0` guard."""
    A, _B, sysm = _rev_system()
    with pytest.raises(KernelError, match="finite"):
        sysm.integrate({A: bad}, duration=1.0, n_samples=3)


def test_kernel_integrate_still_refuses_negative_initial():
    """Regression control: the pre-existing negativity guard still fires."""
    A, _B, sysm = _rev_system()
    with pytest.raises(KernelError):
        sysm.integrate({A: -1.0}, duration=1.0, n_samples=3)


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_coupled_pack_refuses_nonfinite_initial(bad):
    """The coupled world's _pack refuses a non-finite initial inventory for the same reason."""
    A, _B, sysm = _rev_system()
    world = CoupledWorld([Compartment("m", sysm)])
    with pytest.raises(CoupledError, match="finite"):
        world.integrate({"m": {A: bad}}, duration=1.0, n_steps=2, scheme="lie")
