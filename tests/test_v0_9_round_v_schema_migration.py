"""0.9 RC Round V, barrier D11 -- the wire-schema freeze and the EXPLICIT v0.8 legacy migration.

Every v0.8 artifact here is REAL: produced by the released main@df1b38d (0.8.0a1) producer's own public path from a
``git archive df1b38d`` tree (tests/fixtures/v08/README.md carries the commands and sha256).  Nothing is simulated by
stripping keys off a 0.9 payload -- that is exactly how Round IV's F54 "additive-optional" claim went unrefuted while
every genuine v0.8 routes-mode response was refused with a misleading digest error (F81).

The v0.8 schema ids are READ FROM THE FIXTURES, never hard-coded here, so the M80 guard ("each bumped id differs from
the released one") cannot pass vacuously against a constant that drifted with the code.  None of these tests depends
on a 0.9 golden digest (other Round V writers are moving capability/stock/procedure digests concurrently); the only
literal digests below are v0.8 values MEASURED by the main@df1b38d code on these same fixtures.
"""
from __future__ import annotations

import copy
import dataclasses as dc
import hashlib
import json
import re
from pathlib import Path

import pytest

from smartchem.capability.enums import EquipmentCapability
from smartchem.capability.presets import custom
from smartchem.constraints import PHYSICAL_BOUNDS_SCHEMA
from smartchem.contracts import canonical_digest
from smartchem.service import (
    COMPILATION_REQUEST_SCHEMA,
    COMPILATION_RESPONSE_SCHEMA,
    COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR,
    LEGACY_V08_PHYSICAL_BOUNDS_SCHEMA,
    LEGACY_V08_RANKED_DAG_SUMMARY_SCHEMA,
    LEGACY_V08_RANKED_ROUTE_SUMMARY_SCHEMA,
    LEGACY_V08_REQUEST_SCHEMA,
    LEGACY_V08_RESPONSE_SCHEMA,
    RANKED_DAG_SUMMARY_SCHEMA,
    RANKED_ROUTE_SUMMARY_SCHEMA,
    _route_readiness_to_payload,
    _transport_bound_result_digest,
    _v08_digest,
    build_recompile_request,
    request_from_payload,
    request_to_payload,
    response_from_payload,
    response_schema,
    response_to_payload,
    run_compilation,
)

FIX = Path(__file__).parent / "fixtures" / "v08"


def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


_REQUESTS = ("request_isopentyl_acetate.json", "request_ethyl_acetate_smiles.json",
             "request_invalid_input_ethyl_acetate_name.json")
_RESPONSES = ("response_isopentyl_acetate.json", "response_ethyl_acetate_smiles.json",
              "response_ethyl_acetate_smiles_thin.json", "response_invalid_input_ethyl_acetate_name.json",
              "response_isopentyl_acetate_dag.json", "response_stereo_isopentyl_acetate_smiles.json")
_CANONICAL_ROUTE_RESPONSES = ("response_isopentyl_acetate.json", "response_ethyl_acetate_smiles.json")

# v0.8 ids, read from the real fixtures (M80: never from the constants under test).
V08_REQUEST_ID = _load("request_isopentyl_acetate.json")["schema_version"]
V08_RESPONSE_ID = _load("response_isopentyl_acetate.json")["schema_version"]
V08_SUMMARY_ID = _load("response_isopentyl_acetate.json")["ranked_route_dossiers"][0]["schema_version"]
V08_DESCRIPTOR_ID = _load("response_schema_descriptor.json")["descriptor_version"]
# X-high D22: the released DAG summary and PhysicalBounds ids, likewise read from REAL v0.8 producer output (the DAG
# fixture is the v0.8 producer's own convergent-mode run -- tests/fixtures/v08/README.md, gen_dag_v08.py).
V08_DAG_SUMMARY_ID = _load("response_isopentyl_acetate_dag.json")["ranked_dag_dossiers"][0]["schema_version"]
V08_PHYSICAL_BOUNDS_ID = _load("request_isopentyl_acetate.json")["constraints"]["schema_version"]

# Measured by the main@df1b38d code itself on these fixtures (Lane D, scratchpad r5/laneD/dig_v08.json) -- the
# v0.8 truth a faithful legacy decode must reproduce byte-for-byte.
_V08_MEASURED = {
    "request_isopentyl_acetate.json": (
        "8ae5c3036eb26966dff34f3d38fee8e82fc4e9cbeeb047483960118c5c1d2197",
        "16f6cc4ca92d8a6ef63e4b69c78adececf7a9ccc91fd972809cf6a16703ad183"),
    "request_ethyl_acetate_smiles.json": (
        "1523ea4a482e07e87c43b3c9feecfef2c835d9db2441f49e5e728fc18a15f9b6",
        "fb162a1f4370c7582cde23fa5d05b3a4e2524d4546555e2df380e96f9e7cc937"),
    "request_invalid_input_ethyl_acetate_name.json": (
        "ee83a92313224323c985bc27233f314e8c8fbd109b16fb55f0fd7ab8845a8d61",
        "549e4de14cb7e45ca47ba7d23090bac3189b3939877d22c798f812935b74c5e1"),
}


# -- fixture integrity ---------------------------------------------------------------------------------------------

def test_every_v08_fixture_matches_its_recorded_sha256():
    """The fixtures are evidence: a hand edit would silently turn a real v0.8 artifact into a simulated one."""
    readme = (FIX / "README.md").read_text()
    recorded = dict((name, sha) for sha, name in re.findall(r"^\s+([0-9a-f]{64})\s+(\S+)$", readme, re.M))
    for path in sorted(FIX.glob("*.json")) + sorted((FIX / "tamper").glob("*.json")):
        assert recorded[path.name] == hashlib.sha256(path.read_bytes()).hexdigest(), path.name


# -- M80: every shape-changed id is bumped relative to the released main@df1b38d ------------------------------------

def test_each_bumped_id_differs_from_the_released_v08_id():
    assert COMPILATION_REQUEST_SCHEMA != V08_REQUEST_ID
    assert COMPILATION_RESPONSE_SCHEMA != V08_RESPONSE_ID
    assert RANKED_ROUTE_SUMMARY_SCHEMA != V08_SUMMARY_ID
    assert COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR != V08_DESCRIPTOR_ID
    assert RANKED_DAG_SUMMARY_SCHEMA != V08_DAG_SUMMARY_ID          # X-high D22 (A-WIRE P3: replay shape changed)
    assert PHYSICAL_BOUNDS_SCHEMA != V08_PHYSICAL_BOUNDS_ID         # X-high D14 (+min_temperature_k)
    # ... and the legacy whitelist names EXACTLY the released ids (no guessed or drifted legacy id).
    assert (LEGACY_V08_REQUEST_SCHEMA, LEGACY_V08_RESPONSE_SCHEMA, LEGACY_V08_RANKED_ROUTE_SUMMARY_SCHEMA,
            LEGACY_V08_RANKED_DAG_SUMMARY_SCHEMA, LEGACY_V08_PHYSICAL_BOUNDS_SCHEMA) == (
        V08_REQUEST_ID, V08_RESPONSE_ID, V08_SUMMARY_ID, V08_DAG_SUMMARY_ID, V08_PHYSICAL_BOUNDS_ID)


def test_descriptor_declares_the_legacy_whitelist_and_the_new_fields():
    schema = response_schema()
    assert schema["accepted_legacy_schema_versions"] == {
        "request": [V08_REQUEST_ID], "response": [V08_RESPONSE_ID], "ranked_route_summary": [V08_SUMMARY_ID],
        "ranked_dag_summary": [V08_DAG_SUMMARY_ID], "physical_bounds": [V08_PHYSICAL_BOUNDS_ID]}
    assert "capability_question_digest" in schema["response_fields"]
    assert "capability_assessment" in schema["ranked_route_summary_fields"]
    assert "capability_profile" in schema["response_fields"]["request"]
    assert "material_uses" in schema["ranked_route_summary_fields"]["replay_payload"]
    assert "specification" in schema["ranked_route_summary_fields"]["replay_payload"]
    assert COMPILATION_REQUEST_SCHEMA.rsplit("/", 1)[1] in schema["response_fields"]["request"]
    # X-high D14/D18/D20: the floor, the evidence-graded phase and the consumer question pin are disclosed.
    assert "min_temperature_k" in schema["response_fields"]["request"]
    assert "PhaseClaim" in schema["ranked_route_summary_fields"]["replay_payload"]
    assert "expected_capability_question_digest" in schema["response_fields"]["capability_question_digest"]


# -- legacy REQUESTS -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", _REQUESTS)
def test_real_v08_request_loads_as_legacy_not_requested(name):
    req = request_from_payload(_load(name))
    assert req.schema_version == V08_REQUEST_ID and req.is_legacy_v08  # LEGACY, not native
    assert req.capability_profile is None and req.capability_profile_origin == ""
    assert req.capability_question_digest is None  # no question fabricated
    semantic, full = _V08_MEASURED[name]
    assert req.semantic_digest == semantic  # the stored legacy id keeps the v0.8 search identity verifying
    assert req.digest == full  # the frozen v0.8 rule reproduces the v0.8 full identity byte-for-byte


def _with_bounds_generation(request, request_id, bounds_id):
    """Relabel a request AND its embedded constraints box to one schema generation (X-high D22 pairs them)."""
    bounds = dc.replace(request.constraints.bounds, schema_version=bounds_id)
    return dc.replace(request, schema_version=request_id, constraints=dc.replace(request.constraints, bounds=bounds))


def test_the_request_bump_moves_semantic_digest_once_and_only_via_the_id():
    """DECLARED one-time move: the request id is hashed into semantic_digest, so the SAME request re-labelled with the
    current id (and its box with the current PhysicalBounds generation) gets a new semantic_digest -- and nothing else
    about it moved: relabelling back reproduces the MEASURED v0.8 search identity exactly."""
    legacy = request_from_payload(_load("request_isopentyl_acetate.json"))
    relabelled = _with_bounds_generation(legacy, COMPILATION_REQUEST_SCHEMA, PHYSICAL_BOUNDS_SCHEMA)
    assert relabelled.semantic_digest != legacy.semantic_digest
    back = _with_bounds_generation(relabelled, V08_REQUEST_ID, V08_PHYSICAL_BOUNDS_ID)
    assert back.semantic_digest == legacy.semantic_digest == _V08_MEASURED["request_isopentyl_acetate.json"][0]


def test_request_and_constraints_box_generations_cannot_mix():
    """X-high D14/D22: a current request carries the v1alpha2 box, a legacy one the released v1alpha1 box -- mixing
    either way is refused at construction (a 0.9 floor cannot hide under a 0.8 id, nor a 0.8 box under a 0.9 id)."""
    legacy = request_from_payload(_load("request_isopentyl_acetate.json"))
    with pytest.raises(ValueError, match="generation mixing"):
        dc.replace(legacy, schema_version=COMPILATION_REQUEST_SCHEMA)
    current = _with_bounds_generation(legacy, COMPILATION_REQUEST_SCHEMA, PHYSICAL_BOUNDS_SCHEMA)
    with pytest.raises(ValueError, match="generation mixing"):
        _with_bounds_generation(current, COMPILATION_REQUEST_SCHEMA, V08_PHYSICAL_BOUNDS_ID)


def test_a_legacy_constraints_box_cannot_smuggle_a_temperature_floor():
    """X-high D14: ``min_temperature_k`` exists only on the 0.9 wire -- a v1alpha1 box carrying it (even null) is refused
    by the exact key-set guard AND the any-depth 0.9-only-key scan."""
    payload = _load("request_isopentyl_acetate.json")
    payload["constraints"]["min_temperature_k"] = None
    with pytest.raises(ValueError, match="0.9-only key"):
        request_from_payload(payload)


def test_tamper_T1_v08_request_with_injected_capability_is_refused():
    t1 = _load("tamper/T1_request_v08id_injected_capability.json")
    assert t1["schema_version"] == V08_REQUEST_ID and t1["capability_profile"] is not None
    with pytest.raises(ValueError, match=r"0\.9-only key\(s\) \['capability_profile', 'capability_profile_origin'\]"):
        request_from_payload(t1)
    # a single smuggled key (even a null one -- the 0.9.0a1 branch emitted null under the 0.8 id) is enough
    for key, value in (("capability_profile", None), ("capability_profile_origin", "")):
        payload = _load("request_isopentyl_acetate.json")
        payload[key] = value
        with pytest.raises(ValueError, match="0.9-only key"):
            request_from_payload(payload)


def test_legacy_request_object_cannot_carry_a_profile():
    legacy = request_from_payload(_load("request_isopentyl_acetate.json"))
    with pytest.raises(ValueError, match="cannot carry a capability profile"):
        dc.replace(legacy, capability_profile_origin="poor-man")


# -- legacy RESPONSES ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", _RESPONSES)
def test_real_v08_response_loads_as_legacy_with_readiness_preserved(name):
    payload = _load(name)
    resp = response_from_payload(payload)
    # LEGACY, never native (M81)
    assert resp.schema_version == V08_RESPONSE_ID != COMPILATION_RESPONSE_SCHEMA
    assert resp.is_legacy_v08 and resp.request.is_legacy_v08
    # capability NOT_REQUESTED: no question pin, no assessment -- nothing fabricated
    assert resp.capability_question_digest is None
    assert resp.request.capability_profile is None
    assert all(d.capability_assessment is None for d in resp.ranked_route_dossiers)
    assert all(d.schema_version == V08_SUMMARY_ID for d in resp.ranked_route_dossiers)
    # readiness preserved EXACTLY as recorded (full typed ladder, not just the coarse tier)
    recorded = payload["ranked_route_dossiers"]
    assert [d.readiness_tier for d in resp.ranked_route_dossiers] == [d["readiness_tier"] for d in recorded]
    assert [_route_readiness_to_payload(d.readiness) for d in resp.ranked_route_dossiers] == \
           [d["readiness"] for d in recorded]
    # the stored v0.8 result_digest verifies under the frozen v0.8 rule (it was REFUSED before Round V -- F81)
    mode = payload.get("transport_mode", "THIN_ADVISORY")
    assert _transport_bound_result_digest(resp.result_digest, mode) == payload["result_digest"]
    assert resp.outcome.value == payload["outcome"] and resp.exit_code == payload["exit_code"]


@pytest.mark.parametrize("name", _CANONICAL_ROUTE_RESPONSES)
def test_real_v08_canonical_response_passes_verified_admission(name):
    """The CANONICAL_VERIFIED v0.8 wire re-derives every route (bound under the frozen v0.8 route identity) and its
    readiness -- no check is weakened for legacy; the replay genuinely re-derives."""
    resp = response_from_payload(_load(name), require_verified_admission=True)
    assert resp.is_legacy_v08
    assert all(d.replay_payload is not None for d in resp.ranked_route_dossiers)
    for d in resp.ranked_route_dossiers:  # every legacy replay binds to its stored v0.8 route identity
        from smartchem.service import _reconstruct_route
        assert _v08_digest(_reconstruct_route(d.replay_payload)) == d.route_digest


def test_real_v08_procedure_routes_are_actually_exercised():
    """Guard against a vacuous pass: the isopentyl fixture really carries sourced ProcedureEvidence (the routes whose
    replay Lane D saw refused as 'substituted readiness evidence' before the frozen rule)."""
    payload = _load("response_isopentyl_acetate.json")
    with_proc = [d for d in payload["ranked_route_dossiers"]
                 if any(s["envelope"].get("procedure") for s in d["replay_payload"])]
    assert len(with_proc) == 3
    response_from_payload(payload)  # and they load


def test_thin_v08_response_under_verified_admission_fails_closed_with_a_recompile_hint():
    resp_payload = _load("response_ethyl_acetate_smiles_thin.json")
    with pytest.raises(ValueError, match=r"legacy v0\.8 payload .*recompile under 0\.9 \(semantic_digest [0-9a-f]{64}\)"):
        response_from_payload(resp_payload, require_verified_admission=True)


def test_nested_v08_plan_compilation_loads_as_legacy():
    """plan-result-v0.6's OWN shape did not change (its top-level keys are identical to the 0.9 plan payload), so it is
    not bumped; the nested ``compilation`` carries its own versioned response id and migrates like any response."""
    plan = _load("plan_isopentyl_acetate.json")
    assert plan["schema"] == "smartchem.plan/plan-result-v0.6"
    resp = response_from_payload(plan["compilation"])
    assert resp.is_legacy_v08 and resp.capability_question_digest is None


def test_legacy_dossier_migration_does_not_mutate_the_callers_payload():
    payload = _load("response_isopentyl_acetate.json")
    before = json.dumps(payload, sort_keys=True)
    response_from_payload(payload)
    assert json.dumps(payload, sort_keys=True) == before


# -- legacy tamper: nothing is weakened for a v0.8 id --------------------------------------------------------------

def test_tamper_T4b_v08_response_with_injected_profile_and_recomputed_pin_is_refused():
    t4b = _load("tamper/T4b_response_v08id_injected_profile_and_pin.json")
    assert t4b["schema_version"] == V08_RESPONSE_ID and t4b["capability_question_digest"]
    with pytest.raises(ValueError, match="0.9-only key"):
        response_from_payload(t4b)
    with pytest.raises(ValueError, match="0.9-only key"):
        response_from_payload(t4b, require_verified_admission=True)


def _inject(payload: dict, where: str) -> dict:
    p = copy.deepcopy(payload)
    if where == "question":
        p["capability_question_digest"] = None
    elif where == "assessment":
        p["ranked_route_dossiers"][0]["capability_assessment"] = None
    elif where in ("material_uses", "specification"):
        for d in p["ranked_route_dossiers"]:
            for s in d["replay_payload"]:
                proc = s["envelope"].get("procedure")
                if proc:
                    op = proc["operations"][0]
                    op["material_uses"] = [] if where == "material_uses" else [{"specification": None}]
                    return p
    return p


@pytest.mark.parametrize("where", ["question", "assessment", "material_uses", "specification"])
def test_any_0_9_only_key_under_the_v08_response_id_is_refused(where):
    """Even the NULL/empty value is refused: the key's presence is the 0.9 wire (a 0.9.0a1-branch payload that reused
    the v1alpha15 id carried exactly these nulls) -- never reinterpreted as a v0.8 payload."""
    with pytest.raises(ValueError, match="0.9-only key"):
        response_from_payload(_inject(_load("response_isopentyl_acetate.json"), where))


def test_legacy_result_digest_tamper_is_refused_with_a_recompile_hint():
    payload = _load("response_ethyl_acetate_smiles.json")
    payload["result_digest"] = ("0" if payload["result_digest"][0] != "0" else "1") + payload["result_digest"][1:]
    with pytest.raises(ValueError, match=r"result_digest does not match.*legacy v0\.8 payload"):
        response_from_payload(payload)


def test_legacy_substituted_replay_is_refused_under_the_frozen_route_identity():
    """Swap two routes' replay evidence: the frozen-rule binding is still EXACT equality, so the substitution is
    caught (the frozen rule is a different encoding, never a looser check)."""
    payload = _load("response_ethyl_acetate_smiles.json")
    d = payload["ranked_route_dossiers"]
    d[0]["replay_payload"], d[1]["replay_payload"] = d[1]["replay_payload"], d[0]["replay_payload"]
    with pytest.raises(ValueError, match=r"(DIFFERENT route|refused \(D26\.1\)).*legacy v0\.8 payload"):
        response_from_payload(payload)


def test_legacy_readiness_claim_is_still_rederived():
    """Bump a legacy route's claimed tier coherently (ladder + alias) and recompute the v0.8 result_digest the way a
    forger would: the re-derivation from the replay still refuses it."""
    from smartchem.service import (
        CompilationResponse, _route_readiness_from_payload, ranked_summary_from_payload, response_from_payload as rfp,
    )
    payload = _load("response_ethyl_acetate_smiles.json")
    honest = rfp(payload)
    src = next(i for i, d in enumerate(honest.ranked_route_dossiers) if d.readiness_tier == "FORMAL_CANDIDATE")
    donor = next(d for d in payload["ranked_route_dossiers"] if d["readiness_tier"] == "REACTION_VOUCHED")
    forged_dossier = copy.deepcopy(payload["ranked_route_dossiers"][src])
    forged_dossier["readiness"] = copy.deepcopy(donor["readiness"])
    forged_dossier["readiness_tier"] = donor["readiness_tier"]
    _route_readiness_from_payload(forged_dossier["readiness"])  # the forged ladder itself is well-formed
    payload["ranked_route_dossiers"][src] = forged_dossier
    forged = dc.replace(honest, ranked_route_dossiers=tuple(
        ranked_summary_from_payload(d) for d in payload["ranked_route_dossiers"]))
    assert type(forged) is CompilationResponse
    payload["result_digest"] = _transport_bound_result_digest(forged.result_digest, payload["transport_mode"])
    with pytest.raises(ValueError, match="refused"):
        rfp(payload)


def test_legacy_and_current_generations_never_mix():
    legacy = response_from_payload(_load("response_invalid_input_ethyl_acetate_name.json"))
    current_req = build_recompile_request("ethyl acetate")
    with pytest.raises(ValueError, match="cannot embed a request"):
        dc.replace(legacy, request=current_req)
    with pytest.raises(ValueError, match="cannot embed a request"):
        dc.replace(legacy, schema_version=COMPILATION_RESPONSE_SCHEMA)


def test_a_v08_response_relabelled_with_the_current_id_is_not_accepted_as_native():
    """M81: a v0.8 payload can never be accepted as native -- relabelling it to the current id fails the required
    0.9 shape (and would fail the current digest rule besides)."""
    payload = _load("response_isopentyl_acetate.json")
    payload["schema_version"] = COMPILATION_RESPONSE_SCHEMA
    with pytest.raises(ValueError):
        response_from_payload(payload)
    payload["capability_question_digest"] = None
    with pytest.raises(ValueError):
        response_from_payload(payload)


# -- unknown ids are refused precisely -----------------------------------------------------------------------------

# X-high D22: the WIP-only ids pushed on the unreleased branch (request v1alpha6, response v1alpha16) were never
# released, so they are NOT migrated -- refused exactly like any other unknown id.
@pytest.mark.parametrize("bad", ["smartchem.service/compilation-request-v1alpha4",
                                 "smartchem.service/compilation-request-v1alpha6",
                                 "smartchem.service/compilation-request-v1alpha8", "garbage", None])
def test_unknown_request_version_is_refused_precisely(bad):
    payload = _load("request_isopentyl_acetate.json")
    payload["schema_version"] = bad
    with pytest.raises(ValueError, match=rf"unsupported request schema_version {re.escape(repr(bad))} \(supported: "
                                         rf"'{re.escape(COMPILATION_REQUEST_SCHEMA)}'; legacy "
                                         rf"'{re.escape(V08_REQUEST_ID)}'\)"):
        request_from_payload(payload)


@pytest.mark.parametrize("bad", ["smartchem.service/compilation-response-v1alpha12",
                                 "smartchem.service/compilation-response-v1alpha16",
                                 "smartchem.service/compilation-response-v1alpha18", "garbage"])
def test_unknown_response_version_is_refused_precisely(bad):
    payload = _load("response_isopentyl_acetate.json")
    payload["schema_version"] = bad
    with pytest.raises(ValueError, match=rf"unsupported response schema_version {re.escape(repr(bad))} "
                                         rf"\(supported: '{re.escape(COMPILATION_RESPONSE_SCHEMA)}'"):
        response_from_payload(payload)


def test_unknown_ranked_route_summary_version_is_refused_precisely():
    from smartchem.service import ranked_summary_from_payload
    dossier = _load("response_ethyl_acetate_smiles.json")["ranked_route_dossiers"][0]
    dossier["schema_version"] = "smartchem.service/ranked-route-summary-v1alpha2"
    with pytest.raises(ValueError, match="unsupported ranked route summary schema_version"):
        ranked_summary_from_payload(dossier)


# -- the frozen v0.8 rule is NARROW --------------------------------------------------------------------------------

def test_frozen_rule_equals_the_global_rule_on_records_without_0_9_fields():
    resp = response_from_payload(_load("response_ethyl_acetate_smiles.json"))
    readiness = resp.ranked_route_dossiers[0].readiness
    assert _v08_digest(readiness) == canonical_digest(readiness)  # leaf encoding delegated, never re-implemented
    assert _v08_digest(resp.compilation_ir) == resp.compilation_ir.digest


def test_frozen_rule_refuses_0_9_content_rather_than_omitting_it():
    req = build_recompile_request("ethyl acetate", capability_profile="poor-man")
    with pytest.raises(ValueError, match="0.9-only content"):
        _v08_digest(req)


# -- current ids: round-trip, noninterference, rebind --------------------------------------------------------------

_TARGET = "smiles:CC(=O)OC"  # methyl acetate -- the small max_depth=2 search the transport tests share


def test_current_request_and_response_round_trip_under_the_new_ids():
    req = build_recompile_request(_TARGET, max_depth=2, capability_profile="poor-man")
    assert req.schema_version == COMPILATION_REQUEST_SCHEMA and not req.is_legacy_v08
    back_req = request_from_payload(request_to_payload(req))
    assert back_req == req and back_req.digest == req.digest
    resp = run_compilation(req)
    payload = response_to_payload(resp)
    assert payload["schema_version"] == COMPILATION_RESPONSE_SCHEMA
    assert payload["request"]["schema_version"] == COMPILATION_REQUEST_SCHEMA
    assert all(d["schema_version"] == RANKED_ROUTE_SUMMARY_SCHEMA for d in payload["ranked_route_dossiers"])
    back = response_from_payload(payload, require_verified_admission=True)
    assert not back.is_legacy_v08
    assert back.result_digest == resp.result_digest
    assert back.capability_question_digest == resp.capability_question_digest is not None


def test_semantic_digest_is_invariant_across_capability_profiles():
    """Search noninterference under the new request id: no-profile / poor-man / research-lab / custom share ONE
    semantic_digest for the same target; only the capability question pin moves."""
    profiles = [None, "poor-man", "research-lab",
                custom(profile_id="migration-inline", equipment=frozenset({EquipmentCapability.BALANCE}))]
    reqs = [build_recompile_request("isopentyl acetate", capability_profile=p) for p in profiles]
    assert len({r.semantic_digest for r in reqs}) == 1
    pins = [r.capability_question_digest for r in reqs]
    assert pins[0] is None and len(set(pins[1:])) == 3


def test_capability_rebind_on_load_still_refuses_a_mismatched_assessment():
    a = run_compilation(build_recompile_request(_TARGET, max_depth=2, capability_profile="poor-man"))
    b = run_compilation(build_recompile_request(_TARGET, max_depth=2, capability_profile="research-lab"))
    assert a.ranked_route_dossiers, "the methyl-acetate search must surface ranked routes"
    by_route = {d.route_digest: d.capability_assessment for d in b.ranked_route_dossiers}
    doss = list(a.ranked_route_dossiers)
    i = next((k for k, d in enumerate(doss) if by_route.get(d.route_digest) != d.capability_assessment), None)
    assert i is not None, "the two profiles must assess at least one route differently"
    doss[i] = dc.replace(doss[i], capability_assessment=by_route[doss[i].route_digest])
    forged = dc.replace(a, ranked_route_dossiers=tuple(doss))
    payload = response_to_payload(forged)  # the forger recomputes every public digest
    with pytest.raises(ValueError, match="capability_assessment"):
        response_from_payload(payload)


# -- Round V wire: ProcedureMaterialUse.specification survives the replay codec -------------------------------------

def _spec_use():
    from smartchem.material_spec import (
        CompositionConstraint, ConcentrationBasis, DilutionState, EvidenceKind, MaterialSpecification, StateClaim,
        Tolerance,
    )
    from smartchem.procedure_evidence import ProcedureMaterialRole, ProcedureMaterialUse
    spec = MaterialSpecification(
        composition=CompositionConstraint("0.05", "0.05", ConcentrationBasis.UNKNOWN,
                                          Tolerance.NOMINAL_UNSTATED_TOLERANCE, EvidenceKind.SOURCE_QUOTED),
        states=(StateClaim(DilutionState.SOLUTION, EvidenceKind.SOURCE_QUOTED),),
        unresolved_terms=("5%",),
    )
    return ProcedureMaterialUse("sodium bicarbonate", ProcedureMaterialRole.WASH, formulation="5% solution",
                                evidence_source="codec-test locator", specification=spec)


def test_material_use_specification_round_trips_exactly():
    from smartchem.service import _procedure_material_use_from_payload, _procedure_material_use_to_payload
    use = _spec_use()
    payload = json.loads(json.dumps(_procedure_material_use_to_payload(use)))  # through real JSON
    back = _procedure_material_use_from_payload(payload)
    assert back == use and back.digest == use.digest and back.specification == use.specification
    none_payload = _procedure_material_use_to_payload(dc.replace(use, specification=None))
    assert none_payload["specification"] is None
    assert _procedure_material_use_from_payload(none_payload).specification is None


def test_material_use_specification_decoder_is_a_closed_whitelist():
    """A spec payload naming ANY non-material_spec class (here a stock record) is refused -- the generic canonical
    decoder is never an open door."""
    from smartchem.service import _procedure_material_use_from_payload, _procedure_material_use_to_payload
    payload = json.loads(json.dumps(_procedure_material_use_to_payload(_spec_use())))
    payload["specification"]["class"] = "smartchem.experiment.stock.StockQuantity"
    with pytest.raises(ValueError, match="not in the closed"):
        _procedure_material_use_from_payload(payload)
    payload = json.loads(json.dumps(_procedure_material_use_to_payload(_spec_use())))
    del payload["specification"]
    with pytest.raises(ValueError, match="exactly the versioned fields"):
        _procedure_material_use_from_payload(payload)


# -- Wave-C2 (smith) closes ------------------------------------------------------------------------------------------

def _forger_refresh(payload: dict) -> dict:
    """What a keyless forger does after editing a payload: rebuild the response through the PUBLIC decoders and
    recompute every derived public field (result_digest, admissible list, status, exit code, question pin)."""
    from smartchem.service import (
        CompilationResponse, ResponseOutcome, affordability_entry_from_payload, ir_from_payload,
        provider_snapshot_from_payload, ranked_dag_summary_from_payload, ranked_summary_from_payload,
    )
    ir = payload["compilation_ir"]
    resp = CompilationResponse(
        payload["schema_version"], request_from_payload(payload["request"]), ResponseOutcome(payload["outcome"]),
        payload["standard_status"], None if ir is None else ir_from_payload(ir), tuple(payload["diagnostics"]),
        tuple(ranked_summary_from_payload(r) for r in payload["ranked_route_dossiers"]),
        tuple(affordability_entry_from_payload(e) for e in payload["affordability_frontier"]),
        tuple(provider_snapshot_from_payload(s) for s in payload["provider_snapshots"]),
        parse_receipt_summary=payload["parse_receipt_summary"],
        ranked_dag_dossiers=tuple(ranked_dag_summary_from_payload(d) for d in payload["ranked_dag_dossiers"]))
    payload["result_digest"] = _transport_bound_result_digest(resp.result_digest, payload["transport_mode"])
    payload["admissible_route_digests"] = list(resp.admissible_route_digests)
    payload["process_selection_status"] = resp.process_selection_status
    payload["exit_code"] = resp.exit_code
    payload["capability_question_digest"] = resp.capability_question_digest
    return payload


def _set(node: dict, name: str, value: dict) -> None:
    for f in node["fields"]:
        if f[0] == name:
            f[1] = value
            return
    raise KeyError(name)


@pytest.fixture(scope="module")
def _thin_poor_man():
    resp = run_compilation(build_recompile_request(_TARGET, max_depth=2, capability_profile="poor-man"))
    assert resp.ranked_route_dossiers and all(d.capability_assessment for d in resp.ranked_route_dossiers)
    return resp, response_to_payload(resp, include_replay=False)


def test_honest_thin_assessed_payload_still_loads(_thin_poor_man):
    resp, thin = _thin_poor_man
    back = response_from_payload(copy.deepcopy(thin))
    assert [d.capability_assessment for d in back.ranked_route_dossiers] == \
           [d.capability_assessment for d in resp.ranked_route_dossiers]


def test_smith_P0_thin_wire_forged_capability_fit_is_refused(_thin_poor_man):
    """The exact Wave-C2 forgery: overall FIT over BLOCKED/UNKNOWN axes + PROCESS_SPECIFIED tier on a lower dossier +
    profile_digest 0*64 + route_digest f*64, on a replay-free THIN wire.  It loaded on a plain load before; now the
    HARD-LAW fold refuses it at decode, naming the dossier."""
    _, thin = _thin_poor_man
    p = copy.deepcopy(thin)
    a = p["ranked_route_dossiers"][0]["capability_assessment"]
    _set(a, "overall", {"type": "enum", "class": "smartchem.capability.enums.CapabilityStatus",
                        "value": {"type": "str", "value": "FIT"}})
    _set(a, "overall_reasons", {"type": "tuple", "items": [{"type": "str", "value": "forged"}]})
    _set(a, "readiness_tier", {"type": "str", "value": "PROCESS_SPECIFIED"})
    _set(a, "profile_digest", {"type": "str", "value": "0" * 64})
    _set(a, "route_digest", {"type": "str", "value": "f" * 64})
    with pytest.raises(ValueError, match="capability_assessment"):
        response_from_payload(p)


@pytest.mark.parametrize("field,value,match", [
    ("readiness_tier", "PROCESS_SPECIFIED", "readiness"),
    ("readiness_digest", "a" * 64, "readiness"),
    ("profile_digest", "0" * 64, "profile_digest"),
    ("route_digest", "f" * 64, "different route"),
])
def test_each_replay_free_binding_is_checked_on_a_thin_plain_load(_thin_poor_man, field, value, match):
    """Each binding alone, with the forger recomputing every public digest: still refused on a PLAIN load of a THIN
    wire (no replay, no verified admission, no key)."""
    _, thin = _thin_poor_man
    p = copy.deepcopy(thin)
    assert p["ranked_route_dossiers"][0]["readiness_tier"] != "PROCESS_SPECIFIED"  # the tier forgery is a real lie
    a = p["ranked_route_dossiers"][0]["capability_assessment"]
    _set(a, field, {"type": "str", "value": value})
    _forger_refresh(p)  # the record itself is self-consistent (its axes are BLOCKED, so the fold is tier-blind)
    with pytest.raises(ValueError, match=match):
        response_from_payload(p)


def test_capability_fit_is_refused_on_a_thin_wire_but_the_gate_is_discriminating(_thin_poor_man):
    """No corpus route reaches CAPABILITY_FIT (the honest Round IV/V ceiling), so the thin-wire FIT gate is exercised
    on a self-consistent FIT record bound to a PROCESS_SPECIFIED dossier stand-in: refused with the thin flag,
    admitted without it (a discriminating control, not a blanket refusal)."""
    from types import SimpleNamespace

    from smartchem.capability import AxisResult, CapabilityStatus
    resp, _ = _thin_poor_man
    real = resp.ranked_route_dossiers[0]
    fit_axis = AxisResult(CapabilityStatus.FIT, ("stand-in",))
    fit = dc.replace(real.capability_assessment, **{n: fit_axis for n in (
        "material", "equipment", "physical", "process", "containment", "ventilation", "measurement", "waste",
        "procurement", "attention_care", "monetary")}, readiness_tier="PROCESS_SPECIFIED",
        overall=CapabilityStatus.FIT, overall_reasons=("stand-in",))
    assert fit.is_capability_fit
    dossier = SimpleNamespace(capability_assessment=fit, route_digest=fit.route_digest,
                              readiness=SimpleNamespace(tier="PROCESS_SPECIFIED", digest=fit.readiness_digest))
    profile = resp.request.capability_profile
    with pytest.raises(ValueError, match="CAPABILITY_FIT on a THIN_ADVISORY"):
        resp._check_assessment_bindings(dossier, profile, refuse_fit_on_thin=True)
    resp._check_assessment_bindings(dossier, profile, refuse_fit_on_thin=False)  # canonical wire: re-derived instead


def test_smith_P2_real_v08_name_the_resolver_now_registers_fails_closed_with_the_legacy_hint():
    """REAL v0.8 fixtures for "sulfuric acid": v0.8 did not register the name (normalized_identity ""); today's
    resolver does.  Still refused (the stored search identity no longer names 0.9's search) -- but precisely."""
    req = _load("request_sulfuric_acid_name.json")
    assert req["schema_version"] == V08_REQUEST_ID and req["normalized_identity"] == ""
    pattern = (r"legacy v0\.8 payload; the name resolver changed since v0\.8 \(stored normalized_identity '' vs "
               r"today's '.+'\); recompile under 0\.9")
    with pytest.raises(ValueError, match=pattern) as exc:
        request_from_payload(req)
    assert "forged" not in str(exc.value)
    resp = _load("response_sulfuric_acid_name.json")
    assert resp["schema_version"] == V08_RESPONSE_ID and resp["outcome"] == "INVALID_INPUT"
    with pytest.raises(ValueError, match=pattern):
        response_from_payload(resp)


def test_current_request_normalized_identity_forgery_keeps_its_original_refusal():
    payload = request_to_payload(build_recompile_request("isopentyl acetate"))
    payload["normalized_identity"] = "forged"
    with pytest.raises(ValueError, match="forged or stale search identity"):
        request_from_payload(payload)


@pytest.mark.parametrize("label", ["INVALID_INPUT", "REFUSED"])
def test_smith_P2_signature_binds_the_capability_question_with_zero_dossiers(label):
    from smartchem.service import InputKind, TransformGrammar, _capability_profile_to_payload
    from smartchem.capability import resolve_capability_profile
    key = b"producer-key"
    req = (build_recompile_request("ethyl acetate", capability_profile="poor-man") if label == "INVALID_INPUT" else
           build_recompile_request("CCOC(C)=O", input_kind=InputKind.SMILES, capability_profile="poor-man",
                                   grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT))
    resp = run_compilation(req)
    assert resp.outcome.value == label and not resp.ranked_route_dossiers
    signed = response_to_payload(resp, signing_key=key)
    # honest signed load
    response_from_payload(copy.deepcopy(signed), verification_key=key, require_signature=True,
                          expected_request_digest=req.semantic_digest)
    # the question is IN the result identity: same search, no profile -> a different result_digest
    plain = run_compilation(dc.replace(req, capability_profile=None, capability_profile_origin=""))
    assert plain.result_digest != resp.result_digest
    for newprof, origin in ((_capability_profile_to_payload(resolve_capability_profile("research-lab")),
                             "research-lab"), (None, "")):
        forged = copy.deepcopy(signed)
        forged["request"]["capability_profile"], forged["request"]["capability_profile_origin"] = newprof, origin
        _forger_refresh(forged)  # keyless forger recomputes every public digest; the signature cannot follow
        with pytest.raises(ValueError, match="producer_signature does not verify"):
            response_from_payload(forged, verification_key=key, require_signature=True,
                                  expected_request_digest=req.semantic_digest)


def test_smith_P3_legacy_request_refuses_a_0_9_key_at_any_depth():
    payload = _load("request_isopentyl_acetate.json")
    payload["constraints"]["process"]["material_uses"] = []
    with pytest.raises(ValueError, match=r"0\.9-only key\(s\) \['material_uses'\]"):
        request_from_payload(payload)


@pytest.mark.parametrize("bad", [[], "x", 3, None])
def test_smith_P3_non_object_payloads_raise_value_error(bad):
    with pytest.raises(ValueError, match="must be a JSON object"):
        response_from_payload(bad)
    with pytest.raises(ValueError, match="must be a JSON object"):
        request_from_payload(bad)
