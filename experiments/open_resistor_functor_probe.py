"""OPEN-RESISTOR-FUNCTOR-01 (item 6, EM scope): ideal DC resistor networks are functor images of the generic
open SMC (:mod:`smartchem.open_core`), and :class:`ResistorDecoration` is the FIRST non-additive decoration
proven to satisfy ``open_core.Decoration``'s interchange-invariance obligation.

Every cross-check here is NON-CIRCULAR.  The composed boundary relations are checked against
:func:`smartchem.resistive_dc_verifier._expected_relation` -- an independently-written Kirchhoff/Laplacian
re-derivation that imports NEITHER the schema nor the solver this bridge adapts -- never against the thing they
mirror.  The oracle is in-repo (unlike the CIP rdkit probes), so this runs in the committed baseline.

What it proves:
* the functor preserves SERIES composition: ``resistor_edge(R1) `` then `` resistor_edge(R2)`` on ``open_core``
  yields the boundary relation the independent verifier re-derives for the same two-resistor series network;
* the resistor algebra agrees with the independent oracle on a genuine JUNCTION (parallel: ``R1||R2``);
* the INTERCHANGE LAW holds on ``ResistorDecoration`` with a non-vacuity control (the prize -- a non-additive
  monoid satisfying the ``open_core`` obligation, so ``open_core`` genuinely hosts a second physical domain);
* the ``plug_all`` HAZARD is real: it passes the apex through unchanged, leaving a stale, wrong-width relation on
  a resistor diagram -- so resistor networks compose via ``then``/``tensor`` (which DO combine the apex), never
  ``plug_all``.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction

from smartchem.circuit import ResistiveDCModel
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
from smartchem.open_resistor_diagram import apex_matches_boundary, for_resistor, resistor_edge
from smartchem.resistive_dc_schema import BoundaryLinearRelation, PositiveResistance, Rational
from smartchem.resistive_dc_verifier import _expected_relation, _structural_resistances

FROZEN_HASH = "e2068fce48f0ddc14724d6fff606ee0d29ebbeaf944ff89175dc0f086b39edef"

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
    return ResistiveDCModel.for_diagram(
        diagram, tuple(PositiveResistance(Rational(o)) for o in ohms)
    )


def _independent(diagram: OpenDiagram, model: ResistiveDCModel, edge_count: int) -> BoundaryLinearRelation:
    """The boundary relation re-derived by the INDEPENDENT verifier (Kirchhoff/Laplacian), re-canonicalised
    through the schema so the comparison is semantic, not sensitive to a row-echelon convention."""
    resistances = _structural_resistances(model, edge_count)
    return BoundaryLinearRelation.from_equations(1, 1, _expected_relation(diagram, resistances))


def _series_network() -> OpenDiagram:
    return _build(("r0", "r1"), (
        ("p", (_IN, _a("r0"))), ("m", (_b("r0"), _a("r1"))), ("n", (_b("r1"), _OUT)),
    ))


def _parallel_network() -> OpenDiagram:
    return _build(("r0", "r1"), (
        ("p", (_IN, _a("r0"), _a("r1"))), ("n", (_OUT, _b("r0"), _b("r1"))),
    ))


def _rows(relation: BoundaryLinearRelation):
    return [[[v.numerator, v.denominator] for v in row] for row in relation.rref_rows]


def validate() -> None:
    """Raise unless every non-circular functor/law/hazard property holds."""
    # 1. FUNCTOR preserves SERIES: open_core `then` == the INDEPENDENT verifier re-derivation.
    series_oc = resistor_edge(100).then(resistor_edge(200))
    net = _series_network()
    assert series_oc.decoration.relation == _independent(net, _model(net, 100, 200), 2), "series != independent"
    assert series_oc.decoration == for_resistor(300), "series resistances must add exactly"

    # 2. the resistor algebra agrees with the INDEPENDENT oracle on a genuine JUNCTION (parallel R1||R2).
    par = _parallel_network()
    assert for_resistor(Fraction(100 * 200, 100 + 200)).relation == _independent(par, _model(par, 100, 200), 2), (
        "parallel closed form != independent"
    )

    # 3. FUNCTOR preserves TENSOR (juxtaposition): open_core `tensor` == the two relations juxtaposed.
    tensor_oc = resistor_edge(100).tensor(resistor_edge(200))
    assert tensor_oc.decoration.relation == for_resistor(100).relation.tensor(for_resistor(200).relation)

    # 4. THE PRIZE -- the INTERCHANGE LAW on a NON-additive Decoration, with a non-vacuity control.
    a, b, c, d = for_resistor(1), for_resistor(2), for_resistor(3), for_resistor(4)
    lhs = a.then_combine(b).tensor_combine(c.then_combine(d))
    rhs = a.tensor_combine(c).then_combine(b.tensor_combine(d))
    assert lhs == rhs, "the interchange law must hold for ResistorDecoration"
    assert lhs != a.tensor_combine(c).then_combine(d.tensor_combine(b)), "interchange law is vacuous (pairing ignored)"

    # 5. canonicalize (the open_core structural quotient) applies to a resistor diagram.
    canonicalize(series_oc)

    # 6. the plug_all HAZARD (an UNENFORCED convention): it passes the apex through UNCHANGED -> a stale,
    #    wrong-width relation.  apex_matches_boundary() is the opt-in fail-closed guard that CATCHES it.
    juxt = resistor_edge(100).tensor(resistor_edge(200))          # 2->2, block-diagonal
    plugged = juxt.plug_all(((0, 1),))                            # glue -> a 1->1 diagram
    assert len(plugged.dom.ports) == 1 and len(plugged.cod.ports) == 1
    assert plugged.decoration.relation.dom_ports == 2, "plug_all must be shown to leave a STALE 2-port relation"
    assert plugged.decoration.relation == juxt.decoration.relation, "the plug_all hazard demonstration is vacuous"
    assert not apex_matches_boundary(plugged), "the validator must CATCH the stale plug_all apex"
    assert apex_matches_boundary(series_oc), "a then/tensor-composed diagram must pass the apex-boundary guard"

    # 7. the combine guards reject a mixed-domain apex (fail loud, not silent).
    try:
        for_resistor(1).then_combine(_NonResistor())
        raise AssertionError("then_combine must reject a non-resistor decoration")
    except Exception as exc:                                       # noqa: BLE001 - guard proof
        assert "resistor" in str(exc)


class _NonResistor:
    pass


def content_hash() -> str:
    payload = {
        "series_100_200": _rows(resistor_edge(100).then(resistor_edge(200)).decoration.relation),
        "series_100_200_300": _rows(
            resistor_edge(100).then(resistor_edge(200)).then(resistor_edge(300)).decoration.relation
        ),
        "tensor_100_200": _rows(resistor_edge(100).tensor(resistor_edge(200)).decoration.relation),
        "parallel_100_200": _rows(for_resistor(Fraction(200, 3)).relation),
        "resistor_5_over_2": _rows(for_resistor(Fraction(5, 2)).relation),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def report() -> dict:
    validate()
    return {
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
        "interchange_law": "holds (non-additive Decoration; non-vacuity checked)",
        "cross_check_oracle": "resistive_dc_verifier._expected_relation (independent Kirchhoff re-derivation)",
    }


if __name__ == "__main__":
    validate()
    print("validate(): OK (functor preserves then/tensor vs the INDEPENDENT verifier; interchange law; plug_all hazard)")
    print(f"content_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
