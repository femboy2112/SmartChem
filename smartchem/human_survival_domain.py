"""Synthetic-only interval-cohort recovery for a Weibull survival proxy.

This module is compiler/runtime evidence, not human evidence.  It fits one fixed
Weibull proportional-hazards family to independent synthetic life-table intervals.
It deliberately excludes LD50/LC50 semantics, actual people or animals, causal
toxicology, individual predictions, and transfer outside the declared generator.

For a static synthetic dose ``d`` the cumulative hazard is

``H(t|d) = (t/lambda)**k * exp(beta*d/d_ref)``.

An independent cohort observed on ``[t0, t1]`` therefore has conditional event
probability ``q = 1 - exp(-(H(t1)-H(t0)))``.  Fitting uses the corresponding
binomial likelihood.  It never treats cumulative observations at several times as
independent binomials.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

from .contracts import canonical_digest

__all__ = [
    "Applicability",
    "DataAuthority",
    "FitProtocol",
    "SurvivalFitInput",
    "SurvivalFitResult",
    "FitStatus",
    "GeneratorTruth",
    "IntervalCohortRecord",
    "IntervalPrediction",
    "OptimizerDiagnostic",
    "ParameterEstimate",
    "ParameterInterval",
    "RecoveryAssessment",
    "Split",
    "SurvivalAssembly",
    "SurvivalCalibrationResult",
    "SurvivalCalibrationSpec",
    "SurvivalDataset",
    "SurvivalFamily",
    "SyntheticDataGovernance",
    "SyntheticValidationStatus",
    "TruthVisibility",
    "fit_synthetic_survival",
    "fit_synthetic_survival_model",
    "assess_synthetic_survival",
    "interval_event_probability",
]


class _Digestible:
    @property
    def digest(self) -> str:
        return canonical_digest(self)


class Split(str, Enum):
    TRAIN = "TRAIN"
    HOLDOUT = "HOLDOUT"


class DataAuthority(str, Enum):
    SYNTHETIC_ONLY = "SYNTHETIC_ONLY"


class Applicability(str, Enum):
    DECLARED_GENERATOR_RECOVERY_ONLY = "DECLARED_GENERATOR_RECOVERY_ONLY"


class TruthVisibility(str, Enum):
    POST_FIT_RECOVERY_ASSESSMENT_ONLY = "POST_FIT_RECOVERY_ASSESSMENT_ONLY"


class SurvivalFamily(str, Enum):
    WEIBULL_PROPORTIONAL_HAZARDS = "WEIBULL_PROPORTIONAL_HAZARDS"


class SyntheticValidationStatus(str, Enum):
    NOT_VALIDATED_FOR_BIOLOGY_OR_HUMAN_PREDICTION = (
        "NOT_VALIDATED_FOR_BIOLOGY_OR_HUMAN_PREDICTION"
    )


class FitStatus(str, Enum):
    TRAIN_FIT_IDENTIFIED = "TRAIN_FIT_IDENTIFIED"
    SYNTHETIC_RECOVERY_PASSED = "SYNTHETIC_RECOVERY_PASSED"
    SYNTHETIC_RECOVERY_FAILED = "SYNTHETIC_RECOVERY_FAILED"
    UNIDENTIFIED_OR_NUMERICALLY_UNSTABLE = (
        "UNIDENTIFIED_OR_NUMERICALLY_UNSTABLE"
    )


@dataclass(frozen=True)
class ParameterEstimate(_Digestible):
    lambda_days: float
    shape_k: float
    dose_coefficient_beta: float

    def __post_init__(self) -> None:
        _positive("lambda_days", self.lambda_days)
        _positive("shape_k", self.shape_k)
        _finite("dose_coefficient_beta", self.dose_coefficient_beta)
        object.__setattr__(self, "lambda_days", float(self.lambda_days))
        object.__setattr__(self, "shape_k", float(self.shape_k))
        object.__setattr__(
            self, "dose_coefficient_beta", float(self.dose_coefficient_beta)
        )


@dataclass(frozen=True)
class GeneratorTruth(_Digestible):
    """Known only to the post-fit synthetic recovery assessment."""

    generator_id: str
    generator_version_digest: str
    parameters: ParameterEstimate
    visibility: TruthVisibility = TruthVisibility.POST_FIT_RECOVERY_ASSESSMENT_ONLY

    def __post_init__(self) -> None:
        _text("generator_id", self.generator_id)
        _digest("generator_version_digest", self.generator_version_digest)
        _exact("parameters", self.parameters, ParameterEstimate)
        _enum("visibility", self.visibility, TruthVisibility)


@dataclass(frozen=True)
class SyntheticDataGovernance(_Digestible):
    authority: DataAuthority
    applicability: Applicability
    generator_id: str
    generator_version_digest: str
    train_generation_digest: str
    holdout_generation_digest: str
    train_seed: int
    holdout_seed: int
    provenance: str
    no_transfer_clause: str

    def __post_init__(self) -> None:
        _enum("authority", self.authority, DataAuthority)
        _enum("applicability", self.applicability, Applicability)
        _text("generator_id", self.generator_id)
        for name in (
            "generator_version_digest",
            "train_generation_digest",
            "holdout_generation_digest",
        ):
            _digest(name, getattr(self, name))
        if self.train_generation_digest == self.holdout_generation_digest:
            raise ValueError("TRAIN and HOLDOUT generation identities must differ")
        if type(self.train_seed) is not int or type(self.holdout_seed) is not int:
            raise TypeError("TRAIN and HOLDOUT seeds must be exact integers")
        if self.train_seed < 0 or self.holdout_seed < 0:
            raise ValueError("TRAIN and HOLDOUT seeds must be non-negative")
        if self.train_seed == self.holdout_seed:
            raise ValueError("TRAIN and HOLDOUT seeds must differ")
        _text("provenance", self.provenance)
        _text("no_transfer_clause", self.no_transfer_clause)


@dataclass(frozen=True)
class IntervalCohortRecord(_Digestible):
    """One independent synthetic cohort observed over one time interval."""

    record_id: str
    cohort_id: str
    dose: float
    start_days: float
    end_days: float
    at_risk: int
    events: int
    split: Split

    def __post_init__(self) -> None:
        _text("record_id", self.record_id)
        _text("cohort_id", self.cohort_id)
        _nonnegative("dose", self.dose)
        _nonnegative("start_days", self.start_days)
        _positive("end_days", self.end_days)
        if self.end_days <= self.start_days:
            raise ValueError("end_days must be greater than start_days")
        if type(self.at_risk) is not int or self.at_risk < 1:
            raise ValueError("at_risk must be a positive integer")
        if type(self.events) is not int or not 0 <= self.events <= self.at_risk:
            raise ValueError("events must be an integer in [0, at_risk]")
        _enum("split", self.split, Split)
        object.__setattr__(self, "dose", float(self.dose))
        object.__setattr__(self, "start_days", float(self.start_days))
        object.__setattr__(self, "end_days", float(self.end_days))


@dataclass(frozen=True)
class SurvivalDataset(_Digestible):
    records: tuple[IntervalCohortRecord, ...]
    declared_records_digest: str
    declared_record_count: int
    declared_train_ids: tuple[str, ...]
    declared_holdout_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple) or not self.records:
            raise TypeError("records must be a non-empty tuple")
        if any(type(item) is not IntervalCohortRecord for item in self.records):
            raise TypeError("records must contain exact IntervalCohortRecord values")
        _digest("declared_records_digest", self.declared_records_digest)
        if self.declared_records_digest != canonical_digest(self.records):
            raise ValueError("declared_records_digest does not match records")
        if (
            type(self.declared_record_count) is not int
            or self.declared_record_count != len(self.records)
        ):
            raise ValueError("declared_record_count must exactly match records")
        record_ids = tuple(item.record_id for item in self.records)
        cohort_ids = tuple(item.cohort_id for item in self.records)
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("record IDs must be unique")
        if len(cohort_ids) != len(set(cohort_ids)):
            raise ValueError(
                "each record must be an independent cohort with a unique cohort ID"
            )
        _ids("declared_train_ids", self.declared_train_ids)
        _ids("declared_holdout_ids", self.declared_holdout_ids)
        if set(self.declared_train_ids) & set(self.declared_holdout_ids):
            raise ValueError("TRAIN and HOLDOUT record IDs must be disjoint")
        train_ids = tuple(
            item.record_id for item in self.records if item.split is Split.TRAIN
        )
        holdout_ids = tuple(
            item.record_id for item in self.records if item.split is Split.HOLDOUT
        )
        if self.declared_train_ids != train_ids:
            raise ValueError("declared_train_ids must exactly match record order")
        if self.declared_holdout_ids != holdout_ids:
            raise ValueError("declared_holdout_ids must exactly match record order")
        if not train_ids or not holdout_ids:
            raise ValueError("dataset requires non-empty TRAIN and HOLDOUT splits")

    @classmethod
    def from_records(
        cls, records: tuple[IntervalCohortRecord, ...]
    ) -> "SurvivalDataset":
        return cls(
            records=records,
            declared_records_digest=canonical_digest(records),
            declared_record_count=len(records),
            declared_train_ids=tuple(
                item.record_id for item in records if item.split is Split.TRAIN
            ),
            declared_holdout_ids=tuple(
                item.record_id for item in records if item.split is Split.HOLDOUT
            ),
        )

    @property
    def train_records(self) -> tuple[IntervalCohortRecord, ...]:
        return tuple(item for item in self.records if item.split is Split.TRAIN)

    @property
    def holdout_records(self) -> tuple[IntervalCohortRecord, ...]:
        return tuple(item for item in self.records if item.split is Split.HOLDOUT)


@dataclass(frozen=True)
class SurvivalAssembly(_Digestible):
    assembly_id: str
    components: tuple[str, ...]
    aggregation_rule: str
    scope: str

    def __post_init__(self) -> None:
        _text("assembly_id", self.assembly_id)
        _ids("components", self.components)
        _text("aggregation_rule", self.aggregation_rule)
        _text("scope", self.scope)


@dataclass(frozen=True)
class FitProtocol(_Digestible):
    family: SurvivalFamily
    dose_reference: float
    transformed_bounds: tuple[tuple[float, float], ...]
    transformed_starts: tuple[tuple[float, float, float], ...]
    maximum_iterations: int
    gradient_tolerance: float
    objective_agreement_tolerance: float
    parameter_agreement_tolerance: float
    hessian_step: float
    maximum_information_condition: float
    recovery_relative_tolerance: float
    recovery_beta_absolute_tolerance: float

    def __post_init__(self) -> None:
        _enum("family", self.family, SurvivalFamily)
        _positive("dose_reference", self.dose_reference)
        if (
            not isinstance(self.transformed_bounds, tuple)
            or len(self.transformed_bounds) != 3
        ):
            raise TypeError("transformed_bounds must contain three (lower, upper) pairs")
        for lower, upper in self.transformed_bounds:
            _finite("bound lower", lower)
            _finite("bound upper", upper)
            if lower >= upper:
                raise ValueError("every transformed lower bound must be below its upper")
        if (
            not isinstance(self.transformed_starts, tuple)
            or len(self.transformed_starts) < 3
        ):
            raise ValueError("at least three fixed transformed starts are required")
        for start in self.transformed_starts:
            if not isinstance(start, tuple) or len(start) != 3:
                raise TypeError("every transformed start must contain three values")
            for value, (lower, upper) in zip(start, self.transformed_bounds):
                _finite("transformed start", value)
                if not lower < value < upper:
                    raise ValueError("every transformed start must lie inside its bounds")
        if type(self.maximum_iterations) is not int or self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be a positive integer")
        for name in (
            "gradient_tolerance",
            "objective_agreement_tolerance",
            "parameter_agreement_tolerance",
            "hessian_step",
            "maximum_information_condition",
            "recovery_relative_tolerance",
            "recovery_beta_absolute_tolerance",
        ):
            _positive(name, getattr(self, name))


@dataclass(frozen=True)
class SurvivalCalibrationSpec(_Digestible):
    target: str
    dose_unit: str
    time_unit: str
    dataset: SurvivalDataset
    governance: SyntheticDataGovernance
    assembly: SurvivalAssembly
    protocol: FitProtocol
    generator_truth: GeneratorTruth

    def __post_init__(self) -> None:
        if self.target != "synthetic independent-cohort all-cause interval events":
            raise ValueError("only the fixed synthetic interval-cohort target is supported")
        if self.dose_unit != "synthetic dose unit" or self.time_unit != "day":
            raise ValueError("this executor supports only synthetic dose units and days")
        _exact("dataset", self.dataset, SurvivalDataset)
        _exact("governance", self.governance, SyntheticDataGovernance)
        _exact("assembly", self.assembly, SurvivalAssembly)
        _exact("protocol", self.protocol, FitProtocol)
        _exact("generator_truth", self.generator_truth, GeneratorTruth)
        if self.governance.generator_id != self.generator_truth.generator_id:
            raise ValueError("governance and post-fit truth must name the same generator")
        if (
            self.governance.generator_version_digest
            != self.generator_truth.generator_version_digest
        ):
            raise ValueError("governance and post-fit truth version digests differ")
        _design_error(self.dataset.train_records)


@dataclass(frozen=True)
class ParameterInterval(_Digestible):
    parameter: str
    lower: float
    upper: float
    method: str

    def __post_init__(self) -> None:
        _text("parameter", self.parameter)
        _finite("lower", self.lower)
        _finite("upper", self.upper)
        if self.lower > self.upper:
            raise ValueError("interval lower must not exceed upper")
        if self.method != (
            "conditional likelihood-curvature interval in transformed coordinates"
        ):
            raise ValueError("unsupported interval method")


@dataclass(frozen=True)
class IntervalPrediction(_Digestible):
    record_id: str
    record_digest: str
    split: Split
    predicted_event_probability: float
    observed_event_fraction: float
    negative_log_score: float
    brier_score: float

    def __post_init__(self) -> None:
        _text("record_id", self.record_id)
        _digest("record_digest", self.record_digest)
        _enum("split", self.split, Split)
        for name in (
            "predicted_event_probability",
            "observed_event_fraction",
            "negative_log_score",
            "brier_score",
        ):
            _finite(name, getattr(self, name))
        if not 0.0 < self.predicted_event_probability < 1.0:
            raise ValueError("predicted_event_probability must be in (0, 1)")


@dataclass(frozen=True)
class OptimizerDiagnostic(_Digestible):
    successful_start_count: int
    objective_values: tuple[float, ...]
    maximum_gradient_norm: float
    maximum_parameter_disagreement: float
    information_rank: int
    information_condition_number: float
    transformed_coordinate_order: tuple[str, ...]


@dataclass(frozen=True)
class SurvivalFitInput(_Digestible):
    """The only capability given to the fitter: TRAIN records and fit protocol."""

    train_records: tuple[IntervalCohortRecord, ...]
    protocol: FitProtocol

    def __post_init__(self) -> None:
        if (
            not isinstance(self.train_records, tuple)
            or any(type(item) is not IntervalCohortRecord for item in self.train_records)
        ):
            raise TypeError("train_records must contain exact IntervalCohortRecord values")
        if any(item.split is not Split.TRAIN for item in self.train_records):
            raise ValueError("SurvivalFitInput cannot contain HOLDOUT records")
        _exact("protocol", self.protocol, FitProtocol)
        _design_error(self.train_records)


@dataclass(frozen=True)
class SurvivalFitResult(_Digestible):
    """Fit-only output; it contains no HOLDOUT records or generator truth."""

    fit_input_digest: str
    status: FitStatus
    fitted_parameters: ParameterEstimate | None
    transformed_covariance: tuple[tuple[float, ...], ...] | None
    intervals: tuple[ParameterInterval, ...]
    optimizer: OptimizerDiagnostic | None
    detail: str

    def __post_init__(self) -> None:
        _digest("fit_input_digest", self.fit_input_digest)
        _enum("status", self.status, FitStatus)
        _text("detail", self.detail)
        fitted = self.fitted_parameters is not None
        if fitted != (self.transformed_covariance is not None):
            raise ValueError("fit and covariance must be present or absent together")
        if fitted != bool(self.intervals):
            raise ValueError("fit and intervals must be present or absent together")
        if fitted != (self.optimizer is not None):
            raise ValueError("fit and optimizer diagnostics must be present together")
        if fitted and self.status is not FitStatus.TRAIN_FIT_IDENTIFIED:
            raise ValueError("a fit-only parameter result requires TRAIN_FIT_IDENTIFIED")
        if not fitted and self.status is not FitStatus.UNIDENTIFIED_OR_NUMERICALLY_UNSTABLE:
            raise ValueError("a recovery status requires a fitted model")


@dataclass(frozen=True)
class RecoveryAssessment(_Digestible):
    truth: GeneratorTruth
    lambda_relative_error: float
    shape_relative_error: float
    beta_absolute_error: float
    passed: bool


@dataclass(frozen=True)
class SurvivalCalibrationResult(_Digestible):
    spec_digest: str
    dataset_digest: str
    status: FitStatus
    validation: SyntheticValidationStatus
    fitted_parameters: ParameterEstimate | None
    transformed_covariance: tuple[tuple[float, ...], ...] | None
    intervals: tuple[ParameterInterval, ...]
    predictions: tuple[IntervalPrediction, ...]
    heldout_mean_negative_log_score: float | None
    heldout_brier_score: float | None
    optimizer: OptimizerDiagnostic | None
    recovery: RecoveryAssessment | None
    detail: str

    def __post_init__(self) -> None:
        _digest("spec_digest", self.spec_digest)
        _digest("dataset_digest", self.dataset_digest)
        _enum("status", self.status, FitStatus)
        _enum("validation", self.validation, SyntheticValidationStatus)
        _text("detail", self.detail)
        fitted = self.fitted_parameters is not None
        if fitted != (self.transformed_covariance is not None):
            raise ValueError("fit and covariance must be present or absent together")
        if fitted != bool(self.intervals):
            raise ValueError("fit and intervals must be present or absent together")
        if fitted != bool(self.predictions):
            raise ValueError("fit and predictions must be present or absent together")
        if fitted != (self.optimizer is not None) or fitted != (self.recovery is not None):
            raise ValueError("fit diagnostics must be present exactly with a fit")
        if fitted != (self.heldout_mean_negative_log_score is not None):
            raise ValueError("heldout scores must be present exactly with a fit")
        if fitted != (self.heldout_brier_score is not None):
            raise ValueError("heldout scores must be present exactly with a fit")


def interval_event_probability(
    record: IntervalCohortRecord,
    dose_reference: float,
    parameters: ParameterEstimate,
) -> float:
    """Return the fixed-family conditional interval event probability."""
    _exact("record", record, IntervalCohortRecord)
    _positive("dose_reference", dose_reference)
    _exact("parameters", parameters, ParameterEstimate)
    exposure = math.exp(parameters.dose_coefficient_beta * record.dose / dose_reference)
    h0 = (
        (record.start_days / parameters.lambda_days) ** parameters.shape_k
        if record.start_days > 0.0
        else 0.0
    ) * exposure
    h1 = (record.end_days / parameters.lambda_days) ** parameters.shape_k * exposure
    delta = h1 - h0
    if not math.isfinite(delta) or delta <= 0.0:
        raise ValueError("declared parameters produce no finite positive interval hazard")
    probability = -math.expm1(-delta)
    return min(max(probability, np.finfo(float).eps), 1.0 - np.finfo(float).eps)


def fit_synthetic_survival_model(
    fit_input: SurvivalFitInput,
) -> SurvivalFitResult:
    """Fit the train-only capability; HOLDOUT and generator truth are inaccessible."""
    _exact("fit_input", fit_input, SurvivalFitInput)
    train = fit_input.train_records
    protocol = fit_input.protocol
    bounds = tuple(tuple(map(float, pair)) for pair in protocol.transformed_bounds)
    successes: list[object] = []
    for start in protocol.transformed_starts:
        result = minimize(
            _negative_log_likelihood,
            np.asarray(start, dtype=float),
            args=(train, protocol.dose_reference, True),
            method="L-BFGS-B",
            bounds=bounds,
            options={
                "maxiter": protocol.maximum_iterations,
                "gtol": protocol.gradient_tolerance,
                "ftol": 10.0 * np.finfo(float).eps,
                "maxls": 50,
            },
        )
        if (
            result.success
            and np.all(np.isfinite(result.x))
            and math.isfinite(float(result.fun))
            and np.all(np.isfinite(result.jac))
        ):
            successes.append(result)
    if len(successes) < 2:
        return _unfitted_fit(fit_input, "fewer than two fixed starts converged")
    successes.sort(key=lambda item: float(item.fun))
    best = successes[0]
    objectives = tuple(float(item.fun) for item in successes)
    objective_spread = max(objectives) - min(objectives)
    if objective_spread > protocol.objective_agreement_tolerance:
        return _unfitted_fit(
            fit_input, "fixed starts disagree on the mean likelihood objective"
        )
    parameter_disagreement = max(
        float(np.max(np.abs(np.asarray(item.x) - np.asarray(best.x))))
        for item in successes
    )
    if parameter_disagreement > protocol.parameter_agreement_tolerance:
        return _unfitted_fit(
            fit_input, "fixed starts converge to materially different parameters"
        )
    gradient_norms = tuple(
        float(np.linalg.norm(item.jac, ord=np.inf)) for item in successes
    )
    gradient_gate = max(
        protocol.gradient_tolerance,
        math.sqrt(np.finfo(float).eps),
    )
    if max(gradient_norms) > gradient_gate:
        return _unfitted_fit(
            fit_input,
            (
                "fixed starts did not satisfy the normalized score-gradient gate: "
                f"maximum={max(gradient_norms):.12g}, gate={gradient_gate:.12g}"
            ),
        )
    for value, (lower, upper) in zip(best.x, bounds):
        margin = 1e-7 * max(1.0, abs(lower), abs(upper))
        if value <= lower + margin or value >= upper - margin:
            return _unfitted_fit(
                fit_input, "best fit lies on a declared parameter bound"
            )
    information = _finite_hessian(
        lambda vector: _negative_log_likelihood(
            vector, train, protocol.dose_reference, False
        ),
        np.asarray(best.x, dtype=float),
        protocol.hessian_step,
    )
    if not np.all(np.isfinite(information)):
        return _unfitted_fit(fit_input, "conditional likelihood curvature is nonfinite")
    rank = int(np.linalg.matrix_rank(information))
    eigenvalues = np.linalg.eigvalsh(information)
    if rank != 3 or np.min(eigenvalues) <= 0.0:
        return _unfitted_fit(
            fit_input,
            "conditional likelihood curvature is not positive definite/full rank",
        )
    condition = float(np.linalg.cond(information))
    if (
        not math.isfinite(condition)
        or condition > protocol.maximum_information_condition
    ):
        return _unfitted_fit(
            fit_input, "conditional likelihood curvature is too ill-conditioned"
        )
    covariance = np.linalg.inv(information)
    if not np.all(np.isfinite(covariance)):
        return _unfitted_fit(
            fit_input, "conditional likelihood-curvature covariance is nonfinite"
        )
    fitted = ParameterEstimate(
        lambda_days=math.exp(float(best.x[0])),
        shape_k=math.exp(float(best.x[1])),
        dose_coefficient_beta=float(best.x[2]),
    )
    intervals = _intervals(fitted, covariance)
    optimizer = OptimizerDiagnostic(
        successful_start_count=len(successes),
        objective_values=objectives,
        maximum_gradient_norm=max(gradient_norms),
        maximum_parameter_disagreement=parameter_disagreement,
        information_rank=rank,
        information_condition_number=condition,
        transformed_coordinate_order=("log(lambda_days)", "log(shape_k)", "beta"),
    )
    return SurvivalFitResult(
        fit_input_digest=fit_input.digest,
        status=FitStatus.TRAIN_FIT_IDENTIFIED,
        fitted_parameters=fitted,
        transformed_covariance=tuple(
            tuple(float(value) for value in row) for row in covariance
        ),
        intervals=intervals,
        optimizer=optimizer,
        detail=(
            "TRAIN-only fixed-family fit passed start, normalized-gradient, bound, "
            "rank, positive-curvature, and conditioning gates"
        ),
    )


def assess_synthetic_survival(
    spec: SurvivalCalibrationSpec,
    fit: SurvivalFitResult,
) -> SurvivalCalibrationResult:
    """Score HOLDOUT and compare generator truth only after a train-only fit."""
    _exact("spec", spec, SurvivalCalibrationSpec)
    _exact("fit", fit, SurvivalFitResult)
    fit_input = SurvivalFitInput(spec.dataset.train_records, spec.protocol)
    if fit.fit_input_digest != fit_input.digest:
        raise ValueError("fit result is not bound to this specification's TRAIN input")
    if fit.fitted_parameters is None:
        return _unfitted(spec, fit.detail)
    fitted = fit.fitted_parameters
    protocol = spec.protocol
    predictions = tuple(
        _prediction(item, protocol.dose_reference, fitted)
        for item in spec.dataset.records
    )
    heldout = tuple(item for item in predictions if item.split is Split.HOLDOUT)
    heldout_records = spec.dataset.holdout_records
    total_at_risk = sum(item.at_risk for item in heldout_records)
    mean_log = sum(item.negative_log_score for item in heldout) / total_at_risk
    brier = sum(
        item.brier_score * record.at_risk
        for item, record in zip(heldout, heldout_records)
    ) / total_at_risk
    truth = spec.generator_truth.parameters
    recovery = RecoveryAssessment(
        truth=spec.generator_truth,
        lambda_relative_error=abs(fitted.lambda_days - truth.lambda_days)
        / truth.lambda_days,
        shape_relative_error=abs(fitted.shape_k - truth.shape_k) / truth.shape_k,
        beta_absolute_error=abs(
            fitted.dose_coefficient_beta - truth.dose_coefficient_beta
        ),
        passed=False,
    )
    passed = (
        recovery.lambda_relative_error <= protocol.recovery_relative_tolerance
        and recovery.shape_relative_error <= protocol.recovery_relative_tolerance
        and recovery.beta_absolute_error
        <= protocol.recovery_beta_absolute_tolerance
    )
    recovery = RecoveryAssessment(
        truth=recovery.truth,
        lambda_relative_error=recovery.lambda_relative_error,
        shape_relative_error=recovery.shape_relative_error,
        beta_absolute_error=recovery.beta_absolute_error,
        passed=passed,
    )
    return SurvivalCalibrationResult(
        spec_digest=spec.digest,
        dataset_digest=spec.dataset.declared_records_digest,
        status=(
            FitStatus.SYNTHETIC_RECOVERY_PASSED
            if passed
            else FitStatus.SYNTHETIC_RECOVERY_FAILED
        ),
        validation=SyntheticValidationStatus.NOT_VALIDATED_FOR_BIOLOGY_OR_HUMAN_PREDICTION,
        fitted_parameters=fitted,
        transformed_covariance=fit.transformed_covariance,
        intervals=fit.intervals,
        predictions=predictions,
        heldout_mean_negative_log_score=float(mean_log),
        heldout_brier_score=float(brier),
        optimizer=fit.optimizer,
        recovery=recovery,
        detail=(
            "the fitter received only TRAIN interval cohorts and the fixed protocol; "
            "HOLDOUT scoring and generator-truth recovery were separate post-fit steps"
        ),
    )


def fit_synthetic_survival(spec: SurvivalCalibrationSpec) -> SurvivalCalibrationResult:
    """Convenience composition of the structurally separated fit and assessment."""
    _exact("spec", spec, SurvivalCalibrationSpec)
    fit_input = SurvivalFitInput(spec.dataset.train_records, spec.protocol)
    return assess_synthetic_survival(
        spec,
        fit_synthetic_survival_model(fit_input),
    )


def _negative_log_likelihood(
    transformed: np.ndarray,
    records: tuple[IntervalCohortRecord, ...],
    dose_reference: float,
    normalize: bool,
) -> float:
    try:
        parameters = ParameterEstimate(
            math.exp(float(transformed[0])),
            math.exp(float(transformed[1])),
            float(transformed[2]),
        )
        total = 0.0
        for record in records:
            q = interval_event_probability(record, dose_reference, parameters)
            total -= (
                gammaln(record.at_risk + 1)
                - gammaln(record.events + 1)
                - gammaln(record.at_risk - record.events + 1)
                + record.events * math.log(q)
                + (record.at_risk - record.events) * math.log1p(-q)
            )
        if normalize:
            total /= sum(record.at_risk for record in records)
        return float(total)
    except (OverflowError, ValueError):
        return float(np.finfo(float).max / 1000.0)


def _finite_hessian(function: object, point: np.ndarray, step: float) -> np.ndarray:
    size = len(point)
    result = np.empty((size, size), dtype=float)
    f0 = function(point)
    for i in range(size):
        ei = np.zeros(size)
        ei[i] = step
        result[i, i] = (function(point + ei) - 2.0 * f0 + function(point - ei)) / (
            step**2
        )
        for j in range(i + 1, size):
            ej = np.zeros(size)
            ej[j] = step
            value = (
                function(point + ei + ej)
                - function(point + ei - ej)
                - function(point - ei + ej)
                + function(point - ei - ej)
            ) / (4.0 * step**2)
            result[i, j] = result[j, i] = value
    return 0.5 * (result + result.T)


def _prediction(
    record: IntervalCohortRecord,
    dose_reference: float,
    fitted: ParameterEstimate,
) -> IntervalPrediction:
    q = interval_event_probability(record, dose_reference, fitted)
    failures = record.at_risk - record.events
    negative_log_score = -(
        record.events * math.log(q) + failures * math.log1p(-q)
    )
    brier = (
        record.events * (1.0 - q) ** 2 + failures * q**2
    ) / record.at_risk
    return IntervalPrediction(
        record_id=record.record_id,
        record_digest=record.digest,
        split=record.split,
        predicted_event_probability=q,
        observed_event_fraction=record.events / record.at_risk,
        negative_log_score=negative_log_score,
        brier_score=brier,
    )


def _intervals(
    fitted: ParameterEstimate, covariance: np.ndarray
) -> tuple[ParameterInterval, ...]:
    standard_errors = np.sqrt(np.diag(covariance))
    return (
        ParameterInterval(
            "lambda_days",
            math.exp(math.log(fitted.lambda_days) - 1.96 * standard_errors[0]),
            math.exp(math.log(fitted.lambda_days) + 1.96 * standard_errors[0]),
            "conditional likelihood-curvature interval in transformed coordinates",
        ),
        ParameterInterval(
            "shape_k",
            math.exp(math.log(fitted.shape_k) - 1.96 * standard_errors[1]),
            math.exp(math.log(fitted.shape_k) + 1.96 * standard_errors[1]),
            "conditional likelihood-curvature interval in transformed coordinates",
        ),
        ParameterInterval(
            "dose_coefficient_beta",
            fitted.dose_coefficient_beta - 1.96 * standard_errors[2],
            fitted.dose_coefficient_beta + 1.96 * standard_errors[2],
            "conditional likelihood-curvature interval in transformed coordinates",
        ),
    )


def _unfitted_fit(
    fit_input: SurvivalFitInput,
    detail: str,
) -> SurvivalFitResult:
    return SurvivalFitResult(
        fit_input_digest=fit_input.digest,
        status=FitStatus.UNIDENTIFIED_OR_NUMERICALLY_UNSTABLE,
        fitted_parameters=None,
        transformed_covariance=None,
        intervals=(),
        optimizer=None,
        detail=detail,
    )


def _unfitted(
    spec: SurvivalCalibrationSpec, detail: str
) -> SurvivalCalibrationResult:
    return SurvivalCalibrationResult(
        spec_digest=spec.digest,
        dataset_digest=spec.dataset.declared_records_digest,
        status=FitStatus.UNIDENTIFIED_OR_NUMERICALLY_UNSTABLE,
        validation=SyntheticValidationStatus.NOT_VALIDATED_FOR_BIOLOGY_OR_HUMAN_PREDICTION,
        fitted_parameters=None,
        transformed_covariance=None,
        intervals=(),
        predictions=(),
        heldout_mean_negative_log_score=None,
        heldout_brier_score=None,
        optimizer=None,
        recovery=None,
        detail=detail,
    )


def _design_error(records: tuple[IntervalCohortRecord, ...]) -> None:
    doses = {item.dose for item in records}
    ends = {item.end_days for item in records}
    if 0.0 not in doses or len(doses) < 3:
        raise ValueError("TRAIN requires at least three doses including zero")
    if len(ends) < 3:
        raise ValueError("TRAIN requires at least three distinct positive interval ends")
    if len(records) < 9:
        raise ValueError("TRAIN requires at least nine independent cohort intervals")
    if any(item.events in (0, item.at_risk) for item in records):
        raise ValueError("TRAIN event counts must be interior to avoid boundary-only fits")


def _exact(name: str, value: object, expected: type[object]) -> None:
    if type(value) is not expected:
        raise TypeError(f"{name} must be an exact {expected.__name__}")


def _enum(name: str, value: object, expected: type[Enum]) -> None:
    if type(value) is not expected:
        raise TypeError(f"{name} must be an exact {expected.__name__}")


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _finite(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real value")


def _positive(name: str, value: object) -> None:
    _finite(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _nonnegative(name: str, value: object) -> None:
    _finite(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _digest(name: str, value: object) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{name} must be a SHA-256 hex digest") from error


def _ids(name: str, values: object) -> None:
    if (
        not isinstance(values, tuple)
        or not values
        or any(not isinstance(item, str) or not item for item in values)
    ):
        raise TypeError(f"{name} must be a non-empty tuple of strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must contain unique values")
