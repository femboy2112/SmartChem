"""Pure typed domain for the human-isotope identifiability vertical.

This module does not predict mortality for an actual person or population.  It records one
fully scientist-selected hypothetical interpretation of the metaphor and asks the narrower
question that a single median endpoint can answer: what is constrained, and what remains
unidentified?

The supported endpoint semantics are intentionally fixed:

* ``LD50`` is an administered mass dose in ``mg/kg``;
* ``LC50`` is an inhaled concentration in ``mg/m^3``;
* both constrain cumulative mortality to 0.5 at one declared observation window;
* neither is a rate, hazard, individual risk, or identified dynamic model.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real

from .contracts import canonical_digest

__all__ = [
    "AssemblyKind",
    "CalibrationEvidence",
    "ConstraintInventory",
    "EnvironmentalProtocol",
    "EvidenceBasis",
    "ExposureEvent",
    "ExposureMetric",
    "ExposureRoute",
    "FamilyWitness",
    "GranularityLevel",
    "GranularitySpec",
    "HazardEffect",
    "HazardMechanismChoice",
    "HumanIsotopeSpec",
    "HumanTarget",
    "IdentifiabilityDiagnostic",
    "IdentifiabilityStatus",
    "InternalExposureMetric",
    "LivingAssemblyHypothesis",
    "MedianEndpointConstraint",
    "MedianEndpointKind",
    "PopulationProtocol",
    "RecoveryModel",
    "SurvivalFamily",
    "ToxicokineticLink",
    "TransportInventory",
    "UncertaintyInterval",
    "ValidationStatus",
    "diagnose_human_isotope",
]


class _Digestible:
    @property
    def digest(self) -> str:
        return canonical_digest(self)


class HumanTarget(str, Enum):
    """Scientist-selected target; the menu is vocabulary, not an exhaustive ontology."""

    COHORT_ALL_CAUSE_SURVIVAL = "COHORT_ALL_CAUSE_SURVIVAL"
    CAUSE_SPECIFIC_CUMULATIVE_INCIDENCE = "CAUSE_SPECIFIC_CUMULATIVE_INCIDENCE"
    FUNCTIONAL_THRESHOLD_DISTRIBUTION = "FUNCTIONAL_THRESHOLD_DISTRIBUTION"
    INDIVIDUAL_LIFETIME_SAMPLE = "INDIVIDUAL_LIFETIME_SAMPLE"


class GranularityLevel(str, Enum):
    MOLECULAR_CLASSES = "MOLECULAR_CLASSES"
    CELL_POPULATIONS = "CELL_POPULATIONS"
    TISSUES = "TISSUES"
    ORGANS = "ORGANS"
    REPAIR_SYSTEMS = "REPAIR_SYSTEMS"
    LUMPED_FUNCTIONAL_UNITS = "LUMPED_FUNCTIONAL_UNITS"


class AssemblyKind(str, Enum):
    REDUNDANCY_QUORUM = "REDUNDANCY_QUORUM"
    REPAIR_CAPACITY = "REPAIR_CAPACITY"
    COMPETING_SUBSYSTEMS = "COMPETING_SUBSYSTEMS"
    STATE_TRANSITIONS = "STATE_TRANSITIONS"
    CUSTOM_DECLARED = "CUSTOM_DECLARED"


class ExposureRoute(str, Enum):
    ORAL = "ORAL"
    DERMAL = "DERMAL"
    INJECTION = "INJECTION"
    INHALATION = "INHALATION"


class ExposureMetric(str, Enum):
    ADMINISTERED_DOSE_MG_PER_KG = "ADMINISTERED_DOSE_MG_PER_KG"
    AIR_CONCENTRATION_MG_PER_M3 = "AIR_CONCENTRATION_MG_PER_M3"

    @property
    def unit(self) -> str:
        if self is ExposureMetric.ADMINISTERED_DOSE_MG_PER_KG:
            return "mg/kg"
        return "mg/m^3"


class InternalExposureMetric(str, Enum):
    INTERNAL_BURDEN_MG_PER_KG = "INTERNAL_BURDEN_MG_PER_KG"
    BLOOD_CONCENTRATION_MG_PER_L = "BLOOD_CONCENTRATION_MG_PER_L"


class RecoveryModel(str, Enum):
    NONE_DECLARED = "NONE_DECLARED"
    FULL_BETWEEN_EXPOSURES = "FULL_BETWEEN_EXPOSURES"
    PARTIAL_DECLARED = "PARTIAL_DECLARED"
    DYNAMIC_DECLARED = "DYNAMIC_DECLARED"


class HazardEffect(str, Enum):
    PART_FAILURE_HAZARD = "PART_FAILURE_HAZARD"
    REDUNDANCY_OR_REPAIR_STATE = "REDUNDANCY_OR_REPAIR_STATE"
    BOTH = "BOTH"


class MedianEndpointKind(str, Enum):
    LD50 = "LD50"
    LC50 = "LC50"


class EvidenceBasis(str, Enum):
    HUMAN_EVIDENCE_SYNTHESIS = "HUMAN_EVIDENCE_SYNTHESIS"
    NONHUMAN_EXTRAPOLATION = "NONHUMAN_EXTRAPOLATION"
    HYPOTHETICAL_CONSTRAINT = "HYPOTHETICAL_CONSTRAINT"


class IdentifiabilityStatus(str, Enum):
    UNDERIDENTIFIED_DYNAMIC_MODEL = "UNDERIDENTIFIED_DYNAMIC_MODEL"


class ValidationStatus(str, Enum):
    UNVALIDATED = "UNVALIDATED"


class SurvivalFamily(str, Enum):
    EXPONENTIAL = "EXPONENTIAL"
    WEIBULL_SHAPE_2 = "WEIBULL_SHAPE_2"


@dataclass(frozen=True)
class GranularitySpec(_Digestible):
    level: GranularityLevel
    components: tuple[str, ...]
    aggregation: str

    def __post_init__(self) -> None:
        _require_enum("level", self.level, GranularityLevel)
        _require_nonempty_strings("components", self.components, require_values=True)
        _require_unique("components", self.components)
        _require_nonempty("aggregation", self.aggregation)


@dataclass(frozen=True)
class LivingAssemblyHypothesis(_Digestible):
    kind: AssemblyKind
    rules: tuple[str, ...]
    repair: str
    interactions: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_enum("kind", self.kind, AssemblyKind)
        _require_nonempty_strings("rules", self.rules, require_values=True)
        _require_nonempty("repair", self.repair)
        _require_nonempty_strings(
            "interactions", self.interactions, require_values=True
        )


@dataclass(frozen=True)
class ExposureEvent(_Digestible):
    start_days: float
    duration_days: float
    level: float
    metric: ExposureMetric

    def __post_init__(self) -> None:
        _require_nonnegative_finite("start_days", self.start_days)
        _require_positive_finite("duration_days", self.duration_days)
        _require_positive_finite("level", self.level)
        _require_enum("metric", self.metric, ExposureMetric)
        object.__setattr__(self, "start_days", float(self.start_days))
        object.__setattr__(self, "duration_days", float(self.duration_days))
        object.__setattr__(self, "level", float(self.level))


@dataclass(frozen=True)
class EnvironmentalProtocol(_Digestible):
    agent: str
    route: ExposureRoute
    metric: ExposureMetric
    schedule: tuple[ExposureEvent, ...]
    recovery: RecoveryModel
    recovery_description: str

    def __post_init__(self) -> None:
        _require_nonempty("agent", self.agent)
        _require_enum("route", self.route, ExposureRoute)
        _require_enum("metric", self.metric, ExposureMetric)
        _require_enum("recovery", self.recovery, RecoveryModel)
        _require_nonempty("recovery_description", self.recovery_description)
        if (
            not isinstance(self.schedule, tuple)
            or not self.schedule
            or any(not isinstance(event, ExposureEvent) for event in self.schedule)
        ):
            raise TypeError(
                "schedule must be a non-empty tuple of ExposureEvent values"
            )
        if any(event.metric is not self.metric for event in self.schedule):
            raise ValueError("every scheduled exposure must use the protocol metric")
        _require_route_metric(self.route, self.metric)
        previous_end = -math.inf
        for event in self.schedule:
            if event.start_days < previous_end:
                raise ValueError("exposure schedule events must not overlap")
            previous_end = event.start_days + event.duration_days


@dataclass(frozen=True)
class HazardMechanismChoice(_Digestible):
    effect: HazardEffect
    affected_components: tuple[str, ...]
    statement: str

    def __post_init__(self) -> None:
        _require_enum("effect", self.effect, HazardEffect)
        _require_nonempty_strings(
            "affected_components", self.affected_components, require_values=True
        )
        _require_unique("affected_components", self.affected_components)
        _require_nonempty("statement", self.statement)


@dataclass(frozen=True)
class PopulationProtocol(_Digestible):
    population: str
    species: str
    time_origin: str
    event: str
    competing_risks: tuple[str, ...]
    censoring: str
    truncation: str
    strata: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "population",
            "species",
            "time_origin",
            "event",
            "censoring",
            "truncation",
        ):
            _require_nonempty(name, getattr(self, name))
        _require_nonempty_strings("competing_risks", self.competing_risks)
        _require_unique("competing_risks", self.competing_risks)
        _require_nonempty_strings("strata", self.strata, require_values=True)
        _require_unique("strata", self.strata)


@dataclass(frozen=True)
class ToxicokineticLink(_Digestible):
    route: ExposureRoute
    external_metric: ExposureMetric
    internal_metric: InternalExposureMetric
    source_species: str
    target_species: str
    model: str
    assumptions: tuple[str, ...]
    provenance: str
    applicability: str

    def __post_init__(self) -> None:
        _require_enum("route", self.route, ExposureRoute)
        _require_enum("external_metric", self.external_metric, ExposureMetric)
        _require_enum("internal_metric", self.internal_metric, InternalExposureMetric)
        _require_route_metric(self.route, self.external_metric)
        for name in (
            "source_species",
            "target_species",
            "model",
            "provenance",
            "applicability",
        ):
            _require_nonempty(name, getattr(self, name))
        _require_nonempty_strings("assumptions", self.assumptions, require_values=True)


@dataclass(frozen=True)
class UncertaintyInterval(_Digestible):
    lower: float
    upper: float

    def __post_init__(self) -> None:
        _require_positive_finite("lower", self.lower)
        _require_positive_finite("upper", self.upper)
        if self.lower > self.upper:
            raise ValueError("uncertainty lower bound must not exceed the upper bound")
        object.__setattr__(self, "lower", float(self.lower))
        object.__setattr__(self, "upper", float(self.upper))


@dataclass(frozen=True)
class MedianEndpointConstraint(_Digestible):
    """One median endpoint constraint; its unit is fixed by ``kind``."""

    kind: MedianEndpointKind
    value: float
    uncertainty: UncertaintyInterval
    population: str
    species: str
    route: ExposureRoute
    endpoint_definition: str
    exposure_duration_days: float
    observation_window_days: float
    provenance: str
    evidence_basis: EvidenceBasis
    applicability: str

    def __post_init__(self) -> None:
        _require_enum("kind", self.kind, MedianEndpointKind)
        _require_positive_finite("value", self.value)
        if not isinstance(self.uncertainty, UncertaintyInterval):
            raise TypeError("uncertainty must be an UncertaintyInterval")
        if not self.uncertainty.lower <= self.value <= self.uncertainty.upper:
            raise ValueError("endpoint value must lie inside its uncertainty interval")
        for name in (
            "population",
            "species",
            "endpoint_definition",
            "provenance",
            "applicability",
        ):
            _require_nonempty(name, getattr(self, name))
        _require_enum("route", self.route, ExposureRoute)
        _require_positive_finite(
            "exposure_duration_days", self.exposure_duration_days
        )
        _require_positive_finite(
            "observation_window_days", self.observation_window_days
        )
        if self.observation_window_days < self.exposure_duration_days:
            raise ValueError(
                "observation window must include the complete exposure duration"
            )
        _require_enum("evidence_basis", self.evidence_basis, EvidenceBasis)
        _require_route_metric(self.route, self.metric)
        object.__setattr__(self, "value", float(self.value))
        object.__setattr__(
            self, "exposure_duration_days", float(self.exposure_duration_days)
        )
        object.__setattr__(
            self, "observation_window_days", float(self.observation_window_days)
        )

    @property
    def metric(self) -> ExposureMetric:
        if self.kind is MedianEndpointKind.LD50:
            return ExposureMetric.ADMINISTERED_DOSE_MG_PER_KG
        return ExposureMetric.AIR_CONCENTRATION_MG_PER_M3

    @property
    def unit(self) -> str:
        return self.metric.unit

    @property
    def cumulative_mortality(self) -> float:
        return 0.5


@dataclass(frozen=True)
class CalibrationEvidence(_Digestible):
    dose_level_count: int
    observation_time_count: int
    population_count: int
    record_count: int
    dataset_digest: str
    uncertainty_quantified: bool
    uncertainty_model: str
    heldout_record_count: int
    heldout_dataset_digest: str | None

    def __post_init__(self) -> None:
        for name in (
            "dose_level_count",
            "observation_time_count",
            "population_count",
            "record_count",
            "heldout_record_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.dose_level_count < 1 or self.observation_time_count < 1:
            raise ValueError(
                "calibration evidence requires at least one dose level and observation time"
            )
        if self.population_count < 1 or self.record_count < 1:
            raise ValueError(
                "calibration evidence requires a population and at least one record"
            )
        _require_digest("dataset_digest", self.dataset_digest)
        if type(self.uncertainty_quantified) is not bool:
            raise TypeError("uncertainty_quantified must be a bool")
        _require_nonempty("uncertainty_model", self.uncertainty_model)
        if self.heldout_record_count:
            _require_digest("heldout_dataset_digest", self.heldout_dataset_digest)
        elif self.heldout_dataset_digest is not None:
            raise ValueError(
                "heldout_dataset_digest requires a positive heldout_record_count"
            )


@dataclass(frozen=True)
class HumanIsotopeSpec(_Digestible):
    """Every scientist-owned semantic choice needed by the D2 diagnostic."""

    target: HumanTarget
    granularity: GranularitySpec
    assembly: LivingAssemblyHypothesis
    environment: EnvironmentalProtocol
    hazard_mechanism: HazardMechanismChoice
    population: PopulationProtocol
    toxicokinetic_link: ToxicokineticLink
    endpoint: MedianEndpointConstraint
    calibration: CalibrationEvidence

    def __post_init__(self) -> None:
        _require_enum("target", self.target, HumanTarget)
        for name, expected in (
            ("granularity", GranularitySpec),
            ("assembly", LivingAssemblyHypothesis),
            ("environment", EnvironmentalProtocol),
            ("hazard_mechanism", HazardMechanismChoice),
            ("population", PopulationProtocol),
            ("toxicokinetic_link", ToxicokineticLink),
            ("endpoint", MedianEndpointConstraint),
            ("calibration", CalibrationEvidence),
        ):
            if not isinstance(getattr(self, name), expected):
                raise TypeError(f"{name} must be a {expected.__name__}")
        if self.target is HumanTarget.CAUSE_SPECIFIC_CUMULATIVE_INCIDENCE:
            if not self.population.competing_risks:
                raise ValueError(
                    "cause-specific cumulative incidence requires declared competing risks"
                )
        if self.environment.route is not self.endpoint.route:
            raise ValueError("environment and endpoint routes must match")
        if self.environment.metric is not self.endpoint.metric:
            raise ValueError("environment and endpoint exposure metrics must match")
        if self.toxicokinetic_link.route is not self.endpoint.route:
            raise ValueError("toxicokinetic and endpoint routes must match")
        if self.toxicokinetic_link.external_metric is not self.endpoint.metric:
            raise ValueError(
                "toxicokinetic external metric and endpoint metric must match"
            )
        if self.endpoint.endpoint_definition != self.population.event:
            raise ValueError(
                "median endpoint definition must exactly match the target population event"
            )
        if len(self.environment.schedule) != 1:
            raise ValueError(
                "the narrow single-endpoint diagnostic requires exactly one exposure event"
            )
        event = self.environment.schedule[0]
        if event.start_days != 0.0:
            raise ValueError(
                "the narrow single-endpoint diagnostic requires exposure to start "
                "at the declared time origin"
            )
        if event.start_days + event.duration_days > self.endpoint.observation_window_days:
            raise ValueError(
                "the complete scheduled exposure must lie inside the endpoint "
                "observation window"
            )
        if event.level != self.endpoint.value:
            raise ValueError(
                "the scheduled exposure level must equal the median endpoint value"
            )
        if event.duration_days != self.endpoint.exposure_duration_days:
            raise ValueError(
                "the scheduled exposure duration must equal the endpoint duration"
            )
        if self.toxicokinetic_link.target_species != self.population.species:
            raise ValueError(
                "toxicokinetic target species must match the target population species"
            )
        if self.toxicokinetic_link.source_species != self.endpoint.species:
            raise ValueError(
                "toxicokinetic source species must match the endpoint species"
            )
        undeclared_components = tuple(
            component
            for component in self.hazard_mechanism.affected_components
            if component not in self.granularity.components
        )
        if undeclared_components:
            raise ValueError(
                "hazard mechanism affected components must be declared granularity "
                "components: "
                + ", ".join(undeclared_components)
            )
        if self.endpoint.species == self.population.species:
            if self.endpoint.population != self.population.population:
                raise ValueError(
                    "same-species endpoint and target population names must match"
                )
            if (
                self.endpoint.evidence_basis
                is EvidenceBasis.NONHUMAN_EXTRAPOLATION
            ):
                raise ValueError(
                    "nonhuman extrapolation requires different source and target species"
                )
        else:
            if (
                self.endpoint.evidence_basis
                is not EvidenceBasis.NONHUMAN_EXTRAPOLATION
            ):
                raise ValueError(
                    "cross-species endpoint use requires NONHUMAN_EXTRAPOLATION"
                )


@dataclass(frozen=True)
class ConstraintInventory(_Digestible):
    endpoint: MedianEndpointConstraint
    cumulative_mortality_at_endpoint: float
    normalized_observation_time: float
    environmental_protocol_digest: str
    population_protocol_digest: str
    toxicokinetic_link_digest: str
    calibration_evidence_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, MedianEndpointConstraint):
            raise TypeError("endpoint must be a MedianEndpointConstraint")
        if self.cumulative_mortality_at_endpoint != 0.5:
            raise ValueError("a median endpoint constrains cumulative mortality to 0.5")
        if self.normalized_observation_time != 1.0:
            raise ValueError("the endpoint observation time is normalized to 1")
        for name in (
            "environmental_protocol_digest",
            "population_protocol_digest",
            "toxicokinetic_link_digest",
            "calibration_evidence_digest",
        ):
            _require_digest(name, getattr(self, name))


@dataclass(frozen=True)
class FamilyWitness(_Digestible):
    family: SurvivalFamily
    parameters: tuple[tuple[str, float], ...]
    cumulative_mortality_at_half_time: float
    cumulative_mortality_at_endpoint: float

    def __post_init__(self) -> None:
        _require_enum("family", self.family, SurvivalFamily)
        if not isinstance(self.parameters, tuple) or not self.parameters:
            raise TypeError("parameters must be a non-empty tuple")
        names: list[str] = []
        for item in self.parameters:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("parameters must contain (name, value) pairs")
            name, value = item
            _require_nonempty("parameter name", name)
            _require_positive_finite("parameter value", value)
            names.append(name)
        _require_unique("parameter names", tuple(names))
        for name in (
            "cumulative_mortality_at_half_time",
            "cumulative_mortality_at_endpoint",
        ):
            value = getattr(self, name)
            _require_finite_real(name, value)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1]")
        if self.cumulative_mortality_at_endpoint != 0.5:
            raise ValueError("every family witness must satisfy the median endpoint")


@dataclass(frozen=True)
class TransportInventory(_Digestible):
    preserved: tuple[str, ...]
    modified: tuple[str, ...]
    discarded: tuple[str, ...]
    unknown: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("preserved", "modified", "discarded", "unknown"):
            _require_nonempty_strings(name, getattr(self, name), require_values=True)


@dataclass(frozen=True)
class IdentifiabilityDiagnostic(_Digestible):
    spec: HumanIsotopeSpec
    status: IdentifiabilityStatus
    validation: ValidationStatus
    constraint_inventory: ConstraintInventory
    free_parameters: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    transport: TransportInventory
    family_witnesses: tuple[FamilyWitness, ...]
    discriminating_experiments: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, HumanIsotopeSpec):
            raise TypeError("spec must be a HumanIsotopeSpec")
        _require_enum("status", self.status, IdentifiabilityStatus)
        _require_enum("validation", self.validation, ValidationStatus)
        if not isinstance(self.constraint_inventory, ConstraintInventory):
            raise TypeError("constraint_inventory must be a ConstraintInventory")
        _require_nonempty_strings(
            "free_parameters", self.free_parameters, require_values=True
        )
        _require_nonempty_strings(
            "missing_evidence", self.missing_evidence, require_values=True
        )
        if not isinstance(self.transport, TransportInventory):
            raise TypeError("transport must be a TransportInventory")
        if (
            not isinstance(self.family_witnesses, tuple)
            or len(self.family_witnesses) != 2
            or any(
                not isinstance(witness, FamilyWitness)
                for witness in self.family_witnesses
            )
        ):
            raise TypeError("family_witnesses must contain exactly two FamilyWitness values")
        if self.family_witnesses[0].family is self.family_witnesses[1].family:
            raise ValueError("family witnesses must represent distinct dynamic families")
        if (
            self.family_witnesses[0].cumulative_mortality_at_half_time
            == self.family_witnesses[1].cumulative_mortality_at_half_time
        ):
            raise ValueError("family witnesses must differ away from the fitted endpoint")
        _require_nonempty_strings(
            "discriminating_experiments",
            self.discriminating_experiments,
            require_values=True,
        )


def diagnose_human_isotope(spec: HumanIsotopeSpec) -> IdentifiabilityDiagnostic:
    """Return the complete structural diagnosis for one typed single-endpoint hypothesis."""
    if not isinstance(spec, HumanIsotopeSpec):
        raise TypeError("spec must be a HumanIsotopeSpec")

    log_two = math.log(2.0)
    exponential_half = 1.0 - math.exp(-log_two * 0.5)
    weibull_half = 1.0 - math.exp(-log_two * 0.5**2)
    witnesses = (
        FamilyWitness(
            SurvivalFamily.EXPONENTIAL,
            (("normalized_rate", log_two),),
            exponential_half,
            0.5,
        ),
        FamilyWitness(
            SurvivalFamily.WEIBULL_SHAPE_2,
            (("shape", 2.0), ("normalized_scale_coefficient", log_two)),
            weibull_half,
            0.5,
        ),
    )

    free_parameters = (
        "state dynamics F",
        "cause-specific hazard functions G_k",
        "assembly map A",
        "baseline hazard",
        "exposure-response parameters",
        "repair and interaction parameters",
        "toxicokinetic parameters",
        "dependence among competing risks",
    )
    missing: list[str] = [
        "a single median endpoint does not identify a dynamic survival family",
        "assembly and hazard mechanisms lack independent calibration",
        "no evidence separates part-hazard change from redundancy or repair change",
    ]
    if spec.calibration.dose_level_count < 2:
        missing.append("multiple exposure levels")
    if spec.calibration.observation_time_count < 2:
        missing.append("multiple observation times")
    if not spec.calibration.uncertainty_quantified:
        missing.append("quantified calibration uncertainty")
    if spec.calibration.heldout_record_count == 0:
        missing.append("held-out validation evidence")
    if spec.endpoint.species != spec.population.species:
        missing.append("validated nonhuman-to-target-population extrapolation")

    transport = TransportInventory(
        preserved=(
            "stochastic time-to-event structure",
            "population-level survival and cumulative-incidence bookkeeping",
            "state transitions as a possible target-language structure",
        ),
        modified=(
            "nuclear decay becomes a hypothetical population-level failure process",
            "environmental exposure may affect failure hazard, repair state, or both",
            "a median endpoint is retained only as one cumulative-mortality constraint",
        ),
        discarded=(
            "nuclear memorylessness",
            "a universal constant decay rate",
            "a material half-life for a human",
            "daughter-nuclide rate inheritance",
            "independent non-interacting ensemble semantics",
            "prediction for any actual person",
        ),
        unknown=free_parameters,
    )
    inventory = ConstraintInventory(
        endpoint=spec.endpoint,
        cumulative_mortality_at_endpoint=0.5,
        normalized_observation_time=1.0,
        environmental_protocol_digest=spec.environment.digest,
        population_protocol_digest=spec.population.digest,
        toxicokinetic_link_digest=spec.toxicokinetic_link.digest,
        calibration_evidence_digest=spec.calibration.digest,
    )
    return IdentifiabilityDiagnostic(
        spec=spec,
        status=IdentifiabilityStatus.UNDERIDENTIFIED_DYNAMIC_MODEL,
        validation=ValidationStatus.UNVALIDATED,
        constraint_inventory=inventory,
        free_parameters=free_parameters,
        missing_evidence=tuple(missing),
        transport=transport,
        family_witnesses=witnesses,
        discriminating_experiments=(
            "compare cumulative mortality at multiple normalized times away from the "
            "single fitted median endpoint",
            "use multiple exposure levels and schedules to distinguish dose-response "
            "families",
            "measure mechanism-specific state or repair markers to distinguish part-hazard "
            "change from redundancy loss",
            "evaluate the selected family on a held-out synthetic or ethically and legally "
            "obtained population dataset",
        ),
    )


def _require_nonempty(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_nonempty_strings(
    name: str,
    values: object,
    *,
    require_values: bool = False,
) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    if require_values and not values:
        raise ValueError(f"{name} must not be empty")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{name} must contain non-empty strings")


def _require_unique(name: str, values: tuple[object, ...]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must be unique")


def _require_enum(name: str, value: object, enum_type: type[Enum]) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{name} must be a {enum_type.__name__}")


def _require_finite_real(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


def _require_positive_finite(name: str, value: object) -> None:
    _require_finite_real(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _require_nonnegative_finite(name: str, value: object) -> None:
    _require_finite_real(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_digest(name: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _require_route_metric(route: ExposureRoute, metric: ExposureMetric) -> None:
    if metric is ExposureMetric.AIR_CONCENTRATION_MG_PER_M3:
        if route is not ExposureRoute.INHALATION:
            raise ValueError("mg/m^3 concentration is supported only for inhalation")
    elif route is ExposureRoute.INHALATION:
        raise ValueError("the narrow inhalation endpoint requires concentration in mg/m^3")
