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
import functools
import json

import pytest

from smartchem.capability import CapabilityStatus
from smartchem.capability.enums import EquipmentCapability
from smartchem.capability.presets import custom, isopentyl_capability_fit_bench, poor_man
from smartchem.cli import _render_recompile_response
from smartchem.experiment.readiness import PROCESS_SPECIFIED
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


def test_current_request_payload_with_stripped_capability_keys_is_refused():
    """Round V (D11) supersedes the Round-IV F54 "additive-optional" read: on the CURRENT request id the capability
    keys are part of the versioned shape, so a stripped key is a malformed current payload -- REFUSED, never silently
    defaulted.  A genuine v0.8 request (legacy id, keys absent) is migrated instead -- pinned against real main@df1b38d
    fixtures in tests/test_v0_9_round_v_schema_migration.py."""
    req = build_recompile_request("aspirin")
    for key in ("capability_profile", "capability_profile_origin"):
        payload = request_to_payload(req)
        del payload[key]
        with pytest.raises(ValueError, match="must carry"):
            request_from_payload(payload)


# -- CAPABILITY-REBIND-ON-LOAD: accept the honest load, refuse every tamper ------------------------------------

@functools.lru_cache(maxsize=1)
def _fit_response():
    """The real, procedure-backed isopentyl route surfaced through the SERVICE under the fully-declared bench.
    (Cached: the response is an immutable value, and every consumer below derives its tamper by ``dc.replace``.)

    Round IV: no route reaches CAPABILITY_FIT any more (F56/F47/F49 retired the Round-III positive), so this
    is a PROCESS_SPECIFIED route carried at its honest ceiling -- overall UNKNOWN, never a fabricated FIT.
    The helper name is kept (its five tamper/thin-wire consumers only need a PROCESS_SPECIFIED assessment as
    a vehicle, never an overall FIT), but the shipping path no longer delivers a verified FIT."""
    req = build_recompile_request(
        "isopentyl acetate", capability_profile=isopentyl_capability_fit_bench(),
        helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",),
    )
    return run_compilation(req)


def test_rebind_accepts_untampered_and_the_real_verdict_survives_the_wire():
    """Round IV: no route reaches CAPABILITY_FIT (the whole-path semantic hardening -- F56 process, F47
    containment, F49 waste -- retired the Round-III positive), so the rebind's job is proven on the honest
    verdicts it DOES carry: PROCESS_SPECIFIED isopentyl routes assessed to overall UNKNOWN/BLOCKED, never a
    fabricated FIT. The untampered assessments must survive the canonical wire round-trip byte-for-byte
    (result_digest stable, every per-route overall verdict preserved in order), and CAPABILITY-REBIND-ON-LOAD
    must ACCEPT the load -- an honest, self-consistent verdict is not a tamper."""
    resp = _fit_response()
    assessed = [d for d in resp.ranked_route_dossiers if d.capability_assessment is not None]
    assert assessed, "expected the real service path to carry capability assessments"
    # the honest ceiling: assessed PROCESS_SPECIFIED routes, but NO overall FIT survives to the wire.
    assert all(d.capability_assessment.overall is not CapabilityStatus.FIT for d in assessed)
    assert any(d.capability_assessment.overall is CapabilityStatus.UNKNOWN for d in assessed)
    back = response_from_payload(response_to_payload(resp))  # canonical wire runs the rebind fail-closed
    assert back.result_digest == resp.result_digest
    back_assessed = [d for d in back.ranked_route_dossiers if d.capability_assessment is not None]
    assert [d.capability_assessment.overall for d in back_assessed] == \
           [d.capability_assessment.overall for d in assessed]


def test_rebind_refuses_an_altered_carried_assessment_verdict():
    resp = _fit_response()
    doss = list(resp.ranked_route_dossiers)
    i = next(k for k, d in enumerate(doss) if d.capability_assessment)
    real = doss[i].capability_assessment
    # Round V Wave C2: a SELF-CONTRADICTORY verdict (overall FIT over non-FIT axes) can no longer even be built --
    # CapabilityAssessment.__post_init__ refuses any overall that is not the fold of its axes.
    with pytest.raises(ValueError, match="fold of its axes"):
        dc.replace(real, overall=CapabilityStatus.FIT, overall_reasons=("forged",))
    # ...so the rebind is exercised with a SELF-CONSISTENT forgery: the axes/overall fold correctly, but a carried
    # reason no longer matches what the producer's own re-derivation yields.
    forged = dc.replace(real, overall_reasons=("forged",))
    doss[i] = dc.replace(doss[i], capability_assessment=forged)
    with pytest.raises(ValueError):
        dc.replace(resp, ranked_route_dossiers=tuple(doss))._check_capability_coherence(require_verified_admission=True)


def test_rebind_refuses_profile_a_assessment_under_profile_b():
    resp = _fit_response()
    # (X-high D20(g): the display origin is content-bound, so a coherent swap relabels it with the new snapshot's id.)
    pm = poor_man()
    swapped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=pm,
                                                  capability_profile_origin=pm.profile_id))
    with pytest.raises(ValueError):
        swapped._check_capability_coherence(require_verified_admission=True)


def test_rebind_refuses_an_assessment_on_a_not_requested_request():
    resp = _fit_response()
    stripped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=None, capability_profile_origin=""))
    with pytest.raises(ValueError):
        stripped._check_capability_coherence(require_verified_admission=True)


def _stock_stripped_attack(resp):
    """The KEYLESS public-hash attacker (X-high D20, Wave-A' A-SURV/A-WIRE): strip the declared stock from the request's
    profile snapshot, re-bind EVERY carried assessment's public ``profile_digest`` to the tampered snapshot, and
    re-serialize through the public codec -- which recomputes ``capability_question_digest`` and ``result_digest``.
    Every unkeyed pin now agrees with the tampered content; only the stale ASSESSMENTS (their material reasons still
    name the stripped bottles) are left for a semantic re-derivation to catch."""
    tampered = dc.replace(resp.request.capability_profile, material_inventory=())
    dossiers = tuple(
        dc.replace(d, capability_assessment=dc.replace(d.capability_assessment, profile_digest=tampered.profile_digest))
        if d.capability_assessment is not None else d
        for d in resp.ranked_route_dossiers
    )
    return dc.replace(resp, request=dc.replace(resp.request, capability_profile=tampered),
                      ranked_route_dossiers=dossiers)


def test_rebind_refuses_an_altered_profile_snapshot_on_the_wire():
    """Wave-A' A-WIRE P2: the old version of this test passed for the WRONG reason -- stripping the stock without
    recomputing any pin was caught by the PUBLIC ``result_digest`` (a hash a keyless attacker recomputes for free), never
    by the rebind.  Both layers are now pinned separately, each by its OWN refusal message."""
    resp = _fit_response()
    # (1) the naive attacker (content edited, pins stale) -> the public result_digest layer.
    naive = response_to_payload(resp)
    for f in naive["request"]["capability_profile"]["fields"]:
        if f[0] == "material_inventory":
            f[1]["items"] = []
    with pytest.raises(ValueError, match="capability_question_digest does not match|result_digest does not match"):
        response_from_payload(naive)
    # (2) the full keyless attacker (every public pin recomputed) -> ONLY the rebind re-derivation can refuse it.
    forged = _stock_stripped_attack(resp)
    payload = response_to_payload(forged)
    assert payload["capability_question_digest"] == forged.request.capability_question_digest  # pins are coherent
    with pytest.raises(ValueError, match="replayed evidence does not support"):
        response_from_payload(payload)


# -- the replay-free bindings, each ISOLATED on a THIN wire with every public pin recomputed (X-high D20) ----------
#
# D24.14 made dossier DELETION unrepresentable (the ranked set must equal the IR route-candidate set), so the vehicle is
# no longer "the isopentyl response with its PROCESS_SPECIFIED dossiers dropped": it is a response whose dossiers are
# ALL below PROCESS_SPECIFIED to begin with (methyl acetate under poor-man: REACTION_VOUCHED + FORMAL_CANDIDATE), so
# the 0.8 thin-PS law never fires and the binding under test is the ONLY guard standing.


@functools.lru_cache(maxsize=1)
def _thin_vehicle():
    resp = _run("poor-man")[1]
    assert resp.ranked_route_dossiers and all(
        d.readiness.tier != PROCESS_SPECIFIED and d.capability_assessment is not None
        for d in resp.ranked_route_dossiers)
    return resp


def _thin(resp):
    """Serialize THIN through the public codec (every unkeyed pin recomputed)."""
    return response_to_payload(resp, include_replay=False)


def test_thin_vehicle_control_loads_when_no_binding_is_violated():
    """The discriminating control: the SAME thin vehicle with no tamper loads -- so each refusal below is its binding's,
    not the vehicle's."""
    vehicle = _thin_vehicle()
    back = response_from_payload(_thin(vehicle))
    assert back.result_digest == vehicle.result_digest


def test_profile_digest_binding_refuses_a_stale_assessment_on_a_thin_wire():
    """M38b: the request's profile snapshot is altered but the carried assessments keep the OLD profile_digest; with no
    replay there is no rebind -- the profile binding alone refuses."""
    resp = _thin_vehicle()
    tampered = dc.replace(resp.request.capability_profile, provenance="tampered bench declaration")
    swapped = dc.replace(resp, request=dc.replace(resp.request, capability_profile=tampered))
    with pytest.raises(ValueError, match="assessment under a different bench"):
        response_from_payload(_thin(swapped))


def test_route_digest_binding_refuses_a_transplanted_assessment_on_a_thin_wire():
    resp = _thin_vehicle()
    doss = list(resp.ranked_route_dossiers)
    assert len(doss) >= 2
    a0 = doss[0].capability_assessment
    doss[0] = dc.replace(doss[0], capability_assessment=dc.replace(a0, route_digest=doss[1].route_digest))
    with pytest.raises(ValueError, match="assessment of a different route"):
        response_from_payload(_thin(dc.replace(resp, ranked_route_dossiers=tuple(doss))))


def test_readiness_binding_refuses_a_relabelled_tier_on_a_thin_wire():
    """M104b: a sub-PROCESS_SPECIFIED dossier's (non-FIT) assessment relabelled as computed under PROCESS_SPECIFIED --
    fold-consistent (a non-FIT axis keeps the overall non-FIT under any tier), public pins recomputed.  Only the
    readiness binding stands (the premise the M104 thin-FIT redundancy proof rests on)."""
    resp = _thin_vehicle()
    doss = list(resp.ranked_route_dossiers)
    a0 = doss[0].capability_assessment
    doss[0] = dc.replace(doss[0], capability_assessment=dc.replace(
        a0, readiness_tier=PROCESS_SPECIFIED, readiness_digest=doss[1].readiness.digest))
    with pytest.raises(ValueError, match="tier/readiness_digest mismatch"):
        response_from_payload(_thin(dc.replace(resp, ranked_route_dossiers=tuple(doss))))


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
    # D24.12: the label carries the CONTENT identity (the profile digest) beside the free-text origin.
    pdig = field(jd, "profile_digest")["value"]
    assert f"CAPABILITY[poor-man@{pdig[:12]}]: {overall}" in human
    for ax_name in _CAPABILITY_AXIS_NAMES:
        status = field(field(jd, ax_name), "status")["value"]["value"]
        assert f"{ax_name}: {status}" in human, f"human/JSON axis mismatch on {ax_name}"
    assert "It is not a safety certification." in human


def test_no_profile_renders_no_capability_block():
    _, resp = _run(None)
    assert "CAPABILITY[" not in _render_recompile_response(resp, quiet=False)


# -- RC Round IV Wave B: F51/F52/F54 -----------------------------------------------------------------------------

def test_capability_profile_with_convergent_dag_grammar_is_a_typed_refusal():
    """F51: RankedDAGSummary carries no capability field, so a capability question run under the convergent-DAG
    grammar had NO way to be honestly answered -- and, before this fix, got no answer AND no diagnostic (a silent
    drop). It must now come back as a typed REFUSED response naming the unsupported (capability, topology)
    combination, never a quiet nothing."""
    from smartchem.service import ProcessBounds, ResponseOutcome, TransformGrammar

    resp = run_compilation(build_recompile_request(
        "smiles:COCCC", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        capability_profile="poor-man", process=ProcessBounds(max_total_minutes=600.0), max_depth=3,
    ))
    assert resp.outcome is ResponseOutcome.REFUSED
    assert resp.exit_code == 5
    assert resp.compilation_ir is None
    assert resp.ranked_dag_dossiers == ()
    assert any("CAPPED_SCISSION_CONVERGENT" in d and "capability" in d for d in resp.diagnostics)


def test_convergent_dag_search_is_unaffected_without_a_capability_profile():
    """F51 guard rail: the fix must gate on the (profile, convergent) COMBINATION only -- a profile-less convergent
    DAG search must keep running exactly as before (not a regression)."""
    from smartchem.service import ProcessBounds, ResponseOutcome, TransformGrammar

    resp = run_compilation(build_recompile_request(
        "smiles:COCCC", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=ProcessBounds(max_total_minutes=600.0), max_depth=3,
    ))
    assert resp.outcome is not ResponseOutcome.REFUSED
    assert len(resp.ranked_dag_dossiers) >= 2


def test_compile_and_recompile_agree_human_and_json_under_a_capability_profile(capsys):
    """F52 PIN: `compile` (deprecated alias) and `recompile`, human AND --json, under the SAME capability profile,
    must emit the same request, the same exit code, and the same overall + per-axis capability verdict -- the human
    render is no longer a second, capability-blind renderer (compile_synthesis is retired)."""
    import json as _json

    from smartchem.cli import main

    tail = [
        "isopentyl acetate", "--capability-profile", "poor-man",
        "--reagents", "water", "acetic acid", "--have", "isopentyl alcohol", "--max-depth", "2",
    ]

    compile_emit_code = main(["compile", *tail, "--emit-request"])
    compile_emit = capsys.readouterr().out
    recompile_emit_code = main(["recompile", *tail, "--emit-request"])
    recompile_emit = capsys.readouterr().out
    assert compile_emit_code == recompile_emit_code == 0
    assert _json.loads(compile_emit) == _json.loads(recompile_emit)  # same typed request, capability profile included

    compile_json_code = main(["compile", *tail, "--json"])
    compile_json_out = capsys.readouterr().out
    recompile_json_code = main(["recompile", *tail, "--json"])
    recompile_json_out = capsys.readouterr().out
    assert compile_json_code == recompile_json_code
    compile_payload = _json.loads(compile_json_out)
    recompile_payload = _json.loads(recompile_json_out)
    assert compile_payload == recompile_payload  # byte-identical typed response

    compile_human_code = main(["compile", *tail])
    compile_human_out = capsys.readouterr().out
    recompile_human_code = main(["recompile", *tail])
    recompile_human_out = capsys.readouterr().out
    assert compile_human_code == recompile_human_code == compile_payload["exit_code"]
    # compile's human stdout carries NO deprecation text (it rides stderr) and is otherwise the SAME render.
    assert compile_human_out == recompile_human_out
    assert "deprecated" not in compile_human_out.lower()

    # the human render's capability block agrees with the JSON overall + per-axis verdict (criterion 29, F52 scope).
    dossier = compile_payload["ranked_route_dossiers"][0]
    assessment = dossier["capability_assessment"]
    assert assessment is not None

    def field(dcp, name):
        for n, v in dcp["fields"]:
            if n == name:
                return v
        raise KeyError(name)

    overall = field(assessment, "overall")["value"]["value"]
    pdig = field(assessment, "profile_digest")["value"]
    assert f"CAPABILITY[poor-man@{pdig[:12]}]: {overall}" in compile_human_out
    for ax_name in _CAPABILITY_AXIS_NAMES:
        status = field(field(assessment, ax_name), "status")["value"]["value"]
        assert f"{ax_name}: {status}" in compile_human_out


def test_current_response_payload_with_stripped_capability_keys_is_refused():
    """Round V (D11 / F81) CORRECTS Round IV's F54: that test SIMULATED a v0.8 payload by stripping keys off a 0.9
    payload and called it "additive-optional, never a crash" -- while every REAL v0.8 routes-mode response was refused
    with a misleading result_digest mismatch.  The truth now: stripping a 0.9 key off a CURRENT-id payload is a
    malformed current payload and is REFUSED; the real v0.8 migration is proven on real main@df1b38d fixtures in
    tests/test_v0_9_round_v_schema_migration.py."""
    _, resp = _run(None)
    base = response_to_payload(resp)
    assert base.get("capability_question_digest") is None  # NOT_REQUESTED -> null pin, but the KEY is present
    stripped = dict(base)
    del stripped["capability_question_digest"]
    with pytest.raises(ValueError, match="must carry capability_question_digest"):
        response_from_payload(stripped)
    stripped = json.loads(json.dumps(base))
    del stripped["ranked_route_dossiers"][0]["capability_assessment"]
    with pytest.raises(ValueError, match="must carry capability_assessment"):
        response_from_payload(stripped)
    stripped = json.loads(json.dumps(base))
    del stripped["request"]["capability_profile"]
    with pytest.raises(ValueError, match="must carry"):
        response_from_payload(stripped)
