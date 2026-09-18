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

The sweep is the naive ``O(n²)`` all-pairs comparison.  That is correct for any strict partial order (it makes no
transitivity or total-order assumption a cleverer sort would need) and the carriers here are tiny (a search's route
set); a faster divide-and-conquer frontier is a measured-tradeoff optimization, not an identity-preserving one, and
is deferred until a carrier is ever large enough to want it.
"""
from __future__ import annotations

from typing import Callable, Sequence, TypeVar

T = TypeVar("T")

__all__ = ["non_dominated_indices"]


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
