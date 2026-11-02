"""OPERATION XIII P0 -- the claim-tier vocabulary (the executable acceptance spec, section 1 + section 13.B)."""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation import claim_tiers as ct


def test_every_tier_token_has_a_rank():
    for tier in ct.CLAIM_TIERS:
        assert isinstance(ct.rank(tier), int)


def test_the_positive_ladder_is_strictly_increasing():
    ladder = [
        ct.STRUCTURALLY_CONSERVING, ct.NUMERICALLY_VERIFIED, ct.BENCHMARKED_AGAINST_REFERENCE_SOLVER,
        ct.CALIBRATED_TO_MEASUREMENT, ct.PREDICTIVE_WITHIN_VALIDATED_DOMAIN,
    ]
    ranks = [ct.rank(t) for t in ladder]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks)


def test_floors_sit_below_every_positive_claim():
    for floor in (ct.OUT_OF_DOMAIN, ct.REFUSED, ct.ASSUMED_PARAMETER, ct.UNVERIFIED):
        assert ct.rank(floor) < ct.rank(ct.STRUCTURALLY_CONSERVING)


def test_synonyms_share_a_rank():
    assert ct.rank(ct.OUT_OF_DOMAIN) == ct.rank(ct.REFUSED)
    assert ct.rank(ct.ASSUMED_PARAMETER) == ct.rank(ct.UNVERIFIED)


def test_weakest_premise_is_the_minimum_rank():
    # section 13.B made executable: sourced constants (would-be BENCHMARKED) + one assumed kLa caps at ASSUMED.
    assert ct.weakest(ct.BENCHMARKED_AGAINST_REFERENCE_SOLVER, ct.ASSUMED_PARAMETER) == ct.ASSUMED_PARAMETER
    assert ct.weakest(ct.NUMERICALLY_VERIFIED, ct.STRUCTURALLY_CONSERVING) == ct.STRUCTURALLY_CONSERVING
    # a refused premise is a hard floor that dominates everything.
    assert ct.weakest(ct.PREDICTIVE_WITHIN_VALIDATED_DOMAIN, ct.REFUSED) == ct.OUT_OF_DOMAIN


def test_weakest_of_a_single_tier_is_itself_canonically():
    assert ct.weakest(ct.NUMERICALLY_VERIFIED) == ct.NUMERICALLY_VERIFIED
    # a synonym collapses to the canonical spelling at its rank
    assert ct.weakest(ct.UNVERIFIED) == ct.ASSUMED_PARAMETER


def test_empty_premises_assert_nothing_certified():
    assert ct.weakest() == ct.ASSUMED_PARAMETER   # UNVERIFIED canonicalises to ASSUMED_PARAMETER at rank 1


def test_is_at_least():
    assert ct.is_at_least(ct.BENCHMARKED_AGAINST_REFERENCE_SOLVER, ct.NUMERICALLY_VERIFIED)
    assert not ct.is_at_least(ct.NUMERICALLY_VERIFIED, ct.BENCHMARKED_AGAINST_REFERENCE_SOLVER)
    assert ct.is_at_least(ct.NUMERICALLY_VERIFIED, ct.NUMERICALLY_VERIFIED)


def test_an_unknown_tier_raises_never_defaults():
    with pytest.raises(ct.InvalidClaimTierError):
        ct.rank("PRETTY_GOOD")
    with pytest.raises(ct.InvalidClaimTierError):
        ct.weakest(ct.NUMERICALLY_VERIFIED, "VIBES")
