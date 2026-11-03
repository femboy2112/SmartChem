"""Paired drift test for :mod:`experiments.sn2_recognition_probe` (#112).

The probe is committed frozen evidence; this test fails if the recognizer's verdict over the probe corpus
changes silently (the frozen hash drifts) or if the no-false-VOUCH cardinal is ever violated.  Re-freeze
``FROZEN_HASH`` ONLY on an intended, reviewed behaviour change.
"""
from __future__ import annotations

from experiments import sn2_recognition_probe as probe


def test_frozen_hash_is_stable():
    assert probe.content_hash() == probe.FROZEN_HASH, (
        "SN2 recognizer behaviour drifted over the probe corpus; re-freeze FROZEN_HASH only if intended"
    )


def test_validate_passes_the_no_false_vouch_cardinal():
    probe.validate()  # every pos_ vouches SN2; every neg_/deferred_ does not
