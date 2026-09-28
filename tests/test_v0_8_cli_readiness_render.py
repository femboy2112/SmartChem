"""v0.8 Round II -- human/JSON readiness parity (gate #9).

The CLI human render and the machine JSON must report the SAME readiness semantics, because both read the
one derived tier off the one evaluator. This pins that a PROCESS_SPECIFIED route renders the 0.8/0.9 capability
caveat in the human text (never claiming a particular bench can run it) and carries the matching machine tier.
"""
from __future__ import annotations

from smartchem.cli import _render_recompile_response
from smartchem.service import build_recompile_request, run_compilation


def _isopentyl_response():
    req = build_recompile_request(
        "isopentyl acetate", helper_reagents=("water", "acetic acid"),
        stock_materials=("isopentyl alcohol",), max_depth=1,
    )
    return run_compilation(req)


def test_cli_human_render_shows_process_specified_capability_note():
    resp = _isopentyl_response()
    text = _render_recompile_response(resp, quiet=False)
    assert "READINESS: PROCESS_SPECIFIED" in text
    # the 0.8/0.9 boundary must be explicit in the human text -- source-specified != bench-executable
    assert "capability is 0.9" in text
    assert "NOT a guarantee" in text


def test_cli_human_render_tier_matches_the_machine_tier():
    resp = _isopentyl_response()
    text = _render_recompile_response(resp, quiet=False)
    # human/JSON parity: the tier printed in the human render is exactly the machine readiness_tier.
    machine_tiers = {r.readiness_tier for r in resp.ranked_route_dossiers}
    assert "PROCESS_SPECIFIED" in machine_tiers
    # every machine tier appears verbatim in the human render's "[fit_status/tier]" line
    assert all(f"/{t}]" in text for t in machine_tiers)
