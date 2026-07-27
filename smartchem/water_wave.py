"""Typed compiler/runtime seam for one classical water-wave analogue calculation.

The executable slice is intentionally narrow: a scientist supplies a fully typed,
prescribed, stationary one-dimensional background and selects a long-wave characteristic.
The runtime evaluates ``c = sqrt(g h)`` and the selected ``U +/- c`` branch at every input
point, locating all isolated zero crossings.  It does not evolve a free surface and it
cannot emit scattering, thermal, quantum, laser, backreaction, or astrophysical claims.
"""
from __future__ import annotations

import math
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
from .ledger import BindingSchema, COMPILED, Session, Slot
from .program import (
    Adapter,
    ApprovedPlan,
    Artifact,
    AssemblyEvidence,
    AssemblySpec,
    Boundary,
    CalculationSpec,
    CandidatePlan,
    Certificate,
    ClaimScope,
    Component,
    EquivalenceContract,
    ExecutionReport,
    Identity,
    Invariant,
    ModelSpec,
    ObservableRequest,
    OutputContract,
    PhysicalIR,
    Quantity,
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
    _WATER_WAVE_EXECUTOR,
    _compiler_implementation_digest,
    _resource_wall,
)
from .water_wave_domain import (
    HorizonDiagnostic,
    HorizonStatus,
    RegimeAssumptions,
    WaterWaveSpec,
    WaveRegime,
    WaveTarget,
    diagnose_horizon,
)

__all__ = [
    "ShallowWaterHorizonEngine",
    "WATER_WAVE_CASUALTIES",
    "WATER_WAVE_OMISSIONS",
    "compile_session_water_wave_horizon",
    "compile_water_wave_horizon",
    "water_wave_slot",
]


WATER_WAVE_CASUALTIES = (
    "an astrophysical or literal black hole",
    "Einstein dynamics or literal spacetime curvature",
    "a singularity or event horizon for matter",
    "spontaneous quantum Hawking radiation",
    "a Hawking temperature or thermal spectrum",
    "scattering coefficients or mode-conversion amplitudes",
    "dispersive gravity-capillary branch horizons",
    "black-hole-laser gain or instability",
    "wave/mean-flow backreaction",
)

WATER_WAVE_OMISSIONS = (
    "profile measurement and provenance are not represented or validated by this executor",
    "no wavelength or laboratory frequency establishes kh << 1",
    "capillarity and the gravity-dominance condition are not quantified",
    "stationary continuity and momentum balances are not checked",
    "measurement and spatial-resolution uncertainty are not available",
    "linear-interpolation discrepancy is not quantified",
)


class ShallowWaterHorizonEngine:
    """Deterministic built-in engine with an immutable calculation identity."""

    name = "SmartChem prescribed-background shallow-water horizon diagnostic"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": "branch-specific U +/- sqrt(g*h) crossing diagnostic",
            "arithmetic": "IEEE-754 binary64",
            "crossing_location": "linear interpolation of selected characteristic",
            "profile_units": {
                "position": "m",
                "depth": "m",
                "normal_velocity": "m/s",
                "gravity": "m/s^2",
            },
            "version": 1,
        }

    def solve(self, spec: WaterWaveSpec) -> HorizonDiagnostic:
        self.calls += 1
        return diagnose_horizon(spec)


def water_wave_slot(name: str, written: str) -> Slot:
    """An open scientist-owned choice; no menu pretends to exhaust the physics."""
    return Slot(
        name=name,
        written=written,
        schema=BindingSchema((WaterWaveSpec,)),
    )


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                observable_id="water_wave_horizon",
                kind="branch-specific shallow-water kinematic horizon diagnostic",
                unit="structured SI record",
                support=(
                    "every strict crossing bracketed by adjacent supplied samples under "
                    "the declared linear interpolant"
                ),
                resolution="linear interpolation between every adjacent supplied sample",
                precision=(
                    "retain binary64 values; no measurement or interpolation uncertainty "
                    "is invented"
                ),
                coverage=(
                    "all supplied profile points and all sample-bracketed "
                    "selected-characteristic crossings"
                ),
                diagnostics=(
                    "sample-bounded NO_BRACKET_IN_SUPPLIED_SAMPLES status",
                    "black/white orientation along the declared flow direction",
                    "bracketing sample indices for every crossing",
                ),
                retention=(
                    "typed water-wave specification",
                    "all computed characteristic samples",
                    "all horizon points",
                ),
            ),
            ObservableRequest(
                observable_id="water_wave_characteristic_profile",
                kind="pointwise selected shallow-water characteristic",
                unit="m, m/s, dimensionless",
                support="every supplied profile point without downsampling",
                resolution="exactly the scientist-supplied spatial sampling",
                precision="retain every binary64 input and derived value",
                coverage="position, depth, U, sqrt(g h), selected U +/- c, and Froude number",
                diagnostics=("input/output point count equality",),
                retention=("every CharacteristicSample in source order",),
            ),
        ),
        diagnostics=(
            "typed target/regime/branch/orientation verdicts",
            "analogue-scope and casualty verdict",
            "exact output inventory",
            "refusals, invalid results, resource walls, and failures",
        ),
        retention=(
            "source program",
            "complete typed plan and approval",
            "full diagnostic checkpoint",
            "every requested observable payload",
            "run record and certificate",
        ),
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation(
            "water-wave-subject-is-typed-and-supported",
            ObligationStage.PRE,
            "smartchem.water_wave/typed-supported-subject-v1",
            "the approved subject is the supported typed nondispersive horizon request",
        ),
        ValidityObligation(
            "water-wave-scope-remains-analogue",
            ObligationStage.PRE,
            "smartchem.water_wave/analogue-casualty-boundary-v1",
            "the plan remains an experimental classical analogue with every literal casualty",
        ),
        ValidityObligation(
            "water-wave-diagnostic-is-complete",
            ObligationStage.POST,
            "smartchem.water_wave/complete-diagnostic-v1",
            "the diagnostic retains every input point, derived characteristic, and crossing",
        ),
        ValidityObligation(
            "water-wave-orientation-matches-request",
            ObligationStage.POST,
            "smartchem.water_wave/orientation-v1",
            "any horizons meet the scientist-selected black, white, or pair semantics",
        ),
        ValidityObligation(
            "water-wave-output-inventory-exact",
            ObligationStage.POST,
            "smartchem.water_wave/output-inventory-v1",
            "emitted observable identities exactly equal the frozen output contract",
        ),
    )


def _unsupported_assumptions(assumptions: RegimeAssumptions) -> tuple[str, ...]:
    return tuple(
        name
        for name in (
            "stationary",
            "inviscid",
            "irrotational",
            "gravity_only",
            "shallow_water",
            "linear_perturbations",
            "one_dimensional",
            "prescribed_background",
            "no_retained_wave_forcing",
            "negligible_reflections",
        )
        if not getattr(assumptions, name)
    )


def compile_water_wave_horizon(
    source: SourceProgram | str,
    spec: WaterWaveSpec,
    engine: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """Compile, but do not run, the narrow classical water-wave analogue."""
    if isinstance(source, str):
        source = SourceProgram(source)
    if not isinstance(source, SourceProgram):
        raise TypeError("source must be SourceProgram or str")
    if not isinstance(spec, WaterWaveSpec):
        raise TypeError("spec must be a WaterWaveSpec")

    source_theory = SourceTheory(
        name="black-hole wave-kinematics source theory",
        axioms=(
            "a horizon is branch-specific and operationally defined by a zero lab-frame "
            "group characteristic",
            "black/white orientation depends on the direction of flow and the selected "
            "escape or entry characteristic",
            "source spacetime dynamics do not transport through a kinematic analogue",
        ),
        provenance=(
            "https://arxiv.org/abs/gr-qc/0205099",
            "https://arxiv.org/abs/1004.5546",
            "https://arxiv.org/abs/1806.05539",
        ),
    )
    target = TargetIntent(
        statement=source.text,
        target_scale="one prescribed one-dimensional open-channel background profile",
        requested_meaning=(
            f"{spec.target.value} for the {spec.branch.value} characteristic in the "
            f"{spec.regime.value} regime, with {spec.requested_orientation.value} "
            "orientation semantics"
        ),
    )
    resolved = ResolvedDomainProgram(
        source.digest,
        spec,
        target,
        source_theory,
        shepherd_session_digest,
    )
    model = ModelSpec(
        name="prescribed-background nondispersive shallow-water characteristic model",
        equations=(
            "c(x) = sqrt(g h(x))",
            "lambda_counter(x) = U(x) - sign(U) c(x)",
            "lambda_co(x) = U(x) + sign(U) c(x)",
            "Fr(x) = abs(U(x)) / c(x)",
            "a branch horizon is an isolated strict zero crossing of selected lambda",
        ),
        assumptions=(
            "stationary one-dimensional prescribed background",
            "inviscid, irrotational, gravity-only shallow water",
            "linear perturbations, unidirectional flow, no retained wave forcing or "
            "reflections",
            "profile values are already expressed in the fixed SI fields of WaterWaveSpec",
        ),
        valid_if=(
            "every RegimeAssumptions flag required by this model is true",
            "target is KINEMATIC_HORIZON",
            "regime is NONDISPERSIVE_SHALLOW_WATER",
            "critical points are isolated and bracket strict sign changes",
        ),
        postconditions=(
            "every input point has one retained characteristic sample",
            "every sample-bracketed strict crossing is retained or a no-bracket-at-samples "
            "status is returned without claiming continuous-profile absence",
            "computed horizon orientations meet the approved scientist selection",
        ),
        conserved=(),
        version="1",
    )
    transport = TransportMap(
        source_theory.digest,
        target.digest,
        preserved=(
            "branch-specific propagation blocking kinematics",
            "zero lab-frame characteristic as the nondispersive horizon condition",
            "black/white time orientation under an explicit flow convention",
        ),
        modified=(
            "a source null-wave horizon becomes a long-water-wave characteristic crossing",
            "source geometry is represented only up to the effective 1+1 kinematic analogy",
        ),
        discarded=WATER_WAVE_CASUALTIES,
        unknown=(
            "whether the supplied profile was measured in the declared stationary regime",
            "profile-resolution and measurement uncertainty",
        ),
    )
    assembly = AssemblySpec(
        "prescribed sampled channel background",
        "one-dimensional SI profile point",
        (
            "samples remain in scientist-supplied position order",
            "linear interpolation is used only to locate a bracketed characteristic zero",
            "no unmeasured flow or wave dynamics are synthesized between samples",
        ),
    )
    claim_scope = ClaimScope(
        ClaimKind.ANALOGUE,
        "classical shallow-water analogue of black-hole wave kinematics",
        WATER_WAVE_CASUALTIES,
    )
    physical_ir = PhysicalIR(
        resolved_digest=resolved.digest,
        components=(
            Component(
                "prescribed-water-background",
                "one-dimensional shallow-water profile",
                Identity(
                    canonical_digest(spec),
                    "water-wave-background",
                    (
                        ("position-unit", "m"),
                        ("depth-unit", "m"),
                        ("normal-velocity-unit", "m/s"),
                        ("flow-direction", spec.flow_direction.value),
                    ),
                ),
                parameters=(
                    Quantity(
                        spec.gravitational_acceleration_m_s2,
                        "length/time^2",
                        "m/s^2",
                        source="scientist-approved WaterWaveSpec",
                    ),
                ),
            ),
        ),
        connections=(),
        reservoirs=(),
        boundaries=(
            Boundary(
                "prescribed-profile-boundary",
                ("prescribed-water-background",),
                "the background is fixed; wave/mean-flow backreaction is excluded",
            ),
        ),
        models=(model,),
        adapters=(
            Adapter(
                "long-wave analogue-kinematics adapter",
                "source black-hole wave-horizon kinematics",
                "selected shallow-water U +/- sqrt(g h) characteristic",
                (
                    "water_wave_horizon",
                    "water_wave_characteristic_profile",
                ),
                (
                    "nondispersive long-wave regime",
                    "explicit branch, orientation, and flow convention",
                ),
                "dispersion, dissipation, nonlinear waves, quantum state, and backreaction "
                "are outside this adapter",
            ),
        ),
        invariants=(
            Invariant(
                "complete profile retention",
                "one CharacteristicSample is emitted for every supplied ProfilePoint",
                "this approved WaterWaveSpec",
                "smartchem.water_wave/complete-diagnostic-v1",
            ),
            Invariant(
                "analogue casualty boundary",
                "water-wave evidence cannot promote claim scope to literal astrophysics",
                "this approved request and certificate",
                "smartchem.water_wave/analogue-casualty-boundary-v1",
            ),
        ),
        transport_maps=(transport,),
        transport_evidence=(
            TransportEvidence(
                transport.digest,
                (
                    "stationary one-dimensional linear nondispersive shallow-water regime",
                    "branch-specific strict characteristic crossing",
                ),
                (
                    "Schuetzhold and Unruh, Phys. Rev. D 66, 044019 (2002)",
                    "Euve et al., Phys. Rev. Lett. 124, 141101 (2020)",
                ),
                (
                    "experiment-specific validation of the supplied profile and regime",
                    "independent uncertainty and resolution study",
                ),
            ),
        ),
        assemblies=(assembly,),
        assembly_evidence=(
            AssemblyEvidence(
                assembly.digest,
                ("typed SI profile and deterministic complete-retention rule",),
                (
                    "measurement provenance for a physical flume",
                    "spatial convergence or interpolation validation",
                ),
            ),
        ),
        claim_scope=claim_scope,
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
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
                "exact categorical/status equality and binary64 equality of every retained "
                "profile, characteristic, crossing, and provenance field"
            ),
            numeric_tolerances=(),
            ordering="source profile order retained; horizon positions sorted by x",
            rng_policy="no RNG",
            checkpoint_policy=(
                "the full diagnostic is one indivisible call; an interrupted or "
                "post-check-failed result remains quarantined"
            ),
        ),
        _obligations(),
    )
    blockers: list[str] = []
    if contract != _default_output_contract():
        blockers.append(
            "this narrow water-wave executor can honor only its exact default output "
            "contract; changing support, resolution, precision, coverage, diagnostics, "
            "retention, or observable membership requires a different validated executor"
        )
    if spec.target is not WaveTarget.KINEMATIC_HORIZON:
        blockers.append(
            f"target {spec.target.value} is not implemented; this executor emits only "
            "the classical kinematic horizon diagnostic"
        )
    if spec.regime is not WaveRegime.NONDISPERSIVE_SHALLOW_WATER:
        blockers.append(
            f"regime {spec.regime.value} requires a different dispersion/dissipation/"
            "nonlinearity model; the Froude shortcut is refused"
        )
    missing_assumptions = _unsupported_assumptions(spec.assumptions)
    if missing_assumptions:
        blockers.append(
            "declared regime is outside this model; false assumptions: "
            + ", ".join(missing_assumptions)
        )
    unsupported_outputs = sorted(
        set(contract.observable_ids)
        - {"water_wave_horizon", "water_wave_characteristic_profile"}
    )
    if unsupported_outputs:
        blockers.append(
            "water-wave horizon executor cannot emit requested observable(s): "
            + ", ".join(unsupported_outputs)
        )
    calculation = CalculationSpec.from_oracle(engine)
    return CandidatePlan(
        request=request,
        model=model,
        solver=SolverSpec(
            name=getattr(engine, "name", type(engine).__qualname__),
            algorithm="deterministic branch-specific characteristic diagnostic",
            version="1",
            tolerances=(),
            stopping_policy="one complete profile call or no result",
            reproducibility="typed SI input, immutable calculation spec, and source digests",
        ),
        calculation=calculation,
        compiler_implementation_digest=_compiler_implementation_digest(),
        executor_id=_WATER_WAVE_EXECUTOR,
        transforms=(),
        predicted_resources=(
            ("engine calls", "1"),
            ("profile evaluations", str(len(spec.profile))),
            ("wall/memory", "linear in supplied profile length; measured, not guessed"),
        ),
        blockers=tuple(blockers),
        execution_lane=ExecutionLane.EXPERIMENTAL,
        limits=limits or RuntimeLimits(max_engine_calls=1),
    )


def compile_session_water_wave_horizon(
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
            "water-wave execution requires an outright COMPILED typed session; "
            f"received {session.outcome}"
        )
    if session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError(
            "water-wave execution requires a closed session with no unmapped post obligations"
        )
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if slot.typed_binding is None:
        raise TypeError(
            f"slot {slot_name!r} has no typed binding; text cannot authorize execution"
        )
    if not isinstance(slot.typed_binding.value, WaterWaveSpec):
        raise TypeError(
            f"slot {slot_name!r} is bound to {type(slot.typed_binding.value).__name__}, "
            "not a WaterWaveSpec"
        )
    return compile_water_wave_horizon(
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
    spec: WaterWaveSpec,
) -> ObligationResult:
    plan = approved.plan
    if obligation.evaluator_id == "smartchem.water_wave/typed-supported-subject-v1":
        false_assumptions = _unsupported_assumptions(spec.assumptions)
        passed = (
            spec.target is WaveTarget.KINEMATIC_HORIZON
            and spec.regime is WaveRegime.NONDISPERSIVE_SHALLOW_WATER
            and not false_assumptions
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "typed target, regime, branch, orientation, SI profile, and all required "
                "assumptions are present"
                if passed
                else "request is outside the supported typed nondispersive horizon model"
            ),
        )
    if obligation.evaluator_id == "smartchem.water_wave/analogue-casualty-boundary-v1":
        scope = plan.request.physical_ir.claim_scope
        passed = (
            scope.kind is ClaimKind.ANALOGUE
            and scope
            == ClaimScope(
                ClaimKind.ANALOGUE,
                "classical shallow-water analogue of black-hole wave kinematics",
                WATER_WAVE_CASUALTIES,
            )
            and plan.request.physical_ir.evidence_status
            is EvidenceStatus.STRUCTURAL_TOY
            and plan.execution_lane is ExecutionLane.EXPERIMENTAL
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "claim is a structural-toy classical analogue and retains the exact "
                "referent and every casualty"
                if passed
                else "analogue scope, experimental evidence, or casualty list was widened"
            ),
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _diagnostic_is_complete(
    diagnostic: HorizonDiagnostic,
    spec: WaterWaveSpec,
) -> bool:
    try:
        reference = diagnose_horizon(spec)
    except ValueError:
        return False
    if diagnostic != reference:
        return False
    if diagnostic.spec != spec or len(diagnostic.samples) != len(spec.profile):
        return False
    for point, sample in zip(spec.profile, diagnostic.samples):
        if (
            sample.position_m != point.position_m
            or sample.depth_m != point.depth_m
            or sample.normal_velocity_m_s != point.normal_velocity_m_s
            or not math.isfinite(sample.gravity_wave_speed_m_s)
            or not math.isfinite(sample.selected_characteristic_m_s)
            or not math.isfinite(sample.froude_number)
        ):
            return False
    if diagnostic.status is HorizonStatus.NO_BRACKET_IN_SUPPLIED_SAMPLES:
        return not diagnostic.horizons
    return bool(diagnostic.horizons)


def _post_result(
    obligation: ValidityObligation,
    diagnostic: HorizonDiagnostic,
    spec: WaterWaveSpec,
    emitted: tuple[str, ...],
    expected: tuple[str, ...],
) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.water_wave/complete-diagnostic-v1":
        passed = _diagnostic_is_complete(diagnostic, spec)
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            (
                f"retained {len(diagnostic.samples)} of {len(spec.profile)} samples and "
                f"{len(diagnostic.horizons)} horizon points; status={diagnostic.status.value}"
            ),
        )
    if obligation.evaluator_id == "smartchem.water_wave/orientation-v1":
        passed = diagnostic.status is not HorizonStatus.ORIENTATION_MISMATCH
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            (
                f"requested={spec.requested_orientation.value}; "
                f"found={[item.orientation.value for item in diagnostic.horizons]}; "
                f"status={diagnostic.status.value}"
            ),
        )
    if obligation.evaluator_id == "smartchem.water_wave/output-inventory-v1":
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


def _execute_water_wave_horizon(
    approved: ApprovedPlan,
    engine: object,
    *,
    actual_calculation: CalculationSpec,
    journal_path: str | os.PathLike[str] | None = None,
) -> ExecutionReport:
    """Execute after the common approval/compiler/calculation preflight in program.execute."""
    plan = approved.plan
    resolved = plan.request.resolved
    if (
        not isinstance(resolved, ResolvedDomainProgram)
        or not isinstance(resolved.subject, WaterWaveSpec)
    ):
        raise TypeError("water-wave executor requires a ResolvedDomainProgram WaterWaveSpec")
    spec = resolved.subject
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
                record = journal.refused(
                    f"precondition {obligation.name} ended {verdict.outcome.value}: "
                    f"{verdict.detail}"
                )
                return ExecutionReport(record, None, None)

        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=0,
            call_label="water-wave engine calls",
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
            raise TypeError("water-wave engine must expose solve(WaterWaveSpec)")
        try:
            diagnostic = solver(spec)
        except ValueError as error:
            return ExecutionReport(
                journal.invalid(f"approved water-wave input is unclassifiable: {error}"),
                None,
                None,
            )
        if not isinstance(diagnostic, HorizonDiagnostic):
            return ExecutionReport(
                journal.invalid(
                    "water-wave engine returned no typed HorizonDiagnostic"
                ),
                None,
                None,
            )
        checkpoint = Artifact(
            "checkpoint:water-wave-diagnostic",
            "checkpoint",
            canonical_digest(diagnostic),
            True,
            False,
            detail=(
                f"{diagnostic.status.value}; {len(diagnostic.samples)} samples; "
                f"{len(diagnostic.horizons)} horizons"
            ),
            payload=diagnostic,
        )
        journal.add_checkpoint(checkpoint)
        if CalculationSpec.from_oracle(engine).digest != plan.calculation.digest:
            raise RuntimeError(
                "CalculationSpec changed during the approved water-wave engine call"
            )
        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=1,
            call_label="water-wave engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)

        payloads: dict[str, object] = {
            "water_wave_horizon": diagnostic,
            "water_wave_characteristic_profile": diagnostic.samples,
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
                    f"samples={len(diagnostic.samples)}"
                ),
                payload=payload,
            ))
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        journal.add_cache_state("no cache: one deterministic complete profile call")

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
                record = journal.invalid(
                    f"postcondition {obligation.name} ended {verdict.outcome.value}: "
                    f"{verdict.detail}"
                )
                return ExecutionReport(record, None, None)

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
            omissions=WATER_WAVE_OMISSIONS,
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
        record = journal.complete()
        if record.status is not RunStatus.COMPLETE:
            return ExecutionReport(record, None, None)
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
                method="prescribed-background nondispersive shallow-water diagnostic v1",
                support=next(
                    item.support
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                seconds=elapsed,
                uncertainty_note=(
                    "No measurement, model-discrepancy, or interpolation uncertainty was "
                    "provided or inferred; evidence remains STRUCTURAL_TOY."
                ),
                notes=(
                    "Classical analogue kinematics only; see certificate casualties."
                ),
            )
            for observable_id in emitted_ids
        )
        return ExecutionReport(
            record,
            SimulationResult(record.run_id, values, certificate.digest),
            certificate,
        )
    except Exception as error:
        if journal.record.status is RunStatus.RUNNING:
            record = journal.failed(f"{type(error).__name__}: {error}")
            return ExecutionReport(record, None, None)
        raise
