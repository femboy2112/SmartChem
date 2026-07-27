"""Run the synthetic-only Weibull interval-cohort recovery vertical.

The fixture uses independent deterministic synthetic cohorts.  TRAIN records fit one
preselected family; a disjoint HOLDOUT split is scored afterward.  The known generator
is consulted only for the post-fit recovery assessment.  Nothing here is human,
animal, clinical, toxicological, causal, or LD50/LC50 evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from smartchem import (
    COMPILED,
    InferenceKind,
    IntervalCohortRecord,
    SourceProgram,
    Spec,
    SyntheticDataGovernance,
    SyntheticSurvivalApplicability,
    SyntheticSurvivalAssembly,
    SyntheticSurvivalCalibrationSpec,
    SyntheticSurvivalDataAuthority,
    SyntheticSurvivalDataset,
    SyntheticSurvivalFamily,
    SyntheticSurvivalFitProtocol,
    SyntheticSurvivalGeneratorTruth,
    SyntheticSurvivalParameterEstimate,
    SyntheticSurvivalRecoveryEngine,
    SyntheticSurvivalSplit,
    approve,
    compile_session_human_survival_recovery,
    execute,
    human_survival_slot,
    interval_event_probability,
    record_approval,
    shepherd,
)


DEFAULT_JOURNAL = Path(__file__).with_name("compiled_human_survival_run.json")
TRUTH = SyntheticSurvivalParameterEstimate(100.0, 2.0, 0.5)
TRAIN_SEED = 271828
HOLDOUT_SEED = 314159


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(
    record_id: str,
    dose: float,
    end_days: float,
    split: SyntheticSurvivalSplit,
    at_risk: int,
    rng: np.random.Generator,
) -> IntervalCohortRecord:
    shell = IntervalCohortRecord(
        record_id,
        f"cohort-{record_id}",
        dose,
        0.0,
        end_days,
        at_risk,
        1,
        split,
    )
    probability = interval_event_probability(shell, 1.0, TRUTH)
    events = int(rng.binomial(at_risk, probability))
    return IntervalCohortRecord(
        record_id,
        f"cohort-{record_id}",
        dose,
        0.0,
        end_days,
        at_risk,
        events,
        split,
    )


def build_spec() -> SyntheticSurvivalCalibrationSpec:
    train_rng = np.random.default_rng(TRAIN_SEED)
    holdout_rng = np.random.default_rng(HOLDOUT_SEED)
    records = tuple(
        _record(
            f"train-d{dose}-t{time}",
            dose,
            time,
            SyntheticSurvivalSplit.TRAIN,
            10_000,
            train_rng,
        )
        for dose in (0.0, 1.0, 2.0)
        for time in (30.0, 60.0, 100.0)
    ) + tuple(
        _record(
            f"holdout-d{dose}-t{time}",
            dose,
            time,
            SyntheticSurvivalSplit.HOLDOUT,
            4_000,
            holdout_rng,
        )
        for dose in (0.0, 1.0, 2.0)
        for time in (45.0, 80.0)
    )
    generator_digest = _digest("smartchem-synthetic-weibull-generator-v1")
    return SyntheticSurvivalCalibrationSpec(
        target="synthetic independent-cohort all-cause interval events",
        dose_unit="synthetic dose unit",
        time_unit="day",
        dataset=SyntheticSurvivalDataset.from_records(records),
        governance=SyntheticDataGovernance(
            SyntheticSurvivalDataAuthority.SYNTHETIC_ONLY,
            SyntheticSurvivalApplicability.DECLARED_GENERATOR_RECOVERY_ONLY,
            "smartchem-synthetic-weibull-v1",
            generator_digest,
            _digest("locked-train-generation-v1"),
            _digest("locked-holdout-generation-v1"),
            TRAIN_SEED,
            HOLDOUT_SEED,
            "seeded binomial synthetic independent-cohort fixture",
            (
                "No transfer to any human, animal, material, toxicological endpoint, "
                "causal mechanism, clinical claim, or safety decision."
            ),
        ),
        assembly=SyntheticSurvivalAssembly(
            "synthetic-independent-cohorts",
            ("static synthetic dose", "all-cause synthetic interval event"),
            "independent conditional-binomial interval cohorts",
            "same-generator synthetic recovery only",
        ),
        protocol=SyntheticSurvivalFitProtocol(
            SyntheticSurvivalFamily.WEIBULL_PROPORTIONAL_HAZARDS,
            1.0,
            (
                (math.log(10.0), math.log(1_000.0)),
                (math.log(0.2), math.log(5.0)),
                (-3.0, 3.0),
            ),
            (
                (math.log(80.0), math.log(1.5), 0.0),
                (math.log(120.0), math.log(2.5), 0.8),
                (math.log(200.0), math.log(0.8), -0.5),
            ),
            1_000,
            1e-8,
            1e-5,
            1e-4,
            1e-4,
            1e8,
            0.03,
            0.05,
        ),
        generator_truth=SyntheticSurvivalGeneratorTruth(
            "smartchem-synthetic-weibull-v1",
            generator_digest,
            TRUTH,
        ),
    )


def compile_plan(engine: SyntheticSurvivalRecoveryEngine):
    source = SourceProgram(
        (
            "Fit the preselected Weibull proportional-hazards family to these "
            "content-addressed independent synthetic interval cohorts using TRAIN only. "
            "Score every locked HOLDOUT cohort and retain the full uncertainty and "
            "optimizer diagnostics. Use generator truth only after fitting. Do not "
            "interpret this as human, biological, toxicological, causal, LD50/LC50, "
            "clinical, regulatory, or safety evidence."
        ),
        (
            "preselected Weibull proportional-hazards family",
            "independent synthetic interval cohorts",
            "TRAIN only",
            "locked HOLDOUT",
            "generator truth only after fitting",
            "no human or biological transfer",
        ),
        "Leah",
    )
    spec = build_spec()
    starting = Spec(
        "synthetic-survival-recovery",
        (
            human_survival_slot(
                "synthetic-interval-cohorts",
                "Recover the declared synthetic survival generator.",
            ),
        ),
    )
    session = shepherd(
        starting,
        lambda current, _holes: current.bind_typed(
            "synthetic-interval-cohorts",
            spec,
            source_text=(
                "Use the exact content-addressed records, immutable split, fixed model, "
                "fixed starts/bounds, and no-transfer authority."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        ),
        discarded=(
            "actual-human or animal data",
            "LD50/LC50 rate semantics",
            "causal biological assembly",
            "transfer outside the synthetic generator",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return compile_session_human_survival_recovery(
        source,
        session,
        "synthetic-interval-cohorts",
        engine,
    )


def run(journal: Path = DEFAULT_JOURNAL):
    engine = SyntheticSurvivalRecoveryEngine()
    plan = compile_plan(engine)
    approved = approve(
        plan,
        record_approval(
            plan,
            "Leah",
            (
                "run this complete synthetic-only generator-recovery calculation; "
                "no human, biological, toxicological, causal, or safety transfer"
            ),
        ),
    )
    return execute(approved, engine, journal_path=journal)


def summary(report: object) -> dict[str, object]:
    if report.result is None or report.certificate is None:
        return {
            "status": report.record.status.value,
            "failures": report.record.failures,
        }
    fit = report.result.values[0].payload
    plan = next(
        artifact.payload
        for artifact in report.record.artifacts
        if artifact.artifact_id == "candidate-plan"
    )
    return {
        "run_id": report.record.run_id,
        "status": report.record.status.value,
        "scientific_status": fit.status.value,
        "validation_status": fit.validation.value,
        "dataset_digest": fit.dataset_digest,
        "fitted_parameters": {
            "lambda_days": fit.fitted_parameters.lambda_days,
            "shape_k": fit.fitted_parameters.shape_k,
            "dose_coefficient_beta": fit.fitted_parameters.dose_coefficient_beta,
        },
        "heldout_mean_negative_log_score": fit.heldout_mean_negative_log_score,
        "heldout_brier_score": fit.heldout_brier_score,
        "information_rank": fit.optimizer.information_rank,
        "information_condition_number": fit.optimizer.information_condition_number,
        "output_inventory": report.certificate.output_inventory,
        "certificate_digest": report.certificate.digest,
        "plan_digest": report.record.plan_digest,
        "approval_digest": report.record.approval_digest,
        "compiler_implementation_digest": (
            report.certificate.compiler_implementation_digest
        ),
        "engine_implementation_digest": (
            plan.calculation.implementation_digest
        ),
        "scope": (
            "same-generator synthetic recovery only; not human, biological, "
            "toxicological, causal, LD50/LC50, clinical, regulatory, or safety evidence"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    args = parser.parse_args()
    print(json.dumps(summary(run(args.journal)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
