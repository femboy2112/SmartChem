"""Finite typed open-diagram syntax with a budgeted canonical observer.

This module is deliberately only *structure*.  It records typed electrical nodes and
two-terminal component incidence, but no resistance, drive, equation, solver, evidence,
or claim.  Those belong to a domain ``ModelIR`` and an execution layer.

``OpenDiagram.then`` and ``OpenDiagram.tensor`` are total operations on finite
presentations.  Their mathematical quotient by internal names is also total.  The
``canonicalize`` *observer* below is resource-bounded because its exact residual search is
factorial on highly symmetric internal nodes.  It therefore raises a named refusal rather
than turning an exact comparison into an ID-dependent or approximate one.  In particular,
the refusal does not make composition itself partial.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import permutations, product
from math import factorial
from typing import Iterator

__all__ = [
    "BoundaryRef",
    "BoundarySide",
    "CanonicalDiagram",
    "CanonicalizationBudgetExceeded",
    "ComponentKind",
    "ComponentSlot",
    "DiagramConstructionError",
    "DiagramCompositionError",
    "ElementPortRef",
    "Interface",
    "Junction",
    "OpenDiagram",
    "PortKind",
    "braid",
    "canonicalize",
    "identity",
    "unit_interface",
]


class DiagramConstructionError(ValueError):
    """Raised when a raw presentation does not describe a typed open diagram."""


class DiagramCompositionError(ValueError):
    """Raised when two diagrams have mismatched composition interfaces."""


class CanonicalizationBudgetExceeded(RuntimeError):
    """Exact alpha-invariant comparison exceeded its declared finite search budget."""


class PortKind(str, Enum):
    """Kinds currently admitted by the topology-only electrical control."""

    ELECTRICAL = "electrical"


class BoundarySide(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class ComponentKind(str, Enum):
    """Syntactic components; their constitutive parameters are intentionally absent."""

    ELECTRICAL_TWO_TERMINAL = "electrical-two-terminal"


def _nonempty_string(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise DiagramConstructionError(f"{name} must be a non-empty string")


def _exact_enum(value: object, enum_type: type[Enum], name: str) -> None:
    if type(value) is not enum_type:
        raise DiagramConstructionError(f"{name} must be a {enum_type.__name__}")


@dataclass(frozen=True)
class Interface:
    """An ordered typed boundary.  Position, not a user ID, is boundary identity."""

    ports: tuple[PortKind, ...]

    def __post_init__(self) -> None:
        if type(self.ports) is not tuple:
            raise DiagramConstructionError("Interface.ports must be a tuple")
        if any(type(port) is not PortKind for port in self.ports):
            raise DiagramConstructionError("Interface.ports must contain PortKind values")

    def tensor(self, other: "Interface") -> "Interface":
        if type(other) is not Interface:
            raise TypeError("other must be an Interface")
        return Interface(self.ports + other.ports)


@dataclass(frozen=True)
class BoundaryRef:
    side: BoundarySide
    index: int

    def __post_init__(self) -> None:
        _exact_enum(self.side, BoundarySide, "side")
        if type(self.index) is not int or self.index < 0:
            raise DiagramConstructionError("boundary index must be a non-negative integer")


@dataclass(frozen=True)
class ComponentSlot:
    """Construction-local name and syntactic kind of one two-terminal component."""

    component_id: str
    kind: ComponentKind

    def __post_init__(self) -> None:
        _nonempty_string(self.component_id, "component_id")
        _exact_enum(self.kind, ComponentKind, "kind")


@dataclass(frozen=True)
class ElementPortRef:
    """One named terminal of a construction-local component."""

    component_id: str
    terminal: str

    def __post_init__(self) -> None:
        _nonempty_string(self.component_id, "component_id")
        if self.terminal not in ("a", "b"):
            raise DiagramConstructionError("component terminal must be exactly 'a' or 'b'")


EndpointRef = BoundaryRef | ElementPortRef
_PRESENTATION_TOKEN = object()


@dataclass(frozen=True)
class Junction:
    """A construction-local, unordered multiway node junction."""

    junction_id: str
    kind: PortKind
    endpoints: tuple[EndpointRef, ...]

    def __post_init__(self) -> None:
        _nonempty_string(self.junction_id, "junction_id")
        _exact_enum(self.kind, PortKind, "kind")
        if type(self.endpoints) is not tuple:
            raise DiagramConstructionError("Junction.endpoints must be a tuple")
        if len(self.endpoints) < 2:
            raise DiagramConstructionError("a junction requires at least two endpoints")
        if any(type(item) not in (BoundaryRef, ElementPortRef) for item in self.endpoints):
            raise DiagramConstructionError(
                "Junction.endpoints must contain BoundaryRef or ElementPortRef values"
            )


@dataclass(frozen=True)
class _Edge:
    """ID-free component incidence retained in component declaration order."""

    kind: ComponentKind
    node_a: int
    node_b: int

    def __post_init__(self) -> None:
        _exact_enum(self.kind, ComponentKind, "edge kind")
        if type(self.node_a) is not int or type(self.node_b) is not int:
            raise DiagramConstructionError("edge nodes must be integers")


@dataclass(frozen=True, init=False)
class OpenDiagram:
    """A finite presentation of a typed open diagram.

    The class stores no construction-local component or junction identifiers.  It does
    retain edge declaration order so a domain model can align its own opaque component
    data by edge index.  Consequently raw presentations are not themselves alpha-invariant
    values: use :func:`canonicalize` when exact quotient equality or a cache key is needed.
    """

    dom: Interface
    cod: Interface
    input_nodes: tuple[int, ...]
    output_nodes: tuple[int, ...]
    node_kinds: tuple[PortKind, ...]
    edges: tuple[_Edge, ...]

    def __init__(
        self,
        dom: Interface,
        cod: Interface,
        input_nodes: tuple[int, ...],
        output_nodes: tuple[int, ...],
        node_kinds: tuple[PortKind, ...],
        edges: tuple[_Edge, ...],
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _PRESENTATION_TOKEN:
            raise DiagramConstructionError(
                "OpenDiagram presentations are internal; use OpenDiagram.build, identity, or braid"
            )
        object.__setattr__(self, "dom", dom)
        object.__setattr__(self, "cod", cod)
        object.__setattr__(self, "input_nodes", input_nodes)
        object.__setattr__(self, "output_nodes", output_nodes)
        object.__setattr__(self, "node_kinds", node_kinds)
        object.__setattr__(self, "edges", edges)
        self.__post_init__()

    @classmethod
    def _from_presentation(
        cls,
        dom: Interface,
        cod: Interface,
        input_nodes: tuple[int, ...],
        output_nodes: tuple[int, ...],
        node_kinds: tuple[PortKind, ...],
        edges: tuple[_Edge, ...],
    ) -> "OpenDiagram":
        return cls(dom, cod, input_nodes, output_nodes, node_kinds, edges, _token=_PRESENTATION_TOKEN)

    def __post_init__(self) -> None:
        if type(self.dom) is not Interface or type(self.cod) is not Interface:
            raise DiagramConstructionError("dom and cod must be exact Interface values")
        for name in ("input_nodes", "output_nodes", "node_kinds", "edges"):
            if type(getattr(self, name)) is not tuple:
                raise DiagramConstructionError(f"{name} must be a tuple")
        if len(self.input_nodes) != len(self.dom.ports):
            raise DiagramConstructionError("input node count must match the domain interface")
        if len(self.output_nodes) != len(self.cod.ports):
            raise DiagramConstructionError("output node count must match the codomain interface")
        if any(type(kind) is not PortKind for kind in self.node_kinds):
            raise DiagramConstructionError("node_kinds must contain PortKind values")
        if any(type(edge) is not _Edge for edge in self.edges):
            raise DiagramConstructionError("edges must contain internal structural edges")
        n = len(self.node_kinds)
        for node in self.input_nodes + self.output_nodes:
            if type(node) is not int or not 0 <= node < n:
                raise DiagramConstructionError("boundary maps must name extant integer nodes")
        for index, kind in enumerate(self.dom.ports):
            if self.node_kinds[self.input_nodes[index]] is not kind:
                raise DiagramConstructionError("input boundary kind does not match its node")
        for index, kind in enumerate(self.cod.ports):
            if self.node_kinds[self.output_nodes[index]] is not kind:
                raise DiagramConstructionError("output boundary kind does not match its node")
        for edge in self.edges:
            if not (0 <= edge.node_a < n and 0 <= edge.node_b < n):
                raise DiagramConstructionError("edge names an unknown node")
            if self.node_kinds[edge.node_a] is not PortKind.ELECTRICAL:
                raise DiagramConstructionError("electrical component endpoint has non-electrical node")
            if self.node_kinds[edge.node_b] is not PortKind.ELECTRICAL:
                raise DiagramConstructionError("electrical component endpoint has non-electrical node")
        incidences = [0] * n
        for node in self.input_nodes + self.output_nodes:
            incidences[node] += 1
        for edge in self.edges:
            incidences[edge.node_a] += 1
            incidences[edge.node_b] += 1
        if any(count < 2 for count in incidences):
            raise DiagramConstructionError("every retained node must have at least two endpoint incidences")

    @classmethod
    def build(
        cls,
        dom: Interface,
        cod: Interface,
        components: tuple[ComponentSlot, ...],
        junctions: tuple[Junction, ...],
    ) -> "OpenDiagram":
        """Resolve a raw-ID presentation and discard those IDs from the stored diagram."""
        if type(dom) is not Interface or type(cod) is not Interface:
            raise DiagramConstructionError("dom and cod must be exact Interface values")
        if type(components) is not tuple or type(junctions) is not tuple:
            raise DiagramConstructionError("components and junctions must be tuples")
        if any(type(component) is not ComponentSlot for component in components):
            raise DiagramConstructionError("components must contain ComponentSlot values")
        if any(type(junction) is not Junction for junction in junctions):
            raise DiagramConstructionError("junctions must contain Junction values")
        component_by_id = {component.component_id: component for component in components}
        if len(component_by_id) != len(components):
            raise DiagramConstructionError("component IDs must be unique")
        junction_ids = {junction.junction_id for junction in junctions}
        if len(junction_ids) != len(junctions):
            raise DiagramConstructionError("junction IDs must be unique")

        expected: set[EndpointRef] = {
            *(BoundaryRef(BoundarySide.INPUT, index) for index in range(len(dom.ports))),
            *(BoundaryRef(BoundarySide.OUTPUT, index) for index in range(len(cod.ports))),
        }
        for component in components:
            expected.add(ElementPortRef(component.component_id, "a"))
            expected.add(ElementPortRef(component.component_id, "b"))
        node_for: dict[EndpointRef, int] = {}
        node_kinds: list[PortKind] = []
        for node, junction in enumerate(junctions):
            node_kinds.append(junction.kind)
            for endpoint in junction.endpoints:
                if endpoint in node_for:
                    raise DiagramConstructionError(f"endpoint occurs more than once: {endpoint!r}")
                if isinstance(endpoint, BoundaryRef):
                    ports = dom.ports if endpoint.side is BoundarySide.INPUT else cod.ports
                    if endpoint.index >= len(ports):
                        raise DiagramConstructionError(f"boundary endpoint is out of range: {endpoint!r}")
                    expected_kind = ports[endpoint.index]
                else:
                    component = component_by_id.get(endpoint.component_id)
                    if component is None:
                        raise DiagramConstructionError(
                            f"endpoint names unknown component {endpoint.component_id!r}"
                        )
                    expected_kind = PortKind.ELECTRICAL
                if endpoint not in expected:
                    raise DiagramConstructionError(f"unknown endpoint: {endpoint!r}")
                if junction.kind is not expected_kind:
                    raise DiagramConstructionError("junction kind is incompatible with one endpoint")
                node_for[endpoint] = node
        missing = expected - set(node_for)
        if missing:
            raise DiagramConstructionError(f"endpoints are not covered exactly once: {sorted(missing, key=repr)!r}")

        input_nodes = tuple(node_for[BoundaryRef(BoundarySide.INPUT, i)] for i in range(len(dom.ports)))
        output_nodes = tuple(node_for[BoundaryRef(BoundarySide.OUTPUT, i)] for i in range(len(cod.ports)))
        edges = tuple(
            _Edge(
                component.kind,
                node_for[ElementPortRef(component.component_id, "a")],
                node_for[ElementPortRef(component.component_id, "b")],
            )
            for component in components
        )
        return cls._from_presentation(dom, cod, input_nodes, output_nodes, tuple(node_kinds), edges)

    def node_for(self, boundary: BoundaryRef) -> int:
        """Resolve a public boundary position to its stored presentation node."""
        if type(boundary) is not BoundaryRef:
            raise TypeError("boundary must be a BoundaryRef")
        nodes = self.input_nodes if boundary.side is BoundarySide.INPUT else self.output_nodes
        if boundary.index >= len(nodes):
            raise DiagramConstructionError("boundary reference is out of range for this diagram")
        return nodes[boundary.index]

    def then(self, other: "OpenDiagram") -> "OpenDiagram":
        """Total boundary gluing.  It never invokes the bounded canonical observer."""
        if type(other) is not OpenDiagram:
            raise TypeError("other must be an OpenDiagram")
        if self.cod != other.dom:
            raise DiagramCompositionError("codomain must exactly equal the other domain")
        first_n = len(self.node_kinds)
        parent = list(range(first_n + len(other.node_kinds)))

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
        remap = lambda node: compact[find(node)]
        old_kinds = self.node_kinds + other.node_kinds
        node_kinds: list[PortKind | None] = [None] * len(roots)
        for old, kind in enumerate(old_kinds):
            target = remap(old)
            previous = node_kinds[target]
            if previous is not None and previous is not kind:
                raise DiagramCompositionError("glued nodes have incompatible port kinds")
            node_kinds[target] = kind
        edges = tuple(
            _Edge(edge.kind, remap(edge.node_a), remap(edge.node_b))
            for edge in self.edges
        ) + tuple(
            _Edge(edge.kind, remap(first_n + edge.node_a), remap(first_n + edge.node_b))
            for edge in other.edges
        )
        return OpenDiagram._from_presentation(
            self.dom,
            other.cod,
            tuple(remap(node) for node in self.input_nodes),
            tuple(remap(first_n + node) for node in other.output_nodes),
            tuple(kind for kind in node_kinds if kind is not None),
            edges,
        )

    def tensor(self, other: "OpenDiagram") -> "OpenDiagram":
        """Total disjoint union with ordered boundary concatenation."""
        if type(other) is not OpenDiagram:
            raise TypeError("other must be an OpenDiagram")
        offset = len(self.node_kinds)
        return OpenDiagram._from_presentation(
            self.dom.tensor(other.dom),
            self.cod.tensor(other.cod),
            self.input_nodes + tuple(offset + node for node in other.input_nodes),
            self.output_nodes + tuple(offset + node for node in other.output_nodes),
            self.node_kinds + other.node_kinds,
            self.edges
            + tuple(_Edge(edge.kind, offset + edge.node_a, offset + edge.node_b) for edge in other.edges),
        )


def unit_interface() -> Interface:
    """The empty ordered interface, the strict tensor unit."""
    return Interface(())


def identity(interface: Interface) -> OpenDiagram:
    """One wire node per boundary position, joining matching input/output occurrences."""
    if type(interface) is not Interface:
        raise TypeError("interface must be an Interface")
    nodes = tuple(range(len(interface.ports)))
    return OpenDiagram._from_presentation(interface, interface, nodes, nodes, interface.ports, ())


def braid(left: Interface, right: Interface) -> OpenDiagram:
    """The structural symmetry wire diagram ``left ⊗ right → right ⊗ left``."""
    if type(left) is not Interface or type(right) is not Interface:
        raise TypeError("braid arguments must be Interface values")
    count_left = len(left.ports)
    total = count_left + len(right.ports)
    return OpenDiagram._from_presentation(
        left.tensor(right),
        right.tensor(left),
        tuple(range(total)),
        tuple(range(count_left, total)) + tuple(range(count_left)),
        left.ports + right.ports,
        (),
    )


@dataclass(frozen=True)
class CanonicalDiagram:
    """Comparable and hashable exact canonical observation of one open diagram."""

    dom: Interface
    cod: Interface
    input_nodes: tuple[int, ...]
    output_nodes: tuple[int, ...]
    node_kinds: tuple[PortKind, ...]
    edges: tuple[tuple[str, str | None, int, int], ...]


def _refine_colours(diagram: OpenDiagram, labels: tuple[str | None, ...]) -> tuple[int, ...]:
    """Relabelling-equivariant one-dimensional WL refinement with edge multiplicity."""
    n = len(diagram.node_kinds)
    markers: list[list[tuple[str, int]]] = [[] for _ in range(n)]
    for index, node in enumerate(diagram.input_nodes):
        markers[node].append((BoundarySide.INPUT.value, index))
    for index, node in enumerate(diagram.output_nodes):
        markers[node].append((BoundarySide.OUTPUT.value, index))
    initial = [(diagram.node_kinds[node].value, tuple(sorted(markers[node]))) for node in range(n)]

    def ranks(signatures: list[object]) -> tuple[int, ...]:
        rank_by_signature = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
        return tuple(rank_by_signature[signature] for signature in signatures)

    colours = ranks(initial)
    incident: list[list[tuple[str, str | None, int]]] = [[] for _ in range(n)]
    for edge, label in zip(diagram.edges, labels):
        # A self-loop has two terminal incidences at the same node; do not collapse it.
        incident[edge.node_a].append((edge.kind.value, label, edge.node_b))
        incident[edge.node_b].append((edge.kind.value, label, edge.node_a))
    for _ in range(n):
        signatures = [
            (
                colours[node],
                tuple(
                    sorted((kind, label, colours[neighbor]) for kind, label, neighbor in incident[node])
                ),
            )
            for node in range(n)
        ]
        refined = ranks(signatures)
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


def canonicalize(
    diagram: OpenDiagram,
    *,
    budget: int = 100_000,
    edge_labels: tuple[str, ...] | None = None,
) -> CanonicalDiagram:
    """Return exact alpha-invariant form, or explicitly refuse above ``budget``.

    ``edge_labels`` are opaque, declaration-order-aligned domain decorations.  They take
    part in equality but this topology module neither interprets nor validates them as
    physical parameters.  The returned edge sequence is sorted canonically; the original
    presentation's ``diagram.edges`` remains declaration ordered for ModelIR alignment.
    """
    if type(diagram) is not OpenDiagram:
        raise TypeError("diagram must be an OpenDiagram")
    if type(budget) is not int or budget < 1:
        raise ValueError("budget must be a positive integer")
    if edge_labels is None:
        labels: tuple[str | None, ...] = (None,) * len(diagram.edges)
    else:
        if type(edge_labels) is not tuple or len(edge_labels) != len(diagram.edges):
            raise DiagramConstructionError("edge_labels must be a tuple aligned with diagram.edges")
        if any(type(label) is not str for label in edge_labels):
            raise DiagramConstructionError("edge_labels must contain opaque string values")
        labels = edge_labels
    colours = _refine_colours(diagram, labels)
    blocks = _blocks(colours)
    _candidate_cost(blocks, budget)
    node_kinds = tuple(diagram.node_kinds[node] for block in blocks for node in block)
    best: tuple[tuple[int, ...], tuple[int, ...], tuple[tuple[str, str | None, int, int], ...]] | None = None
    for mapping in _permutations_within(blocks, len(diagram.node_kinds)):
        edges = tuple(sorted(
            (
                edge.kind.value,
                label,
                min(mapping[edge.node_a], mapping[edge.node_b]),
                max(mapping[edge.node_a], mapping[edge.node_b]),
            )
            for edge, label in zip(diagram.edges, labels)
        ))
        candidate = (
            tuple(mapping[node] for node in diagram.input_nodes),
            tuple(mapping[node] for node in diagram.output_nodes),
            edges,
        )
        if best is None or candidate < best:
            best = candidate
    assert best is not None  # even the empty graph has its one empty permutation
    return CanonicalDiagram(diagram.dom, diagram.cod, best[0], best[1], node_kinds, best[2])
