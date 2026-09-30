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


# ---------------------------------------------------------------------------------------------------------------------
# S3 / S4 / S5 / S11 / C7-3 -- the Wave-A structure-theorem kills (Lane G F1-F4) and the DAG ledger parity (Lane E),
# as permanent regressions.  Every forgery is COHERENT: the keyless forger recomputes every public pin, so only the law
# under test can refuse it (asserted by its own tag).
# ---------------------------------------------------------------------------------------------------------------------

import dataclasses as dc  # noqa: E402

from smartchem import compilation_ir as cir  # noqa: E402
from smartchem import service as svc  # noqa: E402

_DERIVED = ("process_selection_status", "admissible_route_digests", "exit_code", "search_space_status",
            "capability_question_digest")
_PAIR = dict(max_depth=2, helper_reagents=("water", "acetic acid"), capability_profile="poor-man")


def _raw(p):
    ir = p["compilation_ir"]
    return svc.CompilationResponse(
        p["schema_version"], svc.request_from_payload(p["request"]), svc.ResponseOutcome(p["outcome"]),
        p["standard_status"], None if ir is None else cir.ir_from_payload(ir), tuple(p["diagnostics"]),
        tuple(svc.ranked_summary_from_payload(r) for r in p["ranked_route_dossiers"]),
        tuple(svc.affordability_entry_from_payload(e) for e in p["affordability_frontier"]),
        tuple(svc.provider_snapshot_from_payload(s) for s in p["provider_snapshots"]),
        parse_receipt_summary=p["parse_receipt_summary"],
        ranked_dag_dossiers=tuple(svc.ranked_dag_summary_from_payload(d) for d in p["ranked_dag_dossiers"]))


def _reforge(p):
    """The keyless forger: every derived wire key and the whole-body wire digest recomputed from the forged content."""
    raw = _raw(p)
    for key in _DERIVED:
        value = getattr(raw, key)
        p[key] = list(value) if key == "admissible_route_digests" else value
    p["result_digest"] = svc._transport_bound_result_digest(raw.result_digest, p["transport_mode"],
                                                           svc._payload_body_digest(p))
    return json.loads(json.dumps(p))


def _modes(req):
    pins = dict(expected_request_digest=req.semantic_digest,
                expected_capability_question_digest=req.capability_question_digest)
    return ({}, pins, dict(pins, require_verified_admission=True))


def _transplant_search(into, source, *, receipt_keys=("status", "standard_status", "nodes_visited",
                                                        "transforms_considered", "candidates_emitted",
                                                        "results_returned", "candidates_rejected_by_reason",
                                                        "cut_enumeration_complete", "candidate_enumeration_complete",
                                                        "result_limit_saturated", "stop_reason")):
    """Carry ``source``'s whole search output (dossiers, IR candidates, status, receipt counts) under ``into``'s request."""
    forged = copy.deepcopy(into)
    for k in ("ranked_route_dossiers", "ranked_dag_dossiers", "affordability_frontier", "diagnostics", "outcome",
              "standard_status"):
        forged[k] = copy.deepcopy(source[k])
    for k in ("candidates", "search_status", "standard_status", "diagnostics"):
        forged["compilation_ir"][k] = copy.deepcopy(source["compilation_ir"][k])
    for k in receipt_keys:
        forged["compilation_ir"]["search_receipt"][k] = copy.deepcopy(source["compilation_ir"]["search_receipt"][k])
    return forged


def test_s3_more_answers_than_the_pinned_limit_is_refused():
    """Lane G F1: the 3-route answer of a max_routes=100 search carried under a pinned max_routes=1 request (receipt
    bounds kept = the request's) LOADED in every keyless mode on 0.9; S3 refuses it before any reconstruction."""
    narrow = svc.build_recompile_request("smiles:CC(=O)OC", max_routes=1, **_PAIR)
    wide = svc.build_recompile_request("smiles:CC(=O)OC", max_routes=100, **_PAIR)
    forged = json.loads(json.dumps(_transplant_search(response_to_payload(run_compilation(narrow)),
                                                      response_to_payload(run_compilation(wide)))))
    assert forged["compilation_ir"]["search_receipt"]["results_returned"] > 1
    # S3 is a CONSTRUCTION law (CompilationResponse.__post_init__): the keyless forger cannot even build the response
    # object it needs to recompute the public digests ...
    with pytest.raises(ValueError, match=r"\(0\.9\.5 S3\)"):
        _reforge(copy.deepcopy(forged))
    # ... and the loader refuses the payload before any digest comparison, in every keyless mode.
    for kw in _modes(narrow):
        with pytest.raises(ValueError, match=r"result_limit is 1 .*\(0\.9\.5 S3\)"):
            response_from_payload(copy.deepcopy(forged), **kw)


def _renumbered(replay, seed):
    """The same route with every molecule's atoms renumbered (one consistent spelling per molecule) -- Lane G's respell."""
    import random
    rng, cache, out = random.Random(seed), {}, copy.deepcopy(replay)

    def perm(m):
        n = len(m["atoms"])
        order = list(range(n))
        rng.shuffle(order)
        inv = {old: new for new, old in enumerate(order)}
        return dict(m, atoms=[m["atoms"][order[i]] for i in range(n)],
                    bonds=sorted([min(inv[i], inv[j]), max(inv[i], inv[j]), o] for i, j, o in m["bonds"]))
    for step in out:
        for key in ("target", "reactants", "products"):
            mols = [step[key]] if key == "target" else step[key]
            new = [cache.setdefault(repr(m), perm(m)) for m in mols]
            step[key] = new[0] if key == "target" else new
    return out


def test_s4_a_respelled_duplicate_route_is_refused():
    """Lane G F3: one route's atoms renumbered is a 'new' route digest that every identity law (D26.1, D29.1, D27.1,
    conservation) passes and every tally counts again -- 0.9 loaded k copies under both pins + verified admission, with
    load time linear in k.  S4 keys dossiers on their STRUCTURE chemistry and refuses the duplicate."""
    req = svc.build_recompile_request("smiles:CC(=O)OC", max_routes=100, **_PAIR)
    honest = run_compilation(req)
    base = response_to_payload(honest)
    replays = [d.replay_payload for d in honest.ranked_route_dossiers]
    replays.append(_renumbered(replays[0], seed=7))
    routes = tuple(svc._reconstruct_route(r) for r in replays)
    assert len({r.digest for r in routes}) == len(routes), "setup: the renumbered copy must carry a NEW route digest"
    ranked = svc._ranked_summaries(routes, req.constraints.bounds, honest.identity_losses,
                                   process=req.constraints.process, capability_profile=req.capability_profile)
    forged = copy.deepcopy(base)
    forged["ranked_route_dossiers"] = [svc.ranked_summary_to_payload(s, include_replay=True) for s in ranked]
    forged["affordability_frontier"] = [svc.affordability_entry_to_payload(e)
                                        for e in svc._route_frontier(req, routes, ranked)]
    ir = forged["compilation_ir"]
    schema = ir["candidates"][0]["schema_version"]
    ir["candidates"] = sorted(({"schema_version": schema, "candidate_kind": "ROUTE", "candidate_digest": s.route_digest,
                                "equation": s.equation, "readiness_tier": "FORMAL_CANDIDATE"} for s in ranked),
                              key=lambda c: c["candidate_digest"])
    ir["search_receipt"]["results_returned"] = len(ranked)
    ir["search_receipt"]["candidates_emitted"] = max(ir["search_receipt"]["candidates_emitted"] or 0, len(ranked))
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(ranked), process=req.constraints.process)
    forged["diagnostics"] = list(ir["diagnostics"]) + ([note] if note else [])
    forged = _reforge(forged)
    for kw in _modes(req):
        with pytest.raises(ValueError, match=r"same chemistry as route dossier .*\(0\.9\.5 S4\)"):
            response_from_payload(copy.deepcopy(forged), **kw)


def test_s5_a_dag_higher_than_the_pinned_depth_is_refused():
    """Lane G F4: the convergent answers of a max_depth=3 search carried under a pinned max_depth=1 request loaded on
    0.9 (the DAG leg was bound only through the receipt label).  S5 bounds the DAG's HEIGHT, not its step count."""
    from smartchem.process_constraints import ProcessBounds
    kw = dict(helper_reagents=("water", "acetic acid"), grammar=svc.TransformGrammar.CAPPED_SCISSION_CONVERGENT,
              process=ProcessBounds.of(max_total_minutes=30.0))
    shallow = svc.build_recompile_request("smiles:CC(=O)OC", max_depth=1, **kw)
    deep = svc.build_recompile_request("smiles:CC(=O)OC", max_depth=3, **kw)
    deep_resp = run_compilation(deep)
    assert max(svc._dag_height(svc._reconstruct_dag(d.replay_payload)) for d in deep_resp.ranked_dag_dossiers) > 1
    forged = _transplant_search(response_to_payload(run_compilation(shallow)), response_to_payload(deep_resp))
    ir = forged["compilation_ir"]
    ir["diagnostics"] = list(cir.recompile_ir_diagnostics(
        target_in_terminal_stock=False, complete_within_bounds=ir["search_status"] == "COMPLETE_WITHIN_BOUNDS",
        status_value=ir["search_status"], has_candidates=bool(ir["candidates"]),
        mode=svc._GRAMMAR_TO_MODE[shallow.transform_grammar], max_depth=1))
    deep_ir_diag = response_to_payload(deep_resp)["compilation_ir"]["diagnostics"]
    forged["diagnostics"] = ir["diagnostics"] + response_to_payload(deep_resp)["diagnostics"][len(deep_ir_diag):]
    forged = _reforge(forged)
    for mode in _modes(shallow):
        with pytest.raises(ValueError, match=r"steps high .*max_depth=1 .*\(0\.9\.5 S5\)"):
            response_from_payload(copy.deepcopy(forged), **mode)


def test_s5_honest_dags_are_within_their_height_bound():
    """S5's premise, measured (never assumed): honest convergent DAGs carry MORE steps than max_depth but never a greater
    HEIGHT -- a step-count law would refuse honest answers."""
    from smartchem.process_constraints import ProcessBounds
    resp = run_compilation(svc.build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, grammar=svc.TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        helper_reagents=("water", "acetic acid"), process=ProcessBounds.of(max_total_minutes=30.0)))
    dags = [svc._reconstruct_dag(d.replay_payload) for d in resp.ranked_dag_dossiers]
    assert dags and all(svc._dag_height(d) <= 2 for d in dags)
    assert any(len(d.steps) > 2 for d in dags), "the premise the law rests on: step count > max_depth occurs honestly"


def test_s11_a_consistent_no_route_rewrite_is_the_disclosed_advisory_boundary():
    """The ledger does not over-claim (S11): outcome / exit_code / search_space_status are re-derived only from the
    ADVISORY search output, so a CONSISTENT 'no route' rewrite loads keylessly (the disclosed D25.3 boundary, Lane G F2)
    -- and the receipt says the search output is ADVISORY -- while re-execution refuses it."""
    req = svc.build_recompile_request("smiles:CC(=O)OC", max_routes=100, **_PAIR)
    forged = response_to_payload(run_compilation(req))
    forged["ranked_route_dossiers"], forged["affordability_frontier"] = [], []
    ir, rc = forged["compilation_ir"], forged["compilation_ir"]["search_receipt"]
    ir["candidates"] = []
    ir["search_status"] = rc["status"] = "COMPLETE_WITHIN_BOUNDS"
    ir["standard_status"] = rc["standard_status"] = forged["standard_status"] = \
        cir.SearchStatus("COMPLETE_WITHIN_BOUNDS").standard_name
    rc.update(results_returned=0, candidates_emitted=0, cut_enumeration_complete=True,
              candidate_enumeration_complete=True, result_limit_saturated=False, stop_reason="",
              candidates_rejected_by_reason=[])
    ir["diagnostics"] = list(cir.recompile_ir_diagnostics(
        target_in_terminal_stock=False, complete_within_bounds=True, status_value="COMPLETE_WITHIN_BOUNDS",
        has_candidates=False, mode="routes", max_depth=2))
    note = svc.constraint_note(req.constraints.bounds, fit_counts=None, process=req.constraints.process)
    forged["diagnostics"] = ir["diagnostics"] + ([note] if note else [])
    forged["outcome"] = "NO_ROUTE_COMPLETE"
    forged = _reforge(forged)
    loaded = load_response(copy.deepcopy(forged), _pinned_req(req, require_verified_admission=True))
    assert loaded.response.outcome.value == "NO_ROUTE_COMPLETE"
    assert loaded.receipt.search_output is SearchOutputTrust.ADVISORY
    with pytest.raises(ValueError, match=r"require_reexecution"):
        load_response(copy.deepcopy(forged), _pinned_req(req, require_reexecution=True))


def _pinned_req(req, **extra):
    return VerificationPolicy(expected_request_digest=req.semantic_digest,
                              expected_capability_question_digest=req.capability_question_digest, **extra)


def test_c7_3_a_forged_dag_step_is_refused_by_d29_1():
    """Wave C7 C7-3 (Lane E): ledger parity for the DAG leg -- a DAG step whose acetic-acid byproduct is swapped for
    the same-formula isomer methyl formate (envelope re-looked-up, every dependent field reforged with the producer's
    own helpers) must be refused by D29.1 itself, exactly like the route leg."""
    from smartchem.experiment import routes as _routes
    from smartchem.experiment.dag import DAG_SCHEMA, SynthesisDAG
    from smartchem.experiment.drafter import ConstraintBox
    from smartchem.process_constraints import ProcessBounds
    from smartchem.smiles import parse_smiles

    resp = run_compilation(svc.build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, grammar=svc.TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        helper_reagents=("water", "acetic acid"), process=ProcessBounds.of(max_total_minutes=30.0)))
    dags = [svc._reconstruct_dag(d.replay_payload) for d in resp.ranked_dag_dossiers]
    acetic = {"C": 2, "H": 4, "O": 2}
    site = next((di, si, pi) for di, d in enumerate(dags)
                for si, s in enumerate(d.steps)
                for pi, p in enumerate(s.products)
                if svc._structure_ident(p) != svc._structure_ident(s.target) and p.formula == acetic
                and (si, svc._structure_ident(p)) not in {(a, svc._structure_ident(m)) for a, _b, m in d.edges})
    di, si, pi = site
    steps = list(dags[di].steps)
    products = list(steps[si].products)
    products[pi] = parse_smiles("COC=O").canonical()
    swapped = dc.replace(steps[si], products=tuple(products))
    steps[si] = dc.replace(swapped, envelope=_routes._conditions_for(svc._ReplayedTransform(swapped)))
    new_dags = list(dags)
    new_dags[di] = SynthesisDAG(DAG_SCHEMA, tuple(steps))
    req = resp.request
    box = ConstraintBox.of_bounds(req.constraints.bounds, process=req.constraints.process)
    ranked = svc.ranked_dag_dossiers(tuple(new_dags), box)
    cands = tuple(sorted((cir.CandidateSummary(cir.CANDIDATE_SUMMARY_SCHEMA, "DAG", r.route_digest, r.equation,
                                               "FORMAL_CANDIDATE") for r in ranked), key=lambda c: c.candidate_digest))
    ir2 = dc.replace(resp.compilation_ir, candidates=cands,
                     search_receipt=dc.replace(resp.compilation_ir.search_receipt, results_returned=len(cands)))
    diags = list(ir2.diagnostics)
    for note in (svc.constraint_note(req.constraints.bounds, fit_counts=None, process=req.constraints.process),
                 svc._dag_bench_note(tuple(new_dags), box)):
        if note is not None:
            diags.append(note)
    forged = response_to_payload(dc.replace(resp, compilation_ir=ir2, ranked_dag_dossiers=ranked,
                                            diagnostics=tuple(diags)))
    for kw in _modes(req):
        with pytest.raises(ValueError, match=r"DAG dossier .* is not a transform the carried algebra .*\(D29\.1\)"):
            response_from_payload(copy.deepcopy(forged), **kw)


# ---------------------------------------------------------------------------------------------------------------------
# Wave C2 hardening: authenticate before decode; producer / consumer key parity
# ---------------------------------------------------------------------------------------------------------------------

def test_c2_keyed_consumer_refuses_a_forgery_before_any_decode(honest, monkeypatch):
    """Wave C2 F1: a keyless forger's payload reached molecule decode (request target canonicalisation) BEFORE the
    HMAC check, so even an authenticated() / paranoid() verifier did the forger's work.  The claimed wire digest is now
    authenticated first -- fails if the request is decoded before the signature refuses."""
    resp, _thick, _thin = honest
    signed = response_to_payload(resp, signing_key=_KEY)
    forged = copy.deepcopy(signed)
    forged["diagnostics"] = list(forged["diagnostics"]) + ["forged line"]
    forged = _reforge(forged)                       # every public digest recomputed; the signature cannot follow
    forged["producer_signature"] = signed["producer_signature"]
    calls = _spy_request_decode(monkeypatch)
    with pytest.raises(ValueError, match="producer_signature does not verify"):
        load_response(forged, VerificationPolicy.authenticated(_KEY))
    assert calls == []
    unsigned = copy.deepcopy(forged)
    unsigned["producer_signature"] = None
    with pytest.raises(ValueError, match="producer_signature is required but the payload is unsigned"):
        load_response(unsigned, VerificationPolicy.authenticated(_KEY))
    assert calls == []


def test_c2_a_producer_cannot_sign_with_a_key_no_consumer_accepts(honest):
    """Wave C2 F4: the consumer policy refuses keys shorter than 16 bytes, so the producer must too."""
    resp, _thick, _thin = honest
    for bad in (b"short", "a-str-not-bytes-at-all-32-chars!"):
        with pytest.raises(ValueError, match="signing_key must be bytes of at least 16 bytes"):
            response_to_payload(resp, signing_key=bad)


def test_c2_a_short_producer_keyfile_is_refused(tmp_path, monkeypatch):
    import smartchem.transport_integrity as ti
    keyfile = tmp_path / "producer.key"
    keyfile.write_bytes(b"too-short")
    monkeypatch.delenv(ti._PRODUCER_KEY_ENV, raising=False)
    monkeypatch.setattr(ti, "_PRODUCER_KEY_PATH", keyfile)
    with pytest.raises(ValueError, match="a producer key must be at least 16 bytes"):
        ti.resolve_producer_key()
    keyfile.write_bytes(b"k" * 32)
    assert ti.resolve_producer_key() == b"k" * 32


# ---------------------------------------------------------------------------------------------------------------------
# Wave C3 hardening: typed provider knobs, owned replay evidence, one context per load
# ---------------------------------------------------------------------------------------------------------------------

def test_c3_a_provider_knob_is_exactly_its_declared_type():
    """Wave C3 F2: string-valued manifest entries are prose and stay out of the registry digest, so a knob given as a
    string (ring_aware="yes" vs "") steered enumeration while sharing one enumeration-cache key."""
    from smartchem.transform_provider import CappedScissionProvider
    for bad in (dict(ring_aware="yes"), dict(ring_aware=""), dict(max_reactant_cuts="2"), dict(max_reactant_cuts=True),
                dict(max_reactant_cuts=0)):
        with pytest.raises(TypeError):
            CappedScissionProvider(**bad)
    assert CappedScissionProvider(ring_aware=True, max_reactant_cuts=2).ring_aware is True


def test_c3_a_loaded_response_owns_its_replay_evidence(honest):
    """Wave C3 F5: the loaded response aliased the caller's mutable replay list -- editing the input dict after the load
    changed the evidence a response (and its receipt) describe."""
    _resp, thick, _thin = honest
    payload = copy.deepcopy(thick)
    loaded = load_response(payload).response
    before = json.dumps(loaded.ranked_route_dossiers[0].replay_payload, sort_keys=True)
    payload["ranked_route_dossiers"][0]["replay_payload"][0]["target"]["atoms"][0] = "Xx"
    assert json.dumps(loaded.ranked_route_dossiers[0].replay_payload, sort_keys=True) == before


def test_c3_a_load_inside_a_load_is_refused(honest, monkeypatch):
    """Wave C3: a nested load would silently merge its budget meter, memo and receipt counts into the outer load's."""
    import smartchem.service as svc
    _resp, thick, _thin = honest
    original = svc.CompilationResponse._check_ranking_coherence

    def nested(self):
        svc.response_from_payload(copy.deepcopy(thick))          # a second load started from inside the first
        return original(self)
    monkeypatch.setattr(svc.CompilationResponse, "_check_ranking_coherence", nested)
    with pytest.raises(RuntimeError, match="started inside another load"):
        load_response(copy.deepcopy(thick))


# ---------------------------------------------------------------------------------------------------------------------
# Wave C8 hardening
# ---------------------------------------------------------------------------------------------------------------------

def test_c8_a_thin_payload_carrying_replays_is_refused_by_both_loaders(honest):
    """Wave C8 F6: a canonical payload relabelled THIN_ADVISORY (replays kept, digest recomputed) loaded through
    response_from_payload but was refused by load_response -- two public loaders, two verdicts."""
    resp, thick, _thin = honest
    relabel = copy.deepcopy(thick)
    relabel["transport_mode"] = "THIN_ADVISORY"
    relabel = _reforge(relabel)
    for load in (lambda p: response_from_payload(p), lambda p: load_response(p)):
        with pytest.raises(ValueError, match="THIN_ADVISORY payload carries a replay_payload"):
            load(copy.deepcopy(relabel))


def test_c8_an_honest_invalid_answer_reexecutes():
    """Wave C8 F2: the re-execution root-work charge raised on an unparseable target, so paranoid() could not load
    ANY honest INVALID_INPUT answer."""
    req = build_recompile_request("not-a-real-name-zzz")
    resp = run_compilation(req)
    assert resp.outcome.value == "INVALID_INPUT"
    r = load_response(response_to_payload(resp), VerificationPolicy(
        expected_request_digest=req.semantic_digest, expected_capability_question_digest=None,
        require_reexecution=True)).receipt
    assert r.reexecuted and r.work.reexecutions == 1
