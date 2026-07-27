"""Source-to-certificate acceptance tests for the finite exact C3 control."""
from __future__ import annotations

from dataclasses import fields, replace

import pytest

import smartchem
import smartchem.ising_lattice_gas as ising_module
import smartchem.runtime_registry as runtime_registry
from smartchem.contracts import (
    ClaimKind,
    EvidenceStatus,
    InferenceKind,
    ObligationOutcome,
    ObligationResult,
    RunStatus,
)
from smartchem.ising_lattice_gas import (
    ISING_LATTICE_GAS_CASUALTIES,
    ISING_LATTICE_GAS_OMISSIONS,
    ExactC3EquilibriumEngine,
    compile_ising_lattice_gas_equilibrium,
    compile_session_ising_lattice_gas_equilibrium,
    ising_lattice_gas_slot,
)
from smartchem.ising_lattice_gas_domain import (
    ExactEquilibriumMap,
    IsingLatticeGasSpec,
    MicrostateMap,
    derive_exact_equilibrium_map,
)
from smartchem.ledger import COMPILED, STALLED, Spec, shepherd
from smartchem.program import RuntimeLimits, approve, execute, record_approval


EXECUTOR_ID = "smartchem.ising_lattice_gas/finite-c3-equilibrium-map-v1"
SPEC = IsingLatticeGasSpec(coupling_j_ticks=2, field_h_ticks=1)
OUTPUT_IDS = (
    "ising_lattice_gas_state_map",
    "ising_lattice_gas_partition_identity",
    "ising_lattice_gas_completeness_inventory",
)


def _approved(plan):
    return approve(
        plan,
        record_approval(plan, "scientist", "exact finite C3 equilibrium map only"),
    )


def test_public_exports_and_closed_registry_descriptor_are_exact():
    assert {
        "IsingLatticeGasSpec",
        "ExactC3EquilibriumEngine",
        "compile_ising_lattice_gas_equilibrium",
        "compile_session_ising_lattice_gas_equilibrium",
        "ising_lattice_gas_slot",
    }.issubset(smartchem.__all__)
    descriptor = runtime_registry.descriptor_for(EXECUTOR_ID)
    assert descriptor.subject_type.resolve() is IsingLatticeGasSpec
    assert descriptor.runner.resolve() is ising_module._execute_ising_lattice_gas
    assert EXECUTOR_ID in runtime_registry.executor_ids()


def test_typed_shepherd_is_required_and_complete_execution_retains_all_outputs():
    source = "Map the exact finite C3 Ising equilibrium model to its lattice gas."
    starting = Spec("finite-c3-map", (ising_lattice_gas_slot("map", source),))
    stalled = shepherd(starting, lambda current, _holes: current)
    assert stalled.outcome == STALLED
    with pytest.raises(ValueError, match="outright closed COMPILED"):
        compile_session_ising_lattice_gas_equilibrium(
            source, stalled, "map", ExactC3EquilibriumEngine()
        )

    session = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            "map",
            SPEC,
            source_text=source,
            inference=InferenceKind.QUESTION_CONFIRMED,
        ),
        discarded=ISING_LATTICE_GAS_CASUALTIES,
    )
    assert session.outcome == COMPILED
    engine = ExactC3EquilibriumEngine()
    report = execute(
        _approved(
            compile_session_ising_lattice_gas_equilibrium(source, session, "map", engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.COMPLETE
    assert engine.calls == 1
    assert report.result is not None and report.certificate is not None
    assert report.certificate.claim_scope.kind is ClaimKind.ANALOGUE
    assert report.certificate.evidence_status is EvidenceStatus.ESTABLISHED
    assert report.certificate.casualties == ISING_LATTICE_GAS_CASUALTIES
    assert report.certificate.omissions == ISING_LATTICE_GAS_OMISSIONS
    assert report.certificate.output_inventory == OUTPUT_IDS
    assert tuple(value.observable_id for value in report.result.values) == OUTPUT_IDS
    state_map = report.result.values[0].payload
    assert tuple(item.state_id for item in state_map.states) == (
        "000", "001", "010", "011", "100", "101", "110", "111"
    )
    assert state_map.completeness.output_reduction_applied is False
    assert tuple(item.degeneracy for item in state_map.classes) == (1, 3, 3, 1)
    assert any("complete eight-state" in item for item in report.record.cache_state)


def test_contract_reduction_is_a_blocker_before_any_engine_call():
    engine = ExactC3EquilibriumEngine()
    baseline = compile_ising_lattice_gas_equilibrium("map", SPEC, engine)
    reduced_contract = replace(
        baseline.request.output_contract,
        observables=baseline.request.output_contract.observables[1:],
    )
    altered = compile_ising_lattice_gas_equilibrium(
        "map", SPEC, engine, output_contract=reduced_contract
    )

    assert any("exact default output contract" in item for item in altered.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(altered)
    assert engine.calls == 0


def test_zero_engine_cap_is_incomplete_without_a_calculation():
    engine = ExactC3EquilibriumEngine()
    plan = compile_ising_lattice_gas_equilibrium(
        "map", SPEC, engine, limits=RuntimeLimits(max_engine_calls=0)
    )

    report = execute(_approved(plan), engine)

    assert report.record.status is RunStatus.INCOMPLETE
    assert report.result is None and report.certificate is None
    assert engine.calls == 0
    assert "engine-call cap reached" in report.record.failures[-1]


def test_forged_but_well_formed_diagnostic_is_invalid_and_quarantined():
    class ForgingEngine(ExactC3EquilibriumEngine):
        def solve(self, _spec):
            self.calls += 1
            return derive_exact_equilibrium_map(IsingLatticeGasSpec(2, 2))

    engine = ForgingEngine()
    report = execute(
        _approved(compile_ising_lattice_gas_equilibrium("map", SPEC, engine)), engine
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert engine.calls == 1
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert all(item.quarantined for item in report.record.artifacts)


def test_constructor_bypass_forgery_is_still_caught_by_final_payload_validator(
    monkeypatch,
):
    class ConstructorBypassEngine(ExactC3EquilibriumEngine):
        def solve(self, spec):
            self.calls += 1
            genuine = derive_exact_equilibrium_map(spec)
            forged_row = object.__new__(MicrostateMap)
            for field in fields(MicrostateMap):
                object.__setattr__(
                    forged_row,
                    field.name,
                    getattr(genuine.states[0], field.name),
                )
            object.__setattr__(forged_row, "ising_energy_ticks", 999)
            object.__setattr__(forged_row, "lattice_energy_ticks", 1002)
            object.__setattr__(
                forged_row,
                "ising_boltzmann_exponent_ticks",
                -999,
            )
            object.__setattr__(
                forged_row,
                "lattice_boltzmann_exponent_ticks",
                -1002,
            )
            forged = object.__new__(ExactEquilibriumMap)
            for field in fields(ExactEquilibriumMap):
                object.__setattr__(
                    forged,
                    field.name,
                    getattr(genuine, field.name),
                )
            object.__setattr__(
                forged,
                "states",
                (forged_row, *genuine.states[1:]),
            )
            return forged

    # Prove the final RunJournal payload validator is an independent backstop even if
    # executor-specific postcondition evaluators were themselves defective.
    monkeypatch.setattr(
        ising_module,
        "_post_result",
        lambda obligation, *_args: ObligationResult(
            obligation.digest,
            ObligationOutcome.PASS,
            "test-only forced postcondition pass",
        ),
    )
    engine = ConstructorBypassEngine()
    report = execute(
        _approved(compile_ising_lattice_gas_equilibrium("map", SPEC, engine)),
        engine,
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert engine.calls == 1
    assert "state row 0 differs from direct Hamiltonian evaluation" in (
        report.record.failures[-1]
    )
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert all(item.quarantined for item in report.record.artifacts)


def test_runtime_owned_model_replacement_is_refused_before_engine_execution():
    engine = ExactC3EquilibriumEngine()
    approved = _approved(compile_ising_lattice_gas_equilibrium("map", SPEC, engine))
    object.__setattr__(approved.plan, "model", replace(approved.plan.model, version="forged"))
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(approved, "approval_record_digest", approved.approval.digest)

    with pytest.raises(ValueError, match="exact runtime-owned model"):
        execute(approved, engine)

    assert engine.calls == 0
