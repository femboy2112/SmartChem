"""Adversarial acceptance tests for the first typed program/runtime seam.

These are deliberately small and deterministic.  The contract layer must be testable
without making an expensive quantum-chemistry calculation: the real-backend smoke remains
separate, while these tests exercise authority, immutable identity, lifecycle persistence,
and output-completeness with a counting oracle.
"""
from __future__ import annotations

from dataclasses import replace
import json

import pytest

import smartchem.program as program_module
from smartchem.category import Config, Molecule, Reaction
from smartchem.contracts import (
    ClaimKind,
    DerivationRef,
    EvidenceStatus,
    ExecutionLane,
    InferenceKind,
    ObligationOutcome,
    ObligationResult,
    ObligationStage,
    RunStatus,
    ValidityObligation,
    canonical_digest,
)
from smartchem.oracle.base import BaseOracle, Estimate
from smartchem.oracle.heuristic import HeuristicOracle
from smartchem.ledger import (
    COMPILED,
    COMPILED_SUBJECT_TO,
    BindingSchema,
    Slot,
    Spec,
    reaction_slot,
    shepherd,
)
from smartchem.program import (
    Approval,
    ApprovedPlan,
    Artifact,
    AssemblyHypothesis,
    AssemblySpec,
    CalculationSpec,
    EquivalenceContract,
    ObservableRequest,
    OutputContract,
    RunJournal,
    RuntimeLimits,
    Transform,
    approve,
    compile_reaction_energy,
    compile_session_reaction_energy,
    execute,
    record_approval,
)


H = Molecule.atom("H")
H2 = Molecule.diatomic("H", "H")
H_FORMATION = Reaction(Config.of(H, H), Config.of(H2))


class MutableOracle(BaseOracle):
    """A deterministic, mutable oracle whose calculation identity is explicit."""

    name = "deterministic-test-oracle"
    nominal_accuracy_ev = 0.0

    def __init__(self, *, setting: str = "one", refuse: bool = False):
        self.setting = setting
        self.refuse = refuse
        self.calls: list[str] = []

    def calculation_spec(self):
        # ``calls`` is deliberately telemetry, not scientific calculation identity.
        return {"model": "deterministic-test-v1", "setting": self.setting}

    def energy(self, molecule):
        self.calls.append(repr(molecule))
        if self.refuse:
            return None
        return Estimate(
            value_ev=-4.0 if molecule.bonds else 0.0,
            uncertainty_ev=0.1,
            method=self.name,
            notes=f"setting={self.setting}",
        )


@pytest.fixture
def oracle() -> MutableOracle:
    return MutableOracle()


@pytest.fixture
def plan(oracle):
    return compile_reaction_energy("Compute the closed H + H -> H2 endpoint delta-E.",
                                   H_FORMATION, oracle)


def _approval(plan):
    return record_approval(plan, "test scientist", "Milestone A deterministic test")


def _approved(plan):
    return approve(plan, _approval(plan))


def _with_request(plan, request):
    """Rebuild only the candidate layer after changing one frozen request field."""
    return replace(plan, request=request)


def _changed_model_plan(plan):
    model = replace(plan.model, version="2")
    physical_ir = replace(plan.request.physical_ir, models=(model,))
    request = replace(plan.request, physical_ir=physical_ir)
    return replace(plan, request=request, model=model)


def _changed_output_contract(contract, *, precision=None, retention=None, extra=False):
    observables = contract.observables
    if precision is not None:
        observables = (replace(observables[0], precision=precision),)
    if extra:
        observables = observables + (
            ObservableRequest(
                observable_id="unimplemented_extra_observable",
                kind="adversarial output-completeness sentinel",
                unit="1",
                support="one requested sentinel",
                resolution="one scalar",
                precision="exact identity required",
                coverage="must be emitted or the run is not complete",
            ),
        )
    return OutputContract(
        observables=observables,
        diagnostics=contract.diagnostics,
        retention=contract.retention if retention is None else retention,
    )


def _typed_reaction_session():
    slot = replace(
        reaction_slot("reaction", "two H atoms make H2", (H, H2)),
        schema=BindingSchema((Reaction,)),
    )

    def select_derived(spec, holes):
        option = holes[0].derived_options[0]
        return spec.bind_typed(
            "reaction",
            option.value,
            source_text=option.display,
            inference=InferenceKind.DERIVED_COMPLETE,
            derivation=option.derivation,
        )

    return shepherd(Spec("typed-h2", (slot,)), select_derived)


def test_typed_shepherd_session_is_the_resolution_authority_for_the_vertical(oracle):
    session = _typed_reaction_session()

    plan = compile_session_reaction_energy(
        "Compute the typed H2 formation endpoint.",
        session,
        "reaction",
        oracle,
    )

    assert plan.request.resolved.shepherd_session_digest == canonical_digest(session)
    assert plan.request.resolved.reaction == H_FORMATION
    assert execute(_approved(plan), oracle).record.status is RunStatus.COMPLETE


def test_text_only_session_cannot_authorize_reaction_execution(oracle):
    session = shepherd(
        Spec("legacy", (Slot("reaction", "some reaction", binding="H + H -> H2"),)),
        lambda _spec, _holes: pytest.fail("closed spec must not ask"),
    )

    with pytest.raises(TypeError, match="no typed binding"):
        compile_session_reaction_energy("source", session, "reaction", oracle)


def test_compiled_subject_to_session_cannot_authorize_or_be_relabelled(oracle):
    post = ValidityObligation(
        "unmapped-post-check",
        ObligationStage.POST,
        "tests/unmapped-post-check",
        "must not disappear at the shepherd/runtime seam",
    )
    slot = replace(
        reaction_slot("reaction", "two H atoms make H2", (H, H2)),
        schema=BindingSchema((Reaction,)),
        obligations=(post,),
    )

    def select_derived(spec, holes):
        option = holes[0].derived_options[0]
        return spec.bind_typed(
            "reaction",
            option.value,
            source_text=option.display,
            inference=InferenceKind.DERIVED_COMPLETE,
            derivation=option.derivation,
        )

    session = shepherd(Spec("conditional-h2", (slot,)), select_derived)
    assert session.outcome == COMPILED_SUBJECT_TO
    with pytest.raises(ValueError, match="outright COMPILED"):
        compile_session_reaction_energy("source", session, "reaction", oracle)
    with pytest.raises(ValueError, match="no post-run obligations"):
        replace(session, outcome=COMPILED)


def test_program_lineage_complete_heuristic_hydrogen_vertical(tmp_path):
    """The narrow real vertical preserves lineage, evidence, scope, and every output."""
    oracle = HeuristicOracle()
    plan = compile_reaction_energy("Compute H + H -> H2 at the named endpoint protocol.",
                                   H_FORMATION, oracle)
    approved = _approved(plan)

    report = execute(approved, oracle, journal_path=tmp_path / "run.json")

    assert report.record.status is RunStatus.COMPLETE
    assert report.result is not None and report.certificate is not None
    assert report.result.values[0].observable_id == "reaction_energy"
    assert report.record.output_inventory == plan.request.output_contract.observable_ids
    assert report.certificate.output_inventory == plan.request.output_contract.observable_ids
    assert report.record.plan_digest == plan.digest
    assert report.record.approval_digest == approved.approval.digest
    assert report.certificate.source_digest == plan.request.source.digest
    assert report.certificate.request_digest == plan.request.digest
    assert report.certificate.plan_digest == plan.digest
    assert report.certificate.approval_digest == approved.approval.digest
    assert report.certificate.calculation_digest == plan.calculation.digest
    assert report.certificate.claim_scope.kind is ClaimKind.LITERAL
    assert report.certificate.evidence_status is EvidenceStatus.CALIBRATED
    assert report.certificate.evidence_status is plan.request.physical_ir.evidence_status
    assert all(result.outcome.value == "PASS" for result in report.certificate.validity_results)
    value = report.result.values[0]
    assert value.seconds >= 0
    assert value.methods
    assert isinstance(value.systematic_terms, tuple)
    persisted = json.loads((tmp_path / "run.json").read_text())
    assert persisted["status"] == RunStatus.COMPLETE.value
    assert persisted["plan_digest"] == plan.digest
    observable = next(item for item in persisted["artifacts"]
                      if item["artifact_id"] == "observable:reaction_energy")
    assert set(observable["payload"]) >= {
        "value_ev", "uncertainty_ev", "seconds", "notes", "systematic_ev",
        "methods", "systematic_terms",
    }


def test_every_plan_semantic_axis_invalidates_a_prior_approval(plan, oracle):
    """No output/model/tolerance/retention/calculation change can inherit authority."""
    approval = _approval(plan)
    changed_output = _with_request(
        plan,
        replace(
            plan.request,
            output_contract=_changed_output_contract(
                plan.request.output_contract, precision="tighter than original"
            ),
        ),
    )
    changed_retention = _with_request(
        plan,
        replace(
            plan.request,
            output_contract=_changed_output_contract(
                plan.request.output_contract,
                retention=plan.request.output_contract.retention + ("raw species values",),
            ),
        ),
    )
    changed_tolerance = replace(
        plan,
        solver=replace(plan.solver, tolerances=(("residual", 1e-9),)),
    )
    changed_calculation = replace(
        plan,
        calculation=replace(plan.calculation, engine_name="different immutable protocol"),
    )
    changed_equivalence = _with_request(
        plan,
        replace(
            plan.request,
            equivalence_contract=replace(
                plan.request.equivalence_contract,
                checkpoint_policy="different approved checkpoint policy",
            ),
        ),
    )
    observable = replace(
        plan.request.output_contract.observables[0],
        diagnostics=plan.request.output_contract.observables[0].diagnostics
        + ("additional retained residual",),
    )
    changed_observable_diagnostics = _with_request(
        plan,
        replace(
            plan.request,
            output_contract=replace(
                plan.request.output_contract,
                observables=(observable,),
            ),
        ),
    )
    changed_obligation = _with_request(
        plan,
        replace(
            plan.request,
            obligations=(
                replace(plan.request.obligations[0], required=False),
            ) + plan.request.obligations[1:],
        ),
    )
    changed_transform = replace(
        plan,
        transforms=(
            Transform(
                "identity probe",
                "A",
                plan.model.digest,
                plan.model.digest,
                ("this exact plan",),
                ("independent identity check",),
                (),
            ),
        ),
    )
    changed_lane = replace(plan, execution_lane=ExecutionLane.EXPERIMENTAL)
    changed_limits = replace(plan, limits=RuntimeLimits(max_species_calls=2))
    changed_source = compile_reaction_energy(
        "A different preserved scientist statement.",
        H_FORMATION,
        oracle,
    )
    changed_reaction = compile_reaction_energy(
        plan.request.source,
        Reaction(Config.of(H2), Config.of(H, H)),
        oracle,
    )
    variants = (
        _changed_model_plan(plan),
        changed_output,
        changed_retention,
        changed_tolerance,
        changed_calculation,
        changed_equivalence,
        changed_observable_diagnostics,
        changed_obligation,
        changed_transform,
        changed_lane,
        changed_limits,
        changed_source,
        changed_reaction,
    )

    for changed in variants:
        assert changed.digest != plan.digest
        with pytest.raises(ValueError, match="approval does not name"):
            approve(changed, approval)


def test_approved_plan_cannot_be_constructed_directly_and_raw_plan_cannot_execute(plan, oracle):
    approval = _approval(plan)

    with pytest.raises(PermissionError, match="record_approval"):
        Approval("principal", plan.digest, "scope", (), "2026-07-27T00:00:00+00:00")
    with pytest.raises(PermissionError, match="only be created by approve"):
        ApprovedPlan(plan, approval)
    with pytest.raises(TypeError, match="requires an ApprovedPlan"):
        execute(plan, oracle)


def test_mutating_oracle_after_planning_is_rejected_before_any_call(plan, oracle):
    approved = _approved(plan)
    oracle.setting = "different calculation after approval"

    with pytest.raises(ValueError, match="CalculationSpec changed"):
        execute(approved, oracle)
    assert oracle.calls == []


def test_mutating_compiler_after_approval_is_rejected_before_any_call(
    plan, oracle, monkeypatch
):
    approved = _approved(plan)
    monkeypatch.setattr(
        program_module,
        "_compiler_implementation_digest",
        lambda: "changed-compiler-implementation",
    )

    with pytest.raises(ValueError, match="compiler/runtime implementation changed"):
        execute(approved, oracle)
    assert oracle.calls == []


def test_calculation_spec_freezes_nested_settings_and_new_identity_detects_mutation():
    class NestedMutableOracle(MutableOracle):
        def __init__(self):
            super().__init__()
            self.settings = {"basis": {"cardinal": 3}}

        def calculation_spec(self):
            return self.settings

    oracle = NestedMutableOracle()
    frozen = CalculationSpec.from_oracle(oracle)
    before = frozen.digest
    oracle.settings["basis"]["cardinal"] = 4

    assert frozen.digest == before
    assert CalculationSpec.from_oracle(oracle).digest != before


def test_run_journal_persists_running_then_incomplete_and_quarantines_artifacts(plan, tmp_path):
    journal_path = tmp_path / "journal.json"
    journal = RunJournal(_approved(plan), backend="deterministic", path=journal_path,
                         run_id="durable-run")
    assert json.loads(journal_path.read_text())["status"] == RunStatus.RUNNING.value
    journal.add_artifact(Artifact("intermediate:x", "intermediate", "a" * 64, True, False))

    record = journal.incomplete("approved resource cap reached")

    persisted = json.loads(journal_path.read_text())
    assert record.status is RunStatus.INCOMPLETE
    assert record.artifacts[0].quarantined is True
    assert persisted["status"] == RunStatus.INCOMPLETE.value
    assert persisted["artifacts"][0]["quarantined"] is True
    with pytest.raises(RuntimeError, match="already terminal"):
        journal.complete()


def test_species_call_limit_returns_incomplete_with_quarantined_intermediates(plan, oracle, tmp_path):
    limited = replace(plan, limits=RuntimeLimits(max_species_calls=1))
    report = execute(_approved(limited), oracle, journal_path=tmp_path / "limited.json")

    assert report.record.status is RunStatus.INCOMPLETE
    assert report.result is None and report.certificate is None
    assert report.record.checkpoints and report.record.artifacts
    assert all(artifact.quarantined for artifact in report.record.artifacts)
    assert any("max_species_calls=1" in failure for failure in report.record.failures)
    persisted = json.loads((tmp_path / "limited.json").read_text())
    assert persisted["status"] == RunStatus.INCOMPLETE.value
    assert all(item["quarantined"] for item in persisted["artifacts"])
    assert all(item["quarantined"] for item in persisted["checkpoints"])


@pytest.mark.parametrize(
    "limits,needle",
    [
        (RuntimeLimits(wall_seconds=0.0), "wall_seconds=0.0"),
        (RuntimeLimits(memory_bytes=0), "memory_bytes=0"),
    ],
)
def test_wall_and_memory_limits_are_enforced_as_incomplete_before_oracle_calls(
    plan, oracle, limits, needle
):
    limited = replace(plan, limits=limits)

    report = execute(_approved(limited), oracle)

    assert report.record.status is RunStatus.INCOMPLETE
    assert report.result is None
    assert oracle.calls == []
    assert needle in report.record.failures[-1]
    assert all(item.quarantined for item in report.record.artifacts)


def test_runtime_limits_preserve_the_pre_water_wave_positional_api():
    limits = RuntimeLimits(3, 10.0, 1024)

    assert limits.max_species_calls == 3
    assert limits.wall_seconds == 10.0
    assert limits.memory_bytes == 1024
    assert limits.max_engine_calls is None


def test_unsupported_observable_is_blocked_before_approval(plan, oracle):
    contract = _changed_output_contract(plan.request.output_contract, extra=True)
    blocked = compile_reaction_energy(
        plan.request.source,
        H_FORMATION,
        oracle,
        output_contract=contract,
    )

    assert blocked.blockers
    assert any("cannot emit" in item for item in blocked.blockers)
    with pytest.raises(ValueError, match="blockers"):
        approve(blocked, _approval(blocked))
    with pytest.raises(ValueError, match="unsupported observables"):
        _with_request(plan, replace(plan.request, output_contract=contract))


def test_supported_reaction_output_id_cannot_promise_unsupported_semantics(plan, oracle):
    altered = _changed_output_contract(
        plan.request.output_contract,
        precision="claim an exact Gibbs free energy instead of the emitted endpoint delta-E",
    )

    blocked = compile_reaction_energy(
        plan.request.source,
        H_FORMATION,
        oracle,
        output_contract=altered,
    )

    assert any("exact default output contract" in item for item in blocked.blockers)
    with pytest.raises(ValueError, match="blockers"):
        approve(blocked, _approval(blocked))
    assert oracle.calls == []


def test_required_unknown_obligation_refuses_before_oracle_execution(plan, oracle):
    unknown = ValidityObligation(
        "adversarial-required-obligation",
        ObligationStage.PRE,
        "tests/no-evaluator-registered",
        "must not be silently skipped",
        required=True,
    )
    request = replace(plan.request, obligations=plan.request.obligations + (unknown,))
    report = execute(_approved(_with_request(plan, request)), oracle)

    assert report.record.status is RunStatus.REFUSED
    assert report.result is None and report.certificate is None
    assert oracle.calls == []
    assert report.record.obligation_results[-1].obligation_digest == unknown.digest
    assert report.record.obligation_results[-1].outcome.value == "REFUSE"


def test_run_journal_refuses_completion_when_required_obligations_are_missing(plan):
    journal = RunJournal(_approved(plan), backend="deterministic")
    payload = Estimate(-1.0, 0.1, "typed-test-estimate")
    journal.add_artifact(Artifact(
        "observable:reaction_energy",
        "observable",
        canonical_digest(payload),
        True,
        False,
        payload=payload,
    ))

    record = journal.complete()

    assert record.status is RunStatus.INVALID
    assert record.artifacts[0].quarantined is True
    assert "required obligations did not all pass" in record.failures[-1]


def test_run_journal_rejects_wrong_observable_payload_schema(plan):
    journal = RunJournal(_approved(plan), backend="deterministic")
    payload = {"value_ev": -1.0}
    journal.add_artifact(Artifact(
        "observable:reaction_energy",
        "observable",
        canonical_digest(payload),
        True,
        False,
        payload=payload,
    ))
    for obligation in plan.request.obligations:
        journal.add_obligation_result(
            ObligationResult(
                obligation.digest,
                ObligationOutcome.PASS,
                "forged pass cannot override payload schema",
            )
        )

    record = journal.complete()

    assert record.status is RunStatus.INVALID
    assert all(item.quarantined for item in record.artifacts)
    assert "payload schema mismatch" in record.failures[-1]


def test_an_obligation_cannot_acquire_contradictory_duplicate_results(plan):
    journal = RunJournal(_approved(plan), backend="deterministic")
    obligation = plan.request.obligations[0]
    first = ObligationResult(obligation.digest, ObligationOutcome.PASS, "first verdict")
    journal.add_obligation_result(first)

    with pytest.raises(ValueError, match="exactly one result"):
        journal.add_obligation_result(
            ObligationResult(obligation.digest, ObligationOutcome.FAIL, "contradiction")
        )


def test_run_journal_rejects_undeclared_obligation_results(plan):
    journal = RunJournal(_approved(plan), backend="deterministic")

    with pytest.raises(ValueError, match="not declared"):
        journal.add_obligation_result(
            ObligationResult("forged-obligation-digest", ObligationOutcome.PASS, "forged")
        )


def test_executor_identity_is_rechecked_before_calls(plan, oracle):
    approved = _approved(plan)
    object.__setattr__(approved.plan, "executor_id", "attacker/unregistered")
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(
        approved,
        "approval_record_digest",
        approved.approval.digest,
    )

    with pytest.raises(ValueError, match="no runtime is registered"):
        execute(approved, oracle)
    assert oracle.calls == []


def test_approval_record_mutation_is_rejected_before_calls(plan, oracle):
    approved = _approved(plan)
    object.__setattr__(approved.approval, "scope", "post-authorization wider scope")

    with pytest.raises(ValueError, match="approval record changed"):
        execute(approved, oracle)
    assert oracle.calls == []


def test_observable_artifact_requires_schema_checkable_payload():
    with pytest.raises(ValueError, match="schema-checkable payload"):
        Artifact("observable:forged", "observable", "b" * 64, True, False)


def test_oracle_identity_change_during_a_call_fails_and_quarantines_partial(plan):
    class MutatesDuringCall(MutableOracle):
        def energy(self, molecule):
            estimate = super().energy(molecule)
            self.setting = "changed-during-call"
            return estimate

    mutating = MutatesDuringCall()
    mutation_plan = compile_reaction_energy(plan.request.source, H_FORMATION, mutating)

    report = execute(_approved(mutation_plan), mutating)

    assert report.record.status is RunStatus.FAILED
    assert report.result is None and report.certificate is None
    assert len(mutating.calls) == 1
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.artifacts)
    assert all(item.quarantined for item in report.record.checkpoints)
    assert "CalculationSpec changed during" in report.record.failures[-1]


def test_assembly_hypothesis_cannot_enter_calibrated_or_certified_lane(plan):
    spec = AssemblySpec("hypothetical whole", "component", ("quorum rule",))
    hypothesis = AssemblyHypothesis(spec, ("calibration missing",), ("quorum fails",))

    with pytest.raises(ValueError, match="AssemblyHypothesis"):
        replace(plan.request.physical_ir, assemblies=(hypothesis,))

    experimental_ir = replace(
        plan.request.physical_ir,
        assemblies=(hypothesis,),
        evidence_status=EvidenceStatus.EXPERIMENTAL,
    )
    request = replace(plan.request, physical_ir=experimental_ir)
    with pytest.raises(ValueError, match="certified.*lane"):
        replace(plan, request=request)


def test_oracle_exception_after_one_species_fails_and_quarantines_every_partial(plan):
    class ExplodesOnMolecule(MutableOracle):
        def energy(self, molecule):
            if molecule.bonds:
                raise RuntimeError("injected backend failure")
            return super().energy(molecule)

    exploding = ExplodesOnMolecule()
    failure_plan = compile_reaction_energy(plan.request.source, H_FORMATION, exploding)

    report = execute(_approved(failure_plan), exploding)

    assert report.record.status is RunStatus.FAILED
    assert report.result is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.artifacts)
    assert all(item.quarantined for item in report.record.checkpoints)
    assert "injected backend failure" in report.record.failures[-1]


def test_failed_atomic_replace_keeps_prior_journal_and_in_memory_state(
    plan, tmp_path, monkeypatch
):
    path = tmp_path / "atomic.json"
    journal = RunJournal(_approved(plan), backend="deterministic", path=path)
    before_text = path.read_text()
    before_record = journal.record

    def fail_replace(_source, _target):
        raise OSError("injected replace failure")

    monkeypatch.setattr(program_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        journal.add_diagnostic("must not half-commit")

    assert path.read_text() == before_text
    assert json.loads(path.read_text())["status"] == RunStatus.RUNNING.value
    assert journal.record == before_record
    assert not list(tmp_path.glob("*.tmp"))


def test_oracle_refusal_is_a_refused_run_not_a_partial_success(plan):
    refusing = MutableOracle(refuse=True)
    refusal_plan = compile_reaction_energy(plan.request.source, H_FORMATION, refusing)

    report = execute(_approved(refusal_plan), refusing)

    assert report.record.status is RunStatus.REFUSED
    assert report.result is None and report.certificate is None
    assert report.record.artifacts
    assert all(artifact.quarantined for artifact in report.record.artifacts)
    assert not any(artifact.kind == "observable" for artifact in report.record.artifacts)
    assert any("oracle declined endpoint species" in failure for failure in report.record.failures)


@pytest.mark.parametrize(
    "value,error",
    [
        (object(), TypeError),
        (lambda: None, TypeError),
        ({1: "non-string key"}, TypeError),
        (float("nan"), ValueError),
    ],
)
def test_canonical_serializer_refuses_ambiguous_or_nonfinite_semantic_values(value, error):
    with pytest.raises(error):
        canonical_digest(value)


def test_canonical_serializer_preserves_signed_infinity_explicitly_and_without_aliasing():
    positive = canonical_digest(float("inf"))
    negative = canonical_digest(float("-inf"))

    assert positive == canonical_digest(float("inf"))
    assert positive != negative
    assert positive != canonical_digest("+inf")
    assert CalculationSpec(
        "tests.InfiniteOracle", "infinite-sentinel", {"limit": float("inf")}, "digest"
    ).digest


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DerivationRef("DERIVED_COMPLETE", "source", "digest", "scope"),
        lambda: ValidityObligation("name", "POST", "evaluator", "description"),
        lambda: ObligationResult("digest", "PASS", "detail"),
    ],
)
def test_contract_enums_do_not_accept_aliasing_raw_strings(factory):
    with pytest.raises(TypeError):
        factory()
