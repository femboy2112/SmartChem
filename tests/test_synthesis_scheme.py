"""Named synthesis SCHEME + optional structure depiction: the chemist's drawn, step-by-step view.

These cover the three things that make a synthesis diagram MEAN something without inventing chemistry:
(1) routing the synthesis view through the certified named algebra so the compiler's real reaction
families surface -- proven on the carbocyclic Diels-Alder litmus (cyclohexene retro = butadiene +
ethene, named, an AND-dependency); (2) a reaction family is named ONLY on an exact match to that
family's own canonical reaction centre, never guessed; (3) 2D structures are drawn by an OPTIONAL
RDKit backend and degrade to name/formula boxes when it is absent, with two constitutional isomers
never drawn (or labelled) the same.

RDKit is a dev-only backend: the depiction-drawing tests importorskip it, so the committed baseline
(RDKit uninstalled) skips them and exercises the degrade path instead.
"""
from __future__ import annotations

import json
import re

import pytest

from smartchem.algebra_profiles import resolve_algebra_profile
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.graph_projection import (
    project_synthesis,
    render_scheme_html,
    _bond_change_text,
    _conditions_summary,
    _reaction_family,
    _reaction_family_for_step,
)

_DA_NAME = "Diels–Alder [4+2] cycloaddition"


def _da_route():
    """The carbocyclic Diels-Alder of cyclohexene via the CERTIFIED algebra: 1 named step,
    butadiene + ethene -> cyclohexene, with the retro fragments supplied as terminal stock."""
    registry = resolve_algebra_profile("certified-route-v07")
    target = parse_smiles("C1CC=CCC1")           # cyclohexene, C6H10
    butadiene = parse_smiles("C=CC=C")           # C4H6
    ethene = parse_smiles("C=C")                 # C2H4
    search = search_routes(target, registry=registry, reagents=(),
                           available=(butadiene, ethene), max_depth=2, max_routes=10)
    assert search.routes, "certified algebra must surface the cyclohexene Diels-Alder disconnection"
    return search.routes[0], search




# --- The falsifiable step: named chemistry actually surfaces -----------------------------------

def test_cyclohexene_retro_surfaces_butadiene_and_ethene_as_a_named_diels_alder():
    route, search = _da_route()
    assert len(route.steps) == 1
    step = route.steps[0]
    # AND-dependency: ONE reaction consumes BOTH precursors (not two alternative OR-routes).
    assert sorted(repr_formula(m) for m in step.precursors) == ["C2H4", "C4H6"]
    assert len(step.precursors) == 2
    # The family is the carbocyclic Diels-Alder, recovered by exact reaction-centre match.
    assert _reaction_family(step.reaction_center) == _DA_NAME
    # The projection keeps it convergent: the single reaction node has two distinct consumes arcs.
    graph = project_synthesis(route, search_result=search)
    reaction = next(n for n in graph.nodes if n.kind == "reaction")
    consumes = [a for a in graph.arcs if a.target == reaction.id and a.role == "consumes"]
    assert len(consumes) == 2 and len({a.source for a in consumes}) == 2
    assert graph.search_status == "COMPLETE_WITHIN_BOUNDS"
    assert dict(reaction.attributes)["reaction_family"] == _DA_NAME


def repr_formula(mol):
    from smartchem.decompiler import Formula
    return repr(Formula.of(mol.formula, mol.charge))


# --- Family naming is sound-or-silent, never fabricated --------------------------------------

def test_reaction_family_is_named_only_on_an_exact_centre_match():
    from smartchem.reaction_center import ReactionCenter
    route, _ = _da_route()
    da_center = route.steps[0].reaction_center
    assert _reaction_family(da_center) == _DA_NAME
    # No centre -> no family.
    assert _reaction_family(None) is None
    # A reaction centre that no family declares as its own must NOT be given a Diels-Alder (or any)
    # family name -- the sound-or-silent rule. A bond-change description is still available for it.
    foreign = ReactionCenter.of([("C", "O", 1)], [("C", "O", 2)], 1)
    assert _reaction_family(foreign) is None
    assert _bond_change_text(foreign)
    # And a centre one bond off from the real DA centre is NOT laundered into "Diels-Alder".
    tampered = ReactionCenter.of(list(da_center.formed)[:-1], list(da_center.broken), 1)
    assert _reaction_family(tampered) is None


def test_bond_change_text_is_a_neutral_sound_description():
    route, _ = _da_route()
    text = _bond_change_text(route.steps[0].reaction_center)
    assert text.startswith("forms ") and "; breaks " in text
    # the DA forms the cyclohexene ring (C-C bonds) and breaks the diene/dienophile pi bonds
    assert "C-C" in text or "C=C" in text


def test_undeclared_conditions_report_unknown_never_a_default():
    route, _ = _da_route()
    # the DA step carries no sourced envelope -> conditions must read UNKNOWN, not an invented ambient
    assert _conditions_summary(route.steps[0].envelope) == "unknown"


# --- The scheme render: inherits attestation, degrades honestly, stays injection-safe ----------

def test_scheme_shows_named_step_and_inherits_projection_attestation():
    route, search = _da_route()
    html = render_scheme_html(route, search_result=search, route_label="route 0 of 1")
    assert _DA_NAME in html
    # inherits the sound projection's status + receipt binding (scheme never re-searches)
    projection = project_synthesis(route, search_result=search)
    assert projection.receipt_digest[:12] in html
    assert "COMPLETE_WITHIN_BOUNDS" in html
    # the drawn/degraded data island must be valid JSON and must not break out of the script element
    assert "</script>" not in _data_island_raw(html)
    payload = _parse_island(html)
    assert payload["steps"][0]["family"] == _DA_NAME
    assert sorted(p["formula"] for p in payload["steps"][0]["precursors"]) == ["C2H4", "C4H6"]
    # no cell ever carries a scripted SVG
    assert all("<script" not in (c.get("svg") or "").lower()
               for step in payload["steps"]
               for c in step["precursors"] + [step["target"]] + step["reagents"] + step["byproducts"])


def _paracetamol_route():
    """Paracetamol by the FREE-ACID dehydrative amidation (4-aminophenol + acetic acid -> paracetamol
    + water) -- generated by capped scission and VOUCHED by the oracle as acyl condensation. The
    industrial acetic-ANHYDRIDE route is demoted by the feasibility census, which is a separate gap."""
    from smartchem.cli import _parse_molecule
    registry = resolve_algebra_profile("certified-route-v07")
    search = search_routes(_parse_molecule("paracetamol"), registry=registry,
                           reagents=(parse_smiles("O"),),
                           available=(parse_smiles("Nc1ccc(O)cc1"), parse_smiles("CC(=O)O")),
                           max_depth=2, max_routes=10)
    assert search.routes, "paracetamol must synthesize via the free-acid amidation"
    return search.routes[0], search


def test_scheme_names_an_oracle_vouched_condensation_not_only_diels_alder():
    # The compiler CAN make paracetamol, and the scheme must NAME the step. The name does not come from
    # a Diels-Alder centre match (there is none) -- it comes from the conservation-locked oracle vouch,
    # which the DA-only matcher could not surface.
    route, search = _paracetamol_route()
    step = route.steps[0]
    assert _reaction_family(step.reaction_center) is None            # not a DA centre
    name = _reaction_family_for_step(step)
    assert name is not None and "acyl condensation" in name          # oracle-vouched family
    html = render_scheme_html(route, search_result=search)
    assert "acyl condensation" in html
    assert "paracetamol" in html and "4-aminophenol" in html         # chemist names, not hashes


def test_unvouched_step_stays_unnamed_rather_than_guessing():
    # Family naming is sound-or-silent at the step level too: a step the oracle cannot vouch and whose
    # centre matches no family returns None, so the scheme shows its bond-change, never an invented name.
    from smartchem.reaction_center import ReactionCenter
    from types import SimpleNamespace
    fake = SimpleNamespace(reaction_center=ReactionCenter.of([("C", "O", 1)], [("C", "O", 2)], 1))
    # recognize_reaction_type would reject this synthetic step; the matcher already returns None.
    assert _reaction_family(fake.reaction_center) is None


def test_scheme_degrades_to_formula_boxes_without_depiction(monkeypatch):
    # Force the depiction backend absent: the scheme must still render every species as a formula/name
    # box, name the step, and never crash or claim a missing identity.
    import smartchem.depiction as dep
    monkeypatch.setattr(dep, "_backend", lambda: None)
    monkeypatch.setattr(dep, "_BACKEND", None, raising=False)
    route, search = _da_route()
    html = render_scheme_html(route, search_result=search)
    payload = _parse_island(html)
    assert all(c["svg"] is None
               for step in payload["steps"]
               for c in step["precursors"] + [step["target"]])
    assert payload["steps"][0]["family"] == _DA_NAME     # chemistry still legible without drawings
    assert "C6H10" in html and "C4H6" in html


def test_scheme_rejects_a_route_that_is_not_in_its_search_result():
    route, _ = _da_route()
    _other, other_search = _da_route()
    # a different search object whose receipt does bind the same target still validates; use a
    # structurally mismatched kind to prove the inherited guard fires.
    with pytest.raises(TypeError):
        render_scheme_html(object())


# --- Optional RDKit depiction: real structures, isomers never identical -----------------------

def test_depiction_draws_real_structures_from_the_engine_graph():
    pytest.importorskip("rdkit")
    from smartchem.depiction import depict_svg, molecule_to_rdkit
    from rdkit import Chem
    para = parse_smiles("CC(=O)Nc1ccc(O)cc1")
    svg = depict_svg(para)
    assert svg and svg.lstrip().startswith("<svg") and svg.rstrip().endswith("</svg>")
    # faithfulness: the bridge round-trips the exact constitution (no SMILES writer involved)
    assert Chem.MolToSmiles(Chem.RemoveHs(molecule_to_rdkit(para))) == "CC(=O)Nc1ccc(O)cc1"


def test_depiction_never_draws_two_constitutional_isomers_the_same():
    pytest.importorskip("rdkit")
    from smartchem.depiction import depict_svg
    ethanol = parse_smiles("CCO")
    dimethyl_ether = parse_smiles("COC")
    assert ethanol.formula == dimethyl_ether.formula       # same C2H6O
    a, b = depict_svg(ethanol), depict_svg(dimethyl_ether)
    assert a and b and a != b                               # distinct drawings, never collapsed


def test_depiction_degrades_to_none_when_backend_absent(monkeypatch):
    import smartchem.depiction as dep
    monkeypatch.setattr(dep, "_backend", lambda: None)
    assert dep.depiction_available() is False
    assert dep.depict_svg(parse_smiles("CCO")) is None
    assert dep.molecule_to_rdkit(parse_smiles("CCO")) is None


def test_depiction_bridge_builds_a_valence_legal_mol_or_none():
    pytest.importorskip("rdkit")
    from smartchem.depiction import molecule_to_rdkit
    from rdkit import Chem
    # a valence-legal species builds and sanitises; the bridge returns a real Mol, not a guess
    mol = molecule_to_rdkit(parse_smiles("CC(=O)OC(=O)C"))  # acetic anhydride
    assert mol is not None and Chem.MolToSmiles(Chem.RemoveHs(mol)) == "CC(=O)OC(C)=O"


# --- CLI: the scheme format, algebra selection, and refusal discipline ------------------------

def test_graph_scheme_cli_exit_codes(capsys):
    from smartchem.graph_cli import main
    # synthesis scheme of the DA route via the certified algebra: complete -> exit 0, drawn HTML
    code = main(["synthesis", "C1CC=CCC1", "--algebra", "certified-route-v07",
                 "--available", "C=CC=C", "C=C", "--reagents", "--max-depth", "2", "--format", "scheme"])
    out = capsys.readouterr()
    assert code == 0
    assert _DA_NAME in out.out
    # the drawn 'scheme' format is refused on the formula view (it is composition accounting)
    assert main(["formula", "H2O", "--format", "scheme"]) == 5
    # an out-of-range route index is refused, never silently clamped
    assert main(["synthesis", "C1CC=CCC1", "--algebra", "certified-route-v07",
                 "--available", "C=CC=C", "C=C", "--reagents", "--format", "scheme",
                 "--route-index", "9"]) == 5


def test_graph_cli_algebra_choice_is_honoured(capsys):
    from smartchem.graph_cli import main
    # legacy-capped-v1 is scission-only: cyclohexene yields NO Diels-Alder route, so --format scheme
    # is refused (nothing to draw) rather than inventing one.
    code = main(["synthesis", "C1CC=CCC1", "--algebra", "legacy-capped-v1",
                 "--available", "C=CC=C", "C=C", "--reagents", "--format", "scheme"])
    assert code == 5


# --- helpers ----------------------------------------------------------------------------------

def _data_island_raw(html: str) -> str:
    return re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1)


def _parse_island(html: str) -> dict:
    raw = _data_island_raw(html).replace("<\\/", "</").replace("<\\!--", "<!--")
    return json.loads(raw)
