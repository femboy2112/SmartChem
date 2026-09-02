"""CLI-JSON-01 -- the stable versioned ``--json`` response schema and its golden fixtures.

Acceptance (manifest 3.7): *"Human and JSON agree on all semantic fields."*  The ``--json`` output must be a stable,
versioned view carrying request, identity, receipt, tier, blockers and route IDs (standard 14.3), and it must not
silently carry -- or silently drop -- a semantic fact the human render disagrees with.

Regenerating the goldens (after an INTENTIONAL schema/output change): run
``.venv/bin/python tests/regen_cli_json.py``.  A golden diff on an UNINTENTIONAL change is the guard doing its job.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from smartchem.cli import main
from smartchem.service import (
    build_recompile_request,
    response_schema,
    response_semantic_fields,
    response_to_payload,
    run_compilation,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "cli_json"


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def _golden(name):
    return json.loads((_FIXTURES / name).read_text())


# command -> golden fixture file (the representative matrix)
_GOLDEN_CASES = {
    "recompile_routes_found.json": ["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--json"],
    "recompile_no_route.json": ["recompile", "acetic anhydride", "--elements", "--max-depth", "2", "--json"],
    "recompile_invalid.json": ["recompile", "not-a-real-name-zzz", "--json"],
    "decompile_paracetamol.json": ["decompile", "C8H9NO2", "--json"],
    "decompile_smiles_paracetamol.json": ["decompile", "CC(=O)Nc1ccc(O)cc1", "--smiles", "--json"],
}


class TestSchemaDescriptor:
    def test_descriptor_matches_its_golden(self):
        # the durable pin: the versioned schema SHAPE only changes on an intentional golden update.
        assert response_schema() == _golden("response_schema.json")

    def test_descriptor_is_versioned(self):
        schema = response_schema()
        assert schema["descriptor_version"] == "smartchem.service/compilation-response-schema-v1alpha1"
        assert schema["response_schema_version"] == "smartchem.service/compilation-response-v1alpha1"

    def test_descriptor_cannot_drift_from_a_real_payload(self):
        # the descriptor's field names MUST match what response_to_payload actually emits, at every level, so the
        # golden can never certify a schema that diverges from reality.
        payload = response_to_payload(
            run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
        )
        schema = response_schema()
        assert set(payload) == set(schema["response_fields"])
        assert set(payload["compilation_ir"]) == set(schema["compilation_ir_fields"])
        assert set(payload["compilation_ir"]["target"]) == set(schema["chemical_identity_fields"])
        assert set(payload["compilation_ir"]["candidates"][0]) == set(schema["candidate_summary_fields"])


class TestGoldenResponses:
    @pytest.mark.parametrize("name,argv", list(_GOLDEN_CASES.items()))
    def test_json_output_matches_golden(self, name, argv):
        code, out, _ = _cli(argv)
        emitted = json.loads(out)
        assert emitted == _golden(name)  # parsed-equal: whitespace-agnostic, but any field/value change is caught
        assert emitted["exit_code"] == code  # the JSON's exit_code equals the process exit code

    @pytest.mark.parametrize("argv", list(_GOLDEN_CASES.values()))
    def test_json_is_deterministic(self, argv):
        _, a, _ = _cli(argv)
        _, b, _ = _cli(argv)
        assert a == b and a.strip()


class TestJsonCarriesEverySection143Field:
    """Standard 14.3: the JSON contains request, identity, receipt, tier, blockers and route IDs."""

    def test_routes_found_carries_all_named_fields(self):
        _, out, _ = _cli(["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--json"])
        p = json.loads(out)
        assert p["request"]["operation"] == "RECOMPILE"                      # request
        assert p["compilation_ir"]["target"]["identity_digest"]              # identity
        assert p["compilation_ir"]["search_receipt_digest"]                  # receipt (as a digest)
        assert p["compilation_ir"]["candidates"][0]["readiness_tier"]        # tier
        assert p["compilation_ir"]["candidates"][0]["candidate_digest"]      # route ID
        assert "diagnostics" in p                                           # blockers channel present
        assert p["result_digest"]                                           # stable result identity

    def test_invalid_still_carries_request_and_blockers(self):
        _, out, _ = _cli(["recompile", "not-a-real-name-zzz", "--json"])
        p = json.loads(out)
        assert p["compilation_ir"] is None
        assert p["request"]["target_input"] == "not-a-real-name-zzz"
        assert p["diagnostics"]  # the refusal reason is a visible blocker


class TestHumanAndJsonAgree:
    """The acceptance: neither view silently carries or drops a semantic fact the other disagrees with."""

    @pytest.mark.parametrize("argv", [
        ["recompile", "smiles:CC(=O)OC", "--max-depth", "2"],
        ["recompile", "acetic anhydride", "--elements", "--max-depth", "2"],
        ["recompile", "CCO"],
        ["recompile", "not-a-real-name-zzz"],
    ])
    def test_human_render_surfaces_every_json_semantic_field(self, argv):
        # JSON view
        _, json_out, _ = _cli([*argv, "--json"])
        payload = json.loads(json_out)
        # human view of the SAME command
        code, human_out, _ = _cli(argv)

        # outcome + exit agree between the two views
        assert payload["outcome"] in human_out
        assert payload["exit_code"] == code

        ir = payload["compilation_ir"]
        if ir is not None:
            # identity + status appear in the human render
            assert ir["target"]["canonical_repr"] in human_out
            assert ir["target"]["layer"] in human_out
            assert ir["standard_status"] in human_out
            # every route ID appears (as its human prefix) -- no candidate is JSON-only
            for cand in ir["candidates"]:
                assert cand["candidate_digest"][:12] in human_out
            # every identity loss appears in both
            for loss in ir["identity_losses"]:
                assert loss in human_out
        else:
            # a refusal/invalid: every blocker in the JSON is surfaced to the human
            for blocker in payload["diagnostics"]:
                assert blocker in human_out

    def test_decompile_smiles_loss_appears_in_json_and_matches_the_human_line(self):
        # red-team CLI-JSON-01-A / IDL-01-SILENT-DISCARD-JSON: the SMILES->formula BLOCKER loss the human render
        # prints was absent from --json (identity_losses []). It must now be present AND byte-identical between views.
        _, human, _ = _cli(["decompile", "CC(=O)Nc1ccc(O)cc1", "--smiles"])
        _, jout, _ = _cli(["decompile", "CC(=O)Nc1ccc(O)cc1", "--smiles", "--json"])
        losses = json.loads(jout)["compilation_ir"]["identity_losses"]
        assert losses, "the SMILES->formula loss must reach the machine response, not be silently discarded"
        assert "IDENTITY LOSS [BLOCKER]" in losses[0]
        human_loss = next(line.strip() for line in human.splitlines() if "IDENTITY LOSS" in line)
        assert human_loss == losses[0]  # the two views carry the identical loss string

    def test_decompile_smiles_emit_request_records_the_smiles_origin(self):
        # red-team: --emit-request formerly showed target_input=formula with input_kind AUTO -- no trace of the SMILES.
        _, out, _ = _cli(["decompile", "CC(=O)Nc1ccc(O)cc1", "--smiles", "--emit-request"])
        req = json.loads(out)
        assert req["input_kind"] == "SMILES"
        assert req["target_input"] == "CC(=O)Nc1ccc(O)cc1"

    @pytest.mark.parametrize("argv", [["decompile", "H2O"], ["decompile", "C8H9NO2"], ["decompile", "CO2", "--inventory", "CO2"]])
    def test_decompile_human_and_json_agree_on_outcome_and_status(self, argv):
        # red-team CLI-JSON-01-B: the human decompile render omitted the outcome + section 8.2 status the --json view
        # carries. Both must now appear in the human render.
        _, human, _ = _cli(argv)
        _, jout, _ = _cli([*argv, "--json"])
        p = json.loads(jout)
        assert p["outcome"] in human
        assert p["standard_status"] in human

    def test_semantic_projection_is_recoverable_from_json(self):
        # response_semantic_fields is the single source both views draw from; every field it names must be present
        # in the JSON payload (identity/receipt/tier/blockers/route-IDs are never human-only).
        response = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
        fields = response_semantic_fields(response)
        payload = response_to_payload(response)
        assert fields["outcome"] == payload["outcome"]
        assert fields["exit_code"] == payload["exit_code"]
        assert fields["target_repr"] == payload["compilation_ir"]["target"]["canonical_repr"]
        assert fields["search_receipt_digest"] == payload["compilation_ir"]["search_receipt_digest"]
        assert list(fields["candidate_ids"]) == [c["candidate_digest"] for c in payload["compilation_ir"]["candidates"]]
        assert fields["result_digest"] == payload["result_digest"]
