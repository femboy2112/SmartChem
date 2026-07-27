"""Source-to-certificate acceptance tests for the water-wave analogue vertical."""
from __future__ import annotations

import json
import math
from dataclasses import replace

import pytest

import smartchem.water_wave as water_wave_module
from smartchem.contracts import (
    ClaimKind,
    InferenceKind,
    RunStatus,
)
from smartchem.ledger import COMPILED, STALLED, Spec, shepherd
from smartchem.program import (
    ClaimScope,
    ObservableRequest,
    OutputContract,
    RuntimeLimits,
    approve,
    execute,
    record_approval,
)
from smartchem.water_wave import (
    ShallowWaterHorizonEngine,
    WATER_WAVE_CASUALTIES,
    WATER_WAVE_OMISSIONS,
    compile_session_water_wave_horizon,
    compile_water_wave_horizon,
    water_wave_slot,
)
from smartchem.water_wave_domain import (
    FlowDirection,
    HorizonDiagnostic,
    HorizonOrientation,
    HorizonStatus,
    ProfilePoint,
    RegimeAssumptions,
    WaterWaveSpec,
    WaveBranch,
    WaveRegime,
    WaveTarget,
    diagnose_horizon,
)


def _assumptions(**changes: bool) -> RegimeAssumptions:
    values = {
        "stationary": True,
        "inviscid": True,
        "irrotational": True,
        "gravity_only": True,
        "shallow_water": True,
        "linear_perturbations": True,
        "one_dimensional": True,
        "prescribed_background": True,
        "no_retained_wave_forcing": True,
        "negligible_reflections": True,
    }
    values.update(changes)
    return RegimeAssumptions(**values)


def _spec(
    velocities: tuple[float, ...] = (0.4, 0.8, 1.2, 1.6),
    *,
    target: WaveTarget = WaveTarget.KINEMATIC_HORIZON,
    regime: WaveRegime = WaveRegime.NONDISPERSIVE_SHALLOW_WATER,
    orientation: HorizonOrientation = HorizonOrientation.BLACK,
    assumptions: RegimeAssumptions | None = None,
) -> WaterWaveSpec:
    return WaterWaveSpec(
        profile=tuple(
            ProfilePoint(float(index - 1), 0.1, velocity)
            for index, velocity in enumerate(velocities)
        ),
        gravitational_acceleration_m_s2=9.81,
        target=target,
        regime=regime,
        branch=WaveBranch.COUNTER_CURRENT,
        requested_orientation=orientation,
        flow_direction=FlowDirection.POSITIVE_X,
        assumptions=assumptions or _assumptions(),
    )


def _approved(plan):
    return approve(
        plan,
        record_approval(
            plan,
            "scientist",
            "classical prescribed-background water-wave analogue only",
        ),
    )


def test_underidentified_phrase_remains_open_until_scientist_binds_typed_choices():
    starting = Spec(
        "water-wave-analogue",
        (water_wave_slot("water-model", "Simulate a black hole in water."),),
    )
    session = shepherd(starting, lambda spec, _holes: spec)

    assert session.outcome == STALLED
    assert session.spec.measure() == 1
    with pytest.raises(ValueError, match="outright COMPILED"):
        compile_session_water_wave_horizon(
            "Simulate a black hole in water.",
            session,
            "water-model",
            ShallowWaterHorizonEngine(),
        )


def test_typed_shepherd_session_is_the_execution_authority(tmp_path):
    spec = _spec()
    starting = Spec(
        "water-wave-analogue",
        (water_wave_slot("water-model", "Simulate a black hole in water."),),
    )

    def answer(current, _holes):
        return current.bind_typed(
            "water-model",
            spec,
            source_text=(
                "Use the counter-current nondispersive shallow-water branch on the supplied "
                "positive-x profile and test black-hole kinematics."
            ),
            inference=InferenceKind.QUESTION_CONFIRMED,
        )

    session = shepherd(
        starting,
        answer,
        discarded=(
            "literal astrophysical black hole",
            "unspecified wave regime and orientation",
        ),
    )
    assert session.outcome == COMPILED
    engine = ShallowWaterHorizonEngine()
    plan = compile_session_water_wave_horizon(
        "Simulate a black hole in water.",
        session,
        "water-model",
        engine,
    )
    report = execute(
        _approved(plan),
        engine,
        journal_path=tmp_path / "water-wave.json",
    )

    assert report.record.status is RunStatus.COMPLETE
    assert engine.calls == 1
    assert report.result is not None and report.certificate is not None
    assert report.certificate.claim_scope.kind is ClaimKind.ANALOGUE
    assert set(WATER_WAVE_CASUALTIES).issubset(report.certificate.casualties)
    assert report.certificate.evidence_status.value == "STRUCTURAL_TOY"
    assert report.certificate.omissions == WATER_WAVE_OMISSIONS
    assert report.certificate.output_inventory == (
        "water_wave_horizon",
        "water_wave_characteristic_profile",
    )
    diagnostic = report.result.values[0].payload
    assert isinstance(diagnostic, HorizonDiagnostic)
    assert diagnostic.status is HorizonStatus.KINEMATIC_CROSSING_IN_DECLARED_MODEL
    assert len(diagnostic.samples) == len(spec.profile)
    assert len(diagnostic.horizons) == 1
    expected = (math.sqrt(9.81 * 0.1) - 0.8) / (1.2 - 0.8)
    assert diagnostic.horizons[0].position_m == pytest.approx(expected)
    assert diagnostic.horizons[0].orientation is HorizonOrientation.BLACK
    persisted = json.loads((tmp_path / "water-wave.json").read_text())
    assert persisted["status"] == "COMPLETE"
    assert len(persisted["checkpoints"]) == 1
    observable_payloads = {
        item["artifact_id"]: item["payload"]
        for item in persisted["artifacts"]
        if item["kind"] == "observable"
    }
    assert set(observable_payloads) == {
        "observable:water_wave_horizon",
        "observable:water_wave_characteristic_profile",
    }
    assert len(
        observable_payloads["observable:water_wave_characteristic_profile"]
    ) == len(spec.profile)


def test_no_horizon_is_a_complete_negative_result():
    spec = _spec((0.2, 0.3, 0.4, 0.5))
    engine = ShallowWaterHorizonEngine()
    report = execute(
        _approved(compile_water_wave_horizon("diagnose", spec, engine)),
        engine,
    )

    assert report.record.status is RunStatus.COMPLETE
    diagnostic = report.result.values[0].payload
    assert diagnostic.status is HorizonStatus.NO_HORIZON_IN_DECLARED_REGIME
    assert diagnostic.horizons == ()


@pytest.mark.parametrize(
    "spec, blocker",
    [
        (_spec(target=WaveTarget.QUANTUM_RADIATION), "not implemented"),
        (
            _spec(regime=WaveRegime.DISPERSIVE_GRAVITY_CAPILLARY),
            "Froude shortcut is refused",
        ),
        (
            _spec(assumptions=_assumptions(stationary=False)),
            "false assumptions: stationary",
        ),
    ],
)
def test_unsupported_physics_is_planned_as_a_blocker(spec, blocker):
    engine = ShallowWaterHorizonEngine()
    plan = compile_water_wave_horizon("request", spec, engine)

    assert any(blocker in item for item in plan.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(plan)
    assert engine.calls == 0


def test_output_expansion_is_blocked_before_approval():
    engine = ShallowWaterHorizonEngine()
    baseline = compile_water_wave_horizon("request", _spec(), engine)
    extra = ObservableRequest(
        "quantum_hawking_emission",
        "unsupported quantum observable",
        "occupation",
        "none",
        "none",
        "none",
        "none",
    )
    contract = replace(
        baseline.request.output_contract,
        observables=baseline.request.output_contract.observables + (extra,),
    )
    plan = compile_water_wave_horizon(
        "request",
        _spec(),
        engine,
        output_contract=contract,
    )

    assert any("cannot emit" in item for item in plan.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(plan)
    assert engine.calls == 0


def test_supported_output_id_cannot_promise_unsupported_semantics():
    engine = ShallowWaterHorizonEngine()
    baseline = compile_water_wave_horizon("request", _spec(), engine)
    horizon = replace(
        baseline.request.output_contract.observables[0],
        coverage="100 laboratory-frequency scattering coefficients and uncertainties",
    )
    contract = replace(
        baseline.request.output_contract,
        observables=(
            horizon,
            baseline.request.output_contract.observables[1],
        ),
    )
    plan = compile_water_wave_horizon(
        "request",
        _spec(),
        engine,
        output_contract=contract,
    )

    assert any("exact default output contract" in item for item in plan.blockers)
    with pytest.raises(ValueError, match="blockers"):
        _approved(plan)
    assert engine.calls == 0


def test_post_approval_semantic_output_contract_tampering_fails_before_call():
    engine = ShallowWaterHorizonEngine()
    approved = _approved(compile_water_wave_horizon("request", _spec(), engine))
    altered = replace(
        approved.plan.request.output_contract.observables[0],
        coverage="an unimplemented scattering matrix",
    )
    object.__setattr__(
        approved.plan.request,
        "output_contract",
        replace(
            approved.plan.request.output_contract,
            observables=(
                altered,
                approved.plan.request.output_contract.observables[1],
            ),
        ),
    )
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(approved, "approval_record_digest", approved.approval.digest)

    with pytest.raises(ValueError, match="exact default output contract"):
        execute(approved, engine)
    assert engine.calls == 0


def test_orientation_mismatch_invalidates_and_quarantines_the_diagnostic(tmp_path):
    engine = ShallowWaterHorizonEngine()
    plan = compile_water_wave_horizon(
        "request a white orientation from a black profile",
        _spec(orientation=HorizonOrientation.WHITE),
        engine,
    )
    report = execute(
        _approved(plan),
        engine,
        journal_path=tmp_path / "mismatch.json",
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert all(item.quarantined for item in report.record.artifacts)
    assert any("orientation" in item for item in report.record.failures)


def test_analogue_scope_tampering_refuses_before_engine_call():
    engine = ShallowWaterHorizonEngine()
    approved = _approved(compile_water_wave_horizon("request", _spec(), engine))
    object.__setattr__(
        approved.plan.request.physical_ir,
        "claim_scope",
        ClaimScope(ClaimKind.LITERAL, "astrophysical black hole", ()),
    )
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(
        approved,
        "approval_record_digest",
        approved.approval.digest,
    )

    report = execute(approved, engine)

    assert report.record.status is RunStatus.REFUSED
    assert engine.calls == 0
    assert "analogue" in report.record.failures[-1]


def test_analogue_enum_cannot_name_an_astrophysical_referent():
    engine = ShallowWaterHorizonEngine()
    approved = _approved(compile_water_wave_horizon("request", _spec(), engine))
    object.__setattr__(
        approved.plan.request.physical_ir,
        "claim_scope",
        ClaimScope(
            ClaimKind.ANALOGUE,
            "astrophysical black hole",
            WATER_WAVE_CASUALTIES,
        ),
    )
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(approved, "approval_record_digest", approved.approval.digest)

    report = execute(approved, engine)

    assert report.record.status is RunStatus.REFUSED
    assert engine.calls == 0


def test_approval_record_mutation_is_rejected_before_engine_call():
    engine = ShallowWaterHorizonEngine()
    approved = _approved(compile_water_wave_horizon("request", _spec(), engine))
    object.__setattr__(approved.approval, "scope", "literal astrophysical claims")

    with pytest.raises(ValueError, match="approval record changed"):
        execute(approved, engine)
    assert engine.calls == 0


def test_changed_engine_identity_is_rejected_before_call():
    class MutableEngine(ShallowWaterHorizonEngine):
        def __init__(self):
            super().__init__()
            self.setting = "one"

        def calculation_spec(self):
            return {"setting": self.setting, "version": 1}

    engine = MutableEngine()
    approved = _approved(compile_water_wave_horizon("request", _spec(), engine))
    engine.setting = "two"

    with pytest.raises(ValueError, match="CalculationSpec changed"):
        execute(approved, engine)
    assert engine.calls == 0


def test_executor_subject_mismatch_fails_before_journal_creation(tmp_path):
    engine = ShallowWaterHorizonEngine()
    approved = _approved(compile_water_wave_horizon("request", _spec(), engine))
    object.__setattr__(
        approved.plan,
        "executor_id",
        "smartchem.program/reaction-energy-v1",
    )
    object.__setattr__(approved.approval, "plan_digest", approved.plan.digest)
    object.__setattr__(approved, "approval_record_digest", approved.approval.digest)
    journal = tmp_path / "must-not-exist.json"

    with pytest.raises(ValueError, match="reaction executor requires"):
        execute(approved, engine, journal_path=journal)

    assert engine.calls == 0
    assert not journal.exists()


def test_engine_identity_change_during_call_quarantines_checkpoint():
    class MutatingEngine(ShallowWaterHorizonEngine):
        def __init__(self):
            super().__init__()
            self.setting = "one"

        def calculation_spec(self):
            return {"setting": self.setting, "version": 1}

        def solve(self, spec):
            result = super().solve(spec)
            self.setting = "two"
            return result

    engine = MutatingEngine()
    report = execute(
        _approved(compile_water_wave_horizon("request", _spec(), engine)),
        engine,
    )

    assert report.record.status is RunStatus.FAILED
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert report.result is None and report.certificate is None


@pytest.mark.parametrize("forgery", ["omit-crossing", "move-crossing"])
def test_engine_cannot_forge_a_conforming_looking_diagnostic(forgery):
    class ForgingEngine(ShallowWaterHorizonEngine):
        def solve(self, spec):
            self.calls += 1
            genuine = diagnose_horizon(spec)
            if forgery == "omit-crossing":
                return replace(
                    genuine,
                    horizons=(),
                    status=HorizonStatus.NO_HORIZON_IN_DECLARED_REGIME,
                )
            forged_horizon = replace(
                genuine.horizons[0],
                position_m=123.0,
                orientation=HorizonOrientation.WHITE,
            )
            return replace(genuine, horizons=(forged_horizon,))

    engine = ForgingEngine()
    report = execute(
        _approved(compile_water_wave_horizon("request", _spec(), engine)),
        engine,
    )

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)


def test_post_engine_resource_wall_quarantines_the_complete_checkpoint(monkeypatch):
    checks = iter((None, "injected post-call resource wall"))
    monkeypatch.setattr(
        water_wave_module,
        "_resource_wall",
        lambda *_args, **_kwargs: next(checks),
    )
    engine = ShallowWaterHorizonEngine()
    report = execute(
        _approved(compile_water_wave_horizon("request", _spec(), engine)),
        engine,
    )

    assert report.record.status is RunStatus.INCOMPLETE
    assert engine.calls == 1
    assert report.record.checkpoints
    assert all(item.quarantined for item in report.record.checkpoints)
    assert all(item.quarantined for item in report.record.artifacts)
    assert report.record.failures[-1] == "injected post-call resource wall"


def test_engine_call_resource_cap_is_incomplete_without_call():
    engine = ShallowWaterHorizonEngine()
    plan = compile_water_wave_horizon(
        "request",
        _spec(),
        engine,
        limits=RuntimeLimits(max_engine_calls=0),
    )
    report = execute(_approved(plan), engine)

    assert report.record.status is RunStatus.INCOMPLETE
    assert engine.calls == 0
    assert "max_engine_calls=0" in report.record.failures[-1]
