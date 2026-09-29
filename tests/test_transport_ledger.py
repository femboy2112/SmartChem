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
    partially_advisory_fields,
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
    with pytest.raises(ValueError):  # D28.4: advisory_when qualifies a re-derived / bound entry only
        LedgerEntry(TransportStatus.DIGEST_ONLY_ADVISORY, advisory_when="always")
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
    always, _, partial = section.partition("Partially advisory")
    named = {f"{table}.{field}" for table, field in _TOKEN.findall(always)}
    advisory = set(advisory_fields())
    assert not advisory - named, f"advisory fields the service docstring does not name: {sorted(advisory - named)}"
    assert not named - advisory, f"the service docstring names NON-advisory fields: {sorted(named - advisory)}"
    # X-high D28.4: the partially advisory entries (``advisory_when``) are named in their own sentence -- no more, no less.
    named_partial = {f"{table}.{field}" for table, field in _TOKEN.findall(partial)}
    assert named_partial == set(partially_advisory_fields()), (
        f"'Partially advisory' names {sorted(named_partial)} but the ledger's advisory_when entries are "
        f"{sorted(partially_advisory_fields())}")
    assert "UNCONSTRAINED convergent-DAG" in partial, "D28.4: the unconstrained-DAG candidate case must be disclosed"


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


# -- X-high D28.6: every RE_DERIVED / BOUND / FROZEN label has a keyless single-field forgery the loader REFUSES ----------
#
# The Wave C5 audit found four ledger entries labelled re-derived / bound that a keyless forger could change and still
# load (C5-F1..F4): the old behaviour test covered only the 9 top-level wire keys and merely checked that nested checks
# EXIST.  Here EVERY non-advisory entry names one forgery on an honest world: one field edited, then EVERY public digest a
# keyless forger controls recomputed from the forged content (the response's own result identity via the loader's own
# constructor call, the derived wire keys, the whole-body wire digest) -- so the refusal must come from the entry's own law,
# never from a stale public digest.  A new RE / REQ / FROZEN label without a refusing forgery here fails the suite.

_DERIVED_WIRE = ("process_selection_status", "admissible_route_digests", "exit_code", "search_space_status",
                 "capability_question_digest")


def _raw_response(p):
    """The loader's own constructor call (``response_from_payload``), without its load-time checks: what a keyless forger
    runs to recompute the response's public result identity from a forged payload."""
    ir = p["compilation_ir"]
    return svc.CompilationResponse(
        p["schema_version"], svc.request_from_payload(p["request"]), svc.ResponseOutcome(p["outcome"]),
        p["standard_status"], None if ir is None else cir.ir_from_payload(ir), tuple(p["diagnostics"]),
        tuple(svc.ranked_summary_from_payload(r) for r in p["ranked_route_dossiers"]),
        tuple(svc.affordability_entry_from_payload(e) for e in p["affordability_frontier"]),
        tuple(svc.provider_snapshot_from_payload(s) for s in p["provider_snapshots"]),
        parse_receipt_summary=p["parse_receipt_summary"],
        ranked_dag_dossiers=tuple(svc.ranked_dag_summary_from_payload(d) for d in p["ranked_dag_dossiers"]))


def _reforge(p, *, keep=frozenset()):
    """The keyless forger: recompute every public pin from the FORGED content (``keep`` names the forged key itself)."""
    raw = _raw_response(p)
    for key in _DERIVED_WIRE:
        if key not in keep:
            value = getattr(raw, key)
            p[key] = list(value) if key == "admissible_route_digests" else value
    if "result_digest" not in keep:
        p["result_digest"] = svc._transport_bound_result_digest(raw.result_digest, p["transport_mode"],
                                                               svc._payload_body_digest(p))
    return p


@pytest.fixture(scope="module")
def worlds(honest):
    routes, dag, decompile = honest
    mesal = svc.run_compilation(svc.build_recompile_request(
        "smiles:COC(=O)c1ccccc1O", max_depth=1, helper_reagents=("water",),
        stock_materials=("salicylic acid", "methanol"), max_temperature_k=320.0, capability_profile="poor-man"))
    stereo = svc.run_compilation(svc.build_recompile_request(
        "smiles:C[C@H](O)C(=O)OC", max_depth=1, helper_reagents=("water",), stock_materials=("methanol",)))
    # glycolaldehyde DECLARED (no transform of methyl acetate consumes it): a leaf swapped for this isomer stays inside
    # the terminal set, so D26.1 passes and only D29.1 can refuse it
    isomer = svc.run_compilation(svc.build_recompile_request(
        "smiles:CC(=O)OC", max_depth=1, helper_reagents=("water", "acetic acid"), stock_materials=("smiles:OCC=O",)))
    built = {"routes": routes, "dag": dag, "decompile": decompile, "mesal": mesal, "stereo": stereo, "isomer": isomer}
    wires = {name: svc.response_to_payload(resp, include_replay=True) for name, resp in built.items()}
    assert wires["mesal"]["affordability_frontier"], "setup: the mesal world must carry a frontier entry"
    assert wires["stereo"]["compilation_ir"]["identity_losses"], "setup: the stereo world must carry an identity loss"
    assert len(wires["dag"]["ranked_dag_dossiers"]) >= 2 and len(wires["routes"]["ranked_route_dossiers"]) >= 2
    return wires


_IR = lambda p: p["compilation_ir"]  # noqa: E731
_RC = lambda p: p["compilation_ir"]["search_receipt"]  # noqa: E731
_CAND = lambda p: p["compilation_ir"]["candidates"][0]  # noqa: E731
_DS = lambda p: p["ranked_route_dossiers"][0]  # noqa: E731
_DG = lambda p: p["ranked_dag_dossiers"][0]  # noqa: E731
_DGE = lambda p: max(p["ranked_dag_dossiers"], key=lambda d: len(d["edges"]))  # noqa: E731  (the most-connected DAG)
_ST = lambda p: p["ranked_route_dossiers"][0]["replay_payload"][0]  # noqa: E731
_BUMP = "99"


def _set(getter, key, value):
    return lambda p, wires: getter(p).__setitem__(key, value(getter(p)[key]) if callable(value) else value)


def _bump_bound(name):
    def edit(p, wires):
        for pair in p["request"]["search_bounds"]:
            if pair[0] == name:
                pair[1] += 1
    return edit


def _promote_readiness(p, wires):
    """A PROCESS_SPECIFIED forgery: every unknown obligation of step 1 flipped to SATISFIED, its open obligations and the
    route's cleared, and the derived wire tier kept coherent -- a structurally valid ladder the replay cannot support."""
    readiness = _DS(p)["readiness"]
    for step in readiness["per_step"]:
        for key in ("process", "workup_isolation"):
            step[key] = "SATISFIED"
        step["open_obligations"] = []
    readiness["route_open_obligations"] = []
    _DS(p)["readiness_tier"] = "PROCESS_SPECIFIED"


def _fit(value, exclusions):
    def edit(p, wires):
        _DS(p).update(fit_status=value, exclusions=exclusions, gaps=[])
    return edit


def _dag_fit(value, exclusions):
    def edit(p, wires):
        _DG(p).update(fit_status=value, exclusions=exclusions, gaps=[])
    return edit


def _flip_verdict(getter, key):
    return _set(getter, key, lambda v: "FAVORABLE" if v != "FAVORABLE" else "UNFAVORABLE")


def _strip_envelope(p, wires):
    from smartchem.conditions import ConditionEnvelope
    _ST(p)["envelope"] = svc._condition_envelope_to_payload(ConditionEnvelope.unknown())


def _reforge_routes(resp, routes):
    """The COHERENT keyless forger (Wave C6 masters' ``reforge_routes``): re-rank forged routes with the producer's OWN
    helpers and rebuild every dependent field -- dossiers, frontier, IR candidates, receipt count, diagnostics -- so the
    only law left to refuse a forged replayed step is the step's own (X-high D29.3)."""
    req = resp.request
    ranked = svc._ranked_summaries(tuple(routes), req.constraints.bounds, resp.identity_losses,
                                   process=req.constraints.process, capability_profile=req.capability_profile)
    frontier = svc._route_frontier(req, tuple(routes), ranked)
    ir = resp.compilation_ir
    cands = tuple(sorted((cir.CandidateSummary(cir.CANDIDATE_SUMMARY_SCHEMA, "ROUTE", r.route_digest, r.equation,
                                               "FORMAL_CANDIDATE") for r in ranked), key=lambda c: c.candidate_digest))
    ir2 = dc.replace(ir, candidates=cands, search_receipt=dc.replace(ir.search_receipt, results_returned=len(cands)))
    note = svc.constraint_note(req.constraints.bounds, fit_counts=svc._fit_counts(ranked) if ranked else None,
                               process=req.constraints.process)
    diags = tuple(ir2.diagnostics) + ((note,) if note is not None else ())
    return dc.replace(resp, compilation_ir=ir2, ranked_route_dossiers=ranked, affordability_frontier=frontier,
                      diagnostics=diags)


def _replay_rebind(world, route_index, mutate):
    """A keyless forgery of replayed steps, made coherent everywhere else (``_reforge_routes``): decode the honest
    ``world``, replace the steps of its ``route_index``-th ranked route with ``mutate(steps)`` (every corpus envelope
    re-looked-up, so D27.1 is honest too), and re-serialize through the public codec."""
    from smartchem.experiment import routes as _routes
    from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute

    def edit(p, wires):
        resp = svc.response_from_payload(copy.deepcopy(wires[world]))
        routes = [svc._reconstruct_route(d.replay_payload) for d in resp.ranked_route_dossiers]
        steps = tuple(dc.replace(st, envelope=_routes._conditions_for(svc._ReplayedTransform(st)))
                      for st in mutate(routes[route_index].steps))
        routes[route_index] = ExperimentRoute(ROUTE_SCHEMA, steps)
        p.clear()
        p.update(svc.response_to_payload(_reforge_routes(resp, routes), include_replay=True))
    return edit


def _at(index, mutate):
    return lambda steps: tuple(mutate(st) if i == index else st for i, st in enumerate(steps))


def _swap(molecules, formula_of, smiles):
    """``molecules`` with its (first) member of element counts ``formula_of`` replaced by the isomer ``smiles``."""
    from smartchem.smiles import parse_smiles
    out, done = [], False
    for m in molecules:
        if not done and m.formula == formula_of:
            out.append(parse_smiles(smiles).canonical())
            done = True
        else:
            out.append(m)
    assert done, f"setup: no {formula_of} to swap"
    return tuple(out)


_C2H4O2 = {"C": 2, "H": 4, "O": 2}


def _swap_intermediate(steps):
    """Route 1's intermediate C2H4O2 (made by step 1, consumed by step 2) swapped for its isomer glycolaldehyde in BOTH
    places: the chain, the final target and every leaf stay honest (so D26.1 passes) -- only D29.1 can see it."""
    make, use = steps
    return (dc.replace(make, target=_swap((make.target,), _C2H4O2, "OCC=O")[0],
                       products=_swap(make.products, _C2H4O2, "OCC=O")),
            dc.replace(use, reactants=_swap(use.reactants, _C2H4O2, "OCC=O")))


_FORGERIES = {
    # -- the response ------------------------------------------------------------------------------------------------
    "CompilationResponse.schema_version": ("routes", _set(lambda p: p, "schema_version",
                                                          f"smartchem.service/compilation-response-v1alpha{_BUMP}")),
    "CompilationResponse.request": ("routes", _bump_bound("max_results")),
    "CompilationResponse.outcome": ("routes", _set(lambda p: p, "outcome", "NO_ROUTE_COMPLETE")),
    "CompilationResponse.standard_status": ("routes", _set(lambda p: p, "standard_status", lambda v: (  # a VALID 8.2 name
        "INCOMPLETE_RESULT_LIMIT" if v != "INCOMPLETE_RESULT_LIMIT" else "INCOMPLETE_DEPTH_LIMIT"))),
    "CompilationResponse.compilation_ir": ("routes", _set(_IR, "request_digest", "0" * 64)),
    "CompilationResponse.diagnostics": ("routes", lambda p, w: p["diagnostics"].append("forged: 3 route(s) FIT")),
    "CompilationResponse.ranked_route_dossiers": ("routes", lambda p, w: p["ranked_route_dossiers"].reverse()),
    "CompilationResponse.affordability_frontier": ("mesal", lambda p, w: p["affordability_frontier"].pop()),
    "CompilationResponse.ranked_dag_dossiers": ("dag", lambda p, w: p["ranked_dag_dossiers"].reverse()),
    # -- the derived wire keys (edited AND left edited: the forger's point is the label) -----------------------------
    **{f"CompilationResponse.wire.{key}": ("routes", _set(lambda p: p, key, _FORGED_WIRE_VALUES[key]))
       for key in ("exit_code", "process_selection_status", "admissible_route_digests", "search_space_status",
                   "capability_question_digest")},
    "CompilationResponse.wire.result_digest": ("routes", _set(lambda p: p, "result_digest",
                                                              lambda v: ("1" if v[0] != "1" else "2") + v[1:])),
    # -- a route dossier (the corpus-evidenced methyl-salicylate route) ---------------------------------------------
    "RankedRouteSummary.schema_version": ("mesal", _set(_DS, "schema_version",
                                                        f"smartchem.service/ranked-route-summary-v1alpha{_BUMP}")),
    "RankedRouteSummary.route_digest": ("mesal", _set(_DS, "route_digest", "0" * 64)),
    "RankedRouteSummary.equation": ("mesal", _set(_DS, "equation", lambda v: v + " ")),
    "RankedRouteSummary.fit_status": ("mesal", _fit("FITS", [])),
    "RankedRouteSummary.readiness": ("mesal", _promote_readiness),
    "RankedRouteSummary.exclusions": ("mesal", _fit("EXCLUDED", ["forged: outside a hard bound"])),
    "RankedRouteSummary.gaps": ("mesal", lambda p, w: _DS(p)["gaps"].append("forged gap")),
    **{f"RankedRouteSummary.{key}": ("mesal", _flip_verdict(_DS, key))
       for key in ("composability_verdict", "selectivity_verdict", "feasibility_verdict", "equilibrium_verdict",
                   "kinetics_verdict")},
    "RankedRouteSummary.process_requirements": ("mesal", _set(_DS, "process_requirements",
                                                              lambda v: [None] * len(v))),
    "RankedRouteSummary.replay_payload": ("mesal", lambda p, w: _DS(p).pop("replay_payload")),
    "RankedRouteSummary.capability_assessment": ("mesal", _set(_DS, "capability_assessment", None)),
    "RankedRouteSummary.wire.readiness_tier": ("mesal", _set(_DS, "readiness_tier", lambda v: (
        "FORMAL_CANDIDATE" if v != "FORMAL_CANDIDATE" else "REACTION_VOUCHED"))),
    # -- a DAG dossier ------------------------------------------------------------------------------------------------
    "RankedDAGSummary.schema_version": ("dag", _set(_DG, "schema_version",
                                                    f"smartchem.service/ranked-dag-summary-v1alpha{_BUMP}")),
    "RankedDAGSummary.route_digest": ("dag", _set(_DG, "route_digest", "0" * 64)),
    "RankedDAGSummary.equation": ("dag", _set(_DG, "equation", lambda v: v + " ")),
    "RankedDAGSummary.fit_status": ("dag", _dag_fit("FITS", [])),
    "RankedDAGSummary.exclusions": ("dag", _dag_fit("EXCLUDED", ["forged: outside a hard bound"])),
    "RankedDAGSummary.gaps": ("dag", lambda p, w: _DG(p)["gaps"].append("forged gap")),
    "RankedDAGSummary.process_requirements": ("dag", lambda p, w: _DG(p).__setitem__(  # a transplanted SOURCED record
        "process_requirements", [copy.deepcopy(_DS(w["mesal"])["process_requirements"][0])]
        * len(_DG(p)["process_requirements"]))),
    "RankedDAGSummary.edges": ("dag", _set(_DGE, "edges", lambda v: [[b, a] for a, b in v])),
    **{f"RankedDAGSummary.{key}": ("dag", _flip_verdict(_DG, key))
       for key in ("composability_verdict", "selectivity_verdict", "feasibility_verdict", "equilibrium_verdict",
                   "kinetics_verdict")},
    "RankedDAGSummary.serial_holds": ("dag", lambda p, w: _DGE(p)["serial_holds"].append([0, 2, 99999.0])),
    "RankedDAGSummary.replay_payload": ("dag", lambda p, w: _DG(p).pop("replay_payload")),
    # -- the IR -------------------------------------------------------------------------------------------------------
    "ChemicalCompilationIR.schema_version": ("routes", _set(_IR, "schema_version", lambda v: v + _BUMP)),
    "ChemicalCompilationIR.operation": ("routes", _set(_IR, "operation", "DECOMPILE")),
    "ChemicalCompilationIR.target": ("routes", lambda p, w: (  # a CONSISTENT swap: the receipt's target digest moves too
        _IR(p).__setitem__("target", copy.deepcopy(w["mesal"]["compilation_ir"]["target"])),
        _RC(p).__setitem__("target_identity_digest", w["mesal"]["compilation_ir"]["target"]["identity_digest"]))),
    "ChemicalCompilationIR.request_digest": ("routes", _set(_IR, "request_digest", "0" * 64)),
    "ChemicalCompilationIR.identity_losses": ("stereo", _set(_IR, "identity_losses", [])),
    "ChemicalCompilationIR.terminal_policy_digest": ("routes", lambda p, w: (
        _IR(p).__setitem__("terminal_policy_digest", "0" * 64), _RC(p).__setitem__("terminal_policy_digest", "0" * 64))),
    "ChemicalCompilationIR.transform_registry_digest": ("routes", lambda p, w: (
        _IR(p).__setitem__("transform_registry_digest", "0" * 64),
        _RC(p).__setitem__("transform_registry_digest", "0" * 64))),
    "ChemicalCompilationIR.search_receipt": ("routes", lambda p, w: _IR(p).__setitem__(
        "search_receipt", copy.deepcopy(w["dag"]["compilation_ir"]["search_receipt"]))),
    "ChemicalCompilationIR.diagnostics": ("routes", lambda p, w: (
        _IR(p)["diagnostics"].insert(0, "forged: 1 FIT; CAPABILITY_FIT under poor-man"),
        p["diagnostics"].insert(0, "forged: 1 FIT; CAPABILITY_FIT under poor-man"))),
    # -- the search receipt -------------------------------------------------------------------------------------------
    "Section81ReceiptView.schema_version": ("routes", _set(_RC, "schema_version", lambda v: v + _BUMP)),
    "Section81ReceiptView.search_kind": ("routes", _set(_RC, "search_kind", "CONVERGENT_DAG")),
    "Section81ReceiptView.cut_budget_scope": ("routes", _set(_RC, "cut_budget_scope", "GLOBAL")),
    "Section81ReceiptView.target_identity_digest": ("routes", _set(_RC, "target_identity_digest", None)),
    "Section81ReceiptView.terminal_policy_digest": ("routes", _set(_RC, "terminal_policy_digest", None)),
    "Section81ReceiptView.transform_registry_digest": ("decompile", _set(_RC, "transform_registry_digest", None)),
    "Section81ReceiptView.max_depth": ("routes", _set(_RC, "max_depth", lambda v: v + 1)),
    "Section81ReceiptView.cut_budget": ("routes", _set(_RC, "cut_budget", lambda v: v + 1)),
    "Section81ReceiptView.candidate_limit": ("routes", _set(_RC, "candidate_limit", 5)),
    "Section81ReceiptView.result_limit": ("routes", _set(_RC, "result_limit", lambda v: v + 1)),
    "Section81ReceiptView.results_returned": ("routes", _set(_RC, "results_returned", None)),
    # -- a candidate --------------------------------------------------------------------------------------------------
    "CandidateSummary.schema_version": ("routes", _set(_CAND, "schema_version", lambda v: v + _BUMP)),
    "CandidateSummary.candidate_kind": ("routes", _set(_CAND, "candidate_kind", "DAG")),
    "CandidateSummary.candidate_digest": ("routes", _set(_CAND, "candidate_digest", "0" * 64)),
    "CandidateSummary.equation": ("routes", _set(_CAND, "equation", "forged: CAPABILITY_FIT")),
    "CandidateSummary.readiness_tier": ("routes", _set(_CAND, "readiness_tier", "PROCESS_SPECIFIED")),
    # -- a replayed step ----------------------------------------------------------------------------------------------
    "replay_step.schema_version": ("mesal", _set(_ST, "schema_version", lambda v: v + _BUMP)),
    "replay_step.envelope": ("mesal", _strip_envelope),
    # X-high D29.1 / D29.3: COHERENT forgeries -- every dependent field (dossiers, frontier, candidates, receipt count,
    # diagnostics, envelopes) re-derived by the producer's own helpers, the final target and every leaf the request's,
    # so D29.1 is the ONLY law left.  routes: route 1 = "CH2O2 + CH4O -> C2H4O2 + H2O ; CH4O + C2H4O2 -> C3H6O2 + H2O",
    # route 2 step 2 = "C2H4O3 + C3H6O -> C3H6O2 + C2H4O2"; isomer: route 0 = "CH4O + C2H4O2 -> C3H6O2 + H2O".
    "replay_step.products": ("routes", _replay_rebind("routes", 2, _at(1, lambda st: dc.replace(  # Wave C6 C6-F8:
        st, products=_swap(st.products, _C2H4O2, "COC=O"))))),                   # the byproduct's isomer
    "replay_step.reactants": ("isomer", _replay_rebind("isomer", 0, _at(0, lambda st: dc.replace(
        st, reactants=_swap(st.reactants, _C2H4O2, "OCC=O"))))),                 # a DECLARED leaf isomer
    "replay_step.target": ("routes", _replay_rebind("routes", 1, _swap_intermediate)),  # an intermediate's isomer
    "replay_step.reagents": ("routes", _replay_rebind("routes", 0, _at(0, lambda st: dc.replace(
        st, reagents=(st.reactants[0],))))),                                     # an ancillary-reagent flag
    "replay_step.reaction_center": ("routes", _replay_rebind("routes", 0, _at(0, lambda st: dc.replace(
        st, reaction_center=None)))),                                            # a re-centre (Foreman N4)
}

#: X-high D29.3 (Wave C6 C6-test): the law each forgery must be refused BY.  A refusal by some OTHER law proves only that
#: the forgery is refused, not that the entry's own claim holds -- pre-D28.1 the envelope forgery was caught by readiness
#: coherence, so the sweep could not see a D28.1 regression.  Two locks: the refusal message carries the law's tag (its
#: ``(D2x.y)`` tag; the few pre-D24 guards that carry none are pinned by their exact wording), and the DEEPEST ledger-named
#: frame of the raising traceback is one of the checks the entry itself names (``_refused_in``).
_D274, _D261, _D277, _D276, _D283 = r"\(D27\.4\)", r"\(D26\.1\)", r"\(D27\.7\)", r"\(D27\.6\)", r"\(D28\.3\)"
_OWN_LAW = {
    "CompilationResponse.schema_version": r"unsupported response schema_version",
    "CompilationResponse.request": _D276,
    "CompilationResponse.outcome": r"NO_ROUTE_COMPLETE requires a complete-within-bounds IR",
    "CompilationResponse.standard_status": r"must equal the wrapped IR's standard_status",
    "CompilationResponse.compilation_ir": _D261,
    "CompilationResponse.diagnostics": _D274,
    "CompilationResponse.ranked_route_dossiers": _D274,
    "CompilationResponse.affordability_frontier": _D274,
    "CompilationResponse.ranked_dag_dossiers": _D274,
    **{f"CompilationResponse.wire.{key}": rf"^{key} does not match the reconstructed response"
       for key in ("exit_code", "process_selection_status", "admissible_route_digests", "search_space_status",
                   "capability_question_digest", "result_digest")},
    "RankedRouteSummary.schema_version": r"unsupported ranked route summary schema_version",
    "RankedRouteSummary.route_digest": r"ranked route digest must identify a returned IR candidate",
    "RankedRouteSummary.equation": _D277,
    "RankedRouteSummary.readiness": r"claims a readiness .* its replayed evidence does not support",
    "RankedRouteSummary.replay_payload": _D277,
    "RankedRouteSummary.capability_assessment": r"\(0\.9 D12\)",
    "RankedRouteSummary.wire.readiness_tier": r"disagrees with its own carried readiness ladder",
    **{f"RankedRouteSummary.{key}": _D274
       for key in ("fit_status", "exclusions", "gaps", "composability_verdict", "selectivity_verdict",
                   "feasibility_verdict", "equilibrium_verdict", "kinetics_verdict", "process_requirements")},
    "RankedDAGSummary.schema_version": r"unsupported ranked DAG summary schema_version",
    "RankedDAGSummary.route_digest": r"ranked DAG digest must identify a returned IR candidate",
    "RankedDAGSummary.equation": _D277,
    "RankedDAGSummary.fit_status": r"a forged or inconsistent DAG process admission",
    "RankedDAGSummary.edges": r"a DAG must have exactly one sink",
    "RankedDAGSummary.replay_payload": _D277,
    **{f"RankedDAGSummary.{key}": _D274
       for key in ("exclusions", "gaps", "composability_verdict", "selectivity_verdict", "feasibility_verdict",
                   "equilibrium_verdict", "kinetics_verdict", "serial_holds", "process_requirements")},
    "ChemicalCompilationIR.schema_version": r"schema_version must be exactly '[^']*chemical-compilation-ir-",
    "ChemicalCompilationIR.operation": _D261,
    "ChemicalCompilationIR.target": _D261,
    "ChemicalCompilationIR.request_digest": _D261,
    "ChemicalCompilationIR.identity_losses": r"\(D24\.11\)",
    "ChemicalCompilationIR.terminal_policy_digest": _D261,
    "ChemicalCompilationIR.transform_registry_digest": r"algebra-rebind mismatch on load",
    "ChemicalCompilationIR.search_receipt": r"^search_receipt\.\w+ .* must equal the IR's",
    "ChemicalCompilationIR.diagnostics": r"\(D28\.2\)",
    "Section81ReceiptView.schema_version": r"schema_version must be exactly '[^']*search-receipt-view-",
    **{f"Section81ReceiptView.{key}": _D276 for key in ("search_kind", "cut_budget_scope", "max_depth", "cut_budget",
                                                        "result_limit")},
    **{f"Section81ReceiptView.{key}": _D283
       for key in ("target_identity_digest", "terminal_policy_digest", "transform_registry_digest", "results_returned")},
    "Section81ReceiptView.candidate_limit": r"candidate_limit must be None",
    "CandidateSummary.schema_version": r"schema_version must be exactly '[^']*candidate-summary-",
    "CandidateSummary.candidate_kind": r"\(D24\.14\)",
    "CandidateSummary.candidate_digest": r"ranked route digest must identify a returned IR candidate",
    "CandidateSummary.equation": _D277,
    "CandidateSummary.readiness_tier": r"an IR CandidateSummary is a FORMAL_CANDIDATE",
    "replay_step.schema_version": r"schema_version must be exactly '[^']*/step-v1'",
    "replay_step.envelope": r"\(D28\.1\)",
    **{f"replay_step.{key}": r"\(D29\.1\)" for key in ("target", "reactants", "products", "reagents", "reaction_center")},
}

_ALL_CHECKS = frozenset(c for entries in TRANSPORT_LEDGER.values() for e in entries.values() for c in e.checks)


def _refused_in(exc):
    """The DEEPEST frame of ``exc``'s traceback that is a ledger-named check (``"module:qualname"``), or None."""
    hit, tb = None, exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        name = f"{frame.f_globals.get('__name__')}:{frame.f_code.co_qualname}"
        hit = name if name in _ALL_CHECKS else hit
        tb = tb.tb_next
    return hit


def test_every_forgery_names_its_own_law():
    assert set(_OWN_LAW) == set(_FORGERIES), (
        f"forgeries with no own law: {sorted(set(_FORGERIES) - set(_OWN_LAW))}; "
        f"stale own-law rows: {sorted(set(_OWN_LAW) - set(_FORGERIES))}")


def test_every_non_advisory_ledger_entry_names_a_keyless_forgery():
    """A RE_DERIVED / BOUND / FROZEN label is a CLAIM the loader refuses a forgery of -- so every one needs its forgery
    below (D28.6); a new label added without one fails here, before it can over-claim silently."""
    labelled = {f"{table}.{field}" for table, entries in TRANSPORT_LEDGER.items() for field, entry in entries.items()
                if entry.status is not TransportStatus.DIGEST_ONLY_ADVISORY}
    assert set(_FORGERIES) == labelled, (
        f"non-advisory entries with NO forgery: {sorted(labelled - set(_FORGERIES))}; forgeries for entries that are not "
        f"(or no longer) re-derived/bound/frozen: {sorted(set(_FORGERIES) - labelled)}")


@pytest.mark.parametrize("entry", sorted(_FORGERIES))
def test_every_non_advisory_ledger_entry_refuses_its_keyless_forgery(worlds, entry):
    world, edit = _FORGERIES[entry]
    honest_wire = worlds[world]
    forged = copy.deepcopy(honest_wire)
    edit(forged, worlds)
    assert forged != honest_wire, f"{entry}: the forgery changed nothing (a vacuous test)"
    table, _, field = entry.rpartition(".")
    keep = frozenset({field}) if table == "CompilationResponse.wire" else frozenset()
    with pytest.raises((ValueError, TypeError, KeyError)) as refusal:
        _reforge(forged, keep=keep)  # the loader's own constructor call (a record guard or a coherence law) ...
        svc.response_from_payload(forged)  # ... else the load
    message = str(refusal.value)
    if field != "result_digest":
        assert "result_digest does not match" not in message, (
            f"{entry}: refused only by a stale PUBLIC digest, not by the entry's own law -- the forger recomputes that")
    # X-high D29.3: refused BY its own law, never merely by some law.
    assert re.search(_OWN_LAW[entry], message), f"{entry}: refused by another law, not its own: {message[:300]}"
    assert _refused_in(refusal.value) in TRANSPORT_LEDGER[table][field].checks, (
        f"{entry}: raised in {_refused_in(refusal.value)}, which is not one of the entry's own checks "
        f"{TRANSPORT_LEDGER[table][field].checks}")


def test_the_disclosed_partial_advisory_case_really_loads(worlds, honest):
    """The other direction (the ledger does not UNDER-claim either): an unconstrained convergent-DAG search's candidate has
    no dossier, so its equation text is advisory -- a keyless edit of it LOADS (D28.4 discloses exactly this)."""
    unconstrained = svc.run_compilation(svc.build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, grammar=svc.TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        helper_reagents=("water", "acetic acid")))
    wire = svc.response_to_payload(unconstrained)
    assert wire["compilation_ir"]["candidates"] and not wire["ranked_dag_dossiers"], "setup: dossier-less DAG candidates"
    wire["compilation_ir"]["candidates"][0]["equation"] = "forged text (advisory: no dossier to re-derive it from)"
    svc.response_from_payload(_reforge(wire))
