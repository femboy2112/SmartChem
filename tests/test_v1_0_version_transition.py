"""The version-transition law, enforced as a durable gate.

COMPATIBILITY.md section 2.2 + section 9: a PACKAGE version bump moves exactly the tool-version-bound fields
(``tool_version``, ``result_digest``, the implementation digest, the ``--version`` banner) and NOTHING ELSE.  The
field-by-field proof of the actual 0.9.5a1 -> 1.0.0rc1 transition lives in the forensic
``experiments/v1_0_version_transition.py --diff`` run (release record V1_0_RELEASE_GATE.md); this test is the
DURABLE half: it freezes the VERSION-INDEPENDENT projection of a representative corpus (every payload with
``tool_version`` / ``result_digest`` stripped) and fails the build the instant a SEMANTIC field moves -- a verdict,
a route digest, a readiness tier, a schema id, a capability assessment.  A pure version bump leaves it silent; that
is exactly why it survives rc1 -> 1.0.0 with no edit.
"""
from __future__ import annotations

import json

from experiments.v1_0_version_transition import INVARIANT_GOLDEN, fingerprint_invariant


def _golden() -> dict:
    return json.loads(INVARIANT_GOLDEN.read_text(encoding="utf-8"))


def test_golden_exists():
    assert INVARIANT_GOLDEN.exists(), (
        f"{INVARIANT_GOLDEN} missing; run experiments/v1_0_version_transition.py --write-golden")


def test_semantic_content_is_unmoved_by_the_version_bump():
    """The whole-surface invariant: every case's version-independent fingerprint matches the frozen golden.
    Re-freeze (--write-golden) is sanctioned ONLY for a deliberate semantic change, never to silence this."""
    frozen, live = _golden(), fingerprint_invariant()
    assert live == frozen, (
        "version-independent fingerprint drift -- a SEMANTIC field moved (not just the version). "
        "Cases differing: "
        + ", ".join(sorted(k for k in set(frozen["cases"]) | set(live["cases"])
                           if frozen["cases"].get(k) != live["cases"].get(k)))
    )


def test_version_binding_is_live_on_route_bearing_cases():
    """The gate cannot be passed by a tree that simply dropped the version binding: EVERY case that has a
    compilation IR must carry the LIVE package version in tool_version, and every non-refused response a 64-hex
    result_digest. The golden's `tool_version_carries_live` flag defines the IR-bearing set version-independently
    (it is `tool_version == __version__`, true for an IR case at any version), so this asserts completeness, not
    merely existence."""
    golden = _golden()["cases"]
    live = fingerprint_invariant()["cases"]
    ir_bearing = [cid for cid, g in golden.items() if g.get("tool_version_carries_live")]
    assert ir_bearing, "golden records no IR-bearing case -- the fixture is broken"
    for cid in ir_bearing:
        assert live[cid].get("tool_version_carries_live"), (
            f"{cid}: an IR-bearing case stopped carrying the live package version in tool_version")
    for cid, g in golden.items():
        if "refused" not in g:
            assert live[cid]["has_result_digest"], f"{cid}: response is missing a 64-hex result_digest"
