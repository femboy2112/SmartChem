"""B1 acceptance: each of the five auditor rules, with hand-authored manifests.

Every fixture here is built from raw dataclass construction; none imports a rule's
own construction helper (there are none — the rules are pure functions over plain
data).  Each rule gets at least one manifest it must PASS and one it must REFUSE.
"""
from __future__ import annotations

from smartchem.contracts import ClaimKind, EvidenceStatus
from smartchem.evidence import (
    AuditOutcome,
    EvidenceRecord,
    ProbeManifest,
    ProvenanceTag,
    Role,
    SourceLockedValue,
    rule_provenance_independence,
    rule_scope,
    rule_source_lock,
    rule_teeth,
    rule_tier_boundary,
)


def _rec(**kw) -> EvidenceRecord:
    kw.setdefault("claim_kind", ClaimKind.ANALOGUE)
    kw.setdefault("evidence_status", EvidenceStatus.STRUCTURAL_TOY)
    kw.setdefault("passed", True)
    return EvidenceRecord.build(**kw)


def _manifest(*records, claimed="floor", floor="floor", promoted="legitimized") -> ProbeManifest:
    return ProbeManifest(
        schema="smartchem.evidence/probe-manifest-v1",
        program="demo",
        claimed_tier=claimed,
        floor_tier=floor,
        promoted_tier=promoted,
        records=records,
    )


# ---------------------------------------------------------------- teeth --------
def test_teeth_passes_with_a_breaking_mutation():
    m = _manifest(
        _rec(probe="p", check="claim", role=Role.CLAIM, pairs_with=("mut",)),
        _rec(probe="p", check="mut", role=Role.MUTATION, passed=True),
    )
    assert rule_teeth(m).outcome is AuditOutcome.PASS


def test_teeth_refuses_claim_with_no_mutation():
    m = _manifest(_rec(probe="p", check="claim", role=Role.CLAIM, pairs_with=()))
    assert rule_teeth(m).outcome is AuditOutcome.REFUSE


def test_teeth_refuses_mutation_that_did_not_break():
    m = _manifest(
        _rec(probe="p", check="claim", role=Role.CLAIM, pairs_with=("mut",)),
        _rec(probe="p", check="mut", role=Role.MUTATION, passed=False),
    )
    assert rule_teeth(m).outcome is AuditOutcome.REFUSE


def test_teeth_refuses_absent_or_misroled_mutation():
    absent = _manifest(_rec(probe="p", check="claim", role=Role.CLAIM, pairs_with=("gone",)))
    assert rule_teeth(absent).outcome is AuditOutcome.REFUSE
    misroled = _manifest(
        _rec(probe="p", check="claim", role=Role.CLAIM, pairs_with=("scope",)),
        _rec(probe="p", check="scope", role=Role.SCOPE, scope_boundary="b"),
    )
    assert rule_teeth(misroled).outcome is AuditOutcome.REFUSE


# ------------------------------------------------ provenance-independence ------
def test_provenance_passes_with_two_distinct_sources():
    m = _manifest(
        _rec(
            probe="p", check="claim", role=Role.CLAIM, agreement=True,
            inputs=(ProvenanceTag("A"), ProvenanceTag("B")), scope_boundary="b",
        )
    )
    assert rule_provenance_independence(m).outcome is AuditOutcome.PASS


def test_provenance_refuses_common_mode_over_reported():
    m = _manifest(
        _rec(
            probe="p", check="claim", role=Role.CLAIM, agreement=True,
            evidence_status=EvidenceStatus.VALIDATED_WITHIN_REGIME,
            inputs=(ProvenanceTag("Omega"), ProvenanceTag("Omega", "rearranged")),
            scope_boundary="b",
        )
    )
    assert rule_provenance_independence(m).outcome is AuditOutcome.REFUSE


def test_provenance_flags_honest_common_mode_at_toy_with_scope():
    m = _manifest(
        _rec(
            probe="p", check="claim", role=Role.CLAIM, agreement=True,
            evidence_status=EvidenceStatus.STRUCTURAL_TOY,
            inputs=(ProvenanceTag("Omega"),),
            scope_boundary="common-mode acknowledged: single-source identity",
        )
    )
    assert rule_provenance_independence(m).outcome is AuditOutcome.FLAG


def test_provenance_refuses_common_mode_without_scope():
    m = _manifest(
        _rec(
            probe="p", check="claim", role=Role.CLAIM, agreement=True,
            evidence_status=EvidenceStatus.STRUCTURAL_TOY,
            inputs=(ProvenanceTag("Omega"),), scope_boundary="",
        )
    )
    assert rule_provenance_independence(m).outcome is AuditOutcome.REFUSE


def test_provenance_refuses_single_bearing_over_report_even_without_agreement_flag():
    # The self-labelling dodge: a strong claim on one provenance source that declines
    # to call itself an agreement must still be refused (structural trigger).
    m = _manifest(
        _rec(
            probe="p", check="claim", role=Role.CLAIM, agreement=False,
            evidence_status=EvidenceStatus.ESTABLISHED,
            inputs=(ProvenanceTag("Omega"),), scope_boundary="b",
        )
    )
    assert rule_provenance_independence(m).outcome is AuditOutcome.REFUSE


def test_provenance_passes_honestly_weak_single_bearing_non_agreement():
    m = _manifest(
        _rec(
            probe="p", check="claim", role=Role.CLAIM, agreement=False,
            evidence_status=EvidenceStatus.STRUCTURAL_TOY,
            inputs=(ProvenanceTag("Omega"),), scope_boundary="b",
        )
    )
    assert rule_provenance_independence(m).outcome is AuditOutcome.PASS


# ------------------------------------------------------------ source-lock ------
def test_source_lock_passes_when_locked():
    m = _manifest(
        _rec(
            probe="p", check="c", role=Role.CALIBRATION,
            empirical_values=(SourceLockedValue("alpha", 137.0, "CODATA"),),
        )
    )
    assert rule_source_lock(m).outcome is AuditOutcome.PASS


def test_source_lock_refuses_empty_and_whitespace_sources():
    empty = _manifest(
        _rec(probe="p", check="c", role=Role.CALIBRATION,
             empirical_values=(SourceLockedValue("alpha", 137.0, ""),))
    )
    assert rule_source_lock(empty).outcome is AuditOutcome.REFUSE
    blank = _manifest(
        _rec(probe="p", check="c", role=Role.CALIBRATION,
             empirical_values=(SourceLockedValue("alpha", 137.0, "   "),))
    )
    assert rule_source_lock(blank).outcome is AuditOutcome.REFUSE


# ------------------------------------------------------------------ scope ------
def test_scope_passes_with_scoped_claim_and_scope_record():
    m = _manifest(
        _rec(probe="p", check="claim", role=Role.CLAIM, pairs_with=("mut",), scope_boundary="b"),
        _rec(probe="p", check="mut", role=Role.MUTATION),
        _rec(probe="p", check="scope", role=Role.SCOPE, scope_boundary="the boundary"),
    )
    assert rule_scope(m).outcome is AuditOutcome.PASS


def test_scope_refuses_unscoped_claim():
    m = _manifest(
        _rec(probe="p", check="claim", role=Role.CLAIM, scope_boundary=""),
        _rec(probe="p", check="scope", role=Role.SCOPE, scope_boundary="b"),
    )
    assert rule_scope(m).outcome is AuditOutcome.REFUSE


def test_scope_refuses_probe_without_scope_record():
    m = _manifest(_rec(probe="p", check="claim", role=Role.CLAIM, scope_boundary="b"))
    assert rule_scope(m).outcome is AuditOutcome.REFUSE


# ---------------------------------------------------------- tier-boundary ------
def test_tier_passes_at_floor():
    m = _manifest(claimed="floor")
    assert rule_tier_boundary(m).outcome is AuditOutcome.PASS


def test_tier_passes_promoted_with_literal_passed_discriminator():
    m = _manifest(
        _rec(
            probe="p", check="disc", role=Role.CLAIM, claim_kind=ClaimKind.LITERAL,
            evidence_status=EvidenceStatus.VALIDATED_WITHIN_REGIME,
            passed=True, discriminator=True, scope_boundary="b",
        ),
        claimed="legitimized",
    )
    assert rule_tier_boundary(m).outcome is AuditOutcome.PASS


def test_tier_refuses_promoted_without_discriminator():
    m = _manifest(claimed="legitimized")
    assert rule_tier_boundary(m).outcome is AuditOutcome.REFUSE


def test_tier_refuses_discriminator_that_is_not_literal_or_not_passed():
    not_literal = _manifest(
        _rec(probe="p", check="d", role=Role.CLAIM, claim_kind=ClaimKind.ANALOGUE,
             passed=True, discriminator=True, scope_boundary="b"),
        claimed="legitimized",
    )
    assert rule_tier_boundary(not_literal).outcome is AuditOutcome.REFUSE
    not_passed = _manifest(
        _rec(probe="p", check="d", role=Role.CLAIM, claim_kind=ClaimKind.LITERAL,
             passed=False, discriminator=True, scope_boundary="b"),
        claimed="legitimized",
    )
    assert rule_tier_boundary(not_passed).outcome is AuditOutcome.REFUSE


def test_tier_refuses_unknown_claimed_tier():
    m = _manifest(claimed="transcended")
    assert rule_tier_boundary(m).outcome is AuditOutcome.REFUSE
