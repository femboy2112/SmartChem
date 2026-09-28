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

from smartchem.capability.presets import CAPABILITY_PROFILE_PRESETS, custom, resolve_capability_profile
from smartchem.conditions import Interval
from smartchem.constraints import PHYSICAL_BOUNDS_SCHEMA, PHYSICAL_BOUNDS_SCHEMA_V1
from smartchem.experiment import routes
from smartchem.experiment.stock import Phase
from smartchem.material_spec import EvidenceKind, PhaseClaim
from smartchem.procedure_evidence import ProcedureMaterialRole, ProcedureMaterialUse
from smartchem.process_constraints import Agitation, ProcessBounds, ProcessRequirements
from smartchem.service import (
    COMPILATION_RESPONSE_SCHEMA,
    LEGACY_V08_RANKED_DAG_SUMMARY_SCHEMA,
    RANKED_DAG_SUMMARY_SCHEMA,
    RankedRouteSummary,
    _procedure_material_use_from_payload,
    _procedure_material_use_to_payload,
    build_recompile_request,
    deserialize_response,
    ranked_dag_summary_from_payload,
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
