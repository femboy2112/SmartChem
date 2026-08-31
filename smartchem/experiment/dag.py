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
from typing import Mapping

from ..category import Molecule
from ..contracts import Digestible, canonical_digest
from ..data.stability import DEFAULT_STABILITY, StabilityTable
from ..data.thermo import DEFAULT_THERMO, ThermoTable
from .bucket import Bucket, Quantity
from .ceiling import StoichiometricCeiling, stoichiometric_ceiling
from .composability import Transition, TransitionStatus, _judge_transition
from .equilibrium import EquilibriumExtent, StepEquilibrium, equilibrium_of_step
from .feasibility import FeasibilityDirection, StepFeasibility, feasibility_of_step
from .step import ExperimentStep

__all__ = [
    "DAG_SCHEMA",
    "DAGError",
    "SynthesisDAG",
    "DAGCeiling",
    "DAGComposability",
    "DAGVerification",
    "dag_ceiling",
    "dag_composability",
    "verify_dag",
]

DAG_SCHEMA = "smartchem.experiment/synthesis-dag-v1"


class DAGError(ValueError):
    """A proposed synthesis DAG is not an admissible convergent structure."""


def _ident(m: Molecule) -> str:
    try:
        return canonical_digest(m.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(m)


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

    @classmethod
    def of(cls, *steps: ExperimentStep) -> "SynthesisDAG":
        return cls(DAG_SCHEMA, tuple(steps))

    def __repr__(self) -> str:
        shape = "convergent" if self.is_convergent else "linear"
        return f"SynthesisDAG({shape}, {len(self.steps)} steps -> {self.final_target!r})"


# -- E2 over a DAG: the convergent ceiling --------------------------------------------------------------
@dataclass(frozen=True)
class DAGCeiling(Digestible):
    """The 100%-efficiency ceiling propagated through a convergent DAG in topological order.

    Each step is limited by whichever of its inputs -- an external reagent or an intermediate a branch could
    make -- is scarcest; a convergent step naturally takes the min over ALL its branches.  The sink's max is
    the DAG's ceiling.  ``CONSERVATION`` -- an idealised upper bound over the whole convergent synthesis.
    """

    dag: SynthesisDAG
    per_step: tuple[StoichiometricCeiling, ...]  # in topological order
    final_target_mol: Fraction

    @property
    def quantity(self) -> Quantity:
        return Quantity(
            "max final target (100% efficiency, convergent)", str(self.final_target_mol), "mol",
            Bucket.CONSERVATION,
            "limiting-reagent conservation propagated through the DAG; exact rational, per-step kernel-checked",
        )

    def explain(self) -> str:
        lines = [
            f"convergent ceiling: {self.final_target_mol} mol {self.dag.final_target!r} at 100% efficiency "
            f"[CONSERVATION -- an idealised upper bound over the whole convergent synthesis]"
        ]
        for c in self.per_step:
            lines.append(f"  <= {c.max_target_mol} mol {c.step.target!r} (limited by {c.limiting_reactant!r})")
        return "\n".join(lines)


def dag_ceiling(dag: SynthesisDAG, feed: Mapping[Molecule, "int | Fraction"]) -> DAGCeiling:
    """The exact convergent ceiling of ``dag`` for external ``feed`` amounts (mol per leaf input).

    ``feed`` must cover the leaf inputs (:attr:`SynthesisDAG.leaf_inputs`) you want counted; a leaf absent from
    ``feed`` is treated as charged in excess by the per-step E2 kernel.  Intermediates are supplied
    automatically as the branches that make them are ceilinged, in topological order.
    """
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
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
    final = available[_ident(dag.final_target)][1]
    return DAGCeiling(dag, tuple(per), final)


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

    def explain(self) -> str:
        lines = [f"composability (convergent DAG): {self.verdict}"]
        for t in self.transitions:
            lines.append(f"  step {t.from_step + 1}->{t.to_step + 1}: {t.reason}")
        return "\n".join(lines)


def dag_composability(dag: SynthesisDAG, *, stability: StabilityTable = DEFAULT_STABILITY) -> DAGComposability:
    """Judge whether every intermediate survives its handoff across each DAG edge, over sourced stability."""
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    transitions = tuple(
        _judge_transition(i, j, intermediate, dag.steps[i].envelope, dag.steps[j].envelope, stability)
        for i, j, intermediate in dag.edges
    )
    return DAGComposability(dag, transitions)


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
