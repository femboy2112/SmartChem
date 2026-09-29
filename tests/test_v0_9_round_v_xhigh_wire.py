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
  response_isopentyl_acetate_dag.json), and the WIP-only ids are never migrated.
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
    assert request_to_payload(req)["constraints"] == _load("request_isopentyl_acetate.json")["constraints"]


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
                                 "smartchem.service/ranked-dag-summary-v1alpha6", "garbage"])
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
    with pytest.raises(ValueError, match="TARGET_FILE response's identity losses cannot be re-derived"):
        response_from_payload(payload)
    assert str(target) not in opened


def test_real_v08_loss_bearing_fixture_loads_as_legacy_and_its_stripped_loss_is_refused():
    """The REAL v0.8 producer's stereo response (tests/fixtures/v08/response_stereo_isopentyl_acetate_smiles.json):
    today's derivation reproduces its loss exactly, so it loads (plain AND verified).  The attacker strips the loss and
    re-serializes through the public codec -- the frozen v0.8 digest rule is recomputed too -- and it is refused as
    legacy, never loaded as current."""
    raw = _load("response_stereo_isopentyl_acetate_smiles.json")
    legacy = response_from_payload(copy.deepcopy(raw), require_verified_admission=True)
    assert legacy.is_legacy_v08 and [loss.feature for loss in legacy.identity_losses] == ["stereochemistry"]
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
