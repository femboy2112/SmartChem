"""Item 1 / Move 5 evidence (EM scope): the circuit PIPELINE -- a second-domain step/route/cost stack riding
the SAME generic open SMC (:mod:`smartchem.open_core`) the chemistry layer rides.

Item 6 proved the ``open_core`` decoration slot hosts a non-additive physical apex (``ResistorDecoration``).
That was a DEMONSTRATION consumer (``resistor_edge`` called only in tests), not a pipeline -- the zero-call-sites
gap the Move-5 deferral was waiting on.  This module closes it with a real INGEST and a route/step shape:

* :func:`from_circuit` -- lift an ARBITRARY production resistor network (a :mod:`smartchem.open_diagram`
  presentation + its :class:`~smartchem.resistive_dc_schema.ResistiveDCModel`, the live electrical core with a
  solver) into an ``open_core.OpenDiagram`` whose apex is the network's exact boundary relation.  It reconstructs
  the topology DIRECTLY (one resistor hyperedge per structural edge; the old core's ``structural_edges()`` +
  boundary maps already expose everything -- no new extraction API was needed) and attaches the apex the
  production ``blackbox_resistive_dc`` computes.  Because it reconstructs directly, it INGESTS any topology --
  series, parallel, AND a genuinely non-series-parallel Wheatstone bridge -- whose apex ``then``/``tensor``
  cannot construct.  (The distinction matters: the decoration slot HOSTS the bridge's solver-computed apex; the
  generic compositional algebra does not CONSTRUCT it -- only series/tensor/parallel are compositionally
  reachable.)  The apex is cross-checked in the probe TWO ways: to ``resistive_dc_verifier`` (a second,
  independently-TYPED copy of the same nodal-Laplacian elimination -- this bounds implementation typos but shares
  algorithmic provenance, so it is NOT a fully independent bearing), AND to a PHYSICALLY DISTINCT spanning-tree /
  effective-resistance oracle (a combinatorial matrix-tree computation, not an elimination) that has no
  common-mode with the Laplacian derivation.
* :func:`parallel` -- the parallel-merge primitive at the DIAGRAM level: tensor two 1->1 stages, merge their
  boundary nodes (correct topology), and carry the exact ``R1||R2`` apex via
  :meth:`ResistorDecoration.parallel_combine` (the relation-level merge, the correct-apex counterpart to the
  ``plug_all`` node-merge whose apex rides through stale).  This CLOSES item 6's deferred parallel CONSTRUCTION:
  parallel is now constructible with an exact apex, not only reconstructible via the solver.
* :func:`equivalent_resistance` -- the domain COST read: the two-terminal resistance off a 1->1 apex relation
  (``None``, fail-closed, for an open/short/non-two-terminal apex).
* :func:`within_spec` -- a Move-5 SURVIVAL PREDICATE over that cost (finite resistance inside a band), the
  circuit-domain analogue of the chemistry survival fraction.
* :class:`CircuitStage` / :class:`CircuitRoute` -- the route/step SHAPE: stages (a resistor, an ingested
  sub-network, or a parallel block) composed in SERIES through the generic ``open_core.then``, with the domain
  cost + survival read off the assembled apex.

**The Move-5 claim, bounded honestly (guarding the last-round over-claim lesson).** This is a second-domain
*demonstration* pipeline: a self-contained route/step/cost/survival shape with a live ingest and an
independent-oracle cross-check.  Its internal consumer graph is real -- ``CircuitRoute.assemble`` drives
``open_core.then``, ``CircuitStage.ingest`` drives ``from_circuit``, ``CircuitStage.in_parallel`` drives
``parallel``, and the cost/survival read the assembled apex -- which is the genericity evidence Move 5's deferral
named as missing (item 6's ``resistor_edge`` had NO such graph).  But by this module's own standard (the
zero-call-sites lesson) it is not yet production-integrated: nothing OUTSIDE this module + its test/probe plans,
ranks, or verifies a circuit through this shape.  So it STRENGTHENS the Move-5 case (the genericity is now
exercised end to end by a real consumer graph), it does not COMPLETE Move 5: the full domain-neutral refactor
making the CHEMISTRY ``ExperimentStep``/``ExperimentRoute`` literally parametric over a "conserved-inventory
transition + survival predicate" remains its own large round, and this pipeline still awaits its first non-test
caller.

Scope (bounded, sound): ideal DC resistor networks only (no RLC/AC), the item-6 boundary.  ``from_circuit``
INGESTS any topology (arbitrary, solver-computed apex); compositional CONSTRUCTION covers SERIES (``.then``),
JUXTAPOSITION (``.tensor``), and now PARALLEL (:func:`parallel`).  A general non-series-parallel compositional
builder (assembling e.g. a bridge from parts through the generic ops) stays genuinely deferred -- but the
pipeline does not depend on it, because ``from_circuit`` INGESTS such a network directly (hosting its apex),
which is all the pipeline consumer needs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from .open_core import Hyperedge, Interface, OpenDiagram, Terminal
from .open_diagram import OpenDiagram as ElectricalDiagram
from .open_resistor_diagram import (
    ResistorDecoration,
    apex_matches_boundary,
    resistor_edge,
    resistor_relation,
)
from .resistive_dc_schema import Rational, ResistiveDCModel

__all__ = [
    "from_circuit",
    "parallel",
    "equivalent_resistance",
    "within_spec",
    "CircuitStage",
    "CircuitRoute",
]

_ELECTRICAL = "electrical"


def from_circuit(diagram: ElectricalDiagram, model: ResistiveDCModel) -> OpenDiagram:
    """Lift a production resistor network (:mod:`smartchem.open_diagram` + model) into ``open_core``.

    Reconstructs the topology directly -- one ``resistor`` hyperedge per structural edge, the old core's own
    node indices carried through -- and attaches the apex the production solver computes for the WHOLE network
    (``blackbox_resistive_dc``), a :class:`ResistorDecoration` whose relation is cross-checked in the probe to
    the independent Kirchhoff verifier.  Handles arbitrary topology (series / parallel / bridge).
    """
    from .circuit import blackbox_resistive_dc

    if type(diagram) is not ElectricalDiagram:
        raise TypeError("diagram must be a smartchem.open_diagram.OpenDiagram (the production electrical core)")
    if type(model) is not ResistiveDCModel:
        raise TypeError("model must be an exact ResistiveDCModel bound to this diagram")
    edges = diagram.structural_edges()
    resistances = model.resistances_in_structural_order()
    if len(resistances) != len(edges):
        raise ValueError("model resistance count does not match the diagram's structural-edge count")
    node_ports = tuple(_ELECTRICAL for _ in diagram.node_kinds)
    hyperedges = tuple(
        Hyperedge(
            "resistor",
            f"r{index}={resistance.ohms.numerator}/{resistance.ohms.denominator}",
            (Terminal("a", edge.node_a), Terminal("b", edge.node_b)),
        )
        for index, (edge, resistance) in enumerate(zip(edges, resistances))
    )
    apex = ResistorDecoration(blackbox_resistive_dc(diagram, model))
    lifted = OpenDiagram(
        Interface(tuple(_ELECTRICAL for _ in diagram.dom.ports)),
        Interface(tuple(_ELECTRICAL for _ in diagram.cod.ports)),
        tuple(diagram.input_nodes),
        tuple(diagram.output_nodes),
        node_ports,
        hyperedges,
        apex,
    )
    # invariant: a directly-reconstructed diagram carries a boundary-consistent apex (its own solver relation).
    assert apex_matches_boundary(lifted)
    return lifted


def _require_two_terminal_resistor(diagram: OpenDiagram, who: str) -> None:
    """A TYPE/width gate, NOT an apex-correctness check: it confirms ``diagram`` is a 1->1 ``ResistorDecoration``
    diagram, never that its apex is the physically-correct relation for its topology (a hand-built lying stage
    passes -- garbage in).  Correctness rests on how stages are CONSTRUCTED (``resistor_edge``/``from_circuit``/
    ``parallel``), cross-checked to the independent oracle in the probe."""
    if type(diagram) is not OpenDiagram:
        raise TypeError(f"{who} must be an open_core.OpenDiagram")
    if type(diagram.decoration) is not ResistorDecoration:
        raise TypeError(f"{who} must carry a ResistorDecoration apex")
    if len(diagram.dom.ports) != 1 or len(diagram.cod.ports) != 1:
        raise ValueError(f"{who} must be a 1->1 (two-terminal) circuit stage")


def parallel(left: OpenDiagram, right: OpenDiagram) -> OpenDiagram:
    """Parallel-compose two 1->1 circuit stages: merge both inputs and both outputs, exact ``R1||R2`` apex.

    Tensors the two stages (a 2->2 block-diagonal diagram), then merges the two input nodes into one and the two
    output nodes into one -- the correct parallel TOPOLOGY -- and carries the exact parallel apex via
    :meth:`ResistorDecoration.parallel_combine`.  Closes item 6's deferred parallel construction.
    """
    _require_two_terminal_resistor(left, "left")
    _require_two_terminal_resistor(right, "right")
    tensored = left.tensor(right)                                 # 2->2 disjoint union
    node_count = len(tensored.node_ports)
    parent = list(range(node_count))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: int, b: int) -> None:
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    union(tensored.input_nodes[0], tensored.input_nodes[1])       # merge the two inputs
    union(tensored.output_nodes[0], tensored.output_nodes[1])     # merge the two outputs
    roots = sorted({find(node) for node in range(node_count)})
    compact = {root: index for index, root in enumerate(roots)}

    def remap(node: int) -> int:
        return compact[find(node)]

    merged_ports: list[str | None] = [None] * len(roots)
    for old, port in enumerate(tensored.node_ports):
        target = remap(old)
        if merged_ports[target] is not None and merged_ports[target] != port:
            raise ValueError("parallel merge united nodes with incompatible port tokens")
        merged_ports[target] = port
    hyperedges = tuple(
        Hyperedge(edge.kind, edge.payload, tuple(Terminal(t.role, remap(t.node)) for t in edge.terminals))
        for edge in tensored.hyperedges
    )
    apex = left.decoration.parallel_combine(right.decoration)
    merged = OpenDiagram(
        Interface((_ELECTRICAL,)),
        Interface((_ELECTRICAL,)),
        (remap(tensored.input_nodes[0]),),
        (remap(tensored.output_nodes[0]),),
        tuple(port for port in merged_ports if port is not None),
        hyperedges,
        apex,
    )
    assert apex_matches_boundary(merged)                          # the merged apex is boundary-consistent
    return merged


def equivalent_resistance(diagram: OpenDiagram) -> Fraction | None:
    """The two-terminal equivalent resistance of a 1->1 resistor diagram, or ``None`` (fail-closed).

    Reads the exact rational ``R`` off the apex boundary relation and VERIFIES the relation equals a pure
    two-terminal resistor of that ``R`` -- so an open circuit, a short in a non-resistor form, or a
    non-two-terminal apex returns ``None`` rather than a fabricated resistance.  ``R = 0`` (a wire) is a valid
    finite answer.
    """
    if type(diagram) is not OpenDiagram or type(diagram.decoration) is not ResistorDecoration:
        return None
    relation = diagram.decoration.relation
    if relation.dom_ports != 1 or relation.cod_ports != 1:
        return None
    rows = relation.rref_rows
    # a two-terminal resistor's canonical RREF is [[1,-1,0,R],[0,0,1,1]]: R is the I_cod coefficient of row 0.
    if len(rows) != 2:
        return None
    if not (rows[0][0].fraction == 1 and rows[0][1].fraction == -1 and rows[0][2].fraction == 0):
        return None
    candidate = rows[0][3].fraction
    if candidate < 0:
        return None  # a negative equivalent resistance is not a physical ideal resistor (fail-closed)
    if relation != resistor_relation(candidate):
        return None
    return candidate


def _spec_bound(value, name: str):
    """Coerce a spec bound to an EXACT ``Fraction``, or accept ``±inf`` as an explicit unbounded sentinel.

    Bounds are exact (int / ``Fraction`` / ``Rational``) so a band edge is decided exactly; ``math.inf`` /
    ``-math.inf`` express a one-sided band ("no ceiling" / "no floor").  A FINITE float is refused (adversarial
    review): ``Fraction(0.1)`` is the binary expansion, not ``1/10``, so a finite float silently misjudges an
    exactly-in-spec part at the edge -- the docstring promised exact, so the code now enforces it.
    """
    if type(value) is Rational:
        return value.fraction
    if type(value) is Fraction:
        return value
    if type(value) is int and type(value) is not bool:
        return Fraction(value)
    if type(value) is float and math.isinf(value):
        return value  # ±inf: an explicit unbounded side (comparisons against a Fraction are well-defined)
    raise TypeError(
        f"{name} must be an exact int/Fraction/Rational, or ±math.inf for an unbounded side "
        f"(a finite float is not exact -- Fraction(0.1) != 1/10)"
    )


def within_spec(diagram: OpenDiagram, low_ohms, high_ohms) -> bool:
    """Move-5 survival predicate: True iff the stage's equivalent resistance is finite and in ``[low, high]``.

    Fail-closed: an open/short/non-two-terminal apex (``equivalent_resistance`` is ``None``) never survives.
    Bounds are EXACT (int/``Fraction``/``Rational``); ``±math.inf`` expresses a one-sided band, and ``low <=
    high`` is required.  A finite float bound is refused (it is not exact -- see :func:`_spec_bound`).
    """
    lo = _spec_bound(low_ohms, "low_ohms")
    hi = _spec_bound(high_ohms, "high_ohms")
    if lo > hi:  # Fraction vs ±inf comparisons are well-defined, so a one-sided band orders correctly
        raise ValueError("within_spec requires low_ohms <= high_ohms")
    resistance = equivalent_resistance(diagram)
    if resistance is None:
        return False
    return lo <= resistance <= hi


@dataclass(frozen=True)
class CircuitStage:
    """One 1->1 circuit stage lifted onto ``open_core`` -- a resistor, an ingested sub-network, or a parallel
    block -- plus a human label.  Stages compose in SERIES through :class:`CircuitRoute`."""

    diagram: OpenDiagram
    label: str

    def __post_init__(self) -> None:
        _require_two_terminal_resistor(self.diagram, "CircuitStage.diagram")
        if type(self.label) is not str or not self.label:
            raise ValueError("CircuitStage.label must be a non-empty string")

    @classmethod
    def resistor(cls, ohms, *, label: str | None = None) -> "CircuitStage":
        """A single ideal resistor stage (the ``resistor_edge`` functor image)."""
        edge = resistor_edge(ohms)
        return cls(edge, label if label is not None else f"R={ohms}")

    @classmethod
    def ingest(cls, diagram: ElectricalDiagram, model: ResistiveDCModel, *, label: str) -> "CircuitStage":
        """Ingest a 1->1 production resistor network as one stage (:func:`from_circuit`)."""
        return cls(from_circuit(diagram, model), label)

    @classmethod
    def in_parallel(cls, left: "CircuitStage", right: "CircuitStage", *, label: str | None = None) -> "CircuitStage":
        """A parallel block of two stages (:func:`parallel`)."""
        merged = parallel(left.diagram, right.diagram)
        return cls(merged, label if label is not None else f"({left.label} || {right.label})")

    @property
    def equivalent_resistance(self) -> Fraction | None:
        return equivalent_resistance(self.diagram)


@dataclass(frozen=True)
class CircuitRoute:
    """A SERIES route of circuit stages -- the second-domain route/step shape.

    :meth:`assemble` folds the stages through ``open_core.then`` (the generic series composition), so the
    composite apex is the series relation the chemistry side would get from ``.then`` on ITS decoration.  The
    domain cost (:attr:`equivalent_resistance`) and the Move-5 survival read (:meth:`within_spec`) come off that
    assembled apex.
    """

    stages: tuple[CircuitStage, ...]

    def __post_init__(self) -> None:
        if type(self.stages) is not tuple or not self.stages:
            raise ValueError("a CircuitRoute needs at least one stage")
        if any(type(stage) is not CircuitStage for stage in self.stages):
            raise TypeError("stages must be CircuitStage values")

    @classmethod
    def of(cls, *stages: CircuitStage) -> "CircuitRoute":
        return cls(tuple(stages))

    def assemble(self) -> OpenDiagram:
        """Fold the stages in series via ``open_core.then`` -- the assembled second-domain diagram."""
        composite = self.stages[0].diagram
        for stage in self.stages[1:]:
            composite = composite.then(stage.diagram)
        return composite

    @property
    def equivalent_resistance(self) -> Fraction | None:
        """The route's two-terminal equivalent resistance, read off the assembled series apex."""
        return equivalent_resistance(self.assemble())

    def within_spec(self, low_ohms, high_ohms) -> bool:
        """Move-5 survival predicate on the assembled route cost."""
        return within_spec(self.assemble(), low_ohms, high_ohms)
