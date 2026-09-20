"""Fast regression pins over the committed alkyne-DA-family evidence probe
(:mod:`experiments.alkyne_diels_alder_family_probe`).

Kept independent of the probe so a refactor cannot silently drop the frozen evidence. If ``validate()`` stops
firing, the alkyne-dienophile family regressed; if the frozen hash moves, its measured behaviour changed --
re-audit before re-freezing (in particular the 1,4 vs 1,3 chemistry and the sibling-family non-poaching control
must not silently flip).
"""
from __future__ import annotations

import experiments.alkyne_diels_alder_family_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_parent_alkyne_da_is_the_verified_1_4_chemistry():
    assert probe.parent_alkyne_da() == ["C6H8 -> C2H2 + C4H6"]
    assert probe.alkene_pattern_is_not_matched() == []


def test_the_provider_is_opt_in_and_the_seam_control_holds():
    assert probe.opt_in() is True
    assert probe.seam_integration() == {"with_alkyne_da_provider": 1, "default_registry": 0}


def test_the_two_da_families_do_not_cross_poach():
    result = probe.sibling_families_do_not_cross_poach()
    assert result == {"alkene_provider_on_1_4_chd": [], "alkyne_provider_on_cyclohexene": []}


def test_the_four_pre_existing_classes_stay_not_poached():
    assert all(v == [] for v in probe.four_classes_not_poached().values())
