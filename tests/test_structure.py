"""M-4 v2 structure bridge: named compounds over real bond graphs.

The tests earn their keep by being differential, per the repo's recurring vacuous-guard lesson:
the composition guard is shown to REJECT a wrong structure, and the structural identity is shown to
be both relabel-INVARIANT (same molecule, permuted indices -> same id) and isomer-SEPARATING (same
formula, different connectivity -> different id). An identity that only echoed the formula would
pass the first and fail the second.
"""

import pytest

from smartchem.category import Bond, Molecule
from smartchem.contracts import canonical_digest
from smartchem.decompiler import Formula
from smartchem.smiles import parse_smiles
from smartchem.structure import (
    NamedStructure,
    StructureError,
    known_compounds,
    registered_structures,
    resolve_names,
    resolve_structure,
    structure_by_name,
)


class TestStructureByName:
    """The offline name->structure resolver that keys warming/evidence by a compound's NAME."""

    def test_resolves_a_common_name_case_and_whitespace_insensitively(self):
        assert structure_by_name("  Acetic Acid ").name == "acetic acid"

    def test_resolves_a_synonym(self):
        # acetaminophen is a registered synonym of paracetamol
        assert structure_by_name("acetaminophen").name == "paracetamol"

    def test_an_unregistered_name_is_a_loud_none_not_a_guess(self):
        assert structure_by_name("unobtainium") is None

    def test_empty_input_is_none(self):
        assert structure_by_name("") is None and structure_by_name("   ") is None


def _relabel(molecule: Molecule, perm: dict[int, int]) -> Molecule:
    """Rebuild a molecule under an index permutation (new_index = perm[old_index])."""
    n = len(molecule.atoms)
    new_atoms = [""] * n
    for old, sym in enumerate(molecule.atoms):
        new_atoms[perm[old]] = sym
    new_bonds = frozenset(Bond(perm[b.i], perm[b.j], b.order) for b in molecule.bonds)
    return Molecule(atoms=tuple(new_atoms), bonds=new_bonds, charge=molecule.charge)


class TestTheGuardBites:
    def test_every_registered_structure_matches_its_declared_formula(self):
        # the whole registry loaded, so every _check already passed; assert it explicitly too
        for st in registered_structures():
            assert st.formula == Formula.parse(st.expected_formula)
            assert dict(st.composition) == Formula.parse(st.expected_formula).as_dict

    def test_a_mismatched_formula_is_rejected(self):
        # real water graph, but claim it is H3O -- the guard must reject, not register a lie
        water = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
        with pytest.raises(StructureError):
            NamedStructure("not-water", water, "H3O")

    def test_a_nonmolecule_is_rejected(self):
        with pytest.raises(StructureError):
            NamedStructure("bad", "not a molecule", "H2O")  # type: ignore[arg-type]


class TestForgetfulMap:
    def test_formula_is_the_composition_of_the_bond_graph(self):
        pap = known_compounds("C6H7NO")[0]
        assert pap.formula == Formula.parse("C6H7NO")
        # forgetting the bonds gives exactly the v1 node identity
        assert Formula.of(pap.molecule.formula, pap.molecule.charge) == pap.formula


class TestRegistryLookup:
    def test_resolve_names_for_the_litmus_species(self):
        # C8H9NO2 now resolves to BOTH registered isomers (isomer-keying) -- formula-level is
        # ambiguous by design; a structure resolution picks one.
        assert set(resolve_names("C8H9NO2")) == {"paracetamol", "4-aminophenyl acetate"}
        assert resolve_names("C6H7NO") == ("4-aminophenol",)
        assert resolve_names("C2H2O") == ("ketene",)
        assert resolve_names("C2H4O2") == ("acetic acid",)

    def test_unregistered_formula_resolves_to_nothing(self):
        assert resolve_names({"C": 99}) == ()
        assert known_compounds("Xe") == ()

    def test_synonyms_carry_the_names_a_chemist_uses(self):
        pap = next(s for s in known_compounds("C8H9NO2") if s.name == "paracetamol")  # not [0]
        assert "acetaminophen" in pap.all_names
        assert pap.cas == "103-90-2"
        # common name leads, and names are deduplicated
        assert pap.all_names[0] == "paracetamol"
        assert len(pap.all_names) == len(set(pap.all_names))


class TestStructuralIdentity:
    def test_identity_is_relabel_invariant(self):
        # permute the atom indices of every registered structure; canonical identity must not move
        for st in registered_structures():
            n = len(st.molecule.atoms)
            perm = {i: (i + 3) % n for i in range(n)}  # a fixed nontrivial permutation
            relabeled = _relabel(st.molecule, perm)
            assert relabeled.formula == st.molecule.formula  # sanity: same composition
            assert canonical_digest(relabeled.canonical()) == st.structure_identity

    def test_identity_separates_two_isomers_of_one_formula(self):
        # acetic acid vs methyl formate: both C2H4O2, different connectivity -> different identity.
        # An identity that merely echoed the formula would (wrongly) make these equal.
        acetic = known_compounds("C2H4O2")[0]
        methyl_formate = Molecule(
            ("C", "O", "O", "C", "H", "H", "H", "H"),
            frozenset({
                Bond(0, 1, 2), Bond(0, 2), Bond(2, 3), Bond(0, 4),
                Bond(3, 5), Bond(3, 6), Bond(3, 7),
            }),
        )
        assert methyl_formate.formula == acetic.molecule.formula  # same formula
        mf = NamedStructure("methyl formate", methyl_formate, "C2H4O2")
        assert mf.structure_identity != acetic.structure_identity  # different structure

    def test_all_litmus_structures_have_invariant_identity(self):
        # a substituted ring resolves under 1-WL even though a bare ring would not; assert we are
        # actually getting the presentation-invariant (not the asgiven: fallback) identity here.
        for st in registered_structures():
            assert st.canonical_identity_is_invariant
            assert not st.structure_identity.startswith("asgiven:")


class TestDigestible:
    def test_named_structure_has_a_digest(self):
        st = known_compounds("C2H2O")[0]
        assert isinstance(st.digest, str) and len(st.digest) == 64


class TestS2Mid1CompetingProductIsomers:
    """S2/Mid-1: four new registered isomers -- ooh, TWO whole competing pairs, one alcohol one
    dinitrobenzene -- so selectivity has more than the paracetamol fork to chew on."""

    def test_propanol_isomers_parse_and_resolve_by_name(self):
        assert resolve_structure(parse_smiles("CCCO")).name == "propan-1-ol"
        assert resolve_structure(parse_smiles("CC(O)C")).name == "propan-2-ol"

    def test_dinitrobenzene_isomers_parse_and_resolve_by_name(self):
        meta = parse_smiles("[O-][N+](=O)c1cccc([N+](=O)[O-])c1")
        para = parse_smiles("[O-][N+](=O)c1ccc([N+](=O)[O-])cc1")
        assert resolve_structure(meta).name == "1,3-dinitrobenzene"
        assert resolve_structure(para).name == "1,4-dinitrobenzene"

    def test_propanol_formula_has_at_least_two_registered_isomers(self):
        assert len(known_compounds("C3H8O")) >= 2

    def test_dinitrobenzene_formula_has_at_least_two_registered_isomers(self):
        assert len(known_compounds("C6H4N2O4")) >= 2
