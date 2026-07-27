"""Run the approved D2a human-isotope structural identifiability vertical.

Everything in this run is synthetic.  The endpoint, population, components, assembly,
exposure, and toxicokinetic link are hypotheses chosen to test the compiler.  The output is
the negative result that a single median endpoint admits distinct dynamic families.  It is
not demography, toxicology advice, a human LD50 measurement, or a prediction for anyone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from smartchem import (
    COMPILED,
    AssemblyKind,
    CalibrationEvidence,
    EnvironmentalProtocol,
    EvidenceBasis,
    ExposureEvent,
    ExposureRoute,
    GranularityLevel,
    GranularitySpec,
    HazardEffect,
    HazardMechanismChoice,
    HumanIsotopeIdentifiabilityEngine,
    HumanIsotopeSpec,
    HumanTarget,
    InferenceKind,
    InternalExposureMetric,
    LivingAssemblyHypothesis,
    MedianEndpointConstraint,
    MedianEndpointKind,
    PopulationProtocol,
    RecoveryModel,
    SourceProgram,
    Spec,
    ToxicokineticLink,
    UncertaintyInterval,
    approve,
    compile_human_isotope_identifiability,
    compile_session_human_isotope_identifiability,
    execute,
    human_isotope_slot,
    record_approval,
    shepherd,
)


DEFAULT_JOURNAL = Path(__file__).with_name("compiled_human_isotope_run.json")


def build_spec(
    target: HumanTarget = HumanTarget.COHORT_ALL_CAUSE_SURVIVAL,
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
        evidence_basis=EvidenceBasis.HYPOTHETICAL_CONSTRAINT,
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
    environment = EnvironmentalProtocol(
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
    )
    return HumanIsotopeSpec(
        target=target,
        granularity=GranularitySpec(
            GranularityLevel.LUMPED_FUNCTIONAL_UNITS,
            ("repair reserve", "background failure channel"),
            "two scientist-selected component classes remain differentiated",
        ),
        assembly=LivingAssemblyHypothesis(
            AssemblyKind.REDUNDANCY_QUORUM,
            ("functional reserve must remain above a declared quorum",),
            "repair replenishes reserve under one unvalidated rule",
            ("background and reserve failure channels are explicitly coupled",),
        ),
        environment=environment,
        hazard_mechanism=HazardMechanismChoice(
            HazardEffect.REDUNDANCY_OR_REPAIR_STATE,
            ("repair reserve",),
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


def compile_plan(engine: HumanIsotopeIdentifiabilityEngine):
    source = SourceProgram(
        text=(
            "Model a generic human as a scientist-chosen differentiated bundle using a "
            "modified radioactive-decay analogy whose failure behavior responds to the "
            "environment, constrained by the LD50 concept. Preserve every ambiguity and "
            "do not emit an actual-person prediction."
        ),
        spans=(
            "generic human",
            "scientist-chosen differentiated bundle",
            "modified radioactive-decay analogy",
            "responds to the environment",
            "constrained by the LD50 concept",
            "do not emit an actual-person prediction",
        ),
        scientist="Leah",
    )
    spec = build_spec()
    starting = Spec(
        "compiled-human-isotope-vertical",
        (
            human_isotope_slot(
                "human-model",
                "Model a generic human as an isotope using environmental LD50.",
            ),
        ),
    )

    def select(current, _holes):
        return current.bind_typed(
            "human-model",
            spec,
            source_text=(
                "Use a synthetic cohort-level all-cause target, two lumped functional "
                "classes, a redundancy/repair assembly hypothesis, a hypothetical oral "
                "LD50 endpoint, and diagnose identifiability only."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        )

    session = shepherd(
        starting,
        select,
        discarded=(
            "literal isotope identity",
            "LD50 as a per-time rate",
            "a universal human LD50",
            "actual-person, clinical, causal, or regulatory prediction",
        ),
    )
    if session.outcome != COMPILED:
        raise RuntimeError(session.explain())
    return compile_session_human_isotope_identifiability(
        source,
        session,
        "human-model",
        engine,
    )


def run(journal_path: Path):
    engine = HumanIsotopeIdentifiabilityEngine()
    plan = compile_plan(engine)
    approved = approve(
        plan,
        record_approval(
            plan,
            principal="Leah",
            scope=(
                "run this synthetic structural identifiability diagnostic; retain the "
                "complete default output; no actual-person, mortality-model, toxicological, "
                "clinical, causal, regulatory, or literal-isotope claim"
            ),
        ),
    )
    return execute(approved, engine, journal_path=journal_path)


def blocked_actual_person_plan() -> tuple[str, ...]:
    engine = HumanIsotopeIdentifiabilityEngine()
    plan = compile_human_isotope_identifiability(
        "Predict one person's lifetime from the same LD50 endpoint.",
        build_spec(HumanTarget.INDIVIDUAL_LIFETIME_SAMPLE),
        engine,
    )
    return plan.blockers


def summary(report) -> dict[str, object]:
    diagnostic = report.result.values[0].payload if report.result is not None else None
    certificate_artifact = next(
        (
            item
            for item in report.record.artifacts
            if item.artifact_id == "certificate"
        ),
        None,
    )
    return {
        "run_id": report.record.run_id,
        "status": report.record.status.value,
        "started_at": report.record.started_at,
        "updated_at": report.record.updated_at,
        "plan_digest": report.record.plan_digest,
        "approval_digest": report.record.approval_digest,
        "certificate_artifact_content_digest": (
            certificate_artifact.content_digest
            if certificate_artifact is not None
            else None
        ),
        "claim_scope": (
            report.certificate.claim_scope.kind.value
            if report.certificate is not None
            else None
        ),
        "claim_referent": (
            report.certificate.claim_scope.referent
            if report.certificate is not None
            else None
        ),
        "evidence_status": (
            report.certificate.evidence_status.value
            if report.certificate is not None
            else None
        ),
        "validation": diagnostic.validation.value if diagnostic is not None else None,
        "diagnostic_status": (
            diagnostic.status.value if diagnostic is not None else None
        ),
        "endpoint": (
            {
                "kind": diagnostic.spec.endpoint.kind.value,
                "value": diagnostic.spec.endpoint.value,
                "unit": diagnostic.spec.endpoint.unit,
                "exposure_duration_days": (
                    diagnostic.spec.endpoint.exposure_duration_days
                ),
                "observation_window_days": (
                    diagnostic.spec.endpoint.observation_window_days
                ),
                "cumulative_mortality_constraint": 0.5,
            }
            if diagnostic is not None
            else None
        ),
        "family_witnesses": (
            [
                {
                    "family": item.family.value,
                    "parameters": dict(item.parameters),
                    "cumulative_mortality_at_half_time": (
                        item.cumulative_mortality_at_half_time
                    ),
                    "cumulative_mortality_at_endpoint": (
                        item.cumulative_mortality_at_endpoint
                    ),
                }
                for item in diagnostic.family_witnesses
            ]
            if diagnostic is not None
            else []
        ),
        "free_parameters": (
            list(diagnostic.free_parameters) if diagnostic is not None else []
        ),
        "missing_evidence": (
            list(diagnostic.missing_evidence) if diagnostic is not None else []
        ),
        "discriminating_experiments": (
            list(diagnostic.discriminating_experiments)
            if diagnostic is not None
            else []
        ),
        "casualties": (
            list(report.certificate.casualties)
            if report.certificate is not None
            else []
        ),
        "omissions": (
            list(report.certificate.omissions)
            if report.certificate is not None
            else []
        ),
        "output_inventory": list(report.record.output_inventory),
        "obligations": (
            [
                {
                    "obligation_digest": item.obligation_digest,
                    "outcome": item.outcome.value,
                    "detail": item.detail,
                }
                for item in report.certificate.validity_results
            ]
            if report.certificate is not None
            else []
        ),
        "blocked_actual_person_plan": list(blocked_actual_person_plan()),
        "failures": list(report.record.failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    args = parser.parse_args()
    report = run(args.journal)
    print(json.dumps(summary(report), indent=2, sort_keys=True))
    return 0 if report.record.status.value == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
