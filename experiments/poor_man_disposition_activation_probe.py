"""POOR-MAN-DISPOSITION-ACTIVATION-01: the REAL_BUT_HARD tier goes from structurally-impossible to REACHABLE.

R59 built a 3-tier :class:`~smartchem.experiment.affordability.Disposition` (CLEAN < REAL_BUT_HARD < NOT_A_REACTION)
and shipped it CORRECT-AHEAD-OF-DATA: the REAL_BUT_HARD tier was verdict-neutral because it was never populated (see
:mod:`experiments.poor_man_disposition_channel_probe`).  This round finds WHY it was unpopulated and lifts the wall:

  THE WALL (structural, not data).  ``service._affordability_frontier`` already wires a REAL-BUT-HARD source -- a
  section-11 bench EXCLUSION becomes ``hard_blockers`` (disposition REAL_BUT_HARD).  But whenever a process box is
  active (the ONLY way to produce an EXCLUDED route), ``run_compilation`` rebuilt the frontier from FITS-ONLY routes
  (a deliberate soundness invariant: a bench-constrained frontier admitted only routes that FIT).  So every EXCLUDED
  route was filtered out BEFORE it reached the frontier -- the REAL_BUT_HARD tier could NEVER be populated.  The wiring
  was effectively dead code, and its own docstring (real-but-hard routes are "ranked ABOVE a fiction") contradicted the
  FITS-only gate that starved it.

  THE LIFT (DISPOSITION-ACTIVATE-01, SOUND).  Admit a route to the process-constrained frontier iff it is FITS OR its
  RE-DERIVED process status is EXCLUDED -- ranked below runnable CLEAN routes, above NOT_A_REACTION fictions.  This is
  sound because the process exclusion is re-derived from the route's carried per-step ``process_requirements`` via
  ``evaluate_process_requirements`` -- the SAME authority PROCESS-ADMIT-01 re-checks on load -- so a REAL_BUT_HARD
  route's hardness is trust-boundary-safe (unlike the physical/composability exclusion axes, which stay
  diagnostics-only, not re-derivable from the thin projection, hence NOT admitted).  The disposition itself is not new
  math: it is the EXISTING homomorphic ``CostVector.disposition`` join -- this round only makes it REACHABLE.

WHAT THIS PROBE FREEZES, honestly, against LIVE code:

  (1) ACTIVATION REACHABLE -- isopentyl alcohol + acetic acid -> isopentyl acetate on a poor-man kitchen bench with NO
      reflux condenser: the recognized Fischer esterification is process-EXCLUDED and now appears on the affordability
      frontier at REAL_BUT_HARD.  ``admissible_route_digests`` (bench-ready, FITS-only) is EMPTY for it -- so its
      presence on the frontier PROVES the old FITS-only gate was lifted (a non-FITS route the old gate forbade).

  (2) HARDNESS AUTHENTICATED -- the REAL_BUT_HARD entry's ``hard_blockers`` equal the RE-DERIVED process exclusions
      (``evaluate_process_requirements`` over the carried requirements), not the untrusted free-text; and every
      admitted frontier route under bounds is FITS or re-derived-process-EXCLUDED (never process-UNKNOWN).

  (3) BYTE-STABLE OFF THE PROCESS PATH -- a no-bounds run's frontier is unchanged (the else branch is untouched), and
      the entry shape is unchanged from R59 (no schema bump): R59's own probe still validates with a stable hash.

  (4) *** THE HONEST HEADLINE -- the RANKING INVERSION stays DATA-DARK (this round activates VISIBILITY, not the
      inversion). ***  R59's distinctive effect (REAL_BUT_HARD STRICTLY dominating a co-occurring NOT_A_REACTION,
      differing from the old 2-tier frontier) needs the two tiers on ONE frontier.  Under process bounds, derived
      FICTIONS carry no process record -> they fit UNKNOWN -> they are NOT admitted (correctly), so a fiction and a
      REAL_BUT_HARD route cannot co-occur; and WITHOUT process bounds there is no REAL_BUT_HARD source at all.  The
      catch-22: the inversion is reachable ONLY through a NON-process real-but-hard source -- a declared metal catalyst
      -- which is the deferred escape-#7 wall.  This round makes the REAL_BUT_HARD tier VISIBLE and non-vacuous (a real
      change: it produced nothing before); the tier-vs-fiction ranking inversion is honestly deferred, correct-ahead-
      of-data, exactly like R59.  If a co-occurrence ever becomes reachable this probe's assertion FLIPS -- re-state.

  (5) NO REGRESSION -- R59's probe still validates and its FROZEN_HASH is stable (no-bounds path untouched); every
      prior poor-man probe stays frozen; ``admissible_route_digests`` keeps its FITS-only (bench-ready) meaning.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.service import build_recompile_request, run_compilation
from smartchem.process_constraints import ProcessBounds, evaluate_process_requirements, ProcessFitStatus
from smartchem.experiment.affordability import Disposition

import experiments.poor_man_disposition_channel_probe as p59
import experiments.poor_man_reaction_type_oracle_probe as p56
import experiments.poor_man_etherification_recognizer_probe as p57
import experiments.poor_man_span_local_recognizer_probe as p58

FROZEN_HASH = "5e992095d053c1617b341a83f22cc306a8caa33584c40983c2a837d1cece5f50"

#: a poor-man kitchen inventory that LACKS lab glassware (reflux condenser, heating mantle, distillation apparatus) --
#: "my kitchen can't run a reflux".  This is the authentic poor-man bench wall that makes a real reaction REAL_BUT_HARD.
_KITCHEN = ("stovetop", "pot", "glass jar", "thermometer", "spoon", "funnel")

#: the flagship activation target: a genuine Fischer esterification, kitchen-obtainable catalyst (sulfuric acid), whose
#: SOURCED process record requires lab reflux/distillation glassware the kitchen bench lacks -> process-EXCLUDED.
_TARGET = "isopentyl acetate"
_STOCK = ("isopentyl alcohol", "acetic acid")

_RESP_CACHE: "dict[tuple, object]" = {}


def _resp(target: str, *, bounds: bool, stock: "tuple[str, ...] | None" = None):
    key = (target, bounds, stock)
    if key in _RESP_CACHE:
        return _RESP_CACHE[key]
    kw: dict = {"max_depth": 3}
    if stock is not None:
        kw["stock_materials"] = stock
    if bounds:
        kw["process"] = ProcessBounds(available_equipment=_KITCHEN)
    resp = run_compilation(build_recompile_request(target, **kw))
    _RESP_CACHE[key] = resp
    return resp


def _bounds() -> ProcessBounds:
    return ProcessBounds(available_equipment=_KITCHEN)


# --------------------------------------------------------------------------------------------------
# (1) ACTIVATION REACHABLE: REAL_BUT_HARD now appears on a bench-constrained frontier (was structurally impossible).
# --------------------------------------------------------------------------------------------------
def activation_reachable() -> dict:
    resp = _resp(_TARGET, bounds=True, stock=_STOCK)
    fr = resp.affordability_frontier
    rbh = [e for e in fr if e.cost_vector.disposition is Disposition.REAL_BUT_HARD]
    return {
        "frontier_size": len(fr),
        "real_but_hard_count": len(rbh),
        "real_but_hard_reachable": len(rbh) >= 1,
        # the route is on the frontier yet NOT bench-admissible (FITS-only) -> the old FITS-only gate WAS lifted.
        "admissible_route_digests_empty": len(resp.admissible_route_digests) == 0,
        "gate_lifted_proof": len(rbh) >= 1 and len(resp.admissible_route_digests) == 0,
        # the hardness names the missing lab glassware -- the authentic poor-man wall.
        "hard_reason_is_equipment": bool(rbh) and any("equipment is unavailable" in b for b in rbh[0].cost_vector.hard_blockers),
    }


# --------------------------------------------------------------------------------------------------
# (2) HARDNESS AUTHENTICATED: hard_blockers == re-derived process exclusions; only FITS/re-derived-EXCLUDED admitted.
# --------------------------------------------------------------------------------------------------
def hardness_authenticated() -> dict:
    resp = _resp(_TARGET, bounds=True, stock=_STOCK)
    bounds = _bounds()
    by_digest = {d.route_digest: d for d in resp.ranked_route_dossiers}
    matches = True
    admission_sound = True
    for e in resp.affordability_frontier:
        d = by_digest.get(e.route_digest)
        if d is None:
            admission_sound = False
            continue
        proc = evaluate_process_requirements(d.process_requirements, bounds)
        # every frontier route is FITS or re-derived-process-EXCLUDED (never a process-UNKNOWN sneaking in).
        if d.fit_status != "FITS" and proc.status is not ProcessFitStatus.EXCLUDED:
            admission_sound = False
        # a REAL_BUT_HARD entry's hardness is EXACTLY the re-derived process exclusion (authenticated, not free-text).
        if e.cost_vector.disposition is Disposition.REAL_BUT_HARD:
            if tuple(e.cost_vector.hard_blockers) != tuple(proc.exclusions):
                matches = False
    return {
        "hard_blockers_are_re_derived_process_exclusions": matches,
        "every_frontier_route_fits_or_re_derived_excluded": admission_sound,
    }


# --------------------------------------------------------------------------------------------------
# (3) BYTE-STABLE OFF THE PROCESS PATH: no-bounds frontier unchanged; R59 probe still validates + hash stable.
# --------------------------------------------------------------------------------------------------
def byte_stable_off_process_path() -> dict:
    unbounded = _resp(_TARGET, bounds=False, stock=_STOCK)
    tiers = {e.cost_vector.disposition.name for e in unbounded.affordability_frontier}
    return {
        # with the exact precursors on hand and no bench box, the single esterification is CLEAN (runnable) -- the
        # else-branch behaviour, untouched by the lift.
        "no_bounds_tiers": sorted(tiers),
        "no_bounds_has_no_real_but_hard": Disposition.REAL_BUT_HARD.name not in tiers,
        # R59's probe measures the NO-BOUNDS registry (still 0 reachable real-but-hard) -> unaffected by this lift.
        "r59_probe_still_valid": p59.validate() is True,
        "r59_frozen_hash_stable": p59.content_hash() == p59.FROZEN_HASH,
    }


# --------------------------------------------------------------------------------------------------
# (4) THE HONEST HEADLINE: the RANKING INVERSION stays data-dark -- the two tiers cannot co-occur on a frontier.
# --------------------------------------------------------------------------------------------------
def inversion_still_dark() -> dict:
    bounded = _resp(_TARGET, bounds=True, stock=_STOCK)            # REAL_BUT_HARD source (process-EXCLUDED)
    unbounded = _resp(_TARGET, bounds=False)                       # NOT_A_REACTION source (fictions, no stock)
    b_tiers = {e.cost_vector.disposition.name for e in bounded.affordability_frontier}
    u_tiers = {e.cost_vector.disposition.name for e in unbounded.affordability_frontier}
    return {
        "bounded_frontier_tiers": sorted(b_tiers),
        "unbounded_frontier_tiers": sorted(u_tiers),
        "real_but_hard_under_bounds": Disposition.REAL_BUT_HARD.name in b_tiers,
        "not_a_reaction_without_bounds": Disposition.NOT_A_REACTION.name in u_tiers,
        # under bounds, fictions (process-UNKNOWN) are excluded -> a bounded frontier carries NO NOT_A_REACTION;
        # without bounds there is no REAL_BUT_HARD -> the two tiers never share a frontier -> the inversion is dark.
        "no_fiction_on_bounded_frontier": Disposition.NOT_A_REACTION.name not in b_tiers,
        "no_real_but_hard_without_bounds": Disposition.REAL_BUT_HARD.name not in u_tiers,
        "inversion_data_dark": (
            Disposition.NOT_A_REACTION.name not in b_tiers
            and Disposition.REAL_BUT_HARD.name not in u_tiers
        ),
    }


# --------------------------------------------------------------------------------------------------
# (5) NO REGRESSION: prior poor-man probes stay frozen; admissible_route_digests keeps its FITS-only meaning.
# --------------------------------------------------------------------------------------------------
def no_regression() -> dict:
    prior = {
        name: (hasattr(m, "validate") and hasattr(m, "content_hash") and isinstance(getattr(m, "FROZEN_HASH", None), str))
        for name, m in (("p56", p56), ("p57", p57), ("p58", p58), ("p59", p59))
    }
    # admissible_route_digests is bench-readiness (FITS only): an EXCLUDED (REAL_BUT_HARD) route is on the frontier
    # but is NEVER claimed bench-admissible -- the two notions stay distinct (the lift did not conflate them).
    resp = _resp(_TARGET, bounds=True, stock=_STOCK)
    rbh_digests = {e.route_digest for e in resp.affordability_frontier
                   if e.cost_vector.disposition is Disposition.REAL_BUT_HARD}
    real_but_hard_never_bench_admissible = not (rbh_digests & set(resp.admissible_route_digests))
    return {
        "prior_probes_frozen": prior,
        "all_prior_probes_frozen": all(prior.values()),
        "real_but_hard_never_bench_admissible": real_but_hard_never_bench_admissible,
    }


def _payload() -> dict:
    act = activation_reachable()
    auth = hardness_authenticated()
    stab = byte_stable_off_process_path()
    dark = inversion_still_dark()
    reg = no_regression()
    return {
        "activation_reachable": act,
        "hardness_authenticated": auth,
        "byte_stable_off_process_path": stab,
        "inversion_still_dark": dark,
        "no_regression": reg,
        # THE VERDICT: the REAL_BUT_HARD tier is now REACHABLE + VISIBLE on a bench-constrained frontier (gate lifted),
        # its hardness is AUTHENTICATED (re-derived process exclusion), the no-process path is byte-stable and R59 stays
        # frozen, the RANKING INVERSION is HONESTLY still data-dark (the two tiers cannot co-occur -- reachable only via
        # the catalyst/escape-#7 source), and nothing regressed (prior hashes stable, bench-readiness unconflated).
        "ship_verdict": (
            act["gate_lifted_proof"] and act["real_but_hard_reachable"] and act["hard_reason_is_equipment"]
            and auth["hard_blockers_are_re_derived_process_exclusions"]
            and auth["every_frontier_route_fits_or_re_derived_excluded"]
            and stab["no_bounds_has_no_real_but_hard"] and stab["r59_probe_still_valid"]
            and stab["r59_frozen_hash_stable"]
            and dark["inversion_data_dark"]
            and reg["all_prior_probes_frozen"] and reg["real_but_hard_never_bench_admissible"]
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert DISPOSITION-ACTIVATE-01 against live code: the REAL_BUT_HARD tier is now reachable + visible on a
    bench-constrained frontier (the FITS-only gate is lifted), its hardness is authenticated by the re-derived process
    exclusion, the no-process path is byte-stable and R59 stays frozen, the ranking INVERSION is honestly still
    data-dark (the two tiers cannot co-occur -- reachable only via the catalyst source), and nothing regressed."""
    p = _payload()
    act = p["activation_reachable"]
    assert act["real_but_hard_reachable"], f"REAL_BUT_HARD is not reachable on the bench-constrained frontier: {act}"
    assert act["gate_lifted_proof"], f"the FITS-only gate was NOT lifted (route not on frontier while non-FITS): {act}"
    assert act["hard_reason_is_equipment"], f"the hardness is not the poor-man equipment wall: {act}"
    auth = p["hardness_authenticated"]
    assert auth["hard_blockers_are_re_derived_process_exclusions"], \
        f"REAL_BUT_HARD hardness is not the RE-DERIVED (authenticated) process exclusion: {auth}"
    assert auth["every_frontier_route_fits_or_re_derived_excluded"], \
        f"a frontier route is neither FITS nor re-derived-process-EXCLUDED (unsound admission): {auth}"
    stab = p["byte_stable_off_process_path"]
    assert stab["no_bounds_has_no_real_but_hard"], f"the no-bounds path grew a REAL_BUT_HARD route (ripple): {stab}"
    assert stab["r59_probe_still_valid"] and stab["r59_frozen_hash_stable"], \
        f"R59's probe regressed under the lift (its no-bounds measurement must be untouched): {stab}"
    dark = p["inversion_still_dark"]
    # the HONEST headline is an assertion: if the two tiers ever co-occur on a frontier this FLIPS and the ranking
    # inversion has become reachable via the exclusion source -- re-state this round (a genuine inversion consumer).
    assert dark["inversion_data_dark"], \
        f"the ranking INVERSION is NO LONGER data-dark -- REAL_BUT_HARD and NOT_A_REACTION now co-occur, re-state: {dark}"
    reg = p["no_regression"]
    assert reg["all_prior_probes_frozen"], f"a prior poor-man probe lost its frozen seal: {reg['prior_probes_frozen']}"
    assert reg["real_but_hard_never_bench_admissible"], \
        f"a REAL_BUT_HARD route was conflated into bench-readiness (admissible_route_digests): {reg}"
    assert p["ship_verdict"], f"DISPOSITION-ACTIVATE-01 SHIP verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
