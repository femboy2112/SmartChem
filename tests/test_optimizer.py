"""Acceptance tests for the Class-A reaction-residue optimizer."""
from __future__ import annotations

from dataclasses import replace

import pytest

from smartchem.category import Config, Molecule, Reaction, identity
from smartchem.contracts import RunStatus, canonical_digest
from smartchem.oracle.base import BaseOracle, Estimate
from smartchem.program import (
    ReactionResidueTransform,
    approve,
    compile_reaction_energy,
    execute,
    record_approval,
)
from smartchem.thermo import reaction_energy


H = Molecule.atom("H")
H2 = Molecule.diatomic("H", "H")
HE = Molecule.atom("He")
UNPRICEABLE_SPECTATOR = Molecule.atom("Xx")
H_FORMATION = Reaction(Config.of(H, H), Config.of(H2))
TWO_HE_SPECTATOR_FORMATION = Reaction(
    Config.of(H, H, HE, HE),
    Config.of(H2, HE, HE),
)


class RecordingOracle(BaseOracle):
    """Deterministic species oracle with explicit query telemetry."""

    name = "optimizer-test-oracle"
    nominal_accuracy_ev = 0.0

    def __init__(self, *, h2_energy: float = 4.0, unpriceable=()):
        self.h2_energy = h2_energy
        self.unpriceable = frozenset(unpriceable)
        self.calls: list[Molecule] = []

    def calculation_spec(self):
        return {
            "model": "optimizer-test-v1",
            "h2_energy": self.h2_energy,
            "unpriceable": tuple(sorted(repr(item) for item in self.unpriceable)),
        }

    def energy(self, molecule):
        self.calls.append(molecule)
        if molecule in self.unpriceable:
            return None
        values = {H: 1.0, H2: self.h2_energy, HE: 100.0}
        return Estimate(values.get(molecule, 7.0), 0.1, self.name)


def _approved(plan):
    return approve(
        plan,
        record_approval(plan, "optimizer test", "Class-A optimizer acceptance"),
    )


def _plan(reaction, oracle):
    return compile_reaction_energy("price the closed reaction", reaction, oracle)


def test_class_a_transform_is_plan_visible_with_exact_residue_multiplicity_and_workset():
    plan = _plan(TWO_HE_SPECTATOR_FORMATION, RecordingOracle())

    assert len(plan.transforms) == 1
    transform = plan.transforms[0]
    assert type(transform) is ReactionResidueTransform
    assert transform.original_reaction_digest == canonical_digest(TWO_HE_SPECTATOR_FORMATION)
    assert transform.input_model_digest == plan.model.digest
    assert transform.output_model_digest == plan.model.digest
    assert transform.residual_left == Config.of(H, H)
    assert transform.residual_right == Config.of(H2)
    assert transform.eliminated_species == ((HE, 2),)
    assert transform.workset == (H, H2)
    assert plan.predicted_resources[0] == ("structural residual species calls", "2")


def test_transform_cancels_only_the_shared_multiplicity_not_every_copy():
    reaction = Reaction(Config.of(H2, H2), Config.of(H2, H, H))
    plan = _plan(reaction, RecordingOracle())
    transform = plan.transforms[0]

    assert transform.eliminated_species == ((H2, 1),)
    assert transform.residual_left == Config.of(H2)
    assert transform.residual_right == Config.of(H, H)
    assert transform.workset == (H2, H)


def test_unpriceable_regenerated_spectator_is_never_queried_and_run_completes():
    reaction = Reaction(
        Config.of(H, H, UNPRICEABLE_SPECTATOR),
        Config.of(H2, UNPRICEABLE_SPECTATOR),
    )
    oracle = RecordingOracle(unpriceable=(UNPRICEABLE_SPECTATOR,))
    plan = _plan(reaction, oracle)

    assert plan.blockers == ()
    report = execute(_approved(plan), oracle)

    assert report.record.status is RunStatus.COMPLETE
    assert report.result is not None
    assert UNPRICEABLE_SPECTATOR not in oracle.calls
    assert set(oracle.calls) == {H, H2}


def test_spectator_reaction_matches_the_spectator_free_result_and_output_contract():
    spectator_oracle = RecordingOracle()
    bare_oracle = RecordingOracle()
    spectator_plan = _plan(TWO_HE_SPECTATOR_FORMATION, spectator_oracle)
    bare_plan = _plan(H_FORMATION, bare_oracle)

    spectator_report = execute(_approved(spectator_plan), spectator_oracle)
    bare_report = execute(_approved(bare_plan), bare_oracle)

    assert spectator_report.record.status is RunStatus.COMPLETE
    assert bare_report.record.status is RunStatus.COMPLETE
    assert spectator_plan.request.output_contract == bare_plan.request.output_contract
    assert spectator_report.result is not None and bare_report.result is not None
    spectator_value = spectator_report.result.values[0]
    bare_value = bare_report.result.values[0]
    assert spectator_value.value == bare_value.value
    assert spectator_value.uncertainty == bare_value.uncertainty
    assert spectator_value.method == bare_value.method
    assert spectator_value.systematic_ev == bare_value.systematic_ev
    assert spectator_value.methods == bare_value.methods
    assert spectator_value.systematic_terms == bare_value.systematic_terms
    assert HE not in spectator_oracle.calls


@pytest.mark.parametrize(
    "forgery",
    [
        lambda transform: replace(transform, residual_left=Config.of(H2)),
        lambda transform: replace(transform, residual_right=Config.of(H, H)),
        lambda transform: replace(transform, workset=(H,)),
        lambda transform: replace(transform, input_model_digest="forged-model-digest"),
        lambda transform: replace(transform, eliminated_species=((HE, 1),)),
        lambda transform: replace(
            transform, original_reaction_digest="forged-reaction-digest"
        ),
        lambda transform: replace(transform, verifier_id="forged-verifier"),
    ],
    ids=(
        "residual-left",
        "residual-right",
        "workset",
        "model-digest",
        "eliminated-multiplicity",
        "reaction-digest",
        "verifier",
    ),
)
def test_forged_transform_is_invalid_before_any_oracle_call(forgery):
    oracle = RecordingOracle()
    plan = _plan(TWO_HE_SPECTATOR_FORMATION, oracle)
    forged = replace(plan, transforms=(forgery(plan.transforms[0]),))

    report = execute(_approved(forged), oracle)

    assert report.record.status is RunStatus.INVALID
    assert report.result is None and report.certificate is None
    assert "Class-A transform verification failed" in report.record.failures[-1]
    assert oracle.calls == []


def test_reaction_without_spectators_has_no_transform():
    plan = _plan(H_FORMATION, RecordingOracle())

    assert plan.transforms == ()


def test_identity_reaction_needs_zero_oracle_calls_and_returns_exact_zero():
    oracle = RecordingOracle(unpriceable=(UNPRICEABLE_SPECTATOR,))
    plan = _plan(identity(Config.of(UNPRICEABLE_SPECTATOR)), oracle)

    report = execute(_approved(plan), oracle)

    assert report.record.status is RunStatus.COMPLETE
    assert report.result is not None
    value = report.result.values[0]
    assert value.value == 0.0
    assert value.uncertainty == 0.0
    assert oracle.calls == []


def test_transform_artifact_and_certificate_plan_binding_are_visible():
    oracle = RecordingOracle()
    plan = _plan(TWO_HE_SPECTATOR_FORMATION, oracle)

    report = execute(_approved(plan), oracle)

    assert report.record.status is RunStatus.COMPLETE
    assert report.certificate is not None
    transform = plan.transforms[0]
    artifact = next(
        item
        for item in report.record.artifacts
        if item.artifact_id == "transform:reaction-residue-v1"
    )
    assert artifact.kind == "transform"
    assert artifact.payload == transform
    assert artifact.content_digest == transform.digest
    assert any("spectator cancellation applied" in item for item in report.record.cache_state)
    assert report.certificate.plan_digest == plan.digest
    assert report.certificate.output_inventory == ("reaction_energy",)


def test_runtime_rejects_self_consistent_transform_under_replacement_model():
    oracle = RecordingOracle()
    plan = _plan(TWO_HE_SPECTATOR_FORMATION, oracle)
    forged_model = replace(
        plan.model,
        name="interacting-vessel-endpoint-energy",
        equations=("E includes context-dependent spectator interactions",),
        assumptions=("separability is absent",),
    )
    forged_ir = replace(plan.request.physical_ir, models=(forged_model,))
    forged_request = replace(plan.request, physical_ir=forged_ir)
    forged_transform = replace(
        plan.transforms[0],
        input_model_digest=forged_model.digest,
        output_model_digest=forged_model.digest,
    )
    forged = replace(
        plan,
        model=forged_model,
        request=forged_request,
        transforms=(forged_transform,),
    )

    report = execute(_approved(forged), oracle)

    assert report.record.status is RunStatus.INVALID
    assert "runtime-owned" in report.record.failures[-1]
    assert oracle.calls == []


def test_transformed_execution_preserves_every_reaction_energy_observable_field():
    execution_oracle = RecordingOracle()
    direct_oracle = RecordingOracle()
    plan = _plan(TWO_HE_SPECTATOR_FORMATION, execution_oracle)
    report = execute(_approved(plan), execution_oracle)
    direct = reaction_energy(TWO_HE_SPECTATOR_FORMATION, direct_oracle)

    assert direct is not None and report.result is not None
    value = report.result.values[0]
    assert value.value == direct.value_ev
    assert value.uncertainty == direct.uncertainty_ev
    assert value.method == direct.method
    assert value.seconds == direct.seconds
    assert value.notes == direct.notes
    assert value.systematic_ev == direct.systematic_ev
    assert value.methods == tuple(sorted(direct.methods))
    assert value.systematic_terms == direct.systematic_terms
    request = plan.request.output_contract.observables[0]
    assert value.unit == request.unit
    assert value.support == request.support


def test_changing_a_residual_species_energy_changes_the_result():
    low_oracle = RecordingOracle(h2_energy=4.0)
    high_oracle = RecordingOracle(h2_energy=9.0)
    low_report = execute(_approved(_plan(TWO_HE_SPECTATOR_FORMATION, low_oracle)), low_oracle)
    high_report = execute(_approved(_plan(TWO_HE_SPECTATOR_FORMATION, high_oracle)), high_oracle)

    assert low_report.result is not None and high_report.result is not None
    assert low_report.result.values[0].value == pytest.approx(2.0)
    assert high_report.result.values[0].value == pytest.approx(7.0)
    assert high_report.result.values[0].value != low_report.result.values[0].value


def test_public_optimizer_probe_exposes_domain_fix_and_no_loss(tmp_path):
    from experiments.compiled_class_a_optimizer import run, summary

    payload = summary(run(tmp_path / "class-a"))

    assert payload["status"] == payload["reference_status"] == "COMPLETE"
    assert payload["raw_reaction_domain_blocked"] is True
    assert payload["spectator_was_called"] is False
    assert payload["actual_oracle_calls"] == payload["reference_oracle_calls"]
    assert payload["value_and_uncertainty_identical"] is True
    assert (
        payload["output_contract_digest"]
        == payload["reference_output_contract_digest"]
    )
    assert payload["certificate_bound_transform_inventory"] == (
        "reaction-residue-v1",
    )
