"""M2b (Move-2): the M2-FP functorial-physics objective made LIVE in the route/DAG ranking scorer.

M2-FP (ROUND 25) built ``PhysicsProduct`` / ``pareto_optimal`` / ``route_net_delta_g`` but gave them ZERO call
sites in the core ranker (the tracked debt).  M2b wires them in: ``_pareto_front_indices`` (peeling
``pareto_optimal`` into non-dominated layers) runs on EVERY ``rank_routes`` / ``rank_dags`` call, and two NEW
tiers ride ``_route_score`` / ``_dag_score`` between the worst-node feasibility SIGN and equilibrium --

  * a Pareto non-dominated FRONT over ``PhysicsProduct(net ΔG, survival)`` -- the tier that exercises
    ``PhysicsProduct`` / ``pareto_optimal``; and
  * the additive-ΔG MAGNITUDE (the Hess functor ``G: Process->(ℝ,+,≤)``) -- the LIVE single-axis refinement.

Honest scope (birdperson design fold).  The ΔG-magnitude axis is the BROADLY-LIVE surface (any route with a
sourced/derivable net ΔG).  The two-axis FRONT is DATA-GATED: ``route_surviving_fraction`` is ``None`` unless a
DAG serial hold exposes a SOURCED first-order rate for the idling intermediate (R23), so on the default seed the
front is inert (all layer 0) and the ranking falls to the ΔG magnitude -- the front FIRES where sourced kinetics
reach, proven NON-VACUOUSLY below on a REAL ``Composability``-derived survival (the same data-gated discipline as
the R25 two-axis ``frontier``).  The tie-break decision: Pareto-INCOMPARABLE complete routes SHARE a front (never
a fabricated dominance) and present by ΔG then discovery order -- a PRESENTATION order, not a dominance claim; the
front index is the honest dominance datum, and the two axes are NEVER collapsed into one weighted scalar.
"""
from __future__ import annotations

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.kinetics import DEFAULT_KINETICS, KineticRef
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.drafter import (
    ConstraintBox,
    _dag_score,
    _pareto_front_indices,
    _route_score,
    dag_bench_fit,
    fit_route,
    rank_routes,
)
from smartchem.experiment.functorial_physics import PhysicsProduct, route_net_delta_g
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles as M

# sourced species for real net-ΔG routes
H2, O2, H2O, CO, CO2 = M("[H][H]"), M("O=O"), M("O"), M("[C-]#[O+]"), M("O=C=O")


def _step(reactants, products, target):
    return ExperimentStep.assembling(target, tuple(reactants), tuple(products))


# ======================================================================================
# _pareto_front_indices -- the non-dominated peel (the birdperson termination/remap trap)
# ======================================================================================
class TestParetoFrontIndices:
    def test_a_dominator_sits_in_a_strictly_earlier_layer_than_what_it_dominates(self):
        best = PhysicsProduct(-50.0, 0.9)          # dominates the next
        dominated = PhysicsProduct(-10.0, 0.5)
        assert _pareto_front_indices((best, dominated)) == (0, 1)

    def test_incomparable_complete_points_share_a_layer(self):
        favorable_fragile = PhysicsProduct(-80.0, 0.2)
        marginal_durable = PhysicsProduct(-5.0, 0.99)
        assert _pareto_front_indices((favorable_fragile, marginal_durable)) == (0, 0)

    def test_incomplete_objectives_are_neutral_layer_zero_never_penalized(self):
        # survival None (the common case) -> incomplete -> layer 0, exactly like a non-dominated point.  The
        # DISCLOSED consequence: a dominated-but-complete point (layer 1) can present below an incomplete one.
        complete_best = PhysicsProduct(-50.0, 0.9)
        complete_dominated = PhysicsProduct(-10.0, 0.5)
        incomplete = PhysicsProduct(-1.0, None)
        assert _pareto_front_indices((complete_best, complete_dominated, incomplete)) == (0, 1, 0)

    def test_all_incomplete_is_all_layer_zero_and_terminates(self):
        # the peel must EXCLUDE incompletes (pareto_optimal returns only complete indices) or it never terminates.
        assert _pareto_front_indices((PhysicsProduct(-1.0, None), PhysicsProduct(-2.0, None))) == (0, 0)
        assert _pareto_front_indices(()) == ()

    def test_three_layers_peel_and_remap_correctly(self):
        # a chain a > b > c must peel to layers 0,1,2 -- the index remap (sub-tuple -> original) must be right.
        a, b, c = PhysicsProduct(-30.0, 0.9), PhysicsProduct(-20.0, 0.8), PhysicsProduct(-10.0, 0.7)
        assert _pareto_front_indices((a, b, c)) == (0, 1, 2)
        # and order-independence: the same set shuffled keeps each point's layer
        assert _pareto_front_indices((c, a, b)) == (2, 0, 1)


# ======================================================================================
# The ΔG-magnitude tier is LIVE end-to-end in rank_routes (the broadly-live surface)
# ======================================================================================
class TestDeltaGMagnitudeIsLiveInRankRoutes:
    def test_a_more_negative_net_drive_floats_within_the_same_feasibility_sign(self):
        # two single-step FAVORABLE routes tied on status/composability/selectivity/feasibility-SIGN: the additive
        # net-ΔG magnitude (the Hess functor) breaks the tie -- the far more exergonic water formation floats above
        # the mildly exergonic water-gas shift.  Pre-M2b these tied (the scorer used only the FAVORABLE sign).
        water = ExperimentRoute.of(_step([H2, H2, O2], [H2O, H2O], H2O))     # ~ -474 kJ, strongly favorable
        shift = ExperimentRoute.of(_step([CO, H2O], [CO2, H2], CO2))          # ~ -28 kJ, mildly favorable
        ranked = rank_routes([shift, water])                                  # given worst-first
        assert route_net_delta_g(water) < route_net_delta_g(shift) < 0        # both favorable; water far more so
        assert ranked[0].route == water and ranked[1].route == shift          # the M2b ΔG tier floats water

    def test_unknown_net_drive_is_neutral_not_a_penalty(self):
        # a route with an unsourced species has net ΔG None -> the ΔG tier is the neutral 0.0 sentinel; it never
        # SINKS a route for missing thermo (the "neutral on ignorance" discipline the sign tiers already use).
        unknown_route = ExperimentRoute.of(_step([M("C=C"), M("Br")], [M("CCBr")], M("CCBr")))  # HBr unsourced
        assert route_net_delta_g(unknown_route) is None
        sc = _route_score(fit_route(unknown_route, ConstraintBox()))          # standalone -> net_delta_g None
        assert sc[5] == 0.0                                                   # the ΔG-magnitude slot is neutral


# ======================================================================================
# The Pareto FRONT tier FIRES on a REAL survival (birdperson's non-vacuous requirement)
# ======================================================================================
def _synthetic_form_rate(ea_kj: float = 92.0, log10a: float = 13.0):
    # a transparently SYNTHETIC first-order decomposition rate for the FORMALDEHYDE held intermediate -- a TEST
    # LEVER for the duration wire-in (the exact pattern test_duration_survival_gate uses), NOT fabricated data
    # entering any seed.  Ea=92 kJ/mol, log10A=13 -> k ~ 1e-3 /s at 300 K, so a 5-min forced hold survives ~0.75 and
    # a 120-min forced hold ~0.001 -- a clean survival spread for a domination flip.
    return DEFAULT_KINETICS.with_records(KineticRef(
        reactant_smiles=(("C=O", 1),), product_smiles=(("[H][H]", 1), ("[C-]#[O+]", 1)),
        name="formaldehyde decomposition (SYNTHETIC TEST rate)", ea_kj_per_mol=ea_kj, log10_a=log10a,
        a_units="s^-1", temperature_range_k=(1.0, 1000.0),
        provenance="SYNTHETIC TEST rate; exercises the M2b front tier on a real survival, not a measurement",
    ))


def _forced_between_dag(forced_minutes: float) -> SynthesisDAG:
    # Move 6: a REAL survival fraction now requires an UNAVOIDABLE (forced-between) hold, not a schedule-avoidable
    # one.  A genuine shortcut/diamond delivers it: formaldehyde (the held intermediate) is consumed by BOTH the
    # methanol step and the glycol join, so the methanol step is UNAVOIDABLY between formaldehyde's producer and the
    # join in every valid schedule.  The longer that forced middle step, the longer formaldehyde idles -> the lower
    # its survival (with a matched rate).  (A bare convergent join's hold is schedule-avoidable -> survival None.)
    gly, form, meoh, h2, egly = (M(s) for s in ("OCC=O", "C=O", "CO", "[H][H]", "OCCO"))

    def step(target, reactants, products, minutes):
        env = ConditionEnvelope(
            temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
            provenance="synthetic process control; no experimental claim",
            process=_requirements(minutes),
        )
        return ExperimentStep.assembling(target, reactants, products, envelope=env)

    return SynthesisDAG.of(
        step(form, (gly,), (form, form), 40.0),           # glycolaldehyde -> 2 formaldehyde (the held intermediate)
        step(meoh, (form, h2), (meoh,), forced_minutes),  # formaldehyde + H2 -> methanol (the UNAVOIDABLE middle step)
        step(egly, (form, meoh), (egly,), 40.0),          # formaldehyde + methanol -> ethylene glycol (the join)
    )


def _requirements(minutes: float):
    from tests.test_process_service import requirements
    return requirements(elapsed_minutes=Interval(minutes, minutes, "min"))


class TestParetoFrontTierFiresOnRealSurvival:
    def test_the_front_layers_two_real_dag_objectives_and_flips_their_order(self):
        # TWO forced-between DAGs identical in chemistry, differing ONLY in the length of the UNAVOIDABLE middle
        # step => different REAL survival (from Composability's R23 duration gate over the FORCED hold, via a matched
        # synthetic rate).  Move 6: a real survival now requires an UNAVOIDABLE (forced-between) hold -- a bare
        # convergent join's hold is schedule-avoidable and yields None (its verdict must not depend on listing
        # order).  The shorter forced hold survives more, so at TIED ΔG it Pareto-DOMINATES the longer one -- the
        # non-vacuous proof that the front tier (pareto_optimal) reorders real survival-bearing objectives.
        #
        # HONEST CAVEAT: survival is read via dag_composability(dag, kinetics=...) directly, because dag_bench_fit
        # threads kinetics only to the thermo rollup, NOT to the duration gate (a pre-existing scope boundary), and
        # rank_dags uses the DEFAULT tables.  So END-TO-END through rank_dags the front fires only when the held
        # intermediate carries a DEFAULT-SEEDED first-order rate (N2O5/cyclopropane) -- otherwise survival is None
        # and the front is inert (layer 0), the ranking falling to the live ΔG-magnitude axis.  Data-gated exactly
        # like the R25 two-axis `frontier`; this test exercises the layering on the real survival that gating admits.
        from smartchem.experiment.dag import dag_composability
        box = ConstraintBox()
        kin = _synthetic_form_rate()
        dag_short, dag_long = _forced_between_dag(5.0), _forced_between_dag(120.0)
        surv_short = dag_composability(dag_short, kinetics=kin).route_surviving_fraction
        surv_long = dag_composability(dag_long, kinetics=kin).route_surviving_fraction
        assert surv_short is not None and surv_long is not None       # REAL survival from the UNAVOIDABLE hold
        assert surv_short > surv_long                                  # the shorter forced hold survives more
        # identical chemistry => identical additive net ΔG (the additive functor is blind to the timing attribute):
        # route_net_delta_g agrees for the two (whether it derives to a number or fail-closes to None on this seed).
        assert route_net_delta_g(dag_short) == route_net_delta_g(dag_long)
        # the front must layer these by SURVIVAL when the ΔG axis TIES; use a common (favorable) ΔG so survival is
        # the sole decider and the ΔG-magnitude tier (index 5) is equal-and-neutral between them.
        dg = -100.0
        products = (PhysicsProduct(dg, surv_short), PhysicsProduct(dg, surv_long))
        assert products[0].dominates(products[1])                      # short dominates long (equal ΔG, more survival)
        fronts = _pareto_front_indices(products)
        assert fronts == (0, 1)                                        # the front tier separates them -- NON-VACUOUS
        # and the full _dag_score tuples (the exact rank_dags key) put the dominator strictly first, DRIVEN by the
        # front tier (index 4), not the ΔG magnitude (index 5, equal here) -- the structural fit tiers are identical.
        fit_short, fit_long = dag_bench_fit(dag_short, box), dag_bench_fit(dag_long, box)
        key_short = _dag_score(fit_short, fronts[0], dg)
        key_long = _dag_score(fit_long, fronts[1], dg)
        assert key_short < key_long
        assert key_short[4] < key_long[4] and key_short[5] == key_long[5]


# ======================================================================================
# The tie-break honesty: incomparable complete routes are NOT forced into a false order
# ======================================================================================
class TestIncomparableAreNotFalselyOrdered:
    def test_incomparable_complete_objectives_share_a_front_no_dominance_claimed(self):
        favorable_fragile = PhysicsProduct(-80.0, 0.2)
        marginal_durable = PhysicsProduct(-5.0, 0.99)
        # neither dominates -> same front -> the FRONT tier asserts no order between them (the honest dominance datum
        # says "incomparable").  The ΔG magnitude then PRESENTS them (favorable first) -- disclosed as presentation,
        # not dominance; the front index is what a consumer reads for a real Pareto verdict.
        assert not favorable_fragile.comparable_to(marginal_durable)
        assert _pareto_front_indices((favorable_fragile, marginal_durable)) == (0, 0)
