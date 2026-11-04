"""OPERATION XX section 10 -- the independent lactonization structural witness (1.6 CANDIDATE, standalone).

Ooh yeah!  These tests pin three things:
  1. the witness says True on real hydroxy-acid -> lactone pairs AND the production recognizer (when present on the
     branch) AGREES -- the cross-check is made SEPARATELY, the witness module itself never touches production;
  2. the witness says False where it must (acyclic ester, ring-but-not-ester, anhydride, carbonate, lactam, a
     same-formula fabricated precursor, a wrong-skeleton isomer) -- it can DISAGREE, it does not rubber-stamp;
  3. the independence claim itself is structurally checkable (AST scan of the witness source).

The production module (``smartchem.intramolecular_condensation``) is NOT in this branch's tree (it lives on the 1.5 /
held-1.6 lines); the ``smartchem`` package path happens to resolve it from the main checkout, which is what the
cross-check tests exercise.  They are ``importorskip``-gated, so they SKIP (never silently pass) where it is absent.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from smartchem import lactonization_witness as w
from smartchem.smiles import parse_smiles

POSITIVE_PAIRS = [
    ("beta-propiolactone", "OCCC(=O)O", "O=C1CCO1"),
    ("gamma-butyrolactone", "OCCCC(=O)O", "O=C1CCCO1"),
    ("delta-valerolactone", "OCCCCC(=O)O", "O=C1CCCCO1"),
    ("gamma-valerolactone", "CC(O)CCC(=O)O", "CC1CCC(=O)O1"),
    ("coumarin", "OC(=O)C=Cc1ccccc1O", "O=c1ccc2ccccc2o1"),
    ("pentonolactone (polyol)", "OCC(O)C(O)C(O)C(=O)O", "O=C1OCC(O)C(O)C1O"),
]

# (label, precursor SMILES, target SMILES): pairs the witness must REFUSE.
NEGATIVE_PAIRS = [
    # target is an ACYCLIC ester (methyl acetate): an ester, but not a ring ester
    ("acyclic ester target", "OCC(O)CO", "CC(=O)OC"),
    # target is a RING but not an ester: THF (cyclic ether) from 1,4-butanediol
    ("cyclic ether target", "OCCCCO", "C1CCOC1"),
    # target is a lactam (ring amide), precursor the amino acid: N, not O, closes the ring
    ("lactam target", "NCCCC(=O)O", "O=C1CCCN1"),
    # target is a cyclic ANHYDRIDE (diacid -> anhydride is not a lactonization)
    ("cyclic anhydride", "OC(=O)CCC(=O)O", "O=C1CCC(=O)O1"),
    # target is a cyclic CARBONATE
    ("cyclic carbonate", "OCCOC(=O)O", "O=C1OCCO1"),
    # same formula as the GBL hydroxy-acid, wrong constitution: balances mass, is NOT the lactonization precursor
    ("fabricated same-formula precursor", "COC(=O)CCO", "O=C1CCCO1"),
    # same formula, real lactone, but the precursor is a DIFFERENT skeleton (methyl-branched vs 6-ring)
    ("wrong-skeleton isomer", "CC(O)CCC(=O)O", "O=C1CCCCO1"),
    # mass does not balance at all
    ("no water gap", "OCCCCC(=O)O", "O=C1CCCO1"),
]


def _mol(smiles):
    return parse_smiles(smiles)


# ----------------------------------------------------------------------------------------------------- positives ---

@pytest.mark.parametrize("name,precursor,target", POSITIVE_PAIRS, ids=[p[0] for p in POSITIVE_PAIRS])
def test_witness_accepts_real_lactonizations(name, precursor, target):
    p, t = _mol(precursor), _mol(target)
    assert w.is_lactone_structure(t)
    res = w.witnesses_lactonization(p, t)
    assert res.is_lactonization, res.note
    # every individual check also holds (the verdict is their conjunction)
    assert (res.target_is_lactone and res.water_stoichiometry and res.ring_count_plus_one
            and res.group_deltas_match and res.hydrolysis_recovers_precursor)


@pytest.mark.parametrize("name,precursor,target", POSITIVE_PAIRS, ids=[p[0] for p in POSITIVE_PAIRS])
def test_production_recognizer_agrees_on_positives(name, precursor, target):
    ic = pytest.importorskip("smartchem.intramolecular_condensation")
    p, t = _mol(precursor), _mol(target)
    assert w.witnesses_lactonization(p, t).is_lactonization
    edges = ic.retro_lactonization_edges(t)
    assert any(e.products[0].canonical() == p.canonical() for e in edges), "production disagrees with the witness"


# ----------------------------------------------------------------------------------------------------- negatives ---

@pytest.mark.parametrize("name,precursor,target", NEGATIVE_PAIRS, ids=[n[0] for n in NEGATIVE_PAIRS])
def test_witness_refuses_non_lactonizations(name, precursor, target):
    res = w.witnesses_lactonization(_mol(precursor), _mol(target))
    assert not res.is_lactonization
    assert res.note.startswith("failed:")


@pytest.mark.parametrize("name,precursor,target", NEGATIVE_PAIRS, ids=[n[0] for n in NEGATIVE_PAIRS])
def test_production_recognizer_also_refuses_negatives(name, precursor, target):
    ic = pytest.importorskip("smartchem.intramolecular_condensation")
    p, t = _mol(precursor), _mol(target)
    edges = ic.retro_lactonization_edges(t)
    assert not any(e.products[0].canonical() == p.canonical() for e in edges)


def test_acyclic_ester_is_an_ester_but_not_a_lactone():
    t = _mol("CC(=O)OC")
    assert len(w.ester_motifs(t)) == 1                  # it IS an ester ...
    assert not w.is_lactone_structure(t)                # ... but its ester bond is on no ring
    assert w.ester_motifs(t)[0].ring == ()


def test_ring_that_is_not_an_ester_is_not_a_lactone():
    for smi in ("C1CCOC1", "C1CCCCC1", "O=C1CCCN1", "O=C1CCC(=O)O1", "O=C1OCCO1", "O=C1OCCN1"):
        assert not w.is_lactone_structure(_mol(smi)), smi


def test_the_discrimination_is_real_not_a_rubber_stamp():
    """The same precursor against two targets: the witness must say yes for one and no for the other."""
    p = _mol("OCCCC(=O)O")
    assert w.witnesses_lactonization(p, _mol("O=C1CCCO1")).is_lactonization
    assert not w.witnesses_lactonization(p, _mol("C1CCOC1")).is_lactonization        # THF: not an ester at all
    # isolate the identity check: wrong-skeleton isomer passes stoichiometry + census yet fails identity
    iso = w.witnesses_lactonization(_mol("CC(O)CCC(=O)O"), _mol("O=C1CCCCO1"))
    assert iso.water_stoichiometry and iso.target_is_lactone and iso.ring_count_plus_one and iso.group_deltas_match
    assert not iso.hydrolysis_recovers_precursor and not iso.is_lactonization


# ------------------------------------------------------------------------------------------ the pieces, on their own ---

def test_formula_conservation_is_dict_addition():
    p, t = _mol("OCCCC(=O)O"), _mol("O=C1CCCO1")
    assert dict(p.formula) == {"C": 4, "H": 8, "O": 3}
    assert dict(t.formula) == {"C": 4, "H": 6, "O": 2}
    assert w._formula_gap_is_water(p, t)
    assert not w._formula_gap_is_water(t, p)                                  # direction matters
    assert not w._formula_gap_is_water(p, _mol("O=C1CCCCO1"))                 # wrong carbon count
    assert not w._formula_gap_is_water(_mol("COC(=O)CCO"), _mol("OCCCC(=O)O"))  # isomers: no water gap


def test_ring_rank_rises_by_exactly_one_on_lactonization():
    p, t = _mol("OCCCC(=O)O"), _mol("O=C1CCCO1")
    assert w.group_census(t).cycle_rank == w.group_census(p).cycle_rank + 1 == 1


def test_group_census_of_the_precursor_and_target():
    cp = w.group_census(_mol("OCCCC(=O)O"))
    ct = w.group_census(_mol("O=C1CCCO1"))
    assert (cp.carboxylic_acids, cp.alcohol_hydroxyls, cp.esters, cp.lactones) == (1, 1, 0, 0)
    assert (ct.carboxylic_acids, ct.alcohol_hydroxyls, ct.esters, ct.lactones) == (0, 0, 1, 1)


def test_lactone_ring_size_is_reported_from_an_explicit_cycle():
    assert [len(w.lactone_motifs(_mol(s))[0].ring) for s in ("O=C1CCO1", "O=C1CCCO1", "O=C1CCCCO1")] == [4, 5, 6]
    m = w.lactone_motifs(_mol("O=C1CCCO1"))[0]
    assert m.o_exo not in m.ring and m.o_link in m.ring and m.c in m.ring


def test_bridge_finder_separates_ring_bonds_from_chain_bonds():
    mol = _mol("O=C1CCCO1")
    adj = w._graph(mol)
    bridges = w._bridges(adj)
    ring_atoms = set(w.lactone_motifs(mol)[0].ring)
    for b in mol.bonds:
        on_ring = b.i in ring_atoms and b.j in ring_atoms      # this monocycle has no chords: both ends in ring
        assert (frozenset((b.i, b.j)) not in bridges) == on_ring


def test_own_isomorphism_distinguishes_isomers_and_accepts_relabelings():
    a = _mol("CC(O)CCC(=O)O")
    b = _mol("OCCCCC(=O)O")
    c = _mol("OC(=O)CCCCO")                                                   # same molecule as b, different spelling
    ga, gb, gc = (([*m.atoms], w._graph(m)) for m in (a, b, c))
    assert not w._isomorphic(*ga, *gb)
    assert w._isomorphic(*gb, *gc)


# ---------------------------------------------------------------------------------------- documented divergence ---

def test_documented_divergence_hemiacetal_lactone():
    """KNOWN, DELIBERATE disagreement (see the module docstring): a lactone whose alkoxy carbon bears a second oxygen is
    structurally a cyclic ester, so the witness says True.  The production recognizer at 38e9186 (dalembert XV-P8
    carbinol guard, branch feat/lactonization-exhaustiveness) refuses the masked-carbonyl hydroxyl and emits no edge --
    a DISAGREEMENT a human should look at.  (Verified out-of-band against 38e9186; the older production module that
    ``smartchem.intramolecular_condensation`` may resolve to on other checkouts lacks that guard and AGREES with the
    witness here, so the production half is deliberately not asserted in-suite.)"""
    res = w.witnesses_lactonization(_mol("OC(=O)CCC(O)O"), _mol("O=C1CCC(O)O1"))
    assert res.is_lactonization


# --------------------------------------------------------------------------------------------- independence audit ---

FORBIDDEN_NAMES = {"_lactonizes_to", "_forward_lactonizations", "_ring_ester_sites", "_open_lactone",
                   "IntramolecularCondensationEdge", "_carboxyl_sites", "_hydroxyl_sites", "_acyl_is_lactone_like",
                   "_connected_over", "_drop_atoms", "retro_lactonization_edges", "retro_lactonization_enumeration",
                   "recognize_reaction_type", "resonance_identity", "canonical"}
FORBIDDEN_MODULES = ("intramolecular_condensation", "reaction_type_oracle", "smiles")


def _witness_ast():
    return ast.parse(pathlib.Path(w.__file__).read_text())


def test_witness_does_not_import_the_production_recognizer():
    for node in ast.walk(_witness_ast()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(m in alias.name for m in FORBIDDEN_MODULES), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not any(m in (node.module or "") for m in FORBIDDEN_MODULES), node.module
            assert not any(a.name in FORBIDDEN_NAMES for a in node.names)


def test_witness_never_references_a_production_symbol():
    """AST-level (docstrings and comments may NAME the production functions to explain the contrast; code may not
    reference them): no Name / Attribute / call target in the witness is a production private symbol, and the witness
    never calls ``Molecule.canonical`` (the identity subsystem the production verdict is a function of)."""
    for node in ast.walk(_witness_ast()):
        if isinstance(node, ast.Name):
            assert node.id not in FORBIDDEN_NAMES, node.id
        elif isinstance(node, ast.Attribute):
            assert node.attr not in FORBIDDEN_NAMES, node.attr


def test_witness_imports_only_the_molecule_type_from_the_package():
    pkg_imports = [n for n in ast.walk(_witness_ast()) if isinstance(n, ast.ImportFrom) and n.level >= 1]
    assert [(n.module, sorted(a.name for a in n.names)) for n in pkg_imports] == [("category", ["Molecule"])]
