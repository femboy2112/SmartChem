"""Adversarial controls for the finite open-diagram syntax.

These tests intentionally distinguish total presentation operations from the bounded exact
canonical observer.  Passing them is evidence about finite constructed diagrams, not a
formal proof over arbitrary Python objects.
"""
from __future__ import annotations

from itertools import permutations

import pytest

from smartchem.open_diagram import (
    BoundaryRef,
    BoundarySide,
    CanonicalizationBudgetExceeded,
    ComponentKind,
    ComponentSlot,
    DiagramConstructionError,
    DiagramCompositionError,
    ElementPortRef,
    Interface,
    Junction,
    OpenDiagram,
    PortKind,
    braid,
    canonicalize,
    identity,
    unit_interface,
)
from smartchem.open_diagram import _refine_colours


E = PortKind.ELECTRICAL
ONE = Interface((E,))
TWO = Interface((E, E))


def _resistor(component_id: str = "r") -> OpenDiagram:
    return OpenDiagram.build(
        ONE,
        ONE,
        (ComponentSlot(component_id, ComponentKind.ELECTRICAL_TWO_TERMINAL),),
        (
            Junction("left", E, (BoundaryRef(BoundarySide.INPUT, 0), ElementPortRef(component_id, "a"))),
            Junction("right", E, (ElementPortRef(component_id, "b"), BoundaryRef(BoundarySide.OUTPUT, 0))),
        ),
    )


def _parallel(component_ids: tuple[str, str], *, reverse_junctions: bool = False) -> OpenDiagram:
    first, second = component_ids
    components = tuple(
        ComponentSlot(component_id, ComponentKind.ELECTRICAL_TWO_TERMINAL)
        for component_id in component_ids
    )
    junctions = (
        Junction(
            "left",
            E,
            (BoundaryRef(BoundarySide.INPUT, 0), ElementPortRef(first, "a"), ElementPortRef(second, "a")),
        ),
        Junction(
            "right",
            E,
            (ElementPortRef(second, "b"), BoundaryRef(BoundarySide.OUTPUT, 0), ElementPortRef(first, "b")),
        ),
    )
    return OpenDiagram.build(ONE, ONE, components, tuple(reversed(junctions)) if reverse_junctions else junctions)


def _closed_self_loop(component_id: str = "loop") -> OpenDiagram:
    return OpenDiagram.build(
        unit_interface(),
        unit_interface(),
        (ComponentSlot(component_id, ComponentKind.ELECTRICAL_TWO_TERMINAL),),
        (Junction("node", E, (ElementPortRef(component_id, "a"), ElementPortRef(component_id, "b"))),),
    )


class TestConstruction:
    def test_component_ids_are_resolved_then_discarded_and_edge_order_is_retained(self):
        diagram = _parallel(("first", "second"))
        assert not hasattr(diagram, "components")
        assert len(diagram.edges) == 2
        assert diagram.edges[0].node_a == diagram.input_nodes[0]
        assert diagram.edges[1].node_b == diagram.output_nodes[0]

    def test_unknown_component_and_missing_terminal_refuse(self):
        with pytest.raises(DiagramConstructionError, match="unknown component"):
            OpenDiagram.build(
                ONE,
                ONE,
                (ComponentSlot("r", ComponentKind.ELECTRICAL_TWO_TERMINAL),),
                (
                    Junction("a", E, (BoundaryRef(BoundarySide.INPUT, 0), ElementPortRef("missing", "a"))),
                    Junction("b", E, (ElementPortRef("r", "a"), BoundaryRef(BoundarySide.OUTPUT, 0))),
                ),
            )
        with pytest.raises(DiagramConstructionError, match="not covered"):
            OpenDiagram.build(
                ONE,
                ONE,
                (ComponentSlot("r", ComponentKind.ELECTRICAL_TWO_TERMINAL),),
                (
                    Junction(
                        "a",
                        E,
                        (
                            BoundaryRef(BoundarySide.INPUT, 0),
                            BoundaryRef(BoundarySide.OUTPUT, 0),
                            ElementPortRef("r", "a"),
                        ),
                    ),
                ),
            )

    def test_duplicate_boundary_and_wrong_kind_refuse(self):
        with pytest.raises(DiagramConstructionError, match="more than once"):
            OpenDiagram.build(
                ONE,
                ONE,
                (ComponentSlot("r", ComponentKind.ELECTRICAL_TWO_TERMINAL),),
                (
                    Junction("a", E, (BoundaryRef(BoundarySide.INPUT, 0), ElementPortRef("r", "a"))),
                    Junction("b", E, (BoundaryRef(BoundarySide.INPUT, 0), ElementPortRef("r", "b"))),
                    Junction("c", E, (BoundaryRef(BoundarySide.OUTPUT, 0), ElementPortRef("r", "b"))),
                ),
            )
        with pytest.raises(DiagramConstructionError, match="PortKind"):
            Junction("bad", "electrical", (BoundaryRef(BoundarySide.INPUT, 0), BoundaryRef(BoundarySide.OUTPUT, 0)))

    def test_exact_raw_types_and_boundary_range_refuse(self):
        with pytest.raises(DiagramConstructionError, match="tuple"):
            Interface([E])  # type: ignore[arg-type]
        with pytest.raises(DiagramConstructionError, match="ComponentKind"):
            ComponentSlot("r", "electrical-two-terminal")  # type: ignore[arg-type]
        with pytest.raises(DiagramConstructionError, match="out of range"):
            OpenDiagram.build(
                ONE,
                ONE,
                (),
                (Junction("bad", E, (BoundaryRef(BoundarySide.INPUT, 1), BoundaryRef(BoundarySide.OUTPUT, 0))),),
            )
        with pytest.raises(DiagramConstructionError, match="presentations are internal"):
            OpenDiagram(ONE, ONE, (0,), (0,), (E,), ())

    def test_composition_requires_exact_interface_match(self):
        with pytest.raises(DiagramCompositionError):
            _resistor().then(identity(TWO))


class TestCanonicalObserver:
    def test_alpha_renaming_and_declaration_reordering_are_equal(self):
        left = _parallel(("first", "second"))
        right = _parallel(("beta", "alpha"), reverse_junctions=True)
        assert canonicalize(left) == canonicalize(right)
        # Domain decorations move with declaration order, but are still opaque to structure.
        assert canonicalize(left, edge_labels=("low", "high")) == canonicalize(
            right, edge_labels=("high", "low")
        )
        assert hash(canonicalize(left)) == hash(canonicalize(right))

    def test_parallel_multiplicity_and_self_loop_are_preserved(self):
        parallel = _parallel(("r1", "r2"))
        loop = _closed_self_loop()
        canonical_parallel = canonicalize(parallel)
        canonical_loop = canonicalize(loop)
        assert len(canonical_parallel.edges) == 2
        assert canonical_parallel.edges[0] == canonical_parallel.edges[1]
        assert canonical_loop.edges == ((ComponentKind.ELECTRICAL_TWO_TERMINAL.value, None, 0, 0),)

    def test_exhaustive_small_permutation_oracle(self):
        """The WL restriction agrees with brute force over every node relabelling here."""
        diagram = OpenDiagram.build(
            ONE,
            ONE,
            (
                ComponentSlot("a", ComponentKind.ELECTRICAL_TWO_TERMINAL),
                ComponentSlot("b", ComponentKind.ELECTRICAL_TWO_TERMINAL),
                ComponentSlot("c", ComponentKind.ELECTRICAL_TWO_TERMINAL),
            ),
            (
                Junction("x", E, (BoundaryRef(BoundarySide.INPUT, 0), ElementPortRef("a", "a"), ElementPortRef("c", "b"))),
                Junction("y", E, (ElementPortRef("a", "b"), ElementPortRef("b", "a"))),
                Junction("z", E, (ElementPortRef("b", "b"), ElementPortRef("c", "a"), BoundaryRef(BoundarySide.OUTPUT, 0))),
            ),
        )
        colours = _refine_colours(diagram, (None,) * len(diagram.edges))
        brute = min(
            (
                tuple(colours[tuple(mapping).index(target)] for target in range(len(mapping))),
                tuple(mapping[node] for node in diagram.input_nodes),
                tuple(mapping[node] for node in diagram.output_nodes),
                tuple(sorted(
                    (edge.kind.value, None, min(mapping[edge.node_a], mapping[edge.node_b]), max(mapping[edge.node_a], mapping[edge.node_b]))
                    for edge in diagram.edges
                )),
            )
            for mapping in permutations(range(len(diagram.node_kinds)))
        )
        observed = canonicalize(diagram)
        assert brute[0] == tuple(sorted(colours))
        assert (observed.input_nodes, observed.output_nodes, observed.edges) == brute[1:]

        # This is the same three-node feedback graph under both component and junction
        # declaration permutations, not merely an isomorphic edge list built directly.
        permuted = OpenDiagram.build(
            ONE,
            ONE,
            (
                ComponentSlot("beta", ComponentKind.ELECTRICAL_TWO_TERMINAL),
                ComponentSlot("gamma", ComponentKind.ELECTRICAL_TWO_TERMINAL),
                ComponentSlot("alpha", ComponentKind.ELECTRICAL_TWO_TERMINAL),
            ),
            (
                Junction("z", E, (ElementPortRef("gamma", "a"), BoundaryRef(BoundarySide.OUTPUT, 0), ElementPortRef("beta", "b"))),
                Junction("x", E, (ElementPortRef("gamma", "b"), ElementPortRef("alpha", "a"), BoundaryRef(BoundarySide.INPUT, 0))),
                Junction("y", E, (ElementPortRef("beta", "a"), ElementPortRef("alpha", "b"))),
            ),
        )
        assert observed == canonicalize(permuted)
        assert canonicalize(diagram, edge_labels=("a", "b", "c")) == canonicalize(
            permuted, edge_labels=("b", "c", "a")
        )

    def test_opaque_labels_are_shape_aligned_not_model_interpreted(self):
        diagram = _resistor()
        with pytest.raises(DiagramConstructionError, match="aligned"):
            canonicalize(diagram, edge_labels=())
        with pytest.raises(DiagramConstructionError, match="opaque string"):
            canonicalize(diagram, edge_labels=(1,))  # type: ignore[arg-type]
        assert canonicalize(diagram, edge_labels=("not-a-resistance",))


class TestDiagramLaws:
    def _same(self, left: OpenDiagram, right: OpenDiagram) -> None:
        assert canonicalize(left) == canonicalize(right)

    def test_identity_associativity_and_tensor_interchange(self):
        f, g, h, k = (_resistor(name) for name in ("f", "g", "h", "k"))
        self._same(identity(ONE).then(f), f)
        self._same(f.then(identity(ONE)), f)
        self._same(f.then(g).then(h), f.then(g.then(h)))
        self._same(f.tensor(identity(unit_interface())), f)
        self._same(identity(unit_interface()).tensor(f), f)
        self._same(f.tensor(g).tensor(h), f.tensor(g.tensor(h)))
        self._same(
            f.then(g).tensor(h.then(k)),
            f.tensor(h).then(g.tensor(k)),
        )

    def test_braid_involution_naturality_and_hexagon(self):
        a, b, c = ONE, TWO, ONE
        self._same(braid(a, b).then(braid(b, a)), identity(a.tensor(b)))
        f = _resistor("f")
        g = _parallel(("g1", "g2"))
        self._same(
            f.tensor(g).then(braid(f.cod, g.cod)),
            braid(f.dom, g.dom).then(g.tensor(f)),
        )
        self._same(
            braid(a, b.tensor(c)),
            braid(a, b).tensor(identity(c)).then(identity(b).tensor(braid(a, c))),
        )
        self._same(
            braid(a.tensor(b), c),
            identity(a).tensor(braid(b, c)).then(braid(a, c).tensor(identity(b))),
        )

    def test_total_tensor_survives_before_the_explicit_budgeted_observer_refuses(self):
        nine = _closed_self_loop()
        for _ in range(8):
            nine = nine.tensor(_closed_self_loop())
        assert len(nine.edges) == 9
        assert len(nine.node_kinds) == 9
        with pytest.raises(CanonicalizationBudgetExceeded):
            canonicalize(nine, budget=1_000)
