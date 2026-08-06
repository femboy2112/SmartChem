"""Auditor aggregation, the no-upgrade invariant, and manifest loading (Mode B)."""
from __future__ import annotations

import json

import pytest

from smartchem.contracts import ClaimKind, EvidenceStatus
from smartchem.evidence import (
    EvidenceRecord,
    ManifestError,
    ProbeManifest,
    ProvenanceTag,
    Role,
    SourceLockedValue,
    audit_manifest,
    evidence_rank,
    load_manifest,
    load_manifest_dir,
    manifest_from_mapping,
)


def _rec(**kw) -> EvidenceRecord:
    kw.setdefault("claim_kind", ClaimKind.ANALOGUE)
    kw.setdefault("evidence_status", EvidenceStatus.STRUCTURAL_TOY)
    kw.setdefault("passed", True)
    return EvidenceRecord.build(**kw)


def _healthy() -> ProbeManifest:
    return ProbeManifest(
        schema="smartchem.evidence/probe-manifest-v1",
        program="demo",
        claimed_tier="floor",
        floor_tier="floor",
        promoted_tier="legitimized",
        records=(
            _rec(probe="p", check="claim", role=Role.CLAIM, agreement=True,
                 inputs=(ProvenanceTag("A"), ProvenanceTag("B")),
                 scope_boundary="toy limit", pairs_with=("mut",)),
            _rec(probe="p", check="mut", role=Role.MUTATION, passed=True),
            _rec(probe="p", check="scope", role=Role.SCOPE, scope_boundary="the boundary"),
        ),
    )


def test_healthy_manifest_certifies_at_floor():
    cert = audit_manifest(_healthy())
    assert cert.certified
    assert cert.tier_reported == "floor"
    assert cert.refusals == ()


def test_any_single_refuse_refuses_the_whole_manifest():
    # break only source-lock; everything else is clean.
    m = _healthy()
    broken = ProbeManifest(
        schema=m.schema, program=m.program, claimed_tier=m.claimed_tier,
        floor_tier=m.floor_tier, promoted_tier=m.promoted_tier,
        records=m.records + (
            _rec(probe="p", check="cal", role=Role.CALIBRATION,
                 empirical_values=(SourceLockedValue("x", 1.0, ""),)),
        ),
    )
    cert = audit_manifest(broken)
    assert not cert.certified
    assert cert.tier_reported == "floor"
    assert any("source-lock" in r for r in cert.refusals)


def test_certificate_never_reports_a_status_above_the_strongest_declared():
    # The no-label-borrowing invariant: the auditor aggregates declared statuses and
    # never invents a stronger one.
    cert = audit_manifest(_healthy())
    declared_max = max(
        evidence_rank(r.evidence_status) for r in _healthy().records
    )
    for status_name, _count in cert.evidence_ledger:
        assert evidence_rank(EvidenceStatus(status_name)) <= declared_max


def test_casualties_are_the_union_of_scope_boundaries():
    cert = audit_manifest(_healthy())
    assert set(cert.casualties) == {"toy limit", "the boundary"}


def test_certificate_digest_is_deterministic():
    assert audit_manifest(_healthy()).digest == audit_manifest(_healthy()).digest


# ------------------------------------------------------- manifest loading ------
def _healthy_mapping() -> dict:
    return {
        "schema": "smartchem.evidence/probe-manifest-v1",
        "program": "demo",
        "claimed_tier": "floor",
        "floor_tier": "floor",
        "promoted_tier": "legitimized",
        "records": [
            {"probe": "p", "check": "claim", "role": "CLAIM", "claim_kind": "ANALOGUE",
             "evidence_status": "STRUCTURAL_TOY", "passed": True, "agreement": True,
             "inputs": [{"source": "A"}, {"source": "B"}],
             "scope_boundary": "toy limit", "pairs_with": ["mut"]},
            {"probe": "p", "check": "mut", "role": "MUTATION", "claim_kind": "ANALOGUE",
             "evidence_status": "STRUCTURAL_TOY", "passed": True},
            {"probe": "p", "check": "scope", "role": "SCOPE", "claim_kind": "ANALOGUE",
             "evidence_status": "STRUCTURAL_TOY", "passed": True, "scope_boundary": "b"},
        ],
    }


def test_manifest_from_mapping_roundtrips_and_certifies():
    manifest = manifest_from_mapping(_healthy_mapping())
    assert audit_manifest(manifest).certified


def test_load_manifest_from_file(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps(_healthy_mapping()), encoding="utf-8")
    manifest = load_manifest(path)
    assert audit_manifest(manifest).certified


def test_load_manifest_dir(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(_healthy_mapping()), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(_healthy_mapping()), encoding="utf-8")
    manifests = load_manifest_dir(tmp_path)
    assert len(manifests) == 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("schema"),
        lambda d: d.__setitem__("schema", "wrong/schema"),
        lambda d: d.pop("program"),
        lambda d: d["records"][0].__setitem__("role", "BOGUS"),
        lambda d: d["records"][0].pop("probe"),
        lambda d: d["records"][0].__setitem__("passed", "yes"),
    ],
)
def test_load_rejects_malformed_manifest(mutate):
    data = _healthy_mapping()
    mutate(data)
    with pytest.raises(ManifestError):
        manifest_from_mapping(data)


def test_load_rejects_non_finite_numbers(tmp_path):
    path = tmp_path / "nan.json"
    path.write_text(
        '{"schema":"smartchem.evidence/probe-manifest-v1","program":"d",'
        '"claimed_tier":"floor","floor_tier":"floor","promoted_tier":"x",'
        '"records":[{"probe":"p","check":"c","role":"SCOPE","claim_kind":"ANALOGUE",'
        '"evidence_status":"STRUCTURAL_TOY","passed":true,'
        '"numeric_result":{"v":NaN}}]}',
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_manifest(path)
