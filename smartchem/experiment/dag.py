"""M4 -- convergent synthesis DAGs: two (or more) sub-routes feeding one step.

An :class:`~smartchem.experiment.step.ExperimentRoute` is LINEAR -- a total order where each step's target is
the next step's input -- and E5 enumeration recurses on exactly ONE missing precursor.  A real convergent
synthesis is not a chain: you make intermediate A down one branch and intermediate B down another, then a
single step consumes BOTH.  That is a directed acyclic graph, and the linear route is just the special case
where the DAG happens to be a path.

This module adds the DAG *without disturbing the linear route* (whose invariant is load-bearing across the
suite).  A :class:`SynthesisDAG` composes existing certified :class:`ExperimentStep` nodes and REUSES every
rung: conservation is each step's own E0 certificate; composability is E1's ``_judge_transition`` applied to
each DAG EDGE (a producer->consumer handoff); feasibility (M1) and equilibrium (M2) are per-step and
route-shape-agnostic, so they map over the nodes and aggregate the same worst-dominated way the linear route
verdicts do.  The one genuinely new computation is the **convergent ceiling**: the limiting-reagent maximum
propagated through the DAG in topological order, where a convergent step is limited by whichever of its
several intermediate inputs (or external reagents) is scarcest -- the exact E2 kernel
(:func:`~smartchem.experiment.ceiling.stoichiometric_ceiling`), iterated over a partial order instead of a chain.

The invariants (a synthesis, not an arbitrary graph)
----------------------------------------------------
* **distinct targets** -- each intermediate is produced by exactly one step (a branch that makes A is one
  node; you do not make the same A two different ways in one DAG);
* **acyclic** -- no step (transitively) consumes its own output;
* **exactly one sink** -- one step whose target no other step consumes: the DAG's final target (a synthesis
  makes ONE thing);
* **connected to the sink** -- every step's product is used downstream (no orphan branch making something
  nothing consumes).
A DAG violating any of these is refused at construction, exactly as a non-conserving step is refused.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from ..open_chem_diagram import OpenChemDiagram
    from ..process_constraints import ProcessBounds, ProcessFit

from ..category import Molecule
from ..contracts import Digestible
from ..data.kinetics import DEFAULT_KINETICS as _DEFAULT_DECOMP_KINETICS, KineticTable
from ..data.stability import DEFAULT_STABILITY, StabilityTable
from ..data.thermo import DEFAULT_THERMO, ThermoTable
from .bucket import Bucket, Quantity
from .ceiling import CeilingError, StoichiometricCeiling, _verify_balances, stoichiometric_ceiling
from .composability import Transition, TransitionStatus, _judge_transition, _survival_product
from .exact_lp import LPUnbounded, maximize
from .equilibrium import EquilibriumExtent, StepEquilibrium, equilibrium_of_step
from .feasibility import FeasibilityDirection, StepFeasibility, feasibility_of_step
from .kinetics import DEFAULT_KINETICS, kinetics_of_step, worst_regime
from .selectivity import DEFAULT_SELECTIVITY, SelectivityStatus, selectivity_of_step
from .step import ExperimentStep

__all__ = [
    "DAG_SCHEMA",
    "DAGError",
    "ShoppingUnderdeterminedError",
    "SynthesisDAG",
    "DAGCeiling",
    "DAGFlow",
    "DAGShoppingRequirement",
    "DAGComposability",
    "DAGVerification",
    "DAGThermoRollup",
    "dag_ceiling",
    "dag_shopping_requirement",
    "dag_composability",
    "dag_process_fit",
    "verify_dag",
    "dag_thermo_rollup",
]

DAG_SCHEMA = "smartchem.experiment/synthesis-dag-v1"


class DAGError(ValueError):
    """A proposed synthesis DAG is not an admissible convergent structure."""


def _ident(m: Molecule) -> str:
    # CANON-KEKULE-01 (item 3): resonance-canonical, shared with routes/step/compilation_ir via resonance_identity,
    # so a convergent DAG keys intermediates on the SAME identity the search matches on.
    from ..smiles import resonance_identity
    return resonance_identity(m)


def _producers(steps: tuple[ExperimentStep, ...]) -> dict[str, int]:
    """Map each step's target identity to its (unique) producing step index; refuse duplicate targets."""
    out: dict[str, int] = {}
    for i, step in enumerate(steps):
        key = _ident(step.target)
        if key in out:
            raise DAGError(
                f"two steps produce the same target {step.target!r}; a DAG makes each intermediate once "
                f"(steps {out[key] + 1} and {i + 1})"
            )
        out[key] = i
    return out


def _edges(
    steps: tuple[ExperimentStep, ...], producers: dict[str, int]
) -> tuple[tuple[int, int, Molecule], ...]:
    """The intermediate-flow edges: ``(producer_index, consumer_index, intermediate)`` for each distinct
    produced intermediate a step consumes.  Deduplicated by ``(producer, consumer, intermediate)``."""
    seen: set[tuple[int, int, str]] = set()
    out: list[tuple[int, int, Molecule]] = []
    for j, step in enumerate(steps):
        for r in step.reactants:
            key = _ident(r)
            i = producers.get(key)
            if i is None or i == j:
                continue  # an external leaf input, or a step's own target -- not an internal edge
            tag = (i, j, key)
            if tag in seen:
                continue
            seen.add(tag)
            out.append((i, j, r))
    return tuple(out)


def _sink_index(steps: tuple[ExperimentStep, ...]) -> int:
    """The unique step whose target no OTHER step consumes -- the DAG's final target; refuse if not exactly one."""
    def consumed_by_another(i: int) -> bool:
        target_key = _ident(steps[i].target)
        return any(
            _ident(r) == target_key
            for j, other in enumerate(steps) if j != i
            for r in other.reactants
        )

    sinks = [i for i in range(len(steps)) if not consumed_by_another(i)]
    if len(sinks) != 1:
        raise DAGError(
            f"a synthesis DAG must have exactly one final target (a step whose product nothing else "
            f"consumes); found {len(sinks)}. A structure with several unconsumed products is not one synthesis"
        )
    return sinks[0]


def _topological_order(n: int, edges: tuple[tuple[int, int, Molecule], ...]) -> tuple[int, ...]:
    """Kahn's algorithm over the step-index graph (producer -> consumer); refuse a cycle."""
    indeg = [0] * n
    succ: list[list[int]] = [[] for _ in range(n)]
    for i, j, _m in edges:
        indeg[j] += 1
        succ[i].append(j)
    queue = sorted(k for k in range(n) if indeg[k] == 0)
    order: list[int] = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for nxt in succ[node]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
        queue.sort()
    if len(order) != n:
        raise DAGError(
            "the synthesis DAG contains a cycle (a step transitively consumes its own output); it is not a "
            "directed ACYCLIC graph"
        )
    return tuple(order)


def _reaches(n: int, edges: tuple[tuple[int, int, Molecule], ...], sink: int) -> set[int]:
    """The set of step indices from which the ``sink`` is reachable by following producer->consumer edges."""
    succ: list[list[int]] = [[] for _ in range(n)]
    for i, j, _m in edges:
        succ[i].append(j)
    reaching = {sink}
    changed = True
    while changed:
        changed = False
        for i in range(n):
            if i in reaching:
                continue
            if any(j in reaching for j in succ[i]):
                reaching.add(i)
                changed = True
    return reaching


@dataclass(frozen=True)
class SynthesisDAG(Digestible):
    """A convergent synthesis as a DAG of certified steps: branches produce intermediates, a step joins them.

    The linear :class:`~smartchem.experiment.step.ExperimentRoute` is the special case where this DAG is a
    path; :attr:`is_convergent` is true exactly when some step is fed by two or more produced intermediates.
    """

    schema_version: str
    steps: tuple[ExperimentStep, ...]

    def __post_init__(self) -> None:
        if self.schema_version != DAG_SCHEMA:
            raise DAGError(f"schema_version must be exactly {DAG_SCHEMA!r}")
        if type(self.steps) is not tuple or not self.steps or any(
            type(s) is not ExperimentStep for s in self.steps
        ):
            raise DAGError("a DAG must be a non-empty tuple of ExperimentStep values")
        producers = _producers(self.steps)               # refuses duplicate targets
        edges = _edges(self.steps, producers)
        sink = _sink_index(self.steps)                    # refuses !=1 final target
        _topological_order(len(self.steps), edges)        # refuses a cycle
        reaching = _reaches(len(self.steps), edges, sink)
        if len(reaching) != len(self.steps):
            orphans = [i + 1 for i in range(len(self.steps)) if i not in reaching]
            raise DAGError(
                f"steps {orphans} do not reach the final target; a DAG may not carry an orphan branch that "
                f"makes something no downstream step consumes"
            )

    # -- structure -------------------------------------------------------------------------------------
    @property
    def _producer_map(self) -> dict[str, int]:
        return _producers(self.steps)

    @property
    def edges(self) -> tuple[tuple[int, int, Molecule], ...]:
        """The producer->consumer intermediate-flow edges as ``(producer_index, consumer_index, molecule)``."""
        return _edges(self.steps, self._producer_map)

    @property
    def sink_index(self) -> int:
        return _sink_index(self.steps)

    @property
    def final_target(self) -> Molecule:
        return self.steps[self.sink_index].target

    def topological_order(self) -> tuple[ExperimentStep, ...]:
        """The steps in a valid dependency order (every producer before its consumers)."""
        return tuple(self.steps[i] for i in _topological_order(len(self.steps), self.edges))

    @property
    def convergence_points(self) -> tuple[int, ...]:
        """Indices of steps fed by two or more distinct produced intermediates (the joins)."""
        indeg: Counter = Counter(j for _i, j, _m in self.edges)
        return tuple(sorted(j for j, d in indeg.items() if d >= 2))

    @property
    def is_convergent(self) -> bool:
        """True iff some step joins two or more produced intermediates (else the DAG is a linear chain)."""
        return bool(self.convergence_points)

    @property
    def fanout_points(self) -> tuple[int, ...]:
        """Producer indices whose single produced intermediate is consumed by TWO OR MORE distinct steps (a fan-out).

        The structural DUAL of :attr:`convergence_points` (a step's in-degree -- the joins): this is a producer's
        out-degree -- one produced intermediate feeding several consumers.  A fan-out is an admissible STRUCTURE
        whose shared intermediate the naive limiting-reagent propagation cannot conserve (it would mint copies).
        This is a purely STRUCTURAL descriptor, not a completeness claim: :func:`dag_ceiling` does NOT rely on it to
        decide when to conserve (a shared leaf, or a reused by-product, also mints yet is invisible here -- this
        sees only produced-intermediate edges).  Instead ``dag_ceiling`` ALWAYS computes the exact conserved
        max-yield LP for the number, whatever the shape (DAG-FLOW-01).
        """
        consumers: dict[int, set[int]] = {}
        for i, j, _m in self.edges:
            consumers.setdefault(i, set()).add(j)
        return tuple(sorted(i for i, js in consumers.items() if len(js) >= 2))

    @property
    def leaf_inputs(self) -> tuple[Molecule, ...]:
        """The reactant molecules produced by no step -- the external starting materials and reagents."""
        producers = self._producer_map
        out: dict[str, Molecule] = {}
        for step in self.steps:
            for r in step.reactants:
                key = _ident(r)
                if key not in producers:
                    out.setdefault(key, r)
        return tuple(out.values())

    def open(self) -> "OpenChemDiagram":
        """Project the convergent synthesis onto one open chemistry diagram (Move-1 keystone Rung C).

        Each step is a reaction hyperedge; the DAG's ``edges`` name exactly the internal gluings, so
        parallel branches ride ``tensor`` and the diagram's provenance is the branching causal DAG (P4,
        occurrence-aware over distinct steps).  Leaf inputs and byproducts stay EXTERNAL; a conserving
        DAG yields a saturated CONSERVING diagram whose
        :meth:`~smartchem.open_chem_diagram.OpenChemDiagram.net_reaction` is the overall balanced
        equation.  A convergent DAG has no single linear ``Reaction.path`` (``close()`` refuses it -- the
        honest boundary).  Lazily imported to avoid an import cycle.
        """
        from ..open_chem_diagram import OpenChemDiagram

        return OpenChemDiagram.from_dag(self)

    @classmethod
    def of(cls, *steps: ExperimentStep) -> "SynthesisDAG":
        return cls(DAG_SCHEMA, tuple(steps))

    def __repr__(self) -> str:
        shape = "convergent" if self.is_convergent else "linear"
        return f"SynthesisDAG({shape}, {len(self.steps)} steps -> {self.final_target!r})"


# -- E2 over a DAG: the convergent ceiling --------------------------------------------------------------
@dataclass(frozen=True)
class DAGFlow(Digestible):
    """The conserved max-yield LP solution over a fan-out DAG (DAG-FLOW-01's real quantity-flow accounting).

    Used when a shared BOUNDED reactant couples the steps -- a produced intermediate consumed by two or more
    steps, or a finite leaf reagent shared across them.  There the naive per-step limiting-reagent propagation
    would MINT (it reads the shared reactant at full amount for every consumer), and a single per-step
    ``limiting_reactant`` would be a FALSE local claim about a GLOBAL optimum: the true constraint is how a
    shared reactant is allocated across its competing consumers.  So the ceiling is the maximum of the final
    target over ALL conserved allocations -- a linear program, solved exactly (:mod:`~smartchem.experiment.exact_lp`).
    Choosing the yield-maximizing allocation invents no policy: a *ceiling* is by definition the best case over
    every feasible allocation, so the LP's optimum IS the honest 100%-efficiency upper bound.

    :attr:`step_extents` is each step's reaction EXTENT (mol of that reaction run) at the optimum, in topological
    order; the mol of a step's target produced is ``extent * (target's product multiplicity)``.
    :attr:`binding_reagents` names the FED reactants whose charged supply is fully consumed at the optimum -- a
    factual observation about the yield-maximizing operating point, not a claim that each uniquely bounds the yield.
    """

    step_extents: tuple[tuple[ExperimentStep, Fraction], ...]  # topological order; mol of reaction run per step
    binding_reagents: tuple[Molecule, ...]                     # fed reactants fully consumed at the optimum


@dataclass(frozen=True)
class DAGCeiling(Digestible):
    """The exact 100%-efficiency conserved ceiling of a convergent DAG.

    :attr:`final_target_mol` is ALWAYS the exact conserved max-yield LP number (it counts every produced species,
    by-products included, so it never mints, whatever the DAG's shape).  :attr:`per_step` carries the naive
    limiting-reagent propagation's honest per-step breakdown (each step limited by its scarcest input, a join
    taking the min over its branches) -- but ONLY for a simple tree/chain, where that propagation provably equals
    the LP; there :attr:`flow` is ``None``.  On any DAG where the propagation would mint or over-report (a shared
    reactant, or a reused by-product), it is discarded: :attr:`per_step` is empty and :attr:`flow` (a
    :class:`DAGFlow`) carries the LP solution, because a single per-step ``limiting_reactant`` would misrepresent
    the coupled optimum.  Either way the number is ``CONSERVATION`` -- an exact rational upper bound, never a yield.
    """

    dag: SynthesisDAG
    per_step: tuple[StoichiometricCeiling, ...]  # topological order; () when a shared reactant coupled the solve
    final_target_mol: Fraction
    flow: "DAGFlow | None" = None                # the LP solution when a shared bounded reactant coupled the steps

    @property
    def quantity(self) -> Quantity:
        if self.flow is not None:
            provenance = (
                "conserved max-yield LP over the fan-out (a shared reactant allocated across its competing "
                "consumers to maximize the final target); exact rational"
            )
        else:
            provenance = (
                "limiting-reagent conservation propagated through the DAG; exact rational, per-step kernel-checked"
            )
        return Quantity(
            "max final target (100% efficiency, convergent)", str(self.final_target_mol), "mol",
            Bucket.CONSERVATION, provenance,
        )

    def explain(self) -> str:
        if self.flow is not None:
            binding = ", ".join(repr(m) for m in self.flow.binding_reagents) or "none"
            lines = [
                f"convergent ceiling (conserved max-yield LP): {self.final_target_mol} mol "
                f"{self.dag.final_target!r} at 100% efficiency [CONSERVATION -- exact rational; a shared reactant "
                f"is split across its consumers to maximize yield; fed reactants fully consumed: {binding}]"
            ]
            for step, extent in self.flow.step_extents:
                lines.append(f"  {step.target!r} step at extent {extent} mol")
            return "\n".join(lines)
        lines = [
            f"convergent ceiling: {self.final_target_mol} mol {self.dag.final_target!r} at 100% efficiency "
            f"[CONSERVATION -- an idealised upper bound over the whole convergent synthesis]"
        ]
        for c in self.per_step:
            lines.append(f"  <= {c.max_target_mol} mol {c.step.target!r} (limited by {c.limiting_reactant!r})")
        return "\n".join(lines)


def _max_yield_lp(
    dag: SynthesisDAG, feed: Mapping[Molecule, "int | Fraction"]
) -> "tuple[Fraction, DAGFlow]":
    """The conserved max-yield ceiling of ``dag`` via the exact LP -- the CORRECT number for ANY DAG shape.

    Maximize the final target's net production subject to per-species conservation: for every finite-bounded
    species X (a fed leaf, OR any species PRODUCED by a step -- an intermediate target OR a by-product) the total
    CONSUMED across steps must not exceed the total PRODUCED plus what was fed.  Reaction extents are >= 0.  A
    species that is only an excess leaf (not produced, not fed) imposes no constraint -- it is unbounded.  The
    optimum is the exact best-case ceiling: no allocation policy is invented, because a ceiling is by definition
    the maximum over all conserved allocations.  Crucially this counts EVERY produced species (by-products too),
    so it is the honest answer even when a by-product is reused downstream -- the case the naive propagation mints.
    Returns ``(value, flow)``; raises :class:`CeilingError` if the target has no finite conserved ceiling.
    """
    steps = dag.topological_order()
    for step in steps:
        _verify_balances(step)  # two agreeing derivations (ceiling module discipline), not the step's own say-so
    n = len(steps)
    cons = [Counter(_ident(m) for m in s.reactants) for s in steps]
    prod = [Counter(_ident(m) for m in s.products) for s in steps]
    by_ident: dict[str, Molecule] = {}
    for step in steps:
        for m in (*step.reactants, *step.products):
            by_ident.setdefault(_ident(m), m)
    produced = set().union(*(set(p) for p in prod)) if prod else set()
    feed_by: dict[str, Fraction] = {}
    for m, amount in feed.items():
        if isinstance(amount, bool) or not isinstance(amount, (int, Fraction)):
            raise CeilingError("feed amounts must be exact int or Fraction (mol)")
        if amount < 0:
            raise CeilingError(f"feed amount for {m!r} must be non-negative")
        feed_by[_ident(m)] = feed_by.get(_ident(m), Fraction(0)) + Fraction(amount)

    final_key = _ident(dag.final_target)
    # constrained species: finite-bounded (produced -- target OR by-product -- or fed), excluding the sink target
    # (its net production is the objective).  A by-product is `produced`, so it IS constrained -- the fold that
    # closes the mint the naive propagation left open (it credited only step targets, never by-products).
    constrained = [k for k in sorted(by_ident) if k != final_key and (k in produced or k in feed_by)]
    A = [[cons[s].get(k, 0) - prod[s].get(k, 0) for s in range(n)] for k in constrained]
    b = [feed_by.get(k, Fraction(0)) for k in constrained]
    c = [prod[s].get(final_key, 0) - cons[s].get(final_key, 0) for s in range(n)]
    try:
        value, extents = maximize(c, A, b)
    except LPUnbounded:
        raise CeilingError(
            "the DAG's final target is not bounded by any feed on a sink-reaching path (every such reactant is "
            "charged in excess); there is no finite conserved ceiling. Charge a finite amount of a reactant that "
            "limits the target so the CONSERVATION bound is a real number, not infinity."
        )
    # Self-check independent of the simplex's own bookkeeping: no species is over-consumed (no mint, no deficit).
    # This is exactly the conservation the never-decrementing cache used to violate; assert it on the CLAIMED point.
    for k in constrained:
        consumed = sum(cons[s].get(k, 0) * extents[s] for s in range(n))
        supplied = feed_by.get(k, Fraction(0)) + sum(prod[s].get(k, 0) * extents[s] for s in range(n))
        if consumed > supplied:  # pragma: no cover -- a simplex/formulation bug; loud, never silently minted
            raise AssertionError(
                f"max-yield LP violated conservation for {by_ident[k]!r} (consumed {consumed} > supplied "
                f"{supplied}); refusing to report a minted ceiling"
            )
    # binding_reagents: FED reactants whose charged supply is fully consumed at the optimum (a factual observation).
    binding = tuple(
        by_ident[k] for k in constrained
        if k in feed_by and feed_by[k] > 0
        and sum(cons[s].get(k, 0) * extents[s] for s in range(n)) == feed_by[k]
    )
    step_extents = tuple((steps[s], extents[s]) for s in range(n))
    return value, DAGFlow(step_extents, binding)


def _propagate(dag: SynthesisDAG, feed: Mapping[Molecule, "int | Fraction"]) -> "tuple[tuple[StoichiometricCeiling, ...], Fraction]":
    """The limiting-reagent maximum propagated through the DAG in topological order -- each step limited by its
    scarcest input, a JOIN taking the min over its branches.  Returns ``(per_step, final)``.

    This is FAITHFUL only for a simple tree/chain (no shared reactant, no reused by-product): its ``available``
    cache credits ONLY each step's TARGET, never a by-product, and never decrements a shared reactant -- so on a
    coupled DAG it MINTS or over-reports.  It is therefore never trusted for the number on its own; :func:`dag_ceiling`
    keeps it only for the per-step breakdown, and only after confirming its number matches the exact LP.
    """
    available: dict[str, tuple[Molecule, Fraction]] = {}
    for m, amount in feed.items():
        available[_ident(m)] = (m, Fraction(amount))
    per: list[StoichiometricCeiling] = []
    for step in dag.topological_order():
        step_feed: dict[Molecule, Fraction] = {}
        for r in step.reactants:
            key = _ident(r)
            if key in available:
                step_feed[available[key][0]] = available[key][1]
        ceiling = stoichiometric_ceiling(step, step_feed)
        per.append(ceiling)
        available[_ident(step.target)] = (step.target, ceiling.max_target_mol)
    return tuple(per), available[_ident(dag.final_target)][1]


def dag_ceiling(dag: SynthesisDAG, feed: Mapping[Molecule, "int | Fraction"]) -> DAGCeiling:
    """The exact conserved 100%-efficiency ceiling of ``dag`` for external ``feed`` amounts (mol per leaf input).

    ``feed`` covers the leaf inputs (:attr:`SynthesisDAG.leaf_inputs`) you want counted; a leaf absent from
    ``feed`` is charged in EXCESS (never limiting).  Intermediates are supplied automatically.

    The NUMBER is ALWAYS the exact conserved max-yield LP (:func:`_max_yield_lp`), which counts every produced
    species -- intermediates AND by-products -- and so never mints, whatever the DAG's shape (linear, convergent,
    fan-out, or a reused by-product).  A DAG whose target is bounded by no feed on any sink-reaching path has no
    finite ceiling and raises :class:`CeilingError`.

    The per-step breakdown is a DISPLAY convenience: the naive limiting-reagent propagation
    (:func:`_propagate`) gives an honest per-step ``limiting_reactant`` ONLY for a simple tree/chain, where it
    provably equals the LP.  So :attr:`DAGCeiling.per_step` is exposed ONLY when the propagation's number MATCHES
    the LP (a per-call differential check -- two agreeing derivations); on any DAG where they differ (a shared or
    by-product-coupled DAG the propagation would mint on) the propagation is discarded and :attr:`DAGCeiling.flow`
    carries the LP solution instead, because a single per-step ``limiting_reactant`` would misrepresent the
    coupled optimum.  Either way ``final_target_mol`` is the LP's exact conserved number.
    """
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    value, flow = _max_yield_lp(dag, feed)          # the exact conserved number, for ANY DAG shape
    try:
        per_step, prop_final = _propagate(dag, feed)
    except CeilingError:
        per_step, prop_final = (), None             # the propagation over-refused; the LP is the honest answer
    if prop_final == value:                          # exact-rational agreement: the per-step breakdown is faithful
        return DAGCeiling(dag, per_step, value, flow=None)
    return DAGCeiling(dag, (), value, flow=flow)     # propagation would mint/over-report -> the LP wins, flow only


# -- the inverse of the ceiling: the quantity-aware shopping requirement (SHOP-LEAF-02) -----------------
class ShoppingUnderdeterminedError(DAGError):
    """The external-purchase requirement is not a single conserved number.

    A species is produced by MORE THAN ONE step (a step's target is ALSO a by-product of another step), so how
    much to buy depends on how that shared internal supply is allocated across its sources -- a *range*, not a
    fabricated number.  Pinning one value needs a cost/allocation policy (the SHOP-LEAF-02 follow-on, tied to
    ``COST-VEC-01``); until then this refuses rather than invent, exactly as ``dag_ceiling`` refuses an unbounded
    target.
    """


@dataclass(frozen=True)
class DAGShoppingRequirement(Digestible):
    """The exact conserved EXTERNAL-PURCHASE requirement to make ``final_target_mol`` of the DAG's final target.

    The inverse of :func:`dag_ceiling` (feed -> max target) for the route AS GIVEN: to make a desired amount of the
    final target buying only EXTERNAL LEAVES and making every intermediate INTERNALLY, how much of each input must
    be acquired?  Making all intermediates internally, the extents are determined -- each intermediate has a unique
    NET producer, so producing ``final_target_mol`` forces every step's extent (a self-consuming/autocatalytic step's
    extent is the internal-make FLOOR), and the per-species net (consumed minus produced, by-products CREDITED) is
    exact.  This is NOT the globally-cheapest sourcing: buying an intermediate to bypass a step (which ``dag_ceiling``
    would accept as a feed) is the deferred PURCHASED-SUPPLEMENT feature, not this brick.  Where a target species has
    MORE THAN ONE net producer the buy is a genuine range and it refuses (see :func:`dag_shopping_requirement`).

    :attr:`requirements` are the species whose consumption exceeds internal production -- what a chemist must
    BUY -- each a 100%-EFFICIENCY LOWER BOUND FOR THIS ROUTE (a real yield < 100% needs MORE; a conserved floor on
    purchase, never a predicted amount, and never a claim that no cheaper alternative sourcing exists).
    :attr:`co_products` are species produced in surplus (the final target excluded -- it is THE product, not a
    co-product).  :attr:`step_extents` is each reaction's extent (mol run) at this operating point, in topological
    order.
    """

    dag: SynthesisDAG
    final_target_mol: Fraction
    step_extents: tuple[tuple[ExperimentStep, Fraction], ...]   # topological order; mol of each reaction run
    requirements: tuple[tuple[Molecule, Fraction], ...]         # external species -> mol to buy (net consumed > 0)
    co_products: tuple[tuple[Molecule, Fraction], ...]          # surplus species (net produced > 0), excl. final

    @property
    def quantity(self) -> Quantity:
        return Quantity(
            f"external purchase to make {self.final_target_mol} mol {self.dag.final_target!r} (100% efficiency)",
            str(self.final_target_mol), "mol", Bucket.CONSERVATION,
            "conserved inverse of the max-yield flow for the route as given (intermediates made internally): "
            "extents forced by the target amount (one net producer per intermediate), by-products credited; exact "
            "rational, a 100%-efficiency LOWER BOUND on purchase for THIS route (not the cheapest alternative sourcing)",
        )

    def explain(self) -> str:
        lines = [
            f"shopping requirement: to make {self.final_target_mol} mol {self.dag.final_target!r} at 100% "
            f"efficiency buy [CONSERVATION -- a conserved LOWER BOUND on purchase; a real yield needs MORE]:"
        ]
        for m, amount in self.requirements:
            lines.append(f"  {amount} mol {m!r}")
        if self.co_products:
            lines.append("co-products (produced in surplus, credited -- not bought):")
            for m, amount in self.co_products:
                lines.append(f"  {amount} mol {m!r}")
        return "\n".join(lines)


def dag_shopping_requirement(
    dag: SynthesisDAG, final_target_mol: "int | Fraction"
) -> DAGShoppingRequirement:
    """The exact conserved external-purchase requirement to make ``final_target_mol`` of ``dag``'s final target.

    The inverse of :func:`dag_ceiling` for the route AS GIVEN (buy only external leaves, make intermediates
    internally).  Making all intermediates internally, producing a fixed amount of the final target forces every
    step's reaction EXTENT -- each intermediate has a unique NET producer, so demand propagates back uniquely (a
    self-consuming/autocatalytic step's extent is the internal-make FLOOR) -- and the external requirement is the
    per-species net over those extents: total consumed minus total produced, so a by-product is CREDITED against a
    downstream purchase (the case the naive forward propagation could not see).  ``requirements`` is every species
    whose net consumption is positive (what must be bought), each an exact 100%-efficiency LOWER BOUND FOR THIS
    ROUTE (not a claim that no cheaper sourcing exists -- buying an intermediate to skip a step is the deferred
    purchased-supplement feature); ``co_products`` is every species produced in surplus (the final target excluded).

    Two agreeing derivations, never the arithmetic's own say-so: every step is balance-checked; the net production
    of the final target is asserted to equal ``final_target_mol`` exactly; and the differential oracle is TWO-SIDED
    -- the requirement fed FORWARD through :func:`dag_ceiling` must reproduce ``final_target_mol`` exactly
    (SUFFICIENCY), AND halving any single bought species must strictly drop the ceiling below it (TIGHTNESS), so
    every reported quantity is certified binding -- a real lower bound, not merely sufficient (this catches an
    over-report such as a dropped by-product credit, which sufficiency alone would pass).

    Refuses with :class:`ShoppingUnderdeterminedError` when a TARGET species has more than one NET producer (its
    producer's extent is then free -- the demand can be split across the sources -- so the amount to buy is a range,
    not a number, and inventing one would need a cost/allocation policy, ``COST-VEC-01``).  A species merely written
    on both sides of a step while net-consumed (a spectator / medium) is not a net producer and does not trip this.
    """
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    if isinstance(final_target_mol, bool) or not isinstance(final_target_mol, (int, Fraction)):
        raise CeilingError("final_target_mol must be an exact int or Fraction (mol)")
    demand_final = Fraction(final_target_mol)
    if demand_final <= 0:
        raise CeilingError("final_target_mol must be a positive quantity")

    steps = list(dag.topological_order())
    for step in steps:
        _verify_balances(step)  # two agreeing derivations (ceiling-module discipline), not the step's own say-so
    n = len(steps)
    cons = [Counter(_ident(m) for m in s.reactants) for s in steps]
    prod = [Counter(_ident(m) for m in s.products) for s in steps]
    by_ident: dict[str, Molecule] = {}
    for step in steps:
        for m in (*step.reactants, *step.products):
            by_ident.setdefault(_ident(m), m)
    target_key = [_ident(s.target) for s in steps]
    final_key = _ident(dag.final_target)

    # determinacy guard: a target species with MORE THAN ONE NET producer (net production prod-cons > 0) makes its
    # producer's extent free (the demand can be split across the sources), so the buy quantity is a range -- refuse
    # rather than fabricate one.  The count is on NET production, NOT gross: a species merely written on both sides
    # of a step while net-CONSUMED (a spectator / reaction medium / partial regeneration) is not a producer and must
    # not trip the guard (the red-team gross-vs-net over-refusal fold -- the forward ceiling proves those DAGs have a
    # single determined floor).
    net_producers_of: dict[str, set[int]] = {}
    for s in range(n):
        for k in set(prod[s]) | set(cons[s]):
            if prod[s].get(k, 0) - cons[s].get(k, 0) > 0:  # a NET producer of k
                net_producers_of.setdefault(k, set()).add(s)
    for s in range(n):
        others = net_producers_of.get(target_key[s], set()) - {s}
        if others:
            raise ShoppingUnderdeterminedError(
                f"target species {steps[s].target!r} has more than one NET producer (step {s + 1} and step(s) "
                f"{sorted(o + 1 for o in others)} each net-produce it); how much to buy depends on how the demand "
                "is split across those sources -- a range, not a single conserved number. Pinning it needs a "
                "cost/allocation policy (the SHOP-LEAF-02 follow-on, tied to COST-VEC-01)."
            )

    # back-propagate the UNIQUE reaction extents: consumers before producers (reverse topological order).  A step's
    # demand on each species is its NET consumption (consumed minus produced), NOT gross: a consumer that
    # regenerates part of its own input (water as a reaction medium; a partially-recovered reagent) needs only the
    # net topped up, so charging the gross would over-run its producer (the red-team spectator/regeneration fold).
    demand: dict[str, Fraction] = {final_key: demand_final}
    extent = [Fraction(0)] * n
    for s in reversed(range(n)):
        tk = target_key[s]
        mult = prod[s].get(tk, 0) - cons[s].get(tk, 0)  # the step's net production of its own target
        if mult <= 0:
            raise DAGError(
                f"step {s + 1} does not net-produce its target {steps[s].target!r}; the DAG cannot be inverted"
            )
        x = demand.get(tk, Fraction(0)) / mult
        if x < 0:  # pragma: no cover -- a net-surplus target implies a second net producer, already refused above
            raise DAGError(f"step {s + 1}'s target {steps[s].target!r} is over-supplied; the DAG cannot be inverted")
        extent[s] = x
        for k in set(cons[s]) | set(prod[s]):
            if k == tk:
                continue  # the target's net production is what x satisfies (via mult), not a demand on itself
            net_cons = cons[s].get(k, 0) - prod[s].get(k, 0)  # >0 net consumed (demand upstream); <0 net produced
            if net_cons:
                demand[k] = demand.get(k, Fraction(0)) + net_cons * x

    # per-species net over the forced extents: consumed minus produced (by-products credited).
    net: dict[str, Fraction] = {}
    for s in range(n):
        for k, c in cons[s].items():
            net[k] = net.get(k, Fraction(0)) + c * extent[s]
        for k, p in prod[s].items():
            net[k] = net.get(k, Fraction(0)) - p * extent[s]

    # self-check 1: the extents net exactly the requested amount of the final target (not the arithmetic's say-so).
    if net.get(final_key, Fraction(0)) != -demand_final:
        raise AssertionError(  # pragma: no cover -- a back-propagation bug; loud, never a silent wrong number
            f"inverse accounting did not net {demand_final} mol of the final target "
            f"(got {-net.get(final_key, Fraction(0))}); refusing to report it"
        )

    requirements = tuple((by_ident[k], net[k]) for k in sorted(net) if net[k] > 0)
    co_products = tuple((by_ident[k], -net[k]) for k in sorted(net) if net[k] < 0 and k != final_key)
    if not requirements:  # a real synthesis consumes some external input -- non-vacuous by construction
        raise AssertionError(  # pragma: no cover
            "a synthesis DAG must consume some external input; an empty requirement is a bug"
        )

    # self-check 2 (the differential oracle -- TWO-SIDED): feed the requirement FORWARD through the max-yield
    # ceiling; a derivation sharing no arithmetic with the back-propagation.  (a) SUFFICIENCY: the full requirement
    # makes exactly the requested amount.  (b) TIGHTNESS: halving ANY single bought species must strictly DROP the
    # ceiling below the target -- i.e. every reported quantity is binding, a real LOWER BOUND.  Sufficiency alone
    # would pass an OVER-report (feeding extra of a species the by-product credit should have zeroed still caps at
    # the target), so tightness is the half that certifies the by-product credit is exact, not merely sufficient.
    feed_map = {m: amount for m, amount in requirements}
    forward = dag_ceiling(dag, feed_map)
    if forward.final_target_mol != demand_final:
        raise AssertionError(  # pragma: no cover -- a determinacy escape; refuse rather than report a wrong number
            f"forward LP disagreement: feeding the computed requirement makes {forward.final_target_mol} mol of "
            f"the final target, not {demand_final} -- the requirement is not the exact conserved inverse"
        )
    for m, amount in requirements:
        short = dag_ceiling(dag, {**feed_map, m: amount / 2}).final_target_mol
        if short >= demand_final:
            raise AssertionError(  # pragma: no cover -- an over-reported (non-minimal) buy; refuse, never report it
                f"requirement for {m!r} ({amount} mol) is not tight: halving it still makes {short} mol of the "
                f"final target (>= {demand_final}), so it is over-reported (a dropped by-product credit?)"
            )

    return DAGShoppingRequirement(dag, demand_final, tuple((steps[s], extent[s]) for s in range(n)),
                                  requirements, co_products)


# -- E1 over a DAG: composability across every edge -----------------------------------------------------
@dataclass(frozen=True)
class DAGComposability(Digestible):
    """The composability of a DAG: one :class:`Transition` per producer->consumer EDGE, and the verdict.

    Guarded against the vacuous pass exactly as the linear route is: a DAG with no internal edges is
    ``NO_TRANSITIONS`` (nothing to compose), never ``COMPOSABLE``; a ``COMPOSABLE`` verdict needs every edge
    affirmatively cleared on sourced data, so any ``UNKNOWN`` gap holds the DAG at ``UNKNOWN``.
    """

    dag: SynthesisDAG
    transitions: tuple[Transition, ...]

    @property
    def verdict(self) -> str:
        if not self.transitions:
            return "NO_TRANSITIONS"
        if any(t.status is TransitionStatus.DEGENERATE for t in self.transitions):
            return "DEGENERATE"
        if all(t.status is TransitionStatus.COMPOSABLE for t in self.transitions):
            return "COMPOSABLE"
        return "UNKNOWN"

    @property
    def is_degenerate(self) -> bool:
        return self.verdict == "DEGENERATE"

    @property
    def degenerate_reasons(self) -> tuple[str, ...]:
        return tuple(t.reason for t in self.transitions if t.degenerate)

    @property
    def gaps(self) -> tuple[str, ...]:
        return tuple(t.reason for t in self.transitions if t.status is TransitionStatus.UNKNOWN)

    @property
    def route_surviving_fraction(self) -> float | None:
        """The composite fraction surviving every duration-assessed edge hold -- the survival monoid functor's
        value on the DAG's edges (:func:`~smartchem.experiment.composability._survival_product`).  ``None`` when
        no edge was duration-assessed."""
        return _survival_product(self.transitions)

    @property
    def serial_hold_notes(self) -> tuple[str, ...]:
        """Human disclosures of each edge's serial-schedule hold (DAG-HOLD-01): the intermediate idle time E1's
        instantaneous survival verdict does not model.  A DISCLOSURE, never a verdict -- it does NOT degrade
        ``COMPOSABLE`` (else every convergent DAG with a sibling branch would read ``UNKNOWN``); it is the honest,
        non-vacuous widening of the serial-hold-stability boundary DAG-BENCH-01 documented, drawn straight from the
        observation-only ``serial-hold-minutes`` findings ``dag_composability`` attaches per edge."""
        notes = []
        for t in self.transitions:
            for f in t.findings:
                if f.label == "serial-hold-minutes":
                    notes.append(
                        f"step {t.from_step + 1}->{t.to_step + 1}: intermediate held {f.value} {f.unit} under the "
                        f"serial schedule computed here (schedule-relative -- a different valid order may hold a "
                        f"sibling instead); survival over that hold is UNVERIFIED (E1 is time-blind)"
                    )
        return tuple(notes)

    def explain(self) -> str:
        lines = [f"composability (convergent DAG): {self.verdict}"]
        for t in self.transitions:
            lines.append(f"  step {t.from_step + 1}->{t.to_step + 1}: {t.reason}")
        for note in self.serial_hold_notes:
            lines.append(f"  NOTE {note}")
        return "\n".join(lines)


def _serial_hold_minutes(dag: SynthesisDAG) -> dict[tuple[int, int], float]:
    """The per-edge serial-schedule hold (minutes) for each producer->consumer intermediate: the sum of the sourced
    MINIMUM elapsed times of the steps scheduled STRICTLY between the producer and the consumer under the DAG's own
    topological order (DAG-HOLD-01).  A ``None`` floor counts as 0 (an unknown floor is a lower bound of zero -- so
    the result is a sound LOWER bound on the hold, exactly as :func:`~smartchem.process_constraints._critical_path`
    treats an unknown weight).  This is the EXTRA hold a convergent serial schedule imposes beyond the adjacent
    handoff E1 judges: a linear chain (the consumer runs immediately after its producer) has zero intervening steps
    and so a zero hold.  Schedule-relative by construction (the DAG's canonical ``topological_order``); it is surfaced
    as an observation, never a certified bound over all schedules."""
    from ..process_constraints import _known_min  # lazy: matches dag_process_fit's process_constraints edge
    order = _topological_order(len(dag.steps), dag.edges)
    pos = {idx: rank for rank, idx in enumerate(order)}
    holds: dict[tuple[int, int], float] = {}
    for i, j, _m in dag.edges:
        floor = 0.0
        for k in order:
            if pos[i] < pos[k] < pos[j]:
                proc = dag.steps[k].envelope.process
                if proc is not None:
                    # the SAME known-minimum floor the process gate uses (min_elapsed_minutes and/or interval .lo);
                    # an unknown floor is 0, so the sum stays a sound LOWER bound on the hold.
                    step_floor = _known_min(
                        proc.min_elapsed_minutes,
                        proc.elapsed_minutes.lo if proc.elapsed_minutes is not None else None,
                    )
                    if step_floor is not None:
                        floor += step_floor
        holds[(i, j)] = floor
    return holds


def _serial_hold_segments(dag: SynthesisDAG) -> "dict[tuple[int, int], tuple[tuple[object, float], ...]]":
    """The per-edge ordered hold SEGMENTS: for each producer->consumer intermediate, the ``(temperature, minutes)``
    of every step scheduled STRICTLY between them under the DAG's topological order (DAG-HOLD-01) -- the sibling
    steps the intermediate idles through.  ``temperature`` is that step's declared ``ConditionEnvelope.temperature``
    (possibly ``None``); ``minutes`` is the SAME known-minimum elapsed floor :func:`_serial_hold_minutes` sums (a
    ``None``/zero floor is dropped, so ``sum(minutes) == _serial_hold_minutes[(i, j)]`` -- the disclosure note and
    the duration gate see one consistent hold).  E1's duration gate reads survival over THESE per-step temperatures
    (never a producer/consumer endpoint's), so it renders a verdict only on temperatures the DAG actually declares
    for the idle hold; an undeclared segment temperature makes the gate fail closed."""
    from ..process_constraints import _known_min
    order = _topological_order(len(dag.steps), dag.edges)
    pos = {idx: rank for rank, idx in enumerate(order)}
    segments: "dict[tuple[int, int], tuple[tuple[object, float], ...]]" = {}
    for i, j, _m in dag.edges:
        segs: "list[tuple[object, float]]" = []
        for k in order:
            if pos[i] < pos[k] < pos[j]:
                proc = dag.steps[k].envelope.process
                if proc is None:
                    continue
                floor = _known_min(
                    proc.min_elapsed_minutes,
                    proc.elapsed_minutes.lo if proc.elapsed_minutes is not None else None,
                )
                if floor is None or floor <= 0:
                    continue
                segs.append((dag.steps[k].envelope.temperature, float(floor)))
        segments[(i, j)] = tuple(segs)
    return segments


def dag_composability(
    dag: SynthesisDAG, *, stability: StabilityTable = DEFAULT_STABILITY,
    kinetics: KineticTable = _DEFAULT_DECOMP_KINETICS,
) -> DAGComposability:
    """Judge whether every intermediate survives its handoff across each DAG edge, over sourced stability.

    Each edge's Transition also carries the sourced serial-schedule HOLD (DAG-HOLD-01, :func:`_serial_hold_minutes`)
    as an observation-only finding: a convergent DAG's serial schedule holds an early branch's intermediate through
    its siblings, a hold E1's instantaneous survival verdict is blind to.  It is a disclosure, never a status change
    (it does not degrade COMPOSABLE), the honest widening of the serial-hold-stability boundary DAG-BENCH-01 named."""
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    segments = _serial_hold_segments(dag)
    transitions = tuple(
        _judge_transition(i, j, intermediate, dag.steps[i].envelope, dag.steps[j].envelope, stability,
                          hold_segments=segments.get((i, j)), kinetics=kinetics)
        for i, j, intermediate in dag.edges
    )
    return DAGComposability(dag, transitions)


def dag_process_fit(dag: "SynthesisDAG", bounds: "ProcessBounds") -> "ProcessFit":
    """SOUND process admission for a convergent DAG (ROUND-12: closes the ROUND-11 serial-sum over-conservatism).

    Delegates to :func:`~smartchem.process_constraints.evaluate_dag_process_requirements`, which shares every
    order-agnostic per-step check and the ACTIVE serial-total with the linear gate, but aggregates the ELAPSED
    route-total over ``dag.edges`` so INDEPENDENT branches overlap instead of being summed as if serial:

    * The order-agnostic per-step checks (attention / agitation / check-interval / equipment / workup / per-step
      elapsed) are EXACTLY correct on a DAG -- a step's requirement does not care what ran alongside it.
    * **FITS** is certified by the SERIAL-sum ceiling (achievable one-step-at-a-time with a single set of hands) --
      unchanged, still sound.  **EXCLUDED** now fires on the CRITICAL-PATH floor (unfittable even with fully
      concurrent branches) -- a strictly TIGHTER, still-sound exclude than the ROUND-11 floor-SUM.  Between them
      (serial run over budget, parallel floor under it) is an honest **UNKNOWN**, never the old over-conservative
      EXCLUDED nor a guessed FITS.

    BOUNDARY (unmodeled, do NOT read a FITS as more than it proves): the gate assumes a step's declared attention is
    legal in isolation; it does NOT check JOINT single-operator schedulability -- two independent branches that each
    demand CONTINUOUS attention at overlapping wall-clock cannot both be served by one operator, yet each passes its
    own per-step check.  A whole-DAG resourcing/scheduling model is a named next-step.  This function returns the
    sound verdict; formal RouteDossier admission (flipping ``process_selection_status`` off UNASSESSED) is likewise a
    named next-step -- the caller surfaces this as a diagnostic, not yet as admission.
    """
    from ..process_constraints import evaluate_dag_process_requirements
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    reqs = tuple(step.envelope.process for step in dag.steps)
    edges = tuple((producer, consumer) for producer, consumer, _intermediate in dag.edges)
    return evaluate_dag_process_requirements(reqs, edges, bounds)


# -- the bundled DAG verdict (E1 + M1 + M2 over the convergent structure) --------------------------------
def _worst_feasibility(directions: tuple[FeasibilityDirection, ...]) -> str:
    """The route-shape-agnostic feasibility verdict (mirrors RouteFeasibility.verdict)."""
    if any(d is FeasibilityDirection.UNFAVORABLE for d in directions):
        return "UNFAVORABLE"
    if any(d is FeasibilityDirection.UNKNOWN for d in directions):
        return "UNKNOWN"
    if any(d is FeasibilityDirection.BORDERLINE for d in directions):
        return "BORDERLINE"
    return "FAVORABLE"


def _worst_equilibrium(extents: tuple[EquilibriumExtent, ...]) -> str:
    """The bottleneck-dominated equilibrium verdict (mirrors RouteEquilibrium.verdict)."""
    for worst in (EquilibriumExtent.NEGLIGIBLE, EquilibriumExtent.LIMITED, EquilibriumExtent.UNKNOWN,
                  EquilibriumExtent.BALANCED, EquilibriumExtent.FAVORABLE):
        if any(x is worst for x in extents):
            return worst.value
    return EquilibriumExtent.ESSENTIALLY_COMPLETE.value


def _worst_selectivity(statuses: tuple[SelectivityStatus, ...]) -> str:
    """The route-shape-agnostic selectivity verdict (mirrors RouteSelectivity.verdict EXACTLY): a sourced
    DISFAVORED step dominates, then any UNKNOWN, then a sourced FAVORED, else NOT_APPLICABLE."""
    if any(s is SelectivityStatus.DISFAVORED for s in statuses):
        return "DISFAVORED"
    if any(s is SelectivityStatus.UNKNOWN for s in statuses):
        return "UNKNOWN"
    if any(s is SelectivityStatus.FAVORED for s in statuses):
        return "FAVORED"
    return "NOT_APPLICABLE"


@dataclass(frozen=True)
class DAGVerification(Digestible):
    """The full verdict on a convergent DAG: composability per edge, feasibility + equilibrium per step."""

    dag: SynthesisDAG
    composability: DAGComposability
    feasibility: tuple[StepFeasibility, ...]   # one per step (node), in the DAG's own step order
    equilibrium: tuple[StepEquilibrium, ...]   # one per step (node), in the DAG's own step order

    @property
    def feasibility_verdict(self) -> str:
        return _worst_feasibility(tuple(f.direction for f in self.feasibility))

    @property
    def equilibrium_verdict(self) -> str:
        return _worst_equilibrium(tuple(e.extent for e in self.equilibrium))

    def explain(self) -> str:
        lines = [
            f"convergent synthesis DAG -> {self.dag.final_target!r} "
            f"({'convergent' if self.dag.is_convergent else 'linear'}, "
            f"{len(self.dag.steps)} steps, {len(self.dag.convergence_points)} join(s))",
            self.composability.explain(),
            f"feasibility (thermodynamic ΔG, worst step): {self.feasibility_verdict}",
            f"equilibrium (extent K=exp(-ΔG/RT), worst step): {self.equilibrium_verdict}",
        ]
        return "\n".join(lines)


def verify_dag(
    dag: SynthesisDAG, *, stability: StabilityTable = DEFAULT_STABILITY, thermo: ThermoTable = DEFAULT_THERMO
) -> DAGVerification:
    """Verify a convergent DAG on every rung: E1 composability per edge, M1 feasibility + M2 equilibrium per step.

    Reuses the exact per-step / per-transition machinery the linear route runs on; only the *shape* generalises.
    The stoichiometric ceiling is separate (:func:`dag_ceiling`) because it needs charged amounts.
    """
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    comp = dag_composability(dag, stability=stability)
    feas = tuple(feasibility_of_step(s, thermo=thermo) for s in dag.steps)
    equi = tuple(equilibrium_of_step(s, thermo=thermo) for s in dag.steps)
    return DAGVerification(dag, comp, feas, equi)


# -- the per-node thermochemical roll-up feeding DAG RANKING (DAG-THERMO-01) -----------------------------
@dataclass(frozen=True)
class DAGThermoRollup:
    """The four SOURCED per-reaction thermochemical verdicts a linear ``_route_score`` ranks on, aggregated
    worst-node-dominated over a convergent DAG's nodes -- the DAG analogue of :class:`RouteFit`'s
    selectivity/feasibility/equilibrium/kinetics verdicts, closing the "``DAGBenchFit`` carries no thermochem"
    gap :func:`~smartchem.experiment.drafter._dag_score` named as its next-step.

    RANKING-ONLY, never a grade (identical to the linear discipline): these verdicts order otherwise-tied DAGs
    and NEVER enter a section-11 status -- a DAG's FITS/EXCLUDED/UNKNOWN is unaffected by them, exactly as a
    linear route's ``fit_status`` is independent of its selectivity/feasibility/equilibrium/kinetics verdicts.
    A plain record (not a :class:`~smartchem.contracts.Digestible`): an internal ranking computation the thin
    :class:`~smartchem.service.RankedDAGSummary` projects the strings off, never itself a payload term."""

    selectivity_verdict: str
    feasibility_verdict: str
    equilibrium_verdict: str
    kinetics_verdict: str


def dag_thermo_rollup(
    dag, *, selectivity=None, thermo=None, kinetics=None, losses: tuple = (),
) -> DAGThermoRollup:
    """Aggregate the four SOURCED per-reaction thermochemical verdicts over a convergent DAG's nodes,
    worst-node-dominated -- the DAG analogue of the four ``verify_*`` folds :func:`fit_route` runs, reusing the
    IDENTICAL per-step providers (``selectivity_of_step`` / ``feasibility_of_step`` / ``equilibrium_of_step`` /
    ``kinetics_of_step``), the IDENTICAL default sourced tables, and the IDENTICAL worst-precedence folds
    (:func:`_worst_selectivity` / :func:`_worst_feasibility` / :func:`_worst_equilibrium` / :func:`worst_regime`).

    A per-node verdict does not depend on the schedule, so this maps over ``dag.steps`` directly (order-agnostic,
    exactly as ``dag_bench_fit``'s per-step physical box is).  Each table defaults to its sourced seed when ``None``,
    mirroring ``verify_selectivity``/``verify_feasibility``/``verify_kinetics`` -- so the DAG ranks on the SAME
    sourced facts a linear route does, never an invented one."""
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    sel_tbl = DEFAULT_SELECTIVITY if selectivity is None else selectivity
    thermo_tbl = DEFAULT_THERMO if thermo is None else thermo
    kin_tbl = DEFAULT_KINETICS if kinetics is None else kinetics
    sel = tuple(selectivity_of_step(s, table=sel_tbl, losses=losses) for s in dag.steps)
    feas = tuple(feasibility_of_step(s, thermo=thermo_tbl) for s in dag.steps)
    equi = tuple(equilibrium_of_step(s, thermo=thermo_tbl) for s in dag.steps)
    kin = tuple(kinetics_of_step(s, kinetics=kin_tbl, losses=losses) for s in dag.steps)
    return DAGThermoRollup(
        _worst_selectivity(tuple(s.status for s in sel)),
        _worst_feasibility(tuple(f.direction for f in feas)),
        _worst_equilibrium(tuple(e.extent for e in equi)),
        worst_regime(k.regime for k in kin).value,
    )
