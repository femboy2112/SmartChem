"""FREEZE decision 3: catalyst-procurement obtainability generalized to be PROFILE-relative.

``route_catalyst_blockers`` gained an optional ``allowed_tiers`` parameter; the default (:data:`KITCHEN_TIERS`)
must reproduce the pre-existing poor-man behavior byte-for-byte (existing callers/tests pin the default-path
message text), while a caller with a different capability profile -- a lab that legitimately owns INDUSTRIAL
reagents, or a stricter profile that excludes e.g. POOL_GARDEN -- gets the SAME burden-of-proof-flip algorithm
run against ITS set instead.  ``is_kitchen_obtainable`` is now just ``is_obtainable_under(tier, KITCHEN_TIERS)``;
this file also pins that re-expression didn't change its answers.
"""
from __future__ import annotations

from smartchem.conditions import ConditionEnvelope
from smartchem.contracts import EvidenceStatus
from smartchem.data.reagents import Availability
from smartchem.experiment import catalyst_availability as catalyst_availability_mod
from smartchem.experiment.catalyst_availability import (
    KITCHEN_TIERS,
    catalyst_availability,
    is_kitchen_obtainable,
    is_obtainable_under,
    route_catalyst_blockers,
)

ALL_TIERS: frozenset[Availability] = frozenset(Availability)
LAB_TIERS: frozenset[Availability] = ALL_TIERS  # a lab profile: everything, incl. INDUSTRIAL
NO_POOL_GARDEN_TIERS: frozenset[Availability] = frozenset(
    a for a in Availability if a is not Availability.POOL_GARDEN
)


class _FakeStep:
    def __init__(self, env):
        self.envelope = env


class _FakeRoute:
    def __init__(self, envs):
        self.steps = [_FakeStep(e) for e in envs]


def _declaring(*catalysts: str) -> ConditionEnvelope:
    if not catalysts:
        return ConditionEnvelope.unknown()
    return ConditionEnvelope(
        catalysts=tuple(catalysts), medium="neat", status=EvidenceStatus.EXPERIMENTAL, provenance="test"
    )


# --- (a) default behavior is UNCHANGED ----------------------------------------------------------------------------


def test_default_kitchen_catalyst_is_obtainable_and_unblocked():
    assert catalyst_availability("vinegar") is Availability.GROCERY
    assert catalyst_availability("sulfuric acid") is Availability.HARDWARE
    assert route_catalyst_blockers(_FakeRoute([_declaring("vinegar")])) == ()
    assert route_catalyst_blockers(_FakeRoute([_declaring("sulfuric acid")])) == ()
    # calling with no allowed_tiers argument at all is the same default-path call
    assert route_catalyst_blockers(_FakeRoute([_declaring("sulfuric acid")]), KITCHEN_TIERS) == ()


def test_default_industrial_catalyst_is_blocked_with_the_pinned_message():
    blocked = route_catalyst_blockers(_FakeRoute([_declaring("Pd/C")]))
    assert blocked == ("catalyst not kitchen-obtainable: Pd/C [industrial]",)


# --- (b) a lab profile (incl. INDUSTRIAL) admits the industrial catalyst -------------------------------------------


def test_lab_profile_including_industrial_admits_the_industrial_catalyst():
    assert route_catalyst_blockers(_FakeRoute([_declaring("Pd/C")]), LAB_TIERS) == ()
    assert is_obtainable_under(Availability.INDUSTRIAL, LAB_TIERS) is True


# --- (c) a stricter profile blocks a POOL_GARDEN catalyst the default kitchen would allow --------------------------


def test_stricter_profile_excluding_pool_garden_blocks_a_pool_garden_catalyst(monkeypatch):
    # No live catalog entry is currently POOL_GARDEN-tier (the real commodity table only reaches HARDWARE/
    # INDUSTRIAL for this module today), so the profile-relative ALGORITHM is exercised directly against a
    # positively-classified POOL_GARDEN tier via a monkeypatched lookup -- this stays a fair test of the flip
    # logic itself (route_catalyst_blockers's own `catalyst_availability` call), not of the catalog's coverage.
    fake_name = "copper pool algaecide"

    def _fake_lookup(name: str) -> Availability | None:
        return Availability.POOL_GARDEN if name == fake_name else catalyst_availability(name)

    monkeypatch.setattr(catalyst_availability_mod, "catalyst_availability", _fake_lookup)

    # the default kitchen profile allows POOL_GARDEN -> no blocker
    assert route_catalyst_blockers(_FakeRoute([_declaring(fake_name)])) == ()

    # the stricter profile (no POOL_GARDEN) blocks it, with a reason naming the allowed set
    blocked = route_catalyst_blockers(_FakeRoute([_declaring(fake_name)]), NO_POOL_GARDEN_TIERS)
    assert len(blocked) == 1
    assert "not obtainable under allowed tiers" in blocked[0]
    assert fake_name in blocked[0]


# --- (d) is_kitchen_obtainable is unchanged by its re-expression via is_obtainable_under ----------------------------


def test_is_kitchen_obtainable_matches_is_obtainable_under_kitchen_tiers_for_a_spread_of_tiers():
    for tier in (
        None,
        Availability.GROCERY,
        Availability.PHARMACY,
        Availability.HARDWARE,
        Availability.POOL_GARDEN,
        Availability.INDUSTRIAL,
    ):
        assert is_kitchen_obtainable(tier) == is_obtainable_under(tier, KITCHEN_TIERS)

    # and the concrete pre-existing answers are preserved
    assert is_kitchen_obtainable(Availability.GROCERY) is True
    assert is_kitchen_obtainable(Availability.HARDWARE) is True
    assert is_kitchen_obtainable(Availability.INDUSTRIAL) is False
    assert is_kitchen_obtainable(None) is False


def test_is_obtainable_under_never_vouches_none_regardless_of_profile():
    # unrecognized (None) stays False under EVERY allowed_tiers, including the maximal one -- an unrecognized
    # catalyst is never assumed obtainable no matter how permissive the profile is (false-VOUCH >> false-UNRECOGNIZED
    # holds independent of profile).
    for tiers in (KITCHEN_TIERS, LAB_TIERS, NO_POOL_GARDEN_TIERS, frozenset()):
        assert is_obtainable_under(None, tiers) is False
