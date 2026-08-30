"""E4 -- the procedure drafter and the constraint fitter (the compiler backend), on the paracetamol litmus.

The north-star: given candidate routes to the same target, float the runnable-and-sourced ones above the
degenerate ones; and given a target BENCH (max T, max P, reagents on hand) select what runs and refuse what
does not, citing the exact bound.  The draft that comes out is a composability-checked draft over KNOWN
data, with every number bucket-labelled and every gap loud.
"""
from fractions import Fraction

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment.drafter import (
    ConstraintBox,
    RouteFitStatus,
    draft_procedure,
    fit_route,
    rank_routes,
)
from smartchem.experiment.equipment import EquipmentKind
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles

AMP = parse_smiles("Nc1ccc(O)cc1")
ANH = parse_smiles("CC(=O)OC(=O)C")
PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
ACOH = parse_smiles("CC(=O)O")
WATER = parse_smiles("O")
KETENE = parse_smiles("C=C=O")


def _env(tlo, thi, prov, medium="", pres=None):
    kw = dict(temperature=Interval(tlo, thi, "K"), medium=medium,
              status=EvidenceStatus.EXPERIMENTAL, provenance=prov)
    if pres:
        kw["pressure"] = Interval(pres[0], pres[1], "atm")
    return ConditionEnvelope(**kw)


def _anhydride_route(pres=None):
    return ExperimentRoute.of(ExperimentStep.assembling(
        PARA, (AMP, ANH), (PARA, ACOH), reagents=(ANH,),
        envelope=_env(295, 353, "ACS teaching synthesis", "aqueous, mild acid; volumetric", pres=pres),
    ))


def _ketene_route():
    return ExperimentRoute.of(
        ExperimentStep.assembling(KETENE, (ACOH,), (KETENE, WATER),
                                  envelope=_env(973, 1023, "acetic acid pyrolysis")),
        ExperimentStep.assembling(PARA, (KETENE, AMP), (PARA,),
                                  envelope=_env(273, 298, "ketene acetylation")),
    )


class TestRanking:
    def test_composable_route_ranks_above_degenerate_route(self):
        ranked = rank_routes([_ketene_route(), _anhydride_route()])
        assert ranked[0].route == _anhydride_route()  # the real synthesis, not the ketene path
        assert ranked[-1].composability.verdict == "DEGENERATE"


class TestConstraintFitting:
    def test_a_bench_that_cannot_reach_the_temperature_excludes_the_route(self):
        # a burner that only reaches 1200 C = 1473 K cannot run the 1000 K ketene pyrolysis
        box = ConstraintBox(max_temperature_k=1473)
        fit = fit_route(_ketene_route(), box)
        assert fit.status is RouteFitStatus.EXCLUDED  # degenerate anyway, but also over-temp is captured

    def test_a_route_within_the_box_with_declared_dims_fits(self):
        # declare an ambient pressure so the pressure constraint can be confirmed
        box = ConstraintBox(max_temperature_k=1473, max_pressure_atm=Fraction(3, 2))
        fit = fit_route(_anhydride_route(pres=(1, 1)), box)
        assert fit.status is RouteFitStatus.FITS

    def test_an_undeclared_constrained_dimension_is_unknown_not_a_silent_fit(self):
        # the bench caps pressure but the step declares none -> cannot confirm fit -> UNKNOWN, never FITS
        box = ConstraintBox(max_pressure_atm=Fraction(3, 2))
        fit = fit_route(_anhydride_route(pres=None), box)
        assert fit.status is RouteFitStatus.UNKNOWN
        assert any("pressure undeclared" in g for g in fit.gaps)

    def test_a_missing_reagent_excludes_the_route(self):
        # bench only has 4-aminophenol and water, not acetic anhydride
        box = ConstraintBox(available_reagents=frozenset({"4-aminophenol", "H2O", "water"}))
        fit = fit_route(_anhydride_route(), box)
        assert fit.status is RouteFitStatus.EXCLUDED
        assert any("not in the available-reagent inventory" in e for e in fit.exclusions)

    def test_a_missing_equipment_kind_excludes_the_route(self):
        # a bench with no heating apparatus cannot run a heated step
        box = ConstraintBox(available_equipment=frozenset({EquipmentKind.VESSEL, EquipmentKind.MEASURING}))
        fit = fit_route(_anhydride_route(), box)
        assert fit.status is RouteFitStatus.EXCLUDED


class TestDraft:
    def test_the_draft_carries_banner_equipment_and_ceiling(self):
        d = draft_procedure(_anhydride_route(), feed={AMP: 1, ANH: Fraction(6, 5)})
        text = d.render()
        assert "NOT a predicted successful synthesis" in text  # the honesty banner
        assert "Bunsen" in text or "hotplate" in text or "water bath" in text  # the equipment click
        assert "fume hood" in text  # sourced-hazard containment
        assert d.ceiling.final_target_mol == Fraction(1)  # aminophenol limits at 1 mol
        # every accounting quantity is bucket-labelled
        for sa in d.accounting.per_step:
            for q in sa.quantities():
                assert q.bucket.value in {"CONSERVATION", "COMPOSABILITY", "KNOWN_SOURCED", "UNKNOWN"}

    def test_draft_without_feed_omits_the_ceiling(self):
        d = draft_procedure(_anhydride_route())
        assert d.ceiling is None
