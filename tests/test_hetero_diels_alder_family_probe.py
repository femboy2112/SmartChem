"""Fast regression pins over the committed hetero-DA-family evidence probe
(:mod:`experiments.hetero_diels_alder_family_probe`).

Kept independent of the probe so a refactor cannot silently drop the frozen evidence.  If ``validate()`` stops
firing, a heteroatom-dienophile family regressed; if the frozen hash moves, its measured behaviour changed --
re-audit before re-freezing (in particular the aza/oxa product isomers and the four-family non-cross-poach control
must not silently flip).
"""
from __future__ import annotations

import experiments.hetero_diels_alder_family_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_parent_hetero_disconnections_are_the_verified_chemistry():
    assert probe.parent_aza_da() == ["C5H9N -> CH3N + C4H6"]
    assert probe.parent_oxa_da() == ["C5H8O -> CH2O + C4H6"]


def test_both_providers_are_opt_in_and_the_seam_controls_hold():
    assert all(probe.opt_in().values())
    assert probe.seam_integration() == {"aza": {"with_provider": 1, "default_registry": 0},
                                        "oxa": {"with_provider": 1, "default_registry": 0}}


def test_no_da_family_cross_poaches_another():
    assert all(v == [] for v in probe.families_do_not_cross_poach().values())


def test_near_misses_and_pre_existing_classes_stay_not_matched():
    assert all(v == [] for v in probe.negatives_not_matched().values())
    assert all(v == [] for v in probe.classes_not_poached().values())
