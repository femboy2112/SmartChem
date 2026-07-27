"""Lifecycle and boundary tests for the synthetic D2b survival executor."""
from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pytest

import smartchem
import smartchem.human_survival as human_survival_module
import smartchem.runtime_registry as runtime_registry
from smartchem.contracts import ClaimKind, EvidenceStatus, InferenceKind, RunStatus
from smartchem.human_isotope import human_isotope_slot
from smartchem.human_survival import (
    HUMAN_SURVIVAL_CASUALTIES,
    HUMAN_SURVIVAL_OMISSIONS,
    SyntheticSurvivalRecoveryEngine,
    compile_human_survival_recovery,
    compile_session_human_survival_recovery,
    human_survival_slot,
)
from smartchem.human_survival_domain import (
    Applicability,
    DataAuthority,
    FitProtocol,
    FitStatus,
    GeneratorTruth,
    IntervalCohortRecord,
    ParameterEstimate,
    Split,
    SurvivalAssembly,
    SurvivalCalibrationSpec,
    SurvivalDataset,
    SurvivalFamily,
    SyntheticDataGovernance,
    TruthVisibility,
    interval_event_probability,
)
from smartchem.ledger import COMPILED, STALLED, Spec, shepherd
from smartchem.program import (
    RuntimeLimits,
    approve,
    execute,
    record_approval,
)


TRUE_PARAMETERS = ParameterEstimate(5.0, 1.35, 0.55)


def _event_count(
    dose: float,
    start: float,
    end: float,
    at_risk: int,
    rng: np.random.Generator,
) -> int:
    scratch = IntervalCohortRecord("scratch", "scratch-cohort", dose, start, end, at_risk, 1, Split.TRAIN)
    probability = interval_event_probability(scratch, 1.0, TRUE_PARAMETERS)
    return int(rng.binomial(at_risk, probability))


def _spec() -> SurvivalCalibrationSpec:
    records: list[IntervalCohortRecord] = []
    generators = {
        Split.TRAIN: np.random.default_rng(1729),
        Split.HOLDOUT: np.random.default_rng(2718),
    }
    for split, offset, at_risk in ((Split.TRAIN, 0, 100_000), (Split.HOLDOUT, 100, 40_000)):
        for dose_index, dose in enumerate((0.0, 1.0, 2.0)):
            for time_index, (start, end) in enumerate(((0.0, 1.0), (1.0, 3.0), (3.0, 6.0))):
                number = offset + 3 * dose_index + time_index
                records.append(
                    IntervalCohortRecord(
                        f"{split.value.lower()}-record-{number}",
                        f"{split.value.lower()}-cohort-{number}",
                        dose,
                        start,
                        end,
                        at_risk,
                        _event_count(dose, start, end, at_risk, generators[split]),
                        split,
                    )
                )
    truth = GeneratorTruth(
        "interval-generator-v1", "a" * 64, TRUE_PARAMETERS,
        TruthVisibility.POST_FIT_RECOVERY_ASSESSMENT_ONLY,
    )
    return SurvivalCalibrationSpec(
        "synthetic independent-cohort all-cause interval events",
        "synthetic dose unit",
        "day",
        SurvivalDataset.from_records(tuple(records)),
        SyntheticDataGovernance(
            DataAuthority.SYNTHETIC_ONLY,
            Applicability.DECLARED_GENERATOR_RECOVERY_ONLY,
            truth.generator_id,
            truth.generator_version_digest,
            "b" * 64,
            "c" * 64,
            1729,
            2718,
            "seeded binomial synthetic records for executor acceptance testing",
            "No transfer to biological, clinical, human, animal, or safety claims.",
        ),
        SurvivalAssembly(
            "synthetic-lumped-assembly",
            ("synthetic reserve", "synthetic event channel"),
            "scientist-declared proxy aggregation only",
            "synthetic generator recovery only",
        ),
        FitProtocol(
            SurvivalFamily.WEIBULL_PROPORTIONAL_HAZARDS,
            1.0,
            ((-4.0, 4.0), (-3.0, 3.0), (-3.0, 3.0)),
            (
                (math.log(3.0), math.log(0.8), -0.5),
                (math.log(5.0), math.log(1.3), 0.0),
                (math.log(8.0), math.log(2.0), 1.0),
            ),
            5_000,
            1e-6,
            1e-4,
            1e-3,
            1e-4,
            1e10,
            0.03,
            0.03,
        ),
        truth,
    )


def _approved(plan):
    return approve(
        plan,
        record_approval(
            plan,
            "scientist",
            "run the declared synthetic interval-cohort recovery only",
        ),
    )


def test_public_exports_and_registry_descriptor_are_exact_and_d2b_specific():
    for name in (
        "SyntheticSurvivalCalibrationSpec",
        "SyntheticSurvivalRecoveryEngine",
        "compile_human_survival_recovery",
        "compile_session_human_survival_recovery",
        "human_survival_slot",
        "HUMAN_SURVIVAL_CASUALTIES",
        "HUMAN_SURVIVAL_OMISSIONS",
    ):
        assert hasattr(smartchem, name)
    executor_id = "smartchem.human_survival/synthetic-weibull-interval-recovery-v1"
    descriptor = runtime_registry.descriptor_for(executor_id)
    assert descriptor.subject_type.resolve() is SurvivalCalibrationSpec
    assert descriptor.runner.resolve() is human_survival_module._execute_human_survival
    assert executor_id in runtime_registry.executor_ids()


def test_shepherd_requires_a_typed_closed_d2b_session_and_rejects_d2a_slot_mixup():
    source = "Fit only declared synthetic cohorts and score their locked holdout."
    starting = Spec("synthetic-survival", (human_survival_slot("survival-model", source),))
    stalled = shepherd(starting, lambda current, _holes: current)
    assert stalled.outcome == STALLED
    with pytest.raises(ValueError, match="outright closed COMPILED"):
        compile_session_human_survival_recovery(source, stalled, "survival-model", SyntheticSurvivalRecoveryEngine())

    spec = _spec()
    compiled = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            "survival-model", spec, source_text=source, inference=InferenceKind.QUESTION_CONFIRMED
        ),
        discarded=("actual human calibration", "LD50 semantics", "biology transfer"),
    )
    assert compiled.outcome == COMPILED
    plan = compile_session_human_survival_recovery(source, compiled, "survival-model", SyntheticSurvivalRecoveryEngine())
    assert not plan.blockers

    d2a_start = Spec("human-isotope", (human_isotope_slot("isotope-model", "diagnose"),))
    with pytest.raises(TypeError):
        d2a_start.bind_typed("isotope-model", spec, source_text="wrong rung", inference=InferenceKind.QUESTION_CONFIRMED)


def test_complete_execution_has_exact_certificate_casualties_and_five_output_receipts(tmp_path):
    engine = SyntheticSurvivalRecoveryEngine()
    report = execute(
        _approved(compile_human_survival_recovery("fit synthetic cohorts", _spec(), engine)),
        engine,
        journal_path=tmp_path / "human-survival.json",
    )

    assert report.record.status is RunStatus.COMPLETE
    assert engine.calls == 1
    assert report.result is not None and report.certificate is not None
    assert report.certificate.claim_scope.kind is ClaimKind.EXPERIMENTAL_PROXY
    assert report.certificate.evidence_status is EvidenceStatus.STRUCTURAL_TOY
    assert report.certificate.casualties == HUMAN_SURVIVAL_CASUALTIES
    assert report.certificate.omissions == HUMAN_SURVIVAL_OMISSIONS
    assert report.certificate.output_inventory == (
        "human_survival_synthetic_fit",
        "human_survival_data_governance",
        "human_survival_parameter_uncertainty",
        "human_survival_training_predictions",
        "human_survival_heldout_scoring",
    )
    diagnostic = report.result.values[0].payload
    assert diagnostic.status is FitStatus.SYNTHETIC_RECOVERY_PASSED
    assert "human-isotope" in HUMAN_SURVIVAL_CASUALTIES[4]
    assert all("ld50" not in value.observable_id.lower() for value in report.result.values)
    assert len(report.certificate.validity_results) == 4
    assert all(item.outcome.value == "PASS" for item in report.certificate.validity_results)


def test_output_contract_mutation_becomes_a_planning_blocker_before_engine_execution():
    engine = SyntheticSurvivalRecoveryEngine()
    baseline = compile_human_survival_recovery("fit", _spec(), engine)
    changed_observable = replace(
        baseline.request.output_contract.observables[0],
        retention=("reduced receipt",),
    )
    altered = compile_human_survival_recovery(
        "fit",
        _spec(),
        engine,
        output_contract=replace(
            baseline.request.output_contract,
            observables=(changed_observable, *baseline.request.output_contract.observables[1:]),
        ),
    )

    assert any("exact default output contract" in blocker for blocker in altered.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(altered)
    assert engine.calls == 0


def test_zero_engine_call_limit_is_incomplete_without_a_calculation():
    engine = SyntheticSurvivalRecoveryEngine()
    plan = compile_human_survival_recovery(
        "fit", _spec(), engine, limits=RuntimeLimits(max_engine_calls=0)
    )
    report = execute(_approved(plan), engine)

    assert report.record.status is RunStatus.INCOMPLETE
    assert engine.calls == 0
    assert "engine-call cap reached before fitting" in report.record.failures[-1]


def test_forged_exact_result_is_quarantined_as_invalid_after_checkpoint():
    class ForgingEngine(SyntheticSurvivalRecoveryEngine):
        def solve(self, fit_input):
            genuine = super().solve(fit_input)
            forged = replace(
                genuine.fitted_parameters,
                dose_coefficient_beta=(
                    genuine.fitted_parameters.dose_coefficient_beta + 0.1
                ),
            )
            return replace(genuine, fitted_parameters=forged)

    engine = ForgingEngine()
    report = execute(_approved(compile_human_survival_recovery("fit", _spec(), engine)), engine)

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)


def test_engine_calculation_identity_mutation_fails_and_quarantines_checkpoint():
    class MutatingEngine(SyntheticSurvivalRecoveryEngine):
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
    report = execute(_approved(compile_human_survival_recovery("fit", _spec(), engine)), engine)

    assert report.record.status is RunStatus.FAILED
    assert report.result is None and report.certificate is None
    assert report.record.checkpoints and all(item.quarantined for item in report.record.checkpoints)


def test_exact_type_boundary_rejects_subclass_lookalike_before_planning():
    class LookalikeSpec(SurvivalCalibrationSpec):
        pass

    engine = SyntheticSurvivalRecoveryEngine()
    with pytest.raises(TypeError, match="exact SurvivalCalibrationSpec"):
        compile_human_survival_recovery("fit", object.__new__(LookalikeSpec), engine)
