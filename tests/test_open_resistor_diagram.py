"""Item 6 (EM scope): ideal DC resistor networks as functor images of the generic open SMC, and
``ResistorDecoration`` as the first NON-additive decoration satisfying ``open_core.Decoration``'s
interchange-invariance obligation.  Cross-checks are non-circular (the independent Kirchhoff verifier).
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from smartchem.open_core import Decoration, DiagramCompositionError, canonicalize
from smartchem.open_resistor_diagram import (
    apex_matches_boundary,
    for_resistor,
    resistor_edge,
    resistor_relation,
)
from smartchem.resistive_dc_schema import BoundaryLinearRelation

from experiments import open_resistor_functor_probe as probe


def test_probe_validate_and_frozen_hash():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


def test_for_resistor_calibrates_to_production_blackbox():
    from smartchem.circuit import ResistiveDCModel, blackbox_resistive_dc
    from smartchem.resistive_dc_schema import PositiveResistance, Rational
    from smartchem.open_diagram import (
        BoundaryRef, BoundarySide, ComponentKind, ComponentSlot, ElementPortRef, Interface, Junction, OpenDiagram, PortKind,
    )
    e = PortKind.ELECTRICAL
    one = Interface((e,))
    single = OpenDiagram.build(
        one, one, (ComponentSlot("r", ComponentKind.ELECTRICAL_TWO_TERMINAL),),
        (Junction("p", e, (BoundaryRef(BoundarySide.INPUT, 0), ElementPortRef("r", "a"))),
         Junction("n", e, (BoundaryRef(BoundarySide.OUTPUT, 0), ElementPortRef("r", "b")))),
    )
    model = ResistiveDCModel.for_diagram(single, (PositiveResistance(Rational(100)),))
    assert resistor_relation(100) == blackbox_resistive_dc(single, model)
    # R=0 is exactly a wire (the boundary-relation identity)
    assert resistor_relation(0) == BoundaryLinearRelation.identity(1)


def test_series_is_open_core_then():
    # the functor preserves series composition; series resistances add exactly
    assert resistor_edge(100).then(resistor_edge(200)).decoration == for_resistor(300)
    assert resistor_edge(Fraction(5, 2)).then(resistor_edge(Fraction(1, 2))).decoration == for_resistor(3)


def test_interchange_law_holds_and_is_non_vacuous():
    # THE PRIZE: a NON-additive decoration satisfying open_core.Decoration's interchange obligation
    a, b, c, d = (for_resistor(x) for x in (1, 2, 3, 4))
    lhs = a.then_combine(b).tensor_combine(c.then_combine(d))
    rhs = a.tensor_combine(c).then_combine(b.tensor_combine(d))
    assert lhs == rhs
    assert lhs != a.tensor_combine(c).then_combine(d.tensor_combine(b))  # pairing matters -> non-vacuous


def test_combine_rejects_mixed_domain_apex():
    class _NotResistor(Decoration):  # a Decoration that is not a ResistorDecoration
        def then_combine(self, other):  # pragma: no cover - never reached
            return self

        def tensor_combine(self, other):  # pragma: no cover
            return self

    with pytest.raises(DiagramCompositionError):
        for_resistor(1).then_combine(_NotResistor())
    with pytest.raises(DiagramCompositionError):
        for_resistor(1).tensor_combine(_NotResistor())


def test_float_resistance_is_refused():
    with pytest.raises(TypeError):
        for_resistor(1.5)  # exact rationals only -- never a float


def test_canonicalize_applies_to_a_resistor_diagram():
    canonicalize(resistor_edge(100).then(resistor_edge(200)))  # the open_core quotient is available


def test_plug_all_hazard_and_the_fail_closed_guard():
    # plug_all passes the apex through UNCHANGED -> a stale, wrong-width relation on a resistor diagram (an
    # UNENFORCED convention, not a runtime guard: plug_all is a shared-core method this module cannot override).
    juxt = resistor_edge(100).tensor(resistor_edge(200))     # 2->2 block-diagonal
    plugged = juxt.plug_all(((0, 1),))                       # a 1->1 diagram...
    assert len(plugged.dom.ports) == 1
    assert plugged.decoration.relation.dom_ports == 2        # ...but the relation is STALE (unchanged, 2 ports)
    assert plugged.decoration.relation == juxt.decoration.relation
    # apex_matches_boundary is the opt-in fail-closed guard: it CATCHES the stale plug_all apex, and PASSES a
    # diagram composed only via then/tensor.
    assert not apex_matches_boundary(plugged)
    assert apex_matches_boundary(resistor_edge(100).then(resistor_edge(200)))
    assert apex_matches_boundary(juxt)
