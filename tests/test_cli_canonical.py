"""CLI-CAN-01 -- the canonical ``recompile``/``decompile`` verbs and the alias-equality of the legacy front doors.

The verdict-changing acceptance test (manifest section 3.7) is *"Command matrix gives equal request JSON"*: the
legacy ``compile`` alias and the canonical ``recompile`` verb, given equal flags, MUST construct byte-identical
typed requests (standard section 14.1: a legacy alias "MUST construct the same typed request as ``recompile`` and
MUST NOT keep divergent defaults").  These tests pin that, plus every seam the routing introduced: the section 14.4
exit map through the one service, the ``--json``/``--emit-request``/``--quiet`` output modes, the CLI-level
origin/semantic-digest law, and a cross-engine exit-code coherence tripwire guarding the two-view seam (the legacy
graded ``compile_synthesis`` dossier vs the service's IR -- both wrap the same ``search_routes``).
"""
from __future__ import annotations

import json

import pytest

from smartchem.cli import main
from smartchem.service import (
    CompilationOperation,
    FieldOrigin,
    ResponseOutcome,
    build_recompile_request,
    deserialize_request,
    deserialize_response,
    run_compilation,
)


def _run(capsys, argv):
    code = main(argv)
    cap = capsys.readouterr()
    return code, cap.out, cap.err


# A grid of flag combinations that mean the SAME search under both front doors.  Each row is a full argv tail
# (target + flags) shared by ``compile`` and ``recompile``.
_MATRIX = [
    ["CCO"],
    ["paracetamol"],
    ["smiles:CC(=O)OC", "--max-depth", "2"],
    ["acetic anhydride", "--elements", "--max-depth", "2"],
    ["paracetamol", "--have", "4-aminophenol", "--reagents", "water", "acetic anhydride", "--max-depth", "2"],
    ["paracetamol", "--have", "4-aminophenol", "--max-depth", "1", "--cut-budget", "1000", "--max-routes", "7"],
    ["name:water", "--reagents", "smiles:O"],
]


class TestCommandMatrixEqualRequestJson:
    """The acceptance test: equal flags across the aliases -> byte-identical request JSON."""

    @pytest.mark.parametrize("tail", _MATRIX)
    def test_compile_and_recompile_emit_identical_request_json(self, capsys, tail):
        _, compile_out, _ = _run(capsys, ["compile", *tail, "--emit-request"])
        _, recompile_out, _ = _run(capsys, ["recompile", *tail, "--emit-request"])
        assert compile_out.strip(), "emit-request must print the request JSON"
        assert compile_out == recompile_out  # byte-identical -- the whole point of one shared request builder

    def test_emit_request_is_deterministic(self, capsys):
        _, a, _ = _run(capsys, ["recompile", "paracetamol", "--emit-request"])
        _, b, _ = _run(capsys, ["recompile", "paracetamol", "--emit-request"])
        assert a == b

    @pytest.mark.parametrize(
        "left,right",
        [
            (["paracetamol", "--max-depth", "2"], ["paracetamol", "--max-depth", "3"]),
            (["paracetamol"], ["paracetamol", "--elements"]),
            (["paracetamol", "--reagents", "water"], ["paracetamol", "--reagents", "water", "acetic acid"]),
            (["paracetamol", "--cut-budget", "1000"], ["paracetamol", "--cut-budget", "2000"]),
            (["paracetamol"], ["paracetamol", "--have", "4-aminophenol"]),
        ],
    )
    def test_a_differing_semantic_flag_splits_the_request(self, capsys, left, right):
        _, lout, _ = _run(capsys, ["recompile", *left, "--emit-request"])
        _, rout, _ = _run(capsys, ["recompile", *right, "--emit-request"])
        assert lout != rout

    def test_emit_request_does_not_search_and_tolerates_an_unresolved_name(self, capsys):
        # --emit-request is a DRY echo of the request identity: it must not resolve or search, so an unknown name
        # still emits a valid request at exit 0 (resolution/refusal happens only when the search actually runs).
        code, out, _ = _run(capsys, ["recompile", "definitely-not-a-real-name-xyz", "--emit-request"])
        assert code == 0
        req = deserialize_request(out.strip())
        assert req.operation is CompilationOperation.RECOMPILE
        assert req.target_input == "definitely-not-a-real-name-xyz"


class TestCliOriginLaw:
    """The CLI surface of standard section 13.1: a defaulted knob is a VISIBLE origin=DEFAULT field, and a value
    reached by default vs passed explicitly shares the SEARCH identity (equal semantic_digest) while differing in
    provenance."""

    def test_default_and_explicit_equal_value_share_semantic_digest_but_not_origin(self, capsys):
        _, default_out, _ = _run(capsys, ["recompile", "paracetamol", "--emit-request"])
        _, explicit_out, _ = _run(capsys, ["recompile", "paracetamol", "--max-depth", "3", "--emit-request"])
        default_req = deserialize_request(default_out.strip())
        explicit_req = deserialize_request(explicit_out.strip())
        origins_default = dict(default_req.origins)
        origins_explicit = dict(explicit_req.origins)
        assert origins_default["max_depth"] is FieldOrigin.DEFAULT
        assert origins_explicit["max_depth"] is FieldOrigin.EXPLICIT
        # same resolved value (3) reached two ways -> the SAME search identity ...
        assert default_req.semantic_digest == explicit_req.semantic_digest
        # ... but a different full identity, because provenance differs.
        assert default_req.digest != explicit_req.digest

    def test_no_commodities_is_recorded_explicit(self, capsys):
        _, out, _ = _run(capsys, ["recompile", "paracetamol", "--elements", "--emit-request"])
        req = deserialize_request(out.strip())
        assert dict(req.origins)["commodities_enabled"] is FieldOrigin.EXPLICIT
        assert req.terminal_policy.commodities_enabled is False


class TestRecompileOutcomes:
    """The canonical verb maps each outcome to its section 14.4 exit code through the one service authority."""

    def test_commodity_target_is_already_available(self, capsys):
        code, out, _ = _run(capsys, ["recompile", "CCO"])
        assert code == 0
        assert "TARGET_ALREADY_AVAILABLE" in out and "ALREADY AVAILABLE" in out

    def test_complete_no_route_is_exit_three(self, capsys):
        code, out, _ = _run(capsys, ["recompile", "acetic anhydride", "--elements", "--max-depth", "2"])
        assert code == 3
        assert "NO_ROUTE_COMPLETE" in out and "COMPLETE" in out

    def test_charged_model_boundary_is_a_refusal(self, capsys):
        code, out, _ = _run(capsys, ["recompile", "[CH2+]CCC", "--elements", "--max-depth", "1"])
        assert code == 5
        assert "REFUSED" in out

    def test_unknown_identity_is_invalid_input(self, capsys):
        code, out, _ = _run(capsys, ["recompile", "not-a-real-chemical-zzz"])
        assert code == 2
        assert "INVALID_INPUT" in out

    def test_routes_found_lists_candidates(self, capsys):
        code, out, _ = _run(capsys, ["recompile", "smiles:CC(=O)OC", "--max-depth", "2"])
        assert code == 0
        assert "ROUTES_FOUND" in out
        assert "#" in out  # at least one candidate ID rendered

    def test_partial_search_is_exit_four_with_a_blocker(self, capsys):
        code, out, _ = _run(capsys, [
            "recompile", "paracetamol", "--have", "4-aminophenol",
            "--reagents", "water", "acetic acid", "acetic anhydride",
            "--max-depth", "1", "--cut-budget", "1000", "--elements",
        ])
        assert code == 4
        assert "INCOMPLETE" in out and "PARTIAL" in out


class TestRecompileJson:
    def test_json_round_trips_and_agrees_on_exit(self, capsys):
        code, out, _ = _run(capsys, ["recompile", "CCO", "--json"])
        payload = json.loads(out)
        response = deserialize_response(out.strip())
        assert response.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE
        assert response.exit_code == code == payload["exit_code"] == 0
        # the response schema carries the request (CLI-JSON-01 leans on this)
        assert payload["request"]["operation"] == "RECOMPILE"
        assert payload["result_digest"]

    def test_json_and_human_share_an_exit_code(self, capsys):
        human_code, _, _ = _run(capsys, ["recompile", "acetic anhydride", "--elements", "--max-depth", "2"])
        json_code, _, _ = _run(capsys, ["recompile", "acetic anhydride", "--elements", "--max-depth", "2", "--json"])
        assert human_code == json_code == 3


class TestQuietNeverHidesABlocker:
    def test_quiet_drops_narrative_but_keeps_the_partial_blocker(self, capsys):
        # section 14.3: --quiet MAY suppress narrative but MUST NOT suppress a blocker in a successful-looking result.
        code, out, _ = _run(capsys, [
            "recompile", "paracetamol", "--have", "4-aminophenol",
            "--reagents", "water", "acetic acid", "acetic anhydride",
            "--max-depth", "1", "--cut-budget", "1000", "--elements", "--quiet",
        ])
        assert code == 4
        assert "PARTIAL" in out  # the blocker survives --quiet ...
        assert "  target:" not in out  # ... but the descriptive narrative is gone
        assert "engine:" not in out


class TestCrossEngineExitCoherence:
    """The legacy graded ``compile`` dossier and the service both wrap the same ``search_routes``; their section
    14.4 exit codes MUST agree for equal flags.  This tripwire guards the two-view seam until run_compilation is
    unified to return the dossier."""

    @pytest.mark.parametrize("tail", [
        ["CCO"],
        ["acetic anhydride", "--elements", "--max-depth", "2"],
        ["[CH2+]CCC", "--elements", "--max-depth", "1"],
        ["paracetamol", "--have", "4-aminophenol", "--reagents", "water", "acetic acid", "acetic anhydride",
         "--max-depth", "1", "--cut-budget", "1000", "--elements"],
    ])
    def test_compile_human_and_recompile_json_agree_on_exit(self, capsys, tail):
        compile_code, _, _ = _run(capsys, ["compile", *tail])
        recompile_code, _, _ = _run(capsys, ["recompile", *tail, "--json"])
        assert compile_code == recompile_code


class TestDecompileServiceViews:
    def test_human_and_json_agree(self, capsys):
        human_code, _, _ = _run(capsys, ["decompile", "C8H9NO2"])
        json_code, out, _ = _run(capsys, ["decompile", "C8H9NO2", "--json"])
        response = deserialize_response(out.strip())
        assert human_code == json_code == 0
        assert response.outcome is ResponseOutcome.ROUTES_FOUND

    def test_example_inventory_does_not_crash_the_request(self, capsys):
        # regression: example_inventory() yields Formula OBJECTS; the request keys on formula TEXT, so the CLI must
        # normalise them or the request builder dies on Formula.__lt__ inside its canonical sort.
        code, out, _ = _run(capsys, ["decompile", "CO2", "--json"])
        assert code == 0
        deserialize_response(out.strip())  # parses

    def test_target_that_is_a_bucket_is_already_available(self, capsys):
        code, out, _ = _run(capsys, ["decompile", "CO2", "--inventory", "CO2", "--json"])
        response = deserialize_response(out.strip())
        assert code == 0
        assert response.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE

    def test_emit_request_is_a_decompile_request(self, capsys):
        code, out, _ = _run(capsys, ["decompile", "C8H9NO2", "--emit-request"])
        req = deserialize_request(out.strip())
        assert code == 0
        assert req.operation is CompilationOperation.DECOMPILE
        assert req.transform_grammar.value == "FORMULA_DECOMPOSITION"

    def test_invalid_formula_json_is_exit_two(self, capsys):
        code, _, err = _run(capsys, ["decompile", "H0", "--json"])
        assert code == 2
        assert "Traceback" not in err


class TestDeprecationAndUsage:
    def test_usage_lists_recompile_and_keeps_the_legacy_names(self, capsys):
        code, out, _ = _run(capsys, [])
        assert code == 0
        for cmd in ("decompile", "recompile", "compile", "synthesize", "audit"):
            assert cmd in out

    def test_compile_prints_a_deprecation_notice_to_stderr_only(self, capsys):
        code, out, err = _run(capsys, ["compile", "CCO"])
        assert code == 0
        assert "COMMODITY" in out.upper()  # the rich dossier is preserved on stdout ...
        assert "deprecated" in err.lower()  # ... and the deprecation notice rides stderr
        assert "deprecated" not in out.lower()

    def test_compile_emit_request_stdout_is_clean_json(self, capsys):
        # the deprecation notice must not pollute the request JSON the matrix compares.
        code, out, _ = _run(capsys, ["compile", "paracetamol", "--emit-request"])
        assert code == 0
        deserialize_request(out.strip())  # stdout parses as a request, nothing else


class TestRedTeamRegressions:
    """Each pins a defect the CLI-CAN-01 red-team (workflow wab9d7v2t) CONFIRMED and I folded before the commit."""

    @pytest.mark.parametrize("target,flags", [
        ("smiles:CC(=O)OC", ["--max-depth", "2"]),
        ("paracetamol", ["--max-depth", "2"]),
    ])
    def test_A_empty_reagents_does_not_crash_to_an_undefined_exit(self, capsys, target, flags):
        # CLI-CAN-01-A: `--reagents` with no values gave [] -> () -> the engine raised a raw TypeError that escaped
        # every handler to exit 1 + a traceback (no section-14.4 code). It must now be a defined outcome, no traceback.
        code, _, err = _run(capsys, ["recompile", target, "--reagents", *flags])
        assert code in (0, 2, 3, 4, 5)
        assert "Traceback" not in err

    def test_B_empty_reagents_runs_the_same_search_across_aliases(self, capsys):
        # CLI-CAN-01-B: an identical emitted request (empty --reagents) executed two DIFFERENT searches -- compile
        # silently injected water, recompile searched () and crashed. Both must now coerce the empty pool to the
        # visible water default and agree on the exit code.
        compile_code, _, _ = _run(capsys, ["compile", "paracetamol", "--reagents", "--max-depth", "2"])
        recompile_code, _, _ = _run(capsys, ["recompile", "paracetamol", "--reagents", "--max-depth", "2"])
        assert compile_code == recompile_code

    def test_B_empty_reagents_emits_the_visible_water_default(self, capsys):
        code, out, _ = _run(capsys, ["recompile", "paracetamol", "--reagents", "--emit-request"])
        req = deserialize_request(out.strip())
        assert code == 0
        assert list(req.helper_reagents) == ["water"]  # the default is a VISIBLE field, not an invisible injection
        assert dict(req.origins)["helper_reagents"] is FieldOrigin.DEFAULT

    def test_A_service_refuses_a_programmatic_empty_reagent_pool(self):
        # defense-in-depth: a non-CLI caller building helper_reagents=() must get a typed exit-2 refusal, never a crash.
        response = run_compilation(build_recompile_request("smiles:CC(=O)OC", helper_reagents=()))
        assert response.outcome is ResponseOutcome.INVALID_INPUT
        assert response.exit_code == 2

    @pytest.mark.parametrize("element", ["He", "Fe", "O", "U"])
    def test_F1_bare_element_agrees_and_is_already_available(self, capsys, element):
        # F1 / DEC-ELEM-EXIT-DIVERGE: a bare element is a universal terminal bucket; the human path exits 0
        # (already a bucket) but the service --json path exited 3 (NO_ROUTE_COMPLETE) -- a confident claim of absence
        # over something already elemental, and a drift the routing promises cannot happen.
        human_code, _, _ = _run(capsys, ["decompile", element])
        json_code, out, _ = _run(capsys, ["decompile", element, "--json"])
        response = deserialize_response(out.strip())
        assert human_code == json_code == 0
        assert response.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE

    def test_F1_a_normal_formula_still_reports_routes(self, capsys):
        # the fix must not turn a genuine decomposition into "already available".
        _, out, _ = _run(capsys, ["decompile", "C8H9NO2", "--json"])
        assert deserialize_response(out.strip()).outcome is ResponseOutcome.ROUTES_FOUND
