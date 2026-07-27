"""Typed bindings are additive: physical slots cannot close on text alone."""
from __future__ import annotations

import pytest

from smartchem.category import Molecule, Reaction
from smartchem.contracts import (
    DerivationRef,
    InferenceKind,
    ObligationStage,
    ValidityObligation,
)
from smartchem.ledger import (
    COMPILED,
    COMPILED_SUBJECT_TO,
    BindingSchema,
    DerivedOption,
    Slot,
    Spec,
    TypedBinding,
    reaction_slot,
    shepherd,
)


def derived_ref(scope: str = "test") -> DerivationRef:
    return DerivationRef(
        kind=InferenceKind.DERIVED_COMPLETE,
        source="tests.test_typed_ledger",
        source_digest="a" * 64,
        scope=scope,
    )


class TestBindingSchema:
    def test_schema_slot_rejects_a_legacy_placeholder_at_construction(self):
        with pytest.raises(TypeError, match="legacy text"):
            Slot("distance", "<distance>", binding="<answered>",
                 schema=BindingSchema((float,)))

    def test_spec_bind_refuses_to_close_a_schema_slot_with_text(self):
        spec = Spec("physical", (
            Slot("distance", "<distance>", schema=BindingSchema((float,))),
        ))
        with pytest.raises(TypeError, match="bind_typed"):
            spec.bind("distance", "<answered>")
        assert spec.measure() == 1

    def test_typed_binding_requires_the_declared_runtime_type(self):
        spec = Spec("physical", (
            Slot("distance", "<distance>", schema=BindingSchema((float,))),
        ))
        with pytest.raises(TypeError, match="expected a value"):
            spec.bind_typed(
                "distance", 3, source_text="3", inference=InferenceKind.QUESTION_CONFIRMED
            )

    def test_typed_binding_runs_its_named_validator(self):
        positive = BindingSchema(
            (float,), validator_id="positive-distance", validator=lambda value: value > 0.0
        )
        spec = Spec("physical", (Slot("distance", "<distance>", schema=positive),))
        with pytest.raises(ValueError, match="positive-distance"):
            spec.bind_typed(
                "distance", -1.0, source_text="-1 A",
                inference=InferenceKind.QUESTION_CONFIRMED,
            )
        bound = spec.bind_typed(
            "distance", 1.5, source_text="1.5 A",
            inference=InferenceKind.QUESTION_CONFIRMED,
        )
        slot = bound.slots[0]
        assert slot.is_bound and slot.binding == "1.5 A"
        assert slot.typed_binding is not None
        assert slot.typed_binding.value == 1.5
        assert slot.typed_binding.inference is InferenceKind.QUESTION_CONFIRMED

    def test_checked_and_derived_bindings_need_machine_provenance(self):
        schema = BindingSchema((int,))
        with pytest.raises(ValueError, match="machine derivation"):
            TypedBinding(1, "1", InferenceKind.WRITTEN_CHECKED)
        bound = Slot("n", "<n>", schema=schema).bind_typed(
            1,
            source_text="1",
            inference=InferenceKind.WRITTEN_CHECKED,
            derivation=derived_ref("integer check"),
        )
        assert bound.typed_binding.derivation == derived_ref("integer check")

    def test_legacy_text_slots_keep_their_existing_constructor_and_bind_path(self):
        original = Spec("legacy", (Slot("answer", "<answer>"),))
        bound = original.bind("answer", "<answered>")
        assert original.measure() == 1
        assert bound.measure() == 0
        assert bound.slots[0].binding == "<answered>"
        assert bound.slots[0].typed_binding is None


class TestDerivedOptions:
    def test_reaction_slot_carries_machine_derived_options_aligned_with_its_menu(self):
        h = Molecule.atom("H")
        h2 = Molecule.diatomic("H", "H")
        slot = reaction_slot("formation", "relate H and H2", (h, h2))
        assert tuple(option.display for option in slot.derived_options) == slot.menu
        assert all(isinstance(option, DerivedOption) for option in slot.derived_options)
        assert all(isinstance(option.value, Reaction) for option in slot.derived_options)
        assert all(option.derivation.kind is InferenceKind.DERIVED_COMPLETE
                   for option in slot.derived_options)
        assert len({option.derivation.source_digest for option in slot.derived_options}) == 1

    def test_derived_option_display_cannot_drift_from_the_legacy_menu(self):
        option = DerivedOption("one", 1, derived_ref())
        with pytest.raises(ValueError, match="exactly match"):
            Slot("x", "<x>", menu=("different",), derivation="test",
                 derived_options=(option,))


class TestTypedPostObligations:
    def test_a_post_obligation_keeps_a_closed_typed_spec_subject_to_the_run(self):
        post = ValidityObligation(
            name="T1 diagnostic",
            stage=ObligationStage.POST,
            evaluator_id="qc.t1",
            description="single-reference diagnostic after the calculation",
        )
        spec = Spec("gated", (
            Slot("method", "CCSD(T)", schema=BindingSchema((str,)), obligations=(post,)),
        ))
        session = shepherd(
            spec,
            lambda current, holes: current.bind_typed(
                holes[0].name,
                "CCSD(T)",
                source_text="CCSD(T)",
                inference=InferenceKind.QUESTION_CONFIRMED,
            ),
        )
        assert session.outcome == COMPILED_SUBJECT_TO
        assert session.spec.subject_to() == session.spec.slots
        assert "T1 diagnostic" in session.explain()

    def test_a_pre_obligation_does_not_create_a_post_run_outcome(self):
        pre = ValidityObligation(
            name="neutrality",
            stage=ObligationStage.PRE,
            evaluator_id="chem.neutral",
            description="pre-run neutral charge check",
        )
        spec = Spec("pre", (
            Slot("charge", "0", schema=BindingSchema((int,)), obligations=(pre,)),
        ))
        session = shepherd(
            spec,
            lambda current, holes: current.bind_typed(
                holes[0].name, 0, source_text="0",
                inference=InferenceKind.QUESTION_CONFIRMED,
            ),
        )
        assert session.outcome == COMPILED
