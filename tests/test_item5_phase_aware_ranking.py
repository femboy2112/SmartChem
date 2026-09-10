"""ITEM5-PHASE-RANK-01: the drafter's public linear ranking API (``rank_routes``) is phase-aware.

Pins the item-5 forcing consumer the R37 brick deferred ("no dual-phase ranked route exists -- the zero-call-sites
trap; unparks when one does"): a route whose ranking ORDER now flips on a declared phase, threaded
``rank_routes`` -> ``fit_routes`` -> ``fit_route`` -> ``verify_feasibility``.  Also pins the boundaries: the default
is byte-identical (``phases=None``), the equilibrium axis stays phase-blind (a follow-up, not this brick), and the
DAG ranker (``rank_dags``) deliberately does NOT expose ``phases`` (the ROUND-15 of_dag re-projection fold).
"""
from __future__ import annotations

import inspect

from experiments import item5_phase_aware_ranking_probe as probe
from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef
from smartchem.experiment.drafter import ConstraintBox, fit_route, rank_dags, rank_routes
from smartchem.experiment.feasibility import _formula_str
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles as M


def _step(r, p, t):
    return ExperimentStep.assembling(t, tuple(r), tuple(p))


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_phase_declaration_reaches_the_ranker():
    # the SAME route scored under two phase declarations yields a DIFFERENT feasibility -> the thread reached rank_routes
    br2, br = M("BrBr"), M("[Br]")
    route = ExperimentRoute.of(_step([br2], [br, br], br))
    f_none = fit_route(route, ConstraintBox())
    f_gas = fit_route(route, ConstraintBox(), phases={br2: "gas", br: "gas"})
    assert f_none.feasibility.verdict == "UNKNOWN"          # phase-blind Br2 (multiphase) fail-closes
    assert f_none.feasibility.net_delta_g_kj is None
    assert f_gas.feasibility.verdict == "UNFAVORABLE"       # declared gas resolves to the sourced dissociation
    assert round(f_gas.feasibility.net_delta_g_kj, 2) == 161.65


def test_sign_tier_ranking_order_flips_on_phase():
    br2, br, i2, i = M("BrBr"), M("[Br]"), M("II"), M("[I]")
    ra = ExperimentRoute.of(_step([br2], [br, br], br))     # phase-sensitive
    rb = ExperimentRoute.of(_step([i2], [i, i], i))         # phase-inert (unsourced -> UNKNOWN)
    order_none = [f.route for f in rank_routes([ra, rb])]
    order_gas = [f.route for f in rank_routes([ra, rb], phases={br2: "gas", br: "gas"})]
    assert order_none == [ra, rb]      # tied on every tier -> stable discovery order
    assert order_gas == [rb, ra]       # Br2 route sinks to the UNFAVORABLE feasibility tier -> flip


def test_default_none_is_byte_identical_to_no_arg():
    br2, br, i2, i = M("BrBr"), M("[Br]"), M("II"), M("[I]")
    ra = ExperimentRoute.of(_step([br2], [br, br], br))
    rb = ExperimentRoute.of(_step([i2], [i, i], i))
    noarg = [f.route for f in rank_routes([ra, rb])]
    explicit_none = [f.route for f in rank_routes([ra, rb], phases=None)]
    assert noarg == explicit_none


def test_foreign_phase_declaration_leaves_a_non_carrier_route_untouched():
    # a Br2 phase declaration must not perturb a route that carries no Br2 (the dict is filtered per route's species)
    i2, i = M("II"), M("[I]")
    rb = ExperimentRoute.of(_step([i2], [i, i], i))
    base = fit_route(rb, ConstraintBox())
    with_foreign = fit_route(rb, ConstraintBox(), phases={M("BrBr"): "gas"})
    assert base.feasibility.verdict == with_foreign.feasibility.verdict


def test_magnitude_tier_is_phase_fed_in_the_favorable_class():
    # Br2 + H2 -> 2 HBr is FAVORABLE in BOTH phases but the additive net ΔG (the M2b magnitude tier) is phase-dependent
    br2, h2, hbr = M("BrBr"), M("[H][H]"), M("Br")
    tbl = DEFAULT_THERMO.with_records(
        ThermoRef(_formula_str(hbr), "hydrogen bromide", -36.29, 198.70, "gas", "test HBr(g)"),
    )
    route = ExperimentRoute.of(_step([br2, h2], [hbr, hbr], hbr))
    gas = fit_route(route, ConstraintBox(), thermo=tbl, phases={br2: "gas"})
    liq = fit_route(route, ConstraintBox(), thermo=tbl, phases={br2: "liquid"})
    assert gas.feasibility.verdict == "FAVORABLE" == liq.feasibility.verdict
    assert round(gas.feasibility.net_delta_g_kj, 2) == -109.83
    assert round(liq.feasibility.net_delta_g_kj, 2) == -106.72
    assert gas.feasibility.net_delta_g_kj != liq.feasibility.net_delta_g_kj


def test_fail_closed_guarantee_holds_at_the_specific_phase_layer():
    # evil-morty R43: for a MULTIPHASE species a declared phase the table does not hold (untabulated "solid" or a
    # mis-cased "Gas") must fail-closed to UNKNOWN, not fall through to a phase-blind Benson estimate that answers a
    # DIFFERENT phase than asked.  Ethanol tabulated gas+liquid AND Benson-coverable is the exact leak bed.
    etoh, c2h4, h2o = M("CCO"), M("C=C"), M("O")
    tbl = DEFAULT_THERMO.with_records(
        ThermoRef(_formula_str(etoh), "ethanol", -234.8, 281.6, "gas", "test etoh(g)"),
        ThermoRef(_formula_str(etoh), "ethanol", -277.6, 160.7, "liquid", "test etoh(l)"),
    )
    route = ExperimentRoute.of(_step([etoh], [c2h4, h2o], c2h4))   # ethanol -> ethylene + water

    def verdict(ph):
        phases = None if ph is None else {etoh: ph}
        return fit_route(route, ConstraintBox(), thermo=tbl, phases=phases).feasibility.verdict

    assert verdict("gas") != "UNKNOWN"          # tabulated -> resolves
    assert verdict("liquid") != "UNKNOWN"       # tabulated -> resolves
    assert verdict(None) == "UNKNOWN"           # phase-blind on a multiphase species -> UNKNOWN (R36)
    assert verdict("solid") == "UNKNOWN"        # untabulated specific phase -> UNKNOWN (R43 fix, not fabricated)
    assert verdict("aqueous") == "UNKNOWN"      # untabulated specific phase -> UNKNOWN
    assert verdict("Gas") == "UNKNOWN"          # a mis-cased real phase -> UNKNOWN (exact match; no silent downgrade)


def test_single_phase_species_still_derives_for_an_untabulated_phase():
    # the R43 fail-closed fix is multiphase-only: a SINGLE-phase species is not phase-ambiguous, so an untabulated
    # phase still derives (the legitimate condensed-derive path is untouched -- is_multiphase gates the guard).
    from smartchem.experiment.feasibility import resolve_thermo
    prop = M("CCC")   # propane: single-phase / Benson-coverable
    assert DEFAULT_THERMO.is_multiphase(_formula_str(prop)) is False
    assert resolve_thermo(prop, phase="liquid") is not None   # still derives (guard is multiphase-only)


def test_phase_lever_reverses_sign_with_temperature():
    # dalembert R43: the phase preference on ΔG is non-monotone in T -- ΔG_gas - ΔG_liq = -30.91 + 0.093258*T,
    # zero at 331.45 K.  So any DIRECTIONAL "gas floats / liquid sinks" claim is a 298 K statement, not universal.
    from smartchem.experiment.feasibility import verify_feasibility
    br2, h2, hbr = M("BrBr"), M("[H][H]"), M("Br")
    tbl = DEFAULT_THERMO.with_records(ThermoRef(_formula_str(hbr), "hydrogen bromide", -36.29, 198.70, "gas", "t"))
    route = ExperimentRoute.of(_step([br2, h2], [hbr, hbr], hbr))

    def lever(temp):
        gas = verify_feasibility(route, thermo=tbl, phases={br2: "gas"}, temperature_k=temp).net_delta_g_kj
        liq = verify_feasibility(route, thermo=tbl, phases={br2: "liquid"}, temperature_k=temp).net_delta_g_kj
        return gas - liq

    assert lever(298.15) < 0     # gas the more favorable phase below the 331.45 K crossover
    assert lever(350.0) > 0      # liquid the more favorable phase above it


def test_rank_dags_does_not_expose_phases_the_of_dag_fold():
    # the ROUND-15 fold: rank_routes returns the fits (of_fit projects THOSE, no divergence), rank_dags returns DAGs
    # that of_dag re-projects under defaults -- so phases on rank_dags alone would diverge rank from dossier.
    assert "phases" in inspect.signature(rank_routes).parameters
    assert "phases" not in inspect.signature(rank_dags).parameters


def test_equilibrium_axis_stays_phase_blind_the_documented_boundary():
    # this brick threads only feasibility (the R37 precedent); a multiphase species fail-closes its equilibrium to
    # UNKNOWN even with phases declared -- a sound boundary, not a wrong answer.
    from smartchem.experiment.equilibrium import verify_equilibrium
    assert "phases" not in inspect.signature(verify_equilibrium).parameters
    br2, br = M("BrBr"), M("[Br]")
    route = ExperimentRoute.of(_step([br2], [br, br], br))
    eq = verify_equilibrium(route)
    assert eq.verdict == "UNKNOWN"     # Br2 multiphase -> equilibrium fail-closed regardless of any phase intent
