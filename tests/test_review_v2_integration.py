"""M-4 v2 rung 4: the review layer wired to the structure registry + hazard + thermo data.

This is the litmus made concrete: one decompile_and_review call must surface, for paracetamol, the
real routes with NAMED compounds, ATTACHED sourced hazards, BROADENED energetics where the data is
good, and HONEST UNKNOWNs where it is not -- with nothing filtered out.
"""

from smartchem.decompiler import Formula, admissible_edges
from smartchem.decompiler_review import (
    HazardFlag,
    assess_edge_energy,
    decompile_and_review,
    screen_edge,
)

LITMUS_INVENTORY = ["C6H7NO", "C2H4O2", "C2H2O", "C4H6O3", "CO", "CO2", "CH4"]


def _hydrolysis(reviews):
    want = "C8H9NO2 + H2O -> C2H4O2 + C6H7NO"
    return next(r for r in reviews if r.mediated and r.edge.equation() == want)


class TestNamesSurface:
    def test_the_hydrolysis_edge_reads_in_compound_names(self):
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        r = _hydrolysis(reviews)
        named = r.named_equation()
        assert "C8H9NO2 (paracetamol)" in named
        assert "C6H7NO (4-aminophenol)" in named
        assert "C2H4O2 (acetic acid)" in named
        assert "H2O (water)" in named

    def test_named_equation_is_whole_token_safe(self):
        # H2O2 -> H2O + O : the H2O inside H2O2 must NOT be annotated; only the real H2O token is.
        from smartchem.decompiler_review import EdgeReview, coherence_score
        edges, _ = admissible_edges(Formula.parse("H2O2"), (Formula.parse("H2O"),))
        edge = next(e for e in edges if e.equation() == "H2O2 -> H2O + O")
        review = EdgeReview(edge, coherence_score(edge), screen_edge(edge))
        named = review.named_equation()
        assert named == "H2O2 -> H2O (water) + O"  # H2O2 untouched, H2O annotated

    def test_unregistered_species_are_not_renamed(self):
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        r = _hydrolysis(reviews)
        # CO/CO2/CH4 have no registry entry -- they must never appear parenthesised
        assert "(CO)" not in r.named_equation() and "(carbon" not in r.named_equation().lower()


class TestHazardsAttach:
    def test_the_hydrolysis_edge_carries_sourced_hazards_for_its_species(self):
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        r = _hydrolysis(reviews)
        names = {h.name for h in r.hazard.species_hazards}
        assert {"paracetamol", "acetic acid", "4-aminophenol"} <= names
        assert HazardFlag.DOCUMENTED_HAZARD in r.hazard.flags
        # the regulated-degradant fact is in the attached record a chemist reads
        aminophenol = next(h for h in r.hazard.species_hazards if h.name == "4-aminophenol")
        assert "227" in aminophenol.regulatory

    def test_a_ketene_edge_warns_the_gas_is_fatal(self):
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        ketene_edges = [r for r in reviews if "C2H2O" in r.edge.equation()]
        assert ketene_edges
        r = ketene_edges[0]
        ketene = next(h for h in r.hazard.species_hazards if h.name == "ketene")
        assert "H330" in ketene.ghs_codes  # fatal if inhaled
        assert "FATAL IF INHALED" in ketene.summary.upper()

    def test_nothing_is_filtered_by_hazard(self):
        # inform-never-neuter: every generated edge is still present after review
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        plain, _pc = admissible_edges(Formula.parse("C8H9NO2"),
                                      tuple(Formula.parse(s) for s in LITMUS_INVENTORY))
        assert len(reviews) >= len(plain)  # plain + mediated, none dropped


class TestEnergeticsBroadenedButHonest:
    def test_ketene_and_acetic_acid_now_have_real_energetics(self):
        for f in ("C2H2O", "C2H4O2"):
            edges, _ = admissible_edges(Formula.parse(f))
            floor = next(e for e in edges if e.is_elemental_floor)
            ea = assess_edge_energy(floor)
            assert ea.covered and ea.assembly_lo_ev < 0  # exothermic assembly, a real number

    def test_paracetamol_edges_stay_energetics_unknown(self):
        # paracetamol is 298 K-only and 4-aminophenol's sources disagree: the convention/coverage
        # gap is real, so the honest output is UNKNOWN, not a fabricated number.
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        r = _hydrolysis(reviews)
        assert HazardFlag.ENERGETICS_UNKNOWN in r.hazard.flags
        assert not r.hazard.assessed


class TestSynthesisConditions:
    def test_the_ketene_and_anhydride_routes_now_carry_declared_conditions(self):
        _b, reviews = decompile_and_review(
            "C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O", "C2H4O2"]
        )
        by_eq = {r.edge.equation(): r for r in reviews}
        ketene_route = by_eq.get("C8H9NO2 -> C2H2O + C6H7NO")
        assert ketene_route is not None and ketene_route.conditions.is_declared
        assert "in situ" in ketene_route.conditions.medium
        anhydride_route = by_eq.get("C8H9NO2 + C2H4O2 -> C4H6O3 + C6H7NO")
        assert anhydride_route is not None and anhydride_route.conditions.is_declared
        assert anhydride_route.conditions.provenance  # sourced, reverse-direction synthesis
