"""Lifecycle controls for the compiled ideal-resistor DC vertical."""
from __future__ import annotations

from dataclasses import replace

import pytest

import smartchem
import smartchem.resistive_dc as resistive_dc_module
import smartchem.runtime_registry as runtime_registry
from smartchem.circuit import (
    DCVoltageDrive,
    DCSolveSpec,
    PositiveResistance,
    Rational,
    ResistiveDCModel,
)
from smartchem.contracts import RunStatus
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
from smartchem.program import RuntimeLimits, approve, execute, record_approval
from smartchem.resistive_dc import (
    ExactResistiveDCEngine,
    ResistiveDCAnalysis,
    ResistiveDCSubject,
    analyze_resistive_dc,
    compile_resistive_dc,
)


E = PortKind.ELECTRICAL
ONE = Interface((E,))


def _in() -> BoundaryRef:
    return BoundaryRef(BoundarySide.INPUT, 0)


def _out() -> BoundaryRef:
    return BoundaryRef(BoundarySide.OUTPUT, 0)


def _bridge(*, reverse_junctions: bool = False) -> OpenDiagram:
    """P-L, L-N, P-R, R-N, L-R: not a series/parallel dispatcher fixture."""
    names = ("r0", "r1", "r2", "r3", "r4")
    junctions = (
        Junction("positive", E, (_in(), ElementPortRef("r0", "a"), ElementPortRef("r2", "a"))),
        Junction("left", E, (ElementPortRef("r0", "b"), ElementPortRef("r1", "a"), ElementPortRef("r4", "a"))),
        Junction("right", E, (ElementPortRef("r2", "b"), ElementPortRef("r3", "a"), ElementPortRef("r4", "b"))),
        Junction("negative", E, (_out(), ElementPortRef("r1", "b"), ElementPortRef("r3", "b"))),
    )
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names),
        tuple(reversed(junctions)) if reverse_junctions else junctions,
    )


def _subject(*, budget: int = 100_000) -> ResistiveDCSubject:
    diagram = _bridge()
    model = ResistiveDCModel.for_diagram(
        diagram,
        tuple(PositiveResistance(Rational(value)) for value in (100, 200, 300, 400, 500)),
    )
    experiment = DCSolveSpec(_out(), DCVoltageDrive(_in(), _out(), Rational(10)))
    return ResistiveDCSubject(diagram, model, experiment, budget)


def _approved(subject: ResistiveDCSubject, engine: object, **kwargs: object):
    plan = compile_resistive_dc("solve the declared ideal bridge", subject, engine, **kwargs)
    return plan, approve(plan, record_approval(plan, "test", "ideal mathematical circuit only"))


class TestResistiveDCLifecycle:
    def test_public_exports_and_closed_registry_descriptor_are_exact(self):
        assert {
            "OpenDiagram",
            "BoundaryLinearRelation",
            "ResistiveDCSubject",
            "ExactResistiveDCEngine",
            "compile_resistive_dc",
            "compile_session_resistive_dc",
            "resistive_dc_slot",
        }.issubset(smartchem.__all__)
        descriptor = runtime_registry.descriptor_for(
            "smartchem.resistive_dc/exact-relation-sparse-mna-v1"
        )
        assert descriptor.subject_type.resolve() is ResistiveDCSubject
        assert descriptor.runner.resolve() is resistive_dc_module._execute_resistive_dc

    def test_complete_write_once_run_retains_exact_three_outputs_and_bridge_numbers(self, tmp_path):
        engine = ExactResistiveDCEngine()
        plan, approved = _approved(_subject(), engine)
        journal = tmp_path / "resistive-dc.json"
        report = execute(approved, engine, journal_path=journal)
        assert report.record.status is RunStatus.COMPLETE
        assert report.result is not None and report.certificate is not None
        assert engine.calls == 1
        assert journal.exists()
        assert tuple(value.observable_id for value in report.result.values) == plan.request.output_contract.observable_ids
        payloads = {value.observable_id: value.payload for value in report.result.values}
        analysis = payloads["resistive_dc_analysis"]
        assert type(analysis) is ResistiveDCAnalysis
        assert payloads["resistive_dc_boundary_relation"] == analysis.boundary_relation
        assert payloads["resistive_dc_sparse_solution"] == analysis.sparse_solution
        assert [node.volts for node in analysis.sparse_solution.nodes] == pytest.approx(
            [10.0, 6.580645161290322, 5.935483870967741, 0.0]
        )
        assert analysis.sparse_solution.source.current_entering_positive_amperes == pytest.approx(-0.04774193548387098)
        assert report.certificate.claim_scope.kind.value == "LITERAL"
        with pytest.raises(FileExistsError):
            execute(approved, engine, journal_path=journal)
        assert engine.calls == 1

    def test_contract_mutation_cannot_be_approved(self):
        engine = ExactResistiveDCEngine()
        normal = compile_resistive_dc("bridge", _subject(), engine)
        mutated_contract = replace(normal.request.output_contract, diagnostics=("changed",))
        mutated = compile_resistive_dc("bridge", _subject(), engine, output_contract=mutated_contract)
        assert mutated.blockers
        with pytest.raises(ValueError, match="blockers"):
            approve(mutated, record_approval(mutated, "test", "mutated contract"))

    def test_zero_canonicalization_cap_is_refused_before_engine_call(self):
        engine = ExactResistiveDCEngine()
        _, approved = _approved(_subject(budget=0), engine)
        report = execute(approved, engine)
        assert report.record.status is RunStatus.REFUSED
        assert report.result is None
        assert engine.calls == 0
        assert all(artifact.quarantined for artifact in report.record.artifacts)

    def test_engine_result_mutation_is_invalid_and_quarantined(self):
        class MutatingEngine(ExactResistiveDCEngine):
            def solve(self, subject):
                analysis = super().solve(subject)
                bad_solution = replace(
                    analysis.sparse_solution,
                    branches=analysis.sparse_solution.branches[:-1],
                )
                return replace(analysis, sparse_solution=bad_solution)

        engine = MutatingEngine()
        _, approved = _approved(_subject(), engine)
        report = execute(approved, engine)
        assert report.record.status is RunStatus.INVALID
        assert report.result is None
        assert any(artifact.quarantined for artifact in report.record.checkpoints)

    def test_subject_model_binding_and_floating_solver_refusal(self):
        subject = _subject()
        other = _bridge(reverse_junctions=True)
        with pytest.raises(ValueError, match="resistance count|not bound"):
            ResistiveDCSubject(other, subject.model, subject.experiment, 100)

        floating = OpenDiagram.build(
            ONE,
            ONE,
            (
                ComponentSlot("main", ComponentKind.ELECTRICAL_TWO_TERMINAL),
                ComponentSlot("orphan", ComponentKind.ELECTRICAL_TWO_TERMINAL),
            ),
            (
                Junction("positive", E, (_in(), ElementPortRef("main", "a"))),
                Junction("negative", E, (_out(), ElementPortRef("main", "b"))),
                Junction("orphan", E, (ElementPortRef("orphan", "a"), ElementPortRef("orphan", "b"))),
            ),
        )
        model = ResistiveDCModel.for_diagram(
            floating,
            (PositiveResistance(Rational(10)), PositiveResistance(Rational(10))),
        )
        floating_subject = ResistiveDCSubject(
            floating, model, DCSolveSpec(_out(), DCVoltageDrive(_in(), _out(), Rational(1))), 100
        )
        engine = ExactResistiveDCEngine()
        _, approved = _approved(floating_subject, engine)
        report = execute(approved, engine)
        assert report.record.status is RunStatus.REFUSED
        assert report.result is None
        assert any(artifact.quarantined for artifact in report.record.artifacts)

    def test_resource_cap_quarantines_before_one_call(self):
        engine = ExactResistiveDCEngine()
        _, approved = _approved(_subject(), engine, limits=RuntimeLimits(max_engine_calls=0))
        report = execute(approved, engine)
        assert report.record.status is RunStatus.INCOMPLETE
        assert engine.calls == 0
