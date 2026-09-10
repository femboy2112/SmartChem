"""OPEN-CIRCUIT-PIPELINE-01 (item 1 / Move-5 evidence, EM scope): the second-domain circuit PIPELINE on the
generic open SMC (:mod:`smartchem.open_core`).  ``from_circuit`` ingests an arbitrary production resistor
network; ``parallel`` constructs a parallel block with an exact apex; a ``CircuitRoute`` composes stages in
series; ``equivalent_resistance`` reads the domain cost; ``within_spec`` is the Move-5 survival predicate.

Cross-checks use TWO oracles of DIFFERENT provenance (adversarial review, common-mode caveat).  (1) The apex is
checked against :func:`smartchem.resistive_dc_verifier._expected_relation` -- an independently-TYPED re-derivation
that imports NEITHER the schema's relation algebra NOR the ``blackbox`` solver the pipeline adapts.  But it is the
SAME nodal-Laplacian elimination coded twice, so its agreement bounds implementation TYPOS, not a shared
algorithmic assumption -- it is not a fully independent bearing.  (2) The scalar equivalent resistance is
therefore ALSO checked against a PHYSICALLY DISTINCT spanning-tree / matrix-tree oracle
(:func:`_spanning_tree_resistance`) -- a combinatorial sum over spanning trees and 2-forests, no linear algebra,
no common-mode with the Laplacian derivation.  Both oracles are in-repo (no rdkit), so this runs in the committed
baseline.

What it proves:
* ``from_circuit`` reconstructs SERIES, PARALLEL, and a genuinely NON-series-parallel Wheatstone BRIDGE, and its
  apex equals the INDEPENDENT verifier's re-derivation for each -- so it handles topology ``then``/``tensor``
  cannot build;
* the FUNCTOR law: ``from_circuit(A) `` then `` from_circuit(B)`` on ``open_core`` yields the boundary relation
  the solver computes for the old-core series ``A then B`` (and the item-6 ``resistor_edge`` construction);
* the PARALLEL-MERGE primitive (``BoundaryLinearRelation.parallel`` / ``parallel``) equals the ``R1||R2`` closed
  form AND the independent oracle, commutes, and is non-vacuous (``R1||R2 != R1+R2``) -- closing item 6's
  deferred parallel construction with an exact apex;
* the domain COST (``equivalent_resistance``) and the Move-5 SURVIVAL PREDICATE (``within_spec``) read correctly
  off the assembled apex, and FAIL CLOSED (``None`` / ``False``) on an open circuit;
* a mixed series/parallel ``CircuitRoute`` assembles through the generic ``open_core.then`` and its cost equals
  the closed form -- a real consumer GRAPH (assemble->then, ingest->from_circuit, in_parallel->parallel), the
  genericity evidence Move 5 was missing; still a demonstration pipeline awaiting its first non-test caller;
* the reconstructed TOPOLOGY is load-bearing, not decorative: ``from_circuit``'s hyperedges mirror the source
  network's edges, and ``parallel``'s hand-rolled node-merge canonicalizes byte-identically to ``from_circuit``
  of the same network -- so a wrong merge would be CAUGHT, not silently ridden through on the apex;
* the parallel-merge is exercised at MULTIPORT (a 2->1 network, ``A.parallel(A)`` == the doubled network's apex ==
  the independent oracle), so the general branch of ``BoundaryLinearRelation.parallel`` is committed-verified, not
  only checked in adversarial scratch.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction

from smartchem.circuit import ResistiveDCModel, blackbox_resistive_dc
from smartchem.open_circuit_pipeline import (
    CircuitRoute,
    CircuitStage,
    equivalent_resistance,
    from_circuit,
    parallel,
    within_spec,
)
from smartchem.open_core import canonicalize
from smartchem.open_diagram import (
    BoundaryRef,
    BoundarySide,
    ComponentKind,
    ComponentSlot,
    ElementPortRef,
    Interface,
    Junction,
    OpenDiagram,
    PortKind,
)
from smartchem.open_resistor_diagram import apex_matches_boundary, resistor_edge, resistor_relation
from smartchem.resistive_dc_schema import (
    BoundaryLinearRelation,
    PositiveResistance,
    Rational,
)
from smartchem.resistive_dc_verifier import _expected_relation, _structural_resistances

FROZEN_HASH = "33bc257c90a1454adff92e6df0cccd8740497815a5a7bafc6f678d88071dfffc"

_E = PortKind.ELECTRICAL
_ONE = Interface((_E,))
_IN = BoundaryRef(BoundarySide.INPUT, 0)
_OUT = BoundaryRef(BoundarySide.OUTPUT, 0)


def _a(name: str) -> ElementPortRef:
    return ElementPortRef(name, "a")


def _b(name: str) -> ElementPortRef:
    return ElementPortRef(name, "b")


def _build(names: tuple[str, ...], junctions) -> OpenDiagram:
    return OpenDiagram.build(
        _ONE, _ONE,
        tuple(ComponentSlot(n, ComponentKind.ELECTRICAL_TWO_TERMINAL) for n in names),
        tuple(Junction(nm, _E, ep) for nm, ep in junctions),
    )


def _model(diagram: OpenDiagram, *ohms: int) -> ResistiveDCModel:
    return ResistiveDCModel.for_diagram(diagram, tuple(PositiveResistance(Rational(o)) for o in ohms))


def _independent(diagram: OpenDiagram, model: ResistiveDCModel) -> BoundaryLinearRelation:
    resistances = _structural_resistances(model, len(diagram.structural_edges()))
    return BoundaryLinearRelation.from_equations(
        len(diagram.dom.ports), len(diagram.cod.ports), _expected_relation(diagram, resistances)
    )


def _single(name: str) -> OpenDiagram:
    return _build((name,), ((f"p{name}", (_IN, _a(name))), (f"n{name}", (_b(name), _OUT))))


def _series() -> OpenDiagram:
    return _build(("r0", "r1"), (
        ("p", (_IN, _a("r0"))), ("m", (_b("r0"), _a("r1"))), ("n", (_b("r1"), _OUT)),
    ))


def _parallel_net() -> OpenDiagram:
    return _build(("r0", "r1"), (
        ("p", (_IN, _a("r0"), _a("r1"))), ("n", (_OUT, _b("r0"), _b("r1"))),
    ))


def _bridge() -> OpenDiagram:
    # Wheatstone: IN=in, OUT=out, mids l,r. r4 is the galvanometer arm across l-r. NON series-parallel.
    return _build(
        ("r0", "r1", "r2", "r3", "r4"),
        (
            ("in", (_IN, _a("r0"), _a("r1"))),
            ("out", (_OUT, _b("r2"), _b("r3"))),
            ("l", (_b("r0"), _a("r2"), _a("r4"))),
            ("r", (_b("r1"), _a("r3"), _b("r4"))),
        ),
    )


def _open_circuit_stage() -> object:
    # a genuine OPEN 1->1 apex (no current path): I_dom = 0, I_cod = 0 -- equivalent_resistance must be None.
    open_relation = BoundaryLinearRelation.from_equations(1, 1, [[0, 0, 1, 0], [0, 0, 0, 1]])
    from smartchem.open_resistor_diagram import ResistorDecoration
    edge = resistor_edge(1)  # borrow a valid 1->1 topology, then swap in the open apex
    from smartchem.open_core import OpenDiagram as OCDiagram
    return OCDiagram(
        edge.dom, edge.cod, edge.input_nodes, edge.output_nodes, edge.node_ports, edge.hyperedges,
        ResistorDecoration(open_relation),
    )


def _spanning_tree_resistance(node_count, edges, conductances, source, sink):
    """PHYSICALLY DISTINCT oracle: effective resistance via the weighted matrix-tree theorem.

    ``R_eff(s,t) = T(s|t) / T`` where ``T`` sums the conductance-products of all spanning TREES and ``T(s|t)``
    sums those of all spanning 2-FORESTS separating ``s`` from ``t``.  Pure combinatorics over edge subsets --
    no Laplacian, no Gaussian elimination -- so it shares NO common-mode with ``blackbox``/``_expected_relation``.
    Cheap for the small networks here (<=7 edges).  Returns ``None`` if the network is disconnected.
    """
    from fractions import Fraction as _F
    from itertools import combinations

    def _forest(indices):
        parent = list(range(node_count))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i in indices:
            a, b = edges[i]
            ra, rb = find(a), find(b)
            if ra == rb:
                return None, None            # a cycle: not a forest
            parent[max(ra, rb)] = min(ra, rb)
        return {find(x) for x in range(node_count)}, find

    total = _F(0)
    for combo in combinations(range(len(edges)), node_count - 1):
        roots, _find = _forest(combo)
        if roots is not None and len(roots) == 1:
            weight = _F(1)
            for i in combo:
                weight *= conductances[i]
            total += weight
    separated = _F(0)
    for combo in combinations(range(len(edges)), node_count - 2):
        roots, find = _forest(combo)
        if roots is not None and len(roots) == 2 and find(source) != find(sink):
            weight = _F(1)
            for i in combo:
                weight *= conductances[i]
            separated += weight
    if total == 0:
        return None
    return separated / total


def _spanning_tree_oracle(diagram: OpenDiagram, *ohms: int):
    edges = [(e.node_a, e.node_b) for e in diagram.structural_edges()]
    conductances = [Fraction(1, o) for o in ohms]
    return _spanning_tree_resistance(
        len(diagram.node_kinds), edges, conductances, diagram.input_nodes[0], diagram.output_nodes[0]
    )


def _net_2to1(names) -> OpenDiagram:
    dom, cod = Interface((_E, _E)), Interface((_E,))
    return OpenDiagram.build(
        dom, cod, tuple(ComponentSlot(n, ComponentKind.ELECTRICAL_TWO_TERMINAL) for n in names),
        (Junction("i0", _E, (BoundaryRef(BoundarySide.INPUT, 0), _a(names[0]))),
         Junction("i1", _E, (BoundaryRef(BoundarySide.INPUT, 1), _a(names[1]))),
         Junction("o", _E, (BoundaryRef(BoundarySide.OUTPUT, 0), _b(names[0]), _b(names[1])))),
    )


def _net_2to1_doubled(names) -> OpenDiagram:
    dom, cod = Interface((_E, _E)), Interface((_E,))
    return OpenDiagram.build(
        dom, cod, tuple(ComponentSlot(n, ComponentKind.ELECTRICAL_TWO_TERMINAL) for n in names),
        (Junction("i0", _E, (BoundaryRef(BoundarySide.INPUT, 0), _a(names[0]), _a(names[2]))),
         Junction("i1", _E, (BoundaryRef(BoundarySide.INPUT, 1), _a(names[1]), _a(names[3]))),
         Junction("o", _E, (BoundaryRef(BoundarySide.OUTPUT, 0), _b(names[0]), _b(names[1]), _b(names[2]), _b(names[3])))),
    )


def validate() -> None:
    """Raise unless every non-circular pipeline property holds."""
    # 1. from_circuit apex == the INDEPENDENT verifier, on series / parallel / bridge (arbitrary topology).
    for name, dg, ohms in (
        ("series", _series(), (100, 200)),
        ("parallel", _parallel_net(), (100, 200)),
        ("bridge", _bridge(), (3, 5, 7, 11, 13)),
    ):
        model = _model(dg, *ohms)
        lifted = from_circuit(dg, model)
        assert lifted.decoration.relation == _independent(dg, model), f"from_circuit({name}) != independent oracle"
        assert apex_matches_boundary(lifted), f"from_circuit({name}) apex is not boundary-consistent"

    # 2. FUNCTOR law: from_circuit(A) then from_circuit(B) == blackbox(old-core A then B) == item-6 resistor_edge.
    a_old, b_old = _single("x"), _single("y")
    f_a = from_circuit(a_old, _model(a_old, 100))
    f_b = from_circuit(b_old, _model(b_old, 200))
    composed = f_a.then(f_b)
    ab = a_old.then(b_old)
    assert composed.decoration.relation == blackbox_resistive_dc(ab, _model(ab, 100, 200)), "functor law (solver) broken"
    assert composed.decoration.relation == resistor_edge(100).then(resistor_edge(200)).decoration.relation, (
        "functor law (item-6 resistor_edge) broken"
    )

    # 3. the PARALLEL-MERGE primitive: == R1||R2 closed form AND == the independent oracle; commutes; non-vacuous.
    r1, r2 = 100, 200
    par = parallel(resistor_edge(r1), resistor_edge(r2))
    closed = resistor_relation(Fraction(r1 * r2, r1 + r2))
    pnet = _parallel_net()
    assert par.decoration.relation == closed, "parallel apex != R1||R2 closed form"
    assert par.decoration.relation == _independent(pnet, _model(pnet, r1, r2)), "parallel apex != independent oracle"
    assert par.decoration.relation == parallel(resistor_edge(r2), resistor_edge(r1)).decoration.relation, (
        "parallel is not commutative"
    )
    assert par.decoration.relation != resistor_relation(r1 + r2), "parallel is vacuous (equals series)"
    assert apex_matches_boundary(par), "parallel apex is not boundary-consistent"
    # two identical resistors in parallel halve: R || R == R/2
    assert equivalent_resistance(parallel(resistor_edge(100), resistor_edge(100))) == Fraction(50), "R||R != R/2"

    # 4. the domain COST reads correctly, and FAILS CLOSED on an open circuit.
    assert equivalent_resistance(resistor_edge(300)) == Fraction(300)
    assert equivalent_resistance(resistor_edge(100).then(resistor_edge(200))) == Fraction(300)  # series adds
    assert equivalent_resistance(par) == Fraction(r1 * r2, r1 + r2)                              # parallel
    assert equivalent_resistance(from_circuit(_bridge(), _model(_bridge(), 3, 5, 7, 11, 13))) == Fraction(1483, 241)
    assert equivalent_resistance(_open_circuit_stage()) is None, "open circuit must have no equivalent resistance"

    # 5. the Move-5 SURVIVAL PREDICATE: in-band True, out-of-band False, open-circuit fail-closed False.
    assert within_spec(par, 0, 100) is True                       # 200/3 ~= 66.7 ohms
    assert within_spec(par, 100, 200) is False
    assert within_spec(_open_circuit_stage(), 0, 10 ** 9) is False  # an open circuit never survives

    # 6. the ROUTE shape: a mixed series/parallel route assembles through open_core.then; its cost is exact.
    route = CircuitRoute.of(
        CircuitStage.resistor(100),
        CircuitStage.in_parallel(CircuitStage.resistor(200), CircuitStage.resistor(200)),  # 200||200 = 100
        CircuitStage.ingest(_series(), _model(_series(), 25, 25), label="ingested series 50"),  # 25+25 = 50
    )
    assembled = route.assemble()
    assert route.equivalent_resistance == Fraction(250), "route cost != 100 + 100 + 50"
    assert apex_matches_boundary(assembled), "assembled route apex is not boundary-consistent"
    assert route.within_spec(200, 300) is True and route.within_spec(0, 100) is False

    # 7. the open_core quotient is available on the second domain (canonicalize a from_circuit bridge).
    canonicalize(from_circuit(_bridge(), _model(_bridge(), 3, 5, 7, 11, 13)))

    # 8. the PHYSICALLY DISTINCT oracle: the scalar equivalent resistance equals the combinatorial matrix-tree
    #    value (spanning trees / 2-forests) -- no common-mode with the Laplacian derivation (the σ/source-
    #    correctness bearing the two-Laplacian agreement structurally cannot supply).
    for dg, ohms in ((_series(), (100, 200)), (_parallel_net(), (100, 200)), (_bridge(), (3, 5, 7, 11, 13))):
        got = equivalent_resistance(from_circuit(dg, _model(dg, *ohms)))
        assert got == _spanning_tree_oracle(dg, *ohms), "equivalent_resistance != physically-distinct matrix-tree oracle"

    # 9. the reconstructed TOPOLOGY is load-bearing, not decorative (both reviewers' central doubt):
    #    (a) from_circuit's hyperedge endpoints mirror the SOURCE network's structural edges (no scramble);
    bridge = _bridge()
    lifted = from_circuit(bridge, _model(bridge, 3, 5, 7, 11, 13))
    src_pairs = sorted((min(e.node_a, e.node_b), max(e.node_a, e.node_b)) for e in bridge.structural_edges())
    oc_pairs = sorted(
        (min(h.terminals[0].node, h.terminals[1].node), max(h.terminals[0].node, h.terminals[1].node))
        for h in lifted.hyperedges
    )
    assert src_pairs == oc_pairs, "from_circuit scrambled the topology relative to the source network"
    #    (b) parallel()'s hand-rolled node-merge canonicalizes BYTE-IDENTICALLY to from_circuit of the same
    #        network (matched payload names) -- so a wrong union-find merge would be CAUGHT, not silently ridden.
    par_named = parallel(resistor_edge(100, name="r0"), resistor_edge(200, name="r1"))
    assert canonicalize(par_named) == canonicalize(from_circuit(_parallel_net(), _model(_parallel_net(), 100, 200))), (
        "parallel's merged topology does not match the direct reconstruction"
    )

    # 10. the parallel-merge is exercised at MULTIPORT (2->1), committed (not only in adversarial scratch):
    #     A.parallel(A) == the doubled network's apex == the independent oracle; commutes; associates.
    n2 = _net_2to1(("r0", "r1"))
    apex_a = from_circuit(n2, _model(n2, 100, 200)).decoration.relation
    assert apex_a.dom_ports == 2 and apex_a.cod_ports == 1
    doubled = _net_2to1_doubled(("r0", "r1", "r2", "r3"))
    doubled_apex = from_circuit(doubled, _model(doubled, 100, 200, 100, 200)).decoration.relation
    assert apex_a.parallel(apex_a) == doubled_apex, "multiport 2->1 parallel != doubled-network apex"
    assert apex_a.parallel(apex_a) == _independent(doubled, _model(doubled, 100, 200, 100, 200)), (
        "multiport 2->1 parallel != independent oracle"
    )
    apex_b = from_circuit(_net_2to1(("r0", "r1")), _model(n2, 300, 400)).decoration.relation
    assert apex_a.parallel(apex_b) == apex_b.parallel(apex_a), "multiport parallel is not commutative"
    assert apex_a.parallel(apex_b).parallel(apex_a) == apex_a.parallel(apex_b.parallel(apex_a)), (
        "multiport parallel is not associative"
    )


def _rows(relation: BoundaryLinearRelation):
    return [[[v.numerator, v.denominator] for v in row] for row in relation.rref_rows]


def _resistance_pair(value) -> list[int]:
    frac = Fraction(value)
    return [frac.numerator, frac.denominator]


def content_hash() -> str:
    par = parallel(resistor_edge(100), resistor_edge(200))
    route = CircuitRoute.of(
        CircuitStage.resistor(100),
        CircuitStage.in_parallel(CircuitStage.resistor(200), CircuitStage.resistor(200)),
        CircuitStage.ingest(_series(), _model(_series(), 25, 25), label="ingested series 50"),
    )
    payload = {
        "series_apex": _rows(from_circuit(_series(), _model(_series(), 100, 200)).decoration.relation),
        "parallel_apex": _rows(par.decoration.relation),
        "bridge_apex": _rows(from_circuit(_bridge(), _model(_bridge(), 3, 5, 7, 11, 13)).decoration.relation),
        "bridge_R": _resistance_pair(
            equivalent_resistance(from_circuit(_bridge(), _model(_bridge(), 3, 5, 7, 11, 13)))
        ),
        "parallel_R": _resistance_pair(equivalent_resistance(par)),
        "route_R": _resistance_pair(route.equivalent_resistance),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def report() -> dict:
    validate()
    return {
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
        "from_circuit": "arbitrary topology (series/parallel/bridge) vs independent Kirchhoff verifier",
        "parallel_merge": "R1||R2 exact, == independent oracle, closes item-6 deferred parallel construction",
        "move5": "second-domain pipeline (ingest + route/step + cost + survival predicate) -- DEMONSTRATED",
    }


if __name__ == "__main__":
    validate()
    print("validate(): OK (from_circuit vs INDEPENDENT verifier; functor law; parallel-merge; cost; survival; route)")
    print(f"content_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
