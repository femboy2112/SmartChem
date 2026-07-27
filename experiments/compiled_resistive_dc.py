"""Run the approved finite ideal-resistor DC bridge control.

This is a deterministic mathematical-circuit control: one five-edge bridge with exact
positive rational resistances, an exact 10 V ideal source, an exact boundary relation,
and one independently checked sparse-MNA witness.  It is not a device, AC/RLC, safety,
or material claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from smartchem import (
    COMPILED,
    DCVoltageDrive,
    DCSolveSpec,
    ExactResistiveDCEngine,
    InferenceKind,
    OpenBoundaryRef,
    OpenBoundarySide,
    OpenComponentKind,
    OpenComponentSlot,
    OpenDiagram,
    OpenInterface,
    OpenJunction,
    OpenPortKind,
    PositiveResistance,
    Rational,
    ResistiveDCModel,
    ResistiveDCSubject,
    SourceProgram,
    Spec,
    approve,
    canonical_digest,
    compile_session_resistive_dc,
    execute,
    record_approval,
    resistive_dc_slot,
    shepherd,
)
from smartchem.open_diagram import ElementPortRef


ELECTRICAL = OpenPortKind.ELECTRICAL
ONE_PORT = OpenInterface((ELECTRICAL,))


def _input() -> OpenBoundaryRef:
    return OpenBoundaryRef(OpenBoundarySide.INPUT, 0)


def _output() -> OpenBoundaryRef:
    return OpenBoundaryRef(OpenBoundarySide.OUTPUT, 0)


def build_subject() -> ResistiveDCSubject:
    """The asymmetric P-L, L-N, P-R, R-N, L-R bridge with P=+10 V and N=0 V."""
    names = ("r0", "r1", "r2", "r3", "r4")
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
                (_input(), ElementPortRef("r0", "a"), ElementPortRef("r2", "a")),
            ),
            OpenJunction(
                "left",
                ELECTRICAL,
                (ElementPortRef("r0", "b"), ElementPortRef("r1", "a"), ElementPortRef("r4", "a")),
            ),
            OpenJunction(
                "right",
                ELECTRICAL,
                (ElementPortRef("r2", "b"), ElementPortRef("r3", "a"), ElementPortRef("r4", "b")),
            ),
            OpenJunction(
                "negative",
                ELECTRICAL,
                (_output(), ElementPortRef("r1", "b"), ElementPortRef("r3", "b")),
            ),
        ),
    )
    # The order is the declared structural-edge order: P-L, L-N, P-R, R-N, L-R.
    model = ResistiveDCModel.for_diagram(
        diagram,
        tuple(PositiveResistance(Rational(value)) for value in (100, 200, 300, 400, 500)),
    )
    experiment = DCSolveSpec(
        _output(),
        DCVoltageDrive(_input(), _output(), Rational(10)),
    )
    return ResistiveDCSubject(diagram, model, experiment, canonicalization_budget=100_000)


def compile_plan(engine: ExactResistiveDCEngine):
    source = SourceProgram(
        (
            "Run the scientist-confirmed finite ideal-resistor DC bridge control: "
            "P-L=100 ohm, L-N=200 ohm, P-R=300 ohm, R-N=400 ohm, and L-R=500 ohm. "
            "Set the input boundary to +10 V relative to the output reference. Retain "
            "the structural and resistance-decorated canonical forms, every exact "
            "boundary-relation row, every node/branch/source value, and all residual "
            "and passivity diagnostics. Do not infer a physical device, AC/RLC behavior, "
            "safety, material parameters, or a universal network theorem."
        ),
        (
            "asymmetric five-edge ideal-resistor bridge",
            "exact positive rational resistances",
            "input +10 V versus output reference",
            "exact boundary relation and sparse MNA",
            "complete node branch source diagnostics",
            "canonicalization budget 100000",
        ),
        "Leah",
    )
    subject = build_subject()
    starting = Spec(
        "compiled-resistive-dc-bridge-control",
        (
            resistive_dc_slot(
                "resistive-dc-bridge",
                "Confirm the bridge topology, edge-order resistance tuple, source polarity, "
                "reference boundary, canonicalization budget, and narrow ideal-mathematical scope.",
            ),
        ),
    )
    session = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            "resistive-dc-bridge",
            subject,
            source_text=(
                "Use exactly P-L=100, L-N=200, P-R=300, R-N=400, L-R=500 ohm in "
                "declaration order; input is +10 V versus output reference; retain exact "
                "relation, structural/decorated canonical forms, complete sparse witness, "
                "and all gates under canonicalization budget 100000."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        ),
        discarded=(
            "assembled-device or component-tolerance claim",
            "AC, transient, RLC, radiation, or resonance claim",
            "electrical safety or grounding-practice claim",
            "universal categorical or arbitrary-network theorem",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return compile_session_resistive_dc(
        source,
        session,
        "resistive-dc-bridge",
        engine,
    ), session


def run(journal: Path):
    engine = ExactResistiveDCEngine()
    plan, session = compile_plan(engine)
    approved = approve(
        plan,
        record_approval(
            plan,
            "Leah",
            (
                "run the complete finite ideal-resistor bridge control with the exact "
                "relation, canonical forms, full sparse-MNA witness, every residual, and "
                "all lifecycle records; retain the narrow ideal-mathematical scope"
            ),
        ),
    )
    return plan, session, engine, execute(approved, engine, journal_path=journal)


def _rational(value: Rational) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _canonical_form(form: object) -> dict[str, object]:
    return {
        "digest": canonical_digest(form),
        "input_nodes": list(form.input_nodes),
        "output_nodes": list(form.output_nodes),
        "node_kinds": [kind.value for kind in form.node_kinds],
        "edges": [list(edge) for edge in form.edges],
    }


def summary(results: object) -> dict[str, object]:
    plan, session, engine, report = results
    if report.result is None or report.certificate is None:
        return {
            "status": report.record.status.value,
            "engine_calls": engine.calls,
            "failures": list(report.record.failures),
            "run_id": report.record.run_id,
        }
    analysis = report.result.values[0].payload
    subject = plan.request.resolved.subject
    relation = analysis.boundary_relation
    solution = analysis.sparse_solution
    diagnostics = solution.diagnostics
    certificate = report.certificate
    return {
        "run_id": report.record.run_id,
        "status": report.record.status.value,
        "engine_calls": engine.calls,
        "claim_kind": certificate.claim_scope.kind.value,
        "claim_scope": certificate.claim_scope.referent,
        "evidence_status": certificate.evidence_status.value,
        "execution_lane": plan.execution_lane.value,
        "scientist_confirmed_session": session.outcome,
        "bridge": {
            "edge_order": ["P-L", "L-N", "P-R", "R-N", "L-R"],
            "resistances_ohm": [
                _rational(resistance.ohms)
                for resistance in subject.model.resistances
            ],
            "drive": {
                "positive_boundary": "input[0]",
                "negative_boundary": "output[0]",
                "reference_boundary": "output[0]",
                "volts": _rational(subject.experiment.drive.volts),
            },
            "canonicalization_budget": subject.canonicalization_budget,
        },
        "structural_canonical": _canonical_form(analysis.structural_canonical_form),
        "decorated_model_canonical": _canonical_form(analysis.decorated_model_canonical_form),
        "boundary_relation": {
            "variable_order": "V(input,output), I_inward(input,output)",
            "dom_ports": relation.dom_ports,
            "cod_ports": relation.cod_ports,
            "rref_rows": [
                [_rational(coefficient) for coefficient in row]
                for row in relation.rref_rows
            ],
            "digest": canonical_digest(relation),
        },
        "nodes": [
            {"node_index": node.node_index, "volts": node.volts}
            for node in solution.nodes
        ],
        "branches": [
            {
                "branch_index": branch.branch_index,
                "node_a": branch.node_a,
                "node_b": branch.node_b,
                "resistance_ohm": _rational(branch.resistance.ohms),
                "voltage_drop_volts": branch.voltage_drop_volts,
                "current_amperes": branch.current_amperes,
                "absorbed_power_watts": branch.absorbed_power_watts,
            }
            for branch in solution.branches
        ],
        "source": {
            "positive_node": solution.source.positive_node,
            "negative_node": solution.source.negative_node,
            "volts": solution.source.volts,
            "current_entering_positive_amperes": solution.source.current_entering_positive_amperes,
            "absorbed_power_watts": solution.source.absorbed_power_watts,
        },
        "diagnostics": {
            "raw": {
                "kcl_residual_amperes": diagnostics.kcl_residual_amperes,
                "constraint_residual_volts": diagnostics.constraint_residual_volts,
                "power_residual_watts": diagnostics.power_residual_watts,
                "relation_residual": diagnostics.relation_residual,
            },
            "scaled": {
                "kcl": diagnostics.scaled_kcl_residual,
                "constraint": diagnostics.scaled_constraint_residual,
                "power": diagnostics.scaled_power_residual,
                "relation": diagnostics.scaled_relation_residual,
            },
        },
        "output_inventory": list(certificate.output_inventory),
        "obligation_outcomes": [
            {
                "obligation_digest": result.obligation_digest,
                "outcome": result.outcome.value,
                "detail": result.detail,
            }
            for result in certificate.validity_results
        ],
        "lifecycle_digests": {
            "source": plan.request.source.digest,
            "shepherd_session": canonical_digest(session),
            "resolved": plan.request.resolved.digest,
            "physical_ir": plan.request.physical_ir.digest,
            "request": plan.request.digest,
            "output_contract": plan.request.output_contract.digest,
            "subject": plan.request.resolved.subject.digest,
            "model": canonical_digest(plan.request.resolved.subject.model),
            "experiment": canonical_digest(plan.request.resolved.subject.experiment),
            "plan": plan.digest,
            "approval": certificate.approval_digest,
            "calculation": certificate.calculation_digest,
            "compiler_implementation": certificate.compiler_implementation_digest,
            "analysis": analysis.digest,
            "certificate": certificate.digest,
        },
        "limitations": {
            "casualties": list(certificate.casualties),
            "omissions": list(certificate.omissions),
        },
        "failures": list(report.record.failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summary(run(args.journal)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
