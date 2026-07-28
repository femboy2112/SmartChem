"""Independent-verifier controls for the finite positive-frequency RLC vertical."""

from __future__ import annotations

import ast
from dataclasses import fields, make_dataclass, replace
import inspect

import pytest

import smartchem.rlc_ac as production
import smartchem.rlc_ac_circuit as circuit
import smartchem.rlc_ac_verifier as verifier
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
from smartchem.rlc_ac_schema import (
    ACSolveSpec,
    ACVoltageDrive,
    ComplexBoundaryRelation,
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
from smartchem.rlc_ac_verifier import (
    DirectACVerificationDecision,
    direct_preflight,
    verify_rlc_ac_analysis,
)


ELECTRICAL = PortKind.ELECTRICAL
ONE = Interface((ELECTRICAL,))


def _in() -> BoundaryRef:
    return BoundaryRef(BoundarySide.INPUT, 0)


def _out() -> BoundaryRef:
    return BoundaryRef(BoundarySide.OUTPUT, 0)


def _parallel(names: tuple[str, ...]) -> OpenDiagram:
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(
            ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names
        ),
        (
            Junction(
                "positive",
                ELECTRICAL,
                (_in(), *(ElementPortRef(name, "a") for name in names)),
            ),
            Junction(
                "negative",
                ELECTRICAL,
                (_out(), *(ElementPortRef(name, "b") for name in names)),
            ),
        ),
    )


def _series(names: tuple[str, ...]) -> OpenDiagram:
    junctions: list[Junction] = [
        Junction("positive", ELECTRICAL, (_in(), ElementPortRef(names[0], "a")))
    ]
    junctions.extend(
        Junction(
            f"middle-{left}",
            ELECTRICAL,
            (ElementPortRef(left, "b"), ElementPortRef(right, "a")),
        )
        for left, right in zip(names, names[1:])
    )
    junctions.append(
        Junction("negative", ELECTRICAL, (ElementPortRef(names[-1], "b"), _out()))
    )
    return OpenDiagram.build(
        ONE,
        ONE,
        tuple(
            ComponentSlot(name, ComponentKind.ELECTRICAL_TWO_TERMINAL) for name in names
        ),
        tuple(junctions),
    )


def _component(kind: ElementKind, value: int = 1) -> RLCComponent:
    exact = Rational(value)
    if kind is ElementKind.RESISTOR:
        return RLCComponent(kind, PositiveResistance(exact))
    if kind is ElementKind.INDUCTOR:
        return RLCComponent(kind, PositiveInductance(exact))
    return RLCComponent(kind, PositiveCapacitance(exact))


def _subject() -> RLCACSubject:
    diagram = _parallel(("r", "l", "c"))
    return RLCACSubject(
        diagram,
        RLCModel.for_diagram(
            diagram,
            (
                _component(ElementKind.RESISTOR, 10),
                _component(ElementKind.INDUCTOR, 2),
                _component(ElementKind.CAPACITOR),
            ),
        ),
        ACSolveSpec(
            _out(),
            ACVoltageDrive(_in(), _out(), GaussianComplex.from_parts(10)),
            PositiveAngularFrequency(Rational(1)),
        ),
        100_000,
    )


def _analysis(subject: RLCACSubject | None = None):
    return production.analyze_rlc_ac(subject or _subject())


def _mutate(analysis, family: str):
    solution = analysis.sparse_solution
    if family == "canonical":
        return replace(
            analysis,
            decorated_model_canonical_form=analysis.structural_canonical_form,
        )
    if family == "relation":
        return replace(
            analysis, boundary_relation=ComplexBoundaryRelation.from_equations(1, 1, ())
        )
    if family == "binding":
        return replace(analysis, model_edge_bindings=analysis.model_edge_bindings[:-1])
    if family == "node":
        node = replace(
            solution.nodes[0],
            volts_rms=replace(solution.nodes[0].volts_rms, real=9.0),
        )
        return replace(
            analysis,
            sparse_solution=replace(solution, nodes=(node,) + solution.nodes[1:]),
        )
    if family == "branch":
        branch = replace(
            solution.branches[0],
            current_amperes_rms=replace(
                solution.branches[0].current_amperes_rms,
                real=solution.branches[0].current_amperes_rms.real + 1.0,
            ),
        )
        return replace(
            analysis,
            sparse_solution=replace(
                solution, branches=(branch,) + solution.branches[1:]
            ),
        )
    if family == "source":
        source = replace(
            solution.source,
            current_entering_positive_amperes_rms=replace(
                solution.source.current_entering_positive_amperes_rms,
                real=-solution.source.current_entering_positive_amperes_rms.real,
            ),
        )
        return replace(analysis, sparse_solution=replace(solution, source=source))
    if family == "mna":
        state = replace(
            solution.mna_state,
            normalized_impedance_ohms=solution.mna_state.normalized_impedance_ohms * 2,
        )
        return replace(analysis, sparse_solution=replace(solution, mna_state=state))
    if family == "diagnostics":
        diagnostics = replace(solution.diagnostics, condition_number=1.0)
        return replace(
            analysis, sparse_solution=replace(solution, diagnostics=diagnostics)
        )
    raise AssertionError(family)


def _spoof(value):
    genuine = type(value)
    spoof_type = make_dataclass(
        genuine.__name__,
        tuple((field.name, field.type) for field in fields(value)),
        frozen=True,
        namespace={"__module__": genuine.__module__},
    )
    return spoof_type(*(getattr(value, field.name) for field in fields(value)))


def test_verifier_source_has_no_production_ac_dependency():
    tree = ast.parse(inspect.getsource(verifier))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert "rlc_ac" not in imported
    assert "rlc_ac_circuit" not in imported
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert (
        not {
            "analyze_rlc_ac",
            "solve_rlc_ac",
            "blackbox_rlc_ac",
            "admittance_exact",
            "canonicalize",
        }
        & called
    )


def test_direct_verifier_accepts_when_every_production_entrypoint_is_disabled(
    monkeypatch,
):
    subject = _subject()
    analysis = _analysis(subject)

    def disabled(*_args, **_kwargs):
        raise AssertionError(
            "production AC path must not be invoked by direct verification"
        )

    monkeypatch.setattr(production, "analyze_rlc_ac", disabled)
    monkeypatch.setattr(circuit, "solve_rlc_ac", disabled)
    monkeypatch.setattr(circuit, "blackbox_rlc_ac", disabled)

    report = verify_rlc_ac_analysis(subject, analysis)

    assert report.passed, report.reasons


@pytest.mark.parametrize(
    "family",
    (
        "canonical",
        "relation",
        "binding",
        "node",
        "branch",
        "source",
        "mna",
        "diagnostics",
    ),
)
def test_direct_verifier_rejects_each_retained_output_family(family):
    subject = _subject()
    report = verify_rlc_ac_analysis(subject, _mutate(_analysis(subject), family))
    assert report.decision is DirectACVerificationDecision.FAIL
    assert not report.passed


def test_direct_preflight_refuses_exact_lossless_series_resonance():
    diagram = _series(("l", "c"))
    subject = RLCACSubject(
        diagram,
        RLCModel.for_diagram(
            diagram,
            (_component(ElementKind.INDUCTOR), _component(ElementKind.CAPACITOR)),
        ),
        ACSolveSpec(
            _out(),
            ACVoltageDrive(_in(), _out(), GaussianComplex.from_parts(1)),
            PositiveAngularFrequency(Rational(1)),
        ),
        100_000,
    )

    report = direct_preflight(subject)

    assert report.decision is DirectACVerificationDecision.REFUSE
    assert any("rank deficient" in reason for reason in report.reasons)


def test_direct_verifier_rejects_nominally_spoofed_nested_result():
    subject = _subject()
    analysis = _analysis(subject)
    object.__setattr__(analysis, "sparse_solution", _spoof(analysis.sparse_solution))

    report = verify_rlc_ac_analysis(subject, analysis)

    assert report.decision is DirectACVerificationDecision.FAIL
    assert any("ACSolveResult" in reason for reason in report.reasons)


def test_direct_report_records_are_themselves_nominal():
    valid = verify_rlc_ac_analysis(_subject(), _analysis())
    with pytest.raises(TypeError, match="DirectACVerificationDecision"):
        type(valid)(
            "pass",
            valid.canonical_forms_ok,
            valid.inventory_ok,
            valid.exact_relation_ok,
            valid.exact_mna_rank_ok,
            valid.branch_law_ok,
            valid.kcl_ok,
            valid.source_constraint_ok,
            valid.power_ok,
            valid.passivity_ok,
            valid.diagnostics,
            valid.reasons,
        )
