"""Permanent control for issue #127 -- the raw result cap does not starve credible chemistry.

The full claim, empirical finding (verified-negative) and boundary live in
``experiments/search_starvation_127.py``. The mechanism it fears (classification runs AFTER
the cap; provider order is transform-digest order, not chemical merit) is real; this pins that
the HARM does not manifest for realistic condensation targets under the production default
profile: the credible route is emitted FIRST and is recalled even under ``max_routes=1``.

This control BITES: if a future generator or ordering change ever floods a conserved fiction
ahead of a credible route, cap=1 recall drops and ``validate()`` returns False here -- exactly
the starvation regression #127 describes, caught before release.
"""
from experiments.search_starvation_127 import validate


def test_the_result_cap_does_not_starve_credible_chemistry():
    ok, summary = validate()
    assert ok, f"#127 starvation control failed: {summary}"
    # non-vacuous: every case genuinely has a credible (all-steps-vouched) route, so the
    # "survives the brutal cap=1" check is a real recall guard, not a tautology on an empty set.
    assert summary["with_recognized_route"] == summary["cases"]
    assert summary["recognized_at_rank_0"] == summary["cases"]
    assert summary["credible_route_survives_cap1"] == summary["cases"]
