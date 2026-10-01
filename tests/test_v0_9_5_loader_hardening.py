"""0.9.5 barrier A16 -- transport-loader hardening: Wave D F5 (type-confused wire leaked bare ``TypeError`` /
``AttributeError`` / ``KeyError`` / ``IndexError``), Wave D F11 (``producer_signature`` shape), Wave C8 F5 (capability
re-derivation was unbudgeted) and Wave C8 F4's dict leg (nesting depth reached the recursive decoders).

Each test names the broken behaviour it fails on.  The measurements behind the two constants live in
``experiments/v0_9_5_loader_bounds.py``; this file pins the LAWS on the cheap methyl acetate family.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import smartchem.compilation_ir as cir
import smartchem.service as svc
import smartchem.verification as V
from smartchem.capability.presets import isopentyl_capability_fit_bench
from smartchem.data.provider_snapshot import PROVIDER_SNAPSHOT_SCHEMA, ProviderSnapshot
from smartchem.identity import identity_loss_from_payload, identity_loss_to_payload, stereo_loss
from smartchem.process_constraints import ProcessBounds
from smartchem.service import (
    CompilationResponse,
    TransformGrammar,
    affordability_entry_from_payload,
    build_recompile_request,
    deserialize_request,
    deserialize_response,
    load_response,
    load_response_text,
    provider_snapshot_from_payload,
    provider_snapshot_to_payload,
    ranked_dag_summary_from_payload,
    ranked_summary_from_payload,
    request_from_payload,
    request_to_payload,
    response_from_payload,
    response_to_payload,
    run_compilation,
)
from smartchem.smiles import parse_smiles
from smartchem.verification import (
    MalformedPayloadError,
    VerificationBudget,
    VerificationBudgetExceeded,
    VerificationPolicy,
    WorkMeter,
    count_payload_nodes,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_KEY = b"0.9.5-a16-loader-hardening-key-32"


@pytest.fixture(scope="module")
def wire():
    """methyl acetate (2 routes) under the poor-man bench, carrying one provider snapshot: every container a response
    loader decodes is present (request + profile, IR, dossiers with replay, frontier, snapshot)."""
    snap = ProviderSnapshot(PROVIDER_SNAPSHOT_SCHEMA, ("offline",), 1, "d" * 64, "2026-01-01T00:00:00Z", False)
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man"),
                           provider_snapshots=(snap,))
    return response_to_payload(resp)


@pytest.fixture(scope="module")
def dag_wire():
    return response_to_payload(run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        helper_reagents=("water", "acetic acid"), process=ProcessBounds.of(max_total_minutes=30.0))))


@pytest.fixture(scope="module")
def bench_answer():
    """methyl acetate under the 7-bottle isopentyl fit bench: every assessment charges one capability_work unit per
    bottle and one per component (``service._capability_work_units``, A18). Returns those units per assessment."""
    req = build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile=isopentyl_capability_fit_bench())
    resp = run_compilation(req)
    bottles = len(req.capability_profile.material_inventory)
    assert bottles == 7 and len(resp.ranked_route_dossiers) == 2, "setup: the fixture's shape moved"
    units = svc._capability_work_units(req.capability_profile)
    assert units > bottles, "setup: the bench's bottles declare components"
    return req, response_to_payload(resp), units


def _entry_points(wire, dag_wire):
    """(name, honest payload, load(payload)) for every public wire-load entry point (text loaders get json.dumps)."""
    structure_ir = cir.ir_to_payload(cir.decompile_structure_to_ir(parse_smiles("CC"), reagents=(parse_smiles("O"),)))
    formula_ir = cir.ir_to_payload(cir.decompile_to_ir("H2O", ("H2", "O2")))
    snap = provider_snapshot_to_payload(wire_snapshot(wire))
    water = parse_smiles("O")
    text = json.dumps
    return [
        ("load_response", wire, load_response),
        ("response_from_payload", wire, response_from_payload),
        ("deserialize_response", wire, lambda p: deserialize_response(text(p))),
        ("load_response_text", wire, lambda p: load_response_text(text(p))),
        ("request_from_payload", wire["request"], request_from_payload),
        ("deserialize_request", wire["request"], lambda p: deserialize_request(text(p))),
        ("ranked_summary_from_payload", wire["ranked_route_dossiers"][0], ranked_summary_from_payload),
        ("ranked_dag_summary_from_payload", dag_wire["ranked_dag_dossiers"][0], ranked_dag_summary_from_payload),
        ("affordability_entry_from_payload", wire["affordability_frontier"][0], affordability_entry_from_payload),
        ("provider_snapshot_from_payload", snap, provider_snapshot_from_payload),
        ("ir_from_payload", wire["compilation_ir"], cir.ir_from_payload),
        ("deserialize_ir", structure_ir, lambda p: cir.deserialize_ir(text(p))),
        ("identity_loss_from_payload", identity_loss_to_payload(stereo_loss("C[C@H](O)CC")), identity_loss_from_payload),
        ("recompile_structure_from_serialized", structure_ir, lambda p: cir.recompile_structure_from_serialized(text(p))),
        ("recompile_from_serialized", formula_ir,
         lambda p: cir.recompile_from_serialized(text(p), structure=water, reagents=())),
    ]


def wire_snapshot(wire):
    return provider_snapshot_from_payload(wire["provider_snapshots"][0])


_CONFUSIONS = (None, 0, "", [], {}, True, 1.5, float("nan"), float("inf"), -1, "xxx", [None], {"x": None})


def _paths(obj, prefix=(), depth=0):
    if depth >= 4:
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield prefix + (key,)
            yield from _paths(value, prefix + (key,), depth + 1)
    elif isinstance(obj, list) and obj:
        yield prefix + (0,)
        yield from _paths(obj[0], prefix + (0,), depth + 1)


def _confused(payload, stride):
    """A deterministic sample (every ``stride``-th) of path x confusion mutations, plus every top-level key deleted."""
    index = 0
    for path in _paths(payload):
        for value in _CONFUSIONS:
            index += 1
            if index % stride:
                continue
            mutated = copy.deepcopy(payload)
            parent = mutated
            for step in path[:-1]:
                parent = parent[step]
            parent[path[-1]] = copy.deepcopy(value)
            yield f"{path}={value!r}", mutated
    if isinstance(payload, dict):
        for key in payload:
            mutated = copy.deepcopy(payload)
            del mutated[key]
            yield f"del {key}", mutated


def _outcome(call):
    try:
        call()
        return "ACCEPT"
    except ValueError:
        return "REFUSE"
    except Exception as exc:  # noqa: BLE001 -- the class IS the fact under test
        return f"LEAK {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------------------------------------------------
# F5: every public wire-load entry point refuses type-confused wire TYPED -- never a bare TypeError/AttributeError/...
# ---------------------------------------------------------------------------------------------------------------------

def test_every_public_loader_refuses_type_confusion_typed(wire, dag_wire):
    """Fails if any public loader lets a type confusion escape as anything but a ValueError (the refusal class) -- the
    Wave D fuzz found 386 bare TypeErrors on the response loaders alone."""
    leaks = []
    for name, base, load in _entry_points(wire, dag_wire):
        assert _outcome(lambda b=base: load(copy.deepcopy(b))) == "ACCEPT", f"setup: honest {name} must load"
        stride = 17 if name in ("load_response", "response_from_payload", "deserialize_response",
                                "load_response_text") else 5
        for label, mutated in _confused(base, stride):
            outcome = _outcome(lambda m=mutated: load(m))
            if outcome.startswith("LEAK"):
                leaks.append(f"{name} {label}: {outcome[:160]}")
    assert leaks == []


@pytest.mark.parametrize("loader", [load_response, response_from_payload, request_from_payload,
                                    ranked_summary_from_payload, ranked_dag_summary_from_payload,
                                    affordability_entry_from_payload, provider_snapshot_from_payload,
                                    cir.ir_from_payload, identity_loss_from_payload])
@pytest.mark.parametrize("payload", [None, [], "x", 3, 1.5, True])
def test_a_non_object_payload_is_a_typed_refusal(loader, payload):
    """Fails if a public dict loader leaks AttributeError/TypeError on a payload that is not a JSON object."""
    with pytest.raises(ValueError):
        loader(payload)


@pytest.mark.parametrize("loader", [deserialize_response, load_response_text, deserialize_request, cir.deserialize_ir,
                                    cir.recompile_structure_from_serialized])
@pytest.mark.parametrize("text", [None, 3, b"\xff", ["{}"]])
def test_a_text_loader_refuses_a_non_text_argument_typed(loader, text):
    """Fails if a text loader leaks json's own TypeError for a non-text argument."""
    with pytest.raises(ValueError):
        loader(text)


@pytest.mark.parametrize("mutate", [
    lambda d: d["ranked_route_dossiers"].__setitem__(0, None),
    lambda d: d["request"].__setitem__("stock_materials", None),
    lambda d: d["request"]["constraints"].__setitem__("schema_version", []),
    lambda d: d["request"]["search_bounds"].__setitem__(0, 0),
    lambda d: d.__setitem__("transport_mode", []),
    lambda d: d.__setitem__("ranked_route_dossiers", "xxx"),
    lambda d: d["request"]["terminal_policy"].__setitem__("commodities_enabled", None),
], ids=["dossier-null", "stock-null", "constraints-schema-list", "bound-int", "transport-list", "dossiers-str",
        "commodities-null"])
def test_the_wave_d_leaks_refuse_as_malformed_payload(wire, mutate):
    """The Wave D p22/p18 repros: each used to escape as a bare TypeError/AttributeError.  Fails if any is not a
    MalformedPayloadError (a ValueError -- the refusal class -- AND a TypeError, so the old catch still catches) on
    every response loader, the text ones included."""
    payload = copy.deepcopy(wire)
    mutate(payload)
    text = json.dumps(payload)
    for call in (lambda: load_response(copy.deepcopy(payload)), lambda: response_from_payload(copy.deepcopy(payload)),
                 lambda: deserialize_response(text), lambda: load_response_text(text)):
        with pytest.raises(MalformedPayloadError) as info:
            call()
        assert isinstance(info.value, ValueError) and isinstance(info.value, TypeError)
        assert info.value.__cause__ is not None and "refused (0.9.5 Wave D F5)" in str(info.value)


def test_the_fold_maps_shape_errors_only_never_to_an_answer():
    """Fails if the boundary fold swallows (returns), widens to arbitrary exceptions, or re-wraps a budget refusal."""
    for raised in (TypeError("t"), AttributeError("a"), KeyError("k"), IndexError("i")):
        with pytest.raises(MalformedPayloadError) as info, V._malformed_is_refused():
            raise raised
        assert info.value.__cause__ is raised
    for passthrough in (ValueError("v"), VerificationBudgetExceeded("capability_work", 1, 2), RecursionError("r"),
                        RuntimeError("x"), ZeroDivisionError("z")):
        with pytest.raises(type(passthrough)) as info, V._malformed_is_refused():
            raise passthrough
        assert info.value is passthrough


def test_a_nested_malformed_refusal_is_not_double_wrapped(wire):
    payload = copy.deepcopy(wire)
    payload["request"]["stock_materials"] = None
    with pytest.raises(MalformedPayloadError) as info:
        response_from_payload(payload)
    assert str(info.value).count("malformed payload") == 1


def test_malformed_payload_error_is_exported_from_service_and_verification():
    assert svc.MalformedPayloadError is V.MalformedPayloadError is MalformedPayloadError
    assert "MalformedPayloadError" in svc.__all__ and "MalformedPayloadError" in V.__all__


# ---------------------------------------------------------------------------------------------------------------------
# F11: producer_signature is null or 64 lowercase hex -- on keyless loads too
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("signature", [0, "", "xxx", "A" * 64, "0" * 63, "0" * 65, "0" * 63 + "g", " " + "0" * 63,
                                       "0" * 64 + "\n", [], {}, True, 1.5, float("nan"), ["0" * 64]])
def test_a_malformed_producer_signature_is_refused_on_a_keyless_load(wire, signature):
    """Fails if a keyless load accepts anything but null / 64-hex in the signature slot (Wave D F11: 0, {}, [], NaN,
    "xxx" all loaded)."""
    payload = copy.deepcopy(wire)
    payload["producer_signature"] = signature
    for call in (lambda: load_response(copy.deepcopy(payload)), lambda: response_from_payload(copy.deepcopy(payload))):
        with pytest.raises(ValueError, match="producer_signature must be null or a 64-hex-digit HMAC-SHA256"):
            call()


def test_a_well_shaped_signature_is_shape_checked_only_keyless_and_verified_keyed(wire):
    """The shape law is a SHAPE law: a keyless load still does not verify a 64-hex signature (it is advisory there, per
    the transport ledger), and a keyed load still refuses one that does not verify."""
    payload = copy.deepcopy(wire)
    payload["producer_signature"] = "0" * 64
    assert load_response(copy.deepcopy(payload)).response is not None
    with pytest.raises(ValueError, match="does not verify"):
        load_response(copy.deepcopy(payload), VerificationPolicy(verification_key=_KEY))
    signed = response_to_payload(run_compilation(request_from_payload(wire["request"])), signing_key=_KEY)
    assert load_response(signed, VerificationPolicy(verification_key=_KEY, require_signature=True)).response


def test_a_legacy_v08_payload_obeys_the_signature_shape_law():
    legacy = json.loads((_FIXTURES / "v08" / "response_isopentyl_acetate.json").read_text())
    assert legacy["producer_signature"] is None and load_response(copy.deepcopy(legacy)).response.is_legacy_v08
    legacy["producer_signature"] = 7
    with pytest.raises(ValueError, match="producer_signature must be null"):
        load_response(legacy)


# ---------------------------------------------------------------------------------------------------------------------
# C8 F5: capability_work -- charged BEFORE each assessment, refused before an over-budget one runs, never a skip
# ---------------------------------------------------------------------------------------------------------------------

class _AssessSpy:
    def __init__(self, monkeypatch):
        self.calls = 0
        real = svc.assess_capability

        def spy(*args, **kwargs):
            self.calls += 1
            return real(*args, **kwargs)
        monkeypatch.setattr(svc, "assess_capability", spy)


def test_capability_work_is_bottles_plus_components_per_assessment(bench_answer, monkeypatch):
    """Fails if an honest load's capability re-derivation goes uncharged, or is charged by anything but (bottles +
    components) x assessments."""
    req, thick, bottles = bench_answer
    spy = _AssessSpy(monkeypatch)
    pins = dict(expected_request_digest=req.semantic_digest,
                expected_capability_question_digest=req.capability_question_digest)
    for policy in (VerificationPolicy(), VerificationPolicy(require_verified_admission=True, **pins),
                   VerificationPolicy(require_reexecution=True, **pins)):
        spy.calls = 0
        work = load_response(copy.deepcopy(thick), policy).receipt.work.capability_work
        assert spy.calls > 0 and work == spy.calls * bottles


def test_an_empty_inventory_still_charges_one_unit_per_assessment(wire, monkeypatch):
    """The poor-man preset declares no bottles; an assessment over it is still work (``max(1, bottles)``)."""
    assert wire["request"]["capability_profile"] is not None
    spy = _AssessSpy(monkeypatch)
    work = load_response(copy.deepcopy(wire)).receipt.work.capability_work
    assert spy.calls > 0 and work == spy.calls


@pytest.mark.parametrize("allowed", [0, 1, 2])
def test_capability_work_is_charged_and_refused_before_the_assessment_runs(bench_answer, monkeypatch, allowed):
    """A budget of ``allowed`` assessments' worth (minus one unit when 0) lets EXACTLY ``allowed`` assessments run, then
    refuses typed -- fails if the charge comes after the work (one extra assessment runs) or the refusal waits for the
    end of the load (every assessment runs)."""
    _req, thick, bottles = bench_answer
    spy = _AssessSpy(monkeypatch)
    limit = max(1, allowed * bottles) if allowed else bottles - 1
    with pytest.raises(VerificationBudgetExceeded) as info:
        load_response(copy.deepcopy(thick), VerificationPolicy(budget=VerificationBudget(capability_work=limit)))
    assert info.value.counter == "capability_work" and info.value.limit == limit
    assert spy.calls == allowed


@pytest.mark.parametrize("extra", [{}, {"require_verified_admission": True}, {"require_reexecution": True}])
def test_capability_exhaustion_never_accepts(bench_answer, extra):
    """Fails if any policy turns capability-budget exhaustion into a loaded answer."""
    req, thick, bottles = bench_answer
    policy = VerificationPolicy(budget=VerificationBudget(capability_work=bottles + 1),
                                expected_request_digest=req.semantic_digest, **extra)
    with pytest.raises(VerificationBudgetExceeded):
        load_response(copy.deepcopy(thick), policy)


def test_a_swallowed_capability_refusal_still_refuses_the_load(bench_answer, monkeypatch):
    """The overflow is STICKY: even if EVERY check that assesses swallowed the refusal (and skipped the rest of its
    work), the load cannot finish -- fails if exhaustion could ever become a skipped assessment plus an answer."""
    _req, thick, bottles = bench_answer
    for name in ("_check_capability_coherence", "_check_ranking_coherence"):
        real = getattr(CompilationResponse, name)

        def swallowing(self, *args, _real=real, **kwargs):
            try:
                _real(self, *args, **kwargs)
            except VerificationBudgetExceeded:
                pass                                 # the "helpful" skip
        monkeypatch.setattr(CompilationResponse, name, swallowing)
    with pytest.raises(VerificationBudgetExceeded) as info:
        load_response(copy.deepcopy(thick), VerificationPolicy(budget=VerificationBudget(capability_work=bottles - 1)))
    assert info.value.counter == "capability_work"


def test_the_producer_path_charges_nothing(bench_answer):
    """Outside a load there is no meter: compiling under a big bench is never refused by a verification budget."""
    req, _thick, _bottles = bench_answer
    assert V.current_context() is None and run_compilation(req).ranked_route_dossiers


def test_charge_deferred_is_sticky_and_typed():
    meter = WorkMeter(VerificationBudget(capability_work=10))
    meter.charge_deferred("capability_work", 10)
    assert not meter.exhausted
    meter.charge_deferred("capability_work", 1)             # records, never raises here
    assert meter.exhausted and meter.consumed("capability_work") == 11
    with pytest.raises(VerificationBudgetExceeded) as info:
        meter.raise_if_exhausted()
    assert (info.value.counter, info.value.limit, info.value.consumed) == ("capability_work", 10, 11)
    with pytest.raises(VerificationBudgetExceeded):
        meter.charge("dossiers")                              # the next checked charge refuses too
    with pytest.raises(ValueError, match="use charge_deferred"):
        WorkMeter(VerificationBudget()).charge("capability_work")
    with pytest.raises(ValueError, match="unknown deferred budget counter"):
        WorkMeter(VerificationBudget()).charge_deferred("dossiers", 1)
    with pytest.raises(ValueError):
        WorkMeter(VerificationBudget()).charge_deferred("capability_work", -1)


def test_capability_work_is_a_budget_counter_like_the_others():
    assert VerificationBudget().capability_work == V._DEFAULT_CAPABILITY_WORK
    assert VerificationBudget.unlimited().capability_work is None
    for bad in (0, -1):
        with pytest.raises(ValueError):
            VerificationBudget(capability_work=bad)
    with pytest.raises(TypeError):
        VerificationBudget(capability_work=1.5)
    assert "capability_work" in V._BUDGET_COUNTERS and "capability_work" in V._DEFERRED_COUNTERS


# ---------------------------------------------------------------------------------------------------------------------
# C8 F4 (dict leg): nesting deeper than any honest payload refuses TYPED, before any decoder can recurse
# ---------------------------------------------------------------------------------------------------------------------

def _chain(depth: int) -> list:
    """A list nested ``depth`` containers deep (root = 1)."""
    root = node = []
    for _ in range(depth - 1):
        node.append([])
        node = node[0]
    return root


def _with_deep_profile_node(wire, depth: int) -> dict:
    """``wire`` with the capability profile's inventory replaced by a canonical-codec tuple chain of ``depth`` levels
    (each level adds two containers: the node and its ``items``) -- the C8 F4 shape (5,000 levels crashed
    ``response_from_payload`` with RecursionError).  Built fresh: copy.deepcopy itself recurses on such a chain."""
    payload = copy.deepcopy(wire)
    deep = node = {"type": "tuple", "items": []}
    for _ in range(depth):
        child = {"type": "tuple", "items": []}
        node["items"].append(child)
        node = child
    for field in payload["request"]["capability_profile"]["fields"]:
        if field[0] == "material_inventory":
            field[1] = deep
    return payload


def test_the_depth_ceiling_is_exact():
    ceiling = V._MAX_PAYLOAD_DEPTH
    assert count_payload_nodes(_chain(ceiling)) == ceiling
    with pytest.raises(ValueError, match=f"nests containers more than {ceiling} deep"):
        count_payload_nodes(_chain(ceiling + 1))
    assert count_payload_nodes([[[0]] * 3]) == 8              # scalars add no depth: only containers nest


@pytest.mark.parametrize("depth", [V._MAX_PAYLOAD_DEPTH // 2 + 5, 5_000])   # chain levels: each adds 2 containers
def test_deep_nesting_refuses_typed_before_any_decode(wire, monkeypatch, depth):
    """Fails if a deep payload reaches a decoder (RecursionError at 5,000, or any decode at all) instead of the walk's
    typed refusal."""
    decoded = []
    real = svc._capability_profile_from_payload
    monkeypatch.setattr(svc, "_capability_profile_from_payload", lambda p: decoded.append(1) or real(p))
    for call in (lambda: load_response(_with_deep_profile_node(wire, depth)),
                 lambda: response_from_payload(_with_deep_profile_node(wire, depth)),
                 lambda: request_from_payload(_with_deep_profile_node(wire, depth)["request"])):
        with pytest.raises(ValueError, match="nests containers more than"):
            call()
    assert decoded == []


def test_deep_text_refuses_typed_on_every_text_loader(wire):
    """Nesting the JSON decoder CAN read but no honest payload has: refused by the walk, not by a decoder."""
    deep = _with_deep_profile_node(wire, V._MAX_PAYLOAD_DEPTH // 2 + 5)
    for loader in (load_response_text, deserialize_response):
        with pytest.raises(ValueError, match="nests containers more than"):
            loader(json.dumps(deep))
    with pytest.raises(ValueError, match="nests containers more than"):
        deserialize_request(json.dumps(deep["request"]))
    with pytest.raises(ValueError, match="nests containers more than"):
        deserialize_request("[" * (V._MAX_PAYLOAD_DEPTH + 5) + "]" * (V._MAX_PAYLOAD_DEPTH + 5))
    with pytest.raises(ValueError):
        cir.deserialize_ir("[" * 200_000 + "]" * 200_000)    # past json's own recursion: a refusal, not a crash


def test_every_dict_loader_runs_the_walk_first(wire, dag_wire):
    """Each public dict loader refuses a cyclic or too-deep payload through the walk -- fails if one decodes first."""
    deep = _chain(V._MAX_PAYLOAD_DEPTH + 1)
    for loader, base in ((request_from_payload, wire["request"]),
                         (ranked_summary_from_payload, wire["ranked_route_dossiers"][0]),
                         (ranked_dag_summary_from_payload, dag_wire["ranked_dag_dossiers"][0]),
                         (affordability_entry_from_payload, wire["affordability_frontier"][0]),
                         (provider_snapshot_from_payload, wire["provider_snapshots"][0]),
                         (cir.ir_from_payload, wire["compilation_ir"]),
                         (identity_loss_from_payload, identity_loss_to_payload(stereo_loss("C[C@H](O)CC")))):
        payload = copy.deepcopy(base)
        payload["schema_version"] = deep
        with pytest.raises(ValueError, match="nests containers more than"):
            loader(payload)
        cyclic = copy.deepcopy(base)
        cyclic["schema_version"] = cyclic
        with pytest.raises(ValueError, match="cyclic"):
            loader(cyclic)


# ---------------------------------------------------------------------------------------------------------------------
# honest payloads still load under the defaults
# ---------------------------------------------------------------------------------------------------------------------

def _depth(obj) -> int:
    best, stack = 0, [(obj, 1)]
    while stack:
        node, d = stack.pop()
        kids = node.values() if isinstance(node, dict) else node if isinstance(node, list) else None
        if kids is not None:
            best = max(best, d)
            stack.extend((k, d + 1) for k in kids)
    return best


def test_every_committed_fixture_sits_well_under_the_depth_ceiling():
    """Every JSON fixture (v0.8 payloads, CLI goldens, repros) nests at most a quarter of the ceiling -- fails if a
    fixture (or a ceiling change) erodes the measured margin (experiments/v0_9_5_loader_bounds.py)."""
    depths = {str(p.relative_to(_FIXTURES)): _depth(json.loads(p.read_text())) for p in _FIXTURES.rglob("*.json")}
    assert depths and max(depths.values()) * 4 <= V._MAX_PAYLOAD_DEPTH, max(depths.items(), key=lambda kv: kv[1])


def test_honest_payloads_load_under_the_default_policy(wire, dag_wire, bench_answer):
    _req, thick, _bottles = bench_answer
    for payload in (wire, dag_wire, thick):
        verified = load_response(copy.deepcopy(payload))
        assert verified.receipt.work.within(VerificationBudget())
        assert verified.receipt.work.capability_work <= V._DEFAULT_CAPABILITY_WORK
    # every real v0.8 fixture the frozen baseline accepts (the sulfuric-acid pair is refused there by design, Wave C2 P2)
    for name in ("ethyl_acetate_smiles", "ethyl_acetate_smiles_thin", "invalid_input_ethyl_acetate_name",
                 "isopentyl_acetate_dag", "isopentyl_acetate", "stereo_isopentyl_acetate_smiles"):
        load_response(json.loads((_FIXTURES / "v08" / f"response_{name}.json").read_text()))
    for name in ("ethyl_acetate_smiles", "invalid_input_ethyl_acetate_name", "isopentyl_acetate"):
        request_from_payload(json.loads((_FIXTURES / "v08" / f"request_{name}.json").read_text()))
    ir = cir.decompile_structure_to_ir(parse_smiles("CC"), reagents=(parse_smiles("O"),))
    assert cir.deserialize_ir(cir.serialize_ir(ir)) == ir
    assert identity_loss_from_payload(identity_loss_to_payload(stereo_loss("C[C@H](O)CC"))) == stereo_loss("C[C@H](O)CC")
    assert request_from_payload(request_to_payload(request_from_payload(wire["request"]))) == request_from_payload(
        wire["request"])


def test_the_decorated_loaders_keep_their_identity():
    """``functools.wraps``: name, docstring and the undecorated function (``__wrapped__``) survive the decorator."""
    for loader in (request_from_payload, ranked_summary_from_payload, ranked_dag_summary_from_payload,
                   affordability_entry_from_payload, provider_snapshot_from_payload, cir.ir_from_payload,
                   identity_loss_from_payload):
        assert loader.__wrapped__.__name__ == loader.__name__ and loader.__doc__


def test_a_bottle_s_components_are_charged_not_only_the_bottle():
    """Wave E (A18): charged per bottle, ONE bottle carrying 40,000 name-keyed components loaded in 34 s for 32 units
    -- every component is walked (each name-keyed one resolved through the offline name table), so each is charged."""
    from types import SimpleNamespace
    bench = isopentyl_capability_fit_bench()
    inventory = bench.material_inventory
    assert svc._capability_work_units(bench) == len(inventory) + sum(len(b.components) for b in inventory)
    fat = SimpleNamespace(material_inventory=(SimpleNamespace(components=(None,) * 40_000),))
    assert svc._capability_work_units(fat) == 40_001
    assert svc._capability_work_units(SimpleNamespace(material_inventory=())) == 1
