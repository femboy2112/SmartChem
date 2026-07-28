"""Source-to-certificate acceptance tests for the human-isotope D2a vertical."""
from __future__ import annotations

from dataclasses import replace
import json

import pytest

import smartchem.human_isotope as human_module
from smartchem.contracts import ClaimKind, EvidenceStatus, InferenceKind, RunStatus
from smartchem.human_isotope import (
    HUMAN_ISOTOPE_CASUALTIES,
    HUMAN_ISOTOPE_OMISSIONS,
    HumanIsotopeIdentifiabilityEngine,
    compile_human_isotope_identifiability,
    compile_session_human_isotope_identifiability,
    human_isotope_slot,
)
from smartchem.human_isotope_domain import (
    AssemblyKind,
    CalibrationEvidence,
    EnvironmentalProtocol,
    EvidenceBasis,
    ExposureEvent,
    ExposureMetric,
    ExposureRoute,
    GranularityLevel,
    GranularitySpec,
    HazardEffect,
    HazardMechanismChoice,
    HumanIsotopeSpec,
    HumanTarget,
    IdentifiabilityStatus,
    InternalExposureMetric,
    LivingAssemblyHypothesis,
    MedianEndpointConstraint,
    MedianEndpointKind,
    PopulationProtocol,
    RecoveryModel,
    ToxicokineticLink,
    UncertaintyInterval,
    ValidationStatus,
    diagnose_human_isotope,
)
from smartchem.ledger import COMPILED, STALLED, Spec, shepherd
from smartchem.program import (
    ClaimScope,
    RuntimeLimits,
    approve,
    execute,
    record_approval,
)


def _spec(
    *,
    target: HumanTarget = HumanTarget.COHORT_ALL_CAUSE_SURVIVAL,
    evidence_basis: EvidenceBasis = EvidenceBasis.HYPOTHETICAL_CONSTRAINT,
    level: GranularityLevel = GranularityLevel.LUMPED_FUNCTIONAL_UNITS,
) -> HumanIsotopeSpec:
    endpoint = MedianEndpointConstraint(
        kind=MedianEndpointKind.LD50,
        value=100.0,
        uncertainty=UncertaintyInterval(90.0, 110.0),
        population="synthetic generic-human proxy cohort",
        species="Homo sapiens",
        route=ExposureRoute.ORAL,
        endpoint_definition="declared all-cause functional death event",
        exposure_duration_days=1.0,
        observation_window_days=14.0,
        provenance="hypothetical endpoint for compiler acceptance; no observed humans",
        evidence_basis=evidence_basis,
        applicability="structural identifiability only; no person or population prediction",
    )
    population = PopulationProtocol(
        population=endpoint.population,
        species=endpoint.species,
        time_origin="start of the declared synthetic exposure",
        event=endpoint.endpoint_definition,
        competing_risks=("other declared terminal failure causes",),
        censoring="right censoring retained explicitly",
        truncation="no truncation in the synthetic structural example",
        strata=("one declared synthetic stratum",),
    )
    components = (
        ("repair reserve", "background failure channel")
        if level is GranularityLevel.LUMPED_FUNCTIONAL_UNITS
        else ("repair system", "functional threshold")
    )
    return HumanIsotopeSpec(
        target=target,
        granularity=GranularitySpec(
            level,
            components,
            "the two scientist-selected component classes remain differentiated",
        ),
        assembly=LivingAssemblyHypothesis(
            AssemblyKind.REDUNDANCY_QUORUM,
            ("functional reserve must remain above a declared quorum",),
            "repair replenishes reserve under one unvalidated rule",
            ("background and reserve failure channels are explicitly coupled",),
        ),
        environment=EnvironmentalProtocol(
            agent="synthetic test agent",
            route=endpoint.route,
            metric=endpoint.metric,
            schedule=(
                ExposureEvent(
                    0.0,
                    endpoint.exposure_duration_days,
                    endpoint.value,
                    endpoint.metric,
                ),
            ),
            recovery=RecoveryModel.PARTIAL_DECLARED,
            recovery_description="selected recovery hypothesis; not measured evidence",
        ),
        hazard_mechanism=HazardMechanismChoice(
            HazardEffect.REDUNDANCY_OR_REPAIR_STATE,
            (components[0],),
            "exposure changes reserve/repair, not a nuclear decay constant",
        ),
        population=population,
        toxicokinetic_link=ToxicokineticLink(
            endpoint.route,
            endpoint.metric,
            InternalExposureMetric.INTERNAL_BURDEN_MG_PER_KG,
            endpoint.species,
            population.species,
            "declared one-compartment placeholder transport",
            ("linear transport over the declared synthetic exposure",),
            "synthetic transport hypothesis for compiler acceptance",
            "not validated for any person or population",
        ),
        endpoint=endpoint,
        calibration=CalibrationEvidence(
            dose_level_count=1,
            observation_time_count=1,
            population_count=1,
            record_count=1,
            dataset_digest="a" * 64,
            uncertainty_quantified=False,
            uncertainty_model="endpoint interval only; no dynamic uncertainty model",
            heldout_record_count=0,
            heldout_dataset_digest=None,
        ),
    )


def _approved(plan):
    return approve(
        plan,
        record_approval(
            plan,
            "scientist",
            "run the synthetic structural identifiability diagnostic only",
        ),
    )


def test_underidentified_phrase_remains_open_until_typed_choices_are_bound():
    starting = Spec(
        "human-isotope",
        (
            human_isotope_slot(
                "human-model",
                "Model a generic human as an isotope using LD50 in the environment.",
            ),
        ),
    )
    session = shepherd(starting, lambda current, _holes: current)

    assert session.outcome == STALLED
    assert session.spec.measure() == 1
    with pytest.raises(ValueError, match="outright COMPILED"):
        compile_session_human_isotope_identifiability(
            "Model a generic human as an isotope using LD50 in the environment.",
            session,
            "human-model",
            HumanIsotopeIdentifiabilityEngine(),
        )


def test_typed_session_runs_complete_structural_diagnosis(tmp_path):
    spec = _spec()
    starting = Spec(
        "human-isotope",
        (
            human_isotope_slot(
                "human-model",
                "Model a generic human as an isotope using LD50 in the environment.",
            ),
        ),
    )

    def answer(current, _holes):
        return current.bind_typed(
            "human-model",
            spec,
            source_text=(
                "Use the declared synthetic cohort, lumped functional units, "
                "redundancy/repair hypothesis, oral LD50 endpoint, and structural "
                "identifiability target."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        )

    session = shepherd(
        starting,
        answer,
        discarded=(
            "literal isotope identity",
            "actual-person mortality prediction",
            "LD50 as a rate",
        ),
    )
    assert session.outcome == COMPILED
    engine = HumanIsotopeIdentifiabilityEngine()
    plan = compile_session_human_isotope_identifiability(
        (
            "Model a generic human as a differentiated bundle with modified decay "
            "affected by environmental LD50 constraints."
        ),
        session,
        "human-model",
        engine,
    )
    assert len(plan.request.physical_ir.calibrations) == 1
    assert len(plan.request.physical_ir.model_patches) == 1
    report = execute(
        _approved(plan),
        engine,
        journal_path=tmp_path / "human-isotope.json",
    )

    assert report.record.status is RunStatus.COMPLETE
    assert engine.calls == 1
    assert report.result is not None and report.certificate is not None
    assert report.certificate.claim_scope.kind is ClaimKind.EXPERIMENTAL_PROXY
    assert report.certificate.evidence_status is EvidenceStatus.STRUCTURAL_TOY
    assert set(HUMAN_ISOTOPE_CASUALTIES).issubset(
        report.certificate.casualties
    )
    assert report.certificate.omissions == HUMAN_ISOTOPE_OMISSIONS
    assert report.certificate.output_inventory == (
        "human_isotope_identifiability",
        "human_isotope_constraint_inventory",
        "human_isotope_family_witnesses",
    )
    diagnostic = report.result.values[0].payload
    assert diagnostic.status is IdentifiabilityStatus.UNDERIDENTIFIED_DYNAMIC_MODEL
    assert diagnostic.validation is ValidationStatus.UNVALIDATED
    assert len(diagnostic.family_witnesses) == 2
    assert {
        item.cumulative_mortality_at_endpoint
        for item in diagnostic.family_witnesses
    } == {0.5}
    assert (
        diagnostic.family_witnesses[0].cumulative_mortality_at_half_time
        != diagnostic.family_witnesses[1].cumulative_mortality_at_half_time
    )
    assert all(
        result.outcome.value == "PASS"
        for result in report.certificate.validity_results
    )
    persisted = json.loads((tmp_path / "human-isotope.json").read_text())
    assert persisted["status"] == "COMPLETE"
    assert len(persisted["checkpoints"]) == 1


def test_complete_lifecycle_never_promotes_validation_or_emits_person_probability():
    engine = HumanIsotopeIdentifiabilityEngine()
    report = execute(
        _approved(
            compile_human_isotope_identifiability("diagnose only", _spec(), engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.COMPLETE
    diagnostic = report.result.values[0].payload
    assert diagnostic.validation is ValidationStatus.UNVALIDATED
    assert "prediction for any actual person" in diagnostic.transport.discarded
    assert all(
        "individual" not in value.observable_id
        and "actual_person" not in value.observable_id
        for value in report.result.values
    )


def test_two_materially_different_scientist_interpretations_have_distinct_plans():
    cohort_engine = HumanIsotopeIdentifiabilityEngine()
    threshold_engine = HumanIsotopeIdentifiabilityEngine()
    cohort = compile_human_isotope_identifiability(
        "cohort interpretation",
        _spec(),
        cohort_engine,
    )
    threshold = compile_human_isotope_identifiability(
        "functional threshold interpretation",
        _spec(
            target=HumanTarget.FUNCTIONAL_THRESHOLD_DISTRIBUTION,
            level=GranularityLevel.REPAIR_SYSTEMS,
        ),
        threshold_engine,
    )

    assert cohort.digest != threshold.digest
    assert cohort.request.resolved.digest != threshold.request.resolved.digest
    assert not cohort.blockers
    assert any(
        "supports only COHORT_ALL_CAUSE_SURVIVAL" in item
        for item in threshold.blockers
    )
    with pytest.raises(ValueError, match="blockers"):
        _approved(threshold)


def test_individual_prediction_and_nonhypothetical_evidence_are_planning_blockers():
    engine = HumanIsotopeIdentifiabilityEngine()
    individual = compile_human_isotope_identifiability(
        "predict one person",
        _spec(target=HumanTarget.INDIVIDUAL_LIFETIME_SAMPLE),
        engine,
    )
    observed = compile_human_isotope_identifiability(
        "use observed human evidence",
        _spec(evidence_basis=EvidenceBasis.HUMAN_EVIDENCE_SYNTHESIS),
        engine,
    )

    assert any("individual lifetime" in item for item in individual.blockers)
    assert any("data-governance" in item for item in observed.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(individual)
    with pytest.raises(ValueError, match="blockers"):
        _approved(observed)
    assert engine.calls == 0


def test_cause_specific_and_richer_evidence_require_different_executors():
    engine = HumanIsotopeIdentifiabilityEngine()
    cause_specific = compile_human_isotope_identifiability(
        "estimate the cause-specific cumulative incidence",
        _spec(target=HumanTarget.CAUSE_SPECIFIC_CUMULATIVE_INCIDENCE),
        engine,
    )
    baseline = _spec()
    richer = replace(
        baseline,
        calibration=replace(
            baseline.calibration,
            dose_level_count=4,
            observation_time_count=6,
            record_count=100,
            uncertainty_quantified=True,
            uncertainty_model="declared interval model",
            heldout_record_count=20,
            heldout_dataset_digest="b" * 64,
        ),
    )
    richer_plan = compile_human_isotope_identifiability(
        "use a richer calibration dataset",
        richer,
        engine,
    )

    assert any("competing cause-specific hazards" in item for item in cause_specific.blockers)
    assert any("data-bound calibration" in item for item in richer_plan.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(cause_specific)
    with pytest.raises(ValueError, match="blockers"):
        _approved(richer_plan)
    assert engine.calls == 0


def test_runtime_refuses_noncohort_target_even_if_planning_blocker_is_removed():
    engine = HumanIsotopeIdentifiabilityEngine()
    blocked = compile_human_isotope_identifiability(
        "functional threshold interpretation",
        _spec(
            target=HumanTarget.FUNCTIONAL_THRESHOLD_DISTRIBUTION,
            level=GranularityLevel.REPAIR_SYSTEMS,
        ),
        engine,
    )
    rebuilt = replace(blocked, blockers=())
    report = execute(_approved(rebuilt), engine)

    assert report.record.status is RunStatus.REFUSED
    assert engine.calls == 0
    assert "outside the supported structural identifiability subject" in (
        report.record.failures[-1]
    )


def test_known_output_id_cannot_promise_a_mortality_prediction():
    engine = HumanIsotopeIdentifiabilityEngine()
    baseline = compile_human_isotope_identifiability("diagnose", _spec(), engine)
    changed = replace(
        baseline.request.output_contract.observables[0],
        coverage="actual-person mortality probability and clinical recommendation",
    )
    contract = replace(
        baseline.request.output_contract,
        observables=(
            changed,
            *baseline.request.output_contract.observables[1:],
        ),
    )
    altered = compile_human_isotope_identifiability(
        "diagnose",
        _spec(),
        engine,
        output_contract=contract,
    )

    assert any("exact default output contract" in item for item in altered.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(altered)
    assert engine.calls == 0


def test_post_approval_output_semantic_tampering_fails_before_engine_call():
    engine = HumanIsotopeIdentifiabilityEngine()
    approved = _approved(
        compile_human_isotope_identifiability("diagnose", _spec(), engine)
    )
    changed = replace(
        approved.plan.request.output_contract.observables[0],
        support="a specific person",
    )
    object.__setattr__(
        approved.plan.request,
        "output_contract",
        replace(
            approved.plan.request.output_contract,
            observables=(
                changed,
                *approved.plan.request.output_contract.observables[1:],
            ),
        ),
    )
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(approved, "approval_record_digest", approved.approval.digest)

    with pytest.raises(ValueError, match="exact default output contract"):
        execute(approved, engine)
    assert engine.calls == 0


def test_proxy_scope_tampering_refuses_before_engine_call():
    engine = HumanIsotopeIdentifiabilityEngine()
    approved = _approved(
        compile_human_isotope_identifiability("diagnose", _spec(), engine)
    )
    object.__setattr__(
        approved.plan.request.physical_ir,
        "claim_scope",
        ClaimScope(ClaimKind.LITERAL, "validated human mortality model", ()),
    )
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(approved, "approval_record_digest", approved.approval.digest)

    report = execute(approved, engine)

    assert report.record.status is RunStatus.REFUSED
    assert engine.calls == 0
    assert "claim scope" in report.record.failures[-1]


def test_engine_cannot_forge_a_conforming_looking_diagnostic():
    class ForgingEngine(HumanIsotopeIdentifiabilityEngine):
        def solve(self, spec):
            self.calls += 1
            genuine = diagnose_human_isotope(spec)
            first = replace(
                genuine.family_witnesses[0],
                cumulative_mortality_at_half_time=0.1,
            )
            return replace(
                genuine,
                family_witnesses=(first, genuine.family_witnesses[1]),
            )

    engine = ForgingEngine()
    report = execute(
        _approved(
            compile_human_isotope_identifiability("diagnose", _spec(), engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)


def test_engine_cannot_use_diagnostic_subclass_equality_to_forge_result():
    class LyingDiagnostic(type(diagnose_human_isotope(_spec()))):
        def __eq__(self, _other):
            return True

        def __ne__(self, _other):
            return False

    class ForgingEngine(HumanIsotopeIdentifiabilityEngine):
        def solve(self, spec):
            self.calls += 1
            genuine = diagnose_human_isotope(spec)
            return LyingDiagnostic(
                genuine.spec,
                genuine.status,
                genuine.validation,
                genuine.constraint_inventory,
                genuine.free_parameters,
                genuine.missing_evidence,
                genuine.transport,
                genuine.family_witnesses,
                genuine.discriminating_experiments,
            )

    engine = ForgingEngine()
    report = execute(
        _approved(
            compile_human_isotope_identifiability("diagnose", _spec(), engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None


def test_engine_cannot_use_nested_witness_subclass_equality_to_forge_result():
    genuine_witness_type = type(
        diagnose_human_isotope(_spec()).family_witnesses[0]
    )

    class LyingWitness(genuine_witness_type):
        def __eq__(self, _other):
            return True

        def __ne__(self, _other):
            return False

    class ForgingEngine(HumanIsotopeIdentifiabilityEngine):
        def solve(self, spec):
            self.calls += 1
            genuine = diagnose_human_isotope(spec)
            original = genuine.family_witnesses[0]
            forged = LyingWitness(
                original.family,
                original.parameters,
                0.1,
                original.cumulative_mortality_at_endpoint,
            )
            return replace(
                genuine,
                family_witnesses=(forged, genuine.family_witnesses[1]),
            )

    engine = ForgingEngine()
    report = execute(
        _approved(
            compile_human_isotope_identifiability("diagnose", _spec(), engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None


def test_engine_identity_change_during_call_quarantines_checkpoint():
    class MutatingEngine(HumanIsotopeIdentifiabilityEngine):
        def __init__(self):
            super().__init__()
            self.setting = "one"

        def calculation_spec(self):
            return {"setting": self.setting, "version": 1}

        def solve(self, spec):
            result = super().solve(spec)
            self.setting = "two"
            return result

    engine = MutatingEngine()
    report = execute(
        _approved(
            compile_human_isotope_identifiability("diagnose", _spec(), engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.FAILED
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert report.result is None and report.certificate is None


def test_engine_cannot_mutate_approved_plan_during_solve():
    class PlanMutatingEngine(HumanIsotopeIdentifiabilityEngine):
        def __init__(self):
            super().__init__()
            self.approved = None

        def solve(self, spec):
            diagnostic = super().solve(spec)
            assert self.approved is not None
            contract = self.approved.plan.request.output_contract
            object.__setattr__(
                self.approved.plan.request,
                "output_contract",
                replace(
                    contract,
                    observables=(
                        replace(
                            contract.observables[0],
                            precision="mutated during approved human-isotope solve",
                        ),
                    )
                    + contract.observables[1:],
                ),
            )
            return diagnostic

    engine = PlanMutatingEngine()
    approved = _approved(
        compile_human_isotope_identifiability("diagnose", _spec(), engine)
    )
    engine.approved = approved

    report = execute(approved, engine)

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert report.record.artifacts
    assert all(artifact.quarantined for artifact in report.record.artifacts)


def test_engine_call_cap_is_incomplete_without_call():
    engine = HumanIsotopeIdentifiabilityEngine()
    plan = compile_human_isotope_identifiability(
        "diagnose",
        _spec(),
        engine,
        limits=RuntimeLimits(max_engine_calls=0),
    )
    report = execute(_approved(plan), engine)

    assert report.record.status is RunStatus.INCOMPLETE
    assert engine.calls == 0
    assert "max_engine_calls=0" in report.record.failures[-1]


def test_post_engine_resource_wall_quarantines_complete_checkpoint(monkeypatch):
    checks = iter((None, "injected post-call resource wall"))
    monkeypatch.setattr(
        human_module,
        "_resource_wall",
        lambda *_args, **_kwargs: next(checks),
    )
    engine = HumanIsotopeIdentifiabilityEngine()
    report = execute(
        _approved(
            compile_human_isotope_identifiability("diagnose", _spec(), engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.INCOMPLETE
    assert engine.calls == 1
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert all(item.quarantined for item in report.record.artifacts)


def test_result_construction_failure_is_recorded_before_terminal_complete(monkeypatch):
    def fail_result_construction(*_args, **_kwargs):
        raise RuntimeError("injected result construction failure")

    monkeypatch.setattr(
        human_module,
        "StructuredObservableValue",
        fail_result_construction,
    )
    engine = HumanIsotopeIdentifiabilityEngine()
    report = execute(
        _approved(
            compile_human_isotope_identifiability("diagnose", _spec(), engine)
        ),
        engine,
    )

    assert report.record.status is RunStatus.FAILED
    assert report.result is None and report.certificate is None
    assert "injected result construction failure" in report.record.failures[-1]
