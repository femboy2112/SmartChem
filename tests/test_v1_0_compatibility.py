"""1.0 cross-version wire-compatibility gate (COMPATIBILITY.md sections 3-4), proven at the 1.0 tip.

Three legs, each against REAL wire, not a hand-built mock:

1. **0.9.5 -> 1.0rc1.** A genuine 0.9.5a1 canonical response (captured from the 0.9.5a1 code before the 1.0 bump,
   `tests/fixtures/compat/v0_9_5_responses.json`) loads DIRECTLY under 1.0rc1 -- the current wire generation
   (`compilation-response-v1alpha18`) is unchanged by a package bump. The load re-derives verdicts (version-
   independent) and recomputes `result_digest` with the CURRENT `tool_version`, so the loaded digest differs from the
   carried 0.9.5a1 one: a consumer that pinned the request's `semantic_digest` keeps working, while a consumer that
   pinned the 0.9.5 `result_digest` or requires re-execution-equality must recompile (COMPATIBILITY.md section 2.2:
   "pin requests and verdicts, not result digests, across upgrades").
2. **v0.8 read-only.** The real v0.8 fixtures load (capability `NOT_REQUESTED`, never fabricated) and are refused
   under `require_canonical_transport` / `require_reexecution` -- supported for the whole 1.x series.
3. **0.9.x pre-release.** An unsupported pre-release generation (response `v1alpha17`) is refused with a hint naming
   the supported version; the package version becoming 1.0 does not migrate it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import smartchem.service as svc
from smartchem.verification import VerificationPolicy

FIXTURES = Path(__file__).parent / "fixtures"
V09_5 = json.loads((FIXTURES / "compat" / "v0_9_5_responses.json").read_text())


# ------------------------------------------------------------------ leg 1: 0.9.5 -> 1.0rc1
@pytest.mark.parametrize("cid,expected_exit", [("methyl_acetate", 0), ("aspirin", 4)])
def test_0_9_5_canonical_response_loads_directly_under_1_0(cid, expected_exit):
    case = V09_5[cid]
    payload = case["response_payload"]
    # the fixture is a genuine 0.9.5a1 wire
    assert payload["compilation_ir"]["tool_version"] == "0.9.5a1"
    assert payload["schema_version"].endswith("compilation-response-v1alpha18")

    vl = svc.load_response(payload)
    assert vl.response.exit_code == expected_exit
    assert vl.response.exit_code == case["exit_code"]


def test_0_9_5_result_digest_is_version_bound_but_request_identity_is_not():
    payload = V09_5["methyl_acetate"]["response_payload"]
    carried_digest = payload["result_digest"]

    # loading under 1.0rc1 re-derives the response; result_digest binds the CURRENT tool_version, so it moves
    loaded = svc.load_response(payload).response
    assert loaded.result_digest != carried_digest, "result_digest must bind tool_version (COMPATIBILITY 2.2)"

    # the request's semantic identity is version-INDEPENDENT: pinning it still loads
    req = svc.request_from_payload(V09_5["methyl_acetate"]["request_payload"])
    svc.load_response(payload, VerificationPolicy(expected_request_digest=req.semantic_digest))  # must not raise


def test_0_9_5_reexecution_across_the_version_boundary_is_refused_not_silently_accepted():
    # require_reexecution re-runs the carried request; the 1.0rc1 result_digest differs from the carried 0.9.5a1 one,
    # so the loader REFUSES rather than silently accept -- recompilation is the documented path.
    payload = V09_5["methyl_acetate"]["response_payload"]
    with pytest.raises(ValueError, match="require_reexecution"):
        svc.load_response(payload, VerificationPolicy(require_reexecution=True))


# ------------------------------------------------------------------ leg 2: v0.8 read-only
def _v08_response() -> dict:
    return json.loads((FIXTURES / "v08" / "response_ethyl_acetate_smiles.json").read_text())


def test_v08_fixture_loads_read_only_with_capability_not_requested():
    payload = _v08_response()
    assert payload["schema_version"].endswith("compilation-response-v1alpha15")
    vl = svc.load_response(payload)
    assert vl.response.outcome.value == "ROUTES_FOUND"
    # capability is never fabricated for a v0.8 payload
    assert payload.get("capability_question_digest") is None


def test_v08_is_refused_for_canonical_transport_and_reexecution():
    payload = _v08_response()
    with pytest.raises(ValueError, match="require_canonical_transport"):
        svc.load_response(payload, VerificationPolicy(require_canonical_transport=True))
    with pytest.raises(ValueError, match="re-execute a legacy v0.8"):
        svc.load_response(payload, VerificationPolicy(require_reexecution=True))


# ------------------------------------------------------------------ leg 3: 0.9.x pre-release refusal
def test_0_9_prerelease_wire_is_refused_with_a_supported_version_hint():
    pre09 = dict(V09_5["methyl_acetate"]["response_payload"])
    pre09["schema_version"] = "smartchem.service/compilation-response-v1alpha17"  # the 0.9.0a1 generation
    with pytest.raises(ValueError) as exc:
        svc.load_response(pre09)
    msg = str(exc.value)
    assert "v1alpha17" in msg and "unsupported" in msg
    assert "v1alpha18" in msg  # the hint names the supported generation to recompile to
