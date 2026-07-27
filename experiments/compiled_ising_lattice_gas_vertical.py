"""Run the exact finite C3 Ising-to-lattice-gas cross-domain vertical.

The scientist confirms the graph and integer energy parameters through a typed shepherd
session.  The executor retains all eight mapped microstates and proves the formal
partition-function identity without evaluating beta numerically.  This is an exact finite
algebraic analogue, not a material simulation, dynamics result, or thermodynamic-limit
claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from smartchem import (
    COMPILED,
    ExactC3EquilibriumEngine,
    InferenceKind,
    IsingLatticeGasSpec,
    SourceProgram,
    Spec,
    approve,
    compile_session_ising_lattice_gas_equilibrium,
    execute,
    ising_lattice_gas_slot,
    record_approval,
    shepherd,
)


def compile_plan(engine: ExactC3EquilibriumEngine):
    source = SourceProgram(
        (
            "Treat the three-site Ising equilibrium model as a lattice gas. Use the "
            "scientist-confirmed undirected C3 graph with each edge counted once, "
            "J=2 and h=1 exact energy ticks. Retain all eight states, expose the "
            "constant energy shift and formal partition relation, and do not infer "
            "dynamics, materials, a thermodynamic limit, or literal particle identity."
        ),
        (
            "three-site Ising equilibrium model",
            "lattice gas",
            "each edge counted once",
            "J=2 and h=1 exact energy ticks",
            "retain all eight states",
            "formal partition relation",
        ),
        "Leah",
    )
    spec = IsingLatticeGasSpec(2, 1)
    starting = Spec(
        "finite-C3-Ising-lattice-gas-map",
        (
            ising_lattice_gas_slot(
                "finite-map",
                "Confirm graph, Hamiltonian convention, J, h, and output scope.",
            ),
        ),
    )
    session = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            "finite-map",
            spec,
            source_text=(
                "C3 means vertices (0,1,2) and undirected edges "
                "((0,1),(1,2),(0,2)), counted once; J=2, h=1 integer ticks; "
                "beta is formal; all eight states must be retained."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        ),
        discarded=(
            "literal material identity",
            "dynamics or kinetics",
            "thermodynamic limit",
            "arbitrary-graph transfer",
            "numerical beta evaluation",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return compile_session_ising_lattice_gas_equilibrium(
        source,
        session,
        "finite-map",
        engine,
    )


def run(journal: Path):
    engine = ExactC3EquilibriumEngine()
    plan = compile_plan(engine)
    approved = approve(
        plan,
        record_approval(
            plan,
            "Leah",
            (
                "run the exact finite C3 mapping with all eight states and the full "
                "formal partition/completeness outputs; no literal or scale transfer"
            ),
        ),
    )
    return plan, engine, execute(
        approved,
        engine,
        journal_path=journal,
    )


def summary(results: object) -> dict[str, object]:
    plan, engine, report = results
    if report.result is None or report.certificate is None:
        return {
            "status": report.record.status.value,
            "engine_calls": engine.calls,
            "failures": report.record.failures,
        }
    mapping = report.result.values[0].payload
    parameters = mapping.parameters
    return {
        "run_id": report.record.run_id,
        "status": report.record.status.value,
        "engine_calls": engine.calls,
        "claim_kind": report.certificate.claim_scope.kind.value,
        "evidence_status": report.certificate.evidence_status.value,
        "execution_lane": plan.execution_lane.value,
        "graph": {
            "vertices": mapping.spec.vertices,
            "undirected_edges_counted_once": mapping.spec.edges,
        },
        "source_parameters": {
            "J_ticks": parameters.coupling_j_ticks,
            "h_ticks": parameters.field_h_ticks,
        },
        "mapped_parameters": {
            "epsilon_ticks": parameters.attraction_epsilon_ticks,
            "mu_ticks": parameters.chemical_potential_mu_ticks,
            "C_ticks": parameters.constant_shift_c_ticks,
        },
        "state_ids": [item.state_id for item in mapping.states],
        "state_count": len(mapping.states),
        "state_rows": [
            {
                "state_id": item.state_id,
                "occupancies": item.occupancies,
                "spins": item.spins,
                "N": item.occupied_count,
                "Q": item.occupied_edge_count,
                "M": item.magnetization,
                "spin_edge_sum": item.spin_edge_sum,
                "H_Ising_ticks": item.ising_energy_ticks,
                "H_lattice_ticks": item.lattice_energy_ticks,
            }
            for item in mapping.states
        ],
        "class_degeneracies": [
            (item.occupied_count, item.degeneracy)
            for item in mapping.classes
        ],
        "lattice_partition_terms": [
            (item.degeneracy, item.exponent_ticks)
            for item in mapping.partition.lattice_terms
        ],
        "ising_partition_terms": [
            (item.degeneracy, item.exponent_ticks)
            for item in mapping.partition.ising_terms
        ],
        "statewise_relation": mapping.partition.statewise_relation,
        "partition_relation": mapping.partition.partition_relation,
        "output_reduction_applied": (
            mapping.completeness.output_reduction_applied
        ),
        "output_inventory": report.certificate.output_inventory,
        "obligation_outcomes": [
            item.outcome.value
            for item in report.certificate.validity_results
        ],
        "source_digest": plan.request.source.digest,
        "resolved_digest": plan.request.resolved.digest,
        "physical_ir_digest": plan.request.physical_ir.digest,
        "output_contract_digest": plan.request.output_contract.digest,
        "plan_digest": plan.digest,
        "approval_digest": report.certificate.approval_digest,
        "calculation_digest": report.certificate.calculation_digest,
        "compiler_implementation_digest": (
            report.certificate.compiler_implementation_digest
        ),
        "mapping_digest": mapping.digest,
        "partition_digest": mapping.partition.digest,
        "certificate_digest": report.certificate.digest,
        "scope": (
            "exact finite C3 algebraic analogue only; no floating beta, sampling, "
            "output reduction, material prediction, dynamics, or scale transfer"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summary(run(args.journal)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
