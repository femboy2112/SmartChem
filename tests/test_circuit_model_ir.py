"""Invariance oracle for the fused ``CircuitModelIR`` (M-1a).

``tests/test_rlc_ac_blackbox.py`` proves the exact Q(i) boundary *relation* is preserved
under presentation.  This file proves the same discipline one level up, at the *identity*:
the ``CircuitModelIR`` that fuses topology + decorations + witnesses has a
presentation-invariant :attr:`circuit_identity`, and it is not vacuous -- a genuine
topology, value, or kind change moves it.  Every assertion runs through
``observe_circuit_model_ir`` (or a deliberately forged direct construction, to prove the
fail-closed guards have teeth).  One test crosses to ``analyze_rlc_ac`` to prove the IR's
decorated form is BYTE-IDENTICAL to the analysis pipeline's -- the stated M-1a congruence
risk, checked rather than asserted.
"""

from __future__ import annotations

import pytest

from smartchem.circuit_model_ir import (
    CIRCUIT_MODEL_IR_SCHEMA,
    CircuitModelIR,
    CircuitModelIRError,
    observe_circuit_model_ir,
)
from smartchem.contracts import canonical_digest
from smartchem.open_diagram import (
    BoundaryRef,
    BoundarySide,
    CanonicalDiagram,
    ComponentKind,
    ComponentSlot,
    ElementPortRef,
    Interface,
    Junction,
    OpenDiagram,
    PortKind,
)
from smartchem.rlc_ac_schema import (
    ACSolveSpec,
    ACVoltageDrive,
    ElementKind,
    GaussianComplex,
    PositiveAngularFrequency,
    PositiveCapacitance,
    PositiveInductance,
    PositiveResistance,
    Rational,
    RLCACSubject,
    RLCComponent,
    RLCEdgeBinding,
    RLCModel,
)

ELECTRICAL = PortKind.ELECTRICAL
ONE = Interface((ELECTRICAL,))


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


def _observe(
    diagram: OpenDiagram,
    components: tuple[RLCComponent, ...],
    *,
    bindings: tuple[RLCEdgeBinding, ...] | None = None,
) -> CircuitModelIR:
    return observe_circuit_model_ir(diagram, _model(diagram, components, bindings=bindings))


R100 = _component(ElementKind.RESISTOR, Rational(100))
L2 = _component(ElementKind.INDUCTOR, Rational(2))


class TestPresentationInvariance:
    """Same circuit, however drawn -> same identity."""

    def test_alpha_renaming_and_junction_reorder_preserve_both_identities(self):
        """A one-port resistor drawn two ways -- renamed component and junctions, and the
        junction declarations reordered -- must produce the SAME circuit and topology
        identity.  This is the IR-level analogue of the black-box suite's Item 5.
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
        ir_first = _observe(first, (R100,))
        ir_second = _observe(second, (R100,))
        assert ir_first.circuit_identity == ir_second.circuit_identity
        assert ir_first.topology_identity == ir_second.topology_identity

    def test_model_declaration_reorder_with_explicit_bindings_preserves_identity(self):
        """Assemble a 3-edge series circuit by gluing halves with ``.then`` (structural
        order [a, b, c]); declare the model components OUT of that order and route them
        back with explicit non-identity ``RLCEdgeBinding`` witnesses.  The fused identity
        must equal the natural-order direct build -- the explicit witness composes, and the
        identity absorbs the model permutation.  (IR analogue of Item 6.)
        """
        assembled = _single("a").then(_series(("b", "c")))
        r, l, c = (
            _component(ElementKind.RESISTOR, Rational(10)),
            _component(ElementKind.INDUCTOR, Rational(2)),
            _component(ElementKind.CAPACITOR, Rational(1, 5)),
        )
        reordered = _observe(
            assembled,
            (c, r, l),  # model 0->struct 2, model 1->struct 0, model 2->struct 1
            bindings=(RLCEdgeBinding(0, 2), RLCEdgeBinding(1, 0), RLCEdgeBinding(2, 1)),
        )
        natural = _observe(_series(("r", "l", "c")), (r, l, c))
        assert reordered.circuit_identity == natural.circuit_identity
        assert reordered.topology_identity == natural.topology_identity


class TestTeeth:
    """The identity is not vacuous: real changes move it, in the right face."""

    def test_topology_change_moves_both_identities_with_decorations_held_fixed(self):
        """Same two components, series vs parallel.  Decorations are identical, so ONLY the
        wiring differs -- both the circuit identity and the topology identity must change.
        """
        r = _component(ElementKind.RESISTOR, Rational(100))
        c = _component(ElementKind.CAPACITOR, Rational(3))
        series = _observe(_series(("r", "c")), (r, c))
        parallel = _observe(_parallel(("r", "c")), (r, c))
        assert series.circuit_identity != parallel.circuit_identity
        assert series.topology_identity != parallel.topology_identity

    def test_value_change_moves_circuit_identity_but_not_topology_identity(self):
        """Same series R-L topology, resistance 100 vs 47.  The decorated identity must
        change; the undecorated topology identity must NOT -- the topology face is blind to
        parameters, by construction.
        """
        base = _observe(_series(("r", "l")), (R100, L2))
        perturbed = _observe(
            _series(("r", "l")), (_component(ElementKind.RESISTOR, Rational(47)), L2)
        )
        assert base.circuit_identity != perturbed.circuit_identity
        assert base.topology_identity == perturbed.topology_identity

    def test_element_kind_change_moves_circuit_identity_but_not_topology_identity(self):
        """Same one-port topology and value, resistor vs inductor.  Circuit identity moves;
        topology identity does not (both are single ELECTRICAL two-terminal edges).
        """
        as_r = _observe(_single("x"), (_component(ElementKind.RESISTOR, Rational(5)),))
        as_l = _observe(_single("x"), (_component(ElementKind.INDUCTOR, Rational(5)),))
        assert as_r.circuit_identity != as_l.circuit_identity
        assert as_r.topology_identity == as_l.topology_identity


class TestProvenance:
    """The witness is explicit and the full digest carries it."""

    def test_full_digest_differs_across_presentations_up_to_the_witness(self):
        """Two presentations of one resistor share circuit_identity and topology_identity
        but the full value digest differs -- the ONLY differing field is the adapter
        witness bound to each raw presentation.  This is exactly "equal up to the witnessed
        permutation": the invariant identity is equal, the provenance is not.
        """
        first = _observe(_single("old"), (R100,))
        second = OpenDiagram.build(
            ONE,
            ONE,
            _slots("new"),
            (
                Junction("negative", ELECTRICAL, (_out(), _b("new"))),
                Junction("positive", ELECTRICAL, (_in(), _a("new"))),
            ),
        )
        ir_second = _observe(second, (R100,))
        assert first.circuit_identity == ir_second.circuit_identity
        assert first.digest != ir_second.digest
        # ...and the difference lives in the witness, nowhere else.
        assert first.structure == ir_second.structure
        assert first.decorated_canonical_form == ir_second.decorated_canonical_form
        assert first.edge_witness == ir_second.edge_witness
        assert first.adapter_witness != ir_second.adapter_witness

    def test_edge_witness_is_retained_verbatim_not_normalized_away(self):
        """A non-identity model->structural permutation is stored EXACTLY as declared -- an
        explicit witness, never silently reindexed to identity.
        """
        assembled = _single("a").then(_series(("b", "c")))
        bindings = (RLCEdgeBinding(0, 2), RLCEdgeBinding(1, 0), RLCEdgeBinding(2, 1))
        ir = _observe(
            assembled,
            (
                _component(ElementKind.CAPACITOR, Rational(1, 5)),
                _component(ElementKind.RESISTOR, Rational(10)),
                _component(ElementKind.INDUCTOR, Rational(2)),
            ),
            bindings=bindings,
        )
        assert ir.edge_witness == bindings


class TestPipelineCongruence:
    """The IR's decorated form is byte-identical to what the analysis pipeline builds."""

    def test_decorated_form_and_bindings_match_analyze_rlc_ac(self):
        """observe_circuit_model_ir and analyze_rlc_ac both decorate through the same
        RLCModel.canonical_edge_labels convention, so the presentation-invariant decorated
        canonical form and the retained bindings must be EQUAL objects.  This closes the
        stated M-1a congruence risk against the real pipeline, empirically.
        """
        from smartchem.rlc_ac import analyze_rlc_ac

        diagram = _series(("r", "l"))
        model = _model(diagram, (R100, L2))
        ir = observe_circuit_model_ir(diagram, model)
        subject = RLCACSubject(
            diagram,
            model,
            ACSolveSpec(
                reference=_out(),
                drive=ACVoltageDrive(_in(), _out(), GaussianComplex.one()),
                omega=PositiveAngularFrequency(Rational(1)),
            ),
            100_000,
        )
        analysis = analyze_rlc_ac(subject)
        assert analysis.decorated_model_canonical_form == ir.decorated_canonical_form
        assert analysis.model_edge_bindings == ir.edge_witness
        # The undecorated structure face of the IR is the plan-seam StructureIR; the pipeline
        # keeps a raw CanonicalDiagram of the same undecorated topology.  They agree on the
        # canonical undecorated form the IR's structure re-normalizes to.
        assert (
            ir.structure.to_canonical_diagram()
            == analysis.structural_canonical_form
        )


class TestRoundTripAndFailClosed:
    """Digest round-trip, and every construction guard proven to bite."""

    def test_round_trips_through_canonical_digest_and_is_reproducible(self):
        diagram = _series(("r", "l"))
        model = _model(diagram, (R100, L2))
        first = observe_circuit_model_ir(diagram, model)
        again = observe_circuit_model_ir(diagram, model)
        assert canonical_digest(first) == first.digest
        assert first == again
        assert first.digest == again.digest

    def test_budget_exhaustion_fails_closed(self):
        diagram = _single("r")
        model = _model(diagram, (R100,))
        with pytest.raises(CircuitModelIRError, match="not observable"):
            observe_circuit_model_ir(diagram, model, budget=0)

    def test_model_bound_to_another_presentation_is_refused(self):
        """A model carries its raw-presentation digest.  Renaming a component is invisible
        (a construction-local id the canonical digest discards), so that is NOT a different
        presentation; reordering the junction *declarations* is -- it moves the raw digest.
        A model bound to one presentation must refuse the other, single-edge count or not.
        """
        first = _single("r")
        reordered = OpenDiagram.build(
            ONE,
            ONE,
            _slots("r"),
            (
                Junction("negative", ELECTRICAL, (_out(), _b("r"))),
                Junction("positive", ELECTRICAL, (_in(), _a("r"))),
            ),
        )
        model_for_first = _model(first, (R100,))
        assert len(reordered.structural_edges()) == len(first.structural_edges())
        with pytest.raises(ValueError, match="not bound to this exact OpenDiagram"):
            observe_circuit_model_ir(reordered, model_for_first)

    def test_direct_construction_rejects_a_foreign_adapter_witness(self):
        """A CircuitModelIR cannot wear a witness that identifies a different topology --
        the fail-closed cross-check must bite, or the provenance is forgeable.
        """
        ir_a = _observe(_single("a"), (R100,))
        ir_b = _observe(_series(("r", "l")), (R100, L2))
        with pytest.raises(ValueError, match="does not identify the attached StructureIR"):
            CircuitModelIR(
                CIRCUIT_MODEL_IR_SCHEMA,
                ir_a.structure,
                ir_a.decorated_canonical_form,
                ir_b.adapter_witness,  # witness for a different circuit
                ir_a.edge_witness,
            )

    def test_direct_construction_rejects_a_non_permutation_edge_witness(self):
        ir = _observe(_series(("r", "l")), (R100, L2))
        with pytest.raises(ValueError, match="permute the model and structural"):
            CircuitModelIR(
                CIRCUIT_MODEL_IR_SCHEMA,
                ir.structure,
                ir.decorated_canonical_form,
                ir.adapter_witness,
                (RLCEdgeBinding(0, 0), RLCEdgeBinding(0, 0)),  # not a permutation
            )

    def test_direct_construction_rejects_a_degree_sequence_mismatch(self):
        """The congruence guard between the two topology faces must have TEETH.  The prior
        edge-kind-multiset guard could never fail (ComponentKind is single-valued), so a
        decorated form of a DIFFERENT topology but equal edge count slipped through.  Forge
        exactly that: reuse a real structure's boundaries, node count, and edge count, but
        pile every incidence onto one node so the degree sequence differs.  It must be
        refused.  (An adversarial red-team found the old guard vacuous; this pins the fix.)
        """
        ir = _observe(_series(("r", "l")), (R100, L2))
        s = ir.structure
        node = s.input_nodes[0]
        forged = CanonicalDiagram(
            s.dom,
            s.cod,
            s.input_nodes,
            s.output_nodes,
            s.node_kinds,
            tuple(
                ("electrical-two-terminal", "R:1/1 ohm", node, node) for _ in s.edges
            ),
        )
        with pytest.raises(ValueError, match="degree sequence"):
            CircuitModelIR(
                CIRCUIT_MODEL_IR_SCHEMA,
                s,
                forged,
                ir.adapter_witness,
                ir.edge_witness,
            )

    def test_direct_construction_rejects_a_mismatched_edge_count(self):
        ir = _observe(_series(("r", "l")), (R100, L2))
        with pytest.raises(ValueError, match="equinumerous"):
            CircuitModelIR(
                CIRCUIT_MODEL_IR_SCHEMA,
                ir.structure,
                ir.decorated_canonical_form,
                ir.adapter_witness,
                (RLCEdgeBinding(0, 0),),  # one binding for a two-edge structure
            )


class TestOptionalFace:
    """M-1a1: ``circuit_model_ir_of`` exposes the fused identity as an optional face of the
    analysis pipeline, without adding a field to (and thus moving the digest of) the frozen
    :class:`RLCACAnalysis`.
    """

    def _subject(self, diagram, model, *, budget: int = 100_000) -> RLCACSubject:
        return RLCACSubject(
            diagram,
            model,
            ACSolveSpec(
                reference=_out(),
                drive=ACVoltageDrive(_in(), _out(), GaussianComplex.one()),
                omega=PositiveAngularFrequency(Rational(1)),
            ),
            budget,
        )

    def test_face_is_exactly_the_observed_fused_identity(self):
        """The named pipeline face returns the SAME value as observing the presentation and
        model directly at the subject's budget -- it is thin wiring, not a reimplementation.
        """
        from smartchem.rlc_ac import circuit_model_ir_of

        diagram = _series(("r", "l"))
        model = _model(diagram, (R100, L2))
        subject = self._subject(diagram, model)
        assert circuit_model_ir_of(subject) == observe_circuit_model_ir(
            diagram, model, budget=subject.canonicalization_budget
        )

    def test_face_decorated_form_is_byte_identical_to_analyze_rlc_ac(self):
        """The face's decorated canonical form equals the one ``analyze_rlc_ac`` computes
        inline, and its circuit identity is that form's digest.  This is a *relational*
        congruence -- both sides decorate through ``RLCModel.canonical_edge_labels`` -- so it
        certifies that the two topology worlds AGREE, not that the labels are correct; the
        absolute invariance of the identity is proved by the classes above.
        """
        from smartchem.rlc_ac import analyze_rlc_ac, circuit_model_ir_of

        diagram = _series(("r", "c"))
        model = _model(diagram, (R100, _component(ElementKind.CAPACITOR, Rational(3))))
        subject = self._subject(diagram, model)
        face = circuit_model_ir_of(subject)
        analysis = analyze_rlc_ac(subject)
        assert face.decorated_canonical_form == analysis.decorated_model_canonical_form
        assert face.circuit_identity == canonical_digest(
            analysis.decorated_model_canonical_form
        )
        assert face.edge_witness == analysis.model_edge_bindings

    def test_face_fails_closed_on_exhausted_budget(self):
        """A subject the analysis pipeline would refuse for budget has no fused identity
        either -- the face fails closed exactly as ``observe_circuit_model_ir`` does.
        """
        from smartchem.rlc_ac import circuit_model_ir_of

        diagram = _single("r")
        model = _model(diagram, (R100,))
        subject = self._subject(diagram, model, budget=0)
        with pytest.raises(CircuitModelIRError, match="not observable"):
            circuit_model_ir_of(subject)

    def test_face_rejects_a_non_subject(self):
        from smartchem.rlc_ac import circuit_model_ir_of

        with pytest.raises(TypeError, match="exact RLCACSubject"):
            circuit_model_ir_of(object())
