"""Move-2 functorial physics: the free-energy drive as an additive functor, paired with survival.

The free-energy fold (``docs/research/FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md``) found that two
of Move 2's physics functors are already computed in code but never framed or unified as functors:

* the **thermodynamic-drive** ``Δ_rG`` -- ``feasibility.feasibility_of_step(step).delta_g_kj``, the Gibbs
  free energy of a step via Hess's law over sourced ``ΔfH°/S°``.  Over a route it is the **additive**
  functor ``G: Process -> (ℝ, +, ≤)``: **Hess's law IS the functoriality**, ``Δ_rG(g∘f) = Δ_rG(f) +
  Δ_rG(g)`` -- the shared intermediates cancel, so the route net equals the sum of its steps.  This module
  makes that recognition concrete (:func:`route_net_delta_g`, surfaced as ``RouteFeasibility.net_delta_g_kj``,
  and a property test pinning ``net == Σ steps``);
* the **kinetic-survival** ``S`` -- ``composability`` `` `route_surviving_fraction` `` (R23), the **multiplicative**
  functor ``S: Process -> ([0, 1], ×)``, ``S(g∘f) = S(g)·S(f)``.

The rung's content is the categorical recognition + the honest **product order** on the two.
:class:`PhysicsProduct` pairs ``(Δ_rG, survival)`` under the Pareto partial order (lower ΔG better, higher
survival better) with **no scalar collapse** -- "favorable ≠ fast": a thermodynamically-driven-but-fragile
route does NOT dominate a marginal-but-stable one; they are *incomparable*.  This is the discipline the
[[observability-score]] three-axis rule and the ``a-reaction-key-by-formula-borrows-a-rate`` anti-collapse
lessons already enforce, promoted to the physics objective.

**Two legitimate ΔG aggregations, distinguished (do not conflate).** The **additive net-ΔG** (Hess, here)
answers *"what is the overall thermodynamic drive of the whole route?"*.  The **worst-node** fold
(``RouteFeasibility.verdict`` / ``dag.dag_thermo_rollup``) answers *"is any single step stuck / endergonic?"*.
They are distinct and both correct; the ranking scorer (``drafter._route_score``) uses only the worst-node
categorical *sign*, never the ΔG magnitude, and does not use survival at all -- a recognized limitation
carried as tracked debt (folding either into the score would re-order routes and churn goldens).

:class:`FreeEnergyDecoration` is a SECOND instance of the ``open_core`` monoidal decoration slot (after
conservation): an additive real that rides ``then``/``tensor`` homomorphically, so it is the exact
decoration shape the open-diagram apex could one day carry.  It is provided + law-tested here; wiring it as
a live apex decoration on ``OpenChemDiagram`` is deferred (it would change the compared apex -- byte-stable
only as an opt-in, a later rung).

Anti-fabrication holds: no thermochemistry is invented.  The DOW-Br₂ **thermodynamic** verdict
(``Br₂ -> 2 Br•``) stays UNKNOWN until sourced ``ΔfH°/S°`` for Br₂(g)/Br(g) are injected via
``ThermoTable.with_records`` -- a data add, not a build (a test pins that it fail-closes today).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..open_core import Decoration, DiagramCompositionError

__all__ = [
    "FreeEnergyDecoration",
    "PhysicsProduct",
    "route_net_delta_g",
]


# ======================================================================================
# The additive free-energy functor G: Process -> (ℝ, +, ≤)
# ======================================================================================
def route_net_delta_g(route: "object", *, thermo=None, temperature_k: float | None = None) -> float | None:
    """Σ of the per-step ``Δ_rG`` over a route -- the additive free-energy functor (Hess's law).

    Returns ``None`` (fail-closed) if ANY step has no sourced/derivable thermodynamic data, so a partial
    sum can never masquerade as a route drive.  By Hess's law this equals the ΔG of the route's single net
    reaction (the shared intermediates cancel); :func:`~tests` pins that equality as the functoriality law.
    """
    from .feasibility import DEFAULT_THERMO, feasibility_of_step

    table = DEFAULT_THERMO if thermo is None else thermo
    total = 0.0
    for step in route.steps:
        result = feasibility_of_step(step, thermo=table, temperature_k=temperature_k)
        if result.delta_g_kj is None:
            return None
        total += result.delta_g_kj
    return total


# ======================================================================================
# The free-energy decoration -- a SECOND instance of the open_core monoidal slot
# ======================================================================================
@dataclass(frozen=True)
class FreeEnergyDecoration(Decoration):
    """An additive real free-energy drive riding the ``open_core`` decoration slot (kJ/mol).

    ``then_combine`` and ``tensor_combine`` are both real addition -- a homomorphic SUM over the generators,
    so it is gluing-independent and interchange-invariant (the same reason conservation is a valid
    decoration; see ``a-quotient-must-be-a-congruence``).  ``None`` is the fail-closed "unknown drive"
    element: combining anything with an unknown yields unknown, so a route with one unsourced step carries
    an unknown net drive rather than a misleading partial sum.
    """

    delta_g_kj: float | None = 0.0

    @classmethod
    def identity(cls) -> "FreeEnergyDecoration":
        return cls(0.0)

    def _add(self, other: "FreeEnergyDecoration") -> "FreeEnergyDecoration":
        if type(other) is not FreeEnergyDecoration:
            raise DiagramCompositionError("free-energy decorations only combine with each other")
        if self.delta_g_kj is None or other.delta_g_kj is None:
            return FreeEnergyDecoration(None)
        return FreeEnergyDecoration(self.delta_g_kj + other.delta_g_kj)

    def then_combine(self, other: Decoration) -> Decoration:
        return self._add(other)  # type: ignore[arg-type]

    def tensor_combine(self, other: Decoration) -> Decoration:
        return self._add(other)  # type: ignore[arg-type]

    @property
    def is_known(self) -> bool:
        return self.delta_g_kj is not None


# ======================================================================================
# The Pareto product of the two functors -- no scalar collapse ("favorable != fast")
# ======================================================================================
@dataclass(frozen=True)
class PhysicsProduct:
    """A point in the product order of the two physics functors: ``(Δ_rG drive, survival fraction)``.

    ``delta_g_kj`` -- the additive thermodynamic drive (kJ/mol; MORE NEGATIVE is more favorable).
    ``surviving_fraction`` -- the multiplicative kinetic survival in ``[0, 1]`` (HIGHER is better).

    :meth:`dominates` is the Pareto partial order: ``self`` dominates ``other`` iff it is at least as good on
    BOTH axes and strictly better on at least one.  There is deliberately NO scalar score: a favorable but
    fragile route and a marginal but durable one are **incomparable** (``dominates`` is False both ways).
    An unknown (``None``) axis makes the point incomparable to everything (fail-closed) -- an unmeasured
    drive or survival never lets a route dominate or be dominated on a value we do not have.
    """

    delta_g_kj: float | None
    surviving_fraction: float | None

    @property
    def is_complete(self) -> bool:
        """True iff both axes are known (a prerequisite for participating in the dominance order)."""
        return self.delta_g_kj is not None and self.surviving_fraction is not None

    def dominates(self, other: "PhysicsProduct") -> bool:
        if type(other) is not PhysicsProduct:
            raise TypeError("dominates expects another PhysicsProduct")
        if not (self.is_complete and other.is_complete):
            return False
        # lower ΔG is better; higher survival is better
        at_least_as_good = (
            self.delta_g_kj <= other.delta_g_kj and self.surviving_fraction >= other.surviving_fraction
        )
        strictly_better = (
            self.delta_g_kj < other.delta_g_kj or self.surviving_fraction > other.surviving_fraction
        )
        return at_least_as_good and strictly_better

    def comparable_to(self, other: "PhysicsProduct") -> bool:
        """True iff the two are Pareto-ordered (one dominates), False iff incomparable."""
        return self.dominates(other) or other.dominates(self)


def pareto_optimal(objectives: tuple[PhysicsProduct, ...]) -> tuple[int, ...]:
    """Indices of the non-dominated objectives among those with a COMPLETE objective.

    A point with an unknown (``None``) axis is never non-dominated (its objective is incomparable to
    everything -- we do not certify a point on physics we do not have).  Ties are kept: two distinct
    points with identical objectives never dominate each other (dominance requires a strict axis), so
    both survive.  The frontier's index order follows the input order.
    """
    complete = [i for i, obj in enumerate(objectives) if obj.is_complete]
    return tuple(
        i
        for i in complete
        if not any(objectives[j].dominates(objectives[i]) for j in complete if j != i)
    )
