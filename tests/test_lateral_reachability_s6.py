"""Regression lock for LATERAL-REACHABILITY-S6 (OPERATION §6 -- the moonshot, scoped).

ONE lateral family reachable via the opt-in bounded state-aware search (smartchem.lateral_search), oracle-vouched
step-by-step -- and, the #132 payoff, vouched even CENTRE-LESS (a hand-assembled lateral route with no carried
reaction_center, which the retired Layer-C gate would have demoted).  Demonstrated for Cope, Claisen and 6-pi
electrocyclic.
"""
from __future__ import annotations

import experiments.lateral_reachability_s6 as bench


def test_lateral_families_are_reachable_and_vouched_centre_free():
    rows = bench.measure()["rows"]
    assert len(rows) == 3
    for name, status, classes, carried_blk, centreless_blk in rows:
        assert classes is not None, f"{name}: lateral route not reached ({status})"
        assert carried_blk == (), f"{name}: carried-centre route demoted: {carried_blk}"
        assert centreless_blk == (), f"{name}: CENTRE-LESS route demoted (the #132 payoff regressed): {centreless_blk}"
        assert all(c is not None for c in classes), f"{name}: a centre-less step was not recognized: {classes}"


def test_validate_is_green():
    assert bench.validate() is True
