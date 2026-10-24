"""Regression guard for CANDIDATE-STARVATION-127 (OPERATION SMARTCHEM §4 / issue #127).

The measured result is that the raw ``max_routes`` cap does NOT starve a recognized route: the recognized single
condensation enumerates FIRST (a 1-step route to commodity precursors), so recognized-recall is 1.0 even at cap=1,
and the search is order-invariant.  This gates that result: if a future grammar widening introduces a 1-step
fiction that sorts before a recognized route, ``validate()`` turns red here -- the trigger to build the type-gated /
fair-provider candidate scheduling #127 describes.  (A real failure would be a chemistry/compiler change with its
own evidence, not a silently-tolerated recall drop.)
"""
from __future__ import annotations

import experiments.candidate_starvation_127 as bench


def test_no_cap_starvation_and_order_invariant():
    m = bench.measure()
    assert m["targets_with_recognized_route"] >= 3, f"benchmark went vacuous: {m}"
    assert not m["any_starvation_observed"], (
        f"#127 CAP STARVATION regression on {m['starved_targets']} -- a recognized route was crowded out of the "
        f"raw max_routes cap by fictions; build the type-gated candidate scheduling before widening generation")
    assert m["all_order_invariant"], "search lost order-invariance -- a reagent/commodity reorder changed the result"
    assert bench.validate() is True


def test_recognized_route_enumerates_within_the_smallest_caps():
    # the mechanism behind the non-starvation: every recognized route appears within the first few slots (here, at
    # index 0), so even the tightest cap keeps full recognized-recall.  Pins the empirical "recognized-first" fact.
    for row in bench.measure()["rows"]:
        if row["recognized_total"]:
            assert row["recall_at_cap1"] == 1.0, f"{row['name']}: recognized route missing at cap=1: {row}"
            assert max(row["recognized_indices"]) < 5, f"{row['name']}: a recognized route sits past the small caps: {row}"
