"""Fast regression pins over the committed DA-family evidence probe (:mod:`experiments.diels_alder_family_probe`).

Kept independent of the probe so a refactor cannot silently drop the frozen evidence. If ``validate()`` stops
firing, the DA family regressed; if the frozen hash moves, its measured behaviour changed -- re-audit before
re-freezing (in particular the ketene KILL and the search-seam control must not silently flip).
"""
from __future__ import annotations

import experiments.diels_alder_family_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_ketene_false_vouch_stays_closed():
    # the evil-morty CRITICAL kill: every enone/tetralone must remain UN-vouched.
    assert all(v == [] for v in probe.ketene_kill_closed().values())


def test_the_parent_da_and_norbornene_coverage_hold():
    assert probe.parent_da() == ["C6H10 -> C2H4 + C4H6"]
    assert probe.norbornene_genuine() == ["C7H10 -> C2H4 + C5H6"]


def test_the_provider_is_opt_in_and_the_seam_control_holds():
    assert probe.opt_in() is True
    assert probe.seam_integration() == {"with_da_provider": 1, "default_registry": 0}
