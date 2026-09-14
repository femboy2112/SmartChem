"""POOR-MAN-DISPOSITION-ACTIVATION-01: R59's REAL_BUT_HARD tier is now REACHABLE on a bench-constrained frontier.

The committed probe (:mod:`experiments.poor_man_disposition_activation_probe`) is the frozen evidence that lifting the
FITS-only frontier admission gate to also admit RE-DERIVED-process-EXCLUDED routes makes R59's REAL_BUT_HARD tier
populated (a genuine reaction the kitchen bench cannot run -- e.g. no reflux condenser -- now appears on the
affordability frontier, demoted below runnable CLEAN routes) SOUNDLY (the process exclusion is re-derived and
re-checked on load, PROCESS-ADMIT-01) and HONESTLY (the REAL_BUT_HARD-vs-NOT_A_REACTION ranking INVERSION stays
data-dark: the two tiers cannot co-occur on a frontier, so it remains reachable only via the catalyst/escape-#7 source).

These are the fast regression pins over the SAME live behaviour, independent of the probe.  If the "activation" pin
stops firing, the gate lift broke (re-state the win).  If the "authenticated" pin stops firing, an unauthenticated
route slipped onto the process-constrained frontier (STOP -- the deserialization trust boundary reopened).  If the
"byte-stable" pin stops firing, the no-process path rippled.  If the "inversion still dark" pin stops firing, the two
tiers now co-occur -- a genuine ranking-inversion consumer appeared; re-state this round.
"""
from __future__ import annotations

from smartchem.service import build_recompile_request, run_compilation
from smartchem.process_constraints import ProcessBounds, evaluate_process_requirements, ProcessFitStatus
from smartchem.experiment.affordability import Disposition
import experiments.poor_man_disposition_activation_probe as probe

_KITCHEN = ("stovetop", "pot", "glass jar", "thermometer", "spoon", "funnel")  # no reflux condenser / heating mantle
_TARGET = "isopentyl acetate"
_STOCK = ("isopentyl alcohol", "acetic acid")


def _bench_resp():
    return run_compilation(build_recompile_request(
        _TARGET, max_depth=3, stock_materials=_STOCK, process=ProcessBounds(available_equipment=_KITCHEN)))


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_real_but_hard_is_reachable_on_a_bench_constrained_frontier():
    resp = _bench_resp()
    fr = resp.affordability_frontier
    assert fr, "the bench-constrained frontier is empty -- the gate lift did not surface the real-but-hard route"
    rbh = [e for e in fr if e.cost_vector.disposition is Disposition.REAL_BUT_HARD]
    assert rbh, "no REAL_BUT_HARD route on the frontier -- the tier is still vacuous"
    # the hardness names the missing lab glassware: the authentic poor-man wall.
    assert any("equipment is unavailable" in b for b in rbh[0].cost_vector.hard_blockers)


def test_the_fits_only_gate_was_lifted():
    # the route is on the frontier YET not bench-admissible (admissible_route_digests is FITS-only) -> the old
    # FITS-only gate, which forbade any non-FITS route on the frontier, was lifted.
    resp = _bench_resp()
    assert any(e.cost_vector.disposition is Disposition.REAL_BUT_HARD for e in resp.affordability_frontier)
    assert resp.admissible_route_digests == ()  # no route FITS the kitchen bench -- yet the frontier is non-empty


def test_real_but_hard_hardness_is_authenticated_not_free_text():
    # the REAL_BUT_HARD entry's hard_blockers are EXACTLY the RE-DERIVED process exclusions (the PROCESS-ADMIT-01
    # authority), not the untrusted declared free-text -- so the hardness is trust-boundary-safe on load.
    resp = _bench_resp()
    bounds = ProcessBounds(available_equipment=_KITCHEN)
    by_digest = {d.route_digest: d for d in resp.ranked_route_dossiers}
    checked = 0
    for e in resp.affordability_frontier:
        d = by_digest[e.route_digest]
        proc = evaluate_process_requirements(d.process_requirements, bounds)
        # admission soundness: every frontier route is FITS or re-derived-process-EXCLUDED (never process-UNKNOWN).
        assert d.fit_status == "FITS" or proc.status is ProcessFitStatus.EXCLUDED
        if e.cost_vector.disposition is Disposition.REAL_BUT_HARD:
            assert tuple(e.cost_vector.hard_blockers) == tuple(proc.exclusions)
            checked += 1
    assert checked >= 1


def test_no_process_bounds_path_is_unchanged():
    # the else branch (no process box) is untouched: with the precursors on hand the esterification is CLEAN (runnable).
    resp = run_compilation(build_recompile_request(_TARGET, max_depth=3, stock_materials=_STOCK))
    tiers = {e.cost_vector.disposition.name for e in resp.affordability_frontier}
    assert Disposition.REAL_BUT_HARD.name not in tiers
    assert tiers == {"CLEAN"}


def test_real_but_hard_is_never_conflated_into_bench_readiness():
    # a REAL_BUT_HARD route is SHOWN (ranked, demoted) but NEVER claimed bench-admissible -- admissible_route_digests
    # keeps its FITS-only meaning, so a consumer never mistakes "real but unrunnable" for "runnable".
    resp = _bench_resp()
    rbh = {e.route_digest for e in resp.affordability_frontier
           if e.cost_vector.disposition is Disposition.REAL_BUT_HARD}
    assert rbh and not (rbh & set(resp.admissible_route_digests))


def test_the_ranking_inversion_is_honestly_still_data_dark():
    # the two tiers cannot co-occur on ONE frontier: under bounds fictions are process-UNKNOWN -> excluded; without
    # bounds there is no REAL_BUT_HARD source.  So REAL_BUT_HARD strictly-dominating a co-occurring NOT_A_REACTION
    # (R59's distinctive inversion) remains reachable ONLY via the catalyst source -- honestly deferred.
    bounded = {e.cost_vector.disposition.name for e in _bench_resp().affordability_frontier}
    unbounded = {e.cost_vector.disposition.name
                 for e in run_compilation(build_recompile_request(_TARGET, max_depth=3)).affordability_frontier}
    assert Disposition.NOT_A_REACTION.name not in bounded          # fictions excluded under bounds
    assert Disposition.REAL_BUT_HARD.name not in unbounded         # no real-but-hard source without bounds
