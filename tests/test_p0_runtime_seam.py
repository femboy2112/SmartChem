"""P0 regression tests for typed IR and pre-journal runtime ownership gates."""
from __future__ import annotations

from dataclasses import fields, replace

import pytest

from smartchem.contracts import ClaimKind, EvidenceStatus
from smartchem.category import Config, Molecule, Reaction
from smartchem.program import (
    AssemblyEvidence,
    AssemblySpec,
    Boundary,
    CalibrationSpec,
    CandidatePlan,
    ClaimScope,
    Component,
    Connection,
    Identity,
    ModelSpec,
    ModelPatch,
    PhysicalIR,
    Port,
    CalculationSpec,
    RuntimeLimits,
    SolverSpec,
    Transform,
    TransportEvidence,
    TransportMap,
    approve,
    execute,
    record_approval,
)
from smartchem.runtime_registry import descriptor_for
from smartchem.water_wave import ShallowWaterHorizonEngine, compile_water_wave_horizon
from smartchem.water_wave_domain import (
    FlowDirection,
    HorizonOrientation,
    ProfilePoint,
    RegimeAssumptions,
    WaterWaveSpec,
    WaveBranch,
    WaveRegime,
    WaveTarget,
)


def _model() -> ModelSpec:
    return ModelSpec("test", (), (), (), (), (), "1")


def _scope() -> ClaimScope:
    return ClaimScope(ClaimKind.ANALOGUE, "test")


def _spec() -> WaterWaveSpec:
    return WaterWaveSpec(
        tuple(ProfilePoint(float(index - 1), 0.1, velocity) for index, velocity in enumerate((0.4, 0.8, 1.2, 1.6))),
        9.81,
        WaveTarget.KINEMATIC_HORIZON,
        WaveRegime.NONDISPERSIVE_SHALLOW_WATER,
        WaveBranch.COUNTER_CURRENT,
        HorizonOrientation.BLACK,
        FlowDirection.POSITIVE_X,
        RegimeAssumptions(True, True, True, True, True, True, True, True, True, True),
    )


def _approved(plan):
    return approve(plan, record_approval(plan, "test", "P0 seam test"))


def test_physical_ir_rejects_malformed_members_connections_and_evidence_refs():
    model = _model()
    component_a = Component(
        "a", "test", Identity("a", "test"),
        (Port("a:v", "a", "voltage", "V", "out", "electrical"),),
    )
    component_b = Component(
        "b", "test", Identity("b", "test"),
        (Port("b:t", "b", "temperature", "K", "in", "thermal"),),
    )
    kwargs = dict(
        resolved_digest="resolved",
        components=(component_a, component_b),
        connections=(),
        reservoirs=(),
        boundaries=(),
        models=(model,),
        adapters=(),
        invariants=(),
        transport_maps=(),
        transport_evidence=(),
        assemblies=(),
        assembly_evidence=(),
        claim_scope=_scope(),
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
    )
    with pytest.raises(TypeError, match="components"):
        PhysicalIR(**{**kwargs, "components": ("not-a-component",)})
    with pytest.raises(ValueError, match="shared dimension"):
        PhysicalIR(**{**kwargs, "connections": (Connection("bad", ("a:v", "b:t"), "join"),)})
    with pytest.raises(ValueError, match="unknown target"):
        PhysicalIR(**{**kwargs, "boundaries": (Boundary("bad", ("missing",), "fixed"),)})
    transport = TransportMap("source", "target")
    with pytest.raises(ValueError, match="every and only"):
        PhysicalIR(**{**kwargs, "transport_maps": (transport,), "transport_evidence": (TransportEvidence("orphan", (), ()),)})
    assembly = AssemblySpec("assembly", "one", ())
    evidence = AssemblyEvidence(assembly.digest, (), ())
    with pytest.raises(ValueError, match="at most once"):
        PhysicalIR(**{**kwargs, "assemblies": (assembly,), "assembly_evidence": (evidence, evidence)})


def test_transport_maps_must_bind_the_resolved_source_and_target():
    engine = ShallowWaterHorizonEngine()
    plan = compile_water_wave_horizon("test", _spec(), engine)
    forged_map = replace(plan.request.physical_ir.transport_maps[0], source_theory_digest="forged")
    forged_evidence = replace(
        plan.request.physical_ir.transport_evidence[0],
        transport_digest=forged_map.digest,
    )
    forged_ir = replace(
        plan.request.physical_ir,
        transport_maps=(forged_map,),
        transport_evidence=(forged_evidence,),
    )
    with pytest.raises(ValueError, match="source theory"):
        replace(plan.request, physical_ir=forged_ir)


def test_reaction_tensor_visibly_deprecates_the_left_first_compatibility_name():
    hydrogen = Molecule.atom("H")
    reaction = Reaction(Config.of(hydrogen), Config.of(hydrogen))

    with pytest.warns(DeprecationWarning, match="not a parallel tensor"):
        scheduled = reaction.tensor(reaction)

    assert scheduled == reaction.scheduled_product(reaction)


def test_candidate_plan_rejects_nominal_subclasses_of_primary_records():
    class DerivedSolver(SolverSpec):
        pass

    class DerivedCalculation(CalculationSpec):
        pass

    class DerivedLimits(RuntimeLimits):
        pass

    plan = compile_water_wave_horizon("test", _spec(), ShallowWaterHorizonEngine())

    with pytest.raises(TypeError, match="solver"):
        replace(
            plan,
            solver=DerivedSolver(
                plan.solver.name,
                plan.solver.algorithm,
                plan.solver.version,
                plan.solver.tolerances,
                plan.solver.stopping_policy,
                plan.solver.reproducibility,
            ),
        )
    with pytest.raises(TypeError, match="calculation"):
        replace(
            plan,
            calculation=DerivedCalculation(
                plan.calculation.engine_class,
                plan.calculation.engine_name,
                plan.calculation.settings,
                plan.calculation.implementation_digest,
            ),
        )
    with pytest.raises(TypeError, match="limits"):
        replace(
            plan,
            limits=DerivedLimits(
                plan.limits.max_species_calls,
                plan.limits.wall_seconds,
                plan.limits.memory_bytes,
                plan.limits.max_engine_calls,
            ),
        )


def test_candidate_plan_subclass_cannot_cross_approval_boundary():
    class DerivedPlan(CandidatePlan):
        pass

    plan = compile_water_wave_horizon("test", _spec(), ShallowWaterHorizonEngine())
    derived = DerivedPlan(
        **{field.name: getattr(plan, field.name) for field in fields(plan)}
    )
    approval = record_approval(plan, "test", "exact nominal plan only")

    with pytest.raises(TypeError, match="CandidatePlan"):
        record_approval(derived, "test", "must refuse derived plan")
    with pytest.raises(TypeError, match="CandidatePlan"):
        approve(derived, approval)


def test_resolved_runner_is_not_an_authoritative_public_dispatch_path(tmp_path):
    engine = ShallowWaterHorizonEngine()
    plan = compile_water_wave_horizon("test", _spec(), engine)
    journal = tmp_path / "direct-runner.json"
    runner = descriptor_for(plan.executor_id).resolve_runner()

    with pytest.raises(ValueError, match="internal capabilities"):
        runner(
            _approved(plan),
            engine,
            actual_calculation=plan.calculation,
            journal_path=journal,
        )

    assert engine.calls == 0
    assert not journal.exists()


def test_physical_ir_rejects_nominal_subclasses():
    class DerivedComponent(Component):
        pass

    class DerivedCalibration(CalibrationSpec):
        pass

    class DerivedPatch(ModelPatch):
        pass

    class DerivedScope(ClaimScope):
        pass

    class DerivedTuple(tuple):
        pass

    model = _model()
    base = Component("base", "test", Identity("base", "test"))
    derived = DerivedComponent(
        base.component_id,
        base.kind,
        base.identity,
        base.ports,
        base.parameters,
    )

    kwargs = dict(
        resolved_digest="resolved",
        components=(base,),
        connections=(),
        reservoirs=(),
        boundaries=(),
        models=(model,),
        adapters=(),
        invariants=(),
        transport_maps=(),
        transport_evidence=(),
        assemblies=(),
        assembly_evidence=(),
        claim_scope=_scope(),
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
    )
    with pytest.raises(TypeError, match="components"):
        PhysicalIR(**{**kwargs, "components": (derived,)})
    with pytest.raises(TypeError, match="components"):
        PhysicalIR(**{**kwargs, "components": DerivedTuple((base,))})
    with pytest.raises(TypeError, match="calibrations"):
        PhysicalIR(
            **{
                **kwargs,
                "calibrations": (
                    DerivedCalibration("p", "p", (), "i", "v", "u"),
                ),
            }
        )
    with pytest.raises(TypeError, match="model_patches"):
        PhysicalIR(
            **{
                **kwargs,
                "model_patches": (DerivedPatch("p", (), ()),),
            }
        )
    with pytest.raises(TypeError, match="claim_scope"):
        PhysicalIR(
            **{
                **kwargs,
                "claim_scope": DerivedScope(ClaimKind.ANALOGUE, "derived"),
            }
        )


@pytest.mark.parametrize("attack", ("model", "transform"))
def test_water_wave_ownership_forgery_is_rejected_before_calculation_or_journal(tmp_path, attack):
    engine = ShallowWaterHorizonEngine()
    plan = compile_water_wave_horizon("test", _spec(), engine)
    if attack == "model":
        model = replace(plan.model, version="forged")
        forged = replace(
            plan,
            model=model,
            request=replace(plan.request, physical_ir=replace(plan.request.physical_ir, models=(model,))),
        )
    else:
        forged = replace(
            plan,
            transforms=(Transform("foreign", "A", plan.model.digest, plan.model.digest, (), (), ()),),
        )
    journal = tmp_path / f"{attack}.json"
    with pytest.raises(ValueError, match="runtime-owned model|does not support transforms"):
        execute(_approved(forged), engine, journal_path=journal)
    assert engine.calls == 0
    assert not journal.exists()
