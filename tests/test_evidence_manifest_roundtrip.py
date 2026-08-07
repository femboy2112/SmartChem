"""Round-trip law for ``manifest_to_mapping`` — the exact inverse of ``manifest_from_mapping``.

The serializer exists so a Python emitter can build typed, construction-validated records and
emit a guaranteed-conformant manifest.  Its correctness contract is a single equation:
``manifest_from_mapping(manifest_to_mapping(m)).digest == m.digest`` for every manifest the
loader could have produced.  The decisive evidence is the pass over the *independently
authored* golden fixtures: a serializer that merely inverted its own example could pass the
example test yet mangle a hand-written manifest — the fixtures close that gap.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartchem.evidence import (
    example_manifest,
    load_manifest,
    manifest_from_mapping,
    manifest_to_mapping,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "evidence"


def test_roundtrip_digest_stable_on_built_example():
    m = example_manifest()
    back = manifest_from_mapping(manifest_to_mapping(m))
    assert back.digest == m.digest
    assert back == m


@pytest.mark.parametrize("fixture", ["healthy_probe.json", "section8_retraction.json"])
def test_roundtrip_digest_stable_on_independently_authored_fixtures(fixture):
    # Authored by hand / a prior session, loaded by the loader, then round-tripped exactly.
    # Independent authorship makes this NON-common-mode: it cannot be satisfied by a
    # serializer that only knows how to invert its own example.
    original = load_manifest(_FIXTURES / fixture)
    back = manifest_from_mapping(manifest_to_mapping(original))
    assert back.digest == original.digest
    assert back == original


def test_to_mapping_is_json_serializable_and_omits_defaults():
    mapping = manifest_to_mapping(example_manifest())
    assert json.loads(json.dumps(mapping)) == mapping  # pure JSON, no exotic types
    # The SCOPE record has no numeric_result / inputs / empirical_values / flags: those
    # default keys must be OMITTED (not emitted empty), so the JSON reads hand-written.
    scope = next(r for r in mapping["records"] if r["check"] == "declared_scope")
    for omitted in ("numeric_result", "inputs", "empirical_values", "agreement", "pairs_with"):
        assert omitted not in scope


def test_to_mapping_rejects_a_non_manifest():
    with pytest.raises(TypeError, match="exact ProbeManifest"):
        manifest_to_mapping(object())


def test_raw_constructor_canonicalizes_numeric_result_for_a_stable_roundtrip():
    # The raw EvidenceRecord constructor (bypassing .build) once admitted non-canonical
    # numeric_result text whose digest did not survive serialize->reload; __post_init__ now
    # canonicalizes it, so the digest depends on content, not incoming key order/spacing.
    # (Adversarial probe, 2026-08-07: closes the round-trip footgun in the typed-builder path.)
    from smartchem.contracts import ClaimKind, EvidenceStatus
    from smartchem.evidence import MANIFEST_SCHEMA, EvidenceRecord, ProbeManifest, Role

    record = EvidenceRecord(
        probe="p",
        check="c",
        role=Role.CALIBRATION,
        claim_kind=ClaimKind.LITERAL,
        evidence_status=EvidenceStatus.CALIBRATED,
        passed=True,
        numeric_result='{"b": 1, "a": 2}',  # unsorted, spaced — deliberately non-canonical
    )
    assert record.numeric_result == '{"a":2,"b":1}'  # normalized on construction
    m = ProbeManifest(MANIFEST_SCHEMA, "prog", "floor", "floor", "legit", (record,))
    assert manifest_from_mapping(manifest_to_mapping(m)).digest == m.digest
