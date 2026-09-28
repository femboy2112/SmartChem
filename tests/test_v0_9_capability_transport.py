"""v0.9 Capability Compiler ROUND III -- the service/transport wiring (D10-D12a).

**Space Beth flew the risky sortie: capability rides the request, the response, and the wire -- and the chemistry
search NEVER feels it.** These are the release-critical proofs the freeze demands:

* SEARCH NONINTERFERENCE (criteria 1/2/36, the release-blocker): the SAME recompile request under {no profile,
  research-lab, poor-man, an inline custom} runs the BYTE-IDENTICAL search -- same normalized target, same candidate
  route digests, same receipt, same transform-registry/algebra digest, same completeness, same ``semantic_digest``.
  ONLY the full request ``.digest``, the ``capability_question_digest``, the per-route ``capability_assessment``, and
  ``result_digest`` may move.  A profile that moved any search-identity field would be release-blocking.
* Canonical transport: a request+response round-trips with a resolved preset AND an inline custom (ONE wire shape).
* CAPABILITY-REBIND-ON-LOAD accepts an untampered load and REFUSES each tamper (altered assessment / altered profile
  snapshot / profile-A-under-B / assessment-on-NOT_REQUESTED).  Thin mode never claims a verified FIT.
* Old-payload safety: a pre-Round-III request (no capability_profile) loads as NOT_REQUESTED.
* Human == JSON: the rendered CAPABILITY block matches the JSON ``capability_assessment`` overall + axis verdicts.
"""
from __future__ import annotations

import dataclasses as dc

import pytest

from smartchem.capability import CapabilityStatus
from smartchem.capability.enums import EquipmentCapability
from smartchem.capability.presets import custom, isopentyl_capability_fit_bench, poor_man
from smartchem.cli import _render_recompile_response
from smartchem.service import (
    _CAPABILITY_AXIS_NAMES,
    build_recompile_request,
    request_from_payload,
    request_to_payload,
    response_from_payload,
    response_to_payload,
    run_compilation,
    serialize_response,
)

_TARGET = "smiles:CC(=O)OC"  # methyl acetate -- a small, fast max_depth=2 search shared across every profile

_PROFILES = {
    "none": None,
    "research-lab": "research-lab",
    "poor-man": "poor-man",
    "custom": custom(profile_id="test-inline-bench", equipment=frozenset({EquipmentCapability.BALANCE})),
}


def _run(profile):
    req = build_recompile_request(_TARGET, capability_profile=profile, max_depth=2)
    return req, run_compilation(req)


# -- SEARCH NONINTERFERENCE (the release-blocker) --------------------------------------------------------------

def test_profile_selection_never_moves_the_search_identity():
    runs = {name: _run(prof) for name, prof in _PROFILES.items()}
    base_req, base_resp = runs["none"]
    base_ir = base_resp.compilation_ir
    assert base_ir is not None

    def candidate_digests(resp):
        return tuple(c.candidate_digest for c in resp.compilation_ir.candidates)

    for name, (req, resp) in runs.items():
        ir = resp.compilation_ir
        # Every search-identity field is BYTE-IDENTICAL to the no-profile run.
        assert req.semantic_digest == base_req.semantic_digest, f"{name}: semantic_digest MOVED (release-blocker)"
        assert req.normalized_identity == base_req.normalized_identity, name
        assert candidate_digests(resp) == candidate_digests(base_resp), f"{name}: candidate route digests moved"
        assert ir.search_receipt.digest == base_ir.search_receipt.digest, f"{name}: search receipt moved"
        assert ir.transform_registry_digest == base_ir.transform_registry_digest, f"{name}: algebra digest moved"
        assert resp.search_space_status == base_resp.search_space_status, f"{name}: search completeness moved"

    # And the ONLY things that legitimately move under a profile are the four allowed ones.
    for name in ("research-lab", "poor-man", "custom"):
        req, resp = runs[name]
        assert req.digest != base_req.digest, f"{name}: full request digest should move (new field)"
        assert req.capability_question_digest is not None, name
        assert base_req.capability_question_digest is None
        assert resp.result_digest != base_resp.result_digest, f"{name}: result_digest should move (assessment folds in)"
        # per-route capability_assessment present under a profile, absent (None) with no profile
        assert all(d.capability_assessment is not None for d in resp.ranked_route_dossiers), name
    assert all(d.capability_assessment is None for d in base_resp.ranked_route_dossiers)


def test_capability_question_digest_moves_on_profile_change_but_not_on_search_change():
    r_poor = build_recompile_request(_TARGET, capability_profile="poor-man", max_depth=2)
    r_lab = build_recompile_request(_TARGET, capability_profile="research-lab", max_depth=2)
    # different profile content -> different pin, SAME search identity
    assert r_poor.capability_question_digest != r_lab.capability_question_digest
    assert r_poor.semantic_digest == r_lab.semantic_digest
    # same profile, a search-question change (depth) -> semantic_digest moves, and so does the pin (it folds it in),
    # but the pin change is DRIVEN by the search side, never the reverse: the search digest itself is profile-blind.
    r_poor_deep = build_recompile_request(_TARGET, capability_profile="poor-man", max_depth=3)
    assert r_poor_deep.semantic_digest != r_poor.semantic_digest
    # the no-profile search digest for the two depths is what the pin's search-leg tracks
    assert build_recompile_request(_TARGET, max_depth=2).semantic_digest == r_poor.semantic_digest


# -- canonical transport (preset AND inline custom -- ONE wire shape) ------------------------------------------

@pytest.mark.parametrize("profile", ["poor-man", "research-lab",
                                      custom(profile_id="wire-custom", equipment=frozenset({EquipmentCapability.BALANCE}))])
def test_request_and_response_round_trip_with_a_resolved_profile(profile):
    req, resp = _run(profile)
    # request round-trip: the resolved snapshot survives EXACTLY (never re-resolved)
    back_req = request_from_payload(request_to_payload(req))
    assert back_req.digest == req.digest
    assert back_req.capability_profile == req.capability_profile
    # response round-trip through the canonical wire (CAPABILITY-REBIND-ON-LOAD accepts it)
    back = response_from_payload(response_to_payload(resp))
    assert back.result_digest == resp.result_digest
    assert back.capability_question_digest == resp.capability_question_digest


def test_old_payload_without_capability_loads_as_not_requested():
    req = build_recompile_request("aspirin")
    payload = request_to_payload(req)
    del payload["capability_profile"]
    del payload["capability_profile_origin"]
    back = request_from_payload(payload)
    assert back.capability_profile is None
    assert back.capability_profile_origin == ""
    assert back.semantic_digest == req.semantic_digest  # search identity untouched


# -- CAPABILITY-REBIND-ON-LOAD: accept the honest load, refuse every tamper ------------------------------------

def _fit_response():
    """The real, procedure-backed isopentyl route surfaced through the SERVICE under the fully-declared fit bench --
    a genuine CAPABILITY_FIT on the shipping path."""
    req = build_recompile_request(
        "isopentyl acetate", capability_profile=isopentyl_capability_fit_bench(),
        helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",),
    )
    return run_compilation(req)


def test_rebind_accepts_untampered_and_a_real_fit_survives_the_wire():
    resp = _fit_response()
    fit = [d for d in resp.ranked_route_dossiers
           if d.capability_assessment and d.capability_assessment.overall is CapabilityStatus.FIT]
    assert fit, "expected a genuine CAPABILITY_FIT route on the real service path"
    back = response_from_payload(response_to_payload(resp))  # canonical wire runs the rebind fail-closed
    assert back.result_digest == resp.result_digest
    assert [d for d in back.ranked_route_dossiers
            if d.capability_assessment and d.capability_assessment.overall is CapabilityStatus.FIT]


def test_rebind_refuses_an_altered_carried_assessment_verdict():
    resp = _fit_response()
    doss = list(resp.ranked_route_dossiers)
    i = next(k for k, d in enumerate(doss) if d.capability_assessment)
    forged = dc.replace(doss[i].capability_assessment, overall=CapabilityStatus.FIT, overall_reasons=("forged",))
    doss[i] = dc.replace(doss[i], capability_assessment=forged)
    with pytest.raises(ValueError):
        dc.replace(resp, ranked_route_dossiers=tuple(doss))._check_capability_coherence(require_verified_admission=True)


def test_rebind_refuses_profile_a_assessment_under_profile_b():
    resp = _fit_response()
    swapped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=poor_man()))
    with pytest.raises(ValueError):
        swapped._check_capability_coherence(require_verified_admission=True)


def test_rebind_refuses_an_assessment_on_a_not_requested_request():
    resp = _fit_response()
    stripped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=None, capability_profile_origin=""))
    with pytest.raises(ValueError):
        stripped._check_capability_coherence(require_verified_admission=True)


def test_rebind_refuses_an_altered_profile_snapshot_on_the_wire():
    resp = _fit_response()
    payload = response_to_payload(resp)
    # strip the declared stock from the request's profile snapshot -- the carried FIT no longer re-derives.
    cp = payload["request"]["capability_profile"]
    for f in cp["fields"]:
        if f[0] == "material_inventory":
            f[1]["items"] = []
    with pytest.raises(ValueError):
        response_from_payload(payload)


def test_thin_wire_does_not_deliver_a_verified_fit():
    resp = _fit_response()
    thin = serialize_response(resp, include_replay=False)  # THIN_ADVISORY
    # a FIT needs PROCESS_SPECIFIED, which is inadmissible on an unsigned thin wire (readiness Lane-F) -> refused.
    with pytest.raises(ValueError):
        response_from_payload(__import__("json").loads(thin))


# -- human == JSON (criterion 29) ------------------------------------------------------------------------------

def test_rendered_capability_block_matches_the_json_assessment():
    req, resp = _run("poor-man")
    human = _render_recompile_response(resp, quiet=False)
    payload = response_to_payload(resp)
    jd = payload["ranked_route_dossiers"][0]["capability_assessment"]

    def field(dcp, name):
        for n, v in dcp["fields"]:
            if n == name:
                return v
        raise KeyError(name)

    overall = field(jd, "overall")["value"]["value"]
    assert f"CAPABILITY[poor-man]: {overall}" in human
    for ax_name in _CAPABILITY_AXIS_NAMES:
        status = field(field(jd, ax_name), "status")["value"]["value"]
        assert f"{ax_name}: {status}" in human, f"human/JSON axis mismatch on {ax_name}"
    assert "It is not a safety certification." in human


def test_no_profile_renders_no_capability_block():
    _, resp = _run(None)
    assert "CAPABILITY[" not in _render_recompile_response(resp, quiet=False)
