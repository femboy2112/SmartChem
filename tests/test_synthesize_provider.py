"""CLI-CAN-02 (provider lever): ``synthesize``'s ``--offline`` is the typed request's LIVE section-9 lever.

The last chemical verb (``synthesize``) now builds the ONE shared ``CompilationRequest`` (SVC-REQ-01), and its
``--offline`` choice is carried as the request's :class:`EvidenceProviderSelection` -- which GOVERNS the real
network autoload.  These tests pin three things the arc's engineering lessons say a lever like this fails on:

* the lever is NON-INERT -- it is read from the request field on the LIVE production path (through the public
  ``synthesize`` ``main``), not merely settable in isolation (the "dead switch" hazard);
* it is sourced from the REQUEST, not from ``args.offline`` -- proven by forcing the two to disagree, the only
  test that catches a silent revert to the old ``allow_network=not args.offline`` (the dropped-kwarg hazard);
* the digest law is honest -- an ONLINE selection SPLITS the search identity while the OFFLINE default's digest is
  byte-unchanged (so the goldens do not move), and the split assertion actually fires (non-vacuous).
"""
from __future__ import annotations

import json

import smartchem.data.autoload as autoload_mod
import smartchem.experiment.cli as syn_cli
from smartchem.experiment.cli import main
from smartchem.service import (
    NETWORK_PROVIDER,
    OFFLINE_PROVIDER,
    EvidenceProviderSelection,
    build_recompile_request,
)

# A retrosynthesis invocation that genuinely produces routes offline, so the autoload IS reached (borrowed from
# the existing end-to-end route test).  ``--offline`` is appended/omitted per case.
_ROUTE_ARGV = [
    "CC(=O)Nc1ccc(O)cc1", "--have", "Nc1ccc(O)cc1",
    "--reagents", "O", "CC(=O)O", "CC(=O)OC(=O)C", "--max-depth", "3",
]


class TestAllowNetworkFailClosed:
    """The section-9 lever: only an explicitly network-enabled id fetches; everything else declines to offline."""

    def test_offline_default_declines_network(self):
        assert OFFLINE_PROVIDER.allow_network is False
        assert EvidenceProviderSelection().allow_network is False  # the bare default is offline

    def test_network_provider_allows_network(self):
        assert NETWORK_PROVIDER.allow_network is True
        assert EvidenceProviderSelection("DEFAULT_NETWORK").allow_network is True

    def test_unrecognised_id_fails_closed_to_offline(self):
        # An id that SOUNDS online must still not silently reach the network -- fail-closed, exactly like the
        # phase normaliser declining an unknown medium.  Only ids with a real fetcher earn network permission.
        assert EvidenceProviderSelection("PUBCHEM").allow_network is False
        assert EvidenceProviderSelection("some-unknown-provider").allow_network is False

    def test_offline_provider_is_byte_identical_to_the_default(self):
        # Zero digest churn: OFFLINE_PROVIDER must equal the historical default, or every pinned offline digest
        # (and the golden fixtures) would move.
        assert OFFLINE_PROVIDER == EvidenceProviderSelection()
        assert OFFLINE_PROVIDER.digest == EvidenceProviderSelection().digest


class TestProviderDigestLaw:
    """Online splits the search identity; offline is unchanged.  The split is asserted, not merely referenced."""

    def test_online_splits_semantic_digest_offline_leaves_it_unchanged(self):
        base = build_recompile_request("name:water")  # provider defaulted -> offline
        offline = build_recompile_request("name:water", evidence_provider_selection=OFFLINE_PROVIDER)
        online = build_recompile_request("name:water", evidence_provider_selection=NETWORK_PROVIDER)
        # offline == default on the SEARCH identity (origins differ, so the full digest legitimately does not):
        assert offline.semantic_digest == base.semantic_digest
        # ...and ONLINE is a genuinely different search (an online run may source evidence offline cannot):
        assert online.semantic_digest != offline.semantic_digest

    def test_provider_selection_is_the_only_thing_that_moved(self):
        # The split is due to the provider, not an incidental field: same target, same everything else.
        online = build_recompile_request("name:water", evidence_provider_selection=NETWORK_PROVIDER)
        assert online.evidence_provider_selection is NETWORK_PROVIDER
        assert online.evidence_provider_selection.allow_network is True


class TestSynthesizeProviderLeverIsLive:
    """Through the PUBLIC ``synthesize`` main: the request field DRIVES the real autoload."""

    def _spy_autoload(self, monkeypatch):
        """Replace autoload_stability with a spy that RECORDS the requested allow_network and then runs OFFLINE
        (so the network is never actually touched, even in the allow_network=True case)."""
        captured: list[bool] = []
        real = autoload_mod.autoload_stability

        def spy(*args, **kwargs):
            captured.append(kwargs.get("allow_network"))
            kwargs["allow_network"] = False  # never fetch in the test; we only care WHAT was requested
            return real(*args, **kwargs)

        monkeypatch.setattr(autoload_mod, "autoload_stability", spy)
        return captured

    def test_offline_flag_requests_no_network(self, monkeypatch, capsys):
        captured = self._spy_autoload(monkeypatch)
        code = main([*_ROUTE_ARGV, "--offline"])
        assert code == 0  # the known route-producing case
        assert captured and captured[-1] is False

    def test_no_offline_flag_requests_network(self, monkeypatch, capsys):
        captured = self._spy_autoload(monkeypatch)
        code = main(list(_ROUTE_ARGV))  # no --offline
        assert code == 0
        assert captured and captured[-1] is True

    def test_allow_network_is_read_from_the_request_not_args_offline(self, monkeypatch, capsys):
        """The dropped-kwarg killer: force the request to say NETWORK while argv says --offline.  If main reads the
        REQUEST field (correct) the autoload is asked for network=True; if it reverted to ``not args.offline`` it
        would be False.  This is the ONLY case where the two sources disagree, so it is the one that catches it."""
        captured = self._spy_autoload(monkeypatch)

        def forced_network(args):
            # a FULL request (reagents/stock kept, so the search still produces routes) whose provider is NETWORK
            # regardless of --offline -- the only way to force the request field and argv --offline to disagree while
            # the search still reaches the autoload, now that the main sources its search inputs from the REQUEST.
            return build_recompile_request(
                args.target,
                helper_reagents=tuple(args.reagents),
                stock_materials=tuple(args.have),
                max_depth=args.max_depth,
                evidence_provider_selection=NETWORK_PROVIDER,
            )

        monkeypatch.setattr(syn_cli, "_synthesize_request", forced_network)
        code = main([*_ROUTE_ARGV, "--offline"])  # argv SAYS offline...
        assert code == 0
        assert captured and captured[-1] is True  # ...but the autoload followed the REQUEST field


class TestSynthesizeEmitRequest:
    """--emit-request echoes the canonical identity, carrying the provider selection, WITHOUT searching."""

    def test_emit_request_offline_carries_offline_provider_and_does_not_search(self, monkeypatch, capsys):
        # synthesize now renders through the shared compile_synthesis engine (lazily imported); patch it at its source
        # module so a search under --emit-request would boom.  It must not: --emit-request exits before the engine.
        import smartchem.experiment.compile as compile_mod

        def _boom(*a, **k):
            raise AssertionError("the shared engine must not run under --emit-request")

        monkeypatch.setattr(compile_mod, "compile_synthesis", _boom)
        code = main(["paracetamol", "--offline", "--emit-request"])  # _boom never fires -> emit exits before the engine
        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["evidence_provider_selection"]["selection_id"] == "DEFAULT_OFFLINE"

    def test_emit_request_online_carries_network_provider(self, capsys):
        code = main(["paracetamol", "--emit-request"])  # no --offline -> network provider on the identity
        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["evidence_provider_selection"]["selection_id"] == "DEFAULT_NETWORK"

    def test_emit_request_offline_and_online_are_different_identities(self, capsys):
        off = json.loads(_run_capsys(capsys, ["paracetamol", "--offline", "--emit-request"]))
        on = json.loads(_run_capsys(capsys, ["paracetamol", "--emit-request"]))
        assert off["evidence_provider_selection"]["selection_id"] == "DEFAULT_OFFLINE"
        assert on["evidence_provider_selection"]["selection_id"] == "DEFAULT_NETWORK"
        assert off != on  # the emitted identity genuinely differs by the provider selection (no digest key is emitted)


class TestRedTeamFolds:
    """Folds for the CLI-CAN-02 provider-lever red-team (workflow wqpxvm0lh): building the request early moved its
    validation OUTSIDE the domain-error handler, so a degenerate input regressed from a clean exit 2 to exit 70 /
    a raw traceback; and --emit-request misrepresented an empty --reagents. Both are now fixed and pinned here."""

    def test_empty_target_is_a_clean_exit_2_not_internal_error(self, capsys):
        # was: build-time ValueError escaped -> exit 70 (top) / traceback (experiment entry). Now: clean exit 2.
        assert main([""]) == 2
        err = capsys.readouterr().err
        assert "Traceback" not in err
        assert "synthesize:" in err

    def test_whitespace_target_is_a_clean_exit_2(self, capsys):
        assert main(["   "]) == 2
        assert "Traceback" not in capsys.readouterr().err

    def test_empty_string_reagent_is_a_clean_exit_2(self, capsys):
        assert main(["name:water", "--reagents", ""]) == 2  # '' is an invalid reagent -> TypeError at build -> 2
        assert "Traceback" not in capsys.readouterr().err

    def test_empty_string_have_is_a_clean_exit_2(self, capsys):
        assert main(["name:water", "--have", ""]) == 2
        assert "Traceback" not in capsys.readouterr().err

    def test_valueless_reagents_flag_is_a_clean_exit_2_not_a_traceback(self, capsys):
        # `--reagents` with no values -> the search runs with () reagents and raises TypeError; the extended handler
        # now maps it to a clean exit 2 instead of letting the traceback escape (a bonus of the same fold).
        assert main(["CC(=O)O", "--reagents", "--offline"]) == 2
        assert "Traceback" not in capsys.readouterr().err

    def test_top_level_synthesize_matches_recompile_exit_code_on_the_same_builder_error(self, capsys):
        # the red-team's sharpest point: `recompile ''` and `synthesize ''` raise the IDENTICAL builder error and
        # must not disagree on the exit code (SVC-REQ-01 alias-independence). Both are exit 2 through the top-level
        # guarded CLI -- synthesize no longer launders it into exit 70 (ERROR_INTERNAL).
        from smartchem.cli import main as top_main
        assert top_main(["synthesize", ""]) == 2
        assert top_main(["recompile", ""]) == 2
        assert "ERROR_INTERNAL" not in capsys.readouterr().err

    def test_emit_request_faithfully_carries_empty_reagents(self, capsys):
        # Finding 1: a valueless --reagents means ZERO reagents in the real search; emit must show that, not the
        # builder's water default. The raw arg list is now passed through, so the identity matches the search.
        payload = json.loads(_run_capsys(capsys, ["CC(=O)O", "--reagents", "--emit-request"]))
        assert payload["helper_reagents"] == []

    def test_emit_request_carries_the_given_reagent_set(self, capsys):
        payload = json.loads(_run_capsys(capsys, ["CC(=O)O", "--reagents", "acetic acid", "--emit-request"]))
        assert payload["helper_reagents"] == ["acetic acid"]


class TestSynthesizeRendersThroughSharedEngine:
    """CLI-CAN-02 remainder: synthesize's human dossier renders through the ONE shared engine (compile_synthesis),
    built from the typed request -- its own second search/rank/resolve engine is DELETED."""

    def test_the_second_engine_names_are_gone_from_synthesize(self):
        # importing search_routes/rank_routes/draft_route_dossier into experiment.cli WAS the second engine; their
        # absence from the module namespace is the structural proof synthesize no longer runs its own search here.
        assert not hasattr(syn_cli, "search_routes")
        assert not hasattr(syn_cli, "rank_routes")
        assert not hasattr(syn_cli, "draft_route_dossier")

    def test_human_dossier_is_the_shared_compile_synthesis_render(self, capsys):
        code = main([*_ROUTE_ARGV, "--offline"])
        out = capsys.readouterr().out
        assert code == 0
        assert "COMPILED SYNTHESIS" in out       # the shared engine's header
        assert "OVERALL GRADE (L2)" in out       # graded through the shared engine (the old inline path never graded)

    def test_an_unresolvable_target_is_a_clean_exit_2_through_the_one_parser(self, capsys):
        # the target resolves through the ONE parser service (resolve_target_with_features), not a second resolver;
        # an unresolvable target is a clean section-14.4 exit 2 -- concise, no traceback.
        assert main(["definitely-not-a-molecule-@@@", "--offline"]) == 2
        err = capsys.readouterr().err
        assert "Traceback" not in err and "synthesize:" in err


class TestSynthesizeJsonThroughService:
    """--json runs the request through the ONE service (run_compilation): synthesize's machine contract IS
    run_compilation's typed response, describing the SAME request --emit-request echoes."""

    def test_json_returns_the_service_exit_code_and_a_typed_response(self, capsys):
        code = main(["paracetamol", "--offline", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert "result_digest" in payload
        assert payload["outcome"] in {
            "ROUTES_FOUND", "NO_ROUTE_COMPLETE", "INCOMPLETE", "TARGET_ALREADY_AVAILABLE", "REFUSED", "INVALID_INPUT"
        }
        assert code == payload["exit_code"]      # the CLI returns run_compilation's own section-14.4 exit code

    def test_json_and_emit_request_describe_the_same_request(self, capsys):
        main(["paracetamol", "--offline", "--json"])
        resp = json.loads(capsys.readouterr().out)
        main(["paracetamol", "--offline", "--emit-request"])
        emit = json.loads(capsys.readouterr().out)
        assert resp["request"] == emit           # one request identity, two machine views

    def test_empty_reagents_is_exit_2_on_both_json_and_human(self, capsys):
        # the two corridors AGREE: a valueless --reagents is INVALID on run_compilation (--json) AND the human path.
        assert main(["CC(=O)O", "--reagents", "--offline", "--json"]) == 2
        assert main(["CC(=O)O", "--reagents", "--offline"]) == 2
        assert "Traceback" not in capsys.readouterr().err


class TestStabilityLoaderSeam:
    """The compile_synthesis stability_loader (CLI-CAN-02 remainder): invoked AFTER the search with the discovered
    species (intermediates included); None for every non-synthesize caller so the ranked result is unmoved."""

    @staticmethod
    def _target_reagents_available():
        from smartchem.experiment.cli import _parse
        from smartchem.identity_parse import resolve_target
        target = resolve_target("CC(=O)Nc1ccc(O)cc1")
        reagents = tuple(_parse(s) for s in ("O", "CC(=O)O", "CC(=O)OC(=O)C"))
        available = (resolve_target("Nc1ccc(O)cc1"),)
        return target, reagents, available

    def test_loader_is_invoked_with_the_discovered_route_species(self):
        from smartchem.experiment.compile import _ident, compile_synthesis
        target, reagents, available = self._target_reagents_available()
        captured = {}

        def loader(species):
            captured["species"] = species
            return None                          # None -> seed stability; we assert only WHAT the loader received

        compile_synthesis(target, reagents=reagents, available=available, commodities=(), max_depth=3,
                          stability_loader=loader)
        assert captured.get("species")           # the loader ran, post-search, over a non-empty species set
        # the species cover the ROUTE the search discovered, not merely the CLI inputs: the target is present
        assert _ident(target) in {_ident(m) for m in captured["species"]}

    def test_no_loader_means_no_autoload(self, monkeypatch):
        # every non-synthesize caller (compile) passes no loader, so the loader branch is skipped and no autoload
        # runs -- the ranked result stays byte-identical (goldens safe).  Prove it: autoload booms if ever called.
        import smartchem.data.autoload as autoload_mod

        def _boom(*a, **k):
            raise AssertionError("no stability_loader -> autoload must not run")

        monkeypatch.setattr(autoload_mod, "autoload_stability", _boom)
        target, reagents, available = self._target_reagents_available()
        from smartchem.experiment.compile import compile_synthesis
        compiled = compile_synthesis(target, reagents=reagents, available=available, commodities=(), max_depth=3)
        assert compiled.found_route              # still compiled -- with seed stability, no autoload


def _run_capsys(capsys, argv) -> str:
    assert main(argv) == 0
    return capsys.readouterr().out
