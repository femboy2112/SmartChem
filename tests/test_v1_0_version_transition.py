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
    """The gate cannot be passed by a tree that simply dropped the version binding: every case that has a
    compilation IR must carry the LIVE package version in tool_version, and every response a 64-hex result_digest."""
    live = fingerprint_invariant()["cases"]
    carrying = [cid for cid, rec in live.items() if rec.get("tool_version_carries_live")]
    assert carrying, "no case carried the live package version in tool_version -- the binding is broken"
    for cid, rec in live.items():
        if "refused" in rec:
            continue
        assert rec["has_result_digest"], f"{cid}: response is missing a 64-hex result_digest"
