"""0.9.5 verification core (barrier ``docs/research/V0_9_5_ARCHITECTURE_FREEZE.md`` §2-§5): policy, receipt, context,
budget, enumeration cache.  Each law is stated with the broken behaviour its test fails on.

The service is not wired to this module yet (that is the adapter's incision); these tests pin the module's own laws,
plus drift guards against the service constants it mirrors.
"""
from __future__ import annotations

import copy
import dataclasses
import gc
import inspect
import json
import os
import pickle
import subprocess
import sys
import threading
import weakref

import pytest

from smartchem import verification as V
from smartchem.verification import (
    ENUMERATION_CACHE,
    UNPINNED,
    DigestRule,
    EnumerationCache,
    PinState,
    SchemaGeneration,
    SearchOutputTrust,
    SignatureState,
    Unpinned,
    VerificationBudget,
    VerificationBudgetExceeded,
    VerificationContext,
    VerificationPolicy,
    VerificationReceipt,
    VerifiedLoad,
    WorkLedger,
    WorkMeter,
    cached_enumerate,
    count_payload_nodes,
    current_context,
    enumeration_cache_key,
    predicted_enumeration_work,
    set_enumeration_cache_enabled,
)

KEY = b"k" * 32
OTHER_KEY = b"q" * 32
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
_LANE_B = ("/tmp/claude-1000/-home-leah-SmartChem/163e42aa-2437-472a-9ef0-8b6cec5239e9/scratchpad/waveA/"
           "B_performance/payloads/")


@pytest.fixture(autouse=True)
def _fresh_enumeration_cache():
    # the process cache is shared state: every test starts and ends with it empty and enabled.
    ENUMERATION_CACHE.clear()
    set_enumeration_cache_enabled(True)
    yield
    ENUMERATION_CACHE.clear()
    set_enumeration_cache_enabled(True)


def _mol(text):
    from smartchem.identity_parse import InputKind, resolve_target

    return resolve_target(text, InputKind.AUTO).canonical()


# ---------------------------------------------------------------------------------------------------------------------
# purity: the service imports this module, never the reverse at module level
# ---------------------------------------------------------------------------------------------------------------------

def test_importing_verification_does_not_import_the_service():
    # broken: a module-level `from .service import ...` -> circular import once the service imports verification.
    code = "import sys, smartchem.verification; print('smartchem.service' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)})
    assert out.stdout.strip() == "False"


def test_mirrored_service_constants_have_not_drifted():
    import smartchem.service as svc
    import smartchem.transport_integrity as TI

    assert V._KEY_MIN_BYTES == TI._PRODUCER_KEY_MIN_BYTES  # the key floor moved with its resolver (I1)
    assert V._TRANSPORT_MODES == svc._TRANSPORT_MODES
    assert V._TRANSPORT_CANONICAL_VERIFIED == svc.TRANSPORT_CANONICAL_VERIFIED
    assert V._TRANSPORT_THIN_ADVISORY == svc.TRANSPORT_THIN_ADVISORY


# ---------------------------------------------------------------------------------------------------------------------
# UNPINNED
# ---------------------------------------------------------------------------------------------------------------------

def test_unpinned_is_one_singleton_through_construction_copy_and_pickle():
    # broken: an object() sentinel unpickles into a stranger, which the loader would then read as a PIN.
    assert Unpinned() is UNPINNED
    assert copy.copy(UNPINNED) is UNPINNED and copy.deepcopy(UNPINNED) is UNPINNED
    # EVERY protocol: 0 and 1 rebuild via object.__new__ (bypassing the singleton __new__) unless __reduce__ names it.
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        assert pickle.loads(pickle.dumps(UNPINNED, protocol=protocol)) is UNPINNED, protocol
        policy = pickle.loads(pickle.dumps(VerificationPolicy(), protocol=protocol))
        assert policy.expected_capability_question_digest is UNPINNED and policy == VerificationPolicy(), protocol
    assert repr(UNPINNED) == "UNPINNED"


# ---------------------------------------------------------------------------------------------------------------------
# VerificationBudget / VerificationBudgetExceeded
# ---------------------------------------------------------------------------------------------------------------------

def test_budget_defaults_are_the_barrier_table():
    b = VerificationBudget.default()
    assert b == VerificationBudget()
    assert (b.dossiers, b.replay_steps, b.steps_per_dossier, b.enumeration_targets, b.work_per_target, b.work_total,
            b.reexecutions) == (256, 4096, 32, 128, 32_768, 131_072, 1)
    # payload_nodes: >= 8x the MEASURED honest maximum (100-DAG isopentyl, 174,907 nodes) and the recipe payload
    # (29,259), rounded up to a power of two.
    assert b.payload_nodes == 2 ** 21
    assert b.payload_nodes >= 8 * 174_907 and b.payload_nodes >= 8 * 29_259
    assert b.payload_nodes & (b.payload_nodes - 1) == 0


def test_unlimited_is_the_only_unbounded_budget():
    # broken: None accepted directly -> an unbounded budget reachable by accident (a typo'd config, a None default).
    u = VerificationBudget.unlimited()
    assert all(getattr(u, n) is None for n in V._BUDGET_COUNTERS)
    assert u == VerificationBudget.unlimited()
    with pytest.raises(ValueError, match="only VerificationBudget.unlimited"):
        VerificationBudget(dossiers=None)
    with pytest.raises(ValueError, match="only VerificationBudget.unlimited"):
        dataclasses.replace(u, dossiers=5)          # the licence does not ride along with replace
    assert dataclasses.replace(VerificationBudget(), dossiers=5).dossiers == 5


@pytest.mark.parametrize("bad, exc", [(0, ValueError), (-1, ValueError), (True, TypeError), (1.5, TypeError),
                                      ("10", TypeError)])
def test_budget_refuses_non_positive_and_non_int_limits(bad, exc):
    with pytest.raises(exc):
        VerificationBudget(work_total=bad)


def test_budget_exceeded_is_a_plain_value_error_with_its_facts():
    from smartchem.experiment.ceiling import CeilingError
    from smartchem.experiment.dag import DAGError

    # broken: subclassing DAGError/CeilingError -> service._route_shopping_requirements swallows it (a skipped check).
    assert issubclass(VerificationBudgetExceeded, ValueError)
    assert not issubclass(VerificationBudgetExceeded, (DAGError, CeilingError))
    exc = VerificationBudgetExceeded("work_per_target", 32_768, 473_200)
    assert (exc.counter, exc.limit, exc.consumed) == ("work_per_target", 32_768, 473_200)
    text = str(exc)
    assert "work_per_target" in text and "32768" in text and "473200" in text
    assert ("verification did not complete; raise the budget explicitly (VerificationBudget(...)) only if you trust "
            "this payload's size") in text
    again = pickle.loads(pickle.dumps(exc))
    assert (again.counter, again.limit, again.consumed, str(again)) == (exc.counter, exc.limit, exc.consumed, text)


# ---------------------------------------------------------------------------------------------------------------------
# WorkMeter / WorkLedger / count_payload_nodes
# ---------------------------------------------------------------------------------------------------------------------

def test_charge_checks_before_it_records():
    # broken: record-then-check -> the meter holds consumed > limit after a refusal (the work was booked as done).
    meter = WorkMeter(VerificationBudget(dossiers=3))
    meter.charge("dossiers", 2)
    meter.charge("dossiers")
    with pytest.raises(VerificationBudgetExceeded) as info:
        meter.charge("dossiers")
    assert (info.value.counter, info.value.limit, info.value.consumed) == ("dossiers", 3, 4)
    assert meter.consumed("dossiers") == 3
    meter.charge("dossiers", 0)                      # a zero charge at the limit is not work


def test_per_item_counters_are_checked_per_item_and_record_the_maximum():
    meter = WorkMeter(VerificationBudget(steps_per_dossier=7))
    meter.check_item("steps_per_dossier", 5)
    meter.check_item("steps_per_dossier", 7)
    meter.check_item("steps_per_dossier", 2)
    assert meter.consumed("steps_per_dossier") == 7   # a maximum, not a sum
    with pytest.raises(VerificationBudgetExceeded):
        meter.check_item("steps_per_dossier", 8)
    assert meter.consumed("steps_per_dossier") == 7
    with pytest.raises(ValueError, match="per-item counter: use check_item"):
        meter.charge("work_per_target", 1)
    with pytest.raises(ValueError, match="unknown per-item"):
        meter.check_item("dossiers", 1)
    with pytest.raises(ValueError, match="unknown cumulative"):
        meter.charge("seconds", 1)
    for bad in (-1, True, 1.0):
        with pytest.raises(ValueError, match="non-negative int"):
            meter.charge("dossiers", bad)


def test_composite_charges_are_atomic():
    # broken: booking dossiers before checking replay_steps -> a refused dossier still counted.
    meter = WorkMeter(VerificationBudget(replay_steps=10))
    meter.charge_dossier(6)
    with pytest.raises(VerificationBudgetExceeded) as info:
        meter.charge_dossier(5)
    assert info.value.counter == "replay_steps"
    assert (meter.consumed("dossiers"), meter.consumed("replay_steps"), meter.consumed("steps_per_dossier")) == (1, 6, 6)
    meter = WorkMeter(VerificationBudget(work_total=5_000))
    meter.charge_enumeration(4_356)
    with pytest.raises(VerificationBudgetExceeded) as info:
        meter.charge_enumeration(4_356)
    assert info.value.counter == "work_total"
    assert (meter.consumed("enumeration_targets"), meter.consumed("work_total")) == (1, 4_356)


def test_default_budget_refuses_the_c7_1_hostile_and_admits_the_honest_maximum():
    # hostile C7-1: one target, W = 473,200 -> refused on the per-target cap before any enumeration.
    with pytest.raises(VerificationBudgetExceeded) as info:
        WorkMeter(VerificationBudget()).charge_enumeration(473_200)
    assert (info.value.counter, info.value.limit, info.value.consumed) == ("work_per_target", 32_768, 473_200)
    # honest maxima (Lane B, frozen corpus): 100 dossiers, 542 steps, 7 per dossier, 29 targets, W <= 4,356.
    meter = WorkMeter(VerificationBudget())
    for _ in range(100):
        meter.charge_dossier(5)
    meter.charge_dossier(7)
    for _ in range(9):
        meter.charge_enumeration(4_356)
    meter.charge("reexecutions")
    ledger = meter.snapshot()
    assert ledger.within(VerificationBudget()) and ledger.budget == VerificationBudget()
    assert (ledger.dossiers, ledger.replay_steps, ledger.steps_per_dossier, ledger.work_total) == (101, 507, 7, 39_204)


def test_unlimited_meter_never_refuses():
    meter = WorkMeter(VerificationBudget.unlimited())
    meter.charge_enumeration(10 ** 9)
    meter.charge("reexecutions", 10)
    meter.charge_payload_nodes([0] * 10_000)
    assert meter.snapshot().work_total == 10 ** 9


def test_count_payload_nodes_counts_every_value_and_stops_early():
    assert count_payload_nodes({"a": [1, 2, {"b": None}], "c": "x"}) == 7
    assert count_payload_nodes(3) == 1
    shared = [1, 2]
    assert count_payload_nodes([shared, shared]) == 7        # once per occurrence, as the decoder walks it
    deep = []
    node = deep
    for _ in range(200_000):                                  # no recursion: nesting depth cannot exhaust the stack
        node.append([])
        node = node[0]
    # 0.9.5 A16 (C8 F4, dict leg): such nesting is now REFUSED by the same iterative walk -- typed, before any decoder
    # could recurse -- instead of counted (tests/test_v0_9_5_loader_hardening.py pins the ceiling itself).
    with pytest.raises(ValueError, match="nests containers more than"):
        count_payload_nodes(deep)
    # early stop: the root's million children are counted by len(), never queued -- a lower bound past the limit.
    assert count_payload_nodes(list(range(10 ** 6)), stop_after=10) == 1 + 10 ** 6
    assert count_payload_nodes([[1, 2, 3], [4, 5, 6]], stop_after=4) == 5    # root + one sublist + its 3 children
    assert count_payload_nodes([[1, 2, 3], [4, 5, 6]], stop_after=9) == 9    # at the limit is not past it
    cyclic: list = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match="cyclic"):
        count_payload_nodes(cyclic)


def test_charge_payload_nodes_refuses_an_oversized_payload_without_booking_it():
    meter = WorkMeter(VerificationBudget(payload_nodes=100))
    assert meter.charge_payload_nodes(list(range(50))) == 51
    with pytest.raises(VerificationBudgetExceeded) as info:
        meter.charge_payload_nodes(list(range(10 ** 6)))
    # consumed = 51 already booked + a lower bound on the refused payload (root + its 10**6 children, never walked)
    assert info.value.counter == "payload_nodes" and info.value.consumed == 51 + 1 + 10 ** 6
    assert meter.consumed("payload_nodes") == 51


def test_work_ledger_is_frozen_and_validated():
    ledger = WorkMeter(VerificationBudget()).snapshot()
    with pytest.raises(dataclasses.FrozenInstanceError):
        ledger.dossiers = 5
    with pytest.raises(ValueError):
        WorkLedger(budget=VerificationBudget(), dossiers=-1)
    with pytest.raises(TypeError):
        WorkLedger(budget=None)
    heavy = dataclasses.replace(ledger, work_total=200_000)
    assert not heavy.within(VerificationBudget()) and heavy.within(VerificationBudget.unlimited())


# ---------------------------------------------------------------------------------------------------------------------
# predicted_enumeration_work (Lane B's E/W, bonds INCLUDING hydrogen)
# ---------------------------------------------------------------------------------------------------------------------

def test_predicted_work_reproduces_lane_b_recorded_values():
    water, acetic = _mol("water"), _mol("acetic acid")
    # Lane B payload a: methyl acetate (10 bonds incl. H) x water (2) -> E = 20.
    assert predicted_enumeration_work(_mol("CC(=O)OC"), (water,)) == (20, 200)
    # Lane B b1/c honest maximum: isopentyl acetate (22) x (water 2 + acetic acid 7) -> E = 198, W = 4,356.
    assert predicted_enumeration_work(_mol("isopentyl acetate"), (water, acetic)) == (198, 4_356)
    # C7-1 hostile: the C43H86O2 wax ester (130 bonds) x six helpers (2+7+5+8+3+3 = 28) -> E = 3,640, W = 473,200.
    hostile = _mol("CCCCCCCCCCCCCCCCCCCCCC(=O)OCCCCCCCCCCCCCCCCCCCCC")
    helpers = tuple(_mol(s) for s in ("O", "CC(=O)O", "CO", "CCO", "N", "C=O"))
    assert predicted_enumeration_work(hostile, helpers) == (3_640, 473_200)


def test_predicted_work_counts_distinct_reagents_only():
    # broken: summing duplicates -> the charge moves while the enumeration (Lane B: duplicates inert) does not.
    water, acetic, ma = _mol("water"), _mol("acetic acid"), _mol("CC(=O)OC")
    assert predicted_enumeration_work(ma, (water, water, acetic)) == predicted_enumeration_work(ma, (acetic, water))
    # 0.9.5 S16 floor: no reagents is not no work (a reagentless provider enumerates over the target alone)
    assert predicted_enumeration_work(ma, ()) == (10, 100)


def _replay_targets(payload):
    import smartchem.service as svc

    targets = {}
    for table in ("ranked_route_dossiers", "ranked_dag_dossiers"):
        for dossier in payload.get(table, []):
            if dossier.get("replay_payload") is not None:
                for step in svc._replay_payload_to_steps(dossier["replay_payload"]):
                    targets.setdefault(step.target, None)      # distinct LITERAL targets, as D29.1 dedups them
    return tuple(targets)


@pytest.mark.skipif(not os.path.exists(_LANE_B + "f_hostile2_45.json"), reason="Lane B scratch payloads absent")
def test_predicted_work_on_lane_b_payload_files():
    import smartchem.service as svc

    def load(name):
        with open(_LANE_B + name) as fh:
            payload = json.load(fh)
        req = svc.request_from_payload(payload["request"])
        return _replay_targets(payload), tuple(_mol(s) for s in req.helper_reagents)

    targets, reagents = load("f_hostile2_45.json")
    assert [predicted_enumeration_work(t, reagents)[1] for t in targets] == [473_200]
    targets, reagents = load("c_dag.json")                     # the honest 100-DAG payload
    works = [predicted_enumeration_work(t, reagents)[1] for t in targets]
    assert (len(works), max(works), sum(works)) == (29, 4_356, 41_328)


# ---------------------------------------------------------------------------------------------------------------------
# VerificationPolicy
# ---------------------------------------------------------------------------------------------------------------------

def test_policy_shape_and_defaults_are_frozen():
    assert [f.name for f in dataclasses.fields(VerificationPolicy)] == [
        "verification_key", "require_signature", "require_verified_admission", "expected_request_digest",
        "expected_capability_question_digest", "require_reexecution", "require_canonical_transport", "budget"]
    p = VerificationPolicy()
    assert (p.verification_key, p.require_signature, p.require_verified_admission, p.expected_request_digest,
            p.require_reexecution, p.require_canonical_transport) == (None, False, False, None, False, False)
    assert p.expected_capability_question_digest is UNPINNED and p.budget == VerificationBudget.default()
    assert "kkkk" not in repr(VerificationPolicy.authenticated(KEY))   # repr=False on the key


def test_from_legacy_kwargs_matches_todays_signatures_and_defaults():
    import smartchem.service as svc

    for fn in (svc.response_from_payload, svc.deserialize_response):
        params = {n: p for n, p in inspect.signature(fn).parameters.items()
                  if p.kind is p.KEYWORD_ONLY and n != "policy"}   # policy= is the new, non-legacy slot
        # broken: a trust kwarg added/renamed on one side only -> the shim silently drops or refuses it.
        assert set(params) == set(V._LEGACY_KWARGS), fn.__name__
        # today's defaults -> exactly the default policy (the service's _NO_CAPABILITY_PIN maps to UNPINNED).
        assert VerificationPolicy.from_legacy_kwargs(**{n: p.default for n, p in params.items()}) == \
            VerificationPolicy()
    assert VerificationPolicy.from_legacy_kwargs(
        expected_capability_question_digest=svc._NO_CAPABILITY_PIN).expected_capability_question_digest is UNPINNED
    assert VerificationPolicy.from_legacy_kwargs(
        expected_capability_question_digest=None).expected_capability_question_digest is None   # None is a pin
    legacy = VerificationPolicy.from_legacy_kwargs(verification_key=KEY, require_signature=True,
                                                   require_verified_admission=True, expected_request_digest=DIGEST_A,
                                                   expected_capability_question_digest=DIGEST_B,
                                                   require_reexecution=True)
    assert legacy == VerificationPolicy(verification_key=KEY, require_signature=True, require_verified_admission=True,
                                        expected_request_digest=DIGEST_A,
                                        expected_capability_question_digest=DIGEST_B, require_reexecution=True)
    for bad in ({"policy": VerificationPolicy()}, {"require_canonical_transport": True}, {"verifcation_key": KEY}):
        with pytest.raises(TypeError, match="unexpected keyword"):
            VerificationPolicy.from_legacy_kwargs(**bad)


def test_policy_refuses_contradictions_at_construction():
    with pytest.raises(ValueError) as info:
        VerificationPolicy(require_signature=True)
    assert str(info.value) == "require_signature needs a verification_key"   # today's exact message
    with pytest.raises(TypeError, match="must be bytes"):
        VerificationPolicy(verification_key="k" * 32)
    with pytest.raises(TypeError, match="must be bytes"):
        VerificationPolicy(verification_key=bytearray(KEY))
    with pytest.raises(ValueError, match="at least 16 bytes"):
        VerificationPolicy(verification_key=b"k" * 15)
    assert VerificationPolicy(verification_key=b"k" * 16).verification_key == b"k" * 16
    for field_name in ("expected_request_digest", "expected_capability_question_digest"):
        for bad in ("A" * 64, "a" * 63, "a" * 65, "g" * 64, ""):
            with pytest.raises(ValueError, match="64 lowercase hex"):
                VerificationPolicy(**{field_name: bad})
        with pytest.raises(TypeError, match="str digest"):
            VerificationPolicy(**{field_name: 7})
    with pytest.raises(TypeError, match="str digest"):
        VerificationPolicy(expected_request_digest=UNPINNED)     # UNPINNED is a capability-pin value only
    for flag in ("require_signature", "require_verified_admission", "require_reexecution",
                 "require_canonical_transport"):
        with pytest.raises(TypeError, match="must be a bool"):
            VerificationPolicy(**{flag: 1})
    with pytest.raises(TypeError, match="VerificationBudget"):
        VerificationPolicy(budget={"dossiers": 5})


def test_named_constructors_equal_the_explicit_policy_field_for_field():
    assert VerificationPolicy.advisory() == VerificationPolicy()
    assert VerificationPolicy.canonical() == VerificationPolicy(require_canonical_transport=True,
                                                                require_verified_admission=True)
    assert VerificationPolicy.pinned(DIGEST_A) == VerificationPolicy(expected_request_digest=DIGEST_A)
    assert VerificationPolicy.pinned(DIGEST_A, question_digest=None) == VerificationPolicy(
        expected_request_digest=DIGEST_A, expected_capability_question_digest=None)
    assert VerificationPolicy.pinned(DIGEST_A, question_digest=DIGEST_B) == VerificationPolicy(
        expected_request_digest=DIGEST_A, expected_capability_question_digest=DIGEST_B)
    assert VerificationPolicy.authenticated(KEY) == VerificationPolicy(verification_key=KEY, require_signature=True)
    assert VerificationPolicy.paranoid(DIGEST_A, KEY, question_digest=DIGEST_B) == VerificationPolicy(
        verification_key=KEY, require_signature=True, require_verified_admission=True,
        expected_request_digest=DIGEST_A, expected_capability_question_digest=DIGEST_B, require_reexecution=True,
        require_canonical_transport=True)
    assert VerificationPolicy.paranoid(DIGEST_A, KEY).expected_capability_question_digest is UNPINNED
    with pytest.raises(ValueError, match="64 lowercase hex"):
        VerificationPolicy.pinned("not-a-digest")                # sugar still passes through the refusals


# ---------------------------------------------------------------------------------------------------------------------
# VerificationReceipt
# ---------------------------------------------------------------------------------------------------------------------

def _receipt(policy=None, **overrides):
    policy = VerificationPolicy() if policy is None else policy
    facets = dict(
        schema_generation=SchemaGeneration.CURRENT, transport_mode="CANONICAL_VERIFIED",
        digest_rule=DigestRule.WHOLE_BODY,
        request_pin=PinState.CHECKED if policy.expected_request_digest is not None else PinState.NOT_PINNED,
        capability_pin=(PinState.NOT_PINNED if policy.expected_capability_question_digest is UNPINNED
                        else PinState.CHECKED),
        signature=SignatureState.VERIFIED if policy.verification_key is not None else SignatureState.NOT_CHECKED,
        verified_admission=policy.require_verified_admission, replay_rederived_routes=3, replay_rederived_dags=0,
        reexecuted=policy.require_reexecution, legacy_migrated=False, work=WorkMeter(policy.budget).snapshot(),
        policy=policy, response_result_digest=DIGEST_A)
    facets.update(overrides)
    return V._issue_receipt(**facets)


def _raw_facets(receipt):
    return {f.name: getattr(receipt, f.name) for f in dataclasses.fields(receipt)}


def test_receipt_cannot_be_constructed_outside_the_loader():
    honest = _receipt()
    facets = _raw_facets(honest)
    # broken: no token check -> any caller mints a receipt claiming whatever it likes.
    with pytest.raises(TypeError, match="issued only by the loader"):
        VerificationReceipt(**facets)
    with pytest.raises(TypeError, match="issued only by the loader"):
        VerificationReceipt(**facets, _token=object())
    with pytest.raises(TypeError, match="issued only by the loader"):
        VerificationReceipt(**facets, _token="_RECEIPT_TOKEN")
    assert "_token" not in [f.name for f in dataclasses.fields(VerificationReceipt)]
    assert not hasattr(VerificationReceipt, "from_payload")


def test_receipt_cannot_be_replaced_copied_pickled_or_read_from_json():
    honest = _receipt()
    # broken: token stored as a field -> replace() copies it and upgrades the claim (Lane E measured this).
    with pytest.raises(TypeError, match="issued only by the loader"):
        dataclasses.replace(honest, reexecuted=True)
    with pytest.raises(TypeError, match="issued only by the loader"):
        dataclasses.replace(honest, signature=SignatureState.VERIFIED)
    assert copy.copy(honest) is honest and copy.deepcopy(honest) is honest
    assert copy.deepcopy({"r": honest})["r"] is honest
    with pytest.raises(TypeError, match="issued only by the loader"):
        pickle.dumps(honest)
    wire = json.loads(json.dumps({k: (v.value if hasattr(v, "value") else v) for k, v in _raw_facets(honest).items()
                                  if k not in ("work", "policy")}))
    wire.update(work=honest.work, policy=honest.policy)
    with pytest.raises(TypeError, match="issued only by the loader"):
        VerificationReceipt(**wire)
    with pytest.raises(TypeError, match="issued only by the loader"):
        VerificationReceipt(**wire, _token=None)


def test_search_output_is_derived_not_declared():
    assert _receipt().search_output is SearchOutputTrust.ADVISORY
    assert _receipt(VerificationPolicy.authenticated(KEY)).search_output is SearchOutputTrust.AUTHENTICATED
    assert _receipt(VerificationPolicy(require_reexecution=True)).search_output is SearchOutputTrust.REEXECUTED
    both = _receipt(dataclasses.replace(VerificationPolicy.authenticated(KEY), require_reexecution=True))
    assert both.search_output is SearchOutputTrust.REEXECUTED
    # the factory derives it; a token-holding caller (the loader) that passes a wrong value is still refused.
    # broken: no coherence guard -> a loader bug (or mutant) labels an unsigned, un-re-executed load AUTHENTICATED.
    facets = _raw_facets(_receipt())
    for lie in (SearchOutputTrust.AUTHENTICATED, SearchOutputTrust.REEXECUTED):
        with pytest.raises(ValueError, match="search_output"):
            VerificationReceipt(**{**facets, "search_output": lie}, _token=V._RECEIPT_TOKEN)


@pytest.mark.parametrize("policy, overrides, fragment", [
    (VerificationPolicy(), dict(signature=SignatureState.VERIFIED), "with no verification_key"),
    (VerificationPolicy(verification_key=KEY), dict(signature=SignatureState.NOT_CHECKED), "NOT_CHECKED although"),
    (VerificationPolicy.authenticated(KEY), dict(signature=SignatureState.NOT_REQUIRED_ABSENT),
     "under require_signature"),
    (VerificationPolicy(), dict(request_pin=PinState.CHECKED), "request_pin CHECKED"),
    (VerificationPolicy.pinned(DIGEST_A), dict(request_pin=PinState.NOT_PINNED), "request_pin NOT_PINNED"),
    (VerificationPolicy(), dict(capability_pin=PinState.CHECKED), "capability_pin CHECKED"),
    (VerificationPolicy(), dict(reexecuted=True), "reexecuted=True"),
    (VerificationPolicy(require_reexecution=True), dict(reexecuted=False), "reexecuted=False"),
    (VerificationPolicy(), dict(verified_admission=True), "verified_admission=True"),
    (VerificationPolicy.canonical(), dict(transport_mode="THIN_ADVISORY", replay_rederived_routes=0),
     "under require_canonical_transport"),
    (VerificationPolicy.canonical(), dict(schema_generation=SchemaGeneration.LEGACY_V08,
                                          digest_rule=DigestRule.FROZEN_V08, legacy_migrated=True),
     "under require_canonical_transport"),
    (VerificationPolicy(), dict(transport_mode="THIN_ADVISORY"), "THIN_ADVISORY load"),
    (VerificationPolicy(), dict(digest_rule=DigestRule.FROZEN_V08), "digest_rule FROZEN_V08"),
    (VerificationPolicy(), dict(schema_generation=SchemaGeneration.LEGACY_V08, digest_rule=DigestRule.FROZEN_V08),
     "legacy_migrated=False"),
    (VerificationPolicy(), dict(work=WorkMeter(VerificationBudget.unlimited()).snapshot()), "different budget"),
    (VerificationPolicy(), dict(work=dataclasses.replace(WorkMeter(VerificationBudget()).snapshot(),
                                                         work_total=131_073)), "exceeds the budget"),
])
def test_receipt_refuses_facets_that_contradict_each_other_or_the_policy(policy, overrides, fragment):
    # broken: a receipt accepting these would let the loader (or a mutant of it) claim what it never checked.
    with pytest.raises(ValueError, match="incoherent VerificationReceipt") as info:
        _receipt(policy, **overrides)
    assert fragment in str(info.value)


def test_receipt_refuses_mistyped_facets():
    with pytest.raises(TypeError, match="SchemaGeneration"):
        _receipt(schema_generation="CURRENT")
    with pytest.raises(ValueError, match="transport_mode"):
        _receipt(transport_mode="CANONICAL")
    with pytest.raises(ValueError, match="non-negative int"):
        _receipt(replay_rederived_dags=-1)
    with pytest.raises(ValueError, match="64 lowercase hex"):
        _receipt(response_result_digest="A" * 64)
    # a legacy load is representable when the policy does not demand canonical transport
    legacy = _receipt(schema_generation=SchemaGeneration.LEGACY_V08, digest_rule=DigestRule.FROZEN_V08,
                      legacy_migrated=True)
    assert legacy.legacy_migrated and legacy.digest_rule is DigestRule.FROZEN_V08


def test_satisfies_is_reflexive_and_fail_closed_facet_by_facet():
    paranoid = VerificationPolicy.paranoid(DIGEST_A, KEY, question_digest=DIGEST_B)
    strong = _receipt(paranoid)
    weak = _receipt()
    for receipt in (strong, weak, _receipt(VerificationPolicy.pinned(DIGEST_A, question_digest=None))):
        assert receipt.satisfies(receipt.policy)
    for weaker in (VerificationPolicy(), VerificationPolicy.canonical(), VerificationPolicy.pinned(DIGEST_A),
                   VerificationPolicy.pinned(DIGEST_A, question_digest=DIGEST_B), VerificationPolicy.authenticated(KEY),
                   VerificationPolicy(require_reexecution=True), VerificationPolicy(verification_key=KEY)):
        assert strong.satisfies(weaker), weaker
    # broken: satisfies() returning True off the facet's mere presence rather than its value.
    for stronger in (VerificationPolicy.canonical(), VerificationPolicy.pinned(DIGEST_A),
                     VerificationPolicy.pinned(DIGEST_A, question_digest=None), VerificationPolicy.authenticated(KEY),
                     VerificationPolicy(require_reexecution=True), VerificationPolicy(require_verified_admission=True),
                     VerificationPolicy(verification_key=KEY)):
        assert not weak.satisfies(stronger), stronger
    assert not strong.satisfies(VerificationPolicy.pinned(DIGEST_B))                  # a different pin
    assert not strong.satisfies(VerificationPolicy.pinned(DIGEST_A, question_digest=None))
    assert not strong.satisfies(VerificationPolicy.authenticated(OTHER_KEY))          # a different key
    thin = _receipt(transport_mode="THIN_ADVISORY", replay_rederived_routes=0)
    assert not thin.satisfies(VerificationPolicy(require_canonical_transport=True))
    legacy = _receipt(schema_generation=SchemaGeneration.LEGACY_V08, digest_rule=DigestRule.FROZEN_V08,
                      legacy_migrated=True)
    assert not legacy.satisfies(VerificationPolicy(require_canonical_transport=True))
    # work: a load that fit an unlimited budget does not satisfy a budget it would have exceeded.
    unlimited = VerificationPolicy(budget=VerificationBudget.unlimited())
    meter = WorkMeter(unlimited.budget)
    meter.charge_enumeration(473_200)
    heavy = _receipt(unlimited, work=meter.snapshot())
    assert heavy.satisfies(unlimited) and not heavy.satisfies(VerificationPolicy())
    with pytest.raises(TypeError):
        weak.satisfies({"require_signature": False})


# ---------------------------------------------------------------------------------------------------------------------
# VerifiedLoad (needs one real response: methyl acetate compiles in well under a second)
# ---------------------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def response():
    from smartchem.service import build_recompile_request, run_compilation

    return run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))


def test_verified_load_pairs_only_the_receipt_of_this_response(response):
    receipt = _receipt(response_result_digest=response.result_digest)
    load = V._issue_verified_load(response, receipt)
    assert load.response is response and load.receipt is receipt
    # broken: no binding -> a receipt earned by a canonical load is stapled to a thin/forged response.
    with pytest.raises(ValueError, match="a receipt from another load cannot be paired"):
        V._issue_verified_load(response, _receipt(response_result_digest=DIGEST_B))
    with pytest.raises(TypeError, match="CompilationResponse"):
        V._issue_verified_load(object(), receipt)
    with pytest.raises(TypeError, match="VerificationReceipt"):
        V._issue_verified_load(response, _raw_facets(receipt))


def test_verified_load_has_the_receipts_unforgeability(response):
    receipt = _receipt(response_result_digest=response.result_digest)
    load = V._issue_verified_load(response, receipt)
    with pytest.raises(TypeError, match="issued only by the loader"):
        VerifiedLoad(response=response, receipt=receipt)
    with pytest.raises(TypeError, match="issued only by the loader"):
        VerifiedLoad(response=response, receipt=receipt, _token=V._RECEIPT_TOKEN)   # the wrong licence
    with pytest.raises(TypeError, match="issued only by the loader"):
        dataclasses.replace(load, receipt=_receipt(response_result_digest=response.result_digest))
    assert copy.copy(load) is load and copy.deepcopy(load) is load
    with pytest.raises(TypeError, match="issued only by the loader"):
        pickle.dumps(load)


# ---------------------------------------------------------------------------------------------------------------------
# VerificationContext
# ---------------------------------------------------------------------------------------------------------------------

class _Payload:
    """A weak-referenceable stand-in for a replay-payload object."""


def test_memo_builds_once_per_kind_and_payload_object():
    ctx = VerificationContext(VerificationPolicy())
    calls = []

    def build(obj):
        calls.append(obj)
        return ("built", id(obj))

    a, b = {"steps": []}, {"steps": []}                       # equal VALUES, distinct objects
    first = ctx.memo("route", a, build)
    assert ctx.memo("route", a, build) is first and len(calls) == 1
    ctx.memo("route", b, build)                               # keyed by the object, not its value
    ctx.memo("dag", a, build)                                 # and by kind
    assert len(calls) == 3
    with pytest.raises(TypeError):
        ctx.memo("", a, build)


def test_memo_holds_a_strong_reference_so_ids_cannot_be_reused():
    # broken: keying on id() without holding the object -> a freed id is recycled and a new payload hits a stale build.
    ctx = VerificationContext(VerificationPolicy())
    obj = _Payload()
    ref = weakref.ref(obj)
    ctx.memo("route", obj, lambda o: 1)
    del obj
    gc.collect()
    assert ref() is not None


def test_memo_does_not_store_a_failed_build():
    ctx = VerificationContext(VerificationPolicy())
    obj = _Payload()

    def boom(_o):
        raise ValueError("refused")

    with pytest.raises(ValueError):
        ctx.memo("route", obj, boom)
    assert ctx.memo("route", obj, lambda o: "second") == "second"


def test_context_owns_a_meter_on_the_policy_budget():
    policy = VerificationPolicy(budget=VerificationBudget(dossiers=1))
    ctx = VerificationContext(policy)
    assert ctx.policy is policy and isinstance(ctx.meter, WorkMeter) and ctx.meter.budget is policy.budget
    with pytest.raises(TypeError):
        VerificationContext(None)


def test_activate_installs_restores_and_nests():
    outer, inner = VerificationContext(VerificationPolicy()), VerificationContext(VerificationPolicy())
    assert current_context() is None
    with outer.activate() as active:
        assert active is outer and current_context() is outer
        with inner.activate():
            assert current_context() is inner
        assert current_context() is outer                      # broken: exit resets to None, not to the outer load
        with pytest.raises(RuntimeError):
            with inner.activate():
                raise RuntimeError("load refused mid-way")
        assert current_context() is outer
    assert current_context() is None


def test_contexts_are_isolated_across_threads():
    main_ctx = VerificationContext(VerificationPolicy())
    seen = {}
    barrier = threading.Barrier(2, timeout=60)

    def worker():
        seen["before"] = current_context()
        own = VerificationContext(VerificationPolicy())
        with own.activate():
            barrier.wait()
            seen["inside"] = current_context() is own
            barrier.wait()

    with main_ctx.activate():
        t = threading.Thread(target=worker)
        t.start()
        barrier.wait()
        assert current_context() is main_ctx                   # the worker's activation did not leak here
        barrier.wait()
        t.join()
    assert seen == {"before": None, "inside": True}


# ---------------------------------------------------------------------------------------------------------------------
# EnumerationCache (unit, synthetic values)
# ---------------------------------------------------------------------------------------------------------------------

def _value(weight):
    return (tuple(range(weight)), True)


def _counting(weight, calls, tag):
    def compute():
        calls.append(tag)
        return _value(weight)
    return compute


def test_cache_hit_miss_accounting():
    cache, calls = EnumerationCache(), []
    assert cache.get_or_compute("k", _counting(3, calls, "k")) == _value(3)
    assert cache.get_or_compute("k", _counting(3, calls, "k")) == _value(3)
    assert calls == ["k"]
    s = cache.stats()
    assert (s.hits, s.misses, s.entries, s.retained_transforms) == (1, 1, 1, 3)


def test_cache_evicts_least_recently_used_by_weight():
    cache, calls = EnumerationCache(max_transforms=10, max_entries=100, max_entry_transforms=5), []
    cache.get_or_compute("a", _counting(4, calls, "a"))
    cache.get_or_compute("b", _counting(4, calls, "b"))
    cache.get_or_compute("a", _counting(4, calls, "a"))       # touch a: b is now least recently used
    cache.get_or_compute("c", _counting(4, calls, "c"))       # 12 > 10 -> evict b
    assert cache.stats().retained_transforms == 8 and cache.stats().entries == 2
    cache.get_or_compute("a", _counting(4, calls, "a"))
    cache.get_or_compute("b", _counting(4, calls, "b"))
    assert calls == ["a", "b", "c", "b"]


def test_cache_caps_the_entry_count():
    # broken: weight-only bound -> unboundedly many zero-transform entries.
    cache, calls = EnumerationCache(max_transforms=100, max_entries=3, max_entry_transforms=10), []
    for key in "abcd":
        cache.get_or_compute(key, _counting(0, calls, key))
    assert cache.stats().entries == 3
    cache.get_or_compute("a", _counting(0, calls, "a"))
    assert calls == ["a", "b", "c", "d", "a"]


def test_cache_does_not_retain_an_oversized_entry():
    cache, calls = EnumerationCache(max_transforms=100, max_entries=10, max_entry_transforms=5), []
    assert cache.get_or_compute("big", _counting(6, calls, "big")) == _value(6)
    assert cache.stats().entries == 0
    cache.get_or_compute("big", _counting(6, calls, "big"))
    assert calls == ["big", "big"]


def test_cache_clear_and_disable():
    cache, calls = EnumerationCache(), []
    cache.get_or_compute("k", _counting(2, calls, "k"))
    cache.clear()
    s = cache.stats()
    assert (s.hits, s.misses, s.entries, s.retained_transforms) == (0, 0, 0, 0)
    cache.get_or_compute("k", _counting(2, calls, "k"))
    cache.set_enabled(False)
    # disabled == always compute, never store, never serve what is stored
    cache.get_or_compute("k", _counting(2, calls, "k"))
    cache.get_or_compute("j", _counting(2, calls, "j"))
    assert calls == ["k", "k", "k", "j"] and cache.stats().entries == 1
    cache.set_enabled(True)
    cache.get_or_compute("k", _counting(2, calls, "k"))
    assert calls == ["k", "k", "k", "j"]
    with pytest.raises(TypeError):
        cache.set_enabled(1)


def test_cache_refuses_mutable_values_and_bad_bounds():
    cache = EnumerationCache()
    with pytest.raises(TypeError, match="immutable"):
        cache.get_or_compute("k", lambda: ([1, 2], True))
    assert cache.stats().entries == 0
    for kwargs in ({"max_transforms": 0}, {"max_entries": -1}, {"max_entry_transforms": 1.5},
                   {"max_transforms": 10, "max_entry_transforms": 11}):
        with pytest.raises(ValueError):
            EnumerationCache(**kwargs)


def test_process_cache_bounds_are_the_barrier_bounds():
    assert (ENUMERATION_CACHE.max_transforms, ENUMERATION_CACHE.max_entries,
            ENUMERATION_CACHE.max_entry_transforms) == (65_536, 512, 8_192)


def test_cache_is_consistent_under_concurrent_use():
    cache = EnumerationCache(max_transforms=40, max_entries=8, max_entry_transforms=10)
    keys = [f"k{i}" for i in range(12)]

    def worker(offset):
        for i in range(300):
            key = keys[(i + offset) % len(keys)]
            assert cache.get_or_compute(key, lambda key=key: _value(int(key[1:]) % 6)) == _value(int(key[1:]) % 6)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    s = cache.stats()
    assert s.hits + s.misses == 6 * 300
    assert s.entries <= 8 and s.retained_transforms <= 40
    assert s.retained_transforms == sum(len(v[0]) for v in cache._entries.values())


# ---------------------------------------------------------------------------------------------------------------------
# EnumerationCache (real registry): cache on/off identity + one necessary-coordinate test per key coordinate
# ---------------------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chem():
    from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile

    return dict(certified=resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE),
                legacy=resolve_algebra_profile("legacy-capped-v1"), ma=_mol("CC(=O)OC"), water=_mol("water"),
                acetic=_mol("acetic acid"), cyclohexene=_mol("C1CC=CCC1"))


def test_cached_enumeration_equals_uncached(chem):
    reg, target, reagents = chem["certified"], chem["ma"], (chem["water"], chem["acetic"])
    direct = reg.enumerate(target, reagents, budget=20_000)
    first = cached_enumerate(reg, target, reagents, budget=20_000)
    second = cached_enumerate(reg, target, reagents, budget=20_000)
    assert first == direct and second == direct and len(direct[0]) == 16
    s = ENUMERATION_CACHE.stats()
    assert (s.hits, s.misses, s.entries, s.retained_transforms) == (1, 1, 1, 16)
    set_enumeration_cache_enabled(False)
    assert cached_enumerate(reg, target, reagents, budget=20_000) == direct   # cache off: byte-identical
    assert ENUMERATION_CACHE.stats().hits == 1


def _necessary(chem_a, chem_b):
    """Two calls differing in ONE coordinate: outputs differ, keys differ, and the second is not served the first."""
    (reg_a, tgt_a, rea_a, bud_a), (reg_b, tgt_b, rea_b, bud_b) = chem_a, chem_b
    assert enumeration_cache_key(reg_a, tgt_a, rea_a, bud_a) != enumeration_cache_key(reg_b, tgt_b, rea_b, bud_b)
    first = cached_enumerate(reg_a, tgt_a, rea_a, budget=bud_a)
    second = cached_enumerate(reg_b, tgt_b, rea_b, budget=bud_b)
    assert second != first
    assert second == reg_b.enumerate(tgt_b, rea_b, budget=bud_b)
    assert ENUMERATION_CACHE.stats().hits == 0


def test_key_coordinate_registry_digest_is_necessary(chem):
    # M-C1 (registry): cyclohexene under legacy capped scission emits 0; the certified algebra's Diels-Alder emits 1.
    assert chem["legacy"].digest != chem["certified"].digest
    w = (chem["water"],)
    _necessary((chem["legacy"], chem["cyclohexene"], w, 20_000), (chem["certified"], chem["cyclohexene"], w, 20_000))


def test_key_coordinate_target_value_is_necessary(chem):
    from smartchem.category import Molecule

    reg, ma, reagents = chem["certified"], chem["ma"], (chem["water"], chem["acetic"])
    # M-C1 (target): the same graph with charge +1 is a different literal value and enumerates differently (16 vs 0).
    cation = Molecule(ma.atoms, ma.bonds, charge=1, state=ma.state)
    _necessary((reg, ma, reagents, 20_000), (reg, cation, reagents, 20_000))
    ENUMERATION_CACHE.clear()
    _necessary((reg, ma, reagents, 20_000), (reg, chem["acetic"], reagents, 20_000))   # a different structure


def test_key_coordinate_reagent_tuple_is_necessary(chem):
    reg, ma = chem["certified"], chem["ma"]
    # M-C1 (reagents): (water, acetic acid) emits 16, (water,) emits 12.
    _necessary((reg, ma, (chem["water"], chem["acetic"]), 20_000), (reg, ma, (chem["water"],), 20_000))


def test_key_coordinate_budget_is_necessary(chem):
    reg, ma, reagents = chem["certified"], chem["ma"], (chem["water"], chem["acetic"])
    # M-C1 (budget): 20000 -> 16 transforms, complete; 5 -> 3 transforms, INCOMPLETE.  A budget-blind key would hand
    # a truncated enumeration to a full-budget check (or a "complete" flag to a truncated one).
    _necessary((reg, ma, reagents, 20_000), (reg, ma, reagents, 5))
    assert cached_enumerate(reg, ma, reagents, budget=5)[1] is False


def test_in_process_patch_is_invisible_to_the_key_and_clear_is_the_hook(chem, monkeypatch):
    # M-C2's premise: a provider patched in-process keeps its digest, so only clear() evicts the stale answer.
    reg, ma, w = chem["certified"], chem["ma"], (chem["water"],)
    honest = cached_enumerate(reg, ma, w, budget=20_000)
    assert honest[0]
    provider_cls = type(reg.providers[0])
    digest_before = reg.digest
    monkeypatch.setattr(provider_cls, "enumerate_transforms", lambda self, r, g, *, budget: ((), True))
    assert reg.digest == digest_before
    assert cached_enumerate(reg, ma, w, budget=20_000) == honest            # stale: the hazard clear() exists for
    ENUMERATION_CACHE.clear()
    assert cached_enumerate(reg, ma, w, budget=20_000) == reg.enumerate(ma, w, budget=20_000)
    assert cached_enumerate(reg, ma, w, budget=20_000) != honest


def test_enumeration_cache_key_is_the_full_argument_values(chem):
    reg, ma = chem["certified"], chem["ma"]
    key = enumeration_cache_key(reg, ma, [chem["water"]], 20_000)
    assert key == (reg.digest, ma, (chem["water"],), 20_000)
    with pytest.raises(TypeError):
        enumeration_cache_key(reg, ma, (), "20000")
