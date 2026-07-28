"""Category, migration, and authority controls for the bounded StructureIR adapter."""

from __future__ import annotations

from dataclasses import replace

import pytest

import smartchem
from experiments.compiled_resistive_dc import build_subject as build_e1_subject
from experiments.compiled_rlc_ac import (
    build_damped_subject as build_e2_subject,
    build_singular_subject as build_e2_singular_subject,
)
from smartchem.contracts import canonical_digest
from smartchem.open_diagram import (
    BoundaryRef,
    BoundarySide,
    CanonicalDiagram,
    CanonicalizationBudgetExceeded,
    ComponentKind,
    ComponentSlot,
    DiagramConstructionError,
    ElementPortRef,
    Interface,
    Junction,
    OpenDiagram,
    PortKind,
    canonicalize,
)
from smartchem.program import approve, execute, record_approval
from smartchem.resistive_dc import ExactResistiveDCEngine, compile_resistive_dc
from smartchem.runtime_registry import (
    descriptor_for,
    executor_ids,
    semantic_manifest_digest,
)
from smartchem.structure_ir import (
    STRUCTURE_IR_SCHEMA,
    StructureIR,
    StructureObservationStatus,
    adapt_open_diagram,
    structure_attachment_for_subject,
    structure_braid,
    structure_identity,
)


E = PortKind.ELECTRICAL
UNIT = Interface(())
ONE = Interface((E,))
TWO = Interface((E, E))


def _input(index: int = 0) -> BoundaryRef:
    return BoundaryRef(BoundarySide.INPUT, index)


def _output(index: int = 0) -> BoundaryRef:
    return BoundaryRef(BoundarySide.OUTPUT, index)


def _resistor(name: str = "r") -> OpenDiagram:
    return OpenDiagram.build(
        ONE,
        ONE,
        (ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL),),
        (
            Junction("left", E, (_input(), ElementPortRef(name, "a"))),
            Junction("right", E, (ElementPortRef(name, "b"), _output())),
        ),
    )


def _parallel(
    names: tuple[str, str],
    *,
    reverse_components: bool = False,
    reverse_junctions: bool = False,
) -> OpenDiagram:
    declared = tuple(reversed(names)) if reverse_components else names
    junctions = (
        Junction(
            "left",
            E,
            (_input(), *(ElementPortRef(name, "a") for name in names)),
        ),
        Junction(
            "right",
            E,
            (_output(), *(ElementPortRef(name, "b") for name in names)),
        ),
    )
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(
            ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL)
            for name in declared
        ),
        tuple(reversed(junctions)) if reverse_junctions else junctions,
    )


def _closed_loop(name: str) -> OpenDiagram:
    return OpenDiagram.build(
        UNIT,
        UNIT,
        (ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL),),
        (
            Junction(
                f"node-{name}",
                E,
                (ElementPortRef(name, "a"), ElementPortRef(name, "b")),
            ),
        ),
    )


def test_exact_canonical_encoding_round_trip_and_model_decoration_boundary():
    assert {
        "StructureIR",
        "StructureAdapterWitness",
        "StructureAttachment",
        "adapt_open_diagram",
        "structure_identity",
        "structure_braid",
    }.issubset(smartchem.__all__)
    diagram = _parallel(("first", "second"))
    canonical = canonicalize(diagram)
    structure = StructureIR.from_canonical(canonical)

    assert structure.schema_version == STRUCTURE_IR_SCHEMA
    assert structure.to_canonical_diagram() == canonical
    assert (
        StructureIR.from_open_diagram(structure.to_normalized_open_diagram())
        == structure
    )
    assert len(structure.edges) == 2

    decorated = canonicalize(diagram, edge_labels=("10 ohm", "20 ohm"))
    with pytest.raises(ValueError, match="cannot own domain/model edge decorations"):
        StructureIR.from_canonical(decorated)

    with pytest.raises(DiagramConstructionError, match="use from_canonical"):
        StructureIR(
            STRUCTURE_IR_SCHEMA,
            canonical.dom,
            canonical.cod,
            canonical.input_nodes,
            canonical.output_nodes,
            canonical.node_kinds,
            structure.edges,
        )

    noncanonical = CanonicalDiagram(
        canonical.dom,
        canonical.cod,
        canonical.output_nodes,
        canonical.input_nodes,
        canonical.node_kinds,
        canonical.edges,
    )
    assert noncanonical != canonical
    with pytest.raises(ValueError, match="not the exact canonical S0 form"):
        StructureIR.from_canonical(noncanonical)


def test_alpha_and_declaration_invariance_preserve_distinct_presentation_witnesses():
    left = _parallel(("first", "second"))
    right = _parallel(
        ("alpha", "beta"),
        reverse_components=True,
        reverse_junctions=True,
    )

    left_structure, left_witness = adapt_open_diagram(left, budget=100_000)
    right_structure, right_witness = adapt_open_diagram(right, budget=100_000)

    assert left_structure == right_structure
    assert left_witness.source_presentation_digest != (
        right_witness.source_presentation_digest
    )
    assert left_witness.structure_ir_digest == right_witness.structure_ir_digest
    left_witness.verify(left, left_structure)
    right_witness.verify(right, right_structure)
    with pytest.raises(ValueError, match="different S0 presentation"):
        left_witness.verify(right, right_structure)


def test_structure_ir_represents_the_s0_symmetric_monoidal_laws():
    f = StructureIR.from_open_diagram(_resistor("f"))
    g = StructureIR.from_open_diagram(_resistor("g"))
    h = StructureIR.from_open_diagram(_resistor("h"))
    k = StructureIR.from_open_diagram(_resistor("k"))

    assert structure_identity(ONE).then(f) == f
    assert f.then(structure_identity(ONE)) == f
    assert f.then(g).then(h) == f.then(g.then(h))
    assert f.tensor(structure_identity(UNIT)) == f
    assert structure_identity(UNIT).tensor(f) == f
    assert f.tensor(g).tensor(h) == f.tensor(g.tensor(h))
    assert f.then(g).tensor(h.then(k)) == f.tensor(h).then(g.tensor(k))

    braid = structure_braid(ONE, TWO)
    assert braid.then(structure_braid(TWO, ONE)) == structure_identity(ONE.tensor(TWO))
    parallel = StructureIR.from_open_diagram(_parallel(("g1", "g2")))
    assert f.tensor(parallel).then(structure_braid(ONE, ONE)) == structure_braid(
        ONE, ONE
    ).then(parallel.tensor(f))


def test_budget_refusal_is_typed_and_does_not_make_tensor_partial():
    diagram = _closed_loop("0")
    for index in range(1, 9):
        diagram = diagram.tensor(_closed_loop(str(index)))

    assert len(diagram.edges) == 9
    with pytest.raises(CanonicalizationBudgetExceeded):
        StructureIR.from_open_diagram(diagram, budget=1_000)

    structure, witness = adapt_open_diagram(diagram, budget=1_000)
    assert structure is None
    assert witness.status is StructureObservationStatus.REFUSED
    assert witness.refusal_reason == "canonicalization-budget-exceeded"
    witness.verify(diagram, None)

    zero_structure, zero_witness = adapt_open_diagram(_resistor(), budget=0)
    assert zero_structure is None
    assert zero_witness.refusal_reason == "canonicalization-budget-exhausted"


def test_e1_e2_subject_identity_and_model_binding_survive_the_adapter():
    e1 = build_e1_subject()
    e2 = build_e2_subject()
    singular = build_e2_singular_subject()

    assert canonical_digest(e1) == (
        "af51f2d9d2c2f8062bf6db6f1988d76edef98f38140f1163456265328ce8a2dc"
    )
    assert canonical_digest(e2) == (
        "33bad6b923d602eacfc79eb1b954fe68b991d81c2e6740d91daa248e81f3fe18"
    )
    assert canonical_digest(singular) == (
        "bc087a5e44a13dea521b529213b5c637a74b88cde0b52cc30ee2332806c97110"
    )

    e1_attachment = structure_attachment_for_subject(
        "smartchem.resistive_dc/exact-relation-sparse-mna-v1",
        e1,
    )
    e2_attachment = structure_attachment_for_subject(
        "smartchem.rlc_ac/positive-frequency-passive-rlc-v1",
        e2,
    )
    assert e1_attachment.status is StructureObservationStatus.OBSERVED
    assert e2_attachment.status is StructureObservationStatus.OBSERVED
    assert e1_attachment.witness.source_presentation_digest == (
        e1.model.presentation_digest
    )
    assert e2_attachment.witness.source_presentation_digest == (
        e2.model.presentation_digest
    )
    assert tuple(
        (binding.model_index, binding.structural_edge_index)
        for binding in e2.model.edge_bindings
    ) == ((0, 2), (1, 0), (2, 1))
    e1.model.validate_diagram(e1.diagram)
    e2.model.validate_diagram(e2.diagram)


def test_plan_attachment_records_observation_refusal_and_non_applicability():
    e1 = build_e1_subject()
    e1_plan = compile_resistive_dc(
        "adapter observation",
        e1,
        ExactResistiveDCEngine(),
    )
    assert e1_plan.structure_attachment.status is StructureObservationStatus.OBSERVED
    assert e1_plan.structure_attachment.subject_digest == e1.digest

    refused_subject = replace(e1, canonicalization_budget=0)
    refused_plan = compile_resistive_dc(
        "adapter refusal",
        refused_subject,
        ExactResistiveDCEngine(),
    )
    assert (
        refused_plan.structure_attachment.status is StructureObservationStatus.REFUSED
    )
    assert (
        refused_plan.structure_attachment.reason == "canonicalization-budget-exhausted"
    )

    not_applicable = structure_attachment_for_subject(
        "smartchem.program/reaction-energy-v1",
        e1.experiment,
    )
    assert not_applicable.status is StructureObservationStatus.NOT_APPLICABLE
    assert not_applicable.structure is None and not_applicable.witness is None


def test_forged_plan_attachment_is_rejected_at_construction_and_runtime(tmp_path):
    subject = build_e1_subject()
    engine = ExactResistiveDCEngine()
    plan = compile_resistive_dc("adapter authority", subject, engine)
    admitted_digest = plan.digest
    forged_attachment = replace(
        plan.structure_attachment,
        subject_digest="0" * 64,
    )

    with pytest.raises(ValueError, match="structure_attachment differs"):
        replace(plan, structure_attachment=forged_attachment)

    approved = approve(
        plan,
        record_approval(plan, "test", "exact StructureIR attachment"),
    )
    object.__setattr__(approved.plan, "structure_attachment", forged_attachment)
    assert approved.plan.digest != admitted_digest
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(
        approved,
        "approval_record_digest",
        approved.approval.digest,
    )
    journal = tmp_path / "forged-structure-adapter.json"

    with pytest.raises(ValueError, match="StructureIR plan admission failed"):
        execute(approved, engine, journal_path=journal)

    assert engine.calls == 0
    assert not journal.exists()


def test_attachment_mutation_during_engine_call_invalidates_the_run():
    class MutatingEngine(ExactResistiveDCEngine):
        approved = None

        def solve(self, subject):
            analysis = super().solve(subject)
            assert self.approved is not None
            attachment = self.approved.plan.structure_attachment
            object.__setattr__(
                self.approved.plan,
                "structure_attachment",
                replace(attachment, subject_digest="0" * 64),
            )
            return analysis

    subject = build_e1_subject()
    engine = MutatingEngine()
    plan = compile_resistive_dc("adapter callback mutation", subject, engine)
    approved = approve(
        plan,
        record_approval(plan, "test", "exact pre-callback attachment"),
    )
    engine.approved = approved

    report = execute(approved, engine)

    assert report.record.status.value == "INVALID"
    assert report.result is None and report.certificate is None
    assert engine.calls == 1
    assert any(
        "execution identity changed" in detail for detail in report.record.failures
    )
    assert all(artifact.quarantined for artifact in report.record.artifacts)


_OUTPUT_CONTRACT_DIGESTS = {
    "smartchem.human_isotope/identifiability-v1": (
        "a5e77a662c2941c6f235894cc83299a5848ea149b2b0ef8a002a3b91220d5c10"
    ),
    "smartchem.human_survival/synthetic-weibull-interval-recovery-v1": (
        "084fdccae1bb7116e8154d828c9be94b1c50e498ce7176eab6232d9179de14cd"
    ),
    "smartchem.ising_lattice_gas/finite-c3-equilibrium-map-v1": (
        "8b517a3cc9899d81a70589cb414f0dbc99a2706fcbe249f48e7515556982ebd7"
    ),
    "smartchem.program/reaction-energy-v1": (
        "ee888fdb1a634ca57d8d3c459baa0d80a42660a401b1294dff2811851b77ecd5"
    ),
    "smartchem.resistive_dc/exact-relation-sparse-mna-v1": (
        "fb7a609d2b494373afc2d3565ed4605439b3c8c9a7d2c04563b4fee55e81f6f1"
    ),
    "smartchem.rlc_ac/positive-frequency-passive-rlc-v1": (
        "0a752fc2945e6a715ef42531eb2f9e1d325abe363517a07de80e5693e5619be0"
    ),
    "smartchem.water_wave/finite-section-compatibility-v2": (
        "dea535fce04693b3c15032842ad6113c6489e1c25e22065f5578cc483e74ad8e"
    ),
    "smartchem.water_wave/shallow-water-horizon-v1": (
        "df5e1bf82d9c39a801521028306c7a2c2b5e20d59c92fbe5046f85e6a3cae849"
    ),
    "smartchem.water_wave_continuous/manufactured-steady-v1": (
        "868b8b8cbecf8214687e8563ee2dc2e1725666866a408c99960761d6645d2e41"
    ),
}


def test_registry_and_all_nine_output_contract_digests_are_unchanged():
    assert semantic_manifest_digest() == (
        "a9b8b4f8e0dd698cd018dec31517a3c0c25de4f8569b098bbac15c3e0246359a"
    )
    assert set(_OUTPUT_CONTRACT_DIGESTS) == set(executor_ids())
    assert {
        executor_id: canonical_digest(
            descriptor_for(executor_id).default_output_contract()
        )
        for executor_id in executor_ids()
    } == _OUTPUT_CONTRACT_DIGESTS
