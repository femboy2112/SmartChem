"""Regression tests for the adversarial findings against the evidence auditor.

An orthogonal red-team pass found six bypasses, all one disease: the rules trusted
the manifest to self-incriminate on the exact field being policed.  Three were
cheap dodges and are now closed; three are the irreducible boundary of a
*declarative* auditor and are documented on the certificate banner.  This file pins
both: the closed kills must stay closed, and the documented boundaries are pinned so
that if one is ever tightened the test flips and the change is made consciously.
"""
from __future__ import annotations

import pytest

from smartchem.contracts import ClaimKind, EvidenceStatus
from smartchem.evidence import (
    AuditOutcome,
    EvidenceRecord,
    ProbeManifest,
    ProvenanceTag,
    Role,
    SourceLockedValue,
    audit_manifest,
    rule_source_lock,
    rule_teeth,
)


def _rec(**kw) -> EvidenceRecord:
    kw.setdefault("claim_kind", ClaimKind.ANALOGUE)
    kw.setdefault("evidence_status", EvidenceStatus.STRUCTURAL_TOY)
    kw.setdefault("passed", True)
    return EvidenceRecord.build(**kw)


def _manifest(*records, claimed="floor", floor="floor", promoted="legitimized"):
    return ProbeManifest(
        schema="smartchem.evidence/probe-manifest-v1", program="demo",
        claimed_tier=claimed, floor_tier=floor, promoted_tier=promoted, records=records,
    )


# ============================ CLOSED: role-laundering (Finding 1) ==============
@pytest.mark.parametrize("kwargs", [
    {"agreement": True},
    {"discriminator": True},
    {"pairs_with": ("m",)},
])
def test_claim_only_payload_rejected_on_non_claim_record(kwargs):
    # A non-CLAIM record cannot wear a CLAIM's tell-tale fields to dodge the CLAIM
    # rules; construction refuses it (fail-closed → ManifestError on load).
    with pytest.raises(ValueError):
        _rec(probe="p", check="c", role=Role.CALIBRATION, **kwargs)


def test_over_reported_agreement_cannot_hide_as_calibration():
    # The exact Finding-1 manifest is now unconstructable: agreement on a CALIBRATION.
    with pytest.raises(ValueError):
        _rec(
            probe="p", check="the_real_claim", role=Role.CALIBRATION,
            claim_kind=ClaimKind.LITERAL, evidence_status=EvidenceStatus.ESTABLISHED,
            agreement=True, inputs=(ProvenanceTag("one_single_root"),),
        )


# ================= CLOSED: agreement=False common-mode dodge (Finding 2) =======
def test_single_bearing_over_report_refused_regardless_of_agreement_flag():
    rotten = _manifest(
        _rec(
            probe="p", check="c", role=Role.CLAIM, claim_kind=ClaimKind.LITERAL,
            evidence_status=EvidenceStatus.ESTABLISHED, passed=True, agreement=False,
            inputs=(ProvenanceTag("conformal_factor"),), scope_boundary="scoped",
            pairs_with=("m",),
        ),
        _rec(probe="p", check="m", role=Role.MUTATION, passed=True),
        _rec(probe="p", check="s", role=Role.SCOPE, scope_boundary="b"),
    )
    cert = audit_manifest(rotten)
    assert not cert.certified
    assert any("provenance-independence" in r for r in cert.refusals)


# ================= CLOSED: toy discriminator promotes (Finding 5) ==============
def test_structural_toy_discriminator_cannot_promote_tier():
    m = _manifest(
        _rec(
            probe="p", check="disc", role=Role.CLAIM, claim_kind=ClaimKind.LITERAL,
            evidence_status=EvidenceStatus.STRUCTURAL_TOY, passed=True,
            discriminator=True, scope_boundary="b", pairs_with=("m",),
            inputs=(ProvenanceTag("A"), ProvenanceTag("B")),
        ),
        _rec(probe="p", check="m", role=Role.MUTATION, passed=True),
        _rec(probe="p", check="s", role=Role.SCOPE, scope_boundary="b"),
        claimed="legitimized",
    )
    cert = audit_manifest(m)
    assert not cert.certified
    assert any("tier-boundary" in r for r in cert.refusals)


# ================= DOCUMENTED BOUNDARY: source aliasing (Finding 4) ============
def test_source_aliasing_is_a_documented_boundary():
    # Two DIFFERENT source strings that alias the same root read as independent.
    # The auditor cannot detect semantic aliasing; this is the emitter's honesty
    # obligation, stated on the banner. Pinned so a future tightening is deliberate.
    from smartchem.evidence.rules import rule_provenance_independence

    m = _manifest(
        _rec(
            probe="p", check="c", role=Role.CLAIM,
            evidence_status=EvidenceStatus.STRUCTURAL_TOY, agreement=True,
            inputs=(ProvenanceTag("Omega"), ProvenanceTag("Omega_relabeled")),
            scope_boundary="b", pairs_with=("m",),
        ),
    )
    assert rule_provenance_independence(m).outcome is AuditOutcome.PASS


# ================= DOCUMENTED BOUNDARY: numeric_result smuggling (Finding 3) ===
def test_numeric_result_smuggling_is_a_documented_boundary():
    # An unlocked number hidden in numeric_result (not empirical_values) escapes the
    # source-lock rule. Documented; emitters must declare cited numbers as empirical.
    m = _manifest(
        _rec(
            probe="p", check="c", role=Role.CALIBRATION,
            empirical_values=(),
            numeric_result={"cited_but_unlocked_reference_eV": 4.478},
        ),
    )
    assert rule_source_lock(m).outcome is AuditOutcome.PASS


# ================= DOCUMENTED BOUNDARY: Mode-B rubber-stamp mutation (F6) ======
def test_rubber_stamp_mutation_is_a_mode_b_boundary():
    # In Mode B the teeth verdict trusts the recorded mutation outcome; a no-op
    # mutation self-recorded as passed=True satisfies teeth. Mode A (re-run) closes it.
    m = _manifest(
        _rec(probe="p", check="claim", role=Role.CLAIM, pairs_with=("m",),
             inputs=(ProvenanceTag("A"), ProvenanceTag("B")), scope_boundary="b"),
        _rec(probe="p", check="m", role=Role.MUTATION, passed=True),
    )
    assert rule_teeth(m).outcome is AuditOutcome.PASS
