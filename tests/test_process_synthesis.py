"""Selection guards over real conserved routes, fit checks and epistemic grading.

Only enumeration is injected: the synthetic envelopes below are adversarial test
inputs, not reaction instructions or additions to the chemistry evidence seed.
"""
from importlib import import_module

import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment.classify import Grade, classify_route
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.drafter import ConstraintBox, RouteFitStatus, fit_route
from smartchem.experiment.routes import (
    ROUTE_SEARCH_RECEIPT_SCHEMA,
    ROUTE_SEARCH_RESULT_SCHEMA,
    RouteSearchReceipt,
    RouteSearchResult,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.process_constraints import ProcessBounds, ProcessRequirements
from smartchem.structure import structure_by_name


def _mol(name):
    return structure_by_name(name).molecule


def _route(*, attested, temperature=None, process=None):
    target = _mol("paracetamol")
    acyl = _mol("acetic anhydride" if attested else "acetic acid")
    byproduct = _mol("acetic acid" if attested else "water")
    kwargs = {} if process is None else {"process": process}
    envelope = ConditionEnvelope(
        temperature=Interval(*temperature, "K") if temperature is not None else None,
        medium="synthetic condition control",
        status=EvidenceStatus.EXPERIMENTAL,
        provenance="synthetic selection regression control; not a chemistry source",
        **kwargs,
    )
    return ExperimentRoute.of(ExperimentStep.assembling(
        target, (_mol("4-aminophenol"), acyl), (target, byproduct), envelope=envelope,
    ))


def _inject_search(monkeypatch, routes, *, partial=False):
    receipt = RouteSearchReceipt(
        ROUTE_SEARCH_RECEIPT_SCHEMA, 1, 100, 20000, 1,
        int(partial), False, len(routes),
    )
    search = RouteSearchResult(ROUTE_SEARCH_RESULT_SCHEMA, tuple(routes), receipt)
    module = import_module("smartchem.experiment.compile")
    monkeypatch.setattr(module, "search_routes", lambda *args, **kwargs: search)
    return receipt


@pytest.mark.parametrize("temperature,status", [((290, 300), RouteFitStatus.FITS), (None, RouteFitStatus.UNKNOWN)])
def test_known_grade_cannot_override_a_hard_bench_exclusion(monkeypatch, temperature, status):
    known = _route(attested=True, temperature=(390, 400))
    candidate = _route(attested=False, temperature=temperature)
    box = ConstraintBox(max_temperature_k=350)
    # Calibrate the rival: no fake classifier or fit statuses hide the original bug.
    assert classify_route(known).grade is Grade.KNOWN
    candidate_grade = classify_route(candidate).grade
    assert candidate_grade in (Grade.DERIVED, Grade.PREDICTED, Grade.HYPOTHESIZED)
    assert fit_route(known, box).status is RouteFitStatus.EXCLUDED
    assert fit_route(candidate, box).status is status
    _inject_search(monkeypatch, (known, candidate))
    compiled = compile_synthesis(_mol("paracetamol"), box=box)
    assert compiled.best_draft is not None
    assert compiled.best_draft.route == candidate
    assert compiled.verdict.grade is candidate_grade
    assert len(compiled.ranked) == 2
    assert any(fit.status is RouteFitStatus.EXCLUDED for fit in compiled.ranked)


@pytest.mark.parametrize("partial", [False, True])
def test_all_excluded_has_diagnostics_but_no_dossier_or_shopping(monkeypatch, partial):
    known = _route(attested=True, temperature=(390, 400))
    receipt = _inject_search(monkeypatch, (known,), partial=partial)
    compiled = compile_synthesis(_mol("paracetamol"), box=ConstraintBox(max_temperature_k=350))
    assert not compiled.found_route
    assert compiled.best_draft is None and compiled.verdict is None
    assert compiled.kinetics is None and compiled.eyring is None
    assert compiled.shopping == () and compiled.other_leaves == ()
    assert len(compiled.ranked) == 1 and compiled.ranked[0].exclusions
    assert compiled.search_receipt is receipt
    rendered = compiled.render()
    assert "NO_ADMISSIBLE_RETURNED_ROUTE" in rendered
    assert "EXCLUDED" in rendered and "400" in rendered
    assert "SHOPPING LIST" not in rendered
    assert "NO_ROUTE_IN_DECLARED_SPACE" not in rendered
    assert ("PARTIAL_CANDIDATE_SET" in rendered) is partial


def test_grade_preference_survives_when_no_bench_constraint_is_active(monkeypatch):
    known = _route(attested=True, temperature=(390, 400))
    candidate = _route(attested=False, temperature=(290, 300))
    _inject_search(monkeypatch, (candidate, known))
    compiled = compile_synthesis(_mol("paracetamol"))
    assert compiled.best_draft.route == known
    assert compiled.verdict.grade is Grade.KNOWN


def _process(elapsed):
    return ProcessRequirements(
        elapsed_minutes=Interval(elapsed, elapsed, "min"), workup_included=True,
        provenance="synthetic whole-step duration control; not a chemistry source",
    )


def test_process_unknown_is_retained_but_never_selected_as_manageable(monkeypatch):
    known = _route(attested=True, temperature=(290, 300))
    _inject_search(monkeypatch, (known,))
    compiled = compile_synthesis(
        _mol("paracetamol"), box=ConstraintBox(process=ProcessBounds(max_step_minutes=60)),
    )
    assert compiled.ranked[0].status is RouteFitStatus.UNKNOWN
    assert not compiled.found_route and compiled.shopping == ()
    assert "NO_ADMISSIBLE_RETURNED_ROUTE" in compiled.render()
    assert "UNKNOWN" in compiled.render()
    assert any("require assessed FITS" in note for note in compiled.ledger)


@pytest.mark.parametrize("known_process,status", [
    (None, RouteFitStatus.UNKNOWN),
    (_process(120), RouteFitStatus.EXCLUDED),
])
def test_process_fit_wins_over_better_grade_that_cannot_meet_selection_contract(
    monkeypatch, known_process, status,
):
    known = _route(attested=True, temperature=(290, 300), process=known_process)
    candidate = _route(attested=False, temperature=(290, 300), process=_process(30))
    box = ConstraintBox(process=ProcessBounds(max_step_minutes=60))
    assert fit_route(known, box).status is status
    assert fit_route(candidate, box).status is RouteFitStatus.FITS
    _inject_search(monkeypatch, (known, candidate))
    compiled = compile_synthesis(_mol("paracetamol"), box=box)
    assert compiled.best_draft.route == candidate
    assert "route fit: FITS" in compiled.render()


def test_process_bound_change_releases_formally_eligible_candidate(monkeypatch):
    candidate = _route(attested=False, temperature=(290, 300), process=_process(30))
    _inject_search(monkeypatch, (candidate,))
    tight = compile_synthesis(
        _mol("paracetamol"), box=ConstraintBox(process=ProcessBounds(max_step_minutes=10)),
    )
    relaxed = compile_synthesis(
        _mol("paracetamol"), box=ConstraintBox(process=ProcessBounds(max_step_minutes=60)),
    )
    assert not tight.found_route
    assert relaxed.best_draft.route == candidate
    assert tight.search_receipt == relaxed.search_receipt


@pytest.mark.parametrize("flags", [
    ["--process-profile", "quick"],
    ["--process-profile", "low-touch", "--max-temp", "333", "--min-pressure", "0.5"],
    ["--max-active-minutes", "10", "--attention", "periodic", "passive",
     "--agitation", "none", "periodic", "--equipment", "stirrer"],
])
def test_process_flags_have_one_request_identity_across_all_synthesis_frontends(capsys, flags):
    from smartchem.cli import main
    from smartchem.service import deserialize_request

    outputs = []
    for command in ("compile", "recompile", "synthesize"):
        code = main([command, "acetic anhydride", *flags, "--emit-request"])
        captured = capsys.readouterr()
        assert code == 0, captured.err
        outputs.append(captured.out)
    assert outputs[0] == outputs[1] == outputs[2]
    request = deserialize_request(outputs[0])
    assert request.constraints.process.constrains_anything


@pytest.mark.parametrize("flags", [
    ["--max-step-minutes", "nan"],
    ["--max-active-minutes", "inf"],
    ["--min-check-interval", "-1"],
])
def test_invalid_process_limits_are_domain_errors_in_every_frontend(capsys, flags):
    from smartchem.cli import main

    for command in ("compile", "recompile", "synthesize"):
        code = main([command, "acetic anhydride", *flags, "--emit-request"])
        captured = capsys.readouterr()
        assert code == 2
        assert "internal error" not in captured.err.lower()


@pytest.mark.parametrize("depth,expected_exit", [(1, 4), (3, 5)])
def test_unknown_process_candidates_do_not_pass_human_json_or_quiet_views(capsys, depth, expected_exit):
    from smartchem.cli import main
    from smartchem.service import deserialize_response

    args = ["acetic anhydride", "--max-step-minutes", "60", "--max-depth", str(depth)]
    json_outputs = []
    for command in ("compile", "recompile", "synthesize"):
        code = main([command, *args, "--json"])
        captured = capsys.readouterr()
        assert code == expected_exit, captured.err
        response = deserialize_response(captured.out)
        assert response.process_selection_status == "NO_FIT_FOUND"
        assert response.admissible_route_digests == ()
        assert response.ranked_route_dossiers
        assert all(fit.fit_status == "UNKNOWN" for fit in response.ranked_route_dossiers)
        json_outputs.append(captured.out)
        human_code = main([command, *args])
        captured = capsys.readouterr()
        assert human_code == expected_exit, captured.err
        assert "UNKNOWN" in captured.out
        assert "SHOPPING LIST" not in captured.out
        if command != "recompile":
            assert "NO_ADMISSIBLE_RETURNED_ROUTE" in captured.out
    assert json_outputs[0] == json_outputs[1] == json_outputs[2]
    assert main(["recompile", *args, "--quiet"]) == expected_exit
    quiet = capsys.readouterr().out
    assert "NO_FIT_FOUND" in quiet and "UNKNOWN" in quiet
