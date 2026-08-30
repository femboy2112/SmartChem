"""M-4b review layer: source-backed safety screen (inform, never neuter) + coherence ranking.

The energetics anchor is a *second blind path*: the assembly enthalpy this module computes from
formation enthalpies must equal `smartchem.data.reference.atomization_energy_ev`, which derives the
same quantity by a different route. Two independent paths agreeing is what makes the safety number
Verified rather than merely produced.
"""

import pytest

from smartchem.data import reference
from smartchem.decompiler import DecompositionEdge, Formula, build_decomposition
from smartchem.decompiler_review import (
    SAFETY_BANNER,
    EnergyAssessment,
    HazardFlag,
    _dfh_range_kj,
    assess_edge_energy,
    coherence_score,
    review_graph,
    screen_edge,
)

H = Formula.bucket("H")
OX = Formula.bucket("O")
C = Formula.bucket("C")
N = Formula.bucket("N")


def _edge(formula_str, *products, n=1):
    """Build an edge with products put into the constructor's required canonical order."""
    return DecompositionEdge(Formula.parse(formula_str), n, tuple(sorted(
        products, key=lambda pm: (pm[0].counts, pm[0].charge, pm[1])
    )))


_to_atoms = _edge  # alias: the atomisation cases read more clearly under the old name


class TestEnergyCrossCheck:
    # each edge fully atomises a tabulated molecule; the assembly enthalpy must equal minus the
    # reference atomization energy computed by an INDEPENDENT route.
    CASES = [
        ("H2O", ((H, 2), (OX, 1))),
        ("CO2", ((C, 1), (OX, 2))),
        ("CH4", ((C, 1), (H, 4))),
        ("NH3", ((H, 3), (N, 1))),
        ("CH3OH", ((C, 1), (H, 4), (OX, 1))),
    ]

    @pytest.mark.parametrize("formula,products", CASES)
    def test_assembly_enthalpy_equals_minus_reference_atomization(self, formula, products):
        edge = _to_atoms(formula, *products)
        ea = assess_edge_energy(edge)
        assert ea.covered
        assert ea.assembly_lo_ev == ea.assembly_hi_ev  # all species exactly covered
        assert abs(-ea.assembly_lo_ev - reference.atomization_energy_ev(formula)) < 1e-9

    def test_assembly_from_atoms_is_exothermic_and_flagged(self):
        # forming a molecule from bare atoms releases heat -- the litmus's exothermic reality
        prof = screen_edge(_to_atoms("H2O", (H, 2), (OX, 1)))
        assert prof.energy.is_exothermic_assembly is True
        assert HazardFlag.EXOTHERMIC_ASSEMBLY in prof.flags


class TestCoverageAndUnknownIsNotSafe:
    def test_uncovered_species_yields_loud_unknown_not_silence(self):
        # paracetamol has no tabulated formation enthalpy -> UNKNOWN, explicitly not "safe"
        edge = _edge("C8H9NO2", (Formula.parse("C6H7NO"), 1), (Formula.parse("C2H2O"), 1))
        prof = screen_edge(edge)
        assert not prof.assessed
        assert prof.energy.is_exothermic_assembly is None
        assert HazardFlag.ENERGETICS_UNKNOWN in prof.flags
        assert "not safe" in prof.notes
        assert prof.energy.uncovered_species  # names the gap

    def test_energy_assessment_bounds_are_both_set_or_both_none(self):
        with pytest.raises(ValueError):
            EnergyAssessment(-1.0, None, ())

    def test_isomer_ambiguity_is_surfaced_as_an_interval(self):
        # C2H6O = ethanol (-217.1) or dimethyl ether (-166.6): formula-level gives a real interval
        lo, hi = _dfh_range_kj(Formula.parse("C2H6O"))
        assert (round(lo, 1), round(hi, 1)) == (-217.1, -166.6)


class TestInformNeverCensor:
    def test_screen_always_returns_a_profile(self):
        # even a maximally exothermic edge is screened, never hidden or refused
        prof = screen_edge(_to_atoms("CO2", (C, 1), (OX, 2)))
        assert prof.energy.assembly_lo_ev < 0  # strongly exothermic
        assert HazardFlag.EXOTHERMIC_ASSEMBLY in prof.flags  # flagged, not dropped

    def test_review_graph_drops_no_edge(self):
        g = build_decomposition("C3H6O", ["CO", "CO2", "CH4", "H2O", "C2H6", "C2H4"])
        _banner, reviews = review_graph(g)
        assert len(reviews) == len(g.edges)  # every edge survives; nothing censored

    def test_banner_states_the_doctrine(self):
        assert "INFORMATIONAL" in SAFETY_BANNER and "not safe" in SAFETY_BANNER.lower()


class TestCoherenceRanking:
    def test_elemental_floor_scores_zero(self):
        assert coherence_score(_to_atoms("H2O", (H, 2), (OX, 1))) == 0.0

    def test_all_molecular_split_scores_one(self):
        edge = _edge("C8H9NO2", (Formula.parse("C6H7NO"), 1), (Formula.parse("C2H2O"), 1))
        assert coherence_score(edge) == 1.0

    def test_review_ranks_the_real_backbone_first(self):
        inv = ["C6H7NO", "C2H2O", "C2H4O2", "H2O", "CO", "CO2", "NH3", "CH4"]
        g = build_decomposition("C8H9NO2", inv, max_edges=40000)
        _banner, reviews = review_graph(g, reactant=Formula.parse("C8H9NO2"))
        assert reviews[0].coherence == 1.0  # p-aminophenol + ketene floats to the top
        assert reviews[0].edge.equation() == "C8H9NO2 -> C2H2O + C6H7NO"
        # ranking is monotone non-increasing in coherence
        cohs = [r.coherence for r in reviews]
        assert cohs == sorted(cohs, reverse=True)
