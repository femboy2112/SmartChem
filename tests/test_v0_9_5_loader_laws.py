"""0.9.5 loader laws (barrier docs/research/V0_9_5_ARCHITECTURE_FREEZE.md sections 1-5): the ONE policy, the
out-of-band receipt, S1 (canonical requirement), S2 (the work budget), S6 (no payload-path I/O), the per-load
reconstruction memo and the bounded enumeration cache.

Each test names the broken behaviour it fails on.  The cheap methyl acetate family carries every law; no test here
compiles the slow isopentyl search.
"""
from __future__ import annotations

import builtins
import copy
import json
import os
import tempfile
from pathlib import Path

import pytest

from smartchem.identity_parse import InputKind
from smartchem.service import (
    build_recompile_request,
    deserialize_response,
    load_response,
    load_response_text,
    response_from_payload,
    response_to_payload,
    run_compilation,
)
from smartchem.verification import (
    ENUMERATION_CACHE,
    DigestRule,
    PinState,
    SchemaGeneration,
    SearchOutputTrust,
    SignatureState,
    VerificationBudget,
    VerificationBudgetExceeded,
    VerificationPolicy,
    VerifiedLoad,
    set_enumeration_cache_enabled,
)

_KEY = b"0.9.5-loader-law-test-key-32bytes"
_V08 = Path(__file__).parent / "fixtures" / "v08"


@pytest.fixture(scope="module")
def honest():
    """methyl acetate (2 routes) under the poor-man bench: a canonical thick answer with a capability question."""
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man"))
    return resp, response_to_payload(resp), response_to_payload(resp, include_replay=False)


def _pinned(resp, **extra):
    return VerificationPolicy(expected_request_digest=resp.request.semantic_digest,
                              expected_capability_question_digest=resp.request.capability_question_digest, **extra)


# ---------------------------------------------------------------------------------------------------------------------
# the receipt: what ONE load established, facet by facet
# ---------------------------------------------------------------------------------------------------------------------

def test_plain_canonical_load_receipt(honest):
    resp, thick, _thin = honest
    loaded = load_response(copy.deepcopy(thick))
    assert isinstance(loaded, VerifiedLoad)
    r = loaded.receipt
    assert loaded.response.result_digest == resp.result_digest
    assert (r.schema_generation, r.transport_mode, r.digest_rule) == (
        SchemaGeneration.CURRENT, "CANONICAL_VERIFIED", DigestRule.WHOLE_BODY)
    assert (r.request_pin, r.capability_pin, r.signature) == (
        PinState.NOT_PINNED, PinState.NOT_PINNED, SignatureState.NOT_CHECKED)
    # every dossier's replay was actually reconstructed -- ONCE each (the memo), and counted
    assert r.replay_rederived_routes == len(resp.ranked_route_dossiers) == 2
    assert r.search_output is SearchOutputTrust.ADVISORY      # the D25.3 boundary: no rerun, no signature
    assert r.work.dossiers == 2 and r.work.payload_nodes > 0 and r.work.enumeration_targets >= 1
    assert r.satisfies(VerificationPolicy())


def test_pinned_verified_admission_receipt_and_satisfies(honest):
    resp, thick, _thin = honest
    policy = _pinned(resp, require_verified_admission=True)
    r = load_response(copy.deepcopy(thick), policy).receipt
    assert (r.request_pin, r.capability_pin, r.verified_admission) == (PinState.CHECKED, PinState.CHECKED, True)
    assert r.satisfies(policy) and r.satisfies(VerificationPolicy())
    # a receipt from a weaker load does not satisfy a stronger requirement
    weak = load_response(copy.deepcopy(thick)).receipt
    assert not weak.satisfies(policy)


def test_signed_payload_receipt_is_authenticated(honest):
    resp, _thick, _thin = honest
    signed = response_to_payload(resp, signing_key=_KEY)
    r = load_response(signed, VerificationPolicy.authenticated(_KEY)).receipt
    assert r.signature is SignatureState.VERIFIED and r.search_output is SearchOutputTrust.AUTHENTICATED
    # a key WITHOUT require_signature on an unsigned payload: the receipt says so instead of implying authentication
    unsigned = response_to_payload(resp)
    r2 = load_response(unsigned, VerificationPolicy(verification_key=_KEY)).receipt
    assert r2.signature is SignatureState.NOT_REQUIRED_ABSENT and r2.search_output is SearchOutputTrust.ADVISORY


def test_thin_load_receipt_counts_no_replay(honest):
    _resp, _thick, thin = honest
    r = load_response(copy.deepcopy(thin)).receipt
    assert r.transport_mode == "THIN_ADVISORY"
    assert r.replay_rederived_routes == 0 and r.work.dossiers == 0


def test_legacy_v08_receipt():
    payload = json.loads((_V08 / "response_ethyl_acetate_smiles.json").read_text())
    r = load_response(payload).receipt
    assert (r.schema_generation, r.digest_rule, r.legacy_migrated) == (
        SchemaGeneration.LEGACY_V08, DigestRule.FROZEN_V08, True)


def test_response_from_payload_is_load_response_minus_the_receipt(honest):
    """The compat surface returns the identical response; the legacy kwargs and policy= cannot be mixed."""
    resp, thick, _thin = honest
    a = response_from_payload(copy.deepcopy(thick))
    b = load_response(copy.deepcopy(thick)).response
    assert a.result_digest == b.result_digest == resp.result_digest
    with pytest.raises(TypeError, match="either policy= or the legacy trust kwargs"):
        response_from_payload(copy.deepcopy(thick), policy=VerificationPolicy(), require_verified_admission=True)
    assert deserialize_response(json.dumps(thick), policy=VerificationPolicy()).result_digest == resp.result_digest
    assert load_response_text(json.dumps(thick)).response.result_digest == resp.result_digest


# ---------------------------------------------------------------------------------------------------------------------
# S1: the canonical requirement refuses THIN and legacy at dispatch -- before any decode
# ---------------------------------------------------------------------------------------------------------------------

def _spy_request_decode(monkeypatch):
    import smartchem.service as svc
    calls = []
    real = svc.request_from_payload
    monkeypatch.setattr(svc, "request_from_payload", lambda p: (calls.append(1), real(p))[1])
    return calls


def test_s1_thin_refused_under_canonical_before_decode(honest, monkeypatch):
    """Fails if a THIN payload loads under require_canonical_transport, or is decoded before the refusal."""
    _resp, _thick, thin = honest
    calls = _spy_request_decode(monkeypatch)
    with pytest.raises(ValueError, match=r"require_canonical_transport.*THIN_ADVISORY.*0\.9\.5 S1"):
        load_response(copy.deepcopy(thin), VerificationPolicy.canonical())
    assert calls == []


def test_s1_legacy_refused_under_canonical():
    payload = json.loads((_V08 / "response_ethyl_acetate_smiles.json").read_text())
    with pytest.raises(ValueError, match=r"legacy .* not canonical under 0\.9 semantics.*0\.9\.5 S1"):
        load_response(payload, VerificationPolicy.canonical())


def test_s1_canonical_thick_accepted_under_canonical(honest):
    _resp, thick, _thin = honest
    r = load_response(copy.deepcopy(thick), VerificationPolicy.canonical()).receipt
    assert r.transport_mode == "CANONICAL_VERIFIED" and r.satisfies(VerificationPolicy.canonical())


# ---------------------------------------------------------------------------------------------------------------------
# S6: the loader never touches the filesystem on payload content
# ---------------------------------------------------------------------------------------------------------------------

def test_s6_target_file_response_refused_and_path_never_opened(monkeypatch):
    """Fails if loading a TARGET_FILE answer (IR-less, under require_reexecution) opens the payload's path -- the 0.9
    loader did (parent-verified live)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "target.txt")
        Path(path).write_text("not a molecule zzz")
        bad = run_compilation(build_recompile_request(path, input_kind=InputKind.TARGET_FILE, max_depth=1))
        payload = response_to_payload(bad)
        opened = []
        real_open = builtins.open

        def spy(f, *a, **k):
            if str(f).startswith(d):
                opened.append(str(f))
            return real_open(f, *a, **k)
        monkeypatch.setattr(builtins, "open", spy)
        for kw in ({}, {"require_reexecution": True}):
            with pytest.raises(ValueError, match=r"TARGET_FILE response cannot be verified on load.*0\.9\.5 S6"):
                response_from_payload(copy.deepcopy(payload), **kw)
        assert opened == []


# ---------------------------------------------------------------------------------------------------------------------
# S2: verification work is a budgeted resource -- exhaustion refuses, never skips
# ---------------------------------------------------------------------------------------------------------------------

def test_s2_enumeration_budget_refuses_at_d29_1_not_as_an_unreadable_replay(honest):
    """methyl acetate's target has W = 200; a per-target budget of 100 must REFUSE with the budget error -- fails if
    the charge is skipped (the load then succeeds) or swallowed by D29.1's broad except (the message would read
    'cannot be put to the replayed step's target')."""
    _resp, thick, _thin = honest
    with pytest.raises(VerificationBudgetExceeded) as err:
        load_response(copy.deepcopy(thick), VerificationPolicy(budget=VerificationBudget(work_per_target=100)))
    assert err.value.counter == "work_per_target" and err.value.limit == 100


def test_s2_payload_node_budget_refuses_before_decode(honest, monkeypatch):
    _resp, thick, _thin = honest
    calls = _spy_request_decode(monkeypatch)
    with pytest.raises(VerificationBudgetExceeded) as err:
        load_response(copy.deepcopy(thick), VerificationPolicy(budget=VerificationBudget(payload_nodes=50)))
    assert err.value.counter == "payload_nodes" and calls == []


def test_s2_dossier_budget_refuses(honest):
    _resp, thick, _thin = honest
    with pytest.raises(VerificationBudgetExceeded, match="dossiers"):
        load_response(copy.deepcopy(thick), VerificationPolicy(budget=VerificationBudget(dossiers=1)))


def test_s2_reexecution_is_budgeted(honest):
    resp, thick, _thin = honest
    r = load_response(copy.deepcopy(thick), _pinned(resp, require_reexecution=True)).receipt
    assert r.reexecuted and r.work.reexecutions == 1 and r.search_output is SearchOutputTrust.REEXECUTED
    tight = VerificationBudget(work_per_target=100)   # the rerun's root enumeration (W = 200) is charged BEFORE running
    with pytest.raises(VerificationBudgetExceeded):
        load_response(copy.deepcopy(thick), _pinned(resp, require_reexecution=True, budget=tight))


def test_s2_bare_legacy_kwargs_get_the_default_budget(honest):
    """A bare response_from_payload is budgeted too (the default): its context meters the same load."""
    _resp, thick, _thin = honest
    assert response_from_payload(copy.deepcopy(thick)).result_digest == load_response(
        copy.deepcopy(thick), VerificationPolicy(budget=VerificationBudget.default())).response.result_digest


# ---------------------------------------------------------------------------------------------------------------------
# the memo and the cache: identity-preserving by construction
# ---------------------------------------------------------------------------------------------------------------------

def test_each_replay_is_reconstructed_once_per_load(honest, monkeypatch):
    """Fails if the loader rebuilds a replayed route per guard (0.9 did 5-7x per dossier -- Lane A/B)."""
    import smartchem.experiment.step as step_mod
    _resp, thick, _thin = honest
    built = []
    real = step_mod.ExperimentRoute.__post_init__

    def counting(self):
        built.append(1)
        return real(self)
    monkeypatch.setattr(step_mod.ExperimentRoute, "__post_init__", counting)
    load_response(copy.deepcopy(thick), VerificationPolicy(require_verified_admission=True))
    assert len(built) == 2        # two dossiers, one reconstruction each


def test_cache_on_off_byte_identical(honest):
    """The process cache is lossless: cache on vs off -> the identical accepted response and the identical work
    ledger (the budget never depends on cache state)."""
    _resp, thick, _thin = honest
    ENUMERATION_CACHE.clear()
    on_cold = load_response(copy.deepcopy(thick))
    on_warm = load_response(copy.deepcopy(thick))
    assert ENUMERATION_CACHE.stats().hits >= 1
    set_enumeration_cache_enabled(False)
    try:
        off = load_response(copy.deepcopy(thick))
    finally:
        set_enumeration_cache_enabled(True)
    payloads = {json.dumps(response_to_payload(x.response), sort_keys=True) for x in (on_cold, on_warm, off)}
    assert len(payloads) == 1
    assert on_cold.receipt.work == on_warm.receipt.work == off.receipt.work
