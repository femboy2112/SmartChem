"""OPERATION XVIII Track B (P0, §3) -- every external boundary produces a SIGNED, INDEPENDENTLY-INTEGRATED material
flux, and the world's material balance is checked against THAT, not inferred from the endpoint inventory diff.

The pre-XVIII CoupledWorld exempted fixed-activity (and implicit-solvent) components from conservation and reported
their net change as ``reservoir_exchange[c] = E n_final - E n0`` -- a TAUTOLOGY (the "ledger" is defined as whatever
the inventory did, so internal creation/destruction in such a component is absorbed silently and the world still
certifies STRUCTURALLY_CONSERVING).

The repair accumulates each boundary's flux via quadrature of the SAME raw boundary operations, as augmented ODE
state, so:

    d n / dt = N r + B J + q_ext ,     and     d(E n)/dt = E q_ext

is CHECKED: raw_material_change[c] = E (n_final - n0) must equal external_flux[c] = E (integrated q_ext) within a
scale-aware tolerance, for every component NOT coupled to an implicit solvent reservoir.  A mutation that creates or
destroys material internally (without any boundary flux) must break the balance.

Charge-against-neutral-water: neutral water can supply/absorb H and O, but it cannot source NET charge; where "charge"
is implicit-reservoir-coupled the world must DEMOTE the charge-conservation claim explicitly, never silently exempt it.
"""
from __future__ import annotations

from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
    ExternalBoundary,
)
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    MassActionReversible,
    Phase,
    Reaction,
    Species,
)


def _co2():
    return Species.of("CO2(aq)", {"C": 1, "O": 2}, 0, Phase.AQUEOUS, substance="CO2")


def _one_cell_fixed_activity_world():
    """A single aqueous cell holding CO2(aq), swept by a fixed-activity boundary toward target_conc 0 (an open purge).
    No reactions, no equilibrium -- the only thing that moves CO2 is the boundary, so its flux is the whole story."""
    co2 = _co2()
    cell = Compartment("cell", ChemicalSystem([co2], [], volume_L=1.0))
    sweep = ExternalBoundary("sweep", "cell", co2, "fixed_activity", k_transfer=0.5, target_conc=0.0)
    return co2, CoupledWorld([cell], boundaries=[sweep])


# ============================================================ the fixed-activity flux is INDEPENDENTLY accumulated
def test_fixed_activity_component_is_independently_ledgered():
    """§3: the component a fixed-activity boundary touches is checked against the INTEGRATED boundary flux, not
    endpoint-diffed into an unverifiable reservoir bucket.  external_flux (the accumulator) matches the measured
    change, and the balance closes -- for an honestly-conserving world."""
    co2, world = _one_cell_fixed_activity_world()
    traj = world.integrate({"cell": {co2: 1.0}}, duration=2.0, n_steps=40, scheme="lie")
    rc = traj.receipt
    # the new ledger fields exist and the balance closes
    assert rc.material_balance_closed is True
    assert "C" in rc.external_flux and "C" in rc.raw_material_change
    # the INDEPENDENT accumulator matches the measured inventory change (both ~ -0.63 mol C removed)
    assert rc.external_flux["C"] < 0.0, "the sweep removes carbon, so the external flux is negative"
    assert abs(rc.raw_material_change["C"] - rc.external_flux["C"]) <= rc.ledger_adjusted_residual["C"] + 1e-9
    assert rc.ledger_adjusted_residual["C"] < 1e-6


def test_ledger_is_not_tautological_internal_fabrication_breaks_balance():
    """§3 distinguishing probe: material created INTERNALLY (not through any boundary) must break the material balance.
    A subclass fabricates CO2 in the reaction operator; the boundary accumulator never sees it, so raw change != the
    integrated external flux and the balance FAILS.  (Pre-XVIII this was absorbed into reservoir_exchange, silent.)"""
    class _FabricatingWorld(CoupledWorld):
        def _reaction_rhs(self, y):
            dy = super()._reaction_rhs(y)
            dy = dy.copy()
            dy[0] += 1.0e-3          # fabricate CO2 in slot 0 at 1e-3 mol/s, through NO boundary
            return dy

    co2 = _co2()
    cell = Compartment("cell", ChemicalSystem([co2], [], volume_L=1.0))
    sweep = ExternalBoundary("sweep", "cell", co2, "fixed_activity", k_transfer=0.5, target_conc=0.0)
    world = _FabricatingWorld([cell], boundaries=[sweep])
    traj = world.integrate({"cell": {co2: 1.0}}, duration=2.0, n_steps=40, scheme="lie")
    rc = traj.receipt
    # ~2e-3 mol C fabricated internally over 2 s -> the balance must NOT close
    assert rc.material_balance_closed is False, "internal fabrication was absorbed silently (tautological ledger)"
    assert rc.ledger_adjusted_residual["C"] > 1e-4
    assert any("balance" in c.lower() or "ledger" in c.lower() for c in traj.caveats)


# ============================================================ closed and feed boundaries reconcile
def test_closed_system_has_zero_external_flux_and_closes():
    """A world with no boundary exchanges nothing: external flux is ~0 for every component and the balance closes."""
    a = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS)
    b = Species.of("B", {"X": 1}, 0, Phase.AQUEOUS)
    cell = Compartment("c", ChemicalSystem([a, b], [Reaction("A<->B", ((a, -1), (b, 1)),
                                                              MassActionReversible(kf=1.0, kr=0.5))]))
    world = CoupledWorld([cell])
    traj = world.integrate({"c": {a: 1.0}}, duration=5.0, n_steps=50, scheme="strang")
    rc = traj.receipt
    assert rc.material_balance_closed is True
    assert all(abs(v) < 1e-9 for v in rc.external_flux.values())
    assert abs(rc.raw_material_change["X"]) < 1e-8          # X is internally conserved (A<->B)


def test_feed_boundary_flux_matches_rate_times_duration():
    """A constant feed's accumulated flux equals rate*duration (the accumulator recovers the analytic integral), and
    the measured inventory change matches it."""
    a = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS)
    cell = Compartment("c", ChemicalSystem([a], []))
    feed = ExternalBoundary("feedA", "c", a, "feed", rate=0.2)      # +0.2 mol/s of A
    world = CoupledWorld([cell], boundaries=[feed])
    traj = world.integrate({"c": {a: 0.0}}, duration=3.0, n_steps=30, scheme="lie")
    rc = traj.receipt
    assert rc.material_balance_closed is True
    assert abs(rc.external_flux["X"] - 0.2 * 3.0) < 1e-6           # 0.6 mol X fed
    assert abs(rc.raw_material_change["X"] - rc.external_flux["X"]) < 1e-6


def test_neutral_only_world_claims_charge_conserved():
    """Control for the charge/water demotion: a world with no implicit-solvent charge reservoir conserves charge
    outright, so charge_balance_claim is the CONSERVED (independently-checked) verdict, not a demotion."""
    co2, world = _one_cell_fixed_activity_world()
    traj = world.integrate({"cell": {co2: 1.0}}, duration=1.0, n_steps=10, scheme="lie")
    assert "CONSERV" in traj.receipt.charge_balance_claim.upper()
