# SmartChem schema-id history (service wire generations)

**What this is.** The per-version changelog comments that used to sit on top of the schema-id constants in
`smartchem/service.py`, moved here **verbatim** (not summarised, not corrected) by the 0.9.5 consolidation incision
**I0** (barrier `docs/research/V0_9_5_ARCHITECTURE_FREEZE.md` §9).  Each block below is the exact comment text as it
stood immediately before the move, fenced so nothing is re-flowed.

**What stayed in the code.** Each constant keeps the comment describing its CURRENT generation (and, where one existed,
the one-paragraph description of what the schema is), plus a one-line pointer here.  Current behaviour is owned by the
code and its docstrings; these blocks are provenance -- the record of why each id is the id it is.

**Reading rule.** A block describes the tree at the moment each entry was written.  Present-tense statements about a
superseded generation are historical, not current law; where one conflicts with the code, the code wins.

**Recorded at:** the ids below are the values at the time of the move (0.9.5, pre-S10).  Later bumps add their entry
at the constant in `service.py`; when an entry is superseded it may be appended here.

## `COMPILATION_REQUEST_SCHEMA` = "smartchem.service/compilation-request-v1alpha7"

```text
# v1alpha4 (CLI-CAN-02): ConstraintPolicy carries a real PhysicalBounds (T/P) box instead of a placeholder
# constraint_id string -- a genuine request-payload shape change.  (v1alpha3 added SVC-REQ-01's normalized_identity;
# v1alpha2 added ID-LAYER-02's match_layer.)  (v1alpha5 was the released main@df1b38d / 0.8.0a1 request id.)
# v1alpha6 (0.9 RC Round V, D11 -- F74): a genuine request-payload shape change that Round III shipped WITHOUT a bump:
# the request gains ``capability_profile`` (the RESOLVED CapabilityProfile snapshot in canonical type-tagged form, or
# null = NOT_REQUESTED) and ``capability_profile_origin`` (display/preset-origin name).  Both keys are REQUIRED on a
# v1alpha6 payload.  DECLARED ONE-TIME MOVE: the request schema id is hashed into ``semantic_digest`` (see
# ``CompilationRequest.semantic_digest``), so this bump moves EVERY v1alpha6 semantic_digest exactly once relative to
# v1alpha5 -- no chemistry changed, the search is byte-identical.  Capability context STILL never enters
# semantic_digest (search noninterference).  A v1alpha5 payload is accepted ONLY as LEGACY (see
# ``LEGACY_V08_REQUEST_SCHEMA``): it keeps its stored id (so its stored semantic_digest verifies), means capability
# NOT_REQUESTED, and is REFUSED if it carries any ``capability_*`` key (a 0.9 field wearing a 0.8 id -- tamper T1, or a
# 0.9.0a1-branch payload that reused the id).
# v1alpha7 (0.9 RC Round V X-high, D14/D22): the embedded ``constraints`` PhysicalBounds is now
# ``physical-bounds-v1alpha2`` (+``min_temperature_k``, the temperature FLOOR -- the one shared T/P leaf finally models a
# RANGE) and the embedded capability profile is ``capability-profile-v1alpha3`` (StockMaterial v1alpha3 +phase_evidence,
# PhysicalBounds v1alpha2).  ``capability_profile_origin`` is now CONTENT-BOUND: it must be ``""`` or equal the
# snapshot's own ``profile_id`` (Wave-A' A-WIRE (g): a free-text origin rode outside every digest, even the signed one,
# yet was rendered as ``CAPABILITY[origin]``).  The WIP-only v1alpha6 id (pushed on the unreleased branch, never on
# main) is NOT migrated -- only the released v0.8 id stays legacy.  The request id is hashed into ``semantic_digest``,
# so this moves every current semantic_digest exactly once more; capability STILL never enters it.
```

## `COMPILATION_RESPONSE_SCHEMA` = "smartchem.service/compilation-response-v1alpha17"

```text
# v1alpha2 (SVC-REQ-01 alias-collapse): CompilationResponse gains a ``parse_receipt_summary`` field -- the section
# 14.2 identity-resolution echo, pulled OUT of ``diagnostics`` (where it rode as a free-text last line) into a
# first-class field, so it is surfaced as the section 14.3 receipt yet EXCLUDED from ``result_digest`` (it is
# provenance -- how the string was READ -- not part of the search RESULT).  (v1alpha1 was the first brick.)
# v1alpha3 (CLI-CAN-02 brick 2): ``ranked_route_dossiers`` is now POPULATED (routes mode) with typed
# ``RankedRouteSummary`` objects -- the section-11 bench-fit disposition per route -- so the array elements gain
# structure and the payload shape genuinely changes.
# v1alpha4 (SRCH-NO-01): the response gains a first-class ``search_space_status`` field -- the section-8.3
# no-route matrix label (NO_ROUTE_IN_DECLARED_SPACE / INCOMPLETE_NO_ROUTE_OBSERVED / COMPLETE_CANDIDATE_SET /
# PARTIAL_CANDIDATE_SET), so the four-outcome distinction rides the machine payload uniformly, not only the render.
# v1alpha5 (COST-VEC-01): ``affordability_frontier`` is now POPULATED (routes mode) with typed
# ``AffordabilityFrontierEntry`` objects -- the section-10.4 Pareto affordability frontier over the ranked routes --
# so the array elements gain structure (the old "must be empty" placeholder is retired).
# v1alpha6 (SNAPSHOT-13.2): the response gains a ``provider_snapshots`` field -- the dated section-13.2 provenance of
# any LIVE provider fetch that serviced the request (empty on an offline/default run), so a --network response is
# reproducible.  EXCLUDED from result_digest (a fetch time is provenance, not a search result).
# v1alpha7 (COST-VEC-01-coupled): the affordability_frontier's flattened CostVector gains a ``cash_floor`` axis (an
# honest partial-basket lower bound), so the response value shape changed.
# v1alpha8 (COST-VEC-01 quantity axis): the frontier's ``material_quantity`` axis is now POPULATED (routes mode) with
# each route's total external-leaf MOLES per mol product -- a previously-always-null field now carries a value.
# v1alpha10 (PROCESS-ADMIT-01): each ranked_route_dossiers entry now carries its per-step ``process_requirements`` so
# process admission is RE-DERIVED on load (the deserialization trust-boundary close), not trusted from ``fit_status``.
# v1alpha11 (COMBINED-VERDICT-AUTH): the payload carries a top-level ``producer_signature`` field (an optional HMAC over
# ``result_digest``; ``null`` unless signed) so a consumer with the producer key can reject an out-of-band tamper.
# v1alpha12 (DAG-ADMIT-01): the response gains a ``ranked_dag_dossiers`` field -- the FORMAL, load-re-derived PROCESS
# admission of each convergent-DAG candidate (was a throwaway diagnostic), so ``process_selection_status`` is no longer
# UNASSESSED for a DAG-mode compile.  Folded into ``result_digest`` ONLY when non-empty, so a linear/DAG-less response
# stays byte-identical to v1alpha11 (zero ripple); a DAG-mode process-constrained response's result_digest changes.
# v1alpha13 (TAMPER-HARDENING-01): NO new field -- a new ON-LOAD REFUSAL.  ``_check_frontier_coherence`` re-derives
# each affordability_frontier entry's ``hard_blockers`` (process exclusions + catalyst) and ``fiction_blockers``
# (reaction-type oracle) and REFUSES an entry whose claimed blockers are looser than the re-derivation -- closing the
# R59 disposition serialized-tamper (a stripped blocker flipping REAL_BUT_HARD/NOT_A_REACTION up to CLEAN, undetected
# because the frontier is EXCLUDED from result_digest).  FULLY closed on every transport: the process-exclusion
# channel (re-derived from digest-covered process_requirements, no replay needed).  The catalyst/fiction channels are
# closed on the THICK transport (include_replay=True, digest-bound) and, under verified admission, on the thin
# transport too -- a thin (replay-absent) load then fails CLOSED rather than trusting the unverifiable disposition
# (replay-MANDATORY-for-disposition-claims); a bare non-verified load keeps them ADVISORY.  The bump carries no shape
# change; it marks the version at/after which a loaded
# response is frontier-coherence-checked, so a pre-guarantee v1alpha12 payload is refused by the strict schema gate.
# v1alpha14 (v0.8 Real Route Dossiers, M10): NO new top-level field -- a new ON-LOAD REFUSAL, mirroring v1alpha13's own
# convention.  ``CompilationResponse._check_readiness_coherence`` (run unconditionally from ``response_from_payload``,
# UN-gated on ``fit_status`` or ``require_verified_admission`` -- readiness is orthogonal to bench-fit, Sec 2) re-derives
# each ranked route's typed readiness ladder from its thick ``replay_payload`` via ``evaluate_route`` and REFUSES a
# payload whose carried ``readiness`` disagrees with the re-derivation (a bumped tier, a stripped citation, a
# substituted per-step obligation).  Advisory (unenforceable) on a thin (replay-absent) route on a PLAIN load, exactly
# as the catalyst/fiction frontier channels are -- BUT under ``require_verified_admission`` a thin claim ABOVE the
# FORMAL_CANDIDATE floor is fail-closed (Wave C thin-transport closure), mirroring fit/frontier.  The bump marks the
# version at/after which a readiness claim is re-derived, so a pre-guarantee v1alpha13 payload is refused by the gate.
# v1alpha15 (v0.8 Round II, D5 canonical transport): the response payload gains a top-level ``transport_mode``
# ({CANONICAL_VERIFIED, THIN_ADVISORY}) FOLDED into ``result_digest``, and ``include_replay`` now defaults True so the
# canonical wire ships each dossier's ``replay_payload``.  The digest-covered ConditionEnvelope also gained a
# ``procedure`` field this round (via the replay payload), so envelope->step->route->summary->result digests shift --
# no chemistry changed, the search is byte-identical.  (v1alpha15 was the released main@df1b38d / 0.8.0a1 response id.)
# v1alpha16 (0.9 RC Round V, D11 -- F74/F81): a genuine response shape change that Round III shipped WITHOUT a bump:
# the response gains a top-level ``capability_question_digest`` (null = NOT_REQUESTED) and now EMBEDS a v1alpha6
# request and ranked-route-summary-v1alpha4 dossiers (+capability_assessment; replay ProcedureOperation gains
# ``material_uses`` whose ProcedureMaterialUse carries a typed ``specification``).  ``capability_question_digest`` is
# REQUIRED on a v1alpha16 payload.  The digest-covered ProcedureOperation/RankedRouteSummary shapes grew, so route ->
# dossier -> result digests shift.  A v1alpha15 payload is accepted ONLY as LEGACY (``LEGACY_V08_RESPONSE_SCHEMA``):
# verified under the FROZEN v0.8 digest rule (``_v08_canonical_payload`` -- the 0.9-added fields omitted at their
# default), readiness preserved exactly and re-derived, NO capability question and NO assessment fabricated; REFUSED
# if it carries any 0.9-only key (capability_question_digest / capability_assessment / capability_profile* /
# material_uses / specification -- tamper T4b, and 0.9.0a1-branch payloads that reused the id).
# Still v1alpha16 (unreleased), Wave-C2: ``result_digest`` now folds ``capability_question_digest`` when a question was
# asked (so the producer signature binds the declared bench even with zero dossiers), and every assessed dossier's
# replay-free bindings (HARD-LAW fold, readiness tier/digest, profile_digest, route_digest; CAPABILITY_FIT refused on a
# THIN_ADVISORY wire) are checked on every load.  NOT_REQUESTED/legacy result digests are unchanged.
# v1alpha17 (0.9 RC Round V X-high, D18/D20/D22): embeds a v1alpha7 request, ranked-route-summary-v1alpha5 (replay
# ProcedureMaterialUse ``phase`` is now an evidence-graded PhaseClaim object, D18) and ranked-dag-summary-v1alpha5
# dossiers.  Load gains an optional consumer capability-question pin (``expected_capability_question_digest``), the
# verified-admission re-projection now carries the request's capability profile, and the 0.8 thin law refuses any tier
# AT OR ABOVE PROCESS_SPECIFIED.  The WIP-only v1alpha16 id is NOT migrated (never released).
```

## `COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR` = "smartchem.service/compilation-response-schema-v1alpha20"

```text
# The versioned descriptor of the --json response SHAPE (standard 14.3 "stable versioned response schema").  It is
# bumped only when a field is added/removed/renamed -- never when a derived digest changes -- so it is the durable
# pin CLI-JSON-01's golden guards, distinct from the per-value response schema version above.  v1alpha9: the
# affordability_frontier cost_vector gains cash_floor (COST-VEC-01-coupled).  v1alpha8: the provider_snapshots field
# (SNAPSHOT-13.2).  v1alpha7: the affordability_frontier element shape (COST-VEC-01).  v1alpha6: the
# search_space_status section-8.3 field (SRCH-NO-01).  v1alpha5: the ranked_route_dossiers element shape (CLI-CAN-02
# brick 2).  (v1alpha4: the request schema bumped for ConstraintPolicy.bounds; v1alpha3: the parse_receipt_summary
# response field + the normalized_identity request field; v1alpha2: IR-LOSS-01's identity_losses.)  v1alpha11
# (PROCESS-ADMIT-01): the ranked_route_summary gains a per-step ``process_requirements`` field (re-derived on load).
# v1alpha12 (COMBINED-VERDICT-AUTH): the response gains a top-level ``producer_signature`` field.
# v1alpha13 (DAG-ADMIT-01): the response gains a ``ranked_dag_dossiers`` field (per-DAG process admission).
# v1alpha14 (DAG-BENCH-01): the ranked_dag_summary element's ``process_fit_status`` field is RENAMED to ``fit_status``
# and now carries the COMBINED section-11 verdict (composability + physical box + process), not the process axis alone.
# v1alpha15 (DAG-THERMO-01): the ranked_dag_summary element gains composability/selectivity/feasibility/equilibrium/
# kinetics verdict fields (the per-node thermochemical roll-up feeding the DAG ranking), reaching parity with the
# ranked_route_summary's verdict fields so a DAG dossier's best-first order is as inspectable as a linear one's.
# v1alpha16 (item 2b): the ranked_dag_summary element gains a machine-readable ``serial_holds`` field (the DAG-HOLD-01
# serial-schedule hold as (producer, consumer, minutes) triples) -- a descriptor-only bump (the field is disclosure,
# digest-excluded, so no result_digest ripple, and it is empty for every non-holding/linear-shaped DAG).
# TAMPER-HARDENING-01: the descriptor was NOT bumped for that round.  Its embedded ``response_schema_version`` VALUE
# read v1alpha13 (a derived-value change), but no descriptor FIELD was added/removed/renamed -- the on-load
# frontier-coherence refusal changed behaviour, not shape -- and this descriptor bumps ONLY on a shape change (its own
# stated convention).
# v1alpha17 (v0.8 Real Route Dossiers): a genuine SHAPE change -- ``ranked_route_summary_fields`` gains a typed
# ``readiness`` field (Sec 3/4/8's per-step obligation ladder; ``readiness_tier`` stays, now a documented DERIVED
# convenience alias of ``readiness.tier`` rather than a hard-coded floor).  Bumped per the descriptor's own convention.
# v1alpha18 (v0.8 Round II, D5 canonical transport): a genuine SHAPE change -- ``response_fields`` gains a top-level
# ``transport_mode`` field and ``ranked_route_summary_fields``/``ranked_dag_summary_fields`` disclose the optional
# ``replay_payload`` (emitted by default now that the canonical wire ships it).  Bumped per the descriptor's convention.
# v1alpha19 (0.9 RC Round V, D11 -- F74): a genuine SHAPE change Round III shipped without a bump: ``response_fields``
# gains ``capability_question_digest``; ``ranked_route_summary_fields`` gains ``capability_assessment``; the embedded
# request is now v1alpha6 (+capability_profile, +capability_profile_origin); the replay disclosure now names the
# procedure operations' ``material_uses`` (+``specification``); and the descriptor gains a top-level
# ``accepted_legacy_schema_versions`` map (the explicit, whitelisted v0.8 ids the loader migrates).
# v1alpha20 (0.9 RC Round V X-high, D18/D20/D22): the embedded request is v1alpha7 (the constraints box discloses
# ``min_temperature_k``; the origin is content-bound); the replay disclosure names the PhaseClaim ``phase`` object of a
# procedure material use; ``accepted_legacy_schema_versions`` gains the released ``ranked_dag_summary`` and
# ``physical_bounds`` ids; ``capability_question_digest`` discloses the consumer pin.
```

## `RANKED_ROUTE_SUMMARY_SCHEMA` = "smartchem.service/ranked-route-summary-v1alpha5"

```text
# CLI-CAN-02 brick 2: the thin, digestible per-route ranking summary that POPULATES the response's
# ``ranked_route_dossiers``.  It is projected off a drafter :class:`~smartchem.experiment.drafter.RouteFit` so the
# heavy ExperimentRoute/thermo object graph never enters the response payload; it carries the section-11 bench-fit
# disposition (FITS/EXCLUDED/UNKNOWN/UNCONSTRAINED with exact reasons) and the ranking's sourced verdicts.
# v1alpha3 (v0.8 Real Route Dossiers): gains a typed ``readiness`` field (``smartchem.experiment.readiness.
# RouteReadiness`` -- the Sec 3/4/8 per-step obligation ladder), digest-covered exactly like ``process_requirements``.
# ``readiness_tier`` is retired as a stored field (it was a hard-coded ``FORMAL_CANDIDATE`` floor -- READY-TIER-01 --
# no route could ever earn or lose) and is now a derived ``@property`` reading ``readiness.tier``; every existing
# ``.readiness_tier`` read keeps working, it just answers honestly now.  (v1alpha3 was the released main@df1b38d id.)
# v1alpha4 (0.9 RC Round V, D11 -- F74): gains the digest-covered ``capability_assessment`` field (0.9 Round III, shipped
# without a bump), and its thick ``replay_payload`` procedure operations gain ``material_uses`` (each a
# ProcedureMaterialUse, which gains the typed ``specification`` in Round V).  ``capability_assessment`` is REQUIRED on
# a v1alpha4 payload.  A v1alpha3 summary is accepted ONLY inside a LEGACY v1alpha15 response, decoded with
# capability_assessment=None / material_uses=(), and digested under the frozen v0.8 rule.
# v1alpha5 (0.9 RC Round V X-high, D18): the replay ProcedureMaterialUse ``phase`` is an evidence-graded PhaseClaim
# object ({phase, evidence, note}) instead of an ungraded scalar -- an author's inference can no longer certify a phase
# match (FIT) or mismatch (BLOCKED).  The WIP-only v1alpha4 id is NOT migrated (never released).
```

## `RANKED_DAG_SUMMARY_SCHEMA` = "smartchem.service/ranked-dag-summary-v1alpha5"

```text
# DAG-BENCH-01 (was DAG-ADMIT-01): the thin, digestible per-DAG COMBINED section-11 admission that populates the
# response's ``ranked_dag_dossiers``.  Distinct from RANKED_ROUTE_SUMMARY_SCHEMA on purpose -- a DAG additionally
# carries its ``edges`` (so the critical-path PROCESS component is re-derived on load, the convergent PROCESS-ADMIT-01)
# -- but ``fit_status`` is now the SAME combined verdict (composability + physical box + process) a linear route
# carries, so a convergent DAG is a first-class bench citizen.  v1alpha2: ``process_fit_status`` renamed ``fit_status``
# and widened from the process axis alone to the combined bench fit.  v1alpha3 (DAG-THERMO-01): gains the five ranking
# verdict fields (composability/selectivity/feasibility/equilibrium/kinetics) so the DAG dossier exposes the same
# sourced tiebreakers the ranked_route_summary does -- parity, and the best-first order made inspectable.
# v1alpha4 (item 2b): gains a machine-readable ``serial_holds`` field -- the DAG-HOLD-01 serial-schedule hold as
# (producer, consumer, minutes) triples.  DISCLOSURE only (never changes fit_status) and digest-EXCLUDED (it is
# fully determined by edges + process_requirements), so no existing DAG digest moves; the version bumps because
# the element's serialized SHAPE gained a field.
# v1alpha5 (0.9 RC Round V X-high, D22 -- Wave-A' A-WIRE P3): the thick ``replay_payload`` procedure operations now
# REQUIRE ``material_uses`` (each a ProcedureMaterialUse with its typed specification and PhaseClaim phase) -- a shape
# change Round III/V shipped under the released v1alpha4 id.  The released v1alpha4 shape is decoded ONLY as LEGACY
# (``LEGACY_V08_RANKED_DAG_SUMMARY_SCHEMA``): refused if it carries any 0.9-only key at any depth, its replay operations
# migrated to ``material_uses=[]`` (their only v0.8-expressible value), and paired only with a legacy v0.8 response.
```
