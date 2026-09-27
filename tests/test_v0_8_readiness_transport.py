"""v0.8 Real Route Dossiers -- readiness-on-the-wire transport tests (Writer 3's one job).

These pin two things: (1) an HONEST response's carried ``readiness`` survives a full serialize/deserialize round
trip byte-identical to the re-derivation (test g); (2) a payload whose carried ``readiness`` disagrees with what its
OWN replayed evidence re-derives to is REFUSED on load (``CompilationResponse._check_readiness_coherence``, M10) --
even when the forger is sophisticated enough to recompute ``result_digest``/``exit_code``/``admissible_route_digests``
so the response is otherwise fully internally coherent (the "fully-coherent forgery" residual every other axis in
this module documents; readiness closes the SAME residual on ITS OWN axis).

Integration controls use invented metadata, never experimental chemistry evidence (this file's header banner
convention, matching tests/test_process_service.py).
"""
from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from smartchem.conditions import EvidenceStatus, Interval
from smartchem.experiment import routes
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.service import (
    CompilationResponse,
    ResponseOutcome,
    affordability_entry_from_payload,
    build_recompile_request,
    ir_from_payload,
    provider_snapshot_from_payload,
    ranked_dag_summary_from_payload,
    ranked_summary_from_payload,
    request_from_payload,
    response_from_payload,
    response_to_payload,
    run_compilation,
)

_TARGET = "smiles:CC(=O)OC"  # methyl acetate -- the same fully-exhausting, route-bearing target test_service.py uses


def _sourced_envelope(original):
    """A synthetic, explicitly-accepted-source envelope -- lets a test drive the ``conditions`` obligation to
    SATISFIED (Sec 4) without touching any real experimental chemistry claim."""
    return replace(
        original,
        temperature=Interval(300.0, 310.0, "K"),
        status=EvidenceStatus.EXPERIMENTAL,
        provenance="synthetic software control; no experimental claim",
        source=SourceCitation("https://example.invalid/synthetic-control/test-v0-8-readiness-transport",
                              SourceReview.ACCEPTED),
    )


def _compile(monkeypatch=None, sourced=False):
    if sourced:
        original = routes._conditions_for
        monkeypatch.setattr(routes, "_conditions_for", lambda t: _sourced_envelope(original(t)))
    req = build_recompile_request(_TARGET, max_depth=3, max_routes=50)
    return run_compilation(req)


def _rebuild_response(payload: dict) -> CompilationResponse:
    """Reconstruct a ``CompilationResponse`` straight from a (possibly tampered) payload, WITHOUT running any of the
    load-time coherence guards -- the same construction ``response_from_payload`` does before its checks fire. Used
    to compute the TRUE derived fields (``result_digest`` etc.) a sophisticated forger would recompute, so tests can
    build a "fully-coherent forgery" (every derived field self-consistent) and confirm ``_check_readiness_coherence``
    still catches it via the REPLAY evidence, not via any of the OTHER already-documented guards."""
    ir_payload = payload["compilation_ir"]
    return CompilationResponse(
        payload["schema_version"],
        request_from_payload(payload["request"]),
        ResponseOutcome(payload["outcome"]),
        payload["standard_status"],
        None if ir_payload is None else ir_from_payload(ir_payload),
        tuple(payload["diagnostics"]),
        tuple(ranked_summary_from_payload(r) for r in payload["ranked_route_dossiers"]),
        tuple(affordability_entry_from_payload(e) for e in payload["affordability_frontier"]),
        tuple(provider_snapshot_from_payload(s) for s in payload.get("provider_snapshots", [])),
        parse_receipt_summary=payload["parse_receipt_summary"],
        ranked_dag_dossiers=tuple(
            ranked_dag_summary_from_payload(d) for d in payload.get("ranked_dag_dossiers", [])
        ),
    )


def _recompute_derived_fields(payload: dict) -> dict:
    """Mutate ``payload`` in place so its derived fields (``result_digest``, ``exit_code``,
    ``admissible_route_digests``, ``process_selection_status``) agree with what the tampered ``ranked_route_dossiers``
    NOW reconstruct to -- i.e. do exactly what a controlling, sophisticated forger would do. Returns ``payload``."""
    response = _rebuild_response(payload)
    payload["result_digest"] = response.result_digest
    payload["exit_code"] = response.exit_code
    payload["admissible_route_digests"] = list(response.admissible_route_digests)
    payload["process_selection_status"] = response.process_selection_status
    return payload


def _first_step_with(payload: dict, *, reaction_type: str) -> "tuple[dict, int]":
    """The first ``(ranked route dossier, step index)`` whose step has the given ``reaction_type`` obligation."""
    for r in payload["ranked_route_dossiers"]:
        for i, step in enumerate(r["readiness"]["per_step"]):
            if step["reaction_type"] == reaction_type:
                return r, i
    raise AssertionError(f"no ranked route dossier has a step with reaction_type={reaction_type}")


@pytest.fixture(scope="module")
def unsourced_payload():
    """A real compile of a route-bearing target, thick-serialized (``include_replay=True``); no synthetic conditions
    injected, so every step's ``conditions``/``process``/``workup_isolation`` obligation is UNKNOWN (undeclared)."""
    result = _compile()
    assert result.ranked_route_dossiers, "the target must yield at least one ranked route for these tests to bite"
    return response_to_payload(result, include_replay=True)


@pytest.fixture()
def sourced_payload(monkeypatch):
    """Same target, but every step's condition envelope is a synthetic, explicitly-accepted-source record -- so the
    ``conditions`` obligation reaches SATISFIED wherever ``reaction_type`` is also recognized (tier CONDITIONS_SUPPORTED,
    the strongest tier reachable this round; ``process`` stays DARK by design, Sec 5)."""
    result = _compile(monkeypatch, sourced=True)
    assert result.ranked_route_dossiers
    return response_to_payload(result, include_replay=True)


# -- (g) honest round trip -----------------------------------------------------------------------------------------


def test_g_honest_round_trip_preserves_readiness_identity(unsourced_payload):
    resp2 = response_from_payload(copy.deepcopy(unsourced_payload))
    # readiness rides result_digest (a digest-covered field), so a byte-identical round trip is the strongest form
    # of "preserves identity" available here.
    assert resp2.result_digest == unsourced_payload["result_digest"]
    for r in resp2.ranked_route_dossiers:
        assert isinstance(r.readiness_tier, str)
        assert r.readiness.tier == r.readiness_tier


def test_g_sourced_route_reaches_conditions_supported(sourced_payload):
    """Sanity check that the CONDITIONS_SUPPORTED tier is genuinely reachable through this harness (otherwise tests
    (b)/(c)/(e) below would be vacuously testing a tier no real route ever occupies)."""
    tiers = {r["readiness_tier"] for r in sourced_payload["ranked_route_dossiers"]}
    assert "CONDITIONS_SUPPORTED" in tiers, f"expected a CONDITIONS_SUPPORTED route, got tiers={tiers}"
    resp = response_from_payload(copy.deepcopy(sourced_payload))
    assert resp.result_digest == sourced_payload["result_digest"]


# -- (a) tier bumped while a step is unrecognized ------------------------------------------------------------------


def test_a_tier_bumped_over_an_unrecognized_step_is_refused(unsourced_payload):
    route0, idx = _first_step_with(unsourced_payload, reaction_type="UNSATISFIED")
    payload = copy.deepcopy(unsourced_payload)
    target = next(r for r in payload["ranked_route_dossiers"] if r["route_digest"] == route0["route_digest"])
    step = target["readiness"]["per_step"][idx]
    # Forge reaction_type SATISFIED (with a plausible class name) + bump every downstream obligation + the tier, so
    # the claimed record is INTERNALLY coherent (readiness_tier == its own readiness.tier) -- only the REPLAY
    # evidence (the step's real reaction center/graph, unchanged) disagrees.
    step["reaction_type"] = "SATISFIED"
    step["reaction_class_name"] = "forged reaction class"
    step["open_obligations"] = [o for o in step["open_obligations"] if not o.startswith("reaction_type")]
    target["readiness"]["route_open_obligations"] = sorted({
        reason for s in target["readiness"]["per_step"] for reason in s["open_obligations"]
    } | set(step["open_obligations"]))
    target["readiness_tier"] = "REACTION_VOUCHED" if step["conditions"] != "SATISFIED" else "CONDITIONS_SUPPORTED"
    _recompute_derived_fields(payload)
    with pytest.raises(ValueError, match="readiness"):
        response_from_payload(payload)


# -- (b) VOUCHED -> CONDITIONS_SUPPORTED while the envelope is unsourced --------------------------------------------


def test_b_conditions_satisfied_over_an_unsourced_envelope_is_refused(unsourced_payload):
    route0, idx = _first_step_with(unsourced_payload, reaction_type="SATISFIED")
    payload = copy.deepcopy(unsourced_payload)
    target = next(r for r in payload["ranked_route_dossiers"] if r["route_digest"] == route0["route_digest"])
    step = target["readiness"]["per_step"][idx]
    assert step["conditions"] != "SATISFIED"  # this route's envelope is genuinely undeclared
    step["conditions"] = "SATISFIED"
    step["process"] = "SATISFIED"  # also try to ride all the way to the (DARK) top while we're at it
    step["open_obligations"] = [o for o in step["open_obligations"] if o.startswith("workup")]
    target["readiness"]["route_open_obligations"] = sorted({
        reason for s in target["readiness"]["per_step"] for reason in s["open_obligations"]
    })
    target["readiness_tier"] = "PROCESS_SPECIFIED"
    _recompute_derived_fields(payload)
    with pytest.raises(ValueError, match="readiness"):
        response_from_payload(payload)


# -- (c) citation removed but the tier is kept ----------------------------------------------------------------------


def test_c_citation_removed_but_tier_kept_is_refused(sourced_payload):
    route0, idx = _first_step_with(sourced_payload, reaction_type="SATISFIED")
    assert route0["readiness_tier"] == "CONDITIONS_SUPPORTED"
    payload = copy.deepcopy(sourced_payload)
    target = next(r for r in payload["ranked_route_dossiers"] if r["route_digest"] == route0["route_digest"])
    # Strip the accepted source citation from the THICK replay evidence (the actual envelope the step re-derives
    # from) while leaving the claimed readiness (still CONDITIONS_SUPPORTED, still conditions=SATISFIED, still
    # carrying the provenance locator) untouched -- an internally-coherent claim whose OWN evidence no longer backs it.
    step_payload = target["replay_payload"][idx]
    step_payload["envelope"]["source"] = None
    _recompute_derived_fields(payload)
    with pytest.raises(ValueError, match="readiness"):
        response_from_payload(payload)


# -- (d) one step's readiness changed on a multi-step route while the route tier is kept -----------------------------


def test_d_non_limiting_step_obligation_tamper_on_a_multistep_route_is_refused(unsourced_payload):
    multi_step = None
    for r in unsourced_payload["ranked_route_dossiers"]:
        if len(r["readiness"]["per_step"]) >= 2:
            multi_step = r
            break
    assert multi_step is not None, "need at least one multi-step ranked route for this test to be meaningful"
    payload = copy.deepcopy(unsourced_payload)
    target = next(r for r in payload["ranked_route_dossiers"] if r["route_digest"] == multi_step["route_digest"])
    steps = target["readiness"]["per_step"]
    # Find a NON-limiting step: one whose reaction_type is already SATISFIED (so it is not what caps the route's
    # tier at FORMAL_CANDIDATE -- some OTHER step is). Forge its conditions to SATISFIED: the per-step record changes,
    # but min_tier over the route is unaffected (the limiting step is untouched), so the route's OWN tier claim does
    # not even need to move for this to be a lie.
    satisfied_idx = next(i for i, s in enumerate(steps) if s["reaction_type"] == "SATISFIED")
    steps[satisfied_idx]["conditions"] = "SATISFIED"
    steps[satisfied_idx]["open_obligations"] = [
        o for o in steps[satisfied_idx]["open_obligations"] if not o.startswith("conditions")
    ]
    # route tier / route_open_obligations deliberately left AS-IS -- the tamper is invisible at the coarse level.
    _recompute_derived_fields(payload)
    with pytest.raises(ValueError, match="readiness"):
        response_from_payload(payload)


# -- (e) workup-complete on an unsupporting process record (PROCESS_SPECIFIED is DARK) --------------------------------


def test_e_process_specified_claim_is_always_refused(sourced_payload):
    route0, idx = _first_step_with(sourced_payload, reaction_type="SATISFIED")
    payload = copy.deepcopy(sourced_payload)
    target = next(r for r in payload["ranked_route_dossiers"] if r["route_digest"] == route0["route_digest"])
    step = target["readiness"]["per_step"][idx]
    step["process"] = "SATISFIED"
    step["workup_isolation"] = "SATISFIED"
    step["open_obligations"] = []
    target["readiness"]["route_open_obligations"] = sorted({
        reason for s in target["readiness"]["per_step"] for reason in s["open_obligations"]
    })
    target["readiness_tier"] = "PROCESS_SPECIFIED"
    _recompute_derived_fields(payload)
    with pytest.raises(ValueError, match="readiness"):
        response_from_payload(payload)


# -- (f) same-formula evidence substitution (route_digest mismatch) --------------------------------------------------


def test_f_evidence_substitution_across_routes_is_refused(unsourced_payload):
    payload = copy.deepcopy(unsourced_payload)
    dossiers = payload["ranked_route_dossiers"]
    assert len(dossiers) >= 2, "need at least two distinct ranked routes to substitute evidence between them"
    # Swap the THICK replay payloads (and their readiness records, to keep the forgery internally coherent) between
    # two different routes while leaving each entry's own route_digest untouched -- a same-formula-class evidence
    # substitution (the M10 "route_digest mismatch" case): one entry's claimed readiness now belongs to a DIFFERENT
    # route's steps.
    a, b = dossiers[0], dossiers[1]
    a["replay_payload"], b["replay_payload"] = b["replay_payload"], a["replay_payload"]
    a["readiness"], b["readiness"] = b["readiness"], a["readiness"]
    a["readiness_tier"], b["readiness_tier"] = b["readiness_tier"], a["readiness_tier"]
    _recompute_derived_fields(payload)
    with pytest.raises(ValueError, match="DIFFERENT route"):
        response_from_payload(payload)


# -- M10: edit the serialized tier without moving the evidence (the fully-coherent forgery) ---------------------------


def test_m10_fully_coherent_forgery_is_still_refused_by_replay_evidence(unsourced_payload):
    """The strongest form of the M10 close: a forger who edits the readiness claim AND recomputes every OTHER
    derived field (``result_digest``, ``exit_code``, ``admissible_route_digests``, ``process_selection_status``) so
    the response is fully internally self-consistent -- everything the OTHER coherence guards check agrees with
    itself -- is still refused, because ``_check_readiness_coherence`` re-derives against the REPLAYED STEPS, not
    against anything the forger can make self-consistent without also changing the evidence."""
    route0, idx = _first_step_with(unsourced_payload, reaction_type="SATISFIED")
    payload = copy.deepcopy(unsourced_payload)
    target = next(r for r in payload["ranked_route_dossiers"] if r["route_digest"] == route0["route_digest"])
    step = target["readiness"]["per_step"][idx]
    step["conditions"] = "SATISFIED"
    step["process"] = "SATISFIED"
    step["workup_isolation"] = "SATISFIED"
    step["open_obligations"] = []
    target["readiness"]["route_open_obligations"] = sorted({
        reason for s in target["readiness"]["per_step"] for reason in s["open_obligations"]
    })
    target["readiness_tier"] = "PROCESS_SPECIFIED"
    _recompute_derived_fields(payload)  # the sophisticated forger's move: recompute EVERYTHING else, honestly
    with pytest.raises(ValueError, match="does not support"):
        response_from_payload(payload)


def test_thin_transport_readiness_forgery_stays_advisory_by_documented_design(unsourced_payload):
    """The documented BOUNDARY on ``_check_readiness_coherence``: without a carried ``replay_payload`` (the DEFAULT
    thin wire) there is no evidence to re-derive against, so a forgery on the THIN transport is NOT caught by this
    check -- mirroring the exact advisory boundary the frontier's catalyst/fiction channels already carry. This test
    exists so that boundary is pinned, not accidentally tightened or loosened by a future change."""
    thin = response_to_payload(_rebuild_response(copy.deepcopy(unsourced_payload)))
    assert all("replay_payload" not in r for r in thin["ranked_route_dossiers"])
    route0, idx = _first_step_with(thin, reaction_type="SATISFIED")
    target = next(r for r in thin["ranked_route_dossiers"] if r["route_digest"] == route0["route_digest"])
    step = target["readiness"]["per_step"][idx]
    step["conditions"] = "SATISFIED"
    step["open_obligations"] = [o for o in step["open_obligations"] if not o.startswith("conditions")]
    target["readiness"]["route_open_obligations"] = sorted({
        reason for s in target["readiness"]["per_step"] for reason in s["open_obligations"]
    })
    target["readiness_tier"] = "CONDITIONS_SUPPORTED"
    _recompute_derived_fields(thin)
    resp = response_from_payload(thin)  # no raise -- advisory, by design, on the thin transport
    forged = next(r for r in resp.ranked_route_dossiers if r.route_digest == target["route_digest"])
    assert forged.readiness_tier == "CONDITIONS_SUPPORTED"
