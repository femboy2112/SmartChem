"""ROUND-17 item 1 (PROCESS-OBS-01): the read-only ProcessObservationIR evidence-ingress layer.

P1 of the creator-process contract (``docs/research/PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md``):
footage/institutional sources become SCOPED OPERATIONAL OBSERVATIONS, never a recipe corpus.  Every
test below is one of the contract's own acceptance probes or one of its seven non-negotiable invariants
-- and the battery is deliberately NON-VACUOUS: the ``..._evidences_a_fully_documented_observation``
test proves the capability bundle CAN return EVIDENCED, so the many GAP/BLOCKED probes are checking a
live discriminator, not an always-GAP stub (the ``vacuous-green-over-an-empty-subject`` guard).
"""
from __future__ import annotations

import dataclasses

import pytest

from smartchem.decompiler_conditions import ReactionDirection
from smartchem.experiment.affordability import CostVector, dominates
from smartchem.observation import (
    PROCESS_OBSERVATION_SCHEMA,
    BucketStatus,
    CapabilityBucket,
    ClaimStatus,
    ContextScope,
    FrankenprocedureError,
    ObservationClaim,
    ObservationPhase,
    ProcessObservationIR,
    ProjectionDisposition,
    SourceFragment,
    SourceRole,
    Transport,
    TransportDisposition,
    capability_bundle,
    capability_hard_blockers,
    merge_observations,
    operationally_complete,
    projection_gate,
)
from smartchem.provenance import SourceReview


# --- builders ------------------------------------------------------------------------------------

def _frag(*, review=SourceReview.UNREVIEWED, role=SourceRole.CREATOR, reviewer=None):
    return SourceFragment(
        "https://www.youtube.com/watch?v=example",
        role,
        review=review,
        publication_or_capture_date="2026-01-01",
        quote_or_timecode="12:30",
        reviewer=reviewer,
    )


def _claim(subject, supports, *, status=ClaimStatus.OBSERVED, not_establish="not a general protocol", value=None):
    return ObservationClaim(status, subject, supports, not_establish, value_and_unit=value)


def _obs(**kw):
    base = dict(
        observation_id="obs-1",
        reaction_identity="resonance:paracetamol-hydrolysis",
        reaction_direction=ReactionDirection.DECOMPOSITION,
        run_context_id="run-A",
        phase=ObservationPhase.REACTION,
        source_fragment=_frag(),
    )
    base.update(kw)
    return ProcessObservationIR(**base)


def _fully_documented():
    """One (artificial) super-observation that documents evidence for all five bundles -- the
    non-vacuity anchor: it proves EVIDENCED is reachable on every bucket."""
    return _obs(
        phase=ObservationPhase.ANALYSIS,
        context_scope=ContextScope(
            material_identity_and_assay="acetaminophen, reagent grade, assayed",
            scale_and_geometry="5 g in a 100 mL flask",
            apparatus_capabilities="reflux with a calibrated separation/containment train",
            medium_and_atmosphere="aqueous, ambient air",
            controlled_intervals="30 min at reflux",
        ),
        claims=(
            _claim("material identity and assay", "the material identity is documented"),
            _claim("containment and separation capability", "a ventilation/containment control is documented"),
            _claim("acceptance endpoint", "an observable acceptance test with declared limits"),
            _claim("waste disposal and decontamination", "the waste disposal path is documented"),
        ),
        transport=Transport(TransportDisposition.EXACT),
    )


# --- invariants ----------------------------------------------------------------------------------

def test_schema_version_is_pinned():
    with pytest.raises(ValueError, match="schema"):
        _obs(schema_version="smartchem.observation/process-observation-vBOGUS")
    assert _obs().schema_version == PROCESS_OBSERVATION_SCHEMA


def test_the_ir_carries_no_readiness_or_safety_field():
    # Invariant 4: evidence never promotes by itself -- the IR is STRUCTURALLY incapable of emitting a
    # readiness/safety/clearance value because it has no such field to carry one.
    names = {f.name for f in dataclasses.fields(ProcessObservationIR)}
    for forbidden in ("readiness", "readiness_tier", "safety", "clearance", "proceed", "bench_draft"):
        assert forbidden not in names


def test_an_unknown_claim_cannot_carry_a_value():
    # Invariant 3: unknown stays unknown -- it cannot smuggle a positive number under an UNKNOWN status.
    ObservationClaim(ClaimStatus.UNKNOWN, "yield", "nothing is established", "the yield is undocumented")
    with pytest.raises(ValueError, match="UNKNOWN"):
        ObservationClaim(ClaimStatus.UNKNOWN, "yield", "nothing", "undocumented", value_and_unit="82 %")


def test_a_positive_claim_must_declare_what_it_does_not_establish():
    # Invariant 5: observables have scope.
    _claim("purity", "a rapid screen consistent with the identity")  # ok: both scope fields present
    with pytest.raises(ValueError, match="what_it_does_not_establish"):
        ObservationClaim(ClaimStatus.OBSERVED, "purity", "a rapid screen", "")


def test_an_accepted_source_fragment_must_name_a_reviewer():
    # Fail-closed strengthening of the binary SourceReview: acceptance without attribution is refused.
    with pytest.raises(ValueError, match="reviewer"):
        _frag(review=SourceReview.ACCEPTED, role=SourceRole.INSTITUTIONAL)
    ok = _frag(review=SourceReview.ACCEPTED, role=SourceRole.INSTITUTIONAL, reviewer="curator@lab")
    assert ok.accepted is True


def test_the_provenance_digest_is_computed_not_stored_and_a_mutated_claim_changes_it():
    # Invariant 6, NON-VACUOUS: the digest is over the real content, not a hand-set string.
    o = _fully_documented()
    assert o.provenance_digest == o.digest  # computed property, not a stored field
    assert "provenance_digest" not in {f.name for f in dataclasses.fields(ProcessObservationIR)}
    # reordering the SAME claims is not a change -> identical digest (claims are sorted by content)
    reordered = _obs(
        phase=o.phase, context_scope=o.context_scope, transport=o.transport,
        claims=tuple(reversed(o.claims)),
    )
    assert reordered.provenance_digest == o.provenance_digest
    # mutating a claim, the source fragment, or the transport each MOVES the digest
    mutated_claim = _obs(phase=o.phase, context_scope=o.context_scope, transport=o.transport,
                         claims=o.claims[:-1] + (_claim("waste disposal", "a DIFFERENT waste path"),))
    assert mutated_claim.provenance_digest != o.provenance_digest
    mutated_frag = _obs(phase=o.phase, context_scope=o.context_scope, transport=o.transport,
                        claims=o.claims, source_fragment=_frag(reviewer="someone", review=SourceReview.ACCEPTED))
    assert mutated_frag.provenance_digest != o.provenance_digest
    mutated_transport = _obs(phase=o.phase, context_scope=o.context_scope, claims=o.claims,
                             transport=Transport(TransportDisposition.UNKNOWN))
    assert mutated_transport.provenance_digest != o.provenance_digest


def test_transport_invariants():
    Transport(TransportDisposition.EXACT)  # ok
    with pytest.raises(ValueError, match="EXACT"):
        Transport(TransportDisposition.EXACT, mismatches=("scale differs",))
    with pytest.raises(ValueError, match="reviewed_bridge_id"):
        Transport(TransportDisposition.PARTIAL)
    Transport(TransportDisposition.PARTIAL, mismatches=("grade differs",), reviewed_bridge_id="bridge-7")  # ok
    with pytest.raises(ValueError, match="mismatch"):
        Transport(TransportDisposition.OUT_OF_SCOPE)


# --- capability bundle (NON-VACUOUS: EVIDENCED is reachable) --------------------------------------

def test_the_five_buckets_are_reported_exactly_once():
    findings = capability_bundle(_obs())
    assert {f.bucket for f in findings} == set(CapabilityBucket)
    assert len(findings) == len(CapabilityBucket)


def test_the_capability_bundle_evidences_a_fully_documented_observation_non_vacuously():
    # THE non-vacuity anchor: without this, every GAP/BLOCKED probe below could pass over an always-GAP
    # stub.  A fully documented observation must light up EVIDENCED on every bundle.
    findings = {f.bucket: f for f in capability_bundle(_fully_documented())}
    for bucket in CapabilityBucket:
        assert findings[bucket].status is BucketStatus.EVIDENCED, f"{bucket} should be EVIDENCED"
        assert findings[bucket].supporting_subjects, f"{bucket} EVIDENCED must cite what supported it"


def test_removing_workup_scale_endpoint_or_waste_evidence_yields_a_gap_not_a_promotion():
    # Acceptance probe 1: strip the closure + scale evidence from an otherwise good record.
    good = _fully_documented()
    stripped = _obs(
        phase=good.phase,
        context_scope=ContextScope(  # scale + closure evidence removed
            material_identity_and_assay=good.context_scope.material_identity_and_assay,
            apparatus_capabilities=good.context_scope.apparatus_capabilities,
        ),
        claims=tuple(c for c in good.claims if "waste" not in c.subject),
        transport=good.transport,
    )
    findings = {f.bucket: f for f in capability_bundle(stripped)}
    assert findings[CapabilityBucket.CLOSURE].status is BucketStatus.GAP
    assert findings[CapabilityBucket.SCALE].status is BucketStatus.GAP
    assert operationally_complete(capability_bundle(good)) is True
    assert operationally_complete(capability_bundle(stripped)) is False  # probe 7, explicit


def test_a_generic_apparatus_name_alone_is_a_capability_gap_not_evidenced():
    # Acceptance probe 4: a generic apparatus name with no qualification/capability claim is UNKNOWN
    # (GAP), never FITS -- the forbidden equipment-name-equals-capability shortcut.
    named_only = _obs(context_scope=ContextScope(apparatus_capabilities="a flask, a hot plate, a pump"))
    findings = {f.bucket: f for f in capability_bundle(named_only)}
    assert findings[CapabilityBucket.CAPABILITY].status is BucketStatus.GAP


def test_a_hazard_without_a_containment_capability_is_blocked():
    # The DOW/kitchen edge: a toxic/corrosive species present with NO containment/control evidenced is a
    # CAPABILITY_BLOCKED (a hard blocker), even outdoors -- ventilation is not hazard clearance.
    hazardous = _obs(context_scope=ContextScope(medium_and_atmosphere="chlorine off-gas evolved, outdoors"))
    findings = {f.bucket: f for f in capability_bundle(hazardous)}
    assert findings[CapabilityBucket.CAPABILITY].status is BucketStatus.BLOCKED


def test_a_numeric_conclusion_needs_positive_calibration_or_it_is_blocked_unverified():
    # Acceptance probe 5 + evil-morty fold (fail-closed): a numeric conclusion is UNVERIFIED unless
    # calibration/QC is POSITIVELY evidenced -- SILENTLY-omitted, explicitly-unknown, and negated
    # calibration all BLOCK (the old code blocked only the explicitly-flagged case and let a silently
    # omitted calibration reach EVIDENCED -- a fail-open the test itself had codified).
    numeric = _claim("assay endpoint", "the product assays at the acceptance endpoint", value="98 %")
    calib = _claim("calibration", "the balance was calibrated against a certified reference standard")
    missing = _obs(phase=ObservationPhase.ANALYSIS, claims=(numeric,))                      # silently omitted
    flagged = _obs(phase=ObservationPhase.ANALYSIS, claims=(numeric,),
                   explicit_unknowns=("calibration state of the balance",))                 # explicitly unknown
    calibrated = _obs(phase=ObservationPhase.ANALYSIS, claims=(numeric, calib))             # positively evidenced

    def verification(o):
        return {f.bucket: f for f in capability_bundle(o)}[CapabilityBucket.VERIFICATION].status

    assert verification(missing) is BucketStatus.BLOCKED   # the fold: a silently-omitted calibration blocks
    assert verification(flagged) is BucketStatus.BLOCKED
    assert verification(calibrated) is BucketStatus.EVIDENCED  # NON-VACUOUS differential: real calibration


def test_a_negated_containment_claim_does_not_unblock_a_hazard():
    # evil-morty CRITICAL fold: a claim DENYING containment must never read as evidence FOR it -- the
    # honestly-narrated ABSENCE of a control is the case most likely to describe a hazard, and it must
    # stay BLOCKED (a bare substring match counted "no containment" as containment and inverted this).
    obs = _obs(
        context_scope=ContextScope(apparatus_capabilities="a beaker outdoors",
                                   medium_and_atmosphere="chlorine off-gas evolved"),
        claims=(_claim("containment", "there was NO containment; the chlorine vented into the open air"),),
    )
    findings = capability_bundle(obs)
    assert {f.bucket: f for f in findings}[CapabilityBucket.CAPABILITY].status is BucketStatus.BLOCKED
    assert capability_hard_blockers(findings)  # the hard blocker is NOT erased by the negated claim


def test_a_negated_waste_claim_does_not_mark_the_route_operationally_complete():
    # evil-morty CRITICAL fold: "waste dumped, no treatment" is a described FAILURE of closure, not evidence.
    obs = _obs(
        phase=ObservationPhase.WASTE,
        claims=(_claim("waste path", "the waste was poured down the drain with NO treatment or decontamination"),),
    )
    findings = capability_bundle(obs)
    assert {f.bucket: f for f in findings}[CapabilityBucket.CLOSURE].status is not BucketStatus.EVIDENCED
    assert operationally_complete(findings) is False


def test_a_negated_material_claim_is_not_material_evidence():
    # evil-morty HIGH fold: an unlabeled/unverified material is documented ABSENCE of identity, not evidence.
    obs = _obs(
        context_scope=ContextScope(material_identity_and_assay="a white powder from an unlabeled jar"),
        claims=(_claim("material", "an unlabeled reagent of unknown grade and unverified identity"),),
    )
    assert {f.bucket: f for f in capability_bundle(obs)}[CapabilityBucket.MATERIAL].status is BucketStatus.GAP


def test_a_scale_outside_the_source_envelope_is_blocked_and_needs_a_partial_or_out_of_scope_transport():
    # Acceptance probe 6: change scale/geometry outside scope -> SCALE_UNVALIDATED, transport degraded.
    out = _obs(
        context_scope=ContextScope(scale_and_geometry="scaled 100x to 500 g"),
        transport=Transport(TransportDisposition.OUT_OF_SCOPE, mismatches=("scale increased 100x beyond source",)),
    )
    findings = {f.bucket: f for f in capability_bundle(out)}
    assert findings[CapabilityBucket.SCALE].status is BucketStatus.BLOCKED
    assert out.transport.disposition in (TransportDisposition.PARTIAL, TransportDisposition.OUT_OF_SCOPE)


def test_a_capability_blocked_finding_outranks_cash_via_the_affordability_hard_blocker():
    # Acceptance probe 9: a cheap reagent basket that lacks an engineered control does NOT outrank a
    # controlled route.  The BLOCKED finding becomes a CostVector.hard_blocker, and G6 (hard blocker
    # dominates cost) makes the clean-but-dearer route dominate the cheap-but-blocked one.
    hazardous = _obs(context_scope=ContextScope(medium_and_atmosphere="chlorine off-gas evolved, outdoors"))
    blockers = capability_hard_blockers(capability_bundle(hazardous))
    assert blockers, "a CAPABILITY_BLOCKED finding must yield a hard-blocker string (non-vacuous)"
    cheap_blocked = CostVector(cash=1.0, currency="USD", unit="metric ton", hard_blockers=blockers)
    controlled_dearer = CostVector(cash=100.0, currency="USD", unit="metric ton")
    assert dominates(controlled_dearer, cheap_blocked) is True   # clean beats blocked at any price
    assert dominates(cheap_blocked, controlled_dearer) is False  # blocked never outranks clean


# --- no-Frankenprocedure merge (invariant 1) -----------------------------------------------------

def test_combining_two_run_contexts_without_a_bridge_is_refused():
    # Acceptance probe 3 / invariant 1: fragments from different run contexts cannot be merged.
    a = _obs(observation_id="a", run_context_id="run-A", phase=ObservationPhase.REACTION)
    b = _obs(observation_id="b", run_context_id="run-B", phase=ObservationPhase.WORKUP)
    with pytest.raises(FrankenprocedureError, match="different run contexts"):
        merge_observations((a, b))
    # NON-VACUOUS: same-context fragments DO merge into a phase-ordered view.
    same = merge_observations((
        _obs(observation_id="late", run_context_id="run-A", phase=ObservationPhase.WORKUP),
        _obs(observation_id="early", run_context_id="run-A", phase=ObservationPhase.SETUP),
    ))
    assert [o.phase for o in same] == [ObservationPhase.SETUP, ObservationPhase.WORKUP]


def test_merge_refuses_mismatched_identity_or_direction_within_one_run_context():
    # evil-morty fold: a shared run_context_id is a self-declared string; fragments must ALSO agree on
    # reaction identity and direction, else two unrelated reactions (or a decomposition + an assembly)
    # splice into one bundle under a forged shared label -- bypassing invariants 1 and 2 from inside a
    # single context.
    a = _obs(observation_id="a", run_context_id="run-A", reaction_identity="resonance:X",
             reaction_direction=ReactionDirection.DECOMPOSITION, phase=ObservationPhase.REACTION)
    diff_identity = _obs(observation_id="b", run_context_id="run-A", reaction_identity="resonance:Y",
                         reaction_direction=ReactionDirection.DECOMPOSITION, phase=ObservationPhase.WORKUP)
    opp_direction = _obs(observation_id="c", run_context_id="run-A", reaction_identity="resonance:X",
                         reaction_direction=ReactionDirection.ASSEMBLY, phase=ObservationPhase.WORKUP)
    with pytest.raises(FrankenprocedureError, match="agree on reaction_identity"):
        merge_observations((a, diff_identity))
    with pytest.raises(FrankenprocedureError, match="agree on reaction_identity"):
        merge_observations((a, opp_direction))


# --- one-way projection gate (invariants 1, 2, 5) ------------------------------------------------

def _accepted_exact(**kw):
    base = dict(
        source_fragment=_frag(review=SourceReview.ACCEPTED, role=SourceRole.INSTITUTIONAL, reviewer="curator@lab"),
        transport=Transport(TransportDisposition.EXACT),
        claims=(_claim("elapsed time", "30 min at reflux"), _claim("temperature", "reflux, ~100 C")),
    )
    base.update(kw)
    return _obs(**base)


def test_a_reverse_direction_fragment_cannot_support_the_opposite_direction():
    # Acceptance probe 2 / invariant 2: direction is load-bearing, and it is refused FIRST.
    decomp = _accepted_exact(reaction_direction=ReactionDirection.DECOMPOSITION)
    readout = projection_gate(decomp, target_identity=decomp.reaction_identity,
                              target_direction=ReactionDirection.ASSEMBLY)
    assert readout.disposition is ProjectionDisposition.REFUSED_DIRECTION
    assert not readout.licensed


def test_a_wrong_isomer_identity_is_refused():
    o = _accepted_exact()
    readout = projection_gate(o, target_identity="resonance:a-different-C8H9NO2-isomer",
                              target_direction=o.reaction_direction)
    assert readout.disposition is ProjectionDisposition.REFUSED_IDENTITY


def test_creator_video_only_evidence_cannot_bypass_the_projection_gate():
    # Acceptance probe 8: creator-video evidence may be a demonstrated source record, but until
    # reviewer-accepted it cannot bypass the gate -- even with a matching identity/direction and EXACT
    # transport.
    creator = _obs(
        source_fragment=_frag(role=SourceRole.CREATOR, review=SourceReview.UNREVIEWED),
        transport=Transport(TransportDisposition.EXACT),
    )
    readout = projection_gate(creator, target_identity=creator.reaction_identity,
                              target_direction=creator.reaction_direction)
    assert readout.disposition is ProjectionDisposition.REFUSED_UNREVIEWED


def test_projection_gate_licenses_a_matched_fragment_and_never_lists_an_unknown_subject():
    # NON-VACUOUS positive case + the omitted-facts guard: LICENSED_EXACT names only POSITIVE claim
    # subjects; an UNKNOWN claim's subject is never licensed (omitted facts stay omitted).
    o = _accepted_exact(claims=(
        _claim("elapsed time", "30 min at reflux"),
        ObservationClaim(ClaimStatus.UNKNOWN, "waste path", "nothing is established", "the waste path is undocumented"),
    ))
    readout = projection_gate(o, target_identity=o.reaction_identity, target_direction=o.reaction_direction)
    assert readout.disposition is ProjectionDisposition.LICENSED_EXACT
    assert readout.licensed
    assert "elapsed time" in readout.licensed_fields
    assert "waste path" not in readout.licensed_fields  # the UNKNOWN claim is never licensed


def test_projection_gate_partial_needs_a_reviewed_bridge():
    licensed = _accepted_exact(transport=Transport(TransportDisposition.PARTIAL,
                                                   mismatches=("grade differs",), reviewed_bridge_id="bridge-1"))
    readout = projection_gate(licensed, target_identity=licensed.reaction_identity,
                              target_direction=licensed.reaction_direction)
    assert readout.disposition is ProjectionDisposition.LICENSED_PARTIAL
    # UNKNOWN transport with no bridge is refused
    unknown = _accepted_exact(transport=Transport(TransportDisposition.UNKNOWN))
    refused = projection_gate(unknown, target_identity=unknown.reaction_identity,
                              target_direction=unknown.reaction_direction)
    assert refused.disposition is ProjectionDisposition.REFUSED_TRANSPORT
