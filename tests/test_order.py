"""Contract tests for the shared maximal-antichain primitive :func:`smartchem.experiment.order.non_dominated_indices`.

The primitive is the ONE sweep under both Pareto frontiers (functorial_physics.pareto_optimal +
affordability.pareto_frontier), so its calling convention is load-bearing.  The pin that matters most is
:func:`test_argument_order_is_pinned_the_second_arg_is_the_candidate` -- a dalembert red-team fold: the primitive
asks ``dominates(items[j], items[i])`` = "does j beat the candidate i", and a future caller who passes the
argument order flipped (``lambda a, b: b.dominates(a)``) would SILENTLY INVERT the frontier with no crash.  This
file defends the convention in CI so it is not defended only by whoever last read the docstring.
"""
from __future__ import annotations

from smartchem.experiment.order import non_dominated_indices, non_dominated_layers

# a strict total order used as the domination relation: "a beats b iff a is the larger number", so the ≺-maximal
# (non-dominated) element is the LARGEST.  Directional on purpose -- reversing it changes the answer.
_BIGGER_DOMINATES = lambda a, b: a > b  # noqa: E731


def test_argument_order_is_pinned_the_second_arg_is_the_candidate():
    # Under "bigger dominates", the single survivor is the MAXIMUM: index 0 (value 3), because nothing beats it.
    # If the convention were the other way round -- dominates(candidate, other) -- the survivor would be the MINIMUM.
    # This asserts, in CI, that the SECOND positional argument is the candidate being tested for survival.
    assert non_dominated_indices((3, 1, 2), _BIGGER_DOMINATES) == (0,)
    # the mirror relation ("smaller dominates") must instead surface the MINIMUM (index 1, value 1) -- proving the
    # answer genuinely tracks the relation's direction, so the first pin was not an accident of a symmetric input.
    assert non_dominated_indices((3, 1, 2), lambda a, b: a < b) == (1,)


def test_empty_and_singleton():
    assert non_dominated_indices((), _BIGGER_DOMINATES) == ()
    assert non_dominated_indices((42,), _BIGGER_DOMINATES) == (0,)  # nothing to dominate a lone element


def test_ties_and_duplicates_all_survive():
    # a tie is INCOMPARABLE under a strict order (neither beats the other), so both survive -- the anti-collapse
    # discipline the frontier depends on (identical points never dominate each other).
    assert non_dominated_indices((5, 5, 5), _BIGGER_DOMINATES) == (0, 1, 2)
    # input (index) order is preserved among survivors.
    assert non_dominated_indices((1, 9, 9, 2), _BIGGER_DOMINATES) == (1, 2)


def test_reflexive_relation_is_tolerated_via_self_guard():
    # a (harmlessly) reflexive relation must not knock an element off via self-comparison -- the `j != i` guard.
    everything_beats_everything = lambda a, b: True  # noqa: E731
    # every element is beaten by some OTHER element, so nothing survives -- but NOT because it beat itself.
    assert non_dominated_indices((1, 2, 3), everything_beats_everything) == ()
    assert non_dominated_indices((7,), everything_beats_everything) == (0,)  # lone element: no OTHER to beat it


def test_eligible_restricts_candidates_and_comparators():
    # an ineligible item never appears on the frontier AND never dominates an eligible one: it is removed from BOTH
    # the candidate set and the comparator set (the "incomplete objective is incomparable to everything" semantics).
    items = (10, 3, 20, 1)
    # eligible = "value < 15" excludes index 2 (20).  Among {10, 3, 1} under "bigger dominates", 10 (index 0) wins;
    # crucially the excluded 20 does NOT dominate 10, so 10 survives despite a larger ineligible value existing.
    assert non_dominated_indices(items, _BIGGER_DOMINATES, eligible=lambda x: x < 15) == (0,)
    # eligible=None means all eligible -> the true max (20, index 2) wins.
    assert non_dominated_indices(items, _BIGGER_DOMINATES, eligible=None) == (2,)


def test_incomparable_points_all_survive():
    # a relation with genuine incomparability (2-D Pareto): (x, y), a beats b iff a>=b on both and > on one.
    def dominates(a, b):
        return a[0] >= b[0] and a[1] >= b[1] and (a[0] > b[0] or a[1] > b[1])

    pts = ((2, 1), (1, 2), (3, 3), (2, 2))
    # (3,3) dominates all others; it is the sole survivor.
    assert non_dominated_indices(pts, dominates) == (2,)
    # drop the dominator: (2,1) and (1,2) are mutually incomparable and neither is beaten -> both survive; (2,2)?
    # (2,2) beats (2,1) and (1,2)? (2,2) vs (2,1): 2>=2,2>=1,strict on y -> yes dominates. vs (1,2): 2>=1,2>=2,strict
    # on x -> yes.  So (2,2) is the sole non-dominated point.
    assert non_dominated_indices(((2, 1), (1, 2), (2, 2)), dominates) == (2,)


# ======================================================================================================================
# non_dominated_layers -- the stratification (repeated frontier peels).  This is the drafter M2b Pareto-rank tier's
# home (``_pareto_front_indices``); the pins below are the contract that fold rides on.  The load-bearing one is
# test_layers_frontier_is_the_zero_layer: it asserts, structurally, that the generalization AGREES with the frontier
# primitive at depth 0 -- so the two order primitives cannot silently drift apart.
# ======================================================================================================================


def test_layers_stratify_a_total_order():
    # Under "bigger dominates" on (3, 1, 2): 3 is the frontier (layer 0); remove it and 2 is the next frontier
    # (layer 1); remove it and 1 is last (layer 2).  Indexed back to input positions: value 3@0 -> 0, 1@1 -> 2, 2@2 -> 1.
    assert non_dominated_layers((3, 1, 2), _BIGGER_DOMINATES) == (0, 2, 1)


def test_layers_argument_order_is_pinned_the_second_arg_is_the_candidate():
    # Mirror of the frontier pin: "smaller dominates" must stratify the OTHER way (min is layer 0), proving the depth
    # genuinely tracks the relation's direction and the second positional arg is the candidate under test.
    assert non_dominated_layers((3, 1, 2), lambda a, b: a < b) == (2, 0, 1)
    # and the two directions must disagree -- if they matched, the argument order would not be load-bearing.
    assert non_dominated_layers((3, 1, 2), _BIGGER_DOMINATES) != non_dominated_layers((3, 1, 2), lambda a, b: a < b)


def test_layers_frontier_is_the_zero_layer():
    # The structural invariant that keeps the two primitives coherent: among eligible items, the layer-0 set is EXACTLY
    # the frontier that non_dominated_indices returns.  Checked on a genuine 2-D Pareto carrier (real incomparability).
    def dominates(a, b):
        return a[0] >= b[0] and a[1] >= b[1] and (a[0] > b[0] or a[1] > b[1])

    pts = ((2, 1), (1, 2), (3, 3), (2, 2), (0, 0))
    layers = non_dominated_layers(pts, dominates)
    zero_layer = {i for i, lay in enumerate(layers) if lay == 0}
    assert zero_layer == set(non_dominated_indices(pts, dominates))


def test_layers_incomparable_points_share_a_layer():
    # ties are incomparable under a strict order -> no peel separates them -> all sit on layer 0 together.
    assert non_dominated_layers((5, 5, 5), _BIGGER_DOMINATES) == (0, 0, 0)
    # a genuine 2-D antichain (each better on one axis) is one whole layer too.
    def dominates(a, b):
        return a[0] >= b[0] and a[1] >= b[1] and (a[0] > b[0] or a[1] > b[1])

    assert non_dominated_layers(((2, 1), (1, 2)), dominates) == (0, 0)


def test_layers_2d_stratification_depth():
    # (3,3) dominates everything (layer 0); (2,2) dominates (2,1)&(1,2) so it is the next frontier (layer 1); the two
    # mutually-incomparable points (2,1),(1,2) are the deepest (layer 2).  Indexed to input order: (2,1)@0->2,
    # (1,2)@1->2, (3,3)@2->0, (2,2)@3->1.
    def dominates(a, b):
        return a[0] >= b[0] and a[1] >= b[1] and (a[0] > b[0] or a[1] > b[1])

    assert non_dominated_layers(((2, 1), (1, 2), (3, 3), (2, 2)), dominates) == (2, 2, 0, 1)


def test_layers_ineligible_items_stay_at_the_neutral_zero_and_never_peel():
    # The M2b policy the drafter fold depends on: an ineligible item (an incomplete objective) is NEVER peeled -- it is
    # pinned at the neutral layer 0 and does NOT dominate an eligible one.  items (10,3,20,1), eligible = "value < 15"
    # excludes 20@2.  Eligible peel: 10@0 -> layer 0, 3@1 -> layer 1, 1@3 -> layer 2.  The ineligible 20@2 -> layer 0,
    # and crucially 10 stays layer 0 despite the larger 20 existing (20 does not dominate across the eligibility line).
    assert non_dominated_layers((10, 3, 20, 1), _BIGGER_DOMINATES, eligible=lambda x: x < 15) == (0, 1, 0, 2)
    # eligible=None peels everyone -> the true total-order stratification (20@2 the frontier).
    assert non_dominated_layers((10, 3, 20, 1), _BIGGER_DOMINATES, eligible=None) == (1, 2, 0, 3)


def test_layers_empty_and_singleton():
    assert non_dominated_layers((), _BIGGER_DOMINATES) == ()
    assert non_dominated_layers((42,), _BIGGER_DOMINATES) == (0,)


def test_layers_pathological_relation_terminates_via_the_guard():
    # a (non-strict) relation where every element is "beaten" by some other leaves an EMPTY frontier on a non-empty
    # carrier; without the ``if not front: break`` guard the peel would loop forever.  The guard leaves the unpeeled
    # items at the initialized neutral layer 0 -- matching the drafter code's original defensive behaviour.
    everything_beats_everything = lambda a, b: True  # noqa: E731
    assert non_dominated_layers((1, 2, 3), everything_beats_everything) == (0, 0, 0)
    # a lone element has no OTHER to beat it, so it is a normal layer-0 frontier (the guard does not fire).
    assert non_dominated_layers((7,), everything_beats_everything) == (0,)
