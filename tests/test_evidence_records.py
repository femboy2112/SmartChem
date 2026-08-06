"""B0 acceptance: the evidence data model digests, validates, and ranks correctly.

These tests construct records and manifests by hand and never import an auditor
rule — the reflexive discipline (the auditor's own tests must not share code with
the auditor).
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from smartchem.contracts import ClaimKind, EvidenceStatus
from smartchem.evidence import (
    EvidenceRecord,
    ProbeManifest,
    ProvenanceTag,
    Role,
    SourceLockedValue,
    evidence_rank,
)


def _record(**overrides) -> EvidenceRecord:
    base = dict(
        probe="p",
        check="c",
        role=Role.CLAIM,
        claim_kind=ClaimKind.ANALOGUE,
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
        passed=True,
        inputs=(ProvenanceTag("A"), ProvenanceTag("B")),
        empirical_values=(SourceLockedValue("x", 1.0, "arXiv:1"),),
        numeric_result={"k": 1},
        scope_boundary="toy limit",
        pairs_with=("m",),
        agreement=True,
        discriminator=False,
    )
    base.update(overrides)
    return EvidenceRecord.build(**base)


def test_record_digest_is_deterministic():
    a = _record()
    b = _record()
    assert a.digest == b.digest
    assert a.digest == a.digest


@pytest.mark.parametrize(
    "field, value",
    [
        ("probe", "other"),
        ("check", "other"),
        ("claim_kind", ClaimKind.LITERAL),
        ("evidence_status", EvidenceStatus.CALIBRATED),
        ("passed", False),
        ("scope_boundary", "different boundary"),
        ("pairs_with", ("m", "n")),
        ("agreement", False),
        ("discriminator", True),
        ("numeric_result", '{"k":2}'),
    ],
)
def test_record_digest_changes_when_any_field_changes(field, value):
    base = _record()  # a valid CLAIM (carries CLAIM-only fields)
    mutated = replace(base, **{field: value})
    assert mutated.digest != base.digest


def test_record_digest_distinguishes_roles():
    # Role sensitivity needs two coherent records (a CLAIM cannot be re-roled while
    # holding CLAIM-only fields), so compare two records that differ only in role.
    scope = EvidenceRecord.build(
        probe="p", check="c", role=Role.SCOPE, claim_kind=ClaimKind.ANALOGUE,
        evidence_status=EvidenceStatus.STRUCTURAL_TOY, passed=True,
    )
    calibration = replace(scope, role=Role.CALIBRATION)
    assert scope.digest != calibration.digest


def test_record_digest_changes_with_inputs_and_values():
    base = _record()
    assert replace(base, inputs=(ProvenanceTag("A"),)).digest != base.digest
    assert (
        replace(base, empirical_values=(SourceLockedValue("x", 2.0, "arXiv:1"),)).digest
        != base.digest
    )


def test_manifest_digest_is_deterministic():
    def build() -> ProbeManifest:
        return ProbeManifest(
            schema="smartchem.evidence/probe-manifest-v1",
            program="demo",
            claimed_tier="floor",
            floor_tier="floor",
            promoted_tier="legitimized",
            records=(_record(check="a"), _record(check="b")),
        )

    assert build().digest == build().digest


def test_evidence_rank_is_a_total_order_over_every_status():
    ranks = {status: evidence_rank(status) for status in EvidenceStatus}
    assert len(set(ranks.values())) == len(EvidenceStatus)  # all distinct
    assert ranks[EvidenceStatus.ESTABLISHED] > ranks[EvidenceStatus.STRUCTURAL_TOY]
    assert ranks[EvidenceStatus.STRUCTURAL_TOY] > ranks[EvidenceStatus.UNSUPPORTED]
    assert ranks[EvidenceStatus.CALIBRATED] > ranks[EvidenceStatus.EXPERIMENTAL]


def test_source_locked_value_lock_detection():
    assert SourceLockedValue("x", 1.0, "arXiv:1").is_locked
    assert not SourceLockedValue("x", 1.0, "").is_locked
    assert not SourceLockedValue("x", 1.0, "   ").is_locked


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"probe": ""}, ValueError),
        ({"check": ""}, ValueError),
        ({"role": "CLAIM"}, TypeError),
        ({"claim_kind": "LITERAL"}, TypeError),
        ({"evidence_status": "STRUCTURAL_TOY"}, TypeError),
        ({"passed": 1}, TypeError),
        ({"pairs_with": ("",)}, TypeError),
    ],
)
def test_record_post_init_rejects_malformed(overrides, error):
    with pytest.raises(error):
        _record(**overrides)


def test_record_rejects_nan_empirical_value():
    with pytest.raises(ValueError):
        SourceLockedValue("x", float("nan"), "arXiv:1")


def test_record_rejects_non_object_numeric_result():
    with pytest.raises(ValueError):
        EvidenceRecord(
            probe="p",
            check="c",
            role=Role.SCOPE,
            claim_kind=ClaimKind.ANALOGUE,
            evidence_status=EvidenceStatus.STRUCTURAL_TOY,
            passed=True,
            numeric_result="[1, 2, 3]",
        )


def test_manifest_rejects_duplicate_probe_check():
    dup = _record(probe="p", check="same")
    with pytest.raises(ValueError):
        ProbeManifest(
            schema="smartchem.evidence/probe-manifest-v1",
            program="demo",
            claimed_tier="floor",
            floor_tier="floor",
            promoted_tier="legitimized",
            records=(dup, replace(dup)),
        )


def test_manifest_rejects_equal_floor_and_promoted_tier():
    with pytest.raises(ValueError):
        ProbeManifest(
            schema="smartchem.evidence/probe-manifest-v1",
            program="demo",
            claimed_tier="floor",
            floor_tier="floor",
            promoted_tier="floor",
            records=(),
        )
