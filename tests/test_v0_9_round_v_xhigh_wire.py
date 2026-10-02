"""0.9 RC Round V X-high continuation -- the wire laws of barrier D14/D18/D20/D22 (writer W-WIRE).

**Listen, Morty: a hash an attacker can recompute is a checksum, not a defence.** Every law below is pinned by a
discriminating test -- the honest path and the forged/stale path must DISAGREE, and each refusal is matched by its OWN
message so a test can never pass because some other layer happened to fire first (Wave-A' A-WIRE P2):

* D20(1) verified admission re-projects WITH the request's capability profile (on the WIP tip ``78554a2`` an honest
  FITS route on a profile request was falsely REFUSED -- measured, scratch ``laneWIRE_B/probe_va.py``);
* D20(4) the consumer's capability-question pin (``expected_capability_question_digest``) -- incl. None-vs-set;
* D20(g) the display origin is content-bound (``""`` or the snapshot's own ``profile_id``);
* D14/D22 the constraints box is generation-paired with the request and carries the temperature floor;
* D18 the replayed procedure-material phase is an evidence-graded PhaseClaim on the wire;
* D22 the released v0.8 DAG summary id decodes ONLY as legacy (real v0.8 producer output: tests/fixtures/v08/
  response_isopentyl_acetate_dag.json), and the WIP-only ids are never migrated;
* D27 (Wave C4 C4T-1..8 + Foreman N2-N4, bottom of the file) the structural transport closure: corpus envelopes
  re-derived (D27.1), the whole-body wire digest (D27.2), the outcome / ranking / frontier / diagnostics / receipt
  count / receipt bounds re-derived or bound (D27.3-D27.6), and the D27.7 residual closes;
* D28 (Wave C5 C5-F1..F7, bottom of the file) the ledger made truthful: a carried unknown() envelope is corpus-checked
  too (D28.1), the IR's own diagnostics are re-derived (D28.2), the receipt's identity digests and result count are
  non-null (D28.3), the unconstrained-DAG candidate label is DISCLOSED advisory (D28.4), and every container carries
  exactly its versioned keys, serial holds exact JSON numbers (D28.5);
* D29 (Wave C6 C6-F8 / C6-NEW-1, bottom of the file) every replayed step is a transform the carried algebra emits --
  byproducts as STRUCTURES, the reaction centre, no ancillary flag (D29.1; it also closes the D26.4 re-centre boundary
  on every current load; a legacy v0.8 step: under verified admission, as D27.1) -- and exact keys reach the capability codec's nodes, identity-loss entries and structural candidates
  (D29.2).
"""
from __future__ import annotations

import copy
import dataclasses as dc
import json
from pathlib import Path

import pytest

import smartchem.service as svc  # the D24 attacker patches its OWN copy of the producer (restored before any load)
from smartchem.capability.presets import (
    CAPABILITY_PROFILE_PRESETS,
    custom,
    isopentyl_capability_fit_bench,
    poor_man,
    research_lab,
    resolve_capability_profile,
)
from smartchem.conditions import Interval
from smartchem.constraints import PHYSICAL_BOUNDS_SCHEMA, PHYSICAL_BOUNDS_SCHEMA_V1, PhysicalBounds
from smartchem.experiment import routes
from smartchem.experiment.readiness import PROCESS_SPECIFIED, evaluate_route, tier_rank
from smartchem.experiment.stock import Phase
from smartchem.material_spec import EvidenceKind, PhaseClaim
from smartchem.procedure_evidence import ProcedureMaterialRole, ProcedureMaterialUse
from smartchem.process_constraints import Agitation, ProcessBounds, ProcessRequirements
from smartchem.service import (
    COMPILATION_RESPONSE_SCHEMA,
    LEGACY_V08_RANKED_DAG_SUMMARY_SCHEMA,
    RANKED_DAG_SUMMARY_SCHEMA,
    RankedRouteSummary,
    TransformGrammar,
    _procedure_material_use_from_payload,
    _procedure_material_use_to_payload,
    _reconstruct_route,
    build_recompile_request,
    deserialize_response,
    ranked_dag_summary_from_payload,
    render_capability_lines,
    request_from_payload,
    request_to_payload,
    response_from_payload,
    response_to_payload,
    run_compilation,
    serialize_response,
)

FIX = Path(__file__).parent / "fixtures" / "v08"
_TARGET = "smiles:CC(=O)OC"  # methyl acetate: the small max_depth=2 search the transport tests share


def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def _run(profile, **kw):
    return run_compilation(build_recompile_request(_TARGET, capability_profile=profile, max_depth=2, **kw))


# -- D20(1): verified admission re-projects under the request's OWN capability profile ------------------------------

def _declared_process():
    return ProcessRequirements(elapsed_minutes=Interval(10, 20, "min"), active_minutes=Interval(1, 2, "min"),
                               agitation=Agitation.NONE, workup_included=True,
                               provenance="synthetic software control; no experimental claim")


def _fits_profile_response(monkeypatch):
    original = routes._conditions_for
    monkeypatch.setattr(routes, "_conditions_for", lambda t: dc.replace(original(t), process=_declared_process()))
    resp = _run("poor-man", process=ProcessBounds.quick())
    assert resp.admissible_route_digests, "setup must yield at least one FITS route on a profile request"
    assert all(d.capability_assessment is not None for d in resp.ranked_route_dossiers)
    return resp


def test_verified_admission_admits_an_honest_fits_route_on_a_profile_request(monkeypatch):
    resp = _fits_profile_response(monkeypatch)
    back = deserialize_response(serialize_response(resp, include_replay=True), require_verified_admission=True)
    assert back.admissible_route_digests == resp.admissible_route_digests


def test_a_profile_blind_re_projection_is_the_false_refusal_the_fix_closes(monkeypatch):
    """The discriminating control: re-project WITHOUT the profile (exactly the WIP-tip behaviour) and the honest FITS
    route re-projects to a summary whose capability_assessment is None -- refused."""
    resp = _fits_profile_response(monkeypatch)
    wire = serialize_response(resp, include_replay=True)
    original = RankedRouteSummary.of_fit.__func__

    def profile_blind(cls, fit, *, identity_losses=(), capability_profile=None):
        return original(cls, fit, identity_losses=identity_losses)

    monkeypatch.setattr(RankedRouteSummary, "of_fit", classmethod(profile_blind))
    with pytest.raises(ValueError, match="re-projects to a DIFFERENT summary"):
        deserialize_response(wire, require_verified_admission=True)


# -- D20(4): the consumer capability-question pin -------------------------------------------------------------------

def test_capability_question_pin_admits_the_question_that_was_asked():
    resp = _run("poor-man")
    payload = response_to_payload(resp)
    back = response_from_payload(payload, expected_capability_question_digest=resp.capability_question_digest)
    assert back.capability_question_digest == resp.capability_question_digest
    # and a NOT_REQUESTED consumer pins None
    plain = _run(None)
    response_from_payload(response_to_payload(plain), expected_capability_question_digest=None)


def test_a_coherent_bench_swap_passes_the_request_pin_but_not_the_question_pin():
    """Wave-A' A-WIRE (d): the attacker answers a DIFFERENT bench's question -- an honestly re-derived research-lab
    response for the same search.  ``expected_request_digest`` cannot see it (capability is excluded from the search
    identity by design); the capability-question pin can."""
    asked = build_recompile_request(_TARGET, capability_profile="poor-man", max_depth=2)
    answer = response_to_payload(_run("research-lab"))            # coherent, every pin its own
    response_from_payload(answer, expected_request_digest=asked.semantic_digest)   # the request pin passes...
    with pytest.raises(ValueError, match="DIFFERENT capability question"):
        response_from_payload(answer, expected_request_digest=asked.semantic_digest,
                              expected_capability_question_digest=asked.capability_question_digest)


@pytest.mark.parametrize("asked_profile, answered_profile", [(None, "poor-man"), ("poor-man", None)])
def test_capability_question_pin_is_fail_closed_on_none_vs_set(asked_profile, answered_profile):
    asked = build_recompile_request(_TARGET, capability_profile=asked_profile, max_depth=2)
    answer = serialize_response(_run(answered_profile))
    with pytest.raises(ValueError, match="DIFFERENT capability question"):
        deserialize_response(answer, expected_capability_question_digest=asked.capability_question_digest)


# -- D20(g): the display origin is content-bound --------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(CAPABILITY_PROFILE_PRESETS))
def test_every_preset_builds_an_origin_equal_to_its_snapshot_id(name):
    req = build_recompile_request(_TARGET, capability_profile=name, max_depth=2)
    assert req.capability_profile_origin == req.capability_profile.profile_id == resolve_capability_profile(name).profile_id


def test_origin_relabel_is_refused_at_construction_and_on_the_wire():
    req = build_recompile_request(_TARGET, capability_profile="poor-man", max_depth=2)
    with pytest.raises(ValueError, match="content-bound"):
        dc.replace(req, capability_profile_origin="research-lab")
    payload = request_to_payload(req)
    payload["capability_profile_origin"] = "research-lab"      # moves no digest -- the relabel the law closes
    with pytest.raises(ValueError, match="content-bound"):
        request_from_payload(payload)
    # "" stays admissible (a caller may decline to name an origin); NOT_REQUESTED cannot name one.
    assert dc.replace(req, capability_profile_origin="").capability_profile_origin == ""
    plain = build_recompile_request(_TARGET, max_depth=2)
    with pytest.raises(ValueError, match="no capability profile is declared"):
        dc.replace(plain, capability_profile_origin="poor-man")


def test_inline_custom_origin_is_its_profile_id():
    bench = custom(profile_id="xhigh-inline-bench")
    req = build_recompile_request(_TARGET, capability_profile=bench, max_depth=2)
    assert req.capability_profile_origin == "xhigh-inline-bench"


# -- D14/D22: the constraints box carries the floor, paired with the request generation -----------------------------

def test_a_current_request_carries_and_round_trips_the_temperature_floor():
    req = build_recompile_request(_TARGET, max_depth=2, min_temperature_k=250.0, max_temperature_k=400.0)
    payload = request_to_payload(req)
    assert payload["constraints"]["schema_version"] == PHYSICAL_BOUNDS_SCHEMA
    assert payload["constraints"]["min_temperature_k"] == 250.0
    back = request_from_payload(payload)
    assert back.constraints.bounds.min_temperature_k == 250.0 and back.digest == req.digest
    # the floor is part of the SEARCH identity (it is applied to ranking), exactly like the ceiling
    assert back.semantic_digest != build_recompile_request(_TARGET, max_depth=2, max_temperature_k=400.0).semantic_digest


def test_a_current_constraints_box_missing_the_floor_key_is_refused():
    payload = request_to_payload(build_recompile_request(_TARGET, max_depth=2))
    del payload["constraints"]["min_temperature_k"]
    with pytest.raises(ValueError, match="must contain exactly"):
        request_from_payload(payload)


def test_a_floor_above_the_ceiling_is_refused():
    with pytest.raises(ValueError, match="min_temperature_k cannot exceed max_temperature_k"):
        build_recompile_request(_TARGET, max_depth=2, min_temperature_k=450.0, max_temperature_k=400.0)


def test_the_legacy_request_box_decodes_as_the_released_generation():
    req = request_from_payload(_load("request_isopentyl_acetate.json"))
    assert req.constraints.bounds.schema_version == PHYSICAL_BOUNDS_SCHEMA_V1
    assert req.constraints.bounds.min_temperature_k is None
    # X-high D26.5 (Wave-C'' T6b): a migrated v0.8 request is read-only evidence -- the current encoder would emit
    # 0.9-only keys under the v0.8 id, so re-encoding it is REFUSED (the released box itself decoded above).
    with pytest.raises(ValueError, match=r"legacy v0\.8 request.*\(D26\.5\)"):
        request_to_payload(req)


# -- D18: the replayed phase is an evidence-graded PhaseClaim --------------------------------------------------------

def _use(phase):
    return ProcedureMaterialUse("acetic acid", ProcedureMaterialRole.REACTANT, phase=phase,
                                evidence_source="fixture locator")


def test_a_phase_claim_round_trips_with_its_evidence_kind():
    claim = PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED, "a volume read as a liquid")
    payload = _procedure_material_use_to_payload(_use(claim))
    assert payload["phase"] == {"phase": "LIQUID", "evidence": "AUTHOR_INFERRED", "note": "a volume read as a liquid"}
    back = _procedure_material_use_from_payload(json.loads(json.dumps(payload)))
    assert back == _use(claim) and back.phase.evidence is EvidenceKind.AUTHOR_INFERRED
    assert _procedure_material_use_from_payload(_procedure_material_use_to_payload(_use(None))).phase is None


@pytest.mark.parametrize("bad", [
    "LIQUID",                                                            # the retired ungraded scalar
    {"phase": "LIQUID", "evidence": "SOURCE_QUOTED"},                    # a missing key
    {"phase": "LIQUID", "evidence": "SOURCE_QUOTED", "note": "", "x": 1},  # a smuggled key
    {"phase": "UNKNOWN", "evidence": "SOURCE_QUOTED", "note": ""},       # UNKNOWN is the absence of a claim
    {"phase": "LIQUID", "evidence": "CERTAIN", "note": ""},              # not an EvidenceKind
])
def test_a_malformed_phase_claim_is_refused(bad):
    payload = _procedure_material_use_to_payload(_use(PhaseClaim(Phase.LIQUID, EvidenceKind.SOURCE_QUOTED)))
    payload["phase"] = bad
    with pytest.raises((TypeError, ValueError)):
        _procedure_material_use_from_payload(payload)


# -- D22: the released v0.8 DAG summary decodes ONLY as legacy -------------------------------------------------------

def _v08_dag_dossier_with_procedure():
    payload = _load("response_isopentyl_acetate_dag.json")
    return next(d for d in payload["ranked_dag_dossiers"]
                if any(s["envelope"]["procedure"] is not None for s in d["replay_payload"]))


def test_a_real_v08_dag_dossier_decodes_standalone_as_legacy_with_migrated_uses():
    raw = _v08_dag_dossier_with_procedure()
    assert raw["schema_version"] == LEGACY_V08_RANKED_DAG_SUMMARY_SCHEMA != RANKED_DAG_SUMMARY_SCHEMA
    summary = ranked_dag_summary_from_payload(copy.deepcopy(raw))
    assert summary.is_legacy_v08
    ops = [op for s in summary.replay_payload if s["envelope"]["procedure"]
           for op in s["envelope"]["procedure"]["operations"]]
    assert ops and all(op["material_uses"] == [] for op in ops)
    assert "material_uses" not in json.dumps(raw)          # the caller's payload is never mutated


def test_a_legacy_dag_dossier_carrying_0_9_content_is_refused():
    raw = _v08_dag_dossier_with_procedure()
    op = next(op for s in raw["replay_payload"] if s["envelope"]["procedure"]
              for op in s["envelope"]["procedure"]["operations"])
    op["material_uses"] = []                               # even the "empty" 0.9 slot is 0.9 content under a 0.8 id
    with pytest.raises(ValueError, match="0.9-only key"):
        ranked_dag_summary_from_payload(raw)


@pytest.mark.parametrize("bad", ["smartchem.service/ranked-dag-summary-v1alpha3",
                                 # 0.9.5 S14: the 0.9.0a1 pre-release id is refused like any other non-current id
                                 "smartchem.service/ranked-dag-summary-v1alpha5",
                                 "smartchem.service/ranked-dag-summary-v1alpha7", "garbage"])
def test_an_unknown_dag_summary_id_is_refused_precisely(bad):
    raw = _v08_dag_dossier_with_procedure()
    raw["schema_version"] = bad
    with pytest.raises(ValueError, match="unsupported ranked DAG summary schema_version"):
        ranked_dag_summary_from_payload(raw)


def test_the_real_v08_dag_response_loads_and_a_current_response_cannot_embed_a_legacy_dag():
    legacy = response_from_payload(_load("response_isopentyl_acetate_dag.json"))
    assert legacy.is_legacy_v08 and legacy.ranked_dag_dossiers
    assert all(d.is_legacy_v08 for d in legacy.ranked_dag_dossiers)
    current = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    assert current.schema_version == COMPILATION_RESPONSE_SCHEMA
    with pytest.raises(ValueError, match="ranked DAG summary of the other schema generation"):
        dc.replace(current, ranked_dag_dossiers=legacy.ranked_dag_dossiers[:1])


# -- D14: the ``--min-temp`` CLI surface ------------------------------------------------------------------------------

def _cli(argv):
    import io
    from contextlib import redirect_stderr, redirect_stdout

    from smartchem.cli import main
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def test_min_temp_flag_flows_into_the_request_constraints_box():
    code, out, _ = _cli(["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--min-temp", "273.15",
                         "--max-temp", "400", "--emit-request"])
    assert code == 0
    box = json.loads(out)["constraints"]
    assert box["schema_version"] == PHYSICAL_BOUNDS_SCHEMA
    assert (box["min_temperature_k"], box["max_temperature_k"]) == (273.15, 400.0)
    # and it is the same request the service builder makes (one default table -- alias independence)
    assert json.loads(out) == request_to_payload(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, min_temperature_k=273.15, max_temperature_k=400.0))


def test_a_min_temp_above_max_temp_is_a_loud_domain_exit():
    code, out, err = _cli(["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--min-temp", "500",
                           "--max-temp", "400", "--emit-request"])
    assert code == 2 and not out.strip()
    assert "min_temperature_k cannot exceed max_temperature_k" in err


# =====================================================================================================================
# D24.11-D24.15 (Wave-C' Adversary D, transport).  Each test REPLAYS the adversary's attack: the keyless attacker runs
# a modified producer (a public codec with one law switched off), so EVERY unkeyed pin -- result_digest, the
# capability-question pin, route digests -- is recomputed; then the UNPATCHED consumer loads it with every pin it has.
# =====================================================================================================================


def _attacker(monkeypatch, name, replacement, produce):
    """Run ``produce()`` with ``svc.<name>`` replaced (the attacker's producer), then RESTORE it before the consumer
    loads -- exactly Adversary D's shape (atk_losses.py)."""
    with monkeypatch.context() as m:
        m.setattr(svc, name, replacement)
        return produce()


# -- D24.11: identity losses are re-derived from the carried request ------------------------------------------------

_STEREO_ISOPENTYL = "smiles:CC(=O)OCC[C@H](C)C"   # isopentyl acetate + a stereo marker -> a BLOCKER on "conditions"


def test_D_L1_stripped_identity_loss_forging_process_specified_is_refused(monkeypatch):
    """Adversary D's EXACT attack (atk_losses.py): the corpus isopentyl route under the fit bench, with the target's
    stereochemistry BLOCKER stripped by the attacker's producer -- readiness re-derives to PROCESS_SPECIFIED under the
    forged (empty) losses, the route keeps its OWN route_digest, every public pin is recomputed.  Pre-D24.11 it LOADED
    under the request pin + the capability-question pin + verified admission."""
    request = build_recompile_request(_STEREO_ISOPENTYL, capability_profile=isopentyl_capability_fit_bench(),
                                      helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",))
    forged = _attacker(monkeypatch, "_recompile_identity_losses", lambda target_input, features: (),
                       lambda: run_compilation(request))
    assert forged.identity_losses == ()
    # the forgery is potent: some dossier claims a tier the request's OWN loss forbids
    honest_losses = svc._rederive_identity_losses(request)
    assert [loss.feature for loss in honest_losses] == ["stereochemistry"]
    lifted = [d for d in forged.ranked_route_dossiers
              if tier_rank(d.readiness.tier)
              > tier_rank(evaluate_route(_reconstruct_route(d.replay_payload), identity_losses=honest_losses).tier)]
    assert lifted and any(d.readiness.tier == PROCESS_SPECIFIED for d in lifted)
    payload = response_to_payload(forged)                      # CANONICAL_VERIFIED, every public pin recomputed
    with pytest.raises(ValueError, match=r"do not equal the losses the carried request's own target implies"):
        response_from_payload(payload, expected_request_digest=request.semantic_digest,
                              expected_capability_question_digest=request.capability_question_digest,
                              require_verified_admission=True)
    with pytest.raises(ValueError, match="D24.11"):          # and on a plain load too (the check is replay-free)
        response_from_payload(payload)


def test_an_honest_loss_bearing_response_loads_and_an_injected_loss_is_refused(monkeypatch):
    """The discriminating control, both directions: the honest stereo response (its IR carries the BLOCKER) loads; an
    attacker who INJECTS a loss the target does not imply (hiding a verdict behind a fake blocker) is refused too."""
    request = build_recompile_request("smiles:CC(=O)O[C@@H](C)CC", capability_profile="poor-man", max_depth=2)
    honest = run_compilation(request)
    assert [loss.feature for loss in honest.identity_losses] == ["stereochemistry"]
    back = response_from_payload(response_to_payload(honest), require_verified_admission=True)
    assert back.identity_losses == honest.identity_losses
    flat = build_recompile_request("smiles:CC(=O)OC", capability_profile="poor-man", max_depth=2)
    injected = _attacker(monkeypatch, "_recompile_identity_losses",
                         lambda target_input, features: honest.identity_losses, lambda: run_compilation(flat))
    with pytest.raises(ValueError, match="D24.11"):
        response_from_payload(response_to_payload(injected))


def test_a_stripped_decompile_formula_reduction_loss_is_refused(monkeypatch):
    """The DECOMPILE path re-derives too: a ``decompile --smiles`` IR carries the structure->formula BLOCKER."""
    request = svc.build_decompile_request("CC(=O)Nc1ccc(O)cc1", input_kind=svc.InputKind.SMILES)
    honest = run_compilation(request)
    assert honest.identity_losses and response_from_payload(response_to_payload(honest)).identity_losses
    real = svc._decompile_resolution
    forged = _attacker(monkeypatch, "_decompile_resolution",
                       lambda req: (lambda t, _l, r: (t, (), r))(*real(req)), lambda: run_compilation(request))
    assert forged.identity_losses == ()
    with pytest.raises(ValueError, match="D24.11"):
        response_from_payload(response_to_payload(forged))


def test_a_target_file_response_is_unverifiable_on_load_and_the_loader_never_reads_the_path(tmp_path, monkeypatch):
    target = tmp_path / "target.txt"
    target.write_text("CC(=O)OC\n")
    resp = run_compilation(build_recompile_request(str(target), input_kind=svc.InputKind.TARGET_FILE, max_depth=2))
    assert resp.compilation_ir is not None
    payload = response_to_payload(resp)
    target.unlink()                                             # the consumer's filesystem does not have the file
    opened = []
    real_open = open

    def spy(path, *a, **k):
        opened.append(str(path))
        return real_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", spy)
    # 0.9.5 S6: refused at dispatch now (before the identity-loss re-derivation that used to refuse it second) -- the
    # law this test pins, "the loader never reads the path", is unchanged and now holds by structure, not by order.
    with pytest.raises(ValueError, match=r"TARGET_FILE response cannot be verified on load.*0\.9\.5 S6"):
        response_from_payload(payload)
    assert str(target) not in opened


def test_real_v08_loss_bearing_fixture_loads_as_legacy_and_its_stripped_loss_is_refused():
    """The REAL v0.8 producer's stereo response (tests/fixtures/v08/response_stereo_isopentyl_acetate_smiles.json):
    today's derivation reproduces its loss exactly, so it loads (plain AND verified).  The attacker strips the loss and
    re-serializes through the public codec -- the frozen v0.8 digest rule is recomputed too -- and it is refused as
    legacy, never loaded as current."""
    raw = _load("response_stereo_isopentyl_acetate_smiles.json")
    legacy = response_from_payload(copy.deepcopy(raw))
    assert legacy.is_legacy_v08 and [loss.feature for loss in legacy.identity_losses] == ["stereochemistry"]
    # X-high D27.1 (legacy leg): its procedure routes carry v0.8's CORPUS envelopes, which today's corpus has since
    # corrected, so VERIFIED admission fails closed with the recompile hint (a plain load stays advisory, above).
    with pytest.raises(ValueError, match=r"D27\.1.*recompile under 0\.9"):
        response_from_payload(copy.deepcopy(raw), require_verified_admission=True)
    # the attacker edits the REAL v0.8 wire in place (keeping its v0.8 shape) and recomputes the legacy result digest
    # with the public frozen-v0.8 rule, exactly as the stripped record digests it.
    forged = dc.replace(legacy, compilation_ir=dc.replace(legacy.compilation_ir, identity_losses=()))
    payload = copy.deepcopy(raw)
    payload["compilation_ir"]["identity_losses"] = []
    payload["result_digest"] = svc._transport_bound_result_digest(forged.result_digest, raw["transport_mode"])
    assert payload["result_digest"] != raw["result_digest"]
    with pytest.raises(ValueError, match=r"D24\.11\) \[legacy v0\.8 payload"):
        response_from_payload(payload)


def test_a_real_v08_loss_set_that_todays_resolver_derives_differently_fails_closed_as_legacy(monkeypatch):
    """D24.11's legacy clause, exercised on the REAL fixture: if today's derivation disagreed with the genuine v0.8
    loss set (simulated -- today's resolver reproduces it), the payload fails closed with the legacy hint under verified
    admission, never loads as current."""
    monkeypatch.setattr(svc, "_recompile_identity_losses", lambda target_input, features: ())
    with pytest.raises(ValueError, match=r"legacy v0\.8 payload.*recompile under 0\.9"):
        response_from_payload(_load("response_stereo_isopentyl_acetate_smiles.json"), require_verified_admission=True)


# -- D24.12: the render shows the content identity; the question pin authenticates ----------------------------------

def test_D_O2_a_relabelled_bench_renders_its_real_content_digest_and_the_question_pin_refuses_it():
    """Adversary D O2: research-lab CONTENT relabelled ``profile_id="poor-man"`` passes the D20 origin law (the origin
    equals the free-text id) and loads.  The render now carries the digest of what actually answered, which is NOT the
    poor-man bench's; the consumer's poor-man question pin refuses it."""
    asked = build_recompile_request(_TARGET, capability_profile="poor-man", max_depth=2)
    fake = dc.replace(research_lab(), profile_id="poor-man")
    forged = _run(fake)
    back = response_from_payload(response_to_payload(forged))
    line = render_capability_lines(back.ranked_route_dossiers[0].capability_assessment,
                                   back.request.capability_profile_origin, indent="")[0]
    assert line.startswith(f"CAPABILITY[poor-man@{fake.profile_digest[:12]}]: ")
    assert fake.profile_digest[:12] != poor_man().profile_digest[:12]
    assert f"@{poor_man().profile_digest[:12]}]" not in line
    with pytest.raises(ValueError, match="DIFFERENT capability question"):
        response_from_payload(response_to_payload(forged),
                              expected_capability_question_digest=asked.capability_question_digest)


# -- D24.13: capability profile + convergent-DAG grammar ------------------------------------------------------------

def _dag_request(profile=None):
    return build_recompile_request(_TARGET, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, max_depth=2,
                                   process=ProcessBounds.quick(), capability_profile=profile)


def test_the_producer_refuses_the_profile_convergent_pair():
    resp = run_compilation(_dag_request("poor-man"))
    assert resp.outcome.value == "REFUSED" and resp.compilation_ir is None and not resp.ranked_dag_dossiers


def test_D_G1_a_dag_response_carrying_a_capability_profile_is_refused(monkeypatch):
    """Adversary D G1: an honest DAG-mode response re-labelled as answering a poor-man capability question (a pair the
    producer REFUSES), every public pin recomputed; pre-D24.13 it loaded with request + question pins + verified
    admission, answering the capability question with NOTHING while looking like success."""
    dag = run_compilation(_dag_request())
    assert dag.ranked_dag_dossiers
    asked = _dag_request("poor-man")
    payload = _attacker(monkeypatch, "CompilationResponse",
                        _unchecked_response_class("_check_capability_topology"),
                        lambda: response_to_payload(svc.CompilationResponse(
                            **{f.name: getattr(dag, f.name) for f in dc.fields(dag)} | {"request": asked})))
    with pytest.raises(ValueError, match="D24.13"):
        response_from_payload(payload, expected_request_digest=asked.semantic_digest,
                              expected_capability_question_digest=asked.capability_question_digest,
                              require_verified_admission=True)
    with pytest.raises(ValueError, match="D24.13"):           # and the in-memory record cannot even be built
        dc.replace(dag, request=asked)


def _unchecked_response_class(check_name):
    """The attacker's producer: CompilationResponse with ONE construction law switched off."""
    return type("AttackerResponse", (svc.CompilationResponse,), {check_name: lambda self: None})


# -- D24.14: a verdict cannot be deleted ----------------------------------------------------------------------------

def test_D_D1_deleting_a_ranked_dossier_is_refused(monkeypatch):
    """Adversary D D1: delete dossier 0 (and its frontier entry) and recompute every pin; pre-D24.14 it loaded under the
    request pin + question pin + verified admission, silently omitting a verdict for a candidate the IR still lists."""
    resp = _run("poor-man")
    assert len(resp.ranked_route_dossiers) >= 2
    keep = resp.ranked_route_dossiers[1:]
    kept = {d.route_digest for d in keep}
    fields = {f.name: getattr(resp, f.name) for f in dc.fields(resp)}
    fields |= {"ranked_route_dossiers": keep,
               "affordability_frontier": tuple(e for e in resp.affordability_frontier if e.route_digest in kept)}
    payload = _attacker(monkeypatch, "CompilationResponse", _unchecked_response_class("_check_dossier_completeness"),
                        lambda: response_to_payload(svc.CompilationResponse(**fields)))
    with pytest.raises(ValueError, match=r"a deleted verdict; refused \(D24\.14\)"):
        response_from_payload(payload, expected_request_digest=resp.request.semantic_digest,
                              expected_capability_question_digest=resp.request.capability_question_digest,
                              require_verified_admission=True)
    with pytest.raises(ValueError, match="D24.14"):          # and the in-memory record cannot even be built
        dc.replace(resp, ranked_route_dossiers=keep, affordability_frontier=fields["affordability_frontier"])


def test_dossier_completeness_holds_on_every_honest_mode():
    """The producer invariant D24.14 enforces, on the honest paths it describes (and on every real v0.8 fixture, which
    load above): routes mode ranks every candidate; DAG mode dossiers every DAG iff the box constrains anything."""
    routes_resp = _run(None)
    assert {d.route_digest for d in routes_resp.ranked_route_dossiers} == {
        c.candidate_digest for c in routes_resp.compilation_ir.candidates}
    constrained = run_compilation(_dag_request())
    assert {d.route_digest for d in constrained.ranked_dag_dossiers} == {
        c.candidate_digest for c in constrained.compilation_ir.candidates}
    unconstrained = run_compilation(build_recompile_request(
        _TARGET, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, max_depth=2))
    assert unconstrained.compilation_ir.candidates and not unconstrained.ranked_dag_dossiers


# -- D24.15: a capability profile embeds the current PhysicalBounds generation only ----------------------------------

def test_D_B2_a_profile_embedding_a_legacy_physical_bounds_box_is_refused():
    v1box = PhysicalBounds(PHYSICAL_BOUNDS_SCHEMA_V1, 373.15, None, None)
    with pytest.raises(ValueError, match="D24.15"):
        dc.replace(poor_man(), physical_bounds=v1box)
    # on the wire: relabel the embedded box of a current request's snapshot to the legacy generation
    payload = request_to_payload(build_recompile_request(_TARGET, capability_profile="poor-man", max_depth=2))
    box = next(v for n, v in payload["capability_profile"]["fields"] if n == "physical_bounds")
    for field_pair in box["fields"]:
        if field_pair[0] == "schema_version":
            field_pair[1]["value"] = PHYSICAL_BOUNDS_SCHEMA_V1
        if field_pair[0] == "min_temperature_k":
            field_pair[1] = {"type": "none"}
    with pytest.raises(ValueError, match="D24.15"):
        request_from_payload(payload)


# -- W-WIRE P3: a legacy-loaded v0.8 response is read-only evidence ---------------------------------------------------

@pytest.mark.parametrize("name", ["response_isopentyl_acetate.json", "response_stereo_isopentyl_acetate_smiles.json",
                                  "response_isopentyl_acetate_dag.json", "response_invalid_input_ethyl_acetate_name.json"])
def test_re_serializing_a_legacy_loaded_response_is_refused_not_emitted_with_0_9_keys(name):
    """Pre-fix, ``response_to_payload`` on a migrated v0.8 response emitted the CURRENT shape -- 0.9-only keys
    (capability_question_digest, capability_assessment, capability_profile*, replay material_uses) under the v1alpha15
    id, a payload the loader itself refuses as smuggling.  Now it refuses with a precise 'recompile' error; no v0.8-id
    payload carrying a 0.9-only key can be minted by this codec."""
    legacy = response_from_payload(_load(name))
    assert legacy.is_legacy_v08
    for include_replay in (True, False):
        with pytest.raises(ValueError, match=r"legacy v0\.8 response; recompile under 0\.9"):
            response_to_payload(legacy, include_replay=include_replay)
    with pytest.raises(ValueError, match=r"legacy v0\.8 response; recompile under 0\.9"):
        serialize_response(legacy)
    # the recompile the refusal points at works and is a CURRENT response
    fresh = run_compilation(build_recompile_request(legacy.request.target_input,
                                                    input_kind=legacy.request.input_kind, max_depth=1))
    assert not fresh.is_legacy_v08 and response_to_payload(fresh)["schema_version"] == COMPILATION_RESPONSE_SCHEMA


# -- D25.3 (Wave-C'' NEW-3): the IR's candidate set is bound to the carried search receipt ---------------------------

def _delete_route_everywhere(resp, *, rewrite_receipt=False):
    """Masters' NEW-3 attacker: drop dossier 0 AND its IR route candidate AND its frontier entry (all public pins are
    recomputed by the public codec). ``rewrite_receipt`` additionally rewrites the IR receipt's ``results_returned`` --
    the consistent rewrite D25.3 names as its stated boundary.  The frontier is rebuilt the way a CONSISTENT forger must
    since X-high D27.4 (which re-derives it on load): the producer's own ``_route_frontier`` over the remaining routes
    (the frontier is set-relative -- deleting a dominating route can change it)."""
    gone = resp.ranked_route_dossiers[0].route_digest
    ir = dc.replace(resp.compilation_ir, candidates=tuple(
        c for c in resp.compilation_ir.candidates if c.candidate_digest != gone))
    if rewrite_receipt:
        ir = dc.replace(ir, search_receipt=dc.replace(ir.search_receipt,
                                                      results_returned=ir.search_receipt.results_returned - 1))
    keep = resp.ranked_route_dossiers[1:]
    routes = tuple(svc._reconstruct_route(d.replay_payload) for d in keep)
    forged = copy.copy(resp)
    object.__setattr__(forged, "compilation_ir", ir)
    object.__setattr__(forged, "ranked_route_dossiers", keep)
    object.__setattr__(forged, "affordability_frontier", svc._route_frontier(resp.request, routes, keep))
    return response_to_payload(forged)


def test_new3_deleting_a_route_with_its_ir_candidate_and_frontier_entry_is_refused():
    """Pre-D25.3 the deletion loaded under the request pin + question pin + verified admission with the BLOCKED verdict
    gone, while the carried receipt still said the search returned one more route."""
    resp = _run("poor-man")
    assert resp.compilation_ir.search_receipt.results_returned == len(resp.ranked_route_dossiers) >= 2
    with pytest.raises(ValueError, match=r"D25\.3"):
        response_from_payload(_delete_route_everywhere(resp), expected_request_digest=resp.request.semantic_digest,
                              expected_capability_question_digest=resp.request.capability_question_digest,
                              require_verified_admission=True)


def test_new3_the_consistent_receipt_rewrite_boundary_documented():
    """The STATED boundary of D25.3 (audit §7.8): a keyless attacker who ALSO rewrites the carried receipt's
    ``results_returned`` (and, since D27.4, rebuilds the frontier with the producer's own function) produces a
    self-consistent smaller answer that loads on a plain keyless load -- detectable only by the producer HMAC (whose
    signed digest now covers the whole body, D27.2) or by re-running the deterministic search (``require_reexecution``,
    D26.2). Pinned so the boundary is explicit, not accidental."""
    resp = _run("poor-man")
    loaded = response_from_payload(_delete_route_everywhere(resp, rewrite_receipt=True),
                                   expected_request_digest=resp.request.semantic_digest,
                                   expected_capability_question_digest=resp.request.capability_question_digest)
    assert len(loaded.ranked_route_dossiers) == len(resp.ranked_route_dossiers) - 1


def test_d25_3_every_honest_routes_mode_response_satisfies_the_receipt_bind():
    for profile in (None, "poor-man", "research-lab"):
        resp = _run(profile)
        routes = [c for c in resp.compilation_ir.candidates if c.candidate_kind == "ROUTE"]
        assert len(routes) == resp.compilation_ir.search_receipt.results_returned
    for name in ("response_isopentyl_acetate.json", "response_ethyl_acetate_smiles.json",
                 "response_stereo_isopentyl_acetate_smiles.json", "response_isopentyl_acetate_dag.json"):
        response_from_payload(_load(name))  # real v0.8 producer output still loads under D25.3


# =====================================================================================================================
# D26 (Wave-C'' transport attacker T) -- a response must answer ITS request; opt-in keyless authenticity by determinism
# =====================================================================================================================

_Y = "smiles:CCOC(C)=O"  # ethyl acetate: the SECOND small search the transplant attacks carry under request X


def _bypass(resp, **fields):
    """The keyless attacker's in-memory forgery: a copy with fields swapped, never re-running __post_init__ (the loader,
    not the constructor, is the trust boundary under test)."""
    forged = copy.copy(resp)
    for name, value in fields.items():
        object.__setattr__(forged, name, value)
    return forged


def _pins(request):
    return dict(expected_request_digest=request.semantic_digest,
                expected_capability_question_digest=request.capability_question_digest)


def test_d26_1_t1_a_transplanted_answer_to_a_different_target_is_refused():
    """T1 (P0 shape): request X carrying search Y's IR + dossiers, every public pin recomputed, loaded under the request
    pin + the question pin + verified admission. Pre-D26.1 it LOADED (the attack carried a PROCESS_SPECIFIED isopentyl
    route under a methyl-acetate request)."""
    x, y = _run("poor-man"), run_compilation(build_recompile_request(_Y, capability_profile="poor-man", max_depth=2))
    payload = response_to_payload(_bypass(y, request=x.request))
    with pytest.raises(ValueError, match=r"target identity.*refused \(D26\.1\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(x.request))


def test_d26_1_t1c_a_cosmetic_transplant_is_caught_at_the_replayed_route():
    """T1c: as T1 but every request-derived IR field is copied from the honest answer to X (target, request/terminal
    digests, receipt digests) -- only the REPLAYED routes still make Y's product. The IR's diagnostics stay Y's: since
    X-high D28.2 they are re-derived from the IR's OWN search status, so copying X's would only be a sloppier forgery
    that D28.2 refuses first."""
    x, y = _run("poor-man"), run_compilation(build_recompile_request(_Y, capability_profile="poor-man", max_depth=2))
    irx, iry = x.compilation_ir, y.compilation_ir
    receipt = dc.replace(iry.search_receipt, target_identity_digest=irx.search_receipt.target_identity_digest,
                         terminal_policy_digest=irx.search_receipt.terminal_policy_digest)
    ir = dc.replace(iry, target=irx.target, request_digest=irx.request_digest,
                    terminal_policy_digest=irx.terminal_policy_digest, search_receipt=receipt)
    payload = response_to_payload(_bypass(y, request=x.request, compilation_ir=ir))
    with pytest.raises(ValueError, match=r"does not make the requested target; refused \(D26\.1\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(x.request))


def test_d26_1_t4b_a_decompile_request_cannot_carry_a_recompile_answer():
    x = _run(None)
    dreq = svc.build_decompile_request("C3H6O2")
    # X-high D27.6 (a construction-time law) now catches the transplanted recompile receipt's kind / bounds first;
    # D26.1's operation check stays behind it as the load-time layer.
    with pytest.raises(ValueError, match=r"the IR answers a RECOMPILE but the carried request is a DECOMPILE.*D26\.1|"
                                         r"DIFFERENT search; refused \(D27\.6\)|relabelled receipt; refused \(D27\.6\)"):
        response_from_payload(response_to_payload(_bypass(x, request=dreq)), **_pins(dreq))


def test_d26_1_t3_a_linear_capability_question_answered_by_a_dag_search_is_refused():
    """T3: a linear-grammar poor-man request answered with a convergent-DAG search's IR (registry digest relabelled to
    the linear algebra's -- both public) and DAG dossiers: zero capability assessments. Pre-D26.1 it bypassed D24.13."""
    dag = run_compilation(build_recompile_request(_TARGET, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
                                                  max_depth=2, process=ProcessBounds.quick()))
    lreq = build_recompile_request(_TARGET, max_depth=2, process=ProcessBounds.quick(), capability_profile="poor-man")
    lin = svc.search_algebra_digest(svc._GRAMMAR_TO_MODE_TOPOLOGY["routes"],
                                    svc.resolve_algebra_profile(lreq.algebra_profile))
    # the forger relabels the receipt's search KIND too (X-high D27.6/D27.8 refuses the inconsistent one at
    # construction), so D26.1's candidate-kind law is the layer this test pins
    for kind, law in (("LINEAR_ROUTE", r"refused \(D26\.1\)"), ("CONVERGENT_DAG", r"relabelled receipt; refused \(D27\.6\)")):
        ir = dc.replace(dag.compilation_ir, transform_registry_digest=lin,
                        search_receipt=dc.replace(dag.compilation_ir.search_receipt, transform_registry_digest=lin,
                                                  search_kind=kind))
        with pytest.raises(ValueError, match=law):
            response_from_payload(response_to_payload(_bypass(dag, request=lreq, compilation_ir=ir)),
                                  require_verified_admission=True, **_pins(lreq))


def test_d26_1_t6a_the_legacy_transplant_is_refused_with_the_recompile_hint():
    """T6a: the REAL v0.8 ethyl-acetate request wrapped around the REAL v0.8 isopentyl IR + dossiers, only the derived
    fields recomputed under the frozen v0.8 rule."""
    iso, eth = _load("response_isopentyl_acetate.json"), _load("response_ethyl_acetate_smiles.json")
    forged = copy.deepcopy(iso)
    forged["request"] = copy.deepcopy(eth["request"])
    r = svc.CompilationResponse(
        forged["schema_version"], request_from_payload(forged["request"]), svc.ResponseOutcome(forged["outcome"]),
        forged["standard_status"], svc.ir_from_payload(forged["compilation_ir"]), tuple(forged["diagnostics"]),
        tuple(svc.ranked_summary_from_payload(x) for x in forged["ranked_route_dossiers"]),
        tuple(svc.affordability_entry_from_payload(e) for e in forged["affordability_frontier"]),
        parse_receipt_summary=forged["parse_receipt_summary"])
    forged["exit_code"] = r.exit_code
    forged["process_selection_status"] = r.process_selection_status
    forged["admissible_route_digests"] = list(r.admissible_route_digests)
    forged["result_digest"] = svc._transport_bound_result_digest(r.result_digest,
                                                                 forged.get("transport_mode", "THIN_ADVISORY"))
    with pytest.raises(ValueError, match=r"refused \(D26\.1\).*legacy v0\.8 payload"):
        response_from_payload(forged, require_verified_admission=True,
                              expected_request_digest=request_from_payload(eth["request"]).semantic_digest,
                              expected_capability_question_digest=None)


def test_d26_1_honest_recompile_decompile_and_every_real_v08_fixture_still_load():
    for resp in (_run(None), _run("poor-man"), run_compilation(svc.build_decompile_request("C3H6O2"))):
        response_from_payload(response_to_payload(resp), require_verified_admission=True, **_pins(resp.request))
    for name in ("response_isopentyl_acetate.json", "response_ethyl_acetate_smiles.json",
                 "response_ethyl_acetate_smiles_thin.json", "response_stereo_isopentyl_acetate_smiles.json",
                 "response_isopentyl_acetate_dag.json", "response_invalid_input_ethyl_acetate_name.json"):
        response_from_payload(_load(name))
    response_from_payload(_load("plan_isopentyl_acetate.json")["compilation"])


def test_d26_1_a_decompile_answer_for_a_different_formula_is_refused():
    other = run_compilation(svc.build_decompile_request("C3H6O2"))
    asked = svc.build_decompile_request("C2H4O2")
    with pytest.raises(ValueError, match=r"target identity.*refused \(D26\.1\)"):
        response_from_payload(response_to_payload(_bypass(other, request=asked)), **_pins(asked))


def _no_route_relabel(resp):
    """T2b: delete EVERY candidate and relabel the search COMPLETE -- a forged 'no route in the declared space'. The
    CONSISTENT forger also writes the producer's own no-route diagnostic (X-high D28.2 re-derives it; the rule is the
    public helper, so omitting the line would only be a sloppier forgery)."""
    from smartchem.compilation_ir import recompile_ir_diagnostics
    from smartchem.search import SearchStatus

    ir, req = resp.compilation_ir, resp.request
    receipt = dc.replace(ir.search_receipt, status=SearchStatus.COMPLETE_WITHIN_BOUNDS.value,
                         standard_status=SearchStatus.COMPLETE_WITHIN_BOUNDS.standard_name, results_returned=0,
                         candidate_enumeration_complete=True, cut_enumeration_complete=True,
                         result_limit_saturated=False, stop_reason="")
    diagnostics = recompile_ir_diagnostics(
        target_in_terminal_stock=False, complete_within_bounds=True, status_value=receipt.status,
        has_candidates=False, mode=svc._GRAMMAR_TO_MODE[req.transform_grammar],
        max_depth=req.search_bounds.value("max_depth"))
    ir3 = dc.replace(ir, candidates=(), search_status=SearchStatus.COMPLETE_WITHIN_BOUNDS,
                     standard_status=SearchStatus.COMPLETE_WITHIN_BOUNDS.standard_name, search_receipt=receipt,
                     diagnostics=diagnostics)
    return response_to_payload(_bypass(resp, compilation_ir=ir3, ranked_route_dossiers=(), affordability_frontier=(),
                                       outcome=svc.ResponseOutcome.NO_ROUTE_COMPLETE,
                                       standard_status=ir3.standard_status, diagnostics=diagnostics))


def test_d26_2_t2_a_consistent_deletion_loads_without_reexecution_and_is_refused_with_it():
    """T2 + D25.3's stated boundary: a keyless attacker who deletes routes AND consistently rewrites the carried receipt
    produces a self-consistent smaller answer; only re-running the deterministic search (D26.2) sees it."""
    resp = _run("poor-man")
    for payload in (_no_route_relabel(resp), _delete_route_everywhere(resp, rewrite_receipt=True)):
        response_from_payload(payload, **_pins(resp.request))                      # the documented boundary: loads
        with pytest.raises(ValueError, match=r"re-running the carried request produces a DIFFERENT result.*D26\.2"):
            response_from_payload(payload, require_reexecution=True, **_pins(resp.request))


def test_d26_2_t5_a_re_centred_step_demoting_under_the_same_route_digest_is_refused_on_every_load():
    """T5 / D26.4: ``reaction_center`` is compare=False (outside route.digest) yet feeds readiness. Re-centring the
    REACTION_VOUCHED methyl-acetate route and honestly re-deriving its readiness + capability DEMOTES it under the SAME
    route digest; on adf06ae it loaded under every pin (the then-stated D26.4 boundary) and only ``require_reexecution``
    refused it. X-high D29.1 closes the boundary: the centre must be one the carried algebra assigns."""
    from smartchem.capability.assess import assess as assess_capability
    from smartchem.capability.requirements import compile_capability_requirements

    resp = _run("poor-man")
    new = []
    demoted = 0
    for d in resp.ranked_route_dossiers:
        replay = copy.deepcopy(d.replay_payload)
        centred = [i for i, step in enumerate(replay) if step.get("reaction_center")]
        if d.readiness.tier != "FORMAL_CANDIDATE" and centred:
            replay[centred[0]]["reaction_center"]["n_components"] = 2
            route = _reconstruct_route(replay)
            assert route.digest == d.route_digest
            ready = evaluate_route(route, identity_losses=resp.identity_losses)
            assert tier_rank(ready.tier) < tier_rank(d.readiness.tier)            # a DEMOTION, same route digest
            demoted += 1
            d = dc.replace(d, readiness=ready, replay_payload=replay, capability_assessment=assess_capability(
                resp.request.capability_profile, compile_capability_requirements(route), ready))
        new.append(d)
    assert demoted
    routes_ = tuple(_reconstruct_route(d.replay_payload) for d in new)
    frontier = svc._affordability_frontier(routes_, tuple(new))
    payload = response_to_payload(_bypass(resp, ranked_route_dossiers=tuple(new), affordability_frontier=frontier))
    # the D26.4 boundary CLOSED by X-high D29.1: the centre stays outside route.digest, but it is now one the carried
    # algebra assigns to the step's transform -- refused on every load, not only under re-execution
    for kw in (dict(require_verified_admission=True), dict(require_reexecution=True)):
        with pytest.raises(ValueError, match=r"re-centred replay; refused \(D29\.1\)"):
            response_from_payload(copy.deepcopy(payload), **kw, **_pins(resp.request))


def test_d26_2_reexecution_accepts_an_honest_answer_and_refuses_a_legacy_one():
    resp = _run("poor-man")
    response_from_payload(response_to_payload(resp), require_reexecution=True, **_pins(resp.request))
    deserialize_response(serialize_response(resp), require_reexecution=True)
    with pytest.raises(ValueError, match=r"cannot re-execute a legacy v0\.8 payload.*D26\.2.*recompile under 0\.9"):
        response_from_payload(_load("response_ethyl_acetate_smiles.json"), require_reexecution=True)


def test_d26_3_t4a_a_capability_profile_on_a_decompile_request_is_refused():
    """T4a: the honest producer answered a DECOMPILE + profile with NOTHING (no route, no assessment)."""
    with pytest.raises(ValueError, match=r"DECOMPILE.*D26\.3"):
        dc.replace(svc.build_decompile_request("C7H14O2"), capability_profile=poor_man(),
                   capability_profile_origin=poor_man().profile_id)


def test_d26_5_t6b_a_legacy_request_is_not_re_serialized_with_0_9_keys():
    legacy = svc.deserialize_request(json.dumps(_load("request_isopentyl_acetate.json")))
    assert legacy.is_legacy_v08
    with pytest.raises(ValueError, match=r"legacy v0\.8 request.*\(D26\.5\)"):
        svc.serialize_request(legacy)


def _find_node(tree, cls):
    stack = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("class") == cls:
                return node
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    raise AssertionError(cls)


def test_d26_6_b5_a_canonical_node_missing_a_field_is_refused_not_default_filled():
    payload = request_to_payload(build_recompile_request(_TARGET, max_depth=2, capability_profile="poor-man"))
    profile = copy.deepcopy(payload["capability_profile"])
    box = _find_node(profile, "smartchem.constraints.PhysicalBounds")
    box["fields"] = [f for f in box["fields"] if f[0] != "min_temperature_k"]
    with pytest.raises(ValueError, match=r"EXACTLY its fields.*\(D26\.6\)"):
        svc._capability_profile_from_payload(profile)
    extra = copy.deepcopy(payload["capability_profile"])
    extra["fields"].append(["smuggled", {"type": "none"}])
    with pytest.raises(ValueError, match=r"D26\.6"):
        svc._capability_profile_from_payload(extra)


def test_d26_7_rc_v_a_reaction_centre_payload_of_another_version_is_refused():
    from smartchem.reaction_center import REACTION_CENTER_SCHEMA, ReactionCenter, ReactionCenterError

    good = ReactionCenter.of((("C", "O", 1),), (("C", "O", 1),), 1).to_payload()
    assert ReactionCenter.from_payload(good).schema_version == REACTION_CENTER_SCHEMA
    with pytest.raises(ReactionCenterError, match=r"D26\.7"):
        ReactionCenter.from_payload(dict(good, schema_version="smartchem/reaction-center-v0-bogus"))


# =====================================================================================================================
# D27 (Wave C4 transport attacker C4T-1..8 + the Foreman acceptance probes N2-N4) -- the structural transport closure.
# Every forgery is KEYLESS and built with the producer's OWN public-by-import helpers.  In each test the FIRST
# assertion is the load that SUCCEEDED on 944baea (the discriminating half); helpers that exist only since D27 are
# imported after it, so the test fails on 944baea for the attack's reason, not an ImportError.
# =====================================================================================================================

_BENCH_KW = dict(helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",))
_PROCESS_KW = dict(helper_reagents=("water", "acetic acid"), process=ProcessBounds.of(max_total_minutes=30.0))
_KEY = b"x-high-d27-regression-test-key-32"
_FORGED_SNAPSHOT = {"schema_version": "smartchem.data/provider-snapshot-v1alpha1", "provider_ids": ["pubchem"],
                    "record_count": 3, "content_digest": "0" * 64, "fetched_at": "2026-09-28T00:00:00Z",
                    "allow_network": True}


def _bench_run():
    """Methyl acetate against the fully-declared isopentyl bench (the Wave C4 attacker's X: three ranked routes)."""
    return _run(isopentyl_capability_fit_bench(), **_BENCH_KW)


def _dag_run():
    return run_compilation(build_recompile_request(_TARGET, max_depth=2, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
                                                   **_PROCESS_KW))


def _raw_edit(payload, edit):
    """The wire attacker who edits the JSON and recomputes NOTHING."""
    forged = copy.deepcopy(payload)
    edit(forged)
    return forged


def _isopentyl_corpus_envelope():
    """The shipped corpus's sourced, procedure-bearing isopentyl-acetate esterification envelope (the C4T-1 donor)."""
    from smartchem.structure import structure_by_name

    def mol(name):
        return structure_by_name(name).molecule

    result = routes.search_routes(mol("isopentyl acetate"), reagents=(mol("water"), mol("acetic acid")),
                                  available=(mol("isopentyl alcohol"),), max_depth=1)
    return next(r.steps[0].envelope for r in result.routes if r.steps[0].envelope.procedure is not None)


def _legacy_refresh(wire):
    """Recompute a hand-patched LEGACY wire's derived fields under the FROZEN v0.8 rule, exactly as the loader
    reconstructs them (``response_to_payload`` refuses to emit legacy, so the attacker patches JSON)."""
    r = svc.CompilationResponse(
        wire["schema_version"], request_from_payload(wire["request"]), svc.ResponseOutcome(wire["outcome"]),
        wire["standard_status"], svc.ir_from_payload(wire["compilation_ir"]), tuple(wire["diagnostics"]),
        tuple(svc.ranked_summary_from_payload(x) for x in wire["ranked_route_dossiers"]),
        tuple(svc.affordability_entry_from_payload(e) for e in wire["affordability_frontier"]),
        parse_receipt_summary=wire["parse_receipt_summary"])
    wire["exit_code"] = r.exit_code
    wire["process_selection_status"] = r.process_selection_status
    wire["admissible_route_digests"] = list(r.admissible_route_digests)
    wire["result_digest"] = svc._transport_bound_result_digest(r.result_digest, wire.get("transport_mode", "THIN_ADVISORY"))


def test_d27_1_c4t1_a_corpus_envelope_graft_is_refused_on_every_current_load():
    """C4T-1 (P0): graft the isopentyl corpus envelope onto methyl acetate's one-step esterification, then honestly
    re-derive EVERYTHING from the tampered route with the producer's own helpers (ranking, frontier, IR candidate
    digests). The route SHAPE is untouched, so D26.1 cannot see it; pre-D27.1 it loaded PROCESS_SPECIFIED under both
    pins + verified admission and only re-execution refused."""
    resp = _run(None)
    donor = _isopentyl_corpus_envelope()
    remap, replayed = {}, []
    for d in resp.ranked_route_dossiers:
        route = _reconstruct_route(d.replay_payload)
        if len(route.steps) == 1:
            grafted = dc.replace(route, steps=(dc.replace(route.steps[0], envelope=donor),))
            remap[d.route_digest] = grafted.digest
            route = grafted
        replayed.append(route)
    assert remap, "setup: methyl acetate must have a one-step route to graft"
    ranked = svc._ranked_summaries(tuple(replayed), resp.request.constraints.bounds, resp.identity_losses)
    assert any(d.readiness.tier == PROCESS_SPECIFIED for d in ranked)            # the forged promotion
    ir = resp.compilation_ir
    candidates = tuple(sorted((dc.replace(c, candidate_digest=remap.get(c.candidate_digest, c.candidate_digest))
                               for c in ir.candidates), key=lambda c: c.candidate_digest))
    payload = response_to_payload(_bypass(resp, compilation_ir=dc.replace(ir, candidates=candidates),
                                          ranked_route_dossiers=ranked,
                                          affordability_frontier=svc._affordability_frontier(tuple(replayed), ranked)))
    with pytest.raises(ValueError, match=r"not the one the shipped corpus attaches.*refused \(D27\.1\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(resp.request))
    with pytest.raises(ValueError, match=r"D27\.1"):
        response_from_payload(payload)                                            # every current load, not only VA


def test_d27_1_c4t1_the_legacy_graft_is_refused_under_verified_admission_and_advisory_on_a_plain_load():
    """ATK10: the same graft on the REAL v0.8 ethyl-acetate fixture (frozen v0.8 digest rule; the donor cut to the
    v0.8-expressible shape). Pre-D27.1 it loaded under both pins + verified admission. D27.1's STATED legacy boundary:
    on a PLAIN load v0.8 evidence stays advisory (it is v0.8's corpus; nothing in 0.8 bound it)."""
    wire = _load("response_ethyl_acetate_smiles.json")
    honest = response_from_payload(copy.deepcopy(wire))
    victim = next(d for d in wire["ranked_route_dossiers"] if d["route_digest"].startswith("d2b8867e1930"))
    old = victim["route_digest"]
    step = _reconstruct_route(svc._migrate_legacy_v08_dossier(copy.deepcopy(victim))["replay_payload"]).steps[0]
    envelope = svc._steps_to_replay_payload((dc.replace(step, envelope=_isopentyl_corpus_envelope()),))[0]["envelope"]
    for op in envelope["procedure"]["operations"]:
        op.pop("material_uses", None)            # the only v0.8-expressible value is [] (the decoder re-adds it)
    envelope["procedure"].pop("stream_dispositions", None)   # 0.9.5 S10: likewise a 0.9-only slot (decoder re-adds [])
    victim["replay_payload"][0]["envelope"] = envelope
    route = _reconstruct_route(svc._migrate_legacy_v08_dossier(copy.deepcopy(victim))["replay_payload"])
    ready = evaluate_route(route, identity_losses=honest.identity_losses)
    assert ready.tier == PROCESS_SPECIFIED                                        # the forged promotion
    new = svc._v08_digest(route)
    victim.update(route_digest=new, readiness=svc._route_readiness_to_payload(ready), readiness_tier=ready.tier,
                  process_requirements=[svc._process_requirements_to_payload(s.envelope.process) for s in route.steps])
    for c in wire["compilation_ir"]["candidates"]:
        if c["candidate_digest"] == old:
            c["candidate_digest"] = new
    wire["compilation_ir"]["candidates"].sort(key=lambda c: c["candidate_digest"])
    for e in wire["affordability_frontier"]:
        if e["route_digest"] == old:
            e["route_digest"] = new
    _legacy_refresh(wire)
    with pytest.raises(ValueError, match=r"refused \(D27\.1\).*legacy v0\.8 payload.*recompile under 0\.9"):
        response_from_payload(copy.deepcopy(wire), require_verified_admission=True, **_pins(honest.request))
    loaded = response_from_payload(wire)                         # the documented legacy boundary: advisory, plain
    assert loaded.is_legacy_v08
    assert any(d.readiness.tier == PROCESS_SPECIFIED for d in loaded.ranked_route_dossiers)


def test_d27_2_c4t2_the_frontier_is_inside_the_wire_digest_the_hmac_and_reexecution():
    """C4T-2 (ATK1-delete): the affordability frontier rode OUTSIDE result_digest, so a deleted frontier loaded even
    under the producer HMAC + require_signature + both pins + verified admission + re-execution."""
    resp = _bench_run()
    assert resp.affordability_frontier
    signed = response_to_payload(resp, signing_key=_KEY)
    deleted = _raw_edit(signed, lambda w: w.update(affordability_frontier=[]))
    with pytest.raises(ValueError, match=r"result_digest does not match"):
        response_from_payload(deleted, verification_key=_KEY, require_signature=True, **_pins(resp.request))
    from smartchem.service import _payload_body_digest

    # the keyless forger recomputes the PUBLIC wire digest: the HMAC refuses it ...
    deleted["result_digest"] = svc._transport_bound_result_digest(resp.result_digest, deleted["transport_mode"],
                                                                  _payload_body_digest(deleted))
    with pytest.raises(ValueError, match=r"producer_signature does not verify"):
        response_from_payload(deleted, verification_key=_KEY, require_signature=True, **_pins(resp.request))
    # ... and, keyless, the canonical wire re-derives the frontier on load (D27.4) ...
    with pytest.raises(ValueError, match=r"affordability_frontier is not the producer's frontier.*D27\.4"):
        response_from_payload(deleted)
    # ... while the THIN wire (no replay to re-derive from) keeps it advisory on a plain load -- the stated residual --
    # and re-execution refuses it (D27.2: the rerun's body is compared, not just the result identity).
    thin = response_to_payload(_bypass(resp, affordability_frontier=()), include_replay=False)
    response_from_payload(thin, **_pins(resp.request))
    with pytest.raises(ValueError, match=r"differs from the re-executed one in \['affordability_frontier'\].*D27\.2"):
        response_from_payload(thin, require_reexecution=True, **_pins(resp.request))


def test_d27_3_c4t3_a_routes_found_answer_relabelled_target_already_available_is_refused():
    """C4T-3 (ATK2a): ROUTES_FOUND relabelled TARGET_ALREADY_AVAILABLE (exit 0, "on the shelf") although the target is
    not in the request's declared terminal set."""
    req = build_recompile_request("smiles:COC", max_depth=1)
    honest = run_compilation(req)
    assert honest.outcome is svc.ResponseOutcome.ROUTES_FOUND
    payload = response_to_payload(dc.replace(honest, outcome=svc.ResponseOutcome.TARGET_ALREADY_AVAILABLE))
    with pytest.raises(ValueError, match=r"NOT in the declared terminal set.*refused \(D27\.3\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(req))
    # control: the honest TARGET_ALREADY_AVAILABLE answer (the target IS a declared helper) still loads
    shelf = run_compilation(build_recompile_request("smiles:CC(=O)O", max_depth=1,
                                                    helper_reagents=("water", "acetic acid")))
    assert shelf.outcome is svc.ResponseOutcome.TARGET_ALREADY_AVAILABLE
    response_from_payload(response_to_payload(shelf), require_verified_admission=True, **_pins(shelf.request))


def test_d27_4_c4t4_a_reordered_ranking_is_refused():
    """C4T-4 (ATK4a): the ranking reversed (the REACTION_VOUCHED route last), the frontier rebuilt over it."""
    resp = _bench_run()
    reordered = tuple(reversed(resp.ranked_route_dossiers))
    replayed = tuple(_reconstruct_route(d.replay_payload) for d in reordered)
    payload = response_to_payload(_bypass(resp, ranked_route_dossiers=reordered,
                                          affordability_frontier=svc._affordability_frontier(replayed, reordered)))
    with pytest.raises(ValueError, match=r"not the producer's ranking of the replayed routes.*refused \(D27\.4\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(resp.request))


def test_d27_4_n3_dossiers_judged_under_no_box_carried_under_a_280k_ceiling_are_refused_without_reexecution():
    """Foreman N3: Y's dossiers (no box: fit UNCONSTRAINED) carried under a request with a 280 K ceiling (honest fit:
    UNKNOWN) -- the IR request_digest does not cover the section-11 box, so pre-D27.4 only re-execution refused."""
    y = _run(None)
    assert "UNCONSTRAINED" in {d.fit_status for d in y.ranked_route_dossiers}
    x = build_recompile_request(_TARGET, max_depth=2, max_temperature_k=280.0)
    payload = response_to_payload(_bypass(y, request=x))
    with pytest.raises(ValueError, match=r"not the producer's ranking of the replayed routes.*refused \(D27\.4\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(x))
    honest = run_compilation(x)                                                   # control: the honest 280 K answer
    assert {d.fit_status for d in honest.ranked_route_dossiers} == {"UNKNOWN"}
    response_from_payload(response_to_payload(honest), require_verified_admission=True, **_pins(x))


def test_d27_5_c4t5_deleting_a_dag_or_a_formula_edge_is_refused_by_the_receipt_count():
    """C4T-5 (ATK5a / ATK6c): D25.3 skipped DAG and decompile answers on the false premise that their receipts count
    edges; they count DAGs / emitted edges, one candidate each."""
    hd = _dag_run()
    ir = hd.compilation_ir
    assert ir.search_receipt.results_returned == len(ir.candidates) >= 2          # the premise D25.3 denied
    victim = ir.candidates[0].candidate_digest
    payload = response_to_payload(_bypass(hd, compilation_ir=dc.replace(ir, candidates=ir.candidates[1:]),
                                          ranked_dag_dossiers=tuple(d for d in hd.ranked_dag_dossiers
                                                                    if d.route_digest != victim)))
    with pytest.raises(ValueError, match=r"search receipt says the search returned .*refused \(D25\.3/D27\.5\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(hd.request))
    dq = svc.build_decompile_request("C2H6O")
    hdc = run_compilation(dq)
    assert hdc.compilation_ir.search_receipt.results_returned == len(hdc.compilation_ir.candidates) == 1
    payload = response_to_payload(_bypass(hdc, compilation_ir=dc.replace(hdc.compilation_ir, candidates=()),
                                          outcome=svc.ResponseOutcome.NO_ROUTE_COMPLETE))
    with pytest.raises(ValueError, match=r"FORMULA_DECOMPOSITION search receipt says.*refused \(D25\.3/D27\.5\)"):
        response_from_payload(payload, **_pins(dq))


def test_d27_6_c4t6_n2_the_receipt_bounds_and_every_route_depth_are_the_requests():
    """C4T-6 (ATK5c) + Foreman N2: the receipt's search bounds were never compared with the request -- an inflated
    receipt loaded, and a max_depth=1 request carried a depth-2 answer under both pins + verified admission."""
    y = _run(None)
    ir = y.compilation_ir
    inflated = dc.replace(ir, search_receipt=dc.replace(ir.search_receipt, max_depth=12, cut_budget=10**7,
                                                        result_limit=10**4))
    with pytest.raises(ValueError, match=r"search receipt reports bounds .* DIFFERENT search; refused \(D27\.6\)"):
        response_from_payload(response_to_payload(_bypass(y, compilation_ir=inflated)),
                              require_verified_admission=True, **_pins(y.request))
    x1 = build_recompile_request(_TARGET, max_depth=1)
    assert max(len(d.replay_payload) for d in y.ranked_route_dossiers) == 2
    ir1 = dc.replace(ir, request_digest=svc._rederive_request_context(x1).request_digest)
    with pytest.raises(ValueError, match=r"refused \(D27\.6\)"):
        response_from_payload(response_to_payload(_bypass(y, request=x1, compilation_ir=ir1)),
                              require_verified_admission=True, **_pins(x1))
    # the receipt ALSO rewritten to depth 1: the replayed 2-step route is itself the tell (the linear search never
    # emits a route longer than max_depth)
    ir1b = dc.replace(ir1, search_receipt=dc.replace(ir.search_receipt, max_depth=1))
    with pytest.raises(ValueError, match=r"replayed route has 2 steps .* max_depth=1 .*refused \(D27\.6\)"):
        response_from_payload(response_to_payload(_bypass(y, request=x1, compilation_ir=ir1b)),
                              require_verified_admission=True, **_pins(x1))


@pytest.mark.parametrize("relabel", [dict(search_kind="CONVERGENT_DAG"), dict(cut_budget_scope="GLOBAL")])
def test_d27_8_the_receipt_kind_and_budget_scope_describe_the_requests_search(relabel):
    """Found by the D27.8 ledger audit: the receipt's ``search_kind`` / ``cut_budget_scope`` were free labels (a
    linear answer's receipt relabelled a convergent-DAG search, or its per-node budget a global one, loaded under both
    pins + verified admission on 944baea)."""
    y = _run(None)
    ir = y.compilation_ir
    forged = dc.replace(ir, search_receipt=dc.replace(ir.search_receipt, **relabel))
    with pytest.raises(ValueError, match=r"relabelled receipt; refused \(D27\.6\)"):
        response_from_payload(response_to_payload(_bypass(y, compilation_ir=forged)),
                              require_verified_admission=True, **_pins(y.request))


def test_d27_8_the_wire_search_space_status_is_the_loaded_responses():
    """Found by the D27.8 ledger audit: the derived wire key ``search_space_status`` was never compared on load, so a
    JSON consumer could read NO_ROUTE_IN_DECLARED_SPACE on a routes-found answer -- on 944baea even a raw edit loaded
    (neither the wire digest nor any check covered the key). Now the raw edit is refused, and so is the keyless forger
    who recomputes the public D27.2 digest: the loader's derived-key round trip compares the key itself."""
    y = _run(None)
    wire = response_to_payload(y)
    assert wire["search_space_status"] != "NO_ROUTE_IN_DECLARED_SPACE"
    wire["search_space_status"] = "NO_ROUTE_IN_DECLARED_SPACE"
    with pytest.raises(ValueError, match=r"search_space_status does not match|result_digest does not match"):
        response_from_payload(copy.deepcopy(wire), **_pins(y.request))
    from smartchem.service import _payload_body_digest

    wire["result_digest"] = svc._transport_bound_result_digest(y.result_digest, wire["transport_mode"],
                                                               _payload_body_digest(wire))
    with pytest.raises(ValueError, match=r"search_space_status does not match the reconstructed response"):
        response_from_payload(wire, **_pins(y.request))


def test_d27_4_c4t7_a_forged_fit_tally_is_refused_on_the_canonical_and_the_thin_wire():
    """C4T-7 (ATK6b): the human-visible "N FIT" tally in the diagnostics rewritten. The canonical wire re-derives the
    whole note; the thin wire still re-derives the tally from the fit statuses it carries."""
    resp = _run(None, **_PROCESS_KW)
    note = next(x for x in resp.diagnostics if "section-11 constraint APPLIED" in x)
    fits, excluded, unknown = svc._fit_counts(resp.ranked_route_dossiers)
    honest_tally = f"{fits} FIT, {excluded} EXCLUDED (outside a hard bound), {unknown} UNKNOWN-fit"
    assert honest_tally in note and unknown
    lie = note.replace(honest_tally, f"{fits + unknown} FIT, {excluded} EXCLUDED (outside a hard bound), 0 UNKNOWN-fit")
    diagnostics = tuple(lie if x == note else x for x in resp.diagnostics)
    for include_replay in (True, False):
        payload = response_to_payload(_bypass(resp, diagnostics=diagnostics), include_replay=include_replay)
        with pytest.raises(ValueError, match=r"diagnostics .*refused \(D27\.4\)"):
            response_from_payload(payload, **_pins(resp.request))


def test_d27_7_c4t8_the_ir_candidate_label_is_its_dossiers():
    """C4T-8 (ATK2b): every IR candidate's free-text ``equation`` rewritten to the best route's (the dossiers and their
    replays untouched) -- the human render listed three identical 'CH4O + C2H4O2' candidates."""
    resp = _bench_run()
    ir = resp.compilation_ir
    best = resp.ranked_route_dossiers[0].equation
    candidates = tuple(dc.replace(c, equation=best) for c in ir.candidates)
    payload = response_to_payload(_bypass(resp, compilation_ir=dc.replace(ir, candidates=candidates)))
    with pytest.raises(ValueError, match=r"equation text that is not its dossier's.*refused \(D27\.7\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(resp.request))


def test_d27_7_c4t8_a_canonical_dossier_must_carry_its_replay():
    """C4T-8 (ATK8): on the CANONICAL_VERIFIED wire a FORMAL, no-profile dossier simply dropped its replay -- every
    replay-conditioned bind (D26.1's label, D27.1's evidence, D27.4's ranking) then had nothing to re-derive from."""
    resp = _run(None, **_PROCESS_KW)
    formal = next(d for d in resp.ranked_route_dossiers if d.readiness.tier == "FORMAL_CANDIDATE")
    stripped = tuple(dc.replace(d, replay_payload=None) if d is formal else d for d in resp.ranked_route_dossiers)
    payload = response_to_payload(_bypass(resp, ranked_route_dossiers=stripped))
    assert payload["transport_mode"] == "CANONICAL_VERIFIED"
    with pytest.raises(ValueError, match=r"canonical evidence must be re-derivable; refused \(D27\.7\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(resp.request))


def test_d27_2_c4t8_the_parse_receipt_provider_snapshots_and_dag_serial_holds_are_signed():
    """C4T-8 (ATK2c' / ATK11): the parse receipt, provider snapshots and DAG serial holds rode outside the signed
    digest -- each edit loaded under the producer HMAC + require_signature (+ re-execution)."""
    resp = _run(None)
    signed = response_to_payload(resp, signing_key=_KEY)
    for edit in (lambda w: w.update(parse_receipt_summary=f"{w['parse_receipt_summary']} (FORGED)"),
                 lambda w: w.update(provider_snapshots=[dict(_FORGED_SNAPSHOT)])):
        with pytest.raises(ValueError, match=r"result_digest does not match"):
            response_from_payload(_raw_edit(signed, edit), verification_key=_KEY, require_signature=True,
                                  **_pins(resp.request))
    hd = _dag_run()
    signed_dag = response_to_payload(hd, signing_key=_KEY)
    target = next(d for d in signed_dag["ranked_dag_dossiers"] if d["edges"])
    i, j = target["edges"][0]
    target["serial_holds"] = [[i, j, 99999.0]]
    with pytest.raises(ValueError, match=r"result_digest does not match"):
        response_from_payload(signed_dag, verification_key=_KEY, require_signature=True, **_pins(hd.request))


def test_d27_7_c4t8_an_unpinned_payload_cannot_choose_a_larger_search_for_its_verifier(monkeypatch):
    """C4T-8 (ATK7): without a request pin, ``require_reexecution`` ran whatever search the PAYLOAD declared (receipt
    and IR request digest made consistent via the public helper) before refusing -- payload-chosen work."""
    resp = _run(None)
    bigger = dc.replace(resp.request, search_bounds=svc.SearchBounds.of(
        **dict(dict(resp.request.search_bounds.bounds), max_depth=6)))
    ir = resp.compilation_ir
    ir6 = dc.replace(ir, request_digest=svc._rederive_request_context(bigger).request_digest,
                     search_receipt=dc.replace(ir.search_receipt, max_depth=6))
    payload = response_to_payload(_bypass(resp, request=bigger, compilation_ir=ir6))

    def _no_rerun(request):
        raise AssertionError(f"the verifier ran a payload-chosen search (max_depth="
                             f"{request.search_bounds.value('max_depth')})")

    monkeypatch.setattr(svc, "run_compilation", _no_rerun)
    with pytest.raises(ValueError, match=r"did not pin the request.*refused \(D27\.7\)"):
        response_from_payload(payload, require_reexecution=True)
    # a consumer who PINS the request chose that search itself: the guard stands aside and the rerun is attempted
    with pytest.raises(AssertionError, match="payload-chosen search"):
        response_from_payload(payload, require_reexecution=True, expected_request_digest=bigger.semantic_digest)


def test_d27_2_n4_a_neutral_re_centre_is_refused_on_the_wire_and_under_reexecution():
    """Foreman N4 / T5n: ``replay_payload`` is compare=False (outside the result identity), so a NEUTRAL re-centre
    (step 2 of the FORMAL route: readiness unchanged) passed even require_reexecution on 944baea, and a raw wire edit
    loaded on a plain load. D27.2: the thick replay rides the whole-body wire digest."""
    resp = _run(None)
    k, formal = next((i, d) for i, d in enumerate(resp.ranked_route_dossiers) if len(d.replay_payload) == 2)

    def recentre(replay):
        replay[1]["reaction_center"]["n_components"] += 1

    raw = _raw_edit(response_to_payload(resp), lambda w: recentre(w["ranked_route_dossiers"][k]["replay_payload"]))
    with pytest.raises(ValueError, match=r"result_digest does not match"):
        response_from_payload(raw, **_pins(resp.request))
    # the keyless forger who recomputes the public digest: the centre is outside route.digest and the re-centre is
    # NEUTRAL (same readiness).  On adf06ae it loaded on a plain / verified-admission load (the then-stated boundary)
    # and only re-execution refused it; X-high D29.1 binds the centre to the one the carried algebra assigns, so it is
    # refused on EVERY load now.
    replay = copy.deepcopy(formal.replay_payload)
    recentre(replay)
    assert _reconstruct_route(replay).digest == formal.route_digest
    assert evaluate_route(_reconstruct_route(replay), identity_losses=resp.identity_losses) == formal.readiness
    forged = dc.replace(resp, ranked_route_dossiers=tuple(
        dc.replace(d, replay_payload=replay) if d is formal else d for d in resp.ranked_route_dossiers))
    payload = response_to_payload(forged)
    for kw in ({}, dict(require_verified_admission=True), dict(require_reexecution=True)):
        with pytest.raises(ValueError, match=r"re-centred replay; refused \(D29\.1\)"):
            response_from_payload(copy.deepcopy(payload), **kw, **_pins(resp.request))



# =====================================================================================================================
# D28 (Wave C5 transport-ledger audit C5-F1..F7) -- the ledger made truthful.  Every forgery is KEYLESS: an in-memory
# swap built with the producer's own helpers (``_bypass``), or a JSON edit whose public whole-body digest is recomputed
# with the loader's OWN constructor (``_keyless_redigest``, the Wave C5 architect's ``forge.redigest``).  Each test's
# forgery LOADED on fc710a8 (measured against a pristine ``git archive fc710a8`` tree); D28-only names are imported
# inside the tests, so on fc710a8 each fails for the attack's reason.
# =====================================================================================================================

_MESAL = "smiles:COC(=O)c1ccccc1O"            # methyl salicylate: its esterification carries a sourced corpus record
_ASPIRIN = "smiles:CC(=O)Oc1ccccc1C(=O)O"


def _keyless_redigest(p):
    """Recompute the PUBLIC wire digest of an edited JSON payload exactly as the loader will (its own constructor, the
    D27.2 whole-body digest).  Under D28 a decoder / constructor may refuse the edit right here -- which is the point."""
    ir = p["compilation_ir"]
    base = svc.CompilationResponse(
        p["schema_version"], request_from_payload(p["request"]), svc.ResponseOutcome(p["outcome"]),
        p["standard_status"], None if ir is None else svc.ir_from_payload(ir), tuple(p["diagnostics"]),
        tuple(svc.ranked_summary_from_payload(r) for r in p["ranked_route_dossiers"]),
        tuple(svc.affordability_entry_from_payload(e) for e in p["affordability_frontier"]),
        tuple(svc.provider_snapshot_from_payload(s) for s in p.get("provider_snapshots", [])),
        parse_receipt_summary=p["parse_receipt_summary"],
        ranked_dag_dossiers=tuple(ranked_dag_summary_from_payload(d) for d in p.get("ranked_dag_dossiers", [])),
    ).result_digest
    p["result_digest"] = svc._transport_bound_result_digest(base, p["transport_mode"], svc._payload_body_digest(p))
    return p


def _keyless_load(payload, edit, **kw):
    """Edit a COPY of an honest wire, recompute every public digest, load it."""
    forged = copy.deepcopy(payload)
    edit(forged)
    return response_from_payload(_keyless_redigest(forged), **kw)


def _strip_forgery(resp, strip):
    """C5-F1's object-level keyless forger (Wave C5 architect ``p4_strip.py``): strip the corpus envelopes of the routes
    ``strip`` selects to ``unknown()``, then re-derive EVERYTHING from the tampered routes with the producer's own
    helpers -- ranking (under the request's bench, process bounds and capability profile), frontier, IR candidates and
    the constraint note.  The route SHAPE is untouched, so D26.1 cannot see it; D27.1 skipped a carried unknown()."""
    from smartchem.conditions import ConditionEnvelope

    req, ir = resp.request, resp.compilation_ir
    remap, replayed = {}, []
    for d in resp.ranked_route_dossiers:
        route = _reconstruct_route(d.replay_payload)
        if strip(d):
            bare = dc.replace(route, steps=tuple(dc.replace(s, envelope=ConditionEnvelope.unknown())
                                                 for s in route.steps))
            remap[d.route_digest] = bare.digest
            route = bare
        replayed.append(route)
    replayed = tuple(replayed)
    ranked = svc._ranked_summaries(replayed, req.constraints.bounds, resp.identity_losses,
                                   process=req.constraints.process, capability_profile=req.capability_profile)
    candidates = tuple(sorted((dc.replace(c, candidate_digest=remap.get(c.candidate_digest, c.candidate_digest))
                               for c in ir.candidates), key=lambda c: c.candidate_digest))
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(ranked),
                               process=req.constraints.process)
    forged = _bypass(resp, compilation_ir=dc.replace(ir, candidates=candidates), ranked_route_dossiers=ranked,
                     affordability_frontier=svc._route_frontier(req, replayed, ranked),
                     diagnostics=tuple(ir.diagnostics) + (() if note is None else (note,)))
    return forged, remap


def test_d28_1_c5f1_a_stripped_corpus_envelope_cannot_turn_a_section_11_exclusion_into_unknown():
    """C5-F1 reproducer 1 (P1): methyl salicylate under a PASSIVE-attention-only process box (poor-man). The sourced
    corpus record says the esterification needs PERIODIC attention, so the honest route is section-11 EXCLUDED and sits
    on the frontier as REAL_BUT_HARD. Stripped to ``unknown()`` it read fit UNKNOWN and left the frontier -- loaded
    under both pins + verified admission on fc710a8 ("an unknown envelope claims nothing" held for readiness only)."""
    from smartchem.process_constraints import Attention

    req = build_recompile_request(_MESAL, max_depth=1, helper_reagents=("water",),
                                  stock_materials=("salicylic acid", "methanol"),
                                  process=ProcessBounds.of(allowed_attention=(Attention.PASSIVE,)),
                                  capability_profile="poor-man")
    honest = run_compilation(req)
    assert [d.fit_status for d in honest.ranked_route_dossiers] == ["EXCLUDED"]
    assert honest.affordability_frontier and honest.affordability_frontier[0].cost_vector.hard_blockers
    forged, remap = _strip_forgery(honest, lambda d: True)
    assert [d.fit_status for d in forged.ranked_route_dossiers] == ["UNKNOWN"]      # the forged demotion
    assert forged.affordability_frontier == ()                                        # ... and the vanished entry
    payload = response_to_payload(forged)
    for kw in ({}, dict(require_verified_admission=True, **_pins(req))):
        with pytest.raises(ValueError, match=r"carries unknown\(\) where the shipped corpus attaches a record.*"
                                             r"refused \(D28\.1\)"):
            response_from_payload(copy.deepcopy(payload), **kw)
    response_from_payload(response_to_payload(honest), require_verified_admission=True, **_pins(req))  # control


def test_d28_1_c5f1_a_stripped_corpus_envelope_cannot_turn_an_equipment_block_into_unknown():
    """C5-F1 reproducer 2 (P1, the architect's ``p4b_strip_cap.py``): aspirin from salicylic acid + acetic anhydride
    (poor-man, T <= 350 K). The corpus record behind the anhydride route names equipment the kitchen lacks: the
    equipment axis is BLOCKED. Stripped to ``unknown()`` the axis read UNKNOWN -- loaded under pins + VA on fc710a8."""
    req = build_recompile_request(_ASPIRIN, max_depth=1, helper_reagents=("acetic acid", "water"),
                                  stock_materials=("salicylic acid", "acetic anhydride"), max_temperature_k=350.0,
                                  capability_profile="poor-man")
    honest = run_compilation(req)
    victim = next(d for d in honest.ranked_route_dossiers
                  if d.capability_assessment.equipment.status.value == "BLOCKED")
    forged, remap = _strip_forgery(honest, lambda d: d is victim)
    stripped = next(d for d in forged.ranked_route_dossiers if d.route_digest == remap[victim.route_digest])
    assert stripped.capability_assessment.equipment.status.value == "UNKNOWN"         # BLOCK -> UNKNOWN
    payload = response_to_payload(forged)
    for kw in ({}, dict(require_verified_admission=True, **_pins(req))):
        with pytest.raises(ValueError, match=r"stripped corpus evidence; refused \(D28\.1\)"):
            response_from_payload(copy.deepcopy(payload), **kw)


def test_d28_1_every_honest_producer_path_attaches_exactly_the_corpus_lookup():
    """D28.1's premise, pinned (never assumed): every step of every honest linear AND convergent-DAG answer carries
    exactly ``_conditions_for`` of its own transform -- a carried ``unknown()`` included (the lookup found nothing) --
    for BOTH transform shapes a route algebra emits: the reagent-bearing capped scission and the REAGENTLESS Diels-Alder
    retro (cyclohexene from butadiene + ethylene; the replay adapter's reagentless image, which the first D28 draft
    refused as malformed)."""
    from smartchem.conditions import ConditionEnvelope
    from smartchem.identity_parse import InputKind
    from smartchem.service import _ReplayedTransform

    unknown = ConditionEnvelope.unknown()
    diels_alder = run_compilation(build_recompile_request(
        "C1CC=CCC1", input_kind=InputKind.SMILES, helper_reagents=(), stock_materials=("C=CC=C", "C=C"),
        algebra_profile="certified-route-v07"))
    assert any(not _ReplayedTransform(s).reagents for d in diels_alder.ranked_route_dossiers
               for s in _reconstruct_route(d.replay_payload).steps)
    response_from_payload(response_to_payload(diels_alder), require_verified_admission=True, **_pins(diels_alder.request))
    runs = (_run(None), _dag_run(), diels_alder, run_compilation(build_recompile_request(
        _MESAL, max_depth=1, helper_reagents=("water",), stock_materials=("salicylic acid", "methanol"))))
    seen_unknown = seen_record = False
    for resp in runs:
        steps = [s for d in resp.ranked_route_dossiers for s in _reconstruct_route(d.replay_payload).steps]
        steps += [s for d in resp.ranked_dag_dossiers for s in svc._reconstruct_dag(d.replay_payload).steps]
        for step in steps:
            assert step.envelope == routes._conditions_for(_ReplayedTransform(step))
            seen_unknown |= step.envelope == unknown
            seen_record |= step.envelope != unknown
    assert seen_unknown and seen_record                   # both halves of the law exercised


def test_d28_2_c5f2_an_injected_ir_diagnostic_is_refused():
    """C5-F2 (P2, C4T-7 reopened): D27.4 required the response's diagnostics == the IR's + the producer's notes, but the
    IR's own diagnostics were free text -- a forged "1 FIT ... CAPABILITY_FIT" line injected into BOTH loaded on
    fc710a8, recompile and decompile alike. D28.2: the IR's diagnostics are re-derived by the producer's own rule."""
    lie = ("section-11 constraint APPLIED (T<=320 K): the routes are ranked against the bench -- 1 FIT, 0 EXCLUDED; "
           "CAPABILITY_FIT under poor-man")
    dq = svc.build_decompile_request("C2H6O")
    for resp in (_run(None), run_compilation(dq)):
        ir = resp.compilation_ir
        payload = response_to_payload(_bypass(resp, compilation_ir=dc.replace(ir, diagnostics=(lie,) + ir.diagnostics),
                                              diagnostics=(lie,) + resp.diagnostics))
        with pytest.raises(ValueError, match=r"compilation_ir\.diagnostics are not the producer's own.*"
                                                 r"refused \(D28\.2\)"):
            response_from_payload(payload, **_pins(resp.request))


@pytest.mark.parametrize("operation,field", [
    ("recompile", "target_identity_digest"), ("recompile", "terminal_policy_digest"),
    ("decompile", "target_identity_digest"), ("decompile", "terminal_policy_digest"),
    ("decompile", "transform_registry_digest"),
])
def test_d28_3_c5f3_a_null_receipt_identity_digest_is_refused(operation, field):
    """C5-F3 (P3): the IR compared its receipt's digests only when PRESENT, so ``null`` slipped past (and the decompile
    leg of the algebra rebind skips the registry digest) -- each loaded on fc710a8 with the public digest recomputed.
    (A recompile's null registry digest was already refused by the rebind; D28.3 covers it too.)"""
    resp = _run(None) if operation == "recompile" else run_compilation(svc.build_decompile_request("C2H6O"))
    wire = response_to_payload(resp)
    assert wire["compilation_ir"]["search_receipt"][field] is not None
    with pytest.raises(ValueError, match=rf"{field}.*refused \(D28\.3\)"):
        _keyless_load(wire, lambda p: p["compilation_ir"]["search_receipt"].__setitem__(field, None),
                      **_pins(resp.request))


def test_d28_3_c5f4_a_null_result_count_cannot_hide_a_deleted_candidate():
    """C5-F4 (P3): D27.5 compared the candidate count with ``results_returned`` only when it was not null, so deleting
    a verdict needed just one token -- the worst-ranked route (dossier + IR candidate, frontier and tally rebuilt) and
    a decompile's only formula edge each loaded on fc710a8 with the count nulled."""
    resp = _bench_run()
    req, ir = resp.request, resp.compilation_ir
    keep = resp.ranked_route_dossiers[:-1]
    routes_kept = tuple(_reconstruct_route(d.replay_payload) for d in keep)
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(keep), process=req.constraints.process)
    gone = resp.ranked_route_dossiers[-1].route_digest
    forged_ir = dc.replace(ir, candidates=tuple(c for c in ir.candidates if c.candidate_digest != gone),
                           search_receipt=dc.replace(ir.search_receipt, results_returned=None))
    payload = response_to_payload(_bypass(resp, compilation_ir=forged_ir, ranked_route_dossiers=keep,
                                          affordability_frontier=svc._route_frontier(req, routes_kept, keep),
                                          diagnostics=tuple(ir.diagnostics) + (() if note is None else (note,))))
    with pytest.raises(ValueError, match=r"carries no results_returned count .*refused \(D28\.3\)"):
        response_from_payload(payload, require_verified_admission=True, **_pins(req))
    dq = svc.build_decompile_request("C2H6O")
    hdc = run_compilation(dq)
    dir_ = hdc.compilation_ir
    payload = response_to_payload(_bypass(hdc, compilation_ir=dc.replace(
        dir_, candidates=(), search_receipt=dc.replace(dir_.search_receipt, results_returned=None)),
        outcome=svc.ResponseOutcome.NO_ROUTE_COMPLETE))
    with pytest.raises(ValueError, match=r"carries no results_returned count .*refused \(D28\.3\)"):
        response_from_payload(payload, **_pins(dq))


def test_d28_4_c5f5_the_unconstrained_dag_candidate_label_is_disclosed_advisory():
    """C5-F5 (P3): an UNCONSTRAINED convergent-DAG search judges no DAG (no bench box), so its IR candidates carry no
    dossier and their ``equation`` / ``candidate_digest`` have nothing to re-derive from -- advisory, but the ledger said
    RE_DERIVED_ON_LOAD. D28.4 discloses it (ledger ``advisory_when`` + the service docstring) and pins the boundary
    both ways: the unconstrained label forgery LOADS (the disclosed residual), the constrained one is REFUSED."""
    from smartchem import transport_ledger

    for field in ("candidate_digest", "equation"):
        entry = transport_ledger.TRANSPORT_LEDGER["CandidateSummary"][field]
        assert "UNCONSTRAINED convergent-DAG" in getattr(entry, "advisory_when", "")      # fc710a8: undisclosed
        assert f"CandidateSummary.{field}" in transport_ledger.partially_advisory_fields()
    assert "UNCONSTRAINED convergent-DAG" in svc.__doc__
    free = run_compilation(build_recompile_request(_TARGET, max_depth=2,
                                                   grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT))
    assert free.compilation_ir.candidates and not free.ranked_dag_dossiers
    lie = "C3H6O2 fits your bench: CAPABILITY_FIT"
    loaded = _keyless_load(response_to_payload(free),
                           lambda p: p["compilation_ir"]["candidates"][0].__setitem__("equation", lie))
    assert loaded.compilation_ir.candidates[0].equation == lie                        # the DISCLOSED residual
    boxed = _dag_run()
    assert boxed.ranked_dag_dossiers
    with pytest.raises(ValueError, match=r"D27\.7"):
        _keyless_load(response_to_payload(boxed),
                      lambda p: p["compilation_ir"]["candidates"][0].__setitem__("equation", lie))


def _add_snapshot(p, **extra):
    p["provider_snapshots"] = [dict(_FORGED_SNAPSHOT, **extra)]


# (label, wire, edit): one UNKNOWN key at every container level, and the two REQUIRED keys fc710a8 defaulted.
_D28_5_EDITS = [
    ("response", "bench", lambda p: p.__setitem__("capability_verdict", "CAPABILITY_FIT")),
    ("request", "bench", lambda p: p["request"].__setitem__("capability_verdict", "CAPABILITY_FIT")),
    ("request.identity_policy", "bench", lambda p: p["request"]["identity_policy"].__setitem__("verified", True)),
    ("compilation_ir", "bench", lambda p: p["compilation_ir"].__setitem__("readiness", "PROCESS_SPECIFIED")),
    ("ir.target", "bench", lambda p: p["compilation_ir"]["target"].__setitem__("verified", True)),
    ("search_receipt", "bench", lambda p: p["compilation_ir"]["search_receipt"].__setitem__("verified", True)),
    ("candidate", "bench", lambda p: p["compilation_ir"]["candidates"][0].__setitem__("readiness", "PROCESS_SPECIFIED")),
    ("route dossier", "bench", lambda p: p["ranked_route_dossiers"][0].__setitem__("capability_overall", "CAPABILITY_FIT")),
    ("frontier entry", "bench", lambda p: p["affordability_frontier"][0].__setitem__("disposition", "CLEAN")),
    ("cost_vector", "bench", lambda p: p["affordability_frontier"][0]["cost_vector"].__setitem__("verified_cash", 0)),
    ("DAG dossier", "dag", lambda p: p["ranked_dag_dossiers"][0].__setitem__("capability_overall", "CAPABILITY_FIT")),
    ("provider snapshot", "bench", lambda p: _add_snapshot(p, verified=True)),
    ("missing provider_snapshots", "bench", lambda p: p.pop("provider_snapshots")),
    ("missing ranked_dag_dossiers", "bench", lambda p: p.pop("ranked_dag_dossiers")),
]


@pytest.fixture(scope="module")
def _d28_wires():
    return {"bench": response_to_payload(_bench_run()), "dag": response_to_payload(_dag_run())}


@pytest.mark.parametrize("label,wire,edit", _D28_5_EDITS, ids=[e[0] for e in _D28_5_EDITS])
def test_d28_5_c5f6_every_container_carries_exactly_its_versioned_keys(_d28_wires, label, wire, edit):
    """C5-F6 (P3): unknown keys rode the whole-body digest as unenforced text at every container level (a dossier's
    ``"capability_overall": "CAPABILITY_FIT"``), and two missing required keys were silently defaulted -- each loaded on
    fc710a8 with the public digest recomputed. D28.5: exact keys at every decoder, refused before any digest."""
    with pytest.raises(ValueError, match=r"EXACTLY its versioned fields.*refused \(D28\.5\)"):
        _keyless_load(_d28_wires[wire], edit)


def test_d28_5_the_advisory_snapshot_control_still_loads(_d28_wires):
    """Control for the snapshot row: the same forged snapshot WITHOUT the unknown key is advisory data (the ledger says
    so) and loads -- the refusal above is the key, not the snapshot."""
    _keyless_load(_d28_wires["bench"], _add_snapshot)


@pytest.mark.parametrize("coerce", ["str_index", "bool_index", "str_minutes"])
def test_d28_5_c5f7_serial_holds_are_decoded_exactly(monkeypatch, coerce):
    """C5-F7 (P3): ``serial_holds`` were decoded with ``int()`` / ``float()``, so a string or bool that COERCED to the
    honest value loaded on fc710a8 (the D27.4 re-derivation compared the coerced value). D28.5: exact JSON numbers.
    The corpus gains a synthetic declared process (as in D20(1)) so the convergent DAG discloses REAL holds."""
    original = routes._conditions_for
    monkeypatch.setattr(routes, "_conditions_for", lambda t: dc.replace(original(t), process=_declared_process()))
    wire = response_to_payload(_dag_run())
    k, hold = next((k, h) for k, d in enumerate(wire["ranked_dag_dossiers"]) for h in d["serial_holds"]
                   if h[0] in (0, 1))
    i, j, minutes = hold
    forged_hold = {"str_index": [str(i), j, minutes], "bool_index": [bool(i), j, minutes],
                   "str_minutes": [i, j, str(minutes)]}[coerce]

    def edit(p):
        holds = p["ranked_dag_dossiers"][k]["serial_holds"]
        holds[holds.index(hold)] = forged_hold

    with pytest.raises(TypeError, match=r"serial hold"):
        _keyless_load(wire, edit)
    _keyless_load(wire, lambda p: None)                # control: the honest holds load (same declared corpus)


# =====================================================================================================================
# D29 (Wave C6 closure audit C6-F8, C6-NEW-1) -- a replayed step is a transform the carried ALGEBRA emits (D29.1), and
# exact keys reach the last decoders (D29.2).  Every forgery is KEYLESS (the producer's own helpers, every public digest
# recomputed) and LOADED on adf06ae -- measured against a pristine ``git archive adf06ae`` tree.
# =====================================================================================================================

_PARACETAMOL = "smiles:CC(=O)Nc1ccc(O)cc1"
_C2H4O2 = {"C": 2, "H": 4, "O": 2}


def _paracetamol(profile):
    """4-aminophenol + acetic anhydride -> paracetamol + acetic acid: the SECOND corpus record whose byproduct is not
    water (it carries a sourced procedure), so its waste axis reads a sourced hazard."""
    return build_recompile_request(_PARACETAMOL, max_depth=1, helper_reagents=("acetic acid", "water"),
                                   stock_materials=("4-aminophenol", "acetic anhydride"), capability_profile=profile)


def _isomer_byproduct_forgery(resp, smiles, *, corpus):
    """The Wave C6 masters' C6-F8 forger (``p11_f8.py`` / ``p12_waste.py`` / ``p15_overall.py``): in the first route
    with a step whose byproduct is acetic acid (a step WITH a corpus record, or WITHOUT one, per ``corpus``), swap that
    byproduct for a same-formula isomer -- so the rendered equation stays byte-identical -- re-look-up the step's corpus
    envelope (D27.1/D28.1 honest), and re-derive everything else with the producer's own helpers.  Returns the payload
    and the honest / forged dossiers."""
    from smartchem.compilation_ir import CANDIDATE_SUMMARY_SCHEMA, CandidateSummary
    from smartchem.conditions import ConditionEnvelope
    from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute
    from smartchem.smiles import parse_smiles

    def victim(step):
        if (step.envelope != ConditionEnvelope.unknown()) is not corpus:
            return None
        target = svc._structure_ident(step.target)
        return next((j for j, m in enumerate(step.products)
                     if m.formula == _C2H4O2 and svc._structure_ident(m) != target), None)

    req, ir = resp.request, resp.compilation_ir
    replayed = [_reconstruct_route(d.replay_payload) for d in resp.ranked_route_dossiers]
    k, s = next((k, s) for k, r in enumerate(replayed) for s, step in enumerate(r.steps) if victim(step) is not None)
    step = replayed[k].steps[s]
    j = victim(step)
    step = dc.replace(step, products=step.products[:j] + (parse_smiles(smiles).canonical(),) + step.products[j + 1:])
    step = dc.replace(step, envelope=routes._conditions_for(svc._ReplayedTransform(step)))
    replayed[k] = ExperimentRoute(ROUTE_SCHEMA, replayed[k].steps[:s] + (step,) + replayed[k].steps[s + 1:])
    ranked = svc._ranked_summaries(tuple(replayed), req.constraints.bounds, resp.identity_losses,
                                   process=req.constraints.process, capability_profile=req.capability_profile)
    candidates = tuple(sorted((CandidateSummary(CANDIDATE_SUMMARY_SCHEMA, "ROUTE", r.route_digest, r.equation,
                                                "FORMAL_CANDIDATE") for r in ranked), key=lambda c: c.candidate_digest))
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(ranked), process=req.constraints.process)
    forged = _bypass(resp, ranked_route_dossiers=ranked, affordability_frontier=svc._route_frontier(req, tuple(replayed),
                                                                                                   ranked),
                     compilation_ir=dc.replace(ir, candidates=candidates, search_receipt=dc.replace(
                         ir.search_receipt, results_returned=len(candidates))),
                     diagnostics=tuple(ir.diagnostics) + (() if note is None else (note,)))
    new = next(r for r in ranked if r.route_digest == replayed[k].digest)
    return response_to_payload(forged), resp.ranked_route_dossiers[k], new


def _refused_on_every_load(payload, request, match):
    for kw in ({}, _pins(request), dict(_pins(request), require_verified_admission=True),
               dict(_pins(request), require_reexecution=True)):
        with pytest.raises(ValueError, match=match):
            response_from_payload(copy.deepcopy(payload), **kw)


_NOT_EMITTED = r"is not a transform the carried algebra .* emits for that step's target.*refused \(D29\.1\)"


@pytest.mark.parametrize("isomer", ["COC=O", "OCC=O"])      # methyl formate, glycolaldehyde
def test_d29_1_c6f8_a_byproduct_isomer_cannot_erase_a_sourced_waste_block(isomer):
    """C6-F8 per axis (P1): paracetamol from the anhydride under poor-man. The sourced corpus record still attaches (its
    lookup keys on the reaction's reactants), the equation renders byte-identically, yet the waste axis read the
    carried byproduct STRUCTURE: the acetic-acid block turned UNKNOWN. Loaded on adf06ae under plain, both pins and
    verified admission (only re-execution saw it). D29.1: the step is not an emitted transform -- refused on every load."""
    req = _paracetamol("poor-man")
    honest = run_compilation(req)
    payload, old, new = _isomer_byproduct_forgery(honest, isomer, corpus=True)
    assert new.equation == old.equation                                               # byte-identical rendering
    assert old.capability_assessment.waste.status.value == "BLOCKED"
    assert new.capability_assessment.waste.status.value != "BLOCKED"                 # the erased sourced hazard
    _refused_on_every_load(payload, req, _NOT_EMITTED)
    response_from_payload(response_to_payload(honest), require_verified_admission=True, **_pins(req))   # control


def test_d29_1_c6f8_a_byproduct_isomer_cannot_flip_the_overall_verdict_blocked_to_unknown():
    """C6-F8 OVERALL (P1, ``p15_overall.py``): on a declared hood lab without hazmat routing (the research-lab preset
    minus HAZARDOUS waste -- a plausible Custom bench, test-only, no new chemistry) the waste axis is the route's only
    block, so the isomer swap moved the whole capability verdict BLOCKED -> UNKNOWN. Loaded on adf06ae likewise."""
    from smartchem.capability.enums import WasteCapability

    bench = dc.replace(research_lab(), profile_id="hood-lab-no-hazmat",
                       waste_handling=frozenset({WasteCapability.AQUEOUS_NEUTRAL}),
                       provenance="test-only Custom: research-lab minus HAZARDOUS waste routing (Wave C6 p15)")
    req = _paracetamol(bench)
    honest = run_compilation(req)
    payload, old, new = _isomer_byproduct_forgery(honest, "COC=O", corpus=True)
    assert new.equation == old.equation
    assert (old.capability_assessment.overall.value, new.capability_assessment.overall.value) == ("BLOCKED", "UNKNOWN")
    _refused_on_every_load(payload, req, _NOT_EMITTED)
    response_from_payload(response_to_payload(honest), require_verified_admission=True, **_pins(req))   # control


@pytest.mark.parametrize("isomer", ["COC=O", "OCC=O"])
def test_d29_1_c6f8_a_non_corpus_step_byproduct_isomer_is_refused(isomer):
    """C6-F8 without a corpus record (``p12_waste.py``): step 2 of the methyl-acetate peracid route (C2H4O3 + C3H6O ->
    C3H6O2 + C2H4O2) carries unknown() -- no record, so no D27.1/D28.1 lookup can object -- and its acetic-acid
    byproduct swapped for an isomer loaded on adf06ae. D29.1 binds the step to the algebra, not to the corpus."""
    honest = _run("poor-man", helper_reagents=("acetic acid", "water"))
    payload, old, new = _isomer_byproduct_forgery(honest, isomer, corpus=False)
    assert "C2H4O3 + C3H6O -> C3H6O2 + C2H4O2" in old.equation                       # the peracid step
    assert new.equation == old.equation and new.route_digest != old.route_digest
    _refused_on_every_load(payload, honest.request, _NOT_EMITTED)


def test_d29_1_every_honest_step_is_an_emitted_transform_on_every_producer_path():
    """D29.1's premise, pinned: every step of every honest answer -- linear (plain and bench), convergent DAG, the
    REAGENTLESS Diels-Alder retro, the anhydride and esterification corpus routes -- loads under verified admission.
    Every loadable real v0.8 fixture loads plain, and under verified admission (where D29.1's legacy leg runs) none is
    refused by D29.1: the ethyl-acetate fixture loads outright, the others reach D27.1's corrected-corpus refusal,
    which runs AFTER D29.1 -- so their steps, DAG included, are transforms today's algebra emits."""
    from smartchem.identity_parse import InputKind

    runs = (_run(None), _run("poor-man"), _dag_run(), run_compilation(_paracetamol("poor-man")),
            run_compilation(build_recompile_request("C1CC=CCC1", input_kind=InputKind.SMILES, helper_reagents=(),
                                                    stock_materials=("C=CC=C", "C=C"),
                                                    algebra_profile="certified-route-v07")))
    for resp in runs:
        assert resp.ranked_route_dossiers or resp.ranked_dag_dossiers
        response_from_payload(response_to_payload(resp), require_verified_admission=True, **_pins(resp.request))
    response_from_payload(_load("response_ethyl_acetate_smiles.json"), require_verified_admission=True)
    for name in ("response_isopentyl_acetate.json", "response_ethyl_acetate_smiles.json",
                 "response_stereo_isopentyl_acetate_smiles.json", "response_isopentyl_acetate_dag.json"):
        response_from_payload(_load(name))
        try:
            response_from_payload(_load(name), require_verified_admission=True)
        except ValueError as exc:
            assert "D29.1" not in str(exc) and "refused (D27.1)" in str(exc), (name, str(exc)[:200])


def test_d29_1_a_legacy_re_centred_step_fails_closed_under_verified_admission():
    """The legacy leg (Foreman N4 on v0.8), mirroring D27.1: the REAL v0.8 ethyl-acetate fixture with step 2 of a
    two-step route NEUTRALLY re-centred (readiness and frontier unchanged, the frozen v0.8 digests recomputed) loaded on
    adf06ae under both pins + verified admission. D29.1 refuses it there WITH the recompile hint; on a PLAIN load a v0.8
    step is v0.8's algebra's output, advisory -- the documented legacy boundary, pinned both ways."""
    wire = _load("response_ethyl_acetate_smiles.json")
    honest = response_from_payload(copy.deepcopy(wire))
    victim = next(d for d in wire["ranked_route_dossiers"] if len(d["replay_payload"]) == 2)
    victim["replay_payload"][1]["reaction_center"]["n_components"] += 1
    route = _reconstruct_route(svc._migrate_legacy_v08_dossier(copy.deepcopy(victim))["replay_payload"])
    assert svc._v08_digest(route) == victim["route_digest"]                       # the centre is outside the digest
    assert svc._route_readiness_to_payload(evaluate_route(route, identity_losses=honest.identity_losses)) == \
        victim["readiness"]                                                       # ... and the re-centre is NEUTRAL
    _legacy_refresh(wire)
    with pytest.raises(ValueError, match=r"re-centred replay; refused \(D29\.1\).*legacy v0\.8 payload.*"
                                         r"recompile under 0\.9"):
        response_from_payload(copy.deepcopy(wire), require_verified_admission=True, **_pins(honest.request))
    assert response_from_payload(wire).is_legacy_v08              # the documented legacy boundary: advisory, plain


# -- D29.2: exact keys at the last three decoders (C6-NEW-1) ------------------------------------------------------------

def _profile_node_edit(pick):
    def edit(p):
        pick(p["request"]["capability_profile"])["smuggled"] = "CAPABILITY_FIT"
    return edit


@pytest.mark.parametrize("label,pick", [
    ("profile", lambda n: n),
    ("physical bounds", lambda n: _find_node(n, "smartchem.constraints.PhysicalBounds")),
    ("a str scalar", lambda n: n["fields"][1][1]),
    ("an enum inside a frozenset", lambda n: next(f[1] for f in n["fields"] if f[0] == "equipment")["items"][0]),
], ids=lambda x: x if isinstance(x, str) else "")
def test_d29_2_c6new1_a_capability_codec_node_with_an_extra_key_is_refused(_d28_wires, label, pick):
    """C6-NEW-1 (P3): D28.5 closed the containers, but the canonical capability-profile codec ignored unknown keys on
    its nodes -- a ``"smuggled": "CAPABILITY_FIT"`` rode the whole-body digest as unenforced text and loaded on adf06ae
    with the public digest recomputed. D29.2: every node carries exactly its type's keys."""
    with pytest.raises(ValueError, match=r"refused \(D29\.2\)"):
        _keyless_load(_d28_wires["bench"], _profile_node_edit(pick))


@pytest.mark.parametrize("edit", ["extra", "missing"])
def test_d29_2_c6new1_an_identity_loss_entry_carries_exactly_its_keys(edit):
    """C6-NEW-1: an ``identity_losses`` entry was decoded by field lookup -- an extra key loaded on adf06ae (a missing
    one crashed with a bare KeyError). D29.2: exactly its keys, refused as a law."""
    resp = run_compilation(build_recompile_request("smiles:C[C@H](O)C(=O)OC", max_depth=1, helper_reagents=("water",),
                                                   stock_materials=("methanol",)))
    wire = response_to_payload(resp)
    assert wire["compilation_ir"]["identity_losses"]
    change = {"extra": lambda e: e.__setitem__("verified", True), "missing": lambda e: e.pop("severity")}[edit]
    with pytest.raises(ValueError, match=r"refused \(D29\.2\)"):
        _keyless_load(wire, lambda p: change(p["compilation_ir"]["identity_losses"][0]))
    _keyless_load(wire, lambda p: None)                                              # control


@pytest.mark.parametrize("where", ["candidate", "witness", "parent", "species"])
def test_d29_2_c6new1_a_structural_candidate_carries_exactly_its_keys(where):
    """C6-NEW-1: a STRUCTURE-layer decompile's ``structural_candidates`` (and the witness / species / identity payloads
    inside them) were decoded by field lookup -- an extra key round-tripped on adf06ae."""
    from smartchem.compilation_ir import decompile_structure_to_ir, ir_from_payload, ir_to_payload
    from smartchem.smiles import parse_smiles

    payload = ir_to_payload(decompile_structure_to_ir(parse_smiles("CC"), reagents=(parse_smiles("O"),)))
    ir_from_payload(copy.deepcopy(payload))                                          # control
    candidate = payload["structural_candidates"][0]
    node = {"candidate": candidate, "witness": candidate["witness"], "parent": candidate["parent"],
            "species": candidate["products"][0]}[where]
    node["verified"] = True
    with pytest.raises(ValueError, match=r"refused \(D29\.2\)"):
        ir_from_payload(payload)
