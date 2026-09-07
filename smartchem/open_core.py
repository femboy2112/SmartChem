"""A domain-neutral open symmetric-monoidal diagram core with a monoidal decoration slot.

This module generalises :mod:`smartchem.open_diagram` (the proven electrical open-SMC core)
in exactly the two ways the Move-1 keystone contract requires
(``docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md``):

* **multi-terminal hyperedges** -- a :class:`Hyperedge` connects an *ordered* tuple of typed
  terminals, not exactly two, so one edge can hold an ``N`` reactant -> ``M`` product event;
* a **general monoidal decoration slot** -- every diagram carries one :class:`Decoration`,
  a payload with a declared combine law under ``then``/``tensor`` and an interchange-invariance
  obligation, so a *future* decoration (an additive ``ReactionR`` for a free-energy drive, a
  multiplicative ``[0, 1]`` for a survival fraction) drops in without touching this core.

Like :mod:`smartchem.open_diagram` this module is deliberately only *structure*.  It records
typed nodes, hyperedge incidence, and an opaque decoration; it interprets no port token, no
generator payload, and no decoration content as physics.  A port token is an opaque ``str``:
the electrical layer would map ``PortKind.ELECTRICAL`` to ``"electrical"`` and the chemistry
layer (:mod:`smartchem.open_chem_diagram`) maps a species to its resonance identity.

``then`` and ``tensor`` are total operations on finite presentations.  The ``canonicalize``
*observer* is resource bounded: its exact residual search is factorial on highly symmetric
internal nodes, so it raises :class:`CanonicalizationBudgetExceeded` rather than turning an
exact comparison into an ID-dependent or approximate one.  The refusal does not make
composition itself partial -- it is a fail-closed boundary on the *quotient*, mirroring
:mod:`smartchem.open_diagram`.

The core is written so it *could* host the electrical layer later (Rung C+); this Rung B does
not migrate ``open_diagram.py`` onto it.  The electrical layer would supply a trivial
:data:`UNIT_DECORATION`; the chemistry layer supplies a product-of-decorations apex.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from itertools import permutations, product
from math import factorial
from typing import Iterator

__all__ = [
    "CanonicalDiagram",
    "CanonicalizationBudgetExceeded",
    "Decoration",
    "DiagramCompositionError",
    "DiagramConstructionError",
    "Hyperedge",
    "Interface",
    "OpenDiagram",
    "Terminal",
    "UNIT_DECORATION",
    "UnitDecoration",
    "braid",
    "canonicalize",
    "identity",
    "unit_interface",
]


class DiagramConstructionError(ValueError):
    """Raised when a raw presentation does not describe a well-formed open diagram."""


class DiagramCompositionError(ValueError):
    """Raised when two diagrams have mismatched composition interfaces."""


class CanonicalizationBudgetExceeded(RuntimeError):
    """Exact alpha-invariant comparison exceeded its declared finite search budget."""


# ======================================================================================
# The monoidal decoration slot (Level 2 of the two-level design)
# ======================================================================================
class Decoration(abc.ABC):
    """A monoidal payload riding a diagram's apex.

    A decoration is combined under sequential composition (:meth:`then_combine`) and parallel
    composition (:meth:`tensor_combine`).  A concrete decoration also declares an *identity*
    element (the value a wire/identity diagram carries); because the identity of the provenance
    monoid is sized by the boundary, the identity is supplied by the domain layer when it builds
    :func:`identity`/:func:`braid`, rather than being a single constant here.

    **Interchange-invariance obligation.** For the Level-1 structural quotient (:func:`canonicalize`)
    to be sound, a decoration MUST satisfy the interchange law under its own combine operations::

        (a.then_combine(b)).tensor_combine(c.then_combine(d))
            == (a.tensor_combine(c)).then_combine(b.tensor_combine(d))

    i.e. the decoration value of a process must not depend on the order independent parallel
    events were scheduled.  An *additive* target (a real for a free-energy drive), a
    *multiplicative* target (``[0, 1]`` for a survival fraction), and the two decorations the
    chemistry layer instantiates (an additive net conservation vector; a causal-DAG provenance
    monoid) all satisfy it.  The chemistry layer's tests prove it for its instances.
    """

    @abc.abstractmethod
    def then_combine(self, other: "Decoration") -> "Decoration":
        """Combine two decorations glued in series (``self`` before ``other``)."""

    @abc.abstractmethod
    def tensor_combine(self, other: "Decoration") -> "Decoration":
        """Combine two decorations placed in parallel (``self`` beside ``other``)."""


@dataclass(frozen=True)
class UnitDecoration(Decoration):
    """The trivial decoration: a diagram that decorates nothing (e.g. a bare electrical core).

    It is both the identity and the whole monoid -- combining two units yields a unit -- so a
    domain that needs no apex content simply carries :data:`UNIT_DECORATION` everywhere.
    """

    def then_combine(self, other: "Decoration") -> "Decoration":
        if type(other) is not UnitDecoration:
            raise DiagramCompositionError("cannot combine a UnitDecoration with a decorated diagram")
        return self

    def tensor_combine(self, other: "Decoration") -> "Decoration":
        if type(other) is not UnitDecoration:
            raise DiagramCompositionError("cannot combine a UnitDecoration with a decorated diagram")
        return self


#: The shared trivial decoration for domains that do not decorate their apex.
UNIT_DECORATION = UnitDecoration()


# ======================================================================================
# Level 1 -- structural presentation
# ======================================================================================
@dataclass(frozen=True)
class Interface:
    """An ordered typed boundary.  Position, not a user ID, is boundary identity.

    A port token is an opaque, order-comparable ``str``; the core never interprets it.
    """

    ports: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.ports) is not tuple:
            raise DiagramConstructionError("Interface.ports must be a tuple")
        if any(type(port) is not str for port in self.ports):
            raise DiagramConstructionError("Interface.ports must contain string port tokens")

    def tensor(self, other: "Interface") -> "Interface":
        if type(other) is not Interface:
            raise TypeError("other must be an Interface")
        return Interface(self.ports + other.ports)

    def __len__(self) -> int:
        return len(self.ports)


@dataclass(frozen=True)
class Terminal:
    """One incidence of a hyperedge onto a node, tagged by an opaque role token.

    The role (``"reactant"``/``"product"`` in the chemistry layer) distinguishes the two ends
    of a directed multi-terminal event and takes part in the quotient colouring and equality.
    """

    role: str
    node: int

    def __post_init__(self) -> None:
        if type(self.role) is not str or not self.role:
            raise DiagramConstructionError("Terminal.role must be a non-empty string")
        if type(self.node) is not int or self.node < 0:
            raise DiagramConstructionError("Terminal.node must be a non-negative integer")


@dataclass(frozen=True)
class Hyperedge:
    """One multi-terminal generator occurrence.

    ``kind`` is a syntactic family tag and ``payload`` is an opaque, declaration-aligned domain
    label (a generator identity); both take part in the quotient but this core neither interprets
    nor validates them as physics.  ``terminals`` is the ordered incidence onto nodes.
    """

    kind: str
    payload: str
    terminals: tuple[Terminal, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not str or not self.kind:
            raise DiagramConstructionError("Hyperedge.kind must be a non-empty string")
        if type(self.payload) is not str:
            raise DiagramConstructionError("Hyperedge.payload must be a string")
        if type(self.terminals) is not tuple or any(
            type(t) is not Terminal for t in self.terminals
        ):
            raise DiagramConstructionError("Hyperedge.terminals must be a tuple of Terminal values")
        if not self.terminals:
            raise DiagramConstructionError("a hyperedge must have at least one terminal")


@dataclass(frozen=True)
class OpenDiagram:
    """A finite presentation of a typed open diagram with a decorated apex.

    Fields mirror :class:`smartchem.open_diagram.OpenDiagram` but generalised: ``node_ports``
    types every internal node with an opaque token; ``input_nodes``/``output_nodes`` map the
    ordered boundary onto nodes; ``hyperedges`` are multi-terminal; ``decoration`` is the apex.

    Unlike the electrical core this presentation deliberately does **not** enforce a
    Kirchhoff-style minimum incidence.  A node incident to exactly one hyperedge terminal and no
    boundary port is an *unfilled slot* -- the OPEN state the chemistry layer reads as
    "conservation UNDECIDED".  Raw presentations are not alpha-invariant; use :func:`canonicalize`.
    """

    dom: Interface
    cod: Interface
    input_nodes: tuple[int, ...]
    output_nodes: tuple[int, ...]
    node_ports: tuple[str, ...]
    hyperedges: tuple[Hyperedge, ...]
    decoration: Decoration

    def __post_init__(self) -> None:
        if type(self.dom) is not Interface or type(self.cod) is not Interface:
            raise DiagramConstructionError("dom and cod must be exact Interface values")
        for name in ("input_nodes", "output_nodes", "node_ports", "hyperedges"):
            if type(getattr(self, name)) is not tuple:
                raise DiagramConstructionError(f"{name} must be a tuple")
        if not isinstance(self.decoration, Decoration):
            raise DiagramConstructionError("decoration must be a Decoration")
        if len(self.input_nodes) != len(self.dom.ports):
            raise DiagramConstructionError("input node count must match the domain interface")
        if len(self.output_nodes) != len(self.cod.ports):
            raise DiagramConstructionError("output node count must match the codomain interface")
        if any(type(port) is not str for port in self.node_ports):
            raise DiagramConstructionError("node_ports must contain string port tokens")
        if any(type(edge) is not Hyperedge for edge in self.hyperedges):
            raise DiagramConstructionError("hyperedges must contain Hyperedge values")
        n = len(self.node_ports)
        for node in self.input_nodes + self.output_nodes:
            if type(node) is not int or not 0 <= node < n:
                raise DiagramConstructionError("boundary maps must name extant integer nodes")
        for index, port in enumerate(self.dom.ports):
            if self.node_ports[self.input_nodes[index]] != port:
                raise DiagramConstructionError("input boundary token does not match its node")
        for index, port in enumerate(self.cod.ports):
            if self.node_ports[self.output_nodes[index]] != port:
                raise DiagramConstructionError("output boundary token does not match its node")
        for edge in self.hyperedges:
            for terminal in edge.terminals:
                if not 0 <= terminal.node < n:
                    raise DiagramConstructionError("hyperedge terminal names an unknown node")

    # -- reads -------------------------------------------------------------------------
    def terminal_incidence(self) -> tuple[int, ...]:
        """Per-node count of hyperedge-terminal incidences (boundary ports excluded)."""
        counts = [0] * len(self.node_ports)
        for edge in self.hyperedges:
            for terminal in edge.terminals:
                counts[terminal.node] += 1
        return tuple(counts)

    def edge_incidence(self) -> tuple[int, ...]:
        """Per-node count of DISTINCT hyperedges incident on it (a self-incidence counts once).

        This is the semantically correct "is this node shared between generators?" measure: a node
        touched twice by ONE hyperedge (a symmetric ``A + A -> ...`` on a single node) is incident to
        one generator, not glued to a second, so it is NOT internal.  A chemistry node glued between a
        producer step and a consumer step is incident to two distinct hyperedges.  (The chemistry layer
        classifies port states off this, not the raw terminal count -- closes Rung-B open-debt 5.)"""
        counts = [0] * len(self.node_ports)
        for edge in self.hyperedges:
            for node in {terminal.node for terminal in edge.terminals}:
                counts[node] += 1
        return tuple(counts)

    # -- composition -------------------------------------------------------------------
    def then(self, other: "OpenDiagram") -> "OpenDiagram":
        """Total boundary gluing (pushout along the shared interface).  Never canonicalises."""
        if type(other) is not OpenDiagram:
            raise TypeError("other must be an OpenDiagram")
        if self.cod != other.dom:
            raise DiagramCompositionError("codomain must exactly equal the other domain")
        first_n = len(self.node_ports)
        parent = list(range(first_n + len(other.node_ports)))

        def find(node: int) -> int:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left: int, right: int) -> None:
            left, right = find(left), find(right)
            if left != right:
                if left < right:
                    parent[right] = left
                else:
                    parent[left] = right

        for left, right in zip(self.output_nodes, other.input_nodes):
            union(left, first_n + right)
        roots = sorted({find(node) for node in range(len(parent))})
        compact = {root: index for index, root in enumerate(roots)}

        def remap(node: int) -> int:
            return compact[find(node)]

        old_ports = self.node_ports + other.node_ports
        node_ports: list[str | None] = [None] * len(roots)
        for old, port in enumerate(old_ports):
            target = remap(old)
            previous = node_ports[target]
            if previous is not None and previous != port:
                raise DiagramCompositionError("glued nodes have incompatible port tokens")
            node_ports[target] = port
        hyperedges = tuple(
            _remap_edge(edge, remap, 0) for edge in self.hyperedges
        ) + tuple(_remap_edge(edge, remap, first_n) for edge in other.hyperedges)
        return OpenDiagram(
            self.dom,
            other.cod,
            tuple(remap(node) for node in self.input_nodes),
            tuple(remap(first_n + node) for node in other.output_nodes),
            tuple(port for port in node_ports if port is not None),
            hyperedges,
            self.decoration.then_combine(other.decoration),
        )

    def tensor(self, other: "OpenDiagram") -> "OpenDiagram":
        """Total disjoint union with ordered boundary concatenation."""
        if type(other) is not OpenDiagram:
            raise TypeError("other must be an OpenDiagram")
        offset = len(self.node_ports)
        return OpenDiagram(
            self.dom.tensor(other.dom),
            self.cod.tensor(other.cod),
            self.input_nodes + tuple(offset + node for node in other.input_nodes),
            self.output_nodes + tuple(offset + node for node in other.output_nodes),
            self.node_ports + other.node_ports,
            self.hyperedges + tuple(_remap_edge(edge, lambda x: x, offset) for edge in other.hyperedges),
            self.decoration.tensor_combine(other.decoration),
        )

    def plug_all(self, pairs: tuple[tuple[int, int], ...]) -> "OpenDiagram":
        """Glue selected output ports to input ports in ONE partial pushout; keep the rest boundary.

        ``pairs`` are ``(output_position, input_position)`` indices into ``self.output_nodes`` /
        ``self.input_nodes``.  Each pair unions its two boundary nodes (which must carry the same port
        token) into one node that leaves the boundary (it becomes INTERNAL -- incident to the two
        generators the two ports belonged to); every UNMATCHED port stays on the composite boundary.

        ``then`` is the special case that plugs every output to the matching input across two diagrams;
        ``plug_all`` is the generalisation *within* one (already tensored) diagram, plugging only a
        chosen subset -- which is exactly what lets a multi-step route/DAG, whose steps carry byproducts
        and fresh leaf inputs, compose at only its shared intermediates.  It never canonicalises, and the
        apex decoration rides through unchanged: plugging removes no hyperedge, so a homomorphic sum/
        product apex quantity (conservation, and the future free-energy/survival functors) is invariant.
        """
        if type(pairs) is not tuple:
            raise TypeError("pairs must be a tuple of (output_position, input_position) pairs")
        out_positions = [op for op, _ in pairs]
        in_positions = [ip for _, ip in pairs]
        if len(set(out_positions)) != len(out_positions) or len(set(in_positions)) != len(in_positions):
            raise DiagramCompositionError("each boundary port may be plugged at most once")
        n = len(self.node_ports)
        parent = list(range(n))

        def find(node: int) -> int:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left: int, right: int) -> None:
            left, right = find(left), find(right)
            if left != right:
                if left < right:
                    parent[right] = left
                else:
                    parent[left] = right

        for op, ip in pairs:
            if not (0 <= op < len(self.output_nodes)) or not (0 <= ip < len(self.input_nodes)):
                raise DiagramCompositionError("plug position is out of range")
            out_node = self.output_nodes[op]
            in_node = self.input_nodes[ip]
            if out_node == in_node:
                # An output and input that ALREADY name the same node (a wire whose one node is both):
                # "plugging" it removes both boundary occurrences and leaves an orphan node with no
                # boundary and no incident hyperedge.  Refuse -- a port cannot be plugged into itself.
                raise DiagramCompositionError("cannot plug a port into its own node (would orphan it)")
            if self.node_ports[out_node] != self.node_ports[in_node]:
                raise DiagramCompositionError("plugged ports carry incompatible tokens")
            union(out_node, in_node)

        roots = sorted({find(node) for node in range(n)})
        compact = {root: index for index, root in enumerate(roots)}

        def remap(node: int) -> int:
            return compact[find(node)]

        node_ports: list[str | None] = [None] * len(roots)
        for old, port in enumerate(self.node_ports):
            target = remap(old)
            previous = node_ports[target]
            if previous is not None and previous != port:
                raise DiagramCompositionError("glued nodes have incompatible port tokens")
            node_ports[target] = port

        matched_out = set(out_positions)
        matched_in = set(in_positions)
        new_output_nodes = tuple(
            remap(node) for pos, node in enumerate(self.output_nodes) if pos not in matched_out
        )
        new_input_nodes = tuple(
            remap(node) for pos, node in enumerate(self.input_nodes) if pos not in matched_in
        )
        new_cod = Interface(tuple(port for pos, port in enumerate(self.cod.ports) if pos not in matched_out))
        new_dom = Interface(tuple(port for pos, port in enumerate(self.dom.ports) if pos not in matched_in))
        hyperedges = tuple(_remap_edge(edge, remap, 0) for edge in self.hyperedges)
        return OpenDiagram(
            new_dom,
            new_cod,
            new_input_nodes,
            new_output_nodes,
            tuple(port for port in node_ports if port is not None),
            hyperedges,
            self.decoration,
        )


def _remap_edge(edge: Hyperedge, remap, offset: int) -> Hyperedge:
    return Hyperedge(
        edge.kind,
        edge.payload,
        tuple(Terminal(t.role, remap(t.node + offset)) for t in edge.terminals),
    )


def unit_interface() -> Interface:
    """The empty ordered interface, the strict tensor unit."""
    return Interface(())


def identity(interface: Interface, *, decoration: Decoration = UNIT_DECORATION) -> OpenDiagram:
    """One wire node per boundary position, joining matching input/output occurrences.

    The ``decoration`` must be the domain's identity element sized for this interface (the
    chemistry layer passes ``ChemApex.identity(len(interface))``); it defaults to the trivial
    :data:`UNIT_DECORATION` for an undecorated domain.
    """
    if type(interface) is not Interface:
        raise TypeError("interface must be an Interface")
    nodes = tuple(range(len(interface.ports)))
    return OpenDiagram(interface, interface, nodes, nodes, interface.ports, (), decoration)


def braid(left: Interface, right: Interface, *, decoration: Decoration = UNIT_DECORATION) -> OpenDiagram:
    """The structural symmetry wire diagram ``left (x) right -> right (x) left``.

    A braid has no hyperedges, so its ``decoration`` is the domain's identity element sized for
    ``left (x) right`` (``len(left) + len(right)`` ports).
    """
    if type(left) is not Interface or type(right) is not Interface:
        raise TypeError("braid arguments must be Interface values")
    count_left = len(left.ports)
    total = count_left + len(right.ports)
    return OpenDiagram(
        left.tensor(right),
        right.tensor(left),
        tuple(range(total)),
        tuple(range(count_left, total)) + tuple(range(count_left)),
        left.ports + right.ports,
        (),
        decoration,
    )


# ======================================================================================
# The bounded exact canonical observer (the Level-1 structural quotient)
# ======================================================================================
@dataclass(frozen=True)
class CanonicalDiagram:
    """Comparable and hashable exact canonical observation of one open diagram.

    Equality is the quotiented structural equality *including the decoration*: two diagrams are
    equal iff they have the same boundary, the same canonical hyperedge topology, and equal
    apex decoration.  The decoration is carried verbatim -- it is node-relabelling invariant by
    construction (it references generator content, not internal node indices).
    """

    dom: Interface
    cod: Interface
    input_nodes: tuple[int, ...]
    output_nodes: tuple[int, ...]
    node_ports: tuple[str, ...]
    hyperedges: tuple[tuple[str, str, tuple[tuple[str, int], ...]], ...]
    decoration: Decoration


def _ranks(signatures: list[object]) -> tuple[int, ...]:
    rank_by_signature = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
    return tuple(rank_by_signature[signature] for signature in signatures)


def _refine_colours(diagram: OpenDiagram) -> tuple[int, ...]:
    """Relabelling-equivariant one-dimensional WL refinement over the hypergraph incidence."""
    n = len(diagram.node_ports)
    markers: list[list[tuple[str, int]]] = [[] for _ in range(n)]
    for index, node in enumerate(diagram.input_nodes):
        markers[node].append(("input", index))
    for index, node in enumerate(diagram.output_nodes):
        markers[node].append(("output", index))
    initial = [(diagram.node_ports[node], tuple(sorted(markers[node]))) for node in range(n)]
    colours = _ranks(initial)
    # For each node record every terminal incidence: (edge kind, edge payload, this role, and the
    # other terminals of that edge as (role, node) pairs whose colours are read in the loop).  A
    # node appearing at several terminals of one edge (a self-incidence) is recorded once each.
    incident: list[list[tuple[str, str, str, tuple[tuple[str, int], ...]]]] = [[] for _ in range(n)]
    for edge in diagram.hyperedges:
        for position, terminal in enumerate(edge.terminals):
            others = tuple(
                (other.role, other.node)
                for other_position, other in enumerate(edge.terminals)
                if other_position != position
            )
            incident[terminal.node].append((edge.kind, edge.payload, terminal.role, others))
    for _ in range(n):
        signatures = [
            (
                colours[node],
                tuple(
                    sorted(
                        (
                            kind,
                            payload,
                            role,
                            tuple(sorted((orole, colours[onode]) for orole, onode in others)),
                        )
                        for kind, payload, role, others in incident[node]
                    )
                ),
            )
            for node in range(n)
        ]
        refined = _ranks(signatures)
        if len(set(refined)) == len(set(colours)):
            return refined
        colours = refined
    return colours


def _blocks(colours: tuple[int, ...]) -> list[tuple[int, ...]]:
    grouped: dict[int, list[int]] = {}
    for node, colour in enumerate(colours):
        grouped.setdefault(colour, []).append(node)
    return [tuple(grouped[colour]) for colour in sorted(grouped)]


def _permutations_within(blocks: list[tuple[int, ...]], n: int) -> Iterator[tuple[int, ...]]:
    """Every relabelling that maps each final WL colour cell to its canonical block."""
    targets: list[tuple[int, ...]] = []
    position = 0
    for block in blocks:
        targets.append(tuple(range(position, position + len(block))))
        position += len(block)
    for choices in product(*(permutations(block) for block in blocks)):
        mapping = [0] * n
        for source_order, target_order in zip(choices, targets):
            for source, target in zip(source_order, target_order):
                mapping[source] = target
        yield tuple(mapping)


def _candidate_cost(blocks: list[tuple[int, ...]], budget: int) -> int:
    cost = 1
    for block in blocks:
        factor = factorial(len(block))
        if cost > budget // factor:
            raise CanonicalizationBudgetExceeded(
                "exact open-diagram canonicalization exceeds the declared candidate budget"
            )
        cost *= factor
    return cost


def _canonical_edge(edge: Hyperedge, mapping: tuple[int, ...]) -> tuple[str, str, tuple[tuple[str, int], ...]]:
    return (
        edge.kind,
        edge.payload,
        tuple(sorted((t.role, mapping[t.node]) for t in edge.terminals)),
    )


def canonicalize(diagram: OpenDiagram, *, budget: int = 100_000) -> CanonicalDiagram:
    """Return the exact alpha-invariant form, or explicitly refuse above ``budget``.

    The residual after WL refinement is searched by bounded brute force over intra-cell
    relabellings; above ``budget`` candidate relabellings it raises
    :class:`CanonicalizationBudgetExceeded` rather than returning an approximate or
    ID-dependent form.  This is the fail-closed boundary the chemistry layer surfaces as
    UNKNOWN -- chemistry apices are more symmetric than resistors, so it is load-bearing.
    """
    if type(diagram) is not OpenDiagram:
        raise TypeError("diagram must be an OpenDiagram")
    if type(budget) is not int or budget < 1:
        raise ValueError("budget must be a positive integer")
    colours = _refine_colours(diagram)
    blocks = _blocks(colours)
    _candidate_cost(blocks, budget)
    node_ports = tuple(diagram.node_ports[node] for block in blocks for node in block)
    best: tuple[tuple[int, ...], tuple[int, ...], tuple[tuple[str, str, tuple[tuple[str, int], ...]], ...]] | None = None
    for mapping in _permutations_within(blocks, len(diagram.node_ports)):
        edges = tuple(sorted(_canonical_edge(edge, mapping) for edge in diagram.hyperedges))
        candidate = (
            tuple(mapping[node] for node in diagram.input_nodes),
            tuple(mapping[node] for node in diagram.output_nodes),
            edges,
        )
        if best is None or candidate < best:
            best = candidate
    assert best is not None  # even the empty graph has its one empty permutation
    return CanonicalDiagram(
        diagram.dom, diagram.cod, best[0], best[1], node_ports, best[2], diagram.decoration
    )
