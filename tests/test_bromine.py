"""Element-set breadth: Bromine (Z=35) in the element table unblocks halogen chemistry end to end.

The parse layer already handled F/Cl/Br/I; the only gap was a single missing periodic-table row for Br, which
fail-closed the whole Formula-computing path (scission, NamedStructure, selectivity composition) for EVERY
bromide -- and alkyl bromides / HBr are the canonical substrates of Markovnikov-HX addition and Zaitsev
elimination. This pins that the SOURCED Br row is present and that a bromide now flows through the pipeline
(the two probes that previously raised ``unknown element 'Br'``).
"""
from smartchem.atoms import PT
from smartchem.decompiler import Formula
from smartchem.smiles import parse_smiles
from smartchem.structure import NamedStructure
from smartchem.structure_descent import scission_edges


class TestBromineInTheElementTable:
    def test_bromine_is_present_with_the_sourced_descriptors(self):
        assert "Br" in PT
        br = PT["Br"]
        assert (br.atomic_number, br.group, br.period) == (35, 17, 4)
        assert br.ie_list_ev[0] == 11.814   # NIST ASD IE1 (Kramida et al. 2024)
        assert br.ea_list_ev[0] == 3.364    # Blondel et al. 1989 EA1
        assert br.radius_pm == 114.0        # Pyykko & Atsumi 2009 single-bond covalent radius
        assert br.mass_amu == 79.904        # IUPAC/CIAAW standard atomic weight

    def test_the_radius_is_in_the_same_convention_as_its_neighbours(self):
        # Br must sit monotonically between Cl and I in the SAME single-bond covalent-radius set, not a mix.
        assert PT["Cl"].radius_pm < PT["Br"].radius_pm < PT["I"].radius_pm  # 99 < 114 < 133

    def test_only_the_fetched_first_electron_affinity_is_carried(self):
        # no invented second EA: Br carries exactly the one fetched EA1 (unlike F/Cl/I's placeholder 2-tuples)
        assert len(PT["Br"].ea_list_ev) == 1


class TestBromideFlowsThroughEndToEnd:
    def test_a_bromide_formula_builds(self):
        assert str(Formula.of({"C": 3, "H": 7, "Br": 1})) == "BrC3H7"

    def test_scission_and_named_structure_no_longer_fail_closed_on_a_bromide(self):
        # both were the recon's exact previously-FAILING criteria ("unknown element 'Br'").
        assert len(scission_edges(parse_smiles("CCCBr"))) >= 1
        assert NamedStructure("1-bromopropane", parse_smiles("CCCBr"), "C3H7Br").name == "1-bromopropane"

    def test_markovnikov_hx_and_zaitsev_substrates_build(self):
        assert parse_smiles("Br").formula == {"Br": 1, "H": 1}  # HBr
        assert NamedStructure("2-bromopropane", parse_smiles("CC(Br)C"), "C3H7Br").name == "2-bromopropane"
