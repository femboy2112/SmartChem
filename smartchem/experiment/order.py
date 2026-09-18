"""The order-theoretic primitive under every Pareto frontier in the compiler: the maximal antichain.

A "Pareto frontier" is not a chemistry idea -- it is one order-theoretic operation wearing two hats in this
codebase.  Given a finite carrier ``S`` and a strict partial order ``≺`` ("dominates"), the frontier is the set
of ``≺``-MAXIMAL elements -- the antichain ``{ x ∈ S : ¬∃ y ∈ S. y ≻ x }`` -- the points nothing else beats.  The
ONLY thing that varies between the compiler's frontiers is the ORDER; the sweep that extracts the maximal set is
identical.  So it lives here, once, parameterized by the relation, and the two orders are supplied by their homes:

* the **M2-FP product order** on ``(Δ_rG drive, survival)`` -- :meth:`functorial_physics.PhysicsProduct.dominates`,
  with the eligibility domain "both axes known" (an incomplete objective is incomparable to everything, so it is
  never on the frontier -- passed as ``eligible``).  Consumed by :func:`functorial_physics.pareto_optimal`.
* the **disposition/cost order** on a :class:`~smartchem.experiment.affordability.CostVector` -- the G6 tier
  (CLEAN < REAL_BUT_HARD < NOT_A_REACTION) over the section-10.4 numeric axes, :func:`affordability.dominates`.
  Consumed by :func:`affordability.pareto_frontier`.

This is a deliberately SMALL shared law -- "the maximal elements of a strict partial order" -- not a forced
abstraction (contrast the deferred shared-ranker: two rankers whose *keys* genuinely differed shared no law).
Here the law IS identical and the order is a first-class parameter, which is exactly the case where extracting the
sweep is sound: a bug fix or a tie-handling change now lives in ONE tested place instead of two hand-synced copies.

The same law has a natural GENERALIZATION the ranker needs: :func:`non_dominated_layers` stratifies the whole
carrier into ranked antichains by repeated frontier-peeling (layer 0 is the frontier; layer 1 the frontier once
layer 0 is gone; ...).  It is defined AS repeated :func:`non_dominated_indices`, so the frontier is exactly its
layer 0 and the tie/termination/index-remap handling is never re-derived -- the drafter's M2b Pareto-rank tier
(``_pareto_front_indices``) used to hand-roll that peel-and-remap inline, which is precisely the footgun this
module exists to hold in one audited place.

The sweep is the naive ``O(n²)`` all-pairs comparison.  That is correct for any strict partial order (it makes no
transitivity or total-order assumption a cleverer sort would need) and the carriers here are tiny (a search's route
set); a faster divide-and-conquer frontier is a measured-tradeoff optimization, not an identity-preserving one, and
is deferred until a carrier is ever large enough to want it.
"""
from __future__ import annotations

from typing import Callable, Sequence, TypeVar

T = TypeVar("T")

__all__ = ["non_dominated_indices", "non_dominated_layers"]


def non_dominated_indices(
    items: "Sequence[T]",
    dominates: "Callable[[T, T], bool]",
    *,
    eligible: "Callable[[T], bool] | None" = None,
) -> tuple[int, ...]:
    """Indices of the ``≺``-maximal (non-dominated) items -- the maximal antichain of a strict partial order.

    ``dominates(a, b)`` is the strict partial order: ``True`` iff ``a`` STRICTLY dominates ``b``.  An item survives
    (is on the frontier) iff no OTHER eligible item dominates it.  Index order follows the input order.

    ``eligible`` optionally restricts the carrier to a sub-domain: it filters BOTH the candidates AND the comparators,
    so an ineligible item never appears on the frontier and never dominates one that does.  This is how an
    "incomparable to everything" point (e.g. a physics objective with an unknown axis) is kept off the frontier
    without the ``dominates`` relation having to encode the exclusion -- ``eligible=lambda o: o.is_complete``.  With
    ``eligible=None`` every item is eligible.

    The comparison is ``dominates(items[j], items[i])`` for every eligible ``j != i`` -- so the relation is asked
    "does j beat i?".  ``j != i`` guards self-comparison, so a (harmlessly reflexive) relation is tolerated.
    """
    elig = tuple(i for i, x in enumerate(items) if eligible is None or eligible(x))
    return tuple(
        i for i in elig
        if not any(dominates(items[j], items[i]) for j in elig if j != i)
    )


def non_dominated_layers(
    items: "Sequence[T]",
    dominates: "Callable[[T, T], bool]",
    *,
    eligible: "Callable[[T], bool] | None" = None,
) -> tuple[int, ...]:
    """Per-item non-domination LAYER -- the stratification of a strict partial order into ranked antichains.

    ``layer[i]`` is the peel depth of item ``i``: layer 0 is the frontier (:func:`non_dominated_indices` -- the
    ``≺``-maximal antichain), layer 1 is the frontier once layer 0 is removed, and so on.  This is the natural
    generalization of the frontier -- among the ELIGIBLE items, ``non_dominated_indices(...)`` is exactly
    ``{ i : layer[i] == 0 }`` -- and it is computed AS repeated frontier peels, so the sweep and its tie/index-remap
    handling live in ONE place (:func:`non_dominated_indices`) and are never re-derived here.

    The layering is domination-MONOTONE: a dominator always lands in a STRICTLY lower layer than anything it
    dominates (it is removed in an earlier peel), so the layer index never orders two items against ``dominates``,
    and two INCOMPARABLE items share a layer.  ``layer`` is thus a sound coarsening of the partial order into total
    tiers -- safe to use as a ranking key without ever claiming a Pareto relation ``dominates`` would deny.

    ``eligible`` (same semantics as :func:`non_dominated_indices`) restricts the carrier: an ineligible item is
    NEVER peeled -- it is assigned layer 0 (neutral) and never dominates an eligible one.  This is how an
    "incomparable to everything" point (an objective with an unknown axis) is kept NEUTRAL rather than penalized for
    its unknown axis, without ``dominates`` having to encode the exclusion -- ``eligible=lambda o: o.is_complete``.
    With ``eligible=None`` every item is peeled.

    The comparison direction is inherited verbatim from :func:`non_dominated_indices` -- ``dominates(items[j],
    items[i])`` asks "does j beat i" -- so pinning one primitive's argument-order convention pins both.

    PRECONDITION: ``dominates`` and ``eligible`` must be PURE -- their truth values depend only on the items, not on
    mutable external state.  The peel seeds ``remaining`` from ``eligible`` ONCE and the inner frontier sweep runs on
    that all-eligible sub-carrier WITHOUT re-applying ``eligible``, so a state-dependent ``eligible`` that flipped an
    item from eligible to ineligible mid-peel would silently diverge from a per-pass re-filter.  That "eligible at
    seed time, still eligible at peel time" invariant is the one silent load-bearing assumption here, so the loop
    asserts it rather than trust a comment (a dalembert reinforcement -- make the invariant guard itself:
    [[a-verifier-that-cannot-verify-must-fail-closed]]).
    """
    layers = [0] * len(items)
    remaining = [i for i, x in enumerate(items) if eligible is None or eligible(x)]
    depth = 0
    while remaining:
        # Self-guard the one silent invariant: every surviving ``remaining`` member is STILL eligible, so omitting
        # ``eligible`` on the sub-carrier below is a genuine no-op (not a divergence from a per-pass re-filter).  Holds
        # trivially for a pure ``eligible``; fires loudly only if a caller broke the purity precondition above.
        assert all(eligible is None or eligible(items[i]) for i in remaining), (
            "non_dominated_layers: an item in `remaining` is no longer eligible -- `eligible` must be pure "
            "(state-independent); a mid-peel eligibility flip silently diverges the stratification"
        )
        # The frontier of the SUB-carrier (all-eligible by the assertion above, so no ``eligible`` arg needed), then
        # REMAP its sub-tuple indices back to the ORIGINAL positions.  A non-empty carrier of a strict partial order
        # always has a ``≺``-maximal element, so ``front`` is non-empty and ``remaining`` strictly shrinks -- the peel
        # terminates.  Peeling an empty ``front`` off a non-empty ``remaining`` would loop forever, so guard it.
        nd_local = non_dominated_indices([items[i] for i in remaining], dominates)
        front = {remaining[k] for k in nd_local}
        if not front:  # unreachable for a genuine strict partial order; a defensive guard, not a live branch
            break
        for i in front:
            layers[i] = depth
        remaining = [i for i in remaining if i not in front]
        depth += 1
    return tuple(layers)
