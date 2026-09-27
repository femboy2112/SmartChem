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
from smartchem.identity import identity_loss_from_payload
from smartchem.identity_parse import InputKind
from smartchem.process_constraints import ProcessBounds
from smartchem.service import (
    TransformGrammar,
    build_decompile_request,
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
        # descriptor v1alpha9 (shape): COST-VEC-01-coupled added the cost_vector's cash_floor axis.  Per-value
        # response v1alpha8: the COST-VEC-01 quantity axis now POPULATES material_quantity (routes mode).
        # (v1alpha7 per-value: cash_floor; v1alpha8 descriptor: SNAPSHOT-13.2's provider_snapshots field, response
        # v1alpha6; v1alpha7: COST-VEC-01's affordability_frontier shape, response v1alpha5; v1alpha6: SRCH-NO-01's
        # section-8.3 search_space_status field, response v1alpha4; v1alpha5: CLI-CAN-02 brick 2's
        # ranked_route_dossiers shape; v1alpha4: the request schema bumped for ConstraintPolicy's PhysicalBounds box;
        # v1alpha3: SVC-REQ-01's parse_receipt_summary + normalized_identity; v1alpha2 IR-LOSS-01.)
        # Process constraints add request fields and explicit admission output.  v1alpha11 (descriptor) / v1alpha10
        # (response): PROCESS-ADMIT-01 adds per-step process_requirements to each ranked route (re-derived on load).
        # v1alpha12 (descriptor) / v1alpha11 (response): COMBINED-VERDICT-AUTH adds the top-level producer_signature
        # field (an optional HMAC over result_digest; null unless signed).
        # v1alpha13 (descriptor) / v1alpha12 (response): DAG-ADMIT-01 adds the ranked_dag_dossiers field (per-DAG
        # PROCESS admission for a convergent compile, re-derived on load).
        # v1alpha14 (descriptor only): DAG-BENCH-01 renames the ranked_dag_summary element's process_fit_status ->
        # fit_status and widens it to the COMBINED bench fit (composability + physical + process).  The per-value
        # response schema is UNCHANGED (still v1alpha12): the response's own fields did not change and a linear payload
        # stays byte-identical -- only the nested ranked-dag-summary element bumped (ranked-dag-summary-v1alpha2).
        # v1alpha15 (descriptor only): DAG-THERMO-01 adds the ranked_dag_summary's five verdict fields (composability/
        # selectivity/feasibility/equilibrium/kinetics -- the per-node thermochemical roll-up, parity with the
        # ranked_route_summary).  Per-value response schema STILL v1alpha12: only the nested ranked-dag-summary element
        # bumped (ranked-dag-summary-v1alpha3), and a linear payload (empty ranked_dag_dossiers) stays byte-identical.
        # v1alpha16 (descriptor only): item 2b adds the ranked_dag_summary's machine-readable serial_holds field (the
        # DAG-HOLD-01 serial-schedule hold as (producer, consumer, minutes) triples).  Per-value response schema STILL
        # v1alpha12: serial_holds is DISCLOSURE, digest-excluded, and empty for a linear/non-holding DAG -- only the
        # nested ranked-dag-summary element bumped (ranked-dag-summary-v1alpha4).
        # (response) v1alpha13 (TAMPER-HARDENING-01): the on-load _check_frontier_coherence refusal (the R59 disposition
        # serialized-tamper close).  NO field is added/removed/renamed -- the response SHAPE is unchanged; the response
        # version bump marks the version at/after which a loaded response is frontier-coherence-checked, so a
        # pre-guarantee v1alpha12 payload is refused by the strict schema gate.  The DESCRIPTOR stays v1alpha16: its
        # embedded response_schema_version VALUE tracks v1alpha13, but a value-only change does NOT bump the descriptor
        # version (it bumps only on a field shape change -- its own convention).
        # v1alpha17 (descriptor, a genuine shape change) / v1alpha14 (response): v0.8 Real Route Dossiers adds a typed
        # ``readiness`` field to ranked_route_summary_fields (the Sec 3/4/8 obligation ladder; readiness_tier stays,
        # now a DERIVED alias of readiness.tier). The response version bump ALSO marks a new on-load refusal (M10):
        # _check_readiness_coherence re-derives every ranked route's readiness from its thick replay evidence.
        assert schema["descriptor_version"] == "smartchem.service/compilation-response-schema-v1alpha17"
        assert schema["response_schema_version"] == "smartchem.service/compilation-response-v1alpha14"

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
        # CLI-CAN-02 brick 2: the descriptor's ranked_route_summary_fields must match a REAL ranked payload -- the
        # methyl-acetate search finds routes, so its response carries a populated ranked_route_dossiers[0].
        assert payload["ranked_route_dossiers"], "the routes-found payload must carry a ranked dossier to check"
        assert set(payload["ranked_route_dossiers"][0]) == set(schema["ranked_route_summary_fields"])
        # DAG-ADMIT-01: the descriptor's ranked_dag_summary_fields must match a REAL DAG process admission -- a
        # convergent, process-constrained methyl-acetate compile carries a populated ranked_dag_dossiers[0].
        dag_payload = response_to_payload(run_compilation(build_recompile_request(
            "smiles:CC(=O)OC", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, max_depth=2,
            process=ProcessBounds.quick())))
        assert dag_payload["ranked_dag_dossiers"], "the DAG payload must carry a DAG admission to check"
        assert set(dag_payload["ranked_dag_dossiers"][0]) == set(schema["ranked_dag_summary_fields"])
        # IR-LOSS-01: the descriptor's identity_loss_fields must match a REAL structured loss payload (the routes
        # payload has none, so drive a SMILES decompile, whose formula reduction is a first-class BLOCKER loss).
        loss_payload = response_to_payload(
            run_compilation(build_decompile_request("CC(=O)Nc1ccc(O)cc1", input_kind=InputKind.SMILES))
        )["compilation_ir"]["identity_losses"][0]
        assert set(loss_payload) == set(schema["identity_loss_fields"])


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
        _rcpt = p["compilation_ir"]["search_receipt"]                        # the FULL section 8.1 receipt (IR-CHEM-01)
        assert _rcpt["search_kind"] == "LINEAR_ROUTE" and "nodes_visited" in _rcpt and "candidates_rejected_by_reason" in _rcpt
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
            # SRCH-NO-01: the section-8.3 no-route matrix label the --json view carries must also be in the human
            # render (uniform four-outcome surfacing), never JSON-only.
            if payload["search_space_status"] is not None:
                assert payload["search_space_status"] in human_out
            # every route ID appears (as its human prefix) -- no candidate is JSON-only
            for cand in ir["candidates"]:
                assert cand["candidate_digest"][:12] in human_out
            # every identity loss appears in both: the machine record is structured (IR-LOSS-01), and its
            # reconstructed one-line summary is exactly the human line (CLI-JSON-01 agreement).
            for loss in ir["identity_losses"]:
                assert identity_loss_from_payload(loss).summary() in human_out
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
        # IR-LOSS-01: the machine loss is a STRUCTURED record -- a consumer reads severity/affected_claims directly.
        loss = losses[0]
        assert loss["severity"] == "BLOCKER"
        assert "structure-identity" in loss["affected_claims"]
        # ... and its reconstructed one-line summary is byte-identical to the human line (the two views agree).
        summary = identity_loss_from_payload(loss).summary()
        assert "IDENTITY LOSS [BLOCKER]" in summary
        human_loss = next(line.strip() for line in human.splitlines() if "IDENTITY LOSS" in line)
        assert human_loss == summary

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
        # the receipt now rides in FULL (IR-CHEM-01); the response's convenience digest is recoverable from it.
        from smartchem.compilation_ir import _receipt_view_from_payload
        assert fields["search_receipt_digest"] == _receipt_view_from_payload(
            payload["compilation_ir"]["search_receipt"]
        ).digest
        assert list(fields["candidate_ids"]) == [c["candidate_digest"] for c in payload["compilation_ir"]["candidates"]]
        assert fields["result_digest"] == payload["result_digest"]
