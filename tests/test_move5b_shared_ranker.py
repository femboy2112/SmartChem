"""MOVE5-SHARED-RANKER-01: Move 5(b) cross-domain shared ranker VERIFIED DEFER + the intra-chemistry consolidation.

Pins (a) the two code-run counterexamples that prove the cross-domain unification is lossy-or-non-neutral -- so the
DEFER is a re-checkable differential fact, not prose -- and (b) that the sound intra-chemistry consolidation shipped
this round is LIVE: ``_route_score`` and ``_dag_score`` route through the ONE shared ``_score_tuple`` core (they
cannot diverge by a forgotten hand-edit), and the shared Pareto-wiring helper is in place.  Byte-stability of the
consolidation on REAL routes/DAGs is carried by the full suite (test_drafter / test_dag_rank / test_m2b_pareto_ranking
/ test_service / the paracetamol north-star harness), which this change leaves green.
"""
from __future__ import annotations

from experiments import move5b_shared_ranker_probe as probe
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment import drafter
from smartchem.experiment.composability import verify_composability
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles


def test_probe_validates_and_frozen_hash_stable():
    probe.validate()
    assert probe.content_hash() == probe.FROZEN_HASH


def test_ce1_front_index_is_set_relative():
    # CE-1: a route's Pareto layer depends on its SIBLINGS -- removing the dominator P1 moves P2 from layer 1 to
    # layer 0.  A per-candidate key (circuit's shape) is set-invariant and cannot reproduce this.
    ce1 = probe.ce1_front_index_is_set_relative()
    assert ce1["full"] == [0, 1, 2]
    assert ce1["without_p1"] == [0, 1]
    assert ce1["p2_layer_full"] == 1
    assert ce1["p2_layer_without_p1"] == 0
    assert ce1["set_relative"] is True


def test_ce2_opposite_failclosed_polarity():
    # CE-2: the same abstract "unknown ranking quantity" event -> chemistry floats it to the TOP layer,
    # circuits EJECT it.  One primitive with one unknown-policy is unsound for one of the two domains.
    ce2 = probe.ce2_opposite_failclosed_polarity()
    assert ce2["chem_fronts"] == [0, 1, 0]  # unknown at layer 0, above the complete dominated route at layer 1
    assert ce2["unknown_layer"] == 0
    assert ce2["dominated_layer"] == 1
    assert ce2["circuit_in_band"] is True
    assert ce2["circuit_out_of_band"] is False  # out-of-band candidate ejected, never floated to the top
    assert ce2["opposite_polarity"] is True


def test_intra_chemistry_consolidation_is_live():
    # both scorers are thin extractors over the ONE shared _score_tuple: identical verdicts -> identical key,
    # and each equals a direct _score_tuple call.  This is what makes the DAG-RANK-01 no-divergence promise
    # structural rather than a hand-kept comment.
    rows = probe.consolidation_live()
    assert rows
    assert all(row["equal"] for row in rows)
    assert all(row["matches_core"] for row in rows)


def test_shared_ranker_helpers_exist_and_are_used():
    # the consolidation's two shared primitives are present and are the ones the four public/private ranking
    # functions delegate to (a smoke guard against a partial revert that re-duplicates one scorer).
    assert callable(drafter._score_tuple)
    assert callable(drafter._physics_ranked_order)
    # _route_score / _dag_score keep their public signatures (front_index, net, and the DISCONN-SEL-01 derived_rank
    # default) -- byte-compatible callers; both scorers gained the same neutral-default coordinate together.
    assert drafter._route_score.__defaults__ == (0, None, 1)
    assert drafter._dag_score.__defaults__ == (0, None, 1)


def _env(tlo, thi, prov):
    return ConditionEnvelope(
        temperature=Interval(tlo, thi, "K"), medium="",
        status=EvidenceStatus.EXPERIMENTAL, provenance=prov,
    )


def test_route_composability_verdict_never_no_transitions_invariant():
    # R41-review fold (evil-morty + dalembert + mr-president, all four bearings): the consolidation's byte-identity
    # for ROUTES rests on the shared comp_rank's DAG-only "NO_TRANSITIONS" key never being hit by a route -- an
    # invariant previously held only by composability.py's incidental verdict domain, not by the ranker's design.
    # This tripwire enforces it at the layer it lives (the fail-closed-at-every-layer lesson): it exercises the REAL
    # route Composability.verdict across ALL FOUR of its reachable branches and asserts NONE is "NO_TRANSITIONS", so
    # a future edit that let a route emit it (mirroring dag.py's empty-guard) trips a RED test instead of silently
    # re-ranking such a route from tier 4 to tier 1.
    acoh, water, ketene = parse_smiles("CC(=O)O"), parse_smiles("O"), parse_smiles("C=C=O")
    amp, para, anh = parse_smiles("Nc1ccc(O)cc1"), parse_smiles("CC(=O)Nc1ccc(O)cc1"), parse_smiles("CC(=O)OC(=O)C")
    etoh, ea = parse_smiles("CCO"), parse_smiles("CCOC(=O)C")
    amp_acetate = parse_smiles("CC(=O)Oc1ccc(N)cc1")

    single = ExperimentRoute.of(  # 0 transitions -> SINGLE_STEP branch
        ExperimentStep.assembling(para, (amp, anh), (para, acoh), envelope=_env(295, 320, "one-step")))
    composable = ExperimentRoute.of(  # all-cleared -> COMPOSABLE branch
        ExperimentStep.assembling(amp, (amp_acetate, water), (amp, acoh), envelope=_env(330, 360, "hydrolyse")),
        ExperimentStep.assembling(para, (amp, anh), (para, acoh), envelope=_env(295, 320, "below onset")))
    unknown = ExperimentRoute.of(  # no sourced stability -> UNKNOWN branch
        ExperimentStep.assembling(ea, (acoh, etoh), (ea, water), envelope=_env(340, 350, "esterify")),
        ExperimentStep.assembling(para, (ea, amp), (para, etoh), envelope=_env(300, 320, "toy consume")))
    degenerate = ExperimentRoute.of(  # non-isolable intermediate -> DEGENERATE branch
        ExperimentStep.assembling(ketene, (acoh,), (ketene, water), envelope=_env(973, 1023, "pyrolysis to ketene")),
        ExperimentStep.assembling(para, (ketene, amp), (para,), envelope=_env(273, 298, "ketene acetylation")))

    verdicts = {verify_composability(r).verdict for r in (single, composable, unknown, degenerate)}
    # non-vacuity: all four branches genuinely exercised (a route CANNOT emit NO_TRANSITIONS -- that is DAG-only)
    assert verdicts == {"SINGLE_STEP", "COMPOSABLE", "UNKNOWN", "DEGENERATE"}
    assert "NO_TRANSITIONS" not in verdicts
    # and the shared score core ranks every real route verdict on a DEFINED comp tier (0..3), never the
    # .get(..., 4) fallback -- so the merged dict's NO_TRANSITIONS key is provably inert on the route path.
    for v in verdicts:
        tier = drafter._score_tuple(drafter.RouteFitStatus.FITS, v, "UNKNOWN", "UNKNOWN",
                                    "UNKNOWN", "UNKNOWN", 0, 0)[1]
        assert tier in (0, 1, 2, 3)  # COMPOSABLE=0, SINGLE_STEP=1, UNKNOWN=2, DEGENERATE=3 -- never the fallback 4


def test_score_tuple_net_magnitude_gating_is_favorable_only():
    # the M2b reward-for-ignorance fix lives in the shared core now: the net-ΔG magnitude slot is the real net
    # ONLY in the FAVORABLE class, and a constant 0.0 in every other class (so an unsourced route can't float
    # above a fully-sourced endergonic one).
    from smartchem.experiment.drafter import RouteFitStatus, _score_tuple
    fav = _score_tuple(RouteFitStatus.FITS, "COMPOSABLE", "FAVORED", "FAVORABLE", "FAVORABLE", "FAST", 0, 0, 0, -9.0)
    unf = _score_tuple(RouteFitStatus.FITS, "COMPOSABLE", "FAVORED", "UNFAVORABLE", "FAVORABLE", "FAST", 0, 0, 0, -9.0)
    assert fav[5] == -9.0  # FAVORABLE keeps the magnitude
    assert unf[5] == 0.0  # every other class zeroes it
