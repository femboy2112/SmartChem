"""OPERATION XXV, explorer checkpoint P1: pins for the ExplorationSpec / ExplorationReceipt prototype.

Targets are tiny (ethyl acetate). Production runs are cached per spec within this module to keep the suite light.
"""

import copy
import json
from functools import lru_cache

import pytest

from experiments.sandbox_foundation.exploration_xxv import (
    SPEC_SCHEMA,
    ExplorationReceipt,
    ExplorationSpec,
    ExplorationSpecRefusal,
    RefusalReason,
    explore,
    visual_projection,
)
from smartchem.service import InputKind, build_recompile_request, response_to_payload, run_compilation

EA = "CCOC(C)=O"
STOCK = ("CCO", "CC(=O)O")
AXES = (
    "generation_reachability", "reaction_type_recognition", "search_completeness", "conditions_readiness",
    "simulation", "empirical_validation", "visualization",
)
# ban list: any key that collapses the separate axes into one verdict
AGGREGATE_KEYS = {"score", "overall", "verdict", "true", "safe", "safety", "valid", "ok", "passed", "success", "confidence"}


@lru_cache(maxsize=None)
def _receipt(**kw):
    return explore(ExplorationSpec(EA, **kw))


def _spec(**kw):
    return ExplorationSpec(EA, **kw)


def _all_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _all_keys(v)


# ------------------------------------------------------------------------------------------------------ spec digest


def test_spec_digest_stable_and_versioned():
    a, b = _spec(stock=STOCK, max_depth=2), _spec(stock=STOCK, max_depth=2)
    assert a.digest == b.digest and len(a.digest) == 64
    assert a.schema_version == SPEC_SCHEMA == "smartchem.research.exploration_spec/xxv-1"
    assert a.to_dict()["schema_version"] == SPEC_SCHEMA


def test_spec_stock_order_and_duplicates_do_not_move_digest():
    assert _spec(stock=("CCO", "CC(=O)O")).digest == _spec(stock=("CC(=O)O", "CCO", "CCO")).digest


@pytest.mark.parametrize("kw", [
    dict(stock=("CCO",)), dict(max_depth=2), dict(max_routes=3), dict(cut_budget=5),
    dict(algebra_profile="legacy-capped-v1"), dict(simulation_ref="a" * 64),
])
def test_spec_digest_sensitive_to_every_field(kw):
    assert _spec(**kw).digest != _spec().digest


def test_spec_digest_sensitive_to_target():
    assert ExplorationSpec("CCO").digest != _spec().digest


def test_spec_is_frozen():
    s = _spec()
    with pytest.raises(Exception):
        s.target = "CCO"  # type: ignore[misc]
    with pytest.raises(Exception):
        s.schema_version = "x"  # type: ignore[misc]


# -------------------------------------------------------------------------------------------------------- refusals


@pytest.mark.parametrize("layer", ["CONFIGURATION", "ISOTOPIC"])
def test_finer_identity_layers_refused_citing_130(layer):
    with pytest.raises(ExplorationSpecRefusal) as ei:
        ExplorationSpec("N[C@@H](C)C(=O)O", identity_layer=layer)
    assert ei.value.reason is RefusalReason.IDENTITY_LAYER_UNSUPPORTED
    assert ei.value.issue.endswith("/issues/130") and "issues/130" in str(ei.value)


@pytest.mark.parametrize("layer", ["FORMULA", "constitution", "", None])
def test_other_identity_layers_refused_without_130(layer):
    with pytest.raises(ExplorationSpecRefusal) as ei:
        _spec(identity_layer=layer)
    assert ei.value.reason is RefusalReason.IDENTITY_LAYER_UNKNOWN and ei.value.issue is None


def test_unknown_algebra_profile_refused():
    with pytest.raises(ExplorationSpecRefusal) as ei:
        _spec(algebra_profile="no-such-profile")
    assert ei.value.reason is RefusalReason.UNKNOWN_ALGEBRA_PROFILE


@pytest.mark.parametrize("name,value", [
    ("max_depth", 0), ("max_depth", -1), ("max_depth", True), ("max_routes", 1.5), ("cut_budget", "3"),
])
def test_bad_budgets_refused(name, value):
    with pytest.raises(ExplorationSpecRefusal) as ei:
        _spec(**{name: value})
    assert ei.value.reason is RefusalReason.BAD_BUDGET


@pytest.mark.parametrize("ref", ["", "abc", "A" * 64, 7])
def test_bad_simulation_ref_refused(ref):
    with pytest.raises(ExplorationSpecRefusal) as ei:
        _spec(simulation_ref=ref)
    assert ei.value.reason is RefusalReason.BAD_SIMULATION_REF


def test_bad_target_and_stock_refused():
    with pytest.raises(ExplorationSpecRefusal) as ei:
        ExplorationSpec("  ")
    assert ei.value.reason is RefusalReason.BAD_TARGET
    with pytest.raises(ExplorationSpecRefusal) as ei:
        _spec(stock="CCO")
    assert ei.value.reason is RefusalReason.BAD_STOCK


# ---------------------------------------------------------------------------------------- receipt binds production


def test_receipt_binds_spec_and_production_digests():
    spec = _spec(stock=STOCK)
    r = _receipt(stock=STOCK)
    body = r.body
    assert body["spec_digest"] == spec.digest

    # cross-check against an independent direct call of the same public production entry points
    req = build_recompile_request(EA, input_kind=InputKind.SMILES, stock_materials=STOCK,
                                  algebra_profile="certified-route-v07")
    payload = response_to_payload(run_compilation(req))
    prod = body["production"]
    assert prod["result_digest"] == payload["result_digest"]
    assert prod["request_semantic_digest"] == req.semantic_digest
    assert prod["request_digest"] == req.digest
    assert prod["ir_request_digest"] == payload["compilation_ir"]["request_digest"]
    assert prod["response_schema_version"] == payload["schema_version"]
    assert prod["result_digest_scope"] == "VERSION_BOUND_NOT_CROSS_RELEASE_STABLE"
    assert body["axes"]["generation_reachability"]["routes_returned"] == len(payload["ranked_route_dossiers"])


def test_stock_change_changes_receipt_and_production_digests():
    a, b = _receipt(stock=STOCK), _receipt(stock=("CCO",))
    assert a.digest != b.digest
    assert a.body["spec_digest"] != b.body["spec_digest"]
    assert a.body["production"]["result_digest"] != b.body["production"]["result_digest"]
    assert a.body["production"]["request_semantic_digest"] != b.body["production"]["request_semantic_digest"]


def test_determinism_two_runs_identical_receipt_digest():
    spec = _spec(stock=STOCK, max_depth=2)
    r1, r2 = explore(spec), explore(spec)
    assert r1.digest == r2.digest and r1.body_json == r2.body_json
    assert visual_projection(r1) == visual_projection(r2)


def test_receipt_digest_is_derived_not_suppliable():
    r = _receipt(stock=STOCK)
    with pytest.raises(TypeError):
        ExplorationReceipt(r.body_json, digest="0" * 64)  # type: ignore[call-arg]
    with pytest.raises(Exception):
        r.digest = "0" * 64  # type: ignore[misc]
    assert ExplorationReceipt(r.body_json).digest == r.digest
    assert ExplorationReceipt(r.body_json.replace("COMPLETE", "XOMPLETE")).digest != r.digest


# ------------------------------------------------------------------------------------------------ separate axes


def test_verdict_axes_present_and_separate():
    r = _receipt(stock=STOCK)
    axes = r.body["axes"]
    assert set(axes) == set(AXES)
    # every axis is its own object; no axis embeds another axis' verdict word as a shared field
    assert all(isinstance(axes[k], dict) for k in AXES)
    assert axes["generation_reachability"]["outcome"] == "ROUTES_FOUND"
    assert axes["search_completeness"]["status"] == "COMPLETE_WITHIN_DECLARED_BOUNDS"
    assert axes["simulation"] == {"status": "NOT_RUN", "ref": None}
    assert axes["empirical_validation"] == {"status": "UNVERIFIED"}
    assert axes["visualization"] == {"status": "PROJECTION_ONLY"}


def test_recognition_is_per_step_copied_from_production_including_unrecognized():
    r = _receipt(stock=STOCK)
    per_route = r.body["axes"]["reaction_type_recognition"]["per_route"]
    statuses = {s["status"] for route in per_route for s in route["steps"]}
    assert "RECOGNIZED" in statuses and "NOT_RECOGNIZED" in statuses
    for route in per_route:
        for s in route["steps"]:
            assert s["production_status"] in {"SATISFIED", "UNSATISFIED", "UNKNOWN", "NOT_APPLICABLE"}
            if s["status"] == "NOT_RECOGNIZED":
                # the wire does not distinguish an oracle ABSTAIN from an internal recognizer fault
                assert s["abstain_vs_internal_error"] == "UNKNOWN" and s["reaction_class_name"] is None
            if s["status"] == "RECOGNIZED":
                assert s["reaction_class_name"]


def test_conditions_readiness_is_not_a_pass_without_evidence():
    r = _receipt(stock=STOCK)
    for route in r.body["axes"]["conditions_readiness"]["per_route"]:
        assert route["readiness_tier"] in {"FORMAL_CANDIDATE", "REACTION_VOUCHED"}
        assert all(s["conditions"] == "UNKNOWN" and s["process"] == "UNKNOWN" for s in route["steps"])


def test_no_aggregate_field_anywhere():
    r = _receipt(stock=STOCK)
    top = set(r.to_dict())
    assert top == {"schema_version", "digest", "spec_digest", "spec", "production", "axes", "routes"}
    keys = {k.lower() for k in _all_keys(r.to_dict())}
    assert not (keys & AGGREGATE_KEYS)
    proj_keys = {k.lower() for k in _all_keys(visual_projection(r))}
    assert not (proj_keys & AGGREGATE_KEYS)


def test_simulation_ref_is_carried_but_never_run():
    ref = "b" * 64
    r = _receipt(stock=STOCK, simulation_ref=ref)
    assert r.body["axes"]["simulation"] == {"status": "REFERENCED_NOT_RUN", "ref": ref}
    assert r.body["axes"]["empirical_validation"]["status"] == "UNVERIFIED"
    assert r.digest != _receipt(stock=STOCK).digest


# ------------------------------------------------------------------------------------ INCOMPLETE, not IMPOSSIBLE


def test_budget_truncation_reads_incomplete_not_impossible():
    # cut_budget=1 truncates the cut enumeration before any route is observed (verified from the payload below)
    spec = _spec(cut_budget=1)
    r = explore(spec)
    req_payload = response_to_payload(run_compilation(build_recompile_request(
        EA, input_kind=InputKind.SMILES,
        stock_materials=(), cut_budget=1, algebra_profile="certified-route-v07")))
    assert req_payload["outcome"] == "INCOMPLETE"
    assert req_payload["search_space_status"] == "INCOMPLETE_NO_ROUTE_OBSERVED"
    assert req_payload["compilation_ir"]["search_status"] == "PARTIAL_CUT_BUDGET"
    assert req_payload["ranked_route_dossiers"] == []

    axes = r.body["axes"]
    assert axes["generation_reachability"]["routes_returned"] == 0
    assert axes["generation_reachability"]["outcome"] == "INCOMPLETE"
    assert axes["generation_reachability"]["no_route_reading"] == "NO_ROUTE_OBSERVED_SEARCH_INCOMPLETE"
    assert axes["search_completeness"]["status"] == "INCOMPLETE"
    assert axes["search_completeness"]["search_space_status"] == "INCOMPLETE_NO_ROUTE_OBSERVED"
    assert axes["search_completeness"]["search_receipt"]["cut_enumeration_complete"] is False
    assert "IMPOSSIBLE" not in r.body_json.upper() and "NO_ROUTE_COMPLETE" not in r.body_json


def test_depth_truncation_with_routes_is_still_incomplete():
    r = _receipt(stock=STOCK, max_depth=1)
    axes = r.body["axes"]
    assert axes["generation_reachability"]["no_route_reading"] == "ROUTES_PRESENT"
    assert axes["search_completeness"]["status"] == "INCOMPLETE"
    assert axes["search_completeness"]["search_status"] == "PARTIAL_DEPTH_LIMIT"


def test_result_limit_truncation_is_incomplete():
    r = _receipt(stock=STOCK, max_routes=1)
    c = r.body["axes"]["search_completeness"]
    assert c["status"] == "INCOMPLETE" and c["search_status"] == "PARTIAL_RESULT_LIMIT"
    assert c["search_receipt"]["result_limit"] == 1


def test_complete_no_route_is_scoped_to_declared_bounds_not_absolute():
    # a complete, exhaustive-within-bounds no-route answer is NOT promoted to impossibility either
    r = explore(ExplorationSpec("[Fe]", max_depth=1))
    axes = r.body["axes"]
    assert axes["generation_reachability"]["outcome"] == "NO_ROUTE_COMPLETE"
    assert axes["generation_reachability"]["no_route_reading"] == "NO_ROUTE_WITHIN_DECLARED_BOUNDS"
    assert axes["search_completeness"]["declared_space_only"] is True
    assert "IMPOSSIBLE" not in r.body_json.upper()


def test_invalid_target_is_not_searched_and_not_a_verdict_on_chemistry():
    r = explore(ExplorationSpec("C("))
    axes = r.body["axes"]
    assert axes["generation_reachability"]["outcome"] == "INVALID_INPUT"
    assert axes["generation_reachability"]["no_route_reading"] == "NOT_SEARCHED"
    assert axes["search_completeness"]["status"] == "NOT_RUN"


# --------------------------------------------------------------------------------------------------- projection


def test_projection_shape_and_recognition_labels():
    r = _receipt(stock=STOCK)
    p = visual_projection(r)
    assert p["status"] == "PROJECTION_ONLY" and p["receipt_digest"] == r.digest
    ids = {n["id"] for n in p["nodes"]}
    assert p["nodes"] and p["edges"]
    kinds = {n["kind"] for n in p["nodes"]}
    assert kinds == {"MOLECULE", "REACTION"}
    for e in p["edges"]:
        assert e["source"] in ids and e["target"] in ids
        assert e["recognition"]["status"] in {"RECOGNIZED", "NOT_RECOGNIZED", "UNKNOWN", "NOT_APPLICABLE"}
    assert any(e["recognition"]["status"] == "RECOGNIZED" for e in p["edges"])
    assert any(e["recognition"]["status"] == "NOT_RECOGNIZED" for e in p["edges"])
    assert p["axes"] == r.body["axes"]
    assert {n["formula"] for n in p["nodes"] if n["kind"] == "MOLECULE"} >= {"C4H8O2", "C2H6O", "C2H4O2"}


def test_projection_write_isolation():
    r = _receipt(stock=STOCK)
    digest_before, body_before = r.digest, r.body_json
    reference = copy.deepcopy(visual_projection(r))
    p = visual_projection(r)
    # mutate every level of the returned dict
    p["axes"]["search_completeness"]["status"] = "COMPLETE_WITHIN_DECLARED_BOUNDS_FORGED"
    p["axes"]["empirical_validation"]["status"] = "VALIDATED"
    p["axes"]["simulation"]["status"] = "RAN"
    p["nodes"][0]["kind"] = "FORGED"
    p["nodes"].clear()
    p["edges"][0]["recognition"]["status"] = "RECOGNIZED"
    p["edges"].clear()
    p["status"] = "CERTIFIED"
    body = r.body
    body["axes"]["empirical_validation"]["status"] = "VALIDATED"
    body["routes"].clear()
    # the receipt and its digest are untouched, and a fresh projection equals the pre-mutation reference
    assert r.digest == digest_before and r.body_json == body_before
    assert ExplorationReceipt(r.body_json).digest == digest_before
    assert r.body["axes"]["empirical_validation"]["status"] == "UNVERIFIED"
    assert visual_projection(r) == reference
    assert json.loads(r.body_json)["routes"]


def test_projection_adds_no_unreceipted_content():
    r = _receipt(stock=STOCK)
    p = visual_projection(r)
    receipt_ids = {n["id"] for route in r.body["routes"] for s in route["steps"] for n in s["reactants"] + s["products"]}
    assert {n["id"] for n in p["nodes"] if n["kind"] == "MOLECULE"} == receipt_ids
