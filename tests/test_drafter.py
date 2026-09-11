"""E4 -- the route dossier and constraint fitter (the compiler backend), on the paracetamol litmus.

The north-star: given candidate routes to the same target, float the better-evidenced formal candidates above
degenerate ones; and given declared bounds, identify fits/exclusions without asserting bench readiness.
Every dossier number is bucket-labelled and every gap remains loud.
"""
from fractions import Fraction

import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment.drafter import (
    ConstraintBox,
    RouteDossier,
    RouteFitStatus,
    _route_score,
    draft_route_dossier,
    fit_route,
    rank_routes,
)
from smartchem.data.kinetics import KineticRef, KineticTable
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


class TestRateAwareRanking:
    """A FROZEN/SLOW rate is a LAST-resort ranking tiebreaker only -- it never touches a grade."""

    def _n2o5_route(self):
        a = parse_smiles("O=[N+]([O-])O[N+](=O)[O-]")
        n = parse_smiles("[N+](=O)[O-]")
        o = parse_smiles("O=O")
        return ExperimentRoute.of(ExperimentStep.assembling(o, (a, a), (n, n, n, n, o)))

    def _table(self, ea, log10a):
        rs = (("O=[N+]([O-])O[N+](=O)[O-]", 2),)
        ps = (("[N+](=O)[O-]", 4), ("O=O", 1))
        return KineticTable((KineticRef(rs, ps, "t", ea, log10a, "s^-1", (298.0, 338.0), "synthetic test"),))

    def test_rate_is_the_last_resort_tiebreaker_fast_floats_frozen_sinks(self):
        route, box = self._n2o5_route(), ConstraintBox()
        fast = fit_route(route, box, kinetics=self._table(10.0, 13.0))     # low barrier -> FAST
        frozen = fit_route(route, box, kinetics=self._table(200.0, 13.0))  # high barrier -> FROZEN
        empty = fit_route(route, box, kinetics=KineticTable(()))           # no data -> UNKNOWN
        sf, sfr, se = _route_score(fast), _route_score(frozen), _route_score(empty)
        assert len(sf) == 11                    # DISCONN-SEL-01 appended the DERIVED tier DEAD-LAST; rate is now [-2]
        assert sf[-1] == sfr[-1] == se[-1]      # same route -> identical derived rank (the true dead-last tier ties)
        assert sf[:-2] == sfr[:-2] == se[:-2]   # tied on every dimension above the rate tier (incl. the M2b tiers)
        assert sf[-2] < se[-2] < sfr[-2]        # FAST < UNKNOWN(neutral middle) < FROZEN, the last SOURCED tiebreaker
        assert fast.kinetics.verdict == "FAST" and frozen.kinetics.verdict == "FROZEN"

    def test_unknown_rate_is_neutral_never_a_penalty_for_missing_data(self):
        route, box = self._n2o5_route(), ConstraintBox()
        empty = _route_score(fit_route(route, box, kinetics=KineticTable(())))
        frozen = _route_score(fit_route(route, box, kinetics=self._table(200.0, 13.0)))
        assert empty[-2] < frozen[-2]  # rate tier is now [-2] (derived is dead-last): UNKNOWN (2) < sourced FROZEN (4)


class TestConstraintFitting:
    @pytest.mark.parametrize("kwargs", [
        {"max_temperature_k": 0},
        {"max_pressure_atm": -1},
        {"max_temperature_k": float("inf")},
    ])
    def test_physical_bounds_must_be_finite_and_positive(self, kwargs):
        with pytest.raises(ValueError):
            ConstraintBox(**kwargs)

    def test_pressure_floor_cannot_exceed_ceiling(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            ConstraintBox(min_pressure_atm=2, max_pressure_atm=1)

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

    def test_an_empty_box_is_unconstrained_never_a_silent_fit(self):
        # FIT-SEM-01: with NO bench constraint declared, nothing was assessed -- the route is UNCONSTRAINED,
        # never FITS (which would read as confirmed bench compatibility).  Same route that FITS a real box.
        fit = fit_route(_anhydride_route(pres=(1, 1)), ConstraintBox())
        assert fit.status is RouteFitStatus.UNCONSTRAINED
        assert not fit.fits
        assert fit.exclusions == () and fit.gaps == ()  # nothing wrong -- there was just nothing to check

    def test_fits_requires_the_box_to_actually_constrain_something(self):
        # the ONLY difference between UNCONSTRAINED and FITS for this route is whether the box declared a bound.
        route = _anhydride_route(pres=(1, 1))
        assert not fit_route(route, ConstraintBox()).fits
        assert fit_route(route, ConstraintBox(max_temperature_k=1473, max_pressure_atm=Fraction(3, 2))).fits

    def test_constrains_anything_reflects_declared_bounds(self):
        assert not ConstraintBox().constrains_anything
        assert ConstraintBox(max_temperature_k=1473).constrains_anything
        assert ConstraintBox(max_pressure_atm=Fraction(3, 2)).constrains_anything
        assert ConstraintBox(min_pressure_atm=Fraction(1, 2)).constrains_anything
        assert ConstraintBox(available_reagents=frozenset({"water"})).constrains_anything
        assert ConstraintBox(available_equipment=frozenset({EquipmentKind.VESSEL})).constrains_anything

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


class TestDossier:
    def test_the_dossier_carries_banner_equipment_and_ceiling(self):
        d = draft_route_dossier(_anhydride_route(), feed={AMP: 1, ANH: Fraction(6, 5)})
        assert type(d) is RouteDossier
        text = d.render()
        assert "NOT a predicted successful synthesis" in text  # the honesty banner
        assert "Bunsen" in text or "hotplate" in text or "water bath" in text  # the equipment click
        assert "fume hood" in text  # sourced-hazard containment
        assert d.ceiling.final_target_mol == Fraction(1)  # aminophenol limits at 1 mol
        # every accounting quantity is bucket-labelled
        for sa in d.accounting.per_step:
            for q in sa.quantities():
                assert q.bucket.value in {"CONSERVATION", "COMPOSABILITY", "KNOWN_SOURCED", "UNKNOWN"}

    def test_dossier_without_feed_omits_the_ceiling(self):
        d = draft_route_dossier(_anhydride_route())
        assert d.ceiling is None
