"""Run the approved finite positive-frequency passive-RLC E2 controls.

The primary calculation is a damped parallel RLC network at exact resonance.  The
resistor dissipates real power while the ideal inductor and capacitor currents cancel.
A second, separately approved calculation is the exact undamped series-LC singular
control; it must end REFUSED without an engine call or regularization.

These are deterministic ideal mathematical-circuit controls, not device, transient,
safety, distributed-field, transfer-function, or port-Hamiltonian claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from smartchem import (
    COMPILED,
    ACSolveSpec,
    ACVoltageDrive,
    ExactRLCACEngine,
    GaussianComplex,
    InferenceKind,
    OpenBoundaryRef,
    OpenBoundarySide,
    OpenComponentKind,
    OpenComponentSlot,
    OpenDiagram,
    OpenInterface,
    OpenJunction,
    OpenPortKind,
    PositiveAngularFrequency,
    PositiveCapacitance,
    PositiveInductance,
    RLCACSubject,
    RLCEdgeBinding,
    RLCElementKind,
    RLCModel,
    RLCPositiveResistance,
    RLCComponent,
    Rational,
    SourceProgram,
    Spec,
    approve,
    canonical_digest,
    compile_session_rlc_ac,
    execute,
    record_approval,
    rlc_ac_slot,
    shepherd,
)
from smartchem.open_diagram import ElementPortRef
from smartchem.runtime_registry import semantic_manifest_digest


ELECTRICAL = OpenPortKind.ELECTRICAL
ONE_PORT = OpenInterface((ELECTRICAL,))


def _input() -> OpenBoundaryRef:
    return OpenBoundaryRef(OpenBoundarySide.INPUT, 0)


def _output() -> OpenBoundaryRef:
    return OpenBoundaryRef(OpenBoundarySide.OUTPUT, 0)


def _component(kind: RLCElementKind) -> RLCComponent:
    if kind is RLCElementKind.RESISTOR:
        return RLCComponent(kind, RLCPositiveResistance(Rational(1)))
    if kind is RLCElementKind.INDUCTOR:
        return RLCComponent(kind, PositiveInductance(Rational(1)))
    return RLCComponent(kind, PositiveCapacitance(Rational(1)))


def build_damped_subject() -> RLCACSubject:
    """Parallel R=L=C=1 at omega=1, with a nonidentity model-edge witness."""
    names = ("r", "l", "c")
    diagram = OpenDiagram.build(
        ONE_PORT,
        ONE_PORT,
        tuple(
            OpenComponentSlot(name, OpenComponentKind.ELECTRICAL_TWO_TERMINAL)
            for name in names
        ),
        (
            OpenJunction(
                "positive",
                ELECTRICAL,
                (
                    _input(),
                    *(ElementPortRef(name, "a") for name in names),
                ),
            ),
            OpenJunction(
                "negative",
                ELECTRICAL,
                (
                    _output(),
                    *(ElementPortRef(name, "b") for name in names),
                ),
            ),
        ),
    )
    # Model order is C, R, L while structural order is R, L, C.
    model = RLCModel.for_diagram(
        diagram,
        (
            _component(RLCElementKind.CAPACITOR),
            _component(RLCElementKind.RESISTOR),
            _component(RLCElementKind.INDUCTOR),
        ),
        edge_bindings=(
            RLCEdgeBinding(0, 2),
            RLCEdgeBinding(1, 0),
            RLCEdgeBinding(2, 1),
        ),
    )
    experiment = ACSolveSpec(
        _output(),
        ACVoltageDrive(
            _input(),
            _output(),
            GaussianComplex.from_parts(1),
        ),
        PositiveAngularFrequency(Rational(1)),
    )
    return RLCACSubject(diagram, model, experiment, canonicalization_budget=100_000)


def build_singular_subject() -> RLCACSubject:
    """Series L=C=1 at omega=1: exact undamped singular resonance."""
    diagram = OpenDiagram.build(
        ONE_PORT,
        ONE_PORT,
        (
            OpenComponentSlot("l", OpenComponentKind.ELECTRICAL_TWO_TERMINAL),
            OpenComponentSlot("c", OpenComponentKind.ELECTRICAL_TWO_TERMINAL),
        ),
        (
            OpenJunction(
                "positive",
                ELECTRICAL,
                (_input(), ElementPortRef("l", "a")),
            ),
            OpenJunction(
                "middle",
                ELECTRICAL,
                (ElementPortRef("l", "b"), ElementPortRef("c", "a")),
            ),
            OpenJunction(
                "negative",
                ELECTRICAL,
                (ElementPortRef("c", "b"), _output()),
            ),
        ),
    )
    model = RLCModel.for_diagram(
        diagram,
        (
            _component(RLCElementKind.INDUCTOR),
            _component(RLCElementKind.CAPACITOR),
        ),
    )
    experiment = ACSolveSpec(
        _output(),
        ACVoltageDrive(
            _input(),
            _output(),
            GaussianComplex.from_parts(1),
        ),
        PositiveAngularFrequency(Rational(1)),
    )
    return RLCACSubject(diagram, model, experiment, canonicalization_budget=100_000)


def compile_plan(
    subject: RLCACSubject,
    engine: ExactRLCACEngine,
    *,
    slot_name: str,
    purpose: str,
):
    source = SourceProgram(
        (
            f"Run the scientist-confirmed finite passive-RLC E2 {purpose}. "
            "Use RMS phasors with exp(j omega t), exact positive R/L/C values and "
            "omega, one ideal voltage source, and one reference. Retain the exact "
            "Q(i) boundary relation, structural/decorated canonical forms, complete "
            "complex-MNA state, every node/branch/source phasor and complex power, "
            "all diagnostics, and the production-independent verifier report. Do "
            "not infer a device, transient, safety, transfer-function, distributed, "
            "or port-Hamiltonian claim."
        ),
        (
            purpose,
            "RMS exp(j omega t) phasor convention",
            "exact positive omega=1 rad/s",
            "complete exact relation and sparse-MNA witness or explicit refusal",
            "canonicalization budget 100000",
        ),
        "Leah",
    )
    starting = Spec(
        f"compiled-rlc-ac-{slot_name}",
        (
            rlc_ac_slot(
                slot_name,
                (
                    "Confirm the exact topology, model-edge binding, R/L/C values, "
                    "omega, RMS source polarity, reference, output inventory, and "
                    "narrow ideal-mathematical scope."
                ),
            ),
        ),
    )
    session = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            slot_name,
            subject,
            source_text=(
                f"Use exactly the {purpose}; omega=1 rad/s and 1+0j RMS volts; "
                "retain all declared E2 outputs under canonicalization budget 100000."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        ),
        discarded=(
            "assembled-device, tolerance, thermal, noise, or safety claim",
            "transient, nonlinear, active, distributed, or multi-frequency claim",
            "general positive-real transfer-function theorem",
            "port-Hamiltonian or dynamic-state semantics",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return (
        compile_session_rlc_ac(source, session, slot_name, engine),
        session,
    )


def _approved(plan, detail: str):
    return approve(
        plan,
        record_approval(
            plan,
            "Leah",
            detail,
        ),
    )


def run(journal: Path):
    damped_engine = ExactRLCACEngine()
    damped_plan, damped_session = compile_plan(
        build_damped_subject(),
        damped_engine,
        slot_name="damped-parallel-rlc",
        purpose="parallel R=L=C=1 damped resonance control",
    )
    damped = execute(
        _approved(
            damped_plan,
            (
                "run the complete damped parallel-RLC resonance control and retain "
                "the exact relation, all phasors/powers/MNA state, diagnostics, "
                "direct verifier, lifecycle artifacts, and narrow scope"
            ),
        ),
        damped_engine,
        journal_path=journal,
    )

    singular_engine = ExactRLCACEngine()
    singular_plan, singular_session = compile_plan(
        build_singular_subject(),
        singular_engine,
        slot_name="lossless-series-lc",
        purpose="series L=C=1 exact undamped singular-resonance refusal control",
    )
    singular_journal = journal.with_name(
        f"{journal.stem}.singular-refusal{journal.suffix or '.json'}"
    )
    singular = execute(
        _approved(
            singular_plan,
            (
                "attempt the exact lossless series-LC resonance only through the "
                "approved E2 refusal path; do not regularize or emit a smaller result"
            ),
        ),
        singular_engine,
        journal_path=singular_journal,
    )
    return (
        damped_plan,
        damped_session,
        damped_engine,
        damped,
        singular_plan,
        singular_session,
        singular_engine,
        singular,
        singular_journal,
    )


def _phasor(value) -> dict[str, float]:
    return {"real": value.real, "imag": value.imag}


def summary(results: object) -> dict[str, object]:
    (
        damped_plan,
        damped_session,
        damped_engine,
        damped,
        singular_plan,
        singular_session,
        singular_engine,
        singular,
        singular_journal,
    ) = results
    payloads = (
        {}
        if damped.result is None
        else {value.observable_id: value.payload for value in damped.result.values}
    )
    analysis = payloads.get("rlc_ac_analysis")
    verification = payloads.get("rlc_ac_direct_verification")
    branches = () if analysis is None else analysis.sparse_solution.branches
    source = None if analysis is None else analysis.sparse_solution.source
    return {
        "calculations": {
            "damped_parallel_rlc": {
                "status": damped.record.status.value,
                "run_id": damped.record.run_id,
                "engine_calls": damped_engine.calls,
                "scientist_confirmed_session": damped_session.outcome,
                "plan_digest": damped_plan.digest,
                "calculation_digest": damped_plan.calculation.digest,
                "certificate_digest": (
                    None if damped.certificate is None else damped.certificate.digest
                ),
            },
            "lossless_series_lc": {
                "status": singular.record.status.value,
                "run_id": singular.record.run_id,
                "engine_calls": singular_engine.calls,
                "scientist_confirmed_session": singular_session.outcome,
                "plan_digest": singular_plan.digest,
                "calculation_digest": singular_plan.calculation.digest,
                "journal": str(singular_journal),
                "failures": list(singular.record.failures),
            },
        },
        "scope": {
            "claim_kind": (
                None
                if damped.certificate is None
                else damped.certificate.claim_scope.kind.value
            ),
            "evidence_status": (
                None
                if damped.certificate is None
                else damped.certificate.evidence_status.value
            ),
            "execution_lane": damped_plan.execution_lane.value,
            "omega_radians_per_second": 1,
            "phasor_convention": "RMS exp(j omega t)",
        },
        "damped_resonance": {
            "model_to_structural_edge_bindings": [
                {
                    "model_index": item.model_index,
                    "structural_edge_index": item.structural_edge_index,
                }
                for item in damped_plan.request.resolved.subject.model.edge_bindings
            ],
            "branches": [
                {
                    "kind": branch.component.kind.value,
                    "current_amperes_rms": _phasor(branch.current_amperes_rms),
                    "absorbed_power_va": _phasor(branch.absorbed_power_va),
                }
                for branch in branches
            ],
            "source": (
                None
                if source is None
                else {
                    "current_entering_positive_amperes_rms": _phasor(
                        source.current_entering_positive_amperes_rms
                    ),
                    "absorbed_power_va": _phasor(source.absorbed_power_va),
                }
            ),
            "direct_verification": (
                None
                if verification is None
                else {
                    "decision": verification.decision.value,
                    "exact_relation_ok": verification.exact_relation_ok,
                    "exact_mna_rank_ok": verification.exact_mna_rank_ok,
                    "branch_law_ok": verification.branch_law_ok,
                    "kcl_ok": verification.kcl_ok,
                    "source_constraint_ok": verification.source_constraint_ok,
                    "power_ok": verification.power_ok,
                    "passivity_ok": verification.passivity_ok,
                    "diagnostics": {
                        "condition_number": verification.diagnostics.condition_number,
                        "scaled_kcl_residual": (
                            verification.diagnostics.scaled_kcl_residual
                        ),
                        "scaled_constraint_residual": (
                            verification.diagnostics.scaled_constraint_residual
                        ),
                        "scaled_power_residual": (
                            verification.diagnostics.scaled_power_residual
                        ),
                        "scaled_relation_residual": (
                            verification.diagnostics.scaled_relation_residual
                        ),
                        "mna_backward_residual": (
                            verification.diagnostics.mna_backward_residual
                        ),
                    },
                }
            ),
        },
        "output_inventory": (
            []
            if damped.certificate is None
            else list(damped.certificate.output_inventory)
        ),
        "identities": {
            "runtime_registry": semantic_manifest_digest(),
            "compiler": damped_plan.compiler_implementation_digest,
            "subject": damped_plan.request.resolved.subject.digest,
            "analysis": (None if analysis is None else canonical_digest(analysis)),
        },
        "boundary": (
            "LITERAL/VALIDATED_WITHIN_REGIME/CERTIFIED only for the declared finite "
            "positive-frequency ideal R/L/C mathematical circuits. The completed "
            "control is not a device, transient model, general AC simulator, "
            "positive-real transfer-function theorem, safety result, distributed "
            "field model, or port-Hamiltonian semantics."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.journal)
    report = summary(result)
    print(json.dumps(report, indent=2, sort_keys=True))
    statuses = report["calculations"]
    return (
        0
        if (
            statuses["damped_parallel_rlc"]["status"] == "COMPLETE"
            and statuses["lossless_series_lc"]["status"] == "REFUSED"
            and statuses["damped_parallel_rlc"]["engine_calls"] == 1
            and statuses["lossless_series_lc"]["engine_calls"] == 0
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
