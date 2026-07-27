"""Certified finite Ising-to-lattice-gas analogue executor.

The executor retains an exact eight-state C3 enumeration and a formal partition-function
identity.  It is an established mathematical change of variables between two finite models,
not evidence that their physical referents are literally identical.
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
from .ising_lattice_gas_domain import (
    C3_EDGES,
    C3_VERTICES,
    ExactEquilibriumMap,
    IsingLatticeGasSpec,
    derive_exact_equilibrium_map,
    exact_equilibrium_map_error,
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
    _ISING_LATTICE_GAS_EXECUTOR,
    _compiler_implementation_digest,
    _resource_wall,
)

__all__ = [
    "ISING_LATTICE_GAS_CASUALTIES",
    "ISING_LATTICE_GAS_OMISSIONS",
    "ExactC3EquilibriumEngine",
    "compile_ising_lattice_gas_equilibrium",
    "compile_session_ising_lattice_gas_equilibrium",
    "ising_lattice_gas_slot",
]


ISING_LATTICE_GAS_CASUALTIES = (
    "literal identity between magnetic spins and material particles",
    "literal identity between magnetic field and chemical potential",
    "material-specific calibration, equation of state, or experimental prediction",
    "dynamics, kinetics, diffusion, transport, Glauber updates, or Kawasaki updates",
    "particle-number conservation or a canonical-ensemble claim",
    "quantum, measurement, continuum-fluid, or chemical-reaction semantics",
    "thermodynamic limit, phase transition, critical exponent, or correlation length",
    "transfer to another graph, boundary, degree, dimension, or Hamiltonian",
)

ISING_LATTICE_GAS_OMISSIONS = (
    "beta remains a formal symbol; no floating partition value is emitted",
    "only the fixed three-vertex undirected cycle is enumerated",
    "the three undirected edges are each counted exactly once",
    "all eight microstates are retained; no sampling or output reduction is performed",
    "no finite-size extrapolation, dynamics, kinetics, or material calibration is attempted",
    "a different graph requires re-deriving its degree-dependent chemical-potential shift",
)


def _finite_c3_model() -> ModelSpec:
    """Return the runtime-owned exact model that licenses this certified mapping."""
    return ModelSpec(
        name="exact finite C3 Ising-to-lattice-gas equilibrium map",
        equations=(
            "H_I = -J*sum_edges(s_i*s_j) - h*sum_i(s_i)",
            "n_i = (s_i + 1)/2",
            "H_LG = -epsilon*sum_edges(n_i*n_j) - mu*sum_i(n_i)",
            "epsilon = 4*J; mu = 2*h - 4*J; C = 3*(h-J)",
            "H_I = H_LG + C",
            "Z_I(beta) = exp(-beta*C) * Xi_LG(beta)",
        ),
        assumptions=(
            "vertices are exactly (0,1,2)",
            "undirected edges are exactly (0,1),(1,2),(0,2), counted once",
            "J and h are exact integer energy ticks",
            "beta is formal and identical in both partition expressions",
        ),
        valid_if=(
            "all eight occupancy states are enumerated in lexicographic order",
            "every state obeys s_i=2*n_i-1 and H_I=H_LG+C",
            "the four class degeneracies are exactly 1,3,3,1",
        ),
        postconditions=(
            "all eight state records and all four state classes are retained",
            "the exact formal partition relation is retained without numeric exponentiation",
            "no physical meaning beyond the declared analogue is promoted",
        ),
        conserved=(
            "bijection cardinality: eight states on each side",
            "normalized equilibrium microstate probabilities under the formal identity",
        ),
        version="1",
    )


class ExactC3EquilibriumEngine:
    """One deterministic exact-integer enumeration."""

    name = "SmartChem exact finite C3 Ising-lattice-gas mapper"

    def __init__(self) -> None:
        self.calls = 0

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": "lexicographic enumeration of all 2^3 occupancy states",
            "arithmetic": "exact Python integers; beta retained as a formal symbol",
            "graph": {
                "vertices": C3_VERTICES,
                "undirected_edges_counted_once": C3_EDGES,
            },
            "state_order": "000,001,010,011,100,101,110,111",
            "version": 1,
        }

    def solve(self, spec: IsingLatticeGasSpec) -> ExactEquilibriumMap:
        self.calls += 1
        return derive_exact_equilibrium_map(spec)


def ising_lattice_gas_slot(name: str, written: str) -> Slot:
    """A scientist-owned J/h interpretation; no arbitrary-graph default is inferred."""
    return Slot(
        name=name,
        written=written,
        schema=BindingSchema((IsingLatticeGasSpec,)),
    )


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                "ising_lattice_gas_state_map",
                "complete exact finite cross-domain microstate map",
                "typed integer-energy record",
                "the fixed three-vertex undirected cycle C3",
                "every one of the eight microstates and all four degeneracy classes",
                "exact integer energy ticks; beta remains formal",
                (
                    "specification, parameter map, statewise spins/occupancies/counts/"
                    "energies, grouped classes, partition identity, and completeness"
                ),
                diagnostics=(
                    "statewise H_I=H_LG+C",
                    "M=2*N-3",
                    "sum(s_i*s_j)=4*Q-4*N+3",
                ),
                retention=(
                    "complete IsingLatticeGasSpec",
                    "all eight MicrostateMap records",
                    "all four StateClass records",
                ),
            ),
            ObservableRequest(
                "ising_lattice_gas_partition_identity",
                "formal exact finite partition-function identity",
                "typed symbolic exponent record",
                "the same C3 graph, J, h, energy unit, and formal beta on both sides",
                "all four occupancy classes with degeneracies 1,3,3,1",
                "exact integer exponent coefficients; no floating evaluation",
                (
                    "epsilon, mu, C through the complete map; lattice and Ising terms; "
                    "statewise, partition, and normalized-probability relations"
                ),
                diagnostics=(
                    "classwise exponent shift equals -C",
                    "degeneracy sum equals eight",
                ),
                retention=("complete PartitionIdentity",),
            ),
            ObservableRequest(
                "ising_lattice_gas_completeness_inventory",
                "zero-output-loss state and class inventory",
                "exact count record",
                "all states in the fixed C3 executor",
                "eight unique occupancy states, eight unique spin states, four classes",
                "exact integers and exact state identities",
                (
                    "expected/retained/unique counts, degeneracy sum, missing/duplicate "
                    "identities, and explicit output-reduction flag"
                ),
                diagnostics=(
                    "missing state IDs",
                    "duplicate state IDs",
                    "output reduction applied",
                ),
                retention=("complete CompletenessInventory",),
            ),
        ),
        diagnostics=(
            "typed source/target transport and exact casualty boundary",
            "runtime-owned model identity",
            "independent full-map recomputation",
            "refusal, invalidity, resource-wall, and failure states",
        ),
        retention=(
            "source program and scientist-confirmed typed interpretation",
            "complete plan and approval",
            "complete eight-state checkpoint",
            "all requested observable payloads",
            "run record and certificate",
        ),
    )


def _obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation(
            "finite-C3-subject-and-model-are-exact",
            ObligationStage.PRE,
            "smartchem.ising_lattice_gas/exact-subject-model-v1",
            "the approved subject and model equal the runtime-owned exact finite C3 form",
        ),
        ValidityObligation(
            "cross-domain-claim-remains-an-established-finite-analogue",
            ObligationStage.PRE,
            "smartchem.ising_lattice_gas/analogue-casualty-boundary-v1",
            "established algebra does not promote the distinct physical referents to identity",
        ),
        ValidityObligation(
            "all-eight-state-maps-are-exact",
            ObligationStage.POST,
            "smartchem.ising_lattice_gas/complete-state-map-v1",
            "independent enumeration matches every retained state and class exactly",
        ),
        ValidityObligation(
            "formal-partition-identity-is-exact",
            ObligationStage.POST,
            "smartchem.ising_lattice_gas/partition-identity-v1",
            "each class exponent differs by -C and every degeneracy is retained",
        ),
        ValidityObligation(
            "ising-lattice-output-inventory-is-exact",
            ObligationStage.POST,
            "smartchem.ising_lattice_gas/output-inventory-v1",
            "emitted observable identities exactly equal the frozen output contract",
        ),
    )


def compile_ising_lattice_gas_equilibrium(
    source: SourceProgram | str,
    spec: IsingLatticeGasSpec,
    engine: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """Compile, without running, the exact finite cross-domain map."""
    if isinstance(source, str):
        source = SourceProgram(source)
    if type(source) is not SourceProgram:
        raise TypeError("source must be an exact SourceProgram or str")
    if type(spec) is not IsingLatticeGasSpec:
        raise TypeError("spec must be an exact IsingLatticeGasSpec")

    source_theory = SourceTheory(
        "finite classical Ising equilibrium Hamiltonian",
        (
            "each C3 site has one spin s_i in {-1,+1}",
            "each of the three undirected C3 edges is counted exactly once",
            "H_I=-J sum_edges(s_i*s_j)-h sum_i(s_i)",
        ),
        (),
    )
    target = TargetIntent(
        source.text,
        "fixed three-site periodic lattice-gas occupancy model",
        (
            "interpret each spin exactly as n_i=(s_i+1)/2, retain every finite "
            "microstate, and expose the constant energy and partition shift"
        ),
    )
    resolved = ResolvedDomainProgram(
        source.digest,
        spec,
        target,
        source_theory,
        shepherd_session_digest,
    )
    model = _finite_c3_model()
    transport = TransportMap(
        source_theory.digest,
        target.digest,
        preserved=(
            "one-to-one finite configuration inventory",
            "statewise energy differences",
            "normalized equilibrium probability assigned to each paired state",
        ),
        modified=(
            "spin s_i becomes occupancy n_i=(s_i+1)/2",
            "J,h become epsilon=4J and mu=2h-4J",
            "the absolute energy zero shifts by C=3(h-J)",
        ),
        discarded=ISING_LATTICE_GAS_CASUALTIES,
        unknown=(),
    )
    assembly = AssemblySpec(
        "undirected-three-cycle-C3",
        "three labelled sites and three unordered edges",
        (
            "vertices=(0,1,2)",
            "edges=((0,1),(1,2),(0,2))",
            "each undirected edge counted exactly once",
        ),
    )
    scope = ClaimScope(
        ClaimKind.ANALOGUE,
        "exact finite configuration and equilibrium-weight map on the declared C3 models",
        ISING_LATTICE_GAS_CASUALTIES,
    )
    component = Component(
        "finite-C3-state-space",
        "complete finite configuration space",
        Identity(
            spec.digest,
            "three-site-Ising-and-lattice-gas-parameterization",
            (
                ("J-ticks", str(spec.coupling_j_ticks)),
                ("h-ticks", str(spec.field_h_ticks)),
                ("energy-unit", spec.energy_unit),
                ("state-count", "8"),
            ),
        ),
    )
    physical_ir = PhysicalIR(
        resolved_digest=resolved.digest,
        components=(component,),
        connections=(),
        reservoirs=(),
        boundaries=(
            Boundary(
                "fixed-C3-boundary",
                (component.component_id,),
                "exactly the declared three undirected edges; no arbitrary-graph transfer",
            ),
        ),
        models=(model,),
        adapters=(
            Adapter(
                "exact spin-occupancy affine adapter",
                "three Ising spins",
                "three binary lattice-gas occupancies",
                _default_output_contract().observable_ids,
                (
                    "s_i=2*n_i-1",
                    "all eight states retained",
                    "state-independent shift checked for every state",
                ),
                (
                    "the mapping is algebraically exact but discards literal identity "
                    "between the two physical vocabularies"
                ),
            ),
        ),
        invariants=(
            Invariant(
                "finite state completeness",
                "the ordered occupancy inventory is exactly 000 through 111",
                "this approved fixed-C3 request",
                "smartchem.ising_lattice_gas/complete-state-map-v1",
            ),
            Invariant(
                "affine energy identity",
                "H_I(state)=H_LG(mapped state)+3*(h-J) for all eight states",
                "this approved fixed-C3 request",
                "smartchem.ising_lattice_gas/partition-identity-v1",
            ),
        ),
        transport_maps=(transport,),
        transport_evidence=(
            TransportEvidence(
                transport.digest,
                (
                    "fixed graph C3",
                    "declared Hamiltonians",
                    "exact integer J and h",
                    "formal common beta",
                ),
                (
                    "symbolic substitution s_i=2*n_i-1",
                    "complete independent eight-state enumeration",
                ),
                (),
            ),
        ),
        assemblies=(assembly,),
        assembly_evidence=(
            AssemblyEvidence(
                assembly.digest,
                (
                    "explicit vertex tuple",
                    "explicit undirected edge tuple",
                    "complete 2^3 state inventory",
                ),
                (),
            ),
        ),
        claim_scope=scope,
        evidence_status=EvidenceStatus.ESTABLISHED,
    )
    contract = output_contract or _default_output_contract()
    request = SimulationRequest(
        source,
        resolved,
        physical_ir,
        contract,
        equivalence_contract
        or EquivalenceContract(
            (
                "exact equality of the complete typed specification, parameter map, "
                "eight ordered states, four ordered classes, formal partition terms, "
                "and completeness inventory"
            ),
            (),
            "lexicographic occupancy order 000,001,010,011,100,101,110,111",
            "no RNG",
            "one indivisible enumeration; interruption quarantines the checkpoint",
        ),
        _obligations(),
    )
    blockers: list[str] = []
    if contract != _default_output_contract():
        blockers.append(
            "this narrow finite-C3 executor can honor only its exact default output "
            "contract; changing support, resolution, precision, coverage, diagnostics, "
            "retention, or observable membership requires another validated executor"
        )
    return CandidatePlan(
        request=request,
        model=model,
        solver=SolverSpec(
            getattr(engine, "name", type(engine).__qualname__),
            "exact lexicographic enumeration and integer-algebra verification",
            "1",
            (),
            "retain and verify all eight states or emit no result",
            "fixed state order, exact integers, formal beta, no RNG",
        ),
        calculation=CalculationSpec.from_oracle(engine),
        compiler_implementation_digest=_compiler_implementation_digest(),
        executor_id=_ISING_LATTICE_GAS_EXECUTOR,
        transforms=(),
        predicted_resources=(
            ("engine calls", "1"),
            ("enumerated microstates", "8"),
            ("retained microstates", "8"),
            ("floating exponent evaluations", "0"),
        ),
        blockers=tuple(blockers),
        execution_lane=ExecutionLane.CERTIFIED,
        limits=limits or RuntimeLimits(max_engine_calls=1),
    )


def compile_session_ising_lattice_gas_equilibrium(
    source: SourceProgram | str,
    session: Session,
    slot_name: str,
    engine: object,
    **kwargs: object,
) -> CandidatePlan:
    """Bridge only a closed, typed, scientist-confirmed shepherd session."""
    if type(session) is not Session:
        raise TypeError("session must be an exact shepherd Session")
    if session.outcome != COMPILED or session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError(
            "finite-C3 execution requires an outright closed COMPILED typed session"
        )
    slot = next((item for item in session.spec.slots if item.name == slot_name), None)
    if slot is None:
        raise KeyError(f"compiled session has no slot named {slot_name!r}")
    if (
        slot.typed_binding is None
        or type(slot.typed_binding.value) is not IsingLatticeGasSpec
    ):
        raise TypeError(
            f"slot {slot_name!r} must hold an exact IsingLatticeGasSpec"
        )
    return compile_ising_lattice_gas_equilibrium(
        source,
        slot.typed_binding.value,
        engine,
        shepherd_session_digest=canonical_digest(session),
        **kwargs,
    )


def _payloads(result: ExactEquilibriumMap) -> dict[str, object]:
    return {
        "ising_lattice_gas_state_map": result,
        "ising_lattice_gas_partition_identity": result.partition,
        "ising_lattice_gas_completeness_inventory": result.completeness,
    }


def _result(
    obligation: ValidityObligation,
    outcome: ObligationOutcome,
    detail: str,
) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _pre_result(
    obligation: ValidityObligation,
    approved: ApprovedPlan,
    spec: IsingLatticeGasSpec,
) -> ObligationResult:
    plan = approved.plan
    if (
        obligation.evaluator_id
        == "smartchem.ising_lattice_gas/exact-subject-model-v1"
    ):
        exact_model = _finite_c3_model()
        passed = (
            type(spec) is IsingLatticeGasSpec
            and spec.vertices == C3_VERTICES
            and spec.edges == C3_EDGES
            and plan.model == exact_model
            and plan.request.physical_ir.models == (exact_model,)
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "exact fixed-C3 subject and runtime-owned model are bound"
                if passed
                else "subject, graph, or model differs from the runtime-owned finite C3 form"
            ),
        )
    if (
        obligation.evaluator_id
        == "smartchem.ising_lattice_gas/analogue-casualty-boundary-v1"
    ):
        ir = plan.request.physical_ir
        passed = (
            ir.claim_scope
            == ClaimScope(
                ClaimKind.ANALOGUE,
                (
                    "exact finite configuration and equilibrium-weight map on the "
                    "declared C3 models"
                ),
                ISING_LATTICE_GAS_CASUALTIES,
            )
            and ir.evidence_status is EvidenceStatus.ESTABLISHED
            and plan.execution_lane is ExecutionLane.CERTIFIED
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.REFUSE,
            (
                "claim remains an established finite analogue with every casualty"
                if passed
                else "claim kind, evidence, lane, referent, or casualty boundary was widened"
            ),
        )
    return _result(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _post_result(
    obligation: ValidityObligation,
    diagnostic: object,
    spec: IsingLatticeGasSpec,
    emitted: tuple[str, ...],
    expected: tuple[str, ...],
) -> ObligationResult:
    if (
        obligation.evaluator_id
        == "smartchem.ising_lattice_gas/complete-state-map-v1"
    ):
        passed = (
            type(diagnostic) is ExactEquilibriumMap
            and exact_equilibrium_map_error(diagnostic, spec) is None
            and len(diagnostic.states) == 8
            and diagnostic.completeness.output_reduction_applied is False
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            (
                "all eight ordered state records and four classes match recomputation"
                if passed
                else "a state, class, parameter, energy, order, or completeness field changed"
            ),
        )
    if (
        obligation.evaluator_id
        == "smartchem.ising_lattice_gas/partition-identity-v1"
    ):
        passed = (
            type(diagnostic) is ExactEquilibriumMap
            and exact_equilibrium_map_error(diagnostic, spec) is None
            and all(
                ising.exponent_ticks
                == lattice.exponent_ticks
                - diagnostic.parameters.constant_shift_c_ticks
                for lattice, ising in zip(
                    diagnostic.partition.lattice_terms,
                    diagnostic.partition.ising_terms,
                )
            )
        )
        return _result(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            (
                "all four formal partition terms obey the exact -C exponent shift"
                if passed
                else "formal partition terms, degeneracies, or constant-shift sign changed"
            ),
        )
    if (
        obligation.evaluator_id
        == "smartchem.ising_lattice_gas/output-inventory-v1"
    ):
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


def _execute_ising_lattice_gas(
    approved: ApprovedPlan,
    engine: object,
    *,
    actual_calculation: CalculationSpec,
    journal_path: str | os.PathLike[str] | None = None,
) -> ExecutionReport:
    """Execute after the common approval/compiler/calculation preflight."""
    plan = approved.plan
    if plan.executor_id != _ISING_LATTICE_GAS_EXECUTOR:
        raise ValueError("Ising-lattice-gas runner received a different executor plan")
    resolved = plan.request.resolved
    if (
        type(resolved) is not ResolvedDomainProgram
        or type(resolved.subject) is not IsingLatticeGasSpec
    ):
        raise TypeError(
            "Ising-lattice-gas executor requires an exact ResolvedDomainProgram "
            "IsingLatticeGasSpec"
        )
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
            journal.add_artifact(
                Artifact(
                    artifact_id,
                    kind,
                    payload.digest,
                    True,
                    False,
                    payload=payload,
                )
            )
        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.PRE:
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
            call_label="exact C3 engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)
        if plan.limits.max_engine_calls is not None and plan.limits.max_engine_calls < 1:
            return ExecutionReport(
                journal.incomplete(
                    "approved engine-call cap reached before exact C3 enumeration"
                ),
                None,
                None,
            )
        solver = getattr(engine, "solve", None)
        if not callable(solver):
            raise TypeError(
                "Ising-lattice-gas engine must expose solve(IsingLatticeGasSpec)"
            )
        diagnostic = solver(spec)
        if type(diagnostic) is not ExactEquilibriumMap:
            return ExecutionReport(
                journal.invalid(
                    "Ising-lattice-gas engine returned no exact ExactEquilibriumMap"
                ),
                None,
                None,
            )
        journal.add_checkpoint(
            Artifact(
                "checkpoint:exact-C3-Ising-lattice-gas-map",
                "checkpoint",
                diagnostic.digest,
                True,
                False,
                detail=(
                    f"{len(diagnostic.states)} retained states; "
                    f"{len(diagnostic.classes)} retained classes"
                ),
                payload=diagnostic,
            )
        )
        if CalculationSpec.from_oracle(engine).digest != plan.calculation.digest:
            raise RuntimeError(
                "CalculationSpec changed during the approved exact C3 engine call"
            )
        breach = _resource_wall(
            plan.limits,
            started=started,
            completed_calls=1,
            call_label="exact C3 engine calls",
        )
        if breach is not None:
            return ExecutionReport(journal.incomplete(breach), None, None)

        payloads = _payloads(diagnostic)
        emitted: list[str] = []
        for observable_id in plan.request.output_contract.observable_ids:
            payload = payloads[observable_id]
            journal.add_artifact(
                Artifact(
                    f"observable:{observable_id}",
                    "observable",
                    canonical_digest(payload),
                    True,
                    False,
                    detail=(
                        f"complete {observable_id}; states={len(diagnostic.states)}; "
                        "output reduction=false"
                    ),
                    payload=payload,
                )
            )
            emitted.append(observable_id)
        emitted_ids = tuple(emitted)
        journal.add_cache_state(
            "no cache: one deterministic complete eight-state integer enumeration"
        )

        for obligation in plan.request.obligations:
            if obligation.stage is ObligationStage.POST:
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

        certificate = Certificate(
            plan.request.source.digest,
            plan.request.digest,
            plan.digest,
            approved.approval.digest,
            actual_calculation.digest,
            plan.compiler_implementation_digest,
            journal.record.run_id,
            RunStatus.COMPLETE,
            plan.request.physical_ir.claim_scope,
            plan.request.physical_ir.evidence_status,
            journal.record.obligation_results,
            emitted_ids,
            ISING_LATTICE_GAS_CASUALTIES,
            ISING_LATTICE_GAS_OMISSIONS,
            (),
        )
        journal.add_artifact(
            Artifact(
                "certificate",
                "certificate",
                certificate.digest,
                True,
                False,
                payload=certificate,
            )
        )
        elapsed = time.monotonic() - started
        values = tuple(
            StructuredObservableValue(
                observable_id,
                payloads[observable_id],
                next(
                    item.unit
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                "exact finite C3 integer enumeration v1",
                next(
                    item.support
                    for item in plan.request.output_contract.observables
                    if item.observable_id == observable_id
                ),
                elapsed,
                (
                    "No numerical uncertainty is introduced: energies and exponent "
                    "coefficients are exact integers and beta remains formal."
                ),
                (
                    "COMPLETE certifies this exact finite algebraic map only; the claim "
                    "kind remains ANALOGUE and every physical casualty is retained."
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
        return ExecutionReport(
            journal.failed(f"{type(error).__name__}: {error}"),
            None,
            None,
        )
