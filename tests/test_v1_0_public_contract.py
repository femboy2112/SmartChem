"""The 1.0 public-contract freeze, enforced.

COMPATIBILITY.md section 2 promises a stable surface.  :mod:`experiments.v1_0_public_contract` reads that surface
out of the live code; ``docs/research/V1_0_PUBLIC_CONTRACT_FREEZE.json`` is the frozen golden.  These tests fail the
build the instant a stable surface drifts without a deliberate re-freeze -- a stable public function losing a
parameter, a verdict word changing, a schema id moving, the default budget shrinking, a contract CLI verb
disappearing.  They are deliberately readable: the contract is spelled out here, not only in the JSON, so a reviewer
can see what is promised without decoding a 400-line document.

The surface is version-INDEPENDENT: a package bump (0.9.5a1 -> 1.0.0rc1 -> 1.0.0) must NOT move any of it.  The last
test proves the comparable document contains no version string at all.
"""
from __future__ import annotations

import json

import smartchem
from experiments.v1_0_public_contract import FREEZE_JSON, build_contract


def _frozen() -> dict:
    doc = json.loads(FREEZE_JSON.read_text(encoding="utf-8"))
    doc.pop("_meta", None)  # provenance, never compared
    return doc


def test_frozen_file_exists_and_parses():
    assert FREEZE_JSON.exists(), f"{FREEZE_JSON} is missing; run experiments/v1_0_public_contract.py --write"
    assert _frozen()["contract_schema"] == "smartchem.release/v1_0-public-contract-v1"


def test_public_contract_has_not_drifted():
    """The whole-surface invariant: the live code still produces exactly the frozen public contract."""
    frozen, live = _frozen(), build_contract()
    if frozen != live:
        # a precise, greppable drift report rather than a giant dict assertion dump
        from experiments.v1_0_public_contract import _diff

        drift = _diff(frozen, live)
        raise AssertionError(
            "public contract drift ("
            + str(len(drift))
            + " key(s)); re-freeze deliberately only for a sanctioned surface change "
            "(experiments/v1_0_public_contract.py --write):\n  " + "\n  ".join(drift)
        )


def test_eleven_stable_entry_points_exist_in_service():
    import smartchem.service as svc

    names = (
        "build_recompile_request", "build_decompile_request", "run_compilation", "response_to_payload",
        "load_response", "load_response_text", "response_from_payload", "deserialize_response",
        "request_to_payload", "request_from_payload", "response_schema",
    )
    contract = build_contract()["python_entry_points"]
    assert contract["module"] == "smartchem.service"
    assert set(contract["functions"]) == set(names)
    for n in names:
        assert callable(getattr(svc, n)), f"{n} is not callable on smartchem.service"


def test_verification_types_and_budget_contract():
    import smartchem.verification as ver

    for n in ("VerificationPolicy", "VerificationBudget", "VerifiedLoad", "VerificationBudgetExceeded"):
        assert hasattr(ver, n), f"smartchem.verification.{n} is part of the stable surface and is missing"
    assert hasattr(ver.VerificationBudget, "unlimited")
    # the DEFAULT budget may be raised by a MINOR, never lowered below the frozen corpus (COMPATIBILITY section 4)
    default = build_contract()["verification"]["default_budget"]
    assert default["canonical_work"] == 2 ** 30
    assert default["capability_work"] == 2 ** 14


def test_contract_cli_verbs_are_the_four_and_synthesize_is_not_among_them():
    cli = build_contract()["cli_verbs"]
    assert cli["contract"] == ["plan", "recompile", "decompile", "compile"]
    # synthesize is a deprecated experiment-layer alias, explicitly OUTSIDE the contract (COMPATIBILITY section 2.2)
    assert "synthesize" not in cli["contract"]
    assert "synthesize" in cli["present_noncontract"]


def test_stable_verdict_vocabulary():
    vocab = build_contract()["verdict_vocabulary"]
    assert vocab["response_outcome"]["exit_code"] == {
        "ROUTES_FOUND": 0, "TARGET_ALREADY_AVAILABLE": 0, "NO_ROUTE_COMPLETE": 3,
        "INCOMPLETE": 4, "REFUSED": 5, "INVALID_INPUT": 2, "INTERNAL_ERROR": 70,
    }
    assert set(vocab["search_space_status"]) == {
        "NO_ROUTE_IN_DECLARED_SPACE", "INCOMPLETE_NO_ROUTE_OBSERVED",
        "COMPLETE_CANDIDATE_SET", "PARTIAL_CANDIDATE_SET",
    }
    # the readiness ladder is ORDERED weakest-first; the order is part of the contract
    assert vocab["readiness_tiers_weakest_first"] == [
        "FORMAL_CANDIDATE", "REACTION_VOUCHED", "CONDITIONS_SUPPORTED", "PROCESS_SPECIFIED",
    ]
    assert set(vocab["process_fit_status"]) == {"FITS", "UNKNOWN", "EXCLUDED", "UNCONSTRAINED"}
    assert set(vocab["capability_status"]) == {"FIT", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE", "UNCONSTRAINED"}
    assert vocab["transport_mode"] == ["CANONICAL_VERIFIED", "THIN_ADVISORY"]


def test_current_and_legacy_wire_schema_ids():
    schemas = build_contract()["wire_schema_ids"]
    assert schemas["current"] == {
        "request": "smartchem.service/compilation-request-v1alpha7",
        "response": "smartchem.service/compilation-response-v1alpha18",
        "descriptor": "smartchem.service/compilation-response-schema-v1alpha21",
        "ranked_route_summary": "smartchem.service/ranked-route-summary-v1alpha6",
        "ranked_dag_summary": "smartchem.service/ranked-dag-summary-v1alpha6",
        "stock_material": "smartchem.experiment/stock-material-v1alpha4",
        "material_component": "smartchem.experiment/material-component-v1alpha3",
    }
    # the v0.8 read-only generation is supported for the whole 1.x series (COMPATIBILITY section 3.1)
    assert schemas["legacy_v0_8_read_only"]["request"] == "smartchem.service/compilation-request-v1alpha5"
    assert schemas["legacy_v0_8_read_only"]["response"] == "smartchem.service/compilation-response-v1alpha15"


def test_contract_is_version_independent():
    """A package version bump must not move this surface: the comparable document contains no version string."""
    blob = json.dumps(build_contract(), sort_keys=True)
    assert smartchem.__version__ not in blob
    # and specifically none of the release-arc versions should ever appear in the surface
    for v in ("0.9.5a1", "1.0.0rc1", "1.0.0"):
        assert v not in blob, f"version {v!r} leaked into the public-contract surface"
