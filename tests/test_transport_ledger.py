"""X-high D27.8 -- the transport ledger is machine-checked: COMPLETE (every field and wire key has exactly one entry),
never STALE (no entry for a field that is gone, every named check resolves to real code), in agreement with the service
module's keyless-consumer paragraph in BOTH directions, and -- on the response's own tables -- in agreement with the
loader's behaviour (a re-derived key cannot be forged; an advisory one really is advisory)."""
from __future__ import annotations

import copy
import dataclasses as dc
import importlib
import re

import pytest

import smartchem.service as svc
from smartchem import compilation_ir as cir
from smartchem.process_constraints import ProcessBounds
from smartchem.transport_ledger import (
    TRANSPORT_LEDGER,
    LedgerEntry,
    TransportStatus,
    advisory_fields,
    status_counts,
)

_CLASSES = {
    "CompilationResponse": svc.CompilationResponse,
    "RankedRouteSummary": svc.RankedRouteSummary,
    "RankedDAGSummary": svc.RankedDAGSummary,
    "ChemicalCompilationIR": cir.ChemicalCompilationIR,
    "Section81ReceiptView": cir.Section81ReceiptView,
    "CandidateSummary": cir.CandidateSummary,
}
_KW = dict(helper_reagents=("water", "acetic acid"), process=ProcessBounds.of(max_total_minutes=30.0))


@pytest.fixture(scope="module")
def honest():
    """Honest answers covering the routes, DAG and decompile shapes, so every emitted wire key is observed."""
    return (
        svc.run_compilation(svc.build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man",
                                                        **_KW)),
        svc.run_compilation(svc.build_recompile_request(
            "smiles:CC(=O)OC", max_depth=2, grammar=svc.TransformGrammar.CAPPED_SCISSION_CONVERGENT, **_KW)),
        svc.run_compilation(svc.build_decompile_request("C2H6O")),
    )


@pytest.mark.parametrize("table", sorted(_CLASSES))
def test_every_dataclass_field_has_exactly_one_entry_and_no_entry_is_stale(table):
    fields = {f.name for f in dc.fields(_CLASSES[table])}
    ledger = set(TRANSPORT_LEDGER[table])
    assert not fields - ledger, f"{table}: fields with NO ledger entry: {sorted(fields - ledger)}"
    assert not ledger - fields, f"{table}: STALE ledger entries: {sorted(ledger - fields)}"


def test_every_wire_key_and_replay_step_key_has_exactly_one_entry(honest):
    wire_keys, dossier_keys, dag_keys, ir_keys, receipt_keys, candidate_keys = (set() for _ in range(6))
    for resp in honest:
        w = svc.response_to_payload(resp)
        wire_keys |= set(w)
        for d in w["ranked_route_dossiers"]:
            dossier_keys |= set(d)
        for d in w["ranked_dag_dossiers"]:
            dag_keys |= set(d)
        ir_keys |= set(w["compilation_ir"])
        receipt_keys |= set(w["compilation_ir"]["search_receipt"])
        for c in w["compilation_ir"]["candidates"]:
            candidate_keys |= set(c)
    assert dossier_keys and dag_keys and candidate_keys, "setup: every record shape must be observed"
    assert wire_keys - set(TRANSPORT_LEDGER["CompilationResponse"]) == set(TRANSPORT_LEDGER["CompilationResponse.wire"])
    assert dossier_keys - set(TRANSPORT_LEDGER["RankedRouteSummary"]) == set(TRANSPORT_LEDGER["RankedRouteSummary.wire"])
    assert dag_keys == set(TRANSPORT_LEDGER["RankedDAGSummary"])
    assert ir_keys == set(TRANSPORT_LEDGER["ChemicalCompilationIR"])
    assert receipt_keys == set(TRANSPORT_LEDGER["Section81ReceiptView"])
    assert candidate_keys == set(TRANSPORT_LEDGER["CandidateSummary"])
    assert set(svc._STEP_PAYLOAD_FIELDS) == set(TRANSPORT_LEDGER["replay_step"])


def _resolve(dotted: str):
    module, _, qualname = dotted.partition(":")
    obj = importlib.import_module(module)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    return obj


def test_every_named_check_resolves_to_real_code():
    for table, entries in TRANSPORT_LEDGER.items():
        for name, entry in entries.items():
            for check in entry.checks:
                try:
                    target = _resolve(check)
                except (ImportError, AttributeError) as exc:
                    raise AssertionError(f"{table}.{name}: stale check {check!r} ({exc})") from exc
                assert callable(target), f"{table}.{name}: {check!r} is not code"


def test_the_entry_shape_laws():
    with pytest.raises(ValueError):
        LedgerEntry(TransportStatus.DIGEST_ONLY_ADVISORY, ("smartchem.service:response_from_payload",))
    with pytest.raises(ValueError):
        LedgerEntry(TransportStatus.RE_DERIVED_ON_LOAD)
    for table, entries in TRANSPORT_LEDGER.items():
        for name, entry in entries.items():
            assert entry.thin in (None, TransportStatus.DIGEST_ONLY_ADVISORY), f"{table}.{name}"
            assert entry.thin is None or entry.status is not TransportStatus.DIGEST_ONLY_ADVISORY, f"{table}.{name}"
    assert sum(status_counts().values()) == sum(len(t) for t in TRANSPORT_LEDGER.values())


_TOKEN = re.compile(r"\b(CompilationResponse\.wire|CompilationResponse|RankedRouteSummary\.wire|RankedRouteSummary|"
                    r"RankedDAGSummary|ChemicalCompilationIR|Section81ReceiptView|CandidateSummary|replay_step)"
                    r"\.([a-z_]+)\b")


def test_the_service_docstring_names_exactly_the_advisory_fields():
    doc = svc.__doc__
    section = doc[doc.index("What a KEYLESS consumer must treat as advisory"):]
    named = {f"{table}.{field}" for table, field in _TOKEN.findall(section)}
    advisory = set(advisory_fields())
    assert not advisory - named, f"advisory fields the service docstring does not name: {sorted(advisory - named)}"
    assert not named - advisory, f"the service docstring names NON-advisory fields: {sorted(named - advisory)}"


def _refresh(wire, resp):
    """The keyless forger: recompute the PUBLIC whole-body wire digest after an edit."""
    wire["result_digest"] = svc._transport_bound_result_digest(resp.result_digest, wire["transport_mode"],
                                                               svc._payload_body_digest(wire))
    return wire


_FORGED_WIRE_VALUES = {
    "exit_code": lambda v: v + 1,
    "process_selection_status": lambda v: "NOT_REQUESTED" if v != "NOT_REQUESTED" else "NO_FIT_FOUND",
    "admissible_route_digests": lambda v: [*v, "0" * 64],
    "search_space_status": lambda v: "NO_ROUTE_IN_DECLARED_SPACE" if v != "NO_ROUTE_IN_DECLARED_SPACE" else None,
    "capability_question_digest": lambda v: "0" * 64,
    "transport_mode": lambda v: "THIN_ADVISORY",
    "producer_signature": lambda v: "0" * 64,
    "provider_snapshots": lambda v: [{"schema_version": "smartchem.data/provider-snapshot-v1alpha1",
                                      "provider_ids": ["pubchem"], "record_count": 3, "content_digest": "0" * 64,
                                      "fetched_at": "2026-09-28T00:00:00Z", "allow_network": True}],
    "parse_receipt_summary": lambda v: f"{v} (FORGED)",
}


@pytest.mark.parametrize("key", sorted(_FORGED_WIRE_VALUES))
def test_the_response_level_statuses_are_the_loaders_behaviour(honest, key):
    """Behavioural agreement on the response's own keys: a keyless forger edits the key and recomputes the public
    digest -- a RE_DERIVED / BOUND key is refused, an ADVISORY one loads (the ledger neither over- nor under-claims)."""
    resp = honest[0]
    table = "CompilationResponse.wire" if key in TRANSPORT_LEDGER["CompilationResponse.wire"] else "CompilationResponse"
    status = TRANSPORT_LEDGER[table][key].status
    wire = svc.response_to_payload(resp)
    forged = copy.deepcopy(wire)
    forged[key] = _FORGED_WIRE_VALUES[key](forged[key])
    _refresh(forged, resp)
    if status is TransportStatus.DIGEST_ONLY_ADVISORY:
        svc.response_from_payload(forged)
    else:
        with pytest.raises(ValueError):
            svc.response_from_payload(forged)


def test_the_result_digest_is_the_whole_body_digest(honest):
    for resp in honest:
        for include_replay in (True, False):
            wire = svc.response_to_payload(resp, include_replay=include_replay)
            assert wire["result_digest"] == svc._transport_bound_result_digest(
                resp.result_digest, wire["transport_mode"], svc._payload_body_digest(wire))
            svc.response_from_payload(wire)
