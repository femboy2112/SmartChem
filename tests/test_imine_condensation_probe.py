"""Drift guard for the committed IMINE-CONDENSATION-01 evidence (experiments/imine_condensation_probe.py).

The probe freezes the recognizer's verdict over its positive/adversarial corpus; this test fails if that
behaviour silently changes (a re-freeze must be a deliberate, reviewed edit), and independently re-asserts the
no-false-VOUCH cardinal.
"""
from __future__ import annotations

from experiments import imine_condensation_probe as probe


def test_frozen_hash_matches_current_behaviour():
    assert probe.content_hash() == probe.FROZEN_HASH, (
        "imine-condensation recognizer behaviour drifted from the frozen corpus; "
        "if intended, re-run `python -m experiments.imine_condensation_probe` and update FROZEN_HASH"
    )


def test_no_false_vouch_cardinal_holds_over_the_corpus():
    probe.validate()  # every pos_ vouches IMINE; no neg_ does
