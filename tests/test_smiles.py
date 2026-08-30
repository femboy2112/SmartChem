"""G1 -- the SMILES front door, proven against the hand-entered registry and its own boundaries.

The parser is trusted only as far as it is checked. Two kinds of proof:

* **Structural identity against ground truth.** For every registered species that has a SMILES in the
  organic subset, the parsed molecule is canonical-EQUAL to the hand-entered one -- not merely the
  same formula, the same bond graph (double bonds, ring, everything), byte for byte after
  canonicalisation. A wrong implicit-H count or a wrong bond order fails here.
* **Loud boundaries.** Malformed strings, disconnected components, and out-of-scope features (an
  aromatic heteroatom) raise :class:`SmilesError` -- never a silently-wrong molecule.

Aromatic identity: benzene and the para/mono-substituted rings in the registry are Kekulé-invariant
(the two Kekulé forms are isomorphic under the ring's symmetry), so canonicalisation makes the
parser's Kekulé choice irrelevant and the match is exact -- which is why these tests can compare an
aromatic parse against a hand-drawn Kekulé structure at all.
"""

import pytest

from smartchem.category import Molecule
from smartchem.smiles import SmilesError, parse_smiles
from smartchem.structure import known_compounds

# name -> a SMILES that must reproduce the registered structure exactly (canonical-equal).
# The radicals/hypervalent ones (NO, NO2) need bracket atoms to suppress implicit H -- included on
# purpose, so the implicit-H rule is exercised at its edges, not just on tidy closed-shell molecules.
_REGISTRY_SMILES = {
    "water": "O",
    "carbon monoxide": "[C-]#[O+]",
    "carbon dioxide": "O=C=O",
    "methane": "C",
    "ammonia": "N",
    "hydrogen peroxide": "OO",
    "methanol": "CO",
    "formaldehyde": "C=O",
    "formic acid": "OC=O",
    "ethanol": "CCO",
    "dimethyl ether": "COC",
    "acetone": "CC(=O)C",
    "methylamine": "CN",
    "hydrogen cyanide": "C#N",
    "nitric oxide": "[N]=O",
    "nitrogen dioxide": "[N](=O)[O]",
    "sulfur dioxide": "O=S=O",
    "ketene": "C=C=O",
    "acetic acid": "CC(=O)O",
    "acetic anhydride": "CC(=O)OC(=O)C",
    "4-aminophenol": "Nc1ccc(O)cc1",
    "paracetamol": "CC(=O)Nc1ccc(O)cc1",
    "4-aminophenyl acetate": "CC(=O)Oc1ccc(N)cc1",
}


def _registered(name: str) -> Molecule:
    for formula_species in (known_compounds(f) for f in _all_formulas()):
        for s in formula_species:
            if s.name == name:
                return s.molecule.canonical()
    raise AssertionError(f"{name} not registered")


def _all_formulas() -> set[str]:
    import smartchem.structure as mod
    formulas: set[str] = set()
    for attr in vars(mod).values():
        if isinstance(attr, (list, tuple)):
            for x in attr:
                if hasattr(x, "expected_formula"):
                    formulas.add(x.expected_formula)
    return formulas


@pytest.mark.parametrize("name,smiles", sorted(_REGISTRY_SMILES.items()))
def test_parses_to_the_registered_structure_exactly(name, smiles):
    assert parse_smiles(smiles) == _registered(name)   # canonical-equal: same bond graph, not just formula


def test_every_registry_ring_species_is_covered():
    # the three ring species -- the whole reason canonicalisation had to be fixed first -- are here
    for name in ("paracetamol", "4-aminophenol", "4-aminophenyl acetate"):
        assert name in _REGISTRY_SMILES


class TestSpellingsAgree:
    def test_two_atom_orders_of_ethanol_agree(self):
        assert parse_smiles("CCO") == parse_smiles("OCC")

    def test_two_kekule_spellings_of_benzene_agree(self):
        # aromatic perception and an explicit alternate Kekulé must land on one canonical form
        assert parse_smiles("c1ccccc1") == parse_smiles("C1=CC=CC=C1")

    def test_branch_and_ring_reordering_of_paracetamol_agree(self):
        assert parse_smiles("CC(=O)Nc1ccc(O)cc1") == parse_smiles("Oc1ccc(NC(C)=O)cc1")


class TestImplicitHydrogen:
    def test_carbon_fills_to_four(self):
        assert dict(parse_smiles("C").formula) == {"C": 1, "H": 4}

    def test_double_bond_reduces_implicit_h(self):
        assert dict(parse_smiles("C=C").formula) == {"C": 2, "H": 4}   # ethylene, not ethane

    def test_triple_bond_reduces_further(self):
        assert dict(parse_smiles("C#C").formula) == {"C": 2, "H": 2}   # acetylene

    def test_bracket_atom_h_is_exact_not_implicit(self):
        # [CH3] is a methyl radical: exactly three H, no valence fill to four
        assert dict(parse_smiles("[CH3]").formula) == {"C": 1, "H": 3}


class TestCharge:
    def test_ammonium_carries_its_charge(self):
        m = parse_smiles("[NH4+]")
        assert dict(m.formula) == {"N": 1, "H": 4} and m.charge == 1

    def test_hydroxide_carries_its_charge(self):
        m = parse_smiles("[OH-]")
        assert dict(m.formula) == {"O": 1, "H": 1} and m.charge == -1


class TestBoundariesRefuseLoudly:
    def test_aromatic_heteroatom_is_refused_not_guessed(self):
        with pytest.raises(SmilesError, match="heteroatom"):
            parse_smiles("c1ccncc1")            # pyridine: a documented v1 gap

    def test_disconnected_smiles_is_refused(self):
        with pytest.raises(SmilesError, match="connected"):
            parse_smiles("C.C")

    def test_unbalanced_branch_is_refused(self):
        with pytest.raises(SmilesError):
            parse_smiles("CC(C")

    def test_unclosed_ring_is_refused(self):
        with pytest.raises(SmilesError, match="ring"):
            parse_smiles("c1ccccc")

    def test_unknown_element_is_refused(self):
        with pytest.raises(SmilesError):
            parse_smiles("[Zz]")

    def test_empty_is_refused(self):
        with pytest.raises(SmilesError):
            parse_smiles("   ")


def test_parsed_molecule_flows_into_structure_descent():
    # the whole point of the front door: a parsed molecule is a real Molecule the engine consumes
    from smartchem.smiles import parse_smiles as p
    from smartchem.structure_descent import capped_scissions

    paracetamol = p("CC(=O)Nc1ccc(O)cc1")
    water = p("O")
    edges, complete = capped_scissions(paracetamol, (water,))
    # among the valence-valid hydrolyses is the real one: products include 4-aminophenol + acetic acid
    aminophenol = p("Nc1ccc(O)cc1")
    acetic = p("CC(=O)O")
    assert any(
        {aminophenol, acetic} <= set(e.products) for e in edges
    ), "the parsed paracetamol did not derive the literature hydrolysis products"
