"""Adversarial tests for the typed compilation service (SVC-REQ-01, first brick).

The load-bearing property under test is the standard's section 13.1 / gate G8: two requests built from equal
flags across different aliases must share a semantic (search) digest and, run through the service, an equal result
digest -- while a value reached by default and the same value passed explicitly stay distinguishable in the audit
trail (origins) without splitting the search identity.  The rest hardens the no-laundering coherence guard, the
section 14.4 exit mapping, fail-closed validation, and canonical serialization.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from smartchem import service as svc
from smartchem.compilation_ir import CompilationOperation
from smartchem.identity_parse import IdentityParseError, InputKind, resolve_target
from smartchem.service import (
    COMPILATION_RESPONSE_SCHEMA,
    CompilationResponse,
    EvidenceProviderSelection,
    FieldOrigin,
    IdentityPolicy,
    OutputPolicy,
    RankingPolicy,
    ResponseOutcome,
    SearchBounds,
    TerminalPolicy,
    TransformGrammar,
    build_decompile_request,
    build_recompile_request,
    deserialize_request,
    deserialize_response,
    request_from_payload,
    request_to_payload,
    response_from_payload,
    response_to_payload,
    run_compilation,
    serialize_request,
    serialize_response,
)

# -- shared real fixtures (all fast; searches complete in <2.5s) -------------------------------------------------

_ROUTES_FOUND_TARGET = "smiles:CC(=O)OC"  # methyl acetate: fully exhausts and finds routes to commodities


@pytest.fixture(scope="module")
def ir_complete_with_candidates():
    resp = run_compilation(build_recompile_request(_ROUTES_FOUND_TARGET, max_depth=3, max_routes=50))
    assert resp.outcome is ResponseOutcome.ROUTES_FOUND and resp.compilation_ir.candidate_count > 0
    return resp.compilation_ir


@pytest.fixture(scope="module")
def ir_complete_empty():
    resp = run_compilation(
        build_recompile_request("benzene", commodities_enabled=False, max_depth=2, max_routes=20)
    )
    assert resp.outcome is ResponseOutcome.NO_ROUTE_COMPLETE and resp.compilation_ir.candidate_count == 0
    return resp.compilation_ir


@pytest.fixture(scope="module")
def ir_incomplete():
    resp = run_compilation(build_recompile_request("paracetamol", max_depth=2, max_routes=20, cut_budget=5000))
    assert resp.outcome is ResponseOutcome.INCOMPLETE and not resp.compilation_ir.complete_within_bounds
    return resp.compilation_ir


# -- A. the acceptance property: equal flags across aliases -> equal request AND result digest --------------------


class TestAliasEquality:
    def test_two_aliases_equal_flags_equal_semantic_and_result_digest(self):
        # A `compile`-style caller (leaves grammar/kind default) and a `recompile`-style caller (passes them
        # explicitly, equal to the defaults) with otherwise-equal flags.
        compile_style = build_recompile_request(
            _ROUTES_FOUND_TARGET, max_depth=3, max_routes=50, cut_budget=20_000
        )
        recompile_style = build_recompile_request(
            _ROUTES_FOUND_TARGET,
            input_kind=InputKind.AUTO,
            grammar=TransformGrammar.CAPPED_SCISSION_LINEAR,
            commodities_enabled=True,
            helper_reagents=("water",),
            max_depth=3,
            max_routes=50,
            cut_budget=20_000,
        )
        assert compile_style.semantic_digest == recompile_style.semantic_digest
        # ...and the deterministic producer carries that equality through to the result (the "result digests" half).
        assert run_compilation(compile_style).result_digest == run_compilation(recompile_style).result_digest
        # yet the audit trail is not identical: one defaulted the knobs, the other stated them.
        assert compile_style.origins != recompile_style.origins
        assert compile_style.digest != recompile_style.digest

    def test_explicit_value_equal_to_default_shares_search_identity(self):
        defaulted = build_recompile_request("name:water")
        explicit = build_recompile_request("name:water", cut_budget=20_000)
        assert defaulted.semantic_digest == explicit.semantic_digest
        assert dict(defaulted.origins)["cut_budget"] is FieldOrigin.DEFAULT
        assert dict(explicit.origins)["cut_budget"] is FieldOrigin.EXPLICIT

    def test_bench_order_is_not_search_identity(self):
        a = build_recompile_request("name:water", stock_materials=("ethanol", "benzene"))
        b = build_recompile_request("name:water", stock_materials=("benzene", "ethanol"))
        assert a.semantic_digest == b.semantic_digest
        # canonicalised to sorted order in the stored field, too
        assert a.stock_materials == b.stock_materials == ("benzene", "ethanol")

    def test_duplicate_bench_entries_collapse(self):
        a = build_recompile_request("name:water", helper_reagents=("water", "water"))
        b = build_recompile_request("name:water", helper_reagents=("water",))
        assert a.semantic_digest == b.semantic_digest

    def test_output_policy_is_excluded_from_search_identity(self):
        human = build_recompile_request("name:water")
        as_json = build_recompile_request("name:water", output_policy=OutputPolicy("JSON", quiet=True))
        assert human.semantic_digest == as_json.semantic_digest  # display choice, not search identity
        assert human.digest != as_json.digest  # but preserved in the full identity

    @pytest.mark.parametrize(
        "kwargs",
        [
            dict(max_depth=4),
            dict(max_routes=99),
            dict(cut_budget=19_999),
            dict(commodities_enabled=False),
            dict(grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT),
            dict(helper_reagents=("ethanol",)),
            dict(stock_materials=("benzene",)),
            dict(input_kind=InputKind.NAME),
            dict(identity_policy=IdentityPolicy("STRICT")),
            dict(max_temperature_k=400.0),
            dict(ranking_policy=RankingPolicy("COST_FIRST")),
            dict(evidence_provider_selection=EvidenceProviderSelection("PUBCHEM")),
        ],
    )
    def test_every_semantic_field_moves_the_digest(self, kwargs):
        base = build_recompile_request("name:water")
        mutated = build_recompile_request("name:water", **kwargs)
        assert base.semantic_digest != mutated.semantic_digest

    def test_target_change_moves_the_digest(self):
        assert (
            build_recompile_request("name:water").semantic_digest
            != build_recompile_request("name:ethanol").semantic_digest
        )


# -- B. origin discipline (defaults are explicit, auditable fields) ----------------------------------------------


class TestOrigins:
    def test_defaults_marked_default_explicit_marked_explicit(self):
        req = build_recompile_request("name:water", max_depth=5)
        origins = dict(req.origins)
        assert origins["max_depth"] is FieldOrigin.EXPLICIT
        assert origins["cut_budget"] is FieldOrigin.DEFAULT
        assert origins["commodities_enabled"] is FieldOrigin.DEFAULT

    def test_origins_are_canonical_sorted_and_unique(self):
        names = [name for name, _ in build_recompile_request("name:water").origins]
        assert names == sorted(names)
        assert len(names) == len(set(names))

    def test_origins_survive_serialization(self):
        req = build_recompile_request("name:water", cut_budget=1234)
        back = deserialize_request(serialize_request(req))
        assert back.origins == req.origins


# -- C. run_compilation outcomes and section 14.4 exit codes -----------------------------------------------------


class TestOutcomes:
    def test_routes_found_exits_zero(self):
        resp = run_compilation(build_recompile_request(_ROUTES_FOUND_TARGET, max_depth=3))
        assert resp.outcome is ResponseOutcome.ROUTES_FOUND
        assert resp.exit_code == svc.EXIT_SUCCESS
        assert resp.standard_status == "COMPLETE_WITHIN_DECLARED_SPACE"
        assert len(resp.candidates) > 0

    def test_no_route_complete_exits_three(self):
        resp = run_compilation(
            build_recompile_request("benzene", commodities_enabled=False, max_depth=2)
        )
        assert resp.outcome is ResponseOutcome.NO_ROUTE_COMPLETE
        assert resp.exit_code == svc.EXIT_NO_ROUTE
        assert resp.standard_status == "COMPLETE_WITHIN_DECLARED_SPACE"

    def test_incomplete_depth_exits_four(self):
        resp = run_compilation(build_recompile_request("paracetamol", max_depth=2, cut_budget=5000))
        assert resp.outcome is ResponseOutcome.INCOMPLETE
        assert resp.exit_code == svc.EXIT_INCOMPLETE
        assert resp.standard_status.startswith("INCOMPLETE_")

    def test_incomplete_cut_budget_exits_four(self):
        resp = run_compilation(build_recompile_request("paracetamol", max_depth=1, cut_budget=50))
        assert resp.outcome is ResponseOutcome.INCOMPLETE
        assert resp.exit_code == svc.EXIT_INCOMPLETE
        assert resp.standard_status == "INCOMPLETE_CUT_BUDGET"

    def test_target_already_available_exits_zero(self):
        resp = run_compilation(build_recompile_request("ethanol"))  # ethanol is a commodity terminal
        assert resp.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE
        assert resp.exit_code == svc.EXIT_SUCCESS

    def test_invalid_input_exits_two_with_refused_invalid_request(self):
        resp = run_compilation(build_recompile_request("name:not_a_real_chemical_xyz"))
        assert resp.outcome is ResponseOutcome.INVALID_INPUT
        assert resp.exit_code == svc.EXIT_INVALID_INPUT
        assert resp.standard_status == "REFUSED_INVALID_REQUEST"
        assert resp.compilation_ir is None and resp.diagnostics

    def test_decompile_routes_found(self):
        resp = run_compilation(build_decompile_request("H2O"))
        assert resp.request.operation is CompilationOperation.DECOMPILE
        assert resp.outcome is ResponseOutcome.ROUTES_FOUND
        assert resp.exit_code == svc.EXIT_SUCCESS

    def test_run_is_deterministic(self):
        req = build_recompile_request(_ROUTES_FOUND_TARGET, max_depth=3)
        assert run_compilation(req).result_digest == run_compilation(req).result_digest

    def test_run_reads_only_semantic_fields(self):
        # differ ONLY in provenance/display -> identical execution and result
        a = build_recompile_request(_ROUTES_FOUND_TARGET, max_depth=3)
        b = build_recompile_request(
            _ROUTES_FOUND_TARGET, max_depth=3, cut_budget=20_000,  # explicit == default
            output_policy=OutputPolicy("JSON", quiet=True),
        )
        assert a.semantic_digest == b.semantic_digest
        assert run_compilation(a).result_digest == run_compilation(b).result_digest

    def test_run_rejects_non_request(self):
        with pytest.raises(TypeError):
            run_compilation({"not": "a request"})


# -- D. the no-laundering coherence guard ------------------------------------------------------------------------


def _resp(outcome, status, ir, diagnostics=()):
    req = build_recompile_request("name:water")
    return CompilationResponse(COMPILATION_RESPONSE_SCHEMA, req, outcome, status, ir, tuple(diagnostics))


class TestCoherenceGuard:
    def test_incomplete_cannot_carry_a_complete_ir(self, ir_complete_with_candidates):
        # status matches the (complete) IR, so the status-vs-IR check passes and the completeness clause fires
        with pytest.raises(ValueError, match="complete-within-bounds"):
            _resp(ResponseOutcome.INCOMPLETE, "COMPLETE_WITHIN_DECLARED_SPACE", ir_complete_with_candidates)

    def test_incomplete_must_report_incomplete_status(self, ir_incomplete):
        with pytest.raises(ValueError, match="INCOMPLETE_"):
            _resp(ResponseOutcome.INCOMPLETE, "COMPLETE_WITHIN_DECLARED_SPACE", ir_incomplete)

    def test_no_route_complete_cannot_have_candidates(self, ir_complete_with_candidates):
        with pytest.raises(ValueError, match="zero candidates"):
            _resp(ResponseOutcome.NO_ROUTE_COMPLETE, "COMPLETE_WITHIN_DECLARED_SPACE", ir_complete_with_candidates)

    def test_routes_found_requires_a_candidate(self, ir_complete_empty):
        with pytest.raises(ValueError, match="at least one candidate"):
            _resp(ResponseOutcome.ROUTES_FOUND, "COMPLETE_WITHIN_DECLARED_SPACE", ir_complete_empty)

    def test_routes_found_requires_a_complete_search(self, ir_incomplete):
        with pytest.raises(ValueError, match="complete-within-bounds"):
            _resp(ResponseOutcome.ROUTES_FOUND, "INCOMPLETE_DEPTH_LIMIT", ir_incomplete)

    def test_no_route_complete_requires_a_complete_search(self, ir_incomplete):
        with pytest.raises(ValueError, match="complete-within-bounds"):
            _resp(ResponseOutcome.NO_ROUTE_COMPLETE, "INCOMPLETE_DEPTH_LIMIT", ir_incomplete)

    def test_searched_outcome_requires_an_ir(self):
        with pytest.raises(ValueError, match="requires a compilation_ir"):
            _resp(ResponseOutcome.NO_ROUTE_COMPLETE, "COMPLETE_WITHIN_DECLARED_SPACE", None)

    def test_invalid_input_must_not_carry_an_ir(self, ir_complete_with_candidates):
        with pytest.raises(ValueError, match="must not carry"):
            _resp(ResponseOutcome.INVALID_INPUT, "REFUSED_INVALID_REQUEST", ir_complete_with_candidates, ("x",))

    def test_invalid_input_must_report_refused_invalid_request(self):
        with pytest.raises(ValueError, match="REFUSED_INVALID_REQUEST"):
            _resp(ResponseOutcome.INVALID_INPUT, None, None, ("bad name",))

    def test_refused_must_state_a_reason(self):
        with pytest.raises(ValueError, match="diagnostic reason"):
            _resp(ResponseOutcome.REFUSED, None, None, ())

    def test_refused_rejects_a_completion_status(self):
        with pytest.raises(ValueError, match="REFUSED_"):
            _resp(ResponseOutcome.REFUSED, "COMPLETE_WITHIN_DECLARED_SPACE", None, ("boundary",))

    def test_refused_allows_none_status(self):
        r = _resp(ResponseOutcome.REFUSED, None, None, ("refused at the chemistry-model boundary",))
        assert r.exit_code == svc.EXIT_REFUSED


# -- E. fail-closed validation -----------------------------------------------------------------------------------


class TestValidation:
    def test_request_bad_schema_version(self):
        good = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="schema_version"):
            replace(good, schema_version="bogus")

    def test_empty_target_input(self):
        good = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="target_input"):
            replace(good, target_input="   ")

    def test_search_bounds_reject_nonpositive(self):
        with pytest.raises(ValueError, match="positive int"):
            SearchBounds.of(max_depth=0)

    def test_search_bounds_reject_bool(self):
        with pytest.raises(ValueError, match="positive int"):
            SearchBounds((("flag", True),))

    def test_search_bounds_reject_unsorted(self):
        with pytest.raises(ValueError, match="name-sorted"):
            SearchBounds((("z", 1), ("a", 2)))

    def test_search_bounds_reject_empty(self):
        with pytest.raises(ValueError, match="non-empty"):
            SearchBounds(())

    def test_terminal_policy_bad_match_mode(self):
        with pytest.raises(ValueError, match="match_mode"):
            TerminalPolicy("SOMETHING_ELSE")

    def test_output_policy_bad_render_mode(self):
        with pytest.raises(ValueError, match="render_mode"):
            OutputPolicy("YAML")

    def test_decompile_requires_formula_grammar(self):
        good = build_decompile_request("H2O")
        with pytest.raises(ValueError, match="FORMULA_DECOMPOSITION"):
            replace(good, transform_grammar=TransformGrammar.CAPPED_SCISSION_LINEAR)

    def test_recompile_rejects_formula_grammar(self):
        good = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="capped-scission"):
            replace(good, transform_grammar=TransformGrammar.FORMULA_DECOMPOSITION)

    def test_stock_must_be_canonical(self):
        good = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="canonical"):
            replace(good, stock_materials=("z", "a"))

    def test_stock_rejects_duplicates(self):
        good = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="distinct"):
            replace(good, stock_materials=("a", "a"))

    def test_response_rejects_populated_dossiers(self):
        req = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="READY-TIER-01"):
            CompilationResponse(
                COMPILATION_RESPONSE_SCHEMA, req, ResponseOutcome.REFUSED, None, None,
                ("x",), ("a dossier",), (),
            )


# -- F. canonical serialization ----------------------------------------------------------------------------------


class TestSerialization:
    def test_request_round_trip_stable(self):
        req = build_recompile_request("name:water", stock_materials=("benzene",), cut_budget=7777)
        back = deserialize_request(serialize_request(req))
        assert back.digest == req.digest
        assert back.semantic_digest == req.semantic_digest

    def test_request_serialization_is_deterministic(self):
        req = build_recompile_request("name:water")
        assert serialize_request(req) == serialize_request(req)

    def test_response_round_trip_stable(self):
        resp = run_compilation(build_recompile_request(_ROUTES_FOUND_TARGET, max_depth=3))
        back = deserialize_response(serialize_response(resp))
        assert back.result_digest == resp.result_digest
        assert back.outcome is resp.outcome
        assert back.exit_code == resp.exit_code

    def test_response_round_trip_without_ir(self):
        resp = run_compilation(build_recompile_request("name:not_a_real_chemical_xyz"))
        back = deserialize_response(serialize_response(resp))
        assert back.result_digest == resp.result_digest
        assert back.compilation_ir is None

    def test_tampered_bounds_refused(self):
        payload = request_to_payload(build_recompile_request("name:water"))
        payload["search_bounds"] = [["cut_budget", -5]]
        with pytest.raises(ValueError, match="positive int"):
            request_from_payload(payload)

    def test_unknown_enum_refused(self):
        payload = request_to_payload(build_recompile_request("name:water"))
        payload["transform_grammar"] = "MADE_UP_GRAMMAR"
        with pytest.raises(ValueError):
            request_from_payload(payload)

    def test_response_payload_carries_exit_and_digest(self):
        resp = run_compilation(build_recompile_request(_ROUTES_FOUND_TARGET, max_depth=3))
        payload = response_to_payload(resp)
        assert payload["exit_code"] == resp.exit_code
        assert payload["result_digest"] == resp.result_digest


# -- G. the single shared identity parser (extraction did not regress the CLI) -----------------------------------


class TestIdentityParse:
    def test_auto_resolves_registered_name(self):
        assert resolve_target("water", InputKind.AUTO) is not None

    def test_auto_honours_smiles_prefix(self):
        assert resolve_target("smiles:CCO", InputKind.AUTO) is not None

    def test_explicit_name_of_unknown_is_loud(self):
        with pytest.raises(IdentityParseError, match="unknown offline chemical name"):
            resolve_target("definitely_not_a_chemical", InputKind.NAME)

    def test_parse_error_is_a_value_error(self):
        assert issubclass(IdentityParseError, ValueError)

    @pytest.mark.parametrize("target,kind", [
        ("C8H9NO2", InputKind.FORMULA),
        ("InChI=1S/C8H9NO2/c1-6(10)9-7-2-4-8(11)5-3-7/h2-5,10H,1H3,(H,9,10)", InputKind.INCHI),
    ])
    def test_formula_only_kinds_resolve_but_refuse_a_structure_search(self, target, kind):
        # ID-PARSE-01 FINISHED: FORMULA and an InChI's formula sublayer now RESOLVE (no longer "not yet supported"),
        # but only to a FORMULA-layer identity -- so resolve_target (which needs a MOLECULE for a structure search)
        # refuses them loudly per section 5.4, never guessing a structure.
        from smartchem.identity_parse import resolve_identity
        r = resolve_identity(target, kind)
        assert not r.structure_perceived
        with pytest.raises(IdentityParseError, match="no perceived structure"):
            resolve_target(target, kind)

    def test_cli_parse_molecule_still_delegates(self):
        from smartchem.cli import _parse_molecule
        assert _parse_molecule("water") is not None


# -- H. red-team regressions (each pins a CONFIRMED finding from the SVC-REQ-01 red-team shut) --------------------


class TestRedTeamRegressions:
    def test_decompile_rejects_non_formula_input_kind(self):
        # finding 5 (MEDIUM): a declared NAME/SMILES/InChI must NOT be silently read as a formula (wrong species).
        for kind in (InputKind.SMILES, InputKind.NAME, InputKind.INCHI):
            resp = run_compilation(build_decompile_request("C6H6", input_kind=kind))
            assert resp.outcome is ResponseOutcome.INVALID_INPUT
            assert resp.exit_code == svc.EXIT_INVALID_INPUT

    def test_decompile_accepts_formula_and_auto(self):
        for kind in (InputKind.AUTO, InputKind.FORMULA):
            resp = run_compilation(build_decompile_request("H2O", input_kind=kind))
            assert resp.outcome is ResponseOutcome.ROUTES_FOUND

    def test_decompile_target_in_inventory_is_available_not_no_route(self):
        # finding 4 (LOW): a target that is itself a declared bucket is TARGET_ALREADY_AVAILABLE (exit 0), not a
        # section 8.3 no-route (exit 3) -- keyed by canonical formula identity (H2O == OH2).
        for spelling in ("H2O", "OH2"):
            resp = run_compilation(build_decompile_request(spelling, formula_inventory=("H2O",)))
            assert resp.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE
            assert resp.exit_code == svc.EXIT_SUCCESS

    def test_recompile_payload_with_decompile_bound_names_refused(self):
        # finding 6 (MEDIUM): operation<->bound-name incoherence fails closed at deserialization, not as a KeyError.
        payload = request_to_payload(build_recompile_request("name:water"))
        payload["search_bounds"] = [["budget", 100], ["max_edges", 5], ["max_multiplicity", 1]]
        with pytest.raises(ValueError, match="search bounds must be exactly"):
            request_from_payload(payload)

    def test_recompile_payload_with_formula_inventory_refused(self):
        # finding 2 (LOW): a RECOMPILE terminal policy carries no formula inventory.
        payload = request_to_payload(build_recompile_request("name:water"))
        tp = dict(payload["terminal_policy"])
        tp["formula_inventory"] = ["ZZ"]
        payload["terminal_policy"] = tp
        with pytest.raises(ValueError, match="no formula inventory"):
            request_from_payload(payload)

    def test_decompile_payload_with_structural_stock_refused(self):
        payload = request_to_payload(build_decompile_request("H2O"))
        payload["stock_materials"] = ["ethanol"]
        with pytest.raises(ValueError, match="no structural stock"):
            request_from_payload(payload)

    def test_response_status_must_equal_wrapped_ir(self, ir_incomplete):
        # finding 3 (MEDIUM): a response cannot report a section 8.2 status that contradicts its own IR, even an
        # engine-impossible one like INCOMPLETE_CANDIDATE_LIMIT.
        req = build_recompile_request("name:water")
        with pytest.raises(ValueError, match="must equal the wrapped IR"):
            CompilationResponse(
                COMPILATION_RESPONSE_SCHEMA, req, ResponseOutcome.INCOMPLETE,
                "INCOMPLETE_CANDIDATE_LIMIT", ir_incomplete, ("x",),
            )

    def test_deserialize_rejects_smuggled_status(self):
        # finding 3 via the deserialize path: a tampered standard_status is refused on read.
        resp = run_compilation(build_recompile_request("paracetamol", max_depth=2, cut_budget=5000))
        payload = response_to_payload(resp)
        assert payload["standard_status"] == "INCOMPLETE_DEPTH_LIMIT"
        payload["standard_status"] = "INCOMPLETE_CUT_BUDGET"  # contradicts the wrapped IR
        with pytest.raises(ValueError, match="must equal the wrapped IR"):
            response_from_payload(payload)

    def test_semantic_digest_is_a_safe_one_way_superset(self):
        # findings 1 & 8: the digest is a SUPERSET of what the engine reads -- a not-yet-consumed field SPLITS the
        # identity (a different digest) but the two requests still run the byte-identical search. Safe direction.
        a = build_decompile_request("C6H6", input_kind=InputKind.AUTO)
        b = build_decompile_request("C6H6", input_kind=InputKind.FORMULA)
        assert a.semantic_digest != b.semantic_digest  # split
        assert run_compilation(a).compilation_ir.digest == run_compilation(b).compilation_ir.digest  # same search
        # a placeholder policy differs -> split, same execution
        c = build_recompile_request("benzene", commodities_enabled=False, max_depth=2)
        d = build_recompile_request("benzene", commodities_enabled=False, max_depth=2, ranking_policy=RankingPolicy("COST"))
        assert c.semantic_digest != d.semantic_digest
        assert run_compilation(c).compilation_ir.digest == run_compilation(d).compilation_ir.digest

    def test_parse_smiles_message_quotes_prefixed_form(self):
        # finding 7 (LOW): the compat alias's error is byte-identical to the old helper (quotes the smiles: prefix).
        from smartchem.cli import _parse_smiles
        with pytest.raises(ValueError, match=r"smiles:not_valid_\$\$\$"):
            _parse_smiles("not_valid_$$$")
