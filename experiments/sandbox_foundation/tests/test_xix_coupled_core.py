"""OPERATION XIX Track A -- general_coupled core.

ONE world temperature threaded into the fast-equilibrium projection (1C, replacing the hard-coded 298.15 in
_project); a WORLD-level execution certificate re-verified at integrate() (1D, closing the coupled path that
consumed compartment matrices directly, bypassing the single-compartment guard); and the AUTHORITATIVE fast-
equilibrium derived scalars captured on the trajectory (1B, instead of discarded).  The unified vinegar/bicarbonate
world is the vehicle -- a real multi-compartment CoupledWorld with a projection, an interface and an external
boundary.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from experiments.sandbox_foundation.aqueous_equilibrium import OutOfSourceDomainError
from experiments.sandbox_foundation.general_coupled import CoupledWorld
from experiments.sandbox_foundation.general_kernel import StaleCertificateError
from experiments.sandbox_foundation.unified_chemical_world import (
    UnifiedParams,
    _build_species,
    build_unified_world,
    initial_state,
)

SP = _build_species()
INIT = initial_state(SP, acid_mol=0.5, bicarb_solid_mol=0.2, bicarb_dissolved_mol=0.1)


def _world(**pkw):
    return build_unified_world(UnifiedParams(**pkw), SP, valve_open=True, sealed=False).world


# ---------------------------------------------------------------- 1C: temperature threaded, not hard-coded
def test_1c_off_domain_temperature_fails_closed():
    """The world temperature now flows into _project; a 310 K world fail-closes through the 25 C-only operator's own
    sourced-domain guard instead of running gas physics at T while the equilibria stay pinned at 25 C."""
    base = _world()
    w = CoupledWorld(base.compartments, interfaces=base.interfaces, boundaries=base.boundaries, temperature_K=310.0)
    with pytest.raises(OutOfSourceDomainError):
        w.integrate(INIT, duration=1.0, n_steps=2, scheme="strang")


def test_1c_default_temperature_still_runs():
    assert _world().integrate(INIT, duration=20.0, n_steps=30, scheme="strang").receipt.material_balance_closed


def test_1c_world_rejects_nonfinite_temperature():
    from experiments.sandbox_foundation.general_coupled import CoupledError
    base = _world()
    with pytest.raises(CoupledError):
        CoupledWorld(base.compartments, temperature_K=float("nan"))


# ---------------------------------------------------------------- 1B: authoritative derived scalars captured
def test_1b_derived_scalars_captured_per_cell_and_sample():
    traj = _world().integrate(INIT, duration=40.0, n_steps=60, scheme="strang", n_samples=5)
    dB = traj.equilibrium_derived["B"]
    assert len(dB) == len(traj.times)                       # one derived record per sampled state
    last = dB[-1]
    for key in ("pH", "pH_activity", "pH_concentration", "ionic_strength_M", "activity_model"):
        assert key in last
    assert last["activity_model"] == "davies"
    assert abs(last["pH_activity"] - last["pH_concentration"]) > 1e-6     # Davies: activity != concentration
    # a compartment with NO fast equilibrium (the gas headspace) carries an empty derived dict each sample
    assert traj.equilibrium_derived["gas"][-1] == {}


def test_1b_concentration_ph_matches_recomputed_minus_log10_H():
    """The solver's OWN pH_concentration equals -log10([H+]) recomputed from the installed H+ inventory -- the XVIII
    bug was purely that the renderer reported this CONCENTRATION number under a plain `pH` label while the model is
    Davies-based; the authoritative activity value was available all along."""
    traj = _world().integrate(INIT, duration=40.0, n_steps=60, scheme="strang", n_samples=4)
    hplus = traj.amounts["B"][-1][SP.Hp]                     # mol; V_B_L default = 1.0 L so [H+] = amount
    recomputed = -math.log10(hplus / UnifiedParams().V_B_L)
    assert abs(recomputed - traj.equilibrium_derived["B"][-1]["pH_concentration"]) < 1e-6


# ---------------------------------------------------------------- 1D: world execution certificate
def test_1d_boundary_rebind_is_caught():
    w = _world()
    w.boundaries.append(w.boundaries[0])
    with pytest.raises(StaleCertificateError):
        w.integrate(INIT, duration=1.0, n_steps=2, scheme="strang")


def test_1d_interface_rebind_is_caught():
    w = _world()
    w.interfaces.append(w.interfaces[0])
    with pytest.raises(StaleCertificateError):
        w.integrate(INIT, duration=1.0, n_steps=2, scheme="strang")


def test_1d_compartment_matrix_rebind_is_caught():
    """Rebinding a compartment system's stoichiometric matrix N after construction -- the coupled path consumes N
    directly, which previously skipped the single-compartment integrate() guard -- is now caught."""
    w = _world()
    sysB = w.compartments[1].system
    newN = np.array(sysB.N, dtype=float)
    newN.setflags(write=True)
    newN[0, 0] += 1.0
    sysB.N = newN
    with pytest.raises(StaleCertificateError):
        w.integrate(INIT, duration=1.0, n_steps=2, scheme="strang")


def test_1d_compartment_swap_is_caught():
    w = _world()
    w.compartments[2] = _world().compartments[0]
    with pytest.raises(StaleCertificateError):
        w.integrate(INIT, duration=1.0, n_steps=2, scheme="strang")


def test_1d_unmutated_world_integrates():
    assert _world().integrate(INIT, duration=20.0, n_steps=30, scheme="strang").receipt.material_balance_closed
