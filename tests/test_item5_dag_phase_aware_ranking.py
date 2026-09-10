"""ITEM5-DAG-PHASE-01: the convergent-DAG ranker (``rank_dags``) and its dossier projection (``of_dag``) are phase-aware.

Discharges the R43 documented DEFER (the ROUND-15 ``of_dag`` re-projection fold): ``rank_routes`` could accept
``phases`` soundly because it RETURNS the scored fits ``of_fit`` projects, but ``rank_dags`` returns the DAGs ``of_dag``
RE-PROJECTS under defaults -- so exposing ``phases`` on ``rank_dags`` alone would diverge rank from dossier.  The
fold's stated unlock was "a service API that carries a phase declaration into BOTH ``rank_dags`` and ``of_dag``."
This threads ``phases`` through ``dag_thermo_rollup`` -> ``dag_bench_fit`` -> ``rank_dags`` AND ``of_dag``, behind the
``ranked_dag_dossiers`` seam that passes ONE declaration into both, so rank and dossier cannot diverge.  Pins: the
threading reaches the DAG rollup; the ranking ORDER flips on phase (single-step AND genuinely convergent); ``of_dag``
re-projects the declared phase with no rank-vs-dossier divergence; the default is byte-identical; the status is
phase-invariant (a ranking-only verdict never moves a grade); and the equilibrium axis stays phase-blind (R37 boundary).
"""
from __future__ import annotations

import inspect

from experiments import item5_dag_phase_aware_ranking_probe as probe
from smartchem.experiment.dag import SynthesisDAG, dag_thermo_rollup
from smartchem.experiment.drafter import ConstraintBox, dag_bench_fit, rank_dags
from smartchem.experiment.step import ExperimentStep
from smartchem.service import RankedDAGSummary, ranked_dag_dossiers
from smartchem.smiles import parse_smiles as M


def _step(r, p, t):
    return ExperimentStep.assembling(t, tuple(r), tuple(p))


# --- fixtures (all conserving; verified to behave as the asserts claim) --------------------------------------
def _br2_single():
    br2, br = M("BrBr"), M("[Br]")
    return SynthesisDAG.of(_step([br2], [br, br], br)), {br2: "gas", br: "gas"}


def _i2_single():
    i2, i = M("II"), M("[I]")
    return SynthesisDAG.of(_step([i2], [i, i], i))


def _br2_convergent():
    br2, br, i2, i, ibr = M("BrBr"), M("[Br]"), M("II"), M("[I]"), M("[Br][I]")
    return SynthesisDAG.of(_step([br2], [br, br], br), _step([i2], [i, i], i), _step([br, i], [ibr], ibr))


def _inert_convergent():
    i2, i, cl2, cl, icl = M("II"), M("[I]"), M("ClCl"), M("[Cl]"), M("[Cl][I]")
    return SynthesisDAG.of(_step([i2], [i, i], i), _step([cl2], [cl, cl], cl), _step([i, cl], [icl], icl))


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_phase_declaration_reaches_the_dag_rollup():
    # the SAME single-step Br2 DAG rolled up under two declarations yields a DIFFERENT feasibility -> the thread
    # reached dag_thermo_rollup through dag_bench_fit.
    dag, gas = _br2_single()
    none = dag_bench_fit(dag, ConstraintBox())
    withgas = dag_bench_fit(dag, ConstraintBox(), phases=gas)
    assert none.feasibility_verdict == "UNKNOWN"          # phase-blind Br2 (multiphase) fail-closes
    assert withgas.feasibility_verdict == "UNFAVORABLE"   # declared gas resolves to the sourced dissociation


def test_dag_sign_tier_ranking_order_flips_on_phase_single_step():
    # both single-step DAGs are UNCONSTRAINED under an empty box, so the feasibility SIGN tier decides the order.
    a, gas = _br2_single()
    b = _i2_single()
    order_none = rank_dags([a, b])
    order_gas = rank_dags([a, b], phases=gas)
    assert list(order_none) == [a, b]        # tied on every tier -> stable discovery order
    assert list(order_gas) == [b, a]         # Br2 DAG sinks to the UNFAVORABLE feasibility tier -> flip


def test_dag_sign_tier_ranking_order_flips_on_phase_convergent():
    # two genuinely CONVERGENT 3-step DAGs of the SAME status (UNKNOWN) and equal gap counts, so the feasibility tier
    # (not the status tier) decides -- proving the reorder is real over the multi-node convergent rollup.
    c = _br2_convergent()
    x = _inert_convergent()
    _, gas = _br2_single()
    assert c.is_convergent and x.is_convergent
    assert list(rank_dags([c, x])) == [c, x]              # tied -> discovery order
    assert list(rank_dags([c, x], phases=gas)) == [x, c]  # C's Br2 node rolls up UNFAVORABLE -> C sinks -> flip


def test_of_dag_reprojects_the_declared_phase_no_divergence():
    # THE no-divergence proof: of_dag carries the SAME feasibility verdict the ranker used, but ONLY under the same
    # phases -- so a dossier can never silently disagree with the rank that produced it.
    a, gas = _br2_single()
    box = ConstraintBox()
    s_none = RankedDAGSummary.of_dag(a, box)
    s_gas = RankedDAGSummary.of_dag(a, box, phases=gas)
    assert s_none.feasibility_verdict == "UNKNOWN"
    assert s_gas.feasibility_verdict == "UNFAVORABLE"


def test_ranked_dag_dossiers_seam_moves_rank_and_dossier_together():
    # the seam passes ONE dict into both rank_dags and of_dag: the emitted order is the phase-aware rank AND each
    # dossier carries the phase-aware verdict -- structurally consistent.
    a, gas = _br2_single()
    b = _i2_single()
    box = ConstraintBox()
    dossiers = ranked_dag_dossiers([a, b], box, phases=gas)
    order = ["Br2" if d.route_digest == a.digest else "I2" for d in dossiers]
    assert order == ["I2", "Br2"]                                        # phase-aware rank
    br2_dossier = next(d for d in dossiers if d.route_digest == a.digest)
    assert br2_dossier.feasibility_verdict == "UNFAVORABLE"              # dossier tracks the same phase


def test_default_none_is_byte_identical_to_no_arg():
    a, _ = _br2_single()
    b = _i2_single()
    assert list(rank_dags([a, b])) == list(rank_dags([a, b], phases=None))


def test_foreign_phase_declaration_leaves_a_non_carrier_dag_untouched():
    # a Br2 phase declaration must not perturb a DAG that carries no Br2 (the dict is filtered per step's species).
    b = _i2_single()
    box = ConstraintBox()
    base = dag_bench_fit(b, box)
    with_foreign = dag_bench_fit(b, box, phases={M("BrBr"): "gas"})
    assert base.feasibility_verdict == with_foreign.feasibility_verdict


def test_phase_never_changes_the_section11_status():
    # the load-bearing DAG-THERMO-01 property, now under phase: a phase moves the ranking-only feasibility verdict but
    # NEVER the section-11 status.  This is why the compile path's verified-admission re-projection stays sound.
    a, gas = _br2_single()
    box = ConstraintBox()
    assert dag_bench_fit(a, box).status == dag_bench_fit(a, box, phases=gas).status


def test_equilibrium_axis_stays_phase_blind_in_the_dag_rollup():
    # this brick threads only feasibility (the R37 precedent): even though the rollup carries the phase declaration and
    # the Br2 FEASIBILITY resolves under it (UNFAVORABLE), the multiphase species' equilibrium extent stays UNKNOWN --
    # a sound boundary (never a wrong-phase K), not a wrong answer.
    a, gas = _br2_single()
    box = ConstraintBox()
    fit = dag_bench_fit(a, box, phases=gas)
    assert fit.feasibility_verdict == "UNFAVORABLE"   # feasibility DID resolve under the declared phase
    assert fit.equilibrium_verdict == "UNKNOWN"        # ... but equilibrium stays phase-blind (the boundary)


def test_verified_admission_refuses_a_phase_declared_dossier_fail_closed():
    # evil-morty/dalembert R44 (MEDIUM, fail-closed): _check_verified_admission recomputes of_dag PHASE-BLIND (the
    # replay_payload carries the steps, not the phase), so a phase-DECLARED FITS dossier from the public seam does NOT
    # equal its phase-blind re-projection and is REFUSED on a require_verified_admission round-trip.  This pins the
    # EXACT comparison the check performs (`resummary != d`) on an actually-FITS DAG (the reachable path), and pins
    # that it is FAIL-CLOSED: the status is identical, so verified-admission can only ever REFUSE a genuine dossier,
    # never ADMIT a forged one (a phase never moves a section-11 status).  At parity with the R43 linear side;
    # unreachable from production (_run_recompile passes no phases).  See scope doc Boundary 4.
    from smartchem.conditions import ConditionEnvelope, Interval
    from smartchem.constraints import PhysicalBounds
    from smartchem.contracts import EvidenceStatus
    br2, br = M("BrBr"), M("[Br]")
    env = ConditionEnvelope(temperature=Interval(300, 320, "K"), status=EvidenceStatus.EXPERIMENTAL,
                            provenance="synthetic; no experimental claim")
    dag = SynthesisDAG.of(ExperimentStep.assembling(br, (br2,), (br, br), envelope=env))
    box = ConstraintBox.of_bounds(PhysicalBounds.of(max_temperature_k=500))
    declared = RankedDAGSummary.of_dag(dag, box, phases={br2: "gas", br: "gas"})  # the public seam's phase-aware dossier
    reprojected = RankedDAGSummary.of_dag(dag, box)                               # what _check_verified_admission recomputes
    assert declared.fit_status == "FITS" == reprojected.fit_status                # the check RUNS (only on FITS dossiers)
    assert declared != reprojected                                                # -> `resummary != d` fires -> REFUSE
    assert declared.feasibility_verdict == "UNFAVORABLE"                          # phase-aware
    assert reprojected.feasibility_verdict == "UNKNOWN"                           # phase-blind re-projection
    assert declared.fit_status == reprojected.fit_status                          # FAIL-CLOSED: status identical, never a false-accept


def test_the_phase_threading_signature_is_complete_end_to_end():
    # the fold's unlock: phases reach BOTH the ranker and the dossier projection (and every layer between).
    assert "phases" in inspect.signature(rank_dags).parameters
    assert "phases" in inspect.signature(RankedDAGSummary.of_dag).parameters
    assert "phases" in inspect.signature(dag_bench_fit).parameters
    assert "phases" in inspect.signature(dag_thermo_rollup).parameters
    assert "phases" in inspect.signature(ranked_dag_dossiers).parameters
