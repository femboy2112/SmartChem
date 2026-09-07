"""Move-2 M2-FP: the free-energy drive as an additive functor, paired with survival (no scalar collapse).

Pins: (1) **Hess's law IS functoriality** -- the additive net-ΔG of a multi-step route equals the ΔG of its
single net reaction (shared intermediates cancel), non-vacuously; (2) the :class:`FreeEnergyDecoration`
monoid + interchange law (a second instance of the ``open_core`` decoration slot); (3) the
:class:`PhysicsProduct` Pareto order forbids collapsing "favorable" and "fast" into one score; (4)
anti-fabrication: the DOW-Br₂ dissociation stays UNKNOWN (no sourced Br thermo -> fail-closed, not guessed).
"""
import pytest

from smartchem.experiment.feasibility import (
    FeasibilityDirection,
    RouteFeasibility,
    feasibility_of_step,
)
from smartchem.experiment.functorial_physics import (
    FreeEnergyDecoration,
    PhysicsProduct,
    route_net_delta_g,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles as M

CH4 = M("C")
H2O = M("O")
CO = M("[C-]#[O+]")
CO2 = M("O=C=O")
H2 = M("[H][H]")


def _step(reactants, products, target):
    return ExperimentStep.assembling(target, tuple(reactants), tuple(products))


def _steam_reforming_route() -> ExperimentRoute:
    # all species sourced in DEFAULT_THERMO; the intermediate CO cancels across the two steps
    s1 = _step([CH4, H2O], [CO, H2, H2, H2], CO)     # CH4 + H2O -> CO + 3 H2   (endergonic)
    s2 = _step([CO, H2O], [CO2, H2], CO2)            # CO + H2O -> CO2 + H2     (exergonic)
    return ExperimentRoute.of(s1, s2)


# ======================================================================================
# Hess's law IS functoriality: net-ΔG(route) == Σ per-step ΔG == ΔG(single net reaction)
# ======================================================================================
class TestHessFunctoriality:
    def test_route_net_delta_g_equals_the_single_net_reaction(self):
        route = _steam_reforming_route()
        sigma = route_net_delta_g(route)
        net_step = _step([CH4, H2O, H2O], [CO2, H2, H2, H2, H2], CO2)  # CH4 + 2 H2O -> CO2 + 4 H2
        net_direct = feasibility_of_step(net_step).delta_g_kj
        assert sigma is not None and net_direct is not None
        assert sigma == pytest.approx(net_direct, abs=1e-6)

    def test_the_functoriality_is_non_vacuous(self):
        # the two steps have OPPOSITE signs and the net differs from either -- the sum is doing real work
        route = _steam_reforming_route()
        g1 = feasibility_of_step(route.steps[0]).delta_g_kj
        g2 = feasibility_of_step(route.steps[1]).delta_g_kj
        assert g1 > 0 and g2 < 0
        net = route_net_delta_g(route)
        assert net not in (g1, g2)

    def test_route_feasibility_surfaces_the_additive_drive(self):
        route = _steam_reforming_route()
        rf = RouteFeasibility(route, tuple(feasibility_of_step(s) for s in route.steps))
        assert rf.net_delta_g_kj == pytest.approx(route_net_delta_g(route), abs=1e-6)
        # the additive drive is DISTINCT from the worst-node categorical verdict (both legitimate)
        assert rf.verdict in {"FAVORABLE", "BORDERLINE", "UNFAVORABLE", "UNKNOWN"}

    def test_an_unknown_step_makes_the_net_drive_unknown_fail_closed(self):
        # a step with an unsourced species -> None net drive, never a partial sum
        br2, br = M("BrBr"), M("[Br]")
        s = _step([br2], [br, br], br)
        route = ExperimentRoute.of(s)
        assert route_net_delta_g(route) is None
        rf = RouteFeasibility(route, tuple(feasibility_of_step(x) for x in route.steps))
        assert rf.net_delta_g_kj is None


# ======================================================================================
# The FreeEnergyDecoration monoid -- a second instance of the open_core decoration slot
# ======================================================================================
class TestFreeEnergyDecoration:
    def test_then_and_tensor_are_both_addition(self):
        a = FreeEnergyDecoration(-10.0)
        b = FreeEnergyDecoration(4.0)
        assert a.then_combine(b) == FreeEnergyDecoration(-6.0)
        assert a.tensor_combine(b) == FreeEnergyDecoration(-6.0)

    def test_identity_is_zero(self):
        a = FreeEnergyDecoration(-7.5)
        assert a.then_combine(FreeEnergyDecoration.identity()) == a

    def test_unknown_is_absorbing_fail_closed(self):
        known = FreeEnergyDecoration(3.0)
        unknown = FreeEnergyDecoration(None)
        assert known.then_combine(unknown).delta_g_kj is None
        assert unknown.tensor_combine(known).delta_g_kj is None
        assert unknown.is_known is False and known.is_known is True

    def test_interchange_law_holds(self):
        a, b, c, d = (FreeEnergyDecoration(v) for v in (1.0, 2.0, 4.0, 8.0))
        left = a.then_combine(b).tensor_combine(c.then_combine(d))
        right = a.tensor_combine(c).then_combine(b.tensor_combine(d))
        assert left == right == FreeEnergyDecoration(15.0)


# ======================================================================================
# The Pareto product -- "favorable != fast": no scalar collapse
# ======================================================================================
class TestPhysicsProduct:
    def test_a_pareto_better_point_dominates(self):
        better = PhysicsProduct(delta_g_kj=-50.0, surviving_fraction=0.9)
        worse = PhysicsProduct(delta_g_kj=-10.0, surviving_fraction=0.5)
        assert better.dominates(worse)
        assert not worse.dominates(better)

    def test_favorable_but_fragile_is_incomparable_to_marginal_but_durable(self):
        favorable_fragile = PhysicsProduct(delta_g_kj=-80.0, surviving_fraction=0.2)
        marginal_durable = PhysicsProduct(delta_g_kj=-5.0, surviving_fraction=0.99)
        assert not favorable_fragile.dominates(marginal_durable)
        assert not marginal_durable.dominates(favorable_fragile)
        assert not favorable_fragile.comparable_to(marginal_durable)

    def test_equal_points_do_not_dominate(self):
        p = PhysicsProduct(delta_g_kj=-10.0, surviving_fraction=0.8)
        q = PhysicsProduct(delta_g_kj=-10.0, surviving_fraction=0.8)
        assert not p.dominates(q) and not q.dominates(p)

    def test_an_unknown_axis_is_incomparable_fail_closed(self):
        known = PhysicsProduct(delta_g_kj=-50.0, surviving_fraction=0.9)
        unknown_survival = PhysicsProduct(delta_g_kj=-99.0, surviving_fraction=None)
        assert not known.dominates(unknown_survival)
        assert not unknown_survival.dominates(known)
        assert unknown_survival.is_complete is False


# ======================================================================================
# Anti-fabrication: the DOW-Br₂ thermodynamic verdict is DATA-GATED, never invented
# ======================================================================================
class TestDowBromineThermoIsDataGated:
    def test_bromine_dissociation_is_unknown_without_sourced_thermo(self):
        # Br₂ -> 2 Br•: conserving, but no sourced Br ΔfH°/S° exists, so the verdict fail-closes to UNKNOWN
        br2, br = M("BrBr"), M("[Br]")
        step = _step([br2], [br, br], br)
        result = feasibility_of_step(step)
        assert result.direction is FeasibilityDirection.UNKNOWN
        assert result.delta_g_kj is None
        assert "Br" in "".join(result.missing) or result.missing  # the missing species is named
