"""Independent-verifier and forced common-mode controls for E1."""
from __future__ import annotations

import ast
from dataclasses import fields, make_dataclass, replace
import inspect
import random

import pytest

import smartchem.circuit as circuit
import smartchem.resistive_dc as resistive_dc_module
import smartchem.resistive_dc_verifier as verifier
from smartchem.circuit import (
    BoundaryLinearRelation,
    CircuitDiagnostics,
    DCVoltageDrive,
    DCSolveSpec,
    PositiveResistance,
    Rational,
    ResistorEdgeBinding,
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
from smartchem.program import approve, execute, record_approval
from smartchem.resistive_dc import (
    ExactResistiveDCEngine,
    ResistiveDCSubject,
    analyze_resistive_dc,
    compile_resistive_dc,
)
from smartchem.resistive_dc_verifier import (
    DirectVerificationDecision,
    verify_resistive_dc_analysis,
)
from test_circuit import (
    _bridge as circuit_bridge,
    _cycle,
    _parallel,
    _resistances,
    _series,
    _single,
    _spec,
)
from test_resistive_dc_program import _in, _out, _subject


def _analysis_mutation(analysis, mutation: str):
    solution = analysis.sparse_solution
    if mutation == "node-voltage":
        node = replace(solution.nodes[1], volts=solution.nodes[1].volts + 1.0)
        return replace(
            analysis,
            sparse_solution=replace(
                solution,
                nodes=(solution.nodes[0], node) + solution.nodes[2:],
            ),
        )
    if mutation == "branch-current":
        branch = replace(
            solution.branches[0],
            current_amperes=solution.branches[0].current_amperes + 0.01,
        )
        return replace(
            analysis,
            sparse_solution=replace(
                solution,
                branches=(branch,) + solution.branches[1:],
            ),
        )
    if mutation == "source-sign-and-power":
        source = replace(
            solution.source,
            current_entering_positive_amperes=(
                -solution.source.current_entering_positive_amperes
            ),
            absorbed_power_watts=-solution.source.absorbed_power_watts,
        )
        return replace(
            analysis,
            sparse_solution=replace(solution, source=source),
        )
    if mutation == "branch-power":
        branch = replace(
            solution.branches[0],
            absorbed_power_watts=solution.branches[0].absorbed_power_watts + 1.0,
        )
        return replace(
            analysis,
            sparse_solution=replace(
                solution,
                branches=(branch,) + solution.branches[1:],
            ),
        )
    if mutation == "branch-omitted":
        return replace(
            analysis,
            sparse_solution=replace(solution, branches=solution.branches[:-1]),
        )
    if mutation == "branch-duplicated":
        return replace(
            analysis,
            sparse_solution=replace(
                solution,
                branches=solution.branches + (solution.branches[-1],),
            ),
        )
    if mutation == "branch-resistance-swapped":
        branch = replace(
            solution.branches[0],
            resistance=solution.branches[1].resistance,
        )
        return replace(
            analysis,
            sparse_solution=replace(
                solution,
                branches=(branch,) + solution.branches[1:],
            ),
        )
    if mutation == "boundary-relation":
        return replace(
            analysis,
            boundary_relation=BoundaryLinearRelation.identity(1),
        )
    if mutation == "structural-canonical-form":
        return replace(
            analysis,
            structural_canonical_form=analysis.decorated_model_canonical_form,
        )
    if mutation == "decorated-canonical-form":
        return replace(
            analysis,
            decorated_model_canonical_form=analysis.structural_canonical_form,
        )
    if mutation == "edge-binding-witness":
        binding = replace(
            analysis.model_edge_bindings[0],
            structural_edge_index=1,
        )
        return replace(
            analysis,
            model_edge_bindings=(binding,) + analysis.model_edge_bindings[1:],
        )
    if mutation == "zero-diagnostics":
        return replace(
            analysis,
            sparse_solution=replace(
                solution,
                diagnostics=CircuitDiagnostics(
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
        )
    if mutation == "zero-diagnostics-hide-bad-node":
        bad = _analysis_mutation(analysis, "node-voltage")
        return replace(
            bad,
            sparse_solution=replace(
                bad.sparse_solution,
                diagnostics=CircuitDiagnostics(
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
        )
    raise AssertionError(f"unknown mutation {mutation}")


def _nominal_spoof(value):
    """Build a different dataclass with the genuine class's module/name/fields."""
    genuine = type(value)
    spoof_type = make_dataclass(
        genuine.__name__,
        tuple((field.name, field.type) for field in fields(value)),
        frozen=True,
        namespace={"__module__": genuine.__module__},
    )
    return spoof_type(*(getattr(value, field.name) for field in fields(value)))


def _install_nominal_spoof(analysis, target: str):
    if target == "nested-result":
        object.__setattr__(
            analysis,
            "sparse_solution",
            _nominal_spoof(analysis.sparse_solution),
        )
    elif target == "boundary-relation":
        object.__setattr__(
            analysis,
            "boundary_relation",
            _nominal_spoof(analysis.boundary_relation),
        )
    elif target == "edge-binding":
        object.__setattr__(
            analysis,
            "model_edge_bindings",
            (_nominal_spoof(analysis.model_edge_bindings[0]),)
            + analysis.model_edge_bindings[1:],
        )
    else:  # pragma: no cover - test helper invariant
        raise AssertionError(target)
    return analysis


def test_verifier_source_has_no_production_solver_or_relation_dependency():
    tree = ast.parse(inspect.getsource(verifier))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert "circuit" not in imported_modules
    assert "resistive_dc" not in imported_modules
    forbidden_calls = {
        "analyze_resistive_dc",
        "solve_resistive_dc",
        "blackbox_resistive_dc",
        "_assemble_mna",
        "_solve_sparse",
        "_rref",
    }
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    called.update(
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    )
    assert not (called & forbidden_calls)


@pytest.mark.parametrize(
    ("diagram_factory", "resistances", "volts"),
    (
        (_single, (100,), 10),
        (_series, (100, 200), 12),
        (_parallel, (100, 200), 10),
        (circuit_bridge, (100, 200, 300, 400, 500), 10),
        (_cycle, (100, 200, 300), 6),
    ),
)
def test_direct_verifier_accepts_analytic_and_nongeneric_controls(
    diagram_factory,
    resistances,
    volts,
):
    diagram = diagram_factory()
    subject = ResistiveDCSubject(
        diagram,
        _resistances(diagram, *resistances),
        _spec(volts),
        100_000,
    )
    report = verify_resistive_dc_analysis(
        subject,
        analyze_resistive_dc(subject),
    )
    assert report.decision is DirectVerificationDecision.PASS
    assert report.canonical_forms_ok
    assert report.inventory_ok
    assert report.exact_relation_ok
    assert report.branch_law_ok
    assert report.kcl_ok
    assert report.source_constraint_ok
    assert report.power_ok
    assert report.passivity_ok


def test_verifier_still_passes_when_every_production_computation_is_disabled(
    monkeypatch,
):
    subject = _subject()
    candidate = analyze_resistive_dc(subject)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("production computation was called by the direct verifier")

    for name in (
        "_rref",
        "_project_relation",
        "blackbox_resistive_dc",
        "_assemble_mna",
        "_solve_sparse",
        "solve_resistive_dc",
    ):
        monkeypatch.setattr(circuit, name, forbidden)
    monkeypatch.setattr(resistive_dc_module, "analyze_resistive_dc", forbidden)
    assert verify_resistive_dc_analysis(subject, candidate).passed


def test_seeded_connected_multigraph_holdout_passes_direct_verification():
    rng = random.Random(20260727)
    electrical = PortKind.ELECTRICAL
    one = Interface((electrical,))
    for case in range(64):
        node_count = rng.randint(2, 6)
        edge_nodes = [(node, node + 1) for node in range(node_count - 1)]
        edge_nodes.extend(
            (rng.randrange(node_count), rng.randrange(node_count))
            for _ in range(rng.randint(0, 4))
        )
        components = tuple(
            ComponentSlot(f"r{index}", ComponentKind.ELECTRICAL_TWO_TERMINAL)
            for index in range(len(edge_nodes))
        )
        endpoints: list[list[object]] = [[] for _ in range(node_count)]
        endpoints[0].append(BoundaryRef(BoundarySide.INPUT, 0))
        endpoints[-1].append(BoundaryRef(BoundarySide.OUTPUT, 0))
        for index, (node_a, node_b) in enumerate(edge_nodes):
            endpoints[node_a].append(ElementPortRef(f"r{index}", "a"))
            endpoints[node_b].append(ElementPortRef(f"r{index}", "b"))
        diagram = OpenDiagram.build(
            one,
            one,
            components,
            tuple(
                Junction(f"n{index}", electrical, tuple(node_endpoints))
                for index, node_endpoints in enumerate(endpoints)
            ),
        )
        resistance_values = tuple(
            rng.randint(1, 1000)
            for _ in edge_nodes
        )
        subject = ResistiveDCSubject(
            diagram,
            _resistances(diagram, *resistance_values),
            _spec(rng.randint(-20, 20) or 1),
            1_000_000,
        )
        report = verify_resistive_dc_analysis(
            subject,
            analyze_resistive_dc(subject),
        )
        assert report.decision is DirectVerificationDecision.PASS, (
            case,
            edge_nodes,
            resistance_values,
            report.reasons,
        )


def test_nonidentity_model_reindex_witness_drives_all_semantic_paths():
    diagram = _series()
    model = ResistiveDCModel.for_diagram(
        diagram,
        (
            PositiveResistance(Rational(200)),
            PositiveResistance(Rational(100)),
        ),
        edge_bindings=(
            ResistorEdgeBinding(0, 1),
            ResistorEdgeBinding(1, 0),
        ),
    )
    subject = ResistiveDCSubject(diagram, model, _spec(12), 100_000)
    analysis = analyze_resistive_dc(subject)
    assert [
        branch.resistance.ohms
        for branch in analysis.sparse_solution.branches
    ] == [Rational(100), Rational(200)]
    assert [
        branch.current_amperes
        for branch in analysis.sparse_solution.branches
    ] == pytest.approx([0.04, 0.04])
    report = verify_resistive_dc_analysis(subject, analysis)
    assert report.decision is DirectVerificationDecision.PASS
    assert report.inventory_ok
    assert analysis.model_edge_bindings == model.edge_bindings


@pytest.mark.parametrize(
    "mutation",
    (
        "node-voltage",
        "branch-current",
        "source-sign-and-power",
        "branch-power",
        "branch-omitted",
        "branch-duplicated",
        "branch-resistance-swapped",
        "boundary-relation",
        "structural-canonical-form",
        "decorated-canonical-form",
        "edge-binding-witness",
        "zero-diagnostics",
        "zero-diagnostics-hide-bad-node",
    ),
)
def test_direct_verifier_rejects_each_retained_output_family(mutation):
    subject = _subject()
    forged = _analysis_mutation(analyze_resistive_dc(subject), mutation)
    report = verify_resistive_dc_analysis(subject, forged)
    assert report.decision is DirectVerificationDecision.FAIL
    assert not report.passed
    assert report.reasons


@pytest.mark.parametrize(
    "target",
    ("nested-result", "boundary-relation", "edge-binding"),
)
def test_nominal_dataclass_impostors_are_rejected_by_class_identity(target):
    subject = _subject()
    forged = _install_nominal_spoof(analyze_resistive_dc(subject), target)
    report = verify_resistive_dc_analysis(subject, forged)
    assert report.decision is DirectVerificationDecision.FAIL
    assert not report.passed


@pytest.mark.parametrize(
    "target",
    ("nested-result", "boundary-relation", "edge-binding"),
)
def test_runtime_invalidates_and_quarantines_nominal_dataclass_impostors(target):
    class NominalImpostorEngine(ExactResistiveDCEngine):
        def solve(self, subject):
            return _install_nominal_spoof(super().solve(subject), target)

    subject = _subject()
    engine = NominalImpostorEngine()
    plan = compile_resistive_dc("bridge", subject, engine)
    approved = approve(
        plan,
        record_approval(plan, "test", f"reject nominal impostor {target}"),
    )
    report = execute(approved, engine)
    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert report.certificate is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)


@pytest.mark.parametrize(
    "target",
    (
        "model",
        "experiment",
        "drive",
        "drive-rational",
        "model-resistance",
        "branch-resistance",
    ),
)
def test_recursive_approved_input_and_branch_impostors_are_rejected(target):
    subject = _subject()
    analysis = analyze_resistive_dc(subject)
    if target == "model":
        object.__setattr__(subject, "model", _nominal_spoof(subject.model))
    elif target == "experiment":
        object.__setattr__(
            subject,
            "experiment",
            _nominal_spoof(subject.experiment),
        )
    elif target == "drive":
        object.__setattr__(
            subject.experiment,
            "drive",
            _nominal_spoof(subject.experiment.drive),
        )
    elif target == "drive-rational":
        object.__setattr__(
            subject.experiment.drive,
            "volts",
            _nominal_spoof(subject.experiment.drive.volts),
        )
    elif target == "model-resistance":
        object.__setattr__(
            subject.model,
            "resistances",
            (_nominal_spoof(subject.model.resistances[0]),)
            + subject.model.resistances[1:],
        )
    elif target == "branch-resistance":
        first = analysis.sparse_solution.branches[0]
        object.__setattr__(
            first,
            "resistance",
            _nominal_spoof(first.resistance),
        )
    report = verify_resistive_dc_analysis(subject, analysis)
    assert not report.passed
    assert report.decision in {
        DirectVerificationDecision.REFUSE,
        DirectVerificationDecision.FAIL,
    }


def test_runtime_invalidates_approved_subject_nominal_model_substitution():
    class SpoofModelEngine(ExactResistiveDCEngine):
        def solve(self, subject):
            analysis = super().solve(subject)
            object.__setattr__(subject, "model", _nominal_spoof(subject.model))
            return analysis

    subject = _subject()
    engine = SpoofModelEngine()
    plan = compile_resistive_dc("bridge", subject, engine)
    approved = approve(
        plan,
        record_approval(plan, "test", "reject post-approval model substitution"),
    )
    report = execute(approved, engine)
    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert report.certificate is None
    assert all(item.quarantined for item in report.record.artifacts)


def test_runtime_invalidates_coherent_post_approval_model_rebinding():
    class RebindingEngine(ExactResistiveDCEngine):
        def solve(self, subject):
            self.calls += 1
            rebound = ResistiveDCModel.for_diagram(
                subject.diagram,
                tuple(
                    PositiveResistance(
                        Rational(
                            resistance.ohms.numerator * 2,
                            resistance.ohms.denominator,
                        )
                    )
                    for resistance in subject.model.resistances
                ),
                edge_bindings=subject.model.edge_bindings,
            )
            object.__setattr__(subject, "model", rebound)
            analysis = analyze_resistive_dc(subject)
            # A dynamic equality-only guard can be defeated by rewriting the approval to
            # name the substituted plan.  The runtime must compare against its pre-call
            # snapshot as well.
            object.__setattr__(
                self.approved.approval,
                "plan_digest",
                self.approved.plan.digest,
            )
            object.__setattr__(
                self.approved,
                "approval_record_digest",
                self.approved.approval.digest,
            )
            return analysis

    subject = _subject()
    engine = RebindingEngine()
    plan = compile_resistive_dc("bridge", subject, engine)
    approved = approve(
        plan,
        record_approval(plan, "test", "reject coherent approved-input replacement"),
    )
    engine.approved = approved
    report = execute(approved, engine)
    assert engine.calls == 1
    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert report.certificate is None
    assert all(item.quarantined for item in report.record.artifacts)


@pytest.mark.parametrize(
    "mutation",
    (
        "structural-canonical-form",
        "decorated-canonical-form",
        "zero-diagnostics",
        "edge-binding-witness",
    ),
)
def test_retained_output_forgery_is_invalid_and_quarantined(mutation):
    class ForgingEngine(ExactResistiveDCEngine):
        def solve(self, subject):
            analysis = super().solve(subject)
            return _analysis_mutation(analysis, mutation)

    subject = _subject()
    engine = ForgingEngine()
    plan = compile_resistive_dc("bridge", subject, engine)
    approved = approve(
        plan,
        record_approval(plan, "test", f"reject {mutation}"),
    )
    report = execute(approved, engine)
    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert report.certificate is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)


def test_presentation_digest_mutated_during_engine_call_is_invalid():
    class BindingMutatingEngine(ExactResistiveDCEngine):
        def solve(self, subject):
            analysis = super().solve(subject)
            object.__setattr__(subject.model, "presentation_digest", "0" * 64)
            return analysis

    subject = _subject()
    engine = BindingMutatingEngine()
    plan = compile_resistive_dc("bridge", subject, engine)
    approved = approve(
        plan,
        record_approval(plan, "test", "reject mutated presentation binding"),
    )
    report = execute(approved, engine)
    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert report.certificate is None
    assert any(
        "execution identity changed" in failure
        for failure in report.record.failures
    )


def test_common_mode_production_forgery_is_invalid_and_quarantined(monkeypatch):
    """A coherent wrong-drive analysis plus wrong relation defeats repeated production.

    The old remote postcondition called the same production analysis again and would have
    accepted a shared defect.  This gate patches the production analysis itself while
    leaving the direct verifier's implementation untouched.
    """
    approved_subject = _subject()
    wrong_experiment = DCSolveSpec(
        _out(),
        DCVoltageDrive(_in(), _out(), circuit.Rational(11)),
    )
    wrong_subject = replace(approved_subject, experiment=wrong_experiment)
    forged = replace(
        analyze_resistive_dc(wrong_subject),
        boundary_relation=BoundaryLinearRelation.identity(1),
    )
    original_verifier = verifier.verify_resistive_dc_analysis
    verifier_calls = 0

    def observed_verifier(subject, candidate):
        nonlocal verifier_calls
        verifier_calls += 1
        return original_verifier(subject, candidate)

    monkeypatch.setattr(
        resistive_dc_module,
        "analyze_resistive_dc",
        lambda _subject: forged,
    )
    monkeypatch.setattr(
        resistive_dc_module,
        "verify_resistive_dc_analysis",
        observed_verifier,
    )
    engine = ExactResistiveDCEngine()
    plan = compile_resistive_dc("bridge", approved_subject, engine)
    approved = approve(
        plan,
        record_approval(plan, "test", "forced common-mode verifier gate"),
    )
    report = execute(approved, engine)

    assert verifier_calls == 1
    assert engine.calls == 1
    assert report.record.status is RunStatus.INVALID
    assert report.result is None
    assert report.certificate is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert not any(
        item.kind == "observable" and not item.quarantined
        for item in report.record.artifacts
    )
