"""EVD-KEY-01 (consumer half) -- a sourced record MUST NOT survive a section-5.3 BLOCKER for its class.

IR-LOSS-01 / ID-STEREO-01 PRODUCE typed :class:`~smartchem.identity.IdentityLoss` blockers; this is where they
BITE.  When the target identity carries a BLOCKER for a claim class (selectivity, conditions, ...), the evidence
providers refuse to emit a SOURCED verdict for it -- the dropped feature is one that class can depend on, so a
sourced FAVORED/DISFAVORED or a sourced condition envelope must not attach to the under-determined identity.

The gate is claim-class-PRECISE (an isotope blocker does not gag selectivity) and NON-VACUOUS (with no blocking
loss the sourced verdict fires unchanged) -- never a blanket refusal, never a silent survival.
"""
from __future__ import annotations

import pytest

from smartchem.decompiler import Formula
from smartchem.decompiler_conditions import ReactionDirection, assembly_conditions, reaction_conditions
from smartchem.identity import (
    IDENTITY_LOSS_SCHEMA,
    IdentityLoss,
    LossSeverity,
    blocked_claim_classes,
    blocking_losses,
    is_blocked,
    isotope_loss,
    local_charge_loss,
    stereo_loss,
)
from smartchem.experiment.selectivity import (
    DEFAULT_SELECTIVITY,
    SelectivityStatus,
    selectivity_of_step,
    verify_selectivity,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
AMP = parse_smiles("Nc1ccc(O)cc1")
ANH = parse_smiles("CC(=O)OC(C)=O")
ACOH = parse_smiles("CC(=O)O")


def _para_step():
    return ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH))


def _hydrolysis_edge():
    from types import SimpleNamespace
    return SimpleNamespace(
        reactant=Formula.parse("C8H9NO2"),
        reactant_multiplicity=1,
        reagents=((Formula.parse("H2O"), 1),),
        products=((Formula.parse("C6H7NO"), 1), (Formula.parse("C2H4O2"), 1)),
    )


class TestSelectivityGate:
    def test_no_loss_leaves_the_sourced_favored_verdict_intact(self):
        # NON-VACUITY: the gate must not swallow a legitimate sourced verdict.
        assert selectivity_of_step(_para_step(), table=DEFAULT_SELECTIVITY).status is SelectivityStatus.FAVORED

    def test_a_selectivity_blocker_downgrades_the_sourced_verdict_to_unknown(self):
        sel = selectivity_of_step(
            _para_step(), table=DEFAULT_SELECTIVITY, losses=(stereo_loss("smiles:[C@H]..."),)
        )
        assert sel.status is SelectivityStatus.UNKNOWN
        assert "5.3" in sel.reason and "must not survive" in sel.reason

    def test_a_disfavored_sourced_verdict_is_also_gated(self):
        ester = parse_smiles("CC(=O)Oc1ccc(N)cc1")
        step = ExperimentStep.assembling(ester, (AMP, ANH), (ester, ACOH))
        assert selectivity_of_step(step, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.DISFAVORED
        gated = selectivity_of_step(step, table=DEFAULT_SELECTIVITY, losses=(stereo_loss("x"),))
        assert gated.status is SelectivityStatus.UNKNOWN

    def test_an_isotope_loss_does_not_gag_selectivity(self):
        # claim-class PRECISION: isotope blocks kinetics/isotope-identity, not selectivity.
        sel = selectivity_of_step(_para_step(), table=DEFAULT_SELECTIVITY, losses=(isotope_loss("[13C]", (13,)),))
        assert sel.status is SelectivityStatus.FAVORED

    def test_a_warning_severity_loss_never_gates(self):
        warn = IdentityLoss(
            IDENTITY_LOSS_SCHEMA, "stereochemistry", "in", "ret", "reason", ("selectivity",), LossSeverity.WARNING
        )
        assert selectivity_of_step(_para_step(), table=DEFAULT_SELECTIVITY, losses=(warn,)).status is (
            SelectivityStatus.FAVORED
        )

    def test_verify_selectivity_threads_losses_to_every_step(self):
        route = ExperimentRoute.of(_para_step())
        assert verify_selectivity(route).verdict == "FAVORED"
        assert verify_selectivity(route, losses=(stereo_loss("x"),)).verdict == "UNKNOWN"


class TestConditionsGate:
    def test_no_loss_leaves_the_sourced_condition_declared(self):
        env = reaction_conditions(_hydrolysis_edge(), direction=ReactionDirection.DECOMPOSITION)
        assert env.is_declared

    def test_a_conditions_blocker_refuses_the_sourced_envelope(self):
        env = reaction_conditions(
            _hydrolysis_edge(), direction=ReactionDirection.DECOMPOSITION, losses=(local_charge_loss("x"),)
        )
        assert not env.is_declared

    def test_an_isotope_loss_does_not_gag_conditions(self):
        # isotope blocks kinetics, not conditions -- the sourced envelope survives.
        env = reaction_conditions(
            _hydrolysis_edge(), direction=ReactionDirection.DECOMPOSITION, losses=(isotope_loss("[13C]", (13,)),)
        )
        assert env.is_declared

    def test_assembly_conditions_short_circuits_under_a_conditions_blocker(self):
        # the gate returns unknown() BEFORE touching the capped scission, so a conditions blocker refuses regardless.
        env = assembly_conditions(None, losses=(stereo_loss("x"),))
        assert not env.is_declared


class TestProductionPathBite:
    """The red-team's HIGH finding: the gate must reach a REAL production entry point, not only direct injection."""

    def _route(self):
        return ExperimentRoute.of(_para_step())

    def test_classify_route_selectivity_is_gated_end_to_end(self):
        from smartchem.experiment.classify import classify_route
        assert classify_route(self._route()).selectivity.verdict == "FAVORED"
        assert classify_route(self._route(), losses=(stereo_loss("x"),)).selectivity.verdict == "UNKNOWN"

    def test_classify_step_selectivity_is_gated_end_to_end(self):
        from smartchem.experiment.classify import classify_step
        assert classify_step(_para_step()).selectivity.status is SelectivityStatus.FAVORED
        gated = classify_step(_para_step(), losses=(stereo_loss("x"),))
        assert gated.selectivity.status is SelectivityStatus.UNKNOWN

    def test_classify_route_kinetics_is_gated_by_an_isotope_blocker(self):
        # the CLAIM-CLASS gap fix: an isotope BLOCKER (kinetics class) downgrades every step's sourced rate.
        from smartchem.experiment.classify import classify_route
        graded = classify_route(self._route(), losses=(isotope_loss("[13C]", (13,)),))
        assert all(s.regime.value == "UNKNOWN" for s in graded.kinetics.per_step)

    def test_compile_synthesis_threads_losses_to_the_dossier(self):
        # compile_synthesis passes losses to rank/classify/draft; a step selectivity under a blocker is UNKNOWN.
        from smartchem.experiment.compile import compile_synthesis
        c = compile_synthesis(PARA, reagents=(AMP, ANH), available=(AMP, ANH), commodities=(),
                              losses=(stereo_loss("x"),))
        # whatever route it surfaces, no step may carry a sourced FAVORED/DISFAVORED under the blocker
        if c.best_draft is not None:
            assert c.best_draft.selectivity.verdict in ("UNKNOWN", "NOT_APPLICABLE")


class TestKineticsGate:
    def test_kinetics_of_step_is_gated_by_an_isotope_blocker(self):
        from smartchem.experiment.kinetics import kinetics_of_step
        # a step with sourced kinetics (if any) is downgraded; the gate returns a loud UNKNOWN citing the blocker.
        k = kinetics_of_step(_para_step(), losses=(isotope_loss("[13C]", (13,)),))
        assert k.regime.value == "UNKNOWN"
        assert "5.3" in k.reason and "kinetics" in k.reason

    def test_a_selectivity_blocker_does_not_gag_kinetics(self):
        # claim-class precision the other way: a stereo blocker blocks kinetics too (stereospecific rate), but a
        # local-charge blocker (conditions/product-identity/protonation only) does NOT touch kinetics.
        from smartchem.experiment.kinetics import kinetics_of_step
        k = kinetics_of_step(_para_step(), losses=(local_charge_loss("x"),))
        assert k.regime.value != "UNKNOWN" or "5.3" not in k.reason  # not gated BY the local-charge loss


class TestGatePrimitives:
    def test_blocking_losses_returns_only_the_matching_blockers(self):
        losses = (stereo_loss("x"), isotope_loss("y", (2,)))
        assert len(blocking_losses(losses, "selectivity")) == 1     # stereo only
        assert len(blocking_losses(losses, "kinetics")) == 2        # both block kinetics
        assert blocking_losses(losses, "purity") == ()

    def test_is_blocked_is_the_any_of_blocking_losses(self):
        assert is_blocked((stereo_loss("x"),), "conditions")
        assert not is_blocked((isotope_loss("y", (2,)),), "conditions")

    def test_blocked_claim_classes_is_the_sorted_union(self):
        classes = blocked_claim_classes((stereo_loss("x"), local_charge_loss("z")))
        assert "selectivity" in classes and "protonation-state" in classes
        assert list(classes) == sorted(classes)

    def test_gate_primitives_reject_a_non_loss_tuple(self):
        with pytest.raises(TypeError):
            blocking_losses(("not a loss",), "selectivity")
        with pytest.raises(TypeError):
            blocked_claim_classes(("nope",))

    def test_blocking_losses_rejects_an_empty_claim(self):
        with pytest.raises(ValueError):
            blocking_losses((stereo_loss("x"),), "")
