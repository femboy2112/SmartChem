"""M-4 v2: the W3 boundary made executable -- detection is real, and the refusals hold.

These tests protect two things at once: that the boundary DETECTORS are non-vacuous (they fire on a
real stereocentre / E/Z bond / keto-enol motif and stay silent on symmetric cases), and that the
engine REFUSES to cross the line -- naming stereochemistry it will not claim, and ranking only by
sourced evidence, never inventing an order from nothing.
"""

from smartchem.category import Bond, Molecule
from smartchem.decompiler_boundary import (
    RankingBasis,
    StereoRepresentation,
    cis_trans_candidates,
    evidence_ranking,
    stereo_status,
    stereocenters,
    tautomerizable,
)
from smartchem.structure import known_compounds


def _named(formula: str, name: str) -> Molecule:
    return next(s.molecule for s in known_compounds(formula) if s.name == name)


class TestStereocenterDetection:
    def test_a_chiral_carbon_is_detected(self):
        # CHFClBr -- four distinct substituents on one carbon: a textbook stereocentre
        chiral = Molecule(("C", "H", "F", "Cl", "Br"),
                          frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4)}))
        assert stereocenters(chiral) == (0,)

    def test_a_symmetric_carbon_is_not_a_stereocenter(self):
        # CH2Cl2 -- two identical H and two identical Cl: not stereogenic
        dcm = Molecule(("C", "Cl", "Cl", "H", "H"),
                       frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4)}))
        assert stereocenters(dcm) == ()
        assert stereocenters(_named("CH4", "methane")) == ()


class TestCisTransDetection:
    def test_a_2_butene_double_bond_is_an_ez_candidate(self):
        butene = Molecule(
            ("C", "C", "C", "C", "H", "H", "H", "H", "H", "H", "H", "H"),
            frozenset({Bond(0, 1), Bond(1, 2, 2), Bond(2, 3), Bond(0, 4), Bond(0, 5), Bond(0, 6),
                       Bond(1, 7), Bond(2, 8), Bond(3, 9), Bond(3, 10), Bond(3, 11)}))
        assert cis_trans_candidates(butene) == ((1, 2),)

    def test_ethylene_is_not_an_ez_candidate(self):
        ethylene = Molecule(("C", "C", "H", "H", "H", "H"),
                            frozenset({Bond(0, 1, 2), Bond(0, 2), Bond(0, 3), Bond(1, 4), Bond(1, 5)}))
        assert cis_trans_candidates(ethylene) == ()

    def test_aromatic_ring_bonds_are_not_ez_candidates(self):
        # paracetamol's Kekule ring double bonds are in a ring (not bridges) -> excluded; its
        # carbonyl O has no second substituent -> excluded. So it reports NO E/Z element.
        assert cis_trans_candidates(_named("C8H9NO2", "paracetamol")) == ()

    def test_paracetamol_is_reported_constitutional_and_not_stereogenic(self):
        status = stereo_status(_named("C8H9NO2", "paracetamol"))
        assert status.representation is StereoRepresentation.CONSTITUTIONAL_ONLY
        assert not status.is_stereogenic


class TestStereoStatusRefuses:
    def test_status_is_always_constitutional_and_names_the_unrepresented_freedom(self):
        chiral = Molecule(("C", "H", "F", "Cl", "Br"),
                          frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4)}))
        status = stereo_status(chiral)
        assert status.representation is StereoRepresentation.CONSTITUTIONAL_ONLY  # never claims R/S
        assert status.tetrahedral_stereocenters == (0,)
        assert status.is_stereogenic
        assert "NOT represented or claimed" in status.note   # the refusal is explicit


class TestTautomerDetection:
    def test_acetone_has_a_keto_enol_motif(self):
        assert tautomerizable(_named("C3H6O", "acetone")) != ()

    def test_formaldehyde_has_no_alpha_hydrogen(self):
        # H2C=O has a carbonyl but no alpha carbon -> no keto-enol partner
        assert tautomerizable(_named("CH2O", "formaldehyde")) == ()


class TestEvidenceRankingRefusesToPredict:
    class _Cond:
        def __init__(self, declared): self.is_declared = declared

    class _Haz:
        def __init__(self, flags): self.flags = flags

    class _Review:
        def __init__(self, declared, flags):
            self.conditions = TestEvidenceRankingRefusesToPredict._Cond(declared)
            self.hazard = TestEvidenceRankingRefusesToPredict._Haz(flags)

    def test_orders_by_sourced_evidence_when_present(self):
        no_cond = self._Review(False, [])
        with_cond = self._Review(True, ["DOCUMENTED_HAZARD"])
        ranking = evidence_ranking([no_cond, with_cond])
        assert ranking.basis is RankingBasis.EVIDENCE_ORDERED
        assert ranking.order == (1, 0)                      # the sourced one first
        assert "NOT a reactivity" in ranking.note

    def test_refuses_to_rank_without_an_evidence_basis(self):
        # no edge carries sourced conditions -> UNRANKED, input order preserved, no invented order
        reviews = [self._Review(False, []), self._Review(False, ["DOCUMENTED_HAZARD"])]
        ranking = evidence_ranking(reviews)
        assert ranking.basis is RankingBasis.UNRANKED
        assert ranking.order == (0, 1)                      # untouched
        assert "refuses to invent one" in ranking.note
