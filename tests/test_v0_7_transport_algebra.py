"""v0.7 Round II -- the production transform-ALGEBRA transport gate.

Round I proved the wider algebra widens `search_routes` in an experiment harness.  Round II makes the algebra a
real, selectable COMPILER capability: a request selects a content-bound, use-correct profile, and the exact algebra
survives through the whole `plan/recompile -> service -> search -> receipt -> IR -> response` path.  This file pins:

* the USE-INDEX guard (Course-Correction 1): a consumer refuses an incompatible registry BEFORE enumeration;
* the closed algebra-PROFILE registry (Course-Correction 2) + request-level selection + digest binding;
* the reagentless-algebra handling, the search/IR algebra-binding invariant, and serialization/tamper fail-closed.
"""
from __future__ import annotations

import pytest

from smartchem.algebra_profiles import (
    DEFAULT_ALGEBRA_PROFILE,
    PROFILE_USES,
    UnknownAlgebraProfileError,
    algebra_profile_ids,
    resolve_algebra_profile,
)
from smartchem.compilation_ir import decompile_structure_to_ir
from smartchem.experiment.routes import search_dags, search_routes
from smartchem.identity_parse import InputKind
from smartchem.service import (
    build_recompile_request,
    request_from_payload,
    request_to_payload,
    run_compilation,
)
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY,
    ProviderUse,
    UnsupportedProviderUseError,
    assert_registry_supports_use,
)


# -- Course-Correction 1: the use-index guard refuses incompatible registries BEFORE enumeration ----------------
def test_route_search_refuses_a_decompile_only_registry():
    decompile = resolve_algebra_profile("certified-decompile-v07")  # heterolytic + redox-half: STRUCTURE_DECOMPILE only
    chx = parse_smiles("C1CC=CCC1")
    with pytest.raises(UnsupportedProviderUseError):
        search_routes(chx, reagents=(), available=(), registry=decompile, max_depth=1)
    with pytest.raises(UnsupportedProviderUseError):
        search_dags(chx, reagents=(), available=(), registry=decompile, max_depth=1)


def test_structure_decompile_refuses_a_route_only_registry():
    route = resolve_algebra_profile("certified-route-v07")  # capped + DA: DA has no STRUCTURE_DECOMPILE
    with pytest.raises(UnsupportedProviderUseError):
        decompile_structure_to_ir(parse_smiles("CCO"), reagents=(parse_smiles("O"),), registry=route)


def test_certified_decompile_profile_is_a_live_admitted_decompile_algebra():
    # Positive control (Wave-C residual): certified-decompile-v07 is not dead safety code -- the use-guard ADMITS it
    # for STRUCTURE_DECOMPILE, and it is a live, non-empty algebra (18 real transforms on ethanol: heterolytic +
    # redox-half), distinct from the legacy default. It is library-only by design (no service DECOMPILE front door
    # threads it -- service DECOMPILE is formula descent), exercised here + by the route-refusal negative control.
    decompile = resolve_algebra_profile("certified-decompile-v07")
    assert_registry_supports_use(decompile, ProviderUse.STRUCTURE_DECOMPILE)  # admitted, no raise
    ethanol, water = parse_smiles("CCO"), parse_smiles("O")
    transforms, complete = decompile.enumerate(ethanol, (water,), budget=100_000)
    assert len(transforms) > 0 and complete
    assert {t.witness_kind for t in transforms} == {"HETEROLYTIC_SCISSION", "REDOX_HALF_REACTION"}
    # and the door is actually walked: decompile_structure_to_ir accepts it without a use-guard refusal.
    decompile_structure_to_ir(ethanol, reagents=(water,), registry=decompile)  # does not raise the guard


def test_the_default_algebra_still_serves_all_three_consumers():
    # legacy capped-scission is D+R+C admissible -- the guard is a no-op for the production default.
    assert_registry_supports_use(DEFAULT_TRANSFORM_REGISTRY, ProviderUse.LINEAR_ROUTE)
    assert_registry_supports_use(DEFAULT_TRANSFORM_REGISTRY, ProviderUse.CONVERGENT_DAG)
    assert_registry_supports_use(DEFAULT_TRANSFORM_REGISTRY, ProviderUse.STRUCTURE_DECOMPILE)


# -- the closed profile registry (Course-Correction 2) ----------------------------------------------------------
def test_profile_registry_is_closed_and_legacy_matches_the_default():
    assert set(algebra_profile_ids()) == {"legacy-capped-v1", "certified-route-v07", "certified-decompile-v07"}
    assert DEFAULT_ALGEBRA_PROFILE == "legacy-capped-v1"
    legacy = resolve_algebra_profile("legacy-capped-v1")
    assert legacy.provider_ids == DEFAULT_TRANSFORM_REGISTRY.provider_ids
    assert legacy.digest == DEFAULT_TRANSFORM_REGISTRY.digest  # constructing the wider profiles did not flip the default
    route = resolve_algebra_profile("certified-route-v07")
    assert route.provider_ids[0] == "capped-scission-mediated" and len(route.provider_ids) == 9
    assert route.digest != legacy.digest


def test_unknown_profile_is_a_typed_refusal_not_a_keyerror():
    with pytest.raises(UnknownAlgebraProfileError):
        resolve_algebra_profile("does-not-exist")


def test_profile_use_coherence_is_computed_from_membership():
    assert PROFILE_USES["certified-route-v07"] == frozenset({ProviderUse.LINEAR_ROUTE, ProviderUse.CONVERGENT_DAG})
    assert PROFILE_USES["certified-decompile-v07"] == frozenset({ProviderUse.STRUCTURE_DECOMPILE})


# -- request-level algebra selection + digest binding -----------------------------------------------------------
def _req(profile, reagents=("water",), grammar=None):
    return build_recompile_request(
        "C1CC=CCC1", input_kind=InputKind.SMILES, helper_reagents=reagents,
        stock_materials=("C=CC=C", "C=C"), grammar=grammar, algebra_profile=profile,
    )


def test_semantic_digest_moves_with_the_selected_algebra():
    assert _req("legacy-capped-v1").semantic_digest != _req("certified-route-v07").semantic_digest


def test_request_default_profile_is_legacy_and_origin_tracked():
    r = build_recompile_request("C1CC=CCC1", input_kind=InputKind.SMILES)
    assert r.algebra_profile == "legacy-capped-v1"
    origins = dict(r.origins)
    assert origins["algebra_profile"].value == "DEFAULT"
    explicit = build_recompile_request("C1CC=CCC1", input_kind=InputKind.SMILES, algebra_profile="certified-route-v07")
    assert dict(explicit.origins)["algebra_profile"].value == "EXPLICIT"


def test_unknown_or_incompatible_profile_fails_closed_at_construction():
    with pytest.raises(ValueError):
        _req("bogus-profile")
    # a decompile-only profile cannot be selected under a route grammar.
    with pytest.raises(ValueError):
        _req("certified-decompile-v07")


# -- the forcing consumer: the exact algebra reaches the REAL service ------------------------------------------
def test_certified_route_algebra_reaches_run_compilation_and_finds_the_da_route():
    resp = run_compilation(_req("certified-route-v07", reagents=()))
    assert resp.exit_code == 0  # cyclohexene -> butadiene + ethylene, reagentless, through the actual compiler
    # the default algebra cannot make cyclohexene: the wider algebra is what unlocks it.
    assert run_compilation(_req("legacy-capped-v1", reagents=("water",))).exit_code == 3


def test_reagentless_certified_algebra_runs_but_legacy_still_refuses_an_empty_pool():
    # certified-route-v07 carries reagentless DA families -> an empty helper pool is a runnable search.
    assert run_compilation(_req("certified-route-v07", reagents=())).exit_code == 0
    # legacy capped-scission needs a cutting reagent -> empty pool fails closed (no invented water).
    assert run_compilation(_req("legacy-capped-v1", reagents=())).exit_code == 2


# -- serialization + tamper (fail-closed) -----------------------------------------------------------------------
def test_serialization_round_trips_the_profile():
    r = _req("certified-route-v07")
    back = request_from_payload(request_to_payload(r))
    assert back.algebra_profile == "certified-route-v07"
    assert back.semantic_digest == r.semantic_digest


def test_tampered_serialized_profile_fails_closed_on_deserialize():
    payload = request_to_payload(_req("certified-route-v07"))
    payload["algebra_profile"] = "smuggled-unknown-profile"
    with pytest.raises(ValueError):
        request_from_payload(payload)


def test_a_pre_0_7_payload_without_a_profile_defaults_to_legacy():
    payload = request_to_payload(_req("legacy-capped-v1"))
    del payload["algebra_profile"]  # simulate a pre-0.7 serialized request
    assert request_from_payload(payload).algebra_profile == "legacy-capped-v1"
