"""Integration controls use invented metadata, never experimental chemistry evidence."""
from dataclasses import replace

import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.constraints import PhysicalBounds
from smartchem.experiment import routes
from smartchem.experiment.drafter import ConstraintBox, fit_route
from smartchem.process_constraints import Agitation, ProcessBounds, ProcessRequirements
from smartchem.service import (
    build_recompile_request, deserialize_request, deserialize_response, request_to_payload,
    request_from_payload, response_from_payload, response_to_payload, run_compilation,
    serialize_request, serialize_response,
)


def requirements(**changes):
    return replace(ProcessRequirements(
        elapsed_minutes=Interval(10, 20, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True,
        provenance="synthetic software control; no experimental claim",
    ), **changes)


def request(**kwargs):
    return build_recompile_request("smiles:CC(=O)OC", max_depth=2,
                                   process=ProcessBounds.quick(), **kwargs)


def test_process_profile_is_semantic_and_round_trips():
    req = request()
    assert deserialize_request(serialize_request(req)).semantic_digest == req.semantic_digest
    other = replace(req, constraints=replace(req.constraints, process=ProcessBounds.low_touch()))
    assert other.semantic_digest != req.semantic_digest


@pytest.mark.parametrize("mutation", ["missing", "extra", "nan", "enum"])
def test_invalid_process_payload_cannot_silently_drop_constraints(mutation):
    payload = request_to_payload(request())
    process = payload["constraints"]["process"]
    if mutation == "missing":
        del process["max_step_minutes"]
    elif mutation == "extra":
        process["pretend_unknown_fits"] = True
    elif mutation == "nan":
        process["max_step_minutes"] = float("nan")
    else:
        process["allowed_attention"] = ["EASY"]
    with pytest.raises((ValueError, TypeError)):
        request_from_payload(payload)


def test_real_catalog_unknown_process_is_neither_admitted_nor_cost_recommended():
    result = run_compilation(request())
    assert result.candidates
    assert result.process_selection_status == "NO_FIT_FOUND"
    assert result.exit_code == 5
    assert result.admissible_route_digests == result.affordability_frontier == ()
    assert all(r.fit_status == "UNKNOWN" for r in result.ranked_route_dossiers)
    assert deserialize_response(serialize_response(result)).result_digest == result.result_digest


def test_synthetic_declared_control_fits_real_search_and_workup_mutation_kills_it(monkeypatch):
    original = routes._conditions_for
    metadata = requirements()
    monkeypatch.setattr(routes, "_conditions_for", lambda t: replace(original(t), process=metadata))
    fit = run_compilation(request())
    assert fit.process_selection_status == "FITS_FOUND" and fit.exit_code == 0
    assert set(fit.admissible_route_digests) == {c.candidate_digest for c in fit.candidates}
    assert all(r.readiness_tier == "FORMAL_CANDIDATE" for r in fit.ranked_route_dossiers)
    metadata = replace(metadata, workup_included=False)
    gap = run_compilation(request())
    assert gap.exit_code == 5 and not gap.admissible_route_digests
    assert gap.result_digest != fit.result_digest


@pytest.mark.parametrize("field,forged", [
    ("process_selection_status", "FITS_FOUND"), ("admissible_route_digests", ["fabricated"]),
    ("exit_code", 0), ("result_digest", "fabricated"),
])
def test_derived_admission_fields_are_checked_when_loading(field, forged):
    payload = response_to_payload(run_compilation(request()))
    payload[field] = forged
    with pytest.raises(ValueError, match=field):
        response_from_payload(payload)


def test_nonexistent_or_duplicate_ranked_routes_cannot_be_admitted():
    result = run_compilation(request())
    first = result.ranked_route_dossiers[0]
    forged = replace(first, route_digest="f" * 64, fit_status="FITS", gaps=(), exclusions=())
    with pytest.raises(ValueError, match="returned IR candidate"):
        replace(result, ranked_route_dossiers=(forged,))
    with pytest.raises(ValueError, match="unique"):
        replace(result, ranked_route_dossiers=(first, first))


def test_imported_frontier_cannot_bypass_process_admission():
    restricted = run_compilation(request())
    donor = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    assert donor.affordability_frontier
    with pytest.raises(ValueError, match="only admitted FITS"):
        replace(restricted, affordability_frontier=donor.affordability_frontier)


@pytest.mark.parametrize("field,value,bounds", [
    ("peak_temperature_k", 500, PhysicalBounds.of(max_temperature_k=350)),
    ("max_pressure_atm", 5, PhysicalBounds.of(max_pressure_atm=2)),
    ("min_pressure_atm", 0.1, PhysicalBounds.of(min_pressure_atm=0.5)),
])
def test_workup_extrema_override_mild_reaction_conditions(field, value, bounds):
    from smartchem.contracts import EvidenceStatus
    from smartchem.experiment.step import ExperimentRoute, ExperimentStep
    from smartchem.identity_parse import resolve_target
    water = resolve_target("water")
    # Conserving identity control isolates admission; no synthesis claim.
    def route(metadata):
        envelope = ConditionEnvelope(temperature=Interval(300, 300, "K"),
            pressure=Interval(1, 1, "atm"), status=EvidenceStatus.EXPERIMENTAL,
            provenance="synthetic physical control", process=metadata)
        return ExperimentRoute.of(ExperimentStep.assembling(water, (water,), (water,), envelope=envelope))
    box = ConstraintBox.of_bounds(bounds, process=ProcessBounds.quick())
    unknown = fit_route(route(requirements()), box)
    assert any("whole-process" in gap and field in gap for gap in unknown.gaps)
    excluded = fit_route(route(requirements(**{field: value})), box)
    assert any("whole-process" in reason and field in reason for reason in excluded.exclusions)


@pytest.mark.parametrize("field,interval", [
    ("temperature", Interval(-10, -5, "K")),
    ("pressure", Interval(-1, 0, "atm")),
    ("duration", Interval(-10, -5, "min")),
])
def test_invalid_declared_conditions_are_rejected_at_construction(field, interval):
    from smartchem.contracts import EvidenceStatus
    with pytest.raises(ValueError):
        ConditionEnvelope(**{field: interval}, status=EvidenceStatus.EXPERIMENTAL,
                          provenance="malformed control")
