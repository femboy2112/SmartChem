"""Contract tests for the shared maximal-antichain primitive :func:`smartchem.experiment.order.non_dominated_indices`.

The primitive is the ONE sweep under both Pareto frontiers (functorial_physics.pareto_optimal +
affordability.pareto_frontier), so its calling convention is load-bearing.  The pin that matters most is
:func:`test_argument_order_is_pinned_the_second_arg_is_the_candidate` -- a dalembert red-team fold: the primitive
asks ``dominates(items[j], items[i])`` = "does j beat the candidate i", and a future caller who passes the
argument order flipped (``lambda a, b: b.dominates(a)``) would SILENTLY INVERT the frontier with no crash.  This
file defends the convention in CI so it is not defended only by whoever last read the docstring.
"""
from __future__ import annotations

from smartchem.experiment.order import non_dominated_indices

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
