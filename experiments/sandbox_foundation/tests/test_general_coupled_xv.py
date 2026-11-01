"""OPERATION XV Wave C (P2) -- the general coupled-world gates.

The load-bearing pins:
  * the ARCHITECTURE GATE: two unrelated coupled systems run through ONE unedited integrator;
  * exact global conservation in a closed world, and a measured splitting ORDER (Lie ~1, Strang ~2) against a
    monolithic reference, with the Lie error strictly larger than Strang (R, T do not commute -- the experiment is
    not vacuous);
  * the coupled integrator REPRODUCES its references (single compartment == bare Wave A kernel; pure diffusion ==
    the volume-weighted steady state; the fast-equilibrium projection == a one-shot Wave B solve at the net totals);
  * fail-closed: an identity-changing interface, an unknown compartment/species, a RATE_UNKNOWN reaction, and a
    monolithic request on an equilibrium world are all REFUSED; the admitted tier is DERIVED and capped, never
    inflated by a caller's declared kinetic tier.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.claim_tiers import (
    ASSUMED_PARAMETER,
    BENCHMARKED_AGAINST_REFERENCE_SOLVER,
    STRUCTURALLY_CONSERVING,
)
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    InterfaceTransfer,
    splitting_convergence,
)
from experiments.sandbox_foundation.general_coupled_demo import (
    A,
    Acm,
    B,
    HAc,
    NaAc,
    Nap,
    build_acetate_buffer_world,
    build_pure_diffusion_world,
    build_reaction_diffusion_world,
    build_single_reaction_compartment,
)
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    MassActionIrreversible,
    Phase,
    Reaction,
    Species,
)


# ---------------------------------------------------------------- the architecture gate
def test_two_unrelated_worlds_run_through_one_integrator():
    rd_world, rd_initial = build_reaction_diffusion_world()
    buf_world, _bsys, _coupling, buf_initial = build_acetate_buffer_world()
    # DIFFERENT chemistries (disjoint component sets) through the SAME CoupledWorld.integrate -- no integrator edit
    assert set(rd_world.component_labels) == {"R", "charge"}
    assert set(buf_world.component_labels) == {"C", "H", "Na", "O", "charge"}
    t1 = rd_world.integrate(rd_initial, duration=4.0, n_steps=50, scheme="strang")
    t2 = buf_world.integrate(buf_initial, duration=50.0, n_steps=50, scheme="strang")
    assert t1.solver_success and t2.solver_success
    assert type(rd_world.integrate) is type(buf_world.integrate)


# ---------------------------------------------------------------- conservation + splitting order
def test_closed_reaction_diffusion_conserves_to_machine_zero():
    world, initial = build_reaction_diffusion_world()
    traj = world.integrate(initial, duration=4.0, n_steps=400, scheme="strang")
    assert traj.max_conserved_drift < 1e-12
    assert traj.receipt.conserved_components_held
    assert traj.min_amount >= -1e-10


def test_lie_first_order_strang_second_order_and_noncommuting():
    world, initial = build_reaction_diffusion_world()
    conv = splitting_convergence(world, initial, duration=4.0, steps_list=[4, 8, 16, 32, 64, 128])
    assert 0.80 <= conv["lie"]["fitted_order"] <= 1.25
    assert 1.80 <= conv["strang"]["fitted_order"] <= 2.20
    # the experiment is non-vacuous only if the operators do not commute: Lie error must be real and dominate Strang
    assert conv["lie"]["errors"][-1] > 0.0
    assert conv["lie"]["errors"][-1] > 5.0 * conv["strang"]["errors"][-1]


# ---------------------------------------------------------------- reference reproductions
def test_single_compartment_reproduces_the_bare_wave_a_kernel():
    world, sys, initial = build_single_reaction_compartment()
    traj = world.integrate(initial, duration=5.0, n_steps=100, scheme="strang", rtol=1e-11, atol=1e-14)
    direct = sys.integrate({A: 2.0, B: 0.0}, duration=5.0, n_samples=2, method="BDF", rtol=1e-11, atol=1e-14)
    cf = traj.amounts["only"][-1]
    assert abs(cf[A] - direct.amounts[-1][A]) < 1e-7
    assert abs(cf[B] - direct.amounts[-1][B]) < 1e-7


def test_pure_diffusion_reaches_the_volume_weighted_steady_state():
    V0, V1 = 1.0, 3.0
    world, initial = build_pure_diffusion_world(V0=V0, V1=V1, k=0.8)
    traj = world.integrate(initial, duration=200.0, n_steps=400, scheme="strang")
    c0 = traj.amounts["c0"][-1]
    c1 = traj.amounts["c1"][-1]
    total = 1.0
    assert abs(c0[A] / V0 - c1[A] / V1) < 1e-6                      # equal concentration at steady state
    assert abs(c0[A] - total * V0 / (V0 + V1)) < 1e-4               # the closed-form split
    assert abs((c0[A] + c1[A]) - total) < 1e-12                     # mass conserved exactly


def test_fast_equilibrium_projection_matches_a_one_shot_wave_b_solve():
    world, sys, coupling, initial = build_acetate_buffer_world(volume_L=1.0, feed_rate=2.0e-4)
    traj = world.integrate(initial, duration=100.0, n_steps=200, scheme="strang")
    final = traj.amounts["buffer"][-1]
    acetate = final[HAc] + final[Acm] + final[NaAc]
    sodium = final[Nap] + final[NaAc]
    direct = coupling.operator.speciate({"acetate": acetate, "sodium": sodium}, volume_L=sys.volume_L)
    for name, sp in coupling.species_table.items():
        assert abs(final[sp] - direct.species_amounts[name]) < 1e-9
    # conserved components close exactly; H/O/charge are reported as reservoir exchange, not claimed conserved
    assert traj.max_conserved_drift < 1e-9
    assert traj.feed_ledger_residual < 1e-9
    assert set(traj.receipt.reservoir_exchange) == {"H", "O", "charge"}
    assert abs(traj.receipt.reservoir_exchange["H"] - 4 * 2.0e-4 * 100.0) < 1e-6   # fed H4 x 0.02 mol HAc
    assert abs(traj.receipt.reservoir_exchange["charge"]) < 1e-9


def test_fed_carbon_ledger_tracks_the_acetate_feed():
    # total acetate carbon must rise by exactly the fed HAc (2 C each): a feed ledger, not a tautology
    world, sys, coupling, initial = build_acetate_buffer_world(volume_L=1.0, feed_rate=2.0e-4)
    traj = world.integrate(initial, duration=100.0, n_steps=100, scheme="strang")
    final = traj.amounts["buffer"][-1]
    acetate = final[HAc] + final[Acm] + final[NaAc]
    assert abs(acetate - (0.1 + 2.0e-4 * 100.0)) < 1e-7


# ---------------------------------------------------------------- fail-closed
def test_identity_changing_interface_is_refused():
    with pytest.raises(CoupledError):
        InterfaceTransfer("bad", "c0", "c1", A, B, k_transfer=0.5)   # A ({R:1}) != B ({R:2})


def test_unknown_compartment_and_species_are_refused():
    sys = ChemicalSystem([A, B], [], volume_L=1.0)
    with pytest.raises(CoupledError):
        CoupledWorld(compartments=[Compartment("c0", sys)],
                     interfaces=[InterfaceTransfer("x", "c0", "ghost", A, A, k_transfer=0.1)])
    world = CoupledWorld(compartments=[Compartment("c0", sys)])
    ghost = Species.of("ghost", {"Z": 1}, phase=Phase.AQUEOUS)
    with pytest.raises(CoupledError):
        world.integrate({"c0": {ghost: 1.0}}, duration=1.0, n_steps=1)


def test_rate_unknown_reaction_is_refused_in_the_coupled_world():
    sys = ChemicalSystem([A, B], [Reaction("2A->B", ((A, -2), (B, 1)))], volume_L=1.0)   # no rate law -> RATE_UNKNOWN
    world = CoupledWorld(compartments=[Compartment("c0", sys)])
    with pytest.raises(CoupledError):
        world.integrate({"c0": {A: 1.0}}, duration=1.0, n_steps=1)


def test_monolithic_is_refused_when_an_equilibrium_projection_is_present():
    world, _sys, _coupling, initial = build_acetate_buffer_world()
    with pytest.raises(CoupledError):
        world.integrate(initial, duration=10.0, n_steps=5, scheme="monolithic")
    with pytest.raises(CoupledError):
        splitting_convergence(world, initial, duration=10.0, steps_list=[2, 4])


def test_admitted_tier_is_derived_and_capped_never_inflated():
    # synthetic rate laws are ASSUMED_PARAMETER -> the whole coupled claim caps DOWN to ASSUMED_PARAMETER
    world, initial = build_reaction_diffusion_world()
    traj = world.integrate(initial, duration=4.0, n_steps=50, scheme="strang")
    assert traj.receipt.structural_tier == STRUCTURALLY_CONSERVING
    assert traj.receipt.declared_kinetic_tier == ASSUMED_PARAMETER
    assert traj.tier == ASSUMED_PARAMETER
    # a caller DECLARING a strong kinetic tier cannot push the coupled claim above structural conservation
    strong = Species.of("P", {"R": 1}, phase=Phase.AQUEOUS)
    q = Species.of("Q", {"R": 2}, phase=Phase.AQUEOUS)
    sys = ChemicalSystem(
        [strong, q],
        [Reaction("2P->Q", ((strong, -2), (q, 1)),
                  MassActionIrreversible(k=0.5, tier=BENCHMARKED_AGAINST_REFERENCE_SOLVER))],
        volume_L=1.0)
    w2 = CoupledWorld(compartments=[Compartment("c", sys)])
    t2 = w2.integrate({"c": {strong: 1.0}}, duration=2.0, n_steps=20, scheme="strang")
    assert t2.receipt.declared_kinetic_tier == BENCHMARKED_AGAINST_REFERENCE_SOLVER
    assert t2.tier == STRUCTURALLY_CONSERVING            # capped: the coupled world does no reference-solver check
