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
    def test_the_formula_level_hydrolysis_edge_names_species_honestly(self):
        # decompile_and_review is FORMULA-level: C8H9NO2 now has two registered isomers, so it is
        # named AMBIGUOUSLY ("... or ...") rather than silently picking one. The single-isomer species
        # are still definitive. (The structure-derived path names paracetamol definitively -- see
        # TestStructureResolvedReview.)
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        r = _hydrolysis(reviews)
        named = r.named_equation()
        assert "paracetamol" in named and "4-aminophenyl acetate" in named   # both isomers shown
        assert " or " in named                                                # ambiguity is visible
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
        # both are registered now; the point stands -- each WHOLE token resolves to its OWN name,
        # the "H2O" inside "H2O2" is never matched (that would mangle it to "H2O (water)2").
        assert named == "H2O2 (hydrogen peroxide) -> H2O (water) + O"

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


class TestAdversarialHardening:
    """Regression bars for the three breaks the adversarial pass found -- each fires on its own
    counterexample, so a silent regression to clearance-by-omission would trip here."""

    def test_f1_unassessed_hazards_are_loud_not_silent(self):
        # CO2 -> C + 2 O: CO2 now has a record, but the bare element buckets C/O do not; that gap
        # must still be flagged, not silent (the element buckets can never carry a compound hazard).
        edges, _ = admissible_edges(Formula.parse("CO2"))
        floor = next(e for e in edges if e.is_elemental_floor)
        prof = screen_edge(floor)
        assert HazardFlag.HAZARDS_UNASSESSED in prof.flags
        assert "UNASSESSED" in prof.notes and "not safe" in prof.notes.lower()

    def test_f1_partial_coverage_names_the_unassessed_species(self):
        # the elemental floor of acetic acid: acetic acid IS documented, but the bare element buckets
        # (C, O, H) have no record and must NOT read as assessed-clean. Retargeted at element buckets,
        # which stay permanently unassessed regardless of how far the compound hazard tables widen.
        from smartchem.decompiler_review import _collect_species_hazards
        edges, _ = admissible_edges(Formula.parse("C2H4O2"))
        floor = next(e for e in edges if e.is_elemental_floor)
        prof = screen_edge(floor)
        found, unassessed = _collect_species_hazards(floor)
        assert any(h.name == "acetic acid" for h in found)     # the documented species surfaced
        assert unassessed                                      # AND the element-bucket gap surfaced
        assert HazardFlag.DOCUMENTED_HAZARD in prof.flags
        assert HazardFlag.HAZARDS_UNASSESSED in prof.flags

    def test_f2_isomer_assumption_is_marked_where_a_name_is_attached(self):
        # a formula-level node labelled with one isomer's name/hazards carries the assumption flag...
        _b, reviews = decompile_and_review("C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O"])
        r = _hydrolysis(reviews)
        assert HazardFlag.ISOMER_ASSUMED in r.hazard.flags
        # ...and the flag tracks name attachment EXACTLY -- present iff some touched species resolves
        # to a registered compound. Asserted as the biconditional so it survives registry growth
        # (data widening registered CO2, so its floor now legitimately carries the flag; a still-
        # unregistered floor must not).
        from smartchem.decompiler_review import _edge_species
        from smartchem.structure import resolve_names
        for target in ("CO2", "N2O"):
            edges, _ = admissible_edges(Formula.parse(target))
            floor = next(e for e in edges if e.is_elemental_floor)
            has_name = any(resolve_names(s) for s in _edge_species(floor))
            assert (HazardFlag.ISOMER_ASSUMED in screen_edge(floor).flags) == has_name

    def test_f3_isomer_ambiguous_fires_on_any_nondegenerate_interval(self):
        # C2H6O = ethanol or dimethyl ether: a same-sign but real enthalpy spread. The docstring's
        # own example must now get the flag it promises.
        edges, _ = admissible_edges(Formula.parse("C2H6O"))
        floor = next(e for e in edges if e.is_elemental_floor)
        prof = screen_edge(floor)
        assert prof.energy.assembly_lo_ev != prof.energy.assembly_hi_ev  # a real interval
        assert not prof.energy.sign_ambiguous                            # ...that does not cross zero
        assert HazardFlag.ISOMER_AMBIGUOUS in prof.flags                 # ...still flagged


class TestSynthesisConditions:
    def test_formula_decomposition_does_not_borrow_reverse_assembly_conditions(self):
        _b, reviews = decompile_and_review(
            "C8H9NO2", inventory=LITMUS_INVENTORY, medium=["H2O", "C2H4O2"]
        )
        by_eq = {r.edge.equation(): r for r in reviews}
        ketene_route = by_eq.get("C8H9NO2 -> C2H2O + C6H7NO")
        assert ketene_route is not None and not ketene_route.conditions.is_declared
        anhydride_route = by_eq.get("C8H9NO2 + C2H4O2 -> C4H6O3 + C6H7NO")
        assert anhydride_route is not None and not anhydride_route.conditions.is_declared

    def test_exact_structural_assembly_can_carry_its_own_directional_conditions(self):
        from smartchem.experiment.routes import enumerate_routes
        from smartchem.structure import structure_by_name

        mol = lambda name: structure_by_name(name).molecule
        routes = enumerate_routes(
            mol("paracetamol"),
            reagents=(mol("water"), mol("acetic acid"), mol("acetic anhydride")),
            available=(mol("4-aminophenol"),),
            max_depth=1,
        )
        anhydride = next(
            step for route in routes for step in route.steps
            if step.equation().startswith("C4H6O3 + C6H7NO")
        )
        assert anhydride.envelope.is_declared
        assert anhydride.envelope.provenance
