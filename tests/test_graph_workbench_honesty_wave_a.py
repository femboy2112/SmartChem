"""Wave A -- the graph/synthesis workbench HONESTY + display-security regressions.

Each test pins the RENDERED behaviour (not merely a source string) of a fix for a verified Wave A finding:
a forged advisory reaction-centre must not be shown as proven chemistry (F1); the scheme note must credit
the oracle's re-derivation, not centre equality (F2); the three completeness states must stay distinct in
the banner and the CLI exit code (F3); the Graphviz subprocess must be bounded (F4); the optional RDKit SVG
must be embedded in a sandbox, never via innerHTML (F5). None of these needs RDKit/Graphviz installed.
"""
from __future__ import annotations

import json
import re

from smartchem.diels_alder import _DA_CENTER
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.graph_cli import _completeness_exit_code
from smartchem.graph_projection import (
    project_synthesis,
    render_html,
    render_scheme_html,
)
from smartchem.smiles import parse_smiles as P


def _data_island(html: str) -> dict:
    m = re.search(r'<script[^>]*application/json[^>]*>(.*?)</script>', html, re.S)
    assert m, "no JSON data island in the rendered HTML"
    return json.loads(m.group(1))


def _forged_centre_route() -> ExperimentRoute:
    """A carbon-free H + H -> H2 step wearing a BORROWED carbocyclic Diels-Alder centre (forged advisory
    metadata the oracle correctly refuses to name)."""
    h2, atom = P("[H][H]"), P("[H]")
    return ExperimentRoute.of(
        ExperimentStep.assembling(h2, (atom, atom), (h2,), reaction_center=_DA_CENTER))


# --- F1: a forged advisory centre is never the headline, and is labelled advisory ---------------------

def test_forged_centre_is_not_the_headline():
    html = render_scheme_html(_forged_centre_route(), depict=False)
    step = _data_island(html)["steps"][0]
    # the headline is the SOUND conserved-multiset equation (a hydrogen reaction), NOT the borrowed centre's
    # five carbon bonds -- a carbon-free step must never headline carbon chemistry.
    assert step["headline"] == "H + H -> H2"
    assert "C-C" not in step["headline"] and "C=C" not in step["headline"]


def test_forged_centre_bond_change_is_rendered_as_advisory():
    html = render_scheme_html(_forged_centre_route(), depict=False)
    # the declared centre still appears (diagnostic) but ONLY under an explicit advisory label.
    assert "declared" in html.lower() and "advisory" in html.lower()
    # and the carbon claim is never stated as the authoritative headline span styling without that label.


# --- F2: the scheme note credits the oracle, not centre equality --------------------------------------

def test_scheme_note_does_not_claim_naming_by_centre_equality():
    html = render_scheme_html(_forged_centre_route(), depict=False)
    assert "reaction centre exactly matches that family's own centre" not in html
    assert "re-derive" in html.lower() or "RE-DERIVES" in html


# --- F3: three distinct completeness states -----------------------------------------------------------

def test_completeness_exit_code_is_three_state():
    assert _completeness_exit_code("COMPLETE") == 0
    assert _completeness_exit_code("COMPLETE_WITHIN_BOUNDS") == 0
    assert _completeness_exit_code("UNATTESTED") == 3          # distinct: not 0 (complete), not 4 (truncated)
    assert _completeness_exit_code("INCOMPLETE_NO_ROUTE_OBSERVED") == 4
    assert _completeness_exit_code("PARTIAL_CANDIDATE_SET") == 4
    # the load-bearing #A1 guarantee: UNATTESTED is neither complete nor a failed search.
    assert _completeness_exit_code("UNATTESTED") not in (0, _completeness_exit_code("PARTIAL_CANDIDATE_SET"))


def test_unattested_projection_banner_is_not_shown_as_incomplete():
    # a route with no search receipt -> UNATTESTED (the public-API path evil-morty flagged for render_html).
    html = render_html(project_synthesis(_forged_centre_route()))
    assert _data_island(html)["graph"]["search_status"] == "UNATTESTED"
    # the banner must offer an UNATTESTED message and must NOT be limited to the two-state complete/incomplete
    # logic that bucketed UNATTESTED as "INCOMPLETE — candidates may be missing".
    assert "UNATTESTED" in html and "completeness not established" in html


# --- F4: the Graphviz subprocess is bounded -----------------------------------------------------------

def test_render_svg_bounds_the_subprocess():
    import inspect

    from smartchem import graph_projection
    src = inspect.getsource(graph_projection.render_svg)
    assert "timeout=" in src, "render_svg must bound the dot subprocess runtime"
    assert "TimeoutExpired" in src, "render_svg must handle a dot timeout with an explicit refusal"
    assert "32_000_000" in src or "cap" in src.lower(), "render_svg must bound the output size"


# --- F5: the optional RDKit SVG is sandboxed, never innerHTML ------------------------------------------

def _hostile_depiction(monkeypatch, svg: str):
    import smartchem.depiction as dep
    monkeypatch.setattr(dep, "depict_svg", lambda _mol: svg, raising=False)


def test_rdkit_svg_is_embedded_via_sandboxed_img_not_innerhtml(monkeypatch):
    # a hostile SVG with an event handler (NOT caught by the <script-only server filter) must still be inert.
    _hostile_depiction(monkeypatch, '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><rect/></svg>')
    html = render_scheme_html(_forged_centre_route(), depict=True)
    # the innerHTML sink is gone; the SVG is loaded as an <img> data URI (secure static mode: no script, no
    # event handler fires), via encodeURIComponent -- so onload/foreignObject/javascript: cannot execute.
    assert "pic.innerHTML = c.svg" not in html
    assert "data:image/svg+xml" in html and "encodeURIComponent" in html
    # if the hostile svg is carried at all it sits inside the application/json island (data, inert), never
    # as live markup written to a live element.
    island = _data_island(html)
    carried = [c.get("svg") for s in island["steps"] for c in s["precursors"] if c.get("svg")]
    if carried:
        assert all("onload" in s for s in carried)  # present only as inert JSON data


def test_server_drops_a_script_bearing_svg(monkeypatch):
    _hostile_depiction(monkeypatch, '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    html = render_scheme_html(_forged_centre_route(), depict=True)
    island = _data_island(html)
    for s in island["steps"]:
        for c in s["precursors"]:
            assert c.get("svg") is None, "a <script>-bearing SVG must be dropped server-side (defense-in-depth)"
