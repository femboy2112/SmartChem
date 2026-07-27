"""Adversarial tests for the synthetic interval-cohort survival domain."""
from __future__ import annotations

from dataclasses import replace
import math
from types import SimpleNamespace

import numpy as np
import pytest

import smartchem.human_survival_domain as domain_module
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
    SurvivalFitInput,
    SyntheticDataGovernance,
    TruthVisibility,
    fit_synthetic_survival,
    interval_event_probability,
)


TRUE_PARAMETERS = ParameterEstimate(
    lambda_days=5.0,
    shape_k=1.35,
    dose_coefficient_beta=0.55,
)


def _generator(parameters: ParameterEstimate = TRUE_PARAMETERS) -> GeneratorTruth:
    return GeneratorTruth(
        generator_id="interval-generator-v1",
        generator_version_digest="a" * 64,
        parameters=parameters,
        visibility=TruthVisibility.POST_FIT_RECOVERY_ASSESSMENT_ONLY,
    )


def _governance() -> SyntheticDataGovernance:
    return SyntheticDataGovernance(
        authority=DataAuthority.SYNTHETIC_ONLY,
        applicability=Applicability.DECLARED_GENERATOR_RECOVERY_ONLY,
        generator_id="interval-generator-v1",
        generator_version_digest="a" * 64,
        train_generation_digest="b" * 64,
        holdout_generation_digest="c" * 64,
        train_seed=1729,
        holdout_seed=2718,
        provenance="seeded binomial synthetic life-table generator for acceptance testing",
        no_transfer_clause="No biological, clinical, human, animal, or cross-domain transfer is permitted.",
    )


def _protocol(**changes: object) -> FitProtocol:
    values: dict[str, object] = {
        "family": SurvivalFamily.WEIBULL_PROPORTIONAL_HAZARDS,
        "dose_reference": 1.0,
        "transformed_bounds": ((-4.0, 4.0), (-3.0, 3.0), (-3.0, 3.0)),
        "transformed_starts": (
            (math.log(3.0), math.log(0.8), -0.5),
            (math.log(5.0), math.log(1.3), 0.0),
            (math.log(8.0), math.log(2.0), 1.0),
        ),
        "maximum_iterations": 5_000,
        "gradient_tolerance": 1e-6,
        "objective_agreement_tolerance": 1e-4,
        "parameter_agreement_tolerance": 1e-3,
        "hessian_step": 1e-4,
        "maximum_information_condition": 1e10,
        "recovery_relative_tolerance": 0.03,
        "recovery_beta_absolute_tolerance": 0.03,
    }
    values.update(changes)
    return FitProtocol(**values)  # type: ignore[arg-type]


def _event_count(
    dose: float,
    start: float,
    end: float,
    at_risk: int,
    rng: np.random.Generator,
) -> int:
    record = IntervalCohortRecord(
        record_id="scratch",
        cohort_id="scratch-cohort",
        dose=dose,
        start_days=start,
        end_days=end,
        at_risk=at_risk,
        events=1,
        split=Split.TRAIN,
    )
    probability = interval_event_probability(record, 1.0, TRUE_PARAMETERS)
    return int(rng.binomial(at_risk, probability))


def _records(*, holdout_scale: float = 1.0) -> tuple[IntervalCohortRecord, ...]:
    records: list[IntervalCohortRecord] = []
    generators = {
        Split.TRAIN: np.random.default_rng(1729),
        Split.HOLDOUT: np.random.default_rng(2718),
    }
    # Each record is an independently generated cohort interval, not a repeated
    # cumulative probability from a shared cohort.
    for split, offset, at_risk in ((Split.TRAIN, 0, 100_000), (Split.HOLDOUT, 100, 40_000)):
        for dose_index, dose in enumerate((0.0, 1.0, 2.0)):
            for time_index, (start, end) in enumerate(((0.0, 1.0), (1.0, 3.0), (3.0, 6.0))):
                count = _event_count(dose, start, end, at_risk, generators[split])
                if split is Split.HOLDOUT:
                    count = min(at_risk - 1, max(1, round(count * holdout_scale)))
                number = offset + dose_index * 3 + time_index
                records.append(
                    IntervalCohortRecord(
                        record_id=f"{split.value.lower()}-record-{number}",
                        cohort_id=f"{split.value.lower()}-cohort-{number}",
                        dose=dose,
                        start_days=start,
                        end_days=end,
                        at_risk=at_risk,
                        events=count,
                        split=split,
                    )
                )
    return tuple(records)


def _spec(
    *,
    records: tuple[IntervalCohortRecord, ...] | None = None,
    protocol: FitProtocol | None = None,
    truth: GeneratorTruth | None = None,
) -> SurvivalCalibrationSpec:
    return SurvivalCalibrationSpec(
        target="synthetic independent-cohort all-cause interval events",
        dose_unit="synthetic dose unit",
        time_unit="day",
        dataset=SurvivalDataset.from_records(records or _records()),
        governance=_governance(),
        assembly=SurvivalAssembly(
            assembly_id="synthetic-lumped-assembly",
            components=("synthetic reserve", "synthetic event channel"),
            aggregation_rule="scientist-declared proxy aggregation only",
            scope="synthetic generator recovery; no biological interpretation",
        ),
        protocol=protocol or _protocol(),
        generator_truth=truth or _generator(),
    )


def test_golden_synthetic_generator_recovery_retains_interval_receipt_and_uncertainty():
    result = fit_synthetic_survival(_spec())

    assert result.status is FitStatus.SYNTHETIC_RECOVERY_PASSED
    assert result.fitted_parameters is not None
    assert result.recovery is not None and result.recovery.passed
    assert result.validation.value == "NOT_VALIDATED_FOR_BIOLOGY_OR_HUMAN_PREDICTION"
    assert result.fitted_parameters.lambda_days == pytest.approx(5.0, rel=0.03)
    assert result.fitted_parameters.shape_k == pytest.approx(1.35, rel=0.03)
    assert result.fitted_parameters.dose_coefficient_beta == pytest.approx(0.55, abs=0.03)
    assert len(result.predictions) == 18
    assert {prediction.split for prediction in result.predictions} == {Split.TRAIN, Split.HOLDOUT}
    assert len(result.intervals) == 3
    assert result.transformed_covariance is not None
    assert result.optimizer is not None
    assert result.optimizer.successful_start_count >= 2
    assert result.optimizer.information_rank == 3
    assert result.heldout_mean_negative_log_score is not None
    assert result.heldout_mean_negative_log_score > 0.0
    assert result.heldout_brier_score is not None
    assert 0.0 <= result.heldout_brier_score <= 1.0


def test_conditional_interval_probability_is_not_a_cumulative_binomial_probability():
    parameters = ParameterEstimate(4.0, 1.5, 0.4)
    record = IntervalCohortRecord("r", "c", 2.0, 1.0, 3.0, 100, 10, Split.TRAIN)
    actual = interval_event_probability(record, 1.0, parameters)
    exposure = math.exp(0.4 * 2.0)
    h0 = (1.0 / 4.0) ** 1.5 * exposure
    h1 = (3.0 / 4.0) ** 1.5 * exposure
    expected = 1.0 - math.exp(-(h1 - h0))
    cumulative_to_end = 1.0 - math.exp(-h1)

    assert actual == pytest.approx(expected)
    assert actual != pytest.approx(cumulative_to_end)
    assert IntervalCohortRecord("zero", "zero-c", 0.0, 0.0, 1.0, 100, 5, Split.TRAIN).dose == 0.0


def test_dataset_refuses_digest_count_split_and_independent_cohort_integrity_failures():
    dataset = SurvivalDataset.from_records(_records())
    with pytest.raises(ValueError, match="digest"):
        replace(dataset, declared_records_digest="d" * 64)
    with pytest.raises(ValueError, match="count"):
        replace(dataset, declared_record_count=dataset.declared_record_count + 1)
    with pytest.raises(ValueError, match="disjoint"):
        replace(dataset, declared_holdout_ids=(dataset.declared_train_ids[0],))

    records = list(_records())
    records[1] = replace(records[1], cohort_id=records[0].cohort_id)
    with pytest.raises(ValueError, match="independent cohort"):
        SurvivalDataset.from_records(tuple(records))

    class ForgedRecord(IntervalCohortRecord):
        pass

    forged = ForgedRecord("forged", "forged-c", 0.0, 0.0, 1.0, 100, 5, Split.TRAIN)
    with pytest.raises(TypeError, match="exact"):
        SurvivalDataset.from_records((forged, *dataset.records[1:]))


def test_design_and_governance_gates_reject_unsafe_or_unidentified_specs():
    records = tuple(
        replace(record, dose=1.0) if record.split is Split.TRAIN and record.dose == 0.0 else record
        for record in _records()
    )
    with pytest.raises(ValueError, match="three doses including zero"):
        _spec(records=records)

    one_horizon = tuple(
        replace(record, start_days=0.0, end_days=1.0)
        if record.split is Split.TRAIN
        else record
        for record in _records()
    )
    with pytest.raises(ValueError, match="three distinct positive interval ends"):
        _spec(records=one_horizon)

    spec = _spec()
    with pytest.raises(TypeError, match="DataAuthority"):
        replace(spec.governance, authority="ACTUAL_HUMAN")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Applicability"):
        replace(spec.governance, applicability="TRANSFER")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fixed synthetic interval-cohort target"):
        replace(spec, target="actual human mortality")


def test_holdout_mutation_changes_scores_but_never_train_fit_or_postfit_truth_assessment():
    baseline = fit_synthetic_survival(_spec())
    altered = fit_synthetic_survival(_spec(records=_records(holdout_scale=1.30)))

    assert baseline.fitted_parameters == altered.fitted_parameters
    assert baseline.recovery == altered.recovery
    assert baseline.heldout_mean_negative_log_score != altered.heldout_mean_negative_log_score
    assert baseline.heldout_brier_score != altered.heldout_brier_score


def test_truth_changes_only_postfit_recovery_assessment_not_objective_or_fit():
    baseline = fit_synthetic_survival(_spec())
    wrong_truth = _generator(ParameterEstimate(8.0, 0.7, -1.5))
    changed = fit_synthetic_survival(_spec(truth=wrong_truth))

    assert baseline.fitted_parameters == changed.fitted_parameters
    assert changed.status is FitStatus.SYNTHETIC_RECOVERY_FAILED
    assert changed.recovery is not None and not changed.recovery.passed


def test_fit_capability_structurally_excludes_holdout_and_generator_truth():
    spec = _spec()
    fit_input = SurvivalFitInput(spec.dataset.train_records, spec.protocol)

    assert not hasattr(fit_input, "generator_truth")
    assert not hasattr(fit_input, "holdout_records")
    with pytest.raises(ValueError, match="cannot contain HOLDOUT"):
        SurvivalFitInput(spec.dataset.holdout_records, spec.protocol)


def test_fixed_multistart_failure_returns_unstable_status_without_a_false_fit():
    result = fit_synthetic_survival(_spec(protocol=_protocol(maximum_iterations=1)))

    assert result.status is FitStatus.UNIDENTIFIED_OR_NUMERICALLY_UNSTABLE
    assert result.fitted_parameters is None
    assert result.transformed_covariance is None
    assert result.predictions == ()


def test_optimizer_success_flag_cannot_bypass_normalized_gradient_gate(monkeypatch):
    def false_success(_objective, start, **_kwargs):
        return SimpleNamespace(
            success=True,
            x=np.asarray((1.0, 0.0, 0.0)),
            fun=1.0,
            jac=np.asarray((1e-2, 0.0, 0.0)),
        )

    monkeypatch.setattr(domain_module, "minimize", false_success)
    result = fit_synthetic_survival(_spec())

    assert result.status is FitStatus.UNIDENTIFIED_OR_NUMERICALLY_UNSTABLE
    assert result.fitted_parameters is None
    assert "gradient gate" in result.detail
