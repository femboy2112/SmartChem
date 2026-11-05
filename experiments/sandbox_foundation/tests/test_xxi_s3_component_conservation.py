"""OPERATION XXI section 3 -- material conservation is COMPONENT-WISE: a defect in a trace component cannot hide
under an unrelated bulk component's inventory.

Before XXI the coupled integrator judged every conserved component against ONE global tolerance tol = atol + rtol*S,
where S was the MAX scale over all components.  So on a world with a 1 mol component X and a 1e-6 mol component Y, the
tolerance was ~1e-6 (set by X), and a 1e-9 mol fabrication of Y -- a 0.1% corruption of Y, physically significant --
was ACCEPTED because 1e-9 < 1e-6.  XXI gives each component its OWN scale: scale_i = max(|C_i(0)|, |external flux_i|),
tol_i = atol + rtol*scale_i, and the balance closes iff EVERY component's own max residual is within ITS OWN tol.

These worlds are pure holding cells (no reactions, no boundaries); the test-only observer hook injects a controlled
per-component excursion at a chosen step.  X = 1.0 mol (bulk), Y = 1e-6 mol (trace) are chosen so a ~1e-9 mol Y
excursion (a) is far above Y's own ~1e-12 tol, (b) is far below X's ~1e-6 tol, and (c) never drives Y negative, so the
MATERIAL (ledger) gate is what fires -- not positivity.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_coupled import Compartment, CoupledWorld
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Species

SX = Species.of("SX", {"X": 1}, charge=0, phase=Phase.AQUEOUS)
SY = Species.of("SY", {"Y": 1}, charge=0, phase=Phase.AQUEOUS)


def _xy_world(x=1.0, y=1e-6):
    sysc = ChemicalSystem([SX, SY], [], volume_L=1.0)
    world = CoupledWorld([Compartment("c", sysc)])
    return world, {"c": {SX: x, SY: y}}


def _perturb_slot(world, species, delta, at_step):
    j = world._slot[("c", species)]

    def hook(step, yv):
        if step == at_step:
            yv = yv.copy()
            yv[j] += delta
        return yv
    return hook


def _run(world, initial, hook=None):
    return world.integrate(initial, duration=1.0, n_steps=50, _observer_perturb=hook)


# ---------------------------------------------------------------- the headline: trace defect under a bulk spectator
def test_trace_fabrication_is_caught_under_a_bulk_spectator():
    world, initial = _xy_world()
    tr = _run(world, initial, _perturb_slot(world, SY, +1e-9, 25))
    r = tr.receipt
    assert r.material_balance_closed is False
    assert r.first_violation and r.first_violation[1] == "material_ledger" and r.first_violation[3] == "Y"
    # Y is judged against its OWN (tiny) tolerance, not X's bulk tolerance
    assert r.component_tolerance["Y"] < 1e-9 < r.component_tolerance["X"]
    assert r.component_max_residual["Y"] == pytest.approx(1e-9, rel=1e-6)


def test_trace_destruction_is_caught():
    world, initial = _xy_world()
    tr = _run(world, initial, _perturb_slot(world, SY, -1e-9, 25))
    r = tr.receipt
    assert r.material_balance_closed is False
    assert r.first_violation[3] == "Y"
    assert r.positivity_held is True                     # Y = 1e-6 - 1e-9 > 0: it is the LEDGER gate that fired


def test_opposing_trace_errors_that_cancel_at_the_endpoint_are_still_caught():
    """+1e-9 at step 25, -1e-9 at step 40: the endpoint Y residual is ~0, but a per-STEP, per-COMPONENT gate still
    catches the mid-trajectory excursion (XX-3 observer-invariance x XXI-3 component-wise)."""
    world, initial = _xy_world()
    j = world._slot[("c", SY)]

    def hook(step, yv):
        # the perturbation PERSISTS in the carried state, so one +1e-9 (step 25) then one -1e-9 (step 40) restores
        # the baseline from step 40 on -- Y rides +1e-9 off-baseline for steps 25..39, then closes at the endpoint.
        if step == 25:
            yv = yv.copy()
            yv[j] += 1e-9
        elif step == 40:
            yv = yv.copy()
            yv[j] -= 1e-9
        return yv
    tr = _run(world, initial, hook)
    r = tr.receipt
    assert r.material_balance_closed is False
    assert r.first_violation and r.first_violation[0] == pytest.approx(0.5)   # caught at the EARLIER (step-25) breach
    assert abs(r.raw_material_change["Y"]) < 1e-12                            # ... though the endpoint ~closed


# ---------------------------------------------------------------- no false positives + the bulk path still works
def test_a_legitimate_trace_component_is_not_falsely_refused():
    world, initial = _xy_world()
    tr = _run(world, initial)                            # no perturbation at all
    r = tr.receipt
    assert r.material_balance_closed is True
    assert r.component_max_residual["Y"] <= r.component_tolerance["Y"]
    assert r.component_max_residual["X"] <= r.component_tolerance["X"]


def test_a_bulk_component_defect_is_still_caught():
    world, initial = _xy_world()
    tr = _run(world, initial, _perturb_slot(world, SX, +1e-3, 25))   # 1e-3 > X's ~1e-6 tol
    r = tr.receipt
    assert r.material_balance_closed is False
    assert r.first_violation[3] == "X"


def test_component_tolerances_scale_with_each_components_own_inventory():
    world, initial = _xy_world(x=1.0, y=1e-6)
    r = _run(world, initial).receipt
    # tol_i = atol(1e-12) + rtol(1e-6)*scale_i: X ~ 1e-6, Y ~ 1e-12 -- six orders apart, matching the six-order
    # inventory gap.  The bulk tolerance is UNCHANGED from the pre-XXI global policy (which equalled X's scale here).
    assert r.component_tolerance["X"] == pytest.approx(1e-12 + 1e-6 * 1.0)
    assert r.component_tolerance["Y"] == pytest.approx(1e-12 + 1e-6 * 1e-6)
    assert r.component_tolerance["X"] / r.component_tolerance["Y"] > 1e5
