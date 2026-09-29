"""X-high D27.8 -- the machine-checked TRANSPORT LEDGER of the compilation-response wire.

Every dataclass field of :class:`~smartchem.service.CompilationResponse`, :class:`~smartchem.service.RankedRouteSummary`,
:class:`~smartchem.service.RankedDAGSummary`, :class:`~smartchem.compilation_ir.ChemicalCompilationIR`, its
:class:`~smartchem.compilation_ir.Section81ReceiptView` and :class:`~smartchem.compilation_ir.CandidateSummary`, every
derived wire-only key, and every key of a replayed step carries EXACTLY ONE status.  The status is stated for a KEYLESS
consumer of a CURRENT (0.9) response on the CANONICAL_VERIFIED wire under a plain or verified-admission load
(``response_from_payload`` without ``verification_key`` / ``require_reexecution``):

``RE_DERIVED_ON_LOAD``
    recomputed on load from OTHER carried evidence (the replay, the IR, the request) by the named check; a carried
    value that disagrees is refused.  Trusted exactly as far as the evidence it is re-derived from.
``BOUND_TO_REQUEST``
    must equal what the named check derives from the carried REQUEST -- trusted as far as the request, which the
    consumer binds with ``expected_request_digest`` / ``expected_capability_question_digest``.
``DIGEST_ONLY_ADVISORY``
    nothing re-derives or binds it: only the whole-body wire digest covers it (D27.2), and a keyless forger recomputes
    that public digest.  ADVISORY to a keyless consumer; authenticated by the producer HMAC and (caller-attached
    ``provider_snapshots`` aside) by ``require_reexecution``.
``LEGACY_FROZEN``
    a released-generation constant: the value must equal the codec's fixed id / constant (the current one, or the one
    whitelisted v0.8 id that dispatches the FROZEN v0.8 rule); it carries no answer content to re-derive.

A container field (the IR, the receipt, a tuple of dossiers, a replay) is classified by its CONTAINER-level law
(membership, order, count, request binding); each member record's fields have their own table.  ``thin`` records the
status on the THIN_ADVISORY wire where it is weaker (no replay -> nothing replay-based to re-derive from).  LEGACY v0.8
payloads: every D27 replay-based re-derivation is skipped (the ranking, frontier and diagnostics are v0.8's code's) and
corpus evidence is re-derived only under verified admission -- recompile under 0.9 for the table below.

``advisory_when`` (X-high D28.4) names the CASES in which an otherwise re-derived / bound entry is advisory after all
(a candidate with no dossier has nothing to re-derive its label from) -- stated in the entry, not buried in a note, so
the service docstring's "Partially advisory" sentence is machine-checked against it too.

``tests/test_transport_ledger.py`` machine-checks the ledger: every field / wire key has exactly one entry (no missing,
no stale), every named check resolves to real code, every advisory (and partially advisory) entry is named in the
service module's docstring paragraph for keyless consumers, and -- X-high D28.6 -- every RE_DERIVED_ON_LOAD,
BOUND_TO_REQUEST and LEGACY_FROZEN entry has a keyless single-field forgery (every public digest recomputed) that the
loader REFUSES: a label with no refusing forgery fails the test, so the ledger can no longer over-claim silently (the
Wave C5 audit found four such mislabels).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TransportStatus(str, Enum):
    RE_DERIVED_ON_LOAD = "RE_DERIVED_ON_LOAD"
    BOUND_TO_REQUEST = "BOUND_TO_REQUEST"
    DIGEST_ONLY_ADVISORY = "DIGEST_ONLY_ADVISORY"
    LEGACY_FROZEN = "LEGACY_FROZEN"


@dataclass(frozen=True)
class LedgerEntry:
    """One field's transport status.  ``checks`` name the enforcing code as ``"module:qualname"`` (empty for an
    advisory field); ``thin`` is the weaker status on the THIN_ADVISORY wire, ``None`` when the same."""

    status: TransportStatus
    checks: tuple[str, ...] = ()
    note: str = ""
    thin: TransportStatus | None = None
    advisory_when: str = ""

    def __post_init__(self) -> None:
        if (self.status is TransportStatus.DIGEST_ONLY_ADVISORY) != (not self.checks):
            raise ValueError("an advisory entry names no check, and every other entry names the check enforcing it")
        if self.advisory_when and self.status is TransportStatus.DIGEST_ONLY_ADVISORY:
            raise ValueError("advisory_when qualifies a re-derived / bound entry; an advisory entry is advisory always")


RE, REQ, ADV, FROZEN = (TransportStatus.RE_DERIVED_ON_LOAD, TransportStatus.BOUND_TO_REQUEST,
                        TransportStatus.DIGEST_ONLY_ADVISORY, TransportStatus.LEGACY_FROZEN)

_S = "smartchem.service:"
_IR = "smartchem.compilation_ir:"
_LOAD = _S + "response_from_payload"
_POST = _S + "CompilationResponse.__post_init__"
_OUTCOME = _S + "CompilationResponse._check_outcome_coherence"
_ANSWER = _S + "CompilationResponse._check_request_answer_coherence"            # D26.1 / D27.3 / D27.6 / D27.7
_RANKING = _S + "CompilationResponse._check_ranking_coherence"                  # D27.4
_CORPUS = _S + "CompilationResponse._check_corpus_evidence_coherence"           # D27.1
_TRANSFORMS = _S + "CompilationResponse._check_replay_step_transforms"          # D29.1
_DAG_EDGES = _S + "_validate_dag_edges"                                         # a DAG's own structure guard
_COMPLETE = _S + "CompilationResponse._check_dossier_completeness"              # D24.14 / D25.3 / D27.5
_BOUNDS = _S + "CompilationResponse._check_receipt_bounds"                      # D27.6
_READINESS = _S + "CompilationResponse._check_readiness_coherence"
_CAPABILITY = _S + "CompilationResponse._check_capability_coherence"
_FRONTIER = _S + "CompilationResponse._check_frontier_coherence"
_LOSSES = _S + "CompilationResponse._check_identity_loss_coherence"             # D24.11
_PROCESS = _S + "CompilationResponse._check_process_admission_coherence"
_DAG_PROCESS = _S + "CompilationResponse._check_dag_process_admission_coherence"
_IR_POST = _IR + "ChemicalCompilationIR.__post_init__"
_RECEIPT_POST = _IR + "Section81ReceiptView.__post_init__"
_CANDIDATE_POST = _IR + "CandidateSummary.__post_init__"

_CONSISTENT_REWRITE = ("0.9.5 S11: a function of the ADVISORY IR search status / candidate set -- a single-field relabel is "
                       "refused, but a CONSISTENT rewrite of what the search found (the D25.3 boundary) moves it with "
                       "them; only require_reexecution or the producer HMAC closes that")
_THIN_VERDICT = ("thin: no replay, so only the process axis (PROCESS-ADMIT-01) is re-derived; PROCESS_SPECIFIED and "
                 "CAPABILITY_FIT are refused on a thin wire, and verified admission fail-closes above-FORMAL claims")
_SEARCH_OUTPUT = ("search output: a CONSISTENT rewrite (the D25.3 boundary; ATK5d's INCOMPLETE->COMPLETE flip) is "
                  "re-execution / HMAC only")
_NO_DOSSIER = ("a candidate with NO dossier -- a decompile's FORMULA_EDGE candidates and an UNCONSTRAINED convergent-DAG "
               "search's DAG candidates (no bench box, so no DAG is judged) -- has nothing to re-derive it from (D28.4, "
               "Wave C5 C5-F5)")
_LEGACY_VA = "; a LEGACY v0.8 step is checked under verified admission only (plain = advisory, exactly as D27.1)"


def _route_verdict(note: str = "") -> LedgerEntry:
    return LedgerEntry(RE, (_RANKING,), note or "the whole summary is re-derived from its replayed route (D27.4)",
                       thin=ADV)


def _dag_verdict(note: str = "") -> LedgerEntry:
    return LedgerEntry(RE, (_RANKING, _DAG_PROCESS),
                       note or "re-derived whole by ranked_dag_dossiers over the replayed DAGs (D27.4)", thin=ADV)


TRANSPORT_LEDGER: dict[str, dict[str, LedgerEntry]] = {
    "CompilationResponse": {
        "schema_version": LedgerEntry(FROZEN, (_LOAD, _POST),
                                      "dispatch: the current id, or the whitelisted v0.8 id (frozen v0.8 rule, D11)"),
        "request": LedgerEntry(REQ, (_LOAD, _ANSWER, _BOUNDS), "the anchor every BOUND_TO_REQUEST row derives from; an "
                               "edited request no longer matches the IR / receipt it carries (D26.1, D27.6); bound to the "
                               "consumer's question only by expected_request_digest / expected_capability_question_"
                               "digest (unpinned, the D26.1 binds say only 'the answer answers THIS request')"),
        "outcome": LedgerEntry(RE, (_OUTCOME, _ANSWER), "the producer's _classify of the IR under the request's "
                               "availability (D27.3)", advisory_when=_CONSISTENT_REWRITE),
        "standard_status": LedgerEntry(RE, (_OUTCOME,), "== the IR's standard_status (itself advisory search output)",
                                       advisory_when=_CONSISTENT_REWRITE),
        "compilation_ir": LedgerEntry(REQ, (_ANSWER, _LOSSES), "container law: the IR answers the carried request "
                                      "(D26.1); members in the ChemicalCompilationIR table"),
        "diagnostics": LedgerEntry(RE, (_RANKING, _ANSWER), "== the IR's diagnostics (themselves re-derived, D28.2) + "
                                   "the producer's constraint / DAG-bench notes (D27.4)", thin=ADV,
                                   advisory_when="a decompile's incompleteness line is its receipt's own stop_reason "
                                                 "(advisory search output)"),
        "ranked_route_dossiers": LedgerEntry(RE, (_COMPLETE, _RANKING), "set == the IR's route candidates (D24.14); "
                                             "order and every member re-derived (D27.4)", thin=ADV),
        "affordability_frontier": LedgerEntry(RE, (_RANKING, _POST, _FRONTIER), "== _route_frontier over the replayed "
                                              "routes (D27.4); thin keeps only the hard-blocker channel", thin=ADV),
        "provider_snapshots": LedgerEntry(ADV, note="caller-attached dated provenance: HMAC only (re-execution cannot "
                                          "reproduce a fetch time)"),
        "parse_receipt_summary": LedgerEntry(ADV, note="provenance of how the request was READ (outside the result "
                                             "identity, SVC-REQ-01); HMAC + re-execution"),
        "ranked_dag_dossiers": LedgerEntry(RE, (_COMPLETE, _RANKING), "set == the IR's DAG candidates iff the box "
                                           "constrains (D24.14); order and members re-derived (D27.4)", thin=ADV),
    },
    "CompilationResponse.wire": {
        "exit_code": LedgerEntry(RE, (_LOAD,), "round-trip: == the reconstructed response's",
                                 advisory_when=_CONSISTENT_REWRITE),
        "process_selection_status": LedgerEntry(RE, (_LOAD,), "round-trip: == the reconstructed response's"),
        "admissible_route_digests": LedgerEntry(RE, (_LOAD,), "round-trip: == the reconstructed response's"),
        "search_space_status": LedgerEntry(RE, (_LOAD,), "round-trip: == the reconstructed response's (D27.8)",
                                           advisory_when=_CONSISTENT_REWRITE),
        "capability_question_digest": LedgerEntry(REQ, (_LOAD,), "== the reconstructed request's question pin"),
        "result_digest": LedgerEntry(RE, (_LOAD,), "the whole-body wire digest (D27.2)"),
        "transport_mode": LedgerEntry(ADV, note="self-declared; a downgrade relabel only WEAKENS what is re-derived "
                                      "(thin = advisory) -- a consumer that needs the canonical guarantees loads with "
                                      "VerificationPolicy(require_canonical_transport=True), which refuses THIN (and "
                                      "legacy) at dispatch (0.9.5 S1)"),
        "producer_signature": LedgerEntry(ADV, note="the authenticator itself (outside the digest); meaningless "
                                          "without the verification key"),
    },
    "RankedRouteSummary": {
        "schema_version": LedgerEntry(FROZEN, (_S + "ranked_summary_from_payload", _POST)),
        "route_digest": LedgerEntry(RE, (_RANKING, _POST), "the replayed route's digest (D27.4); an IR candidate "
                                    "(__post_init__)", thin=ADV),
        "equation": LedgerEntry(RE, (_ANSWER, _RANKING), "the replayed route's own rendering (D26.1)", thin=ADV),
        "fit_status": LedgerEntry(RE, (_RANKING, _PROCESS), "under the CARRIED request's box (D27.4, Foreman N3)",
                                  thin=ADV),
        "readiness": LedgerEntry(RE, (_READINESS, _RANKING), _THIN_VERDICT, thin=ADV),
        "exclusions": _route_verdict(),
        "gaps": _route_verdict(),
        "composability_verdict": _route_verdict(),
        "selectivity_verdict": _route_verdict(),
        "feasibility_verdict": _route_verdict(),
        "equilibrium_verdict": _route_verdict(),
        "kinetics_verdict": _route_verdict(),
        "process_requirements": _route_verdict("from the replayed steps' corpus envelopes (D27.1 + D27.4)"),
        "replay_payload": LedgerEntry(REQ, (_ANSWER, _LOAD), "container law: makes the requested target from the "
                                      "declared terminals within max_depth (D26.1, D27.6); mandatory on the canonical "
                                      "wire (D27.7); absent on thin; members in the replay_step table"),
        "capability_assessment": LedgerEntry(RE, (_CAPABILITY, _RANKING), _THIN_VERDICT, thin=ADV),
    },
    "RankedRouteSummary.wire": {
        "readiness_tier": LedgerEntry(RE, (_S + "ranked_summary_from_payload",), "== the carried readiness's tier"),
    },
    "RankedDAGSummary": {
        "schema_version": LedgerEntry(FROZEN, (_S + "ranked_dag_summary_from_payload", _POST)),
        "route_digest": LedgerEntry(RE, (_RANKING, _DAG_PROCESS, _POST), "re-derived whole by ranked_dag_dossiers over "
                                    "the replayed DAGs (D27.4); an IR candidate (__post_init__)", thin=ADV),
        "equation": LedgerEntry(RE, (_ANSWER, _RANKING), "the replayed DAG's own rendering (D26.1)", thin=ADV),
        "fit_status": _dag_verdict(),
        "exclusions": _dag_verdict(),
        "gaps": _dag_verdict(),
        "process_requirements": _dag_verdict(),
        "edges": LedgerEntry(RE, (_RANKING, _DAG_PROCESS, _DAG_EDGES), "re-derived whole by ranked_dag_dossiers over "
                             "the replayed DAGs (D27.4); a malformed edge set fails the DAG's own structure guard",
                             thin=ADV),
        "composability_verdict": _dag_verdict(),
        "selectivity_verdict": _dag_verdict(),
        "feasibility_verdict": _dag_verdict(),
        "equilibrium_verdict": _dag_verdict(),
        "kinetics_verdict": _dag_verdict(),
        "serial_holds": _dag_verdict("compare=False, so compared EXPLICITLY on load (D27.4, C4T-8)"),
        "replay_payload": LedgerEntry(REQ, (_ANSWER, _LOAD), "container law: makes the requested target from the "
                                      "declared terminals (D26.1); mandatory on the canonical wire (D27.7)"),
    },
    "ChemicalCompilationIR": {
        "schema_version": LedgerEntry(FROZEN, (_IR + "ir_from_payload", _IR_POST)),
        "tool_version": LedgerEntry(ADV, note="a producer-version label (any non-empty string)"),
        "operation": LedgerEntry(REQ, (_ANSWER,)),
        "target": LedgerEntry(REQ, (_ANSWER,)),
        "request_digest": LedgerEntry(REQ, (_ANSWER,)),
        "identity_losses": LedgerEntry(REQ, (_LOSSES,)),
        "terminal_policy_digest": LedgerEntry(REQ, (_ANSWER,)),
        "transform_registry_digest": LedgerEntry(REQ, (_ANSWER, _LOAD), "also ALGEBRA-REBIND-ON-LOAD"),
        "search_status": LedgerEntry(ADV, note=_SEARCH_OUTPUT + "; coherent with the outcome by construction"),
        "standard_status": LedgerEntry(ADV, note="== search_status.standard_name (the same completeness claim)"),
        "search_receipt": LedgerEntry(REQ, (_BOUNDS, _IR_POST), "container law: kind, scope and bounds are the "
                                      "request's (D27.6); identity digests == the IR's; members in the "
                                      "Section81ReceiptView table"),
        "candidates": LedgerEntry(ADV, note="membership: == the dossier set (D24.14), count == the receipt's (D27.5), "
                                  "kinds per the grammar (D26.1) -- but " + _SEARCH_OUTPUT),
        "diagnostics": LedgerEntry(RE, (_ANSWER,), "the producer's own rule over the IR's classification facts and the "
                                   "carried request -- ONE shared helper (D28.2, Wave C5 C5-F2); a recompile's is fully "
                                   "templated",
                                   advisory_when="a decompile's incompleteness line is its receipt's own stop_reason "
                                                 "(advisory search output)"),
        "structural_candidates": LedgerEntry(ADV, note="STRUCTURE-layer DECOMPILE only, parent == target, losses "
                                             "re-derived (IR construction, D24.11) -- the scissions are search output"),
    },
    "Section81ReceiptView": {
        "schema_version": LedgerEntry(FROZEN, (_RECEIPT_POST,)),
        "search_kind": LedgerEntry(REQ, (_BOUNDS,), "the kind the request's operation / grammar runs (D27.6, D27.8)"),
        "status": LedgerEntry(ADV, note="== the IR's search_status; " + _SEARCH_OUTPUT),
        "standard_status": LedgerEntry(ADV, note="== the IR's standard_status"),
        "cut_budget_scope": LedgerEntry(REQ, (_BOUNDS,), "PER_NODE for every engine a response wraps (D27.6, D27.8)"),
        "target_identity_digest": LedgerEntry(REQ, (_BOUNDS, _ANSWER), "non-null and == the IR target's (D26.1-bound; "
                                              "D28.3 -- a null used to slip the IR's present-only compare)"),
        "terminal_policy_digest": LedgerEntry(REQ, (_BOUNDS, _ANSWER), "non-null and == the IR's (D26.1-bound; D28.3)"),
        "transform_registry_digest": LedgerEntry(REQ, (_BOUNDS, _LOAD), "non-null and == the IR's (ALGEBRA-REBIND; "
                                                 "D28.3 covers the decompile leg the rebind skips)"),
        "max_depth": LedgerEntry(REQ, (_BOUNDS, _ANSWER), "== the request's (D27.6); every replayed route <= it"),
        "cut_budget": LedgerEntry(REQ, (_BOUNDS,), "== the request's (D27.6)"),
        "candidate_limit": LedgerEntry(FROZEN, (_RECEIPT_POST,), "always None (no engine caps emitted candidates)"),
        "result_limit": LedgerEntry(REQ, (_BOUNDS,), "== the request's (D27.6)"),
        "nodes_visited": LedgerEntry(ADV, note="search telemetry"),
        "transforms_considered": LedgerEntry(ADV, note="search telemetry"),
        "candidates_emitted": LedgerEntry(ADV, note="search telemetry (>= results_returned by construction)"),
        "results_returned": LedgerEntry(RE, (_COMPLETE,), "an int (never null, D28.3) == the carried candidate count, "
                                        "every kind (D27.5)"),
        "candidates_rejected_by_reason": LedgerEntry(ADV, note="search telemetry"),
        "cut_enumeration_complete": LedgerEntry(ADV, note=_SEARCH_OUTPUT),
        "candidate_enumeration_complete": LedgerEntry(ADV, note=_SEARCH_OUTPUT),
        "result_limit_saturated": LedgerEntry(ADV, note=_SEARCH_OUTPUT),
        "stop_reason": LedgerEntry(ADV, note=_SEARCH_OUTPUT),
    },
    "CandidateSummary": {
        "schema_version": LedgerEntry(FROZEN, (_CANDIDATE_POST,)),
        "candidate_kind": LedgerEntry(REQ, (_ANSWER, _COMPLETE), "per the request's grammar (D26.1); a relabelled kind "
                                      "leaves a dossier with no candidate of its kind (D24.14)"),
        "candidate_digest": LedgerEntry(RE, (_COMPLETE, _RANKING, _POST), "== a dossier's route digest (D24.14), the replayed "
                                        "route's (D27.4)", thin=ADV,
                                        advisory_when=_NO_DOSSIER),
        "equation": LedgerEntry(RE, (_ANSWER,), "== its dossier's label (D27.7), the replayed rendering (D26.1)",
                                thin=ADV, advisory_when=_NO_DOSSIER),
        "readiness_tier": LedgerEntry(FROZEN, (_CANDIDATE_POST,), "pinned FORMAL_CANDIDATE (M10)"),
    },
    "replay_step": {
        "schema_version": LedgerEntry(FROZEN, (_S + "_step_from_payload",
                                               "smartchem.experiment.step:ExperimentStep.__post_init__")),
        "target": LedgerEntry(RE, (_TRANSFORMS, _ANSWER), "every step is a transform the carried algebra emits for its "
                              "target (D29.1), the final target + every leaf are the request's (D26.1), <= max_depth "
                              "steps (D27.6); that the bounded SEARCH reached this locally generable route is the "
                              "search-output boundary (re-execution / HMAC only)" + _LEGACY_VA),
        "reactants": LedgerEntry(RE, (_TRANSFORMS, _ANSWER), "== an emitted transform's precursors, as STRUCTURES "
                                 "(D29.1); leaves within the declared terminal set (D26.1)" + _LEGACY_VA),
        "products": LedgerEntry(RE, (_TRANSFORMS,), "== an emitted transform's target + byproducts, as STRUCTURES "
                                "(D29.1 -- Wave C6 C6-F8: a same-formula byproduct isomer kept the rendered equation "
                                "byte-identical and erased a sourced hazard verdict)" + _LEGACY_VA),
        "reagents": LedgerEntry(RE, (_TRANSFORMS,), "the search never flags an ancillary reagent (D29.1)" + _LEGACY_VA),
        "envelope": LedgerEntry(RE, (_CORPUS,), "== the shipped corpus's lookup for the step, a carried unknown() "
                                "included (D27.1; D28.1 -- 'unknown claims nothing' held for readiness only)"),
        "reaction_center": LedgerEntry(RE, (_TRANSFORMS,), "one the emitted transform assigns (D29.1) -- still outside "
                                       "route.digest (D26.4), but a re-centre (Foreman N4) is now refused on every "
                                       "current load, not only under re-execution / HMAC" + _LEGACY_VA),
    },
}


def status_counts() -> dict[TransportStatus, int]:
    """Per-status entry counts over the whole ledger (canonical-wire statuses)."""
    counts = {status: 0 for status in TransportStatus}
    for table in TRANSPORT_LEDGER.values():
        for entry in table.values():
            counts[entry.status] += 1
    return counts


def advisory_fields(*, thin: bool = False) -> tuple[str, ...]:
    """``"Table.field"`` for every entry a keyless consumer must treat as ADVISORY (on the thin wire: incl. ``thin``)."""
    return tuple(f"{name}.{field}" for name, table in TRANSPORT_LEDGER.items() for field, entry in table.items()
                 if entry.status is ADV or (thin and entry.thin is ADV))


def partially_advisory_fields() -> tuple[str, ...]:
    """``"Table.field"`` for every re-derived / bound entry that is advisory in the cases its ``advisory_when`` names
    (X-high D28.4)."""
    return tuple(f"{name}.{field}" for name, table in TRANSPORT_LEDGER.items() for field, entry in table.items()
                 if entry.advisory_when)
