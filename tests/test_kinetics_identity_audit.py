"""Identity and spectator-only steps have no chemical reaction-rate observable."""
from dataclasses import replace
from importlib import import_module

import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.eyring import EyringRef, EyringTable
from smartchem.data.kinetics import DEFAULT_KINETICS, KineticRef, KineticTable
from smartchem.evidence_key import ReactionEvidenceKey
from smartchem.experiment.classify import classify_route
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.drafter import ConstraintBox, fit_route
from smartchem.experiment.eyring import eyring_of_step, verify_eyring
from smartchem.experiment.kinetics import (
    RateGrade, RateRegime, _resolve_record, kinetics_of_step, reaction_evidence_key, verify_kinetics,
)
from smartchem.experiment.routes import (
    ROUTE_SEARCH_RECEIPT_SCHEMA, ROUTE_SEARCH_RESULT_SCHEMA, RouteSearchReceipt, RouteSearchResult,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.process_constraints import ProcessBounds
from smartchem.smiles import parse_smiles


def _envelope():
    return ConditionEnvelope(
        temperature=Interval(300, 300, "K"), pressure=Interval(1, 1, "atm"),
        status=EvidenceStatus.EXPERIMENTAL, provenance="synthetic identity control; no chemistry attestation",
    )


def _identity(*smiles):
    species = tuple(parse_smiles(s) for s in smiles)
    return ExperimentStep.assembling(
        species[0], species, tuple(reversed(species)), envelope=_envelope(),
    )


def _isomerization():
    cyclopropane, propene = parse_smiles("C1CC1"), parse_smiles("CC=C")
    return ExperimentStep.assembling(propene, (cyclopropane,), (propene,))


@pytest.mark.parametrize("smiles", [("O",), ("O", "O", "CCO"), ("C1CC1", "CC=C")])
def test_all_species_cancel_without_fabricating_a_rate_or_crashing(smiles):
    step = _identity(*smiles)
    for assessment in (kinetics_of_step(step), eyring_of_step(step)):
        assert assessment.regime is RateRegime.UNKNOWN
        assert assessment.grade is RateGrade.UNKNOWN
        assert assessment.log10_k is None and assessment.half_life_s is None
        assert "no net chemical transformation" in assessment.reason
    assert _resolve_record(DEFAULT_KINETICS, step) is None
    # The public evidence-key contract remains strict: no empty or invented key.
    with pytest.raises(ValueError, match="no net chemical transformation"):
        reaction_evidence_key(step)
    route = ExperimentRoute.of(step)
    assert fit_route(route, ConstraintBox(max_temperature_k=350)).kinetics.verdict == "UNKNOWN"
    grade = classify_route(route)
    assert grade.kinetics.verdict == "UNKNOWN" and grade.eyring.verdict == "UNKNOWN"


def test_identity_shaped_records_cannot_supply_a_reaction_rate():
    step = _identity("O")
    kinetics = KineticTable((KineticRef(
        (("O", 1),), (("O", 1),), "synthetic identity record", 10, 13, "s^-1", (290, 310),
        "synthetic mutation control",
    ),))
    barriers = EyringTable((EyringRef(
        (("O", 1),), (("O", 1),), "synthetic identity record", 10, 0, "s^-1", (290, 310),
        "synthetic mutation control",
    ),))
    assert kinetics_of_step(step, kinetics=kinetics).regime is RateRegime.UNKNOWN
    assert eyring_of_step(step, barriers=barriers).regime is RateRegime.UNKNOWN


def test_same_formula_isomerization_and_added_spectators_keep_sourced_rates():
    step = _isomerization()
    assert step.reactants[0].formula == step.products[0].formula
    water = parse_smiles("O")
    spectator = replace(step, reactants=(*step.reactants, water), products=(*step.products, water))
    assert reaction_evidence_key(step) == reaction_evidence_key(spectator)
    for provider in (kinetics_of_step, eyring_of_step):
        plain = provider(step, temperature_k=773)
        with_spectator = provider(spectator, temperature_k=773)
        assert plain.is_known
        assert with_spectator.log10_k == pytest.approx(plain.log10_k)


def test_identity_first_step_remains_an_explicit_rate_gap_in_multistep_route():
    route = ExperimentRoute.of(_identity("C1CC1"), _isomerization())
    for result in (verify_kinetics(route, temperature_k=773), verify_eyring(route, temperature_k=773)):
        assert len(result.per_step) == 2
        assert result.per_step[0].regime is RateRegime.UNKNOWN
        assert result.per_step[1].is_known
        assert "no net chemical transformation" in result.explain()


def test_compile_retains_identity_control_diagnostics_under_process_constraints(monkeypatch):
    step = _identity("O")
    route = ExperimentRoute.of(step)
    receipt = RouteSearchReceipt(ROUTE_SEARCH_RECEIPT_SCHEMA, 1, 100, 20000, 1, 0, False, 1)
    result = RouteSearchResult(ROUTE_SEARCH_RESULT_SCHEMA, (route,), receipt)
    monkeypatch.setattr(import_module("smartchem.experiment.compile"), "search_routes", lambda *a, **k: result)
    compiled = compile_synthesis(
        step.target, commodities=(), box=ConstraintBox(process=ProcessBounds(max_step_minutes=60)),
    )
    assert not compiled.found_route
    assert compiled.ranked[0].kinetics.verdict == "UNKNOWN"
    assert "NO_ADMISSIBLE_RETURNED_ROUTE" in compiled.render()


def test_unrelated_evidence_key_failure_is_not_laundered_to_unknown(monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("deliberate evidence-key implementation failure")
    monkeypatch.setattr(ReactionEvidenceKey, "from_molecules", broken)
    for provider in (kinetics_of_step, eyring_of_step):
        with pytest.raises(ValueError, match="deliberate evidence-key implementation failure"):
            provider(_isomerization())
