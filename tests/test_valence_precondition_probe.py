"""Fast regression pins over the committed valence-precondition evidence probe.

Kept independent of the probe so a refactor cannot silently drop the frozen evidence. If ``validate()``
stops firing, the valence gate regressed; if the frozen hash moves, its measured behaviour changed --
re-audit before re-freezing (in particular the pentavalent-carbon KILL and the no-false-reject of real
hypervalent chemistry must not silently flip).
"""
from __future__ import annotations

import experiments.valence_precondition_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_pentavalent_carbon_fail_open_stays_closed():
    assert all(probe.impossible_rejected().values())


def test_no_real_chemistry_is_false_rejected():
    # both adversary kills: net-neutral charge-separated (CO/ozone) + hypervalent halogen/iodine reagents,
    # plus correctly-valenced expanded-octet species.
    assert all(probe.real_chemistry_accepted().values())
    assert all(probe.hand_built_hypervalent_accepted().values())
