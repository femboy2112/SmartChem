"""ROUND-16 item 1 (DAG-THERMO-01): the per-node thermochemical roll-up that makes a DAG ranking as rich as linear.

DAG-RANK-01 (ROUND 15) ranked convergent DAGs on the STRUCTURAL tiers only (status -> composability -> gap/exclusion
counts); its own docstring named "a per-node thermochemical roll-up" as the next-step, because ``DAGBenchFit`` carried
none of the three sourced thermochemical tiers a LINEAR ``_route_score`` rides (selectivity / feasibility / equilibrium)
nor the last-resort kinetics tier.  This closes that gap: ``dag_thermo_rollup`` aggregates the four SOURCED per-reaction
verdicts worst-node-dominated over a DAG's nodes -- the DAG analogue of the four ``verify_*`` folds ``fit_route`` runs,
reusing the IDENTICAL per-step providers, default tables, and worst-precedence -- and ``_dag_score`` now ranks on
EXACTLY ``_route_score``'s tier order.  The load-bearing soundness property, pinned below: the thermo verdicts are
RANKING-ONLY -- they order otherwise-tied DAGs and NEVER change a section-11 ``status`` (a FITS stays a FITS), exactly
as a linear route's ``fit_status`` is independent of its thermo verdicts.
"""
from types import SimpleNamespace

from tests.test_process_service import _convergent_40min_dag

from smartchem.experiment.dag import DAGThermoRollup, SynthesisDAG, _worst_selectivity, dag_thermo_rollup
from smartchem.experiment.drafter import (
    ConstraintBox, DAGBenchFit, RouteFitStatus, _dag_score, dag_bench_fit,
)
from smartchem.experiment.kinetics import kinetics_of_step, worst_regime
from smartchem.experiment.selectivity import SelectivityStatus
from smartchem.process_constraints import ProcessBounds


def _fit(status, comp="COMPOSABLE", *, sel="UNKNOWN", feas="UNKNOWN", eq="UNKNOWN", kin="UNKNOWN",
         gaps=(), exclusions=()):
    """A DAGBenchFit with a stubbed composability verdict + explicit thermo verdicts, to exercise _dag_score's tiers."""
    return DAGBenchFit(status, exclusions, gaps, SimpleNamespace(verdict=comp), sel, feas, eq, kin)


def test_worst_selectivity_mirrors_route_selectivity_precedence_exactly():
    S = SelectivityStatus
    assert _worst_selectivity((S.FAVORED, S.DISFAVORED)) == "DISFAVORED"       # a DISFAVORED step dominates
    assert _worst_selectivity((S.FAVORED, S.UNKNOWN)) == "UNKNOWN"             # then any UNKNOWN outranks a FAVORED
    assert _worst_selectivity((S.FAVORED, S.NOT_APPLICABLE)) == "FAVORED"      # a sourced FAVORED floats over N/A
    assert _worst_selectivity((S.NOT_APPLICABLE,)) == "NOT_APPLICABLE"         # nothing sourced -> N/A


def test_the_rollup_aggregates_real_sourced_thermo_non_vacuously():
    # NON-VACUOUS: the convergent ethyl-chloride DAG (ethanol->ethene dehydration + HCl-from-elements, joining at the
    # hydrochlorination -- NO free-acid dehydrative acylation, so none of it is P1.3-domain-guarded) carries real
    # group-derived thermo, so the worst-node fold yields NON-UNKNOWN verdicts -- a broken fold (e.g. always-UNKNOWN, or
    # reading the wrong field) would fail here, which a vacuous all-UNKNOWN fixture would have hidden.
    r = dag_thermo_rollup(_convergent_40min_dag())
    assert isinstance(r, DAGThermoRollup)
    assert r.feasibility_verdict == "BORDERLINE"                              # a real sourced ΔG verdict, not UNKNOWN
    assert r.equilibrium_verdict == "BALANCED"                                # a real sourced extent, not UNKNOWN
    assert r.feasibility_verdict != "UNKNOWN" or r.equilibrium_verdict != "UNKNOWN"  # the fold reached real data


def test_the_selectivity_and_kinetics_wiring_is_proven_non_vacuously_on_a_real_dag():
    """evil-morty fold (DAG-THERMO-01 LOW-A): the ONLY other real-DAG fixture (_convergent_40min_dag) yields
    sel=UNKNOWN AND kin=UNKNOWN, so the selectivity/kinetics WIRING over dag.steps was proven only to "not raise" --
    a mis-wiring that still resolved to UNKNOWN would have passed (the "vacuous green over an all-UNKNOWN subject"
    class).  This closes it: a single-step DAG of the SOURCED-FAVORED paracetamol acetylation (the amide is the major
    product) makes selectivity_of_step return a NON-UNKNOWN verdict that the rollup must surface, and a differential
    pins the kinetics fold to the actual per-step provider."""
    from tests.test_selectivity import _para_via_anhydride
    dag = SynthesisDAG.of(_para_via_anhydride())
    r = dag_thermo_rollup(dag)
    assert r.selectivity_verdict == "FAVORED"                 # NON-VACUOUS: a real sourced FAVORED reaches the rollup
    # differential: the kinetics fold reads the ACTUAL per-step provider (not a stub), applying the same worst_regime
    # the linear RouteKinetics.verdict does -- so a mis-wired table/field/provider would diverge here.
    assert r.kinetics_verdict == worst_regime(kinetics_of_step(s).regime for s in dag.steps).value


def test_dag_bench_fit_carries_the_four_verdicts_and_they_never_change_status():
    # THE load-bearing soundness property: the thermo verdicts are RANKING-ONLY.  This DAG's feasibility is BORDERLINE
    # (NOT the best, FAVORABLE), yet its section-11 status is decided by composability+physical+process alone -- a
    # non-ideal thermo verdict can never flip the status to EXCLUDED.
    box = ConstraintBox(process=ProcessBounds(max_total_minutes=600.0))
    fit = dag_bench_fit(_convergent_40min_dag(), box)
    assert fit.feasibility_verdict == "BORDERLINE"
    assert fit.status is not RouteFitStatus.EXCLUDED           # a non-FAVORABLE thermo verdict did NOT exclude it


def test_dag_score_breaks_a_status_and_composability_tie_on_feasibility():
    fav = _fit(RouteFitStatus.FITS, feas="FAVORABLE")
    unfav = _fit(RouteFitStatus.FITS, feas="UNFAVORABLE")
    assert _dag_score(fav) < _dag_score(unfav)                 # a thermodynamically favorable DAG floats
    assert fav.status is unfav.status is RouteFitStatus.FITS    # ... and status is identical: a tiebreaker, not a grade


def test_dag_score_tier_order_selectivity_outranks_feasibility_outranks_equilibrium():
    # The _route_score tier order, mirrored: selectivity is a HIGHER tier than feasibility, which is higher than
    # equilibrium.  So a good-selectivity/bad-feasibility DAG must outrank a bad-selectivity/good-feasibility one.
    sel_wins = _fit(RouteFitStatus.FITS, sel="FAVORED", feas="UNFAVORABLE")
    feas_wins = _fit(RouteFitStatus.FITS, sel="DISFAVORED", feas="FAVORABLE")
    assert _dag_score(sel_wins) < _dag_score(feas_wins)        # selectivity dominates feasibility (the higher tier)
    # and feasibility dominates equilibrium in turn:
    feas_hi = _fit(RouteFitStatus.FITS, feas="FAVORABLE", eq="NEGLIGIBLE")
    eq_hi = _fit(RouteFitStatus.FITS, feas="UNFAVORABLE", eq="ESSENTIALLY_COMPLETE")
    assert _dag_score(feas_hi) < _dag_score(eq_hi)


def test_kinetics_is_dead_last_and_never_outranks_a_gap_count():
    # kinetics rides AFTER the gap/exclusion counts (exactly as _route_score places it), so a FAST-kinetics DAG with
    # MORE gaps still sinks below a FROZEN one with fewer gaps -- kinetics only breaks a tie on everything above it.
    fast_manygaps = _fit(RouteFitStatus.UNKNOWN, comp="UNKNOWN", kin="FAST", gaps=("g1", "g2"))
    frozen_fewgaps = _fit(RouteFitStatus.UNKNOWN, comp="UNKNOWN", kin="FROZEN", gaps=("g1",))
    assert _dag_score(frozen_fewgaps) < _dag_score(fast_manygaps)   # fewer gaps beats faster kinetics


def test_the_score_reorders_two_structurally_tied_fits_on_feasibility():
    # Two DAGs identical on status/composability/gaps/exclusions, differing ONLY on feasibility: the _dag_score sort
    # (which is EXACTLY what rank_dags applies) must float the FAVORABLE one first.  The wired real-DAG rank_dags path
    # is covered by tests/test_dag_rank.py's service test; the real-thermo wiring by the dossier test below.
    fav = _fit(RouteFitStatus.FITS, feas="FAVORABLE")
    unfav = _fit(RouteFitStatus.FITS, feas="UNFAVORABLE")
    assert sorted([unfav, fav], key=_dag_score) == [fav, unfav]


def test_the_verdicts_reach_the_dossier_and_survive_the_json_roundtrip():
    from smartchem.service import (
        RankedDAGSummary, ranked_dag_summary_from_payload, ranked_dag_summary_to_payload,
    )
    box = ConstraintBox(process=ProcessBounds(max_total_minutes=600.0))
    summ = RankedDAGSummary.of_dag(_convergent_40min_dag(), box)
    assert summ.feasibility_verdict == "BORDERLINE"            # the real sourced verdict reaches the human dossier
    assert summ.equilibrium_verdict == "BALANCED"
    assert summ.composability_verdict                          # non-empty (parity with the linear summary)
    rt = ranked_dag_summary_from_payload(ranked_dag_summary_to_payload(summ))
    assert rt.digest == summ.digest                            # the verdicts are part of identity: exact round-trip
    assert rt.feasibility_verdict == "BORDERLINE" and rt.kinetics_verdict == summ.kinetics_verdict


def test_serial_holds_reach_the_dossier_machine_readable_and_are_digest_stable():
    # item 2b: DAG-HOLD-01's serial hold, previously a human note only, is now a machine-readable field.
    from dataclasses import replace

    from smartchem.service import (
        RankedDAGSummary, ranked_dag_summary_from_payload, ranked_dag_summary_to_payload,
    )
    box = ConstraintBox(process=ProcessBounds(max_total_minutes=600.0))
    summ = RankedDAGSummary.of_dag(_convergent_40min_dag(), box)
    # NON-vacuous: the 40-min convergent DAG can hold EITHER independent branch's intermediate through the other
    # (Move 6: the disclosure is the POSSIBLY-BETWEEN, schedule-relative hold, order-independent -- both producer->
    # join edges disclose 40 min, where the pre-Move-6 code reported only one under an arbitrary topological order).
    assert summ.serial_holds == ((0, 2, 40.0), (1, 2, 40.0))
    # survives the JSON round-trip as (int, int, float) triples.
    rt = ranked_dag_summary_from_payload(ranked_dag_summary_to_payload(summ))
    assert rt.serial_holds == summ.serial_holds
    # DISCLOSURE, not identity: stripping the holds leaves the digest byte-identical (compare=False), so no
    # existing DAG digest moved when the field was added.
    assert replace(summ, serial_holds=()).digest == summ.digest
    # fail-closed: a hold over a NON-edge is refused (never a fabricated (producer, consumer) pair).
    import pytest
    with pytest.raises(ValueError, match="not one of the DAG's carried edges"):
        replace(summ, serial_holds=((0, 1, 5.0),))
