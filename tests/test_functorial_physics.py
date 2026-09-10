"""Move-2 M2-FP: the free-energy drive as an additive functor, paired with survival (no scalar collapse).

Pins: (1) **Hess's law IS functoriality** -- the additive net-ΔG of a multi-step route equals the ΔG of its
single net reaction (shared intermediates cancel), non-vacuously; (2) the :class:`FreeEnergyDecoration`
monoid + interchange law (a second instance of the ``open_core`` decoration slot); (3) the
:class:`PhysicsProduct` Pareto order forbids collapsing "favorable" and "fast" into one score; (4)
anti-fabrication: the DOW-Br₂ dissociation verdict is now SOURCED (CODATA Br(g)/Br₂(g), DOW-thermo) and
calibrated to the known Br-Br bond enthalpy, while a genuinely unsourced species (HBr) still fail-closes.
"""
import pytest

from smartchem.experiment.feasibility import (
    FeasibilityDirection,
    RouteFeasibility,
    feasibility_of_step,
    verify_feasibility,
)
from smartchem.experiment.functorial_physics import (
    FreeEnergyDecoration,
    PhysicsProduct,
    pareto_optimal,
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
        # a step with an unsourced species -> None net drive, never a partial sum.  HBr ("BrH") has no sourced
        # record and no Benson group, so it stays UNKNOWN even though Br(g)/Br₂(g) are now sourced (DOW-thermo):
        # the sourced-by-formula lookup does NOT leak across a related formula (the anti-fabrication boundary).
        hbr, ethylene, etbr = M("Br"), M("C=C"), M("CCBr")
        s = _step([ethylene, hbr], [etbr], etbr)
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


class TestParetoOptimal:
    def test_dominated_points_are_excluded(self):
        best = PhysicsProduct(-50.0, 0.9)
        dominated = PhysicsProduct(-10.0, 0.5)
        assert pareto_optimal((best, dominated)) == (0,)

    def test_incomparable_points_are_both_kept(self):
        favorable_fragile = PhysicsProduct(-80.0, 0.2)
        marginal_durable = PhysicsProduct(-5.0, 0.99)
        assert pareto_optimal((favorable_fragile, marginal_durable)) == (0, 1)

    def test_identical_points_are_both_kept(self):
        p = PhysicsProduct(-10.0, 0.8)
        q = PhysicsProduct(-10.0, 0.8)
        assert pareto_optimal((p, q)) == (0, 1)

    def test_incomplete_objectives_are_never_optimal(self):
        known = PhysicsProduct(-50.0, 0.9)
        unknown = PhysicsProduct(-99.0, None)
        assert pareto_optimal((known, unknown)) == (0,)

    def test_all_incomplete_yields_empty_frontier(self):
        assert pareto_optimal((PhysicsProduct(-10.0, None), PhysicsProduct(None, 0.5))) == ()


# ======================================================================================
# DOW-thermo: the DOW-Br₂ thermodynamic verdict, now SOURCED (CODATA) and calibrated -- never invented
# ======================================================================================
class TestDowBromineThermodynamicVerdict:
    """DOW-thermo (ROUND 26) supersedes the R25 data-gated fail-close: Br(g)/Br₂(g) ΔfH°/S° are now sourced
    from the CODATA Key Values (Cox, Wagman et al. 1984; fetched + cross-checked 2026-09-07 vs NIST WebBook +
    the official CODATA table), so the DOW-Br₂ dissociation verdict FIRES -- and it reproduces known chemistry
    (Br₂ is thermodynamically stable against dissociation at 298 K), calibrated to the Br-Br bond enthalpy."""

    def test_bromine_dissociation_verdict_is_now_sourced_and_endergonic(self):
        # Br₂ -> 2 Br•: with sourced CODATA Br(g)/Br₂(g), the verdict is UNFAVORABLE (endergonic at 298 K) --
        # the DOW-Br₂ THERMODYNAMIC verdict the R25 fail-close was waiting on a data add to unlock.
        br2, br = M("BrBr"), M("[Br]")
        step = _step([br2], [br, br], br)
        # item 5 (phase-carrying key): Br₂ is now tabulated in BOTH gas and liquid, so a gas-phase dissociation
        # must DECLARE its phase -- a phase-blind Br₂ resolves to a loud UNKNOWN (never the silent gas ΔfH°).
        result = feasibility_of_step(step, phases={br2: "gas", br: "gas"})
        assert result.direction is FeasibilityDirection.UNFAVORABLE  # Br₂ is stable against dissociation at RT
        assert result.missing == ()                                   # nothing missing now -- both are sourced
        # calibration to KNOWN chemistry: ΔH = 2·ΔfH°(Br,g) − ΔfH°(Br₂,g) = 2(111.87) − 30.91 = +192.83 kJ/mol,
        # which IS the standard Br-Br bond dissociation enthalpy (~192.8 kJ/mol) -- not an invented number.
        assert result.delta_h_kj == pytest.approx(192.83, abs=0.05)
        assert result.delta_s_j_per_k == pytest.approx(104.568, abs=0.01)
        assert result.delta_g_kj == pytest.approx(161.65, abs=0.1)    # +ΔG => endergonic, disfavored
        # a real SOURCED band, propagated in quadrature from the CODATA ± -- never a hollow 0.0
        assert result.sigma_delta_g_kj is not None and result.sigma_delta_g_kj > 0

    def test_the_atom_and_the_molecule_are_distinctly_sourced_no_formula_borrow(self):
        # the bromine ATOM ("Br") and the molecule ("Br2") each resolve to their OWN CODATA record; neither is
        # fabricated to (0, 0), and a related formula (HBr = "BrH") does NOT borrow either value.
        from smartchem.experiment.feasibility import resolve_thermo
        assert resolve_thermo(M("[Br]")).dhf_kj_per_mol == pytest.approx(111.87)   # Br atom: single-phase
        # item 5: Br₂ is dual-phase (gas/liquid), so the GAS dfH is reached by NAMING the phase; a phase-blind
        # resolve_thermo(Br₂) is now a loud None, never a silent gas borrow for a liquid claim (M2b debt closed).
        assert resolve_thermo(M("BrBr"), phase="gas").dhf_kj_per_mol == pytest.approx(30.91)
        assert resolve_thermo(M("BrBr")) is None
        assert resolve_thermo(M("Br")) is None   # HBr: unsourced, no Benson group -> a loud gap, no borrow

    def test_the_dissociation_route_net_drive_equals_the_single_step(self):
        # route_net_delta_g on the single-step dissociation route is the same endergonic drive (functoriality)
        br2, br = M("BrBr"), M("[Br]")
        route = ExperimentRoute.of(_step([br2], [br, br], br))
        # item 5: the gas-phase dissociation declares Br₂ is gas (phases forwarded to each step's feasibility)
        assert route_net_delta_g(route, phases={br2: "gas", br: "gas"}) == pytest.approx(161.65, abs=0.1)


# ======================================================================================
# Item-5 brick: verify_feasibility THREADS `phases` (the last phase-blind verify_* fold, closed)
# ======================================================================================
class TestVerifyFeasibilityThreadsPhases:
    """The linear-route ``verify_feasibility`` now forwards ``phases`` to every step, the mirror of
    ``route_net_delta_g``'s DAG threading -- so a single phase declaration flows through BOTH the worst-node
    ``verdict`` and the additive ``net_delta_g_kj`` drive.  A phase-blind route carrying a dual-phase species
    (Br₂ gas/liquid) fail-closes to a loud UNKNOWN at the route level, never a silently-wrong-phase ΔG."""

    def test_phase_blind_route_with_a_dual_phase_species_is_a_loud_unknown(self):
        # Br₂ -> 2 Br•, no phase declared: Br₂ is dual-phase, so the step -- and the whole route verdict + net
        # drive -- fail closed, exactly as feasibility_of_step does for the single step (the fold reaches the route).
        br2, br = M("BrBr"), M("[Br]")
        route = ExperimentRoute.of(_step([br2], [br, br], br))
        rfeas = verify_feasibility(route)
        assert rfeas.verdict == "UNKNOWN"
        assert rfeas.net_delta_g_kj is None                       # a partial/wrong-phase sum never poses as a drive
        assert "bromine" in " ".join(rfeas.per_step[0].missing).lower() or rfeas.per_step[0].missing != ()

    def test_declaring_the_phase_flows_through_verdict_and_net_drive(self):
        # the SAME route, with Br₂ declared gas, now fires: worst-node verdict UNFAVORABLE and the additive
        # Hess drive equals the single endergonic step (functoriality), both off the one `phases` declaration.
        br2, br = M("BrBr"), M("[Br]")
        route = ExperimentRoute.of(_step([br2], [br, br], br))
        rfeas = verify_feasibility(route, phases={br2: "gas", br: "gas"})
        assert rfeas.verdict == "UNFAVORABLE"                     # Br₂ stable against dissociation at RT
        assert rfeas.net_delta_g_kj == pytest.approx(161.65, abs=0.1)
        assert rfeas.per_step[0].missing == ()

    def test_a_single_phase_route_is_byte_identical_with_or_without_phases(self):
        # the default is byte-stable: a route with NO dual-phase species gives the identical RouteFeasibility
        # whether or not `phases` is passed (extra/irrelevant entries are harmless -- each step filters its own).
        route = _steam_reforming_route()
        without = verify_feasibility(route)
        with_irrelevant = verify_feasibility(route, phases={M("BrBr"): "gas"})
        assert without == with_irrelevant
        assert without.verdict == with_irrelevant.verdict
        assert without.net_delta_g_kj == with_irrelevant.net_delta_g_kj
