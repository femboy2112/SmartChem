"""Typed compiler/runtime seam for the human-isotope identifiability diagnostic.

The executable slice is deliberately a negative scientific result.  A scientist supplies
every target, population, granularity, assembly, exposure, toxicokinetic, endpoint, and
calibration choice.  The engine then shows that one median lethality endpoint is compatible
with distinct dynamic survival families.  It emits the identified constraint, free
parameters, missing evidence, transport casualties, and two mathematical witnesses.

It does not fit a mortality model, predict an actual person or population, turn LD50/LC50
into a rate, or authorize human experimentation.
"""
from __future__ import annotations

import os
import time

from .contracts import (
    ClaimKind,
    EvidenceStatus,
    ExecutionLane,
    ObligationOutcome,
    ObligationResult,
    ObligationStage,
    RunStatus,
    ValidityObligation,
    canonical_digest,
)
from .human_isotope_domain import (
    EvidenceBasis,
    HumanIsotopeSpec,
    HumanTarget,
    IdentifiabilityDiagnostic,
    IdentifiabilityStatus,
    ValidationStatus,
    diagnose_human_isotope,
)
from .ledger import BindingSchema, COMPILED, Session, Slot
from .program import (
    Adapter,
    ApprovedPlan,
    Artifact,
    AssemblyEvidence,
    AssemblyHypothesis,
    AssemblySpec,
    Boundary,
    CalculationSpec,
    CalibrationSpec,
    CandidatePlan,
    Certificate,
    ClaimScope,
    Component,
    EquivalenceContract,
    ExecutionReport,
    Identity,
    Invariant,
    ModelPatch,
    ModelSpec,
    ObservableRequest,
    OutputContract,
    PhysicalIR,
    ResolvedDomainProgram,
    RunJournal,
    RuntimeLimits,
    SimulationRequest,
    SimulationResult,
    SolverSpec,
    SourceProgram,
    SourceTheory,
    StructuredObservableValue,
    TargetIntent,
    TransportEvidence,
    TransportMap,
    _HUMAN_ISOTOPE_EXECUTOR,
    _ExecutionAdmissionSnapshot,
    _compiler_implementation_digest,
    _execution_admission_error,
    _require_runtime_dispatch,
    _resource_wall,
)

__all__ = [
    "HUMAN_ISOTOPE_CASUALTIES",
    "HUMAN_ISOTOPE_OMISSIONS",
    "HumanIsotopeIdentifiabilityEngine",
    "compile_human_isotope_identifiability",
    "compile_session_human_isotope_identifiability",
    "human_isotope_slot",
]


HUMAN_ISOTOPE_CASUALTIES = (
    "a human is a radioactive isotope or nucleus",
    "nuclear memorylessness or a constant nuclear decay rate at organism scale",
    "a material half-life belonging to a human",
    "daughter-nuclide or radioactive-chain semantics for biological failure",
    "LD50 or LC50 as a per-time decay constant or hazard",
    "a universal human LD50 or LC50",
    "a unique dynamic, dose-response, toxicokinetic, or assembly model",
    "a mortality prediction for an actual person or population",
    "a causal, clinical, regulatory, or toxicological safety claim",
    "authority for direct human experimentation",
    "validation of the original isotope metaphor",
)

HUMAN_ISOTOPE_OMISSIONS = (
    "no observed human or animal records are included in this structural-toy run",
    "one hypothetical median endpoint does not identify time or dose-response shape",
    "assembly, repair, and environmental hazard mechanisms are scientist-selected hypotheses",
    "the toxicokinetic link is declared but has no fitted parameters or validation evidence",
    "background and exposure hazards are not separated",
    "competing-risk dependence and cause-specific cumulative incidence are not estimated",
    "calibration uncertainty and held-out validation are absent",
    "no prediction for an actual person or population is emitted",
)


class HumanIsotopeIdentifiabilityEngine:
    """Deterministic built-in engine with an immutable calculation identity."""

    name = "SmartChem human-isotope structural identifiability diagnostic"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": (
                "single-median-endpoint dynamic-family identifiability diagnostic"
            ),
            "witnesses": (
                "normalized exponential survival",
                "normalized Weibull shape-2 survival",
            ),
            "arithmetic": "IEEE-754 binary64",
            "endpoint_semantics": (
                "cumulative mortality equals 0.5 at normalized observation time 1"
            ),
            "version": 1,
        }

    def solve(self, spec: HumanIsotopeSpec) -> IdentifiabilityDiagnostic:
        self.calls += 1
        return diagnose_human_isotope(spec)


def human_isotope_slot(name: str, written: str) -> Slot:
    """An open scientist-owned interpretation; the compiler supplies no default human."""
    return Slot(
        name=name,
        written=written,
        schema=BindingSchema((HumanIsotopeSpec,)),
    )


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                observable_id="human_isotope_identifiability",
                kind="single-endpoint dynamic-model identifiability diagnostic",
                unit="typed structural record; no mortality-rate unit",
                support=(
                    "the complete scientist-specified target, population, assembly, "
                    "exposure, endpoint, and evidence record"
                ),
                resolution=(
                    "one complete structural diagnosis with no field suppression"
                ),
                precision=(
                    "retain exact categorical values and binary64 witness probabilities"
                ),
                coverage=(
                    "constraint, validation state, free parameters, missing evidence, "
                    "transport, witnesses, and discriminating experiments"
                ),
                diagnostics=(
                    "endpoint is a cumulative-probability constraint, never a rate",
                    "distinct compatible dynamic families",
                    "explicit UNVALIDATED status",
                ),
                retention=(
                    "complete typed HumanIsotopeSpec",
                    "complete IdentifiabilityDiagnostic",
                ),
            ),
            ObservableRequest(
                observable_id="human_isotope_constraint_inventory",
                kind="complete median-endpoint constraint inventory",
                unit="typed endpoint/protocol digest record",
                support=(
                    "endpoint, environmental protocol, population protocol, "
                    "toxicokinetic link, and calibration evidence"
                ),
                resolution="every inventory field retained exactly once",
                precision="exact categorical and digest identity",
                coverage=(
                    "0.5 cumulative mortality only at the declared endpoint and window"
                ),
                diagnostics=("no conversion from dose or concentration to hazard",),
                retention=("complete typed ConstraintInventory",),
            ),
            ObservableRequest(
                observable_id="human_isotope_family_witnesses",
                kind="compatible normalized dynamic-family witnesses",
                unit="normalized time and cumulative probability",
                support=(
                    "endpoint time 1 and discriminating half-window time 0.5 for both "
                    "families"
                ),
                resolution="both witnesses and all retained parameters",
                precision="binary64 evaluation of the declared closed forms",
                coverage=(
                    "exponential and Weibull-shape-2 witnesses; no human prediction"
                ),
                diagnostics=(
                    "both equal 0.5 at the endpoint",
                    "the families differ away from the endpoint",
                ),
                retention=("every typed FamilyWitness in declared order",),
            ),
        ),
        diagnostics=(
            "typed source/target/transport/assembly/calibration verdicts",
            "experimental-proxy scope and complete casualty verdict",
            "exact output inventory",
            "refusals, invalid results, resource walls, and failures",
        ),
        retention=(
            "source program and scientist-confirmed typed interpretation",
            "complete plan and approval",
            "full diagnostic checkpoint",
            "every requested observable payload",
            "run record and certificate",
        ),
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation(
            "human-isotope-subject-is-typed-and-supported",
            ObligationStage.PRE,
            "smartchem.human_isotope/typed-supported-subject-v1",
            "the approved subject is the supported typed structural diagnostic",
        ),
        ValidityObligation(
            "human-isotope-scope-remains-structural-and-unvalidated",
            ObligationStage.PRE,
            "smartchem.human_isotope/proxy-casualty-boundary-v1",
            "the plan remains a structural-toy experimental proxy with every casualty",
        ),
        ValidityObligation(
            "median-endpoint-is-not-a-rate",
            ObligationStage.PRE,
            "smartchem.human_isotope/endpoint-semantics-v1",
            "LD50/LC50 remains a protocol-bound cumulative-probability endpoint",
        ),
        ValidityObligation(
            "human-isotope-diagnostic-is-complete",
            ObligationStage.POST,
            "smartchem.human_isotope/complete-diagnostic-v1",
            "the diagnostic equals an independent recomputation and retains both witnesses",
        ),
        ValidityObligation(
            "human-isotope-output-inventory-is-exact",
            ObligationStage.POST,
            "smartchem.human_isotope/output-inventory-v1",
            "emitted observable identities exactly equal the frozen output contract",
        ),
    )


def _synthetic_calibration_is_supported(spec: HumanIsotopeSpec) -> bool:
    calibration = spec.calibration
    return (
        calibration.dose_level_count == 1
        and calibration.observation_time_count == 1
        and calibration.population_count == 1
        and calibration.record_count == 1
        and not calibration.uncertainty_quantified
        and calibration.heldout_record_count == 0
        and calibration.heldout_dataset_digest is None
)


def _human_isotope_model() -> ModelSpec:
    return ModelSpec(
        name="single-median-endpoint structural identifiability model",
        equations=(
            "P(event by declared observation window | declared median endpoint protocol) = 0.5",
            "exponential witness: F(tau/2) = 1 - exp(-ln(2)/2)",
            "Weibull-shape-2 witness: F(tau/2) = 1 - exp(-ln(2)/4)",
            "both witnesses satisfy F(tau) = 0.5 and therefore prove non-uniqueness",
        ),
        assumptions=(
            "the endpoint is used only at its declared population, route, protocol, and window",
            "the two normalized witness curves are mathematical counterexamples to uniqueness",
            "the selected assembly and toxicokinetic link are hypotheses, not fitted mechanisms",
        ),
        valid_if=(
            "every scientist-owned choice is present in HumanIsotopeSpec",
            "endpoint, environmental protocol, and toxicokinetic route/metric agree",
            "the one scheduled exposure equals the one declared median endpoint protocol",
        ),
        postconditions=(
            "no empirically calibrated or actual-human mortality probability is emitted",
            "both family witnesses satisfy the endpoint and disagree away from it",
            "validation remains UNVALIDATED regardless of successful execution",
        ),
        conserved=(),
        version="1",
    )


def compile_human_isotope_identifiability(
    source: SourceProgram | str,
    spec: HumanIsotopeSpec,
    engine: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """Compile, but do not run, the narrow structural identifiability diagnostic."""
    if isinstance(source, str):
        source = SourceProgram(source)
    if not isinstance(source, SourceProgram):
        raise TypeError("source must be SourceProgram or str")
    if not isinstance(spec, HumanIsotopeSpec):
        raise TypeError("spec must be a HumanIsotopeSpec")

    diagnostic = diagnose_human_isotope(spec)
    source_theory = SourceTheory(
        name="radioactive-decay source vocabulary",
        axioms=(
            "constant-rate nuclear decay is memoryless and has exponential survival",
            "a material half-life is derived from one constant nuclear rate",
            "an organism-level survival process need not preserve either axiom",
        ),
        provenance=(
            "https://doi.org/10.1006/jtbi.2001.2430",
            "https://www.oecd.org/content/dam/oecd/en/publications/reports/2022/06/"
            "test-no-425-acute-oral-toxicity-up-and-down-procedure_g1gh2953/"
            "9789264071049-en.pdf",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC3396320/",
        ),
    )
    target = TargetIntent(
        statement=source.text,
        target_scale=(
            f"{spec.population.population}; granularity={spec.granularity.level.value}"
        ),
        requested_meaning=(
            f"{spec.target.value}: diagnose what the declared {spec.endpoint.kind.value} "
            "endpoint constrains after the scientist-selected source-to-target transport"
        ),
    )
    resolved = ResolvedDomainProgram(
        source.digest,
        spec,
        target,
        source_theory,
        shepherd_session_digest,
    )
    model = _human_isotope_model()
    transport = TransportMap(
        source_theory.digest,
        target.digest,
        preserved=diagnostic.transport.preserved,
        modified=diagnostic.transport.modified,
        discarded=diagnostic.transport.discarded,
        unknown=diagnostic.transport.unknown,
    )
    assembly_spec = AssemblySpec(
        name=f"scientist-selected {spec.assembly.kind.value} assembly hypothesis",
        granularity=(
            f"{spec.granularity.level.value}: "
            + ", ".join(spec.granularity.components)
        ),
        rules=(
            spec.assembly.rules
            + (f"repair: {spec.assembly.repair}",)
            + tuple(f"interaction: {item}" for item in spec.assembly.interactions)
        ),
    )
    assembly = AssemblyHypothesis(
        assembly_spec,
        (
            "assembly rules have no independent calibration or held-out validation",
            "component differentiation has no measured coarse-graining error",
        ),
        (
            "time-resolved component-state observations disagree with the declared rules",
            "a rival assembly predicts held-out endpoint trajectories better",
        ),
    )
    claim_scope = ClaimScope(
        ClaimKind.EXPERIMENTAL_PROXY,
        "structural identifiability of a scientist-specified human-isotope proxy",
        HUMAN_ISOTOPE_CASUALTIES,
    )
    calibration = CalibrationSpec(
        population=spec.population.population,
        protocol=(
            f"{spec.endpoint.kind.value}; route={spec.endpoint.route.value}; "
            f"exposure_duration_days={spec.endpoint.exposure_duration_days}; "
            f"observation_window_days={spec.endpoint.observation_window_days}"
        ),
        endpoints=(
            f"{spec.endpoint.value} {spec.endpoint.unit} -> cumulative mortality 0.5",
        ),
        identifiability=(
            "underidentified: one endpoint admits at least the two retained dynamic witnesses"
        ),
        validation_split=(
            f"heldout_record_count={spec.calibration.heldout_record_count}; "
            f"heldout_dataset_digest={spec.calibration.heldout_dataset_digest}"
        ),
        uncertainty_treatment=(
            spec.calibration.uncertainty_model
            if spec.calibration.uncertainty_quantified
            else "not quantified; this is a certificate omission"
        ),
    )
    model_patch = ModelPatch(
        "environment-conditioned biological failure proxy",
        (
            f"environment affects {spec.hazard_mechanism.effect.value}",
            f"recovery model is {spec.environment.recovery.value}",
            "the median endpoint constrains cumulative mortality only",
        ),
        HUMAN_ISOTOPE_CASUALTIES,
    )
    components = tuple(
        Component(
            component_id=f"proxy-component-{index}",
            kind=spec.granularity.level.value,
            identity=Identity(
                stable_id=canonical_digest(
                    (spec.granularity.level, name, spec.population.species)
                ),
                kind="scientist-declared proxy component class",
                state=(
                    ("name", name),
                    ("target-species", spec.population.species),
                ),
            ),
        )
        for index, name in enumerate(spec.granularity.components)
    )
    physical_ir = PhysicalIR(
        resolved_digest=resolved.digest,
        components=components,
        connections=(),
        reservoirs=(),
        boundaries=(
            Boundary(
                "declared-environmental-exposure",
                tuple(component.component_id for component in components),
                (
                    f"{spec.environment.agent}; route={spec.environment.route.value}; "
                    f"metric={spec.environment.metric.value}; "
                    f"schedule_digest={spec.environment.digest}"
                ),
            ),
        ),
        models=(model,),
        adapters=(
            Adapter(
                "decay-vocabulary-to-survival-identifiability adapter",
                "constant-rate nuclear-decay vocabulary",
                "scientist-selected population/reliability proxy",
                (
                    "human_isotope_identifiability",
                    "human_isotope_constraint_inventory",
                    "human_isotope_family_witnesses",
                ),
                (
                    "endpoint semantics are preserved as a cumulative-probability constraint",
                    "all target/assembly/exposure choices are explicit and scientist-owned",
                ),
                (
                    "nuclear material semantics, memorylessness, and actual-person "
                    "prediction do not cross this adapter"
                ),
            ),
        ),
        invariants=(
            Invariant(
                "endpoint is not a rate",
                "LD50/LC50 remains dose/concentration with a protocol and window",
                "this approved HumanIsotopeSpec",
                "smartchem.human_isotope/endpoint-semantics-v1",
            ),
            Invariant(
                "underidentification survives convergence",
                "successful execution cannot promote UNVALIDATED or choose a unique model",
                "this approved request and certificate",
                "smartchem.human_isotope/complete-diagnostic-v1",
            ),
        ),
        transport_maps=(transport,),
        transport_evidence=(
            TransportEvidence(
                transport.digest,
                (
                    "the target is population/functional survival vocabulary, not nuclear matter",
                    "the endpoint and assembly remain explicit hypotheses",
                ),
                (
                    "two closed-form dynamic witnesses establish structural non-uniqueness",
                    "OECD endpoint semantics distinguish dose from time rate",
                ),
                diagnostic.missing_evidence,
            ),
        ),
        assemblies=(assembly,),
        assembly_evidence=(
            AssemblyEvidence(
                assembly.digest,
                ("scientist-confirmed typed assembly hypothesis only",),
                assembly.missing_evidence,
            ),
        ),
        claim_scope=claim_scope,
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
        calibrations=(calibration,),
        model_patches=(model_patch,),
    )
    contract = output_contract or _default_output_contract()
    request = SimulationRequest(
        source,
        resolved,
        physical_ir,
        contract,
        equivalence_contract
        or EquivalenceContract(
            relation=(
                "exact categorical/digest equality and binary64 equality of every retained "
                "constraint, witness, casualty, and evidence field"
            ),
            numeric_tolerances=(),
            ordering="source order for components, witnesses, evidence, and casualties",
            rng_policy="no RNG",
            checkpoint_policy=(
                "the complete diagnostic is one indivisible call; interruption or failed "
                "independent recomputation quarantines it"
            ),
        ),
        _obligations(),
    )
    blockers: list[str] = []
    if contract != _default_output_contract():
        blockers.append(
            "this narrow human-isotope executor can honor only its exact default output "
            "contract; changing support, resolution, precision, coverage, diagnostics, "
            "retention, or observable membership requires a different validated executor"
        )
    if spec.target is not HumanTarget.COHORT_ALL_CAUSE_SURVIVAL:
        blockers.append(
            "this narrow lethality-endpoint executor supports only "
            "COHORT_ALL_CAUSE_SURVIVAL; functional thresholds, cause-specific incidence, "
            "and individual lifetimes require target-specific endpoint semantics and "
            "validated executors"
        )
    if spec.target is HumanTarget.INDIVIDUAL_LIFETIME_SAMPLE:
        blockers.append(
            "an individual lifetime sample is unsupported; a population median endpoint "
            "cannot authorize an actual-person or individualized prediction"
        )
    if spec.target is HumanTarget.CAUSE_SPECIFIC_CUMULATIVE_INCIDENCE:
        blockers.append(
            "cause-specific cumulative incidence requires all competing cause-specific "
            "hazards; this single all-cause family-witness executor cannot emit it"
        )
    if spec.endpoint.evidence_basis is not EvidenceBasis.HYPOTHETICAL_CONSTRAINT:
        blockers.append(
            "observational or cross-species evidence requires data-governance, applicability, "
            "and validation adapters not implemented by this structural-toy executor"
        )
    if not _synthetic_calibration_is_supported(spec):
        blockers.append(
            "multi-dose/time, uncertainty, held-out, or multi-population evidence requires "
            "a data-bound calibration/validation executor; this executor accepts only one "
            "synthetic endpoint record"
        )
    unsupported_outputs = sorted(
        set(contract.observable_ids)
        - {
            "human_isotope_identifiability",
            "human_isotope_constraint_inventory",
            "human_isotope_family_witnesses",
        }
    )
    if unsupported_outputs:
        blockers.append(
            "human-isotope identifiability executor cannot emit requested observable(s): "
            + ", ".join(unsupported_outputs)
        )
    return CandidatePlan(
        request=request,
        model=model,
        solver=SolverSpec(
            name=getattr(engine, "name", type(engine).__qualname__),
            algorithm="deterministic structural identifiability diagnostic",
            version="1",
            tolerances=(),
            stopping_policy="one complete diagnostic call or no result",
            reproducibility="typed immutable input, closed-form witnesses, and source digests",
        ),
        calculation=CalculationSpec.from_oracle(engine),
        compiler_implementation_digest=_compiler_implementation_digest(),
        executor_id=_HUMAN_ISOTOPE_EXECUTOR,
        transforms=(),
        predicted_resources=(
            ("engine calls", "1"),
            ("dynamic-family witnesses", "2"),
            ("wall/memory", "constant in this single-endpoint structural diagnostic"),
        ),
        blockers=tuple(blockers),
        execution_lane=ExecutionLane.EXPERIMENTAL,
        limits=limits or RuntimeLimits(max_engine_calls=1),
    )


def compile_session_human_isotope_identifiability(
    source: SourceProgram | str,
    session: Session,
    slot_name: str,
    engine: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
) -> CandidatePlan:
    """Bridge an outright-compiled typed scientist session into this executor."""
    if not isinstance(session, Session):
        raise TypeError("session must be a shepherd Session")
    if session.outcome != COMPILED:
        raise ValueError(
            "human-isotope execution requires an outright COMPILED typed session; "
            f"received {session.outcome}"
        )
    if session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError(
            "human-isotope execution requires a closed session with no unmapped "
            "post obligations"
        )
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if slot.typed_binding is None:
        raise TypeError(
            f"slot {slot_name!r} has no typed binding; text cannot authorize execution"
        )
    if not isinstance(slot.typed_binding.value, HumanIsotopeSpec):
        raise TypeError(
            f"slot {slot_name!r} is bound to "
            f"{type(slot.typed_binding.value).__name__}, not a HumanIsotopeSpec"
        )
    return compile_human_isotope_identifiability(
        source,
        slot.typed_binding.value,
        engine,
        output_contract=output_contract,
        equivalence_contract=equivalence_contract,
        limits=limits,
        shepherd_session_digest=canonical_digest(session),
    )


def _result(
    obligation: ValidityObligation,
    outcome: ObligationOutcome,
    detail: str,
) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _pre_result(
    obligation: ValidityObligation,
    approved: ApprovedPlan,
    spec: HumanIsotopeSpec,
) -> ObligationResult:
    plan = approved.plan
    if obligation.evaluator_id == "smartchem.human_isotope/typed-supported-subject-v1":
        passed = (
            type(spec) is HumanIsotopeSpec
            and spec.target is HumanTarget.COHORT_ALL_CAUSE_SURVIVAL
            and spec.endpoint.evidence_basis is EvidenceBasis.HYPOTHETICAL_CONSTRAINT
            and _synthetic_calibration_is_supported(spec)
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "complete typed target, population, granularity, assembly, exposure, "
                "toxicokinetic link, endpoint, and calibration choices are present"
                if passed
                else "request is outside the supported structural identifiability subject"
            ),
        )
    if obligation.evaluator_id == "smartchem.human_isotope/proxy-casualty-boundary-v1":
        scope = plan.request.physical_ir.claim_scope
        passed = (
            scope
            == ClaimScope(
                ClaimKind.EXPERIMENTAL_PROXY,
                "structural identifiability of a scientist-specified human-isotope proxy",
                HUMAN_ISOTOPE_CASUALTIES,
            )
            and plan.request.physical_ir.evidence_status
            is EvidenceStatus.STRUCTURAL_TOY
            and plan.execution_lane is ExecutionLane.EXPERIMENTAL
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "claim is a structural-toy experimental proxy with the exact referent "
                "and every casualty"
                if passed
                else "claim scope, evidence status, lane, or casualty list was widened"
            ),
        )
    if obligation.evaluator_id == "smartchem.human_isotope/endpoint-semantics-v1":
        inventory = diagnose_human_isotope(spec).constraint_inventory
        passed = (
            inventory.cumulative_mortality_at_endpoint == 0.5
            and inventory.normalized_observation_time == 1.0
            and spec.endpoint.unit in ("mg/kg", "mg/m^3")
            and "/time" not in spec.endpoint.unit
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                f"{spec.endpoint.kind.value} remains {spec.endpoint.value} "
                f"{spec.endpoint.unit} at the declared protocol/window; it is not a rate"
                if passed
                else "median endpoint semantics were changed or rate-like"
            ),
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _post_result(
    obligation: ValidityObligation,
    diagnostic: IdentifiabilityDiagnostic,
    spec: HumanIsotopeSpec,
    emitted: tuple[str, ...],
    expected: tuple[str, ...],
) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.human_isotope/complete-diagnostic-v1":
        reference = diagnose_human_isotope(spec)
        passed = (
            type(diagnostic) is IdentifiabilityDiagnostic
            and type(diagnostic.constraint_inventory)
            is type(reference.constraint_inventory)
            and type(diagnostic.transport) is type(reference.transport)
            and type(diagnostic.family_witnesses) is tuple
            and all(
                type(witness) is type(reference.family_witnesses[0])
                for witness in diagnostic.family_witnesses
            )
            and canonical_digest(diagnostic) == canonical_digest(reference)
            and diagnostic.status
            is IdentifiabilityStatus.UNDERIDENTIFIED_DYNAMIC_MODEL
            and diagnostic.validation is ValidationStatus.UNVALIDATED
            and len(diagnostic.family_witnesses) == 2
            and all(
                witness.cumulative_mortality_at_endpoint == 0.5
                for witness in diagnostic.family_witnesses
            )
            and (
                diagnostic.family_witnesses[0].cumulative_mortality_at_half_time
                != diagnostic.family_witnesses[1].cumulative_mortality_at_half_time
            )
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            (
                "independent recomputation retained the underidentified/UNVALIDATED "
                "diagnostic and both distinct endpoint-compatible witnesses"
                if passed
                else "diagnostic, validation boundary, or family witnesses were altered"
            ),
        )
    if obligation.evaluator_id == "smartchem.human_isotope/output-inventory-v1":
        passed = tuple(sorted(emitted)) == tuple(sorted(expected))
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            f"expected={sorted(expected)}, emitted={sorted(emitted)}",
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _preflight_human_isotope_identifiability(plan: CandidatePlan) -> None:
    expected = _human_isotope_model()
    if plan.executor_id != _HUMAN_ISOTOPE_EXECUTOR:
        raise ValueError("human-isotope preflight received a different executor plan")
    if plan.model != expected or plan.request.physical_ir.models != (expected,):
        raise ValueError("human-isotope executor requires its exact runtime-owned model")
    if plan.transforms:
        raise ValueError("human-isotope executor does not support transforms")


def _execute_human_isotope_identifiability(
    approved: ApprovedPlan,
    engine: object,
    *,
    actual_calculation: CalculationSpec,
    journal_path: str | os.PathLike[str] | None = None,
    _dispatch_token: object = None,
    _admission_snapshot: _ExecutionAdmissionSnapshot | None = None,
) -> ExecutionReport:
    """Execute after the common approval/compiler/calculation preflight."""
    _require_runtime_dispatch(_dispatch_token)
    plan = approved.plan
    _preflight_human_isotope_identifiability(plan)
    resolved = plan.request.resolved
    if (
        not isinstance(resolved, ResolvedDomainProgram)
        or not isinstance(resolved.subject, HumanIsotopeSpec)
    ):
        raise TypeError(
            "human-isotope executor requires a ResolvedDomainProgram HumanIsotopeSpec"
        )
    spec = resolved.subject
    if type(_admission_snapshot) is not _ExecutionAdmissionSnapshot:
        raise TypeError("human-isotope executor requires an execution admission snapshot")
    started = time.monotonic()
    journal = RunJournal(
        approved,
        backend=actual_calculation.engine_name,
        path=journal_path,
    )
    try:
        for artifact_id, kind, payload in (
            ("source-program", "source", plan.request.source),
            ("candidate-plan", "plan", plan),
            ("approval", "approval", approved.approval),
        ):
            journal.add_artifact(Artifact(
                artifact_id,
                kind,
                payload.digest,
                True,
                False,
                payload=payload,
            ))

        for obligation in plan.request.obligations:
            if obligation.stage is not ObligationStage.PRE:
                continue
            verdict = _pre_result(obligation, approved, spec)
            journal.add_obligation_result(verdict)
            if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                return ExecutionReport(
                    journal.refused(
                        f"precondition {obligation.name} ended "
                        f"{verdict.outcome.value}: {verdict.detail}"
                    ),
                    None,
                    None,
                )

        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=0,
            call_label="human-isotope engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        cap = plan.limits.max_engine_calls
        if cap is not None and cap < 1:
            return ExecutionReport(
                journal.incomplete(
                    f"approved max_engine_calls={cap} reached before the diagnostic call"
                ),
                None,
                None,
            )
        solver = getattr(engine, "solve", None)
        if not callable(solver):
            raise TypeError(
                "human-isotope engine must expose solve(HumanIsotopeSpec)"
            )
        diagnostic = solver(spec)
        admission_error = _execution_admission_error(
            approved, spec, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        if type(diagnostic) is not IdentifiabilityDiagnostic:
            return ExecutionReport(
                journal.invalid(
                    "human-isotope engine returned no exact IdentifiabilityDiagnostic"
                ),
                None,
                None,
            )
        checkpoint = Artifact(
            "checkpoint:human-isotope-identifiability",
            "checkpoint",
            canonical_digest(diagnostic),
            True,
            False,
            detail=(
                f"{diagnostic.status.value}/{diagnostic.validation.value}; "
                f"{len(diagnostic.family_witnesses)} family witnesses"
            ),
            payload=diagnostic,
        )
        journal.add_checkpoint(checkpoint)
        observed_calculation = CalculationSpec.from_oracle(engine)
        admission_error = _execution_admission_error(
            approved, spec, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        if observed_calculation.digest != plan.calculation.digest:
            raise RuntimeError(
                "CalculationSpec changed during the approved human-isotope engine call"
            )
        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=1,
            call_label="human-isotope engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)

        payloads: dict[str, object] = {
            "human_isotope_identifiability": diagnostic,
            "human_isotope_constraint_inventory": diagnostic.constraint_inventory,
            "human_isotope_family_witnesses": diagnostic.family_witnesses,
        }
        emitted: list[str] = []
        for observable_id in plan.request.output_contract.observable_ids:
            payload = payloads[observable_id]
            journal.add_artifact(Artifact(
                f"observable:{observable_id}",
                "observable",
                canonical_digest(payload),
                True,
                False,
                detail=(
                    f"complete {observable_id}; status={diagnostic.status.value}; "
                    f"validation={diagnostic.validation.value}"
                ),
                payload=payload,
            ))
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        journal.add_cache_state(
            "no cache: one deterministic complete structural diagnostic call"
        )

        for obligation in plan.request.obligations:
            if obligation.stage is not ObligationStage.POST:
                continue
            verdict = _post_result(
                obligation,
                diagnostic,
                spec,
                emitted_ids,
                plan.request.output_contract.observable_ids,
            )
            journal.add_obligation_result(verdict)
            if obligation.required and verdict.outcome is not ObligationOutcome.PASS:
                return ExecutionReport(
                    journal.invalid(
                        f"postcondition {obligation.name} ended "
                        f"{verdict.outcome.value}: {verdict.detail}"
                    ),
                    None,
                    None,
                )

        admission_error = _execution_admission_error(
            approved, spec, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        certificate = Certificate(
            source_digest=plan.request.source.digest,
            request_digest=plan.request.digest,
            plan_digest=plan.digest,
            approval_digest=approved.approval.digest,
            calculation_digest=actual_calculation.digest,
            compiler_implementation_digest=plan.compiler_implementation_digest,
            run_id=journal.record.run_id,
            run_status=RunStatus.COMPLETE,
            claim_scope=plan.request.physical_ir.claim_scope,
            evidence_status=plan.request.physical_ir.evidence_status,
            validity_results=journal.record.obligation_results,
            output_inventory=emitted_ids,
            casualties=plan.request.physical_ir.claim_scope.exclusions,
            omissions=HUMAN_ISOTOPE_OMISSIONS,
            failures=(),
        )
        journal.add_artifact(Artifact(
            "certificate",
            "certificate",
            certificate.digest,
            True,
            False,
            payload=certificate,
        ))
        elapsed = time.monotonic() - started
        values = tuple(
            StructuredObservableValue(
                observable_id=observable_id,
                payload=payloads[observable_id],
                unit=next(
                    item.unit
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                method="human-isotope structural identifiability diagnostic v1",
                support=next(
                    item.support
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                seconds=elapsed,
                uncertainty_note=(
                    "No probability uncertainty was inferred; the endpoint is hypothetical, "
                    "the dynamic family is underidentified, and validation is UNVALIDATED."
                ),
                notes=(
                    "Mathematical family witnesses only; see certificate casualties and "
                    "omissions. COMPLETE means artifact lifecycle completion."
                ),
            )
            for observable_id in emitted_ids
        )
        result = SimulationResult(
            journal.record.run_id,
            values,
            certificate.digest,
        )
        record = journal.complete()
        if record.status is not RunStatus.COMPLETE:
            return ExecutionReport(record, None, None)
        return ExecutionReport(record, result, certificate)
    except Exception as error:
        admission_error = _execution_admission_error(
            approved, spec, _admission_snapshot
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        record = journal.failed(
            f"{type(error).__name__}: {error}"
        )
        return ExecutionReport(record, None, None)
