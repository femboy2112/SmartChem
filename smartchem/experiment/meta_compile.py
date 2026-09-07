"""Move-1 keystone Rung D: closing an open diagram IS compiling an underdetermined spec.

The keystone thesis (``docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md``, and the
[[meta-compiler-is-the-long-term-goal]] destination): an open morphism with an unfilled port is an
*underdetermined specification*; **closing the diagram is compiling it**.  This rung makes that literal.

``compile_open(target, ...)`` treats "synthesise this target from available stock" as the open spec
(the target is the diagram's one unfilled output).  It **closes** the spec with the shipped bounded
route SEARCH (``routes.search_routes`` -- the transform algebra through the unchanged core), projects
each candidate onto the open-diagram backbone with **Rung C** (``ExperimentRoute.open()``), and ranks
the resulting *closed* (saturated, conserving) diagrams by the **M2-FP** functorial objective -- the
Pareto product of the additive free-energy drive ``route_net_delta_g`` and the multiplicative survival
``verify_composability(...).route_surviving_fraction`` (:class:`PhysicsProduct`, "favorable != fast",
no scalar collapse).

This is the load-bearing CALL SITE for Rungs B/C and M2-FP: an ``OpenChemDiagram`` is produced,
saturated, net-conservation-checked, and scored by the two physics functors -- the backbone is used,
not decorative (the standing zero-call-sites discipline).  Nothing is rewritten: the search, ranking
inputs, projection and objective are all shipped pieces, orchestrated.

Fail-closed throughout: a target the search cannot close yields NO closures (an honest UNCOMPILABLE,
never a fabricated route); a closure whose physics is not fully sourced has an INCOMPLETE objective and
is listed but never physics-ranked above a closure whose objective is known (the Pareto frontier only
admits complete objectives).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..category import Molecule, Reaction
from .composability import DEFAULT_KINETICS, DEFAULT_STABILITY, verify_composability
from .functorial_physics import PhysicsProduct, pareto_optimal, route_net_delta_g
from ..transform_provider import DEFAULT_TRANSFORM_REGISTRY
from .routes import search_routes
from .step import ExperimentRoute

__all__ = [
    "ClosedCompilation",
    "MetaCompilation",
    "compile_open",
    "pareto_frontier",
]


@dataclass(frozen=True)
class ClosedCompilation:
    """One closed synthesis: a candidate ``ExperimentRoute`` closing the spec, plus its physics objective.

    The closed open-diagram (``diagram``), its conserving net reaction (``net_reaction``) and its M2-FP
    objective (``objective``) are all derived from the route -- so a compilation IS a closed morphism the
    backbone can hand back, and its objective is the pair the meta-compiler ranks on.
    """

    route: ExperimentRoute
    net_delta_g_kj: float | None
    surviving_fraction: float | None

    def __post_init__(self) -> None:
        # A closure is DERIVED FROM a route; a route-less compilation is a half-built object whose
        # .diagram/.net_reaction() would raise a raw AttributeError (adversarial fold).  Refuse it -- the
        # Pareto math is tested directly on PhysicsProduct via functorial_physics.pareto_optimal.
        if type(self.route) is not ExperimentRoute:
            raise TypeError("ClosedCompilation.route must be an ExperimentRoute")

    @property
    def objective(self) -> PhysicsProduct:
        return PhysicsProduct(self.net_delta_g_kj, self.surviving_fraction)

    @property
    def diagram(self):
        """The closed open-diagram of this compilation (Rung C projection)."""
        return self.route.open()

    def net_reaction(self) -> Reaction:
        """The conserving overall equation of the closed diagram (fails closed if not saturated)."""
        return self.route.open().net_reaction()


def _closed_of(route: ExperimentRoute, *, thermo, stability, kinetics) -> ClosedCompilation:
    delta_g = route_net_delta_g(route, thermo=thermo)
    survival = verify_composability(route, stability=stability, kinetics=kinetics).route_surviving_fraction
    return ClosedCompilation(route, delta_g, survival)


def pareto_frontier(closures: tuple[ClosedCompilation, ...]) -> tuple[ClosedCompilation, ...]:
    """The non-dominated closures on the M2-FP objective (only those with a COMPLETE objective).

    A closure with an unknown ΔG or survival axis is never on the frontier (its objective is incomparable
    -- we do not certify a route on physics we do not have).  Order within the frontier is the input order.
    Delegates the dominance math to :func:`functorial_physics.pareto_optimal` (tested there directly).
    """
    keep = pareto_optimal(tuple(c.objective for c in closures))
    return tuple(closures[i] for i in keep)


@dataclass(frozen=True)
class MetaCompilation:
    """The result of compiling an open spec: every closure the search found, and the Pareto-best subset.

    ``closures`` is every closed synthesis (search order); ``frontier`` is the Pareto-non-dominated subset
    on the functorial objective (empty when no closure has a fully-sourced objective -- honest, not a guess).
    An empty ``closures`` is an UNCOMPILABLE spec (the search closed nothing), surfaced, never faked.
    """

    target: Molecule
    closures: tuple[ClosedCompilation, ...]

    @property
    def frontier(self) -> tuple[ClosedCompilation, ...]:
        """The strict TWO-axis Pareto frontier (ΔG x survival) -- non-empty only where both are sourced."""
        return pareto_frontier(self.closures)

    @property
    def by_free_energy(self) -> tuple[ClosedCompilation, ...]:
        """Closures with a known net ΔG, most thermodynamically favorable (most negative) first.

        The single-axis projection of the objective onto the free-energy functor -- useful (and honest)
        when survival is unsourced for every closure, the common case for a fresh search.  Closures with
        an UNKNOWN net ΔG are omitted (never ranked on physics we do not have); read ``closures`` for all.
        """
        known = [c for c in self.closures if c.net_delta_g_kj is not None]
        return tuple(sorted(known, key=lambda c: c.net_delta_g_kj))

    @property
    def is_compilable(self) -> bool:
        return bool(self.closures)


def compile_open(
    target: Molecule,
    *,
    reagents: tuple[Molecule, ...] = (),
    available: tuple[Molecule, ...] = (),
    commodities: tuple[Molecule, ...] = (),
    max_depth: int = 2,
    max_routes: int = 100,
    cut_budget: int = 20_000,
    registry=DEFAULT_TRANSFORM_REGISTRY,
    thermo=None,
    stability=DEFAULT_STABILITY,
    kinetics=DEFAULT_KINETICS,
) -> MetaCompilation:
    """Compile the open spec "synthesise ``target`` from stock" by CLOSING it (search -> project -> rank).

    Reuses the shipped bounded route search to enumerate closures, projects each onto a closed
    ``OpenChemDiagram`` (Rung C), and scores it by the M2-FP Pareto objective (ΔG drive x survival).
    Bounded by the search's own ``max_depth``/``max_routes``/``cut_budget`` (fail-closed: an
    over-budget or unreachable spec simply yields fewer or no closures).
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a smartchem.category.Molecule")
    result = search_routes(
        target,
        reagents=reagents,
        available=available,
        commodities=commodities,
        max_depth=max_depth,
        max_routes=max_routes,
        cut_budget=cut_budget,
        registry=registry,
    )
    closures = tuple(
        _closed_of(route, thermo=thermo, stability=stability, kinetics=kinetics) for route in result.routes
    )
    return MetaCompilation(target, closures)
