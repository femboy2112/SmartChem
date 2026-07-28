"""Lifecycle controls for the compiled positive-frequency passive-RLC vertical."""

from __future__ import annotations

from dataclasses import replace

import pytest

import smartchem.rlc_ac as rlc_ac_module
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
from smartchem.rlc_ac import (
    ExactRLCACEngine,
    RLCACAnalysis,
    compile_rlc_ac,
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
    RLCACSubject,
    RLCComponent,
    RLCModel,
    Rational,
)


E = PortKind.ELECTRICAL
ONE = Interface((E,))


def _in() -> BoundaryRef:
    return BoundaryRef(BoundarySide.INPUT, 0)


def _out() -> BoundaryRef:
    return BoundaryRef(BoundarySide.OUTPUT, 0)


def _parallel_rlc() -> OpenDiagram:
    """One source-driven R/L/C parallel network; the resistor damps its resonance."""
    names = ("r", "l", "c")
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(
            ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names
        ),
        (
            Junction(
                "positive", E, (_in(), *(ElementPortRef(name, "a") for name in names))
            ),
            Junction(
                "negative", E, (_out(), *(ElementPortRef(name, "b") for name in names))
            ),
        ),
    )


def _series_rlc() -> OpenDiagram:
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(
            ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL)
            for name in ("r", "l", "c")
        ),
        (
            Junction("positive", E, (_in(), ElementPortRef("r", "a"))),
            Junction("first", E, (ElementPortRef("r", "b"), ElementPortRef("l", "a"))),
            Junction("second", E, (ElementPortRef("l", "b"), ElementPortRef("c", "a"))),
            Junction("negative", E, (_out(), ElementPortRef("c", "b"))),
        ),
    )


def _subject(*, budget: int = 100_000) -> RLCACSubject:
    diagram = _parallel_rlc()
    model = RLCModel.for_diagram(
        diagram,
        (
            RLCComponent(ElementKind.RESISTOR, PositiveResistance(Rational(10))),
            RLCComponent(ElementKind.INDUCTOR, PositiveInductance(Rational(2))),
            RLCComponent(ElementKind.CAPACITOR, PositiveCapacitance(Rational(1))),
        ),
    )
    experiment = ACSolveSpec(
        _out(),
        ACVoltageDrive(_in(), _out(), GaussianComplex.from_parts(10)),
        PositiveAngularFrequency(Rational(1)),
    )
    return RLCACSubject(diagram, model, experiment, budget)


def _singular_subject() -> RLCACSubject:
    diagram = OpenDiagram.build(
        ONE,
        ONE,
        (
            ComponentSlot("l", ComponentKind.ELECTRICAL_TWO_TERMINAL),
            ComponentSlot("c", ComponentKind.ELECTRICAL_TWO_TERMINAL),
        ),
        (
            Junction("positive", E, (_in(), ElementPortRef("l", "a"))),
            Junction(
                "middle",
                E,
                (ElementPortRef("l", "b"), ElementPortRef("c", "a")),
            ),
            Junction("negative", E, (ElementPortRef("c", "b"), _out())),
        ),
    )
    model = RLCModel.for_diagram(
        diagram,
        (
            RLCComponent(ElementKind.INDUCTOR, PositiveInductance(Rational(1))),
            RLCComponent(ElementKind.CAPACITOR, PositiveCapacitance(Rational(1))),
        ),
    )
    return RLCACSubject(
        diagram,
        model,
        ACSolveSpec(
            _out(),
            ACVoltageDrive(_in(), _out(), GaussianComplex.from_parts(1)),
            PositiveAngularFrequency(Rational(1)),
        ),
        100_000,
    )


def _approved(subject: RLCACSubject, engine: object, **kwargs: object):
    plan = compile_rlc_ac(
        "solve the declared damped passive RLC control", subject, engine, **kwargs
    )
    return plan, approve(
        plan,
        record_approval(
            plan, "test", "fixed-frequency ideal mathematical circuit only"
        ),
    )


class TestRLCACLifecycle:
    def test_complete_write_once_run_retains_all_four_outputs(self, tmp_path):
        engine = ExactRLCACEngine()
        plan, approved = _approved(_subject(), engine)
        journal = tmp_path / "rlc-ac.json"

        report = execute(approved, engine, journal_path=journal)

        assert report.record.status is RunStatus.COMPLETE
        assert report.result is not None and report.certificate is not None
        assert engine.calls == 1
        assert journal.exists()
        assert (
            tuple(value.observable_id for value in report.result.values)
            == plan.request.output_contract.observable_ids
        )
        payloads = {
            value.observable_id: value.payload for value in report.result.values
        }
        analysis = payloads["rlc_ac_analysis"]
        assert type(analysis) is RLCACAnalysis
        assert payloads["rlc_ac_boundary_relation"] == analysis.boundary_relation
        assert payloads["rlc_ac_sparse_solution"] == analysis.sparse_solution
        assert payloads["rlc_ac_direct_verification"].passed
        assert len(analysis.sparse_solution.nodes) == 2
        assert len(analysis.sparse_solution.branches) == 3
        assert report.certificate.claim_scope.kind.value == "LITERAL"
        with pytest.raises(FileExistsError):
            execute(approved, engine, journal_path=journal)
        assert engine.calls == 1

    def test_contract_mutation_cannot_be_approved(self):
        engine = ExactRLCACEngine()
        normal = compile_rlc_ac("RLC", _subject(), engine)
        mutated_contract = replace(
            normal.request.output_contract, diagnostics=("changed",)
        )
        mutated = compile_rlc_ac(
            "RLC", _subject(), engine, output_contract=mutated_contract
        )
        assert mutated.blockers
        with pytest.raises(ValueError, match="blockers"):
            approve(mutated, record_approval(mutated, "test", "mutated contract"))

    def test_zero_canonicalization_cap_is_refused_before_engine_call(self):
        engine = ExactRLCACEngine()
        _, approved = _approved(_subject(budget=0), engine)

        report = execute(approved, engine)

        assert report.record.status is RunStatus.REFUSED
        assert report.result is None
        assert engine.calls == 0
        assert all(artifact.quarantined for artifact in report.record.artifacts)

    def test_exact_lossless_singular_resonance_has_explicit_refusal_detail(self):
        engine = ExactRLCACEngine()
        _, approved = _approved(_singular_subject(), engine)

        report = execute(approved, engine)

        assert report.record.status is RunStatus.REFUSED
        assert engine.calls == 0
        assert any("rank deficient" in detail for detail in report.record.failures)
        assert any(
            "without regularization" in detail for detail in report.record.failures
        )

    def test_engine_result_mutation_is_invalid_and_quarantined(self):
        class MutatingEngine(ExactRLCACEngine):
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

    def test_callback_plan_mutation_is_invalid_and_quarantined(self):
        class PlanMutatingRaisingEngine(ExactRLCACEngine):
            def __init__(self):
                super().__init__()
                self.approved = None

            def solve(self, subject):
                assert self.approved is not None
                contract = self.approved.plan.request.output_contract
                object.__setattr__(
                    self.approved.plan.request,
                    "output_contract",
                    replace(
                        contract, diagnostics=("mutated before backend exception",)
                    ),
                )
                raise RuntimeError("backend exception after mutating approved plan")

        engine = PlanMutatingRaisingEngine()
        _, approved = _approved(_subject(), engine)
        engine.approved = approved

        report = execute(approved, engine)

        assert report.record.status is RunStatus.INVALID
        assert report.result is None and report.certificate is None
        assert report.record.artifacts
        assert all(artifact.quarantined for artifact in report.record.artifacts)
        assert any(
            "execution identity changed" in detail for detail in report.record.failures
        )

    def test_subject_model_binding_and_resource_cap_prevent_engine_call(self):
        subject = _subject()
        other = _series_rlc()
        # A same-size but differently connected presentation is not model-bound.
        with pytest.raises(ValueError, match="not bound"):
            RLCACSubject(other, subject.model, subject.experiment, 100)

        engine = ExactRLCACEngine()
        _, approved = _approved(
            _subject(), engine, limits=RuntimeLimits(max_engine_calls=0)
        )
        report = execute(approved, engine)

        assert report.record.status is RunStatus.INCOMPLETE
        assert report.result is None
        assert engine.calls == 0

    def test_executor_is_nominally_separate_from_dc(self):
        assert rlc_ac_module.ExactRLCACEngine is ExactRLCACEngine
        assert "transient" in " ".join(rlc_ac_module.RLC_AC_CASUALTIES)
        assert "lossless-resonant" in " ".join(rlc_ac_module.RLC_AC_OMISSIONS)
