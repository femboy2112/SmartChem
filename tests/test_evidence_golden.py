"""B3 acceptance: the two golden fixtures, pinned by digest.

The §8-retraction manifest must REFUSE (specifically on teeth + provenance — the two
rules that would have blocked the original retraction), and a healthy probe must
CERTIFY at the floor tier.  The manifest digests are pinned so a silent edit to a
golden fixture is caught in CI; an intentional edit updates the pin here on purpose.
"""
from __future__ import annotations

from pathlib import Path

from smartchem.evidence import audit_manifest, load_manifest

_FIXTURES = Path(__file__).parent / "fixtures" / "evidence"


def test_section8_retraction_refuses_on_teeth_and_provenance():
    manifest = load_manifest(_FIXTURES / "section8_retraction.json")
    cert = audit_manifest(manifest)
    assert not cert.certified
    refused = {r.rule for r in cert.rule_results if r.outcome.value == "REFUSE"}
    # The two rules that alone would have blocked the original §8 retraction:
    assert "teeth" in refused
    assert "provenance-independence" in refused
    # Everything else in this fixture is clean, so it demonstrates those two rules
    # catch the retraction shape on their own.
    assert refused == {"teeth", "provenance-independence"}
    assert cert.tier_reported == "floor"


def test_healthy_probe_certifies_at_floor():
    manifest = load_manifest(_FIXTURES / "healthy_probe.json")
    cert = audit_manifest(manifest)
    assert cert.certified, cert.refusals
    assert cert.tier_reported == "floor"


def test_golden_manifest_digests_are_stable():
    # Determinism: loading the same fixture twice yields the same digest.
    for name in ("section8_retraction.json", "healthy_probe.json"):
        a = load_manifest(_FIXTURES / name).digest
        b = load_manifest(_FIXTURES / name).digest
        assert a == b
