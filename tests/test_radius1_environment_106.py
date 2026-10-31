"""#106 (infra W0.3) -- the bounded radius-1 atom-environment predicate.

:class:`~smartchem.radius1_environment.AtomEnvironment` is the LOCAL discriminator a context-free
:class:`~smartchem.reaction_center.ReactionCenter` cannot supply.  These pin the two facts its first consumer
(the #112 SN2 recognizer) reads -- ``is_saturated_carbon`` (the sp3 proxy that excludes aromatic/vinylic/acyl
carbons) and ``carbon_neighbour_count`` (the substitution degree) -- plus the general ``star`` datum and the
bounds/fail-closed behaviour.
"""
from __future__ import annotations

import pytest

from smartchem.category import Molecule
from smartchem.radius1_environment import AtomEnvironment
from smartchem.smiles import parse_smiles


def _carbon_bearing(mol: Molecule, element: str) -> int:
    """The index of a carbon bonded to an atom of ``element`` (the reacting carbon in our substrates)."""
    atoms = mol.atoms
    for b in mol.bonds:
        if atoms[b.i] == "C" and atoms[b.j] == element:
            return b.i
        if atoms[b.j] == "C" and atoms[b.i] == element:
            return b.j
    raise AssertionError(f"no C-{element} bond in {atoms}")


def test_saturated_primary_carbon():
    # ethyl bromide: the C-Br carbon is sp3 with two hydrogens (primary).
    mol = parse_smiles("CCBr")
    env = AtomEnvironment.at(mol, _carbon_bearing(mol, "Br"))
    assert env.element == "C"
    assert env.is_saturated_carbon is True
    assert env.hydrogen_count == 2
    assert env.max_incident_order == 1


def test_tertiary_carbon_is_saturated_but_has_no_hydrogen():
    # tert-butyl bromide: sp3 but ZERO hydrogens (fully substituted) -- the SN2 steric gate's target.
    mol = parse_smiles("CC(C)(C)Br")
    env = AtomEnvironment.at(mol, _carbon_bearing(mol, "Br"))
    assert env.is_saturated_carbon is True
    assert env.hydrogen_count == 0


@pytest.mark.parametrize(
    "smi,element,why",
    [
        ("C=CBr", "Br", "vinylic: the C-Br carbon carries a C=C (order 2)"),
        ("CC(=O)Cl", "Cl", "acyl: the C-Cl carbon is a carbonyl (C=O order 2)"),
        ("Clc1ccccc1", "Cl", "aromatic: the C-Cl carbon carries a Kekule order-2 ring bond"),
    ],
)
def test_unsaturated_carbons_are_not_saturated(smi, element, why):
    mol = parse_smiles(smi)
    env = AtomEnvironment.at(mol, _carbon_bearing(mol, element))
    assert env.is_saturated_carbon is False, why
    assert env.max_incident_order >= 2


def test_heteroatom_is_not_a_saturated_carbon():
    # the nucleophile oxygen of methanol: not carbon, so is_saturated_carbon is False regardless of its bonds.
    mol = parse_smiles("CO")
    o_idx = mol.atoms.index("O")
    env = AtomEnvironment.at(mol, o_idx)
    assert env.element == "O"
    assert env.is_saturated_carbon is False
    assert env.hydrogen_count == 1  # methanol O-H


def test_star_is_the_sorted_radius1_multiset():
    # methyl bromide: the carbon's star is exactly {Br(1), H(1), H(1), H(1)} -- coordinate-free, sorted.
    mol = parse_smiles("CBr")
    env = AtomEnvironment.at(mol, _carbon_bearing(mol, "Br"))
    assert env.star == (("Br", 1), ("H", 1), ("H", 1), ("H", 1))


def test_benzylic_carbon_is_saturated_though_adjacent_to_a_ring():
    # benzyl bromide: the sp3 CH2 is a competent SN2 centre even though a radius-1 neighbour is an aromatic C.
    mol = parse_smiles("BrCc1ccccc1")
    env = AtomEnvironment.at(mol, _carbon_bearing(mol, "Br"))
    assert env.is_saturated_carbon is True
    assert env.hydrogen_count == 2  # the benzylic CH2; the ring's own unsaturation is radius-2, not seen


def test_out_of_range_index_raises():
    mol = parse_smiles("CBr")
    with pytest.raises(IndexError):
        AtomEnvironment.at(mol, len(mol.atoms))
    with pytest.raises(IndexError):
        AtomEnvironment.at(mol, -1)


def test_rejects_non_molecule():
    with pytest.raises(TypeError):
        AtomEnvironment.at(("C", "Br"), 0)  # not a Molecule


def test_unbonded_atom_has_empty_star():
    env = AtomEnvironment.at(Molecule.atom("C"), 0)
    assert env.star == ()
    assert env.max_incident_order == 0
    assert env.is_saturated_carbon is True  # vacuously: a bare carbon atom has no order>1 bond
    assert env.hydrogen_count == 0
