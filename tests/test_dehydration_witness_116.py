"""#116 -- the INDEPENDENT dehydration witness (``smartchem.elimination_witness``).

Pins: the witness accepts genuine dehydrations and the production verdict agrees (cross-check made HERE, never inside
the witness); it rejects the look-alikes; each corroborating check discriminates on its own; and the independence
claim is structurally audited (AST: imports only ``Molecule``; no production symbol, no canonical-identity call).
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from smartchem import elimination_witness as w
from smartchem.elimination import _dehydrates_to
from smartchem.smiles import parse_smiles

P = parse_smiles

POSITIVE_PAIRS = [
    ("ethanol", "CCO", "C=C"),
    ("cyclohexanol", "OC1CCCCC1", "C1=CCCCC1"),
    ("tert-butanol", "CC(C)(C)O", "C=C(C)C"),
    ("2-butanol -> 1-butene", "CCC(C)O", "C=CCC"),
    ("2-butanol -> 2-butene", "CCC(C)O", "CC=CC"),
    ("1-phenylethanol -> styrene", "CC(O)c1ccccc1", "C=Cc1ccccc1"),
    ("1,3-propanediol -> allyl alcohol", "OCCCO", "C=CCO"),
]

NEGATIVE_PAIRS = [
    ("THF from 1,4-butanediol", "OCCCCO", "C1CCOC1"),
    ("neopentyl 1,2-shift", "CC(C)(C)CO", "CC=C(C)C"),
    ("pinacolyl 1,2-shift", "CC(O)C(C)(C)C", "CC(C)=C(C)C"),
    ("1-butanol -> 2-butene", "CCCCO", "CC=CC"),
    ("3-hydroxybutanal -> MVK", "CC(O)CC=O", "C=CC(C)=O"),
    ("dienol -> benzene", "OC1C=CC=CC1", "c1ccccc1"),
    ("gem-diol -> aldehyde", "CC(O)O", "CC=O"),
    ("glycol -> vinyl alcohol", "OCCO", "C=CO"),
    ("vinyl alcohol -> ethyne", "C=CO", "C#C"),
    ("allyl alcohol -> allene", "C=CCO", "C=C=C"),
    ("acetic acid -> ketene", "CC(=O)O", "C=C=O"),
    ("ether -> propene glue", "CCOC", "C=CC"),
    ("epoxide -> enol", "C1CO1", "C=CO"),
    ("bromoethane -> ethene", "CCBr", "C=C"),
    ("two waters", "OCCCCO", "C=CC=C"),
    ("enol ether", "COCCO", "C=COC"),
    ("cyclopropene", "OC1CC1", "C1=CC1"),
]


@pytest.mark.parametrize("name,precursor,target", POSITIVE_PAIRS, ids=[p[0] for p in POSITIVE_PAIRS])
def test_witness_accepts_and_production_agrees(name, precursor, target):
    res = w.witnesses_dehydration(P(precursor), P(target))
    assert res.is_dehydration, res.note
    assert (res.water_stoichiometry and res.cycle_rank_unchanged and res.census_deltas_match
            and res.hydration_recovers_precursor)
    assert _dehydrates_to(P(precursor), P(target))


@pytest.mark.parametrize("name,precursor,target", NEGATIVE_PAIRS, ids=[n[0] for n in NEGATIVE_PAIRS])
def test_witness_rejects_and_production_agrees(name, precursor, target):
    res = w.witnesses_dehydration(P(precursor), P(target))
    assert not res.is_dehydration and res.note.startswith("failed:")
    assert not _dehydrates_to(P(precursor), P(target))


def test_each_corroborating_check_discriminates_on_its_own():
    # cycle rank alone rejects the ring-closing etherification
    thf = w.witnesses_dehydration(P("OCCCCO"), P("C1CCOC1"))
    assert thf.water_stoichiometry and not thf.cycle_rank_unchanged
    # the census alone rejects the aromatising closure, even though hydration of benzene IS the dienol
    arom = w.witnesses_dehydration(P("OC1C=CC=CC1"), P("c1ccccc1"))
    assert arom.water_stoichiometry and arom.cycle_rank_unchanged and not arom.census_deltas_match
    # identity alone rejects the 1,2-shift: stoichiometry, rank and census all pass
    shift = w.witnesses_dehydration(P("CC(C)(C)CO"), P("CC=C(C)C"))
    assert shift.water_stoichiometry and shift.cycle_rank_unchanged and shift.census_deltas_match
    assert not shift.hydration_recovers_precursor


def test_census_reads_arene_bonds_as_ring_conjugated_and_the_vinyl_as_isolated():
    c = w.dehydration_census(P("C=Cc1ccccc1"))
    assert (c.isolated_cc, c.ring_conjugated_cc, c.cycle_rank) == (1, 3, 1)
    c = w.dehydration_census(P("CC(O)c1ccccc1"))
    assert (c.sp3_alcohols, c.isolated_cc, c.ring_conjugated_cc) == (1, 0, 3)


def test_eligible_sites_exclude_cumulene_enol_three_ring_and_arene():
    for smi in ("C=C=C", "C=CO", "C1=CC1", "c1ccccc1"):
        assert w.eligible_alkene_sites(P(smi)) == (), smi
    assert len(w.eligible_alkene_sites(P("C=Cc1ccccc1"))) == 1


def test_own_isomorphism_distinguishes_isomers_and_accepts_relabelings():
    a, b, c = P("CCCCO"), P("CCC(C)O"), P("OCCCC")
    ga, gb, gc = (([*m.atoms], w._graph(m)) for m in (a, b, c))
    assert not w._isomorphic(*ga, *gb)
    assert w._isomorphic(*ga, *gc)


def test_bridges_within_finds_ring_and_chain_bonds():
    m = P("C=Cc1ccccc1")
    g = w._graph(m)
    pi = w._pi_capable_atoms(m.atoms, g)
    bridges = w._bridges_within(g, pi)
    doubles = w._cc_doubles(m.atoms, g)
    assert sum(1 for d in doubles if d in bridges) == 1          # only the vinyl C=C is a bridge


# -- independence audit ----------------------------------------------------------------------------------------------

FORBIDDEN_NAMES = {"_dehydrates_to", "_forward_dehydrations", "_dehydration_sites", "_closes_pi_ring",
                   "_alkene_sites", "_hydrate", "DehydrationEdge", "retro_dehydration_edges",
                   "retro_dehydration_enumeration", "_dehydration", "recognize_reaction_type",
                   "resonance_identity", "canonical"}
FORBIDDEN_MODULES = ("elimination", "reaction_type_oracle", "smiles", "intramolecular_condensation",
                     "lactonization_witness", "rule_calculus")


def _witness_ast():
    return ast.parse(pathlib.Path(w.__file__).read_text())


def test_witness_does_not_import_production():
    for node in ast.walk(_witness_ast()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(m in alias.name for m in FORBIDDEN_MODULES), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not any(m in (node.module or "") for m in FORBIDDEN_MODULES), node.module
            assert not any(a.name in FORBIDDEN_NAMES for a in node.names)


def test_witness_never_references_a_production_symbol():
    for node in ast.walk(_witness_ast()):
        if isinstance(node, ast.Name):
            assert node.id not in FORBIDDEN_NAMES, node.id
        elif isinstance(node, ast.Attribute):
            assert node.attr not in FORBIDDEN_NAMES, node.attr


def test_witness_imports_only_the_molecule_type_from_the_package():
    pkg_imports = [n for n in ast.walk(_witness_ast()) if isinstance(n, ast.ImportFrom) and n.level >= 1]
    assert [(n.module, sorted(a.name for a in n.names)) for n in pkg_imports] == [("category", ["Molecule"])]
