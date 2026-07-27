"""Adversarial tests for the pure human-isotope identifiability domain."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import math

import pytest

from smartchem.human_isotope_domain import (
    AssemblyKind,
    CalibrationEvidence,
    EnvironmentalProtocol,
    EvidenceBasis,
    ExposureEvent,
    ExposureMetric,
    ExposureRoute,
    FamilyWitness,
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
    SurvivalFamily,
    ToxicokineticLink,
    UncertaintyInterval,
    ValidationStatus,
    diagnose_human_isotope,
)


def endpoint(
    kind: MedianEndpointKind = MedianEndpointKind.LD50,
    *,
    population: str = "hypothetical generic cohort",
    species: str = "Homo sapiens",
    evidence_basis: EvidenceBasis = EvidenceBasis.HYPOTHETICAL_CONSTRAINT,
) -> MedianEndpointConstraint:
    if kind is MedianEndpointKind.LD50:
        value, route = 100.0, ExposureRoute.ORAL
    else:
        value, route = 50.0, ExposureRoute.INHALATION
    return MedianEndpointConstraint(
        kind=kind,
        value=value,
        uncertainty=UncertaintyInterval(value * 0.9, value * 1.1),
        population=population,
        species=species,
        route=route,
        endpoint_definition="declared all-cause functional death event",
        exposure_duration_days=1.0,
        observation_window_days=14.0,
        provenance="synthetic endpoint for compiler acceptance testing only",
        evidence_basis=evidence_basis,
        applicability="structural identifiability test; no actual-person prediction",
    )


def population(
    *,
    name: str = "hypothetical generic cohort",
    species: str = "Homo sapiens",
    competing_risks: tuple[str, ...] = ("other declared failure causes",),
) -> PopulationProtocol:
    return PopulationProtocol(
        population=name,
        species=species,
        time_origin="start of the declared exposure protocol",
        event="declared all-cause functional death event",
        competing_risks=competing_risks,
        censoring="right censoring retained explicitly",
        truncation="no truncation in the synthetic structural example",
        strata=("single declared hypothetical stratum",),
    )


def environment(constraint: MedianEndpointConstraint) -> EnvironmentalProtocol:
    return EnvironmentalProtocol(
        agent="synthetic test agent",
        route=constraint.route,
        metric=constraint.metric,
        schedule=(
            ExposureEvent(
                start_days=0.0,
                duration_days=constraint.exposure_duration_days,
                level=constraint.value,
                metric=constraint.metric,
            ),
        ),
        recovery=RecoveryModel.PARTIAL_DECLARED,
        recovery_description="recovery is a selected hypothesis, not measured evidence",
    )


def toxicokinetic_link(
    constraint: MedianEndpointConstraint,
    *,
    target_species: str = "Homo sapiens",
    source_species: str | None = None,
) -> ToxicokineticLink:
    return ToxicokineticLink(
        route=constraint.route,
        external_metric=constraint.metric,
        internal_metric=InternalExposureMetric.INTERNAL_BURDEN_MG_PER_KG,
        source_species=source_species or constraint.species,
        target_species=target_species,
        model="declared one-compartment placeholder transport",
        assumptions=("linear transport over the declared synthetic exposure",),
        provenance="synthetic transport hypothesis for compiler testing",
        applicability="not validated for an actual person or population",
    )


def calibration(**changes: object) -> CalibrationEvidence:
    values: dict[str, object] = {
        "dose_level_count": 1,
        "observation_time_count": 1,
        "population_count": 1,
        "record_count": 1,
        "dataset_digest": "a" * 64,
        "uncertainty_quantified": False,
        "uncertainty_model": "endpoint interval only; no dynamic uncertainty model",
        "heldout_record_count": 0,
        "heldout_dataset_digest": None,
    }
    values.update(changes)
    return CalibrationEvidence(**values)


def spec(
    *,
    target: HumanTarget = HumanTarget.COHORT_ALL_CAUSE_SURVIVAL,
    constraint: MedianEndpointConstraint | None = None,
    target_population: PopulationProtocol | None = None,
    tk_link: ToxicokineticLink | None = None,
    evidence: CalibrationEvidence | None = None,
    granularity: GranularitySpec | None = None,
    hazard: HazardMechanismChoice | None = None,
) -> HumanIsotopeSpec:
    constraint = constraint or endpoint()
    target_population = target_population or population()
    return HumanIsotopeSpec(
        target=target,
        granularity=granularity
        or GranularitySpec(
            level=GranularityLevel.LUMPED_FUNCTIONAL_UNITS,
            components=("repair reserve", "background failure channel"),
            aggregation="two hypothetical functional populations remain differentiated",
        ),
        assembly=LivingAssemblyHypothesis(
            kind=AssemblyKind.REDUNDANCY_QUORUM,
            rules=("the declared functional reserve must remain above its quorum",),
            repair="repair replenishes reserve under one unvalidated rule",
            interactions=("background and reserve failures are explicitly coupled",),
        ),
        environment=environment(constraint),
        hazard_mechanism=hazard
        or HazardMechanismChoice(
            effect=HazardEffect.REDUNDANCY_OR_REPAIR_STATE,
            affected_components=("repair reserve",),
            statement="exposure changes reserve or repair, not a nuclear decay constant",
        ),
        population=target_population,
        toxicokinetic_link=tk_link
        or toxicokinetic_link(
            constraint,
            target_species=target_population.species,
        ),
        endpoint=constraint,
        calibration=evidence or calibration(),
    )


def test_domain_records_are_immutable_and_scientist_choices_change_identity():
    cohort = spec()
    threshold = spec(
        target=HumanTarget.FUNCTIONAL_THRESHOLD_DISTRIBUTION,
        granularity=GranularitySpec(
            GranularityLevel.REPAIR_SYSTEMS,
            ("repair system", "functional threshold"),
            "repair capacity is retained as an explicit state",
        ),
        hazard=HazardMechanismChoice(
            HazardEffect.BOTH,
            ("repair system", "functional threshold"),
            "exposure may alter both failure hazard and repair state",
        ),
    )

    assert cohort.digest != threshold.digest
    assert diagnose_human_isotope(cohort).digest != diagnose_human_isotope(threshold).digest
    with pytest.raises(FrozenInstanceError):
        cohort.target = HumanTarget.INDIVIDUAL_LIFETIME_SAMPLE  # type: ignore[misc]


def test_ld50_and_lc50_have_fixed_distinct_units_and_are_never_rates():
    ld50 = endpoint(MedianEndpointKind.LD50)
    lc50 = endpoint(MedianEndpointKind.LC50)

    assert ld50.metric is ExposureMetric.ADMINISTERED_DOSE_MG_PER_KG
    assert ld50.unit == "mg/kg"
    assert lc50.metric is ExposureMetric.AIR_CONCENTRATION_MG_PER_M3
    assert lc50.unit == "mg/m^3"
    assert all(
        token not in ld50.unit and token not in lc50.unit
        for token in ("/day", "/year", "s^-1")
    )
    assert ld50.cumulative_mortality == lc50.cumulative_mortality == 0.5

    with pytest.raises(ValueError, match="inhalation endpoint requires concentration"):
        replace(ld50, route=ExposureRoute.INHALATION)
    with pytest.raises(ValueError, match="supported only for inhalation"):
        replace(lc50, route=ExposureRoute.ORAL)


def test_spec_binds_endpoint_environment_and_toxicokinetic_route_and_metric():
    baseline = spec()

    with pytest.raises(ValueError, match="environment and endpoint routes"):
        replace(
            baseline,
            endpoint=replace(
                baseline.endpoint,
                kind=MedianEndpointKind.LC50,
                route=ExposureRoute.INHALATION,
                value=50.0,
                uncertainty=UncertaintyInterval(45.0, 55.0),
            ),
        )
    with pytest.raises(ValueError, match="toxicokinetic and endpoint routes"):
        replace(
            baseline,
            toxicokinetic_link=replace(
                baseline.toxicokinetic_link,
                external_metric=ExposureMetric.AIR_CONCENTRATION_MG_PER_M3,
                route=ExposureRoute.INHALATION,
            ),
        )
    with pytest.raises(ValueError, match="definition must exactly match"):
        replace(
            baseline,
            endpoint=replace(
                baseline.endpoint,
                endpoint_definition="a different unapproved endpoint",
            ),
        )

    with pytest.raises(ValueError, match="declared time origin"):
        replace(
            baseline,
            environment=replace(
                baseline.environment,
                schedule=(
                    replace(
                        baseline.environment.schedule[0],
                        start_days=30.0,
                    ),
                ),
            ),
        )
    with pytest.raises(ValueError, match="affected components"):
        replace(
            baseline,
            hazard_mechanism=replace(
                baseline.hazard_mechanism,
                affected_components=("undeclared organ",),
            ),
        )
    with pytest.raises(ValueError, match="source species must match"):
        replace(
            baseline,
            toxicokinetic_link=replace(
                baseline.toxicokinetic_link,
                source_species="Rattus norvegicus",
            ),
        )


def test_cross_species_evidence_requires_explicit_extrapolation_and_link():
    rat_endpoint = endpoint(
        population="synthetic rat assay",
        species="Rattus norvegicus",
        evidence_basis=EvidenceBasis.NONHUMAN_EXTRAPOLATION,
    )
    human_population = population()
    cross_species = spec(
        constraint=rat_endpoint,
        target_population=human_population,
        tk_link=toxicokinetic_link(
            rat_endpoint,
            source_species="Rattus norvegicus",
            target_species="Homo sapiens",
        ),
    )

    diagnostic = diagnose_human_isotope(cross_species)
    assert "validated nonhuman-to-target-population extrapolation" in (
        diagnostic.missing_evidence
    )

    with pytest.raises(ValueError, match="requires NONHUMAN_EXTRAPOLATION"):
        spec(
            constraint=replace(
                rat_endpoint,
                evidence_basis=EvidenceBasis.HYPOTHETICAL_CONSTRAINT,
            ),
            target_population=human_population,
            tk_link=toxicokinetic_link(
                rat_endpoint,
                source_species="Rattus norvegicus",
                target_species="Homo sapiens",
            ),
        )
    with pytest.raises(ValueError, match="source species must match"):
        spec(
            constraint=rat_endpoint,
            target_population=human_population,
            tk_link=toxicokinetic_link(
                rat_endpoint,
                source_species="Mus musculus",
                target_species="Homo sapiens",
            ),
        )


def test_single_endpoint_diagnostic_is_explicitly_underidentified_and_unvalidated():
    selected = spec()
    diagnostic = diagnose_human_isotope(selected)

    assert diagnostic.status is IdentifiabilityStatus.UNDERIDENTIFIED_DYNAMIC_MODEL
    assert diagnostic.validation is ValidationStatus.UNVALIDATED
    assert diagnostic.constraint_inventory.endpoint == selected.endpoint
    assert diagnostic.constraint_inventory.cumulative_mortality_at_endpoint == 0.5
    assert diagnostic.constraint_inventory.normalized_observation_time == 1.0
    assert diagnostic.constraint_inventory.environmental_protocol_digest == (
        selected.environment.digest
    )
    assert diagnostic.constraint_inventory.population_protocol_digest == (
        selected.population.digest
    )
    assert "state dynamics F" in diagnostic.free_parameters
    assert "cause-specific hazard functions G_k" in diagnostic.free_parameters
    assert "assembly map A" in diagnostic.free_parameters
    assert "multiple exposure levels" in diagnostic.missing_evidence
    assert "multiple observation times" in diagnostic.missing_evidence
    assert "held-out validation evidence" in diagnostic.missing_evidence
    assert "prediction for any actual person" in diagnostic.transport.discarded


def test_two_dynamic_family_witnesses_fit_the_endpoint_but_disagree_away_from_it():
    witnesses = diagnose_human_isotope(spec()).family_witnesses
    exponential = next(
        item for item in witnesses if item.family is SurvivalFamily.EXPONENTIAL
    )
    weibull = next(
        item for item in witnesses if item.family is SurvivalFamily.WEIBULL_SHAPE_2
    )

    assert exponential.cumulative_mortality_at_endpoint == 0.5
    assert weibull.cumulative_mortality_at_endpoint == 0.5
    assert exponential.cumulative_mortality_at_half_time == pytest.approx(
        1.0 - 2.0**-0.5
    )
    assert weibull.cumulative_mortality_at_half_time == pytest.approx(
        1.0 - 2.0**-0.25
    )
    assert exponential.cumulative_mortality_at_half_time != pytest.approx(
        weibull.cumulative_mortality_at_half_time
    )


def test_more_counts_do_not_turn_the_single_endpoint_diagnostic_into_unique_parameters():
    richer_counts = calibration(
        dose_level_count=4,
        observation_time_count=6,
        record_count=100,
        uncertainty_quantified=True,
        uncertainty_model="declared interval model",
        heldout_record_count=20,
        heldout_dataset_digest="b" * 64,
    )

    diagnostic = diagnose_human_isotope(spec(evidence=richer_counts))

    assert diagnostic.status is IdentifiabilityStatus.UNDERIDENTIFIED_DYNAMIC_MODEL
    assert len(diagnostic.family_witnesses) == 2
    assert "a single median endpoint does not identify a dynamic survival family" in (
        diagnostic.missing_evidence
    )


def test_cause_specific_target_requires_competing_risks():
    with pytest.raises(ValueError, match="requires declared competing risks"):
        spec(
            target=HumanTarget.CAUSE_SPECIFIC_CUMULATIVE_INCIDENCE,
            target_population=population(competing_risks=()),
        )


@pytest.mark.parametrize(
    "factory, message",
    [
        (
            lambda: replace(endpoint(), value=0.0),
            "value must be positive",
        ),
        (
            lambda: replace(endpoint(), value=float("nan")),
            "value must be finite",
        ),
        (
            lambda: UncertaintyInterval(2.0, 1.0),
            "lower bound",
        ),
        (
            lambda: replace(
                endpoint(),
                uncertainty=UncertaintyInterval(101.0, 110.0),
            ),
            "inside its uncertainty",
        ),
        (
            lambda: ExposureEvent(
                0.0,
                float("inf"),
                1.0,
                ExposureMetric.ADMINISTERED_DOSE_MG_PER_KG,
            ),
            "duration_days must be finite",
        ),
        (
            lambda: calibration(dataset_digest="not-a-digest"),
            "lowercase SHA-256",
        ),
        (
            lambda: calibration(dose_level_count=0),
            "at least one dose level",
        ),
        (
            lambda: calibration(heldout_dataset_digest="b" * 64),
            "positive heldout_record_count",
        ),
        (
            lambda: FamilyWitness(
                SurvivalFamily.EXPONENTIAL,
                (("rate", math.log(2.0)),),
                1.1,
                0.5,
            ),
            r"lie in \[0, 1\]",
        ),
    ],
)
def test_bounds_nonfinite_values_and_malformed_evidence_are_rejected(factory, message):
    with pytest.raises((TypeError, ValueError), match=message):
        factory()


def test_schedule_overlap_and_incomplete_semantic_records_are_rejected():
    metric = ExposureMetric.ADMINISTERED_DOSE_MG_PER_KG
    with pytest.raises(ValueError, match="must not overlap"):
        EnvironmentalProtocol(
            agent="synthetic",
            route=ExposureRoute.ORAL,
            metric=metric,
            schedule=(
                ExposureEvent(0.0, 2.0, 1.0, metric),
                ExposureEvent(1.0, 1.0, 1.0, metric),
            ),
            recovery=RecoveryModel.NONE_DECLARED,
            recovery_description="none declared",
        )
    with pytest.raises(ValueError, match="components must not be empty"):
        GranularitySpec(
            GranularityLevel.CELL_POPULATIONS,
            (),
            "no components were selected",
        )
    with pytest.raises(TypeError, match="GranularityLevel"):
        GranularitySpec(  # type: ignore[arg-type]
            "CELL_POPULATIONS",
            ("cell population",),
            "one population",
        )


def test_diagnostic_refuses_non_spec_inputs():
    with pytest.raises(TypeError, match="HumanIsotopeSpec"):
        diagnose_human_isotope("human half-life")  # type: ignore[arg-type]
