"""M-4b C2: mediated (solution/byproduct) decomposition edges.

The headline is the litmus reaction itself: with water in the medium the generator produces
`paracetamol + H2O -> 4-aminophenol + acetic acid`, the real hydrolysis that v1's own-atoms-only
model structurally could not represent. Every construction invariant is isolated.
"""

import pytest

from smartchem.decompiler import Formula
from smartchem.decompiler_mediated import MediatedEdge, mediated_edges

H = Formula.bucket("H")
OX = Formula.bucket("O")
PARACETAMOL = Formula.parse("C8H9NO2")
AMINOPHENOL = Formula.parse("C6H7NO")
ACETIC = Formula.parse("C2H4O2")
WATER = Formula.parse("H2O")


def _s(*pairs):
    return tuple(sorted(pairs, key=lambda pm: (pm[0].counts, pm[0].charge, pm[1])))


class TestTheRealHydrolysisIsGenerated:
    def test_paracetamol_plus_water_gives_aminophenol_plus_acetic_acid(self):
        edges, complete = mediated_edges(
            "C8H9NO2", inventory=["C6H7NO", "C2H4O2"], medium=["H2O"], max_reagent_instances=1
        )
        assert complete
        hit = [
            e for e in edges
            if {p for p, _ in e.products} == {AMINOPHENOL, ACETIC}
            and dict(e.reagents) == {WATER: 1}
        ]
        assert len(hit) == 1
        assert hit[0].equation() == "C8H9NO2 + H2O -> C2H4O2 + C6H7NO"

    def test_every_edge_conserves_the_augmented_system_and_descends(self):
        edges, _ = mediated_edges("C8H9NO2", inventory=["C6H7NO", "C2H4O2"], medium=["H2O"])
        for e in edges:
            want = {s: e.reactant_multiplicity * k for s, k in e.reactant.counts}
            for r, m in e.reagents:
                for s, k in r.counts:
                    want[s] = want.get(s, 0) + m * k
            got = {}
            for p, m in e.products:
                for s, k in p.counts:
                    got[s] = got.get(s, 0) + m * k
            assert got == want
            assert all(p.rank < e.reactant.rank for p, _ in e.products)
            assert all(r.rank < e.reactant.rank for r, _ in e.reagents)

    def test_no_medium_means_no_mediated_edges(self):
        edges, _ = mediated_edges("C8H9NO2", inventory=["C6H7NO", "C2H4O2"], medium=[])
        assert edges == ()

    def test_a_reagent_must_come_from_the_declared_medium(self):
        # water is not offered -> the hydrolysis edge cannot be built
        edges, _ = mediated_edges("C8H9NO2", inventory=["C6H7NO", "C2H4O2"], medium=["CO2"])
        assert not any(WATER in dict(e.reagents) for e in edges)


class TestMediatedEdgeInvariants:
    def test_the_real_edge_builds(self):
        e = MediatedEdge(PARACETAMOL, 1, ((WATER, 1),), _s((ACETIC, 1), (AMINOPHENOL, 1)))
        assert e.equation() == "C8H9NO2 + H2O -> C2H4O2 + C6H7NO"

    def test_no_reagent_is_refused(self):
        with pytest.raises((TypeError, ValueError)):
            MediatedEdge(PARACETAMOL, 1, (), _s((ACETIC, 1), (AMINOPHENOL, 1)))

    def test_growing_product_is_refused(self):
        with pytest.raises(ValueError, match="non-descending"):
            MediatedEdge(Formula.parse("CH2O"), 1, ((WATER, 1),), _s((Formula.parse("C2H2O"), 1), (H, 2)))

    def test_passthrough_reagent_is_refused(self):
        # a species that is both a reagent and a product is a spectator, not mediation
        with pytest.raises(ValueError, match="pass-through"):
            MediatedEdge(Formula.parse("CH2O2"), 1, ((WATER, 1),), _s((Formula.parse("CO"), 1), (WATER, 1)))

    def test_nonconserving_augmented_system_is_refused(self):
        with pytest.raises(ValueError, match="not conserved"):
            MediatedEdge(Formula.parse("CH4"), 1, ((WATER, 1),), _s((Formula.parse("CO"), 1), (H, 2)))

    def test_non_primitive_edge_is_refused(self):
        with pytest.raises(ValueError, match="not primitive"):
            MediatedEdge(PARACETAMOL, 2, ((WATER, 2),), _s((ACETIC, 2), (AMINOPHENOL, 2)))

    def test_digest_is_order_independent(self):
        a = MediatedEdge(PARACETAMOL, 1, ((WATER, 1),), _s((ACETIC, 1), (AMINOPHENOL, 1)))
        b = MediatedEdge(PARACETAMOL, 1, ((WATER, 1),), _s((AMINOPHENOL, 1), (ACETIC, 1)))
        assert a.digest == b.digest
