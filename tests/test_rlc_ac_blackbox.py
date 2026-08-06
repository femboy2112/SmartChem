"""Exact Q(i) black-box preservation controls for the RLC-AC layer.

``tests/test_rlc_ac_circuit.py`` exercises the FLOAT driven solver
(``solve_rlc_ac``): phasors, resonance, conditioning refusal.  It never touches the
exact ``ComplexBoundaryRelation`` that ``blackbox_rlc_ac`` returns on its own, before
any spsolve or conditioning check runs.  This file closes that gap: it mirrors
``TestExactBoundaryRelations`` in ``tests/test_circuit.py`` (the DC template) at the
AC/Q(i) level, and every assertion below is checked against ``blackbox_rlc_ac``
DIRECTLY.  Nothing here calls ``solve_rlc_ac`` or anything touching scipy spsolve,
nonsingularity, or conditioning -- the whole point is that the exact relation is
well-defined, and its preservation under composition/renaming is provable,
independently of whether the driven float solver would even accept the circuit.

One confirmed API gap, found by reading the source before writing a single test:
``ComplexBoundaryRelation`` (``smartchem/rlc_ac_schema.py``) has NO ``.then``,
``.tensor``, ``.identity``, or ``.contains_exact`` -- unlike its DC sibling
``BoundaryLinearRelation`` (``smartchem/resistive_dc_schema.py``), which has all four.
So composition/identity below are exercised the only way the API supports: build the
diagram two different ways (``OpenDiagram.then``/``OpenDiagram.tensor``/
``open_diagram.identity``, which ARE total operations, confirmed at
``smartchem/open_diagram.py``), push each presentation through ``blackbox_rlc_ac``,
and check the resulting ``ComplexBoundaryRelation`` values for exact equality (its
frozen-dataclass ``__eq__`` over ``rref_rows`` of ``GaussianComplex``).  Membership
witnesses use plain ``in`` over ``rref_rows``, since there is no ``contains_exact``.
"""

from __future__ import annotations

import pytest

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
    identity as diagram_identity,
)
from smartchem.rlc_ac_circuit import admittance_exact, blackbox_rlc_ac
from smartchem.rlc_ac_schema import (
    ComplexBoundaryRelation,
    ElementKind,
    GaussianComplex,
    PositiveAngularFrequency,
    PositiveCapacitance,
    PositiveInductance,
    PositiveResistance,
    Rational,
    RLCComponent,
    RLCEdgeBinding,
    RLCModel,
)


ELECTRICAL = PortKind.ELECTRICAL
ONE = Interface((ELECTRICAL,))
TWO = Interface((ELECTRICAL, ELECTRICAL))


def _in(index: int = 0) -> BoundaryRef:
    return BoundaryRef(BoundarySide.INPUT, index)


def _out(index: int = 0) -> BoundaryRef:
    return BoundaryRef(BoundarySide.OUTPUT, index)


def _a(name: str) -> ElementPortRef:
    return ElementPortRef(name, "a")


def _b(name: str) -> ElementPortRef:
    return ElementPortRef(name, "b")


def _slots(*names: str) -> tuple[ComponentSlot, ...]:
    return tuple(
        ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names
    )


def _single(name: str = "r") -> OpenDiagram:
    """One-port -> one-port single branch (the DC template's ``_single``, for AC)."""
    return OpenDiagram.build(
        ONE,
        ONE,
        _slots(name),
        (
            Junction("positive", ELECTRICAL, (_in(), _a(name))),
            Junction("negative", ELECTRICAL, (_out(), _b(name))),
        ),
    )


def _series(names: tuple[str, ...]) -> OpenDiagram:
    """One-port -> one-port chain, mirroring ``test_rlc_ac_circuit.py``'s ``_diagram``."""
    endpoints: list[tuple[str, tuple[object, ...]]] = [
        ("positive", (_in(), _a(names[0])))
    ]
    for left, right in zip(names, names[1:]):
        endpoints.append((f"mid-{left}", (_b(left), _a(right))))
    endpoints.append(("negative", (_b(names[-1]), _out())))
    return OpenDiagram.build(
        ONE,
        ONE,
        _slots(*names),
        tuple(Junction(name, ELECTRICAL, items) for name, items in endpoints),
    )


def _parallel(names: tuple[str, ...]) -> OpenDiagram:
    """One-port -> one-port parallel bank, mirroring ``test_rlc_ac_circuit.py``'s helper."""
    return OpenDiagram.build(
        ONE,
        ONE,
        _slots(*names),
        (
            Junction("positive", ELECTRICAL, (_in(), *(_a(n) for n in names))),
            Junction("negative", ELECTRICAL, (_out(), *(_b(n) for n in names))),
        ),
    )


def _component(kind: ElementKind, value: Rational) -> RLCComponent:
    if kind is ElementKind.RESISTOR:
        return RLCComponent(kind, PositiveResistance(value))
    if kind is ElementKind.INDUCTOR:
        return RLCComponent(kind, PositiveInductance(value))
    return RLCComponent(kind, PositiveCapacitance(value))


def _model(
    diagram: OpenDiagram,
    components: tuple[RLCComponent, ...],
    *,
    bindings: tuple[RLCEdgeBinding, ...] | None = None,
) -> RLCModel:
    return RLCModel.for_diagram(diagram, components, edge_bindings=bindings)


def _omega(value: int | Rational = 1) -> PositiveAngularFrequency:
    return PositiveAngularFrequency(value if type(value) is Rational else Rational(value))


class TestExactACBoundaryRelations:
    """Ooh yeah -- proving the Q(i) black box holds still, however you draw it!

    Same shape as ``TestExactBoundaryRelations`` in ``tests/test_circuit.py``, but
    every assertion runs at the AC/Q(i) layer through ``blackbox_rlc_ac`` alone. No
    ``solve_rlc_ac``, no spsolve, no conditioning -- existence is pain, but at least
    it's EXACT pain.
    """

    def test_identity_diagram_is_the_exact_open_wire_relation(self):
        """Item 3, worked around: no ``ComplexBoundaryRelation.identity`` classmethod
        exists (the DC ``BoundaryLinearRelation.identity`` has no AC counterpart), so
        the open-wire relation is hand-derived from its own definition -- equal
        boundary voltages, and inward currents that cancel -- via ``from_equations``,
        which DOES exist. The zero-component identity diagram must satisfy exactly
        that, with no MNA elimination artifacts left over.
        """
        diagram = diagram_identity(ONE)
        model = _model(diagram, ())
        relation = blackbox_rlc_ac(diagram, model, _omega())
        one, zero = GaussianComplex.one(), GaussianComplex.zero()
        expected = ComplexBoundaryRelation.from_equations(
            1,
            1,
            [
                [one, -one, zero, zero],
                [zero, zero, one, one],
            ],
        )
        assert relation == expected

    def test_series_via_diagram_then_matches_the_direct_build(self):
        """Item 1, worked around: no ``ComplexBoundaryRelation.then`` exists, so this
        proves preservation the way the API allows it -- ``OpenDiagram.then`` is a
        total composition (confirmed in ``open_diagram.py``); gluing two independently
        built one-port branches and running ``blackbox_rlc_ac`` on the glued diagram
        must land on the SAME relation as declaring the two-edge series circuit in one
        ``OpenDiagram.build`` call, R and L values held fixed either way.
        """
        left, right = _single("left"), _single("right")
        whole = left.then(right)
        r = _component(ElementKind.RESISTOR, Rational(100))
        l = _component(ElementKind.INDUCTOR, Rational(2))
        composed = blackbox_rlc_ac(whole, _model(whole, (r, l)), _omega())
        direct = _series(("r", "l"))
        directly_built = blackbox_rlc_ac(direct, _model(direct, (r, l)), _omega())
        assert composed == directly_built

    def test_tensor_via_diagram_tensor_matches_the_direct_build(self):
        """Item 2, worked around: no ``ComplexBoundaryRelation.tensor`` exists, so this
        proves preservation the way the API allows it -- ``OpenDiagram.tensor`` is a
        total disjoint union with concatenated boundaries; two independent one-port
        branches tensored together must give the SAME relation as declaring their
        2-port direct sum directly, R and C held fixed either way.
        """
        left, right = _single("left"), _single("right")
        whole = left.tensor(right)
        r = _component(ElementKind.RESISTOR, Rational(50))
        c = _component(ElementKind.CAPACITOR, Rational(3))
        composed = blackbox_rlc_ac(whole, _model(whole, (r, c)), _omega())
        direct = OpenDiagram.build(
            TWO,
            TWO,
            _slots("left", "right"),
            (
                Junction("positive-left", ELECTRICAL, (_in(0), _a("left"))),
                Junction("negative-left", ELECTRICAL, (_out(0), _b("left"))),
                Junction("positive-right", ELECTRICAL, (_in(1), _a("right"))),
                Junction("negative-right", ELECTRICAL, (_out(1), _b("right"))),
            ),
        )
        directly_built = blackbox_rlc_ac(direct, _model(direct, (r, c)), _omega())
        assert composed == directly_built

    def test_parallel_relation_has_exact_gaussian_admittance_not_a_scalar_reduction(
        self,
    ):
        """Item 4: the parallel R//C reduces to a single Ohm's-law coefficient in the
        projected relation, and that coefficient is the EXACT Q(i) reciprocal of the
        summed branch admittances -- computed independently here with the module's own
        ``admittance_exact`` (never rounded through Python ``complex``), then checked
        for literal membership in the relation's own rows.
        """
        diagram = _parallel(("r", "c"))
        omega = _omega(Rational(2))
        r = _component(ElementKind.RESISTOR, Rational(100))
        c = _component(ElementKind.CAPACITOR, Rational(1, 4))
        relation = blackbox_rlc_ac(diagram, _model(diagram, (r, c)), omega)
        combined_admittance = admittance_exact(r, omega) + admittance_exact(c, omega)
        expected_impedance = combined_admittance.inverse()
        assert type(expected_impedance) is GaussianComplex
        # 1/100 + j*2*(1/4) = 1/100 + j/2, inverted exactly in Q(i): not 0.01, not a float.
        assert expected_impedance == GaussianComplex.from_parts(
            Rational(100, 2501), Rational(-5000, 2501)
        )
        coefficients = [value for row in relation.rref_rows for value in row]
        assert expected_impedance in coefficients

    def test_composed_diagram_is_compositional_with_explicit_edge_model_reordering(
        self,
    ):
        """Item 6: glue two independently built half-circuits with ``OpenDiagram.then``
        (structural edge order becomes left-half-edges then right-half-edges), declare
        the assembled model's components OUT of that order, and reattach them with
        explicit ``RLCEdgeBinding`` witnesses. The resulting relation must still match
        the direct three-edge series build in natural component order -- composition
        and the edge-binding witness compose cleanly, together.
        """
        left_half = _single("a")
        right_half = _series(("b", "c"))
        assembled = left_half.then(right_half)
        # Structural order after `.then` is [a, b, c]; declare the model as (c, a, b)
        # and route it back with explicit non-identity RLCEdgeBinding witnesses.
        r_value, l_value, c_value = Rational(10), Rational(2), Rational(1, 5)
        model_reordered = _model(
            assembled,
            (
                _component(ElementKind.CAPACITOR, c_value),  # model 0 -> structural 2
                _component(ElementKind.RESISTOR, r_value),  # model 1 -> structural 0
                _component(ElementKind.INDUCTOR, l_value),  # model 2 -> structural 1
            ),
            bindings=(RLCEdgeBinding(0, 2), RLCEdgeBinding(1, 0), RLCEdgeBinding(2, 1)),
        )
        composed = blackbox_rlc_ac(assembled, model_reordered, _omega())
        direct = _series(("r", "l", "c"))
        model_direct = _model(
            direct,
            (
                _component(ElementKind.RESISTOR, r_value),
                _component(ElementKind.INDUCTOR, l_value),
                _component(ElementKind.CAPACITOR, c_value),
            ),
        )
        directly_built = blackbox_rlc_ac(direct, model_direct, _omega())
        assert composed == directly_built

    def test_alpha_renaming_and_junction_reordering_do_not_change_blackbox(self):
        """Item 5: rename every junction and the single component, and reorder the
        junction declarations -- the SAME physical one-port resistor must still
        produce an identical relation. Also confirms (mirroring the DC control) that
        an ``RLCModel`` refuses to bind to a differently-presented diagram at all: the
        presentation digest, not "does it happen to work", is what's enforced.
        """
        first = _single("old")
        second = OpenDiagram.build(
            ONE,
            ONE,
            _slots("new"),
            (
                Junction("negative-renamed", ELECTRICAL, (_out(), _b("new"))),
                Junction("positive-renamed", ELECTRICAL, (_in(), _a("new"))),
            ),
        )
        bound_first = _model(first, (_component(ElementKind.RESISTOR, Rational(47)),))
        with pytest.raises(ValueError, match="exact OpenDiagram presentation"):
            blackbox_rlc_ac(second, bound_first, _omega())
        bound_second = _model(second, (_component(ElementKind.RESISTOR, Rational(47)),))
        assert blackbox_rlc_ac(first, bound_first, _omega()) == blackbox_rlc_ac(
            second, bound_second, _omega()
        )

    def test_relation_storage_is_exact_gaussian_complex_over_rational(self):
        """Item 7: every coefficient in ``rref_rows`` is a ``GaussianComplex`` built
        from ``Rational`` real/imag parts -- never a Python ``complex`` or ``float``
        sneaking into the semantic (as opposed to numeric-witness) layer.
        """
        diagram = _single("r")
        model = _model(diagram, (_component(ElementKind.RESISTOR, Rational(3)),))
        relation = blackbox_rlc_ac(diagram, model, _omega())
        coefficients = [value for row in relation.rref_rows for value in row]
        assert coefficients  # a real circuit must leave a non-empty exact witness.
        assert all(type(value) is GaussianComplex for value in coefficients)
        assert all(type(value.real) is Rational for value in coefficients)
        assert all(type(value.imag) is Rational for value in coefficients)
        assert not any(type(value) is complex for value in coefficients)
        assert not any(type(value) is float for value in coefficients)

    def test_mutation_teeth_different_omega_or_perturbed_value_changes_the_relation(
        self,
    ):
        """TEETH. Every equality assertion above would be vacuous if
        ``ComplexBoundaryRelation`` equality just always came back True (an
        always-true ``__eq__``, an accidentally-empty ``rref_rows``, a constant
        blackbox output...). This proves it does NOT: the same series R-L circuit at
        two different omegas gives two DIFFERENT relations, and so does the same
        omega with a perturbed inductance -- the reactive term measurably changes,
        exactly as Q(i) says it should.
        """
        diagram = _series(("r", "l"))
        r = _component(ElementKind.RESISTOR, Rational(10))
        l = _component(ElementKind.INDUCTOR, Rational(1))
        model = _model(diagram, (r, l))
        at_omega_one = blackbox_rlc_ac(diagram, model, _omega(1))
        at_omega_two = blackbox_rlc_ac(diagram, model, _omega(2))
        assert at_omega_one != at_omega_two

        perturbed_l = _component(ElementKind.INDUCTOR, Rational(7))
        perturbed_model = _model(diagram, (r, perturbed_l))
        at_perturbed_l = blackbox_rlc_ac(diagram, perturbed_model, _omega(1))
        assert at_omega_one != at_perturbed_l
